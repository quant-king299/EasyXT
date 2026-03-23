# 101因子平台架构设计 - YAML配置版

## 📋 核心设计理念

```
因子分析 → 信号生成 → 组合构建 → 回测验证 → 实盘部署
```

## 🎯 核心功能模块

### 1️⃣ 因子分析模块
- 101/191因子库
- IC分析
- 因子相关性分析
- 因子中性化

### 2️⃣ 信号生成模块
- 多因子打分
- 因子方向配置
- 因子权重分配
- 排除条件过滤

### 3️⃣ 组合构建模块
- 股票筛选
- 权重分配
- 风险控制

### 4️⃣ 回测验证模块
- 基于Backtrader的回测引擎
- 绩效分析
- 参数优化

### 5️⃣ 实盘部署模块（新增）
- 自动生成实盘交易代码
- EasyXT实盘接口对接
- 策略监控

---

## 📝 YAML策略配置格式

### 完整策略配置示例

```yaml
# 策略基本信息
strategy:
  name: "小市值多因子策略"
  version: "1.0.0"
  author: "Your Name"
  description: "基于市值、ROE、动量的多因子选股策略"

# 回测参数配置
backtest:
  start_date: "20200101"
  end_date: "20231231"
  initial_cash: 1000000        # 初始资金
  commission: 0.001            # 佣金率
  slippage: 0.001              # 滑点

# 股票池配置
universe:
  type: "index"                # index/custom
  index_code: "399101.SZ"      # 中小板综指
  # 或者自定义股票池
  # codes: ["000001.SZ", "000002.SZ", ...]

# 排除条件配置（排除因子）
exclude_filters:
  # ST股票过滤
  - name: "ST股票"
    type: "stock_status"
    condition: "not_in"
    values: ["ST", "*ST", "S*ST"]

  # 退市股票过滤
  - name: "退市股票"
    type: "delist_status"
    condition: "not_in"
    values: ["退市"]

  # 市场过滤
  - name: "市场选择"
    type: "market"
    condition: "in"
    values: ["深交所", "上交所"]

  # 行业过滤
  - name: "行业排除"
    type: "industry"
    condition: "not_in"
    values: ["银行", "非银金融"]

  # 地域过滤
  - name: "地域选择"
    type: "region"
    condition: "not_in"
    values: []  # 空表示不限制

  # 基本面过滤
  - name: "市值过滤"
    type: "fundamental"
    field: "market_cap"
    condition: "between"
    min_value: 1000000000      # 10亿以上
    max_value: 50000000000     # 500亿以下

  - name: "PE过滤"
    type: "fundamental"
    field: "pe_ratio"
    condition: "between"
    min_value: 0
    max_value: 50              # PE < 50

  - name: "ROE过滤"
    type: "fundamental"
    field: "roe"
    condition: "greater_than"
    min_value: 0.05            # ROE > 5%

# 打分因子配置
scoring_factors:
  # 因子1：市值因子（负相关）
  - name: "市值因子"
    factor_type: "fundamental"  # fundamental/technical/alpha101/alpha191/custom
    field: "market_cap"
    direction: -1              # -1: 负相关（越小越好）
    weight: 0.5                # 权重 50%
    normalize: true            # 标准化
    neutralize:                # 中性化配置
      enabled: true
      by: ["industry", "market_cap"]  # 按行业和市值中性化

  # 因子2：ROE因子（正相关）
  - name: "ROE因子"
    factor_type: "fundamental"
    field: "roe"
    direction: 1               # 1: 正相关（越大越好）
    weight: 0.3                # 权重 30%
    normalize: true
    neutralize:
      enabled: true
      by: ["industry"]

  # 因子3：动量因子（正相关）
  - name: "动量因子"
    factor_type: "technical"
    field: "momentum_20"       # 20日动量
    direction: 1
    weight: 0.2                # 权重 20%
    params:
      period: 20               # 计算周期
    normalize: true
    neutralize:
      enabled: false

  # 因子4：Alpha101因子（可选）
  - name: "Alpha001"
    factor_type: "alpha101"
    field: "alpha001"
    direction: 1
    weight: 0.0                # 暂不启用
    normalize: true
    neutralize:
      enabled: false

# 组合构建配置
portfolio:
  # 选股方式
  select_method: "top_n"       # top_n/quantile/threshold
  top_n: 10                    # 选择得分最高的10只股票
  # 或者按分位数选择
  # quantile: 0.2              # 选择前20%股票
  # 或者按阈值选择
  # threshold: 0.5             # 得分 > 0.5的股票

  # 权重分配方式
  weight_method: "equal"       # equal/equal_risk/market_cap/factor_score
  max_single_weight: 0.2       # 单只股票最大权重20%
  min_single_weight: 0.05      # 单只股票最小权重5%

  # 风险控制
  risk_control:
    max_position_count: 20     # 最大持仓数
    max_single_weight: 0.2
    min_single_weight: 0.05
    industry_max_weight: 0.4   # 单行业最大权重
    max_turnover: 0.5          # 最大换手率

# 调仓配置
rebalance:
  frequency: "monthly"         # daily/weekly/monthly/quarterly
  rebalance_day: 1             # 每月第1个交易日
  trade_time: "open"           # open/close

  # 交易执行
  execution:
    type: "close"              # close/open/vwap
    max_trade_ratio: 0.2       # 单日最大交易比例

# 实盘交易配置
live_trading:
  enabled: false               # 是否启用实盘交易
  account_id: "your_account"   # QMT账户ID

  # 交易执行
  execution:
    order_type: "limit"        # limit/market
    price_offset: 0.001        # 限价单偏移

  # 风控
  risk_control:
    max_drawdown: 0.15         # 最大回撤15%止损
    max_loss_per_trade: 0.02   # 单笔最大亏损2%

  # 通知
  notification:
    enabled: true
    on_trade: true             # 交易时通知
    on_rebalance: true         # 调仓时通知
    on_risk: true              # 触及风控时通知
```

