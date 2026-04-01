"""
工作流节点模块
导出所有节点类型
"""

from .base import BaseNode, DataNode, AnalysisNode, TransformNode

# 数据节点
try:
    from .data_nodes import DataLoaderNode
    _data_loader_available = True
except ImportError:
    _data_loader_available = False

# 分析节点
try:
    from .analysis_nodes import (
        ICAnalysisNode,
        BacktestNode,
        PerformanceAnalysisNode,
        RiskAnalysisNode,
        SignalAnalysisNode,
        FactorCorrelationNode
    )
    _analysis_nodes_available = True
except ImportError:
    _analysis_nodes_available = False

# 特质波动率节点
try:
    from .specific_volatility_nodes import (
        SpecificVolatilityNode,
        MultiWindowSpecificVolatilityNode,
        SpecificVolatilityFactorNode
    )
    _spec_vol_nodes_available = True
except ImportError:
    _spec_vol_nodes_available = False

# 因子节点
try:
    from .factor_nodes import (
        FactorCalculatorNode,
        FactorCombinationNode,
        FactorProcessingNode
    )
    _factor_nodes_available = True
except ImportError:
    _factor_nodes_available = False

# 分组回测节点
try:
    from .group_backtest_nodes import (
        GroupBacktestNode,
        GroupBacktestWithVisualizationNode,
        GroupBacktestReportNode
    )
    _group_backtest_nodes_available = True
except ImportError:
    _group_backtest_nodes_available = False

# 构建导出列表
__all__ = [
    # 基础节点
    'BaseNode',
    'DataNode',
    'AnalysisNode',
    'TransformNode',
]

# 动态添加可用模块
if _data_loader_available:
    __all__.append('DataLoaderNode')

if _analysis_nodes_available:
    __all__.extend([
        'ICAnalysisNode',
        'BacktestNode',
        'PerformanceAnalysisNode',
        'RiskAnalysisNode',
        'SignalAnalysisNode',
        'FactorCorrelationNode',
    ])

if _spec_vol_nodes_available:
    __all__.extend([
        'SpecificVolatilityNode',
        'MultiWindowSpecificVolatilityNode',
        'SpecificVolatilityFactorNode',
    ])

if _factor_nodes_available:
    __all__.extend([
        'FactorCalculatorNode',
        'FactorCombinationNode',
        'FactorProcessingNode',
    ])

if _group_backtest_nodes_available:
    __all__.extend([
        'GroupBacktestNode',
        'GroupBacktestWithVisualizationNode',
        'GroupBacktestReportNode',
    ])
