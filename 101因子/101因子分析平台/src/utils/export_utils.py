"""
导出工具模块
支持将回测结果导出为Excel文件
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Optional
import os


class BacktestExporter:
    """回测结果导出器"""

    @staticmethod
    def export_to_excel(backtest_results: Dict,
                       factor_name: str,
                       output_path: Optional[str] = None) -> str:
        """
        将回测结果导出到Excel文件

        Args:
            backtest_results: 回测结果字典
            factor_name: 因子名称
            output_path: 输出文件路径，如果为None则自动生成

        Returns:
            str: 导出文件的完整路径
        """
        # 生成文件名
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"backtest_{factor_name}_{timestamp}.xlsx"
            # 创建output目录（如果不存在）
            output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'output')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, filename)

        # 创建Excel写入器
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 1. 概览页
            BacktestExporter._write_summary_sheet(writer, backtest_results, factor_name)

            # 2. 绩效指标页
            BacktestExporter._write_metrics_sheet(writer, backtest_results)

            # 3. 交易明细页
            if 'trade_details' in backtest_results:
                BacktestExporter._write_trade_details_sheet(writer, backtest_results)

            # 4. 收益明细页
            if 'returns' in backtest_results:
                BacktestExporter._write_returns_sheet(writer, backtest_results)

            # 5. 分层回测页（如果有）
            if 'quantile_results' in backtest_results and backtest_results['quantile_results']:
                BacktestExporter._write_quantile_sheet(writer, backtest_results)

        print(f"✓ 回测结果已导出到: {output_path}")
        return output_path

    @staticmethod
    def _write_summary_sheet(writer, backtest_results: Dict, factor_name: str):
        """写入概览页"""
        summary_data = {
            '项目': ['因子名称', '回测日期', '总收益率', '年化收益率', '夏普比率', '最大回撤', '胜率', '多空价差'],
            '数值': [
                factor_name,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                f"{backtest_results.get('total_return', 0):.2%}",
                f"{backtest_results.get('annual_return', 0):.2%}",
                f"{backtest_results.get('sharpe_ratio', 0):.4f}",
                f"{backtest_results.get('max_drawdown', 0):.2%}",
                f"{backtest_results.get('win_rate', 0):.2%}",
                f"{backtest_results.get('long_short_spread', 0):.2%}"
            ]
        }

        # 添加交易统计
        if 'trade_details' in backtest_results:
            trade_df = backtest_results['trade_details']
            if not trade_df.empty:
                summary_data['项目'].extend([
                    '总交易次数',
                    '做多交易次数',
                    '做空交易次数',
                    '交易天数'
                ])
                summary_data['数值'].extend([
                    len(trade_df),
                    len(trade_df[trade_df['direction'] == '做多']),
                    len(trade_df[trade_df['direction'] == '做空']),
                    trade_df['date'].nunique()
                ])

        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='概览', index=False)

    @staticmethod
    def _write_metrics_sheet(writer, backtest_results: Dict):
        """写入绩效指标页"""
        metrics = {
            '收益指标': [
                ('总收益率', f"{backtest_results.get('total_return', 0):.2%}"),
                ('年化收益率', f"{backtest_results.get('annual_return', 0):.2%}"),
            ],
            '风险指标': [
                ('年化波动率', f"{backtest_results.get('volatility', 0):.2%}"),
                ('最大回撤', f"{backtest_results.get('max_drawdown', 0):.2%}"),
            ],
            '风险调整收益': [
                ('夏普比率', f"{backtest_results.get('sharpe_ratio', 0):.4f}"),
                ('胜率', f"{backtest_results.get('win_rate', 0):.2%}"),
            ],
            '多空分析': [
                ('做多平均收益', f"{backtest_results.get('long_avg_return', 0):.2%}"),
                ('做空平均收益', f"{backtest_results.get('short_avg_return', 0):.2%}"),
                ('多空价差', f"{backtest_results.get('long_short_spread', 0):.2%}"),
            ]
        }

        # 展开为DataFrame
        data = []
        for category, items in metrics.items():
            for item_name, item_value in items:
                data.append({
                    '类别': category,
                    '指标': item_name,
                    '数值': item_value
                })

        metrics_df = pd.DataFrame(data)
        metrics_df.to_excel(writer, sheet_name='绩效指标', index=False)

    @staticmethod
    def _write_trade_details_sheet(writer, backtest_results: Dict):
        """写入交易明细页"""
        trade_df = backtest_results['trade_details']

        if trade_df.empty:
            # 写入空表格
            pd.DataFrame({'message': ['暂无交易明细']}).to_excel(
                writer, sheet_name='交易明细', index=False
            )
            return

        # 整理交易明细格式
        trade_detail_export = trade_df.copy()

        # 格式化日期
        if 'date' in trade_detail_export.columns:
            trade_detail_export['交易日期'] = trade_detail_export['date'].dt.strftime('%Y-%m-%d')

        # 格式化价格
        if 'price' in trade_detail_export.columns:
            trade_detail_export['交易价格'] = trade_detail_export['price'].apply(
                lambda x: f"{x:.2f}" if pd.notna(x) else '-'
            )

        # 格式化权重
        if 'weight' in trade_detail_export.columns:
            trade_detail_export['权重'] = trade_detail_export['weight'].apply(
                lambda x: f"{x:.2%}" if pd.notna(x) else '-'
            )

        # 格式化因子值
        if 'factor_value' in trade_detail_export.columns:
            trade_detail_export['因子值'] = trade_detail_export['factor_value'].apply(
                lambda x: f"{x:.4f}" if pd.notna(x) else '-'
            )

        # 重命名列
        column_mapping = {
            'symbol': '股票代码',
            'direction': '方向',
            'action': '操作'
        }
        trade_detail_export = trade_detail_export.rename(columns=column_mapping)

        # 选择要导出的列
        export_columns = [
            '交易日期', '股票代码', '方向', '操作',
            '交易价格', '权重', '因子值'
        ]
        trade_detail_export = trade_detail_export[export_columns]

        trade_detail_export.to_excel(writer, sheet_name='交易明细', index=False)

    @staticmethod
    def _write_returns_sheet(writer, backtest_results: Dict):
        """写入收益明细页"""
        returns_df = backtest_results['returns']

        if returns_df.empty:
            pd.DataFrame({'message': ['暂无收益数据']}).to_excel(
                writer, sheet_name='收益明细', index=False
            )
            return

        # 重置索引以便导出日期
        returns_export = returns_df.reset_index()

        # 格式化日期
        returns_export['日期'] = returns_export['date'].dt.strftime('%Y-%m-%d')

        # 格式化百分比
        for col in ['return', 'long_ret', 'short_ret']:
            if col in returns_export.columns:
                returns_export[col] = returns_export[col].apply(lambda x: f"{x:.2%}")

        if 'cumulative_return' in returns_export.columns:
            returns_export['cumulative_return'] = returns_export['cumulative_return'].apply(
                lambda x: f"{x:.2%}"
            )

        # 重命名列
        column_mapping = {
            'return': '日收益率',
            'long_ret': '做多收益',
            'short_ret': '做空收益',
            'cumulative_return': '累计收益'
        }
        returns_export = returns_export.rename(columns=column_mapping)

        # 选择要导出的列
        export_columns = ['日期', '日收益率', '做多收益', '做空收益', '累计收益']
        returns_export = returns_export[[col for col in export_columns if col in returns_export.columns]]

        returns_export.to_excel(writer, sheet_name='收益明细', index=False)

    @staticmethod
    def _write_quantile_sheet(writer, backtest_results: Dict):
        """写入分层回测页"""
        quantile_results = backtest_results['quantile_results']

        if not quantile_results:
            return

        # 汇总各层指标
        summary_data = []
        for q_name, q_result in quantile_results.items():
            summary_data.append({
                '分层': q_name,
                '总收益率': f"{q_result.get('total_return', 0):.2%}",
                '年化收益率': f"{q_result.get('annual_return', 0):.2%}",
                '夏普比率': f"{q_result.get('sharpe_ratio', 0):.4f}",
                '最大回撤': f"{q_result.get('max_drawdown', 0):.2%}",
            })

        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='分层回测', index=False)


def export_trade_details_to_excel(trade_details: pd.DataFrame,
                                   output_path: str) -> str:
    """
    仅导出交易明细到Excel

    Args:
        trade_details: 交易明细DataFrame
        output_path: 输出文件路径

    Returns:
        str: 导出文件的完整路径
    """
    if trade_details.empty:
        print("[WARNING] 交易明细为空，无法导出")
        return ""

    # 创建Excel写入器
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # 交易明细页
        trade_detail_export = trade_details.copy()

        # 格式化日期
        if 'date' in trade_detail_export.columns:
            trade_detail_export['交易日期'] = trade_detail_export['date'].dt.strftime('%Y-%m-%d')

        # 格式化价格
        if 'price' in trade_detail_export.columns:
            trade_detail_export['交易价格'] = trade_detail_export['price'].apply(
                lambda x: f"{x:.2f}" if pd.notna(x) else '-'
            )

        # 格式化权重
        if 'weight' in trade_detail_export.columns:
            trade_detail_export['权重'] = trade_detail_export['weight'].apply(
                lambda x: f"{x:.2%}" if pd.notna(x) else '0%'
            )

        # 格式化因子值
        if 'factor_value' in trade_detail_export.columns:
            trade_detail_export['因子值'] = trade_detail_export['factor_value'].apply(
                lambda x: f"{x:.4f}" if pd.notna(x) else '-'
            )

        # 重命名列
        column_mapping = {
            'symbol': '股票代码',
            'direction': '方向',
            'action': '操作'
        }
        trade_detail_export = trade_detail_export.rename(columns=column_mapping)

        # 选择要导出的列
        export_columns = [
            '交易日期', '股票代码', '方向', '操作',
            '交易价格', '权重', '因子值'
        ]
        trade_detail_export = trade_detail_export[export_columns]

        trade_detail_export.to_excel(writer, sheet_name='交易明细', index=False)

    print(f"✓ 交易明细已导出到: {output_path}")
    return output_path
