"""
技术指标计算模块
=================

提供 50+ 种常用技术分析指标的纯 numpy/pandas 实现。

指标分类:
- 核心数学原语: ref, diff, hhv, llv, ma, ema, sma, wma, std, sum, slope, etc.
- 交叉/条件检测: cross, cross_up, cross_down, bars_last, count_true, etc.
- 摆动指标 (Oscillators): rsi, kdj, macd, cci, wr, mfi, mtm, roc, osc, trix, etc.
- 趋势指标 (Trend): boll, dmi, sar, bbi, expma, dkx, etc.
- 量价指标 (Volume): obv, vmacd, vrsi, wvad, vpt, etc.
- 市场强度 (Market): psy, vr, brar, ar, cr, etc.
- 交易信号 (Signals): ma_cross_signal, macd_signal, kdj_signal, etc.

使用方式:
    from easy_xt.indicators import IndicatorCalculator

    calc = IndicatorCalculator(df)          # df 需包含 open/high/low/close/volume
    df['rsi_14'] = calc.rsi(14)
    df['macd'], df['macd_signal'], df['macd_hist'] = calc.macd()
    df['ma_cross'] = calc.ma_cross_signal(5, 20)
"""

import numpy as np
import pandas as pd
from typing import Tuple, List, Optional, Union


# ============================================================================
# 第一部分: 核心数学原语
# ============================================================================

def ref(series: np.ndarray, n: int = 1) -> np.ndarray:
    """引用前 N 周期的值。 series[i] 返回 series[i-n]"""
    s = pd.Series(series)
    return s.shift(n).values


def diff(series: np.ndarray, n: int = 1) -> np.ndarray:
    """序列 N 阶差分。diff[i] = series[i] - series[i-n]"""
    return pd.Series(series).diff(n).values


def hhv(series: np.ndarray, n: int) -> np.ndarray:
    """N 周期内最高值"""
    return pd.Series(series).rolling(n, min_periods=1).max().values


def llv(series: np.ndarray, n: int) -> np.ndarray:
    """N 周期内最低值"""
    return pd.Series(series).rolling(n, min_periods=1).min().values


def ma(series: np.ndarray, n: int) -> np.ndarray:
    """简单移动平均 (SMA / MA)"""
    return pd.Series(series).rolling(n, min_periods=1).mean().values


def ema(series: np.ndarray, n: int) -> np.ndarray:
    """指数移动平均 (EMA)。alpha = 2/(n+1)"""
    return pd.Series(series).ewm(span=n, adjust=False).mean().values


def sma(series: np.ndarray, n: int, m: int = 1) -> np.ndarray:
    """扩展指数加权移动平均。alpha = m/n"""
    return pd.Series(series).ewm(alpha=m / n, adjust=False).mean().values


def wma(series: np.ndarray, n: int) -> np.ndarray:
    """加权移动平均 (WMA)。权重按线性递减：w_i = (n-i+1) / sum(1..n)"""
    weights = np.arange(1, n + 1)
    return pd.Series(series).rolling(n).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    ).values


def dma(series: np.ndarray, alpha: float) -> np.ndarray:
    """动态移动平均 (DMA)。使用固定 alpha 作为平滑因子，0 < alpha < 1"""
    return pd.Series(series).ewm(alpha=alpha, adjust=False).mean().values


def std(series: np.ndarray, n: int) -> np.ndarray:
    """N 周期标准差（总体标准差 ddof=0）"""
    return pd.Series(series).rolling(n, min_periods=1).std(ddof=0).values


def rolling_sum(series: np.ndarray, n: int) -> np.ndarray:
    """N 周期滚动求和。n=0 时返回累计和"""
    if n > 0:
        return pd.Series(series).rolling(n, min_periods=1).sum().values
    return pd.Series(series).cumsum().values


def avedev(series: np.ndarray, n: int) -> np.ndarray:
    """N 周期平均绝对偏差"""
    return pd.Series(series).rolling(n, min_periods=1).apply(
        lambda x: np.abs(x - x.mean()).mean(), raw=True
    ).values


def slope(series: np.ndarray, n: int) -> np.ndarray:
    """N 周期线性回归斜率"""
    return pd.Series(series).rolling(n, min_periods=1).apply(
        lambda x: np.polyfit(np.arange(n), x, deg=1)[0], raw=True
    ).values


def forecast(series: np.ndarray, n: int) -> np.ndarray:
    """N 周期线性回归后的下一周期预测值"""
    return pd.Series(series).rolling(n, min_periods=1).apply(
        lambda x: np.polyval(np.polyfit(np.arange(n), x, deg=1), n - 1), raw=True
    ).values


