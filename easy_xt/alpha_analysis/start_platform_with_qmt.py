"""
101因子分析平台 - QMT集成版

直接从QMT获取数据进行分析

运行此文件启动因子分析平台，自动从QMT获取行情数据
"""

import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 添加easy_xt到路径
easy_xt_dir = os.path.abspath(os.path.join(current_dir, '../..'))
if easy_xt_dir not in sys.path:
    sys.path.insert(0, easy_xt_dir)

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from ic_ir_analysis import ICIRAnalyzer
from factor_correlation import FactorCorrelationAnalyzer
from layered_backtest import LayeredBacktester

# 配置报告输出目录
REPORT_DIR = r'C:\Users\Administrator\Desktop\miniqmt扩展\101因子\101因子分析平台\reports'
os.makedirs(REPORT_DIR, exist_ok=True)


def print_banner():
    """打印平台横幅"""
    print("\n" + "="*80)
    print(" "*15 + "101因子分析平台 - QMT集成版 v1.0")
    print("="*80)
    print("功能列表：")
    print("  1. IC/IR分析     - 评估因子预测能力")
    print("  2. 相关性分析    - 识别重复因子")
    print("  3. 分层回测      - 验证因子有效性")
    print("  4. 完整分析      - 一键执行所有分析")
    print("  5. 从QMT获取数据 - 获取行情并计算基础因子")
    print("  0. 退出平台")
    print("="*80 + "\n")


