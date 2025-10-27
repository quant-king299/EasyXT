# easy-xt

面向 miniQMT / EasyXT 集成的通用辅助与适配层。

重要说明：本包不包含 `xtquant` 依赖，请先安装“特殊版本 xtquant”（不要使用 pip 上的最新版），再使用本包。

获取方式：
- 发布页：https://github.com/quant-king299/EasyXT/releases/tag/xueqiu_follow-xtquant-v1.0
- 若发布页提供 .whl 包：直接 pip 安装，例如 `pip install C:\Path\To\xtquant-*.whl`
- 若提供解压目录（包含 xtquant 包）：解压到如 `C:\xtquant_special`，并设置环境变量以便本项目识别：
  - PowerShell：`setx XTQUANT_PATH "C:\\xtquant_special"`（重开终端生效）
  - 本仓库的 `strategies/jq2qmt/run_qka_server.py` 会自动把 `XTQUANT_PATH` 注入 sys.path

安装（源码，可编辑安装）：

```powershell
cd "c:\Users\Administrator\Desktop\miniqmt扩展\easy_xt"
pip install -e .
```

卸载重装（本地调试）：

```powershell
pip uninstall easy-xt -y
pip install -e .
```

导入示例：

```python
from easy_xt import get_api, ExtendedAPI
api = get_api()
ext = ExtendedAPI()
```

依赖：
- Python >= 3.8
- pydantic, requests（由本包自动安装）
- xtquant（请按你的专用安装方式预先安装）
