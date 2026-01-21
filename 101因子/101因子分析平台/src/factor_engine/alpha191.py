"""
Alpha191因子实现（部分）
包含Alpha102-Alpha130的部分因子实现
"""
import pandas as pd
import numpy as np
from typing import Dict
from .operators import *


class Alpha191Factors:
    """Alpha191因子计算类"""

    @staticmethod
    def alpha102(data: pd.DataFrame) -> pd.Series:
        """
        Alpha102因子
        公式：((CLOSE - OPEN) / ((HIGH - LOW) + 0.001))
        说明：价格振幅因子
        """
        close = data['close']
        open_ = data['open']
        high = data['high']
        low = data['low']
        return (close - open_) / ((high - low) + 0.001)

    @staticmethod
    def alpha103(data: pd.DataFrame) -> pd.Series:
        """
        Alpha103因子
        公式：(CLOSE - OPEN) / VOLUME
        说明：价格变化与成交量的关系
        """
        close = data['close']
        open_ = data['open']
        volume = data['volume']
        return (close - open_) / volume

    @staticmethod
    def alpha104(data: pd.DataFrame) -> pd.Series:
        """
        Alpha104因子
        公式：-1 * RANK(CORR(RANK(VOLUME), RANK(CLOSE)), 6))
        说明：量价相关性因子（反向）
        """
        volume = data['volume']
        close = data['close']
        return -1 * rank(correlation(rank(volume), rank(close), 6))

    @staticmethod
    def alpha105(data: pd.DataFrame) -> pd.Series:
        """
        Alpha105因子
        公式：-1 * CORR(RANK(VOLUME), RANK(CLOSE)), 10)
        说明：量价相关性因子（10日窗口，反向）
        """
        volume = data['volume']
        close = data['close']
        return -1 * correlation(rank(volume), rank(close), 10)

    @staticmethod
    def alpha106(data: pd.DataFrame) -> pd.Series:
        """
        Alpha106因子
        公式：CLOSE - DELAY(CLOSE, 1)
        说明：当日价格变化
        """
        close = data['close']
        return close - delay(close, 1)

    @staticmethod
    def alpha107(data: pd.DataFrame) -> pd.Series:
        """
        Alpha107因子
        公式：(CLOSE - DELAY(CLOSE, 1)) / DELAY(CLOSE, 1) * 100
        说明：当日收益率（百分比）
        """
        close = data['close']
        return (close - delay(close, 1)) / delay(close, 1) * 100

    @staticmethod
    def alpha108(data: pd.DataFrame) -> pd.Series:
        """
        Alpha108因子
        公式：RANK(CORR(RANK(VOLUME), RANK(OPEN)), 10))
        说明：开盘价与成交量相关性排名
        """
        volume = data['volume']
        open_ = data['open']
        return rank(correlation(rank(volume), rank(open_), 10))

    @staticmethod
    def alpha109(data: pd.DataFrame) -> pd.Series:
        """
        Alpha109因子
        公式：-1 * RANK(CORR(RANK(VOLUME), RANK(HIGH)), 10))
        说明：最高价与成交量相关性排名（反向）
        """
        volume = data['volume']
        high = data['high']
        return -1 * rank(correlation(rank(volume), rank(high), 10))

    @staticmethod
    def alpha110(data: pd.DataFrame) -> pd.Series:
        """
        Alpha110因子
        公式：RANK(CORR(RANK(VOLUME), RANK(LOW)), 10))
        说明：最低价与成交量相关性排名
        """
        volume = data['volume']
        low = data['low']
        return rank(correlation(rank(volume), rank(low), 10))

    @staticmethod
    def alpha111(data: pd.DataFrame) -> pd.Series:
        """
        Alpha111因子
        公式：RANK(VOLUME / DELAY(VOLUME, 1))
        说明：成交量变化排名
        """
        volume = data['volume']
        return rank(volume / delay(volume, 1))

    @staticmethod
    def alpha112(data: pd.DataFrame) -> pd.Series:
        """
        Alpha112因子
        公式：-1 * RANK(CORR(RANK(CLOSE), RANK(VOLUME)), 10))
        说明：收盘价与成交量相关性排名（反向）
        """
        close = data['close']
        volume = data['volume']
        return -1 * rank(correlation(rank(close), rank(volume), 10))

    @staticmethod
    def alpha113(data: pd.DataFrame) -> pd.Series:
        """
        Alpha113因子
        公式：RANK(CORR(RANK(LOW), RANK(VOLUME)), 10))
        说明：最低价与成交量相关性排名
        """
        low = data['low']
        volume = data['volume']
        return rank(correlation(rank(low), rank(volume), 10))

    @staticmethod
    def alpha114(data: pd.DataFrame) -> pd.Series:
        """
        Alpha114因子
        公式：RANK(DELTA(CLOSE, 1)) * -1
        说明：价格变化排名（反向）
        """
        close = data['close']
        return rank(delta(close, 1)) * -1

    @staticmethod
    def alpha115(data: pd.DataFrame) -> pd.Series:
        """
        Alpha115因子
        公式：RANK(DELTA(VOLUME, 1))
        说明：成交量变化排名
        """
        volume = data['volume']
        return rank(delta(volume, 1))

    @staticmethod
    def alpha116(data: pd.DataFrame) -> pd.Series:
        """
        Alpha116因子
        公式：RANK(CLOSE - OPEN)
        说明：开盘跳空排名
        """
        close = data['close']
        open_ = data['open']
        return rank(close - open_)

    @staticmethod
    def alpha117(data: pd.DataFrame) -> pd.Series:
        """
        Alpha117因子
        公式：RANK((HIGH - LOW) / VOLUME)
        说明：价格振幅与成交量比值排名
        """
        high = data['high']
        low = data['low']
        volume = data['volume']
        return rank((high - low) / volume)

    @staticmethod
    def alpha118(data: pd.DataFrame) -> pd.Series:
        """
        Alpha118因子
        公式：RANK(CLOSE / DELAY(CLOSE, 1) - 1)
        说明：收益率排名
        """
        close = data['close']
        return rank(close / delay(close, 1) - 1)

    @staticmethod
    def alpha119(data: pd.DataFrame) -> pd.Series:
        """
        Alpha119因子
        公式：RANK(CORR(CLOSE, DELTA(CLOSE, 1), 5))
        说明：价格自相关性排名
        """
        close = data['close']
        return rank(correlation(close, delta(close, 1), 5))

    @staticmethod
    def alpha120(data: pd.DataFrame) -> pd.Series:
        """
        Alpha120因子
        公式：RANK(CORR(RANK(VOLUME), RANK(VWAP)), 5))
        说明：成交量与VWAP相关性排名
        """
        volume = data['volume']
        vwap = data.get('vwap', data['close'])  # 如果没有vwap，使用close
        return rank(correlation(rank(volume), rank(vwap), 5))

    @staticmethod
    def alpha121(data: pd.DataFrame) -> pd.Series:
        """
        Alpha121因子
        公式：RANK(DELTA(((CLOSE - LOW) - (HIGH - CLOSE)) / (HIGH - LOW), 1))
        说明：价格位置变化排名
        """
        close = data['close']
        low = data['low']
        high = data['high']
        price_pos = ((close - low) - (high - close)) / (high - low)
        return rank(delta(price_pos, 1))

    @staticmethod
    def alpha122(data: pd.DataFrame) -> pd.Series:
        """
        Alpha122因子
        公式：RANK(((HIGH + LOW) / 2 - CLOSE))
        说明：中间价偏离度排名
        """
        high = data['high']
        low = data['low']
        close = data['close']
        return rank(((high + low) / 2 - close))

    @staticmethod
    def alpha123(data: pd.DataFrame) -> pd.Series:
        """
        Alpha123因子
        公式：RANK(HIGH - LOW)
        说明：价格振幅排名
        """
        high = data['high']
        low = data['low']
        return rank(high - low)

    @staticmethod
    def alpha124(data: pd.DataFrame) -> pd.Series:
        """
        Alpha124因子
        公式：RANK(CLOSE / OPEN - 1)
        说明：开盘收益率排名
        """
        close = data['close']
        open_ = data['open']
        return rank(close / open_ - 1)

    @staticmethod
    def alpha125(data: pd.DataFrame) -> pd.Series:
        """
        Alpha125因子
        公式：RANK(DELTA(CLOSE, 5))
        说明：5日价格变化排名
        """
        close = data['close']
        return rank(delta(close, 5))

    @staticmethod
    def alpha126(data: pd.DataFrame) -> pd.Series:
        """
        Alpha126因子
        公式：RANK(CLOSE / DELAY(CLOSE, 5) - 1)
        说明：5日收益率排名
        """
        close = data['close']
        return rank(close / delay(close, 5) - 1)

    @staticmethod
    def alpha127(data: pd.DataFrame) -> pd.Series:
        """
        Alpha127因子
        公式：RANK((CLOSE - DELAY(CLOSE, 10)) / DELAY(CLOSE, 10))
        说明：10日收益率排名
        """
        close = data['close']
        return rank((close - delay(close, 10)) / delay(close, 10))

    @staticmethod
    def alpha128(data: pd.DataFrame) -> pd.Series:
        """
        Alpha128因子
        公式：RANK(DELTA(VOLUME, 5))
        说明：5日成交量变化排名
        """
        volume = data['volume']
        return rank(delta(volume, 5))

    @staticmethod
    def alpha129(data: pd.DataFrame) -> pd.Series:
        """
        Alpha129因子
        公式：RANK(CORR(CLOSE, VOLUME, 10))
        说明：收盘价与成交量相关性排名
        """
        close = data['close']
        volume = data['volume']
        return rank(correlation(close, volume, 10))

    @staticmethod
    def alpha130(data: pd.DataFrame) -> pd.Series:
        """
        Alpha130因子
        公式：RANK((CLOSE - OPEN) / ((HIGH - LOW) + 0.001)) * RANK(VOLUME)
        说明：价格振幅与成交量综合排名
        """
        close = data['close']
        open_ = data['open']
        high = data['high']
        low = data['low']
        volume = data['volume']
        price_range = (close - open_) / ((high - low) + 0.001)
        return rank(price_range) * rank(volume)

    @staticmethod
    def alpha131(data: pd.DataFrame) -> pd.Series:
        """
        Alpha131因子
        公式：RANK(DELTA(CLOSE, 3) / DELAY(CLOSE, 3))
        说明：3日收益率排名
        """
        close = data['close']
        return rank(delta(close, 3) / delay(close, 3))

    @staticmethod
    def alpha132(data: pd.DataFrame) -> pd.Series:
        """
        Alpha132因子
        公式：RANK(STDDEV(RETURNS, 20))
        说明：20日收益率波动率排名
        """
        close = data['close']
        returns = close.pct_change()
        return rank(stddev(returns, 20))

    @staticmethod
    def alpha133(data: pd.DataFrame) -> pd.Series:
        """
        Alpha133因子
        公式：RANK(CORR(RANK(OPEN), RANK(VOLUME)), 10)) * -1
        说明：开盘价与成交量相关性排名（反向）
        """
        open_ = data['open']
        volume = data['volume']
        return rank(correlation(rank(open_), rank(volume), 10)) * -1

    @staticmethod
    def alpha134(data: pd.DataFrame) -> pd.Series:
        """
        Alpha134因子
        公式：RANK(CLOSE - TS_MIN(CLOSE, 10))
        说明：收盘价与10日最小值距离排名
        """
        close = data['close']
        return rank(close - ts_min(close, 10))

    @staticmethod
    def alpha135(data: pd.DataFrame) -> pd.Series:
        """
        Alpha135因子
        公式：RANK(TS_MAX(CLOSE, 10) - CLOSE)
        说明：10日最大值与收盘价距离排名
        """
        close = data['close']
        return rank(ts_max(close, 10) - close)

    @staticmethod
    def alpha136(data: pd.DataFrame) -> pd.Series:
        """
        Alpha136因子
        公式：RANK((HIGH - LOW) / CLOSE)
        说明：价格振幅与收盘价比值排名
        """
        high = data['high']
        low = data['low']
        close = data['close']
        return rank((high - low) / close)

    @staticmethod
    def alpha137(data: pd.DataFrame) -> pd.Series:
        """
        Alpha137因子
        公式：RANK(VOLUME / MEAN(VOLUME, 20))
        说明：量比排名
        """
        volume = data['volume']
        return rank(volume / sma(volume, 20))

    @staticmethod
    def alpha138(data: pd.DataFrame) -> pd.Series:
        """
        Alpha138因子
        公式：RANK(DELTA((CLOSE - OPEN), 5))
        说明：5日开盘跳空变化排名
        """
        close = data['close']
        open_ = data['open']
        return rank(delta((close - open_), 5))

    @staticmethod
    def alpha139(data: pd.DataFrame) -> pd.Series:
        """
        Alpha139因子
        公式：RANK(CORR(DELTA(CLOSE, 1), DELTA(VOLUME, 1), 10))
        说明：价格与成交量变化相关性排名
        """
        close = data['close']
        volume = data['volume']
        return rank(correlation(delta(close, 1), delta(volume, 1), 10))

    @staticmethod
    def alpha140(data: pd.DataFrame) -> pd.Series:
        """
        Alpha140因子
        公式：RANK(DELTA(CLOSE, 7) * (1 - RANK(DECAY_LINEAR(VOLUME / MEAN(VOLUME, 20), 9))))
        说明：价格变化与衰减权重成交量综合因子
        """
        close = data['close']
        volume = data['volume']
        mean_volume = sma(volume, 20)
        decay_vol = decay_linear(volume / mean_volume, 9)
        return rank(delta(close, 7) * (1 - rank(decay_vol)))

    @staticmethod
    def alpha141(data: pd.DataFrame) -> pd.Series:
        """
        Alpha141因子
        公式：RANK(CLOSE - DELAY(CLOSE, 5))
        说明：5日价格变化排名
        """
        close = data['close']
        return rank(close - delay(close, 5))

    @staticmethod
    def alpha142(data: pd.DataFrame) -> pd.Series:
        """
        Alpha142因子
        公式：RANK((HIGH - LOW) / VOLUME)
        说明：价格振幅与成交量比值排名
        """
        high = data['high']
        low = data['low']
        volume = data['volume']
        return rank((high - low) / volume)

    @staticmethod
    def alpha143(data: pd.DataFrame) -> pd.Series:
        """
        Alpha143因子
        公式：RANK(CLOSE / DELAY(CLOSE, 1) - 1)
        说明：日收益率排名
        """
        close = data['close']
        return rank(close / delay(close, 1) - 1)

    @staticmethod
    def alpha144(data: pd.DataFrame) -> pd.Series:
        """
        Alpha144因子
        公式：RANK(CORR(RANK(VOLUME), RANK(CLOSE)), 10)) * -1
        说明：量价相关性排名（反向）
        """
        volume = data['volume']
        close = data['close']
        return rank(correlation(rank(volume), rank(close), 10)) * -1

    @staticmethod
    def alpha145(data: pd.DataFrame) -> pd.Series:
        """
        Alpha145因子
        公式：RANK(DELTA(VOLUME, 10))
        说明：10日成交量变化排名
        """
        volume = data['volume']
        return rank(delta(volume, 10))

    @staticmethod
    def alpha146(data: pd.DataFrame) -> pd.Series:
        """
        Alpha146因子
        公式：RANK(DELTA(CLOSE, 10))
        说明：10日价格变化排名
        """
        close = data['close']
        return rank(delta(close, 10))

    @staticmethod
    def alpha147(data: pd.DataFrame) -> pd.Series:
        """
        Alpha147因子
        公式：RANK((CLOSE - OPEN) / (HIGH - LOW + 0.001))
        说明：价格位置因子排名
        """
        close = data['close']
        open_ = data['open']
        high = data['high']
        low = data['low']
        return rank((close - open_) / (high - low + 0.001))

    @staticmethod
    def alpha148(data: pd.DataFrame) -> pd.Series:
        """
        Alpha148因子
        公式：RANK(CLOSE / OPEN - 1)
        说明：开盘收益率排名
        """
        close = data['close']
        open_ = data['open']
        return rank(close / open_ - 1)

    @staticmethod
    def alpha149(data: pd.DataFrame) -> pd.Series:
        """
        Alpha149因子
        公式：RANK(DELTA((CLOSE - OPEN), 1))
        说明：开盘跳空变化排名
        """
        close = data['close']
        open_ = data['open']
        return rank(delta((close - open_), 1))

    @staticmethod
    def alpha150(data: pd.DataFrame) -> pd.Series:
        """
        Alpha150因子
        公式：RANK(CORR(RANK(HIGH), RANK(VOLUME)), 5))
        说明：最高价与成交量相关性排名
        """
        high = data['high']
        volume = data['volume']
        return rank(correlation(rank(high), rank(volume), 5))




    @staticmethod
    def alpha151(data: pd.DataFrame) -> pd.Series:
        """
        alpha151因子
        公式：SMA(CLOSE-DELAY(CLOSE,20),20,1)
        """
        sma(data['close']-delay(data['close'],20),20,1)
    @staticmethod
    def alpha152(data: pd.DataFrame) -> pd.Series:
        """
        alpha152因子
        公式：SMA(MEAN(DELAY(SMA(DELAY(CLOSE/DELAY(CLOSE,9),1),9,1),1),12)-MEAN(DELAY(SMA(DELAY(CLOSE/DELAY(CLOSE,9),1),9,1),1),26),9,1)
        """
        sma(sma(delay(sma(delay(data['close']/delay(data['close'],9),1),9,1),1),12)-sma(delay(sma(delay(data['close']/delay(data['close'],9),1),9,1),1),26),9,1)
    @staticmethod
    def alpha153(data: pd.DataFrame) -> pd.Series:
        """
        alpha153因子
        公式：(MEAN(CLOSE,3)+MEAN(CLOSE,6)+MEAN(CLOSE,12)+MEAN(CLOSE,24))/4
        """
        (sma(data['close'],3)+sma(data['close'],6)+sma(data['close'],12)+sma(data['close'],24))/4
    @staticmethod
    def alpha154(data: pd.DataFrame) -> pd.Series:
        """
        alpha154因子
        公式：(((VWAP - MIN(VWAP, 16))) < (CORR(VWAP, MEAN(VOLUME,180), 18)))
        """
        part
    @staticmethod
    def alpha155(data: pd.DataFrame) -> pd.Series:
        """
        alpha155因子
        公式：SMA(VOLUME,13,2)-SMA(VOLUME,27,2)-SMA(SMA(VOLUME,13,2)-SMA(VOLUME,27,2),10,2)
        """
        sma(data['volume'],13,2)-sma(data['volume'],27,2)-sma(sma(data['volume'],13,2)-sma(data['volume'],27,2),10,2)
    @staticmethod
    def alpha156(data: pd.DataFrame) -> pd.Series:
        """
        alpha156因子
        公式：(MAX(RANK(DECAYLINEAR(DELTA(VWAP, 5), 3)), RANK(DECAYLINEAR(((DELTA(((OPEN * 0.15) + (LOW *0.85)),2) / ((OPEN * 0.15) + (LOW * 0.85))) * -1), 3))) * -1)
        """
        (Max(rank(Decaylinear(Delta(data.get('vwap', data['close']), 5), 3)), rank(Decaylinear(((Delta(((data['open'] * 0.15) + (data['low'] *0.85)),2) / ((data['open'] * 0.15) + (data['low'] * 0.85))) * -1), 3))) * -1)
    @staticmethod
    def alpha157(data: pd.DataFrame) -> pd.Series:
        """
        alpha157因子
        公式：(MIN(PROD(RANK(RANK(LOG(SUM(TSMIN(RANK(RANK((-1 * RANK(DELTA((CLOSE - 1), 5))))), 2), 1)))), 1), 5) + TSRANK(DELAY((-1 * RET), 6), 5))
        """
        (ts_min(Prod(rank(rank(Log(Sum(ts_min(rank(rank((-1 * rank(Delta((data['close'] - 1), 5))))), 2), 1)))), 1), 5) + ts_rank(delay((-1 * self.returns), 6), 5))
    @staticmethod
    def alpha158(data: pd.DataFrame) -> pd.Series:
        """
        alpha158因子
        公式：((HIGH-SMA(CLOSE,15,2))-(LOW-SMA(CLOSE,15,2)))/CLOSE
        """
        ((data['high']-sma(data['close'],15,2))-(data['low']-sma(data['close'],15,2)))/data['close']
    @staticmethod
    def alpha159(data: pd.DataFrame) -> pd.Series:
        """
        alpha159因子
        公式：((CLOSE-SUM(MIN(LOW,DELAY(CLOSE,1)),6))/SUM(MAX(HGIH,DELAY(CLOSE,1))-MIN(LOW,DELAY(CLOSE,1)),6)*12*24+(CLOSE-SUM(MIN(LOW,DELAY(CLOSE,1)),12))/SUM(MAX(HGIH,DELAY(CLOSE,1))-MIN(LOW,DELAY(CLOSE,1)),12)*6*24+(CLOSE-SUM(MIN(LOW,DELAY(CLOSE,1)),24))/SUM(MAX(HGIH,DELAY(CLOSE,1))-MIN(LOW,DELAY(CLOSE,1)),24)*6*24)*100/(6*12+6*24+12*24)
        """
        ((data['close']-Sum(Min(data['low'],delay(data['close'],1)),6))/Sum(Max(data['high'],delay(data['close'],1))-Min(data['low'],delay(data['close'],1)),6)*12*24+(data['close']-Sum(Min(data['low'],delay(data['close'],1)),12))/Sum(Max(data['high'],delay(data['close'],1))-Min(data['low'],delay(data['close'],1)),12)*6*24+(data['close']-Sum(Min(data['low'],delay(data['close'],1)),24))/Sum(Max(data['high'],delay(data['close'],1))-Min(data['low'],delay(data['close'],1)),24)*6*24)*100/(6*12+6*24+12*24)
    @staticmethod
    def alpha160(data: pd.DataFrame) -> pd.Series:
        """
        alpha160因子
        公式：SMA((CLOSE<=DELAY(CLOSE,1)?STD(CLOSE,20):0),20,1)
        """
        sma(part, 20, 1)
    @staticmethod
    def alpha161(data: pd.DataFrame) -> pd.Series:
        """
        alpha161因子
        公式：MEAN(MAX(MAX((HIGH-LOW),ABS(DELAY(CLOSE,1)-HIGH)),ABS(DELAY(CLOSE,1)-LOW)),12)
        """
        sma(Max(Max((data['high']-data['low']),abs(delay(data['close'],1)-data['high'])),abs(delay(data['close'],1)-data['low'])),12)
    @staticmethod
    def alpha162(data: pd.DataFrame) -> pd.Series:
        """
        alpha162因子
        公式：(SMA(MAX(CLOSE-DELAY(CLOSE,1),0),12,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),12,1)*100-MIN(SMA(MAX(CLOSE-DELAY(CLOSE,1),0),12,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),12,1)*100,12))/(MAX(SMA(MAX(CLOSE-DELAY(CLOSE,1),0),12,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),12,1)*100,12)-MIN(SMA(MAX(CLOSE-DELAY(CLOSE,1),0),12,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),12,1)*100,12))
        """
        (sma(Max(data['close']-delay(data['close'],1),0),12,1)/sma(abs(data['close']-delay(data['close'],1)),12,1)*100-ts_min(sma(Max(data['close']-delay(data['close'],1),0),12,1)/sma(abs(data['close']-delay(data['close'],1)),12,1)*100,12))/(sma(sma(Max(data['close']-delay(data['close'],1),0),12,1)/sma(abs(data['close']-delay(data['close'],1)),12,1)*100,12,1)-ts_min(sma(Max(data['close']-delay(data['close'],1),0),12,1)/sma(abs(data['close']-delay(data['close'],1)),12,1)*100,12))
    @staticmethod
    def alpha163(data: pd.DataFrame) -> pd.Series:
        """
        alpha163因子
        公式：RANK(((((-1 * RET) * MEAN(VOLUME,20)) * VWAP) * (HIGH - CLOSE)))
        """
        rank(((((-1 * self.returns) * sma(data['volume'],20)) * data.get('vwap', data['close'])) * (data['high'] - data['close'])))
    @staticmethod
    def alpha164(data: pd.DataFrame) -> pd.Series:
        """
        alpha164因子
        公式：SMA(( ((CLOSE>DELAY(CLOSE,1))?1/(CLOSE-DELAY(CLOSE,1)):1) - MIN( ((CLOSE>DELAY(CLOSE,1))?1/(CLOSE-DELAY(CLOSE,1)):1) ,12) )/(HIGH-LOW)*100,13,2)
        """
        sma((part - ts_min(part,12))/(part2)*100, 13, 2)
    @staticmethod
    def alpha165(data: pd.DataFrame) -> pd.Series:
        """
        alpha165因子
        公式：MAX(SUMAC(CLOSE-MEAN(CLOSE,48)))-MIN(SUMAC(CLOSE-MEAN(CLOSE,48)))/STD(CLOSE,48)
        """
        -1*(1/p3.div(p2, axis = 0)).sub(p1, axis=0)
    @staticmethod
    def alpha166(data: pd.DataFrame) -> pd.Series:
        """
        alpha166因子
        公式：
        """
        p1/p2
    @staticmethod
    def alpha167(data: pd.DataFrame) -> pd.Series:
        """
        alpha167因子
        公式：SUM((CLOSE-DELAY(CLOSE,1)>0?CLOSE-DELAY(CLOSE,1):0),12)
        """
        Sum(part,12)
    @staticmethod
    def alpha168(data: pd.DataFrame) -> pd.Series:
        """
        alpha168因子
        公式：(-1*VOLUME/MEAN(VOLUME,20))
        """
        (-1*data['volume']/sma(data['volume'],20))
    @staticmethod
    def alpha169(data: pd.DataFrame) -> pd.Series:
        """
        alpha169因子
        公式：SMA(MEAN(DELAY(SMA(CLOSE-DELAY(CLOSE,1),9,1),1),12)-MEAN(DELAY(SMA(CLOSE-DELAY(CLOSE,1),9,1),1),26),10,1)
        """
        sma(sma(delay(sma(data['close']-delay(data['close'],1),9,1),1),12)-sma(delay(sma(data['close']-delay(data['close'],1),9,1),1),26),10,1)
    @staticmethod
    def alpha170(data: pd.DataFrame) -> pd.Series:
        """
        alpha170因子
        公式：((((RANK((1 / CLOSE)) * VOLUME) / MEAN(VOLUME,20)) * ((HIGH * RANK((HIGH - CLOSE))) / (SUM(HIGH, 5) /5))) - RANK((VWAP - DELAY(VWAP, 5))))
        """
        ((((rank((1 / data['close'])) * data['volume']) / sma(data['volume'],20)) * ((data['high'] * rank((data['high'] - data['close']))) / (Sum(data['high'], 5) /5))) - rank((data.get('vwap', data['close']) - delay(data.get('vwap', data['close']), 5))))
    @staticmethod
    def alpha171(data: pd.DataFrame) -> pd.Series:
        """
        alpha171因子
        公式：((-1 * ((LOW - CLOSE) * (OPEN^5))) / ((CLOSE - HIGH) * (CLOSE^5)))
        """
        ((-1 * ((data['low'] - data['close']) * (data['open']**5))) / ((data['close'] - data['high']) * (data['close']**5)))
    @staticmethod
    def alpha172(data: pd.DataFrame) -> pd.Series:
        """
        alpha172因子
        公式：
        """
        sma(abs(Sum(part1,14)*100/Sum(TR,14)-Sum(part2,14)*100/Sum(TR,14))/(Sum(part1,14)*100/Sum(TR,14)+Sum(part2,14)*100/Sum(TR,14))*100,6)
    @staticmethod
    def alpha173(data: pd.DataFrame) -> pd.Series:
        """
        alpha173因子
        公式：3*SMA(CLOSE,13,2)-2*SMA(SMA(CLOSE,13,2),13,2)+SMA(SMA(SMA(LOG(CLOSE),13,2),13,2),13,2)
        """
        3*sma(data['close'],13,2)-2*sma(sma(data['close'],13,2),13,2)+sma(sma(sma(Log(data['close']),13,2),13,2),13,2)
    @staticmethod
    def alpha174(data: pd.DataFrame) -> pd.Series:
        """
        alpha174因子
        公式：SMA((CLOSE>DELAY(CLOSE,1)?STD(CLOSE,20):0),20,1)
        """
        sma(part,20,1)
    @staticmethod
    def alpha175(data: pd.DataFrame) -> pd.Series:
        """
        alpha175因子
        公式：MEAN(MAX(MAX((HIGH-LOW),ABS(DELAY(CLOSE,1)-HIGH)),ABS(DELAY(CLOSE,1)-LOW)),6)
        """
        sma(Max(Max((data['high']-data['low']),abs(delay(data['close'],1)-data['high'])),abs(delay(data['close'],1)-data['low'])),6)
    @staticmethod
    def alpha176(data: pd.DataFrame) -> pd.Series:
        """
        alpha176因子
        公式：CORR(RANK(((CLOSE - TSMIN(LOW, 12)) / (TSMAX(HIGH, 12) - TSMIN(LOW,12)))), RANK(VOLUME), 6)
        """
        correlation(rank(((data['close'] - ts_min(data['low'], 12)) / (ts_max(data['high'], 12) - ts_min(data['low'],12)))), rank(data['volume']), 6)
    @staticmethod
    def alpha177(data: pd.DataFrame) -> pd.Series:
        """
        alpha177因子
        公式：((20-HIGHDAY(HIGH,20))/20)*100
        """
        ((20-Highday(data['high'],20))/20)*100
    @staticmethod
    def alpha178(data: pd.DataFrame) -> pd.Series:
        """
        alpha178因子
        公式：(CLOSE-DELAY(CLOSE,1))/DELAY(CLOSE,1)*VOLUME
        """
        (data['close']-delay(data['close'],1))/delay(data['close'],1)*data['volume']
    @staticmethod
    def alpha179(data: pd.DataFrame) -> pd.Series:
        """
        alpha179因子
        公式：(RANK(CORR(VWAP, VOLUME, 4)) *RANK(CORR(RANK(LOW), RANK(MEAN(VOLUME,50)), 12)))
        """
        (rank(correlation(data.get('vwap', data['close']), data['volume'], 4)) *rank(correlation(rank(data['low']), rank(sma(data['volume'],50)), 12)))
    @staticmethod
    def alpha180(data: pd.DataFrame) -> pd.Series:
        """
        alpha180因子
        公式：
        """
        part
    @staticmethod
    def alpha181(data: pd.DataFrame) -> pd.Series:
        """
        alpha181因子
        公式：SUM(((CLOSE/DELAY(CLOSE,1)-1)-MEAN((CLOSE/DELAY(CLOSE,1)-1),20))-(BANCHMARKINDEXCLOSE-MEAN(BANCHMARKINDEXCLOSE,20))^2,20)/SUM((BANCHMARKINDEXCLOSE-MEAN(BANCHMARKINDEXCLOSE,20))^3)
        """
        Sum(((data['close']/delay(data['close'],1)-1)-sma((data['close']/delay(data['close'],1)-1),20))-(self.benchmark_close-sma(self.benchmark_close,20))**2,20)/Sum(((self.benchmark_close-sma(self.benchmark_close,20))**3),20)
    @staticmethod
    def alpha182(data: pd.DataFrame) -> pd.Series:
        """
        alpha182因子
        公式：COUNT((CLOSE>OPEN & BANCHMARKINDEXCLOSE>BANCHMARKINDEXOPEN)OR(CLOSE<OPEN & BANCHMARKINDEXCLOSE<BANCHMARKINDEXOPEN),20)/20
        """
        Count((((data['close']>data['open']) & (self.benchmark_close>self.benchmark_open)) | ((data['close']<data['open']) & (self.benchmark_close<self.benchmark_open))),20)/20
    @staticmethod
    def alpha183(data: pd.DataFrame) -> pd.Series:
        """
        alpha183因子
        公式：
        """
        -1*(1/p3.div(p2, axis = 0)).sub(p1, axis=0)
    @staticmethod
    def alpha184(data: pd.DataFrame) -> pd.Series:
        """
        alpha184因子
        公式：(RANK(CORR(DELAY((OPEN - CLOSE), 1), CLOSE, 200)) + RANK((OPEN - CLOSE)))
        """
        (rank(correlation(delay((data['open'] - data['close']), 1), data['close'], 200)) + rank((data['open'] - data['close'])))
    @staticmethod
    def alpha185(data: pd.DataFrame) -> pd.Series:
        """
        alpha185因子
        公式：RANK((-1 * ((1 - (OPEN / CLOSE))^2)))
        """
        rank((-1 * ((1 - (data['open'] / data['close']))**2)))
    @staticmethod
    def alpha186(data: pd.DataFrame) -> pd.Series:
        """
        alpha186因子
        公式：
        """
        (sma(abs(Sum(part1,14)*100/Sum(TR,14)-Sum(part2,14)*100/Sum(TR,14))/(Sum(part1,14)*100/Sum(TR,14)+Sum(part2,14)*100/Sum(TR,14))*100,6)+delay(sma(abs(Sum(part1,14)*100/Sum(TR,14)-Sum(part2,14)*100/Sum(TR,14))/(Sum(part1,14)*100/Sum(TR,14)+Sum(part2,14)*100/Sum(TR,14))*100,6),6))/2
    @staticmethod
    def alpha187(data: pd.DataFrame) -> pd.Series:
        """
        alpha187因子
        公式：SUM((OPEN<=DELAY(OPEN,1)?0:MAX((HIGH-OPEN),(OPEN-DELAY(OPEN,1)))),20)
        """
        Sum(part,20)
    @staticmethod
    def alpha188(data: pd.DataFrame) -> pd.Series:
        """
        alpha188因子
        公式：((HIGH-LOW–SMA(HIGH-LOW,11,2))/SMA(HIGH-LOW,11,2))*100
        """
        ((data['high']-data['low']-sma(data['high']-data['low'],11,2))/sma(data['high']-data['low'],11,2))*100
    @staticmethod
    def alpha189(data: pd.DataFrame) -> pd.Series:
        """
        alpha189因子
        公式：MEAN(ABS(CLOSE-MEAN(CLOSE,6)),6)
        """
        sma(abs(data['close']-sma(data['close'],6)),6)
    @staticmethod
    def alpha190(data: pd.DataFrame) -> pd.Series:
        """
        alpha190因子
        公式：
        """
        0
    @staticmethod
    def alpha191(data: pd.DataFrame) -> pd.Series:
        """
        alpha191因子
        公式：((CORR(MEAN(VOLUME,20), LOW, 5) + ((HIGH + LOW) / 2)) - CLOSE)
        """
        ((correlation(sma(data['volume'],20), data['low'], 5) + ((data['high'] + data['low']) / 2)) - data['close'])

def calculate_alpha191_factor(data: pd.DataFrame, factor_name: str) -> pd.Series:
    """
    计算指定的Alpha191因子

    Args:
        data: 包含OHLCV数据的DataFrame
        factor_name: 因子名称（如'alpha102'）

    Returns:
        pd.Series: 因子值
    """
    factor_class = Alpha191Factors()

    # 动态调用因子方法
    if hasattr(factor_class, factor_name):
        method = getattr(factor_class, factor_name)
        return method(data)
    else:
        raise ValueError(f"不支持的因子: {factor_name}")


# 获取所有可用的Alpha191因子列表
def get_alpha191_factors_list() -> list:
    """获取所有可用的Alpha191因子名称列表"""
    return [name for name in dir(Alpha191Factors) if name.startswith('alpha')]
