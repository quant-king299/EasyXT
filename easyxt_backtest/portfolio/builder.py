"""
组合构建器

根据打分结果构建投资组合。
"""

from typing import List, Dict, Optional
import pandas as pd

try:
    from .weight_methods import WeightMethods
    from .risk_control import RiskControl
except ImportError:
    from easyxt_backtest.portfolio.weight_methods import WeightMethods
    from easyxt_backtest.portfolio.risk_control import RiskControl


class PortfolioBuilder:
    """
    组合构建器

    功能：
    1. 根据得分选股
    2. 分配权重
    3. 应用风险控制
    """

    def __init__(self, portfolio_config: Dict, data_manager=None):
        """
        初始化组合构建器

        Args:
            portfolio_config: 组合配置字典
            data_manager: 数据管理器（可选）
        """
        self.config = portfolio_config
        self.data_manager = data_manager

        # 提取配置参数
        self.select_method = portfolio_config.get('select_method', 'top_n')
        self.top_n = portfolio_config.get('top_n', 10)
        self.quantile = portfolio_config.get('quantile', 0.2)
        self.threshold = portfolio_config.get('threshold', 0.5)
        self.weight_method = portfolio_config.get('weight_method', 'equal')

        # 风控配置
        risk_config = portfolio_config.get('risk_control', {})
        self.risk_control = RiskControl(risk_config) if risk_config else None

    def build_portfolio(self,
                       scores: pd.Series,
                       date: str = None,
                       current_portfolio: Dict[str, float] = None) -> Dict[str, float]:
        """
        构建投资组合

        Args:
            scores: 股票得分Series (index=股票, values=得分)
            date: 日期（可选，用于获取额外数据）
            current_portfolio: 当前持仓（可选）

        Returns:
            Dict: {股票代码: 权重}
        """
        # 1. 选股
        selected_stocks = self._select_stocks(scores)

        if len(selected_stocks) == 0:
            print("⚠️ 没有股票被选中")
            return {}

        # 2. 分配权重
        weights = self._allocate_weights(selected_stocks, scores, date)

        # 3. 应用风控
        if self.risk_control:
            weights = self._apply_risk_control(weights, date, current_portfolio)

        # 4. 确保权重和为1
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}

        return weights

    def _select_stocks(self, scores: pd.Series) -> List[str]:
        """
        选股

        Args:
            scores: 股票得分Series

        Returns:
            选中的股票列表
        """
        # 去除NaN
        valid_scores = scores.dropna()

        if len(valid_scores) == 0:
            return []

        if self.select_method == 'top_n':
            # 选择得分最高的N只股票
            top_stocks = valid_scores.nlargest(self.top_n)
            return top_stocks.index.tolist()

        elif self.select_method == 'quantile':
            # 选择得分最高的分位数股票
            threshold = valid_scores.quantile(1 - self.quantile)
            selected = valid_scores[valid_scores >= threshold]
            return selected.index.tolist()

        elif self.select_method == 'threshold':
            # 选择得分大于阈值的股票
            selected = valid_scores[valid_scores >= self.threshold]
            return selected.index.tolist()

        else:
            raise ValueError(f"不支持的选股方法: {self.select_method}")

    def _allocate_weights(self,
                         stocks: List[str],
                         scores: pd.Series,
                         date: str = None) -> Dict[str, float]:
        """
        分配权重

        Args:
            stocks: 股票列表
            scores: 得分Series
            date: 日期

        Returns:
            权重字典
        """
        if self.weight_method == 'equal':
            # 等权重
            weights = WeightMethods.equal_weight(stocks)

        elif self.weight_method == 'market_cap':
            # 市值加权
            if self.data_manager is not None:
                market_cap_data = self._get_market_cap_data(stocks, date)
                weights = WeightMethods.market_cap_weight(stocks, market_cap_data)
            else:
                print("⚠️ 未提供data_manager，使用等权重")
                weights = WeightMethods.equal_weight(stocks)

        elif self.weight_method == 'factor_score':
            # 因子得分加权
            weights = WeightMethods.factor_score_weight(stocks, scores)

        elif self.weight_method == 'equal_risk':
            # 等风险权重
            if self.data_manager is not None:
                returns_data = self._get_returns_data(stocks, date)
                weights = WeightMethods.equal_risk_weight(stocks, returns_data)
            else:
                print("⚠️ 未提供data_manager，使用等权重")
                weights = WeightMethods.equal_weight(stocks)

        else:
            raise ValueError(f"不支持的权重方法: {self.weight_method}")

        return weights.to_dict()

    def _apply_risk_control(self,
                           weights: Dict[str, float],
                           date: str = None,
                           current_portfolio: Dict[str, float] = None) -> Dict[str, float]:
        """
        应用风控

        Args:
            weights: 权重字典
            date: 日期
            current_portfolio: 当前持仓

        Returns:
            调整后的权重
        """
        if self.risk_control is None:
            return weights

        # 获取行业数据
        industry_data = None
        if self.data_manager is not None and date is not None:
            industry_data = self._get_industry_data(list(weights.keys()), date)

        # 应用风控
        adjusted_weights = self.risk_control.apply_risk_control(
            weights,
            current_portfolio,
            industry_data
        )

        return adjusted_weights

    def _get_market_cap_data(self, stocks: List[str], date: str) -> pd.Series:
        """
        获取市值数据

        Args:
            stocks: 股票列表
            date: 日期

        Returns:
            市值Series
        """
        try:
            if hasattr(self.data_manager, 'get_fundamentals'):
                df = self.data_manager.get_fundamentals(
                    codes=stocks,
                    date=date,
                    fields=['market_cap']
                )
                return df['market_cap']
            else:
                return pd.Series(index=stocks, dtype=float)
        except Exception as e:
            print(f"⚠️ 获取市值数据失败: {e}")
            return pd.Series(index=stocks, dtype=float)

    def _get_returns_data(self, stocks: List[str], date: str) -> pd.DataFrame:
        """
        获取收益率数据

        Args:
            stocks: 股票列表
            date: 日期

        Returns:
            收益率DataFrame
        """
        # TODO: 实现获取历史收益率数据
        # 这里暂时返回空DataFrame
        return pd.DataFrame(index=stocks, columns=stocks)

    def _get_industry_data(self, stocks: List[str], date: str) -> pd.Series:
        """
        获取行业数据

        Args:
            stocks: 股票列表
            date: 日期

        Returns:
            行业Series
        """
        try:
            if hasattr(self.data_manager, 'get_industry'):
                return self.data_manager.get_industry(stocks, date)
            else:
                return pd.Series(index=stocks, dtype=str)
        except Exception as e:
            print(f"⚠️ 获取行业数据失败: {e}")
            return pd.Series(index=stocks, dtype=str)

    def get_portfolio_summary(self, portfolio: Dict[str, float]) -> str:
        """
        获取组合摘要

        Args:
            portfolio: 持仓字典

        Returns:
            组合摘要字符串
        """
        if not portfolio:
            return "空持仓"

        summary = f"持仓摘要:\n"
        summary += f"  持仓数量: {len(portfolio)}\n"
        summary += f"  权重范围: [{min(portfolio.values()):.2%}, {max(portfolio.values()):.2%}]\n"
        summary += f"  前5大持仓:\n"

        sorted_items = sorted(portfolio.items(), key=lambda x: x[1], reverse=True)
        for i, (stock, weight) in enumerate(sorted_items[:5]):
            summary += f"    {i+1}. {stock}: {weight:.2%}\n"

        return summary
