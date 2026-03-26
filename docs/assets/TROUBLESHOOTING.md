# 疑难问题解答（FAQ）

> 遇到问题？先看这里！本文档收集了用户最常遇到的问题和解决方案。

---

## 目录

- [数据相关](#数据相关)
  - [DuckDB是什么？我需要它吗？如何启用？](#1-duckdb是什么我需要它吗如何启用)
  - [DuckDB数据库下载完整步骤](#2-duckdb数据库下载完整步骤)
  - [下载了DuckDB数据但回测/代码里还是报错](#3-下载了duckdb数据但回测代码里还是报错)
  - [DuckDB数据库文件找不到](#4-duckdb数据库文件找不到)
  - [数据下载失败](#5-数据下载失败)
  - [Tushare配置问题](#6-tushare配置问题)
  - [QMT历史数据补充](#7-qmt历史数据补充)
- [安装相关](#安装相关)
- [运行相关](#运行相关)
- [性能相关](#性能相关)

---

## 数据相关

### 1. DuckDB是什么？我需要它吗？如何启用？

#### DuckDB是什么？

DuckDB 是一个**嵌入式数据库**，类似于 SQLite，但专为分析查询（OLAP）优化。在本项目中，它用来把股票行情数据保存到本地文件（`stock_data.ddb`），回测时直接从本地文件读取，**速度比每次从网络获取快 10-30 倍**。

#### 我需要它吗？

| 你的情况 | 是否需要 | 说明 |
|---------|---------|------|
| 只做实盘交易，不回测 | 不需要 | QMT 实时数据足够 |
| 偶尔跑几次回测 | 可选 | 不装也能跑，只是慢一些 |
| 频繁回测、调参、因子分析 | **强烈推荐** | 速度提升 10-30 倍 |
| 使用小市值策略 | **需要** | 策略依赖市值数据表 |

#### DuckDB怎么启用？需要什么条件？

只需要满足以下任意一种条件即可：

- **方式A**：有 Tushare Token（推荐，免费注册）— 不需要 QMT
- **方式B**：有 QMT/miniQMT 环境 — 不需要 Tushare Token
- **方式C**：两者都有 — 最灵活

无论哪种方式，都需要先安装 DuckDB：
```bash
pip install duckdb
```

#### 启用流程一览

```
安装 duckdb（pip install duckdb）
    |
    v
选择下载方式
    |
    +---> 方式A：GUI 下载（推荐新手）
    |     python run_gui.py → "Tushare下载" 标签页
    |     只需 Tushare Token，不需要 QMT
    |
    +---> 方式B：命令行下载
    |     python tools/setup_duckdb.py
    |     需要 Tushare Token（市值数据）+ QMT（日线数据）
    |
    +---> 方式C：使用 QMT 本地数据
          python run_gui.py → "数据管理" 标签页
          需要 QMT/miniQMT 已启动
```

数据下载完成后，回测时会**自动检测并使用 DuckDB**，无需额外配置。

---

### 2. DuckDB数据库下载完整步骤

以下是从零开始的详细操作步骤，以最常用的 **GUI 方式**为例。

#### Step 1：注册 Tushare 并获取 Token

1. 访问 https://tushare.pro ，点击右上角「注册」
2. 用手机号注册（免费，注册即送积分）
3. 登录后，进入「用户中心」→「接口Token」
4. 复制一长串 Token（类似 `1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab`）

#### Step 2：配置 Token

在项目根目录创建 `.env` 文件（如果还没有的话）：

```bash
# Windows PowerShell
Copy-Item .env.example .env

# Windows CMD
copy .env.example .env

# 或者手动创建
```

编辑 `.env` 文件，填入 Token：

```env
TUSHARE_TOKEN=你的Token粘贴在这里
```

验证配置：
```bash
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('Token OK:', os.getenv('TUSHARE_TOKEN')[:10]+'...') if os.getenv('TUSHARE_TOKEN') else print('Token 未配置')"
```

#### Step 3：启动 GUI 并下载数据

```bash
python run_gui.py
```

在 GUI 中：
1. 切换到 **"Tushare下载"** 标签页
2. 在 Token 输入框中粘贴你的 Token（如果 `.env` 已配置会自动填入）
3. 点击 **"测试连接"** ，看到"连接成功"说明 Token 没问题
4. 在 **"快速下载"** 子标签页中：
   - 勾选 **"日线行情"**（回测必需的数据）
   - 勾选 **"市值数据"**（小市值策略必需）
   - 股票数量设为 **100**（新手先下 100 只试试）
   - 数据年份设为 **1 年**（新手先下 1 年试试）
5. 点击 **"开始批量下载"**
6. 等待下载完成（100 只股票 1 年数据大约 5-15 分钟）

#### Step 4：验证下载是否成功

```python
import duckdb

con = duckdb.connect('D:/StockData/stock_data.ddb', read_only=True)

# 查看有哪些表
tables = con.execute("SHOW TABLES").fetchall()
print("表列表:", [t[0] for t in tables])

# 查看日线数据概况
try:
    result = con.execute("""
        SELECT
            COUNT(DISTINCT stock_code) as stocks,
            MIN(date) as from_date,
            MAX(date) as to_date,
            COUNT(*) as records
        FROM stock_daily
    """).fetchone()
    print(f"日线数据: {result[0]} 只股票, {result[1]} ~ {result[2]}, 共 {result[3]:,} 条")
except:
    print("日线数据表为空")

# 查看市值数据概况
try:
    result = con.execute("""
        SELECT
            COUNT(DISTINCT date) as days,
            MIN(date) as from_date,
            MAX(date) as to_date
        FROM stock_market_cap
    """).fetchone()
    print(f"市值数据: {result[0]} 个交易日, {result[1]} ~ {result[2]}")
except:
    print("市值数据表为空")

con.close()
```

#### Step 5：开始使用

下载成功后，**无需任何额外配置**，回测和数据查询会自动使用 DuckDB：

```python
from easyxt_backtest import DataManager, BacktestEngine

# 自动检测 DuckDB 路径
dm = DataManager()
engine = BacktestEngine(initial_cash=1000000, data_manager=dm)

# 开始回测
result = engine.run_backtest(strategy, '2024-01-01', '2024-12-31')
result.print_summary()
```

#### 常见的新手问题

**Q: 下载报错"积分不足"怎么办？**
A: Tushare 采用积分制。日线行情 `daily` 接口消耗较少积分，注册送的积分通常够下载几百只股票。如果不够，可以先减少下载数量（比如 50 只），或者到 Tushare 论坛做任务获取积分。

**Q: 没有D盘怎么办？数据会存在哪里？**
A: 系统会自动检测 D 盘、C 盘、E 盘。如果都不存在，会自动创建 `D:/StockData/` 目录。你也可以通过环境变量自定义路径：
```bash
setx DUCKDB_PATH "C:/MyData/stock_data.ddb"
```

**Q: 数据下载到一半中断了怎么办？**
A: 直接重新下载。系统会自动跳过已有的数据，只下载缺失的部分。

**Q: 我没有 QMT，能只用 Tushare 下载吗？**
A: **完全可以！** GUI 的"Tushare下载"标签页只依赖 Tushare，不需要 QMT。这是新手最推荐的方式。

---

### 3. 下载了DuckDB数据但回测/代码里还是报错

#### 症状

DuckDB 文件已经存在（`D:/StockData/stock_data.ddb`），但运行回测时代码找不到数据。

#### 可能原因和解决方案

**原因1：表名不匹配**

旧版本教程可能引用了 `stock_data` 表，但实际表名是 `stock_daily`。

```python
# 检查实际的表名
import duckdb
con = duckdb.connect('D:/StockData/stock_data.ddb', read_only=True)
tables = con.execute("SHOW TABLES").fetchall()
print([t[0] for t in tables])
con.close()
```

**原因2：回测日期范围没有重叠**

如果你下载的是 2024 年的数据，但回测设置的是 2022 年，就会报"数据为空"。

```python
# 检查数据库中的实际日期范围
import duckdb
con = duckdb.connect('D:/StockData/stock_data.ddb', read_only=True)
result = con.execute("SELECT MIN(date), MAX(date) FROM stock_daily").fetchone()
print(f"数据范围: {result[0]} ~ {result[1]}")
con.close()

# 回测日期应在此范围内
```

**原因3：DataManager 没有指向正确的路径**

如果数据库不在默认路径，需要手动指定：

```python
from easyxt_backtest import DataManager

# 自动检测（检查 D盘、C盘、E盘）
dm = DataManager()

# 手动指定
dm = DataManager(duckdb_path='你的实际路径/stock_data.ddb')
```

**原因4：数据库文件损坏**

如果数据库文件损坏，删除后重新下载：

```bash
# 备份旧文件
ren "D:\StockData\stock_data.ddb" "stock_data.ddb.bak"

# 重新下载
python run_gui.py
# → "Tushare下载" → 重新下载
```

---

### 4. DuckDB数据库文件找不到

#### 错误信息
```
IO Error: Cannot open file "D:\StockData\stock_data.ddb": 系统找不到指定的路径。
```

#### 问题原因
- 你还没有下载过数据（第一次使用项目）
- 数据库文件存放在其他盘符（C盘、E盘）

#### 解决方案

**最推荐：用 GUI 下载一次数据**

按照上方 [第2节](#2-duckdb数据库下载完整步骤) 的步骤操作。

**或者：手动创建目录后使用 QMT 数据**

如果你有 QMT，不需要 DuckDB 也能跑回测（只是速度慢一些）。系统会自动降级到 QMT 数据源。

---

### 5. 数据下载失败

#### 常见错误

**错误1：Tushare连接失败**
```
ConnectionError: Unable to connect to Tushare API
```

**错误2：积分不足**
```
API Error: 积分不足
```

**错误3：下载速度慢或中断**
```
TimeoutError: Request timeout
```

#### 解决方案

**检查Token是否有效：**
1. 登录 Tushare Pro
2. 进入「用户中心」→「接口Token」
3. 确认Token没有过期

**检查积分是否足够：**
1. 在Tushare网站查看账户积分
2. 基础功能需要一定积分（注册后会获得初始积分）
3. 高级功能需要更多积分（可能需要充值）

**优化下载策略：**
- 减少下载数量（GUI中：股票数量改为 10-50 只）
- 减少时间范围（GUI中：数据年份改为 1 年）
- 分批下载（多次运行，每次下载不同的股票）

**使用其他数据源：**
项目支持多种数据源，会自动降级：
```
DuckDB > QMT > Tushare > akshare > qstock
```

如果你有QMT终端，可以直接使用QMT本地数据，无需下载到DuckDB。

---

### 6. Tushare配置问题

#### 问题：Token配置后仍然报错

```
ValueError: TUSHARE_TOKEN not found in environment variables
```

#### 解决方案

**检查.env文件：**

1. 确认 `.env` 文件在项目根目录：
   ```
   miniqmt扩展/
   ├── .env              ← 这个文件
   ├── easy_xt/
   └── README.md
   ```

2. 检查文件内容格式：
   ```env
   # 正确格式（不加引号）
   TUSHARE_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

   # 错误格式
   TUSHARE_TOKEN="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
   ```

3. 验证环境变量：
   ```bash
   python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('Token OK') if os.getenv('TUSHARE_TOKEN') else print('Token 未配置')"
   ```

**手动设置环境变量（永久）：**

```powershell
# PowerShell
setx TUSHARE_TOKEN "你的Token"

# CMD
setx TUSHARE_TOKEN "你的Token"
```

注意：设置后需要**重启终端/IDE**才能生效。

---

### 7. QMT历史数据补充

#### 错误信息
```
ERROR: 无法获取股票 ['000001.SZ'] 的数据。可能的原因：
1. 需要先在迅投客户端中下载历史数据
2. 股票代码错误
```

#### 问题原因

QMT刚安装时本地数据库为空，需要先下载历史数据。

#### 解决方案

**方案一：使用项目的一键下载工具**

```bash
cd tools
python download_all_stocks.py
```

**方案二：安装pytdx，自动降级到TDX**

```bash
pip install pytdx
```

安装后系统会自动使用通达信数据源，不需要QMT也能获取数据。

**方案三：使用 DuckDB（推荐长期使用）**

按照上方 [第2节](#2-duckdb数据库下载完整步骤) 下载 DuckDB 数据，彻底避免 QMT 数据管理问题。

---

## 安装相关

### 8. xtquant安装失败

#### 错误信息
```
ImportError: cannot import name 'datacenter' from 'xtquant'
```

#### 解决方案

**必须使用项目提供的特殊版本！**

1. 下载：https://github.com/quant-king299/EasyXT/releases/tag/v1.0.0 → `xtquant.rar`
2. 解压到项目根目录（与 `easy_xt/` 同级）
3. 验证：`python -c "from xtquant import datacenter; print('OK')"`

> 不要使用 `pip install xtquant` 安装官方版本！

#### 一键检查工具

```bash
cd easy_xt
python check_xtquant.py
```

---

### 9. 依赖安装失败

#### 常见错误

```
ReadTimeoutError: HTTPSConnectionPool read timeout
ERROR: Could not find a version that satisfies the requirement
```

#### 解决方案

**使用国内镜像源：**
```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

**逐个安装依赖：**
```bash
pip install pandas numpy PyQt5 duckdb streamlit
pip install -e ./easy_xt
```

---

## 运行相关

### 10. GUI启动失败

#### 错误信息
```
ImportError: No module named 'PyQt5'
```

#### 解决方案
```bash
pip install PyQt5
```

---

### 11. 回测报错

#### 错误1：数据为空
```
ValueError: No data available for the specified date range
```

#### 错误2：股票代码格式错误
```
KeyError: 'STOCK_CODE not found'
```

#### 解决方案

**检查数据是否存在：**
```python
import duckdb
con = duckdb.connect('D:/StockData/stock_data.ddb', read_only=True)
result = con.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM stock_daily").fetchone()
print(f"数据量: {result[0]} 条, 范围: {result[1]} ~ {result[2]}")
con.close()
```

**确认股票代码格式：**
- 正确：`000001.SZ`, `600000.SH`
- 错误：`000001`, `600000`, `sz000001`

---

### 12. 策略运行失败

#### 错误信息
```
ConnectionError: 无法连接到交易账户
```

#### 解决方案

- 确保QMT客户端已启动并登录
- 确保账户有交易权限
- 确认 `qmt_path` 配置正确

---

## 性能相关

### 13. 回测速度慢

#### 性能对比

| 数据源 | 回测1000次耗时 | 推荐场景 |
|--------|----------------|---------|
| DuckDB | ~10秒 | 高频回测（推荐） |
| QMT本地 | ~30秒 | 实盘交易 |
| Tushare在线 | ~300秒 | 快速测试 |

#### 优化建议

**安装并启用 DuckDB（效果最明显）：**

按照 [第2节](#2-duckdb数据库下载完整步骤) 下载 DuckDB 数据即可，回测时会自动使用。

```python
from easyxt_backtest import DataManager

# 自动检测 DuckDB（无需手动指定路径）
dm = DataManager()
```

**使用向量化操作代替循环：**
```python
# 慢
for i in range(len(df)):
    df.loc[i, 'ma5'] = df['close'].iloc[i-5:i].mean()

# 快
df['ma5'] = df['close'].rolling(5).mean()
```

---

### 14. 内存占用过高

#### 问题
```
MemoryError: Unable to allocate array
```

#### 解决方案

```python
# 分批处理
for batch in stock_batches:
    data = load_batch(batch)
    process(data)

# 及时释放
import gc
del large_dataframe
gc.collect()
```

---

## 快速诊断工具

运行以下命令快速检查环境状态：

```bash
python -c "
import sys, os
from pathlib import Path

print('=' * 50)
print('EasyXT 环境快速检查')
print('=' * 50)

# 1. Python
print(f'[1] Python {sys.version_info.major}.{sys.version_info.minor}: ', end='')
print('OK' if sys.version_info >= (3, 8) else '建议升级到3.8+')

# 2. duckdb
try:
    import duckdb; print('[2] duckdb: OK')
except: print('[2] duckdb: 未安装 (pip install duckdb)')

# 3. easy_xt
try:
    from easy_xt import get_api; print('[3] easy_xt: OK')
except: print('[3] easy_xt: 未安装 (pip install -e ./easy_xt)')

# 4. DuckDB数据库
db_found = False
for p in ['D:/StockData/stock_data.ddb', 'C:/StockData/stock_data.ddb', 'E:/StockData/stock_data.ddb']:
    if Path(p).exists():
        size_mb = os.path.getsize(p) / 1024 / 1024
        print(f'[4] DuckDB数据库: 找到 ({p}, {size_mb:.1f}MB)')
        db_found = True; break
if not db_found:
    print('[4] DuckDB数据库: 未找到 (运行 python run_gui.py 下载)')

# 5. Tushare Token
token = os.environ.get('TUSHARE_TOKEN', '')
if not token:
    try:
        with open('.env') as f:
            for line in f:
                if line.startswith('TUSHARE_TOKEN='):
                    token = line.split('=',1)[1].strip()
    except: pass
print(f'[5] Tushare Token: {\"OK (\" + token[:10] + \"...)\" if token else \"未配置\"}')

print('=' * 50)
"
```

---

## 获取更多帮助

### 官方文档
- [项目 README](README.md)
- [DuckDB 使用指南](DUCKDB_GUIDE.md)
- [回测系统指南](../../easyxt_backtest/README.md)
- [101因子平台指南](../../101因子/101因子分析平台/README.md)

### 社区支持
- **GitHub Issues**: https://github.com/quant-king299/EasyXT/issues
- **微信公众号**: 王者quant
- **知识星球**: 获取一对一答疑服务

### 提交问题时请提供：
1. 完整的错误信息
2. 运行环境（Python版本、操作系统）
3. 复现步骤
4. 相关代码片段

---

**最后更新**: 2026-03-26
