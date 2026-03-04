# 聚宽到Ptrade代码转换器 v2.0

## 🎯 重大更新

### v2.0 统一转换器
我们整合了之前的6个独立转换器，推出了**统一转换器**，具有以下优势：

- ✅ **自动识别策略类型**：智能判断回测/实盘/混合策略
- ✅ **智能API转换**：根据策略类型优化API处理
- ✅ **详细转换报告**：列出所有API映射和需要手动调整的项目
- ✅ **保留代码逻辑**：不再覆盖用户代码，真正实现转换
- ✅ **统一命令行接口**：一个工具处理所有场景

## 🚀 快速开始

### 基本使用

```bash
# 自动检测策略类型并转换
python cli.py your_jq_strategy.py -o ptrade_strategy.py

# 指定策略类型
python cli.py your_jq_strategy.py -o ptrade_strategy.py -t backtest
python cli.py your_jq_strategy.py -o ptrade_strategy.py -t live

# 静默模式（减少输出）
python cli.py your_jq_strategy.py -o ptrade_strategy.py -q
```

### Python代码中使用

```python
from converters.jq_to_ptrade_unified import JQToPtradeUnifiedConverter, StrategyType

# 创建转换器
converter = JQToPtradeUnifiedConverter(verbose=True)

# 自动检测策略类型
ptrade_code = converter.convert(jq_code)

# 或指定策略类型
ptrade_code = converter.convert(jq_code, strategy_type=StrategyType.BACKTEST)

# 获取转换报告
report = converter.get_conversion_report()
print(f"API映射: {report['api_mappings']}")
print(f"警告: {report['warnings']}")
```

## 📊 支持的API转换

### 基础行情API

| 聚宽API | Ptrade API | 转换方式 | 说明 |
|---------|-----------|---------|------|
| `get_price()` | `get_price()` | 自动映射 | 参数可能需要调整 |
| `attribute_history()` | `get_history()` | 自动映射 | API名称变更 |
| `get_bars()` | `get_history()` | 自动映射 | API名称变更 |
| `get_current_data()` | `get_snapshot()` | 自动映射 | API名称变更 |

### 基本面数据API

| 聚宽API | Ptrade API | 转换方式 | 说明 |
|---------|-----------|---------|------|
| `get_fundamentals()` | `get_fundamentals()` | 智能转换 | query语法需要手动调整 |
| `query()` | `query()` | 保留+注释 | 需检查语法兼容性 |
| `valuation.*` | `valuation.*` | 保留 | 字段名可能不同 |

### 因子数据API

| 聚宽API | Ptrade API | 转换方式 | 说明 |
|---------|-----------|---------|------|
| `get_factor_values()` | `get_factor_values()` | 保留+注释 | 需确认Ptrade支持 |
| `MACD()` / `RSI()` 等 | 自定义实现 | 提供示例 | 转换器提供实现示例 |

### 证券信息API

| 聚宽API | Ptrade API | 转换方式 | 说明 |
|---------|-----------|---------|------|
| `get_all_securities()` | `get_Ashares()` | 自动映射 | 日期参数格式需调整 |
| `get_security_info()` | `get_stock_info()` | 自动映射 | API名称变更 |
| `get_index_stocks()` | `get_index_stocks()` | 自动映射 | 直接映射 |

### 交易API

| 聚宽API | Ptrade API | 转换方式 | 说明 |
|---------|-----------|---------|------|
| `order()` | `order()` | 自动映射 | 直接映射 |
| `order_target_value()` | `order_target_value()` | 自动映射 | 直接映射 |
| `order_value()` | `order_value()` | 自动映射 | 直接映射 |

### 定时任务API

| 聚宽API | Ptrade API | 转换方式 | 说明 |
|---------|-----------|---------|------|
| `run_daily()` | `run_daily()` | 参数调整 | 添加context参数 |
| `run_weekly()` | `run_daily()` | 转换 | 需在函数内检查weekday |
| `run_monthly()` | `run_daily()` | 转换 | 需在函数内检查日期 |

### 不支持的API

以下API会被注释或移除，并给出警告：

- `log.set_level()` - 已移除
- `set_commission()` - 已移除
- `set_price_limit()` - 已移除
- `set_order_cost()` - 已移除

## 🔧 高级功能

### 策略类型自动检测

转换器会根据代码特征自动识别策略类型：

```python
# 使用了实时行情数据 → 实盘策略
current_data = get_current_data()

# 使用了历史回测数据 → 回测策略
h = attribute_history(stock, 30, '1d', ['close'])

# 同时使用 → 混合策略
```

### 智能API处理

转换器对关键API进行智能处理：

```python
# 聚宽代码
g.stock_pool = get_all_securities(date=context.current_date)

# 转换后
context.stock_pool = get_Ashares(date=context.current_date)  # [注意] 确保日期参数为YYYY-MM-DD格式字符串
```

### 技术指标处理

如果策略使用了聚宽因子库中的技术指标，转换器会：

1. 检测到 `from jqfactor import ...`
2. 在代码中添加技术指标实现示例
3. 提示用户需要实现或使用Ptrade提供的指标

```python
# 自动添加的技术指标实现
def get_MACD(close_prices, short_period=12, long_period=26, signal_period=9):
    """计算MACD指标"""
    import pandas as pd
    ema_short = pd.Series(close_prices).ewm(span=short_period).mean()
    ema_long = pd.Series(close_prices).ewm(span=long_period).mean()
    dif = ema_short - ema_long
    dea = dif.ewm(span=signal_period).mean()
    bar = (dif - dea) * 2
    return dif.values, dea.values, bar.values
```