### 简化版配置示例（小市值策略）

```yaml
strategy:
  name: "简单小市值策略"
  description: "选择市值最小的10只股票"

backtest:
  start_date: "20200101"
  end_date: "20231231"
  initial_cash: 1000000
  commission: 0.001

universe:
  type: "index"
  index_code: "399101.SZ"      # 中小板

exclude_filters:
  - name: "排除ST"
    type: "stock_status"
    condition: "not_in"
    values: ["ST", "*ST"]

  - name: "市值范围"
    type: "fundamental"
    field: "market_cap"
    condition: "between"
    min_value: 1000000000      # 10亿以上
    max_value: 100000000000    # 100亿以下

scoring_factors:
  - name: "市值因子"
    factor_type: "fundamental"
    field: "market_cap"
    direction: -1              # 负相关
    weight: 1.0
    normalize: true
    neutralize:
      enabled: false

portfolio:
  select_method: "top_n"
  top_n: 10
  weight_method: "equal"

rebalance:
  frequency: "monthly"
  rebalance_day: 1
```

---

## 🏗️ 系统架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                  101因子平台 (easyxt_backtest)               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         YAML策略配置加载器 (StrategyConfigLoader)     │  │
│  │         解析YAML配置，生成策略配置对象                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            排除条件过滤器 (ExcludeFilterEngine)       │  │
│  │         • ST/退市过滤                                 │  │
│  │         • 市场/行业/地域过滤                          │  │
│  │         • 基本面条件过滤                              │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           因子计算引擎 (FactorCalculatorEngine)       │  │
│  │         • 基本面因子计算                              │  │
│  │         • 技术指标因子计算                            │  │
│  │         • Alpha101/191因子计算                        │  │
│  │         • 因子标准化和中性化                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            多因子打分器 (MultiFactorScorer)           │  │
│  │         • 因子方向配置                                │  │
│  │         • 因子权重分配                                │  │
│  │         • 综合打分                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           组合构建器 (PortfolioBuilder)               │  │
│  │         • 股票筛选（Top N/分位数/阈值）               │  │
│  │         • 权重分配                                    │  │
│  │         • 风险控制                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          Backtrader回测引擎 (BacktestEngine)          │  │
│  │         • 交易模拟                                    │  │
│  │         • 佣金/滑点                                  │  │
│  │         • 绩效分析                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         实盘代码生成器 (LiveCodeGenerator) ⭐新增     │  │
│  │         • 生成EasyXT实盘交易代码                      │  │
│  │         • 策略配置导入                                │  │
│  │         • 交易接口封装                                │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           EasyXT实盘交易 (LiveTrading)                │  │
│  │         • QMT实盘对接                                 │  │
│  │         • 订单执行                                    │  │
│  │         • 持仓管理                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 目录结构设计

