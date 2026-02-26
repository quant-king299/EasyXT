#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tushare数据管理模块
提供从Tushare下载数据并保存到DuckDB的功能
"""

from .tushare_config import TushareConfig, get_config
from .tushare_downloader import TushareDownloader

__all__ = [
    'TushareConfig',
    'get_config',
    'TushareDownloader'
]

__version__ = '1.0.0'
