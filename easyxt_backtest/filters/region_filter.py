"""
地域过滤器

用于过滤特定地域的股票。
"""

from typing import List
from .base import BaseFilter


class RegionFilter(BaseFilter):
    """
    地域过滤器

    支持按省份或地区过滤股票。
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

        # 如果配置的values为空，表示不限制地域
        if not self.config.values or len(self.config.values) == 0:
            return stock_pool

        # 获取地域数据
        region_data = self._get_region_data(stock_pool, date)

        if region_data is None or region_data.empty:
            # 如果无法获取地域数据，返回原股票池
            return stock_pool

        # 获取需要过滤的地域列表
        target_regions = self.config.values
        condition = self.config.condition

        result_stocks = []

        for stock_code in stock_pool:
            if stock_code not in region_data.index:
                # 如果没有地域数据，根据条件决定
                if condition == 'in':
                    continue
                else:
                    result_stocks.append(stock_code)
                continue

            region = region_data.loc[stock_code]

            # 检查是否匹配目标地域
            is_target = any(target_reg in region for target_reg in target_regions)

            if condition == 'in' and is_target:
                result_stocks.append(stock_code)
            elif condition == 'not_in' and not is_target:
                result_stocks.append(stock_code)

        return result_stocks

    def _get_region_data(self, stock_pool: List[str], date: str):
        """
        获取地域数据

        Args:
            stock_pool: 股票列表
            date: 日期

        Returns:
            Series: 股票代码到地域的映射
        """
        try:
            # 尝试从data_manager获取地域数据
            if hasattr(self.data_manager, 'get_region'):
                return self.data_manager.get_region(stock_pool, date)
            elif hasattr(self.data_manager, 'get_stock_region'):
                return self.data_manager.get_stock_region(stock_pool, date)
            else:
                # 如果data_manager不支持地域数据，返回None
                print("⚠️ 当前data_manager不支持地域数据过滤")
                return None
        except Exception as e:
            print(f"⚠️ 获取地域数据失败: {e}")
            return None
