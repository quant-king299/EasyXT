# 📊 DuckDB 数据库使用指南

> 本指南详细介绍如何在EasyXT项目中初始化、使用和维护DuckDB数据库。

---

## 📋 目录

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
- ✅ **零配置**：无需安装数据库服务器
- ✅ **高性能**：向量化查询引擎，速度极快
- ✅ **轻量级**：单个文件存储所有数据
- ✅ **SQL支持**：完整的SQL-99标准
- ✅ **Python友好**：与pandas完美集成

### 在EasyXT中的应用

EasyXT使用DuckDB存储：
- 股票日线数据
- 市值数据
- 财务数据
- 技术指标数据

---

## 为什么使用DuckDB

### 性能对比

| 数据源 | 1000次回测耗时 | 数据加载速度 | 适用场景 |
|--------|----------------|--------------|----------|
| **DuckDB** | ~10秒 | ⚡⚡⚡⚡⚡ | 高频回测、因子分析 |
| **QMT本地** | ~30秒 | ⚡⚡⚡⚡ | 实盘交易 |
| **Tushare** | ~300秒 | ⚡⚡ | 数据下载 |

### 优势

1. **极速回测**
   - 批量因子计算速度快10倍以上
   - 适合全市场扫描

2. **离线使用**
   - 下载一次，永久使用
   - 不受网络和API限制

3. **数据完整**
   - 历史数据完整
   - 不会因为API问题导致数据缺失

4. **易于管理**
   - 单个文件，方便备份
   - 跨平台兼容

---

## 快速开始

### 方式一：使用GUI下载数据（推荐新手）

```bash
# 1. 启动GUI
python run_gui.py

# 2. 切换到"📥 Tushare下载"标签页

# 3. 配置参数
# - 输入Tushare Token
# - 选择股票数量（建议先100只）
# - 选择时间范围（建议先30天）

# 4. 点击"开始下载"
# 数据会自动保存到 D:/StockData/stock_data.ddb
```

### 方式二：使用命令行工具

```bash
cd "101因子/101因子分析平台/scripts"
python init_data.py

# 选择模式：
# 1. 快速测试模式（10只股票，2年数据）
# 2. 标准模式（100只股票，5年数据）
# 3. 完整模式（全市场股票，10年数据）
```

### 方式三：使用Python脚本

```python
from easyxt_backtest import DataManager

# 创建数据管理器
dm = DataManager(duckdb_path='D:/StockData/stock_data.ddb')

# 下载数据
dm.download_and_save(
    symbols=['000001.SZ', '600000.SH'],
    start_date='2020-01-01',
    end_date='2023-12-31',
    symbol_type='stock'
)

# 保存
dm.close()
```

---

## 数据下载与初始化

### 前置准备

#### 1. 安装DuckDB

```bash
pip install duckdb
```

#### 2. 配置Tushare Token（如果需要）

创建 `.env` 文件：
```env
TUSHARE_TOKEN=你的Token
```

#### 3. 创建数据目录

```bash
# Windows PowerShell
New-Item -ItemType Directory -Path "D:\StockData" -Force

# Windows CMD
mkdir D:\StockData

# Linux/Mac
mkdir -p ~/StockData
```

---

### 完整初始化流程

#### Step 1: 选择数据源

EasyXT支持多种数据源，按优先级自动选择：

```
DuckDB > QMT > Tushare > akshare > qstock
```

**建议**：
- 有DuckDB数据时优先使用（速度最快）
- 没有DuckDB时使用QMT本地数据
- 都没有时使用Tushare在线下载

#### Step 2: 下载股票列表

```python
import tushare as ts
import os
from dotenv import load_dotenv

load_dotenv()

ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

# 获取股票列表
df = pro.stock_basic(exchange='', list_status='L',
                    fields='ts_code,symbol,name,area,industry,list_date')

# 保存到文件
df.to_csv('stock_list.csv', index=False)
```

