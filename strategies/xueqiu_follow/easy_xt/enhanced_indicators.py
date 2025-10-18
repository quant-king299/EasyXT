"""
增强技术指标模块
补充MACD、KDJ等常用技术指标
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, List
from .data_api import DataAPI


class EnhancedIndicators:
    """增强技术指标计算类"""
    
    def __init__(self, data_api: DataAPI):
        self.data_api = data_api
    
    def calculate_macd(self, code: str, fast_period: int = 12, slow_period: int = 26, 
                      signal_period: int = 9, data_period: str = '1d') -> Dict[str, float]:
        """
        计算MACD指标
        
        Args:
            code: 股票代码
            fast_period: 快线周期，默认12
            slow_period: 慢线周期，默认26
            signal_period: 信号线周期，默认9
            data_period: 数据周期
            
        Returns:
            Dict: 包含MACD、信号线、柱状图的字典
        """
        # 获取足够的历史数据
        required_periods = max(slow_period, signal_period) + 50
        data = self.data_api.get_price([code], period=data_period, count=required_periods)
        
        if data is None or len(data) < required_periods:
            return {}
        
        closes = data['close']
        
        # 计算EMA
        ema_fast = closes.ewm(span=fast_period).mean()
        ema_slow = closes.ewm(span=slow_period).mean()
        
        # 计算MACD线
        macd_line = ema_fast - ema_slow
        
        # 计算信号线（MACD的EMA）
        signal_line = macd_line.ewm(span=signal_period).mean()
        
        # 计算MACD柱状图
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line.iloc[-1],
            'signal': signal_line.iloc[-1],
            'histogram': histogram.iloc[-1],
            'macd_trend': 'up' if macd_line.iloc[-1] > macd_line.iloc[-2] else 'down',
            'signal_cross': self._check_macd_cross(macd_line.tail(3), signal_line.tail(3))
        }
    
    def calculate_kdj(self, code: str, k_period: int = 9, d_period: int = 3, 
                     j_period: int = 3, data_period: str = '1d') -> Dict[str, float]:
        """
        计算KDJ指标
        
        Args:
            code: 股票代码
            k_period: K值计算周期，默认9
            d_period: D值平滑周期，默认3
            j_period: J值计算周期，默认3
            data_period: 数据周期
            
        Returns:
            Dict: 包含K、D、J值的字典
        """
        # 获取足够的历史数据
        required_periods = k_period + max(d_period, j_period) + 20
        data = self.data_api.get_price([code], period=data_period, count=required_periods)
        
        if data is None or len(data) < required_periods:
            return {}
        
        highs = data['high']
        lows = data['low']
        closes = data['close']
        
        # 计算RSV (Raw Stochastic Value)
        lowest_low = lows.rolling(window=k_period).min()
        highest_high = highs.rolling(window=k_period).max()
        
        rsv = ((closes - lowest_low) / (highest_high - lowest_low)) * 100
        rsv = rsv.fillna(50)  # 填充NaN值
        
        # 计算K值（RSV的移动平均）
        k_values = []
        k_prev = 50  # 初始K值
        
        for rsv_val in rsv:
            if pd.isna(rsv_val):
                k_val = k_prev
            else:
                k_val = (2/3) * k_prev + (1/3) * rsv_val
            k_values.append(k_val)
            k_prev = k_val
        
        k_series = pd.Series(k_values, index=rsv.index)
        
        # 计算D值（K值的移动平均）
        d_values = []
        d_prev = 50  # 初始D值
        
        for k_val in k_series:
            d_val = (2/3) * d_prev + (1/3) * k_val
            d_values.append(d_val)
            d_prev = d_val
        
        d_series = pd.Series(d_values, index=k_series.index)
        
        # 计算J值
        j_series = 3 * k_series - 2 * d_series
        
        return {
            'k': k_series.iloc[-1],
            'd': d_series.iloc[-1],
            'j': j_series.iloc[-1],
            'k_trend': 'up' if k_series.iloc[-1] > k_series.iloc[-2] else 'down',
            'd_trend': 'up' if d_series.iloc[-1] > d_series.iloc[-2] else 'down',
            'signal': self._analyze_kdj_signal(k_series.iloc[-1], d_series.iloc[-1], j_series.iloc[-1])
        }
    
    def calculate_boll_enhanced(self, code: str, period: int = 20, std_dev: float = 2.0, 
                               data_period: str = '1d') -> Dict[str, float]:
        """
        增强版布林带计算
        
        Args:
            code: 股票代码
            period: 计算周期
            std_dev: 标准差倍数
            data_period: 数据周期
            
        Returns:
            Dict: 增强的布林带信息
        """
        data = self.data_api.get_price([code], period=data_period, count=period + 10)
        if data is None or len(data) < period:
            return {}
        
        closes = data['close'].tail(period + 5)
        
        # 计算布林带
        ma = closes.rolling(window=period).mean()
        std = closes.rolling(window=period).std()
        
        upper_band = ma + (std_dev * std)
        lower_band = ma - (std_dev * std)
        
        current_price = closes.iloc[-1]
        current_ma = ma.iloc[-1]
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        
        # 计算布林带宽度
        band_width = ((current_upper - current_lower) / current_ma) * 100
        
        # 计算%B指标
        percent_b = (current_price - current_lower) / (current_upper - current_lower)
        
        # 分析位置
        position = self._analyze_boll_position(current_price, current_upper, current_lower, current_ma)
        
        return {
            'upper_band': current_upper,
            'middle_band': current_ma,
            'lower_band': current_lower,
            'current_price': current_price,
            'band_width': band_width,
            'percent_b': percent_b,
            'position': position,
            'signal': self._analyze_boll_signal(percent_b, position)
        }
    
    def calculate_rsi_enhanced(self, code: str, period: int = 14, 
                              data_period: str = '1d') -> Dict[str, float]:
        """
        增强版RSI计算
        
        Args:
            code: 股票代码
            period: 计算周期
            data_period: 数据周期
            
        Returns:
            Dict: 增强的RSI信息
        """
        data = self.data_api.get_price([code], period=data_period, count=period + 20)
        if data is None or len(data) < period + 1:
            return {}
        
        closes = data['close']
        deltas = closes.diff()
        
        gains = deltas.where(deltas > 0, 0)
        losses = -deltas.where(deltas < 0, 0)
        
        # 使用EMA计算平均收益和损失
        avg_gain = gains.ewm(span=period).mean()
        avg_loss = losses.ewm(span=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]
        
        # 分析RSI信号
        signal = self._analyze_rsi_signal(current_rsi, prev_rsi)
        
        return {
            'rsi': current_rsi,
            'rsi_trend': 'up' if current_rsi > prev_rsi else 'down',
            'signal': signal,
            'overbought': current_rsi > 70,
            'oversold': current_rsi < 30,
            'divergence': self._check_rsi_divergence(closes.tail(10), rsi.tail(10))
        }
    
    def batch_calculate_indicators(self, codes: List[str], 
                                  indicators: List[str] = None) -> Dict[str, Dict]:
        """
        批量计算技术指标
        
        Args:
            codes: 股票代码列表
            indicators: 指标列表，默认计算所有指标
            
        Returns:
            Dict: 各股票的指标结果
        """
        if indicators is None:
            indicators = ['macd', 'kdj', 'rsi', 'boll']
        
        results = {}
        
        for code in codes:
            code_results = {}
            
            try:
                if 'macd' in indicators:
                    code_results['macd'] = self.calculate_macd(code)
                
                if 'kdj' in indicators:
                    code_results['kdj'] = self.calculate_kdj(code)
                
                if 'rsi' in indicators:
                    code_results['rsi'] = self.calculate_rsi_enhanced(code)
                
                if 'boll' in indicators:
                    code_results['boll'] = self.calculate_boll_enhanced(code)
                
                results[code] = code_results
                
            except Exception as e:
                results[code] = {'error': str(e)}
        
        return results
    
    def get_comprehensive_signal(self, code: str) -> Dict[str, str]:
        """
        获取综合技术信号
        
        Args:
            code: 股票代码
            
        Returns:
            Dict: 综合信号分析
        """
        try:
            macd = self.calculate_macd(code)
            kdj = self.calculate_kdj(code)
            rsi = self.calculate_rsi_enhanced(code)
            boll = self.calculate_boll_enhanced(code)
            
            signals = []
            
            # MACD信号
            if macd.get('signal_cross') == 'golden':
                signals.append('buy')
            elif macd.get('signal_cross') == 'death':
                signals.append('sell')
            
            # KDJ信号
            kdj_signal = kdj.get('signal', 'hold')
            if kdj_signal != 'hold':
                signals.append(kdj_signal)
            
            # RSI信号
            rsi_signal = rsi.get('signal', 'hold')
            if rsi_signal != 'hold':
                signals.append(rsi_signal)
            
            # 布林带信号
            boll_signal = boll.get('signal', 'hold')
            if boll_signal != 'hold':
                signals.append(boll_signal)
            
            # 综合判断
            buy_count = signals.count('buy')
            sell_count = signals.count('sell')
            
            if buy_count > sell_count and buy_count >= 2:
                final_signal = 'strong_buy' if buy_count >= 3 else 'buy'
            elif sell_count > buy_count and sell_count >= 2:
                final_signal = 'strong_sell' if sell_count >= 3 else 'sell'
            else:
                final_signal = 'hold'
            
            return {
                'final_signal': final_signal,
                'signal_strength': max(buy_count, sell_count),
                'individual_signals': {
                    'macd': macd.get('signal_cross', 'hold'),
                    'kdj': kdj_signal,
                    'rsi': rsi_signal,
                    'boll': boll_signal
                }
            }
            
        except Exception as e:
            return {'error': str(e), 'final_signal': 'hold'}
    
    # 辅助方法
    def _check_macd_cross(self, macd_line: pd.Series, signal_line: pd.Series) -> str:
        """检查MACD金叉死叉"""
        if len(macd_line) < 2 or len(signal_line) < 2:
            return 'hold'
        
        # 当前MACD > 信号线，前一期MACD < 信号线 -> 金叉
        if (macd_line.iloc[-1] > signal_line.iloc[-1] and 
            macd_line.iloc[-2] <= signal_line.iloc[-2]):
            return 'golden'
        
        # 当前MACD < 信号线，前一期MACD > 信号线 -> 死叉
        elif (macd_line.iloc[-1] < signal_line.iloc[-1] and 
              macd_line.iloc[-2] >= signal_line.iloc[-2]):
            return 'death'
        
        return 'hold'
    
    def _analyze_kdj_signal(self, k: float, d: float, j: float) -> str:
        """分析KDJ信号"""
        if k < 20 and d < 20 and j < 20:
            return 'buy'  # 超卖区域
        elif k > 80 and d > 80 and j > 80:
            return 'sell'  # 超买区域
        elif k > d and j > k:
            return 'buy'  # 金叉向上
        elif k < d and j < k:
            return 'sell'  # 死叉向下
        else:
            return 'hold'
    
    def _analyze_boll_position(self, price: float, upper: float, 
                              lower: float, middle: float) -> str:
        """分析布林带位置"""
        if price > upper:
            return 'above_upper'
        elif price < lower:
            return 'below_lower'
        elif price > middle:
            return 'upper_half'
        else:
            return 'lower_half'
    
    def _analyze_boll_signal(self, percent_b: float, position: str) -> str:
        """分析布林带信号"""
        if percent_b < 0:
            return 'buy'  # 价格低于下轨
        elif percent_b > 1:
            return 'sell'  # 价格高于上轨
        elif percent_b < 0.2 and position == 'lower_half':
            return 'buy'  # 接近下轨
        elif percent_b > 0.8 and position == 'upper_half':
            return 'sell'  # 接近上轨
        else:
            return 'hold'
    
    def _analyze_rsi_signal(self, current_rsi: float, prev_rsi: float) -> str:
        """分析RSI信号"""
        if current_rsi < 30:
            return 'buy'  # 超卖
        elif current_rsi > 70:
            return 'sell'  # 超买
        elif current_rsi > 50 and prev_rsi <= 50:
            return 'buy'  # 突破中线向上
        elif current_rsi < 50 and prev_rsi >= 50:
            return 'sell'  # 跌破中线向下
        else:
            return 'hold'
    
    def _check_rsi_divergence(self, prices: pd.Series, rsi: pd.Series) -> bool:
        """检查RSI背离"""
        if len(prices) < 5 or len(rsi) < 5:
            return False
        
        # 简化的背离检测
        price_trend = prices.iloc[-1] > prices.iloc[-3]
        rsi_trend = rsi.iloc[-1] > rsi.iloc[-3]
        
        return price_trend != rsi_trend