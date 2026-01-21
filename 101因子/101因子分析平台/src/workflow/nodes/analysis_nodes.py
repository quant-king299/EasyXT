"""
分析节点
实现IC分析、回测、绩效评估等分析功能节点
"""
from .base import AnalysisNode
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import sys
import os

# 添加项目路径
project_path = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_path)

from src.analysis.ic_analysis import ICAnalysis
from src.analysis.backtest import BacktestEngine
from src.analysis.performance import PerformanceAnalyzer
from src.analysis.factor_correlation import FactorCorrelationAnalyzer


class ICAnalysisNode(AnalysisNode):
    """IC分析节点"""
    
    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)
    
    def _execute_analysis(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行IC分析"""
        # 获取因子数据和收益率数据
        factor_data = None
        returns_data = None
        
        for key, value in input_data.items():
            if isinstance(value, pd.Series):
                if 'factor' in key.lower() or 'alpha' in key.lower():
                    factor_data = value
                elif 'return' in key.lower():
                    returns_data = value
        
        if factor_data is None and 'factor_data' in input_data:
            factor_data = input_data['factor_data']
        if returns_data is None and 'returns_data' in input_data:
            returns_data = input_data['returns_data']
        
        if factor_data is None or returns_data is None:
            raise ValueError("IC分析需要因子数据和收益率数据")
        
        # 获取参数
        periods = self.params.get('periods', 1)
        
        # 执行IC分析
        analyzer = ICAnalysis()
        ic_series = analyzer.calculate_ic(factor_data, returns_data, periods=periods)
        ic_stats = analyzer.calculate_ic_stats(ic_series)
        
        # 计算额外的IC相关指标
        additional_ic_metrics = self._calculate_additional_ic_metrics(ic_series)
        
        self.outputs = {
            'ic_series': ic_series,
            'ic_stats': ic_stats,
            'additional_metrics': additional_ic_metrics,
            'factor_data': factor_data,
            'returns_data': returns_data,
            'analysis_summary': {
                'ic_mean': ic_stats['ic_mean'],
                'ic_ir': ic_stats['ic_ir'],
                'ic_prob': ic_stats['ic_prob'],
                'ic_abs_mean': ic_stats['ic_abs_mean']
            }
        }
        
        return self.outputs
    
    def _calculate_additional_ic_metrics(self, ic_series: pd.Series) -> Dict[str, float]:
        """计算额外的IC指标"""
        if len(ic_series) == 0:
            return {}
        
        # IC衰减
        ic_lag_correlations = []
        for lag in range(1, min(6, len(ic_series))):
            corr = ic_series.corr(ic_series.shift(lag))
            if not pd.isna(corr):
                ic_lag_correlations.append(corr)
        
        # IC分位数统计
        ic_q10 = ic_series.quantile(0.1) if len(ic_series) > 0 else 0.0
        ic_q90 = ic_series.quantile(0.9) if len(ic_series) > 0 else 0.0
        
        return {
            'ic_decay_rates': ic_lag_correlations,
            'ic_q10': float(ic_q10),
            'ic_q90': float(ic_q90),
            'ic_positive_ratio': float((ic_series > 0).sum() / len(ic_series)) if len(ic_series) > 0 else 0.0,
            'ic_negative_ratio': float((ic_series < 0).sum() / len(ic_series)) if len(ic_series) > 0 else 0.0
        }


class BacktestNode(AnalysisNode):
    """回测节点"""
    
    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)
    
    def _execute_analysis(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行回测"""
        # 获取因子数据和价格数据
        factor_data = None
        price_data = None
        
        for key, value in input_data.items():
            if isinstance(value, pd.Series) and 'factor' in key.lower():
                factor_data = value
            elif isinstance(value, pd.DataFrame) and any(col in value.columns for col in ['open', 'close', 'high', 'low']):
                price_data = value
        
        if factor_data is None and 'factor_data' in input_data:
            factor_data = input_data['factor_data']
        if price_data is None and 'price_data' in input_data:
            price_data = input_data['price_data']
        
        if factor_data is None or price_data is None:
            raise ValueError("回测需要因子数据和价格数据")
        
        # 获取参数
        top_quantile = self.params.get('top_quantile', 0.2)
        bottom_quantile = self.params.get('bottom_quantile', 0.2)
        transaction_cost = self.params.get('transaction_cost', 0.001)
        n_quantiles = self.params.get('n_quantiles', 5)
        
        # 执行回测
        backtester = BacktestEngine()
        
        # 多空组合回测
        ls_results = backtester.backtest_long_short_portfolio(
            factor_data=factor_data,
            price_data=price_data,
            top_quantile=top_quantile,
            bottom_quantile=bottom_quantile,
            transaction_cost=transaction_cost
        )
        
        # 分层回测
        quantile_results = backtester.backtest_quantile_portfolio(
            factor_data=factor_data,
            price_data=price_data,
            n_quantiles=n_quantiles
        )
        
        self.outputs = {
            'long_short_results': ls_results,
            'quantile_results': quantile_results,
            'factor_data': factor_data,
            'price_data': price_data,
            'backtest_summary': {
                'long_short': self._extract_ls_summary(ls_results),
                'quantile': self._extract_quantile_summary(quantile_results)
            }
        }
        
        return self.outputs
    
    def _extract_ls_summary(self, ls_results: Dict) -> Dict[str, Any]:
        """提取多空回测摘要"""
        if 'error' in ls_results:
            return {'error': ls_results['error']}
        
        return {
            'total_return': ls_results.get('total_return', 0),
            'annual_return': ls_results.get('annual_return', 0),
            'sharpe_ratio': ls_results.get('sharpe_ratio', 0),
            'max_drawdown': ls_results.get('max_drawdown', 0),
            'win_rate': ls_results.get('win_rate', 0),
            'long_short_spread': ls_results.get('long_short_spread', 0)
        }
    
    def _extract_quantile_summary(self, quantile_results: Dict) -> Dict[str, Any]:
        """提取分层回测摘要"""
        summary = {}
        for q_name, q_result in quantile_results.items():
            summary[q_name] = {
                'total_return': q_result.get('total_return', 0),
                'annual_return': q_result.get('annual_return', 0),
                'sharpe_ratio': q_result.get('sharpe_ratio', 0),
                'max_drawdown': q_result.get('max_drawdown', 0)
            }
        return summary


class PerformanceAnalysisNode(AnalysisNode):
    """绩效分析节点"""
    
    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)
    
    def _execute_analysis(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行绩效分析"""
        # 获取收益率数据
        returns_data = None
        benchmark_data = None
        
        for key, value in input_data.items():
            if isinstance(value, pd.Series):
                if 'return' in key.lower() or 'returns' in key.lower():
                    if 'benchmark' in key.lower():
                        benchmark_data = value
                    else:
                        returns_data = value
            elif isinstance(value, pd.DataFrame) and 'return' in str(value.columns).lower():
                returns_data = value.squeeze() if len(value.columns) == 1 else value
        
        if returns_data is None and 'returns_data' in input_data:
            returns_data = input_data['returns_data']
        if benchmark_data is None and 'benchmark_data' in input_data:
            benchmark_data = input_data.get('benchmark_data')
        
        if returns_data is None:
            raise ValueError("绩效分析需要收益率数据")
        
        # 执行绩效分析
        analyzer = PerformanceAnalyzer()
        perf_metrics = analyzer.calculate_strategy_performance(returns_data, benchmark_data)
        
        # 计算额外的绩效指标
        additional_metrics = self._calculate_additional_metrics(returns_data, benchmark_data)
        
        self.outputs = {
            'performance_metrics': perf_metrics,
            'additional_metrics': additional_metrics,
            'returns_data': returns_data,
            'benchmark_data': benchmark_data,
            'performance_summary': {
                'annual_return': perf_metrics['annual_return'],
                'sharpe_ratio': perf_metrics['sharpe_ratio'],
                'max_drawdown': perf_metrics['max_drawdown'],
                'win_rate': perf_metrics['win_rate'],
                'information_ratio': perf_metrics['information_ratio'],
                'alpha': perf_metrics['alpha'],
                'beta': perf_metrics['beta']
            }
        }
        
        return self.outputs
    
    def _calculate_additional_metrics(self, returns_data: pd.Series, benchmark_data: pd.Series = None) -> Dict[str, float]:
        """计算额外的绩效指标"""
        additional_metrics = {}
        
        # 计算月度和季度绩效
        if len(returns_data) > 0:
            # 月度绩效
            try:
                monthly_returns = returns_data.resample('M').apply(lambda x: (1+x).prod() - 1)
                additional_metrics['avg_monthly_return'] = float(monthly_returns.mean())
                additional_metrics['monthly_volatility'] = float(monthly_returns.std())
            except:
                additional_metrics['avg_monthly_return'] = 0.0
                additional_metrics['monthly_volatility'] = 0.0
            
            # 年度绩效
            try:
                yearly_returns = returns_data.resample('Y').apply(lambda x: (1+x).prod() - 1)
                additional_metrics['avg_yearly_return'] = float(yearly_returns.mean())
                additional_metrics['yearly_volatility'] = float(yearly_returns.std())
            except:
                additional_metrics['avg_yearly_return'] = 0.0
                additional_metrics['yearly_volatility'] = 0.0
        
        # 计算最大连续盈利/亏损期
        if len(returns_data) > 0:
            positive_streak = 0
            negative_streak = 0
            max_positive_streak = 0
            max_negative_streak = 0
            
            for ret in returns_data:
                if ret > 0:
                    positive_streak += 1
                    negative_streak = 0
                elif ret < 0:
                    negative_streak += 1
                    positive_streak = 0
                else:
                    positive_streak = 0
                    negative_streak = 0
                
                max_positive_streak = max(max_positive_streak, positive_streak)
                max_negative_streak = max(max_negative_streak, negative_streak)
            
            additional_metrics['max_positive_streak'] = max_positive_streak
            additional_metrics['max_negative_streak'] = max_negative_streak
        
        return additional_metrics


class RiskAnalysisNode(AnalysisNode):
    """风险分析节点"""
    
    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)
    
    def _execute_analysis(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行风险分析"""
        # 获取收益率数据
        returns_data = None
        factor_data = None
        
        for key, value in input_data.items():
            if isinstance(value, pd.Series):
                if 'return' in key.lower():
                    returns_data = value
                elif 'factor' in key.lower():
                    factor_data = value
        
        if returns_data is None and 'returns_data' in input_data:
            returns_data = input_data['returns_data']
        if factor_data is None and 'factor_data' in input_data:
            factor_data = input_data['factor_data']
        
        if returns_data is None:
            raise ValueError("风险分析需要收益率数据")
        
        # 计算风险指标
        risk_metrics = self._calculate_risk_metrics(returns_data)
        
        # 如果有因子数据，计算因子风险
        factor_risk = {}
        if factor_data is not None:
            factor_risk = self._calculate_factor_risk(returns_data, factor_data)
        
        self.outputs = {
            'risk_metrics': risk_metrics,
            'factor_risk': factor_risk,
            'returns_data': returns_data,
            'factor_data': factor_data,
            'risk_summary': {
                'volatility': risk_metrics.get('volatility', 0),
                'max_drawdown': risk_metrics.get('max_drawdown', 0),
                'var_95': risk_metrics.get('var_95', 0),
                'cvar_95': risk_metrics.get('cvar_95', 0)
            }
        }
        
        return self.outputs
    
    def _calculate_risk_metrics(self, returns_data: pd.Series) -> Dict[str, float]:
        """计算风险指标"""
        if len(returns_data) == 0:
            return {}
        
        # 基础风险指标
        volatility = float(returns_data.std() * np.sqrt(252))  # 年化波动率
        daily_var = returns_data.quantile(0.05)  # VaR 5%
        cvar = returns_data[returns_data <= returns_data.quantile(0.05)].mean()  # CVaR
        
        # 最大回撤
        cumulative = (1 + returns_data).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = float(drawdown.min())
        
        # 下行风险
        downside_returns = returns_data[returns_data < 0]
        downside_deviation = float(np.sqrt((downside_returns ** 2).mean()) * np.sqrt(252)) if len(downside_returns) > 0 else 0.0
        
        # 贝塔和夏普比率（如果可能）
        risk_metrics = {
            'volatility': volatility,
            'max_drawdown': max_drawdown,
            'var_95': float(daily_var),
            'cvar_95': float(cvar),
            'downside_deviation': downside_deviation,
            'skewness': float(returns_data.skew()),
            'kurtosis': float(returns_data.kurtosis()),
            'gain_loss_ratio': self._calculate_gain_loss_ratio(returns_data)
        }
        
        return risk_metrics
    
    def _calculate_gain_loss_ratio(self, returns_data: pd.Series) -> float:
        """计算盈利损失比"""
        gains = returns_data[returns_data > 0]
        losses = returns_data[returns_data < 0]
        
        if len(losses) == 0:
            return float('inf') if len(gains) > 0 else 0.0
        
        avg_gain = gains.mean() if len(gains) > 0 else 0.0
        avg_loss = abs(losses.mean()) if len(losses) > 0 else 1.0  # 避免除零
        
        return avg_gain / avg_loss
    
    def _calculate_factor_risk(self, returns_data: pd.Series, factor_data: pd.Series) -> Dict[str, float]:
        """计算因子风险"""
        try:
            # 对齐数据
            aligned_returns, aligned_factors = returns_data.align(factor_data, join='inner')
            
            if len(aligned_returns) < 2 or len(aligned_factors) < 2:
                return {}
            
            # 计算因子暴露度
            factor_beta = np.cov(aligned_returns, aligned_factors)[0, 1] / np.var(aligned_factors) if np.var(aligned_factors) != 0 else 0.0
            
            # 计算残差风险
            predicted_returns = factor_beta * aligned_factors
            residuals = aligned_returns - predicted_returns
            residual_risk = float(residuals.std())
            
            # R平方
            ss_res = np.sum((aligned_returns - predicted_returns) ** 2)
            ss_tot = np.sum((aligned_returns - aligned_returns.mean()) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
            
            return {
                'factor_beta': float(factor_beta),
                'residual_risk': residual_risk,
                'r_squared': float(r_squared),
                'factor_exposure': float(aligned_factors.mean())
            }
        except:
            return {}


class SignalAnalysisNode(AnalysisNode):
    """信号分析节点"""
    
    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)
    
    def _execute_analysis(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行信号分析"""
        # 获取信号数据
        signal_data = None
        price_data = None
        returns_data = None
        
        for key, value in input_data.items():
            if isinstance(value, pd.Series):
                if 'signal' in key.lower():
                    signal_data = value
                elif 'return' in key.lower():
                    returns_data = value
            elif isinstance(value, pd.DataFrame):
                if any(col in value.columns for col in ['open', 'close', 'high', 'low']):
                    price_data = value
        
        if signal_data is None and 'signal_data' in input_data:
            signal_data = input_data['signal_data']
        if price_data is None and 'price_data' in input_data:
            price_data = input_data.get('price_data')
        if returns_data is None and 'returns_data' in input_data:
            returns_data = input_data.get('returns_data')
        
        if signal_data is None:
            raise ValueError("信号分析需要信号数据")
        
        # 计算信号分析指标
        signal_metrics = self._calculate_signal_metrics(signal_data)
        
        # 计算信号与收益率的关系（如果提供）
        predictive_power = {}
        if returns_data is not None:
            predictive_power = self._calculate_predictive_power(signal_data, returns_data)
        
        self.outputs = {
            'signal_metrics': signal_metrics,
            'predictive_power': predictive_power,
            'signal_data': signal_data,
            'price_data': price_data,
            'returns_data': returns_data,
            'signal_summary': {
                'signal_coverage': signal_metrics.get('coverage', 0),
                'signal_concentration': signal_metrics.get('concentration', 0),
                'signal_stability': signal_metrics.get('stability', 0)
            }
        }
        
        return self.outputs
    
    def _calculate_signal_metrics(self, signal_data: pd.Series) -> Dict[str, float]:
        """计算信号指标"""
        if len(signal_data) == 0:
            return {}
        
        # 信号覆盖率（非零信号的比例）
        coverage = float((signal_data != 0).sum() / len(signal_data))
        
        # 信号集中度（信号的标准差）
        concentration = float(signal_data.std())
        
        # 信号分布
        long_signals = (signal_data > 0).sum()
        short_signals = (signal_data < 0).sum()
        neutral_signals = (signal_data == 0).sum()
        
        # 信号稳定度（变化频率的倒数）
        signal_changes = (signal_data != signal_data.shift(1)).sum()
        stability = 1.0 / (signal_changes / len(signal_data)) if signal_changes > 0 else float('inf')
        
        return {
            'mean': float(signal_data.mean()),
            'std': float(signal_data.std()),
            'coverage': coverage,
            'concentration': concentration,
            'long_ratio': float(long_signals / len(signal_data)) if len(signal_data) > 0 else 0.0,
            'short_ratio': float(short_signals / len(signal_data)) if len(signal_data) > 0 else 0.0,
            'neutral_ratio': float(neutral_signals / len(signal_data)) if len(signal_data) > 0 else 0.0,
            'stability': float(stability if stability != float('inf') else 1.0)
        }
    
    def _calculate_predictive_power(self, signal_data: pd.Series, returns_data: pd.Series) -> Dict[str, float]:
        """计算信号预测能力"""
        try:
            # 对齐数据
            aligned_signals, aligned_returns = signal_data.align(returns_data, join='inner')
            
            if len(aligned_signals) < 2 or len(aligned_returns) < 2:
                return {}
            
            # 计算信号与未来收益率的相关性
            correlation = float(aligned_signals.corr(aligned_returns))
            
            # 按信号分组的平均收益
            signal_groups = pd.cut(aligned_signals, bins=5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
            group_returns = pd.DataFrame({
                'signal_group': signal_groups,
                'returns': aligned_returns
            }).groupby('signal_group')['returns'].mean()
            
            return {
                'correlation': correlation,
                'group_returns': group_returns.to_dict() if not group_returns.empty else {},
                'predictive_power': abs(correlation) if not pd.isna(correlation) else 0.0
            }
        except:
            return {}


class FactorCorrelationNode(AnalysisNode):
    """因子相关性分析节点"""

    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)

    def _execute_analysis(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行因子相关性分析"""
        # 收集所有因子数据
        factor_dict = {}

        for key, value in input_data.items():
            # 收集因子数据（Series或DataFrame格式）
            if isinstance(value, (pd.Series, pd.DataFrame)):
                if 'factor' in key.lower() or 'alpha' in key.lower():
                    factor_dict[key] = value

        # 如果没有从input_data中找到因子，尝试从params中获取
        if not factor_dict and 'factor_dict' in input_data:
            factor_dict = input_data['factor_dict']

        if not factor_dict:
            raise ValueError("因子相关性分析需要至少两个因子数据")

        # 获取参数
        threshold = self.params.get('threshold', 0.7)
        method = self.params.get('method', 'spearman')
        n_clusters = self.params.get('n_clusters', None)

        # 执行相关性分析
        analyzer = FactorCorrelationAnalyzer(factor_dict)

        # 计算相关系数矩阵
        corr_matrix = analyzer.calculate_correlation(method=method)

        # 找出高相关性因子对
        high_corr_pairs = analyzer.find_high_correlation_pairs(threshold=threshold, method=method)

        # 层次聚类分析
        if n_clusters:
            cluster_result = analyzer.hierarchical_clustering(n_clusters=n_clusters)
        else:
            cluster_result = analyzer.hierarchical_clustering()

        # 生成去重建议
        removal_suggestions = analyzer.generate_removal_suggestions(threshold=threshold, method=method)

        # 生成详细报告
        report = analyzer.generate_report()

        self.outputs = {
            'correlation_matrix': corr_matrix,
            'high_correlation_pairs': high_corr_pairs,
            'cluster_result': cluster_result,
            'removal_suggestions': removal_suggestions,
            'correlation_report': report,
            'factor_names': list(factor_dict.keys()),
            'n_factors': len(factor_dict),
            'correlation_summary': {
                'n_factors': len(factor_dict),
                'n_high_corr_pairs': len(high_corr_pairs),
                'max_correlation': float(corr_matrix.abs().max().max()) if len(corr_matrix) > 0 else 0.0,
                'avg_correlation': float(corr_matrix.abs().values[np.triu_indices_from(corr_matrix.values, k=1)].mean()) if len(corr_matrix) > 0 else 0.0,
                'threshold': threshold
            }
        }

        return self.outputs
