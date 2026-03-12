# EasyXT 多数据源支持的数据类型完整报告

> **创建时间**：2026-03-12
> **数据源**：通达信、东方财富、同花顺
> **状态**：Tick 数据已支持但未实现

---

## 📊 一、当前已实现的数据类型

### 1. 通达信（TdxDataProvider）

| 数据类型 | 方法名 | 状态 | 说明 |
|---------|--------|------|------|
| **实时行情** | `get_realtime_quotes()` | ✅ 已实现 | 包含五档买卖价和量 |
| **分时数据** | `get_minute_data()` | ✅ 已实现 | 240条分时数据 |
| **K线数据** | `get_kline_data()` | ✅ 已实现 | 1/5/15/30/60分钟、日/周/月 |
| **指数行情** | `get_index_quotes()` | ✅ 已实现 | 上证、深证、创业板等指数 |
| **Tick数据** | - | ❌ **未实现** | pytdx支持，需添加 |
| **逐笔成交** | - | ❌ **未实现** | pytdx支持，需添加 |

**已实现的字段（实时行情）：**
```python
{
    'code': '股票代码',
    'name': '股票名称',
    'price': '最新价',
    'last_close': '昨收价',
    'change': '涨跌额',
    'change_pct': '涨跌幅',
    'volume': '成交量',
    'turnover': '成交额',
    'high': '最高价',
    'low': '最低价',
    'open': '开盘价',
    # 五档买价
    'bid1', 'bid2', 'bid3', 'bid4', 'bid5',
    # 五档卖价
    'ask1', 'ask2', 'ask3', 'ask4', 'ask5',
    # 五档买量
    'bid1_vol', 'bid2_vol', 'bid3_vol', 'bid4_vol', 'bid5_vol',
    # 五档卖量
    'ask1_vol', 'ask2_vol', 'ask3_vol', 'ask4_vol', 'ask5_vol',
}
```

---

### 2. 东方财富（EastmoneyDataProvider）

| 数据类型 | 方法名 | 状态 | 说明 |
|---------|--------|------|------|
| **实时行情** | `get_realtime_quotes()` | ✅ 已实现 | HTTP接口获取 |
| **热门股票** | `get_hot_stocks()` | ✅ 已实现 | 热度排行 |
| **板块数据** | `get_sector_data()` | ✅ 已实现 | 概念/行业板块 |
| **K线数据** | `get_kline_data()` | ✅ **新增** | 支持多周期K线 |
| **分时数据** | `get_minute_data()` | ⚠️ 部分实现 | API有反爬限制 |
| **Tick数据** | - | ❌ 不支持 | API限制 |

**热门股票类型：**
- 大家都在看
- 快速飙升中
- 技术交易派
- 价值投资派
- 趋势投资派

---

### 3. 同花顺（ThsDataProvider）

| 数据类型 | 方法名 | 状态 | 说明 |
|---------|--------|------|------|
| **热度排行** | `get_hot_stocks()` | ✅ 已实现 | 热度数据 |
| **概念数据** | `get_sector_data()` | ✅ 已实现 | 概念板块 |
| **龙虎榜** | - | ⚠️ 部分实现 | 资金流向 |
| **实时行情** | - | ❌ 不支持 | 只提供辅助数据 |

---

## 🆕 二、未实现但 pytdx 支持的数据类型

### 1. Tick 逐笔成交数据

**pytdx API：**
```python
# 实时逐笔成交
TdxHq_API().get_transaction_data(market, code, start, count)

# 历史逐笔成交
TdxHq_API().get_history_transaction_data(market, code, start, count, date)
```

**数据内容：**
- 逐笔成交时间
- 成交价格
- 成交数量
- 买卖方向（内盘/外盘）

**使用场景：**
- 高频交易策略
- 逐笔成交分析
- 大单追踪
- 资金流向分析

---

### 2. Level-2 深度数据

**pytdx 支持的 Level-2 数据：**
```python
# Level-2 逐笔委托
TdxHq_API().get_history_transaction_data()

# Level-2 实时行情补充
TdxHq_API().get_l2quoteaux()

# Level-2 委托队列
TdxHq_API().get_l2orderqueue()

# Level-2 千档盘口
TdxHq_API().get_l2thousand()
```

**数据内容：**
- 逐笔委托（挂单）
- 委托队列（买一/卖一队列）
- 千档盘口
- 实时行情补充

**使用场景：**
- 超高频交易
- 委托分析
- 深度盘口分析
- 大单监控

---

### 3. 期货数据

**pytdx 支持期货数据：**
- 期货行情
- 期货K线
- 期货分时
- 期货tick

