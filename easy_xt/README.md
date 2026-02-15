# ⚠️ 重要：xtquant 安装说明

**本包需要特殊版本的 xtquant，不能使用 pip 安装的官方版本！**

---

## 🔴 快速检查

运行检查脚本验证 xtquant 是否已正确安装：

```bash
# Windows
cd easy_xt
python check_xtquant.py

# 或使用一键安装脚本
install.bat
```

如果报错 `cannot import name 'datacenter' from 'xtquant'`，说明 xtquant **未安装或版本不完整**。

---

## 📦 如何安装 xtquant

### 方法 1：从 GitHub Releases 下载（推荐）

1. **下载地址**：https://github.com/quant-king299/EasyXT/releases/tag/xueqiu_follow-xtquant-v1.0

2. 解压到指定目录，例如：
   - `C:\xtquant_special`
   - `D:\tools\xtquant`

3. 设置环境变量（重启终端生效）：

   **PowerShell**：
   ```powershell
   setx XTQUANT_PATH "C:\xtquant_special"
   ```

   **CMD**：
   ```cmd
   setx XTQUANT_PATH "C:\xtquant_special"
   ```

4. 重启终端，再次运行 `python check_xtquant.py` 验证

### 方法 2：从 QMT 软件目录复制

如果已安装迅投 QMT：

1. 找到 QMT 安装目录，如：
   ```
   D:\国金证券QMT交易端\userdata_mini\Python\
   ```

2. 复制 `xtquant` 文件夹到以下任一位置：
   - Python 的 `site-packages` 目录
   - 项目根目录
   - 或设置 `XTQUANT_PATH` 环境变量指向该目录

### 方法 3：使用 wheel 包（如果提供）

如果 Releases 页面提供 `.whl` 包：
```bash
pip install C:\Path\To\xtquant-*.whl
```

---

## 🚀 安装 easy-xt

xtquant 安装完成后，安装 easy-xt：

### 方式 1：一键安装（Windows）

```bash
cd easy_xt
install.bat
```

### 方式 2：手动安装

```bash
cd easy_xt
pip install -e .
```

### 卸载重装（本地调试）

```bash
pip uninstall easy-xt -y
pip install -e .
```

---

## 💡 使用示例

```python
from easy_xt import get_api, ExtendedAPI

# 获取 QMT API
api = get_api()

# 使用扩展 API
ext = ExtendedAPI()

# 示例：获取股票行情
data = ext.get_full_history(['000001.SZ'], period='1d', start_time='20240101')
```

---

## 📋 依赖要求

- **Python >= 3.8**
- **xtquant**（特殊版本，按上述方式安装）
- **pydantic, requests**（由本包自动安装）

---

## ❓ 常见问题

### Q: 为什么不能用 `pip install xtquant`？

A: pip 上的 xtquant 是最新官方版本，与 miniQMT/EasyXT 不兼容。必须使用本项目的特殊版本。

### Q: 报错 `cannot import name 'datacenter'`？

A: 这是因为 xtquant 文件不完整。GitHub 上的仓库受文件大小限制，无法包含完整的二进制文件（.pyd、.dll）。必须从 Releases 页面下载完整版。

### Q: 如何验证安装成功？

A: 运行以下命令：
```bash
python -c "from xtquant import datacenter; print('✓ xtquant 正确')"
python -c "from easy_xt import get_api; print('✓ easy-xt 正确')"
```

### Q: XTQUANT_PATH 环境变量不生效？

A:
1. 确认环境变量设置正确（注意不要有多余的引号）
2. **完全重启**终端/IDE（不是新开标签页）
3. Windows 可能需要重启电脑才能生效

---

## 🔗 相关链接

- **xtquant 下载**：https://github.com/quant-king299/EasyXT/releases
- **miniQMT 文档**：[QMT 交易接口使用指南](https://dict.thinktrader.net/nativeApi/start_now.html)
- **问题反馈**：[GitHub Issues](https://github.com/quant-king299/EasyXT/issues)
