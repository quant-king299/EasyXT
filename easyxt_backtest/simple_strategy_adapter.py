# -*- coding: utf-8 -*-
"""
简单函数策略适配器

将 func(df, top_n) -> List[str] 形式的策略函数
转换为 EnhancedBacktestEngine 所需的 StrategyBase 实例。

用法:
    from easyxt_backtest.simple_strategy_adapter import adapt
    from easyxt_backtest import EnhancedBacktestEngine

    engine = EnhancedBacktestEngine(initial_cash=100000)
    strategy = adapt(my_func, top_n=20, rebalance_days=5,
                     start_date='20240101', end_date='20250630')
    result = engine.run_backtest(strategy, start_date, end_date)
"""

import pandas as pd
from typing import Callable, List, Dict, Optional
from .strategy_base import StrategyBase


class SimpleFunctionAdapter(StrategyBase):
    """将简单函数适配为 StrategyBase"""

    def __init__(self, func: Callable, top_n: int = 20,
                 rebalance_days: int = 5,
                 start_date: str = '20200101',
                 end_date: str = '20251231',
                 data_manager=None,
                 **extra_kwargs):
        super().__init__(data_manager)
        self.func = func
        self.top_n = top_n
        self._rebalance_days = rebalance_days
        self._start = start_date
        self._end = end_date
        self._extra = extra_kwargs

    def select_stocks(self, date: str) -> List[str]:
        """选股：直接从 DuckDB 加载当日全市场数据"""
        try:
            import duckdb
            db_path = 'D:/StockData/stock_data.ddb'

            # YYYYMMDD → YYYY-MM-DD（DuckDB DATE 类型要求）
            if len(date) == 8 and date.isdigit():
                date_fmt = f'{date[:4]}-{date[4:6]}-{date[6:]}'
            else:
                date_fmt = date

            # 尝试从三个表加载数据
            frames = []
            con = duckdb.connect(db_path, read_only=True)
            for table, code_col, date_col, extra_cols in [
                ('etf_daily', 'ts_code', 'trade_date',
                 'pct_chg, amount'),
                ('stock_daily', 'stock_code', 'date',
                 '(close - LAG(close) OVER w) / NULLIF(LAG(close) OVER w, 0) * 100 AS pct_chg, amount'),
                ('cb_daily', 'ts_code', 'trade_date',
                 'cb_over_rate, bond_value, cb_value'),
            ]:
                try:
                    if table == 'stock_daily':
                        query = f"""
                            SELECT {code_col} AS ts_code, {date_col} AS trade_date,
                                   close, {extra_cols}
                            FROM {table}
                            WHERE {date_col} = '{date_fmt}'
                              AND close > 0 AND amount > 0
                            WINDOW w AS (PARTITION BY stock_code ORDER BY date)
                        """
                    else:
                        query = f"""
                            SELECT {code_col} AS ts_code, {date_col} AS trade_date,
                                   close, {extra_cols}
                            FROM {table}
                            WHERE {date_col} = '{date_fmt}'
                              AND close > 0
                        """
                    df = con.execute(query).fetchdf()
                    if not df.empty:
                        df['trade_date'] = pd.to_datetime(df['trade_date'])
                        frames.append(df)
                except Exception:
                    pass
            con.close()

            if not frames:
                return []
            day_df = pd.concat(frames, ignore_index=True)

            result = self.func(day_df, top_n=self.top_n, **self._extra)
            return result[:self.top_n] if isinstance(result, list) else []
        except Exception:
            return []

    def get_target_weights(self, date: str, selected: List[str]) -> Dict[str, float]:
        if not selected:
            return {}
        w = 1.0 / len(selected)
        return {s: w for s in selected}

    def get_rebalance_dates(self, start_date: str, end_date: str) -> List[str]:
        return self._get_all_trading_days(start_date or self._start,
                                          end_date or self._end)


def adapt(func: Callable, top_n: int = 20, rebalance_days: int = 5,
          start_date: str = '20200101', end_date: str = '20251231',
          data_manager=None, **extra) -> StrategyBase:
    """快速适配: 给一个函数, 返回 StrategyBase"""
    return SimpleFunctionAdapter(
        func, top_n=top_n, rebalance_days=rebalance_days,
        start_date=start_date, end_date=end_date,
        data_manager=data_manager, **extra,
    )