# ============================================================================
# 第二部分: 交叉/条件检测
# ============================================================================

def cross(s1: np.ndarray, s2: np.ndarray) -> np.ndarray:
    """两条序列的交叉检测。s1 从下方上穿 s2 时返回 True"""
    result = np.zeros(len(s1), dtype=bool)
    for i in range(1, len(s1)):
        result[i] = (s1[i] > s2[i]) and (s1[i - 1] <= s2[i - 1])
    return result


def cross_up(s1: np.ndarray, s2: np.ndarray) -> np.ndarray:
    """上穿检测。s1 从下方向上穿越 s2"""
    return cross(s1, s2)


def cross_down(s1: np.ndarray, s2: np.ndarray) -> np.ndarray:
    """下穿检测。s1 从上方向下穿越 s2"""
    result = np.zeros(len(s1), dtype=bool)
    for i in range(1, len(s1)):
        result[i] = (s1[i] < s2[i]) and (s1[i - 1] >= s2[i - 1])
    return result


def bars_last(condition: np.ndarray) -> np.ndarray:
    """上一次条件成立到当前的周期数"""
    m = np.concatenate(([0], np.where(condition, 1, 0)))
    for i in range(1, len(m)):
        m[i] = 0 if m[i] else m[i - 1] + 1
    return m[1:]


def count_true(condition: np.ndarray, n: int) -> np.ndarray:
    """最近 N 周期内条件为 True 的次数"""
    return rolling_sum(condition.astype(float), n)


def every_true(condition: np.ndarray, n: int) -> np.ndarray:
    """最近 N 周期内是否所有条件都为 True"""
    total = count_true(condition, n)
    return np.isclose(total, n)


def exist_true(condition: np.ndarray, n: int) -> np.ndarray:
    """最近 N 周期内是否存在至少一个 True"""
    total = count_true(condition, n)
    return total > 0


def bars_last_count(condition: np.ndarray) -> np.ndarray:
    """连续满足条件的周期数（从最近往前数）"""
    rt = np.zeros(len(condition) + 1)
    for i in range(len(condition)):
        rt[i + 1] = rt[i] + 1 if condition[i] else 0
    return rt[1:]


# ============================================================================
# 第三部分: 摆动指标 (Oscillators)
# ============================================================================