```
easyxt_backtest/
├── config/
│   ├── __init__.py
│   ├── strategy_loader.py           # YAML策略配置加载器
│   ├── strategy_config.py           # 策略配置数据类
│   └── examples/                    # 配置示例
│       ├── simple_small_cap.yaml
│       ├── multi_factor_strategy.yaml
│       └── alpha101_strategy.yaml
│
├── factors/
│   ├── __init__.py
│   ├── base.py                      # 因子基类
│   ├── calculator.py                # 因子计算器
│   ├── neutralization.py            # 因子中性化
│   ├── fundamental_factors.py       # 基本面因子
│   ├── technical_factors.py         # 技术指标因子
│   ├── alpha101_factors.py          # Alpha101因子（迁移）
│   ├── alpha191_factors.py          # Alpha191因子（迁移）
│   └── custom_factors.py            # 自定义因子示例
│
├── filters/
│   ├── __init__.py
│   ├── base.py                      # 过滤器基类
│   ├── stock_status_filter.py       # ST/退市过滤
│   ├── market_filter.py             # 市场过滤
│   ├── industry_filter.py           # 行业过滤
│   ├── region_filter.py             # 地域过滤
│   └── fundamental_filter.py        # 基本面条件过滤
│
├── scoring/
│   ├── __init__.py
│   ├── multi_factor_scorer.py       # 多因子打分器
│   ├── normalization.py             # 标准化
│   └── weight_manager.py            # 权重管理
│
├── portfolio/
│   ├── __init__.py
│   ├── builder.py                   # 组合构建器
│   ├── weight_methods.py            # 权重分配方法
│   └── risk_control.py              # 风险控制
│
├── strategies/
│   ├── __init__.py
│   ├── base.py                      # 策略基类
│   ├── config_driven_strategy.py    # 配置驱动策略
│   ├── small_cap_strategy.py        # 小市值策略（已有）
│   └── multi_factor_strategy.py     # 多因子策略
│
├── backtest/
│   ├── __init__.py
│   ├── engine.py                    # 回测引擎
│   ├── analyzers.py                 # 分析器
│   └── reports.py                   # 报告生成
│
├── live_trading/
│   ├── __init__.py
│   ├── code_generator.py            # 实盘代码生成器 ⭐新增
│   ├── live_trader.py               # 实盘交易执行
│   ├── order_manager.py             # 订单管理
│   └── risk_monitor.py              # 风险监控
│
├── analysis/
│   ├── __init__.py
│   ├── ic_analysis.py               # IC分析（迁移）
│   ├── factor_correlation.py        # 因子相关性（迁移）
│   └── performance.py               # 绩效分析
│
├── data/
│   ├── __init__.py
│   ├── data_manager.py              # 数据管理器（已有）
│   └── factor_data_loader.py        # 因子数据加载器
│
└── utils/
    ├── __init__.py
    ├── plotting.py                  # 绘图工具
    └── helpers.py                   # 辅助函数
```

---

## 🔧 核心模块设计

### 1. YAML策略配置加载器

