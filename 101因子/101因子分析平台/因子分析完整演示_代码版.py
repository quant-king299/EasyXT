"""
101因子分析完整演示 - 代码实现版本
相当于学习案例23的功能
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

import pandas as pd
import numpy as np

def complete_factor_analysis_demo():
    """完整的因子分析演示"""

    print("=" * 80)
    print(" " * 20 + "101因子分析完整演示")
    print("=" * 80)

    # ========================================
    # 步骤1: 数据加载
    # ========================================
    print("\n[步骤1] 数据加载")
    print("-" * 80)

    from src.easyxt_adapter.data_loader import EasyXTDataLoader

    # 配置参数
    symbols = ['600519.SH', '000858.SZ', '600036.SH', '000002.SZ', '601318.SH',
               '600030.SH', '000333.SZ', '600276.SH', '000001.SZ', '600000.SH']

    start_date = '2023-01-01'
    end_date = '2023-12-31'

    print(f"股票池: {symbols}")
    print(f"时间范围: {start_date} 到 {end_date}")

    # 加载数据
    data_loader = EasyXTDataLoader()
    data = data_loader.load_data(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        fields=['open', 'high', 'low', 'close', 'volume']
    )

    print(f"✅ 数据加载成功: {data.shape}")
    print(f"  交易日: {data.index.get_level_values(0).nunique()}天")
    print(f"  股票: {data.index.get_level_values(1).nunique()}只")

    # ========================================
    # 步骤2: 因子计算
    # ========================================
    print("\n[步骤2] 因子计算")
    print("-" * 80)

    from src.factor_engine.alpha101 import Alpha101Factors

    # 创建因子计算器
    factor_calculator = Alpha101Factors(data)

    # 计算单个因子（以alpha001为例）
    factor_name = 'alpha001'
    print(f"计算因子: {factor_name}")

    factor_data = factor_calculator.calculate_single_factor(
        factor_name=factor_name,
        data=data
    )

    if factor_data is not None and not factor_data.empty:
        print(f"✅ 因子计算成功: {factor_data.shape}")
        print(f"  因子统计: mean={factor_data.mean():.4f}, std={factor_data.std():.4f}")
        print(f"  有效数据: {factor_data.notna().sum()}个")
    else:
        print("❌ 因子计算失败")
        return

    # ========================================
    # 步骤3: IC分析
    # ========================================
    print("\n[步骤3] IC分析")
    print("-" * 80)

    from src.analysis.ic_analysis import ICAnalysis

    # 创建IC分析器
    ic_analyzer = ICAnalysis()

    # 准备收益率数据
    returns_data = data[['returns']].copy()

    # 计算IC序列
    print("计算IC序列...")
    ic_series = ic_analyzer.calculate_ic(factor_data, returns_data)

    # 计算IC统计
    ic_stats = ic_analyzer.calculate_ic_stats(ic_series)

    print(f"✅ IC分析完成:")
    print(f"  IC均值: {ic_stats['ic_mean']:.4f}")
    print(f"  IC标准差: {ic_stats['ic_std']:.4f}")
    print(f"  IC_IR: {ic_stats['ic_ir']:.4f}")
    print(f"  IC绝对值均值: {ic_stats['ic_abs_mean']:.4f}")
    print(f"  t统计量: {ic_stats['t_stat']:.4f}")
    print(f"  p值: {ic_stats['p_value']:.4f}")
    print(f"  IC为正比例: {ic_stats['ic_prob']:.2%}")

    # IC评估
    print(f"\n[因子评估]")
    abs_ic_mean = abs(ic_stats['ic_mean'])
    if abs_ic_mean > 0.05:
        print("  预测能力: [优秀] |IC| > 0.05")
    elif abs_ic_mean > 0.03:
        print("  预测能力: [良好] |IC| > 0.03")
    elif abs_ic_mean > 0.02:
        print("  预测能力: [一般] |IC| > 0.02")
    else:
        print("  预测能力: [较弱] |IC| < 0.02")

    # ========================================
    # 步骤4: 分组回测
    # ========================================
    print("\n[步骤4] 分组回测")
    print("-" * 80)

    from src.analysis.group_backtest import GroupBacktestEngine

    # 准备数据格式
    factor_df = factor_data.reset_index()
    if 'symbol' in factor_df.columns:
        factor_df = factor_df.rename(columns={'symbol': 'stock_code'})

    if not hasattr(factor_data, 'name') or factor_data.name is None:
        if len(factor_df.columns) == 3:
            factor_df = factor_df.rename(columns={factor_df.columns[-1]: 'factor'})

    returns_df = returns_data.reset_index()
    if 'symbol' in returns_df.columns:
        returns_df = returns_df.rename(columns={'symbol': 'stock_code'})
    returns_df = returns_df.rename(columns={'returns': 'ret'})

    # 创建回测引擎
    backtester = GroupBacktestEngine()

    # 运行分组回测
    print("运行分组回测（月频调仓）...")
    backtest_result = backtester.run_backtest(
        factor_data=factor_df,
        returns_data=returns_df,
        n_groups=5,
        freq='monthly',
        commission=0.00025,
        slippage=0.001
    )

    print("✅ 分组回测完成")

    # 提取分组收益
    group_returns = backtest_result['backtest_results']['group_returns']
    if not group_returns.empty:
        print(f"\n[分组收益]")
        cumulative = (1 + group_returns).cumprod()

        for col in group_returns.columns:
            total_ret = cumulative[col].iloc[-1] - 1
            annual_ret = group_returns[col].mean() * 252
            print(f"  第{col}组: 总收益={total_ret:.2%}, 年化={annual_ret:.2%}")

    # 提取多空策略
    ls_returns = backtest_result['backtest_results']['long_short_returns']
    if not ls_returns.empty and 'long_short_return' in ls_returns.columns:
        ls_series = ls_returns['long_short_return']
        cumulative_ls = (1 + ls_series).cumprod()

        print(f"\n[多空策略]")
        print(f"  总收益: {cumulative_ls.iloc[-1] - 1:.2%}")
        print(f"  年化收益: {ls_series.mean() * 252:.2%}")
        print(f"  夏普比率: {(ls_series.mean() / ls_series.std() * np.sqrt(252)) if ls_series.std() > 0 else 0:.4f}")

    # 单调性检验
    monotonicity = backtest_result['monotonicity_test']
    print(f"\n[单调性检验]")
    print(f"  是否单调: {monotonicity['is_monotonic']}")
    print(f"  趋势: {monotonicity['trend']}")
    print(f"  相关系数: {monotonicity['correlation']:.4f}")

    # ========================================
    # 步骤5: 可视化分析
    # ========================================
    print("\n[步骤5] 生成可视化图表")
    print("-" * 80)

    from src.analysis.visualization import FactorAnalysisVisualizer

    # 创建可视化器
    visualizer = FactorAnalysisVisualizer()

    # 创建输出目录
    output_dir = Path(__file__).parent / 'output'
    output_dir.mkdir(exist_ok=True)

    # 5.1 IC分析图表
    print("生成IC分析图表...")
    try:
        ic_fig = visualizer.plot_ic_analysis(
            ic_series=ic_series,
            factor_name=factor_name
        )
        ic_path = output_dir / f'{factor_name}_IC分析.png'
        visualizer.save_figure('ic_analysis', str(ic_path))
        print(f"  ✅ IC分析图表已保存: {ic_path}")
    except Exception as e:
        print(f"  ⚠️ IC分析图表生成失败: {e}")

    # 5.2 分组回测图表
    print("生成分组回测图表...")
    try:
        group_fig = visualizer.plot_group_backtest(
            group_returns=group_returns,
            long_short_returns=ls_returns,
            factor_name=factor_name
        )
        group_path = output_dir / f'{factor_name}_分组回测.png'
        visualizer.save_figure('group_backtest', str(group_path))
        print(f"  ✅ 分组回测图表已保存: {group_path}")
    except Exception as e:
        print(f"  ⚠️ 分组回测图表生成失败: {e}")

    # 5.3 单调性分析图表
    print("生成单调性分析图表...")
    try:
        # 计算各组平均收益
        group_avg_returns = group_returns.mean()
        mono_fig = visualizer.plot_monotonicity_analysis(
            group_avg_returns=group_avg_returns,
            correlation=monotonicity['correlation'],
            trend=monotonicity['trend'],
            factor_name=factor_name
        )
        mono_path = output_dir / f'{factor_name}_单调性分析.png'
        visualizer.save_figure('monotonicity_analysis', str(mono_path))
        print(f"  ✅ 单调性分析图表已保存: {mono_path}")
    except Exception as e:
        print(f"  ⚠️ 单调性分析图表生成失败: {e}")

    # 5.4 创建IC统计图表（2x2布局，与学习案例一致）
    print("生成IC统计图表...")
    try:
        import matplotlib.pyplot as plt

        # 创建2x2布局的IC统计图
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))

        # IC分布图
        ic_clean = ic_series.dropna()
        axes[0, 0].hist(ic_clean, bins=30, density=True, alpha=0.7, edgecolor='black', color='steelblue')
        axes[0, 0].axvline(x=ic_stats['ic_mean'], color='red', linestyle='--', linewidth=2,
                          label=f'均值: {ic_stats["ic_mean"]:.4f}')
        axes[0, 0].axvline(x=0, color='black', linestyle='-', linewidth=1, label='零线')
        axes[0, 0].set_title(f'{factor_name} - IC分布', fontsize=12, fontweight='bold')
        axes[0, 0].set_xlabel('IC值')
        axes[0, 0].set_ylabel('密度')
        axes[0, 0].legend(loc='best')
        axes[0, 0].grid(True, alpha=0.3)

        # IC时序图
        colors = ['red' if x < 0 else 'green' for x in ic_clean.values]
        axes[0, 1].bar(range(len(ic_clean)), ic_clean.values, color=colors, alpha=0.7)
        axes[0, 1].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        axes[0, 1].axhline(y=ic_stats['ic_mean'], color='blue', linestyle='--', linewidth=1,
                          label=f'均值: {ic_stats["ic_mean"]:.4f}')
        axes[0, 1].set_title(f'{factor_name} - IC时序图', fontsize=12, fontweight='bold')
        axes[0, 1].set_ylabel('IC值')
        axes[0, 1].legend(loc='best')
        axes[0, 1].grid(True, alpha=0.3)

        # 累计IC图
        cumulative_ic = ic_clean.cumsum()
        axes[1, 0].plot(cumulative_ic.index, cumulative_ic.values, linewidth=2, color='darkblue')
        axes[1, 0].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        axes[1, 0].set_title(f'{factor_name} - 累计IC', fontsize=12, fontweight='bold')
        axes[1, 0].set_ylabel('累计IC')
        axes[1, 0].grid(True, alpha=0.3)

        # IC统计摘要
        stats_text = f"""
