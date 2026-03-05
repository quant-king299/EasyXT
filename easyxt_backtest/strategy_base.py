# -*- coding: utf-8 -*-
"""
策略基类 - 定义所有策略必须实现的接口
"""
from abc import ABC, abstractmethod
from typing import List, Dict
import pandas as pd
from datetime import datetime, timedelta


class StrategyBase(ABC):
    """
    策略基类

    所有策略必须继承此类并实现以下方法：
    1. select_stocks() - 选股接口
    2. get_target_weights() - 获取目标权重
    3. get_rebalance_dates() - 获取调仓日期

    使用示例：
        class MyStrategy(StrategyBase):
            def select_stocks(self, date: str) -> List[str]:
                # 实现选股逻辑
                return ['000001.SZ', '000002.SZ']

            def get_target_weights(self, date: str, selected_stocks: List[str]) -> Dict[str, float]:
                # 实现权重分配逻辑
                return {stock: 1.0/len(selected_stocks) for stock in selected_stocks}

            def get_rebalance_dates(self, start_date: str, end_date: str) -> List[str]:
                # 返回调仓日期列表
                return ['20230101', '20230201', '20230301']
    """

    def __init__(self, data_manager=None):
        """
        初始化策略

        Args:
            data_manager: 数据管理器实例
        """
        self.data_manager = data_manager

    # ==================== 必须实现的抽象方法 ====================

    @abstractmethod
    def select_stocks(self, date: str) -> List[str]:
        """
        选股接口

        根据给定日期选择股票池

        Args:
            date: 交易日期 (YYYYMMDD)

        Returns:
            股票代码列表

        示例：
            def select_stocks(self, date: str) -> List[str]:
                # 获取小市值股票
                df = self.data_manager.get_fundamentals(
                    codes=all_stocks,
                    date=date,
                    fields=['circ_mv']
                )
                # 按市值排序，选择最小的5只
                return df.nsmallest(5, 'circ_mv').index.tolist()
        """
        pass

    @abstractmethod
    def get_target_weights(self, date: str, selected_stocks: List[str]) -> Dict[str, float]:
        """
        获取目标权重

        计算选中股票的目标权重

        Args:
            date: 交易日期 (YYYYMMDD)
            selected_stocks: 选中的股票列表

        Returns:
            股票代码到权重的映射 {stock_code: weight}

        注意：
            - 权重总和应该等于1.0
            - 权重值应该在[0, 1]范围内
            - 可以返回空字典表示清仓

        示例：
            def get_target_weights(self, date, selected_stocks):
                # 等权重配置
                weight = 1.0 / len(selected_stocks)
                return {stock: weight for stock in selected_stocks}
        """
        pass

    @abstractmethod
    def get_rebalance_dates(self, start_date: str, end_date: str) -> List[str]:
        """
        获取调仓日期列表

        确定在回测期间哪些日期需要调仓

        Args:
            start_date: 回测开始日期 (YYYYMMDD)
            end_date: 回测结束日期 (YYYYMMDD)

        Returns:
            调仓日期列表 (YYYYMMDD格式)

        示例：
            def get_rebalance_dates(self, start_date, end_date):
                # 每月第一个交易日调仓
                return self._get_first_trading_days_monthly(start_date, end_date)
        """
        pass

    # ==================== 可选重写的辅助方法 ====================

    def pre_rebalance(self, date: str, current_positions: Dict[str, int]) -> Dict[str, int]:
        """
        调仓前处理（可选）

        在调仓前执行一些自定义逻辑，比如：
        - 检查停牌股票
        - 过滤涨跌停股票
        - 自定义卖出条件

        Args:
            date: 当前交易日期
            current_positions: 当前持仓 {stock_code: volume}

        Returns:
            调整后的持仓 {stock_code: volume}
        """
        return current_positions

    def post_rebalance(self, date: str, trades: List) -> List:
        """
        调仓后处理（可选）

        在调仓后执行一些自定义逻辑，比如：
        - 记录交易日志
        - 自定义风险控制

        Args:
            date: 当前交易日期
            trades: 交易列表

        Returns:
            处理后的交易列表
        """
        return trades

    # ==================== 工具方法 ====================

    def _get_first_trading_days_monthly(self,
                                       start_date: str,
                                       end_date: str) -> List[str]:
        """
        获取每月第一个交易日（工具方法）

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            每月第一个交易日列表
        """
        if not self.data_manager:
            raise ValueError("需要data_manager来获取交易日历")

        # 获取所有交易日
        all_dates = self.data_manager.get_trading_dates(start_date, end_date)

        # 筛选每月第一个交易日
        monthly_first = []
        last_month = None

        for date_str in all_dates:
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            current_month = date_obj.month

            if current_month != last_month:
                monthly_first.append(date_str)
                last_month = current_month

        return monthly_first

    def _get_first_trading_days_weekly(self,
                                      start_date: str,
                                      end_date: str) -> List[str]:
        """
        获取每周第一个交易日（工具方法）

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            每周第一个交易日列表
        """
        if not self.data_manager:
            raise ValueError("需要data_manager来获取交易日历")

        # 获取所有交易日
        all_dates = self.data_manager.get_trading_dates(start_date, end_date)

        # 筛选每周第一个交易日
        weekly_first = []
        last_week = None

        for date_str in all_dates:
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            current_week = date_obj.isocalendar()[1]

            if current_week != last_week:
                weekly_first.append(date_str)
                last_week = current_week

        return weekly_first

    def _get_all_trading_days(self,
                             start_date: str,
                             end_date: str) -> List[str]:
        """
        获取所有交易日（工具方法）

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            所有交易日列表
        """
        if not self.data_manager:
            raise ValueError("需要data_manager来获取交易日历")

        return self.data_manager.get_trading_dates(start_date, end_date)


