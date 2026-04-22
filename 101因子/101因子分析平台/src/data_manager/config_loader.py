"""
101因子平台配置加载器
从.env文件读取配置，避免硬编码路径
"""

import os
from pathlib import Path
from typing import Dict, Optional

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def get_env_config() -> Dict[str, str]:
    """
    从环境变量获取配置

    Returns:
        配置字典
    """
    config = {}

    # 尝试多个可能的.env文件位置
    env_paths = [
        PROJECT_ROOT / '.env',
        Path.cwd() / '.env',
        Path.home() / '.env',
    ]

    env_file = None
    for env_path in env_paths:
        if env_path.exists():
            env_file = env_path
            break

    if env_file:
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # 跳过注释和空行
                    if not line or line.startswith('#'):
                        continue
                    # 解析 KEY=VALUE 格式
                    if '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        except Exception as e:
            print(f"[WARN] 加载.env文件失败: {e}")

    return config


def get_stock_data_root() -> str:
    """
    获取数据根目录

    Returns:
        数据根目录路径
    """
    config = get_env_config()

    # 优先使用环境变量
    if 'STOCK_DATA_ROOT' in config:
        return config['STOCK_DATA_ROOT']

    # 默认路径
    return 'D:/StockData'


def get_duckdb_path() -> str:
    """
    获取DuckDB数据库路径

    Returns:
        DuckDB数据库文件路径
    """
    config = get_env_config()

    # 优先使用环境变量
    if 'DUCKDB_PATH' in config:
        return config['DUCKDB_PATH']

    # 默认路径（相对于数据根目录）
    root_dir = get_stock_data_root()
    return f"{root_dir}/stock_data.ddb"


def get_metadata_path() -> str:
    """
    获取元数据路径

    Returns:
        元数据路径（现在是DuckDB的一部分）
    """
    # 现在元数据存储在DuckDB中
    return get_duckdb_path()


def get_raw_data_path() -> str:
    """
    获取原始数据路径

    Returns:
        原始数据目录路径
    """
    root_dir = get_stock_data_root()
    return f"{root_dir}/raw"


# 全局配置实例
_global_config = None


def load_config() -> Dict[str, str]:
    """加载全局配置"""
    global _global_config
    if _global_config is None:
        _global_config = get_env_config()
    return _global_config


if __name__ == "__main__":
    print("配置测试:")
    print(f"数据根目录: {get_stock_data_root()}")
    print(f"DuckDB路径: {get_duckdb_path()}")
    print(f"元数据路径: {get_metadata_path()}")
    print(f"原始数据路径: {get_raw_data_path()}")
