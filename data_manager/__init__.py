"""
数据管理模块
提供便捷的数据管理功能，兼容101因子分析平台
"""

import sys
from pathlib import Path

# 添加101因子平台路径
factor_platform_path = Path(__file__).parents[1] / "101因子" / "101因子分析平台" / "src"
if str(factor_platform_path) not in sys.path:
    sys.path.insert(0, str(factor_platform_path))

# 直接从目标模块导入（避免循环导入）
try:
    import importlib

    # 动态导入 101因子平台的数据管理模块
    dm_module = importlib.import_module('data_manager')

    # 提取需要的类和变量
    LocalDataManager = getattr(dm_module, 'LocalDataManager', None)
    MetadataDB = getattr(dm_module, 'MetadataDB', None)
    ParquetStorage = getattr(dm_module, 'ParquetStorage', None)
    DUCKDB_AVAILABLE = getattr(dm_module, 'DUCKDB_AVAILABLE', False)

    # 尝试导入可选的DuckDB相关类
    DuckDBStorage = getattr(dm_module, 'DuckDBStorage', None)
    DuckDBDataManager = getattr(dm_module, 'DuckDBDataManager', None)
    HybridDataManager = getattr(dm_module, 'HybridDataManager', None)

except ImportError as e:
    # 如果101因子平台不可用，提供友好的错误提示
    raise ImportError(
        f"无法从101因子分析平台导入数据管理类: {e}\n"
        f"请确保 101因子/101因子分析平台/src 目录存在且包含必要的数据管理模块"
    )

__all__ = [
    'LocalDataManager',
    'MetadataDB',
    'ParquetStorage',
    'DuckDBStorage',
    'DuckDBDataManager',
    'HybridDataManager',
    'DUCKDB_AVAILABLE'
]
