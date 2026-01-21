"""
数据工具函数
提供数据处理、转换等常用功能
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import sys
import os


def align_factor_with_prices(factor_data: pd.Series, price_data: pd.DataFrame) -> Tuple[pd.Series, pd.DataFrame]:
    """
    对齐因子数据和价格数据
    
    Args:
        factor_data: 因子数据 (Series)，索引为[date, symbol]
        price_data: 价格数据 (DataFrame)，索引为[date, symbol]
        
    Returns:
        Tuple[pd.Series, pd.DataFrame]: 对齐后的因子数据和价格数据
    """
    # 对齐两个数据框的索引
    aligned_factor, aligned_price = factor_data.align(price_data, join='inner', axis=0)
    
    # 过滤掉任何一方的NaN值
    mask = ~(aligned_factor.isna() | aligned_price.isna().any(axis=1))
    
    return aligned_factor[mask], aligned_price[mask]


def neutralize_factor(factor_data: pd.Series, by: pd.DataFrame = None, 
                     sector_data: pd.Series = None, industry_data: pd.Series = None) -> pd.Series:
    """
    中性化因子（去除行业、市值等影响）
    
    Args:
        factor_data: 因子数据，索引为[date, symbol]
        by: 用于中性化的其他因子数据
        sector_data: 行业数据
        industry_data: 行业数据
        
    Returns:
        pd.Series: 中性化后的因子数据
    """
    result = factor_data.copy()
    
    # 按日期分组进行中性化
    dates = factor_data.index.get_level_values(0).unique()
    
    for date in dates:
        date_mask = factor_data.index.get_level_values(0) == date
        current_factors = factor_data[date_mask]
        
        # 这里简化实现，仅进行截面标准化
        mean_val = current_factors.mean()
        std_val = current_factors.std()
        if std_val != 0 and not pd.isna(std_val):
            normalized = (current_factors - mean_val) / std_val
            result[date_mask] = normalized
    
    return result


def winsorize_series(series: pd.Series, limits: Tuple[float, float] = (0.05, 0.05)) -> pd.Series:
    """
    Winsorize处理（极端值处理）
    
    Args:
        series: 输入序列
        limits: 去除两端的百分比 (lower, upper)
        
    Returns:
        pd.Series: 处理后的序列
    """
    from scipy.stats.mstats import winsorize
    
    # 按日期分组进行winsorize
    if isinstance(series.index, pd.MultiIndex):
        dates = series.index.get_level_values(0).unique()
        result = series.copy()
        
        for date in dates:
            date_mask = series.index.get_level_values(0) == date
            current_data = series[date_mask]
            
            # 对当前截面数据进行winsorize
            if len(current_data) > 1:  # 至少需要2个数据点
                winsorized = winsorize(current_data, limits=limits)
                result[date_mask] = winsorized
    else:
        result = pd.Series(winsorize(series, limits=limits), index=series.index)
    
    return result


def zscore_normalize(series: pd.Series) -> pd.Series:
    """
    Z-Score标准化
    
    Args:
        series: 输入序列
        
    Returns:
        pd.Series: Z-Score标准化后的序列
    """
    # 按日期分组进行标准化
    if isinstance(series.index, pd.MultiIndex):
        dates = series.index.get_level_values(0).unique()
        result = series.copy()
        
        for date in dates:
            date_mask = series.index.get_level_values(0) == date
            current_data = series[date_mask]
            
            mean_val = current_data.mean()
            std_val = current_data.std()
            
            if std_val != 0 and not pd.isna(std_val):
                standardized = (current_data - mean_val) / std_val
                result[date_mask] = standardized
            else:
                result[date_mask] = 0.0  # 如果标准差为0，设置为0
    else:
        mean_val = series.mean()
        std_val = series.std()
        if std_val != 0 and not pd.isna(std_val):
            result = (series - mean_val) / std_val
        else:
            result = pd.Series([0.0] * len(series), index=series.index)
    
    return result


def rank_transform(series: pd.Series, method: str = 'average', ascending: bool = True) -> pd.Series:
    """
    排序转换
    
    Args:
        series: 输入序列
        method: 排序方法 ('average', 'min', 'max', 'first', 'dense')
        ascending: 是否升序
        
    Returns:
        pd.Series: 排序转换后的序列
    """
    # 按日期分组进行排序转换
    if isinstance(series.index, pd.MultiIndex):
        dates = series.index.get_level_values(0).unique()
        result = series.copy()
        
        for date in dates:
            date_mask = series.index.get_level_values(0) == date
            current_data = series[date_mask]
            
            ranked = current_data.rank(method=method, ascending=ascending)
            result[date_mask] = ranked
    else:
        result = series.rank(method=method, ascending=ascending)
    
    return result


def industry_dummies(industry_series: pd.Series) -> pd.DataFrame:
    """
    创建行业哑变量
    
    Args:
        industry_series: 行业数据，索引为[date, symbol]，值为行业名称
        
    Returns:
        pd.DataFrame: 行业哑变量矩阵
    """
    # 透视行业数据
    industry_pivot = industry_series.to_frame(name='industry').reset_index()
    industry_dummies = pd.get_dummies(industry_pivot, columns=['industry'])
    
    # 重新设置多级索引
    industry_dummies.set_index(['date', 'symbol'], inplace=True)
    
    return industry_dummies


def shift_groupby(data: pd.Series, groups: pd.Series, periods: int = 1) -> pd.Series:
    """
    按组进行shift操作
    
    Args:
        data: 输入数据
        groups: 分组依据
        periods: shift的期数
        
    Returns:
        pd.Series: shift后的数据
    """
    return data.groupby(groups).shift(periods)


def calculate_turnover(factor_data: pd.Series, top_n: int = 10) -> pd.Series:
    """
    计算因子换手率
    
    Args:
        factor_data: 因子数据，索引为[date, symbol]
        top_n: 前N只股票
        
    Returns:
        pd.Series: 换手率序列
    """
    # 按日期获取因子排名
    ranked_data = factor_data.groupby(level=0).rank(ascending=False, method='min')
    
    # 获取每天的前N名
    top_stocks = ranked_data[ranked_data <= top_n]
    
    # 计算换手率（基于前N名的变化）
    turnover_rates = []
    
    dates = sorted(top_stocks.index.get_level_values(0).unique())
    
    for i in range(1, len(dates)):
        current_date = dates[i]
        prev_date = dates[i-1]
        
        current_top = set(top_stocks[top_stocks.index.get_level_values(0) == current_date].index.get_level_values(1))
        prev_top = set(top_stocks[top_stocks.index.get_level_values(0) == prev_date].index.get_level_values(1))
        
        # 计算换手率
        intersection = current_top.intersection(prev_top)
        turnover = 1 - len(intersection) / top_n if top_n > 0 else 0
        
        turnover_rates.append({'date': current_date, 'turnover': turnover})
    
    if turnover_rates:
        turnover_df = pd.DataFrame(turnover_rates)
        turnover_df.set_index('date', inplace=True)
        return turnover_df['turnover']
    else:
        return pd.Series(dtype=float)


# 测试代码
if __name__ == '__main__':
    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=10, freq='D')
    symbols = ['A', 'B', 'C', 'D', 'E']
    
    # 创建多级索引
    index = pd.MultiIndex.from_product([dates, symbols], names=['date', 'symbol'])
    
    # 生成测试数据
    np.random.seed(42)
    test_data = pd.Series(
        np.random.randn(len(index)), 
        index=index,
        name='factor'
    )
    
    print("测试数据形状:", test_data.shape)
    print("测试数据头部:")
    print(test_data.head(10))
    
    # 测试Z-Score标准化
    print("\n=== 测试Z-Score标准化 ===")
    zscored = zscore_normalize(test_data)
    print(f"Z-Score标准化后均值: {zscored.groupby(level=0).mean().mean():.6f}")
    print(f"Z-Score标准化后标准差: {zscored.groupby(level=0).std().mean():.6f}")
    
    # 测试排序转换
    print("\n=== 测试排序转换 ===")
    ranked = rank_transform(test_data)
    print(f"排序转换后范围: [{ranked.groupby(level=0).min().min()}, {ranked.groupby(level=0).max().max()}]")
    
    # 测试Winsorize
    print("\n=== 测试Winsorize ===")
    extreme_data = test_data.copy()
    extreme_data.iloc[::5] = extreme_data.iloc[::5] * 10  # 制造一些极端值
    winsorized = winsorize_series(extreme_data, limits=(0.1, 0.1))
    print(f"Winsorize前极值: {extreme_data.abs().max():.4f}")
    print(f"Winsorize后极值: {winsorized.abs().max():.4f}")
    
    # 测试换手率计算
    print("\n=== 测试换手率计算 ===")
    turnover = calculate_turnover(test_data, top_n=2)
    print(f"换手率序列长度: {len(turnover)}")
    print(f"平均换手率: {turnover.mean():.4f}")
    
    print("\n数据工具测试完成!")