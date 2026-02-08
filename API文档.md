# EasyXT 完整API文档

## 概述

EasyXT是基于xtquant的二次开发封装库，提供以下核心功能：

1. **交易功能** - 基于xtquant的股票交易接口
2. **因子库** - EasyFactor：技术指标因子 + 基本面因子 + 财务因子
3. **数据管理** - DuckDB本地数据库（767万条记录）
4. **资金流向** - qstock集成（行业/概念/北向资金/个股资金流）
5. **龙虎榜数据** - 龙虎榜列表、个股历史、机构明细

---

## 快速开始

### 安装依赖

```bash
pip install pandas numpy duckdb qstock
```

### 基础初始化

```python
import easy_xt
from easy_xt.factor_library import create_easy_factor

# 1. 初始化基础API（用于交易）
api = easy_xt.get_api()
api.init_data()

# 2. 初始化EasyFactor（用于因子计算和数据管理）
DUCKDB_PATH = r'D:/StockData/stock_data.ddb'
ef = create_easy_factor(DUCKDB_PATH, enable_extended_modules=True)
```

---

## 模块一：EasyFactor 因子库

### 1.1 初始化

```python
from easy_xt.factor_library import create_easy_factor

# 创建EasyFactor实例
ef = create_easy_factor(
    duckdb_path=r'D:/StockData/stock_data.ddb',
    enable_extended_modules=True  # 启用扩展模块（qstock资金流向等）
)
```

### 1.2 技术指标因子

```python
# 计算单个因子
df = ef.calculate_factor('000001.SZ', 'MA', period=20)

# 计算多个因子
factors = ['MA_5', 'MA_20', 'RSI_14', 'MACD', 'KDJ']
df = ef.calculate_factors('000001.SZ', factors)

# 批量计算多只股票
stocks = ['000001.SZ', '000002.SZ', '600000.SH']
df = ef.calculate_batch_factors(stocks, factors)
```

**支持的因子类型**：
- 趋势类：MA、EMA、MACD、BOLL
- 动量类：RSI、KDJ、CCI、ROC
- 成交量类：VOL_MA、VOL_RATIO、OBV
- 波动率类：ATR、HV、STD

### 1.3 基本面因子（增强版）

```python
from easy_xt.fundamental_enhanced import get_enhanced_fundamental_factors

# 获取单只股票的所有基本面因子（29个因子）
df = get_enhanced_fundamental_factors('000001.SZ', ef.duckdb_reader)

# 批量获取
stocks = ['000001.SZ', '000002.SZ', '600000.SH']
df = get_enhanced_fundamental_factors(stocks, ef.duckdb_reader)
```

**29个基本面因子分类**：

**估值因子（3个）**
- `price_to_ma20/60` - 相对均线位置
- `price_percentile` - 价格历史分位数
- `dist_from_high_252` - 距离52周高点百分比

**动量因子（8个）**
- `momentum_1/5/10/20/60/120/252d` - 多周期动量
- `momentum_accel` - 动量加速度
- `rsi_14` - 相对强弱指数

**波动率因子（6个）**
- `volatility_20/60/120d` - 历史波动率
- `atr_14` - 平均真实波幅
- `volatility_percentile` - 波动率分位数

**质量因子（5个）**
- `price_cv_60d` - 价格变异系数
- `trend_strength_60d` - 趋势强度
- `consecutive_up/down_days` - 连续涨跌天数
- `price_position_52w` - 52周价格位置

**流动性因子（7个）**
- `avg_volume_5/20/60d` - 平均成交量
- `volume_ratio` - 成交量比率
- `turnover_5/20d` - 换手率

### 1.4 数据获取

```python
# 从DuckDB获取市场数据
df = ef.get_market_data(
    stock_list=['000001.SZ', '600000.SH'],
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# 获取最新数据
df = ef.get_market_data(
    stock_list=['000001.SZ'],
    count=100  # 最近100条
)
```

---

## 模块二：qstock 资金流向数据

### 2.1 同花顺行业/概念资金流向

```python
# 获取行业资金流向TOP20（90个行业）
industry_flow = ef.get_ths_industry_money_flow(top_n=20, use_cache=True)
print(industry_flow)

# 获取概念资金流向TOP20（387个概念）
concept_flow = ef.get_ths_concept_money_flow(top_n=20, use_cache=True)
print(concept_flow)

# 更新缓存
result = ef.update_ths_money_flow()
# 返回: {'industry': 90, 'concept': 387}
```

