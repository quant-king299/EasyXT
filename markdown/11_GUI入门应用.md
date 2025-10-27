# EasyXT 学习实例 11 - GUI 入门应用

本教程对应脚本：学习实例/11_GUI应用入门.py  
目标：掌握 gui_app 下各模块的用途、依赖检查，以及如何启动主GUI、简洁交易界面与回测窗口。  
推荐先完成基础入门与交易基础，再学习本教程。

# 🚀 EasyXT GUI 入门应用教程

> 项目地址: https://github.com/quant-king299/EasyXT  
> 本教程基于 学习实例/11_GUI应用入门.py，并参考 学习实例/03_高级交易.py 的结构呈现方式。

# 🛠️ 环境准备

### 系统要求
- Windows 10/11 操作系统
- Python 3.7+ 环境（建议 3.8~3.11）

### QMT账号获取指导
- 迅投 QMT 客户端已安装、启动并登录
- 若尚无 QMT 账号，可联系维护者协助开通与环境配置
- 可放置引导二维码图片（占位）：  
  ![微信二维码](qrcode.png)

### 配置信息（示例，按需在本地/GUI内配置）
```python
# 配置信息（请根据实际情况修改）
USERDATA_PATH = r'D:\国金QMT交易端模拟\userdata_mini'  # 修改为实际路径
ACCOUNT_ID = "39020958"                                  # 修改为实际账号
TEST_CODES = ["000001.SZ", "000002.SZ", "600000.SH"]     # 测试用股票
```

### 项目结构（聚焦 GUI 与学习实例）
```
miniqmt扩展/
├── gui_app/
│   ├── main_window.py               # 专业主窗口（策略管理与回测入口）
│   ├── trading_interface_simple.py  # 简洁交易界面
│   ├── widgets/
│   │   └── backtest_widget.py       # 回测窗口组件
│   └── README_Enhanced.md           # GUI 增强说明
├── 学习实例/
│   ├── 03_高级交易.py               # 高级交易教程示例
│   └── 11_GUI应用入门.py            # 本教程对应课程脚本
├── config/                          # 配置
└── logs/                            # 日志
```

---

## 适用人群
- 想快速理解并体验本项目 GUI 能力的用户
- 需要从命令行一键检查依赖、启动 GUI 的同学
- 计划二次开发 GUI（主窗口、交易界面、回测组件）的开发者

## 前置条件
- 已正确克隆本项目并可在命令行进入项目根目录
- Python 3.7+ 环境（建议 3.8~3.11）
- 能运行基础脚本（如 01_基础入门.py）

## 环境依赖
核心依赖（GUI 相关）：
- PyQt5
- pandas、numpy
- matplotlib（可选，用于图表）
- pyqtgraph（可选，用于高性能图表）

安装示例：
- 使用 requirements（如存在）：  
  pip install -r gui_app/requirements.txt
- 或手动安装：  
  pip install PyQt5 pandas numpy matplotlib pyqtgraph

---

## 快速开始

- 仅讲解与检查（逐课按回车继续）  
  python 学习实例/11_GUI应用入门.py

- 自动连续执行（不需要手动回车）  
  python 学习实例/11_GUI应用入门.py --auto

- 实际启动 GUI 子进程体验（新窗口弹出）  
  python 学习实例/11_GUI应用入门.py --run

- 自动且实际启动  
  python 学习实例/11_GUI应用入门.py --auto --run

注意：--run 会尝试以子进程独立窗口拉起 GUI，若无界面通常与依赖或运行环境有关，请参考“常见问题”。

---

## 课程结构（与脚本一致）

本教程与“11_GUI应用入门.py”保持一致的课程节奏，建议按顺序体验。

### 第1课：GUI 应用结构总览
目标：了解 gui_app 的主要文件与功能定位

关键路径与职责：
- gui_app/main_window.py  
  专业策略管理平台：参数配置/监控/控制/日志/回测入口
- gui_app/trading_interface_simple.py  
  简洁交易界面：快速体验账户/下单/持仓展示
- gui_app/widgets/backtest_widget.py  
  回测窗口组件：参数配置、执行进度、性能概览、详细指标、风险分析、交易记录、HTML 报告导出
