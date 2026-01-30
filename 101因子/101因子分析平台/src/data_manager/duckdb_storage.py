"""
DuckDB存储引擎
高性能的列式存储，特别适合时间序列数据
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
from datetime import datetime
import warnings


class DuckDBStorage:
    """
    DuckDB存储引擎

    优势：
    1. 列式存储 - 时间序列查询快10-100倍
    2. 支持窗口函数 - 技术指标计算更快
    3. 并发读取 - 多线程安全
    4. 数据压缩 - 节省50-80%存储空间
    5. 支持Parquet - 可直接读写Parquet文件
    """

    def __init__(self, db_path: str, compression: str = 'zstd'):
        """
        初始化DuckDB存储引擎

        Args:
            db_path: 数据库文件路径
            compression: 压缩算法 ('none', 'uncompressed', 'snappy', 'zstd', 'lz4')
        """
        self.db_path = Path(db_path)
        self.compression = compression

        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 延迟导入duckdb
        try:
            import duckdb
            self.duckdb = duckdb
        except ImportError:
            raise ImportError(
                "DuckDB未安装，请运行: pip install duckdb\n"
                "推荐版本: >= 0.9.0"
            )

        # 连接数据库
        self.con = self.duckdb.connect(str(self.db_path))

        # 性能优化配置
        self._configure_performance()

        # 初始化表结构
        self._init_tables()

    def _configure_performance(self):
        """配置性能参数"""
        # 多线程配置
        self.con.execute("PRAGMA threads=4")

        # 内存限制（4GB）
        self.con.execute("PRAGMA memory_limit='4GB'")

        # 启用向量化执行
        self.con.execute("SET enable_object_cache=true")

        # 配置排序
        self.con.execute("PRAGMA default_order='DESC'")

    def _init_tables(self):
        """初始化表结构"""
        # 股票日线数据表
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS stock_daily (
                stock_code VARCHAR NOT NULL,
                symbol_type VARCHAR NOT NULL,  -- 'stock', 'index', 'etf'
                date DATE NOT NULL,
                period VARCHAR NOT NULL,        -- '1d', '1h', '5m', '1m'
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume BIGINT,
                amount DOUBLE,
                adjust_type VARCHAR DEFAULT 'none',  -- 'none', 'front', 'back'
                factor DOUBLE DEFAULT 1.0,            -- 复权因子
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (stock_code, date, period, adjust_type)
            )
        """)

        # 分红数据表
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS dividends (
                stock_code VARCHAR NOT NULL,
                ex_date DATE NOT NULL,
                dividend_per_share DOUBLE,
                bonus_ratio DOUBLE,              -- 送股比例（每10股送X股）
                rights_issue_ratio DOUBLE,       -- 配股比例
                rights_issue_price DOUBLE,       -- 配股价格
                record_date DATE,
                pay_date DATE,
                PRIMARY KEY (stock_code, ex_date)
            )
        """)

        # 数据质量统计表
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS data_quality (
                stock_code VARCHAR NOT NULL,
                period VARCHAR NOT NULL,
                total_records INTEGER,
                trading_days INTEGER,
                first_date DATE,
                last_date DATE,
                missing_days INTEGER,
                outliers INTEGER,
                quality_score DOUBLE,
                last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (stock_code, period)
            )
        """)

        # 创建索引
        self._create_indexes()

    def _create_indexes(self):
        """创建索引以优化查询性能"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_stock_code ON stock_daily (stock_code)",
            "CREATE INDEX IF NOT EXISTS idx_date ON stock_daily (date)",
            "CREATE INDEX IF NOT EXISTS idx_period ON stock_daily (period)",
            "CREATE INDEX IF NOT EXISTS idx_adjust_type ON stock_daily (adjust_type)",
            "CREATE INDEX IF NOT EXISTS idx_stock_date ON stock_daily (stock_code, date)",
            "CREATE INDEX IF NOT EXISTS idx_stock_period ON stock_daily (stock_code, period)",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_dividends ON dividends (stock_code, ex_date)",
        ]

        for idx_sql in indexes:
            try:
                self.con.execute(idx_sql)
            except Exception as e:
                warnings.warn(f"创建索引失败: {e}")

    def save_data(self, df: pd.DataFrame, symbol_type: str = 'stock',
                  period: str = '1d', adjust_type: str = 'none') -> Tuple[bool, int]:
        """
        保存数据到DuckDB（只保存不复权数据）

        Args:
            df: DataFrame，必须包含列：stock_code, date, open, high, low, close, volume, amount
            symbol_type: 标的类型 ('stock', 'index', 'etf')
            period: 周期 ('1d', '1h', '5m', '1m')
            adjust_type: 复权类型（会被强制设置为'none'）

        Returns:
            (成功标志, 保存的记录数)
        """
        if df.empty:
            return False, 0

        # 强制只保存不复权数据
        adjust_type = 'none'

        # 准备数据
        df_copy = df.copy()

        # 确保日期列是date类型
        if 'date' in df_copy.columns:
            df_copy['date'] = pd.to_datetime(df_copy['date']).dt.date

        # 添加元数据列
        df_copy['symbol_type'] = symbol_type
        df_copy['period'] = period
        df_copy['adjust_type'] = adjust_type
        df_copy['factor'] = 1.0

        # 去除重复数据
        df_copy = df_copy.drop_duplicates(subset=['stock_code', 'date', 'period', 'adjust_type'])

        # 使用UPSERT（INSERT OR REPLACE）
        try:
            # 注册临时表
            self.con.register('temp_data', df_copy)

            # 执行UPSERT
            result = self.con.execute("""
                INSERT OR REPLACE INTO stock_daily
                SELECT stock_code, symbol_type, date, period,
                       open, high, low, close, volume, amount,
                       adjust_type, factor,
                       CURRENT_TIMESTAMP as created_at,
                       CURRENT_TIMESTAMP as updated_at
                FROM temp_data
            """)

            count = result.rowcount if hasattr(result, 'rowcount') else len(df_copy)

            # 更新数据质量统计
            self._update_quality_stats(df_copy['stock_code'].iloc[0] if 'stock_code' in df_copy.columns else None,
                                       period)

            return True, count

        except Exception as e:
            print(f"[ERROR] 保存数据失败: {e}")
            return False, 0
        finally:
            # 清理临时表
            try:
                self.con.unregister('temp_data')
            except:
                pass

    def load_data(self, stock_code: str, period: str = '1d',
                  adjust_type: str = 'none') -> pd.DataFrame:
        """
        加载单个股票的数据（按需从QMT获取复权）

        Args:
            stock_code: 股票代码
            period: 周期
            adjust_type: 复权类型 ('none', 'front', 'back')

        Returns:
            DataFrame with adjusted prices
        """
        # 如果是不复权，直接从DuckDB读取
        if adjust_type == 'none':
            query = """
                SELECT date, open, high, low, close, volume, amount
                FROM stock_daily
                WHERE stock_code = ?
                  AND period = ?
                  AND adjust_type = 'none'
                ORDER BY date ASC
            """

            try:
                return self.con.execute(query, [stock_code, period]).df()
            except Exception as e:
                warnings.warn(f"加载数据失败 ({stock_code}): {e}")
                return pd.DataFrame()

        # 如果需要复权，从QMT获取
        else:
            return self._load_adjusted_from_qmt(stock_code, period, adjust_type)

    def _load_adjusted_from_qmt(self, stock_code: str, period: str = '1d',
                                adjust_type: str = 'front') -> pd.DataFrame:
        """
        从QMT获取已复权的数据

        Args:
            stock_code: 股票代码
            period: 周期
            adjust_type: 复权类型

        Returns:
            复权后的DataFrame
        """
        try:
            # 导入xtquant
            import xtquant.xtdata as xt_data

            # 映射复权类型到QMT格式
            # QMT dividend_type: 'none'=不复权, 'front'=前复权, 'back'=后复权
            qmt_adjust_map = {
                'none': 'none',
                'front': 'front',
                'back': 'back'
            }

            qmt_adjust = qmt_adjust_map.get(adjust_type, 'none')

            print(f"[DEBUG] 从QMT获取 {stock_code} 数据，复权类型: {adjust_type} -> QMT参数: {qmt_adjust}")

            # 使用 get_market_data_ex 而不是 get_market_data
            # 需要提供日期范围，我们使用最近10年的数据
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365*10)  # 最近10年

            # 格式化日期为YYYYMMDD
            start_time = start_date.strftime('%Y%m%d')
            end_time = end_date.strftime('%Y%m%d')

            # 从QMT获取数据（支持复权）
            data = xt_data.get_market_data_ex(
                stock_list=[stock_code],
                period=period,
                start_time=start_time,
                end_time=end_time,
                dividend_type=qmt_adjust,
                fill_data=True
            )

            # 检查返回数据
            if data is None:
                print(f"[DEBUG] QMT返回None")
                warnings.warn(f"从QMT获取复权数据失败，降级为不复权数据: {stock_code}")
                return self._load_unadjusted(stock_code, period)

            if not isinstance(data, dict):
                print(f"[DEBUG] QMT返回类型错误: {type(data)}")
                warnings.warn(f"从QMT获取复权数据失败，降级为不复权数据: {stock_code}")
                return self._load_unadjusted(stock_code, period)

            if stock_code not in data:
                print(f"[DEBUG] QMT返回数据中不包含 {stock_code}")
                warnings.warn(f"从QMT获取复权数据失败，降级为不复权数据: {stock_code}")
                return self._load_unadjusted(stock_code, period)

            df = data[stock_code]

            if df is None or df.empty:
                print(f"[DEBUG] QMT返回空数据")
                warnings.warn(f"从QMT获取复权数据失败，降级为不复权数据: {stock_code}")
                return self._load_unadjusted(stock_code, period)

            print(f"[DEBUG] QMT返回数据形状: {df.shape}, 列名: {list(df.columns)}")
            print(f"[DEBUG] 索引类型: {type(df.index)}, 索引名称: {df.index.name}")

            # 标准化列名
            df.columns = df.columns.str.lower()

            # DataFrame从QMT返回时已经设置了datetime索引，直接使用
            # 只需要确保索引名为date
            if df.index.name is None:
                df.index.name = 'date'
            elif df.index.name != 'date':
                df = df.rename_axis('date')

            # 选择需要的列
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            optional_cols = ['amount']

            # 确保列存在
            for col in required_cols:
                if col not in df.columns:
                    print(f"[DEBUG] 缺少列: {col}")
                    df[col] = 0

            # 添加amount列（如果不存在）
            if 'amount' not in df.columns:
                df['amount'] = df['close'] * df['volume']

            # 选择需要的列
            cols_to_keep = required_cols + ['amount']
            df = df[cols_to_keep]

            # 确保索引名为date（兼容性）
            if df.index.name != 'date':
                df.index.name = 'date'

            # 按日期升序排列
            df = df.sort_index()

            print(f"[OK] 从QMT成功获取 {len(df)} 条复权数据")
            return df

        except ImportError:
            warnings.warn("xtquant模块未安装，无法从QMT获取复权数据")
            return self._load_unadjusted(stock_code, period)

        except Exception as e:
            print(f"[DEBUG] 从QMT获取数据异常: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            warnings.warn(f"从QMT获取复权数据异常 ({stock_code}): {e}")
            return self._load_unadjusted(stock_code, period)

    def _load_unadjusted(self, stock_code: str, period: str = '1d') -> pd.DataFrame:
        """
        从DuckDB加载不复权数据（降级方案）

        Args:
            stock_code: 股票代码
            period: 周期

        Returns:
            不复权的DataFrame
        """
        query = """
            SELECT date, open, high, low, close, volume, amount
            FROM stock_daily
            WHERE stock_code = ?
              AND period = ?
              AND adjust_type = 'none'
            ORDER BY date ASC
        """

        try:
            return self.con.execute(query, [stock_code, period]).df()
        except Exception as e:
            warnings.warn(f"加载不复权数据失败 ({stock_code}): {e}")
            return pd.DataFrame()

    def load_batch(self, stock_codes: List[str], period: str = '1d',
                   start_date: str = None, end_date: str = None,
                   adjust_type: str = 'none') -> Dict[str, pd.DataFrame]:
        """
        批量加载多个股票的数据（按需从QMT获取复权）

        Args:
            stock_codes: 股票代码列表
            period: 周期
            start_date: 开始日期
            end_date: 结束日期
            adjust_type: 复权类型

        Returns:
            {stock_code: DataFrame} 字典
        """
        if not stock_codes:
            return {}

        # 如果是不复权，批量从DuckDB读取（高效）
        if adjust_type == 'none':
            codes_str = ", ".join([f"'{code}'" for code in stock_codes])

            where_conditions = [
                f"stock_code IN ({codes_str})",
                f"period = '{period}'",
                f"adjust_type = 'none'"
            ]

            if start_date:
                where_conditions.append(f"date >= '{start_date}'")
            if end_date:
                where_conditions.append(f"date <= '{end_date}'")

            query = f"""
                SELECT stock_code, date, open, high, low, close, volume, amount
                FROM stock_daily
                WHERE {' AND '.join(where_conditions)}
                ORDER BY stock_code, date ASC
            """

            try:
                df_all = self.con.execute(query).df()

                # 分组返回
                result = {}
                for code in stock_codes:
                    df_code = df_all[df_all['stock_code'] == code].copy()
                    if not df_code.empty:
                        df_code = df_code.drop(columns=['stock_code'])
                        result[code] = df_code

                return result

            except Exception as e:
                warnings.warn(f"批量加载数据失败: {e}")
                return {}

        # 如果需要复权，逐个从QMT获取（稍慢但准确）
        else:
            result = {}
            for code in stock_codes:
                df = self._load_adjusted_from_qmt(code, period, adjust_type)
                if not df.empty:
                    result[code] = df

            return result

    def calculate_indicators(self, stock_code: str, start_date: str, end_date: str,
                            indicators: List[str] = None) -> pd.DataFrame:
        """
        使用DuckDB的窗口函数计算技术指标

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            indicators: 指标列表 (默认计算常用指标)

        Returns:
            包含技术指标的DataFrame
        """
        if indicators is None:
            indicators = ['ma5', 'ma10', 'ma20', 'ma60', 'rsi']

        query = """
            WITH base_data AS (
                SELECT date, close,
                    LAG(close, 1) OVER (ORDER BY date) as prev_close
                FROM stock_daily
                WHERE stock_code = ?
                  AND date BETWEEN ? AND ?
                  AND period = '1d'
                  AND adjust_type = 'none'
                ORDER BY date
            ),
            ma_data AS (
                SELECT date, close,
                    -- 移动平均线
                    AVG(close) OVER (ORDER BY date ROWS BETWEEN 4 AND 0 PRECEDING) as ma5,
                    AVG(close) OVER (ORDER BY date ROWS BETWEEN 9 AND 0 PRECEDING) as ma10,
                    AVG(close) OVER (ORDER BY date ROWS BETWEEN 19 AND 0 PRECEDING) as ma20,
                    AVG(close) OVER (ORDER BY date ROWS BETWEEN 59 AND 0 PRECEDING) as ma60
                FROM base_data
            )
            SELECT *,
                -- 价格变化
                CASE WHEN prev_close > 0
                     THEN (close - prev_close) / prev_close * 100
                     ELSE 0 END as price_change_pct
            FROM ma_data
            ORDER BY date
        """

        try:
            return self.con.execute(query, [stock_code, start_date, end_date]).df()
        except Exception as e:
            warnings.warn(f"计算技术指标失败: {e}")
            return pd.DataFrame()

    def get_statistics(self) -> Dict:
        """
        获取数据库统计信息

        Returns:
            统计信息字典
        """
        stats = {}

        try:
            # 总记录数
            result = self.con.execute("""
                SELECT
                    COUNT(*) as total_records,
                    COUNT(DISTINCT stock_code) as total_symbols,
                    MIN(date) as first_date,
                    MAX(date) as last_date
                FROM stock_daily
            """).fetchone()

            if result:
                stats['total_records'] = result[0]
                stats['total_symbols'] = result[1]
                stats['first_date'] = str(result[2]) if result[2] else None
                stats['last_date'] = str(result[3]) if result[3] else None

            # 按周期统计
            period_stats = self.con.execute("""
                SELECT period, COUNT(*) as count
                FROM stock_daily
                GROUP BY period
                ORDER BY period
            """).fetchall()

            stats['by_period'] = {period: count for period, count in period_stats}

            # 按复权类型统计
            adjust_stats = self.con.execute("""
                SELECT adjust_type, COUNT(*) as count
                FROM stock_daily
                GROUP BY adjust_type
            """).fetchall()

            stats['by_adjust_type'] = {adj: count for adj, count in adjust_stats}

            # 数据库文件大小
            if self.db_path.exists():
                stats['db_size_mb'] = self.db_path.stat().st_size / (1024 * 1024)

        except Exception as e:
            warnings.warn(f"获取统计信息失败: {e}")

        return stats

    def _update_quality_stats(self, stock_code: str, period: str):
        """更新数据质量统计"""
        try:
            self.con.execute(f"""
                INSERT OR REPLACE INTO data_quality
                SELECT
                    '{stock_code}',
                    '{period}',
                    COUNT(*) as total_records,
                    COUNT(DISTINCT date) as trading_days,
                    MIN(date) as first_date,
                    MAX(date) as last_date,
                    0 as missing_days,  -- TODO: 计算缺失天数
                    0 as outliers,      -- TODO: 检测异常值
                    100.0 as quality_score,
                    CURRENT_TIMESTAMP
                FROM stock_daily
                WHERE stock_code = '{stock_code}' AND period = '{period}'
            """)
        except Exception as e:
            warnings.warn(f"更新质量统计失败: {e}")

    def export_to_parquet(self, output_path: str, table: str = 'stock_daily'):
        """
        导出数据为Parquet格式

        Args:
            output_path: 输出路径
            table: 表名
        """
        try:
            self.con.execute(f"COPY {table} TO '{output_path}' (FORMAT PARQUET, COMPRESSION 'ZSTD')")
            print(f"[OK] 已导出到: {output_path}")
        except Exception as e:
            print(f"[ERROR] 导出失败: {e}")

    def import_from_parquet(self, parquet_path: str, table: str = 'stock_daily'):
        """
        从Parquet文件导入数据

        Args:
            parquet_path: Parquet文件路径
            table: 目标表名
        """
        try:
            self.con.execute(f"""
                INSERT OR REPLACE INTO {table}
                SELECT * FROM '{parquet_path}'
            """)
            print(f"[OK] 已导入: {parquet_path}")
        except Exception as e:
            print(f"[ERROR] 导入失败: {e}")

    def import_from_sqlite(self, sqlite_path: str):
        """
        从SQLite数据库导入数据

        Args:
            sqlite_path: SQLite数据库文件路径
        """
        try:
            # 获取SQLite中的所有表
            tables = self.con.execute(f"""
                SELECT name FROM sqlite_table('{sqlite_path}')
                WHERE type='table'
            """).fetchall()

            for (table_name,) in tables:
                # 导入每个表
                self.con.execute(f"""
                    CREATE OR REPLACE TABLE {table_name} AS
                    SELECT * FROM sqlite_table('{sqlite_path}', '{table_name}')
                """)
                print(f"[OK] 已迁移表: {table_name}")

        except Exception as e:
            print(f"[ERROR] 从SQLite导入失败: {e}")

    def optimize_database(self):
        """优化数据库性能"""
        try:
            # 执行VACUUM（清理和压缩）
            self.con.execute("VACUUM")

            # 重新分析表统计信息
            self.con.execute("ANALYZE")

            print("[OK] 数据库优化完成")
        except Exception as e:
            print(f"[ERROR] 优化失败: {e}")

    def close(self):
        """关闭数据库连接"""
        if self.con:
            self.con.close()

    def __enter__(self):
        """支持with语句"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持with语句"""
        self.close()