class FactorStrategyBase(StrategyBase):
    """
    因子策略基类

    专门用于基于因子的策略，提供因子相关的接口

    使用示例：
        class MyFactorStrategy(FactorStrategyBase):
            def get_factor_values(self, date: str) -> pd.Series:
                # 获取因子值
                df = self.data_manager.get_fundamentals(...)
                return df['pe_ratio']  # 返回因子值Series

            def select_stocks(self, date: str) -> List[str]:
                # 因子策略通常不需要选股，返回所有股票
                return self.get_stock_universe(date)
    """

    @abstractmethod
    def get_factor_values(self, date: str) -> pd.Series:
        """
        获取因子值

        Args:
            date: 交易日期 (YYYYMMDD)

        Returns:
            因子值Series，index为股票代码，values为因子值

        示例：
            def get_factor_values(self, date: str) -> pd.Series:
                df = self.data_manager.get_fundamentals(
                    codes=all_stocks,
                    date=date,
                    fields=['pe_ratio', 'market_cap']
                )
                return df['pe_ratio']  # PE因子
        """
        pass

    def get_stock_universe(self, date: str) -> List[str]:
        """
        获取股票池

        Args:
            date: 交易日期

        Returns:
            股票代码列表
        """
        # 默认实现：从data_manager获取
        if self.data_manager:
            # 可以从指数成分股或全市场获取
            # 这里简单返回空，子类可以重写
            return []
        return []

    def select_stocks_by_factor_quantile(self,
                                        date: str,
                                        top_quantile: float = 0.1,
                                        bottom_quantile: float = 0.1) -> List[str]:
        """
        按因子分位数选股

        Args:
            date: 交易日期
            top_quantile: 顶部分位数（做多）
            bottom_quantile: 底部分位数（做空）

        Returns:
            选中股票列表
        """
        factor_values = self.get_factor_values(date)

        if factor_values.empty:
            return []

        # 计算分位数
        top_threshold = factor_values.quantile(1 - top_quantile)
        bottom_threshold = factor_values.quantile(bottom_quantile)

        # 选择顶部和底部
        top_stocks = factor_values[factor_values >= top_threshold].index.tolist()
        bottom_stocks = factor_values[factor_values <= bottom_threshold].index.tolist()

        return top_stocks + bottom_stocks

    def get_target_weights_by_factor(self,
                                     date: str,
                                     selected_stocks: List[str],
                                     long_only: bool = True) -> Dict[str, float]:
        """
        按因子值分配权重

        Args:
            date: 交易日期
            selected_stocks: 选中股票
            long_only: 是否只做多

        Returns:
            权重字典
        """
        factor_values = self.get_factor_values(date)
        selected_factors = factor_values[selected_stocks]

        if long_only:
            # 等权重
            weight = 1.0 / len(selected_stocks)
            return {stock: weight for stock in selected_stocks}
        else:
            # 多空组合：前一半做多，后一半做空
            n = len(selected_stocks)
            long_stocks = selected_stocks[:n//2]
            short_stocks = selected_stocks[n//2:]

            weight = 1.0 / len(long_stocks)

            weights = {}
            for stock in long_stocks:
                weights[stock] = weight
            for stock in short_stocks:
                weights[stock] = -weight

            return weights
