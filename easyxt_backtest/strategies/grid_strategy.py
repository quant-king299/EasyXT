# -*- coding: utf-8 -*-
"""
网格交易策略

基于 Backtrader 的网格策略实现：
1. GridStrategy - 固定网格策略
2. AdaptiveGridStrategy - 自适应网格策略
3. ATRGridStrategy - ATR动态网格策略

适合震荡行情的ETF品种（如511380.SH债券ETF）
"""
import backtrader as bt
from typing import Dict, List, Tuple, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


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
        ('price_range', 0.20),        # 价格区间比例（最终修复：20%覆盖99.6%时间）
        ('position_size', 1000),      # 每格交易数量
        ('base_price', None),         # 基准价格（None则使用首日收盘价）
        ('enable_trailing', True),    # 是否启用动态调整
        ('trailing_period', 5),       # 动态调整周期
        ('max_position', 15000),      # 最大持仓限制（防止持仓无限累积）
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

    def _find_grid_index(self, price: float) -> int:
        """
        找到价格所在的网格索引

        返回：
            网格索引（0到grid_count-1）
            -1表示价格超出网格范围
        """
        for i in range(len(self.grid_lines) - 1):
            lower_grid = self.grid_lines[i]
            upper_grid = self.grid_lines[i + 1]
            if lower_grid <= price <= upper_grid:
                return i
        return -1  # 超出网格范围

    def _check_grid_triggers(self, current_price: float, current_date):
        """
        检查是否触发网格交易（修复版）

        修复BUG：价格跳跃时只交易一次的问题
        现在每次穿越网格都会触发交易
        """
        # 找到当前价格所在的网格区间
        new_grid_index = self._find_grid_index(current_price)

        # 如果价格超出网格范围，不交易
        if new_grid_index == -1:
            return

        # 如果是第一次，设置索引但不交易
        if self.current_grid_index == -1:
            self.current_grid_index = new_grid_index
            return

        # 计算穿越的网格数（可以是正数或负数）
        grid_diff = new_grid_index - self.current_grid_index

        if grid_diff > 0:
            # 从下方进入上方（价格上涨），应该卖出
            # 修复：穿越了多个网格，卖出多次
            for i in range(grid_diff):
                # 卖出时使用上方网格线价格作为触发价
                trigger_grid_idx = self.current_grid_index + i + 1
                if trigger_grid_idx < len(self.grid_lines):
                    trigger_price = self.grid_lines[trigger_grid_idx]
                    self._execute_grid_trade(trigger_price, current_price, 'sell', current_date)

        elif grid_diff < 0:
            # 从上方进入下方（价格下跌），应该买入
            # 修复：穿越了多个网格，买入多次
            for i in range(abs(grid_diff)):
                # 买入时使用下方网格线价格作为触发价
                trigger_grid_idx = self.current_grid_index - i - 1
                if trigger_grid_idx >= 0:
                    trigger_price = self.grid_lines[trigger_grid_idx]
                    self._execute_grid_trade(trigger_price, current_price, 'buy', current_date)

        # 更新当前网格索引
        self.current_grid_index = new_grid_index

    def _execute_grid_trade(self, trigger_price: float, current_price: float,
                          action: str, current_date):
        """
        执行网格交易（修复版）

        修复：
        - 添加持仓上限检查
        - 改进卖出逻辑（卖出所有持仓而不是固定数量）
        - 添加每格持仓跟踪
        """
        current_pos = self.getposition(self.data).size

        if action == 'buy':
            # 买入逻辑
            if not self.order:  # 没有挂单
                size = self.params.position_size

                # 修复：检查持仓上限
                max_pos = self.params.max_position
                if current_pos + size > max_pos:
                    # 超过持仓上限，减少买入数量或跳过
                    if current_pos < max_pos:
                        size = max_pos - current_pos
                    else:
                        # 已达上限，跳过这次买入
                        return

                # 执行买入
                self.order = self.buy(size=size)

                # 修复：跟踪每格持仓
                self.grid_positions[trigger_price] = \
                    self.grid_positions.get(trigger_price, 0) + size

                self.trade_log.append({
                    'date': current_date,
                    'action': 'buy',
                    'price': current_price,
                    'size': size,
                    'trigger_price': trigger_price
                })

        elif action == 'sell':
            # 卖出逻辑
            if not self.order and current_pos > 0:
                # 修复：只卖出这个触发价的持仓
                grid_pos = self.grid_positions.get(trigger_price, 0)

                if grid_pos > 0:
                    # 卖出这格的持仓
                    size = min(grid_pos, self.params.position_size, current_pos)
                    self.order = self.sell(size=size)

                    # 更新持仓跟踪
                    self.grid_positions[trigger_price] = grid_pos - size

                    self.trade_log.append({
                        'date': current_date,
                        'action': 'sell',
                        'price': current_price,
                        'size': size,
                        'trigger_price': trigger_price
                    })
                else:
                    # 这格没有持仓，不能卖出
                    pass

    def _adjust_base_price(self, current_price: float):
        """
        动态调整基准价格（修复版）

        修复：动态调整时不重置current_grid_index，避免重复触发交易
        """
        # 使用最近的高低点重新计算基准价
        new_base = (self.price_high + self.price_low) / 2

        # 只有当变化超过10%时才调整
        if abs(new_base - self.base_price) / self.base_price > 0.10:
            print(f"[动态调整] 基准价: {self.base_price:.3f} -> {new_base:.3f}")
            self.base_price = new_base

            # 重新初始化网格
            price_range = self.base_price * self.params.price_range
            grid_spacing = price_range / self.params.grid_count

            # 保存旧持仓以便迁移
            old_positions = self.grid_positions.copy()

            self.grid_lines = []
            self.grid_positions = {}
            for i in range(self.params.grid_count + 1):
                grid_price = self.base_price - (price_range / 2) + (i * grid_spacing)
                self.grid_lines.append(grid_price)
                self.grid_positions[grid_price] = 0

            # 修复：找到当前价格在新网格中的位置
            new_index = self._find_grid_index(current_price)
            self.current_grid_index = new_index

            # 重置高低点
            self.price_high = current_price
            self.price_low = current_price

            print(f"[网格重新初始化] 新范围: {self.grid_lines[0]:.3f} ~ {self.grid_lines[-1]:.3f}")
            print(f"[动态调整] 当前网格索引: {new_index}, 当前价格: {current_price:.3f}")

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
        """
        检查是否触发网格交易（修复版）

        修复BUG：价格跳跃时只交易一次的问题
        现在每次穿越网格都会触发交易
        """
        # 找到当前价格所在的网格区间
        new_grid_index = self._find_grid_index(current_price)

        # 如果价格超出网格范围，不交易
        if new_grid_index == -1:
            return

        # 如果是第一次，设置索引但不交易
        if self.current_grid_index == -1:
            self.current_grid_index = new_grid_index
            return

        # 计算穿越的网格数（可以是正数或负数）
        grid_diff = new_grid_index - self.current_grid_index

        if grid_diff > 0:
            # 从下方进入上方（价格上涨），应该卖出
            # 修复：穿越了多个网格，卖出多次
            for i in range(grid_diff):
                trigger_grid_idx = self.current_grid_index + i + 1
                if trigger_grid_idx < len(self.grid_lines):
                    trigger_price = self.grid_lines[trigger_grid_idx]
                    self._execute_grid_trade(trigger_price, current_price, 'sell', current_date)

        elif grid_diff < 0:
            # 从上方进入下方（价格下跌），应该买入
            # 修复：穿越了多个网格，买入多次
            for i in range(abs(grid_diff)):
                trigger_grid_idx = self.current_grid_index - i - 1
                if trigger_grid_idx >= 0:
                    trigger_price = self.grid_lines[trigger_grid_idx]
                    self._execute_grid_trade(trigger_price, current_price, 'buy', current_date)

        # 更新当前网格索引
        self.current_grid_index = new_grid_index

    def _find_grid_index(self, price: float) -> int:
        """找到价格所在的网格索引，-1表示超出范围"""
        for i in range(len(self.grid_lines) - 1):
            lower_grid = self.grid_lines[i]
            upper_grid = self.grid_lines[i + 1]
            if lower_grid <= price <= upper_grid:
                return i
        return -1

    def _execute_grid_trade(self, trigger_price: float, current_price: float,
                          action: str, current_date):
        """执行网格交易（修复版：添加持仓上限检查）"""
        current_pos = self.getposition(self.data).size

        if action == 'buy':
            if not self.order:
                size = self.params.position_size
                # 检查持仓上限（如果有定义）
                max_pos = getattr(self.params, 'max_position', 15000)
                if current_pos + size > max_pos:
                    if current_pos < max_pos:
                        size = max_pos - current_pos
                    else:
                        return
                self.order = self.buy(size=size)
                self.trade_log.append({
                    'date': current_date,
                    'action': 'buy',
                    'price': current_price,
                    'size': size,
                    'trigger_price': trigger_price
                })

        elif action == 'sell':
            if not self.order and current_pos > 0:
                size = min(self.params.position_size, current_pos)
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
