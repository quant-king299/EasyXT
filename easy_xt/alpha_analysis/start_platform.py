"""
101因子分析平台 - 交互式启动界面

运行此文件启动因子分析平台，通过菜单选择功能
"""

import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import numpy as np
import pandas as pd
from ic_ir_analysis import ICIRAnalyzer
from factor_correlation import FactorCorrelationAnalyzer
from layered_backtest import LayeredBacktester


def print_banner():
    """打印平台横幅"""
    print("\n" + "="*80)
    print(" "*20 + "101因子分析平台 v1.0")
    print("="*80)
    print("功能列表：")
    print("  1. IC/IR分析     - 评估因子预测能力")
    print("  2. 相关性分析    - 识别重复因子")
    print("  3. 分层回测      - 验证因子有效性")
    print("  4. 完整分析      - 一键执行所有分析")
    print("  5. 使用示例      - 运行演示")
    print("  0. 退出平台")
    print("="*80 + "\n")


def load_data_example():
    """加载示例数据"""
    print("\n正在生成示例数据...")

    np.random.seed(42)
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
    stocks = [f'{i:06d}.SZ' for i in range(1, 101)]

    # 生成价格数据
    trend = np.linspace(0, 0.3, len(dates))
    price_data = pd.DataFrame(
        np.random.randn(len(dates), len(stocks)) * 0.02 + trend.reshape(-1, 1) + 1,
        index=dates,
        columns=stocks
    ).cumprod() * 10

    # 生成多个因子
    factor_dict = {}
    factor_dict['alpha001'] = pd.DataFrame(
        np.random.randn(len(dates), len(stocks)),
        index=dates,
        columns=stocks
    )
    factor_dict['alpha002'] = factor_dict['alpha001'] * 0.9 + np.random.randn(len(dates), len(stocks)) * 0.1
    factor_dict['alpha003'] = pd.DataFrame(
        np.random.randn(len(dates), len(stocks)),
        index=dates,
        columns=stocks
    )

    momentum = price_data.pct_change(5).shift(-5)
    factor_dict['alpha004'] = momentum

    reversal = -price_data.pct_change(1).shift(-1)
    factor_dict['alpha005'] = reversal

    print(f"[OK] 数据生成完成：{len(dates)}个交易日，{len(stocks)}只股票，{len(factor_dict)}个因子\n")

    return price_data, factor_dict


def load_data_from_file():
    """从文件加载数据"""
    print("\n请准备数据文件：")
    print("  - 价格数据：CSV格式，索引为日期，列为股票代码")
    print("  - 因子数据：CSV格式，索引为日期，列为股票代码")

    price_file = input("\n请输入价格数据文件路径（留空使用示例数据）: ").strip()
    if not price_file:
        return None

    factor_file = input("请输入因子数据文件路径: ").strip()

    try:
        price_data = pd.read_csv(price_file, index_col=0, parse_dates=True)
        factor_data = pd.read_csv(factor_file, index_col=0, parse_dates=True)
        print(f"\n[OK] 数据加载成功！")
        print(f"  价格数据：{price_data.shape}")
        print(f"  因子数据：{factor_data.shape}\n")
        return price_data, factor_data
    except Exception as e:
        print(f"\n[X] 数据加载失败：{str(e)}\n")
        return None


def ic_ir_analysis(price_data, factor_dict):
    """IC/IR分析"""
    print("\n" + "="*80)
    print("IC/IR分析")
    print("="*80)

    # 选择因子
    print("\n可用因子：")
    for i, name in enumerate(factor_dict.keys(), 1):
        print(f"  {i}. {name}")

    choice = input("\n请选择因子编号（多个用逗号分隔，留空分析所有）: ").strip()

    if choice:
        indices = [int(x.strip()) - 1 for x in choice.split(',')]
        selected_factors = {list(factor_dict.keys())[i]: factor_dict[list(factor_dict.keys())[i]]
                           for i in indices}
    else:
        selected_factors = factor_dict

    # 选择参数
    try:
        period = input("请输入持有期数（默认1）: ").strip()
        period = int(period) if period else 1
    except:
        period = 1

    # 执行分析
    for factor_name, factor_data in selected_factors.items():
        print(f"\n{'='*80}")
        print(f"分析因子: {factor_name}")
        print(f"{'='*80}")

        try:
            analyzer = ICIRAnalyzer(price_data, factor_data)
            analyzer.calculate_ic(periods=period, method='spearman')
            analyzer.print_report()

            # 保存结果
            save = input(f"\n是否保存{factor_name}的分析结果？(y/n): ").strip().lower()
            if save == 'y':
                analyzer.save_ic_series(f'{factor_name}_ic_series.csv')
                analyzer.save_report(f'{factor_name}_ic_report.csv')
                print(f"[OK] 结果已保存\n")

        except Exception as e:
            print(f"[X] 分析失败：{str(e)}\n")


