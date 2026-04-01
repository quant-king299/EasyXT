"""
自定义因子模块

收集和实现各种自定义量化因子。

主要因子：
- 小市值质量因子（f1）：小市值 + 高ROE/ROA筛选
- 特质波动率因子（spec_vol）：基于残差的波动率
- 周内效应因子（week_effect）：周一vs其他交易日

使用示例：
>>> from factors.custom import SmallCapQualityFactor
>>> factor = SmallCapQualityFactor()
>>> factor_df = factor.calculate('2024-01-15', data_manager)
"""

from .small_cap_quality import SmallCapQualityFactor

from .spec_vol import SpecVolFactor

from .week_effect import WeekEffectFactor

__all__ = [
    'SmallCapQualityFactor',
    'SpecVolFactor',
    'WeekEffectFactor'
]
