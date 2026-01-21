"""
绩效分析模块
用于分析因子和策略的绩效指标
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import sys
import os

# 添加项目路径
project_path = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_path)


class PerformanceAnalyzer:
    """
    绩效分析类
    用于分析因子和策略的绩效指标
    """
    
    def __init__(self):
        self.metrics = {}
        self.performance_data = {}
    
    def calculate_factor_performance(self, factor_data: pd.Series, returns_data: pd.Series) -> Dict:
        """
        计算因子绩效指标
        
        Args:
            factor_data: 因子数据 (Series)
            returns_data: 收益率数据 (Series)
            
        Returns:
            Dict: 绩效指标
        """
        # 确保数据对齐
        aligned_factor, aligned_returns = factor_data.align(returns_data, join='inner')
        
        # 计算基本统计指标
        metrics = {
            'factor_mean': float(aligned_factor.mean()),
            'factor_std': float(aligned_factor.std()),
            'factor_min': float(aligned_factor.min()),
            'factor_max': float(aligned_factor.max()),
            'factor_skewness': float(aligned_factor.skew()),
            'factor_kurtosis': float(aligned_factor.kurtosis()),
            'returns_mean': float(aligned_returns.mean()),
            'returns_std': float(aligned_returns.std()),
            'returns_min': float(aligned_returns.min()),
            'returns_max': float(aligned_returns.max()),
            'correlation': float(aligned_factor.corr(aligned_returns)),
            'count': len(aligned_factor)
        }
        
        return metrics
    
    def calculate_strategy_performance(self, returns_series: pd.Series, benchmark_returns: pd.Series = None) -> Dict:
        """
        计算策略绩效指标
        
        Args:
            returns_series: 策略收益率序列
            benchmark_returns: 基准收益率序列（可选）
            
        Returns:
            Dict: 策略绩效指标
        """
        # 移除NaN值
        clean_returns = returns_series.dropna()
        if len(clean_returns) == 0:
            return self._get_default_performance_metrics()
        
        # 计算累计收益
        cumulative_returns = (1 + clean_returns).cumprod()
        total_return = cumulative_returns.iloc[-1] - 1 if len(cumulative_returns) > 0 else 0.0
        
        # 年化收益
        years = len(clean_returns) / 252.0  # 假设每年252个交易日
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0
        
        # 年化波动率
        annual_volatility = clean_returns.std() * np.sqrt(252)
        
        # 夏普比率
        risk_free_rate = 0.03  # 假设无风险利率3%
        sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility if annual_volatility != 0 else 0.0
        
        # 最大回撤
        rolling_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = float(drawdown.min()) if len(drawdown) > 0 else 0.0
        
        # 胜率
        win_rate = (clean_returns > 0).sum() / len(clean_returns) if len(clean_returns) > 0 else 0.0
        
        # Calmar比率
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0.0
        
        # 计算信息比率（如果有基准）
        if benchmark_returns is not None and len(benchmark_returns) > 0:
            excess_returns = clean_returns - benchmark_returns[:len(clean_returns)].values
            information_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() != 0 else 0.0
        else:
            information_ratio = 0.0
        
        # Beta和Alpha（如果有基准）
        if benchmark_returns is not None and len(benchmark_returns) > 0:
            benchmark_subset = benchmark_returns[:len(clean_returns)]
            # 计算Beta
            cov_matrix = np.cov(clean_returns, benchmark_subset)
            beta = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else 0.0
            # 计算Alpha
            alpha = annual_return - risk_free_rate - beta * (benchmark_subset.mean() * 252 - risk_free_rate)
        else:
            beta = 0.0
            alpha = 0.0
        
        metrics = {
            'total_return': total_return,
            'annual_return': annual_return,
            'annual_volatility': annual_volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'calmar_ratio': calmar_ratio,
            'win_rate': win_rate,
            'information_ratio': information_ratio,
            'beta': beta,
            'alpha': alpha,
            'var_95': float(clean_returns.quantile(0.05)) if len(clean_returns) > 0 else 0.0,  # VaR 95%
            'sortino_ratio': self._calculate_sortino_ratio(clean_returns, risk_free_rate / 252),  # 日化无风险利率
            'return_to_drawdown': abs(annual_return / max_drawdown) if max_drawdown != 0 else 0.0,
            'tracking_error': self._calculate_tracking_error(clean_returns, benchmark_subset) if benchmark_returns is not None else 0.0
        }
        
        return metrics
    
    def _calculate_sortino_ratio(self, returns: pd.Series, risk_free_rate: float = 0.0) -> float:
        """计算Sortino比率"""
        if len(returns) == 0:
            return 0.0
        
        # 只考虑下行风险（负收益）
        negative_returns = returns[returns < risk_free_rate]
        if len(negative_returns) == 0:
            return np.inf if returns.mean() > risk_free_rate else 0.0
        
        downside_deviation = np.sqrt((negative_returns ** 2).mean())
        excess_return = returns.mean() - risk_free_rate
        sortino_ratio = excess_return / downside_deviation * np.sqrt(252) if downside_deviation != 0 else 0.0
        
        return sortino_ratio
    
    def _calculate_tracking_error(self, strategy_returns: pd.Series, benchmark_returns: pd.Series) -> float:
        """计算跟踪误差"""
        if len(strategy_returns) == 0 or len(benchmark_returns) == 0:
            return 0.0
        
        excess_returns = strategy_returns - benchmark_returns[:len(strategy_returns)].values
        tracking_error = excess_returns.std() * np.sqrt(252)
        return tracking_error
    
    def _get_default_performance_metrics(self) -> Dict:
        """返回默认绩效指标"""
        return {
            'total_return': 0.0,
            'annual_return': 0.0,
            'annual_volatility': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'calmar_ratio': 0.0,
            'win_rate': 0.0,
            'information_ratio': 0.0,
            'beta': 0.0,
            'alpha': 0.0,
            'var_95': 0.0,
            'sortino_ratio': 0.0,
            'return_to_drawdown': 0.0,
            'tracking_error': 0.0
        }

    def generate_factor_report(self, factor_data: pd.Series, returns_data: pd.Series, factor_name: str = "Factor") -> Dict:
        """
        生成因子分析报告
        
        Args:
            factor_data: 因子数据
            returns_data: 收益率数据
            factor_name: 因子名称
            
        Returns:
            Dict: 分析报告
        """
        # 计算因子绩效
        factor_perf = self.calculate_factor_performance(factor_data, returns_data)
        
        # 从IC分析模块获取IC指标（如果可用）
        try:
            from src.analysis.ic_analysis import ICAnalysis
            ic_analyzer = ICAnalysis()
            ic_series = ic_analyzer.calculate_ic(factor_data, returns_data)
            ic_stats = ic_analyzer.calculate_ic_stats(ic_series)
        except:
            ic_stats = {
                'ic_mean': 0.0,
                'ic_std': 0.0,
                'ic_ir': 0.0,
                'ic_prob': 0.0,
                'ic_abs_mean': 0.0,
                't_stat': 0.0,
                'p_value': 1.0
            }
        
        report = {
            'factor_name': factor_name,
            'factor_stats': factor_perf,
            'ic_stats': ic_stats,
            'summary': {
                'ic_mean': ic_stats['ic_mean'],
                'ic_ir': ic_stats['ic_ir'],
                'turnover_rate': self._estimate_turnover_rate(factor_data),
                'monotonicity': self._assess_monotonicity(factor_data, returns_data)
            }
        }
        
        return report
    
    def _estimate_turnover_rate(self, factor_data: pd.Series) -> float:
        """估算因子换手率"""
        # 计算因子值的变化率作为换手率的代理
        try:
            # 按日期聚合因子值，然后计算变化率
            dates = sorted(factor_data.index.get_level_values(0).unique())
            if len(dates) < 2:
                return 0.0
            
            factor_changes = []
            for i in range(1, len(dates)):
                current_date = dates[i]
                prev_date = dates[i-1]
                
                current_factors = factor_data[factor_data.index.get_level_values(0) == current_date]
                prev_factors = factor_data[factor_data.index.get_level_values(0) == prev_date]
                
                # 对齐数据
                aligned_current, aligned_prev = current_factors.align(prev_factors, join='inner')
                if len(aligned_current) > 0:
                    change = ((aligned_current - aligned_prev) / aligned_prev).abs().mean()
                    factor_changes.append(change)
            
            turnover_rate = np.mean(factor_changes) if factor_changes else 0.0
            return float(turnover_rate)
        except:
            return 0.0
    
    def _assess_monotonicity(self, factor_data: pd.Series, returns_data: pd.Series) -> float:
        """评估因子单调性"""
        try:
            # 将因子按日期分组，按因子值分层，计算每层的平均收益率
            dates = sorted(factor_data.index.get_level_values(0).unique())
            monotonicity_measures = []
            
            for date in dates:
                date_mask = factor_data.index.get_level_values(0) == date
                current_factors = factor_data[date_mask]
                current_returns = returns_data[date_mask]
                
                if len(current_factors) < 10:  # 需要足够多的股票
                    continue
                
                # 将因子值分为5层
                try:
                    quintiles = pd.qcut(current_factors, q=5, labels=False, duplicates='drop')
                    if len(set(quintiles)) < 5:
                        continue
                except:
                    continue
                
                # 计算每层的平均收益率
                layer_returns = []
                for q in range(5):
                    q_mask = quintiles == q
                    layer_return = current_returns[q_mask].mean()
                    layer_returns.append(layer_return)
                
                if len(layer_returns) == 5:
                    # 检查是否单调（理论上应该是单调递增或递减，取决于因子定义）
                    # 这里简单计算相邻层收益率的相关性
                    layers = list(range(5))
                    mono_corr = np.corrcoef(layers, layer_returns)[0, 1]
                    if not np.isnan(mono_corr):
                        monotonicity_measures.append(abs(mono_corr))
            
            monotonicity = np.mean(monotonicity_measures) if monotonicity_measures else 0.0
            return float(monotonicity)
        except:
            return 0.0


# 测试代码
if __name__ == '__main__':
    import pandas as pd
    import numpy as np
    
    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=60, freq='D')
    symbols = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '000858.SZ']
    
    # 创建多级索引
    index = pd.MultiIndex.from_product([dates, symbols], names=['date', 'symbol'])
    
    # 生成测试数据
    np.random.seed(42)
    factor_data = pd.Series(np.random.randn(len(index)), index=index, name='factor')
    returns_data = pd.Series(np.random.randn(len(index)) * 0.02, index=index, name='returns')
    
    print(f"测试数据形状: 因子-{factor_data.shape}, 收益率-{returns_data.shape}")
    
    # 创建绩效分析器
    perf_analyzer = PerformanceAnalyzer()
    
    # 分析因子绩效
    factor_report = perf_analyzer.generate_factor_report(
        factor_data=factor_data,
        returns_data=returns_data,
        factor_name="Test_Factor"
    )
    
    print(f"\n因子分析报告: {factor_report['factor_name']}")
    print(f"IC均值: {factor_report['ic_stats']['ic_mean']:.4f}")
    print(f"IC_IR: {factor_report['ic_stats']['ic_ir']:.4f}")
    print(f"换手率估计: {factor_report['summary']['turnover_rate']:.4f}")
    print(f"单调性: {factor_report['summary']['monotonicity']:.4f}")
    
    # 测试策略绩效分析
    strategy_returns = pd.Series(np.random.randn(100) * 0.01)  # 模拟策略收益率
    benchmark_returns = pd.Series(np.random.randn(100) * 0.008)  # 模拟基准收益率
    
    strategy_perf = perf_analyzer.calculate_strategy_performance(strategy_returns, benchmark_returns)
    print(f"\n策略绩效指标:")
    print(f"年化收益: {strategy_perf['annual_return']:.2%}")
    print(f"夏普比率: {strategy_perf['sharpe_ratio']:.4f}")
    print(f"最大回撤: {strategy_perf['max_drawdown']:.2%}")
    print(f"胜率: {strategy_perf['win_rate']:.2%}")
    print(f"信息比率: {strategy_perf['information_ratio']:.4f}")
    
    print("\n绩效分析测试完成!")