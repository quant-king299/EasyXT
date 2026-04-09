# 克隆自聚宽文章：https://www.joinquant.com/post/19619
# 标题：【策略】夏普超过2.0，后市靠定增一步步往上爬
# 作者：安藤忠雄

# 导入函数库
import jqdata
import pandas as pd
import numpy as np
from math import log as lg

MY_EXCLUDE_STOCKS = ["600656.XSHG","000594.XSHE"]
# 初始化函数，设定要操作的股票、基准等等
def initialize(context):
    set_option("avoid_future_data", True)
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    
    g.s1 = '000001.XSHG'
    g.small_cap_num = 50
    g.stop_index_drop = -0.03
    g.win_length = 126
    g.rel_return = -0.5 
    g.max_weight = 0.3 
    
    # schedule rebalance function/定时器
    run_daily(rebalance,time='14:21')
    
def before_trading_start(context): 
    fundamental_df = get_fundamentals(
        query(
            valuation.code
        ).order_by(
            valuation.market_cap.asc()
        ).limit(
            g.small_cap_num 
        )
    )
    g.stocks=np.array([i[0] for i in fundamental_df.values])
  
    
    
    g.stocks = remove_st(g.stocks) 
    
    
def remove_st(stocks):
    result = []
    for s in stocks:
        if ( not get_current_data()[s].is_st) and (s not in MY_EXCLUDE_STOCKS):
            result.append(s)
    return np.array(result)

# 交易日志
def trade_log(stock, weight):
    log.info("[ %s(%s) -> %.2f]" % (stock_name(stock), stock, weight))

# 股票名字
def stock_name(stock):
    return get_security_info(stock).display_name
    
def rebalance(context):
    bar_dict = get_current_data()
    
    for stock in context.portfolio.positions.keys():
        if stock not in g.stocks:
            order_target_value(stock, 0); trade_log(stock, 0)#打印交易日志
    
    index_hist = attribute_history(g.s1,2, "1d", "close")
    index_return_1d = lg(index_hist['close'][1]/index_hist['close'][0]) 
    if index_return_1d < g.stop_index_drop: 
        for stock in g.stocks:
            order_target_value(stock, 0); trade_log(stock, 0)
        return
    
    a = g.stocks.tolist()
    a.append(g.s1)
    set_universe(a)
    stock_hist = history(g.win_length, "1d", "close")
    stock_return = (stock_hist.ix[g.win_length-1]-stock_hist.ix[0])/stock_hist.ix[0] 
    index_return = stock_return[g.s1] 
    rel_return = stock_return - index_return
    g.stocks = [stock for stock in g.stocks if not bar_dict[stock].paused 
    and get_bars(stock, 1, '1m', 'volume', include_now=True)['volume']!=0
    and bar_dict[stock].day_open<1.095*stock_hist[stock].iloc[-1] 
    and bar_dict[stock].day_open>0.905*stock_hist[stock].iloc[-1] 
    and rel_return[stock]<abs(index_return)*g.rel_return]
    
    if len(g.stocks) == 0:
        return
    
    weight = {}
    sum_weight = 0 
    for stock in g.stocks:
        weight[stock] = abs((rel_return[stock]-abs(index_return)*g.rel_return)/(index_return) ) * g.max_weight # 超跌的相对情况 |(个股上证相对调幅-|上证调幅|*(-0.5))/(上证调幅)|*0.3
        if weight[stock] > g.max_weight: 
            weight[stock] = g.max_weight
        sum_weight += weight[stock]
        
    for stock in g.stocks:
        weight[stock] /= sum_weight # 归一化
        if weight[stock] > g.max_weight: # 单个股票仓位控制
            weight[stock] = g.max_weight
        trade_log(stock, weight[stock])
        value = context.portfolio.total_value * weight[stock]
        order_target_value(stock, value) 



