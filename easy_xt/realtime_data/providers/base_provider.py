"""
数据提供者基类

定义所有数据源提供者的统一接口规范。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseDataProvider(ABC):
    """数据提供者基类
    
    所有数据源提供者都应该继承此类并实现抽象方法。
    """
    
    def __init__(self, name: str):
        """初始化数据提供者
        
        Args:
            name: 数据源名称
        """
        self.name = name
        self.connected = False
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    def connect(self) -> bool:
        """连接到数据源
        
        Returns:
            bool: 连接是否成功
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """断开数据源连接"""
        pass
    
    @abstractmethod
    def get_realtime_quotes(self, codes: List[str]) -> List[Dict[str, Any]]:
        """获取实时行情数据
        
        Args:
            codes: 股票代码列表
            
        Returns:
            List[Dict]: 行情数据列表，每个字典包含：
                - code: 股票代码
                - name: 股票名称
                - price: 当前价格
                - change: 涨跌额
                - change_pct: 涨跌幅
                - volume: 成交量
                - turnover: 成交额
                - timestamp: 数据时间戳
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查数据源是否可用
        
        Returns:
            bool: 数据源是否可用
        """
        pass
    
    def get_provider_info(self) -> Dict[str, Any]:
        """获取数据提供者信息
        
        Returns:
            Dict: 提供者信息
        """
        return {
            'name': self.name,
            'connected': self.connected,
            'available': self.is_available()
        }