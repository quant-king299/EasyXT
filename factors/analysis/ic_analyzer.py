"""
IC（Information Coefficient）分析器

计算和分析因子的预测能力：
- IC：因子值与未来收益率的相关系数（Spearman/Pearson）
- IR：信息比率（IC均值 / IC标准差）
- IC半衰期：IC的衰减周期
- IC时序分析：IC的稳定性

参考：
- Grinold, R. C., & Kahn, R. N. (2000). Active Portfolio Management.

使用示例：
>>> from factors.analysis import ICAnalyzer
>>> analyzer = ICAnalyzer(data_manager)
>>> ic_series = analyzer.calculate_ic(factor_df, return_df)
>>> ic_stats = analyzer.calculate_ic_statistics(ic_series)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
from scipy import stats
import warnings

warnings.filterwarnings('ignore')


class ICAnalyzer:
    """
    IC分析器

    计算因子与收益率的相关性，评估因子预测能力
    """

    def __init__(self, data_manager=None):
        """
        初始化

        参数:
            data_manager: 数据管理器（可选）
        """
        self.data_manager = data_manager

    def calculate_ic(self,
                      factor_df: pd.DataFrame,
                      return_df: pd.DataFrame,
                      method: str = 'spearman',
                      min_stock_num: int = 10) -> pd.Series:
        """
        计算IC序列

        参数:
            factor_df: 因子值 DataFrame
                       格式1: Date × Stock（wide格式）
                       格式2: (date, stock)两列（long格式）
            return_df: 未来收益率 DataFrame
                       格式同factor_df
            method: 'spearman'（秩相关系数）或 'pearson'（线性相关系数）
            min_stock_num: 每期最少股票数量

        返回:
            pd.Series: IC序列（索引为日期）
        """
        # 转换为wide格式
        factor_wide = self._to_wide_format(factor_df, value_col='factor')
        return_wide = self._to_wide_format(return_df, value_col='return')

        if factor_wide is None or return_wide is None:
            return pd.Series(dtype=float)

        # 对齐日期
        common_dates = factor_wide.index.intersection(return_wide.index)
        if len(common_dates) == 0:
            print("[WARNING] factor_df和return_df没有共同的日期")
            return pd.Series(dtype=float)

        # 计算每日IC
        ic_series = []

        for date in common_dates:
            factor_values = factor_wide.loc[date].dropna()
            return_values = return_wide.loc[date].dropna()

            # 对齐股票
            common_stocks = factor_values.index.intersection(return_values.index)

            if len(common_stocks) < min_stock_num:
                ic_series.append(np.nan)
                continue

            factor_vals = factor_values.loc[common_stocks]
            return_vals = return_values.loc[common_stocks]

            # 计算相关系数
            if method == 'spearman':
                ic, _ = stats.spearmanr(factor_vals, return_vals)
            elif method == 'pearson':
                ic, _ = stats.pearsonr(factor_vals, return_vals)
            else:
                raise ValueError(f"不支持的method: {method}")

            ic_series.append(ic)

        return pd.Series(ic_series, index=common_dates)

    def calculate_ic_statistics(self,
                                  ic_series: pd.Series,
                                  annual_trading_days: int = 250) -> Dict[str, float]:
        """
        计算IC统计指标

        参数:
            ic_series: IC序列
            annual_trading_days: 年交易日数（用于年化）

        返回:
            dict: {
                'ic_mean': IC均值,
                'ic_std': IC标准差,
                'ir': 信息比率（IC均值/IC标准差）,
                'ic_mean_annual': 年化IC均值,
                'ir_annual': 年化信息比率,
                't_stat': t统计量,
                'p_value': p值,
                'positive_ratio': IC为正的比例
            }
        """
        # 去除NaN
        ic_valid = ic_series.dropna()

        if len(ic_valid) == 0:
            return {
                'ic_mean': np.nan,
                'ic_std': np.nan,
                'ir': np.nan,
                'ic_mean_annual': np.nan,
                'ir_annual': np.nan,
                't_stat': np.nan,
                'p_value': np.nan,
                'positive_ratio': np.nan,
                'n_obs': 0
            }

        # 基础统计
        ic_mean = ic_valid.mean()
        ic_std = ic_valid.std()
        ir = ic_mean / ic_std if ic_std > 0 else np.nan

        # 年化
        ic_mean_annual = ic_mean * np.sqrt(annual_trading_days)
        ir_annual = ir * np.sqrt(annual_trading_days)

        # t检验
        from scipy import stats
        t_stat, p_value = stats.ttest_1samp(ic_valid, 0)

        # IC为正的比例
        positive_ratio = (ic_valid > 0).sum() / len(ic_valid)

        return {
            'ic_mean': ic_mean,
            'ic_std': ic_std,
            'ir': ir,
            'ic_mean_annual': ic_mean_annual,
            'ir_annual': ir_annual,
            't_stat': t_stat,
            'p_value': p_value,
            'positive_ratio': positive_ratio,
            'n_obs': len(ic_valid)
        }

    def ic_half_life(self,
                      ic_series: pd.Series,
                      max_lag: int = 200) -> Dict[str, float]:
        """
        计算IC半衰期

        IC半衰期：自相关系数衰减到一半所需的滞后天数

        参数:
            ic_series: IC序列
            max_lag: 最大滞后天数

        返回:
            dict: {
                'half_life': 半衰期（天）,
                'acf': 自相关系数序列
            }
        """
        ic_valid = ic_series.dropna()

        if len(ic_valid) < 20:
            return {
                'half_life': np.nan,
                'acf': pd.Series(dtype=float)
            }

        # 计算自相关系数
        acf_values = []
        lags = []

        for lag in range(1, min(max_lag, len(ic_valid) // 2)):
            # 计算滞后相关性
            ic_lead = ic_valid.iloc[:-lag]
            ic_lag = ic_valid.iloc[lag:]

            if len(ic_lead) > 0:
                corr, _ = stats.pearsonr(ic_lead, ic_lag)
                acf_values.append(corr)
                lags.append(lag)

        acf = pd.Series(acf_values, index=lags)

        # 找到半衰期（相关系数首次降到0.5以下）
        half_life = np.nan

        for lag, corr_value in zip(lags, acf_values):
            if abs(corr_value) < 0.5:
                half_life = lag
                break

        return {
            'half_life': half_life,
            'acf': acf
        }

    def ic_decay_analysis(self,
                           ic_series: pd.Series,
                           n_lags: int = 10) -> pd.DataFrame:
        """
        IC衰减分析

        分析因子在不同预测周期下的IC值

        参数:
            ic_series: 各个预测周期的IC序列（MultiIndex）
                       或单个IC序列（需要配合factor_df和return_df计算）
            n_lags: 分析的滞后周期数

        返回:
            pd.DataFrame: 各周期的IC统计
        """
        # 这里简化处理，返回单周期的IC统计
        # 实际应用中，需要计算不同前瞻期（1日、5日、10日等）的IC

        if not isinstance(ic_series.index, pd.MultiIndex):
            # 单周期IC
            stats = self.calculate_ic_statistics(ic_series)
            return pd.DataFrame([stats])

        # 多周期IC
        results = []

        for lag in range(1, n_lags + 1):
            # 提取对应周期的IC
            # 这里需要根据实际数据结构调整
            pass

        return pd.DataFrame()

    def _to_wide_format(self,
                         df: pd.DataFrame,
                         value_col: str = 'value') -> Optional[pd.DataFrame]:
        """
        转换为wide格式（Date × Stock）

        参数:
            df: DataFrame
            value_col: 值列名

        返回:
            pd.DataFrame: wide格式
        """
        if df is None or df.empty:
            return None

        # 检查是否已经是wide格式
        if isinstance(df.index, pd.DatetimeIndex) or isinstance(df.index, pd.Index):
            # 假设列名是股票代码
            if not df.select_dtypes(include=[np.number]).empty:
                return df

        # long格式转换wide
        # 期望的列：date, stock_code, factor/value
        try:
            if 'date' in df.columns and 'stock_code' in df.columns:
                pivot_df = df.pivot(
                    index='date',
                    columns='stock_code',
                    values=value_col
                )
                return pivot_df

            # 如果有factor列，尝试使用
            elif 'factor' in df.columns:
                pivot_df = df.pivot(
                    index='date',
                    columns='stock_code',
                    values='factor'
                )
                return pivot_df

            else:
                # 尝试自动识别
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) == 1:
                    pivot_df = df.pivot(
                        index=df.columns[0],  # 假设第一列是date
                        columns=df.columns[1],  # 假设第二列是stock_code
                        values=numeric_cols[0]
                    )
                    return pivot_df

        except Exception as e:
            print(f"[WARNING] 转换为wide格式失败: {e}")
            return None

        return None

    def calculate_rank_ic(self,
                          factor_df: pd.DataFrame,
                          return_df: pd.DataFrame,
                          min_stock_num: int = 10) -> pd.Series:
        """
        计算Rank IC（等价于Spearman相关系数）

        参数:
            factor_df: 因子值
            return_df: 收益率
            min_stock_num: 最少股票数

        返回:
            pd.Series: Rank IC序列
        """
        return self.calculate_ic(
            factor_df,
            return_df,
            method='spearman',
            min_stock_num=min_stock_num
        )

    def calculate_normal_ic(self,
                             factor_df: pd.DataFrame,
                             return_df: pd.DataFrame,
                             min_stock_num: int = 10) -> pd.Series:
        """
        计算Normal IC（Pearson相关系数）

        参数:
            factor_df: 因子值
            return_df: 收益率
            min_stock_num: 最少股票数

        返回:
            pd.Series: Normal IC序列
        """
        return self.calculate_ic(
            factor_df,
            return_df,
            method='pearson',
            min_stock_num=min_stock_num
        )


# ============================================================
# 便捷函数
# ============================================================

def calculate_ic(factor_df: pd.DataFrame,
                 return_df: pd.DataFrame,
                 method: str = 'spearman') -> pd.Series:
    """
    便捷函数：计算IC序列

    参数:
        factor_df: 因子值
        return_df: 收益率
        method: 'spearman' 或 'pearson'

    返回:
        pd.Series: IC序列
    """
    analyzer = ICAnalyzer()
    return analyzer.calculate_ic(factor_df, return_df, method=method)


def calculate_ic_statistics(ic_series: pd.Series) -> Dict[str, float]:
    """
    便捷函数：计算IC统计指标

    参数:
        ic_series: IC序列

    返回:
        dict: IC统计指标
    """
    analyzer = ICAnalyzer()
    return analyzer.calculate_ic_statistics(ic_series)


if __name__ == "__main__":
    print("=" * 70)
    print(" " * 25 + "IC分析器")
    print("=" * 70)

    print("\n[功能说明]")
    print("- IC（Information Coefficient）：因子与收益率的相关系数")
    print("- Rank IC：Spearman秩相关系数（常用，更稳健）")
    print("- Normal IC：Pearson线性相关系数")
    print("- IR（Information Ratio）：IC均值 / IC标准差")
    print("- IC半衰期：IC衰减到一半所需天数")

    print("\n[IC评价标准]")
    print("  |IC| > 0.05 : 强预测能力")
    print("  |IC| > 0.03 : 较强预测能力")
    print("  |IC| > 0.02 : 有一定预测能力")
    print("  |IC| < 0.02 : 预测能力较弱")

    print("\n[IR评价标准]")
    print("  IR > 1.0 : 优秀")
    print("  IR > 0.5 : 良好")
    print("  IR > 0.3 : 一般")
    print("  IR < 0.3 : 较差")

    print("\n[使用示例]")
    print("""
    from factors.analysis import ICAnalyzer

    analyzer = ICAnalyzer()

    # 计算Rank IC
    ic_series = analyzer.calculate_rank_ic(factor_df, return_df)

    # 计算IC统计
    ic_stats = analyzer.calculate_ic_statistics(ic_series)
    print(f"IC均值: {ic_stats['ic_mean']:.4f}")
    print(f"IR: {ic_stats['ir']:.4f}")
    print(f"t统计量: {ic_stats['t_stat']:.4f}")

    # 计算IC半衰期
    half_life = analyzer.ic_half_life(ic_series)
    print(f"IC半衰期: {half_life['half_life']:.0f}天")
    """)

    print("\n" + "=" * 70)
