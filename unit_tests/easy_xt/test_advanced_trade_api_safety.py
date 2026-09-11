from types import SimpleNamespace

import pytest

from easy_xt.advanced_trade_api import AdvancedTradeAPI
import easy_xt.advanced_trade_api as advanced_module


class RecordingTrader:
    def __init__(self):
        self.calls = []

    def order_stock(self, **kwargs):
        self.calls.append(kwargs)
        return 42


def make_api():
    api = AdvancedTradeAPI.__new__(AdvancedTradeAPI)
    api.trader = RecordingTrader()
    api.accounts = {'account': object()}
    return api


@pytest.mark.parametrize(
    'order_type,volume,price,price_type',
    [
        ('hold', 100, 0, 'market'),
        ('buy', 0, 0, 'market'),
        ('sell', 101, 0, 'market'),
        ('buy', 100, 0, 'limit'),
        ('sell', 100, -1, 'market'),
        ('buy', 100, 10, 'unknown'),
    ],
)
@pytest.mark.parametrize('method_name', ['sync_order', 'async_order'])
def test_invalid_advanced_orders_never_reach_trader(
    method_name, order_type, volume, price, price_type
):
    api = make_api()

    with pytest.raises(ValueError):
        getattr(api, method_name)(
            'account', '000001.SZ', order_type, volume, price, price_type
        )

    assert api.trader.calls == []


@pytest.mark.parametrize(
    'order_type,expected_constant',
    [('buy', 23), ('买入', 23), ('sell', 24), ('卖出', 24)],
)
def test_valid_direction_is_mapped_explicitly(monkeypatch, order_type, expected_constant):
    api = make_api()
    monkeypatch.setattr(
        advanced_module,
        'xt_const',
        SimpleNamespace(
            STOCK_BUY=23,
            STOCK_SELL=24,
            LATEST_PRICE=5,
            FIX_PRICE=11,
        ),
    )

    order_id = api.sync_order('account', '000001.SZ', order_type, 100)

    assert order_id == 42
    assert api.trader.calls[0]['order_type'] == expected_constant
