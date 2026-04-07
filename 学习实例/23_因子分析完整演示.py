# -*- coding: utf-8 -*-
"""
因子分析完整工作流演示（DuckDB真实数据版）
==============================================

本教程展示了完整的因子分析流程，从DuckDB读取真实股票数据到可视化报告生成。

涵盖内容：
-----------
1. 数据准备 - 从DuckDB读取真实股票数据
2. IC/IR分析 - 评估因子的预测能力和稳定性
3. 特质波动率计算 - 分解系统性风险和特质风险
4. 分组回测 - 检验分组收益的单调性
5. 绩效评估 - 计算夏普比率、最大回撤等指标
6. 可视化分析 - 生成6张专业图表

数据要求：
-----------
- 需要DuckDB数据库（stock_data.ddb）
- 数据库位置: D:/StockData/, C:/StockData/, E:/StockData/
- 如无数据，脚本会显示详细的下载指南

作者：101因子分析平台
"""

import sys
import os

# ============================================================
# 第一部分：路径设置
# ============================================================

script_dir = os.path.dirname(os.path.abspath(__file__))

# 尝试多种可能的路径
possible_roots = [
    os.path.normpath(os.path.join(script_dir, '..', '101因子', '101因子分析平台')),
    os.path.normpath(script_dir),
    os.path.normpath(os.path.join(script_dir, '101因子', '101因子分析平台')),
    os.path.normpath(os.path.join(os.path.dirname(script_dir), '101因子', '101因子分析平台')),
]

project_root = None
for root in possible_roots:
    if os.path.exists(os.path.join(root, 'src', 'analysis')):
        project_root = os.path.abspath(root)
        break

# 如果还是找不到，尝试向上查找
if project_root is None:
    current = script_dir
    for _ in range(3):
        current = os.path.dirname(current)
        if os.path.exists(os.path.join(current, 'src', 'analysis')):
            project_root = os.path.abspath(current)
            break

# 最后的备用方案
if project_root is None:
    project_root = os.path.abspath('.')

# 确保项目根目录在sys.path中
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ============================================================
# 第二部分：导入和依赖检查
# ============================================================

import pandas as pd
import numpy as np
import matplotlib
# 不设置后端，让matplotlib自动选择交互式后端（Windows会用TkAgg）
import matplotlib.pyplot as plt

# 设置中文字体（优先使用系统字体）
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 测试中文字体是否可用
try:
    plt.figure(figsize=(1, 1))
    plt.text(0.5, 0.5, '测试中文', fontsize=12)
    plt.close()
    print("[OK] 中文字体设置成功")
except Exception as e:
    print(f"[WARN] 中文字体设置失败: {e}")
    # 如果中文字体失败，使用英文标签
    USE_CHINESE = False
else:
    USE_CHINESE = True

print("=" * 80)
print(" " * 20 + "因子分析完整工作流演示（DuckDB真实数据）")
print("=" * 80)
print("\n[提示] 每张图生成后会弹出显示窗口，关闭窗口后继续下一步")

print("=" * 80)
print(" " * 20 + "因子分析完整工作流演示（DuckDB真实数据）")
print("=" * 80)

# 依赖检查
print("\n[检查依赖...]")
missing_deps = []

try:
    import duckdb
    print("  [OK] duckdb")
except ImportError:
    missing_deps.append("duckdb")
    print("  [缺少] duckdb - 请运行: pip install duckdb")

try:
    from src.analysis.group_backtest import GroupBacktestEngine
    from src.analysis.visualization import FactorAnalysisVisualizer
    print("  [OK] src.analysis")
except ImportError as e:
    print(f"  [警告] 导入失败: {e}")

try:
    from src.analysis.enhanced_performance import EnhancedPerformanceAnalyzer
    print("  [OK] src.analysis.enhanced_performance")
except ImportError:
    print("  [提示] enhanced_performance不可用，将跳过部分功能")

try:
    from src.factor_engine.specific_volatility import SpecificVolatilityCalculator
    print("  [OK] src.factor_engine.specific_volatility")
except ImportError:
    print("  [提示] specific_volatility不可用，将跳过特质波动率计算")

if missing_deps:
    print(f"\n[错误] 缺少必要的依赖: {', '.join(missing_deps)}")
    print("\n请运行以下命令安装:")
    print(f"  pip install {' '.join(missing_deps)}")
    sys.exit(1)

print("  [OK] 所有核心依赖已安装")

# ============================================================
# 第三部分：数据准备（从DuckDB读取真实数据）
# ============================================================

print("\n[步骤1] 准备数据 - 从DuckDB读取真实股票数据")
print("-" * 80)

