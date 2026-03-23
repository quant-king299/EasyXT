"""
权重管理器

管理因子权重的分配和调整。
"""

from typing import List, Dict
import pandas as pd
from ..config import FactorConfig


class WeightManager:
    """
    权重管理器

    功能：
    1. 验证权重和为1
    2. 动态调整权重
    3. 均等权重分配
    4. 基于IC值的权重优化
    """

    @staticmethod
    def validate_weights(factor_configs: List[FactorConfig]) -> bool:
        """
        验证因子权重和是否为1

        Args:
            factor_configs: 因子配置列表

        Returns:
            是否有效
        """
        total_weight = sum(f.weight for f in factor_configs)

        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"因子权重和必须为1.0，当前为{total_weight:.3f}")

        return True

    @staticmethod
    def normalize_weights(factor_configs: List[FactorConfig]) -> List[FactorConfig]:
        """
        归一化因子权重（使权重和为1）

        Args:
            factor_configs: 因子配置列表

        Returns:
            归一化后的因子配置列表
        """
        total_weight = sum(f.weight for f in factor_configs)

        if total_weight == 0:
            raise ValueError("因子权重和不能为0")

        # 归一化
        for config in factor_configs:
            config.weight = config.weight / total_weight

        return factor_configs

    @staticmethod
    def equal_weights(factor_configs: List[FactorConfig]) -> List[FactorConfig]:
        """
        均等权重分配

        Args:
            factor_configs: 因子配置列表

        Returns:
            均等权重分配后的因子配置列表
        """
        n_factors = len(factor_configs)

        if n_factors == 0:
            return factor_configs

        weight = 1.0 / n_factors

        for config in factor_configs:
            config.weight = weight

        return factor_configs

    @staticmethod
    def optimize_weights_by_ic(factor_configs: List[FactorConfig],
                               ic_values: Dict[str, float]) -> List[FactorConfig]:
        """
        基于IC值优化因子权重

        权重与IC绝对值成正比

        Args:
            factor_configs: 因子配置列表
            ic_values: 因子IC值字典 {factor_name: ic_value}

        Returns:
            优化后的因子配置列表
        """
        # 计算IC绝对值
        abs_ic_values = {name: abs(val) for name, val in ic_values.items()}

        # 计算权重
        total_abs_ic = sum(abs_ic_values.values())

        if total_abs_ic == 0:
            # 如果所有IC都为0，使用均等权重
            return WeightManager.equal_weights(factor_configs)

        # 分配权重
        for config in factor_configs:
            if config.name in abs_ic_values:
                config.weight = abs_ic_values[config.name] / total_abs_ic
            else:
                config.weight = 0

        return factor_configs

    @staticmethod
    def get_weight_summary(factor_configs: List[FactorConfig]) -> pd.DataFrame:
        """
        获取权重摘要

        Args:
            factor_configs: 因子配置列表

        Returns:
            DataFrame: 权重摘要
        """
        data = []

        for config in factor_configs:
            data.append({
                'factor_name': config.name,
                'factor_type': config.factor_type,
                'direction': '正相关' if config.direction == 1 else '负相关',
                'weight': config.weight,
                'normalize': '是' if config.normalize else '否',
                'neutralize': '是' if config.neutralize and config.neutralize.get('enabled', False) else '否'
            })

        df = pd.DataFrame(data)

        # 添加权重占比
        df['weight_pct'] = df['weight'].apply(lambda x: f"{x:.1%}")

        return df

    @staticmethod
    def adjust_weights(factor_configs: List[FactorConfig],
                      adjustments: Dict[str, float]) -> List[FactorConfig]:
        """
        手动调整因子权重

        Args:
            factor_configs: 因子配置列表
            adjustments: 权重调整字典 {factor_name: new_weight}

        Returns:
            调整后的因子配置列表
        """
        # 应用调整
        for config in factor_configs:
            if config.name in adjustments:
                config.weight = adjustments[config.name]

        # 归一化
        return WeightManager.normalize_weights(factor_configs)
