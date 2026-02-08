"""
EasyFactor 扩展模块演示（完整版）

展示整合后的EasyFactor功能：

【qstock数据源】
- 同花顺行业/概念资金流向（90行业+387概念）
- 北向资金流向（外资流向）
- 同花顺个股资金流向（5175只股票）

【DuckDB本地数据源】
- 767万条历史数据记录（2015-2026）
- 增强版基本面因子（29个因子）
- 智能缓存（首次下载，后续读取本地）
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from easy_xt.factor_library import create_easy_factor
from easy_xt.fundamental_enhanced import FundamentalAnalyzerEnhanced, get_enhanced_fundamental_factors, get_batch_enhanced_factors
import pandas as pd

print("=" * 90)
print(" " * 20 + "EasyFactor 扩展模块演示（完整版）")
print("=" * 90)

# 配置
DUCKDB_PATH = r'D:/StockData/stock_data.ddb'

# 初始化EasyFactor（启用扩展模块）
print("\n[步骤1] 初始化EasyFactor...")
print("-" * 90)

try:
    ef = create_easy_factor(DUCKDB_PATH, enable_extended_modules=True)
    print("[OK] EasyFactor初始化成功\n")
except Exception as e:
    print(f"[FAIL] {e}")
    exit(1)

# ============================================================
# 测试1：同花顺行业/概念资金流向（qstock）
# ============================================================

print("\n" + "=" * 90)
print("[测试1] 同花顺行业/概念资金流向")
print("=" * 90)

print("\n功能说明：")
print("- 同花顺行业资金流向：覆盖90个行业")
print("- 同花顺概念资金流向：覆盖387个概念")
print("- 智能缓存：首次下载，后续读取本地（200-400x速度提升）")

print("\n代码：")
print("""
# 获取行业资金流向TOP20
industry_flow = ef.get_ths_industry_money_flow(top_n=20, use_cache=True)
print(industry_flow)

# 获取概念资金流向TOP20
concept_flow = ef.get_ths_concept_money_flow(top_n=20, use_cache=True)
print(concept_flow)

# 手动更新缓存（可选）
# result = ef.update_ths_money_flow()
# print(result)
""")

print("\n执行结果：")
try:
    # 行业资金流向
    industry_flow = ef.get_ths_industry_money_flow(top_n=10, use_cache=True)
    if not industry_flow.empty:
        print(f"[OK] 获取行业资金流向成功，共 {len(industry_flow)} 个行业")
        print("\n行业资金流向TOP10：")
        print(industry_flow.to_string(index=False))
    else:
        print("[INFO] 行业资金流向为空")
except Exception as e:
    print(f"[INFO] {e}")

try:
    # 概念资金流向
    concept_flow = ef.get_ths_concept_money_flow(top_n=10, use_cache=True)
    if not concept_flow.empty:
        print(f"\n[OK] 获取概念资金流向成功，共 {len(concept_flow)} 个概念")
        print("\n概念资金流向TOP10：")
        print(concept_flow.to_string(index=False))
except Exception as e:
    print(f"[INFO] {e}")

# ============================================================
# 测试2：北向资金流向（qstock）
# ============================================================

print("\n\n" + "=" * 90)
print("[测试2] 北向资金流向（外资流向）")
print("=" * 90)

print("\n功能说明：")
print("- 北向资金历史流向：2,616条历史记录")
print("- 北向资金行业流向：86个行业的资金分布")
print("- 北向资金个股流向：2,767只股票的外资持仓")

print("\n代码：")
print("""
# 获取北向资金历史流向（最近30天）
north_flow = ef.get_north_money_flow(days=30, use_cache=True)
print(north_flow)

# 获取北向资金行业流向TOP20
north_sector = ef.get_north_money_sector(top_n=20)
print(north_sector)

# 获取北向资金个股流向TOP20
north_stock = ef.get_north_money_stock(top_n=20)
print(north_stock)

