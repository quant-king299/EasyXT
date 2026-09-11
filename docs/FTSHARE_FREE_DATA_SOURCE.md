# FTShare 免费版数据源

EasyXT 已保存官方免费版 160 项接口清单，并接入历史数据层与统一实时行情层。

## 配置

真实密钥只写入项目根目录 `.env.local`：

```env
FTSHARE_API_KEY=你的密钥
FTSHARE_ENABLED=true
EASYXT_FTSHARE_ENABLED=true
```

## 查询和调用免费接口

```python
from core.data_manager.config import DataManagerConfig
from core.data_manager.sources.ftshare_source import FTShareSource

source = FTShareSource(DataManagerConfig().get_source_config("ftshare"))
source.connect()
print(source.list_free_endpoints("资金流"))

df = source.call_free(
    "东方财富个股估值",
    symbol="000001",
    trade_date="20260911",
)
```

清单文件为 `config/ftshare_free_endpoints.json`，每项包含中文名称、SDK 方法、
接口路径、参数和官方文档链接。`call_ftshare_free` 只允许调用这份免费清单中的方法。

## 统一行情 API

```python
from easy_xt.realtime_data.unified_api import UnifiedDataAPI

api = UnifiedDataAPI()
api.connect_all()
quotes = api.get_realtime_quotes(
    ["000001.SZ", "600519.SH"],
    preferred_source="ftshare",
)
```

FTShare 免费行情是 HTTP 实时快照轮询，不是 Tick 推送。大QMT桥接优先级仍高于
FTShare；FTShare 默认作为跨平台实时快照与基本面字段补充源。
