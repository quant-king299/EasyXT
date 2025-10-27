"""
指标收集器

统一收集各种监控指标，提供统一的查询接口。
"""

import time
import logging
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque

from .system_monitor import SystemMonitor
from .data_source_monitor import DataSourceMonitor
from .api_monitor import APIMonitor
from .alert_manager import AlertManager

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """指标数据点"""
    timestamp: datetime
    metric_name: str
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    source: str = ""


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, 
                 collection_interval: int = 30,
                 retention_period: timedelta = timedelta(days=7),
                 max_points_per_metric: int = 10000):
        """初始化指标收集器
        
        Args:
            collection_interval: 收集间隔（秒）
            retention_period: 数据保留期
            max_points_per_metric: 每个指标最大数据点数
        """
        self.collection_interval = collection_interval
        self.retention_period = retention_period
        self.max_points_per_metric = max_points_per_metric
        
        # 指标存储
        self.metrics_data: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_points_per_metric)
        )
        
        # 监控器实例
        self.system_monitor: Optional[SystemMonitor] = None
        self.data_source_monitor: Optional[DataSourceMonitor] = None
        self.api_monitor: Optional[APIMonitor] = None
        self.alert_manager: Optional[AlertManager] = None
        
        # 自定义指标收集器
        self.custom_collectors: Dict[str, Callable[[], Dict[str, float]]] = {}
        
        # 运行状态
        self._running = False
        self._collection_thread = None
        self._cleanup_thread = None
        self._lock = threading.RLock()
        
        logger.info(f"指标收集器初始化完成，收集间隔: {collection_interval}秒")
    
    def register_system_monitor(self, system_monitor: SystemMonitor):
        """注册系统监控器"""
        self.system_monitor = system_monitor
        logger.info("系统监控器已注册")
    
    def register_data_source_monitor(self, data_source_monitor: DataSourceMonitor):
        """注册数据源监控器"""
        self.data_source_monitor = data_source_monitor
        logger.info("数据源监控器已注册")
    
    def register_api_monitor(self, api_monitor: APIMonitor):
        """注册API监控器"""
        self.api_monitor = api_monitor
        logger.info("API监控器已注册")
    
    def register_alert_manager(self, alert_manager: AlertManager):
        """注册告警管理器"""
        self.alert_manager = alert_manager
        logger.info("告警管理器已注册")
    
    def register_custom_collector(self, name: str, collector_func: Callable[[], Dict[str, float]]):
        """注册自定义指标收集器
        
        Args:
            name: 收集器名称
            collector_func: 收集函数，返回 {metric_name: value} 字典
        """
        self.custom_collectors[name] = collector_func
        logger.info(f"自定义收集器已注册: {name}")
    
    def start(self):
        """启动指标收集"""
        if self._running:
            logger.warning("指标收集器已在运行")
            return
        
        self._running = True
        
        # 启动收集线程
        self._collection_thread = threading.Thread(
            target=self._collection_loop,
            name="MetricsCollector",
            daemon=True
        )
        self._collection_thread.start()
        
        # 启动清理线程
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            name="MetricsCleanup",
            daemon=True
        )
        self._cleanup_thread.start()
        
        logger.info("指标收集器已启动")
    
    def stop(self):
        """停止指标收集"""
        if not self._running:
            return
        
        self._running = False
        
        if self._collection_thread and self._collection_thread.is_alive():
            self._collection_thread.join(timeout=5)
        
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        
        logger.info("指标收集器已停止")
    
    def _collection_loop(self):
        """指标收集循环"""
        while self._running:
            try:
                self._collect_all_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"指标收集失败: {e}")
                time.sleep(self.collection_interval)
    
    def _cleanup_loop(self):
        """数据清理循环"""
        while self._running:
            try:
                self._cleanup_old_data()
                time.sleep(3600)  # 每小时清理一次
            except Exception as e:
                logger.error(f"数据清理失败: {e}")
                time.sleep(3600)
    
    def _collect_all_metrics(self):
        """收集所有指标"""
        timestamp = datetime.now()
        
        # 收集系统指标
        if self.system_monitor:
            self._collect_system_metrics(timestamp)
        
        # 收集数据源指标
        if self.data_source_monitor:
            self._collect_data_source_metrics(timestamp)
        
        # 收集API指标
        if self.api_monitor:
            self._collect_api_metrics(timestamp)
        
        # 收集告警指标
        if self.alert_manager:
            self._collect_alert_metrics(timestamp)
        
        # 收集自定义指标
        self._collect_custom_metrics(timestamp)
    
    def _collect_system_metrics(self, timestamp: datetime):
        """收集系统指标"""
        try:
            current_metrics = self.system_monitor.get_current_metrics()
            if not current_metrics:
                return
            
            # CPU指标
            self._add_metric_point(MetricPoint(
                timestamp=timestamp,
                metric_name="system.cpu.percent",
                value=current_metrics.cpu_percent,
                source="system_monitor"
            ))
            
            # 内存指标
            self._add_metric_point(MetricPoint(
                timestamp=timestamp,
                metric_name="system.memory.percent",
                value=current_metrics.memory_percent,
                source="system_monitor"
            ))
            
            self._add_metric_point(MetricPoint(
                timestamp=timestamp,
                metric_name="system.memory.used_bytes",
                value=current_metrics.memory_used,
                source="system_monitor"
            ))
            
            # 磁盘指标
            self._add_metric_point(MetricPoint(
                timestamp=timestamp,
                metric_name="system.disk.percent",
                value=current_metrics.disk_percent,
                source="system_monitor"
            ))
            
            # 网络指标
            self._add_metric_point(MetricPoint(
                timestamp=timestamp,
                metric_name="system.network.sent_bytes",
                value=current_metrics.network_sent,
                source="system_monitor"
            ))
            
            self._add_metric_point(MetricPoint(
                timestamp=timestamp,
                metric_name="system.network.recv_bytes",
                value=current_metrics.network_recv,
                source="system_monitor"
            ))
            
            # 进程数
            self._add_metric_point(MetricPoint(
                timestamp=timestamp,
                metric_name="system.process.count",
                value=current_metrics.process_count,
                source="system_monitor"
            ))
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
    
    def _collect_data_source_metrics(self, timestamp: datetime):
        """收集数据源指标"""
        try:
            all_status = self.data_source_monitor.get_current_status()
            
            for source_name, status_info in all_status.items():
                if isinstance(status_info, dict) and 'status' in status_info:
                    # 可用性指标（1=在线，0=离线）
                    availability = 1.0 if status_info['status'] == 'online' else 0.0
                    self._add_metric_point(MetricPoint(
                        timestamp=timestamp,
                        metric_name="datasource.availability",
                        value=availability,
                        tags={'source': source_name},
                        source="data_source_monitor"
                    ))
                    
                    # 响应时间指标
                    if 'response_time' in status_info:
                        self._add_metric_point(MetricPoint(
                            timestamp=timestamp,
                            metric_name="datasource.response_time_ms",
                            value=status_info['response_time'],
                            tags={'source': source_name},
                            source="data_source_monitor"
                        ))
                    
                    # 错误率指标
                    if 'error_rate' in status_info:
                        self._add_metric_point(MetricPoint(
                            timestamp=timestamp,
                            metric_name="datasource.error_rate_percent",
                            value=status_info['error_rate'],
                            tags={'source': source_name},
                            source="data_source_monitor"
                        ))
            
        except Exception as e:
            logger.error(f"收集数据源指标失败: {e}")
    
    def _collect_api_metrics(self, timestamp: datetime):
        """收集API指标"""
        try:
            overall_stats = self.api_monitor.get_overall_stats()
            
            # 整体API指标
            self._add_metric_point(MetricPoint(
                timestamp=timestamp,
                metric_name="api.requests_total",
                value=overall_stats.get('total_requests', 0),
                source="api_monitor"
            ))
            
            self._add_metric_point(MetricPoint(
                timestamp=timestamp,
                metric_name="api.success_rate_percent",
                value=overall_stats.get('success_rate', 0),
                source="api_monitor"
            ))
            
            self._add_metric_point(MetricPoint(
                timestamp=timestamp,
                metric_name="api.error_rate_percent",
                value=overall_stats.get('error_rate', 0),
                source="api_monitor"
            ))
            
            self._add_metric_point(MetricPoint(
                timestamp=timestamp,
                metric_name="api.avg_response_time_ms",
                value=overall_stats.get('avg_response_time', 0),
                source="api_monitor"
            ))
            
            self._add_metric_point(MetricPoint(
                timestamp=timestamp,
                metric_name="api.requests_per_second",
                value=overall_stats.get('requests_per_second', 0),
                source="api_monitor"
            ))
            
            # 端点级别指标
            endpoint_stats = self.api_monitor.get_endpoint_stats()
            for endpoint, stats in endpoint_stats.items():
                tags = {'endpoint': endpoint}
                
                self._add_metric_point(MetricPoint(
                    timestamp=timestamp,
                    metric_name="api.endpoint.requests_total",
                    value=stats.get('total_requests', 0),
                    tags=tags,
                    source="api_monitor"
                ))
                
                self._add_metric_point(MetricPoint(
                    timestamp=timestamp,
                    metric_name="api.endpoint.error_rate_percent",
                    value=stats.get('error_rate', 0),
                    tags=tags,
                    source="api_monitor"
                ))
                
                self._add_metric_point(MetricPoint(
                    timestamp=timestamp,
                    metric_name="api.endpoint.avg_response_time_ms",
                    value=stats.get('avg_response_time', 0),
                    tags=tags,
                    source="api_monitor"
                ))
            
        except Exception as e:
            logger.error(f"收集API指标失败: {e}")
    
    def _collect_alert_metrics(self, timestamp: datetime):
        """收集告警指标"""
        try:
            alert_stats = self.alert_manager.get_alert_stats()
            
            # 告警总数
            self._add_metric_point(MetricPoint(
                timestamp=timestamp,
                metric_name="alerts.total",
                value=alert_stats.get('total_alerts', 0),
                source="alert_manager"
            ))
            
            # 活跃告警数
            self._add_metric_point(MetricPoint(
                timestamp=timestamp,
                metric_name="alerts.active",
                value=alert_stats.get('active_alerts', 0),
                source="alert_manager"
            ))
            
            # 按级别统计
            by_level = alert_stats.get('by_level', {})
            for level, count in by_level.items():
                self._add_metric_point(MetricPoint(
                    timestamp=timestamp,
                    metric_name="alerts.by_level",
                    value=count,
                    tags={'level': level},
                    source="alert_manager"
                ))
            
            # 解决率
            self._add_metric_point(MetricPoint(
                timestamp=timestamp,
                metric_name="alerts.resolution_rate_percent",
                value=alert_stats.get('resolution_rate', 0),
                source="alert_manager"
            ))
            
        except Exception as e:
            logger.error(f"收集告警指标失败: {e}")
    
    def _collect_custom_metrics(self, timestamp: datetime):
        """收集自定义指标"""
        for collector_name, collector_func in self.custom_collectors.items():
            try:
                metrics = collector_func()
                for metric_name, value in metrics.items():
                    self._add_metric_point(MetricPoint(
                        timestamp=timestamp,
                        metric_name=metric_name,
                        value=value,
                        source=collector_name
                    ))
            except Exception as e:
                logger.error(f"收集自定义指标失败 {collector_name}: {e}")
    
    def _add_metric_point(self, point: MetricPoint):
        """添加指标数据点"""
        with self._lock:
            # 生成指标键（包含标签）
            metric_key = self._generate_metric_key(point.metric_name, point.tags)
            self.metrics_data[metric_key].append(point)
    
    def _generate_metric_key(self, metric_name: str, tags: Dict[str, str]) -> str:
        """生成指标键"""
        if not tags:
            return metric_name
        
        tag_str = ','.join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{metric_name}{{{tag_str}}}"
    
    def _cleanup_old_data(self):
        """清理过期数据"""
        with self._lock:
            cutoff_time = datetime.now() - self.retention_period
            
            for metric_key, points in self.metrics_data.items():
                # 过滤掉过期的数据点
                valid_points = deque(
                    (p for p in points if p.timestamp >= cutoff_time),
                    maxlen=self.max_points_per_metric
                )
                self.metrics_data[metric_key] = valid_points
            
            # 删除空的指标
            empty_metrics = [k for k, v in self.metrics_data.items() if not v]
            for k in empty_metrics:
                del self.metrics_data[k]
            
            logger.debug(f"数据清理完成，保留 {len(self.metrics_data)} 个指标")
    
    def query_metrics(self, 
                     metric_name: str,
                     tags: Dict[str, str] = None,
                     start_time: datetime = None,
                     end_time: datetime = None) -> List[MetricPoint]:
        """查询指标数据
        
        Args:
            metric_name: 指标名称
            tags: 标签过滤
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            List[MetricPoint]: 指标数据点列表
        """
        with self._lock:
            metric_key = self._generate_metric_key(metric_name, tags or {})
            points = self.metrics_data.get(metric_key, deque())
            
            # 时间过滤
            if start_time or end_time:
                filtered_points = []
                for point in points:
                    if start_time and point.timestamp < start_time:
                        continue
                    if end_time and point.timestamp > end_time:
                        continue
                    filtered_points.append(point)
                return filtered_points
            
            return list(points)
    
    def get_metric_names(self) -> List[str]:
        """获取所有指标名称"""
        with self._lock:
            names = set()
            for metric_key in self.metrics_data.keys():
                # 提取指标名称（去掉标签部分）
                if '{' in metric_key:
                    name = metric_key.split('{')[0]
                else:
                    name = metric_key
                names.add(name)
            return sorted(names)
    
    def get_metric_tags(self, metric_name: str) -> List[Dict[str, str]]:
        """获取指标的所有标签组合"""
        with self._lock:
            tag_combinations = []
            for metric_key in self.metrics_data.keys():
                if metric_key.startswith(metric_name):
                    if '{' in metric_key:
                        # 解析标签
                        tag_part = metric_key.split('{')[1].rstrip('}')
                        tags = {}
                        for tag_pair in tag_part.split(','):
                            if '=' in tag_pair:
                                k, v = tag_pair.split('=', 1)
                                tags[k] = v
                        tag_combinations.append(tags)
                    else:
                        tag_combinations.append({})
            return tag_combinations
    
    def aggregate_metrics(self, 
                         metric_name: str,
                         aggregation: str = 'avg',
                         duration: timedelta = timedelta(minutes=5),
                         tags: Dict[str, str] = None) -> Optional[float]:
        """聚合指标数据
        
        Args:
            metric_name: 指标名称
            aggregation: 聚合方式 ('avg', 'sum', 'min', 'max', 'count')
            duration: 聚合时间窗口
            tags: 标签过滤
            
        Returns:
            float: 聚合结果
        """
        end_time = datetime.now()
        start_time = end_time - duration
        
        points = self.query_metrics(metric_name, tags, start_time, end_time)
        
        if not points:
            return None
        
        values = [p.value for p in points]
        
        if aggregation == 'avg':
            return sum(values) / len(values)
        elif aggregation == 'sum':
            return sum(values)
        elif aggregation == 'min':
            return min(values)
        elif aggregation == 'max':
            return max(values)
        elif aggregation == 'count':
            return len(values)
        else:
            raise ValueError(f"不支持的聚合方式: {aggregation}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取收集器统计信息"""
        with self._lock:
            total_points = sum(len(points) for points in self.metrics_data.values())
            
            return {
                'collector_info': {
                    'running': self._running,
                    'collection_interval': self.collection_interval,
                    'retention_period_days': self.retention_period.days,
                    'max_points_per_metric': self.max_points_per_metric
                },
                'data_info': {
                    'total_metrics': len(self.metrics_data),
                    'total_points': total_points,
                    'unique_metric_names': len(self.get_metric_names()),
                    'registered_monitors': {
                        'system_monitor': self.system_monitor is not None,
                        'data_source_monitor': self.data_source_monitor is not None,
                        'api_monitor': self.api_monitor is not None,
                        'alert_manager': self.alert_manager is not None
                    },
                    'custom_collectors': list(self.custom_collectors.keys())
                }
            }