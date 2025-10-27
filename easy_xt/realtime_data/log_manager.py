"""
日志管理系统
提供统一的日志管理功能，包括日志收集、格式化、轮转、分析等
"""

import logging
import logging.handlers
import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import gzip
import re
from collections import defaultdict, deque
import queue


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    """日志格式"""
    SIMPLE = "simple"
    DETAILED = "detailed"
    JSON = "json"
    CUSTOM = "custom"


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: LogLevel
    logger_name: str
    message: str
    module: str = ""
    function: str = ""
    line_number: int = 0
    thread_id: int = 0
    process_id: int = 0
    extra_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "logger_name": self.logger_name,
            "message": self.message,
            "module": self.module,
            "function": self.function,
            "line_number": self.line_number,
            "thread_id": self.thread_id,
            "process_id": self.process_id,
            "extra_data": self.extra_data
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class LogConfig:
    """日志配置"""
    log_dir: str = "logs"
    log_level: LogLevel = LogLevel.INFO
    log_format: LogFormat = LogFormat.DETAILED
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    compress_backups: bool = True
    console_output: bool = True
    file_output: bool = True
    json_output: bool = False
    custom_format: Optional[str] = None
    date_format: str = "%Y-%m-%d %H:%M:%S"
    encoding: str = "utf-8"
    buffer_size: int = 1000
    flush_interval: float = 5.0
    enable_colors: bool = True


class ColorFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
        'RESET': '\033[0m'        # 重置
    }
    
    def __init__(self, fmt=None, datefmt=None, enable_colors=True):
        super().__init__(fmt, datefmt)
        self.enable_colors = enable_colors
    
    def format(self, record):
        if self.enable_colors and hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, '')
            reset = self.COLORS['RESET']
            record.levelname = f"{color}{record.levelname}{reset}"
        
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """JSON格式化器"""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "process": record.process
        }
        
        # 添加额外数据
        if hasattr(record, 'extra_data'):
            log_entry.update(record.extra_data)
        
        return json.dumps(log_entry, ensure_ascii=False)


