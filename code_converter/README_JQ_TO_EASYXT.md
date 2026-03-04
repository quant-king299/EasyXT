# 聚宽转EasyXT转换器使用指南

## 📖 目录

- [功能介绍](#功能介绍)
- [核心特性](#核心特性)
- [快速开始](#快速开始)
- [详细说明](#详细说明)
- [API映射表](#api映射表)
- [常见问题](#常见问题)
- [实战案例](#实战案例)

---

## 功能介绍

聚宽转EasyXT转换器是一个智能代码转换工具，可以将聚宽平台的策略代码自动转换为可以在miniqmt（EasyXT）环境运行的代码。

### 支持的转换功能

- ✅ **框架转换**：将聚宽的 `initialize/handle_data` 框架转换为独立脚本
- ✅ **API映射**：自动将聚宽API转换为EasyXT API
- ✅ **变量转换**：将全局变量 `g.xxx` 转换为Python全局变量
- ✅ **定时任务**：将 `run_daily` 等定时任务转换为可调用函数
- ✅ **代码重构**：生成结构清晰、易于维护的代码

---

## 核心特性

### 1. 智能分析

自动分析聚宽代码特征：
- 识别策略类型（日线策略、分钟策略等）
- 检测使用的API类型
- 提取定时任务函数
- 分析交易逻辑

### 2. 详细报告

转换过程中提供详细的日志：
- API映射记录
- 警告信息
- 需要手动修复的部分
- 转换成功率统计

### 3. 安全可靠

- 保留原始代码逻辑
- 标注需要手动处理的部分
- 提供完善的错误提示
- 支持转换后人工检查

---

## 快速开始

### 安装依赖

```bash
# 进入项目目录
cd C:\EasyXT

# 安装依赖（如果还没安装）
pip install -r requirements.txt
```

### 基础使用

```python
from converters.jq_to_easyxt import JQToEasyXTConverter

# 准备聚宽代码
jq_code = """
import jqdata

def initialize(context):
    g.stock = '000001.XSHE'
    set_benchmark('000300.XSHG')

def handle_data(context, data):
    hist = attribute_history(g.stock, 5, '1d', ['close'], df=True)
    ma5 = hist['close'].mean()
    # ... 策略逻辑
"""

# 创建转换器
converter = JQToEasyXTConverter(
    verbose=True,  # 显示详细日志
    account_id="your_account_id"  # 设置账户ID
)

# 执行转换
easyxt_code = converter.convert(
    jq_code,
    output_file='my_strategy.py'  # 保存到文件
)

print("转换完成！")
```

### 运行转换后的代码

```bash
# 运行生成的策略
python my_strategy.py
```

---

## 详细说明

### 转换流程

#### 步骤1：代码分析

转换器首先分析聚宽代码：

```python
# 检测到的特征：
# - initialize函数：✅
# - handle_data函数：✅
# - 定时任务：run_daily(check_entry)
# - 使用的API：attribute_history, order_value, log.info
# - 全局变量：g.stock, g.ma_short
```

#### 步骤2：框架转换

将聚宽框架转换为EasyXT独立脚本：

**聚宽框架：**
```python
def initialize(context):
    g.stock = '000001.XSHE'

def handle_data(context, data):
    # 策略逻辑
    pass
```

**EasyXT框架：**
```python
def initialize():
    """初始化函数"""
    api = easy_xt.get_api()
    api.init_data()
    return api

def run_strategy(api):
    """主策略循环"""
    # 策略逻辑
    pass

if __name__ == "__main__":
    api = initialize()
    run_strategy(api)
```

#### 步骤3：API映射

自动转换API调用：

| 聚宽API | EasyXT API | 说明 |
|---------|-----------|------|
| `get_price()` | `api.get_price()` | 获取历史数据 |
| `attribute_history()` | `api.get_price()` | 获取历史数据 |
| `get_current_data()` | `api.get_current_price()` | 获取实时数据 |
| `get_all_securities()` | `api.get_stock_list()` | 获取股票列表 |
| `log.info()` | `print()` | 输出日志 |

#### 步骤4：变量转换

转换变量引用：

**聚宽代码：**
```python
g.stock = '000001.XSHE'
price = get_current_data()[g.stock].last_price
cash = context.portfolio.available_cash
```

**EasyXT代码：**
```python
stock = '000001.SZ'  # 全局变量
current = api.get_current_price(stock)
price = current['price'].iloc[0]
cash = account_cash  # 需要手动实现
```

#### 步骤5：交易函数转换

交易函数需要手动完善：

**聚宽代码：**
```python
# 按金额买入
order_value(stock, cash)

# 调整持仓
order_target(stock, 0)

# 按目标金额
order_target_value(stock, 100000)
```

**EasyXT代码（需要手动完善）：**
```python
# TODO: 转换按金额买入逻辑
# api.buy(account_id, stock, volume=计算数量)

# TODO: 转换卖出逻辑
# api.sell(account_id, stock, volume=持仓数量)
```

---

## API映射表

### 数据获取API

| 聚宽API | EasyXT API | 参数差异 | 备注 |
|---------|-----------|---------|------|
| `get_price(security, count)` | `api.get_price(code, count)` | security→code | 完全兼容 |
| `attribute_history(security, count, unit, fields, df)` | `api.get_price(code, count, period)` | unit→period | 简化参数 |
| `get_current_data()` | `api.get_current_price(code)` | 需要传入code | 返回格式不同 |
| `get_all_securities(types, date)` | `api.get_stock_list(market)` | 参数简化 | 返回格式不同 |
| `get_trade_days(start_date, end_date)` | `api.get_trading_dates(start, end)` | 参数名变化 | 日期格式兼容 |

### 交易API

| 聚宽API | EasyXT API | 说明 |
|---------|-----------|------|
| `order_value(security, value)` | `api.buy(account_id, code, volume)` | 需要计算volume |
| `order_target(security, amount)` | `api.buy/sell(account_id, code, volume)` | 需要判断买卖 |
| `order_target_value(security, value)` | `api.buy(account_id, code, volume)` | 需要计算volume |
| `cancel_order(order)` | 暂不支持 | EasyXT待完善 |

### 系统API

| 聚宽API | EasyXT API | 说明 |
|---------|-----------|------|
| `log.info(msg)` | `print(msg)` | 直接使用print |
| `log.warn(msg)` | `print(msg)` | 直接使用print |
| `set_benchmark(security)` | 不需要 | EasyXT无此概念 |
| `get_datetime()` | `datetime.now()` | 使用datetime模块 |

---

## 常见问题

### Q1: 转换后的代码需要手动修改哪些部分？

**A:** 主要需要手动修改的部分：

1. **账户配置**
   ```python
   ACCOUNT_ID = "your_account_id"  # 修改为实际账户ID
   USERDATA_PATH = "D:\\QMT\\userdata_mini"  # 修改为实际路径
   ```

2. **交易逻辑**
   ```python
   # TODO: 转换按金额买入逻辑
   # 需要手动计算买入数量
   volume = int(cash / current_price / 100) * 100  # 按手数
   api.buy(ACCOUNT_ID, stock, volume=volume)
   ```

3. **持仓管理**
   ```python
   # 需要手动维护持仓数据
   positions = {}  # {stock: volume}
   ```

4. **context对象相关**
   ```python
   # context.portfolio.available_cash
   # 需要手动实现账户资金查询
   ```

### Q2: 如何处理定时任务？

**A:** 聚宽的定时任务转换为函数，需要手动调用：

**聚宽代码：**
```python
run_daily(check_entry, time='9:30')
run_weekly(rebalance, weekday=1, time='9:30')
```

**EasyXT代码：**
```python
def check_entry(api):
    # 入场逻辑
    pass

def rebalance(api):
    # 调仓逻辑
    pass

# 需要在主循环中手动调用
if __name__ == "__main__":
    api = initialize()

    # 简单定时：每分钟检查
    while True:
        now = datetime.now()
        if now.hour == 9 and now.minute == 30:
            check_entry(api)

        if now.weekday() == 0 and now.hour == 9 and now.minute == 30:  # 周一
            rebalance(api)

        time.sleep(60)
```

### Q3: 如何处理基本面数据？

**A:** 基本面数据需要使用其他数据源：

**聚宽代码：**
```python
q = query(valuation.code).filter(
    valuation.code.in_(stock_list),
    valuation.pe_ratio < 20
)
df = get_fundamentals(q)
```

**EasyXT代码：**
```python
# TODO: 实现基本面数据获取
# 方案1：使用tushare
import tushare as ts
pro = ts.pro_api('your_token')
df = pro.daily_basic(ts_code='000001.SZ', fields='ts_code,pe_ttm')

# 方案2：使用akshare
import akshare as ak
df = ak.stock_a_lg_indicator(symbol="000001")

# 方案3：使用easy_xt的扩展数据源（如果有）
```

### Q4: 转换后如何测试？

**A:** 建议按以下步骤测试：

1. **语法检查**
   ```bash
   python -m py_compile my_strategy.py
   ```

2. **数据测试**
   ```python
   # 测试数据获取
   api = easy_xt.get_api()
   api.init_data()
   data = api.get_price('000001.SZ', count=10)
   print(data)
   ```

3. **模拟运行**
   ```python
   # 注释掉实际交易，只打印信号
   # api.buy(ACCOUNT_ID, stock, volume)
   print(f"买入信号: {stock}, 数量: {volume}")
   ```

4. **小资金验证**
   ```python
   # 使用少量资金测试
   test_cash = 1000  # 1000元测试
   ```

### Q5: 转换失败怎么办？

**A:** 检查以下几点：

1. **代码格式**
   - 确保缩进正确（4空格）
   - 函数定义完整
   - 没有语法错误

2. **函数提取**
   - `initialize` 和 `handle_data` 函数必须存在
   - 定时任务函数定义完整

3. **手动处理**
   - 查看转换报告中的警告
   - 完善标记为TODO的部分
   - 检查手动修复列表

---

## 实战案例

### 案例1：双均线策略

**聚宽原始代码：**
```python
import jqdata

def initialize(context):
    g.stock = '000001.XSHE'
    g.ma_short = 5
    g.ma_long = 20
    set_benchmark('000300.XSHG')

def handle_data(context, data):
    # 获取历史数据
    hist = attribute_history(g.stock, g.ma_long, '1d', ['close'], df=True)

    # 计算均线
    ma_short = hist['close'].tail(g.ma_short).mean()
    ma_long = hist['close'].mean()

    # 获取当前价格
    current = get_current_data()
    price = current[g.stock].last_price

    # 获取可用资金
    cash = context.portfolio.available_cash

    # 金叉买入
    if ma_short > ma_long and cash > 0:
        order_value(g.stock, cash)
        log.info("金叉买入")

    # 死叉卖出
    elif ma_short < ma_long:
        order_target(g.stock, 0)
        log.info("死叉卖出")
```

**转换后（关键部分）：**
```python
# 全局变量
stock = '000001.SZ'
ma_short = 5
ma_long = 20

def initialize():
    api = easy_xt.get_api()
    api.init_data()
    api.init_trade(USERDATA_PATH)
    api.add_account(ACCOUNT_ID)
    return api

def run_strategy(api):
    # 获取历史数据
    hist = api.get_price(stock, count=ma_long, period='1d')

    # 计算均线
    ma_short_val = hist['close'].tail(ma_short).mean()
    ma_long_val = hist['close'].mean()

    # 获取当前价格
    current = api.get_current_price(stock)
    price = current['price'].iloc[0]

    # 金叉买入
    if ma_short_val > ma_long_val:
        # TODO: 获取实际可用资金
        cash = 10000  # 示例值

        # TODO: 计算买入数量
        volume = int(cash / price / 100) * 100

        api.buy(ACCOUNT_ID, stock, volume=volume)
        print(f"金叉买入 {stock}")

    # 死叉卖出
    elif ma_short_val < ma_long_val:
        # TODO: 获取实际持仓
        volume = 100  # 示例值

        api.sell(ACCOUNT_ID, stock, volume=volume)
        print(f"死叉卖出 {stock}")
```

### 案例2：多因子选股策略

**聚宽原始代码：**
```python
def initialize(context):
    g.stock_num = 10
    g.rebalance_days = 5
    run_weekly(rebalance, weekday=1, time='9:30')

def rebalance(context):
    # 获取股票池
    pool = get_stock_pool(context)

    # 计算因子得分
    scores = []
    for stock in pool:
        hist = attribute_history(stock, 20, '1d', ['close'], df=True)
        ret = (hist['close'].iloc[-1] - hist['close'].iloc[0]) / hist['close'].iloc[0]
        scores.append((stock, ret))

    # 选择得分最高的股票
    scores.sort(key=lambda x: x[1], reverse=True)
    target_stocks = [s for s, _ in scores[:g.stock_num]]

    # 调仓
    for stock in target_stocks:
        order_value(stock, 10000)
```

**转换后（关键部分）：**
```python
def rebalance(api):
    # 获取股票池
    pool = get_stock_pool(api)

    # 计算因子得分
    scores = []
    for stock in pool:
        hist = api.get_price(stock, count=20, period='1d')
        ret = (hist['close'].iloc[-1] - hist['close'].iloc[0]) / hist['close'].iloc[0]
        scores.append((stock, ret))

    # 选择得分最高的股票
    scores.sort(key=lambda x: x[1], reverse=True)
    target_stocks = [s for s, _ in scores[:stock_num]]

    # 调仓
    for stock in target_stocks:
        # TODO: 计算买入数量
        volume = 100  # 示例值
        api.buy(ACCOUNT_ID, stock, volume=volume)

def get_stock_pool(api):
    # 获取股票池
    stock_list = api.get_stock_list('A股')
    return stock_list[:100]  # 示例：返回前100只
```

---

## 高级技巧

### 1. 自定义转换规则

```python
converter = JQToEasyXTConverter()

# 添加自定义API映射
converter.api_mapping['custom_api'] = 'my_custom_function'

# 执行转换
result = converter.convert(jq_code)
```

### 2. 批量转换

```python
import os
from pathlib import Path

# 转换目录下所有聚宽策略
jq_dir = Path('jq_strategies')
output_dir = Path('easyxt_strategies')
output_dir.mkdir(exist_ok=True)

for jq_file in jq_dir.glob('*.py'):
    print(f"转换 {jq_file.name}...")

    with open(jq_file, 'r', encoding='utf-8') as f:
        jq_code = f.read()

    converter = JQToEasyXTConverter(verbose=False)
    output_file = output_dir / f"converted_{jq_file.name}"

    converter.convert(jq_code, output_file=str(output_file))

print("批量转换完成！")
```

### 3. 转换报告分析

```python
converter = JQToEasyXTConverter()
converter.convert(jq_code)

# 获取转换报告
report = converter.get_conversion_report()

print(f"API映射数量: {len(report['api_mappings'])}")
print(f"警告数量: {len(report['warnings'])}")
print(f"需要手动修复: {len(report['manual_fixes'])}")

# 保存报告
import json
with open('conversion_report.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
```

---

## 总结

聚宽转EasyXT转换器可以大大简化代码迁移工作，但需要注意：

1. ✅ **自动转换**：大部分代码可以自动转换
2. ⚠️ **手动完善**：交易逻辑需要手动实现
3. 🔍 **仔细测试**：转换后必须充分测试
4. 📝 **持续优化**：根据实际需求优化代码

**记住：转换器只是辅助工具，最终的策略正确性需要你自己验证！**

---

## 联系方式

- 项目地址：https://github.com/quant-king299/EasyXT
- 问题反馈：提交Issue
- 技术交流：加入知识星球

---

**祝转换顺利！** 🎉
