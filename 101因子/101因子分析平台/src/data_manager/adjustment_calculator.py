# -*- coding: utf-8 -*-
"""
复权计算器 - 支持前复权和后复权
"""

import pandas as pd
import numpy as np
from typing import Optional, Literal
from datetime import datetime


class AdjustmentCalculator:
    """复权计算器"""

    @staticmethod
    def apply_qfq(df: pd.DataFrame, dividends_df: pd.DataFrame) -> pd.DataFrame:
        """
        前复权（Quantitative Forward Adjustment）

        原理：保持当前价格不变，调整历史价格
        公式：复权因子 = 当日收盘价 / (当日收盘价 + 每股分红)

        Args:
            df: 原始数据（OHLCV），索引为时间
            dividends_df: 分红数据，包含 ex_date, dividend_per_share

        Returns:
            前复权后的DataFrame
        """
        if df.empty or dividends_df.empty:
            return df.copy()

        df_result = df.copy()

        # 确保索引是DatetimeIndex
        if not isinstance(df_result.index, pd.DatetimeIndex):
            df_result.index = pd.to_datetime(df_result.index)

        # 提取日期部分用于比较
        df_result['date_only'] = df_result.index.date

        # 按除权日排序（从早到晚）
        dividends_df = dividends_df.sort_values('ex_date')
        dividends_df['ex_date'] = pd.to_datetime(dividends_df['ex_date']).dt.date

        # 计算复权因子
        cumulative_factor = 1.0

        for _, div_row in dividends_df.iterrows():
            ex_date = div_row['ex_date']
            dividend = div_row['dividend_per_share']

            # 找到除权日的价格
            mask = df_result['date_only'] == ex_date

            if mask.any():
                # 使用除权日的收盘价计算因子
                ex_close = df_result.loc[mask, 'close'].iloc[0]

                if ex_close > 0:
                    # 前复权因子 = 除权前收盘价 / 除权后收盘价
                    # 除权后收盘价 = 除权前收盘价 - 每股分红
                    # 所以 factor = ex_close / (ex_close - dividend)
                    factor = ex_close / (ex_close - dividend)
                    cumulative_factor *= factor

                    # 调整除权日之前的所有价格
                    # 注意：前复权是调整"之前"的数据
                    df_result.loc[df_result['date_only'] < ex_date, ['open', 'high', 'low', 'close']] *= cumulative_factor

        # 删除临时列
        if 'date_only' in df_result.columns:
            df_result = df_result.drop(columns=['date_only'])

        # 重置索引名称
        df_result.index.name = 'time'

        return df_result

    @staticmethod
    def apply_hfq(df: pd.DataFrame, dividends_df: pd.DataFrame) -> pd.DataFrame:
        """
        后复权（Historical Forward Adjustment）

        原理：保持历史价格不变，调整当前价格
        公式：每次分红后，之后的所有价格都乘以因子

        Args:
            df: 原始数据（OHLCV），索引为时间
            dividends_df: 分红数据，包含 ex_date, dividend_per_share

        Returns:
            后复权后的DataFrame
        """
        if df.empty or dividends_df.empty:
            return df.copy()

        df_result = df.copy()

        # 确保索引是DatetimeIndex
        if not isinstance(df_result.index, pd.DatetimeIndex):
            df_result.index = pd.to_datetime(df_result.index)

        # 提取日期部分
        df_result['date_only'] = df_result.index.date

        # 按除权日排序（从早到晚）
        dividends_df = dividends_df.sort_values('ex_date')
        dividends_df['ex_date'] = pd.to_datetime(dividends_df['ex_date']).dt.date

        # 计算复权因子
        cumulative_factor = 1.0

        for _, div_row in dividends_df.iterrows():
            ex_date = div_row['ex_date']
            dividend = div_row['dividend_per_share']

            # 找到除权日的价格
            mask = df_result['date_only'] == ex_date

            if mask.any():
                ex_close = df_result.loc[mask, 'close'].iloc[0]

                if ex_close > 0:
                    # 后复权因子 = 除权后收盘价 / 除权前收盘价
                    # 除权后收盘价 = 除权前收盘价 - 每股分红
                    # 所以 factor = (ex_close - dividend) / ex_close
                    factor = (ex_close - dividend) / ex_close
                    cumulative_factor *= factor

                    # 调整除权日及之后的所有价格
                    # 注意：后复权是调整"之后"的数据
                    df_result.loc[df_result['date_only'] >= ex_date, ['open', 'high', 'low', 'close']] *= cumulative_factor

        # 删除临时列
        if 'date_only' in df_result.columns:
            df_result = df_result.drop(columns=['date_only'])

        # 重置索引名称
        df_result.index.name = 'time'

        return df_result

    @staticmethod
    def apply_adjustment(df: pd.DataFrame,
                         dividends_df: pd.DataFrame,
                         adjust_type: Literal['none', 'qfq', 'hfq'] = 'none') -> pd.DataFrame:
        """
        应用复权

        Args:
            df: 原始数据
            dividends_df: 分红数据
            adjust_type: 复权类型
                - 'none': 不复权
                - 'qfq': 前复权
                - 'hfq': 后复权

        Returns:
            复权后的数据
        """
        if df.empty:
            return df

        if adjust_type == 'none' or dividends_df.empty:
            return df.copy()

        if adjust_type == 'qfq':
            return AdjustmentCalculator.apply_qfq(df, dividends_df)
        elif adjust_type == 'hfq':
            return AdjustmentCalculator.apply_hfq(df, dividends_df)

        return df.copy()


def test_adjustment():
    """测试复权计算"""
    # 创建测试数据
    dates = pd.date_range('2024-01-01', periods=10, freq='D')
    df = pd.DataFrame({
        'open': [100] * 10,
        'high': [102] * 10,
        'low': [99] * 10,
        'close': [101] * 10,
        'volume': [1000000] * 10
    }, index=dates)

    # 模拟分红（1月5日分红10元）
    dividends = pd.DataFrame({
        'ex_date': ['2024-01-05'],
        'dividend_per_share': [10.0]
    })

    print("原始数据:")
    print(df.head(10))
    print()

    # 前复权
    df_qfq = AdjustmentCalculator.apply_qfq(df, dividends)
    print("前复权数据:")
    print(df_qfq.head(10))
    print()

    # 后复权
    df_hfq = AdjustmentCalculator.apply_hfq(df, dividends)
    print("后复权数据:")
    print(df_hfq.head(10))


if __name__ == '__main__':
    test_adjustment()
