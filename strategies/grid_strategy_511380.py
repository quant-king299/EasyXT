#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
511380.SH 网格策略回测
专门针对债券ETF的网格策略实现和参数优化
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import json

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "101因子" / "101因子分析平台" / "src"))

try:
    import backtrader as bt
    BACKTRADER_AVAILABLE = True
except ImportError:
    BACKTRADER_AVAILABLE = False
    print("[ERROR] Backtrader未安装，请先安装: pip install backtrader")

from data_manager import LocalDataManager


class GridStrategy(bt.Strategy):
    """
    固定网格交易策略

    核心逻辑：
    1. 在价格区间内设置多个网格线
    2. 价格每跌到一个网格线买入
    3. 价格每涨到一个网格线卖出
    4. 适合震荡行情的ETF品种
    """

    params = (
        ('grid_count', 15),           # 网格数量
        ('price_range', 0.05),        # 价格区间比例
        ('position_size', 1000),      # 每格交易数量
        ('base_price', None),         # 基准价格（None则使用首日收盘价）
        ('enable_trailing', True),    # 是否启用动态调整
        ('trailing_period', 5),       # 动态调整周期
    )

    def __init__(self):
        self.order = None
        self.grid_lines = []  # 网格线价格列表
        self.grid_positions = {}  # 每个网格线的持仓状态
        self.base_price = self.params.base_price
        self.current_grid_index = -1  # 当前所在的网格索引

        # 记录交易
        self.trade_log = []
        self.equity_curve = []

        # 动态调整相关
        self.last_adjust_date = None
        self.price_high = None
        self.price_low = None

        # 性能统计
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0
        self.total_loss = 0

    def next(self):
        """每个bar调用一次"""
        # 如果第一个数据点，初始化网格
        if len(self.data) == 1:
            self._init_grid()
            return

        current_price = self.data.close[0]
        current_date = self.data.datetime.date(0)

        # 记录净值
        self.equity_curve.append({
            'date': current_date,
            'price': current_price,
            'portfolio_value': self.broker.getvalue(),
            'position': self.getposition(self.data).size
        })

        # 动态调整基准价
        if self.params.enable_trailing:
            if self.last_adjust_date is None:
                self.last_adjust_date = current_date
                self.price_high = current_price
                self.price_low = current_price
            else:
                days_since_adjust = (current_date - self.last_adjust_date).days
                if days_since_adjust >= self.params.trailing_period:
                    self._adjust_base_price(current_price)
                    self.last_adjust_date = current_date

            # 更新高低点
            self.price_high = max(self.price_high, current_price)
            self.price_low = min(self.price_low, current_price)

        # 检查是否到达网格线
        self._check_grid_triggers(current_price, current_date)

    def _init_grid(self):
        """初始化网格线"""
        if self.base_price is None:
            self.base_price = self.data.close[0]

        price_range = self.base_price * self.params.price_range
        grid_spacing = price_range / self.params.grid_count

        # 创建网格线（从下到上）
        for i in range(self.params.grid_count + 1):
            grid_price = self.base_price - (price_range / 2) + (i * grid_spacing)
            self.grid_lines.append(grid_price)
            self.grid_positions[grid_price] = 0  # 0表示该网格无持仓

        print(f"[网格初始化] 基准价: {self.base_price:.3f}, 网格数: {self.params.grid_count}")
        print(f"[网格线] {len(self.grid_lines)}条: {[f'{p:.3f}' for p in self.grid_lines[:5]]}...")

    def _check_grid_triggers(self, current_price: float, current_date):
        """检查是否触发网格交易"""
        # 找到当前价格所在的网格区间
        for i in range(len(self.grid_lines) - 1):
            lower_grid = self.grid_lines[i]
            upper_grid = self.grid_lines[i + 1]

            # 如果价格在当前网格区间内
            if lower_grid <= current_price <= upper_grid:
                # 如果是新进入的网格（从上方进入，买入）
                if self.current_grid_index < i:
                    self._execute_grid_trade(lower_grid, current_price, 'buy', current_date)
                    self.current_grid_index = i

                # 如果是新进入的网格（从下方进入，卖出）
                elif self.current_grid_index > i:
                    self._execute_grid_trade(upper_grid, current_price, 'sell', current_date)
                    self.current_grid_index = i

                break

    def _execute_grid_trade(self, trigger_price: float, current_price: float,
                          action: str, current_date):
        """执行网格交易"""
        current_pos = self.getposition(self.data).size

        if action == 'buy':
            # 买入
            if not self.order:  # 没有挂单
                size = self.params.position_size
                self.order = self.buy(size=size)
                self.trade_log.append({
                    'date': current_date,
                    'action': 'buy',
                    'price': current_price,
                    'size': size,
                    'trigger_price': trigger_price
                })

        elif action == 'sell':
            # 卖出（需要持仓）
            if not self.order and current_pos >= self.params.position_size:
                size = self.params.position_size
                self.order = self.sell(size=size)
                self.trade_log.append({
                    'date': current_date,
                    'action': 'sell',
                    'price': current_price,
                    'size': size,
                    'trigger_price': trigger_price
                })

    def _adjust_base_price(self, current_price: float):
        """动态调整基准价格"""
        # 使用最近的高低点重新计算基准价
        new_base = (self.price_high + self.price_low) / 2

        # 只有当变化超过10%时才调整
        if abs(new_base - self.base_price) / self.base_price > 0.10:
            print(f"[动态调整] 基准价: {self.base_price:.3f} -> {new_base:.3f}")
            self.base_price = new_base

            # 重新初始化网格
            price_range = self.base_price * self.params.price_range
            grid_spacing = price_range / self.params.grid_count

            self.grid_lines = []
            self.grid_positions = {}
            for i in range(self.params.grid_count + 1):
                grid_price = self.base_price - (price_range / 2) + (i * grid_spacing)
                self.grid_lines.append(grid_price)
                self.grid_positions[grid_price] = 0

            # 重置当前网格索引
            self.current_grid_index = -1

            # 重置高低点
            self.price_high = current_price
            self.price_low = current_price

            print(f"[网格重新初始化] 新范围: {self.grid_lines[0]:.3f} ~ {self.grid_lines[-1]:.3f}")

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Completed]:
            if order.isbuy():
                self.total_trades += 1
            elif order.issell():
                pass

        self.order = None

    def get_trade_log(self) -> pd.DataFrame:
        """获取交易日志"""
        return pd.DataFrame(self.trade_log)

    def get_equity_curve(self) -> pd.DataFrame:
        """获取净值曲线"""
        return pd.DataFrame(self.equity_curve)

    def stop(self):
        """策略停止时调用"""
        final_value = self.broker.getvalue()
        starting_cash = 100000
        total_return = (final_value - starting_cash) / starting_cash * 100
        print(f"\n{'='*60}")
        print(f"回测完成")
        print(f"初始资金: {starting_cash:,.2f}")
        print(f"最终资金: {final_value:,.2f}")
        print(f"总收益率: {total_return:.2f}%")
        print(f"总交易次数: {len(self.trade_log)}")
        print(f"{'='*60}\n")


