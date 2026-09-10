import duckdb
import pandas as pd
import pytest

from data_manager.tushare_daily_repair import update_missing_daily_units


def test_repairs_only_missing_existing_rows_and_preserves_ohlc():
    conn = duckdb.connect(':memory:')
    conn.execute("""
        CREATE TABLE stock_daily (
            stock_code VARCHAR, date DATE, period VARCHAR, open DOUBLE,
            high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT,
            amount DOUBLE, updated_at TIMESTAMP,
            PRIMARY KEY (stock_code, date, period))
    """)
    conn.execute("""
        INSERT INTO stock_daily VALUES
        ('000001.SZ','2026-08-18','1d',11,12,10,11.05,80893000,0,NULL),
        ('000002.SZ','2026-08-18','1d',9,10,8,9.5,1000,123456,NULL)
    """)
    source = pd.DataFrame({
        'stock_code': ['000001.SZ', '000002.SZ', '000003.SZ'],
        'date': pd.to_datetime(['20260818'] * 3, format='%Y%m%d'),
        'volume': [808929.71, 2222.2, 3333.3],
        'amount': [896326748.71, 222200.0, 333300.0],
    })

    assert update_missing_daily_units(conn, source) == 1
    damaged = conn.execute("""
        SELECT open,high,low,close,volume,amount FROM stock_daily
        WHERE stock_code='000001.SZ'
    """).fetchone()
    assert damaged[:4] == (11.0, 12.0, 10.0, 11.05)
    assert damaged[4] == 808930
    assert damaged[5] == pytest.approx(896326748.71)
    assert conn.execute("""
        SELECT volume,amount FROM stock_daily WHERE stock_code='000002.SZ'
    """).fetchone() == (1000, 123456.0)
    assert conn.execute("SELECT COUNT(*) FROM stock_daily").fetchone()[0] == 2
    conn.close()
