"""
风险管理模块测试
"""

import asyncio
import pytest
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from strategies.xueqiu_follow.core.risk_manager import RiskManager, RiskLevel


class TestRiskManager:
    """风险管理器测试类"""
    
    def test_initialization(self):
        """测试初始化"""
        risk_manager = RiskManager()
        
        assert risk_manager.max_position_ratio == 0.1
        assert risk_manager.stop_loss_ratio == 0.05
        assert risk_manager.max_total_exposure == 0.8
        assert risk_manager.emergency_stop is False
    
    def test_symbol_validation(self):
        """测试股票代码验证"""
        risk_manager = RiskManager()
        
        # 测试有效代码
        valid_symbols = ['SH600036', 'SZ000001', '000001', '600036']
        for symbol in valid_symbols:
            allowed, reason = risk_manager.check_symbol_allowed(symbol)
            assert allowed, f"应该允许 {symbol}: {reason}"
        
        # 测试无效代码
        invalid_symbols = ['ABC123', '12345', 'SH12345']
        for symbol in invalid_symbols:
            allowed, reason = risk_manager.check_symbol_allowed(symbol)
            assert not allowed, f"不应该允许 {symbol}"
    
    def test_blacklist_functionality(self):
        """测试黑名单功能"""
        risk_manager = RiskManager()
        
        # 添加到黑名单
        risk_manager.add_to_blacklist('SZ000001')
        
        # 检查黑名单股票
        allowed, reason = risk_manager.check_symbol_allowed('SZ000001')
        assert not allowed
        assert '黑名单' in reason
        
        # 移除黑名单
        risk_manager.remove_from_blacklist('SZ000001')
        allowed, reason = risk_manager.check_symbol_allowed('SZ000001')
        assert allowed
    
    def test_position_size_check(self):
        """测试仓位大小检查"""
        risk_manager = RiskManager()
        
        # 测试正常仓位
        current_positions = {
            'SH600036': {'weight': 0.05}
        }
        
        allowed, reason = risk_manager.check_position_size('SZ000001', 0.08, current_positions)
        assert allowed, f"正常仓位应该允许: {reason}"
        
        # 测试超限仓位
        allowed, reason = risk_manager.check_position_size('SZ000001', 0.15, current_positions)
        assert not allowed, "超限仓位不应该允许"
        
        # 测试总仓位超限
        large_positions = {
            'SH600036': {'weight': 0.4},
            'SH600519': {'weight': 0.3}
        }
        
        allowed, reason = risk_manager.check_position_size('SZ000001', 0.2, large_positions)
        assert not allowed, "总仓位超限不应该允许"
    
    def test_stop_loss_check(self):
        """测试止损检查"""
        risk_manager = RiskManager()
        
        # 模拟持仓数据
        positions = {
            'SZ000001': {
                'open_price': 10.0,
                'current_price': 9.0,  # 下跌10%
                'volume': 1000
            },
            'SH600036': {
                'open_price': 20.0,
                'current_price': 19.5,  # 下跌2.5%
                'volume': 500
            }
        }
        
        stop_loss_signals = risk_manager.check_stop_loss(positions)
        
        # 应该有一个止损信号（SZ000001下跌10% > 5%止损线）
        assert len(stop_loss_signals) == 1
        assert stop_loss_signals[0]['symbol'] == 'SZ000001'
        assert stop_loss_signals[0]['action'] == 'sell'
        assert stop_loss_signals[0]['reason'] == 'stop_loss'
    
    def test_daily_loss_limit(self):
        """测试单日亏损限制"""
        risk_manager = RiskManager()
        
        # 测试正常情况
        account_info = {
            'total_asset': 100000,
            'daily_pnl': -1000  # 亏损1%
        }
        
        allowed, reason = risk_manager.check_daily_loss_limit(account_info)
        assert allowed, "正常亏损应该允许"
        
        # 测试超限情况
        account_info['daily_pnl'] = -3000  # 亏损3% > 2%限制
        
        allowed, reason = risk_manager.check_daily_loss_limit(account_info)
        assert not allowed, "超限亏损不应该允许"
    
    def test_order_validation(self):
        """测试订单验证"""
        risk_manager = RiskManager()
        
        # 模拟数据
        current_positions = {}
        account_info = {
            'total_asset': 100000,
            'cash': 50000,
            'daily_pnl': -500
        }
        
        # 测试正常买入订单
        allowed, reason, risk_level = risk_manager.validate_order(
            'SZ000001', 'buy', 100, 10.0, current_positions, account_info
        )
        assert allowed, f"正常订单应该允许: {reason}"
        assert risk_level == RiskLevel.LOW
        
        # 测试资金不足
        allowed, reason, risk_level = risk_manager.validate_order(
            'SZ000001', 'buy', 10000, 10.0, current_positions, account_info
        )
        assert not allowed, "资金不足订单不应该允许"
        assert '资金不足' in reason
    
    def test_emergency_stop(self):
        """测试紧急停止"""
        risk_manager = RiskManager()
        
        # 设置紧急停止
        risk_manager.set_emergency_stop("测试紧急停止")
        assert risk_manager.emergency_stop is True
        
        # 验证紧急停止时订单被拒绝
        allowed, reason, risk_level = risk_manager.validate_order(
            'SZ000001', 'buy', 100, 10.0, {}, {}
        )
        assert not allowed
        assert risk_level == RiskLevel.CRITICAL
        
        # 清除紧急停止
        risk_manager.clear_emergency_stop()
        assert risk_manager.emergency_stop is False
    
    def test_position_risk_calculation(self):
        """测试持仓风险计算"""
        risk_manager = RiskManager()
        
        # 模拟持仓
        positions = {
            'SZ000001': {'market_value': 30000},
            'SH600036': {'market_value': 20000},
            'SH600519': {'market_value': 10000}
        }
        
        risk_metrics = risk_manager.calculate_position_risk(positions)
        
        assert risk_metrics['total_positions'] == 3
        assert abs(risk_metrics['total_exposure'] - 1.0) < 0.01  # 总仓位100%
        assert abs(risk_metrics['max_single_position'] - 0.5) < 0.01  # 最大单仓50%
        assert risk_metrics['risk_level'] == RiskLevel.MEDIUM  # 应该是中等风险
    
    def test_risk_report_generation(self):
        """测试风险报告生成"""
        risk_manager = RiskManager()
        
        # 模拟数据
        positions = {
            'SZ000001': {
                'market_value': 15000,
                'open_price': 10.0,
                'current_price': 9.5,
                'volume': 1500
            }
        }
        
        account_info = {
            'total_asset': 100000,
            'cash': 50000,
            'market_value': 50000,
            'daily_pnl': -800
        }
        
        report = risk_manager.generate_risk_report(positions, account_info)
        
        assert 'timestamp' in report
        assert 'account_info' in report
        assert 'position_risk' in report
        assert 'stop_loss_signals' in report
        assert 'overall_risk_level' in report
        
        # 检查账户信息
        assert report['account_info']['total_asset'] == 100000
        
        # 检查持仓风险
        assert report['position_risk']['total_positions'] == 1


