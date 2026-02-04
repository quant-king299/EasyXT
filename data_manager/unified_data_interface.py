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

    def connect(self, read_only: bool = True):
        """
        连接DuckDB数据库

        Args:
            read_only: 是否只读模式（避免文件被占用问题）
        """
        if not self.duckdb_available:
            return False

        try:
            import duckdb
            # 只读模式可以避免文件被占用的问题
            if read_only:
                self.con = duckdb.connect(self.duckdb_path, read_only=True)
            else:
                self.con = duckdb.connect(self.duckdb_path)

            print("[INFO] DuckDB 连接成功")
            return True
        except Exception as e:
            print(f"[ERROR] DuckDB 连接失败: {e}")
            self.con = None
            return False

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
        """从DuckDB读取数据"""
        try:
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
        """保存数据到DuckDB"""
        try:
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
                        df_to_save['symbol_type'] = 'stock'  # 科创板
                    else:
                        df_to_save['symbol_type'] = 'stock'
                elif stock_code.endswith('.SZ'):
                    if stock_code.startswith('15') or stock_code.startswith('16'):
                        df_to_save['symbol_type'] = 'etf'
                    elif stock_code.startswith('30'):
                        df_to_save['symbol_type'] = 'stock'  # 创业板
                    else:
                        df_to_save['symbol_type'] = 'stock'
                else:
                    df_to_save['symbol_type'] = 'stock'

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

            # 添加缺失的复权列（如果表有这些列）
            if table_name == 'stock_daily':
                # 添加 adjust_type 和 factor 列
                if 'adjust_type' not in df_to_save.columns:
                    df_to_save['adjust_type'] = 'none'
                if 'factor' not in df_to_save.columns:
                    df_to_save['factor'] = 1.0

                # 添加时间戳列
                import time
                current_time = pd.Timestamp.now()
                if 'created_at' not in df_to_save.columns:
                    df_to_save['created_at'] = current_time
                if 'updated_at' not in df_to_save.columns:
                    df_to_save['updated_at'] = current_time

                # 添加所有复权列（复制原始价格）
                price_cols = ['open', 'high', 'low', 'close']
                adjustment_types = ['_front', '_back', '_geometric_front', '_geometric_back']

                for price_col in price_cols:
                    if price_col in df_to_save.columns:
                        for adj_type in adjustment_types:
                            adj_col = price_col + adj_type
                            if adj_col not in df_to_save.columns:
                                df_to_save[adj_col] = df_to_save[price_col]

            # 获取表的列顺序
            table_columns = self.con.execute(f"DESCRIBE {table_name}").fetchdf()['column_name'].tolist()

            # 按表的列顺序重新排列DataFrame
            df_ordered = pd.DataFrame()
            for col in table_columns:
                if col in df_to_save.columns:
                    df_ordered[col] = df_to_save[col]
                else:
                    df_ordered[col] = None  # 缺失列填充NULL

            # 注册并插入新数据
            self.con.register('df_to_save_temp', df_ordered)
            self.con.execute(f"INSERT INTO {table_name} SELECT * FROM df_to_save_temp")
            self.con.unregister('df_to_save_temp')

            print(f"    → 已保存 {len(df_ordered)} 条记录到 {table_name}")

        except Exception as e:
            print(f"    [ERROR] 保存失败: {e}")
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
