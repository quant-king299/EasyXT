"""
IC分析模块
用于分析因子与未来收益率的相关性
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import sys
import os

# 添加项目路径
project_path = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_path)


class ICAnalysis:
    """
    IC (Information Coefficient) 分析类
    用于分析因子与未来收益率的相关性
    """
    
    def __init__(self):
        self.ic_data = {}
        self.ic_stats = {}
    
    def calculate_ic(self, factor_data: pd.Series, 
                     returns_data: pd.Series, 
                     periods: int = 1) -> pd.Series:
        """
        计算IC (Information Coefficient)
        
        Args:
            factor_data: 因子数据，索引为[date, symbol]
            returns_data: 收益率数据，索引为[date, symbol]
            periods: 收益率期数（默认1期后）
            
        Returns:
            pd.Series: IC序列
        """
        # 确保数据按日期对齐
        aligned_factor, aligned_returns = factor_data.align(returns_data, join='inner')
        
        # 按日期分组计算IC
        ic_values = []
        ic_dates = []
        
        # 按日期分组
        factor_by_date = aligned_factor.groupby(level=0)
        returns_by_date = aligned_returns.groupby(level=0)
        
        # 获取所有日期
        factor_date_keys = list(factor_by_date.groups.keys())
        return_date_keys = list(returns_by_date.groups.keys())
        
        # 获取共同的日期
        common_date_keys = set(factor_date_keys) & set(return_date_keys)
        
        # 转换为可比较的类型并排序
        sorted_common_dates = sorted(common_date_keys, key=lambda x: str(x))
        
        for date in sorted_common_dates:
            try:
                # 获取当天的因子值和收益率
                daily_factors = factor_by_date.get_group(date)
                daily_returns = returns_by_date.get_group(date)
                
                # 确保它们有相同的股票
                factor_symbols = set(daily_factors.index.get_level_values(1))
                return_symbols = set(daily_returns.index.get_level_values(1))
                common_symbols = factor_symbols.intersection(return_symbols)
                
                if len(common_symbols) < 2:  # 需要至少2个数据点来计算相关性
                    continue
                
                # 创建对应的数据对
                factor_vals = []
                return_vals = []
                
                for symbol in common_symbols:
                    factor_key = (date, symbol)
                    return_key = (date, symbol)
                    
                    if factor_key in daily_factors.index and return_key in daily_returns.index:
                        factor_val = daily_factors.loc[factor_key]
                        return_val = daily_returns.loc[return_key]
                        
                        # 检查是否为有效数值 - 修复Series判断问题
                        try:
                            factor_is_valid = not pd.isna(factor_val)
                            return_is_valid = not pd.isna(return_val)
                            
                            if factor_is_valid and return_is_valid:
                                factor_vals.append(factor_val)
                                return_vals.append(return_val)
                        except:
                            # 如果出现类型错误，跳过这个数据点
                            continue
                
                # 计算当日IC
                if len(factor_vals) >= 2:  # 至少需要2个点来计算相关性
                    factors_np = np.array(factor_vals)
                    returns_np = np.array(return_vals)
                    
                    # 检查是否有足够的数据和变化
                    if len(factors_np) > 1:
                        # 检查数据是否有变化（否则相关系数未定义）
                        if np.var(factors_np) > 0 and np.var(returns_np) > 0:
                            # 计算皮尔逊相关系数
                            correlation_matrix = np.corrcoef(factors_np, returns_np)
                            ic_value = correlation_matrix[0, 1]
                            
                            if not np.isnan(ic_value):
                                ic_values.append(ic_value)
                                ic_dates.append(date)
                            else:
                                ic_values.append(0.0)  # 用0代替NaN
                                ic_dates.append(date)
                        else:
                            # 如果数据没有变化，相关系数为0
                            ic_values.append(0.0)
                            ic_dates.append(date)
                    else:
                        ic_values.append(0.0)
                        ic_dates.append(date)
                
            except Exception as e:
                print(f"计算 {date} 的IC时出错: {e}")
                import traceback
                traceback.print_exc()
        
        if ic_values:
            ic_series = pd.Series(ic_values, index=pd.Index(ic_dates, name='date'), name='ic')
            return ic_series
        else:
            return pd.Series([], dtype=float, name='ic')
    
    def calculate_ic_stats(self, ic_series) -> Dict:
        """
        计算IC统计指标
        
        Args:
            ic_series: IC序列
            
        Returns:
            Dict: IC统计指标
        """
        ic_clean = ic_series.dropna()
        
        if len(ic_clean) == 0:
            return {
                'ic_mean': 0.0,
                'ic_std': 0.0,
                'ic_ir': 0.0,
                'ic_prob': 0.0,
                'ic_abs_mean': 0.0,
                't_stat': 0.0,
                'p_value': 1.0
            }
        
        ic_mean = float(ic_clean.mean())
        ic_std = float(ic_clean.std())
        ic_ir = ic_mean / ic_std if ic_std != 0 else 0.0
        
        # IC大于0的概率
        ic_prob = float((ic_clean > 0).sum() / len(ic_clean)) if len(ic_clean) > 0 else 0.0
        
        # IC绝对值均值
        ic_abs_mean = float(ic_clean.abs().mean())
        
        # 简化的t统计量和p值计算（避免使用scipy）
        n = len(ic_clean)
        t_stat = ic_mean / (ic_std / np.sqrt(n)) if ic_std != 0 and n > 1 else 0.0
        
        # 使用近似方法计算p值（不使用scipy）
        # 这里使用简单的经验法则来估算显著性
        p_value = 1.0  # 默认值
        if n > 1:
            # 使用简单的正态近似来估算p值
            import math
            z_score = abs(t_stat)
            # 使用近似的累积分布函数
            p_value = 2 * (1 - (0.5 * (1 + math.erf(z_score / math.sqrt(2)))))

        return {
            'ic_mean': ic_mean,
            'ic_std': ic_std,
            'ic_ir': ic_ir,
            'ic_prob': ic_prob,
            'ic_abs_mean': ic_abs_mean,
            't_stat': t_stat,
            'p_value': p_value
        }
    
    def analyze_factor_ic(self, factor_data: pd.Series, 
                          returns_data: pd.Series, 
                          factor_name: str = "Factor") -> Dict:
        """
        分析单个因子的IC
        
        Args:
            factor_data: 因子数据 (Series)
            returns_data: 收益率数据 (Series)
            factor_name: 因子名称
            
        Returns:
            Dict: 分析结果
        """
        print(f"开始分析因子 {factor_name} 的IC...")
        
        # 确保收益率数据已正确计算
        returns_clean = returns_data.dropna()
        factor_clean = factor_data.dropna()
        
        if len(returns_clean) == 0 or len(factor_clean) == 0:
            print(f"警告: {factor_name} 的数据为空或全部为NaN")
            # 返回默认统计值
            default_stats = {
                'ic_mean': 0.0,
                'ic_std': 0.0,
                'ic_ir': 0.0,
                'ic_prob': 0.0,
                'ic_abs_mean': 0.0,
                't_stat': 0.0,
                'p_value': 1.0
            }
            
            return {
                'ic_series': pd.Series([], dtype=float, name='ic'),
                'stats': default_stats,
                'factor_name': factor_name
            }
        
        # 计算IC
        ic_series = self.calculate_ic(factor_clean, returns_clean)
        
        # 计算统计指标
        stats = self.calculate_ic_stats(ic_series)
        
        # 保存结果
        self.ic_data[factor_name] = ic_series
        self.ic_stats[factor_name] = stats
        
        # 打印结果
        print(f"{factor_name} IC 分析结果:")
        print(f"  IC均值: {stats['ic_mean']:.6f}")
        print(f"  IC标准差: {stats['ic_std']:.6f}")
        print(f"  IR (IC信息比率): {stats['ic_ir']:.6f}")
        print(f"  IC>0概率: {stats['ic_prob']:.2%}")
        print(f"  IC绝对值均值: {stats['ic_abs_mean']:.6f}")
        print(f"  t统计量: {stats['t_stat']:.6f}")
        print(f"  p值: {stats['p_value']:.6f}")
        
        return {
            'ic_series': ic_series,
            'stats': stats,
            'factor_name': factor_name
        }
    
    def compare_ic_across_factors(self, factor_returns_pairs: List[Tuple[pd.Series, pd.Series, str]]) -> pd.DataFrame:
        """
        比较多个因子的IC
        
        Args:
            factor_returns_pairs: [(factor_data, returns_data, factor_name), ...] 列表
            
        Returns:
            pd.DataFrame: 比较结果
        """
        comparison_data = []
        
        for factor_data, returns_data, factor_name in factor_returns_pairs:
            ic_analysis = self.analyze_factor_ic(factor_data, returns_data, factor_name)
            stats = ic_analysis['stats']
            
            comparison_data.append({
                'factor_name': factor_name,
                'ic_mean': stats['ic_mean'],
                'ic_std': stats['ic_std'],
                'ic_ir': stats['ic_ir'],
                'ic_prob': stats['ic_prob'],
                'ic_abs_mean': stats['ic_abs_mean']
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        return comparison_df.sort_values(by='ic_ir', key=abs, ascending=False)


# 测试代码
if __name__ == '__main__':
    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=60, freq='D')
    symbols = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '000858.SZ']
    
    # 创建多级索引
    index = pd.MultiIndex.from_product([dates, symbols], names=['date', 'symbol'])
    
    # 生成测试数据
    np.random.seed(42)
    factor_data = pd.Series(
        np.random.randn(len(index)), 
        index=index,
        name='factor_value'
    )
    
    # 生成相关性收益数据
    base_returns = pd.Series(
        np.random.randn(len(index)) * 0.01,  # 较小的随机收益率
        index=index,
        name='returns'
    )
    
    print(f"测试数据形状: 因子-{factor_data.shape}, 收益率-{base_returns.shape}")
    print(f"测试数据日期范围: {factor_data.index.get_level_values('date').min()} 到 {factor_data.index.get_level_values('date').max()}")
    
    # 创建IC分析器
    ic_analyzer = ICAnalysis()
    
    # 分析单个因子
    result = ic_analyzer.analyze_factor_ic(
        factor_data=factor_data,
        returns_data=base_returns,
        factor_name="Test_Factor"
    )
    
    print(f"\nIC序列长度: {len(result['ic_series'])}")
    if len(result['ic_series']) > 0:
        print(f"IC序列前5个值: {result['ic_series'].head()}")
    
    # 测试多个因子比较（使用相同数据的不同变换）
    factor2_data = factor_data * -1  # 反向因子
    factor3_data = factor_data.abs()  # 绝对值因子
    
    pairs = [
        (factor_data, base_returns, "Original_Factor"),
        (factor2_data, base_returns, "Inverse_Factor"),
        (factor3_data, base_returns, "Abs_Factor")
    ]
    
    comparison = ic_analyzer.compare_ic_across_factors(pairs)
    print("\n因子IC比较结果:")
    print(comparison)
    
    print("\nIC分析测试完成!")