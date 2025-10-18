#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雪球跟单系统压力测试
"""

import unittest
import asyncio
import time
import sys
import os
import json
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from strategies.xueqiu_follow.core.config_manager import ConfigManager
from strategies.xueqiu_follow.core.strategy_engine import StrategyEngine
from strategies.xueqiu_follow.tests.simple_performance_monitor import SimplePerformanceMonitor


class TestStressLoad(unittest.IsolatedAsyncioTestCase):
    """压力测试类"""
    
    async def asyncSetUp(self):
        """测试前准备"""
        # 创建临时配置
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'stress_config.json')
        
        self.test_config = {
            'account': {
                'qmt_path': 'D:/test_qmt',
                'account_id': 'stress_test_account',
                'password': 'test_password'
            },
            'risk': {
                'max_position_ratio': 0.1,
                'stop_loss_ratio': 0.05,
                'max_total_exposure': 0.8
            },
            'xueqiu': {
                'cookies': 'test_cookies',
                'user_agent': 'test_user_agent',
                'rate_limit': 0.1  # 更快的速率限制用于压力测试
            },
            'strategy': {
                'follow_portfolios': ['ZH001', 'ZH002', 'ZH003'],
                'follow_ratios': [0.3, 0.2, 0.1],
                'min_trade_amount': 1000,
                'max_trade_amount': 50000
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_config, f, ensure_ascii=False, indent=2)
        
        self.config_manager = ConfigManager(self.config_file)
        self.strategy_engine = StrategyEngine(self.config_manager)
        self.performance_monitor = SimplePerformanceMonitor()
    
    async def asyncTearDown(self):
        """清理测试环境"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    async def test_high_frequency_data_collection(self):
        """测试高频数据收集压力"""
        print("\n开始高频数据收集压力测试...")
        
        # 启动性能监控
        self.performance_monitor.start_monitoring()
        
        async def mock_data_collection():
            """模拟数据收集任务"""
            await asyncio.sleep(0.01)  # 模拟网络延迟
            return {
                'portfolio_id': f'ZH{hash(asyncio.current_task()) % 1000:03d}',
                'changes': [
                    {
                        'symbol': f'{i:06d}',
                        'name': f'股票{i}',
                        'type': 'add' if i % 2 == 0 else 'remove',
                        'weight': 0.01 * (i % 10),
                        'timestamp': datetime.now()
                    }
                    for i in range(10)
                ]
            }
        
        # 创建大量并发任务
        tasks = []
        start_time = time.time()
        
        for i in range(200):  # 200个并发数据收集任务
            task = asyncio.create_task(mock_data_collection())
            tasks.append(task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 停止性能监控
        metrics = self.performance_monitor.stop_monitoring()
        
        # 验证结果
        successful_tasks = [r for r in results if not isinstance(r, Exception)]
        failed_tasks = [r for r in results if isinstance(r, Exception)]
        
        print(f"完成时间: {total_time:.2f}秒")
        print(f"成功任务: {len(successful_tasks)}")
        print(f"失败任务: {len(failed_tasks)}")
        print(f"平均CPU使用率: {metrics.get('avg_cpu_percent', 0):.2f}%")
        print(f"峰值内存使用: {metrics.get('peak_memory_mb', 0):.2f}MB")
        
        # 性能断言
        self.assertEqual(len(failed_tasks), 0, "不应该有任务失败")
        self.assertLess(total_time, 10.0, "200个任务应该在10秒内完成")
        self.assertLess(metrics.get('avg_cpu_percent', 100), 80, "平均CPU使用率应该低于80%")
    
    async def test_concurrent_strategy_execution(self):
        """测试并发策略执行压力"""
        print("\n开始并发策略执行压力测试...")
        
        # Mock外部依赖
        with patch('strategies.xueqiu_follow.core.strategy_engine.get_advanced_api') as mock_trader, \
             patch('strategies.xueqiu_follow.core.strategy_engine.RiskManager') as mock_risk:
            
            # 设置Mock
            mock_trader_instance = Mock()
            mock_trader_instance.connect.return_value = True
            mock_trader_instance.add_account.return_value = True
            mock_trader_instance.get_account_info.return_value = {
                'total_asset': 1000000,
                'available_cash': 500000
            }
            mock_trader_instance.get_positions_detailed.return_value = {}
            mock_trader.return_value = mock_trader_instance
            
            mock_risk_instance = Mock()
            mock_risk_instance.validate_order.return_value = {'allowed': True, 'reason': '通过'}
            mock_risk.return_value = mock_risk_instance
            
            self.strategy_engine.trader_api = mock_trader_instance
            
            # 启动性能监控
            self.performance_monitor.start_monitoring()
            
            async def execute_strategy_task(portfolio_id, task_id):
                """执行策略任务"""
                portfolio_changes = [
                    {
                        'symbol': f'{task_id:06d}',
                        'name': f'测试股票{task_id}',
                        'type': 'add',
                        'weight': 0.05,
                        'price': 10.0 + (task_id % 10),
                        'change_time': datetime.now()
                    }
                ]
                
                with patch.object(self.strategy_engine, '_load_current_positions', return_value=None), \
                     patch.object(self.strategy_engine, '_get_current_price', return_value=10.0):
                    
                    result = await self.strategy_engine.execute_strategy(portfolio_id, portfolio_changes)
                    return {'task_id': task_id, 'result': result}
            
            # 创建并发策略执行任务
            tasks = []
            start_time = time.time()
            
            for i in range(50):  # 50个并发策略执行
                portfolio_id = f'ZH{i % 3 + 1:03d}'  # 轮换使用3个组合
                task = asyncio.create_task(execute_strategy_task(portfolio_id, i))
                tasks.append(task)
            
            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # 停止性能监控
            metrics = self.performance_monitor.stop_monitoring()
            
            # 分析结果
            successful_tasks = [r for r in results if not isinstance(r, Exception)]
            failed_tasks = [r for r in results if isinstance(r, Exception)]
            
            print(f"策略执行完成时间: {total_time:.2f}秒")
            print(f"成功执行: {len(successful_tasks)}")
            print(f"执行失败: {len(failed_tasks)}")
            print(f"平均CPU使用率: {metrics.get('avg_cpu_percent', 0):.2f}%")
            print(f"峰值内存使用: {metrics.get('peak_memory_mb', 0):.2f}MB")
            
            # 性能断言
            self.assertEqual(len(failed_tasks), 0, "策略执行不应该失败")
            self.assertLess(total_time, 15.0, "50个策略执行应该在15秒内完成")
    
    async def test_memory_leak_detection(self):
        """测试内存泄漏检测"""
        print("\n开始内存泄漏检测测试...")
        
        import gc
        import psutil
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行大量操作
        for cycle in range(10):
            tasks = []
            
            # 创建临时对象
            for i in range(100):
                async def temp_task():
                    # 创建一些临时数据结构
                    data = {
                        'large_list': list(range(1000)),
                        'nested_dict': {f'key_{j}': f'value_{j}' for j in range(100)},
                        'timestamp': datetime.now()
                    }
                    await asyncio.sleep(0.001)
                    return len(data['large_list'])
                
                tasks.append(asyncio.create_task(temp_task()))
            
            # 等待任务完成
            await asyncio.gather(*tasks)
            
            # 强制垃圾回收
            gc.collect()
            
            # 检查内存使用
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_growth = current_memory - initial_memory
            
            print(f"周期 {cycle + 1}: 内存使用 {current_memory:.2f}MB (增长 {memory_growth:.2f}MB)")
            
            # 如果内存增长过多，可能存在内存泄漏
            if memory_growth > 100:  # 100MB阈值
                self.fail(f"检测到可能的内存泄漏: 内存增长 {memory_growth:.2f}MB")
        
        final_memory = process.memory_info().rss / 1024 / 1024
        total_growth = final_memory - initial_memory
        
        print(f"最终内存增长: {total_growth:.2f}MB")
        self.assertLess(total_growth, 50, "总内存增长应该小于50MB")
    
    async def test_database_connection_pool_stress(self):
        """测试数据库连接池压力"""
        print("\n开始数据库连接池压力测试...")
        
        # 模拟数据库操作
        connection_count = 0
        max_connections = 20
        
        async def mock_db_operation(operation_id):
            """模拟数据库操作"""
            nonlocal connection_count
            
            # 模拟获取连接
            if connection_count >= max_connections:
                raise Exception("连接池已满")
            
            connection_count += 1
            
            try:
                # 模拟数据库查询
                await asyncio.sleep(0.1)  # 模拟查询时间
                
                # 模拟数据处理
                result = {
                    'operation_id': operation_id,
                    'data': [{'id': i, 'value': f'data_{i}'} for i in range(10)],
                    'timestamp': datetime.now()
                }
                
                return result
            
            finally:
                # 释放连接
                connection_count -= 1
        
        # 创建大量并发数据库操作
        tasks = []
        start_time = time.time()
        
        for i in range(100):  # 100个并发数据库操作
            task = asyncio.create_task(mock_db_operation(i))
            tasks.append(task)
        
        # 等待所有操作完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 分析结果
        successful_ops = [r for r in results if not isinstance(r, Exception)]
        failed_ops = [r for r in results if isinstance(r, Exception)]
        
        print(f"数据库操作完成时间: {total_time:.2f}秒")
        print(f"成功操作: {len(successful_ops)}")
        print(f"失败操作: {len(failed_ops)}")
        print(f"最终连接数: {connection_count}")
        
        # 验证连接池管理
        self.assertEqual(connection_count, 0, "所有连接都应该被正确释放")
        self.assertLess(len(failed_ops), 10, "失败操作应该少于10个")


class TestSystemLimits(unittest.IsolatedAsyncioTestCase):
    """系统极限测试类"""
    
    async def test_maximum_portfolio_handling(self):
        """测试最大组合处理能力"""
        print("\n开始最大组合处理能力测试...")
        
        # 创建大量组合数据
        portfolios = []
        for i in range(100):  # 100个组合
            portfolio = {
                'code': f'ZH{i:03d}',
                'follow_ratio': 0.01,  # 每个组合1%权重
                'changes': [
                    {
                        'symbol': f'{j:06d}',
                        'name': f'股票{j}',
                        'type': 'add' if j % 2 == 0 else 'remove',
                        'weight': 0.001 * j,
                        'price': 10.0 + (j % 50),
                        'change_time': datetime.now()
                    }
                    for j in range(i, i + 10)  # 每个组合10只股票
                ]
            }
            portfolios.append(portfolio)
        
        # 测试处理时间
        start_time = time.time()
        
        # 模拟处理所有组合
        processed_count = 0
        for portfolio in portfolios:
            # 模拟组合处理逻辑
            await asyncio.sleep(0.001)  # 模拟处理时间
            processed_count += 1
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"处理 {len(portfolios)} 个组合用时: {processing_time:.2f}秒")
        print(f"平均每个组合处理时间: {processing_time/len(portfolios)*1000:.2f}毫秒")
        
        # 性能断言
        self.assertEqual(processed_count, 100, "应该处理所有组合")
        self.assertLess(processing_time, 5.0, "处理100个组合应该在5秒内完成")
    
    async def test_extreme_market_volatility_simulation(self):
        """测试极端市场波动模拟"""
        print("\n开始极端市场波动模拟测试...")
        
        # 模拟极端市场条件
        extreme_changes = []
        
        # 生成大幅波动数据
        for i in range(1000):  # 1000只股票同时大幅变动
            change = {
                'symbol': f'{i:06d}',
                'name': f'股票{i}',
                'type': 'update',
                'old_weight': 0.001,
                'new_weight': 0.001 * (1 + ((-1) ** i) * 0.5),  # ±50%变动
                'price_change': ((-1) ** i) * 0.1,  # ±10%价格变动
                'timestamp': datetime.now()
            }
            extreme_changes.append(change)
        
        # 测试系统响应时间
        start_time = time.time()
        
        # 模拟处理极端变化
        processed_changes = []
        for change in extreme_changes:
            # 模拟风险检查和处理
            if abs(change['price_change']) > 0.05:  # 5%阈值
                # 模拟风险控制逻辑
                await asyncio.sleep(0.0001)  # 模拟风险计算时间
            
            processed_changes.append(change)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"处理 {len(extreme_changes)} 个极端变化用时: {processing_time:.2f}秒")
        print(f"平均每个变化处理时间: {processing_time/len(extreme_changes)*1000:.3f}毫秒")
        
        # 验证处理能力
        self.assertEqual(len(processed_changes), 1000, "应该处理所有变化")
        self.assertLess(processing_time, 2.0, "处理1000个极端变化应该在2秒内完成")


