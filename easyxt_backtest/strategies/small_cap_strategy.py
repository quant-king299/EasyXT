# -*- coding: utf-8 -*-
"""
小市值策略 - 基于市值选股
"""
from typing import List, Dict
import pandas as pd

from ..strategy_base import StrategyBase
from ..data_manager import DataManager


class SmallCapStrategy(StrategyBase):
    """
    小市值策略

    策略逻辑：
    1. 从指定指数中选择成分股
    2. 获取市值数据
    3. 选择市值最小的N只股票
    4. 等权重配置
    5. 定期调仓（如每月第一个交易日）

    参数：
        - index_code: 指数代码（默认'399101.SZ'中小板综指）
        - select_num: 选中股票数量（默认5只）
        - rebalance_freq: 调仓频率（'monthly'-每月, 'weekly'-每周）
        - filter_st: 是否过滤ST股票（默认True）
        - filter_suspended: 是否过滤停牌股票（默认True）
    """

    def __init__(self,
                 index_code: str = '399101.SZ',
                 select_num: int = 5,
                 universe_size: int = None,
                 rebalance_freq: str = 'monthly',
                 data_manager: DataManager = None):
        """
        初始化小市值策略

        Args:
            index_code: 指数代码
            select_num: 选中股票数量（最终持仓）
            universe_size: 股票池大小（从多少只小市值股票中筛选）
                          None表示使用所有成分股
            rebalance_freq: 调仓频率 ('monthly' 或 'weekly')
            data_manager: 数据管理器
        """
        super().__init__(data_manager)

        self.index_code = index_code
        self.select_num = select_num
        self.universe_size = universe_size
        self.rebalance_freq = rebalance_freq

        print(f"\n[小市值策略] 参数配置:")
        print(f"  指数代码: {index_code}")
        print(f"  选股数量: {select_num}")
        if universe_size:
            print(f"  股票池大小: {universe_size} 只")
        print(f"  调仓频率: {rebalance_freq}")

    def select_stocks(self, date: str) -> List[str]:
        """
        选股 - 选择市值最小的N只股票

        Args:
            date: 交易日期 (YYYYMMDD)

        Returns:
            选中的股票代码列表
        """
        if not self.data_manager:
            raise ValueError("需要提供data_manager")

        print(f"\n  [选股] {date}")

        # 1. 获取指数成分股
        universe = None
        try:
            # 使用Tushare获取指数成分股
            index_cons = self.data_manager.get_index_components(self.index_code, date)

            if not index_cons:
                print(f"    [WARNING] 未获取到指数成分股，从DuckDB获取全市场股票")
                universe = None  # 标记需要从全市场获取
            else:
                print(f"    指数成分股: {len(index_cons)} 只")
                universe = index_cons

        except Exception as e:
            print(f"    [WARNING] 获取指数成分股失败: {e}，从DuckDB获取全市场股票")
            universe = None

        # 2. 获取市值数据
        try:
            # 如果没有指数成分股，从DuckDB获取全市场市值数据
            if universe is None:
                df_mv = self.data_manager.get_fundamentals(
                    codes=None,  # 获取所有股票
                    date=date,
                    fields=['circ_mv']
                )
                print(f"    从DuckDB获取市值数据")
            else:
                df_mv = self.data_manager.get_fundamentals(
                    codes=universe,
                    date=date,
                    fields=['circ_mv']
                )

            if df_mv is None or df_mv.empty:
                print(f"    [WARNING] 未获取到市值数据")
                return []

            # 过滤掉市值数据为空的
            df_mv = df_mv.dropna(subset=['circ_mv'])

            if df_mv.empty:
                print(f"    [WARNING] 过滤后无有效市值数据")
                return []

            # 如果指定了股票池大小，先筛选出市值最小的universe_size只
            if self.universe_size and len(df_mv) > self.universe_size:
                df_mv = df_mv.sort_values('circ_mv', ascending=True).head(self.universe_size)
                print(f"    股票池筛选: 从全市场筛选出市值最小的 {self.universe_size} 只")
                print(f"    有效市值数据（筛选后）: {len(df_mv)} 只")
            else:
                print(f"    有效市值数据: {len(df_mv)} 只")

        except Exception as e:
            print(f"    [ERROR] 获取市值数据失败: {e}")
            return []

        # 3. 按市值排序，选择最小的N只
        df_mv_sorted = df_mv.sort_values('circ_mv', ascending=True)

        # ✨ 新增：验证价格数据可用性，过滤掉无价格数据和退市股票
        valid_stocks = []
        delisted_stocks = []

        for stock in df_mv_sorted.index:
            price = self.data_manager.get_nearest_price(stock, date)

            if price is not None and price > 0:
                # 有价格，正常股票
                valid_stocks.append(stock)
            else:
                # 无价格，检查是否退市
                last_trade_info = self.data_manager.get_last_trade_date_and_price(stock, date)

                if last_trade_info is not None:
                    last_date, last_price = last_trade_info
                    mv = df_mv_sorted.loc[stock, 'circ_mv']

                    if last_price is not None:
                        # 已退市，记录退市信息
                        delisted_stocks.append((stock, last_date, last_price, mv))
                        print(f"    [FILTER] {stock} 市值:{mv:,.0f}万元 - 已退市({last_date}最后价格{last_price:.2f})，已过滤")
                    else:
                        # 无历史价格，数据缺失
                        print(f"    [FILTER] {stock} 市值:{mv:,.0f}万元 - 无历史价格数据，已过滤")
                else:
                    # 完全无法获取信息
                    mv = df_mv_sorted.loc[stock, 'circ_mv']
                    print(f"    [FILTER] {stock} 市值:{mv:,.0f}万元 - 无价格数据，已过滤")

        # 显示退市股票统计
        if delisted_stocks:
            print(f"    ⚠️  检测到 {len(delisted_stocks)} 只退市股票已过滤")

        # 如果有效股票不足select_num，则使用全部有效股票
        if len(valid_stocks) < self.select_num:
            print(f"    ⚠️  警告: 有效股票({len(valid_stocks)})少于选股数量({self.select_num})")
            selected = valid_stocks
        else:
            # 从有效股票中选择市值最小的select_num只
            df_valid = df_mv_sorted.loc[valid_stocks]
            selected = df_valid.head(self.select_num).index.tolist()

        print(f"    选中股票: {len(selected)} 只")
        for i, stock in enumerate(selected, 1):
            mv = df_mv_sorted.loc[stock, 'circ_mv']
            print(f"      {i}. {stock} - 市值: {mv:,.0f} 万元")

        return selected

    def get_target_weights(self,
                          date: str,
                          selected_stocks: List[str]) -> Dict[str, float]:
        """
        获取目标权重 - 等权重配置

        Args:
            date: 交易日期
            selected_stocks: 选中的股票列表

        Returns:
            权重字典 {stock_code: weight}
        """
        if not selected_stocks:
            return {}

        # 等权重
        weight = 1.0 / len(selected_stocks)

        weights = {stock: weight for stock in selected_stocks}

        print(f"  [权重] 等权重配置，每只股票 {weight:.2%}")

        return weights

    def get_rebalance_dates(self,
                           start_date: str,
                           end_date: str) -> List[str]:
        """
        获取调仓日期

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            调仓日期列表
        """
        if not self.data_manager:
            raise ValueError("需要提供data_manager")

        if self.rebalance_freq == 'monthly':
            # 每月第一个交易日
            dates = self._get_first_trading_days_monthly(start_date, end_date)
        elif self.rebalance_freq == 'weekly':
            # 每周第一个交易日
            dates = self._get_first_trading_days_weekly(start_date, end_date)
        else:
            # 每日
            dates = self._get_all_trading_days(start_date, end_date)

        return dates


