"""
EasyFactor 使用示例 - DuckDB版

展示EasyFactor基于DuckDB本地数据库的完整功能
专注于高效批量因子计算和综合分析
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from easy_xt.factor_library import EasyFactor, create_easy_factor, create_duckdb_factor
import pandas as pd

print("=" * 90)
print(" " * 30 + "EasyFactor DuckDB版使用示例")
print("=" * 90)

# ============================================================
# 配置DuckDB数据库路径
# ============================================================
DUCKDB_PATH = r'D:/StockData/stock_data.ddb'  # 请修改为你的实际路径

# ============================================================
# 示例1：初始化EasyFactor
# ============================================================

print("\n" + "=" * 90)
print("[示例1] 初始化EasyFactor")
print("=" * 90)

print("\n代码：")
print("""
# 方式1：使用EasyFactor类
ef = EasyFactor(duckdb_path='D:/StockData/stock_data.ddb')

# 方式2：使用便捷函数
ef = create_easy_factor('D:/StockData/stock_data.ddb')

# 方式3：使用别名（向后兼容）
ef = create_duckdb_factor('D:/StockData/stock_data.ddb')
""")

print("\n执行结果：")
try:
    ef = create_easy_factor(DUCKDB_PATH)
    print("[OK] EasyFactor初始化成功")
except Exception as e:
    print(f"[FAIL] {e}")
    print("\n[提示] 请确保DuckDB数据库文件存在，并修改DUCKDB_PATH变量")
    exit(1)

# ============================================================
# 示例2：获取股票列表
# ============================================================

print("\n\n" + "=" * 90)
print("[示例2] 获取股票列表")
print("=" * 90)

print("\n代码：")
print("""
# 获取所有股票
all_stocks = ef.get_stock_list()

# 获取前10只股票
stocks = ef.get_stock_list(limit=10)
""")

print("\n执行结果：")
try:
    stocks_df = ef.get_stock_list(limit=10)
    if not stocks_df.empty:
        stock_list = stocks_df['stock_code'].tolist()
        print(f"[OK] 数据库中的股票（前10只）: {', '.join(stock_list)}")
    else:
        print("[INFO] 股票列表为空")
except Exception as e:
    print(f"[FAIL] {e}")

# ============================================================
# 示例3：获取市场数据
# ============================================================

print("\n\n" + "=" * 90)
print("[示例3] 获取市场数据")
print("=" * 90)

print("\n代码：")
print("""
# 获取单只股票的日线数据
df = ef.get_market_data_ex(
    stock_code='000001.SZ',
    start_time='2024-01-01',
    end_time='2024-11-30',
    period='daily'
)
""")

print("\n执行结果：")
try:
    df = ef.get_market_data_ex('000001.SZ', '2024-01-01', '2024-11-30', period='daily')
    if not df.empty:
        print(f"[OK] 获取 {len(df)} 条数据")
        print("\n数据预览（最后3天）：")
        print(df[['Date', 'Open', 'High', 'Low', 'Close']].tail(3))
    else:
        print("[FAIL] 数据为空")
except Exception as e:
    print(f"[FAIL] {e}")

# ============================================================
# 示例4：计算单个因子
# ============================================================

print("\n\n" + "=" * 90)
print("[示例4] 计算单个因子")
print("=" * 90)

print("\n代码：")
print("""
# 计算20日动量因子
momentum = ef.get_factor('000001.SZ', 'momentum_20d', '2024-01-01', '2024-11-30')

# 计算RSI
rsi = ef.get_factor('000001.SZ', 'rsi', '2024-01-01', '2024-11-30')

