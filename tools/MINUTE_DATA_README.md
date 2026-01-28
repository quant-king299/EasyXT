# 分钟线数据下载工具

## 问题说明

之前使用 `easy_xt` API 直接获取分钟数据会失败，错误提示：
```
DataError: 无法获取股票['511380.SH']的数据
```

**原因：** QMT 需要先通过 `download_history_data()` 将数据下载到本地，然后才能通过 `get_market_data()` 读取。

## 解决方案

### 1. 新增分钟线下载工具

**工具位置：** `tools/download_minute_data.py`

**使用方法：**

```bash
# 下载单个股票的1分钟数据
python tools/download_minute_data.py --stocks 511380.SH --period 1m --start-date 20250101 --end-date 20250120 --verify

# 下载多个股票的5分钟数据
python tools/download_minute_data.py --stocks 511380.SH,512100.SH,159915.SZ --period 5m --start-date 20250101 --end-date 20250128

# 下载最近3个月的15分钟数据（不指定日期则默认最近90天）
python tools/download_minute_data.py --stocks 512100.SH --period 15m --verify

# 强制重新下载（不使用增量下载）
python tools/download_minute_data.py --stocks 511380.SH --period 1m --force
```

**参数说明：**
- `--stocks`: 股票代码（必需），多个用逗号分隔
- `--period`: 数据周期，支持 1m, 5m, 15m, 30m, 60m, 1d
- `--start-date`: 开始日期，格式 YYYYMMDD
- `--end-date`: 结束日期，格式 YYYYMMDD
- `--force`: 强制重新下载所有数据
- `--verify`: 下载后验证数据是否可用

**示例股票代码：**
- 511380.SH - 沪深300ETF
- 512100.SH - 中证1000ETF
- 159915.SZ - 深证ETF
- 510300.SH - 300ETF

### 2. GUI 界面更新

已更新 `gui_app/widgets/local_data_manager_widget.py` 中的 `SingleStockDownloadThread`：

**修改内容：**
- 日线数据：使用 `LocalDataManager._fetch_from_source()`
- 分钟数据：使用 `xtquant.xtdata` API
  1. 先调用 `xtdata.download_history_data()` 下载数据到本地
  2. 再调用 `xtdata.get_market_data()` 从本地读取数据

**支持的数据类型：**
- 日线数据 (1d)
- 1分钟数据 (1m)
- 5分钟数据 (5m)
- 15分钟数据 (15m)
- 30分钟数据 (30m)
- 60分钟数据 (60m)

### 3. API 使用方式

**直接使用 xtquant API：**

```python
from xtquant import xtdata

# 1. 下载历史数据到本地
xtdata.download_history_data(
    stock_code='511380.SH',
    period='1m',
    start_time='20250101',
    end_time='20250128'
)

# 2. 从本地读取数据
data = xtdata.get_market_data(
    stock_list=['511380.SH'],
    period='1m',
    count=0  # 0表示获取全部数据
)

# 3. 获取DataFrame
df = data['511380.SH']
```

## 注意事项

1. **数据先下载后读取：** QMT 的机制是先下载数据到本地目录，然后才能读取
2. **日期格式：** `download_history_data` 使用 YYYYMMDD 格式，而不是 YYYY-MM-DD
3. **分钟数据量：** 分钟数据量很大，建议：
   - 首次下载限制日期范围（如1-3个月）
   - 使用增量下载（默认开启）
   - 避免一次性下载过多股票的分钟数据
4. **数据存储位置：** QMT会将数据保存在 `datadir` 目录下，通常在：
   - 迷你QMT：`userdata_mini/datadir/`
   - 标准QMT：`userdata/datadir/`

## 常见问题

**Q: 下载成功但验证失败？**
A: 可能是指定日期范围内没有交易日数据，尝试：
- 扩大日期范围
- 不指定日期（使用默认最近90天）
- 检查股票代码是否正确

**Q: 速度很慢？**
A: 分钟数据量巨大，建议：
- 减少日期范围
- 减少股票数量
- 使用更长的周期（如5m、15m代替1m）

**Q: GUI手动下载失败？**
A: 确保：
- QMT客户端正在运行
- 使用命令行工具先测试是否能下载
- 检查股票代码格式正确（如511380.SH）

## 相关文件

- `tools/download_minute_data.py` - 分钟数据下载工具
- `tools/download_all_stocks.py` - 日线数据下载工具
- `gui_app/widgets/local_data_manager_widget.py` - GUI数据管理组件
- `101因子/101因子分析平台/src/data_manager/local_data_manager.py` - 本地数据管理器
