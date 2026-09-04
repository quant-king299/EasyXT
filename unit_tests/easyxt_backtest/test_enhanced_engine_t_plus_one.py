import pandas as pd
import pytest

from easyxt_backtest.enhanced_backtest_engine import EnhancedBacktestEngine


class FakeStrategy:
    name = "T+1 test"

    def __init__(self, include_open=True):
        self.include_open = include_open
        self.selection_dates = []

    def get_rebalance_dates(self, start_date, end_date):
        return ["20240102"]

    def select_stocks(self, date):
        self.selection_dates.append(date)
        return ["000001.SZ"]

    def get_target_weights(self, date, selected_stocks):
        return {"000001.SZ": 1.0}

    def get_open_prices_for_date(self, symbols, date):
        assert date == "20240103"
        return {"000001.SZ": 11.0} if self.include_open else {}

    def get_prices_batch(self, symbols, start_date, end_date):
        return {
            "000001.SZ": pd.DataFrame(
                {
                    "open": [10.0, 11.0, 12.0],
                    "close": [10.5, 11.5, 12.5],
                },
                index=["20240102", "20240103", "20240104"],
            )
        }


class FakeCalendar:
    @staticmethod
    def get_trading_dates(start_date, end_date):
        return ["20240102", "20240103", "20240104"]


def test_signal_is_generated_on_t_and_filled_at_t_plus_one_open():
    strategy = FakeStrategy()
    engine = EnhancedBacktestEngine(
        initial_cash=100_000,
        commission=0,
        slippage=0,
        data_manager=FakeCalendar(),
    )

    result = engine.run_backtest(strategy, "20240102", "20240104", auto_report=False)

    assert strategy.selection_dates == ["20240102"]
    assert len(result.trades) == 1
    trade = result.trades.iloc[0]
    assert trade["signal_date"] == pd.Timestamp("2024-01-02")
    assert trade["date"] == pd.Timestamp("2024-01-03")
    assert trade["price"] == pytest.approx(11.0)


def test_missing_t_plus_one_open_does_not_fallback_to_close():
    strategy = FakeStrategy(include_open=False)
    engine = EnhancedBacktestEngine(data_manager=FakeCalendar())

    result = engine.run_backtest(strategy, "20240102", "20240104", auto_report=False)

    assert result.trades.empty


def test_zero_lag_is_rejected():
    with pytest.raises(ValueError, match="signal_lag_days"):
        EnhancedBacktestEngine(signal_lag_days=0)


def test_negative_slippage_is_rejected():
    with pytest.raises(ValueError, match="slippage"):
        EnhancedBacktestEngine(slippage=-0.001)
