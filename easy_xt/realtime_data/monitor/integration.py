"""
监控系统集成

将所有监控组件整合在一起，提供统一的监控服务。
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import timedelta

from .system_monitor import SystemMonitor
from .data_source_monitor import DataSourceMonitor, create_tcp_check, create_http_check
from .api_monitor import APIMonitor
from .alert_manager import (AlertManager, AlertRule, AlertLevel, 
                           create_system_alert_rules, create_api_alert_rules, 
                           create_data_source_alert_rules)
from .metrics_collector import MetricsCollector
from .monitor_dashboard import MonitorDashboard

logger = logging.getLogger(__name__)


class MonitoringService:
    """监控服务集成类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化监控服务
        
        Args:
            config: 监控配置
        """
        self.config = config or {}
        
        # 监控组件
        self.system_monitor: Optional[SystemMonitor] = None
        self.data_source_monitor: Optional[DataSourceMonitor] = None
        self.api_monitor: Optional[APIMonitor] = None
        self.alert_manager: Optional[AlertManager] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        self.dashboard: Optional[MonitorDashboard] = None
        
        # 运行状态
        self._running = False
        
        logger.info("监控服务初始化完成")
    
    async def start(self):
        """启动监控服务"""
        if self._running:
            logger.warning("监控服务已在运行")
            return
        
        try:
            # 初始化各组件
            await self._init_components()
            
            # 启动监控组件
            await self._start_components()
            
            # 注册数据源
            self._register_data_sources()
            
            # 设置告警规则
            self._setup_alert_rules()
            
            self._running = True
            logger.info("监控服务启动成功")
            
        except Exception as e:
            logger.error(f"监控服务启动失败: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """停止监控服务"""
        if not self._running:
            return
        
        try:
            # 停止各组件
            if self.dashboard:
                await self.dashboard.stop()
            
            if self.metrics_collector:
                self.metrics_collector.stop()
            
            if self.system_monitor:
                self.system_monitor.stop()
            
            if self.data_source_monitor:
                self.data_source_monitor.stop()
            
            self._running = False
            logger.info("监控服务已停止")
            
        except Exception as e:
            logger.error(f"停止监控服务失败: {e}")
    
    async def _init_components(self):
        """初始化监控组件"""
        # 系统监控器
        system_config = self.config.get('system_monitor', {})
        self.system_monitor = SystemMonitor(
            interval=system_config.get('interval', 30),
            history_size=system_config.get('history_size', 1000)
        )
        
        # 数据源监控器
        datasource_config = self.config.get('data_source_monitor', {})
        self.data_source_monitor = DataSourceMonitor(
            check_interval=datasource_config.get('check_interval', 60),
            history_size=datasource_config.get('history_size', 1000)
        )
        
        # API监控器
        api_config = self.config.get('api_monitor', {})
        self.api_monitor = APIMonitor(
            history_size=api_config.get('history_size', 10000),
            window_size=api_config.get('window_size', 1000)
        )
        
        # 告警管理器
        alert_config = self.config.get('alert_manager', {})
        self.alert_manager = AlertManager(alert_config)
        
        # 指标收集器
        metrics_config = self.config.get('metrics_collector', {})
        self.metrics_collector = MetricsCollector(
            collection_interval=metrics_config.get('collection_interval', 30),
            retention_period=timedelta(days=metrics_config.get('retention_days', 7)),
            max_points_per_metric=metrics_config.get('max_points_per_metric', 10000)
        )
        
        # 注册监控器到指标收集器
        self.metrics_collector.register_system_monitor(self.system_monitor)
        self.metrics_collector.register_data_source_monitor(self.data_source_monitor)
        self.metrics_collector.register_api_monitor(self.api_monitor)
        self.metrics_collector.register_alert_manager(self.alert_manager)
        
        # 监控仪表板
        dashboard_config = self.config.get('dashboard', {})
        self.dashboard = MonitorDashboard(
            host=dashboard_config.get('host', '0.0.0.0'),
            port=dashboard_config.get('port', 8081),
            enable_cors=dashboard_config.get('enable_cors', True)
        )
        
        # 注册组件到仪表板
        self.dashboard.register_system_monitor(self.system_monitor)
        self.dashboard.register_data_source_monitor(self.data_source_monitor)
        self.dashboard.register_api_monitor(self.api_monitor)
        self.dashboard.register_alert_manager(self.alert_manager)
        self.dashboard.register_metrics_collector(self.metrics_collector)
    
    async def _start_components(self):
        """启动监控组件"""
        # 启动系统监控
        self.system_monitor.start()
        
        # 启动数据源监控
        self.data_source_monitor.start()
        
        # 启动指标收集
        self.metrics_collector.start()
        
        # 启动仪表板
        await self.dashboard.start()
    
    def _register_data_sources(self):
        """注册数据源"""
        data_sources = self.config.get('data_sources', {})
        
        for name, config in data_sources.items():
            source_type = config.get('type')
            
            if source_type == 'tcp':
                check_func = create_tcp_check(
                    host=config['host'],
                    port=config['port'],
                    timeout=config.get('timeout', 10.0)
                )
            elif source_type == 'http':
                check_func = create_http_check(
                    url=config['url'],
                    timeout=config.get('timeout', 10.0)
                )
            else:
                logger.warning(f"未知的数据源类型: {source_type}")
                continue
            
            self.data_source_monitor.register_data_source(
                name=name,
                check_func=check_func,
                timeout=config.get('timeout', 10.0),
                critical=config.get('critical', True)
            )
            
            logger.info(f"注册数据源: {name} ({source_type})")
    
    def _setup_alert_rules(self):
        """设置告警规则"""
        # 添加系统告警规则
        for rule in create_system_alert_rules():
            self.alert_manager.add_rule(rule)
        
        # 添加API告警规则
        for rule in create_api_alert_rules():
            self.alert_manager.add_rule(rule)
        
        # 添加数据源告警规则
        for rule in create_data_source_alert_rules():
            self.alert_manager.add_rule(rule)
        
        # 添加自定义告警规则
        custom_rules = self.config.get('alert_rules', [])
        for rule_config in custom_rules:
            rule = AlertRule(
                name=rule_config['name'],
                condition=rule_config['condition'],
                level=AlertLevel(rule_config['level']),
                threshold=rule_config['threshold'],
                duration=rule_config.get('duration', 0),
                cooldown=rule_config.get('cooldown', 300),
                notification_channels=rule_config.get('notification_channels', [])
            )
            self.alert_manager.add_rule(rule)
        
        logger.info(f"设置告警规则完成，共 {len(self.alert_manager.rules)} 条规则")
    
    def get_api_monitor(self) -> APIMonitor:
        """获取API监控器"""
        return self.api_monitor
    
    def get_alert_manager(self) -> AlertManager:
        """获取告警管理器"""
        return self.alert_manager
    
    def get_metrics_collector(self) -> MetricsCollector:
        """获取指标收集器"""
        return self.metrics_collector
    
    async def check_and_trigger_alerts(self):
        """检查并触发告警"""
        try:
            # 检查系统告警
            if self.system_monitor:
                system_thresholds = {
                    'cpu': 80.0,
                    'memory': 85.0,
                    'disk': 90.0
                }
                system_alerts = self.system_monitor.check_thresholds(system_thresholds)
                
                for alert_info in system_alerts:
                    self.alert_manager.trigger_alert(
                        rule_name=alert_info['type'],
                        title=f"系统{alert_info['type']}告警",
                        message=alert_info['message'],
                        value=alert_info['value'],
                        threshold=alert_info['threshold'],
                        source='system_monitor'
                    )
            
            # 检查数据源告警
            if self.data_source_monitor:
                datasource_rules = {
                    'default': {
                        'availability_threshold': 95.0,
                        'response_time_threshold': 5000.0,
                        'max_consecutive_failures': 3
                    }
                }
                datasource_alerts = self.data_source_monitor.check_alerts(datasource_rules)
                
                for alert_info in datasource_alerts:
                    self.alert_manager.trigger_alert(
                        rule_name=alert_info['type'],
                        title=f"数据源{alert_info['type']}告警",
                        message=alert_info['message'],
                        value=alert_info['value'],
                        threshold=alert_info['threshold'],
                        source='data_source_monitor',
                        tags={'source': alert_info.get('source', '')}
                    )
            
            # 检查API告警
            if self.api_monitor:
                api_rules = {
                    'error_rate_threshold': 5.0,
                    'avg_response_time_threshold': 2000.0,
                    'requests_per_second_threshold': 1000.0
                }
                api_alerts = self.api_monitor.check_alerts(api_rules)
                
                for alert_info in api_alerts:
                    self.alert_manager.trigger_alert(
                        rule_name=alert_info['type'],
                        title=f"API{alert_info['type']}告警",
                        message=alert_info['message'],
                        value=alert_info['value'],
                        threshold=alert_info['threshold'],
                        source='api_monitor'
                    )
            
        except Exception as e:
            logger.error(f"检查告警失败: {e}")
    
    async def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        health = {
            'overall': 'healthy',
            'timestamp': logger.info.__globals__['datetime'].datetime.now().isoformat(),
            'components': {}
        }
        
        # 检查各组件状态
        if self.system_monitor:
            health['components']['system_monitor'] = {
                'status': 'running' if self.system_monitor._running else 'stopped'
            }
        
        if self.data_source_monitor:
            health['components']['data_source_monitor'] = {
                'status': 'running' if self.data_source_monitor._running else 'stopped'
            }
        
        if self.metrics_collector:
            health['components']['metrics_collector'] = {
                'status': 'running' if self.metrics_collector._running else 'stopped'
            }
        
        if self.dashboard:
            health['components']['dashboard'] = {
                'status': 'running' if self.dashboard.app else 'stopped'
            }
        
        # 检查是否有组件异常
        unhealthy_count = sum(1 for comp in health['components'].values() 
                             if comp['status'] != 'running')
        
        if unhealthy_count > 0:
            health['overall'] = 'degraded' if unhealthy_count < len(health['components']) else 'unhealthy'
        
        return health
    
    def get_stats(self) -> Dict[str, Any]:
        """获取监控服务统计信息"""
        stats = {
            'service_info': {
                'running': self._running,
                'components_count': 0
            }
        }
        
        if self.system_monitor:
            stats['system_monitor'] = self.system_monitor.get_stats()
            stats['service_info']['components_count'] += 1
        
        if self.data_source_monitor:
            stats['data_source_monitor'] = self.data_source_monitor.get_stats()
            stats['service_info']['components_count'] += 1
        
        if self.api_monitor:
            stats['api_monitor'] = self.api_monitor.get_stats()
            stats['service_info']['components_count'] += 1
        
        if self.alert_manager:
            stats['alert_manager'] = self.alert_manager.get_stats()
            stats['service_info']['components_count'] += 1
        
        if self.metrics_collector:
            stats['metrics_collector'] = self.metrics_collector.get_stats()
            stats['service_info']['components_count'] += 1
        
        if self.dashboard:
            stats['dashboard'] = self.dashboard.get_stats()
            stats['service_info']['components_count'] += 1
        
        return stats


# 默认配置
DEFAULT_MONITORING_CONFIG = {
    'system_monitor': {
        'interval': 30,
        'history_size': 1000
    },
    'data_source_monitor': {
        'check_interval': 60,
        'history_size': 1000
    },
    'api_monitor': {
        'history_size': 10000,
        'window_size': 1000
    },
    'metrics_collector': {
        'collection_interval': 30,
        'retention_days': 7,
        'max_points_per_metric': 10000
    },
    'dashboard': {
        'host': '0.0.0.0',
        'port': 8081,
        'enable_cors': True
    },
    'alert_manager': {
        'max_history_size': 10000,
        'notification_channels': {
            'webhook': {
                'type': 'webhook',
                'url': 'http://localhost:8080/webhook/alerts',
                'method': 'POST',
                'timeout': 10
            }
        }
    },
    'data_sources': {
        'tdx_server_1': {
            'type': 'tcp',
            'host': '114.80.63.12',
            'port': 7709,
            'timeout': 10.0,
            'critical': True
        },
        'tdx_server_2': {
            'type': 'tcp',
            'host': '180.153.39.51',
            'port': 7709,
            'timeout': 10.0,
            'critical': True
        }
    },
    'alert_rules': [
        {
            'name': 'high_memory_usage',
            'condition': '内存使用率 > 90%',
            'level': 'critical',
            'threshold': 90.0,
            'cooldown': 600,
            'notification_channels': ['webhook']
        }
    ]
}


async def create_monitoring_service(config: Dict[str, Any] = None) -> MonitoringService:
    """创建监控服务的便捷函数
    
    Args:
        config: 监控配置，None时使用默认配置
        
    Returns:
        MonitoringService: 监控服务实例
    """
    if config is None:
        config = DEFAULT_MONITORING_CONFIG
    
    service = MonitoringService(config)
    await service.start()
    return service