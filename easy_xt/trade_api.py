"""
交易API封装模块
简化xtquant交易接口的调用
"""
import pandas as pd
from typing import Union, List, Optional, Dict, Any, Callable
import sys
import os
import time
import datetime
from threading import Event

# 添加xtquant路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
xtquant_path = os.path.join(project_root, 'xtquant')

if xtquant_path not in sys.path:
    sys.path.insert(0, xtquant_path)

# 延迟导入xtquant，只在需要时才导入
# 避免在只使用数据功能时显示不必要的警告
_xt_trader_available = False
_xt_trader = None
_xt_type = None
_xt_const = None
_xtdata = None

def _ensure_xt_trader():
    """确保xtquant已导入，延迟加载"""
    global _xt_trader_available, _xt_trader, _xt_type, _xt_const, _xtdata

    if _xt_trader_available:
        return True

    try:
        import xtquant.xttrader as xt_trader
        import xtquant.xttype as xt_type
        import xtquant.xtconstant as xt_const
        from xtquant import xtdata

        _xt_trader = xt_trader
        _xt_type = xt_type
        _xt_const = xt_const
        _xtdata = xtdata
        _xt_trader_available = True
        print("[OK] xtquant.xttrader 导入成功")
        return True
    except ImportError as e:
        print(f"[INFO] xtquant.xttrader 未安装或不可用")
        print(f"[INFO] 如需交易功能，请安装QMT客户端")
        print(f"[INFO] 数据功能可正常使用，不受影响")
        return False

# 旧代码保持兼容（已弃用）
try:
    import xtquant.xttrader as xt_trader
    import xtquant.xttype as xt_type
    import xtquant.xtconstant as xt_const
    from xtquant import xtdata
    _xt_trader_available = True
    _xt_trader = xt_trader
    _xt_type = xt_type
    _xt_const = xt_const
    _xtdata = xtdata
    xt_trader = xt_trader
    xt_type = xt_type
    xt_const = xt_const
except ImportError:
    xt_trader = None
    xt_type = None
    xt_const = None

from .utils import StockCodeUtils, ErrorHandler
from .config import config

# 条件定义SimpleCallback类
if xt_trader is not None:
    class SimpleCallback(xt_trader.XtQuantTraderCallback):
        """简化的交易回调类"""

        def __init__(self):
            super().__init__()
            self.connected = False
            self.orders = {}
            self.trades = {}
            self.positions = {}
            self.assets = {}
            self.errors = []

            # 事件通知
            self.order_event = Event()
            self.trade_event = Event()

        def on_connected(self):
            """连接成功"""
            self.connected = True
            print("交易连接成功")

        def on_disconnected(self):
            """连接断开"""
            self.connected = False
            print("交易连接断开")

        def on_stock_order(self, order):
            """委托回调"""
            self.orders[order.order_id] = order
            self.order_event.set()

        def on_stock_trade(self, trade):
            """成交回调"""
            self.trades[trade.traded_id] = trade
            self.trade_event.set()

        def on_stock_position(self, position):
            """持仓回调"""
            key = f"{position.account_id}_{position.stock_code}"
            self.positions[key] = position

        def on_stock_asset(self, asset):
            """资产回调"""
            self.assets[asset.account_id] = asset

        def on_order_error(self, order_error):
            """委托错误回调"""
            self.errors.append(order_error)
            print(f"委托错误: {order_error.error_msg}")
else:
    # xtquant不可用时的占位符类
    class SimpleCallback:
        """占位符回调类（xtquant不可用时）"""
        def __init__(self):
            pass

