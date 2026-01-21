"""
工作流节点模块
导出所有节点类型
"""

from .base import BaseNode, DataNode, AnalysisNode
from .data_nodes import DataLoaderNode, FactorCalculationNode
from .analysis_nodes import (
    ICAnalysisNode,
    BacktestNode,
    PerformanceAnalysisNode,
    RiskAnalysisNode,
    SignalAnalysisNode,
    FactorCorrelationNode  # 新增的因子相关性分析节点
)

__all__ = [
    # 基础节点
    'BaseNode',
    'DataNode',
    'AnalysisNode',

    # 数据节点
    'DataLoaderNode',
    'FactorCalculationNode',

    # 分析节点
    'ICAnalysisNode',
    'BacktestNode',
    'PerformanceAnalysisNode',
    'RiskAnalysisNode',
    'SignalAnalysisNode',
    'FactorCorrelationNode',  # 新增
]
