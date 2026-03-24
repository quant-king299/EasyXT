"""
Alpha101因子库

WorldQuant Alpha101因子实现。
包含前20个最常用的Alpha101因子。

参考：https://worldquant.com/101/
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from .operators import *
from .base import BaseFactor
from ..config import FactorConfig


class Alpha101Factor(BaseFactor):
    """
    Alpha101因子基类

    所有Alpha101因子都继承此类。
    """

    def __init__(self, config: FactorConfig, data_manager):
        super().__init__(config, data_manager)
        self.factor_name = config.field  # 例如: alpha001, alpha002...

    def calculate(self, stock_pool: List[str], date: str) -> pd.Series:
        """
        计算Alpha因子值

        Args:
            stock_pool: 股票列表
            date: 日期 (YYYYMMDD)

        Returns:
            Series: 股票代码到因子值的映射
        """
        try:
            # 获取历史价格数据（需要历史窗口）
            bars = self._get_bars(stock_pool, date, window=60)

            if bars is None or bars.empty:
                return pd.Series(index=stock_pool, dtype=float)

            # 调用对应的因子计算方法
            factor_method = getattr(self, self.factor_name, None)

            if factor_method is None:
                raise ValueError(f"不支持的因子: {self.factor_name}")

            # 计算因子值
            factor_values = factor_method(bars)

            # 提取最新一天的因子值
            if isinstance(factor_values.index, pd.MultiIndex):
                # MultiIndex: [date, symbol]
                latest_values = factor_values.groupby(level=1).last()
            else:
                # 单一日期
                latest_values = factor_values

            # 确保返回所有股票的值
            result = pd.Series(index=stock_pool, dtype=float)
            for stock in stock_pool:
                if stock in latest_values.index:
                    result[stock] = latest_values.loc[stock]
                else:
                    result[stock] = np.nan

            return result

        except Exception as e:
            print(f"❌ 计算Alpha101因子失败 [{self.factor_name}]: {e}")
            return pd.Series(index=stock_pool, dtype=float)

    def _get_bars(self, stock_pool: List[str], date: str, window: int = 60) -> pd.DataFrame:
        """
        获取历史K线数据

        Args:
            stock_pool: 股票列表
            date: 日期
            window: 窗口大小

        Returns:
            DataFrame with MultiIndex [date, symbol]
        """
        try:
            if hasattr(self.data_manager, 'get_bars_for_stocks'):
                return self.data_manager.get_bars_for_stocks(stock_pool, date, window)
            elif hasattr(self.data_manager, 'get_bars'):
                # 单个股票获取，需要循环
                all_data = []
                for stock in stock_pool[:10]:  # 限制数量避免过慢
                    try:
                        bars = self.data_manager.get_bars(
                            code=stock,
                            end_date=date,
                            period='daily',
                            count=window + 10
                        )
                        if bars is not None and not bars.empty:
                            bars['symbol'] = stock
                            all_data.append(bars)
                    except:
                        continue

                if all_data:
                    df = pd.concat(all_data, ignore_index=True)
                    df['date'] = pd.to_datetime(df['time'] if 'time' in df.columns else df.index)
                    df = df.set_index(['date', 'symbol'])
                    return df

            return None

        except Exception as e:
            print(f"⚠️ 获取历史数据失败: {e}")
            return None

    # ==================== Alpha101因子实现 ====================

    def alpha001(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha001: (-1 * correlation(rank(delta(log(volume), 1)), rank(((close - open) / open)), 6))

        逻辑：
        1. 计算成交量的对数变化
        2. 计算（收盘-开盘）/开盘（价格相对位置）
        3. 对两者进行排名
        4. 计算6天相关系数
        """
        volume = data['close'] * data['volume']  # 成交额
        volume_delta = delta(log_series(volume), 1)
        rank_volume = rank(volume_delta)

        price_change = (data['close'] - data['open']) / data['open']
        rank_price = rank(price_change)

        corr = correlation(rank_volume, rank_price, 6)
        return -corr

    def alpha002(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha002: (-1 * delta((((close - low) - (high - close)) / (high - low)), 1))

        逻辑：
        1. 计算（收盘-最低）-（最高-收盘）/（最高-最低）
        2. 计算变化率
        """
        numerator = (data['close'] - data['low']) - (data['high'] - data['close'])
        denominator = (data['high'] - data['low'])
        ratio = numerator / denominator

        return -delta(ratio, 1)

    def alpha003(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha003: sum((close == delay(close, 1)) ? 0 : ((close - (close > delay(close, 1)) ? ((close - delay(close, 1)) / delay(close, 1), 0)))

        简化版：6天内上涨日累计涨幅
        """
        close_lag1 = delay(data['close'], 1)
        close_diff = data['close'] - close_lag1
        pos_condition = data['close'] > close_lag1

        result = np.where(pos_condition, close_diff / close_lag1, 0)
        return ts_sum(pd.Series(result, index=data.index), 6)

    def alpha004(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha004: (-1 * ts_rank(rank(low), 9))

        逻辑：最低价的9天排名的负值
        """
        rank_low = rank(data['low'])
        return -rolling_rank(rank_low, 9)

    def alpha005(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha005: correlation(rank(open), rank(volume), 10)

        逻辑：开盘价排名与成交量的10天相关性
        """
        rank_open = rank(data['open'])
        rank_volume = rank(data['volume'])
        return correlation(rank_open, rank_volume, 10)

    def alpha006(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha006: (-1 * correlation(rank(open), rank(volume), 10))

        逻辑：开盘价排名与成交量的10天相关性的负值
        """
        rank_open = rank(data['open'])
        rank_volume = rank(data['volume'])
        return -correlation(rank_open, rank_volume, 10)

    def alpha007(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha007: ((adv20 < volume) ? ((-1 * ts_rank(abs(delta(close, 7)), 60)) * sign(delta(close, 7))) : ((-1 * abs(delta(close, 7))) * sign(delta(close, 7))))

        逻辑：
        1. 如果成交量大于20日均值：使用ts_rank加权的动量
        2. 否则：使用简单动量
        """
        adv20 = sma(data['volume'], 20)
        condition = adv20 < data['volume']

        delta_close = delta(data['close'], 7)
        abs_delta = abs_series(delta_close)
        sign_delta = sign(delta_close)

        ts_rank_abs = rolling_rank(abs_delta, 60)

        result = np.where(condition, (-ts_rank_abs * sign_delta), (-abs_delta * sign_delta))
        return pd.Series(result, index=data.index)

    def alpha008(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha008: (-1 * rank(((sum(open, 5) * sum(returns, 5)) - delay((sum(open, 5) * sum(returns, 5)), 10))))

        逻辑：
        1. 计算5日开盘价之和
        2. 计算5日收益率之和
        3. 两者相乘
        4. 与10天前的值做差
        5. 排名并取负
        """
        open_sum = ts_sum(data['open'], 5)
        returns = data['close'].pct_change()
        returns_sum = ts_sum(returns, 5)

        combined = open_sum * returns_sum
        diff = combined - delay(combined, 10)

        return -rank(diff)

    def alpha009(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha009: ((0 < ts_min(delta(close, 1), 5)) ? delta(close, 1) : ((ts_max(delta(close, 1), 5) < 0) ? delta(close, 1) : (-1 * delta(close, 1))))

        逻辑：
        1. 如果5天内最小涨幅>0：做多
        2. 如果5天内最大涨幅<0：做多
        3. 否则：做空
        """
        delta_close = delta(data['close'], 1)
        min_delta = ts_min(delta_close, 5)
        max_delta = ts_max(delta_close, 5)

        condition1 = min_delta > 0
        condition2 = max_delta < 0

        result = np.where(condition1, delta_close, np.where(condition2, delta_close, -delta_close))
        return pd.Series(result, index=data.index)

    def alpha010(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha010: rank(((0 < delta(close, 1)) ? delta(close, 1) : ((delta(close, 1) < 0) ? delta(close, 1) : (-1 * delta(close, 1)))))

        逻辑：动量方向强化
        """
        delta_close = delta(data['close'], 1)
        condition_pos = delta_close > 0
        condition_neg = delta_close < 0

        result = np.where(condition_pos, delta_close, np.where(condition_neg, delta_close, -delta_close))
        result_series = pd.Series(result, index=data.index)
        return rank(result_series)

    def alpha011(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha011: (rank(ts_max((vwap - close), 3)) + rank(ts_min((vwap - close), 3))) * rank(delta(volume, 3))

        逻辑：
        1. 计算vwap-close的3天最大排名和最小排名
        2. 乘以成交量变化排名
        """
        # 简化：使用close代替vwap
        vwap_close = data['close'] - data['close']

        rank_max = -rank(ts_max(vwap_close, 3))
        rank_min = rank(ts_min(vwap_close, 3))
        rank_volume_delta = rank(delta(data['volume'], 3))

        return (rank_max + rank_min) * rank_volume_delta

    def alpha012(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha012: sign(delta(volume, 1)) * (-1 * delta(close, 1))

        逻辑：成交量变化方向与价格变化方向相反
        """
        return sign(delta(data['volume'], 1)) * (-delta(data['close'], 1))

    def alpha013(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha013: (-1 * rank(covariance(rank(close), rank(volume), 5)))

        逻辑：收盘价排名与成交量排名的5天协方差，取负排名
        """
        rank_close = rank(data['close'])
        rank_volume = rank(data['volume'])
        cov_value = covariance(rank_close, rank_volume, 5)

        return -rank(cov_value)

    def alpha014(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha014: (-1 * rank(delta(returns, 3))) * correlation(open, volume, 10)

        逻辑：
        1. 3天收益率变化的排名（负）
        2. 乘以开盘价与成交量的10天相关性
        """
        returns = data['close'].pct_change()
        delta_returns = delta(returns, 3)

        rank_delta_returns = -rank(delta_returns)
        corr_open_volume = correlation(data['open'], data['volume'], 10)

        return rank_delta_returns * corr_open_volume

    def alpha015(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha015: (-1 * sum(rank(correlation(rank(high), rank(volume), 3)), 3))

        逻辑：最高价排名与成交量排名3天相关性的3天排名之和
        """
        rank_high = rank(data['high'])
        rank_volume = rank(data['volume'])
        corr_value = correlation(rank_high, rank_volume, 3)

        rank_corr = rank(corr_value)
        return -ts_sum(rank_corr, 3)

    def alpha016(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha016: (-1 * rank(covariance(rank(high), rank(volume), 5)))

        逻辑：最高价排名与成交量排名的5天协方差的负排名
        """
        rank_high = rank(data['high'])
        rank_volume = rank(data['volume'])
        cov_value = covariance(rank_high, rank_volume, 5)

        return -rank(cov_value)

    def alpha017(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha017: (-1 * rank(ts_rank((close), 10)))

        逻辑：收盘价的10天排名的负排名
        """
        return -rank(rolling_rank(data['close'], 10))

    def alpha018(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha018: (-1 * rank(((close - open)) / (high - low)))

        逻辑：相对位置（收盘-开盘）/（最高-最低）的负排名
        """
        price_position = (data['close'] - data['open']) / (data['high'] - data['low'])
        return -rank(price_position)

    def alpha019(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha019: (-1 * sign(((close - delay(close, 7))) + delta(volume, 7)))

        逻辑：
        1. 7天价格变化
        2. 7天成交量变化
        3. 两者之和的符号取负
        """
        price_change = data['close'] - delay(data['close'], 7)
        volume_change = delta(data['volume'], 7)

        return -sign(price_change + volume_change)

    def alpha020(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha020: (-1 * (open - delay(close, 1)))

        逻辑：今日开盘价与昨日收盘价的差额（负值）
        """
        return -(data['open'] - delay(data['close'], 1))


# 便捷函数：获取所有Alpha101因子名称
def get_alpha101_factors() -> List[str]:
    """获取所有可用的Alpha101因子名称"""
    return [
        'alpha001', 'alpha002', 'alpha003', 'alpha004', 'alpha005',
        'alpha006', 'alpha007', 'alpha008', 'alpha009', 'alpha010',
        'alpha011', 'alpha012', 'alpha013', 'alpha014', 'alpha015',
        'alpha016', 'alpha017', 'alpha018', 'alpha019', 'alpha020'
    ]


# 便捷函数：获取因子描述
def get_alpha101_descriptions() -> Dict[str, str]:
    """获取Alpha101因子的描述"""
    return {
        'alpha001': '成交量变化与价格相对位置的相关性',
        'alpha002': '价格位置变化的负值',
        'alpha003': '6天内上涨日累计涨幅',
        'alpha004': '最低价的9天排名',
        'alpha005': '开盘价与成交量的相关性',
        'alpha006': '开盘价与成交量的负相关性',
        'alpha007': '基于成交量的动量策略',
        'alpha008': '开盘价与收益率的组合变化',
        'alpha009': '基于动量方向的策略',
        'alpha010': '动量方向强化',
        'alpha011': 'VWAP与成交量的组合',
        'alpha012': '成交量与价格的反向关系',
        'alpha013': '收盘价与成交量的协方差',
        'alpha014': '收益率变化与成交量相关性',
        'alpha015': '最高价与成交量相关性累计',
        'alpha016': '最高价与成交量协方差',
        'alpha017': '收盘价时序排名',
        'alpha018': '日内价格相对位置',
        'alpha019': '价格与成交量变化方向',
        'alpha020': '开盘跳空'
    }
