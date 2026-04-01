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
        # DuckDB路径（None = 自动检测或不用DuckDB）
        'duckdb_path': None,  # 改为None，避免硬编码路径
        'tushare_token': None,
        'tushare_token_2': None,  # 备用token（限流时自动切换）
        'qmt_path': None,
        # 数据源优先级（改为智能模式，优先使用本地可用数据源）
        'preferred_sources': None,  # None = 自动检测可用数据源
        'cache_enabled': True,
        'cache_size': 1000,
        'log_level': 'INFO',
        'timeout': 30,
        'max_retries': 3,
        # 新增：新手模式（默认False，优先QMT/Tushare）
        'beginner_mode': False,
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

    def _load_dotenv(self):
        """
        尝试加载.env文件

        从项目根目录加载.env文件（如果存在）
        """
        try:
            from pathlib import Path

            # 尝试多个可能的.env文件位置
            possible_paths = [
                Path.cwd() / '.env',  # 当前工作目录
                Path(__file__).parent.parent.parent / '.env',  # 项目根目录
                Path.home() / '.env',  # 用户主目录
            ]

            for env_path in possible_paths:
                if env_path.exists():
                    # 读取.env文件并手动解析（避免依赖python-dotenv）
                    with open(env_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            # 跳过注释和空行
                            if not line or line.startswith('#'):
                                continue
                            # 解析 KEY=VALUE 格式
                            if '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip()
                                # 移除引号
                                if value.startswith('"') and value.endswith('"'):
                                    value = value[1:-1]
                                elif value.startswith("'") and value.endswith("'"):
                                    value = value[1:-1]
                                # 只设置未设置的环境变量
                                if key not in os.environ:
                                    os.environ[key] = value
                    # 找到一个有效的.env文件后就停止
                    break
        except Exception as e:
            # .env文件加载失败不是致命错误，静默处理
            pass

    def _load_from_env(self):
        """从环境变量和.env文件加载配置"""
        # 1. 先尝试加载 .env 文件
        self._load_dotenv()

        # 2. 从环境变量加载配置
        # Tushare Token
        if 'TUSHARE_TOKEN' in os.environ:
            self.config['tushare_token'] = os.environ['TUSHARE_TOKEN']

        # Tushare 备用Token（限流时自动切换）
        if 'TUSHARE_TOKEN_2' in os.environ:
            self.config['tushare_token_2'] = os.environ['TUSHARE_TOKEN_2']

        # DuckDB路径
        if 'DUCKDB_PATH' in os.environ:
            self.config['duckdb_path'] = os.environ['DUCKDB_PATH']
        # 如果没有设置DUCKDB_PATH，尝试检测常见路径
        elif self.config.get('duckdb_path') is None:
            self.config['duckdb_path'] = self._detect_duckdb_path()

        # QMT路径
        if 'QMT_PATH' in os.environ:
            self.config['qmt_path'] = os.environ['QMT_PATH']

        # 日志级别
        if 'LOG_LEVEL' in os.environ:
            self.config['log_level'] = os.environ['LOG_LEVEL']

        # 新手模式（环境变量）
        if 'BEGINNER_MODE' in os.environ:
            self.config['beginner_mode'] = os.environ['BEGINNER_MODE'].lower() in ('true', '1', 'yes')

    def _detect_duckdb_path(self) -> Optional[str]:
        """
        自动检测DuckDB数据库文件

        Returns:
            Optional[str]: 找到的DuckDB路径，未找到返回None
        """
        # 常见路径列表（按优先级）
        possible_paths = [
            'D:/StockData/stock_data.ddb',  # Windows D盘
            'C:/StockData/stock_data.ddb',  # Windows C盘
            'E:/StockData/stock_data.ddb',  # Windows E盘
            './data/stock_data.ddb',        # 项目相对路径
            '~/StockData/stock_data.ddb',   # 用户主目录
            '../stock_data.ddb',            # 项目上级目录
        ]

        for path in possible_paths:
            # 展开 ~
            expanded_path = os.path.expanduser(path)
            # 转为绝对路径
            abs_path = os.path.abspath(expanded_path)

            if os.path.exists(abs_path):
                print(f"[Config] 自动检测到DuckDB数据库: {abs_path}")
                return abs_path

        # 未找到DuckDB文件
        return None

    def _detect_available_sources(self) -> List[str]:
        """
        检测可用的数据源

        Returns:
            List[str]: 可用数据源列表（按优先级排序）
        """
        available = []

        # 1. 检测DuckDB（如果文件存在）
        if self.config.get('duckdb_path') and os.path.exists(self.config['duckdb_path']):
            available.append('duckdb')

        # 2. 检测QMT（always available on Windows with QMT installed）
        # QMT总是可用的（如果用户安装了QMT/miniQMT）
        if os.name == 'nt':  # Windows系统
            available.append('qmt')

        # 3. 检测Tushare（如果有token）
        if self.config.get('tushare_token'):
            available.append('tushare')

        return available

    def get(self, key: str, default=None):
        """
        获取配置值

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值或默认值
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
            source_name: 数据源名称 (duckdb/tushare/qmt)

        Returns:
            Dict: 数据源配置
        """
        source_configs = {
            'duckdb': {
                'path': self.get('duckdb_path'),
                'enabled': self.get('duckdb_path') is not None
            },
            'tushare': {
                'token': self.get('tushare_token'),
                'token_2': self.get('tushare_token_2'),
                'enabled': self.get('tushare_token') is not None
            },
            'qmt': {
                'path': self.get('qmt_path'),
                'enabled': True  # QMT总是可用的（如果安装了）
            }
        }

        return source_configs.get(source_name, {})

    def get_preferred_sources(self) -> List[str]:
        """
        获取优先数据源列表

        如果没有明确指定preferred_sources，自动检测可用的数据源

        Returns:
            List[str]: 数据源名称列表
        """
        # 如果已经明确指定了优先级，直接返回
        if self.config.get('preferred_sources'):
            return self.config['preferred_sources']

        # 否则，自动检测可用数据源
        available = self._detect_available_sources()

        if not available:
            # 如果什么都检测不到，使用默认降级方案
            print("[Config] 未检测到任何数据源，使用默认降级方案: QMT -> Tushare")
            return ['qmt', 'tushare']

        # 根据是否为新手模式调整优先级
        if self.config.get('beginner_mode'):
            # 新手模式：优先使用最容易获取的数据源
            # QMT（本地） > Tushare（在线，需token） > DuckDB（需要下载）
            preferred = []
            if 'qmt' in available:
                preferred.append('qmt')
            if 'tushare' in available:
                preferred.append('tushare')
            if 'duckdb' in available:
                preferred.append('duckdb')
        else:
            # 进阶模式：优先使用最快的数据源
            # DuckDB（本地最快） > QMT（本地） > Tushare（在线）
            preferred = available

        print(f"[Config] 自动检测到的可用数据源: {preferred}")
        return preferred

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