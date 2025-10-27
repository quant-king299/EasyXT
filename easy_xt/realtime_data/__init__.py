"""
实时数据模块

提供统一的实时数据接口，支持多数据源和缓存功能。
"""

from .unified_api import UnifiedDataAPI
from .providers import BaseDataProvider, TdxDataProvider, ThsDataProvider, EastmoneyDataProvider
from .config_manager import (
    ConfigManager, ConfigLevel, DataProviderConfig, CacheConfig as ConfigCacheConfig,
    WebSocketConfig, MonitorConfig, SchedulerConfig, 
    get_config, set_config, get_provider_config
)
from .config.settings import RealtimeDataConfig
from .push_service import RealtimeDataPushService
from .api_server import RealtimeDataAPIServer
from .cache import CacheManager as DataCacheManager, MemoryCache, RedisCache, CacheConfig
from .error_handler import (
    ErrorHandler, ErrorInfo, RecoveryAction, CircuitBreaker,
    ErrorSeverity, ErrorCategory, RecoveryStrategy, CircuitBreakerState,
    handle_errors, handle_async_errors, handle_error, record_success
)

__all__ = [
    'UnifiedDataAPI',
    'BaseDataProvider', 
    'TdxDataProvider', 
    'ThsDataProvider', 
    'EastmoneyDataProvider',
    'ConfigManager',
    'ConfigLevel',
    'DataProviderConfig',
    'ConfigCacheConfig',
    'WebSocketConfig',
    'MonitorConfig', 
    'SchedulerConfig',
    'get_config',
    'set_config',
    'get_provider_config',
    'RealtimeDataConfig',
    'RealtimeDataPushService',
    'RealtimeDataAPIServer',
    'DataCacheManager',
    'MemoryCache',
    'RedisCache', 
    'CacheConfig',
    'ErrorHandler',
    'ErrorInfo',
    'RecoveryAction',
    'CircuitBreaker',
    'ErrorSeverity',
    'ErrorCategory',
    'RecoveryStrategy',
    'CircuitBreakerState',
    'handle_errors',
    'handle_async_errors',
    'handle_error',
    'record_success'
]