# EasyXT API 文档

## 概述

EasyXT是基于xtquant的二次开发封装库，旨在简化xtquant的使用，提供更友好的API接口。通过统一的接口设计、智能参数处理和完善的错误处理，让量化交易开发变得更加简单高效。

## 快速开始

### 安装和导入

```python
# 导入EasyXT
import easy_xt
from easy_xt.advanced_trade_api import AdvancedTradeAPI

# 获取基础API实例
api = easy_xt.get_api()

# 创建高级交易API实例
advanced_api = AdvancedTradeAPI()
```

### 基本初始化

```python
# 初始化数据服务
api.init_data()

# 初始化交易服务
userdata_path = r"C:\迅投极速交易终端 睿智融科版\userdata_mini"
api.init_trade(userdata_path, session_id='my_session')

# 添加交易账户
account_id = "你的资金账号"
api.add_account(account_id, 'STOCK')
```

---

## 核心模块

### 1. 基础API模块 (easy_xt.api)

#### 类: EasyXT

主要的API入口类，提供数据获取和基础交易功能。

##### 初始化方法

```python
class EasyXT:
    def __init__(self)
```

##### 连接方法

```python
def init_data(self) -> bool
```
**功能**: 初始化数据服务连接
**返回**: bool - 是否成功连接

```python
def init_trade(self, userdata_path: str, session_id: str = None) -> bool
```
**功能**: 初始化交易服务连接
**参数**:
- `userdata_path`: 迅投客户端userdata路径
- `session_id`: 会话ID，可选

**返回**: bool - 是否成功连接

```python
def add_account(self, account_id: str, account_type: str = 'STOCK') -> bool
```
**功能**: 添加交易账户
**参数**:
- `account_id`: 资金账号
- `account_type`: 账户类型，默认'STOCK'

**返回**: bool - 是否成功添加

##### 数据获取方法

```python
def get_price(self, 
              codes: Union[str, List[str]], 
              start: str = None, 
              end: str = None, 
              period: str = '1d',
              count: int = None,
              fields: List[str] = None,
              adjust: str = 'front') -> pd.DataFrame
```
**功能**: 获取股票价格数据
**参数**:
- `codes`: 股票代码，支持单个或多个
- `start`: 开始日期，支持多种格式
- `end`: 结束日期，支持多种格式
- `period`: 周期，支持'1d', '1m', '5m', '15m', '30m', '1h'
- `count`: 数据条数，如果指定则忽略start
- `fields`: 字段列表，默认['open', 'high', 'low', 'close', 'volume']
- `adjust`: 复权类型，'front'前复权, 'back'后复权, 'none'不复权

**返回**: DataFrame - 价格数据

**示例**:
```python
# 获取单只股票最近100天数据
data = api.get_price('000001.SZ', count=100)

# 获取多只股票指定时间段数据
data = api.get_price(['000001.SZ', '000002.SZ'], 
                     start='2023-01-01', 
                     end='2023-12-31')

# 获取分钟线数据
data = api.get_price('000001.SZ', period='5m', count=240)
```

```python
def get_current_price(self, codes: Union[str, List[str]]) -> pd.DataFrame
```
**功能**: 获取当前价格（实时行情）
**参数**:
- `codes`: 股票代码

**返回**: DataFrame - 实时价格数据

**示例**:
```python
# 获取实时价格
current = api.get_current_price(['000001.SZ', '000002.SZ'])
print(current[['code', 'price', 'change_pct']])
```

```python
def get_financial_data(self, 
                      codes: Union[str, List[str]], 
                      tables: List[str] = None,
                      start: str = None, 
                      end: str = None,
                      report_type: str = 'report_time') -> Dict[str, Dict[str, pd.DataFrame]]
```
**功能**: 获取财务数据
**参数**:
- `codes`: 股票代码
- `tables`: 财务表类型，如['Balance', 'Income', 'CashFlow']
- `start`: 开始时间
- `end`: 结束时间
- `report_type`: 'report_time'报告期, 'announce_time'公告期

**返回**: Dict - {股票代码: {表名: DataFrame}}

**示例**:
```python
# 获取财务数据
financial = api.get_financial_data(['000001.SZ'], 
                                   tables=['Balance', 'Income'],
                                   start='2023-01-01')
for stock, tables in financial.items():
    for table_name, df in tables.items():
        print(f"{stock} - {table_name}: {df.shape}")
```

