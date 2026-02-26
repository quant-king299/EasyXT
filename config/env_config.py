#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境变量配置管理模块
从 .env 文件加载配置信息
"""

import os
from pathlib import Path
from typing import Optional


class EnvConfig:
    """环境变量配置管理器"""

    def __init__(self, env_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            env_path: .env 文件路径，默认为项目根目录下的 .env
        """
        if env_path is None:
            # 获取项目根目录
            project_root = Path(__file__).parent.parent
            env_path = project_root / '.env'

        self.env_path = Path(env_path)
        self.config = {}
        self._load_env()

    def _load_env(self):
        """从 .env 文件加载配置"""
        if not self.env_path.exists():
            print(f"[WARN] .env file not found at: {self.env_path}")
            print("[INFO] Create .env file from .env.example:")
            print(f"       cp {self.env_path.parent / '.env.example'} {self.env_path}")
            return

        try:
            with open(self.env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()

                    # 跳过空行和注释
                    if not line or line.startswith('#'):
                        continue

                    # 解析 KEY=VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        self.config[key.strip()] = value.strip()

            print(f"[OK] Loaded config from: {self.env_path}")

        except Exception as e:
            print(f"[ERROR] Failed to load .env file: {e}")

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        获取配置值

        Args:
            key: 配置键名
            default: 默认值

        Returns:
            配置值或默认值
        """
        # 优先从 .env 文件读取
        value = self.config.get(key)

        # 如果 .env 中没有，尝试从环境变量读取
        if value is None:
            value = os.environ.get(key)

        # 如果还是没有，返回默认值
        if value is None:
            value = default

        return value

    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数配置"""
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """获取浮点数配置"""
        value = self.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔值配置"""
        value = self.get(key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')

    @property
    def tushare_token(self) -> Optional[str]:
        """获取 Tushare Token"""
        return self.get('TUSHARE_TOKEN')

    @property
    def duckdb_path(self) -> str:
        """获取 DuckDB 数据库路径"""
        return self.get('DUCKDB_PATH', 'D:/StockData/stock_data.ddb')


# 全局配置实例
_env_config_instance = None


def get_env_config() -> EnvConfig:
    """获取全局环境配置实例"""
    global _env_config_instance
    if _env_config_instance is None:
        _env_config_instance = EnvConfig()
    return _env_config_instance


if __name__ == "__main__":
    # 测试配置加载
    print("=" * 60)
    print("环境变量配置测试")
    print("=" * 60)

    config = get_env_config()

    print(f"\nTushare Token: {config.tushare_token[:20] if config.tushare_token else 'None'}...")
    print(f"DuckDB Path: {config.duckdb_path}")