**市场ID：**
- 商品期货：市场ID 6-8
- 股指期货：市场ID 4

---

### 4. 融资融券数据

**pytdx 支持：**
- 融资融券余额
- 融资买入额
- 融券卖出额

---

## 📋 三、数据类型详细对比

### 3.1 按数据时效分类

| 类型 | 子类型 | 通达信 | 东方财富 | 同花顺 |
|------|--------|--------|---------|--------|
| **实时数据** | 实时行情 | ✅ | ✅ | ❌ |
| | 五档盘口 | ✅ | ✅ | ❌ |
| | Tick逐笔 | ❌ | ❌ | ❌ |
| | Level-2 | ❌ | ❌ | ❌ |
| **历史数据** | 分时 | ✅ | ✅ | ❌ |
| | K线 | ✅ | ⚠️ | ❌ |
| | 逐笔历史 | ❌ | ❌ | ❌ |
| **辅助数据** | 热度排行 | ❌ | ✅ | ✅ |
| | 板块数据 | ❌ | ✅ | ✅ |
| | 指数行情 | ✅ | ⚠️ | ❌ |

### 3.2 按市场类型分类

| 市场类型 | 通达信 | 东方财富 | 同花顺 |
|---------|--------|---------|--------|
| **股票** | ✅ 完整支持 | ✅ 基础支持 | ⚠️ 辅助数据 |
| **基金** | ✅ 已修复价格 | ✅ 支持 | ❌ 不支持 |
| **指数** | ✅ 支持 | ⚠️ 部分支持 | ❌ 不支持 |
| **期货** | ⚠️ pytdx支持 | ❌ 不支持 | ❌ 不支持 |
| **债券** | ✅ 支持 | ⚠️ 部分支持 | ❌ 不支持 |

---

## 🚀 四、推荐实现的数据类型优先级

### 第一优先级（立即可做）

1. **Tick 逐笔成交数据** ⭐⭐⭐⭐⭐
   - **价值**：高价值，高频策略必需
   - **难度**：🟢 低（pytdx已支持）
   - **时间**：30分钟

2. **历史逐笔数据** ⭐⭐⭐⭐⭐
   - **价值**：回测必需
   - **难度**：🟢 低
   - **时间**：30分钟

### 第二优先级（近期规划）

3. **期货数据支持** ⭐⭐⭐⭐
   - **价值**：扩展到期货策略
   - **难度**：🟡 中（需要市场ID映射）
   - **时间**：2小时

4. **融资融券数据** ⭐⭐⭐
   - **价值**：辅助决策
   - **难度**：🟢 低
   - **时间**：1小时

### 第三优先级（长期规划）

5. **Level-2 深度数据** ⭐⭐⭐
   - **价值**：超高频策略
   - **难度**：🔴 高（需要Level-2权限）
   - **时间**：5小时

---

## 💻 五、Tick 数据实现示例

### 添加到 TdxDataProvider

```python
def get_transaction_data(self, code: str, count: int = 100) -> List[Dict[str, Any]]:
    """获取实时逐笔成交数据（Tick数据）

    Args:
        code: 股票代码
        count: 获取条数

    Returns:
        List[Dict]: 逐笔成交数据
        [
            {
                'code': '000001',
                'datetime': '14:30:00',
                'price': 10.50,
                'volume': 1000,
                'direction': 'B',  # B=买盘，S=卖盘，N=未知
                'source': 'tdx'
            },
            ...
        ]
    """
    try:
        if not self._ensure_connected():
            return []

        market, std_code = self._parse_stock_code(code)

        # 判断是否为基金
        is_etf = std_code.startswith('5') or std_code.startswith('1')
        price_divisor = 10.0 if is_etf else 1.0

        # 获取逐笔成交数据
        data = self.api.get_transaction_data(market, std_code, 0, count)

        if not data:
            return []

        formatted_data = []
        for item in data:
            formatted_data.append({
                'code': code,
                'datetime': item.get('time', ''),  # 格式：HH:MM:SS
                'price': float(item.get('price', 0)) / price_divisor,
                'volume': int(item.get('volume', 0)),
                'direction': item.get('direction', 'N'),  # B/S/N
                'source': 'tdx_transaction'
            })

        return formatted_data

    except Exception as e:
        self.logger.error(f"获取逐笔成交数据失败: {e}")
        return []


def get_history_transaction_data(self, code: str, date: str = None, count: int = 500) -> List[Dict[str, Any]]:
    """获取历史逐笔成交数据

    Args:
        code: 股票代码
        date: 日期 (YYYYMMDD)，默认当天
        count: 获取条数

    Returns:
        List[Dict]: 历史逐笔成交数据
    """
    try:
        if not self._ensure_connected():
            return []

        market, std_code = self._parse_stock_code(code)

        # 判断是否为基金
        is_etf = std_code.startswith('5') or std_code.startswith('1')
        price_divisor = 10.0 if is_etf else 1.0

        # 如果没有指定日期，使用今天
        if date is None:
            from datetime import datetime
            date = datetime.now().strftime('%Y%m%d')

        # 获取历史逐笔数据
        data = self.api.get_history_transaction_data(market, std_code, 0, count, date)

        if not data:
            return []

        formatted_data = []
        for item in data:
            formatted_data.append({
                'code': code,
                'datetime': item.get('time', ''),
                'price': float(item.get('price', 0)) / price_divisor,
                'volume': int(item.get('volume', 0)),
                'direction': item.get('direction', 'N'),
                'source': 'tdx_history_transaction'
            })

        return formatted_data

    except Exception as e:
        self.logger.error(f"获取历史逐笔数据失败: {e}")
        return []
```