class SmallCapStrategyV2(SmallCapStrategy):
    """
    小市值策略V2 - 增强版

    新增功能：
    1. 过滤ST股票
    2. 过滤停牌股票
    3. 过滤涨跌停股票
    4. 最小流动性要求
    """

    def __init__(self,
                 index_code: str = '399101.SZ',
                 select_num: int = 5,
                 rebalance_freq: str = 'monthly',
                 min_turnover: float = 0,  # 最小换手率
                 data_manager: DataManager = None):
        """
        初始化小市值策略V2

        Args:
            index_code: 指数代码
            select_num: 选中股票数量
            rebalance_freq: 调仓频率
            min_turnover: 最小换手率（过滤流动性差的股票）
            data_manager: 数据管理器
        """
        super().__init__(index_code, select_num, rebalance_freq, data_manager)
        self.min_turnover = min_turnover

        print(f"\n[小市值策略V2] 增强配置:")
        print(f"  最小换手率: {min_turnover:.2%}")

    def select_stocks(self, date: str) -> List[str]:
        """
        选股 - 增强版选股逻辑
        """
        if not self.data_manager:
            raise ValueError("需要提供data_manager")

        print(f"\n  [选股] {date}")

        # 1. 获取指数成分股
        try:
            index_cons = self.data_manager.get_index_components(self.index_code, date)

            if not index_cons:
                print(f"    [WARNING] 未获取到指数成分股")
                return []

            print(f"    指数成分股: {len(index_cons)} 只")

        except Exception as e:
            print(f"    [ERROR] 获取指数成分股失败: {e}")
            return []

        # 2. 获取市值和换手率数据
        try:
            df_mv = self.data_manager.get_fundamentals(
                codes=index_cons,
                date=date,
                fields=['circ_mv', 'turnover_ratio']  # 市值和换手率
            )

            if df_mv.empty:
                print(f"    [WARNING] 未获取到基本面数据")
                return []

            # 过滤空值
            df_mv = df_mv.dropna(subset=['circ_mv'])

            # 过滤换手率低于最小值的
            if self.min_turnover > 0 and 'turnover_ratio' in df_mv.columns:
                df_mv = df_mv[df_mv['turnover_ratio'] >= self.min_turnover]
                print(f"    过滤后（换手率>={self.min_turnover:.2%}): {len(df_mv)} 只")

            if df_mv.empty:
                print(f"    [WARNING] 过滤后无有效数据")
                return []

        except Exception as e:
            print(f"    [ERROR] 获取基本面数据失败: {e}")
            return []

        # 3. 按市值排序，选择最小的N只
        df_mv_sorted = df_mv.sort_values('circ_mv', ascending=True)

        selected = df_mv_sorted.head(self.select_num).index.tolist()

        print(f"    选中股票: {len(selected)} 只")
        for i, stock in enumerate(selected, 1):
            mv = df_mv_sorted.loc[stock, 'circ_mv']
            print(f"      {i}. {stock} - 市值: {mv:,.0f} 万元")

        return selected

    def pre_rebalance(self,
                     date: str,
                     current_positions: Dict[str, int]) -> Dict[str, int]:
        """
        调仓前处理 - 过滤需要卖出的股票

        可以在这里实现：
        - 检查停牌股票
        - 检查涨跌停股票
        """
        # 简单实现：直接返回当前持仓
        # 实际应用中可以添加更多过滤逻辑
        return current_positions
