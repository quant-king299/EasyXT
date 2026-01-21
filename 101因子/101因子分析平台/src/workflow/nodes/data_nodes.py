"""
数据节点
实现各种数据加载和处理节点
"""
from .base import DataNode
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import sys
import os

# 添加项目路径
project_path = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_path)

from src.easyxt_adapter.data_loader import EasyXTDataLoader


class DataLoaderNode(DataNode):
    """数据加载节点"""
    
    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)
    
    def _execute_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行数据加载"""
        symbols = self.params.get('symbols', [])
        start_date = self.params.get('start_date', '2023-01-01')
        end_date = self.params.get('end_date', '2023-12-31')
        fields = self.params.get('fields', ['open', 'high', 'low', 'close', 'volume'])
        
        # 第三重保险：节点执行层强制清洗
        if isinstance(symbols, str):
            symbols = [s.strip() for s in symbols.split(',') if s.strip()]
        
        loader = EasyXTDataLoader()
        data = loader.get_historical_data(symbols, start_date, end_date, fields)
        
        # 强制结构校检
        if not data.empty and hasattr(data.index, 'get_level_values'):
            actual_symbols = data.index.get_level_values('symbol').unique().tolist()
            if any(len(str(s)) == 1 for s in actual_symbols[:5]):
                 print(f"检测到异常symbol结构，强制重新处理: {actual_symbols[:5]}")
                 # 如果发现结构破坏，尝试重置索引并修复
                 data = data.reset_index()
                 # 这种情况下 data 肯定是有问题的，我们尝试重新过滤 symbols
                 valid_symbols = [s for s in symbols if len(str(s)) > 1]
                 data = data[data['symbol'].isin(valid_symbols)]
                 data = data.set_index(['date', 'symbol']).sort_index()

        self.outputs = {
            'data': data,
            'symbols': ','.join(symbols) if isinstance(symbols, list) else symbols,
            'symbol_list': symbols,  # 保留原始列表供其他用途
            'date_range': (start_date, end_date),
            'fields': fields
        }
        
        return self.outputs


class FactorDataNode(DataNode):
    """因子数据节点"""
    
    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)
    
    def _execute_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行因子数据准备"""
        # 从输入数据中获取基础数据
        if 'data' in input_data:
            raw_data = input_data['data']
        else:
            # 如果没有输入数据，加载默认数据
            symbols = self.params.get('symbols', ['000001.SZ', '000002.SZ', '600000.SH'])
            start_date = self.params.get('start_date', '2023-01-01')
            end_date = self.params.get('end_date', '2023-12-31')
            
            # 强制转换，防止字符分解
            if isinstance(symbols, str):
                symbols = [s.strip() for s in symbols.split(',') if s.strip()]
                
            loader = EasyXTDataLoader()
            raw_data = loader.get_historical_data(symbols, start_date, end_date)
        
        # 准备因子计算所需的数据格式
        factor_data = self._prepare_factor_data(raw_data)
        
        self.outputs = {
            'factor_data': factor_data,
            'price_data': raw_data,
            'universe': raw_data.index.get_level_values(1).unique().tolist() if hasattr(raw_data.index, 'get_level_values') else []
        }
        
        return self.outputs
    
    def _prepare_factor_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """准备因子数据"""
        # 确保数据格式正确
        if isinstance(raw_data, pd.DataFrame):
            # 计算收益率
            if 'close' in raw_data.columns:
                # 按股票分组计算收益率
                raw_data['returns'] = raw_data.groupby(level=1)['close'].pct_change()
            
            # 计算其他常用指标
            if all(col in raw_data.columns for col in ['high', 'low', 'close']):
                raw_data['hl_ratio'] = (raw_data['high'] - raw_data['low']) / raw_data['close']
            
            return raw_data
        else:
            return pd.DataFrame()


