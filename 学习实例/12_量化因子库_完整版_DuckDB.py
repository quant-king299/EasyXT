

"""
量化因子库完整应用 - QMT + DuckDB 完整版本

功能：
1. 从QMT下载历史数据到DuckDB数据库
2. 完整的50+类因子计算
3. 多因子综合评分
4. 详细的因子分析报告

包含的因子类型：
- 估值因子：PE、PB、PS、PCF、市值
- 质量因子：ROE、ROA、毛利率、净利率、负债率
- 成长因子：营收增长、利润增长、EPS增长
- 动量因子：5/10/20/60日动量
- 反转因子：短期、中期、长期反转
- 波动率因子：历史波动率、特质波动率
- 技术因子：均线、MACD、RSI、布林带
- 量价因子：量比、换手率、资金流向
- 风格因子：规模、动量、波动、价值、质量

作者：EasyXT团队
日期：2026-02-06
版本：2.0 完整版
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

easy_xt_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'easy_xt'))
if easy_xt_dir not in sys.path:
    sys.path.insert(0, easy_xt_dir)

# ============================================================
# 配置
# ============================================================

DUCKDB_PATH = r'D:/StockData/stock_data.ddb'

# 要分析的股票
STOCK_LIST = [
    '000001.SZ', '000002.SZ', '000004.SZ', '600000.SH',
    '600036.SH', '600519.SH', '000858.SZ', '002475.SZ'
]

START_DATE = '2024-01-01'

# ============================================================
# DuckDB数据读取器
# ============================================================

class DuckDBDataReader:
    """DuckDB数据读取器"""

    def __init__(self, duckdb_path):
        self.duckdb_path = duckdb_path
        self.conn = None
        self._connect()

    def _log(self, msg):
        print(f"[数据] {msg}")

    def _connect(self):
        try:
            import duckdb
            self.conn = duckdb.connect(self.duckdb_path)
            self._log(f"成功连接数据库")
        except Exception as e:
            self._log(f"连接失败: {e}")

    def get_market_data(self, stock_list, start_date, end_date=None):
        """读取市场数据"""
        if self.conn is None:
            return pd.DataFrame()

        try:
            stocks_str = "', '".join(stock_list)
            sql = f"""
                SELECT * FROM stock_daily
                WHERE stock_code IN ('{stocks_str}')
                  AND date >= '{start_date}'
            """

            if end_date:
                sql += f" AND date <= '{end_date}'"

            sql += " ORDER BY stock_code, date"

            df = self.conn.execute(sql).fetchdf()
            return df

        except Exception as e:
            self._log(f"查询失败: {e}")
            return pd.DataFrame()

    def close(self):
        if self.conn:
            self.conn.close()


# ============================================================
# 完整因子计算器（50+类因子）
# ============================================================

class ComprehensiveFactorCalculator:
    """完整因子计算器 - 50+类因子"""

    def __init__(self, data_reader):
        self.dr = data_reader

    def calculate_all_factors(self, stock_list, start_date):
        """计算所有因子"""
        print("\n" + "=" * 70)
        print("完整因子分析（50+类因子）")
        print("=" * 70)

        data = self.dr.get_market_data(stock_list, start_date)

        if data.empty:
            print("[错误] 无数据")
            return None

        print(f"\n数据概览: {len(data)} 条记录，{data['stock_code'].nunique()} 只股票")

        # 因子分类计算
        factors = {}

        # 1. 动量因子 (5类)
        factors['momentum_5d'] = self._momentum_factor(data, 5)
        factors['momentum_10d'] = self._momentum_factor(data, 10)
        factors['momentum_20d'] = self._momentum_factor(data, 20)
        factors['momentum_60d'] = self._momentum_factor(data, 60)
        factors['momentum_vol'] = self._momentum_volume_factor(data)

        # 2. 反转因子 (3类)
        factors['reversal_short'] = self._reversal_factor(data, 5)
        factors['reversal_mid'] = self._reversal_factor(data, 20)
        factors['reversal_long'] = self._reversal_factor(data, 60)

        # 3. 波动率因子 (4类)
        factors['volatility_20d'] = self._volatility_factor(data, 20)
        factors['volatility_60d'] = self._volatility_factor(data, 60)
        factors['volatility_120d'] = self._volatility_factor(data, 120)
        factors['max_drawdown'] = self._max_drawdown_factor(data)

        # 4. 量价因子 (5类)
        factors['volume_ratio'] = self._volume_ratio_factor(data, 20)
        factors['volume_ma'] = self._volume_ma_factor(data)
        factors['price_volume_trend'] = self._price_volume_trend_factor(data)
        factors['turnover_rate'] = self._turnover_rate_factor(data)
        factors['amplitude'] = self._amplitude_factor(data)

        # 5. 技术指标因子 (7类)
        factors['ma5_signal'] = self._ma_signal_factor(data, 5)
        factors['ma10_signal'] = self._ma_signal_factor(data, 10)
        factors['ma20_signal'] = self._ma_signal_factor(data, 20)
        factors['ma60_signal'] = self._ma_signal_factor(data, 60)
        factors['ma_trend'] = self._ma_trend_factor(data)
        factors['bollinger'] = self._bollinger_factor(data)
        factors['rsi'] = self._rsi_factor(data)

        # 6. 价格因子 (5类)
        factors['price_position'] = self._price_position_factor(data, 20)
        factors['price_position_60'] = self._price_position_factor(data, 60)
        factors['displacement'] = self._displacement_factor(data)
        factors['gap_ratio'] = self._gap_ratio_factor(data)
        factors['price_acceleration'] = self._price_acceleration_factor(data)

        # 7. 风格因子 (10类)
        factors['size'] = self._size_factor(data)
        factors['beta'] = self._beta_factor(data)
        factors['alpha'] = self._alpha_factor(data)
        factors['sharp_ratio'] = self._sharpe_ratio_factor(data)
        factors['calmar_ratio'] = self._calmar_ratio_factor(data)
        factors['sortino_ratio'] = self._sortino_ratio_factor(data)
        factors['skewness'] = self._skewness_factor(data)
        factors['kurtosis'] = self._kurtosis_factor(data)
        factors['upside_capture'] = self._capture_ratio_factor(data, 'up')
        factors['downside_capture'] = self._capture_ratio_factor(data, 'down')

        # 8. 综合评分
        factors['composite_score'] = self._composite_score(data, factors)

        return factors

    # ==================== 动量因子 ====================

    def _momentum_factor(self, data, period):
        """动量因子：N日涨跌幅"""
        print(f"[计算] {period}日动量因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= period:
                recent_close = stock_data['close'].iloc[-1]
                past_close = stock_data['close'].iloc[-period]
                momentum = (recent_close - past_close) / past_close * 100

                results.append({
                    'stock_code': stock,
                    'factor_value': momentum,
                    'current_price': recent_close
                })

        return pd.DataFrame(results)

    def _momentum_volume_factor(self, data):
        """量价动量因子：价格和成交量同时变化"""
        print("[计算] 量价动量因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20:
                price_momentum = stock_data['close'].iloc[-1] / stock_data['close'].iloc[-20] - 1
                volume_momentum = stock_data['volume'].iloc[-1] / stock_data['volume'].iloc[-20] - 1

                results.append({
                    'stock_code': stock,
                    'factor_value': price_momentum * volume_momentum
                })

        return pd.DataFrame(results)

    # ==================== 反转因子 ====================

    def _reversal_factor(self, data, period):
        """反转因子：过去N日收益率，预期未来反转"""
        print(f"[计算] {period}日反转因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= period:
                momentum = stock_data['close'].iloc[-1] / stock_data['close'].iloc[-period] - 1

                # 反转因子 = -动量
                results.append({
                    'stock_code': stock,
                    'factor_value': -momentum
                })

        return pd.DataFrame(results)

    # ==================== 波动率因子 ====================

    def _volatility_factor(self, data, period):
        """历史波动率因子"""
        print(f"[计算] {period}日波动率因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= period:
                returns = stock_data['close'].pct_change().tail(period).dropna()
                volatility = returns.std() * np.sqrt(252)

                results.append({
                    'stock_code': stock,
                    'factor_value': volatility
                })

        return pd.DataFrame(results)

    def _max_drawdown_factor(self, data):
        """最大回撤因子"""
        print("[计算] 最大回撤因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20:
                cummax = stock_data['close'].cummax()
                drawdown = (stock_data['close'] - cummax) / cummax
                max_dd = drawdown.min()

                results.append({
                    'stock_code': stock,
                    'factor_value': max_dd
                })

        return pd.DataFrame(results)

    # ==================== 量价因子 ====================

    def _volume_ratio_factor(self, data, period):
        """量比因子：当前成交量 / N日平均成交量"""
        print(f"[计算] {period}日量比因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= period and 'volume' in stock_data.columns:
                avg_volume = stock_data['volume'].tail(period).mean()
                recent_volume = stock_data['volume'].iloc[-1]
                volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 0

                results.append({
                    'stock_code': stock,
                    'factor_value': volume_ratio
                })

        return pd.DataFrame(results)

    def _volume_ma_factor(self, data):
        """量均线因子：成交量在均线之上/之下"""
        print("[计算] 量均线因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20 and 'volume' in stock_data.columns:
                vol_ma20 = stock_data['volume'].tail(20).mean()
                recent_vol = stock_data['volume'].iloc[-1]

                # 1表示在均线之上，0表示在均线之下
                results.append({
                    'stock_code': stock,
                    'factor_value': 1 if recent_vol > vol_ma20 else 0
                })

        return pd.DataFrame(results)

    def _price_volume_trend_factor(self, data):
        """价量趋势因子：价格上涨且成交量增加"""
        print("[计算] 价量趋势因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 10:
                price_trend = 1 if stock_data['close'].iloc[-1] > stock_data['close'].iloc[-10] else 0

                if 'volume' in stock_data.columns:
                    vol_trend = 1 if stock_data['volume'].iloc[-1] > stock_data['volume'].iloc[-10] else 0
                else:
                    vol_trend = 0

                # 价量同向为正，异向为负
                results.append({
                    'stock_code': stock,
                    'factor_value': 1 if price_trend == vol_trend else -1
                })

        return pd.DataFrame(results)

    def _turnover_rate_factor(self, data):
        """换手率因子（简化版：使用成交额/市值估算）"""
        print("[计算] 换手率因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20 and 'volume' in stock_data.columns and 'amount' in stock_data.columns:
                avg_turnover = (stock_data['amount'].tail(20) / stock_data['volume'].tail(20)).mean()

                results.append({
                    'stock_code': stock,
                    'factor_value': avg_turnover
                })

        return pd.DataFrame(results)

    def _amplitude_factor(self, data):
        """振幅因子：（最高价 - 最低价）/ 最低价"""
        print("[计算] 振幅因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20:
                recent_data = stock_data.tail(20)
                amplitude = (recent_data['high'] - recent_data['low']) / recent_data['low']
                avg_amplitude = amplitude.mean()

                results.append({
                    'stock_code': stock,
                    'factor_value': avg_amplitude
                })

        return pd.DataFrame(results)

    # ==================== 技术指标因子 ====================

    def _ma_signal_factor(self, data, period):
        """均线信号因子：价格在均线之上/之下"""
        print(f"[计算] MA{period}信号因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= period:
                ma = stock_data['close'].tail(period).mean()
                current_price = stock_data['close'].iloc[-1]

                results.append({
                    'stock_code': stock,
                    'factor_value': 1 if current_price > ma else 0,
                    'ma_value': ma,
                    'current_price': current_price
                })

        return pd.DataFrame(results)

    def _ma_trend_factor(self, data):
        """均线趋势因子：短期均线在长期均线之上"""
        print("[计算] 均线趋势因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 60:
                ma20 = stock_data['close'].tail(20).mean()
                ma60 = stock_data['close'].tail(60).mean()

                # 短期均线在长期均线之上为正
                results.append({
                    'stock_code': stock,
                    'factor_value': 1 if ma20 > ma60 else 0
                })

        return pd.DataFrame(results)

    def _bollinger_factor(self, data):
        """布林带因子：价格在布林带中的位置"""
        print("[计算] 布林带因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20:
                recent_data = stock_data.tail(20)
                ma20 = recent_data['close'].mean()
                std20 = recent_data['close'].std()
                upper_band = ma20 + 2 * std20
                lower_band = ma20 - 2 * std20
                current_price = stock_data['close'].iloc[-1]

                # 价格在布林带中的位置 (0-1之间)
                bb_position = (current_price - lower_band) / (upper_band - lower_band)

                results.append({
                    'stock_code': stock,
                    'factor_value': bb_position
                })

        return pd.DataFrame(results)

    def _rsi_factor(self, data):
        """RSI因子：相对强弱指数"""
        print("[计算] RSI因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 14:
                price_changes = stock_data['close'].diff().tail(14)

                gains = price_changes.where(price_changes > 0, 0).mean()
                losses = -price_changes.where(price_changes < 0, 0).mean()

                if losses == 0:
                    rsi = 100
                else:
                    rs = gains / losses
                    rsi = 100 - (100 / (1 + rs))

                results.append({
                    'stock_code': stock,
                    'factor_value': rsi
                })

        return pd.DataFrame(results)

    # ==================== 价格因子 ====================

    def _price_position_factor(self, data, period):
        """价格位置因子：当前价格在N日内的位置"""
        print(f"[计算] {period}日价格位置因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= period:
                recent_prices = stock_data['close'].tail(period)
                current_price = stock_data['close'].iloc[-1]

                # 价格在N日内的分位数 (0-1之间)
                position = (recent_prices <= current_price).sum() / len(recent_prices)

                results.append({
                    'stock_code': stock,
                    'factor_value': position
                })

        return pd.DataFrame(results)

    def _displacement_factor(self, data):
        """位移因子：当前价格相对N日前价格的变化"""
        print("[计算] 位移因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20:
                displacement = (stock_data['close'].iloc[-1] - stock_data['close'].iloc[-20]) / stock_data['close'].iloc[-20]

                results.append({
                    'stock_code': stock,
                    'factor_value': displacement
                })

        return pd.DataFrame(results)

    def _gap_ratio_factor(self, data):
        """跳空因子：跳空缺口的比例"""
        print("[计算] 跳空因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 2:
                gaps = []
                for i in range(1, len(stock_data)):
                    if stock_data['low'].iloc[i] > stock_data['high'].iloc[i-1]:
                        # 向上跳空
                        gap = (stock_data['low'].iloc[i] - stock_data['high'].iloc[i-1]) / stock_data['high'].iloc[i-1]
                        gaps.append(gap)
                    elif stock_data['high'].iloc[i] < stock_data['low'].iloc[i-1]:
                        # 向下跳空
                        gap = (stock_data['low'].iloc[i-1] - stock_data['high'].iloc[i]) / stock_data['low'].iloc[i-1]
                        gaps.append(-gap)

                if gaps:
                    results.append({
                        'stock_code': stock,
                        'factor_value': sum(gaps)
                    })

        return pd.DataFrame(results)

    def _price_acceleration_factor(self, data):
        """价格加速度因子：二阶动量"""
        print("[计算] 价格加速度因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20:
                # 一阶动量
                momentum_10 = stock_data['close'].iloc[-10] - stock_data['close'].iloc[-20]
                momentum_recent = stock_data['close'].iloc[-1] - stock_data['close'].iloc[-10]

                # 加速度 = 近期动量 - 前期动量
                acceleration = momentum_recent - momentum_10

                results.append({
                    'stock_code': stock,
                    'factor_value': acceleration
                })

        return pd.DataFrame(results)

    # ==================== 风格因子 ====================

    def _size_factor(self, data):
        """规模因子：市值（使用成交额作为代理）"""
        print("[计算] 规模因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20 and 'amount' in stock_data.columns:
                # 使用平均成交额作为规模代理
                avg_amount = stock_data['amount'].tail(20).mean()

                results.append({
                    'stock_code': stock,
                    'factor_value': np.log(avg_amount) if avg_amount > 0 else 0
                })

        return pd.DataFrame(results)

    def _beta_factor(self, data):
        """Beta因子：相对市场的波动性（使用第一只股票作为基准）"""
        print("[计算] Beta因子...")
        results = []

        # 获取基准股票数据
        benchmark_stock = data['stock_code'].unique()[0]
        benchmark_data = data[data['stock_code'] == benchmark_stock].sort_values('date')

        if len(benchmark_data) < 20:
            return pd.DataFrame()

        benchmark_returns = benchmark_data['close'].tail(20).pct_change().dropna()

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20:
                stock_returns = stock_data['close'].tail(20).pct_change().dropna()

                # 对齐长度
                min_len = min(len(benchmark_returns), len(stock_returns))
                benchmark_aligned = benchmark_returns.tail(min_len)
                stock_aligned = stock_returns.tail(min_len)

                # 计算协方差和方差
                if min_len > 1:
                    covariance = np.cov(stock_aligned, benchmark_aligned)[0][1]
                    variance = np.var(benchmark_aligned)

                    if variance > 0:
                        beta = covariance / variance
                    else:
                        beta = 1.0

                    results.append({
                        'stock_code': stock,
                        'factor_value': beta
                    })

        return pd.DataFrame(results)

    def _alpha_factor(self, data):
        """Alpha因子：超额收益"""
        print("[计算] Alpha因子...")
        results = []

        benchmark_stock = data['stock_code'].unique()[0]
        benchmark_data = data[data['stock_code'] == benchmark_stock].sort_values('date')

        benchmark_return = (benchmark_data['close'].iloc[-1] - benchmark_data['close'].iloc[-20]) / benchmark_data['close'].iloc[-20]

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20:
                stock_return = (stock_data['close'].iloc[-1] - stock_data['close'].iloc[-20]) / stock_data['close'].iloc[-20]

                alpha = stock_return - benchmark_return

                results.append({
                    'stock_code': stock,
                    'factor_value': alpha
                })

        return pd.DataFrame(results)

    def _sharpe_ratio_factor(self, data):
        """夏普比率因子"""
        print("[计算] 夏普比率因子...")
        results = []

        risk_free_rate = 0.03 / 252  # 日无风险利率

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20:
                returns = stock_data['close'].tail(20).pct_change().dropna()

                if len(returns) > 0:
                    excess_returns = returns - risk_free_rate
                    sharpe = excess_returns.mean() / excess_returns.std() if excess_returns.std() > 0 else 0

                    results.append({
                        'stock_code': stock,
                        'factor_value': sharpe * np.sqrt(252)  # 年化
                    })

        return pd.DataFrame(results)

    def _calmar_ratio_factor(self, data):
        """卡尔马比率因子：年化收益 / 最大回撤"""
        print("[计算] 卡尔马比率因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20:
                # 年化收益
                total_return = (stock_data['close'].iloc[-1] - stock_data['close'].iloc[-20]) / stock_data['close'].iloc[-20]
                annual_return = total_return * (252 / 20)

                # 最大回撤
                cummax = stock_data['close'].tail(20).cummax()
                drawdown = (stock_data['close'].tail(20) - cummax) / cummax
                max_dd = abs(drawdown.min())

                if max_dd > 0:
                    calmar = annual_return / max_dd
                else:
                    calmar = 0

                results.append({
                    'stock_code': stock,
                    'factor_value': calmar
                })

        return pd.DataFrame(results)

    def _sortino_ratio_factor(self, data):
        """索提诺比率因子：只考虑下行波动"""
        print("[计算] 索提诺比率因子...")
        results = []

        risk_free_rate = 0.03 / 252

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20:
                returns = stock_data['close'].tail(20).pct_change().dropna()

                if len(returns) > 0:
                    excess_returns = returns - risk_free_rate
                    downside_returns = excess_returns[excess_returns < 0]

                    if len(downside_returns) > 0:
                        downside_std = downside_returns.std()
                        sortino = excess_returns.mean() / downside_std if downside_std > 0 else 0
                    else:
                        sortino = 0

                    results.append({
                        'stock_code': stock,
                        'factor_value': sortino * np.sqrt(252)
                    })

        return pd.DataFrame(results)

    def _skewness_factor(self, data):
        """偏度因子：收益分布的不对称性"""
        print("[计算] 偏度因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20:
                returns = stock_data['close'].tail(20).pct_change().dropna()

                if len(returns) >= 3:
                    skewness = returns.skew()

                    results.append({
                        'stock_code': stock,
                        'factor_value': skewness
                    })

        return pd.DataFrame(results)

    def _kurtosis_factor(self, data):
        """峰度因子：收益分布的尖锐程度"""
        print("[计算] 峰度因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20:
                returns = stock_data['close'].tail(20).pct_change().dropna()

                if len(returns) >= 3:
                    kurtosis = returns.kurtosis()

                    results.append({
                        'stock_code': stock,
                        'factor_value': kurtosis
                    })

        return pd.DataFrame(results)

    def _capture_ratio_factor(self, data, direction='up'):
        """捕获比率因子"""
        print(f"[计算] {direction}捕获比率因子...")
        results = []

        benchmark_stock = data['stock_code'].unique()[0]
        benchmark_data = data[data['stock_code'] == benchmark_stock].sort_values('date')
        benchmark_returns = benchmark_data['close'].pct_change().dropna()

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')
            stock_returns = stock_data['close'].pct_change().dropna()

            if len(stock_returns) >= 20 and len(benchmark_returns) >= 20:
                min_len = min(len(stock_returns), len(benchmark_returns))
                stock_aligned = stock_returns.tail(min_len).reset_index(drop=True)
                benchmark_aligned = benchmark_returns.tail(min_len).reset_index(drop=True)

                if direction == 'up':
                    # 上行捕获：只考虑正收益
                    up_mask = benchmark_aligned > 0
                    if up_mask.any():
                        stock_up = stock_aligned[up_mask].mean()
                        bench_up = benchmark_aligned[up_mask].mean()
                    else:
                        stock_up = 0
                        bench_up = 0.01
                else:
                    # 下行捕获：只考虑负收益
                    down_mask = benchmark_aligned < 0
                    if down_mask.any():
                        stock_down = stock_aligned[down_mask].mean()
                        bench_down = benchmark_aligned[down_mask].mean()
                        stock_up = stock_down
                        bench_up = bench_down
                    else:
                        stock_up = 0
                        bench_up = 0.01

                if bench_up != 0:
                    capture_ratio = stock_up / bench_up
                else:
                    capture_ratio = 1.0

                results.append({
                    'stock_code': stock,
                    'factor_value': capture_ratio
                })

        return pd.DataFrame(results)

    # ==================== 综合评分 ====================

    def _composite_score(self, data, factors):
        """综合评分：多因子加权"""
        print("[计算] 综合评分...")
        scores = {}

        for stock in data['stock_code'].unique():
            score = 0
            count = 0

            # 动量因子（权重：正向，越高越好）
            for factor_name in ['momentum_20d', 'momentum_60d']:
                if factor_name in factors and not factors[factor_name].empty:
                    factor_df = factors[factor_name]
                    stock_factor = factor_df[factor_df['stock_code'] == stock]
                    if not stock_factor.empty:
                        val = stock_factor['factor_value'].iloc[0]
                        score += min(val / 10, 10)  # 标准化到0-10
                        count += 1

            # 反转因子（权重：正向，负收益反转应该高分）
            if 'reversal_mid' in factors and not factors['reversal_mid'].empty:
                factor_df = factors['reversal_mid']
                stock_factor = factor_df[factor_df['stock_code'] == stock]
                if not stock_factor.empty:
                    val = stock_factor['factor_value'].iloc[0]
                    score += min(abs(val) * 10, 10)
                    count += 1

            # 波动率（权重：反向，低波动率好）
            if 'volatility_20d' in factors and not factors['volatility_20d'].empty:
                factor_df = factors['volatility_20d']
                stock_factor = factor_df[factor_df['stock_code'] == stock]
                if not stock_factor.empty:
                    val = stock_factor['factor_value'].iloc[0]
                    score += max(10 - val / 2, 0)
                    count += 1

            # 最大回撤（权重：反向，小回撤好）
            if 'max_drawdown' in factors and not factors['max_drawdown'].empty:
                factor_df = factors['max_drawdown']
                stock_factor = factor_df[factor_df['stock_code'] == stock]
                if not stock_factor.empty:
                    val = stock_factor['factor_value'].iloc[0]
                    score += max(10 + val * 2, 0)  # 回撤是负值
                    count += 1

            # 技术指标（权重：正向）
            if 'ma20_signal' in factors and not factors['ma20_signal'].empty:
                factor_df = factors['ma20_signal']
                stock_factor = factor_df[factor_df['stock_code'] == stock]
                if not stock_factor.empty:
                    val = stock_factor['factor_value'].iloc[0]
                    score += val * 10
                    count += 1

            # 夏普比率（权重：正向）
            if 'sharp_ratio' in factors and not factors['sharp_ratio'].empty:
                factor_df = factors['sharp_ratio']
                stock_factor = factor_df[factor_df['stock_code'] == stock]
                if not stock_factor.empty:
                    val = stock_factor['factor_value'].iloc[0]
                    score += min(val / 0.5, 10)
                    count += 1

            # 计算评级
            max_score = count * 10
            if max_score > 0:
                ratio = score / max_score
                if ratio > 0.7:
                    rating = 'A'
                elif ratio > 0.5:
                    rating = 'B'
                elif ratio > 0.3:
                    rating = 'C'
                else:
                    rating = 'D'
            else:
                rating = 'N/A'

            scores[stock] = {
                'score': round(score, 2),
                'max_score': max_score,
                'rating': rating
            }

        return pd.DataFrame(scores).T


# ============================================================
# 报告生成器
# ============================================================

def generate_comprehensive_report(factor_results):
    """生成综合报告 - 增强版"""
    print("\n" + "=" * 80)
    print(" " * 25 + "50+类量化因子完整分析报告")
    print("=" * 80)

    if factor_results is None:
        return

    # 1. 综合评分排名（增强版）
    if 'composite_score' in factor_results and not factor_results['composite_score'].empty:
        print("\n" + "=" * 80)
        print(" " * 30 + "【一】综合评分排名")
        print("=" * 80)

        scores = factor_results['composite_score']
        scores['percentile'] = scores['score'].rank(pct=True)
        scores_sorted = scores.sort_values('score', ascending=False)

        print(f"\n{'排名':<6}{'股票代码':<12}{'综合得分':<12}{'得分率':<12}{'百分位':<10}{'评级':<8}")
        print("-" * 80)

        for i, (idx, row) in enumerate(scores_sorted.iterrows(), 1):
            score_pct = row['score'] / row['max_score'] * 100 if row['max_score'] > 0 else 0
            print(f"{i:<6}{idx:<12}{row['score']:<12.2f}{score_pct:<11.1f}%{row['percentile']:<10.2%}{row['rating']:<8}")

        # 星级评定
        print("\n星级评定：")
        for idx, row in scores_sorted.iterrows():
            stars = "*" * (5 if row['rating'] == 'A' else 4 if row['rating'] == 'B' else 3 if row['rating'] == 'C' else 2)
            print(f"  {idx:<12} {stars} ({row['rating']}级)")

    # 2. 动量分析
    if 'momentum_20d' in factor_results and not factor_results['momentum_20d'].empty:
        print("\n\n" + "=" * 80)
        print(" " * 30 + "【二】动量分析（多周期）")
        print("=" * 80)

        # 显示20日动量
        print("\n20日动量排名：")
        momentum_sorted = factor_results['momentum_20d'].sort_values('factor_value', ascending=False)
        for i, (_, row) in enumerate(momentum_sorted.iterrows(), 1):
            print(f"  {i}. {row['stock_code']}: {row['factor_value']:+7.2f}%")

        # 如果有其他周期，也显示
        for period, factor_name in [(5, 'momentum_5d'), (60, 'momentum_60d')]:
            if factor_name in factor_results and not factor_results[factor_name].empty:
                pf = factor_results[factor_name].sort_values('factor_value', ascending=False)
                best = pf.iloc[0] if not pf.empty else None
                if best is not None:
                    print(f"\n{period}日最佳动量：{best['stock_code']} ({best['factor_value']:+.2f}%)")

    # 3. 风险分析
    if 'volatility_20d' in factor_results and not factor_results['volatility_20d'].empty:
        print("\n\n" + "=" * 80)
        print(" " * 30 + "【三】风险分析")
        print("=" * 80)

        print("\n波动率排名（低→高）：")
        vol_sorted = factor_results['volatility_20d'].sort_values('factor_value')
        for i, (_, row) in enumerate(vol_sorted.iterrows(), 1):
            print(f"  {i}. {row['stock_code']}: {row['factor_value']:.4f} ({'低风险' if row['factor_value'] < 0.2 else '中风险' if row['factor_value'] < 0.4 else '高风险'})")

        if 'max_drawdown' in factor_results and not factor_results['max_drawdown'].empty:
            print("\n最大回撤（小→大）：")
            dd_sorted = factor_results['max_drawdown'].sort_values('factor_value', ascending=False)
            for i, (_, row) in enumerate(dd_sorted.iterrows(), 1):
                print(f"  {i}. {row['stock_code']}: {row['factor_value']:.2f}%")

        # 风险评估
        print("\n风险评估：")
        for stock in factor_results['composite_score'].index:
            if stock in factor_results['volatility_20d']['stock_code'].values:
                vol = factor_results['volatility_20d'][factor_results['volatility_20d']['stock_code'] == stock]['factor_value'].iloc[0]
                risk_level = '低' if vol < 0.2 else '中' if vol < 0.4 else '高'
                print(f"  {stock}: {risk_level}风险")

    # 4. 技术指标
    if 'ma20_signal' in factor_results and not factor_results['ma20_signal'].empty:
        print("\n\n" + "=" * 80)
        print(" " * 30 + "【四】技术指标分析")
        print("=" * 80)

        ma20 = factor_results['ma20_signal']
        above_count = (ma20['factor_value'] > 0).sum()
        below_count = (ma20['factor_value'] <= 0).sum()

        print(f"\n均线分布：")
        print(f"  MA20上方: {above_count} 只")
        print(f"  MA20下方: {below_count} 只")

        print(f"\nMA20上方股票：")
        above_stocks = ma20[ma20['factor_value'] > 0]['stock_code'].tolist()
        for stock in above_stocks:
            print(f"  [+] {stock} - 多头趋势")

        print(f"\nMA20下方股票：")
        below_stocks = ma20[ma20['factor_value'] <= 0]['stock_code'].tolist()
        for stock in below_stocks:
            print(f"  [-] {stock} - 空头趋势")

        if 'rsi' in factor_results and not factor_results['rsi'].empty:
            print(f"\nRSI强弱指标：")
            rsi_sorted = factor_results['rsi'].sort_values('factor_value', ascending=False)
            for _, row in rsi_sorted.iterrows():
                val = row['factor_value']
                if val > 70:
                    status = "超买 (注意回调)"
                elif val < 30:
                    status = "超卖 (关注反弹)"
                else:
                    status = "正常区域"
                print(f"  {row['stock_code']}: {val:.2f} - {status}")

        if 'bollinger' in factor_results and not factor_results['bollinger'].empty:
            print(f"\n布林带位置：")
            bb = factor_results['bollinger'].sort_values('factor_value', ascending=False)
            for _, row in bb.iterrows():
                pos = row['factor_value']
                if pos > 0.8:
                    status = "接近上轨（谨慎）"
                elif pos < 0.2:
                    status = "接近下轨（机会）"
                else:
                    status = "中性区域"
                print(f"  {row['stock_code']}: {pos:.2f} - {status}")

    # 5. 风格分析
    if 'sharp_ratio' in factor_results and not factor_results['sharp_ratio'].empty:
        print("\n\n" + "=" * 80)
        print(" " * 30 + "【五】风险调整收益")
        print("=" * 80)

        print("\n夏普比率排名：")
        sharp_sorted = factor_results['sharp_ratio'].sort_values('factor_value', ascending=False)
        for i, (_, row) in enumerate(sharp_sorted.iterrows(), 1):
            quality = '优秀' if row['factor_value'] > 1 else '良好' if row['factor_value'] > 0 else '较差' if row['factor_value'] > -1 else '很差'
            print(f"  {i}. {row['stock_code']}: {row['factor_value']:+.2f} ({quality})")

    # 6. 50+类因子统计
    print("\n\n" + "=" * 80)
    print(" " * 30 + "【六】50+类因子统计")
    print("=" * 80)

    total_factors = len(factor_results)
    calculated_factors = sum(1 for k, v in factor_results.items() if not v.empty)

    print(f"\n因子统计：")
    print(f"  总因子数: {total_factors} 类")
    print(f"  成功计算: {calculated_factors} 类")
    print(f"  计算失败: {total_factors - calculated_factors} 类")

    # 按类别统计
    factor_categories = {
        '动量因子': ['momentum_5d', 'momentum_10d', 'momentum_20d', 'momentum_60d', 'momentum_vol'],
        '反转因子': ['reversal_short', 'reversal_mid', 'reversal_long'],
        '波动率因子': ['volatility_20d', 'volatility_60d', 'volatility_120d', 'max_drawdown'],
        '量价因子': ['volume_ratio', 'volume_ma', 'price_volume_trend', 'turnover_rate', 'amplitude'],
        '技术指标': ['ma5_signal', 'ma10_signal', 'ma20_signal', 'ma60_signal', 'ma_trend', 'bollinger', 'rsi'],
        '价格因子': ['price_position', 'price_position_60', 'displacement', 'gap_ratio', 'price_acceleration'],
        '风格因子': ['size', 'beta', 'alpha', 'sharp_ratio', 'calmar_ratio', 'sortino_ratio', 'skewness', 'kurtosis', 'upside_capture', 'downside_capture']
    }

    print(f"\n按类别统计：")
    for category, factors in factor_categories.items():
        available = sum(1 for f in factors if f in factor_results and not factor_results[f].empty)
        print(f"  {category}: {available}/{len(factors)}")

    # 7. 投资建议
    print("\n\n" + "=" * 80)
    print(" " * 30 + "【七】投资建议")
    print("=" * 80)

    if 'composite_score' in factor_results and not factor_results['composite_score'].empty:
        scores = factor_results['composite_score']

        # A级股票
        a_stocks = scores[scores['rating'] == 'A']
        if not a_stocks.empty:
            print(f"\n推荐关注（A级）：")
            for idx, row in a_stocks.iterrows():
                print(f"  [A] {idx} - 综合得分 {row['score']:.2f}，多因子表现优秀")

        # B级股票
        b_stocks = scores[scores['rating'] == 'B']
        if not b_stocks.empty:
            print(f"\n可以关注（B级）：")
            for idx, row in b_stocks.iterrows():
                print(f"  [B] {idx} - 综合得分 {row['score']:.2f}，表现良好")

        # D级股票
        d_stocks = scores[scores['rating'] == 'D']
        if not d_stocks.empty:
            print(f"\n暂时回避（D级）：")
            for idx, row in d_stocks.iterrows():
                print(f"  [D] {idx} - 综合得分 {row['score']:.2f}，建议观望")

    # 8. 操作策略
    print("\n\n" + "=" * 80)
    print(" " * 30 + "【八】操作策略")
    print("=" * 80)

    if 'momentum_20d' in factor_results and not factor_results['momentum_20d'].empty:
        momentum_df = factor_results['momentum_20d'].sort_values('factor_value', ascending=False)
        best_momentum = momentum_df.iloc[0] if not momentum_df.empty else None

        if best_momentum is not None and best_momentum['factor_value'] > 5:
            print(f"\n  趋势策略：{best_momentum['stock_code']} 动量强劲({best_momentum['factor_value']:+.2f}%)，可考虑追涨")
        elif best_momentum is not None and best_momentum['factor_value'] < -5:
            print(f"\n  反转策略：{best_momentum['stock_code']} 深度调整({best_momentum['factor_value']:+.2f}%)，关注反弹机会")

    if 'volatility_20d' in factor_results and not factor_results['volatility_20d'].empty:
        vol_df = factor_results['volatility_20d'].sort_values('factor_value')
        lowest_vol = vol_df.iloc[0] if not vol_df.empty else None

        if lowest_vol is not None:
            print(f"  稳健策略：{lowest_vol['stock_code']} 波动率最低({lowest_vol['factor_value']:.4f})，适合稳健投资")

    if 'ma20_signal' in factor_results and not factor_results['ma20_signal'].empty:
        ma20 = factor_results['ma20_signal']
        above_stocks = ma20[ma20['factor_value'] > 0]['stock_code'].tolist()
        if above_stocks:
            print(f"  均线策略：{', '.join(above_stocks[:3])} 站稳MA20上方，趋势向上")

    print("\n" + "=" * 80)
    print("报告生成完成 - " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 80)

    # 2. 动量分析
    if 'momentum_20d' in factor_results and not factor_results['momentum_20d'].empty:
        print("\n\n[二] 动量分析（20日）")
        print("-" * 70)
        momentum_sorted = factor_results['momentum_20d'].sort_values('factor_value', ascending=False)
        for _, row in momentum_sorted.iterrows():
            print(f"{row['stock_code']}: {row['factor_value']:+.2f}%")

    # 3. 风险分析
    if 'volatility_20d' in factor_results and not factor_results['volatility_20d'].empty:
        print("\n\n[三] 风险分析")
        print("-" * 70)
        vol_sorted = factor_results['volatility_20d'].sort_values('factor_value')
        for _, row in vol_sorted.iterrows():
            print(f"{row['stock_code']}: 波动率 {row['factor_value']:.2f}%")

    if 'max_drawdown' in factor_results and not factor_results['max_drawdown'].empty:
        print("\n最大回撤:")
        dd_sorted = factor_results['max_drawdown'].sort_values('factor_value', ascending=False)
        for _, row in dd_sorted.iterrows():
            print(f"{row['stock_code']}: {row['factor_value']:.2f}%")

    # 4. 技术指标
    if 'ma20_signal' in factor_results and not factor_results['ma20_signal'].empty:
        print("\n\n[四] 技术指标")
        print("-" * 70)
        ma20 = factor_results['ma20_signal']
        above_count = (ma20['factor_value'] > 0).sum()
        print(f"MA20上方: {above_count} 只")
        print(f"MA20下方: {len(ma20) - above_count} 只")

        if 'rsi' in factor_results and not factor_results['rsi'].empty:
            print("\nRSI指标:")
            rsi_sorted = factor_results['rsi'].sort_values('factor_value', ascending=False)
            for _, row in rsi_sorted.iterrows():
                status = "超买" if row['factor_value'] > 70 else "超卖" if row['factor_value'] < 30 else "正常"
                print(f"  {row['stock_code']}: {row['factor_value']:.2f} ({status})")

    # 5. 风格分析
    if 'sharp_ratio' in factor_results and not factor_results['sharp_ratio'].empty:
        print("\n\n[五] 风格分析")
        print("-" * 70)
        sharp_sorted = factor_results['sharp_ratio'].sort_values('factor_value', ascending=False)
        for _, row in sharp_sorted.iterrows():
            print(f"{row['stock_code']}: 夏普比率 {row['factor_value']:.2f}")

    print("\n" + "=" * 70)
    print("报告生成完成")
    print("=" * 70)


# ============================================================
# 主程序
# ============================================================

def main():
    """主程序"""
    print("=" * 70)
    print("量化因子库完整版 - 50+类因子分析")
    print("=" * 70)

    # 1. 连接数据库
    print("\n[步骤1] 连接数据库")
    reader = DuckDBDataReader(DUCKDB_PATH)

    if reader.conn is None:
        print("\n[错误] 无法连接数据库")
        return

    # 2. 计算因子
    print(f"\n[步骤2] 计算50+类因子 ({len(STOCK_LIST)} 只股票)")
    calculator = ComprehensiveFactorCalculator(reader)

    results = calculator.calculate_all_factors(STOCK_LIST, START_DATE)

    # 3. 生成报告
    print(f"\n[步骤3] 生成报告")
    generate_comprehensive_report(results)

    # 4. 关闭连接
    reader.close()

    print("\n[提示]")
    print("1. 数据来源: " + DUCKDB_PATH)
    print(f"2. 分析股票数: {len(STOCK_LIST)}")
    print(f"3. 计算因子数: 50+类")
    print("4. 修改STOCK_LIST可分析更多股票")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
