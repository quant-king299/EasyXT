# -*- coding: utf-8 -*-
"""
EasyXT 统一回测框架

支持多种策略类型的回测：
- 技术指标策略：双均线、RSI、MACD等
- 选股策略：小市值、因子策略等
- 网格策略：固定网格、自适应网格等
"""

# 核心模块
from .core import BacktestCore
from core.data_manager import HybridDataManager as DataManager

# 策略基类
from .strategy_base import StrategyBase, FactorStrategyBase

# 回测引擎
from .enhanced_backtest_engine import EnhancedBacktestEngine

# 性能分析
from .performance import PerformanceAnalyzer

# API
from .api import (
    GridBacktestEngine,
    backtest_grid_fixed,
    backtest_grid_adaptive,
    backtest_grid_atr
)

# 函数策略适配器
from .simple_strategy_adapter import adapt, SimpleFunctionAdapter

# 策略示例
from .strategies.small_cap_strategy import SmallCapStrategy
from .strategies.technical import DualMovingAverageStrategy, RSIStrategy, BollingerBandsStrategy
from .strategies.grid_strategy import GridStrategy, AdaptiveGridStrategy, ATRGridStrategy

# 默认使用增强回测引擎
BacktestEngine = EnhancedBacktestEngine

__version__ = '3.0.0'

__all__ = [
    # 核心
    'BacktestCore',
    'DataManager',

    # 策略基类
    'StrategyBase',
    'FactorStrategyBase',

    # 回测引擎
    'BacktestEngine',            # 默认：增强回测引擎
    'EnhancedBacktestEngine',    # 增强回测引擎

    # API
    'GridBacktestEngine',        # 网格交易策略引擎
    'backtest_grid_fixed',       # 固定网格快速回测
    'backtest_grid_adaptive',    # 自适应网格快速回测
    'backtest_grid_atr',         # ATR网格快速回测

    # 函数适配器
    'adapt',
    'SimpleFunctionAdapter',

    # 性能分析
    'PerformanceAnalyzer',

    # 策略示例
    'SmallCapStrategy',
    'DualMovingAverageStrategy',
    'RSIStrategy',
    'BollingerBandsStrategy',
    'GridStrategy',
    'AdaptiveGridStrategy',
    'ATRGridStrategy',
]
