"""
EasyXT API包装器
提供统一的接口访问EasyXT功能
"""
import pandas as pd
from typing import List, Dict, Optional
import sys
import os

# 添加项目路径
project_path = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_path)

from .data_loader import EasyXTDataLoader


class EasyXTAPIWrapper:
    """EasyXT API包装器"""
    
    def __init__(self):
        self.data_loader = EasyXTDataLoader()
    
    def get_market_data(self, symbols: List[str], start_date: str, end_date: str,
                       fields: Optional[List[str]] = None) -> pd.DataFrame:
        """
        获取市场数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期 (格式: 'YYYY-MM-DD')
            end_date: 结束日期 (格式: 'YYYY-MM-DD')
            fields: 需要的字段列表
            
        Returns:
            pd.DataFrame: 市场数据，索引为[date, symbol]
        """
        return self.data_loader.load_data(symbols, start_date, end_date, fields)
    
    def get_universe(self, market: str = "a_stock") -> List[str]:
        """
        获取股票池
        
        Args:
            market: 市场类型
            
        Returns:
            List[str]: 股票代码列表
        """
        # 这里根据实际EasyXT API实现
        # 暂时返回模拟数据
        if market == "hs300":
            # 沪深300成分股示例
            return [
                '000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '000858.SZ',
                '002594.SZ', '601318.SH', '601398.SH', '601939.SH', '601328.SH'
            ]
        else:
            # 默认返回一些A股代码
            return [
                '000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '000858.SZ'
            ]
    
    def get_instrument_info(self, symbols: List[str]) -> pd.DataFrame:
        """
        获取证券信息
        
        Args:
            symbols: 股票代码列表
            
        Returns:
            pd.DataFrame: 证券信息
        """
        # 这里根据实际EasyXT API实现
        # 暂时返回模拟数据
        data = []
        for symbol in symbols:
            info = {
                'symbol': symbol,
                'name': f'股票{symbol}',
                'industry': '未知行业',
                'market': 'A股',
                'currency': 'CNY',
                'status': '交易'
            }
            data.append(info)
        
        return pd.DataFrame(data)


# 单例模式的EasyXT实例
easyxt_instance = EasyXTAPIWrapper()


def get_easyxt_instance() -> EasyXTAPIWrapper:
    """
    获取EasyXT实例
    
    Returns:
        EasyXTAPIWrapper: EasyXT API包装器实例
    """
    return easyxt_instance


# 测试代码
if __name__ == '__main__':
    api = get_easyxt_instance()
    
    # 测试获取股票池
    universe = api.get_universe("hs300")
    print(f'沪深300股票池: {universe}')
    
    # 测试获取市场数据
    symbols = universe[:3]  # 取前3只股票
    data = api.get_market_data(
        symbols=symbols,
        start_date='2023-01-01',
        end_date='2023-01-10'
    )
    
    print(f'获取数据形状: {data.shape}')
    print(f'数据预览:')
    print(data.head(10))
    
    # 测试获取证券信息
    info = api.get_instrument_info(symbols)
    print(f'证券信息:')
    print(info)