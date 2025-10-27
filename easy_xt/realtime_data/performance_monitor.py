"""
性能监控和优化模块
实现性能监控，识别瓶颈并优化系统性能
"""

import time
import psutil
import threading
import asyncio
import statistics
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path


@dataclass
class PerformanceMetric:
    """性能指标"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    category: str = "general"
    tags: Optional[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


@dataclass
class PerformanceThreshold:
    """性能阈值"""
    metric_name: str
    warning_threshold: float
    critical_threshold: float
    comparison: str = "greater"  # greater, less, equal
    enabled: bool = True


@dataclass
class PerformanceReport:
    """性能报告"""
    start_time: datetime
    end_time: datetime
    metrics: List[PerformanceMetric]
    bottlenecks: List[Dict[str, Any]]
    recommendations: List[str]
    summary: Dict[str, Any]


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.metrics = defaultdict(lambda: deque(maxlen=1000))
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
    
    def record_metric(self, name: str, value: float, unit: str = "", 
                     category: str = "general", tags: Optional[Dict[str, str]] = None):
        """记录性能指标"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            category=category,
            tags=tags or {}
        )
        
        with self.lock:
            self.metrics[name].append(metric)
    
    def get_metrics(self, name: str, since: Optional[datetime] = None) -> List[PerformanceMetric]:
        """获取指标数据"""
        with self.lock:
            metrics = list(self.metrics[name])
        
        if since:
            metrics = [m for m in metrics if m.timestamp >= since]
        
        return metrics
    
    def get_metric_statistics(self, name: str, since: Optional[datetime] = None) -> Dict[str, float]:
        """获取指标统计信息"""
        metrics = self.get_metrics(name, since)
        
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "p95": statistics.quantiles(values, n=20)[18] if len(values) >= 20 else max(values),
            "p99": statistics.quantiles(values, n=100)[98] if len(values) >= 100 else max(values)
        }
    
    def clear_metrics(self, name: Optional[str] = None):
        """清除指标数据"""
        with self.lock:
            if name:
                self.metrics[name].clear()
            else:
                self.metrics.clear()


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.monitoring = False
        self.monitor_thread = None
        self.logger = logging.getLogger(__name__)
    
    def start_monitoring(self, interval: float = 1.0):
        """开始系统监控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        self.logger.info("系统监控已启动")
    
    def stop_monitoring(self):
        """停止系统监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        self.logger.info("系统监控已停止")
    
    def _monitor_loop(self, interval: float):
        """监控循环"""
        while self.monitoring:
            try:
                self._collect_system_metrics()
                time.sleep(interval)
            except Exception as e:
                self.logger.error(f"系统监控错误: {e}")
    
    def _collect_system_metrics(self):
        """收集系统指标"""
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=None)
        self.collector.record_metric("cpu_usage", cpu_percent, "%", "system")
        
        # 内存使用情况
        memory = psutil.virtual_memory()
        self.collector.record_metric("memory_usage", memory.percent, "%", "system")
        self.collector.record_metric("memory_available", memory.available / (1024**3), "GB", "system")
        
        # 磁盘使用情况
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        self.collector.record_metric("disk_usage", disk_percent, "%", "system")
        
        # 网络IO
        net_io = psutil.net_io_counters()
        self.collector.record_metric("network_bytes_sent", net_io.bytes_sent, "bytes", "network")
        self.collector.record_metric("network_bytes_recv", net_io.bytes_recv, "bytes", "network")
        
        # 进程信息
        process = psutil.Process()
        self.collector.record_metric("process_cpu", process.cpu_percent(), "%", "process")
        self.collector.record_metric("process_memory", process.memory_info().rss / (1024**2), "MB", "process")


