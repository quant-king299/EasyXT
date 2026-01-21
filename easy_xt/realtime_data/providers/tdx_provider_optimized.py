"""
通达信数据提供者 - 优化版

针对连接速度和用户体验优化的版本
"""

import time
import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Tuple
import logging
from pytdx.hq import TdxHq_API
from .base_provider import BaseDataProvider

logger = logging.getLogger(__name__)


class TdxDataProviderOptimized(BaseDataProvider):
    """通达信数据提供者 - 优化版
    
    特点:
    1. 快速并发连接测试
    2. 智能服务器选择
    3. 详细的连接进度反馈
    4. 优化的超时设置
    """
    
    def is_available(self) -> bool:
        """检查数据提供者是否可用"""
        return self.current_server is not None
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化优化版通达信数据提供者"""
        super().__init__("tdx_optimized")
        self.config = config or {}
        self.api = TdxHq_API()
        self.current_server = None
        
        # 优化的服务器列表 - 按地理位置和稳定性排序
        self.servers = [
            {"name": "深圳主站", "host": "119.147.212.81", "port": 7709, "priority": 1},
            {"name": "上海主站", "host": "114.80.63.12", "port": 7709, "priority": 1},
            {"name": "北京主站", "host": "123.125.108.23", "port": 7709, "priority": 1},
            {"name": "广州主站", "host": "180.153.39.51", "port": 7709, "priority": 2},
            {"name": "杭州主站", "host": "115.238.56.198", "port": 7709, "priority": 2},
            {"name": "南京主站", "host": "115.238.90.165", "port": 7709, "priority": 2},
            {"name": "四川主站", "host": "218.108.98.244", "port": 7709, "priority": 3},
            {"name": "重庆主站", "host": "218.108.47.69", "port": 7709, "priority": 3},
            {"name": "武汉主站", "host": "124.74.236.94", "port": 7709, "priority": 3},
            {"name": "西安主站", "host": "218.25.36.142", "port": 7709, "priority": 4},
            {"name": "沈阳主站", "host": "218.60.29.136", "port": 7709, "priority": 4},
            {"name": "青岛主站", "host": "218.108.50.178", "port": 7709, "priority": 4},
            {"name": "厦门主站", "host": "103.48.67.20", "port": 7709, "priority": 5},
            {"name": "福州主站", "host": "180.153.18.171", "port": 7709, "priority": 5},
            {"name": "备用服务器", "host": "106.120.74.86", "port": 7709, "priority": 5}
        ]
        
        # 优化的配置参数
        self.connection_timeout = self.config.get('connection_timeout', 3)  # 连接超时3秒
        self.socket_timeout = self.config.get('socket_timeout', 2)          # Socket超时2秒
        self.max_workers = self.config.get('max_workers', 5)                # 最大并发数
        self.retry_count = self.config.get('retry_count', 1)                # 减少重试次数
        
    def test_server_connectivity(self, server: Dict[str, Any], timeout: int = 2) -> bool:
        """快速测试服务器连通性
        
        Args:
            server: 服务器信息
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否可连接
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((server['host'], server['port']))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def get_available_servers(self, max_test: int = 8) -> List[Dict[str, Any]]:
        """并发测试服务器可用性
        
        Args:
            max_test: 最大测试服务器数量
            
        Returns:
            List[Dict]: 可用服务器列表，按优先级排序
        """
        print("正在测试服务器连通性...")
        available_servers = []
        
        # 按优先级排序，只测试前max_test个
        test_servers = sorted(self.servers, key=lambda x: x['priority'])[:max_test]
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有测试任务
            future_to_server = {
                executor.submit(self.test_server_connectivity, server, self.socket_timeout): server
                for server in test_servers
            }
            
            # 收集结果
            for future in as_completed(future_to_server, timeout=10):
                server = future_to_server[future]
                try:
                    if future.result():
                        available_servers.append(server)
                        print(f"  [OK] {server['name']} ({server['host']}:{server['port']})")
                    else:
                        print(f"  [ERROR] {server['name']} ({server['host']}:{server['port']})")
                except Exception as e:
                    print(f"  [ERROR] {server['name']} 测试异常: {e}")
        
        # 按优先级排序返回
        return sorted(available_servers, key=lambda x: x['priority'])
    
    def connect(self) -> bool:
        """连接到通达信服务器
        
        Returns:
            bool: 连接是否成功
        """
        print("开始连接通达信服务器...")
        
        # 获取可用服务器
        available_servers = self.get_available_servers()
        
        if not available_servers:
            print("[ERROR] 未发现可用服务器")
            return False
        
        print(f"发现 {len(available_servers)} 个可用服务器，开始尝试连接...")
        
        # 尝试连接可用服务器
        for i, server in enumerate(available_servers, 1):
            print(f"尝试连接 {i}/{len(available_servers)}: {server['name']}")
            
            try:
                # 创建新的API实例
                if hasattr(self, 'api') and self.api:
                    try:
                        self.api.disconnect()
                    except:
                        pass
                
                self.api = TdxHq_API()
                
                # 尝试连接
                if self.api.connect(server['host'], server['port'], time_out=self.connection_timeout):
                    # 验证连接 - 获取股票数量来验证
                    try:
                        count = self.api.get_security_count(0)  # 获取深圳市场股票数量
                        if count and count > 0:
                            self.current_server = server
                            print(f"[OK] 连接成功: {server['name']} ({server['host']}:{server['port']})")
                            return True
                    except Exception as e:
                        print(f"  连接验证失败: {e}")
                        self.api.disconnect()
                        continue
                else:
                    print(f"  连接失败: {server['name']}")
                    
            except Exception as e:
                print(f"  连接异常: {e}")
                continue
        
        print("[ERROR] 所有服务器连接失败")
        return False
    
    def disconnect(self):
        """断开连接"""
        if hasattr(self, 'api') and self.api:
            try:
                self.api.disconnect()
                print("[OK] 已断开连接")
            except:
                pass
        self.current_server = None
    
    def get_realtime_quotes(self, codes: List[str]) -> List[Dict[str, Any]]:
        """获取实时行情
        
        Args:
            codes: 股票代码列表
            
        Returns:
            List[Dict]: 行情数据列表
        """
        if not self.api or not self.current_server:
            print("[ERROR] 未连接到服务器")
            return []
        
        quotes = []
        
        try:
            for code in codes:
                # 判断市场
                market = 1 if code.startswith('6') else 0  # 1=上海, 0=深圳
                
                # 获取行情数据
                data = self.api.get_security_quotes(market, [code])
                
                if data and len(data) > 0:
                    quote_data = data[0]
                    quotes.append({
                        'code': code,
                        'name': quote_data.get('name', ''),
                        'price': quote_data.get('price', 0.0),
                        'last_close': quote_data.get('last_close', 0.0),
                        'open': quote_data.get('open', 0.0),
                        'high': quote_data.get('high', 0.0),
                        'low': quote_data.get('low', 0.0),
                        'volume': quote_data.get('vol', 0),
                        'amount': quote_data.get('amount', 0.0),
                        'bid1': quote_data.get('bid1', 0.0),
                        'ask1': quote_data.get('ask1', 0.0),
                        'change_pct': ((quote_data.get('price', 0) - quote_data.get('last_close', 0)) / quote_data.get('last_close', 1)) * 100 if quote_data.get('last_close', 0) > 0 else 0
                    })
                    
        except Exception as e:
            print(f"获取行情异常: {e}")
        
        return quotes
    
    def get_server_status(self) -> Dict[str, Any]:
        """获取服务器状态信息
        
        Returns:
            Dict: 服务器状态信息
        """
        available_servers = self.get_available_servers()
        
        return {
            'total_servers': len(self.servers),
            'available_servers': len(available_servers),
            'available_server_list': available_servers,
            'current_server': self.current_server,
            'connection_timeout': self.connection_timeout,
            'socket_timeout': self.socket_timeout
        }
    
    def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        return {
            'provider_name': self.name,
            'connected': self.current_server is not None,
            'current_server': self.current_server,
            'total_servers': len(self.servers),
            'config': {
                'connection_timeout': self.connection_timeout,
                'socket_timeout': self.socket_timeout,
                'max_workers': self.max_workers,
                'retry_count': self.retry_count
            }
        }