def load_data_from_qmt():
    """从QMT获取数据"""
    print("\n" + "="*80)
    print("从QMT获取数据")
    print("="*80)

    try:
        from easy_xt import get_api

        print("\n正在连接QMT...")
        api = get_api()

        # 获取股票池
        print("\n请选择股票池：")
        print("  1. 全A股")
        print("  2. 沪深300")
        print("  3. 中证500")
        print("  4. 自定义股票代码（逗号分隔）")

        pool_choice = input("\n请选择 (1-4): ").strip()

        if pool_choice == '1':
            # 获取全A股列表
            stock_list = api.get_stock_list()
            stock_codes = [s['stock_code'] for s in stock_list if s['stock_code'].endswith('.SZ') or s['stock_code'].endswith('.SH')]
        elif pool_choice == '2':
            # 沪深300成分股
            stock_codes = get_hs300_stocks()
        elif pool_choice == '3':
            # 中证500成分股
            stock_codes = get_cs500_stocks()
        elif pool_choice == '4':
            # 自定义股票
            codes_input = input("请输入股票代码（用逗号分隔）: ").strip()
            stock_codes = [c.strip() for c in codes_input.split(',')]
        else:
            print("\n使用默认：沪深300")
            stock_codes = get_hs300_stocks()

        print(f"\n已选择 {len(stock_codes)} 只股票")

        # 选择时间范围
        print("\n请选择时间范围：")
        print("  1. 最近1年")
        print("  2. 最近2年")
        print("  3. 最近3年")
        print("  4. 自定义时间范围")

        time_choice = input("\n请选择 (1-4): ").strip()

        end_date = datetime.now()
        if time_choice == '1':
            start_date = end_date - timedelta(days=365)
        elif time_choice == '2':
            start_date = end_date - timedelta(days=730)
        elif time_choice == '3':
            start_date = end_date - timedelta(days=1095)
        elif time_choice == '4':
            start_str = input("请输入开始日期 (YYYY-MM-DD): ").strip()
            end_str = input("请输入结束日期 (YYYY-MM-DD, 留空至今): ").strip()
            start_date = datetime.strptime(start_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_str, '%Y-%m-%d') if end_str else datetime.now()
        else:
            print("\n使用默认：最近1年")
            start_date = end_date - timedelta(days=365)

        print(f"\n时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")

        # 获取行情数据
        print("\n正在从QMT获取行情数据，请稍候...")

        price_dict = {}
        for i, code in enumerate(stock_codes[:100]):  # 限制前100只股票演示
            try:
                print(f"\r获取进度: {i+1}/{min(len(stock_codes), 100)}", end='')
                data = api.get_history(
                    stock_code=code,
                    period='daily',
                    start_time=start_date.strftime('%Y%m%d'),
                    end_time=end_date.strftime('%Y%m%d')
                )

                if data is not None and len(data) > 0:
                    price_dict[code] = data['close'].to_dict()

            except Exception as e:
                continue

        print(f"\n成功获取 {len(price_dict)} 只股票的行情数据")

        # 转换为DataFrame格式
        price_data = pd.DataFrame.from_dict(price_dict, orient='index').T
        price_data.index = pd.to_datetime(price_data.index)
        price_data = price_data.sort_index()

        # 生成基础因子
        print("\n正在计算基础因子...")
        factor_dict = calculate_basic_factors(price_data)

        print(f"\n[OK] 数据准备完成！")
        print(f"  日期范围: {price_data.index[0]} 至 {price_data.index[-1]}")
        print(f"  股票数量: {len(price_data.columns)}")
        print(f"  因子数量: {len(factor_dict)}\n")

        return price_data, factor_dict

    except ImportError:
        print("\n[错误] 无法导入easy_xt模块")
        print("请确保已安装easy_xt: pip install -e easy_xt")
        return None
    except Exception as e:
        print(f"\n[错误] 从QMT获取数据失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def get_hs300_stocks():
    """获取沪深300成分股代码（示例）"""
    # 实际使用时可以从QMT或数据源获取
    return [
        '000001.SZ', '000002.SZ', '000063.SZ', '000069.SZ', '000100.SZ',
        '000166.SZ', '000333.SZ', '000338.SZ', '000651.SZ', '000708.SZ',
        '000725.SZ', '000768.SZ', '000858.SZ', '000876.SZ', '000883.SZ',
        # ... 更多股票代码
    ][:50]  # 示例只取50只


def get_cs500_stocks():
    """获取中证500成分股代码（示例）"""
    # 实际使用时可以从QMT或数据源获取
    return [
        '002001.SZ', '002004.SZ', '002008.SZ', '002016.SZ', '002027.SZ',
        # ... 更多股票代码
    ][:50]  # 示例只取50只


def calculate_basic_factors(price_data):
    """计算基础因子"""
    factor_dict = {}

    # 因子1: 动量因子 (5日收益率)
    momentum = price_data.pct_change(5)
    factor_dict['momentum_5d'] = momentum

    # 因子2: 反转因子 (1日收益率的负值)
    reversal = -price_data.pct_change(1)
    factor_dict['reversal_1d'] = reversal

    # 因子3: 波动率因子 (20日标准差)
    volatility = price_data.pct_change().rolling(20).std()
    factor_dict['volatility_20d'] = volatility

    # 因子4: 估值因子 (价格倒数)
    valuation = 1 / price_data
    factor_dict['price_inverse'] = valuation

    # 因子5: 量价关系 (这里简化，实际应该用成交量)
    # price_volume_ratio = price_data.pct_change()  # 需要成交量数据
    # factor_dict['price_ratio'] = price_volume_ratio

    return factor_dict


def load_data_example():
    """加载示例数据（备用）"""
    print("\n正在生成示例数据...")

    np.random.seed(42)
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
    stocks = [f'{i:06d}.SZ' for i in range(1, 51)]

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
    factor_dict['momentum_5d'] = momentum

    reversal = -price_data.pct_change(1).shift(-1)
    factor_dict['reversal_1d'] = reversal

    print(f"[OK] 示例数据生成完成：{len(dates)}个交易日，{len(stocks)}只股票，{len(factor_dict)}个因子\n")

    return price_data, factor_dict


def load_data_from_file():
    """从文件加载数据（保留原功能）"""
    print("\n" + "="*80)
    print("从文件加载数据")
    print("="*80)
    print("\n请准备数据文件：")
    print("  - 价格数据：CSV格式，索引为日期，列为股票代码")
    print("  - 因子数据：CSV格式，索引为日期，列为股票代码")

    price_file = input("\n请输入价格数据文件路径（留空取消）: ").strip()
    if not price_file:
        return None

    factor_file = input("请输入因子数据文件路径: ").strip()

    try:
        price_data = pd.read_csv(price_file, index_col=0, parse_dates=True)
        factor_data = pd.read_csv(factor_file, index_col=0, parse_dates=True)

        # 转换为因子字典格式
        factor_dict = {'custom_factor': factor_data}

        print(f"\n[OK] 数据加载成功！")
        print(f"  价格数据：{price_data.shape}")
        print(f"  因子数据：{factor_data.shape}\n")
        return price_data, factor_dict
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
    factor_list = list(factor_dict.keys())
    for i, name in enumerate(factor_list, 1):
        print(f"  {i}. {name}")

    choice = input("\n请选择因子编号（多个用逗号分隔，留空分析所有）: ").strip()

    if choice:
        indices = [int(x.strip()) - 1 for x in choice.split(',')]
        selected_factors = {factor_list[i]: factor_dict[factor_list[i]] for i in indices}
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
                analyzer.save_ic_series(os.path.join(REPORT_DIR, f'{factor_name}_ic_series.csv'))
                analyzer.save_report(os.path.join(REPORT_DIR, f'{factor_name}_ic_report.csv'))
                print(f"[OK] 结果已保存到 {REPORT_DIR}\n")

        except Exception as e:
            print(f"[X] 分析失败：{str(e)}\n")


def factor_correlation_analysis(price_data, factor_dict):
    """因子相关性分析"""
    print("\n" + "="*80)
    print("因子相关性分析")
    print("="*80)

    # 选择因子
    print("\n可用因子：")
    factor_list = list(factor_dict.keys())
    for i, name in enumerate(factor_list, 1):
        print(f"  {i}. {name}")

    choice = input("\n请选择因子编号（多个用逗号分隔，留空分析所有）: ").strip()

    if choice:
        indices = [int(x.strip()) - 1 for x in choice.split(',')]
        selected_factors = {factor_list[i]: factor_dict[factor_list[i]] for i in indices}
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
            analyzer.save_correlation_matrix(os.path.join(REPORT_DIR, 'factor_correlation_matrix.csv'))
            analyzer.save_report(os.path.join(REPORT_DIR, 'factor_correlation_report.csv'), threshold=threshold)
            print(f"[OK] 结果已保存到 {REPORT_DIR}\n")

    except Exception as e:
        print(f"[X] 分析失败：{str(e)}\n")


def layered_backtest(price_data, factor_dict):
    """分层回测"""
    print("\n" + "="*80)
    print("分层回测")
    print("="*80)

    # 选择因子
    print("\n可用因子：")
    factor_list = list(factor_dict.keys())
    for i, name in enumerate(factor_list, 1):
        print(f"  {i}. {name}")

    choice = input("\n请选择因子编号（多个用逗号分隔，留空回测所有）: ").strip()

    if choice:
        indices = [int(x.strip()) - 1 for x in choice.split(',')]
        selected_factors = {factor_list[i]: factor_dict[factor_list[i]] for i in indices}
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
                backtester.save_returns(os.path.join(REPORT_DIR, f'{factor_name}_long_short_returns.csv'))
                backtester.save_report(os.path.join(REPORT_DIR, f'{factor_name}_backtest_report.csv'))
                print(f"[OK] 结果已保存到 {REPORT_DIR}\n")

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
        report_path = os.path.join(REPORT_DIR, 'factor_comparison_report.csv')
        results_df.to_csv(report_path, encoding='utf-8-sig')
        print(f"\n[OK] 综合报告已保存到: {report_path}\n")


def main():
    """主程序"""
    while True:
        print_banner()

        # 加载数据
        print("请选择数据来源：")
        print("  1. 从QMT获取数据（推荐）")
        print("  2. 从文件加载")
        print("  3. 使用示例数据（快速体验）")

        data_choice = input("\n请选择 (1-3): ").strip()

        if data_choice == '1':
            data = load_data_from_qmt()
            if data is None:
                print("\nQMT数据获取失败，使用示例数据继续...\n")
                price_data, factor_dict = load_data_example()
            else:
                price_data, factor_dict = data
        elif data_choice == '2':
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
            # 重新获取数据
            print("\n将从QMT重新获取数据...")
            price_data, factor_dict = load_data_from_qmt()
            if price_data is not None:
                print("\n数据获取完成，请选择分析功能\n")
            continue
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