class LogBuffer:
    """日志缓冲区"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffer = deque(maxlen=max_size)
        self.lock = threading.Lock()
    
    def add(self, log_entry: LogEntry):
        """添加日志条目"""
        with self.lock:
            self.buffer.append(log_entry)
    
    def get_recent(self, count: int = 100) -> List[LogEntry]:
        """获取最近的日志条目"""
        with self.lock:
            return list(self.buffer)[-count:]
    
    def clear(self):
        """清空缓冲区"""
        with self.lock:
            self.buffer.clear()
    
    def search(self, 
              keyword: Optional[str] = None,
              level: Optional[LogLevel] = None,
              start_time: Optional[datetime] = None,
              end_time: Optional[datetime] = None) -> List[LogEntry]:
        """搜索日志条目"""
        with self.lock:
            results = []
            for entry in self.buffer:
                # 关键词过滤
                if keyword and keyword.lower() not in entry.message.lower():
                    continue
                
                # 级别过滤
                if level and entry.level != level:
                    continue
                
                # 时间范围过滤
                if start_time and entry.timestamp < start_time:
                    continue
                if end_time and entry.timestamp > end_time:
                    continue
                
                results.append(entry)
            
            return results


class LogAnalyzer:
    """日志分析器"""
    
    def __init__(self):
        self.stats = defaultdict(int)
        self.error_patterns = []
        self.performance_metrics = {}
    
    def analyze_entry(self, entry: LogEntry):
        """分析单个日志条目"""
        # 统计各级别日志数量
        self.stats[f"level_{entry.level.value}"] += 1
        self.stats["total_logs"] += 1
        
        # 错误模式检测
        if entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            self._detect_error_patterns(entry)
        
        # 性能指标提取
        self._extract_performance_metrics(entry)
    
    def _detect_error_patterns(self, entry: LogEntry):
        """检测错误模式"""
        # 常见错误模式
        patterns = [
            r"Connection.*failed",
            r"Timeout.*error",
            r"Permission.*denied",
            r"File.*not.*found",
            r"Memory.*error",
            r"Database.*error"
        ]
        
        for pattern in patterns:
            if re.search(pattern, entry.message, re.IGNORECASE):
                self.stats[f"error_pattern_{pattern}"] += 1
    
    def _extract_performance_metrics(self, entry: LogEntry):
        """提取性能指标"""
        # 查找响应时间信息
        time_pattern = r"(\d+\.?\d*)\s*(ms|seconds?|s)"
        matches = re.findall(time_pattern, entry.message, re.IGNORECASE)
        
        for value, unit in matches:
            try:
                time_value = float(value)
                if unit.lower() in ['s', 'second', 'seconds']:
                    time_value *= 1000  # 转换为毫秒
                
                if 'response_times' not in self.performance_metrics:
                    self.performance_metrics['response_times'] = []
                self.performance_metrics['response_times'].append(time_value)
            except ValueError:
                continue
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = dict(self.stats)
        
        # 计算错误率
        total_logs = stats.get("total_logs", 0)
        error_logs = stats.get("level_ERROR", 0) + stats.get("level_CRITICAL", 0)
        stats["error_rate"] = error_logs / total_logs if total_logs > 0 else 0
        
        # 性能统计
        if 'response_times' in self.performance_metrics:
            times = self.performance_metrics['response_times']
            if times:
                stats["avg_response_time"] = sum(times) / len(times)
                stats["max_response_time"] = max(times)
                stats["min_response_time"] = min(times)
        
        return stats
    
    def reset(self):
        """重置统计"""
        self.stats.clear()
        self.performance_metrics.clear()


class LogManager:
    """日志管理器"""
    
    def __init__(self, config: Optional[LogConfig] = None):
        self.config = config or LogConfig()
        self.loggers: Dict[str, logging.Logger] = {}
        self.buffer = LogBuffer(self.config.buffer_size)
        self.analyzer = LogAnalyzer()
        self.handlers: List[logging.Handler] = []
        self._setup_logging()
        self._start_flush_thread()
    
    def _setup_logging(self):
        """设置日志系统"""
        # 创建日志目录
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置根日志级别
        logging.getLogger().setLevel(getattr(logging, self.config.log_level.value))
        
        # 创建格式化器
        formatters = self._create_formatters()
        
        # 控制台处理器
        if self.config.console_output:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatters['console'])
            self.handlers.append(console_handler)
        
        # 文件处理器
        if self.config.file_output:
            file_handler = self._create_file_handler()
            file_handler.setFormatter(formatters['file'])
            self.handlers.append(file_handler)
        
        # JSON文件处理器
        if self.config.json_output:
            json_handler = self._create_json_handler()
            json_handler.setFormatter(formatters['json'])
            self.handlers.append(json_handler)
    
    def _create_formatters(self) -> Dict[str, logging.Formatter]:
        """创建格式化器"""
        formatters = {}
        
        # 控制台格式化器
        if self.config.log_format == LogFormat.SIMPLE:
            console_fmt = "%(levelname)s - %(message)s"
        elif self.config.log_format == LogFormat.DETAILED:
            console_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        elif self.config.log_format == LogFormat.CUSTOM and self.config.custom_format:
            console_fmt = self.config.custom_format
        else:
            console_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        formatters['console'] = ColorFormatter(
            console_fmt, 
            self.config.date_format,
            self.config.enable_colors
        )
        
        # 文件格式化器（不使用颜色）
        formatters['file'] = logging.Formatter(
            console_fmt.replace('\033[36m', '').replace('\033[0m', ''),
            self.config.date_format
        )
        
        # JSON格式化器
        formatters['json'] = JSONFormatter()
        
        return formatters
    
    def _create_file_handler(self) -> logging.Handler:
        """创建文件处理器"""
        log_file = Path(self.config.log_dir) / "application.log"
        
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.config.max_file_size,
            backupCount=self.config.backup_count,
            encoding=self.config.encoding
        )
        
        # 压缩备份文件
        if self.config.compress_backups:
            handler.rotator = self._compress_rotator
        
        return handler
    
    def _create_json_handler(self) -> logging.Handler:
        """创建JSON文件处理器"""
        json_file = Path(self.config.log_dir) / "application.json"
        
        return logging.handlers.RotatingFileHandler(
            json_file,
            maxBytes=self.config.max_file_size,
            backupCount=self.config.backup_count,
            encoding=self.config.encoding
        )
    
    def _compress_rotator(self, source, dest):
        """压缩轮转文件"""
        with open(source, 'rb') as f_in:
            with gzip.open(f"{dest}.gz", 'wb') as f_out:
                f_out.writelines(f_in)
        os.remove(source)
    
    def _start_flush_thread(self):
        """启动刷新线程"""
        def flush_logs():
            while True:
                time.sleep(self.config.flush_interval)
                for handler in self.handlers:
                    handler.flush()
        
        flush_thread = threading.Thread(target=flush_logs, daemon=True)
        flush_thread.start()
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取日志记录器"""
        if name not in self.loggers:
            logger = logging.getLogger(name)
            
            # 清除现有处理器
            logger.handlers.clear()
            
            # 添加配置的处理器
            for handler in self.handlers:
                logger.addHandler(handler)
            
            # 设置日志级别
            logger.setLevel(getattr(logging, self.config.log_level.value))
            
            # 防止重复日志
            logger.propagate = False
            
            # 添加自定义处理器用于缓冲和分析
            buffer_handler = self._create_buffer_handler()
            logger.addHandler(buffer_handler)
            
            self.loggers[name] = logger
        
        return self.loggers[name]
    
    def _create_buffer_handler(self) -> logging.Handler:
        """创建缓冲处理器"""
        class BufferHandler(logging.Handler):
            def __init__(self, buffer, analyzer):
                super().__init__()
                self.buffer = buffer
                self.analyzer = analyzer
            
            def emit(self, record):
                try:
                    # 清理levelname中的ANSI颜色代码
                    clean_levelname = record.levelname
                    if '\x1b[' in clean_levelname:
                        import re
                        clean_levelname = re.sub(r'\x1b\[[0-9;]*m', '', clean_levelname)
                    
                    # 创建日志条目
                    entry = LogEntry(
                        timestamp=datetime.fromtimestamp(record.created),
                        level=LogLevel(clean_levelname),
                        logger_name=record.name,
                        message=record.getMessage(),
                        module=getattr(record, 'module', record.filename),
                        function=record.funcName,
                        line_number=record.lineno,
                        thread_id=record.thread,
                        process_id=record.process,
                        extra_data=getattr(record, 'extra_data', {})
                    )
                    
                    # 添加到缓冲区
                    self.buffer.add(entry)
                    
                    # 分析日志
                    self.analyzer.analyze_entry(entry)
                    
                except Exception:
                    self.handleError(record)
        
        return BufferHandler(self.buffer, self.analyzer)
    
    def log(self, logger_name: str, level: LogLevel, message: str, **kwargs):
        """记录日志"""
        logger = self.get_logger(logger_name)
        log_level = getattr(logging, level.value)
        
        # 添加额外数据
        if kwargs:
            extra = {'extra_data': kwargs}
            logger.log(log_level, message, extra=extra)
        else:
            logger.log(log_level, message)
    
    def debug(self, logger_name: str, message: str, **kwargs):
        """记录调试日志"""
        self.log(logger_name, LogLevel.DEBUG, message, **kwargs)
    
    def info(self, logger_name: str, message: str, **kwargs):
        """记录信息日志"""
        self.log(logger_name, LogLevel.INFO, message, **kwargs)
    
    def warning(self, logger_name: str, message: str, **kwargs):
        """记录警告日志"""
        self.log(logger_name, LogLevel.WARNING, message, **kwargs)
    
    def error(self, logger_name: str, message: str, **kwargs):
        """记录错误日志"""
        self.log(logger_name, LogLevel.ERROR, message, **kwargs)
    
    def critical(self, logger_name: str, message: str, **kwargs):
        """记录严重错误日志"""
        self.log(logger_name, LogLevel.CRITICAL, message, **kwargs)
    
    def get_recent_logs(self, count: int = 100) -> List[LogEntry]:
        """获取最近的日志"""
        return self.buffer.get_recent(count)
    
    def search_logs(self, 
                   keyword: Optional[str] = None,
                   level: Optional[LogLevel] = None,
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None) -> List[LogEntry]:
        """搜索日志"""
        return self.buffer.search(keyword, level, start_time, end_time)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取日志统计"""
        return self.analyzer.get_statistics()
    
    def export_logs(self, 
                   filename: str,
                   format: str = "json",
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None):
        """导出日志"""
        logs = self.search_logs(start_time=start_time, end_time=end_time)
        
        if format.lower() == "json":
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump([log.to_dict() for log in logs], f, indent=2, ensure_ascii=False)
        elif format.lower() == "csv":
            import csv
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                if logs:
                    writer = csv.DictWriter(f, fieldnames=logs[0].to_dict().keys())
                    writer.writeheader()
                    for log in logs:
                        writer.writerow(log.to_dict())
        else:
            raise ValueError(f"不支持的导出格式: {format}")
    
    def clear_logs(self):
        """清空日志缓冲区"""
        self.buffer.clear()
        self.analyzer.reset()
    
    def set_log_level(self, level: LogLevel):
        """设置日志级别"""
        self.config.log_level = level
        log_level = getattr(logging, level.value)
        
        for logger in self.loggers.values():
            logger.setLevel(log_level)
    
    def add_custom_handler(self, handler: logging.Handler):
        """添加自定义处理器"""
        self.handlers.append(handler)
        for logger in self.loggers.values():
            logger.addHandler(handler)
    
    def remove_handler(self, handler: logging.Handler):
        """移除处理器"""
        if handler in self.handlers:
            self.handlers.remove(handler)
            for logger in self.loggers.values():
                logger.removeHandler(handler)


# 全局日志管理器实例
_global_log_manager = None


def get_global_log_manager() -> LogManager:
    """获取全局日志管理器"""
    global _global_log_manager
    if _global_log_manager is None:
        _global_log_manager = LogManager()
    return _global_log_manager


def get_logger(name: str) -> logging.Logger:
    """获取日志记录器"""
    return get_global_log_manager().get_logger(name)


def log_info(logger_name: str, message: str, **kwargs):
    """记录信息日志"""
    get_global_log_manager().info(logger_name, message, **kwargs)


def log_error(logger_name: str, message: str, **kwargs):
    """记录错误日志"""
    get_global_log_manager().error(logger_name, message, **kwargs)


def log_warning(logger_name: str, message: str, **kwargs):
    """记录警告日志"""
    get_global_log_manager().warning(logger_name, message, **kwargs)


def log_debug(logger_name: str, message: str, **kwargs):
    """记录调试日志"""
    get_global_log_manager().debug(logger_name, message, **kwargs)