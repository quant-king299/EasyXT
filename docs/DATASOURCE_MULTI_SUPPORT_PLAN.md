# DataAPI 多数据源支持方案

> **状态**：待实现
> **更新时间**：2026-03-12
> **问题**：用户没有 QMT 时无法使用 easy_xt

---

## 📋 当前问题

### 用户反馈

```python
from easy_xt import EasyXT

api = EasyXT()
api.init_data()
data = api.get_price('000001.SZ', count=100)
print(data.head())
```

**输出：**
```
⚠️ xtquant.xttrader 导入失败: No module named 'xtquant'
⚠️ 交易服务未连接
```

### 问题分析

1. **DataAPI 依赖 QMT** - 当前实现强制依赖 `xtquant.xtdata`
2. **无降级机制** - QMT 不可用时自动失败，不尝试其他数据源
3. **用户体验差** - 即使安装了 TDX，也无法使用

---

## 💡 解决方案

### 方案 A：修改 DataAPI 支持多数据源（推荐）⭐

**实现思路：**

```python
class DataAPI:
    def __init__(self):
        # 尝试导入多个数据源
        self.xt = self._try_import_qmt()
        self._tdx = TdxDataProvider() if TDX_AVAILABLE else None
        self._eastmoney = EastmoneyDataProvider() if EASTMONEY_AVAILABLE else None

        # 数据源优先级
        self._active_source = None

    def connect(self):
        """自动选择最佳数据源"""
        # 1. 优先使用 QMT
        if self.xt and self._connect_qmt():
            self._active_source = 'qmt'
            return True

        # 2. 降级到 TDX
        if self._tdx and self._connect_tdx():
            self._active_source = 'tdx'
            return True

        # 3. 降级到 Eastmoney
        if self._eastmoney and self._connect_eastmoney():
            self._active_source = 'eastmoney'
            return True

        return False

    def get_price(self, ...):
        """根据 active_source 调用相应方法"""
        if self._active_source == 'qmt':
            return self._get_price_qmt(...)
        elif self._active_source == 'tdx':
            return self._get_price_tdx(...)
        elif self._active_source == 'eastmoney':
            return self._get_price_eastmoney(...)
```

**优点：**
- ✓ 对用户透明，无需修改代码
- ✓ 自动降级，优先使用最佳数据源
- ✓ 支持三种数据源：QMT > TDX > Eastmoney

**缺点：**
- ⚠️ 需要修改大量代码
- ⚠️ 需要统一数据格式
- ⚠️ 可能引入新 bug

**工作量：** 4-6 小时

---

### 方案 B：创建新的 MultiSourceAPI（推荐）⭐⭐⭐

**实现思路：**

```python
class MultiSourceAPI:
    """多数据源 API - 不依赖 QMT"""

    def __init__(self):
        self.tdx = TdxDataProvider()
        self.eastmoney = EastmoneyDataProvider()
        self._active_source = None

    def connect(self):
        """自动选择可用数据源"""
        # 优先 TDX，备用 Eastmoney
        if self.tdx.connect():
            self._active_source = 'tdx'
            return True
        elif self.eastmoney.connect():
            self._active_source = 'eastmoney'
            return True
        return False

    def get_price(self, codes, count=100):
        """获取价格数据"""
        if self._active_source == 'tdx':
            return self.tdx.get_kline_data(codes, count=count)
        else:
            return self.eastmoney.get_kline_data(codes, count=count)

# 使用方式
from easy_xt.multi_source_api import MultiSourceAPI

api = MultiSourceAPI()
api.connect()
data = api.get_price('000001', count=100)
```

**优点：**
- ✓ 不破坏现有 DataAPI
- ✓ 新代码，测试独立
- ✓ 可以逐步完善
- ✓ 适合不想安装 QMT 的用户

**缺点：**
- ⚠️ API 接口可能略有不同
- ⚠️ 需要维护两套 API

**工作量：** 2-3 小时

---

### 方案 C：提供使用指南（临时方案）⭐

**实现思路：**

