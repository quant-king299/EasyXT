"""
特质波动率因子模块

特质波动率（Idiosyncratic Volatility）是指股票收益率中不能被市场因子解释的部分的波动率。
这是衡量股票特有风险的重要指标。

主要功能：
- 计算个股特质波动率
- 基于市场模型回归分解系统性风险和特质风险
- 提供多种时间窗口的特质波动率
- 支持滚动回归计算
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import sys
import os

# 添加项目路径
project_path = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_path)

try:
    from statsmodels.regression.linear_model import OLS
    from statsmodels.tools import add_constant
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    print("[警告] statsmodels未安装，将使用简化方法计算特质波动率")

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class SpecificVolatilityCalculator:
    """
    特质波动率计算器

    计算股票的特质波动率（Idiosyncratic Volatility）
    """

    def __init__(self,
                 market_return_column: str = 'market_return',
                 window: int = 20,
                 min_obs: int = 10):
        """
        初始化特质波动率计算器

        参数:
            market_return_column: 市场收益率列名
            window: 回归窗口长度（交易日）
            min_obs: 最小观测值数量
        """
        self.market_return_column = market_return_column
        self.window = window
        self.min_obs = min_obs

    def calculate_specific_volatility(self,
                                     stock_returns: pd.Series,
                                     market_returns: pd.Series,
                                     window: Optional[int] = None) -> pd.Series:
        """
        计算特质波动率

        参数:
            stock_returns: 个股收益率序列
            market_returns: 市场收益率序列
            window: 回归窗口（可选，默认使用初始化时的窗口）

        返回:
            pd.Series: 特质波动率序列
        """
        if window is None:
            window = self.window

        # 对齐数据
        aligned_data = pd.DataFrame({
            'stock': stock_returns,
            'market': market_returns
        }).dropna()

        if len(aligned_data) < window:
            return pd.Series(dtype=float)

        # 滚动回归计算特质波动率
        specific_vol_series = pd.Series(dtype=float)

        for i in range(window, len(aligned_data)):
            window_data = aligned_data.iloc[i-window:i]

            if len(window_data.dropna()) < self.min_obs:
                continue

            # 计算特质波动率
            spec_vol = self._calculate_single_period(
                window_data['stock'].values,
                window_data['market'].values
            )

            specific_vol_series.loc[aligned_data.index[i]] = spec_vol

        return specific_vol_series

    def _calculate_single_period(self,
                                 stock_returns: np.ndarray,
                                 market_returns: np.ndarray) -> float:
        """
        计算单个时间段的特质波动率

        参数:
            stock_returns: 个股收益率数组
            market_returns: 市场收益率数组

        返回:
            float: 特质波动率（年化标准差）
        """
        # 移除NaN值
        mask = ~(np.isnan(stock_returns) | np.isnan(market_returns))
        stock_clean = stock_returns[mask]
        market_clean = market_returns[mask]

        if len(stock_clean) < self.min_obs:
            return np.nan

        # 方法1：使用statsmodels进行OLS回归
        if STATSMODELS_AVAILABLE:
            try:
                X = add_constant(market_clean)
                model = OLS(stock_clean, X).fit()

                # 获取残差
                residuals = model.resid

                # 计算特质波动率（年化）
                specific_vol = np.std(residuals) * np.sqrt(252)

                return specific_vol
            except Exception:
                pass

        # 方法2：使用scipy
        if SCIPY_AVAILABLE:
            try:
                slope, intercept, r_value, p_value, std_err = stats.linregress(
                    market_clean, stock_clean
                )

                # 计算残差
                predicted = intercept + slope * market_clean
                residuals = stock_clean - predicted

                # 计算特质波动率（年化）
                specific_vol = np.std(residuals) * np.sqrt(252)

                return specific_vol
            except Exception:
                pass

        # 方法3：简化方法（使用协方差）
        try:
            # 计算beta
            cov_matrix = np.cov(stock_clean, market_clean)
            beta = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else 1.0

            # 计算系统性收益
            systematic_return = beta * market_clean

            # 计算特质收益
            specific_return = stock_clean - systematic_return

            # 计算特质波动率（年化）
            specific_vol = np.std(specific_return) * np.sqrt(252)

            return specific_vol
        except Exception:
            return np.nan

    def calculate_batch_specific_volatility(self,
                                           returns_df: pd.DataFrame,
                                           market_returns: pd.Series,
                                           window: Optional[int] = None) -> pd.DataFrame:
        """
        批量计算多只股票的特质波动率

        参数:
            returns_df: 收益率DataFrame（列为股票，索引为日期）
            market_returns: 市场收益率序列
            window: 回归窗口

        返回:
            pd.DataFrame: 特质波动率DataFrame
        """
        if window is None:
            window = self.window

        specific_vol_df = pd.DataFrame()

        for stock in returns_df.columns:
            stock_returns = returns_df[stock]

            spec_vol = self.calculate_specific_volatility(
                stock_returns, market_returns, window
            )

            if not spec_vol.empty:
                specific_vol_df[stock] = spec_vol

        return specific_vol_df


class SpecificVolatilityFactor:
    """
    特质波动率因子

    为101因子平台提供的特质波动率因子接口
    """

    def __init__(self,
                 windows: List[int] = [20, 60, 120]):
        """
        初始化特质波动率因子

        参数:
            windows: 计算窗口列表 [20日, 60日, 120日]
        """
        self.windows = windows
        self.calculator = SpecificVolatilityCalculator()

    def calculate(self,
                 data: pd.DataFrame,
                 market_return_col: str = 'market_return') -> pd.DataFrame:
        """
        计算特质波动率因子

        参数:
            data: 包含股票收益率和市场收益率的数据
                  格式1: MultiIndex (date, stock_code) with columns [return, market_return]
                  格式2: DataFrame with columns [date, stock_code, return, market_return]
            market_return_col: 市场收益率列名

        返回:
            pd.DataFrame: 特质波动率因子值
        """
        # 数据预处理
        if isinstance(data.index, pd.MultiIndex):
            df = data.reset_index()
        else:
            df = data.copy()

        # 确保有必要的列
        required_cols = ['date', 'stock_code']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"缺少必要列: {col}")

        # 确保有收益率列
        if 'return' not in df.columns:
            raise ValueError("缺少收益率列: return")

        if market_return_col not in df.columns:
            raise ValueError(f"缺少市场收益率列: {market_return_col}")

        # 转换为宽表格式
        pivot_df = df.pivot(index='date', columns='stock_code', values='return')
        market_series = df.groupby('date')[market_return_col].first()

        # 计算不同窗口的特质波动率
        result_df = pd.DataFrame()

        for window in self.windows:
            self.calculator.window = window
            spec_vol = self.calculator.calculate_batch_specific_volatility(
                pivot_df, market_series, window
            )

            if not spec_vol.empty:
                # 重命名列
                factor_name = f'specific_volatility_{window}d'
                spec_vol_t = spec_vol.T
                spec_vol_t.columns = [factor_name]
                result_df = pd.concat([result_df, spec_vol_t], axis=1)

        return result_df

    def calculate_single_stock(self,
                              stock_code: str,
                              data: pd.DataFrame,
                              window: int = 20) -> pd.Series:
        """
        计算单只股票的特质波动率

        参数:
            stock_code: 股票代码
            data: 价格/收益率数据
            window: 计算窗口

        返回:
            pd.Series: 特质波动率序列
        """
        if 'return' not in data.columns:
            # 如果没有收益率列，计算收益率
            if 'close' in data.columns:
                data = data.copy()
                data['return'] = data['close'].pct_change()
            else:
                raise ValueError("数据中缺少close或return列")

        if 'market_return' not in data.columns:
            # 如果没有市场收益率，假设为0（简化处理）
            data = data.copy()
            data['market_return'] = 0.0

        stock_returns = data.set_index('date')['return']
        market_returns = data.set_index('date')['market_return']

        self.calculator.window = window
        spec_vol = self.calculator.calculate_specific_volatility(
            stock_returns, market_returns, window
        )

        return spec_vol


# 便捷函数
def calculate_specific_volatility_factor(data: pd.DataFrame,
                                        windows: List[int] = [20, 60, 120]) -> pd.DataFrame:
    """
    计算特质波动率因子的便捷函数

    参数:
        data: 包含收益率和市场收益率的数据
        windows: 计算窗口列表

    返回:
        pd.DataFrame: 特质波动率因子值
    """
    factor = SpecificVolatilityFactor(windows=windows)
    return factor.calculate(data)


# 导出接口
__all__ = [
    'SpecificVolatilityCalculator',
    'SpecificVolatilityFactor',
    'calculate_specific_volatility_factor'
]
