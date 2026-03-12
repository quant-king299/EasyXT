# 多数据源自动降级测试指南

> **更新时间**：2026-03-12
> **状态**：已实现，待验证

---

## ✅ 已实现功能

### 1. 多数据源检测

```python
[OK] QMT (xtquant.xtdata) imported successfully
[OK] TDX (通达信) provider available
[OK] Eastmoney (东方财富) provider available
```

### 2. 自动降级逻辑

```
优先级:
1. QMT (xtquant) - 优先使用（如果可用）
2. TDX (通达信) - QMT不可用时自动降级
3. Eastmoney (东方财富) - TDX不可用时继续降级
```

### 3. 连接流程

```
用户调用 init_data()
    ↓
尝试连接 QMT
    ↓ 成功 → 使用 QMT 作为数据源
    ↓ 失败
    ↓
尝试连接 TDX
    ↓ 成功 → 使用 TDX 作为数据源
    ↓ 失败
    ↓
尝试连接 Eastmoney
    ↓ 成功 → 使用 Eastmoney 作为数据源
    ↓ 失败
    ↓
所有数据源都失败 → 报错
```

---

## 🧪 测试场景

### 场景1：有 QMT（当前环境）✅ 已验证

**测试代码：**
```python
from easy_xt import EasyXT

api = EasyXT()
api.init_data()
data = api.get_price('000001.SZ', count=3)

print(f"数据源: {api.data.get_active_source()}")
print(f"数据量: {len(data)} 行")
```

**输出：**
```
[Connecting to data source...]
  Trying QMT (xtquant)...
[OK] Using QMT (xtquant) as data source
数据源: qmt
数据量: 3 行
```

**测试结果：** ✅ 通过

---

### 场景2：没有 QMT，有 TDX（待用户验证）

**环境要求：**
- ✅ 没有安装 QMT
- ✅ 安装了 pytdx（`pip install pytdx`）

**测试代码：**（同场景1）

**预期输出：**
```
[INFO] QMT (xtquant.xtdata) not available
[OK] TDX (通达信) provider available
[OK] Eastmoney (东方财富) provider available

[Connecting to data source...]
  Trying QMT (xtquant)...
  [WARN] QMT connection failed
  Trying TDX (通达信)...
[OK] Using TDX (通达信) as data source

数据源: tdx
数据量: X 行
```

**验证步骤：**
1. 在一台没有 QMT 的机器上运行
2. 确保安装了 pytdx：`pip install pytdx`
3. 运行测试代码
4. 确认输出显示 "Using TDX"
5. 确认 get_price 返回了数据

---

### 场景3：没有 QMT，没有 TDX，有 Eastmoney（待用户验证）

**环境要求：**
- ✅ 没有安装 QMT
- ✅ 没有安装 pytdx
- ✅ 有 requests 库

**预期输出：**
```
[INFO] QMT (xtquant.xtdata) not available
[INFO] TDX provider not available
[OK] Eastmoney (东方财富) provider available

[Connecting to data source...]
  Trying QMT (xtquant)...
  [WARN] QMT connection failed
  Trying TDX (通达信)...
  [INFO] TDX provider not available
  Trying Eastmoney (东方财富)...
[OK] Using Eastmoney (东方财富) as data source

数据源: eastmoney
数据量: X 行
```

---

## 🎯 核心实现

### 修改的文件

1. **easy_xt/data_api.py**
   - 添加 TDX、Eastmoney 导入
   - 添加多数据源检测
   - 修改 connect() 方法，实现自动降级
   - 修改 get_price() 方法，根据 active_source 调用对应方法

2. **easy_xt/api.py**
   - TradeAPI 改为延迟加载
   - 避免只使用数据功能的用户看到交易警告

### 关键代码