**数据字段**：
- 行业名称/板块名称
- 涨跌幅
- 净流入(万)
- 上涨家数/下跌家数
- 领涨股票

**智能缓存**：
- 首次运行：从qstock下载 → 保存到DuckDB
- 再次运行：直接从DuckDB读取（速度提升200-400倍）

### 2.2 北向资金流向

```python
# 获取北向资金历史流向（最近30天）
north_flow = ef.get_north_money_flow(days=30, use_cache=True)
print(north_flow)

# 获取北向资金行业流向（86个行业）
north_sector = ef.get_north_money_sector(top_n=20)
print(north_sector)

# 获取北向资金个股流向（2,767只股票）
north_stock = ef.get_north_money_stock(top_n=20)
print(north_stock)

# 查询特定股票的北向资金
north_single = ef.get_north_money_stock(stock_code='600050')
print(north_single)
```

**数据覆盖**：
- 历史流向：2,616条记录（2014-11-17 至 2026-02-06）
- 行业流向：86个行业
- 个股流向：2,767只股票

### 2.3 同花顺个股资金流向

```python
# 获取个股资金流向排名TOP20（5,175只股票）
stock_flow = ef.get_ths_stock_money_flow(top_n=20, use_cache=True)
print(stock_flow)

# 查询特定股票的资金流向
single_flow = ef.get_ths_stock_money_flow(stock_code='000001', use_cache=True)
print(single_flow)
```

**数据字段**：
- 代码、名称
- 最新价、涨跌幅
- 换手率
- 净流入(万)

---

## 模块三：DuckDB 数据管理

### 3.1 数据库连接

```python
from easy_xt.data_api import DuckDBDataReader

# 连接DuckDB数据库
reader = DuckDBDataReader('D:/StockData/stock_data.ddb')
```

### 3.2 数据统计

```python
# 查看数据库概况
print(reader.get_db_stats())

# 输出示例：
# 总记录数：7,675,290条
# 数据范围：2015-10-26 到 2026-02-02
# 覆盖股票：5,190只
# 数据库大小：2.5 GB
```

### 3.3 数据查询

```python
# 查询特定股票数据
df = reader.get_market_data(
    stock_list=['000001.SZ'],
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# 查询最新N条数据
df = reader.get_market_data(
    stock_list=['000001.SZ'],
    count=100
)
```

### 3.4 缓存表管理

```python
# 查看所有缓存表
tables = reader.get_all_tables()

# 查看特定表
import pandas as pd
df = reader.conn.execute("SELECT * FROM ths_industry_money_flow").fetchdf()
```

**缓存表列表**：
- `stock_daily` - 日线数据（767万条）
- `ths_industry_money_flow` - 行业资金流向（90行业）
- `ths_concept_money_flow` - 概念资金流向（387概念）
- `ths_stock_money_flow` - 个股资金流向（5,175股票）
- `north_money_flow` - 北向资金流向（2,616条）

---

## 模块四：龙虎榜数据

### 4.1 获取龙虎榜列表

```python
# 获取指定日期的龙虎榜
dt_list = ef.get_dragon_tiger_list(date='2024-01-15')
print(dt_list)
```

**数据字段**：
- 股票代码、股票名称
- 涨跌幅
- 龙虎榜 reason
- 上榜次数

### 4.2 获取个股龙虎榜历史

```python
# 获取个股龙虎榜历史
dt_history = ef.get_stock_dragon_tiger_history('000001.SZ')
print(dt_history)
```

### 4.3 获取机构明细

```python
# 获取机构交易明细
institution_detail = ef.get_institutional_detail('000001.SZ')
print(institution_detail)
```

---

## 模块五：交易API

### 5.1 基础交易

```python
# 初始化交易服务
userdata_path = r"C:\迅投极速交易终端 睿智融科版\userdata_mini"
api.init_trade(userdata_path, session_id='my_session')

# 添加账户
account_id = "你的资金账号"
api.add_account(account_id, 'STOCK')

# 买入股票
order_id = api.buy(account_id, '000001.SZ', volume=100, price=10.5, price_type='limit')

# 卖出股票
order_id = api.sell(account_id, '000001.SZ', volume=100, price=11.0, price_type='limit')

# 撤销委托
result = api.cancel_order(account_id, order_id)
```