def factor_correlation_analysis(price_data, factor_dict):
    """因子相关性分析"""
    print("\n" + "="*80)
    print("因子相关性分析")
    print("="*80)

    # 选择因子
    print("\n可用因子：")
    for i, name in enumerate(factor_dict.keys(), 1):
        print(f"  {i}. {name}")

    choice = input("\n请选择因子编号（多个用逗号分隔，留空分析所有）: ").strip()

    if choice:
        indices = [int(x.strip()) - 1 for x in choice.split(',')]
        selected_factors = {list(factor_dict.keys())[i]: factor_dict[list(factor_dict.keys())[i]]
                           for i in indices}
    else:
        selected_factors = factor_dict

    # 选择阈值
    try:
        threshold = input("请输入相关性阈值（默认0.7）: ").strip()
        threshold = float(threshold) if threshold else 0.7
    except:
        threshold = 0.7

    # 执行分析
    try:
        analyzer = FactorCorrelationAnalyzer(selected_factors)
        analyzer.print_report(threshold=threshold)

        # 保存结果
        save = input("\n是否保存分析结果？(y/n): ").strip().lower()
        if save == 'y':
            analyzer.save_correlation_matrix('factor_correlation_matrix.csv')
            analyzer.save_report('factor_correlation_report.csv', threshold=threshold)
            print("[OK] 结果已保存\n")

    except Exception as e:
        print(f"[X] 分析失败：{str(e)}\n")


def layered_backtest(price_data, factor_dict):
    """分层回测"""
    print("\n" + "="*80)
    print("分层回测")
    print("="*80)

    # 选择因子
    print("\n可用因子：")
    for i, name in enumerate(factor_dict.keys(), 1):
        print(f"  {i}. {name}")

    choice = input("\n请选择因子编号（多个用逗号分隔，留空回测所有）: ").strip()

    if choice:
        indices = [int(x.strip()) - 1 for x in choice.split(',')]
        selected_factors = {list(factor_dict.keys())[i]: factor_dict[list(factor_dict.keys())[i]]
                           for i in indices}
    else:
        selected_factors = factor_dict

    # 选择参数
    try:
        n_layers = input("请输入分层数量（默认5）: ").strip()
        n_layers = int(n_layers) if n_layers else 5
    except:
        n_layers = 5

    try:
        period = input("请输入持有期数（默认1）: ").strip()
        period = int(period) if period else 1
    except:
        period = 1

    # 执行回测
    for factor_name, factor_data in selected_factors.items():
        print(f"\n{'='*80}")
        print(f"回测因子: {factor_name}")
        print(f"{'='*80}")

        try:
            backtester = LayeredBacktester(price_data, factor_data)
            backtester.calculate_layer_returns(n_layers=n_layers, periods=period)
            backtester.calculate_long_short_returns(n_layers=n_layers, periods=period)
            backtester.calculate_backtest_metrics()
            backtester.print_report()

            # 保存结果
            save = input(f"\n是否保存{factor_name}的回测结果？(y/n): ").strip().lower()
            if save == 'y':
                backtester.save_returns(f'{factor_name}_long_short_returns.csv')
                backtester.save_report(f'{factor_name}_backtest_report.csv')
                print(f"[OK] 结果已保存\n")

        except Exception as e:
            print(f"[X] 回测失败：{str(e)}\n")


def complete_analysis(price_data, factor_dict):
    """完整分析"""
    print("\n" + "="*80)
    print("完整因子分析流程")
    print("="*80)

    print("\n将对所有因子进行系统分析...")
    print("分析流程：IC/IR分析 -> 分层回测 -> 因子排名\n")

    results = {}

    for factor_name, factor_data in factor_dict.items():
        print(f"\n{'='*80}")
        print(f"正在分析: {factor_name}")
        print(f"{'='*80}")

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
            print(f"[X] {factor_name} 分析失败: {str(e)}")
            continue

    # 生成综合报告
    print(f"\n{'='*80}")
    print("因子综合分析报告")
    print(f"{'='*80}\n")

    results_df = pd.DataFrame(results).T
    results_df = results_df.sort_values('IR', ascending=False)

    print("因子排名（按IR排序）：\n")
    print(results_df.to_string())

    # 保存综合报告
    save = input("\n是否保存综合分析报告？(y/n): ").strip().lower()
    if save == 'y':
        results_df.to_csv('factor_comparison_report.csv', encoding='utf-8-sig')
        print("\n[OK] 综合报告已保存到: factor_comparison_report.csv\n")


def run_example():
    """运行示例"""
    print("\n" + "="*80)
    print("运行使用示例")
    print("="*80)

    print("\n将运行example_usage.py中的完整示例...")
    print("这将演示所有功能的使用方法\n")

    try:
        exec(open('example_usage.py', encoding='utf-8').read())
    except Exception as e:
        print(f"\n[X] 示例运行失败：{str(e)}\n")


def main():
    """主程序"""
    while True:
        print_banner()

        # 加载数据
        data_choice = input("请选择数据来源 (1-示例数据 2-从文件加载): ").strip()

        if data_choice == '2':
            data = load_data_from_file()
            if data is None:
                print("\n使用示例数据继续...\n")
                price_data, factor_dict = load_data_example()
            else:
                price_data, factor_dict = data
        else:
            price_data, factor_dict = load_data_example()

        # 选择功能
        choice = input("\n请选择功能 (0-5): ").strip()

        if choice == '0':
            print("\n感谢使用101因子分析平台！再见！\n")
            break
        elif choice == '1':
            ic_ir_analysis(price_data, factor_dict)
        elif choice == '2':
            factor_correlation_analysis(price_data, factor_dict)
        elif choice == '3':
            layered_backtest(price_data, factor_dict)
        elif choice == '4':
            complete_analysis(price_data, factor_dict)
        elif choice == '5':
            run_example()
        else:
            print("\n[X] 无效选择，请重新输入\n")

        # 询问是否继续
        continue_choice = input("\n是否继续使用平台？(y/n): ").strip().lower()
        if continue_choice != 'y':
            print("\n感谢使用101因子分析平台！再见！\n")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序已中断。感谢使用！\n")
    except Exception as e:
        print(f"\n[X] 程序运行出错：{str(e)}\n")
        import traceback
        traceback.print_exc()
