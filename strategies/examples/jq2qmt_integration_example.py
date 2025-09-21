#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JQ2QMT集成示例
演示如何在EasyXT策略中使用JQ2QMT功能
"""

import sys
import os
import time
import logging
from typing import List, Dict

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from base.strategy_template import BaseStrategy
from adapters.jq2qmt_adapter import EasyXTJQ2QMTAdapter, jq2qmt_manager
from adapters.data_converter import DataConverter, PositionDiffer


class JQ2QMTIntegratedStrategy(BaseStrategy):
    """集成JQ2QMT功能的策略示例"""
    
    def __init__(self, config):
        super().__init__(config)
        
        # JQ2QMT配置
        self.jq2qmt_config = config.get('jq2qmt_config', {})
        self.enable_jq2qmt = self.jq2qmt_config.get('enabled', False)
        
        # 初始化JQ2QMT适配器
        self.jq2qmt_adapter = None
        if self.enable_jq2qmt:
            self._init_jq2qmt_adapter()
        
        # 持仓同步设置
        self.auto_sync_positions = self.jq2qmt_config.get('auto_sync', True)
        self.sync_interval = self.jq2qmt_config.get('sync_interval', 30)
        self.last_sync_time = 0
        
        self.logger.info(f"JQ2QMT集成{'已启用' if self.enable_jq2qmt else '已禁用'}")
    
    def _init_jq2qmt_adapter(self):
        """初始化JQ2QMT适配器"""
        try:
            self.jq2qmt_adapter = EasyXTJQ2QMTAdapter(self.jq2qmt_config)
            
            if self.jq2qmt_adapter.is_available():
                # 测试连接
                if self.jq2qmt_adapter.test_connection():
                    self.logger.info("JQ2QMT适配器初始化成功，连接正常")
                    
                    # 注册到全局管理器
                    jq2qmt_manager.add_adapter(self.strategy_name, self.jq2qmt_config)
                else:
                    self.logger.warning("JQ2QMT适配器初始化成功，但连接失败")
            else:
                self.logger.error("JQ2QMT适配器不可用")
                self.jq2qmt_adapter = None
                
        except Exception as e:
            self.logger.error(f"JQ2QMT适配器初始化失败: {e}")
            self.jq2qmt_adapter = None
    
    def update_positions(self, positions: List[Dict]):
        """
        更新持仓 - 扩展支持JQ2QMT同步
        
        Args:
            positions: EasyXT格式的持仓列表
                [
                    {
                        'symbol': '000001.SZ',
                        'name': '平安银行',
                        'quantity': 1000,
                        'avg_price': 12.50
                    }
                ]
        """
        # 调用父类方法更新本地持仓
        super().update_positions(positions)
        
        # 同步到JQ2QMT
        if self.enable_jq2qmt and self.jq2qmt_adapter:
            self._sync_positions_to_jq2qmt(positions)
    
    def _sync_positions_to_jq2qmt(self, positions: List[Dict]):
        """同步持仓到JQ2QMT"""
        try:
            # 检查是否需要同步
            current_time = time.time()
            if not self.auto_sync_positions:
                return
            
            if current_time - self.last_sync_time < self.sync_interval:
                return
            
            # 执行同步
            success = self.jq2qmt_adapter.sync_positions_to_qmt(
                self.strategy_name, positions
            )
            
            if success:
                self.last_sync_time = current_time
                self.logger.info(f"持仓已同步到JQ2QMT: {len(positions)} 个持仓")
                
                # 记录同步详情
                for pos in positions:
                    self.logger.debug(
                        f"同步持仓: {pos['symbol']} {pos['name']} "
                        f"数量:{pos['quantity']} 成本:{pos['avg_price']:.3f}"
                    )
            else:
                self.logger.error("持仓同步到JQ2QMT失败")
                
        except Exception as e:
            self.logger.error(f"JQ2QMT持仓同步异常: {e}")
    
    def get_jq2qmt_positions(self) -> List[Dict]:
        """从JQ2QMT获取持仓信息"""
        if not self.jq2qmt_adapter:
            return []
        
        try:
            positions = self.jq2qmt_adapter.get_strategy_positions(self.strategy_name)
            return positions if positions else []
        except Exception as e:
            self.logger.error(f"从JQ2QMT获取持仓失败: {e}")
            return []
    
    def compare_positions_with_jq2qmt(self) -> Dict:
        """比较本地持仓与JQ2QMT持仓的差异"""
        if not self.jq2qmt_adapter:
            return {}
        
        try:
            # 获取本地持仓
            local_positions = self.get_current_positions()
            
            # 获取JQ2QMT持仓
            jq2qmt_positions = self.get_jq2qmt_positions()
            
            # 比较差异
            diff_result = PositionDiffer.compare_positions(
                local_positions, jq2qmt_positions, 'easyxt'
            )
            
            self.logger.info(f"持仓差异分析: "
                           f"买入{len(diff_result['to_buy'])} "
                           f"卖出{len(diff_result['to_sell'])} "
                           f"调整{len(diff_result['to_adjust'])} "
                           f"不变{len(diff_result['unchanged'])}")
            
            return diff_result
            
        except Exception as e:
            self.logger.error(f"持仓差异分析失败: {e}")
            return {}
    
    def force_sync_to_jq2qmt(self):
        """强制同步持仓到JQ2QMT"""
        if not self.jq2qmt_adapter:
            self.logger.warning("JQ2QMT适配器不可用，无法强制同步")
            return False
        
        try:
            positions = self.get_current_positions()
            success = self.jq2qmt_adapter.sync_positions_to_qmt(
                self.strategy_name, positions
            )
            
            if success:
                self.last_sync_time = time.time()
                self.logger.info("强制同步到JQ2QMT成功")
            else:
                self.logger.error("强制同步到JQ2QMT失败")
            
            return success
            
        except Exception as e:
            self.logger.error(f"强制同步到JQ2QMT异常: {e}")
            return False
    
    def get_jq2qmt_sync_status(self) -> Dict:
        """获取JQ2QMT同步状态"""
        if not self.jq2qmt_adapter:
            return {'available': False, 'message': 'JQ2QMT适配器不可用'}
        
        try:
            status = self.jq2qmt_adapter.get_sync_status()
            status['available'] = True
            status['last_local_sync'] = self.last_sync_time
            return status
        except Exception as e:
            return {'available': False, 'message': f'获取状态失败: {e}'}
    
    def on_strategy_start(self):
        """策略启动时的处理"""
        super().on_strategy_start()
        
        if self.enable_jq2qmt and self.jq2qmt_adapter:
            self.logger.info("策略启动，准备同步初始持仓到JQ2QMT")
            
            # 获取当前持仓并同步
            current_positions = self.get_current_positions()
            if current_positions:
                self._sync_positions_to_jq2qmt(current_positions)
    
    def on_strategy_stop(self):
        """策略停止时的处理"""
        super().on_strategy_stop()
        
        if self.enable_jq2qmt and self.jq2qmt_adapter:
            self.logger.info("策略停止，执行最后一次持仓同步")
            
            # 最后一次同步
            current_positions = self.get_current_positions()
            if current_positions:
                self.force_sync_to_jq2qmt()
            
            # 从全局管理器中移除
            jq2qmt_manager.remove_adapter(self.strategy_name)


def create_jq2qmt_strategy_config():
    """创建包含JQ2QMT配置的策略配置示例"""
    return {
        # 基础策略配置
        'strategy_name': 'JQ2QMT集成示例策略',
        'symbol_list': ['000001.SZ', '000002.SZ', '600000.SH'],
        'initial_capital': 1000000,
        
        # JQ2QMT集成配置
        'jq2qmt_config': {
            'enabled': True,  # 启用JQ2QMT集成
            'server_url': 'http://localhost:5366',
            'auth_config': {
                'use_crypto_auth': True,
                'client_id': 'easyxt_strategy_client',
                'private_key_file': 'keys/easyxt_private.pem',
                'simple_api_key': ''  # 不使用RSA时的简单密钥
            },
            'sync_settings': {
                'auto_sync': True,  # 自动同步持仓
                'sync_interval': 30,  # 同步间隔(秒)
                'retry_times': 3  # 重试次数
            }
        },
        
        # 其他策略参数
        'risk_management': {
            'max_position_ratio': 0.1,  # 单只股票最大持仓比例
            'stop_loss_ratio': 0.05,    # 止损比例
            'take_profit_ratio': 0.15   # 止盈比例
        }
    }


def demo_jq2qmt_integration():
    """JQ2QMT集成功能演示"""
    print("=== JQ2QMT集成功能演示 ===")
    
    # 创建策略配置
    config = create_jq2qmt_strategy_config()
    
    # 创建策略实例
    strategy = JQ2QMTIntegratedStrategy(config)
    
    # 模拟持仓数据
    demo_positions = [
        {
            'symbol': '000001.SZ',
            'name': '平安银行',
            'quantity': 1000,
            'avg_price': 12.50
        },
        {
            'symbol': '000002.SZ',
            'name': '万科A',
            'quantity': 500,
            'avg_price': 25.80
        },
        {
            'symbol': '600000.SH',
            'name': '浦发银行',
            'quantity': 800,
            'avg_price': 8.90
        }
    ]
    
    print(f"策略名称: {strategy.strategy_name}")
    print(f"JQ2QMT集成状态: {'已启用' if strategy.enable_jq2qmt else '已禁用'}")
    
    if strategy.enable_jq2qmt:
        # 获取同步状态
        sync_status = strategy.get_jq2qmt_sync_status()
        print(f"JQ2QMT连接状态: {sync_status}")
        
        # 更新持仓（会自动同步到JQ2QMT）
        print("\n更新持仓...")
        strategy.update_positions(demo_positions)
        
        # 等待同步完成
        time.sleep(2)
        
        # 从JQ2QMT获取持仓
        print("\n从JQ2QMT获取持仓...")
        jq2qmt_positions = strategy.get_jq2qmt_positions()
        print(f"JQ2QMT持仓数量: {len(jq2qmt_positions)}")
        
        for pos in jq2qmt_positions:
            print(f"  {pos['symbol']} {pos['name']} "
                  f"数量:{pos['quantity']} 成本:{pos['avg_price']:.3f}")
        
        # 持仓差异分析
        print("\n持仓差异分析...")
        diff_result = strategy.compare_positions_with_jq2qmt()
        if diff_result:
            print(f"  需要买入: {len(diff_result.get('to_buy', []))}")
            print(f"  需要卖出: {len(diff_result.get('to_sell', []))}")
            print(f"  需要调整: {len(diff_result.get('to_adjust', []))}")
            print(f"  无需变动: {len(diff_result.get('unchanged', []))}")
        
        # 强制同步测试
        print("\n执行强制同步...")
        sync_success = strategy.force_sync_to_jq2qmt()
        print(f"强制同步结果: {'成功' if sync_success else '失败'}")
    
    else:
        print("JQ2QMT集成未启用，请检查配置")
    
    print("\n=== 演示完成 ===")


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行演示
    demo_jq2qmt_integration()