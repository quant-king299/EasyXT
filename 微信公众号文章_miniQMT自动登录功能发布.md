# 🎯 量化交易必备！miniQMT一键自动登录，告别手动输入密码！

> 告别繁琐的手动登录，让你的量化策略自动起飞！🚀

---

## 📖 前言

作为一个量化交易者，你是否遇到过这些烦恼：

- 😤 每天早上都要手动打开QMT，输入密码
- 😤 策略运行时发现QMT没登录，导致交易失败
- 😤 守护进程重启后，又要重新登录QMT
- 😤 多个策略共享QMT，管理起来很麻烦

**今天，我们带来了完美的解决方案！**

EasyXT项目新增**miniQMT自动登录功能**，让你的QMT登录全程自动化，彻底解放双手！✨

---

## 🎉 功能亮点

### ✨ 核心特性

- 🔐 **一键自动登录**：只需一个命令，QMT自动启动并登录
- 🤖 **智能验证码处理**：验证码自动显示，无需手动输入
- 🔄 **自动重连机制**：QMT断线自动重新登录
- 🛡️ **安全配置**：密码本地存储，绝不外传
- 📦 **即插即用**：3行代码即可集成到你的策略中

### 🎯 适用场景

1. **策略自动启动**：策略启动前自动检查QMT状态
2. **数据自动获取**：获取行情前确保QMT已登录
3. **守护进程**：定时任务中保持QMT始终在线
4. **批量操作**：一键启动多个策略，共享QMT连接

---

## 🚀 快速开始

### 第一步：安装依赖

```bash
pip install pywinauto pyautogui python-dotenv
```

### 第二步：配置文件

在项目根目录创建 `.env` 文件（已提供 `.env.example` 模板）：

```env
# QMT可执行文件路径（必填）
QMT_EXE_PATH=D:\国金QMT交易端模拟\bin.x64\XtMiniQmt.exe

# QMT登录密码（必填）
QMT_PASSWORD=your_password_here

# QMT数据目录（可选）
QMT_DATA_DIR=D:\国金QMT交易端模拟\userdata_mini
```

**⚠️ 安全提醒**：
- 密码以明文存储在 `.env` 文件中
- `.env` 文件已在 `.gitignore` 中，不会被提交到GitHub
- 建议在个人电脑上使用，不要在共享电脑上使用

### 第三步：启动自动登录

```bash
# 方式1：交互式登录（推荐）
python start_qmt_interactive.py

# 方式2：全自动登录
python start_qmt.py
```

**就这么简单！** 🎊

---

## 💡 深入了解：登录流程

### 🔍 miniQMT登录原理

通过分析QMT的登录流程，我们发现：

1. **用户ID** - 自动显示，无需输入 ✅
2. **验证码** - 自动生成并显示，无需输入 ✅
3. **密码** - 唯一需要手动输入的环节 ✅

**自动登录流程**：

```
启动QMT
    ↓
Tab键跳到密码框
    ↓
输入密码
    ↓
按回车（验证码自动显示）
    ↓
再按回车（提交登录）
    ↓
登录成功！✅
```

### 🎨 技术实现

我们使用了 `pyautogui` 库模拟键盘操作：

```python
import pyautogui

# Tab到密码框
pyautogui.press('tab')
time.sleep(0.8)

# 输入密码
pyautogui.typewrite(password)
time.sleep(0.5)

# 按回车（验证码自动显示）
pyautogui.press('enter')
time.sleep(1.0)

# 再按回车提交登录
pyautogui.press('enter')
```

**简洁、可靠、高效！** 👍

---

## 📚 实战案例

### 案例1：策略启动前自动登录

```python
#!/usr/bin/env python3
from core.qmt_connection import ensure_qmt_logged_in

def main():
    print("策略启动中...")
    
    # 确保QMT已登录
    if ensure_qmt_logged_in(auto_login=True):
        print("✓ QMT已就绪")
        
        # 启动你的策略
        strategy = MyStrategy()
        strategy.run()
    else:
        print("✗ QMT登录失败")

if __name__ == '__main__':
    main()
```

### 案例2：使用装饰器（更优雅）

```python
from core.qmt_connection import require_qmt_login

@require_qmt_login(auto_login=True)
def my_strategy():
    """这个函数执行前会自动检查QMT状态"""
    from easy_xt import get_api
    api = get_api()
    
    # 你的策略代码
    data = api.get_stock_data('000001.SZ')
    # ...

# 直接调用，无需手动检查QMT
my_strategy()
```

### 案例3：查询QMT状态

