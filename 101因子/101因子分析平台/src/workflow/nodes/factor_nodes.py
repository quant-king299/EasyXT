"""
因子节点
实现各种因子计算和处理节点
"""
from .base import TransformNode
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import sys
import os

# 添加项目路径
project_path = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_path)

from src.factor_engine.calculator import FactorCalculator
from src.factor_engine.operators import ts_sum, sma, stddev, correlation, covariance, ts_rank, ts_argmax, ts_argmin, ts_min, ts_max, delta, delay, rank, scale, decay_linear


class FactorCalculatorNode(TransformNode):
    """因子计算节点"""
    
    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)
    
    def _execute_transform(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行因子计算"""
        # 获取输入数据
        if 'factor_data' in input_data:
            data = input_data['factor_data']
        elif 'price_data' in input_data:
            data = input_data['price_data']
        else:
            raise ValueError("缺少因子计算所需的数据")
        
        factor_name = self.params.get('factor_name', 'alpha001')
        
        # 使用因子计算器
        calculator = FactorCalculator()
        factor_result = calculator.calculate_single_factor(data, factor_name)
        
        self.outputs = {
            'factor_data': factor_result,
            'factor_name': factor_name,
            'factor_stats': self._calculate_factor_stats(factor_result)
        }
        
        return self.outputs
    
    def _calculate_factor_stats(self, factor_data: pd.Series) -> Dict[str, float]:
        """计算因子统计信息"""
        if factor_data is None or len(factor_data) == 0:
            return {}
        
        return {
            'mean': float(factor_data.mean()),
            'std': float(factor_data.std()),
            'min': float(factor_data.min()),
            'max': float(factor_data.max()),
            'nan_count': int(factor_data.isna().sum()),
            'total_count': len(factor_data)
        }


class FactorCombinationNode(TransformNode):
    """因子组合节点"""
    
    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)
    
    def _execute_transform(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行因子组合"""
        # 获取多个因子数据
        factor_data_list = []
        factor_names = []
        
        # 从输入数据中查找因子
        for key, value in input_data.items():
            if isinstance(value, pd.Series) and key.endswith('_data'):
                factor_data_list.append(value)
                factor_names.append(key.replace('_data', ''))
        
        # 或者从参数中获取因子名称列表
        if not factor_data_list and 'factor_names' in self.params:
            factor_names = self.params['factor_names']
            if 'price_data' in input_data:
                data = input_data['price_data']
                calculator = FactorCalculator()
                for name in factor_names:
                    factor_data_list.append(calculator.calculate_single_factor(data, name))
        
        if not factor_data_list:
            raise ValueError("没有找到因子数据进行组合")
        
        # 对齐所有因子数据
        combined_factor = factor_data_list[0]
        for factor in factor_data_list[1:]:
            aligned_combined, aligned_factor = combined_factor.align(factor, join='inner')
            combined_factor = aligned_combined
        
        # 应用组合方法
        combination_method = self.params.get('method', 'average')
        weights = self.params.get('weights', [1.0/len(factor_data_list)] * len(factor_data_list))
        
        if combination_method == 'weighted_average':
            # 加权平均
            if len(weights) != len(factor_data_list):
                weights = [1.0/len(factor_data_list)] * len(factor_data_list)
            
            combined_factor = sum(w * f for w, f in zip(weights, factor_data_list))
        elif combination_method == 'rank_combination':
            # 排名组合
            rank_factors = [f.groupby(level=0).rank(pct=True) for f in factor_data_list]
            combined_factor = sum(rank_factors) / len(rank_factors)
        elif combination_method == 'zscore_combination':
            # Z-Score标准化后组合
            zscore_factors = [(f - f.mean()) / f.std() for f in factor_data_list]
            combined_factor = sum(zscore_factors) / len(zscore_factors)
        else:
            # 简单平均
            combined_factor = sum(factor_data_list) / len(factor_data_list)
        
        self.outputs = {
            'combined_factor': combined_factor,
            'factor_names': factor_names,
            'combination_method': combination_method,
            'weights': weights
        }
        
        return self.outputs


class FactorProcessingNode(TransformNode):
    """因子处理节点"""
    
    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)
    
    def _execute_transform(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行因子处理"""
        # 获取因子数据
        factor_data = None
        for key, value in input_data.items():
            if isinstance(value, pd.Series) and ('factor' in key or 'data' in key):
                factor_data = value
                break
        
        if factor_data is None and 'factor_data' in input_data:
            factor_data = input_data['factor_data']
        
        if factor_data is None:
            raise ValueError("缺少因子数据进行处理")
        
        # 应用处理方法
        processing_method = self.params.get('method', 'standardize')
        
        processed_factor = self._apply_processing(factor_data, processing_method)
        
        self.outputs = {
            'processed_factor': processed_factor,
            'original_factor': factor_data,
            'processing_method': processing_method
        }
        
        return self.outputs
    
    def _apply_processing(self, factor_data: pd.Series, method: str) -> pd.Series:
        """应用处理方法"""
        if method == 'standardize':
            # Z-Score标准化
            mean_val = factor_data.groupby(level=0).transform('mean')
            std_val = factor_data.groupby(level=0).transform('std')
            return (factor_data - mean_val) / std_val.replace(0, 1)  # 避免除零
        elif method == 'rank':
            # 排序转换
            return factor_data.groupby(level=0).rank(pct=True)
        elif method == 'neutralize':
            # 行业中性化（简化版）
            return factor_data.groupby(level=0).apply(lambda x: x - x.mean())
        elif method == 'winsorize':
            # 去极值处理（winsorize）
            def winsorize_series(s):
                q95 = s.quantile(0.95)
                q05 = s.quantile(0.05)
                return s.clip(q05, q95)
            return factor_data.groupby(level=0).apply(winsorize_series)
        elif method == 'smooth':
            # 平滑处理
            return factor_data.groupby(level=1).transform(lambda x: x.rolling(window=3, min_periods=1).mean())
        else:
            return factor_data


class FactorFilterNode(TransformNode):
    """因子过滤节点"""
    
    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)
    
    def _execute_transform(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行因子过滤"""
        # 获取因子数据
        factor_data = None
        for key, value in input_data.items():
            if isinstance(value, pd.Series) and ('factor' in key or 'data' in key):
                factor_data = value
                break
        
        if factor_data is None and 'factor_data' in input_data:
            factor_data = input_data['factor_data']
        
        if factor_data is None:
            raise ValueError("缺少因子数据进行过滤")
        
        # 应用过滤条件
        filtered_factor = self._apply_filtering(factor_data)
        
        self.outputs = {
            'filtered_factor': filtered_factor,
            'original_factor': factor_data,
            'filter_params': self.params
        }
        
        return self.outputs
    
    def _apply_filtering(self, factor_data: pd.Series) -> pd.Series:
        """应用过滤条件"""
        # 去除NaN值
        filtered = factor_data.dropna()
        
        # 应用极值过滤
        if 'min_value' in self.params:
            min_val = self.params['min_value']
            filtered = filtered[filtered >= min_val]
        
        if 'max_value' in self.params:
            max_val = self.params['max_value']
            filtered = filtered[filtered <= max_val]
        
        # 应用股票池过滤
        if 'universe_filter' in self.params:
            universe = self.params['universe_filter']
            if isinstance(universe, list):
                mask = filtered.index.get_level_values(1).isin(universe)
                filtered = filtered[mask]
        
        # 应用日期过滤
        if 'date_filter' in self.params:
            date_range = self.params['date_filter']
            if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                start_date, end_date = date_range
                mask = (filtered.index.get_level_values(0) >= start_date) & \
                       (filtered.index.get_level_values(0) <= end_date)
                filtered = filtered[mask]
        
        return filtered


class FactorAnalysisNode(TransformNode):
    """因子分析节点"""
    
    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)
    
    def _execute_transform(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行因子分析"""
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
        
        if factor_data is None:
            raise ValueError("缺少因子数据进行分析")
        
        # 计算因子分析指标
        analysis_results = self._perform_factor_analysis(factor_data, returns_data)
        
        self.outputs = {
            'analysis_results': analysis_results,
            'factor_data': factor_data,
            'returns_data': returns_data
        }
        
        return self.outputs
    
    def _perform_factor_analysis(self, factor_data: pd.Series, returns_data: pd.Series = None) -> Dict[str, Any]:
        """执行因子分析"""
        analysis = {}
        
        # 基本统计
        analysis['basic_stats'] = {
            'mean': float(factor_data.mean()) if len(factor_data) > 0 else 0.0,
            'std': float(factor_data.std()) if len(factor_data) > 0 else 0.0,
            'min': float(factor_data.min()) if len(factor_data) > 0 else 0.0,
            'max': float(factor_data.max()) if len(factor_data) > 0 else 0.0,
            'nan_ratio': float(factor_data.isna().sum() / len(factor_data)) if len(factor_data) > 0 else 0.0
        }
        
        # 分布特征
        analysis['distribution'] = {
            'skewness': float(factor_data.skew()) if len(factor_data) > 0 else 0.0,
            'kurtosis': float(factor_data.kurtosis()) if len(factor_data) > 0 else 0.0
        }
        
        # 如果有收益率数据，计算IC
        if returns_data is not None:
            from src.analysis.ic_analysis import ICAnalysis
            ic_analyzer = ICAnalysis()
            ic_series = ic_analyzer.calculate_ic(factor_data, returns_data)
            ic_stats = ic_analyzer.calculate_ic_stats(ic_series)
            
            analysis['ic_analysis'] = {
                'ic_series': ic_series,
                'ic_stats': ic_stats,
                'ic_timeseries': ic_series.values.tolist() if len(ic_series) > 0 else []
            }
        
        # 计算因子换手率（基于因子值变化）
        analysis['turnover_analysis'] = self._calculate_turnover(factor_data)
        
        return analysis
    
    def _calculate_turnover(self, factor_data: pd.Series) -> Dict[str, float]:
        """计算因子换手率"""
        try:
            # 按日期分组，计算因子值的变化
            dates = sorted(factor_data.index.get_level_values(0).unique())
            if len(dates) < 2:
                return {'turnover_rate': 0.0}
            
            factor_changes = []
            for i in range(1, len(dates)):
                current_date = dates[i]
                prev_date = dates[i-1]
                
                current_factors = factor_data[factor_data.index.get_level_values(0) == current_date]
                prev_factors = factor_data[factor_data.index.get_level_values(0) == prev_date]
                
                # 对齐数据
                aligned_current, aligned_prev = current_factors.align(prev_factors, join='inner')
                if len(aligned_current) > 0:
                    # 计算变化率
                    change = ((aligned_current - aligned_prev) / aligned_prev).abs().mean()
                    factor_changes.append(float(change) if not pd.isna(change) else 0.0)
            
            avg_turnover = np.mean(factor_changes) if factor_changes else 0.0
            return {'turnover_rate': avg_turnover}
        except:
            return {'turnover_rate': 0.0}