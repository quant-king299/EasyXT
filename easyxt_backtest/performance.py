# -*- coding: utf-8 -*-
"""
性能分析器 - 计算回测性能指标
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional


class PerformanceAnalyzer:
    """
    性能分析器

    计算各种回测性能指标：
    - 收益率指标（总收益、年化收益）
    - 风险指标（最大回撤、波动率）
    - 风险调整收益（夏普比率、卡尔玛比率）
    """

    def __init__(self, risk_free_rate: float = 0.03):
        """
        初始化性能分析器

        Args:
            risk_free_rate: 无风险利率（默认3%）
        """
        self.risk_free_rate = risk_free_rate

    def analyze(self,
                returns: pd.Series,
                initial_cash: float = 1000000) -> Dict[str, float]:
        """
        分析性能

        Args:
            returns: 每日收益率序列
            initial_cash: 初始资金

        Returns:
            性能指标字典
        """
        if returns.empty:
            return self._empty_metrics()

        # 收益率指标
        total_return = self._calculate_total_return(returns)
        annual_return = self._calculate_annual_return(returns, len(returns))

        # 风险指标
        max_drawdown = self._calculate_max_drawdown(returns)
        volatility = self._calculate_volatility(returns)

        # 风险调整收益
        sharpe_ratio = self._calculate_sharpe_ratio(returns, volatility)
        calmar_ratio = self._calculate_calmar_ratio(annual_return, max_drawdown)

        # 最终资产
        final_value = initial_cash * (1 + total_return)

        # 汇总
        metrics = {
            # 收益指标
            'total_return': total_return,
            'annual_return': annual_return,
            'initial_cash': initial_cash,
            'final_value': final_value,

            # 风险指标
            'max_drawdown': max_drawdown,
            'volatility': volatility,

            # 风险调整收益
            'sharpe_ratio': sharpe_ratio,
            'calmar_ratio': calmar_ratio,

            # 其他
            'total_days': len(returns),
            'positive_days': (returns > 0).sum(),
            'negative_days': (returns < 0).sum(),
        }

        return metrics

    def _empty_metrics(self) -> Dict[str, float]:
        """返回空指标"""
        return {
            'total_return': 0.0,
            'annual_return': 0.0,
            'max_drawdown': 0.0,
            'volatility': 0.0,
            'sharpe_ratio': 0.0,
            'calmar_ratio': 0.0,
            'initial_cash': 0.0,
            'final_value': 0.0,
            'total_days': 0,
            'positive_days': 0,
            'negative_days': 0,
        }

    # ==================== 收益率计算 ====================

    def _calculate_total_return(self, returns: pd.Series) -> float:
        """
        计算总收益率

        公式：(1 + r1) * (1 + r2) * ... * (1 + rn) - 1
        """
        if returns.empty:
            return 0.0

        return (1 + returns).prod() - 1

    def _calculate_annual_return(self,
                                  returns: pd.Series,
                                  n_days: int) -> float:
        """
        计算年化收益率

        公式：(1 + total_return) ^ (252 / n_days) - 1

        Args:
            returns: 收益率序列
            n_days: 交易日数量
        """
        if returns.empty or n_days == 0:
            return 0.0

        total_return = self._calculate_total_return(returns)

        # 假设一年有252个交易日
        trading_days_per_year = 252
        years = n_days / trading_days_per_year

        if years == 0:
            return 0.0

        return (1 + total_return) ** (1 / years) - 1

    # ==================== 风险指标计算 ====================

    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """
        计算最大回撤

        回撤 = (峰值 - 当前值) / 峰值

        最大回撤 = max(所有回撤)
        """
        if returns.empty:
            return 0.0

        # 计算累计净值
        cumulative = (1 + returns).cumprod()

        # 计算历史最高点
        running_max = cumulative.expanding().max()

        # 计算回撤
        drawdown = (cumulative - running_max) / running_max

        # 最大回撤（取最小值，因为回撤是负数）
        return drawdown.min()

    def _calculate_volatility(self,
                               returns: pd.Series,
                               annualize: bool = True) -> float:
        """
        计算波动率（标准差）

        Args:
            returns: 收益率序列
            annualize: 是否年化

        Returns:
            波动率
        """
        if returns.empty:
            return 0.0

        vol = returns.std()

        if annualize:
            # 年化：乘以sqrt(252)
            vol = vol * np.sqrt(252)

        return vol

    # ==================== 风险调整收益计算 ====================

    def _calculate_sharpe_ratio(self,
                                returns: pd.Series,
                                volatility: float) -> float:
        """
        计算夏普比率

        公式：(年化收益率 - 无风险利率) / 年化波动率

        Args:
            returns: 收益率序列
            volatility: 年化波动率

        Returns:
            夏普比率
        """
        if returns.empty or volatility == 0:
            return 0.0

        # 计算年化收益率
        annual_return = self._calculate_annual_return(returns, len(returns))

        # 夏普比率
        sharpe = (annual_return - self.risk_free_rate) / volatility

        return sharpe

    def _calculate_calmar_ratio(self,
                                 annual_return: float,
                                 max_drawdown: float) -> float:
        """
        计算卡尔玛比率

        公式：年化收益率 / |最大回撤|

        Args:
            annual_return: 年化收益率
            max_drawdown: 最大回撤（负数）

        Returns:
            卡尔玛比率
        """
        if max_drawdown == 0:
            return 0.0

        return annual_return / abs(max_drawdown)

    # ==================== 其他指标 ====================

    def calculate_win_rate(self, returns: pd.Series) -> float:
        """
        计算胜率

        公式：盈利天数 / 总天数

        Args:
            returns: 收益率序列

        Returns:
            胜率（0-1之间）
        """
        if returns.empty:
            return 0.0

        positive_days = (returns > 0).sum()
        total_days = len(returns)

        return positive_days / total_days if total_days > 0 else 0.0

    def calculate_profit_loss_ratio(self, returns: pd.Series) -> float:
        """
        计算盈亏比

        公式：平均盈利 / 平均亏损

        Args:
            returns: 收益率序列

        Returns:
            盈亏比
        """
        if returns.empty:
            return 0.0

        positive_returns = returns[returns > 0]
        negative_returns = returns[returns < 0]

        if positive_returns.empty or negative_returns.empty:
            return 0.0

        avg_profit = positive_returns.mean()
        avg_loss = abs(negative_returns.mean())

        return avg_profit / avg_loss if avg_loss != 0 else 0.0

    # ==================== 详细报告 ====================

    def generate_detailed_report(self,
                                  returns: pd.Series,
                                  initial_cash: float = 1000000) -> str:
        """
        生成详细的性能报告

        Args:
            returns: 收益率序列
            initial_cash: 初始资金

        Returns:
            报告字符串
        """
        metrics = self.analyze(returns, initial_cash)

        report = []
        report.append("="*70)
        report.append("回测性能报告")
        report.append("="*70)

        # 收益指标
        report.append("\n【收益指标】")
        report.append(f"总收益率:     {metrics['total_return']:>10.2%}")
        report.append(f"年化收益率:   {metrics['annual_return']:>10.2%}")
        report.append(f"初始资金:     {metrics['initial_cash']:>10,.2f} 元")
        report.append(f"最终资金:     {metrics['final_value']:>10,.2f} 元")

        # 风险指标
        report.append("\n【风险指标】")
        report.append(f"最大回撤:     {metrics['max_drawdown']:>10.2%}")
        report.append(f"波动率:       {metrics['volatility']:>10.2%}")

        # 风险调整收益
        report.append("\n【风险调整收益】")
        report.append(f"夏普比率:     {metrics['sharpe_ratio']:>10.2f}")
        report.append(f"卡尔玛比率:   {metrics['calmar_ratio']:>10.2f}")

        # 交易统计
        report.append("\n【交易统计】")
        report.append(f"总交易日:     {metrics['total_days']:>10} 天")
        report.append(f"盈利天数:     {metrics['positive_days']:>10} 天")
        report.append(f"亏损天数:     {metrics['negative_days']:>10} 天")

        # 胜率和盈亏比
        win_rate = self.calculate_win_rate(returns)
        profit_loss_ratio = self.calculate_profit_loss_ratio(returns)
        report.append(f"胜率:         {win_rate:>10.2%}")
        report.append(f"盈亏比:       {profit_loss_ratio:>10.2f}")

        report.append("\n" + "="*70)

        return "\n".join(report)
