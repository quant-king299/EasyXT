"""
风险控制模块

提供组合风险控制功能。
"""

from typing import List, Dict
import pandas as pd


class RiskControl:
    """
    风险控制

    功能：
    1. 持仓数量限制
    2. 单股权重限制
    3. 行业权重限制
    4. 换手率限制
    """

    def __init__(self, risk_config: Dict):
        """
        初始化风险控制

        Args:
            risk_config: 风控配置字典
        """
        self.config = risk_config

        # 提取风控参数
        self.max_position_count = risk_config.get('max_position_count', 50)
        self.max_single_weight = risk_config.get('max_single_weight', 0.3)
        self.min_single_weight = risk_config.get('min_single_weight', 0.0)
        self.industry_max_weight = risk_config.get('industry_max_weight', 0.5)
        self.max_turnover = risk_config.get('max_turnover', 1.0)

    def check_position_count(self, stocks: List[str]) -> bool:
        """
        检查持仓数量

        Args:
            stocks: 股票列表

        Returns:
            是否符合风控要求
        """
        return len(stocks) <= self.max_position_count

    def check_single_weight(self, weights: pd.Series) -> bool:
        """
        检查单股权重

        Args:
            weights: 权重Series

        Returns:
            是否符合风控要求
        """
        # 检查最大权重
        if weights.max() > self.max_single_weight:
            return False

        # 检查最小权重
        if self.min_single_weight > 0:
            if (weights > 0).sum() * self.min_single_weight > 1.0:
                return False

        return True

    def check_industry_weight(self,
                             weights: pd.Series,
                             industry_data: pd.Series) -> bool:
        """
        检查行业权重

        Args:
            weights: 权重Series (index=股票)
            industry_data: 行业数据Series (index=股票)

        Returns:
            是否符合风控要求
        """
        # 计算每个行业的权重
        industry_weights = {}
        for stock in weights.index:
            if stock in industry_data.index:
                industry = industry_data.loc[stock]
                if pd.notna(industry):
                    industry_weights[industry] = industry_weights.get(industry, 0) + weights.loc[stock]

        # 检查是否有行业超限
        for industry, weight in industry_weights.items():
            if weight > self.industry_max_weight:
                return False

        return True

    def check_turnover(self,
                      current_portfolio: Dict[str, float],
                      target_portfolio: Dict[str, float]) -> bool:
        """
        检查换手率

        Args:
            current_portfolio: 当前持仓 {股票: 权重}
            target_portfolio: 目标持仓 {股票: 权重}

        Returns:
            是否符合风控要求
        """
        # 计算换手率
        turnover = self._calculate_turnover(current_portfolio, target_portfolio)

        return turnover <= self.max_turnover

    def _calculate_turnover(self,
                           current_portfolio: Dict[str, float],
                           target_portfolio: Dict[str, float]) -> float:
        """
        计算换手率

        换手率 = (买入金额 + 卖出金额) / 2 / 总资产

        Args:
            current_portfolio: 当前持仓
            target_portfolio: 目标持仓

        Returns:
            换手率
        """
        # 计算卖出
        sell = 0
        for stock, weight in current_portfolio.items():
            target_weight = target_portfolio.get(stock, 0)
            if weight > target_weight:
                sell += weight - target_weight

        # 计算买入
        buy = 0
        for stock, weight in target_portfolio.items():
            current_weight = current_portfolio.get(stock, 0)
            if weight > current_weight:
                buy += weight - current_weight

        # 换手率
        turnover = (buy + sell) / 2

        return turnover

    def apply_risk_control(self,
                          target_portfolio: Dict[str, float],
                          current_portfolio: Dict[str, float] = None,
                          industry_data: pd.Series = None) -> Dict[str, float]:
        """
        应用风险控制

        Args:
            target_portfolio: 目标持仓
            current_portfolio: 当前持仓
            industry_data: 行业数据

        Returns:
            调整后的持仓
        """
        result = target_portfolio.copy()

        # 1. 限制持仓数量
        if len(result) > self.max_position_count:
            # 选择权重最大的股票
            sorted_stocks = sorted(result.items(), key=lambda x: x[1], reverse=True)
            result = dict(sorted_stocks[:self.max_position_count])

        # 2. 限制单股权重
        weights_series = pd.Series(result)
        weights_series = weights_series.clip(upper=self.max_single_weight)
        weights_series = weights_series / weights_series.sum()
        result = weights_series.to_dict()

        # 3. 行业权重限制
        if industry_data is not None and not industry_data.empty:
            result = self._apply_industry_limit(result, industry_data)

        # 4. 重新归一化
        total_weight = sum(result.values())
        if total_weight > 0:
            result = {k: v / total_weight for k, v in result.items()}

        return result

    def _apply_industry_limit(self,
                             portfolio: Dict[str, float],
                             industry_data: pd.Series) -> Dict[str, float]:
        """
        应用行业权重限制

        Args:
            portfolio: 目标持仓
            industry_data: 行业数据

        Returns:
            调整后的持仓
        """
        # 计算行业权重
        industry_weights = {}
        for stock, weight in portfolio.items():
            if stock in industry_data.index:
                industry = industry_data.loc[stock]
                if pd.notna(industry):
                    industry_weights[industry] = industry_weights.get(industry, 0) + weight

        # 检查是否超限
        max_industry = max(industry_weights.values()) if industry_weights else 0

        if max_industry > self.industry_max_weight:
            # 按比例缩减
            scale = self.industry_max_weight / max_industry

            for stock in portfolio:
                if stock in industry_data.index:
                    industry = industry_data.loc[stock]
                    if pd.notna(industry) and industry_weights.get(industry, 0) > self.industry_max_weight:
                        portfolio[stock] *= scale

        return portfolio
