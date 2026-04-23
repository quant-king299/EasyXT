# EasyXT 路径配置说明

## 什么是"项目根目录"？

**项目根目录**是指你从 GitHub 下载或克隆 EasyXT 项目后得到的最顶层文件夹。

### 常见的项目根目录路径

根据你获取项目的方式，项目根目录可能是：

#### 1. GitHub 直接下载
```
下载文件: EasyXT.zip
解压后文件夹: EasyXT/
项目根目录: EasyXT/
```

#### 2. Git Clone
```bash
git clone https://github.com/quant-king299/EasyXT.git
# 项目根目录: EasyXT/
```

#### 3. 自定义文件夹名
如果你重命名了文件夹，例如：
```bash
# 原始: EasyXT/
# 你改名为: MyQuantProject/
# 那么项目根目录就是: MyQuantProject/
```

## 文档中的路径说明

### 相对路径表示法

文档中使用的相对路径都是相对于**项目根目录**的：

```
EasyXT/                          # ← 项目根目录
├── easy_xt/                     # 相对路径: easy_xt/
├── 101因子/                     # 相对路径: 101因子/
├── strategies/                  # 相对路径: strategies/
└── docs/                        # 相对路径: docs/
```

### 绝对路径示例

**Windows 系统：**
```
C:\Users\YourName\EasyXT\
D:\Projects\EasyXT\
```

**Linux/Mac 系统：**
```
/home/username/EasyXT/
~/projects/EasyXT/
```

## 常见问题

### Q: 文档中写 `cd <你的项目路径>` 是什么意思？

**A:** 将 `<你的项目路径>` 替换为你实际的项目根目录路径。

**示例：**
```bash
# 如果你的项目在桌面
cd C:\Users\YourName\Desktop\EasyXT

# 如果你的项目在 D 盘
cd D:\EasyXT

# Mac/Linux 用户
cd ~/EasyXT
```

### Q: 如何确认我是否在正确的目录？

**A:** 检查该目录下是否包含以下文件和文件夹：

```
✓ easy_xt/          文件夹
✓ 101因子/          文件夹
✓ strategies/       文件夹
✓ README.md         文件
✓ .env.example      文件
```

### Q: 代码示例中的路径需要改吗？

**A:** 不需要。代码中的路径管理是自动的，只需要确保：
1. 你在项目根目录运行代码
2. 或者正确设置了 `PYTHONPATH`

## 安装 xtquant 时的路径

### 方法 1: 直接解压到项目根目录（推荐）

```
项目根目录/
├── xtquant/          ← 解压到这里
├── easy_xt/
├── 101因子/
└── ...
```

### 方法 2: 自定义路径 + 环境变量

如果你将 `xtquant` 解压到其他位置（如 `C:\xtquant\`），需要设置环境变量：

```bash
# Windows PowerShell
setx XTQUANT_PATH "C:\xtquant"

# Linux/Mac
export XTQUANT_PATH="/path/to/xtquant"
```

## 路径相关的代码说明

### 代码中的路径管理

项目使用智能路径管理系统，会自动处理不同操作系统和路径差异：

```python
# core/path_manager.py 提供统一的路径管理
from core.path_manager import PathManager

pm = PathManager.get_instance()
project_root = pm.project_root  # 自动获取项目根目录
```

**无需手动修改代码中的路径！**

## 总结

1. **项目根目录** = 你下载/克隆的 EasyXT 文件夹
2. 大多数情况下名为 `EasyXT/`（除非你重命名了）
3. 文档中的相对路径都基于项目根目录
4. 代码会自动处理路径，无需修改
5. 遇到路径问题，先检查是否在正确的目录下运行

---

**需要帮助？**
- GitHub Issues: https://github.com/quant-king299/EasyXT/issues
- 查看故障排查文档: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