# 检测DuckDB数据库路径
def detect_duckdb_path():
    """自动检测DuckDB数据库路径"""
    candidates = [
        'D:/StockData/stock_data.ddb',
        'C:/StockData/stock_data.ddb',
        'E:/StockData/stock_data.ddb',
        './data/stock_data.ddb',
        os.path.join(project_root, 'data', 'stock_data.ddb'),
    ]

    for path in candidates:
        if os.path.exists(path):
            return path

    # 环境变量
    env = os.environ.get('DUCKDB_PATH')
    if env and os.path.exists(env):
        return env

    return None

# 检查数据库是否存在
duckdb_path = detect_duckdb_path()

if duckdb_path is None:
    print("\n[错误] 未找到DuckDB数据库文件！")
    print("\n" + "="*80)
    print("如何下载股票数据到DuckDB")
    print("="*80)

    print("\n方法1: 使用QMT/xtquant下载（推荐）")
    print("-"*80)
    print("1. 安装QMT交易软件")
    print("2. 运行: python scripts/download_stocks.py")
    print("3. 数据自动保存到DuckDB数据库")

    print("\n方法2: 创建最小测试数据库")
    print("-"*80)
    print("运行以下Python代码:")
    print("""
    import pandas as pd
    import duckdb
    import numpy as np

    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=500, freq='D')
    stocks = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '600519.SH']

    data = []
    np.random.seed(42)
    for stock in stocks:
        for date in dates:
            price = 10 + np.random.randn() * 2
            data.append({
                'date': date,
                'stock_code': stock,
                'open': price * (1 + np.random.randn() * 0.01),
                'high': price * (1 + abs(np.random.randn() * 0.02)),
                'low': price * (1 - abs(np.random.randn() * 0.02)),
                'close': price,
                'volume': np.random.randint(1000000, 10000000)
            })

    df = pd.DataFrame(data)
    conn = duckdb.connect('data/stock_data.ddb')
    conn.execute('CREATE TABLE stock_daily AS SELECT * FROM df')
    conn.close()
    print("测试数据库已创建: data/stock_data.ddb")
    """)

    print("\n方法3: 使用Tushare数据源")
    print("-"*80)
    print("1. 注册账号: https://tushare.pro")
    print("2. 获取API Token")
    print("3. 运行Tushare下载脚本")

    print("\n" + "="*80)
    print("数据准备完成后，请重新运行此脚本")
    print("="*80)
    sys.exit(1)

print(f"[OK] 找到DuckDB数据库: {duckdb_path}")

# 从DuckDB读取数据
print("\n从DuckDB读取股票数据...")

