#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tushare 数据下载组件单元测试

测试目标：gui_app/widgets/tushare_data_widget.py 中日线数据保存逻辑
"""

import sys
from pathlib import Path

import duckdb
import pandas as pd
import pytest

# gui_app 不是 Python package，需要把项目根目录加入 sys.path
PROJECT_ROOT = Path(__file__).parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gui_app.widgets.tushare_data_widget import TushareDownloadThread


# ─── fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def db_conn():
    """提供一个干净的内存 DuckDB 连接。"""
    conn = duckdb.connect(':memory:')
    yield conn
    conn.close()


def _create_stock_daily_table(conn):
    """创建与 _download_daily 一致的 stock_daily 表结构。"""
    conn.execute("""
        CREATE TABLE stock_daily (
            stock_code VARCHAR,
            symbol_type VARCHAR DEFAULT 'stock',
            date DATE,
            period VARCHAR DEFAULT '1d',
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume BIGINT,
            amount DOUBLE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (stock_code, date, period)
        )
    """)


def _make_daily_df(**overrides):
    """构造标准日线 DataFrame。"""
    data = {
        'stock_code': ['000001.SZ'],
        'symbol_type': ['stock'],
        'date': [pd.to_datetime('2026-07-01').date()],
        'period': ['1d'],
        'open': [10.0],
        'high': [11.0],
        'low': [9.0],
        'close': [10.5],
        'volume': [1_000_000],
        'amount': [10_500_000.0],
    }
    data.update(overrides)
    return pd.DataFrame(data)


# ─── tests ───────────────────────────────────────────────────────────────────


def test_save_daily_dataframe_inserts_correctly(db_conn):
    """验证日线数据能正确写入 12 列的 stock_daily 表。"""
    _create_stock_daily_table(db_conn)
    df = _make_daily_df()

    TushareDownloadThread._save_daily_dataframe(db_conn, df)

    rows = db_conn.execute("SELECT * FROM stock_daily").fetchdf()
    assert len(rows) == 1
    assert rows.loc[0, 'stock_code'] == '000001.SZ'
    assert rows.loc[0, 'close'] == 10.5
    assert rows.loc[0, 'volume'] == 1_000_000


def test_save_daily_dataframe_no_legacy_columns(db_conn):
    """验证新表结构不含已废弃的 adjust_type / factor 列。"""
    _create_stock_daily_table(db_conn)
    df = _make_daily_df()

    TushareDownloadThread._save_daily_dataframe(db_conn, df)

    schema = db_conn.execute("DESCRIBE stock_daily").fetchdf()
    columns = [c.lower() for c in schema['column_name'].tolist()]
    assert 'adjust_type' not in columns
    assert 'factor' not in columns


def test_save_daily_dataframe_column_order_independent(db_conn):
    """验证 DataFrame 列顺序打乱后仍能按列名正确写入。"""
    _create_stock_daily_table(db_conn)
    # 故意打乱列顺序
    df = pd.DataFrame({
        'close': [10.5],
        'low': [9.0],
        'volume': [1_000_000],
        'stock_code': ['000001.SZ'],
        'amount': [10_500_000.0],
        'symbol_type': ['stock'],
        'date': [pd.to_datetime('2026-07-01').date()],
        'period': ['1d'],
        'open': [10.0],
        'high': [11.0],
    })

    TushareDownloadThread._save_daily_dataframe(db_conn, df)

    row = db_conn.execute("""
        SELECT stock_code, open, high, low, close, volume, amount
        FROM stock_daily
        WHERE stock_code = '000001.SZ' AND date = '2026-07-01'
    """).fetchone()

    assert row[0] == '000001.SZ'
    assert row[1] == 10.0   # open
    assert row[2] == 11.0   # high
    assert row[3] == 9.0    # low
    assert row[4] == 10.5   # close
    assert row[5] == 1_000_000
    assert row[6] == 10_500_000.0


def test_save_daily_dataframe_preserves_created_at_on_conflict(db_conn):
    """验证冲突替换时 created_at 被保留，updated_at 和 close 被更新。"""
    _create_stock_daily_table(db_conn)

    original_created_at = pd.Timestamp('2026-01-01 12:00:00')
    original_updated_at = pd.Timestamp('2026-01-01 12:00:00')
    db_conn.execute("""
        INSERT INTO stock_daily
        (stock_code, symbol_type, date, period, open, high, low, close, volume, amount, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        '000001.SZ', 'stock', pd.to_datetime('2026-07-01').date(), '1d',
        10.0, 11.0, 9.0, 10.5, 1_000_000, 10_500_000.0,
        original_created_at, original_updated_at
    ])

    # 同一条记录，价格更新
    df = _make_daily_df(
        open=[20.0],
        high=[21.0],
        low=[19.0],
        close=[20.5],
        volume=[2_000_000],
        amount=[20_500_000.0],
    )

    TushareDownloadThread._save_daily_dataframe(db_conn, df)

    row = db_conn.execute("""
        SELECT created_at, updated_at, close
        FROM stock_daily
        WHERE stock_code = '000001.SZ' AND date = '2026-07-01'
    """).fetchone()

    # created_at 应保持原值
    assert row[0] == original_created_at
    # updated_at 应被刷新
    assert row[1] > original_updated_at
    # close 应被更新
    assert row[2] == 20.5


def test_save_daily_dataframe_ignores_extra_columns(db_conn):
    """验证 DataFrame 中多余列不会干扰写入。"""
    _create_stock_daily_table(db_conn)
    df = _make_daily_df()
    df['extra_col'] = 999  # 不应该被写入，也不应该报错

    TushareDownloadThread._save_daily_dataframe(db_conn, df)

    rows = db_conn.execute("SELECT * FROM stock_daily").fetchdf()
    assert len(rows) == 1
    assert 'extra_col' not in rows.columns
