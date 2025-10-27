"""
API监控

监控API接口的响应时间、成功率、错误率等指标。
"""

import time
import logging
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics

logger = logging.getLogger(__name__)


@dataclass
class APIMetrics:
    """API指标"""
    timestamp: datetime
    endpoint: str
    method: str
    status_code: int
    response_time: float  # 毫秒
    request_size: int = 0
    response_size: int = 0
    user_agent: str = ""
    client_ip: str = ""
    error_message: str = ""


class APIMonitor:
    """API监控器"""
    
    def __init__(self, history_size: int = 10000, window_size: int = 1000):
        """初始化API监控器
        
        Args:
            history_size: 历史记录保存数量
            window_size: 滑动窗口大小（用于实时统计）
        """
        self.history_size = history_size
        self.window_size = window_size
        
        # 指标历史记录
        self.metrics_history: List[APIMetrics] = []
        
        # 滑动窗口（用于快速统计）
        self.sliding_window: deque = deque(maxlen=window_size)
        
        # 实时统计
        self.endpoint_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'total_requests': 0,
            'success_requests': 0,
            'error_requests': 0,
            'total_response_time': 0.0,
            'min_response_time': float('inf'),
            'max_response_time': 0.0,
            'response_times': deque(maxlen=100),  # 保存最近100次响应时间
            'status_codes': defaultdict(int),
            'last_request': None
        })
        
        self._lock = threading.RLock()
        
        logger.info(f"API监控器初始化完成，历史记录: {history_size}, 窗口大小: {window_size}")
    
    def record_request(self, 
                      endpoint: str,
                      method: str,
                      status_code: int,
                      response_time: float,
                      request_size: int = 0,
                      response_size: int = 0,
                      user_agent: str = "",
                      client_ip: str = "",
                      error_message: str = ""):
        """记录API请求
        
        Args:
            endpoint: API端点
            method: HTTP方法
            status_code: 状态码
            response_time: 响应时间（毫秒）
            request_size: 请求大小（字节）
            response_size: 响应大小（字节）
            user_agent: 用户代理
            client_ip: 客户端IP
            error_message: 错误信息
        """
        metrics = APIMetrics(
            timestamp=datetime.now(),
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time=response_time,
            request_size=request_size,
            response_size=response_size,
            user_agent=user_agent,
            client_ip=client_ip,
            error_message=error_message
        )
        
        self._add_metrics(metrics)
        self._update_stats(metrics)
    
    def _add_metrics(self, metrics: APIMetrics):
        """添加指标到历史记录"""
        with self._lock:
            self.metrics_history.append(metrics)
            self.sliding_window.append(metrics)
            
            # 保持历史记录大小
            if len(self.metrics_history) > self.history_size:
                self.metrics_history.pop(0)
    
    def _update_stats(self, metrics: APIMetrics):
        """更新实时统计"""
        with self._lock:
            endpoint_key = f"{metrics.method} {metrics.endpoint}"
            stats = self.endpoint_stats[endpoint_key]
            
            # 更新计数
            stats['total_requests'] += 1
            if 200 <= metrics.status_code < 400:
                stats['success_requests'] += 1
            else:
                stats['error_requests'] += 1
            
            # 更新响应时间统计
            stats['total_response_time'] += metrics.response_time
            stats['min_response_time'] = min(stats['min_response_time'], metrics.response_time)
            stats['max_response_time'] = max(stats['max_response_time'], metrics.response_time)
            stats['response_times'].append(metrics.response_time)
            
            # 更新状态码统计
            stats['status_codes'][metrics.status_code] += 1
            
            # 更新最后请求时间
            stats['last_request'] = metrics.timestamp
    
    def get_endpoint_stats(self, endpoint: str = None, method: str = None) -> Dict[str, Any]:
        """获取端点统计信息
        
        Args:
            endpoint: API端点，None表示所有
            method: HTTP方法，None表示所有
            
        Returns:
            Dict: 统计信息
        """
        with self._lock:
            if endpoint and method:
                key = f"{method} {endpoint}"
                stats = self.endpoint_stats.get(key, {})
                return self._calculate_endpoint_metrics(key, stats)
            
            # 返回所有端点统计
            result = {}
            for key, stats in self.endpoint_stats.items():
                if endpoint and not key.endswith(f" {endpoint}"):
                    continue
                if method and not key.startswith(f"{method} "):
                    continue
                
                result[key] = self._calculate_endpoint_metrics(key, stats)
            
            return result
    
    def _calculate_endpoint_metrics(self, key: str, stats: Dict[str, Any]) -> Dict[str, Any]:
        """计算端点指标"""
        if not stats or stats['total_requests'] == 0:
            return {
                'endpoint': key,
                'total_requests': 0,
                'success_rate': 0.0,
                'error_rate': 0.0,
                'avg_response_time': 0.0,
                'min_response_time': 0.0,
                'max_response_time': 0.0,
                'p95_response_time': 0.0,
                'p99_response_time': 0.0,
                'requests_per_minute': 0.0,
                'status_codes': {},
                'last_request': None
            }
        
        total = stats['total_requests']
        success = stats['success_requests']
        error = stats['error_requests']
        
        # 计算成功率和错误率
        success_rate = (success / total) * 100
        error_rate = (error / total) * 100
        
        # 计算平均响应时间
        avg_response_time = stats['total_response_time'] / total
        
        # 计算百分位数
        response_times = list(stats['response_times'])
        p95_response_time = 0.0
        p99_response_time = 0.0
        
        if response_times:
            response_times.sort()
            p95_index = int(len(response_times) * 0.95)
            p99_index = int(len(response_times) * 0.99)
            
            if p95_index < len(response_times):
                p95_response_time = response_times[p95_index]
            if p99_index < len(response_times):
                p99_response_time = response_times[p99_index]
        
        # 计算每分钟请求数
        requests_per_minute = 0.0
        if stats['last_request']:
            time_diff = (datetime.now() - stats['last_request']).total_seconds()
            if time_diff > 0:
                requests_per_minute = (total / time_diff) * 60
        
        return {
            'endpoint': key,
            'total_requests': total,
            'success_requests': success,
            'error_requests': error,
            'success_rate': success_rate,
            'error_rate': error_rate,
            'avg_response_time': avg_response_time,
            'min_response_time': stats['min_response_time'] if stats['min_response_time'] != float('inf') else 0.0,
            'max_response_time': stats['max_response_time'],
            'p95_response_time': p95_response_time,
            'p99_response_time': p99_response_time,
            'requests_per_minute': requests_per_minute,
            'status_codes': dict(stats['status_codes']),
            'last_request': stats['last_request'].isoformat() if stats['last_request'] else None
        }
    
    def get_overall_stats(self, duration: timedelta = None) -> Dict[str, Any]:
        """获取整体统计信息
        
        Args:
            duration: 统计时间范围
            
        Returns:
            Dict: 整体统计
        """
        with self._lock:
            # 获取指定时间范围内的指标
            if duration:
                cutoff_time = datetime.now() - duration
                metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
            else:
                metrics = list(self.sliding_window)
            
            if not metrics:
                return {
                    'total_requests': 0,
                    'success_rate': 0.0,
                    'error_rate': 0.0,
                    'avg_response_time': 0.0,
                    'requests_per_second': 0.0,
                    'unique_endpoints': 0,
                    'unique_clients': 0
                }
            
            total_requests = len(metrics)
            success_requests = sum(1 for m in metrics if 200 <= m.status_code < 400)
            error_requests = total_requests - success_requests
            
            success_rate = (success_requests / total_requests) * 100
            error_rate = (error_requests / total_requests) * 100
            
            # 平均响应时间
            avg_response_time = sum(m.response_time for m in metrics) / total_requests
            
            # 每秒请求数
            time_span = (metrics[-1].timestamp - metrics[0].timestamp).total_seconds()
            requests_per_second = total_requests / time_span if time_span > 0 else 0
            
            # 唯一端点和客户端数
            unique_endpoints = len(set(f"{m.method} {m.endpoint}" for m in metrics))
            unique_clients = len(set(m.client_ip for m in metrics if m.client_ip))
            
            return {
                'total_requests': total_requests,
                'success_requests': success_requests,
                'error_requests': error_requests,
                'success_rate': success_rate,
                'error_rate': error_rate,
                'avg_response_time': avg_response_time,
                'requests_per_second': requests_per_second,
                'unique_endpoints': unique_endpoints,
                'unique_clients': unique_clients,
                'time_range': {
                    'start': metrics[0].timestamp.isoformat(),
                    'end': metrics[-1].timestamp.isoformat(),
                    'duration_seconds': time_span
                }
            }
    
    def get_slow_requests(self, threshold: float = 1000.0, limit: int = 10) -> List[Dict[str, Any]]:
        """获取慢请求列表
        
        Args:
            threshold: 响应时间阈值（毫秒）
            limit: 返回数量限制
            
        Returns:
            List: 慢请求列表
        """
        with self._lock:
            slow_requests = [
                {
                    'timestamp': m.timestamp.isoformat(),
                    'endpoint': f"{m.method} {m.endpoint}",
                    'response_time': m.response_time,
                    'status_code': m.status_code,
                    'client_ip': m.client_ip,
                    'user_agent': m.user_agent[:100] if m.user_agent else "",
                    'error_message': m.error_message
                }
                for m in self.metrics_history
                if m.response_time > threshold
            ]
            
            # 按响应时间降序排序
            slow_requests.sort(key=lambda x: x['response_time'], reverse=True)
            
            return slow_requests[:limit]
    
    def get_error_requests(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取错误请求列表
        
        Args:
            limit: 返回数量限制
            
        Returns:
            List: 错误请求列表
        """
        with self._lock:
            error_requests = [
                {
                    'timestamp': m.timestamp.isoformat(),
                    'endpoint': f"{m.method} {m.endpoint}",
                    'status_code': m.status_code,
                    'response_time': m.response_time,
                    'client_ip': m.client_ip,
                    'user_agent': m.user_agent[:100] if m.user_agent else "",
                    'error_message': m.error_message
                }
                for m in self.metrics_history
                if m.status_code >= 400 or m.error_message
            ]
            
            # 按时间降序排序
            error_requests.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return error_requests[:limit]
    
    def check_alerts(self, alert_rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查告警规则
        
        Args:
            alert_rules: 告警规则配置
            
        Returns:
            List: 告警列表
        """
        alerts = []
        overall_stats = self.get_overall_stats(timedelta(minutes=5))  # 最近5分钟
        
        # 检查整体错误率告警
        if 'error_rate_threshold' in alert_rules:
            threshold = alert_rules['error_rate_threshold']
            if overall_stats['error_rate'] > threshold:
                alerts.append({
                    'type': 'api_error_rate_high',
                    'level': 'critical',
                    'message': f'API错误率过高: {overall_stats["error_rate"]:.1f}%',
                    'value': overall_stats['error_rate'],
                    'threshold': threshold,
                    'timestamp': datetime.now()
                })
        
        # 检查平均响应时间告警
        if 'avg_response_time_threshold' in alert_rules:
            threshold = alert_rules['avg_response_time_threshold']
            if overall_stats['avg_response_time'] > threshold:
                alerts.append({
                    'type': 'api_response_time_high',
                    'level': 'warning',
                    'message': f'API平均响应时间过长: {overall_stats["avg_response_time"]:.1f}ms',
                    'value': overall_stats['avg_response_time'],
                    'threshold': threshold,
                    'timestamp': datetime.now()
                })
        
        # 检查请求量告警
        if 'requests_per_second_threshold' in alert_rules:
            threshold = alert_rules['requests_per_second_threshold']
            if overall_stats['requests_per_second'] > threshold:
                alerts.append({
                    'type': 'api_requests_high',
                    'level': 'warning',
                    'message': f'API请求量过高: {overall_stats["requests_per_second"]:.1f} req/s',
                    'value': overall_stats['requests_per_second'],
                    'threshold': threshold,
                    'timestamp': datetime.now()
                })
        
        # 检查特定端点告警
        endpoint_rules = alert_rules.get('endpoints', {})
        for endpoint_key, endpoint_stats in self.endpoint_stats.items():
            endpoint_rule = endpoint_rules.get(endpoint_key, {})
            
            if 'error_rate_threshold' in endpoint_rule:
                metrics = self._calculate_endpoint_metrics(endpoint_key, endpoint_stats)
                threshold = endpoint_rule['error_rate_threshold']
                
                if metrics['error_rate'] > threshold:
                    alerts.append({
                        'type': 'endpoint_error_rate_high',
                        'endpoint': endpoint_key,
                        'level': 'warning',
                        'message': f'端点 {endpoint_key} 错误率过高: {metrics["error_rate"]:.1f}%',
                        'value': metrics['error_rate'],
                        'threshold': threshold,
                        'timestamp': datetime.now()
                    })
        
        return alerts
    
    def get_stats(self) -> Dict[str, Any]:
        """获取监控统计信息"""
        with self._lock:
            overall_stats = self.get_overall_stats()
            endpoint_stats = self.get_endpoint_stats()
            
            return {
                'monitor_info': {
                    'history_size': len(self.metrics_history),
                    'max_history_size': self.history_size,
                    'window_size': len(self.sliding_window),
                    'max_window_size': self.window_size,
                    'tracked_endpoints': len(self.endpoint_stats)
                },
                'overall_stats': overall_stats,
                'endpoint_stats': endpoint_stats,
                'slow_requests': self.get_slow_requests(1000, 5),
                'error_requests': self.get_error_requests(5)
            }
    
    def clear_history(self):
        """清空历史记录"""
        with self._lock:
            self.metrics_history.clear()
            self.sliding_window.clear()
            self.endpoint_stats.clear()
            logger.info("API监控历史记录已清空")


# 装饰器：自动记录API调用
def monitor_api(api_monitor: APIMonitor, endpoint: str = None):
    """API监控装饰器
    
    Args:
        api_monitor: API监控器实例
        endpoint: 端点名称，None时使用函数名
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            endpoint_name = endpoint or func.__name__
            error_message = ""
            status_code = 200
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status_code = 500
                error_message = str(e)
                raise
            finally:
                response_time = (time.time() - start_time) * 1000
                api_monitor.record_request(
                    endpoint=endpoint_name,
                    method="FUNC",
                    status_code=status_code,
                    response_time=response_time,
                    error_message=error_message
                )
        
        return wrapper
    return decorator