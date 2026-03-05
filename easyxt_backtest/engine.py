# -*- coding: utf-8 -*-
"""
回测引擎 - 核心执行逻辑
"""
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from data_manager import DataManager
from strategy_base import StrategyBase
from performance import PerformanceAnalyzer


@dataclass
class Trade:
    """交易记录"""
    date: str
    symbol: str
    direction: str  # 'buy' or 'sell'
    volume: int
    price: float
    amount: float
    commission: float
    net_amount: float  # 扣除手续费后的净额


@dataclass
class PortfolioSnapshot:
    """持仓快照"""
    date: str
    cash: float
    positions: Dict[str, int]  # {symbol: volume}
    market_value: float  # 持仓市值
    total_value: float  # 总资产（现金+持仓）


@dataclass
class BacktestResult:
    """回测结果"""
    trades: pd.DataFrame  # 所有交易记录
    portfolio_history: pd.DataFrame  # 每日持仓历史
    returns: pd.Series  # 每日收益率
    performance: dict  # 性能指标

    def print_summary(self):
        """打印回测结果摘要"""
        print("\n" + "="*70)
        print("回测结果摘要")
        print("="*70)

        perf = self.performance
        print(f"\n【收益指标】")
        print(f"  总收益率:     {perf.get('total_return', 0):.2%}")
        print(f"  年化收益率:   {perf.get('annual_return', 0):.2%}")
        print(f"  初始资金:     {perf.get('initial_cash', 0):,.2f} 元")
        print(f"  最终资金:     {perf.get('final_value', 0):,.2f} 元")

        print(f"\n【风险指标】")
        print(f"  最大回撤:     {perf.get('max_drawdown', 0):.2%}")
        print(f"  波动率:       {perf.get('volatility', 0):.2%}")
        print(f"  夏普比率:     {perf.get('sharpe_ratio', 0):.2f}")

        print(f"\n【交易统计】")
        print(f"  总交易次数:   {len(self.trades)}")
        print(f"  交易天数:     {len(self.portfolio_history)}")

        print("\n" + "="*70)


