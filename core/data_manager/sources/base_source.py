# -*- coding: utf-8 -*-
"""
数据源抽象基类

定义所有数据源的统一接口
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Union
import pandas as pd
from datetime import datetime
import re


class BaseDataSource(ABC):
    """
    数据源抽象基类

    所有数据源必须实现此接口，确保统一的API
    """

    def __init__(self, config: Dict):
        """
        初始化数据源

        Args:
            config: 数据源配置字典
        """
        self.config = config
        self._connection = None
        self._cache = {}
        self._last_used = None
        self.is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """
        建立数据源连接

        Returns:
            bool: 连接是否成功
        """
        pass

    @abstractmethod
    def get_price(self,
                  symbol: str,
                  start_date: str,
                  end_date: str,
                  period: str = '1d',
                  adjust: str = 'none') -> Optional[pd.DataFrame]:
        """
        获取价格数据

        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 数据周期 ('1d', '1w', '1m')
            adjust: 复权类型 ('none', 'qfq', 'hfq')

        Returns:
            DataFrame: 价格数据，包含列：date, open, high, low, close, volume, amount
        """
        pass

    @abstractmethod
    def get_fundamentals(self,
                         symbols: List[str],
                         date: str,
                         fields: Optional[List[str]] = None) -> Optional[pd.DataFrame]:
        """
        获取基本面数据

        Args:
            symbols: 股票代码列表
            date: 查询日期 (YYYYMMDD)
            fields: 需要的字段列表（None表示所有字段）

        Returns:
            DataFrame: 基本面数据
        """
        pass

    @abstractmethod
    def get_trading_dates(self,
                          start_date: str,
                          end_date: str) -> Optional[List[str]]:
        """
        获取交易日历

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            List[str]: 交易日列表 (YYYYMMDD格式)
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        检查数据源是否可用

        Returns:
            bool: 数据源是否可用
        """
        pass

    def close(self):
        """关闭数据源连接"""
        if self._connection:
            try:
                self._connection.close()
            except Exception as e:
                print(f"[{self.__class__.__name__}] 关闭连接时出错: {e}")
            finally:
                self._connection = None
                self.is_connected = False

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()

    def get_cache_key(self, *args) -> str:
        """
        生成缓存键

        Args:
            *args: 缓存参数

        Returns:
            str: 缓存键
        """
        return ':'.join(str(arg) for arg in args)

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()

    def get_cache_info(self) -> Dict:
        """
        获取缓存信息

        Returns:
            Dict: 缓存统计信息
        """
        return {
            'cache_size': len(self._cache),
            'last_used': self._last_used
        }

    def validate_date_format(self, date_str: str) -> bool:
        """
        验证日期格式

        Args:
            date_str: 日期字符串

        Returns:
            bool: 格式是否正确
        """
        try:
            datetime.strptime(date_str, '%Y%m%d')
            return True
        except ValueError:
            return False

    def validate_symbol(self, symbol: str) -> bool:
        """
        验证股票代码格式

        Args:
            symbol: 股票代码

        Returns:
            bool: 格式是否正确
        """
        # 基本格式验证：6位数字 + 可选后缀
        pattern = r'^\d{6}(\.(SZ|SH))?$'
        return bool(re.match(pattern, symbol))

    def normalize_symbol(self, symbol: str) -> str:
        """
        标准化股票代码格式

        Args:
            symbol: 股票代码

        Returns:
            str: 标准化后的股票代码
        """
        symbol = symbol.strip().upper()

        # 如果没有后缀，添加默认后缀
        if '.' not in symbol:
            if symbol.startswith('6'):
                symbol += '.SH'  # 上海股票
            elif symbol.startswith(('0', '3')):
                symbol += '.SZ'  # 深圳股票

        return symbol

    def __repr__(self) -> str:
        """字符串表示"""
        return f"{self.__class__.__name__}(available={self.is_available()})"