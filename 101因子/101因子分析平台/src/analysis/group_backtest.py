"""
分组回测模块

基于外部项目的分组回测逻辑，为101因子分析平台添加完整的因子分组回测功能。

主要功能：
- 按因子值分组（默认10组）
- 计算各分组收益
- 计算多空策略收益
- 评估因子单调性
- IC/IR分析
- 生成详细回测报告
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import sys
import os

# 添加项目路径
project_path = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_path)

from .enhanced_performance import EnhancedPerformanceAnalyzer, PerformanceVisualizer
from .ic_analysis import ICAnalysis


class GroupBacktestEngine:
    """
    分组回测引擎（增强版）

    完整的因子分组回测功能，整合了IC/IR分析

    主要功能：
    1. 分组回测（N组可配置）
    2. IC/IR分析
    3. 单调性检验
    4. 绩效评估
    5. 可视化

    使用示例：
        # 分组回测
        engine = GroupBacktestEngine()
        result = engine.run_backtest(factor_data, returns_data, n_groups=10)

        # IC/IR分析（新增）
        ic_result = engine.calculate_ic_analysis(factor_data, returns_data)

        # 快速IC测试（新增）
        ic_result = engine.quick_ic_test(factor_data, returns_data)
    """

    def __init__(self):
        self.analyzer = EnhancedPerformanceAnalyzer()
        self.visualizer = PerformanceVisualizer()
        self.ic_analyzer = ICAnalysis()

    def run_backtest(self,
                    factor_data: pd.DataFrame,
                    returns_data: pd.DataFrame,
                    n_groups: int = 10,
                    freq: str = 'monthly',
                    commission: float = 0.00025,
                    slippage: float = 0.001) -> Dict:
        """
        运行完整的分组回测

        参数:
            factor_data: 因子数据
                       格式: DataFrame with columns [date, stock_code, factor]
                       或者: MultiIndex (date, stock_code)
            returns_data: 收益数据
                       格式: DataFrame with columns [date, stock_code, ret]
                       或者: MultiIndex (date, stock_code)
            n_groups: 分组数量（默认10）
            freq: 调仓频率 ('daily', 'weekly', 'monthly')
            commission: 手续费率（默认0.025%）
            slippage: 滑点（默认0.1%）

        返回:
            dict: 完整的回测结果
        """
        # 数据预处理
        factor_df = self._prepare_factor_data(factor_data)
        returns_df = self._prepare_returns_data(returns_data)

        # 执行分组回测
        backtest_results = self._execute_group_backtest(
            factor_df, returns_df, n_groups, freq, commission, slippage
        )

        # 计算绩效指标
        performance_summary = self._calculate_performance_summary(backtest_results)

        # 评估单调性
        monotonicity_test = self._test_monotonicity(backtest_results)

        # 组装结果
        result = {
            'backtest_results': backtest_results,
            'performance_summary': performance_summary,
            'monotonicity_test': monotonicity_test,
            'parameters': {
                'n_groups': n_groups,
                'freq': freq,
                'commission': commission,
                'slippage': slippage
            }
        }

        return result

    def _prepare_factor_data(self, factor_data: pd.DataFrame) -> pd.DataFrame:
        """准备因子数据"""
        if isinstance(factor_data.index, pd.MultiIndex):
            # 已经是MultiIndex格式
            if 'factor' not in factor_data.columns:
                # 尝试找到因子列
                numeric_cols = factor_data.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    factor_df = factor_data.reset_index()
                    factor_col = numeric_cols[0]
                    factor_df = factor_df.rename(columns={factor_col: 'factor'})
                else:
                    raise ValueError("无法找到因子列")
            else:
                factor_df = factor_data.reset_index()
        else:
            # 不是MultiIndex，需要转换
            factor_df = factor_data.copy()

            # 确保有必要的列
            if 'date' not in factor_df.columns:
                # 假设第一列是date
                factor_df = factor_df.reset_index()
                if 'date' not in factor_df.columns:
                    factor_df.columns = ['date'] + list(factor_df.columns[:-1])

            # 确保有factor列
            if 'factor' not in factor_df.columns:
                numeric_cols = factor_df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    factor_df = factor_df.rename(columns={numeric_cols[0]: 'factor'})

        # 确保日期格式正确
        factor_df['date'] = pd.to_datetime(factor_df['date'])

        return factor_df

    def _prepare_returns_data(self, returns_data: pd.DataFrame) -> pd.DataFrame:
        """准备收益数据"""
        if isinstance(returns_data.index, pd.MultiIndex):
            # 已经是MultiIndex格式
            if 'ret' not in returns_data.columns:
                # 尝试找到收益列
                numeric_cols = returns_data.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    returns_df = returns_data.reset_index()
                    ret_col = numeric_cols[0]
                    returns_df = returns_df.rename(columns={ret_col: 'ret'})
                else:
                    raise ValueError("无法找到收益列")
            else:
                returns_df = returns_data.reset_index()
        else:
            # 不是MultiIndex，需要转换
            returns_df = returns_data.copy()

            # 确保必要的列
            if 'date' not in returns_df.columns:
                returns_df = returns_df.reset_index()

            # 确保有ret列
            if 'ret' not in returns_df.columns:
                numeric_cols = returns_df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    returns_df = returns_df.rename(columns={numeric_cols[0]: 'ret'})

        # 确保日期格式正确
        returns_df['date'] = pd.to_datetime(returns_df['date'])

        return returns_df

    def _execute_group_backtest(self,
                               factor_df: pd.DataFrame,
                               returns_df: pd.DataFrame,
                               n_groups: int,
                               freq: str,
                               commission: float,
                               slippage: float) -> Dict:
        """执行分组回测"""
        # 获取调仓日期
        all_dates = sorted(factor_df['date'].unique())
        rebalance_dates = self._get_rebalance_dates(all_dates, freq)

        group_returns_list = []
        long_short_returns_list = []

        # 按时间回测
        for i in range(len(rebalance_dates) - 1):
            current_date = rebalance_dates[i]
            next_date = rebalance_dates[i + 1]

            # 获取当前日期的因子
            current_factors = factor_df[factor_df['date'] == current_date].copy()

            if len(current_factors) < n_groups * 3:
                continue

            # 分组
            current_factors['group'] = self._assign_groups(
                current_factors['factor'].values,
                current_factors['stock_code'].values,
                n_groups
            )

            # 计算收益
            period_returns = returns_df[
                (returns_df['date'] > current_date) &
                (returns_df['date'] <= next_date)
            ].copy()

            if len(period_returns) == 0:
                continue

            # 计算各分组收益（扣减交易成本）
            group_ret = self._calculate_group_returns_with_cost(
                current_factors, period_returns, commission, slippage
            )

            if group_ret is not None:
                group_ret['date'] = current_date
                group_returns_list.append(group_ret)

            # 计算多空收益
            if group_ret is not None and len(group_ret) > 1:
                # 复制group_ret以避免修改原数据
                group_ret_copy = group_ret.copy()

                # 移除date列（如果存在）
                if isinstance(group_ret_copy, pd.Series):
                    # Series: 检查并移除date索引项
                    if 'date' in group_ret_copy.index:
                        group_ret_clean = group_ret_copy.drop('date')
                    else:
                        group_ret_clean = group_ret_copy

                    long_group = group_ret_clean.idxmax()
                    short_group = group_ret_clean.idxmin()
                    long_short_ret = group_ret_clean[long_group] - group_ret_clean[short_group]
                else:
                    # DataFrame: 移除date列
                    if 'date' in group_ret_copy.columns:
                        group_ret_clean = group_ret_copy.drop(columns=['date'])
                    else:
                        group_ret_clean = group_ret_copy

                    if len(group_ret_clean.columns) > 0:
                        # 选择第一个数值列
                        numeric_cols = group_ret_clean.select_dtypes(include=[np.number]).columns
                        if len(numeric_cols) > 0:
                            col = numeric_cols[0]
                            long_group = group_ret_clean[col].idxmax()
                            short_group = group_ret_clean[col].idxmin()
                            long_short_ret = group_ret_clean.loc[long_group, col] - group_ret_clean.loc[short_group, col]
                        else:
                            long_short_ret = None
                    else:
                        long_short_ret = None

                long_short_returns_list.append({
                    'date': current_date,
                    'long_short_return': long_short_ret
                })

        # 整理结果
        if group_returns_list:
            group_returns_df = pd.DataFrame(group_returns_list)
            group_returns_df = group_returns_df.set_index('date')
        else:
            group_returns_df = pd.DataFrame()

        if long_short_returns_list:
            long_short_series = pd.DataFrame(long_short_returns_list)
            long_short_series = long_short_series.set_index('date')
        else:
            long_short_series = pd.DataFrame()

        return {
            'group_returns': group_returns_df,
            'long_short_returns': long_short_series,
            'n_periods': len(group_returns_list)
        }

    def _assign_groups(self, factor_values: np.ndarray,
                       stock_codes: np.ndarray,
                       n_groups: int) -> np.ndarray:
        """分配分组"""
        # 创建排序索引
        sorted_indices = np.argsort(factor_values)

        groups = np.zeros(len(factor_values), dtype=int)

        group_size = len(sorted_indices) // n_groups

        for i in range(n_groups):
            start_idx = i * group_size
            end_idx = (i + 1) * group_size if i < n_groups - 1 else len(sorted_indices)

            groups[sorted_indices[start_idx:end_idx]] = i + 1

        return groups

    def _calculate_group_returns_with_cost(self,
                                          factor_df: pd.DataFrame,
                                          returns_df: pd.DataFrame,
                                          commission: float,
                                          slippage: float) -> Optional[pd.Series]:
        """计算考虑交易成本的分组收益"""
        group_returns = {}

        # 获取日期范围内的股票收益（支持ret或return列）
        ret_col = 'ret' if 'ret' in returns_df.columns else 'return'

        # 修复：对于日收益率数据，应该计算平均日收益
        # 而不是复合收益，避免收益被放大
        stock_returns = returns_df.groupby('stock_code')[ret_col].mean()

        # 扣减交易成本（按调仓次数分摊）
        # 假设每次调仓的成本是commission + slippage
        total_cost = commission + slippage
        stock_returns = stock_returns - total_cost

        # 计算各分组收益
        for group_id in range(1, factor_df['group'].max() + 1):
            group_stocks = factor_df[factor_df['group'] == group_id]['stock_code'].values

            # 获取这些股票的收益
            valid_stocks = [s for s in group_stocks if s in stock_returns.index]

            if len(valid_stocks) > 0:
                group_ret = stock_returns.loc[valid_stocks].mean()
                group_returns[group_id] = group_ret

        if group_returns:
            return pd.Series(group_returns)
        else:
            return None

    def _get_rebalance_dates(self, all_dates, freq: str) -> list:
        """获取调仓日期"""
        if freq == 'daily':
            return all_dates
        elif freq == 'weekly':
            df = pd.DataFrame({'date': all_dates})
            df['date'] = pd.to_datetime(df['date'])
            df['week'] = df['date'].dt.isocalendar().week
            df['year'] = df['date'].dt.year
            return df.groupby(['year', 'week'])['date'].last().tolist()
        elif freq == 'monthly':
            df = pd.DataFrame({'date': all_dates})
            df['date'] = pd.to_datetime(df['date'])
            df['month'] = df['date'].dt.month
            df['year'] = df['date'].dt.year
            return df.groupby(['year', 'month'])['date'].last().tolist()
        else:
            return all_dates

    def _calculate_performance_summary(self, backtest_results: Dict) -> Dict:
        """计算绩效汇总"""
        summary = {}

        # 分组收益统计
        if 'group_returns' in backtest_results and not backtest_results['group_returns'].empty:
            group_returns = backtest_results['group_returns']

            # 计算累计收益
            cumulative = (1 + group_returns).cumprod()
            total_returns = cumulative.iloc[-1] - 1

            # 计算年化收益
            annual_returns = group_returns.mean() * 252

            summary['group_total_returns'] = total_returns.to_dict()
            summary['group_annual_returns'] = annual_returns.to_dict()

        # 多空策略统计
        if 'long_short_returns' in backtest_results and not backtest_results['long_short_returns'].empty:
            ls_returns = backtest_results['long_short_returns']['long_short_return']

            cumulative_ls = (1 + ls_returns).cumprod()
            total_ls = cumulative_ls.iloc[-1] - 1
            annual_ls = ls_returns.mean() * 252

            summary['long_short'] = {
                'total_return': total_ls,
                'annual_return': annual_ls,
                'sharpe_ratio': ls_returns.mean() / ls_returns.std() * np.sqrt(252) if ls_returns.std() > 0 else 0
            }

        return summary

    def _test_monotonicity(self, backtest_results: Dict) -> Dict:
        """测试因子单调性"""
        if 'group_returns' not in backtest_results or backtest_results['group_returns'].empty:
            return {
                'is_monotonic': False,
                'correlation': np.nan,
                'trend': 'unknown'
            }

        group_returns = backtest_results['group_returns']

        # 计算各组的平均收益
        group_avg_returns = group_returns.mean()

        # 计算相关系数
        group_ids = list(range(1, len(group_avg_returns) + 1))
        correlation = np.corrcoef(group_ids, group_avg_returns.values)[0, 1]

        # 判断单调性
        is_increasing = all(group_avg_returns.iloc[i] <= group_avg_returns.iloc[i+1]
                           for i in range(len(group_avg_returns) - 1))

        is_decreasing = all(group_avg_returns.iloc[i] >= group_avg_returns.iloc[i+1]
                           for i in range(len(group_avg_returns) - 1))

        if is_increasing:
            trend = 'increasing'
            is_monotonic = True
        elif is_decreasing:
            trend = 'decreasing'
            is_monotonic = True
        else:
            trend = 'none'
            is_monotonic = False

        return {
            'is_monotonic': is_monotonic,
            'correlation': correlation,
            'trend': trend,
            'group_avg_returns': group_avg_returns.to_dict()
        }

    def calculate_ic_analysis(self,
                            factor_data: pd.DataFrame,
                            returns_data: pd.DataFrame,
                            min_stock_num: int = 10) -> Dict:
        """
        计算IC/IR分析

        整合自 ic_analysis.py，为因子分析提供IC/IR计算功能

        参数:
            factor_data: 因子数据
                       格式: DataFrame with columns [date, stock_code, factor]
                       或者: MultiIndex (date, stock_code)
            returns_data: 收益数据
                       格式: DataFrame with columns [date, stock_code, ret]
                       或者: MultiIndex (date, stock_code)
            min_stock_num: 最小股票数量

        返回:
            dict: IC分析结果
                {
                    'ic_series': pd.Series,  # IC序列
                    'ic_statistics': dict,    # IC统计指标
                    'analysis_result': dict   # 完整分析结果
                }
        """
        # 准备因子数据
        factor_df = self._prepare_factor_data(factor_data)
        returns_df = self._prepare_returns_data(returns_data)

        # 转换为MultiIndex Series格式（ICAnalysis需要的格式）
        factor_series = factor_df.pivot(index='date', columns='stock_code', values='factor')
        # 支持ret或return列名
        ret_col = 'ret' if 'ret' in returns_df.columns else 'return'
        returns_series = returns_df.pivot(index='date', columns='stock_code', values=ret_col)

        # 展平为MultiIndex Series
        factor_multi = factor_series.stack()
        returns_multi = returns_series.stack()

        # 使用ICAnalysis类计算
        ic_analyzer = ICAnalysis()

        # 计算IC序列
        ic_series = ic_analyzer.calculate_ic(factor_multi, returns_multi)

        # 计算IC统计
        ic_stats = ic_analyzer.calculate_ic_stats(ic_series)

        # 完整分析结果
        analysis_result = ic_analyzer.analyze_factor_ic(
            factor_multi,
            returns_multi,
            factor_name="Factor"
        )

        return {
            'ic_series': ic_series,
            'ic_statistics': ic_stats,
            'analysis_result': analysis_result
        }

    def quick_ic_test(self,
                     factor_data: pd.DataFrame,
                     returns_data: pd.DataFrame) -> Dict:
        """
        快速IC测试（便捷方法）

        这是替代原 backtest.py 的主要方法，提供快速的IC/IR分析

        参数:
            factor_data: 因子数据
            returns_data: 收益数据

        返回:
            dict: IC分析结果（简化版）
        """
        result = self.calculate_ic_analysis(factor_data, returns_data)

        # 提取关键信息
        ic_stats = result['ic_statistics']

        return {
            'ic_mean': ic_stats['ic_mean'],
            'ic_std': ic_stats['ic_std'],
            'ic_ir': ic_stats['ic_ir'],
            'ic_abs_mean': ic_stats['ic_abs_mean'],
            't_stat': ic_stats['t_stat'],
            'p_value': ic_stats['p_value'],
            'ic_positive_ratio': ic_stats['ic_prob'],
            'ic_series': result['ic_series']
        }

    def generate_ic_report(self, ic_result: Dict, factor_name: str = "因子") -> str:
        """
        生成IC分析报告

        参数:
            ic_result: IC分析结果
            factor_name: 因子名称

        返回:
            str: 格式化的IC分析报告
        """
        report = []
        report.append("=" * 70)
        report.append(f" " * 20 + f"{factor_name} - IC分析报告")
        report.append("=" * 70)

        ic_stats = ic_result['ic_statistics']
        ic_series = ic_result['ic_series']

        # IC统计信息
        report.append(f"\n[IC统计指标]")
        report.append(f"  IC均值: {ic_stats['ic_mean']:.4f}")
        report.append(f"  IC标准差: {ic_stats['ic_std']:.4f}")
        report.append(f"  IC_IR（信息比率）: {ic_stats['ic_ir']:.4f}")
        report.append(f"  IC绝对值均值: {ic_stats['ic_abs_mean']:.4f}")
        report.append(f"  t统计量: {ic_stats['t_stat']:.4f}")
        report.append(f"  p值: {ic_stats['p_value']:.4f}")
        report.append(f"  IC为正比例: {ic_stats['ic_prob']:.2%}")

        # IC评价
        report.append(f"\n[因子评价]")
        abs_ic_mean = abs(ic_stats['ic_mean'])
        if abs_ic_mean > 0.05:
            report.append(f"  [优秀] 强预测能力 (|IC| > 0.05)")
        elif abs_ic_mean > 0.03:
            report.append(f"  [良好] 较强预测能力 (|IC| > 0.03)")
        elif abs_ic_mean > 0.02:
            report.append(f"  [一般] 有一定预测能力 (|IC| > 0.02)")
        else:
            report.append(f"  [较弱] 预测能力较弱 (|IC| < 0.02)")

        ic_ir = ic_stats['ic_ir']
        if ic_ir > 1.0:
            report.append(f"  [优秀] 稳定性优秀 (IR > 1.0)")
        elif ic_ir > 0.5:
            report.append(f"  [良好] 稳定性良好 (IR > 0.5)")
        elif ic_ir > 0.3:
            report.append(f"  [一般] 稳定性一般 (IR > 0.3)")
        else:
            report.append(f"  [较差] 稳定性较差 (IR < 0.3)")

        # IC序列信息
        if not ic_series.empty:
            report.append(f"\n[IC序列信息]")
            report.append(f"  有效期数: {len(ic_series)}")
            report.append(f"  最大IC: {ic_series.max():.4f}")
            report.append(f"  最小IC: {ic_series.min():.4f}")

        report.append("\n" + "=" * 70)

        return "\n".join(report)

    def generate_report(self, backtest_result: Dict) -> str:
        """生成回测报告"""
        report = []
        report.append("=" * 70)
        report.append(" " * 20 + "因子分组回测报告")
        report.append("=" * 70)

        # 参数信息
        params = backtest_result['parameters']
        report.append(f"\n[回测参数]")
        report.append(f"  分组数量: {params['n_groups']}")
        report.append(f"  调仓频率: {params['freq']}")
        report.append(f"  手续费率: {params['commission']:.4%}")
        report.append(f"  滑点: {params['slippage']:.2%}")

        # 回测结果
        backtest_results = backtest_result['backtest_results']
        report.append(f"\n[回测结果]")
        report.append(f"  回测期数: {backtest_results['n_periods']}")

        # 分组收益
        if 'group_returns' in backtest_results:
            group_returns = backtest_results['group_returns']
            cumulative = (1 + group_returns).cumprod()

            report.append(f"\n[分组收益]")
            for group in group_returns.columns:
                if 'group' in str(group):
                    total_ret = cumulative[group].iloc[-1] - 1
                    annual_ret = group_returns[group].mean() * 252
                    report.append(f"  {group}: 总收益={total_ret:.2%}, 年化={annual_ret:.2%}")

        # 多空策略
        if 'long_short_returns' in backtest_results:
            ls_returns = backtest_results['long_short_returns']['long_short_return']
            cumulative_ls = (1 + ls_returns).cumprod()
            total_ls = cumulative_ls.iloc[-1] - 1

            report.append(f"\n[多空策略]")
            report.append(f"  总收益: {total_ls:.2%}")
            report.append(f"  年化收益: {ls_returns.mean() * 252:.2%}")
            report.append(f"  夏普比率: {ls_returns.mean() / ls_returns.std() * np.sqrt(252):.4f}")

        # 单调性测试
        monotonicity = backtest_result['monotonicity_test']
        report.append(f"\n[单调性检验]")
        report.append(f"  是否单调: {monotonicity['is_monotonic']}")
        report.append(f"  趋势: {monotonicity['trend']}")
        report.append(f"  相关系数: {monotonicity['correlation']:.4f}")

        # 绩效汇总
        summary = backtest_result['performance_summary']
        if 'long_short' in summary:
            ls = summary['long_short']
            report.append(f"\n[多空策略绩效]")
            report.append(f"  总收益: {ls['total_return']:.2%}")
            report.append(f"  年化收益: {ls['annual_return']:.2%}")
            report.append(f"  夏普比率: {ls['sharpe_ratio']:.4f}")

        report.append("\n" + "=" * 70)

        return "\n".join(report)


# 导出接口
__all__ = [
    'GroupBacktestEngine'
]
