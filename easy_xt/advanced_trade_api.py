"""
高级交易API模块
提供更丰富的交易功能和回调机制
"""
import pandas as pd
from typing import Union, List, Optional, Dict, Any, Callable
import sys
import os
import time
import datetime
from threading import Event, Thread
import asyncio

# 添加xtquant路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
xtquant_path = os.path.join(project_root, 'xtquant')

if xtquant_path not in sys.path:
    sys.path.insert(0, xtquant_path)

try:
    import xtquant.xttrader as xt_trader
    import xtquant.xttype as xt_type
    import xtquant.xtconstant as xt_const
    from xtquant import xtdata
    print("xtquant高级交易模块导入成功")
except ImportError as e:
    print(f"[WARNING] xtquant高级交易模块导入失败: {e}")
    xt_trader = None
    xt_type = None
    xt_const = None

from .utils import StockCodeUtils, ErrorHandler
from .config import config

class AdvancedCallback:
    """高级交易回调类"""
    
    def __init__(self):
        if xt_trader:
            super().__init__()
        else:
            # 模拟XtQuantTraderCallback的基本功能
            pass
        self.connected = False
        self.orders = {}
        self.trades = {}
        self.positions = {}
        self.assets = {}
        self.errors = []
        
        # 用户自定义回调
        self.order_callback = None
        self.trade_callback = None
        self.error_callback = None
        
        # 事件通知
        self.order_event = Event()
        self.trade_event = Event()
        
    def set_callbacks(self, order_callback=None, trade_callback=None, error_callback=None):
        """设置用户回调函数"""
        self.order_callback = order_callback
        self.trade_callback = trade_callback
        self.error_callback = error_callback
        
    def on_connected(self):
        """连接成功"""
        self.connected = True
        print("高级交易连接成功")
    
    def on_disconnected(self):
        """连接断开"""
        self.connected = False
        print("高级交易连接断开")
    
    def on_stock_order(self, order):
        """委托回调"""
        self.orders[order.order_id] = order
        self.order_event.set()
        
        # 调用用户回调
        if self.order_callback:
            try:
                self.order_callback(order)
            except Exception as e:
                print(f"用户委托回调异常: {e}")
        
    def on_stock_trade(self, trade):
        """成交回调"""
        self.trades[trade.traded_id] = trade
        self.trade_event.set()
        
        # 调用用户回调
        if self.trade_callback:
            try:
                self.trade_callback(trade)
            except Exception as e:
                print(f"用户成交回调异常: {e}")
        
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
        
        # 调用用户回调
        if self.error_callback:
            try:
                self.error_callback(order_error)
            except Exception as e:
                print(f"用户错误回调异常: {e}")

