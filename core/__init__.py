# -*- coding: utf-8 -*-
"""
核心数据管理模块

提供统一的数据管理接口，支持多数据源：
- DuckDB本地数据库
- Tushare在线API
- QMT历史数据
"""

__version__ = '1.0.0'
__author__ = 'Claude Code'

from .data_manager import (
    BaseDataSource,
    DataManagerConfig,
    get_global_config,
    set_global_config
)

__all__ = [
    'BaseDataSource',
    'DataManagerConfig',
    'get_global_config',
    'set_global_config',
]