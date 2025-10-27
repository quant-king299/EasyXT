"""
数据源监控

监控各个数据源的连接状态、响应时间、错误率等指标。
"""

import time
import asyncio
import logging
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class DataSourceStatus(Enum):
    """数据源状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class DataSourceMetrics:
    """数据源指标"""
    timestamp: datetime
    source_name: str
    status: DataSourceStatus
    response_time: float  # 毫秒
    success_count: int = 0
    error_count: int = 0
    total_requests: int = 0
    error_rate: float = 0.0
    last_error: Optional[str] = None
    additional_info: Dict[str, Any] = field(default_factory=dict)


class DataSourceMonitor:
    """数据源监控器"""
    
    def __init__(self, check_interval: int = 60, history_size: int = 1000):
        """初始化数据源监控器
        
        Args:
            check_interval: 检查间隔（秒）
            history_size: 历史数据保存数量
        """
        self.check_interval = check_interval
        self.history_size = history_size
        
        # 数据源配置
        self.data_sources: Dict[str, Dict[str, Any]] = {}
        
        # 监控历史
        self.metrics_history: Dict[str, List[DataSourceMetrics]] = {}
        
        # 运行状态
        self._running = False
        self._monitor_thread = None
        self._lock = threading.RLock()
        
        logger.info(f"数据源监控器初始化完成，检查间隔: {check_interval}秒")
    
    def register_data_source(self, 
                           name: str, 
                           check_func: Callable[[], Dict[str, Any]],
                           timeout: float = 10.0,
                           critical: bool = True):
        """注册数据源
        
        Args:
            name: 数据源名称
            check_func: 检查函数，返回 {'status': bool, 'response_time': float, 'info': dict}
            timeout: 超时时间（秒）
            critical: 是否为关键数据源
        """
        self.data_sources[name] = {
            'check_func': check_func,
            'timeout': timeout,
            'critical': critical,
            'last_check': None,
            'consecutive_failures': 0
        }
        
        # 初始化历史记录
        if name not in self.metrics_history:
            self.metrics_history[name] = []
        
        logger.info(f"注册数据源: {name}, 关键性: {critical}")
    
    def unregister_data_source(self, name: str):
        """注销数据源"""
        if name in self.data_sources:
            del self.data_sources[name]
            logger.info(f"注销数据源: {name}")
    
    def start(self):
        """启动监控"""
        if self._running:
            logger.warning("数据源监控器已在运行")
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="DataSourceMonitor",
            daemon=True
        )
        self._monitor_thread.start()
        logger.info("数据源监控器已启动")
    
    def stop(self):
        """停止监控"""
        if not self._running:
            return
        
        self._running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        
        logger.info("数据源监控器已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                self._check_all_sources()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"数据源监控检查失败: {e}")
                time.sleep(self.check_interval)
    
    def _check_all_sources(self):
        """检查所有数据源"""
        for source_name in list(self.data_sources.keys()):
            try:
                self._check_single_source(source_name)
            except Exception as e:
                logger.error(f"检查数据源 {source_name} 失败: {e}")
    
    def _check_single_source(self, source_name: str):
        """检查单个数据源"""
        source_config = self.data_sources.get(source_name)
        if not source_config:
            return
        
        check_func = source_config['check_func']
        timeout = source_config['timeout']
        
        start_time = time.time()
        status = DataSourceStatus.UNKNOWN
        response_time = 0.0
        error_msg = None
        additional_info = {}
        
        try:
            # 执行检查函数
            result = check_func()
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            if isinstance(result, dict):
                is_success = result.get('status', False)
                if 'response_time' in result:
                    response_time = result['response_time']
                additional_info = result.get('info', {})
                
                if is_success:
                    status = DataSourceStatus.ONLINE
                    source_config['consecutive_failures'] = 0
                else:
                    status = DataSourceStatus.OFFLINE
                    source_config['consecutive_failures'] += 1
                    error_msg = result.get('error', '检查失败')
            else:
                # 简单布尔返回值
                if result:
                    status = DataSourceStatus.ONLINE
                    source_config['consecutive_failures'] = 0
                else:
                    status = DataSourceStatus.OFFLINE
                    source_config['consecutive_failures'] += 1
                    error_msg = '检查返回False'
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            status = DataSourceStatus.OFFLINE
            source_config['consecutive_failures'] += 1
            error_msg = str(e)
            logger.error(f"数据源 {source_name} 检查异常: {e}")
        
        # 判断是否为降级状态
        if (status == DataSourceStatus.ONLINE and 
            response_time > timeout * 1000 * 0.8):  # 响应时间超过80%超时时间
            status = DataSourceStatus.DEGRADED
        
        # 创建指标记录
        metrics = DataSourceMetrics(
            timestamp=datetime.now(),
            source_name=source_name,
            status=status,
            response_time=response_time,
            last_error=error_msg,
            additional_info=additional_info
        )
        
        # 计算成功率和错误率
        self._calculate_rates(source_name, metrics)
        
        # 添加到历史记录
        self._add_metrics(source_name, metrics)
        
        # 更新最后检查时间
        source_config['last_check'] = datetime.now()
    
    def _calculate_rates(self, source_name: str, metrics: DataSourceMetrics):
        """计算成功率和错误率"""
        history = self.metrics_history.get(source_name, [])
        
        # 获取最近1小时的数据
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_metrics = [m for m in history if m.timestamp >= one_hour_ago]
        
        if recent_metrics:
            success_count = sum(1 for m in recent_metrics 
                              if m.status == DataSourceStatus.ONLINE)
            total_count = len(recent_metrics)
            
            metrics.success_count = success_count
            metrics.error_count = total_count - success_count
            metrics.total_requests = total_count
            metrics.error_rate = (total_count - success_count) / total_count * 100
    
    def _add_metrics(self, source_name: str, metrics: DataSourceMetrics):
        """添加指标到历史记录"""
        with self._lock:
            if source_name not in self.metrics_history:
                self.metrics_history[source_name] = []
            
            self.metrics_history[source_name].append(metrics)
            
            # 保持历史记录大小
            if len(self.metrics_history[source_name]) > self.history_size:
                self.metrics_history[source_name].pop(0)
    
    def get_current_status(self, source_name: str = None) -> Dict[str, Any]:
        """获取当前状态
        
        Args:
            source_name: 数据源名称，None表示获取所有
            
        Returns:
            Dict: 状态信息
        """
        with self._lock:
            if source_name:
                history = self.metrics_history.get(source_name, [])
                if history:
                    latest = history[-1]
                    return {
                        'source_name': source_name,
                        'status': latest.status.value,
                        'response_time': latest.response_time,
                        'error_rate': latest.error_rate,
                        'last_check': latest.timestamp.isoformat(),
                        'last_error': latest.last_error,
                        'consecutive_failures': self.data_sources.get(source_name, {}).get('consecutive_failures', 0)
                    }
                return {'source_name': source_name, 'status': 'no_data'}
            
            # 获取所有数据源状态
            result = {}
            for name in self.data_sources.keys():
                result[name] = self.get_current_status(name)
            
            return result
    
    def get_metrics_history(self, 
                          source_name: str, 
                          duration: timedelta = None) -> List[DataSourceMetrics]:
        """获取历史指标
        
        Args:
            source_name: 数据源名称
            duration: 时间范围
            
        Returns:
            List[DataSourceMetrics]: 指标列表
        """
        with self._lock:
            history = self.metrics_history.get(source_name, [])
            
            if duration is None:
                return history.copy()
            
            cutoff_time = datetime.now() - duration
            return [m for m in history if m.timestamp >= cutoff_time]
    
    def get_availability_stats(self, 
                             source_name: str, 
                             duration: timedelta = timedelta(hours=24)) -> Dict[str, Any]:
        """获取可用性统计
        
        Args:
            source_name: 数据源名称
            duration: 统计时间范围
            
        Returns:
            Dict: 可用性统计
        """
        history = self.get_metrics_history(source_name, duration)
        
        if not history:
            return {
                'availability': 0.0,
                'avg_response_time': 0.0,
                'total_checks': 0,
                'successful_checks': 0,
                'failed_checks': 0
            }
        
        total_checks = len(history)
        successful_checks = sum(1 for m in history 
                              if m.status == DataSourceStatus.ONLINE)
        failed_checks = total_checks - successful_checks
        
        availability = (successful_checks / total_checks) * 100
        
        # 计算平均响应时间（仅成功的请求）
        successful_metrics = [m for m in history 
                            if m.status == DataSourceStatus.ONLINE]
        avg_response_time = 0.0
        if successful_metrics:
            avg_response_time = sum(m.response_time for m in successful_metrics) / len(successful_metrics)
        
        return {
            'availability': availability,
            'avg_response_time': avg_response_time,
            'total_checks': total_checks,
            'successful_checks': successful_checks,
            'failed_checks': failed_checks,
            'uptime_percentage': availability,
            'downtime_count': failed_checks
        }
    
    def check_alerts(self, alert_rules: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检查告警规则
        
        Args:
            alert_rules: 告警规则配置
            
        Returns:
            List: 告警列表
        """
        alerts = []
        
        for source_name in self.data_sources.keys():
            current_status = self.get_current_status(source_name)
            source_rules = alert_rules.get(source_name, alert_rules.get('default', {}))
            
            # 检查可用性告警
            if 'availability_threshold' in source_rules:
                stats = self.get_availability_stats(source_name, timedelta(hours=1))
                threshold = source_rules['availability_threshold']
                
                if stats['availability'] < threshold:
                    alerts.append({
                        'type': 'availability_low',
                        'source': source_name,
                        'level': 'critical' if self.data_sources[source_name]['critical'] else 'warning',
                        'message': f'数据源 {source_name} 可用性过低: {stats["availability"]:.1f}%',
                        'value': stats['availability'],
                        'threshold': threshold,
                        'timestamp': datetime.now()
                    })
            
            # 检查响应时间告警
            if 'response_time_threshold' in source_rules:
                threshold = source_rules['response_time_threshold']
                current_rt = current_status.get('response_time', 0)
                
                if current_rt > threshold:
                    alerts.append({
                        'type': 'response_time_high',
                        'source': source_name,
                        'level': 'warning',
                        'message': f'数据源 {source_name} 响应时间过长: {current_rt:.1f}ms',
                        'value': current_rt,
                        'threshold': threshold,
                        'timestamp': datetime.now()
                    })
            
            # 检查连续失败告警
            if 'max_consecutive_failures' in source_rules:
                threshold = source_rules['max_consecutive_failures']
                failures = self.data_sources[source_name].get('consecutive_failures', 0)
                
                if failures >= threshold:
                    alerts.append({
                        'type': 'consecutive_failures',
                        'source': source_name,
                        'level': 'critical',
                        'message': f'数据源 {source_name} 连续失败 {failures} 次',
                        'value': failures,
                        'threshold': threshold,
                        'timestamp': datetime.now()
                    })
        
        return alerts
    
    def get_stats(self) -> Dict[str, Any]:
        """获取监控统计信息"""
        with self._lock:
            stats = {
                'monitor_info': {
                    'running': self._running,
                    'check_interval': self.check_interval,
                    'registered_sources': len(self.data_sources),
                    'critical_sources': sum(1 for s in self.data_sources.values() if s['critical'])
                },
                'sources': {}
            }
            
            # 获取每个数据源的统计
            for source_name in self.data_sources.keys():
                current_status = self.get_current_status(source_name)
                availability_stats = self.get_availability_stats(source_name)
                
                stats['sources'][source_name] = {
                    'current_status': current_status,
                    'availability_24h': availability_stats,
                    'is_critical': self.data_sources[source_name]['critical']
                }
            
            return stats


