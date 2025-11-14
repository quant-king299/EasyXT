# 聚宽到Ptrade代码转换器

## 📋 概述

本工具用于将聚宽（JoinQuant）策略代码自动转换为Ptrade格式的代码，帮助用户快速迁移策略到Ptrade平台。

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 使用方法

#### 命令行使用

```bash
# 基本用法
python cli.py input_strategy.py

# 指定输出文件
python cli.py input_strategy.py -o output_strategy.py

# 使用自定义API映射文件
python cli.py input_strategy.py -m custom_mapping.json

# 查看帮助
python cli.py -h
```

#### Python代码中使用

```python
from converters.jq_to_ptrade import JQToPtradeConverter

# 创建转换器
converter = JQToPtradeConverter()

# 读取聚宽策略代码
with open('jq_strategy.py', 'r', encoding='utf-8') as f:
    jq_code = f.read()

# 转换代码
ptrade_code = converter.convert(jq_code)

# 保存转换后的代码
with open('ptrade_strategy.py', 'w', encoding='utf-8') as f:
    f.write(ptrade_code)
```

## 📊 支持的转换

### 数据获取API

| 聚宽API | Ptrade对应API | 状态 |
|---------|---------------|------|
| `get_price()` | `get_price()` | ✅ 支持 |
| `get_current_data()` | `get_current_data()` | ✅ 支持 |
| `get_fundamentals()` | `get_fundamentals()` | ✅ 支持 |
| `get_index_stocks()` | `get_index_stocks()` | ✅ 支持 |
| `get_industry_stocks()` | `get_industry_stocks()` | ✅ 支持 |
| `get_concept_stocks()` | `get_concept_stocks()` | ✅ 支持 |
| `get_all_securities()` | `get_all_securities()` | ✅ 支持 |
| `get_security_info()` | `get_security_info()` | ✅ 支持 |
| `attribute_history()` | `get_price()` | ✅ 支持 |

### 交易API

| 聚宽API | Ptrade对应API | 状态 |
|---------|---------------|------|
| [order()](file://c:\Users\Administrator\Desktop\miniqmt扩展\strategies\tdxtrader\tdxtrader\order.py#L0-L106) | [order()](file://c:\Users\Administrator\Desktop\miniqmt扩展\strategies\tdxtrader\tdxtrader\order.py#L0-L106) | ✅ 支持 |
| `order_value()` | `order_value()` | ✅ 支持 |
| `order_target()` | `order_target()` | ✅ 支持 |
| `order_target_value()` | `order_target_value()` | ✅ 支持 |
| `cancel_order()` | `cancel_order()` | ✅ 支持 |
| `get_open_orders()` | `get_open_orders()` | ✅ 支持 |

### 账户API

| 聚宽API | Ptrade对应API | 状态 |
|---------|---------------|------|
| `get_portfolio()` | `get_portfolio()` | ✅ 支持 |
| `get_positions()` | `get_positions()` | ✅ 支持 |
| `get_orders()` | `get_orders()` | ✅ 支持 |
| `get_trades()` | `get_trades()` | ✅ 支持 |

### 系统API

| 聚宽API | Ptrade对应API | 状态 |
|---------|---------------|------|
| `log.info()` | `log.info()` | ✅ 支持 |
| `log.warn()` | `log.warn()` | ✅ 支持 |
| `log.error()` | `log.error()` | ✅ 支持 |
| `record()` | `record()` | ✅ 支持 |
| `plot()` | `plot()` | ✅ 支持 |
| `set_benchmark()` | `set_benchmark()` | ✅ 支持 |
| `set_option()` | `set_option()` | ✅ 支持 |

### 风险控制API

| 聚宽API | Ptrade对应API | 状态 |
|---------|---------------|------|
| `set_slippage()` | `set_slippage()` | ✅ 支持 |
| `set_commission()` | `set_commission()` | ✅ 支持 |
| `set_price_limit()` | `set_price_limit()` | ✅ 支持 |

### 定时任务API

| 聚宽API | Ptrade对应API | 状态 |
|---------|---------------|------|
| `run_daily()` | `run_daily()` | ✅ 支持 |
| `run_weekly()` | `run_weekly()` | ✅ 支持 |
| `run_monthly()` | `run_monthly()` | ✅ 支持 |

## 🛠️ 高级功能

### 自定义API映射

```python
converter = JQToPtradeConverter()
# 添加自定义映射
converter.api_mapping['custom_jq_func'] = 'custom_ptrade_func'
```

### 扩展特殊处理

```python
def custom_handler(node):
    # 自定义处理逻辑
    return node

converter = JQToPtradeConverter()
converter.special_handlers['special_func'] = custom_handler
```

### 自定义API映射文件

可以创建一个JSON文件来定义API映射关系：

```json
{
  "get_price": "get_price",
  "order": "order",
  "log.info": "log.info"
}
```

然后在命令行中使用：
```bash
python cli.py input.py -m custom_mapping.json
```

## 📈 最佳实践

1. **代码规范**：确保聚宽代码符合Python语法规范
2. **API兼容性**：检查使用的API是否在映射表中
3. **测试验证**：转换后在Ptrade环境中测试策略逻辑
4. **逐步迁移**：建议先转换简单策略，再处理复杂策略
5. **全局变量处理**：聚宽中的`g`变量会被自动转换为`context`变量

## 🆘 故障排除

### 常见问题

1. **转换失败**
   - 检查输入代码是否符合Python语法
   - 确认使用的API是否支持转换

2. **运行时错误**
   - 验证转换后的代码逻辑
   - 检查API参数是否匹配

3. **API未找到**
   - 检查API映射文件是否正确
   - 确认Ptrade平台是否支持该API

### 调试方法

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 启用详细日志
converter = JQToPtradeConverter()
```

## 📚 相关文档

- [聚宽API文档](https://www.joinquant.com/help/api/help)
- [Ptrade API文档](https://www.ptrade.com.cn/api)

## 📁 项目结构

```
code_converter/
├── cli.py                 # 命令行接口
├── api_mapping.json       # API映射文件
├── converters/
│   └── jq_to_ptrade.py    # 核心转换器
├── utils/
│   ├── code_parser.py     # 代码解析工具
│   └── code_generator.py  # 代码生成工具
├── samples/               # 示例文件
└── README.md              # 项目说明
```

## 🧪 测试示例

项目包含多个测试示例：

1. 基础示例：`samples/jq_sample_strategy.py`
2. 完整示例：`samples/jq_sample_strategy_complete.py`

转换后的文件保存在相同目录下，文件名带有`ptrade_`前缀。

## 📞 技术支持

如有问题，请提交Issue或联系项目维护者。