"""
缓存管理器

统一管理内存缓存和Redis缓存，提供智能缓存策略。
"""

import time
import logging
from typing import Any, Dict, Optional, List, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .cache_strategy import CacheConfig, CacheStrategy, CacheType, CacheKeyBuilder, CacheMetrics
from .memory_cache import MemoryCache

try:
    from .redis_cache import RedisCache, REDIS_AVAILABLE
except ImportError:
    RedisCache = None
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class CacheManager:
    """缓存管理器
    
    支持多级缓存策略：
    1. 内存缓存（L1）- 最快访问
    2. Redis缓存（L2）- 分布式共享
    3. 混合模式 - 内存+Redis
    """
    
    def __init__(self, config: CacheConfig):
        """初始化缓存管理器
        
        Args:
            config: 缓存配置
        """
        self.config = config
        self.strategy = CacheStrategy(config)
        self.metrics = CacheMetrics()
        
        # 初始化缓存后端
        self.memory_cache = None
        self.redis_cache = None
        self.cache_type = config.cache_type
        
        self._init_caches()
        
        # 线程池用于异步操作
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cache")
        
        # 缓存同步锁
        self.sync_lock = threading.RLock()
        
        logger.info(f"缓存管理器初始化完成，类型: {config.cache_type.value}")
    
    def _init_caches(self):
        """初始化缓存后端"""
        try:
            if self.cache_type in [CacheType.MEMORY, CacheType.HYBRID]:
                self.memory_cache = MemoryCache(self.config)
                logger.info("内存缓存初始化成功")
            
            if self.cache_type in [CacheType.REDIS, CacheType.HYBRID]:
                if REDIS_AVAILABLE and RedisCache:
                    try:
                        self.redis_cache = RedisCache(self.config)
                        if not self.redis_cache.ping():
                            logger.warning("Redis缓存连接失败，降级为内存缓存")
                            if self.cache_type == CacheType.REDIS:
                                # Redis模式下连接失败，创建内存缓存作为备用
                                self.memory_cache = MemoryCache(self.config)
                                self.cache_type = CacheType.MEMORY
                        else:
                            logger.info("Redis缓存初始化成功")
                    except ImportError as e:
                        logger.warning(f"Redis缓存初始化失败: {e}")
                        self.redis_cache = None
                        if self.cache_type == CacheType.REDIS:
                            self.memory_cache = MemoryCache(self.config)
                            self.cache_type = CacheType.MEMORY
                else:
                    logger.warning("Redis库不可用，降级为内存缓存")
                    self.redis_cache = None
                    if self.cache_type == CacheType.REDIS:
                        self.memory_cache = MemoryCache(self.config)
                        self.cache_type = CacheType.MEMORY
                    
        except Exception as e:
            logger.error(f"缓存初始化失败: {e}")
            # 降级为内存缓存
            if not self.memory_cache:
                self.memory_cache = MemoryCache(self.config)
                self.cache_type = CacheType.MEMORY
    
    def get(self, key: str, data_type: str = "default") -> Optional[Any]:
        """获取缓存值
        
        Args:
            key: 缓存键
            data_type: 数据类型
            
        Returns:
            Any: 缓存值，不存在返回None
        """
        start_time = time.time()
        
        try:
            # 生成完整的缓存键
            full_key = self.strategy.generate_key(data_type, {"key": key})
            
            if self.cache_type == CacheType.MEMORY:
                return self._get_from_memory(full_key, data_type)
            
            elif self.cache_type == CacheType.REDIS:
                return self._get_from_redis(full_key, data_type)
            
            elif self.cache_type == CacheType.HYBRID:
                return self._get_hybrid(full_key, data_type)
            
            return None
            
        except Exception as e:
            logger.error(f"获取缓存失败: {key}, 错误: {e}")
            self.metrics.record_error(data_type)
            return None
        
        finally:
            # 记录访问时间
            access_time = time.time() - start_time
            if access_time > 0.1:  # 超过100ms记录警告
                logger.warning(f"缓存访问耗时过长: {key}, 耗时: {access_time:.3f}s")
    
    def set(self, key: str, value: Any, data_type: str = "default", ttl: int = None) -> bool:
        """设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            data_type: 数据类型
            ttl: 过期时间（秒）
            
        Returns:
            bool: 是否设置成功
        """
        try:
            # 检查是否应该缓存
            value_size = len(str(value).encode('utf-8'))
            if not self.strategy.should_cache(data_type, value_size):
                return False
            
            # 生成完整的缓存键
            full_key = self.strategy.generate_key(data_type, {"key": key})
            
            # 获取TTL
            if ttl is None:
                ttl = self.strategy.get_ttl(data_type)
            
            if self.cache_type == CacheType.MEMORY:
                return self._set_to_memory(full_key, value, ttl, data_type)
            
            elif self.cache_type == CacheType.REDIS:
                return self._set_to_redis(full_key, value, ttl, data_type)
            
            elif self.cache_type == CacheType.HYBRID:
                return self._set_hybrid(full_key, value, ttl, data_type)
            
            return False
            
        except Exception as e:
            logger.error(f"设置缓存失败: {key}, 错误: {e}")
            self.metrics.record_error(data_type)
            return False
    
    def delete(self, key: str, data_type: str = "default") -> bool:
        """删除缓存项
        
        Args:
            key: 缓存键
            data_type: 数据类型
            
        Returns:
            bool: 是否删除成功
        """
        try:
            full_key = self.strategy.generate_key(data_type, {"key": key})
            
            success = True
            
            if self.memory_cache:
                success &= self.memory_cache.delete(full_key, data_type)
            
            if self.redis_cache:
                success &= self.redis_cache.delete(full_key, data_type)
            
            return success
            
        except Exception as e:
            logger.error(f"删除缓存失败: {key}, 错误: {e}")
            self.metrics.record_error(data_type)
            return False
    
    def exists(self, key: str, data_type: str = "default") -> bool:
        """检查缓存项是否存在
        
        Args:
            key: 缓存键
            data_type: 数据类型
            
        Returns:
            bool: 是否存在
        """
        try:
            full_key = self.strategy.generate_key(data_type, {"key": key})
            
            if self.cache_type == CacheType.MEMORY and self.memory_cache:
                return self.memory_cache.exists(full_key)
            
            elif self.cache_type == CacheType.REDIS and self.redis_cache:
                return self.redis_cache.exists(full_key)
            
            elif self.cache_type == CacheType.HYBRID:
                # 任一缓存存在即返回True
                if self.memory_cache and self.memory_cache.exists(full_key):
                    return True
                if self.redis_cache and self.redis_cache.exists(full_key):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"检查缓存存在性失败: {key}, 错误: {e}")
            return False
    
    def clear(self, data_type: str = None):
        """清空缓存
        
        Args:
            data_type: 数据类型，None表示清空所有
        """
        try:
            if self.memory_cache:
                self.memory_cache.clear(data_type)
            
            if self.redis_cache:
                self.redis_cache.clear(data_type)
            
            logger.info(f"缓存清空完成，类型: {data_type or '全部'}")
            
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
    
    def _get_from_memory(self, key: str, data_type: str) -> Optional[Any]:
        """从内存缓存获取"""
        if not self.memory_cache:
            return None
        return self.memory_cache.get(key, data_type)
    
    def _get_from_redis(self, key: str, data_type: str) -> Optional[Any]:
        """从Redis缓存获取"""
        if not self.redis_cache:
            return None
        return self.redis_cache.get(key, data_type)
    
    def _get_hybrid(self, key: str, data_type: str) -> Optional[Any]:
        """混合模式获取"""
        # 先从内存缓存获取
        if self.memory_cache:
            value = self.memory_cache.get(key, data_type)
            if value is not None:
                return value
        
        # 内存缓存未命中，从Redis获取
        if self.redis_cache:
            value = self.redis_cache.get(key, data_type)
            if value is not None:
                # 异步回写到内存缓存
                if self.memory_cache:
                    ttl = self.strategy.get_ttl(data_type)
                    self.executor.submit(
                        self.memory_cache.set, key, value, ttl, data_type
                    )
                return value
        
        return None
    
    def _set_to_memory(self, key: str, value: Any, ttl: int, data_type: str) -> bool:
        """设置到内存缓存"""
        if not self.memory_cache:
            return False
        return self.memory_cache.set(key, value, ttl, data_type)
    
    def _set_to_redis(self, key: str, value: Any, ttl: int, data_type: str) -> bool:
        """设置到Redis缓存"""
        if not self.redis_cache:
            return False
        return self.redis_cache.set(key, value, ttl, data_type)
    
    def _set_hybrid(self, key: str, value: Any, ttl: int, data_type: str) -> bool:
        """混合模式设置"""
        success = True
        
        # 同时设置到内存和Redis
        futures = []
        
        if self.memory_cache:
            future = self.executor.submit(
                self.memory_cache.set, key, value, ttl, data_type
            )
            futures.append(future)
        
        if self.redis_cache:
            future = self.executor.submit(
                self.redis_cache.set, key, value, ttl, data_type
            )
            futures.append(future)
        
        # 等待所有操作完成
        for future in as_completed(futures, timeout=5):
            try:
                result = future.result()
                success &= result
            except Exception as e:
                logger.error(f"混合缓存设置失败: {e}")
                success = False
        
        return success
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息
        
        Returns:
            Dict: 统计信息
        """
        stats = {
            "manager": {
                "cache_type": self.cache_type.value,
                "strategy_count": len(self.strategy.STRATEGIES) + len(self.strategy.custom_strategies)
            }
        }
        
        if self.memory_cache:
            stats["memory"] = self.memory_cache.get_stats()
        
        if self.redis_cache:
            stats["redis"] = self.redis_cache.get_stats()
        
        # 合并指标
        combined_metrics = CacheMetrics()
        if self.memory_cache:
            mem_stats = self.memory_cache.get_stats()["total"]
            combined_metrics.hits += mem_stats["hits"]
            combined_metrics.misses += mem_stats["misses"]
            combined_metrics.sets += mem_stats["sets"]
            combined_metrics.deletes += mem_stats["deletes"]
            combined_metrics.evictions += mem_stats["evictions"]
            combined_metrics.errors += mem_stats["errors"]
        
        if self.redis_cache:
            redis_stats = self.redis_cache.get_stats()["total"]
            combined_metrics.hits += redis_stats["hits"]
            combined_metrics.misses += redis_stats["misses"]
            combined_metrics.sets += redis_stats["sets"]
            combined_metrics.deletes += redis_stats["deletes"]
            combined_metrics.evictions += redis_stats["evictions"]
            combined_metrics.errors += redis_stats["errors"]
        
        stats["combined"] = combined_metrics.get_stats()["total"]
        
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查
        
        Returns:
            Dict: 健康状态
        """
        health = {
            "overall": "healthy",
            "components": {}
        }
        
        # 检查内存缓存
        if self.memory_cache:
            try:
                # 简单的读写测试
                test_key = "health_check_memory"
                self.memory_cache.set(test_key, "test", 10)
                result = self.memory_cache.get(test_key)
                self.memory_cache.delete(test_key)
                
                health["components"]["memory"] = {
                    "status": "healthy" if result == "test" else "unhealthy",
                    "message": "内存缓存正常" if result == "test" else "内存缓存异常"
                }
            except Exception as e:
                health["components"]["memory"] = {
                    "status": "unhealthy",
                    "message": f"内存缓存错误: {e}"
                }
                health["overall"] = "degraded"
        
        # 检查Redis缓存
        if self.redis_cache:
            try:
                if self.redis_cache.ping():
                    # 简单的读写测试
                    test_key = "health_check_redis"
                    self.redis_cache.set(test_key, "test", 10)
                    result = self.redis_cache.get(test_key)
                    self.redis_cache.delete(test_key)
                    
                    health["components"]["redis"] = {
                        "status": "healthy" if result == "test" else "unhealthy",
                        "message": "Redis缓存正常" if result == "test" else "Redis缓存异常"
                    }
                else:
                    health["components"]["redis"] = {
                        "status": "unhealthy",
                        "message": "Redis连接失败"
                    }
                    health["overall"] = "degraded"
            except Exception as e:
                health["components"]["redis"] = {
                    "status": "unhealthy",
                    "message": f"Redis缓存错误: {e}"
                }
                health["overall"] = "degraded"
        
        # 检查整体状态
        unhealthy_count = sum(1 for comp in health["components"].values() 
                             if comp["status"] == "unhealthy")
        
        if unhealthy_count == len(health["components"]):
            health["overall"] = "unhealthy"
        elif unhealthy_count > 0:
            health["overall"] = "degraded"
        
        return health
    
    def close(self):
        """关闭缓存管理器"""
        try:
            # 关闭线程池
            self.executor.shutdown(wait=True)
            
            # 关闭缓存后端
            if self.memory_cache:
                self.memory_cache.stop()
            
            if self.redis_cache:
                self.redis_cache.close()
            
            logger.info("缓存管理器已关闭")
            
        except Exception as e:
            logger.error(f"关闭缓存管理器失败: {e}")


# 便捷函数
def create_cache_manager(cache_type: str = "memory", **kwargs) -> CacheManager:
    """创建缓存管理器的便捷函数
    
    Args:
        cache_type: 缓存类型 ("memory", "redis", "hybrid")
        **kwargs: 其他配置参数
        
    Returns:
        CacheManager: 缓存管理器实例
    """
    config = CacheConfig(
        cache_type=CacheType(cache_type),
        **kwargs
    )
    return CacheManager(config)