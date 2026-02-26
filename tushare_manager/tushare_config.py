#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tushare配置管理模块
管理Tushare token和API配置
优先从环境变量(.env)读取，其次从配置文件读取
"""

import os
import json
from pathlib import Path
from typing import Optional

class TushareConfig:
    """Tushare配置管理器"""

    DEFAULT_DB_PATH = 'D:/StockData/stock_data.ddb'

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径，默认为项目根目录下的tushare_config.json
        """
        if config_path is None:
            project_root = Path(__file__).parent.parent
            config_path = project_root / 'tushare_config.json'

        self.config_path = Path(config_path)
        self.env_config = None
        self.config = self._load_config()

    def _load_env_config(self):
        """加载环境变量配置"""
        try:
            from config import get_env_config
            self.env_config = get_env_config()
        except ImportError:
            self.env_config = None

    def _load_config(self) -> dict:
        """加载配置（优先从环境变量）"""
        # 尝试加载环境变量配置
        self._load_env_config()

        # 从环境变量获取 Token
        env_token = None
        if self.env_config:
            env_token = self.env_config.tushare_token
            if env_token:
                print(f"[INFO] Loaded Tushare token from .env file")

        # 从配置文件加载
        file_config = {}
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                print(f"[INFO] Loaded config from: {self.config_path}")
            except Exception as e:
                print(f"[WARN] Failed to load config file: {e}")

        # 合并配置（环境变量优先级更高）
        default_config = {
            'token': env_token or file_config.get('token', ''),
            'db_path': self.env_config.duckdb_path if self.env_config else self.DEFAULT_DB_PATH,
            'sync_settings': {
                'financial_years': 5,
                'dividend_years': 10
            }
        }

        # 如果环境变量没有Token，提示用户
        if not default_config['token']:
            print("[WARN] Tushare token not found in .env file")
            print("[INFO] Please set TUSHARE_TOKEN in .env file:")
            print("       1. Copy .env.example to .env")
            print("       2. Add your token: TUSHARE_TOKEN=your_token_here")

        return default_config

    @property
    def token(self) -> str:
        """获取Tushare token（优先从环境变量）"""
        return self.config.get('token', '')

    @property
    def db_path(self) -> str:
        """获取DuckDB数据库路径"""
        return self.config.get('db_path', self.DEFAULT_DB_PATH)

    @property
    def financial_years(self) -> int:
        """获取财务数据年数"""
        return self.config.get('sync_settings', {}).get('financial_years', 5)

    @property
    def dividend_years(self) -> int:
        """获取分红数据年数"""
        return self.config.get('sync_settings', {}).get('dividend_years', 10)

    def has_token(self) -> bool:
        """检查是否已配置Token"""
        return bool(self.config.get('token'))


# 全局配置实例
_config_instance = None

def get_config() -> TushareConfig:
    """获取全局配置实例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = TushareConfig()
    return _config_instance


if __name__ == "__main__":
    # 测试配置管理
    config = get_config()
    print(f"Token: {config.token[:20]}...")
    print(f"DB Path: {config.db_path}")
    print(f"Batch Size: {config.batch_size}")
    print(f"Sleep Time: {config.sleep_time}s")
