# -*- coding: utf-8 -*-
"""
用户策略模块

将 .py 文件放入此目录即可自动注册到回测平台。
详见 strategy_loader.py 文档。
"""

from .strategy_loader import discover_strategies, get_merged_registry, list_strategies_by_category
