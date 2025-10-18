"""
实时数据配置管理

更新配置以支持缓存功能。
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from .cache.cache_strategy import CacheConfig, CacheType, EvictionPolicy

logger = logging.getLogger(__name__)


@dataclass
class RealtimeDataConfig:
    """实时数据配置类"""
    
    # 数据源配置
    data_sources: Dict[str, bool] = None
    source_priority: List[str] = None
    
    # API服务配置
    api_host: str = "localhost"
    api_port: int = 8080
    api_cors_origins: List[str] = None
    
    # WebSocket配置
    websocket_host: str = "localhost"
    websocket_port: int = 8765
    websocket_max_connections: int = 100
    
    # 性能配置
    max_workers: int = 10
    request_timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # 缓存配置
    cache_enabled: bool = True
    cache_type: str = "memory"  # memory, redis, hybrid
    cache_max_size: int = 1000
    cache_default_ttl: int = 300
    cache_eviction_policy: str = "lru"  # lru, lfu, fifo
    cache_compression: bool = False
    cache_compression_threshold: int = 1024
    
    # Redis配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = None
    log_max_size: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5
    
    def __post_init__(self):
        """初始化后处理"""
        if self.data_sources is None:
            self.data_sources = {
                "tdx": True,
                "ths": True,
                "eastmoney": True
            }
        
        if self.source_priority is None:
            self.source_priority = ["tdx", "ths", "eastmoney"]
        
        if self.api_cors_origins is None:
            self.api_cors_origins = ["*"]
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        return getattr(self, key, default)
    
    def set(self, key: str, value: Any):
        """设置配置值
        
        Args:
            key: 配置键
            value: 配置值
        """
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            logger.warning(f"未知配置项: {key}")
    
    def get_cache_config(self) -> CacheConfig:
        """获取缓存配置对象
        
        Returns:
            CacheConfig: 缓存配置
        """
        try:
            cache_type = CacheType(self.cache_type)
        except ValueError:
            logger.warning(f"无效的缓存类型: {self.cache_type}，使用默认值 memory")
            cache_type = CacheType.MEMORY
        
        try:
            eviction_policy = EvictionPolicy(self.cache_eviction_policy)
        except ValueError:
            logger.warning(f"无效的淘汰策略: {self.cache_eviction_policy}，使用默认值 lru")
            eviction_policy = EvictionPolicy.LRU
        
        return CacheConfig(
            cache_type=cache_type,
            max_size=self.cache_max_size,
            default_ttl=self.cache_default_ttl,
            eviction_policy=eviction_policy,
            redis_host=self.redis_host,
            redis_port=self.redis_port,
            redis_db=self.redis_db,
            redis_password=self.redis_password,
            enable_compression=self.cache_compression,
            compression_threshold=self.cache_compression_threshold,
            enable_stats=True
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            Dict: 配置字典
        """
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RealtimeDataConfig':
        """从字典创建配置
        
        Args:
            data: 配置字典
            
        Returns:
            RealtimeDataConfig: 配置实例
        """
        return cls(**data)
    
    def save_to_file(self, file_path: str):
        """保存配置到文件
        
        Args:
            file_path: 文件路径
        """
        try:
            config_dict = self.to_dict()
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"配置已保存到: {file_path}")
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            raise
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'RealtimeDataConfig':
        """从文件加载配置
        
        Args:
            file_path: 文件路径
            
        Returns:
            RealtimeDataConfig: 配置实例
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            logger.info(f"配置已从文件加载: {file_path}")
            return cls.from_dict(config_dict)
            
        except FileNotFoundError:
            logger.warning(f"配置文件不存在: {file_path}，使用默认配置")
            return cls()
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            raise
    
    def validate(self) -> List[str]:
        """验证配置
        
        Returns:
            List[str]: 错误信息列表
        """
        errors = []
        
        # 验证端口号
        if not (1 <= self.api_port <= 65535):
            errors.append(f"无效的API端口号: {self.api_port}")
        
        if not (1 <= self.websocket_port <= 65535):
            errors.append(f"无效的WebSocket端口号: {self.websocket_port}")
        
        if not (1 <= self.redis_port <= 65535):
            errors.append(f"无效的Redis端口号: {self.redis_port}")
        
        # 验证数值范围
        if self.max_workers <= 0:
            errors.append(f"无效的工作线程数: {self.max_workers}")
        
        if self.request_timeout <= 0:
            errors.append(f"无效的请求超时时间: {self.request_timeout}")
        
        if self.cache_max_size <= 0:
            errors.append(f"无效的缓存大小: {self.cache_max_size}")
        
        if self.cache_default_ttl < 0:
            errors.append(f"无效的缓存TTL: {self.cache_default_ttl}")
        
        # 验证数据源
        if not self.data_sources:
            errors.append("至少需要启用一个数据源")
        
        enabled_sources = [k for k, v in self.data_sources.items() if v]
        if not enabled_sources:
            errors.append("至少需要启用一个数据源")
        
        # 验证优先级列表
        for source in self.source_priority:
            if source not in self.data_sources:
                errors.append(f"优先级列表中的数据源不存在: {source}")
        
        return errors
    
    def get_enabled_sources(self) -> List[str]:
        """获取启用的数据源列表
        
        Returns:
            List[str]: 启用的数据源
        """
        return [source for source, enabled in self.data_sources.items() if enabled]
    
    def is_source_enabled(self, source: str) -> bool:
        """检查数据源是否启用
        
        Args:
            source: 数据源名称
            
        Returns:
            bool: 是否启用
        """
        return self.data_sources.get(source, False)
    
    def enable_source(self, source: str):
        """启用数据源
        
        Args:
            source: 数据源名称
        """
        if source in self.data_sources:
            self.data_sources[source] = True
            logger.info(f"数据源已启用: {source}")
        else:
            logger.warning(f"未知数据源: {source}")
    
    def disable_source(self, source: str):
        """禁用数据源
        
        Args:
            source: 数据源名称
        """
        if source in self.data_sources:
            self.data_sources[source] = False
            logger.info(f"数据源已禁用: {source}")
        else:
            logger.warning(f"未知数据源: {source}")
    
    def set_source_priority(self, priority: List[str]):
        """设置数据源优先级
        
        Args:
            priority: 优先级列表
        """
        # 验证优先级列表
        for source in priority:
            if source not in self.data_sources:
                raise ValueError(f"优先级列表中的数据源不存在: {source}")
        
        self.source_priority = priority
        logger.info(f"数据源优先级已更新: {priority}")


def load_config(config_file: str = None) -> RealtimeDataConfig:
    """加载配置的便捷函数
    
    Args:
        config_file: 配置文件路径，None使用默认路径
        
    Returns:
        RealtimeDataConfig: 配置实例
    """
    if config_file is None:
        # 默认配置文件路径
        config_file = os.path.join(
            os.path.dirname(__file__), 
            "..", "..", "config", "realtime_data.json"
        )
    
    if os.path.exists(config_file):
        return RealtimeDataConfig.load_from_file(config_file)
    else:
        logger.info("使用默认配置")
        return RealtimeDataConfig()


def create_default_config_file(file_path: str = None):
    """创建默认配置文件
    
    Args:
        file_path: 配置文件路径
    """
    if file_path is None:
        file_path = os.path.join(
            os.path.dirname(__file__), 
            "..", "..", "config", "realtime_data.json"
        )
    
    config = RealtimeDataConfig()
    config.save_to_file(file_path)
    logger.info(f"默认配置文件已创建: {file_path}")


# 全局配置实例
_global_config = None


def get_global_config() -> RealtimeDataConfig:
    """获取全局配置实例
    
    Returns:
        RealtimeDataConfig: 全局配置
    """
    global _global_config
    if _global_config is None:
        _global_config = load_config()
    return _global_config


def set_global_config(config: RealtimeDataConfig):
    """设置全局配置实例
    
    Args:
        config: 配置实例
    """
    global _global_config
    _global_config = config