class AdaptiveGridStrategy(bt.Strategy):
    """
    自适应网格交易策略

    核心逻辑：
    1. 根据相对涨跌幅触发交易，而非固定网格线
    2. 价格下跌超过买入阈值时买入
    3. 价格上涨超过卖出阈值时卖出
    4. 适合趋势行情或波动较大的品种
    """

    params = (
        ('buy_threshold', 0.01),      # 买入阈值（默认1%）
        ('sell_threshold', 0.01),     # 卖出阈值（默认1%）
        ('position_size', 1000),      # 每次交易数量
        ('base_price', None),         # 基准价格（None则使用首日收盘价）
        ('max_position', 10000),      # 最大持仓数量
    )

    def __init__(self):
        self.order = None
        self.base_price = self.params.base_price
        self.last_buy_price = None  # 上次买入价格
        self.last_sell_price = None  # 上次卖出价格
        self.current_position = 0  # 当前持仓

        # 记录交易
        self.trade_log = []
        self.equity_curve = []

    def next(self):
        """每个bar调用一次"""
        # 如果第一个数据点，初始化基准价
        if len(self.data) == 1:
            if self.base_price is None:
                self.base_price = self.data.close[0]
                self.last_buy_price = self.base_price
                self.last_sell_price = self.base_price
            print(f"[自适应网格初始化] 基准价: {self.base_price:.3f}")
            print(f"[参数] 买入阈值: {self.params.buy_threshold*100:.2f}%, 卖出阈值: {self.params.sell_threshold*100:.2f}%")
            return

        current_price = self.data.close[0]
        current_date = self.data.datetime.date(0)
        current_pos = self.getposition(self.data).size

        # 记录净值
        self.equity_curve.append({
            'date': current_date,
            'price': current_price,
            'portfolio_value': self.broker.getvalue(),
            'position': current_pos
        })

        # 计算相对于基准价的变化
        change_from_base = (current_price - self.base_price) / self.base_price

        # 计算相对于上次交易价格的变化
        if self.last_buy_price:
            change_from_last_buy = (current_price - self.last_buy_price) / self.last_buy_price
        else:
            change_from_last_buy = 0

        if self.last_sell_price:
            change_from_last_sell = (current_price - self.last_sell_price) / self.last_sell_price
        else:
            change_from_last_sell = 0

        # 买入逻辑：价格下跌超过买入阈值
        if change_from_last_buy < -self.params.buy_threshold:
            if not self.order and current_pos < self.params.max_position:
                self.order = self.buy(size=self.params.position_size)
                self.last_buy_price = current_price
                self.trade_log.append({
                    'date': current_date,
                    'action': 'buy',
                    'price': current_price,
                    'size': self.params.position_size,
                    'trigger_price': current_price
                })
                print(f"[自适应网格买入] 价格: {current_price:.3f}, 跌幅: {change_from_last_buy*100:.2f}%")

        # 卖出逻辑：价格上涨超过卖出阈值 且有持仓
        elif change_from_last_sell > self.params.sell_threshold and current_pos >= self.params.position_size:
            if not self.order:
                self.order = self.sell(size=self.params.position_size)
                self.last_sell_price = current_price
                self.trade_log.append({
                    'date': current_date,
                    'action': 'sell',
                    'price': current_price,
                    'size': self.params.position_size,
                    'trigger_price': current_price
                })
                print(f"[自适应网格卖出] 价格: {current_price:.3f}, 涨幅: {change_from_last_sell*100:.2f}%")

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Completed]:
            pass  # 订单完成
        self.order = None

    def get_trade_log(self) -> pd.DataFrame:
        """获取交易日志"""
        return pd.DataFrame(self.trade_log)

    def get_equity_curve(self) -> pd.DataFrame:
        """获取净值曲线"""
        return pd.DataFrame(self.equity_curve)

    def stop(self):
        """策略停止时调用"""
        final_value = self.broker.getvalue()
        starting_cash = 100000
        total_return = (final_value - starting_cash) / starting_cash * 100
        print(f"\n{'='*60}")
        print(f"自适应网格策略回测完成")
        print(f"初始资金: {starting_cash:,.2f}")
        print(f"最终资金: {final_value:,.2f}")
        print(f"总收益率: {total_return:.2f}%")
        print(f"总交易次数: {len(self.trade_log)}")
        print(f"{'='*60}\n")


