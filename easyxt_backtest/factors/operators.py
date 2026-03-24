"""
时序算子库

提供Alpha因子计算所需的时序算子函数。
"""

import pandas as pd
import numpy as np


def ts_sum(df: pd.Series, window: int) -> pd.Series:
    """时间序列求和"""
    return df.rolling(window=window).sum()


def sma(df: pd.Series, window: int) -> pd.Series:
    """简单移动平均"""
    return df.rolling(window=window).mean()


def stddev(df: pd.Series, window: int) -> pd.Series:
    """标准差"""
    return df.rolling(window=window).std()


def correlation(x: pd.Series, y: pd.Series, window: int) -> pd.Series:
    """相关系数"""
    return x.rolling(window=window).corr(y)


def covariance(x: pd.Series, y: pd.Series, window: int) -> pd.Series:
    """协方差"""
    return x.rolling(window=window).cov(y)


def rolling_rank(df: pd.Series, window: int) -> pd.Series:
    """滚动排名（返回最后一天在窗口内的排名）"""
    return df.rolling(window=window).apply(lambda x: x.rank().iloc[-1])


def ts_min(df: pd.Series, window: int) -> pd.Series:
    """时间序列最小值"""
    return df.rolling(window=window).min()


def ts_max(df: pd.Series, window: int) -> pd.Series:
    """时间序列最大值"""
    return df.rolling(window=window).max()


def delta(df: pd.Series, period: int) -> pd.Series:
    """差分"""
    return df.diff(periods=period)


def delay(df: pd.Series, period: int) -> pd.Series:
    """延迟"""
    return df.shift(periods=period)


def rank(df: pd.Series) -> pd.Series:
    """
    横截面排名

    对于MultiIndex [date, symbol]的数据，按日期分组排名
    对于普通Series，直接排名
    """
    if isinstance(df.index, pd.MultiIndex) and df.index.nlevels > 1:
        # 按第一个级别（通常是日期）进行分组排名
        return df.groupby(level=0).rank(pct=True)
    else:
        return df.rank(pct=True)


def scale(df: pd.Series, scale_factor: float = 1) -> pd.Series:
    """缩放"""
    return df / df.abs().sum() * scale_factor


def decay_linear(df: pd.Series, window: int) -> pd.Series:
    """线性衰减加权移动平均"""
    weights = np.arange(1, window + 1)
    weights = weights / weights.sum()

    def weighted_mean(x):
        if len(x) < window:
            return np.nan
        return (x * weights).sum()

    return df.rolling(window=window).apply(weighted_mean, raw=True)


def ts_argmax(df: pd.Series, window: int) -> pd.Series:
    """滚动最大值位置"""
    return df.rolling(window=window).apply(lambda x: x.argmax())


def ts_argmin(df: pd.Series, window: int) -> pd.Series:
    """滚动最小值位置"""
    return df.rolling(window=window).apply(lambda x: x.argmin())


def sign(df: pd.Series) -> pd.Series:
    """符号函数"""
    return np.sign(df)


def abs_series(df: pd.Series) -> pd.Series:
    """绝对值"""
    return df.abs()


def log_series(df: pd.Series) -> pd.Series:
    """对数"""
    return np.log(df)


def ts_product(df: pd.Series, window: int) -> pd.Series:
    """时间序列乘积"""
    return df.rolling(window=window).apply(np.prod, raw=True)
