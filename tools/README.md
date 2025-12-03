# 深圳股票日线数据下载工具

本工具包提供了批量下载和补充深圳股票日线数据的功能，专门用于补充 `D:\国金QMT交易端模拟\userdata_mini\datadir\SZ\86400` 目录下的深圳股票日线数据。

## 工具介绍

### 1. download_sz_stocks.py (深圳股票)
最简化的命令行工具，直接调用xtdata下载深圳股票日线数据。

#### 使用方法：

```bash
# 下载所有深圳股票日线数据
python tools/download_sz_stocks.py

# 强制重新下载所有数据
python tools/download_sz_stocks.py --force

# 下载指定股票
python tools/download_sz_stocks.py --stocks 000001.SZ,000002.SZ,000651.SZ

# 下载指定日期范围的数据
python tools/download_sz_stocks.py --start-date 20240101 --end-date 20241231

# 演示模式（只下载几只股票）
python tools/download_sz_stocks.py --demo
```

### 2. download_sh_stocks.py (上海股票)
用于下载上海股票日线数据，存储在 `D:\国金QMT交易端模拟\userdata_mini\datadir\SH\86400` 目录。

#### 使用方法：

```bash
# 下载所有上海股票日线数据
python tools/download_sh_stocks.py

# 强制重新下载所有数据
python tools/download_sh_stocks.py --force

# 下载指定股票
python tools/download_sh_stocks.py --stocks 600000.SH,600036.SH,600519.SH

# 下载指定日期范围的数据
python tools/download_sh_stocks.py --start-date 20240101 --end-date 20241231

# 演示模式（只下载几只股票）
python tools/download_sh_stocks.py --demo
```

### 3. download_all_stocks.py (全部A股)
同时下载深圳和上海全部A股日线数据。

#### 使用方法：

```bash
# 下载所有A股日线数据
python tools/download_all_stocks.py

# 强制重新下载所有数据
python tools/download_all_stocks.py --force

# 下载指定股票
python tools/download_all_stocks.py --stocks 000001.SZ,600000.SH

# 下载指定日期范围的数据
python tools/download_all_stocks.py --start-date 20240101 --end-date 20241231

# 演示模式（只下载几只股票）
python tools/download_all_stocks.py --demo
```

### 4. supplement_sz_daily_data.py
功能更完整的工具，包含数据文件存在性检查等功能。

#### 使用方法：

```bash
# 直接运行交互式界面
python tools/supplement_sz_daily_data.py
```

### 5. batch_download_sz_daily_data.py
最完整的工具，包含详细的日志记录和统计功能。

#### 使用方法：

```bash
# 直接运行交互式界面
python tools/batch_download_sz_daily_data.py
```

## 功能特点

1. **自动获取股票列表**：自动从迅投API获取所有深圳/上海A股股票代码
2. **智能跳过已存在数据**：避免重复下载已有的数据文件
3. **批量下载支持**：支持并发下载多只股票数据
4. **进度显示**：实时显示下载进度和统计信息
5. **错误处理**：完善的错误处理机制，单只股票下载失败不影响整体流程
6. **灵活配置**：支持指定股票列表、日期范围等参数

## 数据存储说明

股票日线数据存储在以下目录结构中：
```
D:\国金QMT交易端模拟\userdata_mini\datadir\
├── SZ\                             # 深圳交易所
│   └── 86400\                      # 日线数据（86400秒=1天）
│       ├── 000001.DAT
│       ├── 000002.DAT
│       └── ...
└── SH\                             # 上海交易所
    └── 86400\                      # 日线数据（86400秒=1天）
        ├── 600000.DAT
        ├── 600036.DAT
        └── ...
```

其中：
- `SZ` 表示深圳交易所，`SH` 表示上海交易所
- `86400` 表示日线数据（86400秒=1天）
- `.DAT` 文件包含股票的历史日线数据

## 使用建议

1. **首次使用**：建议先使用演示模式测试工具是否正常工作
2. **定期更新**：建议每周或每月运行一次工具补充最新数据
3. **网络环境**：确保网络连接稳定，避免下载过程中断
4. **磁盘空间**：确保有足够的磁盘空间存储数据文件

## 常见问题

### 1. 下载速度慢
- 原因：为了避免对服务器造成压力，工具在每次下载间添加了延迟
- 解决：可以适当调整代码中的sleep时间

### 2. 部分股票下载失败
- 原因：某些股票可能已退市或数据源问题
- 解决：工具会自动跳过并继续下载其他股票

### 3. 数据目录权限问题
- 原因：可能没有写入数据目录的权限
- 解决：以管理员身份运行或检查目录权限

## 技术说明

工具基于 `xtquant.xtdata` 模块实现，主要调用以下API：

1. `xtdata.download_sector_data()` - 下载板块数据
2. `xtdata.get_stock_list_in_sector()` - 获取板块内股票列表
3. `xtdata.download_history_data()` - 下载历史数据

数据下载后会自动存储到迅投客户端配置的数据目录中。

## 维护说明

- 工具会自动处理股票代码标准化
- 深圳股票代码格式：000xxx.SZ, 002xxx.SZ, 300xxx.SZ, 301xxx.SZ
- 上海股票代码格式：600xxx.SH, 601xxx.SH, 603xxx.SH, 605xxx.SH, 688xxx.SH
- 自动过滤无效或格式不正确的股票代码