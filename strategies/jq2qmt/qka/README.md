# qka (快量化)

快捷量化助手（Quick Quantitative Assistant）是一个简洁易用，可实操A股的量化交易框架。

## 安装

```bash
pip install qka
```

## 使用方法

### QMTServer

```python
from qka.server import QMTServer

server = QMTServer("YOUR_ACCOUNT_ID", "YOUR_QMT_PATH")
# 服务器启动时会打印生成的token
server.start()
```

### QMTClient

#### 查询

```python
from qka.client import QMTClient

client = QMTClient(token="服务器打印的token")
# 调用接口
result = client.api("query_stock_asset")
```

#### 下单

```python
from qka.client import QMTClient
from xtquant import xtconstant

client = QMTClient(token="服务器打印的token", url="服务端地址")
# 调用接口
result = client.api("order_stock", stock_code='600000.SH', order_type=xtconstant.STOCK_BUY, order_volume =1000, price_type=xtconstant.FIX_PRICE, price=10.5)
```
<!-- ```python
datas = qka.data(
  stock_list=[], 
  period='tick', 
  indicators=[
    'MA',
    'BOLL'
  ]
)


def strategy(bar, bars, borker):
  pass

res = qka.backtest(datas, start_time='', end_time='', strategy=strategy)

borker = qka.broker(type='qmt', config={})

qka.trade(datas, start_time='', strategy=strategy, borker=borker)

``` -->
