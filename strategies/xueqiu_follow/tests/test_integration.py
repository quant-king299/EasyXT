#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雪球跟单系统集成测试
"""

import unittest
import asyncio
import sys
import os
import json
import tempfile
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from strategies.xueqiu_follow.core.config_manager import ConfigManager
from strategies.xueqiu_follow.core.strategy_engine import StrategyEngine
from strategies.xueqiu_follow.core.xueqiu_collector import XueqiuCollector
from strategies.xueqiu_follow.core.trade_executor import TradeExecutor
from strategies.xueqiu_follow.core.risk_manager import RiskManager


class TestSystemIntegration(unittest.IsolatedAsyncioTestCase):
    """系统集成测试类"""
    
    async def asyncSetUp(self):
        """异步测试前准备"""
        # 创建临时配置文件
        self.temp_dir = tempfile.mkdtemp()
        
        # 测试配置
        self.test_settings = {
            'account': {
                'qmt_path': 'D:/test_qmt',
                'account_id': 'test_account_123',
                'password': 'test_password'
            },
            'risk': {
                'max_position_ratio': 0.1,
                'stop_loss_ratio': 0.05,
                'max_total_exposure': 0.8,
                'blacklist': ['ST股票', '退市股票']
            },
            'monitoring': {
                'check_interval': 30,
                'retry_times': 3,
                'timeout': 10,
                'max_delay': 3
            },
            'logging': {
                'level': 'INFO',
                'file': 'logs/test.log',
                'max_size': '10MB',
                'backup_count': 5
            }
        }
        
        self.test_portfolios = {
            'portfolios': [
                {
                    'name': '测试组合',
                    'code': 'ZH001',
                    'follow_ratio': 0.4,
                    'enabled': True,
                    'description': '测试用组合'
                }
            ],
            'global_settings': {
                'total_follow_ratio': 0.4,
                'auto_start': False,
                'emergency_stop': False
            }
        }
        
        # 创建配置文件
        settings_file = os.path.join(self.temp_dir, 'settings.json')
        portfolios_file = os.path.join(self.temp_dir, 'portfolios.json')
        
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_settings, f, ensure_ascii=False, indent=2)
        
        with open(portfolios_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_portfolios, f, ensure_ascii=False, indent=2)
        
        # 初始化配置管理器
        self.config_manager = ConfigManager(self.temp_dir)
        
        # 强制设置测试配置
        self.config_manager._settings = self.test_settings
        self.config_manager._portfolios = self.test_portfolios
        
        # 初始化策略引擎
        self.strategy_engine = StrategyEngine(self.config_manager)
    
    async def asyncTearDown(self):
        """清理测试环境"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('strategies.xueqiu_follow.core.strategy_engine.XueqiuCollector')
    @patch('strategies.xueqiu_follow.core.strategy_engine.get_advanced_api')
    @patch('strategies.xueqiu_follow.core.strategy_engine.RiskManager')
    async def test_complete_trading_workflow(self, mock_risk_manager, mock_trader, mock_collector):
        """测试完整的交易工作流程"""
        # 设置Mock对象
        mock_collector_instance = AsyncMock()
        mock_collector_instance.get_portfolio_changes.return_value = [
            {
                'symbol': '000001',
                'name': '平安银行',
                'type': 'add',
                'weight': 0.1,
                'price': 10.50,
                'change_time': datetime.now()
            }
        ]
        mock_collector.return_value = mock_collector_instance
        
        mock_trader_instance = Mock()
        mock_trader_instance.connect.return_value = True
        mock_trader_instance.add_account.return_value = True
        mock_trader_instance._mock_name = 'MockTrader'
        mock_trader_instance.get_account_info.return_value = {
            'total_asset': 100000,
            'available_cash': 50000,
            'market_value': 50000
        }
        mock_trader_instance.get_positions_detailed.return_value = {}
        mock_trader.return_value = mock_trader_instance
        
        mock_risk_instance = Mock()
        mock_risk_instance.validate_order.return_value = {'allowed': True, 'reason': '通过'}
        mock_risk_manager.return_value = mock_risk_instance
        
        # 设置策略引擎
        self.strategy_engine.trader_api = mock_trader_instance
        
        # Mock方法
        with patch.object(self.strategy_engine, '_load_current_positions', return_value=None), \
             patch.object(self.strategy_engine, '_get_current_price', return_value=10.50):
            
            # 1. 初始化系统
            init_result = await self.strategy_engine.initialize()
            self.assertTrue(init_result, "系统初始化应该成功")
            
            # 2. 执行策略
            portfolio_changes = await mock_collector_instance.get_portfolio_changes('ZH001')
            result = await self.strategy_engine.execute_strategy('ZH001', portfolio_changes)
            
            # 3. 验证结果
            self.assertTrue(result, "策略执行应该成功")
    
    async def test_risk_management_integration(self):
        """测试风险管理集成"""
        # 创建风险管理器
        risk_config = self.test_settings['risk']
        risk_manager = RiskManager(risk_config)
        
        # 模拟账户信息
        account_info = {
            'total_asset': 100000,
            'available_cash': 30000,
            'market_value': 70000
        }
        
        # 模拟当前持仓
        current_positions = {
            '000001': {
                'volume': 1000,
                'value': 15000,
                'weight': 0.15
            }
        }
        
        # 测试订单验证
        test_order = {
            'symbol': '000002',
            'action': 'buy',
            'volume': 500,
            'price': 20.0,
            'amount': 10000
        }
        
        validation_result = risk_manager.validate_order(
            'buy', '000002', 500, 20.0, current_positions, account_info
        )
        
        # 验证风险检查结果
        self.assertIn('allowed', validation_result)
        self.assertIn('reason', validation_result)
    
    async def test_configuration_management_integration(self):
        """测试配置管理集成"""
        # 测试配置读取
        qmt_path = self.config_manager.get_setting('account.qmt_path')
        self.assertEqual(qmt_path, 'D:/test_qmt')
        
        # 测试配置修改
        self.config_manager.set_setting('account.qmt_path', 'D:/new_qmt', save=False)
        new_qmt_path = self.config_manager.get_setting('account.qmt_path')
        self.assertEqual(new_qmt_path, 'D:/new_qmt')
        
        # 测试组合配置
        portfolios = self.config_manager.get_portfolios()
        self.assertEqual(len(portfolios), 1)
        self.assertEqual(portfolios[0]['code'], 'ZH001')
        
        # 验证配置有效性
        errors = self.config_manager.validate_settings()
        # 忽略QMT路径不存在的错误（测试环境）
        errors = [e for e in errors if 'QMT路径不存在' not in e]
        self.assertEqual(len(errors), 0, f"配置验证失败: {errors}")
    
    async def test_performance_under_load(self):
        """测试系统负载性能"""
        # 模拟并发任务
        tasks = []
        
        async def mock_trading_task():
            """模拟交易任务"""
            await asyncio.sleep(0.01)  # 模拟处理时间
            return {'status': 'success'}
        
        # 创建50个并发任务
        for i in range(50):
            task = asyncio.create_task(mock_trading_task())
            tasks.append(task)
        
        # 记录开始时间
        start_time = datetime.now()
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 记录结束时间
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # 验证性能指标
        self.assertEqual(len(results), 50, "所有任务都应该完成")
        self.assertLess(processing_time, 3.0, "处理时间应该在3秒内")
        
        # 验证没有异常
        exceptions = [r for r in results if isinstance(r, Exception)]
        self.assertEqual(len(exceptions), 0, "不应该有异常发生")
    
    async def test_multi_portfolio_integration(self):
        """测试多组合集成"""
        # 模拟多个组合的变化
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
        with patch.object(self.strategy_engine, '_get_account_value', return_value=100000):
            merged_positions = self.strategy_engine.merge_multiple_portfolios(portfolio_list)
        
        # 验证合并结果
        self.assertIn('000001', merged_positions)
        
        # 验证权重合并: 100000*0.3*0.1 + 100000*0.2*0.05 = 3000 + 1000 = 4000
        self.assertEqual(merged_positions['000001']['target_value'], 4000)


