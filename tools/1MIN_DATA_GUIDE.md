# 1分钟数据管理指南

## 已完成的工作

### 1. 数据下载
- ✅ 从QMT下载了 511380.SH 的1分钟数据
- ✅ 数据量：58,704 条记录
- ✅ 时间范围：2025-01-24 到 2026-01-28（约1年）
- ✅ 文件大小：1.68 MB

### 2. 数据保存
- ✅ 已保存到本地数据库：`D:\StockData\raw\1min\511380.SH.parquet`
- ✅ 元数据已更新
- ✅ 数据可永久保存，不会因QMT限制而丢失

### 3. 数据验证
已验证数据包含以下字段：
- `open` - 开盘价
- `high` - 最高价
- `low` - 最低价
- `close` - 收盘价
- `volume` - 成交量
- `amount` - 成交额

## 使用工具

### 1. 自动更新数据（推荐）

**使用场景：** 定期更新QMT的最新数据到本地数据库

```bash
# 更新单只股票的1分钟数据
python tools/update_1m_data.py --stocks 511380.SH

# 更新多只股票
python tools/update_1m_data.py --stocks 511380.SH,512100.SH,159915.SZ

# 更新5分钟数据
python tools/update_1m_data.py --stocks 511380.SH --period 5m

# 强制重新下载（覆盖本地数据）
python tools/update_1m_data.py --stocks 511380.SH --force
```

**建议：** 每天或每周运行一次，保持数据最新

### 2. 从QMT下载新数据

**使用场景：** 添加新的股票/ETF的分钟数据

```bash
# 下载1分钟数据（最近1年）
python tools/download_minute_data.py --stocks 512100.SH --period 1m --verify

# 下载5分钟数据
python tools/download_minute_data.py --stocks 159915.SZ --period 5m --start-date 20250101 --end-date 20260128

# 下载多只股票
python tools/download_minute_data.py --stocks 511380.SH,512100.SH --period 1m
```

### 3. 保存到本地数据库

**使用场景：** 将QMT数据保存到本地永久存储

```bash
# 保存1分钟数据
python tools/save_1m_to_local.py

# 可以修改脚本中的股票代码和周期
```

### 4. 验证本地数据

**使用场景：** 检查本地数据库中的数据情况

```bash
python tools/verify_saved_data.py
```

### 5. 查看数据统计

**使用场景：** 查看QMT中的数据统计信息

```bash
python tools/check_data_stats.py
```

## 数据流程

```
QMT服务器 (只能保存1年)
    ↓ download_history_data()
QMT本地缓存 (1年数据)
    ↓ get_market_data()
    ↓ convert_xtdata_to_dataframe()
    ↓ save_to_local_database()
本地数据库 (永久保存)
    ↓ 101因子分析平台 / easy_xt回测框架
```

## 在回测中使用

### 1. 在101因子平台中使用

```python
import sys
from pathlib import Path
factor_path = Path("101因子/101因子分析平台/src")
sys.path.insert(0, str(factor_path))

from data_manager import LocalDataManager

manager = LocalDataManager()

# 读取1分钟数据
df = manager.load_data('511380.SH', data_type='1min')

print(df.head())
print(f"Total records: {len(df)}")
print(f"Date range: {df.index.min()} to {df.index.max()}")

manager.close()
```

### 2. 在easy_xt回测框架中使用

回测框架已集成本地数据源，优先使用本地缓存：

```python
# 在回测时自动使用本地1分钟数据
# DataSource 优先级: LOCAL > QMT > QStock > AKShare > MOCK
```

## 定期维护建议

### 每日维护
```bash
# 更新常用ETF的1分钟数据
python tools/update_1m_data.py --stocks 511380.SH,512100.SH,159915.SZ
```

### 每周维护
```bash
# 下载完整的最近1年数据（补充任何缺失）
python tools/download_minute_data.py --stocks 511380.SH --period 1m --force
python tools/save_1m_to_local.py
```

### 验证数据
```bash
# 定期检查数据完整性
python tools/verify_saved_data.py
```

## 支持的数据周期

- `1m` - 1分钟（约1年数据）
- `5m` - 5分钟
- `15m` - 15分钟
- `30m` - 30分钟
- `60m` - 60分钟
- `1d` - 日线（可下载10年）

## 常用ETF代码

- `511380.SH` - 沪深300ETF
- `512100.SH` - 中证1000ETF
- `510300.SH` - 300ETF
- `159915.SZ` - 深证ETF
- `510500.SH` - 500ETF

## 注意事项

1. **QMT限制：** QMT只能保存约1年的1分钟数据，必须定期保存到本地
2. **数据更新：** 建议每天或每周运行更新脚本
3. **数据备份：** 本地数据库位于 `D:\StockData\`，定期备份此目录
4. **文件大小：** 1年1分钟数据约1.7MB，多个标的也很小
5. **GUI支持：** 可以在GUI的"数据管理"页面查看和管理数据

## 工具文件清单

- `tools/download_minute_data.py` - 从QMT下载分钟数据
- `tools/save_1m_to_local.py` - 保存到本地数据库
- `tools/update_1m_data.py` - 自动更新数据（推荐）
- `tools/verify_saved_data.py` - 验证本地数据
- `tools/check_data_stats.py` - 查看数据统计
- `tools/download_10year_1m.py` - 批量下载多年数据

## 总结

✅ 数据已保存在本地，永久可用
✅ 可在101因子平台和回测框架中使用
✅ 定期运行更新脚本保持数据最新
✅ GUI界面支持查看和管理数据
