"""
Redis缓存实现

基于Redis的分布式缓存，支持集群部署和数据持久化。
"""

import json
import time
import gzip
import logging
from typing import Any, Dict, Optional, List
try:
    import redis
    from redis.exceptions import ConnectionError, TimeoutError, RedisError
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    ConnectionError = Exception
    TimeoutError = Exception
    RedisError = Exception
    REDIS_AVAILABLE = False

from .cache_strategy import CacheConfig, CacheMetrics

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis缓存管理器"""
    
    def __init__(self, config: CacheConfig):
        """初始化Redis缓存
        
        Args:
            config: 缓存配置
        """
        if not REDIS_AVAILABLE:
            raise ImportError("Redis库未安装，请运行: pip install redis")
            
        self.config = config
        self.metrics = CacheMetrics()
        
        # Redis连接配置
        self.redis_config = {
            'host': config.redis_host,
            'port': config.redis_port,
            'db': config.redis_db,
            'decode_responses': False,  # 处理二进制数据
            'socket_timeout': 5,
            'socket_connect_timeout': 5,
            'retry_on_timeout': True,
            'health_check_interval': 30
        }
        
        if config.redis_password:
            self.redis_config['password'] = config.redis_password
        
        # 连接池
        self.pool = None
        self.client = None
        self._connect()
        
        logger.info(f"Redis缓存初始化完成，服务器: {config.redis_host}:{config.redis_port}")
    
    def _connect(self) -> bool:
        """连接Redis服务器
        
        Returns:
            bool: 是否连接成功
        """
        try:
            # 创建连接池
            self.pool = redis.ConnectionPool(**self.redis_config)
            self.client = redis.Redis(connection_pool=self.pool)
            
            # 测试连接
            self.client.ping()
            logger.info("Redis连接成功")
            return True
            
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            self.client = None
            return False
    
    def _ensure_connected(self) -> bool:
        """确保Redis连接可用
        
        Returns:
            bool: 连接是否可用
        """
        if self.client is None:
            return self._connect()
        
        try:
            self.client.ping()
            return True
        except (ConnectionError, TimeoutError):
            logger.warning("Redis连接断开，尝试重连...")
            return self._connect()
        except Exception as e:
            logger.error(f"Redis连接检查失败: {e}")
            return False
    
    def get(self, key: str, data_type: str = None) -> Optional[Any]:
        """获取缓存值
        
        Args:
            key: 缓存键
            data_type: 数据类型（用于统计）
            
        Returns:
            Any: 缓存值，不存在返回None
        """
        if not self._ensure_connected():
            self.metrics.record_error(data_type)
            return None
        
        try:
            # 获取数据和元数据
            pipe = self.client.pipeline()
            pipe.hget(key, 'data')
            pipe.hget(key, 'compressed')
            pipe.hget(key, 'created_time')
            pipe.hget(key, 'ttl')
            pipe.hincrby(key, 'access_count', 1)
            pipe.hset(key, 'last_access_time', time.time())
            
            results = pipe.execute()
            data, compressed, created_time, ttl = results[:4]
            
            if data is None:
                self.metrics.record_miss(data_type)
                return None
            
            # 检查是否过期
            if created_time and ttl:
                created_time = float(created_time)
                ttl = int(ttl)
                if ttl > 0 and time.time() - created_time > ttl:
                    self.delete(key, data_type)
                    self.metrics.record_miss(data_type)
                    return None
            
            # 解压缩和反序列化
            if compressed and compressed == b'1':
                data = gzip.decompress(data)
            
            value = json.loads(data.decode('utf-8'))
            self.metrics.record_hit(data_type)
            
            return value
            
        except Exception as e:
            logger.error(f"Redis获取缓存失败: {key}, 错误: {e}")
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
        if not self._ensure_connected():
            self.metrics.record_error(data_type)
            return False
        
        try:
            if ttl is None:
                ttl = self.config.default_ttl
            
            # 序列化
            serialized_data = json.dumps(value, ensure_ascii=False).encode('utf-8')
            compressed = False
            
            # 压缩
            if (self.config.enable_compression and 
                len(serialized_data) > self.config.compression_threshold):
                serialized_data = gzip.compress(serialized_data)
                compressed = True
            
            # 存储数据和元数据
            current_time = time.time()
            cache_data = {
                'data': serialized_data,
                'compressed': '1' if compressed else '0',
                'created_time': current_time,
                'last_access_time': current_time,
                'access_count': 0,
                'ttl': ttl
            }
            
            # 使用管道提高性能
            pipe = self.client.pipeline()
            pipe.hset(key, mapping=cache_data)
            
            # 设置Redis TTL（比缓存TTL稍长，避免数据丢失）
            if ttl > 0:
                redis_ttl = ttl + 60  # 多给60秒缓冲
                pipe.expire(key, redis_ttl)
            
            pipe.execute()
            self.metrics.record_set(data_type)
            
            return True
            
        except Exception as e:
            logger.error(f"Redis设置缓存失败: {key}, 错误: {e}")
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
        if not self._ensure_connected():
            self.metrics.record_error(data_type)
            return False
        
        try:
            result = self.client.delete(key)
            if result > 0:
                self.metrics.record_delete(data_type)
                return True
            return False
            
        except Exception as e:
            logger.error(f"Redis删除缓存失败: {key}, 错误: {e}")
            self.metrics.record_error(data_type)
            return False
    
    def exists(self, key: str) -> bool:
        """检查缓存项是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 是否存在
        """
        if not self._ensure_connected():
            return False
        
        try:
            # 检查键是否存在
            if not self.client.exists(key):
                return False
            
            # 检查是否过期
            created_time = self.client.hget(key, 'created_time')
            ttl = self.client.hget(key, 'ttl')
            
            if created_time and ttl:
                created_time = float(created_time)
                ttl = int(ttl)
                if ttl > 0 and time.time() - created_time > ttl:
                    self.client.delete(key)
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Redis检查缓存存在性失败: {key}, 错误: {e}")
            return False
    
    def clear(self, data_type: str = None):
        """清空缓存
        
        Args:
            data_type: 数据类型，None表示清空所有
        """
        if not self._ensure_connected():
            return
        
        try:
            if data_type is None:
                # 清空当前数据库
                self.client.flushdb()
            else:
                # 清空特定类型的缓存
                pattern = f"easyxt:{data_type}:*"
                keys = self.client.keys(pattern)
                if keys:
                    self.client.delete(*keys)
                    logger.info(f"清空Redis缓存类型 {data_type}: {len(keys)}个键")
            
        except Exception as e:
            logger.error(f"Redis清空缓存失败: {e}")
    
    def get_keys(self, pattern: str = "*") -> List[str]:
        """获取匹配模式的键列表
        
        Args:
            pattern: 匹配模式
            
        Returns:
            List[str]: 键列表
        """
        if not self._ensure_connected():
            return []
        
        try:
            keys = self.client.keys(pattern)
            return [key.decode('utf-8') if isinstance(key, bytes) else key for key in keys]
        except Exception as e:
            logger.error(f"Redis获取键列表失败: {e}")
            return []
    
    def get_info(self) -> Dict[str, Any]:
        """获取Redis服务器信息
        
        Returns:
            Dict: 服务器信息
        """
        if not self._ensure_connected():
            return {}
        
        try:
            info = self.client.info()
            return {
                'redis_version': info.get('redis_version'),
                'used_memory': info.get('used_memory'),
                'used_memory_human': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'total_commands_processed': info.get('total_commands_processed'),
                'keyspace_hits': info.get('keyspace_hits'),
                'keyspace_misses': info.get('keyspace_misses'),
                'uptime_in_seconds': info.get('uptime_in_seconds')
            }
        except Exception as e:
            logger.error(f"获取Redis信息失败: {e}")
            return {}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息
        
        Returns:
            Dict: 统计信息
        """
        stats = self.metrics.get_stats()
        
        # 添加Redis特定信息
        redis_info = self.get_info()
        stats["cache_info"] = {
            "type": "redis",
            "host": self.config.redis_host,
            "port": self.config.redis_port,
            "db": self.config.redis_db,
            "default_ttl": self.config.default_ttl,
            "compression_enabled": self.config.enable_compression,
            "connected": self._ensure_connected(),
            "redis_info": redis_info
        }
        
        return stats
    
    def ping(self) -> bool:
        """测试Redis连接
        
        Returns:
            bool: 连接是否正常
        """
        return self._ensure_connected()
    
    def close(self):
        """关闭Redis连接"""
        try:
            if self.client:
                self.client.close()
            if self.pool:
                self.pool.disconnect()
            logger.info("Redis连接已关闭")
        except Exception as e:
            logger.error(f"关闭Redis连接失败: {e}")


class RedisClusterCache(RedisCache):
    """Redis集群缓存实现"""
    
    def __init__(self, config: CacheConfig, cluster_nodes: List[Dict[str, Any]]):
        """初始化Redis集群缓存
        
        Args:
            config: 缓存配置
            cluster_nodes: 集群节点列表 [{'host': 'host1', 'port': 6379}, ...]
        """
        self.cluster_nodes = cluster_nodes
        super().__init__(config)
    
    def _connect(self) -> bool:
        """连接Redis集群
        
        Returns:
            bool: 是否连接成功
        """
        try:
            from rediscluster import RedisCluster
            
            startup_nodes = self.cluster_nodes
            self.client = RedisCluster(
                startup_nodes=startup_nodes,
                decode_responses=False,
                skip_full_coverage_check=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            # 测试连接
            self.client.ping()
            logger.info(f"Redis集群连接成功，节点数: {len(startup_nodes)}")
            return True
            
        except ImportError:
            logger.error("redis-py-cluster库未安装，无法使用集群模式")
            return False
        except Exception as e:
            logger.error(f"Redis集群连接失败: {e}")
            self.client = None
            return False