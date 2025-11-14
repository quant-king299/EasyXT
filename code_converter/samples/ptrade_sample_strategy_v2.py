# 自动生成的Ptrade策略代码
# 原始代码来自聚宽策略

def initialize(context):
    context.security = '000001.XSHE'
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013, min_cost=5))
    set_slippage(PriceRelatedSlippage(0.002))
    run_daily(market_open, time='open')

def market_open(context):
    security = context.security
    close_data = attribute_history(security, 5, '1d', ['close'])
    MA5 = close_data['close'].mean()
    current_price = close_data['close'][-1]
    cash = context.portfolio.cash
    if current_price > 1.01 * MA5:
        order_value(security, cash)
        log.info('Buying %s' % security)
    elif current_price < MA5 and context.portfolio.positions[security].closeable_amount > 0:
        order_target(security, 0)
        log.info('Selling %s' % security)
    record(stock_price=current_price)
    current_data = get_current_data()
    if security in current_data:
        log.info('当前价格: %.2f' % current_data[security].last_price)