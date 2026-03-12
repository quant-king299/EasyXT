# QMT vs 多数据源数据类型对比

> **更新时间**：2026-03-12
> **目的**：对齐多数据源与 QMT 的数据类型支持

---

## 📊 一、QMT 支持的数据类型（完整列表）

### Level-1 数据

| 数据类型 | 周期标识 | 说明 | QMT方法 |
|---------|---------|------|---------|
| **分笔数据** | `tick` | Tick逐笔成交 | `download_history_data()` |
| **1分钟线** | `1m` | 1分钟K线 | `download_history_data()` |
| **5分钟线** | `5m` | 5分钟K线 | `download_history_data()` |
| **15分钟线** | `15m` | 15分钟K线 | `download_history_data()` |
| **30分钟线** | `30m` | 30分钟K线 | `download_history_data()` |
| **1小时线** | `1h` | 1小时K线 | `download_history_data()` |
| **日线** | `1d` | 日K线 | `download_history_data()` |

### Level-2 数据（需要权限）

| 数据类型 | 周期标识 | 说明 | QMT方法 |
|---------|---------|------|---------|
| **L2实时行情快照** | `l2quote` | Level2完整快照 | `get_full_tick()` |
| **L2逐笔委托** | `l2order` | 逐笔挂单数据 | `get_l2_order()` |
| **L2逐笔成交** | `l2transaction` | 逐笔成交数据 | `get_l2_transaction()` |
| **L2行情补充** | `l2quoteaux` | L2补充数据 | `get_l2_quote()` |
| **L2委托队列** | `l2orderqueue` | 买卖一档委托队列 | `get_l2_order_queue()` |
| **L2千档盘口** | `l2thousand` | 买卖千档数据 | `get_l2_thousand()` |

---

## 🔄 二、多数据源（TDX）当前支持情况

### ✅ 已完全实现

| 数据类型 | TdxProvider | 对齐QMT | 方法名 |
|---------|-----------|---------|--------|
| **实时行情** | ✅ | ✅ | `get_realtime_quotes()` |
| **五档盘口** | ✅ | ✅ | `get_realtime_quotes()` |
| **分时数据** | ✅ | ⚠️ | `get_minute_data()` (240条) |
| **K线数据** | ✅ | ✅ | `get_kline_data()` (多周期) |
| **Tick逐笔** | ✅ | ✅ | `get_transaction_data()` |
| **历史逐笔** | ✅ | ✅ | `get_history_transaction_data()` |
| **指数行情** | ✅ | ⚠️ | `get_index_quotes()` |
| **股票列表** | ✅ | ⚠️ | `get_stock_list()` |

### ⚠️ 部分实现

| 数据类型 | TdxProvider | 对齐QMT | 说明 |
|---------|-----------|---------|------|
| **分时数据** | ✅ 240条 | ⚠️ | QMT可获取全天，TDX限制240条 |
| **交易日历** | ✅ | ⚠️ | 简化实现，QMT更准确 |
| **财务数据** | ❌ | ✅ | TDX未实现 |

### ❌ 未实现

| 数据类型 | TdxProvider | QMT支持 | pytdx支持 |
|---------|-----------|---------|-----------|
| **Level-2行情** | ❌ | ✅ | ✅ pytdx支持，待实现 |
| **Level-2逐笔委托** | ❌ | ✅ | ✅ pytdx支持，待实现 |
| **Level-2委托队列** | ❌ | ✅ | ✅ pytdx支持，待实现 |
| **Level-2千档** | ❌ | ✅ | ✅ pytdx支持，待实现 |

---

## 📋 三、数据类型对比表

### 3.1 按用途分类

#### 实时交易场景

| 数据类型 | QMT | TDX | 东方财富 | 说明 |
|---------|-----|-----|---------|------|
| **实时价格** | ✅ | ✅ | ✅ | 都支持 |
| **五档盘口** | ✅ | ✅ | ⚠️ | TDX最完整 |
| **Tick逐笔** | ✅ | ✅ | ❌ | TDX新增支持 |
| **Level-2** | ✅ | ❌ | ❌ | 仅QMT |

#### 历史数据场景

| 数据类型 | QMT | TDX | 东方财富 | 说明 |
|---------|-----|-----|---------|------|
| **分时数据** | ✅ 全天 | ⚠️ 240条 | ✅ 全天 | 东方财富更完整 |
| **K线数据** | ✅ | ✅ | ⚠️ | TDX最完整 |
| **历史逐笔** | ✅ | ✅ | ❌ | TDX新增支持 |
| **财务数据** | ✅ | ❌ | ❌ | 仅QMT |

#### 辅助数据场景

