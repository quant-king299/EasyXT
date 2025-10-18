#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能监控工具
"""

import time
import psutil
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    active_tasks: int
    response_time_ms: float
    throughput_per_sec: float
    error_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'memory_used_mb': self.memory_used_mb,
            'active_tasks': self.active_tasks,
            'response_time_ms': self.response_time_ms,
            'throughput_per_sec': self.throughput_per_sec,
            'error_count': self.error_count
        }


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, max_history: int = 1000):
        """
        初始化性能监控器
        
        Args:
            max_history: 最大历史记录数量
        """
        self.max_history = max_history
        self.metrics_history: deque = deque(maxlen=max_history)
        self.operation_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.start_time = datetime.now()
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 性能阈值
        self.thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'response_time_ms': 1000.0,
            'error_rate': 0.05  # 5%
        }
    
    async def start_monitoring(self, interval: float = 1.0):
        """
        开始性能监控
        
        Args:
            interval: 监控间隔（秒）
        """
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop(interval))
        self.logger.info("性能监控已启动")
    
    async def stop_monitoring(self):
        """停止性能监控"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("性能监控已停止")
    
    async def _monitor_loop(self, interval: float):
        """监控循环"""
        while self.is_monitoring:
            try:
                metrics = await self._collect_metrics()
                self.metrics_history.append(metrics)
                
                # 检查性能阈值
                await self._check_thresholds(metrics)
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"性能监控错误: {e}")
                await asyncio.sleep(interval)
    
    async def _collect_metrics(self) -> PerformanceMetrics:
        """收集性能指标"""
        # 系统资源使用情况
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / 1024 / 1024
        
        # 活跃任务数量
        active_tasks = len([task for task in asyncio.all_tasks() if not task.done()])
        
        # 计算平均响应时间
        avg_response_time = self._calculate_average_response_time()
        
        # 计算吞吐量
        throughput = self._calculate_throughput()
        
        # 错误计数
        total_errors = sum(self.error_counts.values())
        
        return PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_mb=memory_used_mb,
            active_tasks=active_tasks,
            response_time_ms=avg_response_time,
            throughput_per_sec=throughput,
            error_count=total_errors
        )
    
    def _calculate_average_response_time(self) -> float:
        """计算平均响应时间"""
        all_times = []
        for operation_times in self.operation_times.values():
            all_times.extend(operation_times)
        
        if not all_times:
            return 0.0
        
        return sum(all_times) / len(all_times) * 1000  # 转换为毫秒
    
    def _calculate_throughput(self) -> float:
        """计算吞吐量（每秒操作数）"""
        if len(self.metrics_history) < 2:
            return 0.0
        
        # 计算最近一分钟的操作数
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        
        recent_operations = 0
        for operation_times in self.operation_times.values():
            # 这里简化处理，实际应该记录操作时间戳
            recent_operations += len(operation_times)
        
        return recent_operations / 60.0  # 每秒操作数
    
    async def _check_thresholds(self, metrics: PerformanceMetrics):
        """检查性能阈值"""
        warnings = []
        
        if metrics.cpu_percent > self.thresholds['cpu_percent']:
            warnings.append(f"CPU使用率过高: {metrics.cpu_percent:.1f}%")
        
        if metrics.memory_percent > self.thresholds['memory_percent']:
            warnings.append(f"内存使用率过高: {metrics.memory_percent:.1f}%")
        
        if metrics.response_time_ms > self.thresholds['response_time_ms']:
            warnings.append(f"响应时间过长: {metrics.response_time_ms:.1f}ms")
        
        # 计算错误率
        total_operations = sum(len(times) for times in self.operation_times.values())
        if total_operations > 0:
            error_rate = metrics.error_count / total_operations
            if error_rate > self.thresholds['error_rate']:
                warnings.append(f"错误率过高: {error_rate:.2%}")
        
        if warnings:
            self.logger.warning("性能警告: " + "; ".join(warnings))
    
    def record_operation(self, operation_name: str, duration: float):
        """
        记录操作执行时间
        
        Args:
            operation_name: 操作名称
            duration: 执行时间（秒）
        """
        self.operation_times[operation_name].append(duration)
    
    def record_error(self, error_type: str):
        """
        记录错误
        
        Args:
            error_type: 错误类型
        """
        self.error_counts[error_type] += 1
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """获取当前性能指标"""
        if not self.metrics_history:
            return None
        return self.metrics_history[-1]
    
    def get_metrics_history(self, minutes: int = 10) -> List[PerformanceMetrics]:
        """
        获取历史性能指标
        
        Args:
            minutes: 获取最近多少分钟的数据
            
        Returns:
            性能指标列表
        """
        if not self.metrics_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [
            metrics for metrics in self.metrics_history
            if metrics.timestamp >= cutoff_time
        ]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.metrics_history:
            return {}
        
        recent_metrics = self.get_metrics_history(10)  # 最近10分钟
        
        if not recent_metrics:
            return {}
        
        # 计算统计信息
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        response_times = [m.response_time_ms for m in recent_metrics]
        
        return {
            'monitoring_duration': str(datetime.now() - self.start_time),
            'total_samples': len(self.metrics_history),
            'recent_samples': len(recent_metrics),
            'cpu_usage': {
                'current': recent_metrics[-1].cpu_percent,
                'average': sum(cpu_values) / len(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values)
            },
            'memory_usage': {
                'current': recent_metrics[-1].memory_percent,
                'average': sum(memory_values) / len(memory_values),
                'max': max(memory_values),
                'min': min(memory_values)
            },
            'response_time': {
                'current': recent_metrics[-1].response_time_ms,
                'average': sum(response_times) / len(response_times),
                'max': max(response_times),
                'min': min(response_times)
            },
            'active_tasks': recent_metrics[-1].active_tasks,
            'total_errors': sum(self.error_counts.values()),
            'error_breakdown': dict(self.error_counts)
        }
    
    def export_metrics(self, filepath: str):
        """
        导出性能指标到文件
        
        Args:
            filepath: 文件路径
        """
        import json
        
        data = {
            'export_time': datetime.now().isoformat(),
            'monitoring_duration': str(datetime.now() - self.start_time),
            'metrics': [metrics.to_dict() for metrics in self.metrics_history],
            'summary': self.get_performance_summary()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"性能指标已导出到: {filepath}")