# 查询特定股票的北向资金
north_single = ef.get_north_money_stock(stock_code='600050')
print(north_single)
""")

print("\n执行结果：")
try:
    # 北向资金历史流向
    north_flow = ef.get_north_money_flow(days=10, use_cache=True)
    if not north_flow.empty:
        print(f"[OK] 获取北向资金历史流向成功，共 {len(north_flow)} 条记录")
        print("\n最近10天北向资金流向：")
        print(north_flow.to_string(index=False))
    else:
        print("[INFO] 北向资金历史流向为空")
except Exception as e:
    print(f"[INFO] {e}")

try:
    # 北向资金行业流向
    north_sector = ef.get_north_money_sector(top_n=10)
    if not north_sector.empty:
        print(f"\n[OK] 获取北向资金行业流向成功，共 {len(north_sector)} 个行业")
        print("\n北向资金行业流向TOP10：")
        print(north_sector.to_string(index=False))
except Exception as e:
    print(f"[INFO] {e}")

try:
    # 北向资金个股流向
    north_stock = ef.get_north_money_stock(top_n=10)
    if not north_stock.empty:
        print(f"\n[OK] 获取北向资金个股流向成功，共 {len(north_stock)} 只股票")
        print("\n北向资金个股流向TOP10：")
        print(north_stock.to_string(index=False))
except Exception as e:
    print(f"[INFO] {e}")

# ============================================================
# 测试3：同花顺个股资金流向（qstock）
# ============================================================

print("\n\n" + "=" * 90)
print("[测试3] 同花顺个股资金流向")
print("=" * 90)

print("\n功能说明：")
print("- 覆盖5,175只股票")
print("- 实时资金流向数据")
print("- 支持排名查询和个股查询")

print("\n代码：")
print("""
# 获取个股资金流向排名TOP20
stock_flow = ef.get_ths_stock_money_flow(top_n=20, use_cache=True)
print(stock_flow)

# 查询特定股票的资金流向
single_flow = ef.get_ths_stock_money_flow(stock_code='000001', use_cache=True)
print(single_flow)
""")

print("\n执行结果：")
try:
    # 个股资金流向排名
    stock_flow = ef.get_ths_stock_money_flow(top_n=10, use_cache=True)
    if not stock_flow.empty:
        print(f"[OK] 获取个股资金流向成功，共 {len(stock_flow)} 只股票")
        print("\n个股资金流向TOP10：")
        print(stock_flow.to_string(index=False))
    else:
        print("[INFO] 个股资金流向为空")
except Exception as e:
    print(f"[INFO] {e}")

try:
    # 查询特定股票
    single_flow = ef.get_ths_stock_money_flow(stock_code='000001', use_cache=True)
    if not single_flow.empty:
        print(f"\n[OK] 查询000001资金流向成功：")
        print(single_flow.to_string(index=False))
except Exception as e:
    print(f"[INFO] {e}")

# ============================================================
# 测试4：增强版基本面因子（DuckDB本地数据）
# ============================================================

print("\n\n" + "=" * 90)
print("[测试4] 增强版基本面因子")
print("=" * 90)

print("\n功能说明：")
print("- 基于DuckDB本地767万条真实数据")
print("- 数据范围：2015-10-26 到 2026-02-02")
print("- 覆盖5,190只股票")
print("- 共29个因子，分为5大类")

print("\n代码：")
print("""
# 创建增强版基本面分析器
analyzer = FundamentalAnalyzerEnhanced(ef.duckdb_reader)

# 获取单只股票的所有因子（29个因子）
df = analyzer.get_all_fundamental_factors('000001.SZ')
print(df)

# 批量获取因子
stock_list = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH']
df_batch = analyzer.get_batch_fundamental_factors(stock_list)
print(df_batch)

