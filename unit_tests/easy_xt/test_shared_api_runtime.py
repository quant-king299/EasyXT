from easy_xt.api import EasyXT
from easy_xt.extended_api import ExtendedAPI
from easy_xt.api_runtime import _reset_shared_apis_for_tests


def setup_function():
    _reset_shared_apis_for_tests()


def teardown_function():
    _reset_shared_apis_for_tests()


def test_public_facades_share_data_and_trade_state():
    easy = EasyXT()
    extended = ExtendedAPI()

    assert easy.data is extended.data_api
    assert easy.trade is extended.trade_api


def test_extended_api_still_accepts_explicit_dependencies():
    data = object()
    trade = object()
    extended = ExtendedAPI(data_api=data, trade_api=trade)

    assert extended.data_api is data
    assert extended.trade_api is trade
