"""
系统性能监控

监控CPU、内存、磁盘、网络等系统资源使用情况。
"""

import time
import psutil
import logging
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """系统指标数据类"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used: int
    memory_total: int
    disk_percent: float
    disk_used: int
    disk_total: int
    network_sent: int
    network_recv: int
    process_count: int
    load_average: List[float]


class SystemMonitor:
    """系统性能监控器"""
    
    def __init__(self, interval: int = 30, history_size: int = 1000):
        """初始化系统监控器
        
        Args:
            interval: 监控间隔（秒）
            history_size: 历史数据保存数量
        """
        self.interval = interval
        self.history_size = history_size
        self.metrics_history: List[SystemMetrics] = []
        
        self._running = False
        self._monitor_thread = None
        self._lock = threading.RLock()
        
        # 网络统计基准值
        self._last_network_stats = None
        
        logger.info(f"系统监控器初始化完成，监控间隔: {interval}秒")
    
    def start(self):
        """启动监控"""
        if self._running:
            logger.warning("系统监控器已在运行")
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="SystemMonitor",
            daemon=True
        )
        self._monitor_thread.start()
        logger.info("系统监控器已启动")
    
    def stop(self):
        """停止监控"""
        if not self._running:
            return
        
        self._running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        
        logger.info("系统监控器已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                metrics = self._collect_metrics()
                self._add_metrics(metrics)
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"系统监控采集失败: {e}")
                time.sleep(self.interval)
    
    def _collect_metrics(self) -> SystemMetrics:
        """采集系统指标"""
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 内存使用情况
        memory = psutil.virtual_memory()
        
        # 磁盘使用情况
        disk = psutil.disk_usage('/')
        
        # 网络统计
        network = psutil.net_io_counters()
        network_sent = network.bytes_sent
        network_recv = network.bytes_recv
        
        # 如果有上次的网络统计，计算增量
        if self._last_network_stats:
            network_sent = network.bytes_sent - self._last_network_stats.bytes_sent
            network_recv = network.bytes_recv - self._last_network_stats.bytes_recv
        
        self._last_network_stats = network
        
        # 进程数量
        process_count = len(psutil.pids())
        
        # 系统负载（Linux/Unix）
        load_average = []
        try:
            if hasattr(psutil, 'getloadavg'):
                load_average = list(psutil.getloadavg())
        except (AttributeError, OSError):
            # Windows系统没有load average
            load_average = [0.0, 0.0, 0.0]
        
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used=memory.used,
            memory_total=memory.total,
            disk_percent=disk.percent,
            disk_used=disk.used,
            disk_total=disk.total,
            network_sent=network_sent,
            network_recv=network_recv,
            process_count=process_count,
            load_average=load_average
        )
    
    def _add_metrics(self, metrics: SystemMetrics):
        """添加指标到历史记录"""
        with self._lock:
            self.metrics_history.append(metrics)
            
            # 保持历史记录大小
            if len(self.metrics_history) > self.history_size:
                self.metrics_history.pop(0)
    
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """获取当前系统指标"""
        with self._lock:
            if self.metrics_history:
                return self.metrics_history[-1]
            return None
    
    def get_metrics_history(self, duration: timedelta = None) -> List[SystemMetrics]:
        """获取历史指标
        
        Args:
            duration: 时间范围，None表示全部历史
            
        Returns:
            List[SystemMetrics]: 指标列表
        """
        with self._lock:
            if duration is None:
                return self.metrics_history.copy()
            
            cutoff_time = datetime.now() - duration
            return [
                m for m in self.metrics_history 
                if m.timestamp >= cutoff_time
            ]
    
    def get_average_metrics(self, duration: timedelta = None) -> Dict[str, float]:
        """获取平均指标
        
        Args:
            duration: 时间范围
            
        Returns:
            Dict: 平均指标
        """
        history = self.get_metrics_history(duration)
        if not history:
            return {}
        
        total_cpu = sum(m.cpu_percent for m in history)
        total_memory = sum(m.memory_percent for m in history)
        total_disk = sum(m.disk_percent for m in history)
        count = len(history)
        
        return {
            'avg_cpu_percent': total_cpu / count,
            'avg_memory_percent': total_memory / count,
            'avg_disk_percent': total_disk / count,
            'sample_count': count
        }
    
    def check_thresholds(self, thresholds: Dict[str, float]) -> List[Dict[str, Any]]:
        """检查阈值告警
        
        Args:
            thresholds: 阈值配置 {'cpu': 80, 'memory': 85, 'disk': 90}
            
        Returns:
            List: 告警列表
        """
        current = self.get_current_metrics()
        if not current:
            return []
        
        alerts = []
        
        # CPU告警
        if 'cpu' in thresholds and current.cpu_percent > thresholds['cpu']:
            alerts.append({
                'type': 'cpu_high',
                'level': 'warning',
                'message': f'CPU使用率过高: {current.cpu_percent:.1f}%',
                'value': current.cpu_percent,
                'threshold': thresholds['cpu'],
                'timestamp': current.timestamp
            })
        
        # 内存告警
        if 'memory' in thresholds and current.memory_percent > thresholds['memory']:
            alerts.append({
                'type': 'memory_high',
                'level': 'warning',
                'message': f'内存使用率过高: {current.memory_percent:.1f}%',
                'value': current.memory_percent,
                'threshold': thresholds['memory'],
                'timestamp': current.timestamp
            })
        
        # 磁盘告警
        if 'disk' in thresholds and current.disk_percent > thresholds['disk']:
            alerts.append({
                'type': 'disk_high',
                'level': 'critical',
                'message': f'磁盘使用率过高: {current.disk_percent:.1f}%',
                'value': current.disk_percent,
                'threshold': thresholds['disk'],
                'timestamp': current.timestamp
            })
        
        return alerts
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            
            return {
                'platform': psutil.LINUX if hasattr(psutil, 'LINUX') else 'unknown',
                'cpu_count': psutil.cpu_count(),
                'cpu_count_logical': psutil.cpu_count(logical=True),
                'memory_total': psutil.virtual_memory().total,
                'disk_total': psutil.disk_usage('/').total,
                'boot_time': boot_time.isoformat(),
                'uptime_seconds': int(uptime.total_seconds()),
                'uptime_human': str(uptime).split('.')[0]  # 去掉微秒
            }
        except Exception as e:
            logger.error(f"获取系统信息失败: {e}")
            return {}
    
    def get_process_info(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取进程信息
        
        Args:
            limit: 返回进程数量限制
            
        Returns:
            List: 进程信息列表
        """
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # 按CPU使用率排序
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            return processes[:limit]
            
        except Exception as e:
            logger.error(f"获取进程信息失败: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """获取监控统计信息"""
        with self._lock:
            current = self.get_current_metrics()
            avg_1h = self.get_average_metrics(timedelta(hours=1))
            
            return {
                'monitor_info': {
                    'running': self._running,
                    'interval': self.interval,
                    'history_size': len(self.metrics_history),
                    'max_history_size': self.history_size
                },
                'current_metrics': current.__dict__ if current else None,
                'average_1h': avg_1h,
                'system_info': self.get_system_info(),
                'top_processes': self.get_process_info(5)
            }


class ProcessMonitor:
    """进程监控器"""
    
    def __init__(self, process_name: str = None, pid: int = None):
        """初始化进程监控器
        
        Args:
            process_name: 进程名称
            pid: 进程ID
        """
        self.process_name = process_name
        self.pid = pid
        self.process = None
        
        self._find_process()
    
    def _find_process(self):
        """查找目标进程"""
        try:
            if self.pid:
                self.process = psutil.Process(self.pid)
            elif self.process_name:
                for proc in psutil.process_iter(['pid', 'name']):
                    if proc.info['name'] == self.process_name:
                        self.process = proc
                        break
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(f"查找进程失败: {e}")
    
    def get_process_metrics(self) -> Optional[Dict[str, Any]]:
        """获取进程指标"""
        if not self.process:
            self._find_process()
        
        if not self.process:
            return None
        
        try:
            with self.process.oneshot():
                return {
                    'pid': self.process.pid,
                    'name': self.process.name(),
                    'status': self.process.status(),
                    'cpu_percent': self.process.cpu_percent(),
                    'memory_percent': self.process.memory_percent(),
                    'memory_info': self.process.memory_info()._asdict(),
                    'num_threads': self.process.num_threads(),
                    'create_time': self.process.create_time(),
                    'cmdline': ' '.join(self.process.cmdline())
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(f"获取进程指标失败: {e}")
            return None
    
    def is_running(self) -> bool:
        """检查进程是否运行"""
        if not self.process:
            self._find_process()
        
        if not self.process:
            return False
        
        try:
            return self.process.is_running()
        except psutil.NoSuchProcess:
            return False