```python
# config/strategy_loader.py

import yaml
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path

@dataclass
class FactorConfig:
    """因子配置"""
    name: str
    factor_type: str               # fundamental/technical/alpha101/alpha191/custom
    field: str
    direction: int                 # 1 或 -1
    weight: float
    normalize: bool
    neutralize: Optional[Dict]
    params: Optional[Dict] = None

@dataclass
class ExcludeFilterConfig:
    """排除条件配置"""
    name: str
    type: str
    condition: str
    values: Optional[List[str]] = None
    field: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None

@dataclass
class StrategyConfig:
    """策略配置"""
    name: str
    version: str
    author: str
    description: str

    # 回测参数
    backtest_config: Dict

    # 股票池
    universe_config: Dict

    # 排除条件
    exclude_filters: List[ExcludeFilterConfig]

    # 打分因子
    scoring_factors: List[FactorConfig]

    # 组合构建
    portfolio_config: Dict

    # 调仓配置
    rebalance_config: Dict

    # 实盘交易配置
    live_trading_config: Optional[Dict]

class StrategyConfigLoader:
    """策略配置加载器"""

    @staticmethod
    def load_from_yaml(yaml_path: str) -> StrategyConfig:
        """从YAML文件加载策略配置"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)

        return StrategyConfigLoader._parse_config(config_dict)

    @staticmethod
    def _parse_config(config_dict: Dict) -> StrategyConfig:
        """解析配置字典"""
        strategy = config_dict['strategy']

        # 解析排除条件
        exclude_filters = [
            ExcludeFilterConfig(**f) for f in config_dict.get('exclude_filters', [])
        ]

        # 解析打分因子
        scoring_factors = [
            FactorConfig(**f) for f in config_dict.get('scoring_factors', [])
        ]

        return StrategyConfig(
            name=strategy['name'],
            version=strategy.get('version', '1.0.0'),
            author=strategy.get('author', ''),
            description=strategy.get('description', ''),
            backtest_config=config_dict['backtest'],
            universe_config=config_dict['universe'],
            exclude_filters=exclude_filters,
            scoring_factors=scoring_factors,
            portfolio_config=config_dict['portfolio'],
            rebalance_config=config_dict['rebalance'],
            live_trading_config=config_dict.get('live_trading')
        )

    @staticmethod
    def validate_config(config: StrategyConfig) -> bool:
        """验证配置有效性"""
        # 1. 检查因子权重和为1
        total_weight = sum(f.weight for f in config.scoring_factors)
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"因子权重和必须为1，当前为{total_weight}")

        # 2. 检查日期格式
        # ...

        # 3. 检查资金参数
        # ...

        return True
```

### 2. 排除条件过滤器引擎

```python
# filters/__init__.py

from .stock_status_filter import StockStatusFilter
from .market_filter import MarketFilter
from .industry_filter import IndustryFilter
from .region_filter import RegionFilter
from .fundamental_filter import FundamentalFilter

class ExcludeFilterEngine:
    """排除条件过滤器引擎"""

    def __init__(self, filters: List[ExcludeFilterConfig], data_manager):
        self.filters = filters
        self.data_manager = data_manager
        self.filter_instances = self._init_filters()

    def _init_filters(self):
        """初始化过滤器实例"""
        instances = {}
        for filter_config in self.filters:
            if filter_config.type == "stock_status":
                instances[filter_config.name] = StockStatusFilter(filter_config, self.data_manager)
            elif filter_config.type == "market":
                instances[filter_config.name] = MarketFilter(filter_config, self.data_manager)
            elif filter_config.type == "industry":
                instances[filter_config.name] = IndustryFilter(filter_config, self.data_manager)
            elif filter_config.type == "region":
                instances[filter_config.name] = RegionFilter(filter_config, self.data_manager)
            elif filter_config.type == "fundamental":
                instances[filter_config.name] = FundamentalFilter(filter_config, self.data_manager)
        return instances

    def filter(self, stock_pool: List[str], date: str) -> List[str]:
        """应用所有过滤器"""
        result = stock_pool.copy()
        for name, filter_instance in self.filter_instances.items():
            result = filter_instance.filter(result, date)
        return result
```

### 3. 多因子打分器