def rsi(close: np.ndarray, n: int = 14) -> np.ndarray:
    """
    相对强弱指标 (RSI)。
    RSI = 100 - 100 / (1 + 平均涨幅 / 平均跌幅)
    """
    delta = np.diff(close, prepend=close[0])
    gain = np.maximum(delta, 0)
    loss = np.abs(np.minimum(delta, 0))
    avg_gain = sma(gain, n, 1)
    avg_loss = sma(loss, n, 1)
    # 避免除零
    avg_loss = np.where(avg_loss == 0, np.finfo(float).eps, avg_loss)
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def macd(close: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9
         ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    MACD 指标。
    返回: (DIF, DEA, MACD柱)
      - DIF = EMA(fast) - EMA(slow)
      - DEA = EMA(DIF, signal)
      - MACD = 2 * (DIF - DEA)
    """
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    dif = ema_fast - ema_slow
    dea = ema(dif, signal)
    macd_hist = 2.0 * (dif - dea)
    return dif, dea, macd_hist


def kdj(close: np.ndarray, high: np.ndarray, low: np.ndarray,
        n: int = 9, m1: int = 3, m2: int = 3
        ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    随机指标 (KDJ)。
    返回: (K, D, J)
      K = SMA(RSV, m1, 1)
      D = SMA(K, m2, 1)
      J = 3*K - 2*D
    """
    lowest_low = llv(low, n)
    highest_high = hhv(high, n)
    denom = highest_high - lowest_low
    denom = np.where(denom == 0, np.finfo(float).eps, denom)
    rsv = (close - lowest_low) / denom * 100.0
    k = sma(rsv, m1, 1)
    d = sma(k, m2, 1)
    j = 3.0 * k - 2.0 * d
    return k, d, j


def cci(close: np.ndarray, high: np.ndarray, low: np.ndarray, n: int = 14) -> np.ndarray:
    """
    商品通道指数 (CCI)。
    CCI = (TP - MA(TP, n)) / (0.015 * AVEDEV(TP, n))
    TP = (high + low + close) / 3
    """
    tp = (high + low + close) / 3.0
    ma_tp = ma(tp, n)
    md = avedev(tp, n)
    md = np.where(md == 0, np.finfo(float).eps, md)
    return (tp - ma_tp) / (0.015 * md)


def wr(close: np.ndarray, high: np.ndarray, low: np.ndarray, n: int = 10) -> np.ndarray:
    """
    威廉指标 (WR)。
    WR = (HHV(high, n) - close) / (HHV(high, n) - LLV(low, n)) * 100
    """
    hh = hhv(high, n)
    ll = llv(low, n)
    denom = hh - ll
    denom = np.where(denom == 0, np.finfo(float).eps, denom)
    return (hh - close) / denom * 100.0


def mfi(close: np.ndarray, high: np.ndarray, low: np.ndarray,
        volume: np.ndarray, n: int = 14) -> np.ndarray:
    """
    资金流量指标 (MFI)。
    典型价格 = (H+L+C)/3
    正向资金流 / 负向资金流的 14 周期比率
    """
    tp = (high + low + close) / 3.0
    tp_prev = ref(tp, 1)
    pos_flow = np.where(tp > tp_prev, tp * volume, 0)
    neg_flow = np.where(tp < tp_prev, tp * volume, 0)
    pos_sum = rolling_sum(pos_flow, n)
    neg_sum = rolling_sum(neg_flow, n)
    neg_sum = np.where(neg_sum == 0, np.finfo(float).eps, neg_sum)
    money_ratio = pos_sum / neg_sum
    return 100.0 - 100.0 / (1.0 + money_ratio)


def mtm(close: np.ndarray, n: int = 12, m: int = 6
        ) -> Tuple[np.ndarray, np.ndarray]:
    """
    动量线指标 (MTM)。
    MTM = close - ref(close, n)
    MTMMA = MA(MTM, m)
    """
    momentum = close - ref(close, n)
    mtmma = ma(momentum, m)
    return momentum, mtmma


def roc(close: np.ndarray, n: int = 12, m: int = 6
        ) -> Tuple[np.ndarray, np.ndarray]:
    """
    变动率指标 (ROC)。
    ROC = 100 * (close - ref(close, n)) / ref(close, n)
    MAROC = MA(ROC, m)
    """
    prev_close = ref(close, n)
    prev_close = np.where(prev_close == 0, np.finfo(float).eps, prev_close)
    roc_values = 100.0 * (close - prev_close) / prev_close
    maroc = ma(roc_values, m)
    return roc_values, maroc


def trix(close: np.ndarray, n: int = 12, m: int = 9) -> Tuple[np.ndarray, np.ndarray]:
    """
    三重指数平滑平均线 (TRIX)。
    TR = EMA(EMA(EMA(close, n), n), n)
    TRIX = 100 * (TR - ref(TR, 1)) / ref(TR, 1)
    MATRIX = MA(TRIX, m)
    """
    tr = ema(ema(ema(close, n), n), n)
    prev_tr = ref(tr, 1)
    prev_tr = np.where(prev_tr == 0, np.finfo(float).eps, prev_tr)
    trix_values = 100.0 * (tr - prev_tr) / prev_tr
    matrix = ma(trix_values, m)
    return trix_values, matrix


def uos(close: np.ndarray, high: np.ndarray, low: np.ndarray,
        n1: int = 7, n2: int = 14, n3: int = 28, m: int = 6) -> np.ndarray:
    """
    终极指标 (UOS)。
    结合三个时间框架的买卖压力。
    """
    bp = close - np.minimum(low, ref(close, 1))
    tr_range = np.maximum(high, ref(close, 1)) - np.minimum(low, ref(close, 1))
    tr_range = np.where(tr_range == 0, np.finfo(float).eps, tr_range)

    avg7 = rolling_sum(bp, n1) / rolling_sum(tr_range, n1)
    avg14 = rolling_sum(bp, n2) / rolling_sum(tr_range, n2)
    avg28 = rolling_sum(bp, n3) / rolling_sum(tr_range, n3)

    uos_raw = (4.0 * avg7 + 2.0 * avg14 + avg28) / 7.0 * 100.0
    return sma(uos_raw, m, 1)


# ============================================================================
# 第四部分: 趋势指标 (Trend)
# ============================================================================

def boll(close: np.ndarray, n: int = 20, k: float = 2.0
         ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    布林带 (Bollinger Bands)。
    返回: (中轨, 上轨, 下轨)
      中轨 = MA(close, n)
      上轨 = 中轨 + k * STD(close, n)
      下轨 = 中轨 - k * STD(close, n)
    """
    mid = ma(close, n)
    s = std(close, n)
    upper = mid + k * s
    lower = mid - k * s
    return mid, upper, lower


def bbi(close: np.ndarray,
        m1: int = 3, m2: int = 6, m3: int = 12, m4: int = 24) -> np.ndarray:
    """
    多空指标 (BBI)。
    BBI = (MA(close,3) + MA(close,6) + MA(close,12) + MA(close,24)) / 4
    """
    return (ma(close, m1) + ma(close, m2) + ma(close, m3) + ma(close, m4)) / 4.0


def dmi(close: np.ndarray, high: np.ndarray, low: np.ndarray,
        n: int = 14, m: int = 6
        ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    趋向指标 (DMI)。
    返回: (PDI, MDI, ADX, ADXR)
      PDI = +DI 方向线
      MDI = -DI 方向线
      ADX = MA(DX, n)
      ADXR = (ADX + ref(ADX, m)) / 2
    """
    high_diff = high - ref(high, 1)
    low_diff = ref(low, 1) - low

    plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
    minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)

    tr_range = np.maximum(
        np.maximum(high - low, np.abs(high - ref(close, 1))),
        np.abs(low - ref(close, 1))
    )

    plus_di = 100.0 * sma(plus_dm, n, 1) / sma(tr_range, n, 1)
    minus_di = 100.0 * sma(minus_dm, n, 1) / sma(tr_range, n, 1)

    di_sum = plus_di + minus_di
    di_sum = np.where(di_sum == 0, np.finfo(float).eps, di_sum)
    dx = 100.0 * np.abs(plus_di - minus_di) / di_sum
    adx = ma(dx, m)
    adxr = (adx + ref(adx, m)) / 2.0
    return plus_di, minus_di, adx, adxr


def sar(high: np.ndarray, low: np.ndarray,
        af_init: float = 0.02, af_max: float = 0.2, af_step: float = 0.02
        ) -> np.ndarray:
    """
    抛物线指标 (SAR)。

    Wilders 经典实现：加速因子从 af_init 逐步增加到 af_max。
    """
    n = len(high)
    sar_values = np.full(n, np.nan)
    # 初始方向：判断第一个非 NaN 值后的趋势
    ep = high[0]  # 极值点
    af = af_init
    is_long = True  # 当前为多头方向
    sar_values[0] = low[0]

    for i in range(1, n):
        sar_prev = sar_values[i - 1]

        if is_long:
            # 多头 SAR
            sar_today = sar_prev + af * (ep - sar_prev)
            sar_today = min(sar_today, low[i - 1], low[i - 2] if i >= 2 else low[i - 1])

            # 检查反转
            if low[i] < sar_today:
                is_long = False
                sar_today = ep
                ep = low[i]
                af = af_init
            else:
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + af_step, af_max)
        else:
            # 空头 SAR
            sar_today = sar_prev + af * (ep - sar_prev)
            sar_today = max(sar_today, high[i - 1], high[i - 2] if i >= 2 else high[i - 1])

            # 检查反转
            if high[i] > sar_today:
                is_long = True
                sar_today = ep
                ep = high[i]
                af = af_init
            else:
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + af_step, af_max)

        sar_values[i] = sar_today

    return sar_values