# 计算波动率
volatility = ef.get_factor('000001.SZ', 'volatility_20d', '2024-01-01', '2024-11-30')
""")

print("\n执行结果：")
try:
    # 动量
    momentum = ef.get_factor('000001.SZ', 'momentum_20d', '2024-01-01', '2024-11-30')
    if not momentum.empty:
        val = momentum['momentum_20d'].iloc[-1]
        print(f"[OK] 20日动量: {val:+.2%}")

    # RSI
    rsi = ef.get_factor('000001.SZ', 'rsi', '2024-01-01', '2024-11-30')
    if not rsi.empty:
        val = rsi['rsi'].iloc[-1]
        print(f"[OK] RSI指标: {val:.2f}")

    # 波动率
    volatility = ef.get_factor('000001.SZ', 'volatility_20d', '2024-01-01', '2024-11-30')
    if not volatility.empty:
        val = volatility['volatility_20d'].iloc[-1]
        print(f"[OK] 年化波动率: {val:.2%}")

except Exception as e:
    print(f"[FAIL] {e}")

# ============================================================
# 示例5：批量获取因子
# ============================================================

print("\n\n" + "=" * 90)
print("[示例5] 批量获取因子")
print("=" * 90)

print("\n代码：")
print("""
# 批量获取多只股票的因子
factors = ef.get_factor_batch(
    stock_list=['000001.SZ', '600000.SH', '600519.SH'],
    factor_names=['momentum_20d', 'rsi', 'volatility_20d'],
    start_date='2024-01-01',
    end_date='2024-11-30'
)
""")

print("\n执行结果：")
try:
    factors = ef.get_factor_batch(
        stock_list=['000001.SZ', '600000.SH', '600519.SH'],
        factor_names=['momentum_20d', 'rsi', 'volatility_20d'],
        start_date='2024-01-01',
        end_date='2024-11-30'
    )

    if 'momentum_20d' in factors and not factors['momentum_20d'].empty:
        print("[OK] 批量获取成功\n")
        print("20日动量排名：")
        momentum_df = factors['momentum_20d'].sort_values('momentum_20d', ascending=False)
        for _, row in momentum_df.iterrows():
            print(f"  {row['stock_code']}: {row['momentum_20d']:+.2%}")

except Exception as e:
    print(f"[FAIL] {e}")

# ============================================================
# 示例6：批量分析（DuckDB优化版）
# ============================================================

print("\n\n" + "=" * 90)
print("[示例6] 批量分析 - DuckDB高效版")
print("=" * 90)

print("\n代码：")
print("""
# 批量分析多只股票（一次读取，批量计算）
stock_list = ['000001.SZ', '000002.SZ', '600000.SH', '600519.SH']
results = ef.analyze_batch(
    stock_list=stock_list,
    start_date='2024-01-01',
    end_date='2024-11-30',
    factors=['momentum', 'volatility', 'technical', 'score']
)

# 查看综合评分
print(results['score'])
""")

print("\n执行结果：")
try:
    stock_list = ['000001.SZ', '000002.SZ', '600000.SH', '600519.SH']
    results = ef.analyze_batch(stock_list, '2024-01-01', '2024-11-30')

    if 'score' in results and not results['score'].empty:
        print("[OK] 批量分析成功\n")
        print("综合评分排名：")
        scores_sorted = results['score'].sort_values('score', ascending=False)
        for stock, row in scores_sorted.iterrows():
            print(f"  {stock:<12} 评分:{row['score']:>6.2f}/{row['max_score']:.0f}  {row['rating']}级")

except Exception as e:
    print(f"[FAIL] {e}")

# ============================================================
# 示例7：综合评分
# ============================================================

print("\n\n" + "=" * 90)
print("[示例7] 综合评分")
print("=" * 90)

print("\n代码：")
print("""
# 多因子综合评分
stock_list = ['000001.SZ', '600000.SH', '600519.SH', '000858.SZ']
scores = ef.get_comprehensive_score(stock_list)

# 按评分排序
print(scores.sort_values('score', ascending=False))
""")

print("\n执行结果：")
try:
    stock_list = ['000001.SZ', '600000.SH', '600519.SH', '000858.SZ']
    scores = ef.get_comprehensive_score(stock_list)

    if not scores.empty:
        print("[OK] 综合评分计算成功\n")
        print("综合评分排名：")
        for idx, (stock, row) in enumerate(scores.sort_values('score', ascending=False).iterrows(), 1):
            rating_stars = "*" * (5 if row['rating'] == 'A' else 4 if row['rating'] == 'B' else 3)
            print(f"  {idx}. {stock:<12} {row['rating']}级  {rating_stars}  评分:{row['score']:>6.2f}")

except Exception as e:
    print(f"[FAIL] {e}")

# ============================================================
# 支持的因子列表
# ============================================================

print("\n\n" + "=" * 90)
print(" " * 25 + "支持的50+类因子列表")
print("=" * 90)

factor_list = """
技术面因子（50+类）：

