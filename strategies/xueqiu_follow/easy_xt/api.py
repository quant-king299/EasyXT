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
    
    def init_trade(self, userdata_path: str, session_id: str = None) -> bool:
        """
        初始化交易服务
        
        Args:
            userdata_path: 迅投客户端userdata路径
            session_id: 会话ID
            
        Returns:
            bool: 是否成功
        """
        self._trade_connected = self.trade.connect(userdata_path, session_id)
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
                  start: str = None, 
                  end: str = None, 
                  period: str = '1d',
                  count: int = None,
                  fields: List[str] = None,
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
    
    def get_financial_data(self, 
                          codes: Union[str, List[str]], 
                          tables: List[str] = None,
                          start: str = None, 
                          end: str = None,
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
    
    def get_stock_list(self, sector: str = None) -> List[str]:
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
                         start: str = None, 
                         end: str = None,
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
                     start: str = None, 
                     end: str = None) -> bool:
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
    
    def get_positions(self, account_id: str, code: str = None) -> pd.DataFrame:
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
        return self.trade.get_positions(account_id, code)
    
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
    
    # ==================== 便捷方法 ====================
    
    def quick_buy(self, account_id: str, code: str, amount: float, price_type: str = 'market') -> Optional[int]:
        """
        按金额买入股票
        
        Args:
            account_id: 资金账号
            code: 股票代码
            amount: 买入金额
            price_type: 价格类型
            
        Returns:
            Optional[int]: 委托编号
        """
        # 获取当前价格
        current_price_df = self.get_current_price(code)
        if current_price_df.empty:
            ErrorHandler.log_error("无法获取当前价格")
            return None
        
        current_price = current_price_df.iloc[0]['price']
        if current_price <= 0:
            ErrorHandler.log_error("当前价格无效")
            return None
        
        # 计算买入数量（向下取整到100的倍数）
        volume = int(amount / current_price / 100) * 100
        if volume < 100:
            ErrorHandler.log_error("买入金额不足100股")
            return None
        
        return self.buy(account_id, code, volume, current_price if price_type == 'limit' else 0, price_type)
    
    def sell_all(self, account_id: str, code: str, price_type: str = 'market') -> Optional[int]:
        """
        卖出持仓的全部股票
        
        Args:
            account_id: 资金账号
            code: 股票代码
            price_type: 价格类型
            
        Returns:
            Optional[int]: 委托编号
        """
        # 获取持仓
        positions = self.get_positions(account_id, code)
        if positions.empty:
            ErrorHandler.log_error("没有持仓")
            return None
        
        volume = int(positions.iloc[0]['can_use_volume'])
        if volume <= 0:
            ErrorHandler.log_error("可用持仓为0")
            return None
        
        # 获取当前价格
        current_price = 0
        if price_type == 'limit':
            current_price_df = self.get_current_price(code)
            if not current_price_df.empty:
                current_price = current_price_df.iloc[0]['price']
        
        return self.sell(account_id, code, volume, current_price, price_type)
    
    def get_portfolio_value(self, account_id: str) -> Dict[str, float]:
        """
        获取投资组合价值
        
        Args:
            account_id: 资金账号
            
        Returns:
            Dict: 投资组合价值信息
        """
        asset = self.get_account_asset(account_id)
        if not asset:
            return {}
        
        return {
            'cash': asset['cash'],
            'market_value': asset['market_value'],
            'total_value': asset['total_asset'],
            'frozen_cash': asset['frozen_cash']
        }
    
    # ==================== 配置方法 ====================
    
    def set_config(self, key: str, value: Any) -> None:
        """
        设置配置
        
        Args:
            key: 配置键
            value: 配置值
        """
        config.set(key, value)
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取配置
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        return config.get(key, default)
    
    def disconnect(self):
        """断开所有连接"""
        if self._trade_connected:
            self.trade.disconnect()
            self._trade_connected = False
        
        print("EasyXT已断开连接")
