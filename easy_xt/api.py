"""
EasyXT主API入口
统一的API接口，简化xtquant的使用
"""
import pandas as pd
from typing import Union, List, Optional, Dict, Any
from .data_api import DataAPI
from .trade_api import TradeAPI
from .extended_api import ExtendedAPI
from .config import config
from .utils import ErrorHandler

class EasyXT:
    """
    EasyXT主API类
    提供统一的数据和交易接口
    """
    
    def __init__(self):
        self.data = DataAPI()
        self.trade = TradeAPI()
        self._data_connected = False
        self._trade_connected = False
    
    def init_data(self) -> bool:
        """
        初始化数据服务
        
        Returns:
            bool: 是否成功
        """
        self._data_connected = self.data.connect()
        if self._data_connected:
            print("数据服务初始化成功")
        else:
            print("数据服务初始化失败")
        return self._data_connected
    
    def init_trade(self, userdata_path: str, session_id: Optional[str] = None) -> bool:
        """
        初始化交易服务
        
        Args:
            userdata_path: 迅投客户端userdata路径
            session_id: 会话ID
            
        Returns:
            bool: 是否成功
        """
        self._trade_connected = self.trade.connect(userdata_path, session_id if session_id else "")
        if self._trade_connected:
            print("交易服务初始化成功")
        else:
            print("交易服务初始化失败")
        return self._trade_connected
    
    def add_account(self, account_id: str, account_type: str = 'STOCK') -> bool:
        """
        添加交易账户
        
        Args:
            account_id: 资金账号
            account_type: 账户类型
            
        Returns:
            bool: 是否成功
        """
        if not self._trade_connected:
            ErrorHandler.log_error("交易服务未初始化")
            return False
        return self.trade.add_account(account_id, account_type)
    
    # ==================== 数据接口 ====================
    
    def get_price(self, 
                  codes: Union[str, List[str]], 
                  start: Optional[str] = None, 
                  end: Optional[str] = None, 
                  period: str = '1d',
                  count: Optional[int] = None,
                  fields: Optional[List[str]] = None,
                  adjust: str = 'front') -> pd.DataFrame:
        """
        获取股票价格数据
        
        Args:
            codes: 股票代码，支持单个或多个
            start: 开始日期，支持多种格式
            end: 结束日期，支持多种格式  
            period: 周期，支持'1d', '1m', '5m', '15m', '30m', '1h'
            count: 数据条数，如果指定则忽略start
            fields: 字段列表，默认['open', 'high', 'low', 'close', 'volume']
            adjust: 复权类型，'front'前复权, 'back'后复权, 'none'不复权
            
        Returns:
            DataFrame: 价格数据
        """
        return self.data.get_price(codes, start, end, period, count, fields, adjust)
    
    def get_current_price(self, codes: Union[str, List[str]]) -> pd.DataFrame:
        """
        获取当前价格（实时行情）
        
        Args:
            codes: 股票代码
            
        Returns:
            DataFrame: 实时价格数据
        """
        return self.data.get_current_price(codes)

    def get_order_book(self, codes: Union[str, List[str]]) -> pd.DataFrame:
        """
        获取五档行情数据（买卖盘口）

        Args:
            codes: 股票代码

        Returns:
            DataFrame: 包含五档买卖价和量的数据
            字段包括：
            - code: 股票代码
            - lastPrice: 最新价
            - bid1-bid5: 买一到买五价格
            - ask1-ask5: 卖一到卖五价格
            - bidVol1-bidVol5: 买一到买五量
            - askVol1-askVol5: 卖一到卖五量

        Example:
            >>> # 获取单只股票五档行情
            >>> order_book = api.get_order_book('000001.SZ')
            >>> print(order_book)
            >>> # 获取多只股票五档行情
            >>> order_book = api.get_order_book(['000001.SZ', '600000.SH'])
        """
        return self.data.get_order_book(codes)

    def get_l2_quote(self, codes: Union[str, List[str]]) -> Dict[str, Dict]:
        """
        获取Level2五档行情数据（专用接口，返回原始数据）

        Args:
            codes: 股票代码

        Returns:
            Dict: {股票代码: {字段: 值}}
            包含完整的五档买卖价量等Level2数据

        Example:
            >>> # 获取Level2行情
            >>> l2_data = api.get_l2_quote('000001.SZ')
            >>> for code, data in l2_data.items():
            ...     print(f"{code}: 买一 {data.get('bid1')} 卖一 {data.get('ask1')}")
        """
        return self.data.get_l2_quote(codes)

    def get_financial_data(self, 
                          codes: Union[str, List[str]], 
                          tables: Optional[List[str]] = None,
                          start: Optional[str] = None, 
                          end: Optional[str] = None,
                          report_type: str = 'report_time') -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        获取财务数据
        
        Args:
            codes: 股票代码
            tables: 财务表类型，如['Balance', 'Income', 'CashFlow']
            start: 开始时间
            end: 结束时间
            report_type: 'report_time'报告期, 'announce_time'公告期
            
        Returns:
            Dict: {股票代码: {表名: DataFrame}}
        """
        return self.data.get_financial_data(codes, tables, start, end, report_type)
    
    def get_stock_list(self, sector: Optional[str] = None) -> List[str]:
        """
        获取股票列表
        
        Args:
            sector: 板块名称，如'沪深300', 'A股'等
            
        Returns:
            List[str]: 股票代码列表
        """
        return self.data.get_stock_list(sector)
    
    def get_trading_dates(self, 
                         market: str = 'SH', 
                         start: Optional[str] = None, 
                         end: Optional[str] = None,
                         count: int = -1) -> List[str]:
        """
        获取交易日列表
        
        Args:
            market: 市场代码，'SH'或'SZ'
            start: 开始日期
            end: 结束日期
            count: 数据条数
            
        Returns:
            List[str]: 交易日列表
        """
        return self.data.get_trading_dates(market, start, end, count)
    
    def download_data(self, 
                     codes: Union[str, List[str]], 
                     period: str = '1d',
                     start: Optional[str] = None, 
                     end: Optional[str] = None) -> bool:
        """
        下载历史数据到本地
        
        Args:
            codes: 股票代码
            period: 周期
            start: 开始日期
            end: 结束日期
            
        Returns:
            bool: 是否成功
        """
        return self.data.download_data(codes, period, start, end)
    
    def download_history_data_batch(self, 
                                  stock_list: Union[str, List[str]], 
                                  period: str = '1d',
                                  start_time: str = '',
                                  end_time: str = '') -> Dict[str, bool]:
        """
        批量下载历史数据（使用xtdata.download_history_data2）
        
        Args:
            stock_list: 股票代码列表
            period: 数据周期，如'1d', '1m', '5m'等
            start_time: 开始时间，格式YYYYMMDD
            end_time: 结束时间，格式YYYYMMDD
            
        Returns:
            Dict[str, bool]: 每只股票的下载结果 {股票代码: 是否成功}
        """
        return self.data.download_history_data_batch(stock_list, period, start_time, end_time)

    # ==================== 订阅接口 ====================

    def subscribe(self,
                  codes: Union[str, List[str]],
                  period: str = 'tick',
                  callback: Optional[callable] = None) -> int:
        """
        订阅行情数据

        Args:
            codes: 股票代码，支持单个或列表
            period: 数据周期，'tick'分笔, '1m'1分钟, '1d'日线等
            callback: 回调函数，接收推送数据

        Returns:
            int: 订阅号，成功返回>0，失败返回-1

        Example:
            >>> # 定义回调函数
            >>> def on_tick(data):
            ...     for code, tick in data.items():
            ...         print(f"{code}: {tick.get('lastPrice')}")
            ...
            >>> # 订阅
            >>> seq = api.subscribe('000001.SZ', callback=on_tick)
            >>> # 持续运行接收推送
            >>> api.run_forever()
        """
        if not self._data_connected:
            print("⚠️ 数据服务未连接，正在尝试连接...")
            self._data_connected = self.data.connect()
            if not self._data_connected:
                print("❌ 数据服务连接失败")
                return -1

        return self.data.subscribe_quote(codes, period, callback)

    def subscribe_whole(self,
                        codes: Union[str, List[str]],
                        callback: Optional[callable] = None) -> int:
        """
        订阅全推行情数据（推荐用于多股票订阅）

        与subscribe的区别：
        - subscribe_whole订阅全市场或指定股票的tick数据
        - 更适合订阅数量较多的场景（>50只股票）
        - 只支持tick周期

        Args:
            codes: 股票代码列表
            callback: 回调函数，接收推送数据

        Returns:
            int: 订阅号，成功返回>0，失败返回-1

        Example:
            >>> def on_tick(data):
            ...     for code, tick in data.items():
            ...         print(f"{code}: {tick.get('lastPrice')}")
            ...
            >>> codes = ['000001.SZ', '000002.SZ', '600000.SH']
            >>> seq = api.subscribe_whole(codes, callback=on_tick)
            >>> api.run_forever()
        """
        if not self._data_connected:
            print("⚠️ 数据服务未连接，正在尝试连接...")
            self._data_connected = self.data.connect()
            if not self._data_connected:
                print("❌ 数据服务连接失败")
                return -1

        return self.data.subscribe_whole_quote(codes, callback)

    def unsubscribe(self, seq_id: int) -> bool:
        """
        取消订阅

        Args:
            seq_id: 订阅号（subscribe或subscribe_whole的返回值）

        Returns:
            bool: 是否成功
        """
        return self.data.unsubscribe_quote(seq_id)

    def run_forever(self, check_interval: float = 1.0):
        """
        阻塞当前线程，持续接收行情推送

        通常与subscribe配合使用，保持程序运行以接收推送数据

        Args:
            check_interval: 检查连接状态的间隔时间（秒）

        Example:
            >>> api.subscribe('000001.SZ', callback=on_tick)
            >>> api.run_forever()  # 阻塞运行，按Ctrl+C退出
        """
        self.data.run_forever(check_interval)

    # ==================== 交易接口 ====================
    
    def buy(self, 
            account_id: str, 
            code: str, 
            volume: int, 
            price: float = 0, 
            price_type: str = 'market') -> Optional[int]:
        """
        买入股票
        
        Args:
            account_id: 资金账号
            code: 股票代码
            volume: 买入数量
            price: 买入价格，市价单时可为0
            price_type: 价格类型，'market'市价, 'limit'限价
            
        Returns:
            Optional[int]: 委托编号，失败返回None
        """
        if not self._trade_connected:
            ErrorHandler.log_error("交易服务未初始化")
            return None
        return self.trade.buy(account_id, code, volume, price, price_type)
    
    def sell(self, 
             account_id: str, 
             code: str, 
             volume: int, 
             price: float = 0, 
             price_type: str = 'market') -> Optional[int]:
        """
        卖出股票
        
        Args:
            account_id: 资金账号
            code: 股票代码
            volume: 卖出数量
            price: 卖出价格，市价单时可为0
            price_type: 价格类型，'market'市价, 'limit'限价
            
        Returns:
            Optional[int]: 委托编号，失败返回None
        """
        if not self._trade_connected:
            ErrorHandler.log_error("交易服务未初始化")
            return None
        return self.trade.sell(account_id, code, volume, price, price_type)

    def quick_buy(self,
                  account_id: str,
                  code: str,
                  amount: float,
                  price_type: str = 'market') -> Optional[int]:
        """
        按金额快速买入股票

        根据指定金额自动计算买入数量并下单

        Args:
            account_id: 资金账号
            code: 股票代码
            amount: 买入金额（元）
            price_type: 价格类型，'market'市价, 'limit'限价

        Returns:
            Optional[int]: 委托编号，失败返回None

        Example:
            >>> # 买入1000元的平安银行
            >>> order_id = api.quick_buy(account_id='123456', code='000001.SZ', amount=1000)
        """
        if not self._trade_connected:
            ErrorHandler.log_error("交易服务未初始化")
            return None

        # 获取当前价格
        try:
            current_price_data = self.data.get_current_price(code)
            if current_price_data.empty or code not in current_price_data.index:
                ErrorHandler.log_error(f"无法获取{code}的当前价格")
                return None

            current_price = current_price_data.loc[code, 'lastPrice']
            if current_price <= 0:
                ErrorHandler.log_error(f"{code}的当前价格无效: {current_price}")
                return None

            # 计算买入数量（向下取整到100的倍数）
            # A股最小交易单位是100股（1手）
            volume = int(amount / current_price / 100) * 100

            if volume < 100:
                ErrorHandler.log_error(f"金额{amount}元不足以买入100股（当前价格{current_price:.2f}元）")
                return None

            # 调用买入接口
            return self.buy(account_id, code, volume, 0, price_type)

        except Exception as e:
            ErrorHandler.log_error(f"quick_buy失败: {str(e)}")
            return None

    def quick_sell(self,
                   account_id: str,
                   code: str,
                   amount: float,
                   price_type: str = 'market') -> Optional[int]:
        """
        按金额快速卖出股票

        根据指定金额和持仓计算卖出数量并下单

        Args:
            account_id: 资金账号
            code: 股票代码
            amount: 卖出金额（元）
            price_type: 价格类型，'market'市价, 'limit'限价

        Returns:
            Optional[int]: 委托编号，失败返回None

        Example:
            >>> # 卖出1000元的持仓股票
            >>> order_id = api.quick_sell(account_id='123456', code='000001.SZ', amount=1000)
        """
        if not self._trade_connected:
            ErrorHandler.log_error("交易服务未初始化")
            return None

        try:
            # 获取当前持仓
            positions = self.get_positions(account_id, code)
            if positions.empty:
                ErrorHandler.log_error(f"没有{code}的持仓")
                return None

            # 获取持仓数量
            volume_available = positions.iloc[0]['available_volume'] if 'available_volume' in positions.columns else positions.iloc[0]['volume']
            if volume_available <= 0:
                ErrorHandler.log_error(f"{code}没有可用持仓")
                return None

            # 获取当前价格
            current_price_data = self.data.get_current_price(code)
            if current_price_data.empty or code not in current_price_data.index:
                ErrorHandler.log_error(f"无法获取{code}的当前价格")
                return None

            current_price = current_price_data.loc[code, 'lastPrice']
            if current_price <= 0:
                ErrorHandler.log_error(f"{code}的当前价格无效: {current_price}")
                return None

            # 计算卖出数量（向下取整到100的倍数）
            volume = int(amount / current_price / 100) * 100

            # 检查是否超过可用持仓
            if volume > volume_available:
                volume = int(volume_available / 100) * 100
                if volume < 100:
                    ErrorHandler.log_error(f"可用持仓不足{volume_available}股")
                    return None

            if volume < 100:
                ErrorHandler.log_error(f"金额{amount}元不足以卖出100股")
                return None

            # 调用卖出接口
            return self.sell(account_id, code, volume, 0, price_type)

        except Exception as e:
            ErrorHandler.log_error(f"quick_sell失败: {str(e)}")
            return None

    def cancel_order(self, account_id: str, order_id: int) -> bool:
        """
        撤销委托
        
        Args:
            account_id: 资金账号
            order_id: 委托编号
            
        Returns:
            bool: 是否成功
        """
        if not self._trade_connected:
            ErrorHandler.log_error("交易服务未初始化")
            return False
        return self.trade.cancel_order(account_id, order_id)
    
    def get_account_asset(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        获取账户资产
        
        Args:
            account_id: 资金账号
            
        Returns:
            Optional[Dict]: 资产信息
        """
        if not self._trade_connected:
            ErrorHandler.log_error("交易服务未初始化")
            return None
        return self.trade.get_account_asset(account_id)
    
    def get_positions(self, account_id: str, code: Optional[str] = None) -> pd.DataFrame:
        """
        获取持仓信息
        
        Args:
            account_id: 资金账号
            code: 股票代码，为空则获取所有持仓
            
        Returns:
            DataFrame: 持仓信息
        """
        if not self._trade_connected:
            ErrorHandler.log_error("交易服务未初始化")
            return pd.DataFrame()
        return self.trade.get_positions(account_id, code if code else "")
    
    def get_orders(self, account_id: str, cancelable_only: bool = False) -> pd.DataFrame:
        """
        获取委托信息
        
        Args:
            account_id: 资金账号
            cancelable_only: 是否只获取可撤销委托
            
        Returns:
            DataFrame: 委托信息
        """
        if not self._trade_connected:
            ErrorHandler.log_error("交易服务未初始化")
            return pd.DataFrame()
        return self.trade.get_orders(account_id, cancelable_only)
    
    def get_trades(self, account_id: str) -> pd.DataFrame:
        """
        获取成交信息 - 使用最简单的方式
        
        Args:
            account_id: 资金账号
            
        Returns:
            DataFrame: 成交信息
        """
        if not self._trade_connected:
            ErrorHandler.log_error("交易服务未初始化")
            return pd.DataFrame()
        
        # 直接使用最简单的方式，就像用户的代码一样
        if hasattr(self.trade, 'trader') and self.trade.trader and account_id in self.trade.accounts:
            account = self.trade.accounts[account_id]
            trades = self.trade.trader.query_stock_trades(account)
            print("成交数量:", len(trades))
            
            if len(trades) == 0:
                return pd.DataFrame()
            
            # 简单处理成交数据
            result_data = []
            for trade in trades:
                result_data.append({
                    'trade_id': trade.traded_id,
                    'order_id': trade.order_id,
                    'stock_code': trade.stock_code,
                    'order_type': trade.order_type,
                    'traded_volume': trade.traded_volume,
                    'traded_price': trade.traded_price,
                    'traded_amount': trade.traded_amount,
                    'traded_time': trade.traded_time,
                    'account_type': trade.account_type,
                    'account_id': trade.account_id,
                    'order_sysid': trade.order_sysid
                })
            
            return pd.DataFrame(result_data)
        else:
            print("成交数量: 0")
            return pd.DataFrame()