class TradeAPI:
    """交易API封装类"""
    
    def __init__(self):
        self.trader = None
        self.callback = None
        self.accounts = {}
        self._session_id = config.get('trade.session_id', 'default')
        
    def connect(self, userdata_path: str, session_id: str = None) -> bool:
        """
        连接交易服务
        
        Args:
            userdata_path: 迅投客户端userdata路径
            session_id: 会话ID
            
        Returns:
            bool: 是否连接成功
        """
        if not xt_trader:
            ErrorHandler.log_error("xtquant交易模块未正确导入")
            return False
            
        try:
            if session_id:
                self._session_id = session_id
                
            # 处理路径编码问题
            try:
                # 确保路径是字符串格式，处理中文路径
                if isinstance(userdata_path, bytes):
                    userdata_path = userdata_path.decode('utf-8')
                
                # 规范化路径
                userdata_path = os.path.normpath(userdata_path)
                
                # 检查路径是否存在
                if not os.path.exists(userdata_path):
                    ErrorHandler.log_error(f"userdata路径不存在: {userdata_path}")
                    return False
                    
            except Exception as path_error:
                ErrorHandler.log_error(f"路径处理失败: {str(path_error)}")
                return False
                
            # 创建回调对象
            self.callback = SimpleCallback()
            
            # 创建交易对象 - 修复session_id类型问题
            try:
                # 根据错误信息，XtQuantAsyncClient需要的第三个参数是int类型
                # 尝试将session_id转换为数字，如果失败则使用默认值
                try:
                    # 使用时间戳作为session_id以确保唯一性
                    session_int = int(time.time() * 1000) % 1000000
                except:
                    session_int = 123456  # 默认session ID
                
                print(f"🔧 使用session_id: {session_int}")
                
                # 创建交易对象，使用数字类型的session_id
                self.trader = xt_trader.XtQuantTrader(userdata_path, session_int)
                # 注册回调
                self.trader.register_callback(self.callback)
            except Exception as create_error:
                ErrorHandler.log_error(f"创建交易对象失败: {str(create_error)}")
                return False
            
            # 启动交易
            print("🚀 启动交易服务...")
            self.trader.start()
            
            # 连接
            print("🔗 连接交易服务...")
            result = self.trader.connect()
            if result == 0:
                print("[OK] 交易服务连接成功")
                return True
            else:
                ErrorHandler.log_error(f"交易服务连接失败，错误码: {result}")
                return False
                
        except Exception as e:
            ErrorHandler.log_error(f"连接交易服务失败: {str(e)}")
            return False
    
    def add_account(self, account_id: str, account_type: str = 'STOCK') -> bool:
        """
        添加交易账户
        
        Args:
            account_id: 资金账号
            account_type: 账户类型，'STOCK'股票, 'CREDIT'信用
            
        Returns:
            bool: 是否成功
        """
        if not self.trader:
            ErrorHandler.log_error("交易服务未连接")
            return False
            
        try:
            print(f"➕ 添加账户: {account_id}")
            account = xt_type.StockAccount(account_id, account_type)
            if isinstance(account, str):  # 错误信息
                ErrorHandler.log_error(account)
                return False
                
            # 订阅账户
            print("📡 订阅账户...")
            result = self.trader.subscribe(account)
            if result == 0:
                self.accounts[account_id] = account
                print(f"[OK] 账户 {account_id} 添加成功")
                return True
            else:
                ErrorHandler.log_error(f"订阅账户失败，错误码: {result}")
                return False
                
        except Exception as e:
            ErrorHandler.log_error(f"添加账户失败: {str(e)}")
            return False
    
    @ErrorHandler.handle_api_error
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
        if not self.trader or account_id not in self.accounts:
            ErrorHandler.log_error("交易服务未连接或账户未添加")
            return None
            
        account = self.accounts[account_id]
        code = StockCodeUtils.normalize_code(code)
        
        # 价格类型映射
        price_type_map = {
            'market': xt_const.MARKET_PEER_PRICE_FIRST,  # 对手价
            'limit': xt_const.FIX_PRICE,  # 限价
            '市价': xt_const.MARKET_PEER_PRICE_FIRST,
            '限价': xt_const.FIX_PRICE
        }
        
        xt_price_type = price_type_map.get(price_type, xt_const.MARKET_PEER_PRICE_FIRST)
        
        try:
            print(f"🛒 买入 {code}, 数量: {volume}, 价格: {price}, 类型: {price_type}")
            order_id = self.trader.order_stock(
                account=account,
                stock_code=code,
                order_type=xt_const.STOCK_BUY,
                order_volume=volume,
                price_type=xt_price_type,
                price=price,
                strategy_name='EasyXT',
                order_remark=f'买入{code}'
            )
            
            if order_id > 0:
                print(f"[OK] 买入委托成功: {code}, 数量: {volume}, 委托号: {order_id}")
                return order_id
            else:
                ErrorHandler.log_error(f"买入委托失败，返回值: {order_id}")
                return None
                
        except Exception as e:
            ErrorHandler.log_error(f"买入操作失败: {str(e)}")
            return None
    
    @ErrorHandler.handle_api_error
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
        if not self.trader or account_id not in self.accounts:
            ErrorHandler.log_error("交易服务未连接或账户未添加")
            return None
            
        account = self.accounts[account_id]
        code = StockCodeUtils.normalize_code(code)
        
        # 价格类型映射
        price_type_map = {
            'market': xt_const.MARKET_PEER_PRICE_FIRST,
            'limit': xt_const.FIX_PRICE,
            '市价': xt_const.MARKET_PEER_PRICE_FIRST,
            '限价': xt_const.FIX_PRICE
        }
        
        xt_price_type = price_type_map.get(price_type, xt_const.MARKET_PEER_PRICE_FIRST)
        
        try:
            print(f"💰 卖出 {code}, 数量: {volume}, 价格: {price}, 类型: {price_type}")
            order_id = self.trader.order_stock(
                account=account,
                stock_code=code,
                order_type=xt_const.STOCK_SELL,
                order_volume=volume,
                price_type=xt_price_type,
                price=price,
                strategy_name='EasyXT',
                order_remark=f'卖出{code}'
            )
            
            if order_id > 0:
                print(f"[OK] 卖出委托成功: {code}, 数量: {volume}, 委托号: {order_id}")
                return order_id
            else:
                ErrorHandler.log_error(f"卖出委托失败，返回值: {order_id}")
                return None
                
        except Exception as e:
            ErrorHandler.log_error(f"卖出操作失败: {str(e)}")
            return None
    
    @ErrorHandler.handle_api_error
    def cancel_order(self, account_id: str, order_id: int) -> bool:
        """
        撤销委托
        
        Args:
            account_id: 资金账号
            order_id: 委托编号
            
        Returns:
            bool: 是否成功
        """
        if not self.trader or account_id not in self.accounts:
            ErrorHandler.log_error("交易服务未连接或账户未添加")
            return False
            
        account = self.accounts[account_id]
        
        try:
            result = self.trader.cancel_order_stock(account, order_id)
            if result == 0:
                print(f"[OK] 撤单成功: {order_id}")
                return True
            else:
                ErrorHandler.log_error(f"撤单失败，错误码: {result}")
                return False
                
        except Exception as e:
            ErrorHandler.log_error(f"撤单操作失败: {str(e)}")
            return False
    
    @ErrorHandler.handle_api_error
    def get_account_asset(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        获取账户资产
        
        Args:
            account_id: 资金账号
            
        Returns:
            Optional[Dict]: 资产信息
        """
        if not self.trader or account_id not in self.accounts:
            ErrorHandler.log_error("交易服务未连接或账户未添加")
            return None
            
        account = self.accounts[account_id]
        
        try:
            asset = self.trader.query_stock_asset(account)
            if asset:
                return {
                    'account_id': asset.account_id,
                    'cash': asset.cash,  # 可用资金
                    'frozen_cash': asset.frozen_cash,  # 冻结资金
                    'market_value': asset.market_value,  # 持仓市值
                    'total_asset': asset.total_asset  # 总资产
                }
            return None
            
        except Exception as e:
            ErrorHandler.log_error(f"获取账户资产失败: {str(e)}")
            return None
    
    @ErrorHandler.handle_api_error
    def get_positions(self, account_id: str, code: str = None) -> pd.DataFrame:
        """
        获取持仓信息
        
        Args:
            account_id: 资金账号
            code: 股票代码，为空则获取所有持仓
            
        Returns:
            DataFrame: 持仓信息
        """
        if not self.trader or account_id not in self.accounts:
            ErrorHandler.log_error("交易服务未连接或账户未添加")
            return pd.DataFrame()
            
        account = self.accounts[account_id]
        
        try:
            if code:
                # 获取单只股票持仓
                code = StockCodeUtils.normalize_code(code)
                position = self.trader.query_stock_position(account, code)
                if position:
                    return pd.DataFrame([{
                        'code': position.stock_code,
                        'volume': position.volume,
                        'can_use_volume': position.can_use_volume,
                        'open_price': position.open_price,
                        'market_value': position.market_value,
                        'frozen_volume': position.frozen_volume
                    }])
                else:
                    return pd.DataFrame()
            else:
                # 获取所有持仓
                positions = self.trader.query_stock_positions(account)
                if positions:
                    data = []
                    for pos in positions:
                        data.append({
                            'code': pos.stock_code,
                            'volume': pos.volume,
                            'can_use_volume': pos.can_use_volume,
                            'open_price': pos.open_price,
                            'market_value': pos.market_value,
                            'frozen_volume': pos.frozen_volume
                        })
                    return pd.DataFrame(data)
                else:
                    return pd.DataFrame()
                    
        except Exception as e:
            ErrorHandler.log_error(f"获取持仓信息失败: {str(e)}")
            return pd.DataFrame()
    
    @ErrorHandler.handle_api_error
    def get_orders(self, account_id: str, cancelable_only: bool = False) -> pd.DataFrame:
        """
        获取委托信息
        
        Args:
            account_id: 资金账号
            cancelable_only: 是否只获取可撤销委托
            
        Returns:
            DataFrame: 委托信息
        """
        if not self.trader or account_id not in self.accounts:
            ErrorHandler.log_error("交易服务未连接或账户未添加")
            return pd.DataFrame()
            
        account = self.accounts[account_id]
        
        try:
            orders = self.trader.query_stock_orders(account, cancelable_only)
            if orders:
                data = []
                for order in orders:
                    # 委托类型转换
                    order_type_name = '买入' if order.order_type == xt_const.STOCK_BUY else '卖出'
                    
                    # 委托状态转换
                    status_map = {
                        xt_const.ORDER_UNREPORTED: '未报',
                        xt_const.ORDER_WAIT_REPORTING: '待报',
                        xt_const.ORDER_REPORTED: '已报',
                        xt_const.ORDER_PART_SUCC: '部成',
                        xt_const.ORDER_SUCCEEDED: '已成',
                        xt_const.ORDER_PART_CANCEL: '部撤',
                        xt_const.ORDER_CANCELED: '已撤',
                        xt_const.ORDER_JUNK: '废单'
                    }
                    status_name = status_map.get(order.order_status, '未知')
                    
                    data.append({
                        'order_id': order.order_id,
                        'code': order.stock_code,
                        'order_type': order_type_name,
                        'volume': order.order_volume,
                        'price': order.price,
                        'traded_volume': order.traded_volume,
                        'status': status_name,
                        'order_time': order.order_time,
                        'remark': order.order_remark
                    })
                return pd.DataFrame(data)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            ErrorHandler.log_error(f"获取委托信息失败: {str(e)}")
            return pd.DataFrame()
    
    def get_trades(self, account_id: str, timeout: int = 5) -> pd.DataFrame:
        """
        获取成交信息 - 修复版本，解决QMT API查询问题
        
        Args:
            account_id: 资金账号
            timeout: 超时时间（秒），默认5秒
            
        Returns:
            DataFrame: 成交信息
        """
        if not self.trader or account_id not in self.accounts:
            print("[ERROR] 交易服务未连接或账户未添加")
            return pd.DataFrame()
            
        account = self.accounts[account_id]
        
        print(f"🔍 正在查询成交信息...")
        
        try:
            # 方法1：直接查询成交
            print("  📡 尝试方法1：直接查询成交...")
            trades = self.trader.query_stock_trades(account)
            
            if trades and len(trades) > 0:
                print(f"[OK] 直接查询成功，找到 {len(trades)} 条成交记录")
                return self._process_trades_data(trades)
            else:
                print("[WARNING] 直接查询无成交记录")
            
            # 方法2：从委托信息推断成交
            print("  🔄 尝试方法2：从委托信息推断成交...")
            trades_from_orders = self.get_trades_from_orders(account_id)
            if not trades_from_orders.empty:
                print(f"[OK] 从委托推断成功，找到 {len(trades_from_orders)} 条成交记录")
                return trades_from_orders
            
            # 方法3：使用回调中的成交信息
            print("  🔄 尝试方法3：使用回调成交信息...")
            if self.callback and self.callback.trades:
                callback_trades = list(self.callback.trades.values())
                if callback_trades:
                    print(f"[OK] 回调查询成功，找到 {len(callback_trades)} 条成交记录")
                    return self._process_trades_data(callback_trades)
            
            print("📝 所有方法均未找到成交记录")
            return pd.DataFrame()
            
        except Exception as e:
            print(f"[ERROR] 成交查询异常: {e}")
            # 异常时也尝试从委托推断
            try:
                return self.get_trades_from_orders(account_id)
            except:
                return pd.DataFrame()
    
    def _process_trades_data(self, trades) -> pd.DataFrame:
        """处理成交数据"""
        if not trades:
            return pd.DataFrame()
        
        print("📊 正在处理成交数据...")
        data = []
        
        for trade in trades:
            # 委托类型转换
            order_type_name = '买入' if trade.order_type == xt_const.STOCK_BUY else '卖出'
            
            data.append({
                'code': trade.stock_code,
                'order_type': order_type_name,
                'volume': trade.traded_volume,
                'price': trade.traded_price,
                'amount': trade.traded_amount,
                'time': trade.traded_time,
                'order_id': trade.order_id,
                'trade_id': trade.traded_id,
                'strategy_name': getattr(trade, 'strategy_name', ''),
                'remark': getattr(trade, 'order_remark', '')
            })
        
        result_df = pd.DataFrame(data)
        print(f"[OK] 成交数据处理完成，共 {len(result_df)} 条记录")
        return result_df
    
    def get_trades_from_orders(self, account_id: str) -> pd.DataFrame:
        """
        从委托信息推断成交情况（备用方案）
        
        Args:
            account_id: 资金账号
            
        Returns:
            DataFrame: 推断的成交信息
        """
        print("🔄 使用备用方案：从委托信息推断成交...")
        
        orders_df = self.get_orders(account_id)
        if orders_df.empty:
            print("📝 无委托信息，无法推断成交")
            return pd.DataFrame()
        
        # 筛选已成交的委托
        filled_orders = orders_df[orders_df['status'].isin(['已成', '部成'])]
        
        if filled_orders.empty:
            print("📝 无已成交委托")
            return pd.DataFrame()
        
        # 转换为成交格式
        trades_data = []
        for _, order in filled_orders.iterrows():
            if order['traded_volume'] > 0:
                trades_data.append({
                    '证券代码': order['code'],
                    '委托类型': order['order_type'],
                    '成交数量': order['traded_volume'],
                    '委托价格': order['price'],
                    '委托时间': order['order_time'],
                    '状态': order['status'],
                    '备注': '从委托推断'
                })
        
        if trades_data:
            result_df = pd.DataFrame(trades_data)
            print(f"[OK] 从委托推断出 {len(result_df)} 条成交记录")
            return result_df
        else:
            print("📝 无法从委托推断出成交信息")
            return pd.DataFrame()
    
    def disconnect(self):
        """断开连接"""
        if self.trader:
            try:
                self.trader.stop()
                print("交易服务已断开")
            except Exception as e:
                ErrorHandler.log_error(f"断开交易服务失败: {str(e)}")