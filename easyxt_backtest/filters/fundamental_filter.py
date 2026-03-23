"""
基本面过滤器

用于根据基本面指标过滤股票。
"""

import pandas as pd
from typing import List
from .base import BaseFilter


class FundamentalFilter(BaseFilter):
    """
    基本面过滤器

    支持根据基本面指标过滤，如：
    - 市值 (market_cap)
    - PE (pe_ratio)
    - PB (pb_ratio)
    - ROE (roe)
    - 成交额 (turnover)
    等
    """

    def filter(self, stock_pool: List[str], date: str) -> List[str]:
        """
        过滤股票池

        Args:
            stock_pool: 待过滤的股票列表
            date: 日期 (YYYYMMDD)

        Returns:
            过滤后的股票列表
        """
        if not self._validate_stock_list(stock_pool):
            return []

        # 获取基本面数据
        field = self.config.field
        fundamental_data = self._get_fundamental_data(stock_pool, date, field)

        if fundamental_data is None or fundamental_data.empty:
            # 如果无法获取数据，返回原股票池
            return stock_pool

        # 应用过滤条件
        condition = self.config.condition
        result_stocks = []

        for stock_code in stock_pool:
            if stock_code not in fundamental_data.index:
                # 如果没有数据，根据条件决定是否包含
                if condition in ['in', 'not_in']:
                    # 对于in/not_in条件，没有数据的股票默认包含
                    result_stocks.append(stock_code)
                continue

            value = fundamental_data.loc[stock_code]

            # 检查是否通过过滤条件
            passed = self._check_condition(value, condition)

            if passed:
                result_stocks.append(stock_code)

        return result_stocks

    def _check_condition(self, value: float, condition: str) -> bool:
        """
        检查数值是否满足条件

        Args:
            value: 检查的值
            condition: 条件类型

        Returns:
            是否通过
        """
        try:
            if condition == 'greater_than':
                return value > self.config.min_value
            elif condition == 'less_than':
                return value < self.config.max_value
            elif condition == 'between':
                min_val = self.config.min_value
                max_val = self.config.max_value
                return min_val <= value <= max_val
            else:
                raise ValueError(f"不支持的条件类型: {condition}")
        except Exception as e:
            print(f"⚠️ 检查条件时出错: {e}, value={value}")
            return False

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
            # 尝试从data_manager获取基本面数据
            if hasattr(self.data_manager, 'get_fundamentals'):
                df = self.data_manager.get_fundamentals(
                    codes=stock_pool,
                    date=date,
                    fields=[field]
                )
                return df[field]
            elif hasattr(self.data_manager, 'get_factor'):
                # 尝试获取因子数据
                return self.data_manager.get_factor(stock_pool, date, field)
            else:
                return None
        except Exception as e:
            print(f"⚠️ 获取基本面数据失败 [{field}]: {e}")
            return None
