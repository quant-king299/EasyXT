"""
分层回测模块
用于验证因子的有效性

功能：
1. 根据因子值将股票分为多层
2. 计算各层的收益率
3. 计算回测指标（夏普比率、最大回撤、年化收益等）
4. 多空策略收益计算
5. 生成可视化报告

作者：EasyXT团队
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
import warnings
warnings.filterwarnings('ignore')


class LayeredBacktester:
    """
    分层回测器

    功能：
    1. 根据因子值将股票分层
    2. 计算各层收益率
    3. 计算回测性能指标
    4. 多空策略回测
    """

    def __init__(
        self,
        price_data: pd.DataFrame,
        factor_data: pd.DataFrame
    ):
        """
        初始化分层回测器

        参数：
        ----------
        price_data : pd.DataFrame
            价格数据，索引为日期，列为股票代码
            格式：DataFrame(index=date, columns=stock_code, values=close_price)
        factor_data : pd.DataFrame
            因子数据，索引为日期，列为股票代码
            格式：DataFrame(index=date, columns=stock_code, values=factor_value)
        """
        self.price_data = price_data.sort_index()
        self.factor_data = factor_data.sort_index()

        # 数据对齐
        self.common_dates = sorted(set(price_data.index) & set(factor_data.index))
        self.common_stocks = sorted(set(price_data.columns) & set(factor_data.columns))

        if len(self.common_dates) == 0:
            raise ValueError("价格数据和因子数据没有共同的日期")

        if len(self.common_stocks) == 0:
            raise ValueError("价格数据和因子数据没有共同的股票")

        # 截取共同数据
        self.price_data = price_data.loc[self.common_dates, self.common_stocks]
        self.factor_data = factor_data.loc[self.common_dates, self.common_stocks]

        # 回测结果存储
        self.layer_returns = None
        self.long_short_returns = None
        self.backtest_metrics = None
        self.layer_positions = None

    def calculate_returns(
        self,
        periods: int = 1,
        return_type: str = 'simple'
    ) -> pd.DataFrame:
        """
        计算收益率

        参数：
        ----------
        periods : int
            未来期数
        return_type : str
            收益率类型，'simple'为简单收益率，'log'为对数收益率

        返回：
        ----------
        returns : pd.DataFrame
            收益率矩阵
        """
        if return_type == 'simple':
            # 简单收益率
            returns = self.price_data.pct_change(periods).shift(-periods)
        elif return_type == 'log':
            # 对数收益率
            returns = np.log(self.price_data).diff(periods).shift(-periods)
        else:
            raise ValueError(f"未知的收益率类型: {return_type}")

        # 移除最后periods行
        returns = returns.iloc[:-periods]
        self.factor_data = self.factor_data.iloc[:-periods]

        return returns

    def create_layers(
        self,
        n_layers: int = 5,
        method: str = 'quantile'
    ) -> Dict[int, List[str]]:
        """
        根据因子值将股票分层

        参数：
        ----------
        n_layers : int
            分层数量，默认为5
        method : str
            分层方法，'quantile'为等分位数，'equal_weight'为等权重

        返回：
        ----------
        layer_positions : Dict[int, List[str]]
            每层的股票列表，key为层号（0为最低因子值层，n_layers-1为最高因子值层）
        """
        layer_positions = {}

        for date in self.factor_data.index:
            factor_values = self.factor_data.loc[date].dropna()

            if len(factor_values) < n_layers:
                # 如果股票数量太少，跳过
                continue

            if method == 'quantile':
                # 等分位数分层
                quantiles = pd.qcut(factor_values, n_layers, labels=False, duplicates='drop')
            elif method == 'equal_weight':
                # 等数量分层
                sorted_stocks = factor_values.sort_values().index.tolist()
                n_per_layer = len(sorted_stocks) // n_layers

                quantiles = pd.Series(index=factor_values.index, dtype=int)
                for i in range(n_layers):
                    if i == n_layers - 1:
                        quantiles[sorted_stocks[i * n_per_layer:]] = i
                    else:
                        quantiles[sorted_stocks[i * n_per_layer:(i + 1) * n_per_layer]] = i
            else:
                raise ValueError(f"未知的分层方法: {method}")

            layer_positions[date] = {}

            for layer_id in range(n_layers):
                stocks_in_layer = quantiles[quantiles == layer_id].index.tolist()
                layer_positions[date][layer_id] = stocks_in_layer

        self.layer_positions = layer_positions
        self.n_layers = n_layers

        return layer_positions

    def calculate_layer_returns(
        self,
        n_layers: int = 5,
        periods: int = 1,
        method: str = 'quantile',
        return_type: str = 'simple'
    ) -> pd.DataFrame:
        """
        计算各层收益率

        参数：
        ----------
        n_layers : int
            分层数量
        periods : int
            持有期数
        method : str
            分层方法
        return_type : str
            收益率类型

        返回：
        ----------
        layer_returns : pd.DataFrame
            各层收益率时间序列，索引为日期，列为各层收益率
        """
        # 分层
        self.create_layers(n_layers=n_layers, method=method)

        # 计算收益率
        returns = self.calculate_returns(periods=periods, return_type=return_type)

        # 计算各层平均收益率
        layer_returns_list = []

        for date in self.layer_positions.keys():
            if date not in returns.index:
                continue

            layer_return = {}
            returns_on_date = returns.loc[date]

            for layer_id in range(n_layers):
                stocks_in_layer = self.layer_positions[date][layer_id]

                # 计算该层所有股票的平均收益率
                layer_stocks_returns = returns_on_date[stocks_in_layer]
                layer_return[layer_id] = layer_stocks_returns.mean()

            layer_returns_list.append(layer_return)

        self.layer_returns = pd.DataFrame(layer_returns_list)

        return self.layer_returns

    def calculate_long_short_returns(
        self,
        n_layers: int = 5,
        periods: int = 1,
        method: str = 'quantile',
        long_layer: int = -1,  # 做多最高层
        short_layer: int = 0   # 做空最低层
    ) -> pd.Series:
        """
        计算多空策略收益率

        参数：
        ----------
        n_layers : int
            分层数量
        periods : int
            持有期数
        method : str
            分层方法
        long_layer : int
            做多层，-1表示最高层
        short_layer : int
            做空层，0表示最低层

        返回：
        ----------
        long_short_returns : pd.Series
            多空策略收益率时间序列
        """
        # 计算各层收益率
        if self.layer_returns is None or self.layer_returns.shape[1] != n_layers:
            self.calculate_layer_returns(
                n_layers=n_layers,
                periods=periods,
                method=method
            )

        # 确定做多和做空层
        if long_layer == -1:
            long_layer = n_layers - 1

        # 计算多空收益
        long_short_returns = (
            self.layer_returns[long_layer] -
            self.layer_returns[short_layer]
        )

        self.long_short_returns = long_short_returns

        return long_short_returns

    def calculate_backtest_metrics(
        self,
        returns: Optional[pd.Series] = None,
        annualization_factor: int = 252
    ) -> Dict[str, float]:
        """
        计算回测性能指标

        参数：
        ----------
        returns : pd.Series, optional
            收益率序列，如果为None则使用多空收益
        annualization_factor : int
            年化系数，默认252（交易日）

        返回：
        ----------
        metrics : Dict[str, float]
            回测指标字典，包含：
            - total_return: 总收益率
            - annual_return: 年化收益率
            - sharpe_ratio: 夏普比率
            - max_drawdown: 最大回撤
            - win_rate: 胜率
            - profit_loss_ratio: 盈亏比
        """
        if returns is None:
            returns = self.long_short_returns

        if returns is None:
            raise ValueError("请先计算多空收益率或传入收益率序列")

        returns = returns.dropna()

        if len(returns) == 0:
            raise ValueError("没有有效的收益率数据")

        # 总收益率
        total_return = (1 + returns).prod() - 1

        # 年化收益率
        n_periods = len(returns)
        annual_return = (1 + total_return) ** (annualization_factor / n_periods) - 1

        # 夏普比率
        mean_return = returns.mean()
        std_return = returns.std()
        sharpe_ratio = mean_return / std_return * np.sqrt(annualization_factor) if std_return != 0 else 0

        # 最大回撤
        cumulative_returns = (1 + returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()

        # 胜率
        win_rate = (returns > 0).sum() / len(returns)

        # 盈亏比
        profit_returns = returns[returns > 0]
        loss_returns = returns[returns < 0]
        avg_profit = profit_returns.mean() if len(profit_returns) > 0 else 0
        avg_loss = abs(loss_returns.mean()) if len(loss_returns) > 0 else 0
        profit_loss_ratio = avg_profit / avg_loss if avg_loss != 0 else 0

        # 波动率
        volatility = returns.std() * np.sqrt(annualization_factor)

        # Calmar比率（年化收益/最大回撤绝对值）
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

        self.backtest_metrics = {
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'volatility': volatility,
            'calmar_ratio': calmar_ratio,
            'n_periods': n_periods
        }

        return self.backtest_metrics

    def generate_layer_statistics(self) -> pd.DataFrame:
        """
        生成分层统计报告

        返回：
        ----------
        stats : pd.DataFrame
            分层统计报告
        """
        if self.layer_returns is None:
            raise ValueError("请先调用calculate_layer_returns()计算分层收益")

        stats_data = []

        for layer_id in self.layer_returns.columns:
            layer_return = self.layer_returns[layer_id].dropna()

            stats_data.append({
                '分层': f'第{layer_id + 1}层',
                '平均收益率': layer_return.mean(),
                '收益率标准差': layer_return.std(),
                '夏普比率': layer_return.mean() / layer_return.std() if layer_return.std() != 0 else 0,
                '胜率': (layer_return > 0).sum() / len(layer_return),
                '总收益率': (1 + layer_return).prod() - 1,
                '最大回撤': self._calculate_max_drawdown(layer_return)
            })

        stats_df = pd.DataFrame(stats_data)

        return stats_df

    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """计算最大回撤"""
        cumulative_returns = (1 + returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        return drawdown.min()

    def generate_report(self) -> pd.DataFrame:
        """
        生成回测报告

        返回：
        ----------
        report : pd.DataFrame
            回测报告
        """
        if self.backtest_metrics is None:
            self.calculate_backtest_metrics()

        # 创建报告DataFrame
        report_data = {
            '指标': [
                '总收益率',
                '年化收益率',
                '夏普比率',
                '最大回撤',
                '胜率',
                '盈亏比',
                '年化波动率',
                'Calmar比率',
                '交易次数'
            ],
            '数值': [
                f"{self.backtest_metrics['total_return']:.2%}",
                f"{self.backtest_metrics['annual_return']:.2%}",
                f"{self.backtest_metrics['sharpe_ratio']:.4f}",
                f"{self.backtest_metrics['max_drawdown']:.2%}",
                f"{self.backtest_metrics['win_rate']:.2%}",
                f"{self.backtest_metrics['profit_loss_ratio']:.4f}",
                f"{self.backtest_metrics['volatility']:.2%}",
                f"{self.backtest_metrics['calmar_ratio']:.4f}",
                f"{self.backtest_metrics['n_periods']:.0f}"
            ],
            '说明': [
                '整个回测期间的总收益',
                '年化后的收益率',
                '收益风险比，>1为优秀',
                '最大回撤幅度（负数）',
                '盈利交易占比',
                '平均盈利/平均亏损',
                '年化波动率',
                '年化收益/最大回撤绝对值',
                '总交易次数'
            ]
        }

        report = pd.DataFrame(report_data)

        return report

    def print_report(self):
        """打印回测报告"""
        if self.backtest_metrics is None:
            self.calculate_backtest_metrics()

        print("=" * 80)
        print("多空策略回测报告")
        print("=" * 80)
        print(f"{'指标':<20} {'数值':<15} {'说明'}")
        print("-" * 80)

        report_map = {
            'total_return': ('总收益率', '整个回测期间的总收益'),
            'annual_return': ('年化收益率', '年化后的收益率'),
            'sharpe_ratio': ('夏普比率', '收益风险比，>1为优秀'),
            'max_drawdown': ('最大回撤', '最大回撤幅度（负数）'),
            'win_rate': ('胜率', '盈利交易占比'),
            'profit_loss_ratio': ('盈亏比', '平均盈利/平均亏损'),
            'volatility': ('年化波动率', '年化波动率'),
            'calmar_ratio': ('Calmar比率', '年化收益/最大回撤绝对值'),
            'n_periods': ('交易次数', '总交易次数')
        }

        for key, (name, desc) in report_map.items():
            value = self.backtest_metrics[key]
            if key in ['total_return', 'annual_return', 'max_drawdown', 'win_rate', 'volatility']:
                value_str = f"{value:.2%}"
            elif key == 'n_periods':
                value_str = f"{value:.0f}"
            else:
                value_str = f"{value:.4f}"
            print(f"{name:<20} {value_str:<15} {desc}")

        print("=" * 80)

        # 策略评级
        sharpe = self.backtest_metrics['sharpe_ratio']
        annual_return = self.backtest_metrics['annual_return']

        print("\n策略评级：", end="")
        if sharpe >= 2.0 and annual_return > 0.1:
            print("优秀 ⭐⭐⭐⭐⭐")
        elif sharpe >= 1.5 and annual_return > 0.05:
            print("良好 ⭐⭐⭐⭐")
        elif sharpe >= 1.0 and annual_return > 0:
            print("中等 ⭐⭐⭐")
        elif sharpe >= 0.5:
            print("一般 ⭐⭐")
        else:
            print("较差 ⭐")

        print("=" * 80)

        # 分层统计
        if self.layer_returns is not None:
            print("\n分层收益统计：")
            print("-" * 80)

            layer_stats = self.generate_layer_statistics()
            print(layer_stats.to_string(index=False))

            print("=" * 80)

    def save_returns(self, filepath: str):
        """保存收益率数据到文件"""
        if self.long_short_returns is not None:
            self.long_short_returns.to_csv(filepath)
            print(f"多空收益率已保存到: {filepath}")
        elif self.layer_returns is not None:
            self.layer_returns.to_csv(filepath)
            print(f"分层收益率已保存到: {filepath}")
        else:
            raise ValueError("没有可保存的收益率数据")

    def save_report(self, filepath: str):
        """保存回测报告到文件"""
        report = self.generate_report()
        report.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"回测报告已保存到: {filepath}")


# 使用示例
if __name__ == "__main__":
    # 生成示例数据
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
    stocks = [f'{i:06d}.SZ' for i in range(1, 101)]  # 100只股票

    # 生成随机价格数据（模拟上涨趋势）
    trend = np.linspace(0, 0.3, len(dates))
    price_data = pd.DataFrame(
        np.random.randn(len(dates), len(stocks)) * 0.02 + trend.reshape(-1, 1) + 1,
        index=dates,
        columns=stocks
    ).cumprod() * 10

    # 生成随机因子数据
    factor_data = pd.DataFrame(
        np.random.randn(len(dates), len(stocks)),
        index=dates,
        columns=stocks
    )

    # 创建回测器
    backtester = LayeredBacktester(price_data, factor_data)

    # 计算分层收益
    backtester.calculate_layer_returns(
        n_layers=5,
        periods=1,
        method='quantile'
    )

    # 计算多空收益
    backtester.calculate_long_short_returns(
        n_layers=5,
        periods=1,
        method='quantile'
    )

    # 计算回测指标
    backtester.calculate_backtest_metrics()

    # 打印报告
    backtester.print_report()

    # 保存结果
    backtester.save_returns('long_short_returns.csv')
    backtester.save_report('backtest_report.csv')
