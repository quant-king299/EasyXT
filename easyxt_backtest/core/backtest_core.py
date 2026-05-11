# -*- coding: utf-8 -*-
"""
统一的 Backtrader 底层引擎

这是所有回测策略的核心，提供：
- 统一的 Cerebro 管理
- 统一的数据加载
- 统一的性能分析
- 统一的结果提取
"""

import backtrader as bt
import backtrader.analyzers as btanalyzers
import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime


class BacktestCore:
    """
    统一的 Backtrader 底层引擎

    所有回测策略（技术指标、选股、网格等）都基于这个核心
    """

    def __init__(self,
                 initial_cash: float = 100000.0,
                 commission: float = 0.001):
        """
        初始化回测核心

        Args:
            initial_cash: 初始资金
            commission: 佣金率
        """
        self.initial_cash = initial_cash
        self.commission = commission

        # 创建 Cerebro 引擎
        self.cerebro = bt.Cerebro()

        # 设置初始资金和佣金
        self.cerebro.broker.setcash(initial_cash)
        self.cerebro.broker.setcommission(commission=commission)

        # 设置默认每手股数（中国股市为100股/手）
        self.cerebro.addsizer(bt.sizers.FixedSize, stake=100)

        # 添加分析器
        self._add_analyzers()

        # 数据源列表
        self.data_feeds = []

        # 运行结果
        self.results = None

    def _add_analyzers(self):
        """添加性能分析器"""
        self.cerebro.addanalyzer(btanalyzers.SharpeRatio, _name='sharpe', riskfreerate=0.03)
        self.cerebro.addanalyzer(btanalyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(btanalyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name='trades')
        self.cerebro.addanalyzer(btanalyzers.TimeReturn, _name='timereturn')

    def add_data(self, data, name: Optional[str] = None):
        """
        添加数据源

        Args:
            data: 数据源（PandasData 或其他格式）
            name: 数据源名称
        """
        if name is not None:
            data._name = name

        self.cerebro.adddata(data)
        self.data_feeds.append(data)

        return self

    def add_strategy(self, strategy_class, **kwargs):
        """
        添加策略

        Args:
            strategy_class: 策略类
            **kwargs: 策略参数
        """
        self.cerebro.addstrategy(strategy_class, **kwargs)
        return self

    def run(self):
        """运行回测"""
        self.results = self.cerebro.run()
        return self.results

    def get_broker_value(self):
        """获取当前账户价值"""
        return self.cerebro.broker.getvalue()

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        获取性能指标

        Returns:
            性能指标字典
        """
        if not self.results or len(self.results) == 0:
            return self._get_empty_metrics()

        strat = self.results[0]
        metrics = {}

        # 提取各项指标
        try:
            # 夏普比率
            sharpe_analysis = strat.analyzers.sharpe.get_analysis()
            metrics['sharpe_ratio'] = sharpe_analysis.get('sharperatio', 0)

            # 最大回撤
            drawdown_analysis = strat.analyzers.drawdown.get_analysis()
            raw_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0)
            metrics['max_drawdown'] = raw_drawdown / 100.0 if raw_drawdown != 0 else 0

            # 总收益率
            returns_analysis = strat.analyzers.returns.get_analysis()
            total_return = returns_analysis.get('rtot', 0)
            metrics['total_return'] = total_return

            # 年化收益率
            annual_return = returns_analysis.get('ravg', 0)
            metrics['annual_return'] = annual_return * 252  # 假设252个交易日

            # 初始资金和最终资金
            metrics['initial_cash'] = self.initial_cash
            metrics['final_value'] = self.get_broker_value()

        except Exception as e:
            print(f"[WARNING] 提取性能指标时出错: {e}")
            return self._get_empty_metrics()

        return metrics

    def _get_empty_metrics(self) -> Dict[str, Any]:
        """返回空指标（用于测试）"""
        return {
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'total_return': 0,
            'annual_return': 0,
            'initial_cash': self.initial_cash,
            'final_value': self.initial_cash,
        }

    def get_full_results(self) -> Dict[str, Any]:
        """
        获取完整的回测结果（含交易记录和净值曲线）

        Returns:
            包含 metrics, trades, portfolio_curve, risk_analysis 的字典
        """
        metrics = self.get_performance_metrics()

        trades = []
        portfolio_curve = {'dates': [], 'values': []}
        risk_analysis = {}

        if not self.results or len(self.results) == 0:
            return {
                'metrics': metrics,
                'trades': trades,
                'portfolio_curve': portfolio_curve,
                'risk_analysis': risk_analysis,
            }

        strat = self.results[0]

        # 提取交易记录
        try:
            trade_analysis = strat.analyzers.trades.get_analysis()
            total = trade_analysis.get('total', {})
            won = trade_analysis.get('won', {})
            lost = trade_analysis.get('lost', {})
            trades = [
                ('总交易次数', total.get('total', 0), ''),
                ('盈利次数', won.get('total', 0), ''),
                ('亏损次数', lost.get('total', 0), ''),
                ('胜率', f"{won.get('total', 0) / max(total.get('total', 1), 1) * 100:.1f}%", ''),
            ]
        except Exception as e:
            print(f"[WARNING] 提取交易记录时出错: {e}")

        # 构建净值曲线
        try:
            timereturn_analysis = strat.analyzers.timereturn.get_analysis()
            if timereturn_analysis:
                cumulative_value = self.initial_cash
                dates = []
                values = []
                for date_key, ret in timereturn_analysis.items():
                    cumulative_value *= (1 + ret)
                    dates.append(str(date_key))
                    values.append(round(cumulative_value, 2))
                portfolio_curve = {'dates': dates, 'values': values}
        except Exception as e:
            print(f"[WARNING] 构建净值曲线时出错: {e}")

        # 计算风险指标
        try:
            risk_analysis = {
                'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                'max_drawdown': metrics.get('max_drawdown', 0),
                'total_return': metrics.get('total_return', 0),
                'annual_return': metrics.get('annual_return', 0),
                'volatility': metrics.get('volatility', 0),
                'calmar_ratio': metrics.get('calmar_ratio', 0),
                'initial_cash': metrics.get('initial_cash', self.initial_cash),
                'final_value': metrics.get('final_value', self.initial_cash),
            }
        except Exception as e:
            print(f"[WARNING] 计算风险指标时出错: {e}")

        return {
            'metrics': metrics,
            'trades': trades,
            'portfolio_curve': portfolio_curve,
            'risk_analysis': risk_analysis,
        }

