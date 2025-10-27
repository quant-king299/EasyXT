"""
内存缓存实现

基于Python字典的高性能内存缓存，支持LRU、LFU等淘汰策略。
"""

import time
import threading
from typing import Any, Dict, Optional, List, Tuple
from collections import OrderedDict
from dataclasses import dataclass
import heapq
import json
import gzip
import logging

from .cache_strategy import CacheConfig, EvictionPolicy, CacheMetrics

logger = logging.getLogger(__name__)


@dataclass
class CacheItem:
    """缓存项"""
    key: str
    value: Any
    created_time: float
    last_access_time: float
    access_count: int
    ttl: int
    compressed: bool = False
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl <= 0:
            return False
        return time.time() - self.created_time > self.ttl
    
    def touch(self):
        """更新访问时间和次数"""
        self.last_access_time = time.time()
        self.access_count += 1


class LRUCache:
    """LRU缓存实现"""
    
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.cache = OrderedDict()
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[CacheItem]:
        """获取缓存项"""
        with self.lock:
            if key in self.cache:
                # 移动到末尾（最近使用）
                item = self.cache.pop(key)
                self.cache[key] = item
                return item
            return None
    
    def set(self, key: str, item: CacheItem):
        """设置缓存项"""
        with self.lock:
            if key in self.cache:
                # 更新现有项
                self.cache.pop(key)
            elif len(self.cache) >= self.max_size:
                # 删除最久未使用的项
                self.cache.popitem(last=False)
            
            self.cache[key] = item
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self.lock:
            return self.cache.pop(key, None) is not None
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
    
    def keys(self) -> List[str]:
        """获取所有键"""
        with self.lock:
            return list(self.cache.keys())
    
    def size(self) -> int:
        """获取缓存大小"""
        return len(self.cache)


class LFUCache:
    """LFU缓存实现"""
    
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.cache = {}
        self.frequencies = {}
        self.freq_to_keys = {}
        self.min_freq = 0
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[CacheItem]:
        """获取缓存项"""
        with self.lock:
            if key not in self.cache:
                return None
            
            item = self.cache[key]
            self._update_freq(key)
            return item
    
    def set(self, key: str, item: CacheItem):
        """设置缓存项"""
        with self.lock:
            if key in self.cache:
                self.cache[key] = item
                self._update_freq(key)
                return
            
            if len(self.cache) >= self.max_size:
                self._evict()
            
            self.cache[key] = item
            self.frequencies[key] = 1
            if 1 not in self.freq_to_keys:
                self.freq_to_keys[1] = set()
            self.freq_to_keys[1].add(key)
            self.min_freq = 1
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self.lock:
            if key not in self.cache:
                return False
            
            freq = self.frequencies[key]
            self.freq_to_keys[freq].remove(key)
            if not self.freq_to_keys[freq] and freq == self.min_freq:
                self.min_freq += 1
            
            del self.cache[key]
            del self.frequencies[key]
            return True
    
    def _update_freq(self, key: str):
        """更新访问频率"""
        freq = self.frequencies[key]
        self.freq_to_keys[freq].remove(key)
        
        if not self.freq_to_keys[freq] and freq == self.min_freq:
            self.min_freq += 1
        
        new_freq = freq + 1
        self.frequencies[key] = new_freq
        if new_freq not in self.freq_to_keys:
            self.freq_to_keys[new_freq] = set()
        self.freq_to_keys[new_freq].add(key)
    
    def _evict(self):
        """淘汰最少使用的项"""
        key_to_remove = self.freq_to_keys[self.min_freq].pop()
        del self.cache[key_to_remove]
        del self.frequencies[key_to_remove]
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.frequencies.clear()
            self.freq_to_keys.clear()
            self.min_freq = 0
    
    def keys(self) -> List[str]:
        """获取所有键"""
        with self.lock:
            return list(self.cache.keys())
    
    def size(self) -> int:
        """获取缓存大小"""
        return len(self.cache)


class FIFOCache:
    """FIFO缓存实现"""
    
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.cache = {}
        self.insertion_order = []
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[CacheItem]:
        """获取缓存项"""
        with self.lock:
            return self.cache.get(key)
    
    def set(self, key: str, item: CacheItem):
        """设置缓存项"""
        with self.lock:
            if key in self.cache:
                self.cache[key] = item
                return
            
            if len(self.cache) >= self.max_size:
                # 删除最先插入的项
                oldest_key = self.insertion_order.pop(0)
                del self.cache[oldest_key]
            
            self.cache[key] = item
            self.insertion_order.append(key)
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                self.insertion_order.remove(key)
                return True
            return False
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.insertion_order.clear()
    
    def keys(self) -> List[str]:
        """获取所有键"""
        with self.lock:
            return list(self.cache.keys())
    
    def size(self) -> int:
        """获取缓存大小"""
        return len(self.cache)


