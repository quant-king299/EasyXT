# QMT版本说明

## 📖 概述

QMT（迅投量化交易平台）有两个版本，**本项目主要针对 miniQMT 进行设计和测试**。

> ⚠️ **重要**：虽然项目理论上可能支持完整版QMT，但所有测试和示例都基于miniQMT环境。推荐使用miniQMT以获得最佳体验。

---

## 🔍 两个版本的区别

### 1️⃣ 完整版QMT

**特点：**
- ✅ 包含完整的图形用户界面（GUI）
- ✅ 提供可视化交易界面
- ✅ 支持手动交易和策略交易
- ✅ 功能全面，适合专业交易员

**适用场景：**
- 需要手动交易的用户
- 需要可视化监控的用户
- 专业交易机构

**安装方式：**
- 需要联系券商客户经理申请
- 通常需要满足一定的资金门槛

---

### 2️⃣ miniQMT（本项目使用的版本）

**特点：**
- ✅ 轻量级API版本
- ✅ 无GUI界面，纯API调用
- ✅ 部署简单，占用资源少
- ✅ 适合服务器环境运行

**适用场景：**
- 量化策略自动交易
- 服务器部署
- 程序化交易
- 回测和数据分析

**安装方式：**
- 某些券商提供免费版本
- 通常与QMT客户端配套使用

---

## 🔧 环境配置区别

### 完整版QMT

```bash
# 典型安装路径
C:\QMT\userdata
```

**配置文件：**
- `userdata_mini/config/` - 配置目录
- 需要启动QMT客户端
- 通过GUI界面登录账户

### miniQMT（本项目）

```bash
# 典型安装路径
C:\miniQMT\userdata_mini
```

**配置文件：**
- `userdata_mini/config/` - 配置目录
- 无需启动GUI
- 通过API登录账户

---

## 💻 API使用对比

### 代码示例

**两个版本的API调用方式基本一致：**

```python
from xtquant import xtdata, xttrader

# 1. 连接交易账户
connect_result = xttrader.connect(
    path='C:/QMT/userdata',  # 或 miniQMT 的路径
    session_id=123456
)

# 2. 获取行情数据
data = xtdata.get_market_data(
    stock_list=['000001.SZ'],
    period='1d',
    start_time='20240101',
    end_time='20240131'
)

# 3. 下单交易
order_result = xttrader.order_stock(
    account='账户ID',
    stock_code='000001.SZ',
    order_type='buy',
    volume=100,
    price_type='limit'
)
```

**唯一区别：**
- `path` 参数指向不同的目录
- 完整版QMT指向 `userdata`
- miniQMT指向 `userdata_mini`

---

## 📋 如何选择版本？

### 使用完整版QMT，如果：
- ✅ 需要GUI界面手动操作
- ✅ 需要实时可视化监控
- ✅ 习惯使用传统交易软件
- ⚠️ 但可能需要自己解决与EasyXT的兼容性问题

### 使用miniQMT（✅ 强烈推荐本项目用户），如果：
- ✅ 使用EasyXT项目自动交易
- ✅ 在服务器/云环境运行
- ✅ 追求轻量级部署
- ✅ 需要稳定可靠的API调用
- ✅ 希望直接运行项目示例代码无需修改

---

## 🚀 EasyXT项目兼容性

### ⚠️ 重要说明
**本项目主要针对 miniQMT 进行设计和测试**，推荐使用 miniQMT 环境。

### 支持情况

| 版本 | 支持程度 | 说明 |
|------|---------|------|
| **miniQMT** | ✅ 完美支持 | 主要设计和测试环境 |
| **完整版QMT** | ⚠️ 理论支持 | 理论上可以使用，但未经过充分测试 |

**为什么推荐miniQMT？**
- ✅ 轻量级，资源占用少
- ✅ 部署简单，适合服务器运行
- ✅ API调用更稳定
- ✅ 项目所有示例都基于miniQMT

### 配置示例

```python
from easy_xt import get_api

# 推荐使用：miniQMT
api = get_api()
api.init_trade(
    qmt_path='C:/miniQMT/userdata_mini'  # miniQMT路径
)

# 如果使用完整版QMT（未充分测试）
api = get_api()
api.init_trade(
    qmt_path='C:/QMT/userdata'  # 完整版QMT路径
)
```

**注意：** 使用完整版QMT时，可能需要手动配置路径，并自行测试兼容性。

---

## 📚 相关文档

- [EasyXT安装指南](../README.md)
- [疑难问题解答](../TROUBLESHOOTING.md)
- [QMT官方文档](https://www.gtja.com/)

---

## 💡 常见问题

### Q1: 我应该用哪个版本？

**A:** 对于EasyXT项目用户：
- ✅ **强烈推荐：miniQMT**（项目主要测试环境）
- ⚠️ 完整版QMT：理论上可以使用，但可能遇到兼容性问题
- 如果需要完整版QMT的GUI界面，建议同时安装两个版本：
  - 使用完整版QMT手动查看行情
  - 使用miniQMT运行EasyXT自动交易策略

### Q2: 可以在同一个电脑安装两个版本吗？

**A:** 可以，但建议：
- 使用不同的安装目录
- 避免端口冲突
- 不要同时运行

### Q3: 如何获取miniQMT？

**A:**
1. 联系你的券商客户经理
2. 询问是否有miniQMT版本
3. 部分券商提供免费申请渠道

### Q4: miniQMT功能完整吗？

**A:** 核心功能完整！
- ✅ 行情数据获取
- ✅ 账户查询
- ✅ 下单交易
- ✅ 持仓管理
- ❌ 无GUI界面（这是特点，不是缺陷）

---

**最后更新：** 2026-03-08
