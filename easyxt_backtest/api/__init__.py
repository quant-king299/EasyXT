# -*- coding: utf-8 -*-
"""
API 模块

提供不同类型策略的便捷 API
"""

from .technical_api import TechnicalBacktestEngine, backtest_dual_ma
from .selection_api import SelectionBacktestEngine
from .grid_api import GridBacktestEngine, backtest_grid_fixed, backtest_grid_adaptive, backtest_grid_atr

__all__ = [
    'TechnicalBacktestEngine',   # 技术指标策略 API
    'backtest_dual_ma',          # 双均线快速回测
    'SelectionBacktestEngine',   # 选股策略 API
    'GridBacktestEngine',        # 网格交易策略 API
    'backtest_grid_fixed',       # 固定网格快速回测
    'backtest_grid_adaptive',    # 自适应网格快速回测
    'backtest_grid_atr',         # ATR网格快速回测
]