def dkx(close: np.ndarray, low: np.ndarray, _open: np.ndarray,
        high: np.ndarray, m: int = 10) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    多空线指标 (DKX)。
    MID = (3*close + low + open + high) / 6
    DKX = MA(20*MID + 19*ref(MID,1) + ... + 1*ref(MID,19)) / 210
    MADKX = MA(DKX, m)
    返回: (DKX, MADKX, 信号)
    """
    mid = (3.0 * close + low + _open + high) / 6.0
    # 20 周期加权
    mid_series = pd.Series(mid)
    weights = np.arange(20, 0, -1)
    dkx_values = mid_series.rolling(20, min_periods=1).apply(
        lambda x: np.dot(x[-len(weights):], weights[-len(x):]) / weights[-len(x):].sum()
        if len(x) > 0 else x[-1],
        raw=True
    ).values
    madkx = ma(dkx_values, m)
    return dkx_values, madkx, dkx_values > madkx


def expma(close: np.ndarray, m1: int = 12, m2: int = 50
          ) -> Tuple[np.ndarray, np.ndarray]:
    """
    指数平均线 (EXPMA)。
    返回: (EMA(m1), EMA(m2))
    """
    return ema(close, m1), ema(close, m2)


# ============================================================================
# 第五部分: 量价指标 (Volume)
# ============================================================================

def obv(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    """
    能量潮 (OBV)。
    累计成交量：价格上涨加成交量，价格下跌减成交量。
    """
    direction = np.sign(np.diff(close, prepend=close[0]))
    direction = np.where(direction == 0, 0, direction)
    daily_obv = direction * volume
    return np.cumsum(daily_obv)


def vmacd(volume: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9
          ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    成交量 MACD (VMACD)。
    对成交量序列应用 MACD 算法。
    """
    return macd(volume, fast, slow, signal)


