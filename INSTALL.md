# EasyXT 安装指南

本文档提供 EasyXT 项目的完整安装说明，包括环境准备、安装步骤、常见问题排查等内容。

> 🆕 **新手推荐**：如果你遇到配置问题（如 `cannot import name 'datacenter' from 'xtquant'`），请查看 **[📖 增强版配置指南](SETUP_GUIDE.md)**，包含针对不同场景的详细配置说明。

## 📋 目录

- [🚀 快速安装（推荐）](#快速安装推荐)
- [📖 详细安装步骤](#详细安装步骤)
- [⚠️ xtquant 配置（重要！）](#xtquant-配置重要)
- [❓ 常见错误与解决方案](#常见错误与解决方案)
- [✅ 验证安装](#验证安装)
- [🔧 卸载说明](#卸载说明)
- [📞 需要帮助？](#需要帮助)

---

## 🚀 快速安装（推荐）

> ⚡ **5分钟完成安装，推荐新手使用**

### 前提条件

- Windows 10/11 用户
- Python 3.8+ 已安装（推荐 Python 3.11）
- 有 Git（可选，用于克隆项目）

### 一键安装步骤

```powershell
# 1. 克隆项目（如果还没有）
git clone https://github.com/quant-king299/EasyXT.git
cd EasyXT

# 2. 选择安装方式

# 方式1：仅安装核心库（命令行使用）
pip install -e ./easy_xt

# 方式2：完整安装（包含GUI、回测等所有功能）⭐ 推荐
pip install -e .

# 方式3：实时数据推送功能（可选）
pip install -r requirements_realtime.txt
```

**💡 说明**：
- **方式1**：只安装核心数据API，适合命令行使用，不包含GUI界面
- **方式2**：完整安装，包含GUI界面、回测框架等所有功能
- **方式3**：实时数据推送功能，包括：
  - ✅ **pytdx** - 通达信数据接口，支持实时行情和历史数据
  - ✅ **aiohttp/websockets** - 异步HTTP和WebSocket支持
  - ✅ **实时数据推送** - 支持实时行情订阅和推送
  - ✅ **自动降级** - 当QMT数据不可用时自动切换到通达信数据源

**安装建议**：
- 如果需要使用GUI界面（run_gui.py），请使用**方式2**
- 如果需要**实时数据推送**或**通达信数据源**（推荐），额外安装**方式3**
- 完整安装：方式2 + 方式3

### 验证安装

```powershell
# 测试 easy_xt
python -c "from easy_xt import get_api; print('easy_xt OK')"

# 测试 easyxt_backtest
python -c "from easyxt_backtest import BacktestEngine; print('easyxt_backtest OK')"
```

**成功输出**：
```
easy_xt OK
easyxt_backtest OK
```

---

## ⚠️ xtquant 配置（重要！）

> 🔴 **如果你遇到 `cannot import name 'datacenter' from 'xtquant'` 错误，请仔细阅读本节！**

### 为什么需要特殊版本的 xtquant？

本项目需要**特殊版本**的 xtquant，不能使用 `pip install xtquant` 安装的官方版本！

**原因**：不同券商的 QMT 版本发布节奏不一致，xtquant 接口和行为存在差异。为避免连接失败、字段缺失、接口不兼容等问题，本项目仅支持特定版本。

### 快速安装 xtquant

**方法 1：从 GitHub Releases 下载（推荐）**

1. 访问下载页面：
   ```
   https://github.com/quant-king299/EasyXT/releases/tag/v1.0.0
   ```

2. 下载附件：`xtquant.rar`

3. 解压到项目根目录（即克隆/下载 EasyXT 项目后的文件夹）

   > **说明**：如果你从 GitHub 下载的是 `EasyXT-main.zip`，解压后的文件夹名为 `EasyXT-main`，那么项目根目录就是 `EasyXT-main/`

4. 验证安装：
   ```bash
   python -c "from xtquant import datacenter; print('✓ xtquant 安装正确')"
   ```

**方法 2：一键下载并解压（PowerShell）**

```powershell
# 先进入项目根目录（EasyXT项目文件夹）
cd <你的项目路径>

$url = "https://github.com/quant-king299/EasyXT/releases/download/v1.0.0/xtquant.rar"
$dest = "$PWD\xtquant.rar"
Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
if (Test-Path "$env:ProgramFiles\7-Zip\7z.exe") {
  & "$env:ProgramFiles\7-Zip\7z.exe" x -y "$dest" -o"$PWD"
}
Remove-Item $dest -ErrorAction SilentlyContinue
```

**如果解压到自定义目录**，需要设置环境变量：

```powershell
setx XTQUANT_PATH "C:\xtquant_special"
```

**⚠️ 重要**：设置环境变量后必须**重启终端/IDE**才能生效！

### 验证安装

运行诊断脚本：
```bash
python easy_xt/check_xtquant.py
```

该脚本会自动检测问题并给出详细指引。

### 详细配置说明

如果需要更详细的配置说明（包括 IDE 配置、数据源配置等），请查看 **[📖 增强版配置指南](SETUP_GUIDE.md)**。

---

## 📖 详细安装步骤

### 第一步：环境准备

#### 1.1 检查 Python 版本

```powershell
python --version
```

**要求**：Python 3.8 或更高版本

**推荐版本**：Python 3.11 ⭐
- 兼容性最好，性能优秀
- 与 XtQuant 库完全兼容
- 社区支持广泛

**如果未安装或版本过低**：
- 访问 [python.org](https://www.python.org/downloads/)
- 下载 Python 3.11 或更高版本（推荐 3.11.x）
- 安装时勾选 "Add Python to PATH"

#### 1.2 XtQuant 运行依赖环境 ⭐ 重要

**XtQuant Python 版本支持**：
- XtQuant 目前提供 **64 位 Python 3.6、3.7、3.8、3.9、3.10、3.11、3.12** 版本
- 不同版本的 Python 导入时会自动切换对应的库
- 建议使用 Python 3.11 以获得最佳兼容性

**运行前准备**：
> 🔴 **重要**：在运行使用 XtQuant 的程序前，**必须先启动 MiniQMT 客户端**！

1. 确保 MiniQMT 客户端已安装并配置好
2. 启动 MiniQMT 客户端并登录
3. 保持 MiniQMT 客户端运行状态
4. 然后再运行你的 Python 程序

**为什么需要先启动 MiniQMT？**
- XtQuant 库需要与 MiniQMT 客户端建立通信
- 客户端负责与券商服务器连接
- 未启动客户端会导致连接失败或数据获取错误

#### 1.3 检查 Git（可选）

```powershell
git --version
```

**如果未安装**：
- 访问 [git-scm.com](https://git-scm.com/)
- 下载 Windows 版本并安装

#### 1.3 克隆项目（如果还没有）

```powershell
# 选择一个目录克隆项目
cd D:\workspace

# 克隆项目
git clone https://github.com/quant-king299/EasyXT.git

# 进入项目目录
cd EasyXT
```

---

### 第二步：安装 easy_xt（核心库）

**什么是 easy_xt？**
- QMT API 的轻量级封装
- 提供数据获取、交易下单等功能
- **必需的**，除非你只用回测框架

```powershell
# 安装 easy_xt
pip install -e ./easy_xt
```

**可能的输出**：
```
Successfully installed easy-xt
```

**验证安装**：
```powershell
python -c "from easy_xt import get_api; print('easy_xt OK')"
```

---

### 第三步：安装 easyxt_backtest（回测框架）

**什么是 easyxt_backtest？**
- 通用量化策略回测框架
- 支持技术指标、选股、网格等多种策略
- **可选的**，如果你只做数据查询不需要回测

#### 方式A：使用 pip 安装（推荐，最简单）

```powershell
# 安装 easyxt_backtest
pip install -e ./easyxt_backtest
```

**优点**：
- ✅ IDE 会正确识别所有类和函数（不再有"未定义"错误）
- ✅ 标准的 Python 包管理方式
- ✅ 自动安装所有依赖

**验证安装**：
```powershell
python -c "from easyxt_backtest import BacktestEngine; print('easyxt_backtest OK')"
```

#### 方式B：自动安装脚本（可选）

如果你想使用自动安装脚本（会配置 PYTHONPATH）：

```powershell
cd easyxt_backtest
install.bat
```

**注意**：如果已经用 pip 安装，就不需要运行 install.bat 了。

**输出示例**：
```
[1/4] Check project directory...
     Found easyxt_backtest

[2/4] Install dependencies...
     backtrader installed successfully

[3/4] Configure PYTHONPATH...
     Success!

[4/4] Verify installation...
     easyxt_backtest: OK
```

---

### 第四步：安装实时数据推送功能（可选）

**什么是实时数据推送功能？**
- 基于通达信数据接口的实时行情推送
- 支持实时数据订阅和历史数据获取
- **可选的**，如果你只需要基础数据查询功能

#### 主要功能

1. **实时行情推送**
   - 支持实时订阅股票行情
   - 异步数据推送，性能优秀
   - WebSocket 支持

2. **通达信数据源**
   - **pytdx** - 通达信数据接口
   - 不依赖 QMT 客户端
   - 自动降级：当 QMT 数据不可用时自动切换

3. **历史数据获取**
   - 支持分钟级、日级等多种周期
   - 数据覆盖面广
   - 无需手动下载

#### 安装步骤

```powershell
# 安装实时数据推送功能及依赖
pip install -r requirements_realtime.txt
```

**安装内容包括**：
- `pytdx>=1.72` - 通达信数据接口
- `aiohttp>=3.8.0` - 异步HTTP支持
- `websockets>=10.0` - WebSocket支持
- `asyncio-mqtt>=0.11.0` - 异步MQTT支持
- 其他相关依赖

**验证安装**：
```powershell
# 测试 pytdx
python -c "import pytdx; print('✓ pytdx 安装成功')"

# 测试实时数据模块
python -c "from easy_xt.realtime_data.providers.tdx_provider import TdxDataProvider; print('✓ 实时数据推送模块 OK')"
```

**成功输出**：
```
✓ pytdx 安装成功
✓ 实时数据推送模块 OK
```

#### 使用场景

**推荐安装实时数据推送功能的情况**：
- ✅ 需要实时行情推送
- ✅ 需要分钟级历史数据（1分钟、5分钟等）
- ✅ 不想频繁使用 QMT 客户端下载数据
- ✅ 需要稳定的数据源（QMT + 通达信双数据源）

**可以不安装的情况**：
- ❌ 只使用日级数据
- ❌ 经常使用 QMT 客户端手动下载
- ❌ 只做回测不需要实时数据

---

### 第五步：重启终端（如果需要）

**注意**：
- 使用 `pip install -e` 安装后，**不需要**重启终端
- 如果之前使用过 install.bat 设置了 PYTHONPATH，建议先清理：
  ```powershell
  [System.Environment]::SetEnvironmentVariable("PYTHONPATH", "", "User")
  ```
- ⚠️ 配置 PYTHONPATH 后**必须重启终端**才能生效
- ⚠️ 如果使用虚拟环境，需要在虚拟环境中设置

---

### 第四步：重启终端

**重要**：配置 PYTHONPATH 后，**必须重启终端**才能生效！

```powershell
# 方法1：关闭当前 PowerShell 窗口，重新打开

# 方法2：如果你在 IDE（如 VSCode、PyCharm）中
#    需要重启 IDE 或重新加载窗口
```

---

## ❓ 常见错误与解决方案

### 错误 0：`ModuleNotFoundError: No module named 'PyQt5'` ⭐ 常见

**错误信息**：
```
ModuleNotFoundError: No module named 'PyQt5'
```

**原因**：使用了核心库安装方式（`pip install -e ./easy_xt`），未安装 GUI 依赖

**解决方案**：

**方案1：重新安装完整依赖**（推荐）
```powershell
# 从项目根目录安装（包含 GUI、回测等所有依赖）
pip install -e .
```

**方案2：单独安装 PyQt5**
```powershell
pip install PyQt5
```

**验证安装**：
```powershell
python -c "from PyQt5.QtWidgets import QApplication; print('PyQt5 OK')"
```

**说明**：
- ✅ `pip install -e ./easy_xt` - 只安装核心库，适合命令行使用
- ✅ `pip install -e .` - 完整安装，包含 GUI 界面、回测框架等
- 如果需要使用 `run_gui.py`，必须使用**完整安装**

---

### 错误 0.1：`ModuleNotFoundError: No module named 'duckdb'`

**错误信息**：
```
ModuleNotFoundError: No module named 'duckdb'
```

**原因**：DuckDB 数据库依赖未安装

**解决方案**：

**方案1：安装 duckdb**
```powershell
pip install duckdb
```

**方案2：重新安装完整依赖**
```powershell
pip install -e .
```

**验证安装**：
```powershell
python -c "import duckdb; print('duckdb OK')"
```

**说明**：DuckDB 是数据存储核心依赖，用于本地数据管理和因子分析

---

### 错误 1：`ValueError: No file/folder found for module easy_xt`

**错误信息**：
```
ValueError: No file/folder found for module easy_xt
```

**原因**：`easy_xt/pyproject.toml` 缺少模块配置

**解决方案**：
```powershell
# 1. 确保使用最新版本
git pull origin main

# 2. 检查 easy_xt/pyproject.toml 文件
type easy_xt\pyproject.toml | findstr "tool.flit.module"
# 应该看到：[tool.flit.module]

# 3. 如果没有，手动添加
# 在 easy_xt/pyproject.toml 末尾添加：
# [tool.flit.module]
# name = "easy_xt"
```

---

### 错误 2：`pip install` 失败，提示权限错误

**错误信息**：
```
ERROR: Could not install packages due to EnvironmentError: [Errno 13] Permission denied
```

**解决方案 1**：使用虚拟环境（推荐）
```powershell
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
.\\venv\\Scripts\\Activate.ps1

# 重新安装
pip install -e ./easy_xt
```

**解决方案 2**：使用用户安装
```powershell
pip install --user -e ./easy_xt
```

---

### 错误 3：`ModuleNotFoundError: No module named 'backtrader'`

**错误信息**：
```
ModuleNotFoundError: No module named 'backtrader'
```

**原因**：缺少 backtrader 依赖

**解决方案**：
```powershell
# 安装 backtrader
pip install backtrader
```

---

### 错误 4：导入错误 `No module named 'easyxt_backtest.core.backtest_core'`

**错误信息**：
```
ModuleNotFoundError: No module named 'easyxt_backtest.core.backtest_core'
```

**原因**：`backtest_core.py` 文件不在版本控制中

**解决方案**：
```powershell
# 1. 拉取最新代码
git pull origin main

# 2. 检查文件是否存在
dir easyxt_backtest\core\backtest_core.py

# 3. 如果不存在，尝试重新克隆
git clone https://github.com/quant-king299/EasyXT.git EasyXT_Fresh
```

---

### 错误 5：安装成功但导入失败

**症状**：
```powershell
# 安装成功
Successfully installed easy-xt

# 但导入失败
python -c "from easy_xt import get_api"
# ModuleNotFoundError: No module named 'easy_xt'
```

**原因**：Python 路径缓存问题

**解决方案**：
```powershell
# 方法1：重启 PowerShell
# 关闭当前窗口，重新打开

# 方法2：检查安装
pip list | findstr easy
# 应该看到：easy-xt

# 方法3：重新安装
pip uninstall easy-xt -y
pip install -e ./easy_xt

# 方法4：如果是虚拟环境问题
# 重新激活虚拟环境
.\\venv\\Scripts\\Activate.ps1
```

---

### 错误 6：安装脚本报错 `SyntaxError: EOL while scanning string literal`

**错误信息**：
```
SyntaxError: EOL while scanning string literal
```

**原因**：使用了旧版本的脚本（有特殊字符）

**解决方案**：
```powershell
# 确保使用最新版本
git pull origin main

# 检查脚本位置
dir easyxt_backtest\\install.bat

# 重新运行
cd easyxt_backtest
install.bat
```

---

### 错误 7：终端显示乱码

**症状**：安装脚本中的中文显示为乱码，但功能正常

**原因**：PowerShell 编码问题

**影响**：不影响功能，只是显示问题

**解决方案**：已创建英文版脚本 `install.bat`（无乱码）

---

### 错误 8：配置 PYTHONPATH 后仍然无法导入

**症状**：
```powershell
$env:PYTHONPATH = "D:\EasyXT"
python -c "from easyxt_backtest import BacktestEngine"
# 还是报错
```

**排查步骤**：

1. **检查 PYTHONPATH 是否正确设置**
```powershell
echo $env:PYTHONPATH
# 应该输出：D:\EasyXT
```

2. **检查 Python 是否能找到项目**
```powershell
python -c "import sys; print(sys.path[0])"
# 应该显示：D:\EasyXT
```

3. **检查文件是否存在**
```powershell
dir easyxt_backtest\__init__.py
dir easyxt_backtest\core\backtest_core.py
```

4. **重启终端**
```powershell
# 配置 PYTHONPATH 后必须重启才能生效！
```

---

### 错误 9：git pull 失败

**错误信息**：
```
error: Your local changes to the following files would be overwritten by merge
        xtquant/config/MarketTime.ini
        ...
```

**解决方案 1**：暂存本地修改
```powershell
# 暂存 xtquant 修改
git stash push -m "保存xtquant配置" xtquant/

# 拉取
git pull origin main

# 恢复修改（如果需要）
git stash pop
```

**解决方案 2**：强制更新（会丢弃本地修改）
```powershell
# 备份重要文件
copy xtquant\config\config.lua xtquant\config.lua.backup

# 强制更新
git fetch origin
git reset --hard origin/main
```

---

## ✅ 验证安装

### 基础验证

```powershell
# 1. 验证 easy_xt
python -c "from easy_xt import get_api; print('easy_xt OK')"

# 2. 验证 easyxt_backtest
python -c "from easyxt_backtest import BacktestEngine; print('easyxt_backtest OK')"

# 3. 验证实时数据推送功能（如果安装了）
python -c "import pytdx; print('pytdx OK')"
python -c "from easy_xt.realtime_data.providers.tdx_provider import TdxDataProvider; print('实时数据推送 OK')"
```

### 完整验证

```powershell
# 测试数据获取
python -c "
from easy_xt import get_api
api = get_api()
data = api.get_price(['000001.SZ'], start='20240101', period='1d')
print(f'获取到 {len(data)} 条数据')
"

# 测试回测引擎
python -c "
from easyxt_backtest import BacktestEngine, DataManager
from easyxt_backtest.strategies import SmallCapStrategy

# 创建回测引擎
data_manager = DataManager()
engine = BacktestEngine(initial_cash=1000000, data_manager=data_manager)

# 创建策略
strategy = SmallCapStrategy(select_num=3)
result = engine.run_backtest(strategy, '20230101', '20231231')
result.print_summary()
"
```

---

## 🔧 卸载说明

### 卸载 easy_xt

```powershell
pip uninstall easy-xt -y
```

### 卸载 easyxt_backtest

```powershell
pip uninstall easyxt-backtest -y
```

**注意**：如果之前使用过 install.bat，可以清理 PYTHONPATH：
```powershell
[System.Environment]::SetEnvironmentVariable("PYTHONPATH", "", "User")
```

### 卸载虚拟环境

```powershell
# 停用虚拟环境
deactivate

# 删除虚拟环境
rmdir venv
```

---

## 📊 安装方式对比

| 方式 | easy_xt | easyxt_backtest | 实时数据推送 |
|------|---------|-----------------|-------------|
| **安装方式** | `pip install -e ./easy_xt` | `pip install -e ./easyxt_backtest` | `pip install -r requirements_realtime.txt` |
| **是否必需** | 是 | 可选 | 可选 |
| **主要功能** | QMT数据API | 回测框架 | pytdx+实时推送 |
| **是否设置 PYTHONPATH** | 否 | **否** | 否 |
| **pip list 可见** | 是 | 是 | 是 |
| **重启终端** | 不需要 | 不需要 | 不需要 |
| **更新代码** | `git pull` | `git pull` | `git pull` |
| **卸载方式** | `pip uninstall easy-xt` | `pip uninstall easyxt-backtest` | 手动删除 |
| **IDE 识别** | ✅ 完美 | ✅ 完美 | ✅ 完美 |

---

## 🎯 推荐安装流程

### 新手用户（推荐）

```powershell
# 1. 克隆项目
git clone https://github.com/quant-king299/EasyXT.git
cd EasyXT

# 2. 安装核心库
pip install -e ./easy_xt

# 3. 安装回测框架
pip install -e ./easyxt_backtest

# 4. 安装实时数据推送功能（可选，推荐）⭐
pip install -r requirements_realtime.txt

# 5. 验证安装
python -c "from easyxt_backtest import BacktestEngine; print('安装成功！')"
```

### 开发者

```powershell
# 1. 使用虚拟环境（推荐）
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. 安装所有依赖
pip install -e ./easy_xt
pip install -e ./easyxt_backtest
pip install -r requirements_realtime.txt  # 实时数据推送功能

# 3. 配置开发环境
code .

# 4. 开始开发
```

---

## 🔍 高级配置

### 配置 IDE（VSCode）

1. **设置 Python 解释器**
   - 按 `Ctrl+Shift+P`
   - 输入 "Python: Select Interpreter"
   - 选择虚拟环境的 Python 或系统 Python

2. **配置工作区**
   - File → Open Folder
   - 选择 `EasyXT` 目录

3. **设置环境变量**（如果需要）
   - launch.json 中添加：
   ```json
   {
       "env": {
           "PYTHONPATH": "${workspaceFolder}"
       }
   }
   ```

---

## 📞 需要帮助？

### 自助排查

1. **检查 Python 版本**
   ```powershell
   python --version
   # 必须 >= 3.8，推荐 3.11
   ```

2. **检查 pip 版本**
   ```powershell
   python -m pip --version
   # 建议升级到最新
   python -m pip install --upgrade pip
   ```

3. **查看已安装的包**
   ```powershell
   pip list
   ```

4. **检查环境变量**
   ```powershell
   echo $env:PYTHONPATH
   echo $env:Path
   ```

### 文档资源

- 📖 [快速开始指南](QUICK_START.md)
- 📖 [架构设计文档](ARCHITECTURE.md)
- ❓ [疑难问题解答](docs/assets/TROUBLESHOOTING.md)
- 📝 [API 文档](API文档.md)

### 获取帮助

1. **查看 FAQ** - 大部分问题都有解答
2. **提交 Issue** - https://github.com/quant-kin299/EasyXT/issues
   - 附上完整的错误信息
   - 说明你的操作系统和 Python 版本
   - 提供复现步骤

---

**祝你安装顺利！** 🎉

如有问题，请查看 [FAQ](docs/assets/TROUBLESHOOTING.md) 或提 Issue。