#### Step 3: 批量下载历史数据

```python
from easyxt_backtest import DataManager
import pandas as pd

# 读取股票列表
stocks = pd.read_csv('stock_list.csv')
symbols = stocks['ts_code'].tolist()[:100]  # 先下载100只测试

# 创建数据管理器
dm = DataManager(duckdb_path='D:/StockData/stock_data.ddb')

# 批量下载
for symbol in symbols:
    try:
        dm.download_and_save(
            symbols=[symbol],
            start_date='2020-01-01',
            end_date='2023-12-31',
            symbol_type='stock'
        )
        print(f"✓ {symbol} 下载完成")
    except Exception as e:
        print(f"✗ {symbol} 下载失败: {e}")

dm.close()
```

#### Step 4: 下载市值数据（可选但推荐）

```bash
# 使用GUI下载
python run_gui.py
# 切换到"📥 Tushare下载"标签页
# 点击"开始下载市值数据"
```

---

## 数据验证

### 检查数据库文件

```bash
# 检查文件是否存在
ls -lh D:/StockData/stock_data.ddb

# 查看文件大小
# 正常情况下，100只股票5年数据约50-100MB
```

### 使用Python验证

```python
import duckdb

# 连接数据库
con = duckdb.connect('D:/StockData/stock_data.ddb', read_only=True)

# 1. 查看所有表
print("=== 数据表列表 ===")
tables = con.execute("SHOW TABLES").fetchall()
for table in tables:
    print(f"  - {table[0]}")

# 2. 查看股票数量
print("\n=== 股票数量 ===")
count = con.execute("""
    SELECT COUNT(DISTINCT stock_code) FROM stock_data
""").fetchone()[0]
print(f"  共 {count} 只股票")

# 3. 查看数据时间范围
print("\n=== 数据时间范围 ===")
date_range = con.execute("""
    SELECT
        MIN(date) as start_date,
        MAX(date) as end_date,
        COUNT(*) as total_records
    FROM stock_data
""").fetchone()
print(f"  起始: {date_range[0]}")
print(f"  结束: {date_range[1]}")
print(f"  记录数: {date_range[2]:,}")

# 4. 查看最新数据
print("\n=== 最新数据预览 ===")
latest = con.execute("""
    SELECT stock_code, date, close, volume
    FROM stock_data
    ORDER BY date DESC
    LIMIT 5
""").fetchdf()
print(latest)

con.close()
```

### 使用环境检查工具

```bash
python tools/check_env.py
```

自动检查：
- ✅ DuckDB数据库是否存在
- ✅ 数据表数量和记录数
- ✅ 数据时间范围

---

## 日常使用

### 在回测中使用

```python
from easyxt_backtest import BacktestEngine, DataManager
from easyxt_backtest.strategies import SmallCapStrategy

# 1. 创建数据管理器
dm = DataManager(duckdb_path='D:/StockData/stock_data.ddb')

# 2. 创建回测引擎
engine = BacktestEngine(
    initial_cash=1000000,
    data_manager=dm
)

# 3. 运行回测
strategy = SmallCapStrategy(select_num=5)
result = engine.run_backtest(
    strategy=strategy,
    start_date='2023-01-01',
    end_date='2023-12-31'
)

# 4. 查看结果
result.print_summary()
```

### 在因子分析中使用

```python
from easy_xt.factor_library import create_easy_factor

# 1. 初始化EasyFactor
ef = create_easy_factor('D:/StockData/stock_data.ddb')

# 2. 获取股票列表
stocks = ef.get_stock_list(limit=10)

# 3. 批量分析
results = ef.analyze_batch(
    stock_list=stocks,
    start_date='2023-01-01',
    end_date='2023-12-31'
)

# 4. 查看综合评分
print(results['score'])
```

### 直接使用SQL查询

