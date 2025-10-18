#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略引擎测试
"""

import unittest
import asyncio
import sys
import os
from unittest.mock import Mock, patch, AsyncMock

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from strategies.xueqiu_follow.core.strategy_engine import StrategyEngine


class TestStrategyEngine(unittest.TestCase):
    """策略引擎测试类"""
    
    def setUp(self):
        """测试前准备"""
        from unittest.mock import Mock
        
        # 创建mock配置管理器
        self.mock_config_manager = Mock()
        self.mock_config_manager.get_setting.side_effect = lambda key, default=None: {
            'account.qmt_path': 'D:/test_qmt',
            'account.account_id': 'test_account',
            'account.password': 'test_password',
            'risk.max_position_ratio': 0.1,
            'risk.stop_loss_ratio': 0.05,
            'risk.max_total_exposure': 0.8,
            'risk.blacklist': []
        }.get(key, default)
        
        self.engine = StrategyEngine(self.mock_config_manager)
    
    def test_calculate_target_positions(self):
        """测试目标仓位计算"""
        portfolio_changes = [
            {
                'symbol': '000001',
                'name': '平安银行',
                'type': 'add',
                'weight': 0.1
            },
            {
                'symbol': '000002',
                'name': '万科A',
                'type': 'modify',
                'old_weight': 0.05,
                'new_weight': 0.08
            },
            {
                'symbol': '000003',
                'name': '中国建筑',
                'type': 'remove',
                'weight': 0
            }
        ]
        
        follow_ratio = 0.5
        account_value = 100000
        
        target_positions = self.engine.calculate_target_positions(
            portfolio_changes, follow_ratio, account_value
        )
        
        # 验证结果
        self.assertIn('000001', target_positions)
        self.assertIn('000002', target_positions)
        self.assertIn('000003', target_positions)
        
        # 验证新增持仓
        self.assertEqual(target_positions['000001']['action'], 'buy')
        self.assertEqual(target_positions['000001']['target_value'], 5000)  # 100000 * 0.5 * 0.1
        
        # 验证调整持仓
        self.assertEqual(target_positions['000002']['action'], 'buy')
        self.assertEqual(target_positions['000002']['target_value'], 4000)  # 100000 * 0.5 * 0.08
        
        # 验证清仓
        self.assertEqual(target_positions['000003']['action'], 'sell')
        self.assertEqual(target_positions['000003']['target_value'], 0)
    
    def test_generate_trade_orders(self):
        """测试交易指令生成"""
        target_positions = {
            '000001': {
                'action': 'buy',
                'target_value': 5000,
                'weight': 0.1,
                'reason': '新增持仓'
            },
            '000002': {
                'action': 'sell',
                'target_value': 0,
                'weight': 0,
                'reason': '清仓'
            }
        }
        
        current_positions = {
            '000002': {
                'volume': 1000,
                'value': 3000
            }
        }
        
        # Mock价格获取
        with patch.object(self.engine, '_get_current_price', return_value=10.0):
            orders = self.engine.generate_trade_orders(target_positions, current_positions)
        
        # 验证结果
        self.assertEqual(len(orders), 2)
        
        # 验证买入指令
        buy_order = next((o for o in orders if o['action'] == 'buy'), None)
        self.assertIsNotNone(buy_order)
        self.assertEqual(buy_order['symbol'], '000001')
        self.assertEqual(buy_order['volume'], 500)  # 5000 / 10.0 / 100 * 100
        
        # 验证卖出指令
        sell_order = next((o for o in orders if o['action'] == 'sell'), None)
        self.assertIsNotNone(sell_order)
        self.assertEqual(sell_order['symbol'], '000002')
        self.assertEqual(sell_order['volume'], 1000)
    
    def test_merge_multiple_portfolios(self):
        """测试多组合合并"""
        portfolio_list = [
            {
                'code': 'ZH001',
                'follow_ratio': 0.3,
                'changes': [
                    {
                        'symbol': '000001',
                        'name': '平安银行',
                        'type': 'add',
                        'weight': 0.1
                    }
                ]
            },
            {
                'code': 'ZH002',
                'follow_ratio': 0.2,
                'changes': [
                    {
                        'symbol': '000001',
                        'name': '平安银行',
                        'type': 'add',
                        'weight': 0.05
                    }
                ]
            }
        ]
        
        # Mock账户价值获取
        with patch.object(self.engine, '_get_account_value', return_value=100000):
            merged_positions = self.engine.merge_multiple_portfolios(portfolio_list)
        
        # 验证结果
        self.assertIn('000001', merged_positions)
        # 应该合并两个组合的目标价值: 100000*0.3*0.1 + 100000*0.2*0.05 = 3000 + 1000 = 4000
        self.assertEqual(merged_positions['000001']['target_value'], 4000)
    
    @patch('strategies.xueqiu_follow.core.strategy_engine.RiskManager')
    def test_validate_trade_orders(self, mock_risk_manager):
        """测试交易指令验证"""
        # 设置风险管理器mock
        mock_risk_instance = Mock()
        mock_risk_manager.return_value = mock_risk_instance
        mock_risk_instance.check_trade_risk.return_value = {'allowed': True}
        
        # 重新初始化引擎以使用mock
        self.engine.risk_manager = mock_risk_instance
        
        orders = [
            {
                'symbol': '000001',
                'action': 'buy',
                'volume': 1000,
                'price': 10.0,
                'reason': '测试买入'
            }
        ]
        
        valid_orders = self.engine.validate_trade_orders(orders)
        
        # 验证结果
        self.assertEqual(len(valid_orders), 1)
        self.assertEqual(valid_orders[0]['symbol'], '000001')
        
        # 验证风险检查被调用
        mock_risk_instance.check_trade_risk.assert_called_once()


class TestStrategyEngineAsync(unittest.IsolatedAsyncioTestCase):
    """策略引擎异步测试类"""
    
    async def asyncSetUp(self):
        """异步测试前准备"""
        from unittest.mock import Mock
        
        # 创建mock配置管理器
        self.mock_config_manager = Mock()
        self.mock_config_manager.get_setting.side_effect = lambda key, default=None: {
            'account.qmt_path': 'D:/test_qmt',
            'account.account_id': 'test_account',
            'account.password': 'test_password',
            'risk.max_position_ratio': 0.1,
            'risk.stop_loss_ratio': 0.05,
            'risk.max_total_exposure': 0.8,
            'risk.blacklist': []
        }.get(key, default)
        
        self.engine = StrategyEngine(self.mock_config_manager)
    
    @patch('strategies.xueqiu_follow.core.strategy_engine.XueqiuCollector')
    @patch('strategies.xueqiu_follow.core.strategy_engine.get_advanced_api')
    @patch('strategies.xueqiu_follow.core.strategy_engine.RiskManager')
    async def test_initialize(self, mock_risk_manager, mock_trader, mock_collector):
        """测试初始化"""
        # 设置mocks
        mock_collector_instance = AsyncMock()
        mock_collector.return_value = mock_collector_instance
        
        mock_trader_instance = Mock()
        mock_trader_instance.connect.return_value = True
        mock_trader_instance.add_account.return_value = True
        mock_trader_instance._mock_name = 'MockTrader'  # 标记为Mock对象
        mock_trader.return_value = mock_trader_instance
        
        mock_risk_instance = Mock()
        mock_risk_manager.return_value = mock_risk_instance
        
        # 直接设置Mock对象到引擎中，避免初始化时的连接问题
        self.engine.trader_api = mock_trader_instance
        
        # Mock _load_current_positions方法
        with patch.object(self.engine, '_load_current_positions', return_value=None):
            # 执行初始化
            result = await self.engine.initialize()
        
        # 验证结果
        self.assertTrue(result)
        mock_collector_instance.initialize.assert_called_once()
    
    async def test_execute_strategy(self):
        """测试策略执行"""
        # 设置mock交易接口
        mock_trader_instance = Mock()
        mock_trader_instance.execute_orders.return_value = [
            {'status': 'success', 'symbol': '000001', 'action': 'buy', 'volume': 1000}
        ]
        self.engine.trader_api = mock_trader_instance
        
        # 设置风险管理器mock
        mock_risk_manager = Mock()
        mock_risk_manager.validate_order.return_value = (True, "通过", "low")
        self.engine.risk_manager = mock_risk_manager
        
        # 设置当前持仓
        self.engine.current_positions = {}
        
        # Mock方法
        with patch.object(self.engine, '_get_account_value', return_value=100000), \
             patch.object(self.engine, '_get_current_price', return_value=10.0), \
             patch.object(self.engine, '_get_account_info', return_value={'total_asset': 100000, 'cash': 50000}):
            
            changes = [
                {
                    'symbol': '000001',
                    'name': '平安银行',
                    'type': 'add',
                    'weight': 0.1
                }
            ]
            
            # 执行策略
            result = await self.engine.execute_strategy('ZH001', changes, follow_ratio=0.5)
        
        # 验证结果
        self.assertTrue(result)


def run_tests():
    """运行测试"""
    print("开始测试策略引擎...")
    
    # 运行同步测试
    suite = unittest.TestLoader().loadTestsFromTestCase(TestStrategyEngine)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 运行异步测试
    async_suite = unittest.TestLoader().loadTestsFromTestCase(TestStrategyEngineAsync)
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