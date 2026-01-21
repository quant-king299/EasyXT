"""
WorldQuant 101 Alpha因子实现
基于已有的alpha101.py和alpha_factors.py整合实现
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import sys
import os

# 添加项目路径
project_path = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_path)

from src.factor_engine.operators import (
    ts_sum, sma, stddev, correlation, covariance,
    ts_rank, ts_min, ts_max, delta, delay, rank,
    scale, ts_argmax, ts_argmin, decay_linear,
    signedpower, product, returns, count
)


class Alpha101Factors:
    """
    WorldQuant 101 Alpha因子实现类
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        初始化因子计算器

        Args:
            data: 输入数据，索引为[date, symbol]，包含open, high, low, close, volume等字段
        """
        print(f"[DEBUG] Alpha101Factors.__init__ - 输入数据形状: {data.shape}")
        print(f"[DEBUG] Alpha101Factors.__init__ - 输入数据列: {list(data.columns)}")
        print(f"[DEBUG] Alpha101Factors.__init__ - 输入数据前3行:\n{data.head(3)}")

        # 检查并处理重复索引
        if isinstance(data.index, pd.MultiIndex):
            # 检查是否有重复的索引
            if data.index.duplicated().any():
                print(f"警告: 数据中发现重复索引，将进行去重处理")
                data = data[~data.index.duplicated(keep='first')]  # type: ignore

        self.data = data
        
        # 检查数据是否为MultiIndex格式
        if isinstance(data.index, pd.MultiIndex) and 'date' in data.index.names and 'symbol' in data.index.names:
            # MultiIndex格式：(date, symbol)
            # 将数据转换为传统的Date x Stock格式
            print(f"[DEBUG] 正在unstack数据...")
            self.open = data['open'].unstack(level='symbol') if 'open' in data.columns else data.iloc[:, 0].unstack(level='symbol')  # type: ignore
            self.high = data['high'].unstack(level='symbol') if 'high' in data.columns else data.iloc[:, 1].unstack(level='symbol')  # type: ignore
            self.low = data['low'].unstack(level='symbol') if 'low' in data.columns else data.iloc[:, 2].unstack(level='symbol')  # type: ignore
            self.close = data['close'].unstack(level='symbol') if 'close' in data.columns else data.iloc[:, 3].unstack(level='symbol')  # type: ignore
            self.volume = data['volume'].unstack(level='symbol') if 'volume' in data.columns else data.iloc[:, 4].unstack(level='symbol')  # type: ignore
            print(f"[DEBUG] unstack后 - close形状: {self.close.shape}, close前3个值:\n{self.close.iloc[:3, :3]}")
            
            # 如果没有vwap字段，则计算
            if 'vwap' in data.columns:
                self.vwap = data['vwap'].unstack(level='symbol')  # type: ignore
            else:
                # 简化计算vwap为OHLC的平均值
                self.vwap = (self.open + self.high + self.low + self.close) / 4  # type: ignore
                
            # 如果没有returns字段，则计算
            if 'returns' in data.columns:
                self.returns = data['returns'].unstack(level='symbol')  # type: ignore
            else:
                # 按股票分组计算收益率
                returns_data = data.groupby(level=1)['close'].pct_change()
                # 同样处理重复索引
                if returns_data.index.duplicated().any():
                    returns_data = returns_data[~returns_data.index.duplicated(keep='first')]  # type: ignore
                self.returns = returns_data.unstack(level='symbol')  # type: ignore
        else:
            # 传统格式：Date x Stock
            self.open = data['open'] if 'open' in data.columns else data.iloc[:, 0]  # type: ignore
            self.high = data['high'] if 'high' in data.columns else data.iloc[:, 1]  # type: ignore
            self.low = data['low'] if 'low' in data.columns else data.iloc[:, 2]  # type: ignore
            self.close = data['close'] if 'close' in data.columns else data.iloc[:, 3]  # type: ignore
            self.volume = data['volume'] if 'volume' in data.columns else data.iloc[:, 4]  # type: ignore
            
            # 如果没有vwap字段，则计算
            if 'vwap' in data.columns:
                self.vwap = data['vwap']  # type: ignore
            else:
                # 简化计算vwap为OHLC的平均值
                self.vwap = (self.open + self.high + self.low + self.close) / 4  # type: ignore
                
            # 如果没有returns字段，则计算
            if 'returns' in data.columns:
                self.returns = data['returns']  # type: ignore
            else:
                # 按股票分组计算收益率
                self.returns = data.groupby(level=1)['close'].pct_change()  # type: ignore
        
        # 确保所有数据都是数值型，处理NaN
        for attr_name in ['open', 'high', 'low', 'close', 'volume', 'vwap', 'returns']:
            if hasattr(self, attr_name):
                attr_value = getattr(self, attr_name)
                if isinstance(attr_value, pd.DataFrame):
                    setattr(self, attr_name, attr_value.fillna(0))
                elif isinstance(attr_value, pd.Series):
                    setattr(self, attr_name, attr_value.fillna(0))
                    
        # 验证数据完整性，确保列名是完整的股票代码而不是单个字符
        for attr_name in ['open', 'high', 'low', 'close', 'volume', 'vwap', 'returns']:
            if hasattr(self, attr_name):
                attr_value = getattr(self, attr_name)
                if isinstance(attr_value, pd.DataFrame):
                    # 检查列名是否是完整的股票代码
                    columns = attr_value.columns
                    # 如果列名包含单个字符，这可能是问题所在
                    if any(len(str(col)) == 1 for col in columns if pd.notna(col)):
                        print(f"警告: {attr_name} 的列名包含单个字符: {columns}")
    
    def alpha001(self) -> pd.DataFrame:
        """(rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5)) -0.5)"""
        print(f"[DEBUG] alpha001 - close形状: {self.close.shape}, close前3个值:\n{self.close.iloc[:3, :3]}")
        print(f"[DEBUG] alpha001 - returns形状: {self.returns.shape}, returns前3个值:\n{self.returns.iloc[:3, :3]}")

        inner = self.close.copy()
        negative_returns = self.returns < 0
        print(f"[DEBUG] alpha001 - negative_returns数量: {negative_returns.sum().sum()}")

        inner[negative_returns] = stddev(self.returns, 20)[negative_returns]
        result = rank(ts_argmax(signedpower(inner ** 2, 1), 5)) - 0.5

        print(f"[DEBUG] alpha001 - 结果形状: {result.shape}")
        print(f"[DEBUG] alpha001 - 结果前3个值:\n{result.iloc[:3, :3]}")
        print(f"[DEBUG] alpha001 - 结果统计: min={result.min().min():.4f}, max={result.max().max():.4f}, mean={result.mean().mean():.4f}")

        return result
    
    def alpha002(self) -> pd.DataFrame:
        """(-1 * correlation(rank(delta(log(volume), 2)), rank(((close - open) / open)), 6))"""
        from numpy import log
        df = -1 * correlation(
            rank(delta(log(self.volume), 2)), 
            rank(((self.close - self.open) / self.open)), 
            6
        )
        return df.replace([-np.inf, np.inf], 0).fillna(value=0)
    
    def alpha003(self) -> pd.DataFrame:
        """(-1 * correlation(rank(open), rank(volume), 10))"""
        df = -1 * correlation(rank(self.open), rank(self.volume), 10)
        return df.replace([-np.inf, np.inf], 0).fillna(value=0)
    
    def alpha004(self) -> pd.DataFrame:
        """(-1 * Ts_Rank(rank(low), 9))"""
        return -1 * ts_rank(rank(self.low), 9)
    
    def alpha005(self) -> pd.DataFrame:
        """(rank((open - (sum(vwap, 10) / 10))) * (-1 * abs(rank((close - vwap)))))"""
        return (rank((self.open - (ts_sum(self.vwap, 10) / 10))) * 
                (-1 * np.abs(rank((self.close - self.vwap)))))
    
    def alpha006(self) -> pd.DataFrame:
        """(-1 * correlation(open, volume, 10))"""
        df = -1 * correlation(self.open, self.volume, 10)
        return df.replace([-np.inf, np.inf], 0).fillna(value=0)
    
    def alpha007(self) -> pd.DataFrame:
        """((adv20 < volume) ? ((-1 * ts_rank(abs(delta(close, 7)), 60)) * sign(delta(close, 7))) : (-1* 1))"""
        from numpy import sign
        adv20 = sma(self.volume, 20)
        alpha = -1 * ts_rank(np.abs(delta(self.close, 7)), 60) * sign(delta(self.close, 7))
        alpha[adv20 >= self.volume] = -1
        return alpha
    
    def alpha008(self) -> pd.DataFrame:
        """(-1 * rank(((sum(open, 5) * sum(returns, 5)) - delay((sum(open, 5) * sum(returns, 5)),10))))"""
        sum_open_5 = ts_sum(self.open, 5)
        sum_returns_5 = ts_sum(self.returns, 5)
        combined = sum_open_5 * sum_returns_5
        return -1 * rank(((combined - delay(combined, 10))))
    
    def alpha009(self) -> pd.DataFrame:
        """((0 < ts_min(delta(close, 1), 5)) ? delta(close, 1) : ((ts_max(delta(close, 1), 5) < 0) ?delta(close, 1) : (-1 * delta(close, 1))))"""
        delta_close = delta(self.close, 1)
        cond_1 = ts_min(delta_close, 5) > 0
        cond_2 = ts_max(delta_close, 5) < 0
        alpha = -1 * delta_close
        alpha[cond_1 | cond_2] = delta_close
        return alpha
    
    def alpha010(self) -> pd.DataFrame:
        """rank(((0 < ts_min(delta(close, 1), 4)) ? delta(close, 1) : ((ts_max(delta(close, 1), 4) < 0)? delta(close, 1) : (-1 * delta(close, 1)))))"""
        delta_close = delta(self.close, 1)
        cond_1 = ts_min(delta_close, 4) > 0
        cond_2 = ts_max(delta_close, 4) < 0
        alpha = -1 * delta_close
        alpha[cond_1 | cond_2] = delta_close
        return rank(alpha)
    
    def alpha011(self) -> pd.DataFrame:
        """((rank(ts_max((vwap - close), 3)) + rank(ts_min((vwap - close), 3))) *rank(delta(volume, 3)))"""
        return ((rank(ts_max((self.vwap - self.close), 3)) + rank(ts_min((self.vwap - self.close), 3))) * 
                rank(delta(self.volume, 3)))
    
    def alpha012(self) -> pd.DataFrame:
        """(sign(delta(volume, 1)) * (-1 * delta(close, 1)))"""
        from numpy import sign
        return sign(delta(self.volume, 1)) * (-1 * delta(self.close, 1))

    def alpha013(self) -> pd.DataFrame:
        """(-1 * rank(covariance(rank(close), rank(volume), 5)))"""
        return -1 * rank(covariance(rank(self.close), rank(self.volume), 5))
    
    def alpha014(self) -> pd.DataFrame:
        """((-1 * rank(delta(returns, 3))) * correlation(open, volume, 10))"""
        df = correlation(self.open, self.volume, 10)
        df = df.replace([-np.inf, np.inf], 0).fillna(value=0)
        return -1 * rank(delta(self.returns, 3)) * df
    
    def alpha015(self) -> pd.DataFrame:
        """(-1 * sum(rank(correlation(rank(high), rank(volume), 3)), 3))"""
        df = correlation(rank(self.high), rank(self.volume), 3)
        df = df.replace([-np.inf, np.inf], 0).fillna(value=0)
        return -1 * ts_sum(rank(df), 3)
    
    def alpha016(self) -> pd.DataFrame:
        """(-1 * rank(covariance(rank(high), rank(volume), 5)))"""
        return -1 * rank(covariance(rank(self.high), rank(self.volume), 5))
    
    def alpha017(self) -> pd.DataFrame:
        """(((-1 * rank(ts_rank(close, 10))) * rank(delta(delta(close, 1), 1))) *rank(ts_rank((volume / adv20), 5)))"""
        adv20 = sma(self.volume, 20)
        return -1 * (rank(ts_rank(self.close, 10)) *
                     rank(delta(delta(self.close, 1), 1)) *
                     rank(ts_rank((self.volume / adv20), 5)))
        
    def alpha018(self) -> pd.DataFrame:
        """(-1 * rank(((stddev(abs((close - open)), 5) + (close - open)) + correlation(close, open,10))))"""
        df = correlation(self.close, self.open, 10)
        df = df.replace([-np.inf, np.inf], 0).fillna(value=0)
        return -1 * (rank((stddev(np.abs((self.close - self.open)), 5) + (self.close - self.open)) +
                          df))
    
    def alpha019(self) -> pd.DataFrame:
        """((-1 * sign(((close - delay(close, 7)) + delta(close, 7)))) * (1 + rank((1 + sum(returns,250)))))"""
        from numpy import sign
        return ((-1 * sign((self.close - delay(self.close, 7)) + delta(self.close, 7))) *
                (1 + rank(1 + ts_sum(self.returns, 250))))
    
    def alpha020(self) -> pd.DataFrame:
        """(((-1 * rank((open - delay(high, 1)))) * rank((open - delay(close, 1)))) * rank((open -delay(low, 1))))"""
        return -1 * (rank(self.open - delay(self.high, 1)) *
                     rank(self.open - delay(self.close, 1)) *
                     rank(self.open - delay(self.low, 1)))
    
    def alpha021(self) -> pd.DataFrame:
        """((((sum(close, 8) / 8) + stddev(close, 8)) < (sum(close, 2) / 2)) ? (-1 * 1) : (((sum(close,2) / 2) < ((sum(close, 8) / 8) - stddev(close, 8))) ? 1 : (((1 < (volume / adv20)) || ((volume /adv20) == 1)) ? 1 : (-1 * 1))))"""
        ma8_close = sma(self.close, 8)
        std8_close = stddev(self.close, 8)
        ma2_close = sma(self.close, 2)
        adv20 = sma(self.volume, 20)
        
        cond_1 = (ma8_close + std8_close) < ma2_close
        cond_2 = ma2_close < (ma8_close - std8_close)
        cond_3 = (adv20 / self.volume) <= 1

        result = pd.DataFrame(np.ones_like(self.close), index=self.close.index, columns=self.close.columns)
        result[cond_1] = -1
        result[~cond_1 & ~cond_2 & ~cond_3] = -1
        return result
    
    def alpha022(self) -> pd.DataFrame:
        """(-1 * (delta(correlation(high, volume, 5), 5) * rank(stddev(close, 20))))"""
        df = correlation(self.high, self.volume, 5)
        df = df.replace([-np.inf, np.inf], 0).fillna(value=0)
        return -1 * delta(df, 5) * rank(stddev(self.close, 20))

    def alpha023(self) -> pd.DataFrame:
        """(((sum(high, 20) / 20) < high) ? (-1 * delta(high, 2)) : 0)"""
        ma20_high = sma(self.high, 20)
        cond = ma20_high < self.high
        alpha = pd.DataFrame(np.zeros_like(self.close), index=self.close.index, columns=self.close.columns)
        alpha[cond] = -1 * delta(self.high, 2)
        return alpha
    
    def alpha024(self) -> pd.DataFrame:
        """((((delta((sum(close, 100) / 100), 100) / delay(close, 100)) < 0.05) ||((delta((sum(close, 100) / 100), 100) / delay(close, 100)) == 0.05)) ? (-1 * (close - ts_min(close,100))) : (-1 * delta(close, 3)))"""
        sma100_close = sma(self.close, 100)
        delta_sma100 = delta(sma100_close, 100)
        delay_close_100 = delay(self.close, 100)
        
        ratio = delta_sma100 / delay_close_100
        cond = ratio <= 0.05
        alpha = -1 * delta(self.close, 3)
        alpha[cond] = -1 * (self.close - ts_min(self.close, 100))
        return alpha
    
    def alpha025(self) -> pd.DataFrame:
        """rank(((((-1 * returns) * adv20) * vwap) * (high - close)))"""
        adv20 = sma(self.volume, 20)
        return rank(((((-1 * self.returns) * adv20) * self.vwap) * (self.high - self.close)))
    
    def alpha026(self) -> pd.DataFrame:
        """(-1 * ts_max(correlation(ts_rank(volume, 5), ts_rank(high, 5), 5), 3))"""
        df = correlation(ts_rank(self.volume, 5), ts_rank(self.high, 5), 5)
        df = df.replace([-np.inf, np.inf], 0).fillna(value=0)
        return -1 * ts_max(df, 3)
    
    def alpha027(self) -> pd.DataFrame:
        """((0.5 < rank((sum(correlation(rank(volume), rank(vwap), 6), 2) / 2.0))) ? (-1 * 1) : 1)"""
        from numpy import sign
        alpha = rank((sma(correlation(rank(self.volume), rank(self.vwap), 6), 2) / 2.0))
        return sign((alpha - 0.5) * (-2)).fillna(1)
    
    def alpha028(self) -> pd.DataFrame:
        """scale(((correlation(adv20, low, 5) + ((high + low) / 2)) - close))"""
        adv20 = sma(self.volume, 20)
        df = correlation(adv20, self.low, 5)
        df = df.replace([-np.inf, np.inf], 0).fillna(value=0)
        return scale(((df + ((self.high + self.low) / 2)) - self.close))

    def alpha029(self) -> pd.DataFrame:
        """(min(product(rank(rank(scale(log(sum(ts_min(rank(rank((-1 * rank(delta((close - 1),5))))), 2), 1))))), 1), 5) + ts_rank(delay((-1 * returns), 6), 5))"""
        from numpy import log
        inner_expr = -1 * rank(delta((self.close - 1), 5))
        min_inner = ts_min(rank(rank(inner_expr)), 2)
        log_expr = log(min_inner)
        sum_log = ts_sum(log_expr, 1)
        scaled_expr = scale(sum_log)
        ranked_expr = rank(rank(scaled_expr))
        product_expr = product(ranked_expr, 1)
        min_expr = ts_min(product_expr, 1)
        return min_expr + ts_rank(delay((-1 * self.returns), 6), 5)

    def alpha030(self) -> pd.DataFrame:
        """(((1.0 - rank(((sign((close - delay(close, 1))) + sign((delay(close, 1) - delay(close, 2)))) +sign((delay(close, 2) - delay(close, 3)))))) * sum(volume, 5)) / sum(volume, 20))"""
        from numpy import sign
        delta_close = delta(self.close, 1)
        delay_delta1 = delay(delta_close, 1)
        delay_delta2 = delay(delta_close, 2)
        inner = sign(delta_close) + sign(delay_delta1) + sign(delay_delta2)
        return ((1.0 - rank(inner)) * ts_sum(self.volume, 5)) / ts_sum(self.volume, 20)


    # Alpha#31
    def alpha031(self) -> pd.DataFrame:
        """((rank(rank(rank(decay_linear((-1 * rank(rank(delta(close, 10)))), 10)))) + rank((-1 *delta(close, 3)))) + sign(scale(correlation(adv20, low, 12))))"""
        adv20 = sma(self.volume, 20)
        df = correlation(adv20, self.low, 12).replace([-np.inf, np.inf], 0).fillna(value=0)
        p1 = rank(rank(rank(decay_linear((-1 * rank(rank(delta(self.close, 10)))), 10))))
        p2 = rank((-1 * delta(self.close, 3)))
        p3 = sign(scale(df))
        return p1 + p2 + p3

    # Alpha#32
    def alpha032(self) -> pd.DataFrame:
        """(scale(((sum(close, 7) / 7) - close)) + (20 * scale(correlation(vwap, delay(close, 5),230))))"""
        return scale(((sma(self.close, 7) / 7) - self.close)) + (20 * scale(correlation(self.vwap, delay(self.close, 5), 230)))

    # Alpha#33
    def alpha033(self) -> pd.DataFrame:
        """rank((-1 * ((1 - (open / close))^1)))"""
        return rank(-1 + (self.open / self.close))

    # Alpha#34
    def alpha034(self) -> pd.DataFrame:
        """rank(((1 - rank((stddev(returns, 2) / stddev(returns, 5)))) + (1 - rank(delta(close, 1)))))"""
        inner = stddev(self.returns, 2) / stddev(self.returns, 5)
        inner = inner.replace([-np.inf, np.inf], 1).fillna(value=1)
        return rank(2 - rank(inner) - rank(delta(self.close, 1)))

    # Alpha#35
    def alpha035(self) -> pd.DataFrame:
        """((Ts_Rank(volume, 32) * (1 - Ts_Rank(((close + high) - low), 16))) * (1 -Ts_Rank(returns, 32)))"""
        return ((ts_rank(self.volume, 32) *
                 (1 - ts_rank(self.close + self.high - self.low, 16))) *
                (1 - ts_rank(self.returns, 32)))

    # Alpha#36
    def alpha036(self) -> pd.DataFrame:
        """(((((2.21 * rank(correlation((close - open), delay(volume, 1), 15))) + (0.7 * rank((open- close)))) + (0.73 * rank(Ts_Rank(delay((-1 * returns), 6), 5)))) + rank(abs(correlation(vwap,adv20, 6)))) + (0.6 * rank((((sum(close, 200) / 200) - open) * (close - open)))))"""
        adv20 = sma(self.volume, 20)
        return (((((2.21 * rank(correlation((self.close - self.open), delay(self.volume, 1), 15))) + (0.7 * rank((self.open- self.close)))) + (0.73 * rank(ts_rank(delay((-1 * self.returns), 6), 5)))) + rank(abs(correlation(self.vwap,adv20, 6)))) + (0.6 * rank((((sma(self.close, 200) / 200) - self.open) * (self.close - self.open)))))

    # Alpha#37
    def alpha037(self) -> pd.DataFrame:
        """(rank(correlation(delay((open - close), 1), close, 200)) + rank((open - close)))"""
        return rank(correlation(delay(self.open - self.close, 1), self.close, 200)) + rank(self.open - self.close)

    # Alpha#38
    def alpha038(self) -> pd.DataFrame:
        """((-1 * rank(Ts_Rank(close, 10))) * rank((close / open)))"""
        inner = self.close / self.open
        inner = inner.replace([-np.inf, np.inf], 1).fillna(value=1)
        return -1 * rank(ts_rank(self.open, 10)) * rank(inner)

    # Alpha#39
    def alpha039(self) -> pd.DataFrame:
        """((-1 * rank((delta(close, 7) * (1 - rank(decay_linear((volume / adv20), 9)))))) * (1 +rank(sum(returns, 250))))"""
        adv20 = sma(self.volume, 20)
        return ((-1 * rank(delta(self.close, 7) * (1 - rank(decay_linear((self.volume / adv20), 9))))) *
                (1 + rank(sma(self.returns, 250))))

    # Alpha#40
    def alpha040(self) -> pd.DataFrame:
        """((-1 * rank(stddev(high, 10))) * correlation(high, volume, 10))"""
        return -1 * rank(stddev(self.high, 10)) * correlation(self.high, self.volume, 10)

    # Alpha#41
    def alpha041(self) -> pd.DataFrame:
        """(((high * low)^0.5) - vwap)"""
        return pow((self.high * self.low), 0.5) - self.vwap

    # Alpha#42
    def alpha042(self) -> pd.DataFrame:
        """(rank((vwap - close)) / rank((vwap + close)))"""
        return rank((self.vwap - self.close)) / rank((self.vwap + self.close))

    # Alpha#43
    def alpha043(self) -> pd.DataFrame:
        """(ts_rank((volume / adv20), 20) * ts_rank((-1 * delta(close, 7)), 8))"""
        adv20 = sma(self.volume, 20)
        return ts_rank(self.volume / adv20, 20) * ts_rank((-1 * delta(self.close, 7)), 8)

    # Alpha#44
    def alpha044(self) -> pd.DataFrame:
        """(-1 * correlation(high, rank(volume), 5))"""
        df = correlation(self.high, rank(self.volume), 5)
        df = df.replace([-np.inf, np.inf], 0).fillna(value=0)
        return -1 * df

    # Alpha#45
    def alpha045(self) -> pd.DataFrame:
        """(-1 * ((rank((sum(delay(close, 5), 20) / 20)) * correlation(close, volume, 2)) *rank(correlation(sum(close, 5), sum(close, 20), 2))))"""
        df = correlation(self.close, self.volume, 2)
        df = df.replace([-np.inf, np.inf], 0).fillna(value=0)
        return -1 * (rank(sma(delay(self.close, 5), 20)) * df *
                     rank(correlation(ts_sum(self.close, 5), ts_sum(self.close, 20), 2)))

    # Alpha#46
    def alpha046(self) -> pd.DataFrame:
        """((0.25 < (((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10))) ?(-1 * 1) : (((((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10)) < 0) ? 1 :((-1 * 1) * (close - delay(close, 1)))))"""
        inner = ((delay(self.close, 20) - delay(self.close, 10)) / 10) - ((delay(self.close, 10) - self.close) / 10)
        alpha = (-1 * delta(self.close))
        alpha[inner < 0] = 1
        alpha[inner > 0.25] = -1
        return alpha

    # Alpha#47
    def alpha047(self) -> pd.DataFrame:
        """((((rank((1 / close)) * volume) / adv20) * ((high * rank((high - close))) / (sum(high, 5) /5))) - rank((vwap - delay(vwap, 5))))"""
        adv20 = sma(self.volume, 20)
        return ((((rank((1 / self.close)) * self.volume) / adv20) * ((self.high * rank((self.high - self.close))) / (sma(self.high, 5) /5))) - rank((self.vwap - delay(self.vwap, 5))))

    # Alpha#048
    def alpha048(self) -> pd.DataFrame:
        """(-1*((RANK(((SIGN((CLOSE - DELAY(CLOSE, 1))) + SIGN((DELAY(CLOSE, 1) - DELAY(CLOSE, 2)))) + SIGN((DELAY(CLOSE, 2) - DELAY(CLOSE, 3)))))) * SUM(VOLUME, 5)) / SUM(VOLUME, 20))"""
        from numpy import sign
        inner = (sign((self.close - delay(self.close, 1))) +
                 sign((delay(self.close, 1) - delay(self.close, 2))) +
                 sign((delay(self.close, 2) - delay(self.close, 3))))
        return (-1 * (rank(inner) * ts_sum(self.volume, 5))) / ts_sum(self.volume, 20)

    # Alpha#49
    def alpha049(self) -> pd.DataFrame:
        """(((((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10)) < (-1 *0.1)) ? 1 : ((-1 * 1) * (close - delay(close, 1))))"""
        inner = (((delay(self.close, 20) - delay(self.close, 10)) / 10) - ((delay(self.close, 10) - self.close) / 10))
        alpha = (-1 * delta(self.close))
        alpha[inner < -0.1] = 1
        return alpha

    # Alpha#50
    def alpha050(self) -> pd.DataFrame:
        """(-1 * ts_max(rank(correlation(rank(volume), rank(vwap), 5)), 5))"""
        return (-1 * ts_max(rank(correlation(rank(self.volume), rank(self.vwap), 5)), 5))

    # Alpha#51
    def alpha051(self) -> pd.DataFrame:
        """(((((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10)) < (-1 *0.05)) ? 1 : ((-1 * 1) * (close - delay(close, 1))))"""
        inner = (((delay(self.close, 20) - delay(self.close, 10)) / 10) - ((delay(self.close, 10) - self.close) / 10))
        alpha = (-1 * delta(self.close))
        alpha[inner < -0.05] = 1
        return alpha

    # Alpha#52
    def alpha052(self) -> pd.DataFrame:
        """((((-1 * ts_min(low, 5)) + delay(ts_min(low, 5), 5)) * rank(((sum(returns, 240) -sum(returns, 20)) / 220))) * ts_rank(volume, 5))"""
        return (((-1 * delta(ts_min(self.low, 5), 5)) *
                 rank(((ts_sum(self.returns, 240) - ts_sum(self.returns, 20)) / 220))) * ts_rank(self.volume, 5))

    # Alpha#53
    def alpha053(self) -> pd.DataFrame:
        """(-1 * delta((((close - low) - (high - close)) / (close - low)), 9))"""
        inner = (self.close - self.low).replace(0, 0.0001)
        return -1 * delta((((self.close - self.low) - (self.high - self.close)) / inner), 9)

    # Alpha#54
    def alpha054(self) -> pd.DataFrame:
        """((-1 * ((low - close) * (open^5))) / ((low - high) * (close^5)))"""
        inner = (self.low - self.high).replace(0, -0.0001)
        return -1 * (self.low - self.close) * (self.open ** 5) / (inner * (self.close ** 5))

    # Alpha#55
    def alpha055(self) -> pd.DataFrame:
        """(-1 * correlation(rank(((close - ts_min(low, 12)) / (ts_max(high, 12) - ts_min(low,12)))), rank(volume), 6))"""
        divisor = (ts_max(self.high, 12) - ts_min(self.low, 12)).replace(0, 0.0001)
        inner = (self.close - ts_min(self.low, 12)) / (divisor)
        df = correlation(rank(inner), rank(self.volume), 6)
        return -1 * df.replace([-np.inf, np.inf], 0).fillna(value=0)

    # Alpha#056
    def alpha056(self) -> pd.DataFrame:
        """(RANK((OPEN - TSMIN(OPEN, 12))) < RANK((RANK(CORR(SUM(((HIGH + LOW) / 2), 19),SUM(MEAN(VOLUME,40), 19), 13))^5)))"""
        A = rank((self.open - ts_min(self.open, 12)))
        B = rank((rank(correlation(ts_sum(((self.high + self.low) / 2), 19),ts_sum(sma(self.volume,40), 19), 13))**5))
        cond = (A < B)
        part = self.close.copy()
        part.loc[:, :] = np.nan
        part[cond] = 1
        part[~cond] = 0
        return part

    # Alpha#57
    def alpha057(self) -> pd.DataFrame:
        """(0 - (1 * ((close - vwap) / decay_linear(rank(ts_argmax(close, 30)), 2))))"""
        return (0 - (1 * ((self.close - self.vwap) / decay_linear(rank(ts_argmax(self.close, 30)), 2))))

    # Alpha#058
    def alpha058(self) -> pd.DataFrame:
        """COUNT(CLOSE>DELAY(CLOSE,1),20)/20*100"""
        cond = (self.close > delay(self.close,1))
        return count(cond,20)/20*100

    # Alpha#059
    def alpha059(self) -> pd.DataFrame:
        """SUM((CLOSE=DELAY(CLOSE,1)?0:CLOSE-(CLOSE>DELAY(CLOSE,1)?MIN(LOW,DELAY(CLOSE,1)):MAX(HIGH,DELAY(CLOSE,1)))),20)"""
        cond1 = (self.close == delay(self.close,1))
        cond2 = (self.close > delay(self.close,1))
        cond3 = (self.close < delay(self.close,1))
        part = self.close.copy()
        part.loc[:, :] = np.nan
        part[cond1] = 0
        part[cond2] = self.close - np.minimum(self.low,delay(self.close,1))
        part[cond3] = self.close - np.maximum(self.high,delay(self.close,1))
        return ts_sum(part, 20)

    # Alpha#60
    def alpha060(self) -> pd.DataFrame:
        """(0 - (1 * ((2 * scale(rank(((((close - low) - (high - close)) / (high - low)) * volume)))) -scale(rank(ts_argmax(close, 10)))))"""
        divisor = (self.high - self.low).replace(0, 0.0001)
        inner = ((self.close - self.low) - (self.high - self.close)) * self.volume / divisor
        return - ((2 * scale(rank(inner))) - scale(rank(ts_argmax(self.close, 10))))

    # Alpha#61
    def alpha061(self) -> pd.DataFrame:
        """(rank((vwap - ts_min(vwap, 16.1219))) < rank(correlation(vwap, adv180, 17.9282)))"""
        adv180 = sma(self.volume, 180)
        return (rank((self.vwap - ts_min(self.vwap, 16))) < rank(correlation(self.vwap, adv180, 18))).astype('int')

    # Alpha#62
    def alpha062(self) -> pd.DataFrame:
        """((rank(correlation(vwap, sum(adv20, 22.4101), 9.91009)) < rank(((rank(open) +rank(open)) < (rank(((high + low) / 2)) + rank(high))))) * -1)"""
        adv20 = sma(self.volume, 20)
        return ((rank(correlation(self.vwap, sma(adv20, 22), 10)) < rank(((rank(self.open) +rank(self.open)) < (rank(((self.high + self.low) / 2)) + rank(self.high))))) * -1)

    # Alpha#063
    def alpha063(self) -> pd.DataFrame:
        """SMA(MAX(CLOSE-DELAY(CLOSE,1),0),6,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),6,1)*100"""
        return sma(np.maximum(self.close-delay(self.close,1),0),6,1)/sma(np.abs(self.close-delay(self.close,1)),6,1)*100

    # Alpha#64
    def alpha064(self) -> pd.DataFrame:
        """((rank(correlation(sum(((open * 0.178404) + (low * (1 - 0.178404))), 12.7054),sum(adv120, 12.7054), 16.6208)) < rank(delta(((((high + low) / 2) * 0.178404) + (vwap * (1 -0.178404))), 3.69741))) * -1)"""
        adv120 = sma(self.volume, 120)
        return ((rank(correlation(sma(((self.open * 0.178404) + (self.low * (1 - 0.178404))), 13),sma(adv120, 13), 17)) < rank(delta(((((self.high + self.low) / 2) * 0.178404) + (self.vwap * (1 -0.178404))), 4))) * -1)

    # Alpha#65
    def alpha065(self) -> pd.DataFrame:
        """((rank(correlation(((open * 0.00817205) + (vwap * (1 - 0.00817205))), sum(adv60,8.6911), 6.40374)) < rank((open - ts_min(open, 13.635)))) * -1)"""
        adv60 = sma(self.volume, 60)
        return ((rank(correlation(((self.open * 0.00817205) + (self.vwap * (1 - 0.00817205))), sma(adv60,9), 6)) < rank((self.open - ts_min(self.open, 14)))) * -1)

    # Alpha#066
    def alpha066(self) -> pd.DataFrame:
        """((rank(decay_linear(delta(vwap, 3.51013), 7.23052)) + Ts_Rank(decay_linear(((((low* 0.96633) + (low * (1 - 0.96633))) - vwap) / (open - ((high + low) / 2))), 11.4157), 6.72611)) * -1)"""
        return ((rank(decay_linear(delta(self.vwap, 4), 7)) + ts_rank(decay_linear(((((self.low* 0.96633) + (self.low * (1 - 0.96633))) - self.vwap) / (self.open - ((self.high + self.low) / 2))), 11), 7)) * -1)

    # Alpha#067
    def alpha067(self) -> pd.DataFrame:
        """SMA(MAX(CLOSE-DELAY(CLOSE,1),0),24,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),24,1)*100"""
        a1 = sma(np.maximum(self.close-delay(self.close,1),0),24,1)
        a2 = sma(np.abs(self.close-delay(self.close,1)),24,1)
        return a1/a2*100

    # Alpha#068
    def alpha068(self) -> pd.DataFrame:
        """SMA(((HIGH+LOW)/2-(DELAY(HIGH,1)+DELAY(LOW,1))/2)*(HIGH-LOW)/VOLUME,15,2)"""
        return sma(((self.high+self.low)/2-(delay(self.high,1)+delay(self.low,1))/2)*(self.high-self.low)/self.volume,15,2)

    # Alpha#069
    def alpha069(self) -> pd.DataFrame:
        """(SUM(DTM,20)>SUM(DBM,20)？ (SUM(DTM,20)-SUM(DBM,20))/SUM(DTM,20)： (SUM(DTM,20)=SUM(DBM,20)？0： (SUM(DTM,20)-SUM(DBM,20))/SUM(DBM,20)))"""
        # DTM (OPEN<=DELAY(OPEN,1)?0:MAX((HIGH-OPEN),(OPEN-DELAY(OPEN,1))))
        # DBM (OPEN>=DELAY(OPEN,1)?0:MAX((OPEN-LOW),(OPEN-DELAY(OPEN,1))))
        cond1 = (self.open <= delay(self.open,1))
        cond2 = (self.open >= delay(self.open,1))

        DTM = self.close.copy()
        DTM.loc[:, :] = np.nan
        DTM[cond1] = 0
        DTM[~cond1] = np.maximum((self.high-self.open),(self.open-delay(self.open,1)))

        DBM = self.close.copy()
        DBM.loc[:, :] = np.nan
        DBM[cond2] = 0
        DBM[~cond2] = np.maximum((self.open-self.low),(self.open-delay(self.open,1)))

        cond3 = (ts_sum(DTM,20) > ts_sum(DBM,20))
        cond4 = (ts_sum(DTM,20)== ts_sum(DBM,20))
        cond5 = (ts_sum(DTM,20) < ts_sum(DBM,20))
        part = self.close.copy()
        part.loc[:, :] = np.nan
        part[cond3] = (ts_sum(DTM,20)-ts_sum(DBM,20))/ts_sum(DTM,20)
        part[cond4] = 0
        part[cond5] = (ts_sum(DTM,20)-ts_sum(DBM,20))/ts_sum(DBM,20)
        return part

    # Alpha#070
    def alpha070(self) -> pd.DataFrame:
        """STD(AMOUNT,6)"""
        if hasattr(self, 'amount'):
            return stddev(self.amount,6)
        else:
            # 如果没有amount字段，使用volume代替
            return stddev(self.volume,6)

    # Alpha#71
    def alpha071(self) -> pd.DataFrame:
        """max(Ts_Rank(decay_linear(correlation(Ts_Rank(close, 3.43976), Ts_Rank(adv180,12.0647), 18.0175), 4.20501), 15.6948), Ts_Rank(decay_linear((rank(((low + open) - (vwap +vwap)))^2), 16.4662), 4.4388))"""
        adv180 = sma(self.volume, 180)
        p1 = ts_rank(decay_linear(correlation(ts_rank(self.close, 3), ts_rank(adv180,12), 18), 4), 16)
        p2 = ts_rank(decay_linear((rank(((self.low + self.open) - (self.vwap +self.vwap))).pow(2)), 16), 4)
        return max(p1, p2)

    # Alpha#72
    def alpha072(self) -> pd.DataFrame:
        """(rank(decay_linear(correlation(((high + low) / 2), adv40, 8.93345), 10.1519)) /rank(decay_linear(correlation(Ts_Rank(vwap, 3.72469), Ts_Rank(volume, 18.5188), 6.86671),2.95011)))"""
        adv40 = sma(self.volume, 40)
        return (rank(decay_linear(correlation(((self.high + self.low) / 2), adv40, 9), 10)) /rank(decay_linear(correlation(ts_rank(self.vwap, 4), ts_rank(self.volume, 19), 7),3)))

    # Alpha#73
    def alpha073(self) -> pd.DataFrame:
        """(max(rank(decay_linear(delta(vwap, 4.72775), 2.91864)),Ts_Rank(decay_linear(((delta(((open * 0.147155) + (low * (1 - 0.147155))), 2.03608) / ((open *0.147155) + (low * (1 - 0.147155)))) * -1), 3.33829), 16.7411)) * -1)"""
        p1 = rank(decay_linear(delta(self.vwap, 5), 3))
        p2 = ts_rank(decay_linear(((delta(((self.open * 0.147155) + (self.low * (1 - 0.147155))), 2) / ((self.open *0.147155) + (self.low * (1 - 0.147155)))) * -1), 3), 17)
        return -1*max(p1, p2)

    # Alpha#74
    def alpha074(self) -> pd.DataFrame:
        """((rank(correlation(close, sum(adv30, 37.4843), 15.1365)) <rank(correlation(rank(((high * 0.0261661) + (vwap * (1 - 0.0261661)))), rank(volume), 11.4791)))* -1)"""
        adv30 = sma(self.volume, 30)
        return ((rank(correlation(self.close, sma(adv30, 37), 15)) <rank(correlation(rank(((self.high * 0.0261661) + (self.vwap * (1 - 0.0261661)))), rank(self.volume), 11)))* -1)

    # Alpha#75
    def alpha075(self) -> pd.DataFrame:
        """(rank(correlation(vwap, volume, 4.24304)) < rank(correlation(rank(low), rank(adv50),12.4413)))"""
        adv50 = sma(self.volume, 50)
        return (rank(correlation(self.vwap, self.volume, 4)) < rank(correlation(rank(self.low), rank(adv50),12))).astype('int')

    # Alpha#076
    def alpha076(self) -> pd.DataFrame:
        """STD(ABS((CLOSE/DELAY(CLOSE,1)-1))/VOLUME,20)/MEAN(ABS((CLOSE/DELAY(CLOSE,1)-1))/VOLUME,20)"""
        return stddev(np.abs((self.close/delay(self.close,1)-1))/self.volume,20)/sma(np.abs((self.close/delay(self.close,1)-1))/self.volume,20)

    # Alpha#77
    def alpha077(self) -> pd.DataFrame:
        """min(rank(decay_linear(((((high + low) / 2) + high) - (vwap + high)), 20.0451)),rank(decay_linear(correlation(((high + low) / 2), adv40, 3.1614), 5.64125)))"""
        adv40 = sma(self.volume, 40)
        p1 = rank(decay_linear(((((self.high + self.low) / 2) + self.high) - (self.vwap + self.high)), 20))
        p2 = rank(decay_linear(correlation(((self.high + self.low) / 2), adv40, 3), 6))
        return min(p1, p2)

    # Alpha#78
    def alpha078(self) -> pd.DataFrame:
        """(rank(correlation(sum(((low * 0.352233) + (vwap * (1 - 0.352233))), 19.7428),sum(adv40, 19.7428), 6.83313))^rank(correlation(rank(vwap), rank(volume), 5.77492)))"""
        adv40 = sma(self.volume, 40)
        return (rank(correlation(ts_sum(((self.low * 0.352233) + (self.vwap * (1 - 0.352233))), 20),ts_sum(adv40,20), 7)).pow(rank(correlation(rank(self.vwap), rank(self.volume), 6))))

    # Alpha#079
    def alpha079(self) -> pd.DataFrame:
        """SMA(MAX(CLOSE-DELAY(CLOSE,1),0),12,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),12,1)*100"""
        return sma(np.maximum(self.close-delay(self.close,1),0),12,1)/sma(np.abs(self.close-delay(self.close,1)),12,1)*100

    # Alpha#080
    def alpha080(self) -> pd.DataFrame:
        """(VOLUME-DELAY(VOLUME,5))/DELAY(VOLUME,5)*100"""
        return (self.volume-delay(self.volume,5))/delay(self.volume,5)*100

    # Alpha#81
    def alpha081(self) -> pd.DataFrame:
        """((rank(Log(product(rank((rank(correlation(vwap, sum(adv10, 49.6054),8.47743))^4)), 14.9655))) < rank(correlation(rank(vwap), rank(volume), 5.07914))) * -1)"""
        from numpy import log
        adv10 = sma(self.volume, 10)
        return ((rank(log(product(rank((rank(correlation(self.vwap, ts_sum(adv10, 50),8)).pow(4))), 15))) < rank(correlation(rank(self.vwap), rank(self.volume), 5))) * -1)

    # Alpha#082
    def alpha082(self) -> pd.DataFrame:
        """SMA((TSMAX(HIGH,6)-CLOSE)/(TSMAX(HIGH,6)-TSMIN(LOW,6))*100,20,1)"""
        return sma((ts_max(self.high,6)-self.close)/(ts_max(self.high,6)-ts_min(self.low,6))*100,20,1)

    # Alpha#83
    def alpha083(self) -> pd.DataFrame:
        """((rank(delay(((high - low) / (sum(close, 5) / 5)), 2)) * rank(rank(volume))) / (((high -low) / (sum(close, 5) / 5)) / (vwap - close)))"""
        return ((rank(delay(((self.high - self.low) / (ts_sum(self.close, 5) / 5)), 2)) * rank(rank(self.volume))) / (((self.high -self.low) / (ts_sum(self.close, 5) / 5)) / (self.vwap - self.close)))

    # Alpha#84
    def alpha084(self) -> pd.DataFrame:
        """SignedPower(Ts_Rank((vwap - ts_max(vwap, 15.3217)), 20.7127), delta(close,4.96796))"""
        return pow(ts_rank((self.vwap - ts_max(self.vwap, 15)), 21), delta(self.close,5))

    # Alpha#85
    def alpha085(self) -> pd.DataFrame:
        """(rank(correlation(((high * 0.876703) + (close * (1 - 0.876703))), adv30,9.61331))^rank(correlation(Ts_Rank(((high + low) / 2), 3.70596), Ts_Rank(volume, 10.1595),7.11408)))"""
        adv30 = sma(self.volume, 30)
        return (rank(correlation(((self.high * 0.876703) + (self.close * (1 - 0.876703))), adv30,10)).pow(rank(correlation(ts_rank(((self.high + self.low) / 2), 4), ts_rank(self.volume, 10),7))))

    # Alpha#86
    def alpha086(self) -> pd.DataFrame:
        """((Ts_Rank(correlation(close, sum(adv20, 14.7444), 6.00049), 20.4195) < rank(((open+ close) - (vwap + open)))) * -1)"""
        adv20 = sma(self.volume, 20)
        return ((ts_rank(correlation(self.close, sma(adv20, 15), 6), 20) < rank(((self.open+ self.close) - (self.vwap +self.open)))*20) * -1)

    # Alpha#087
    def alpha087(self) -> pd.DataFrame:
        """((RANK(DECAYLINEAR(DELTA(VWAP, 4), 7)) + TSRANK(DECAYLINEAR(((((LOW * 0.9) + (LOW * 0.1)) - VWAP) /(OPEN - ((HIGH + LOW) / 2))), 11), 7)) * -1)"""
        return ((rank(decay_linear(delta(self.vwap, 4), 7)) + ts_rank(decay_linear(((((self.low * 0.9) + (self.low * 0.1)) - self.vwap) /(self.open - ((self.high + self.low) / 2))), 11), 7)) * -1)

    # Alpha#88
    def alpha088(self) -> pd.DataFrame:
        """min(rank(decay_linear(((rank(open) + rank(low)) - (rank(high) + rank(close))),8.06882)), Ts_Rank(decay_linear(correlation(Ts_Rank(close, 8.44728), Ts_Rank(adv60,20.6966), 8.01266), 6.65053), 2.61957))"""
        adv60 = sma(self.volume, 60)
        p1 = rank(decay_linear(((rank(self.open) + rank(self.low)) - (rank(self.high) + rank(self.close))),8))
        p2 = ts_rank(decay_linear(correlation(ts_rank(self.close, 8), ts_rank(adv60,21), 8), 7), 3)
        return min(p1, p2)

    # Alpha#089
    def alpha089(self) -> pd.DataFrame:
        """2*(SMA(CLOSE,13,2)-SMA(CLOSE,27,2)-SMA(SMA(CLOSE,13,2)-SMA(CLOSE,27,2),10,2))"""
        return 2*(sma(self.close,13,2)-sma(self.close,27,2)-sma(sma(self.close,13,2)-sma(self.close,27,2),10,2))

    # Alpha#090
    def alpha090(self) -> pd.DataFrame:
        """(RANK(CORR(RANK(VWAP), RANK(VOLUME), 5)) * -1)"""
        return (rank(correlation(rank(self.vwap), rank(self.volume), 5)) * -1)

    # Alpha#091
    def alpha091(self) -> pd.DataFrame:
        """((RANK((CLOSE - MAX(CLOSE, 5)))*RANK(CORR((MEAN(VOLUME,40)), LOW, 5))) * -1)"""
        return ((rank((self.close - ts_max(self.close, 5)))*rank(correlation((sma(self.volume,40)), self.low, 5))) * -1)

    # Alpha#92
    def alpha092(self) -> pd.DataFrame:
        """min(Ts_Rank(decay_linear(((((high + low) / 2) + close) < (low + open)), 14.7221),18.8683), Ts_Rank(decay_linear(correlation(rank(low), rank(adv30), 7.58555), 6.94024),6.80584))"""
        adv30 = sma(self.volume, 30)
        p1 = ts_rank(decay_linear(((((self.high + self.low) / 2) + self.close) < (self.low + self.open)), 15),19)
        p2 = ts_rank(decay_linear(correlation(rank(self.low), rank(adv30), 8), 7),7)
        return min(p1, p2)

    # Alpha#093
    def alpha093(self) -> pd.DataFrame:
        """SUM((OPEN>=DELAY(OPEN,1)?0:MAX((OPEN-LOW),(OPEN-DELAY(OPEN,1)))),20)"""
        cond = (self.open >= delay(self.open,1))
        part = self.close.copy()
        part.loc[:, :] = np.nan
        part[cond] = 0
        part[~cond] = np.maximum((self.open-self.low),(self.open-delay(self.open,1)))
        return ts_sum(part, 20)

    # Alpha#94
    def alpha094(self) -> pd.DataFrame:
        """((rank((vwap - ts_min(vwap, 11.5783)))^Ts_Rank(correlation(Ts_Rank(vwap,19.6462), Ts_Rank(adv60, 4.02992), 18.0926), 2.70756)) * -1)"""
        adv60 = sma(self.volume, 60)
        return ((rank((self.vwap - ts_min(self.vwap, 12))).pow(ts_rank(correlation(ts_rank(self.vwap,20), ts_rank(adv60, 4), 18), 3)) * -1))

    # Alpha#95
    def alpha095(self) -> pd.DataFrame:
        """(rank((open - ts_min(open, 12.4105))) < Ts_Rank((rank(correlation(sum(((high + low)/ 2), 19.1351), sum(adv40, 19.1351), 12.8742))^5), 11.7584))"""
        adv40 = sma(self.volume, 40)
        return (rank((self.open - ts_min(self.open, 12)))*12 < ts_rank((rank(correlation(sma(((self.high + self.low)/ 2), 19), sma(adv40, 19), 13)).pow(5)), 12)).astype('int')

    # Alpha#96
    def alpha096(self) -> pd.DataFrame:
        """(max(Ts_Rank(decay_linear(correlation(rank(vwap), rank(volume), 3.83878),4.16783), 8.38151), Ts_Rank(decay_linear(Ts_ArgMax(correlation(Ts_Rank(close, 7.45404),Ts_Rank(adv60, 4.13242), 3.65459), 12.6556), 14.0365), 13.4143)) * -1)"""
        adv60 = sma(self.volume, 60)
        p1 = ts_rank(decay_linear(correlation(rank(self.vwap), rank(self.volume), 4),4), 8)
        p2 = ts_rank(decay_linear(ts_argmax(correlation(ts_rank(self.close, 7),ts_rank(adv60, 4), 4), 13), 14), 13)
        return -1*max(p1, p2)

    # Alpha#097
    def alpha097(self) -> pd.DataFrame:
        """STD(VOLUME,10)"""
        return stddev(self.volume,10)

    # Alpha#98
    def alpha098(self) -> pd.DataFrame:
        """(rank(decay_linear(correlation(vwap, sum(adv5, 26.4719), 4.58418), 7.18088)) -rank(decay_linear(Ts_Rank(Ts_ArgMin(correlation(rank(open), rank(adv15), 20.8187), 8.62571),6.95668), 8.07206)))"""
        adv5 = sma(self.volume, 5)
        adv15 = sma(self.volume, 15)
        return (rank(decay_linear(correlation(self.vwap, sma(adv5, 26), 5), 7)) -rank(decay_linear(ts_rank(ts_argmin(correlation(rank(self.open), rank(adv15), 21), 9),7), 8)))

    # Alpha#99
    def alpha099(self) -> pd.DataFrame:
        """((rank(correlation(sum(((high + low) / 2), 19.8975), sum(adv60, 19.8975), 8.8136)) <rank(correlation(low, volume, 6.28259))) * -1)"""
        adv60 = sma(self.volume, 60)
        return ((rank(correlation(ts_sum(((self.high + self.low) / 2), 20), ts_sum(adv60, 20), 9)) <rank(correlation(self.low, self.volume, 6))) * -1)

    # Alpha#100
    def alpha100(self) -> pd.DataFrame:
        """Std(self.volume,20)"""
        return stddev(self.volume,20)

    # Alpha#101
    def alpha101(self) -> pd.DataFrame:
        """((close - open) / ((high - low) + .001))"""
        return (self.close - self.open) / ((self.high - self.low) + 0.001)

    # 添加更多因子实现...
    # 由于篇幅限制，这里只实现前30个因子，完整的101个因子实现会根据需要继续添加

    def calculate_all_factors(self) -> Dict[str, pd.DataFrame]:
        """
        计算所有已实现的因子
        
        Returns:
            Dict[str, pd.DataFrame]: 因子名称到因子值的映射
        """
        factors = {}
        factor_methods = [method for method in dir(self) if method.startswith('alpha') and method[5:].isdigit()]
        
        for method_name in factor_methods:
            try:
                method = getattr(self, method_name)
                factor_value = method()
                factors[method_name] = factor_value
                print(f"成功计算因子: {method_name}")
            except Exception as e:
                print(f"计算因子 {method_name} 时出错: {e}")
        
        return factors

    def calculate_single_factor(self, factor_name: str) -> pd.DataFrame:
        """
        计算单个因子
        
        Args:
            factor_name: 因子名称，如 'alpha001'
            
        Returns:
            pd.DataFrame: 因子值
        """
        if hasattr(self, factor_name):
            try:
                method = getattr(self, factor_name)
                result = method()
                # 确保返回的是DataFrame
                if result is None:
                    print(f"警告: 因子 {factor_name} 计算返回了None")
                    # 返回一个与输入数据形状相同的零值DataFrame
                    return pd.DataFrame(index=self.close.index, columns=self.close.columns, dtype=float)
                elif isinstance(result, pd.Series):
                    # 如果返回的是Series，转换为DataFrame
                    if isinstance(result.index, pd.MultiIndex):
                        # 如果是MultiIndex Series，先转换为宽表格式
                        if len(result) > 0:
                            # 重塑为DataFrame
                            df_result = result.unstack(level='symbol') if 'symbol' in result.index.names else result.to_frame()
                            return df_result
                        else:
                            return pd.DataFrame(index=self.close.index, columns=self.close.columns, dtype=float)
                    else:
                        return result.to_frame()
                elif isinstance(result, pd.DataFrame):
                    return result
                else:
                    # 如果是其他类型，尝试转换为DataFrame
                    return pd.DataFrame(result, index=self.close.index, columns=self.close.columns)
            except Exception as e:
                print(f"计算因子 {factor_name} 时出错: {e}")
                import traceback
                traceback.print_exc()
                # 返回一个与输入数据形状相同的零值DataFrame
                return pd.DataFrame(index=self.close.index, columns=self.close.columns, dtype=float)
        else:
            raise ValueError(f"因子 {factor_name} 不存在")


# 测试代码
if __name__ == '__main__':
    # 创建测试数据
    import pandas as pd
    import numpy as np
    
    # 创建测试数据 - 使用多级索引
    dates = pd.date_range('2023-01-01', periods=30, freq='D')
    symbols = ['000001.SZ', '000002.SZ', '600000.SH']
    
    # 创建组合索引
    index = pd.MultiIndex.from_product([dates, symbols], names=['date', 'symbol'])
    
    # 生成测试数据
    np.random.seed(42)  # 为了结果可重现
    data_dict = {
        'open': np.random.uniform(90, 110, len(index)),
        'high': np.random.uniform(100, 120, len(index)),
        'low': np.random.uniform(80, 100, len(index)),
        'close': np.random.uniform(90, 110, len(index)),
        'volume': np.random.randint(1000000, 10000000, len(index))
    }
    
    test_data = pd.DataFrame(data_dict, index=index)
    
    # 确保数据按日期排序
    test_data = test_data.sort_index()
    
    print(f"测试数据形状: {test_data.shape}")
    print(f"测试数据列: {list(test_data.columns)}")
    
    # 测试因子计算
    factor_calculator = Alpha101Factors(test_data)
    
    # 计算单个因子测试
    try:
        alpha001_values = factor_calculator.alpha001()
        print(f"alpha001 计算完成，结果形状: {alpha001_values.shape}")
        print("alpha001 前几行结果:")
        print(alpha001_values.head())
    except Exception as e:
        print(f"计算alpha001时出错: {e}")
    
    # 计算所有已实现的因子
    all_factors = factor_calculator.calculate_all_factors()
    print(f"\n总共计算了 {len(all_factors)} 个因子")