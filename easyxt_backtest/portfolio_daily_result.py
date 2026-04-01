# -*- coding: utf-8 -*-
"""
每日盯市盈亏计算

参考vnpy的设计，实现逐日盯市的盈亏计算。
"""
from typing import Dict, List
from datetime import date, datetime
from dataclasses import dataclass, field
import pandas as pd


@dataclass
class TradeRecord:
    """成交记录"""
    symbol: str
    direction: str  # 'long' or 'short'
    volume: float
    price: float
    datetime: datetime
    commission: float = 0.0


@dataclass
class PositionRecord:
    """持仓记录"""
    symbol: str
    volume: float  # 持仓数量（正数为多头，负数为空头）
    last_price: float = 0.0  # 上次结算价
    avg_price: float = 0.0  # 平均开仓价


class PortfolioDailyResult:
    """
    组合每日盈亏结果

    功能：
    1. 记录每日交易
    2. 计算持仓盈亏
    3. 计算交易盈亏
    4. 计算总盈亏和净盈亏
    """

    def __init__(self, result_date: date, close_prices: Dict[str, float]):
        """
        初始化

        Args:
            result_date: 日期
            close_prices: 收盘价字典 {symbol: close_price}
        """
        self.date: date = result_date
        self.close_prices: Dict[str, float] = close_prices.copy()
        self.pre_closes: Dict[str, float] = {}  # 昨收价
        self.start_positions: Dict[str, float] = {}  # 期初持仓
        self.end_positions: Dict[str, float] = {}  # 期末持仓

        # 成交记录
        self.trades: List[TradeRecord] = []

        # 盈亏数据
        self.trade_count: int = 0  # 成交笔数
        self.turnover: float = 0.0  # 成交金额
        self.commission: float = 0.0  # 手续费

        self.holding_pnl: float = 0.0  # 持仓盈亏
        self.trading_pnl: float = 0.0  # 交易盈亏
        self.total_pnl: float = 0.0  # 总盈亏
        self.net_pnl: float = 0.0  # 净盈亏（扣除手续费）

    def add_trade(self, trade: TradeRecord) -> None:
        """添加成交记录"""
        self.trades.append(trade)

    def calculate_pnl(self,
                     pre_closes: Dict[str, float],
                     start_positions: Dict[str, float],
                     commission_rate: float = 0.0003) -> None:
        """
        计算盈亏

        Args:
            pre_closes: 昨收价字典
            start_positions: 期初持仓字典
            commission_rate: 佣金率（默认万三）
        """
        self.pre_closes = pre_closes.copy()
        self.start_positions = start_positions.copy()
        self.end_positions = start_positions.copy()

        # 1. 计算持仓盈亏（盯市盈亏）
        # 持仓盈亏 = 持仓量 × (今收 - 昨收)
        self.holding_pnl = 0.0
        for symbol, pos in start_positions.items():
            if symbol not in self.close_prices:
                continue

            close_price = self.close_prices[symbol]
            pre_close = pre_closes.get(symbol, close_price)  # 如果没有昨收，用今收代替

            # 持仓盈亏
            self.holding_pnl += pos * (close_price - pre_close)

        # 2. 计算交易盈亏和手续费
        self.trade_count = len(self.trades)
        self.trading_pnl = 0.0
        self.turnover = 0.0
        self.commission = 0.0

        for trade in self.trades:
            symbol = trade.symbol
            direction = trade.direction
            volume = trade.volume
            price = trade.price

            if symbol not in self.close_prices:
                continue

            close_price = self.close_prices[symbol]

            # 计算成交金额
            trade_turnover = price * volume
            self.turnover += trade_turnover

            # 计算手续费
            trade_commission = trade_turnover * commission_rate
            self.commission += trade_commission

            # 更新持仓
            if direction == 'long':
                self.end_positions[symbol] = self.end_positions.get(symbol, 0) + volume
                # 买入盈亏 = (今收 - 买入价) × 数量
                self.trading_pnl += volume * (close_price - price)
            else:  # 'short'
                self.end_positions[symbol] = self.end_positions.get(symbol, 0) - volume
                # 卖出盈亏 = (卖出价 - 今收) × 数量
                self.trading_pnl += volume * (price - close_price)

        # 3. 计算总盈亏和净盈亏
        self.total_pnl = self.holding_pnl + self.trading_pnl
        self.net_pnl = self.total_pnl - self.commission

    def update_close_prices(self, close_prices: Dict[str, float]) -> None:
        """更新收盘价"""
        self.close_prices.update(close_prices)


