"""
因子基类

所有因子类都继承自BaseFactor。
"""

from abc import ABC, abstractmethod
from typing import List, Union
import pandas as pd

try:
    from ..config import FactorConfig
except ImportError:
    from easyxt_backtest.config import FactorConfig


class BaseFactor(ABC):
    """
    因子基类

    所有具体因子都必须继承此类并实现calculate方法。
    """

    def __init__(self, config: FactorConfig, data_manager):
        """
        初始化因子

        Args:
            config: 因子配置
            data_manager: 数据管理器
        """
        self.config = config
        self.data_manager = data_manager
        self.name = config.name
        self.factor_type = config.factor_type
        self.field = config.field

    @abstractmethod
    def calculate(self, stock_pool: List[str], date: str) -> pd.Series:
        """
        计算因子值

        Args:
            stock_pool: 股票列表
            date: 日期 (YYYYMMDD)

        Returns:
            Series: 股票代码到因子值的映射
        """
        pass

    def validate_result(self, factor_values: pd.Series) -> bool:
        """
        验证因子计算结果

        Args:
            factor_values: 因子值Series

        Returns:
            是否有效
        """
        if factor_values is None or factor_values.empty:
            return False

        # 检查是否有NaN
        if factor_values.isna().all():
            return False

        return True