def run_stress_tests():
    """运行压力测试"""
    print("=" * 60)
    print("开始雪球跟单系统压力测试")
    print("=" * 60)
    
    # 运行压力测试
    stress_suite = unittest.TestLoader().loadTestsFromTestCase(TestStressLoad)
    limits_suite = unittest.TestLoader().loadTestsFromTestCase(TestSystemLimits)
    
    runner = unittest.TextTestRunner(verbosity=2)
    
    print("\n1. 压力负载测试")
    print("-" * 40)
    stress_result = runner.run(stress_suite)
    
    print("\n2. 系统极限测试")
    print("-" * 40)
    limits_result = runner.run(limits_suite)
    
    # 汇总结果
    total_tests = stress_result.testsRun + limits_result.testsRun
    total_failures = len(stress_result.failures) + len(limits_result.failures)
    total_errors = len(stress_result.errors) + len(limits_result.errors)
    
    print("\n" + "=" * 60)
    print("压力测试结果汇总:")
    print(f"总测试数: {total_tests}")
    print(f"成功: {total_tests - total_failures - total_errors}")
    print(f"失败: {total_failures}")
    print(f"错误: {total_errors}")
    print("=" * 60)
    
    return total_failures + total_errors == 0


if __name__ == "__main__":
    success = run_stress_tests()
    sys.exit(0 if success else 1)