【动量类】
  momentum_5d    - 5日动量
  momentum_10d   - 10日动量
  momentum_20d   - 20日动量
  momentum_60d   - 60日动量
  momentum_vol   - 量价动量

【反转类】
  reversal_short - 短期反转（5日）
  reversal_mid   - 中期反转（20日）
  reversal_long  - 长期反转（60日）

【波动率类】
  volatility_20d   - 20日波动率（年化）
  volatility_60d   - 60日波动率（年化）
  volatility_120d  - 120日波动率（年化）
  max_drawdown     - 最大回撤

【均线信号】
  ma5_signal   - 5日均线信号
  ma10_signal  - 10日均线信号
  ma20_signal  - 20日均线信号
  ma60_signal  - 60日均线信号
  ma_trend     - 均线趋势

【技术指标】
  rsi       - 相对强弱指数
  macd      - MACD指标
  kdj       - 随机指标
  atr       - 平均真实波幅
  obv       - 能量潮
  bollinger - 布林带位置

【量价因子】
  volume_ratio      - 量比
  turnover_rate     - 换手率
  amplitude         - 振幅
  price_volume_trend - 价量趋势

基本面因子（框架已建立，数据源待完善）：

【估值因子】
  pe_ttm     - 滚动市盈率
  pb         - 市净率
  ps         - 市销率
  pcf        - 市现率
  market_cap - 市值

【质量因子】
  roe         - 净资产收益率
  roa         - 总资产收益率
  gross_margin - 毛利率
  net_margin   - 净利率
  debt_ratio   - 资产负债率

【成长因子】
  revenue_growth - 营收增长率
  profit_growth  - 利润增长率
  eps_growth     - EPS增长率
"""

print(factor_list)

# ============================================================
# 最佳实践
# ============================================================

print("\n" + "=" * 90)
print(" " * 35 + "最佳实践")
print("=" * 90)

best_practices = """
【1】初始化：
  ef = EasyFactor(duckdb_path='D:/StockData/stock_data.ddb')

【2】单股票因子分析：
  momentum = ef.get_factor('000001.SZ', 'momentum_20d', '2024-01-01', '2024-11-30')

【3】多股票批量分析（推荐）：
  results = ef.analyze_batch(
      stock_list=['000001.SZ', '600000.SH', ...],
      start_date='2024-01-01',
      end_date='2024-11-30',
      factors=['momentum', 'volatility', 'score']
  )

【4】综合评分选股：
  scores = ef.get_comprehensive_score(stock_list)
  a_stocks = scores[scores['rating'] == 'A']

【5】全市场扫描：
  all_stocks = ef.get_stock_list()
  results = ef.analyze_batch(all_stocks[:100], '2024-01-01', '2024-11-30')
"""

print(best_practices)

# ============================================================
# 总结
# ============================================================

print("\n" + "=" * 90)
print(" " * 30 + "总结")
print("=" * 90)

summary = """
EasyFactor DuckDB版特点：

1. 高性能批量计算
   - 一次读取多只股票数据
   - 并行计算多个因子
   - 适合全市场扫描

2. 简洁的API接口
   - 只需指定DuckDB数据库路径
   - 统一的因子计算接口
   - 自动处理数据格式

3. 完整的因子库
   - 50+类技术面因子
   - 基本面因子框架
   - 综合评分系统

4. 灵活的使用方式
   - 单股票分析：get_factor()
   - 批量分析：analyze_batch()
   - 综合评分：get_comprehensive_score()

【提示】
- DuckDB数据库需预先下载历史数据
- 批量分析比单股票分析效率高10倍以上
- 推荐使用analyze_batch()进行多股票分析
"""

print(summary)

print("\n" + "=" * 90)
print(" " * 30 + "示例程序执行完成")
print("=" * 90)
