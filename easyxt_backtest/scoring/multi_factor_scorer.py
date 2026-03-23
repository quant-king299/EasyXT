"""
多因子打分器

综合多个因子对股票进行打分。
"""

from typing import List, Dict
import pandas as pd
import numpy as np

try:
    from ..config import FactorConfig
    from ..factors.calculator import FactorCalculator
except ImportError:
    from easyxt_backtest.config import FactorConfig
    from easyxt_backtest.factors.calculator import FactorCalculator


class MultiFactorScorer:
    """
    多因子打分器

    功能：
    1. 计算多个因子的值
    2. 应用因子方向（正相关/负相关）
    3. 应用因子权重
    4. 综合打分（加权求和）
    """

    def __init__(self, factor_configs: List[FactorConfig], data_manager):
        """
        初始化多因子打分器

        Args:
            factor_configs: 因子配置列表
            data_manager: 数据管理器
        """
        self.factor_configs = factor_configs
        self.data_manager = data_manager
        self.factor_calculator = FactorCalculator(data_manager)

        # 验证因子权重
        self._validate_weights()

    def calculate_scores(self, stock_pool: List[str], date: str, verbose: bool = False) -> pd.Series:
        """
        计算综合得分

        Args:
            stock_pool: 股票列表
            date: 日期 (YYYYMMDD)
            verbose: 是否打印详细信息

        Returns:
            Series: 股票代码到综合得分的映射
        """
        if verbose:
            print(f"\n📊 计算多因子得分 @ {date}")
            print(f"  股票池数量: {len(stock_pool)}")
            print(f"  因子数量: {len(self.factor_configs)}")

        all_scores = {}

        # 计算每个因子的得分
        for i, factor_config in enumerate(self.factor_configs):
            # 跳过权重为0的因子
            if factor_config.weight == 0:
                if verbose:
                    print(f"  ⏭️  跳过因子 [{factor_config.name}] (权重=0)")
                continue

            # 计算因子值
            if verbose:
                print(f"  📈 计算因子 [{factor_config.name}] (权重={factor_config.weight:.1%})...")

            factor_values = self.factor_calculator.calculate(
                stock_pool, date, factor_config
            )

            # 应用因子方向
            directed_values = factor_values * factor_config.direction

            # 应用权重
            weighted_values = directed_values * factor_config.weight

            # 存储加权后的因子得分
            all_scores[factor_config.name] = weighted_values

            if verbose:
                valid_count = weighted_values.notna().sum()
                print(f"     ✅ 有效股票数: {valid_count}/{len(stock_pool)}")

        # 综合打分（加权求和）
        if all_scores:
            scores_df = pd.DataFrame(all_scores)
            final_scores = scores_df.sum(axis=1)

            # 标准化最终得分
            final_scores = (final_scores - final_scores.mean()) / final_scores.std()

            if verbose:
                print(f"  ✅ 综合得分计算完成")
                print(f"     有效股票数: {final_scores.notna().sum()}/{len(stock_pool)}")
                print(f"     得分范围: [{final_scores.min():.2f}, {final_scores.max():.2f}]")

            return final_scores
        else:
            # 如果没有有效因子，返回全零
            return pd.Series(np.zeros(len(stock_pool)), index=stock_pool)

    def get_factor_contributions(self, stock_pool: List[str], date: str) -> pd.DataFrame:
        """
        获取每个因子的贡献度

        Args:
            stock_pool: 股票列表
            date: 日期

        Returns:
            DataFrame: 股票×因子的贡献度矩阵
        """
        all_scores = {}

        for factor_config in self.factor_configs:
            if factor_config.weight == 0:
                continue

            # 计算因子值
            factor_values = self.factor_calculator.calculate(
                stock_pool, date, factor_config
            )

            # 应用方向和权重
            directed_values = factor_values * factor_config.direction
            weighted_values = directed_values * factor_config.weight

            all_scores[factor_config.name] = weighted_values

        return pd.DataFrame(all_scores)

    def _validate_weights(self):
        """验证因子权重"""
        total_weight = sum(f.weight for f in self.factor_configs)

        if abs(total_weight - 1.0) > 0.01:
            print(f"⚠️ 警告: 因子权重和为{total_weight:.3f}，建议调整为1.0")

        # 检查权重范围
        for config in self.factor_configs:
            if not 0 <= config.weight <= 1:
                raise ValueError(f"因子 [{config.name}] 的权重必须在0-1之间")

    def get_factor_summary(self) -> str:
        """
        获取因子摘要

        Returns:
            因子摘要字符串
        """
        summary = "因子配置:\n"

        for config in self.factor_configs:
            direction_str = "正相关" if config.direction == 1 else "负相关"
            summary += f"  - {config.name}\n"
            summary += f"    类型: {config.factor_type}\n"
            summary += f"    方向: {direction_str}\n"
            summary += f"    权重: {config.weight:.1%}\n"
            summary += f"    标准化: {'是' if config.normalize else '否'}\n"
            if config.neutralize:
                neutralize_str = "是" if config.neutralize.get('enabled', False) else "否"
                summary += f"    中性化: {neutralize_str}\n"

        return summary
