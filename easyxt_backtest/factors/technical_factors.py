"""
技术指标因子

基于价格和成交量的技术指标因子。
"""

from typing import List
import pandas as pd
import numpy as np
from .base import BaseFactor


class TechnicalFactor(BaseFactor):
    """
    技术指标因子

    支持的因子字段：
    - momentum_N: N日动量
    - ma_N: N日移动平均
    - rsi_N: N日RSI
    - volatility_N: N日波动率
    - turnover_ratio: 换手率
    等
    """

    def calculate(self, stock_pool: List[str], date: str) -> pd.Series:
        """
        计算技术指标因子值

        Args:
            stock_pool: 股票列表
            date: 日期 (YYYYMMDD)

        Returns:
            Series: 股票代码到因子值的映射
        """
        try:
            # 解析因子字段
            factor_field = self.field
            params = self.config.params or {}

            # 判断因子类型
            if factor_field.startswith('momentum_'):
                return self._calculate_momentum(stock_pool, date, params)
            elif factor_field.startswith('ma_'):
                return self._calculate_ma(stock_pool, date, params)
            elif factor_field.startswith('rsi_'):
                return self._calculate_rsi(stock_pool, date, params)
            elif factor_field == 'volatility':
                return self._calculate_volatility(stock_pool, date, params)
            else:
                # 尝试直接从data_manager获取
                return self._get_from_data_manager(stock_pool, date, factor_field)

        except Exception as e:
            print(f"❌ 计算技术指标因子失败 [{self.field}]: {e}")
            return pd.Series(index=stock_pool, dtype=float)

    def _calculate_momentum(self, stock_pool: List[str], date: str, params: dict) -> pd.Series:
        """
        计算动量因子

        动量 = (当前价格 - N日前价格) / N日前价格

        Args:
            stock_pool: 股票列表
            date: 日期
            params: 参数，包含period（周期）

        Returns:
            Series: 动量值
        """
        period = params.get('period', 20)

        result = pd.Series(index=stock_pool, dtype=float)

        for stock in stock_pool:
            try:
                # 获取历史价格数据
                if hasattr(self.data_manager, 'get_bars'):
                    bars = self.data_manager.get_bars(
                        code=stock,
                        start_date=date,
                        end_date=date,
                        period='daily',
                        count=period + 5  # 多取一些数据以应对停牌
                    )

                    if bars is not None and len(bars) >= period:
                        # 计算动量
                        current_price = bars['close'].iloc[-1]
                        past_price = bars['close'].iloc[-period]

                        if past_price > 0:
                            momentum = (current_price - past_price) / past_price
                            result[stock] = momentum
                        else:
                            result[stock] = np.nan
                    else:
                        result[stock] = np.nan
                else:
                    result[stock] = np.nan

            except Exception as e:
                result[stock] = np.nan

        return result

    def _calculate_ma(self, stock_pool: List[str], date: str, params: dict) -> pd.Series:
        """
        计算移动平均因子

        MA = N日收盘价的平均值

        Args:
            stock_pool: 股票列表
            date: 日期
            params: 参数，包含period（周期）

        Returns:
            Series: MA值
        """
        period = params.get('period', 20)

        result = pd.Series(index=stock_pool, dtype=float)

        for stock in stock_pool:
            try:
                if hasattr(self.data_manager, 'get_bars'):
                    bars = self.data_manager.get_bars(
                        code=stock,
                        start_date=date,
                        end_date=date,
                        period='daily',
                        count=period + 5
                    )

                    if bars is not None and len(bars) >= period:
                        ma = bars['close'].tail(period).mean()
                        result[stock] = ma
                    else:
                        result[stock] = np.nan
                else:
                    result[stock] = np.nan

            except Exception as e:
                result[stock] = np.nan

        return result

    def _calculate_rsi(self, stock_pool: List[str], date: str, params: dict) -> pd.Series:
        """
        计算RSI因子

        RSI = 100 - (100 / (1 + RS))
        RS = 平均上涨幅度 / 平均下跌幅度

        Args:
            stock_pool: 股票列表
            date: 日期
            params: 参数，包含period（周期，默认14）

        Returns:
            Series: RSI值
        """
        period = params.get('period', 14)

        result = pd.Series(index=stock_pool, dtype=float)

        for stock in stock_pool:
            try:
                if hasattr(self.data_manager, 'get_bars'):
                    bars = self.data_manager.get_bars(
                        code=stock,
                        start_date=date,
                        end_date=date,
                        period='daily',
                        count=period + 20
                    )

                    if bars is not None and len(bars) > period:
                        # 计算价格变化
                        delta = bars['close'].diff()

                        # 分离上涨和下跌
                        gains = delta.where(delta > 0, 0)
                        losses = -delta.where(delta < 0, 0)

                        # 计算平均上涨和下跌
                        avg_gains = gains.tail(period).mean()
                        avg_losses = losses.tail(period).mean()

                        if avg_losses == 0:
                            result[stock] = 100 if avg_gains > 0 else 50
                        else:
                            rs = avg_gains / avg_losses
                            rsi = 100 - (100 / (1 + rs))
                            result[stock] = rsi
                    else:
                        result[stock] = np.nan
                else:
                    result[stock] = np.nan

            except Exception as e:
                result[stock] = np.nan

        return result

    def _calculate_volatility(self, stock_pool: List[str], date: str, params: dict) -> pd.Series:
        """
        计算波动率因子

        波动率 = 收益率的标准差

        Args:
            stock_pool: 股票列表
            date: 日期
            params: 参数，包含period（周期）

        Returns:
            Series: 波动率值
        """
        period = params.get('period', 20)

        result = pd.Series(index=stock_pool, dtype=float)

        for stock in stock_pool:
            try:
                if hasattr(self.data_manager, 'get_bars'):
                    bars = self.data_manager.get_bars(
                        code=stock,
                        start_date=date,
                        end_date=date,
                        period='daily',
                        count=period + 5
                    )

                    if bars is not None and len(bars) >= period:
                        # 计算收益率
                        returns = bars['close'].pct_change().tail(period)

                        # 计算波动率（标准差）
                        volatility = returns.std()
                        result[stock] = volatility
                    else:
                        result[stock] = np.nan
                else:
                    result[stock] = np.nan

            except Exception as e:
                result[stock] = np.nan

        return result

    def _get_from_data_manager(self, stock_pool: List[str], date: str, field: str) -> pd.Series:
        """
        尝试从data_manager直接获取因子数据

        Args:
            stock_pool: 股票列表
            date: 日期
            field: 字段名

        Returns:
            Series: 因子值
        """
        try:
            if hasattr(self.data_manager, 'get_factor'):
                return self.data_manager.get_factor(stock_pool, date, field)
            elif hasattr(self.data_manager, 'get_technical_factor'):
                return self.data_manager.get_technical_factor(stock_pool, date, field)
            else:
                return pd.Series(index=stock_pool, dtype=float)
        except Exception as e:
            return pd.Series(index=stock_pool, dtype=float)
