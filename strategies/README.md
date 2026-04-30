# 策略中心

基于 miniQMT + EasyXT 的本地量化交易策略集合。每个策略都可以独立运行。

---

## 策略一览

| 策略 | 类型 | 说明 | 实盘 | 难度 |
|------|------|------|:----:|:----:|
| [小市值选股](./小市值基础策略_使用指南.md) | 选股 | 按市值排序筛选小盘股，定期轮仓 | ✅ | ⭐⭐ |
| [网格交易](./grid_trading/README.md) | 自动化 | 固定/ATR动态/自适应三种网格模式 | ✅ | ⭐ |
| [雪球跟单](./xueqiu_follow/README.md) | 跟单 | 跟踪雪球大V组合，自动同步调仓 | ✅ | ⭐⭐ |
| [通达信预警交易](./tdxtrader/README.md) | 触发型 | 读取通达信预警信号自动下单 | ✅ | ⭐⭐ |
| [双均线趋势](./trend_following/双均线策略.py) | 趋势 | 经典快慢均线交叉策略 | ✅ | ⭐ |
| [止损止盈](./conditional_orders/止损止盈.py) | 风控 | 自动止损止盈条件单 | ✅ | ⭐ |
| [可转债回测](../101因子/101因子分析平台/) | 回测 | 可转债双低策略本地回测 | ❌ | ⭐⭐⭐ |
| [101因子分析](../101因子/101因子分析平台/) | 因子 | 101个Alpha因子分析Web平台 | ❌ | ⭐⭐⭐ |

---

## 新手推荐路径

```
第1步：双均线趋势        → 最简单，理解策略框架
第2步：网格交易          → 实用性强，适合震荡市
第3步：小市值选股        → 进阶，学习选股+轮仓逻辑
```

---

## 策略详情

### 小市值选股
从指数成分股中筛选市值最小的N只股票，定期调仓。有V1（纯回测）和V2（回测+实盘）两个版本。

- **文件**: `小市值基础策略V2.py` / `小市值基础策略V2_QMT版.py`
- **数据源**: Tushare 或 miniQMT 本地数据
- **核心逻辑**: 市值排序 → 排除ST/停牌 → 等权买入 → 定期轮换

### 网格交易
支持三种网格模式，适合ETF和低波动品种：

| 模式 | 特点 | 配置文件 |
|------|------|---------|
| 固定网格 | 价格间隔固定，简单直观 | `fixed_grid_config.json` |
| ATR动态网格 | 根据ATR自动调整网格间距 | `atr_grid_config.json` |
| 自适应网格 | 根据市场波动自动切换参数 | `adaptive_grid_config.json` |

- **一键启动**: `启动固定网格测试.bat` / `启动ATR网格测试.bat` / `启动自适应网格测试.bat`
- **详细文档**: [grid_trading/README.md](./grid_trading/README.md)

### 雪球跟单
跟踪雪球平台大V的投资组合，自动同步调仓到miniQMT实盘。

- **一键启动**: `xueqiu_follow/启动雪球跟单.bat`
- **前置条件**: 需要配置雪球Cookie（详见 [Cookie配置指南](./xueqiu_follow/雪球Cookie快速配置.md)）

### 通达信预警交易
将通达信的技术指标预警信号转化为自动交易指令，支持个股预警和板块预警。

- **核心机制**: 通达信预警文件 → 解析信号 → EasyXT下单
- **双重保障**: EasyXT + xt_trader 双通道下单

---

## 快速开始

```bash
# 1. 确保miniQMT已启动并登录

# 2. 运行一个策略（以双均线为例）
python strategies/trend_following/双均线策略.py

# 3. 运行网格交易（带配置文件）
python strategies/grid_trading/run_fixed_grid.py
```

---

## 策略开发模板

所有策略继承 `BaseStrategy` 基类：

```python
from strategies.base.strategy_template import BaseStrategy

class MyStrategy(BaseStrategy):
    def calculate_signals(self):
        # 实现你的策略逻辑
        pass
```

详见 [策略基类模板](./base/strategy_template.py)。
