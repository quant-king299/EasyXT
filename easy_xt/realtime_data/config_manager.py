"""
配置管理模块
提供统一的配置管理功能，支持动态参数调整和多环境配置
"""

import json
import os
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum


class ConfigLevel(Enum):
    """配置级别"""
    SYSTEM = "system"      # 系统级配置
    USER = "user"          # 用户级配置
    SESSION = "session"    # 会话级配置
    RUNTIME = "runtime"    # 运行时配置


@dataclass
class DataProviderConfig:
    """数据源配置"""
    enabled: bool = True
    timeout: int = 30
    retry_count: int = 3
    retry_delay: float = 1.0
    rate_limit: int = 100  # 每分钟请求数
    headers: Optional[Dict[str, str]] = None
    servers: Optional[list] = None  # 服务器列表
    base_urls: Optional[Dict[str, str]] = None  # 基础URL配置
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}
        if self.servers is None:
            self.servers = []
        if self.base_urls is None:
            self.base_urls = {}


@dataclass
class CacheConfig:
    """缓存配置"""
    enabled: bool = True
    backend: str = "memory"  # memory, redis
    ttl: int = 300  # 默认5分钟
    max_size: int = 10000
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0


@dataclass
class WebSocketConfig:
    """WebSocket配置"""
    host: str = "localhost"
    port: int = 8765
    max_connections: int = 100
    heartbeat_interval: int = 30
    message_queue_size: int = 1000


@dataclass
class MonitorConfig:
    """监控配置"""
    enabled: bool = True
    metrics_interval: int = 60
    alert_thresholds: Optional[Dict[str, float]] = None
    notification_channels: Optional[Dict[str, Dict[str, Any]]] = None
    
    def __post_init__(self):
        if self.alert_thresholds is None:
            self.alert_thresholds = {
                "cpu_usage": 80.0,
                "memory_usage": 85.0,
                "error_rate": 5.0
            }
        if self.notification_channels is None:
            self.notification_channels = {}