class MemoryCache:
    """内存缓存管理器"""
    
    def __init__(self, config: CacheConfig):
        """初始化内存缓存
        
        Args:
            config: 缓存配置
        """
        self.config = config
        self.metrics = CacheMetrics()
        
        # 根据淘汰策略选择缓存实现
        if config.eviction_policy == EvictionPolicy.LRU:
            self.cache = LRUCache(config.max_size)
        elif config.eviction_policy == EvictionPolicy.LFU:
            self.cache = LFUCache(config.max_size)
        elif config.eviction_policy == EvictionPolicy.FIFO:
            self.cache = FIFOCache(config.max_size)
        else:
            self.cache = LRUCache(config.max_size)  # 默认LRU
        
        # 启动清理线程
        self.cleanup_thread = None
        self.running = False
        if config.default_ttl > 0:
            self._start_cleanup_thread()
        
        logger.info(f"内存缓存初始化完成，策略: {config.eviction_policy.value}, 大小: {config.max_size}")
    
    def get(self, key: str, data_type: str = None) -> Optional[Any]:
        """获取缓存值
        
        Args:
            key: 缓存键
            data_type: 数据类型（用于统计）
            
        Returns:
            Any: 缓存值，不存在返回None
        """
        try:
            item = self.cache.get(key)
            
            if item is None:
                self.metrics.record_miss(data_type)
                return None
            
            # 检查是否过期
            if item.is_expired():
                self.cache.delete(key)
                self.metrics.record_miss(data_type)
                return None
            
            # 更新访问信息
            item.touch()
            self.metrics.record_hit(data_type)
            
            # 解压缩数据
            if item.compressed:
                return self._decompress(item.value)
            
            return item.value
            
        except Exception as e:
            logger.error(f"获取缓存失败: {key}, 错误: {e}")
            self.metrics.record_error(data_type)
            return None
    
    def set(self, key: str, value: Any, ttl: int = None, data_type: str = None) -> bool:
        """设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None使用默认值
            data_type: 数据类型（用于统计）
            
        Returns:
            bool: 是否设置成功
        """
        try:
            if ttl is None:
                ttl = self.config.default_ttl
            
            # 序列化和压缩
            serialized_value = self._serialize(value)
            compressed = False
            
            if (self.config.enable_compression and 
                len(serialized_value) > self.config.compression_threshold):
                serialized_value = self._compress(serialized_value)
                compressed = True
            
            # 创建缓存项
            item = CacheItem(
                key=key,
                value=serialized_value,
                created_time=time.time(),
                last_access_time=time.time(),
                access_count=0,
                ttl=ttl,
                compressed=compressed
            )
            
            self.cache.set(key, item)
            self.metrics.record_set(data_type)
            
            return True
            
        except Exception as e:
            logger.error(f"设置缓存失败: {key}, 错误: {e}")
            self.metrics.record_error(data_type)
            return False
    
    def delete(self, key: str, data_type: str = None) -> bool:
        """删除缓存项
        
        Args:
            key: 缓存键
            data_type: 数据类型（用于统计）
            
        Returns:
            bool: 是否删除成功
        """
        try:
            success = self.cache.delete(key)
            if success:
                self.metrics.record_delete(data_type)
            return success
            
        except Exception as e:
            logger.error(f"删除缓存失败: {key}, 错误: {e}")
            self.metrics.record_error(data_type)
            return False
    
    def exists(self, key: str) -> bool:
        """检查缓存项是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 是否存在
        """
        item = self.cache.get(key)
        if item is None:
            return False
        
        if item.is_expired():
            self.cache.delete(key)
            return False
        
        return True
    
    def clear(self, data_type: str = None):
        """清空缓存
        
        Args:
            data_type: 数据类型，None表示清空所有
        """
        if data_type is None:
            self.cache.clear()
        else:
            # 清空特定类型的缓存
            keys_to_delete = []
            for key in self.cache.keys():
                if key.startswith(f"easyxt:{data_type}:"):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                self.cache.delete(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息
        
        Returns:
            Dict: 统计信息
        """
        stats = self.metrics.get_stats()
        stats["cache_info"] = {
            "type": "memory",
            "eviction_policy": self.config.eviction_policy.value,
            "max_size": self.config.max_size,
            "current_size": self.cache.size(),
            "default_ttl": self.config.default_ttl,
            "compression_enabled": self.config.enable_compression
        }
        return stats
    
    def _serialize(self, value: Any) -> bytes:
        """序列化值"""
        return json.dumps(value, ensure_ascii=False).encode('utf-8')
    
    def _compress(self, data: bytes) -> bytes:
        """压缩数据"""
        return gzip.compress(data)
    
    def _decompress(self, data: bytes) -> Any:
        """解压缩数据"""
        decompressed = gzip.decompress(data)
        return json.loads(decompressed.decode('utf-8'))
    
    def _start_cleanup_thread(self):
        """启动清理线程"""
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_expired, daemon=True)
        self.cleanup_thread.start()
    
    def _cleanup_expired(self):
        """清理过期项"""
        while self.running:
            try:
                expired_keys = []
                
                for key in self.cache.keys():
                    item = self.cache.get(key)
                    if item and item.is_expired():
                        expired_keys.append(key)
                
                for key in expired_keys:
                    self.cache.delete(key)
                    self.metrics.record_eviction()
                
                if expired_keys:
                    logger.debug(f"清理过期缓存项: {len(expired_keys)}个")
                
                # 每30秒清理一次
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"清理过期缓存失败: {e}")
                time.sleep(30)
    
    def stop(self):
        """停止缓存服务"""
        self.running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        logger.info("内存缓存服务已停止")