try:
    conn = duckdb.connect(duckdb_path)

    # 查询数据统计
    stats_query = """
    SELECT COUNT(*) as total,
           MIN(date) as start_date,
           MAX(date) as end_date,
           COUNT(DISTINCT stock_code) as n_stocks
    FROM stock_daily
    WHERE date >= '2023-01-01' AND date <= '2023-12-31'
    """
    stats = conn.execute(stats_query).fetchdf()

    n_stocks_total = stats['n_stocks'].iloc[0]
    total_records = stats['total'].iloc[0]
    start_date = stats['start_date'].iloc[0]
    end_date = stats['end_date'].iloc[0]

    print(f"[数据统计] 数据库共有 {n_stocks_total:,.0f} 只股票")
    print(f"           分析时间范围: 2023年全年")
    print(f"           可用记录数: {total_records:,.0f}")

    # 选择部分股票进行分析（选择100只股票以加快速度）
    print("\n选择100只股票进行分析...")

    # 读取数据 - 使用2023年全年数据
    data_query = """
    SELECT date, stock_code, close,
           LAG(close, 1) OVER (PARTITION BY stock_code ORDER BY date) as prev_close
    FROM (
        SELECT * FROM stock_daily
        WHERE stock_code IN (
            SELECT DISTINCT stock_code FROM stock_daily
            WHERE date >= '2023-01-01' AND date <= '2023-12-31'
            LIMIT 100
        )
        AND date >= '2023-01-01' AND date <= '2023-12-31'
    )
    QUALIFY prev_close IS NOT NULL
    ORDER BY stock_code, date
    """

    df_raw = conn.execute(data_query).fetchdf()
    conn.close()

    if df_raw.empty:
        print("[错误] 未读取到数据，请检查数据库中的数据")
        sys.exit(1)

    # 计算收益率
    df_raw['return'] = df_raw['close'] / df_raw['prev_close'] - 1

    # 计算一个简单的动量因子作为演示（5日收益率，避免与1日收益率高度相关）
    # 注意：不要使用过长的窗口，否则因子会和收益高度相关
    df_raw['factor'] = df_raw.groupby('stock_code')['close'].transform(
        lambda x: x.pct_change(5)  # 使用5日而不是20日
    )

    # 删除缺失值
    df_raw = df_raw.dropna()
    df = df_raw[['date', 'stock_code', 'factor', 'return']].copy()

    # 数据验证：检查因子和收益的相关性
    correlation = df['factor'].corr(df['return'])
    print(f"\n[数据验证] 因子与收益率相关系数: {correlation:.4f}")
    if abs(correlation) > 0.95:
        print(f"[警告] 相关系数过高({correlation:.4f})，因子和收益几乎完全相关！")
        print(f"        这会导致IC分析失效，请检查因子计算逻辑")

    # 检查数据量
    n_dates = df['date'].nunique()
    if n_dates < 20:
        print(f"[警告] 交易日数太少({n_dates}个)，IC分析结果可能不可靠")
        print(f"        建议至少需要60个交易日（约3个月）的数据")

    print(f"[OK] 数据读取完成: {len(df):,} 条记录")
    print(f"  分析股票数: {df['stock_code'].nunique()}")
    print(f"  日期范围: {df['date'].min()} 至 {df['date'].max()}")
    print(f"  平均收益率: {df['return'].mean():.4%}")

    # 检查数据相关性（调试信息）
    print(f"\n[DEBUG] 数据相关性检查:")
    print(f"  因子值范围: [{df['factor'].min():.4f}, {df['factor'].max():.4f}]")
    print(f"  收益率范围: [{df['return'].min():.4f}, {df['return'].max():.4f}]")
    print(f"  因子标准差: {df['factor'].std():.4f}")
    print(f"  收益率标准差: {df['return'].std():.4f}")
    print(f"  唯一日期数: {df['date'].nunique()}")
    print(f"  每只股票平均记录数: {len(df) / df['stock_code'].nunique():.1f}")

    # 检查是否有重复数据或异常相关性
    if df['factor'].std() < 1e-10 or df['return'].std() < 1e-10:
        print("\n[警告] 数据标准差接近0，可能导致IC计算异常！")
        print(f"  因子值可能全部相同，样本量过小或数据有问题")

    # 如果数据量太少，给出警告
    if df['date'].nunique() < 10:
        print(f"\n[错误] 数据量不足！只有{df['date'].nunique()}个交易日，无法进行有效的IC分析")
        print("        建议至少需要20个交易日以上的数据")
        sys.exit(1)

