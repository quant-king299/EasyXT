"""
绩效评估模块 - 增强版

基于外部项目的因子分析功能，增强101因子平台的绩效评估能力。

主要功能：
- 完整的绩效指标计算
- 分组回测分析
- 净值曲线绘制
- 回撤分析
- 绩效对比
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import sys
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

# 添加项目路径
project_path = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_path)

# 尝试导入factors模块
try:
    from factors.analysis.performance import PerformanceEvaluator
    FACTORS_AVAILABLE = True
except ImportError:
    FACTORS_AVAILABLE = False


class EnhancedPerformanceAnalyzer:
    """
    增强版绩效分析器

    整合外部项目的因子分析功能
    """

    def __init__(self):
        self.metrics = {}

    def calculate_performance_metrics(self,
                                     returns_series: pd.Series,
                                     benchmark_returns: Optional[pd.Series] = None,
                                     annual_trading_days: int = 252) -> Dict:
        """
        计算完整的绩效指标

        参数:
            returns_series: 收益率序列
            benchmark_returns: 基准收益率序列（可选）
            annual_trading_days: 年交易日数

        返回:
            dict: 绩效指标字典
        """
        # 清理数据
        clean_returns = returns_series.dropna()

        if len(clean_returns) == 0:
            return self._get_default_metrics()

        # 累计收益
        cumulative_returns = (1 + clean_returns).cumprod()
        total_return = cumulative_returns.iloc[-1] - 1

        # 年化收益
        years = len(clean_returns) / annual_trading_days
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        # 年化波动率
        annual_volatility = clean_returns.std() * np.sqrt(annual_trading_days)

        # 夏普比率（假设无风险利率3%）
        risk_free_rate = 0.03
        excess_return = annual_return - risk_free_rate
        sharpe_ratio = excess_return / annual_volatility if annual_volatility > 0 else 0

        # 最大回撤
        rolling_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        # Calmar比率
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

        # 胜率
        win_rate = (clean_returns > 0).sum() / len(clean_returns)

        # 索提诺比率
        downside_returns = clean_returns[clean_returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(annual_trading_days)
        sortino_ratio = excess_return / downside_deviation if downside_deviation > 0 else 0

        # VaR 95%
        var_95 = clean_returns.quantile(0.05)

        metrics = {
            'total_return': total_return,
            'annual_return': annual_return,
            'annual_volatility': annual_volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'calmar_ratio': calmar_ratio,
            'win_rate': win_rate,
            'var_95': var_95,
            'n_days': len(clean_returns)
        }

        # 如果有基准，计算相对指标
        if benchmark_returns is not None and len(benchmark_returns) > 0:
            benchmark_clean = benchmark_returns.dropna()

            # 对齐数据
            min_len = min(len(clean_returns), len(benchmark_clean))
            strategy_aligned = clean_returns.iloc[:min_len]
            benchmark_aligned = benchmark_clean.iloc[:min_len]

            # 超额收益
            excess_returns = strategy_aligned - benchmark_aligned

            # 信息比率
            tracking_error = excess_returns.std() * np.sqrt(annual_trading_days)
            information_ratio = excess_returns.mean() / tracking_error if tracking_error > 0 else 0

            # Beta
            cov_matrix = np.cov(strategy_aligned, benchmark_aligned)
            beta = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else 1.0

            # Alpha
            alpha = annual_return - risk_free_rate - beta * (benchmark_aligned.mean() * annual_trading_days - risk_free_rate)

            metrics.update({
                'information_ratio': information_ratio,
                'tracking_error': tracking_error,
                'beta': beta,
                'alpha': alpha
            })

        return metrics

    def calculate_group_performance(self,
                                   group_returns: pd.DataFrame,
                                   n_groups: int = 10) -> Dict:
        """
        计算分组绩效

        参数:
            group_returns: 各分组收益 DataFrame
            n_groups: 分组数量

        返回:
            dict: 分组绩效统计
        """
        results = {}

        for group in range(1, n_groups + 1):
            if group not in group_returns.columns:
                continue

            group_ret = group_returns[group].dropna()

            if len(group_ret) == 0:
                continue

            # 计算该分组的绩效
            cumulative = (1 + group_ret).cumprod()
            total_return = cumulative.iloc[-1] - 1
            annual_return = group_ret.mean() * 252  # 简化年化
            volatility = group_ret.std() * np.sqrt(252)
            sharpe = group_ret.mean() / group_ret.std() * np.sqrt(252) if group_ret.std() > 0 else 0
            max_dd = self._calculate_max_drawdown(cumulative)

            results[f'group_{group}'] = {
                'total_return': total_return,
                'annual_return': annual_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe,
                'max_drawdown': max_dd,
                'n_obs': len(group_ret)
            }

        return results

    def _calculate_max_drawdown(self, cumulative_returns: pd.Series) -> float:
        """计算最大回撤"""
        if len(cumulative_returns) == 0:
            return 0.0

        cummax = cumulative_returns.cummax()
        drawdown = (cumulative_returns - cummax) / cummax
        return drawdown.min()

    def _get_default_metrics(self) -> Dict:
        """返回默认指标"""
        return {
            'total_return': 0.0,
            'annual_return': 0.0,
            'annual_volatility': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'max_drawdown': 0.0,
            'calmar_ratio': 0.0,
            'win_rate': 0.0,
            'var_95': 0.0,
            'n_days': 0
        }

    def format_metrics(self, metrics: Dict) -> pd.DataFrame:
        """
        将指标格式化为DataFrame

        参数:
            metrics: 指标字典

        返回:
            pd.DataFrame: 格式化的指标表
        """
        df = pd.DataFrame([metrics]).T

        # 格式化百分比
        for col in ['total_return', 'annual_return', 'max_drawdown', 'calmar_ratio', 'win_rate', 'var_95']:
            if col in df.index:
                df.loc[col] = df.loc[col].apply(lambda x: f"{x:.2%}")

        # 格式化比率
        for col in ['sharpe_ratio', 'sortino_ratio']:
            if col in df.index:
                df.loc[col] = df.loc[col].apply(lambda x: f"{x:.4f}")

        return df


class GroupBacktestAnalyzer:
    """
    分组回测分析器

    基于外部项目的分组回测逻辑
    """

    def __init__(self):
        self.group_returns = None
        self.long_short_returns = None
        self.ic_data = None

    def run_group_backtest(self,
                           factor_data: pd.DataFrame,
                           price_data: pd.DataFrame,
                           returns_data: pd.DataFrame,
                           n_groups: int = 10,
                           freq: str = 'monthly') -> Dict:
        """
        运行分组回测

        参数:
            factor_data: 因子数据 (date, stock_code, factor)
            price_data: 价格数据 (date, stock_code, close)
            returns_data: 收益数据 (date, stock_code, ret)
            n_groups: 分组数量
            freq: 调仓频率 ('daily', 'weekly', 'monthly')

        返回:
            dict: 回测结果
        """
        # 准备数据
        factor_df = self._prepare_factor_data(factor_data)
        returns_df = self._prepare_returns_data(returns_data)

        # 按日期分组回测
        group_results = []
        long_short_results = []

        # 获取调仓日期
        rebalance_dates = self._get_rebalance_dates(factor_df.index.get_level_values(0).unique(), freq)

        for i in range(len(rebalance_dates) - 1):
            current_date = rebalance_dates[i]
            next_date = rebalance_dates[i + 1]

            # 获取当期因子
            current_factors = factor_df.loc[current_date].dropna()

            if len(current_factors) < n_groups * 3:  # 每组至少3只股票
                continue

            # 分组
            groups = self._assign_groups(current_factors, n_groups)

            # 计算收益
            group_ret, long_short_ret = self._calculate_group_returns(
                groups, returns_df, current_date, next_date
            )

            if group_ret is not None:
                group_ret['date'] = current_date
                group_results.append(group_ret)

            if long_short_ret is not None:
                long_short_ret['date'] = current_date
                long_short_results.append(long_short_ret)

        # 整理结果
        if group_results:
            self.group_returns = pd.DataFrame(group_results)

        if long_short_results:
            self.long_short_returns = pd.DataFrame(long_short_results)

        return {
            'group_returns': self.group_returns,
            'long_short_returns': self.long_short_returns,
            'n_periods': len(group_results)
        }

    def _prepare_factor_data(self, factor_data: pd.DataFrame) -> pd.DataFrame:
        """准备因子数据"""
        if isinstance(factor_data.index, pd.MultiIndex):
            # 已经是MultiIndex格式
            return factor_data
        else:
            # 需要转换为MultiIndex
            return factor_data.set_index(['date', 'stock_code'])

    def _prepare_returns_data(self, returns_data: pd.DataFrame) -> pd.DataFrame:
        """准备收益数据"""
        if isinstance(returns_data.index, pd.MultiIndex):
            return returns_data
        else:
            return returns_data.set_index(['date', 'stock_code'])

    def _get_rebalance_dates(self, all_dates, freq: str) -> list:
        """获取调仓日期"""
        dates = sorted(all_dates)

        if freq == 'daily':
            return dates
        elif freq == 'weekly':
            # 每周最后一个交易日
            df = pd.DataFrame({'date': dates})
            df['week'] = pd.to_datetime(df['date']).dt.isocalendar().week
            df['year'] = pd.to_datetime(df['date']).dt.year
            return df.groupby(['year', 'week'])['date'].last().tolist()
        elif freq == 'monthly':
            # 每月最后一个交易日
            df = pd.DataFrame({'date': dates})
            df['month'] = pd.to_datetime(df['date']).dt.month
            df['year'] = pd.to_datetime(df['date']).dt.year
            return df.groupby(['year', 'month'])['date'].last().tolist()
        else:
            return dates

    def _assign_groups(self, factor_values: pd.Series, n_groups: int) -> pd.Series:
        """分配分组"""
        sorted_values = factor_values.sort_values(ascending=True)

        groups = pd.Series(index=factor_values.index, dtype=int)

        group_size = len(sorted_values) // n_groups

        for i in range(n_groups):
            start_idx = i * group_size
            end_idx = (i + 1) * group_size if i < n_groups - 1 else len(sorted_values)
            stocks = sorted_values.index[start_idx:end_idx]
            groups[stocks] = i + 1

        return groups

    def _calculate_group_returns(self,
                                   groups: pd.Series,
                                   returns_df: pd.DataFrame,
                                   start_date,
                                   end_date) -> Tuple:
        """计算分组收益"""
        # 获取日期范围内的收益
        mask = (returns_df.index.get_level_values(0) > start_date) & \
                (returns_df.index.get_level_values(0) <= end_date)

        period_returns = returns_df[mask]

        if len(period_returns) == 0:
            return None, None

        # 计算各分组收益
        group_returns = {}

        for group_id in range(1, len(groups.unique()) + 1):
            group_stocks = groups[groups == group_id].index

            # 获取这些股票的收益
            stock_returns = period_returns[period_returns.index.get_level_values(1).isin(group_stocks)]

            if len(stock_returns) > 0:
                # 等权平均
                group_ret = stock_returns.mean()
                group_returns[group_id] = group_ret

        # 计算多空收益
        if group_returns:
            long_group = max(group_returns.items(), key=lambda x: x[1])
            short_group = min(group_returns.items(), key=lambda x: x[1])
            long_short_ret = long_group[1] - short_group[1]
        else:
            long_short_ret = None

        return pd.Series(group_returns), long_short_ret


class PerformanceVisualizer:
    """
    绩效可视化器

    基于外部项目的可视化功能
    """

    def __init__(self):
        self.fig = None
        self.ax = None

    def plot_nav_curve(self,
                      returns_series: pd.Series,
                      benchmark_returns: Optional[pd.Series] = None,
                      title: str = "净值曲线",
                      figsize: tuple = (12, 6)):
        """
        绘制净值曲线

        参数:
            returns_series: 收益率序列
            benchmark_returns: 基准收益率（可选）
            title: 图表标题
            figsize: 图表大小
        """
        # 计算累计净值
        cumulative = (1 + returns_series).cumprod()

        # 创建图表
        fig, ax = plt.subplots(figsize=figsize)

        # 绘制策略净值
        ax.plot(cumulative.index, cumulative.values, label='策略', linewidth=2)

        # 绘制基准净值
        if benchmark_returns is not None and len(benchmark_returns) > 0:
            benchmark_cumulative = (1 + benchmark_returns[:len(cumulative)]).cumprod()
            ax.plot(benchmark_cumulative.index, benchmark_cumulative.values,
                   label='基准', linewidth=2, linestyle='--')

        # 设置标题和标签
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('净值', fontsize=12)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

        # 格式化x轴
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.xticks(rotation=45)

        plt.tight_layout()

        return fig, ax

    def plot_drawdown(self,
                     returns_series: pd.Series,
                     title: str = "回撤分析",
                     figsize: tuple = (12, 4)):
        """
        绘制回撤图

        参数:
            returns_series: 收益率序列
            title: 图表标题
            figsize: 图表大小
        """
        # 计算累计净值和回撤
        cumulative = (1 + returns_series).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max

        # 创建图表
        fig, ax = plt.subplots(figsize=figsize)

        # 绘制回撤
        ax.fill_between(drawdown.index, drawdown.values, 0, alpha=0.3, color='red')
        ax.plot(drawdown.index, drawdown.values, color='darkred', linewidth=1)

        # 标记最大回撤
        max_dd_idx = drawdown.idxmin()
        max_dd_value = drawdown.min()
        ax.annotate(f'最大回撤: {max_dd_value:.2%}',
                    xy=(max_dd_idx, max_dd_value),
                    xytext=(10, 10), textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7),
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('回撤', fontsize=12)
        ax.grid(True, alpha=0.3)

        # 格式化x轴
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.xticks(rotation=45)

        plt.tight_layout()

        return fig, ax

    def plot_group_returns(self,
                          group_returns: pd.DataFrame,
                          title: str = "分组收益对比",
                          figsize: tuple = (12, 6)):
        """
        绘制分组收益对比图

        参数:
            group_returns: 各分组收益
            title: 图表标题
            figsize: 图表大小
        """
        # 计算累计收益
        cumulative_returns = (1 + group_returns).cumprod()

        # 创建图表
        fig, ax = plt.subplots(figsize=figsize)

        # 绘制各分组净值
        for column in cumulative_returns.columns:
            if 'group' in str(column):
                ax.plot(cumulative_returns.index, cumulative_returns[column],
                       label=f'{column}', linewidth=1.5, alpha=0.7)

        # 绘制多空收益
        if 'long_short' in cumulative_returns.columns:
            ax.plot(cumulative_returns.index, cumulative_returns['long_short'],
                   label='多空', linewidth=2, linestyle='--', color='black')

        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('净值', fontsize=12)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        return fig, ax

    def plot_ic_series(self,
                      ic_series: pd.Series,
                      title: str = "IC序列",
                      figsize: tuple = (12, 4)):
        """
        绘制IC序列图

        参数:
            ic_series: IC序列
            title: 图表标题
            figsize: 图表大小
        """
        fig, ax = plt.subplots(figsize=figsize)

        # 绘制IC序列
        colors = ['red' if x < 0 else 'green' for x in ic_series.values]
        ax.bar(range(len(ic_series)), ic_series.values, color=colors, alpha=0.7)

        # 添加零线
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

        # 标注均值
        ic_mean = ic_series.mean()
        ax.axhline(y=ic_mean, color='blue', linestyle='--', linewidth=1, label=f'均值: {ic_mean:.4f}')

        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('期数', fontsize=12)
        ax.set_ylabel('IC值', fontsize=12)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        return fig, ax


# 导出接口
__all__ = [
    'EnhancedPerformanceAnalyzer',
    'GroupBacktestAnalyzer',
    'PerformanceVisualizer'
]


if __name__ == "__main__":
    # 测试代码
    print("=" * 70)
    print(" " * 20 + "101因子平台 - 增强绩效分析模块测试")
    print("=" * 70)

    # 创建模拟数据
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='D')

    returns = pd.Series(np.random.normal(0.001, 0.02, len(dates)), index=dates)
    benchmark = pd.Series(np.random.normal(0.0008, 0.015, len(dates)), index=dates)

    # 测试绩效分析
    analyzer = EnhancedPerformanceAnalyzer()
    metrics = analyzer.calculate_performance_metrics(returns, benchmark)

    print("\n[绩效指标]")
    for key, value in metrics.items():
        if isinstance(value, float):
            if key in ['total_return', 'annual_return', 'max_drawdown']:
                print(f"  {key}: {value:.2%}")
            else:
                print(f"  {key}: {value:.4f}")

    # 测试可视化
    visualizer = PerformanceVisualizer()
    fig, ax = visualizer.plot_nav_curve(returns, benchmark)
    plt.show()

    print("\n测试完成!")
