from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
import random
from qka.utils import timestamp_to_datetime_string, parse_order_type, convert_to_current_date
from qka.anis import RED, GREEN, YELLOW, BLUE, RESET
from qka.logger import logger

error_orders = []

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