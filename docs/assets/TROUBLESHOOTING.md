# 疑难问题解答（FAQ）

> 遇到问题？先看这里！本文档收集了用户最常遇到的问题和解决方案。

---

## 目录

- [xtquant 相关](#xtquant-相关) ← 🆕 常见问题
- [数据相关](#数据相关)
- [配置相关](#配置相关) ← 🆕 新增章节
- [QMT自动登录相关](#qmt自动登录相关) ← 🆕 新增
- [代码转换相关](#代码转换相关)
- [安装相关](#安装相关)
- [运行相关](#运行相关)
- [性能相关](#性能相关)

---

## xtquant 相关

### ❌ 错误：`cannot import name 'datacenter' from 'xtquant'`

这是最常见的错误！说明 xtquant **未正确安装**或**版本不兼容**。

#### 原因

本项目需要**特殊版本**的 xtquant，不能使用 `pip install xtquant` 安装的官方版本！

**为什么？** 不同券商的 QMT 版本发布节奏不一致，xtquant 接口和行为存在差异。使用官方版本会导致：连接失败、字段缺失、接口不兼容。

#### 解决方案

**方法 1：从 GitHub Releases 下载（推荐）**

1. 访问：https://github.com/quant-king299/EasyXT/releases/tag/v1.0.0
2. 下载：`xtquant.rar`
3. 解压到项目根目录（即下载的 EasyXT 项目文件夹）

   > **说明**：从 GitHub 下载的文件夹名为 `EasyXT`，项目根目录就是 `EasyXT/`

4. 验证安装：
   ```bash
   python -c "from xtquant import datacenter; print('✓ OK')"
   ```

**方法 2：一键下载并解压（PowerShell）**

```powershell
# 先进入项目根目录（EasyXT项目文件夹）
cd <你的项目路径>

$url = "https://github.com/quant-king299/EasyXT/releases/download/v1.0.0/xtquant.rar"
$dest = "$PWD\xtquant.rar"
Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing

# 解压（需要 7-Zip）
if (Test-Path "$env:ProgramFiles\7-Zip\7z.exe") {
  & "$env:ProgramFiles\7-Zip\7z.exe" x -y "$dest" -o"$PWD"
}

Remove-Item $dest -ErrorAction SilentlyContinue
python easy_xt/check_xtquant.py
```

**方法 3：从 QMT 软件目录复制**

如果已安装 QMT 客户端：
1. 找到 QMT 安装目录，如：`D:\国金证券QMT交易端\userdata_mini\Python\`
2. 复制 `xtquant` 文件夹到项目根目录（EasyXT项目文件夹）

#### 验证安装

运行诊断脚本：
```bash
python easy_xt/check_xtquant.py
```

该脚本会自动检查：
- ✅ xtquant 模块能否导入
- ✅ xtquant.datacenter 能否导入（关键组件）
- ✅ xtquant.xtdata 能否导入

---

### ⚠️ Python 版本不兼容

**问题**：XtQuant **不支持 Python 3.13**！

**支持版本**：Python 3.6 - 3.12（推荐 3.11）

**检查版本**：
```bash
python --version
# 正确: Python 3.11.x
# 错误: Python 3.13.x
```

**解决方案**：

如果系统默认是 Python 3.13，需要将 Python 3.11 设为默认：

1. 按 `Win + S` 搜索 **"编辑系统环境变量"**
2. 点击 **"环境变量"**
3. 在 **"用户变量"** 的 `Path` 中，将 Python 3.11 的路径移到最顶部：
   ```
   C:\Users\你的用户名\AppData\Local\Programs\Python\Python311\Scripts\
   C:\Users\你的用户名\AppData\Local\Programs\Python\Python311\
   ```
4. **删除** Python 3.13 的路径
5. 重启终端，验证：`python --version`

---

### 自定义 xtquant 安装位置

如果将 xtquant 解压到自定义目录（如 `C:\xtquant_special`），需设置环境变量：

```powershell
setx XTQUANT_PATH "C:\xtquant_special"
```

**⚠️ 设置后必须重启终端/IDE才能生效！**

---

## 数据相关

### 1. 首次运行：应该选择"下载A股数据"还是"补全历史数据"？

#### 症状

运行 `rungui.py` 后看到提示：
```
[时间] 本地数据管理组件已加载
[时间] 提示：首次使用请先下载数据
[时间] ℹ️  DuckDB数据库尚未创建，请先下载股票数据
```

不知道应该点击哪个按钮：
- 📥 下载A股数据
- 📜 补全历史数据
- 🔄 更新缺失数据

#### 答案

**首次运行应该选择：📥 下载A股数据**

#### 三个功能的区别

| 功能 | 用途 | 使用场景 | 数据库状态 |
|------|------|----------|------------|
| **📥 下载A股数据** | 从零开始，自动获取全部A股列表并下载指定日期范围的数据 | **首次使用** | 数据库为空 |
| **📜 补全历史数据** | 补充指定日期之前的历史空白 | 发现历史数据缺失时 | 已有股票列表 |
| **🔄 更新缺失数据** | 智能检测并补充最新日期之后的所有缺失数据 | 日常更新数据 | 已有完整历史数据 |

#### 详细说明

**📥 下载A股数据（首次使用必选）**
- **功能**：从零开始建立数据库
- **操作**：
  1. 设置日期范围（建议首次：2024-01-01 ~ 今天）
  2. 点击「📥 下载A股数据」按钮
  3. 等待下载完成（首次可能需要几小时）
- **说明**：
  - ✅ 自动获取全部A股列表（约5000只股票）
  - ✅ 创建DuckDB数据库和表结构
  - ✅ 下载指定日期范围内的日线数据
  - ⏰ 首次下载时间较长

**📜 补全历史数据**
- **功能**：补充指定日期之前的历史空白
- **用途**：发现历史数据有缺失时使用
- **说明**：
  - 需要数据库中已有股票列表
  - 只会补充缺失的部分，已有数据不会被删除
  - 适合修复历史数据空白期

**🔄 更新缺失数据**
- **功能**：智能检测并补充最近缺失的数据
- **用途**：日常更新推荐使用
- **说明**：
  - 自动检测每只股票的最新日期
  - 补充从最新日期之后到今天缺失的所有数据
  - 不管缺失1天还是100天，都会一并补全

#### 推荐使用流程

```
首次运行：    📥 下载A股数据 → 从零开始建立数据库
日常使用：    🔄 更新缺失数据 → 补充最近几天的数据（推荐）
发现缺失：    📜 补全历史数据 → 修复历史数据空白期
```

#### 注意事项

1. **数据存储位置**：`D:/StockData/stock_data.ddb`
2. **首次下载建议**：
   - 先下载1年数据测试（如2024-01-01 ~ 今天）
   - 确认无误后再下载更早年份的数据
   - 建议**晚上睡觉前运行**，避免交易时间影响速度
3. **下载过程可以最小化窗口**，不影响使用
4. **数据来源**：QMT本地数据（需要QMT已运行并登录）

---

### 2. DuckDB是什么？我需要它吗？如何启用？

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

### 3. DuckDB数据库下载完整步骤

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

### 4. 下载了DuckDB数据但回测/代码里还是报错

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

### 8. 1分钟数据获取失败：count值太小

#### 错误信息

```
[降级] 尝试使用 TDX 数据源...
[WARN] TDX 数据源失败: 时间范围内无数据: None - 20260414
```

或者

```
ERROR: 无法获取股票 ['000001.SZ'] 的数据。
```

#### 问题原因

**TDX（通达信）对1分钟数据有最小count限制：count必须 ≥ 2**

当你使用 `count=1` 获取1分钟数据时：
```python
data = api.get_price(['000001.SZ'], period='1m', count=1)  # ❌ 会失败
```

TDX服务器认为请求的数据量太少，拒绝请求或返回空数据。

#### count 参数说明

**count** = 数据条数，表示获取最近多少根K线：

| 周期 | count=5 的实际含义 | 时间范围 |
|------|-------------------|---------|
| **1d** (日线) | 最近5个**交易日** | 约1周 |
| **1m** (1分钟) | 最近5个**分钟** | 最近5分钟 |
| **5m** (5分钟) | 最近5个**5分钟** | 最近25分钟 |
| **1h** (1小时) | 最近5个**小时** | 最近5小时 |

#### 解决方案

**方案一：自动调整（推荐，已修复）** ✅

最新代码已经自动处理此问题：
```python
# 即使你写 count=1，也会自动调整为 count=2
data = api.get_price(['000001.SZ'], period='1m', count=1)
# 输出：[INFO] TDX 1分钟数据最小count为2，已自动调整: 1 -> 2
```

**方案二：手动调整count值**

```python
# ✅ 正确：使用 count >= 2
data = api.get_price(['000001.SZ'], period='1m', count=2)
data = api.get_price(['000001.SZ'], period='1m', count=5)
data = api.get_price(['000001.SZ'], period='1m', count=10)

# ❌ 错误：count=1 会失败
data = api.get_price(['000001.SZ'], period='1m', count=1)
```

**方案三：使用更大的count值**

对于1分钟数据，建议使用较大的count值：
```python
# 推荐：获取最近10-20分钟的1分钟数据
data = api.get_price(['000001.SZ'], period='1m', count=10)
# 或
data = api.get_price(['000001.SZ'], period='1m', count=20)
```

#### 不同周期的count建议

| 周期 | 最小count | 推荐count | 说明 |
|------|----------|----------|------|
| **1m** | 2 | 10-20 | TDX有最小限制 |
| **5m** | 1 | 5-10 | 无特殊限制 |
| **15m** | 1 | 5-10 | 无特殊限制 |
| **30m** | 1 | 5 | 无特殊限制 |
| **1h** | 1 | 5 | 无特殊限制 |
| **1d** | 1 | 5-100 | 根据需求 |

#### 为什么有这个限制？

**技术原因**：

1. **数据完整性**：TDX服务器可能要求返回一定量的数据
2. **性能优化**：对于高频数据（如1分钟），服务器希望一次性返回更多
3. **接口设计**：某些API设计时就规定了最小请求量

#### 其他周期有此限制吗？

**只有1分钟数据有此限制**：
- ✅ 5m、15m、30m、1h、1d 等周期可以使用 `count=1`
- ❌ 1m 数据必须使用 `count>=2`

#### 降级行为说明

当QMT没有分钟数据时，系统会自动降级到TDX：

```
[降级] 尝试使用 TDX 数据源...
[INFO] TDX 1分钟数据最小count为2，已自动调整: 1 -> 2  ← 自动调整
[OK] TDX 数据源获取成功
```

如果TDX也失败，会继续尝试Eastmoney：
```
[降级] 尝试使用 EASTMONEY 数据源...
[WARN] EASTMONEY 数据源失败: ...
```

---

### 9. 用download_all_stocks.py下载了.DAT文件，如何导入DuckDB并复权？

#### 症状

使用了 `tools/download_all_stocks.py` 下载了全部A股数据，文件保存在 QMT 的 `.DAT` 格式中（如 `userdata_mini/datadir/SZ/86400/000001.DAT`），但想导入到 DuckDB（`stock_data.ddb`）并使用五维复权功能，不知道怎么操作。

#### 问题原因

`download_all_stocks.py` 只做了一件事：调用 `xtdata.download_history_data()` 把数据下载到 QMT 的 `.DAT` 本地文件。**它不会自动把数据提取出来存到 DuckDB。**

完整的下载流程应该是三步：

```
① xtdata.download_history_data()  →  下载数据到 .DAT 文件
② xtdata.get_market_data_ex()     →  从 .DAT 读取为 Python DataFrame
③ 写入 DuckDB + 五维复权          →  存入 stock_data.ddb
```

`download_all_stocks.py` 只做了第①步，缺少第②③步。

#### 解决方案

**不需要手动转换 .DAT 文件！** 直接使用 GUI 界面操作即可：

**情况一：.DAT 文件已经下载好了（你之前运行过 download_all_stocks.py）**

1. 启动 GUI：`python run_gui.py`
2. 切换到 **"📊 数据管理"** 标签页
3. 点击 **"🔄 更新缺失数据"** 按钮
4. 系统会通过 QMT API（`xtdata.get_market_data_ex()`）自动读取已有的 .DAT 文件，提取数据并存入 DuckDB

> 已经下载好的 .DAT 文件不会被浪费，QMT API 会直接从本地 .DAT 文件读取，不需要重新从网络下载。

**情况二：还没有下载过数据，想一步到位**

1. 启动 GUI：`python run_gui.py`
2. 切换到 **"📊 数据管理"** 标签页
3. 设置日期范围（建议开始日期设为5年前）
4. 点击 **"📥 下载A股数据"** 按钮
5. 系统会自动完成：下载 → 读取 → 存入 DuckDB → 五维复权，一条龙搞定

**情况三：只想下载单只股票**

1. 启动 GUI：`python run_gui.py`
2. 切换到 **"📊 数据管理"** 标签页
3. 在 "🎯 手动下载单个标的" 区域输入股票代码（如 `000001.SZ`）
4. 选择数据类型和日期范围
5. 点击 **"⬇️ 下载单个标的"**

#### 关于五维复权

数据存入 DuckDB 后，在 **"📈 数据查看器"** 标签页可以切换五种复权方式查看数据：

| 复权类型 | 说明 | 用途 |
|---------|------|------|
| 不复权 | 除权除息后的原始价格 | 看真实交易价格 |
| 前复权 | 以最新价格为基准调整历史 | 看K线图最常用 |
| 后复权 | 以上市首日为基准调整当前 | 计算真实收益率 |
| 等比前复权 | 几何平均消除除权跳空 | 连续K线 |
| 等比后复权 | 几何平均消除跳空 | 连续收益曲线 |

> 提示：不要使用 `download_all_stocks.py` 下载数据，直接用 GUI 里的按钮就行，省时省力。

---

### 10. 复权系统架构说明：为什么只存不复权数据？

#### 问题

有用户反馈：既然回测基本都用前复权，为什么 DuckDB 只存不复权数据？每次都要先查 DuckDB 再调 QMT API 获取复权，是不是多了一步？DuckDB 还有什么用？

#### 解答

**核心逻辑：原始数据不变，存本地；复权数据会变，用时再算。**

#### 数据流向（并不是"先查DuckDB再做复权"）

不复权和复权是两条**并行路径**，不是串行的：

| 查询类型 | 数据来源 | 是否需要QMT |
|---------|---------|------------|
| 不复权 | 直接读 DuckDB | 不需要 |
| 任何复权 | 直接调 QMT API | 需要 |

具体来说：
- **不复权**：从 DuckDB 读取原始 OHLCV 数据，速度快，无需启动 QMT
- **前/后/等比前/等比后复权**：直接调用 QMT API 的 `get_market_data_ex(dividend_type=...)` 接口，QMT 实时计算并返回已复权数据

不存在"先从 DuckDB 取原始数据再本地做复权转换"的流程，所以没有"多绕一步"的问题。

#### 为什么不把复权数据也存进 DuckDB？

复权数据有一个关键特性：**每次新的除权除息发生后，所有历史数据的复权值都会变**。

比如某股票在 2026 年 6 月派息，那么：
- 前复权：6 月之前所有历史价格都要重新计算
- 后复权：6 月之后所有价格都要重新计算

如果预存复权数据，就需要在每次除权除息后批量更新全量历史数据，维护成本高且容易出错。改为按需从 QMT API 获取，复权计算由 QMT 官方算法保证准确性，无需本地维护。

#### 五种复权类型的区别

| 复权类型 | QMT参数 | 说明 | 典型用途 |
|---------|---------|------|---------|
| 不复权 | `none` | 原始交易价格 | 看真实交易价、事件研究 |
| 前复权 | `front` | 以最新价为基准调整历史价格 | 技术分析、看K线图 |
| 后复权 | `back` | 以上市首日为基准调整当前价格 | 计算长期真实收益率 |
| 等比前复权 | `front_ratio` | 乘法因子调整历史价格 | 量化回测（推荐） |
| 等比后复权 | `back_ratio` | 乘法因子调整当前价格 | 复合收益曲线 |

> 等比复权与普通复权的区别：普通复权用加法（加回分红金额），等比复权用乘法（乘以比例因子）。等比复权能保证涨跌幅的连续性，是量化回测的推荐选择。

#### DuckDB 的实际应用场景

1. **离线查看原始行情**：不需要启动 QMT 就能浏览历史数据
2. **数据完整性检测**：对比本地已有数据，发现缺失时才触发在线补充
3. **快速量价统计**：不复权场景下的数据分析
4. **GUI 数据查看器的默认模式**：`local_only=True` 时只展示本地数据，响应更快

#### 回测时是否必须启动 QMT？

目前是的。如果 QMT 未启动，系统会降级返回不复权的原始数据并给出提示。后续如果有"离线回测"需求，可以考虑增加一层复权结果缓存（按股票+日期范围缓存 QMT 返回的复权数据），按需填充，不会像之前那样预存全量复权列。

---

## 配置相关

### ❓ 配置文件在哪里？

本项目主要有两个配置文件：

| 配置文件 | 路径 | 用途 |
|---------|------|------|
| **unified_config.json** | `config/unified_config.json` | 主配置（QMT路径、交易参数等） |
| **.env** | 项目根目录 `/.env` | 环境变量（Token、Cookie等） |

### ❓ 如何编辑配置文件？

**Windows 最简单方法**：
1. 按 `Win + R`，输入 `notepad`
2. 文件 → 打开
3. 选择配置文件（`.env` 或 `config/unified_config.json`）
4. 编辑并保存

**如果 .env 不存在**：
```bash
# Windows PowerShell
Copy-Item .env.example .env

# Windows CMD
copy .env.example .env
```

### ⚠️ QMT 路径配置错误

**错误**：QMT 连接失败

**解决方案**：

编辑 `config/unified_config.json`，修改路径：

```json
{
  "settings": {
    "account": {
      "qmt_path": "D:\\\\国金QMT交易端模拟\\\\userdata_mini"
    }
  }
}
```

**⚠️ 注意**：Windows 路径在 JSON 中需要用 `\\\\` 或 `/`：
- ✅ `"D:\\\\国金QMT交易端模拟\\\\userdata_mini"`
- ✅ `"D:/国金QMT交易端模拟/userdata_mini"`
- ❌ `"D:\国金QMT交易端模拟\userdata_mini"`

**验证配置**：
```python
from easy_xt.config import config
config.print_qmt_status()
```

### ❓ Tushare Token 如何配置？

**步骤 1**：获取 Token
- 访问 https://tushare.pro 注册
- 登录后进入「用户中心」→「接口Token」

**步骤 2**：配置 Token

编辑项目根目录的 `.env` 文件：
```env
TUSHARE_TOKEN=你的Token粘贴在这里
```

**验证**：
```bash
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('✓ Token OK' if os.getenv('TUSHARE_TOKEN') else '✗ Token 未配置')"
```

### ❓ IDE（VSCode/PyCharm/Trae）中无法导入模块

**原因**：PYTHONPATH 配置错误

**VSCode 解决方案**：

创建 `.vscode/settings.json`：
```json
{
  "python.envFile": "${workspaceFolder}/.env",
  "python.analysis.extraPaths": ["${workspaceFolder}"]
}
```

**PyCharm 解决方案**：

1. Run → Edit Configurations
2. 添加环境变量：`PYTHONPATH=项目根目录路径`

**Trae 解决方案**：

在 Trae 终端中设置：
```bash
export PYTHONPATH="项目根目录路径:$PYTHONPATH"
```

---

### 10. 可转债数据下载失败：648只只成功4只

#### 症状

```
[10:52:22] 📥 开始下载可转债数据 (2016-04-16 ~ 2026-04-16)
[10:52:22] ✅ 获取到 648 只可转债
[10:56:45] 📊 进度: 500/648 | 成功: 4 | 失败: 496
[10:58:00] ✅ 下载完成! 总数: 648, 成功: 4, 失败: 644
```

可转债数据下载失败率高达99%，同时看到错误信息：
```python
[WARN] TDX 数据源失败: 无法获取股票 ['123001.SZ'] 的TDX数据
ERROR:easy_xt.realtime_data.providers.eastmoney_provider:获取K线数据请求失败: ('Connection aborted.', RemoteDisconnected)
```

#### 原因分析

**可转债代码格式特殊**：
- **123xxx.SZ**（深交所可转债）
- **128xxx.SZ**（深交所可转债）
- **110xxx.SH**（上交所可转债）
- **113xxx.SH**（上交所可转债）

**数据源支持情况**：

| 数据源 | 股票支持 | 可转债支持 | 说明 |
|--------|----------|------------|------|
| **QMT** | ✅ 完全支持 | ⚠️ 有限支持 | 需要特殊配置，部分券商不支持 |
| **TDX** | ✅ 支持股票 | ❌ 不支持可转债 | 通达信主要支持股票和指数 |
| **Eastmoney** | ✅ 支持股票 | ⚠️ 理论支持 | 网络不稳定，经常连接失败 |

**三个降级阶段都失败**：

1. **QMT主数据源失败**：
   - QMT可能没有订阅可转债行情
   - 券商QMT版本可能不支持可转债数据
   - 可转债代码不在QMT的订阅列表中

2. **TDX降级失败**：
   - TDX（通达信）不支持可转债数据
   - 只支持股票、指数、期货等品种

3. **Eastmoney降级失败**：
   - Eastmoney理论上支持可转债
   - 但网络连接不稳定，经常超时

#### 解决方案

**方案1：在QMT中订阅可转债行情（推荐）**

1. 打开QMT软件，登录交易账户
2. 订阅可转债行情：
   - 在QMT自选股中添加可转债代码
   - 或使用QMT的"品种订阅"功能
3. 验证订阅：
   ```python
   import easy_xt
   api = easy_xt.get_api()
   api.init_data()
   data = api.get_price(['123001.SZ'], period='1d', count=5)
   print(data)
   ```
4. 重新运行"下载可转债数据"

**方案2：使用Tushare下载可转债数据（推荐备选）**

Tushare对可转债支持更好，数据更完整：

1. 切换到GUI的"Tushare下载"标签页
2. Tushare支持可转债数据
3. 数据质量更好，来源更稳定

**方案3：跳过可转债数据（快速解决）**

如果你主要做股票量化，可转债数据不是必需的：
- 直接使用"下载A股数据"功能
- 后续需要可转债时再配置

#### 清除Python缓存

如果看到`'DataManager' object has no attribute 'get_stock_data'`错误：

```bash
# 清除Python缓存
rm -rf "101因子/101因子分析平台/src/data_manager/__pycache__"

# 重启GUI
python run_gui.py
```

#### 总结

**可转债下载失败是正常现象**，主要原因：

1. ✅ **QMT支持有限**：需要特殊配置才能获取可转债数据
2. ❌ **TDX不支持**：通达信只支持股票和指数
3. ⚠️ **Eastmoney不稳定**：网络连接经常失败

**推荐方案**：
- **短期**：使用Tushare下载可转债数据
- **长期**：在QMT中订阅可转债行情

**如果你只做股票量化**，可以直接跳过可载数据下载，不影响股票策略的开发和回测。

---

## 代码转换相关

### 11. 聚宽转PTrade：需要安装miniQMT吗？可以独立运行吗？

**完全可以独立运行，不需要安装 miniQMT！**

聚宽转PTrade 模块（`code_converter/`）是一个纯代码转换工具，把聚宽的 API 语法翻译成 PTrade 的语法。它与 QMT/easy_xt 完全没有依赖关系。

| 问题 | 回答 |
|------|------|
| 需要 miniQMT 吗？ | 不需要 |
| 需要 easy_xt 吗？ | 不需要 |
| 需要 xtquant 吗？ | 不需要 |
| 需要启动 QMT 客户端吗？ | 不需要 |
| 转换后的代码在哪里运行？ | 复制到 PTrade 平台运行 |

项目中的 QMT 相关模块（easy_xt、xtquant 等）是给 QMT 用户用的，和 PTrade 没有关系，可以忽略。

---

### 12. 聚宽转PTrade：如何使用？

#### 方式一：图形界面（推荐）

1. 从 GitHub 下载项目代码
2. 进入 `code_converter` 文件夹
3. 双击 `run_converter.bat`，弹出图形界面
4. 选择你的聚宽策略 .py 文件，点击"开始转换"
5. 点击"保存结果"，将转换后的代码复制到 PTrade 平台运行

#### 方式二：命令行

```bash
cd code_converter
python cli.py 你的聚宽策略.py -o ptrade策略.py
```

#### 方式三：学习参考

`code_converter/代码转换学习-demo/` 目录提供了学习资料：

| 文件 | 说明 |
|------|------|
| `jq_code_demo.py` | 聚宽策略示例代码 |
| `trans_PTrade.txt` | 转换后的 PTrade 代码 |
| `check_before.txt` | 转换前后的对比说明 |
| `聚宽一键迁移ptrade代码转换使用手册.docx` | 完整的使用手册 |

> **注意**：部分复杂的聚宽 API（如 get_fundamentals 的复杂 query）转换后可能需要手动微调，转换器会给出提示。

---

### 13. 聚宽转PTrade：转换结果只有几行注释，没有代码

#### 症状

转换后的文件只有头部注释：
```
# 聚宽策略转Ptrade - BACKTEST版本
# 转换时间: 2026-04-09 22:19:28
# 转换器版本: v3.4
```

#### 原因

输入的聚宽策略文件内容为空。转换器读入空文件，自然只能输出头部信息。

#### 解决方案

确保输入文件包含有效的聚宽策略代码。一个有效的聚宽策略通常包含：

```python
# 至少要有 initialize 和策略函数
def initialize(context):
    set_benchmark('000300.XSHG')
    run_daily(my_trade, time='9:30')

def my_trade(context):
    stocks = get_all_securities().index.tolist()
    for stock in stocks[:10]:
        order_value(stock, 10000)
```

---

## 安装相关

### 8. 从GitHub下载代码后运行报错

#### 错误信息

```
TypeError: 'NoneType' object is not callable
ModuleNotFoundError: No module named 'duckdb'
AttributeError: 'DataManager' object has no attribute 'get_connection_status'
```

#### 快速解决方案

**一键修复脚本（推荐）**

```powershell
# 1. 更新到最新代码
git pull origin main

# 2. 重新安装依赖
python -m pip install -r requirements.txt

# 3. 重新安装 easyxt_backtest
python -m pip uninstall easyxt_backtest -y
python -m pip install -e ./easyxt_backtest

# 4. 启动程序
python run_gui.py
```

**如果上面不行，试试完整重装：**

```powershell
# 删除虚拟环境
Remove-Item -Recurse -Force .venv

# 重新创建虚拟环境
python -m venv .venv
& .\.venv\Scripts\Activate.ps1

# 安装所有依赖
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e ./easyxt_backtest

# 启动程序
python run_gui.py
```

#### 常见问题

**Q: pip 命令报错怎么办？**

A: 使用 `python -m pip` 代替 `pip`：
```powershell
# 如果这个报错
pip install xxx

# 改成这样
python -m pip install xxx
```

**Q: 提示 "ModuleNotFoundError: No module named 'duckdb'"？**

A: 安装缺失的包：
```powershell
python -m pip install duckdb pyarrow
```

**Q: 为什么本地能跑，GitHub 下载的代码不能跑？**

A: 可能是版本不同步，运行 `git pull origin main` 更新到最新代码即可。

---

### 10. 依赖安装失败

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

### 11. GUI启动失败

#### 错误信息
```
ImportError: No module named 'PyQt5'
```

#### 解决方案
```bash
pip install PyQt5
```

---

### 12. matplotlib中文字体错误

#### 错误信息

```
File "matplotlib\artist.py", line 72, in draw_wrapper
  return draw(artist)
  ...
  ymax = corners_rotated[:, 1].max()
  File "numpy\_core\_methods.py", line 44, in amax
    return umr_maximum(a, axis, None, out, keepdims, initial, where)
```

#### 问题原因

matplotlib找不到中文字体SimHei（黑体），导致绘制图表时出错。

#### 快速解决方案

**使用项目提供的字体安装工具（推荐）：**

```powershell
# 进入tools目录
cd tools

# 运行字体安装工具
python install_simhei_font.py

# 或者双击运行
.\install_simhei_font.bat
```

安装工具会自动完成：
1. ✓ 从Windows系统复制SimHei字体
2. ✓ 安装到matplotlib字体目录
3. ✓ 清除matplotlib缓存
4. ✓ 验证字体安装

#### 手动安装（如果工具失败）

**步骤1：复制字体文件**

```powershell
# 查找matplotlib字体目录
python -c "import matplotlib,os;print(os.path.join(os.path.dirname(matplotlib.__file__),'mpl-data','fonts','ttf'))"

# 复制字体（替换上面的路径）
$font_dir = "matplotlib字体目录路径"
Copy-Item "C:\Windows\Fonts\simhei.ttf" -Destination "$font_dir\simhei.ttf"
```

**步骤2：清除matplotlib缓存**

```powershell
python -c "import matplotlib,shutil;cache_dir=matplotlib.get_cachedir();shutil.rmtree(cache_dir,ignore_errors=True);print('缓存已清除')"
```

**步骤3：验证安装**

```powershell
python -c "import matplotlib.pyplot as plt;plt.rcParams['font.sans-serif']=['SimHei'];print('字体配置成功')"
```

#### 常见问题

**Q: 为什么会出现这个问题？**

A: Windows系统自带SimHei字体，但matplotlib默认不会使用系统字体，需要手动配置。

**Q: 安装工具提示找不到SimHei字体？**

A: 检查Windows字体目录是否存在该字体：
```powershell
Test-Path "C:\Windows\Fonts\simhei.ttf"
```

如果返回False，说明系统缺少该字体，需要先安装SimHei字体。

**Q: 安装后还是报错？**

A: 重启Python程序或IDE，确保matplotlib重新加载字体配置。

---

### 14. 回测报错

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

### 15. 策略运行失败

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

### 16. 回测速度慢

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

### 17. 内存占用过高

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

**最后更新**: 2026-04-10
