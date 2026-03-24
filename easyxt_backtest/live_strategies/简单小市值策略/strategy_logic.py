# -*- coding: utf-8 -*-
"""
策略逻辑模块

自动生成于: 2026-03-24 10:15:44
"""

from typing import List, Dict
from datetime import datetime


class 简单小市值策略Strategy:
    """
    选择市值最小的10只股票，适合研究小市值效应

    核心逻辑：
    1. 获取股票池
    2. 应用排除条件
    3. 计算因子得分
    4. 构建投资组合
    """

    def __init__(self, data_manager):
        """
        初始化策略

        Args:
            data_manager: 数据管理器
        """
        self.data_manager = data_manager
        self.name = "简单小市值策略"
        self.current_portfolio = {}

        # 配置
        self.universe_config = {'type': 'index', 'index_code': '399101.SZ'}
        self.portfolio_config = {'select_method': 'top_n', 'top_n': 10, 'weight_method': 'equal', 'risk_control': {'max_position_count': 20, 'max_single_weight': 0.2, 'min_single_weight': 0.05}}

    def get_stock_pool(self, date: str) -> List[str]:
        """
        获取股票池

        Args:
            date: 日期 (YYYYMMDD)

        Returns:
            股票列表
        """
        universe_config = self.universe_config

        if universe_config['type'] == 'index':
            index_code = universe_config['index_code']
            if self.data_manager is not None and hasattr(self.data_manager, 'get_index_components'):
                return self.data_manager.get_index_components(index_code, date)
            else:
                # 模拟模式：返回空列表
                print(f"[WARN] 未配置data_manager，无法获取指数成分股: {index_code}")
                print(f"       模拟模式：使用空股票池")
                return []

        return universe_config.get('codes', [])

    def apply_filters(self, stock_pool: List[str], date: str) -> List[str]:
        """
        应用排除条件

        Args:
            stock_pool: 股票列表
            date: 日期

        Returns:
            过滤后的股票列表
        """
        # TODO: 实现过滤逻辑
        return stock_pool

    def calculate_scores(self, stock_pool: List[str], date: str) -> Dict[str, float]:
        """
        计算因子得分（市值因子）

        Args:
            stock_pool: 股票列表
            date: 日期

        Returns:
            股票得分字典（市值越小，得分越高）
        """
        scores = {}

        if self.data_manager is not None:
            try:
                # 获取基本面数据（市值）
                fundamentals = self.data_manager.get_fundamentals(
                    codes=stock_pool,
                    date=date,
                    fields=['market_cap']  # 市值字段
                )

                if fundamentals is not None and not fundamentals.empty:
                    # 市值因子：市值越小越好（负相关）
                    for stock in stock_pool:
                        if stock in fundamentals.index:
                            market_cap = fundamentals.loc[stock, 'market_cap']
                            # 使用负市值作为得分，市值越小得分越高
                            scores[stock] = -market_cap
                        else:
                            # 没有市值数据的股票，给一个很低的得分
                            scores[stock] = -float('inf')
                else:
                    print("[WARN] 无法获取基本面数据，使用随机得分")
                    scores = {stock: 0.0 for stock in stock_pool}
            except Exception as e:
                print(f"[WARN] 计算市值因子失败: {e}")
                scores = {stock: 0.0 for stock in stock_pool}
        else:
            print("[WARN] data_manager未配置，无法计算市值因子")
            scores = {stock: 0.0 for stock in stock_pool}

        return scores

    def build_portfolio(self, scores: Dict[str, float], date: str) -> Dict[str, float]:
        """
        构建投资组合

        Args:
            scores: 股票得分
            date: 日期

        Returns:
            持仓权重字典
        """
        portfolio_config = self.portfolio_config

        # 选股
        if portfolio_config['select_method'] == 'top_n':
            top_n = portfolio_config['top_n']
            selected = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        else:
            selected = list(scores.items())

        # 分配权重
        if portfolio_config['weight_method'] == 'equal':
            weights = {stock: 1.0/len(selected) for stock, _ in selected}
        else:
            weights = dict(selected)

        return weights

    def run_rebalance(self, date: str) -> Dict[str, float]:
        """
        运行调仓逻辑

        Args:
            date: 日期

        Returns:
            目标持仓
        """
        # 1. 获取股票池
        stock_pool = self.get_stock_pool(date)

        # 2. 应用过滤
        filtered_stocks = self.apply_filters(stock_pool, date)

        # 3. 计算得分
        scores = self.calculate_scores(filtered_stocks, date)

        # 4. 构建组合
        portfolio = self.build_portfolio(scores, date)

        self.current_portfolio = portfolio

        return portfolio
