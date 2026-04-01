"""
定价因子模块

基于Fama-French模型的标准定价因子计算。

主要功能：
- Fama-French三因子/四因子模型
- 个股Beta系数计算
- 残差收益率（剥离系统性风险）
- 特质波动率因子

使用示例：
>>> from factors.pricing import FamaFrenchCalculator
>>> ff_calc = FamaFrenchCalculator(data_manager)
>>> factors = ff_calc.calculate_ff3_factors('2024-01-15')
"""

from .fama_french import (
    FamaFrenchCalculator,
    PricingFactorCalculator
)

from .beta_calc import BetaCalculator

from .residuals import (
    ResidualCalculator,
    SpecVolCalculator
)

__all__ = [
    'FamaFrenchCalculator',
    'PricingFactorCalculator',
    'BetaCalculator',
    'ResidualCalculator',
    'SpecVolCalculator'
]
