"""
数据管理模块
从101因子分析平台重新导出核心数据管理类
"""

import sys
from pathlib import Path

# 添加101因子平台路径
factor_platform_path = Path(__file__).parents[1] / "101因子" / "101因子分析平台" / "src"
if str(factor_platform_path) not in sys.path:
    sys.path.insert(0, str(factor_platform_path))

# 重新导出核心类
try:
    from data_manager import (
        LocalDataManager,
        MetadataDB,
        ParquetStorage,
        DuckDBStorage,
        DuckDBDataManager,
        HybridDataManager,
        DUCKDB_AVAILABLE
    )
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
