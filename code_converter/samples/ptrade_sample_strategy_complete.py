# 自动生成的Ptrade策略代码
# 原始代码来自聚宽策略

def initialize(context):
    context.security = '000001.XSHE'
    context.benchmark = '000300.XSHG'
    set_benchmark(context.benchmark)
    set_option('use_real_price', True)
    set_option('max_history_window', 60)
    set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013, min_cost=5))
    set_slippage(PriceRelatedSlippage(0.002))
    run_daily(daily_task, time='open')
    run_weekly(weekly_task, weekday=1, time='open')
    run_monthly(monthly_task, monthday=1, time='open')

def before_trading_start(context):
    """开盘前处理"""
    context.stocks = get_index_stocks(context.benchmark)
    log.info('今日股票池数量: %d' % len(context.stocks))
    industry_stocks = get_industry_stocks('A01', date=None)
    all_securities = get_all_securities(types=['stock'], date=None)
    security_info = get_security_info(context.security)

def daily_task(context):
    """每日任务"""
    price_data = get_price(context.security, count=10, end_date=None, frequency='1d', fields=['open', 'close', 'high', 'low', 'volume'])
    current_data = get_current_data()
    fundamentals = get_fundamentals(query(valuation.market_cap, income.net_profit).filter(valuation.code == context.security))
    positions = get_positions()
    portfolio = get_portfolio()
    open_orders = get_open_orders()
    log.info('当前持仓数量: %d' % len(positions))
    log.info('总资产: %.2f' % portfolio.total_value)

def weekly_task(context):
    """每周任务"""
    record(security=context.security, benchmark=context.benchmark)

def monthly_task(context):
    """每月任务"""
    plot('portfolio_value', context.portfolio.total_value)

def handle_data(context, data):
    """处理数据函数"""
    security = context.security
    hist = attribute_history(security, 10, '1d', ['close', 'volume'])
    ma5 = hist['close'].mean()
    current_price = hist['close'][-1]
    if current_price > ma5 * 1.02:
        order_value(security, context.portfolio.cash * 0.2)
        log.info('买入 %s' % security)
    elif current_price < ma5 * 0.98 and context.portfolio.positions[security].closeable_amount > 0:
        order_target(security, 0)
        log.info('卖出 %s' % security)
    open_orders = get_open_orders()
    for order_id, order_obj in open_orders.items():
        if order_obj.status == OrderStatus.open:
            cancel_order(order_id)
            log.info('撤单: %s' % order_id)