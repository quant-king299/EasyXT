# MiniQMT扩展 - 量化交易工具包

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![QMT](https://img.shields.io/badge/QMT-Compatible-orange.svg)](https://www.gtja.com/)
[![Website](https://img.shields.io/badge/Website-ptqmt.com-blue?logo=google-chrome)](https://www.ptqmt.com)
[![知识星球](https://img.shields.io/badge/知识星球-quant--king299-brightgreen)](https://www.zhihu.com/club/12345678901234567890)

> **注意**：本项目使用的是miniQMT环境。QMT有两个版本：完整版QMT（包含GUI界面）和miniQMT（轻量级API版本）。两者在API使用上基本一致，但在环境配置和部署方式上有显著区别。详细区别请参阅 [QMT版本说明](qmt_versions_explanation.md)。

> 量化为王，策略致胜，我是只聊干货的王者 quant！
>
> 欢迎加入[知识星球](https://www.zhihu.com/club/12345678901234567890)，获取更多量化交易干货和一对一答疑服务！

一个基于迅投QMT的量化交易扩展工具包，提供简化的API接口和丰富的学习实例。

项目地址: https://github.com/quant-king299/EasyXT

项目结构:
```
miniqmt扩展/
├── strategies/
│   ├── jq2qmt/                         # 聚宽到QMT的中转服务实现
│   │   ├── qka/                        # QKA服务端实现
│   │   ├── ptqmt_client.py             # PTQMT客户端实现
│   │   ├── qmt_client_mini.py          # 聚宽策略使用的简化客户端
│   │   ├── run_qka_server.py           # QKA服务启动脚本
│   │   └── config/                     # 配置文件目录
│   ├── xueqiu_follow/                  # 雪球跟单策略
│   │   ├── start_xueqiu_follow_easyxt.py   # 生产主入口（推荐）
│   │   ├── start_with_initial_sync.py      # 启动即调仓版（首次对齐）
│   │   ├── start_real_trading_easyxt.py    # 真实交易连通性自测
│   │   ├── startup_manager.py              # 守护式统一管理入口
│   │   ├── system_monitor.py               # 运行期轻量监控
│   │   ├── core/                           # 策略引擎/采集器/执行器/风控
│   │   ├── config/                         # 统一配置（unified_config.json 等）
│   │   ├── logs/                           # 策略运行日志
│   │   └── tests/                          # 单元/集成测试
│   └── ...                             # 其他策略模块
├── gui_app/                            # 通用GUI（位于仓库根目录）
│   ├── main_window.py                  # 专业主窗口（策略管理与回测入口）
│   ├── trading_interface_simple.py     # 简洁交易界面
│   └── widgets/
│       └── backtest_widget.py          # 回测窗口组件
├── easy_xt/                            # 交易/数据子系统封装
└── reports/                            # 导出报表（如组合持仓导出）
```

## 🚀 特性

- **简化API**: 封装复杂的QMT接口，提供易用的Python API
- **真实交易**: 支持通过EasyXT接口进行真实股票交易
- **数据获取**: 集成qstock、akshare等多种数据源
- **技术指标**: 内置常用技术指标计算
- **策略开发**: 提供完整的量化策略开发框架
- **学习实例**: 丰富的教学案例，从入门到高级

## 📦 安装

### 环境要求

- 64 位 Python（建议 3.9+）
- 已安装并登录的 QMT 客户端（标准版或迷你版）
- Windows 系统（QMT 限制）

### 通过 pip 从 GitHub 安装（推荐用于生产环境）

推荐固定到稳定标签 v1.0.0：
```powershell
# 可选：创建虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install -U pip setuptools wheel
pip install "git+https://github.com/quant-king299/EasyXT.git@v1.0.0"
```

国内镜像（依赖走镜像，源码仍从 GitHub 拉取）：
```powershell
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple "git+https://github.com/quant-king299/EasyXT.git@v1.0.0"
```

验证安装：
```powershell
python - << 'PY'
import easy_xt
print("easy_xt import OK:", easy_xt.__name__)
from easy_xt import get_api
api = get_api()
print("get_api OK:", type(api))
PY
```

> 说明：pip 仅安装 Python 包，不会安装 QMT/xtquant，本地需自备。

### ⚙️ 首次使用配置（重要）

如果你需要使用 **Tushare 数据下载功能**，请配置环境变量：

1. **复制配置文件**
   ```bash
   # Windows PowerShell
   Copy-Item .env.example .env

   # Windows CMD
   copy .env.example .env

   # Linux/Mac
   cp .env.example .env
   ```

2. **获取并填写 Tushare Token**
   - 访问 [Tushare Pro](https://tushare.pro) 注册并获取 Token
   - 打开 `.env` 文件，将 `your_tushare_token_here` 替换为你的 Token：
   ```env
   TUSHARE_TOKEN=你的Token
   ```

3. **保存并重启程序**

> 📖 详细配置说明：[SETUP_TUSHARE_TOKEN.md](SETUP_TUSHARE_TOKEN.md) | [docs/TUSHARE_TOKEN_CONFIG.md](docs/TUSHARE_TOKEN_CONFIG.md)
>
> 必装的 xtquant 特殊版本（强制）：请到以下 Release 页面下载附件 `xtquant.rar`，解压后覆盖到本项目根目录下的 `xtquant/` 目录（若不存在则直接解压到根目录会创建该目录）：
>
> https://github.com/quant-king299/EasyXT/releases/tag/v1.0.0
>
> 为什么必须使用这一份 xtquant：券商侧随各自版本发布，不会与迅投官方保持一致节奏；不同券商包的 xtquant 版本、接口和行为差异会导致本项目运行报错。为确保一致性与稳定性，本项目仅支持上述 Release 附件中的 xtquant 版本，使用高/低其它版本都可能出现连接失败、字段缺失、接口不兼容等错误。
>
> 一键下载并解压（PowerShell，推荐）：
> ```powershell
> $url = "https://github.com/quant-king299/EasyXT/releases/download/v1.0.0/xtquant.rar"
> $dest = "$PWD\xtquant.rar"
> Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
> if (Test-Path "$env:ProgramFiles\7-Zip\7z.exe") {
>   & "$env:ProgramFiles\7-Zip\7z.exe" x -y "$dest" -o"$PWD"
> } elseif (Get-Command 7z.exe -ErrorAction SilentlyContinue) {
>   7z x -y "$dest" -o"$PWD"
> } else {
>   Write-Host "未检测到 7-Zip，请手动解压 $dest 到项目根目录（或安装 7-Zip 后重试）"
> }
> Remove-Item $dest -ErrorAction SilentlyContinue
> # 验证目录：应出现 $PWD\xtquant 目录
> if (Test-Path "$PWD\xtquant") { Write-Host "xtquant 安装完成" } else { Write-Host "xtquant 目录未找到，请检查解压是否成功" }
> ```
> 注：PowerShell 无法原生解压 .rar，需本机已安装 7-Zip（https://www.7-zip.org/）。如无 7-Zip，请手动解压 `xtquant.rar` 到项目根目录。

### 项目源码方式安装（可选）

#### # 克隆项目到本地
```bash
git clone https://github.com/quant-king299/EasyXT.git
cd EasyXT
```

#### # 安装依赖到Python环境

**方式一：直接安装依赖到系统Python环境**
```bash
pip install -r requirements.txt
```

**方式二：创建虚拟环境安装（推荐）**
```bash
# 创建虚拟环境
python -m venv .venv
# 激活虚拟环境（Windows）
.\.venv\Scripts\activate
# 安装依赖
pip install -r requirements.txt
```

**方式三：通过pip从GitHub直接安装（推荐用于生产环境）**
```bash
# 可选：创建虚拟环境
python -m venv .venv
.\.venv\Scripts\activate

# 更新pip并安装
python -m pip install -U pip setuptools wheel
pip install "git+https://github.com/quant-king299/EasyXT.git@v1.0.0"
```
## 🔧 配置

### 配置 QMT 路径（雪球跟单）

编辑：`strategies/xueqiu_follow/config/unified_config.json`

关键键名：`settings.account.qmt_path`（若同时存在 `account.qmt_path`，两处保持一致）。

示例（Windows JSON 需双反斜杠或用正斜杠）：
```json
{
  "settings": {
    "account": {
      "qmt_path": "D:\\国金证券QMT交易端\\userdata_mini",
      "account_id": "你的交易账号ID"
    }
  }
}
```

如何判断“正确目录”：
- 必须是 QMT 的 `userdata` 或 `userdata_mini` 目录本身
- 目录内通常包含 `xtquant`, `log`, `cfg` 等子目录
- 常见错写：`0MT`（应为 `QMT`）、`userdata mini`（应为 `userdata_mini`）

## 📚 快速开始

### 基础数据获取

```python
from easy_xt import EasyXT

# 创建API实例
api = EasyXT()

# 初始化数据服务
api.init_data()

# 获取股票价格
data = api.get_price('000001.SZ', count=100)
print(data.head())
```

### 简单交易示例

```python
# 初始化交易服务
api.init_trade(USERDATA_PATH)
api.add_account(ACCOUNT_ID)

# 买入股票
order_id = api.buy(
    account_id=ACCOUNT_ID,
    code='000001.SZ',
    volume=100,
    price_type='market'
)
```

### 运行雪球跟单

方式一：批处理脚本（Windows）
```powershell
.\strategies\xueqiu_follow\启动雪球跟单.bat
```

方式二：Python 入口脚本
```powershell
python strategies\xueqiu_follow\start_xueqiu_follow_easyxt.py
```

## 📖 学习路径

### 初学者路径

1. **01_基础入门.py** - 学习基本的数据获取和API使用
2. **02_交易基础.py** - 掌握基础交易操作
3. **05_数据周期详解.py** - 了解不同数据周期的使用

### 进阶路径

4. **03_高级交易.py** - 学习高级交易功能
5. **04_策略开发.py** - 开发量化交易策略
6. **06_扩展API学习实例.py** - 掌握扩展功能

### 实战路径

7. **07_qstock数据获取学习案例.py** - 真实数据获取
8. **08_数据获取与交易结合案例.py** - 数据与交易结合
9. **10_qstock真实数据交易案例_修复交易服务版.py** - 完整实战案例

## 🏗️ 项目结构

```
miniqmt扩展/
├── easy_xt/                    # 核心API模块
│   ├── __init__.py
│   ├── api.py                  # 主API接口
│   ├── data_api.py            # 数据接口
│   ├── trade_api.py           # 交易接口
│   ├── advanced_trade_api.py  # 高级交易接口
│   └── utils.py               # 工具函数
├── 学习实例/                   # 学习案例
│   ├── 01_基础入门.py
│   ├── 02_交易基础.py
│   ├── 03_高级交易.py
│   └── ...
├── config/                     # 配置文件
│   ├── config_template.py
│   └── config.py
├── data/                       # 数据存储目录
├── logs/                       # 日志目录
├── xtquant/                    # QMT相关文件
├── gui_app/                    # GUI应用（可选）
├── requirements.txt            # 依赖列表
├── README.md                   # 项目说明
└── .gitignore                  # Git忽略文件
```

## ⚠️ 风险提示

1. **投资风险**: 量化交易存在投资风险，请谨慎操作
2. **测试环境**: 建议先在模拟环境中测试策略
3. **资金管理**: 合理控制仓位，设置止损止盈
4. **合规要求**: 遵守相关法律法规和交易所规则

## 🤝 贡献

欢迎提交Issue和Pull Request！

### 开发指南

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [迅投QMT](https://www.gtja.com/) - 提供量化交易平台
- [qstock](https://github.com/tkfy920/qstock) - 股票数据获取
- [akshare](https://github.com/akfamily/akshare) - 金融数据接口

## 📞 联系方式

- 项目主页: https://github.com/quant-king299/EasyXT
- 问题反馈: https://github.com/quant-king299/EasyXT/issues
- 网站: **https://www.ptqmt.com**

## 📈 更新日志

### v1.0.0 (2025-01-11)
- 初始版本发布
- 完整的EasyXT API封装
- 丰富的学习实例
- 修复交易服务初始化问题


## 🧰 开发者工具与演示脚本

- 诊断工具（tools/）
  - `tools/debug_qmt_api.py`：检查 easy_xt API 结构，枚举 trade/data/account 能力并做基础调用验证
  - `tools/debug_data_api.py`：直连 DataAPI 验证 connect/xtquant 可用性及行情、列表获取
- 演示脚本（tools/demos/）
  - `tools/demos/P1-006_config_demo.py`：配置系统演示
  - `tools/demos/P1-009_monitor_demo.py`：监控告警演示
  - `tools/demos/P1-010_validator_demo.py`：配置校验器演示
  - `tools/demos/P1-011_scheduler_demo.py`：任务调度器演示（定时、周期、优先级、并发、重试、统计）
  - `tools/demos/P2-011_performance_demo.py`：性能/压测演示
  - `tools/demos/P2-012_error_handler_demo.py`：错误处理与恢复机制（重试/降级/优雅退化、断路器）
  - `tools/demos/P2-013_log_manager_demo.py`：日志管理（配置、检索/过滤、统计分析、导出）
  - `tools/demos/quick_start_monitor.py`：监控告警系统快速启动（演示用）
  - `tools/demos/find_current_holdings_api.py`：雪球接口探测（确定“当前持仓”来源）

运行示例（PowerShell）：
```powershell
# 诊断脚本
cd "c:\Users\Administrator\Desktop\miniqmt扩展\tools"
python .\debug_qmt_api.py
python .\debug_data_api.py

# 演示脚本
cd "c:\Users\Administrator\Desktop\miniqmt扩展\tools\demos"
python .\P1-006_config_demo.py
python .\P1-009_monitor_demo.py
python .\P1-010_validator_demo.py
python .\P1-011_scheduler_demo.py
python .\P2-011_performance_demo.py
python .\P2-012_error_handler_demo.py
python .\P2-013_log_manager_demo.py
python .\quick_start_monitor.py
python .\find_current_holdings_api.py
```

依赖说明：需预先安装“xtquant 特殊版本”，并按 README 配置（或设置环境变量 `XTQUANT_PATH`）；推荐通过 `pip install -e .\easy_xt` 可编辑安装后再运行脚本。

## 👀 监控系统

- 标准启动入口（独立服务）：
```powershell
python start_monitor.py --config config/monitor_config.json
# 查看状态
python start_monitor.py --status
```
- 演示快速启动：`tools/demos/quick_start_monitor.py`
- 相关组件：`easy_xt/realtime_data/monitor_service.py`

## ❄️ 雪球跟单策略

- 快速启动：
```powershell
# 批处理脚本（Windows）
.\strategies\xueqiu_follow\启动雪球跟单.bat

# 或 Python 入口
python strategies\xueqiu_follow\start_xueqiu_follow_easyxt.py
```
- 配置目录：`strategies/xueqiu_follow/config/`
- 示例/样本数据：`strategies/xueqiu_follow/fixtures/`

### 常见问题（FAQ）
- Q: 连接返回 -1 / “交易服务连接失败”？
  - A: 99% 为 `qmt_path` 路径错误：请指向本机 `userdata` 或 `userdata_mini` 目录；避免 `0MT` 与 `userdata mini` 等拼写错误；确保 QMT 已登录、Python 与 QMT 权限一致（管理员/普通一致）。

## 🔌 JQ2QMT / QKA 服务（如需）

- 快速启动 QKA 服务端：
```powershell
python strategies\jq2qmt\run_qka_server.py --account YOUR_ACCOUNT_ID --mini-qmt-path "C:\\Path\\To\\miniQMT" --host 127.0.0.1 --port 8000
```
- 若使用本地 xtquant 解压目录，设置环境变量：
```powershell
setx XTQUANT_PATH "C:\\xtquant_special"
```

---

**免责声明**: 本项目仅供学习和研究使用，不构成投资建议。使用本项目进行实际交易的风险由用户自行承担。

---

## 关注公众号 / 加群交流

- 关注公众号：

<img src="docs/assets/wechat_qr.jpg" alt="公众号二维码" width="260" />

- 欢迎加入QQ交流群：492287081（或扫码加入）

<img src="docs/assets/qq_group_qr.jpg" alt="QQ群二维码" width="260" />

- 欢迎加入知识星球，获取更多量化交易干货和一对一答疑服务

<img src="docs/assets/知识星球.jpg" alt="知识星球二维码" width="260" />