@dataclass
class SchedulerConfig:
    """调度器配置"""
    enabled: bool = True
    max_workers: int = 10
    task_timeout: int = 300
    retry_policy: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.retry_policy is None:
            self.retry_policy = {
                "max_retries": 3,
                "backoff_factor": 2.0,
                "max_delay": 300
            }


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "config", config_file: str = "realtime_config.json"):
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / config_file
        self.logger = logging.getLogger(__name__)
        
        # 配置层级存储
        self._configs = {level: {} for level in ConfigLevel}
        self._watchers = []  # 配置变更监听器
        
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载配置
        self._load_default_config()
        self._load_config_file()
    
    def _load_default_config(self):
        """加载默认配置"""
        default_config = {
            "data_providers": {
                "tdx": asdict(DataProviderConfig(
                    timeout=30,
                    retry_count=3,
                    rate_limit=200
                )),
                "ths": asdict(DataProviderConfig(
                    timeout=20,
                    retry_count=2,
                    rate_limit=100,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                )),
                "eastmoney": asdict(DataProviderConfig(
                    timeout=25,
                    retry_count=3,
                    rate_limit=150
                ))
            },
            "cache": asdict(CacheConfig()),
            "websocket": asdict(WebSocketConfig()),
            "monitor": asdict(MonitorConfig()),
            "scheduler": asdict(SchedulerConfig()),
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file_path": "logs/realtime_data.log",
                "max_file_size": "10MB",
                "backup_count": 5
            }
        }
        
        self._configs[ConfigLevel.SYSTEM] = default_config
    
    def _load_config_file(self):
        """从文件加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                self._configs[ConfigLevel.USER] = user_config
                self.logger.info(f"配置文件加载成功: {self.config_file}")
            except Exception as e:
                self.logger.error(f"配置文件加载失败: {e}")
        else:
            # 创建默认配置文件
            self.save_config()
    
    def get_config(self, key: str, level: Optional[ConfigLevel] = None) -> Any:
        """获取配置值"""
        # 如果指定了级别，只从该级别获取
        if level:
            return self._get_nested_value(self._configs[level], key)
        
        # 按优先级顺序查找配置
        for level in [ConfigLevel.RUNTIME, ConfigLevel.SESSION, 
                     ConfigLevel.USER, ConfigLevel.SYSTEM]:
            value = self._get_nested_value(self._configs[level], key)
            if value is not None:
                return value
        
        return None
    
    def set_config(self, key: str, value: Any, level: ConfigLevel = ConfigLevel.USER):
        """设置配置值"""
        self._set_nested_value(self._configs[level], key, value)
        
        # 如果是用户级配置，保存到文件
        if level == ConfigLevel.USER:
            self.save_config()
        
        # 通知监听器
        self._notify_watchers(key, value, level)
    
    def get_provider_config(self, provider_name: str) -> DataProviderConfig:
        """获取数据源配置"""
        config_dict = self.get_config(f"data_providers.{provider_name}")
        if config_dict:
            # 过滤掉DataProviderConfig不支持的字段
            valid_fields = {
                'enabled', 'timeout', 'retry_count', 'retry_delay', 
                'rate_limit', 'headers', 'servers', 'base_urls'
            }
            filtered_config = {k: v for k, v in config_dict.items() if k in valid_fields}
            return DataProviderConfig(**filtered_config)
        return DataProviderConfig()
    
    def get_cache_config(self) -> CacheConfig:
        """获取缓存配置"""
        config_dict = self.get_config("cache")
        if config_dict:
            return CacheConfig(**config_dict)
        return CacheConfig()
    
    def get_websocket_config(self) -> WebSocketConfig:
        """获取WebSocket配置"""
        config_dict = self.get_config("websocket")
        if config_dict:
            return WebSocketConfig(**config_dict)
        return WebSocketConfig()
    
    def get_monitor_config(self) -> MonitorConfig:
        """获取监控配置"""
        config_dict = self.get_config("monitor")
        if config_dict:
            return MonitorConfig(**config_dict)
        return MonitorConfig()
    
    def get_scheduler_config(self) -> SchedulerConfig:
        """获取调度器配置"""
        config_dict = self.get_config("scheduler")
        if config_dict:
            return SchedulerConfig(**config_dict)
        return SchedulerConfig()
    
    def update_provider_config(self, provider_name: str, **kwargs):
        """更新数据源配置"""
        current_config = self.get_provider_config(provider_name)
        
        # 更新配置
        for key, value in kwargs.items():
            if hasattr(current_config, key):
                setattr(current_config, key, value)
        
        # 保存更新后的配置
        self.set_config(f"data_providers.{provider_name}", asdict(current_config))
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._configs[ConfigLevel.USER], f, 
                         indent=2, ensure_ascii=False)
            self.logger.info(f"配置已保存到: {self.config_file}")
        except Exception as e:
            self.logger.error(f"配置保存失败: {e}")
    
    def reload_config(self):
        """重新加载配置"""
        self._configs[ConfigLevel.USER] = {}
        self._load_config_file()
        self.logger.info("配置已重新加载")
    
    def add_config_watcher(self, callback):
        """添加配置变更监听器"""
        self._watchers.append(callback)
    
    def remove_config_watcher(self, callback):
        """移除配置变更监听器"""
        if callback in self._watchers:
            self._watchers.remove(callback)
    
    def _notify_watchers(self, key: str, value: Any, level: ConfigLevel):
        """通知配置变更监听器"""
        for watcher in self._watchers:
            try:
                watcher(key, value, level)
            except Exception as e:
                self.logger.error(f"配置监听器执行失败: {e}")
    
    def _get_nested_value(self, config_dict: Dict[str, Any], key: str) -> Any:
        """获取嵌套配置值"""
        keys = key.split('.')
        value = config_dict
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        
        return value
    
    def _set_nested_value(self, config_dict: Dict[str, Any], key: str, value: Any):
        """设置嵌套配置值"""
        keys = key.split('.')
        current = config_dict
        
        # 创建嵌套结构
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # 设置最终值
        current[keys[-1]] = value
    
    def get_all_configs(self) -> Dict[str, Any]:
        """获取所有配置（合并后的结果）"""
        merged_config = {}
        
        # 按优先级合并配置
        for level in [ConfigLevel.SYSTEM, ConfigLevel.USER, 
                     ConfigLevel.SESSION, ConfigLevel.RUNTIME]:
            self._deep_merge(merged_config, self._configs[level])
        
        return merged_config
    
    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]):
        """深度合并字典"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
    
    def validate_config(self) -> Dict[str, Any]:
        """验证配置有效性"""
        errors = []
        warnings = []
        
        try:
            # 验证数据源配置
            providers = self.get_config("data_providers", ConfigLevel.USER) or {}
            for provider_name, config in providers.items():
                if not isinstance(config.get("timeout"), (int, float)) or config.get("timeout") <= 0:
                    errors.append(f"数据源 {provider_name} 的超时时间配置无效")
                
                if not isinstance(config.get("retry_count"), int) or config.get("retry_count") < 0:
                    errors.append(f"数据源 {provider_name} 的重试次数配置无效")
            
            # 验证缓存配置
            cache_config = self.get_cache_config()
            if cache_config.backend not in ["memory", "redis"]:
                errors.append(f"缓存后端配置无效: {cache_config.backend}")
            
            if cache_config.ttl <= 0:
                warnings.append("缓存TTL设置过小，可能影响性能")
            
            # 验证WebSocket配置
            ws_config = self.get_websocket_config()
            if not (1024 <= ws_config.port <= 65535):
                errors.append(f"WebSocket端口配置无效: {ws_config.port}")
            
        except Exception as e:
            errors.append(f"配置验证过程中发生错误: {e}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def export_config(self, file_path: str):
        """导出配置到指定文件"""
        try:
            config_data = self.get_all_configs()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"配置已导出到: {file_path}")
        except Exception as e:
            self.logger.error(f"配置导出失败: {e}")
            raise
    
    def import_config(self, file_path: str, level: ConfigLevel = ConfigLevel.USER):
        """从指定文件导入配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            self._configs[level] = imported_config
            
            if level == ConfigLevel.USER:
                self.save_config()
            
            self.logger.info(f"配置已从 {file_path} 导入到 {level.value} 级别")
        except Exception as e:
            self.logger.error(f"配置导入失败: {e}")
            raise


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config(key: str, default: Any = None) -> Any:
    """获取配置的便捷函数"""
    value = config_manager.get_config(key)
    return value if value is not None else default


def set_config(key: str, value: Any, level: ConfigLevel = ConfigLevel.USER):
    """设置配置的便捷函数"""
    config_manager.set_config(key, value, level)


def get_provider_config(provider_name: str) -> DataProviderConfig:
    """获取数据源配置的便捷函数"""
    return config_manager.get_provider_config(provider_name)