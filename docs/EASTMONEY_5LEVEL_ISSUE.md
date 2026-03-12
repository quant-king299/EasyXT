# 东方财富五档盘口数据问题说明

> **问题报告时间**：2026-03-12
> **状态**：已确认，待修复

---

## 📋 问题描述

有用户反馈：**东方财富EastmoneyDataProvider获取五档数据有问题，现有的bid1、ask1及对应的bid1_vol和ask1_vol也有问题**

---

## 🔍 问题分析

### 1. 通达信 TDX - ✅ 已修复

**问题：** pytdx返回的五档成交量单位是"手"，需要乘以100转换为"股"

**修复状态：** ✅ 已完成

**代码：**
```python
# 修复后
'bid1_vol': int(quote.get('bid1_vol', 0)) * 100,
'bid2_vol': int(quote.get('bid2_vol', 0)) * 100,
'ask1_vol': int(quote.get('ask1_vol', 0)) * 100,
'ask2_vol': int(quote.get('ask2_vol', 0)) * 100,
```

**测试结果：** ✅ 通过

---

### 2. 东方财富 Eastmoney - ⚠️ API字段映射问题

#### 问题1：API端点选择不当

**当前使用的API：**
```
https://push2.eastmoney.com/api/qt/ulist.np/get
```

**问题：** 该端点返回的字段映射不明确，数据异常

**测试结果：**
```
买一: 价格=10.94(正确) 量=-61.05(❌ 负数异常)
卖一: 价格=10.95(正确) 量=430970(可能正确)
买二: 价格=323936(❌ 数值异常) 量=19405600653(❌ 数值过大)
卖二: 价格=42789(❌ 数值异常) 量=100668000000(❌ 数值过大)
```

#### 问题2：字段映射不确定

**假设的字段映射（未验证）：**
```python
# 这个映射可能不正确
f31: 买一价
f32: 卖一价
f33: 买一量  # ❌ 实际返回负数
f34: 卖一量
f35: 买二价  # ❌ 实际返回超大数值
f36: 卖二价
...
```

#### 可能的原因：

1. **API端点错误** - `ulist.np/get` 可能不是获取五档盘口的正确端点
2. **字段编号错误** - 东方财富API的字段编号可能随时间变化
3. **非交易时间** - 盘后数据可能不准确
4. **需要额外参数** - 可能需要特定的请求参数才能获取正确数据

---

## 💡 解决方案

### 方案A：使用腾讯API（推荐）⭐

腾讯API提供稳定的五档盘口数据：

```python
def get_realtime_quotes_from_tencent(self, codes: List[str]):
    """使用腾讯API获取五档盘口"""
    import requests

    results = []
    for code in codes:
        # 转换代码格式
        if code.startswith('6'):
            symbol = f'sh{code}'
        else:
            symbol = f'sz{code}'

        url = f'https://qt.gtimg.cn/q={symbol}'
        response = requests.get(url)

        if response.status_code == 200:
            # 解析腾讯API返回的数据
            # 格式: v_sh600000="1~浦发银行~600000~..."
            data = response.text
            # ... 解析逻辑

    return results
```

**优点：**
- ✅ 稳定可靠
- ✅ 数据准确
- ✅ 五档完整

**缺点：**
- ⚠️ HTTP接口，可能被限流

---

### 方案B：使用新浪API

新浪API也提供五档数据：

```python
url = f'https://hq.sinajs.cn/list={symbol}'
```

**优点：**
- ✅ 稳定
- ✅ 五档完整

**缺点：**
- ⚠️ HTTP接口
- ⚠️ 可能被限流

---

### 方案C：继续调试东方财富API

**需要的步骤：**
1. 找到正确的API端点
2. 确认字段编号
3. 验证数据格式

**可能的API端点：**
```
https://push2.eastmoney.com/api/qt/stock/get
https://quote.eastmoney.com/api/v1/get
```

---

### 方案D：降级使用（当前临时方案）

**建议：**
- 东方财富Provider标记为**不提供五档数据**
- 专注于其优势功能：
  - ✅ K线数据
  - ✅ 热度排行
  - ✅ 板块数据

**实现：**
```python
def get_realtime_quotes(self, codes: List[str]):
    """获取实时行情（仅基础数据，不含五档）"""
    # ... 只返回基础行情数据
    return {
        'symbol': code,
        'price': price,
        'change': change,
        # 不返回五档盘口数据
        # bid1-5, ask1-5, bid1_vol-5, ask1_vol-5 全部设为0或None
    }
```

---

## 🎯 推荐回复用户

### 回复内容：

```
感谢反馈！关于五档盘口数据问题：

## 已修复
✅ 通达信(TDX)五档数据单位问题已修复
- pytdx返回的单位是"手"，现已转换为"股"（×100）
- bid1_vol到bid5_vol, ask1_vol到ask5_vol已全部修复

## 东方财富问题
⚠️ 东方财富API的五档盘口字段映射存在问题
- 当前使用的API端点返回的数据异常
- 正在寻找正确的API端点或替代方案

## 当前推荐
建议使用以下数据源获取五档盘口：
1. QMT（实盘） - 最完整、最准确
2. TDX（备用） - 已修复，数据准确
3. 东方财富 - 暂时不推荐用于五档盘口

东方财富继续用于其优势功能：
- ✅ K线数据
- ✅ 热度排行
- ✅ 板块数据

我们正在修复东方财富的五档数据问题，预计下个版本更新。
```

---

## 📝 后续计划

1. **短期（1-2天）**
   - 测试腾讯API的五档数据
   - 如果可行，集成到EastmoneyDataProvider

2. **中期（1周）**
   - 寻找东方财富正确的API端点
   - 或使用多个API源互补

3. **长期**
   - 统一五档数据接口
   - 提供数据源自动切换

---

## 🧪 测试用例

```python
# 验证五档数据正确性的测试代码
def test_5level_data():
    """测试五档盘口数据"""

    # 1. 价格应该在合理范围内
    assert 0 < bid1 < price * 1.1
    assert price * 0.9 < ask1 < price * 1.1

    # 2. 买一价 < 卖一价
    assert bid1 < ask1

    # 3. 买价递减
    assert bid1 >= bid2 >= bid3 >= bid4 >= bid5

    # 4. 卖价递增
    assert ask1 <= ask2 <= ask3 <= ask4 <= ask5

    # 5. 成交量应该为正数（且不为0或负数）
    assert bid1_vol > 0
    assert ask1_vol > 0

    # 6. 成交量应该在合理范围内
    # 正常单笔挂单量：100 - 1000000 股
    assert 100 <= bid1_vol <= 10000000
    assert 100 <= ask1_vol <= 10000000

    print("✅ 五档数据验证通过")
```

---

**文档版本**：v1.0
**最后更新**：2026-03-12
**状态**：待修复
