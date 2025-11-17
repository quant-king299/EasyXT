# 自动生成的Ptrade策略代码
# 原始代码来自聚宽策略

# 初始化
def initialize(context):
    log.info('初始函数开始运行且全局只运行一次')
    # Ptrade使用标准函数，不使用run_daily等聚宽特定函数

# 盘前处理
def before_trading_start(context, data):
    log.info('函数运行时间(before_trading_start)：' + str(context.current_dt.time()))
    context.security = '000001.XSHE'

# 盘中处理
def handle_data(context, data):
    log.info('函数运行时间(handle_data):' + str(context.current_dt.time()))
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

# 收盘后处理
def after_trading_end(context, data):
    log.info(str('函数运行时间(after_trading_end):' + str(context.current_dt.time())))
    trades = get_trades()
    for _trade in trades.values():
        log.info('成交记录：' + str(_trade))
    log.info('一天结束')
    log.info('##############################################################')