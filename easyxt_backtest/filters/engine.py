"""
排除条件过滤器引擎

协调多个过滤器对股票池进行过滤。
"""

from typing import List

try:
    from .base import BaseFilter
    from .stock_status_filter import StockStatusFilter
    from .market_filter import MarketFilter
    from .industry_filter import IndustryFilter
    from .region_filter import RegionFilter
    from .fundamental_filter import FundamentalFilter
except ImportError:
    from easyxt_backtest.filters.base import BaseFilter
    from easyxt_backtest.filters.stock_status_filter import StockStatusFilter
    from easyxt_backtest.filters.market_filter import MarketFilter
    from easyxt_backtest.filters.industry_filter import IndustryFilter
    from easyxt_backtest.filters.region_filter import RegionFilter
    from easyxt_backtest.filters.fundamental_filter import FundamentalFilter


class ExcludeFilterEngine:
    """
    排除条件过滤器引擎

    按顺序应用多个过滤器对股票池进行过滤。
    """

    def __init__(self, filter_configs: List, data_manager):
        """
        初始化过滤器引擎

        Args:
            filter_configs: 过滤器配置列表
            data_manager: 数据管理器
        """
        self.filter_configs = filter_configs
        self.data_manager = data_manager
        self.filter_instances = self._init_filters()

    def _init_filters(self):
        """
        初始化过滤器实例

        Returns:
            dict: 过滤器名称到实例的映射
        """
        instances = {}

        for config in self.filter_configs:
            try:
                # 根据过滤器类型创建对应的过滤器实例
                if config.type == "stock_status":
                    instances[config.name] = StockStatusFilter(config, self.data_manager)
                elif config.type == "market":
                    instances[config.name] = MarketFilter(config, self.data_manager)
                elif config.type == "industry":
                    instances[config.name] = IndustryFilter(config, self.data_manager)
                elif config.type == "region":
                    instances[config.name] = RegionFilter(config, self.data_manager)
                elif config.type == "fundamental":
                    instances[config.name] = FundamentalFilter(config, self.data_manager)
                else:
                    print(f"⚠️ 不支持的过滤器类型: {config.type}")
            except Exception as e:
                print(f"⚠️ 初始化过滤器失败 [{config.name}]: {e}")

        return instances

    def filter(self, stock_pool: List[str], date: str, verbose: bool = False) -> List[str]:
        """
        应用所有过滤器

        Args:
            stock_pool: 待过滤的股票列表
            date: 日期 (YYYYMMDD)
            verbose: 是否打印过滤过程

        Returns:
            过滤后的股票列表
        """
        if not stock_pool:
            return []

        result = stock_pool.copy()
        initial_count = len(result)

        # 按顺序应用每个过滤器
        for name, filter_instance in self.filter_instances.items():
            before_count = len(result)
            result = filter_instance.filter(result, date)
            after_count = len(result)
            filtered_count = before_count - after_count

            if verbose and filtered_count > 0:
                print(f"  📊 过滤器 [{name}]: {before_count} -> {after_count} (过滤{filtered_count}只)")

        if verbose:
            final_count = len(result)
            total_filtered = initial_count - final_count
            print(f"  ✅ 过滤完成: {initial_count} -> {final_count} (总共过滤{total_filtered}只)")

        return result

    def get_filter_summary(self) -> str:
        """
        获取过滤器摘要

        Returns:
            过滤器摘要字符串
        """
        summary = "过滤器配置:\n"
        for config in self.filter_configs:
            summary += f"  - {config.name} ({config.type})\n"

        return summary