```python
def get_stock_list(self, sector: str = None) -> List[str]
```
**功能**: 获取股票列表
**参数**:
- `sector`: 板块名称，如'沪深300', 'A股'等

**返回**: List[str] - 股票代码列表

```python
def get_trading_dates(self, 
                     market: str = 'SH', 
                     start: str = None, 
                     end: str = None,
                     count: int = -1) -> List[str]
```
**功能**: 获取交易日列表
**参数**:
- `market`: 市场代码，'SH'或'SZ'
- `start`: 开始日期
- `end`: 结束日期
- `count`: 数据条数

**返回**: List[str] - 交易日列表

##### 基础交易方法

```python
def buy(self, 
        account_id: str, 
        code: str, 
        volume: int, 
        price: float = 0, 
        price_type: str = 'market') -> Optional[int]
```
**功能**: 买入股票
**参数**:
- `account_id`: 资金账号
- `code`: 股票代码
- `volume`: 买入数量
- `price`: 买入价格，市价单时可为0
- `price_type`: 价格类型，'market'市价, 'limit'限价

**返回**: Optional[int] - 委托编号，失败返回None

```python
def sell(self, 
         account_id: str, 
         code: str, 
         volume: int, 
         price: float = 0, 
         price_type: str = 'market') -> Optional[int]
```
**功能**: 卖出股票
**参数**: 同buy方法
**返回**: Optional[int] - 委托编号，失败返回None

```python
def cancel_order(self, account_id: str, order_id: int) -> bool
```
**功能**: 撤销委托
**参数**:
- `account_id`: 资金账号
- `order_id`: 委托编号

**返回**: bool - 是否成功

```python
def get_account_asset(self, account_id: str) -> Optional[Dict[str, Any]]
```
**功能**: 获取账户资产
**返回**: Optional[Dict] - 资产信息

```python
def get_positions(self, account_id: str, code: str = None) -> pd.DataFrame
```
**功能**: 获取持仓信息
**返回**: DataFrame - 持仓信息

```python
def get_orders(self, account_id: str, cancelable_only: bool = False) -> pd.DataFrame
```
**功能**: 获取委托信息
**返回**: DataFrame - 委托信息

```python
def get_trades(self, account_id: str) -> pd.DataFrame
```
**功能**: 获取成交信息
**返回**: DataFrame - 成交信息

##### 便捷方法

```python
def quick_buy(self, account_id: str, code: str, amount: float, price_type: str = 'market') -> Optional[int]
```
**功能**: 按金额买入股票
**参数**:
- `amount`: 买入金额

**示例**:
```python
# 用1万元买入平安银行
order_id = api.quick_buy(account_id, '000001.SZ', 10000)
```

---

### 2. 高级交易API模块 (easy_xt.advanced_trade_api)

#### 类: AdvancedTradeAPI

提供完整的高级交易功能，包括异步交易、批量操作、风险管理和策略支持。

##### 初始化和连接

```python
class AdvancedTradeAPI:
    def __init__(self)
```

```python
def connect(self, userdata_path: str, session_id: str = None) -> bool
```
**功能**: 连接高级交易服务
**参数**:
- `userdata_path`: 迅投客户端路径
- `session_id`: 会话ID

**返回**: bool - 是否连接成功

```python
def add_account(self, account_id: str, account_type: str = 'STOCK') -> bool
```
**功能**: 添加交易账户

```python
def set_callbacks(self, order_callback=None, trade_callback=None, error_callback=None)
```
**功能**: 设置回调函数
**参数**:
- `order_callback`: 委托回调函数
- `trade_callback`: 成交回调函数
- `error_callback`: 错误回调函数

**示例**:
```python
def my_order_callback(order):
    print(f"委托回调: {order.stock_code} {order.order_volume}股")

def my_trade_callback(trade):
    print(f"成交回调: {trade.stock_code} {trade.traded_volume}股")

advanced_api.set_callbacks(
    order_callback=my_order_callback,
    trade_callback=my_trade_callback
)
```

##### 交易执行方法

