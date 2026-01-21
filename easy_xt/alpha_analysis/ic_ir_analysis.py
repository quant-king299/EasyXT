"""
IC/IR分析模块
用于评估因子的预测能力

IC (Information Coefficient) - 信息系数：衡量因子值与未来收益率的相关性
IR (Information Ratio) - 信息比率：IC均值与IC标准差的比值，衡量因子稳定性

作者：EasyXT团队
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class ICIRAnalyzer:
    """
    IC/IR分析器

    功能：
    1. 计算日度IC值（因子值与未来收益率的相关系数）
    2. 计算IC统计指标（均值、标准差、IR、t统计量）
    3. IC时序分析
    4. IC分布分析
    5. 生成可视化报告
    """

    def __init__(self, price_data: pd.DataFrame, factor_data: pd.DataFrame):
        """
        初始化IC/IR分析器

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

        # 分析结果存储
        self.ic_series = None
        self.ic_stats = None
        self.forward_returns = None

    def calculate_forward_returns(
        self,
        periods: int = 1,
        return_type: str = 'simple'
    ) -> pd.DataFrame:
        """
        计算未来收益率

        参数：
        ----------
        periods : int
            未来期数，默认为1（下一期）
        return_type : str
            收益率类型，'simple'为简单收益率，'log'为对数收益率

        返回：
        ----------
        forward_returns : pd.DataFrame
            未来收益率矩阵
        """
        if return_type == 'simple':
            # 简单收益率: (P_t+n - P_t) / P_t
            self.forward_returns = self.price_data.pct_change(periods).shift(-periods)
        elif return_type == 'log':
            # 对数收益率: log(P_t+n) - log(P_t)
            self.forward_returns = np.log(self.price_data).diff(periods).shift(-periods)
        else:
            raise ValueError(f"未知的收益率类型: {return_type}")

        # 移除最后periods行（因为没有未来数据）
        self.forward_returns = self.forward_returns.iloc[:-periods]
        self.factor_data = self.factor_data.iloc[:-periods]

        return self.forward_returns

    def calculate_ic(
        self,
        periods: int = 1,
        return_type: str = 'simple',
        method: str = 'pearson'
    ) -> pd.Series:
        """
        计算IC值（因子值与未来收益率的相关系数）

        参数：
        ----------
        periods : int
            未来期数，默认为1
        return_type : str
            收益率类型
        method : str
            相关系数计算方法，'pearson'或'spearman'

        返回：
        ----------
        ic_series : pd.Series
            IC时间序列，索引为日期
        """
        # 计算未来收益率
        if self.forward_returns is None or periods != 1:
            self.calculate_forward_returns(periods=periods, return_type=return_type)

        # 计算每日IC
        ic_list = []
        dates = []

        for date in self.factor_data.index:
            factor_values = self.factor_data.loc[date]
            return_values = self.forward_returns.loc[date]

            # 移除NaN值
            valid_mask = ~(factor_values.isna() | return_values.isna())
            factor_valid = factor_values[valid_mask]
            return_valid = return_values[valid_mask]

            if len(factor_valid) < 10:  # 至少需要10个样本
                continue

            # 计算相关系数
            if method == 'pearson':
                ic = factor_valid.corr(return_valid, method='pearson')
            elif method == 'spearman':
                ic = factor_valid.corr(return_valid, method='spearman')
            else:
                raise ValueError(f"未知的相关系数计算方法: {method}")

            ic_list.append(ic)
            dates.append(date)

        self.ic_series = pd.Series(ic_list, index=dates, name='IC')

        return self.ic_series

    def calculate_ic_stats(self) -> Dict[str, float]:
        """
        计算IC统计指标

        返回：
        ----------
        ic_stats : Dict[str, float]
            IC统计指标字典，包含：
            - ic_mean: IC均值
            - ic_std: IC标准差
            - ir: 信息比率 (IC均值/IC标准差)
            - ic_skew: IC偏度
            - ic_kurt: IC峰度
            - t_stat: t统计量 (IC均值 * sqrt(N) / IC标准差)
            - positive_ic_ratio: 正IC占比
        """
        if self.ic_series is None:
            raise ValueError("请先调用calculate_ic()计算IC值")

        ic_values = self.ic_series.dropna()
        n = len(ic_values)

        if n == 0:
            raise ValueError("没有有效的IC值")

        ic_mean = ic_values.mean()
        ic_std = ic_values.std()
        ir = ic_mean / ic_std if ic_std != 0 else 0

        # t统计量
        t_stat = ic_mean * np.sqrt(n) / ic_std if ic_std != 0 else 0

        # 偏度和峰度
        ic_skew = ic_values.skew()
        ic_kurt = ic_values.kurtosis()

        # 正IC占比
        positive_ic_ratio = (ic_values > 0).sum() / n

        # 绝对值均值
        abs_ic_mean = abs(ic_values).mean()

        self.ic_stats = {
            'ic_mean': ic_mean,
            'ic_std': ic_std,
            'ir': ir,
            'ic_skew': ic_skew,
            'ic_kurt': ic_kurt,
            't_stat': t_stat,
            'positive_ic_ratio': positive_ic_ratio,
            'abs_ic_mean': abs_ic_mean,
            'ic_count': n
        }

        return self.ic_stats

    def get_ic_rolling_stats(
        self,
        window: int = 20
    ) -> pd.DataFrame:
        """
        计算IC滚动统计指标

        参数：
        ----------
        window : int
            滚动窗口大小

        返回：
        ----------
        rolling_stats : pd.DataFrame
            滚动统计指标，包含：
            - rolling_mean: 滚动IC均值
            - rolling_std: 滚动IC标准差
            - rolling_ir: 滚动IR
        """
        if self.ic_series is None:
            raise ValueError("请先调用calculate_ic()计算IC值")

        rolling_mean = self.ic_series.rolling(window).mean()
        rolling_std = self.ic_series.rolling(window).std()
        rolling_ir = rolling_mean / rolling_std

        rolling_stats = pd.DataFrame({
            'rolling_mean': rolling_mean,
            'rolling_std': rolling_std,
            'rolling_ir': rolling_ir
        })

        return rolling_stats

    def generate_report(self) -> pd.DataFrame:
        """
        生成IC/IR分析报告

        返回：
        ----------
        report : pd.DataFrame
            分析报告，包含所有IC统计指标
        """
        if self.ic_stats is None:
            self.calculate_ic_stats()

        # 创建报告DataFrame
        report_data = {
            '指标': [
                'IC均值',
                'IC标准差',
                'IR (信息比率)',
                'IC偏度',
                'IC峰度',
                't统计量',
                '正IC占比',
                'IC绝对值均值',
                'IC样本数'
            ],
            '数值': [
                f"{self.ic_stats['ic_mean']:.4f}",
                f"{self.ic_stats['ic_std']:.4f}",
                f"{self.ic_stats['ir']:.4f}",
                f"{self.ic_stats['ic_skew']:.4f}",
                f"{self.ic_stats['ic_kurt']:.4f}",
                f"{self.ic_stats['t_stat']:.4f}",
                f"{self.ic_stats['positive_ic_ratio']:.2%}",
                f"{self.ic_stats['abs_ic_mean']:.4f}",
                f"{self.ic_stats['ic_count']:.0f}"
            ],
            '说明': [
                'IC均值越大，因子预测能力越强',
                'IC标准差越小，因子稳定性越好',
                'IR>0.5为良好，IR>1为优秀',
                '衡量IC分布的对称性',
                '衡量IC分布的尖峰程度',
                'IC显著性的统计检验',
                '正IC占比越高越好',
                'IC绝对值的平均大小',
                '有效IC样本数量'
            ]
        }

        report = pd.DataFrame(report_data)

        return report

    def print_report(self):
        """打印IC/IR分析报告"""
        if self.ic_stats is None:
            self.calculate_ic_stats()

        print("=" * 80)
        print("IC/IR分析报告")
        print("=" * 80)
        print(f"{'指标':<20} {'数值':<15} {'说明'}")
        print("-" * 80)

        report_map = {
            'ic_mean': ('IC均值', 'IC均值越大，因子预测能力越强'),
            'ic_std': ('IC标准差', 'IC标准差越小，因子稳定性越好'),
            'ir': ('IR (信息比率)', 'IR>0.5为良好，IR>1为优秀'),
            'ic_skew': ('IC偏度', '衡量IC分布的对称性'),
            'ic_kurt': ('IC峰度', '衡量IC分布的尖峰程度'),
            't_stat': ('t统计量', 'IC显著性的统计检验'),
            'positive_ic_ratio': ('正IC占比', '正IC占比越高越好'),
            'abs_ic_mean': ('IC绝对值均值', 'IC绝对值的平均大小'),
            'ic_count': ('IC样本数', '有效IC样本数量')
        }

        for key, (name, desc) in report_map.items():
            value = self.ic_stats[key]
            if key == 'positive_ic_ratio':
                value_str = f"{value:.2%}"
            elif key == 'ic_count':
                value_str = f"{value:.0f}"
            else:
                value_str = f"{value:.4f}"
            print(f"{name:<20} {value_str:<15} {desc}")

        print("=" * 80)

        # 因子评级
        ir = self.ic_stats['ir']
        ic_mean = self.ic_stats['ic_mean']

        print("\n因子评级：", end="")
        if abs(ir) >= 1.0 and abs(ic_mean) >= 0.05:
            print("优秀 ⭐⭐⭐⭐⭐")
        elif abs(ir) >= 0.7 and abs(ic_mean) >= 0.03:
            print("良好 ⭐⭐⭐⭐")
        elif abs(ir) >= 0.5 and abs(ic_mean) >= 0.02:
            print("中等 ⭐⭐⭐")
        elif abs(ir) >= 0.3 and abs(ic_mean) >= 0.01:
            print("一般 ⭐⭐")
        else:
            print("较差 ⭐")

        print("=" * 80)

    def save_ic_series(self, filepath: str):
        """
        保存IC时间序列到文件

        参数：
        ----------
        filepath : str
            保存路径（CSV格式）
        """
        if self.ic_series is None:
            raise ValueError("请先调用calculate_ic()计算IC值")

        self.ic_series.to_csv(filepath)
        print(f"IC时间序列已保存到: {filepath}")

    def save_report(self, filepath: str):
        """
        保存分析报告到文件

        参数：
        ----------
        filepath : str
            保存路径（CSV格式）
        """
        report = self.generate_report()
        report.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"分析报告已保存到: {filepath}")


# 使用示例
if __name__ == "__main__":
    # 生成示例数据
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
    stocks = [f'{i:06d}.SZ' for i in range(1, 101)]  # 100只股票

    # 生成随机价格数据
    price_data = pd.DataFrame(
        np.random.randn(len(dates), len(stocks)) * 0.02 + 1,
        index=dates,
        columns=stocks
    ).cumprod() * 10

    # 生成随机因子数据
    factor_data = pd.DataFrame(
        np.random.randn(len(dates), len(stocks)),
        index=dates,
        columns=stocks
    )

    # 创建分析器
    analyzer = ICIRAnalyzer(price_data, factor_data)

    # 计算IC
    analyzer.calculate_ic(periods=1, method='pearson')

    # 打印报告
    analyzer.print_report()

    # 生成报告
    report = analyzer.generate_report()
    print("\n详细报告：")
    print(report)
