"""
DuckDB元数据库管理
使用DuckDB替代SQLite存储数据版本、索引、质量指标等元信息
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import json


class DuckDBMetadataDB:
    """基于DuckDB的元数据库管理器"""

    def __init__(self, db_path: str):
        """
        初始化元数据库

        Args:
            db_path: DuckDB数据库文件路径
        """
        self.db_path = Path(db_path)
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

        self.con = self.duckdb.connect(str(self.db_path))
        self._create_tables()

    def _create_tables(self):
        """创建数据表"""
        # 数据版本表
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS data_versions (
                symbol VARCHAR NOT NULL,
                symbol_type VARCHAR NOT NULL,  -- stock/bond
                data_type VARCHAR NOT NULL,    -- daily/minute
                start_date DATE,
                end_date DATE,
                last_update TIMESTAMP,
                record_count INTEGER,
                file_size DOUBLE,
                data_quality DOUBLE,
                PRIMARY KEY (symbol, data_type)
            )
        """)

        # 交易日历表
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS trading_calendar (
                trade_date DATE PRIMARY KEY,
                is_trading_day INTEGER NOT NULL,
                market VARCHAR  -- SH/SZ
            )
        """)

        # 因子计算记录表（可选，用于追踪已计算的因子）
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS factor_computations (
                factor_name VARCHAR NOT NULL,
                symbol VARCHAR NOT NULL,
                date DATE NOT NULL,
                computed_at TIMESTAMP,
                file_path VARCHAR,
                ic_value DOUBLE,
                PRIMARY KEY (factor_name, symbol, date)
            )
        """)

        # 数据更新日志
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS update_logs (
                id INTEGER PRIMARY KEY,
                update_time TIMESTAMP,
                operation VARCHAR,  -- download/update/verify
                status VARCHAR,     -- success/failed/partial
                symbols_count INTEGER,
                records_count INTEGER,
                error_msg VARCHAR,
                duration_seconds DOUBLE,
                metadata JSON
            )
        """)

        # 创建索引
        self.con.execute("CREATE INDEX IF NOT EXISTS idx_data_versions_symbol ON data_versions(symbol)")
        self.con.execute("CREATE INDEX IF NOT EXISTS idx_trading_calendar_date ON trading_calendar(trade_date)")

    def update_data_version(self, symbol: str, symbol_type: str = 'stock',
                           data_type: str = 'daily', start_date: str = None,
                           end_date: str = None, record_count: int = 0,
                           file_size: float = 0, data_quality: float = None):
        """
        更新数据版本信息

        Args:
            symbol: 股票代码
            symbol_type: 类型（stock/bond/index）
            data_type: 数据类型（daily/minute）
            start_date: 开始日期
            end_date: 结束日期
            record_count: 记录数量
            file_size: 文件大小（字节）
            data_quality: 数据质量分数
        """
        self.con.execute("""
            INSERT INTO data_versions
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
            ON CONFLICT (symbol, data_type)
            DO UPDATE SET
                start_date = EXCLUDED.start_date,
                end_date = EXCLUDED.end_date,
                last_update = EXCLUDED.last_update,
                record_count = EXCLUDED.record_count,
                file_size = EXCLUDED.file_size,
                data_quality = EXCLUDED.data_quality
        """, [symbol, symbol_type, data_type, start_date, end_date,
              record_count, file_size, data_quality])

    def get_data_version(self, symbol: str, data_type: str = 'daily') -> Optional[Dict]:
        """
        获取数据版本信息

        Args:
            symbol: 股票代码
            data_type: 数据类型

        Returns:
            版本信息字典，不存在返回None
        """
        result = self.con.execute("""
            SELECT * FROM data_versions
            WHERE symbol = ? AND data_type = ?
        """, [symbol, data_type]).fetchone()

        if result:
            return {
                'symbol': result[0],
                'symbol_type': result[1],
                'data_type': result[2],
                'start_date': result[3],
                'end_date': result[4],
                'last_update': result[5],
                'record_count': result[6],
                'file_size': result[7],
                'data_quality': result[8]
            }
        return None

    def get_all_symbols(self, symbol_type: str = None, data_type: str = 'daily') -> List[str]:
        """
        获取所有已下载的股票代码

        Args:
            symbol_type: 筛选类型（可选）
            data_type: 数据类型

        Returns:
            股票代码列表
        """
        if symbol_type:
            result = self.con.execute("""
                SELECT DISTINCT symbol FROM data_versions
                WHERE symbol_type = ? AND data_type = ?
                ORDER BY symbol
            """, [symbol_type, data_type]).fetchall()
        else:
            result = self.con.execute("""
                SELECT DISTINCT symbol FROM data_versions
                WHERE data_type = ?
                ORDER BY symbol
            """, [data_type]).fetchall()

        return [row[0] for row in result]

    def log_update(self, operation: str, status: str, symbols_count: int = 0,
                  records_count: int = 0, error_msg: str = None,
                  duration_seconds: float = None, metadata: Dict = None):
        """
        记录数据更新日志

        Args:
            operation: 操作类型（download/update/verify）
            status: 状态（success/failed/partial）
            symbols_count: 处理的股票数量
            records_count: 处理的记录数量
            error_msg: 错误信息
            duration_seconds: 耗时
            metadata: 额外元数据
        """
        metadata_json = json.dumps(metadata) if metadata else None

        self.con.execute("""
            INSERT INTO update_logs
            VALUES (COALESCE((SELECT MAX(id) FROM update_logs), 0) + 1,
                    CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?)
        """, [operation, status, symbols_count, records_count,
              error_msg, duration_seconds, metadata_json])

    def get_recent_updates(self, days: int = 7) -> pd.DataFrame:
        """
        获取最近的更新记录

        Args:
            days: 查询最近多少天

        Returns:
            更新记录DataFrame
        """
        query = """
            SELECT * FROM update_logs
            WHERE update_time >= CURRENT_DATE - INTERVAL '{days} days'
            ORDER BY update_time DESC
        """.format(days=days)

        return self.con.execute(query).df()

    def add_trading_days(self, dates: List[str], market: str = 'SH'):
        """
        添加交易日

        Args:
            dates: 日期列表（YYYY-MM-DD格式）
            market: 市场（SH/SZ）
        """
        for date in dates:
            self.con.execute("""
                INSERT INTO trading_calendar
                VALUES (?, TRUE, ?)
                ON CONFLICT (trade_date)
                DO NOTHING
            """, [date, market])

    def is_trading_day(self, date: str) -> bool:
        """
        判断是否为交易日

        Args:
            date: 日期（YYYY-MM-DD格式）

        Returns:
            是否为交易日
        """
        result = self.con.execute("""
            SELECT is_trading_day FROM trading_calendar
            WHERE trade_date = ?
        """, [date]).fetchone()

        return bool(result and result[0])

    def get_trading_days(self, start_date: str, end_date: str) -> List[str]:
        """
        获取日期范围内的交易日

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            交易日列表
        """
        result = self.con.execute("""
            SELECT trade_date FROM trading_calendar
            WHERE trade_date BETWEEN ? AND ?
            AND is_trading_day = TRUE
            ORDER BY trade_date
        """, [start_date, end_date]).fetchall()

        return [row[0] for row in result]

    def get_latest_trading_day(self) -> Optional[str]:
        """
        获取最新的交易日

        Returns:
            最新交易日，不存在返回None
        """
        result = self.con.execute("""
            SELECT trade_date FROM trading_calendar
            WHERE is_trading_day = TRUE
            ORDER BY trade_date DESC
            LIMIT 1
        """).fetchone()

        return result[0] if result else None

    def close(self):
        """关闭数据库连接"""
        if self.con:
            self.con.close()

    def __del__(self):
        """析构函数，确保连接关闭"""
        self.close()
