"""
东方财富数据提供者

基于HTTP请求实现的东方财富数据接口，支持实时行情、资金流向、热门股票等数据获取。
参考综合交易系统项目的成熟实现方案。
"""

import json
import time
import requests
import logging
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode

from .base_provider import BaseDataProvider


class EastmoneyDataProvider(BaseDataProvider):
    """东方财富数据提供者"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化东方财富数据提供者
        
        Args:
            config: 配置参数
        """
        super().__init__('eastmoney')
        self.config = config or {}
        
        # 基础配置
        self.base_url = "https://push2.eastmoney.com"
        self.quote_url = "https://qt.gtimg.cn"
        self.fund_url = "https://push2his.eastmoney.com"
        
        # 请求配置
        self.timeout = self.config.get('timeout', 10)
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 1)
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 市场代码映射
        self.market_mapping = {
            'sh': '1',  # 上海
            'sz': '0',  # 深圳
            'bj': '0'   # 北京
        }
        
        # 数据字段映射
        self.quote_fields = [
            'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10',
            'f11', 'f12', 'f13', 'f14', 'f15', 'f16', 'f17', 'f18', 'f20',
            'f21', 'f23', 'f24', 'f25', 'f22', 'f33', 'f11', 'f62', 'f128',
            'f136', 'f115', 'f152'
        ]
        
        self._connected = False
        self._last_connect_time = 0
        
    def connect(self) -> bool:
        """连接到东方财富数据源
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 测试连接
            test_url = f"{self.base_url}/api/qt/clist/get"
            params = {
                'pn': '1',
                'pz': '1',
                'po': '1',
                'np': '1',
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': '2',
                'invt': '2',
                'fid': 'f3',
                'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
                'fields': 'f12,f14'
            }
            
            response = self._make_request(test_url, params)
            if response and response.status_code == 200:
                self._connected = True
                self._last_connect_time = time.time()
                self.logger.info("东方财富数据源连接成功")
                return True
            
            self._connected = False
            self.logger.error("东方财富数据源连接失败")
            return False
            
        except Exception as e:
            self._connected = False
            self.logger.error(f"连接东方财富数据源异常: {e}")
            return False
    
    def disconnect(self) -> None:
        """断开连接"""
        self._connected = False
        self.logger.info("已断开东方财富数据源连接")
    
    def is_connected(self) -> bool:
        """检查连接状态
        
        Returns:
            bool: 是否已连接
        """
        # 检查连接时效性（5分钟）
        if self._connected and time.time() - self._last_connect_time > 300:
            return self.connect()
        return self._connected
    
    def is_available(self) -> bool:
        """检查数据源是否可用
        
        Returns:
            bool: 数据源是否可用
        """
        return self.is_connected()
    
    def get_provider_info(self) -> Dict[str, Any]:
        """获取数据源信息
        
        Returns:
            Dict: 数据源信息
        """
        return {
            'name': '东方财富',
            'code': 'eastmoney',
            'description': '东方财富实时行情数据源',
            'supported_markets': ['沪A', '深A', '创业板', '科创板'],
            'supported_data_types': ['实时行情', '资金流向', '热门股票', '板块数据'],
            'update_frequency': '实时',
            'connected': self.is_connected()
        }
    
    def _make_request(self, url: str, params: Optional[Dict] = None, 
                     headers: Optional[Dict] = None) -> Optional[requests.Response]:
        """发送HTTP请求
        
        Args:
            url: 请求URL
            params: 请求参数
            headers: 请求头
            
        Returns:
            requests.Response: 响应对象
        """
        if headers is None:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://quote.eastmoney.com/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url, 
                    params=params, 
                    headers=headers, 
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    return response
                else:
                    self.logger.warning(f"请求失败，状态码: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"请求异常 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
        
        return None
    
    def get_realtime_quotes(self, codes: List[str]) -> List[Dict[str, Any]]:
        """获取实时行情数据
        
        Args:
            codes: 股票代码列表，格式如 ['000001', '000002']
            
        Returns:
            List[Dict]: 实时行情数据列表
        """
        if not self.is_connected():
            self.logger.error("数据源未连接")
            return []
        
        try:
            # 构建股票代码字符串
            secids = []
            for symbol in codes:
                if symbol.startswith('6'):
                    secids.append(f"1.{symbol}")  # 沪市
                elif symbol.startswith(('0', '3')):
                    secids.append(f"0.{symbol}")  # 深市
                elif symbol.startswith('8') or symbol.startswith('4'):
                    secids.append(f"0.{symbol}")  # 北交所
            
            if not secids:
                return []
            
            # 构建请求URL
            url = f"{self.base_url}/api/qt/ulist.np/get"
            params = {
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': '2',
                'invt': '2',
                'fields': ','.join(self.quote_fields),
                'secids': ','.join(secids)
            }
            
            response = self._make_request(url, params)
            if not response:
                return []
            
            # 解析响应数据
            data = response.json()
            
            if data.get('rc') == 0 and 'data' in data and data['data']:
                quotes = []
                
                for item in data['data']['diff']:
                    quote_info = self._parse_quote_data(item)
                    if quote_info:
                        quotes.append(quote_info)
                
                self.logger.info(f"成功获取实时行情: {len(quotes)}只股票")
                return quotes
            
            return []
            
        except Exception as e:
            self.logger.error(f"获取实时行情失败: {e}")
            return []
    
    def _parse_quote_data(self, item: Dict) -> Optional[Dict[str, Any]]:
        """解析行情数据
        
        Args:
            item: 原始行情数据
            
        Returns:
            Dict: 格式化的行情数据
        """
        try:
            def safe_float(value, default=0.0):
                """安全转换为浮点数"""
                if value is None or value == '-' or value == '':
                    return default
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return default
            
            def safe_int(value, default=0):
                """安全转换为整数"""
                if value is None or value == '-' or value == '':
                    return default
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return default
            
            return {
                'symbol': item.get('f12', ''),
                'name': item.get('f14', ''),
                'price': safe_float(item.get('f2')),
                'change': safe_float(item.get('f4')),
                'change_pct': safe_float(item.get('f3')),
                'volume': safe_int(item.get('f5')),
                'amount': safe_float(item.get('f6')),
                'open': safe_float(item.get('f17')),
                'high': safe_float(item.get('f15')),
                'low': safe_float(item.get('f16')),
                'pre_close': safe_float(item.get('f18')),
                'bid1': safe_float(item.get('f31')),
                'ask1': safe_float(item.get('f32')),
                'bid1_vol': safe_int(item.get('f33')),
                'ask1_vol': safe_int(item.get('f34')),
                'timestamp': int(time.time()),
                'source': 'eastmoney'
            }
        except Exception as e:
            self.logger.warning(f"解析行情数据失败: {e}")
            return None
    
    def get_hot_stocks(self, market: str = 'all', count: int = 50) -> List[Dict[str, Any]]:
        """获取热门股票
        
        Args:
            market: 市场类型 ('all', 'sh', 'sz')
            count: 获取数量
            
        Returns:
            List[Dict]: 热门股票数据
        """
        try:
            # 市场过滤条件
            if market == 'sh':
                fs = 'm:1+t:2,m:1+t:23'
            elif market == 'sz':
                fs = 'm:0+t:6,m:0+t:80'
            else:
                fs = 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23'
            
            url = f"{self.base_url}/api/qt/clist/get"
            params = {
                'pn': '1',
                'pz': str(count),
                'po': '1',
                'np': '1',
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': '2',
                'invt': '2',
                'fid': 'f62',  # 按主力净流入排序
                'fs': fs,
                'fields': 'f12,f14,f2,f3,f4,f5,f6,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87'
            }
            
            response = self._make_request(url, params)
            if not response:
                return []
            
            data = response.json()
            
            if data.get('rc') == 0 and 'data' in data and data['data']:
                stocks = []
                
                def safe_float(value, default=0.0):
                    """安全转换为浮点数"""
                    if value is None or value == '-' or value == '':
                        return default
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return default
                
                def safe_int(value, default=0):
                    """安全转换为整数"""
                    if value is None or value == '-' or value == '':
                        return default
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        return default
                
                for i, item in enumerate(data['data']['diff']):
                    stock_info = {
                        'rank': i + 1,
                        'symbol': item.get('f12', ''),
                        'name': item.get('f14', ''),
                        'price': safe_float(item.get('f2')),
                        'change_pct': safe_float(item.get('f3')),
                        'volume': safe_int(item.get('f5')),
                        'amount': safe_float(item.get('f6')),
                        'main_net_inflow': safe_float(item.get('f62')),
                        'main_net_inflow_pct': safe_float(item.get('f184')),
                        'timestamp': int(time.time()),
                        'source': 'eastmoney'
                    }
                    stocks.append(stock_info)
                
                self.logger.info(f"成功获取热门股票: {len(stocks)}只")
                return stocks
            
            return []
            
        except Exception as e:
            self.logger.error(f"获取热门股票失败: {e}")
            return []
    
    def get_sector_data(self, sector_type: str = 'concept') -> List[Dict[str, Any]]:
        """获取板块数据
        
        Args:
            sector_type: 板块类型 ('concept', 'industry')
            
        Returns:
            List[Dict]: 板块数据
        """
        try:
            # 板块类型映射
            if sector_type == 'concept':
                fs = 'm:90+t:3'
                fid = 'f104'  # 概念板块按涨跌幅排序
            elif sector_type == 'industry':
                fs = 'm:90+t:2'
                fid = 'f104'  # 行业板块按涨跌幅排序
            else:
                return []
            
            url = f"{self.base_url}/api/qt/clist/get"
            params = {
                'pn': '1',
                'pz': '50',
                'po': '1',
                'np': '1',
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': '2',
                'invt': '2',
                'fid': fid,
                'fs': fs,
                'fields': 'f12,f14,f2,f3,f4,f104,f105,f106,f107,f108'
            }
            
            response = self._make_request(url, params)
            if not response:
                return []
            
            data = response.json()
            
            if data.get('rc') == 0 and 'data' in data and data['data']:
                sectors = []
                
                def safe_float(value, default=0.0):
                    """安全转换为浮点数"""
                    if value is None or value == '-' or value == '':
                        return default
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return default
                
                def safe_int(value, default=0):
                    """安全转换为整数"""
                    if value is None or value == '-' or value == '':
                        return default
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        return default
                
                for i, item in enumerate(data['data']['diff']):
                    sector_info = {
                        'rank': i + 1,
                        'code': item.get('f12', ''),
                        'name': item.get('f14', ''),
                        'change_pct': safe_float(item.get('f104')),
                        'up_count': safe_int(item.get('f105')),
                        'down_count': safe_int(item.get('f106')),
                        'total_count': safe_int(item.get('f107')),
                        'leader_symbol': item.get('f108', ''),
                        'sector_type': sector_type,
                        'timestamp': int(time.time()),
                        'source': 'eastmoney'
                    }
                    sectors.append(sector_info)
                
                self.logger.info(f"成功获取{sector_type}板块数据: {len(sectors)}个")
                return sectors
            
            return []
            
        except Exception as e:
            self.logger.error(f"获取板块数据失败: {e}")
            return []
    
    def get_market_status(self) -> Dict[str, Any]:
        """获取市场状态
        
        Returns:
            Dict: 市场状态信息
        """
        try:
            # 获取上证指数作为市场状态指标
            quotes = self.get_realtime_quotes(['000001'])
            
            if quotes:
                index_data = quotes[0]
                
                # 判断市场状态
                current_time = time.strftime('%H:%M:%S')
                is_trading = '09:30:00' <= current_time <= '11:30:00' or '13:00:00' <= current_time <= '15:00:00'
                
                return {
                    'market_status': 'trading' if is_trading else 'closed',
                    'index_price': index_data.get('price', 0),
                    'index_change': index_data.get('change', 0),
                    'index_change_pct': index_data.get('change_pct', 0),
                    'timestamp': int(time.time()),
                    'source': 'eastmoney'
                }
            
            return {
                'market_status': 'unknown',
                'timestamp': int(time.time()),
                'source': 'eastmoney'
            }
            
        except Exception as e:
            self.logger.error(f"获取市场状态失败: {e}")
            return {
                'market_status': 'error',
                'error': str(e),
                'timestamp': int(time.time()),
                'source': 'eastmoney'
            }