class PriceDataNode(DataNode):
    """价格数据节点"""
    
    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)
    
    def _execute_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行价格数据准备"""
        # 从输入获取数据或加载新数据
        if 'data' in input_data:
            raw_data = input_data['data']
        else:
            symbols = self.params.get('symbols', ['000001.SZ'])
            start_date = self.params.get('start_date', '2023-01-01')
            end_date = self.params.get('end_date', '2023-12-31')
            
            # 强制转换，防止字符分解
            if isinstance(symbols, str):
                symbols = [s.strip() for s in symbols.split(',') if s.strip()]
                
            loader = EasyXTDataLoader()
            raw_data = loader.get_historical_data(symbols, start_date, end_date)
        
        # 提取价格相关数据
        price_fields = ['open', 'high', 'low', 'close', 'volume']
        price_data = raw_data[[col for col in price_fields if col in raw_data.columns]].copy()
        
        # 计算额外的价格指标
        if 'close' in price_data.columns:
            price_data['prev_close'] = price_data.groupby(level=1)['close'].shift(1)
            price_data['returns'] = price_data['close'] / price_data['prev_close'] - 1
            price_data['log_returns'] = np.log(price_data['close'] / price_data['prev_close'])
        
        if all(col in price_data.columns for col in ['high', 'low', 'close']):
            price_data['hl_pct'] = (price_data['high'] - price_data['low']) / price_data['close']
        
        self.outputs = {
            'price_data': price_data,
            'returns_data': price_data.get('returns'),
            'volume_data': price_data.get('volume'),
            'basic_indicators': self._calculate_basic_indicators(price_data)
        }
        
        return self.outputs
    
    def _calculate_basic_indicators(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """计算基础技术指标"""
        indicators = pd.DataFrame(index=price_data.index)
        
        # 移动平均线
        if 'close' in price_data.columns:
            close = price_data['close']
            indicators['ma5'] = close.groupby(level=1).rolling(window=5).mean().droplevel(0)
            indicators['ma10'] = close.groupby(level=1).rolling(window=10).mean().droplevel(0)
            indicators['ma20'] = close.groupby(level=1).rolling(window=20).mean().droplevel(0)
        
        # 波动率
        if 'returns' in price_data.columns:
            returns = price_data['returns']
            indicators['volatility'] = returns.groupby(level=1).rolling(window=20).std().droplevel(0)
        
        # 价格相对位置
        if all(col in price_data.columns for col in ['high', 'low', 'close']):
            high = price_data['high']
            low = price_data['low']
            close = price_data['close']
            
            indicators['hl_ratio'] = (close - low) / (high - low)  # 当前价格在高低区间的位置
        
        return indicators


class MarketDataNode(DataNode):
    """市场数据节点"""
    
    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)
    
    def _execute_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行市场数据准备"""
        # 获取基础数据
        if 'data' in input_data:
            raw_data = input_data['data']
        else:
            symbols = self.params.get('symbols', ['000001.SZ'])
            start_date = self.params.get('start_date', '2023-01-01')
            end_date = self.params.get('end_date', '2023-12-31')
            
            # 强制转换，防止字符分解
            if isinstance(symbols, str):
                symbols = [s.strip() for s in symbols.split(',') if s.strip()]
                
            loader = EasyXTDataLoader()
            raw_data = loader.get_historical_data(symbols, start_date, end_date)
        
        # 计算市场级别的指标
        market_data = self._calculate_market_indicators(raw_data)
        
        self.outputs = {
            'market_data': market_data,
            'cross_sectional_data': self._calculate_cross_sectional_features(raw_data),
            'risk_metrics': self._calculate_risk_metrics(raw_data)
        }
        
        return self.outputs
    
    def _calculate_market_indicators(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """计算市场指标"""
        market_indicators = pd.DataFrame(index=raw_data.index)
        
        # 市场波动率（横截面）
        if 'close' in raw_data.columns:
            market_indicators['cross_sectional_vol'] = raw_data.groupby(level=0)['close'].std()
        
        # 市场收益率（等权平均）
        if 'returns' in raw_data.columns:
            market_indicators['market_return'] = raw_data.groupby(level=0)['returns'].mean()
        
        return market_indicators
    
    def _calculate_cross_sectional_features(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """计算横截面特征"""
        cross_sec_data = pd.DataFrame(index=raw_data.index)
        
        # 横截面标准化
        if 'close' in raw_data.columns:
            # 按日期标准化
            raw_data['zscore_close'] = raw_data.groupby(level=0)['close'].apply(
                lambda x: (x - x.mean()) / x.std()
            )
            cross_sec_data['zscore_close'] = raw_data['zscore_close']
        
        # 横截面排名
        if 'returns' in raw_data.columns:
            cross_sec_data['return_rank'] = raw_data.groupby(level=0)['returns'].rank(pct=True)
        
        return cross_sec_data
    
    def _calculate_risk_metrics(self, raw_data: pd.DataFrame) -> Dict[str, Any]:
        """计算风险指标"""
        risk_metrics = {}
        
        # 整体波动率
        if 'returns' in raw_data.columns:
            total_vol = raw_data['returns'].std()
            risk_metrics['total_volatility'] = float(total_vol)
        
        # 最大回撤
        if 'close' in raw_data.columns:
            cum_returns = raw_data['close'] / raw_data.groupby(level=1)['close'].first() - 1
            rolling_max = cum_returns.expanding().max()
            drawdown = (cum_returns - rolling_max) / rolling_max
            max_dd = float(drawdown.min()) if len(drawdown) > 0 else 0.0
            risk_metrics['max_drawdown'] = max_dd
        
        return risk_metrics