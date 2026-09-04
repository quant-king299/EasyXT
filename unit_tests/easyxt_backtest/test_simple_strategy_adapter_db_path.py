"""Regression tests for SimpleFunctionAdapter's shared DuckDB path contract."""

from easyxt_backtest.simple_strategy_adapter import SimpleFunctionAdapter


def _select_nothing(frame, top_n, **kwargs):
    return []


def test_explicit_database_path_is_retained_without_loading_stock_data(tmp_path):
    """Stock strategies must use the caller's DuckDB snapshot, not a D: drive path."""
    db_path = tmp_path / "backtest.ddb"

    strategy = SimpleFunctionAdapter(
        _select_nothing,
        category="stock",
        db_path=db_path,
    )

    assert strategy._db_path == str(db_path)