### 转换报告

转换完成后，转换器会输出详细报告：

```
============================================================
转换报告
============================================================

✓ API映射:
  - get_price → get_price
  - attribute_history → get_history
  - get_all_securities → get_Ashares
  - run_weekly → run_daily

⚠ 警告:
  - 检测到get_fundamentals使用。Ptrade需要手动调整query对象语法。
  - 检测到get_factor_values使用。请确认Ptrade支持所需的因子数据。

============================================================
转换完成！请检查生成的代码并根据警告信息手动调整。
============================================================
```

## 📋 转换后需要手动调整的项目

### 1. 基本面数据查询

聚宽和Ptrade的query语法可能略有不同：

```python
# 聚宽语法
q = query(valuation.code).filter(
    valuation.code.in_(stock_list),
    indicator.eps > 0
).order_by(valuation.circulating_market_cap.asc())

# 可能需要调整为Ptrade语法（具体请参考Ptrade文档）
```

### 2. 因子数据确认

确认Ptrade支持策略中使用的因子：

```python
# 检查因子是否可用
s_score = get_factor_values(stock_list, 'sales_growth', ...)
# 如果报错，说明Ptrade不支持该因子
```

### 3. 日期参数格式

确保日期参数为字符串格式：

```python
# 错误
get_Ashares(date=context.current_date)  # datetime对象

# 正确
get_Ashares(date=context.current_date.strftime('%Y-%m-%d'))  # 字符串
```

### 4. 定时任务逻辑

对于`run_weekly`转换后的`run_daily`，需要在函数内添加weekday检查：

```python
def weekly_adjustment(context):
    # 添加weekday检查
    if context.current_dt.weekday() != 1:  # 1 = 周二
        return

    # 原有逻辑...
```

### 5. 技术指标实现

如果策略使用了技术指标，需要：

1. 使用转换器提供的实现示例
2. 或使用Ptrade提供的技术指标函数
3. 或自行实现

## 🎓 最佳实践

1. **先自动转换，后手动调整**
   - 使用统一转换器完成大部分转换工作
   - 根据转换报告手动调整关键部分

2. **保留原始聚宽代码**
   - 转换前备份原始代码
   - 便于对比和调试

3. **逐步验证**
   - 先转换简单策略验证转换器
   - 再处理复杂策略

4. **利用Ptrade文档**
   - 遇到API不兼容时，查阅Ptrade官方文档
   - 确认正确的API使用方式

5. **测试转换结果**
   - 在Ptrade环境中测试转换后的代码
   - 检查回测/实盘结果是否符合预期

## 🔍 常见问题

### Q: 转换后代码报错怎么办？

A: 查看转换报告中的警告信息，通常是以下原因：

1. API语法不兼容 → 根据Ptrade文档调整
2. 日期参数格式错误 → 改为YYYY-MM-DD格式字符串
3. 因子数据不支持 → 移除或替换该因子
4. 技术指标未实现 → 添加技术指标实现函数

### Q: run_weekly转换后策略执行频率不对？

A: 这是正常的，因为Ptrade不支持run_weekly。需要在函数内添加weekday检查：

```python
def your_function(context):
    if context.current_dt.weekday() != 1:  # 只在周一执行
        return
    # 原有逻辑...
```

### Q: 基本面数据查询报错？

A: query语法可能需要调整。建议：

1. 查看Ptrade文档确认query语法
2. 简化查询条件逐步测试
3. 考虑使用其他方式获取基本面数据

### Q: 因子数据不支持怎么办？

A: 有以下替代方案：

1. 使用Ptrade提供的其他因子
2. 通过get_fundamentals计算类似指标
3. 从外部数据源获取因子数据

## 📁 项目结构

```
code_converter/
├── cli.py                              # 命令行工具（已更新使用统一转换器）
├── converters/
│   ├── jq_to_ptrade_unified.py        # 🆕 统一转换器（推荐）
│   ├── jq_to_ptrade.py                # 旧版基础转换器（已弃用）
│   ├── jq_to_ptrade_enhanced.py       # 旧版增强转换器（已弃用）
│   ├── jq_to_ptrade_factors.py        # 旧版因子转换器（已弃用）
│   ├── jq_to_ptrade_live.py           # 旧版实盘转换器（已弃用）
│   └── ...
├── samples/                            # 示例策略文件
└── README_UNIFIED.md                   # 📖 本文档
```

## 📞 技术支持

如有问题或建议，请：

1. 查看本文档的常见问题部分
2. 检查转换报告中的警告信息
3. 参考Ptrade官方文档
4. 提交Issue或联系项目维护者

## 🎉 v2.0 更新日志

### 新增功能
- ✨ 统一转换器：整合6个独立转换器
- ✨ 自动策略类型检测
- ✨ 详细转换报告
- ✨ 技术指标实现示例
- ✨ 智能API处理

### 改进优化
- 🔧 保留用户代码逻辑
- 🔧 更好的错误处理
- 🔧 改进的g.变量转换
- 🔧 证券代码标准化

### 已弃用
- ❌ jq_to_ptrade.py（基础版）
- ❌ jq_to_ptrade_enhanced.py（增强版）
- ❌ jq_to_ptrade_factors.py（因子版）
- ❌ jq_to_ptrade_live.py（实盘版）
- ❌ jq_to_ptrade_monthly.py（月度版）
- ❌ jq_to_ptrade_current_data.py（实时数据版）

*注意：旧版转换器仍然可用，但推荐使用新的统一转换器。*
