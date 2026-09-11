import pandas as pd

from easy_xt.realtime_data.providers.ftshare_provider import FTShareDataProvider


class FakeClient:
    def __init__(self):
        self.filters = []

    def stock_daec_stocks(self, **kwargs):
        self.filters.append(kwargs["filter"])
        return pd.DataFrame([{
            "symbol": "000001.SZ", "name": "平安银行", "close": "11.77",
            "prev_close": "11.85", "change": "-0.08", "change_rate": -0.00675,
            "volume": 100, "turnover": "1177", "ts_millis": 1789108329000,
        }])

    def close(self):
        pass


def test_ftshare_provider_maps_symbols_and_quote_fields():
    provider = FTShareDataProvider({"api_key": "test"})
    provider._client = FakeClient()
    provider.connected = True
    quotes = provider.get_realtime_quotes(["000001.SZ", "600519.SH"])
    assert '"000001.XSHE"' in provider._client.filters[0]
    assert '"600519.XSHG"' in provider._client.filters[0]
    assert quotes[0]["code"] == "000001.SZ"
    assert quotes[0]["price"] == 11.77
    assert quotes[0]["change_pct"] == -0.675
    assert quotes[0]["source"] == "ftshare"
