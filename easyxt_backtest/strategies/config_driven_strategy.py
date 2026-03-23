"""
配置驱动策略

通过YAML配置文件驱动的策略，整合：
- 排除条件过滤器
- 多因子打分器
- 组合构建器
"""

from typing import List, Dict
from datetime import datetime, timedelta
import pandas as pd

from .strategy_base import StrategyBase
from ..config import StrategyConfig
from ..filters.engine import ExcludeFilterEngine
from ..scoring.multi_factor_scorer import MultiFactorScorer
from ..portfolio.builder import PortfolioBuilder


class ConfigDrivenStrategy(StrategyBase):
    """
    配置驱动策略

    完整的量化策略流程：
    1. 获取股票池
    2. 应用排除条件过滤
    3. 计算多因子得分
    4. 构建投资组合
    5. 定期调仓

    使用示例：
        >>> from easyxt_backtest.config import load_strategy_config
        >>> from easyxt_backtest.strategies import ConfigDrivenStrategy
        >>>
        >>> # 加载配置
        >>> config = load_strategy_config('my_strategy.yaml')
        >>>
        >>> # 创建策略
        >>> strategy = ConfigDrivenStrategy(config, data_manager)
        >>>
        >>> # 运行回测
        >>> engine.run_backtest(strategy, '20200101', '20231231')
    """

    def __init__(self, config: StrategyConfig, data_manager=None):
        """
        初始化配置驱动策略

        Args:
            config: 策略配置对象
            data_manager: 数据管理器
        """
        super().__init__(data_manager)

        self.config = config
        self.name = config.name

        # 初始化过滤器引擎
        self.filter_engine = ExcludeFilterEngine(config.exclude_filters, data_manager)

        # 初始化多因子打分器
        self.scorer = MultiFactorScorer(config.scoring_factors, data_manager)

        # 初始化组合构建器
        self.portfolio_builder = PortfolioBuilder(config.portfolio_config, data_manager)

        # 当前持仓
        self.current_portfolio = {}

    def get_stock_pool(self, date: str) -> List[str]:
        """
        获取股票池

        Args:
            date: 日期 (YYYYMMDD)

        Returns:
            股票列表
        """
        universe_config = self.config.universe_config

        if universe_config['type'] == 'index':
            # 从指数成分股获取股票池
            index_code = universe_config.get('index_code')
            if index_code and hasattr(self.data_manager, 'get_index_components'):
                return self.data_manager.get_index_components(index_code, date)
            else:
                raise ValueError(f"无法获取指数成分股: {index_code}")

        elif universe_config['type'] == 'custom':
            # 自定义股票池
            return universe_config.get('codes', [])

        else:
            raise ValueError(f"不支持的股票池类型: {universe_config['type']}")

    def select_stocks(self, date: str) -> List[str]:
        """
        选股

        流程：
        1. 获取股票池
        2. 应用排除条件过滤
        3. 计算多因子得分
        4. 根据得分选股

        Args:
            date: 日期 (YYYYMMDD)

        Returns:
            选中的股票列表
        """
        # 1. 获取股票池
        stock_pool = self.get_stock_pool(date)

        # 2. 应用排除条件过滤
        filtered_stocks = self.filter_engine.filter(stock_pool, date, verbose=False)

        # 3. 计算多因子得分
        scores = self.scorer.calculate_scores(filtered_stocks, date, verbose=False)

        # 4. 选股（由PortfolioBuilder完成）
        selected_stocks = self.portfolio_builder._select_stocks(scores)

        return selected_stocks

    def get_target_weights(self, date: str, selected_stocks: List[str]) -> Dict[str, float]:
        """
        获取目标权重

        流程：
        1. 计算多因子得分
        2. 根据得分分配权重
        3. 应用风险控制

        Args:
            date: 日期
            selected_stocks: 选中的股票列表

        Returns:
            权重字典 {股票代码: 权重}
        """
        # 1. 获取过滤后的股票池
        stock_pool = self.get_stock_pool(date)
        filtered_stocks = self.filter_engine.filter(stock_pool, date, verbose=False)

        # 2. 计算多因子得分
        scores = self.scorer.calculate_scores(filtered_stocks, date, verbose=False)

        # 3. 构建投资组合（包含权重分配和风控）
        weights = self.portfolio_builder.build_portfolio(
            scores,
            date,
            self.current_portfolio
        )

        # 更新当前持仓
        self.current_portfolio = weights

        return weights

    def get_rebalance_dates(self, start_date: str, end_date: str) -> List[str]:
        """
        获取调仓日期

        根据配置的频率计算调仓日期

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            调仓日期列表
        """
        rebalance_config = self.config.rebalance_config
        frequency = rebalance_config.get('frequency', 'monthly')

        # 转换日期格式
        start = datetime.strptime(start_date, '%Y%m%d')
        end = datetime.strptime(end_date, '%Y%m%d')

        rebalance_dates = []

        if frequency == 'daily':
            # 每日调仓
            current = start
            while current <= end:
                rebalance_dates.append(current.strftime('%Y%m%d'))
                current += timedelta(days=1)

        elif frequency == 'weekly':
            # 每周调仓（每周第一个交易日）
            current = start
            while current <= end:
                # 假设周一为第一个交易日
                if current.weekday() == 0:  # 周一
                    rebalance_dates.append(current.strftime('%Y%m%d'))
                current += timedelta(days=1)

        elif frequency == 'monthly':
            # 每月调仓（每月第N个交易日）
            rebalance_day = rebalance_config.get('rebalance_day', 1)

            current = start
            while current <= end:
                # 每月第1天
                if current.day == rebalance_day:
                    rebalance_dates.append(current.strftime('%Y%m%d'))
                    # 移到下个月
                    if current.month == 12:
                        current = current.replace(year=current.year + 1, month=1, day=1)
                    else:
                        current = current.replace(month=current.month + 1, day=1)
                else:
                    current += timedelta(days=1)

        elif frequency == 'quarterly':
            # 每季度调仓
            current = start
            while current <= end:
                # 每季度第1个月（1, 4, 7, 10月）的第1天
                if current.day == 1 and current.month in [1, 4, 7, 10]:
                    rebalance_dates.append(current.strftime('%Y%m%d'))
                    # 移到下个月
                    if current.month == 12:
                        current = current.replace(year=current.year + 1, month=1, day=1)
                    else:
                        current = current.replace(month=current.month + 1, day=1)
                else:
                    current += timedelta(days=1)

        else:
            raise ValueError(f"不支持的调仓频率: {frequency}")

        return rebalance_dates

    def get_strategy_summary(self) -> str:
        """
        获取策略摘要

        Returns:
            策略摘要字符串
        """
        summary = f"策略名称: {self.config.name}\n"
        summary += f"版本: {self.config.version}\n"
        summary += f"描述: {self.config.description}\n\n"

        summary += self.filter_engine.get_filter_summary()
        summary += "\n"
        summary += self.scorer.get_factor_summary()

        return summary
