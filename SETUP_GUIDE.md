# EasyXT 增强版配置指南

> 📖 **本指南补充 INSTALL.md，提供针对不同场景的详细配置说明**
>
> ❓ **遇到问题？** 查看 **[TROUBLESHOOTING.md](docs/assets/TROUBLESHOOTING.md)** 疑难问题解答

---

## 📋 目录

- [快速诊断：我应该配置哪些内容？](#快速诊断我应该配置哪些内容)
- [1. 配置文件说明](#1-配置文件说明)
- [2. 数据源配置](#2-数据源配置)
- [3. IDE 配置（Trae/VSCode/PyCharm）](#3-ide-配置traevscodepycharm)
- [4. 常见场景配置清单](#4-常见场景配置清单)

---

## 快速诊断：我应该配置哪些内容？

### 场景选择器

请选择你的使用场景，了解需要配置哪些内容：

#### 🔴 场景 A：我想使用 QMT/miniQMT 进行交易
- ✅ **必需**：[xtquant 配置](#1-xtquant-配置)
- ✅ **必需**：[QMT 路径配置](#qmt-路径配置)
- ⚙️ **可选**：[Tushare Token（用于数据下载）](#tushare-数据源)
- ⚙️ **可选**：[DuckDB 数据库（用于加速回测）](#duckdb-数据库配置)

#### 🔵 场景 B：我想使用通达信（TDX）数据
- ✅ **必需**：[TDX 数据源配置](#tdx-通达信数据源)
- ⚙️ **可选**：[DuckDB 数据库](#duckdb-数据库配置)
- ❌ **不需要**：QMT/xtquant

#### 🟢 场景 C：我只想做回测（不交易）
- ✅ **必需**：[任一数据源（Tushare/TDX/QMT）](#3-数据源配置)
- 🚀 **推荐**：[DuckDB 数据库（提速 10-30 倍）](#duckdb-数据库配置)
- ❌ **不需要**：QMT 交易配置

#### 🟡 场景 D：我想使用雪球跟单策略
- ✅ **必需**：[xtquant 配置](#1-xtquant-配置)
- ✅ **必需**：[雪球 Cookie 配置](#雪球跟单配置)
- ✅ **必需**：[QMT 路径配置](#qmt-路径配置)

#### 🟣 场景 E：我是 Mac/Linux 用户
- ✅ **必需**：[xqshare 远程客户端配置](#xqshare-跨平台配置)
- ⚙️ **可选**：[Tushare/TDX 数据源](#3-数据源配置)
- ❌ **不需要**：本地 QMT（不支持）

---

## 1. 配置文件说明

本项目使用**统一配置系统**，支持多个配置文件。理解配置文件的优先级很重要。

### 1.1 配置文件优先级

```
运行时配置（代码中动态设置）
    ↓ (优先级最高)
用户配置文件（unified_config.json）
    ↓
系统默认配置（代码中的默认值）
    ↓ (优先级最低)
```

### 1.2 主要配置文件

| 配置文件 | 位置 | 用途 | 是否必需 |
|---------|------|------|---------|
| **unified_config.json** | `config/unified_config.json` | **主配置文件**，包含大部分配置项 | ✅ 推荐创建 |
| **.env** | 项目根目录 | 环境变量（Token、路径等） | ✅ 如需使用 Tushare/雪球 |
| **realtime_config.json** | `config/realtime_config.json` | 实时数据配置（WebSocket、监控等） | ⚙️ 高级功能 |
| **策略独立配置** | `strategies/*/config/*.json` | 各策略的独立配置 | ⚙️ 使用特定策略时 |

### 1.3 如何编辑配置文件

**Windows 最简单方法**：
1. 按 `Win + R`，输入 `notepad`
2. 打开配置文件（`.env` 或 `config/unified_config.json`）
3. 编辑并保存

**如果 .env 不存在**：
```bash
Copy-Item .env.example .env
```

**Windows 路径注意事项**：
在 JSON 文件中，Windows 路径需要特殊处理：
- ✅ `"D:\\\\国金QMT交易端模拟\\\\userdata_mini"` （双反斜杠）
- ✅ `"D:/国金QMT交易端模拟/userdata_mini"` （正斜杠，推荐）
- ❌ `"D:\国金QMT交易端模拟\userdata_mini"` （单反斜杠，错误！）

### 1.4 创建配置文件

**步骤 1：复制配置模板**

```bash
# Windows PowerShell
Copy-Item config\unified_config.json config\unified_config.json.backup

# 如果没有 .env 文件
Copy-Item .env.example .env
```

**步骤 2：编辑 unified_config.json**

配置文件包含详细注释，以下是关键配置项：

```json
{
  "settings": {
    "account": {
      // QMT 路径配置（使用 QMT 交易时必需）
      "qmt_path": "D:\\\\国金QMT交易端模拟\\\\userdata_mini",
      "account_id": "39020958",
      "auto_detect_qmt": true
    },
    "logging": {
      // 日志配置（调试时建议设为 DEBUG）
      "level": "INFO",
      "file": "logs/application.log"
    },
    "trading": {
      // 交易模式（paper_trading=仿真，real=实盘）
      "trade_mode": "paper_trading",
      "auto_confirm": false  // ⚠️ 实盘交易前确认此配置
    }
  }
}
```

**步骤 3：编辑 .env 文件**

```env
# Tushare Token（使用 Tushare 数据源时必需）
TUSHARE_TOKEN=你的Token粘贴在这里

# DuckDB 路径（使用 DuckDB 时推荐配置）
DUCKDB_PATH=D:/StockData/stock_data.ddb

# 雪球 Cookie（使用雪球跟单时必需）
XUEQIU_COOKIE=你的雪球Cookie
```

### 1.5 QMT 路径配置

**QMT 路径查找**

常见的 QMT 安装路径：

```
D:\国金证券QMT交易端\userdata_mini\
D:\国金QMT交易端模拟\userdata_mini\
D:\QMT\userdata_mini\
C:\QMT\userdata_mini\
```

**自动检测 QMT 路径**

```python
from easy_xt.config import config
config.print_qmt_status()
```

**手动设置 QMT 路径**

```python
from easy_xt.config import config
config.set_qmt_path('D:\\国金QMT交易端模拟')
```

或在 `unified_config.json` 中设置：

```json
{
  "settings": {
    "account": {
      "qmt_path": "D:\\\\国金QMT交易端模拟\\\\userdata_mini"
    }
  }
}
```

---

## 2. 数据源配置

本项目支持**多种数据源**，系统会按优先级自动选择可用的数据源。

### 2.1 数据源优先级

```
DuckDB（本地数据库）
    ↓ 失败/未配置
QMT/miniQMT（本地数据）
    ↓ 失败/未配置
Tushare（在线数据）
    ↓ 失败/未配置
TDX（通达信）
    ↓ 失败/未配置
Eastmoney（东方财富）
```

### 2.2 数据源配置清单

#### Tushare 数据源

**何时需要**：需要在线股票数据（日线、财务、指数等）

**配置步骤**：

1. 注册并获取 Token：
   - 访问 https://tushare.pro
   - 注册账号
   - 进入「用户中心」→「接口Token」→ 复制 Token

2. 配置 Token：

   **方法 A：使用 .env 文件（推荐）**
   ```env
   TUSHARE_TOKEN=你的Token粘贴在这里
   ```

   **方法 B：环境变量**
   ```powershell
   setx TUSHARE_TOKEN "你的Token"
   ```

   **方法 C：配置文件**
   ```json
   {
     "data_providers": {
       "tushare": {
         "token": "你的Token"
       }
     }
   }
   ```

3. 验证配置：
   ```bash
   python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('✓ Token配置成功' if os.getenv('TUSHARE_TOKEN') else '✗ Token未配置')"
   ```

**常见问题**：
- Q: Token 会被限流吗？
  A: 是的。可以在 .env 中配置备用 Token：`TUSHARE_TOKEN_2=你的备用Token`

- Q: 免费账户够用吗？
  A: 基础功能（日线行情）够用。高频数据或高级财务数据需要更多积分。

#### TDX（通达信）数据源

**何时需要**：使用通达信作为数据源

**配置步骤**：

1. 安装 pytdx：
   ```bash
   pip install pytdx
   ```

2. 配置 TDX 服务器（可选，有默认配置）：

   编辑 `config/unified_config.json`：
   ```json
   {
     "data_providers": {
       "tdx": {
         "enabled": true,
         "timeout": 30,
         "retry_count": 3,
         "servers": [
           {
             "host": "115.238.56.198",
             "port": 7709,
             "name": "杭州主站"
           }
         ]
       }
     }
   }
   ```

3. 验证连接：
   ```python
   from easy_xt.realtime_data.providers import TdxDataProvider
   tdx = TdxDataProvider()
   if tdx.connect():
       print("✓ TDX 连接成功")
   ```

**常见 TDX 服务器列表**：

| 服务器 | 地址 | 端口 |
|--------|------|------|
| 杭州主站 | 115.238.56.198 | 7709 |
| 南京主站 | 115.238.90.165 | 7709 |
| 上海主站 | 114.80.63.12 | 7709 |
| 深圳主站 | 119.147.212.81 | 7709 |

#### QMT/miniQMT 数据源

**何时需要**：已安装 QMT/miniQMT，想使用本地数据

**配置步骤**：

1. 确保 xtquant 已正确安装（见 [xtquant 配置](#1-xtquant-配置)）

2. 配置 QMT 路径（见 [QMT 路径配置](#24-qmt-路径配置)）

3. 启动 QMT/miniQMT 客户端并登录

4. 验证连接：
   ```python
   from easy_xt import get_api
   api = get_api()
   data = api.get_price(['000001.SZ'], count=10)
   print(f"获取到 {len(data)} 条数据")
   ```

#### xqshare（跨平台）数据源

**何时需要**：Mac/Linux 用户，或远程连接 QMT

**配置步骤**：

1. 安装 xqshare：
   ```bash
   pip install xqshare
   ```

2. 配置环境变量：
   ```env
   XQSHARE_REMOTE_HOST=你的服务器IP
   XQSHARE_REMOTE_PORT=18812
   ```

3. 验证连接：
   ```python
   from xqshare import XtQuantClient
   client = XtQuantClient('你的服务器IP', 18812)
   # 正常使用 EasyXT，会自动检测并使用 xqshare
   ```

详细说明：见 [README.md 跨平台支持章节](README.md#-跨平台支持)

#### DuckDB 数据库配置

**何时需要**：频繁回测、因子分析，需要提速 10-30 倍

**配置步骤**：

1. 安装 DuckDB：
   ```bash
   pip install duckdb
   ```

2. 下载/生成数据库：

   **方式 A：GUI 下载（推荐）**
   ```bash
   python run_gui.py
   ```
   在 "Tushare下载" 标签页中选择要下载的数据

   **方式 B：命令行下载**
   ```bash
   python tools/setup_duckdb.py
   ```

   **方式 C：使用现有数据库**
   将数据库文件放到指定位置，如 `D:/StockData/stock_data.ddb`

3. 配置路径：

   **方法 A：.env 文件**
   ```env
   DUCKDB_PATH=D:/StockData/stock_data.ddb
   ```

   **方法 B：配置文件**
   ```json
   {
     "data_providers": {
       "duckdb": {
         "path": "D:/StockData/stock_data.ddb"
       }
     }
   }
   ```

   **方法 C：代码中指定**
   ```python
   from easyxt_backtest import DataManager
   data_manager = DataManager(duckdb_path='D:/StockData/stock_data.ddb')
   ```

4. 验证数据库：
   ```python
   import duckdb
   con = duckdb.connect('D:/StockData/stock_data.ddb', read_only=True)
   tables = con.execute("SHOW TABLES").fetchall()
   print("数据库表:", [t[0] for t in tables])
   ```

**性能对比**：

| 数据源 | 获取 100 只股票 1 年数据 | 适用场景 |
|--------|------------------------|---------|
| DuckDB | ~1 秒 | 频繁回测、因子分析 |
| QMT 本地 | ~10-30 秒 | 偶尔回测 |
| Tushare 在线 | ~30-60 秒 | 无本地数据时 |

### 3.3 数据源选择建议

| 使用场景 | 推荐数据源 | 原因 |
|---------|-----------|------|
| 实盘交易 | QMT 本地 | 最实时、最稳定 |
| 频繁回测 | DuckDB | 速度最快 |
| 偶尔回测 | Tushare / TDX | 无需预先下载 |
| Mac/Linux 用户 | xqshare + Tushare | 跨平台支持 |
| 因子分析 | DuckDB | 大数据查询优化 |

---

## 3. IDE 配置（Trae/VSCode/PyCharm）

### 3.1 通用步骤

所有 IDE 都需要完成以下步骤：

1. **安装核心库**：
   ```bash
   pip install -e ./easy_xt
   ```

2. **配置 Python 解释器**：
   - 确保使用正确的 Python 环境
   - 验证：`python --version`（需要 >= 3.9）

3. **验证安装**：
   ```bash
   python -c "from easy_xt import get_api; print('✓ 安装成功')"
   ```

### 3.2 VSCode 配置

**创建 `.vscode/settings.json`**：

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
  "python.envFile": "${workspaceFolder}/.env",
  "python.analysis.extraPaths": [
    "${workspaceFolder}"
  ]
}
```

**创建 `.vscode/launch.json`**：

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: 当前文件",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    }
  ]
}
```

### 3.3 PyCharm 配置

**设置项目根目录**：

1. File → Open → 选择项目根目录
2. File → Settings → Project → Python Interpreter
3. 选择正确的 Python 解释器

**配置运行配置**：

1. Run → Edit Configurations
2. 添加环境变量：
   - Name: `PYTHONPATH`
   - Value: 项目根目录路径

### 3.4 Trae 配置

**已知问题和解决方案**：

**问题 1**：模块导入错误

**解决方案**：

1. 在项目根目录创建 `trae_config.json`：
   ```json
   {
     "pythonPath": "你的Python路径",
     "env": {
       "PYTHONPATH": "项目根目录路径"
     }
   }
   ```

2. 或在 Trae 的终端中手动设置：
   ```bash
   export PYTHONPATH="项目根目录路径:$PYTHONPATH"
   ```

**问题 2**：xtquant 导入失败

**解决方案**：

确保 `XTQUANT_PATH` 环境变量已设置并在 Trae 中生效：

1. 系统环境变量中设置：
   ```powershell
   setx XTQUANT_PATH "xtquant所在路径"
   ```

2. 重启 Trae IDE

3. 验证：
   ```python
   import os
   print(os.getenv('XTQUANT_PATH'))  # 应该输出路径
   from xtquant import datacenter  # 不应该报错
   ```

### 3.5 Jupyter Notebook 配置

**安装 IPython Kernel**：

```bash
pip install ipykernel
python -m ipykernel install --user --name=easyxt-env
```

**在 Notebook 中设置路径**：

```python
import sys
sys.path.insert(0, '项目根目录路径')
```

---

## 4. 常见场景配置清单

### 4.1 场景 A：QMT 实盘交易

**配置文件位置**：`config/unified_config.json`

**配置清单**：

- [ ] xtquant 已正确安装
- [ ] QMT 路径已配置（`config/unified_config.json`）
- [ ] QMT 客户端已启动并登录
- [ ] 交易模式已设置（`real` 或 `paper_trading`）
- [ ] 账户 ID 已配置

**配置步骤**：

1. **编辑配置文件** `config/unified_config.json`：

   ```json
   {
     "settings": {
       "account": {
         "qmt_path": "D:\\\\国金QMT交易端模拟\\\\userdata_mini",
         "account_id": "你的账户ID",
         "auto_detect_qmt": true
       },
       "trading": {
         "trade_mode": "real",
         "auto_confirm": false
       }
     }
   }
   ```

2. **⚠️ 重要提示**：
   - Windows 路径中的反斜杠需要写成 `\\\\`（双转义）
   - 或者使用正斜杠：`D:/国金QMT交易端模拟/userdata_mini`
   - `trade_mode: "real"` 表示实盘交易，请谨慎操作！
   - 建议先使用 `trade_mode: "paper_trading"` 测试

3. **启动 QMT 客户端并登录**

**验证命令**：

```bash
# 验证 xtquant
python -c "from xtquant import datacenter; print('✓ xtquant OK')"

# 验证配置
python -c "from easy_xt.config import config; config.print_qmt_status()"

# 验证连接
python -c "from easy_xt import get_api; api = get_api(); print('✓ 连接成功')"
```

### 4.2 场景 B：TDX 数据源 + 回测

**配置文件位置**：
- 主配置：`config/unified_config.json`
- 环境变量：项目根目录的 `.env` 文件（可选）

**配置清单**：

- [ ] pytdx 已安装（`pip install pytdx`）
- [ ] TDX 服务器已配置（可选，有默认值）
- [ ] easyxt_backtest 已安装
- [ ] DuckDB 已配置（可选，但推荐）

**配置步骤**：

1. **安装 pytdx**：
   ```bash
   pip install pytdx
   ```

2. **编辑配置文件** `config/unified_config.json`：

   ```json
   {
     "data_providers": {
       "tdx": {
         "enabled": true,
         "timeout": 30,
         "retry_count": 3,
         "servers": [
           {
             "host": "115.238.56.198",
             "port": 7709,
             "name": "杭州主站"
           }
         ]
       }
     }
   }
   ```

3. **（可选）配置 DuckDB** 以提升回测速度：

   编辑项目根目录的 `.env` 文件：
   ```env
   DUCKDB_PATH=D:/StockData/stock_data.ddb
   ```

**验证命令**：

```bash
# 验证 TDX
python -c "from pytdx.hq import TdxHq_API; print('✓ pytdx OK')"

# 验证回测
python -c "from easyxt_backtest import BacktestEngine; print('✓ backtest OK')"

# 测试 TDX 连接
python easy_xt/realtime_data/providers/tdx_provider.py
```

### 4.3 场景 C：雪球跟单策略

**配置文件位置**：
- 主配置：`config/unified_config.json` 或 `strategies/xueqiu_follow/config/unified_config.json`
- 环境变量：项目根目录的 `.env` 文件

**配置清单**：

- [ ] xtquant 已正确安装
- [ ] QMT 路径已配置
- [ ] 雪球 Cookie 已配置（`.env` 文件）
- [ ] 雪球跟单配置已设置

**配置步骤**：

1. **编辑项目根目录的 `.env` 文件**：
   ```env
   # 雪球 Cookie（必需）
   XUEQIU_COOKIE=你的雪球Cookie
   ```

2. **编辑配置文件** `config/unified_config.json`：
   ```json
   {
     "settings": {
       "account": {
         "qmt_path": "D:\\\\国金QMT交易端模拟\\\\userdata_mini",
         "account_id": "你的账户ID"
       },
       "trading": {
         "trade_mode": "paper_trading"
       }
     },
     "xueqiu": {
       "cookie": "你的雪球Cookie",
       "follow_combination_id": "你要跟单的组合ID"
     }
   }
   ```

3. **获取雪球 Cookie**：
   - 浏览器访问 https://xueqiu.com 并登录
   - F12 打开开发者工具 → 网络(Network)标签
   - 刷新页面，点击任意 xueqiu.com 请求
   - 在请求头中复制完整 Cookie 值

**验证命令**：

```bash
# 验证雪球 Cookie
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('✓ Cookie 已配置' if os.getenv('XUEQIU_COOKIE') else '✗ Cookie 未配置')"

# 启动雪球跟单
python strategies/xueqiu_follow/start_xueqiu_follow_easyxt.py
```

### 4.4 场景 D：Mac/Linux 用户

**配置文件位置**：
- 主配置：`config/unified_config.json`
- 环境变量：项目根目录的 `.env` 文件

**配置清单**：

- [ ] xqshare 已安装（`pip install xqshare`）
- [ ] 远程服务器地址已配置
- [ ] Tushare Token 已配置（备用数据源）
- [ ] DuckDB 已配置（可选，但推荐）

**配置步骤**：

1. **安装 xqshare**：
   ```bash
   pip install xqshare
   ```

2. **编辑项目根目录的 `.env` 文件**：
   ```env
   # xqshare 远程服务器配置
   XQSHARE_REMOTE_HOST=你的服务器IP
   XQSHARE_REMOTE_PORT=18812

   # 备用数据源（推荐）
   TUSHARE_TOKEN=你的Token
   ```

3. **编辑配置文件** `config/unified_config.json`：
   ```json
   {
     "data_providers": {
       "xqshare": {
         "enabled": true,
         "remote_host": "你的服务器IP",
         "remote_port": 18812
       },
       "tushare": {
         "enabled": true,
         "token": "你的Token"
       }
     }
   }
   ```

**验证命令**：

```bash
# 验证 xqshare
python -c "from xqshare import XtQuantClient; print('✓ xqshare OK')"

# 验证数据源
python -c "from easy_xt import get_api; api = get_api(); data = api.get_price(['000001.SZ'], count=10); print(f'✓ 获取到 {len(data)} 条数据')"
```

---

## 5. 快速检查清单

在开始使用前，请确认以下事项：

---

## 6. 获取帮助

### 自助资源

- 📖 **[完整安装指南](INSTALL.md)** - 安装步骤和故障排查
- ❓ **[疑难问题解答](docs/assets/TROUBLESHOOTING.md)** - 常见问题 FAQ
- 📐 **[系统架构文档](ARCHITECTURE.md)** - 项目架构说明
- 📖 **[项目 README](README.md)** - 项目说明和快速导航

### 诊断工具

```bash
# 完整诊断
python easy_xt/check_xtquant.py

# QMT 状态检查
python -c "from easy_xt.config import config; config.print_qmt_status()"

# 配置验证
python -c "from core.config import get_global_config_manager; cm = get_global_config_manager(); print(cm.validate())"
```

### 报告问题

如果问题仍未解决，请提交 Issue：
https://github.com/quant-king299/EasyXT/issues

提交时请包含：
1. 完整的错误信息
2. 操作系统和 Python 版本
3. 配置文件内容（脱敏后）
4. 复现步骤

---

**祝你配置顺利！** 🎉

如有任何问题，请先查看 [TROUBLESHOOTING.md](docs/assets/TROUBLESHOOTING.md)
