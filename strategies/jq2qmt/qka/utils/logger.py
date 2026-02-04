import logging
import requests
import os
import re
import json
from datetime import date, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Dict, Any
import threading

# 自定义格式化器
class JSONFormatter(logging.Formatter):
    """JSON格式的日志格式化器"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # 添加自定义字段
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
            
        return json.dumps(log_entry, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """带颜色的控制台格式化器"""
    
    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
        'RESET': '\033[0m'       # 重置
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # 格式化消息
        formatted = super().format(record)
        return f"{color}{formatted}{reset}"


class RemoveAnsiEscapeCodes(logging.Filter):
    """移除ANSI转义码的过滤器"""
    
    def filter(self, record):
        record.msg = re.sub(r'\033\[[0-9;]*m', '', str(record.msg))
        return True


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str = 'qka'):
        self.logger = logging.getLogger(name)
        self._lock = threading.Lock()
    
    def log(self, level: int, message: str, **kwargs):
        """记录结构化日志"""
        with self._lock:
            # 创建日志记录，附加额外字段
            if kwargs:
                record = self.logger.makeRecord(
                    self.logger.name, level, '', 0, message, (), None
                )
                record.extra_fields = kwargs
                self.logger.handle(record)
            else:
                self.logger.log(level, message)
    
    def debug(self, message: str, **kwargs):
        self.log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self.log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self.log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self.log(logging.CRITICAL, message, **kwargs)


def create_logger(
    name: str = 'qka',
    level: str = 'INFO',
    console_output: bool = True,
    file_output: bool = True,
    log_dir: str = 'logs',
    max_file_size: str = '10MB',
    backup_count: int = 10,
    json_format: bool = False,
    colored_console: bool = True
):
    """
    创建增强的日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        console_output: 是否输出到控制台
        file_output: 是否输出到文件
        log_dir: 日志文件目录
        max_file_size: 最大文件大小
        backup_count: 备份文件数量
        json_format: 是否使用JSON格式
        colored_console: 控制台是否使用颜色
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 清除现有处理器
    logger.handlers.clear()
    
    # 创建格式化器
    if json_format:
        file_formatter = JSONFormatter()
        console_formatter = JSONFormatter()
    else:
        file_formatter = logging.Formatter(
            '[%(levelname)s][%(asctime)s][%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_formatter = ColoredFormatter(
            '[%(levelname)s][%(asctime)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ) if colored_console else file_formatter

    # 控制台处理器
    if console_output:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(console_formatter)
        logger.addHandler(stream_handler)

    # 文件处理器
    if file_output:
        # 创建日志文件夹
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        # 解析文件大小
        size_map = {'KB': 1024, 'MB': 1024*1024, 'GB': 1024*1024*1024}
        size_unit = max_file_size[-2:].upper()
        size_value = int(max_file_size[:-2])
        max_bytes = size_value * size_map.get(size_unit, 1024*1024)
        
        # 创建轮转文件处理器
        file_handler = RotatingFileHandler(
            f"{log_dir}/{date.today().strftime('%Y-%m-%d')}.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(RemoveAnsiEscapeCodes())
        logger.addHandler(file_handler)

    return logger


def setup_logging_from_config(config_dict: Dict[str, Any]) -> logging.Logger:
    """从配置字典设置日志"""
    return create_logger(**config_dict)


def get_structured_logger(name: str = 'qka') -> StructuredLogger:
    """获取结构化日志记录器"""
    return StructuredLogger(name)


class WeChatHandler(logging.Handler):
    def __init__(self, webhook_url):
        super().__init__()
        self.webhook_url = webhook_url

    def emit(self, record):
        log_entry = self.format(record)
        payload = {
            "msgtype": "text",
            "text": {
                "content": log_entry
            }
        }
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=5)
            response.raise_for_status()
        except Exception as e:
            print(f"发送微信消息失败: {e}")


def add_wechat_handler(logger_instance: logging.Logger, webhook_url: str, level: str = 'ERROR'):
    """
    为日志记录器添加微信通知处理器
    
    Args:
        logger_instance: 日志记录器实例
        webhook_url: 企业微信机器人webhook地址
        level: 通知级别
    """
    wechat_handler = WeChatHandler(webhook_url)
    wechat_handler.setLevel(getattr(logging, level.upper()))
    
    # 创建简单格式化器用于微信消息
    formatter = logging.Formatter(
        '[%(levelname)s][%(asctime)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    wechat_handler.setFormatter(formatter)
    wechat_handler.addFilter(RemoveAnsiEscapeCodes())
    logger_instance.addHandler(wechat_handler)


# 创建默认日志记录器
logger = create_logger()


if __name__ == '__main__':
    # 测试日志系统
    test_logger = create_logger('test', colored_console=True)
    
    test_logger.debug("这是调试信息")
    test_logger.info("这是普通信息")
    test_logger.warning("这是警告信息")
    test_logger.error("这是错误信息")
    test_logger.critical("这是严重错误")
    
    # 测试结构化日志
    struct_logger = get_structured_logger('test_struct')
    struct_logger.info("结构化日志测试", 
                      user_id=123, 
                      action="login", 
                      ip="192.168.1.1")
    
    print("日志测试完成，请查看logs目录")
