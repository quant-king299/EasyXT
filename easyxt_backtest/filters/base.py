"""
过滤器基类

所有过滤器都继承自BaseFilter，实现filter方法。
"""

from abc import ABC, abstractmethod
from typing import List

# 导入配置
try:
    from easyxt_backtest.config import ExcludeFilterConfig
except ImportError:
    from ..config import ExcludeFilterConfig


class BaseFilter(ABC):
    """
    过滤器基类

    所有具体过滤器都必须继承此类并实现filter方法。
    """

    def __init__(self, config: ExcludeFilterConfig, data_manager):
        """
        初始化过滤器

        Args:
            config: 过滤器配置
            data_manager: 数据管理器
        """
        self.config = config
        self.data_manager = data_manager
        self.name = config.name

    @abstractmethod
    def filter(self, stock_pool: List[str], date: str) -> List[str]:
        """
        过滤股票池

        Args:
            stock_pool: 待过滤的股票列表
            date: 日期

        Returns:
            过滤后的股票列表
        """
        pass

    def _validate_stock_list(self, stocks: List[str]) -> bool:
        """
        验证股票列表格式

        Args:
            stocks: 股票列表

        Returns:
            是否有效
        """
        if not stocks:
            return False
        return all(isinstance(s, str) and len(s) > 0 for s in stocks)
