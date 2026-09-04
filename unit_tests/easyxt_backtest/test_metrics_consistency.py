import pandas as pd
import pytest

from easyxt_backtest.enhanced_backtest_engine import EnhancedBacktestEngine
from easyxt_backtest.metrics import annualized_return, annualized_sharpe
from easyxt_backtest.performance import PerformanceAnalyzer
from easyxt_backtest.portfolio_daily_result import DailyResultManager
from easyxt_backtest.vectorized_engine import VectorizedBacktestEngine


def test_geometric_annualization():
    assert annualized_return(0.10, 126) == pytest.approx(0.21)


def test_all_entry_points_share_annual_return_and_sharpe():
    returns = pd.Series([0.0, 0.01, -0.004, 0.006])
    values = (1 + returns).cumprod() * 100_000
    total_return = values.iloc[-1] / values.iloc[0] - 1
    expected_annual = annualized_return(total_return, len(values))
    expected_sharpe = annualized_sharpe(returns, 0.03)

    analyzer = PerformanceAnalyzer(risk_free_rate=0.03)
    assert analyzer._calculate_sharpe_ratio(returns, 1.0) == pytest.approx(expected_sharpe)

    portfolio_df = pd.DataFrame({
        "date": ["20240102", "20240103", "20240104", "20240105"],
        "value": values,
        "daily_return": returns,
    })
    daily_df = pd.DataFrame({"commission": [0] * 4, "turnover": [0] * 4, "trade_count": [0] * 4})
    enhanced = EnhancedBacktestEngine(initial_cash=values.iloc[0], risk_free_rate=0.03)
    enhanced_metrics = enhanced._calculate_statistics_from_daily(portfolio_df, daily_df)
    assert enhanced_metrics["annual_return"] / 100 == pytest.approx(expected_annual)
    assert enhanced_metrics["sharpe_ratio"] == pytest.approx(expected_sharpe)

    nav_df = pd.DataFrame({
        "nav": values / values.iloc[0],
        "daily_return": returns,
        "total_value": values,
    })
    vector_metrics = VectorizedBacktestEngine._calc_metrics(nav_df, values.iloc[0], 0.03)
    assert vector_metrics["annual_return"] == pytest.approx(expected_annual)
    assert vector_metrics["sharpe_ratio"] == pytest.approx(expected_sharpe)


def test_daily_result_manager_uses_252_day_geometric_formula():
    manager = DailyResultManager(initial_cash=100_000)
    daily_df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "net_pnl": [5_000, 5_000],
        "balance": [105_000, 110_000],
        "commission": [0, 0],
        "turnover": [0, 0],
        "trade_count": [0, 0],
    })
    metrics = manager.calculate_statistics(daily_df)
    assert metrics["annual_return"] / 100 == pytest.approx(annualized_return(0.10, 2))