### 5.2 查询账户信息

```python
# 查询账户资产
asset = api.get_account_asset(account_id)
print(asset)

# 查询持仓
positions = api.get_positions(account_id)
print(positions)

# 查询委托
orders = api.get_orders(account_id)
print(orders)

# 查询成交
trades = api.get_trades(account_id)
print(trades)
```

### 5.3 高级交易功能

```python
from easy_xt.advanced_trade_api import AdvancedTradeAPI

# 创建高级交易API
advanced_api = AdvancedTradeAPI()
advanced_api.connect(userdata_path)
advanced_api.add_account(account_id)

# 批量下单
batch_orders = [
    {'code': '000001.SZ', 'order_type': 'buy', 'volume': 100, 'price': 10.0},
    {'code': '000002.SZ', 'order_type': 'buy', 'volume': 200, 'price': 8.0}
]
results = advanced_api.batch_order(account_id, batch_orders)

# 设置风险参数
advanced_api.set_risk_params(
    max_position_ratio=0.3,  # 最大持仓30%
    max_single_order_amount=50000,  # 单笔最大5万
    slippage=0.002  # 滑点0.2%
)
```

---

## 完整使用示例

### 示例1：因子选股

```python
from easy_xt.factor_library import create_easy_factor
from easy_xt.fundamental_enhanced import get_batch_enhanced_factors

# 初始化
ef = create_easy_factor(r'D:/StockData/stock_data.ddb', enable_extended_modules=True)

# 获取股票池
stock_list = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '600519.SH']

# 获取基本面因子
df_factors = get_batch_enhanced_factors(stock_list, ef.duckdb_reader)

# 多因子筛选
df_selected = df_factors[
    (df_factors['momentum_20d'] > 0) &  # 20日动量>0
    (df_factors['momentum_60d'] > 0) &  # 60日动量>0
    (df_factors['rsi_14'] < 70) &       # RSI<70（不超买）
    (df_factors['volatility_20d'] < 0.3)  # 波动率<0.3（风险适中）
]

print("符合条件的股票：")
print(df_selected)
```

### 示例2：资金流向选股

```python
# 1. 获取资金流入TOP20
stock_flow = ef.get_ths_stock_money_flow(top_n=20, use_cache=True)

# 2. 获取这些股票的基本面因子
stock_list = stock_flow['股票代码'].tolist()
df_factors = get_batch_enhanced_factors(stock_list, ef.duckdb_reader)

# 3. 多因子筛选
df_selected = df_factors[
    (df_factors['momentum_20d'] > 0) &
    (df_factors['rsi_14'] < 70) &
    (df_factors['volatility_20d'] < 0.3)
]

print("资金流入且技术面良好的股票：")
print(df_selected)
```

### 示例3：板块轮动策略

```python
# 1. 获取行业资金流向
industry_flow = ef.get_ths_industry_money_flow(top_n=10, use_cache=True)

# 2. 筛选资金流入>1亿元的行业
hot_industries = industry_flow[industry_flow['净流入(万)'] > 10000]

# 3. 获取热门行业的成分股
for _, row in hot_industries.iterrows():
    industry_name = row['行业名称']
    print(f"\n热门行业：{industry_name}，净流入：{row['净流入(万)']}万")
```

### 示例4：北向资金策略

```python
# 1. 获取北向资金连续增持的股票
north_stocks = ef.get_north_money_stock(top_n=50)

# 2. 获取这些股票的基本面因子
stock_list = north_stocks['代码'].tolist()
df_factors = get_batch_enhanced_factors(stock_list, ef.duckdb_reader)

# 3. 筛选条件：外资增持 + 动量向上
df_selected = df_factors[
    (df_factors['momentum_20d'] > 0) &
    (df_factors['trend_strength_60d'] > 0)
]

print("北向资金增持且趋势向上的股票：")
print(df_selected[['code', 'momentum_20d', 'trend_strength_60d']])
```

---

## API参考速查表

### EasyFactor 因子库

