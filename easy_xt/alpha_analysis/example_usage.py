"""
101因子分析完整示例
演示如何使用IC/IR分析、因子相关性分析、分层回测三大功能

使用方法：
    1. 准备价格数据和因子数据
    2. 运行IC/IR分析评估因子预测能力
    3. 运行因子相关性分析识别重复因子
    4. 运行分层回测验证因子有效性

作者：王者quant
"""

import numpy as np
import pandas as pd
import os
from ic_ir_analysis import ICIRAnalyzer
from factor_correlation import FactorCorrelationAnalyzer
from layered_backtest import LayeredBacktester

# 配置报告输出目录
REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
os.makedirs(REPORT_DIR, exist_ok=True)


def generate_sample_data():
    """
    生成示例数据（用于演示）
    实际使用时，请替换为你的真实数据
    """
    print("正在生成示例数据...")

    np.random.seed(42)
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
    stocks = [f'{i:06d}.SZ' for i in range(1, 101)]  # 100只股票

    # 生成价格数据（模拟上涨趋势）
    trend = np.linspace(0, 0.3, len(dates))
    price_data = pd.DataFrame(
        np.random.randn(len(dates), len(stocks)) * 0.02 + trend.reshape(-1, 1) + 1,
        index=dates,
        columns=stocks
    ).cumprod() * 10

    # 生成多个因子数据
    factor_dict = {}

    # 因子1：随机因子
    factor_dict['alpha001'] = pd.DataFrame(
        np.random.randn(len(dates), len(stocks)),
        index=dates,
        columns=stocks
    )

    # 因子2：与因子1高度相关
    factor_dict['alpha002'] = (
        factor_dict['alpha001'] * 0.9 +
        np.random.randn(len(dates), len(stocks)) * 0.1
    )

    # 因子3：中等质量因子
    factor_dict['alpha003'] = pd.DataFrame(
        np.random.randn(len(dates), len(stocks)),
        index=dates,
        columns=stocks
    )

    # 因子4：动量因子（有一定预测能力）
    momentum = price_data.pct_change(5).shift(-5)
    factor_dict['alpha004'] = momentum

    # 因子5：反转因子
    reversal = -price_data.pct_change(1).shift(-1)
    factor_dict['alpha005'] = reversal

    print("示例数据生成完成！")
    print(f"日期范围: {dates[0]} 至 {dates[-1]}")
    print(f"股票数量: {len(stocks)}")
    print(f"因子数量: {len(factor_dict)}")

    return price_data, factor_dict


def example_ic_ir_analysis(price_data, factor_data, factor_name='alpha001'):
    """
    示例1：IC/IR分析
    评估因子的预测能力
    """
    print("\n" + "="*80)
    print("示例1：IC/IR分析 - 评估因子预测能力")
    print("="*80)

    # 创建IC/IR分析器
    analyzer = ICIRAnalyzer(price_data, factor_data)

    # 计算IC值（使用1期收益率）
    print("\n正在计算IC值...")
    analyzer.calculate_ic(
        periods=1,
        method='spearman'  # 使用Spearman相关系数
    )

    # 打印分析报告
    analyzer.print_report()

    # 保存结果
    analyzer.save_ic_series(os.path.join(REPORT_DIR, f'{factor_name}_ic_series.csv'))
    analyzer.save_report(os.path.join(REPORT_DIR, f'{factor_name}_ic_report.csv'))

    # 获取IC统计指标
    ic_stats = analyzer.calculate_ic_stats()
    print(f"\nIC均值: {ic_stats['ic_mean']:.4f}")
    print(f"IR: {ic_stats['ir']:.4f}")

    return analyzer


def example_factor_correlation_analysis(factor_dict):
    """
    示例2：因子相关性分析
    识别重复因子
    """
    print("\n" + "="*80)
    print("示例2：因子相关性分析 - 识别重复因子")
    print("="*80)

    # 创建因子相关性分析器
    analyzer = FactorCorrelationAnalyzer(factor_dict)

    # 打印分析报告
    analyzer.print_report(threshold=0.7)

    # 保存相关系数矩阵
    analyzer.save_correlation_matrix(os.path.join(REPORT_DIR, 'factor_correlation_matrix.csv'))

    # 保存分析报告
    analyzer.save_report(os.path.join(REPORT_DIR, 'factor_correlation_report.csv'), threshold=0.7)

    # 获取去重建议
    suggestions = analyzer.generate_removal_suggestions(threshold=0.7)
    print("\n去重建议：")
    for keep_factor, remove_factors in suggestions.items():
        print(f"  保留 {keep_factor}, 删除 {', '.join(remove_factors)}")

    # 聚类分析
    cluster_result = analyzer.hierarchical_clustering(n_clusters=3)
    print("\n聚类结果：")
    print(cluster_result)

    return analyzer