class DailyResultManager:
    """
    每日结果管理器

    管理整个回测期间的每日盈亏结果。
    """

    def __init__(self, initial_cash: float = 1000000):
        """
        初始化

        Args:
            initial_cash: 初始资金
        """
        self.initial_cash = initial_cash
        self.daily_results: Dict[date, PortfolioDailyResult] = {}

    def get_or_create_result(self, dt: datetime, close_prices: Dict[str, float]) -> PortfolioDailyResult:
        """获取或创建当日结果"""
        result_date = dt.date()
        if result_date not in self.daily_results:
            self.daily_results[result_date] = PortfolioDailyResult(result_date, close_prices)
        else:
            # 更新收盘价
            self.daily_results[result_date].update_close_prices(close_prices)

        return self.daily_results[result_date]

    def calculate_all(self, positions_history: Dict[datetime, Dict[str, float]],
                     trades_history: Dict[datetime, List[TradeRecord]],
                     commission_rate: float = 0.0003) -> pd.DataFrame:
        """
        计算所有日期的盈亏

        Args:
            positions_history: 持仓历史 {datetime: {symbol: position}}
            trades_history: 成交历史 {datetime: [TradeRecord]}
            commission_rate: 佣金率

        Returns:
            DataFrame with columns: date, trade_count, turnover, commission,
                                  holding_pnl, trading_pnl, total_pnl, net_pnl, balance
        """
        if not self.daily_results:
            return pd.DataFrame()

        # 排序日期
        sorted_dates = sorted(self.daily_results.keys())

        pre_closes = {}
        start_positions = {}

        results = []

        for result_date in sorted_dates:
            daily_result = self.daily_results[result_date]

            # 添加成交记录
            if result_date in trades_history:
                for trade in trades_history[result_date]:
                    daily_result.add_trade(trade)

            # 设置期初持仓
            if result_date in positions_history:
                start_positions = positions_history[result_date]

            # 计算盈亏
            daily_result.calculate_pnl(pre_closes, start_positions, commission_rate)

            # 更新昨收价和期初持仓为今天的
            pre_closes = daily_result.close_prices.copy()
            start_positions = daily_result.end_positions.copy()

            results.append({
                'date': result_date,
                'trade_count': daily_result.trade_count,
                'turnover': daily_result.turnover,
                'commission': daily_result.commission,
                'holding_pnl': daily_result.holding_pnl,
                'trading_pnl': daily_result.trading_pnl,
                'total_pnl': daily_result.total_pnl,
                'net_pnl': daily_result.net_pnl,
            })

        df = pd.DataFrame(results)

        # 计算每日余额
        if not df.empty:
            df['balance'] = df['net_pnl'].cumsum() + self.initial_cash

        return df

    def calculate_statistics(self, daily_df: pd.DataFrame, annual_days: int = 240) -> Dict:
        """
        计算统计指标

        Args:
            daily_df: 每日盈亏DataFrame
            annual_days: 年化交易日数

        Returns:
            统计指标字典
        """
        if daily_df is None or daily_df.empty:
            return {}

        # 计算回撤
        daily_df = daily_df.copy()
        daily_df['highlevel'] = daily_df['balance'].cummax()
        daily_df['drawdown'] = daily_df['balance'] - daily_df['highlevel']
        daily_df['ddpercent'] = (daily_df['balance'] / daily_df['highlevel'] - 1) * 100

        # 统计数据
        start_date = daily_df['date'].iloc[0]
        end_date = daily_df['date'].iloc[-1]
        total_days = len(daily_df)
        profit_days = (daily_df['net_pnl'] > 0).sum()
        loss_days = (daily_df['net_pnl'] < 0).sum()

        end_balance = daily_df['balance'].iloc[-1]
        max_drawdown = daily_df['drawdown'].min()
        max_ddpercent = daily_df['ddpercent'].min()

        # 最大回撤持续时间
        max_dd_idx = daily_df['drawdown'].argmin()
        max_dd_end = daily_df['date'].iloc[max_dd_idx]
        max_dd_start_idx = daily_df['balance'].iloc[:max_dd_idx+1].argmax()
        max_dd_start = daily_df['date'].iloc[max_dd_start_idx]
        max_drawdown_duration = (max_dd_end - max_dd_start).days

        # 收益率
        total_net_pnl = daily_df['net_pnl'].sum()
        total_return = (end_balance / self.initial_cash - 1) * 100
        annual_return = total_return / total_days * annual_days

        # 波动率和夏普比率
        daily_returns = daily_df['balance'].pct_change().dropna()
        daily_return_mean = daily_returns.mean() * 100
        return_std = daily_returns.std() * 100

        if return_std > 0:
            sharpe_ratio = daily_return_mean / return_std * (annual_days ** 0.5)
        else:
            sharpe_ratio = 0.0

        # 收益回撤比
        if max_drawdown != 0:
            return_drawdown_ratio = -total_net_pnl / max_drawdown
        else:
            return_drawdown_ratio = 0.0

        return {
            'start_date': start_date,
            'end_date': end_date,
            'total_days': total_days,
            'profit_days': int(profit_days),
            'loss_days': int(loss_days),
            'initial_cash': self.initial_cash,
            'end_balance': end_balance,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'max_ddpercent': max_ddpercent,
            'max_drawdown_duration': max_drawdown_duration,
            'total_net_pnl': total_net_pnl,
            'daily_net_pnl': total_net_pnl / total_days if total_days > 0 else 0,
            'total_commission': daily_df['commission'].sum(),
            'total_turnover': daily_df['turnover'].sum(),
            'total_trade_count': int(daily_df['trade_count'].sum()),
            'sharpe_ratio': sharpe_ratio,
            'return_drawdown_ratio': return_drawdown_ratio,
        }