| 数据类型 | QMT | TDX | 东方财富 | 同花顺 |
|---------|-----|-----|---------|--------|
| **股票列表** | ✅ | ✅ | ⚠️ | ⚠️ |
| **交易日历** | ✅ | ⚠️ | ⚠️ | ❌ |
| **热度排行** | ❌ | ❌ | ✅ | ✅ |
| **板块数据** | ❌ | ❌ | ✅ | ✅ |

---

## 💡 四、使用建议

### 场景 1：实盘交易（QMT 为主）

```python
from easy_xt import get_api

api = get_api()

# 1. 获取实时价格
price = api.get_current_price('000001.SZ')

# 2. 获取五档盘口
order_book = api.get_order_book('000001.SZ')

# 3. 获取Level-2数据（需要权限）
l2_data = api.get_l2_quote('000001.SZ')
```

**优势**：
- ✅ 数据最完整
- ✅ Level-2支持
- ✅ 可直接下单
- ✅ 实时性最好

---

### 场景 2：回测（TDX 为主）

```python
from easy_xt.realtime_data.providers.tdx_provider import TdxDataProvider

tdx = TdxDataProvider()

# 1. 获取历史K线
kline = tdx.get_kline_data('000001.SZ', period='D', count=100)

# 2. 获取历史逐笔（新增）
ticks = tdx.get_history_transaction_data('000001.SZ', date='20240312')

# 3. 获取分时数据
minute = tdx.get_minute_data('000001.SZ', count=240)
```

**优势**：
- ✅ 不依赖QMT终端
- ✅ Tick数据支持（新增）
- ✅ 数据丰富
- ✅ 独立运行

---

### 场景 3：多数据源备份（自动切换）

```python
from easy_xt.realtime_data import UnifiedDataAPI

api = UnifiedDataAPI()

# 自动选择最优数据源
quotes = api.get_realtime_quotes(['000001.SZ', '600000.SH'])

# 优先级：QMT > TDX > 东方财富
```

---

## 🚀 五、下一步优化方向

### 高优先级

1. ✅ **Tick逐笔数据** - 已完成
2. ⭐ **Level-2 数据支持** - 待实现
   ```python
   def get_l2_transaction(self, code: str):
       """获取Level-2逐笔成交"""
       pass
   ```

3. ⭐ **完善分时数据** - 获取全天数据
4. ⭐ **财务数据支持** - 补全数据类型

### 中优先级

5. **缓存机制** - 提高性能
6. **并发优化** - 批量获取
7. **容错切换** - 多数据源自动切换

---

## 📝 六、API 对齐检查表

### QMT DataAPI 方法 vs TdxProvider 方法

| QMT方法 | TdxProvider方法 | 对齐状态 | 说明 |
|---------|----------------|---------|------|
| `get_price()` | `get_kline_data()` | ✅ | 基本对齐 |
| `get_current_price()` | `get_realtime_quotes()` | ✅ | 已对齐 |
| `get_order_book()` | `get_realtime_quotes()` | ✅ | 包含五档 |
| `get_l2_quote()` | ❌ 未实现 | ⚠️ | pytdx支持 |
| `download_data()` | `get_kline_data()` | ✅ | 已对齐 |
| `get_stock_list()` | `get_stock_list()` | ✅ | 新增 |
| `get_trading_dates()` | `get_trading_calendar()` | ⚠️ | 简化实现 |

---

## 🎯 七、总结

### 当前状态

**QMT（实盘）**：
- ✅ 完整的数据支持
- ✅ Level-2深度数据
- ✅ 可直接交易

**TDX（备用）**：
- ✅ 基础数据完整
- ✅ Tick数据支持（新增）
- ✅ 独立运行
- ⚠️ 无Level-2（pytdx支持但未实现）

**东方财富**：
- ✅ HTTP接口易用
- ✅ 热度、板块数据
- ⚠️ 数据类型不完整

### 推荐使用

| 场景 | 推荐数据源 | 原因 |
|------|-----------|------|
| **实盘交易** | QMT | 完整、可直接交易 |
| **回测** | TDX | 数据丰富、独立运行 |
| **高频策略** | QMT+TDX | QMT实时，TDX tick回测 |
| **模拟盘** | TDX | 无需QMT，数据准确 |
| **辅助决策** | 东方财富+同花顺 | 热度、板块数据 |

---

## 📊 数据类型支持度评分

| 数据源 | 实时行情 | 五档 | 分时 | K线 | Tick | 指数 | 板块 | 总分 |
|--------|---------|-----|------|-----|-----|------|------|-----|
| **QMT** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | **45/50** |
| **TDX** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⚠️ | ⭐⭐⭐ | **38/50** |
| **东方财富** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ | ⭐⭐⭐ | ⭐⭐⭐⭐ | **28/50** |
| **同花顺** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⭐⭐⭐⭐ | **10/50** |

---

**结论**：TDX 已基本对齐 QMT 的核心数据类型，Tick 数据已添加！🎉