def vrsi(volume: np.ndarray, n: int = 14) -> np.ndarray:
    """
    成交量 RSI (VRSI)。
    对成交量序列应用 RSI 算法。
    """
    return rsi(volume, n)


def vpt(close: np.ndarray, volume: np.ndarray, n: int = 51, m: int = 6
        ) -> Tuple[np.ndarray, np.ndarray]:
    """
    量价趋势 (VPT)。
    VPT = 累计(volume * (close - ref(close,1)) / ref(close,1))
    MAVPT = MA(VPT, m)
    """
    prev_close = ref(close, 1)
    prev_close = np.where(prev_close == 0, np.finfo(float).eps, prev_close)
    price_change_ratio = (close - prev_close) / prev_close
    daily_vpt = volume * price_change_ratio
    vpt_values = np.cumsum(daily_vpt)
    mavpt = ma(vpt_values, m)
    return vpt_values, mavpt


# ============================================================================
# 第六部分: 市场强度指标 (Market Strength)
# ============================================================================

def psy(close: np.ndarray, n: int = 12, m: int = 6) -> Tuple[np.ndarray, np.ndarray]:
    """
    心理线指标 (PSY)。
    PSY = 最近N周期内上涨天数 / N * 100
    MAPSY = MA(PSY, m)
    """
    up_days = (close > ref(close, 1)).astype(float)
    psy_values = rolling_sum(up_days, n) / n * 100.0
    mapsy = ma(psy_values, m)
    return psy_values, mapsy


def vr(close: np.ndarray, volume: np.ndarray, n: int = 26) -> np.ndarray:
    """
    成交量变异率 (VR)。
    VR = 上涨日成交量之和 / 下跌日成交量之和 * 100
    """
    close_prev = ref(close, 1)
    up_vol = np.where(close > close_prev, volume, 0)
    down_vol = np.where(close < close_prev, volume, 0)
    up_sum = rolling_sum(up_vol, n)
    down_sum = rolling_sum(down_vol, n)
    down_sum = np.where(down_sum == 0, np.finfo(float).eps, down_sum)
    return up_sum / down_sum * 100.0


def brar(_open: np.ndarray, high: np.ndarray, low: np.ndarray, n: int = 26
         ) -> Tuple[np.ndarray, np.ndarray]:
    """
    人气意愿指标 (BR/AR)。
    AR = N周期内 (high-open) 之和 / (open-low) 之和 * 100
    BR = N周期内 (high-ref(close,1)) 正和 / (ref(close,1)-low) 正和 * 100
    """
    # AR
    ho = high - _open
    ol = _open - low
    ar_sum_ho = rolling_sum(np.maximum(ho, 0), n)
    ar_sum_ol = rolling_sum(np.maximum(ol, 0), n)
    ar_sum_ol = np.where(ar_sum_ol == 0, np.finfo(float).eps, ar_sum_ol)
    ar = ar_sum_ho / ar_sum_ol * 100.0

    # BR
    prev_close = ref(close_from_data(_open, high, low), 1)
    br_pos = rolling_sum(np.maximum(high - prev_close, 0), n)
    br_neg = rolling_sum(np.maximum(prev_close - low, 0), n)
    br_neg = np.where(br_neg == 0, np.finfo(float).eps, br_neg)
    br = br_pos / br_neg * 100.0
    return br, ar


def close_from_data(_open: np.ndarray, high: np.ndarray, low: np.ndarray) -> np.ndarray:
    """根据开/高/低估算收盘价（仅用于内部计算）"""
    return (_open + high + low) / 3.0


def atr(close: np.ndarray, high: np.ndarray, low: np.ndarray, n: int = 14) -> np.ndarray:
    """
    真实波幅均值 (ATR)。
    TR = max(high-low, |high-ref(close,1)|, |low-ref(close,1)|)
    ATR = MA(TR, n)
    """
    prev_close = ref(close, 1)
    tr = np.maximum(
        np.maximum(high - low, np.abs(high - prev_close)),
        np.abs(low - prev_close)
    )
    return ma(tr, n)


# ============================================================================
# 第七部分: 交易信号生成
# ============================================================================

def ma_cross_signal(close: np.ndarray, short: int = 5, long: int = 20
                    ) -> Tuple[np.ndarray, np.ndarray]:
    """
    MA 金叉死叉信号。
    返回: (buy_signal, sell_signal)
      buy_signal: 短周期上穿长周期
      sell_signal: 短周期下穿长周期
    """
    ma_short = ma(close, short)
    ma_long = ma(close, long)
    return cross_up(ma_short, ma_long), cross_down(ma_short, ma_long)


