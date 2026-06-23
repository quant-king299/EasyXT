# -*- coding: utf-8 -*-
"""
通用向量化回测引擎

一次加载全量日线数据，逐日向量化过滤、选股、查价。
支持可转债 / ETF / 股票三类资产。
"""

import pandas as pd
import numpy as np
from typing import Callable, Dict, Any, List, Optional

DB_PATH = 'D:/StockData/stock_data.ddb'

# 各类资产配置
CATEGORY_CONFIG = {
    'cb': {
        'table': 'cb_daily',
        'code_col': 'ts_code',
        'date_col': 'trade_date',
        'extra_cols': ('cb_value', 'cb_over_rate', 'bond_value', 'bond_over_rate',
                       'vol', 'amount', 'pct_chg'),
        'trading_unit': 10,       # 可转债10张/手
        'default_min_price': 100,
        'default_max_price': 500,
        'fallback_sort_col': 'cb_over_rate',  # 策略失败时的兜底排序
    },
    'etf': {
        'table': 'etf_daily',
        'code_col': 'ts_code',
        'date_col': 'trade_date',
        'extra_cols': ('vol', 'amount', 'pct_chg'),
        'trading_unit': 100,
        'default_min_price': 0.5,
        'default_max_price': 10,
        'fallback_sort_col': 'pct_chg',
    },
    'stock': {
        'table': 'stock_daily',
        'code_col': 'stock_code',
        'date_col': 'date',
        'extra_cols': ('vol', 'amount'),
        'trading_unit': 100,
        'default_min_price': 1,
        'default_max_price': 9999,
        'fallback_sort_col': 'amount',  # 成交额排序
    },
}


