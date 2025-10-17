#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易执行器测试
"""

import unittest
import asyncio
import sys
import os
from unittest.mock import Mock, patch, AsyncMock

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from strategies.xueqiu_follow.core.trade_executor import TradeExecutor, OrderStatus, OrderType


class TestTradeExecutor(unittest.TestCase):
    """交易执行器测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.config = {
            'qmt_path': 'C:/QMT/',
            'account_id': 'test_account',
            'max_concurrent_orders': 5,
            'order_timeout': 10,
            'retry_times': 2,
            'retry_delay': 0.1
        }
        self.executor = TradeExecutor(self.config)
    
    def test_preprocess_order_valid(self):
        """测试有效订单预处理"""
        order = {
            'symbol': 'sz000001',
            'action': 'BUY',
            'volume': 150,
            'price': 10.5,
            'order_type': 'market'
        }
        
        # 使用asyncio运行异步方法
        async def run_test():
            result = await self.executor._preprocess_order(order, 'test_order_1')
            return result
        
        result = asyncio.run(run_test())
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result['symbol'], 'SZ000001')
        self.assertEqual(result['action'], 'buy')
        self.assertEqual(result['volume'], 100)  # 应该调整为100的倍数
        self.assertEqual(result['order_id'], 'test_order_1')
    
    def test_preprocess_order_invalid(self):
        """测试无效订单预处理"""
        # 缺少必要字段
        invalid_order = {
            'symbol': '000001',
            'action': 'buy'
            # 缺少volume
        }
        
        async def run_test():
            result = await self.executor._preprocess_order(invalid_order, 'test_order_2')
            return result
        
        result = asyncio.run(run_test())
        self.assertIsNone(result)
    
    def test_create_order_result(self):
        """测试订单结果创建"""
        result = self.executor._create_order_result(
            'test_order', 
            OrderStatus.FILLED, 
            'success',
            qmt_order_id='qmt_123',
            filled_volume=100,
            filled_price=10.5
        )
        
        self.assertEqual(result['order_id'], 'test_order')
        self.assertEqual(result['status'], OrderStatus.FILLED.value)
        self.assertEqual(result['qmt_order_id'], 'qmt_123')
        self.assertEqual(result['filled_volume'], 100)
        self.assertEqual(result['filled_price'], 10.5)
        self.assertTrue(result['success'])
    
    def test_update_execution_stats(self):
        """测试执行统计更新"""
        # 成功订单
        success_result = {
            'success': True,
            'filled_volume': 100,
            'filled_price': 10.0
        }
        
        self.executor._update_execution_stats(success_result)
        
        stats = self.executor.get_execution_stats()
        self.assertEqual(stats['total_orders'], 1)
        self.assertEqual(stats['successful_orders'], 1)
        self.assertEqual(stats['failed_orders'], 0)
        self.assertEqual(stats['total_volume'], 100)
        self.assertEqual(stats['total_amount'], 1000.0)
        
        # 失败订单
        failed_result = {'success': False}
        self.executor._update_execution_stats(failed_result)
        
        stats = self.executor.get_execution_stats()
        self.assertEqual(stats['total_orders'], 2)
        self.assertEqual(stats['successful_orders'], 1)
        self.assertEqual(stats['failed_orders'], 1)


