"""
因子计算器

统一计算不同类型的因子。
"""

from typing import List, Dict
import pandas as pd

try:
    from .base import BaseFactor
    from .fundamental_factors import FundamentalFactor, MarketCapFactor
    from .technical_factors import TechnicalFactor
    from .normalization import FactorNormalization
    from .neutralization import FactorNeutralization
    from ..config import FactorConfig
except ImportError:
    from easyxt_backtest.factors.base import BaseFactor
    from easyxt_backtest.factors.fundamental_factors import FundamentalFactor, MarketCapFactor
    from easyxt_backtest.factors.technical_factors import TechnicalFactor
    from easyxt_backtest.factors.normalization import FactorNormalization
    from easyxt_backtest.factors.neutralization import FactorNeutralization
    from easyxt_backtest.config import FactorConfig


class FactorCalculator:
    """
    因子计算器

    根据因子配置计算因子值，支持：
    - 基本面因子
    - 技术指标因子
    - Alpha101因子
    - Alpha191因子
    - 自定义因子
    """

    def __init__(self, data_manager):
        """
        初始化因子计算器

        Args:
            data_manager: 数据管理器
        """
        self.data_manager = data_manager
        self.factor_cache = {}  # 因子缓存

    def calculate(self,
                  stock_pool: List[str],
                  date: str,
                  factor_config: FactorConfig,
                  use_cache: bool = True) -> pd.Series:
        """
        计算因子值

        Args:
            stock_pool: 股票列表
            date: 日期 (YYYYMMDD)
            factor_config: 因子配置
            use_cache: 是否使用缓存

        Returns:
            Series: 股票代码到因子值的映射
        """
        # 检查缓存
        cache_key = (date, factor_config.name)
        if use_cache and cache_key in self.factor_cache:
            return self.factor_cache[cache_key].copy()

        # 创建因子实例
        factor_instance = self._create_factor(factor_config)

        # 计算原始因子值
        raw_values = factor_instance.calculate(stock_pool, date)

        # 标准化
        if factor_config.normalize:
            normalized_values = FactorNormalization.normalize(
                raw_values,
                method='zscore',
                winsorize_first=True
            )
        else:
            normalized_values = raw_values

        # 中性化
        if factor_config.neutralize and factor_config.neutralize.get('enabled', False):
            neutralized_values = self._apply_neutralization(
                normalized_values,
                stock_pool,
                date,
                factor_config.neutralize
            )
        else:
            neutralized_values = normalized_values

        # 缓存结果
        if use_cache:
            self.factor_cache[cache_key] = neutralized_values.copy()

        return neutralized_values

    def _create_factor(self, config: FactorConfig) -> BaseFactor:
        """
        创建因子实例

        Args:
            config: 因子配置

        Returns:
            因子实例
        """
        factor_type = config.factor_type

        if factor_type == 'fundamental':
            if config.field == 'market_cap':
                return MarketCapFactor(config, self.data_manager)
            else:
                return FundamentalFactor(config, self.data_manager)
        elif factor_type == 'technical':
            return TechnicalFactor(config, self.data_manager)
        elif factor_type == 'alpha101':
            # 导入并使用Alpha101因子
            from .alpha101 import Alpha101Factor
            return Alpha101Factor(config, self.data_manager)
        elif factor_type == 'alpha191':
            # 导入并使用Alpha191因子
            from .alpha191 import Alpha191Factor
            return Alpha191Factor(config, self.data_manager)
        elif factor_type == 'custom':
            # TODO: 支持自定义因子
            raise NotImplementedError("自定义因子尚未实现")
        else:
            raise ValueError(f"不支持的因子类型: {factor_type}")

    def _apply_neutralization(self,
                              factor_values: pd.Series,
                              stock_pool: List[str],
                              date: str,
                              neutralize_config: Dict) -> pd.Series:
        """
        应用因子中性化

        Args:
            factor_values: 因子值
            stock_pool: 股票列表
            date: 日期
            neutralize_config: 中性化配置

        Returns:
            中性化后的因子值
        """
        by_fields = neutralize_config.get('by', [])

        # 准备中性化所需的数据
        industry_data = None
        market_cap_data = None

        if 'industry' in by_fields:
            industry_data = self._get_industry_data(stock_pool, date)

        if 'market_cap' in by_fields:
            market_cap_data = self._get_market_cap_data(stock_pool, date)

        # 执行中性化
        neutralized_values = FactorNeutralization.neutralize(
            factor_values,
            industry_data=industry_data,
            market_cap_data=market_cap_data,
            method='regression'
        )

        return neutralized_values

    def _get_industry_data(self, stock_pool: List[str], date: str) -> pd.Series:
        """
        获取行业分类数据

        Args:
            stock_pool: 股票列表
            date: 日期

        Returns:
            Series: 股票代码到行业的映射
        """
        try:
            if hasattr(self.data_manager, 'get_industry'):
                return self.data_manager.get_industry(stock_pool, date)
            else:
                return pd.Series(index=stock_pool, dtype=str)
        except Exception as e:
            print(f"⚠️ 获取行业数据失败: {e}")
            return pd.Series(index=stock_pool, dtype=str)

    def _get_market_cap_data(self, stock_pool: List[str], date: str) -> pd.Series:
        """
        获取市值数据

        Args:
            stock_pool: 股票列表
            date: 日期

        Returns:
            Series: 股票代码到市值的映射
        """
        try:
            if hasattr(self.data_manager, 'get_fundamentals'):
                df = self.data_manager.get_fundamentals(
                    codes=stock_pool,
                    date=date,
                    fields=['market_cap']
                )
                return df['market_cap']
            else:
                return pd.Series(index=stock_pool, dtype=float)
        except Exception as e:
            print(f"⚠️ 获取市值数据失败: {e}")
            return pd.Series(index=stock_pool, dtype=float)

    def clear_cache(self):
        """清空因子缓存"""
        self.factor_cache.clear()