class ATRGridStrategy(bt.Strategy):
    """
    ATR动态网格交易策略

    核心逻辑：
    1. 使用ATR（平均真实波幅）计算网格间距
    2. 网格间距 = ATR * 倍数
    3. 根据市场波动率动态调整网格
    4. 适合波动率变化的品种
    """

    params = (
        ('atr_period', 300),          # ATR计算周期（分钟数据建议200-500）
        ('atr_multiplier', 6.0),      # ATR倍数（可转债ETF建议5-8）
        ('position_size', 1000),      # 每次交易数量
        ('base_price', None),         # 基准价格（None则使用首日收盘价）
        ('enable_trailing', True),    # 是否启用动态调整基准价
        ('trailing_period', 20),      # 基准价调整周期（天）
    )

    def __init__(self):
        self.order = None
        self.base_price = self.params.base_price
        self.grid_lines = []  # 网格线价格列表
        self.current_grid_index = -1  # 当前所在的网格索引
        self.atr_values = []  # 存储ATR值
        self.current_atr = None  # 当前ATR值

        # 记录交易
        self.trade_log = []
        self.equity_curve = []

        # 动态调整相关
        self.last_adjust_date = None
        self.last_rebalance_date = None

        # 添加ATR指标
        self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)

    def next(self):
        """每个bar调用一次"""
        current_price = self.data.close[0]
        current_date = self.data.datetime.date(0)

        # 如果还未初始化（第一个bar）
        if self.last_rebalance_date is None:
            if self.base_price is None:
                self.base_price = current_price
            self.last_adjust_date = current_date
            self.last_rebalance_date = current_date
            print(f"[ATR网格初始化] 基准价: {self.base_price:.3f}")
            print(f"[参数] ATR周期: {self.params.atr_period}, ATR倍数: {self.params.atr_multiplier}")

            # 立即创建初始网格线，不要等到20天后
            self._rebalance_grid(current_price)
            return

        # 更新当前ATR值
        if len(self.atr) > 0:
            self.current_atr = self.atr[0]

        # 记录净值
        self.equity_curve.append({
            'date': current_date,
            'price': current_price,
            'portfolio_value': self.broker.getvalue(),
            'position': self.getposition(self.data).size
        })

        # 定期重新计算网格（基于ATR）
        days_since_rebalance = (current_date - self.last_rebalance_date).days
        if days_since_rebalance >= self.params.trailing_period and self.current_atr:
            self._rebalance_grid(current_price)
            self.last_rebalance_date = current_date

        # 动态调整基准价
        if self.params.enable_trailing:
            days_since_adjust = (current_date - self.last_adjust_date).days
            if days_since_adjust >= self.params.trailing_period:
                self._adjust_base_price(current_price)
                self.last_adjust_date = current_date

        # 检查是否触发网格交易
        if self.grid_lines:
            self._check_grid_triggers(current_price, current_date)

    def _rebalance_grid(self, current_price: float):
        """基于ATR重新计算网格"""
        # 使用当前ATR或估算值
        if self.current_atr is None:
            # ATR还没有值，使用简单的估算：最近高低价的平均值
            if not hasattr(self, '_price_history') or self._price_history is None:
                self._price_history = []
            self._price_history.append(current_price)
            if len(self._price_history) < 5:
                # 数据太少，使用基准价的1%作为估算
                estimated_atr = self.base_price * 0.01
            else:
                # 使用最近价格的标准差作为估算
                import numpy as np
                prices = np.array(self._price_history[-20:])
                estimated_atr = prices.std() if len(prices) > 0 else self.base_price * 0.01

            grid_spacing = estimated_atr * self.params.atr_multiplier
            print(f"[ATR网格初始化] 使用估算ATR: {estimated_atr:.4f}, 网格间距: {grid_spacing:.4f}")
        else:
            grid_spacing = self.current_atr * self.params.atr_multiplier
            print(f"[ATR网格重新平衡] ATR: {self.current_atr:.4f}, 网格间距: {grid_spacing:.4f}")

        # 创建网格线（以基准价为中心，上下各10格）
        self.grid_lines = []
        num_grids = 10  # 上下各10格

        for i in range(-num_grids, num_grids + 1):
            grid_price = self.base_price + (i * grid_spacing)
            if grid_price > 0:  # 确保价格为正
                self.grid_lines.append(grid_price)

        self.grid_lines.sort()
        print(f"[网格线] {len(self.grid_lines)}条: {[f'{p:.3f}' for p in self.grid_lines[:5]]}...")

    def _check_grid_triggers(self, current_price: float, current_date):
        """检查是否触发网格交易"""
        # 找到当前价格所在的网格区间
        for i in range(len(self.grid_lines) - 1):
            lower_grid = self.grid_lines[i]
            upper_grid = self.grid_lines[i + 1]

            # 如果价格在当前网格区间内
            if lower_grid <= current_price <= upper_grid:
                # 如果是新进入的网格（从上方进入，买入）
                if self.current_grid_index < i:
                    self._execute_grid_trade(lower_grid, current_price, 'buy', current_date)
                    self.current_grid_index = i

                # 如果是新进入的网格（从下方进入，卖出）
                elif self.current_grid_index > i:
                    self._execute_grid_trade(upper_grid, current_price, 'sell', current_date)
                    self.current_grid_index = i

                break

    def _execute_grid_trade(self, trigger_price: float, current_price: float,
                          action: str, current_date):
        """执行网格交易"""
        current_pos = self.getposition(self.data).size

        if action == 'buy':
            # 买入
            if not self.order:
                size = self.params.position_size
                self.order = self.buy(size=size)
                self.trade_log.append({
                    'date': current_date,
                    'action': 'buy',
                    'price': current_price,
                    'size': size,
                    'trigger_price': trigger_price
                })

        elif action == 'sell':
            # 卖出（需要持仓）
            if not self.order and current_pos >= self.params.position_size:
                size = self.params.position_size
                self.order = self.sell(size=size)
                self.trade_log.append({
                    'date': current_date,
                    'action': 'sell',
                    'price': current_price,
                    'size': size,
                    'trigger_price': trigger_price
                })

    def _adjust_base_price(self, current_price: float):
        """动态调整基准价格"""
        # 确保base_price不为None
        if self.base_price is None:
            self.base_price = current_price
            return

        # 简单策略：基准价向当前价格靠近10%
        diff = current_price - self.base_price
        if abs(diff) / self.base_price > 0.05:  # 变化超过5%才调整
            new_base = self.base_price + diff * 0.1
            print(f"[ATR动态调整] 基准价: {self.base_price:.3f} -> {new_base:.3f}")
            self.base_price = new_base
            self._rebalance_grid(current_price)

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Completed]:
            pass
        self.order = None

    def get_trade_log(self) -> pd.DataFrame:
        """获取交易日志"""
        return pd.DataFrame(self.trade_log)

    def get_equity_curve(self) -> pd.DataFrame:
        """获取净值曲线"""
        return pd.DataFrame(self.equity_curve)

    def stop(self):
        """策略停止时调用"""
        final_value = self.broker.getvalue()
        starting_cash = 100000
        total_return = (final_value - starting_cash) / starting_cash * 100
        print(f"\n{'='*60}")
        print(f"ATR动态网格策略回测完成")
        print(f"初始资金: {starting_cash:,.2f}")
        print(f"最终资金: {final_value:,.2f}")
        print(f"总收益率: {total_return:.2f}%")
        print(f"总交易次数: {len(self.trade_log)}")
        print(f"{'='*60}\n")


