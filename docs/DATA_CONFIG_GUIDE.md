# 数据存储配置指南

## 📂 数据存储位置配置

本项目使用统一的`.env`文件配置所有数据存储路径，方便管理和迁移。

### 快速开始

1. **复制配置模板**
   ```bash
   cp .env.example .env
   ```

2. **编辑.env文件**
   ```bash
   # 修改数据存储位置
   STOCK_DATA_ROOT=D:/StockData
   DUCKDB_PATH=D:/StockData/stock_data.ddb
   ```

3. **重启应用程序**
   配置自动生效，无需修改代码！

### 配置项说明

#### STOCK_DATA_ROOT
- **作用**：所有数据的根目录
- **默认值**：`D:/StockData` (Windows)
- **常用路径**：
  - Windows: `D:/StockData`, `E:/Data/Stock`
  - Linux: `~/StockData`, `/data/stock`
  - Mac: `~/StockData`, `/Volumes/Data/Stock`

#### DUCKDB_PATH
- **作用**：DuckDB数据库文件路径
- **默认值**：自动使用 `{STOCK_DATA_ROOT}/stock_data.ddb`
- **说明**：通常不需要单独设置，跟随STOCK_DATA_ROOT

### 迁移数据到新位置

#### 方法1：移动后修改配置（推荐）

1. **移动数据文件**
   ```bash
   # Windows
   move D:\StockData E:\NewLocation\StockData
   
   # Linux/Mac
   mv ~/StockData /new/location/StockData
   ```

2. **修改.env配置**
   ```bash
   STOCK_DATA_ROOT=E:/NewLocation/StockData
   DUCKDB_PATH=E:/NewLocation/StockData/stock_data.ddb
   ```

3. **重启应用** - 完成！

#### 方法2：先修改配置再移动

1. **修改.env配置**
   ```bash
   STOCK_DATA_ROOT=E:/NewLocation/StockData
   ```

2. **移动数据文件**
   ```bash
   move D:\StockData E:\NewLocation\StockData
   ```

3. **重启应用** - 完成！

### 目录结构说明

配置后的目录结构：
```
{STOCK_DATA_ROOT}/
├── stock_data.ddb              # DuckDB数据库（主要数据文件）
├── raw/                        # 原始数据（可选，已弃用）
│   ├── daily/                  # 日线数据（Parquet格式）
│   └── factors/                # 因子数据（可选）
└── metadata.db                # 旧元数据库（可选，已弃用）
```

**说明**：
- ✅ **stock_data.ddb** - 推荐使用，包含所有数据
- ⚠️ **raw/** - 旧格式，可以删除
- ⚠️ **metadata.db** - 旧元数据库，已迁移到DuckDB

### 多设备共享数据

#### 在多台电脑上使用相同数据

1. **将数据存储到共享位置**
   ```bash
   # 网络驱动器
   STOCK_DATA_ROOT=Z:/SharedData/Stock
   
   # 云同步文件夹（OneDrive/Dropbox）
   STOCK_DATA_ROOT=C:/Users/YourName/OneDrive/StockData
   ```

2. **每台电脑上配置相同的.env**
   ```bash
   STOCK_DATA_ROOT=Z:/SharedData/Stock
   ```

3. **享受数据同步** - 所有设备使用相同数据！

### 磁盘空间管理

#### 清理旧文件（推荐）

如果已经迁移到DuckDB，可以删除旧文件释放空间：

```bash
# 释放约300MB空间
rm -rf {STOCK_DATA_ROOT}/raw
rm {STOCK_DATA_ROOT}/metadata.db
```

**数据迁移验证**：
- ✅ DuckDB包含所有股票数据（1100万+条记录）
- ✅ 包含所有财务数据
- ✅ 包含所有分红数据
- ✅ 旧文件可安全删除

### 常见问题

#### Q: 修改配置后数据找不到？
**A**: 检查以下几点：
1. .env文件路径是否正确（项目根目录）
2. 新路径是否存在
3. 数据文件是否已移动到新位置
4. 应用程序是否已重启

#### Q: 支持相对路径吗？
**A**: 支持！可以使用相对路径：
```bash
# 项目相对路径
STOCK_DATA_ROOT=./data
DUCKDB_PATH=./data/stock_data.ddb

# 用户主目录
STOCK_DATA_ROOT=~/StockData
```

#### Q: 想要多个独立的数据集？
**A**: 创建多个.env文件：
```bash
# 主数据集
cp .env .env.main
# 测试数据集
cp .env .env.test

# 使用时指定
python run.py --env .env.test
```

### 配置示例

#### 开发环境
```bash
# 本地开发，使用D盘
STOCK_DATA_ROOT=D:/StockData
DUCKDB_PATH=D:/StockData/stock_data.ddb
```

#### 生产环境
```bash
# 服务器环境，使用数据盘
STOCK_DATA_ROOT=/data/stock
DUCKDB_PATH=/data/stock/stock_data.ddb
```

#### 便携模式
```bash
# 数据和应用在一起，方便U盘携带
STOCK_DATA_ROOT=./data
DUCKDB_PATH=./data/stock_data.ddb
```

---

**需要帮助？**
- 查看项目文档：`docs/`目录
- 提交Issue：https://github.com/quant-king299/EasyXT/issues
- 查看故障排除：`docs/TROUBLESHOOTING.md`
