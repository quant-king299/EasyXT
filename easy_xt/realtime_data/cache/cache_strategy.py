"""
缓存策略配置

定义缓存的键值规则、过期时间和更新策略。
"""

from typing import Dict, Any, Optional, Union
from enum import Enum
from dataclasses import dataclass
import hashlib
import json


class CacheType(Enum):
    """缓存类型枚举"""
    MEMORY = "memory"
    REDIS = "redis"
    HYBRID = "hybrid"  # 内存+Redis混合


class EvictionPolicy(Enum):
    """缓存淘汰策略"""
    LRU = "lru"        # 最近最少使用
    LFU = "lfu"        # 最少使用频率
    FIFO = "fifo"      # 先进先出
    TTL = "ttl"        # 基于过期时间


@dataclass
class CacheConfig:
    """缓存配置"""
    # 基础配置
    cache_type: CacheType = CacheType.MEMORY
    max_size: int = 1000
    default_ttl: int = 300  # 默认5分钟
    
    # 淘汰策略
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    
    # Redis配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # 性能配置
    enable_compression: bool = False
    compression_threshold: int = 1024  # 超过1KB压缩
    
    # 统计配置
    enable_stats: bool = True


class CacheStrategy:
    """缓存策略管理器"""
    
    # 预定义的缓存策略
    STRATEGIES = {
        # 实时行情数据 - 短期缓存
        "realtime_quotes": {
            "ttl": 5,           # 5秒过期
            "max_size": 500,
            "priority": "high"
        },
        
        # 热门股票 - 中期缓存
        "hot_stocks": {
            "ttl": 60,          # 1分钟过期
            "max_size": 100,
            "priority": "medium"
        },
        
        # 概念数据 - 长期缓存
        "concept_data": {
            "ttl": 300,         # 5分钟过期
            "max_size": 200,
            "priority": "medium"
        },
        
        # 市场状态 - 超短期缓存
        "market_status": {
            "ttl": 10,          # 10秒过期
            "max_size": 10,
            "priority": "low"
        },
        
        # 数据源状态 - 短期缓存
        "source_status": {
            "ttl": 30,          # 30秒过期
            "max_size": 50,
            "priority": "low"
        },
        
        # 历史数据 - 长期缓存
        "historical_data": {
            "ttl": 3600,        # 1小时过期
            "max_size": 1000,
            "priority": "low"
        }
    }
    
    def __init__(self, config: CacheConfig):
        """初始化缓存策略
        
        Args:
            config: 缓存配置
        """
        self.config = config
        self.custom_strategies = {}
    
    def get_strategy(self, data_type: str) -> Dict[str, Any]:
        """获取数据类型的缓存策略
        
        Args:
            data_type: 数据类型
            
        Returns:
            Dict: 缓存策略配置
        """
        # 优先使用自定义策略
        if data_type in self.custom_strategies:
            return self.custom_strategies[data_type]
        
        # 使用预定义策略
        if data_type in self.STRATEGIES:
            return self.STRATEGIES[data_type]
        
        # 默认策略
        return {
            "ttl": self.config.default_ttl,
            "max_size": 100,
            "priority": "medium"
        }
    
    def add_strategy(self, data_type: str, strategy: Dict[str, Any]) -> None:
        """添加自定义缓存策略
        
        Args:
            data_type: 数据类型
            strategy: 策略配置
        """
        self.custom_strategies[data_type] = strategy
    
    def generate_key(self, data_type: str, params: Dict[str, Any]) -> str:
        """生成缓存键
        
        Args:
            data_type: 数据类型
            params: 参数字典
            
        Returns:
            str: 缓存键
        """
        # 创建参数的哈希值
        params_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        
        return f"easyxt:{data_type}:{params_hash}"
    
    def should_cache(self, data_type: str, data_size: int) -> bool:
        """判断是否应该缓存数据
        
        Args:
            data_type: 数据类型
            data_size: 数据大小（字节）
            
        Returns:
            bool: 是否缓存
        """
        strategy = self.get_strategy(data_type)
        
        # 检查数据大小限制
        max_data_size = strategy.get("max_data_size", 1024 * 1024)  # 默认1MB
        if data_size > max_data_size:
            return False
        
        # 检查优先级
        priority = strategy.get("priority", "medium")
        if priority == "none":
            return False
        
        return True
    
    def get_ttl(self, data_type: str) -> int:
        """获取数据类型的TTL
        
        Args:
            data_type: 数据类型
            
        Returns:
            int: TTL秒数
        """
        strategy = self.get_strategy(data_type)
        return strategy.get("ttl", self.config.default_ttl)
    
    def get_priority(self, data_type: str) -> str:
        """获取数据类型的优先级
        
        Args:
            data_type: 数据类型
            
        Returns:
            str: 优先级
        """
        strategy = self.get_strategy(data_type)
        return strategy.get("priority", "medium")