class BacktestEngine:
    """
    回测引擎

    功能：
    - 执行回测主循环
    - 管理持仓和资金
    - 模拟交易执行
    - 记录交易历史
    - 计算性能指标
    """

    def __init__(self,
                 initial_cash: float = 1000000,
                 commission: float = 0.001,
                 slippage: float = 0.0,
                 data_manager: Optional[DataManager] = None):
        """
        初始化回测引擎

        Args:
            initial_cash: 初始资金
            commission: 佣金率（默认0.1%）
            slippage: 滑点率（默认0%）
            data_manager: 数据管理器
        """
        self.initial_cash = initial_cash
        self.commission = commission
        self.slippage = slippage

        # 数据管理器
        if data_manager is None:
            data_manager = DataManager()
        self.data_manager = data_manager

        # 性能分析器
        self.performance_analyzer = PerformanceAnalyzer()

        # 回测状态
        self.cash = initial_cash
        self.positions = {}  # {symbol: volume}
        self.current_date = None

        # 记录
        self.trade_history = []  # List[Trade]
        self.portfolio_history = []  # List[PortfolioSnapshot]
        self.daily_values = []  # [(date, total_value)]

        # ✨ 退市损失追踪
        self.delisted_stocks = {}  # {symbol: {'buy_dates': [date], 'buy_prices': [price], 'volumes': [volume], 'sell_date': date, 'sell_price': float, 'loss': float}}
        self.delisted_total_loss = 0.0  # 退市总损失
        self.position_costs = {}  # {symbol: {'total_cost': float, 'total_volume': int}} - 用于追踪持仓成本

    # ==================== 主回测循环 ====================

    def run_backtest(self,
                    strategy: StrategyBase,
                    start_date: str,
                    end_date: str) -> BacktestResult:
        """
        运行回测

        Args:
            strategy: 策略实例
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            BacktestResult
        """
        print(f"\n{'='*70}")
        print(f"开始回测: {start_date} ~ {end_date}")
        print(f"{'='*70}")

        # 重置状态
        self._reset()

        # 注入data_manager到策略
        strategy.data_manager = self.data_manager

        # 获取调仓日期
        rebalance_dates = strategy.get_rebalance_dates(start_date, end_date)
        print(f"\n调仓日期: {len(rebalance_dates)} 个")
        for i, date in enumerate(rebalance_dates, 1):
            print(f"  {i}. {date}")

        # 获取所有交易日（用于计算每日净值）
        all_trading_days = self.data_manager.get_trading_dates(start_date, end_date)

        # 执行回测
        last_rebalance_idx = 0

        for i, trade_date in enumerate(all_trading_days):
            self.current_date = trade_date

            # 检查是否需要调仓
            if trade_date in rebalance_dates:
                print(f"\n[{trade_date}] 调仓...")

                # 选股
                selected_stocks = strategy.select_stocks(trade_date)
                print(f"  选中股票: {len(selected_stocks)} 只")

                if not selected_stocks:
                    print("  [WARNING] 未选中任何股票，跳过调仓")
                    self._record_portfolio(trade_date)
                    continue

                # 获取目标权重
                target_weights = strategy.get_target_weights(trade_date, selected_stocks)
                print(f"  目标权重: {len(target_weights)} 只")

                if not target_weights:
                    print("  [WARNING] 目标权重为空，清仓")
                    self._sell_all(trade_date)
                else:
                    # 执行调仓
                    self._rebalance(trade_date, target_weights)

            # 记录每日持仓
            self._record_portfolio(trade_date)

        # 计算最终结果
        result = self._calculate_result(all_trading_days)

        return result

    def _reset(self):
        """重置回测状态"""
        self.cash = self.initial_cash
        self.positions = {}
        self.current_date = None
        self.trade_history = []
        self.portfolio_history = []
        self.daily_values = []

        # ✨ 重置退市损失追踪
        self.delisted_stocks = {}
        self.delisted_total_loss = 0.0
        self.position_costs = {}

    def _rebalance(self, date: str, target_weights: Dict[str, float]):
        """
        执行调仓

        Args:
            date: 调仓日期
            target_weights: 目标权重 {symbol: weight}
        """
        # 1. 计算当前总资产
        current_value = self._get_total_value(date)
        print(f"  当前总资产: {current_value:,.2f}")

        # 2. 处理退市股票（使用最后交易日价格强制卖出）
        to_sell_delisted = []
        for code in list(self.positions.keys()):  # 使用list()避免迭代时修改字典
            current_price = self.data_manager.get_nearest_price(code, date)

            if current_price is None:
                # 当前无价格，检查是否退市
                last_trade_info = self.data_manager.get_last_trade_date_and_price(code, date)

                if last_trade_info is not None:
                    last_date, last_price = last_trade_info

                    if last_price is not None:
                        # 已退市，使用最后价格强制卖出
                        volume = self.positions[code]
                        loss_amount = last_price * volume

                        print(f"    [DELISTED] {code} 已退市({last_date}最后价格{last_price:.2f})，强制卖出{volume}股")
                        print(f"              损失约: {loss_amount:,.2f} 元")

                        # 使用最后价格执行卖出
                        self._sell_with_price(code, date, volume, last_price, is_delisted=True)
                        to_sell_delisted.append(code)
                    else:
                        # 无历史价格，清零持仓（模拟血本无归）
                        volume = self.positions[code]
                        print(f"    [DELISTED] {code} 已退市且无价格数据，清零持仓{volume}股（血本无归）")
                        print(f"              损失: {volume}股（无法估值）")

                        # 从positions中移除，但不增加资金（血本无归）
                        del self.positions[code]
                        to_sell_delisted.append(code)

        # 3. 卖出不在目标中的股票
        to_sell = [code for code in self.positions if code not in target_weights]
        if to_sell:
            print(f"  卖出: {len(to_sell)} 只")
            for code in to_sell:
                self._sell(code, date, self.positions[code])

        # 3. 买入目标股票
        print(f"  买入/调整: {len(target_weights)} 只")
        for code, target_weight in target_weights.items():
            target_value = current_value * target_weight

            # 获取当前持仓
            current_volume = self.positions.get(code, 0)
            current_price = self.data_manager.get_nearest_price(code, date)

            if current_price is None:
                print(f"    [SKIP] {code} 无法获取价格")
                continue

            # 计算当前持仓市值
            current_stock_value = current_volume * current_price

            # 计算需要调整的金额
            diff_value = target_value - current_stock_value

            if abs(diff_value) < current_price * 100:  # 差额小于1手，忽略
                if current_volume > 0:
                    print(f"    [OK] {code} 持仓已达标 ({current_volume}股)")
                continue

            if diff_value > 0:
                # 需要买入
                buy_amount = diff_value
                buy_volume = int(buy_amount / current_price / 100) * 100  # 整手
                if buy_volume > 0:
                    self._buy(code, date, buy_volume)
            else:
                # 需要卖出
                sell_volume = int(abs(diff_value) / current_price / 100) * 100
                sell_volume = min(sell_volume, current_volume)  # 不能超过持仓
                if sell_volume > 0:
                    self._sell(code, date, sell_volume)

    # ==================== 交易执行 ====================

    def _buy(self, symbol: str, date: str, volume: int):
        """
        买入

        Args:
            symbol: 股票代码
            date: 日期
            volume: 买入股数（整手）
        """
        price = self.data_manager.get_nearest_price(symbol, date)

        if price is None:
            print(f"    [FAIL] {symbol} 买入失败 - 无价格数据")
            return

        # 计算滑点
        execution_price = price * (1 + self.slippage)

        # 计算金额
        amount = execution_price * volume
        commission = max(amount * self.commission, 5)  # 最低5元
        net_amount = amount + commission

        # 检查资金
        if net_amount > self.cash:
            print(f"    [FAIL] {symbol} 资金不足 (需要{net_amount:,.2f}, 可用{self.cash:,.2f})")
            return

        # 扣除资金
        self.cash -= net_amount

        # 增加持仓
        self.positions[symbol] = self.positions.get(symbol, 0) + volume

        # ✨ 记录持仓成本（用于计算退市损失）
        cost = amount + commission  # 总成本（含手续费）
        if symbol not in self.position_costs:
            self.position_costs[symbol] = {'total_cost': 0.0, 'total_volume': 0}
        self.position_costs[symbol]['total_cost'] += cost
        self.position_costs[symbol]['total_volume'] += volume

        # 记录交易
        trade = Trade(
            date=date,
            symbol=symbol,
            direction='buy',
            volume=volume,
            price=execution_price,
            amount=amount,
            commission=commission,
            net_amount=net_amount
        )
        self.trade_history.append(trade)

        print(f"    [BUY] {symbol} {volume}股 @ {execution_price:.2f} 元")

    def _sell(self, symbol: str, date: str, volume: int):
        """
        卖出

        Args:
            symbol: 股票代码
            date: 日期
            volume: 卖出股数
        """
        if symbol not in self.positions or self.positions[symbol] < volume:
            print(f"    [FAIL] {symbol} 卖出失败 - 持仓不足")
            return

        price = self.data_manager.get_nearest_price(symbol, date)

        if price is None:
            print(f"    [FAIL] {symbol} 卖出失败 - 无价格数据")
            return

        # 计算滑点
        execution_price = price * (1 - self.slippage)

        # 计算金额
        amount = execution_price * volume
        commission = max(amount * self.commission, 5)  # 最低5元
        net_amount = amount - commission

        # 增加资金
        self.cash += net_amount

        # 减少持仓
        self.positions[symbol] -= volume
        if self.positions[symbol] == 0:
            del self.positions[symbol]

        # ✨ 更新持仓成本（按比例减少）
        if symbol in self.position_costs:
            cost_ratio = volume / (volume + self.positions.get(symbol, 0))
            cost_to_reduce = self.position_costs[symbol]['total_cost'] * cost_ratio
            self.position_costs[symbol]['total_cost'] -= cost_to_reduce
            self.position_costs[symbol]['total_volume'] -= volume

            # 如果持仓清零，清除成本记录
            if symbol not in self.positions:
                del self.position_costs[symbol]

        # 记录交易
        trade = Trade(
            date=date,
            symbol=symbol,
            direction='sell',
            volume=volume,
            price=execution_price,
            amount=amount,
            commission=commission,
            net_amount=net_amount
        )
        self.trade_history.append(trade)

        print(f"    [SELL] {symbol} {volume}股 @ {execution_price:.2f} 元")

    def _sell_with_price(self, symbol: str, date: str, volume: int, force_price: float, is_delisted: bool = False):
        """
        使用指定价格卖出（用于退市股票处理）

        Args:
            symbol: 股票代码
            date: 日期
            volume: 卖出股数
            force_price: 强制使用的价格
            is_delisted: 是否为退市股票
        """
        if symbol not in self.positions or self.positions[symbol] < volume:
            print(f"    [FAIL] {symbol} 卖出失败 - 持仓不足")
            return

        # 直接使用指定价格，不计算滑点
        execution_price = force_price

        # 计算金额
        amount = execution_price * volume
        commission = max(amount * self.commission, 5)  # 最低5元
        net_amount = amount - commission

        # 增加资金
        self.cash += net_amount

        # 减少持仓
        self.positions[symbol] -= volume
        if self.positions[symbol] == 0:
            del self.positions[symbol]

        # ✨ 如果是退市股票，计算并记录损失
        if is_delisted and symbol in self.position_costs:
            # 计算平均成本
            avg_cost_price = self.position_costs[symbol]['total_cost'] / self.position_costs[symbol]['total_volume']

            # 计算损失
            total_cost = avg_cost_price * volume
            total_revenue = net_amount
            loss = total_cost - total_revenue  # 正数表示损失

            # 记录退市信息
            self.delisted_stocks[symbol] = {
                'buy_avg_price': avg_cost_price,
                'sell_date': date,
                'sell_price': execution_price,
                'volume': volume,
                'total_cost': total_cost,
                'total_revenue': total_revenue,
                'loss': loss,
                'loss_pct': (loss / total_cost * 100) if total_cost > 0 else 0
            }

            self.delisted_total_loss += loss

            # 清除持仓成本记录
            del self.position_costs[symbol]

        # 记录交易（标记为退市卖出）
        direction = 'sell_delisted' if is_delisted else 'sell'
        trade = Trade(
            date=date,
            symbol=symbol,
            direction=direction,
            volume=volume,
            price=execution_price,
            amount=amount,
            commission=commission,
            net_amount=net_amount
        )
        self.trade_history.append(trade)

        if is_delisted:
            loss_info = self.delisted_stocks.get(symbol, {})
            if loss_info:
                print(f"    [SELL_DELISTED] {symbol} {volume}股 @ {execution_price:.2f} 元（退市处理）")
                print(f"                   买入均价: {loss_info['buy_avg_price']:.2f} 元")
                print(f"                   亏损: {loss_info['loss']:,.2f} 元 ({loss_info['loss_pct']:.1f}%)")
            else:
                print(f"    [SELL_DELISTED] {symbol} {volume}股 @ {execution_price:.2f} 元（退市处理）")
        else:
            print(f"    [SELL] {symbol} {volume}股 @ {execution_price:.2f} 元")

    def _sell_all(self, date: str):
        """清仓"""
        for symbol in list(self.positions.keys()):
            self._sell(symbol, date, self.positions[symbol])

    # ==================== 持仓管理 ====================

    def _get_total_value(self, date: str) -> float:
        """获取总资产（现金+持仓市值）"""
        market_value = self._get_market_value(date)
        return self.cash + market_value

    def _get_market_value(self, date: str) -> float:
        """获取持仓市值"""
        total = 0.0
        for symbol, volume in self.positions.items():
            price = self.data_manager.get_nearest_price(symbol, date)
            if price:
                total += price * volume
            else:
                # ✨ 警告：无法获取价格的股票不计入市值（但持仓仍在）
                # 这种情况应该在下一次调仓时被卖出
                print(f"    [WARNING] {symbol} 持仓{volume}股无法估值（无价格数据）")
        return total

    def _record_portfolio(self, date: str):
        """记录持仓快照"""
        market_value = self._get_market_value(date)
        total_value = self.cash + market_value

        snapshot = PortfolioSnapshot(
            date=date,
            cash=self.cash,
            positions=self.positions.copy(),
            market_value=market_value,
            total_value=total_value
        )

        self.portfolio_history.append(snapshot)
        self.daily_values.append((date, total_value))

    # ==================== 结果计算 ====================

    def _calculate_result(self, trading_days: List[str]) -> BacktestResult:
        """计算回测结果"""
        # 1. 交易记录DataFrame
        trades_df = pd.DataFrame([
            {
                'date': t.date,
                'symbol': t.symbol,
                'direction': t.direction,
                'volume': t.volume,
                'price': t.price,
                'amount': t.amount,
                'commission': t.commission,
                'net_amount': t.net_amount
            }
            for t in self.trade_history
        ])

        if not trades_df.empty:
            trades_df.set_index('date', inplace=True)

        # 2. 持仓历史DataFrame
        portfolio_df = pd.DataFrame([
            {
                'date': p.date,
                'cash': p.cash,
                'market_value': p.market_value,
                'total_value': p.total_value,
                'position_count': len(p.positions)
            }
            for p in self.portfolio_history
        ])

        if not portfolio_df.empty:
            portfolio_df.set_index('date', inplace=True)

        # 3. 计算每日收益率
        returns = self._calculate_returns(trading_days)

        # 4. 计算性能指标
        performance = self.performance_analyzer.analyze(
            returns=returns,
            initial_cash=self.initial_cash
        )

        # ✨ 添加退市损失统计
        performance['delisted_stocks_count'] = len(self.delisted_stocks)
        performance['delisted_total_loss'] = self.delisted_total_loss
        performance['delisted_stocks'] = self.delisted_stocks

        # 打印退市损失统计
        if self.delisted_stocks:
            print(f"\n{'='*70}")
            print(f"【退市股票统计】")
            print(f"  退市股票数量: {len(self.delisted_stocks)} 只")
            print(f"  退市总损失:   {self.delisted_total_loss:,.2f} 元")
            print(f"  损失占比:     {self.delisted_total_loss / self.initial_cash * 100:.2f}%")
            print(f"\n  退市详情:")
            for i, (symbol, info) in enumerate(self.delisted_stocks.items(), 1):
                print(f"    {i}. {symbol}")
                print(f"       买入均价: {info['buy_avg_price']:.2f} 元")
                print(f"       卖出日期: {info['sell_date']} (退市)")
                print(f"       卖出价格: {info['sell_price']:.2f} 元")
                print(f"       亏损:     {info['loss']:,.2f} 元 ({info['loss_pct']:.1f}%)")
            print(f"{'='*70}")

        return BacktestResult(
            trades=trades_df,
            portfolio_history=portfolio_df,
            returns=returns,
            performance=performance
        )

    def _calculate_returns(self, trading_days: List[str]) -> pd.Series:
        """计算每日收益率"""
        # 构建日期到总价值的映射
        value_dict = {date: value for date, value in self.daily_values}

        # 构建完整的每日净值序列
        values = []
        dates = []

        for date in trading_days:
            if date in value_dict:
                values.append(value_dict[date])
                dates.append(date)
            elif len(values) > 0:
                # 如果当天没有记录（可能是非交易日），使用前一天的值
                values.append(values[-1])
                dates.append(date)

        if not values:
            return pd.Series()

        # 计算收益率
        values_series = pd.Series(values, index=dates)
        returns = values_series.pct_change().fillna(0)

        return returns
