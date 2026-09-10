"""Canonical, side-effect-free DuckDB reader for local daily prices."""

from __future__ import annotations

from typing import Iterable
from datetime import datetime

import pandas as pd


DAILY_COLUMNS = ['date', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'amount']


def _date_text(value) -> str:
    text = str(value)[:10]
    if len(text) == 8 and text.isdigit():
        return datetime.strptime(text, '%Y%m%d').strftime('%Y-%m-%d')
    return datetime.strptime(text, '%Y-%m-%d').strftime('%Y-%m-%d')


def read_daily_prices(connection, symbols: Iterable[str], start_date: str,
                      end_date: str, *, include_etf: bool = True) -> pd.DataFrame:
    """Read canonical daily bars without opening connections or online fallback.

    Output units follow ``stock_daily``: volume in lots and amount in yuan.
    Tushare ``etf_daily.amount`` is stored in thousand yuan and is normalized
    on read until that legacy table is migrated.
    """
    symbols = sorted({str(symbol).strip().upper() for symbol in symbols if symbol})
    if not symbols:
        return pd.DataFrame(columns=DAILY_COLUMNS)

    start_date, end_date = _date_text(start_date), _date_text(end_date)
    if start_date > end_date:
        raise ValueError('start_date cannot be later than end_date')

    tables = {row[0] for row in connection.execute("""
        SELECT table_name FROM information_schema.tables WHERE table_schema='main'
    """).fetchall()}
    placeholders = ','.join('?' for _ in symbols)
    queries = []
    params = []
    if 'stock_daily' in tables:
        queries.append(f"""
            SELECT CAST(date AS DATE) AS date, stock_code AS symbol,
                   open, high, low, close, volume, amount
            FROM stock_daily
            WHERE stock_code IN ({placeholders})
              AND CAST(date AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
        """)
        params.extend(symbols + [start_date, end_date])
    if include_etf and 'etf_daily' in tables:
        queries.append(f"""
            SELECT CAST(trade_date AS DATE) AS date, ts_code AS symbol,
                   open, high, low, close, vol AS volume,
                   amount * 1000 AS amount
            FROM etf_daily
            WHERE ts_code IN ({placeholders})
              AND CAST(trade_date AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
        """)
        params.extend(symbols + [start_date, end_date])
    if not queries:
        return pd.DataFrame(columns=DAILY_COLUMNS)

    sql = " UNION ALL ".join(queries) + " ORDER BY date, symbol"
    result = connection.execute(sql, params).df()
    return result[DAILY_COLUMNS] if not result.empty else pd.DataFrame(columns=DAILY_COLUMNS)
