"""Shared runtime services used by EasyXT's public API facades."""

import threading


_lock = threading.RLock()
_data_api = None
_trade_api = None


def get_shared_data_api():
    """Return the process-wide DataAPI used by all high-level facades."""
    global _data_api
    with _lock:
        if _data_api is None:
            from .data_api import DataAPI
            _data_api = DataAPI()
        return _data_api


def get_shared_trade_api():
    """Return the process-wide TradeAPI used by all high-level facades."""
    global _trade_api
    with _lock:
        if _trade_api is None:
            from .trade_api import TradeAPI
            _trade_api = TradeAPI()
        return _trade_api


def _reset_shared_apis_for_tests():
    global _data_api, _trade_api
    with _lock:
        _data_api = None
        _trade_api = None