def macd_signal(close: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9
                ) -> Tuple[np.ndarray, np.ndarray]:
    """
    MACD 金叉死叉信号。
    DIF 与 DEA 的交叉。
    """
    dif, dea, _ = macd(close, fast, slow, signal)
    return cross_up(dif, dea), cross_down(dif, dea)


def macd_divergence_signal(close: np.ndarray, fast: int = 12, slow: int = 26,
                           signal: int = 9
                           ) -> Tuple[np.ndarray, np.ndarray]:
    """
    MACD 背离信号。
    检测价格与 MACD 柱的顶背离/底背离。
    返回: (顶背离信号, 底背离信号)
    """
    dif, dea, hist = macd(close, fast, slow, signal)
    # 简化版：检测 DIF 与价格的背离
    n = len(close)
    top_div = np.zeros(n, dtype=bool)
    bot_div = np.zeros(n, dtype=bool)
    for i in range(20, n):
        # 底背离：价格新低但 DIF 未新低
        close_20_low = llv(close[i - 20:i + 1], 20)[-1]
        dif_20_low = llv(dif[i - 20:i + 1], 20)[-1]
        if close[i] <= close_20_low and dif[i] > dif_20_low:
            bot_div[i] = True
        # 顶背离：价格新高但 DIF 未新高
        close_20_high = hhv(close[i - 20:i + 1], 20)[-1]
        dif_20_high = hhv(dif[i - 20:i + 1], 20)[-1]
        if close[i] >= close_20_high and dif[i] < dif_20_high:
            top_div[i] = True
    return top_div, bot_div


def kdj_signal(k: np.ndarray, d: np.ndarray, oversold: float = 20,
               overbought: float = 80) -> Tuple[np.ndarray, np.ndarray]:
    """
    KDJ 金叉死叉信号 + 超卖/超买区过滤器。
    返回: (buy_signal, sell_signal)
    """
    buy = cross_up(k, d) & (k < oversold)
    sell = cross_down(k, d) & (k > overbought)
    return buy, sell


def boll_signal(close: np.ndarray, n: int = 20, k: float = 2.0
                ) -> Tuple[np.ndarray, np.ndarray]:
    """
    布林带信号。
    突破下轨为买，突破上轨为卖。
    """
    mid, upper, lower = boll(close, n, k)
    buy = cross_up(close, lower)
    sell = cross_down(close, upper)
    return buy, sell


# ============================================================================
# 第八部分: IndicatorCalculator 便捷类
# ============================================================================

