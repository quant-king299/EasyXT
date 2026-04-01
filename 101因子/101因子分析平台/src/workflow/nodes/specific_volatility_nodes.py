"""
特质波动率因子节点

实现特质波动率因子计算和处理的节点
"""
from .base import TransformNode
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
import sys
import os

# 添加项目路径
project_path = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_path)

from src.factor_engine.specific_volatility import (
    SpecificVolatilityCalculator,
    SpecificVolatilityFactor
)


class SpecificVolatilityNode(TransformNode):
    """特质波动率计算节点"""

    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)

    def _execute_transform(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行特质波动率计算"""
        # 获取输入数据
        if 'returns_data' not in input_data and 'price_data' not in input_data:
            raise ValueError("缺少收益率数据或价格数据")

        # 获取参数
        window = self.params.get('window', 20)
        market_return_col = self.params.get('market_return_col', 'market_return')

        # 准备数据
        if 'returns_data' in input_data:
            returns_df = input_data['returns_data']
        else:
            # 从价格数据计算收益率
            price_df = input_data['price_data']
            returns_df = self._calculate_returns(price_df)

        # 获取市场收益率
        if market_return_col in returns_df.columns:
            market_returns = returns_df.set_index('date')[market_return_col]
        else:
            # 如果没有市场收益率，计算等权市场收益率
            market_returns = self._calculate_market_returns(returns_df)

        # 计算特质波动率
        calculator = SpecificVolatilityCalculator(window=window)

        # 准备股票收益率数据
        if 'stock_code' in returns_df.columns:
            pivot_df = returns_df.pivot(index='date', columns='stock_code', values='return')
        else:
            pivot_df = returns_df

        # 批量计算特质波动率
        spec_vol_df = calculator.calculate_batch_specific_volatility(
            pivot_df,
            market_returns,
            window=window
        )

        # 计算统计信息
        spec_vol_stats = self._calculate_stats(spec_vol_df)

        self.outputs = {
            'specific_volatility': spec_vol_df,
            'window': window,
            'stats': spec_vol_stats
        }

        return self.outputs

    def _calculate_returns(self, price_df: pd.DataFrame) -> pd.DataFrame:
        """从价格数据计算收益率"""
        if 'close' in price_df.columns:
            df = price_df.copy()
            if 'stock_code' in df.columns:
                df['return'] = df.groupby('stock_code')['close'].pct_change()
            else:
                df['return'] = df['close'].pct_change()
            return df
        else:
            raise ValueError("价格数据中缺少close列")

    def _calculate_market_returns(self, returns_df: pd.DataFrame) -> pd.Series:
        """计算市场收益率（等权平均）"""
        if 'stock_code' in returns_df.columns:
            market_returns = returns_df.groupby('date')['return'].mean()
        else:
            market_returns = returns_df.mean(axis=1)
        return market_returns

    def _calculate_stats(self, spec_vol_df: pd.DataFrame) -> Dict[str, Any]:
        """计算统计信息"""
        if spec_vol_df.empty:
            return {}

        return {
            'mean': float(spec_vol_df.mean().mean()),
            'std': float(spec_vol_df.std().mean()),
            'min': float(spec_vol_df.min().min()),
            'max': float(spec_vol_df.max().max()),
            'n_stocks': len(spec_vol_df.columns),
            'n_dates': len(spec_vol_df)
        }


class MultiWindowSpecificVolatilityNode(TransformNode):
    """多窗口特质波动率计算节点"""

    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)

    def _execute_transform(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行多窗口特质波动率计算"""
        # 获取输入数据
        if 'returns_data' not in input_data and 'price_data' not in input_data:
            raise ValueError("缺少收益率数据或价格数据")

        # 获取参数
        windows = self.params.get('windows', [20, 60, 120])
        market_return_col = self.params.get('market_return_col', 'market_return')

        # 准备数据
        if 'returns_data' in input_data:
            returns_df = input_data['returns_data']
        else:
            # 从价格数据计算收益率
            price_df = input_data['price_data']
            returns_df = self._calculate_returns(price_df)

        # 获取市场收益率
        if market_return_col in returns_df.columns:
            market_returns = returns_df.set_index('date')[market_return_col]
        else:
            # 如果没有市场收益率，计算等权市场收益率
            market_returns = self._calculate_market_returns(returns_df)

        # 准备股票收益率数据
        if 'stock_code' in returns_df.columns:
            pivot_df = returns_df.pivot(index='date', columns='stock_code', values='return')
        else:
            pivot_df = returns_df

        # 计算多个窗口的特质波动率
        results = {}
        for window in windows:
            calculator = SpecificVolatilityCalculator(window=window)
            spec_vol_df = calculator.calculate_batch_specific_volatility(
                pivot_df,
                market_returns,
                window=window
            )
            results[f'window_{window}'] = spec_vol_df

        # 计算统计信息
        stats = {}
        for window_name, spec_vol_df in results.items():
            if not spec_vol_df.empty:
                stats[window_name] = {
                    'mean': float(spec_vol_df.mean().mean()),
                    'std': float(spec_vol_df.std().mean()),
                    'n_stocks': len(spec_vol_df.columns),
                    'n_dates': len(spec_vol_df)
                }

        self.outputs = {
            'specific_volatility_multi': results,
            'windows': windows,
            'stats': stats
        }

        return self.outputs

    def _calculate_returns(self, price_df: pd.DataFrame) -> pd.DataFrame:
        """从价格数据计算收益率"""
        if 'close' in price_df.columns:
            df = price_df.copy()
            if 'stock_code' in df.columns:
                df['return'] = df.groupby('stock_code')['close'].pct_change()
            else:
                df['return'] = df['close'].pct_change()
            return df
        else:
            raise ValueError("价格数据中缺少close列")

    def _calculate_market_returns(self, returns_df: pd.DataFrame) -> pd.Series:
        """计算市场收益率（等权平均）"""
        if 'stock_code' in returns_df.columns:
            market_returns = returns_df.groupby('date')['return'].mean()
        else:
            market_returns = returns_df.mean(axis=1)
        return market_returns


class SpecificVolatilityFactorNode(TransformNode):
    """特质波动率因子节点（使用Factor类）"""

    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)

    def _execute_transform(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行特质波动率因子计算"""
        # 获取输入数据
        if 'factor_data' not in input_data and 'returns_data' not in input_data:
            raise ValueError("缺少因子数据或收益率数据")

        # 获取参数
        windows = self.params.get('windows', [20, 60, 120])
        market_return_col = self.params.get('market_return_col', 'market_return')

        # 准备数据
        if 'factor_data' in input_data:
            factor_df = input_data['factor_data']
        elif 'returns_data' in input_data:
            returns_df = input_data['returns_data']
            # 转换为因子数据格式
            factor_df = returns_df.rename(columns={'return': 'return'})
        else:
            raise ValueError("无法准备因子数据")

        # 使用SpecificVolatilityFactor类计算
        factor = SpecificVolatilityFactor(windows=windows)
        result_df = factor.calculate(factor_df, market_return_col=market_return_col)

        # 计算统计信息
        stats = {}
        for col in result_df.columns:
            stats[col] = {
                'mean': float(result_df[col].mean()),
                'std': float(result_df[col].std()),
                'min': float(result_df[col].min()),
                'max': float(result_df[col].max()),
                'nan_count': int(result_df[col].isna().sum())
            }

        self.outputs = {
            'specific_volatility_factor': result_df,
            'windows': windows,
            'stats': stats,
            'factor_names': list(result_df.columns)
        }

        return self.outputs


# 导出节点类
__all__ = [
    'SpecificVolatilityNode',
    'MultiWindowSpecificVolatilityNode',
    'SpecificVolatilityFactorNode'
]
