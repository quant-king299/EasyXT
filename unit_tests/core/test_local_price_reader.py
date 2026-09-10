import duckdb
import pytest

from core.data_manager.local_price_reader import read_daily_prices
from core.data_manager.sources.duckdb_source import DuckDBSource
from data_manager.unified_data_interface import UnifiedDataInterface


def _database():
    conn = duckdb.connect(':memory:')
    conn.execute("""
        CREATE TABLE stock_daily (
            stock_code VARCHAR, date DATE, open DOUBLE, high DOUBLE,
            low DOUBLE, close DOUBLE, volume BIGINT, amount DOUBLE)
    """)
    conn.execute("""
        CREATE TABLE etf_daily (
            ts_code VARCHAR, trade_date DATE, open DOUBLE, high DOUBLE,
            low DOUBLE, close DOUBLE, vol BIGINT, amount DOUBLE)
    """)
    conn.execute("""
        INSERT INTO stock_daily VALUES
          ('000001.SZ','2026-09-09',10,11,9,10.5,1000,1050000),
          ('000002.SZ','2026-09-09',20,21,19,20.5,2000,4100000);
        INSERT INTO etf_daily VALUES
          ('510300.SH','2026-09-09',4,4.1,3.9,4.05,3000,12.5)
    """)
    return conn


def test_reader_is_parameterized_and_normalizes_etf_amount_to_yuan():
    conn = _database()
    result = read_daily_prices(
        conn, ["000001.SZ", "510300.SH", "bad' OR 1=1 --"],
        '20260909', '2026-09-09')

    assert result['symbol'].tolist() == ['000001.SZ', '510300.SH']
    assert result.loc[result.symbol == '000001.SZ', 'amount'].iloc[0] == 1050000
    assert result.loc[result.symbol == '510300.SH', 'amount'].iloc[0] == 12500
    conn.close()


def test_duckdb_source_delegates_to_canonical_reader():
    conn = _database()
    source = DuckDBSource({'path': 'unused'})
    source.connection = conn

    result = source.get_price(
        ['000001.SZ', '510300.SH'], '20260909', '20260909', verbose=False)

    assert result.index.names == ['date', 'symbol']
    assert result.xs('510300.SH', level='symbol')['amount'].iloc[0] == pytest.approx(12500)
    conn.close()


def test_legacy_unified_interface_delegates_raw_daily_reads():
    conn = _database()
    interface = UnifiedDataInterface.__new__(UnifiedDataInterface)
    interface.con = conn

    result = interface._read_from_duckdb(
        '000001.SZ', '20260909', '2026-09-09', '1d', 'none')

    assert result.index.name == 'datetime'
    assert result['stock_code'].tolist() == ['000001.SZ']
    assert result['amount'].iloc[0] == pytest.approx(1050000)
    conn.close()
