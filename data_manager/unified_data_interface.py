#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据接口
实现DuckDB和QMT数据源的统一管理
优先使用DuckDB本地数据，自动回退到QMT在线数据，并自动保存到DuckDB

参考文档：docs/DUCKDB_COMPARISON_ANALYSIS.md
"""

import pandas as pd
import numpy as np
from typing import Optional, Union, List, Dict
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 导入五维复权管理器
from data_manager.duckdb_fivefold_adjust import FiveFoldAdjustmentManager


class UnifiedDataInterface:
    """
    统一数据接口

    功能：
    1. 优先从DuckDB读取（包含五维复权，速度快）
    2. 如无数据或数据不全，使用QMT在线获取
    3. 获取后自动保存到DuckDB
    4. 智能检测缺失数据
    5. 支持多种复权类型
    """

    def __init__(self, duckdb_path: str = r'D:/StockData/stock_data.ddb'):
        """
        初始化统一数据接口

        Args:
            duckdb_path: DuckDB数据库路径
        """
        self.duckdb_path = duckdb_path
        self.con = None
        self.qmt_available = False
        self._tables_initialized = False  # 记录表是否已初始化
        self.db_manager = None  # 使用连接池管理器

        # 初始化五维复权管理器
        self.adjustment_manager = FiveFoldAdjustmentManager(duckdb_path)

        # 尝试导入DuckDB
        try:
            import duckdb
            self.duckdb_available = True
            print("[INFO] DuckDB 可用")
        except ImportError:
            self.duckdb_available = False
            print("[WARNING] DuckDB 不可用，将仅使用QMT数据")

        # 尝试导入QMT
        try:
            from xtquant import xtdata
            self.qmt_available = True
            print("[INFO] QMT xtdata 可用")
        except ImportError:
            self.qmt_available = False
            print("[WARNING] QMT xtdata 不可用")

    def connect(self, read_only: bool = False):
        """
        连接DuckDB数据库（使用连接池管理器）

        Args:
            read_only: 是否只读模式（首次建表需要写权限）

        修复：首次使用时允许写模式以创建表
        """
        if not self.duckdb_available:
            return False

        try:
            # 使用连接池管理器（解决并发冲突）
            from data_manager.duckdb_connection_pool import get_db_manager

            if self.db_manager is None:
                self.db_manager = get_db_manager(self.duckdb_path)

            # 获取连接（注意：这里获取的是非上下文管理器的连接）
            # 为了兼容现有代码，我们这里仍保持self.con
            import duckdb
            from pathlib import Path

            # 确保目录存在
            Path(self.duckdb_path).parent.mkdir(parents=True, exist_ok=True)

            # 直接创建连接（实际使用时会配合连接池的写锁）
            if read_only and self._tables_initialized:
                self.con = duckdb.connect(self.duckdb_path, read_only=True)
            else:
                self.con = duckdb.connect(self.duckdb_path)

            # 配置性能
            self.con.execute("PRAGMA threads=4")
            self.con.execute("PRAGMA memory_limit='4GB'")

            print("[INFO] DuckDB 连接成功")
            return True
        except Exception as e:
            print(f"[ERROR] DuckDB 连接失败: {e}")
            self.con = None
            return False

    def _ensure_tables_exist(self):
        """确保所有必需的表都存在

        修复：首次使用时自动创建表，避免"Table does not exist"错误
        """
        if not self.con or self._tables_initialized:
            return

        try:
            # 创建 stock_daily 表（日线）
            self.con.execute("""
                CREATE TABLE IF NOT EXISTS stock_daily (
                    stock_code VARCHAR NOT NULL,
                    symbol_type VARCHAR NOT NULL,
                    date DATE NOT NULL,
                    period VARCHAR NOT NULL,
                    open DECIMAL(18, 6),
                    high DECIMAL(18, 6),
                    low DECIMAL(18, 6),
                    close DECIMAL(18, 6),
                    volume BIGINT,
                    amount DECIMAL(18, 6),
                    adjust_type VARCHAR DEFAULT 'none',
                    factor DECIMAL(18, 6) DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (stock_code, date, period, adjust_type)
                )
            """)

            # 创建 stock_1m 表（1分钟线）
            self.con.execute("""
                CREATE TABLE IF NOT EXISTS stock_1m (
                    stock_code VARCHAR NOT NULL,
                    symbol_type VARCHAR NOT NULL,
                    datetime TIMESTAMP NOT NULL,
                    period VARCHAR NOT NULL,
                    open DECIMAL(18, 6),
                    high DECIMAL(18, 6),
                    low DECIMAL(18, 6),
                    close DECIMAL(18, 6),
                    volume BIGINT,
                    amount DECIMAL(18, 6),
                    adjust_type VARCHAR DEFAULT 'none',
                    factor DECIMAL(18, 6) DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (stock_code, datetime, period, adjust_type)
                )
            """)

            # 创建 stock_5m 表（5分钟线）
            self.con.execute("""
                CREATE TABLE IF NOT EXISTS stock_5m (
                    stock_code VARCHAR NOT NULL,
                    symbol_type VARCHAR NOT NULL,
                    datetime TIMESTAMP NOT NULL,
                    period VARCHAR NOT NULL,
                    open DECIMAL(18, 6),
                    high DECIMAL(18, 6),
                    low DECIMAL(18, 6),
                    close DECIMAL(18, 6),
                    volume BIGINT,
                    amount DECIMAL(18, 6),
                    adjust_type VARCHAR DEFAULT 'none',
                    factor DECIMAL(18, 6) DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (stock_code, datetime, period, adjust_type)
                )
            """)

            # 创建 stock_tick 表（tick数据）
            self.con.execute("""
                CREATE TABLE IF NOT EXISTS stock_tick (
                    stock_code VARCHAR NOT NULL,
                    symbol_type VARCHAR NOT NULL,
                    datetime TIMESTAMP NOT NULL,
                    period VARCHAR NOT NULL,
                    open DECIMAL(18, 6),
                    high DECIMAL(18, 6),
                    low DECIMAL(18, 6),
                    close DECIMAL(18, 6),
                    volume BIGINT,
                    amount DECIMAL(18, 6),
                    adjust_type VARCHAR DEFAULT 'none',
                    factor DECIMAL(18, 6) DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (stock_code, datetime, period, adjust_type)
                )
            """)

            # 创建索引
            try:
                self.con.execute("CREATE INDEX IF NOT EXISTS idx_stock_code_daily ON stock_daily (stock_code)")
                self.con.execute("CREATE INDEX IF NOT EXISTS idx_date_daily ON stock_daily (date)")
            except:
                pass  # 索引可能已存在

            self._tables_initialized = True
            print("[INFO] 数据表检查完成")

        except Exception as e:
            print(f"[WARNING] 创建表失败: {e}")

    def get_stock_data(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        period: str = '1d',
        adjust: str = 'none',
        auto_save: bool = True
    ) -> pd.DataFrame:
        """
        获取股票数据（统一入口）

        修复：首次使用时自动创建表

        数据获取策略：
        1. 优先从DuckDB读取（包含五维复权，速度快）
        2. 如DuckDB无数据或数据不全，使用QMT在线获取
        3. 获取后自动保存到DuckDB

        Args:
            stock_code: 股票代码（如 '511380.SH'）
            start_date: 开始日期（'YYYY-MM-DD'）
            end_date: 结束日期（'YYYY-MM-DD'）
            period: 数据周期（'1d'=日线, '1m'=分钟, '5m'=5分钟, 'tick'=tick）
            adjust: 复权类型（'none'=不复权, 'front'=前复权, 'back'=后复权,
                                 'geometric_front'=等比前复权, 'geometric_back'=等比后复权）
            auto_save: 是否自动保存到DuckDB

        Returns:
            DataFrame: 包含 OHLCV 数据
        """
        print(f"\n[获取数据] {stock_code} | {start_date} ~ {end_date} | {period} | {adjust}")

        # 确保数据库已连接
        if self.duckdb_available and self.con is None:
            self.connect(read_only=True)

        # 确保表存在（修复首次使用问题）
        self._ensure_tables_exist()

        # Step 1: 尝试从DuckDB读取（使用QMT API复权方案）
        data = None
        if self.duckdb_available and self.con:
            print(f"  [INFO] 使用QMT API复权方案查询数据 [股票:{stock_code}]")

            try:
                # 导入复权缓存模块
                from data_manager.adjustment_cache import AdjustmentCache

                if not hasattr(self, 'adjustment_cache'):
                    self.adjustment_cache = AdjustmentCache(self.duckdb_path)

                # 使用缓存管理器获取数据
                if period == '1d':
                    data = self.adjustment_cache.get_adjusted_data(
                        stock_code=stock_code,
                        start_date=start_date,
                        end_date=end_date,
                        adjust_type=adjust,
                        con=self.con
                    )

                    if data is not None and not data.empty:
                        print(f"  [OK] 从DuckDB获取成功 {len(data)} 条记录 [股票:{stock_code}]")
                        # 验证stock_code列是否存在且正确
                        if 'stock_code' in data.columns and not data.empty:
                            actual_codes = data['stock_code'].unique()
                            print(f"  [DEBUG] 返回数据中的stock_code: {actual_codes}")
                    else:
                        data = None
                else:
                    # 分钟线数据不需要复权，直接查询
                    data = self._read_from_duckdb(stock_code, start_date, end_date, period, 'none')

            except Exception as e:
                print(f"  [WARN] 复权缓存查询失败: {e}")
                print(f"  [INFO] 降级到原有的_read_from_duckdb方法")
                # 降级到原有的 _read_from_duckdb 方法
                data = self._read_from_duckdb(stock_code, start_date, end_date, period, adjust)

        # Step 2: 检查数据完整性
        need_download = False

        if data is None or data.empty:
            print(f"  → DuckDB 无数据，需要从在线数据源获取")
            need_download = True
        else:
            # 检查是否有缺失
            missing_days = self._check_missing_trading_days(data, start_date, end_date)
            if missing_days > 0:
                print(f"  → DuckDB 数据不完整（缺失 {missing_days} 个交易日），需要补充")
                need_download = True

        # Step 3: 如需下载，使用QMT获取
        if need_download:
            if not self.qmt_available:
                print(f"  [ERROR] QMT 不可用，无法获取在线数据")
                return data if data is not None else pd.DataFrame()

            print(f"  → 从 QMT 获取在线数据...")
            qmt_data = self._read_from_qmt(stock_code, start_date, end_date, period)

            if qmt_data is None or qmt_data.empty:
                print(f"  [ERROR] QMT 数据获取失败")
                return data if data is not None else pd.DataFrame()

            print(f"  [DEBUG] QMT返回 {len(qmt_data)} 条记录")

            # 合并数据（DuckDB有的就用，没有的补充）
            if data is not None and not data.empty:
                print(f"  → 合并 DuckDB 和 QMT 数据...")
                print(f"  [DEBUG] 合并前 - DuckDB: {len(data)}条, QMT: {len(qmt_data)}条")
                try:
                    merged_data = self._merge_data(data, qmt_data)
                    print(f"  [DEBUG] 合并后: {len(merged_data)}条")
                    data = merged_data
                except Exception as e:
                    print(f"  [ERROR] 合并失败: {e}")
                    import traceback
                    traceback.print_exc()
                    # 降级：只使用QMT数据
                    data = qmt_data
            else:
                data = qmt_data

            # Step 4: 保存到DuckDB
            if auto_save and self.duckdb_available and self.con:
                print(f"  → 保存数据到 DuckDB...")
                self._save_to_duckdb(data, stock_code, period)
                print(f"  [OK] 数据已保存到 DuckDB")
        else:
            print(f"  [OK] 从 DuckDB 读取成功（{len(data)} 条记录）")

        # Step 5: 应用复权
        if not data.empty and adjust != 'none':
            data = self._apply_adjustment(data, adjust)

        return data

    def _read_from_duckdb(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        period: str,
        adjust: str
    ) -> Optional[pd.DataFrame]:
        """从DuckDB读取数据 - 修复版（添加表存在性检查）"""
        try:
            # 确定表名
            table_map = {
                '1d': 'stock_daily',
                '1m': 'stock_1m',
                '5m': 'stock_5m',
                'tick': 'stock_tick'
            }
            table_name = table_map.get(period, 'stock_daily')

            # 检查表是否存在（修复首次使用问题）
            table_exists = self.con.execute(f"""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = '{table_name}'
            """).fetchone()[0] > 0

            if not table_exists:
                print(f"  [INFO] 表 {table_name} 不存在，返回空数据")
                return None

            # 确定列名（根据复权类型）
            # 确定表名
            table_map = {
                '1d': 'stock_daily',
                '1m': 'stock_1m',
                '5m': 'stock_5m',
                'tick': 'stock_tick'
            }
            table_name = table_map.get(period, 'stock_daily')

            # 确定列名（根据复权类型）
            if adjust == 'none':
                price_cols = ['open', 'high', 'low', 'close']
            elif adjust == 'front':
                price_cols = ['open_front', 'high_front', 'low_front', 'close_front']
            elif adjust == 'back':
                price_cols = ['open_back', 'high_back', 'low_back', 'close_back']
            elif adjust == 'geometric_front':
                price_cols = ['open_geometric_front', 'high_geometric_front',
                            'low_geometric_front', 'close_geometric_front']
            elif adjust == 'geometric_back':
                price_cols = ['open_geometric_back', 'high_geometric_back',
                            'low_geometric_back', 'close_geometric_back']
            else:
                price_cols = ['open', 'high', 'low', 'close']

            # 构建SQL
            sql = f"""
                SELECT
                    stock_code,
                    date as datetime,
                    {price_cols[0]} as open,
                    {price_cols[1]} as high,
                    {price_cols[2]} as low,
                    {price_cols[3]} as close,
                    volume,
                    amount
                FROM {table_name}
                WHERE stock_code = '{stock_code}'
                    AND date >= '{start_date}'
                    AND date <= '{end_date}'
                ORDER BY date
            """

            # 执行查询
            df = self.con.execute(sql).df()

            if not df.empty:
                # 转换datetime列
                df['datetime'] = pd.to_datetime(df['datetime'])
                df.set_index('datetime', inplace=True)
                df.index.name = 'datetime'  # 明确命名索引

                # 删除全为NaN的列（某些复权类型可能不存在）
                df = df.dropna(axis=1, how='all')

            return df

        except Exception as e:
            # 可能是表不存在或列不存在
            return None

    def _read_from_qmt(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        period: str
    ) -> Optional[pd.DataFrame]:
        """从QMT读取数据"""
        try:
            from xtquant import xtdata

            print(f"    [DEBUG] _read_from_qmt: 开始获取 {stock_code} 数据...")

            # 转换日期格式
            start_str = start_date.replace('-', '')
            end_str = end_date.replace('-', '')

            # QMT的period参数：1d, 1m, 5m, tick 直接使用
            qmt_period = period

            print(f"    [DEBUG] 调用 download_history_data: {stock_code}, {qmt_period}, {start_str} ~ {end_str}")
            # 下载历史数据
            xtdata.download_history_data(
                stock_code=stock_code,
                period=qmt_period,
                start_time=start_str,
                end_time=end_str
            )
            print(f"    [DEBUG] download_history_data 完成")

            # 获取数据
            print(f"    [DEBUG] 调用 get_market_data...")
            data = xtdata.get_market_data(
                stock_list=[stock_code],
                period=qmt_period,
                start_time=start_str,
                end_time=end_str,
                count=0
            )

            if not data or 'time' not in data:
                print(f"    [WARN] QMT返回数据为空或缺少time列")
                return None

            print(f"    [DEBUG] get_market_data 完成，数据keys: {list(data.keys())}")

            # 转换为DataFrame
            time_df = data['time']
            timestamps = time_df.columns.tolist()

            print(f"    [DEBUG] 开始解析 {len(timestamps)} 条时间戳...")

            records = []
            for idx, ts in enumerate(timestamps):
                try:
                    # 修复时区问题：明确处理时间戳转换
                    if isinstance(ts, (int, float)) and ts > 1e10:  # 毫秒时间戳
                        dt = pd.to_datetime(ts, unit='ms', utc=True).tz_convert('Asia/Shanghai')
                    else:
                        dt = pd.to_datetime(ts)
                    records.append({
                        'datetime': dt,
                        'code': stock_code,
                        'open': float(data['open'].iloc[0, idx]),
                        'high': float(data['high'].iloc[0, idx]),
                        'low': float(data['low'].iloc[0, idx]),
                        'close': float(data['close'].iloc[0, idx]),
                        'volume': float(data['volume'].iloc[0, idx]),
                        'amount': float(data['amount'].iloc[0, idx])
                    })
                except Exception as e:
                    print(f"    [WARN] 解析第{idx}条记录失败: {e}")
                    continue

            if not records:
                print(f"    [WARN] 没有成功解析任何记录")
                return None

            print(f"    [DEBUG] 成功解析 {len(records)} 条记录")

            df = pd.DataFrame(records)
            df.set_index('datetime', inplace=True)
            df.index.name = 'datetime'  # 明确命名索引
            df.sort_index(inplace=True)

            # 输出日期范围
            if not df.empty:
                print(f"    [DEBUG] QMT数据日期范围: {df.index.min()} ~ {df.index.max()}")

            # 删除重复索引
            df = df[~df.index.duplicated(keep='first')]

            print(f"    [OK] _read_from_qmt 完成，返回 {len(df)} 条记录")

            return df

        except Exception as e:
            print(f"  [ERROR] QMT 数据获取失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_dividends_from_qmt(
        self,
        stock_code: str,
        start_date,
        end_date
    ) -> Optional[pd.DataFrame]:
        """
        从QMT获取分红数据，用于计算复权价格

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame: 分红数据，包含 ex_date, dividend_per_share 等列
        """
        try:
            from xtquant import xtdata

            # 转换日期格式
            start_str = pd.to_datetime(start_date).strftime('%Y%m%d')
            end_str = pd.to_datetime(end_date).strftime('%Y%m%d')

            # 调用QMT接口获取分红数据
            divid_data = xtdata.get_divid_factors(stock_code, start_str, end_str)

            if divid_data is None or divid_data.empty:
                print(f"    [INFO] 无分红数据: {stock_code}")
                return pd.DataFrame()

            # 转换为标准格式
            # QMT返回的数据可能包含多列，我们需要提取必要的列
            dividends_df = pd.DataFrame()

            # 检查返回的数据结构并提取需要的字段
            if isinstance(divid_data, pd.DataFrame):
                # 尝试映射列名
                col_mapping = {
                    'date': 'ex_date',
                    'ex_date': 'ex_date',
                    'exDivDate': 'ex_date',
                    'bonus_date': 'ex_date',
                    'dividend': 'dividend_per_share',
                    'dividend_per_share': 'dividend_per_share',
                    'cashBonus': 'dividend_per_share',
                    'bonus_ratio': 'bonus_ratio',
                    'bonusRatio': 'bonus_ratio',
                    'rightsissue_ratio': 'rights_issue_ratio',
                }

                # 查找实际的列名
                actual_cols = {}
                for qmt_col, std_col in col_mapping.items():
                    if qmt_col in divid_data.columns:
                        actual_cols[std_col] = qmt_col

                # 提取数据
                for std_col, qmt_col in actual_cols.items():
                    dividends_df[std_col] = divid_data[qmt_col]

                # 确保有ex_date列
                if 'ex_date' not in dividends_df.columns and len(divid_data.columns) > 0:
                    # 尝试使用第一列作为ex_date
                    dividends_df['ex_date'] = divid_data.iloc[:, 0]

                # 确保有dividend_per_share列
                if 'dividend_per_share' not in dividends_df.columns and len(divid_data.columns) > 1:
                    dividends_df['dividend_per_share'] = divid_data.iloc[:, 1]

                if not dividends_df.empty and 'ex_date' in dividends_df.columns:
                    # 确保日期格式正确
                    dividends_df['ex_date'] = pd.to_datetime(dividends_df['ex_date']).dt.date
                    print(f"    [OK] 获取 {len(dividends_df)} 条分红记录")
                    return dividends_df
                else:
                    print(f"    [WARN] 分红数据格式不符，无法使用")
                    return pd.DataFrame()

            return pd.DataFrame()

        except Exception as e:
            print(f"    [WARN] 获取分红数据失败: {e}")
            return pd.DataFrame()

    def _check_missing_trading_days(
        self,
        data: pd.DataFrame,
        start_date: str,
        end_date: str
    ) -> int:
        """检查缺失的交易日数量"""
        if data.empty:
            return 9999  # 返回一个很大的数表示需要下载

        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        # 简单估算：假设每天250个交易日/年
        expected_days = (end - start).days * 250 / 365
        actual_days = len(data)

        # 如果实际数据少于预期的80%，认为需要补充
        if actual_days < expected_days * 0.8:
            return int(expected_days - actual_days)

        return 0

    def _merge_data(
        self,
        duckdb_data: pd.DataFrame,
        qmt_data: pd.DataFrame
    ) -> pd.DataFrame:
        """合并DuckDB和QMT数据"""
        print(f"    [DEBUG] _merge_data: 开始合并...")

        # 确保索引类型一致（统一转换为datetime索引）
        def ensure_datetime_index(df, name=""):
            """确保DataFrame有datetime类型的日期索引"""
            if df.empty:
                print(f"      [DEBUG] {name} 为空，跳过")
                return df

            # 检查是否有datetime/date列
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
                df = df.set_index('datetime')
                df.index.name = 'datetime'  # 明确命名索引
            elif 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
                df.index.name = 'date'  # 明确命名索引
            # 如果已经有索引，确保是datetime类型
            elif not isinstance(df.index, pd.DatetimeIndex):
                # 尝试将当前索引转换为datetime
                try:
                    df.index = pd.to_datetime(df.index)
                    df.index.name = 'date'  # 明确命名索引
                except:
                    print(f"  [WARN] 无法转换{name}的索引类型: {type(df.index)}")
            else:
                # 已经是DatetimeIndex，确保有名字
                if df.index.name is None:
                    df.index.name = 'date'

            print(f"      [DEBUG] {name}: {len(df)}条, 索引类型={type(df.index).__name__}, 索引名={df.index.name}")
            return df

        # 标准化索引
        print(f"    [DEBUG] 标准化索引...")
        duckdb_data = ensure_datetime_index(duckdb_data, "DuckDB数据")
        qmt_data = ensure_datetime_index(qmt_data, "QMT数据")

        # 使用QMT数据作为基础
        merged = qmt_data.copy()
        print(f"    [DEBUG] 复制QMT数据作为基础: {len(merged)}条")

        # 找出DuckDB中有但QMT中没有的日期（用DuckDB补充）
        duckdb_dates = set(duckdb_data.index)
        qmt_dates = set(qmt_data.index)

        print(f"    [DEBUG] DuckDB日期数: {len(duckdb_dates)}, QMT日期数: {len(qmt_dates)}")

        only_in_duckdb = duckdb_dates - qmt_dates
        print(f"    [DEBUG] 仅在DuckDB中的日期数: {len(only_in_duckdb)}")

        if only_in_duckdb:
            # 使用.loc[]选择行
            print(f"    [DEBUG] 添加 {len(only_in_duckdb)} 条DuckDB独有数据...")
            additional = duckdb_data.loc[list(only_in_duckdb)]
            merged = pd.concat([merged, additional]).sort_index()
            print(f"    [DEBUG] 合并后总计: {len(merged)}条")

        # 删除重复索引
        before_dedup = len(merged)
        merged = merged[~merged.index.duplicated(keep='first')]
        after_dedup = len(merged)
        if before_dedup != after_dedup:
            print(f"    [DEBUG] 删除 {before_dedup - after_dedup} 条重复记录")

        print(f"    [OK] _merge_data 完成，返回 {len(merged)} 条记录")
        return merged

    def _save_to_duckdb(
        self,
        data: pd.DataFrame,
        stock_code: str,
        period: str
    ):
        """保存数据到DuckDB - 使用连接池确保原子性"""
        try:
            print(f"    [DEBUG] _save_to_duckdb: 开始保存 {stock_code} 的 {len(data)} 条记录...")

            # 使用连接池的写锁（确保原子性操作）
            from data_manager.duckdb_connection_pool import get_db_manager

            if self.db_manager is None:
                self.db_manager = get_db_manager(self.duckdb_path)

            # 使用写连接的上下文管理器（自动处理并发冲突）
            with self.db_manager.get_write_connection() as con:
                print(f"    [DEBUG] 获取写连接成功")

                # 确保表存在
                self._ensure_tables_exist_with_con(con)

                # 确定表名
                table_map = {
                    '1d': 'stock_daily',
                    '1m': 'stock_1m',
                    '5m': 'stock_5m',
                    'tick': 'stock_tick'
                }
                table_name = table_map.get(period, 'stock_daily')

                # 重置索引，把datetime变成列
                df_to_save = data.reset_index()
                df_to_save = df_to_save.rename(columns={'index': 'date', 'datetime': 'date'})

                print(f"    [DEBUG] reset_index后列名: {list(df_to_save.columns)[:5]}...")
                print(f"    [DEBUG] 保存数据日期范围: {df_to_save['date'].min()} ~ {df_to_save['date'].max()}")

                # 确保有stock_code列
                if 'stock_code' not in df_to_save.columns:
                    df_to_save['stock_code'] = stock_code

                # 确保有period列
                if 'period' not in df_to_save.columns:
                    df_to_save['period'] = period

                # 确保有symbol_type列
                if 'symbol_type' not in df_to_save.columns:
                    # 判断是股票、指数还是ETF
                    if stock_code.endswith('.SH'):
                        if stock_code.startswith('5') or stock_code.startswith('51'):
                            df_to_save['symbol_type'] = 'etf'
                        elif stock_code.startswith('688'):
                            df_to_save['symbol_type'] = 'stock'
                        else:
                            df_to_save['symbol_type'] = 'stock'
                    elif stock_code.endswith('.SZ'):
                        if stock_code.startswith('15') or stock_code.startswith('16'):
                            df_to_save['symbol_type'] = 'etf'
                        elif stock_code.startswith('30'):
                            df_to_save['symbol_type'] = 'stock'
                        else:
                            df_to_save['symbol_type'] = 'stock'
                    else:
                        df_to_save['symbol_type'] = 'stock'

                # 删除已存在的重复数据
                date_min = str(df_to_save['date'].min())
                date_max = str(df_to_save['date'].max())

                print(f"    [DEBUG] 删除范围: {date_min} ~ {date_max}")

                delete_sql = f"""
                    DELETE FROM {table_name}
                    WHERE stock_code = '{stock_code}'
                        AND date >= '{date_min}'
                        AND date <= '{date_max}'
                """
                con.execute(delete_sql)
                print(f"    [DEBUG] DELETE执行完成")

                # 添加缺失的列
                if table_name == 'stock_daily':
                    if 'adjust_type' not in df_to_save.columns:
                        df_to_save['adjust_type'] = 'none'
                    if 'factor' not in df_to_save.columns:
                        df_to_save['factor'] = 1.0

                    import time
                    current_time = pd.Timestamp.now()
                    if 'created_at' not in df_to_save.columns:
                        df_to_save['created_at'] = current_time
                    if 'updated_at' not in df_to_save.columns:
                        df_to_save['updated_at'] = current_time

                # 获取表的列顺序
                table_columns = con.execute(f"DESCRIBE {table_name}").fetchdf()['column_name'].tolist()

                # 按表的列顺序重新排列DataFrame
                df_ordered = pd.DataFrame()
                for col in table_columns:
                    if col in df_to_save.columns:
                        df_ordered[col] = df_to_save[col]
                    else:
                        df_ordered[col] = None

                print(f"    [DEBUG] 准备插入 {len(df_ordered)} 条记录...")

                # 策略：使用DELETE+INSERT确保数据保存成功
                try:
                    # 注册临时表
                    con.register('df_to_save_temp', df_ordered)

                    # 先删除重复数据
                    print(f"    [DEBUG] 删除重复数据...")
                    con.execute(f"""
                        DELETE FROM {table_name}
                        WHERE stock_code = '{stock_code}'
                            AND date >= '{date_min}'
                            AND date <= '{date_max}'
                    """)

                    # 插入新数据（明确指定所有列，避免列数不匹配）
                    print(f"    [DEBUG] 插入新数据...")
                    con.execute(f"""
                        INSERT INTO {table_name} (
                            stock_code, symbol_type, date, period,
                            open, high, low, close, volume, amount,
                            adjust_type, factor, created_at, updated_at,
                            open_front, high_front, low_front, close_front,
                            open_back, high_back, low_back, close_back,
                            open_geometric_front, high_geometric_front, low_geometric_front, close_geometric_front,
                            open_geometric_back, high_geometric_back, low_geometric_back, close_geometric_back
                        )
                        SELECT
                            stock_code, symbol_type, CAST(date AS DATE), period,
                            open, high, low, close, volume, amount,
                            adjust_type, factor, created_at, updated_at,
                            open_front, high_front, low_front, close_front,
                            open_back, high_back, low_back, close_back,
                            open_geometric_front, high_geometric_front, low_geometric_front, close_geometric_front,
                            open_geometric_back, high_geometric_back, low_geometric_back, close_geometric_back
                        FROM df_to_save_temp
                    """)

                    con.unregister('df_to_save_temp')
                    print(f"    → 已保存 {len(df_ordered)} 条记录到 {table_name}")

                except Exception as insert_err:
                    print(f"    [ERROR] INSERT失败: {insert_err}")

                    # 降级方案：只插入基础列（不含复权列）
                    print(f"    [DEBUG] 使用降级方案（只保存基础列）...")
                    basic_cols = [
                        'stock_code', 'symbol_type', 'date', 'period',
                        'open', 'high', 'low', 'close', 'volume', 'amount',
                        'adjust_type', 'factor', 'created_at', 'updated_at'
                    ]

                    # 确保这些列都存在
                    existing_basic_cols = [col for col in basic_cols if col in df_ordered.columns]

                    df_basic = df_ordered[existing_basic_cols]
                    con.register('df_to_save_temp2', df_basic)

                    # 先删除
                    con.execute(f"""
                        DELETE FROM {table_name}
                        WHERE stock_code = '{stock_code}'
                            AND date >= '{date_min}'
                            AND date <= '{date_max}'
                    """)

                    # 插入基础列
                    col_list = ', '.join(existing_basic_cols)
                    con.execute(f"INSERT INTO {table_name} ({col_list}) SELECT {col_list} FROM df_to_save_temp2")

                    con.unregister('df_to_save_temp2')
                    print(f"    → 降级方案成功：保存 {len(df_basic)} 条记录（基础列）")

                # 验证保存结果
                verify_sql = f"""
                    SELECT COUNT(*) as count, MIN(date) as min_date, MAX(date) as max_date
                    FROM {table_name}
                    WHERE stock_code = '{stock_code}'
                        AND date >= '{date_min}'
                        AND date <= '{date_max}'
                """
                verify_result = con.execute(verify_sql).fetchdf()
                verify_dict = verify_result.to_dict('records')[0]
                print(f"    [DEBUG] 验证保存结果（{date_min} ~ {date_max}）: count={verify_dict['count']}, max_date={verify_dict['max_date']}")

                # 检查是否真的保存成功了
                if verify_dict['count'] == 0:
                    print(f"    [ERROR] 保存失败！数据未写入数据库")
                elif verify_dict['count'] != len(df_ordered):
                    print(f"    [WARN] 部分数据未保存：期望{len(df_ordered)}条，实际{verify_dict['count']}条")
                else:
                    print(f"    [OK] 数据保存成功！")

        except Exception as e:
            print(f"    [ERROR] 保存失败: {e}")
            import traceback
            traceback.print_exc()

    def _ensure_tables_exist_with_con(self, con):
        """确保所有必需的表都存在（使用指定连接）"""
        try:
            # 创建 stock_daily 表
            con.execute("""
                CREATE TABLE IF NOT EXISTS stock_daily (
                    stock_code VARCHAR NOT NULL,
                    symbol_type VARCHAR NOT NULL,
                    date DATE NOT NULL,
                    period VARCHAR NOT NULL,
                    open DECIMAL(18, 6),
                    high DECIMAL(18, 6),
                    low DECIMAL(18, 6),
                    close DECIMAL(18, 6),
                    volume BIGINT,
                    amount DECIMAL(18, 6),
                    adjust_type VARCHAR DEFAULT 'none',
                    factor DECIMAL(18, 6) DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (stock_code, date, period, adjust_type)
                )
            """)
            print("[DEBUG] 表检查完成")
        except Exception as e:
            print(f"[WARNING] 创建表失败: {e}")
    def _apply_adjustment(
        self,
        data: pd.DataFrame,
        adjust: str
    ) -> pd.DataFrame:
        """应用复权（如果数据中有复权列）"""
        # 检查是否有对应的复权列
        if adjust == 'front':
            if 'close_front' in data.columns:
                # 使用前复权列
                for col in ['open', 'high', 'low', 'close']:
                    if f'{col}_front' in data.columns:
                        data[col] = data[f'{col}_front']
        elif adjust == 'back':
            if 'close_back' in data.columns:
                # 使用后复权列
                for col in ['open', 'high', 'low', 'close']:
                    if f'{col}_back' in data.columns:
                        data[col] = data[f'{col}_back']
        elif adjust == 'geometric_front':
            if 'close_geometric_front' in data.columns:
                # 使用等比前复权列
                for col in ['open', 'high', 'low', 'close']:
                    if f'_{col}_geometric_front' in data.columns:
                        data[col] = data[f'_{col}_geometric_front']
        elif adjust == 'geometric_back':
            if 'close_geometric_back' in data.columns:
                # 使用等比后复权列
                for col in ['open', 'high', 'low', 'close']:
                    if f'_{col}_geometric_back' in data.columns:
                        data[col] = data[f'_{col}_geometric_back']

        return data

    def get_multiple_stocks(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str,
        period: str = '1d',
        adjust: str = 'none'
    ) -> Dict[str, pd.DataFrame]:
        """
        批量获取多个股票的数据

        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期
            adjust: 复权类型

        Returns:
            Dict: {stock_code: DataFrame}
        """
        result = {}

        print(f"\n[批量获取] {len(stock_codes)} 只股票")

        for i, code in enumerate(stock_codes, 1):
            print(f"\n[{i}/{len(stock_codes)}] {code}")
            data = self.get_stock_data(code, start_date, end_date, period, adjust)
            result[code] = data

        return result

    def close(self):
        """关闭数据库连接"""
        if self.con:
            self.con.close()
            self.con = None
            print("[INFO] DuckDB 连接已关闭")


# 便捷函数
def get_stock_data(
    stock_code: str,
    start_date: str,
    end_date: str,
    period: str = '1d',
    adjust: str = 'none',
    duckdb_path: str = r'D:/StockData/stock_data.ddb'
) -> pd.DataFrame:
    """
    便捷函数：获取股票数据（统一入口）

    Args:
        stock_code: 股票代码
        start_date: 开始日期（'YYYY-MM-DD'）
        end_date: 结束日期（'YYYY-MM-DD'）
        period: 数据周期（'1d', '1m', '5m'）
        adjust: 复权类型（'none', 'front', 'back'）
        duckdb_path: DuckDB路径

    Returns:
        DataFrame: OHLCV数据
    """
    interface = UnifiedDataInterface(duckdb_path=duckdb_path)
    interface.connect()

    try:
        data = interface.get_stock_data(stock_code, start_date, end_date, period, adjust)
        return data
    finally:
        interface.close()


# 测试代码
if __name__ == "__main__":
    print("="*80)
    print("统一数据接口测试")
    print("="*80)

    # 测试1：获取单只股票数据
    print("\n【测试1】获取511380.SH数据")
    interface = UnifiedDataInterface()
    interface.connect()

    data = interface.get_stock_data(
        stock_code='511380.SH',
        start_date='2024-01-01',
        end_date='2024-12-31',
        period='1d',
        adjust='none'
    )

    if not data.empty:
        print(f"\n[OK] 数据获取成功")
        print(f"  时间范围: {data.index.min()} ~ {data.index.max()}")
        print(f"  总记录数: {len(data)}")
        print(f"  价格范围: {data['close'].min():.2f} ~ {data['close'].max():.2f}")
        print(f"\n前5条数据:")
        print(data.head())
    else:
        print("\n[ERROR] 数据获取失败")

    interface.close()

    # 测试2：使用便捷函数
    print("\n\n【测试2】使用便捷函数")
    data2 = get_stock_data(
        stock_code='511380.SH',
        start_date='2024-06-01',
        end_date='2024-12-31',
        period='1d',
        adjust='front'
    )

    if not data2.empty:
        print(f"\n[OK] 便捷函数测试成功")
        print(f"  获取 {len(data2)} 条记录")