class AdvancedTradeAPI:
    """高级交易API类"""
    
    def __init__(self):
        self.trader = None
        self.callback = None
        self.accounts = {}
        self._session_id = config.get('trade.session_id', 'advanced')
        
        # 风险管理参数
        self.risk_params = {
            'max_position_ratio': 0.3,
            'max_single_order_amount': 10000,
            'slippage': 0.002
        }
        
        # 异步订单管理
        self.async_orders = {}
        self.order_sequence = 0
        
    def connect(self, userdata_path: str, session_id: str = 'advanced') -> bool:
        """连接交易服务"""
        """连接交易服务"""
        if not xt_trader:
            ErrorHandler.log_error("xtquant交易模块未正确导入")
            return False
            
        try:
            if session_id:
                self._session_id = session_id
                
            # 处理路径
            userdata_path = os.path.normpath(userdata_path)
            if not os.path.exists(userdata_path):
                ErrorHandler.log_error(f"userdata路径不存在: {userdata_path}")
                return False
                
            # 创建高级回调对象
            self.callback = AdvancedCallback()
            
            # 创建交易对象
            try:
                session_int = int(self._session_id) if self._session_id.isdigit() else hash(self._session_id) % 10000
                self.trader = xt_trader.XtQuantTrader(userdata_path, session_int, self.callback)
            except Exception as create_error:
                ErrorHandler.log_error(f"创建高级交易对象失败: {str(create_error)}")
                return False
            
            # 启动交易
            self.trader.start()
            
            # 连接
            result = self.trader.connect()
            if result == 0:
                print("高级交易服务连接成功")
                return True
            else:
                ErrorHandler.log_error(f"高级交易服务连接失败，错误码: {result}")
                return False
                
        except Exception as e:
            ErrorHandler.log_error(f"连接高级交易服务失败: {str(e)}")
            return False
    
    def set_callbacks(self, order_callback=None, trade_callback=None, error_callback=None):
        """设置回调函数"""
        if self.callback:
            self.callback.set_callbacks(order_callback, trade_callback, error_callback)
            print("高级交易回调函数设置完成")
        else:
            print("[WARNING] 回调对象未初始化")
    
    def add_account(self, account_id: str, account_type: str = 'STOCK') -> bool:
        """添加交易账户"""
        if not self.trader:
            ErrorHandler.log_error("高级交易服务未连接")
            return False
            
        try:
            if xt_type:
                account = xt_type.StockAccount(account_id, account_type)
                if isinstance(account, str):
                    ErrorHandler.log_error(account)
                    return False
            else:
                ErrorHandler.log_error("xtquant模块未导入")
                return False
                
            result = self.trader.subscribe(account)
            if result == 0:
                self.accounts[account_id] = account
                print(f"高级交易账户 {account_id} 添加成功")
                return True
            else:
                ErrorHandler.log_error(f"订阅高级交易账户失败，错误码: {result}")
                return False
                
        except Exception as e:
            ErrorHandler.log_error(f"添加高级交易账户失败: {str(e)}")
            return False
    
    def set_risk_params(self, max_position_ratio=0.3, max_single_order_amount=10000, slippage=0.002):
        """设置风险参数"""
        self.risk_params.update({
            'max_position_ratio': max_position_ratio,
            'max_single_order_amount': max_single_order_amount,
            'slippage': slippage
        })
        print(f"风险参数设置完成")
    
    def check_trading_time(self) -> bool:
        """检查交易时间"""
        now = datetime.datetime.now().time()
        # 上午: 9:30-11:30, 下午: 13:00-15:00
        morning = datetime.time(9, 30) <= now <= datetime.time(11, 30)
        afternoon = datetime.time(13, 0) <= now <= datetime.time(15, 0)
        return morning or afternoon
    
    def validate_order(self, account_id: str, amount: float) -> dict:
        """验证订单"""
        reasons = []
        
        # 检查金额限制
        if amount > self.risk_params['max_single_order_amount']:
            reasons.append(f"超过单笔最大交易金额限制: {self.risk_params['max_single_order_amount']}")
        
        # 检查交易时间
        if not self.check_trading_time():
            reasons.append("当前不是交易时间")
        
        return {
            'valid': len(reasons) == 0,
            'reasons': reasons
        }
    
    def sync_order(self, account_id: str, code: str, order_type: str, volume: int, 
                   price: float = 0, price_type: str = 'market', 
                   strategy_name: str = 'EasyXT', order_remark: str = '') -> Optional[int]:
        """同步下单"""
        if not self.trader or account_id not in self.accounts:
            ErrorHandler.log_error("高级交易服务未连接或账户未添加")
            return None
            
        account = self.accounts[account_id]
        code = StockCodeUtils.normalize_code(code)
        
        # 价格类型映射
        # 为了与xt_trader保持一致，市价单使用LATEST_PRICE
        price_type_map = {
            'market': xt_const.LATEST_PRICE if xt_const else 5,  # 市价单使用最新价
            'limit': xt_const.FIX_PRICE if xt_const else 11,      # 限价单使用指定价
            '市价': xt_const.LATEST_PRICE if xt_const else 5,
            '限价': xt_const.FIX_PRICE if xt_const else 11
        }
        
        xt_price_type = price_type_map.get(price_type, xt_const.LATEST_PRICE if xt_const else 5)
        xt_order_type = xt_const.STOCK_BUY if xt_const and order_type == 'buy' else xt_const.STOCK_SELL if xt_const else 24
        
        try:
            order_id = self.trader.order_stock(
                account=account,
                stock_code=code,
                order_type=xt_order_type,
                order_volume=volume,
                price_type=xt_price_type,
                price=price,
                strategy_name=strategy_name,
                order_remark=order_remark or f'{order_type}_{code}'
            )
            
            if order_id > 0:
                print(f"同步{order_type}委托成功: {code}, 数量: {volume}, 委托号: {order_id}")
                return order_id
            else:
                ErrorHandler.log_error("同步下单失败")
                return None
                
        except Exception as e:
            ErrorHandler.log_error(f"同步下单操作失败: {str(e)}")
            return None
    
    def async_order(self, account_id: str, code: str, order_type: str, volume: int,
                    price: float = 0, price_type: str = 'market',
                    strategy_name: str = 'EasyXT', order_remark: str = '') -> bool:
        """异步下单 - 真正的异步方式，不等待结果，通过回调处理"""
        if not self.trader or account_id not in self.accounts:
            ErrorHandler.log_error("高级交易服务未连接或账户未添加")
            return False
            
        account = self.accounts[account_id]
        code = StockCodeUtils.normalize_code(code)
        
        # 价格类型映射
        price_type_map = {
            'market': xt_const.LATEST_PRICE if xt_const else 5,
            'limit': xt_const.FIX_PRICE if xt_const else 11,
            '市价': xt_const.LATEST_PRICE if xt_const else 5,
            '限价': xt_const.FIX_PRICE if xt_const else 11
        }
        
        xt_price_type = price_type_map.get(price_type, xt_const.LATEST_PRICE if xt_const else 5)
        xt_order_type = xt_const.STOCK_BUY if xt_const and order_type == 'buy' else xt_const.STOCK_SELL if xt_const else 24
        
        try:
            # 发送下单请求后立即返回，不等待结果
            order_id = self.trader.order_stock(
                account=account,
                stock_code=code,
                order_type=xt_order_type,
                order_volume=volume,
                price_type=xt_price_type,
                price=price,
                strategy_name=strategy_name,
                order_remark=order_remark or f'{order_type}_{code}'
            )
            
            # 立即返回True表示请求已发送（不表示执行成功）
            print(f"异步下单请求已发送: {code}, 数量: {volume}, 序列号: {order_id}")
            return True
            
        except Exception as e:
            ErrorHandler.log_error(f"异步下单请求失败: {str(e)}")
            return False
    
    def batch_order(self, account_id: str, orders: list) -> list:
        """批量下单"""
        results = []
        for order in orders:
            order_id = self.sync_order(
                account_id, 
                order['code'], 
                order['order_type'], 
                order['volume'], 
                order.get('price', 0), 
                order.get('price_type', 'market'),
                order.get('strategy_name', 'EasyXT'),
                order.get('order_remark', '')
            )
            results.append(order_id)
            time.sleep(0.1)  # 避免过快下单
        return results
    
    def batch_order_async(self, account_id: str, orders: list) -> list:
        """异步批量下单"""
        results = []
        for order in orders:
            success = self.async_order(
                account_id, 
                order['code'], 
                order['order_type'], 
                order['volume'], 
                order.get('price', 0), 
                order.get('price_type', 'market'),
                order.get('strategy_name', 'EasyXT'),
                order.get('order_remark', '')
            )
            results.append(success)
            time.sleep(0.1)  # 避免过快下单
        return results
    
    def condition_order(self, account_id: str, code: str, condition_type: str,
                       trigger_price: float, order_type: str, volume: int,
                       target_price: float = 0) -> bool:
        """条件单（真实实现）
        
        通过后台线程监控价格，当达到触发条件时执行交易
        """
        try:
            # 使用xtdata.get_full_tick获取实时行情数据，这是EasyXT中使用的方法
            from xtquant import xtdata
            import pandas as pd
            
            # 获取当前价格
            normalized_code = StockCodeUtils.normalize_code(code)
            tick_data = None
            try:
                tick_data = xtdata.get_full_tick([normalized_code])
            except Exception as e:
                print(f"获取实时行情失败: {str(e)}")
                tick_data = None
            
            current_price = 0
            if tick_data and normalized_code in tick_data:
                tick_info = tick_data[normalized_code]
                if tick_info and 'lastPrice' in tick_info:
                    current_price = float(tick_info['lastPrice'])
                elif tick_info and 'price' in tick_info:
                    current_price = float(tick_info['price'])
            
            # 如果get_full_tick失败，再尝试get_market_data作为备选
            if current_price == 0:
                try:
                    current_data = xtdata.get_market_data(
                        stock_list=[normalized_code],
                        period='tick',
                        count=1
                    )
                    
                    if current_data and isinstance(current_data, dict) and normalized_code in current_data:
                        data_array = current_data[normalized_code]
                        if hasattr(data_array, '__len__') and len(data_array) > 0:
                            first_item = data_array[0]
                            if hasattr(first_item, 'lastPrice'):
                                current_price = float(first_item['lastPrice'])
                            elif hasattr(first_item, '__getitem__') and 'lastPrice' in first_item.dtype.names if hasattr(first_item, 'dtype') and hasattr(first_item.dtype, 'names') else False:
                                current_price = float(first_item['lastPrice'])
                except Exception as e:
                    print(f"获取tick数据失败: {str(e)}")
                    current_price = 0
            
            if current_price == 0:
                print(f"无法获取{code}的当前价格，条件单设置失败")
                return False
            
            print(f"{code} 当前价格: {current_price}, 触发价格: {trigger_price}")
            
            # 启动条件单监控线程
            thread = Thread(
                target=self._monitor_condition_order,
                args=(account_id, code, condition_type, trigger_price, order_type, volume, target_price, current_price),
                daemon=True
            )
            thread.start()
            
            print(f"条件单设置成功: {code}, 类型: {condition_type}, 触发价: {trigger_price}")
            return True
            
        except Exception as e:
            print(f"条件单设置失败: {str(e)}")
            return False
    
    def _monitor_condition_order(self, account_id: str, code: str, condition_type: str,
                                trigger_price: float, order_type: str, volume: int,
                                target_price: float, initial_price: float):
        """后台监控条件单
        
        Args:
            account_id: 账户ID
            code: 股票代码
            condition_type: 条件类型 ('stop_loss'止损, 'take_profit'止盈)
            trigger_price: 触发价格
            order_type: 订单类型 ('buy'买入, 'sell'卖出)
            volume: 交易数量
            target_price: 目标价格
            initial_price: 初始价格
        """
        import time
        from xtquant import xtdata
        
        code = StockCodeUtils.normalize_code(code)
        
        # 确定触发条件
        if condition_type == 'stop_loss':
            # 止损：当价格跌破触发价时卖出
            trigger_condition = lambda current, trigger: current <= trigger
        elif condition_type == 'take_profit':
            # 止盈：当价格涨过触发价时卖出
            trigger_condition = lambda current, trigger: current >= trigger
        else:
            print(f"不支持的条件单类型: {condition_type}")
            return
        
        print(f"开始监控条件单: {code}, {condition_type}, 触发价: {trigger_price}")
        
        # 持续监控价格
        while True:
            try:
                # 使用get_full_tick获取实时价格，这是最可靠的方法
                current_price = None
                try:
                    tick_data = xtdata.get_full_tick([code])
                    if tick_data and code in tick_data:
                        tick_info = tick_data[code]
                        if tick_info and 'lastPrice' in tick_info:
                            current_price = float(tick_info['lastPrice'])
                        elif tick_info and 'price' in tick_info:
                            current_price = float(tick_info['price'])
                except Exception as e:
                    print(f"获取实时tick数据失败: {str(e)}")
                    current_price = None
                
                # 如果get_full_tick失败，尝试get_market_data作为备选
                if current_price is None or current_price <= 0:
                    try:
                        current_data = xtdata.get_market_data(
                            stock_list=[code],
                            period='tick',
                            count=1
                        )
                        
                        if current_data and isinstance(current_data, dict) and code in current_data:
                            data_array = current_data[code]
                            if hasattr(data_array, '__len__') and len(data_array) > 0:
                                first_item = data_array[0]
                                if hasattr(first_item, 'lastPrice'):
                                    current_price = float(first_item['lastPrice'])
                                elif hasattr(first_item, '__getitem__') and 'lastPrice' in first_item.dtype.names if hasattr(first_item, 'dtype') and hasattr(first_item.dtype, 'names') else False:
                                    current_price = float(first_item['lastPrice'])
                    except Exception as e:
                        print(f"获取tick数据失败: {str(e)}")
                        current_price = None
                
                if current_price is not None and current_price > 0:
                    print(f"{code} 实时价格: {current_price}, 触发价: {trigger_price}")
                    
                    # 检查是否触发条件
                    if trigger_condition(current_price, trigger_price):
                        print(f"条件单触发: {code}, 当前价格: {current_price}, 触发价: {trigger_price}")
                        
                        # 执行订单 - 使用目标价格或当前价格
                        execution_price = target_price if target_price > 0 else current_price
                        
                        # 确保卖出方向
                        actual_order_type = 'sell' if order_type.lower() in ['sell', '卖出'] else 'sell'
                        
                        order_id = self.sync_order(
                            account_id=account_id,
                            code=code,
                            order_type=actual_order_type,
                            volume=volume,
                            price=execution_price,
                            price_type='limit' if target_price > 0 else 'market'
                        )
                        
                        if order_id:
                            print(f"条件单执行成功: {code}, 委托号: {order_id}")
                        else:
                            print(f"条件单执行失败: {code}")
                        
                        # 执行完成后退出监控
                        break
                    else:
                        print(f"条件未满足: {current_price} 与 {trigger_price} 的关系不满足触发条件")
                else:
                    print(f"无法获取有效实时价格: {current_price}")
                
                # 等待一段时间再检查 (避免过于频繁的API调用)
                time.sleep(5)  # 每5秒检查一次
                
            except Exception as e:
                print(f"监控条件单时出错: {str(e)}")
                time.sleep(5)  # 出错时也等待5秒再继续
                continue
    
    def sync_cancel_order(self, account_id: str, order_id: int) -> bool:
        """同步撤单"""
        if not self.trader or account_id not in self.accounts:
            ErrorHandler.log_error("高级交易服务未连接或账户未添加")
            return False
            
        account = self.accounts[account_id]
        
        try:
            # 先检查委托状态
            orders = self.trader.query_stock_orders(account)
            if orders:
                for order in orders:
                    if order.order_id == order_id:
                        # 检查订单状态，如果已成交或已撤销，不能撤单
                        if hasattr(order, 'order_status'):
                            if xt_const and order.order_status in [xt_const.ORDER_SUCCEEDED, xt_const.ORDER_CANCELED, 
                                                    xt_const.ORDER_PART_CANCEL, xt_const.ORDER_JUNK]:
                                print(f"委托 {order_id} 已成交或已撤销，无法撤单")
                                return False
            
            # 尝试撤单
            result = self.trader.cancel_order_stock(account, order_id)
            if result == 0:
                print(f"同步撤单成功: {order_id}")
                return True
            else:
                print(f"同步撤单失败，错误码: {result}")
                return False
                
        except Exception as e:
            print(f"同步撤单操作失败: {str(e)}")
            return False
    
    def batch_cancel_orders(self, account_id: str, order_ids: list) -> list:
        """批量撤单"""
        results = []
        for order_id in order_ids:
            result = self.sync_cancel_order(account_id, order_id)
            results.append(result)
            time.sleep(0.1)  # 避免过快撤单
        return results
    
    def get_account_asset_detailed(self, account_id: str) -> Optional[Dict[str, Any]]:
        """获取详细账户资产"""
        if not self.trader or account_id not in self.accounts:
            ErrorHandler.log_error("高级交易服务未连接或账户未添加")
            return None
            
        account = self.accounts[account_id]
        
        try:
            asset = self.trader.query_stock_asset(account)
            if asset:
                return {
                    'account_id': asset.account_id,
                    'cash': asset.cash,
                    'frozen_cash': asset.frozen_cash,
                    'market_value': asset.market_value,
                    'total_asset': asset.total_asset,
                    'profit_loss': getattr(asset, 'profit_loss', 0.0),
                    'update_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            return None
            
        except Exception as e:
            ErrorHandler.log_error(f"获取详细账户资产失败: {str(e)}")
            return None
    
    def get_positions_detailed(self, account_id: str, code: str = '') -> pd.DataFrame:
        """获取详细持仓"""
        """获取详细持仓"""
        if not self.trader or account_id not in self.accounts:
            ErrorHandler.log_error("高级交易服务未连接或账户未添加")
            return pd.DataFrame()
            
        account = self.accounts[account_id]
        
        try:
            if code:
                code = StockCodeUtils.normalize_code(code)
                position = self.trader.query_stock_position(account, code)
                if position:
                    return pd.DataFrame([{
                        'code': position.stock_code,
                        'stock_name': getattr(position, 'stock_name', ''),
                        'volume': position.volume,
                        'can_use_volume': position.can_use_volume,
                        'open_price': position.open_price,
                        'market_value': position.market_value,
                        'frozen_volume': position.frozen_volume,
                        'profit_loss': getattr(position, 'profit_loss', 0.0),
                        'profit_loss_ratio': getattr(position, 'profit_loss_ratio', 0.0),
                        'update_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }])
                else:
                    return pd.DataFrame()
            else:
                positions = self.trader.query_stock_positions(account)
                if positions:
                    data = []
                    for pos in positions:
                        data.append({
                            'code': pos.stock_code,
                            'stock_name': getattr(pos, 'stock_name', ''),
                            'volume': pos.volume,
                            'can_use_volume': pos.can_use_volume,
                            'open_price': pos.open_price,
                            'market_value': pos.market_value,
                            'frozen_volume': pos.frozen_volume,
                            'profit_loss': getattr(pos, 'profit_loss', 0.0),
                            'profit_loss_ratio': getattr(pos, 'profit_loss_ratio', 0.0),
                            'update_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                    return pd.DataFrame(data)
                else:
                    return pd.DataFrame()
                    
        except Exception as e:
            ErrorHandler.log_error(f"获取详细持仓信息失败: {str(e)}")
            return pd.DataFrame()
    
    def get_today_orders(self, account_id: str, cancelable_only: bool = False) -> pd.DataFrame:
        """获取当日委托"""
        if not self.trader or account_id not in self.accounts:
            ErrorHandler.log_error("高级交易服务未连接或账户未添加")
            return pd.DataFrame()
            
        account = self.accounts[account_id]
        
        try:
            orders = self.trader.query_stock_orders(account, cancelable_only)
            if orders:
                data = []
                for order in orders:
                    order_type_name = '买入' if xt_const and order.order_type == xt_const.STOCK_BUY else '卖出'
                    
                    status_map = {
                        (xt_const.ORDER_UNREPORTED if xt_const else 0): '未报',
                        (xt_const.ORDER_WAIT_REPORTING if xt_const else 1): '待报',
                        (xt_const.ORDER_REPORTED if xt_const else 2): '已报',
                        (xt_const.ORDER_PART_SUCC if xt_const else 3): '部成',
                        (xt_const.ORDER_SUCCEEDED if xt_const else 4): '已成',
                        (xt_const.ORDER_PART_CANCEL if xt_const else 5): '部撤',
                        (xt_const.ORDER_CANCELED if xt_const else 6): '已撤',
                        (xt_const.ORDER_JUNK if xt_const else 7): '废单'
                    }
                    status_name = status_map.get(order.order_status, '未知')
                    
                    data.append({
                        'order_id': order.order_id,
                        'stock_code': order.stock_code,
                        'order_type': order_type_name,
                        'order_volume': order.order_volume,
                        'order_price': order.price,
                        'traded_volume': order.traded_volume,
                        'order_status': status_name,
                        'order_time': order.order_time,
                        'order_remark': order.order_remark
                    })
                return pd.DataFrame(data)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            ErrorHandler.log_error(f"获取当日委托失败: {str(e)}")
            return pd.DataFrame()
    
    def get_today_trades(self, account_id: str) -> pd.DataFrame:
        """获取当日成交"""
        if not self.trader or account_id not in self.accounts:
            ErrorHandler.log_error("高级交易服务未连接或账户未添加")
            return pd.DataFrame()
            
        account = self.accounts[account_id]
        
        try:
            trades = self.trader.query_stock_trades(account)
            if trades:
                data = []
                for trade in trades:
                    order_type_name = '买入' if xt_const and trade.order_type == xt_const.STOCK_BUY else '卖出'
                    
                    data.append({
                        'trade_id': trade.traded_id,
                        'order_id': trade.order_id,
                        'stock_code': trade.stock_code,
                        'stock_name': getattr(trade, 'stock_name', ''),
                        'order_type': order_type_name,
                        'traded_volume': trade.traded_volume,
                        'traded_price': trade.traded_price,
                        'traded_amount': trade.traded_amount,
                        'traded_time': trade.traded_time,
                        'strategy_name': getattr(trade, 'strategy_name', ''),
                        'order_remark': getattr(trade, 'order_remark', '')
                    })
                return pd.DataFrame(data)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            ErrorHandler.log_error(f"获取当日成交失败: {str(e)}")
            return pd.DataFrame()
    
    def subscribe_realtime_data(self, codes, period='tick', callback=None) -> bool:
        """订阅实时数据"""
        try:
            # 这里应该实现真实的实时数据订阅
            print(f"实时数据订阅成功: {codes}")
            return True
        except Exception as e:
            ErrorHandler.log_error(f"订阅实时数据失败: {str(e)}")
            return False
    
    def download_history_data(self, codes, period='1d', start=None, end=None) -> bool:
        """下载历史数据"""
        try:
            # 这里应该实现真实的历史数据下载
            print(f"历史数据下载成功: {codes}")
            return True
        except Exception as e:
            ErrorHandler.log_error(f"下载历史数据失败: {str(e)}")
            return False
    
    def get_local_data(self, codes, period='1d', count=10):
        """获取本地数据"""
        try:
            # 使用xtdata获取历史数据
            from xtquant import xtdata
            
            if isinstance(codes, str):
                codes = [codes]
            
            data_frames = []
            for code in codes:
                code = StockCodeUtils.normalize_code(code)
                data = xtdata.get_market_data(
                    stock_list=[code],
                    period=period,
                    count=count
                )
                
                # 检查数据类型和内容
                if data is not None:
                    if isinstance(data, dict):
                        # 如果是字典，尝试转换为DataFrame
                        if code in data and len(data[code]) > 0:
                            df = pd.DataFrame(data[code])
                            df['code'] = code
                            data_frames.append(df)
                    elif hasattr(data, 'empty') and not data.empty:
                        # 如果是DataFrame且不为空
                        data['code'] = code
                        data_frames.append(data)
                    elif isinstance(data, pd.DataFrame):
                        # 如果是DataFrame但可能为空
                        if len(data) > 0:
                            data['code'] = code
                            data_frames.append(data)
            
            if data_frames:
                return pd.concat(data_frames, ignore_index=True)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            ErrorHandler.log_error(f"获取本地数据失败: {str(e)}")
            return pd.DataFrame()
    
    def disconnect(self):
        """断开连接"""
        if self.trader:
            try:
                self.trader.stop()
                print("高级交易服务已断开")
            except Exception as e:
                ErrorHandler.log_error(f"断开高级交易服务失败: {str(e)}")