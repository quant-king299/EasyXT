"""
本地数据管理系统
轻量级数据存储方案，支持增量更新
"""

from .local_data_manager import LocalDataManager
from .metadata_db import MetadataDB
from .parquet_storage import ParquetStorage

__all__ = ['LocalDataManager', 'MetadataDB', 'ParquetStorage']


# 便捷函数
def get_local_data_manager():
    """获取本地数据管理器实例（单例模式）"""
    if not hasattr(get_local_data_manager, '_instance'):
        get_local_data_manager._instance = LocalDataManager()
    return get_local_data_manager._instance


def load_stock_data(symbols, start_date, end_date,
                   use_local_first: bool = True,
                   auto_download: bool = True):
    """
    加载股票数据的便捷函数

    Args:
        symbols: 股票代码或代码列表
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        use_local_first: 是否优先使用本地数据
        auto_download: 本地缺失时是否自动下载

    Returns:
        DataFrame: 多级索引 [date, symbol]
    """
    manager = get_local_data_manager()

    # 标准化输入
    if isinstance(symbols, str):
        symbols = [s.strip() for s in symbols.split(',') if s.strip()]

    # 从本地加载
    local_data = manager.load_data(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        check_local=auto_download
    )

    if not local_data:
        return None

    # 合并为单个DataFrame
    df_list = []
    for symbol, df in local_data.items():
        df = df.copy()
        df['symbol'] = symbol
        df_list.append(df)

    if df_list:
        result = pd.concat(df_list)
        result = result.reset_index().set_index(['date', 'symbol']).sort_index()
        return result

    return None


def update_local_data(symbols=None, days_back: int = 5):
    """
    更新本地数据的便捷函数

    Args:
        symbols: 要更新的股票列表，None表示全部
        days_back: 向前回溯天数
    """
    manager = get_local_data_manager()
    manager.update_data(symbols=symbols)


def get_data_statistics():
    """获取本地数据统计信息"""
    manager = get_local_data_manager()
    return manager.get_statistics()


# 导入pandas
import pandas as pd
