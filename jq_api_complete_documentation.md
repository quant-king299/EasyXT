# 聚宽(JoinQuant) API完整文档

来源: [聚宽官方API文档](https://www.joinquant.com/help/api/help)
更新时间: 2025-11-14

## 目录

1. [策略编写基础](#策略编写基础)
2. [数据获取API](#数据获取api)
3. [交易API](#交易api)
4. [账户与持仓](#账户与持仓)
5. [技术指标](#技术指标)
6. [金融数据](#金融数据)
7. [宏观经济数据](#宏观经济数据)
8. [系统函数](#系统函数)
9. [风险控制](#风险控制)
10. [回测参数](#回测参数)
11. [实盘交易](#实盘交易)

## 策略编写基础

### initialize(context)
初始化函数，在整个回测模拟实盘中最初执行一次，用于初始化一些全局变量。

参数:
- context: Context对象，存放有当前的账户/股票持仓信息

返回: None

示例:
```python
def initialize(context):
    # 定义一个全局变量, 保存要操作的股票
    g.security = '000001.XSHE'
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
```

### handle_data(context, data)
该函数每个单位时间会调用一次，如果按天回测，则每天调用一次，如果按分钟，则每分钟调用一次。

参数:
- context: Context对象，存放有当前的账户/标的持仓信息
- data: 一个字典，key是股票代码，value是当前的SecurityUnitData对象

注意事项:
- 该函数依据的时间是股票的交易时间，即 9:30 - 15:00
- 该函数在回测中的非交易日是不会触发的

### before_trading_start(context)
该函数会在每天开始交易前被调用一次，可用于每日初始化。

### after_trading_end(context)
该函数会在每天结束交易后被调用一次，可用于收盘后处理。

### run_monthly/run_weekly/run_daily
定时运行函数，可设定策略定期执行。

```python
def initialize(context):
    # 按月运行
    run_monthly(func, monthday, time='open', reference_security)
    # 按周运行
    run_weekly(func, weekday, time='open', reference_security)
    # 每天内录时运行
    run_daily(func, time='open', reference_security)
```

参数说明:
- func: 一个函数，此函数必须接受context参数
- monthday/weekday: 指定每月/每周的第几个交易日
- time: 执行时间，支持具体时间表达式
- reference_security: 时间的参考标的

## 数据获取API

### get_price
获取历史数据

```python
get_price(security, start_date=None, end_date=None, frequency='1d', fields=None, skip_paused=False, fq='pre', count=None)
```

参数:
- security: 标的代码
- start_date/end_date: 起止日期
- frequency: 数据频率('1d', '1m', '5m', '15m', '30m', '60m')
- fields: 获取字段(['open', 'close', 'high', 'low', 'volume', 'money'])
- skip_paused: 是否跳过停牌
- fq: 复权方式('pre'-前复权, 'post'-后复权, 'None'-不复权)
- count: 数据数量

### get_current_data
获取当前行情数据

```python
get_current_data()
```

返回值是一个dict，其中key是股票代码，value是拥有以下属性的对象:
- last_price: 最新价
- high_limit: 涨停价
- low_limit: 跌停价
- paused: 是否停牌
- is_st: 是否是ST
- day_open: 当天开盘价
- name: 股票名称

### get_fundamentals
获取财务数据

```python
get_fundamentals(query_object, date=None, statDate=None)
```

### get_index_stocks
获取指数成分股

```python
get_index_stocks(index_symbol, date=None)
```

### get_industry_stocks
获取行业成分股

```python
get_industry_stocks(industry_code, date=None)
```

### get_concept_stocks
获取概念板块成分股

```python
get_concept_stocks(concept_code, date=None)
```

### get_all_securities
获取所有标的

```python
get_all_securities(types=[], date=None)
```

### get_security_info
获取单个标的信息

```python
get_security_info(code)
```

## 交易API

### order
基础下单函数，按股数下单

```python
order(security, amount, style=None, price=None, account=None)
```

参数:
- security: 标的代码
- amount: 下单数量（股），正数表示买入，负数表示卖出
- style: 订单类型
- price: 价格
- account: 指定账户

### order_value
按价值下单

```python
order_value(security, value, style=None, price=None, account=None)
```

参数:
- security: 标的代码
- value: 下单价值（元），正数表示买入，负数表示卖出

### order_target
目标股数下单

```python
order_target(security, amount, style=None, price=None, account=None)
```

参数:
- security: 标的代码
- amount: 目标股数

### order_target_value
目标价值下单

```python
order_target_value(security, value, style=None, price=None, account=None)
```

参数:
- security: 标的代码
- value: 目标价值（元）

### cancel_order
撤单

```python
cancel_order(order_or_id, account=None)
```

### get_open_orders
获取未完成订单

```python
get_open_orders(account=None)
```

## 账户与持仓

### get_portfolio
获取账户信息

```python
get_portfolio(account=None)
```

Portfolio对象属性:
- cash: 可用资金
- total_value: 总资产
- positions_value: 持仓市值
- returns: 策略收益
- starting_cash: 初始资金

### get_positions
获取持仓信息

```python
get_positions(account=None)
```

返回一个字典，key是股票代码，value是Position对象。

Position对象属性:
- security: 股票代码
- amount: 持仓数量
- closeable_amount: 可卖出数量
- avg_cost: 持仓成本
- price: 最新价格
- value: 持仓市值
- profit: 浮动盈亏

### get_orders
获取订单历史

```python
get_orders(account=None)
```

### get_trades
获取成交记录

```python
get_trades(account=None)
```

## 技术指标

### MA
移动平均线

```python
MA(data, n)
```

### EMA
指数移动平均线

```python
EMA(data, n)
```

### MACD
异同移动平均线

```python
MACD(data, fast_period=12, slow_period=26, signal_period=9)
```

### RSI
相对强弱指标

```python
RSI(data, n=14)
```

### KDJ
随机指标

```python
KDJ(data, n=9, m1=3, m2=3)
```

### BOLL
布林带

```python
BOLL(data, n=20, k=2)
```

## 金融数据

### valuation
估值数据
- market_cap: 总市值
- circulating_market_cap: 流通市值
- pe_ratio: 市盈率
- pb_ratio: 市净率
- ps_ratio: 市销率
- pcf_ratio: 市现率

### income
利润表数据
- net_profit: 净利润
- operating_revenue: 营业收入
- total_operating_revenue: 营业总收入

### balance
资产负债表数据
- total_assets: 资产总计
- total_liabilities: 负债合计
- total_equity: 股东权益合计

### cash_flow
现金流量表数据
- net_operate_cash_flow: 经营活动现金流量净额
- net_invest_cash_flow: 投资活动现金流量净额
- net_finance_cash_flow: 筹资活动现金流量净额

## 宏观经济数据

### 宏观经济指标查询
```python
from jqdata import macro
macro.run_query(query_object)
```

## 系统函数

### log
日志记录

```python
log.info(message)
log.warn(message)
log.error(message)
```

### record
记录数据

```python
record(**kwargs)
```

### plot
绘图

```python
plot(key, value)
```

### set_benchmark
设置基准

```python
set_benchmark(security)
```

### set_option
设置选项

```python
set_option(key, value)
```

常用选项:
- use_real_price: 使用真实价格
- max_history_window: 最大历史数据窗口

## 风险控制

### set_slippage
设置滑点

```python
set_slippage(slippage)
```

### set_commission
设置手续费

```python
set_commission(cost, type, ref=None)
```

### set_price_limit
设置涨跌停限制

```python
set_price_limit(limit)
```

## 回测参数

### 回测起止时间
在聚宽平台界面设置

### 初始资金
在聚宽平台界面设置

### 手续费设置
使用set_commission函数

### 滑点设置
使用set_slippage函数

### 涨跌停处理
使用set_price_limit函数

## 实盘交易

### 实盘账户连接
在聚宽平台配置

### 实盘交易接口
与回测接口基本一致

### 实盘数据获取
与回测数据获取一致

### 实盘风险控制
与回测风险控制一致

## 使用示例

### 简单策略示例

```python
# 导入聚宽函数库
import jqdata

# 初始化函数，设定要操作的股票基准等
def initialize(context):
    # 定义一个全局变量，保存要操作的股票
    g.security = '000001.XSHE'
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 运行函数
    run_daily(market_open, time='every_bar')

# 每个单位时间(如果按天回测，则每天调用一次，如果按分钟，则每分钟调用一次)调用一次
def market_open(context):
    security = g.security
    # 获取股票的收盘价
    close_data = attribute_history(security, 5, '1d', ['close'])
    # 取得过去五天的平均价格
    MA5 = close_data['close'].mean()
    # 取得上一时间点价格
    current_price = close_data['close'][-1]
    # 取得当前的现金
    cash = context.portfolio.cash
    
    # 如果上一时间点价格高出五天平均价1%，则全仓买入
    if current_price > 1.01*MA5:
        # 用所有cash买入股票
        order_value(security, cash)
        # 记录这次买入
        log.info("Buying %s" % (security))
    # 如果上一时间点价格低于五天平均价，则空仓卖出
    elif current_price < MA5 and context.portfolio.positions[security].closeable_amount > 0:
        # 卖出所有股票，使这只股票的最终持有量为0
        order_target(security, 0)
        # 记录这次卖出
        log.info("Selling %s" % (security))
    # 画出上一时间点价格
    record(stock_price=current_price)
```

### 实用策略示例

```python
# 导入聚宽函数库
import jqdata

# 初始化函数，设定基准等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 设置佣金和滑点
    set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013, min_cost=5))
    set_slippage(PriceRelatedSlippage(0.002))
    
    # 运行函数
    run_daily(trade_before_open, time='before_open')
    run_daily(trade_at_open, time='open')
    run_daily(trade_during_day, time='14:30')

def trade_before_open(context):
    """开盘前处理"""
    # 获取要交易的股票池
    g.stocks = get_index_stocks('000300.XSHG')
    log.info("今日股票池数量: %d" % len(g.stocks))

def trade_at_open(context):
    """开盘时处理"""
    # 策略逻辑
    pass

def trade_during_day(context):
    """盘中处理"""
    # 策略逻辑
    pass
```

## 注意事项

1. 聚宽API在回测环境和实盘环境中可能有差异
2. 部分API只能在回测环境中使用
3. 实盘交易需要正确配置账户信息
4. 注意交易时间和交易规则
5. 合理控制策略执行频率，避免过度交易
6. 开发策略时建议先在回测环境中验证，再进行实盘交易

## 完整文档下载

如需查看完整API文档，请下载官方PDF版本：
[JoinQuantAPI.pdf](https://cdn.joinquant.com/help/img/JoinQuantAPI.pdf)

## 使用说明

1. 本文档基于聚宽官方API文档整理
2. 如需查看完整API文档，请下载PDF版本
3. 聚宽API在回测环境和实盘环境中可能有差异
4. 部分API只能在回测环境中使用
5. 实盘交易需要正确配置账户信息