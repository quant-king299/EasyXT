"""
统一因子库接口

提供完整的因子计算、分析和管理功能。

向后兼容：
- EasyFactor: 技术面因子（50+因子）
- FundamentalAnalyzerEnhanced: 基本面因子（29因子）

新增功能：
- FamaFrenchCalculator: Fama-French定价因子
- ICAnalyzer: IC/IR因子分析
- GroupBacktester: 因子分组回测
- SmallCapQualityFactor: 小市值质量因子
- SpecVolFactor: 特质波动率因子

使用示例：
>>> from factors import EasyFactor, ICAnalyzer
>>> from factors.pricing import FamaFrenchCalculator
>>> from factors.analysis import GroupBacktester

版本：1.0.0
作者：EasyXT团队
"""

__version__ = "1.0.0"

# ============================================================
# 向后兼容：重新导出 easy_xt 的因子模块
# ============================================================

try:
    from easy_xt.factor_library import EasyFactor, create_easy_factor
    from easy_xt.fundamental_enhanced import (
        FundamentalAnalyzerEnhanced,
        get_enhanced_fundamental_factors,
        get_batch_enhanced_factors
    )
    EASYXT_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] 无法导入easy_xt因子模块: {e}")
    EASYXT_AVAILABLE = False

# ============================================================
# 新增：定价因子模块
# ============================================================

try:
    from .pricing import (
        FamaFrenchCalculator,
        PricingFactorCalculator,
        BetaCalculator,
        ResidualCalculator
    )
    PRICING_AVAILABLE = True
except ImportError as e:
    print(f"[INFO] 定价因子模块暂不可用: {e}")
    PRICING_AVAILABLE = False

# ============================================================
# 新增：因子分析模块
# ============================================================

try:
    from .analysis import (
        ICAnalyzer,
        GroupBacktester,
        PerformanceEvaluator,
        FactorVisualizer
    )
    ANALYSIS_AVAILABLE = True
except ImportError as e:
    print(f"[INFO] 因子分析模块暂不可用: {e}")
    ANALYSIS_AVAILABLE = False

# ============================================================
# 新增：自定义因子模块
# ============================================================

try:
    from .custom import (
        SmallCapQualityFactor,
        SpecVolFactor,
        WeekEffectFactor
    )
    CUSTOM_AVAILABLE = True
except ImportError as e:
    print(f"[INFO] 自定义因子模块暂不可用: {e}")
    CUSTOM_AVAILABLE = False

# ============================================================
# 导出接口
# ============================================================

__all__ = []

# 向后兼容导出
if EASYXT_AVAILABLE:
    __all__.extend([
        'EasyFactor',
        'create_easy_factor',
        'FundamentalAnalyzerEnhanced',
        'get_enhanced_fundamental_factors',
        'get_batch_enhanced_factors'
    ])

# 定价因子导出
if PRICING_AVAILABLE:
    __all__.extend([
        'FamaFrenchCalculator',
        'PricingFactorCalculator',
        'BetaCalculator',
        'ResidualCalculator'
    ])

# 因子分析导出
if ANALYSIS_AVAILABLE:
    __all__.extend([
        'ICAnalyzer',
        'GroupBacktester',
        'PerformanceEvaluator',
        'FactorVisualizer'
    ])

# 自定义因子导出
if CUSTOM_AVAILABLE:
    __all__.extend([
        'SmallCapQualityFactor',
        'SpecVolFactor',
        'WeekEffectFactor'
    ])

# ============================================================
# 便捷函数
# ============================================================

def get_available_modules():
    """
    获取可用的因子模块列表

    返回:
        dict: 可用模块状态
    """
    return {
        'easyxt_factors': EASYXT_AVAILABLE,
        'pricing_factors': PRICING_AVAILABLE,
        'analysis_tools': ANALYSIS_AVAILABLE,
        'custom_factors': CUSTOM_AVAILABLE
    }


def list_all_factors():
    """
    列出所有可用的因子

    返回:
        dict: 因子分类列表
    """
    all_factors = {
        '技术面因子': [],
        '基本面因子': [],
        '定价因子': [],
        '自定义因子': []
    }

    if EASYXT_AVAILABLE:
        all_factors['技术面因子'].extend([
            'momentum_5d', 'momentum_10d', 'momentum_20d', 'momentum_60d',
            'volatility_20d', 'volatility_60d', 'volatility_120d',
            'rsi', 'macd', 'kdj', 'atr', 'obv', 'bollinger',
            'volume_ratio', 'turnover_rate', 'amplitude'
        ])

        all_factors['基本面因子'].extend([
            'price_to_ma20', 'price_to_ma60', 'price_percentile',
            'momentum_20d', 'momentum_60d', 'momentum_252d',
            'volatility_20d', 'volatility_60d', 'rsi_14',
            'price_cv_60d', 'trend_strength_60d',
            'avg_volume_5d', 'avg_volume_20d', 'turnover_5d'
        ])

    if PRICING_AVAILABLE:
        all_factors['定价因子'].extend([
            'MKT',  # 市场因子
            'SMB',  # 规模因子
            'HML',  # 价值因子
            'UMD',  # 动量因子
            'beta_mkt', 'beta_smb', 'beta_hml',  # Beta系数
            'residual',  # 残差收益率
            'spec_vol'  # 特质波动率
        ])

    if CUSTOM_AVAILABLE:
        all_factors['自定义因子'].extend([
            'f1_small_cap_quality',  # 小市值质量因子
            'week_effect'  # 周内效应因子
        ])

    return all_factors


if __name__ == "__main__":
    print("=" * 70)
    print(" " * 20 + "统一因子库 - 因子列表")
    print("=" * 70)

    print("\n[可用模块状态]")
    modules = get_available_modules()
    for module, available in modules.items():
        status = "✓" if available else "✗"
        print(f"  {status} {module}")

    print("\n[所有因子]")
    all_factors = list_all_factors()
    for category, factors in all_factors.items():
        if factors:
            print(f"\n{category} ({len(factors)}个):")
            for factor in factors[:10]:  # 只显示前10个
                print(f"  - {factor}")
            if len(factors) > 10:
                print(f"  ... 还有 {len(factors) - 10} 个")

    print("\n" + "=" * 70)