class VectorizedBacktestEngine:
    """
    通用向量化回测引擎

    CB/ETF/股票共享同一套回测逻辑，仅数据源和交易参数不同。
    """

    def __init__(self, category: str = 'cb', db_path: str = None):
        if category not in CATEGORY_CONFIG:
            raise ValueError(f"不支持类别: {category}，可选: {list(CATEGORY_CONFIG.keys())}")
        self.category = category
        self.cfg = CATEGORY_CONFIG[category]
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = DB_PATH

    def run_backtest(
        self,
        strategy_func: Callable,
        start_date: str,
        end_date: str,
        rebalance_days: int = 5,
        top_n: int = 20,
        commission: float = 0.001,
        initial_cash: float = 100000.0,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        **strategy_kwargs
    ) -> Dict[str, Any]:
        """
        Args:
            strategy_func: 策略函数 (df_day, top_n, **kwargs) -> List[str]
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            rebalance_days: 调仓频率（交易日数）
            top_n: 持仓数量
            commission: 单边交易费率
            initial_cash: 初始资金
            min_price: 最低价格过滤（None=用默认值）
            max_price: 最高价格过滤（None=用默认值）
        """
        if min_price is None:
            min_price = self.cfg['default_min_price']
        if max_price is None:
            max_price = self.cfg['default_max_price']

        # ── 加载全量日线数据 ──
        df = self._load_daily_data(start_date, end_date)
        if df.empty:
            return self._empty_result()

        df['trade_date'] = pd.to_datetime(df[self.cfg['date_col']])
        code_col = self.cfg['code_col']
        df.sort_values(['trade_date', code_col], inplace=True)

        trading_dates = sorted(df['trade_date'].unique())

        cash = initial_cash
        holdings: Dict[str, tuple] = {}  # code → (shares, buy_price)
        nav_list = []
        holdings_history = []
        trades = []
        rebalance_counter = 0
        unit = self.cfg['trading_unit']

        for i, date in enumerate(trading_dates):
            day_df = df[df['trade_date'] == date].copy()

            # 基本过滤
            mask = (day_df['close'] >= min_price) & (day_df['close'] <= max_price)
            if 'vol' in day_df.columns:
                mask &= (day_df['vol'] > 0)
            day_df_filtered = day_df[mask].copy()

            # 计算持仓市值
            holdings_value = 0.0
            for code, (shares, buy_price) in holdings.items():
                rows = day_df[day_df[code_col] == code]
                if not rows.empty:
                    holdings_value += shares * rows.iloc[0]['close']
                else:
                    holdings_value += shares * buy_price

            total_value = cash + holdings_value
            nav = total_value / initial_cash

            rebalance_counter += 1
            should_rebalance = (rebalance_counter >= rebalance_days) or (i == 0)

            if should_rebalance and not day_df_filtered.empty:
                rebalance_counter = 0

                # 策略选股
                try:
                    selected = strategy_func(day_df_filtered, top_n=top_n,
                                             **strategy_kwargs)
                except Exception:
                    selected = []
                if not selected:
                    fallback = self.cfg['fallback_sort_col']
                    if fallback in day_df_filtered.columns:
                        selected = day_df_filtered.nsmallest(top_n, fallback)[code_col].tolist()
                    else:
                        selected = day_df_filtered.nsmallest(top_n, 'close')[code_col].tolist()
                selected = selected[:top_n]

                # 卖出
                for code in [c for c in holdings if c not in selected]:
                    shares, buy_price = holdings[code]
                    rows = day_df[day_df[code_col] == code]
                    sell_price = rows.iloc[0]['close'] if not rows.empty else buy_price
                    proceeds = shares * sell_price * (1 - commission)
                    cash += proceeds
                    trades.append({
                        'date': date, 'code': code, 'action': 'sell',
                        'price': sell_price, 'shares': shares,
                        'amount': proceeds,
                        'pnl': (sell_price - buy_price) * shares
                    })
                    del holdings[code]

                # 买入
                to_buy = [c for c in selected if c not in holdings]
                if to_buy:
                    target_per_stock = total_value / max(top_n, 1)
                    for code in to_buy:
                        rows = day_df[day_df[code_col] == code]
                        if rows.empty:
                            continue
                        buy_price = rows.iloc[0]['close']
                        budget = min(target_per_stock, cash)
                        shares = int(budget / (buy_price * unit)) * unit
                        if shares <= 0:
                            continue
                        cost = shares * buy_price * (1 + commission)
                        if cost > cash:
                            shares = int(cash / (buy_price * unit * (1 + commission))) * unit
                            cost = shares * buy_price * (1 + commission)
                        if shares > 0:
                            cash -= cost
                            holdings[code] = (shares, buy_price)
                            trades.append({
                                'date': date, 'code': code, 'action': 'buy',
                                'price': buy_price, 'shares': shares,
                                'amount': cost, 'pnl': 0
                            })

                holdings_history.append((date, list(holdings.keys())))

            nav_list.append({
                'date': date, 'nav': nav, 'cash': cash,
                'holdings_value': holdings_value,
                'total_value': total_value, 'num_holdings': len(holdings)
            })

        return self._build_result(nav_list, trades, holdings_history, initial_cash)

    # ── 数据加载 ──

    def _load_daily_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """从 DuckDB 加载全量日线数据"""
        import duckdb
        s = f'{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}'
        e = f'{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}'
        table = self.cfg['table']
        code_col = self.cfg['code_col']
        date_col = self.cfg['date_col']
        extra = ', '.join(self.cfg['extra_cols'])

        con = None
        try:
            con = duckdb.connect(self.db_path, read_only=True)
            df = con.execute(f"""
                SELECT {code_col} AS ts_code, {date_col} AS trade_date,
                       open, high, low, close,
                       {extra}
                FROM {table}
                WHERE {date_col} >= DATE '{s}'
                  AND {date_col} <= DATE '{e}'
                  AND close > 0
                ORDER BY ts_code, {date_col}
            """).fetchdf()
            label = {'cb': 'CB', 'etf': 'ETF', 'stock': '股票'}[self.category]
            print(f"[{label}引擎] 加载 {table}: {len(df)} 行, "
                  f"{df['ts_code'].nunique()} 只标的, "
                  f"{df['trade_date'].nunique()} 个交易日")
            return df
        except Exception as e:
            print(f"[{label}引擎] 数据加载失败: {e}")
            return pd.DataFrame()
        finally:
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass

    # ── 结果构建 ──

    def _build_result(self, nav_list: list, trades: list,
                      holdings_history: list,
                      initial_cash: float) -> Dict[str, Any]:
        nav_df = pd.DataFrame(nav_list)
        if nav_df.empty:
            return self._empty_result()

        nav_df.set_index('date', inplace=True)
        nav_df['daily_return'] = nav_df['nav'].pct_change().fillna(0)

        return {
            'nav_curve': nav_df,
            'metrics': self._calc_metrics(nav_df, initial_cash),
            'holdings_history': holdings_history,
            'trades': trades,
        }

    @staticmethod
    def _calc_metrics(nav_df: pd.DataFrame, initial_cash: float) -> dict:
        if nav_df.empty or len(nav_df) < 2:
            return {}

        total_days = len(nav_df)
        final_nav = nav_df['nav'].iloc[-1]
        total_return = final_nav - 1
        annual_return = (1 + total_return) ** (252 / max(total_days, 1)) - 1

        cummax = nav_df['nav'].cummax()
        drawdown = (nav_df['nav'] - cummax) / cummax
        max_drawdown = drawdown.min()

        daily_std = nav_df['daily_return'].std()
        sharpe = (nav_df['daily_return'].mean() / daily_std * np.sqrt(252)) \
            if daily_std > 0 else 0

        calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        win_rate = (nav_df['daily_return'] > 0).sum() / total_days

        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe,
            'calmar_ratio': calmar,
            'win_rate': win_rate,
            'total_days': total_days,
            'initial_cash': initial_cash,
            'final_value': nav_df['total_value'].iloc[-1],
        }

    def _empty_result(self) -> Dict[str, Any]:
        return {
            'nav_curve': pd.DataFrame(),
            'metrics': {},
            'holdings_history': [],
            'trades': [],
        }


# 向后兼容别名
CBBactestEngine = lambda **kw: VectorizedBacktestEngine(category='cb', **kw)
ETFBacktestEngine = lambda **kw: VectorizedBacktestEngine(category='etf', **kw)
StockBacktestEngine = lambda **kw: VectorizedBacktestEngine(category='stock', **kw)
