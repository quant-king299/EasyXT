"""Compatibility exports for the project's canonical performance metrics."""

from core.performance_metrics import (
    DEFAULT_RISK_FREE_RATE,
    TRADING_DAYS_PER_YEAR,
    annualized_return,
    annualized_sharpe,
)

__all__ = [
    'DEFAULT_RISK_FREE_RATE',
    'TRADING_DAYS_PER_YEAR',
    'annualized_return',
    'annualized_sharpe',
]
