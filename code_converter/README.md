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

### 交易API

| 聚宽API | Ptrade对应API | 状态 |
|---------|---------------|------|
| [order()](file://c:\Users\Administrator\Desktop\miniqmt扩展\strategies\tdxtrader\tdxtrader\order.py#L0-L106) | [order()](file://c:\Users\Administrator\Desktop\miniqmt扩展\strategies\tdxtrader\tdxtrader\order.py#L0-L106) | ✅ 支持 |
| `order_value()` | `order_value()` | ✅ 支持 |
| `order_target()` | `order_target()` | ✅ 支持 |
| `order_target_value()` | `order_target_value()` | ✅ 支持 |
| `cancel_order()` | `cancel_order()` | ✅ 支持 |

### 其他API

| 聚宽API | Ptrade对应API | 状态 |
|---------|---------------|------|
| `log.info()` | `log.info()` | ✅ 支持 |
| `record()` | `record()` | ✅ 支持 |

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

## 📈 最佳实践

1. **代码规范**：确保聚宽代码符合Python语法规范
2. **API兼容性**：检查使用的API是否在映射表中
3. **测试验证**：转换后在Ptrade环境中测试策略逻辑
4. **逐步迁移**：建议先转换简单策略，再处理复杂策略

## 🆘 故障排除

### 常见问题

1. **转换失败**
   - 检查输入代码是否符合Python语法
   - 确认使用的API是否支持转换

2. **运行时错误**
   - 验证转换后的代码逻辑
   - 检查API参数是否匹配

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

## 📞 技术支持

如有问题，请提交Issue或联系项目维护者。