IC统计摘要
IC均值: {ic_stats['ic_mean']:.4f}
IC标准差: {ic_stats['ic_std']:.4f}
IC_IR: {ic_stats['ic_ir']:.4f}
t统计量: {ic_stats['t_stat']:.4f}
p值: {ic_stats['p_value']:.4f}
IC为正比例: {ic_stats['ic_prob']:.2%}

因子评估:
"""
        # 添加因子评估
        abs_ic_mean = abs(ic_stats['ic_mean'])
        if abs_ic_mean > 0.05:
            eval_text = "预测能力: [优秀]"
        elif abs_ic_mean > 0.03:
            eval_text = "预测能力: [良好]"
        elif abs_ic_mean > 0.02:
            eval_text = "预测能力: [一般]"
        else:
            eval_text = "预测能力: [较弱]"

        if ic_stats['ic_ir'] > 1.0:
            stability_text = "稳定性: [优秀]"
        elif ic_stats['ic_ir'] > 0.5:
            stability_text = "稳定性: [良好]"
        elif ic_stats['ic_ir'] > 0.3:
            stability_text = "稳定性: [一般]"
        else:
            stability_text = "稳定性: [较差]"

        stats_text += eval_text + "\n" + stability_text

        axes[1, 1].text(0.1, 0.5, stats_text, fontsize=11, verticalalignment='center',
                       family='monospace',
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        axes[1, 1].axis('off')
        axes[1, 1].set_title('IC统计摘要', fontsize=12, fontweight='bold')

        plt.suptitle(f'{factor_name} - IC统计分析', fontsize=14, fontweight='bold', y=0.995)
        plt.tight_layout()

        ic_stats_path = output_dir / f'{factor_name}_IC统计.png'
        fig.savefig(ic_stats_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"  ✅ IC统计图表已保存: {ic_stats_path}")
    except Exception as e:
        print(f"  ⚠️ IC统计图表生成失败: {e}")
        import traceback
        traceback.print_exc()

    # 5.5 创建综合仪表板
    print("生成综合仪表板...")
    try:
        dashboard_fig = visualizer.create_dashboard(
            ic_series=ic_series,
            group_returns=group_returns,
            performance_returns=ls_returns['long_short_return'] if not ls_returns.empty else None,
            factor_name=factor_name
        )
        dashboard_path = output_dir / f'{factor_name}_综合仪表板.png'
        visualizer.save_figure('dashboard', str(dashboard_path))
        print(f"  ✅ 综合仪表板已保存: {dashboard_path}")
    except Exception as e:
        print(f"  ⚠️ 综合仪表板生成失败: {e}")

    # ========================================
    # 步骤6: 生成文本报告
    # ========================================
    print("\n[步骤6] 生成分析报告")
    print("-" * 80)

    report = backtester.generate_report(backtest_result)
    print(report)

    # 保存报告到文件
    report_path = output_dir / f'{factor_name}_分析报告.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# {factor_name} 因子分析报告\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        f.write(report)

    print(f"\n✅ 分析报告已保存: {report_path}")

    # ========================================
    # 总结
    # ========================================
    print("\n" + "=" * 80)
    print(" " * 30 + "分析完成!")
    print("=" * 80)

    print("\n[主要发现]")
    print(f"1. 因子 {factor_name} 的预测能力: {ic_stats['ic_mean']:.4f}")
    print(f"2. IC_IR比率: {ic_stats['ic_ir']:.4f} ({'优秀' if ic_stats['ic_ir'] > 0.5 else '一般'})")
    print(f"3. 分组单调性: {monotonicity['trend']} ({'显著' if monotonicity['is_monotonic'] else '不显著'})")
    print(f"4. 多空策略年化收益: {ls_series.mean() * 252:.2%}")

    print("\n[生成文件]")
    print(f"📊 图表文件:")
    print(f"  - {output_dir / f'{factor_name}_IC分析.png'}")
    print(f"  - {output_dir / f'{factor_name}_IC统计.png'} (2x2布局)")
    print(f"  - {output_dir / f'{factor_name}_分组回测.png'}")
    print(f"  - {output_dir / f'{factor_name}_单调性分析.png'}")
    print(f"  - {output_dir / f'{factor_name}_综合仪表板.png'}")
    print(f"📄 报告文件:")
    print(f"  - {output_dir / f'{factor_name}_分析报告.txt'}")

    print("\n[建议]")
    if abs(ic_stats['ic_mean']) > 0.03 and monotonicity['is_monotonic']:
        print("✅ 该因子表现良好，可考虑纳入策略")
    else:
        print("⚠️ 该因子表现一般，建议优化或尝试其他因子")

    print("\n[下一步]")
    print("1. 尝试其他alpha101因子")
    print("2. 调整参数（分组数、调仓频率等）")
    print("3. 构建多因子组合")
    print("4. 进行样本外测试")

    # 询问是否显示图表
    print("\n" + "=" * 80)
    show_charts = input("是否显示图表？(y/n，默认n): ").strip().lower()
    if show_charts == 'y':
        print("\n正在显示图表...")
        try:
            import matplotlib.pyplot as plt
            plt.show()
        except Exception as e:
            print(f"显示图表时出错: {e}")
            print("请查看output目录下的图片文件")
    else:
        print("\n图表已保存到output目录，可以使用图片查看器打开")

    return {
        'factor_data': factor_data,
        'ic_stats': ic_stats,
        'backtest_result': backtest_result,
        'figures': visualizer.figures
    }


if __name__ == '__main__':
    try:
        result = complete_factor_analysis_demo()
        print("\n✅ 演示成功完成!")
    except Exception as e:
        print(f"\n❌ 演示执行出错: {e}")
        import traceback
        traceback.print_exc()
