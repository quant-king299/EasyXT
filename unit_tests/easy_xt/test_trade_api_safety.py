from types import SimpleNamespace

import pandas as pd
import pytest

from easy_xt.trade_api import TradeAPI


@pytest.mark.parametrize(
    "volume,price,price_type",
    [
        (0, 0, "market"),
        (101, 0, "market"),
        (100.0, 0, "market"),
        (100, 0, "limit"),
        (100, -1, "market"),
        (100, float("nan"), "limit"),
        (100, 10, "unknown"),
    ],
)
def test_rejects_invalid_order_params(volume, price, price_type):
    with pytest.raises(ValueError):
        TradeAPI._validate_order_params(volume, price, price_type)


def test_accepts_valid_market_and_limit_orders():
    TradeAPI._validate_order_params(100, 0, "market")
    TradeAPI._validate_order_params(200, 10.5, "limit")


def test_process_and_filter_history_trades():
    api = TradeAPI.__new__(TradeAPI)
    raw_trades = [
        SimpleNamespace(
            order_type=23,
            stock_code="000001.SZ",
            traded_volume=100,
            traded_price=10.0,
            traded_amount=1000.0,
            traded_time=1722474000,
            order_id=1,
            traded_id="t1",
        )
    ]

    import easy_xt.trade_api as trade_api_module

    old_xt_const = getattr(trade_api_module, "xt_const", None)
    trade_api_module.xt_const = SimpleNamespace(STOCK_BUY=23)
    try:
        processed = api._process_trades_data(raw_trades)
    finally:
        trade_api_module.xt_const = old_xt_const

    api.get_trades = lambda account_id: processed
    result = api.get_history_trades("test", "20240801", "20240801")

    assert list(result["order_type"]) == ["买入"]
    assert pd.api.types.is_datetime64_any_dtype(result["time"])
