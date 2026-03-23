"""
YAML策略配置加载器

支持通过YAML文件配置量化策略，包括：
- 策略基本信息
- 回测参数
- 股票池配置
- 排除条件（过滤器）
- 打分因子配置
- 组合构建配置
- 调仓配置
- 实盘交易配置
"""

import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime


@dataclass
class FactorConfig:
    """
    因子配置

    Attributes:
        name: 因子名称
        factor_type: 因子类型 (fundamental/technical/alpha101/alpha191/custom)
        field: 因子字段名
        direction: 因子方向 (1: 正相关, -1: 负相关)
        weight: 因子权重 (0-1)
        normalize: 是否标准化
        neutralize: 中性化配置
        params: 因子参数 (可选)
    """
    name: str
    factor_type: str
    field: str
    direction: int
    weight: float
    normalize: bool
    neutralize: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """验证因子配置"""
        # 验证方向
        if self.direction not in [1, -1]:
            raise ValueError(f"因子 {self.name} 的方向必须是1或-1")

        # 验证权重
        if not 0 <= self.weight <= 1:
            raise ValueError(f"因子 {self.name} 的权重必须在0-1之间")

        # 验证因子类型
        valid_types = ['fundamental', 'technical', 'alpha101', 'alpha191', 'custom']
        if self.factor_type not in valid_types:
            raise ValueError(f"因子 {self.name} 的类型必须是{valid_types}之一")

        # 默认中性化配置
        if self.neutralize is None:
            self.neutralize = {'enabled': False}

        # 默认参数
        if self.params is None:
            self.params = {}


@dataclass
class ExcludeFilterConfig:
    """
    排除条件配置

    Attributes:
        name: 过滤器名称
        type: 过滤器类型 (stock_status/market/industry/region/fundamental)
        condition: 条件类型 (in/not_in/greater_than/less_than/between)
        values: 值列表 (可选)
        field: 字段名 (用于基本面过滤)
        min_value: 最小值 (用于范围过滤)
        max_value: 最大值 (用于范围过滤)
    """
    name: str
    type: str
    condition: str
    values: Optional[List[str]] = None
    field: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    def __post_init__(self):
        """验证过滤器配置"""
        valid_types = ['stock_status', 'market', 'industry', 'region', 'fundamental']
        if self.type not in valid_types:
            raise ValueError(f"过滤器 {self.name} 的类型必须是{valid_types}之一")

        valid_conditions = ['in', 'not_in', 'greater_than', 'less_than', 'between']
        if self.condition not in valid_conditions:
            raise ValueError(f"过滤器 {self.name} 的条件必须是{valid_conditions}之一")


@dataclass
class StrategyConfig:
    """
    策略配置

    包含策略的所有配置信息，用于驱动回测和实盘交易。

    Attributes:
        name: 策略名称
        version: 版本号
        author: 作者
        description: 策略描述
        backtest_config: 回测参数配置
        universe_config: 股票池配置
        exclude_filters: 排除条件列表
        scoring_factors: 打分因子列表
        portfolio_config: 组合构建配置
        rebalance_config: 调仓配置
        live_trading_config: 实盘交易配置 (可选)
    """
    name: str
    version: str
    author: str
    description: str
    backtest_config: Dict[str, Any]
    universe_config: Dict[str, Any]
    exclude_filters: List[ExcludeFilterConfig]
    scoring_factors: List[FactorConfig]
    portfolio_config: Dict[str, Any]
    rebalance_config: Dict[str, Any]
    live_trading_config: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """验证策略配置"""
        # 验证因子权重和
        total_weight = sum(f.weight for f in self.scoring_factors)
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(
                f"策略 {self.name} 的因子权重和必须为1.0，当前为{total_weight:.3f}"
            )

        # 验证回测日期格式
        start_date = self.backtest_config.get('start_date', '')
        end_date = self.backtest_config.get('end_date', '')
        try:
            datetime.strptime(start_date, '%Y%m%d')
            datetime.strptime(end_date, '%Y%m%d')
        except ValueError:
            raise ValueError(f"回测日期格式必须为YYYYMMDD，例如: 20200101")

        # 验证初始资金
        initial_cash = self.backtest_config.get('initial_cash', 0)
        if initial_cash <= 0:
            raise ValueError(f"初始资金必须大于0，当前为{initial_cash}")


