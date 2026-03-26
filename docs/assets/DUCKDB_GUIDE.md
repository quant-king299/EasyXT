# DuckDB 数据库使用指南

> 本指南详细介绍如何在EasyXT项目中初始化、使用和维护DuckDB数据库。

---

## 目录

- [什么是DuckDB](#什么是duckdb)
- [为什么使用DuckDB](#为什么使用duckdb)
- [快速开始](#快速开始)
- [数据下载与初始化](#数据下载与初始化)
- [数据验证](#数据验证)
- [日常使用](#日常使用)
- [数据更新](#数据更新)
- [备份与维护](#备份与维护)
- [常见问题](#常见问题)

---

## 什么是DuckDB

**DuckDB** 是一个嵌入式分析数据库，专为OLAP（在线分析处理）场景设计。

### 特点
- 零配置：无需安装数据库服务器
- 高性能：向量化查询引擎，速度极快
- 轻量级：单个文件存储所有数据
- SQL支持：完整的SQL-99标准
- Python友好：与pandas完美集成

### 在EasyXT中的应用

EasyXT使用DuckDB存储：
- 股票日线数据（stock_daily 表）
- 市值数据（stock_market_cap 表）
- 财务数据、分红数据等

---

## 为什么使用DuckDB

### 性能对比

| 数据源 | 1000次回测耗时 | 数据加载速度 | 适用场景 |
|--------|----------------|--------------|----------|
| **DuckDB** | ~10秒 | 极快 | 高频回测、因子分析 |
| **QMT本地** | ~30秒 | 快 | 实盘交易 |
| **Tushare** | ~300秒 | 慢 | 数据下载 |

### 优势

1. **极速回测** - 批量因子计算速度快10倍以上，适合全市场扫描
2. **离线使用** - 下载一次，永久使用，不受网络和API限制
3. **数据完整** - 历史数据完整，不会因为API问题导致数据缺失
4. **易于管理** - 单个文件，方便备份，跨平台兼容

---

## 快速开始

### 方式一：使用GUI下载数据（推荐新手）

这是最简单的方式，只需有 Tushare Token 即可，**不需要 QMT**。

```bash
# 1. 启动GUI
python run_gui.py

# 2. 切换到 "Tushare下载" 标签页

# 3. 输入 Tushare Token，点击"测试连接"

# 4. 在"快速下载"标签页中：
#    - 勾选 "日线行情"（回测必需）
#    - 勾选 "市值数据"（小市值策略必需）
#    - 设置股票数量（新手建议先 100 只）
#    - 设置数据年份（新手建议先 1 年）
#    - 点击"开始批量下载"
```

数据会自动保存到 `D:/StockData/stock_data.ddb`。

### 方式二：使用命令行一键下载

```bash
python tools/setup_duckdb.py
```

按提示选择下载模式：
1. 快速模式（推荐新手）- 近1年数据，10-20分钟
2. 完整模式（推荐进阶）- 近3年数据，30-60分钟
3. 自定义模式 - 自定义日期范围

**注意**：命令行下载日线数据需要 QMT 环境（xtquant）。如果只有 Tushare Token 没有 QMT，请使用方式一（GUI）。

### 方式三：在"数据管理"标签页下载（需要QMT）

如果你的电脑上已安装 QMT/miniQMT 且已启动：

```bash
# 1. 启动GUI
python run_gui.py

# 2. 切换到 "数据管理" 标签页

# 3. 点击"下载股票数据"按钮
#    - 选择日期范围
#    - 点击开始下载
```

这种方式使用 QMT 本地数据，速度取决于 QMT 数据下载速度。

---

## 数据下载与初始化

### 前置准备

#### 1. 安装DuckDB

```bash
pip install duckdb
```

#### 2. 配置Tushare Token（如果使用方式一或方式二）

创建 `.env` 文件（在项目根目录）：
```env
TUSHARE_TOKEN=你的Token
```

Token 获取方式：
1. 访问 https://tushare.pro 注册账号（免费）
2. 登录后进入「用户中心」→「接口Token」
3. 复制你的 Token

#### 3. 创建数据目录（通常自动创建，但如果需要手动）

```bash
# Windows PowerShell
New-Item -ItemType Directory -Path "D:\StockData" -Force

# Windows CMD
mkdir D:\StockData
```

---

### 完整初始化流程

#### Step 1: 理解数据源优先级

EasyXT支持多种数据源，按优先级自动选择：

```
DuckDB（本地最快） > QMT（本地） > Tushare（在线） > akshare > qstock
```

#### Step 2: 选择适合你的下载方式

| 方式 | 需要 QMT | 需要 Tushare | 推荐人群 |
|------|----------|-------------|---------|
| GUI → Tushare下载 | 不需要 | 需要 | 所有人（推荐新手） |
| GUI → 数据管理 | 需要 | 不需要 | 有QMT的用户 |
| 命令行 setup_duckdb.py | 需要（日线） | 需要（市值） | 进阶用户 |

#### Step 3: 下载并验证

推荐新手使用 GUI 方式，下载 100 只股票 1 年数据作为起步。下载完成后使用下方"数据验证"步骤确认。

---

## 数据验证

### 检查数据库文件

```bash
# 检查文件是否存在
ls -lh D:/StockData/stock_data.ddb

# 正常情况下，100只股票1年数据约 10-50MB
```

### 使用Python验证

```python
import duckdb

# 连接数据库（路径根据实际情况调整）
con = duckdb.connect('D:/StockData/stock_data.ddb', read_only=True)

# 1. 查看所有表
print("=== 数据表列表 ===")
tables = con.execute("SHOW TABLES").fetchall()
for table in tables:
    print(f"  - {table[0]}")

# 2. 查看股票数量
print("\n=== 股票数量 ===")
count = con.execute("""
    SELECT COUNT(DISTINCT stock_code) FROM stock_daily
""").fetchone()[0]
print(f"  共 {count} 只股票")

# 3. 查看数据时间范围
print("\n=== 数据时间范围 ===")
date_range = con.execute("""
    SELECT
        MIN(date) as start_date,
        MAX(date) as end_date,
        COUNT(*) as total_records
    FROM stock_daily
""").fetchone()
print(f"  起始: {date_range[0]}")
print(f"  结束: {date_range[1]}")
print(f"  记录数: {date_range[2]:,}")

con.close()
```

---

## 日常使用

### 在回测中使用

```python
from easyxt_backtest import DataManager, BacktestEngine

# 创建数据管理器（自动检测DuckDB路径）
dm = DataManager()

# 或手动指定路径
# dm = DataManager(duckdb_path='D:/StockData/stock_data.ddb')

# 创建回测引擎
engine = BacktestEngine(initial_cash=1000000, data_manager=dm)

# 运行回测（具体策略代码参考 easyxt_backtest 示例）
result = engine.run_backtest(strategy, '2023-01-01', '2023-12-31')
result.print_summary()
```

### 直接使用SQL查询

```python
import duckdb

con = duckdb.connect('D:/StockData/stock_data.ddb')

# 查询特定股票
df = con.execute("""
    SELECT * FROM stock_daily
    WHERE stock_code = '000001.SZ'
    ORDER BY date DESC
    LIMIT 100
""").fetchdf()

print(df.head())

con.close()
```

---

## 数据更新

### 使用GUI更新

```bash
python run_gui.py
# 切换到 "Tushare下载" 标签页
# 设置较短的年份范围（如 1 年）
# 点击"开始批量下载"
```

### 使用命令行更新

```bash
# 更新市值数据（使用Tushare）
python -c "from tools.download_market_cap_fast import download_market_cap; download_market_cap('20250101')"

# 更新日线数据（需要QMT，通过数据管理界面操作）
python run_gui.py
```

---

## 备份与维护

### 数据备份

```bash
# Windows PowerShell
$timestamp = Get-Date -Format "yyyyMMdd"
Copy-Item "D:\StockData\stock_data.ddb" "D:\StockData\backup\stock_data_$timestamp.ddb"
```

### 数据库优化

```python
import duckdb

con = duckdb.connect('D:/StockData/stock_data.ddb')
con.execute("PRAGMA optimize")
con.execute("VACUUM")
con.close()
```

---

## 常见问题

### Q1: 数据库文件太大怎么办？

```python
import duckdb
con = duckdb.connect('D:/StockData/stock_data.ddb')
con.execute("DELETE FROM stock_daily WHERE date < DATE('now', '-3 years')")
con.execute("VACUUM")
con.close()
```

### Q2: 数据库路径可以改吗？

可以。通过以下方式之一指定：
1. 环境变量 `DUCKDB_PATH`（推荐）
2. 代码中手动指定 `DataManager(duckdb_path='你的路径')`

系统会自动检测以下路径：
- `D:/StockData/stock_data.ddb`
- `C:/StockData/stock_data.ddb`
- `E:/StockData/stock_data.ddb`
- `./data/stock_data.ddb`

### Q3: 没有 QMT 能用 DuckDB 吗？

**可以！** 使用 GUI 的 "Tushare下载" 标签页，只需要 Tushare Token 就能下载日线行情和市值数据到 DuckDB，不需要安装 QMT。

### Q4: DuckDB vs 其他数据库？

| 特性 | DuckDB | SQLite | PostgreSQL |
|------|--------|--------|------------|
| 性能 | 极快 | 一般 | 快 |
| 易用性 | 极好 | 好 | 一般 |
| 部署 | 单文件 | 单文件 | 需服务器 |
| 分析优化 | 是 | 否 | 是 |
| 推荐场景 | 回测分析 | 轻量存储 | 生产环境 |

---

## 相关资源

- [DuckDB官方文档](https://duckdb.org/docs/)
- [疑难问题解答 (FAQ)](TROUBLESHOOTING.md)
- [回测系统指南](../../easyxt_backtest/README.md)

---

**最后更新**: 2026-03-26
