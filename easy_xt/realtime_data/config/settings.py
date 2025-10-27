"""
实时数据配置管理

管理各种数据源的配置参数和系统设置。
"""

import json
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class RealtimeDataConfig:
    """实时数据配置管理器"""
    
    DEFAULT_CONFIG = {
        "providers": {
            "tdx": {
                "enabled": True,
                "servers": [
                    {"host": "119.147.212.81", "port": 7709},
                    {"host": "114.80.63.12", "port": 7709},
                    {"host": "180.153.39.51", "port": 7709}
                ],
                "timeout": 10,
                "retry_count": 3,
                "retry_delay": 1
            },
            "ths": {
                "enabled": True,
                "base_url": "http://data.10jqka.com.cn",
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "http://data.10jqka.com.cn/"
                },
                "timeout": 15,
                "retry_count": 2
            },
            "eastmoney": {
                "enabled": True,
                "base_url": "http://push2his.eastmoney.com",
                "timeout": 10,
                "retry_count": 2,
                "request_delay": 0.5
            }
        },
        "cache": {
            "enabled": True,
            "ttl": 60,
            "max_size": 1000
        },
        "websocket": {
            "host": "localhost",
            "port": 8765,
            "max_connections": 100
        },
        "scheduler": {
            "update_interval": 3,
            "batch_size": 50
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """初始化配置管理器
        
        Args:
            config_file: 配置文件路径，如果为None则使用默认配置
        """
        self.config_file = config_file or "realtime_config.json"
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件
        
        Returns:
            Dict: 配置字典
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"配置文件加载成功: {self.config_file}")
                return self._merge_config(self.DEFAULT_CONFIG, config)
            except Exception as e:
                logger.error(f"配置文件加载失败: {e}")
                return self.DEFAULT_CONFIG.copy()
        else:
            logger.info("配置文件不存在，使用默认配置")
            return self.DEFAULT_CONFIG.copy()
    
    def _merge_config(self, default: Dict, custom: Dict) -> Dict:
        """合并默认配置和自定义配置
        
        Args:
            default: 默认配置
            custom: 自定义配置
            
        Returns:
            Dict: 合并后的配置
        """
        result = default.copy()
        for key, value in custom.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """获取特定数据源的配置
        
        Args:
            provider_name: 数据源名称
            
        Returns:
            Dict: 数据源配置
        """
        return self.config.get("providers", {}).get(provider_name, {})
    
    def get_cache_config(self) -> Dict[str, Any]:
        """获取缓存配置
        
        Returns:
            Dict: 缓存配置
        """
        return self.config.get("cache", {})
    
    def get_websocket_config(self) -> Dict[str, Any]:
        """获取WebSocket配置
        
        Returns:
            Dict: WebSocket配置
        """
        return self.config.get("websocket", {})
    
    def get_scheduler_config(self) -> Dict[str, Any]:
        """获取调度器配置
        
        Returns:
            Dict: 调度器配置
        """
        return self.config.get("scheduler", {})
    
    def update_config(self, key: str, value: Any) -> None:
        """更新配置项
        
        Args:
            key: 配置键，支持点分隔的嵌套键如 "providers.tdx.timeout"
            value: 配置值
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        logger.info(f"配置更新: {key} = {value}")
    
    def save_config(self) -> None:
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"配置保存成功: {self.config_file}")
        except Exception as e:
            logger.error(f"配置保存失败: {e}")
    
    def is_provider_enabled(self, provider_name: str) -> bool:
        """检查数据源是否启用
        
        Args:
            provider_name: 数据源名称
            
        Returns:
            bool: 是否启用
        """
        provider_config = self.get_provider_config(provider_name)
        return provider_config.get("enabled", False)