class TestTradeExecutorAsync(unittest.IsolatedAsyncioTestCase):
    """交易执行器异步测试类"""
    
    async def asyncSetUp(self):
        """异步测试前准备"""
        self.config = {
            'qmt_path': 'C:/QMT/',
            'account_id': 'test_account',
            'max_concurrent_orders': 5,
            'order_timeout': 2,
            'retry_times': 2,
            'retry_delay': 0.1
        }
        self.executor = TradeExecutor(self.config)
    
    @patch('strategies.xueqiu_follow.core.trade_executor.get_advanced_api')
    @patch('strategies.xueqiu_follow.core.trade_executor.RiskManager')
    async def test_initialize(self, mock_risk_manager, mock_qmt_trader):
        """测试初始化"""
        # 设置mocks
        mock_qmt_instance = AsyncMock()
        mock_qmt_instance.initialize.return_value = True
        mock_qmt_trader.return_value = mock_qmt_instance
        
        mock_risk_instance = Mock()
        mock_risk_manager.return_value = mock_risk_instance
        
        # 执行初始化
        result = await self.executor.initialize()
        
        # 验证结果
        self.assertTrue(result)
        mock_qmt_instance.initialize.assert_called_once()
    
    @patch('strategies.xueqiu_follow.core.trade_executor.get_advanced_api')
    @patch('strategies.xueqiu_follow.core.trade_executor.RiskManager')
    async def test_execute_order_success(self, mock_risk_manager, mock_get_api):
        """测试成功执行订单"""
        # 设置mocks
        mock_qmt_instance = AsyncMock()
        mock_qmt_instance.initialize.return_value = True
        mock_qmt_instance.place_order.return_value = 'qmt_order_123'
        mock_qmt_instance.get_orders.return_value = {
            'qmt_order_123': {
                'status': 'filled',
                'filled_volume': 100,
                'filled_price': 10.5
            }
        }
        mock_qmt_instance.get_account_info.return_value = {
            'total_asset': 100000,
            'available_cash': 50000
        }
        
        mock_risk_instance = Mock()
        mock_risk_instance.validate_order.return_value = {'allowed': True}
        
        # 设置执行器
        self.executor.trader_api = mock_qmt_instance
        self.executor.risk_manager = mock_risk_instance
        
        # 测试订单
        order = {
            'symbol': '000001',
            'action': 'buy',
            'volume': 100,
            'price': 10.5,
            'order_type': 'market'
        }
        
        # 执行订单
        result = await self.executor.execute_order(order)
        
        # 验证结果
        self.assertEqual(result['status'], OrderStatus.FILLED.value)
        self.assertTrue(result['success'])
        self.assertEqual(result['filled_volume'], 100)
        self.assertEqual(result['filled_price'], 10.5)
        
        # 验证调用
        mock_qmt_instance.place_order.assert_called_once()
        mock_risk_instance.validate_order.assert_called_once()
    
    @patch('strategies.xueqiu_follow.core.trade_executor.get_advanced_api')
    @patch('strategies.xueqiu_follow.core.trade_executor.RiskManager')
    async def test_execute_order_risk_rejected(self, mock_risk_manager, mock_get_api):
        """测试风险检查拒绝订单"""
        # 设置mocks
        mock_qmt_instance = AsyncMock()
        mock_qmt_instance.get_account_info.return_value = {
            'total_asset': 100000,
            'available_cash': 50000
        }
        
        mock_risk_instance = Mock()
        mock_risk_instance.validate_order.return_value = {
            'allowed': False, 
            'reason': '超过仓位限制'
        }
        
        # 设置执行器
        self.executor.trader_api = mock_qmt_instance
        self.executor.risk_manager = mock_risk_instance
        
        # 测试订单
        order = {
            'symbol': '000001',
            'action': 'buy',
            'volume': 100,
            'price': 10.5
        }
        
        # 执行订单
        result = await self.executor.execute_order(order)
        
        # 验证结果
        self.assertEqual(result['status'], OrderStatus.REJECTED.value)
        self.assertFalse(result['success'])
        self.assertIn('超过仓位限制', result['message'])
        
        # 验证没有调用下单
        mock_qmt_instance.place_order.assert_not_called()
    
    @patch('strategies.xueqiu_follow.core.trade_executor.get_advanced_api')
    @patch('strategies.xueqiu_follow.core.trade_executor.RiskManager')
    async def test_execute_batch_orders(self, mock_risk_manager, mock_get_api):
        """测试批量执行订单"""
        # 设置mocks
        mock_qmt_instance = AsyncMock()
        mock_qmt_instance.initialize.return_value = True
        mock_qmt_instance.place_order.return_value = 'qmt_order_123'
        mock_qmt_instance.get_orders.return_value = {
            'qmt_order_123': {
                'status': 'filled',
                'filled_volume': 100,
                'filled_price': 10.5
            }
        }
        mock_qmt_instance.get_account_info.return_value = {
            'total_asset': 100000,
            'available_cash': 50000
        }
        
        mock_risk_instance = Mock()
        mock_risk_instance.validate_order.return_value = {'allowed': True}
        
        # 设置执行器
        self.executor.trader_api = mock_qmt_instance
        self.executor.risk_manager = mock_risk_instance
        
        # 测试订单列表
        orders = [
            {
                'symbol': '000001',
                'action': 'buy',
                'volume': 100,
                'price': 10.5
            },
            {
                'symbol': '000002',
                'action': 'sell',
                'volume': 200,
                'price': 15.0
            }
        ]
        
        # 执行批量订单
        results = await self.executor.execute_batch_orders(orders)
        
        # 验证结果
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertEqual(result['status'], OrderStatus.FILLED.value)
            self.assertTrue(result['success'])
    
    async def test_get_order_status(self):
        """测试查询订单状态"""
        # 添加测试订单到活跃订单
        test_order = {
            'order_id': 'test_order_1',
            'symbol': '000001',
            'action': 'buy',
            'volume': 100,
            'status': OrderStatus.SUBMITTED.value
        }
        self.executor.active_orders['test_order_1'] = test_order
        
        # 查询订单状态
        status = await self.executor.get_order_status('test_order_1')
        
        # 验证结果
        self.assertIsNotNone(status)
        self.assertEqual(status['order_id'], 'test_order_1')
        self.assertEqual(status['status'], OrderStatus.SUBMITTED.value)
        
        # 查询不存在的订单
        status = await self.executor.get_order_status('non_existent')
        self.assertIsNone(status)
    
    @patch('strategies.xueqiu_follow.core.trade_executor.get_advanced_api')
    async def test_cancel_order(self, mock_get_api):
        """测试撤销订单"""
        # 设置mock
        mock_qmt_instance = AsyncMock()
        mock_qmt_instance.sync_cancel_order.return_value = True
        self.executor.trader_api = mock_qmt_instance
        
        # 添加测试订单
        test_order = {
            'order_id': 'test_order_1',
            'qmt_order_id': 'qmt_123',
            'symbol': '000001',
            'action': 'buy',
            'volume': 100,
            'status': OrderStatus.SUBMITTED.value
        }
        self.executor.active_orders['test_order_1'] = test_order
        
        # 撤销订单
        result = await self.executor.cancel_order('test_order_1')
        
        # 验证结果
        self.assertTrue(result)
        mock_qmt_instance.sync_cancel_order.assert_called_once()
        
        # 验证订单已从活跃订单中移除
        self.assertNotIn('test_order_1', self.executor.active_orders)
        
        # 验证订单已添加到历史记录
        self.assertEqual(len(self.executor.order_history), 1)
        self.assertEqual(self.executor.order_history[0]['order_id'], 'test_order_1')


def run_tests():
    """运行测试"""
    print("开始测试交易执行器...")
    
    # 运行同步测试
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTradeExecutor)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 运行异步测试
    async_suite = unittest.TestLoader().loadTestsFromTestCase(TestTradeExecutorAsync)
    async_result = runner.run(async_suite)
    
    # 汇总结果
    total_tests = result.testsRun + async_result.testsRun
    total_failures = len(result.failures) + len(async_result.failures)
    total_errors = len(result.errors) + len(async_result.errors)
    
    print(f"\n测试完成:")
    print(f"总测试数: {total_tests}")
    print(f"成功: {total_tests - total_failures - total_errors}")
    print(f"失败: {total_failures}")
    print(f"错误: {total_errors}")
    
    return total_failures + total_errors == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)