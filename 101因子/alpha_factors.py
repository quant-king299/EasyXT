# Alpha Factors Module for EasyXT
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import datetime
import sys
import os

# 添加项目路径以导入easy_xt
project_path = os.path.join(os.path.dirname(__file__))
sys.path.insert(0, project_path)

from easy_xt.api import EasyXT


class AlphaFactors:
    """使用EasyXT实现WorldQuant 101 Alpha因子计算"""
    
    def __init__(self):
        self.data = None
        self.factor_data = {}
        self.easyxt = EasyXT()
        
    def load_data(self, symbols: List[str], start_date: str, end_date: str):
        """使用EasyXT加载股票历史数据"""
        print(f'正在使用EasyXT加载数据: {symbols} from {start_date} to {end_date}')
        
        # 初始化数据服务
        if not self.easyxt.init_data():
            print('初始化EasyXT数据服务失败')
            return
        
        try:
            # 获取价格数据
            df_data = self.easyxt.get_price(
                codes=symbols,
                start=start_date,
                end=end_date,
                period='1d',
                fields=['open', 'high', 'low', 'close', 'volume']
            )
            
            if df_data.empty:
                print('获取的数据为空，请检查股票代码和时间范围')
                return
            
            # 重命名列以匹配期望的格式
            df_data = df_data.rename(columns={
                'time': 'date',
                'code': 'symbol'
            })
            
            # 设置多级索引 [date, symbol]
            df_data = df_data.set_index(['date', 'symbol']).sort_index()
            
            self.data = df_data
            print(f'成功加载数据，形状: {self.data.shape}')
            print(f'数据列: {list(self.data.columns)}')
            print(f'股票代码: {self.data.index.get_level_values("symbol").unique().tolist()}')
            
        except Exception as e:
            print(f'加载数据时出错: {e}')
            # 如果无法获取真实数据，使用模拟数据作为备选
            print('使用模拟数据作为备选...')
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            # 过滤掉非交易日
            dates = [date for date in dates if date.weekday() < 5]  # 简单过滤周末
            
            data_dict = {}
            for symbol in symbols:
                # 模拟获取OHLCV数据
                temp_data = {
                    'date': dates,
                    'open': np.random.rand(len(dates)) * 100,
                    'high': np.random.rand(len(dates)) * 100,
                    'low': np.random.rand(len(dates)) * 100,
                    'close': np.random.rand(len(dates)) * 100,
                    'volume': np.random.randint(1000000, 10000000, len(dates)),
                    'symbol': symbol
                }
                df_temp = pd.DataFrame(temp_data)
                data_dict[symbol] = df_temp.set_index('date')
            
            # 合并所有股票的数据
            all_data = []
            for symbol, df in data_dict.items():
                df['symbol'] = symbol
                all_data.append(df)
            
            self.data = pd.concat(all_data)
            print(f'成功加载模拟数据，形状: {self.data.shape}')
        
    def ts_sum(self, df: pd.DataFrame, window: int) -> pd.Series:
        """时间序列求和"""
        return df.rolling(window=window).sum()
    
    def sma(self, df: pd.DataFrame, window: int) -> pd.Series:
        """简单移动平均"""
        return df.rolling(window=window).mean()
    
    def stddev(self, df: pd.DataFrame, window: int) -> pd.Series:
        """标准差"""
        return df.rolling(window=window).std()
    
    def correlation(self, x: pd.DataFrame, y: pd.DataFrame, window: int) -> pd.Series:
        """相关系数"""
        return x.rolling(window=window).corr(y)
    
    def covariance(self, x: pd.DataFrame, y: pd.DataFrame, window: int) -> pd.Series:
        """协方差"""
        return x.rolling(window=window).cov(y)
    
    def rolling_rank(self, df: pd.DataFrame, window: int) -> pd.Series:
        """滚动排名"""
        return df.rolling(window=window).apply(lambda x: x.rank().iloc[-1])
    
    def rolling_argmax(self, df: pd.DataFrame, window: int) -> pd.Series:
        """滚动最大值位置"""
        return df.rolling(window=window).apply(lambda x: x.argmax())
    
    def rolling_argmin(self, df: pd.DataFrame, window: int) -> pd.Series:
        """滚动最小值位置"""
        return df.rolling(window=window).apply(lambda x: x.argmin())
    
    def ts_min(self, df: pd.DataFrame, window: int) -> pd.Series:
        """时间序列最小值"""
        return df.rolling(window=window).min()
    
    def ts_max(self, df: pd.DataFrame, window: int) -> pd.Series:
        """时间序列最大值"""
        return df.rolling(window=window).max()
    
    def delta(self, df: pd.DataFrame, period: int) -> pd.Series:
        """差分"""
        return df.diff(periods=period)
    
    def delay(self, df: pd.DataFrame, period: int) -> pd.Series:
        """延迟"""
        return df.shift(periods=period)
    
    def rank(self, df: pd.Series) -> pd.Series:
        """截面排名"""
        # 对于多级索引数据，我们需要按日期进行横截面排名
        if isinstance(df.index, pd.MultiIndex):
            # 按第一个级别（日期）进行分组排名
            return df.groupby(level=0).rank(pct=True)
        else:
            # 如果不是多级索引，按索引进行排名
            return df.rank(pct=True)
    
    def scale(self, df: pd.DataFrame, scale_factor: float = 1) -> pd.Series:
        """缩放"""
        return df / df.abs().sum() * scale_factor
    
    def decay_linear(self, df: pd.DataFrame, window: int) -> pd.Series:
        """线性衰减"""
        weights = np.arange(1, window + 1)
        weights = weights / weights.sum()
        return df.rolling(window=window).apply(lambda x: (x * weights).sum(), raw=True)
    
    def alpha001(self, data: pd.DataFrame) -> pd.Series:
        """(-1 * correlation(rank(delta(log(volume), 1)), rank(((close - open) / open)), 6))"""
        volume_delta = np.log(data['volume']).diff()
        rank_volume = self.rank(volume_delta)
        price_change = (data['close'] - data['open']) / data['open']
        rank_price = self.rank(price_change)
        corr = self.correlation(rank_volume, rank_price, 6)
        return -corr

    def alpha002(self, data: pd.DataFrame) -> pd.Series:
        """(-1 * delta((((close-low)-(high-close))/((high-low)),1))"""
        numerator = (data['close'] - data['low']) - (data['high'] - data['close'])
        denominator = (data['high'] - data['low'])
        ratio = numerator / denominator
        return -self.delta(ratio, 1)

    def alpha003(self, data: pd.DataFrame) -> pd.Series:
        """sum(((close==delay(close,1))?0:((close-(close>delay(close,1))?((close-delay(close,1))/(delay(close,1)),0)))"""
        close_diff = data['close'] - data['close'].shift(1)
        pos_condition = (data['close'] > data['close'].shift(1))
        result = np.where(pos_condition, close_diff / data['close'].shift(1), 0)
        return self.ts_sum(pd.Series(result, index=data.index), 6)

    def alpha004(self, data: pd.DataFrame) -> pd.Series:
        """(-1 * ts_rank(rank(low), 9))"""
        rank_low = self.rank(data['low'])
        return -self.rolling_rank(rank_low, 9)

    def alpha005(self, data: pd.DataFrame) -> pd.Series:
        """correlation(rank(open), rank(volume), 10)"""
        rank_open = self.rank(data['open'])
        rank_volume = self.rank(data['volume'])
        return self.correlation(rank_open, rank_volume, 10)

    def alpha006(self, data: pd.DataFrame) -> pd.Series:
        """(-1 * correlation(rank(open), rank(close), 10))"""
        rank_open = self.rank(data['open'])
        rank_close = self.rank(data['close'])
        return -self.correlation(rank_open, rank_close, 10)

    def alpha007(self, data: pd.DataFrame) -> pd.Series:
        """((adv20<volume)?((-1*ts_rank(abs(delta(close,7)),60))*sign(delta(close,7))):((-1*abs(delta(close,7)))*sign(delta(close,7))))"""
        adv20 = self.sma(data['volume'], 20)
        condition = adv20 < data['volume']
        delta_close = self.delta(data['close'], 7)
        abs_delta = abs(delta_close)
        sign_delta = np.sign(delta_close)
        ts_rank_abs = self.rolling_rank(abs_delta, 60)
        
        result = np.where(condition, 
                         (-ts_rank_abs * sign_delta),
                         (-abs_delta * sign_delta))
        return pd.Series(result, index=data.index)

    def alpha008(self, data: pd.DataFrame) -> pd.Series:
        """(-1 * rank(((sum(open, 5) * sum(returns, 5)) - delay((sum(open, 5) * sum(returns, 5)), 10)))"""
        open_sum = self.ts_sum(data['open'], 5)
        returns = data['close'].pct_change()
        returns_sum = self.ts_sum(returns, 5)
        combined = open_sum * returns_sum
        diff = combined - combined.shift(10)
        return -self.rank(diff)

    def alpha009(self, data: pd.DataFrame) -> pd.Series:
        """((0 < ts_min(delta(close, 1), 5)) ? delta(close, 1) : ((ts_max(delta(close, 1), 5) < 0) ? delta(close, 1) : (-1 * delta(close, 1))))"""
        delta_close = self.delta(data['close'], 1)
        min_delta = self.ts_min(delta_close, 5)
        max_delta = self.ts_max(delta_close, 5)
        
        condition1 = min_delta > 0
        condition2 = max_delta < 0
        
        result = np.where(condition1, delta_close,
                         np.where(condition2, delta_close, -delta_close))
        return pd.Series(result, index=data.index)

    def alpha010(self, data: pd.DataFrame) -> pd.Series:
        """rank(((0 < delta(close, 1)) ? delta(close, 1) : ((delta(close, 1) < 0) ? delta(close, 1) : (-1 * delta(close, 1)))))"""
        delta_close = self.delta(data['close'], 1)
        condition_pos = delta_close > 0
        condition_neg = delta_close < 0
        
        result = np.where(condition_pos, delta_close,
                         np.where(condition_neg, delta_close, -delta_close))
        result_series = pd.Series(result, index=data.index)
        return self.rank(result_series)

    def alpha011(self, data: pd.DataFrame) -> pd.Series:
        """(rank(ts_max((vwap - close), 3)) + rank(ts_min((vwap - close), 3))) * rank(delta(volume, 3))"""
        # 假设vwap是成交量加权平均价，这里简化处理
        vwap = (data['high'] + data['low'] + data['close']) / 3
        vwap_close_diff = vwap - data['close']
        rank_max = self.rank(self.ts_max(vwap_close_diff, 3))
        rank_min = self.rank(self.ts_min(vwap_close_diff, 3))
        rank_vol_delta = self.rank(self.delta(data['volume'], 3))
        return (rank_max + rank_min) * rank_vol_delta

    def alpha012(self, data: pd.DataFrame) -> pd.Series:
        """(sign(delta(volume, 1)) * (-1 * delta(close, 1)))"""
        sign_vol = np.sign(self.delta(data['volume'], 1))
        neg_close_delta = -self.delta(data['close'], 1)
        return sign_vol * neg_close_delta

    def alpha013(self, data: pd.DataFrame) -> pd.Series:
        """(-1 * rank(covariance(rank(close), rank(volume), 5)))"""
        rank_close = self.rank(data['close'])
        rank_volume = self.rank(data['volume'])
        covar = self.covariance(rank_close, rank_volume, 5)
        return -self.rank(covar)

    def alpha014(self, data: pd.DataFrame) -> pd.Series:
        """((-1 * rank(rank(correlation(returns, sum(close, 50), 14))) * rank(correlation(rank(close), rank(volume), 15)))"""
        returns = data['close'].pct_change()
        close_sum = self.ts_sum(data['close'], 50)
        corr1 = self.correlation(returns, close_sum, 14)
        rank_corr1 = self.rank(corr1)
        
        rank_close = self.rank(data['close'])
        rank_volume = self.rank(data['volume'])
        corr2 = self.correlation(rank_close, rank_volume, 15)
        rank_corr2 = self.rank(corr2)
        
        return -rank_corr1 * rank_corr2

    def alpha015(self, data: pd.DataFrame) -> pd.Series:
        """(-1 * sum(rank(correlation(rank(high), rank(volume), 3)), 2))"""
        rank_high = self.rank(data['high'])
        rank_volume = self.rank(data['volume'])
        corr = self.correlation(rank_high, rank_volume, 3)
        rank_corr = self.rank(corr)
        return -self.ts_sum(rank_corr, 2)

    def alpha016(self, data: pd.DataFrame) -> pd.Series:
        """(-1 * rank(covariance(rank(high), rank(volume), 5)))"""
        rank_high = self.rank(data['high'])
        rank_volume = self.rank(data['volume'])
        covar = self.covariance(rank_high, rank_volume, 5)
        return -self.rank(covar)

    def alpha017(self, data: pd.DataFrame) -> pd.Series:
        """(((rank((vwap - ts_min(low, 6))) < rank((vwap - ts_max(high, 6)))) * -1)"""
        vwap = (data['high'] + data['low'] + data['close']) / 3
        vwap_low_diff = vwap - self.ts_min(data['low'], 6)
        vwap_high_diff = vwap - self.ts_max(data['high'], 6)
        
        rank1 = self.rank(vwap_low_diff)
        rank2 = self.rank(vwap_high_diff)
        
        return pd.Series(np.where(rank1 < rank2, -1, 0), index=data.index)

    def alpha018(self, data: pd.DataFrame) -> pd.Series:
        """(-1 * rank(stddev(abs((close - open)), 5) + (close - open)) + rank((log(abs((close - open))) - log(abs(delay(close, 1) - open)))))"""
        close_open_diff = abs(data['close'] - data['open'])
        std_dev = self.stddev(close_open_diff, 5)
        first_part = self.rank(std_dev + (data['close'] - data['open']))
        
        log_diff = np.log(abs(data['close'] - data['open'])) - np.log(abs(data['close'].shift(1) - data['open']))
        second_part = self.rank(log_diff)
        
        return -first_part + second_part

    def alpha019(self, data: pd.DataFrame) -> pd.Series:
        """((-1 * sign(((close - delay(close, 7)) + delta(close, 7)))) * correlation(rank(close), rank(volume), 6))"""
        close_delay = data['close'] - data['close'].shift(7)
        close_delta = self.delta(data['close'], 7)
        sign_expr = np.sign(close_delay + close_delta)
        
        rank_close = self.rank(data['close'])
        rank_volume = self.rank(data['volume'])
        corr = self.correlation(rank_close, rank_volume, 6)
        
        return -sign_expr * corr

    def alpha020(self, data: pd.DataFrame) -> pd.Series:
        """((-1 * rank((open - delay(high, 1)))) * rank((open - delay(close, 1))) * rank((open - delay(low, 1))))"""
        rank1 = self.rank(data['open'] - data['high'].shift(1))
        rank2 = self.rank(data['open'] - data['close'].shift(1))
        rank3 = self.rank(data['open'] - data['low'].shift(1))
        return -rank1 * rank2 * rank3

    def calculate_single_factor(self, factor_func, symbol_data):
        """计算单个因子"""
        try:
            result = factor_func(symbol_data)
            return result
        except Exception as e:
            print(f'计算因子时出错: {e}')
            return pd.Series([np.nan] * len(symbol_data), index=symbol_data.index)

    def calculate_all_factors(self, symbols: List[str], start_date: str, end_date: str):
        """计算所有101个因子"""
        print('开始加载数据...')
        self.load_data(symbols, start_date, end_date)
        
        factors_to_calculate = {
            'alpha001': self.alpha001,
            'alpha002': self.alpha002,
            'alpha003': self.alpha003,
            'alpha004': self.alpha004,
            'alpha005': self.alpha005,
            'alpha006': self.alpha006,
            'alpha007': self.alpha007,
            'alpha008': self.alpha008,
            'alpha009': self.alpha009,
            'alpha010': self.alpha010,
            'alpha011': self.alpha011,
            'alpha012': self.alpha012,
            'alpha013': self.alpha013,
            'alpha014': self.alpha014,
            'alpha015': self.alpha015,
            'alpha016': self.alpha016,
            'alpha017': self.alpha017,
            'alpha018': self.alpha018,
            'alpha019': self.alpha019,
            'alpha020': self.alpha020
        }
        
        print('开始计算因子...')
        results = {}
        
        for symbol in symbols:
            # 适配多级索引的数据结构
            symbol_data = self.data.xs(symbol, level='symbol', drop_level=False)
            
            for factor_name, factor_func in factors_to_calculate.items():
                print(f'正在计算 {factor_name} 对于 {symbol}')
                factor_values = self.calculate_single_factor(factor_func, symbol_data)
                
                if factor_name not in results:
                    results[factor_name] = {}
                results[factor_name][symbol] = factor_values
        
        self.factor_data = results
        print('因子计算完成!')
        return results

    def analyze_factors(self):
        """分析因子"""
        print('正在进行因子分析...')
        analysis_results = {}
        
        for factor_name, factor_data in self.factor_data.items():
            print(f'分析因子: {factor_name}')
            correlations = {}
            
            for symbol, values in factor_data.items():
                # 计算与收益率的相关性
                symbol_data = self.data.xs(symbol, level='symbol', drop_level=False)
                returns = symbol_data['close'].pct_change()
                
                # 对齐索引
                aligned_values, aligned_returns = values.align(returns, join='inner')
                
                if len(aligned_values) > 0 and len(aligned_returns) > 0:
                    corr = np.corrcoef(aligned_values.dropna(), aligned_returns.dropna())[0, 1]
                    correlations[symbol] = corr
            
            analysis_results[factor_name] = correlations
        
        return analysis_results

    def backtest(self, factor_name: str, top_n: int = 10):
        """简单的回测功能"""
        print(f'对因子 {factor_name} 进行回测...')
        
        if factor_name not in self.factor_data:
            print(f'因子 {factor_name} 不存在')
            return None
        
        backtest_results = {}
        
        # 获取指定日期范围内的因子值和价格数据
        for date in self.data.index.get_level_values(0).unique():
            date_data = self.data.loc[date]
            factor_values = {}
            
            for symbol in date_data.index:
                if factor_name in self.factor_data and symbol in self.factor_data[factor_name]:
                    factor_series = self.factor_data[factor_name][symbol]
                    if isinstance(factor_series, pd.Series) and date in factor_series.index:
                        factor_val = factor_series.loc[date]
                    else:
                        factor_val = np.nan
                    factor_values[symbol] = factor_val
            
            if factor_values:
                # 排序并选择top N
                sorted_factors = {k: v for k, v in sorted(factor_values.items(), key=lambda item: item[1] if not pd.isna(item[1]) else -np.inf, reverse=True)}
                top_symbols = list(sorted_factors.keys())[:top_n]
                
                # 计算收益率
                date_returns = {}
                for symbol in top_symbols:
                    if (date, symbol) in self.data.index:
                        current_price = self.data.loc[(date, symbol), 'close']
                        future_date = date + pd.Timedelta(days=1)
                        # 查找下一个交易日
                        available_dates = self.data.index.get_level_values(0).unique()
                        next_trading_day = None
                        for d in sorted(available_dates):
                            if d > date:
                                next_trading_day = d
                                break
                        
                        if next_trading_day is not None and (next_trading_day, symbol) in self.data.index:
                            future_price = self.data.loc[(next_trading_day, symbol), 'close']
                            ret = (future_price - current_price) / current_price
                        else:
                            ret = 0  # 如果没有下一个交易日数据，则收益率为0
                        date_returns[symbol] = ret
                
                backtest_results[date] = {
                    'top_symbols': top_symbols,
                    'returns': date_returns
                }
        
        return backtest_results


# 示例使用
if __name__ == '__main__':
    # 初始化因子计算器
    af = AlphaFactors()
    
    # 定义测试股票列表和日期范围
    symbols = ['000001.SZ', '600000.SH', '000002.SZ', '600036.SH', '000858.SZ']  # 使用中国A股代码
    start_date = '2023-01-01'
    end_date = '2023-03-01'  # 使用较短的时间范围进行测试
    
    # 计算因子
    results = af.calculate_all_factors(symbols, start_date, end_date)
    
    # 分析因子
    analysis = af.analyze_factors()
    print('\n因子分析结果:')
    for factor, corr_data in analysis.items():
        print(f'{factor}: {len([v for v in corr_data.values() if not pd.isna(v)])} 有效相关性')
    
    # 回测示例
    backtest_result = af.backtest('alpha001', top_n=3)
    print(f'\n回测结果样本: {list(backtest_result.keys())[:3] if backtest_result else "无数据"}')
