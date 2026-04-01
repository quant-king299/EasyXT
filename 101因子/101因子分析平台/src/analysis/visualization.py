"""
增强版可视化工具模块

整合101因子平台的所有可视化功能，包括：
- 绩效评估可视化
- 分组回测可视化
- 因子分析可视化
- IC分析可视化
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
try:
    import seaborn as sns
    SEABORN_AVAILABLE = True
except ImportError:
    SEABORN_AVAILABLE = False
from typing import Dict, List, Optional, Tuple, Any
import sys
import os
from datetime import datetime

# 添加项目路径
project_path = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_path)

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 导入现有的可视化模块
from src.analysis.enhanced_performance import PerformanceVisualizer


class FactorAnalysisVisualizer:
    """
    因子分析可视化器

    整合所有因子分析相关的可视化功能
    """

    def __init__(self):
        """初始化可视化器"""
        self.perf_visualizer = PerformanceVisualizer()
        self.figures = {}  # 存储创建的图表

    def plot_ic_analysis(self,
                        ic_series: pd.Series,
                        factor_name: str = "因子",
                        figsize: Tuple[int, int] = (14, 10)) -> plt.Figure:
        """
        绘制IC分析图表

        参数:
            ic_series: IC序列
            factor_name: 因子名称
            figsize: 图表大小

        返回:
            plt.Figure: 图表对象
        """
        fig, axes = plt.subplots(3, 1, figsize=figsize)

        # 1. IC时序图
        colors = ['red' if x < 0 else 'green' for x in ic_series.values]
        axes[0].bar(range(len(ic_series)), ic_series.values, color=colors, alpha=0.7)
        axes[0].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        axes[0].axhline(y=ic_series.mean(), color='blue', linestyle='--',
                       linewidth=1, label=f'均值: {ic_series.mean():.4f}')
        axes[0].set_title(f'{factor_name} - IC时序图', fontsize=14, fontweight='bold')
        axes[0].set_ylabel('IC值')
        axes[0].legend(loc='best')
        axes[0].grid(True, alpha=0.3)

        # 2. IC分布图
        ic_clean = ic_series.dropna()
        axes[1].hist(ic_clean, bins=30, density=True, alpha=0.7, edgecolor='black', color='steelblue')
        axes[1].axvline(x=ic_clean.mean(), color='red', linestyle='--',
                       linewidth=2, label=f'均值: {ic_clean.mean():.4f}')
        axes[1].axvline(x=0, color='black', linestyle='-', linewidth=1, label='零线')
        axes[1].set_title(f'{factor_name} - IC分布', fontsize=14, fontweight='bold')
        axes[1].set_xlabel('IC值')
        axes[1].set_ylabel('密度')
        axes[1].legend(loc='best')
        axes[1].grid(True, alpha=0.3)

        # 3. IC累计统计图
        cumulative_ic = ic_series.cumsum()
        axes[2].plot(cumulative_ic.index, cumulative_ic.values,
                    linewidth=2, color='darkblue', label='累计IC')
        axes[2].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        axes[2].set_title(f'{factor_name} - 累计IC', fontsize=14, fontweight='bold')
        axes[2].set_xlabel('期数')
        axes[2].set_ylabel('累计IC')
        axes[2].legend(loc='best')
        axes[2].grid(True, alpha=0.3)

        plt.tight_layout()

        self.figures['ic_analysis'] = fig
        return fig

    def plot_group_backtest(self,
                           group_returns: pd.DataFrame,
                           long_short_returns: Optional[pd.DataFrame] = None,
                           factor_name: str = "因子",
                           figsize: Tuple[int, int] = (14, 8)) -> plt.Figure:
        """
        绘制分组回测图表

        参数:
            group_returns: 分组收益DataFrame
            long_short_returns: 多空收益（可选）
            factor_name: 因子名称
            figsize: 图表大小

        返回:
            plt.Figure: 图表对象
        """
        fig, axes = plt.subplots(2, 1, figsize=figsize)

        # 1. 分组累计收益
        cumulative_group_returns = (1 + group_returns).cumprod()

        for col in cumulative_group_returns.columns:
            col_str = str(col)
            if 'group' in col_str.lower() or col_str.isdigit():
                axes[0].plot(cumulative_group_returns.index,
                           cumulative_group_returns[col],
                           label=f'Group {col}',
                           linewidth=1.5, alpha=0.8)

        axes[0].set_title(f'{factor_name} - 分组累计收益', fontsize=14, fontweight='bold')
        axes[0].set_ylabel('累计净值')
        axes[0].legend(loc='best', ncol=2)
        axes[0].grid(True, alpha=0.3)

        # 2. 多空收益
        if long_short_returns is not None and 'long_short_return' in long_short_returns.columns:
            ls_returns = long_short_returns['long_short_return']
            cumulative_ls = (1 + ls_returns).cumprod()

            color = 'darkgreen' if cumulative_ls.iloc[-1] > 1 else 'darkred'
            axes[1].fill_between(cumulative_ls.index, 1, cumulative_ls.values,
                                alpha=0.3, color=color)
            axes[1].plot(cumulative_ls.index, cumulative_ls.values,
                        linewidth=2, color=color, label='多空策略')
            axes[1].axhline(y=1, color='black', linestyle='-', linewidth=0.5)

            axes[1].set_title(f'{factor_name} - 多空策略累计收益', fontsize=14, fontweight='bold')
            axes[1].set_xlabel('日期')
            axes[1].set_ylabel('累计净值')
            axes[1].legend(loc='best')
            axes[1].grid(True, alpha=0.3)
        else:
            # 如果没有多空收益，显示分组收益的最后一个时间点的对比
            final_returns = cumulative_group_returns.iloc[-1].sort_values(ascending=False)
            colors_bar = ['green' if x > 1 else 'red' for x in final_returns.values]
            axes[1].bar(range(len(final_returns)), final_returns.values, color=colors_bar, alpha=0.7)
            axes[1].axhline(y=1, color='black', linestyle='-', linewidth=0.5)
            axes[1].set_xticks(range(len(final_returns)))
            axes[1].set_xticklabels([f'G{x}' for x in final_returns.index])
            axes[1].set_title(f'{factor_name} - 最终分组收益对比', fontsize=14, fontweight='bold')
            axes[1].set_xlabel('分组')
            axes[1].set_ylabel('累计净值')
            axes[1].grid(True, alpha=0.3)

        plt.tight_layout()

        self.figures['group_backtest'] = fig
        return fig

    def plot_performance_metrics(self,
                                 returns_series: pd.Series,
                                 benchmark_returns: Optional[pd.Series] = None,
                                 factor_name: str = "策略",
                                 figsize: Tuple[int, int] = (14, 10)) -> plt.Figure:
        """
        绘制绩效评估图表

        参数:
            returns_series: 收益率序列
            benchmark_returns: 基准收益率（可选）
            factor_name: 策略名称
            figsize: 图表大小

        返回:
            plt.Figure: 图表对象
        """
        fig, axes = plt.subplots(3, 1, figsize=figsize)

        # 1. 净值曲线
        cumulative = (1 + returns_series).cumprod()
        axes[0].plot(cumulative.index, cumulative.values,
                    linewidth=2, label=factor_name, color='blue')

        if benchmark_returns is not None and len(benchmark_returns) > 0:
            benchmark_cumulative = (1 + benchmark_returns[:len(cumulative)]).cumprod()
            axes[0].plot(benchmark_cumulative.index, benchmark_cumulative.values,
                        linewidth=2, label='基准', color='orange', linestyle='--')

        axes[0].set_title(f'{factor_name} - 净值曲线', fontsize=14, fontweight='bold')
        axes[0].set_ylabel('净值')
        axes[0].legend(loc='best')
        axes[0].grid(True, alpha=0.3)

        # 2. 回撤分析
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max

        axes[1].fill_between(drawdown.index, drawdown.values, 0,
                            alpha=0.3, color='red')
        axes[1].plot(drawdown.index, drawdown.values,
                    color='darkred', linewidth=1)

        # 标记最大回撤
        max_dd_idx = drawdown.idxmin()
        max_dd_value = drawdown.min()
        axes[1].annotate(f'最大回撤: {max_dd_value:.2%}',
                        xy=(max_dd_idx, max_dd_value),
                        xytext=(10, 10), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

        axes[1].set_title(f'{factor_name} - 回撤分析', fontsize=14, fontweight='bold')
        axes[1].set_xlabel('日期')
        axes[1].set_ylabel('回撤')
        axes[1].grid(True, alpha=0.3)

        # 3. 收益分布
        returns_clean = returns_series.dropna()
        axes[2].hist(returns_clean, bins=50, density=True, alpha=0.7,
                    edgecolor='black', color='steelblue')
        axes[2].axvline(x=returns_clean.mean(), color='red', linestyle='--',
                       linewidth=2, label=f'均值: {returns_clean.mean():.4f}')
        axes[2].axvline(x=0, color='black', linestyle='-', linewidth=1, label='零线')
        axes[2].set_title(f'{factor_name} - 收益分布', fontsize=14, fontweight='bold')
        axes[2].set_xlabel('收益率')
        axes[2].set_ylabel('密度')
        axes[2].legend(loc='best')
        axes[2].grid(True, alpha=0.3)

        plt.tight_layout()

        self.figures['performance_metrics'] = fig
        return fig

    def plot_specific_volatility(self,
                                 spec_vol_data: pd.DataFrame,
                                 factor_name: str = "特质波动率",
                                 figsize: Tuple[int, int] = (14, 8)) -> plt.Figure:
        """
        绘制特质波动率图表

        参数:
            spec_vol_data: 特质波动率数据（可以是单列或多列）
            factor_name: 因子名称
            figsize: 图表大小

        返回:
            plt.Figure: 图表对象
        """
        if isinstance(spec_vol_data, pd.Series):
            spec_vol_data = spec_vol_data.to_frame()

        fig, axes = plt.subplots(2, 1, figsize=figsize)

        # 1. 特质波动率时序图
        for col in spec_vol_data.columns:
            axes[0].plot(spec_vol_data.index, spec_vol_data[col],
                        label=col, linewidth=1.5, alpha=0.8)

        axes[0].set_title(f'{factor_name} - 时序图', fontsize=14, fontweight='bold')
        axes[0].set_ylabel('特质波动率')
        axes[0].legend(loc='best')
        axes[0].grid(True, alpha=0.3)

        # 2. 特质波动率分布
        for col in spec_vol_data.columns:
            data_clean = spec_vol_data[col].dropna()
            axes[1].hist(data_clean, bins=30, density=True, alpha=0.5,
                        edgecolor='black', label=col)

        axes[1].set_title(f'{factor_name} - 分布', fontsize=14, fontweight='bold')
        axes[1].set_xlabel('特质波动率')
        axes[1].set_ylabel('密度')
        axes[1].legend(loc='best')
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()

        self.figures['specific_volatility'] = fig
        return fig

    def plot_monotonicity_analysis(self,
                                  group_avg_returns: pd.Series,
                                  correlation: float,
                                  trend: str,
                                  factor_name: str = "因子",
                                  figsize: Tuple[int, int] = (12, 6)) -> plt.Figure:
        """
        绘制单调性分析图表

        参数:
            group_avg_returns: 各组平均收益
            correlation: 相关系数
            trend: 趋势类型
            factor_name: 因子名称
            figsize: 图表大小

        返回:
            plt.Figure: 图表对象
        """
        fig, ax = plt.subplots(figsize=figsize)

        # 绘制柱状图
        colors = ['green' if x > 0 else 'red' for x in group_avg_returns.values]
        ax.bar(range(len(group_avg_returns)), group_avg_returns.values,
               color=colors, alpha=0.7, edgecolor='black')

        # 添加趋势线
        z = np.polyfit(range(len(group_avg_returns)), group_avg_returns.values, 1)
        p = np.poly1d(z)
        ax.plot(range(len(group_avg_returns)), p(range(len(group_avg_returns))),
                "r--", alpha=0.8, linewidth=2, label='趋势线')

        # 标注信息
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax.set_xticks(range(len(group_avg_returns)))
        ax.set_xticklabels([f'G{i+1}' for i in range(len(group_avg_returns))])

        title_text = f'{factor_name} - 分组单调性分析\n'
        title_text += f'趋势: {trend} | 相关系数: {correlation:.4f}'
        ax.set_title(title_text, fontsize=14, fontweight='bold')
        ax.set_xlabel('分组')
        ax.set_ylabel('平均收益')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        self.figures['monotonicity_analysis'] = fig
        return fig

    def create_dashboard(self,
                        ic_series: Optional[pd.Series] = None,
                        group_returns: Optional[pd.DataFrame] = None,
                        performance_returns: Optional[pd.Series] = None,
                        factor_name: str = "因子") -> plt.Figure:
        """
        创建综合仪表板

        参数:
            ic_series: IC序列（可选）
            group_returns: 分组收益（可选）
            performance_returns: 绩效收益（可选）
            factor_name: 因子名称

        返回:
            plt.Figure: 图表对象
        """
        n_plots = sum([
            ic_series is not None,
            group_returns is not None,
            performance_returns is not None
        ])

        if n_plots == 0:
            raise ValueError("至少需要提供一种数据")

        fig, axes = plt.subplots(n_plots, 1, figsize=(14, 6 * n_plots))

        if n_plots == 1:
            axes = [axes]

        plot_idx = 0

        # IC分析
        if ic_series is not None:
            colors = ['red' if x < 0 else 'green' for x in ic_series.values]
            axes[plot_idx].bar(range(len(ic_series)), ic_series.values,
                              color=colors, alpha=0.7)
            axes[plot_idx].axhline(y=ic_series.mean(), color='blue',
                                  linestyle='--', linewidth=1,
                                  label=f'均值: {ic_series.mean():.4f}')
            axes[plot_idx].set_title(f'{factor_name} - IC分析', fontsize=14, fontweight='bold')
            axes[plot_idx].set_ylabel('IC值')
            axes[plot_idx].legend(loc='best')
            axes[plot_idx].grid(True, alpha=0.3)
            plot_idx += 1

        # 分组回测
        if group_returns is not None:
            cumulative_group_returns = (1 + group_returns).cumprod()
            for col in cumulative_group_returns.columns:
                if 'group' in str(col).lower() or col.isdigit():
                    axes[plot_idx].plot(cumulative_group_returns.index,
                                       cumulative_group_returns[col],
                                       label=f'G{col}', linewidth=1.5, alpha=0.8)
            axes[plot_idx].set_title(f'{factor_name} - 分组收益', fontsize=14, fontweight='bold')
            axes[plot_idx].set_ylabel('累计净值')
            axes[plot_idx].legend(loc='best', ncol=2)
            axes[plot_idx].grid(True, alpha=0.3)
            plot_idx += 1

        # 绩效分析
        if performance_returns is not None:
            cumulative = (1 + performance_returns).cumprod()
            axes[plot_idx].plot(cumulative.index, cumulative.values,
                               linewidth=2, label=factor_name)
            axes[plot_idx].set_title(f'{factor_name} - 累计收益', fontsize=14, fontweight='bold')
            axes[plot_idx].set_xlabel('日期')
            axes[plot_idx].set_ylabel('累计净值')
            axes[plot_idx].legend(loc='best')
            axes[plot_idx].grid(True, alpha=0.3)

        plt.tight_layout()

        self.figures['dashboard'] = fig
        return fig

    def save_figure(self, figure_name: str, save_path: str, dpi: int = 300):
        """
        保存图表

        参数:
            figure_name: 图表名称（在self.figures中的键）
            save_path: 保存路径
            dpi: 分辨率
        """
        if figure_name not in self.figures:
            raise ValueError(f"图表 {figure_name} 不存在")

        self.figures[figure_name].savefig(save_path, dpi=dpi, bbox_inches='tight')
        print(f"[OK] 图表已保存到: {save_path}")

    def show_all(self):
        """显示所有图表"""
        for fig_name, fig in self.figures.items():
            print(f"显示图表: {fig_name}")
            plt.show(fig)


# 导出接口
__all__ = [
    'FactorAnalysisVisualizer'
]