async def run_manual_test():
    """手动测试函数"""
    print("开始风险管理模块测试...")
    
    try:
        # 创建风险管理器
        print("1. 创建风险管理器...")
        risk_manager = RiskManager()
        print(f"   最大单仓比例: {risk_manager.max_position_ratio:.1%}")
        print(f"   止损比例: {risk_manager.stop_loss_ratio:.1%}")
        print(f"   最大总仓位: {risk_manager.max_total_exposure:.1%}")
        
        # 测试股票代码验证
        print("2. 测试股票代码验证...")
        test_symbols = ['SH600036', 'SZ000001', 'ABC123', '000001']
        for symbol in test_symbols:
            allowed, reason = risk_manager.check_symbol_allowed(symbol)
            print(f"   {symbol}: {'✅' if allowed else '❌'} {reason}")
        
        # 测试仓位检查
        print("3. 测试仓位检查...")
        current_positions = {'SH600036': {'weight': 0.05}}
        
        test_cases = [
            ('SZ000001', 0.08, "正常仓位"),
            ('SZ000002', 0.15, "超限仓位"),
        ]
        
        for symbol, weight, desc in test_cases:
            allowed, reason = risk_manager.check_position_size(symbol, weight, current_positions)
            print(f"   {desc} {symbol} {weight:.1%}: {'✅' if allowed else '❌'} {reason}")
        
        # 测试止损检查
        print("4. 测试止损检查...")
        positions = {
            'SZ000001': {
                'open_price': 10.0,
                'current_price': 9.0,
                'volume': 1000
            },
            'SH600036': {
                'open_price': 20.0,
                'current_price': 19.5,
                'volume': 500
            }
        }
        
        stop_loss_signals = risk_manager.check_stop_loss(positions)
        print(f"   检测到 {len(stop_loss_signals)} 个止损信号")
        for signal in stop_loss_signals:
            print(f"   止损: {signal['symbol']} 亏损 {signal['pnl_ratio']:.1%}")
        
        # 测试风险报告
        print("5. 生成风险报告...")
        account_info = {
            'total_asset': 100000,
            'cash': 50000,
            'market_value': 50000,
            'daily_pnl': -1000
        }
        
        report = risk_manager.generate_risk_report(positions, account_info)
        print(f"   整体风险等级: {report['overall_risk_level']}")
        print(f"   持仓数量: {report['position_risk']['total_positions']}")
        print(f"   止损信号: {len(report['stop_loss_signals'])}")
        
        print("✅ 所有测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")


if __name__ == "__main__":
    asyncio.run(run_manual_test())