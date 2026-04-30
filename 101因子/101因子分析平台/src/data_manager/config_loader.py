# -*- coding: utf-8 -*-
"""
数据路径配置加载器

优先级：环境变量 > .env文件 > 默认路径
"""

import os
from pathlib import Path

# 默认路径
DEFAULT_DATA_ROOT = 'D:/StockData'
DEFAULT_DUCKDB_NAME = 'stock_data.ddb'


def get_stock_data_root() -> str:
    """
    获取数据根目录

    优先级：环境变量 STOCK_DATA_ROOT > 默认 D:/StockData
    """
    root = os.environ.get('STOCK_DATA_ROOT', '').strip()
    if root:
        return root
    return DEFAULT_DATA_ROOT


def get_duckdb_path() -> str:
    """
    获取DuckDB数据库完整路径

    优先级：环境变量 DUCKDB_PATH > {STOCK_DATA_ROOT}/stock_data.ddb
    """
    path = os.environ.get('DUCKDB_PATH', '').strip()
    if path:
        return path
    return os.path.join(get_stock_data_root(), DEFAULT_DUCKDB_NAME)