class RequestTracker:
    """请求跟踪器"""
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.active_requests = {}
        self.lock = threading.Lock()
    
    def start_request(self, request_id: str, endpoint: str, method: str = "GET") -> str:
        """开始跟踪请求"""
        start_time = time.time()
        
        with self.lock:
            self.active_requests[request_id] = {
                "endpoint": endpoint,
                "method": method,
                "start_time": start_time,
                "timestamp": datetime.now()
            }
        
        return request_id
    
    def end_request(self, request_id: str, status_code: int = 200, error: Optional[str] = None):
        """结束请求跟踪"""
        end_time = time.time()
        
        with self.lock:
            if request_id not in self.active_requests:
                return
            
            request_info = self.active_requests.pop(request_id)
        
        # 计算响应时间
        response_time = (end_time - request_info["start_time"]) * 1000  # 毫秒
        
        # 记录指标
        tags = {
            "endpoint": request_info["endpoint"],
            "method": request_info["method"],
            "status": str(status_code)
        }
        
        self.collector.record_metric("request_duration", response_time, "ms", "request", tags)
        self.collector.record_metric("request_count", 1, "count", "request", tags)
        
        if error:
            self.collector.record_metric("request_error", 1, "count", "request", 
                                       {**tags, "error": error})


class PerformanceAnalyzer:
    """性能分析器"""
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.thresholds = []
        self.logger = logging.getLogger(__name__)
    
    def add_threshold(self, threshold: PerformanceThreshold):
        """添加性能阈值"""
        self.thresholds.append(threshold)
    
    def analyze_performance(self, duration_minutes: int = 60) -> PerformanceReport:
        """分析性能"""
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=duration_minutes)
        
        # 收集所有指标
        all_metrics = []
        metric_names = list(self.collector.metrics.keys())
        
        for name in metric_names:
            metrics = self.collector.get_metrics(name, start_time)
            all_metrics.extend(metrics)
        
        # 识别瓶颈
        bottlenecks = self._identify_bottlenecks(start_time)
        
        # 生成建议
        recommendations = self._generate_recommendations(bottlenecks)
        
        # 生成摘要
        summary = self._generate_summary(start_time)
        
        return PerformanceReport(
            start_time=start_time,
            end_time=end_time,
            metrics=all_metrics,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
            summary=summary
        )
    
    def _identify_bottlenecks(self, since: datetime) -> List[Dict[str, Any]]:
        """识别性能瓶颈"""
        bottlenecks = []
        
        for threshold in self.thresholds:
            if not threshold.enabled:
                continue
            
            stats = self.collector.get_metric_statistics(threshold.metric_name, since)
            if not stats:
                continue
            
            # 检查阈值
            value = stats.get("mean", 0)
            is_bottleneck = False
            severity = "info"
            
            if threshold.comparison == "greater":
                if value >= threshold.critical_threshold:
                    is_bottleneck = True
                    severity = "critical"
                elif value >= threshold.warning_threshold:
                    is_bottleneck = True
                    severity = "warning"
            elif threshold.comparison == "less":
                if value <= threshold.critical_threshold:
                    is_bottleneck = True
                    severity = "critical"
                elif value <= threshold.warning_threshold:
                    is_bottleneck = True
                    severity = "warning"
            
            if is_bottleneck:
                bottlenecks.append({
                    "metric": threshold.metric_name,
                    "value": value,
                    "threshold": threshold.warning_threshold if severity == "warning" else threshold.critical_threshold,
                    "severity": severity,
                    "statistics": stats
                })
        
        return bottlenecks
    
    def _generate_recommendations(self, bottlenecks: List[Dict[str, Any]]) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        for bottleneck in bottlenecks:
            metric = bottleneck["metric"]
            severity = bottleneck["severity"]
            
            if metric == "cpu_usage":
                if severity == "critical":
                    recommendations.append("CPU使用率过高，建议：1) 优化算法复杂度 2) 增加并发控制 3) 考虑水平扩展")
                else:
                    recommendations.append("CPU使用率较高，建议监控并优化计算密集型操作")
            
            elif metric == "memory_usage":
                if severity == "critical":
                    recommendations.append("内存使用率过高，建议：1) 检查内存泄漏 2) 优化缓存策略 3) 增加内存容量")
                else:
                    recommendations.append("内存使用率较高，建议优化数据结构和缓存策略")
            
            elif metric == "request_duration":
                if severity == "critical":
                    recommendations.append("请求响应时间过长，建议：1) 优化数据库查询 2) 增加缓存 3) 异步处理")
                else:
                    recommendations.append("请求响应时间较长，建议检查慢查询和网络延迟")
            
            elif metric == "disk_usage":
                if severity == "critical":
                    recommendations.append("磁盘使用率过高，建议：1) 清理日志文件 2) 数据归档 3) 扩展存储容量")
                else:
                    recommendations.append("磁盘使用率较高，建议定期清理和监控存储空间")
        
        if not recommendations:
            recommendations.append("系统性能良好，建议继续监控关键指标")
        
        return recommendations
    
    def _generate_summary(self, since: datetime) -> Dict[str, Any]:
        """生成性能摘要"""
        summary = {
            "period": f"{(datetime.now() - since).total_seconds() / 60:.1f} minutes",
            "metrics_collected": len(self.collector.metrics),
            "key_metrics": {}
        }
        
        # 关键指标统计
        key_metrics = ["cpu_usage", "memory_usage", "request_duration", "request_count"]
        
        for metric in key_metrics:
            stats = self.collector.get_metric_statistics(metric, since)
            if stats:
                summary["key_metrics"][metric] = {
                    "avg": round(stats.get("mean", 0), 2),
                    "max": round(stats.get("max", 0), 2),
                    "p95": round(stats.get("p95", 0), 2)
                }
        
        return summary