```python
def sync_order(self, account_id: str, code: str, order_type: str, volume: int, 
               price: float = 0, price_type: str = 'market', 
               strategy_name: str = 'EasyXT', order_remark: str = '') -> Optional[int]
```
**功能**: 同步下单
**参数**:
- `order_type`: 委托类型，'buy'买入, 'sell'卖出
- `strategy_name`: 策略名称
- `order_remark`: 委托备注

**返回**: Optional[int] - 委托编号

**示例**:
```python
# 同步下单
order_id = advanced_api.sync_order(
    account_id=account_id,
    code='000001.SZ',
    order_type='buy',
    volume=100,
    price=10.5,
    price_type='limit',
    strategy_name='我的策略',
    order_remark='测试买入'
)
```

```python
def async_order(self, account_id: str, code: str, order_type: str, volume: int,
                price: float = 0, price_type: str = 'market',
                strategy_name: str = 'EasyXT', order_remark: str = '') -> Optional[int]
```
**功能**: 异步下单
**返回**: Optional[int] - 下单请求序号

```python
def batch_order(self, account_id: str, orders: List[Dict[str, Any]]) -> List[Optional[int]]
```
**功能**: 批量下单
**参数**:
- `orders`: 订单列表

**示例**:
```python
# 批量下单
batch_orders = [
    {
        'code': '000001.SZ',
        'order_type': 'buy',
        'volume': 100,
        'price': 10.0,
        'price_type': 'limit'
    },
    {
        'code': '000002.SZ',
        'order_type': 'buy', 
        'volume': 200,
        'price': 8.0,
        'price_type': 'limit'
    }
]
results = advanced_api.batch_order(account_id, batch_orders)
```

```python
def condition_order(self, account_id: str, code: str, condition_type: str,
                   trigger_price: float, order_type: str, volume: int,
                   target_price: float = 0) -> bool
```
**功能**: 条件单（止损单、止盈单）
**参数**:
- `condition_type`: 条件类型，'stop_loss'止损, 'take_profit'止盈
- `trigger_price`: 触发价格
- `target_price`: 目标价格

**示例**:
```python
# 设置止损单
result = advanced_api.condition_order(
    account_id=account_id,
    code='000001.SZ',
    condition_type='stop_loss',
    trigger_price=9.5,  # 跌破9.5触发
    order_type='sell',
    volume=100,
    target_price=9.4  # 以9.4价格卖出
)
```

##### 撤单方法

```python
def sync_cancel_order(self, account_id: str, order_id: int) -> bool
```
**功能**: 同步撤单

```python
def async_cancel_order(self, account_id: str, order_id: int) -> Optional[int]
```
**功能**: 异步撤单

```python
def batch_cancel_orders(self, account_id: str, order_ids: List[int]) -> List[bool]
```
**功能**: 批量撤单

##### 数据查询方法

```python
def get_account_asset_detailed(self, account_id: str) -> Optional[Dict[str, Any]]
```
**功能**: 获取详细账户资产信息
**返回**: Dict - 包含以下字段的资产信息
- `cash`: 可用资金
- `frozen_cash`: 冻结资金
- `market_value`: 持仓市值
- `total_asset`: 总资产
- `profit_loss`: 浮动盈亏

**示例**:
```python
asset = advanced_api.get_account_asset_detailed(account_id)
print(f"总资产: {asset['total_asset']}")
print(f"可用资金: {asset['cash']}")
print(f"浮动盈亏: {asset['profit_loss']}")
```

```python
def get_positions_detailed(self, account_id: str, code: str = None) -> pd.DataFrame
```
**功能**: 获取详细持仓信息
**返回**: DataFrame - 包含盈亏计算的持仓信息

**示例**:
```python
# 获取所有持仓
positions = advanced_api.get_positions_detailed(account_id)
print(positions[['code', 'volume', 'open_price', 'current_price', 'profit_loss']])

# 获取单只股票持仓
single_pos = advanced_api.get_positions_detailed(account_id, '000001.SZ')
```

```python
def get_today_orders(self, account_id: str, cancelable_only: bool = False) -> pd.DataFrame
```
**功能**: 获取当日委托

```python
def get_today_trades(self, account_id: str) -> pd.DataFrame
```
**功能**: 获取当日成交

```python
def get_history_orders(self, account_id: str, start_date: str = None, end_date: str = None) -> pd.DataFrame
```
**功能**: 获取历史委托