| 功能 | 方法 | 说明 |
|-----|------|------|
| 计算因子 | `ef.calculate_factor(code, name, period)` | 计算单个技术指标 |
| 批量计算因子 | `ef.calculate_factors(code, factors)` | 计算多个技术指标 |
| 批量股票因子 | `ef.calculate_batch_factors(stocks, factors)` | 批量计算多股票 |
| 市场数据 | `ef.get_market_data(stocks, start, end)` | 获取行情数据 |
| 基本面因子 | `get_enhanced_fundamental_factors(code, reader)` | 29个基本面因子 |

### 资金流向数据

| 功能 | 方法 | 数据量 |
|-----|------|--------|
| 行业资金流向 | `ef.get_ths_industry_money_flow(top_n)` | 90个行业 |
| 概念资金流向 | `ef.get_ths_concept_money_flow(top_n)` | 387个概念 |
| 北向资金历史 | `ef.get_north_money_flow(days)` | 2,616条记录 |
| 北向资金行业 | `ef.get_north_money_sector(top_n)` | 86个行业 |
| 北向资金个股 | `ef.get_north_money_stock(code, top_n)` | 2,767只股票 |
| 个股资金流向 | `ef.get_ths_stock_money_flow(code, top_n)` | 5,175只股票 |
| 更新缓存 | `ef.update_ths_money_flow()` | 更新所有缓存 |

### 龙虎榜数据

| 功能 | 方法 | 说明 |
|-----|------|------|
| 龙虎榜列表 | `ef.get_dragon_tiger_list(date)` | 指定日期列表 |
| 个股龙虎榜历史 | `ef.get_stock_dragon_tiger_history(code)` | 个股历史 |
| 机构明细 | `ef.get_institutional_detail(code)` | 机构交易明细 |

### 交易API

| 功能 | 方法 | 说明 |
|-----|------|------|
| 买入 | `api.buy(account_id, code, volume, price)` | 买入股票 |
| 卖出 | `api.sell(account_id, code, volume, price)` | 卖出股票 |
| 撤单 | `api.cancel_order(account_id, order_id)` | 撤销委托 |
| 查资产 | `api.get_account_asset(account_id)` | 查询资产 |
| 查持仓 | `api.get_positions(account_id)` | 查询持仓 |
| 查委托 | `api.get_orders(account_id)` | 查询委托 |
| 查成交 | `api.get_trades(account_id)` | 查询成交 |

---

## 性能优化建议

### 1. 使用智能缓存

```python
# 首次运行：从qstock下载（较慢）
industry_flow = ef.get_ths_industry_money_flow(top_n=20, use_cache=True)

# 再次运行：从DuckDB读取（快200-400倍）
industry_flow = ef.get_ths_industry_money_flow(top_n=20, use_cache=True)
```

### 2. 批量处理

```python
# 推荐：批量获取
stocks = ['000001.SZ', '000002.SZ', '600000.SH']
df = ef.get_market_data(stock_list=stocks, count=100)

# 避免：循环单个获取
for stock in stocks:
    df = ef.get_market_data(stock_list=[stock], count=100)  # 慢
```

### 3. 本地数据优先

```python
# 使用DuckDB本地数据（767万条记录）
df = ef.get_market_data(
    stock_list=['000001.SZ'],
    start_date='2024-01-01',
    end_date='2024-12-31'
)
```

---

## 常见问题

### Q1: 如何更新缓存数据？

```python
# 强制更新缓存
ef.update_ths_money_flow()
```

### Q2: DuckDB数据库在哪里？

默认位置：`D:/StockData/stock_data.ddb`（2.5 GB）

### Q3: 如何添加自定义因子？

```python
# 在 factor_library.py 中添加
def calculate_custom_factor(df):
    # 自定义计算逻辑
    return df['close'] / df['ma20'] - 1

# 注册因子
ef.register_factor('CUSTOM', calculate_custom_factor)
```

---

## 版本信息

- **EasyXT版本**: 3.1
- **Python版本**: 3.6+
- **数据库**: DuckDB
- **数据源**: xtquant + qstock
- **数据量**: 767万条记录

---

## 技术支持

微信公众号：**王者quant**

完整代码和示例：`学习实例/EasyFactor_扩展模块演示.py`
