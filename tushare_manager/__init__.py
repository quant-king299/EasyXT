#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tushare数据管理模块
提供从Tushare下载数据并保存到DuckDB的功能
"""

from .tushare_config import TushareConfig, get_config
from .tushare_downloader import TushareDownloader
from .download_basic_data import (
    download_adj_factor,
    download_stk_limit,
    download_suspend,
    download_sw_industry,
    download_all_basic,
)

__all__ = [
    'TushareConfig',
    'get_config',
    'TushareDownloader',
    'download_adj_factor',
    'download_stk_limit',
    'download_suspend',
    'download_sw_industry',
    'download_all_basic',
]

__version__ = '1.0.0'
