import pandas as pd

from core.data_manager.sources.ftshare_source import FTShareSource


class FakeClient:
    def __init__(self):
        self.calls = []

    def stock_candlesticks(self, **kwargs):
        self.calls.append(("stock_candlesticks", kwargs))
        return pd.DataFrame([{
            "timestamp": 1789088400000, "open": "10", "high": "11",
            "low": "9", "close": "10.5", "volume": "1000",
        }])

    def stock_realtime_minute_kline(self, **kwargs):
        self.calls.append(("stock_realtime_minute_kline", kwargs))
        return [{"trade_code": "000001.SZ", "close": 10.5}]

    def stock_minutes(self, **kwargs):
        self.calls.append(("stock_minutes", kwargs))
        return pd.DataFrame([{
            "timestamp": 1789088400000, "open": "10", "high": "11",
            "low": "9", "close": "10.5", "volume": "1000",
        }])

    def balance(self, **kwargs):
        self.calls.append(("balance", kwargs))
        return [{"publish_date": "2020-04-21", "t_assets": "90"},
                {"publish_date": "2026-08-30", "t_assets": "100"}]

    def trading_calendar(self, **kwargs):
        self.calls.append(("trading_calendar", kwargs))
        return [{"trade_date": "20260910", "is_open": 1},
                {"trade_date": "20260911", "is_open": 0}]

    def close(self):
        pass


def make_source():
    source = FTShareSource({}, client=FakeClient())
    assert source.connect()
    return source


def test_get_price_maps_easyxt_arguments_to_ftshare():
    source = make_source()
    frame = source.get_price("000001", "20260901", "20260911", "5m", "qfq")
    name, params = source._client.calls[-1]
    assert name == "stock_minutes"
    assert params["symbol"] == "000001.SZ"
    assert params["interval_value"] == 5
    assert params["adjust_kind"] == "forward"
    assert list(frame[["open", "close", "volume"]].iloc[0]) == [10, 10.5, 1000]


def test_daily_price_is_split_into_twelve_month_chunks():
    source = make_source()
    frame = source.get_price("000001", "20240101", "20251231", "1d")
    calls = [call for call in source._client.calls if call[0] == "stock_candlesticks"]
    assert len(calls) == 2
    assert frame is not None


def test_local_free_catalog_is_complete_and_searchable():
    endpoints = FTShareSource.list_free_endpoints()
    assert len(endpoints) == 160
    assert all(item["sdk_method"] for item in endpoints)
    assert any(item["sdk_method"] == "stock_capital_flows"
               for item in FTShareSource.list_free_endpoints("资金流"))


def test_realtime_calendar_and_fundamentals_wrappers():
    source = make_source()
    realtime = source.get_realtime_kline(["000001"], "1m")
    assert realtime.iloc[0]["symbol"] == "000001.SZ"
    assert source.get_trading_dates("20260910", "20260911") == ["20260910"]
    fundamentals = source.get_fundamentals(["000001.SZ"], "20260901", ["total_assets"])
    assert fundamentals.to_dict("records") == [{"symbol": "000001.SZ", "total_assets": 100}]


def test_connect_requires_key_when_no_injected_client(monkeypatch):
    monkeypatch.delenv("FTSHARE_API_KEY", raising=False)
    assert FTShareSource({}).connect() is False
