"""
Alpha191因子库

WorldQuant Alpha191因子实现（精选部分）。

Alpha191是Alpha101的扩展版本，包含更多复杂的因子。
这里实现了部分核心Alpha191因子。
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from .operators import *
from .alpha101 import Alpha101Factor


class Alpha191Factor(Alpha101Factor):
    """
    Alpha191因子基类

    继承自Alpha101Factor，复用部分逻辑。
    """

    # ==================== Alpha191新增因子实现 ====================

    def alpha101(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha101: (close - open) / ((high - low) + 1e-12)

        逻辑：相对价格位置的简化版
        """
        return (data['close'] - data['open']) / ((data['high'] - data['low']) + 1e-12)

    def alpha102(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha102: -1 * rank(close - open) * rank(volume)

        逻辑：价格变化与成交量的排名乘积
        """
        price_change = data['close'] - data['open']
        return -rank(price_change) * rank(data['volume'])

    def alpha103(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha103: ((close - open) / (high - low)) * volume

        逻辑：相对价格位置乘以成交量
        """
        price_position = (data['close'] - data['open']) / (data['high'] - data['low'])
        return price_position * data['volume']

    def alpha104(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha104: rank(correlation(close, volume, 10))

        逻辑：收盘价与成交量的10天相关性排名
        """
        corr_value = correlation(data['close'], data['volume'], 10)
        return rank(corr_value)

    def alpha105(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha105: -1 * correlation(rank(high), rank(volume), 5)

        逻辑：最高价排名与成交量排名的5天相关性
        """
        rank_high = rank(data['high'])
        rank_volume = rank(data['volume'])
        return -correlation(rank_high, rank_volume, 5)

    def alpha106(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha106: -1 * ts_rank(abs(close - open), 10)

        逻辑：10天内价格变化幅度的排名
        """
        price_change = abs_series(data['close'] - data['open'])
        return -rolling_rank(price_change, 10)

    def alpha107(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha107: rank((close - open) / (delay(close, 1) - open))

        逻辑：今日跳空与昨日跳空的比值
        """
        today_gap = (data['close'] - data['open'])
        yesterday_close = delay(data['close'], 1)
        yesterday_gap = (yesterday_close - data['open'])

        return rank(today_gap / (yesterday_gap + 1e-12))

    def alpha108(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha108: (close - open) / (high - low) * volume

        逻辑：相对价格位置乘以成交量
        """
        price_position = (data['close'] - data['open']) / (data['high'] - data['low'])
        return price_position * data['volume']

    def alpha109(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha109: -1 * delta(close, 5)

        逻辑：5天价格变化
        """
        return -delta(data['close'], 5)

    def alpha110(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha110: rank(low - delay(close, 1))

        逻辑：今日最低价与昨日收盘价差额的排名
        """
        gap_down = data['low'] - delay(data['close'], 1)
        return rank(gap_down)

    def alpha111(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha111: rank((close - delay(close, 1)) / (delay(close, 1) - open))

        逻辑：今日涨跌幅与昨日跳空的比值排名
        """
        today_return = (data['close'] - delay(data['close'], 1)) / delay(data['close'], 1)
        yesterday_gap = (delay(data['close'], 1) - data['open']) / data['open']

        return rank(today_return / (yesterday_gap + 1e-12))

    def alpha112(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha112: -1 * rank(delta(close, 1)) * rank(volume)

        逻辑：价格变化与成交量排名的乘积
        """
        delta_close = delta(data['close'], 1)
        return -rank(delta_close) * rank(data['volume'])

    def alpha113(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha113: -1 * correlation(rank(open), rank(volume), 10)

        逻辑：开盘价排名与成交量排名的相关性
        """
        rank_open = rank(data['open'])
        rank_volume = rank(data['volume'])
        return -correlation(rank_open, rank_volume, 10)

    def alpha114(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha114: rank((close - open) / (high - low))

        逻辑：日内价格相对位置排名
        """
        price_position = (data['close'] - data['open']) / (data['high'] - data['low'])
        return rank(price_position)

    def alpha115(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha115: -1 * delta(close, 7)

        逻辑：7天价格变化
        """
        return -delta(data['close'], 7)

    def alpha116(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha116: -1 * ts_rank(abs(close - delay(close, 1)), 20)

        逻辑：20天内价格变化幅度的排名
        """
        price_change = abs_series(data['close'] - delay(data['close'], 1))
        return -rolling_rank(price_change, 20)

    def alpha117(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha117: (close - open) / ((high - low) + 1e-12) * volume

        逻辑：相对价格位置乘以成交量
        """
        price_position = (data['close'] - data['open']) / ((data['high'] - data['low']) + 1e-12)
        return price_position * data['volume']

    def alpha118(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha118: rank(correlation(close, volume, 5))

        逻辑：收盘价与成交量的5天相关性排名
        """
        corr_value = correlation(data['close'], data['volume'], 5)
        return rank(corr_value)

    def alpha119(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha119: -1 * delta(close, 3)

        逻辑：3天价格变化
        """
        return -delta(data['close'], 3)

    def alpha120(self, data: pd.DataFrame) -> pd.Series:
        """
        Alpha120: -1 * rank(stddev(close, 10))

        逻辑：10天收盘价标准差的排名
        """
        std_value = stddev(data['close'], 10)
        return -rank(std_value)


# 便捷函数：获取所有Alpha191因子名称
def get_alpha191_factors() -> List[str]:
    """获取所有可用的Alpha191因子名称"""
    return [
        'alpha101', 'alpha102', 'alpha103', 'alpha104', 'alpha105',
        'alpha106', 'alpha107', 'alpha108', 'alpha109', 'alpha110',
        'alpha111', 'alpha112', 'alpha113', 'alpha114', 'alpha115',
        'alpha116', 'alpha117', 'alpha118', 'alpha119', 'alpha120'
    ]


# 便捷函数：获取因子描述
def get_alpha191_descriptions() -> Dict[str, str]:
    """获取Alpha191因子的描述"""
    return {
        'alpha101': '相对价格位置',
        'alpha102': '价格变化与成交量排名乘积',
        'alpha103': '相对价格位置乘以成交量',
        'alpha104': '收盘价与成交量相关性排名',
        'alpha105': '最高价与成交量负相关性',
        'alpha106': '价格变化幅度排名',
        'alpha107': '跳空相对值排名',
        'alpha108': '相对位置乘以成交量',
        'alpha109': '5天价格变化',
        'alpha110': '向下跳空排名',
        'alpha111': '收益率与跳空比值',
        'alpha112': '价格变化与成交量乘积',
        'alpha113': '开盘价与成交量相关性',
        'alpha114': '相对价格位置排名',
        'alpha115': '7天价格变化',
        'alpha116': '20天价格变化幅度',
        'alpha117': '相对位置乘以成交量（带平滑）',
        'alpha118': '5天相关性排名',
        'alpha119': '3天价格变化',
        'alpha120': '10天波动率排名'
    }
