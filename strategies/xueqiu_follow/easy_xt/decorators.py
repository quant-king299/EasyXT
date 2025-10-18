"""
EasyXT装饰器模块
提供API调用的装饰器功能，包括重试、缓存、日志等
"""
import time
import functools
from typing import Any, Callable, Optional, Dict, Union
from datetime import datetime, timedelta
import logging
from .types import EasyXTError, ConnectionError, TradeError, DataError
from .validators import ValidationError

# 配置日志
logger = logging.getLogger('easy_xt')

class RetryConfig:
    """重试配置"""
    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        exceptions: tuple = (ConnectionError, DataError)
    ):
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.exceptions = exceptions

class CacheConfig:
    """缓存配置"""
    def __init__(
        self,
        ttl: int = 300,  # 缓存时间（秒）
        max_size: int = 1000,  # 最大缓存条目
        key_func: Optional[Callable] = None  # 自定义键函数
    ):
        self.ttl = ttl
        self.max_size = max_size
        self.key_func = key_func

# 简单的内存缓存实现
class SimpleCache:
    """简单缓存实现"""
    
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
    
    def get(self, key: str, ttl: int = 300) -> Optional[Any]:
        """获取缓存值"""
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if datetime.now() > entry['expires']:
            del self.cache[key]
            return None
        
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """设置缓存值"""
        # 如果缓存已满，删除最旧的条目
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k]['created'])
            del self.cache[oldest_key]
        
        self.cache[key] = {
            'value': value,
            'created': datetime.now(),
            'expires': datetime.now() + timedelta(seconds=ttl)
        }
    
    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()

# 全局缓存实例
_cache = SimpleCache()

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    exceptions: tuple = (ConnectionError, DataError),
    on_retry: Optional[Callable] = None
):
    """
    重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff_factor: 退避因子
        max_delay: 最大延迟时间（秒）
        exceptions: 需要重试的异常类型
        on_retry: 重试时的回调函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        # 最后一次尝试失败
                        logger.error(f"函数 {func.__name__} 重试 {max_attempts} 次后仍然失败: {e}")
                        raise
                    
                    # 执行重试回调
                    if on_retry:
                        on_retry(attempt + 1, e)
                    
                    logger.warning(f"函数 {func.__name__} 第 {attempt + 1} 次调用失败，{current_delay}秒后重试: {e}")
                    time.sleep(current_delay)
                    
                    # 计算下次延迟时间
                    current_delay = min(current_delay * backoff_factor, max_delay)
                except Exception as e:
                    # 不在重试范围内的异常直接抛出
                    logger.error(f"函数 {func.__name__} 发生不可重试的异常: {e}")
                    raise
            
            # 理论上不会到达这里
            raise last_exception
        
        return wrapper
    return decorator

def cache(
    ttl: int = 300,
    max_size: int = 1000,
    key_func: Optional[Callable] = None,
    cache_instance: Optional[SimpleCache] = None
):
    """
    缓存装饰器
    
    Args:
        ttl: 缓存时间（秒）
        max_size: 最大缓存条目
        key_func: 自定义键生成函数
        cache_instance: 自定义缓存实例
    """
    def decorator(func: Callable) -> Callable:
        cache_obj = cache_instance or _cache
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # 尝试从缓存获取
            cached_result = cache_obj.get(cache_key, ttl)
            if cached_result is not None:
                logger.debug(f"缓存命中: {func.__name__}")
                return cached_result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache_obj.set(cache_key, result, ttl)
            logger.debug(f"缓存设置: {func.__name__}")
            
            return result
        
        return wrapper
    return decorator

def log_calls(
    level: int = logging.INFO,
    include_args: bool = True,
    include_result: bool = False,
    max_arg_length: int = 100
):
    """
    日志记录装饰器
    
    Args:
        level: 日志级别
        include_args: 是否包含参数
        include_result: 是否包含返回值
        max_arg_length: 参数最大长度
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # 记录函数调用开始
            if include_args:
                args_str = str(args)[:max_arg_length]
                kwargs_str = str(kwargs)[:max_arg_length]
                logger.log(level, f"调用 {func.__name__}(args={args_str}, kwargs={kwargs_str})")
            else:
                logger.log(level, f"调用 {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                
                # 记录函数调用成功
                elapsed = time.time() - start_time
                if include_result:
                    result_str = str(result)[:max_arg_length]
                    logger.log(level, f"{func.__name__} 成功完成 ({elapsed:.3f}s), 结果: {result_str}")
                else:
                    logger.log(level, f"{func.__name__} 成功完成 ({elapsed:.3f}s)")
                
                return result
                
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"{func.__name__} 执行失败 ({elapsed:.3f}s): {e}")
                raise
        
        return wrapper
    return decorator

