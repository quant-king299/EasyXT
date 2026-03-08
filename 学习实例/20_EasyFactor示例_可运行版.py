"""
EasyFactor 使用示例 - 可运行版本 (DuckDB版)

展示EasyFactor的主要功能
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from easy_xt.factor_library import EasyFactor, create_easy_factor
import pandas as pd

print("=" * 90)
print(" " * 30 + "EasyFactor 使用示例 (DuckDB版)")
print("=" * 90)

# 配置DuckDB数据库路径（请修改为你的实际路径）
DUCKDB_PATH = r'D:/StockData/stock_data.ddb'

# 创建EasyFactor实例
print("\n[步骤1] 创建EasyFactor实例...")
try:
    ef = create_easy_factor(DUCKDB_PATH)
    print("[OK] EasyFactor实例创建成功\n")
except Exception as e:
    print(f"[FAIL] EasyFactor初始化失败: {e}")
    print("\n[提示] 请修改DUCKDB_PATH变量为你的实际数据库路径")
    exit(1)

# 测试1：获取市场数据
print("=" * 90)
print("[步骤2] 获取市场数据")
print("=" * 90)
try:
    df = ef.get_market_data_ex(
        stock_code='000001.SZ',
        start_time='2024-01-01',
        end_time='2024-11-30',
        period='daily'
    )

    if not df.empty:
        print(f"[OK] 成功获取 {len(df)} 条日线数据\n")
        print("数据预览（最后5天）：")
        # 显示可用的列
        print(df[['date', 'open', 'high', 'low', 'close', 'volume']].tail())
    else:
        print("[FAIL] 数据为空")
except Exception as e:
    print(f"[FAIL] 获取市场数据失败: {e}")

# 测试2：计算动量因子
print("\n" + "=" * 90)
print("[步骤3] 计算动量因子")
print("=" * 90)
try:
    momentum = ef.get_factor('000001.SZ', 'momentum_20d', '2024-01-01', '2024-11-30')

    if not momentum.empty:
        val = momentum['momentum_20d'].iloc[-1]
        print(f"[OK] 20日动量: {val:+.2%}")
        if val > 0:
            print(f"     解读：近期上涨趋势，动量较强")
        else:
            print(f"     解读：近期下跌趋势，动量较弱\n")
    else:
        print("[FAIL] 动量因子为空\n")
except Exception as e:
    print(f"[FAIL] 计算动量因子失败: {e}\n")

# 测试3：计算RSI
print("=" * 90)
print("[步骤4] 计算RSI指标")
print("=" * 90)
try:
    rsi = ef.get_factor('000001.SZ', 'rsi', '2024-01-01', '2024-11-30')

    if not rsi.empty:
        val = rsi['rsi'].iloc[-1]
        print(f"[OK] RSI指标: {val:.2f}")
        if val > 70:
            print(f"     解读：超买区域，注意回调风险\n")
        elif val < 30:
            print(f"     解读：超卖区域，关注反弹机会\n")
        else:
            print(f"     解读：正常区域\n")
    else:
        print("[FAIL] RSI为空\n")
except Exception as e:
    print(f"[FAIL] 计算RSI失败: {e}\n")

# 测试4：计算波动率
print("=" * 90)
print("[步骤5] 计算波动率")
print("=" * 90)
try:
    volatility = ef.get_factor('000001.SZ', 'volatility_20d', '2024-01-01', '2024-11-30')

    if not volatility.empty:
        val = volatility['volatility_20d'].iloc[-1]
        print(f"[OK] 年化波动率: {val:.2%}")
        if val < 0.2:
            print(f"     解读：低波动率，走势平稳\n")
        elif val < 0.4:
            print(f"     解读：中等波动率\n")
        else:
            print(f"     解读：高波动率，风险较大\n")
    else:
        print("[FAIL] 波动率为空\n")
except Exception as e:
    print(f"[FAIL] 计算波动率失败: {e}\n")

# 测试5：批量获取因子
print("=" * 90)
print("[步骤6] 批量获取多只股票的因子")
print("=" * 90)
try:
    test_stocks = ['000001.SZ', '600000.SH', '600519.SH']
    factors = ef.get_factor_batch(
        stock_list=test_stocks,
        factor_names=['momentum_20d', 'rsi', 'volatility_20d'],
        start_date='2024-01-01',
        end_date='2024-11-30'
    )

    if 'momentum_20d' in factors and not factors['momentum_20d'].empty:
        print("[OK] 批量获取因子成功\n")
        print("20日动量排名：")
        momentum_df = factors['momentum_20d'].sort_values('momentum_20d', ascending=False)
        for _, row in momentum_df.iterrows():
            print(f"  {row['stock_code']}: {row['momentum_20d']:+.2%}")
        print()
    else:
        print("[FAIL] 批量因子为空\n")
except Exception as e:
    print(f"[FAIL] 批量获取因子失败: {e}\n")

# 测试6：获取股票列表
print("=" * 90)
print("[步骤7] 获取股票列表")
print("=" * 90)
try:
    stocks = ef.get_stock_list()

    if not stocks.empty:
        print(f"[OK] 获取股票列表成功，共 {len(stocks)} 只股票\n")
        print("股票列表预览：")
        print(stocks)
    else:
        print("[FAIL] 股票列表为空\n")
except Exception as e:
    print(f"[FAIL] 获取股票列表失败: {e}\n")

# 总结
print("\n" + "=" * 90)
print(" " * 35 + "总结")
print("=" * 90)

print("""
EasyFactor DuckDB版 主要功能：

1. get_market_data_ex()  - 获取市场数据
   支持：日线/周线/月线
   参数：stock_code, start_time, end_time, period
   注意：日期格式使用 YYYY-MM-DD（例如：2024-01-01）

2. get_factor()          - 计算单个因子
   支持的因子：
   - 动量：momentum_5d, momentum_10d, momentum_20d, momentum_60d
   - 反转：reversal_short, reversal_mid, reversal_long
   - 波动率：volatility_20d, volatility_60d, volatility_120d
   - 技术指标：rsi, macd, kdj, atr, obv, bollinger
   - 量价：volume_ratio, turnover_rate, amplitude

3. get_factor_batch()    - 批量获取因子
   参数：stock_list, factor_names, start_date, end_date

4. analyze_batch()       - 高效批量分析（推荐）
   参数：stock_list, start_date, end_date, factors

5. get_stock_list()      - 获取股票列表

6. get_comprehensive_score() - 多因子综合评分
   返回：score（得分）、rating（评级A/B/C/D）、rank（排名）

示例代码：
    # 初始化
    ef = EasyFactor(duckdb_path='D:/StockData/stock_data.ddb')

    # 获取市场数据（注意日期格式：YYYY-MM-DD）
    df = ef.get_market_data_ex('000001.SZ', '2024-01-01', '2024-12-31')

    # 计算因子
    momentum = ef.get_factor('000001.SZ', 'momentum_20d', '2024-01-01', '2024-12-31')
    rsi = ef.get_factor('000001.SZ', 'rsi', '2024-01-01', '2024-12-31')

    # 批量分析（高效）
    results = ef.analyze_batch(
        stock_list=['000001.SZ', '600000.SH'],
        start_date='2024-01-01',
        end_date='2024-12-31'
    )

特点：
- 基于DuckDB本地数据库，高性能批量计算
- 接口简洁，易于使用
- 支持50+类因子计算
- 适用于量化研究和策略开发
""")

print("=" * 90)
print(" " * 30 + "示例程序执行完成")
print("=" * 90)
