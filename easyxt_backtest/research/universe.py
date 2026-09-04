"""按历史时点解析 EasyXT 股票池。"""

from __future__ import annotations

from datetime import date
from typing import Iterable, Optional

import pandas as pd


REQUIRED_COLUMNS = {"symbol", "effective_from", "effective_to"}


def validate_universe_history(history: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(history.columns)
    if missing:
        raise ValueError(f"股票池历史缺少字段: {sorted(missing)}")
    starts = pd.to_datetime(history["effective_from"], errors="coerce")
    ends = pd.to_datetime(history["effective_to"], errors="coerce")
    if starts.isna().any() or ends.isna().any():
        raise ValueError("股票池生效日期不能为空")
    if (starts > ends).any():
        raise ValueError("股票池存在 effective_from 晚于 effective_to 的记录")


def universe_as_of(history: pd.DataFrame, as_of: str | date, *,
                   exclude: Optional[Iterable[str]] = None) -> list[str]:
    validate_universe_history(history)
    moment = pd.Timestamp(as_of)
    starts = pd.to_datetime(history["effective_from"])
    ends = pd.to_datetime(history["effective_to"])
    mask = (starts <= moment) & (ends >= moment)
    excluded = set(exclude or [])
    symbols = history.loc[mask, "symbol"].astype(str)
    return sorted({symbol for symbol in symbols if symbol not in excluded})
