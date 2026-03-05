# EasyXT通用回测框架

一个功能强大、易于扩展的量化策略回测框架，专为EasyXT设计。

## 特性

✅ **多策略支持**
- 选股策略（如小市值策略）
- 因子策略
- 自定义策略

✅ **多数据源**
- DuckDB本地数据库（最快）
- QMT历史数据
- Tushare在线API

✅ **完整交易模拟**
- 买入/卖出执行
- 佣金和滑点
- 持仓管理

✅ **详细性能分析**
- 总收益率、年化收益率
- 最大回撤、波动率
- 夏普比率、卡尔玛比率
- 交易记录完整保存

✅ **智能数据处理**
- 自动查找最近交易日价格（解决数据缺失问题）
- 多数据源自动切换
- 日期格式自动转换

## 快速开始

### 1. 基础使用

```python
from easyxt_backtest import DataManager, BacktestEngine
from easyxt_backtest.strategies import SmallCapStrategy

# 创建数据管理器
data_manager = DataManager(
    duckdb_path='D:/StockData/stock_data.ddb',
    tushare_token='your_token_here'
)

# 创建策略
strategy = SmallCapStrategy(
    index_code='399101.SZ',  # 中小板综指
    select_num=5,            # 选择5只股票
    rebalance_freq='monthly' # 每月调仓
)

# 创建回测引擎
engine = BacktestEngine(
    initial_cash=1000000,  # 初始资金100万
    commission=0.001,      # 佣金0.1%
    data_manager=data_manager
)

# 运行回测
result = engine.run_backtest(
    strategy=strategy,
    start_date='20230101',
    end_date='20231231'
)

# 查看结果
result.print_summary()
```

### 2. 运行示例

```bash
# 快速测试（3个月）
cd easyxt_backtest/examples
python small_cap_backtest.py --quick

# 完整回测
python small_cap_backtest.py

# 自定义参数
python small_cap_backtest.py --start 20220101 --end 20231231 --num 10 --cash 5000000
```

## 项目结构

```
easyxt_backtest/
├── __init__.py                 # 模块导出
├── data_manager.py             # 数据管理器（多数据源）
├── strategy_base.py            # 策略基类
├── engine.py                   # 回测引擎
├── performance.py              # 性能分析器
├── strategies/
│   ├── __init__.py
│   └── small_cap_strategy.py   # 小市值策略
├── examples/
│   ├── __init__.py
│   └── small_cap_backtest.py   # 使用示例
└── output/                     # 输出目录（自动创建）
    ├── trades.csv              # 交易记录
    ├── portfolio_history.csv   # 持仓历史
    └── returns.csv             # 收益率序列
```

## 创建自定义策略

### 选股策略示例

```python
from easyxt_backtest.strategy_base import StrategyBase
from typing import List, Dict

class MyStrategy(StrategyBase):
    """自定义选股策略"""

    def select_stocks(self, date: str) -> List[str]:
        """实现选股逻辑"""
        # 1. 获取股票池
        all_stocks = self.data_manager.get_index_components('000300.SH', date)

        # 2. 获取基本面数据
        df = self.data_manager.get_fundamentals(
            codes=all_stocks,
            date=date,
            fields=['pe_ratio', 'market_cap']
        )

        # 3. 应用筛选条件
        df = df[df['pe_ratio'] < 20]  # PE < 20
        df = df[df['market_cap'] > 1000000]  # 市值 > 100亿

        # 4. 排序选择
        selected = df.nsmallest(10, 'pe_ratio').index.tolist()

        return selected

    def get_target_weights(self, date: str, selected_stocks: List[str]) -> Dict[str, float]:
        """计算目标权重"""
        # 等权重
        weight = 1.0 / len(selected_stocks)
        return {stock: weight for stock in selected_stocks}

    def get_rebalance_dates(self, start_date: str, end_date: str) -> List[str]:
        """获取调仓日期"""
        # 每月第一个交易日
        return self._get_first_trading_days_monthly(start_date, end_date)
```

### 因子策略示例

```python
from easyxt_backtest.strategy_base import FactorStrategyBase
import pandas as pd

class MyFactorStrategy(FactorStrategyBase):
    """自定义因子策略"""

    def get_factor_values(self, date: str) -> pd.Series:
        """获取因子值"""
        all_stocks = self.data_manager.get_index_components('000300.SH', date)

        df = self.data_manager.get_fundamentals(
            codes=all_stocks,
            date=date,
            fields=['roe']  # ROE因子
        )

        return df['roe']

    def get_target_weights(self, date: str, selected_stocks: List[str]) -> Dict[str, float]:
        """基于因子值分配权重"""
        factor_values = self.get_factor_values(date)

        # 选择因子值最高的20%股票做多，最低20%做空
        top_threshold = factor_values.quantile(0.8)
        bottom_threshold = factor_values.quantile(0.2)

        long_stocks = factor_values[factor_values >= top_threshold].index.tolist()
        short_stocks = factor_values[factor_values <= bottom_threshold].index.tolist()

        # 分配权重
        weight = 1.0 / len(long_stocks)
        weights = {}

        for stock in long_stocks:
            weights[stock] = weight  # 做多
        for stock in short_stocks:
            weights[stock] = -weight  # 做空

        return weights

    def get_rebalance_dates(self, start_date: str, end_date: str) -> List[str]:
        """每季度调仓"""
        return self._get_first_trading_days_monthly(start_date, end_date)[::3]
```

## 性能指标说明

### 收益指标
- **总收益率**: (最终价值 - 初始资金) / 初始资金
- **年化收益率**: (1 + 总收益率)^(365/回测天数) - 1

### 风险指标
- **最大回撤**: 从历史最高点到最低点的最大跌幅
- **波动率**: 收益率标准差的年化值

### 风险调整收益
- **夏普比率**: (年化收益率 - 无风险利率) / 年化波动率
  - >1: 优秀
  - 0.5-1: 良好
  - <0.5: 一般
- **卡尔玛比率**: 年化收益率 / |最大回撤|

## 常见问题

### Q: 如何解决"调仓日数据缺失"问题？
A: 框架已内置 `get_nearest_price()` 方法，会自动查找最近交易日的价格，无需手动处理。

### Q: 支持哪些数据源？
A: 优先级：DuckDB > QMT > Tushare。框架会自动选择可用的数据源。

### Q: 如何添加自定义数据源？
A: 继承 `DataManager` 类并重写对应方法即可。

### Q: 回测速度如何？
A: 使用DuckDB本地数据库时，2023年全年回测约需1-2分钟。

### Q: 如何查看详细交易记录？
A: 回测结果会保存到 `easyxt_backtest/output/` 目录。

## 技术支持

- 查看示例：`easyxt_backtest/examples/small_cap_backtest.py`
- 查看策略实现：`easyxt_backtest/strategies/small_cap_strategy.py`
- 查看API文档：各模块的docstring

## 版本历史

### v1.0.0 (2025-03-04)
- ✅ 核心框架完成
- ✅ 数据管理器（多数据源支持）
- ✅ 策略基类（选股+因子）
- ✅ 回测引擎（完整交易模拟）
- ✅ 性能分析器（全面指标）
- ✅ 小市值策略示例

## 待开发功能

- [ ] 可视化图表（净值曲线、回撤图、持仓分析）
- [ ] HTML/PDF回测报告生成
- [ ] 更多内置策略（动量、均值回归等）
- [ ] 参数优化功能
- [ ] 多策略组合回测
- [ ] 实盘交易接口对接

## License

MIT License
