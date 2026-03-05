# -*- coding: utf-8 -*-
"""
EasyXT通用回测框架

支持多种策略类型的回测：
- 选股策略（如小市值策略）
- 因子策略
- 自定义策略
"""

from .data_manager import DataManager
from .strategy_base import StrategyBase
from .engine import BacktestEngine, BacktestResult
from .performance import PerformanceAnalyzer
from .strategies.small_cap_strategy import SmallCapStrategy

__version__ = '1.0.0'

__all__ = [
    'DataManager',
    'StrategyBase',
    'BacktestEngine',
    'BacktestResult',
    'PerformanceAnalyzer',
    'SmallCapStrategy',
]
