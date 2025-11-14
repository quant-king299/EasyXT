# EasyXT与通达信预警集成方案

[配置说明](CONFIGURATION.md)

本方案展示了如何将EasyXT量化交易框架与通达信预警信号结合，实现自动化的程序交易。

## 📋 方案概述

通过集成tdxtrader和EasyXT，我们可以：

1. **读取通达信预警信号**：监控通达信生成的买卖信号
2. **使用EasyXT执行交易**：利用EasyXT封装的交易API执行买卖操作
3. **统一配置管理**：通过配置文件管理交易参数
4. **支持多种交易类型**：市价单、限价单等
5. **提供日志和通知**：交易日志记录和企业微信通知

## 📁 项目结构

```
strategies/tdxtrader/
├── easyxt_tdx_integration.py    # EasyXT与通达信集成主模块
├── tdxtrader_integration_example.py  # 集成示例
├── tdxtrader/                   # tdxtrader源码
│   ├── __init__.py
│   ├── index.py
│   ├── trader.py
│   ├── order.py
│   ├── file.py
│   ├── logger.py
│   ├── utils.py
│   └── anis.py
└── README_EASYXT_INTEGRATION.md # 本说明文件
```

## 🚀 快速开始

### 1. 配置通达信预警

1. 在通达信中设置预警指标
2. 配置预警文件输出路径（如：`D:\new_tdx\sign.txt`）
3. 确保通达信正在运行并生成预警信号

### 2. 配置交易参数

运行程序后会自动生成配置文件模板 `tdx_easyxt_config.json`：

```json
{
    "tdx_file_path": "D:/new_tdx/sign.txt",
    "interval": 1,
    "buy_signals": ["KDJ买入条件选股", "MACD买入条件选股"],
    "sell_signals": ["KDJ卖出条件选股", "MACD卖出条件选股"],
    "cancel_after": 10,
    "wechat_webhook_url": null,
    "default_volume": 100,
    "price_type": "limit"
}
```

> **注意**：账户ID和QMT路径配置已移至项目根目录的统一配置文件中，请参考 [配置说明](CONFIGURATION.md) 进行配置。

### 3. 启动交易系统

```python
from strategies.tdxtrader.easyxt_tdx_integration import TDXEasyXTIntegration

# 初始化集成器
integration = TDXEasyXTIntegration("tdx_easyxt_config.json")

# 启动交易系统
integration.start_trading()
```

## 🔧 核心功能

### 1. 信号处理

- **买入信号处理**：当通达信生成买入信号时，自动执行买入操作
- **卖出信号处理**：当通达信生成卖出信号时，自动执行卖出操作
- **多信号支持**：支持多个买入/卖出信号

### 2. 交易执行

- **市价单/限价单**：支持不同类型的订单
- **自动计算数量**：根据配置自动计算交易数量
- **持仓检查**：卖出前检查是否有持仓
- **异常处理**：完善的异常处理机制

### 3. 配置管理

- **统一配置**：所有参数通过配置文件管理
- **默认值**：提供合理的默认配置
- **灵活扩展**：支持自定义配置项

## 📊 使用示例

```python
# 创建集成器实例
integration = TDXEasyXTIntegration("my_config.json")

# 启动交易系统
integration.start_trading()
```

## ⚙️ 配置说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| account_id | QMT账户ID | 从统一配置文件读取 |
| qmt_path | QMT用户数据路径 | 从统一配置文件读取 |
| tdx_file_path | 通达信预警文件路径 | "D:/new_tdx/sign.txt" |
| interval | 轮询间隔(秒) | 1 |
| buy_signals | 买入信号列表 | ["KDJ买入条件选股"] |
| sell_signals | 卖出信号列表 | ["KDJ卖出条件选股"] |
| cancel_after | 未成交撤单时间(秒) | 10 |
| wechat_webhook_url | 企业微信机器人URL | None |
| default_volume | 默认交易数量 | 100 |
| price_type | 价格类型(limit/market) | "limit" |

## 🛡️ 安全建议

1. **模拟盘测试**：首次使用前请在模拟盘充分测试
2. **参数验证**：确保配置参数正确无误
3. **风险控制**：设置合理的交易数量和金额
4. **日志监控**：定期检查交易日志
5. **网络稳定**：确保网络连接稳定

## 📈 扩展功能

### 1. 自定义交易逻辑

可以重写 `buy_event` 和 `sell_event` 方法实现自定义交易逻辑：

```python
def custom_buy_event(self, params):
    # 自定义买入逻辑
    stock = params.get('stock')
    position = params.get('position')
    
    # 例如：根据持仓情况决定是否买入
    if position is None:
        # 无持仓时买入
        return {'size': 100, 'price': stock.get('price'), 'type': '限价'}
    else:
        # 有持仓时不买入
        return None
```

### 2. 集成其他通知方式

除了企业微信，还可以集成其他通知方式：

```python
# 邮件通知
def send_email_notification(subject, content):
    # 实现邮件发送逻辑
    pass

# 短信通知
def send_sms_notification(content):
    # 实现短信发送逻辑
    pass
```

## 🤝 集成优势

1. **简化API调用**：EasyXT封装了复杂的xtquant接口
2. **统一错误处理**：提供一致的错误处理机制
3. **配置化管理**：通过配置文件管理所有参数
4. **日志记录**：完整的交易日志记录
5. **易于扩展**：模块化设计，便于功能扩展

## 📞 技术支持

如有问题，请联系：

- 查看EasyXT项目文档
- 提交GitHub Issue
- 加入交流群讨论

---

**免责声明**：本集成方案仅供学习和研究使用，不构成投资建议。使用本方案进行实际交易的风险由用户自行承担。