```python
import duckdb

# 连接数据库
con = duckdb.connect('D:/StockData/stock_data.ddb')

# 查询特定股票
df = con.execute("""
    SELECT * FROM stock_data
    WHERE stock_code = '000001.SZ'
    ORDER BY date DESC
    LIMIT 100
""").fetchdf()

print(df.head())

# 计算技术指标
df = con.execute("""
    SELECT
        stock_code,
        date,
        close,
        AVG(close) OVER (
            PARTITION BY stock_code
            ORDER BY date
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ) as ma20
    FROM stock_data
    WHERE stock_code = '000001.SZ'
    ORDER BY date DESC
    LIMIT 100
""").fetchdf()

con.close()
```

---

## 数据更新

### 增量更新（推荐）

```python
from easyxt_backtest import DataManager
from datetime import datetime, timedelta

dm = DataManager(duckdb_path='D:/StockData/stock_data.ddb')

# 更新最近30天的数据
end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

dm.download_and_save(
    symbols=['000001.SZ', '600000.SH'],
    start_date=start_date,
    end_date=end_date,
    symbol_type='stock'
)

# 自动去重，不会重复插入相同日期的数据
dm.close()
```

### 使用GUI更新

```bash
python run_gui.py
# 切换到"📥 Tushare下载"标签页
# 设置较短时间范围（如7天）
# 点击"开始下载"
```

### 定时更新脚本

创建 `update_data.py`：

```python
#!/usr/bin/env python3
"""定时更新DuckDB数据"""

from easyxt_backtest import DataManager
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_stock_data():
    """更新股票数据"""
    dm = DataManager(duckdb_path='D:/StockData/stock_data.ddb')

    # 更新最近7天
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    logger.info(f"开始更新数据: {start_date} ~ {end_date}")

    # 获取所有股票
    stocks = dm.get_stock_list()

    # 批量更新
    for i, stock in enumerate(stocks, 1):
        try:
            dm.download_and_save(
                symbols=[stock],
                start_date=start_date,
                end_date=end_date,
                symbol_type='stock'
            )
            if i % 10 == 0:
                logger.info(f"进度: {i}/{len(stocks)}")
        except Exception as e:
            logger.error(f"{stock} 更新失败: {e}")

    dm.close()
    logger.info("数据更新完成")

if __name__ == '__main__':
    update_stock_data()
```

使用Windows任务计划程序定时运行：
```bash
# 每周日凌晨2点执行
schtasks /create /tn "更新股票数据" /tr "python C:\path\to\update_data.py" /sc weekly /d sun /st 02:00
```

---

## 备份与维护

### 数据备份

#### 方式一：手动备份

```bash
# Windows PowerShell
$timestamp = Get-Date -Format "yyyyMMdd"
Copy-Item "D:\StockData\stock_data.ddb" "D:\StockData\backup\stock_data_$timestamp.ddb"

# Linux/Mac
timestamp=$(date +%Y%m%d)
cp ~/StockData/stock_data.ddb ~/StockData/backup/stock_data_$timestamp.ddb
```

#### 方式二：自动备份脚本

```python
#!/usr/bin/env python3
"""自动备份DuckDB数据库"""

import shutil
from datetime import datetime
import os

def backup_database():
    source = 'D:/StockData/stock_data.ddb'
    backup_dir = 'D:/StockData/backup'

    # 创建备份目录
    os.makedirs(backup_dir, exist_ok=True)

    # 生成备份文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'{backup_dir}/stock_data_{timestamp}.ddb'

    # 复制文件
    shutil.copy2(source, backup_file)
    print(f"✓ 备份完成: {backup_file}")

    # 清理旧备份（保留最近10个）
    backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.ddb')])
    if len(backups) > 10:
        for old_backup in backups[:-10]:
            os.remove(f'{backup_dir}/{old_backup}')
            print(f"✓ 删除旧备份: {old_backup}")

if __name__ == '__main__':
    backup_database()
```

