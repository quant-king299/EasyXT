# 安装指南 | Installation Guide

本文档提供 EasyXT 项目的详细安装说明。

## 📋 目录

- [环境要求](#环境要求)
- [方法一：安装核心库（推荐）](#方法一安装核心库推荐)
- [方法二：完整克隆安装](#方法二完整克隆安装)
- [常见问题](#常见问题)
- [验证安装](#验证安装)

---

## 环境要求

### 必需环境

- **Python**: 3.8 或更高版本
- **操作系统**:
  - Windows 10/11（完整功能）
  - macOS（通过 xqshare 远程客户端）
  - Linux（通过 xqshare 远程客户端）

### 可选依赖

- **QMT/miniQMT**: Windows 本地交易（仅 Windows 需要）
- **DuckDB**: 本地数据缓存（可选，但强烈推荐）
- **Git**: 版本控制（克隆项目时需要）

---

## 方法一：安装核心库（推荐）

如果你只需要使用 API 封装，不需要完整的策略和示例，推荐此方法。

### 1️⃣ 安装 easy_xt（核心库）

```bash
# 进入项目目录
cd EasyXT

# 安装核心库（开发模式）
pip install -e ./easy_xt
```

**验证安装**：
```bash
python -c "from easy_xt import get_api; print('✅ easy_xt 安装成功！')"
```

### 2️⃣ 安装 easyxt_backtest（可选，用于回测）

**方法1：添加到 PYTHONPATH（推荐）**

```bash
# Windows PowerShell
$env:PYTHONPATH += ";C:\Users\Administrator\EasyXT"

# 或者永久添加（需要重启终端）
[System.Environment]::SetEnvironmentVariable("PYTHONPATH", "C:\Users\Administrator\EasyXT", "User")
```

**方法2：在代码中添加路径**

```python
import sys
sys.path.insert(0, 'C:/Users/Administrator/EasyXT')

from easyxt_backtest import BacktestEngine
```

**验证安装**：
```bash
python -c "import sys; sys.path.insert(0, 'C:/Users/Administrator/EasyXT'); from easyxt_backtest import BacktestEngine; print('✅ easyxt_backtest 可用！')"
```

---

## 方法二：完整克隆安装

如果你想访问所有模块（策略、学习实例、GUI等），使用此方法。

### 1️⃣ 克隆项目

```bash
# 使用 HTTPS
git clone https://github.com/quant-king299/EasyXT.git

# 或使用 SSH（如果你配置了 SSH 密钥）
git clone git@github.com:quant-king299/EasyXT.git

# 进入项目目录
cd EasyXT
```

### 2️⃣ 安装核心模块

```bash
# 安装 easy_xt 核心库
pip install -e ./easy_xt

# 安装回测框架（可选）
pip install -e ./easyxt_backtest
```

### 3️⃣ 安装可选依赖

```bash
# 安装所有依赖（包括 GUI、数据分析等）
pip install -r requirements.txt
```

### 4️⃣ 配置环境（可选）

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，添加你的配置
# Windows: notepad .env
# macOS/Linux: nano .env
```

---

## 常见问题

### ❌ 问题 1: `ValueError: No file/folder found for module easy_xt`

**原因**: `easy_xt/pyproject.toml` 缺少模块配置

**解决方案**:
```bash
# 确保你使用的是最新版本的项目
git pull origin main

# 或者手动添加以下内容到 easy_xt/pyproject.toml
# [tool.flit.module]
# name = "easy_xt"
```

### ❌ 问题 2: `pip install` 失败，提示权限错误

**解决方案**:
```bash
# 方案 1: 使用用户安装（推荐）
pip install --user -e ./easy_xt

# 方案 2: 使用虚拟环境（最佳实践）
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
pip install -e ./easy_xt
```

### ❌ 问题 3: 导入错误 `No module named 'easy_xt'`

**原因**: Python 路径问题或未正确安装

**解决方案**:
```bash
# 检查安装
pip list | grep easy-xt

# 重新安装
pip uninstall easy-xt
pip install -e ./easy_xt

# 验证 Python 路径
python -c "import sys; print('\n'.join(sys.path))"
```

### ❌ 问题 4: macOS/Linux 用户报错

**原因**: QMT 只支持 Windows

**解决方案**: 使用 xqshare 远程客户端
```bash
# 安装 xqshare
pip install xqshare

# 配置环境变量
export XQSHARE_REMOTE_HOST="your-server-ip"
export XQSHARE_REMOTE_PORT="18812"
```

详见：[📖 跨平台支持文档](https://github.com/quant-king299/EasyXT#-跨平台支持)

---

## 验证安装

### 快速测试

```bash
# 进入项目目录
cd EasyXT

# 测试 easy_xt
python -c "
from easy_xt import get_api
api = get_api()
print('✅ easy_xt 安装成功！')
"

# 测试 easyxt_backtest
python -c "
from easyxt_backtest import BacktestEngine
print('✅ easyxt_backtest 安装成功！')
"
```

### 运行示例

```bash
# 运行学习实例
python 学习实例/01_快速开始.py

# 运行 GUI（如果安装了 PyQt5）
python run_gui.py
```

---

## 下一步

安装完成后，你可以：

- 📖 阅读 [快速开始指南](QUICK_START.md)
- 🎯 查看 [学习实例](学习实例/)
- 📊 运行 [101因子分析平台](101因子/101因子分析平台/)
- 🔧 使用 [回测框架](easyxt_backtest/)

---

## 需要帮助？

如果遇到其他问题：

1. 查看 [疑难问题解答 (FAQ)](docs/assets/TROUBLESHOOTING.md)
2. 在 GitHub 上提 [Issue](https://github.com/quant-king299/EasyXT/issues)
3. 加入我们的讨论区

---

**祝你使用愉快！** 🎉