class IndicatorCalculator:
    """
    基于 pandas DataFrame 的技术指标计算器。

    自动从 DataFrame 中提取 open/high/low/close/volume 列。
    所有方法返回添加了指标列的 DataFrame 或 numpy 数组。

    使用方式:
        calc = IndicatorCalculator(df)
        df = calc.add_rsi(14)              # 添加 RSI 列
        df = calc.add_macd()               # 添加 MACD 列
        df = calc.add_boll()               # 添加布林带列
        df = calc.add_all()                # 添加所有常用指标
    """

    def __init__(self, df: pd.DataFrame,
                 col_open: str = 'open',
                 col_high: str = 'high',
                 col_low: str = 'low',
                 col_close: str = 'close',
                 col_volume: str = 'volume'):
        self.df = df.copy() if df is not None else pd.DataFrame()
        self.col_open = col_open
        self.col_high = col_high
        self.col_low = col_low
        self.col_close = col_close
        self.col_volume = col_volume
        self._validate_columns()

    def _validate_columns(self):
        """验证必要列是否存在"""
        required = [self.col_open, self.col_high, self.col_low,
                    self.col_close, self.col_volume]
        missing = [c for c in required if c not in self.df.columns]
        if missing:
            cols_str = ', '.join(missing)
            raise ValueError(f"DataFrame 缺少必要列: {cols_str}")

    def _get(self, col: str) -> np.ndarray:
        return self.df[col].values

    # ---- 单个指标方法 ----

    def add_ma(self, periods: List[int] = None) -> pd.DataFrame:
        """添加移动平均线列: ma_{period}"""
        periods = periods or [5, 10, 20, 60, 120, 250]
        close = self._get(self.col_close)
        for p in periods:
            self.df[f'ma_{p}'] = ma(close, p)
        return self.df

    def add_ema(self, periods: List[int] = None) -> pd.DataFrame:
        """添加指数移动平均线列: ema_{period}"""
        periods = periods or [12, 26, 50]
        close = self._get(self.col_close)
        for p in periods:
            self.df[f'ema_{p}'] = ema(close, p)
        return self.df

    def add_rsi(self, n: int = 14) -> pd.DataFrame:
        """添加 RSI 列"""
        self.df[f'rsi_{n}'] = rsi(self._get(self.col_close), n)
        return self.df

    def add_macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """添加 MACD 列: macd_dif, macd_dea, macd_hist"""
        dif, dea, hist = macd(self._get(self.col_close), fast, slow, signal)
        self.df['macd_dif'] = dif
        self.df['macd_dea'] = dea
        self.df['macd_hist'] = hist
        return self.df

    def add_kdj(self, n: int = 9) -> pd.DataFrame:
        """添加 KDJ 列"""
        k, d, j = kdj(self._get(self.col_close), self._get(self.col_high),
                      self._get(self.col_low), n)
        self.df['kdj_k'] = k
        self.df['kdj_d'] = d
        self.df['kdj_j'] = j
        return self.df

    def add_boll(self, n: int = 20, k: float = 2.0) -> pd.DataFrame:
        """添加布林带列"""
        mid, upper, lower = boll(self._get(self.col_close), n, k)
        self.df['boll_mid'] = mid
        self.df['boll_upper'] = upper
        self.df['boll_lower'] = lower
        return self.df

    def add_atr(self, n: int = 14) -> pd.DataFrame:
        """添加 ATR 列"""
        self.df[f'atr_{n}'] = atr(self._get(self.col_close), self._get(self.col_high),
                                   self._get(self.col_low), n)
        return self.df

    def add_cci(self, n: int = 14) -> pd.DataFrame:
        """添加 CCI 列"""
        self.df[f'cci_{n}'] = cci(self._get(self.col_close), self._get(self.col_high),
                                   self._get(self.col_low), n)
        return self.df

    def add_wr(self, n: int = 10) -> pd.DataFrame:
        """添加 WR 列"""
        self.df[f'wr_{n}'] = wr(self._get(self.col_close), self._get(self.col_high),
                                 self._get(self.col_low), n)
        return self.df

    def add_dmi(self, n: int = 14, m: int = 6) -> pd.DataFrame:
        """添加 DMI 列"""
        pdi, mdi, adx, adxr = dmi(self._get(self.col_close), self._get(self.col_high),
                                   self._get(self.col_low), n, m)
        self.df['dmi_pdi'] = pdi
        self.df['dmi_mdi'] = mdi
        self.df['dmi_adx'] = adx
        self.df['dmi_adxr'] = adxr
        return self.df

    def add_obv(self) -> pd.DataFrame:
        """添加 OBV 列"""
        self.df['obv'] = obv(self._get(self.col_close), self._get(self.col_volume))
        return self.df

    def add_mfi(self, n: int = 14) -> pd.DataFrame:
        """添加 MFI 列"""
        self.df[f'mfi_{n}'] = mfi(self._get(self.col_close), self._get(self.col_high),
                                   self._get(self.col_low), self._get(self.col_volume), n)
        return self.df

    def add_bbi(self) -> pd.DataFrame:
        """添加 BBI 列"""
        self.df['bbi'] = bbi(self._get(self.col_close))
        return self.df

    def add_sar(self) -> pd.DataFrame:
        """添加 SAR 列"""
        self.df['sar'] = sar(self._get(self.col_high), self._get(self.col_low))
        return self.df

    def add_psy(self, n: int = 12) -> pd.DataFrame:
        """添加 PSY 列"""
        psy_val, mapsy = psy(self._get(self.col_close), n)
        self.df[f'psy_{n}'] = psy_val
        self.df[f'psyma_{n}'] = mapsy
        return self.df

    def add_vr(self, n: int = 26) -> pd.DataFrame:
        """添加 VR 列"""
        self.df[f'vr_{n}'] = vr(self._get(self.col_close), self._get(self.col_volume), n)
        return self.df

    def add_trix(self, n: int = 12, m: int = 9) -> pd.DataFrame:
        """添加 TRIX 列"""
        trix_val, matrix = trix(self._get(self.col_close), n, m)
        self.df[f'trix_{n}'] = trix_val
        self.df[f'trixma_{n}'] = matrix
        return self.df

    def add_roc(self, n: int = 12) -> pd.DataFrame:
        """添加 ROC 列"""
        roc_val, maroc = roc(self._get(self.col_close), n)
        self.df[f'roc_{n}'] = roc_val
        self.df[f'maroc_{n}'] = maroc
        return self.df

    def add_mtm(self, n: int = 12) -> pd.DataFrame:
        """添加 MTM 动量列"""
        mtm_val, mtmma = mtm(self._get(self.col_close), n)
        self.df[f'mtm_{n}'] = mtm_val
        self.df[f'mtmma_{n}'] = mtmma
        return self.df

    def add_expma(self, m1: int = 12, m2: int = 50) -> pd.DataFrame:
        """添加 EXPMA 双线"""
        ema1, ema2 = expma(self._get(self.col_close), m1, m2)
        self.df[f'expma_{m1}'] = ema1
        self.df[f'expma_{m2}'] = ema2
        return self.df

    # ---- 信号生成方法 ----

    def add_ma_cross_signal(self, short: int = 5, long: int = 20) -> pd.DataFrame:
        """添加 MA 金叉死叉信号"""
        buy, sell = ma_cross_signal(self._get(self.col_close), short, long)
        self.df[f'ma_{short}_{long}_buy'] = buy
        self.df[f'ma_{short}_{long}_sell'] = sell
        return self.df

    def add_macd_signal(self) -> pd.DataFrame:
        """添加 MACD 金叉死叉信号"""
        buy, sell = macd_signal(self._get(self.col_close))
        self.df['macd_cross_buy'] = buy
        self.df['macd_cross_sell'] = sell
        return self.df

    def add_kdj_signal(self) -> pd.DataFrame:
        """添加 KDJ 超卖超买信号"""
        self.add_kdj()
        buy, sell = kdj_signal(self._get('kdj_k'), self._get('kdj_d'))
        self.df['kdj_signal_buy'] = buy
        self.df['kdj_signal_sell'] = sell
        return self.df

    def add_boll_signal(self) -> pd.DataFrame:
        """添加布林带突破信号"""
        buy, sell = boll_signal(self._get(self.col_close))
        self.df['boll_signal_buy'] = buy
        self.df['boll_signal_sell'] = sell
        return self.df

    # ---- 批量添加 ----

    def add_all(self) -> pd.DataFrame:
        """一键添加所有常用指标"""
        self.add_ma()
        self.add_rsi()
        self.add_macd()
        self.add_kdj()
        self.add_boll()
        self.add_atr()
        self.add_dmi()
        self.add_obv()
        self.add_bbi()
        self.add_ma_cross_signal()
        self.add_macd_signal()
        self.add_kdj_signal()
        return self.df

    def add_all_oscillators(self) -> pd.DataFrame:
        """添加所有摆动类指标"""
        self.add_rsi()
        self.add_macd()
        self.add_kdj()
        self.add_cci()
        self.add_wr()
        self.add_mfi()
        self.add_roc()
        self.add_mtm()
        self.add_trix()
        return self.df

    def add_all_trend(self) -> pd.DataFrame:
        """添加所有趋势类指标"""
        self.add_ma()
        self.add_boll()
        self.add_dmi()
        self.add_atr()
        self.add_bbi()
        self.add_expma()
        self.add_sar()
        return self.df

    def to_dataframe(self) -> pd.DataFrame:
        """返回带指标的 DataFrame"""
        return self.df


