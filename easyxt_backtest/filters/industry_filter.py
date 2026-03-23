"""
行业过滤器

用于过滤特定行业的股票。
"""

from typing import List
from .base import BaseFilter


class IndustryFilter(BaseFilter):
    """
    行业过滤器

    支持按申万行业分类过滤股票。
    """

    def filter(self, stock_pool: List[str], date: str) -> List[str]:
        """
        过滤股票池

        Args:
            stock_pool: 待过滤的股票列表
            date: 日期

        Returns:
            过滤后的股票列表
        """
        if not self._validate_stock_list(stock_pool):
            return []

        # 获取行业分类数据
        industry_data = self._get_industry_data(stock_pool, date)

        if industry_data is None or industry_data.empty:
            # 如果无法获取行业数据，返回原股票池
            return stock_pool

        # 获取需要过滤的行业列表
        target_industries = self.config.values
        condition = self.config.condition

        result_stocks = []

        for stock_code in stock_pool:
            if stock_code not in industry_data.index:
                # 如果没有行业数据，根据条件决定
                if condition == 'in':
                    # 对于'in'条件，没有数据的股票不包含
                    continue
                else:
                    # 对于'not_in'条件，没有数据的股票包含
                    result_stocks.append(stock_code)
                continue

            industry = industry_data.loc[stock_code]

            # 检查是否匹配目标行业
            is_target = any(target_ind in industry for target_ind in target_industries)

            if condition == 'in' and is_target:
                result_stocks.append(stock_code)
            elif condition == 'not_in' and not is_target:
                result_stocks.append(stock_code)

        return result_stocks

    def _get_industry_data(self, stock_pool: List[str], date: str):
        """
        获取行业分类数据

        Args:
            stock_pool: 股票列表
            date: 日期

        Returns:
            Series: 股票代码到行业的映射
        """
        try:
            # 尝试从data_manager获取行业数据
            if hasattr(self.data_manager, 'get_industry'):
                return self.data_manager.get_industry(stock_pool, date)
            elif hasattr(self.data_manager, 'get_stock_industry'):
                return self.data_manager.get_stock_industry(stock_pool, date)
            else:
                return None
        except Exception as e:
            print(f"⚠️ 获取行业数据失败: {e}")
            return None
