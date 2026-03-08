# 🔧 疑难问题解答（FAQ）

> 遇到问题？先看这里！本文档收集了用户最常遇到的问题和解决方案。

---

## 📋 目录

- [数据相关](#数据相关)
  - [DuckDB数据库找不到](#1-duckdb数据库找不到)
  - [数据下载失败](#2-数据下载失败)
  - [Tushare配置问题](#3-tushare配置问题)
- [安装相关](#安装相关)
- [运行相关](#运行相关)
- [性能相关](#性能相关)

---

## 数据相关

### 1. DuckDB数据库找不到

#### 🚨 错误信息
```
IO Error: Cannot open file "D:\StockData\stock_data.ddb": 系统找不到指定的路径。
```

#### 🔍 问题原因
- 项目代码中硬编码了DuckDB数据库路径：`D:/StockData/stock_data.ddb`
- 从GitHub下载项目后，本地没有这个数据库文件
- 需要先下载股票数据才能使用回测、因子分析等功能

#### ✅ 解决方案

**方案一：使用GUI下载数据（推荐，最简单）**

1. 启动GUI应用：
   ```bash
   python run_gui.py
   ```

2. 配置Tushare Token：
   - 访问 https://tushare.pro 注册并获取Token
   - 在项目根目录创建 `.env` 文件：
     ```env
     TUSHARE_TOKEN=你的Token
     ```

3. 在GUI中下载数据：
   - 切换到 **"📥 Tushare下载"** 标签页
   - 输入Tushare Token
   - 点击 **"🔗 测试连接"** 验证Token
   - 配置下载参数（建议：100只股票，30天）
   - 点击 **"🚀 开始下载市值数据"**
   - 等待下载完成

**方案二：使用命令行下载数据**

```bash
cd "101因子\101因子分析平台\scripts"
python init_data.py
```

选择模式：
1. 快速测试模式（10只股票，2年数据）
2. 标准模式（100只股票，5年数据）
3. 完整模式（全市场股票，10年数据）

**方案三：手动创建数据库目录**

如果只是目录不存在：
```bash
# Windows PowerShell
New-Item -ItemType Directory -Path "D:\StockData" -Force

# Windows CMD
mkdir D:\StockData

# Linux/Mac
mkdir -p ~/StockData
```

#### 📝 详细指南

查看完整的DuckDB初始化指南：[DuckDB数据库使用指南](docs/assets/DUCKDB_GUIDE.md)

---

### 2. 数据下载失败

#### 🚨 常见错误

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

#### ✅ 解决方案

**检查Token是否有效：**
1. 登录 Tushare Pro
2. 进入「用户中心」→「接口Token」
3. 确认Token没有过期

**检查积分是否足够：**
1. 在Tushare网站查看账户积分
2. 基础功能需要一定积分（注册后会获得初始积分）
3. 高级功能需要更多积分（可能需要充值）

**优化下载策略：**
```bash
# 1. 减少下载数量
# GUI中：股票数量改为 10-50 只

# 2. 减少时间范围
# GUI中：时间范围改为 7-14 天

# 3. 分批下载
# 多次运行，每次下载不同时间段的数据
```

**使用其他数据源：**
项目支持多种数据源，会自动降级：
```
DuckDB > QMT > Tushare > akshare > qstock
```

如果你有QMT终端，可以直接使用QMT本地数据，无需下载。

---

### 3. Tushare配置问题

#### 🚨 问题：Token配置后仍然报错

```
ValueError: TUSHARE_TOKEN not found in environment variables
```

#### ✅ 解决方案

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
   # 正确格式
   TUSHARE_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

   # 错误格式（不要加引号）
   TUSHARE_TOKEN="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
   ```

3. 验证环境变量：
   ```bash
   python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('✓ Token:', os.getenv('TUSHARE_TOKEN')[:10] + '...') if os.getenv('TUSHARE_TOKEN') else print('✗ Token未配置')"
   ```

**手动设置环境变量（临时）：**

```python
import os
os.environ['TUSHARE_TOKEN'] = '你的Token'
```

**永久设置环境变量：**

```powershell
# PowerShell
setx TUSHARE_TOKEN "你的Token"

# CMD
setx TUSHARE_TOKEN "你的Token"
```

⚠️ **注意：** 设置后需要重启终端/IDE才能生效。

---

## 安装相关

### 4. xtquant安装失败

#### 🚨 错误信息
```
ImportError: cannot import name 'datacenter' from 'xtquant'
```

#### ✅ 解决方案

**必须使用项目提供的特殊版本！**

1. 下载特殊版本：
   - 访问：https://github.com/quant-king299/EasyXT/releases/tag/v1.0.0
   - 下载：`xtquant.rar`

2. 解压到项目根目录：
   ```
   miniqmt扩展/
   ├── xtquant/          ← 解压到这里
   ├── easy_xt/
   └── README.md
   ```

3. 验证安装：
   ```bash
   python -c "from xtquant import datacenter; print('✓ xtquant OK')"
   ```

❌ **不要使用 `pip install xtquant` 安装官方版本！**

---

### 5. 依赖安装失败

#### 🚨 常见错误

**错误1：pip安装超时**
```
ReadTimeoutError: HTTPSConnectionPool read timeout
```

**错误2：某些包无法安装**
```
ERROR: Could not find a version that satisfies the requirement
```

#### ✅ 解决方案

**使用国内镜像源：**
```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

**升级pip：**
```bash
python -m pip install --upgrade pip
```

**逐个安装依赖：**
```bash
pip install pandas numpy PyQt5 streamlit
pip install -e ./easy_xt
```

---

## 运行相关

### 6. GUI启动失败

#### 🚨 错误信息
```
ImportError: No module named 'PyQt5'
```

#### ✅ 解决方案

**安装GUI依赖：**
```bash
pip install PyQt5 PyQt5-tools
```

**检查依赖完整性：**
```bash
cd "gui_app"
pip install -r requirements.txt
```

---

### 7. 回测报错

#### 🚨 常见错误

**错误1：数据为空**
```
ValueError: No data available for the specified date range
```

**错误2：股票代码不存在**
```
KeyError: 'STOCK_CODE not found'
```

#### ✅ 解决方案

**检查数据源优先级：**
```python
# 确认DuckDB数据库有数据
import duckdb
con = duckdb.connect('D:/StockData/stock_data.ddb')
result = con.execute("SELECT COUNT(*) FROM stock_data").fetchone()
print(f"数据总量: {result[0]} 条")
con.close()
```

**使用QMT数据（如果安装了QMT）：**
```python
from easy_xt import get_api
api = get_api()
api.init_data()  # 使用QMT数据
```

**检查股票代码格式：**
- 正确：`000001.SZ`, `600000.SH`
- 错误：`000001`, `600000`, `sz000001`

---

### 8. 策略运行失败

#### 🚨 常见错误

**错误1：账户未连接**
```
ConnectionError: 无法连接到交易账户
```

**错误2：权限不足**
```
PermissionError: 没有交易权限
```

#### ✅ 解决方案

**检查QMT路径配置：**
```python
# 确保路径正确
USERDATA_PATH = r"C:\QMT\userdata"  # 或你的QMT安装路径
```

**检查QMT是否登录：**
- 确保QMT客户端已启动
- 确保已登录交易账户
- 确保账户有交易权限

**使用模拟账户测试：**
```python
# 先在模拟环境测试
api.add_account('模拟账户ID')
```

---

## 性能相关

### 9. 回测速度慢

#### 📊 性能对比

| 数据源 | 回测1000次耗时 | 性能 |
|--------|----------------|------|
| DuckDB | ~10秒 | ⚡⚡⚡⚡⚡ |
| QMT本地 | ~30秒 | ⚡⚡⚡⚡ |
| Tushare | ~300秒 | ⚡⚡ |

#### ✅ 优化建议

**优先使用DuckDB：**
```python
from easyxt_backtest import DataManager
dm = DataManager(duckdb_path='D:/StockData/stock_data.ddb')
```

**批量计算：**
```python
# ❌ 慢：逐个股票计算
for stock in stock_list:
    result = calculate_factor(stock)

# ✅ 快：批量计算
results = calculate_factors_batch(stock_list)
```

**使用向量化操作：**
```python
# ❌ 慢：循环
for i in range(len(df)):
    df.loc[i, 'ma5'] = df['close'].iloc[i-5:i].mean()

# ✅ 快：向量化
df['ma5'] = df['close'].rolling(5).mean()
```

---

### 10. 内存占用过高

#### 🚨 问题
```
MemoryError: Unable to allocate array
```

#### ✅ 解决方案

**分批处理：**
```python
# ❌ 一次加载全部数据
all_data = load_all_stocks()  # 可能占用几GB内存

# ✅ 分批加载
for batch in stock_batches:
    data = load_batch(batch)
    process(data)
```

**使用生成器：**
```python
def data_generator(stocks):
    for stock in stocks:
        yield load_stock_data(stock)

for data in data_generator(stock_list):
    process(data)  # 处理完立即释放内存
```

**清理缓存：**
```python
import gc
del large_dataframe
gc.collect()
```

---

## 🔍 快速诊断工具

### 一键检查脚本

创建 `check_env.py` 文件：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速环境检查工具"""

import sys
import os
from pathlib import Path

print("=" * 70)
print("EasyXT 环境检查工具")
print("=" * 70)

# 1. Python版本
print(f"\n[1] Python版本: {sys.version}")
if sys.version_info < (3, 9):
    print("    ⚠️ 警告：建议使用Python 3.9+")
else:
    print("    ✓ 版本正常")

# 2. xtquant
print("\n[2] xtquant模块:")
try:
    from xtquant import datacenter
    print("    ✓ xtquant已安装")
except ImportError:
    print("    ✗ xtquant未安装或版本错误")
    print("    解决方案：下载特殊版本并解压到项目根目录")

# 3. easy_xt
print("\n[3] easy_xt模块:")
try:
    from easy_xt import get_api
    print("    ✓ easy_xt已安装")
except ImportError:
    print("    ✗ easy_xt未安装")
    print("    解决方案：pip install -e ./easy_xt")

# 4. DuckDB
print("\n[4] DuckDB数据库:")
duckdb_paths = [
    'D:/StockData/stock_data.ddb',
    'd:/stockdata/stock_data.ddb',
    './data/stock_data.ddb'
]
db_found = False
for path in duckdb_paths:
    if Path(path).exists():
        print(f"    ✓ 找到数据库: {path}")
        db_found = True
        break
if not db_found:
    print("    ✗ 未找到DuckDB数据库")
    print("    解决方案：运行 python run_gui.py 下载数据")

# 5. Tushare Token
print("\n[5] Tushare配置:")
try:
    from dotenv import load_dotenv
    load_dotenv()
    token = os.getenv('TUSHARE_TOKEN')
    if token:
        print(f"    ✓ Token已配置: {token[:10]}...")
    else:
        print("    ⚠️ Token未配置")
        print("    解决方案：在项目根目录创建.env文件并添加TUSHARE_TOKEN")
except ImportError:
    print("    ⚠️ python-dotenv未安装")
    print("    解决方案：pip install python-dotenv")

# 6. GUI依赖
print("\n[6] GUI依赖:")
try:
    import PyQt5
    print("    ✓ PyQt5已安装")
except ImportError:
    print("    ✗ PyQt5未安装")
    print("    解决方案：pip install PyQt5")

print("\n" + "=" * 70)
print("检查完成！")
print("=" * 70)
```

**使用方法：**
```bash
python check_env.py
```

---

## 📞 获取更多帮助

### 官方文档
- [项目README](README.md)
- [101因子平台指南](101因子/101因子分析平台/README.md)
- [回测系统指南](easyxt_backtest/README.md)

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

**最后更新**: 2026-03-08
