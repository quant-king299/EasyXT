import pytest

from easyxt_backtest.position_manager import PositionManager


def test_buy_uses_configured_commission_rate():
    manager = PositionManager(initial_cash=20_000, commission_rate=0.002)
    order = {"symbol": "000001.SZ", "action": "buy", "volume": 100, "price": 10}

    manager.execute_order(order)

    assert order["commission"] == pytest.approx(2.0)
    assert manager.cash == pytest.approx(18_998.0)


def test_sell_uses_configured_commission_rate():
    manager = PositionManager(initial_cash=20_000, commission_rate=0.002)
    manager.positions["000001.SZ"] = 100
    order = {"symbol": "000001.SZ", "action": "sell", "volume": 100, "price": 10}

    manager.execute_order(order)

    assert order["commission"] == pytest.approx(2.0)
    assert manager.cash == pytest.approx(20_998.0)


def test_rebalance_affordability_uses_same_commission_rate():
    manager = PositionManager(initial_cash=1_001, commission_rate=0.002)
    manager.set_target_position("000001.SZ", 100)

    orders = manager.execute_rebalance({"000001.SZ": 10}, price_tolerance=0)

    assert orders == []
    assert manager.cash == 1_001


def test_negative_commission_is_rejected():
    with pytest.raises(ValueError):
        PositionManager(commission_rate=-0.001)
