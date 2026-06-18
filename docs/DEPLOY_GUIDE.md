# EasyXT 新电脑完整部署攻略

> 从零到策略下单，手把手教程。

---

## 前置条件

- Windows 10/11 64 位
- Python 3.9 ~ 3.12（推荐 3.11）
- QMT/miniQMT 客户端（券商提供，模拟盘即可）
- Tushare Token（注册 https://tushare.pro/weborder/#/login?reg=344724，建议充值到 2000 积分以上以获取更高权限，回测用，可选）

---

## 第一步：克隆项目

```bash
git clone https://github.com/quant-king299/EasyXT.git
cd EasyXT
```

---

## 第二步：安装依赖

```bash
pip install -r requirements.txt
```

核心依赖：`pandas numpy duckdb requests`。如果 `requirements.txt` 缺了什么，按报错补装就行。

---

## 第三步：配置 .env 文件

在项目根目录创建 `.env`，填入以下内容：

```env
# 数据目录（必须）
STOCK_DATA_ROOT=D:/StockData
DUCKDB_PATH=D:/StockData/stock_data.ddb

# QMT 配置（实盘必须）
QMT_DATA_DIR=D:/国金QMT交易端模拟/userdata_mini
QMT_ACCOUNT_ID=你的QMT账户ID
QMT_EXE_PATH=D:/国金QMT交易端模拟/bin.x64/XtMiniQmt.exe
QMT_PASSWORD=你的QMT密码

# Tushare（可选，回测和因子分析用）
TUSHARE_TOKEN=你的TushareToken
```

> QMT_DATA_DIR 是关键路径，指向 QMT 的 `userdata_mini` 文件夹。数据目录 `D:/StockData` 需要手动创建：`mkdir D:\StockData`

---

## 第四步：安装 QMT

1. 从券商下载 QMT 或 miniQMT（模拟盘免费）
2. 安装后启动 QMT，登录交易账户
3. 确认 QMT 右下角显示"已连接"

验证 QMT 连接：

```bash
python -c "from easy_xt import get_api; api = get_api(); api.init_data()"
```

看到 `[OK] Using QMT (xtquant) as data source` 即成功。

---

## 第五步：下载数据（可选但强烈建议）

### 方式一：GUI 下载（推荐）

```bash
python run_gui.py
```

依次下载以下数据（在 "Tushare下载" 标签页）：

| 数据 | 用途 | 耗时 |
|------|------|------|
| 股票日线 + 市值 | 回测、红利低波策略 | 10-30 分钟 |
| 可转债基本信息 + 日行情 | 可转债策略 | 5-10 分钟 |
| ETF 基本信息 + 日行情 | ETF 策略 | 5-10 分钟 |
| 分红数据 | 红利低波策略 | 2-5 分钟 |

### 方式二：跳过，让策略自动补

不下载也能跑。策略第一次运行时会从 QMT 自动拉数据并写入 DuckDB，第二次就秒出了。

---

## 第六步：安装策略包（知识星球）

1. 从知识星球下载 `cb_etf_strategies.zip`
2. 解压，将 `strategies/` 文件夹复制到 EasyXT 项目根目录
3. 目录结构应为：
   ```
   EasyXT/
   ├── strategies/
   │   ├── __init__.py
   │   └── quant_strategies/
   │       ├── __init__.py
   │       ├── run_cb_double_low.py
   │       ├── run_cb_three_low.py
   │       ├── run_etf_trend.py
   │       ├── run_limit_up.py
   │       ├── run_dividend_lowvol.py
   │       ├── run_cb_factor_rotation.py
   │       ├── run_etf_hot_theme.py
   │       ├── cb_double_low.py
   │       ├── cb_three_low.py
   │       ├── etf_trend.py
   │       ├── limit_up.py
   │       ├── dividend_lowvol.py
   │       ├── cb_factor_rotation.py
   │       ├── etf_hot_theme.py
   │       └── data_utils.py
   ├── easy_xt/
   ├── .env
   └── ...
   ```

---

## 第七步：验证

### 1. 验证基础连接

```bash
python -c "from easy_xt import get_api; api = get_api(); print(api.init_data())"
```

### 2. 验证策略（dry_run 模式，不下单）

```bash
# 可转债双低
python strategies/quant_strategies/run_cb_double_low.py

# ETF 强势轮动
python strategies/quant_strategies/run_etf_hot_theme.py

# 涨停板（需在交易时段）
python strategies/quant_strategies/run_limit_up.py
```

### 3. 验证 DuckDB 数据

```bash
python -c "
import duckdb
con = duckdb.connect('D:/StockData/stock_data.ddb', read_only=True)
tables = con.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
for t in tables:
    cnt = con.execute(f'SELECT COUNT(*) FROM {t[0]}').fetchone()[0]
    print(f'{t[0]}: {cnt} rows')
con.close()
"
```

---

## 第八步：实盘下单

确认 QMT 已启动并登录交易账户后：

```bash
python strategies/quant_strategies/run_cb_double_low.py --trade
```

**安全提示**：首次实盘建议先 dry_run 看信号，确认逻辑符合预期再 --trade。

---

## 常见问题

### Q1: `ModuleNotFoundError: No module named 'xxx'`
```bash
pip install xxx
```
常见的缺：`duckdb` `requests` `pandas` `numpy` `PyQt5`

### Q2: `交易服务连接失败，错误码: -1`
- QMT 没有启动或没有登录
- `QMT_DATA_DIR` 路径写错了

### Q3: DuckDB 提示文件被锁定
- 关掉 QMT 或 GUI 再试
- DuckDB 同时只能被一个进程写入

### Q4: Tushare 下载报 token 无效
- 去 https://tushare.pro/weborder/#/login?reg=344724 注册（建议充值到 2000 积分以上）
- 确认 `.env` 里 `TUSHARE_TOKEN=` 后面的 token 正确

### Q5: 东方财富 API 返回空数据
- 被临时限流了，等 5-10 分钟
- 限流恢复前策略会自动降级用 QMT 数据

---

## 策略速查

| 策略 | dry_run（看信号） | 实盘下单 |
|------|-------------------|---------|
| 可转债双低 | `python strategies/quant_strategies/run_cb_double_low.py` | 加 `--trade` |
| 可转债三低 | `python strategies/quant_strategies/run_cb_three_low.py` | 加 `--trade` |
| 可转债因子轮动 | `python strategies/quant_strategies/run_cb_factor_rotation.py` | 加 `--trade` |
| ETF 趋势 | `python strategies/quant_strategies/run_etf_trend.py` | 加 `--trade` |
| ETF 强势轮动 | `python strategies/quant_strategies/run_etf_hot_theme.py` | 加 `--trade` |
| 红利低波 | `python strategies/quant_strategies/run_dividend_lowvol.py` | 加 `--trade` |
| 涨停板 | `python strategies/quant_strategies/run_limit_up.py` | 加 `--trade` |
