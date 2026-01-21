"""
101因子分析平台 - 快速测试脚本

运行此脚本可以快速测试平台功能是否正常
"""

import sys
import numpy as np
import pandas as pd


def test_ic_ir_analysis():
    """测试IC/IR分析功能"""
    print("\n" + "="*80)
    print("测试1: IC/IR分析")
    print("="*80)

    try:
        # 尝试直接导入
        try:
            from ic_ir_analysis import ICIRAnalyzer
        except ImportError:
            # 如果失败，尝试从easy_xt导入
            from easy_xt.alpha_analysis.ic_ir_analysis import ICIRAnalyzer

        # 生成测试数据
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', '2023-03-31', freq='D')
        stocks = [f'{i:06d}.SZ' for i in range(1, 51)]

        price_data = pd.DataFrame(
            np.random.randn(len(dates), len(stocks)) * 0.02 + 1,
            index=dates,
            columns=stocks
        ).cumprod() * 10

        factor_data = pd.DataFrame(
            np.random.randn(len(dates), len(stocks)),
            index=dates,
            columns=stocks
        )

        # 测试分析器
        analyzer = ICIRAnalyzer(price_data, factor_data)
        analyzer.calculate_ic(periods=1, method='spearman')
        ic_stats = analyzer.calculate_ic_stats()

        print(f"[OK] IC均值: {ic_stats['ic_mean']:.4f}")
        print(f"[OK] IR: {ic_stats['ir']:.4f}")
        print("[OK] IC/IR分析测试通过！")
        return True

    except Exception as e:
        print(f"[X] IC/IR分析测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_factor_correlation():
    """测试因子相关性分析功能"""
    print("\n" + "="*80)
    print("测试2: 因子相关性分析")
    print("="*80)

    try:
        # 尝试直接导入
        try:
            from factor_correlation import FactorCorrelationAnalyzer
        except ImportError:
            # 如果失败，尝试从easy_xt导入
            from easy_xt.alpha_analysis.factor_correlation import FactorCorrelationAnalyzer

        # 生成测试数据
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', '2023-03-31', freq='D')
        stocks = [f'{i:06d}.SZ' for i in range(1, 51)]

        factor_dict = {}
        factor_dict['alpha001'] = pd.DataFrame(
            np.random.randn(len(dates), len(stocks)),
            index=dates,
            columns=stocks
        )

        # 创建高度相关的因子
        factor_dict['alpha002'] = factor_dict['alpha001'] * 0.9 + np.random.randn(len(dates), len(stocks)) * 0.1

        # 测试分析器
        analyzer = FactorCorrelationAnalyzer(factor_dict)
        corr_matrix = analyzer.calculate_correlation(method='spearman')

        high_corr_pairs = analyzer.find_high_correlation_pairs(threshold=0.7)

        print(f"[OK] 因子数量: {len(factor_dict)}")
        print(f"[OK] 高相关性因子对数量: {len(high_corr_pairs)}")
        if high_corr_pairs:
            print(f"[OK] 最高相关系数: {high_corr_pairs[0][2]:.4f}")
        print("[OK] 因子相关性分析测试通过！")
        return True

    except Exception as e:
        print(f"[X] 因子相关性分析测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_layered_backtest():
    """测试分层回测功能"""
    print("\n" + "="*80)
    print("测试3: 分层回测")
    print("="*80)

    try:
        # 尝试直接导入
        try:
            from layered_backtest import LayeredBacktester
        except ImportError:
            # 如果失败，尝试从easy_xt导入
            from easy_xt.alpha_analysis.layered_backtest import LayeredBacktester

        # 生成测试数据
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', '2023-03-31', freq='D')
        stocks = [f'{i:06d}.SZ' for i in range(1, 51)]

        price_data = pd.DataFrame(
            np.random.randn(len(dates), len(stocks)) * 0.02 + 1,
            index=dates,
            columns=stocks
        ).cumprod() * 10

        factor_data = pd.DataFrame(
            np.random.randn(len(dates), len(stocks)),
            index=dates,
            columns=stocks
        )

        # 测试回测器
        backtester = LayeredBacktester(price_data, factor_data)
        backtester.calculate_layer_returns(n_layers=5, periods=1)
        backtester.calculate_long_short_returns(n_layers=5)
        metrics = backtester.calculate_backtest_metrics()

        print(f"[OK] 年化收益率: {metrics['annual_return']:.2%}")
        print(f"[OK] 夏普比率: {metrics['sharpe_ratio']:.4f}")
        print(f"[OK] 最大回撤: {metrics['max_drawdown']:.2%}")
        print("[OK] 分层回测测试通过！")
        return True

    except Exception as e:
        print(f"[X] 分层回测测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("="*80)
    print("101因子分析平台 - 功能测试")
    print("="*80)

    results = []

    # 测试IC/IR分析
    results.append(test_ic_ir_analysis())

    # 测试因子相关性分析
    results.append(test_factor_correlation())

    # 测试分层回测
    results.append(test_layered_backtest())

    # 汇总结果
    print("\n" + "="*80)
    print("测试结果汇总")
    print("="*80)

    test_names = ['IC/IR分析', '因子相关性分析', '分层回测']
    passed = sum(results)
    total = len(results)

    for name, result in zip(test_names, results):
        status = "[OK] 通过" if result else "[X] 失败"
        print(f"{name}: {status}")

    print("\n" + "="*80)
    print(f"总计: {passed}/{total} 测试通过")

    if passed == total:
        print("[OK] 所有测试通过！平台功能正常。")
        return 0
    else:
        print(f"[X] 有{total-passed}个测试失败，请检查错误信息。")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
