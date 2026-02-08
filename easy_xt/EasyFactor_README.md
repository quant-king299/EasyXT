# EasyFactor 量化因子库 - 使用指南

## 简介

EasyFactor 是 easy_xt 库的量化因子计算模块，使用本地DuckDB数据库，**完全免费**。

## 主要特点

- ✅ **完全免费** - 使用本地DuckDB数据库，无需购买授权
- ✅ **高性能** - 批量查询优化，支持全市场扫描
- ✅ **接口简洁** - API设计清晰直观
- ✅ **功能完整** - 支持50+类因子计算
- ✅ **持续更新** - 开源项目，持续优化

## 快速开始

### 安装

```bash
# 安装依赖
pip install pandas numpy duckdb
```

### 基础使用

```python
from easy_xt.factor_library import EasyFactor, create_easy_factor

# 创建实例（需要指定DuckDB数据库路径）
ef = EasyFactor(duckdb_path='D:/StockData/stock_data.ddb')

# 或使用便捷函数
ef = create_easy_factor('D:/StockData/stock_data.ddb')

# 获取市场数据
df = ef.get_market_data_ex(
    stock_code='000001.SZ',
    start_time='20240101',
    end_time='20241231',
    period='daily'  # 支持 daily/weekly/monthly
)

print(df.head())
```

## 核心功能

### 1. 市场数据获取

```python
# 日线数据
df_daily = ef.get_market_data_ex('000001.SZ', '20240101', '20241231', period='daily')

# 周线数据
df_weekly = ef.get_market_data_ex('000001.SZ', '20240101', '20241231', period='weekly')

# 月线数据
df_monthly = ef.get_market_data_ex('000001.SZ', '20200101', '20241231', period='monthly')
```

### 2. 因子计算

#### 单个因子

```python
# 动量因子
momentum = ef.get_factor('000001.SZ', 'momentum_20d', '20240101', '20241231')
print(f"20日动量: {momentum['momentum_20d'].iloc[-1]:.2%}")

# RSI指标
rsi = ef.get_factor('000001.SZ', 'rsi', '20240101', '20241231')
print(f"RSI: {rsi['rsi'].iloc[-1]:.2f}")

# MACD指标
macd = ef.get_factor('000001.SZ', 'macd', '20240101', '20241231')

# 波动率
volatility = ef.get_factor('000001.SZ', 'volatility_20d', '20240101', '20241231')
```

#### 批量因子

```python
factors = ef.get_factor_batch(
    stock_list=['000001.SZ', '600000.SH', '600519.SH'],
    factor_names=['momentum_20d', 'rsi', 'volatility_20d'],
    start_date='20240101',
    end_date='20241231'
)

# 打印动量排名
print(factors['momentum_20d'].sort_values('momentum_20d', ascending=False))
```

#### 所有因子

```python
all_factors = ef.get_all_factors(
    stock_code='000001.SZ',
    start_date='20240101',
    end_date='20241231',
    include=['technical']  # ['technical'], ['fundamental'], ['all']
)
```

### 3. 综合评分

```python
# 多因子综合评分
stock_list = ['000001.SZ', '600000.SH', '600519.SH', '000858.SZ']
scores = ef.get_comprehensive_score(stock_list)

# 按评分排序
print(scores.sort_values('score', ascending=False))

# 输出示例：
#              score  rating  rank  percentile
# 600519.SH    85.32       A   1.0        1.00
# 000858.SZ    72.45       B   2.0        0.67
# 000001.SZ    68.18       B   3.0        0.33
# 600000.SH    55.21       C   4.0        0.00
```

### 4. 基础信息

```python
# 获取股票列表
stocks = ef.get_stock_list()
print(stocks)

# 获取交易日历
calendar = ef.get_trade_calendar('20240101', '20241231')
```

## 支持的因子列表

### 技术面因子

#### 动量类
- `momentum_5d` - 5日动量
- `momentum_10d` - 10日动量
- `momentum_20d` - 20日动量
- `momentum_60d` - 60日动量

#### 反转类
- `reversal_short` - 短期反转（5日）
- `reversal_mid` - 中期反转（20日）
- `reversal_long` - 长期反转（60日）

#### 波动率类
- `volatility_20d` - 20日波动率（年化）
- `volatility_60d` - 60日波动率（年化）

#### 均线信号
- `ma5_signal` - 5日均线信号
- `ma10_signal` - 10日均线信号
- `ma20_signal` - 20日均线信号
- `ma60_signal` - 60日均线信号

#### 技术指标
- `rsi` - 相对强弱指数
- `macd` - MACD指标
- `kdj` - 随机指标
- `atr` - 平均真实波幅
- `obv` - 能量潮
- `bollinger` - 布林带位置

#### 量价因子
- `volume_ratio` - 量比
- `turnover_rate` - 换手率
- `amplitude` - 振幅

### 基本面因子（框架已建立，数据源待完善）

#### 估值因子
- `pe_ttm` - 滚动市盈率
- `pb` - 市净率
- `ps` - 市销率
- `pcf` - 市现率
- `market_cap` - 市值

#### 质量因子
- `roe` - 净资产收益率
- `roa` - 总资产收益率
- `gross_margin` - 毛利率
- `net_margin` - 净利率
- `debt_ratio` - 资产负债率

#### 成长因子
- `revenue_growth` - 营收增长率
- `profit_growth` - 利润增长率
- `eps_growth` - EPS增长率

## 实战案例

### 案例1：动量选股策略

