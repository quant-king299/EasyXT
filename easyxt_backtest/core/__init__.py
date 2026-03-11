# -*- coding: utf-8 -*-
"""
回测核心模块

提供统一的 Backtrader 底层引擎，所有回测策略都基于此核心
"""

from .backtest_core import BacktestCore, DataManager

__all__ = [
    'BacktestCore',
    'DataManager',
]
