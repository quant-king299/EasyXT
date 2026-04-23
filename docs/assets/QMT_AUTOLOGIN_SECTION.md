# QMT自动登录 - 完整指南

> 🎯 EasyXT项目QMT自动登录功能的完整使用指南

---

## 🎯 功能介绍

EasyXT 现在支持 **miniQMT 自动登录**功能，可以：
- ✅ 自动启动 QMT
- ✅ 自动填写密码
- ✅ 自动处理验证码（验证码会自动显示）
- ✅ 一键完成登录

---

## 📦 安装依赖

```bash
pip install pywinauto pyautogui python-dotenv
```

或者安装主项目依赖（已包含这些库）：
```bash
pip install -r requirements.txt
```

---

## ⚙️ 配置步骤

### 1. 配置 `.env` 文件

在项目根目录的 `.env` 文件中添加：

```env
# QMT 可执行文件路径（必需）
QMT_EXE_PATH=D:\国金QMT交易端模拟\bin.x64\XtMiniQmt.exe

# QMT 登录密码（必需）
# 注意：用户ID会自动显示，无需配置
QMT_PASSWORD=your_password_here

# QMT 数据目录（可选）
QMT_DATA_DIR=D:\国金QMT交易端模拟\userdata_mini
```

### 2. 验证配置

运行测试脚本：
```bash
python test_qmt_login.py
```

**预期输出**：
```
============================================================
QMT 自动登录配置测试
============================================================

配置检查：
------------------------------------------------------------
[OK] QMT_EXE_PATH: D:\国金QMT交易端模拟\bin.x64\XtMiniQmt.exe
     文件存在
[OK] QMT_PASSWORD: ******** (已配置)
------------------------------------------------------------

[OK] 配置检查通过！
```

---

## 🚀 使用方法

### 方式1：交互式登录（推荐）

```bash
python start_qmt_interactive.py
```

**使用步骤**：
1. 运行脚本
2. QMT 自动启动
3. 程序自动填写密码并登录
4. 完成！

### 方式2：全自动登录

```bash
python start_qmt.py
```

### 方式3：在代码中使用

```python
from core.auto_login import QMTAutoLogin

auto_login = QMTAutoLogin()
success = auto_login.login()

if success:
    print("登录成功！")
else:
    print("登录失败！")
```

---

## 🔑 正确的登录流程

miniQMT的登录流程（已验证）：

1. **Tab到密码框**
2. **输入密码**
3. **按回车**（验证码会自动显示）
4. **再按回车**提交登录

**关键点**：
- ✅ 用户ID自动显示，无需输入
- ✅ 验证码自动显示，无需输入
- ✅ 只需Tab + 密码 + 两次回车

---

## 💡 集成到策略中

### 方法1：使用便捷函数

```python
from core.qmt_connection import ensure_qmt_logged_in

def main():
    # 确保QMT已登录
    if ensure_qmt_logged_in(auto_login=True):
        print("QMT已就绪，启动策略...")
        strategy = MyStrategy()
        strategy.run()
```

### 方法2：使用装饰器（更优雅）

```python
from core.qmt_connection import require_qmt_login

@require_qmt_login(auto_login=True)
def my_strategy():
    """这个函数执行前会自动检查QMT状态"""
    from easy_xt import get_api
    api = get_api()
    # 你的策略代码...
```

---

## ❓ 常见问题

### Q1: 提示"缺少依赖库"

**解决方法**：
```bash
pip install pywinauto pyautogui python-dotenv
```

### Q2: 提示"文件不存在"

**检查项**：
1. `.env` 文件中的 `QMT_EXE_PATH` 是否正确
2. 路径是否使用完整的绝对路径
3. 文件是否真的存在

**查找QMT路径的方法**：
- 右键点击QMT快捷方式 → 选择"打开文件所在位置"
- 找到 `XtMiniQmt.exe` 文件 → 复制完整路径

### Q3: 登录失败

**检查项**：
1. 密码是否正确
2. QMT可执行文件路径是否正确
3. 网络连接是否正常
4. 查看控制台输出的错误信息

### Q4: 程序一直卡在登录界面

**原因**：登录流程不正确

**解决方案**：
- 确保使用的是正确的登录流程：Tab → 密码 → 回车 → 回车
- 程序已实现正确的流程，确保使用最新版本

### Q5: QMT连接管理器是什么？

`core.qmt_connection` 模块提供统一的QMT连接检查和自动登录功能，用于：
- **策略启动前**检查QMT状态
- **数据获取前**确保QMT已登录
- **自动处理QMT连接断开重连

**使用方法**：
```python
from core.qmt_connection import ensure_qmt_logged_in, get_qmt_status

# 检查状态
status = get_qmt_status()
print(f"QMT运行: {status['running']}")
print(f"QMT登录: {status['logged_in']}")

# 确保登录
ensure_qmt_logged_in(auto_login=True)
```

---

## ⚠️ 安全提醒

- 密码以明文存储在 `.env` 文件中
- 确保 `.env` 文件不会被提交到Git（已在 `.gitignore` 中）
- 不要在共享计算机上使用此功能
- 建议定期修改密码

---

## 📚 相关文档

- [QMT自动登录使用指南](../../QMT_AUTOLOGIN_USER_GUIDE.md)
- [QMT连接管理器文档](../../core/qmt_connection/README.md)
- [自动登录模块文档](../../core/auto_login/README.md)
- [主项目README](../../README.md)

---

*最后更新：2024年4月23日*
