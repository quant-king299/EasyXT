# JQ → miniQMT（qka-only）联调测试步骤

本指南提供从零到可测试的分步操作，帮助你验证"聚宽策略 → miniQMT（通过 qka）"的单策略一键同步与下单流程。

## 1. 前置准备

- 操作系统：Windows（PowerShell）
- Python 环境：Python 3.8+（确保能导入 `xtquant` 与 `PyQt5`）
- miniQMT 客户端：已安装并可连接交易账户
- 项目路径：`c:\Users\Administrator\Desktop\miniqmt扩展`
- 依赖安装：
```
# 进入项目根目录
cd "c:\Users\Administrator\Desktop\miniqmt扩展"

# 安装基础依赖（如未安装）
pip install -r requirements.txt
# 若未安装 PyQt5（GUI 需要）
pip install PyQt5

# 重要：安装"xtquant 特殊版本"（不要用 pip 官方最新版）
# 从发布页下载：https://github.com/quant-king299/EasyXT/releases/tag/xueqiu_follow-xtquant-v1.0
# 如果发布页包含 xtquant 的 .whl 包，使用：
#   pip install C:\Path\To\xtquant-*.whl
# 如果发布页提供的是解压目录（含 xtquant 包），建议解压到如 C:\xtquant_special，然后设置环境变量供本项目识别：
#   setx XTQUANT_PATH "C:\\xtquant_special"  # 重新打开终端生效
#   # run_qka_server.py 会自动将 XTQUANT_PATH 注入 sys.path

# 通过 pip 从 GitHub 安装 easy_xt（推荐用标签）
# 推荐固定到稳定标签 v1.0.0：

# 可选：创建虚拟环境
# python -m venv .venv
# .\.venv\Scripts\Activate.ps1

python -m pip install -U pip setuptools wheel

pip install "git+https://github.com/quant-king299/EasyXT.git@v1.0.0"

# 国内镜像（依赖走镜像，源码仍从 GitHub 拉取）：
# pip install -i https://pypi.tuna.tsinghua.edu.cn/simple "git+https://github.com/quant-king299/EasyXT.git@v1.0.0"

# 验证安装：
# python -c "import easy_xt; print('easy_xt import OK:', easy_xt.__name__); from easy_xt import get_api; api = get_api(); print('get_api OK:', type(api))"

# 说明：pip 仅安装 Python 包，不会安装 QMT/xtquant，本地需自备。
```

## 2. 聚宽研究环境准备

在聚宽研究环境中使用 QMT 交易功能，需要上传 qmt_client_mini.py 文件：

1. 下载 qmt_client_mini.py 文件：
   - 文件路径：`strategies/jq2qmt/qmt_client_mini.py`
   - 该文件是 QMT 客户端最小内核版本，仅保留 client.api 核心功能
   - 代码共 53 行，非常小巧

2. 上传到聚宽研究环境：
   - 登录聚宽研究环境
   - 在研究环境中创建新文件
   - 将 qmt_client_mini.py 的内容复制到新文件中
   - 保存文件名为 `qmt_client_mini.py`

3. 在聚宽策略中使用：
```python
# 导入 QMT 客户端
from qmt_client_mini import QMTClient

# 初始化客户端（需要与 qka 服务器配置一致）
client = QMTClient(
    base_url="http://localhost:8000",  # qka 服务器地址
    token="YOUR_TOKEN"  # 与 qka 服务器配置的 token 一致
)

# 调用交易接口示例
try:
    # 查询账户资产
    asset = client.api('query_stock_asset')
    print("账户资产:", asset)
    
    # 下单示例
    order_result = client.api('order_stock', 
                             stock_code='000001.SZ',
                             order_type=23,  # 买入
                             order_volume=100,
                             price_type=1,   # 市价
                             price=0)
    print("下单结果:", order_result)
    
except Exception as e:
    print(f"调用失败: {e}")
```

## 3. 启动 qka 服务端并获取 token

qka 服务端将把 miniQMT 的交易接口以 FastAPI 暴露，对外采用 `X-Token` 认证。服务启动时会打印授权 Token。

- 启动方式（推荐使用仓库脚本，避免路径问题）：
```powershell
cd "c:\Users\Administrator\Desktop\miniqmt扩展"
python strategies\jq2qmt\run_qka_server.py --account YOUR_ACCOUNT_ID --mini-qmt-path "C:\\Path\\To\\miniQMT" --host 127.0.0.1 --port 8000


cd "c:\Users\Administrator\Desktop\miniqmt扩展"
python strategies\jq2qmt\run_qka_server.py --account 39020958 --mini-qmt-path "D:\国金QMT交易端模拟\userdata_mini" --host 127.0.0.1 --port 8000
# 如需自定义 Token：追加 --token YOUR_TOKEN
```
- 启动成功后，控制台会打印类似：
```powershell
授权Token: <THIS_IS_THE_TOKEN>
```
- 记录该 Token，稍后将写入客户端配置。

