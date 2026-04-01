"""
Fama-French定价因子计算器

实现标准的Fama-French三因子和四因子模型：
- MKT（Market）：市场因子
- SMB（Small Minus Big）：规模因子
- HML（High Minus Low）：价值因子
- UMD（Up Minus Down）：动量因子（四因子模型）

参考：
- Fama, E. F., & French, K. R. (1993). Common risk factors in the returns on stocks and bonds.
- Carhart, M. M. (1997). On persistence in mutual fund performance.

使用示例：
>>> from factors.pricing import FamaFrenchCalculator
>>> calc = FamaFrenchCalculator(data_manager)
>>> factors = calc.calculate_ff3_factors('2024-01-15')
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')


class FamaFrenchCalculator:
    """
    Fama-French定价因子计算器

    支持三因子和四因子模型计算
    """

    def __init__(self, data_manager=None):
        """
        初始化计算器

        参数:
            data_manager: 数据管理器实例（支持get_market_data等方法）
        """
        self.data_manager = data_manager

    def calculate_ff3_factors(self,
                               trade_date: str,
                               stock_data: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """
        计算Fama-French三因子

        参数:
            trade_date: 交易日期 '2024-01-15'
            stock_data: 股票数据（可选，如果不提供则从data_manager获取）

        返回:
            dict: {
                'MKT': 市场因子,
                'SMB': 规模因子,
                'HML': 价值因子,
                'N_STOCKS': 有效股票数量
            }
        """
        # 获取股票数据
        if stock_data is None:
            if self.data_manager is None:
                raise ValueError("需要提供data_manager或stock_data")
            stock_data = self._get_stock_data(trade_date)

        if stock_data is None or stock_data.empty:
            return {'MKT': np.nan, 'SMB': np.nan, 'HML': np.nan, 'N_STOCKS': 0}

        # 数据清洗：过滤无效数据
        stock_data = self._filter_valid_data(stock_data)

        if len(stock_data) < 9:  # 至少需要9只股票（三分位分组）
            return {'MKT': np.nan, 'SMB': np.nan, 'HML': np.nan, 'N_STOCKS': 0}

        # 计算个股收益率
        stock_data['return'] = stock_data['close'].pct_change()

        # 过滤收益率异常值
        stock_data = stock_data[
            (stock_data['return'] > -0.35) &  # 涨跌幅限制
            (stock_data['return'] < 0.35)
        ]
        stock_data = stock_data.dropna(subset=['return'])

        if len(stock_data) < 9:
            return {'MKT': np.nan, 'SMB': np.nan, 'HML': np.nan, 'N_STOCKS': 0}

        # 1. MKT因子：所有股票的平均收益率
        mkt = stock_data['return'].mean()

        # 2. SMB因子：小市值组合收益 - 大市值组合收益
        smb = self._calculate_smb_factor(stock_data)

        # 3. HML因子：价值股组合收益 - 成长股组合收益
        hml = self._calculate_hml_factor(stock_data)

        return {
            'MKT': mkt,
            'SMB': smb,
            'HML': hml,
            'N_STOCKS': len(stock_data)
        }

    def calculate_ff4_factors(self,
                               trade_date: str,
                               stock_data: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """
        计算Fama-French四因子（增加动量因子）

        参数:
            trade_date: 交易日期
            stock_data: 股票数据

        返回:
            dict: 包含MKT, SMB, HML, UMD四个因子
        """
        # 计算三因子
        ff3 = self.calculate_ff3_factors(trade_date, stock_data)

        if ff3['N_STOCKS'] < 9:
            return {
                'MKT': np.nan,
                'SMB': np.nan,
                'HML': np.nan,
                'UMD': np.nan,
                'N_STOCKS': 0
            }

        # 计算UMD动量因子
        if stock_data is None:
            stock_data = self._get_stock_data(trade_date)

        if stock_data is not None and not stock_data.empty:
            umd = self._calculate_umd_factor(stock_data)
        else:
            umd = np.nan

        return {
            'MKT': ff3['MKT'],
            'SMB': ff3['SMB'],
            'HML': ff3['HML'],
            'UMD': umd,
            'N_STOCKS': ff3['N_STOCKS']
        }

    def _filter_valid_data(self, stock_data: pd.DataFrame) -> pd.DataFrame:
        """
        过滤有效的股票数据

        过滤条件：
        - 市值不为空
        - PB不为空且为正数
        - 价格不为空且为正数
        """
        df = stock_data.copy()

        # 确保必要的字段存在
        required_cols = ['close', 'total_mv']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"数据缺少必要字段: {required_cols}")

        # 过滤条件
        df = df[df['close'] > 0]
        df = df[df['total_mv'] > 0]

        if 'pb' in df.columns:
            df = df[df['pb'] > 0]
        else:
            # 如果没有PB字段，无法计算HML因子，返回空数据
            return pd.DataFrame()

        return df.dropna()

    def _calculate_smb_factor(self, stock_data: pd.DataFrame) -> float:
        """
        计算SMB（规模因子）

        方法：
        1. 按市值中位数分组
        2. 小市值组合收益 - 大市值组合收益
        """
        # 按市值中位数分组
        mv_median = stock_data['total_mv'].median()

        small_caps = stock_data[stock_data['total_mv'] <= mv_median]
        large_caps = stock_data[stock_data['total_mv'] > mv_median]

        # 等权平均收益
        small_return = small_caps['return'].mean()
        large_return = large_caps['return'].mean()

        smb = small_return - large_return

        return smb

    def _calculate_hml_factor(self, stock_data: pd.DataFrame) -> float:
        """
        计算HML（价值因子）

        方法：
        1. 按PB中位数分组
        2. 低PB（价值股）组合收益 - 高PB（成长股）组合收益
        """
        # 按PB中位数分组
        pb_median = stock_data['pb'].median()

        value_stocks = stock_data[stock_data['pb'] <= pb_median]  # 低PB = 价值股
        growth_stocks = stock_data[stock_data['pb'] > pb_median]  # 高PB = 成长股

        # 等权平均收益
        value_return = value_stocks['return'].mean()
        growth_return = growth_stocks['return'].mean()

        hml = value_return - growth_return

        return hml

    def _calculate_umd_factor(self, stock_data: pd.DataFrame,
                               lookback_days: int = 252) -> float:
        """
        计算UMD（动量因子）

        方法：
        1. 计算过去252日（约1年）的累计收益
        2. 高收益组合 - 低收益组合

        注意：这里需要历史数据，如果data_manager不支持会返回NaN
        """
        if self.data_manager is None:
            return np.nan

        try:
            # 获取历史数据（需要252日历史）
            end_date = stock_data['date'].max() if 'date' in stock_data.columns else datetime.now()
            start_date = end_date - timedelta(days=lookback_days * 2)  # 乘以2考虑非交易日

            # 这里简化处理：直接使用当日数据排序
            # 实际应该计算过去一年的累计收益
            if 'return' in stock_data.columns:
                # 简化：使用当日收益率作为代理（不严谨，仅作示例）
                return_median = stock_data['return'].median()

                winners = stock_data[stock_data['return'] >= return_median]
                losers = stock_data[stock_data['return'] < return_median]

                winner_return = winners['return'].mean()
                loser_return = losers['return'].mean()

                umd = winner_return - loser_return

                return umd
            else:
                return np.nan

        except Exception as e:
            print(f"[WARNING] 计算UMD因子失败: {e}")
            return np.nan

    def _get_stock_data(self, trade_date: str) -> Optional[pd.DataFrame]:
        """
        获取股票数据

        参数:
            trade_date: 交易日期

        返回:
            pd.DataFrame: 包含close, total_mv, pb等字段
        """
        if self.data_manager is None:
            return None

        try:
            # 尝试通过data_manager获取数据
            if hasattr(self.data_manager, 'get_market_data'):
                # DuckDBDataReader风格
                df = self.data_manager.get_market_data(
                    stock_list=None,  # 获取所有股票
                    start_date=trade_date,
                    end_date=trade_date
                )
                return df
            elif hasattr(self.data_manager, 'get_stock_data_by_date'):
                # 其他风格的数据管理器
                df = self.data_manager.get_stock_data_by_date(trade_date)
                return df
            else:
                print("[WARNING] data_manager不支持获取数据的方法")
                return None

        except Exception as e:
            print(f"[WARNING] 获取股票数据失败: {e}")
            return None


class PricingFactorCalculator:
    """
    综合定价因子计算器

    整合所有定价因子计算功能
    """

    def __init__(self, data_manager=None):
        """
        初始化

        参数:
            data_manager: 数据管理器
        """
        self.data_manager = data_manager
        self.ff_calculator = FamaFrenchCalculator(data_manager)

    def calculate_all_pricing_factors(self,
                                       trade_date: str,
                                       model: str = 'ff3') -> pd.Series:
        """
        计算所有定价因子

        参数:
            trade_date: 交易日期
            model: 'ff3'（三因子）或 'ff4'（四因子）

        返回:
            pd.Series: 因子值
        """
        if model == 'ff3':
            factors = self.ff_calculator.calculate_ff3_factors(trade_date)
        elif model == 'ff4':
            factors = self.ff_calculator.calculate_ff4_factors(trade_date)
        else:
            raise ValueError(f"不支持的模型: {model}")

        return pd.Series(factors)

    def batch_calculate_factors(self,
                                 start_date: str,
                                 end_date: str,
                                 model: str = 'ff3') -> pd.DataFrame:
        """
        批量计算定价因子时间序列

        参数:
            start_date: 开始日期
            end_date: 结束日期
            model: 'ff3' 或 'ff4'

        返回:
            pd.DataFrame: 因子时间序列
        """
        if self.data_manager is None:
            raise ValueError("批量计算需要data_manager")

        # 获取交易日列表（这里简化处理）
        try:
            # 假设data_manager有get_trade_dates方法
            if hasattr(self.data_manager, 'get_trade_dates'):
                trade_dates = self.data_manager.get_trade_dates(start_date, end_date)
            else:
                # 简化：按工作日生成
                dates = pd.date_range(start_date, end_date, freq='B')
                trade_dates = [d.strftime('%Y-%m-%d') for d in dates]

        except Exception as e:
            print(f"[WARNING] 获取交易日历失败: {e}")
            return pd.DataFrame()

        results = []

        for trade_date in trade_dates:
            try:
                factors = self.calculate_all_pricing_factors(trade_date, model)
                factors['trade_date'] = trade_date
                results.append(factors)

            except Exception as e:
                print(f"[WARNING] {trade_date} 因子计算失败: {e}")
                continue

        if results:
            df = pd.DataFrame(results)
            df = df.set_index('trade_date')
            return df
        else:
            return pd.DataFrame()


# ============================================================
# 便捷函数
# ============================================================

def calculate_ff3_factors(trade_date: str, stock_data: pd.DataFrame) -> Dict[str, float]:
    """
    便捷函数：计算Fama-French三因子

    参数:
        trade_date: 交易日期
        stock_data: 股票数据

    返回:
        dict: 三因子值
    """
    calc = FamaFrenchCalculator()
    return calc.calculate_ff3_factors(trade_date, stock_data)


def calculate_ff4_factors(trade_date: str, stock_data: pd.DataFrame) -> Dict[str, float]:
    """
    便捷函数：计算Fama-French四因子

    参数:
        trade_date: 交易日期
        stock_data: 股票数据

    返回:
        dict: 四因子值
    """
    calc = FamaFrenchCalculator()
    return calc.calculate_ff4_factors(trade_date, stock_data)


if __name__ == "__main__":
    print("=" * 70)
    print(" " * 20 + "Fama-French定价因子计算器")
    print("=" * 70)

    print("\n[功能说明]")
    print("- MKT（市场因子）：所有股票的平均收益")
    print("- SMB（规模因子）：小市值组合收益 - 大市值组合收益")
    print("- HML（价值因子）：低PB组合收益 - 高PB组合收益")
    print("- UMD（动量因子）：高收益组合 - 低收益组合")

    print("\n[使用示例]")
    print("""
    from factors.pricing import FamaFrenchCalculator

    # 方式1：使用data_manager
    calc = FamaFrenchCalculator(data_manager)
    factors = calc.calculate_ff3_factors('2024-01-15')

    # 方式2：直接提供股票数据
    factors = calc.calculate_ff3_factors('2024-01-15', stock_data)

    # 批量计算
    from factors.pricing import PricingFactorCalculator
    calc = PricingFactorCalculator(data_manager)
    factor_ts = calc.batch_calculate_factors('2024-01-01', '2024-12-31')
    """)

    print("\n" + "=" * 70)
