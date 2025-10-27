"""
实时数据推送服务

基于WebSocket的实时数据推送服务，支持多客户端连接和数据分发。
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Set, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException

from .unified_api import UnifiedDataAPI
from .config.settings import RealtimeDataConfig


@dataclass
class ClientInfo:
    """客户端信息"""
    client_id: str
    websocket: WebSocketServerProtocol
    subscriptions: Set[str]
    connect_time: float
    last_ping: float
    user_agent: str = ""
    remote_address: str = ""


@dataclass
class PushMessage:
    """推送消息"""
    message_type: str
    data: Any
    timestamp: float
    client_ids: Optional[List[str]] = None  # None表示广播给所有客户端


class RealtimeDataPushService:
    """实时数据推送服务
    
    提供WebSocket服务，支持客户端订阅和实时数据推送。
    """
    
    def __init__(self, config: Optional[RealtimeDataConfig] = None):
        """初始化推送服务
        
        Args:
            config: 配置对象
        """
        self.config = config or RealtimeDataConfig()
        self.logger = logging.getLogger(__name__)
        
        # WebSocket配置
        ws_config = self.config.get_websocket_config()
        self.host = ws_config.get('host', 'localhost')
        self.port = ws_config.get('port', 8765)
        self.max_connections = ws_config.get('max_connections', 100)
        
        # 调度器配置
        scheduler_config = self.config.get_scheduler_config()
        self.update_interval = scheduler_config.get('update_interval', 3)
        self.batch_size = scheduler_config.get('batch_size', 50)
        
        # 数据API
        self.data_api = UnifiedDataAPI(config)
        
        # 客户端管理
        self.clients: Dict[str, ClientInfo] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # symbol -> client_ids
        
        # 服务状态
        self.server = None
        self.is_running = False
        self.update_task = None
        
        # 消息队列
        self.message_queue: asyncio.Queue = asyncio.Queue()
        
        # 统计信息
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'messages_sent': 0,
            'errors': 0,
            'start_time': 0
        }
    
    async def start_server(self):
        """启动WebSocket服务器"""
        try:
            # 连接数据源
            self.logger.info("连接数据源...")
            connect_results = self.data_api.connect_all()
            available_sources = sum(1 for success in connect_results.values() if success)
            
            if available_sources == 0:
                self.logger.warning("没有可用的数据源，服务将以有限功能启动")
            else:
                self.logger.info(f"成功连接 {available_sources} 个数据源")
            
            # 启动WebSocket服务器
            self.server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                max_size=1024*1024,  # 1MB
                ping_interval=30,
                ping_timeout=10
            )
            
            self.is_running = True
            self.stats['start_time'] = time.time()
            
            # 启动数据更新任务
            self.update_task = asyncio.create_task(self.data_update_loop())
            
            # 启动消息处理任务
            asyncio.create_task(self.message_processor())
            
            self.logger.info(f"实时数据推送服务已启动: ws://{self.host}:{self.port}")
            
        except Exception as e:
            self.logger.error(f"启动服务器失败: {e}")
            raise
    
    async def stop_server(self):
        """停止WebSocket服务器"""
        self.is_running = False
        
        # 停止数据更新任务
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
        
        # 关闭所有客户端连接
        if self.clients:
            await asyncio.gather(
                *[self.disconnect_client(client_id) for client_id in list(self.clients.keys())],
                return_exceptions=True
            )
        
        # 关闭服务器
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # 断开数据源连接
        self.data_api.disconnect_all()
        
        self.logger.info("实时数据推送服务已停止")
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """处理客户端连接
        
        Args:
            websocket: WebSocket连接
            path: 请求路径
        """
        client_id = f"client_{int(time.time() * 1000)}_{id(websocket)}"
        
        # 检查连接数限制
        if len(self.clients) >= self.max_connections:
            await websocket.close(code=1013, reason="服务器连接数已满")
            return
        
        # 创建客户端信息
        client_info = ClientInfo(
            client_id=client_id,
            websocket=websocket,
            subscriptions=set(),
            connect_time=time.time(),
            last_ping=time.time(),
            remote_address=f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        )
        
        # 注册客户端
        self.clients[client_id] = client_info
        self.stats['total_connections'] += 1
        self.stats['active_connections'] = len(self.clients)
        
        self.logger.info(f"客户端连接: {client_id} from {client_info.remote_address}")
        
        # 发送欢迎消息
        await self.send_to_client(client_id, {
            'type': 'welcome',
            'client_id': client_id,
            'server_time': time.time(),
            'available_sources': self.data_api.get_available_providers()
        })
        
        try:
            # 处理客户端消息
            async for message in websocket:
                await self.handle_client_message(client_id, message)
                
        except ConnectionClosed:
            self.logger.info(f"客户端断开连接: {client_id}")
        except WebSocketException as e:
            self.logger.warning(f"WebSocket异常: {client_id} - {e}")
        except Exception as e:
            self.logger.error(f"处理客户端消息异常: {client_id} - {e}")
        finally:
            # 清理客户端
            await self.disconnect_client(client_id)
    
    async def handle_client_message(self, client_id: str, message: str):
        """处理客户端消息
        
        Args:
            client_id: 客户端ID
            message: 消息内容
        """
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'subscribe':
                # 订阅股票
                symbols = data.get('symbols', [])
                await self.subscribe_symbols(client_id, symbols)
                
            elif msg_type == 'unsubscribe':
                # 取消订阅
                symbols = data.get('symbols', [])
                await self.unsubscribe_symbols(client_id, symbols)
                
            elif msg_type == 'get_quotes':
                # 获取实时行情
                symbols = data.get('symbols', [])
                await self.send_quotes(client_id, symbols)
                
            elif msg_type == 'get_hot_stocks':
                # 获取热门股票
                count = data.get('count', 50)
                await self.send_hot_stocks(client_id, count)
                
            elif msg_type == 'get_concepts':
                # 获取概念数据
                count = data.get('count', 50)
                await self.send_concepts(client_id, count)
                
            elif msg_type == 'ping':
                # 心跳检测
                client_info = self.clients.get(client_id)
                if client_info:
                    client_info.last_ping = time.time()
                await self.send_to_client(client_id, {'type': 'pong', 'timestamp': time.time()})
                
            elif msg_type == 'get_status':
                # 获取服务状态
                await self.send_server_status(client_id)
                
            else:
                await self.send_to_client(client_id, {
                    'type': 'error',
                    'message': f'未知消息类型: {msg_type}'
                })
                
        except json.JSONDecodeError:
            await self.send_to_client(client_id, {
                'type': 'error',
                'message': '消息格式错误，请发送有效的JSON'
            })
        except Exception as e:
            self.logger.error(f"处理客户端消息失败: {client_id} - {e}")
            await self.send_to_client(client_id, {
                'type': 'error',
                'message': f'处理消息失败: {str(e)}'
            })
    
    async def subscribe_symbols(self, client_id: str, symbols: List[str]):
        """订阅股票代码
        
        Args:
            client_id: 客户端ID
            symbols: 股票代码列表
        """
        client_info = self.clients.get(client_id)
        if not client_info:
            return
        
        # 添加订阅
        for symbol in symbols:
            client_info.subscriptions.add(symbol)
            
            if symbol not in self.subscriptions:
                self.subscriptions[symbol] = set()
            self.subscriptions[symbol].add(client_id)
        
        self.logger.info(f"客户端 {client_id} 订阅: {symbols}")
        
        # 发送确认消息
        await self.send_to_client(client_id, {
            'type': 'subscribe_success',
            'symbols': symbols,
            'total_subscriptions': len(client_info.subscriptions)
        })
        
        # 立即发送当前行情
        await self.send_quotes(client_id, symbols)
    
    async def unsubscribe_symbols(self, client_id: str, symbols: List[str]):
        """取消订阅股票代码
        
        Args:
            client_id: 客户端ID
            symbols: 股票代码列表
        """
        client_info = self.clients.get(client_id)
        if not client_info:
            return
        
        # 移除订阅
        for symbol in symbols:
            client_info.subscriptions.discard(symbol)
            
            if symbol in self.subscriptions:
                self.subscriptions[symbol].discard(client_id)
                if not self.subscriptions[symbol]:
                    del self.subscriptions[symbol]
        
        self.logger.info(f"客户端 {client_id} 取消订阅: {symbols}")
        
        # 发送确认消息
        await self.send_to_client(client_id, {
            'type': 'unsubscribe_success',
            'symbols': symbols,
            'total_subscriptions': len(client_info.subscriptions)
        })
    
    async def send_quotes(self, client_id: str, symbols: List[str]):
        """发送实时行情数据
        
        Args:
            client_id: 客户端ID
            symbols: 股票代码列表
        """
        try:
            quotes = self.data_api.get_realtime_quotes(symbols)
            
            await self.send_to_client(client_id, {
                'type': 'quotes',
                'data': quotes,
                'timestamp': time.time(),
                'count': len(quotes)
            })
            
        except Exception as e:
            self.logger.error(f"发送行情数据失败: {e}")
            await self.send_to_client(client_id, {
                'type': 'error',
                'message': f'获取行情数据失败: {str(e)}'
            })
    
    async def send_hot_stocks(self, client_id: str, count: int):
        """发送热门股票数据
        
        Args:
            client_id: 客户端ID
            count: 获取数量
        """
        try:
            hot_stocks = self.data_api.get_hot_stocks(count=count)
            
            await self.send_to_client(client_id, {
                'type': 'hot_stocks',
                'data': hot_stocks,
                'timestamp': time.time(),
                'count': len(hot_stocks)
            })
            
        except Exception as e:
            self.logger.error(f"发送热门股票失败: {e}")
            await self.send_to_client(client_id, {
                'type': 'error',
                'message': f'获取热门股票失败: {str(e)}'
            })
    
    async def send_concepts(self, client_id: str, count: int):
        """发送概念数据
        
        Args:
            client_id: 客户端ID
            count: 获取数量
        """
        try:
            concepts = self.data_api.get_concept_data(count=count)
            
            await self.send_to_client(client_id, {
                'type': 'concepts',
                'data': concepts,
                'timestamp': time.time(),
                'count': len(concepts)
            })
            
        except Exception as e:
            self.logger.error(f"发送概念数据失败: {e}")
            await self.send_to_client(client_id, {
                'type': 'error',
                'message': f'获取概念数据失败: {str(e)}'
            })
    
    async def send_server_status(self, client_id: str):
        """发送服务器状态
        
        Args:
            client_id: 客户端ID
        """
        try:
            health = self.data_api.health_check()
            
            status = {
                'server_stats': self.stats.copy(),
                'data_sources': health,
                'active_subscriptions': len(self.subscriptions),
                'uptime': time.time() - self.stats['start_time'] if self.stats['start_time'] > 0 else 0
            }
            
            await self.send_to_client(client_id, {
                'type': 'server_status',
                'data': status,
                'timestamp': time.time()
            })
            
        except Exception as e:
            self.logger.error(f"发送服务器状态失败: {e}")
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]):
        """发送消息给指定客户端
        
        Args:
            client_id: 客户端ID
            message: 消息内容
        """
        client_info = self.clients.get(client_id)
        if not client_info:
            return
        
        try:
            await client_info.websocket.send(json.dumps(message, ensure_ascii=False))
            self.stats['messages_sent'] += 1
            
        except ConnectionClosed:
            self.logger.info(f"客户端已断开连接: {client_id}")
            await self.disconnect_client(client_id)
        except Exception as e:
            self.logger.error(f"发送消息失败: {client_id} - {e}")
            self.stats['errors'] += 1
    
    async def broadcast_message(self, message: Dict[str, Any], client_ids: Optional[List[str]] = None):
        """广播消息
        
        Args:
            message: 消息内容
            client_ids: 目标客户端ID列表，None表示广播给所有客户端
        """
        target_clients = client_ids or list(self.clients.keys())
        
        tasks = []
        for client_id in target_clients:
            if client_id in self.clients:
                tasks.append(self.send_to_client(client_id, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def disconnect_client(self, client_id: str):
        """断开客户端连接
        
        Args:
            client_id: 客户端ID
        """
        client_info = self.clients.get(client_id)
        if not client_info:
            return
        
        # 清理订阅
        for symbol in client_info.subscriptions:
            if symbol in self.subscriptions:
                self.subscriptions[symbol].discard(client_id)
                if not self.subscriptions[symbol]:
                    del self.subscriptions[symbol]
        
        # 移除客户端
        del self.clients[client_id]
        self.stats['active_connections'] = len(self.clients)
        
        # 关闭WebSocket连接
        try:
            await client_info.websocket.close()
        except Exception:
            pass
        
        self.logger.info(f"客户端已清理: {client_id}")
    
    async def data_update_loop(self):
        """数据更新循环"""
        self.logger.info("数据更新循环已启动")
        
        while self.is_running:
            try:
                # 获取所有订阅的股票代码
                all_symbols = list(self.subscriptions.keys())
                
                if all_symbols:
                    # 分批获取数据
                    for i in range(0, len(all_symbols), self.batch_size):
                        batch_symbols = all_symbols[i:i + self.batch_size]
                        
                        # 获取实时行情
                        quotes = self.data_api.get_realtime_quotes(batch_symbols)
                        
                        if quotes:
                            # 按股票代码分组推送
                            for quote in quotes:
                                symbol = quote.get('symbol')
                                if symbol and symbol in self.subscriptions:
                                    # 获取订阅该股票的客户端
                                    subscriber_ids = list(self.subscriptions[symbol])
                                    
                                    # 推送数据
                                    message = {
                                        'type': 'realtime_update',
                                        'symbol': symbol,
                                        'data': quote,
                                        'timestamp': time.time()
                                    }
                                    
                                    await self.broadcast_message(message, subscriber_ids)
                
                # 等待下次更新
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"数据更新循环异常: {e}")
                await asyncio.sleep(1)  # 短暂等待后重试
        
        self.logger.info("数据更新循环已停止")
    
    async def message_processor(self):
        """消息处理器"""
        while self.is_running:
            try:
                # 从队列获取消息
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                
                # 处理消息
                await self.broadcast_message(message.data, message.client_ids)
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"消息处理异常: {e}")
    
    def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计信息
        
        Returns:
            Dict: 统计信息
        """
        return {
            'stats': self.stats.copy(),
            'clients': len(self.clients),
            'subscriptions': len(self.subscriptions),
            'is_running': self.is_running,
            'data_sources': self.data_api.health_check()
        }


# 导出类
__all__ = ['RealtimeDataPushService', 'ClientInfo', 'PushMessage']