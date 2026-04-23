# EasyXT 项目架构详细说明

> **文档版本**：v1.0
> **更新日期**：2026-03-17
> **适用对象**：开发者、新用户
> **文档类型**：架构规范与使用指南

---

## 📋 目录

- [1. 项目概述](#1-项目概述)
- [2. 架构分层](#2-架构分层)
- [3. 核心模块详解](#3-核心模块详解)
- [4. 数据流与调用关系](#4-数据流与调用关系)
- [5. 配置系统](#5-配置系统)
- [6. 路径管理](#6-路径管理)
- [7. 主要功能模块](#7-主要功能模块)
- [8. 开发指南](#8-开发指南)
- [9. 快速开始](#9-快速开始)
- [10. 常见使用场景](#10-常见使用场景)

---

## 1. 项目概述

### 1.1 项目定位

**EasyXT** 是一套**模块化的量化交易工具集**，不是单一框架。

**核心理念**：按需选用，低耦合，清晰边界

**主要能力**：
- 🎯 QMT交易API封装（简化使用）
- 💻 策略开发与回测
- 📊 多数据源支持（TDX、EastMoney、Tushare等）
- 🤖 自动化交易执行
- 📈 因子分析与回测
- 🌐 雪球组合跟单

### 1.2 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.9+ | 主要开发语言 |
| QMT/miniQMT | 最新 | 交易通道 |
| Streamlit | 最新 | Web应用（101因子平台） |
| Pandas | 最新 | 数据处理 |
| SQLite/DuckDB | 最新 | 数据存储 |

---

## 2. 架构分层

### 2.1 三层架构

```
┌─────────────────────────────────────────────────────────────┐
│                      应用层 (Application Layer)              │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ strategies/ │  │ 101因子平台   │  │   gui_app/       │   │
│  │  交易策略   │  │ (因子分析)    │  │  (GUI应用)       │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓ 依赖
┌─────────────────────────────────────────────────────────────┐
│                       核心层 (Core Layer)                    │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ core/config │  │core/alpha_   │  │ core/data_       │   │
│  │ (配置管理)   │  │analysis/     │  │ manager/         │   │
│  │             │  │(因子分析)     │  │ (数据管理)        │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓ 依赖
┌─────────────────────────────────────────────────────────────┐
│                    基础层 (Foundation Layer)                │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  easy_xt/   │  │  qstock/     │  │   xtquant/       │   │
│  │ (API封装)    │  │ (数据源)      │  │  (QMT原生API)    │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 依赖关系（单向）

```
应用层 → 核心层 → 基础层
  ↓         ↓         ↓
strategies → core → easy_xt → QMT API
101因子平台 → core → easy_xt → QMT API
gui_app → core → easy_xt → QMT API
```

**关键规则**：
- ✅ 单向依赖，无循环
- ✅ 上层可以调用下层
- ❌ 下层不能调用上层
- ❌ 同层之间不直接依赖

---

## 3. 核心模块详解

### 3.1 基础层模块

#### 📦 easy_xt/

**定位**：QMT API的轻量级封装，提供简洁的Python接口

**核心文件**：
```
easy_xt/
├── __init__.py              # 统一API导出
├── api.py                   # 主API接口（账户、持仓查询）
├── data_api.py              # 数据接口（行情、K线）
├── trade_api.py             # 交易接口（下单、撤单）
├── advanced_trade_api.py    # 高级交易接口（批量操作）
├── config.py                # QMT路径配置
├── load_config.py           # 统一配置加载
├── realtime_data/           # 实时行情模块
│   ├── config.py            # 实时数据配置
│   ├── config_manager.py    # 配置管理器
│   └── ...
└── cli/                     # 命令行工具
```

**主要功能**：
```python
from easy_xt import (
    get_account,        # 获取账户信息
    get_position,       # 获取持仓
    get_full_tick,      # 获取五档行情
    download_history_kline,  # 下载历史K线
    order_stock,        # 下单
    cancel_order,       # 撤单
)

# 示例：获取账户信息
account = get_account()
print(f"账户资产: {account['asset']}")

# 示例：下单
result = order_stock('600036.SH', 'buy', 100, price=10.5)
```

**独立性**：✅ 可独立使用，无需其他模块

---

#### 📊 qstock/ (第三方库)

**定位**：多数据源封装（TDX、EastMoney、Tushare等）

**主要功能**：
- 提供统一的数据获取接口
- 支持多数据源自动切换
- 缓存机制提高性能

---

### 3.2 核心层模块

#### ⚙️ core/config/

**定位**：统一配置管理模块（新增）

**核心文件**：
```
core/config/
├── __init__.py           # 模块导出
├── config_manager.py     # 统一配置管理器
├── config_path.py        # 配置路径管理
├── test_config_manager.py # 测试脚本
└── README.md            # 使用文档
```

**主要功能**：
```python
from core.config import get_config, set_config

# 获取配置
timeout = get_config("data_providers.tdx.timeout", 30)

# 设置配置
set_config("logging.level", "DEBUG")
```

**特性**：
- ✅ 支持配置层级（系统、用户、运行时）
- ✅ 支持嵌套键访问（`data_providers.tdx.timeout`）
- ✅ 支持环境变量（`EASYXT_CONFIG_PATH`）
- ✅ 线程安全
- ✅ 自动保存

---

#### 📈 core/alpha_analysis/

**定位**：因子分析工具（从easy_xt迁移到core）

**核心文件**：
```
core/alpha_analysis/
├── __init__.py
├── ic_analysis.py        # IC/IR分析
├── layered_backtest.py   # 分层回测
├── correlation.py        # 因子相关性分析
└── README.md
```

**主要功能**：
```python
from core.alpha_analysis import ICAnalyzer, LayeredBacktester

# IC/IR分析
analyzer = ICAnalyzer()
result = analyzer.calculate_ic(factor_data, price_data)

# 分层回测
backtester = LayeredBacktester()
result = backtester.run_layered_backtest(factor_data, returns)
```

---

#### 💾 core/data_manager/

**定位**：统一数据管理接口

**主要功能**：
- 多数据源管理
- 数据缓存
- 统一数据接口

---

### 3.3 应用层模块

#### 📁 strategies/ - 交易策略集合

**雪球跟单** (`xueqiu_follow/`)
```
strategies/xueqiu_follow/
├── start_xueqiu_follow_easyxt.py    # 启动脚本
├── config/
│   └── unified_config.json           # 统一配置文件
├── internal/                         # 内部模块
│   ├── config_manager.py             # 配置管理器
│   ├── strategy_engine.py            # 策略引擎
│   ├── trade_executor.py             # 交易执行器
│   ├── xueqiu_collector_real.py      # 雪球数据采集器
│   └── risk_manager.py               # 风险管理
├── utils/                            # 工具函数
│   ├── logger.py                     # 日志工具
│   └── rate_limiter.py               # 限流器
└── README.md
```

**网格交易** (`grid_trading/`)
```
strategies/grid_trading/
├── README.md                         # 使用说明
├── run_*.py                          # 启动脚本
├── config/                           # 配置目录
└── *.py                              # 策略实现
```

**聚宽转QMT** (`jq2qmt/`)
**通达信预警交易** (`tdxtrader/`)

---

#### 📊 101因子/101因子分析平台/

**定位**：基于Streamlit的因子分析Web应用

**架构**：
```
101因子/101因子分析平台/
├── main_app.py                       # Streamlit主应用
├── src/
│   ├── workflow/                     # 工作流模块
│   │   ├── nodes/                    # 工作流节点
│   │   ├── engine.py                 # 工作流引擎
│   │   └── *.py                      # 各功能页面
│   ├── factor_engine/                # 因子引擎
│   ├── data_manager/                 # 数据管理
│   └── easyxt_adapter/               # EasyXT适配器
└── data/                             # 数据存储
```

**主要功能**：
- 191个Alpha因子计算
- IC/IR分析
- 分层回测
- 因子相关性分析
- 因子组合优化

---

#### 🖥️ gui_app/

**定位**：桌面GUI应用

**主要功能**：
- 策略管理
- 实时行情监控
- 交易界面

---

## 4. 数据流与调用关系

### 4.1 典型的数据流（雪球跟单）

```
用户启动
    ↓
start_xueqiu_follow_easyxt.py
    ↓
初始化路径管理 (core.path_manager)
    ↓
加载配置 (internal.config_manager)
    ↓
初始化雪球采集器 (internal.xueqiu_collector_real)
    ↓
  [网络请求] 雪球API (获取持仓数据)
    ↓
计算目标仓位 (internal.strategy_engine)
    ↓
生成交易指令 (internal.strategy_engine)
    ↓
风险检查 (internal.risk_manager)
    ↓
执行交易 (internal.trade_executor)
    ↓
  [API调用] EasyXT → QMT (下单/撤单)
    ↓
导出报告 (reports/*.xlsx)
```

### 4.2 模块调用关系

```
┌──────────────────────────────────────────────────────────┐
│  启动脚本 (start_xueqiu_follow_easyxt.py)               │
│  - 初始化路径                                           │
│  - 加载配置                                             │
│  - 启动主程序                                           │
└──────────────────────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────────────────┐
│  策略引擎 (StrategyEngine)                               │
│  - 管理策略生命周期                                       │
│  - 计算目标仓位                                           │
│  - 生成交易指令                                           │
└──────────────────────────────────────────────────────────┘
        ↓ 调用
┌──────────────────┬──────────────────┬──────────────────┐
│  数据采集器       │  交易执行器       │  风险管理器       │
│  (Collector)      │  (TradeExecutor) │  (RiskManager)    │
│  - 获取雪球数据   │  - 执行下单       │  - 风险检查       │
│  - 解析持仓信息   │  - 查询订单状态   │  - 仓位控制       │
└──────────────────┴──────────────────┴──────────────────┘
        ↓                   ↓                   ↓
┌──────────────────────────────────────────────────────────┐
│  EasyXT API                                             │
│  - 连接QMT                                              │
│  - 账户查询                                             │
│  - 下单交易                                             │
└──────────────────────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────────────────┐
│  QMT/miniQMT (交易通道)                                  │
└──────────────────────────────────────────────────────────┘
```

---

## 5. 配置系统

### 5.1 配置文件层级

```
全局配置 (项目级)
├── config/
│   └── unified_config.json        # 全局统一配置
│
策略级配置
├── strategies/xueqiu_follow/config/
│   └── unified_config.json        # 雪球跟单配置
│
用户配置
└── ~/.miniqmt/config.json         # 用户本地配置（可选）
```

### 5.2 配置文件结构（雪球跟单示例）

```json
{
  "version": "3.0",
  "system": {
    "qmt": {
      "session_id": "xueqiu_follow",
      "api_type": "easyxt"
    }
  },
  "xueqiu_settings": {
    "cookie": "xq_a_token=xxxx; xq_is_login=1",
    "cookie_status": "enabled"
  },
  "portfolios": {
    "portfolios": [
      {
        "code": "ZH3331011",
        "name": "雪球组合ZH3331011",
        "follow_ratio": 0.02,
        "enabled": true
      }
    ]
  },
  "settings": {
    "follow_mode": {
      "mode": "smart_follow"
    },
    "risk_control": {
      "max_position_ratio": 0.1
    }
  }
}
```

### 5.3 统一配置管理器

**位置**：`core/config/config_manager.py`

**使用方式**：
```python
# 方式1：使用便捷函数
from core.config import get_config, set_config

timeout = get_config("data_providers.tdx.timeout", 30)
set_config("logging.level", "DEBUG")

# 方式2：使用配置管理器
from core.config import UnifiedConfigManager

config = UnifiedConfigManager()
timeout = config.get("data_providers.tdx.timeout")
config.set("logging.level", "DEBUG")
```

---

## 6. 路径管理

### 6.1 统一路径管理器

**问题**：项目中有275处 `sys.path.insert()` 重复代码

**解决方案**：`core/path_manager.py`

**使用方式**：
```python
from core.path_manager import init_paths, get_project_root

# 初始化路径（幂等性，多次调用只生效一次）
init_paths()

# 获取项目根目录
root = get_project_root()
```

**特性**：
- ✅ 自动检测项目根目录
- ✅ 一次性设置所有需要的路径
- ✅ 幂等性设计（多次调用不重复添加）
- ✅ 便捷的路径获取函数

**提供的函数**：
```python
from core.path_manager import (
    get_project_root,        # 获取项目根目录
    get_path,                # 获取相对路径
    get_config_path,         # 获取配置文件路径
    get_xueqiu_config_path,  # 获取雪球配置路径
    get_reports_path,        # 获取报告目录
    get_logs_path,           # 获取日志目录
)
```

---

## 7. 主要功能模块

### 7.1 数据管理

**支持的类型**：
- 实时行情（五档盘口、Tick数据）
- 历史K线（日K、分钟K）
- 财务数据
- 持仓数据

**数据源优先级**：
```
QMT本地数据 → TDX → EastMoney → Tushare
```

### 7.2 交易执行

**支持的操作**：
- 买入股票
- 卖出股票
- 撤单
- 查询订单
- 查询持仓
- 查询账户资产

**风险控制**：
- 单只股票最大仓位
- 单日最大交易金额
- 交易前风险检查

### 7.3 策略类型

| 策略类型 | 说明 | 文件位置 |
|---------|------|---------|
| 雪球跟单 | 跟随雪球组合调仓 | `strategies/xueqiu_follow/` |
| 网格交易 | 自动网格交易 | `strategies/grid_trading/` |
| 聚宽转QMT | 聚宽策略转QMT执行 | `strategies/jq2qmt/` |
| 自定义策略 | 用户自行开发 | `strategies/custom/` |

---

## 8. 开发指南

### 8.1 开发新策略

**步骤**：

1. **创建策略目录**
```bash
mkdir strategies/my_strategy
cd strategies/my_strategy
```

2. **创建策略文件**
```python
# strategies/my_strategy/main.py

from core.path_manager import init_paths
from easy_xt import get_account, order_stock

# 初始化路径
init_paths()

class MyStrategy:
    def __init__(self):
        self.account = get_account()

    def run(self):
        # 策略逻辑
        pass

if __name__ == "__main__":
    strategy = MyStrategy()
    strategy.run()
```

3. **创建配置文件**
```json
// strategies/my_strategy/config.json
{
  "strategy_name": "我的策略",
  "symbols": ["600036.SH", "000001.SZ"],
  "params": {
    "param1": "value1"
  }
}
```

### 8.2 使用EasyXT API

**导入方式**：
```python
# 方式1：导入常用API
from easy_xt import (
    get_account,
    get_position,
    order_stock,
    cancel_order
)

# 方式2：导入特定模块
from easy_xt import data_api, trade_api

# 方式3：导入所有API
from easy_xt import *
```

**常用操作**：
```python
# 1. 获取账户信息
account = get_account()
print(f"总资产: {account['asset']}")
print(f"可用资金: {account['cash']}")

# 2. 获取持仓
positions = get_position()
for pos in positions:
    print(f"{pos['stock_code']}: {pos['volume']}股")

# 3. 获取实时行情
tick = get_full_tick('600036.SH')
print(f"买一: {tick['bid1']} @ {tick['bid1_vol']}")
print(f"卖一: {tick['ask1']} @ {tick['ask1_vol']}")

# 4. 下单
result = order_stock('600036.SH', 'buy', 100, price=10.5)
print(f"订单ID: {result['order_id']}")

# 5. 撤单
result = cancel_order(order_id)
```

### 8.3 调试技巧

**查看日志**：
```bash
# 实时查看日志
tail -f strategies/xueqiu_follow/logs/xueqiu_follow.log
```

**启用调试模式**：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**使用pdb调试**：
```python
import pdb; pdb.set_trace()
```

---

## 9. 快速开始

### 9.1 环境准备

**安装Python**：
```bash
# 确保Python版本 >= 3.9
python --version
```

**安装依赖**：
```bash
pip install -r requirements.txt
```

### 9.2 启动雪球跟单

**1. 配置Cookie**：
- 打开 `strategies/xueqiu_follow/config/unified_config.json`
- 配置 `xueqiu_settings.cookie` 字段

**2. 配置跟单组合**：
- 在 `portfolios.portfolios` 中添加雪球组合代码
- 设置 `follow_ratio` 跟随比例

**3. 启动**：
```bash
# Windows
双击：启动雪球跟单-简化的.bat

# 命令行
cd strategies/xueqiu_follow
python start_xueqiu_follow_easyxt.py
```

### 9.3 使用101因子平台

**启动Web应用**：
```bash
cd 101因子/101因子分析平台
streamlit run main_app.py
```

**访问**：
- 浏览器打开：`http://localhost:8501`

---

## 10. 常见使用场景

### 10.1 场景1：开发简单策略

**需求**：每天9:30买入固定股票

**实现**：
```python
# strategies/simple_daily_buy/main.py
from core.path_manager import init_paths
from easy_xt import order_stock, get_account
import schedule
import time

init_paths()

def daily_buy():
    """每天买入"""
    result = order_stock('600036.SH', 'buy', 100)
    print(f"下单成功: {result}")

if __name__ == "__main__":
    # 每天9:30执行
    schedule.every().day.at("09:30").do(daily_buy)

    while True:
        schedule.run_pending()
        time.sleep(60)
```

### 10.2 场景2：数据获取与回测

**需求**：获取历史数据并回测策略

**实现**：
```python
from core.path_manager import init_paths
from easy_xt import download_history_kline
import pandas as pd

init_paths()

# 1. 下载数据
df = download_history_kline(
    stock_code='600036.SH',
    period='1d',
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# 2. 编写策略
def strategy(df):
    # 简单的双均线策略
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['signal'] = (df['ma5'] > df['ma20']).astype(int)
    return df

# 3. 回测
result = strategy(df)
print(result[['date', 'close', 'signal']].tail())
```

### 10.3 场景3：监控持仓变化

**需求**：实时监控持仓变化

**实现**：
```python
from core.path_manager import init_paths
from easy_xt import get_position
import time

init_paths()

last_positions = {}

def monitor_positions():
    """监控持仓变化"""
    global last_positions

    # 获取当前持仓
    positions = get_position()
    current_positions = {p['stock_code']: p['volume'] for p in positions}

    # 对比变化
    for code, volume in current_positions.items():
        if code not in last_positions:
            print(f"[新增] {code}: {volume}股")
        elif volume != last_positions[code]:
            change = volume - last_positions[code]
            print(f"[变化] {code}: {change}股 ({last_positions[code]} -> {volume})")

    last_positions = current_positions

if __name__ == "__main__":
    while True:
        monitor_positions()
        time.sleep(10)  # 每10秒检查一次
```

---

## 附录

### A. 项目目录结构（完整版）

```
EasyXT/                          # 项目根目录（从 GitHub 下载后的文件夹名）
├── core/                          # 核心层
│   ├── __init__.py
│   ├── path_manager.py            # 统一路径管理 ✨
│   ├── config/                    # 配置管理 ✨
│   │   ├── config_manager.py
│   │   ├── config_path.py
│   │   └── README.md
│   ├── alpha_analysis/            # 因子分析 ✨
│   │   ├── ic_analysis.py
│   │   ├── layered_backtest.py
│   │   └── correlation.py
│   ├── data_manager/              # 数据管理
│   └── tests/                     # 测试
│       └── test_path_manager.py
│
├── easy_xt/                       # 基础层（API封装）
│   ├── __init__.py
│   ├── api.py
│   ├── data_api.py
│   ├── trade_api.py
│   ├── advanced_trade_api.py
│   ├── config.py
│   ├── load_config.py
│   ├── realtime_data/
│   └── cli/
│
├── strategies/                    # 应用层（策略）
│   ├── xueqiu_follow/             # 雪球跟单
│   │   ├── start_xueqiu_follow_easyxt.py
│   │   ├── config/
│   │   │   └── unified_config.json
│   │   ├── internal/              # 内部模块 ✨
│   │   │   ├── config_manager.py
│   │   │   ├── strategy_engine.py
│   │   │   ├── trade_executor.py
│   │   │   ├── xueqiu_collector_real.py
│   │   │   └── risk_manager.py
│   │   ├── utils/
│   │   │   ├── logger.py
│   │   │   └── rate_limiter.py
│   │   └── README.md
│   ├── grid_trading/              # 网格交易
│   ├── jq2qmt/                    # 聚宽转QMT
│   └── tdxtrader/                 # 通达信预警交易
│
├── 101因子/                       # 应用层（因子分析）
│   └── 101因子分析平台/
│       ├── main_app.py
│       └── src/
│
├── gui_app/                       # GUI应用
│
├── config/                        # 全局配置
│   └── unified_config.json
│
├── docs/                          # 文档
│   └── assets/
│
├── data/                          # 数据存储
│
├── logs/                          # 日志
│
└── ARCHITECTURE.md                # 本文档
```

### B. 关键技术决策

1. **为什么使用三层架构？**
   - 清晰的职责划分
   - 便于维护和扩展
   - 避免循环依赖

2. **为什么雪球跟单有自己的配置管理器？**
   - 专门为雪球业务设计
   - 包含特有的字段和验证
   - 与业务逻辑紧密结合
   - 不影响核心模块的通用性

3. **为什么创建统一路径管理器？**
   - 解决275处重复代码
   - 统一路径管理方式
   - 简化新模块开发

### C. 相关文档

- `REFACTOR_PROGRESS.md` - 重构进度报告
- `ARCHITECTURE_ISSUES.md` - 架构问题分析
- `core/config/README.md` - 配置管理器文档
- `core/PATH_MANAGER_GUIDE.md` - 路径管理器使用指南
- `strategies/xueqiu_follow/README.md` - 雪球跟单使用说明

### D. 更新日志

**v1.0 (2026-03-17)**
- ✅ 初始版本
- ✅ 完成三层架构设计
- ✅ 消除循环依赖
- ✅ 创建统一配置管理器
- ✅ 创建统一路径管理器
- ✅ 完成模块重组

---

**文档维护**：本文档应随项目演进持续更新

**反馈渠道**：如有疑问或建议，请提交Issue或Pull Request
