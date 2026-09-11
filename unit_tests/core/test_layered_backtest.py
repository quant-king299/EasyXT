import logging

import numpy as np
import pandas as pd

from core.alpha_analysis import LayeredBacktester
from core.performance_metrics import annualized_sharpe


def sample_data():
    dates = pd.date_range('2026-01-05', periods=5, freq='B')
    stocks = ['000001.SZ', '000002.SZ', '600000.SH', '600519.SH']
    prices = pd.DataFrame([
        [10.0, 20.0, 30.0, 40.0],
        [10.1, 19.8, 30.6, 39.6],
        [10.2, 20.2, 30.3, 40.4],
        [10.4, 20.0, 30.9, 40.0],
        [10.5, 20.4, 31.2, 40.8],
    ], index=dates, columns=stocks)
    factors = pd.DataFrame(
        np.tile([1.0, 2.0, 3.0, 4.0], (len(dates), 1)),
        index=dates, columns=stocks)
    return prices, factors


def test_layer_returns_keep_dates_and_repeated_runs_do_not_mutate_factors():
    prices, factors = sample_data()
    backtester = LayeredBacktester(prices, factors)

    first = backtester.calculate_layer_returns(n_layers=2, periods=1)
    second = backtester.calculate_layer_returns(n_layers=2, periods=1)

    assert first.index.equals(prices.index[:-1].rename('date'))
    pd.testing.assert_frame_equal(first, second)
    pd.testing.assert_frame_equal(backtester.factor_data, factors, check_freq=False)


def test_metrics_use_shared_risk_free_sharpe_formula():
    prices, factors = sample_data()
    backtester = LayeredBacktester(prices, factors)
    returns = pd.Series([0.01, -0.005, 0.007, 0.002])

    metrics = backtester.calculate_backtest_metrics(
        returns, annualization_factor=252, risk_free_rate=0.03)

    assert metrics['sharpe_ratio'] == annualized_sharpe(
        returns, risk_free_rate=0.03, annual_days=252)


def test_print_report_uses_standard_logging(caplog):
    prices, factors = sample_data()
    backtester = LayeredBacktester(prices, factors)
    backtester.calculate_backtest_metrics(
        pd.Series([0.01, -0.005, 0.007, 0.002]))

    with caplog.at_level(logging.INFO):
        backtester.print_report()

    assert '策略评级：' in caplog.text


def test_invalid_layer_and_holding_period_are_rejected():
    prices, factors = sample_data()
    backtester = LayeredBacktester(prices, factors)

    for invalid in (0, -1):
        try:
            backtester.calculate_returns(periods=invalid)
        except ValueError as exc:
            assert 'periods' in str(exc)
        else:
            raise AssertionError('invalid periods should fail')

    try:
        backtester.create_layers(n_layers=1)
    except ValueError as exc:
        assert 'n_layers' in str(exc)
    else:
        raise AssertionError('one layer should fail')
