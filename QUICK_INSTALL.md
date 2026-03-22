# EasyXT 快速安装指南

## 🚀 3种安装方式

### 方式1：自动安装脚本（推荐，最简单）

```powershell
# 1. 进入项目目录
cd C:\Users\Administrator\EasyXT

# 2. 运行安装脚本
install_easyxt.bat
```

**优点**：
- ✅ 一键安装，无需手动设置
- ✅ 自动配置环境变量
- ✅ 自动验证安装
- ✅ 提供清晰的反馈

---

### 方式2：手动设置 PYTHONPATH

#### Windows PowerShell

```powershell
# 临时设置（当前窗口有效）
$env:PYTHONPATH = "C:\Users\Administrator\EasyXT"

# 永久设置（所有新窗口都有效）
[System.Environment]::SetEnvironmentVariable("PYTHONPATH", "C:\Users\Administrator\EasyXT", "User")
```

#### Windows CMD

```cmd
# 永久设置
setx PYTHONPATH "C:\Users\Administrator\EasyXT"
```

---

### 方式3：在代码中动态添加

```python
import sys
sys.path.insert(0, 'C:/Users/Administrator/EasyXT')

from easyxt_backtest import BacktestEngine
```

---

## ✅ 验证安装

```python
# 测试 easy_xt
from easy_xt import get_api
print("easy_xt OK")

# 测试 easyxt_backtest
from easyxt_backtest import BacktestEngine
print("easyxt_backtest OK")
```

---

## ❓ 常见问题

### Q: 为什么不能用 pip install？

A: `easyxt_backtest` 使用"目录即包"的结构，pip/setuptools 对这种结构支持不完善。使用 PYTHONPATH 更可靠。

### Q: 会不会和其他项目冲突？

A: 不会。PYTHONPATH 只影响 Python 搜索路径，不会覆盖已安装的包。

### Q: 如何卸载？

A:
```powershell
# 删除 PYTHONPATH 环境变量
[System.Environment]::SetEnvironmentVariable("PYTHONPATH", "", "User")
```

---

## 📞 需要帮助？

- 查看 [完整安装文档](INSTALL.md)
- 或提交 Issue: https://github.com/quant-king299/EasyXT/issues