```python
def get_history_trades(self, account_id: str, start_date: str = None, end_date: str = None) -> pd.DataFrame
```
**功能**: 获取历史成交

```python
def get_history_positions(self, account_id: str, date: str = None) -> pd.DataFrame
```
**功能**: 获取历史持仓

##### 数据获取方法

```python
def subscribe_realtime_data(self, codes: Union[str, List[str]], 
                           period: str = 'tick', callback: Callable = None) -> bool
```
**功能**: 订阅实时行情数据
**参数**:
- `period`: 周期，'tick', '1m', '5m', '1d'等
- `callback`: 数据回调函数

**示例**:
```python
def quote_callback(data):
    print(f"实时行情: {data}")

result = advanced_api.subscribe_realtime_data(
    codes=['000001.SZ', '000002.SZ'],
    period='tick',
    callback=quote_callback
)
```

```python
def subscribe_whole_market(self, markets: List[str] = ['SH', 'SZ'], 
                          callback: Callable = None) -> bool
```
**功能**: 订阅全市场行情

```python
def download_history_data(self, codes: Union[str, List[str]], 
                         period: str = '1d', start: str = None, end: str = None) -> bool
```
**功能**: 下载历史数据

```python
def get_local_data(self, codes: Union[str, List[str]], period: str = '1d',
                  start: str = None, end: str = None, count: int = -1) -> pd.DataFrame
```
**功能**: 读取本地历史数据

##### 风险管理方法

```python
def set_risk_params(self, max_position_ratio: float = None, 
                   max_single_order_amount: float = None,
                   slippage: float = None) -> None
```
**功能**: 设置风险参数
**参数**:
- `max_position_ratio`: 最大持仓比例
- `max_single_order_amount`: 单笔最大交易金额
- `slippage`: 滑点设置

**示例**:
```python
# 设置风险参数
advanced_api.set_risk_params(
    max_position_ratio=0.3,  # 最大持仓30%
    max_single_order_amount=50000,  # 单笔最大5万
    slippage=0.002  # 滑点0.2%
)
```

```python
def check_trading_time(self) -> bool
```
**功能**: 检查交易时间

```python
def validate_order(self, account_id: str, order_amount: float) -> Dict[str, Any]
```
**功能**: 验证订单
**返回**: Dict - 包含验证结果和失败原因

**示例**:
```python
validation = advanced_api.validate_order(account_id, 60000)
if not validation['valid']:
    print(f"订单验证失败: {validation['reasons']}")
```

##### 策略支持方法

```python
def moving_average_signal(self, code: str, short_period: int = 5, 
                         long_period: int = 20) -> str
```
**功能**: 均线信号
**返回**: str - 'buy', 'sell', 'hold'

**示例**:
```python
signal = advanced_api.moving_average_signal('000001.SZ', 5, 20)
if signal == 'buy':
    order_id = advanced_api.sync_order(account_id, '000001.SZ', 'buy', 100)
```

```python
def percentage_order(self, account_id: str, code: str, percentage: float, 
                    order_type: str) -> Optional[int]
```
**功能**: 百分比交易
**参数**:
- `percentage`: 百分比，0-1之间
- `order_type`: 'buy'按资金比例, 'sell'按持仓比例

**示例**:
```python
# 用30%的资金买入
order_id = advanced_api.percentage_order(account_id, '000001.SZ', 0.3, 'buy')

# 卖出50%的持仓
order_id = advanced_api.percentage_order(account_id, '000001.SZ', 0.5, 'sell')
```

```python
def target_value_order(self, account_id: str, code: str, target_value: float) -> Optional[int]
```
**功能**: 目标价值下单
**参数**:
- `target_value`: 目标持仓价值

**示例**:
```python
# 调整持仓到2万元
order_id = advanced_api.target_value_order(account_id, '000001.SZ', 20000)
```

```python
def target_quantity_order(self, account_id: str, code: str, target_quantity: int) -> Optional[int]
```
**功能**: 目标数量下单
**参数**:
- `target_quantity`: 目标持仓数量

**示例**:
```python
# 调整持仓到1000股
order_id = advanced_api.target_quantity_order(account_id, '000001.SZ', 1000)
```

##### 其他功能方法

```python
def get_trading_calendar(self, market: str = 'SH', start: str = None, end: str = None) -> List[str]
```
**功能**: 获取交易日历

