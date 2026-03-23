"""
权重分配方法

实现多种组合权重分配方法。
"""

from typing import List, Dict
import pandas as pd
import numpy as np


class WeightMethods:
    """
    权重分配方法

    支持：
    - equal: 等权重
    - equal_risk: 等风险权重
    - market_cap: 市值加权
    - factor_score: 因子得分加权
    """

    @staticmethod
    def equal_weight(stocks: List[str]) -> pd.Series:
        """
        等权重分配

        Args:
            stocks: 股票列表

        Returns:
            Series: 股票代码到权重的映射
        """
        n = len(stocks)
        weight = 1.0 / n

        return pd.Series([weight] * n, index=stocks)

    @staticmethod
    def equal_risk_weight(stocks: List[str],
                          returns_data: pd.DataFrame) -> pd.Series:
        """
        等风险权重分配

        根据历史波动率倒数分配权重

        Args:
            stocks: 股票列表
            returns_data: 收益率数据 DataFrame (index=日期, columns=股票)

        Returns:
            Series: 股票代码到权重的映射
        """
        # 计算每只股票的波动率
        volatilities = returns_data[stocks].std()

        # 计算风险权重（波动率倒数）
        risk_weights = 1.0 / volatilities

        # 归一化
        risk_weights = risk_weights / risk_weights.sum()

        return risk_weights

    @staticmethod
    def market_cap_weight(stocks: List[str],
                          market_cap_data: pd.Series) -> pd.Series:
        """
        市值加权

        Args:
            stocks: 股票列表
            market_cap_data: 市值数据 Series (index=股票)

        Returns:
            Series: 股票代码到权重的映射
        """
        # 获取选中股票的市值
        mc = market_cap_data.loc[stocks]

        # 归一化
        weights = mc / mc.sum()

        return weights

    @staticmethod
    def factor_score_weight(stocks: List[str],
                            factor_scores: pd.Series) -> pd.Series:
        """
        因子得分加权

        得分越高，权重越大

        Args:
            stocks: 股票列表
            factor_scores: 因子得分 Series (index=股票)

        Returns:
            Series: 股票代码到权重的映射
        """
        # 获取选中股票的得分
        scores = factor_scores.loc[stocks]

        # 将得分转换为正数（最小为0）
        scores = scores - scores.min()

        # 归一化
        weights = scores / scores.sum()

        return weights

    @staticmethod
    def apply_weight_limits(weights: pd.Series,
                           max_weight: float = 0.2,
                           min_weight: float = 0.0) -> pd.Series:
        """
        应用权重限制

        Args:
            weights: 原始权重
            max_weight: 最大权重
            min_weight: 最小权重

        Returns:
            调整后的权重
        """
        # 限制最大权重
        weights = weights.clip(upper=max_weight)

        # 限制最小权重
        if min_weight > 0:
            weights = weights.clip(lower=min_weight)

            # 重新归一化
            weights = weights / weights.sum()

        return weights
