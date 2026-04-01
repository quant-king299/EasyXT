"""
因子分析模块

完整的因子分析工具链。

主要功能：
- IC/IR分析（信息系数、信息比率）
- 分组回测（10分组收益分析）
- 绩效评估（夏普比率、最大回撤等）
- 可视化工具（净值曲线、IC序列）

使用示例：
>>> from factors.analysis import ICAnalyzer, GroupBacktester
>>> ic_analyzer = ICAnalyzer(data_manager)
>>> ic_series = ic_analyzer.calculate_ic(factor_df, return_df)
"""

from .ic_analyzer import ICAnalyzer

from .group_backtest import (
    GroupBacktester,
    GroupBacktestResult
)

from .performance import PerformanceEvaluator

from .visualization import FactorVisualizer

__all__ = [
    'ICAnalyzer',
    'GroupBacktester',
    'GroupBacktestResult',
    'PerformanceEvaluator',
    'FactorVisualizer'
]
