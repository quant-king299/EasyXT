"""
因子引擎模块

包含：
- Alpha101因子
- Alpha191因子
- 特质波动率因子
- 因子计算器
- 因子分析器
"""

from .alpha101 import Alpha101Factors
from .alpha191 import Alpha191Factors, calculate_alpha191_factor
from .specific_volatility import (
    SpecificVolatilityCalculator,
    SpecificVolatilityFactor,
    calculate_specific_volatility_factor
)
from .calculator import FactorCalculator

# 可选导入
try:
    from .factor_analyzer_with_local_data import EasyFactorAnalyzer
    _easy_factor_analyzer_available = True
except (ImportError, ModuleNotFoundError):
    _easy_factor_analyzer_available = False

__all__ = [
    'Alpha101Factors',
    'Alpha191Factors',
    'calculate_alpha191_factor',
    'SpecificVolatilityCalculator',
    'SpecificVolatilityFactor',
    'calculate_specific_volatility_factor',
    'FactorCalculator',
]

# 如果可用，添加到导出列表
if _easy_factor_analyzer_available:
    __all__.append('EasyFactorAnalyzer')
