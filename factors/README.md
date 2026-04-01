# factors 统一因子库

完整的量化因子计算、分析和管理库。

## 📦 目录结构

```
factors/
├── __init__.py              # 统一接口（向后兼容）
├── pricing/                 # 定价因子模块
│   ├── fama_french.py      # Fama-French三因子/四因子
│   ├── beta_calc.py        # Beta系数计算
│   └── residuals.py        # 残差计算（待完善）
├── analysis/                # 因子分析模块
│   ├── ic_analyzer.py      # IC/IR分析
│   ├── group_backtest.py   # 分组回测
│   ├── performance.py      # 绩效评估（待完善）
│   └── visualization.py    # 可视化（待完善）
└── custom/                  # 自定义因子模块
    ├── small_cap_quality.py # 小市值质量因子
    ├── spec_vol.py         # 特质波动率（待完善）
    └── week_effect.py      # 周内效应（待完善）
```

## 🎯 核心功能

### 1. 定价因子（Pricing Factors）

基于Fama-French模型的标准定价因子。

**使用示例**：

```python
from factors.pricing import FamaFrenchCalculator

# 创建计算器
calc = FamaFrenchCalculator(data_manager)

# 计算三因子
factors = calc.calculate_ff3_factors('2024-01-15')
# 返回: {'MKT': 0.0012, 'SMB': 0.0008, 'HML': -0.0005}

# 计算四因子（增加动量因子）
factors = calc.calculate_ff4_factors('2024-01-15')
```

### 2. Beta系数计算

计算个股对定价因子的敏感度。

```python
from factors.pricing import BetaCalculator

calc = BetaCalculator(data_manager)

# 计算单只股票的Beta
beta = calc.calculate_stock_beta('000001.SZ', '2024-01-15', window=60)
# 返回: {'beta_mkt': 1.2, 'beta_smb': 0.5, 'beta_hml': -0.3, ...}

# 批量计算
beta_df = calc.batch_calculate_beta(stock_list, '2024-01-15')
```

### 3. IC/IR分析

评估因子预测能力的核心工具。

```python
from factors.analysis import ICAnalyzer

analyzer = ICAnalyzer()

# 计算Rank IC（推荐）
ic_series = analyzer.calculate_rank_ic(factor_df, return_df)

# 计算IC统计
ic_stats = analyzer.calculate_ic_statistics(ic_series)
print(f"IC均值: {ic_stats['ic_mean']:.4f}")
print(f"IR: {ic_stats['ir']:.4f}")

# 计算IC半衰期
half_life = analyzer.ic_half_life(ic_series)
print(f"IC半衰期: {half_life['half_life']:.0f}天")
```

**IC评价标准**：
- `|IC| > 0.05` : 强预测能力
- `|IC| > 0.03` : 较强预测能力
- `IR > 1.0` : 优秀
- `IR > 0.5` : 良好

### 4. 分组回测

检验因子单调性的标准方法。

```python
from factors.analysis import GroupBacktester

backtester = GroupBacktester(
    commission=0.00025,  # 万2.5手续费
    slippage=0.001       # 千一滑点
)

# 运行分组回测
result = backtester.run_group_backtest(
    factor_data=factor_df,
    price_data=price_df,
    n_groups=10,
    freq='monthly'
)

# 查看多空策略表现
print(result.summary['long_short'])

# 检验单调性
monotonicity = result.get_monotonicity_test()
print(f"单调性: {monotonicity['is_monotonic']}")
print(f"趋势: {monotonicity['trend']}")
```

### 5. 小市值质量因子

经典的多因子选股策略。

```python
from factors.custom import SmallCapQualityFactor

factor = SmallCapQualityFactor()

# 计算单日因子
factor_df = factor.calculate('2024-01-15', data_manager)

# 因子逻辑：
# 1. 过滤：剔除创业板、科创板、ST、高价股
# 2. 筛选：ROE > 15% 且 ROA > 10%
# 3. 排序：因子值 = -(rank_mv + rank_pb) / 2
# 4. 选股：因子值最小的前20只股票
```

## 🔄 向后兼容

现有代码无需修改，可以直接使用：

```python
# 仍然可以从easy_xt导入（向后兼容）
from easy_xt.factor_library import EasyFactor
from easy_xt.fundamental_enhanced import FundamentalAnalyzerEnhanced

# 或者从factors导入（推荐）
from factors import EasyFactor, FundamentalAnalyzerEnhanced
```

## 📊 因子列表

### 技术面因子（16个）
- 动量：momentum_5d, momentum_10d, momentum_20d, momentum_60d
- 波动率：volatility_20d, volatility_60d, volatility_120d
- 技术指标：rsi, macd, kdj, atr, obv, bollinger
- 量价：volume_ratio, turnover_rate, amplitude

### 基本面因子（14个）
- 估值：price_to_ma20, price_to_ma60, price_percentile
- 动量：momentum_20d, momentum_60d, rsi_14
- 质量：price_cv_60d, trend_strength_60d
- 流动性：avg_volume_5d, avg_volume_20d, turnover_5d

### 定价因子（9个）
- FF三因子：MKT, SMB, HML
- FF四因子：+ UMD
- Beta系数：beta_mkt, beta_smb, beta_hml
- 其他：residual, spec_vol

### 自定义因子（2个）
- 小市值质量因子：f1_small_cap_quality
- 特质波动率：spec_vol（待完善）

## 🚀 快速开始

### 安装依赖

```bash
pip install pandas numpy scipy statsmodels duckdb
```

### 测试模块

```bash
python test_factors.py
```

### 使用示例

```python
import pandas as pd
from factors import FamaFrenchCalculator, ICAnalyzer, GroupBacktester

# 1. 计算定价因子
ff_calc = FamaFrenchCalculator(data_manager)
factors = ff_calc.calculate_ff3_factors('2024-01-15')

# 2. 评估因子预测能力
ic_analyzer = ICAnalyzer()
ic_series = ic_analyzer.calculate_rank_ic(factor_df, return_df)
ic_stats = ic_analyzer.calculate_ic_statistics(ic_series)

# 3. 分组回测
backtester = GroupBacktester(commission=0.00025)
result = backtester.run_group_backtest(factor_df, price_df)

# 4. 查看结果
print(f"IC均值: {ic_stats['ic_mean']:.4f}")
print(f"IR: {ic_stats['ir']:.4f}")
print(f"多空年化收益: {result.summary['long_short']['annual_return']:.2%}")
```

## 📖 参考资料

- [Fama-French三因子模型](https://www.duke.edu/~charvey/Teaching/BA453_2006/Fama_French.pdf)
- [IC分析原理](https://www.investopedia.com/terms/i/informationcoefficient.asp)
- [分组回测方法](https://www.cfainstitute.org/)

## 🔧 开发计划

### 已完成 ✅
- [x] Fama-French三因子/四因子计算
- [x] Beta系数计算
- [x] IC/IR分析
- [x] 分组回测
- [x] 小市值质量因子
- [x] 向后兼容easy_xt因子

### 待完善 🚧
- [ ] 残差收益率计算
- [ ] 特质波动率因子
- [ ] 完整绩效评估
- [ ] 可视化工具
- [ ] 周内效应因子

## 📝 版本历史

### v1.0.0 (2026-04-01)
- ✨ 初始版本
- ✨ 定价因子模块（FF三/四因子、Beta）
- ✨ 因子分析模块（IC/IR、分组回测）
- ✨ 自定义因子（小市值质量因子）
- ✨ 向后兼容easy_xt

## 👥 作者

EasyXT团队

## 📄 许可证

MIT License
