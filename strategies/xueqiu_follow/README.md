# 🎯 雪球跟单系统3.0

> 基于EasyXT框架的智能雪球大V组合跟单策略系统

## 📋 项目简介

雪球跟单系统3.0是一个专为量化交易设计的智能跟单策略系统，能够实时监控雪球平台上知名投资者的组合调仓动作，并在3秒内同步执行跟单交易。系统集成在EasyXT量化交易框架中，提供完整的GUI操作界面和强大的风险控制功能。

### ✨ 核心特性

- 🚀 **超低延迟**: 雪球调仓信号获取延迟 < 3秒
- 🎯 **多组合支持**: 同时跟踪多个雪球投资组合
- 🛡️ **智能风控**: 止损、仓位限制、黑名单等多重保护
- 🖥️ **友好界面**: 集成GUI管理界面，操作简单直观
- ⚙️ **灵活配置**: 支持跟单比例、风险参数等个性化配置
- 🔄 **实时监控**: 7x24小时实时监控和自动执行
- 📊 **完整日志**: 详细的交易记录和系统运行日志

## 🏗️ 系统架构

```
雪球跟单系统3.0
├── 数据采集层 (Data Collection)
│   ├── 雪球API接口
│   ├── 组合持仓监控
│   └── 调仓信号检测
├── 策略引擎层 (Strategy Engine)
│   ├── 跟单策略计算
│   ├── 多组合信号合并
│   └── 目标仓位生成
├── 风险管理层 (Risk Management)
│   ├── 仓位限制检查
│   ├── 止损机制
│   └── 黑名单过滤
├── 交易执行层 (Trade Execution)
│   ├── QMT交易接口
│   ├── 订单管理
│   └── 执行结果跟踪
└── 用户界面层 (User Interface)
    ├── 主控制面板
    ├── 配置管理界面
    └── 实时监控显示
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- EasyXT量化交易框架
- 迅投QMT交易软件
- Windows 10+ 操作系统

### 安装步骤

重要：安装“xtquant 特殊版本”（不要用 pip 官方最新版）
- 发布页：https://github.com/quant-king299/EasyXT/releases/tag/xueqiu_follow-xtquant-v1.0
- 若发布页提供 .whl 包：例如 `pip install C:\Path\To\xtquant-*.whl`
- 若提供解压目录（包含 xtquant 包）：解压到如 `C:\xtquant_special`，并设置环境变量，重开终端生效：
  - PowerShell：`setx XTQUANT_PATH "C:\\xtquant_special"`
  - 本仓库的 `strategies/jq2qmt/run_qka_server.py` 会自动把 `XTQUANT_PATH` 注入 sys.path

安装本地源码包（可编辑安装，便于开发调试）：
```powershell
cd "c:\Users\Administrator\Desktop\miniqmt扩展"
pip install -e .\easy_xt
pip install -e .\jq2qmt_adapter
```


1. **克隆项目到EasyXT策略目录**
   ```bash
   cd your_easyxt_path/strategies/
   git clone https://github.com/your-repo/xueqiu_follow.git
   ```

2. **安装依赖包**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置系统参数**
   ```bash
   # 编辑配置文件
   nano xueqiu_follow/config/unified_config.json
   ```

4. **启动系统**
   ```bash
   python xueqiu_follow/main.py
   ```

### qka 启动方式（推荐）

```powershell
cd "c:\Users\Administrator\Desktop\miniqmt扩展"
python strategies\jq2qmt\run_qka_server.py --account YOUR_ACCOUNT_ID --mini-qmt-path "C:\\Path\\To\\miniQMT" --host 127.0.0.1 --port 8000
# 如需自定义 Token：追加 --token YOUR_TOKEN
```

### 基础配置

#### 1. 账户配置 (config/unified_config.json)
```json
{
  "settings": {
    "account": {
      "qmt_path": "C:/QMT/",
      "account_id": "your_account_id",
      "password": "your_encrypted_password"
    },
    "risk": {
      "max_position_ratio": 0.1,
      "stop_loss_ratio": 0.05,
      "max_total_exposure": 0.8
    }
  }
}
```

#### 2. 组合配置 (config/unified_config.json)
```json
{
  "portfolios": {
    "portfolios": [
      {
        "name": "价值投资组合",
        "code": "ZH123456",
        "follow_ratio": 0.4,
        "enabled": true
      }
    ]
  }
}
```

## 📖 使用指南

### 1. 启动系统

运行主程序后，系统会自动打开GUI管理界面：

```bash
python strategies/xueqiu_follow/main.py
```

### 2. 配置组合

在GUI界面中：
- 点击"配置"按钮打开配置对话框
- 添加要跟踪的雪球组合代码
- 设置跟单比例（如0.4表示用40%资金跟单）
- 配置风险控制参数

### 3. 开始跟单

- 点击"启动"按钮开始监控
- 系统会实时显示组合状态和跟单进度
- 发生调仓时会自动执行交易并记录日志

### 4. 监控管理

- 实时查看跟单状态和持仓情况
- 查看交易记录和系统日志
- 随时调整配置参数或停止跟单

## ⚙️ 高级配置

### 风险控制参数

| 参数名称 | 说明 | 默认值 | 建议范围 |
|---------|------|--------|----------|
| max_position_ratio | 单股最大仓位比例 | 0.1 | 0.05-0.2 |
| stop_loss_ratio | 止损比例 | 0.05 | 0.03-0.1 |
| max_total_exposure | 最大总仓位 | 0.8 | 0.6-0.9 |
| check_interval | 监控间隔(秒) | 30 | 10-60 |

### 多组合跟单策略

支持两种多组合跟单方式：

1. **单实例多组合**: 在一个程序中配置多个组合，系统自动合并信号
2. **多实例单组合**: 运行多个程序实例，每个跟踪不同组合和比例

示例配置：
```json
{
  "portfolios": [
    {
      "name": "成长股组合",
      "code": "ZH111111",
      "follow_ratio": 0.3,
      "enabled": true
    },
    {
      "name": "价值股组合", 
      "code": "ZH222222",
      "follow_ratio": 0.2,
      "enabled": true
    }
  ]
}
```

## 🛡️ 安全特性

### 数据安全
- 账户密码加密存储
- 敏感配置文件权限控制
- 交易日志完整记录

### 交易安全
- 多重风险检查机制
- 异常情况自动停止
- 交易前资金验证

### 系统安全
- 异常恢复机制
- 网络连接重试
- 故障自动报警

## 📊 监控和日志

### 实时监控
- 组合持仓变化监控
- 交易执行状态跟踪
- 系统运行状态显示
- 风险指标实时计算

### 日志系统
- 详细的操作日志记录
- 交易记录完整保存
- 异常情况自动记录
- 支持日志文件轮转

### 性能指标
- 数据获取延迟统计
- 交易执行时间记录
- 系统资源使用监控
- 跟单准确率统计

## 🔧 故障排除

### 常见问题

**Q: 无法获取雪球数据**
```
A: 检查网络连接和雪球组合代码是否正确
   确认组合是公开可访问的
   检查是否被反爬虫机制限制
