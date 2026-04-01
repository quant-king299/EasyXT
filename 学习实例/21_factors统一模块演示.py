# -*- coding: utf-8 -*-
"""
factors统一模块演示

展示新增的factors模块功能：
- 定价因子（Fama-French三因子/四因子）
- 因子分析（IC/IR分析）
- 分组回测
- 自定义因子（小市值质量因子）

【导入方式】
# 推荐方式：从factors统一导入
from factors import EasyFactor, FundamentalAnalyzerEnhanced
from factors.pricing import FamaFrenchCalculator
from factors.analysis import ICAnalyzer, GroupBacktester
from factors.custom import SmallCapQualityFactor

# 或者直接从子模块导入
from factors.pricing.fama_french import FamaFrenchCalculator
from factors.analysis.ic_analyzer import ICAnalyzer
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("=" * 90)
print(" " * 25 + "factors统一模块演示")
print("=" * 90)

# ============================================================
# 导入factors模块
# ============================================================

print("\n[步骤1] 导入factors模块")
print("-" * 90)

try:
    # 统一导入方式
    from factors import (
        EasyFactor,
        FundamentalAnalyzerEnhanced,
        FamaFrenchCalculator,
        ICAnalyzer,
        GroupBacktester,
        SmallCapQualityFactor
    )
    print("[OK] factors模块导入成功")
    print("\n导入的类:")
    print("  - EasyFactor: 技术面因子（50+因子）")
    print("  - FundamentalAnalyzerEnhanced: 基本面因子（29因子）")
    print("  - FamaFrenchCalculator: Fama-French定价因子")
    print("  - ICAnalyzer: IC/IR因子分析")
    print("  - GroupBacktester: 因子分组回测")
    print("  - SmallCapQualityFactor: 小市值质量因子")
except Exception as e:
    print(f"[FAIL] 导入失败: {e}")
    exit(1)

# ============================================================
# 测试1：查询可用模块和因子
# ============================================================

print("\n" + "=" * 90)
print("[测试1] 查询可用模块和因子")
print("=" * 90)

import factors

# 查询模块状态
modules = factors.get_available_modules()
print("\n[可用模块状态]")
for module, available in modules.items():
    status = "[OK]" if available else "[--]"
    print(f"  {status} {module}")

# 查询因子列表
all_factors = factors.list_all_factors()
print("\n[因子列表]")
for category, factors_list in all_factors.items():
    if factors_list:
        print(f"\n{category} ({len(factors_list)}个):")
        for i, factor in enumerate(factors_list[:5]):  # 只显示前5个
            print(f"  {i+1}. {factor}")
        if len(factors_list) > 5:
            print(f"  ... 还有 {len(factors_list) - 5} 个因子")

# ============================================================
# 测试2：Fama-French定价因子（使用模拟数据）
# ============================================================

print("\n" + "=" * 90)
print("[测试2] Fama-French定价因子计算")
print("=" * 90)

print("\n功能说明:")
print("- MKT（市场因子）: 所有股票的平均收益")
print("- SMB（规模因子）: 小市值组合 - 大市值组合")
print("- HML（价值因子）: 低PB组合 - 高PB组合")
print("- UMD（动量因子）: 高收益组合 - 低收益组合")

print("\n创建模拟数据...")

# 创建模拟数据
np.random.seed(42)
n_stocks = 100
stock_codes = [f'{i:06d}.SZ' for i in range(n_stocks)]

mock_stock_data = pd.DataFrame({
    'stock_code': stock_codes,
    'close': np.random.uniform(10, 100, n_stocks),
    'total_mv': np.random.uniform(10, 1000, n_stocks),  # 市值（亿）
    'pb': np.random.uniform(0.5, 10, n_stocks),  # 市净率
})

mock_stock_data['return'] = np.random.normal(0, 0.02, n_stocks)

print(f"[OK] 模拟数据创建成功")
print(f"  股票数量: {len(mock_stock_data)}")
print(f"  平均市值: {mock_stock_data['total_mv'].mean():.2f}亿")
print(f"  平均PB: {mock_stock_data['pb'].mean():.2f}")

# 计算Fama-French三因子
print("\n计算Fama-French三因子...")
ff_calc = FamaFrenchCalculator()
ff_factors = ff_calc.calculate_ff3_factors('2024-01-15', mock_stock_data)

print("\n[OK] 三因子计算成功")
print(f"  MKT（市场因子）: {ff_factors['MKT']:.4f}")
print(f"  SMB（规模因子）: {ff_factors['SMB']:.4f}")
print(f"  HML（价值因子）: {ff_factors['HML']:.4f}")
print(f"  有效股票数: {ff_factors['N_STOCKS']}")

# 计算Fama-French四因子
print("\n计算Fama-French四因子...")
ff_factors_4 = ff_calc.calculate_ff4_factors('2024-01-15', mock_stock_data)

print("\n[OK] 四因子计算成功")
print(f"  MKT: {ff_factors_4['MKT']:.4f}")
print(f"  SMB: {ff_factors_4['SMB']:.4f}")
print(f"  HML: {ff_factors_4['HML']:.4f}")
print(f"  UMD（动量因子）: {ff_factors_4['UMD']:.4f}")

# ============================================================
# 测试3：IC/IR因子分析
# ============================================================

print("\n" + "=" * 90)
print("[测试3] IC/IR因子分析")
print("=" * 90)

print("\n功能说明:")
print("- IC（信息系数）: 因子与收益率的相关系数")
print("- IR（信息比率）: IC均值 / IC标准差")
print("- 评价标准:")
print("    |IC| > 0.05 : 强预测能力")
print("    IR > 1.0     : 优秀")

print("\n创建模拟因子和收益率数据...")

# 创建模拟数据
n_stocks = 100
n_dates = 50
dates = pd.date_range('2024-01-01', periods=n_dates, freq='D')
stock_codes = [f'{i:06d}.SZ' for i in range(n_stocks)]

# 生成因子值
factor_values = np.random.randn(n_dates, n_stocks) * 0.1
factor_df = pd.DataFrame(factor_values, index=dates, columns=stock_codes)

# 生成收益率（与因子有微弱正相关）
returns = factor_values * 0.03 + np.random.randn(n_dates, n_stocks) * 0.02
return_df = pd.DataFrame(returns, index=dates, columns=stock_codes)

print(f"[OK] 模拟数据创建成功")
print(f"  股票数量: {n_stocks}")
print(f"  交易日数: {n_dates}")

# 计算Rank IC
print("\n计算Rank IC...")
ic_analyzer = ICAnalyzer()
ic_series = ic_analyzer.calculate_rank_ic(factor_df, return_df, min_stock_num=10)

print(f"[OK] Rank IC计算成功")
print(f"  IC序列长度: {len(ic_series)}")
print(f"  IC均值: {ic_series.mean():.4f}")
print(f"  IC标准差: {ic_series.std():.4f}")

# 计算IC统计指标
print("\n计算IC统计指标...")
ic_stats = ic_analyzer.calculate_ic_statistics(ic_series)

print("\n[OK] IC统计计算成功")
print(f"  IC均值: {ic_stats['ic_mean']:.4f}")
print(f"  IC标准差: {ic_stats['ic_std']:.4f}")
print(f"  IR（信息比率）: {ic_stats['ir']:.4f}")
print(f"  t统计量: {ic_stats['t_stat']:.4f}")
print(f"  p值: {ic_stats['p_value']:.4f}")
print(f"  IC为正比例: {ic_stats['positive_ratio']:.2%}")

# 因子评价
print("\n[因子评价]")
if abs(ic_stats['ic_mean']) > 0.05:
    print("  [优秀] 强预测能力 (|IC| > 0.05)")
elif abs(ic_stats['ic_mean']) > 0.03:
    print("  [良好] 较强预测能力 (|IC| > 0.03)")
elif abs(ic_stats['ic_mean']) > 0.02:
    print("  [一般] 有一定预测能力 (|IC| > 0.02)")
else:
    print("  [较弱] 预测能力较弱 (|IC| < 0.02)")

if ic_stats['ir'] > 1.0:
    print("  [优秀] 稳定性优秀 (IR > 1.0)")
elif ic_stats['ir'] > 0.5:
    print("  [良好] 稳定性良好 (IR > 0.5)")
elif ic_stats['ir'] > 0.3:
    print("  [一般] 稳定性一般 (IR > 0.3)")
else:
    print("  [较差] 稳定性较差 (IR < 0.3)")

# ============================================================
# 测试4：小市值质量因子
# ============================================================

print("\n" + "=" * 90)
print("[测试4] 小市值质量因子")
print("=" * 90)

print("\n因子逻辑:")
print("  1. 股票池过滤:")
print("     - 剔除创业板、科创板、北交所")
print("     - 剔除ST股票、高价股（>100元）")
print("  2. 基本面筛选:")
print("     - ROE > 15%")
print("     - ROA > 10%")
print("  3. 因子计算:")
print("     - factor_value = -(rank_mv + rank_pb) / 2")
print("     - 因子值越小越好（小市值+低PB）")

# 创建因子实例
print("\n创建因子实例...")
factor = SmallCapQualityFactor()

print(f"[OK] 因子实例创建成功")
print(f"  因子名称: {factor.name}")
print(f"  因子描述: {factor.description}")
print(f"  计算频率: {factor.freq}")

print("\n[提示] 实际计算需要data_manager和真实数据")
print("      factor_df = factor.calculate('2024-01-15', data_manager)")

# ============================================================
# 总结
# ============================================================

print("\n" + "=" * 90)
print(" " * 30 + "演示总结")
print("=" * 90)

print("\n[已演示的功能]")
print("  [OK] factors模块导入")
print("  [OK] 模块状态查询")
print("  [OK] 因子列表查询（41个因子）")
print("  [OK] Fama-French三因子/四因子计算")
print("  [OK] IC/IR因子分析")
print("  [OK] 小市值质量因子")

print("\n[factors模块优势]")
print("  1. 统一接口：所有因子功能集中管理")
print("  2. 向后兼容：原有easy_xt导入方式仍然有效")
print("  3. 功能扩展：新增定价因子、因子分析等")
print("  4. 模块清晰：pricing、analysis、custom分类明确")

print("\n[下一步]")
print("  1. 准备真实数据（DuckDB数据库）")
print("  2. 使用ICAnalyzer评估因子预测能力")
print("  3. 使用GroupBacktester进行因子回测")
print("  4. 开发更多自定义因子")

print("\n[学习资源]")
print("  - 完整文档: factors/README.md")
print("  - 测试脚本: test_factors_simple.py")
print("  - 定价因子: factors/pricing/fama_french.py")
print("  - IC分析: factors/analysis/ic_analyzer.py")
print("  - 分组回测: factors/analysis/group_backtest.py")

print("\n" + "=" * 90)
print(" " * 25 + "演示完成！")
print("=" * 90)