def validate_params(**validators):
    """
    参数验证装饰器
    
    Args:
        **validators: 参数名到验证函数的映射
    
    Example:
        @validate_params(
            code=StockCodeValidator.validate,
            volume=TradeValidator.validate_volume
        )
        def buy(code, volume):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 获取函数签名
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # 验证参数
            for param_name, validator in validators.items():
                if param_name in bound_args.arguments:
                    try:
                        validated_value = validator(bound_args.arguments[param_name])
                        bound_args.arguments[param_name] = validated_value
                    except Exception as e:
                        raise ValidationError(f"参数 {param_name} 验证失败: {e}")
            
            return func(*bound_args.args, **bound_args.kwargs)
        
        return wrapper
    return decorator

def rate_limit(calls_per_second: float = 10.0):
    """
    限流装饰器
    
    Args:
        calls_per_second: 每秒允许的调用次数
    """
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            
            last_called[0] = time.time()
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

def api_method(
    retry_config: Optional[RetryConfig] = None,
    cache_config: Optional[CacheConfig] = None,
    log_level: int = logging.INFO,
    rate_limit_rps: Optional[float] = None,
    validators: Optional[Dict[str, Callable]] = None
):
    """
    API方法组合装饰器
    
    Args:
        retry_config: 重试配置
        cache_config: 缓存配置
        log_level: 日志级别
        rate_limit_rps: 限流配置（每秒请求数）
        validators: 参数验证器
    """
    def decorator(func: Callable) -> Callable:
        # 应用装饰器（注意顺序）
        decorated_func = func
        
        # 1. 参数验证（最内层）
        if validators:
            decorated_func = validate_params(**validators)(decorated_func)
        
        # 2. 限流控制
        if rate_limit_rps:
            decorated_func = rate_limit(rate_limit_rps)(decorated_func)
        
        # 3. 缓存
        if cache_config:
            decorated_func = cache(
                ttl=cache_config.ttl,
                max_size=cache_config.max_size,
                key_func=cache_config.key_func
            )(decorated_func)
        
        # 4. 重试机制
        if retry_config:
            decorated_func = retry(
                max_attempts=retry_config.max_attempts,
                delay=retry_config.delay,
                backoff_factor=retry_config.backoff_factor,
                max_delay=retry_config.max_delay,
                exceptions=retry_config.exceptions
            )(decorated_func)
        
        # 5. 日志记录（最外层）
        decorated_func = log_calls(level=log_level)(decorated_func)
        
        return decorated_func
    
    return decorator

# ==================== 预定义装饰器配置 ====================

# 数据API装饰器
data_api = api_method(
    retry_config=RetryConfig(
        max_attempts=3,
        delay=1.0,
        exceptions=(ConnectionError, DataError)
    ),
    cache_config=CacheConfig(ttl=60),
    log_level=logging.INFO
)

# 交易API装饰器
trade_api = api_method(
    retry_config=RetryConfig(
        max_attempts=2,
        delay=0.5,
        exceptions=(ConnectionError,)
    ),
    log_level=logging.WARNING,
    rate_limit_rps=5.0
)

# 查询API装饰器
query_api = api_method(
    cache_config=CacheConfig(ttl=30),
    log_level=logging.DEBUG
)