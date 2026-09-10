import logging

import pandas as pd

from core.data_manager.hybrid_manager import HybridDataManager


class FundamentalsSource:
    def __init__(self, available_date=None):
        self.available_date = available_date
        self.requested_dates = []

    def is_available(self):
        return True

    def get_fundamentals(self, symbols, date, fields):
        self.requested_dates.append(date)
        if date == self.available_date:
            return pd.DataFrame({'symbol': symbols})
        return pd.DataFrame()


def manager_with_source(source):
    manager = HybridDataManager.__new__(HybridDataManager)
    manager.sources = {'duckdb': source}
    manager.price_cache = {}
    manager.fundamental_cache = {}
    manager.trading_dates_cache = None
    return manager


def test_nearest_fundamentals_never_reads_future_dates():
    source = FundamentalsSource(available_date='20260102')
    manager = manager_with_source(source)

    actual = manager._find_nearest_trading_date_with_data(
        '20260101', ['000001.SZ'], ['circ_mv'], max_days=3)

    assert actual == '20260101'
    assert source.requested_dates == [
        '20260101', '20251231', '20251230', '20251229']


def test_nearest_fundamentals_uses_latest_prior_date():
    source = FundamentalsSource(available_date='20260108')
    manager = manager_with_source(source)

    actual = manager._find_nearest_trading_date_with_data(
        '20260110', ['000001.SZ'], ['circ_mv'], max_days=3)

    assert actual == '20260108'
    assert source.requested_dates == ['20260110', '20260109', '20260108']


def test_cache_status_uses_logging_without_stdout(capsys, caplog):
    source = FundamentalsSource()
    source.clear_cache = lambda: None
    manager = manager_with_source(source)

    with caplog.at_level(logging.INFO):
        manager.clear_cache()

    assert capsys.readouterr().out == ''
    assert '所有缓存已清空' in caplog.text
