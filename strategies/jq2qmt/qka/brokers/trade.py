from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
import random
from qka.utils.util import timestamp_to_datetime_string, parse_order_type, convert_to_current_date
from qka.utils.anis import RED, GREEN, YELLOW, BLUE, RESET
from qka.utils.logger import logger

error_orders = []

class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"

class OrderType(Enum):
    """订单类型"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class Order:
    """订单对象"""
    
    def __init__(self, symbol: str, side: str, quantity: int, 
                 order_type: str = "market", price: Optional[float] = None,
                 order_id: Optional[str] = None):
        """
        初始化订单
        
        Args:
            symbol: 股票代码
            side: 买卖方向 ("buy" 或 "sell")
            quantity: 数量
            order_type: 订单类型
            price: 价格（限价单需要）
            order_id: 订单ID
        """
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.order_type = order_type
        self.price = price
        self.order_id = order_id or self._generate_order_id()
        self.status = OrderStatus.PENDING.value
        self.created_time = datetime.now()
        self.filled_quantity = 0
        self.remaining_quantity = quantity
    
    def _generate_order_id(self) -> str:
        """生成订单ID"""
        import uuid
        return str(uuid.uuid4())[:8]

class Trade:
    """交易记录"""
    
    def __init__(self, order_id: str, symbol: str, side: str, 
                 quantity: int, price: float, commission: float = 0.0):
        """
        初始化交易记录
        
        Args:
            order_id: 订单ID
            symbol: 股票代码
            side: 买卖方向
            quantity: 成交数量
            price: 成交价格
            commission: 手续费
        """
        self.order_id = order_id
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.price = price
        self.commission = commission
        self.trade_time = datetime.now()
        self.trade_value = quantity * price

class Position:
    """持仓信息"""
    
    def __init__(self, symbol: str, quantity: int = 0, avg_price: float = 0.0):
        """
        初始化持仓
        
        Args:
            symbol: 股票代码
            quantity: 持仓数量
            avg_price: 平均持仓价格
        """
        self.symbol = symbol
        self.quantity = quantity
        self.avg_price = avg_price
        self.market_value = 0.0
        self.unrealized_pnl = 0.0
        self.realized_pnl = 0.0
    
    def update_market_price(self, current_price: float):
        """更新市场价格和盈亏"""
        self.market_value = self.quantity * current_price
        if self.quantity > 0:
            self.unrealized_pnl = (current_price - self.avg_price) * self.quantity

class MyXtQuantTraderCallback(XtQuantTraderCallback):
    def on_disconnected(self):
        """
        连接状态回调
        :return:
        """
        print("connection lost")
    def on_stock_order(self, order):
        """
        委托信息推送
        :param order: XtOrder对象
        :return:
        """
        # 委托
        if order.order_status == 50:
            logger.info(f"{BLUE}【已委托】{RESET} {parse_order_type(order.order_type)} 代码:{order.stock_code} 名称:{order.order_remark} 委托价格:{order.price:.2f} 委托数量:{order.order_volume} 订单编号:{order.order_id} 委托时间:{timestamp_to_datetime_string(convert_to_current_date(order.order_time))}")
        elif order.order_status == 53 or order.order_status == 54:
            logger.warning(f"{YELLOW}【已撤单】{RESET} {parse_order_type(order.order_type)} 代码:{order.stock_code} 名称:{order.order_remark} 委托价格:{order.price:.2f} 委托数量:{order.order_volume} 订单编号:{order.order_id} 委托时间:{timestamp_to_datetime_string(convert_to_current_date(order.order_time))}")

    def on_stock_trade(self, trade):
        """
        成交信息推送
        :param trade: XtTrade对象
        :return:
        """
        logger.info(f"{GREEN}【已成交】{RESET} {parse_order_type(trade.order_type)} 代码:{trade.stock_code} 名称:{trade.order_remark} 成交价格:{trade.traded_price:.2f} 成交数量:{trade.traded_volume} 成交编号:{trade.order_id} 成交时间:{timestamp_to_datetime_string(convert_to_current_date(trade.traded_time))}")

    def on_order_error(self, data):
        if data.order_id in error_orders:
            return
        error_orders.append(data.order_id)
        logger.error(f"{RED}【委托失败】{RESET}错误信息:{data.error_msg.strip()}")

    def on_cancel_error(self, data):
        if data.order_id in error_orders:
            return
        error_orders.append(data.order_id)
        logger.error(f"{RED}【撤单失败】{RESET}错误信息:{data.error_msg.strip()}")


def create_trader(account_id, mini_qmt_path):
    # 创建session_id
    session_id = int(random.randint(100000, 999999))
    # 创建交易对象
    xt_trader = XtQuantTrader(mini_qmt_path, session_id)
    # 启动交易对象
    xt_trader.start()
    # 连接客户端
    connect_result = xt_trader.connect()

    if connect_result == 0:
        logger.debug(f"{GREEN}【miniQMT连接成功】{RESET} 路径:{mini_qmt_path}")

    # 创建账号对象
    account = StockAccount(account_id)
    # 订阅账号
    xt_trader.subscribe(account)
    logger.debug(f"{GREEN}【账号订阅成功】{RESET} 账号ID:{account_id}")
    # 注册回调类
    xt_trader.register_callback(MyXtQuantTraderCallback())

    return xt_trader, account