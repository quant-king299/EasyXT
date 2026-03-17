"""
统一配置管理器
提供项目级的配置管理功能
"""

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Union, List
from enum import Enum
import logging

from .config_path import get_config_dir, get_config_path


class ConfigLevel(Enum):
    """配置级别"""
    SYSTEM = "system"      # 系统级配置（默认值）
    USER = "user"          # 用户级配置（配置文件）
    RUNTIME = "runtime"    # 运行时配置（临时修改）


class UnifiedConfigManager:
    """
    统一配置管理器

    特性：
    1. 支持配置层级（系统、用户、运行时）
    2. 运行时配置优先级最高
    3. 支持嵌套键访问（如 "data_providers.tdx.timeout"）
    4. 线程安全
    5. 自动保存和重载
    """

    def __init__(
        self,
        config_file: str = 'unified_config.json',
        auto_save: bool = True,
        env_var: str = 'EASYXT_CONFIG_PATH'
    ):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件名
            auto_save: 是否自动保存配置修改
            env_var: 环境变量名
        """
        self.config_file = config_file
        self.auto_save = auto_save
        self.env_var = env_var
        self.logger = logging.getLogger(__name__)

        # 获取配置目录
        self.config_dir = get_config_dir(env_var)
        self.config_path = self.config_dir / config_file

        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 配置层级存储
        self._configs: Dict[ConfigLevel, Dict[str, Any]] = {
            ConfigLevel.SYSTEM: {},   # 默认系统配置
            ConfigLevel.USER: {},     # 用户配置文件
            ConfigLevel.RUNTIME: {}   # 运行时配置
        }

        # 线程锁
        self._lock = threading.RLock()

        # 加载配置
        self._load_system_defaults()
        self._load_user_config()

        self.logger.info(f"配置管理器初始化成功: {self.config_path}")

    def _load_system_defaults(self):
        """加载系统默认配置"""
        defaults = {
            "data_providers": {
                "tdx": {
                    "enabled": True,
                    "timeout": 30,
                    "retry_count": 3,
                    "retry_delay": 1.0,
                    "rate_limit": 200
                },
                "eastmoney": {
                    "enabled": True,
                    "timeout": 25,
                    "retry_count": 3,
                    "retry_delay": 1.0,
                    "rate_limit": 150
                },
                "tushare": {
                    "enabled": True,
                    "timeout": 30,
                    "retry_count": 3,
                    "token": "",
                    "pro": False
                }
            },
            "cache": {
                "enabled": True,
                "backend": "memory",
                "ttl": 300,
                "max_size": 10000
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file_path": "logs/app.log",
                "max_file_size": "10MB",
                "backup_count": 5
            },
            "trading": {
                "dry_run": True,
                "commission": 0.0003,
                "slippage": 0.001
            }
        }

        self._configs[ConfigLevel.SYSTEM] = defaults

    def _load_user_config(self):
        """从文件加载用户配置"""
        if not self.config_path.exists():
            # 创建默认配置文件
            self._save_user_config()
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            self._configs[ConfigLevel.USER] = user_config
            self.logger.info(f"用户配置加载成功: {self.config_path}")
        except Exception as e:
            self.logger.error(f"用户配置加载失败: {e}")
            self._configs[ConfigLevel.USER] = {}

    def _save_user_config(self):
        """保存用户配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(
                    self._configs[ConfigLevel.USER],
                    f,
                    indent=2,
                    ensure_ascii=False
                )
            self.logger.info(f"用户配置已保存: {self.config_path}")
        except Exception as e:
            self.logger.error(f"用户配置保存失败: {e}")
            raise

    def get(self, key: str, default: Any = None, level: Optional[ConfigLevel] = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键，支持点号分隔的嵌套键（如 "data_providers.tdx.timeout"）
            default: 默认值
            level: 配置级别，如果为None则按优先级查找

        Returns:
            配置值，如果未找到则返回默认值

        Examples:
            >>> config.get("data_providers.tdx.timeout")
            30
            >>> config.get("logging.level")
            'INFO'
        """
        with self._lock:
            if level:
                # 从指定级别获取
                return self._get_nested(self._configs[level], key, default)

            # 按优先级查找：RUNTIME > USER > SYSTEM
            for level in [ConfigLevel.RUNTIME, ConfigLevel.USER, ConfigLevel.SYSTEM]:
                value = self._get_nested(self._configs[level], key, None)
                if value is not None:
                    return value

            return default

    def set(self, key: str, value: Any, level: ConfigLevel = ConfigLevel.USER, save: bool = None) -> None:
        """
        设置配置值

        Args:
            key: 配置键，支持点号分隔的嵌套键
            value: 配置值
            level: 配置级别
            save: 是否立即保存，如果为None则使用auto_save设置

        Examples:
            >>> config.set("logging.level", "DEBUG")
            >>> config.set("data_providers.tdx.timeout", 60)
        """
        with self._lock:
            self._set_nested(self._configs[level], key, value)

            # 如果是用户级配置，自动保存
            if level == ConfigLevel.USER:
                should_save = self.auto_save if save is None else save
                if should_save:
                    self._save_user_config()

            self.logger.debug(f"配置已设置: {key} = {value} (level={level.value})")

    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置（合并后的结果）

        Returns:
            合并后的配置字典
        """
        with self._lock:
            result = {}
            # 按优先级合并：SYSTEM -> USER -> RUNTIME
            for level in [ConfigLevel.SYSTEM, ConfigLevel.USER, ConfigLevel.RUNTIME]:
                self._deep_merge(result, self._configs[level])
            return result

    def reload(self) -> None:
        """重新加载配置文件"""
        with self._lock:
            self._configs[ConfigLevel.USER] = {}
            self._configs[ConfigLevel.RUNTIME] = {}
            self._load_user_config()
            self.logger.info("配置已重新加载")

    def save(self) -> None:
        """保存配置到文件"""
        with self._lock:
            self._save_user_config()

    def reset_runtime(self) -> None:
        """重置运行时配置"""
        with self._lock:
            self._configs[ConfigLevel.RUNTIME] = {}
            self.logger.info("运行时配置已重置")

    def _get_nested(self, config: Dict[str, Any], key: str, default: Any) -> Any:
        """获取嵌套配置值"""
        keys = key.split('.')
        value = config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def _set_nested(self, config: Dict[str, Any], key: str, value: Any) -> None:
        """设置嵌套配置值"""
        keys = key.split('.')
        current = config

        # 创建嵌套结构
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # 设置最终值
        current[keys[-1]] = value

    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """深度合并字典"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取配置段

        Args:
            section: 配置段名称

        Returns:
            配置段字典
        """
        return self.get(section, {})

    def update(self, config: Dict[str, Any], level: ConfigLevel = ConfigLevel.USER) -> None:
        """
        批量更新配置

        Args:
            config: 配置字典
            level: 配置级别
        """
        with self._lock:
            self._deep_merge(self._configs[level], config)
            if level == ConfigLevel.USER and self.auto_save:
                self._save_user_config()

    def validate(self) -> Dict[str, Any]:
        """
        验证配置

        Returns:
            验证结果，包含 'valid', 'errors', 'warnings' 键
        """
        errors = []
        warnings = []

        try:
            # 验证数据源配置
            providers = self.get("data_providers", {})
            for name, config in providers.items():
                if not isinstance(config.get("timeout"), (int, float)) or config.get("timeout", 0) <= 0:
                    errors.append(f"数据源 {name} 的超时时间配置无效")
                if not isinstance(config.get("retry_count"), int) or config.get("retry_count", 0) < 0:
                    errors.append(f"数据源 {name} 的重试次数配置无效")

            # 验证缓存配置
            cache_backend = self.get("cache.backend", "memory")
            if cache_backend not in ["memory", "redis"]:
                errors.append(f"缓存后端配置无效: {cache_backend}")

            # 验证日志级别
            log_level = self.get("logging.level", "INFO")
            if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                errors.append(f"日志级别配置无效: {log_level}")

        except Exception as e:
            errors.append(f"配置验证过程中发生错误: {e}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def export(self, file_path: str) -> None:
        """
        导出配置到指定文件

        Args:
            file_path: 导出文件路径
        """
        config = self.get_all()
        export_path = Path(file_path)

        try:
            export_path.parent.mkdir(parents=True, exist_ok=True)
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.logger.info(f"配置已导出到: {export_path}")
        except Exception as e:
            self.logger.error(f"配置导出失败: {e}")
            raise

    def import_config(self, file_path: str, level: ConfigLevel = ConfigLevel.USER) -> None:
        """
        从指定文件导入配置

        Args:
            file_path: 导入文件路径
            level: 配置级别
        """
        import_path = Path(file_path)

        if not import_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {import_path}")

        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)

            self._configs[level] = imported_config

            if level == ConfigLevel.USER and self.auto_save:
                self._save_user_config()

            self.logger.info(f"配置已从 {import_path} 导入到 {level.value} 级别")
        except Exception as e:
            self.logger.error(f"配置导入失败: {e}")
            raise


# 全局配置管理器实例
_global_config_manager: Optional[UnifiedConfigManager] = None


def get_global_config_manager() -> UnifiedConfigManager:
    """获取全局配置管理器实例（单例模式）"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = UnifiedConfigManager()
    return _global_config_manager


def get_config(key: str, default: Any = None) -> Any:
    """
    获取配置值的便捷函数

    Args:
        key: 配置键
        default: 默认值

    Returns:
        配置值

    Examples:
        >>> from core.config import get_config
        >>> timeout = get_config("data_providers.tdx.timeout", 30)
    """
    return get_global_config_manager().get(key, default)


def set_config(key: str, value: Any) -> None:
    """
    设置配置值的便捷函数

    Args:
        key: 配置键
        value: 配置值

    Examples:
        >>> from core.config import set_config
        >>> set_config("logging.level", "DEBUG")
    """
    get_global_config_manager().set(key, value)