```python
# scoring/multi_factor_scorer.py

import pandas as pd
import numpy as np

class MultiFactorScorer:
    """多因子打分器"""

    def __init__(self, factor_configs: List[FactorConfig], data_manager):
        self.factor_configs = factor_configs
        self.data_manager = data_manager

    def calculate_scores(self, stock_pool: List[str], date: str) -> pd.Series:
        """计算综合得分"""
        all_scores = {}

        for factor_config in self.factor_configs:
            if factor_config.weight == 0:
                continue  # 跳过权重为0的因子

            # 1. 计算因子值
            factor_values = self._calculate_factor(
                stock_pool, date, factor_config
            )

            # 2. 标准化
            if factor_config.normalize:
                factor_values = self._normalize(factor_values)

            # 3. 中性化
            if factor_config.neutralize and factor_config.neutralize['enabled']:
                factor_values = self._neutralize(
                    factor_values, date, factor_config.neutralize['by']
                )

            # 4. 应用方向
            factor_values = factor_values * factor_config.direction

            # 5. 应用权重
            all_scores[factor_config.name] = factor_values * factor_config.weight

        # 综合打分
        final_scores = pd.DataFrame(all_scores).sum(axis=1)
        return final_scores

    def _calculate_factor(self, stock_pool, date, config):
        """计算单个因子"""
        if config.factor_type == "fundamental":
            return self._calculate_fundamental_factor(stock_pool, date, config)
        elif config.factor_type == "technical":
            return self._calculate_technical_factor(stock_pool, date, config)
        elif config.factor_type == "alpha101":
            return self._calculate_alpha101_factor(stock_pool, date, config)
        elif config.factor_type == "alpha191":
            return self._calculate_alpha191_factor(stock_pool, date, config)

    def _normalize(self, series: pd.Series) -> pd.Series:
        """Z-score标准化"""
        return (series - series.mean()) / series.std()

    def _neutralize(self, series: pd.Series, date: str, by: List[str]) -> pd.Series:
        """因子中性化"""
        # 实现行业中性化、市值中性化等
        # ...
        return series
```

### 4. 实盘代码生成器（新增核心功能）

```python
# live_trading/code_generator.py

from jinja2 import Template
from pathlib import Path

class LiveCodeGenerator:
    """实盘代码生成器"""

    EASYXT_LIVE_TEMPLATE = """
from easyxt import XtQuantTrader
from datetime import datetime

# 策略配置（从回测配置导入）
STRATEGY_CONFIG = {{ config }}

class {{ strategy_name }}Live:
    \"\"\"{{ strategy_description }} - 实盘交易版本\"\"\"

    def __init__(self, account_id):
        self.account_id = account_id
        self.trader = XtQuantTrader(account_id)
        self.config = STRATEGY_CONFIG

    def on_rebalance(self, date):
        \"\"\"调仓逻辑\"\"\"
        # 1. 获取当前持仓
        current_positions = self.trader.get_positions()

        # 2. 计算目标组合
        target_portfolio = self.calculate_target_portfolio(date)

        # 3. 生成交易订单
        orders = self.generate_orders(current_positions, target_portfolio)

        # 4. 执行交易
        self.execute_orders(orders)

    def calculate_target_portfolio(self, date):
        \"\"\"计算目标组合（使用回测时相同的逻辑）\"\"\"
        # 这里调用与回测时相同的选股和权重计算逻辑
        # ...

    def generate_orders(self, current_positions, target_portfolio):
        \"\"\"生成交易订单\"\"\"
        orders = []
        # ...
        return orders

    def execute_orders(self, orders):
        \"\"\"执行交易\"\"\"
        for order in orders:
            # 应用风控检查
            if self.risk_check(order):
                self.trader.order(order)

    def risk_check(self, order):
        \"\"\"风控检查\"\"\"
        # 实现风控逻辑
        # ...
        return True

if __name__ == "__main__":
    # 启动实盘交易
    strategy = {{ strategy_name }}Live("{{ account_id }}")
    strategy.run()
"""

    @staticmethod
    def generate_live_code(config: StrategyConfig, output_path: str):
        """生成实盘交易代码"""
        # 1. 准备模板变量
        template_vars = {
            'strategy_name': config.name.replace(' ', '_'),
            'strategy_description': config.description,
            'config': config.__dict__,
            'account_id': config.live_trading_config.get('account_id', '')
        }

        # 2. 渲染模板
        template = Template(LiveCodeGenerator.EASYXT_LIVE_TEMPLATE)
        code = template.render(**template_vars)

        # 3. 写入文件
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(code, encoding='utf-8')

        print(f"✅ 实盘交易代码已生成: {output_path}")
        return code

    @staticmethod
    def generate_live_code_v2(config: StrategyConfig, output_path: str):
        """生成实盘交易代码 V2（完整版）"""

        # 生成以下文件：
        # 1. 策略配置文件
        # 2. 实盘交易主程序
        # 3. 策略逻辑模块（复用回测时的选股、打分、组合构建逻辑）
        # 4. 订单管理模块
        # 5. 风控模块
        # 6. 启动脚本

        # ...
```

