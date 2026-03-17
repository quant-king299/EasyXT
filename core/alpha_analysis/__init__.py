"""
101因子分析模块
提供IC/IR测试、因子相关性分析、分层回测等功能
"""

from .ic_ir_analysis import ICIRAnalyzer
from .factor_correlation import FactorCorrelationAnalyzer
from .layered_backtest import LayeredBacktester

# 向后兼容的别名
ICAnalyzer = ICIRAnalyzer

__all__ = [
    'ICIRAnalyzer',
    'ICAnalyzer',  # 向后兼容别名
    'FactorCorrelationAnalyzer',
    'LayeredBacktester'
]
