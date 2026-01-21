"""
通达信数据提供者 - 增强版

解决连接问题的增强版本，包含更多服务器和更好的连接策略。
"""

import time
import random
import socket
from typing import List, Dict, Any, Optional, Tuple
import logging
from pytdx.hq import TdxHq_API
from pytdx.params import TDXParams
from .base_provider import BaseDataProvider

logger = logging.getLogger(__name__)


class TdxDataProviderEnhanced(BaseDataProvider):
    """通达信数据提供者 - 增强版
    
    提供更稳定的连接和更多的服务器选择
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化通达信数据提供者
        
        Args:
            config: 配置字典，包含服务器列表、超时设置等
        """
        super().__init__("tdx_enhanced")
        self.config = config or {}
        self.api = TdxHq_API()
        self.current_server = None
        
        # 扩展的服务器列表（包含更多可用服务器）
        self.servers = self.config.get('servers', [
            # 主要服务器
            {"host": "119.147.212.81", "port": 7709, "name": "深圳主站"},
            {"host": "114.80.63.12", "port": 7709, "name": "上海主站"},
            {"host": "180.153.39.51", "port": 7709, "name": "广州主站"},
            {"host": "218.108.98.244", "port": 7709, "name": "四川主站"},
            {"host": "218.108.47.69", "port": 7709, "name": "重庆主站"},
            
            # 备用服务器
            {"host": "180.153.18.171", "port": 7709, "name": "备用1"},
            {"host": "103.48.67.20", "port": 7709, "name": "备用2"},
            {"host": "14.215.128.18", "port": 7709, "name": "备用3"},
            {"host": "59.173.18.140", "port": 7709, "name": "备用4"},
            {"host": "202.108.253.130", "port": 7709, "name": "备用5"},
            
            # 扩展服务器
            {"host": "202.108.253.131", "port": 7709, "name": "扩展1"},
            {"host": "61.152.107.141", "port": 7709, "name": "扩展2"},
            {"host": "140.207.202.181", "port": 7709, "name": "扩展3"},
            {"host": "140.207.202.182", "port": 7709, "name": "扩展4"},
            {"host": "218.25.152.90", "port": 7709, "name": "扩展5"}
        ])
        
        self.timeout = self.config.get('timeout', 8)  # 减少超时时间
        self.retry_count = self.config.get('retry_count', 2)  # 减少重试次数
        self.retry_delay = self.config.get('retry_delay', 0.5)  # 减少重试延迟
        self.connection_test_timeout = 3  # 连接测试超时
        
    def _test_server_connectivity(self, host: str, port: int, timeout: int = 3) -> bool:
        """测试服务器连通性
        
        Args:
            host: 服务器地址
            port: 端口号
            timeout: 超时时间
            
        Returns:
            bool: 是否可连通
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def _get_available_servers(self) -> List[Dict]:
        """获取可用的服务器列表
        
        Returns:
            List[Dict]: 可用服务器列表
        """
        available_servers = []
        
        self.logger.info("正在测试服务器连通性...")
        
        for server in self.servers:
            if self._test_server_connectivity(server['host'], server['port'], self.connection_test_timeout):
                available_servers.append(server)
                self.logger.info(f"[OK] {server['name']} ({server['host']}:{server['port']}) 可连通")
            else:
                self.logger.debug(f"[ERROR] {server['name']} ({server['host']}:{server['port']}) 不可连通")
        
        if available_servers:
            self.logger.info(f"发现 {len(available_servers)} 个可用服务器")
        else:
            self.logger.warning("未发现可用服务器，将尝试所有服务器")
            available_servers = self.servers  # 如果都不通，还是尝试所有服务器
        
        return available_servers
    
    def connect(self) -> bool:
        """连接到通达信服务器
        
        Returns:
            bool: 连接是否成功
        """
        if self.connected:
            return True
        
        # 获取可用服务器
        available_servers = self._get_available_servers()
        
        # 随机打乱服务器顺序，避免都连接同一个服务器
        random.shuffle(available_servers)
        
        for server in available_servers:
            try:
                self.logger.info(f"尝试连接: {server['name']} ({server['host']}:{server['port']})")
                
                # 设置较短的超时时间
                result = self.api.connect(server['host'], server['port'], time_out=self.timeout)
                
                if result:
                    # 测试连接是否真正可用
                    try:
                        test_result = self.api.get_markets()
                        if test_result is not None:
                            self.connected = True
                            self.current_server = server
                            self.logger.info(f"[OK] 连接成功: {server['name']} ({server['host']}:{server['port']})")
                            return True
                        else:
                            self.logger.warning(f"连接测试失败: {server['name']}")
                    except Exception as e:
                        self.logger.warning(f"连接测试异常: {server['name']}, 错误: {e}")
                else:
                    self.logger.debug(f"连接失败: {server['name']}")
                    
            except Exception as e:
                self.logger.debug(f"连接异常: {server['name']}, 错误: {e}")
                continue
        
        self.logger.error("所有服务器连接失败")
        return False
    
    def disconnect(self) -> None:
        """断开连接"""
        try:
            if self.connected:
                self.api.disconnect()
                self.connected = False
                self.current_server = None
                self.logger.info("连接已断开")
        except Exception as e:
            self.logger.error(f"断开连接异常: {e}")
    
    def _ensure_connected(self) -> bool:
        """确保连接可用，如果断开则重连
        
        Returns:
            bool: 连接是否可用
        """
        if not self.connected:
            return self.connect()
        
        # 测试连接是否正常
        try:
            # 获取市场数量来测试连接
            self.api.get_markets()
            return True
        except Exception as e:
            self.logger.warning(f"连接测试失败，尝试重连: {e}")
            self.connected = False
            return self.connect()
    
    def _parse_stock_code(self, code: str) -> Tuple[int, str]:
        """解析股票代码，返回市场ID和标准代码
        
        Args:
            code: 股票代码，如 '000001' 或 '000001.SZ'
            
        Returns:
            Tuple[int, str]: (市场ID, 标准代码)
        """
        # 移除后缀
        if '.' in code:
            code = code.split('.')[0]
        
        # 根据代码前缀判断市场
        if code.startswith(('000', '001', '002', '003', '300')):
            return TDXParams.MARKET_SZ, code  # 深圳市场
        elif code.startswith(('600', '601', '603', '605', '688')):
            return TDXParams.MARKET_SH, code  # 上海市场
        else:
            # 默认深圳市场
            return TDXParams.MARKET_SZ, code
    
    def get_realtime_quotes(self, codes: List[str]) -> List[Dict[str, Any]]:
        """获取实时行情数据
        
        Args:
            codes: 股票代码列表
            
        Returns:
            List[Dict]: 行情数据列表
        """
        if not codes:
            return []
        
        for attempt in range(self.retry_count):
            try:
                if not self._ensure_connected():
                    self.logger.error("无法建立连接")
                    return []
                
                # 准备股票代码和市场信息
                stock_list = []
                for code in codes:
                    market, std_code = self._parse_stock_code(code)
                    stock_list.append((market, std_code))
                
                # 分批获取数据（通达信API限制每次最多80只股票）
                batch_size = 80
                all_quotes = []
                
                for i in range(0, len(stock_list), batch_size):
                    batch = stock_list[i:i + batch_size]
                    
                    try:
                        # 获取实时行情
                        quotes = self.api.get_security_quotes(batch)
                        
                        if quotes:
                            for quote in quotes:
                                formatted_quote = self._format_quote_data(quote)
                                if formatted_quote:
                                    all_quotes.append(formatted_quote)
                        
                        # 避免请求过于频繁
                        if i + batch_size < len(stock_list):
                            time.sleep(0.1)
                            
                    except Exception as e:
                        self.logger.error(f"获取批次数据失败: {e}")
                        continue
                
                self.logger.info(f"成功获取 {len(all_quotes)} 只股票的实时行情")
                return all_quotes
                
            except Exception as e:
                self.logger.error(f"获取实时行情失败 (尝试 {attempt + 1}/{self.retry_count}): {e}")
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay)
                    self.connected = False  # 强制重连
                else:
                    return []
        
        return []
    
    def _format_quote_data(self, quote: Dict) -> Optional[Dict[str, Any]]:
        """格式化行情数据为统一格式
        
        Args:
            quote: 原始行情数据
            
        Returns:
            Dict: 格式化后的行情数据
        """
        try:
            # 计算涨跌额和涨跌幅
            price = float(quote.get('price', 0))
            last_close = float(quote.get('last_close', 0))
            
            if last_close > 0:
                change = price - last_close
                change_pct = (change / last_close) * 100
            else:
                change = 0
                change_pct = 0
            
            return {
                'code': quote.get('code', ''),
                'name': quote.get('name', ''),
                'price': price,
                'last_close': last_close,
                'change': round(change, 2),
                'change_pct': round(change_pct, 2),
                'volume': int(quote.get('vol', 0)),
                'turnover': float(quote.get('amount', 0)),
                'high': float(quote.get('high', 0)),
                'low': float(quote.get('low', 0)),
                'open': float(quote.get('open', 0)),
                'bid1': float(quote.get('bid1', 0)),
                'ask1': float(quote.get('ask1', 0)),
                'bid1_vol': int(quote.get('bid1_vol', 0)),
                'ask1_vol': int(quote.get('ask1_vol', 0)),
                'timestamp': int(time.time()),
                'source': 'tdx_enhanced'
            }
        except Exception as e:
            self.logger.error(f"格式化行情数据失败: {e}")
            return None
    
    def get_kline_data(self, code: str, period: str = 'D', count: int = 100) -> List[Dict[str, Any]]:
        """获取K线数据
        
        Args:
            code: 股票代码
            period: 周期 ('1', '5', '15', '30', '60', 'D', 'W', 'M')
            count: 数据条数
            
        Returns:
            List[Dict]: K线数据列表
        """
        try:
            if not self._ensure_connected():
                return []
            
            market, std_code = self._parse_stock_code(code)
            
            # 周期映射
            period_map = {
                '1': 8,    # 1分钟
                '5': 0,    # 5分钟
                '15': 1,   # 15分钟
                '30': 2,   # 30分钟
                '60': 3,   # 60分钟
                'D': 9,    # 日线
                'W': 5,    # 周线
                'M': 6     # 月线
            }
            
            period_id = period_map.get(period, 9)  # 默认日线
            
            # 获取K线数据
            data = self.api.get_security_bars(period_id, market, std_code, 0, count)
            
            if not data:
                return []
            
            formatted_data = []
            for item in data:
                formatted_data.append({
                    'code': code,
                    'datetime': item.get('datetime', ''),
                    'open': float(item.get('open', 0)),
                    'high': float(item.get('high', 0)),
                    'low': float(item.get('low', 0)),
                    'close': float(item.get('close', 0)),
                    'volume': int(item.get('vol', 0)),
                    'amount': float(item.get('amount', 0)),
                    'period': period,
                    'source': 'tdx_enhanced'
                })
            
            return formatted_data
            
        except Exception as e:
            self.logger.error(f"获取K线数据失败: {e}")
            return []
    
    def is_available(self) -> bool:
        """检查数据源是否可用
        
        Returns:
            bool: 数据源是否可用
        """
        try:
            return self._ensure_connected()
        except Exception:
            return False
    
    def get_server_status(self) -> Dict[str, Any]:
        """获取服务器状态信息
        
        Returns:
            Dict: 服务器状态信息
        """
        try:
            available_servers = self._get_available_servers()
            
            return {
                'current_server': self.current_server,
                'connected': self.connected,
                'total_servers': len(self.servers),
                'available_servers': len(available_servers),
                'available_server_list': available_servers,
                'timestamp': int(time.time())
            }
            
        except Exception as e:
            self.logger.error(f"获取服务器状态失败: {e}")
            return {}
    
    def __del__(self):
        """析构函数，确保连接被正确关闭"""
        try:
            self.disconnect()
        except Exception:
            pass