# 101因子分析平台

EasyXT的101因子分析模块，提供IC/IR测试、因子相关性分析、分层回测等完整的因子分析功能。

## 功能特性

### 1. IC/IR分析 (ic_ir_analysis.py)
评估因子的预测能力

- **IC (Information Coefficient)**: 信息系数，衡量因子值与未来收益率的相关性
- **IR (Information Ratio)**: 信息比率，IC均值/IC标准差，衡量因子稳定性

功能包括：
- 日度IC值计算
- IC统计指标（均值、标准差、IR、t统计量等）
- IC滚动统计
- IC分布分析
- 因子评级系统

### 2. 因子相关性分析 (factor_correlation.py)
识别重复因子，避免因子冗余

功能包括：
- 因子间相关系数矩阵计算
- 高相关性因子对识别
- 层次聚类分析
- 因子去重建议
- 相关性强度评级

### 3. 分层回测 (layered_backtest.py)
验证因子的有效性

功能包括：
- 根据因子值将股票分层
- 计算各层收益率
- 多空策略回测
- 回测指标计算（夏普比率、最大回撤、年化收益等）
- 分层统计报告

## 安装依赖

```bash
pip install pandas numpy scipy
```

## 快速开始

### 基础使用

```python
import pandas as pd
from easy_xt.alpha_analysis import ICIRAnalyzer, FactorCorrelationAnalyzer, LayeredBacktester

# 准备数据
price_data = pd.DataFrame(...)  # 价格数据: index=日期, columns=股票代码
factor_data = pd.DataFrame(...)  # 因子数据: index=日期, columns=股票代码

# 1. IC/IR分析
analyzer = ICIRAnalyzer(price_data, factor_data)
analyzer.calculate_ic(periods=1, method='spearman')
analyzer.print_report()

# 2. 因子相关性分析
factor_dict = {'alpha001': factor_data1, 'alpha002': factor_data2, ...}
correlation_analyzer = FactorCorrelationAnalyzer(factor_dict)
correlation_analyzer.print_report(threshold=0.7)

# 3. 分层回测
backtester = LayeredBacktester(price_data, factor_data)
backtester.calculate_layer_returns(n_layers=5, periods=1)
backtester.calculate_long_short_returns(n_layers=5)
backtester.print_report()
```

### 完整示例

运行完整示例：

```bash
cd easy_xt/alpha_analysis
python example_usage.py
```

这将：
1. 生成示例数据
2. 演示IC/IR分析
3. 演示因子相关性分析
4. 演示分层回测
5. 生成综合分析报告

## 数据格式要求

### 价格数据格式
```python
price_data = pd.DataFrame(
    data=[[10.5, 20.3, 15.2], ...],  # 价格数据
    index=['2023-01-01', '2023-01-02', ...],  # 日期索引
    columns=['000001.SZ', '000002.SZ', ...]  # 股票代码
)
```

### 因子数据格式
```python
factor_data = pd.DataFrame(
    data=[[0.5, -0.3, 1.2], ...],  # 因子值
    index=['2023-01-01', '2023-01-02', ...],  # 日期索引
    columns=['000001.SZ', '000002.SZ', ...]  # 股票代码
)
```

## API文档

### ICIRAnalyzer

```python
class ICIRAnalyzer:
    """IC/IR分析器"""

    def __init__(self, price_data, factor_data):
        """初始化分析器"""

    def calculate_ic(self, periods=1, return_type='simple', method='pearson'):
        """计算IC值"""

    def calculate_ic_stats(self):
        """计算IC统计指标"""

    def print_report(self):
        """打印分析报告"""

    def save_ic_series(self, filepath):
        """保存IC时间序列"""

    def save_report(self, filepath):
        """保存分析报告"""
```

### FactorCorrelationAnalyzer