class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(self, collector: MetricsCollector, analyzer: PerformanceAnalyzer):
        self.collector = collector
        self.analyzer = analyzer
        self.optimizations = []
        self.logger = logging.getLogger(__name__)
    
    def register_optimization(self, name: str, condition: Callable, action: Callable):
        """注册优化策略"""
        self.optimizations.append({
            "name": name,
            "condition": condition,
            "action": action
        })
    
    def auto_optimize(self) -> List[str]:
        """自动优化"""
        applied_optimizations = []
        
        # 分析当前性能
        report = self.analyzer.analyze_performance(duration_minutes=10)
        
        for optimization in self.optimizations:
            try:
                if optimization["condition"](report):
                    optimization["action"](report)
                    applied_optimizations.append(optimization["name"])
                    self.logger.info(f"应用优化策略: {optimization['name']}")
            except Exception as e:
                self.logger.error(f"优化策略执行失败 {optimization['name']}: {e}")
        
        return applied_optimizations


class PerformanceMonitor:
    """性能监控主类"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.collector = MetricsCollector()
        self.system_monitor = SystemMonitor(self.collector)
        self.request_tracker = RequestTracker(self.collector)
        self.analyzer = PerformanceAnalyzer(self.collector)
        self.optimizer = PerformanceOptimizer(self.collector, self.analyzer)
        
        self.logger = logging.getLogger(__name__)
        self.monitoring = False
        
        # 加载配置
        if config_file:
            self._load_config(config_file)
        else:
            self._setup_default_thresholds()
        
        # 注册默认优化策略
        self._register_default_optimizations()
    
    def _load_config(self, config_file: str):
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 加载阈值配置
            for threshold_config in config.get("thresholds", []):
                threshold = PerformanceThreshold(**threshold_config)
                self.analyzer.add_threshold(threshold)
            
            self.logger.info(f"性能监控配置加载成功: {config_file}")
        except Exception as e:
            self.logger.error(f"配置加载失败: {e}")
            self._setup_default_thresholds()
    
    def _setup_default_thresholds(self):
        """设置默认阈值"""
        default_thresholds = [
            PerformanceThreshold("cpu_usage", 70.0, 90.0, "greater"),
            PerformanceThreshold("memory_usage", 80.0, 95.0, "greater"),
            PerformanceThreshold("disk_usage", 85.0, 95.0, "greater"),
            PerformanceThreshold("request_duration", 1000.0, 3000.0, "greater"),
        ]
        
        for threshold in default_thresholds:
            self.analyzer.add_threshold(threshold)
    
    def _register_default_optimizations(self):
        """注册默认优化策略"""
        # CPU优化
        def high_cpu_condition(report):
            cpu_bottlenecks = [b for b in report.bottlenecks if b["metric"] == "cpu_usage"]
            return len(cpu_bottlenecks) > 0
        
        def cpu_optimization_action(report):
            # 这里可以实现具体的CPU优化逻辑
            self.logger.info("执行CPU优化策略")
        
        self.optimizer.register_optimization("cpu_optimization", high_cpu_condition, cpu_optimization_action)
        
        # 内存优化
        def high_memory_condition(report):
            memory_bottlenecks = [b for b in report.bottlenecks if b["metric"] == "memory_usage"]
            return len(memory_bottlenecks) > 0
        
        def memory_optimization_action(report):
            # 这里可以实现具体的内存优化逻辑
            self.logger.info("执行内存优化策略")
        
        self.optimizer.register_optimization("memory_optimization", high_memory_condition, memory_optimization_action)
    
    def start_monitoring(self, system_interval: float = 1.0):
        """开始性能监控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.system_monitor.start_monitoring(system_interval)
        self.logger.info("性能监控已启动")
    
    def stop_monitoring(self):
        """停止性能监控"""
        if not self.monitoring:
            return
        
        self.monitoring = False
        self.system_monitor.stop_monitoring()
        self.logger.info("性能监控已停止")
    
    def record_request(self, request_id: str, endpoint: str, method: str = "GET") -> str:
        """记录请求开始"""
        return self.request_tracker.start_request(request_id, endpoint, method)
    
    def complete_request(self, request_id: str, status_code: int = 200, error: Optional[str] = None):
        """记录请求完成"""
        self.request_tracker.end_request(request_id, status_code, error)
    
    def record_custom_metric(self, name: str, value: float, unit: str = "", 
                           category: str = "custom", tags: Optional[Dict[str, str]] = None):
        """记录自定义指标"""
        self.collector.record_metric(name, value, unit, category, tags)
    
    def get_performance_report(self, duration_minutes: int = 60) -> PerformanceReport:
        """获取性能报告"""
        return self.analyzer.analyze_performance(duration_minutes)
    
    def export_report(self, report: PerformanceReport, file_path: str):
        """导出性能报告"""
        report_data = {
            "start_time": report.start_time.isoformat(),
            "end_time": report.end_time.isoformat(),
            "metrics_count": len(report.metrics),
            "bottlenecks": report.bottlenecks,
            "recommendations": report.recommendations,
            "summary": report.summary
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"性能报告已导出: {file_path}")
    
    def auto_optimize(self) -> List[str]:
        """执行自动优化"""
        return self.optimizer.auto_optimize()


# 性能监控装饰器
def monitor_performance(monitor: PerformanceMonitor, metric_name: str = None):
    """性能监控装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            name = metric_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                monitor.record_custom_metric(f"{name}_duration", duration, "ms", "function")
                monitor.record_custom_metric(f"{name}_success", 1, "count", "function")
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                monitor.record_custom_metric(f"{name}_duration", duration, "ms", "function")
                monitor.record_custom_metric(f"{name}_error", 1, "count", "function", {"error": str(e)})
                raise
        
        return wrapper
    return decorator


# 异步性能监控装饰器
def monitor_async_performance(monitor: PerformanceMonitor, metric_name: str = None):
    """异步性能监控装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            name = metric_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                monitor.record_custom_metric(f"{name}_duration", duration, "ms", "async_function")
                monitor.record_custom_metric(f"{name}_success", 1, "count", "async_function")
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                monitor.record_custom_metric(f"{name}_duration", duration, "ms", "async_function")
                monitor.record_custom_metric(f"{name}_error", 1, "count", "async_function", {"error": str(e)})
                raise
        
        return wrapper
    return decorator