def example_layered_backtest(price_data, factor_data, factor_name='alpha001'):
    """
    示例3：分层回测
    验证因子有效性
    """
    print("\n" + "="*80)
    print("示例3：分层回测 - 验证因子有效性")
    print("="*80)

    # 创建分层回测器
    backtester = LayeredBacktester(price_data, factor_data)

    # 计算分层收益（5层）
    print("\n正在计算分层收益...")
    backtester.calculate_layer_returns(
        n_layers=5,
        periods=1,
        method='quantile'  # 按分位数分层
    )

    # 计算多空收益
    print("正在计算多空策略收益...")
    backtester.calculate_long_short_returns(
        n_layers=5,
        periods=1,
        method='quantile'
    )

    # 计算回测指标
    print("正在计算回测指标...")
    backtester.calculate_backtest_metrics()

    # 打印回测报告
    backtester.print_report()

    # 保存结果
    backtester.save_returns(os.path.join(REPORT_DIR, f'{factor_name}_long_short_returns.csv'))
    backtester.save_report(os.path.join(REPORT_DIR, f'{factor_name}_backtest_report.csv'))

    return backtester


def example_complete_analysis(price_data, factor_dict):
    """
    示例4：完整的因子分析流程
    对所有因子进行系统分析
    """
    print("\n" + "="*80)
    print("示例4：完整的因子分析流程")
    print("="*80)

    results = {}

    for factor_name in factor_dict.keys():
        print(f"\n正在分析因子: {factor_name}")
        print("-" * 80)

        factor_data = factor_dict[factor_name]

        try:
            # IC/IR分析
            ic_analyzer = ICIRAnalyzer(price_data, factor_data)
            ic_analyzer.calculate_ic(periods=1, method='spearman')
            ic_stats = ic_analyzer.calculate_ic_stats()

            # 分层回测
            backtester = LayeredBacktester(price_data, factor_data)
            backtester.calculate_layer_returns(n_layers=5, periods=1)
            backtester.calculate_long_short_returns(n_layers=5, periods=1)
            backtest_metrics = backtester.calculate_backtest_metrics()

            # 汇总结果
            results[factor_name] = {
                'IC均值': ic_stats['ic_mean'],
                'IR': ic_stats['ir'],
                '年化收益率': backtest_metrics['annual_return'],
                '夏普比率': backtest_metrics['sharpe_ratio'],
                '最大回撤': backtest_metrics['max_drawdown'],
                '胜率': backtest_metrics['win_rate']
            }

            print(f"[OK] {factor_name} 分析完成")

        except Exception as e:
            print(f"[ERROR] {factor_name} 分析失败: {str(e)}")
            continue

    # 生成综合报告
    print("\n" + "="*80)
    print("因子综合分析报告")
    print("="*80)

    results_df = pd.DataFrame(results).T
    results_df = results_df.sort_values('IR', ascending=False)

    print("\n因子排名（按IR排序）：")
    print(results_df)

    # 保存综合报告
    report_path = os.path.join(REPORT_DIR, 'factor_comparison_report.csv')
    results_df.to_csv(report_path, encoding='utf-8-sig')
    print(f"\n综合报告已保存到: {report_path}")

    return results_df


def main():
    """
    主函数：运行所有示例
    """
    print("="*80)
    print("101因子分析平台 - 完整示例")
    print("="*80)

    # 1. 生成示例数据
    price_data, factor_dict = generate_sample_data()

    # 2. IC/IR分析（示例：分析alpha001因子）
    example_ic_ir_analysis(price_data, factor_dict['alpha001'], 'alpha001')

    # 3. 因子相关性分析（分析所有因子）
    example_factor_correlation_analysis(factor_dict)

    # 4. 分层回测（示例：回测alpha001因子）
    example_layered_backtest(price_data, factor_dict['alpha001'], 'alpha001')

    # 5. 完整分析流程（分析所有因子）
    example_complete_analysis(price_data, factor_dict)

    print("\n" + "="*80)
    print("所有分析完成！")
    print("="*80)
    print("\n生成的文件：")
    print("  - IC分析: alpha001_ic_series.csv, alpha001_ic_report.csv")
    print("  - 相关性: factor_correlation_matrix.csv, factor_correlation_report.csv")
    print("  - 回测: alpha001_long_short_returns.csv, alpha001_backtest_report.csv")
    print("  - 综合报告: factor_comparison_report.csv")


if __name__ == "__main__":
    main()
