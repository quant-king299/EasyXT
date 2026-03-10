# -*- coding: utf-8 -*-
"""
配置管理模块

统一管理数据源配置
"""
import os
from typing import Dict, Optional, List
from pathlib import Path
import json


class DataManagerConfig:
    """
    数据管理器配置类

    支持从环境变量、.env文件、配置文件加载配置
    """

    # 默认配置
    DEFAULTS = {
        'duckdb_path': 'D:/StockData/stock_data.ddb',
        'tushare_token': None,
        'qmt_path': None,
        'preferred_sources': ['duckdb', 'qmt', 'tushare'],
        'cache_enabled': True,
        'cache_size': 1000,
        'log_level': 'INFO',
        'timeout': 30,
        'max_retries': 3,
    }

    def __init__(self,
                 config_file: Optional[str] = None,
                 **kwargs):
        """
        初始化配置

        Args:
            config_file: 配置文件路径
            **kwargs: 额外的配置参数
        """
        self.config = self.DEFAULTS.copy()

        # 按优先级加载配置：kwargs > config_file > .env > DEFAULTS
        self._load_from_env()
        if config_file:
            self._load_from_file(config_file)
        self.config.update(kwargs)

    def _load_from_env(self):
        """从环境变量和.env文件加载配置"""
        # 1. 先尝试加载 .env 文件
        self._load_dotenv()

        # 2. 从环境变量加载配置
        # Tushare Token
        if 'TUSHARE_TOKEN' in os.environ:
            self.config['tushare_token'] = os.environ['TUSHARE_TOKEN']

        # DuckDB路径
        if 'DUCKDB_PATH' in os.environ:
            self.config['duckdb_path'] = os.environ['DUCKDB_PATH']

        # QMT路径
        if 'QMT_PATH' in os.environ:
            self.config['qmt_path'] = os.environ['QMT_PATH']

        # 日志级别
        if 'LOG_LEVEL' in os.environ:
            self.config['log_level'] = os.environ['LOG_LEVEL']

    def _load_dotenv(self):
        """手动加载 .env 文件到环境变量"""
        # 查找 .env 文件
        possible_paths = [
            '.env',
            '../.env',
            '../../.env',
            'easyxt_backtest/.env',
            '101因子/101因子分析平台/.env',
        ]

        env_file = None
        for path in possible_paths:
            if os.path.exists(path):
                env_file = path
                break

        if not env_file:
            return  # 没有 .env 文件

        # 读取 .env 文件并设置环境变量
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # 跳过空行和注释
                    if not line or line.startswith('#'):
                        continue

                    # 解析 KEY=VALUE 格式
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()

                        # 移除引号（如果有）
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]

                        # 设置到环境变量（如果还没设置）
                        if key not in os.environ:
                            os.environ[key] = value
        except Exception as e:
            # 静默失败，避免影响启动
            pass

    def _load_from_file(self, config_file: str):
        """
        从配置文件加载配置

        Args:
            config_file: 配置文件路径（支持.json格式）
        """
        config_path = Path(config_file)

        if not config_path.exists():
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix == '.json':
                    file_config = json.load(f)
                    self.config.update(file_config)
                # 可以扩展支持其他格式（.yaml, .ini等）
        except Exception as e:
            print(f"[Config] 加载配置文件失败: {e}")

    def get(self, key: str, default=None):
        """
        获取配置值

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        return self.config.get(key, default)

    def set(self, key: str, value):
        """
        设置配置值

        Args:
            key: 配置键
            value: 配置值
        """
        self.config[key] = value

    def get_source_config(self, source_name: str) -> Dict:
        """
        获取特定数据源的配置

        Args:
            source_name: 数据源名称 ('duckdb', 'tushare', 'qmt')

        Returns:
            Dict: 数据源配置
        """
        source_configs = {
            'duckdb': {
                'path': self.get('duckdb_path'),
                'timeout': self.get('timeout'),
                'max_retries': self.get('max_retries'),
            },
            'tushare': {
                'token': self.get('tushare_token'),
                'timeout': self.get('timeout'),
                'max_retries': self.get('max_retries'),
            },
            'qmt': {
                'path': self.get('qmt_path'),
                'timeout': self.get('timeout'),
            }
        }

        return source_configs.get(source_name, {})

    def get_preferred_sources(self) -> List[str]:
        """
        获取优先数据源列表

        Returns:
            List[str]: 数据源名称列表
        """
        return self.get('preferred_sources', ['duckdb', 'qmt', 'tushare'])

    def is_cache_enabled(self) -> bool:
        """
        是否启用缓存

        Returns:
            bool: 是否启用缓存
        """
        return self.get('cache_enabled', True)

    def get_cache_size(self) -> int:
        """
        获取缓存大小

        Returns:
            int: 缓存大小
        """
        return self.get('cache_size', 1000)

    def save_to_file(self, config_file: str):
        """
        保存配置到文件

        Args:
            config_file: 配置文件路径
        """
        config_path = Path(config_file)

        try:
            # 确保目录存在
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(config_path, 'w', encoding='utf-8') as f:
                if config_path.suffix == '.json':
                    json.dump(self.config, f, indent=2, ensure_ascii=False)

            print(f"[Config] 配置已保存到: {config_file}")
        except Exception as e:
            print(f"[Config] 保存配置文件失败: {e}")

    def __repr__(self) -> str:
        """字符串表示"""
        return f"DataManagerConfig(duckdb={self.get('duckdb_path')}, tushare={'***' if self.get('tushare_token') else None}, qmt={self.get('qmt_path')})"


# 全局配置实例
_global_config = None


def get_global_config() -> DataManagerConfig:
    """
    获取全局配置实例

    Returns:
        DataManagerConfig: 全局配置实例
    """
    global _global_config
    if _global_config is None:
        _global_config = DataManagerConfig()
    return _global_config


def set_global_config(config: DataManagerConfig):
    """
    设置全局配置实例

    Args:
        config: 配置实例
    """
    global _global_config
    _global_config = config