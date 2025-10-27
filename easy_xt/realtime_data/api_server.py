"""
RESTful API服务器

提供HTTP方式的实时数据访问接口，作为WebSocket推送服务的补充。
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import traceback

try:
    from aiohttp import web, web_request, web_response
    from aiohttp.web import middleware
    from aiohttp_cors import setup as cors_setup, ResourceOptions
except ImportError:
    print("需要安装aiohttp: pip install aiohttp aiohttp-cors")
    raise

from .unified_api import UnifiedDataAPI
from .config.settings import RealtimeDataConfig


class RealtimeDataAPIServer:
    """实时数据API服务器"""
    
    def __init__(self, config: RealtimeDataConfig):
        """初始化API服务器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.data_api = UnifiedDataAPI(config)
        self.app = None
        self.runner = None
        self.site = None
        
        # 服务器配置
        api_config = config.config.get('api', {})
        self.host = api_config.get('host', 'localhost')
        self.port = api_config.get('port', 8080)
        self.cors_enabled = api_config.get('cors_enabled', True)
        
        # 日志配置
        self.logger = logging.getLogger(__name__)
        
        # 统计信息
        self.stats = {
            'start_time': datetime.now(),
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'endpoints_stats': {}
        }
        
        self._setup_app()
    
    def _setup_app(self):
        """设置应用程序"""
        self.app = web.Application(middlewares=[
            self._logging_middleware,
            self._error_middleware,
            self._stats_middleware
        ])
        
        # 设置路由
        self._setup_routes()
        
        # 设置CORS
        if self.cors_enabled:
            self._setup_cors()
    
    def _setup_routes(self):
        """设置路由"""
        # 健康检查
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/status', self.get_status)
        
        # 实时行情数据
        self.app.router.add_get('/api/v1/quotes', self.get_quotes)
        self.app.router.add_post('/api/v1/quotes', self.get_quotes_batch)
        
        # 热门股票
        self.app.router.add_get('/api/v1/hot-stocks', self.get_hot_stocks)
        
        # 概念数据
        self.app.router.add_get('/api/v1/concepts', self.get_concepts)
        
        # 市场状态
        self.app.router.add_get('/api/v1/market-status', self.get_market_status)
        
        # 数据源状态
        self.app.router.add_get('/api/v1/sources', self.get_sources_status)
        
        # 多数据源对比
        self.app.router.add_get('/api/v1/compare', self.compare_sources)
        
        # 服务器统计
        self.app.router.add_get('/api/v1/stats', self.get_server_stats)
        
        # API文档
        self.app.router.add_get('/docs', self.get_api_docs)
        self.app.router.add_get('/', self.get_api_docs)  # 根路径重定向到文档
    
    def _setup_cors(self):
        """设置CORS"""
        cors = cors_setup(self.app, defaults={
            "*": ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # 为所有路由添加CORS
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    @middleware
    async def _logging_middleware(self, request: web_request.Request, handler):
        """日志中间件"""
        start_time = datetime.now()
        
        try:
            response = await handler(request)
            duration = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(
                f"{request.method} {request.path} - "
                f"{response.status} - {duration:.3f}s"
            )
            
            return response
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.error(
                f"{request.method} {request.path} - "
                f"ERROR: {str(e)} - {duration:.3f}s"
            )
            raise
    
    @middleware
    async def _error_middleware(self, request: web_request.Request, handler):
        """错误处理中间件"""
        try:
            return await handler(request)
        except web.HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"API错误: {str(e)}\n{traceback.format_exc()}")
            return web.json_response(
                {
                    'error': 'Internal Server Error',
                    'message': str(e),
                    'timestamp': datetime.now().isoformat()
                },
                status=500
            )
    
    @middleware
    async def _stats_middleware(self, request: web_request.Request, handler):
        """统计中间件"""
        self.stats['total_requests'] += 1
        
        # 记录端点统计
        endpoint = f"{request.method} {request.path}"
        if endpoint not in self.stats['endpoints_stats']:
            self.stats['endpoints_stats'][endpoint] = {
                'count': 0,
                'success': 0,
                'error': 0
            }
        
        self.stats['endpoints_stats'][endpoint]['count'] += 1
        
        try:
            response = await handler(request)
            
            if response.status < 400:
                self.stats['successful_requests'] += 1
                self.stats['endpoints_stats'][endpoint]['success'] += 1
            else:
                self.stats['failed_requests'] += 1
                self.stats['endpoints_stats'][endpoint]['error'] += 1
            
            return response
            
        except Exception:
            self.stats['failed_requests'] += 1
            self.stats['endpoints_stats'][endpoint]['error'] += 1
            raise
    
    async def health_check(self, request: web_request.Request) -> web_response.Response:
        """健康检查"""
        health_status = self.data_api.health_check()
        
        return web.json_response({
            'status': 'healthy' if health_status['overall_health'] else 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'data_sources': health_status
        })
    
    async def get_status(self, request: web_request.Request) -> web_response.Response:
        """获取服务器状态"""
        source_status = self.data_api.get_source_status()
        
        return web.json_response({
            'server': {
                'status': 'running',
                'start_time': self.stats['start_time'].isoformat(),
                'uptime_seconds': (datetime.now() - self.stats['start_time']).total_seconds(),
                'host': self.host,
                'port': self.port
            },
            'data_sources': source_status,
            'statistics': self.stats
        })
    
    async def get_quotes(self, request: web_request.Request) -> web_response.Response:
        """获取实时行情"""
        # 从查询参数获取股票代码
        symbols_param = request.query.get('symbols', '')
        if not symbols_param:
            return web.json_response(
                {'error': 'Missing symbols parameter'},
                status=400
            )
        
        symbols = [s.strip() for s in symbols_param.split(',') if s.strip()]
        if not symbols:
            return web.json_response(
                {'error': 'Invalid symbols parameter'},
                status=400
            )
        
        # 获取数据源参数
        source = request.query.get('source', 'auto')
        
        try:
            if source == 'auto':
                quotes = self.data_api.get_realtime_quotes(symbols)
            else:
                quotes = self.data_api.get_realtime_quotes(symbols, preferred_source=source)
            
            return web.json_response({
                'success': True,
                'data': quotes,
                'timestamp': datetime.now().isoformat(),
                'source': source
            })
            
        except Exception as e:
            self.logger.error(f"获取行情失败: {str(e)}")
            return web.json_response(
                {'error': f'Failed to get quotes: {str(e)}'},
                status=500
            )
    
    async def get_quotes_batch(self, request: web_request.Request) -> web_response.Response:
        """批量获取实时行情"""
        try:
            data = await request.json()
            symbols = data.get('symbols', [])
            source = data.get('source', 'auto')
            
            if not symbols:
                return web.json_response(
                    {'error': 'Missing symbols in request body'},
                    status=400
                )
            
            if source == 'auto':
                quotes = self.data_api.get_realtime_quotes(symbols)
            else:
                quotes = self.data_api.get_realtime_quotes(symbols, preferred_source=source)
            
            return web.json_response({
                'success': True,
                'data': quotes,
                'timestamp': datetime.now().isoformat(),
                'source': source
            })
            
        except Exception as e:
            self.logger.error(f"批量获取行情失败: {str(e)}")
            return web.json_response(
                {'error': f'Failed to get quotes: {str(e)}'},
                status=500
            )
    
    async def get_hot_stocks(self, request: web_request.Request) -> web_response.Response:
        """获取热门股票"""
        try:
            count = int(request.query.get('count', 20))
            source = request.query.get('source', 'auto')
            
            if source == 'auto':
                hot_stocks = self.data_api.get_hot_stocks(count)
            else:
                hot_stocks = self.data_api.get_hot_stocks(count, preferred_source=source)
            
            return web.json_response({
                'success': True,
                'data': hot_stocks,
                'timestamp': datetime.now().isoformat(),
                'source': source
            })
            
        except Exception as e:
            self.logger.error(f"获取热门股票失败: {str(e)}")
            return web.json_response(
                {'error': f'Failed to get hot stocks: {str(e)}'},
                status=500
            )
    
    async def get_concepts(self, request: web_request.Request) -> web_response.Response:
        """获取概念数据"""
        try:
            count = int(request.query.get('count', 20))
            source = request.query.get('source', 'auto')
            
            if source == 'auto':
                concepts = self.data_api.get_concept_data(count)
            else:
                concepts = self.data_api.get_concept_data(count, preferred_source=source)
            
            return web.json_response({
                'success': True,
                'data': concepts,
                'timestamp': datetime.now().isoformat(),
                'source': source
            })
            
        except Exception as e:
            self.logger.error(f"获取概念数据失败: {str(e)}")
            return web.json_response(
                {'error': f'Failed to get concepts: {str(e)}'},
                status=500
            )
    
    async def get_market_status(self, request: web_request.Request) -> web_response.Response:
        """获取市场状态"""
        try:
            market_status = self.data_api.get_market_status()
            
            return web.json_response({
                'success': True,
                'data': market_status,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"获取市场状态失败: {str(e)}")
            return web.json_response(
                {'error': f'Failed to get market status: {str(e)}'},
                status=500
            )
    
    async def get_sources_status(self, request: web_request.Request) -> web_response.Response:
        """获取数据源状态"""
        try:
            sources_status = self.data_api.get_source_status()
            
            return web.json_response({
                'success': True,
                'data': sources_status,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"获取数据源状态失败: {str(e)}")
            return web.json_response(
                {'error': f'Failed to get sources status: {str(e)}'},
                status=500
            )
    
    async def compare_sources(self, request: web_request.Request) -> web_response.Response:
        """多数据源对比"""
        try:
            symbols_param = request.query.get('symbols', '')
            if not symbols_param:
                return web.json_response(
                    {'error': 'Missing symbols parameter'},
                    status=400
                )
            
            symbols = [s.strip() for s in symbols_param.split(',') if s.strip()]
            if not symbols:
                return web.json_response(
                    {'error': 'Invalid symbols parameter'},
                    status=400
                )
            
            comparison_data = self.data_api.get_multi_source_data(symbols)
            
            return web.json_response({
                'success': True,
                'data': comparison_data,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"多数据源对比失败: {str(e)}")
            return web.json_response(
                {'error': f'Failed to compare sources: {str(e)}'},
                status=500
            )
    
    async def get_server_stats(self, request: web_request.Request) -> web_response.Response:
        """获取服务器统计信息"""
        return web.json_response({
            'success': True,
            'data': {
                **self.stats,
                'start_time': self.stats['start_time'].isoformat(),
                'uptime_seconds': (datetime.now() - self.stats['start_time']).total_seconds()
            },
            'timestamp': datetime.now().isoformat()
        })
    
    async def get_api_docs(self, request: web_request.Request) -> web_response.Response:
        """获取API文档"""
        docs_html = """
<!DOCTYPE html>
<html>
<head>
    <title>EasyXT实时数据API文档</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .endpoint { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .method { font-weight: bold; color: #007bff; }
        .path { font-family: monospace; background: #f8f9fa; padding: 2px 5px; }
        .params { margin: 10px 0; }
        .example { background: #f8f9fa; padding: 10px; border-radius: 3px; margin: 10px 0; }
        pre { margin: 0; }
    </style>
</head>
<body>
    <h1>EasyXT实时数据API文档</h1>
    
    <h2>基础信息</h2>
    <p>服务器地址: <code>http://""" + self.host + ":" + str(self.port) + """</code></p>
    <p>API版本: v1</p>
    
    <h2>端点列表</h2>
    
    <div class="endpoint">
        <h3><span class="method">GET</span> <span class="path">/health</span></h3>
        <p>健康检查</p>
        <div class="example">
            <strong>示例:</strong>
            <pre>curl http://""" + self.host + ":" + str(self.port) + """/health</pre>
        </div>
    </div>
    
    <div class="endpoint">
        <h3><span class="method">GET</span> <span class="path">/api/v1/quotes</span></h3>
        <p>获取实时行情</p>
        <div class="params">
            <strong>参数:</strong>
            <ul>
                <li><code>symbols</code> - 股票代码，多个用逗号分隔</li>
                <li><code>source</code> - 数据源 (可选): auto, tdx, ths, eastmoney</li>
            </ul>
        </div>
        <div class="example">
            <strong>示例:</strong>
            <pre>curl "http://""" + self.host + ":" + str(self.port) + """/api/v1/quotes?symbols=000001,000002"</pre>
        </div>
    </div>
    
    <div class="endpoint">
        <h3><span class="method">POST</span> <span class="path">/api/v1/quotes</span></h3>
        <p>批量获取实时行情</p>
        <div class="example">
            <strong>示例:</strong>
            <pre>curl -X POST -H "Content-Type: application/json" \\
     -d '{"symbols":["000001","000002"],"source":"auto"}' \\
     http://""" + self.host + ":" + str(self.port) + """/api/v1/quotes</pre>
        </div>
    </div>
    
    <div class="endpoint">
        <h3><span class="method">GET</span> <span class="path">/api/v1/hot-stocks</span></h3>
        <p>获取热门股票</p>
        <div class="params">
            <strong>参数:</strong>
            <ul>
                <li><code>count</code> - 数量 (默认20)</li>
                <li><code>source</code> - 数据源 (可选)</li>
            </ul>
        </div>
        <div class="example">
            <strong>示例:</strong>
            <pre>curl "http://""" + self.host + ":" + str(self.port) + """/api/v1/hot-stocks?count=10"</pre>
        </div>
    </div>
    
    <div class="endpoint">
        <h3><span class="method">GET</span> <span class="path">/api/v1/concepts</span></h3>
        <p>获取概念数据</p>
        <div class="params">
            <strong>参数:</strong>
            <ul>
                <li><code>count</code> - 数量 (默认20)</li>
                <li><code>source</code> - 数据源 (可选)</li>
            </ul>
        </div>
    </div>
    
    <div class="endpoint">
        <h3><span class="method">GET</span> <span class="path">/api/v1/market-status</span></h3>
        <p>获取市场状态</p>
    </div>
    
    <div class="endpoint">
        <h3><span class="method">GET</span> <span class="path">/api/v1/sources</span></h3>
        <p>获取数据源状态</p>
    </div>
    
    <div class="endpoint">
        <h3><span class="method">GET</span> <span class="path">/api/v1/compare</span></h3>
        <p>多数据源对比</p>
        <div class="params">
            <strong>参数:</strong>
            <ul>
                <li><code>symbols</code> - 股票代码，多个用逗号分隔</li>
            </ul>
        </div>
    </div>
    
    <div class="endpoint">
        <h3><span class="method">GET</span> <span class="path">/api/v1/stats</span></h3>
        <p>获取服务器统计信息</p>
    </div>
    
    <h2>响应格式</h2>
    <div class="example">
        <strong>成功响应:</strong>
        <pre>{
    "success": true,
    "data": {...},
    "timestamp": "2024-01-01T12:00:00"
}</pre>
    </div>
    
    <div class="example">
        <strong>错误响应:</strong>
        <pre>{
    "error": "Error message",
    "timestamp": "2024-01-01T12:00:00"
}</pre>
    </div>
    
</body>
</html>
        """
        
        return web.Response(text=docs_html, content_type='text/html')
    
    async def start_server(self):
        """启动API服务器"""
        try:
            # 连接数据源
            self.logger.info("连接数据源...")
            connect_results = self.data_api.connect_all()
            available_sources = sum(1 for success in connect_results.values() if success)
            
            if available_sources == 0:
                self.logger.warning("没有可用的数据源，API服务将以有限功能启动")
            else:
                self.logger.info(f"成功连接 {available_sources} 个数据源")
            
            # 启动HTTP服务器
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()
            
            self.logger.info(f"API服务器已启动: http://{self.host}:{self.port}")
            self.logger.info(f"API文档地址: http://{self.host}:{self.port}/docs")
            
        except Exception as e:
            self.logger.error(f"启动API服务器失败: {str(e)}")
            raise
    
    async def stop_server(self):
        """停止API服务器"""
        try:
            if self.site:
                await self.site.stop()
                self.site = None
            
            if self.runner:
                await self.runner.cleanup()
                self.runner = None
            
            # 断开数据源连接
            self.data_api.disconnect_all()
            
            self.logger.info("API服务器已停止")
            
        except Exception as e:
            self.logger.error(f"停止API服务器失败: {str(e)}")
            raise
    
    def is_running(self) -> bool:
        """检查服务器是否运行中"""
        return self.site is not None


async def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建配置
    config = RealtimeDataConfig()
    
    # 创建API服务器
    server = RealtimeDataAPIServer(config)
    
    try:
        # 启动服务器
        await server.start_server()
        
        print(f"🚀 API服务器已启动: http://{server.host}:{server.port}")
        print(f"📖 API文档: http://{server.host}:{server.port}/docs")
        print("按 Ctrl+C 停止服务器")
        
        # 保持运行
        while server.is_running():
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n正在停止服务器...")
        await server.stop_server()
        print("服务器已停止")
    except Exception as e:
        print(f"服务器错误: {e}")
        await server.stop_server()


if __name__ == "__main__":
    asyncio.run(main())