```

**Q: QMT连接失败**
```
A: 确认QMT软件正常运行
   检查账户配置是否正确
   验证交易权限是否开通
```

**Q: 交易执行失败**
```
A: 检查账户资金是否充足
   确认股票是否停牌或涨跌停
   查看风险控制是否触发
```

### 日志分析

系统日志位置：`logs/xueqiu_follow.log`

重要日志关键词：
- `ERROR`: 系统错误，需要立即处理
- `WARNING`: 警告信息，建议关注
- `TRADE`: 交易相关日志
- `RISK`: 风险控制触发日志

## 🤝 贡献指南

### 开发环境搭建

1. Fork项目仓库
2. 创建功能分支
3. 安装开发依赖
4. 运行测试用例
5. 提交Pull Request

### 代码规范

- 遵循PEP8编码规范
- 使用类型提示增强代码可读性
- 编写完整的文档字符串
- 添加必要的单元测试

### 测试

```bash
# 运行单元测试
python -m pytest tests/ -v

# 代码质量检查
python -m flake8 . --max-line-length=88
python -m black . --check

# 类型检查
python -m mypy .
```

## 📄 许可证

本项目采用MIT许可证，详见 [LICENSE](LICENSE) 文件。

## 📞 支持与反馈

- 📧 邮箱: support@example.com
- 🐛 问题反馈: [GitHub Issues](https://github.com/your-repo/xueqiu_follow/issues)
- 📖 文档: [项目Wiki](https://github.com/your-repo/xueqiu_follow/wiki)
- 💬 讨论: [GitHub Discussions](https://github.com/your-repo/xueqiu_follow/discussions)

## 🎯 路线图

### v3.1 (计划中)
- [ ] 支持更多数据源
- [ ] 增加回测功能
- [ ] 优化GUI界面
- [ ] 添加移动端支持

### v3.2 (规划中)
- [ ] 机器学习信号优化
- [ ] 云端配置同步
- [ ] 多账户管理
- [ ] API接口开放

---

**⚠️ 风险提示**: 本系统仅供学习和研究使用，投资有风险，使用前请充分了解相关风险并谨慎决策。

**📈 让智能跟单为您的投资保驾护航！**