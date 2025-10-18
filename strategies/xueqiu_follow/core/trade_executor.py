#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易执行模块
负责执行交易指令，处理交易结果，管理订单状态
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

import sys
import os

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from easy_xt import get_advanced_api
from .risk_manager import RiskManager
from strategies.xueqiu_follow.utils.logger import setup_logger


class OrderStatus(Enum):
    """订单状态枚举"""
    PENDING = "pending"          # 待提交
    SUBMITTED = "submitted"      # 已提交
    PARTIAL_FILLED = "partial_filled"  # 部分成交
    FILLED = "filled"           # 全部成交
    CANCELLED = "cancelled"     # 已撤销
    REJECTED = "rejected"       # 被拒绝
    FAILED = "failed"          # 执行失败


class OrderType(Enum):
    """订单类型枚举"""
    MARKET = "market"          # 市价单
    LIMIT = "limit"           # 限价单
    STOP = "stop"             # 止损单


class TradeExecutor:
    """交易执行器"""
    
    def __init__(self, qmt_config: Dict[str, Any]):
        self.logger = setup_logger("TradeExecutor")
        self.config = qmt_config
        
        # 核心组件
        self.trader_api = get_advanced_api()
        self.risk_manager: Optional[RiskManager] = None
        
        # 订单管理
        self.active_orders: Dict[str, Dict[str, Any]] = {}
        self.order_history: List[Dict[str, Any]] = []
        self.execution_stats: Dict[str, Any] = {
            'total_orders': 0,
            'successful_orders': 0,
            'failed_orders': 0,
            'total_volume': 0,
            'total_amount': 0
        }
        
        # 执行控制
        self.max_concurrent_orders = qmt_config.get('max_concurrent_orders', 10)
        self.order_timeout = qmt_config.get('order_timeout', 30)  # 秒
        self.retry_times = qmt_config.get('retry_times', 3)
        self.retry_delay = qmt_config.get('retry_delay', 1)  # 秒
        
    async def initialize(self):
        """初始化交易执行器"""
        try:
            self.logger.info("初始化交易执行器...")
            
            # 初始化交易接口
            userdata_path = self.config.get('userdata_path', 'D:/国金证券QMT交易端/userdata_mini')
            session_id = self.config.get('session_id', 'xueqiu_follow')
            
            if not self.trader_api.connect(userdata_path, session_id):
                raise Exception("交易服务连接失败")
            
            # 添加交易账户
            account_id = self.config.get('account_id')
            if account_id and not self.trader_api.add_account(account_id):
                raise Exception(f"添加交易账户失败: {account_id}")
            
            # 初始化风险管理器
            self.risk_manager = RiskManager(self.config.get('risk_config_path'))
            
            self.logger.info("交易执行器初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"交易执行器初始化失败: {e}")
            return False
    
    async def execute_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个交易指令"""
        order_id = f"order_{int(time.time() * 1000)}_{len(self.active_orders)}"
        
        try:
            self.logger.info(f"开始执行订单: {order_id}")
            
            # 订单预处理
            processed_order = await self._preprocess_order(order, order_id)
            if not processed_order:
                return self._create_order_result(order_id, OrderStatus.REJECTED, "订单预处理失败")
            
            # 风险检查
            risk_check = await self._check_order_risk(processed_order)
            if not risk_check['allowed']:
                return self._create_order_result(order_id, OrderStatus.REJECTED, f"风险检查失败: {risk_check['reason']}")
            
            # 添加到活跃订单
            self.active_orders[order_id] = processed_order
            
            # 执行订单
            execution_result = await self._execute_order_with_retry(processed_order)
            
            # 更新订单状态
            await self._update_order_status(order_id, execution_result)
            
            # 更新统计信息
            self._update_execution_stats(execution_result)
            
            return execution_result
            
        except Exception as e:
            self.logger.error(f"执行订单 {order_id} 失败: {e}")
            return self._create_order_result(order_id, OrderStatus.FAILED, str(e))
    
    async def execute_batch_orders(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量执行交易指令"""
        try:
            self.logger.info(f"开始批量执行 {len(orders)} 个订单")
            
            # 检查并发限制
            if len(orders) > self.max_concurrent_orders:
                self.logger.warning(f"订单数量 {len(orders)} 超过并发限制 {self.max_concurrent_orders}，将分批执行")
                return await self._execute_orders_in_batches(orders)
            
            # 并发执行所有订单
            tasks = [self.execute_order(order) for order in orders]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常结果
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_result = self._create_order_result(
                        f"batch_order_{i}", 
                        OrderStatus.FAILED, 
                        str(result)
                    )
                    processed_results.append(error_result)
                else:
                    processed_results.append(result)
            
            self.logger.info(f"批量执行完成，成功: {sum(1 for r in processed_results if r['status'] == OrderStatus.FILLED.value)}")
            return processed_results
            
        except Exception as e:
            self.logger.error(f"批量执行订单失败: {e}")
            return [self._create_order_result("batch_error", OrderStatus.FAILED, str(e))]
    
    async def _execute_orders_in_batches(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """分批执行订单"""
        all_results = []
        batch_size = self.max_concurrent_orders
        
        for i in range(0, len(orders), batch_size):
            batch = orders[i:i + batch_size]
            self.logger.info(f"执行第 {i//batch_size + 1} 批订单，数量: {len(batch)}")
            
            batch_results = await self.execute_batch_orders(batch)
            all_results.extend(batch_results)
            
            # 批次间延迟
            if i + batch_size < len(orders):
                await asyncio.sleep(0.5)
        
        return all_results
    
    async def _preprocess_order(self, order: Dict[str, Any], order_id: str) -> Optional[Dict[str, Any]]:
        """订单预处理"""
        try:
            # 验证必要字段
            required_fields = ['symbol', 'action', 'volume']
            for field in required_fields:
                if field not in order:
                    self.logger.error(f"订单缺少必要字段: {field}")
                    return None
            
            # 标准化订单格式
            processed_order = {
                'order_id': order_id,
                'symbol': order['symbol'].upper(),
                'action': order['action'].lower(),  # buy/sell
                'volume': int(order['volume']),
                'order_type': order.get('order_type', OrderType.LIMIT.value),
                'price': float(order.get('price', 0)),
                'timestamp': datetime.now(),
                'status': OrderStatus.PENDING.value,
                'reason': order.get('reason', ''),
                'retry_count': 0
            }
            
            # 验证订单参数
            if processed_order['volume'] <= 0:
                self.logger.error(f"订单数量无效: {processed_order['volume']}")
                return None
            
            if processed_order['action'] not in ['buy', 'sell']:
                self.logger.error(f"订单操作无效: {processed_order['action']}")
                return None
            
            # 确保股数为100的倍数
            processed_order['volume'] = (processed_order['volume'] // 100) * 100
            if processed_order['volume'] == 0:
                self.logger.error("订单数量调整后为0")
                return None
            
            # 限价单必须有有效价格
            if processed_order['order_type'] == OrderType.LIMIT.value:
                if processed_order['price'] is None or processed_order['price'] <= 0:
                    self.logger.error("限价单价格无效或缺失，拒绝下单")
                    return None
            
            return processed_order
            
        except Exception as e:
            self.logger.error(f"订单预处理失败: {e}")
            return None
    
    async def _check_order_risk(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """检查订单风险"""
        try:
            if not self.risk_manager:
                return {'allowed': True, 'reason': '风险管理器未初始化'}
            
            # 获取当前账户信息
            account_info = await self.get_account_info()
            if not account_info:
                return {'allowed': False, 'reason': '无法获取账户信息'}
            
            # 执行风险检查
            risk_result = self.risk_manager.validate_order(
                symbol=order['symbol'],
                order_type=order['action'],
                volume=order['volume'],
                price=order['price'],
                account_info=account_info
            )
            
            return risk_result
            
        except Exception as e:
            self.logger.error(f"风险检查失败: {e}")
            return {'allowed': False, 'reason': f'风险检查异常: {str(e)}'}
    
    async def _execute_order_with_retry(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """带重试的订单执行"""
        last_error = None
        
        for attempt in range(self.retry_times):
            try:
                self.logger.info(f"执行订单 {order['order_id']}，第 {attempt + 1} 次尝试")
                
                # 更新订单状态
                order['status'] = OrderStatus.SUBMITTED.value
                order['retry_count'] = attempt
                
                # 调用交易API执行订单
                account_id = self.config.get('account_id')
                qmt_order_id = self.trader_api.sync_order(
                    account_id=account_id,
                    code=order['symbol'],
                    order_type=order['action'],
                    volume=order['volume'],
                    price=order['price'] if order['order_type'] == OrderType.LIMIT.value else 0,
                    price_type='limit' if order['order_type'] == OrderType.LIMIT.value else 'market'
                )
                
                if qmt_order_id:
                    # 等待订单执行结果
                    execution_result = await self._wait_for_order_completion(order['order_id'], qmt_order_id)
                    return execution_result
                else:
                    raise Exception("QMT订单提交失败")
                    
            except Exception as e:
                last_error = e
                self.logger.warning(f"订单执行第 {attempt + 1} 次尝试失败: {e}")
                
                if attempt < self.retry_times - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))  # 递增延迟
        
        # 所有重试都失败
        return self._create_order_result(
            order['order_id'], 
            OrderStatus.FAILED, 
            f"重试 {self.retry_times} 次后仍失败: {str(last_error)}"
        )
    
    async def _wait_for_order_completion(self, order_id: str, qmt_order_id: str) -> Dict[str, Any]:
        """等待订单完成"""
        start_time = time.time()
        
        while time.time() - start_time < self.order_timeout:
            try:
                # 查询订单状态
                account_id = self.config.get('account_id')
                orders_df = self.trader_api.get_today_orders(account_id)
                orders = {str(row['order_id']): row.to_dict() for _, row in orders_df.iterrows()} if not orders_df.empty else {}
                if str(qmt_order_id) in orders:
                    order_info = orders[qmt_order_id]
                    status = order_info.get('status', 'unknown')
                    
                    if status in ['filled', 'cancelled', 'rejected']:
                        # 订单已完成
                        return self._create_order_result(
                            order_id,
                            OrderStatus.FILLED if status == 'filled' else OrderStatus.CANCELLED,
                            f"QMT订单状态: {status}",
                            qmt_order_id=qmt_order_id,
                            filled_volume=order_info.get('filled_volume', 0),
                            filled_price=order_info.get('filled_price', 0)
                        )
                
                await asyncio.sleep(1)  # 每秒检查一次
                
            except Exception as e:
                self.logger.warning(f"查询订单状态失败: {e}")
                await asyncio.sleep(1)
        
        # 超时
        return self._create_order_result(
            order_id, 
            OrderStatus.FAILED, 
            f"订单执行超时 ({self.order_timeout}秒)"
        )
    
    def _create_order_result(self, order_id: str, status: OrderStatus, message: str = "", 
                           qmt_order_id: str = None, filled_volume: int = 0, 
                           filled_price: float = 0) -> Dict[str, Any]:
        """创建订单结果"""
        return {
            'order_id': order_id,
            'qmt_order_id': qmt_order_id,
            'status': status.value if isinstance(status, OrderStatus) else status,
            'message': message,
            'filled_volume': filled_volume,
            'filled_price': filled_price,
            'timestamp': datetime.now().isoformat(),
            'success': status in [OrderStatus.FILLED, OrderStatus.PARTIAL_FILLED]
        }
    
    async def _update_order_status(self, order_id: str, result: Dict[str, Any]):
        """更新订单状态"""
        try:
            if order_id in self.active_orders:
                order = self.active_orders[order_id]
                order['status'] = result['status']
                order['qmt_order_id'] = result.get('qmt_order_id')
                order['filled_volume'] = result.get('filled_volume', 0)
                order['filled_price'] = result.get('filled_price', 0)
                order['completion_time'] = datetime.now()
                
                # 如果订单完成，移到历史记录
                if result['status'] in [OrderStatus.FILLED.value, OrderStatus.CANCELLED.value, OrderStatus.FAILED.value]:
                    self.order_history.append(order.copy())
                    del self.active_orders[order_id]
                    
        except Exception as e:
            self.logger.error(f"更新订单状态失败: {e}")
    
    def _update_execution_stats(self, result: Dict[str, Any]):
        """更新执行统计"""
        try:
            self.execution_stats['total_orders'] += 1
            
            if result.get('success', False):
                self.execution_stats['successful_orders'] += 1
                self.execution_stats['total_volume'] += result.get('filled_volume', 0)
                self.execution_stats['total_amount'] += result.get('filled_volume', 0) * result.get('filled_price', 0)
            else:
                self.execution_stats['failed_orders'] += 1
                
        except Exception as e:
            self.logger.error(f"更新执行统计失败: {e}")
    
    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """获取账户信息（资金、持仓等）"""
        try:
            account_id = self.config.get('account_id')
            if not account_id:
                return None
            
            account_info = self.trader_api.get_account_asset_detailed(account_id)
            return account_info
            
        except Exception as e:
            self.logger.error(f"获取账户信息失败: {e}")
            return None
    
    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """查询订单状态"""
        try:
            # 先查活跃订单
            if order_id in self.active_orders:
                return self.active_orders[order_id]
            
            # 再查历史订单
            for order in self.order_history:
                if order['order_id'] == order_id:
                    return order
            
            return None
            
        except Exception as e:
            self.logger.error(f"查询订单状态失败: {e}")
            return None
    
    async def cancel_order(self, order_id: str) -> bool:
        """撤销订单"""
        try:
            self.logger.info(f"撤销订单: {order_id}")
            
            # 检查订单是否存在
            if order_id not in self.active_orders:
                self.logger.warning(f"订单 {order_id} 不存在或已完成")
                return False
            
            order = self.active_orders[order_id]
            qmt_order_id = order.get('qmt_order_id')
            
            if not qmt_order_id:
                self.logger.warning(f"订单 {order_id} 没有QMT订单ID")
                return False
            
            # 调用交易API撤销订单
            account_id = self.config.get('account_id')
            if not account_id:
                return False
            
            # 处理QMT订单ID类型转换
            try:
                qmt_id = int(qmt_order_id) if isinstance(qmt_order_id, str) and qmt_order_id.isdigit() else qmt_order_id
            except (ValueError, TypeError):
                self.logger.error(f"无效的QMT订单ID格式: {qmt_order_id}")
                return False
                
            success = self.trader_api.sync_cancel_order(account_id, qmt_id)
            
            if success:
                # 更新订单状态
                await self._update_order_status(order_id, self._create_order_result(
                    order_id, OrderStatus.CANCELLED, "用户主动撤销"
                ))
                self.logger.info(f"订单 {order_id} 撤销成功")
            else:
                self.logger.warning(f"订单 {order_id} 撤销失败")
            
            return success
            
        except Exception as e:
            self.logger.error(f"撤销订单失败: {e}")
            return False
    
    async def cancel_all_orders(self) -> int:
        """撤销所有活跃订单"""
        try:
            self.logger.info(f"撤销所有活跃订单，数量: {len(self.active_orders)}")
            
            cancelled_count = 0
            order_ids = list(self.active_orders.keys())
            
            for order_id in order_ids:
                if await self.cancel_order(order_id):
                    cancelled_count += 1
            
            self.logger.info(f"成功撤销 {cancelled_count} 个订单")
            return cancelled_count
            
        except Exception as e:
            self.logger.error(f"撤销所有订单失败: {e}")
            return 0
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        stats = self.execution_stats.copy()
        stats['success_rate'] = (
            stats['successful_orders'] / stats['total_orders'] 
            if stats['total_orders'] > 0 else 0
        )
        stats['active_orders_count'] = len(self.active_orders)
        stats['history_orders_count'] = len(self.order_history)
        return stats
    
    def get_active_orders(self) -> Dict[str, Dict[str, Any]]:
        """获取活跃订单"""
        return self.active_orders.copy()
    
    def get_order_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取订单历史"""
        return self.order_history[-limit:] if limit > 0 else self.order_history.copy()
    
    async def close(self):
        """关闭交易执行器"""
        try:
            self.logger.info("关闭交易执行器...")
            
            # 撤销所有活跃订单
            if self.active_orders:
                await self.cancel_all_orders()
            
            # 关闭交易连接
            if hasattr(self.trader_api, 'disconnect'):
                self.trader_api.disconnect()
            
            self.logger.info("交易执行器已关闭")
            
        except Exception as e:
            self.logger.error(f"关闭交易执行器失败: {e}")


async def main():
    """测试函数"""
    config = {
        'qmt_path': 'C:/QMT/',
        'account_id': 'test_account',
        'max_concurrent_orders': 5,
        'order_timeout': 30,
        'retry_times': 3
    }
    
    executor = TradeExecutor(config)
    
    try:
        # 初始化
        if not await executor.initialize():
            print("初始化失败")
            return
        
        # 测试单个订单
        test_order = {
            'symbol': '000001',
            'action': 'buy',
            'volume': 100,
            'order_type': 'market',
            'reason': '测试买入'
        }
        
        result = await executor.execute_order(test_order)
        print(f"订单执行结果: {result}")
        
        # 获取统计信息
        stats = executor.get_execution_stats()
        print(f"执行统计: {stats}")
        
    finally:
        await executor.close()


if __name__ == "__main__":
    asyncio.run(main())