```python
def get_financial_data(self, codes: Union[str, List[str]], tables: List[str] = None,
                      start: str = None, end: str = None, report_type: str = 'report_time') -> Dict
```
**功能**: 获取财务数据

```python
def get_instrument_info(self, code: str) -> Optional[Dict[str, Any]]
```
**功能**: 获取合约信息

```python
def timestamp_to_datetime(self, timestamp: int, format_str: str = '%Y-%m-%d %H:%M:%S') -> str
```
**功能**: 时间戳转换

---

### 3. 工具模块 (easy_xt.utils)

#### 类: StockCodeUtils

股票代码处理工具类。

```python
@staticmethod
def normalize_code(code: str) -> str
```
**功能**: 标准化股票代码
**示例**:
```python
from easy_xt.utils import StockCodeUtils

# 各种格式都能正确处理
code1 = StockCodeUtils.normalize_code('000001')      # -> '000001.SZ'
code2 = StockCodeUtils.normalize_code('SH600000')    # -> '600000.SH'
code3 = StockCodeUtils.normalize_code('000001.SZ')   # -> '000001.SZ'
```

```python
@staticmethod
def normalize_codes(codes: Union[str, List[str]]) -> List[str]
```
**功能**: 批量标准化股票代码

```python
@staticmethod
def get_market(code: str) -> str
```
**功能**: 获取股票所属市场

```python
@staticmethod
def is_valid_code(code: str) -> bool
```
**功能**: 验证股票代码是否有效

#### 类: TimeUtils

时间处理工具类。

```python
@staticmethod
def normalize_date(date_str: str) -> str
```
**功能**: 标准化日期格式
**示例**:
```python
from easy_xt.utils import TimeUtils

# 各种日期格式都能处理
date1 = TimeUtils.normalize_date('2023-01-01')   # -> '20230101'
date2 = TimeUtils.normalize_date('2023/1/1')     # -> '20230101'
date3 = TimeUtils.normalize_date('20230101')     # -> '20230101'
```

```python
@staticmethod
def get_trading_days(start: str, end: str, market: str = 'SH') -> List[str]
```
**功能**: 获取交易日列表

```python
@staticmethod
def is_trading_day(date: str, market: str = 'SH') -> bool
```
**功能**: 判断是否为交易日

#### 类: ErrorHandler

错误处理工具类。

```python
@staticmethod
def handle_api_error(func)
```
**功能**: API错误处理装饰器

```python
@staticmethod
def log_error(message: str, level: str = 'ERROR')
```
**功能**: 记录错误日志

---

### 4. 配置模块 (easy_xt.config)

#### 类: Config

配置管理类。

```python
def get(self, key: str, default: Any = None) -> Any
```
**功能**: 获取配置值
**示例**:
```python
from easy_xt.config import config

# 获取配置
timeout = config.get('data.timeout', 30)
debug = config.get('common.debug', False)
```

```python
def set(self, key: str, value: Any) -> None
```
**功能**: 设置配置值

```python
def update(self, config_dict: Dict[str, Any]) -> None
```
**功能**: 批量更新配置

---

## 完整使用示例

### 基础数据获取示例

```python
import easy_xt
import pandas as pd

# 初始化
api = easy_xt.get_api()
api.init_data()

# 获取股票价格数据
data = api.get_price('000001.SZ', count=100)
print(data.head())

# 获取实时价格
current = api.get_current_price(['000001.SZ', '000002.SZ'])
print(current)

# 获取财务数据
financial = api.get_financial_data(['000001.SZ'], 
                                   tables=['Balance', 'Income'])
```

### 基础交易示例

```python
# 初始化交易
userdata_path = r"C:\迅投极速交易终端 睿智融科版\userdata_mini"
api.init_trade(userdata_path)

account_id = "你的资金账号"
api.add_account(account_id)

# 买入股票
order_id = api.buy(account_id, '000001.SZ', 100, 10.5, 'limit')
print(f"买入委托号: {order_id}")

# 查询持仓
positions = api.get_positions(account_id)
print(positions)

# 卖出股票
order_id = api.sell(account_id, '000001.SZ', 100, 11.0, 'limit')

# 撤销委托
result = api.cancel_order(account_id, order_id)
```

### 高级交易示例

