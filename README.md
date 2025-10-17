# MiniQMT扩展 - 量化交易工具包

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![QMT](https://img.shields.io/badge/QMT-Compatible-orange.svg)](https://www.gtja.com/)

一个基于迅投QMT的量化交易扩展工具包，提供简化的API接口和丰富的学习实例。

## 🚀 特性

- **简化API**: 封装复杂的QMT接口，提供易用的Python API
- **真实交易**: 支持通过EasyXT接口进行真实股票交易
- **数据获取**: 集成qstock、akshare等多种数据源
- **技术指标**: 内置常用技术指标计算
- **策略开发**: 提供完整的量化策略开发框架
- **学习实例**: 丰富的教学案例，从入门到高级

## 📦 安装

### 环境要求

- Python 3.7+
- 迅投QMT客户端
- Windows系统（QMT限制）

### 依赖安装

```bash
pip install pandas numpy matplotlib requests
pip install qstock  # 可选，用于股票数据获取
pip install akshare  # 可选，用于金融数据获取
```

### 项目安装

```bash
git clone https://github.com/quant-king299/EasyXT.git
cd EasyXT
```

## 🔧 配置

### 1. QMT客户端配置

1. 安装并启动迅投QMT客户端
2. 登录您的交易账户
3. 记录userdata路径（通常在QMT安装目录下）

### 2. 项目配置

复制配置模板并修改：

```bash
cp config/config_template.py config/config.py
```

编辑 `config/config.py`：

```python
# QMT配置
USERDATA_PATH = r'D:\QMT\userdata_mini'  # 修改为您的实际路径
ACCOUNT_ID = "您的资金账号"

# 数据源配置
USE_QSTOCK = True
USE_AKSHARE = True

# 交易配置
ENABLE_REAL_TRADING = False  # 生产环境设为True
MAX_POSITION_RATIO = 0.3     # 最大持仓比例
```

## 📚 快速开始

### 基础数据获取

```python
from easy_xt import EasyXT

# 创建API实例
api = EasyXT()

# 初始化数据服务
api.init_data()

# 获取股票价格
data = api.get_price('000001.SZ', count=100)
print(data.head())
```

### 简单交易示例

```python
# 初始化交易服务
api.init_trade(USERDATA_PATH)
api.add_account(ACCOUNT_ID)

# 买入股票
order_id = api.buy(
    account_id=ACCOUNT_ID,
    code='000001.SZ',
    volume=100,
    price_type='market'
)
```

### 运行学习实例

```bash
# 基础入门
python 学习实例/01_基础入门.py

# 交易基础
python 学习实例/02_交易基础.py

# 高级交易
python 学习实例/03_高级交易.py

# 策略开发
python 学习实例/04_策略开发.py
```

## 📖 学习路径

### 初学者路径

1. **01_基础入门.py** - 学习基本的数据获取和API使用
2. **02_交易基础.py** - 掌握基础交易操作
3. **05_数据周期详解.py** - 了解不同数据周期的使用

### 进阶路径

4. **03_高级交易.py** - 学习高级交易功能
5. **04_策略开发.py** - 开发量化交易策略
6. **06_扩展API学习实例.py** - 掌握扩展功能

### 实战路径

7. **07_qstock数据获取学习案例.py** - 真实数据获取
8. **08_数据获取与交易结合案例.py** - 数据与交易结合
9. **10_qstock真实数据交易案例_修复交易服务版.py** - 完整实战案例

## 🏗️ 项目结构

```
miniqmt扩展/
├── easy_xt/                    # 核心API模块
│   ├── __init__.py
│   ├── api.py                  # 主API接口
│   ├── data_api.py            # 数据接口
│   ├── trade_api.py           # 交易接口
│   ├── advanced_trade_api.py  # 高级交易接口
│   └── utils.py               # 工具函数
├── 学习实例/                   # 学习案例
│   ├── 01_基础入门.py
│   ├── 02_交易基础.py
│   ├── 03_高级交易.py
│   └── ...
├── config/                     # 配置文件
│   ├── config_template.py
│   └── config.py
├── data/                       # 数据存储目录
├── logs/                       # 日志目录
├── xtquant/                    # QMT相关文件
├── gui_app/                    # GUI应用（可选）
├── requirements.txt            # 依赖列表
├── README.md                   # 项目说明
└── .gitignore                  # Git忽略文件
```

## ⚠️ 风险提示

1. **投资风险**: 量化交易存在投资风险，请谨慎操作
2. **测试环境**: 建议先在模拟环境中测试策略
3. **资金管理**: 合理控制仓位，设置止损止盈
4. **合规要求**: 遵守相关法律法规和交易所规则

## 🤝 贡献

欢迎提交Issue和Pull Request！

### 开发指南

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [迅投QMT](https://www.gtja.com/) - 提供量化交易平台
- [qstock](https://github.com/tkfy920/qstock) - 股票数据获取
- [akshare](https://github.com/akfamily/akshare) - 金融数据接口

## 📞 联系方式

- 项目主页: https://github.com/quant-king299/EasyXT
- 问题反馈: https://github.com/quant-king299/EasyXT/issues
- 邮箱: quant-king299@example.com

## 📈 更新日志

### v1.0.0 (2025-01-11)
- 初始版本发布
- 完整的EasyXT API封装
- 丰富的学习实例
- 修复交易服务初始化问题

---

**免责声明**: 本项目仅供学习和研究使用，不构成投资建议。使用本项目进行实际交易的风险由用户自行承担。