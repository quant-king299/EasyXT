"""
因子中性化

提供行业中性化、市值中性化等功能。
"""

import pandas as pd
import numpy as np
from typing import List, Optional


class FactorNeutralization:
    """
    因子中性化

    通过回归方法剔除因子中的行业和市值影响。
    """

    @staticmethod
    def neutralize(factor_values: pd.Series,
                   industry_data: Optional[pd.Series] = None,
                   market_cap_data: Optional[pd.Series] = None,
                   method: str = 'regression') -> pd.Series:
        """
        因子中性化

        Args:
            factor_values: 因子值Series (index: 股票代码)
            industry_data: 行业分类Series (index: 股票代码, values: 行业)
            market_cap_data: 市值数据Series (index: 股票代码, values: 市值)
            method: 中性化方法 ('regression', 'group')

        Returns:
            中性化后的因子值Series
        """
        if method == 'regression':
            return FactorNeutralization._regression_neutralize(
                factor_values, industry_data, market_cap_data
            )
        elif method == 'group':
            return FactorNeutralization._group_neutralize(
                factor_values, industry_data, market_cap_data
            )
        else:
            raise ValueError(f"不支持的中性化方法: {method}")

    @staticmethod
    def _regression_neutralize(factor_values: pd.Series,
                               industry_data: Optional[pd.Series] = None,
                               market_cap_data: Optional[pd.Series] = None) -> pd.Series:
        """
        回归中性化

        对每个股票：
        factor_residual = factor - beta1 * industry_dummy - beta2 * log(market_cap)

        Args:
            factor_values: 因子值
            industry_data: 行业数据
            market_cap_data: 市值数据

        Returns:
            中性化后的因子值
        """
        # 对齐数据
        common_index = factor_values.dropna().index
        result = pd.Series(index=factor_values.index, dtype=float)

        if len(common_index) < 10:
            # 数据量太少，不做中性化
            return factor_values

        # 准备回归数据
        y = factor_values.loc[common_index].values

        # 构建回归矩阵
        X = []
        feature_names = []

        # 1. 行业哑变量
        if industry_data is not None and not industry_data.empty:
            # 获取行业列表
            industries = industry_data.loc[common_index].unique()
            industries = [ind for ind in industries if pd.notna(ind)]

            # 创建行业哑变量
            for industry in industries[:-1]:  # 避免完全共线性，去掉最后一个
                dummy = (industry_data.loc[common_index] == industry).astype(float)
                X.append(dummy.values)
                feature_names.append(f'industry_{industry}')

        # 2. 市值因子（对数市值）
        if market_cap_data is not None and not market_cap_data.empty:
            log_mc = np.log(market_cap_data.loc[common_index].replace(0, np.nan))
            log_mc = (log_mc - log_mc.mean()) / log_mc.std()  # 标准化
            X.append(log_mc.values)
            feature_names.append('log_market_cap')

        # 如果没有特征，返回原值
        if len(X) == 0:
            return factor_values

        # 转换为numpy数组
        X = np.array(X).T

        # 添加常数项
        X_with_const = np.column_stack([np.ones(len(X)), X])

        try:
            # 最小二乘回归
            coeffs = np.linalg.lstsq(X_with_const, y, rcond=None)[0]

            # 计算残差
            y_pred = X_with_const @ coeffs
            residuals = y - y_pred

            # 标准化残差
            residuals = (residuals - residuals.mean()) / residuals.std()

            # 填充结果
            result.loc[common_index] = residuals

            # NaN处理
            result = result.fillna(0)

            return result

        except Exception as e:
            print(f"⚠️ 回归中性化失败: {e}")
            return factor_values

    @staticmethod
    def _group_neutralize(factor_values: pd.Series,
                         industry_data: Optional[pd.Series] = None,
                         market_cap_data: Optional[pd.Series] = None) -> pd.Series:
        """
        分组中性化

        1. 行业中性化：在每个行业内标准化
        2. 市值中性化：在市值分组内标准化

        Args:
            factor_values: 因子值
            industry_data: 行业数据
            market_cap_data: 市值数据

        Returns:
            中性化后的因子值
        """
        result = factor_values.copy()

        # 1. 行业中性化
        if industry_data is not None and not industry_data.empty:
            result = FactorNeutralization._group_normalize(result, industry_data)

        # 2. 市值中性化
        if market_cap_data is not None and not market_cap_data.empty:
            # 将市值分为10组
            mc_groups = pd.qcut(market_cap_data, q=10, labels=False, duplicates='drop')
            result = FactorNeutralization._group_normalize(result, mc_groups)

        return result

    @staticmethod
    def _group_normalize(factor_values: pd.Series, group_data: pd.Series) -> pd.Series:
        """
        在分组内标准化

        Args:
            factor_values: 因子值
            group_data: 分组数据

        Returns:
            标准化后的因子值
        """
        result = pd.Series(index=factor_values.index, dtype=float)

        # 对每个分组进行标准化
        for group in group_data.unique():
            if pd.isna(group):
                continue

            # 获取该组的股票
            group_mask = group_data == group
            group_stocks = factor_values[group_mask].dropna()

            if len(group_stocks) < 3:
                # 该组股票太少，不做标准化
                result[group_mask] = factor_values[group_mask]
            else:
                # Z-score标准化
                group_mean = group_stocks.mean()
                group_std = group_stocks.std()

                if group_std > 0:
                    normalized = (group_stocks - group_mean) / group_std
                    result[group_stocks.index] = normalized
                else:
                    result[group_stocks.index] = 0

        return result