```python
from easy_xt.advanced_trade_api import AdvancedTradeAPI

# 初始化高级API
advanced_api = AdvancedTradeAPI()
advanced_api.connect(userdata_path, 'advanced_session')
advanced_api.add_account(account_id)

# 设置回调
def order_callback(order):
    print(f"委托回调: {order.stock_code} {order.order_volume}股")

advanced_api.set_callbacks(order_callback=order_callback)

# 设置风险参数
advanced_api.set_risk_params(
    max_position_ratio=0.3,
    max_single_order_amount=50000,
    slippage=0.002
)

# 批量下单
batch_orders = [
    {'code': '000001.SZ', 'order_type': 'buy', 'volume': 100, 'price': 10.0},
    {'code': '000002.SZ', 'order_type': 'buy', 'volume': 200, 'price': 8.0}
]
results = advanced_api.batch_order(account_id, batch_orders)

# 策略交易
signal = advanced_api.moving_average_signal('000001.SZ', 5, 20)
if signal == 'buy':
    order_id = advanced_api.percentage_order(account_id, '000001.SZ', 0.3, 'buy')

# 目标价值调仓
order_id = advanced_api.target_value_order(account_id, '000001.SZ', 20000)
```

### 数据订阅示例

```python
# 订阅实时行情
def quote_callback(data):
    print(f"实时行情: {data}")

advanced_api.subscribe_realtime_data(
    codes=['000001.SZ', '000002.SZ'],
    period='tick',
    callback=quote_callback
)

# 下载历史数据
advanced_api.download_history_data(
    codes=['000001.SZ'],
    period='1d',
    start='20230101',
    end='20231231'
)

# 读取本地数据
local_data = advanced_api.get_local_data(
    codes=['000001.SZ'],
    period='1d',
    count=100
)
```

---

## 错误处理

### 常见错误类型

1. **连接错误**: 客户端未启动或路径错误
2. **账户错误**: 账户未添加或账户类型错误
3. **参数错误**: 股票代码格式错误或参数无效
4. **权限错误**: 账户权限不足或功能未开通
5. **网络错误**: 网络连接问题或服务器异常
6. **风险控制**: 触发风险控制规则

### 错误处理示例

```python
try:
    # 执行交易操作
    order_id = api.buy(account_id, '000001.SZ', 100, 10.5)
    if order_id:
        print(f"下单成功: {order_id}")
    else:
        print("下单失败")
except Exception as e:
    print(f"发生异常: {str(e)}")

# 使用验证功能
validation = advanced_api.validate_order(account_id, 50000)
if validation['valid']:
    # 执行交易
    order_id = advanced_api.sync_order(account_id, '000001.SZ', 'buy', 100)
else:
    print(f"订单验证失败: {validation['reasons']}")
```

---

## 最佳实践

### 1. 初始化顺序

```python
# 推荐的初始化顺序
import easy_xt
from easy_xt.advanced_trade_api import AdvancedTradeAPI

# 1. 基础API初始化（用于数据获取）
api = easy_xt.get_api()
api.init_data()

# 2. 高级API初始化（用于交易）
advanced_api = AdvancedTradeAPI()
advanced_api.connect(userdata_path, session_id)
advanced_api.add_account(account_id)

# 3. 设置回调和风险参数
advanced_api.set_callbacks(order_callback=my_order_callback)
advanced_api.set_risk_params(max_position_ratio=0.3, slippage=0.002)
```

### 2. 数据获取最佳实践

```python
# 批量获取数据
codes = ['000001.SZ', '000002.SZ', '600000.SH']

# 一次性获取多只股票数据
data = api.get_price(codes, count=100)

# 获取实时价格
current_prices = api.get_current_price(codes)

# 下载历史数据到本地
api.download_data(codes, period='1d', start='20230101')

# 从本地读取数据（更快）
local_data = advanced_api.get_local_data(codes, period='1d', count=100)
```

### 3. 交易最佳实践

```python
# 交易前检查
def safe_trade(account_id, code, order_type, volume, price=0):
    # 1. 检查交易时间
    if not advanced_api.check_trading_time():
        print("非交易时间")
        return None
    
    # 2. 验证订单
    order_amount = volume * price if price > 0 else volume * 10  # 估算金额
    validation = advanced_api.validate_order(account_id, order_amount)
    if not validation['valid']:
        print(f"订单验证失败: {validation['reasons']}")
        return None
    
    # 3. 执行交易
    order_id = advanced_api.sync_order(
        account_id=account_id,
        code=code,
        order_type=order_type,
        volume=volume,
        price=price,
        price_type='limit' if price > 0 else 'market'
    )
    
    return order_id

# 使用示例
order_id = safe_trade(account_id, '000001.SZ', 'buy', 100, 10.5)
```

