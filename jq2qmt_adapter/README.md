# jq2qmt-adapter

用于将 EasyXT 策略与 JQ2QMT/qka 服务集成的适配层。当前包为最小包装：
- 复用本仓库 `strategies/adapters/jq2qmt_adapter.py` 的实现
- 通过在运行时注入项目根目录到 `sys.path` 来完成导入

安装（源码，可编辑安装）：

```powershell
cd "c:\Users\Administrator\Desktop\miniqmt扩展\jq2qmt_adapter"
pip install -e .
```

使用示例：

```python
from jq2qmt_adapter import EasyXTJQ2QMTAdapter
adapter = EasyXTJQ2QMTAdapter(config={
    "server_url": "http://127.0.0.1:8000",
    "order_settings": {"enabled": True, "mode": "qka", "timeout": 10},
    "qka_settings": {"enabled": True, "base_url": "http://127.0.0.1:8000", "token": "YOUR_TOKEN"}
})
```

依赖：
- Python >= 3.8
- easy-xt（本地先安装）
- requests
- 若启用 qka 模式，请确保 qka 服务端已在本地运行。
