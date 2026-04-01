"""
小市值质量因子

因子逻辑：
1. 股票池过滤：
   - 剔除创业板（30）、科创板（688）、北交所（8、4）
   - 剔除ST股票
   - 剔除停牌股票
   - 剔除高价股（>100元）

2. 基本面筛选：
   - ROE > 15%（高盈利能力）
   - ROA > 10%（高资产回报率）

3. 因子计算：
   - 因子值 = -(rank_mv + rank_pb) / 2
   - 负号：因子值越小越好（小市值+低PB）

来源：外部量化项目整合

使用示例：
>>> from factors.custom import SmallCapQualityFactor
>>> factor = SmallCapQualityFactor()
>>> factor_df = factor.calculate('2024-01-15', data_manager)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')


class SmallCapQualityFactor:
    """
    小市值质量因子

    选股逻辑：小市值 + 高质量（高ROE/ROA）+ 低估值（低PB）
    """

    def __init__(self):
        """初始化"""
        self.name = 'f1_small_cap_quality'
        self.description = '小市值+高质量+低估值因子'
        self.freq = 'monthly'

    def calculate(self,
                  trade_date: str,
                  data_manager) -> pd.DataFrame:
        """
        计算因子值

        参数:
            trade_date: 交易日期 '2024-01-15'
            data_manager: 数据管理器（需要支持获取股票、财务数据）

        返回:
            pd.DataFrame: {
                'stock_code': 股票代码,
                'factor_value': 因子值,
                'rank_mv': 市值排名,
                'rank_pb': PB排名
            }
        """
        if data_manager is None:
            raise ValueError("需要提供data_manager")

        # 1. 获取股票基础数据
        stock_data = self._get_stock_data(trade_date, data_manager)

        if stock_data is None or stock_data.empty:
            print(f"[INFO] {trade_date} 未获取到股票数据")
            return pd.DataFrame()

        # 2. 过滤股票
        stock_data = self._filter_stocks(stock_data)

        if stock_data.empty:
            print(f"[INFO] {trade_date} 过滤后无股票")
            return pd.DataFrame()

        # 3. 获取财务数据
        financial_data = self._get_financial_data(trade_date, data_manager)

        if financial_data is None or financial_data.empty:
            print(f"[INFO] {trade_date} 未获取到财务数据")
            return pd.DataFrame()

        # 4. 基本面筛选
        qualified_stocks = self._filter_by_fundamentals(stock_data, financial_data)

        if qualified_stocks.empty:
            print(f"[INFO] {trade_date} 基本面筛选后无股票")
            return pd.DataFrame()

        # 5. 计算因子值
        factor_df = self._calculate_factor_values(qualified_stocks)

        return factor_df

    def _get_stock_data(self,
                         trade_date: str,
                         data_manager) -> Optional[pd.DataFrame]:
        """
        获取股票基础数据

        需要：close, total_mv, pb, name（用于过滤ST）
        """
        try:
            # 尝试通过data_manager获取数据
            if hasattr(data_manager, 'get_market_data'):
                df = data_manager.get_market_data(
                    stock_list=None,  # 获取所有股票
                    start_date=trade_date,
                    end_date=trade_date
                )

                if df.empty:
                    return None

                # 确保必要的列存在
                required_cols = ['close', 'total_mv', 'pb']
                if not all(col in df.columns for col in required_cols):
                    print(f"[WARNING] 数据缺少必要列: {required_cols}")
                    return None

                return df

            elif hasattr(data_manager, 'get_daily_basic'):
                # 其他风格的数据管理器
                df = data_manager.get_daily_basic(trade_date)
                return df

            else:
                print("[WARNING] data_manager不支持获取股票数据")
                return None

        except Exception as e:
            print(f"[WARNING] 获取股票数据失败: {e}")
            return None

    def _get_financial_data(self,
                             trade_date: str,
                             data_manager) -> Optional[pd.DataFrame]:
        """
        获取财务数据

        需要：stock_code, roe, roa
        """
        try:
            if hasattr(data_manager, 'get_financial_data'):
                df = data_manager.get_financial_data(
                    trade_date=trade_date,
                    fields=['stock_code', 'roe', 'roa']
                )
                return df

            elif hasattr(data_manager, 'get_financial'):
                df = data_manager.get_financial(trade_date)
                return df

            else:
                # 财务数据可选，如果没有则跳过基本面筛选
                return None

        except Exception as e:
            print(f"[INFO] 获取财务数据失败（可选）: {e}")
            return None

    def _filter_stocks(self, stock_data: pd.DataFrame) -> pd.DataFrame:
        """
        股票池过滤

        过滤条件：
        1. 剔除创业板（30）、科创板（688）、北交所（8、4）
        2. 剔除ST股票
        3. 剔除高价股（>100元）
        """
        df = stock_data.copy()

        # 1. 剔除特定板块
        if 'stock_code' in df.columns:
            df = df[~df['stock_code'].str.startswith('30')]
            df = df[~df['stock_code'].str.startswith('688')]
            df = df[~df['stock_code'].str.startswith('8')]
            df = df[~df['stock_code'].str.startswith('4')]

        # 2. 剔除ST
        if 'name' in df.columns:
            df = df[~df['name'].str.contains('ST')]

        # 3. 剔除高价股
        if 'close' in df.columns:
            df = df[df['close'] < 100]

        # 4. 剔除PB为空或为负的
        if 'pb' in df.columns:
            df = df[df['pb'] > 0]

        # 5. 剔除市值为空或为负的
        if 'total_mv' in df.columns:
            df = df[df['total_mv'] > 0]

        return df

    def _filter_by_fundamentals(self,
                                 stock_data: pd.DataFrame,
                                 financial_data: pd.DataFrame) -> pd.DataFrame:
        """
        基本面筛选

        条件：
        - ROE > 15%
        - ROA > 10%
        """
        if financial_data is None or financial_data.empty:
            # 如果没有财务数据，返回所有股票（跳过筛选）
            return stock_data

        # 合并数据
        merged = pd.merge(
            stock_data,
            financial_data,
            on='stock_code',
            how='inner'
        )

        if merged.empty:
            return pd.DataFrame()

        # 基本面筛选
        if 'roe' in merged.columns:
            merged = merged[merged['roe'] > 0.15]  # ROE > 15%

        if 'roa' in merged.columns:
            merged = merged[merged['roa'] > 0.10]  # ROA > 10%

        return merged

    def _calculate_factor_values(self, stock_data: pd.DataFrame) -> pd.DataFrame:
        """
        计算因子值

        因子 = -(rank_mv + rank_pb) / 2

        负号：因子值越小越好（小市值+低PB）
        """
        df = stock_data.copy()

        # 计算排名（百分比排名）
        df['rank_mv'] = df['total_mv'].rank(pct=True)
        df['rank_pb'] = df['pb'].rank(pct=True)

        # 计算因子值
        df['factor_value'] = -(df['rank_mv'] + df['rank_pb']) / 2

        # 选择需要的列
        result = df[['stock_code', 'factor_value', 'rank_mv', 'rank_pb']].copy()

        # 按因子值排序
        result = result.sort_values('factor_value')

        return result

    def batch_calculate(self,
                        start_date: str,
                        end_date: str,
                        data_manager) -> pd.DataFrame:
        """
        批量计算因子时间序列

        参数:
            start_date: 开始日期
            end_date: 结束日期
            data_manager: 数据管理器

        返回:
            pd.DataFrame: 因子时间序列
        """
        if data_manager is None:
            raise ValueError("需要data_manager")

        # 获取交易日列表
        try:
            if hasattr(data_manager, 'get_trade_dates'):
                trade_dates = data_manager.get_trade_dates(start_date, end_date)
            else:
                dates = pd.date_range(start_date, end_date, freq='M')
                trade_dates = [d.strftime('%Y-%m-%d') for d in dates]

        except Exception as e:
            print(f"[WARNING] 获取交易日历失败: {e}")
            return pd.DataFrame()

        results = []

        for trade_date in trade_dates:
            try:
                factor_df = self.calculate(trade_date, data_manager)

                if not factor_df.empty:
                    factor_df['trade_date'] = trade_date
                    results.append(factor_df)

            except Exception as e:
                print(f"[WARNING] {trade_date} 因子计算失败: {e}")
                continue

        if results:
            return pd.concat(results)
        else:
            return pd.DataFrame()


# ============================================================
# 便捷函数
# ============================================================

def calculate_small_cap_quality_factor(trade_date: str,
                                        data_manager) -> pd.DataFrame:
    """
    便捷函数：计算小市值质量因子

    参数:
        trade_date: 交易日期
        data_manager: 数据管理器

    返回:
        pd.DataFrame: 因子值
    """
    factor = SmallCapQualityFactor()
    return factor.calculate(trade_date, data_manager)


if __name__ == "__main__":
    print("=" * 70)
    print(" " * 15 + "小市值质量因子（f1）")
    print("=" * 70)

    print("\n[因子逻辑]")
    print("1. 股票池过滤：")
    print("   - 剔除创业板、科创板、北交所")
    print("   - 剔除ST股票")
    print("   - 剔除停牌、高价股（>100元）")

    print("\n2. 基本面筛选：")
    print("   - ROE > 15%（高盈利能力）")
    print("   - ROA > 10%（高资产回报率）")

    print("\n3. 因子计算：")
    print("   - rank_mv = 市值排名（百分比）")
    print("   - rank_pb = PB排名（百分比）")
    print("   - factor_value = -(rank_mv + rank_pb) / 2")
    print("   - 因子值越小越好（小市值+低PB）")

    print("\n[使用示例]")
    print("""
    from factors.custom import SmallCapQualityFactor

    factor = SmallCapQualityFactor()

    # 计算单日因子
    factor_df = factor.calculate('2024-01-15', data_manager)
    print(factor_df.head(20))

    # 批量计算
    factor_ts = factor.batch_calculate(
        '2024-01-01',
        '2024-12-31',
        data_manager
    )
    """)

    print("\n[因子的投资逻辑]")
    print("- 小市值：小盘股通常有更大的成长空间")
    print("- 高质量：高ROE/ROA表示公司盈利能力强")
    print("- 低估值：低PB表示被低估，安全边际高")
    print("- 组合：小盘+优质+低估 = 高性价比")

    print("\n" + "=" * 70)
