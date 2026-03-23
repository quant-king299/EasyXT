"""
股票状态过滤器

用于过滤ST、退市等特殊状态的股票。
"""

from typing import List
from .base import BaseFilter


class StockStatusFilter(BaseFilter):
    """
    股票状态过滤器

    支持过滤：
    - ST股票
    - *ST股票
    - S*ST股票
    - 退市股票
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

        # 获取股票状态信息
        stock_info = self._get_stock_info(stock_pool, date)

        if stock_info is None or stock_info.empty:
            # 如果无法获取股票信息，返回原股票池
            return stock_pool

        # 应用过滤条件
        exclude_values = self.config.values

        # 找出需要排除的股票
        exclude_stocks = []
        for stock_code in stock_pool:
            if stock_code in stock_info.index:
                status = stock_info.loc[stock_code, 'stock_status']
                name = stock_info.loc[stock_code, 'stock_name']

                # 检查是否匹配排除条件
                should_exclude = False

                for exclude_val in exclude_values:
                    # 检查状态字段
                    if exclude_val in status:
                        should_exclude = True
                        break

                    # 检查股票名称
                    if exclude_val in name:
                        should_exclude = True
                        break

                if should_exclude:
                    exclude_stocks.append(stock_code)

        # 返回未排除的股票
        result = [s for s in stock_pool if s not in exclude_stocks]

        return result

    def _get_stock_info(self, stock_pool: List[str], date: str):
        """
        获取股票信息

        Args:
            stock_pool: 股票列表
            date: 日期

        Returns:
            DataFrame with columns: stock_status, stock_name
        """
        try:
            # 尝试从data_manager获取股票信息
            if hasattr(self.data_manager, 'get_stock_info'):
                return self.data_manager.get_stock_info(stock_pool, date)
            elif hasattr(self.data_manager, 'get_stock_basic_info'):
                return self.data_manager.get_stock_basic_info(stock_pool, date)
            else:
                # 如果data_manager没有相关方法，返回空
                return None
        except Exception as e:
            print(f"⚠️ 获取股票信息失败: {e}")
            return None
