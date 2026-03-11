# -*- coding: utf-8 -*-
"""
技术指标策略

包含各种基于技术指标的策略：
- 双均线策略
- RSI策略
- MACD策略
- 布林带策略
"""

import backtrader as bt
from typing import Optional


class DualMovingAverageStrategy(bt.Strategy):
    """
    双均线策略

    策略逻辑：
    - 短期均线上穿长期均线（金叉）→ 买入
    - 短期均线下穿长期均线（死叉）→ 卖出
    """

    params = (
        ('short_period', 5),      # 短期均线周期
        ('long_period', 20),      # 长期均线周期
        ('print_log', True),      # 是否打印日志
    )

    def __init__(self):
        # 计算均线
        self.sma_short = bt.indicators.SMA(period=self.params.short_period)
        self.sma_long = bt.indicators.SMA(period=self.params.long_period)

        # 金叉死叉信号
        self.crossover = bt.indicators.CrossOver(self.sma_short, self.sma_long)

        # 记录订单
        self.order = None

    def next(self):
        """每个bar调用"""
        # 如果有未完成订单，不操作
        if self.order:
            return

        # 如果没有持仓
        if not self.position:
            # 金叉，买入
            if self.crossover > 0:
                self.order = self.buy()
                if self.params.print_log:
                    self.log(f'金叉买入 @ {self.data.close[0]:.2f}')
        else:
            # 死叉，卖出
            if self.crossover < 0:
                self.order = self.sell()
                if self.params.print_log:
                    self.log(f'死叉卖出 @ {self.data.close[0]:.2f}')

    def log(self, txt):
        """打印日志"""
        dt = self.data.datetime.date(0)
        print(f'[{dt}] {txt}')


class RSIStrategy(bt.Strategy):
    """
    RSI策略

    策略逻辑：
    - RSI < 30（超卖）→ 买入
    - RSI > 70（超买）→ 卖出
    """

    params = (
        ('rsi_period', 14),      # RSI周期
        ('oversold', 30),        # 超卖线
        ('overbought', 70),      # 超买线
    )

    def __init__(self):
        # 计算RSI
        self.rsi = bt.indicators.RSI(period=self.params.rsi_period)

        self.order = None

    def next(self):
        if self.order:
            return

        if not self.position:
            # RSI超卖，买入
            if self.rsi < self.params.oversold:
                self.order = self.buy()
        else:
            # RSI超买，卖出
            if self.rsi > self.params.overbought:
                self.order = self.sell()


class BollingerBandsStrategy(bt.Strategy):
    """
    布林带策略

    策略逻辑：
    - 价格跌破下轨 → 买入
    - 价格突破上轨 → 卖出
    """

    params = (
        ('period', 20),          # 均线周期
        ('devfactor', 2),        # 标准差倍数
    )

    def __init__(self):
        # 计算布林带
        self.bollinger = bt.indicators.BollingerBands(
            period=self.params.period,
            devfactor=self.params.devfactor
        )

        self.order = None

    def next(self):
        if self.order:
            return

        if not self.position:
            # 价格跌破下轨，买入
            if self.data.close[0] < self.bollinger.lines.bot[0]:
                self.order = self.buy()
        else:
            # 价格突破上轨，卖出
            if self.data.close[0] > self.bollinger.lines.top[0]:
                self.order = self.sell()