### 4. 策略开发最佳实践

```python
def simple_ma_strategy(account_id, code, short_period=5, long_period=20):
    """简单均线策略示例"""
    
    # 1. 获取信号
    signal = advanced_api.moving_average_signal(code, short_period, long_period)
    
    # 2. 获取当前持仓
    positions = advanced_api.get_positions_detailed(account_id, code)
    current_volume = positions['volume'].sum() if not positions.empty else 0
    
    # 3. 根据信号执行交易
    if signal == 'buy' and current_volume == 0:
        # 买入信号且无持仓
        order_id = advanced_api.percentage_order(account_id, code, 0.2, 'buy')
        print(f"买入信号，下单: {order_id}")
        
    elif signal == 'sell' and current_volume > 0:
        # 卖出信号且有持仓
        order_id = advanced_api.percentage_order(account_id, code, 1.0, 'sell')
        print(f"卖出信号，下单: {order_id}")
        
    else:
        print(f"持有信号，当前持仓: {current_volume}")

# 策略运行
simple_ma_strategy(account_id, '000001.SZ')
```

### 5. 批量操作最佳实践

```python
def batch_rebalance(account_id, target_portfolio):
    """批量调仓示例"""
    
    results = []
    
    for code, target_value in target_portfolio.items():
        try:
            # 调整到目标价值
            order_id = advanced_api.target_value_order(account_id, code, target_value)
            results.append({
                'code': code,
                'target_value': target_value,
                'order_id': order_id,
                'success': order_id is not None
            })
            
            # 控制下单频率
            time.sleep(0.1)
            
        except Exception as e:
            results.append({
                'code': code,
                'target_value': target_value,
                'order_id': None,
                'success': False,
                'error': str(e)
            })
    
    return results

# 使用示例
target_portfolio = {
    '000001.SZ': 20000,  # 平安银行目标2万
    '000002.SZ': 15000,  # 万科A目标1.5万
    '600000.SH': 25000   # 浦发银行目标2.5万
}

results = batch_rebalance(account_id, target_portfolio)
for result in results:
    print(f"{result['code']}: {'成功' if result['success'] else '失败'}")
```

---

## 性能优化

### 1. 数据获取优化

```python
# 优先使用本地数据
def get_optimized_data(codes, period='1d', count=100):
    # 先尝试本地数据
    local_data = advanced_api.get_local_data(codes, period, count=count)
    
    if local_data.empty:
        # 本地无数据，下载后再读取
        advanced_api.download_history_data(codes, period)
        local_data = advanced_api.get_local_data(codes, period, count=count)
    
    return local_data

# 批量获取多只股票数据
data = get_optimized_data(['000001.SZ', '000002.SZ'], count=100)
```

### 2. 交易性能优化

```python
# 使用异步下单提高性能
def async_batch_order(account_id, orders):
    """异步批量下单"""
    
    sequences = []
    for order in orders:
        seq = advanced_api.async_order(
            account_id=account_id,
            code=order['code'],
            order_type=order['order_type'],
            volume=order['volume'],
            price=order.get('price', 0),
            price_type=order.get('price_type', 'market')
        )
        sequences.append(seq)
    
    return sequences

# 使用异步下单
batch_orders = [
    {'code': '000001.SZ', 'order_type': 'buy', 'volume': 100},
    {'code': '000002.SZ', 'order_type': 'buy', 'volume': 200}
]
sequences = async_batch_order(account_id, batch_orders)
```

### 3. 内存优化

```python
# 分批处理大量数据
def process_large_stock_list(stock_list, batch_size=50):
    """分批处理大量股票"""
    
    results = []
    for i in range(0, len(stock_list), batch_size):
        batch = stock_list[i:i + batch_size]
        
        # 处理当前批次
        batch_data = api.get_current_price(batch)
        results.append(batch_data)
        
        # 释放内存
        del batch_data
    
    # 合并结果
    final_result = pd.concat(results, ignore_index=True)
    return final_result
```

