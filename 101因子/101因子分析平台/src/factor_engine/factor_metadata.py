"""
Alpha101因子元数据
包含因子的公式、说明和解释
"""

# Alpha101因子元数据 (alpha001-alpha020)
ALPHA101_METADATA = {
    "alpha001": {
        "name": "ALPHA001",
        "formula": "(rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5)) -0.5)",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha002": {
        "name": "ALPHA002",
        "formula": "(-1 * correlation(rank(delta(log(volume), 2)), rank(((close - open) / open)), 6))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha003": {
        "name": "ALPHA003",
        "formula": "(-1 * correlation(rank(open), rank(volume), 10))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha004": {
        "name": "ALPHA004",
        "formula": "(-1 * Ts_Rank(rank(low), 9))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha005": {
        "name": "ALPHA005",
        "formula": "(rank((open - (sum(vwap, 10) / 10))) * (-1 * abs(rank((close - vwap)))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha006": {
        "name": "ALPHA006",
        "formula": "(-1 * correlation(open, volume, 10))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha007": {
        "name": "ALPHA007",
        "formula": "((adv20 < volume) ? ((-1 * ts_rank(abs(delta(close, 7)), 60)) * sign(delta(close, 7))) : (-1* 1))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha008": {
        "name": "ALPHA008",
        "formula": "(-1 * rank(((sum(open, 5) * sum(returns, 5)) - delay((sum(open, 5) * sum(returns, 5)),10))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha009": {
        "name": "ALPHA009",
        "formula": "((0 < ts_min(delta(close, 1), 5)) ? delta(close, 1) : ((ts_max(delta(close, 1), 5) < 0) ?delta(close, 1) : (-1 * delta(close, 1))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha010": {
        "name": "ALPHA010",
        "formula": "rank(((0 < ts_min(delta(close, 1), 4)) ? delta(close, 1) : ((ts_max(delta(close, 1), 4) < 0)? delta(close, 1) : (-1 * delta(close, 1)))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha011": {
        "name": "ALPHA011",
        "formula": "((rank(ts_max((vwap - close), 3)) + rank(ts_min((vwap - close), 3))) *rank(delta(volume, 3)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha012": {
        "name": "ALPHA012",
        "formula": "(sign(delta(volume, 1)) * (-1 * delta(close, 1)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha013": {
        "name": "ALPHA013",
        "formula": "(-1 * rank(covariance(rank(close), rank(volume), 5)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha014": {
        "name": "ALPHA014",
        "formula": "((-1 * rank(delta(returns, 3))) * correlation(open, volume, 10))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha015": {
        "name": "ALPHA015",
        "formula": "(-1 * sum(rank(correlation(rank(high), rank(volume), 3)), 3))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha016": {
        "name": "ALPHA016",
        "formula": "(-1 * rank(covariance(rank(high), rank(volume), 5)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha017": {
        "name": "ALPHA017",
        "formula": "(((-1 * rank(ts_rank(close, 10))) * rank(delta(delta(close, 1), 1))) *rank(ts_rank((volume / adv20), 5)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha018": {
        "name": "ALPHA018",
        "formula": "(-1 * rank(((stddev(abs((close - open)), 5) + (close - open)) + correlation(close, open,10))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha019": {
        "name": "ALPHA019",
        "formula": "((-1 * sign(((close - delay(close, 7)) + delta(close, 7)))) * (1 + rank((1 + sum(returns,250)))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha020": {
        "name": "ALPHA020",
        "formula": "(((-1 * rank((open - delay(high, 1)))) * rank((open - delay(close, 1)))) * rank((open -delay(low, 1))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha021": {
        "name": "ALPHA021",
        "formula": "((((sum(close, 8) / 8) + stddev(close, 8)) < (sum(close, 2) / 2)) ? (-1 * 1) : (((sum(close,2) / 2) < ((sum(close, 8) / 8) - stddev(close, 8))) ? 1 : (((1 < (volume / adv20)) || ((volume /adv20) == 1)) ? 1 : (-1 * 1))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha022": {
        "name": "ALPHA022",
        "formula": "(-1 * (delta(correlation(high, volume, 5), 5) * rank(stddev(close, 20))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha023": {
        "name": "ALPHA023",
        "formula": "(((sum(high, 20) / 20) < high) ? (-1 * delta(high, 2)) : 0)",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha024": {
        "name": "ALPHA024",
        "formula": "((((delta((sum(close, 100) / 100), 100) / delay(close, 100)) < 0.05) ||((delta((sum(close, 100) / 100), 100) / delay(close, 100)) == 0.05)) ? (-1 * (close - ts_min(close,100))) : (-1 * delta(close, 3)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha025": {
        "name": "ALPHA025",
        "formula": "rank(((((-1 * returns) * adv20) * vwap) * (high - close)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha026": {
        "name": "ALPHA026",
        "formula": "(-1 * ts_max(correlation(ts_rank(volume, 5), ts_rank(high, 5), 5), 3))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha027": {
        "name": "ALPHA027",
        "formula": "((0.5 < rank((sum(correlation(rank(volume), rank(vwap), 6), 2) / 2.0))) ? (-1 * 1) : 1)",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha028": {
        "name": "ALPHA028",
        "formula": "scale(((correlation(adv20, low, 5) + ((high + low) / 2)) - close))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha029": {
        "name": "ALPHA029",
        "formula": "(min(product(rank(rank(scale(log(sum(ts_min(rank(rank((-1 * rank(delta((close - 1),5))))), 2), 1))))), 1), 5) + ts_rank(delay((-1 * returns), 6), 5))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha030": {
        "name": "ALPHA030",
        "formula": "(((1.0 - rank(((sign((close - delay(close, 1))) + sign((delay(close, 1) - delay(close, 2)))) +sign((delay(close, 2) - delay(close, 3)))))) * sum(volume, 5)) / sum(volume, 20))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha031": {
        "name": "ALPHA031",
        "formula": "((rank(rank(rank(decay_linear((-1 * rank(rank(delta(close, 10)))), 10)))) + rank((-1 *delta(close, 3)))) + sign(scale(correlation(adv20, low, 12))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha032": {
        "name": "ALPHA032",
        "formula": "(scale(((sum(close, 7) / 7) - close)) + (20 * scale(correlation(vwap, delay(close, 5),230))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha033": {
        "name": "ALPHA033",
        "formula": "rank((-1 * ((1 - (open / close))^1)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha034": {
        "name": "ALPHA034",
        "formula": "rank(((1 - rank((stddev(returns, 2) / stddev(returns, 5)))) + (1 - rank(delta(close, 1)))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha035": {
        "name": "ALPHA035",
        "formula": "((Ts_Rank(volume, 32) * (1 - Ts_Rank(((close + high) - low), 16))) * (1 -Ts_Rank(returns, 32)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha036": {
        "name": "ALPHA036",
        "formula": "(((((2.21 * rank(correlation((close - open), delay(volume, 1), 15))) + (0.7 * rank((open- close)))) + (0.73 * rank(Ts_Rank(delay((-1 * returns), 6), 5)))) + rank(abs(correlation(vwap,adv20, 6)))) + (0.6 * rank((((sum(close, 200) / 200) - open) * (close - open)))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha037": {
        "name": "ALPHA037",
        "formula": "(rank(correlation(delay((open - close), 1), close, 200)) + rank((open - close)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha038": {
        "name": "ALPHA038",
        "formula": "((-1 * rank(Ts_Rank(close, 10))) * rank((close / open)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha039": {
        "name": "ALPHA039",
        "formula": "((-1 * rank((delta(close, 7) * (1 - rank(decay_linear((volume / adv20), 9)))))) * (1 +rank(sum(returns, 250))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha040": {
        "name": "ALPHA040",
        "formula": "((-1 * rank(stddev(high, 10))) * correlation(high, volume, 10))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha041": {
        "name": "ALPHA041",
        "formula": "(((high * low)^0.5) - vwap)",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha042": {
        "name": "ALPHA042",
        "formula": "(rank((vwap - close)) / rank((vwap + close)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha043": {
        "name": "ALPHA043",
        "formula": "(ts_rank((volume / adv20), 20) * ts_rank((-1 * delta(close, 7)), 8))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha044": {
        "name": "ALPHA044",
        "formula": "(-1 * correlation(high, rank(volume), 5))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha045": {
        "name": "ALPHA045",
        "formula": "(-1 * ((rank((sum(delay(close, 5), 20) / 20)) * correlation(close, volume, 2)) *rank(correlation(sum(close, 5), sum(close, 20), 2))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha046": {
        "name": "ALPHA046",
        "formula": "((0.25 < (((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10))) ?(-1 * 1) : (((((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10)) < 0) ? 1 :((-1 * 1) * (close - delay(close, 1)))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha047": {
        "name": "ALPHA047",
        "formula": "((((rank((1 / close)) * volume) / adv20) * ((high * rank((high - close))) / (sum(high, 5) /5))) - rank((vwap - delay(vwap, 5))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha048": {
        "name": "ALPHA048",
        "formula": "(-1*((RANK(((SIGN((CLOSE - DELAY(CLOSE, 1))) + SIGN((DELAY(CLOSE, 1) - DELAY(CLOSE, 2)))) + SIGN((DELAY(CLOSE, 2) - DELAY(CLOSE, 3)))))) * SUM(VOLUME, 5)) / SUM(VOLUME, 20))",
        "description": "WorldQuant Alpha048因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha049": {
        "name": "ALPHA049",
        "formula": "(((((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10)) < (-1 *0.1)) ? 1 : ((-1 * 1) * (close - delay(close, 1))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha050": {
        "name": "ALPHA050",
        "formula": "(-1 * ts_max(rank(correlation(rank(volume), rank(vwap), 5)), 5))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha051": {
        "name": "ALPHA051",
        "formula": "(((((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10)) < (-1 *0.05)) ? 1 : ((-1 * 1) * (close - delay(close, 1))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha052": {
        "name": "ALPHA052",
        "formula": "((((-1 * ts_min(low, 5)) + delay(ts_min(low, 5), 5)) * rank(((sum(returns, 240) -sum(returns, 20)) / 220))) * ts_rank(volume, 5))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha053": {
        "name": "ALPHA053",
        "formula": "(-1 * delta((((close - low) - (high - close)) / (close - low)), 9))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha054": {
        "name": "ALPHA054",
        "formula": "((-1 * ((low - close) * (open^5))) / ((low - high) * (close^5)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha055": {
        "name": "ALPHA055",
        "formula": "(-1 * correlation(rank(((close - ts_min(low, 12)) / (ts_max(high, 12) - ts_min(low,12)))), rank(volume), 6))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha056": {
        "name": "ALPHA056",
        "formula": "(RANK((OPEN - TSMIN(OPEN, 12))) < RANK((RANK(CORR(SUM(((HIGH + LOW) / 2), 19),SUM(MEAN(VOLUME,40), 19), 13))^5)))",
        "description": "WorldQuant Alpha056因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha057": {
        "name": "ALPHA057",
        "formula": "(0 - (1 * ((close - vwap) / decay_linear(rank(ts_argmax(close, 30)), 2))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha058": {
        "name": "ALPHA058",
        "formula": "COUNT(CLOSE>DELAY(CLOSE,1),20)/20*100",
        "description": "WorldQuant Alpha058因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha059": {
        "name": "ALPHA059",
        "formula": "SUM((CLOSE=DELAY(CLOSE,1)?0:CLOSE-(CLOSE>DELAY(CLOSE,1)?MIN(LOW,DELAY(CLOSE,1)):MAX(HIGH,DELAY(CLOSE,1)))),20)",
        "description": "WorldQuant Alpha059因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha060": {
        "name": "ALPHA060",
        "formula": "(0 - (1 * ((2 * scale(rank(((((close - low) - (high - close)) / (high - low)) * volume)))) -scale(rank(ts_argmax(close, 10))))))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha061": {
        "name": "ALPHA061",
        "formula": "(rank((vwap - ts_min(vwap, 16.1219))) < rank(correlation(vwap, adv180, 17.9282)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha062": {
        "name": "ALPHA062",
        "formula": "((rank(correlation(vwap, sum(adv20, 22.4101), 9.91009)) < rank(((rank(open) +rank(open)) < (rank(((high + low) / 2)) + rank(high))))) * -1)",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha063": {
        "name": "ALPHA063",
        "formula": "SMA(MAX(CLOSE-DELAY(CLOSE,1),0),6,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),6,1)*100",
        "description": "WorldQuant Alpha063因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha064": {
        "name": "ALPHA064",
        "formula": "((rank(correlation(sum(((open * 0.178404) + (low * (1 - 0.178404))), 12.7054),sum(adv120, 12.7054), 16.6208)) < rank(delta(((((high + low) / 2) * 0.178404) + (vwap * (1 -0.178404))), 3.69741))) * -1)",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha065": {
        "name": "ALPHA065",
        "formula": "((rank(correlation(((open * 0.00817205) + (vwap * (1 - 0.00817205))), sum(adv60,8.6911), 6.40374)) < rank((open - ts_min(open, 13.635)))) * -1)",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha066": {
        "name": "ALPHA066",
        "formula": "((rank(decay_linear(delta(vwap, 3.51013), 7.23052)) + Ts_Rank(decay_linear(((((low* 0.96633) + (low * (1 - 0.96633))) - vwap) / (open - ((high + low) / 2))), 11.4157), 6.72611)) * -1)",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha067": {
        "name": "ALPHA067",
        "formula": "SMA(MAX(CLOSE-DELAY(CLOSE,1),0),24,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),24,1)*100",
        "description": "WorldQuant Alpha067因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha068": {
        "name": "ALPHA068",
        "formula": "SMA(((HIGH+LOW)/2-(DELAY(HIGH,1)+DELAY(LOW,1))/2)*(HIGH-LOW)/VOLUME,15,2)",
        "description": "WorldQuant Alpha068因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha069": {
        "name": "ALPHA069",
        "formula": "(SUM(DTM,20)>SUM(DBM,20)? (SUM(DTM,20)-SUM(DBM,20))/SUM(DTM,20): (SUM(DTM,20)=SUM(DBM,20)?0: (SUM(DTM,20)-SUM(DBM,20))/SUM(DBM,20)))",
        "description": "WorldQuant Alpha069因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha070": {
        "name": "ALPHA070",
        "formula": "STD(AMOUNT,6)",
        "description": "WorldQuant Alpha070因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha071": {
        "name": "ALPHA071",
        "formula": "max(Ts_Rank(decay_linear(correlation(Ts_Rank(close, 3.43976), Ts_Rank(adv180,12.0647), 18.0175), 4.20501), 15.6948), Ts_Rank(decay_linear((rank(((low + open) - (vwap +vwap)))^2), 16.4662), 4.4388))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha072": {
        "name": "ALPHA072",
        "formula": "(rank(decay_linear(correlation(((high + low) / 2), adv40, 8.93345), 10.1519)) /rank(decay_linear(correlation(Ts_Rank(vwap, 3.72469), Ts_Rank(volume, 18.5188), 6.86671),2.95011)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha073": {
        "name": "ALPHA073",
        "formula": "(max(rank(decay_linear(delta(vwap, 4.72775), 2.91864)),Ts_Rank(decay_linear(((delta(((open * 0.147155) + (low * (1 - 0.147155))), 2.03608) / ((open *0.147155) + (low * (1 - 0.147155)))) * -1), 3.33829), 16.7411)) * -1)",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha074": {
        "name": "ALPHA074",
        "formula": "((rank(correlation(close, sum(adv30, 37.4843), 15.1365)) <rank(correlation(rank(((high * 0.0261661) + (vwap * (1 - 0.0261661)))), rank(volume), 11.4791)))* -1)",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha075": {
        "name": "ALPHA075",
        "formula": "(rank(correlation(vwap, volume, 4.24304)) < rank(correlation(rank(low), rank(adv50),12.4413)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha076": {
        "name": "ALPHA076",
        "formula": "STD(ABS((CLOSE/DELAY(CLOSE,1)-1))/VOLUME,20)/MEAN(ABS((CLOSE/DELAY(CLOSE,1)-1))/VOLUME,20)",
        "description": "WorldQuant Alpha076因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha077": {
        "name": "ALPHA077",
        "formula": "min(rank(decay_linear(((((high + low) / 2) + high) - (vwap + high)), 20.0451)),rank(decay_linear(correlation(((high + low) / 2), adv40, 3.1614), 5.64125)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha078": {
        "name": "ALPHA078",
        "formula": "(rank(correlation(sum(((low * 0.352233) + (vwap * (1 - 0.352233))), 19.7428),sum(adv40, 19.7428), 6.83313))^rank(correlation(rank(vwap), rank(volume), 5.77492)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha079": {
        "name": "ALPHA079",
        "formula": "SMA(MAX(CLOSE-DELAY(CLOSE,1),0),12,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),12,1)*100",
        "description": "WorldQuant Alpha079因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha080": {
        "name": "ALPHA080",
        "formula": "(VOLUME-DELAY(VOLUME,5))/DELAY(VOLUME,5)*100",
        "description": "WorldQuant Alpha080因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha081": {
        "name": "ALPHA081",
        "formula": "((rank(Log(product(rank((rank(correlation(vwap, sum(adv10, 49.6054),8.47743))^4)), 14.9655))) < rank(correlation(rank(vwap), rank(volume), 5.07914))) * -1)",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha082": {
        "name": "ALPHA082",
        "formula": "SMA((TSMAX(HIGH,6)-CLOSE)/(TSMAX(HIGH,6)-TSMIN(LOW,6))*100,20,1)",
        "description": "WorldQuant Alpha082因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha083": {
        "name": "ALPHA083",
        "formula": "((rank(delay(((high - low) / (sum(close, 5) / 5)), 2)) * rank(rank(volume))) / (((high -low) / (sum(close, 5) / 5)) / (vwap - close)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha084": {
        "name": "ALPHA084",
        "formula": "SignedPower(Ts_Rank((vwap - ts_max(vwap, 15.3217)), 20.7127), delta(close,4.96796))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha085": {
        "name": "ALPHA085",
        "formula": "(rank(correlation(((high * 0.876703) + (close * (1 - 0.876703))), adv30,9.61331))^rank(correlation(Ts_Rank(((high + low) / 2), 3.70596), Ts_Rank(volume, 10.1595),7.11408)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha086": {
        "name": "ALPHA086",
        "formula": "((Ts_Rank(correlation(close, sum(adv20, 14.7444), 6.00049), 20.4195) < rank(((open+ close) - (vwap + open)))) * -1)",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha087": {
        "name": "ALPHA087",
        "formula": "((RANK(DECAYLINEAR(DELTA(VWAP, 4), 7)) + TSRANK(DECAYLINEAR(((((LOW * 0.9) + (LOW * 0.1)) - VWAP) /(OPEN - ((HIGH + LOW) / 2))), 11), 7)) * -1)",
        "description": "WorldQuant Alpha087因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha088": {
        "name": "ALPHA088",
        "formula": "min(rank(decay_linear(((rank(open) + rank(low)) - (rank(high) + rank(close))),8.06882)), Ts_Rank(decay_linear(correlation(Ts_Rank(close, 8.44728), Ts_Rank(adv60,20.6966), 8.01266), 6.65053), 2.61957))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha089": {
        "name": "ALPHA089",
        "formula": "2*(SMA(CLOSE,13,2)-SMA(CLOSE,27,2)-SMA(SMA(CLOSE,13,2)-SMA(CLOSE,27,2),10,2))",
        "description": "WorldQuant Alpha089因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha090": {
        "name": "ALPHA090",
        "formula": "(RANK(CORR(RANK(VWAP), RANK(VOLUME), 5)) * -1)",
        "description": "WorldQuant Alpha090因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha091": {
        "name": "ALPHA091",
        "formula": "((RANK((CLOSE - MAX(CLOSE, 5)))*RANK(CORR((MEAN(VOLUME,40)), LOW, 5))) * -1)",
        "description": "WorldQuant Alpha091因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha092": {
        "name": "ALPHA092",
        "formula": "min(Ts_Rank(decay_linear(((((high + low) / 2) + close) < (low + open)), 14.7221),18.8683), Ts_Rank(decay_linear(correlation(rank(low), rank(adv30), 7.58555), 6.94024),6.80584))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha093": {
        "name": "ALPHA093",
        "formula": "SUM((OPEN>=DELAY(OPEN,1)?0:MAX((OPEN-LOW),(OPEN-DELAY(OPEN,1)))),20)",
        "description": "WorldQuant Alpha093因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha094": {
        "name": "ALPHA094",
        "formula": "((rank((vwap - ts_min(vwap, 11.5783)))^Ts_Rank(correlation(Ts_Rank(vwap,19.6462), Ts_Rank(adv60, 4.02992), 18.0926), 2.70756)) * -1)",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha095": {
        "name": "ALPHA095",
        "formula": "(rank((open - ts_min(open, 12.4105))) < Ts_Rank((rank(correlation(sum(((high + low)/ 2), 19.1351), sum(adv40, 19.1351), 12.8742))^5), 11.7584))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha096": {
        "name": "ALPHA096",
        "formula": "(max(Ts_Rank(decay_linear(correlation(rank(vwap), rank(volume), 3.83878),4.16783), 8.38151), Ts_Rank(decay_linear(Ts_ArgMax(correlation(Ts_Rank(close, 7.45404),Ts_Rank(adv60, 4.13242), 3.65459), 12.6556), 14.0365), 13.4143)) * -1)",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha097": {
        "name": "ALPHA097",
        "formula": "STD(VOLUME,10)",
        "description": "WorldQuant Alpha097因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha098": {
        "name": "ALPHA098",
        "formula": "(rank(decay_linear(correlation(vwap, sum(adv5, 26.4719), 4.58418), 7.18088)) -rank(decay_linear(Ts_Rank(Ts_ArgMin(correlation(rank(open), rank(adv15), 20.8187), 8.62571),6.95668), 8.07206)))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha099": {
        "name": "ALPHA099",
        "formula": "((rank(correlation(sum(((high + low) / 2), 19.8975), sum(adv60, 19.8975), 8.8136)) <rank(correlation(low, volume, 6.28259))) * -1)",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha100": {
        "name": "ALPHA100",
        "formula": "Std(self.volume,20)",
        "description": "WorldQuant Alpha100因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha101": {
        "name": "ALPHA101",
        "formula": "((close - open) / ((high - low) + .001))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    }
}

# Alpha191因子元数据 (alpha102-alpha191)
ALPHA191_METADATA = {
    "alpha102": {
        "name": "ALPHA102",
        "formula": "((CLOSE - OPEN) / ((HIGH - LOW) + 0.001))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha103": {
        "name": "ALPHA103",
        "formula": "(CLOSE - OPEN) / VOLUME",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha104": {
        "name": "ALPHA104",
        "formula": "-1 * RANK(CORR(RANK(VOLUME), RANK(CLOSE)), 6))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha105": {
        "name": "ALPHA105",
        "formula": "-1 * CORR(RANK(VOLUME), RANK(CLOSE)), 10)",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha106": {
        "name": "ALPHA106",
        "formula": "CLOSE - DELAY(CLOSE, 1)",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha107": {
        "name": "ALPHA107",
        "formula": "(CLOSE - DELAY(CLOSE, 1)) / DELAY(CLOSE, 1) * 100",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha108": {
        "name": "ALPHA108",
        "formula": "RANK(CORR(RANK(VOLUME), RANK(OPEN)), 10))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha109": {
        "name": "ALPHA109",
        "formula": "-1 * RANK(CORR(RANK(VOLUME), RANK(HIGH)), 10))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha110": {
        "name": "ALPHA110",
        "formula": "RANK(CORR(RANK(VOLUME), RANK(LOW)), 10))",
        "description": "基于价格动量的因子",
        "logic": "基于价格、成交量等市场数据计算的动量类因子",
        "category": "动量类",
        "author": "WorldQuant",
        "icon": "⚡"
    },
    "alpha111": {
        "name": "ALPHA111",
        "formula": "RANK(VOLUME / DELAY(VOLUME, 1))",
        "description": "结合成交量和价格的因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "💹"
    },
    "alpha112": {
        "name": "ALPHA112",
        "formula": "-1 * RANK(CORR(RANK(CLOSE), RANK(VOLUME)), 10))",
        "description": "结合成交量和价格的因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "💹"
    },
    "alpha113": {
        "name": "ALPHA113",
        "formula": "RANK(CORR(RANK(LOW), RANK(VOLUME)), 10))",
        "description": "结合成交量和价格的因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "💹"
    },
    "alpha114": {
        "name": "ALPHA114",
        "formula": "RANK(DELTA(CLOSE, 1)) * -1",
        "description": "结合成交量和价格的因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "💹"
    },
    "alpha115": {
        "name": "ALPHA115",
        "formula": "RANK(DELTA(VOLUME, 1))",
        "description": "结合成交量和价格的因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "💹"
    },
    "alpha116": {
        "name": "ALPHA116",
        "formula": "RANK(CLOSE - OPEN)",
        "description": "结合成交量和价格的因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "💹"
    },
    "alpha117": {
        "name": "ALPHA117",
        "formula": "RANK((HIGH - LOW) / VOLUME)",
        "description": "结合成交量和价格的因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "💹"
    },
    "alpha118": {
        "name": "ALPHA118",
        "formula": "RANK(CLOSE / DELAY(CLOSE, 1) - 1)",
        "description": "结合成交量和价格的因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "💹"
    },
    "alpha119": {
        "name": "ALPHA119",
        "formula": "RANK(CORR(CLOSE, DELTA(CLOSE, 1), 5))",
        "description": "结合成交量和价格的因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "💹"
    },
    "alpha120": {
        "name": "ALPHA120",
        "formula": "RANK(CORR(RANK(VOLUME), RANK(VWAP)), 5))",
        "description": "结合成交量和价格的因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "💹"
    },
    "alpha121": {
        "name": "ALPHA121",
        "formula": "RANK(DELTA(((CLOSE - LOW) - (HIGH - CLOSE)) / (HIGH - LOW), 1))",
        "description": "结合成交量和价格的因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "💹"
    },
    "alpha122": {
        "name": "ALPHA122",
        "formula": "RANK(((HIGH + LOW) / 2 - CLOSE))",
        "description": "结合成交量和价格的因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "💹"
    },
    "alpha123": {
        "name": "ALPHA123",
        "formula": "RANK(HIGH - LOW)",
        "description": "结合成交量和价格的因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "💹"
    },
    "alpha124": {
        "name": "ALPHA124",
        "formula": "RANK(CLOSE / OPEN - 1)",
        "description": "结合成交量和价格的因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "💹"
    },
    "alpha125": {
        "name": "ALPHA125",
        "formula": "RANK(DELTA(CLOSE, 5))",
        "description": "结合成交量和价格的因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "💹"
    },
    "alpha126": {
        "name": "ALPHA126",
        "formula": "RANK(CLOSE / DELAY(CLOSE, 5) - 1)",
        "description": "结合成交量和价格的因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "💹"
    },
    "alpha127": {
        "name": "ALPHA127",
        "formula": "RANK((CLOSE - DELAY(CLOSE, 10)) / DELAY(CLOSE, 10))",
        "description": "结合成交量和价格的因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "💹"
    },
    "alpha128": {
        "name": "ALPHA128",
        "formula": "RANK(DELTA(VOLUME, 5))",
        "description": "结合成交量和价格的因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "💹"
    },
    "alpha129": {
        "name": "ALPHA129",
        "formula": "RANK(CORR(CLOSE, VOLUME, 10))",
        "description": "结合成交量和价格的因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "💹"
    },
    "alpha130": {
        "name": "ALPHA130",
        "formula": "RANK((CLOSE - OPEN) / ((HIGH - LOW) + 0.001)) * RANK(VOLUME)",
        "description": "结合成交量和价格的因子",
        "logic": "基于价格、成交量等市场数据计算的量价类因子",
        "category": "量价类",
        "author": "WorldQuant",
        "icon": "💹"
    },
    "alpha131": {
        "name": "ALPHA131",
        "formula": "RANK(DELTA(CLOSE, 3) / DELAY(CLOSE, 3))",
        "description": "识别价格趋势的因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha132": {
        "name": "ALPHA132",
        "formula": "RANK(STDDEV(RETURNS, 20))",
        "description": "识别价格趋势的因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha133": {
        "name": "ALPHA133",
        "formula": "RANK(CORR(RANK(OPEN), RANK(VOLUME)), 10)) * -1",
        "description": "识别价格趋势的因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha134": {
        "name": "ALPHA134",
        "formula": "RANK(CLOSE - TS_MIN(CLOSE, 10))",
        "description": "识别价格趋势的因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha135": {
        "name": "ALPHA135",
        "formula": "RANK(TS_MAX(CLOSE, 10) - CLOSE)",
        "description": "识别价格趋势的因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha136": {
        "name": "ALPHA136",
        "formula": "RANK((HIGH - LOW) / CLOSE)",
        "description": "识别价格趋势的因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha137": {
        "name": "ALPHA137",
        "formula": "RANK(VOLUME / MEAN(VOLUME, 20))",
        "description": "识别价格趋势的因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha138": {
        "name": "ALPHA138",
        "formula": "RANK(DELTA((CLOSE - OPEN), 5))",
        "description": "识别价格趋势的因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha139": {
        "name": "ALPHA139",
        "formula": "RANK(CORR(DELTA(CLOSE, 1), DELTA(VOLUME, 1), 10))",
        "description": "识别价格趋势的因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha140": {
        "name": "ALPHA140",
        "formula": "RANK(DELTA(CLOSE, 7) * (1 - RANK(DECAY_LINEAR(VOLUME / MEAN(VOLUME, 20), 9))))",
        "description": "识别价格趋势的因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha141": {
        "name": "ALPHA141",
        "formula": "RANK(CLOSE - DELAY(CLOSE, 5))",
        "description": "识别价格趋势的因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha142": {
        "name": "ALPHA142",
        "formula": "RANK((HIGH - LOW) / VOLUME)",
        "description": "识别价格趋势的因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha143": {
        "name": "ALPHA143",
        "formula": "RANK(CLOSE / DELAY(CLOSE, 1) - 1)",
        "description": "识别价格趋势的因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha144": {
        "name": "ALPHA144",
        "formula": "RANK(CORR(RANK(VOLUME), RANK(CLOSE)), 10)) * -1",
        "description": "识别价格趋势的因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha145": {
        "name": "ALPHA145",
        "formula": "RANK(DELTA(VOLUME, 10))",
        "description": "识别价格趋势的因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha146": {
        "name": "ALPHA146",
        "formula": "RANK(DELTA(CLOSE, 10))",
        "description": "识别价格趋势的因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha147": {
        "name": "ALPHA147",
        "formula": "RANK((CLOSE - OPEN) / (HIGH - LOW + 0.001))",
        "description": "识别价格趋势的因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha148": {
        "name": "ALPHA148",
        "formula": "RANK(CLOSE / OPEN - 1)",
        "description": "识别价格趋势的因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha149": {
        "name": "ALPHA149",
        "formula": "RANK(DELTA((CLOSE - OPEN), 1))",
        "description": "识别价格趋势的因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha150": {
        "name": "ALPHA150",
        "formula": "RANK(CORR(RANK(HIGH), RANK(VOLUME)), 5))",
        "description": "识别价格趋势的因子",
        "logic": "基于价格、成交量等市场数据计算的趋势类因子",
        "category": "趋势类",
        "author": "WorldQuant",
        "icon": "📈"
    },
    "alpha151": {
        "name": "ALPHA151",
        "formula": "SMA(CLOSE-DELAY(CLOSE,20),20,1)",
        "description": "基于价格波动率的因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "〰️"
    },
    "alpha152": {
        "name": "ALPHA152",
        "formula": "SMA(MEAN(DELAY(SMA(DELAY(CLOSE/DELAY(CLOSE,9),1),9,1),1),12)-MEAN(DELAY(SMA(DELAY(CLOSE/DELAY(CLOSE,9),1),9,1),1),26),9,1)",
        "description": "基于价格波动率的因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "〰️"
    },
    "alpha153": {
        "name": "ALPHA153",
        "formula": "(MEAN(CLOSE,3)+MEAN(CLOSE,6)+MEAN(CLOSE,12)+MEAN(CLOSE,24))/4",
        "description": "基于价格波动率的因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "〰️"
    },
    "alpha154": {
        "name": "ALPHA154",
        "formula": "(((VWAP - MIN(VWAP, 16))) < (CORR(VWAP, MEAN(VOLUME,180), 18)))",
        "description": "基于价格波动率的因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "〰️"
    },
    "alpha155": {
        "name": "ALPHA155",
        "formula": "SMA(VOLUME,13,2)-SMA(VOLUME,27,2)-SMA(SMA(VOLUME,13,2)-SMA(VOLUME,27,2),10,2)",
        "description": "基于价格波动率的因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "〰️"
    },
    "alpha156": {
        "name": "ALPHA156",
        "formula": "(MAX(RANK(DECAYLINEAR(DELTA(VWAP, 5), 3)), RANK(DECAYLINEAR(((DELTA(((OPEN * 0.15) + (LOW *0.85)),2) / ((OPEN * 0.15) + (LOW * 0.85))) * -1), 3))) * -1)",
        "description": "基于价格波动率的因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "〰️"
    },
    "alpha157": {
        "name": "ALPHA157",
        "formula": "(MIN(PROD(RANK(RANK(LOG(SUM(TSMIN(RANK(RANK((-1 * RANK(DELTA((CLOSE - 1), 5))))), 2), 1)))), 1), 5) + TSRANK(DELAY((-1 * RET), 6), 5))",
        "description": "基于价格波动率的因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "〰️"
    },
    "alpha158": {
        "name": "ALPHA158",
        "formula": "((HIGH-SMA(CLOSE,15,2))-(LOW-SMA(CLOSE,15,2)))/CLOSE",
        "description": "基于价格波动率的因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "〰️"
    },
    "alpha159": {
        "name": "ALPHA159",
        "formula": "((CLOSE-SUM(MIN(LOW,DELAY(CLOSE,1)),6))/SUM(MAX(HGIH,DELAY(CLOSE,1))-MIN(LOW,DELAY(CLOSE,1)),6)*12*24+(CLOSE-SUM(MIN(LOW,DELAY(CLOSE,1)),12))/SUM(MAX(HGIH,DELAY(CLOSE,1))-MIN(LOW,DELAY(CLOSE,1)),12)*6*24+(CLOSE-SUM(MIN(LOW,DELAY(CLOSE,1)),24))/SUM(MAX(HGIH,DELAY(CLOSE,1))-MIN(LOW,DELAY(CLOSE,1)),24)...",
        "description": "基于价格波动率的因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "〰️"
    },
    "alpha160": {
        "name": "ALPHA160",
        "formula": "SMA((CLOSE<=DELAY(CLOSE,1)?STD(CLOSE,20):0),20,1)",
        "description": "基于价格波动率的因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "〰️"
    },
    "alpha161": {
        "name": "ALPHA161",
        "formula": "MEAN(MAX(MAX((HIGH-LOW),ABS(DELAY(CLOSE,1)-HIGH)),ABS(DELAY(CLOSE,1)-LOW)),12)",
        "description": "基于价格波动率的因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "〰️"
    },
    "alpha162": {
        "name": "ALPHA162",
        "formula": "(SMA(MAX(CLOSE-DELAY(CLOSE,1),0),12,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),12,1)*100-MIN(SMA(MAX(CLOSE-DELAY(CLOSE,1),0),12,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),12,1)*100,12))/(MAX(SMA(MAX(CLOSE-DELAY(CLOSE,1),0),12,1)/SMA(ABS(CLOSE-DELAY(CLOSE,1)),12,1)*100,12)-MIN(SMA(MAX(CLOSE-DELAY(CLOSE,1),0),12,1)/SMA(A...",
        "description": "基于价格波动率的因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "〰️"
    },
    "alpha163": {
        "name": "ALPHA163",
        "formula": "RANK(((((-1 * RET) * MEAN(VOLUME,20)) * VWAP) * (HIGH - CLOSE)))",
        "description": "基于价格波动率的因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "〰️"
    },
    "alpha164": {
        "name": "ALPHA164",
        "formula": "SMA(( ((CLOSE>DELAY(CLOSE,1))?1/(CLOSE-DELAY(CLOSE,1)):1) - MIN( ((CLOSE>DELAY(CLOSE,1))?1/(CLOSE-DELAY(CLOSE,1)):1) ,12) )/(HIGH-LOW)*100,13,2)",
        "description": "基于价格波动率的因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "〰️"
    },
    "alpha165": {
        "name": "ALPHA165",
        "formula": "MAX(SUMAC(CLOSE-MEAN(CLOSE,48)))-MIN(SUMAC(CLOSE-MEAN(CLOSE,48)))/STD(CLOSE,48)",
        "description": "基于价格波动率的因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "〰️"
    },
    "alpha166": {
        "name": "ALPHA166",
        "formula": "-20* ( 20-1 ) ^1.5*SUM(CLOSE/DELAY(CLOSE,1)-1-MEAN(CLOSE/DELAY(CLOSE,1)-1,20),20)/((20-1)*(20-2)(SUM((CLOSE/DELAY(CLOSE,1),20)^2,20))^1.5)         p1 = -20* ( 20-1 )**1.5*Sum(self.close/Delay(self.close,1)-1-Mean(self.close/Delay(self.close,1)-1,20),20)         p2 = ((20-1)*(20-2)*(Sum(Mean(self.clo...",
        "description": "基于价格波动率的因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "〰️"
    },
    "alpha167": {
        "name": "ALPHA167",
        "formula": "SUM((CLOSE-DELAY(CLOSE,1)>0?CLOSE-DELAY(CLOSE,1):0),12)",
        "description": "基于价格波动率的因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "〰️"
    },
    "alpha168": {
        "name": "ALPHA168",
        "formula": "(-1*VOLUME/MEAN(VOLUME,20))",
        "description": "基于价格波动率的因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "〰️"
    },
    "alpha169": {
        "name": "ALPHA169",
        "formula": "SMA(MEAN(DELAY(SMA(CLOSE-DELAY(CLOSE,1),9,1),1),12)-MEAN(DELAY(SMA(CLOSE-DELAY(CLOSE,1),9,1),1),26),10,1)",
        "description": "基于价格波动率的因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "〰️"
    },
    "alpha170": {
        "name": "ALPHA170",
        "formula": "((((RANK((1 / CLOSE)) * VOLUME) / MEAN(VOLUME,20)) * ((HIGH * RANK((HIGH - CLOSE))) / (SUM(HIGH, 5) /5))) - RANK((VWAP - DELAY(VWAP, 5))))",
        "description": "基于价格波动率的因子",
        "logic": "基于价格、成交量等市场数据计算的波动率类因子",
        "category": "波动率类",
        "author": "WorldQuant",
        "icon": "〰️"
    },
    "alpha171": {
        "name": "ALPHA171",
        "formula": "((-1 * ((LOW - CLOSE) * (OPEN^5))) / ((CLOSE - HIGH) * (CLOSE^5)))",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    },
    "alpha172": {
        "name": "ALPHA172",
        "formula": "MEAN(ABS(SUM((LD>0 & LD>HD)?LD:0,14)*100/SUM(TR,14)-SUM((HD>0 &HD>LD)?HD:0,14)*100/SUM(TR,14))/(SUM((LD>0 & LD>HD)?LD:0,14)*100/SUM(TR,14)+SUM((HD>0 &HD>LD)?HD:0,14)*100/SUM(TR,14))*100,6)         TR = Max(Max(self.high-self.low,Abs(self.high-Delay(self.close,1))),Abs(self.low-Delay(self.close,1))) ...",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    },
    "alpha173": {
        "name": "ALPHA173",
        "formula": "3*SMA(CLOSE,13,2)-2*SMA(SMA(CLOSE,13,2),13,2)+SMA(SMA(SMA(LOG(CLOSE),13,2),13,2),13,2)",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    },
    "alpha174": {
        "name": "ALPHA174",
        "formula": "SMA((CLOSE>DELAY(CLOSE,1)?STD(CLOSE,20):0),20,1)",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    },
    "alpha175": {
        "name": "ALPHA175",
        "formula": "MEAN(MAX(MAX((HIGH-LOW),ABS(DELAY(CLOSE,1)-HIGH)),ABS(DELAY(CLOSE,1)-LOW)),6)",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    },
    "alpha176": {
        "name": "ALPHA176",
        "formula": "CORR(RANK(((CLOSE - TSMIN(LOW, 12)) / (TSMAX(HIGH, 12) - TSMIN(LOW,12)))), RANK(VOLUME), 6)",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    },
    "alpha177": {
        "name": "ALPHA177",
        "formula": "((20-HIGHDAY(HIGH,20))/20)*100",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    },
    "alpha178": {
        "name": "ALPHA178",
        "formula": "(CLOSE-DELAY(CLOSE,1))/DELAY(CLOSE,1)*VOLUME",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    },
    "alpha179": {
        "name": "ALPHA179",
        "formula": "(RANK(CORR(VWAP, VOLUME, 4)) *RANK(CORR(RANK(LOW), RANK(MEAN(VOLUME,50)), 12)))",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    },
    "alpha180": {
        "name": "ALPHA180",
        "formula": "((MEAN(VOLUME,20) < VOLUME) ? ((-1 * TSRANK(ABS(DELTA(CLOSE, 7)), 60)) * SIGN(DELTA(CLOSE, 7)) : (-1 *VOLUME)))         cond = (Mean(self.volume,20) < self.volume)         part = self.close.copy(deep=True)         part.loc[:, :] = None         part[cond] = (-1 * Tsrank(Abs(Delta(self.close, 7)), 60)...",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    },
    "alpha181": {
        "name": "ALPHA181",
        "formula": "SUM(((CLOSE/DELAY(CLOSE,1)-1)-MEAN((CLOSE/DELAY(CLOSE,1)-1),20))-(BANCHMARKINDEXCLOSE-MEAN(BANCHMARKINDEXCLOSE,20))^2,20)/SUM((BANCHMARKINDEXCLOSE-MEAN(BANCHMARKINDEXCLOSE,20))^3)",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    },
    "alpha182": {
        "name": "ALPHA182",
        "formula": "COUNT((CLOSE>OPEN & BANCHMARKINDEXCLOSE>BANCHMARKINDEXOPEN)OR(CLOSE<OPEN & BANCHMARKINDEXCLOSE<BANCHMARKINDEXOPEN),20)/20",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    },
    "alpha183": {
        "name": "ALPHA183",
        "formula": "(RANK(CORR(DELAY((OPEN - CLOSE), 1), CLOSE, 200)) + RANK((OPEN - CLOSE)))",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    },
    "alpha184": {
        "name": "ALPHA184",
        "formula": "(RANK(CORR(DELAY((OPEN - CLOSE), 1), CLOSE, 200)) + RANK((OPEN - CLOSE)))",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    },
    "alpha185": {
        "name": "ALPHA185",
        "formula": "RANK((-1 * ((1 - (OPEN / CLOSE))^2)))",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    },
    "alpha186": {
        "name": "ALPHA186",
        "formula": "(MEAN(ABS(SUM((LD>0 & LD>HD)?LD:0,14)*100/SUM(TR,14)-SUM((HD>0 & HD>LD)?HD:0,14)*100/SUM(TR,14))/(SUM((LD>0 & LD>HD)?LD:0,14)*100/SUM(TR,14)+SUM((HD>0 & HD>LD)?HD:0,14)*100/SUM(TR,14))*100,6)+DELAY(MEAN(ABS(SUM((LD>0 & LD>HD)?LD:0,14)*100/SUM(TR,14)-SUM((HD>0 & HD>LD)?HD:0,14)*100/SUM(TR,14))/(SUM((...",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    },
    "alpha187": {
        "name": "ALPHA187",
        "formula": "SUM((OPEN<=DELAY(OPEN,1)?0:MAX((HIGH-OPEN),(OPEN-DELAY(OPEN,1)))),20)",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    },
    "alpha188": {
        "name": "ALPHA188",
        "formula": "((HIGH-LOW–SMA(HIGH-LOW,11,2))/SMA(HIGH-LOW,11,2))*100",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    },
    "alpha189": {
        "name": "ALPHA189",
        "formula": "MEAN(ABS(CLOSE-MEAN(CLOSE,6)),6)",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    },
    "alpha190": {
        "name": "ALPHA190",
        "formula": "LOG((COUNT( CLOSE/DELAY(CLOSE,1)>((CLOSE/DELAY(CLOSE,19))^(1/20)-1) ,20)-1)*(SUMIF((CLOSE/DELAY(CLOSE,1)-((CLOSE/DELAY(CLOSE,19))^(1/20)-1))^2,20,CLOSE/DELAY(CLOSE,1)<(CLOSE/DELAY(CLOSE,19))^(1/20)-1))/((COUNT((CLOSE/DELAY(CLOSE,1)<(CLOSE/DELAY(CLOSE,19))^(1/20)-1),20))*(SUMIF((CLOSE/DELAY(CLOSE,1)-...",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    },
    "alpha191": {
        "name": "ALPHA191",
        "formula": "((CORR(MEAN(VOLUME,20), LOW, 5) + ((HIGH + LOW) / 2)) - CLOSE)",
        "description": "高级复合因子",
        "logic": "基于价格、成交量等市场数据计算的高级因子类因子",
        "category": "高级因子类",
        "author": "WorldQuant",
        "icon": "⭐"
    }
}
ALL_FACTORS_METADATA = {**ALPHA101_METADATA, **ALPHA191_METADATA}


def get_factor_info(factor_name: str) -> dict:
    """
    获取因子信息

    Args:
        factor_name: 因子名称，如 'alpha001'

    Returns:
        dict: 因子信息字典，包含 name, formula, description, logic, category, author, icon
    """
    # 从所有因子元数据中查找
    info = ALL_FACTORS_METADATA.get(factor_name, {
        "name": factor_name,
        "formula": "暂无公式",
        "description": "暂无描述",
        "logic": "暂无逻辑说明",
        "category": "未分类",
        "author": "未知"
    })

    # 如果没有icon，根据分类自动添加
    if 'icon' not in info:
        category_icons = {
            "动量类": "📈",
            "量价类": "📊",
            "趋势类": "📉",
            "均值回归类": "🔄",
            "波动率类": "🌊",
            "成交量类": "📦",
            "未分类": "📊"
        }
        info['icon'] = category_icons.get(info.get('category', '未分类'), '📊')

    return info


def list_all_factors() -> list:
    """列出所有可用的因子（包括Alpha101和Alpha191）"""
    return sorted(ALL_FACTORS_METADATA.keys())
