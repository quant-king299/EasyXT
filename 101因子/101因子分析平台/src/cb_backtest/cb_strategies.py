# -*- coding: utf-8 -*-
"""
可转债回测策略库

每个策略函数接收当日行情 DataFrame，返回按偏好排序的 ts_code 列表。
"""

import pandas as pd


def strategy_low_premium(df: pd.DataFrame, top_n: int = 20) -> list:
    """低溢价率策略"""
    if 'cb_over_rate' not in df.columns:
        return df.nsmallest(top_n, 'close')['ts_code'].tolist()
    return df.dropna(subset=['cb_over_rate']).nsmallest(top_n, 'cb_over_rate')['ts_code'].tolist()


def strategy_dual_low(df: pd.DataFrame, top_n: int = 20) -> list:
    """双低策略（转债价格 + 转股溢价率 * 100）"""
    d = df.copy()
    d['dual_low'] = d['close'] + d['cb_over_rate'].fillna(0)
    return d.nsmallest(top_n, 'dual_low')['ts_code'].tolist()


def strategy_low_price_premium(df: pd.DataFrame, top_n: int = 20,
                               price_weight: float = 0.5) -> list:
    """价格+溢价率加权策略"""
    d = df.copy()
    d['price_rank'] = d['close'].rank(ascending=True)
    d['premium_rank'] = d['cb_over_rate'].rank(ascending=True)
    d['score'] = price_weight * d['price_rank'] + (1 - price_weight) * d['premium_rank']
    return d.nsmallest(top_n, 'score')['ts_code'].tolist()


def strategy_high_cb_value(df: pd.DataFrame, top_n: int = 20) -> list:
    """高转股价值策略"""
    if 'cb_value' not in df.columns:
        return []
    return df.dropna(subset=['cb_value']).nlargest(top_n, 'cb_value')['ts_code'].tolist()


def strategy_low_price(df: pd.DataFrame, top_n: int = 20) -> list:
    """低价策略"""
    return df.nsmallest(top_n, 'close')['ts_code'].tolist()


STRATEGY_REGISTRY = {
    'low_premium': {
        'name': '低溢价率',
        'desc': '选出转股溢价率最低的可转债',
        'func': strategy_low_premium,
    },
    'dual_low': {
        'name': '双低策略',
        'desc': '转债价格 + 溢价率*100，双低值越小越好',
        'func': strategy_dual_low,
    },
    'low_price_premium': {
        'name': '价格+溢价率加权',
        'desc': '综合排名价格和溢价率',
        'func': strategy_low_price_premium,
    },
    'high_cb_value': {
        'name': '高转股价值',
        'desc': '选出转股价值最高的可转债',
        'func': strategy_high_cb_value,
    },
    'low_price': {
        'name': '低价策略',
        'desc': '选出价格最低的可转债',
        'func': strategy_low_price,
    },
}