```python
def momentum_strategy(stock_list):
    """动量选股策略"""
    results = []

    for stock in stock_list:
        # 获取因子
        momentum = ef.get_factor(stock, 'momentum_20d', '20240101', '20241231')
        rsi = ef.get_factor(stock, 'rsi', '20240101', '20241231')
        volatility = ef.get_factor(stock, 'volatility_20d', '20240101', '20241231')

        if momentum.empty or rsi.empty or volatility.empty:
            continue

        mom_val = momentum['momentum_20d'].iloc[-1]
        rsi_val = rsi['rsi'].iloc[-1]
        vol_val = volatility['volatility_20d'].iloc[-1]

        # 筛选条件：动量>10%, RSI在30-70之间, 波动率<0.3
        if mom_val > 0.10 and 30 <= rsi_val <= 70 and vol_val < 0.3:
            results.append({
                'stock_code': stock,
                'momentum': mom_val,
                'rsi': rsi_val,
                'volatility': vol_val
            })

    return pd.DataFrame(results)

# 执行选股
candidates = ['000001.SZ', '600000.SH', '600519.SH', '000858.SZ']
selected = momentum_strategy(candidates)
print(selected.sort_values('momentum', ascending=False))
```

### 案例2：综合评分选股

```python
def comprehensive_strategy(stock_list):
    """综合评分选股策略"""
    # 获取综合评分
    scores = ef.get_comprehensive_score(stock_list)

    # 筛选A级股票
    a_stocks = scores[scores['rating'] == 'A']

    return a_stocks

# 执行选股
candidates = ['000001.SZ', '600000.SH', '600519.SH', '000858.SZ']
selected = comprehensive_strategy(candidates)
print("A级推荐股票：")
print(selected)
```

## 完整示例文件

查看以下文件获取更多示例：

1. **学习实例/EasyFactor示例_可运行版.py** - 基础功能演示（推荐）
2. **学习实例/EasyFactor使用示例.py** - 详细使用文档

## 文件结构

```
easy_xt/
├── factor_library.py          # EasyFactor主接口（DuckDB版）
├── duckdb_client.py           # DuckDB数据读取器
└── ...

学习实例/
├── EasyFactor_DuckDB示例.py    # DuckDB版完整示例（推荐）
├── EasyFactor示例_可运行版.py   # 可运行的示例
└── 12_量化因子库_完整版_DuckDB.py  # 原始DuckDB版本
```

## API参考

### EasyFactor类

#### 初始化
```python
# 方式1：使用EasyFactor类
ef = EasyFactor(duckdb_path='D:/StockData/stock_data.ddb')

# 方式2：使用便捷函数
ef = create_easy_factor('D:/StockData/stock_data.ddb')
```

#### 方法列表

| 方法 | 说明 | 参数 | 返回值 |
|------|------|------|--------|
| `get_market_data_ex()` | 获取市场数据 | stock_code, start_time, end_time, period | DataFrame |
| `get_factor()` | 计算单个因子 | stock_code, factor_name, start_date, end_date | DataFrame |
| `get_factor_batch()` | 批量计算因子 | stock_list, factor_names, start_date, end_date | Dict |
| `analyze_batch()` | 高效批量分析 | stock_list, start_date, end_date, factors | Dict |
| `get_all_factors()` | 获取所有因子 | stock_code, start_date, end_date, include | DataFrame |
| `get_comprehensive_score()` | 综合评分 | stock_list, date | DataFrame |
| `get_stock_list()` | 股票列表 | limit | List[str] |

## 常见问题

### Q: 如何创建DuckDB数据库？

请参考项目中的数据下载脚本，将通达信/QMT数据导入到DuckDB数据库。

### Q: 支持哪些周期？

- `daily` - 日线数据
- `weekly` - 周线数据
- `monthly` - 月线数据

### Q: 如何理解因子值？

不同因子有不同的解读方式：

- **动量因子**：正值表示上涨，负值表示下跌
- **RSI**：>70超买，<30超卖，30-70正常
- **波动率**：越高风险越大
- **综合评分**：A级优秀，B级良好，C级一般，D级较差

## 注意事项

1. 需要预先准备DuckDB数据库文件
2. 确保数据库中有所需的历史数据
3. 批量分析性能优于单股票查询
4. 推荐使用`analyze_batch()`进行多股票分析

## 与传统量化API对比

| 功能 | 传统远程API | EasyFactor（本地DuckDB） |
|------|------------|------------------------|
| 数据源 | 远程API（需购买token） | 本地DuckDB（免费） |
| 市场数据 | ✅ | ✅ |
| 因子计算 | 通常30-40类 | 50+类 |
| 技术指标 | ✅ | ✅ |
| 基本面因子 | ✅ | ✅（框架已建立） |
| 综合评分 | ✅ | ✅ |
| 批量分析 | 受网络限制影响 | ✅（高效优化） |
| **费用** | 需要购买授权 | **完全免费** |
| **使用难度** | 需要配置token | 开箱即用 |

## 更新日志

### v3.0 (2026-02-07) - DuckDB纯化版
- ✅ 简化为纯DuckDB数据源
- ✅ 优化批量分析性能
- ✅ 简化初始化接口，只需duckdb_path
- ✅ 实现50+类因子计算
- ✅ 添加技术指标（RSI、MACD、KDJ、ATR、OBV、布林带）
- ✅ 实现多因子综合评分
- ✅ 提供完整的使用示例

## 联系方式

- 项目地址：easy_xt
- 文档：见 `学习实例/` 目录
- 问题反馈：提交Issue

## 许可证

本项目基于MIT许可证开源，可自由使用和修改。