- gui_app/README_Enhanced.md  
  增强版平台说明，列出 01-10 案例整合与功能清单
- gui_app/requirements.txt  
  GUI所需依赖清单

建议动作：
- 熟悉以上文件位置与作用
- 后续需要二开时优先阅读 main_window.py 与 backtest_widget.py 源码

命令（仅输出讲解，不启动 GUI）：
- python 学习实例/11_GUI应用入门.py

示例输出（节选）：
```
============================================================
第1课：GUI应用结构总览
============================================================
✓ 发现目录: gui_app
✓ 增强说明文档: gui_app/README_Enhanced.md
✓ 专业主窗口: gui_app/main_window.py
✓ 简洁交易界面: gui_app/trading_interface_simple.py
✓ 回测窗口组件: gui_app/widgets/backtest_widget.py
✓ 依赖清单: gui_app/requirements.txt
...
按回车键继续下一课...
```

---

### 第2课：依赖与环境检查
目标：确认 PyQt5、pandas、numpy、matplotlib、pyqtgraph 是否安装

动作：
- 脚本会检测核心依赖并给出状态
- 若缺失，请按“环境依赖”章节安装

命令：
- python 学习实例/11_GUI应用入门.py  （交互式）
- python 学习实例/11_GUI应用入门.py --auto  （自动化）

示例输出（节选）：
```
============================================================
第2课：检查依赖与环境
============================================================
Python版本: 3.10.13
✓ 已安装: PyQt5
✓ 已安装: pandas
✓ 已安装: numpy
⚠️ 未检测到: matplotlib(可选)
⚠️ 未检测到: pyqtgraph(可选)

可参考依赖清单: gui_app/requirements.txt
安装示例:
  pip install -r gui_app/requirements.txt
```

---

### 第3课：启动专业主窗口（main_window.py）
亮点：
- 策略参数配置、保存/加载，内置模板与代码生成
- 策略执行线程、状态监控、持仓/委托实时展示
- 回测入口：菜单 工具 -> “📊 专业回测”
- EasyXT 连接状态检测（状态栏实时展示）

命令：
- 直接启动主窗口（独立运行）：  
  python gui_app/main_window.py
- 通过学习脚本拉起（子进程方式）：  
  python 学习实例/11_GUI应用入门.py --run  
  或自动且拉起：  
  python 学习实例/11_GUI应用入门.py --auto --run

提示：
- 首次运行若无界面，多与 PyQt5 安装或系统环境变量相关
- 右下状态栏会显示连接状态（例如 EasyXT/QMT）

示例输出（节选）：
```
============================================================
第3课：启动专业主窗口
============================================================
功能亮点：
- 策略参数配置、保存/加载，内置模板与代码生成
- 策略执行线程、状态监控、持仓/委托实时展示
- 回测入口：菜单 工具 -> 📊 专业回测
- EasyXT 连接状态检测，状态栏实时展示
✓ 已找到 专业主窗口 (main_window.py): gui_app/main_window.py
启动方式（命令行示例）:
  python gui_app/main_window.py
🔄 正在启动子进程...
✓ 已尝试启动，若无界面请检查依赖与环境。
```

---

### 第4课：启动简洁交易界面（trading_interface_simple.py）
场景：快速体验账户/持仓/下单流程  
特性：EasyXT 可用则真实连接，否则提供模拟模式（界面按钮交互一致）

命令：
- 直接启动：  
  python gui_app/trading_interface_simple.py
- 通过学习脚本拉起：  
  python 学习实例/11_GUI应用入门.py --run

界面要点：
- 顶部状态：连接/断开交易服务
- 中部操作：股票代码、数量、价格，支持买入/卖出
- 下方表格：账户资金、持仓信息定时刷新

示例输出（节选）：
```
============================================================
第4课：启动简洁交易界面
============================================================
场景：快速体验账户/持仓/下单流程（EasyXT可用则真实连接，否则有模拟模式）
操作区：股票代码、数量、价格，支持买入/卖出；顶部可连接/断开交易服务
✓ 已找到 简洁交易界面 (trading_interface_simple.py): gui_app/trading_interface_simple.py
启动方式（命令行示例）:
  python gui_app/trading_interface_simple.py
🔄 正在启动子进程...
✓ 已尝试启动，若无界面请检查依赖与环境。
```

