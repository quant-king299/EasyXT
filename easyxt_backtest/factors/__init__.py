"""
因子计算引擎模块

提供因子计算、标准化和中性化功能。
"""

from .base import BaseFactor
from .calculator import FactorCalculator

__all__ = [
    'BaseFactor',
    'FactorCalculator'
]