class PerformanceDecorator:
    """性能监控装饰器"""
    
    def __init__(self, monitor: PerformanceMonitor, operation_name: str = None):
        """
        初始化装饰器
        
        Args:
            monitor: 性能监控器实例
            operation_name: 操作名称
        """
        self.monitor = monitor
        self.operation_name = operation_name
    
    def __call__(self, func):
        """装饰器调用"""
        operation_name = self.operation_name or f"{func.__module__}.{func.__name__}"
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    self.monitor.record_error(type(e).__name__)
                    raise
                finally:
                    duration = time.time() - start_time
                    self.monitor.record_operation(operation_name, duration)
            
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    self.monitor.record_error(type(e).__name__)
                    raise
                finally:
                    duration = time.time() - start_time
                    self.monitor.record_operation(operation_name, duration)
            
            return sync_wrapper


# 全局性能监控器实例
global_monitor = PerformanceMonitor()


def monitor_performance(operation_name: str = None):
    """
    性能监控装饰器
    
    Args:
        operation_name: 操作名称
        
    Returns:
        装饰器函数
    """
    return PerformanceDecorator(global_monitor, operation_name)


async def start_global_monitoring(interval: float = 1.0):
    """启动全局性能监控"""
    await global_monitor.start_monitoring(interval)


async def stop_global_monitoring():
    """停止全局性能监控"""
    await global_monitor.stop_monitoring()


def get_performance_summary() -> Dict[str, Any]:
    """获取全局性能摘要"""
    return global_monitor.get_performance_summary()


if __name__ == "__main__":
    # 测试性能监控器
    async def test_monitor():
        monitor = PerformanceMonitor()
        
        # 启动监控
        await monitor.start_monitoring(0.5)
        
        # 模拟一些操作
        for i in range(10):
            start_time = time.time()
            await asyncio.sleep(0.1)
            duration = time.time() - start_time
            monitor.record_operation(f"test_operation_{i % 3}", duration)
        
        # 等待收集一些数据
        await asyncio.sleep(2)
        
        # 获取性能摘要
        summary = monitor.get_performance_summary()
        print("性能摘要:")
        import json
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        
        # 停止监控
        await monitor.stop_monitoring()
    
    asyncio.run(test_monitor())