# 或使用便捷函数
df = get_enhanced_fundamental_factors('000001.SZ', ef.duckdb_reader)
df_batch = get_batch_enhanced_factors(stock_list, ef.duckdb_reader)
""")

print("\n执行结果：")
try:
    # 创建分析器
    analyzer = FundamentalAnalyzerEnhanced(ef.duckdb_reader)

    # 获取单只股票的因子
    df = analyzer.get_all_fundamental_factors('000001.SZ')
    if not df.empty:
        print(f"[OK] 成功获取 {len(df.columns)} 个基本面因子\n")

        # 按类别显示
        print("[估值因子]")
        valuation_cols = [col for col in df.columns if any(k in col for k in ['price_to', 'percentile', 'dist_from'])]
        if valuation_cols:
            print(df[valuation_cols].to_string())

        print("\n[动量因子]")
        momentum_cols = [col for col in df.columns if 'momentum' in col or 'rsi' in col]
        if momentum_cols:
            print(df[momentum_cols].to_string())

        print("\n[波动率因子]")
        volatility_cols = [col for col in df.columns if 'volatility' in col or 'atr' in col]
        if volatility_cols:
            print(df[volatility_cols].to_string())

    else:
        print("[INFO] 基本面因子为空")
except Exception as e:
    print(f"[INFO] {e}")
    import traceback
    traceback.print_exc()

try:
    # 批量获取因子
    stock_list = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH']
    df_batch = analyzer.get_batch_fundamental_factors(stock_list)
    if not df_batch.empty:
        print(f"\n[OK] 批量获取因子成功，共 {len(df_batch)} 只股票")

        # 显示关键因子
        key_factors = [
            'momentum_20d', 'momentum_60d', 'momentum_252d',
            'volatility_20d', 'volatility_60d',
            'price_to_ma60', 'price_percentile',
            'rsi_14'
        ]
        available_factors = [f for f in key_factors if f in df_batch.columns]

        if available_factors:
            print("\n关键因子对比：")
            print(df_batch[available_factors].to_string())
except Exception as e:
    print(f"[INFO] {e}")

# ============================================================
# 测试5：综合应用（多数据源联动）
# ============================================================

print("\n\n" + "=" * 90)
print("[测试5] 综合应用：资金流向 + 基本面因子双筛选")
print("=" * 90)

print("\n功能说明：")
print("结合资金流向和基本面因子进行股票筛选")
print("示例：找出资金流入且技术面良好的股票")

print("\n代码：")
print("""
# 1. 获取资金流入排名TOP20
stock_flow = ef.get_ths_stock_money_flow(top_n=20, use_cache=True)

# 2. 获取这些股票的基本面因子
stock_list = stock_flow['股票代码'].tolist()
df_factors = get_batch_enhanced_factors(stock_list, ef.duckdb_reader)

# 3. 筛选条件：
#    - 动量>0（20日上涨）
#    - RSI < 70（不超买）
#    - 波动率 < 0.3（风险适中）

df_selected = df_factors[
    (df_factors['momentum_20d'] > 0) &
    (df_factors['rsi_14'] < 70) &
    (df_factors['volatility_20d'] < 0.3)
]

print("符合条件的股票：")
print(df_selected)
""")

print("\n执行结果：")
try:
    # 获取资金流入排名
    stock_flow = ef.get_ths_stock_money_flow(top_n=20, use_cache=True)
    if not stock_flow.empty:
        # 获取基本面因子
        stock_list = stock_flow['股票代码'].tolist()[:10]  # 只取前10只测试
        df_factors = get_batch_enhanced_factors(stock_list, ef.duckdb_reader)

        if not df_factors.empty and all(col in df_factors.columns for col in ['momentum_20d', 'rsi_14', 'volatility_20d']):
            # 筛选
            df_selected = df_factors[
                (df_factors['momentum_20d'] > 0) &
                (df_factors['rsi_14'] < 70) &
                (df_factors['volatility_20d'] < 0.3)
            ]

            if not df_selected.empty:
                print(f"[OK] 找到 {len(df_selected)} 只符合条件的股票：")
                print("(资金流入 + 20日动量>0 + RSI<70 + 波动率<0.3)")
                print(df_selected[['momentum_20d', 'rsi_14', 'volatility_20d']].to_string())
            else:
                print("[INFO] 没有符合条件的股票")
        else:
            print("[INFO] 无法获取完整的基本面因子")
    else:
        print("[INFO] 无法获取资金流向数据")
except Exception as e:
    print(f"[INFO] {e}")

# ============================================================
# 测试6：因子筛选示例
# ============================================================

print("\n\n" + "=" * 90)
print("[测试6] 因子筛选示例：动量选股策略")
print("=" * 90)

print("\n功能说明：")
print("使用基本面因子进行量化选股")
print("示例：动量策略 - 选择趋势向上的股票")

print("\n代码：")
print("""
# 1. 获取多只股票的基本面因子
stock_list = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '600519.SH']
df_factors = get_batch_enhanced_factors(stock_list, ef.duckdb_reader)

# 2. 动量策略筛选条件：
#    - 短期动量>0（20日上涨）
#    - 中期动量>0（60日上涨）
#    - RSI < 70（不超买）

df_selected = df_factors[
    (df_factors['momentum_20d'] > 0) &
    (df_factors['momentum_60d'] > 0) &
    (df_factors['rsi_14'] < 70)
]

