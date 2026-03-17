# -*- coding: utf-8 -*-
"""
核心模块

提供项目核心功能：
- 数据管理（data_manager）
- 路径管理（path_manager）
- 配置管理（config）
- Alpha分析（alpha_analysis）
"""

__version__ = '1.0.0'
__author__ = 'Claude Code'

# 数据管理
from .data_manager import (
    BaseDataSource,
    DataManagerConfig,
    get_global_config,
    set_global_config
)

# 路径管理
from .path_manager import (
    init_paths,
    get_project_root,
    get_path,
    get_easyxt_path,
    get_core_path,
    get_strategies_path,
    get_config_path,
    get_xueqiu_config_path,
    get_reports_path,
    get_logs_path,
)

__all__ = [
    # 数据管理
    'BaseDataSource',
    'DataManagerConfig',
    'get_global_config',
    'set_global_config',
    # 路径管理
    'init_paths',
    'get_project_root',
    'get_path',
    'get_easyxt_path',
    'get_core_path',
    'get_strategies_path',
    'get_config_path',
    'get_xueqiu_config_path',
    'get_reports_path',
    'get_logs_path',
]