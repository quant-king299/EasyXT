"""
东方财富数据提供者 - 更新版

修复连接问题，更新API端点和请求头
"""

import json
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode

try:
    from .base_provider import BaseDataProvider
except ImportError:
    # 如果无法导入，创建一个简单的基类
    class BaseDataProvider:
        def __init__(self, name):
            self.name = name
            self.logger = logging.getLogger(name)
            self.connected = False


class EastmoneyDataProviderV2(BaseDataProvider):
    """东方财富数据提供者 - 更新版"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化东方财富数据提供者

        Args:
            config: 配置参数
        """
        super().__init__('eastmoney_v2')
        self.config = config or {}

        # 基础配置 - 更新的API端点
        self.base_url = "https://push2.eastmoney.com"
        self.quote_url = "https://qt.gtimg.cn"
        self.api_url = "https://api.futures.eastmoney.com"

        # 请求配置
        self.timeout = self.config.get('timeout', 10)
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 1)

        # 创建session以复用连接
        self.session = self._create_session()

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

    def _create_session(self) -> requests.Session:
        """创建带有重试机制的session

        Returns:
            requests.Session: 配置好的session对象
        """
        session = requests.Session()

        # 配置重试策略
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _get_headers(self) -> Dict[str, str]:
        """获取完整的HTTP请求头

        Returns:
            Dict: 请求头字典
        """
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://quote.eastmoney.com/',
            'Origin': 'https://quote.eastmoney.com',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'sec-ch-ua': '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }

    def connect(self) -> bool:
        """连接到东方财富数据源

        Returns:
            bool: 连接是否成功
        """
        try:
            # 尝试多个测试端点
            test_endpoints = [
                # 方法1: 使用新的API格式
                {
                    'url': f"{self.base_url}/api/qt/clist/get",
                    'params': {
                        'pn': '1',
                        'pz': '1',
                        'po': '1',
                        'np': '1',
                        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                        'fltt': '2',
                        'invt': '2',
                        'fid': 'f3',
                        'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
                        'fields': 'f12,f14'
                    }
                },
                # 方法2: 使用更简单的参数
                {
                    'url': f"{self.base_url}/api/qt/ulist.np/get",
                    'params': {
                        'fltt': '2',
                        'invt': '2',
                        'secids': '0.000001',
                        'fields': 'f12,f14,f2,f3'
                    }
                },
                # 方法3: 备用端点
                {
                    'url': 'https://pdfm.eastmoney.com/EM_UBG_PDTI_Fast/apiJS',
                    'params': {
                        'type': 'UA',
                        'sty': 'FCOYTA',
                        'cmd': '',
                        'p': '1',
                        'ps': '1'
                    }
                }
            ]

            for i, endpoint in enumerate(test_endpoints, 1):
                try:
                    self.logger.info(f"尝试连接方法 {i}/{len(test_endpoints)}...")
                    response = self._make_request(endpoint['url'], endpoint['params'])

                    if response and response.status_code == 200:
                        self._connected = True
                        self._last_connect_time = time.time()
                        self.logger.info(f"东方财富数据源连接成功 (方法{i})")
                        return True

                except Exception as e:
                    self.logger.debug(f"方法{i}连接失败: {e}")
                    continue

            self._connected = False
            self.logger.error("东方财富数据源连接失败 - 所有方法均失败")
            return False

        except Exception as e:
            self._connected = False
            self.logger.error(f"连接东方财富数据源异常: {e}")
            return False

    def disconnect(self) -> None:
        """断开连接"""
        self._connected = False
        if hasattr(self, 'session'):
            self.session.close()
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
            'code': 'eastmoney_v2',
            'description': '东方财富实时行情数据源（更新版）',
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
            headers: 请求头（可选，如果不提供则使用默认头）

        Returns:
            requests.Response: 响应对象
        """
        if headers is None:
            headers = self._get_headers()

        for attempt in range(self.max_retries):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True
                )

                if response.status_code == 200:
                    return response
                else:
                    self.logger.warning(f"请求失败，状态码: {response.status_code}")

            except requests.exceptions.Timeout as e:
                self.logger.warning(f"请求超时 (尝试 {attempt + 1}/{self.max_retries}): {e}")

            except requests.exceptions.ConnectionError as e:
                self.logger.warning(f"连接错误 (尝试 {attempt + 1}/{self.max_retries}): {e}")

            except requests.exceptions.RequestException as e:
                self.logger.warning(f"请求异常 (尝试 {attempt + 1}/{self.max_retries}): {e}")

            except Exception as e:
                self.logger.error(f"未知异常 (尝试 {attempt + 1}/{self.max_retries}): {e}")

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

            # 尝试多个API端点
            api_endpoints = [
                # 端点1: 新版API
                {
                    'url': f"{self.base_url}/api/qt/ulist.np/get",
                    'params': {
                        'fltt': '2',
                        'invt': '2',
                        'fields': ','.join(self.quote_fields),
                        'secids': ','.join(secids),
                        'ut': 'fa5fd1943c7b386f172d6893dbfba10b'
                    }
                },
                # 端点2: 备用API
                {
                    'url': f"{self.base_url}/api/qt/stock/get",
                    'params': {
                        'secids': ','.join(secids),
                        'fields': 'f12,f14,f2,f3,f4,f5,f6,f15,f16,f17,f18'
                    }
                }
            ]

            for endpoint in api_endpoints:
                try:
                    response = self._make_request(endpoint['url'], endpoint['params'])
                    if not response:
                        continue

                    # 解析响应数据
                    data = response.json()

                    if data.get('rc') == 0 and 'data' in data and data['data']:
                        quotes = []

                        for item in data['data'].get('diff', []):
                            quote_info = self._parse_quote_data(item)
                            if quote_info:
                                quotes.append(quote_info)

                        if quotes:
                            self.logger.info(f"成功获取实时行情: {len(quotes)}只股票")
                            return quotes

                except Exception as e:
                    self.logger.debug(f"端点 {endpoint['url']} 获取失败: {e}")
                    continue

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
                'source': 'eastmoney_v2'
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
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
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
                    if value is None or value == '-' or value == '':
                        return default
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return default

                def safe_int(value, default=0):
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
                        'source': 'eastmoney_v2'
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
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
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
                    if value is None or value == '-' or value == '':
                        return default
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return default

                def safe_int(value, default=0):
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
                        'source': 'eastmoney_v2'
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
                    'source': 'eastmoney_v2'
                }

            return {
                'market_status': 'unknown',
                'timestamp': int(time.time()),
                'source': 'eastmoney_v2'
            }

        except Exception as e:
            self.logger.error(f"获取市场状态失败: {e}")
            return {
                'market_status': 'error',
                'error': str(e),
                'timestamp': int(time.time()),
                'source': 'eastmoney_v2'
            }

    def __del__(self):
        """析构函数"""
        try:
            self.disconnect()
        except Exception:
            pass