# ============================================================================
# 便捷函数
# ============================================================================

def compute_indicators(df: pd.DataFrame, *indicators: str) -> pd.DataFrame:
    """
    对 DataFrame 批量计算指定指标。

    Args:
        df: 包含 open/high/low/close/volume 的 DataFrame
        *indicators: 要计算的指标名，如 'rsi', 'macd', 'boll', 'all', 'all_osc', 'all_trend'

    Returns:
        添加了指标列的 DataFrame

    Example:
        df = compute_indicators(df, 'rsi', 'macd', 'boll')
        df = compute_indicators(df, 'all')  # 所有常用指标
    """
    calc = IndicatorCalculator(df)
    if 'all' in indicators:
        calc.add_all()
    if 'all_osc' in indicators:
        calc.add_all_oscillators()
    if 'all_trend' in indicators:
        calc.add_all_trend()
    if 'rsi' in indicators:
        calc.add_rsi()
    if 'macd' in indicators:
        calc.add_macd()
    if 'kdj' in indicators:
        calc.add_kdj()
    if 'boll' in indicators:
        calc.add_boll()
    if 'atr' in indicators:
        calc.add_atr()
    if 'cci' in indicators:
        calc.add_cci()
    if 'wr' in indicators:
        calc.add_wr()
    if 'obv' in indicators:
        calc.add_obv()
    if 'dmi' in indicators:
        calc.add_dmi()
    if 'bbi' in indicators:
        calc.add_bbi()
    if 'mfi' in indicators:
        calc.add_mfi()
    return calc.to_dataframe()