# 预定义的数据源检查函数
def create_http_check(url: str, timeout: float = 10.0) -> Callable[[], Dict[str, Any]]:
    """创建HTTP检查函数"""
    import requests
    
    def check():
        try:
            start_time = time.time()
            response = requests.get(url, timeout=timeout)
            response_time = (time.time() - start_time) * 1000
            
            return {
                'status': response.status_code == 200,
                'response_time': response_time,
                'info': {
                    'status_code': response.status_code,
                    'content_length': len(response.content)
                },
                'error': None if response.status_code == 200 else f'HTTP {response.status_code}'
            }
        except Exception as e:
            return {
                'status': False,
                'response_time': timeout * 1000,
                'info': {},
                'error': str(e)
            }
    
    return check


def create_tcp_check(host: str, port: int, timeout: float = 10.0) -> Callable[[], Dict[str, Any]]:
    """创建TCP连接检查函数"""
    import socket
    
    def check():
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            response_time = (time.time() - start_time) * 1000
            
            return {
                'status': result == 0,
                'response_time': response_time,
                'info': {'host': host, 'port': port},
                'error': None if result == 0 else f'连接失败: {result}'
            }
        except Exception as e:
            return {
                'status': False,
                'response_time': timeout * 1000,
                'info': {'host': host, 'port': port},
                'error': str(e)
            }
    
    return check