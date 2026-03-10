# 🚀 5分钟快速开始指南

> ⚠️ **重要提示**：您**不需要预先准备DuckDB数据库文件**也能使用EasyXT！

## 🎯 三种使用方式（任选其一）

### 方式1️⃣：使用QMT本地数据（推荐新手）✅

**最简单！如果您已安装QMT/miniQMT**

```python
from easyxt_backtest import DataManager, BacktestEngine
from easyxt_backtest.strategies import SmallCapStrategy

# 不需要任何参数，自动使用QMT数据
data_manager = DataManager()

# 创建并运行回测
engine = BacktestEngine(initial_cash=1000000, data_manager=data_manager)
strategy = SmallCapStrategy(select_num=5)
result = engine.run_backtest(strategy, '20240101', '20240331')
```

**优点：**
- ✅ 零配置，开箱即用
- ✅ 无需额外下载
- ✅ 速度快

**要求：**
- 已安装QMT/miniQMT

---

### 方式2️⃣：使用Tushare在线数据（需token）

**适合：没有QMT，但能联网**

```python
import os
os.environ['TUSHARE_TOKEN'] = '你的token'  # 从 https://tushare.pro 获取

from easyxt_backtest import DataManager, BacktestEngine

# 自动使用Tushare在线数据
data_manager = DataManager()

# 创建并运行回测
engine = BacktestEngine(initial_cash=1000000, data_manager=data_manager)
# ... 同上
```

**优点：**
- ✅ 无需本地数据库
- ✅ 数据准确
- ✅ 新用户有免费积分（需注册）

**缺点：**
- ⚠️ 需要注册获取token
- ⚠️ 免费积分有限（约1200积分/天）
- ⚠️ 高级数据需要付费或更多积分
- ⚠️ 受网络限制
- ⚠️ 速度较慢

---

### 方式3️⃣：使用DuckDB本地数据库（推荐进阶用户）🚀

**适合：频繁回测，追求极致速度**

#### 步骤1：自动下载DuckDB数据库

我们提供了**一键下载脚本**：

```bash
# Windows PowerShell
cd "C:\Users\Administrator\Desktop\miniqmt扩展"
python tools/download_all_stocks.py
```

或者手动下载特定数据：

```bash
# 下载市值数据（推荐）
python tools/download_market_cap_fast.py

# 下载日线数据
python tools/correct_data_download_usage.py
```

**注意：**
- ⏱️ 首次下载需要时间（取决于数据量）
- 📊 需要Tushare token（免费注册）
- 💾 数据会保存到 `D:/StockData/stock_data.ddb`

#### 步骤2：使用DuckDB数据

```python
from easyxt_backtest import DataManager, BacktestEngine

# 指定DuckDB路径
data_manager = DataManager(duckdb_path='D:/StockData/stock_data.ddb')

# 创建并运行回测
engine = BacktestEngine(initial_cash=1000000, data_manager=data_manager)
# ... 同上
```

**优点：**
- ✅ 极速（比QMT快10倍，比Tushare快100倍）
- ✅ 离线可用
- ✅ 数据完整

**缺点：**
- ⚠️ 需要预先下载
- ⚠️ 占用磁盘空间

---

## 🤔 我该选哪种方式？

| 场景 | 推荐方案 |
|------|---------|
| **新手，第一次使用** | 方式1（QMT数据） |
| **没有QMT，想快速试** | 方式2（Tushare在线） |
| **频繁回测，追求速度** | 方式3（DuckDB） |
| **生产环境，稳定可靠** | 方式3（DuckDB） |

---

## 🔄 数据源优先级（自动fallback）

```
DataManager会自动尝试：

1. DuckDB（如果配置了路径）  ← 最快
2. QMT本地数据                ← 最方便
3. Tushare在线API            ← 最准确

如果某个数据源失败，自动尝试下一个！
```

**示例：**
```python
# 即使没有DuckDB，也能用QMT或Tushare
data_manager = DataManager()  # 智能选择可用数据源

# 或者指定优先级
data_manager = DataManager(
    duckdb_path='D:/StockData/stock_data.ddb'  # 如果有，优先使用
)
# 如果DuckDB不存在，自动fallback到QMT/Tushare
```

---

## ❓ 常见问题

### Q1：我真的不需要DuckDB吗？

**A：** 对！DuckDB只是**可选加速**，不是必须的。

- ❌ **错误理解**：必须先有DuckDB才能用
- ✅ **正确理解**：有DuckDB会更快，没有也能正常用

### Q2：为什么文档里总提到DuckDB？

**A：** 因为DuckDB是最快的方案，适合进阶用户。但新手完全可以从QMT或Tushare开始。

### Q3：下载DuckDB数据需要多久？

**A：** 取决于数据量：

| 数据类型 | 时间 | 说明 |
|---------|------|------|
| 市值数据（1年） | 5-10分钟 | 推荐 |
| 日线数据（全A股1年） | 20-30分钟 | 可选 |
| 完整数据（10年） | 2-3小时 | 一次性下载后永久使用 |

### Q4：我没有Tushare token怎么办？

**A：** 两个选择：

1. **注册获取**：
   - 访问 https://tushare.pro
   - 注册账号（免费）
   - 获取token（新用户有免费积分）
   - ⚠️ 注意：免费积分有限（约1200积分/天），适合学习测试
   - ⚠️ 高级数据功能需要付费或更多积分

2. **只用QMT**（更推荐）：
   - 如果您有QMT/miniQMT，完全不需要Tushare
   - QMT数据本地访问，速度快且无限制

### Q5：DuckDB数据会过期吗？

**A：** 不会！但建议定期更新：

```bash
# 每周更新一次数据
python tools/download_market_cap_fast.py
```

---

## 📚 下一步

- **想深入学习？** 查看 [学习路径](README.md#-学习路径)
- **遇到问题？** 查看 [疑难问题解答](docs/assets/TROUBLESHOOTING.md)
- **想看实战案例？** 查看 [strategies/](strategies/)

---

## 🆘 还是不行？

加入我们的交流群：

- QQ群：492287081
- 微信公众号：王者quant
- 知识星球：获取一对一答疑

---

**最后提醒：** 🎉

**您不需要DuckDB也能开始！先跑起来，再优化速度！**
