# -*- coding: utf-8 -*-
"""
增强回测引擎 - 自建回测框架（参考vnpy设计）

完全独立于Backtrader的自建回测引擎，集成：
1. PositionManager - 目标仓位管理
2. DailyResultManager - 每日盯市计算
3. 事件驱动架构（参考vnpy）
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, date
import warnings

warnings.filterwarnings('ignore')

# 导入新功能
from easyxt_backtest.portfolio_daily_result import DailyResultManager, TradeRecord
from easyxt_backtest.position_manager import PositionManager


class EnhancedBacktestResult:
    """增强回测结果（兼容BacktestEngine格式）"""

    def __init__(self, trades, portfolio_history, returns, performance,
                 position_manager=None, trades_history=None,
                 positions_history=None, statistics=None):
        """
        初始化回测结果

        Args:
            trades: 交易记录DataFrame
            portfolio_history: 组合历史DataFrame
            returns: 每日收益DataFrame
            performance: 性能指标字典
            position_manager: 仓位管理器（增强功能）
            trades_history: 交易历史（增强功能）
            positions_history: 持仓历史（增强功能）
            statistics: 统计指标（增强功能）
        """
        self.trades = trades
        self.portfolio_history = portfolio_history
        self.returns = returns
        self.performance = performance

        # 增强功能数据
        self.position_manager = position_manager
        self.trades_history = trades_history or {}
        self.positions_history = positions_history or {}
        self.statistics = statistics or {}

    def print_summary(self):
        """打印结果摘要"""
        print(f"\n{'='*70}")
        print(f"回测结果摘要（增强引擎）")
        print(f"{'='*70}")

        perf = self.performance
        print(f"\n【收益指标】")
        print(f"  总收益率:     {perf.get('total_return', 0):.2%}")
        print(f"  年化收益率:   {perf.get('annual_return', 0):.2%}")
        print(f"  初始资金:     {perf.get('initial_cash', 0):,.2f}")
        print(f"  最终资金:     {perf.get('final_value', 0):,.2f}")

        print(f"\n【风险指标】")
        print(f"  最大回撤:     {perf.get('max_drawdown', 0):.2%}")
        sharpe = perf.get('sharpe_ratio', 0)
        if sharpe:
            print(f"  夏普比率:     {sharpe:.2f}")
        else:
            print(f"  夏普比率:     N/A")

        print(f"\n【交易统计】")
        print(f"  总交易次数:   {len(self.trades) if not self.trades.empty else 0}")
        print(f"  交易天数:     {len(self.portfolio_history) if not self.portfolio_history.empty else 0}")

        print(f"{'='*70}\n")

    def get_portfolio_summary(self, date: datetime = None) -> Dict:
        """
        获取组合摘要（增强功能）

        Args:
            date: 日期，None表示最新

        Returns:
            组合摘要字典
        """
        if not self.position_manager:
            return {}

        return self.position_manager.get_portfolio_summary()

    def print_daily_results(self, top_n: int = 10):
        """打印每日盈亏TOP N（增强功能）"""
        if self.returns is None or self.returns.empty:
            print("\n无每日盈亏数据")
            return

        print(f"\n{'='*80}")
        print(f"每日盈亏 TOP {top_n}")
        print(f"{'='*80}\n")

        # 按净盈亏排序
        df = self.returns.nlargest(top_n, 'net_pnl')

        for idx, row in df.iterrows():
            print(f"  {row['date'].strftime('%Y-%m-%d')}: "
                  f"{'+' if row['net_pnl'] >= 0 else ''}{row['net_pnl']:,.2f} "
                  f"({row['total_pnl']:.2f} - {row['commission']:.2f})")

        print(f"\n{'='*80}\n")


class EnhancedBacktestEngine:
    """
    增强回测引擎

    集成了每日盯市和目标仓位管理功能。
    """

    def __init__(self,
                 initial_cash: float = 1000000,
                 commission: float = 0.001,
                 slippage: float = 0.0,
                 data_manager=None):
        """
        初始化回测引擎

        Args:
            initial_cash: 初始资金
            commission: 佣金率
            slippage: 滑点
            data_manager: 数据管理器
        """
        self.initial_cash = initial_cash
        self.commission = commission
        self.slippage = slippage
        self.data_manager = data_manager

        # 新增：仓位管理器
        self.position_manager = PositionManager(initial_cash)

        # 新增：每日结果管理器
        self.daily_result_manager = DailyResultManager(initial_cash)

        # 历史数据
        self.positions_history: Dict[datetime, Dict[str, float]] = {}
        self.trades_history: Dict[datetime, List[TradeRecord]] = {}
        self.prices_history: Dict[datetime, Dict[str, float]] = {}

    def run_backtest(self,
                     strategy,
                     start_date: str,
                     end_date: str) -> Dict:
        """
        运行回测（参考vnpy逐日遍历设计）

        核心流程：
        1. 获取交易日历和调仓日期
        2. 遍历每个调仓日执行选股和交易
        3. 遍历每个交易日计算每日净值（逐日盯市）
        4. 计算统计指标

        Args:
            strategy: 策略实例
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            回测结果字典
        """
        print(f"\n{'='*80}")
        print(f"  增强回测引擎")
        print(f"{'='*80}")
        print(f"  策略: {strategy.name if hasattr(strategy, 'name') else 'Unknown'}")
        print(f"  期间: {start_date} - {end_date}")
        print(f"  初始资金: {self.initial_cash:,.2f}")
        print(f"  佣金: {self.commission:.2%}")

        # ========== 阶段1：准备数据 ==========
        # 获取交易日历
        trading_dates = []
        if self.data_manager and hasattr(self.data_manager, 'get_trading_dates'):
            trading_dates = self.data_manager.get_trading_dates(start_date, end_date)
        if not trading_dates:
            print("[WARN] 无法获取交易日历")
            return self._empty_result()

        print(f"  [OK] 获取交易日: {len(trading_dates)} 个")

        # 获取调仓日期
        rebalance_dates = strategy.get_rebalance_dates(start_date, end_date)
        rebalance_set = set(rebalance_dates)
        print(f"  调仓次数: {len(rebalance_dates)}")

        # ========== 阶段2：执行调仓 ==========
        # 记录每次调仓后的持仓快照 {rebalance_date_str: {symbol: volume}}
        rebalance_positions: Dict[str, Dict[str, float]] = {}
        # 记录每次调仓后的现金
        rebalance_cash: Dict[str, float] = {}
        # 记录交易历史
        all_trade_records: List[Dict] = []

        for i, rebalance_date in enumerate(rebalance_dates, 1):
            print(f"\n[INFO] 调仓 {i}/{len(rebalance_dates)}: {rebalance_date}")

            dt = datetime.strptime(rebalance_date, '%Y%m%d')

            # 2.1 选股
            selected_stocks = strategy.select_stocks(rebalance_date)
            print(f"[INFO] 选中股票: {len(selected_stocks)} 只")

            if not selected_stocks:
                print("[WARN] 未选中股票，跳过本次调仓")
                # 保持上一次的持仓
                if rebalance_positions:
                    last_date = max(rebalance_positions.keys())
                    rebalance_positions[rebalance_date] = rebalance_positions[last_date].copy()
                    rebalance_cash[rebalance_date] = rebalance_cash[last_date]
                continue

            # 2.2 获取目标权重
            target_weights = strategy.get_target_weights(rebalance_date, selected_stocks)
            print(f"[INFO] 目标权重: {len(target_weights)} 只")

            if not target_weights:
                print("[WARN] 目标权重为空，跳过本次调仓")
                if rebalance_positions:
                    last_date = max(rebalance_positions.keys())
                    rebalance_positions[rebalance_date] = rebalance_positions[last_date].copy()
                    rebalance_cash[rebalance_date] = rebalance_cash[last_date]
                continue

            # 2.3 获取当前价格
            current_prices = self._get_current_prices(
                list(target_weights.keys()) + list(self.position_manager.positions.keys()),
                rebalance_date
            )

            if not current_prices:
                print(f"[WARN] 无法获取价格数据，跳过本次调仓")
                if rebalance_positions:
                    last_date = max(rebalance_positions.keys())
                    rebalance_positions[rebalance_date] = rebalance_positions[last_date].copy()
                    rebalance_cash[rebalance_date] = rebalance_cash[last_date]
                continue

            # 2.4 更新市值
            for symbol, price in current_prices.items():
                self.position_manager.update_market_value(symbol, price)

            # 2.5 设置目标权重
            total_value = self.position_manager.get_total_value()
            self.position_manager.set_target_weights(
                target_weights,
                total_value,
                current_prices
            )

            # 2.6 执行调仓
            executed_orders = self.position_manager.execute_rebalance(
                current_prices,
                price_tolerance=0.001
            )

            # 2.7 记录交易
            trades = []
            for order in executed_orders:
                trade = TradeRecord(
                    symbol=order['symbol'],
                    direction='long' if order['action'] == 'buy' else 'short',
                    volume=order['volume'],
                    price=order['price'],
                    datetime=dt,
                    commission=order['volume'] * order['price'] * self.commission
                )
                trades.append(trade)

                print(f"  [TRADE] {order['action'].upper():4} {order['symbol']} "
                      f"{order['volume']:.0f} shares @ {order['price']:.2f}")

            # 2.8 记录调仓后的持仓快照和现金（过滤微小残余仓位）
            rebalance_positions[rebalance_date] = {
                s: v for s, v in self.position_manager.positions.items()
                if v >= 100  # 至少1手（100股）
            }
            rebalance_cash[rebalance_date] = self.position_manager.cash

            # 记录到历史
            self.trades_history[dt] = trades
            self.positions_history[dt] = self.position_manager.positions.copy()
            self.prices_history[dt] = current_prices.copy()

            # 记录交易到all_trade_records
            for order in executed_orders:
                all_trade_records.append({
                    'date': dt,
                    'symbol': order['symbol'],
                    'direction': 'long' if order['action'] == 'buy' else 'short',
                    'volume': order['volume'],
                    'price': order['price'],
                    'commission': order['volume'] * order['price'] * self.commission
                })

        # ========== 阶段3：逐日计算净值（参考vnpy load_data + new_bars） ==========
        print(f"\n[INFO] 开始逐日盯市计算...")

        # 收集所有持仓过的股票
        all_symbols = set()
        for positions in rebalance_positions.values():
            all_symbols.update(positions.keys())

        # 批量加载所有股票的日线价格
        daily_price_data = self._load_daily_prices(
            list(all_symbols), start_date, end_date
        )

        # 参考vnpy load_data：从数据中提取所有日期（self.dts.add(bar.datetime)）
        # 同时构建 history_data[(date_str, symbol)] = close_price
        history_data: Dict[tuple, float] = {}
        data_dates: set = set()

        for symbol, symbol_df in daily_price_data.items():
            if symbol_df is None or symbol_df.empty:
                continue
            close_col = 'close' if 'close' in symbol_df.columns else symbol_df.columns[-1]
            for idx_val, row in symbol_df.iterrows():
                date_str = self._normalize_date_to_str(idx_val)
                if date_str:
                    history_data[(date_str, symbol)] = float(row[close_col])
                    data_dates.add(date_str)

        # 参考vnpy run_backtesting：用数据本身的日期作为遍历序列
        # 而不是外部交易日历（避免格式不匹配）
        sorted_data_dates = sorted(data_dates)

        # 如果数据日期不足，回退到交易日历
        if len(sorted_data_dates) < 10:
            print(f"[WARN] 数据日期不足({len(sorted_data_dates)})，回退使用交易日历")
            sorted_data_dates = trading_dates

        print(f"[OK] 价格数据覆盖 {len(sorted_data_dates)} 个交易日, "
              f"{len(history_data)} 条价格记录")

        # 建立调仓日期排序列表
        sorted_rebalance_dates = sorted(rebalance_positions.keys())
        sorted_rebalance_dates.append('99999999')  # 哨兵

        # 逐日计算组合净值
        portfolio_records = []
        prev_value = self.initial_cash
        current_holdings: Dict[str, float] = {}
        current_cash = self.initial_cash

        # 参考vnpy bars：缓存的最新价格（用于fill_bar）
        cached_bars: Dict[str, float] = {}

        for trading_date in sorted_data_dates:
            # 确定当前持仓
            active_rebalance = None
            for rb_date in sorted_rebalance_dates[:-1]:
                if rb_date <= trading_date:
                    active_rebalance = rb_date
                else:
                    break

            if active_rebalance is not None:
                current_holdings = rebalance_positions[active_rebalance]
                current_cash = rebalance_cash[active_rebalance]

            # 参考vnpy new_bars：获取当日收盘价
            close_prices = {}
            for symbol in current_holdings:
                # 优先从 history_data 获取（参考vnpy: bar = history_data.get((dt, vt_symbol))）
                price = history_data.get((trading_date, symbol))
                if price is not None:
                    close_prices[symbol] = price
                    cached_bars[symbol] = price  # 更新缓存
                elif symbol in cached_bars:
                    # 参考vnpy：没有数据时用缓存填充（fill_bar）
                    close_prices[symbol] = cached_bars[symbol]

            # 计算当日组合市值
            holding_value = sum(
                volume * close_prices[symbol]
                for symbol, volume in current_holdings.items()
                if symbol in close_prices
            )

            total_value = current_cash + holding_value
            daily_return = (total_value - prev_value) / prev_value if prev_value > 0 else 0.0
            total_return = (total_value - self.initial_cash) / self.initial_cash

            portfolio_records.append({
                'date': trading_date,
                'value': total_value,
                'cash': current_cash,
                'position_count': len([v for v in current_holdings.values() if v > 0]),
                'positions': list(current_holdings.keys()),
                'daily_return': daily_return,
                'total_return': total_return,
            })

            prev_value = total_value

            # 更新 daily_result_manager（用于统计计算）
            dt_obj = datetime.strptime(trading_date, '%Y%m%d')
            self.daily_result_manager.get_or_create_result(dt_obj, close_prices)

        portfolio_df = pd.DataFrame(portfolio_records)

        # ========== 阶段4：计算每日盈亏和统计 ==========
        print(f"[INFO] 计算每日盈亏...")

        # 用 portfolio_df 直接构建 daily_df（兼容原有格式）
        if not portfolio_df.empty:
            daily_pnl_data = {
                'date': [],
                'trade_count': [],
                'turnover': [],
                'commission': [],
                'holding_pnl': [],
                'trading_pnl': [],
                'total_pnl': [],
                'net_pnl': [],
            }

            for idx, row in portfolio_df.iterrows():
                daily_pnl_data['date'].append(row['date'])
                daily_pnl_data['trade_count'].append(0)
                daily_pnl_data['turnover'].append(0)
                daily_pnl_data['commission'].append(0)
                daily_pnl_data['holding_pnl'].append(0)
                daily_pnl_data['trading_pnl'].append(0)

                # 用净值变化计算 net_pnl
                if idx == 0:
                    net_pnl = row['value'] - self.initial_cash
                else:
                    net_pnl = row['value'] - portfolio_df.iloc[idx - 1]['value']
                daily_pnl_data['total_pnl'].append(net_pnl)
                daily_pnl_data['net_pnl'].append(net_pnl)

            # 将交易信息合并到对应的交易日
            for trade_rec in all_trade_records:
                trade_date_str = trade_rec['date'].strftime('%Y%m%d')
                # 找到对应的行
                mask = portfolio_df['date'] == trade_date_str
                if mask.any():
                    idx = portfolio_df.index[mask][0]
                    daily_pnl_data['trade_count'][idx] += 1
                    daily_pnl_data['turnover'][idx] += trade_rec['volume'] * trade_rec['price']
                    daily_pnl_data['commission'][idx] += trade_rec['commission']

            daily_df = pd.DataFrame(daily_pnl_data)
            daily_df['balance'] = daily_df['net_pnl'].cumsum() + self.initial_cash
        else:
            daily_df = pd.DataFrame()

        # 计算统计指标
        print(f"[INFO] 计算统计指标...")
        statistics = self._calculate_statistics_from_daily(portfolio_df, daily_df)

        # 输出结果
        self._print_results(statistics)

        # 构建 trades DataFrame
        trades_df = pd.DataFrame(all_trade_records) if all_trade_records else pd.DataFrame()

        # 构建 performance 字典（与 BacktestEngine 兼容）
        performance = {
            'total_return': statistics.get('total_return', 0) / 100,
            'annual_return': statistics.get('annual_return', 0) / 100,
            'max_drawdown': statistics.get('max_drawdown', 0) / self.initial_cash,
            'sharpe_ratio': statistics.get('sharpe_ratio', 0),
            'initial_cash': self.initial_cash,
            'final_value': statistics.get('end_balance', 0),
            'total_days': statistics.get('total_days', 0),
            'profit_days': statistics.get('profit_days', 0),
            'loss_days': statistics.get('loss_days', 0)
        }

        return EnhancedBacktestResult(
            trades=trades_df,
            portfolio_history=portfolio_df,
            returns=daily_df,
            performance=performance,
            position_manager=self.position_manager,
            trades_history=self.trades_history,
            positions_history=self.positions_history,
            statistics=statistics
        )

    def _calculate_statistics_from_daily(self, portfolio_df: pd.DataFrame,
                                          daily_df: pd.DataFrame,
                                          annual_days: int = 240) -> Dict:
        """
        从每日净值数据计算统计指标（参考vnpy）

        Args:
            portfolio_df: 每日组合净值 DataFrame
            daily_df: 每日盈亏 DataFrame
            annual_days: 年化交易日数

        Returns:
            统计指标字典
        """
        if portfolio_df is None or portfolio_df.empty:
            return {}

        df = portfolio_df.copy()

        # 回撤计算
        df['highlevel'] = df['value'].cummax()
        df['drawdown'] = df['value'] - df['highlevel']
        df['ddpercent'] = (df['value'] / df['highlevel'] - 1) * 100

        # 基本统计
        total_days = len(df)
        profit_days = int((df['daily_return'] > 0).sum())
        loss_days = int((df['daily_return'] < 0).sum())

        end_balance = df['value'].iloc[-1]
        max_drawdown = df['drawdown'].min()
        max_ddpercent = df['ddpercent'].min()

        # 最大回撤持续时间
        max_dd_idx = df['drawdown'].values.argmin()
        max_dd_end = df['date'].iloc[max_dd_idx]
        max_dd_start_idx = df['value'].iloc[:max_dd_idx + 1].values.argmax()
        max_dd_start = df['date'].iloc[max_dd_start_idx]

        # 计算天数差
        try:
            start_dt = datetime.strptime(str(max_dd_start), '%Y%m%d')
            end_dt = datetime.strptime(str(max_dd_end), '%Y%m%d')
            max_drawdown_duration = (end_dt - start_dt).days
        except (ValueError, TypeError):
            max_drawdown_duration = 0

        # 收益率
        total_net_pnl = end_balance - self.initial_cash
        total_return = (end_balance / self.initial_cash - 1) * 100
        annual_return = total_return / total_days * annual_days if total_days > 0 else 0

        # 波动率和夏普比率
        daily_returns = df['daily_return']
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

        # 总成交额和手续费（从 daily_df）
        total_commission = daily_df['commission'].sum() if not daily_df.empty else 0
        total_turnover = daily_df['turnover'].sum() if not daily_df.empty else 0
        total_trade_count = int(daily_df['trade_count'].sum()) if not daily_df.empty else 0

        start_date = df['date'].iloc[0]
        end_date = df['date'].iloc[-1]

        return {
            'start_date': start_date,
            'end_date': end_date,
            'total_days': total_days,
            'profit_days': profit_days,
            'loss_days': loss_days,
            'initial_cash': self.initial_cash,
            'end_balance': end_balance,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'max_ddpercent': max_ddpercent,
            'max_drawdown_duration': max_drawdown_duration,
            'total_net_pnl': total_net_pnl,
            'daily_net_pnl': total_net_pnl / total_days if total_days > 0 else 0,
            'total_commission': total_commission,
            'total_turnover': total_turnover,
            'total_trade_count': total_trade_count,
            'sharpe_ratio': sharpe_ratio,
            'return_drawdown_ratio': return_drawdown_ratio,
        }

    def _empty_result(self) -> 'EnhancedBacktestResult':
        """返回空结果"""
        return EnhancedBacktestResult(
            trades=pd.DataFrame(),
            portfolio_history=pd.DataFrame(),
            returns=pd.DataFrame(),
            performance={
                'total_return': 0,
                'annual_return': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'initial_cash': self.initial_cash,
                'final_value': self.initial_cash,
                'total_days': 0,
                'profit_days': 0,
                'loss_days': 0,
            },
            position_manager=self.position_manager,
            trades_history={},
            positions_history={},
            statistics={}
        )

    def _get_current_prices(self, symbols: List[str], date: str,
                            max_days_back: int = 10) -> Dict[str, float]:
        """
        获取当前价格（支持非交易日自动回退）

        自动兼容多种 data_manager 接口：
        - LocalDataAdapter: get_stock_price_data() -> Dict[str, DataFrame]
        - DataManager: get_price() -> DataFrame with MultiIndex
        - DuckDBDataReader: get_price() -> DataFrame

        Args:
            symbols: 股票代码列表
            date: 日期 (YYYYMMDD)
            max_days_back: 非交易日最大回退天数
        """
        prices = {}

        if not self.data_manager:
            return prices

        try:
            # 方法1: 使用 get_stock_price_data (LocalDataAdapter 风格)
            if hasattr(self.data_manager, 'get_stock_price_data'):
                price_dict = self.data_manager.get_stock_price_data(
                    codes=symbols,
                    start_date=date,
                    end_date=date
                )

                if price_dict:
                    for symbol, symbol_df in price_dict.items():
                        if symbol_df is not None and not symbol_df.empty:
                            if 'close' in symbol_df.columns:
                                prices[symbol] = float(symbol_df['close'].iloc[-1])

            # 方法2: 使用 get_price (DataManager / DuckDBDataReader 风格)
            elif hasattr(self.data_manager, 'get_price'):
                df = self.data_manager.get_price(
                    codes=symbols,
                    start_date=date,
                    end_date=date
                )

                if df is not None and not df.empty:
                    # MultiIndex (date, symbol) 格式
                    if isinstance(df.index, pd.MultiIndex):
                        for symbol in symbols:
                            try:
                                symbol_data = df.xs(symbol, level='symbol')
                                if not symbol_data.empty:
                                    prices[symbol] = float(symbol_data['close'].iloc[-1])
                            except KeyError:
                                pass
                    else:
                        # 普通索引
                        for symbol in symbols:
                            if 'symbol' in df.columns:
                                symbol_data = df[df['symbol'] == symbol]
                                if not symbol_data.empty:
                                    prices[symbol] = float(symbol_data['close'].iloc[-1])

            # 对缺失的股票尝试向前回退查找
            if len(prices) < len(symbols):
                missing = [s for s in symbols if s not in prices]
                for symbol in missing:
                    # 尝试 get_nearest_price
                    if hasattr(self.data_manager, 'get_nearest_price'):
                        try:
                            price = self.data_manager.get_nearest_price(symbol, date, max_days_back)
                            if price is not None:
                                prices[symbol] = price
                        except Exception:
                            pass
                    # 尝试向前扩展日期范围获取
                    elif hasattr(self.data_manager, 'get_stock_price_data'):
                        try:
                            dt_obj = datetime.strptime(date, '%Y%m%d')
                            for days_back in range(1, max_days_back + 1):
                                prev_date = (dt_obj - __import__('datetime').timedelta(days=days_back)).strftime('%Y%m%d')
                                prev_dict = self.data_manager.get_stock_price_data(
                                    codes=[symbol],
                                    start_date=prev_date,
                                    end_date=prev_date
                                )
                                if prev_dict and symbol in prev_dict:
                                    prev_df = prev_dict[symbol]
                                    if prev_df is not None and not prev_df.empty and 'close' in prev_df.columns:
                                        prices[symbol] = float(prev_df['close'].iloc[-1])
                                        break
                        except Exception:
                            pass

        except Exception as e:
            print(f"[WARN] 获取价格失败: {e}")

        return prices

    @staticmethod
    def _normalize_date_to_str(idx_val) -> Optional[str]:
        """
        将各种日期格式统一转换为 YYYYMMDD 字符串

        支持的输入格式：
        - datetime 对象
        - date 对象
        - '20240102' 字符串
        - '2024-01-02' 字符串
        - pandas Timestamp
        - numpy datetime64
        """
        try:
            if isinstance(idx_val, str):
                # 已经是字符串
                cleaned = idx_val.replace('-', '').replace('/', '')
                if len(cleaned) == 8 and cleaned.isdigit():
                    return cleaned
                # 尝试解析
                return pd.to_datetime(idx_val).strftime('%Y%m%d')
            elif isinstance(idx_val, (datetime, date)):
                return idx_val.strftime('%Y%m%d')
            elif hasattr(idx_val, 'strftime'):
                # pandas Timestamp, numpy datetime64 等
                return idx_val.strftime('%Y%m%d')
            else:
                return pd.to_datetime(idx_val).strftime('%Y%m%d')
        except Exception:
            return None

    def _load_daily_prices(self, symbols: List[str],
                           start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """
        批量加载所有股票在整个回测期间的日线价格数据

        参考 vnpy 的 load_data 设计：一次性加载所有数据到内存

        Args:
            symbols: 股票代码列表
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            {symbol: DataFrame(index=date, columns=[open,close,...])}
        """
        if not self.data_manager or not symbols:
            return {}

        all_price_data = {}

        try:
            print(f"[INFO] 批量加载 {len(symbols)} 只股票的日线数据...")

            # 方法1: get_stock_price_data (LocalDataAdapter 风格，返回 Dict[str, DataFrame])
            if hasattr(self.data_manager, 'get_stock_price_data'):
                price_dict = self.data_manager.get_stock_price_data(
                    codes=symbols,
                    start_date=start_date,
                    end_date=end_date
                )

                if price_dict:
                    for symbol, symbol_df in price_dict.items():
                        if symbol_df is not None and not symbol_df.empty:
                            # 确保索引是日期字符串格式 (YYYYMMDD)
                            df_copy = symbol_df.copy()
                            if not isinstance(df_copy.index, str):
                                # 尝试转换索引为 YYYYMMDD 字符串
                                try:
                                    df_copy.index = pd.to_datetime(df_copy.index).strftime('%Y%m%d')
                                except Exception:
                                    pass
                            all_price_data[symbol] = df_copy

            # 方法2: get_price (DataManager 风格，返回合并的 DataFrame)
            elif hasattr(self.data_manager, 'get_price'):
                df = self.data_manager.get_price(
                    codes=symbols,
                    start_date=start_date,
                    end_date=end_date
                )

                if df is not None and not df.empty:
                    # 重置索引以便按symbol分组
                    if isinstance(df.index, pd.MultiIndex):
                        df = df.reset_index()

                    if 'symbol' in df.columns:
                        for symbol in symbols:
                            symbol_data = df[df['symbol'] == symbol].copy()
                            if not symbol_data.empty:
                                if 'date' in symbol_data.columns:
                                    symbol_data = symbol_data.set_index('date')
                                all_price_data[symbol] = symbol_data
                    else:
                        # 单只股票
                        all_price_data[symbols[0]] = df

            print(f"[OK] 成功加载 {len(all_price_data)} 只股票的日线数据")

        except Exception as e:
            print(f"[WARN] 批量加载日线数据失败: {e}")

        return all_price_data

    def _print_results(self, statistics: Dict) -> None:
        """打印回测结果"""
        print("\n" + "="*80)
        print("  回测结果")
        print("="*80)

        if not statistics:
            print("[WARN] 无统计数据")
            return

        print(f"\n【时间范围】")
        print(f"  起始日期: {statistics.get('start_date', 'N/A')}")
        print(f"  结束日期: {statistics.get('end_date', 'N/A')}")
        print(f"  总交易日: {statistics.get('total_days', 0)}")

        print(f"\n【资金情况】")
        print(f"  初始资金: {statistics.get('initial_cash', 0):,.2f}")
        print(f"  结束资金: {statistics.get('end_balance', 0):,.2f}")
        print(f"  总盈亏: {statistics.get('total_net_pnl', 0):,.2f}")

        print(f"\n【收益指标】")
        print(f"  总收益率: {statistics.get('total_return', 0):.2f}%")
        print(f"  年化收益: {statistics.get('annual_return', 0):.2f}%")
        print(f"  最大回撤: {statistics.get('max_drawdown', 0):,.2f}")
        print(f"  最大回撤率: {statistics.get('max_ddpercent', 0):.2f}%")
        print(f"  最大回撤持续: {statistics.get('max_drawdown_duration', 0)} 天")

        print(f"\n【交易统计】")
        print(f"  盈利天数: {statistics.get('profit_days', 0)}")
        print(f"  亏损天数: {statistics.get('loss_days', 0)}")
        print(f"  总成交额: {statistics.get('total_turnover', 0):,.2f}")
        print(f"  总手续费: {statistics.get('total_commission', 0):,.2f}")
        print(f"  总成交笔数: {statistics.get('total_trade_count', 0)}")

        print(f"\n【风险指标】")
        print(f"  夏普比率: {statistics.get('sharpe_ratio', 0):.2f}")
        print(f"  收益回撤比: {statistics.get('return_drawdown_ratio', 0):.2f}")

        print("\n" + "="*80)


def run_enhanced_backtest(strategy,
                         start_date: str,
                         end_date: str,
                         data_manager,
                         initial_cash: float = 1000000,
                         commission: float = 0.001) -> Dict:
    """
    运行增强回测的便捷函数

    Args:
        strategy: 策略实例
        start_date: 开始日期
        end_date: 结束日期
        data_manager: 数据管理器
        initial_cash: 初始资金
        commission: 佣金率

    Returns:
        回测结果字典
    """
    engine = EnhancedBacktestEngine(
        initial_cash=initial_cash,
        commission=commission,
        data_manager=data_manager
    )

    return engine.run_backtest(strategy, start_date, end_date)
