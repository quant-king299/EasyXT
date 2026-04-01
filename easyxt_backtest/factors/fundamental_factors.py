"""
基本面因子

基于公司财务数据的因子，如市值、PE、ROE等。
"""

from typing import List
import pandas as pd
import numpy as np
from .base import BaseFactor


class FundamentalFactor(BaseFactor):
    """
    基本面因子

    支持的因子字段：
    - market_cap: 市值
    - pe_ratio: 市盈率
    - pb_ratio: 市净率
    - ps_ratio: 市销率
    - roe: 净资产收益率
    - roa: 总资产收益率
    - eps: 每股收益
    - bps: 每股净资产
    - total_assets: 总资产
    - total_liabilities: 总负债
    - turnover: 成交额
    等
    """

    def calculate(self, stock_pool: List[str], date: str) -> pd.Series:
        """
        计算基本面因子值

        Args:
            stock_pool: 股票列表
            date: 日期 (YYYYMMDD)

        Returns:
            Series: 股票代码到因子值的映射
        """
        try:
            # 从data_manager获取基本面数据
            fundamental_data = self._get_fundamental_data(stock_pool, date, self.field)

            if fundamental_data is None or fundamental_data.empty:
                print(f"[WARNING] Cannot get fundamental data [{self.field}] at {date}")
                # 返回空的Series，索引为股票池
                return pd.Series(index=stock_pool, dtype=float)

            # 确保返回的Series包含所有股票
            result = pd.Series(index=stock_pool, dtype=float)

            # 填充有数据的股票
            for stock in stock_pool:
                if stock in fundamental_data.index:
                    result[stock] = fundamental_data.loc[stock]
                else:
                    result[stock] = np.nan

            return result

        except Exception as e:
            print(f"[ERROR] Failed to calculate fundamental factor [{self.field}]: {e}")
            return pd.Series(index=stock_pool, dtype=float)

    def _get_fundamental_data(self, stock_pool: List[str], date: str, field: str):
        """
        获取基本面数据

        Args:
            stock_pool: 股票列表
            date: 日期
            field: 字段名

        Returns:
            Series: 股票代码到字段值的映射
        """
        try:
            # 尝试不同的方法获取基本面数据
            if hasattr(self.data_manager, 'get_fundamentals'):
                df = self.data_manager.get_fundamentals(
                    codes=stock_pool,
                    date=date,
                    fields=[field]
                )
                return df[field]
            elif hasattr(self.data_manager, 'get_factor'):
                return self.data_manager.get_factor(stock_pool, date, field)
            else:
                print(f"[WARNING] data_manager does not support getting fundamental data")
                return None
        except Exception as e:
            print(f"[WARNING] Failed to get fundamental data [{field}]: {e}")
            return None


class MarketCapFactor(FundamentalFactor):
    """
    市值因子

    特殊处理：通常使用对数市值
    """

    def calculate(self, stock_pool: List[str], date: str) -> pd.Series:
        """
        计算市值因子（对数市值）

        Args:
            stock_pool: 股票列表
            date: 日期

        Returns:
            Series: 对数市值
        """
        # 获取原始市值
        raw_values = super().calculate(stock_pool, date)

        # 转换为对数市值
        log_values = np.log(raw_values.replace(0, np.nan))  # 避免log(0)
        log_values = log_values.replace([np.inf, -np.inf], np.nan)

        return log_values
