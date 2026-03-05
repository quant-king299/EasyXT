#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据接口 - 修复版
实现DuckDB和QMT数据源的统一管理
修复首次使用时建表缺失的问题

参考文档：docs/DUCKDB_COMPARISON_ANALYSIS.md
"""

import pandas as pd
import numpy as np
from typing import Optional, Union, List, Dict
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class UnifiedDataInterface:
    """
    统一数据接口 - 修复版

    修复内容：
    1. 首次使用时自动创建表
    2. 表不存在时不会报错
    3. 更健壮的错误处理
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
        self._tables_initialized = False

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
        连接DuckDB数据库

        Args:
            read_only: 是否只读模式（首次建表需要写权限）

        修复：首次使用时允许写模式以创建表
        """
        if not self.duckdb_available:
            return False

        try:
            import duckdb
            from pathlib import Path

            # 确保目录存在
            Path(self.duckdb_path).parent.mkdir(parents=True, exist_ok=True)

            # 首次使用时用读写模式
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
        """确保所有必需的表都存在"""
        if not self.con or self._tables_initialized:
            return

        try:
            import duckdb

            # 创建 stock_daily 表（日线）
            self.con.execute("""
                CREATE TABLE IF NOT EXISTS stock_daily (
                    stock_code VARCHAR NOT NULL,
                    symbol_type VARCHAR NOT NULL,
                    date DATE NOT NULL,
                    period VARCHAR NOT NULL,
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume BIGINT,
                    amount DOUBLE,
                    adjust_type VARCHAR DEFAULT 'none',
                    factor DOUBLE DEFAULT 1.0,
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
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume BIGINT,
                    amount DOUBLE,
                    adjust_type VARCHAR DEFAULT 'none',
                    factor DOUBLE DEFAULT 1.0,
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
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume BIGINT,
                    amount DOUBLE,
                    adjust_type VARCHAR DEFAULT 'none',
                    factor DOUBLE DEFAULT 1.0,
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
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume BIGINT,
                    amount DOUBLE,
                    adjust_type VARCHAR DEFAULT 'none',
                    factor DOUBLE DEFAULT 1.0,
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
        获取股票数据（统一入口）- 修复版

        修复：
        1. 首次使用时自动创建表
        2. 表不存在时不会报错
        3. 更健壮的错误处理

        Args:
            stock_code: 股票代码（如 '511380.SH'）
            start_date: 开始日期（'YYYY-MM-DD'）
            end_date: 结束日期（'YYYY-MM-DD'）
            period: 数据周期（'1d'=日线, '1m'=分钟, '5m'=5分钟, 'tick'=tick）
            adjust: 复权类型（'none'=不复权, 'front'=前复权, 'back'=后复权）
            auto_save: 是否自动保存到DuckDB

        Returns:
            DataFrame: 包含 OHLCV 数据
        """
        print(f"\n[获取数据] {stock_code} | {start_date} ~ {end_date} | {period} | {adjust}")

        # 确保表存在
        self._ensure_tables_exist()

        # Step 1: 尝试从DuckDB读取
        data = None
        if self.duckdb_available and self.con:
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

            # 合并数据（DuckDB有的就用，没有的补充）
            if data is not None and not data.empty:
                print(f"  → 合并 DuckDB 和 QMT 数据...")
                merged_data = self._merge_data(data, qmt_data)
                data = merged_data
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
        """从DuckDB读取数据 - 修复版"""
        try:
            # 确定表名
            table_map = {
                '1d': 'stock_daily',
                '1m': 'stock_1m',
                '5m': 'stock_5m',
                'tick': 'stock_tick'
            }
            table_name = table_map.get(period, 'stock_daily')

            # 检查表是否存在
            table_exists = self.con.execute(f"""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = '{table_name}'
            """).fetchone()[0] > 0

            if not table_exists:
                print(f"  [INFO] 表 {table_name} 不存在，返回空数据")
                return None

            # 确定列名（根据复权类型）
            if adjust == 'none':
                price_cols = ['open', 'high', 'low', 'close']
                date_col = 'date'
            elif adjust == 'front':
                price_cols = ['open_front', 'high_front', 'low_front', 'close_front']
                date_col = 'date'
            elif adjust == 'back':
                price_cols = ['open_back', 'high_back', 'low_back', 'close_back']
                date_col = 'date'
            else:
                # 其他复权类型暂不支持，使用不复权
                price_cols = ['open', 'high', 'low', 'close']
                date_col = 'date'

            # 构建SQL
            sql = f"""
                SELECT
                    stock_code,
                    {date_col} as datetime,
                    {price_cols[0]} as open,
                    {price_cols[1]} as high,
                    {price_cols[2]} as low,
                    {price_cols[3]} as close,
                    volume,
                    amount
                FROM {table_name}
                WHERE stock_code = '{stock_code}'
                    AND {date_col} >= '{start_date}'
                    AND {date_col} <= '{end_date}'
                    AND period = '{period}'
                    AND adjust_type = 'none'
                ORDER BY {date_col}
            """

            # 执行查询
            df = self.con.execute(sql).df()

            if not df.empty:
                # 转换datetime列
                df['datetime'] = pd.to_datetime(df['datetime'])
                df.set_index('datetime', inplace=True)

            return df

        except Exception as e:
            # 表不存在或其他错误
            print(f"  [DEBUG] DuckDB 读取异常: {e}")
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

            # 转换日期格式
            start_str = start_date.replace('-', '')
            end_str = end_date.replace('-', '')

            # QMT的period参数：1d, 1m, 5m, tick 直接使用
            qmt_period = period

            # 下载历史数据
            xtdata.download_history_data(
                stock_code=stock_code,
                period=qmt_period,
                start_time=start_str,
                end_time=end_str
            )

            # 获取数据
            data = xtdata.get_market_data(
                stock_list=[stock_code],
                period=qmt_period,
                start_time=start_str,
                end_time=end_str,
                count=0
            )

            if not data or 'time' not in data:
                return None

            # 转换为DataFrame
            time_df = data['time']
            timestamps = time_df.columns.tolist()

            records = []
            for idx, ts in enumerate(timestamps):
                try:
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
                except:
                    continue

            if not records:
                return None

            df = pd.DataFrame(records)
            df.set_index('datetime', inplace=True)
            df.sort_index(inplace=True)

            # 删除重复索引
            df = df[~df.index.duplicated(keep='first')]

            return df

        except Exception as e:
            print(f"  [ERROR] QMT 数据获取失败: {e}")
            return None

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
        # 使用QMT数据作为基础
        merged = qmt_data.copy()

        # 找出DuckDB中有但QMT中没有的日期（用DuckDB补充）
        duckdb_dates = set(duckdb_data.index)
        qmt_dates = set(qmt_data.index)

        only_in_duckdb = duckdb_dates - qmt_dates

        if only_in_duckdb:
            additional = duckdb_data[list(only_in_duckdb)]
            merged = pd.concat([merged, additional]).sort_index()

        # 删除重复索引
        merged = merged[~merged.index.duplicated(keep='first')]

        return merged

    def _save_to_duckdb(
        self,
        data: pd.DataFrame,
        stock_code: str,
        period: str
    ):
        """保存数据到DuckDB - 修复版"""
        try:
            # 确保表存在
            self._ensure_tables_exist()

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

            # 确保有必需列
            if 'datetime' in df_to_save.columns:
                df_to_save.rename(columns={'datetime': 'date'}, inplace=True)
            elif 'date' not in df_to_save.columns:
                df_to_save['date'] = df_to_save.index

            # 确保有stock_code列
            if 'stock_code' not in df_to_save.columns:
                df_to_save['stock_code'] = stock_code

            # 确保有period列
            if 'period' not in df_to_save.columns:
                df_to_save['period'] = period

            # 确保date是date类型
            df_to_save['date'] = pd.to_datetime(df_to_save['date']).dt.date

            # 确保symbol_type列
            if 'symbol_type' not in df_to_save.columns:
                df_to_save['symbol_type'] = 'stock'

            # 确保adjust_type和factor列
            if 'adjust_type' not in df_to_save.columns:
                df_to_save['adjust_type'] = 'none'
            if 'factor' not in df_to_save.columns:
                df_to_save['factor'] = 1.0

            # 添加时间戳
            import time
            current_time = pd.Timestamp.now()
            if 'created_at' not in df_to_save.columns:
                df_to_save['created_at'] = current_time
            if 'updated_at' not in df_to_save.columns:
                df_to_save['updated_at'] = current_time

            # 删除已存在的重复数据
            date_min = str(df_to_save['date'].min())
            date_max = str(df_to_save['date'].max())

            delete_sql = f"""
                DELETE FROM {table_name}
                WHERE stock_code = '{stock_code}'
                    AND date >= '{date_min}'
                    AND date <= '{date_max}'
            """
            self.con.execute(delete_sql)

            # 只保存需要的列
            required_cols = ['stock_code', 'symbol_type', 'date', 'period',
                          'open', 'high', 'low', 'close', 'volume', 'amount',
                          'adjust_type', 'factor', 'created_at', 'updated_at']

            df_final = df_to_save[required_cols].copy()

            # 注册并插入
            self.con.register('df_to_save_temp', df_final)
            self.con.execute(f"INSERT INTO {table_name} SELECT * FROM df_to_save_temp")
            self.con.unregister('df_to_save_temp')

            print(f"    → 已保存 {len(df_final)} 条记录到 {table_name}")

        except Exception as e:
            print(f"    [ERROR] 保存失败: {e}")
            import traceback
            traceback.print_exc()

    def _apply_adjustment(
        self,
        data: pd.DataFrame,
        adjust: str
    ) -> pd.DataFrame:
        """应用复权（目前简单实现，暂不支持五维复权）"""
        # 目前只返回原始数据
        # TODO: 实现前复权、后复权等
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
    interface.connect(read_only=False)  # 首次使用需要写权限

    try:
        data = interface.get_stock_data(stock_code, start_date, end_date, period, adjust)
        return data
    finally:
        interface.close()


# 测试代码
if __name__ == "__main__":
    print("=" * 80)
    print("统一数据接口测试 - 修复版")
    print("=" * 80)

    # 测试：获取单只股票数据
    print("\n【测试】获取511380.SH数据")
    interface = UnifiedDataInterface()
    interface.connect(read_only=False)  # 首次使用需要写权限

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
