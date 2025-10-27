"""
监控仪表板

提供Web界面展示监控数据和告警信息。
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from aiohttp import web, WSMsgType
import aiohttp_cors
import weakref

from .system_monitor import SystemMonitor
from .data_source_monitor import DataSourceMonitor
from .api_monitor import APIMonitor
from .alert_manager import AlertManager
from .metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)


class MonitorDashboard:
    """监控仪表板"""
    
    def __init__(self, 
                 host: str = "0.0.0.0",
                 port: int = 8081,
                 enable_cors: bool = True):
        """初始化监控仪表板
        
        Args:
            host: 监听地址
            port: 监听端口
            enable_cors: 是否启用CORS
        """
        self.host = host
        self.port = port
        self.enable_cors = enable_cors
        
        # 监控组件
        self.system_monitor: Optional[SystemMonitor] = None
        self.data_source_monitor: Optional[DataSourceMonitor] = None
        self.api_monitor: Optional[APIMonitor] = None
        self.alert_manager: Optional[AlertManager] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        
        # Web应用
        self.app = None
        self.runner = None
        self.site = None
        
        # WebSocket连接管理
        self.websocket_connections: weakref.WeakSet = weakref.WeakSet()
        
        logger.info(f"监控仪表板初始化完成，地址: {host}:{port}")
    
    def register_system_monitor(self, system_monitor: SystemMonitor):
        """注册系统监控器"""
        self.system_monitor = system_monitor
    
    def register_data_source_monitor(self, data_source_monitor: DataSourceMonitor):
        """注册数据源监控器"""
        self.data_source_monitor = data_source_monitor
    
    def register_api_monitor(self, api_monitor: APIMonitor):
        """注册API监控器"""
        self.api_monitor = api_monitor
    
    def register_alert_manager(self, alert_manager: AlertManager):
        """注册告警管理器"""
        self.alert_manager = alert_manager
    
    def register_metrics_collector(self, metrics_collector: MetricsCollector):
        """注册指标收集器"""
        self.metrics_collector = metrics_collector
    
    async def start(self):
        """启动仪表板服务"""
        if self.app:
            logger.warning("监控仪表板已在运行")
            return
        
        # 创建Web应用
        self.app = web.Application()
        
        # 配置CORS
        if self.enable_cors:
            cors = aiohttp_cors.setup(self.app, defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods="*"
                )
            })
        
        # 注册路由
        self._setup_routes()
        
        # 启动服务器
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        
        logger.info(f"监控仪表板已启动: http://{self.host}:{self.port}")
    
    async def stop(self):
        """停止仪表板服务"""
        if self.site:
            await self.site.stop()
        
        if self.runner:
            await self.runner.cleanup()
        
        self.app = None
        self.runner = None
        self.site = None
        
        logger.info("监控仪表板已停止")
    
    def _setup_routes(self):
        """设置路由"""
        # 静态文件
        self.app.router.add_get('/', self._handle_index)
        self.app.router.add_get('/dashboard', self._handle_dashboard)
        
        # API路由
        self.app.router.add_get('/api/health', self._handle_health)
        self.app.router.add_get('/api/overview', self._handle_overview)
        
        # 系统监控API
        self.app.router.add_get('/api/system/current', self._handle_system_current)
        self.app.router.add_get('/api/system/history', self._handle_system_history)
        self.app.router.add_get('/api/system/stats', self._handle_system_stats)
        
        # 数据源监控API
        self.app.router.add_get('/api/datasources/status', self._handle_datasources_status)
        self.app.router.add_get('/api/datasources/stats', self._handle_datasources_stats)
        
        # API监控API
        self.app.router.add_get('/api/api/stats', self._handle_api_stats)
        self.app.router.add_get('/api/api/endpoints', self._handle_api_endpoints)
        self.app.router.add_get('/api/api/errors', self._handle_api_errors)
        
        # 告警API
        self.app.router.add_get('/api/alerts/active', self._handle_alerts_active)
        self.app.router.add_get('/api/alerts/history', self._handle_alerts_history)
        self.app.router.add_get('/api/alerts/stats', self._handle_alerts_stats)
        self.app.router.add_post('/api/alerts/resolve', self._handle_alerts_resolve)
        
        # 指标API
        self.app.router.add_get('/api/metrics/names', self._handle_metrics_names)
        self.app.router.add_get('/api/metrics/query', self._handle_metrics_query)
        
        # WebSocket
        self.app.router.add_get('/ws', self._handle_websocket)
    
    async def _handle_index(self, request):
        """首页"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>EasyXT 监控仪表板</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
                .nav { margin: 20px 0; }
                .nav a { margin-right: 20px; text-decoration: none; color: #007bff; }
                .nav a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>EasyXT 实时数据监控系统</h1>
                <p>监控系统性能、数据源状态、API指标和告警信息</p>
            </div>
            
            <div class="nav">
                <a href="/dashboard">监控仪表板</a>
                <a href="/api/health">健康检查</a>
                <a href="/api/overview">系统概览</a>
            </div>
            
            <h2>API 端点</h2>
            <ul>
                <li><a href="/api/system/current">当前系统指标</a></li>
                <li><a href="/api/datasources/status">数据源状态</a></li>
                <li><a href="/api/api/stats">API统计</a></li>
                <li><a href="/api/alerts/active">活跃告警</a></li>
                <li><a href="/api/metrics/names">指标名称列表</a></li>
            </ul>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')
    
    async def _handle_dashboard(self, request):
        """仪表板页面"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>监控仪表板</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
                .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .card h3 { margin-top: 0; color: #333; }
                .metric { display: flex; justify-content: space-between; margin: 10px 0; }
                .metric-name { font-weight: bold; }
                .metric-value { color: #007bff; }
                .status-online { color: #28a745; }
                .status-offline { color: #dc3545; }
                .alert-critical { background: #f8d7da; border-left: 4px solid #dc3545; }
                .alert-warning { background: #fff3cd; border-left: 4px solid #ffc107; }
                .refresh-btn { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
            </style>
        </head>
        <body>
            <h1>EasyXT 监控仪表板</h1>
            <button class="refresh-btn" onclick="refreshData()">刷新数据</button>
            
            <div class="dashboard" id="dashboard">
                <div class="card">
                    <h3>系统状态</h3>
                    <div id="system-metrics">加载中...</div>
                </div>
                
                <div class="card">
                    <h3>数据源状态</h3>
                    <div id="datasource-status">加载中...</div>
                </div>
                
                <div class="card">
                    <h3>API统计</h3>
                    <div id="api-stats">加载中...</div>
                </div>
                
                <div class="card">
                    <h3>活跃告警</h3>
                    <div id="active-alerts">加载中...</div>
                </div>
            </div>
            
            <script>
                async function fetchData(url) {
                    try {
                        const response = await fetch(url);
                        return await response.json();
                    } catch (error) {
                        console.error('获取数据失败:', error);
                        return null;
                    }
                }
                
                function formatMetric(name, value, unit = '') {
                    return `<div class="metric"><span class="metric-name">${name}</span><span class="metric-value">${value}${unit}</span></div>`;
                }
                
                async function updateSystemMetrics() {
                    const data = await fetchData('/api/system/current');
                    const container = document.getElementById('system-metrics');
                    
                    if (data) {
                        container.innerHTML = 
                            formatMetric('CPU使用率', data.cpu_percent?.toFixed(1), '%') +
                            formatMetric('内存使用率', data.memory_percent?.toFixed(1), '%') +
                            formatMetric('磁盘使用率', data.disk_percent?.toFixed(1), '%') +
                            formatMetric('进程数', data.process_count);
                    } else {
                        container.innerHTML = '<div>无法获取系统指标</div>';
                    }
                }
                
                async function updateDataSourceStatus() {
                    const data = await fetchData('/api/datasources/status');
                    const container = document.getElementById('datasource-status');
                    
                    if (data && typeof data === 'object') {
                        let html = '';
                        for (const [name, status] of Object.entries(data)) {
                            const statusClass = status.status === 'online' ? 'status-online' : 'status-offline';
                            html += `<div class="metric"><span class="metric-name">${name}</span><span class="metric-value ${statusClass}">${status.status || '未知'}</span></div>`;
                        }
                        container.innerHTML = html || '<div>暂无数据源</div>';
                    } else {
                        container.innerHTML = '<div>无法获取数据源状态</div>';
                    }
                }
                
                async function updateApiStats() {
                    const data = await fetchData('/api/api/stats');
                    const container = document.getElementById('api-stats');
                    
                    if (data && data.overall_stats) {
                        const stats = data.overall_stats;
                        container.innerHTML = 
                            formatMetric('总请求数', stats.total_requests) +
                            formatMetric('成功率', stats.success_rate?.toFixed(1), '%') +
                            formatMetric('平均响应时间', stats.avg_response_time?.toFixed(1), 'ms') +
                            formatMetric('每秒请求数', stats.requests_per_second?.toFixed(1));
                    } else {
                        container.innerHTML = '<div>无法获取API统计</div>';
                    }
                }
                
                async function updateActiveAlerts() {
                    const data = await fetchData('/api/alerts/active');
                    const container = document.getElementById('active-alerts');
                    
                    if (data && Array.isArray(data)) {
                        if (data.length === 0) {
                            container.innerHTML = '<div style="color: #28a745;">暂无活跃告警</div>';
                        } else {
                            let html = '';
                            data.slice(0, 5).forEach(alert => {
                                const alertClass = alert.level === 'critical' ? 'alert-critical' : 'alert-warning';
                                html += `<div class="${alertClass}" style="padding: 10px; margin: 5px 0; border-radius: 4px;">
                                    <strong>${alert.title}</strong><br>
                                    <small>${alert.message}</small>
                                </div>`;
                            });
                            container.innerHTML = html;
                        }
                    } else {
                        container.innerHTML = '<div>无法获取告警信息</div>';
                    }
                }
                
                async function refreshData() {
                    await Promise.all([
                        updateSystemMetrics(),
                        updateDataSourceStatus(),
                        updateApiStats(),
                        updateActiveAlerts()
                    ]);
                }
                
                // 初始加载和定时刷新
                refreshData();
                setInterval(refreshData, 30000); // 30秒刷新一次
            </script>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')
    
    async def _handle_health(self, request):
        """健康检查"""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }
        
        # 检查各组件状态
        if self.system_monitor:
            health_status['components']['system_monitor'] = 'running'
        
        if self.data_source_monitor:
            health_status['components']['data_source_monitor'] = 'running'
        
        if self.api_monitor:
            health_status['components']['api_monitor'] = 'running'
        
        if self.alert_manager:
            health_status['components']['alert_manager'] = 'running'
        
        if self.metrics_collector:
            health_status['components']['metrics_collector'] = 'running'
        
        return web.json_response(health_status)
    
    async def _handle_overview(self, request):
        """系统概览"""
        overview = {
            'timestamp': datetime.now().isoformat(),
            'system': None,
            'datasources': None,
            'api': None,
            'alerts': None
        }
        
        # 系统概览
        if self.system_monitor:
            current = self.system_monitor.get_current_metrics()
            if current:
                overview['system'] = {
                    'cpu_percent': current.cpu_percent,
                    'memory_percent': current.memory_percent,
                    'disk_percent': current.disk_percent,
                    'process_count': current.process_count
                }
        
        # 数据源概览
        if self.data_source_monitor:
            status = self.data_source_monitor.get_current_status()
            online_count = sum(1 for s in status.values() 
                             if isinstance(s, dict) and s.get('status') == 'online')
            overview['datasources'] = {
                'total': len(status),
                'online': online_count,
                'offline': len(status) - online_count
            }
        
        # API概览
        if self.api_monitor:
            stats = self.api_monitor.get_overall_stats()
            overview['api'] = {
                'total_requests': stats.get('total_requests', 0),
                'success_rate': stats.get('success_rate', 0),
                'error_rate': stats.get('error_rate', 0),
                'avg_response_time': stats.get('avg_response_time', 0)
            }
        
        # 告警概览
        if self.alert_manager:
            active_alerts = self.alert_manager.get_active_alerts()
            overview['alerts'] = {
                'active_count': len(active_alerts),
                'critical_count': len([a for a in active_alerts if a.level.value == 'critical']),
                'warning_count': len([a for a in active_alerts if a.level.value == 'warning'])
            }
        
        return web.json_response(overview)
    
    async def _handle_system_current(self, request):
        """当前系统指标"""
        if not self.system_monitor:
            return web.json_response({'error': '系统监控器未注册'}, status=404)
        
        current = self.system_monitor.get_current_metrics()
        if current:
            return web.json_response({
                'timestamp': current.timestamp.isoformat(),
                'cpu_percent': current.cpu_percent,
                'memory_percent': current.memory_percent,
                'memory_used': current.memory_used,
                'memory_total': current.memory_total,
                'disk_percent': current.disk_percent,
                'disk_used': current.disk_used,
                'disk_total': current.disk_total,
                'network_sent': current.network_sent,
                'network_recv': current.network_recv,
                'process_count': current.process_count,
                'load_average': current.load_average
            })
        
        return web.json_response({'error': '暂无系统指标数据'}, status=404)
    
    async def _handle_system_history(self, request):
        """系统历史指标"""
        if not self.system_monitor:
            return web.json_response({'error': '系统监控器未注册'}, status=404)
        
        # 获取查询参数
        duration_str = request.query.get('duration', '1h')
        try:
            if duration_str.endswith('h'):
                duration = timedelta(hours=int(duration_str[:-1]))
            elif duration_str.endswith('m'):
                duration = timedelta(minutes=int(duration_str[:-1]))
            else:
                duration = timedelta(hours=1)
        except ValueError:
            duration = timedelta(hours=1)
        
        history = self.system_monitor.get_metrics_history(duration)
        
        return web.json_response([
            {
                'timestamp': m.timestamp.isoformat(),
                'cpu_percent': m.cpu_percent,
                'memory_percent': m.memory_percent,
                'disk_percent': m.disk_percent,
                'network_sent': m.network_sent,
                'network_recv': m.network_recv
            }
            for m in history
        ])
    
    async def _handle_system_stats(self, request):
        """系统统计信息"""
        if not self.system_monitor:
            return web.json_response({'error': '系统监控器未注册'}, status=404)
        
        return web.json_response(self.system_monitor.get_stats())
    
    async def _handle_datasources_status(self, request):
        """数据源状态"""
        if not self.data_source_monitor:
            return web.json_response({'error': '数据源监控器未注册'}, status=404)
        
        return web.json_response(self.data_source_monitor.get_current_status())
    
    async def _handle_datasources_stats(self, request):
        """数据源统计"""
        if not self.data_source_monitor:
            return web.json_response({'error': '数据源监控器未注册'}, status=404)
        
        return web.json_response(self.data_source_monitor.get_stats())
    
    async def _handle_api_stats(self, request):
        """API统计"""
        if not self.api_monitor:
            return web.json_response({'error': 'API监控器未注册'}, status=404)
        
        return web.json_response(self.api_monitor.get_stats())
    
    async def _handle_api_endpoints(self, request):
        """API端点统计"""
        if not self.api_monitor:
            return web.json_response({'error': 'API监控器未注册'}, status=404)
        
        return web.json_response(self.api_monitor.get_endpoint_stats())
    
    async def _handle_api_errors(self, request):
        """API错误请求"""
        if not self.api_monitor:
            return web.json_response({'error': 'API监控器未注册'}, status=404)
        
        limit = int(request.query.get('limit', 10))
        return web.json_response(self.api_monitor.get_error_requests(limit))
    
    async def _handle_alerts_active(self, request):
        """活跃告警"""
        if not self.alert_manager:
            return web.json_response({'error': '告警管理器未注册'}, status=404)
        
        alerts = self.alert_manager.get_active_alerts()
        return web.json_response([
            {
                'id': alert.id,
                'rule_name': alert.rule_name,
                'level': alert.level.value,
                'title': alert.title,
                'message': alert.message,
                'value': alert.value,
                'threshold': alert.threshold,
                'timestamp': alert.timestamp.isoformat(),
                'source': alert.source,
                'tags': alert.tags
            }
            for alert in alerts
        ])
    
    async def _handle_alerts_history(self, request):
        """告警历史"""
        if not self.alert_manager:
            return web.json_response({'error': '告警管理器未注册'}, status=404)
        
        limit = int(request.query.get('limit', 50))
        duration_str = request.query.get('duration', '24h')
        
        try:
            if duration_str.endswith('h'):
                duration = timedelta(hours=int(duration_str[:-1]))
            elif duration_str.endswith('d'):
                duration = timedelta(days=int(duration_str[:-1]))
            else:
                duration = timedelta(hours=24)
        except ValueError:
            duration = timedelta(hours=24)
        
        alerts = self.alert_manager.get_alert_history(duration, limit=limit)
        return web.json_response([
            {
                'id': alert.id,
                'rule_name': alert.rule_name,
                'level': alert.level.value,
                'title': alert.title,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'status': alert.status.value,
                'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
            }
            for alert in alerts
        ])
    
    async def _handle_alerts_stats(self, request):
        """告警统计"""
        if not self.alert_manager:
            return web.json_response({'error': '告警管理器未注册'}, status=404)
        
        return web.json_response(self.alert_manager.get_alert_stats())
    
    async def _handle_alerts_resolve(self, request):
        """解决告警"""
        if not self.alert_manager:
            return web.json_response({'error': '告警管理器未注册'}, status=404)
        
        data = await request.json()
        alert_id = data.get('alert_id')
        
        if not alert_id:
            return web.json_response({'error': '缺少alert_id参数'}, status=400)
        
        self.alert_manager.resolve_alert(alert_id)
        return web.json_response({'success': True})
    
    async def _handle_metrics_names(self, request):
        """指标名称列表"""
        if not self.metrics_collector:
            return web.json_response({'error': '指标收集器未注册'}, status=404)
        
        return web.json_response(self.metrics_collector.get_metric_names())
    
    async def _handle_metrics_query(self, request):
        """查询指标数据"""
        if not self.metrics_collector:
            return web.json_response({'error': '指标收集器未注册'}, status=404)
        
        metric_name = request.query.get('metric')
        if not metric_name:
            return web.json_response({'error': '缺少metric参数'}, status=400)
        
        # 解析时间范围
        duration_str = request.query.get('duration', '1h')
        try:
            if duration_str.endswith('h'):
                duration = timedelta(hours=int(duration_str[:-1]))
            elif duration_str.endswith('m'):
                duration = timedelta(minutes=int(duration_str[:-1]))
            else:
                duration = timedelta(hours=1)
        except ValueError:
            duration = timedelta(hours=1)
        
        end_time = datetime.now()
        start_time = end_time - duration
        
        points = self.metrics_collector.query_metrics(metric_name, None, start_time, end_time)
        
        return web.json_response([
            {
                'timestamp': p.timestamp.isoformat(),
                'value': p.value,
                'tags': p.tags
            }
            for p in points
        ])
    
    async def _handle_websocket(self, request):
        """WebSocket连接处理"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # 添加到连接集合
        self.websocket_connections.add(ws)
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_websocket_message(ws, data)
                    except json.JSONDecodeError:
                        await ws.send_str(json.dumps({
                            'error': '无效的JSON格式'
                        }))
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f'WebSocket错误: {ws.exception()}')
        except Exception as e:
            logger.error(f'WebSocket处理异常: {e}')
        
        return ws
    
    async def _handle_websocket_message(self, ws, data):
        """处理WebSocket消息"""
        msg_type = data.get('type')
        
        if msg_type == 'subscribe':
            # 订阅实时数据
            await ws.send_str(json.dumps({
                'type': 'subscribed',
                'message': '已订阅实时数据推送'
            }))
        
        elif msg_type == 'get_overview':
            # 获取系统概览
            overview = await self._get_overview_data()
            await ws.send_str(json.dumps({
                'type': 'overview',
                'data': overview
            }))
        
        else:
            await ws.send_str(json.dumps({
                'error': f'未知的消息类型: {msg_type}'
            }))
    
    async def _get_overview_data(self):
        """获取概览数据"""
        # 这里可以复用 _handle_overview 的逻辑
        # 为了简化，直接返回基本信息
        return {
            'timestamp': datetime.now().isoformat(),
            'status': 'running'
        }
    
    async def broadcast_to_websockets(self, message: Dict[str, Any]):
        """向所有WebSocket连接广播消息"""
        if not self.websocket_connections:
            return
        
        message_str = json.dumps(message)
        
        # 创建连接列表的副本，避免在迭代时修改
        connections = list(self.websocket_connections)
        
        for ws in connections:
            try:
                if not ws.closed:
                    await ws.send_str(message_str)
            except Exception as e:
                logger.error(f'WebSocket广播失败: {e}')
    
    def get_stats(self) -> Dict[str, Any]:
        """获取仪表板统计信息"""
        return {
            'dashboard_info': {
                'host': self.host,
                'port': self.port,
                'running': self.app is not None,
                'websocket_connections': len(self.websocket_connections),
                'cors_enabled': self.enable_cors
            },
            'registered_components': {
                'system_monitor': self.system_monitor is not None,
                'data_source_monitor': self.data_source_monitor is not None,
                'api_monitor': self.api_monitor is not None,
                'alert_manager': self.alert_manager is not None,
                'metrics_collector': self.metrics_collector is not None
            }
        }