```python
# 多数据源导入
xt_available = False
try:
    import xtquant.xtdata as xt
    xt_available = True
except ImportError:
    pass

TDX_AVAILABLE = False
try:
    from .realtime_data.providers.tdx_provider import TdxDataProvider
    TDX_AVAILABLE = True
except ImportError:
    pass

# 自动降级连接
def connect(self):
    # 优先级1: QMT
    if xt_available and self._connect_qmt():
        self._active_source = 'qmt'
        return True

    # 优先级2: TDX
    if TDX_AVAILABLE and self._connect_tdx():
        self._active_source = 'tdx'
        return True

    # 优先级3: Eastmoney
    if EASTMONEY_AVAILABLE and self._connect_eastmoney():
        self._active_source = 'eastmoney'
        return True

    return False
```

---

## 📝 使用说明

### 对用户完全透明

用户代码无需修改：

```python
from easy_xt import EasyXT

api = EasyXT()
api.init_data()  # 自动选择最佳数据源
data = api.get_price('000001.SZ', count=100)  # 自动使用选择的数据源

# 无论有 QMT 还是没有，代码都一样
```

### 查看当前使用的数据源

```python
print(f"当前数据源: {api.data.get_active_source()}")
# 输出: qmt 或 tdx 或 eastmoney
```

---

## 🐛 已知问题

### 1. TDX 和 Eastmoney 的 get_price 实现不完整

**当前状态：**
- ✓ QMT 的 get_price 完整实现（原有逻辑）
- ⚠️ TDX 的 get_price 需要完整实现（当前是简化版）
- ⚠️ Eastmoney 的 get_price 需要完整实现

**影响：**
- QMT：所有功能都支持
- TDX/Eastmoney：只支持基础的 get_price
  - ✓ 支持周期：1d, 1w
  - ⚠️ 支持字段：open, high, low, close, volume, amount
  - ⚠️ 不支持：分钟数据（1m, 5m等）

**解决方案：**
- 短期：建议优先使用 QMT（功能最全）
- 长期：逐步完善 TDX/Eastmoney 的实现

---

## 📊 测试清单

- [x] 场景1：有 QMT - **已验证** ✓
- [ ] 场景2：没有 QMT，有 TDX - **待用户验证**
- [ ] 场景3：没有 QMT，没有 TDX，有 Eastmoney - **待用户验证**
- [ ] 场景4：所有数据源都不可用 - **待用户验证**

---

## 💡 给用户的建议

### 如果你想测试多数据源降级

**方法1：在没有 QMT 的机器上测试**
1. 准备一台没有安装 QMT 的电脑
2. 安装必要的依赖：`pip install pytdx pandas`
3. 运行测试代码
4. 观察是否自动降级到 TDX

**方法2：临时重命名 xtquant 模块**
```python
# 临时模拟没有 QMT 的环境
import sys
import xtquant as xt_backup

# 临时隐藏 xtquant
sys.modules['xtquant'] = None

# 测试自动降级
from easy_xt import EasyXT
api = EasyXT()
api.init_data()  # 应该自动使用 TDX

# 恢复 xtquant
sys.modules['xtquant'] = xt_backup
```

---

## 🎉 总结

### 已实现功能 ✅

1. ✓ 多数据源检测
2. ✓ 自动降级逻辑
3. ✓ QMT 数据源正常工作
4. ✓ 延迟加载 TradeAPI
5. ✓ 对用户透明，无需修改代码

### 待完善 ⚠️

1. ⚠️ TDX/Eastmoney 的 get_price 完整实现
2. ⚠️ 支持更多周期（分钟数据）
3. ⚠️ 支持更多字段（复权等）
4. ⚠️ 在无 QMT 环境下的实际测试

### 推荐使用

| 场景 | 推荐数据源 | 原因 |
|------|-----------|------|
| 有 QMT | QMT (xtquant) | 功能最全 |
| 没有 QMT | TDX (通达信) | 数据完整，无需安装 |
| 回测/模拟 | TDX 或 Eastmoney | 无需 QMT |

---

**文档版本**：v1.0
**最后更新**：2026-03-12
**测试状态**：QMT场景已验证 ✓，其他场景待验证
