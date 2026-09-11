"""Side-effect-free performance metrics shared by research and backtests."""

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 252
DEFAULT_RISK_FREE_RATE = 0.03


def annualized_return(total_return: float, periods: int,
                      annual_days: int = TRADING_DAYS_PER_YEAR) -> float:
    """Calculate annualized compound return."""
    if periods <= 0 or annual_days <= 0:
        return 0.0
    if total_return <= -1:
        return -1.0
    return (1.0 + float(total_return)) ** (annual_days / periods) - 1.0


def annualized_sharpe(daily_returns: pd.Series,
                      risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
                      annual_days: int = TRADING_DAYS_PER_YEAR) -> float:
    """Calculate annualized Sharpe ratio from daily excess returns."""
    returns = pd.Series(daily_returns, dtype=float).dropna()
    if returns.empty or annual_days <= 0 or risk_free_rate <= -1:
        return 0.0
    std = returns.std()
    if not np.isfinite(std) or std <= 0:
        return 0.0
    daily_risk_free = (1.0 + risk_free_rate) ** (1.0 / annual_days) - 1.0
    return float((returns.mean() - daily_risk_free) / std * np.sqrt(annual_days))
