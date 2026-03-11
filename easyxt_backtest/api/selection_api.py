# -*- coding: utf-8 -*-
"""
选股策略 API

提供简洁的 API 用于选股策略回测
"""
from typing import Dict, List
from ..engine_v2 import BacktestEngineV2, BacktestResult


class SelectionBacktestEngine:
    """
    选股策略回测引擎

    使用完全修复的新引擎（基于 Backtrader）
    所有已知的除零错误都已修复
    """

    def __init__(self,
                 initial_cash: float = 1000000,
                 commission: float = 0.001,
                 data_manager=None):
        """
        初始化回测引擎

        Args:
            initial_cash: 初始资金
            commission: 佣金率
            data_manager: 数据管理器
        """
        # 使用修复后的新引擎
        self._engine = BacktestEngineV2(
            initial_cash=initial_cash,
            commission=commission,
            data_manager=data_manager
        )

    def run_backtest(self,
                    strategy,
                    start_date: str,
                    end_date: str) -> BacktestResult:
        """
        运行回测

        Args:
            strategy: 选股策略实例
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            回测结果
        """
        return self._engine.run_backtest(strategy, start_date, end_date)
