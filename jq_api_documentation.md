# 聚宽API文档

来源: [聚宽API文档](https://www.joinquant.com/help/api/help?name=api)

## 目录

### 策略编写基础
- 初始化函数 initialize
- 定时运行函数 run_monthly/run_weekly/run_daily
- 数据处理函数 handle_data
- 交易日前后处理 before_trading_start/after_trading_end

### 数据获取API
- get_price - 获取历史数据
- get_current_data - 获取当前行情
- get_fundamentals - 获取财务数据
- get_index_stocks - 获取指数成分股
- get_industry_stocks - 获取行业成分股
- get_concept_stocks - 获取概念板块成分股
- get_all_securities - 获取所有标的
- get_security_info - 获取单个标的信息
- get_billboard_list - 获取龙虎榜数据
- get_locked_shares - 获取限售解禁数据

### 交易API
- order - 基础下单函数
- order_value - 按价值下单
- order_target - 目标股数下单
- order_target_value - 目标价值下单
- cancel_order - 撤单
- get_open_orders - 获取未成交订单
- batch_order - 批量下单

### 账户与持仓
- get_portfolio - 获取账户信息
- get_positions - 获取持仓信息
- get_orders - 获取订单历史
- get_trades - 获取成交记录

### 技术指标
- MA - 移动平均线
- EMA - 指数移动平均线
- MACD - 异同移动平均线
- RSI - 相对强弱指标
- KDJ - 随机指标
- BOLL - 布林带
- 其他技术指标函数

### 金融数据
- valuation - 估值数据
- income - 利润表数据
- balance - 资产负债表数据
- cash_flow - 现金流量表数据
- indicator - 财务指标数据

### 宏观经济数据
- 宏观经济指标查询
- 行业经济数据
- 区域经济数据

### 系统函数
- log - 日志记录
- record - 记录数据
- plot - 绘图
- set_benchmark - 设置基准
- set_option - 设置选项
- get_environment - 获取环境信息

### 风险控制
- set_slippage - 设置滑点
- set_commission - 设置手续费
- set_price_limit - 设置涨跌停限制

### 回测参数
- 回测起止时间
- 初始资金
- 手续费设置
- 滑点设置
- 涨跌停处理

### 实盘交易
- 实盘账户连接
- 实盘交易接口
- 实盘数据获取
- 实盘风险控制

## 详细API说明

### 策略编写基础

#### initialize(context)
初始化函数，在整个回测模拟实盘中最初执行一次，用于初始化一些全局变量。

参数:
- context: Context对象，存放有当前的账户/股票持仓信息

返回: None

#### run_monthly/run_weekly/run_daily
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

#### handle_data(context, data)
该函数在每个单位时间会调用一次，用于处理数据和下单。

参数:
- context: Context对象，存放有当前的账户/标的持仓信息
- data: 一个字典，key是股票代码，value是当前的行情数据

#### before_trading_start(context)
该函数会在每天开始交易前被调用一次，可用于每日初始化。

#### after_trading_end(context)
该函数会在每天结束交易后被调用一次，可用于收盘后处理。

### 数据获取API

#### get_price
获取历史数据

```python
get_price(security, start_date=None, end_date=None, frequency='1d', fields=None, skip_paused=False, fq='pre', count=None)
```

参数:
- security: 标的代码
- start_date/end_date: 起止日期
- frequency: 数据频率
- fields: 获取字段
- skip_paused: 是否跳过停牌
- fq: 复权方式
- count: 数据数量

#### get_current_data
获取当前行情数据

```python
get_current_data()
```

#### get_fundamentals
获取财务数据

```python
get_fundamentals(query_object, date=None, statDate=None)
```

### 交易API

#### order
基础下单函数

```python
order(security, amount, style=None, price=None, account=None)
```

参数:
- security: 标的代码
- amount: 下单数量（股）
- style: 订单类型
- price: 价格
- account: 指定账户

#### order_value
按价值下单

```python
order_value(security, value, style=None, price=None, account=None)
```

参数:
- security: 标的代码
- value: 下单价值（元）
- style: 订单类型
- price: 价格
- account: 指定账户

#### order_target
目标股数下单

```python
order_target(security, amount, style=None, price=None, account=None)
```

参数:
- security: 标的代码
- amount: 目标股数
- style: 订单类型
- price: 价格
- account: 指定账户

#### order_target_value
目标价值下单

```python
order_target_value(security, value, style=None, price=None, account=None)
```

参数:
- security: 标的代码
- value: 目标价值（元）
- style: 订单类型
- price: 价格
- account: 指定账户

#### cancel_order
撤单

```python
cancel_order(order_or_id, account=None)
```

### 账户与持仓

#### get_portfolio
获取账户信息

```python
get_portfolio(account=None)
```

#### get_positions
获取持仓信息

```python
get_positions(account=None)
```

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