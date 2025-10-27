"""
错误处理和恢复机制模块
实现全面的错误处理、异常恢复和系统容错功能
"""

import logging
import traceback
import time
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Union, Type
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import json
import uuid


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """错误类别"""
    NETWORK = "network"
    DATABASE = "database"
    API = "api"
    SYSTEM = "system"
    DATA = "data"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """恢复策略"""
    RETRY = "retry"
    FALLBACK = "fallback"
    CIRCUIT_BREAKER = "circuit_breaker"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    RESTART = "restart"
    IGNORE = "ignore"
    ESCALATE = "escalate"


@dataclass
class ErrorInfo:
    """错误信息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    exception_type: str = ""
    message: str = ""
    traceback: str = ""
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    category: ErrorCategory = ErrorCategory.UNKNOWN
    context: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3


@dataclass
class RecoveryAction:
    """恢复动作"""
    name: str
    strategy: RecoveryStrategy
    condition: Callable[[ErrorInfo], bool]
    action: Callable[[ErrorInfo], Any]
    max_attempts: int = 3
    delay: float = 1.0
    backoff_multiplier: float = 2.0
    enabled: bool = True


class CircuitBreakerState(Enum):
    """断路器状态"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """断路器"""
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 3
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    next_attempt_time: Optional[datetime] = None


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.errors: List[ErrorInfo] = []
        self.recovery_actions: List[RecoveryAction] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_callbacks: List[Callable[[ErrorInfo], None]] = []
        self.recovery_callbacks: List[Callable[[ErrorInfo, Any], None]] = []
        self.config = self._load_config(config_file)
        self._setup_default_recovery_actions()
        self._lock = threading.Lock()
    
    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """加载配置"""
        default_config = {
            "max_error_history": 1000,
            "auto_cleanup_hours": 24,
            "default_retry_attempts": 3,
            "default_retry_delay": 1.0,
            "circuit_breaker_enabled": True,
            "error_reporting_enabled": True,
            "recovery_logging_enabled": True
        }
        
        if config_file:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                self.logger.warning(f"无法加载配置文件 {config_file}: {e}")
        
        return default_config
    
    def _setup_default_recovery_actions(self):
        """设置默认恢复动作"""
        # 网络错误重试
        self.add_recovery_action(RecoveryAction(
            name="network_retry",
            strategy=RecoveryStrategy.RETRY,
            condition=lambda error: error.category == ErrorCategory.NETWORK,
            action=self._retry_action,
            max_attempts=3,
            delay=1.0
        ))
        
        # API错误降级
        self.add_recovery_action(RecoveryAction(
            name="api_fallback",
            strategy=RecoveryStrategy.FALLBACK,
            condition=lambda error: error.category == ErrorCategory.API and error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL],
            action=self._fallback_action,
            max_attempts=1
        ))
        
        # 超时错误断路器
        self.add_recovery_action(RecoveryAction(
            name="timeout_circuit_breaker",
            strategy=RecoveryStrategy.CIRCUIT_BREAKER,
            condition=lambda error: error.category == ErrorCategory.TIMEOUT,
            action=self._circuit_breaker_action,
            max_attempts=1
        ))
    
    def handle_error(self, 
                    exception: Exception, 
                    context: Optional[Dict[str, Any]] = None,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    category: ErrorCategory = ErrorCategory.UNKNOWN,
                    source: str = "") -> ErrorInfo:
        """处理错误"""
        error_info = ErrorInfo(
            exception_type=type(exception).__name__,
            message=str(exception),
            traceback=traceback.format_exc(),
            severity=severity,
            category=category,
            context=context or {},
            source=source
        )
        
        with self._lock:
            self.errors.append(error_info)
            self._cleanup_old_errors()
        
        # 记录错误
        self._log_error(error_info)
        
        # 通知回调
        self._notify_error_callbacks(error_info)
        
        # 尝试恢复
        self._attempt_recovery(error_info)
        
        return error_info
    
    def _log_error(self, error_info: ErrorInfo):
        """记录错误日志"""
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error_info.severity, logging.ERROR)
        
        self.logger.log(
            log_level,
            f"错误处理 [{error_info.id}]: {error_info.exception_type} - {error_info.message}"
        )
    
    def _notify_error_callbacks(self, error_info: ErrorInfo):
        """通知错误回调"""
        for callback in self.error_callbacks:
            try:
                callback(error_info)
            except Exception as e:
                self.logger.error(f"错误回调执行失败: {e}")
    
    def _attempt_recovery(self, error_info: ErrorInfo):
        """尝试恢复"""
        for recovery_action in self.recovery_actions:
            if not recovery_action.enabled:
                continue
            
            if recovery_action.condition(error_info):
                try:
                    result = self._execute_recovery_action(recovery_action, error_info)
                    if result:
                        error_info.resolved = True
                        error_info.resolution_time = datetime.now()
                        self._notify_recovery_callbacks(error_info, result)
                        break
                except Exception as e:
                    self.logger.error(f"恢复动作执行失败: {e}")
    
    def _execute_recovery_action(self, recovery_action: RecoveryAction, error_info: ErrorInfo) -> Any:
        """执行恢复动作"""
        max_attempts = min(recovery_action.max_attempts, error_info.max_recovery_attempts)
        delay = recovery_action.delay
        
        for attempt in range(max_attempts):
            error_info.recovery_attempts += 1
            
            try:
                if self.config.get("recovery_logging_enabled", True):
                    self.logger.info(f"执行恢复动作 {recovery_action.name} (尝试 {attempt + 1}/{max_attempts})")
                
                result = recovery_action.action(error_info)
                
                if result:
                    self.logger.info(f"恢复动作 {recovery_action.name} 成功")
                    return result
                
            except Exception as e:
                self.logger.warning(f"恢复动作 {recovery_action.name} 失败 (尝试 {attempt + 1}): {e}")
            
            # 等待重试
            if attempt < max_attempts - 1:
                time.sleep(delay)
                delay *= recovery_action.backoff_multiplier
        
        return None
    
    def _retry_action(self, error_info: ErrorInfo) -> Any:
        """重试动作"""
        # 这是一个基础重试动作，实际使用时应该由调用者提供具体的重试逻辑
        self.logger.info(f"执行重试动作: {error_info.message}")
        return True  # 假设重试成功
    
    def _fallback_action(self, error_info: ErrorInfo) -> Any:
        """降级动作"""
        self.logger.info(f"执行降级动作: {error_info.message}")
        # 实际实现中应该提供降级服务
        return {"fallback": True, "message": "使用降级服务"}
    
    def _circuit_breaker_action(self, error_info: ErrorInfo) -> Any:
        """断路器动作"""
        source = error_info.source or "default"
        circuit_breaker = self.get_or_create_circuit_breaker(source)
        
        if circuit_breaker.state == CircuitBreakerState.OPEN:
            if circuit_breaker.next_attempt_time and datetime.now() >= circuit_breaker.next_attempt_time:
                circuit_breaker.state = CircuitBreakerState.HALF_OPEN
                circuit_breaker.success_count = 0
                self.logger.info(f"断路器 {source} 进入半开状态")
            else:
                self.logger.warning(f"断路器 {source} 处于开启状态，拒绝请求")
                return None
        
        # 记录失败
        circuit_breaker.failure_count += 1
        circuit_breaker.last_failure_time = datetime.now()
        
        if circuit_breaker.failure_count >= circuit_breaker.failure_threshold:
            circuit_breaker.state = CircuitBreakerState.OPEN
            circuit_breaker.next_attempt_time = datetime.now() + timedelta(seconds=circuit_breaker.recovery_timeout)
            self.logger.warning(f"断路器 {source} 开启")
        
        return None
    
    def _notify_recovery_callbacks(self, error_info: ErrorInfo, result: Any):
        """通知恢复回调"""
        for callback in self.recovery_callbacks:
            try:
                callback(error_info, result)
            except Exception as e:
                self.logger.error(f"恢复回调执行失败: {e}")
    
    def add_recovery_action(self, recovery_action: RecoveryAction):
        """添加恢复动作"""
        self.recovery_actions.append(recovery_action)
    
    def remove_recovery_action(self, name: str):
        """移除恢复动作"""
        self.recovery_actions = [action for action in self.recovery_actions if action.name != name]
    
    def add_error_callback(self, callback: Callable[[ErrorInfo], None]):
        """添加错误回调"""
        self.error_callbacks.append(callback)
    
    def add_recovery_callback(self, callback: Callable[[ErrorInfo, Any], None]):
        """添加恢复回调"""
        self.recovery_callbacks.append(callback)
    
    def get_or_create_circuit_breaker(self, name: str) -> CircuitBreaker:
        """获取或创建断路器"""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(name=name)
        return self.circuit_breakers[name]
    
    def record_success(self, source: str):
        """记录成功操作（用于断路器）"""
        if source in self.circuit_breakers:
            circuit_breaker = self.circuit_breakers[source]
            
            if circuit_breaker.state == CircuitBreakerState.HALF_OPEN:
                circuit_breaker.success_count += 1
                if circuit_breaker.success_count >= circuit_breaker.success_threshold:
                    circuit_breaker.state = CircuitBreakerState.CLOSED
                    circuit_breaker.failure_count = 0
                    self.logger.info(f"断路器 {source} 关闭")
            elif circuit_breaker.state == CircuitBreakerState.CLOSED:
                circuit_breaker.failure_count = max(0, circuit_breaker.failure_count - 1)
    
    def get_errors(self, 
                  severity: Optional[ErrorSeverity] = None,
                  category: Optional[ErrorCategory] = None,
                  resolved: Optional[bool] = None,
                  hours: Optional[int] = None) -> List[ErrorInfo]:
        """获取错误列表"""
        with self._lock:
            errors = self.errors.copy()
        
        # 过滤条件
        if severity:
            errors = [e for e in errors if e.severity == severity]
        
        if category:
            errors = [e for e in errors if e.category == category]
        
        if resolved is not None:
            errors = [e for e in errors if e.resolved == resolved]
        
        if hours:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            errors = [e for e in errors if e.timestamp >= cutoff_time]
        
        return errors
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计"""
        with self._lock:
            errors = self.errors.copy()
        
        total_errors = len(errors)
        resolved_errors = len([e for e in errors if e.resolved])
        
        # 按严重程度统计
        severity_stats = {}
        for severity in ErrorSeverity:
            severity_stats[severity.value] = len([e for e in errors if e.severity == severity])
        
        # 按类别统计
        category_stats = {}
        for category in ErrorCategory:
            category_stats[category.value] = len([e for e in errors if e.category == category])
        
        # 最近24小时错误
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_errors = [e for e in errors if e.timestamp >= recent_cutoff]
        
        return {
            "total_errors": total_errors,
            "resolved_errors": resolved_errors,
            "unresolved_errors": total_errors - resolved_errors,
            "resolution_rate": resolved_errors / total_errors if total_errors > 0 else 0,
            "severity_distribution": severity_stats,
            "category_distribution": category_stats,
            "recent_24h_errors": len(recent_errors),
            "circuit_breakers": {name: cb.state.value for name, cb in self.circuit_breakers.items()}
        }
    
    def _cleanup_old_errors(self):
        """清理旧错误"""
        max_errors = self.config.get("max_error_history", 1000)
        cleanup_hours = self.config.get("auto_cleanup_hours", 24)
        
        # 按数量限制
        if len(self.errors) > max_errors:
            self.errors = self.errors[-max_errors:]
        
        # 按时间清理
        cutoff_time = datetime.now() - timedelta(hours=cleanup_hours)
        self.errors = [e for e in self.errors if e.timestamp >= cutoff_time]
    
    def clear_errors(self, resolved_only: bool = True):
        """清理错误"""
        with self._lock:
            if resolved_only:
                self.errors = [e for e in self.errors if not e.resolved]
            else:
                self.errors.clear()
    
    def export_errors(self, filename: str, format: str = "json"):
        """导出错误数据"""
        with self._lock:
            errors_data = []
            for error in self.errors:
                error_dict = {
                    "id": error.id,
                    "timestamp": error.timestamp.isoformat(),
                    "exception_type": error.exception_type,
                    "message": error.message,
                    "severity": error.severity.value,
                    "category": error.category.value,
                    "context": error.context,
                    "source": error.source,
                    "resolved": error.resolved,
                    "resolution_time": error.resolution_time.isoformat() if error.resolution_time else None,
                    "recovery_attempts": error.recovery_attempts
                }
                errors_data.append(error_dict)
        
        if format.lower() == "json":
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(errors_data, f, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"不支持的导出格式: {format}")


