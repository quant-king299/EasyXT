# -*- coding: utf-8 -*-
"""
DuckDB数据源

提供从本地DuckDB数据库读取股票数据的功能
"""
import pandas as pd
from typing import List, Optional
from datetime import datetime, timedelta

from .base_source import BaseDataSource
from ..utils import normalize_symbol, validate_date, convert_date_format


class DuckDBSource(BaseDataSource):
    """
    DuckDB数据源

    从本地DuckDB数据库读取价格、基本面、交易日历等数据
    """

    def __init__(self, config: dict):
        """
        初始化DuckDB数据源

        Args:
            config: 配置字典，包含 path（数据库路径）
        """
        self.db_path = config.get('path')
        self.connection = None
        self._max_lookback_days = 30  # 最多向前查找天数

    def connect(self) -> bool:
        """
        连接到DuckDB数据库

        Returns:
            bool: 连接是否成功
        """
        import duckdb

        if not self.db_path:
            return False

        try:
            self.connection = duckdb.connect(self.db_path, read_only=True)
            # 测试连接
            test_query = "SELECT COUNT(*) FROM stock_daily LIMIT 1"
            self.connection.execute(test_query)
            return True
        except Exception as e:
            print(f"[DuckDBSource] 连接失败: {e}")
            return False

    def is_available(self) -> bool:
        """检查数据源是否可用"""
        return self.connection is not None

    def get_price(self,
                  symbols: List[str],
                  start_date: str,
                  end_date: str,
                  verbose: bool = True) -> Optional[pd.DataFrame]:
        """
        从DuckDB获取价格数据

        Args:
            symbols: 股票代码列表
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            verbose: 是否打印详细日志

        Returns:
            DataFrame: 价格数据
        """
        if not self.is_available():
            return None

        try:
            # 验证日期格式
            if not validate_date(start_date) or not validate_date(end_date):
                if verbose:
                    print(f"[DuckDBSource] 日期格式错误: {start_date} ~ {end_date}")
                return None

            # 标准化股票代码
            symbols = [self.normalize_symbol(s) for s in symbols]

            # 转换日期格式
            start = convert_date_format(start_date)
            end = convert_date_format(end_date)

            symbols_str = "', '".join(symbols)

            # 构建查询
            query = f"""
                SELECT
                    date,
                    stock_code as symbol,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    amount
                FROM stock_daily
                WHERE stock_code IN ('{symbols_str}')
                  AND date >= '{start}'
                  AND date <= '{end}'
                ORDER BY date, stock_code
            """

            # 执行查询
            df = self.connection.execute(query).df()

            if df.empty:
                if verbose:
                    print(f"[DuckDBSource] 未找到价格数据: {start_date} ~ {end_date}")
                return None

            # 设置MultiIndex
            df.set_index(['date', 'symbol'], inplace=True)

            if verbose:
                print(f"[DuckDBSource] 获取价格数据成功: {len(df)}条记录")

            return df

        except Exception as e:
            if verbose:
                print(f"[DuckDBSource] 获取价格数据失败: {e}")
            return None

    def get_fundamentals(self,
                         symbols: List[str],
                         date: str,
                         fields: Optional[List[str]] = None) -> Optional[pd.DataFrame]:
        """
        从DuckDB获取基本面数据

        注意：
        - 如果查询日期是非交易日，会自动使用最近的交易日数据
        - 每个股票取其最新的市值数据（date <= 查询日期）

        Args:
            symbols: 股票代码列表
            date: 查询日期 (YYYYMMDD)
            fields: 需要的字段列表（None表示所有字段）

        Returns:
            DataFrame: 基本面数据
        """
        if not self.is_available():
            return None

        try:
            # 验证日期格式
            if not validate_date(date):
                print(f"[DuckDBSource] 日期格式错误: {date}")
                return None

            # 标准化股票代码
            symbols = [self.normalize_symbol(s) for s in symbols]

            # 转换日期格式
            date_formatted = convert_date_format(date)

            # 检查请求的字段
            if fields is None:
                fields = ['circ_mv', 'total_mv']

            # 只支持市值相关字段（使用stock_market_cap表）
            supported_fields = ['circ_mv', 'total_mv']
            unsupported_fields = [f for f in fields if f not in supported_fields]

            if unsupported_fields:
                # 如果请求了不支持的字段，静默返回None，让fallback处理
                return None

            symbols_str = "', '".join(symbols)

            # ✅ 修复：简单的查询逻辑，然后对每个股票取最新一条
            # 避免窗口函数可能的兼容性问题
            query = f"""
                SELECT
                    stock_code as symbol,
                    circ_mv,
                    total_mv,
                    date
                FROM stock_market_cap
                WHERE stock_code IN ('{symbols_str}')
                  AND date <= '{date_formatted}'
                ORDER BY stock_code, date DESC
            """

            # 执行查询
            df = self.connection.execute(query).df()

            if df.empty:
                return None

            # 每个股票只保留最新的一条记录
            df = df.drop_duplicates(subset=['symbol'], keep='first')

            # 只返回请求的字段
            result = df[['symbol'] + fields].copy()

            return result

        except Exception as e:
            # 如果表不存在或其他错误，静默返回None
            # 让HybridDataManager的fallback机制处理
            import sys
            print(f"[DuckDBSource] 获取基本面数据失败: {e}", file=sys.stderr)
            return None

    def get_trading_dates(self,
                          start_date: str,
                          end_date: str) -> Optional[List[str]]:
        """
        从DuckDB获取交易日历

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            List[str]: 交易日列表 (YYYYMMDD格式)
        """
        if not self.is_available():
            return None

        try:
            # 验证日期格式
            if not validate_date(start_date) or not validate_date(end_date):
                return None

            # 转换日期格式
            start = convert_date_format(start_date)
            end = convert_date_format(end_date)

            # 构建查询
            query = f"""
                SELECT DISTINCT date
                FROM stock_daily
                WHERE date >= '{start}'
                  AND date <= '{end}'
                ORDER BY date
            """

            # 执行查询
            df = self.connection.execute(query).df()

            if df.empty:
                return None

            # 转换为YYYYMMDD格式
            trading_dates = df['date'].dt.strftime('%Y%m%d').tolist()

            return trading_dates

        except Exception as e:
            return None

    def get_stock_list(self, market_type: str = 'stock') -> Optional[List[str]]:
        """
        获取股票列表

        Args:
            market_type: 市场类型 ('stock', 'index', 'fund')

        Returns:
            List[str]: 股票代码列表
        """
        if not self.is_available():
            return None

        try:
            # 根据市场类型筛选
            if market_type == 'stock':
                # 股票代码以6开头或3开头
                pattern = "[360]\\d{4}"
            elif market_type == 'index':
                # 指数代码以其他开头
                pattern = "0\\d{5}"
            else:
                return None

            query = f"""
                SELECT DISTINCT stock_code
                FROM stock_daily
                WHERE stock_code SIMILAR TO '{pattern}'
                LIMIT 10000
            """

            df = self.connection.execute(query).df()

            if df.empty:
                return None

            return df['stock_code'].tolist()

        except Exception as e:
            return None

    def normalize_symbol(self, symbol: str) -> str:
        """标准化股票代码"""
        if isinstance(symbol, (int, float)):
            if isinstance(symbol, float) and symbol.is_integer():
                symbol = str(int(symbol))
            else:
                symbol = str(symbol)
        symbol = symbol.strip().upper()
        return symbol

    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