说明：
- `YOUR_ACCOUNT_ID` 为你的 QMT 证券账户 ID（如 `110XXXXXX`）
- `C:\Path\To\miniQMT` 为你的 miniQMT 安装目录（示例：`C:\QMT\bin` 或实际路径）

## 4. 配置客户端（jq2qmt_config.json）

修改 `strategies\jq2qmt\config\jq2qmt_config.json`：
- 启用 qka 模式
- 设置 `qka_settings.base_url` 为你的服务地址（如 `http://127.0.0.1:8000`）
- 将 `qka_settings.token` 替换为步骤 3 的实际 Token

示例关键片段：
```json
{
  "enabled": true,
  "order_settings": { "enabled": true, "mode": "qka", "timeout": 10 },
  "qka_settings": { "enabled": true, "base_url": "http://127.0.0.1:8000", "token": "REPLACE_WITH_REAL_TOKEN" }
}
```

## 5. 运行示例脚本（命令行）

示例脚本演示：
- 同步本地模拟持仓到 qka 账户
- 比对差异并生成市场单
- 调用 qka 接口逐单下发
- 检查连接有效性

运行命令：
```powershell
cd "c:\Users\Administrator\Desktop\miniqmt扩展"
python strategies\examples\jq2qmt_integration_example.py
```
预期输出（示意）：
- 打印持仓同步、差异统计、订单提交结果
- 打印 `qka连接测试: OK`

## 6. 运行 GUI 测试（一键同步）

GUI 集成了"一键同步下单"按钮，便于交互式测试。

- 启动 GUI：
```powershell
cd "c:\Users\Administrator\Desktop\miniqmt扩展"
python gui_app\main_window.py
```
- 在主界面切换到"JQ2QMT 集成管理"页签：
  1) 在"配置"页签中，点击"测试连接"，确保显示连接成功
  2) 切换到"同步控制"页签，点击"【一键同步下单】"，将自动：
     - 读取本地持仓（需设置提供者，见下一步）
     - 查询 qka 账户持仓
     - 比对差异并生成市场单
     - 下发订单并弹窗显示结果

### 设置本地持仓提供者（一次性）

`JQ2QMTWidget` 暴露了 `set_local_positions_provider(callable)` 接口，你需要在主窗口或集成代码中注入一个函数以返回 EasyXT 标准持仓列表。

示例（伪代码，供你在主窗口实例化后调用）：
```python
# 伪代码：将本地持仓提供者注入到 JQ2QMTWidget
from gui_app.widgets.jq2qmt_widget import JQ2QMTWidget

jq_widget = JQ2QMTWidget()

def my_local_positions_provider():
    # 从你的策略/账户模块读取持仓，返回 EasyXT 格式
    return [
        {"symbol": "000001.SZ", "name": "平安银行", "quantity": 1000, "avg_price": 12.5},
        {"symbol": "000002.SZ", "name": "万科A", "quantity": 500, "avg_price": 25.8},
    ]

jq_widget.set_local_positions_provider(my_local_positions_provider)
```

注：如果不设置提供者，GUI 将提示"未设置本地持仓提供者"。

## 7. 成功验证标准

- 命令行示例：
  - 控制台打印订单提交结果 `{"success": true, ...}` 或各单结果列表
  - 打印 `qka连接测试: OK`
- GUI：
  - "测试连接"显示成功（绿色状态）
  - 点击"【一键同步下单】"后弹出提示"提交完成: 成功"，日志区域显示订单详情
  - 持仓查看页可刷新并显示最新持仓

## 8. 常见问题与排查

- 无法导入 `xtquant`：
  - 请安装/修复 xtquant：`pip install xtquant`
  - 确认 miniQMT 安装完整，且 Python 能访问到相关 DLL/依赖
- qka 服务端未打印 Token 或 401：
  - 请确认服务端启动参数正确，控制台会打印"授权Token: ..."
  - 客户端 `jq2qmt_config.json` 的 `qka_settings.token` 必须与服务端一致
- 下单接口返回失败：
  - 检查 `order_type`、`price_type` 常量（适配器在无 `xtquant.xtconstant` 时使用回退常量 23/24, 0/1）
  - 检查账户是否有交易权限、代码是否正确、交易时段是否可下单
- GUI 没有本地持仓：
  - 调用 `set_local_positions_provider()` 注入持仓提供者，或先用命令行示例验证逻辑
- `query_stock_asset` 字段不一致：
  - 适配器已对 `holdings/positions` 键名进行容错映射，如仍异常，请提供实际返回结构，以便快速适配

## 9. 回归与扩展

- 当前范围：单策略、一键同步、市场单、qka-only 模式
- 可扩展：
  - 限价单支持（在 `one_click_sync(price_type='limit', price_map=...)` 传入价格）
  - 风控前置校验（白名单、滑点、仓位比例）
  - 多策略合并持仓与冲突处理（后续阶段）

---
如需要，我可以将你的策略/账户模块默认绑定为 GUI 的本地持仓提供者，或根据你的实际服务端返回结构进一步适配字段。