# miniQMT 自动登录功能

## 功能介绍

自动登录模块可以自动启动 QMT/miniQMT 并完成登录流程，包括：
- ✅ 自动填写用户名和密码
- ✅ 自动识别并计算数学验证码（如：3+4=?）
- ✅ 检测登录状态
- ✅ 支持重启已运行的QMT
- ✅ 自动清理临时文件

## 安装依赖

```bash
pip install pywinauto pyautogui
```

## 配置步骤

### 1. 编辑 `.env` 文件

在项目根目录的 `.env` 文件中添加以下配置（如果没有该文件，从 `.env.example` 复制）：

```env
# QMT 可执行文件路径（必须填写）
QMT_EXE_PATH=D:\国金QMT交易端模拟\bin.x64\XtMiniQmt.exe

# QMT 用户ID/资金账号（必须填写）
QMT_USER_ID=8888499999

# QMT 登录密码（必须填写）
QMT_PASSWORD=your_password_here

# QMT 数据目录（可选，用于清理临时文件）
QMT_DATA_DIR=D:\国金QMT交易端模拟\userdata_mini
```

### 2. 获取配置信息

**QMT_EXE_PATH**: QMT可执行文件的完整路径
- 通常在：`D:\国金QMT交易端模拟\bin.x64\XtMiniQmt.exe`
- 或者：`C:\国金证券QMT交易端\bin.x64\XtMiniQmt.exe`
- 可以通过右键点击QMT快捷方式 → 打开文件所在位置 找到

**QMT_USER_ID**: 你的QMT资金账号
- 在QMT登录界面可以看到
- 通常是8-10位数字

**QMT_PASSWORD**: 你的QMT登录密码
- 请注意保管密码安全

## 使用方法

### 方法1：命令行启动（推荐）

```bash
# 在项目根目录运行
python start_qmt.py

# 或使用模块方式
python -m core.auto_login.qmt_login

# 带参数运行
python -m core.auto_login.qmt_login --restart --timeout=90
```

**参数说明：**
- `--restart`: 如果QMT已运行，先关闭再启动
- `--timeout`: 登录超时时间（秒），默认60秒

### 方法2：Python代码调用

```python
from core.auto_login import QMTAutoLogin

# 创建自动登录实例
auto_login = QMTAutoLogin()

# 执行登录
success = auto_login.login(restart=False, timeout=60)

if success:
    print("登录成功！")
else:
    print("登录失败！")
```

### 方法3：自定义配置

```python
from core.auto_login import QMTAutoLogin

# 使用自定义配置（不从.env读取）
auto_login = QMTAutoLogin(
    exe_path=r"D:\国金QMT交易端模拟\bin.x64\XtMiniQmt.exe",
    user_id="8888499999",
    password="your_password",
    data_dir=r"D:\国金QMT交易端模拟\userdata_mini"
)

auto_login.login()
```

## 注意事项

### ⚠️ 安全提醒

1. **密码存储**: 密码以明文形式存储在 `.env` 文件中
   - 确保 `.env` 文件不会被提交到版本控制系统
   - 不要在共享计算机上使用此功能
   - 定期修改密码

2. **文件权限**: 确保 `.env` 文件权限设置正确
   - Windows: 右键文件 → 属性 → 安全
   - Linux/Mac: `chmod 600 .env`

### 故障排查

**问题1：无法找到QMT窗口**
- 检查 `QMT_EXE_PATH` 是否正确
- 确认QMT是否正常启动
- 尝试手动启动QMT确认路径

**问题2：验证码识别失败**
- 如果未安装 `pytesseract` 和 `opencv-python`，程序会等待30秒供手动输入
- 可以手动安装OCR库：`pip install pytesseract opencv-python`
- 或者在30秒内手动输入验证码

**问题3：登录超时**
- 增加超时时间：`--timeout=120`
- 检查网络连接
- 确认QMT服务器是否正常运行

**问题4：填写用户名/密码失败**
- 不同版本的QMT窗口结构可能不同
- 程序会自动尝试备用方案
- 如果仍然失败，请手动填写或提供窗口信息用于调试

## 高级功能

### 创建桌面快捷方式（Windows）

创建一个 `.bat` 文件：

```batch
@echo off
cd /d C:\Users\YourName\EasyXT
python start_qmt.py
pause
```

保存为 `启动QMT.bat`，放到桌面即可。

### 开机自启动

1. 按 `Win + R`，输入 `shell:startup` 打开启动文件夹
2. 创建上述 `.bat` 文件的快捷方式
3. 将快捷方式放入启动文件夹

### 在策略中使用

```python
from core.auto_login import QMTAutoLogin

# 在策略启动前确保QMT已登录
auto_login = QMTAutoLogin()
auto_login.login()

# 然后启动你的策略
# ...
```

## 技术原理

自动登录使用 `pywinauto` 库实现：

1. **启动QMT**: 使用 `Application.start()` 启动QMT程序
2. **窗口定位**: 通过UI自动化找到登录窗口和输入框
3. **填写信息**: 自动填写用户名、密码
4. **验证码处理**: 使用OCR识别数学表达式并计算结果
5. **登录确认**: 检测登录是否成功

## 相关文档

- [QMT官方文档](https://www.gtja.com/)
- [pywinauto文档](https://pywinauto.readthedocs.io/)
- [主项目README](../../README.md)
