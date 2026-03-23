"""
市场过滤器

用于过滤不同市场的股票（深交所、上交所等）。
"""

from typing import List
from .base import BaseFilter


class MarketFilter(BaseFilter):
    """
    市场过滤器

    支持按交易所过滤：
    - 深交所 (SZ)
    - 上交所 (SH)
    - 北交所 (BJ)
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

        # 从配置中获取需要包含或排除的市场
        target_markets = self.config.values

        # 映射市场名称到代码后缀
        market_suffix_map = {
            '深交所': '.SZ',
            'SZ': '.SZ',
            '上交所': '.SH',
            'SH': '.SH',
            '北交所': '.BJ',
            'BJ': '.BJ'
        }

        # 转换为后缀列表
        target_suffixes = []
        for market in target_markets:
            suffix = market_suffix_map.get(market)
            if suffix:
                target_suffixes.append(suffix)

        if not target_suffixes:
            return stock_pool

        # 应用过滤条件
        condition = self.config.condition

        if condition == 'in':
            # 只保留目标市场的股票
            result = [s for s in stock_pool if any(s.endswith(suffix) for suffix in target_suffixes)]
        elif condition == 'not_in':
            # 排除目标市场的股票
            result = [s for s in stock_pool if not any(s.endswith(suffix) for suffix in target_suffixes)]
        else:
            raise ValueError(f"不支持的条件类型: {condition}")

        return result
