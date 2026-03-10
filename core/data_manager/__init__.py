# -*- coding: utf-8 -*-
"""
数据管理器模块

统一的数据管理接口，支持多数据源自动切换
"""

from .sources import BaseDataSource, DuckDBSource, TushareSource, QMTSource
from .config import DataManagerConfig, get_global_config, set_global_config
from .hybrid_manager import HybridDataManager
from .utils import (
    convert_date_format,
    get_trading_date_range,
    validate_date,
    normalize_symbol,
    normalize_symbols,
    validate_symbol,
    is_sh_stock,
    is_sz_stock,
)

__all__ = [
    # 数据源
    'BaseDataSource',
    'DuckDBSource',
    'TushareSource',
    'QMTSource',

    # 混合管理器
    'HybridDataManager',

    # 配置管理
    'DataManagerConfig',
    'get_global_config',
    'set_global_config',

    # 工具函数
    'convert_date_format',
    'get_trading_date_range',
    'validate_date',
    'normalize_symbol',
    'normalize_symbols',
    'validate_symbol',
    'is_sh_stock',
    'is_sz_stock',
]