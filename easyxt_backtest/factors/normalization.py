"""
因子标准化

提供多种因子标准化方法。
"""

import pandas as pd
import numpy as np
from typing import Optional


class FactorNormalization:
    """
    因子标准化

    提供多种标准化方法：
    - Z-score标准化
    - Min-Max标准化
    - Rank标准化
    - Winsorize去极值
    """

    @staticmethod
    def zscore(series: pd.Series, inf_to_nan: bool = True) -> pd.Series:
        """
        Z-score标准化

        z = (x - mean) / std

        Args:
            series: 因子值Series
            inf_to_nan: 是否将inf转换为nan

        Returns:
            标准化后的Series
        """
        # 复制Series
        result = series.copy()

        # 计算均值和标准差
        mean = result.mean()
        std = result.std()

        if std == 0 or np.isnan(std):
            # 如果标准差为0，返回全0
            return pd.Series(np.zeros(len(result)), index=result.index)

        # Z-score标准化
        result = (result - mean) / std

        # 处理inf
        if inf_to_nan:
            result = result.replace([np.inf, -np.inf], np.nan)

        return result

    @staticmethod
    def min_max(series: pd.Series, min_val: float = 0, max_val: float = 1) -> pd.Series:
        """
        Min-Max标准化

        normalized = (x - min) / (max - min)

        Args:
            series: 因子值Series
            min_val: 目标最小值
            max_val: 目标最大值

        Returns:
            标准化后的Series
        """
        # 复制Series
        result = series.copy()

        # 计算最小值和最大值
        min_val_raw = result.min()
        max_val_raw = result.max()

        if max_val_raw == min_val_raw:
            # 如果所有值相同，返回常数
            return pd.Series([min_val] * len(result), index=result.index)

        # Min-Max标准化
        result = (result - min_val_raw) / (max_val_raw - min_val_raw)

        # 缩放到目标范围
        result = result * (max_val - min_val) + min_val

        return result

    @staticmethod
    def rank(series: pd.Series) -> pd.Series:
        """
        Rank标准化

        将因子值转换为排名（百分比）

        Args:
            series: 因子值Series

        Returns:
            标准化后的Series
        """
        # 计算排名
        ranks = series.rank(pct=True)

        return ranks

    @staticmethod
    def winsorize(series: pd.Series, limits: float = 0.05) -> pd.Series:
        """
        去极值（Winsorize）

        将超出指定分位数的值替换为分位数值

        Args:
            series: 因子值Series
            limits: 极值分位数（默认0.05，即上下5%）

        Returns:
            去极值后的Series
        """
        # 复制Series
        result = series.copy()

        # 计算分位数
        lower_bound = result.quantile(limits)
        upper_bound = result.quantile(1 - limits)

        # 替换极值
        result = result.clip(lower=lower_bound, upper=upper_bound)

        return result

    @staticmethod
    def normalize(series: pd.Series,
                 method: str = 'zscore',
                 winsorize_first: bool = True,
                 winsorize_limits: float = 0.05) -> pd.Series:
        """
        综合标准化方法

        先去极值，再标准化

        Args:
            series: 因子值Series
            method: 标准化方法 ('zscore', 'min_max', 'rank')
            winsorize_first: 是否先去极值
            winsorize_limits: 去极值的分位数

        Returns:
            标准化后的Series
        """
        result = series.copy()

        # 先去极值
        if winsorize_first:
            result = FactorNormalization.winsorize(result, winsorize_limits)

        # 标准化
        if method == 'zscore':
            result = FactorNormalization.zscore(result)
        elif method == 'min_max':
            result = FactorNormalization.min_max(result)
        elif method == 'rank':
            result = FactorNormalization.rank(result)
        else:
            raise ValueError(f"不支持的标准化方法: {method}")

        return result
