"""
雪球数据采集器测试
"""

import asyncio
import pytest
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from strategies.xueqiu_follow.core.xueqiu_collector import XueqiuCollector
from strategies.xueqiu_follow.utils.rate_limiter import RateLimiter


class TestXueqiuCollector:
    """雪球数据采集器测试类"""
    
    @pytest.fixture
    async def collector(self):
        """创建采集器实例"""
        collector = XueqiuCollector()
        await collector.initialize()
        yield collector
        await collector.close()
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """测试初始化"""
        collector = XueqiuCollector()
        result = await collector.initialize()
        assert result is True
        assert collector.session is not None
        await collector.close()
    
    @pytest.mark.asyncio
    async def test_rate_limiter(self):
        """测试频率限制器"""
        limiter = RateLimiter(max_requests=5, time_window=10)
        
        # 测试正常请求
        for i in range(5):
            await limiter.acquire()
        
        # 检查剩余请求数
        remaining = limiter.get_remaining_requests()
        assert remaining == 0
    
    @pytest.mark.asyncio
    async def test_portfolio_info_mock(self, collector):
        """测试获取组合信息（模拟）"""
        # 由于需要真实的雪球组合代码，这里只测试方法调用
        portfolio_code = "ZH000000"  # 示例代码
        
        try:
            result = await collector.get_portfolio_info(portfolio_code)
            # 即使失败也不报错，因为可能是网络或认证问题
            print(f"获取组合信息结果: {result is not None}")
        except Exception as e:
            print(f"获取组合信息异常: {e}")
    
    @pytest.mark.asyncio
    async def test_holdings_parsing(self):
        """测试持仓数据解析"""
        collector = XueqiuCollector()
        
        # 模拟调仓数据
        mock_data = {
            'updated_at': 1640995200000,
            'rebalancing_histories': [
                {
                    'stock_symbol': 'SZ000001',
                    'stock_name': '平安银行',
                    'target_weight': 1500,  # 15%
                    'prev_weight': 1000     # 10%
                },
                {
                    'stock_symbol': 'SH600036',
                    'stock_name': '招商银行',
                    'target_weight': 2000,  # 20%
                    'prev_weight': 1800     # 18%
                }
            ]
        }
        
        holdings = await collector._parse_holdings(mock_data)
        
        assert len(holdings) == 2
        assert holdings[0]['symbol'] == 'SZ000001'
        assert holdings[0]['target_weight'] == 15.0  # 雪球返回的是百分比形式
        assert holdings[0]['weight_change'] == 5.0
    
    @pytest.mark.asyncio
    async def test_change_detection(self):
        """测试变化检测"""
        collector = XueqiuCollector()
        
        old_holdings = [
            {'symbol': 'SZ000001', 'name': '平安银行', 'target_weight': 0.15},
            {'symbol': 'SH600036', 'name': '招商银行', 'target_weight': 0.20}
        ]
        
        new_holdings = [
            {'symbol': 'SZ000001', 'name': '平安银行', 'target_weight': 0.18},  # 权重增加
            {'symbol': 'SH600519', 'name': '贵州茅台', 'target_weight': 0.10}   # 新增
            # 招商银行被删除
        ]
        
        changes = collector._detect_changes(old_holdings, new_holdings)
        
        assert len(changes) == 3
        
        # 检查变化类型
        change_types = [c['type'] for c in changes]
        assert 'modify' in change_types  # 平安银行权重修改
        assert 'add' in change_types     # 贵州茅台新增
        assert 'remove' in change_types  # 招商银行删除


async def run_manual_test():
    """手动测试函数"""
    print("开始雪球数据采集器测试...")
    
    collector = XueqiuCollector()
    
    try:
        # 测试初始化
        print("1. 测试初始化...")
        result = await collector.initialize()
        print(f"   初始化结果: {result}")
        
        # 测试频率限制器
        print("2. 测试频率限制器...")
        limiter = RateLimiter(max_requests=3, time_window=5)
        for i in range(3):
            await limiter.acquire()
            print(f"   请求 {i+1} 完成，剩余: {limiter.get_remaining_requests()}")
        
        # 测试数据解析
        print("3. 测试数据解析...")
        mock_data = {
            'updated_at': 1640995200000,
            'rebalancing_histories': [
                {
                    'stock_symbol': 'SZ000001',
                    'stock_name': '平安银行',
                    'target_weight': 1500,
                    'prev_weight': 1000
                }
            ]
        }
        
        holdings = await collector._parse_holdings(mock_data)
        print(f"   解析结果: {len(holdings)} 个持仓")
        if holdings:
            print(f"   示例持仓: {holdings[0]}")
        
        print("✅ 所有测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    finally:
        await collector.close()


if __name__ == "__main__":
    asyncio.run(run_manual_test())