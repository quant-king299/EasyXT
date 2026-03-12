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

        # 服务器性能统计（用于记住最快的服务器）
        # 格式：{host: {'avg_time': float, 'success_count': int, 'fail_count': int}}
        self.server_stats = {}
        self.servers = self.config.get('servers', [
            # 优先级1：已验证可用的服务器
            {"host": "115.238.56.198", "port": 7709, "name": "杭州主站", "priority": 1},
            {"host": "115.238.90.165", "port": 7709, "name": "南京主站", "priority": 1},

            # 优先级2：主要城市服务器
            {"host": "119.147.212.81", "port": 7709, "name": "深圳主站", "priority": 2},
            {"host": "114.80.63.12", "port": 7709, "name": "上海主站", "priority": 2},
            {"host": "180.153.39.51", "port": 7709, "name": "广州主站", "priority": 2},
            {"host": "123.125.108.23", "port": 7709, "name": "北京主站", "priority": 2},
            {"host": "218.108.98.244", "port": 7709, "name": "四川主站", "priority": 2},
            {"host": "218.108.47.69", "port": 7709, "name": "重庆主站", "priority": 2},

            # 优先级3：其他地区服务器
            {"host": "180.153.18.171", "port": 7709, "name": "福州主站", "priority": 3},
            {"host": "103.48.67.20", "port": 7709, "name": "厦门主站", "priority": 3},
            {"host": "218.25.152.90", "port": 7709, "name": "武汉主站", "priority": 3},
            {"host": "218.60.29.136", "port": 7709, "name": "沈阳主站", "priority": 3},
            {"host": "124.74.236.94", "port": 7709, "name": "西安主站", "priority": 3},
            {"host": "61.152.107.141", "port": 7709, "name": "济南主站", "priority": 3},

            # 优先级4：备用服务器
            {"host": "202.108.253.130", "port": 7709, "name": "备用1", "priority": 4},
            {"host": "202.108.253.131", "port": 7709, "name": "备用2", "priority": 4},
            {"host": "14.215.128.18", "port": 7709, "name": "备用3", "priority": 4},
            {"host": "140.207.202.181", "port": 7709, "name": "备用4", "priority": 4}
        ])
        self.timeout = self.config.get('timeout', 10)
        self.retry_count = self.config.get('retry_count', 3)
        self.retry_delay = self.config.get('retry_delay', 1)
        
    def connect(self) -> bool:
        """连接到通达信服务器（智能选择最快服务器）

        Returns:
            bool: 连接是否成功
        """
        if self.connected:
            return True

        # 根据历史性能排序服务器（优先选择历史上最快的）
        servers = self._sort_servers_by_performance()

        for server in servers:
            try:
                self.logger.info(f"尝试连接服务器: {server['name']} ({server['host']}:{server['port']})")

                # 记录开始时间
                import time
                start_time = time.time()

                result = self.api.connect(server['host'], server['port'], time_out=self.timeout)

                # 计算连接耗时
                connect_time = time.time() - start_time

                if result:
                    self.connected = True
                    self.current_server = server
                    self.logger.info(f"连接成功: {server['name']} (耗时: {connect_time:.2f}秒)")

                    # 记录成功的连接时间
                    self._record_server_performance(server['host'], connect_time, success=True)
                    return True
                else:
                    self.logger.warning(f"连接失败: {server['name']}")
                    # 记录失败的连接
                    self._record_server_performance(server['host'], connect_time, success=False)

            except Exception as e:
                connect_time = time.time() - start_time
                self.logger.error(f"连接异常: {server['name']}, 错误: {e}")
                # 记录异常的连接
                self._record_server_performance(server['host'], connect_time, success=False)
                continue

        self.logger.error("所有服务器连接失败")
        return False

    def _sort_servers_by_performance(self) -> List[Dict]:
        """根据历史性能排序服务器

        优先级规则：
        1. 有历史记录的服务器按平均响应时间排序
        2. 无历史记录的服务器按配置的优先级排序
        3. 同优先级内，有记录的优于无记录的

        Returns:
            List[Dict]: 排序后的服务器列表
        """
        servers = self.servers.copy()

        def get_sort_key(server):
            host = server['host']
            priority = server.get('priority', 99)

            # 如果有历史性能数据
            if host in self.server_stats and self.server_stats[host]['success_count'] > 0:
                stats = self.server_stats[host]
                avg_time = stats['avg_time']
                # 成功率
                total = stats['success_count'] + stats['fail_count']
                success_rate = stats['success_count'] / total if total > 0 else 0

                # 排序键：(优先级, 平均响应时间, 成功率)
                # 平均时间越短越好，成功率越高越好
                return (priority, avg_time, -success_rate)
            else:
                # 无历史数据，排在同优先级的最后
                return (priority, 999, 0)

        return sorted(servers, key=get_sort_key)

    def _record_server_performance(self, host: str, connect_time: float, success: bool):
        """记录服务器性能数据

        Args:
            host: 服务器地址
            connect_time: 连接耗时（秒）
            success: 是否连接成功
        """
        if host not in self.server_stats:
            self.server_stats[host] = {
                'avg_time': 0,
                'success_count': 0,
                'fail_count': 0,
                'total_time': 0,
                'total_count': 0
            }

        stats = self.server_stats[host]

        if success:
            # 更新成功的连接时间（使用移动平均）
            stats['success_count'] += 1
            stats['total_time'] += connect_time
            stats['total_count'] += 1
            stats['avg_time'] = stats['total_time'] / stats['total_count']
        else:
            stats['fail_count'] += 1
            stats['total_count'] += 1
    
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
            return TDXParams.MARKET_SZ, code  # 深圳市场（股票）
        elif code.startswith('1'):
            return TDXParams.MARKET_SZ, code  # 深圳市场（基金）
        elif code.startswith(('600', '601', '603', '605', '688')):
            return TDXParams.MARKET_SH, code  # 上海市场（股票）
        elif code.startswith('5'):
            return TDXParams.MARKET_SH, code  # 上海市场（基金/ETF）
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
            # 判断是否为基金（5开头上海基金或1开头深圳基金）
            code = quote.get('code', '')
            is_etf = code.startswith('5') or code.startswith('1')

            # 通达信对基金价格做了10倍放大，需要还原
            price_divisor = 10.0 if is_etf else 1.0

            # 计算涨跌额和涨跌幅
            price = float(quote.get('price', 0)) / price_divisor
            last_close = float(quote.get('last_close', 0)) / price_divisor

            if last_close > 0:
                change = price - last_close
                change_pct = (change / last_close) * 100
            else:
                change = 0
                change_pct = 0

            return {
                'code': code,
                'name': quote.get('name', ''),
                'price': price,
                'last_close': last_close,
                'change': round(change, 2),
                'change_pct': round(change_pct, 2),
                'volume': int(quote.get('vol', 0)),
                'turnover': float(quote.get('amount', 0)),
                'high': float(quote.get('high', 0)) / price_divisor,
                'low': float(quote.get('low', 0)) / price_divisor,
                'open': float(quote.get('open', 0)) / price_divisor,
                # 五档买价
                'bid1': float(quote.get('bid1', 0)) / price_divisor,
                'bid2': float(quote.get('bid2', 0)) / price_divisor,
                'bid3': float(quote.get('bid3', 0)) / price_divisor,
                'bid4': float(quote.get('bid4', 0)) / price_divisor,
                'bid5': float(quote.get('bid5', 0)) / price_divisor,
                # 五档卖价
                'ask1': float(quote.get('ask1', 0)) / price_divisor,
                'ask2': float(quote.get('ask2', 0)) / price_divisor,
                'ask3': float(quote.get('ask3', 0)) / price_divisor,
                'ask4': float(quote.get('ask4', 0)) / price_divisor,
                'ask5': float(quote.get('ask5', 0)) / price_divisor,
                # 五档买量
                'bid1_vol': int(quote.get('bid1_vol', 0)),
                'bid2_vol': int(quote.get('bid2_vol', 0)),
                'bid3_vol': int(quote.get('bid3_vol', 0)),
                'bid4_vol': int(quote.get('bid4_vol', 0)),
                'bid5_vol': int(quote.get('bid5_vol', 0)),
                # 五档卖量
                'ask1_vol': int(quote.get('ask1_vol', 0)),
                'ask2_vol': int(quote.get('ask2_vol', 0)),
                'ask3_vol': int(quote.get('ask3_vol', 0)),
                'ask4_vol': int(quote.get('ask4_vol', 0)),
                'ask5_vol': int(quote.get('ask5_vol', 0)),
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

            # 判断是否为基金（5开头上海基金或1开头深圳基金）
            is_etf = std_code.startswith('5') or std_code.startswith('1')
            price_divisor = 10.0 if is_etf else 1.0

            # 获取分时数据
            data = self.api.get_minute_time_data(market, std_code, count)

            if not data:
                return []

            formatted_data = []
            for item in data:
                formatted_data.append({
                    'code': code,
                    'datetime': item.get('datetime', ''),
                    'price': float(item.get('price', 0)) / price_divisor,  # 修复基金价格
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

            # 判断是否为基金（5开头上海基金或1开头深圳基金）
            is_etf = std_code.startswith('5') or std_code.startswith('1')
            price_divisor = 10.0 if is_etf else 1.0

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
                    'open': float(item.get('open', 0)) / price_divisor,     # 修复基金价格
                    'high': float(item.get('high', 0)) / price_divisor,     # 修复基金价格
                    'low': float(item.get('low', 0)) / price_divisor,      # 修复基金价格
                    'close': float(item.get('close', 0)) / price_divisor,   # 修复基金价格
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

    def get_server_performance_stats(self) -> Dict[str, Any]:
        """获取服务器性能统计信息

        Returns:
            Dict: 服务器性能统计
            {
                'current_server': 当前连接的服务器,
                'servers': [
                    {
                        'host': 服务器地址,
                        'avg_time': 平均响应时间,
                        'success_count': 成功次数,
                        'fail_count': 失败次数,
                        'success_rate': 成功率
                    },
                    ...
                ]
            }
        """
        server_list = []

        for server in self.servers:
            host = server['host']
            if host in self.server_stats:
                stats = self.server_stats[host]
                total = stats['success_count'] + stats['fail_count']
                success_rate = stats['success_count'] / total if total > 0 else 0

                server_list.append({
                    'name': server['name'],
                    'host': host,
                    'avg_time': round(stats['avg_time'], 3),
                    'success_count': stats['success_count'],
                    'fail_count': stats['fail_count'],
                    'success_rate': round(success_rate * 100, 2)
                })
            else:
                # 无历史数据
                server_list.append({
                    'name': server['name'],
                    'host': host,
                    'avg_time': None,
                    'success_count': 0,
                    'fail_count': 0,
                    'success_rate': 0
                })

        # 按平均响应时间排序
        server_list.sort(key=lambda x: x['avg_time'] or 999)

        return {
            'current_server': self.current_server,
            'servers': server_list
        }

    def get_index_quotes(self, codes: List[str]) -> List[Dict[str, Any]]:
        """获取指数行情数据

        支持的指数代码：
        - 000001: 上证指数
        - 399001: 深证成指
        - 399006: 创业板指
        - 399005: 中小板指
        - 000300: 沪深300
        - 000016: 上证50
        - 000905: 中证500

        Args:
            codes: 指数代码列表（6位数字，如 '000001' 或 '000001.SH'）

        Returns:
            List[Dict]: 指数行情数据列表
        """
        if not codes:
            return []

        try:
            if not self._ensure_connected():
                self.logger.error("无法建立连接")
                return []

            # 准备指数代码和市场信息
            index_list = []
            for code in codes:
                # 移除后缀
                if '.' in code:
                    code = code.split('.')[0]

                # 指数使用市场ID 1（上海）或 0（深圳）
                # 上海指数以000、888开头
                if code.startswith(('000', '888')):
                    market = 1  # 上海市场
                else:
                    market = 0  # 深圳市场

                index_list.append((market, code))

            # 分批获取数据
            batch_size = 80
            all_quotes = []

            for i in range(0, len(index_list), batch_size):
                batch = index_list[i:i + batch_size]

                try:
                    # 获取指数行情
                    quotes = self.api.get_security_quotes(batch)

                    if quotes:
                        for quote in quotes:
                            formatted_quote = self._format_index_data(quote)
                            if formatted_quote:
                                all_quotes.append(formatted_quote)

                    # 避免请求过于频繁
                    if i + batch_size < len(index_list):
                        time.sleep(0.1)

                except Exception as e:
                    self.logger.error(f"获取指数批次数据失败: {e}")
                    continue

            self.logger.info(f"成功获取 {len(all_quotes)} 个指数的实时行情")
            return all_quotes

        except Exception as e:
            self.logger.error(f"获取指数行情失败: {e}")
            return []

    def _format_index_data(self, quote: Dict) -> Optional[Dict[str, Any]]:
        """格式化指数行情数据

        Args:
            quote: 原始指数行情数据

        Returns:
            Dict: 格式化后的指数行情数据
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
                'timestamp': int(time.time()),
                'source': 'tdx_index'
            }
        except Exception as e:
            self.logger.error(f"格式化指数行情数据失败: {e}")
            return None

    def __del__(self):
        """析构函数，确保连接被正确关闭"""
        try:
            self.disconnect()
        except Exception:
            pass