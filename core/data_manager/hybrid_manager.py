# -*- coding: utf-8 -*-
"""
混合数据管理器

统一的数据管理接口，支持多数据源自动选择和优雅降级
"""
import pandas as pd
from typing import Optional, List, Dict, Union
from datetime import datetime
import time

from .sources import BaseDataSource, DuckDBSource, TushareSource, QMTSource
from .config import DataManagerConfig, get_global_config
from .utils import (
    normalize_symbol,
    normalize_symbols,
    validate_date,
)


class HybridDataManager:
    """
    混合数据管理器

    特性：
    - 自动数据源选择（DuckDB > QMT > Tushare）
    - 优雅降级（一个数据源失败，自动切换到下一个）
    - 统一缓存策略
    - 批量操作优化
    - 完整的错误处理
    """

    def __init__(self,
                 config: Optional[DataManagerConfig] = None,
                 preferred_sources: Optional[List[str]] = None):
        """
        初始化混合数据管理器

        Args:
            config: 配置对象（None时使用全局配置）
            preferred_sources: 优先数据源列表 ['duckdb', 'qmt', 'tushare']
        """
        # 加载配置
        self.config = config or get_global_config()

        # 数据源优先级（默认：DuckDB > QMT > Tushare）
        self.source_priority = preferred_sources or self.config.get_preferred_sources()

        # 数据源实例
        self.sources: Dict[str, BaseDataSource] = {}

        # 缓存
        self.price_cache = {}
        self.fundamental_cache = {}
        self.trading_dates_cache = None

        # 统计信息
        self.stats = {
            'duckdb_queries': 0,
            'qmt_queries': 0,
            'tushare_queries': 0,
            'cache_hits': 0,
            'total_queries': 0
        }

        # 初始化数据源
        self._initialize_sources()

    def _initialize_sources(self):
        """初始化所有数据源"""
        print("[HybridDataManager] 正在初始化数据源...")

        # 初始化DuckDB
        if 'duckdb' in self.source_priority:
            try:
                duckdb_config = self.config.get_source_config('duckdb')
                duckdb_source = DuckDBSource(duckdb_config)
                if duckdb_source.connect():
                    self.sources['duckdb'] = duckdb_source
                    print("[HybridDataManager] [OK] DuckDB数据源已连接")
                else:
                    print("[HybridDataManager] [FAIL] DuckDB数据源连接失败")
            except Exception as e:
                print(f"[HybridDataManager] [FAIL] DuckDB初始化失败: {e}")

        # 初始化Tushare
        if 'tushare' in self.source_priority:
            try:
                tushare_config = self.config.get_source_config('tushare')
                if tushare_config.get('token'):
                    tushare_source = TushareSource(tushare_config)
                    if tushare_source.connect():
                        self.sources['tushare'] = tushare_source
                        print("[HybridDataManager] [OK] Tushare数据源已连接")
                    else:
                        print("[HybridDataManager] [FAIL] Tushare数据源连接失败")
                else:
                    print("[HybridDataManager] [FAIL] Tushare Token未提供")
            except Exception as e:
                print(f"[HybridDataManager] [FAIL] Tushare初始化失败: {e}")

        # 初始化QMT
        if 'qmt' in self.source_priority:
            try:
                qmt_config = self.config.get_source_config('qmt')
                qmt_source = QMTSource(qmt_config)
                if qmt_source.connect():
                    self.sources['qmt'] = qmt_source
                    print("[HybridDataManager] [OK] QMT数据源已连接")
                else:
                    print("[HybridDataManager] [FAIL] QMT数据源连接失败")
            except Exception as e:
                print(f"[HybridDataManager] [FAIL] QMT初始化失败: {e}")

        print(f"[HybridDataManager] 数据源初始化完成，可用数据源: {list(self.sources.keys())}")

    def get_price(self,
                  symbol: Union[str, List[str]],
                  start_date: str,
                  end_date: str,
                  period: str = '1d',
                  adjust: str = 'none',
                  preferred_source: Optional[str] = None,
                  verbose: bool = True) -> Optional[pd.DataFrame]:
        """
        获取价格数据（自动选择数据源）

        Args:
            symbol: 股票代码或代码列表
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 数据周期
            adjust: 复权类型
            preferred_source: 优先使用的数据源
            verbose: 是否打印详细日志

        Returns:
            DataFrame: 价格数据
        """
        self.stats['total_queries'] += 1

        # 标准化输入
        symbols = normalize_symbols(symbol) if isinstance(symbol, str) else normalize_symbols(symbol)
        symbols_str = ','.join(symbols) if isinstance(symbols, list) else symbols

        # 检查缓存
        cache_key = f"price:{symbols_str}:{start_date}:{end_date}"
        if cache_key in self.price_cache:
            self.stats['cache_hits'] += 1
            return self.price_cache[cache_key].copy()

        # 确定要尝试的数据源顺序
        if preferred_source and preferred_source in self.sources:
            sources_to_try = [preferred_source] + [s for s in self.source_priority if s != preferred_source and s in self.sources]
        else:
            sources_to_try = [s for s in self.source_priority if s in self.sources]

        # 按优先级尝试各个数据源
        for source_name in sources_to_try:
            source = self.sources.get(source_name)
            if not source or not source.is_available():
                continue

            try:
                if verbose:
                    print(f"[HybridDataManager] 尝试从 {source_name} 获取价格数据...")

                # 批量获取多只股票的数据
                all_data = []
                for s in symbols:
                    df = source.get_price(s, start_date, end_date, period, adjust)
                    if df is not None and not df.empty:
                        all_data.append(df)

                if all_data:
                    # 合并所有股票的数据
                    result = pd.concat(all_data, ignore_index=True)
                    # 缓存结果
                    self.price_cache[cache_key] = result.copy()
                    # 更新统计
                    self.stats[f'{source_name}_queries'] += 1
                    if verbose:
                        print(f"[HybridDataManager] [OK] 从 {source_name} 获取价格数据成功 ({len(result)}条记录)")
                    return result

            except Exception as e:
                if verbose:
                    print(f"[HybridDataManager] [FAIL] {source_name} 获取价格数据失败: {e}")
                continue

        if verbose:
            print(f"[HybridDataManager] [FAIL] 所有数据源均无法获取价格数据")
        return None

    def get_fundamentals(self,
                         symbols: Union[str, List[str]],
                         date: str,
                         fields: Optional[List[str]] = None,
                         preferred_source: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        获取基本面数据（自动选择数据源）

        Args:
            symbols: 股票代码或代码列表
            date: 查询日期 (YYYYMMDD)
            fields: 需要的字段列表
            preferred_source: 优先使用的数据源

        Returns:
            DataFrame: 基本面数据
        """
        self.stats['total_queries'] += 1

        # 标准化输入
        symbols = normalize_symbols(symbols) if isinstance(symbols, str) else normalize_symbols(symbols)

        # 检查缓存
        cache_key = f"fundamentals:{','.join(symbols)}:{date}"
        if cache_key in self.fundamental_cache:
            self.stats['cache_hits'] += 1
            return self.fundamental_cache[cache_key].copy()

        # ✅ 优化：如果查询日期是非交易日，自动使用最近的交易日数据
        actual_date = self._find_nearest_trading_date_with_data(date, symbols, fields)
        if actual_date != date:
            print(f"[HybridDataManager] {date}非交易日，使用{actual_date}数据")

        # 确定要尝试的数据源顺序
        if preferred_source and preferred_source in self.sources:
            sources_to_try = [preferred_source] + [s for s in self.source_priority if s != preferred_source and s in self.sources]
        else:
            sources_to_try = [s for s in self.source_priority if s in self.sources]

        # 按优先级尝试各个数据源
        for source_name in sources_to_try:
            source = self.sources.get(source_name)
            if not source or not source.is_available():
                continue

            try:
                print(f"[HybridDataManager] 尝试从 {source_name} 获取基本面数据...")

                # 使用实际日期（可能是最近的交易日）查询
                result = source.get_fundamentals(symbols, actual_date, fields)

                if result is not None and not result.empty:
                    # 缓存结果（使用原始日期作为key）
                    self.fundamental_cache[cache_key] = result.copy()
                    # 更新统计
                    self.stats[f'{source_name}_queries'] += 1
                    print(f"[HybridDataManager] [OK] 从 {source_name} 获取基本面数据成功 ({len(result)}只股票)")
                    return result

            except Exception as e:
                print(f"[HybridDataManager] [FAIL] {source_name} 获取基本面数据失败: {e}")
                continue

        print(f"[HybridDataManager] [FAIL] 所有数据源均无法获取基本面数据")
        return None

    def _find_nearest_trading_date_with_data(self, date: str, symbols: List[str], fields: List[str], max_days: int = 10) -> str:
        """
        查找最近的交易日（有基本面数据的日期）

        优先向后查找（使用最近的数据），如果向后找不到则向前查找（使用未来的数据）

        Args:
            date: 查询日期 (YYYYMMDD)
            symbols: 股票代码列表
            fields: 需要的字段
            max_days: 最多查找天数（向前和向后各max_days天）

        Returns:
            str: 最近的交易日 (YYYYMMDD格式)
        """
        from datetime import datetime, timedelta

        # 如果DuckDB可用，优先从DuckDB查找
        if 'duckdb' in self.sources:
            source = self.sources['duckdb']
            if source.is_available():
                date_obj = datetime.strptime(date, '%Y%m%d')

                # 1. 先向后查找（使用最近的数据）
                for i in range(max_days + 1):
                    if i == 0:
                        check_date = date
                    else:
                        check_date = (date_obj - timedelta(days=i)).strftime('%Y%m%d')

                    # 尝试获取数据
                    result = source.get_fundamentals(symbols[:5], check_date, fields)  # 只检查前5只，提高速度

                    if result is not None and not result.empty:
                        # 找到有数据的日期
                        if i > 0:
                            print(f"[HybridDataManager] {date}无数据，使用最近的交易日{check_date}")
                            return check_date
                        else:
                            return date

                # 2. 向后找不到，向前查找（使用未来的数据）
                # 这种情况发生在查询日期早于数据起始日期（如查询2024-01-01，但数据从2024-01-02开始）
                for i in range(1, max_days + 1):
                    check_date = (date_obj + timedelta(days=i)).strftime('%Y%m%d')

                    # 尝试获取数据
                    result = source.get_fundamentals(symbols[:5], check_date, fields)

                    if result is not None and not result.empty:
                        print(f"[HybridDataManager] {date}早于数据起始日期，使用{check_date}数据")
                        return check_date

        # 如果DuckDB找不到，返回原日期
        return date

    def get_trading_dates(self,
                          start_date: str,
                          end_date: str,
                          preferred_source: Optional[str] = None) -> Optional[List[str]]:
        """
        获取交易日历（自动选择数据源）

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            preferred_source: 优先使用的数据源

        Returns:
            List[str]: 交易日列表
        """
        self.stats['total_queries'] += 1

        # 检查缓存
        if self.trading_dates_cache:
            # 假设交易日历不常变化，可以长期缓存
            return self.trading_dates_cache.copy()

        # 确定要尝试的数据源顺序
        if preferred_source and preferred_source in self.sources:
            sources_to_try = [preferred_source] + [s for s in self.source_priority if s != preferred_source and s in self.sources]
        else:
            sources_to_try = [s for s in self.source_priority if s in self.sources]

        # 按优先级尝试各个数据源
        for source_name in sources_to_try:
            source = self.sources.get(source_name)
            if not source or not source.is_available():
                continue

            try:
                print(f"[HybridDataManager] 尝试从 {source_name} 获取交易日历...")

                result = source.get_trading_dates(start_date, end_date)

                if result:
                    # 缓存结果
                    self.trading_dates_cache = result.copy()
                    # 更新统计
                    self.stats[f'{source_name}_queries'] += 1
                    print(f"[HybridDataManager] [OK] 从 {source_name} 获取交易日历成功 ({len(result)}个交易日)")
                    return result

            except Exception as e:
                print(f"[HybridDataManager] [FAIL] {source_name} 获取交易日历失败: {e}")
                continue

        print(f"[HybridDataManager] [FAIL] 所有数据源均无法获取交易日历")
        return None

    def clear_cache(self):
        """清空所有缓存"""
        self.price_cache.clear()
        self.fundamental_cache.clear()
        self.trading_dates_cache = None

        # 同时清空各个数据源的缓存
        for source in self.sources.values():
            source.clear_cache()

        print("[HybridDataManager] 所有缓存已清空")

    def get_cache_info(self) -> Dict:
        """
        获取缓存信息

        Returns:
            Dict: 缓存统计信息
        """
        return {
            'price_cache_size': len(self.price_cache),
            'fundamental_cache_size': len(self.fundamental_cache),
            'trading_dates_cached': self.trading_dates_cache is not None,
            'total_cache_items': len(self.price_cache) + len(self.fundamental_cache),
        }

    def get_statistics(self) -> Dict:
        """
        获取统计信息

        Returns:
            Dict: 统计信息
        """
        return {
            **self.stats,
            'cache_hit_rate': f"{(self.stats['cache_hits'] / self.stats['total_queries'] * 100):.1f}%" if self.stats['total_queries'] > 0 else "0%",
            'available_sources': list(self.sources.keys()),
            'source_priority': self.source_priority,
        }

    def get_available_sources(self) -> List[str]:
        """
        获取可用的数据源列表

        Returns:
            List[str]: 可用数据源名称列表
        """
        return [name for name, source in self.sources.items() if source.is_available()]

    def close(self):
        """关闭所有数据源连接"""
        for source in self.sources.values():
            source.close()
        print("[HybridDataManager] 所有数据源连接已关闭")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()

    def __repr__(self) -> str:
        """字符串表示"""
        available = self.get_available_sources()
        return f"HybridDataManager(available_sources={available}, priority={self.source_priority})"