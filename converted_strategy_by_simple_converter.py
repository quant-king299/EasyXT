# 自动生成的Ptrade策略代码
# 原始代码来自聚宽策略

def initialize(context):
    log.info('初始函数开始运行且全局只运行一次')
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
    run_daily(market_open, time='open', reference_security='000300.XSHG')
    run_daily(after_market_close, time='after_close', reference_security='000300.XSHG')

def before_market_open(context):
    log.info('函数运行时间(before_market_open)：' + str(context.current_dt.time()))
    context.security = '000001.XSHE'

def market_open(context):
    log.info('函数运行时间(market_open):' + str(context.current_dt.time()))
    security = context.security
    close_data = get_price(security, count=5, unit='1d', fields=['close'])
    MA5 = close_data['close'].mean()
    current_price = close_data['close'][-1]
    cash = context.portfolio.available_cash
    if current_price > 1.01 * MA5 and cash > 0:
        log.info('价格高于均价 1%%, 买入 %s' % security)
        order_value(security, cash)
    elif current_price < MA5 and context.portfolio.positions[security].closeable_amount > 0:
        log.info('价格低于均价, 卖出 %s' % security)
        order_target(security, 0)

def after_market_close(context):
    log.info(str('函数运行时间(after_market_close):' + str(context.current_dt.time())))
    trades = get_trades()
    for _trade in trades.values():
        log.info('成交记录：' + str(_trade))
    log.info('一天结束')
    log.info('##############################################################')
def before_trading_start(context, data):
    # 盘前处理
    pass


def handle_data(context, data):
    # 盘中处理
    pass


def after_trading_end(context, data):
    # 收盘后处理
    pass