class GridBacktester:
    """
    网格策略回测器

    提供完整的回测、分析和参数优化功能
    """

    def __init__(self, initial_cash: float = 100000.0, commission: float = 0.0001):
        """
        初始化回测器

        Args:
            initial_cash: 初始资金（默认10万）
            commission: 手续费率（默认万分之一，适合ETF）
        """
        self.initial_cash = initial_cash
        self.commission = commission

    def _load_data_from_qmt(self, stock_code: str, start_date: str, end_date: str, period: str = '1m') -> pd.DataFrame:
        """
        智能加载K线数据：优先从DuckDB读取，无数据时从QMT下载并保存

        策略：
        1. 首先检查DuckDB是否有该周期数据
        2. 有数据：直接使用（快速）
        3. 无数据：从QMT下载 → 保存到DuckDB → 返回数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期（1m/5m/15m/30m/1h/1d/1w）

        Returns:
            pd.DataFrame: K线数据
        """
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        print(f"[数据周期] {period}")
        print(f"[数据获取] 尝试获取 {stock_code} {period} 数据...")
        print(f"[数据获取] 请求日期范围: {start_date} ~ {end_date}")

        # ========== 步骤1: 尝试从DuckDB读取 ==========
        try:
            print(f"[步骤1/3] 检查DuckDB中是否有 {period} 数据...")

            # 根据周期确定表名
            period_to_table = {
                '1m': 'stock_1m',
                '5m': 'stock_5m',
                '15m': 'stock_15m',
                '30m': 'stock_30m',
                '1h': 'stock_60m',
                '1d': 'stock_daily',
                '1w': 'stock_daily'
            }

            table_name = period_to_table.get(period, 'stock_daily')
            print(f"[步骤1/3] 查询表: {table_name}")

            import duckdb
            db_path = 'D:/StockData/stock_data.ddb'
            con = duckdb.connect(db_path, read_only=True)

            # 构建查询（根据不同的表使用不同的字段）
            if table_name == 'stock_daily':
                # stock_daily表使用date字段和period字段
                query = f"""
                    SELECT date, open, high, low, close, volume, amount
                    FROM {table_name}
                    WHERE stock_code = '{stock_code}'
                      AND period = '{period}'
                      AND date >= '{start_date}'
                      AND date <= '{end_date}'
                    ORDER BY date ASC
                """
            else:
                # stock_1m等表直接使用date字段（TIMESTAMP类型）
                query = f"""
                    SELECT date, open, high, low, close, volume, amount
                    FROM {table_name}
                    WHERE stock_code = '{stock_code}'
                      AND date >= '{start_date} 00:00:00'
                      AND date <= '{end_date} 23:59:59'
                    ORDER BY date ASC
                """

            df = con.execute(query).df()
            con.close()

            if not df.empty:
                # 设置索引
                df = df.set_index('date')
                df.index = pd.to_datetime(df.index)
                df = df.sort_index()

                # 删除amount列（Backtrader不认识，需要openinterest）
                if 'amount' in df.columns:
                    df = df.drop(columns=['amount'])

                print(f"[步骤1/3] [OK] 从DuckDB读取成功 ({len(df):,} 条)")
                print(f"[数据范围] {df.index[0]} ~ {df.index[-1]}")
                print(f"[数据来源] DuckDB本地数据库（高速读取）")
                return df
            else:
                print(f"[步骤1/3] DuckDB中无该周期数据，将从QMT下载")

        except Exception as e:
            print(f"[步骤1/3] DuckDB读取失败: {e}")
            print(f"[步骤1/3] 将从QMT下载数据")

        # ========== 步骤2: 从QMT下载数据 ==========
        try:
            from xtquant import xtdata
        except ImportError:
            raise Exception("xtquant未安装，且DuckDB无数据，无法获取数据")

        start_time_str = start_dt.strftime('%Y%m%d')
        end_time_str = end_dt.strftime('%Y%m%d')

        print(f"[步骤2/3] 从QMT下载数据...")
        print(f"[步骤2/3] QMT下载参数: {start_time_str} ~ {end_time_str}, 周期={period}")

        # 下载历史数据（使用指定的周期）
        xtdata.download_history_data(
            stock_code=stock_code,
            period=period,
            start_time=start_time_str,
            end_time=end_time_str
        )

        # 获取市场数据（使用count=0获取全部数据）
        data = xtdata.get_market_data(
            stock_list=[stock_code],
            period=period,
            count=0
        )

        if not data or 'time' not in data:
            raise Exception(f"无法从QMT获取{stock_code}的数据")

        print(f"[步骤2/3] QMT返回原始数据: {len(data['time'].columns)} 条")

        # 转换数据格式
        time_df = data['time']
        timestamps = time_df.columns.tolist()

        records = []
        seen_timestamps = set()

        for idx, ts in enumerate(timestamps):
            try:
                dt = pd.to_datetime(ts)

                # 去重
                if dt in seen_timestamps:
                    continue
                seen_timestamps.add(dt)

                # 过滤日期范围
                if start_dt <= dt <= end_dt:
                    records.append({
                        'datetime': dt,
                        'open': float(data['open'].iloc[0, idx]),
                        'high': float(data['high'].iloc[0, idx]),
                        'low': float(data['low'].iloc[0, idx]),
                        'close': float(data['close'].iloc[0, idx]),
                        'volume': float(data['volume'].iloc[0, idx])
                        # 注意：不包含amount，因为Backtrader不认识
                    })
            except:
                continue

        df = pd.DataFrame(records)

        if df.empty:
            raise Exception(f"没有{start_date}到{end_date}的数据")

        df.set_index('datetime', inplace=True)
        df.sort_index(inplace=True)

        # 删除重复索引
        df = df[~df.index.duplicated(keep='first')]

        print(f"[步骤2/3] [OK] 从QMT下载成功 ({len(df):,} 条)")
        print(f"[数据范围] {df.index[0]} ~ {df.index[-1]}")
        print(f"[价格范围] {df['close'].min():.3f} ~ {df['close'].max():.3f}")

        # 调试信息：显示数据周期
        if len(df) > 0:
            time_diff = df.index[-1] - df.index[0]
            days = time_diff.days
            if days > 0:
                avg_per_day = len(df) / days
                print(f"[数据验证] 平均每天{avg_per_day:.0f}条数据")
                if avg_per_day > 200:
                    print(f"[数据验证] 确认: 分钟级数据")
                elif avg_per_day > 50:
                    print(f"[数据验证] 确认: 可能是5-15分钟数据")
                elif avg_per_day < 5:
                    print(f"[数据验证] 确认: 日线数据")
                else:
                    print(f"[数据验证] 确认: 小时级数据")

        # ========== 步骤3: 保存到DuckDB（下次更快） ==========
        try:
            print(f"[步骤3/3] 保存数据到DuckDB...")

            # 确定目标表
            period_to_table = {
                '1m': 'stock_1m',
                '5m': 'stock_5m',
                '15m': 'stock_15m',
                '30m': 'stock_30m',
                '1h': 'stock_60m',
                '1d': 'stock_daily',
                '1w': 'stock_daily'
            }

            table_name = period_to_table.get(period, 'stock_daily')
            print(f"[步骤3/3] 目标表: {table_name}")

            import duckdb
            db_path = 'D:/StockData/stock_data.ddb'
            con = duckdb.connect(db_path)

            # 准备数据
            df_to_save = df.reset_index()
            df_to_save.columns = df_to_save.columns.str.lower()

            # 重命名datetime为date（如果需要）
            if 'datetime' in df_to_save.columns:
                df_to_save = df_to_save.rename(columns={'datetime': 'date'})

            # 添加必要字段
            df_to_save['stock_code'] = stock_code
            df_to_save['symbol_type'] = 'stock'
            df_to_save['period'] = period
            df_to_save['adjust_type'] = 'none'
            df_to_save['factor'] = 1.0

            # 确保日期格式正确
            if 'date' in df_to_save.columns:
                df_to_save['date'] = pd.to_datetime(df_to_save['date'])

            # 删除旧数据（简单方式：删除该股票在该周期的所有数据）
            if table_name == 'stock_daily':
                delete_query = f"""
                    DELETE FROM {table_name}
                    WHERE stock_code = '{stock_code}'
                      AND period = '{period}'
                """
            else:
                # 对于分钟表，删除整个股票的数据（因为表中可能没有period字段）
                delete_query = f"""
                    DELETE FROM {table_name}
                    WHERE stock_code = '{stock_code}'
                """

            con.execute(delete_query)
            print(f"[步骤3/3] 已清除旧数据")

            # 插入新数据
            # 使用DuckDB的DataFrame注册功能
            con.register('df_to_save_table', df_to_save)
            con.execute(f"INSERT INTO {table_name} SELECT * FROM df_to_save_table")
            con.unregister('df_to_save_table')
            print(f"[步骤3/3] [OK] 已保存 {len(df_to_save):,} 条数据到 {table_name}")

            con.close()

        except Exception as e:
            print(f"[步骤3/3] 保存失败（可忽略）: {e}")
            import traceback
            traceback.print_exc()

        print(f"\n[完成] 数据加载完成，来源: QMT（已缓存到DuckDB）")
        return df

    def _calculate_win_rate(self, trade_log: pd.DataFrame):
        """从交易日志计算真实的胜率"""
        if trade_log.empty:
            return 0, 0, 0.0

        # 配对买入和卖出，计算每对交易的盈亏
        buy_trades = trade_log[trade_log['action'] == 'buy'].copy()
        sell_trades = trade_log[trade_log['action'] == 'sell'].copy()

        if buy_trades.empty or sell_trades.empty:
            return 0, 0, 0.0

        # 按日期排序
        buy_trades = buy_trades.sort_values('date').reset_index(drop=True)
        sell_trades = sell_trades.sort_values('date').reset_index(drop=True)

        # 简单的FIFO配对：第一个买入配第一个卖出
        pairs = min(len(buy_trades), len(sell_trades))
        won_count = 0
        lost_count = 0

        for i in range(pairs):
            buy_price = buy_trades.iloc[i]['price']
            sell_price = sell_trades.iloc[i]['price']

            # 卖出价 > 买入价 = 盈利
            if sell_price > buy_price:
                won_count += 1
            else:
                lost_count += 1

        total_pairs = won_count + lost_count
        win_rate = won_count / total_pairs if total_pairs > 0 else 0.0

        print(f"[胜率统计] 总交易对: {total_pairs}, 盈利: {won_count}, 亏损: {lost_count}, 胜率: {win_rate*100:.1f}%")

        return won_count, lost_count, win_rate

    def run_backtest(self,
                    stock_code: str,
                    start_date: str,
                    end_date: str,
                    strategy_mode: str = 'fixed',
                    # 固定网格参数
                    grid_count: int = 15,
                    price_range: float = 0.05,
                    enable_trailing: bool = True,
                    # 自适应网格参数
                    buy_threshold: float = 0.01,
                    sell_threshold: float = 0.01,
                    # ATR网格参数
                    atr_period: int = 14,
                    atr_multiplier: float = 1.0,
                    # 通用参数
                    position_size: int = 1000,
                    base_price: float = None,
                    data_period: str = '1m') -> Dict[str, Any]:
        """
        运行单次回测（支持三种策略模式）

        Args:
            stock_code: 股票代码（如511380.SH）
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            strategy_mode: 策略模式 ('fixed'/'adaptive'/'atr')
            grid_count: 固定网格数量
            price_range: 固定网格价格区间比例
            enable_trailing: 固定网格是否启用动态调整
            buy_threshold: 自适应网格买入阈值
            sell_threshold: 自适应网格卖出阈值
            atr_period: ATR网格周期
            atr_multiplier: ATR网格倍数
            position_size: 每格交易数量
            base_price: 基准价格（None则使用首日收盘价）
            data_period: 数据周期（1m/5m/15m/30m/1h/1d/1w）
        """
        if not BACKTRADER_AVAILABLE:
            raise Exception("Backtrader未安装")

        # 获取数据（使用指定的数据周期）
        stock_data = self._load_data_from_qmt(stock_code, start_date, end_date, period=data_period)

        if stock_data.empty:
            raise Exception(f"无法获取{stock_code}的数据")

        # 创建回测引擎
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(self.initial_cash)
        cerebro.broker.setcommission(commission=self.commission)

        # 添加数据
        data_feed = bt.feeds.PandasData(dataname=stock_data)
        cerebro.adddata(data_feed)

        # 根据策略模式添加不同的策略
        if strategy_mode == 'fixed':
            cerebro.addstrategy(
                GridStrategy,
                grid_count=grid_count,
                price_range=price_range,
                position_size=position_size,
                base_price=base_price,
                enable_trailing=enable_trailing
            )
            print(f"[策略模式] 固定网格")
            print(f"[参数] 网格数={grid_count}, 区间={price_range*100:.1f}%, 动态调整={enable_trailing}")

        elif strategy_mode == 'adaptive':
            cerebro.addstrategy(
                AdaptiveGridStrategy,
                buy_threshold=buy_threshold,
                sell_threshold=sell_threshold,
                position_size=position_size,
                base_price=base_price
            )
            print(f"[策略模式] 自适应网格")
            print(f"[参数] 买入阈值={buy_threshold*100:.2f}%, 卖出阈值={sell_threshold*100:.2f}%")

        elif strategy_mode == 'atr':
            cerebro.addstrategy(
                ATRGridStrategy,
                atr_period=atr_period,
                atr_multiplier=atr_multiplier,
                position_size=position_size,
                base_price=base_price,
                enable_trailing=enable_trailing
            )
            print(f"[策略模式] ATR动态网格")
            print(f"[参数] ATR周期={atr_period}, ATR倍数={atr_multiplier}")

        # 添加分析器
        cerebro.addanalyzer(btanalyzers.SharpeRatio, _name='sharpe', riskfreerate=0.0)
        cerebro.addanalyzer(btanalyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(btanalyzers.Returns, _name='returns')
        cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name='trades')

        # 运行回测
        print(f"\n{'='*60}")
        print(f"开始回测: {stock_code}")
        print(f"时间范围: {start_date} ~ {end_date}")
        print(f"初始资金: {self.initial_cash:,.2f}")
        print(f"每格交易数量: {position_size}股")
        print(f"{'='*60}\n")

        results = cerebro.run()
        strategy = results[0]

        # 获取分析结果
        sharpe = results[0].analyzers.sharpe.get_analysis()
        drawdown = results[0].analyzers.drawdown.get_analysis()
        returns = results[0].analyzers.returns.get_analysis()
        trades = results[0].analyzers.trades.get_analysis()

        # 获取交易日志（实际订单数量）
        trade_log = strategy.get_trade_log()
        actual_trade_count = len(trade_log)

        # 计算真实的胜率（从交易日志中配对买卖）
        won_count, lost_count, win_rate = self._calculate_win_rate(trade_log)

        # 提取关键指标
        metrics = {
            'initial_cash': self.initial_cash,
            'final_value': cerebro.broker.getvalue(),
            'total_return': (cerebro.broker.getvalue() - self.initial_cash) / self.initial_cash,
            'sharpe_ratio': sharpe.get('sharperatio', 0) if 'sharperatio' in sharpe else None,
            'max_drawdown': drawdown.get('max', {}).get('drawdown', 0) if drawdown else 0,
            'max_drawdown_len': drawdown.get('max', {}).get('len', 0) if drawdown else 0,
            'total_trades': actual_trade_count,
            'won_trades': won_count,
            'lost_trades': lost_count,
            'win_rate': win_rate,
        }

        # 构建返回的参数字典
        params_dict = {
            'strategy_mode': strategy_mode,
            'position_size': position_size,
            'base_price': base_price,
            'data_period': data_period
        }

        # 根据策略模式添加特定参数
        if strategy_mode == 'fixed':
            params_dict.update({
                'grid_count': grid_count,
                'price_range': price_range,
                'enable_trailing': enable_trailing
            })
        elif strategy_mode == 'adaptive':
            params_dict.update({
                'buy_threshold': buy_threshold,
                'sell_threshold': sell_threshold
            })
        elif strategy_mode == 'atr':
            params_dict.update({
                'atr_period': atr_period,
                'atr_multiplier': atr_multiplier
            })

        return {
            'metrics': metrics,
            'trade_log': strategy.get_trade_log(),
            'equity_curve': strategy.get_equity_curve(),
            'params': params_dict
        }


