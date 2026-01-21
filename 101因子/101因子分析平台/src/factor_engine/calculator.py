"""
因子计算器主类
整合EasyXT数据加载和Alpha101/Alpha191因子计算
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import sys
import os

# 添加项目路径
project_path = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_path)

from src.easyxt_adapter.api_wrapper import get_easyxt_instance
from src.factor_engine.alpha101 import Alpha101Factors
from src.factor_engine.alpha191 import Alpha191Factors, calculate_alpha191_factor


class FactorCalculator:
    """
    因子计算器主类
    整合数据获取、因子计算、分析功能
    """
    
    def __init__(self):
        """初始化因子计算器"""
        self.easyxt_api = get_easyxt_instance()
        self.factor_data = {}
        self.raw_data = None
    
    def load_data(self, symbols: List[str], start_date: str, end_date: str,
                  fields: Optional[List[str]] = None) -> pd.DataFrame:
        """
        加载数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            fields: 字段列表
            
        Returns:
            pd.DataFrame: 加载的数据
        """
        print(f"正在加载数据: {symbols} 从 {start_date} 到 {end_date}")
        self.raw_data = self.easyxt_api.get_market_data(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            fields=fields
        )
        print(f"数据加载完成，形状: {self.raw_data.shape}")
        return self.raw_data
    
    def calculate_factors(self, factor_names: Optional[List[str]] = None) -> Dict[str, pd.DataFrame]:
        """
        计算因子
        
        Args:
            factor_names: 要计算的因子名称列表，如果为None则计算所有因子
            
        Returns:
            Dict[str, pd.DataFrame]: 因子名称到因子值的映射
        """
        if self.raw_data is None:
            raise ValueError("请先加载数据")
        
        print("开始计算因子...")
        alpha_calculator = Alpha101Factors(self.raw_data)
        
        if factor_names is None:
            # 计算所有因子
            self.factor_data = alpha_calculator.calculate_all_factors()
        else:
            # 计算指定因子
            self.factor_data = {}
            for factor_name in factor_names:
                try:
                    factor_value = alpha_calculator.calculate_single_factor(factor_name)
                    self.factor_data[factor_name] = factor_value
                    print(f"成功计算因子: {factor_name}")
                except Exception as e:
                    print(f"计算因子 {factor_name} 时出错: {e}")
        
        print(f"因子计算完成，共计算了 {len(self.factor_data)} 个因子")
        return self.factor_data
    
    def calculate_single_factor(self, data: pd.DataFrame, factor_name: str) -> pd.Series:
        """
        计算单个因子（支持Alpha101和Alpha191因子）

        Args:
            data: 输入数据
            factor_name: 因子名称（如'alpha001'或'alpha102'）

        Returns:
            pd.Series: 因子值
        """
        # 判断是Alpha101还是Alpha191因子
        if factor_name.startswith('alpha') and 1 <= int(factor_name[5:]) <= 101:
            # Alpha101因子 (alpha001-alpha101)
            alpha_calculator = Alpha101Factors(data)
            try:
                factor_values = alpha_calculator.calculate_single_factor(factor_name)

                # 如果factor_values是DataFrame，需要重新转换回MultiIndex格式
                if isinstance(factor_values, pd.DataFrame):
                    # 将DataFrame重新转换为MultiIndex Series格式
                    if not factor_values.empty:
                        # 检查是否有重复的索引，避免stack操作出错
                        if factor_values.index.duplicated().any():
                            # 如果有重复索引，先去重
                            factor_values = factor_values[~factor_values.index.duplicated(keep='first')]

                        # 在stack之前，检查列名是否正确
                        print(f"[DEBUG] Alpha101因子 - stacking DataFrame with columns: {factor_values.columns.tolist()[:10]}")  # 只显示前10个列名

                        # 将DataFrame从宽格式转换为长格式
                        result_series = factor_values.stack()

                        print(f"[DEBUG] Calculator - stacking 后: type={type(result_series)}, shape={result_series.shape if hasattr(result_series, 'shape') else 'N/A'}, index_type={type(result_series.index)}, index_names={result_series.index.names if hasattr(result_series.index, 'names') else 'N/A'}")

                    # 检查stack后的索引情况
                    if isinstance(result_series.index, pd.MultiIndex):
                        print(f"FactorCalculator - after stacking, index names: {result_series.index.names}")
                        print(f"FactorCalculator - after stacking, symbol level unique values: {result_series.index.get_level_values(1).unique().tolist()[:10] if len(result_series.index.names) > 1 else 'N/A'}")

                        # 确保MultiIndex的名称是正确的
                        if len(result_series.index.names) >= 2:
                            result_series.index.names = ['date', 'symbol']
                        else:
                            # 如果索引名字不够，设置默认名字
                            result_series.index.names = ['date', 'symbol']
                    result_series.name = factor_name
                    print(f"[DEBUG] Calculator - 返回前: type={type(result_series)}, shape={result_series.shape}, index_names={result_series.index.names}")
                    return result_series  # 直接返回，不要重新包装
                elif isinstance(factor_values, pd.Series):
                    # 如果已经是Series，但不是MultiIndex格式，需要确保格式正确
                    if isinstance(factor_values.index, pd.MultiIndex):
                        factor_values.name = factor_name
                        return factor_values  # 直接返回
                    else:
                        # 如果是普通Series，需要根据输入数据的索引格式进行处理
                        factor_series = factor_values.reindex(data.index)
                        factor_series.name = factor_name
                        return factor_series  # 直接返回
                else:
                    # 如果是其他类型，创建一个适当索引的Series
                    factor_series = pd.Series(factor_values, index=data.index, name=factor_name)
                    return factor_series
            except Exception as e:
                print(f"计算Alpha101因子 {factor_name} 时出错: {e}")
                import traceback
                traceback.print_exc()
                # 返回一个空的Series，但保持相同的索引
                return pd.Series(index=data.index, dtype=float, name=factor_name)
        elif factor_name.startswith('alpha') and 102 <= int(factor_name[5:]) <= 191:
            # Alpha191因子 (alpha102-alpha191)
            print(f"[DEBUG] 计算Alpha191因子: {factor_name}")
            try:
                factor_values = calculate_alpha191_factor(data, factor_name)

                # Alpha191返回的是直接的Series
                if isinstance(factor_values, pd.Series):
                    # 确保有正确的名称
                    factor_values.name = factor_name
                    print(f"[DEBUG] Alpha191因子计算成功，形状: {factor_values.shape}")
                    return factor_values
                else:
                    print(f"[WARNING] Alpha191因子返回类型错误: {type(factor_values)}")
                    return pd.Series(index=data.index, dtype=float, name=factor_name)
            except Exception as e:
                print(f"计算Alpha191因子 {factor_name} 时出错: {e}")
                import traceback
                traceback.print_exc()
                # 返回一个空的Series，但保持相同的索引
                return pd.Series(index=data.index, dtype=float, name=factor_name)
        else:
            # 不支持的因子
            raise ValueError(f"不支持的因子: {factor_name}。仅支持alpha001-alpha101和alpha102-alpha191")

    def get_factor_names(self) -> List[str]:
        """
        获取所有可用的因子名称
        
        Returns:
            List[str]: 因子名称列表
        """
        alpha_calculator = Alpha101Factors(self._get_empty_data())
        factor_methods = [method for method in dir(alpha_calculator) if method.startswith('alpha') and method[5:].isdigit()]
        return factor_methods
    
    def _get_empty_data(self) -> pd.DataFrame:
        """获取空数据用于获取因子名称"""
        # 创建一个空的示例数据
        index = pd.MultiIndex.from_tuples([], names=['date', 'symbol'])
        empty_df = pd.DataFrame(index=index)
        empty_df['open'] = pd.Series([], dtype=float, index=empty_df.index)
        empty_df['high'] = pd.Series([], dtype=float, index=empty_df.index)
        empty_df['low'] = pd.Series([], dtype=float, index=empty_df.index)
        empty_df['close'] = pd.Series([], dtype=float, index=empty_df.index)
        empty_df['volume'] = pd.Series([], dtype=float, index=empty_df.index)
        return empty_df
    
    def analyze_factor(self, factor_name: str, target_col: str = 'close') -> Dict:
        """
        分析单个因子
        
        Args:
            factor_name: 因子名称
            target_col: 目标列（用于计算收益率相关性）
            
        Returns:
            Dict: 分析结果
        """
        if factor_name not in self.factor_data:
            raise ValueError(f"因子 {factor_name} 未计算")
        
        factor_values = self.factor_data[factor_name]
        
        # 确保factor_values是Series
        if isinstance(factor_values, pd.DataFrame):
            if len(factor_values.columns) > 0:
                factor_series = factor_values.iloc[:, 0]
            else:
                factor_series = pd.Series(dtype=float)
        elif isinstance(factor_values, pd.Series):
            factor_series = factor_values
        else:
            factor_series = pd.Series([factor_values] * len(self.raw_data)) if self.raw_data is not None else pd.Series(dtype=float)
        
        # 计算因子与收益率的相关性（IC）
        if self.raw_data is not None and target_col in self.raw_data.columns:
            try:
                # 获取目标列的收益率
                returns_data = self.raw_data.groupby(level=1)[target_col].pct_change()  # 按股票分组计算收益率
                
                # 确保returns_data是Series
                if isinstance(returns_data, pd.DataFrame) and len(returns_data.columns) > 0:
                    returns_series = returns_data.iloc[:, 0]
                elif isinstance(returns_data, pd.Series):
                    returns_series = returns_data
                else:
                    returns_series = pd.Series(dtype=float)
                
                # 对齐因子值和收益率
                aligned_factor, aligned_returns = factor_series.align(returns_series, join='inner')
                
                # 确保两者都是Series且有数据
                if len(aligned_factor) > 1 and len(aligned_returns) > 1 and len(aligned_factor) == len(aligned_returns):
                    # 计算IC（信息系数）
                    ic = aligned_factor.corr(aligned_returns)
                    
                    # 计算IC的均值和标准差
                    ic_mean = float(ic) if not np.isnan(ic) else 0.0
                    ic_std = aligned_factor.std() * aligned_returns.std() if len(aligned_factor) > 0 and len(aligned_returns) > 0 else 0.0
                    ic_ir = ic_mean / ic_std if ic_std != 0 else 0.0
                else:
                    ic_mean = 0.0
                    ic_std = 0.0
                    ic_ir = 0.0
                
                analysis_result = {
                    'ic_mean': ic_mean,
                    'ic_std': ic_std,
                    'ic_ir': ic_ir,
                    'factor_desc': f"因子 {factor_name} 与 {target_col} 收益率的相关性分析"
                }
            except Exception as e:
                print(f"分析因子 {factor_name} 时出错: {e}")
                analysis_result = {
                    'ic_mean': 0.0,
                    'ic_std': 0.0,
                    'ic_ir': 0.0,
                    'factor_desc': f"因子 {factor_name} 分析出错: {str(e)}"
                }
        else:
            analysis_result = {
                'ic_mean': 0.0,
                'ic_std': 0.0,
                'ic_ir': 0.0,
                'factor_desc': f"因子 {factor_name} 分析（无收益率数据）"
            }
        
        return analysis_result
    
    def analyze_all_factors(self) -> Dict[str, Dict]:
        """
        分析所有已计算的因子
        
        Returns:
            Dict[str, Dict]: 所有因子的分析结果
        """
        analysis_results = {}
        for factor_name in self.factor_data.keys():
            try:
                analysis_results[factor_name] = self.analyze_factor(factor_name)
            except Exception as e:
                print(f"分析因子 {factor_name} 时出错: {e}")
                analysis_results[factor_name] = {
                    'error': str(e),
                    'factor_desc': f"因子 {factor_name} 分析出错"
                }
        
        return analysis_results


# 测试代码
if __name__ == '__main__':
    # 创建因子计算器
    calculator = FactorCalculator()
    
    # 获取股票池
    symbols = calculator.easyxt_api.get_universe("hs300")[:5]  # 取前5只股票
    print(f"使用的股票: {symbols}")
    
    # 加载数据
    start_date = '2023-01-01'
    end_date = '2023-02-01'
    data = calculator.load_data(symbols, start_date, end_date)
    
    print(f"数据列: {list(data.columns)}")
    print(f"数据形状: {data.shape}")
    print(f"日期范围: {data.index.get_level_values('date').min()} 到 {data.index.get_level_values('date').max()}")
    
    # 计算部分因子进行测试
    factor_names = ['alpha001', 'alpha002', 'alpha003']
    factors = calculator.calculate_factors(factor_names)
    
    print(f"\n计算的因子数量: {len(factors)}")
    for name, values in factors.items():
        print(f"{name} 形状: {values.shape}")
    
    # 分析因子
    print("\n开始因子分析...")
    analysis = calculator.analyze_all_factors()
    
    for factor_name, result in analysis.items():
        if 'error' not in result:
            print(f"{factor_name}: IC均值={result['ic_mean']:.4f}, IC_IR={result['ic_ir']:.4f}")
        else:
            print(f"{factor_name}: 分析出错 - {result['error']}")
    
    print("\n因子计算和分析完成!")