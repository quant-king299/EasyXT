"""
通达信数据提供者

基于pytdx库实现的通达信数据接口，支持实时行情和历史数据获取。
参考综合自定义交易系统v5.5.7.6.5项目的成熟实现。
"""

import time
import random
from typing import List, Dict, Any, Optional, Tuple
import logging
from pytdx.hq import TdxHq_API
from pytdx.params import TDXParams
from .base_provider import BaseDataProvider

logger = logging.getLogger(__name__)


class TdxDataProvider(BaseDataProvider):
    """通达信数据提供者
    
    提供通达信行情数据接口，包含连接管理、数据获取、异常处理等功能。
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化通达信数据提供者
        
        Args:
            config: 配置字典，包含服务器列表、超时设置等
        """
        super().__init__("tdx")
        self.config = config or {}
        self.api = TdxHq_API()
        self.current_server = None
        self.servers = self.config.get('servers', [
            {"host": "115.238.56.198", "port": 7709, "name": "杭州主站"},  # 已验证可用
            {"host": "115.238.90.165", "port": 7709, "name": "南京主站"},  # 已验证可用
            {"host": "119.147.212.81", "port": 7709, "name": "深圳主站"},
            {"host": "114.80.63.12", "port": 7709, "name": "上海主站"},
            {"host": "180.153.39.51", "port": 7709, "name": "广州主站"},
            {"host": "123.125.108.23", "port": 7709, "name": "北京主站"},
            {"host": "180.153.18.171", "port": 7709, "name": "福州主站"},
            {"host": "103.48.67.20", "port": 7709, "name": "厦门主站"}
        ])
        self.timeout = self.config.get('timeout', 10)
        self.retry_count = self.config.get('retry_count', 3)
        self.retry_delay = self.config.get('retry_delay', 1)
        
    def connect(self) -> bool:
        """连接到通达信服务器
        
        Returns:
            bool: 连接是否成功
        """
        if self.connected:
            return True
            
        # V3优化：严格按照配置的优先级顺序连接服务器，不随机打乱
        # 这样可以确保优先连接到验证可用的快速服务器
        servers = self.servers.copy()
        # 移除 random.shuffle(servers) - 保持配置的优先级顺序
        
        for server in servers:
            try:
                self.logger.info(f"尝试连接服务器: {server['host']}:{server['port']}")
                result = self.api.connect(server['host'], server['port'], time_out=self.timeout)
                
                if result:
                    self.connected = True
                    self.current_server = server
                    self.logger.info(f"连接成功: {server['host']}:{server['port']}")
                    return True
                else:
                    self.logger.warning(f"连接失败: {server['host']}:{server['port']}")
                    
            except Exception as e:
                self.logger.error(f"连接异常: {server['host']}:{server['port']}, 错误: {e}")
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
            # 使用正确的API方法测试连接
            count = self.api.get_security_count(0)  # 测试深圳市场
            return count > 0
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
                'source': 'tdx'
            }
        except Exception as e:
            self.logger.error(f"格式化行情数据失败: {e}")
            return None
    
    def get_minute_data(self, code: str, count: int = 240) -> List[Dict[str, Any]]:
        """获取分时数据
        
        Args:
            code: 股票代码
            count: 数据条数
            
        Returns:
            List[Dict]: 分时数据列表
        """
        try:
            if not self._ensure_connected():
                return []
            
            market, std_code = self._parse_stock_code(code)
            
            # 获取分时数据
            data = self.api.get_minute_time_data(market, std_code, count)
            
            if not data:
                return []
            
            formatted_data = []
            for item in data:
                formatted_data.append({
                    'code': code,
                    'datetime': item.get('datetime', ''),
                    'price': float(item.get('price', 0)),
                    'volume': int(item.get('vol', 0)),
                    'amount': float(item.get('amount', 0)),
                    'source': 'tdx'
                })
            
            return formatted_data
            
        except Exception as e:
            self.logger.error(f"获取分时数据失败: {e}")
            return []
    
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
                    'source': 'tdx'
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
    
    def get_market_status(self) -> Dict[str, Any]:
        """获取市场状态信息
        
        Returns:
            Dict: 市场状态信息
        """
        try:
            if not self._ensure_connected():
                return {}
            
            # 获取市场信息
            sz_count = self.api.get_security_count(0)  # 深圳市场
            sh_count = self.api.get_security_count(1)  # 上海市场
            
            return {
                'sz_market_count': sz_count,
                'sh_market_count': sh_count,
                'total_count': sz_count + sh_count,
                'server': self.current_server,
                'connected': self.connected,
                'timestamp': int(time.time())
            }
            
        except Exception as e:
            self.logger.error(f"获取市场状态失败: {e}")
            return {}
    
    def __del__(self):
        """析构函数，确保连接被正确关闭"""
        try:
            self.disconnect()
        except Exception:
            pass