class StrategyConfigLoader:
    """
    策略配置加载器

    从YAML文件加载策略配置，并转换为StrategyConfig对象。
    """

    @staticmethod
    def load_from_yaml(yaml_path: str) -> StrategyConfig:
        """
        从YAML文件加载策略配置

        Args:
            yaml_path: YAML文件路径

        Returns:
            StrategyConfig: 策略配置对象

        Example:
            >>> config = StrategyConfigLoader.load_from_yaml('my_strategy.yaml')
            >>> print(config.name)
            '小市值多因子策略'
        """
        yaml_file = Path(yaml_path)

        if not yaml_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {yaml_path}")

        # 读取YAML文件
        with open(yaml_file, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)

        # 解析配置
        return StrategyConfigLoader._parse_config(config_dict)

    @staticmethod
    def _parse_config(config_dict: Dict[str, Any]) -> StrategyConfig:
        """
        解析配置字典

        Args:
            config_dict: YAML加载后的字典

        Returns:
            StrategyConfig: 策略配置对象
        """
        # 解析策略基本信息
        strategy = config_dict.get('strategy', {})

        # 解析排除条件
        exclude_filters = []
        for f in config_dict.get('exclude_filters', []):
            exclude_filters.append(ExcludeFilterConfig(**f))

        # 解析打分因子
        scoring_factors = []
        for f in config_dict.get('scoring_factors', []):
            scoring_factors.append(FactorConfig(**f))

        # 如果没有因子，添加警告
        if not scoring_factors:
            raise ValueError("策略必须至少配置一个打分因子")

        # 构建策略配置对象
        config = StrategyConfig(
            name=strategy.get('name', '未命名策略'),
            version=strategy.get('version', '1.0.0'),
            author=strategy.get('author', ''),
            description=strategy.get('description', ''),
            backtest_config=config_dict.get('backtest', {}),
            universe_config=config_dict.get('universe', {}),
            exclude_filters=exclude_filters,
            scoring_factors=scoring_factors,
            portfolio_config=config_dict.get('portfolio', {}),
            rebalance_config=config_dict.get('rebalance', {}),
            live_trading_config=config_dict.get('live_trading')
        )

        return config

    @staticmethod
    def validate_config(config: StrategyConfig) -> bool:
        """
        验证配置有效性

        Args:
            config: 策略配置对象

        Returns:
            bool: 验证是否通过

        Raises:
            ValueError: 配置无效时抛出异常
        """
        # StrategyConfig的__post_init__已经做了基础验证
        # 这里可以做额外的验证

        # 验证调仓频率
        freq = config.rebalance_config.get('frequency', '')
        valid_freqs = ['daily', 'weekly', 'monthly', 'quarterly']
        if freq not in valid_freqs:
            raise ValueError(f"调仓频率必须是{valid_freqs}之一")

        # 验证选股方式
        select_method = config.portfolio_config.get('select_method', '')
        valid_methods = ['top_n', 'quantile', 'threshold']
        if select_method not in valid_methods:
            raise ValueError(f"选股方式必须是{valid_methods}之一")

        # 验证权重分配方式
        weight_method = config.portfolio_config.get('weight_method', '')
        valid_weight_methods = ['equal', 'equal_risk', 'market_cap', 'factor_score']
        if weight_method not in valid_weight_methods:
            raise ValueError(f"权重分配方式必须是{valid_weight_methods}之一")

        return True

    @staticmethod
    def save_to_yaml(config: StrategyConfig, yaml_path: str):
        """
        将策略配置保存为YAML文件

        Args:
            config: 策略配置对象
            yaml_path: 保存路径

        Example:
            >>> config = StrategyConfig(...)
            >>> StrategyConfigLoader.save_to_yaml(config, 'my_strategy.yaml')
        """
        # 转换为字典
        config_dict = {
            'strategy': {
                'name': config.name,
                'version': config.version,
                'author': config.author,
                'description': config.description
            },
            'backtest': config.backtest_config,
            'universe': config.universe_config,
            'exclude_filters': [f.__dict__ for f in config.exclude_filters],
            'scoring_factors': [f.__dict__ for f in config.scoring_factors],
            'portfolio': config.portfolio_config,
            'rebalance': config.rebalance_config
        }

        if config.live_trading_config:
            config_dict['live_trading'] = config.live_trading_config

        # 保存为YAML
        yaml_file = Path(yaml_path)
        yaml_file.parent.mkdir(parents=True, exist_ok=True)

        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        print(f"✅ 策略配置已保存到: {yaml_path}")


# 便捷函数
def load_strategy_config(yaml_path: str) -> StrategyConfig:
    """
    加载策略配置的便捷函数

    Args:
        yaml_path: YAML文件路径

    Returns:
        StrategyConfig: 策略配置对象
    """
    config = StrategyConfigLoader.load_from_yaml(yaml_path)
    StrategyConfigLoader.validate_config(config)
    return config


def create_sample_config(output_path: str = 'sample_strategy.yaml'):
    """
    创建示例配置文件

    Args:
        output_path: 输出路径
    """
    sample_config = """
# 策略基本信息
strategy:
  name: "示例小市值策略"
  version: "1.0.0"
  author: "Your Name"
  description: "选择市值最小的10只股票"

# 回测参数配置
backtest:
  start_date: "20200101"
  end_date: "20231231"
  initial_cash: 1000000
  commission: 0.001

# 股票池配置
universe:
  type: "index"
  index_code: "399101.SZ"

# 排除条件配置
exclude_filters:
  - name: "排除ST"
    type: "stock_status"
    condition: "not_in"
    values: ["ST", "*ST"]

  - name: "市值范围"
    type: "fundamental"
    field: "market_cap"
    condition: "between"
    min_value: 1000000000
    max_value: 100000000000

# 打分因子配置
scoring_factors:
  - name: "市值因子"
    factor_type: "fundamental"
    field: "market_cap"
    direction: -1
    weight: 1.0
    normalize: true
    neutralize:
      enabled: false

# 组合构建配置
portfolio:
  select_method: "top_n"
  top_n: 10
  weight_method: "equal"

# 调仓配置
rebalance:
  frequency: "monthly"
  rebalance_day: 1
"""

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(sample_config.strip())

    print(f"✅ 示例配置已创建: {output_path}")