### 数据库优化

```python
import duckdb

con = duckdb.connect('D:/StockData/stock_data.ddb')

# 1. 优化表
con.execute("PRAGMA optimize")

# 2. 分析表统计信息
con.execute("ANALYZE")

# 3. 清理未使用的空间
con.execute("VACUUM")

con.close()
```

### 数据完整性检查

```python
import duckdb

def check_data_integrity():
    con = duckdb.connect('D:/StockData/stock_data.ddb')

    issues = []

    # 1. 检查重复记录
    duplicates = con.execute("""
        SELECT stock_code, date, COUNT(*) as count
        FROM stock_data
        GROUP BY stock_code, date
        HAVING COUNT(*) > 1
    """).fetchdf()

    if not duplicates.empty:
        issues.append(f"发现重复记录: {len(duplicates)} 条")

    # 2. 检查缺失值
    nulls = con.execute("""
        SELECT COUNT(*) FROM stock_data
        WHERE close IS NULL OR volume IS NULL
    """).fetchone()[0]

    if nulls > 0:
        issues.append(f"发现缺失值: {nulls} 条")

    # 3. 检查数据异常
    abnormal = con.execute("""
        SELECT COUNT(*) FROM stock_data
        WHERE close <= 0 OR volume < 0
    """).fetchone()[0]

    if abnormal > 0:
        issues.append(f"发现异常数据: {abnormal} 条")

    con.close()

    if issues:
        print("❌ 发现问题:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ 数据完整性检查通过")

if __name__ == '__main__':
    check_data_integrity()
```

---

## 常见问题

### Q1: 数据库文件太大怎么办？

**A**: 可以按需删除不需要的数据：

```python
import duckdb

con = duckdb.connect('D:/StockData/stock_data.ddb')

# 只保留最近3年的数据
con.execute("""
    DELETE FROM stock_data
    WHERE date < DATE('now', '-3 years')
""")

con.execute("VACUUM")  # 回收空间
con.close()
```

### Q2: 如何只下载特定股票的数据？

**A**: 创建股票列表文件：

```python
# 创建 my_stocks.txt
stocks = """
000001.SZ
000002.SZ
600000.SH
600519.SH
"""

with open('my_stocks.txt', 'w') as f:
    f.write(stocks.strip())

# 下载
with open('my_stocks.txt') as f:
    symbols = [line.strip() for line in f if line.strip()]

dm.download_and_save(symbols=symbols, ...)
```

### Q3: 数据库损坏了怎么办？

**A**: 使用备份恢复：

```bash
# 1. 停止所有程序
# 2. 恢复备份
cp D:/StockData/backup/stock_data_20260301.ddb D:/StockData/stock_data.ddb

# 3. 验证
python tools/check_env.py
```

### Q4: 如何迁移到其他电脑？

**A**: 直接复制文件：

```bash
# 1. 复制数据库文件
scp user@old:/path/to/stock_data.ddb /path/to/new/location/

# 2. 更新配置
# 修改代码中的 duckdb_path
```

### Q5: DuckDB vs 其他数据库？

**A**:

| 特性 | DuckDB | SQLite | PostgreSQL |
|------|--------|--------|------------|
| 性能 | ⚡⚡⚡⚡⚡ | ⚡⚡⚡ | ⚡⚡⚡⚡ |
| 易用性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 部署 | 单文件 | 单文件 | 需服务器 |
| 分析优化 | ✅ | ❌ | ✅ |
| 推荐场景 | 回测分析 | 轻量存储 | 生产环境 |

---

## 📚 相关资源

- [DuckDB官方文档](https://duckdb.org/docs/)
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - 疑难问题解答
- [101因子平台使用指南](../101因子/101因子分析平台/README.md)
- [回测系统指南](../../easyxt_backtest/README.md)

---

**最后更新**: 2026-03-08
**版本**: 1.0.0
