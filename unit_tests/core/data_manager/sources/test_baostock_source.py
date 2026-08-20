# -*- coding: utf-8 -*-
"""BaoStockSource 单元测试，不连接真实数据服务器。"""
import threading
import time

import pandas as pd

from core.data_manager.sources.baostock_source import BaoStockSource


class FakeResult:
    def __init__(self, fields, rows, error_code="0", error_msg="success"):
        self.fields = fields
        self.rows = rows
        self.error_code = error_code
        self.error_msg = error_msg
        self._index = -1

    def next(self):
        self._index += 1
        return self._index < len(self.rows)

    def get_row_data(self):
        return self.rows[self._index]


class FakeLogin:
    error_code = "0"
    error_msg = "success"


class FakeClient:
    def __init__(self, rows=None):
        self.rows = rows if rows is not None else [[
            "2026-08-19", "sh.600000", "9.10", "9.20", "9.00", "9.15",
            "9.05", "1000", "9100", "3", "0.1", "1", "1.1",
            "6.2", "0.4", "1.8", "3.0", "0",
        ]]
        self.calls = []

    def login(self):
        return FakeLogin()

    def logout(self):
        return FakeLogin()

    def query_history_k_data_plus(self, code, fields, **kwargs):
        self.calls.append((code, fields, kwargs))
        names = fields.split(",")
        if fields.startswith("date,code,open"):
            return FakeResult(names, self.rows)
        values = {"date": "2026-08-19", "code": code, "peTTM": "6.2", "pbMRQ": "0.4"}
        return FakeResult(names, [[values.get(name, "") for name in names]])

    def query_trade_dates(self, **kwargs):
        return FakeResult(
            ["calendar_date", "is_trading_day"],
            [["2026-08-15", "0"], ["2026-08-17", "1"]],
        )


def make_source(client=None):
    source = BaoStockSource({"max_retries": 0}, client=client or FakeClient())
    assert source.connect()
    return source


def test_symbol_mapping_covers_stock_and_etf():
    assert BaoStockSource._to_bs_symbol("600000.SH") == "sh.600000"
    assert BaoStockSource._to_bs_symbol("510300") == "sh.510300"
    assert BaoStockSource._to_bs_symbol("000001.SZ") == "sz.000001"
    assert BaoStockSource._from_bs_symbol("sh.600000") == "600000.SH"


def test_get_price_maps_parameters_and_numeric_fields():
    client = FakeClient()
    source = make_source(client)
    result = source.get_price("600000.SH", "20260801", "20260819", adjust="qfq")

    assert result is not None
    assert result.loc[0, "symbol"] == "600000.SH"
    assert result.loc[0, "date"] == "20260819"
    assert result.loc[0, "close"] == 9.15
    assert pd.api.types.is_numeric_dtype(result["volume"])
    code, _, kwargs = client.calls[0]
    assert code == "sh.600000"
    assert kwargs["start_date"] == "2026-08-01"
    assert kwargs["frequency"] == "d"
    assert kwargs["adjustflag"] == "2"


def test_get_price_rejects_mismatched_response_symbol():
    bad_row = FakeClient().rows[0].copy()
    bad_row[1] = "sz.000001"
    source = make_source(FakeClient([bad_row]))
    assert source.get_price("600000.SH", "20260801", "20260819") is None


def test_empty_result_is_none():
    source = make_source(FakeClient(rows=[]))
    assert source.get_price("600000.SH", "20260801", "20260819") is None


def test_trading_dates_only_returns_open_days():
    source = make_source()
    assert source.get_trading_dates("20260815", "20260817") == ["20260817"]


def test_fundamentals_uses_latest_known_daily_valuation():
    source = make_source()
    result = source.get_fundamentals(["600000.SH"], "20260819", ["peTTM", "pbMRQ"])
    assert result is not None
    assert result.loc[0, "peTTM"] == 6.2
    assert result.loc[0, "pbMRQ"] == 0.4


def test_fundamentals_supports_easyxt_aliases():
    source = make_source()
    result = source.get_fundamentals(["600000.SH"], "20260819", ["pe", "pb"])
    assert result is not None
    assert result.loc[0, "pe"] == 6.2
    assert result.loc[0, "pb"] == 0.4


def test_process_lock_serializes_complete_result_consumption():
    active = 0
    maximum = 0
    guard = threading.Lock()

    class SlowResult(FakeResult):
        def next(self):
            nonlocal active, maximum
            with guard:
                active += 1
                maximum = max(maximum, active)
            time.sleep(0.01)
            value = super().next()
            with guard:
                active -= 1
            return value

    class SlowClient(FakeClient):
        def query_history_k_data_plus(self, code, fields, **kwargs):
            row = self.rows[0].copy()
            row[1] = code
            return SlowResult(fields.split(","), [row])

    source = make_source(SlowClient())
    threads = [
        threading.Thread(target=source.get_price, args=(symbol, "20260801", "20260819"))
        for symbol in ("600000.SH", "000001.SZ", "510300.SH")
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert maximum == 1
