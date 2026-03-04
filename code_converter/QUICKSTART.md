# 聚宽转Ptrade - 快速使用指南

## 🚀 一键转换

### 方式1：命令行转换（推荐）

```bash
# 基本用法 - 自动检测策略类型
python cli.py input_strategy.py -o output_strategy.py

# 指定策略类型
python cli.py input_strategy.py -o output_strategy.py -t backtest  # 回测策略
python cli.py input_strategy.py -o output_strategy.py -t live       # 实盘策略

# 静默模式（减少输出）
python cli.py input_strategy.py -o output_strategy.py -q
```

### 方式2：Python代码中使用

```python
from converters.jq_to_ptrade_unified import JQToPtradeUnifiedConverter

# 读取聚宽策略
with open('jq_strategy.py', 'r', encoding='utf-8') as f:
    jq_code = f.read()

# 创建转换器并转换
converter = JQToPtradeUnifiedConverter(verbose=True)
ptrade_code = converter.convert(jq_code)

# 保存转换结果
with open('ptrade_strategy.py', 'w', encoding='utf-8') as f:
    f.write(ptrade_code)
```

## 📊 转换示例

### 示例1：简单行情数据策略

**聚宽原代码：**
```python
def initialize(context):
    g.stock = '000001.XSHE'
    set_benchmark('000300.XSHG')

def handle_data(context, data):
    # 获取历史数据
    h = attribute_history(g.stock, 30, '1d', ['close'])
    # 交易逻辑...
    order(g.stock, 100)
```

**Ptrade转换后：**
```python
def initialize(context):
    context.stock = '000001.SZ'  # 证券代码标准化
    set_benchmark('000300.SS')

def handle_data(context, data):
    # API名称调整
    h = get_history(context.stock, 30, '1d', ['close'])
    # 交易逻辑...
    order(context.stock, 100)  # g. → context.
```

### 示例2：定时任务策略

**聚宽原代码：**
```python
def initialize(context):
    run_weekly(weekly_adjustment, weekday=1, time='9:30')
    run_daily(daily_check, time='14:00')
```

**Ptrade转换后：**
```python
def initialize(context):
    run_daily(context, weekly_adjustment, time='9:30')  # run_weekly → run_daily
    run_daily(context, daily_check, time='14:00')

def weekly_adjustment(context):
    # 需要手动添加weekday检查
    if context.current_dt.weekday() != 1:  # 1 = 周二
        return
    # 原有逻辑...
```

### 示例3：基本面选股策略

**聚宽原代码：**
```python
def get_stock_list(context):
    q = query(valuation.code).filter(
        valuation.code.in_(stock_list),
        indicator.eps > 0
    ).limit(100)

    df = get_fundamentals(q)
    return df['code'].tolist()
```

**Ptrade转换后：**
```python
# 在文件开头添加了说明：
# Ptrade支持get_fundamentals函数，但query语法可能略有不同
# 如果出现语法错误，请根据Ptrade文档调整

def get_stock_list(context):
    q = query(valuation.code).filter(
        valuation.code.in_(stock_list),
        indicator.eps > 0
    ).limit(100)

    df = get_fundamentals(q)  # 保留原API调用
    return df['code'].tolist()
    # ⚠️ 注意：可能需要手动调整query语法
```

### 示例4：技术指标策略

**聚宽原代码：**
```python
from jqfactor import MACD, RSI

def check_indicator(context, stock):
    macd_value = MACD(stock, check_date=context.previous_date)
    if macd_value > 0:
        order_target_value(stock, 100000)
```

**Ptrade转换后：**
```python
# from jqfactor import MACD, RSI  # 已注释

# 自动添加技术指标实现
def get_MACD(close_prices, short_period=12, long_period=26, signal_period=9):
    """计算MACD指标"""
    import pandas as pd
    ema_short = pd.Series(close_prices).ewm(span=short_period).mean()
    ema_long = pd.Series(close_prices).ewm(span=long_period).mean()
    dif = ema_short - ema_long
    dea = dif.ewm(span=signal_period).mean()
    bar = (dif - dea) * 2
    return dif.values, dea.values, bar.values

def check_indicator(context, stock):
    # MACD调用已转换为自定义函数
    macd_value = get_macd_value(context, stock)
    if macd_value > 0:
        order_target_value(stock, 100000)
```

## ⚠️ 常见问题及解决方案

### 问题1：日期参数格式错误

**错误信息：**
```
TypeError: get_Ashares() argument must be str, not datetime.date
```

**解决方案：**
```python
# 错误写法
get_Ashares(date=context.current_date)  # datetime对象

# 正确写法
get_Ashares(date=context.current_date.strftime('%Y-%m-%d'))  # 字符串
```

### 问题2：query语法不兼容

**错误信息：**
```
AttributeError: 'Query' object has no attribute 'filter'
```

**解决方案：**
1. 查看转换报告中添加的说明注释
2. 参考Ptrade文档调整query语法
3. 或者简化查询，逐步测试

### 问题3：因子数据不支持

**错误信息：**
```
KeyError: 'sales_growth'  # 或其他因子名
```

**解决方案：**
1. 确认Ptrade是否支持该因子
2. 查看Ptrade文档中的支持因子列表
3. 使用其他因子或通过get_fundamentals计算

### 问题4：run_weekly执行频率不对

**现象：**策略每天都执行，而不是每周一次

**解决方案：**
```python
def weekly_adjustment(context):
    # 添加weekday检查
    if context.current_dt.weekday() != 1:  # 1 = 周二
        return
    # 原有逻辑...
```

## 📝 转换报告说明

转换完成后会生成详细报告：

```
============================================================
转换报告
============================================================

[OK] API映射:
  - get_price → get_price
  - attribute_history → get_history
  - get_all_securities → get_Ashares

[WARNING] 警告:
  - 检测到get_fundamentals使用。需要手动调整query语法。
  - 检测到get_factor_values使用。请确认Ptrade支持该因子。

============================================================
转换完成！请检查生成的代码并根据警告信息手动调整。
============================================================
```

**根据警告信息进行相应调整：**
- `[OK]` 表示成功转换，无需修改
- `[WARNING]` 表示需要手动检查和调整
- `[ERROR]` 表示转换失败，需要查看代码

## 🎯 最佳实践

### 1. 转换前准备
- [ ] 备份原始聚宽代码
- [ ] 确认策略类型（回测/实盘）
- [ ] 记录策略使用的API列表

### 2. 转换过程
- [ ] 使用统一转换器进行转换
- [ ] 查看转换报告
- [ ] 记录所有警告信息

### 3. 转换后检查
- [ ] 检查日期参数格式
- [ ] 检查query语法（如有）
- [ ] 检查因子数据支持（如有）
- [ ] 添加weekday检查（如有run_weekly）
- [ ] 测试技术指标实现（如有）

### 4. 验证测试
- [ ] 在Ptrade环境中加载策略
- [ ] 运行简单回测验证逻辑
- [ ] 检查交易信号是否正确
- [ ] 确认性能指标符合预期

## 🔗 相关资源

- **完整文档**: `README_UNIFIED.md`
- **转换器代码**: `converters/jq_to_ptrade_unified.py`
- **命令行工具**: `cli.py`
- **Ptrade文档**: (请添加Ptrade官方文档链接)

## 📞 获取帮助

如果遇到问题：

1. ✅ 查看本文档的"常见问题"部分
2. ✅ 查看转换报告中的警告信息
3. ✅ 参考上面的转换示例
4. ✅ 提交Issue或联系项目维护者

---

**版本**: v2.0 (统一转换器)
**更新时间**: 2026-03-02