```python
from core.qmt_connection import get_qmt_status

status = get_qmt_status()
print(f"QMT运行: {status['running']}")
print(f"QMT登录: {status['logged_in']}")
```

---

## 🔧 高级功能

### 1️⃣ QMT连接管理器

EasyXT提供了统一的QMT连接管理器：

```python
from core.qmt_connection import get_qmt_manager

manager = get_qmt_manager()

# 检查状态
status = manager.get_qmt_status()

# 确保登录
if manager.ensure_qmt_logged_in():
    # 你的代码...
```

**特性**：
- ✅ 单例模式，全局共享一个实例
- ✅ 智能缓存，30秒内不重复检查
- ✅ 自动重连，QMT断线自动恢复

### 2️⃣ 集成到现有策略

**步骤1**：在策略开头添加导入

```python
from core.qmt_connection import ensure_qmt_logged_in
```

**步骤2**：在main函数中调用

```python
def main():
    if not ensure_qmt_logged_in(auto_login=True):
        print("QMT登录失败")
        return
    
    # 原有的策略代码...
```

**就这么简单！** 🎯

---

## ❓ 常见问题

### Q1：支持哪些QMT版本？

**A**：支持所有miniQMT版本，包括：
- 国金证券QMT交易端（模拟）
- 国金证券QMT交易端（实盘）
- miniQMT轻量版

### Q2：密码安全吗？

**A**：我们采取了多重安全措施：
- ✅ 密码存储在本地 `.env` 文件中
- ✅ `.env` 文件已在 `.gitignore` 中
- ✅ 不会上传到GitHub等代码托管平台
- ✅ 建议定期修改密码

**⚠️ 注意**：不要在共享电脑上使用此功能！

### Q3：登录失败怎么办？

**A**：检查以下几点：
1. ✅ 确认 `.env` 文件中的 `QMT_EXE_PATH` 路径正确
2. ✅ 确认 `QMT_PASSWORD` 密码正确
3. ✅ 确认QMT可执行文件存在
4. ✅ 确认网络连接正常

### Q4：可以多个策略共享QMT吗？

**A**：完全可以！QMT连接管理器使用单例模式：
- ✅ 多个策略共享同一个QMT实例
- ✅ 自动避免重复启动QMT
- ✅ 统一管理QMT连接状态

### Q5：如何确认QMT登录成功？

**A**：使用状态查询功能：

```python
from core.qmt_connection import get_qmt_status

status = get_qmt_status()
if status['logged_in']:
    print("✓ QMT已登录")
else:
    print("✗ QMT未登录")
```

---

## 🎊 总结

miniQMT自动登录功能的推出，让量化交易变得更加便捷：

### ✅ 核心优势

1. **省时省力**：告别手动登录，一键启动QMT
2. **自动化**：策略启动前自动检查QMT状态
3. **智能化**：QMT断线自动重连
4. **易用性**：3行代码即可集成到你的策略
5. **安全性**：密码本地存储，绝不外传

### 🚀 立即体验

```bash
# 1. 安装依赖
pip install pywinauto pyautogui python-dotenv

# 2. 配置.env文件
cp .env.example .env
# 编辑.env，填写QMT路径和密码

# 3. 启动自动登录
python start_qmt_interactive.py
```

**就这么简单！** 🎯

---

## 📮 获取方式

项目已开源，欢迎Star⭐：

🔗 **GitHub仓库**：[https://github.com/quant-king299/EasyXT](https://github.com/quant-king299/EasyXT)

**相关文档**：
- [QMT自动登录使用指南](https://github.com/quant-king299/EasyXT/blob/main/QMT_AUTOLOGIN_USER_GUIDE.md)
- [QMT连接管理器文档](https://github.com/quant-king299/EasyXT/blob/main/core/qmt_connection/README.md)
- [项目主README](https://github.com/quant-king299/EasyXT)

---

## 💬 交流反馈

如果你在使用过程中遇到任何问题，欢迎：

- 📝 提交Issue：[GitHub Issues](https://github.com/quant-king299/EasyXT/issues)
- 💬 加入讨论：[GitHub Discussions](https://github.com/quant-king299/EasyXT/discussions)
- 📧 联系作者：quant-king299

---

**一键登录，策略起飞！** 🚀

*让量化交易变得更简单，让每一个策略都能稳定运行！*

---

> **关注我们，获取更多量化交易技巧！**
> 
> 🎯 **EasyXT - 模块化QMT量化交易工具集**
> 
> 🔗 [https://github.com/quant-king299/EasyXT](https://github.com/quant-king299/EasyXT)

---

*© 2024 EasyXT Project. All rights reserved.*