不修改代码，直接告诉用户如何使用多数据源：

```python
# 方式1：使用 DataAPI（需要 QMT）
from easy_xt import EasyXT
api = EasyXT()
api.init_data()  # 依赖 QMT

# 方式2：直接使用 TDX（无需 QMT）
from easy_xt.realtime_data.providers.tdx_provider import TdxDataProvider

tdx = TdxDataProvider()
data = tdx.get_kline_data('000001', period='D', count=100)

# 方式3：使用 Eastmoney（无需 QMT）
from easy_xt.realtime_data.providers.eastmoney_provider import EastmoneyDataProvider

em = EastmoneyDataProvider()
data = em.get_kline_data('000001', period='D', count=100)
```

**优点：**
- ✓ 无需修改代码
- ✓ 立即可用
- ✓ 用户自由选择

**缺点：**
- ⚠️ API 不统一
- ⚠️ 用户需要学习不同接口

**工作量：** 30 分钟（写文档）

---

## 🎯 推荐实施步骤

### 短期（今天）

1. **创建使用指南文档** - 方案 C
   - 说明 DataAPI 需要 QMT
   - 提供 TDX/Eastmoney 的使用示例
   - 说明如何选择数据源

2. **优化错误提示**
   - 明确告知用户需要安装 QMT
   - 提供替代方案（TDX、Eastmoney）

### 中期（本周）

3. **实现 MultiSourceAPI** - 方案 B
   - 创建新文件：`easy_xt/multi_source_api.py`
   - 支持 TDX + Eastmoney 自动降级
   - 提供统一的 get_price 接口

### 长期（下周）

4. **逐步迁移**
   - 逐步完善 MultiSourceAPI
   - 最终让它成为默认推荐
   - DataAPI 保留给 QMT 用户

---

## 📝 给用户的回复（方案 C）

### 回草内容：

```
关于 "No module named 'xtquant' 警告的问题：

## 问题原因

easy_xt 的 DataAPI 目前依赖 QMT 客户端的 xtquant 模块。
你的机器上没有安装 QMT，所以无法使用。

## 解决方案

### 方案1：安装 QMT（推荐，功能最全）

1. 下载 QMT 迷你版
2. 安装到本地
3. 重新运行代码

**适用场景：** 实盘交易 + 回测

### 方案2：使用多数据源（推荐，无需QMT）

如果你不想安装 QMT，可以直接使用其他数据源：

# 使用通达信数据源（推荐）
from easy_xt.realtime_data.providers.tdx_provider import TdxDataProvider

tdx = TdxDataProvider()
data = tdx.get_kline_data('000001', period='D', count=100)
print(data.head())

# 或使用东方财富数据源
from easy_xt.realtime_data.providers.eastmoney_provider import EastmoneyDataProvider

em = EastmoneyDataProvider()
data = em.get_kline_data('000001', period='D', count=100)
print(data.head())

**适用场景：** 回测、数据分析（无需 QMT）

## 数据源对比

| 数据源 | 需要 QMT | 功能 | 推荐场景 |
|--------|----------|------|---------|
| DataAPI | ✓ 需要 | 最全 | 实盘+回测 |
| TDX | ✗ 不需要 | 完整 | 回测 |
| Eastmoney | ✗ 不需要 | 基础 | 回测 |

## 建议

如果你只是做回测或数据分析，建议使用 TDX 数据源：
- ✓ 无需安装 QMT
- ✓ 数据完整
- ✓ 性能稳定

示例代码已准备好，随时可以使用！
```

---

## 📊 实现优先级

1. **立即可做**（30分钟）
   - ✓ 创建使用指南文档
   - ✓ 提供 TDX/Eastmoney 使用示例

2. **本周完成**（2-3小时）
   - ⭐ 实现 MultiSourceAPI
   - ⭐ 支持自动降级

3. **下周优化**（按需）
   - 逐步完善 MultiSourceAPI
   - 考虑重构 DataAPI

---

**文档版本**：v1.0
**最后更新**：2026-03-12
**状态**：待实现