except Exception as e:
    print(f"[错误] DuckDB读取失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================
# 第四部分：IC/IR分析
# ============================================================

print("\n" + "=" * 80)
print("[步骤2] IC/IR分析 - 评估因子预测能力")
print("=" * 80)

from src.analysis.group_backtest import GroupBacktestEngine
from src.analysis.visualization import FactorAnalysisVisualizer

# 创建引擎实例
engine = GroupBacktestEngine()
visualizer = FactorAnalysisVisualizer()

print("\n运行快速IC测试...")

# 准备因子数据和收益率数据（分别传入）
factor_df = df[['date', 'stock_code', 'factor']].copy()
returns_df = df[['date', 'stock_code', 'return']].copy()
returns_df = returns_df.rename(columns={'return': 'ret'})  # 重命名为ret

print(f"[DEBUG] 因子数据: {factor_df.shape}, 因子范围: [{factor_df['factor'].min():.4f}, {factor_df['factor'].max():.4f}]")
print(f"[DEBUG] 收益数据: {returns_df.shape}, 收益范围: [{returns_df['ret'].min():.4f}, {returns_df['ret'].max():.4f}]")

ic_result = engine.quick_ic_test(factor_df, returns_df)

# 显示IC统计结果
print("\n[IC统计结果]")
abs_ic = abs(ic_result['ic_mean'])
ic_ir = ic_result['ic_ir']

print(f"  IC均值:     {ic_result['ic_mean']:.4f}", end="")
if abs_ic > 0.05:
    print("  [优秀] 强预测能力")
elif abs_ic > 0.03:
    print("  [良好] 较强预测能力")
elif abs_ic > 0.02:
    print("  [一般] 有一定预测能力")
else:
    print("  [较弱] 预测能力较弱")

print(f"  IC标准差:   {ic_result['ic_std']:.4f}")
print(f"  IC_IR:      {ic_result['ic_ir']:.4f}", end="")
if ic_ir > 1.0:
    print("  [优秀] 稳定性优秀")
elif ic_ir > 0.5:
    print("  [良好] 稳定性良好")
elif ic_ir > 0.3:
    print("  [一般] 稳定性一般")
else:
    print("  [较差] 稳定性较差")

print(f"  IC绝对值均值: {ic_result['ic_abs_mean']:.4f}")
print(f"  t统计量:    {ic_result['t_stat']:.4f}")
print(f"  p值:        {ic_result['p_value']:.4f}")
print(f"  IC为正比例:  {ic_result['ic_positive_ratio']:.2%}")

# 生成IC可视化图表
print("\n生成IC分析图表...")

# 图1: IC时序图（带正负柱状）
print("  [1/2] 生成IC时序图...")
fig_ic = visualizer.plot_ic_analysis(
    ic_result['ic_series'],
    factor_name="动量因子（20日收益率）"
)
fig_ic.savefig('demo_ic_analysis.png', dpi=150, bbox_inches='tight')
print("       [OK] 已保存: demo_ic_analysis.png")
print("       [提示] 正在显示图表，关闭窗口后继续...")
plt.show()

# 图2: IC统计综合图（4子图）
print("  [2/2] 生成IC统计综合图...")
fig_stats, axes = plt.subplots(2, 2, figsize=(14, 10))

ic_clean = ic_result['ic_series'].dropna()

# 子图1: IC分布直方图
axes[0, 0].hist(ic_clean, bins=40, density=True, alpha=0.7,
                color='steelblue', edgecolor='black')
axes[0, 0].axvline(x=ic_result['ic_mean'], color='red',
                   linestyle='--', linewidth=2, label=f"均值={ic_result['ic_mean']:.4f}")
axes[0, 0].axvline(x=0, color='black', linestyle='-', linewidth=0.5)
axes[0, 0].set_title('IC分布直方图', fontsize=12, fontweight='bold')
axes[0, 0].set_xlabel('IC值')
axes[0, 0].set_ylabel('密度')
axes[0, 0].legend()
axes[0, 0].grid(True, alpha=0.3)

# 子图2: IC时序图
axes[0, 1].plot(ic_clean.index, ic_clean.values, linewidth=1,
                color='steelblue', alpha=0.8)
axes[0, 1].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
axes[0, 1].axhline(y=ic_result['ic_mean'], color='red',
                   linestyle='--', linewidth=1.5, label=f"均值={ic_result['ic_mean']:.4f}")
axes[0, 1].fill_between(ic_clean.index, 0, ic_clean.values,
                        where=ic_clean.values >= 0, color='red', alpha=0.3, label='正IC')
axes[0, 1].fill_between(ic_clean.index, 0, ic_clean.values,
                        where=ic_clean.values < 0, color='green', alpha=0.3, label='负IC')
axes[0, 1].set_title('IC时序图', fontsize=12, fontweight='bold')
axes[0, 1].set_ylabel('IC值')
axes[0, 1].legend(loc='upper left', fontsize=8)
axes[0, 1].grid(True, alpha=0.3)

# 子图3: 累计IC图
cumulative_ic = ic_clean.cumsum()
axes[1, 0].plot(cumulative_ic.index, cumulative_ic.values,
                linewidth=2, color='darkblue')
axes[1, 0].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
axes[1, 0].set_title('累计IC', fontsize=12, fontweight='bold')
axes[1, 0].set_ylabel('累计IC')
axes[1, 0].grid(True, alpha=0.3)

# 子图4: IC统计摘要文本
# 确保中文字体设置
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 使用英文标签避免编码问题
stats_text = f"""
IC Statistics Summary
══════════════════════
IC Mean:     {ic_result['ic_mean']:.4f}
IC Std Dev:  {ic_result['ic_std']:.4f}
IC IR:       {ic_result['ic_ir']:.4f}
IC Abs Mean: {ic_result['ic_abs_mean']:.4f}
t-statistic: {ic_result['t_stat']:.2f}
p-value:     {ic_result['p_value']:.4f}
IC>0 Ratio:  {ic_result['ic_positive_ratio']:.1%}

══════════════════════
Prediction: {'Excellent' if abs_ic > 0.05 else 'Good' if abs_ic > 0.03 else 'Fair'}
Stability:  {'Excellent' if ic_ir > 1.0 else 'Good' if ic_ir > 0.5 else 'Fair'}
"""
axes[1, 1].text(0.1, 0.5, stats_text, fontsize=11,
                verticalalignment='center', family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
axes[1, 1].axis('off')
axes[1, 1].set_title('IC Statistics Summary', fontsize=12, fontweight='bold')

plt.tight_layout()
fig_stats.savefig('demo_ic_statistics.png', dpi=150, bbox_inches='tight')
print("       [OK] 已保存: demo_ic_statistics.png")
print("       [提示] 正在显示图表，关闭窗口后继续...")
plt.show()

# ============================================================
# 第五部分：特质波动率计算
# ============================================================

print("\n" + "=" * 80)
print("[步骤3] 特质波动率计算")
print("=" * 80)

try:
    from src.factor_engine.specific_volatility import SpecificVolatilityCalculator

    calculator = SpecificVolatilityCalculator(window=20)

    # 计算市场收益（等权平均）
    market_returns = df.groupby('date')['return'].mean()

    # 选择部分股票演示
    demo_stocks = df['stock_code'].unique()[:5]
    print(f"\n计算 {len(demo_stocks)} 只股票的特质波动率:")

    for stock in demo_stocks:
        stock_returns = df[df['stock_code'] == stock].set_index('date')['return']
        spec_vol = calculator.calculate_specific_volatility(
            stock_returns,
            market_returns,
            window=20
        )

        if not spec_vol.empty:
            avg_vol = spec_vol.mean()
            print(f"  {stock}: {avg_vol:.2%} (平均特质波动率)")
        else:
            print(f"  {stock}: 数据不足")

except Exception as e:
    print(f"[提示] 特质波动率计算跳过: {e}")

# ============================================================
# 第六部分：分组回测
# ============================================================

print("\n" + "=" * 80)
print("[步骤4] 分组回测 - 检验因子有效性")
print("=" * 80)

# 准备回测数据
factor_df = df[['date', 'stock_code', 'factor']].copy()
returns_df = df[['date', 'stock_code', 'return']].copy()

print("\n运行分组回测...")
print("  分组数: 5")
print("  调仓频率: 月度")
print("  手续费: 0.025%")
print("  滑点: 0.1%")

backtest_result = engine.run_backtest(
    factor_data=factor_df,
    returns_data=returns_df,
    n_groups=5,
    freq='monthly',
    commission=0.00025,
    slippage=0.001
)

n_periods = backtest_result['backtest_results']['n_periods']
print(f"\n[OK] 回测完成，共 {n_periods} 个调仓期")

# 显示分组收益统计
if 'group_returns' in backtest_result['backtest_results']:
    group_returns = backtest_result['backtest_results']['group_returns']

    if not group_returns.empty:
        print("\n[分组收益统计]")

        # 计算累计收益
        cumulative = (1 + group_returns).cumprod()

        print("\n各组累计收益和年化收益:")
        print(f"{'分组':<8} {'累计收益':<12} {'年化收益':<12}")
        print("-" * 35)

        for col in cumulative.columns:
            final_value = cumulative[col].iloc[-1]
            annual_ret = group_returns[col].mean() * 252
            print(f"{col:<8} {final_value:>10.2%}     {annual_ret:>10.2%}")

        # 检验单调性
        print("\n[单调性检验]")
        group_annual = [group_returns[col].mean() * 252 for col in cumulative.columns]
        is_monotonic = all(group_annual[i] <= group_annual[i+1] for i in range(len(group_annual)-1))

        if is_monotonic:
            print("  [OK] 分组收益呈现单调性，因子有效")
        else:
            print("  [INFO] 分组收益未完全呈现单调性，需进一步分析")

# ============================================================
# 第七部分：绩效评估
# ============================================================

print("\n" + "=" * 80)
print("[步骤5] 绩效评估 - 计算策略表现指标")
print("=" * 80)

try:
    from src.analysis.enhanced_performance import EnhancedPerformanceAnalyzer

    analyzer = EnhancedPerformanceAnalyzer()

    # 构建多空策略收益
    print("\n构建多空策略收益...")

    # 找出因子值最高和最低的股票
    high_factor_stocks = df.groupby('stock_code')['factor'].mean().nlargest(10).index
    low_factor_stocks = df.groupby('stock_code')['factor'].mean().nsmallest(10).index

    # 计算每日多空收益
    long_short_returns = []
    for date in df['date'].unique():
        daily_data = df[df['date'] == date]
        long_ret = daily_data[daily_data['stock_code'].isin(high_factor_stocks)]['return'].mean()
        short_ret = daily_data[daily_data['stock_code'].isin(low_factor_stocks)]['return'].mean()
        long_short_returns.append(long_ret - short_ret)

    ls_series = pd.Series(long_short_returns, index=df['date'].unique())

    # 计算基准收益（等权市场组合）
    benchmark_returns = df.groupby('date')['return'].mean()

    # 计算绩效指标
    metrics = analyzer.calculate_performance_metrics(ls_series, benchmark_returns)

    print("\n[多空策略绩效指标]")
    print(f"{'指标':<20} {'值'}")
    print("-" * 35)
    print(f"{'总收益':<20} {metrics['total_return']:>12.2%}")
    print(f"{'年化收益':<20} {metrics['annual_return']:>12.2%}")
    print(f"{'年化波动率':<20} {metrics['annual_volatility']:>12.2%}")
    print(f"{'夏普比率':<20} {metrics['sharpe_ratio']:>12.4f}")
    print(f"{'Sortino比率':<20} {metrics['sortino_ratio']:>12.4f}")
    print(f"{'Calmar比率':<20} {metrics['calmar_ratio']:>12.4f}")
    print(f"{'最大回撤':<20} {metrics['max_drawdown']:>12.2%}")
    print(f"{'胜率':<20} {metrics['win_rate']:>12.2%}")

    # 评价
    print("\n[绩效评价]")
    if metrics['sharpe_ratio'] > 2:
        print("  [优秀] 夏普比率>2，策略表现优秀")
    elif metrics['sharpe_ratio'] > 1:
        print("  [良好] 夏普比率>1，策略表现良好")
    elif metrics['sharpe_ratio'] > 0.5:
        print("  [一般] 夏普比率>0.5，策略表现一般")
    else:
        print("  [较差] 夏普比率<0.5，策略需要优化")

    if metrics['max_drawdown'] < 0.1:
        print("  [优秀] 最大回撤<10%，风险控制良好")
    elif metrics['max_drawdown'] < 0.2:
        print("  [良好] 最大回撤<20%，风险控制尚可")
    else:
        print("  [WARN] 最大回撤>20%，需加强风险控制")

except Exception as e:
    print(f"[提示] 绩效评估跳过: {e}")
    # 创建简单的绩效指标
    high_factor_stocks = df.groupby('stock_code')['factor'].mean().nlargest(10).index
    low_factor_stocks = df.groupby('stock_code')['factor'].mean().nsmallest(10).index

    long_short_returns = []
    for date in df['date'].unique():
        daily_data = df[df['date'] == date]
        long_ret = daily_data[daily_data['stock_code'].isin(high_factor_stocks)]['return'].mean()
        short_ret = daily_data[daily_data['stock_code'].isin(low_factor_stocks)]['return'].mean()
        long_short_returns.append(long_ret - short_ret)

    ls_series = pd.Series(long_short_returns, index=df['date'].unique())
    benchmark_returns = df.groupby('date')['return'].mean()

    # 简单计算
    total_return = (1 + ls_series).prod() - 1
    annual_return = ls_series.mean() * 252
    annual_vol = ls_series.std() * np.sqrt(252)
    sharpe = annual_return / annual_vol if annual_vol > 0 else 0

    cumulative = (1 + ls_series).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_dd = drawdown.min()

    metrics = {
        'total_return': total_return,
        'annual_return': annual_return,
        'annual_volatility': annual_vol,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_dd,
        'win_rate': (ls_series > 0).mean()
    }

    print("\n[多空策略绩效指标（简化版）]")
    print(f"  总收益: {metrics['total_return']:.2%}")
    print(f"  年化收益: {metrics['annual_return']:.2%}")
    print(f"  夏普比率: {metrics['sharpe_ratio']:.4f}")
    print(f"  最大回撤: {metrics['max_drawdown']:.2%}")

# ============================================================
# 第八部分：可视化分析
# ============================================================

print("\n" + "=" * 80)
print("[步骤6] 可视化分析 - 生成专业图表")
print("=" * 80)

# 图1: 净值曲线对比
print("\n生成净值曲线图...")
fig_nav, ax = plt.subplots(figsize=(14, 7))

# 计算累计净值
cumulative_ls = (1 + ls_series).cumprod()
cumulative_bench = (1 + benchmark_returns).cumprod()

# 绘制曲线
ax.plot(cumulative_ls.index, cumulative_ls.values,
        label='多空策略', linewidth=2.5, color='#2E86AB')
ax.plot(cumulative_bench.index, cumulative_bench.values,
        label='基准（等权市场）', linewidth=2, color='#A23B72', linestyle='--')

# 标注最大回撤
running_max = cumulative_ls.expanding().max()
drawdown = (cumulative_ls - running_max) / running_max
max_dd_idx = drawdown.idxmin()
peak_idx = cumulative_ls[:max_dd_idx].idxmax()

ax.scatter([peak_idx, max_dd_idx],
           [cumulative_ls.loc[peak_idx], cumulative_ls.loc[max_dd_idx]],
           color='red', s=100, zorder=5)
ax.annotate('', xy=(max_dd_idx, cumulative_ls.loc[max_dd_idx]),
            xytext=(peak_idx, cumulative_ls.loc[peak_idx]),
            arrowprops=dict(arrowstyle='->', color='red', lw=1.5))

# 设置标题和标签
ax.set_title('多空策略净值曲线', fontsize=16, fontweight='bold', pad=15)
ax.set_xlabel('日期', fontsize=12)
ax.set_ylabel('净值', fontsize=12)
ax.legend(loc='best', fontsize=11)
ax.grid(True, alpha=0.3)

# 添加绩效摘要文本
info_text = f"""
策略绩效
━━━━━━━━━
年化收益: {metrics['annual_return']:.2%}
夏普比率: {metrics['sharpe_ratio']:.2f}
最大回撤: {metrics['max_drawdown']:.2%}
"""
ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
        fontsize=10, verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
fig_nav.savefig('demo_nav_curve.png', dpi=150, bbox_inches='tight')
print("  [OK] 已保存: demo_nav_curve.png")
print("  [提示] 正在显示图表，关闭窗口后继续...")
plt.show()

# 图2: 分组收益对比
if 'group_returns' in backtest_result['backtest_results']:
    group_returns = backtest_result['backtest_results']['group_returns']
    if not group_returns.empty:
        print("\n生成分组收益对比图...")
        fig_groups = visualizer.plot_group_backtest(
            group_returns,
            None,
            factor_name="动量因子"
        )
        fig_groups.savefig('demo_group_returns.png', dpi=150, bbox_inches='tight')
        print("  [OK] 已保存: demo_group_returns.png")
        print("  [提示] 正在显示图表，关闭窗口后继续...")
        plt.show()

# 图3: 回撤图
print("\n生成回撤分析图...")
fig_dd, ax = plt.subplots(figsize=(14, 6))

# 计算回撤序列
cumulative = (1 + ls_series).cumprod()
running_max = cumulative.expanding().max()
drawdown = (cumulative - running_max) / running_max

# 绘制回撤
ax.fill_between(drawdown.index, drawdown.values, 0,
                where=drawdown.values < 0, color='red', alpha=0.3)
ax.plot(drawdown.index, drawdown.values, color='darkred', linewidth=1.5)

# 标注最大回撤
ax.scatter([max_dd_idx], [drawdown.loc[max_dd_idx]],
           color='darkred', s=150, zorder=5, marker='v')
ax.annotate(f'最大回撤: {metrics["max_drawdown"]:.2%}',
            xy=(max_dd_idx, drawdown.loc[max_dd_idx]),
            xytext=(10, 10), textcoords='offset points',
            fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7),
            arrowprops=dict(arrowstyle='->', color='black', lw=1.5))

ax.set_title('策略回撤分析', fontsize=16, fontweight='bold', pad=15)
ax.set_xlabel('日期', fontsize=12)
ax.set_ylabel('回撤幅度', fontsize=12)
ax.grid(True, alpha=0.3)
ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

plt.tight_layout()
fig_dd.savefig('demo_drawdown.png', dpi=150, bbox_inches='tight')
print("  [OK] 已保存: demo_drawdown.png")
print("  [提示] 正在显示图表，关闭窗口后继续...")
plt.show()

# ============================================================
# 第九部分：生成综合报告
# ============================================================

print("\n" + "=" * 80)
print("[步骤7] 生成综合分析报告")
print("=" * 80)

# 计算综合评分
score = 0
if abs_ic > 0.05: score += 25
elif abs_ic > 0.03: score += 15
elif abs_ic > 0.02: score += 5

if ic_ir > 1.0: score += 25
elif ic_ir > 0.5: score += 15
elif ic_ir > 0.3: score += 5

if metrics['sharpe_ratio'] > 2: score += 25
elif metrics['sharpe_ratio'] > 1: score += 15
elif metrics['sharpe_ratio'] > 0.5: score += 5

if metrics['max_drawdown'] < 0.1: score += 25
elif metrics['max_drawdown'] < 0.2: score += 15
elif metrics['max_drawdown'] < 0.3: score += 5

report = f"""
{'='*80}
                    因子分析综合报告
{'='*80}

数据来源: DuckDB真实股票数据
分析时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

一、数据概况
{'─'*80}
  股票数量: {df['stock_code'].nunique()}
  记录数量: {len(df):,}
  日期范围: {df['date'].min()} 至 {df['date'].max()}
  数据来源: {duckdb_path}

二、IC/IR分析
{'─'*80}
IC均值:        {ic_result['ic_mean']:.4f}  {'[优秀]' if abs_ic > 0.05 else '[良好]' if abs_ic > 0.03 else '[一般]'}
IC标准差:      {ic_result['ic_std']:.4f}
IC_IR:         {ic_result['ic_ir']:.4f}  {'[优秀]' if ic_ir > 1.0 else '[良好]' if ic_ir > 0.5 else '[一般]'}
IC绝对值均值:  {ic_result['ic_abs_mean']:.4f}
t统计量:       {ic_result['t_stat']:.2f}
p值:           {ic_result['p_value']:.4f}
IC为正比例:    {ic_result['ic_positive_ratio']:.1%}

三、多空策略绩效
{'─'*80}
年化收益:      {metrics['annual_return']:.2%}
年化波动率:    {metrics['annual_volatility']:.2%}
夏普比率:      {metrics['sharpe_ratio']:.4f}
最大回撤:      {metrics['max_drawdown']:.2%}
胜率:          {metrics['win_rate']:.2%}

四、分组回测结果
{'─'*80}
"""

if 'group_returns' in backtest_result['backtest_results']:
    group_returns = backtest_result['backtest_results']['group_returns']
    if not group_returns.empty:
        report += "\n各组年化收益:\n"
        for col in group_returns.columns:
            annual_ret = group_returns[col].mean() * 252
            report += f"  {col}: {annual_ret:.2%}\n"

report += f"""
五、综合评估
{'─'*80}
综合得分: {score}/100

"""

if score >= 80:
    report += "评价: [优秀] 这是一个非常优秀的因子，建议深入研究\n"
elif score >= 60:
    report += "评价: [良好] 这是一个良好的因子，可以考虑使用\n"
elif score >= 40:
    report += "评价: [一般] 因子效果一般，建议优化后再使用\n"
else:
    report += "评价: [较差] 因子效果较差，不建议使用\n"

report += f"""
{'='*80}
101因子分析平台
生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*80}
"""

print(report)

# 保存报告
with open('factor_analysis_report.txt', 'w', encoding='utf-8') as f:
    f.write(report)
print("\n[OK] 报告已保存到: factor_analysis_report.txt")

# ============================================================
# 第十部分：总结
# ============================================================

print("\n" + "=" * 80)
print(" " * 30 + "分析完成！")
print("=" * 80)

print("\n[生成的文件]")
print("  1. demo_ic_analysis.png    - IC时序分析图")
print("  2. demo_ic_statistics.png  - IC统计综合图（4子图）")
print("  3. demo_nav_curve.png      - 净值曲线图")
print("  4. demo_group_returns.png  - 分组收益对比图")
print("  5. demo_drawdown.png       - 回撤分析图")
print("  6. factor_analysis_report.txt - 综合分析报告")

print("\n[核心结论]")
print(f"  1. 因子预测能力: IC={ic_result['ic_mean']:.4f} ({'优秀' if abs_ic > 0.05 else '良好' if abs_ic > 0.03 else '一般'})")
print(f"  2. 因子稳定性: IR={ic_result['ic_ir']:.4f} ({'优秀' if ic_ir > 1.0 else '良好' if ic_ir > 0.5 else '一般'})")
print(f"  3. 策略年化收益: {metrics['annual_return']:.2%}")
print(f"  4. 夏普比率: {metrics['sharpe_ratio']:.4f}")
print(f"  5. 最大回撤: {metrics['max_drawdown']:.2%}")
print(f"  6. 综合评分: {score}/100")

print("\n[如何使用你自己的数据]")
print()
print("本脚本使用DuckDB数据库中的真实股票数据。数据来源：")
print()
print("方法1: 使用QMT/xtquant下载（推荐）")
print("  1. 安装QMT交易软件")
print("  2. 运行: python scripts/download_stocks.py")
print("  3. 数据自动保存到DuckDB数据库")
print()
print("方法2: 使用Tushare数据源")
print("  1. 注册账号: https://tushare.pro")
print("  2. 修改scripts/中的Tushare下载脚本")
print("  3. 运行下载数据到DuckDB")
print()
print("方法3: 使用自己的CSV文件")
print("  1. 准备包含以下列的CSV文件:")
print("     - date: 交易日期")
print("     - stock_code: 股票代码")
print("     - open, high, low, close, volume: OHLCV数据")
print()
print("  2. 使用以下代码导入到DuckDB:")
print("     ```python")
print("     import pandas as pd")
print("     import duckdb")
print()
print("     df = pd.read_csv('your_data.csv')")
print("     conn = duckdb.connect('data/stock_data.ddb')")
print("     conn.execute('CREATE TABLE stock_daily AS SELECT * FROM df')")
print("     conn.close()")
print("     ```")
print()
print("  4. 重新运行本脚本")
print()
print("数据要求:")
print("  - 时间范围: 至少1年历史数据")
print("  - 股票数量: 至少20只")
print("  - 数据频率: 日线数据")
print("  - 必须字段: date, stock_code, close")

print("\n[进一步学习]")
print("  - IC分析详解: docs/ic_integration_guide.md")
print("  - 分组回测: src/analysis/group_backtest.py")
print("  - 特质波动率: src/factor_engine/specific_volatility.py")
print("  - 绩效评估: src/analysis/enhanced_performance.py")

print("\n" + "=" * 80)