---

## 📈 六、实际应用场景

### 场景 1：实时行情（已支持）

```python
tdx = TdxDataProvider()
quotes = tdx.get_realtime_quotes(['000001.SZ'])

# 返回
[{
    'code': '000001.SZ',
    'price': 10.50,
    'bid1': 10.49,
    'ask1': 10.50,
    'bid1_vol': 1500,
    'ask1_vol': 2000,
    ...
}]
```

### 场景 2：Tick 数据（待实现）

```python
tdx = TdxDataProvider()
ticks = tdx.get_transaction_data('000001.SZ', count=100)

# 返回（待实现）
[{
    'code': '000001.SZ',
    'datetime': '14:30:00',
    'price': 10.50,
    'volume': 1000,
    'direction': 'B',  # 主动买
}]
```

### 场景 3：分时数据（已支持）

```python
minute = tdx.get_minute_data('000001.SZ', count=240)

# 返回
[{
    'code': '000001.SZ',
    'datetime': '09:31:00',
    'price': 10.45,
    'volume': 1500,
}, ...]
```

### 场景 4：K线数据（已支持）

```python
kline = tdx.get_kline_data('000001.SZ', period='D', count=100)

# 返回
[{
    'code': '000001.SZ',
    'datetime': '2024-01-01',
    'open': 10.40,
    'high': 10.60,
    'low': 10.35,
    'close': 10.50,
    'volume': 1500000,
}, ...]
```

---

## 🎯 七、总结与建议

### 当前状态

| 数据类型 | 实现状态 | 完整度 | 建议 |
|---------|---------|--------|------|
| 实时行情 | ✅ 已实现 | ⭐⭐⭐⭐⭐ | 已完善 |
| 五档盘口 | ✅ 已实现 | ⭐⭐⭐⭐⭐ | 已完整 |
| 分时数据 | ✅ 已实现 | ⭐⭐⭐⭐ | 已完善 |
| K线数据 | ✅ 已实现 | ⭐⭐⭐⭐⭐ | 已完善 |
| 指数行情 | ✅ 已实现 | ⭐⭐⭐⭐ | 基础完善 |
| **Tick逐笔** | ❌ 未实现 | - | **建议添加** |
| **历史逐笔** | ❌ 未实现 | - | **建议添加** |
| 期货数据 | ❌ 未实现 | - | 可选 |
| Level-2 | ❌ 未实现 | - | 需权限 |

### 推荐实现

1. **立即实现**：Tick 逐笔成交数据（30分钟）
   - 高价值
   - 低难度
   - pytdx已支持

2. **近期实现**：历史逐笔数据（30分钟）
   - 回测必需
   - 同样简单

3. **可选实现**：期货数据
   - 扩展应用场景
   - 需要额外测试

---

## 📝 附录：pytdx 完整 API 参考

**行情数据：**
- `get_security_quotes()` - 实时行情（已使用）
- `get_market_state()` - 市场状态

**K线数据：**
- `get_security_bars()` - K线数据（已使用）
- `get_index_bars()` - 指数K线

**分时数据：**
- `get_minute_time_data()` - 分时数据（已使用）

**Tick数据：**
- `get_transaction_data()` - 实时逐笔（**待实现**）
- `get_history_transaction_data()` - 历史逐笔（**待实现**）

**Level-2数据：**
- `get_l2quoteaux()` - Level-2行情补充
- `get_l2orderqueue()` - 委托队列
- `get_l2thousand()` - 千档盘口

**其他：**
- `get_security_list()` - 股票列表
- `get_security_count()` - 股票数量
- `get_finance_info()` - 财务信息