class CacheKeyBuilder:
    """缓存键构建器"""
    
    @staticmethod
    def build_quotes_key(symbols: list, source: str = "auto") -> str:
        """构建行情数据缓存键"""
        symbols_str = ",".join(sorted(symbols))
        return f"quotes:{source}:{symbols_str}"
    
    @staticmethod
    def build_hot_stocks_key(count: int, source: str = "auto") -> str:
        """构建热门股票缓存键"""
        return f"hot_stocks:{source}:{count}"
    
    @staticmethod
    def build_concepts_key(count: int, source: str = "auto") -> str:
        """构建概念数据缓存键"""
        return f"concepts:{source}:{count}"
    
    @staticmethod
    def build_market_status_key() -> str:
        """构建市场状态缓存键"""
        return "market_status:current"
    
    @staticmethod
    def build_source_status_key() -> str:
        """构建数据源状态缓存键"""
        return "source_status:all"
    
    @staticmethod
    def build_comparison_key(symbols: list) -> str:
        """构建多数据源对比缓存键"""
        symbols_str = ",".join(sorted(symbols))
        return f"comparison:{symbols_str}"


class CacheMetrics:
    """缓存指标统计"""
    
    def __init__(self):
        """初始化指标"""
        self.reset()
    
    def reset(self):
        """重置指标"""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.evictions = 0
        self.errors = 0
        
        # 按数据类型统计
        self.type_stats = {}
    
    def record_hit(self, data_type: str = None):
        """记录缓存命中"""
        self.hits += 1
        if data_type:
            self._update_type_stats(data_type, "hits")
    
    def record_miss(self, data_type: str = None):
        """记录缓存未命中"""
        self.misses += 1
        if data_type:
            self._update_type_stats(data_type, "misses")
    
    def record_set(self, data_type: str = None):
        """记录缓存设置"""
        self.sets += 1
        if data_type:
            self._update_type_stats(data_type, "sets")
    
    def record_delete(self, data_type: str = None):
        """记录缓存删除"""
        self.deletes += 1
        if data_type:
            self._update_type_stats(data_type, "deletes")
    
    def record_eviction(self, data_type: str = None):
        """记录缓存淘汰"""
        self.evictions += 1
        if data_type:
            self._update_type_stats(data_type, "evictions")
    
    def record_error(self, data_type: str = None):
        """记录缓存错误"""
        self.errors += 1
        if data_type:
            self._update_type_stats(data_type, "errors")
    
    def _update_type_stats(self, data_type: str, metric: str):
        """更新类型统计"""
        if data_type not in self.type_stats:
            self.type_stats[data_type] = {
                "hits": 0, "misses": 0, "sets": 0,
                "deletes": 0, "evictions": 0, "errors": 0
            }
        self.type_stats[data_type][metric] += 1
    
    def get_hit_rate(self) -> float:
        """获取缓存命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total": {
                "hits": self.hits,
                "misses": self.misses,
                "sets": self.sets,
                "deletes": self.deletes,
                "evictions": self.evictions,
                "errors": self.errors,
                "hit_rate": self.get_hit_rate()
            },
            "by_type": self.type_stats
        }