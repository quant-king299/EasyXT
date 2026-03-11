# -*- coding: utf-8 -*-
"""
API 模块

提供不同类型策略的便捷 API
"""

from .technical_api import TechnicalBacktestEngine, backtest_dual_ma
from .selection_api import SelectionBacktestEngine

__all__ = [
    'TechnicalBacktestEngine',   # 技术指标策略 API
    'backtest_dual_ma',          # 双均线快速回测
    'SelectionBacktestEngine',   # 选股策略 API
]