---

## 常见问题解答

### Q1: 如何处理连接失败？

```python
def robust_connect(userdata_path, max_retries=3):
    """健壮的连接方法"""
    
    for attempt in range(max_retries):
        try:
            advanced_api = AdvancedTradeAPI()
            if advanced_api.connect(userdata_path):
                print(f"连接成功，尝试次数: {attempt + 1}")
                return advanced_api
            else:
                print(f"连接失败，尝试次数: {attempt + 1}")
                time.sleep(2)  # 等待2秒后重试
        except Exception as e:
            print(f"连接异常: {str(e)}")
            time.sleep(2)
    
    print("连接失败，请检查客户端是否启动")
    return None
```

### Q2: 如何处理股票代码格式问题？

```python
from easy_xt.utils import StockCodeUtils

# 自动处理各种格式
codes = ['000001', 'SH600000', '000002.SZ', '600000.SH']
normalized_codes = [StockCodeUtils.normalize_code(code) for code in codes]
print(normalized_codes)  # ['000001.SZ', '600000.SH', '000002.SZ', '600000.SH']

# 验证代码有效性
for code in codes:
    if StockCodeUtils.is_valid_code(code):
        print(f"{code} 是有效的股票代码")
```

### Q3: 如何设置合理的风险参数？

```python
# 根据账户资金设置风险参数
def setup_risk_params(account_id):
    asset = advanced_api.get_account_asset_detailed(account_id)
    if asset:
        total_asset = asset['total_asset']
        
        # 根据资金规模设置参数
        if total_asset < 100000:  # 10万以下
            max_position_ratio = 0.2  # 最大持仓20%
            max_single_order = 10000  # 单笔最大1万
        elif total_asset < 500000:  # 50万以下
            max_position_ratio = 0.3  # 最大持仓30%
            max_single_order = 50000  # 单笔最大5万
        else:  # 50万以上
            max_position_ratio = 0.4  # 最大持仓40%
            max_single_order = 100000  # 单笔最大10万
        
        advanced_api.set_risk_params(
            max_position_ratio=max_position_ratio,
            max_single_order_amount=max_single_order,
            slippage=0.002  # 滑点0.2%
        )
        
        print(f"风险参数设置完成: 最大持仓比例{max_position_ratio}, 单笔最大{max_single_order}")

# 使用示例
setup_risk_params(account_id)
```

### Q4: 如何监控交易状态？

```python
def monitor_orders(account_id, check_interval=5):
    """监控委托状态"""
    
    while True:
        try:
            # 获取当日委托
            orders = advanced_api.get_today_orders(account_id)
            
            # 筛选未完成委托
            pending_orders = orders[orders['order_status'].isin(['未报', '已报', '部成'])]
            
            if not pending_orders.empty:
                print(f"未完成委托数量: {len(pending_orders)}")
                for _, order in pending_orders.iterrows():
                    print(f"  {order['stock_code']} {order['order_type']} "
                          f"{order['order_volume']}股 状态:{order['order_status']}")
            else:
                print("所有委托已完成")
                break
            
            time.sleep(check_interval)
            
        except KeyboardInterrupt:
            print("监控已停止")
            break
        except Exception as e:
            print(f"监控异常: {str(e)}")
            time.sleep(check_interval)

# 启动监控
monitor_orders(account_id)
```

---

## 版本信息

- **当前版本**: 1.0.0
- **兼容的xtquant版本**: 1.1.9及以上
- **Python版本要求**: 3.6及以上
- **依赖库**: pandas, numpy, datetime

---

## 技术支持

如果在使用过程中遇到问题，请检查：

1. **环境检查**
   - 迅投极速交易客户端是否正常启动并登录
   - Python环境是否正确安装pandas等依赖
   - xtquant模块是否正确安装

2. **配置检查**
   - userdata_path路径是否正确
   - 账户信息是否正确
   - 网络连接是否正常

3. **权限检查**
   - 账户是否有相应的交易权限
   - 是否开通了相关的交易功能

4. **日志检查**
   - 查看错误日志获取详细信息
   - 使用debug模式获取更多调试信息

---

这份API文档涵盖了EasyXT的所有功能和使用方法，通过详细的示例和最佳实践，帮助您快速掌握这个强大的量化交易工具。
