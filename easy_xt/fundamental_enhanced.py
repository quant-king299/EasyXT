"""
增强版基本面因子分析器

基于DuckDB中的真实数据计算基本面因子
利用stock_daily表的丰富数据（OHLCV、复权因子等）

主要功能：
1. 估值因子：基于价格和成交量
2. 质量因子：基于价格波动和趋势
3. 动量因子：多周期动量
4. 流动性因子：基于成交量
5. 波动率因子：风险度量
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')


class FundamentalAnalyzerEnhanced:
    """增强版基本面因子分析器"""

    def __init__(self, duckdb_reader=None):
        """
        初始化

        参数:
            duckdb_reader: DuckDBDataReader实例
        """
        self.duckdb_reader = duckdb_reader

    def get_price_data(self, stock_code: str, days: int = 252) -> pd.DataFrame:
        """
        从DuckDB获取价格数据

        参数:
            stock_code: 股票代码
            days: 获取天数（默认252个交易日，约1年）

        返回:
            pd.DataFrame: 价格数据
        """
        if self.duckdb_reader is None:
            print("[ERROR] 需要提供DuckDBDataReader实例")
            return pd.DataFrame()

        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days * 2)).strftime('%Y-%m-%d')

            df = self.duckdb_reader.get_market_data(
                stock_list=[stock_code],
                start_date=start_date,
                end_date=end_date
            )

            if df.empty:
                return pd.DataFrame()

            # 按日期排序并取最近days条
            df = df.sort_values('date').tail(days)

            return df

        except Exception as e:
            print(f"[ERROR] 获取 {stock_code} 数据失败: {e}")
            return pd.DataFrame()

    # ============================================================
    # 估值因子
    # ============================================================

    def calculate_valuation_factors(self, df_price: pd.DataFrame) -> Dict:
        """
        计算估值因子

        参数:
            df_price: 价格数据

        返回:
            Dict: 估值因子
        """
        if df_price.empty or len(df_price) < 20:
            return {}

        factors = {}

        try:
            # 1. 相对估值：股价相对均线的位置
            if len(df_price) >= 60:
                ma20 = df_price['close'].tail(20).mean()
                ma60 = df_price['close'].tail(60).mean()
                latest = df_price['close'].iloc[-1]

                factors['price_to_ma20'] = latest / ma20 if ma20 > 0 else np.nan
                factors['price_to_ma60'] = latest / ma60 if ma60 > 0 else np.nan

            # 2. 估值分位数：在历史价格中的位置
            if len(df_price) >= 252:
                price_rank = (df_price['close'] <= df_price['close'].iloc[-1]).sum() / len(df_price)
                factors['price_percentile'] = price_rank

            # 3. 相对高点距离
            if len(df_price) >= 252:
                high_252 = df_price['close'].tail(252).max()
                factors['dist_from_high_252'] = (df_price['close'].iloc[-1] / high_252 - 1) * 100

        except Exception as e:
            print(f"[INFO] 计算估值因子失败: {e}")

        return factors

    # ============================================================
    # 动量因子
    # ============================================================

    def calculate_momentum_factors(self, df_price: pd.DataFrame) -> Dict:
        """
        计算动量因子

        参数:
            df_price: 价格数据

        返回:
            Dict: 动量因子
        """
        if df_price.empty or len(df_price) < 20:
            return {}

        factors = {}

        try:
            # 1. 短期动量（1日、5日、10日、20日）
            for period in [1, 5, 10, 20]:
                if len(df_price) > period:
                    momentum = (df_price['close'].iloc[-1] / df_price['close'].iloc[-period-1] - 1) * 100
                    factors[f'momentum_{period}d'] = momentum

            # 2. 中期动量（60日、120日、252日）
            for period in [60, 120, 252]:
                if len(df_price) > period:
                    momentum = (df_price['close'].iloc[-1] / df_price['close'].iloc[-period-1] - 1) * 100
                    factors[f'momentum_{period}d'] = momentum

            # 3. 动量加速度（近期动量 - 远期动量）
            if len(df_price) >= 120:
                mom_20 = (df_price['close'].iloc[-1] / df_price['close'].iloc[-20] - 1)
                mom_60 = (df_price['close'].iloc[-20] / df_price['close'].iloc[-60] - 1)
                factors['momentum_accel'] = (mom_20 - mom_60) * 100

            # 4. 相对强弱指数（RSI）
            if len(df_price) >= 14:
                deltas = df_price['close'].diff()
                gains = deltas.where(deltas > 0, 0)
                losses = -deltas.where(deltas < 0, 0)

                avg_gain = gains.tail(14).mean()
                avg_loss = losses.tail(14).mean()

                if avg_loss != 0:
                    rs = avg_gain / avg_loss
                    factors['rsi_14'] = 100 - (100 / (1 + rs))
                else:
                    factors['rsi_14'] = 100

        except Exception as e:
            print(f"[INFO] 计算动量因子失败: {e}")

        return factors

    # ============================================================
    # 波动率因子
    # ============================================================

    def calculate_volatility_factors(self, df_price: pd.DataFrame) -> Dict:
        """
        计算波动率因子

        参数:
            df_price: 价格数据

        返回:
            Dict: 波动率因子
        """
        if df_price.empty or len(df_price) < 20:
            return {}

        factors = {}

        try:
            # 1. 历史波动率（不同周期）
            returns = df_price['close'].pct_change().dropna()

            for period in [20, 60, 120]:
                if len(returns) >= period:
                    hist_vol = returns.tail(period).std() * np.sqrt(252)
                    factors[f'volatility_{period}d'] = hist_vol

            # 2. ATR（平均真实波幅）
            if len(df_price) >= 14:
                high_low = df_price['high'] - df_price['low']
                high_close = np.abs(df_price['high'] - df_price['close'].shift(1))
                low_close = np.abs(df_price['low'] - df_price['close'].shift(1))

                tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                atr = tr.rolling(14).mean().iloc[-1]

                if not np.isnan(atr):
                    latest_price = df_price['close'].iloc[-1]
                    factors['atr_14'] = atr / latest_price if latest_price > 0 else np.nan
                    factors['atr_14_pct'] = (atr / latest_price * 100) if latest_price > 0 else np.nan

            # 3. 波动率分位数
            if len(returns) >= 60:
                current_vol = returns.tail(20).std()
                vol_percentile = (returns.tail(252).std() <= current_vol).sum() / min(len(returns), 252)
                factors['volatility_percentile'] = vol_percentile

        except Exception as e:
            print(f"[INFO] 计算波动率因子失败: {e}")

        return factors

    # ============================================================
    # 质量因子
    # ============================================================

    def calculate_quality_factors(self, df_price: pd.DataFrame) -> Dict:
        """
        计算质量因子

        参数:
            df_price: 价格数据

        返回:
            Dict: 质量因子
        """
        if df_price.empty or len(df_price) < 20:
            return {}

        factors = {}

        try:
            # 1. 价格稳定性（变异系数）
            if len(df_price) >= 60:
                prices = df_price['close'].tail(60)
                cv = prices.std() / prices.mean() if prices.mean() > 0 else np.nan
                factors['price_cv_60d'] = cv

            # 2. 趋势强度（线性回归斜率）
            if len(df_price) >= 60:
                prices = df_price['close'].tail(60).values
                x = np.arange(len(prices))
                slope, _ = np.polyfit(x, prices, 1)
                factors['trend_strength_60d'] = slope / prices.mean() if prices.mean() > 0 else np.nan

            # 3. 连续上涨/下跌天数
            if len(df_price) >= 20:
                changes = df_price['close'].tail(20).diff()

                up_days = 0
                down_days = 0
                for change in changes:
                    if change > 0:
                        up_days += 1
                        down_days = 0
                    elif change < 0:
                        down_days += 1
                        up_days = 0

                factors['consecutive_up_days'] = up_days
                factors['consecutive_down_days'] = down_days

            # 4. 价格位置（相对52周高点）
            if len(df_price) >= 252:
                high_52w = df_price['close'].tail(252).max()
                low_52w = df_price['close'].tail(252).min()
                latest = df_price['close'].iloc[-1]

                factors['price_position_52w'] = (latest - low_52w) / (high_52w - low_52w) if (high_52w - low_52w) > 0 else np.nan

        except Exception as e:
            print(f"[INFO] 计算质量因子失败: {e}")

        return factors

    # ============================================================
    # 流动性因子
    # ============================================================

    def calculate_liquidity_factors(self, df_price: pd.DataFrame) -> Dict:
        """
        计算流动性因子

        参数:
            df_price: 价格数据（需要包含volume字段）

        返回:
            Dict: 流动性因子
        """
        if df_price.empty or len(df_price) < 20:
            return {}

        factors = {}

        try:
            # 1. 成交量均值（不同周期）
            if 'volume' in df_price.columns:
                for period in [5, 20, 60]:
                    if len(df_price) >= period:
                        avg_volume = df_price['volume'].tail(period).mean()
                        factors[f'avg_volume_{period}d'] = avg_volume

                # 2. 成交量比率（近期/远期）
                if len(df_price) >= 60:
                    vol_20 = df_price['volume'].tail(20).mean()
                    vol_60 = df_price['volume'].tail(60).mean()
                    factors['volume_ratio'] = vol_20 / vol_60 if vol_60 > 0 else np.nan

                # 3. 换手率（成交额/收盘价）
                if 'amount' in df_price.columns and 'close' in df_price.columns:
                    # 近20天平均换手率
                    for period in [5, 20]:
                        if len(df_price) >= period:
                            avg_amount = df_price['amount'].tail(period).mean()
                            avg_close = df_price['close'].tail(period).mean()

                            if avg_close > 0:
                                # 假设每手100股（需要根据实际情况调整）
                                turnover = (avg_amount / avg_close) / 100
                                factors[f'turnover_{period}d'] = turnover

        except Exception as e:
            print(f"[INFO] 计算流动性因子失败: {e}")

        return factors

    # ============================================================
    # 综合因子计算
    # ============================================================

    def get_all_fundamental_factors(self, stock_code: str, duckdb_reader=None) -> pd.DataFrame:
        """
        获取所有基本面因子

        参数:
            stock_code: 股票代码
            duckdb_reader: DuckDBDataReader实例（可选）

        返回:
            pd.DataFrame: 所有基本面因子
        """
        reader = duckdb_reader or self.duckdb_reader

        # 获取价格数据
        df_price = self.get_price_data(stock_code, days=252)

        if df_price.empty:
            print(f"[INFO] 未找到 {stock_code} 的数据")
            return pd.DataFrame()

        # 计算各类因子
        all_factors = {}

        # 估值因子
        valuation = self.calculate_valuation_factors(df_price)
        if valuation:
            all_factors.update(valuation)

        # 动量因子
        momentum = self.calculate_momentum_factors(df_price)
        if momentum:
            all_factors.update(momentum)

        # 波动率因子
        volatility = self.calculate_volatility_factors(df_price)
        if volatility:
            all_factors.update(volatility)

        # 质量因子
        quality = self.calculate_quality_factors(df_price)
        if quality:
            all_factors.update(quality)

        # 流动性因子
        liquidity = self.calculate_liquidity_factors(df_price)
        if liquidity:
            all_factors.update(liquidity)

        if all_factors:
            return pd.DataFrame([all_factors], index=[stock_code])
        else:
            return pd.DataFrame()

    def get_batch_fundamental_factors(self, stock_list: List[str],
                                    duckdb_reader=None) -> pd.DataFrame:
        """
        批量获取基本面因子

        参数:
            stock_list: 股票代码列表
            duckdb_reader: DuckDBDataReader实例（可选）

        返回:
            pd.DataFrame: 批量基本面因子
        """
        results = []

        for stock_code in stock_list:
            try:
                df = self.get_all_fundamental_factors(stock_code, duckdb_reader)
                if not df.empty:
                    results.append(df)
            except Exception as e:
                print(f"[INFO] 跳过 {stock_code}: {e}")
                continue

        if results:
            return pd.concat(results)
        else:
            return pd.DataFrame()


# ============================================================
# 便捷函数
# ============================================================

def get_enhanced_fundamental_factors(stock_code: str, duckdb_reader=None) -> pd.DataFrame:
    """
    获取增强版基本面因子

    参数:
        stock_code: 股票代码
        duckdb_reader: DuckDBDataReader实例

    返回:
        pd.DataFrame: 基本面因子
    """
    analyzer = FundamentalAnalyzerEnhanced(duckdb_reader)
    return analyzer.get_all_fundamental_factors(stock_code, duckdb_reader)


def get_batch_enhanced_factors(stock_list: List[str], duckdb_reader=None) -> pd.DataFrame:
    """
    批量获取增强版基本面因子

    参数:
        stock_list: 股票代码列表
        duckdb_reader: DuckDBDataReader实例

    返回:
        pd.DataFrame: 批量基本面因子
    """
    analyzer = FundamentalAnalyzerEnhanced(duckdb_reader)
    return analyzer.get_batch_fundamental_factors(stock_list, duckdb_reader)


if __name__ == "__main__":
    """测试代码"""
    print("=" * 70)
    print("  增强版基本面因子分析器测试")
    print("=" * 70)

    print("\n[说明]")
    print("基于DuckDB stock_daily表（767万条记录）")
    print("数据范围：2015-10-26 到 2026-02-02")
    print("覆盖股票：5190只")
    print("\n因子类型：")
    print("1. 估值因子：相对估值、价格分位数、距离高点")
    print("2. 动量因子：多周期动量、动量加速度、RSI")
    print("3. 波动率因子：历史波动率、ATR、波动率分位数")
    print("4. 质量因子：价格稳定性、趋势强度、连续涨跌")
    print("5. 流动性因子：成交量均值、换手率")
    print("\n" + "=" * 70)