class TestSystemResilience(unittest.IsolatedAsyncioTestCase):
    """系统韧性测试类"""
    
    async def test_error_handling_integration(self):
        """测试错误处理集成"""
        # 测试配置文件不存在的情况
        with self.assertRaises(Exception):
            ConfigManager('/nonexistent/config.json')
    
    async def test_network_failure_recovery(self):
        """测试网络故障恢复"""
        collector = XueqiuCollector()
        
        # 模拟网络故障
        with patch('strategies.xueqiu_follow.core.xueqiu_collector.aiohttp.ClientSession') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session_instance.get.side_effect = Exception("网络超时")
            mock_session.return_value = mock_session_instance
            
            await collector.initialize()
            
            # 测试网络故障处理
            result = await collector.get_portfolio_info('ZH001')
            self.assertIsNone(result, "网络故障时应该返回None")


def run_integration_tests():
    """运行集成测试"""
    print("开始系统集成测试...")
    
    # 运行集成测试
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSystemIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 运行韧性测试
    resilience_suite = unittest.TestLoader().loadTestsFromTestCase(TestSystemResilience)
    resilience_result = runner.run(resilience_suite)
    
    # 汇总结果
    total_tests = result.testsRun + resilience_result.testsRun
    total_failures = len(result.failures) + len(resilience_result.failures)
    total_errors = len(result.errors) + len(resilience_result.errors)
    
    print(f"\n集成测试完成:")
    print(f"总测试数: {total_tests}")
    print(f"成功: {total_tests - total_failures - total_errors}")
    print(f"失败: {total_failures}")
    print(f"错误: {total_errors}")
    
    return total_failures + total_errors == 0


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)