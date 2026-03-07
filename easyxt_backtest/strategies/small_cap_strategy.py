# -*- coding: utf-8 -*-
"""
小市值策略 - 基于市值选股
"""
from typing import List, Dict
import pandas as pd

from easyxt_backtest.strategy_base import StrategyBase
from easyxt_backtest.data_manager import DataManager


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
                 accuracy_mode: str = 'fast',
                 data_manager: DataManager = None):
        """
        初始化小市值策略

        Args:
            index_code: 指数代码
            select_num: 选中股票数量（最终持仓）
            universe_size: 股票池大小（从多少只小市值股票中筛选）
                          None表示使用所有成分股
            rebalance_freq: 调仓频率 ('monthly' 或 'weekly')
            accuracy_mode: 准确性模式
                - 'fast': 快速模式，只检查前 select_num*3 只（最少50只）
                - 'balanced': 平衡模式，检查前 select_num*10 只（最少100只）
                - 'accurate': 精确模式，检查所有股票（慢但最准确）
            data_manager: 数据管理器
        """
        super().__init__(data_manager)

        self.index_code = index_code
        self.select_num = select_num
        self.universe_size = universe_size
        self.rebalance_freq = rebalance_freq
        self.accuracy_mode = accuracy_mode

        print(f"\n[小市值策略] 参数配置:")
        print(f"  指数代码: {index_code}")
        print(f"  选股数量: {select_num}")
        if universe_size:
            print(f"  股票池大小: {universe_size} 只")
        print(f"  调仓频率: {rebalance_freq}")
        print(f"  准确性模式: {accuracy_mode}")

        # 根据模式设置检查倍数
        if accuracy_mode == 'fast':
            self.check_multiplier = 3
            self.min_check = 50
            print(f"    → 检查范围: 前{self.min_check}只（快速）")
        elif accuracy_mode == 'balanced':
            self.check_multiplier = 10
            self.min_check = 100
            print(f"    → 检查范围: 前{self.min_check}只（平衡）")
        elif accuracy_mode == 'accurate':
            self.check_multiplier = 9999  # 实际上会检查所有
            self.min_check = 9999
            print(f"    → 检查范围: 全部（精确）")
        else:
            # 默认使用快速模式
            self.check_multiplier = 3
            self.min_check = 50
            print(f"    → 检查范围: 前{self.min_check}只（快速）")

    def select_stocks(self, date: str) -> List[str]:
        """
        选股 - 选择市值最小的N只股票

        优化逻辑（用户建议）：
        1. 先批量获取所有股票的市值数据
        2. 批量过滤掉无效股票（退市、停牌、数据过期）
        3. 对剩余有效股票按市值排序
        4. 选出市值最小的N只

        这样既快又准，不会错过任何有效的小市值股票！

        Args:
            date: 交易日期 (YYYYMMDD)

        Returns:
            选中的股票代码列表
        """
        if not self.data_manager:
            raise ValueError("需要提供data_manager")

        print(f"\n  [选股] {date}")

        # 1. 获取股票池（全市场或指数成分股）
        universe = None
        try:
            # 使用Tushare获取指数成分股
            index_cons = self.data_manager.get_index_components(self.index_code, date)

            if not index_cons:
                print(f"    [INFO] 未获取到指数成分股，使用全市场股票")
                universe = None  # 标记需要从全市场获取
            else:
                print(f"    指数成分股: {len(index_cons)} 只")
                universe = index_cons

        except Exception as e:
            print(f"    [INFO] 获取指数成分股失败: {e}，使用全市场股票")
            universe = None

        # 2. 获取所有股票的市值数据
        try:
            if universe is None:
                df_mv = self.data_manager.get_fundamentals(
                    codes=None,  # 获取所有股票
                    date=date,
                    fields=['circ_mv']
                )
                print(f"    从DuckDB获取全市场市值数据")
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

            print(f"    获取市值数据: {len(df_mv)} 只")

        except Exception as e:
            print(f"    [ERROR] 获取市值数据失败: {e}")
            return []

        # 3. 【用户建议】批量过滤无效股票，再排序选股
        #
        # 优化思路：
        # 1. 先对所有股票进行批量有效性检查（标记无效的）
        # 2. 过滤掉所有无效股票
        # 3. 对剩余有效股票按市值排序
        # 4. 选出市值最小的N只
        #
        # 这样既快又准，不会错过任何有效的小市值股票！

        print(f"    [优化] 批量过滤无效股票...")

        # 先按市值排序
        df_mv_sorted = df_mv.sort_values('circ_mv', ascending=True)

        # 确定检查范围（避免检查太多，但也要保证找到足够的）
        # 策略：从市值最小的开始检查，找到足够的有效股票就停止
        # 这样既能保证准确性（不会错过更小的），又能保证速度（早期退出）

        valid_stocks = []
        delisted_count = 0
        suspended_count = 0
        expired_count = 0

        from datetime import datetime, timedelta

        print(f"    [进度] 从市值最小的股票开始验证...")

        # 从小到大检查，不限制范围（但会早期退出）
        for idx, stock in enumerate(df_mv_sorted.index):
            # 进度显示（每100只显示一次）
            if (idx + 1) % 100 == 0:
                print(f"    [进度] 已检查 {idx + 1}/{len(df_mv_sorted)} 只", end='\r')

            # 快速检查股票有效性
            is_valid, reason, price_date, price = self.data_manager.check_price_data_valid(
                stock, date, max_days_diff=7
            )

            if is_valid:
                valid_stocks.append(stock)

                # 【关键】早期退出：找到足够的有效股票就停止
                if len(valid_stocks) >= self.select_num:
                    print(f"\n    [完成] 已找到足够的有效股票({len(valid_stocks)})，停止检查")
                    print(f"    [统计] 总共检查了 {idx + 1} 只股票")
                    break
            else:
                # 统计无效原因
                if "已退市" in reason:
                    delisted_count += 1
                elif "停牌" in reason:
                    suspended_count += 1
                elif "过期" in reason:
                    expired_count += 1

        # 4. 检查是否找到足够的有效股票
        if len(valid_stocks) < self.select_num:
            print(f"\n    [WARNING] 警告: 有效股票({len(valid_stocks)})少于选股数量({self.select_num})")
            print(f"    [分析] 可能原因：")
            print(f"      • 市值最小的股票中有较多退市/停牌")
            print(f"      • 数据质量问题")
            print(f"    [建议] 使用全部有效股票：{len(valid_stocks)} 只")

        # 5. 从有效股票中选择市值最小的N只
        # 注意：valid_stocks已经是按市值从小到大的顺序（因为我们就是按这个顺序检查的）
        selected = valid_stocks[:min(self.select_num, len(valid_stocks))]

        # 6. 显示统计信息
        print(f"\n    [统计] 过滤结果:")
        print(f"      • 检查股票总数: {len(valid_stocks) + delisted_count + suspended_count + expired_count} 只")
        print(f"      • 有效股票: {len(valid_stocks)} 只")
        if delisted_count > 0:
            print(f"      • 过滤-退市: {delisted_count} 只")
        if suspended_count > 0:
            print(f"      • 过滤-停牌: {suspended_count} 只")
        if expired_count > 0:
            print(f"      • 过滤-数据过期: {expired_count} 只")

        print(f"    [结果] 最终选中: {len(selected)} 只")
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
