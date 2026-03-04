# ========================================
# 聚宽策略转Ptrade - LIVE版本
# 转换时间: 2026-03-02 09:55:55
# ========================================


# ========================================
# Ptrade基本面数据处理说明
# ========================================
# Ptrade支持get_fundamentals函数，但query语法可能略有不同
# 如果出现语法错误，请检查以下内容：
# 1. query()函数的参数格式
# 2. valuation对象的字段名称
# 3. filter()条件的写法
# 4. order_by()方法的参数
# ========================================


# import jqdata  # 聚宽数据模块已移除
# from jqfactor import MACD, RSI  # 聚宽因子库需要手动处理



# ========================================
# 技术指标实现
# ========================================
# 如果策略使用了聚宽因子库中的技术指标，需要自行实现或使用Ptrade提供的指标
# 以下是常用技术指标的实现示例：

def get_MACD(close_prices, short_period=12, long_period=26, signal_period=9):
    """计算MACD指标"""
    import pandas as pd
    ema_short = pd.Series(close_prices).ewm(span=short_period).mean()
    ema_long = pd.Series(close_prices).ewm(span=long_period).mean()
    dif = ema_short - ema_long
    dea = dif.ewm(span=signal_period).mean()
    bar = (dif - dea) * 2
    return dif.values, dea.values, bar.values

def get_RSI(close_prices, period=14):
    """计算RSI指标"""
    import pandas as pd
    import numpy as np
    delta = pd.Series(close_prices).diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.values

# ========================================

def initialize(context):
    # 初始化
    context.stock_num = 10
    context.hold_list = []
    set_benchmark('000300.SS')

    # 设置定时任务
    run_daily(context, weekly_adjustment, time='9:30')
    run_daily(context, check_limit_up, time='14:00')

def get_stock_list(context):
    """获取股票池"""
    # 获取A股列表
    initial_list = get_Ashares(date=context.current_date)

    # 基本面筛选
    # [需要手动调整] Ptrade中query语法可能不同
# 原始代码: q = query(valuation.code).filter(
        valuation.code.in_(initial_list)
# 请根据Ptrade文档调整query语法
q = query(valuation.code).filter(
        valuation.code.in_(initial_list),
        indicator.eps > 0
    ).order_by(valuation.circulating_market_cap.asc()).limit(100)

    df = get_fundamentals(q)
    stock_pool = df['code'].tolist()

    # 因子筛选
    factor_list = get_single_factor_list(context, stock_pool, 'sales_growth', False, 0, 0.3)

    return factor_list

def get_single_factor_list(context, stock_list, jqfactor, sort, p1, p2):
    """获取因子列表"""
    s_score = # [Ptrade注意] 确认支持该因子
 get_factor_values(stock_list, jqfactor, end_date=context.previous_date, count=1)
    return s_score[jqfactor].iloc[0].dropna().sort_values(ascending=sort).index[int(p1*len(stock_list)):int(p2*len(stock_list))].tolist()

def weekly_adjustment(context):
    """周度调整"""
    target_list = get_stock_list(context)

    # 技术指标过滤
    for stock in target_list:
        macd_value = get_macd_value(context, stock)
        if macd_value < 0:
            continue
        # 开仓逻辑...
        order_target_value(stock, 100000)

def check_limit_up(context):
    """检查涨停"""
    current_data = get_snapshot()
    for stock in context.hold_list:
        if current_data[stock].last_price >= current_data[stock].high_limit:
            log.info(f'{stock} 涨停')

def handle_data(context, data):
    pass