class GridParameterOptimizer:
    """
    网格策略参数优化器

    使用网格搜索或遗传算法优化策略参数
    """

    def __init__(self, backtester: GridBacktester):
        self.backtester = backtester

    def grid_search(self,
                   stock_code: str,
                   start_date: str,
                   end_date: str,
                   param_grid: Dict[str, List],
                   optimization_metric: str = 'total_return',
                   data_period: str = '1m') -> pd.DataFrame:  # 新增：数据周期参数
        """
        网格搜索参数优化

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            param_grid: 参数网格
                {
                    'grid_count': [5, 10, 15, 20],
                    'price_range': [0.01, 0.02, 0.03, 0.05],
                    'position_size': [500, 1000, 2000]
                }
            optimization_metric: 优化目标指标
            data_period: 数据周期（1m/5m/15m/30m/1h/1d/1w）

        Returns:
            优化结果DataFrame
        """
        results = []
        total_combinations = 1
        for param_values in param_grid.values():
            total_combinations *= len(param_values)

        print(f"\n{'='*60}")
        print(f"参数优化开始")
        print(f"数据周期: {data_period}")
        print(f"总参数组合数: {total_combinations}")
        print(f"优化目标: {optimization_metric}")
        print(f"{'='*60}\n")

        count = 0
        # 生成所有参数组合
        import itertools
        keys = list(param_grid.keys())
        values = list(param_grid.values())

        for combination in itertools.product(*values):
            params = dict(zip(keys, combination))
            count += 1

            try:
                print(f"[{count}/{total_combinations}] 测试参数: {params}")

                result = self.backtester.run_backtest(
                    stock_code=stock_code,
                    start_date=start_date,
                    end_date=end_date,
                    data_period=data_period,  # 显式传递数据周期
                    **params
                )

                results.append({
                    **params,
                    **result['metrics']
                })

            except Exception as e:
                print(f"  [FAIL] 失败: {e}")
                continue

        # 转换为DataFrame并排序
        results_df = pd.DataFrame(results)

        # 计算综合评分
        results_df['score'] = (
            results_df['total_return'] * 0.4 +           # 收益率权重40%
            results_df['sharpe_ratio'].fillna(0) * 0.3 +  # 夏普比率权重30%
            (10 - results_df['max_drawdown']) * 0.2 +    # 回撤越小越好（权重20%）
            results_df['win_rate'] * 100 * 0.1           # 胜率权重10%
        )

        # 按优化指标排序（降序）
        results_df = results_df.sort_values(by=optimization_metric, ascending=False)

        print(f"\n{'='*60}")
        print(f"优化完成！最佳参数:")
        best_params = results_df.iloc[0]
        print(f"收益率: {best_params['total_return']*100:.2f}%")
        print(f"夏普比率: {best_params['sharpe_ratio']:.2f}")
        print(f"最大回撤: {best_params['max_drawdown']:.2f}%")
        print(f"参数: {dict(results_df[keys].iloc[0])}")
        print(f"{'='*60}\n")

        return results_df


# 导入必要的模块
try:
    import backtrader.analyzers as btanalyzers
except:
    pass


if __name__ == "__main__":
    # 示例：运行511380.SH的回测
    backtester = GridBacktester(initial_cash=100000, commission=0.0001)

    result = backtester.run_backtest(
        stock_code='511380.SH',
        start_date='2024-01-01',
        end_date='2024-12-31',
        grid_count=10,
        price_range=0.02,
        position_size=1000,
        enable_trailing=False
    )

    print("\n回测结果:")
    print(f"总收益率: {result['metrics']['total_return']*100:.2f}%")
    sharpe = result['metrics'].get('sharpe_ratio')
    print(f"夏普比率: {sharpe:.2f}" if sharpe is not None else "夏普比率: N/A")
    print(f"最大回撤: {result['metrics']['max_drawdown']:.2f}%")
    print(f"交易次数: {result['metrics']['total_trades']}")
    print(f"盈利交易: {result['metrics'].get('won_trades', 0)}")
    print(f"亏损交易: {result['metrics'].get('lost_trades', 0)}")
    print(f"胜率: {result['metrics'].get('win_rate', 0)*100:.2f}%")
