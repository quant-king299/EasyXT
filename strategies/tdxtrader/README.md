[![PyPI version](https://badge.fury.io/py/tdxtrader.svg)](https://badge.fury.io/py/tdxtrader)
[![Downloads](https://static.pepy.tech/badge/tdxtrader/month)](https://pepy.tech/project/tdxtrader)

# tdxtrader

通达信预警信号程序化交易

> 声明：本项目仅用于学习和研究，不保证交易收益，不作为投资建议，风险自负，请充分使用QMT模拟盘测试。

## 运行效果

![效果](../../docs/assets/output.png)

## 安装

```shell
pip install tdxtrader
```

## 预警指标设置

设置两个指标，一个作为买入信号，一个作为卖出信号

![预警指标](../../docs/assets/cut2.png)

## 预警文件设置

![预警文件](../../docs/assets/cut1.png)

## 自定义板块交易功能

新增支持通过通达信自定义板块文件触发买卖操作的功能。当股票被添加到指定的买入或卖出板块时，系统会自动执行相应的交易操作。

> 📚 **详细说明**：关于板块交易功能的完整技术文档，请查看 [板块交易功能详解](BLOCK_TRADING_FEATURES.md)

### 板块文件格式说明

通达信自定义板块文件(.blk)格式如下：
```
000001
000002
600001
600002
```
每行一个股票代码，只包含6位数字代码。

### 板块文件配置示例

在配置文件中添加`block_files`字段来指定板块文件和对应的操作：

```json
{
    "block_files": {
        "D:/new_tdx/T0002/blocknew/MR.blk": "buy",
        "D:/new_tdx/T0002/blocknew/MC.blk": "sell"
    }
}
```

### 板块交易工作原理

1. **文件监控**：系统会定期检查指定的板块文件是否有修改
2. **变化检测**：比较当前板块内容与上次检查时的内容
3. **新增股票**：检测到新增的股票时触发买入操作
4. **移除股票**：检测到移除的股票时触发卖出操作
5. **自动交易**：根据配置自动执行相应的交易委托

### 板块交易配置

在集成示例中，可以通过以下方式配置板块文件：

```python
# 板块文件配置
mr_block_path = r"D:\new_tdx\T0002\blocknew\MR.blk"
mc_block_path = r"D:\new_tdx\T0002\blocknew\MC.blk"
block_files = {
    mr_block_path: "buy",  # 买入板块
    mc_block_path: "sell"  # 卖出板块
}
```

### 使用步骤

1. 在通达信中创建自定义板块
2. 配置板块文件路径
3. 将股票添加到买入板块时自动触发买入
4. 将股票从买入板块移除时自动触发卖出

### 注意事项

- 板块文件必须是通达信标准的.blk格式
- 系统会自动处理股票代码的市场后缀(SH/SZ)
- 板块交易与预警文件交易可以同时使用
- 建议使用模拟盘测试板块交易功能

## 测试与运行

### 1. 准备工作

在运行测试之前，请确保完成以下准备工作：

1. **配置通达信预警**：
   - 在通达信中设置技术指标预警
   - 配置预警文件输出路径（默认为：`D:\new_tdx\sign.txt`）

2. **配置QMT账户**：
   - 确保QMT已正确安装并能正常登录
   - 在项目根目录的统一配置文件中配置账户信息

3. **检查依赖**：
   - 确保已安装所有必要的依赖包

### 2. 运行集成示例

项目提供了完整的集成示例，可以直接运行进行测试：

```bash
cd c:\Users\Administrator\Desktop\miniqmt扩展
python strategies/tdxtrader/tdxtrader_integration_example.py
```

该示例会：
- 自动从统一配置文件读取账户和QMT路径信息
- 初始化交易服务
- 启动通达信预警监听
- 处理买入/卖出信号并执行交易

### 3. 配置文件说明

集成示例使用项目根目录的统一配置文件 `config/unified_config.json`：

```json
{
  "settings": {
    "account": {
      "account_id": "你的账户ID",
      "qmt_path": "D:\\国金QMT交易端模拟\\userdata_mini"
    }
  }
}
```

### 4. 监控与调试

运行过程中可以通过以下方式监控系统状态：

1. **查看控制台输出**：实时显示交易信号和执行结果
2. **检查日志文件**：在 `strategies/tdxtrader/logs/` 目录下
3. **企业微信通知**：可配置企业微信机器人接收交易通知

### 5. 板块交易监控

板块交易功能会输出详细的日志信息：

- 板块文件变化检测
- 新增/移除股票识别
- 交易委托执行情况
- 委托结果反馈

通过观察这些日志可以了解板块交易的完整执行过程。

## demo

### 基础示例

```python
import tdxtrader
# 参数
account_id = 'xxxx' # 账号ID
mini_qmt_path = r'D:\国金证券QMT交易端\userdata_mini' # mini_qmt 路径
file_path = r'D:\new_tdx\sign.txt' # 预警文件路径
interval = 1 # 轮询时间(秒)
buy_sign = 'KDJ买入条件选股' # 买入信号
sell_sign = 'KDJ卖出条件选股' # 卖出信号

def buy_event(params):
    '''买入事件'''

    stock = params.get('stock')

    return { 
        'size': 200, 
        'price': -1, # 如果是限价，则设置价格
        'type': '市价', # 市价，限价
    }

def sell_event(params):
    '''卖出事件'''

    stock = params.get('stock')
    position = params.get('position')
    
    return { 
        'size': position.can_use_volume, # 卖全仓
        'price': -1,  # 如果是限价，则设置价格
        'type': '市价' # 市价，限价
    }


tdxtrader.start(
    account_id=account_id,
    mini_qmt_path=mini_qmt_path,
    file_path=file_path,
    interval=interval,
    buy_sign=buy_sign,
    sell_sign=sell_sign,
    buy_event=buy_event,
    sell_event=sell_event,
    cancel_after=10 # 10秒未成交则撤单
)
```

### 限价委托（获取预警价格）

stock对象中包含了当前股票的详细信息，可以通过price属性获取预警时的价格

```python
def buy_event(params):
    '''买入事件'''

    stock = params.get('stock')

    return { 
        'size': 200, 
        'price': stock.get('price'), # 如果是市价，则设置-1
        'type': '限价', # 市价，限价
    }

def sell_event(params):
    '''卖出事件'''

    stock = params.get('stock')
    position = params.get('position')

    return { 
        'size': position.can_use_volume, # 卖全仓
        'price': stock.get('price'),  # 如果是市价，则设置-1
        'type': '限价' # 市价，限价
    }
```

### 按金额买卖

``python
def buy_event(params):
    '''买入事件'''

    stock = params.get('stock')

    return { 
        'amount': 100000, 
        'price': stock.get('price'), # 如果是市价，则设置-1
        'type': '限价', # 市价，限价
    }

def sell_event(params):
    '''卖出事件'''

    stock = params.get('stock')

    return { 
        'amount': 100000, # 卖全仓
        'price': stock.get('price'),  # 如果是市价，则设置-1
        'type': '限价' # 市价，限价
    }
```

### 使用当前持仓判断是否买入

``python
def buy_event(params):
    '''买入数量'''

    stock = params.get('stock')
    position = params.get('position')

    if position is None:
        return { 
            'amount': 100000, 
            'price': stock.get('price'), # 如果是市价，则设置-1
            'type': '限价', # 市价，限价
        }
    else:
        return None

def sell_event(params):
    '''卖出数量'''

    stock = params.get('stock')

    return { 
        'amount': 100000, # 卖全仓
        'price': stock.get('price'),  # 如果是限价，则设置价格
        'type': '限价' # 市价，限价
    }
```

### 按资金比例买入（卖出逻辑一致）

``python
def buy_event(params):
    '''买入数量'''

    stock = params.get('stock')
    position = params.get('position')
    xt_trader = params.get('xt_trader')
    account = params.get('account')

    asset = xt_trader.query_stock_asset(account)

    if position is None:
        return { 
            'amount': asset.total_asset * 0.01, 
            'price': stock.get('price'), # 如果是市价，则设置-1
            'type': '限价', # 市价，限价
        }
    else:
        return None
```

### 多买入/卖出信号示例

``python
import tdxtrader
# 参数
account_id = 'xxxx' # 账号ID
mini_qmt_path = r'D:\国金证券QMT交易端\userdata_mini' # mini_qmt 路径
file_path = r'D:\new_tdx\sign.txt' # 预警文件路径
interval = 1 # 轮询时间(秒)
buy_sign = ['KDJ买入条件选股', 'MACD买入条件选股'] # 多个买入信号
sell_sign = ['KDJ卖出条件选股', 'MACD卖出条件选股'] # 多个卖出信号

def buy_event(params):
    '''买入事件'''

    stock = params.get('stock')

    return { 
        'size': 200, 
        'price': -1, # 如果是限价，则设置价格
        'type': '市价', # 市价，限价
    }

def sell_event(params):
    '''卖出事件'''

    stock = params.get('stock')
    position = params.get('position')
    
    return { 
        'size': position.can_use_volume, # 卖全仓
        'price': -1,  # 如果是限价，则设置价格
        'type': '市价' # 市价，限价
    }


tdxtrader.start(
    account_id=account_id,
    mini_qmt_path=mini_qmt_path,
    file_path=file_path,
    interval=interval,
    buy_sign=buy_sign,
    sell_sign=sell_sign,
    buy_event=buy_event,
    sell_event=sell_event,
    cancel_after=10 # 10秒未成交则撤单
)
```

### 企业微信通知

利用企业微信机器人发送通知

设置群机器人参看：https://open.work.weixin.qq.com/help2/pc/14931

```
tdxtrader.start(
    account_id=account_id,
    mini_qmt_path=mini_qmt_path,
    file_path=file_path,
    interval=interval,
    buy_sign=buy_sign,
    sell_sign=sell_sign,
    buy_event=buy_event,
    sell_event=sell_event,
    cancel_after=10, # 10秒未成交则撤单,
    wechat_webhook_url='你的webhook_url' # 企业微信机器人webhook url
)
```

![微信机器人](../../docs/assets/wxbot.png)

![消息示例](../../docs/assets/msg.png)

## 详细参数

### account_id

QMT账号ID

### mini_qmt_path

QMT mini路径

### file_path

预警文件路径

### interval

轮询时间(秒)

### buy_sign

买入信号

### sell_sign

卖出信号

### buy_event

买入事件

### sell_event

卖出事件

### cancel_after

未成交撤单时间(秒)

### wechat_webhook_url

企业微信机器人webhook url

## 第三方组件

本项目包含来自[zsrl/tdxtrader](https://github.com/zsrl/tdxtrader)的tdxtrader组件，该组件使用MIT许可证。
原始项目地址：[https://github.com/zsrl/tdxtrader](https://github.com/zsrl/tdxtrader)