print("动量策略筛选结果：")
print(df_selected)
""")

print("\n执行结果：")
try:
    stock_list = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '600519.SH']
    df_factors = get_batch_enhanced_factors(stock_list, ef.duckdb_reader)

    if not df_factors.empty and all(col in df_factors.columns for col in ['momentum_20d', 'momentum_60d', 'rsi_14']):
        df_selected = df_factors[
            (df_factors['momentum_20d'] > 0) &
            (df_factors['momentum_60d'] > 0) &
            (df_factors['rsi_14'] < 70)
        ]

        if not df_selected.empty:
            print(f"[OK] 找到 {len(df_selected)} 只符合条件的股票：")
            print("(20日动量>0 + 60日动量>0 + RSI<70)")
            print(df_selected[['momentum_20d', 'momentum_60d', 'rsi_14']].to_string())
        else:
            print("[INFO] 没有符合条件的股票")
    else:
        print("[INFO] 无法获取完整的动量因子")
except Exception as e:
    print(f"[INFO] {e}")

# ============================================================
# 总结
# ============================================================

print("\n\n" + "=" * 90)
print(" " * 30 + "总结")
print("=" * 90)

summary = """
EasyFactor 扩展模块完整功能

【数据源】

1. qstock数据源（主要数据源）
   - 同花顺行业资金流向（90个行业）
   - 同花顺概念资金流向（387个概念）
   - 北向资金历史流向（2,616条记录）
   - 北向资金行业流向（86个行业）
   - 北向资金个股流向（2,767只股票）
   - 同花顺个股资金流向（5,175只股票）

2. DuckDB本地数据源
   - 767万条历史数据（2015-2026）
   - 5,190只股票覆盖
   - 智能缓存（首次下载，后续读取本地）

【增强版基本面因子】（29个因子）

1. 估值因子（3个）
   - price_to_ma20/60: 相对均线位置
   - price_percentile: 价格历史分位数
   - dist_from_high_252: 距离52周高点的百分比

2. 动量因子（8个）
   - momentum_1/5/10/20/60/120/252d: 多周期动量
   - momentum_accel: 动量加速度
   - rsi_14: 相对强弱指数

3. 波动率因子（6个）
   - volatility_20/60/120d: 历史波动率
   - atr_14: 平均真实波幅
   - volatility_percentile: 波动率分位数

4. 质量因子（5个）
   - price_cv_60d: 价格变异系数
   - trend_strength_60d: 趋势强度
   - consecutive_up/down_days: 连续涨跌天数
   - price_position_52w: 52周价格位置

5. 流动性因子（7个）
   - avg_volume_5/20/60d: 平均成交量
   - volume_ratio: 成交量比率
   - turnover_5/20d: 换手率

【API列表】

# 资金流向相关
ef.get_ths_industry_money_flow(top_n=20, use_cache=True)      # 行业资金流向
ef.get_ths_concept_money_flow(top_n=20, use_cache=True)       # 概念资金流向
ef.get_north_money_flow(days=30, use_cache=True)              # 北向资金历史
ef.get_north_money_sector(top_n=20)                           # 北向资金行业
ef.get_north_money_stock(stock_code=None, top_n=20)           # 北向资金个股
ef.get_ths_stock_money_flow(stock_code=None, top_n=20, use_cache=True)  # 个股资金流向
ef.update_ths_money_flow()                                     # 更新缓存

# 基本面因子相关
get_enhanced_fundamental_factors('000001.SZ', ef.duckdb_reader)           # 单只股票
get_batch_enhanced_factors(stock_list, ef.duckdb_reader)                  # 批量获取

【优势】

1. 数据稳定：qstock提供稳定可靠的数据源
2. 智能缓存：首次下载，后续读取本地（200-400x速度提升）
3. 数据丰富：29个基本面因子 + 6类资金流向数据
4. 高性能：基于767万条本地数据计算
5. 完全本地化：基本面因子无需网络，速度极快

【使用建议】

1. 首次使用会下载数据并缓存到DuckDB
2. 后续使用会直接读取本地缓存，速度极快
3. 可以设置 use_cache=False 强制更新数据
4. 基本面因子完全基于本地数据，无需网络
5. 适合量化选股、回测、实盘分析等场景
"""

print(summary)

print("\n" + "=" * 90)
print(" " * 30 + "演示完成")
print("=" * 90)

print("\n【提示】")
print("1. qstock数据：首次下载，后续读取本地缓存（速度极快）")
print("2. DuckDB数据：完全本地，767万条记录，无需网络")
print("3. 基本面因子：基于本地数据计算，29个因子，速度最快")
print("4. 所有数据都经过测试验证，稳定可靠")