---

### 第5课：启动回测窗口组件（widgets/backtest_widget.py）
功能：回测参数配置、执行进度、性能概览、详细指标、风险分析、交易记录、HTML 报告导出  
数据源：DataManager 自动选择 QMT→QStock→AKShare→模拟（可手动切换）

命令：
- 直接启动：  
  python gui_app/widgets/backtest_widget.py
- 通过学习脚本拉起：  
  python 学习实例/11_GUI应用入门.py --run

建议：
- 先用“模拟数据”确认流程正确，再切换到真实数据源
- 若需要更专业的策略回测，阅读 backtest/engine.py 与 risk_analyzer.py

示例输出（节选）：
```
============================================================
第5课：启动回测窗口组件
============================================================
功能：回测参数配置、执行进度、性能概览、详细指标、风险分析、交易记录、HTML报告导出
数据源：DataManager自动选择 QMT→QStock→AKShare→模拟，可手动切换
✓ 已找到 回测窗口组件 (widgets/backtest_widget.py): gui_app/widgets/backtest_widget.py
启动方式（命令行示例）:
  python gui_app/widgets/backtest_widget.py
🔄 正在启动子进程...
✓ 已尝试启动，若无界面请检查依赖与环境。
```

---

### 第6课：常见问题与建议
- 依赖安装：  
  pip install PyQt5 pandas numpy matplotlib pyqtgraph
- 中文显示：  
  已在部分模块设置中文字体，若乱码请检查系统字体
- QMT 连接：  
  本机需安装并登录迅投客户端；EasyXT 需可用
- 运行策略卡住：  
  核对数据周期、网络状态、是否处于交易时段
- 回测无数据：  
  检查 DataManager 数据源状态，尝试缩短时间区间或切换到模拟
- Windows 子进程新窗口：  
  学习脚本使用子进程尝试新控制台拉起 GUI，减少阻塞；若未弹出，请在同一环境直接运行目标脚本确认报错

进阶建议：
- 在主窗口（main_window.py）中通过“工具 -> 📊 专业回测”打开回测组件
- 在自定义 PyQt5 项目中 import BacktestWidget 并嵌入布局，形成统一工作台

示例输出（节选）：
```
============================================================
第6课：常见问题与建议
============================================================
- 依赖安装:
  pip install PyQt5 pandas numpy matplotlib pyqtgraph
- 字体/中文: 代码中已设置中文字体，若乱码可检查系统字体。
- QMT连接: 需本机已安装并登录迅投客户端；EasyXT需可用。
- 回测无数据: 检查 DataManager 数据源状态，可改用模拟或缩短日期区间。
...
🎉 GUI应用入门课程完成！
```

---

## 命令速查

- 查看课程式讲解：  
  python 学习实例/11_GUI应用入门.py

- 自动执行课程：  
  python 学习实例/11_GUI应用入门.py --auto

- 课程中实际启动 GUI：  
  python 学习实例/11_GUI应用入门.py --run

- 主窗口（独立）：  
  python gui_app/main_window.py

- 简洁交易界面（独立）：  
  python gui_app/trading_interface_simple.py

- 回测窗口（独立）：  
  python gui_app/widgets/backtest_widget.py

---

## 附录

- 目录参考（精简）：
  - gui_app/main_window.py：专业主窗口（策略管理与回测入口）
  - gui_app/trading_interface_simple.py：简洁交易界面
  - gui_app/widgets/backtest_widget.py：回测组件
  - gui_app/README_Enhanced.md：增强版平台说明
  - 学习实例/11_GUI应用入门.py：本教程对应的课程式脚本

- 建议学习顺序：
  1) 01_基础入门 → 2) 02_交易基础 → 3) 03_高级交易 → 4) 11_GUI应用入门  
  之后可继续探索策略开发与专业回测。

- 反馈与改进：
  如需“逐步截图引导版”或“自动检测 QMT 并给出修复建议”的增强版教程，请在 Issues 中提出需求。