# -*- coding: utf-8 -*-
"""
技术指标策略 API

提供简洁的 API 用于技术指标策略回测
"""

import backtrader as bt
import pandas as pd
from typing import Dict, Any, Optional, Type
from datetime import datetime

from ..core import BacktestCore, DataManager
from ..strategies.technical import (
    DualMovingAverageStrategy,
    RSIStrategy,
    BollingerBandsStrategy
)


class TechnicalBacktestEngine:
    """
    技术指标策略回测引擎

    提供简洁的 API，隐藏 Backtrader 的复杂性
    """

    def __init__(self,
                 initial_cash: float = 100000.0,
                 commission: float = 0.001):
        """
        初始化回测引擎

        Args:
            initial_cash: 初始资金
            commission: 佣金率
        """
        self.core = BacktestCore(initial_cash, commission)
        self.data_manager = DataManager()

    def load_data(self,
                  stock_code: str,
                  start_date: str,
                  end_date: str) -> bt.feeds.PandasData:
        """
        加载股票数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            Backtrader 数据源
        """
        df = self.data_manager.load_stock_data(stock_code, start_date, end_date)

        if df.empty:
            raise ValueError(f"无法获取 {stock_code} 的数据")

        return self.data_manager.prepare_backtrader_data(df)

    def add_data(self, data: bt.feeds.PandasData):
        """
        添加数据到回测引擎

        Args:
            data: Backtrader 数据源
        """
        self.core.add_data(data)

    def add_strategy(self,
                    strategy_class: Type[bt.Strategy],
                    **kwargs):
        """
        添加策略

        Args:
            strategy_class: 策略类
            **kwargs: 策略参数
        """
        self.core.add_strategy(strategy_class, **kwargs)

    def run(self) -> Dict[str, Any]:
        """
        运行回测

        Returns:
            回测结果字典（含 metrics, trades, portfolio_curve, risk_analysis）
        """
        # 运行回测
        self.core.run()

        # 获取完整结果
        return self.core.get_full_results()

    def quick_backtest(self,
                      stock_code: str,
                      start_date: str,
                      end_date: str,
                      strategy_class: Type[bt.Strategy],
                      **strategy_params) -> Dict[str, Any]:
        """
        快速回测（一站式）

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            strategy_class: 策略类
            **strategy_params: 策略参数

        Returns:
            回测结果

        示例：
            engine = TechnicalBacktestEngine()
            result = engine.quick_backtest(
                stock_code='000001.SZ',
                start_date='2023-01-01',
                end_date='2023-12-31',
                strategy_class=DualMovingAverageStrategy,
                short_period=5,
                long_period=20
            )
        """
        # 加载数据
        data = self.load_data(stock_code, start_date, end_date)

        # 添加数据
        self.add_data(data)

        # 添加策略
        self.add_strategy(strategy_class, **strategy_params)

        # 运行回测
        return self.run()


# 便捷函数
def backtest_dual_ma(stock_code: str,
                    start_date: str,
                    end_date: str,
                    short_period: int = 5,
                    long_period: int = 20,
                    initial_cash: float = 100000.0) -> Dict[str, Any]:
    """
    双均线策略快速回测

    Args:
        stock_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        short_period: 短期均线周期
        long_period: 长期均线周期
        initial_cash: 初始资金

    Returns:
        回测结果
    """
    engine = TechnicalBacktestEngine(initial_cash=initial_cash)
    return engine.quick_backtest(
        stock_code=stock_code,
        start_date=start_date,
        end_date=end_date,
        strategy_class=DualMovingAverageStrategy,
        short_period=short_period,
        long_period=long_period
    )