```python
class FactorCorrelationAnalyzer:
    """因子相关性分析器"""

    def __init__(self, factor_dict):
        """初始化分析器"""

    def calculate_correlation(self, method='spearman', time_window=None):
        """计算相关系数矩阵"""

    def find_high_correlation_pairs(self, threshold=0.7, method='spearman'):
        """识别高相关性因子对"""

    def hierarchical_clustering(self, method='average', n_clusters=None):
        """层次聚类分析"""

    def generate_removal_suggestions(self, threshold=0.7, keep_criteria='name'):
        """生成去重建议"""

    def print_report(self, threshold=0.7):
        """打印分析报告"""
```

### LayeredBacktester

```python
class LayeredBacktester:
    """分层回测器"""

    def __init__(self, price_data, factor_data):
        """初始化回测器"""

    def calculate_layer_returns(self, n_layers=5, periods=1, method='quantile'):
        """计算分层收益率"""

    def calculate_long_short_returns(self, n_layers=5, periods=1, long_layer=-1, short_layer=0):
        """计算多空策略收益率"""

    def calculate_backtest_metrics(self, returns=None, annualization_factor=252):
        """计算回测指标"""

    def print_report(self):
        """打印回测报告"""
```

## 因子评级标准

### IC/IR评级
- **优秀**: IR >= 1.0 且 |IC均值| >= 0.05
- **良好**: IR >= 0.7 且 |IC均值| >= 0.03
- **中等**: IR >= 0.5 且 |IC均值| >= 0.02
- **一般**: IR >= 0.3 且 |IC均值| >= 0.01
- **较差**: IR < 0.3 或 |IC均值| < 0.01

### 回测评级
- **优秀**: 夏普比率 >= 2.0 且 年化收益 > 10%
- **良好**: 夏普比率 >= 1.5 且 年化收益 > 5%
- **中等**: 夏普比率 >= 1.0 且 年化收益 > 0%
- **一般**: 夏普比率 >= 0.5
- **较差**: 夏普比率 < 0.5

### 相关性强度
- **极强**: |相关系数| >= 0.9
- **强**: |相关系数| >= 0.7
- **中等**: |相关系数| >= 0.5
- **弱**: |相关系数| >= 0.3
- **极弱**: |相关系数| < 0.3

## 输出文件说明

### IC/IR分析
- `{factor_name}_ic_series.csv`: IC时间序列数据
- `{factor_name}_ic_report.csv`: IC统计报告

### 相关性分析
- `factor_correlation_matrix.csv`: 因子相关系数矩阵
- `factor_correlation_report.csv`: 高相关性因子对报告

### 分层回测
- `{factor_name}_long_short_returns.csv`: 多空策略收益率序列
- `{factor_name}_backtest_report.csv`: 回测统计报告
- `factor_comparison_report.csv`: 因子对比综合报告

## 实际应用建议

1. **因子筛选流程**：
   - 首先使用IC/IR分析筛选出预测能力强的因子
   - 然后使用相关性分析去除冗余因子
   - 最后使用分层回测验证因子实际效果

2. **参数调优**：
   - periods: 尝试1、5、10、20等不同周期
   - n_layers: 通常使用5层，也可尝试3层、10层
   - threshold: 相关性阈值通常设为0.7-0.8

3. **风险提示**：
   - 历史表现不代表未来收益
   - 注意过拟合风险
   - 建议使用样本外测试验证
   - 实盘前先进行充分回测

## 常见问题

### Q: IC为负数怎么办？
A: IC为负说明因子与收益负相关，可以考虑将因子值取反使用。

### Q: 如何判断因子是否有效？
A: 综合考虑以下几个指标：
   - |IC均值| >= 0.03
   - IR >= 0.5
   - 分层回测的年化收益 > 0
   - 夏普比率 > 1

### Q: 相关系数高但IC表现不同，是为什么？
A: 可能是因子计算方式或数据处理不同导致的。建议检查因子原始定义，确保计算一致。

## 更新日志

### v1.0.0 (2025-01-17)
- 初始版本发布
- 实现IC/IR分析功能
- 实现因子相关性分析功能
- 实现分层回测功能
- 提供完整使用示例

## 许可证

MIT License

## 作者

EasyXT团队

## 贡献

欢迎提交Issue和Pull Request！