# 装饰器函数
def handle_errors(handler: ErrorHandler, 
                 category: ErrorCategory = ErrorCategory.UNKNOWN,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 source: str = ""):
    """错误处理装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_info = handler.handle_error(
                    exception=e,
                    context={"function": func.__name__, "args": str(args), "kwargs": str(kwargs)},
                    category=category,
                    severity=severity,
                    source=source or func.__name__
                )
                # 根据错误严重程度决定是否重新抛出异常
                if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] and not error_info.resolved:
                    raise
                return None
        return wrapper
    return decorator


def handle_async_errors(handler: ErrorHandler,
                       category: ErrorCategory = ErrorCategory.UNKNOWN,
                       severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                       source: str = ""):
    """异步错误处理装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_info = handler.handle_error(
                    exception=e,
                    context={"function": func.__name__, "args": str(args), "kwargs": str(kwargs)},
                    category=category,
                    severity=severity,
                    source=source or func.__name__
                )
                if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] and not error_info.resolved:
                    raise
                return None
        return wrapper
    return decorator


# 全局错误处理器实例
_global_error_handler = None


def get_global_error_handler() -> ErrorHandler:
    """获取全局错误处理器"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def handle_error(exception: Exception, 
                context: Optional[Dict[str, Any]] = None,
                severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                category: ErrorCategory = ErrorCategory.UNKNOWN,
                source: str = "") -> ErrorInfo:
    """全局错误处理函数"""
    return get_global_error_handler().handle_error(exception, context, severity, category, source)


def record_success(source: str):
    """记录成功操作"""
    get_global_error_handler().record_success(source)