---

## 🚀 实施路线图

### 阶段1：核心框架（第1-2周）
- [ ] 创建目录结构
- [ ] 实现YAML配置加载器
- [ ] 实现策略配置数据类
- [ ] 编写配置示例（小市值、多因子）

### 阶段2：因子计算引擎（第3-4周）
- [ ] 迁移Alpha101/191因子库
- [ ] 实现基本面因子计算
- [ ] 实现技术指标因子计算
- [ ] 实现因子标准化和中性化

### 阶段3：过滤和打分（第5-6周）
- [ ] 实现各类过滤器（ST、市场、行业、基本面）
- [ ] 实现多因子打分器
- [ ] 实现组合构建器
- [ ] 实现权重分配方法

### 阶段4：回测集成（第7-8周）
- [ ] 实现配置驱动策略
- [ ] 集成到Backtrader回测引擎
- [ ] 完善绩效分析
- [ ] 回测结果对比验证

### 阶段5：实盘代码生成（第9-10周）
- [ ] 实现实盘代码生成器
- [ ] 生成策略逻辑模块（复用回测代码）
- [ ] 生成订单管理和风控模块
- [ ] 测试实盘代码可用性

### 阶段6：测试和文档（第11-12周）
- [ ] 单元测试
- [ ] 集成测试
- [ ] 编写使用文档
- [ ] 编写教程和示例

---

## 📊 使用示例

### 1. 创建策略配置

```bash
# 复制模板
cp easyxt_backtest/config/examples/simple_small_cap.yaml my_strategy.yaml

# 编辑配置
vim my_strategy.yaml
```

### 2. 运行回测

```python
from easyxt_backtest.config import StrategyConfigLoader
from easyxt_backtest.strategies import ConfigDrivenStrategy
from easyxt_backtest.backtest import BacktestEngine

# 加载配置
config = StrategyConfigLoader.load_from_yaml('my_strategy.yaml')

# 创建策略
strategy = ConfigDrivenStrategy(config)

# 运行回测
engine = BacktestEngine(data_manager=data_manager)
result = engine.run(strategy)

# 查看结果
result.print_summary()
```

### 3. 生成实盘代码

```python
from easyxt_backtest.live_trading import LiveCodeGenerator

# 生成实盘交易代码
LiveCodeGenerator.generate_live_code(
    config=config,
    output_path='live_trading_strategies/my_small_cap_live.py'
)

# 运行实盘
# python live_trading_strategies/my_small_cap_live.py
```

---

## 🎯 成功标准

- [x] 支持YAML配置驱动策略
- [x] 支持排除条件（ST、退市、市场、行业、基本面）
- [x] 支持多因子打分（方向、权重、中性化）
- [x] 支持灵活的权重分配
- [x] 回测验证完整
- [x] 自动生成实盘交易代码
- [x] 实盘代码可直接运行
- [x] 完整的文档和示例

---

**文档版本**: v2.0
**创建日期**: 2026-03-23
**作者**: Claude
**状态**: 待用户确认
