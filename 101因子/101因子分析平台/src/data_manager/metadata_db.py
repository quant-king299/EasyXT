"""
元数据库管理
使用SQLite存储数据版本、索引、质量指标等元信息
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import json


class MetadataDB:
    """元数据库管理器"""

    def __init__(self, db_path: str):
        """
        初始化元数据库

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        """创建数据表"""
        cursor = self.conn.cursor()

        # 数据版本表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_versions (
                symbol TEXT NOT NULL,
                symbol_type TEXT NOT NULL,  -- stock/bond
                data_type TEXT NOT NULL,    -- daily/minute
                start_date TEXT,
                end_date TEXT,
                last_update TEXT,
                record_count INTEGER,
                file_size REAL,
                data_quality REAL,
                PRIMARY KEY (symbol, data_type)
            )
        """)

        # 交易日历表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trading_calendar (
                trade_date TEXT PRIMARY KEY,
                is_trading_day INTEGER NOT NULL,
                market TEXT  -- SH/SZ
            )
        """)

        # 因子计算记录表（可选，用于追踪已计算的因子）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS factor_computations (
                factor_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                computed_at TEXT,
                file_path TEXT,
                ic_value REAL,
                PRIMARY KEY (factor_name, symbol, date)
            )
        """)

        # 数据更新日志
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS update_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                update_time TEXT,
                operation TEXT,  -- download/update/verify
                status TEXT,     -- success/failed/partial
                symbols_count INTEGER,
                records_count INTEGER,
                error_message TEXT,
                duration_seconds REAL
            )
        """)

        # 市场信息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_info (
                trade_date TEXT PRIMARY KEY,
                total_stocks INTEGER,
                total_bonds INTEGER,
                suspension_count INTEGER  -- 停牌数量
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_versions_symbol ON data_versions(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_versions_type ON data_versions(symbol_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_versions_dates ON data_versions(start_date, end_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calendar_date ON trading_calendar(trade_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_factor_name ON factor_computations(factor_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_update_time ON update_logs(update_time)")

        self.conn.commit()

    def update_data_version(self, symbol: str, symbol_type: str,
                           start_date: str, end_date: str,
                           record_count: int, file_size: float,
                           data_quality: float = 1.0):
        """更新数据版本信息"""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO data_versions
            (symbol, symbol_type, data_type, start_date, end_date,
             last_update, record_count, file_size, data_quality)
            VALUES (?, ?, 'daily', ?, ?, ?, ?, ?, ?)
        """, (symbol, symbol_type, start_date, end_date,
              datetime.now().isoformat(), record_count, file_size, data_quality))

        self.conn.commit()

    def get_data_version(self, symbol: str) -> Optional[Dict]:
        """获取数据版本信息"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM data_versions WHERE symbol = ?
        """, (symbol,))

        row = cursor.fetchone()
        if row:
            columns = ['symbol', 'symbol_type', 'data_type', 'start_date',
                      'end_date', 'last_update', 'record_count', 'file_size', 'data_quality']
            return dict(zip(columns, row))
        return None

    def get_symbols_needing_update(self, days_threshold: int = 1) -> List[Tuple[str, str]]:
        """
        获取需要更新的标的列表

        Args:
            days_threshold: 距离上次更新的天数阈值

        Returns:
            [(symbol, symbol_type), ...]
        """
        cursor = self.conn.cursor()

        threshold_date = (datetime.now() - timedelta(days=days_threshold)).isoformat()

        cursor.execute("""
            SELECT symbol, symbol_type FROM data_versions
            WHERE last_update < ? OR last_update IS NULL
        """, (threshold_date,))

        return cursor.fetchall()

    def batch_update_versions(self, records: List[Dict]):
        """批量更新数据版本"""
        cursor = self.conn.cursor()

        for record in records:
            cursor.execute("""
                INSERT OR REPLACE INTO data_versions
                (symbol, symbol_type, data_type, start_date, end_date,
                 last_update, record_count, file_size, data_quality)
                VALUES (?, ?, 'daily', ?, ?, ?, ?, ?, ?)
            """, (
                record['symbol'], record['symbol_type'],
                record['start_date'], record['end_date'],
                datetime.now().isoformat(),
                record['record_count'], record.get('file_size', 0),
                record.get('data_quality', 1.0)
            ))

        self.conn.commit()

    def add_trading_days(self, dates: List[str], market: str = 'SH'):
        """添加交易日历"""
        cursor = self.conn.cursor()

        for date in dates:
            cursor.execute("""
                INSERT OR IGNORE INTO trading_calendar (trade_date, is_trading_day, market)
                VALUES (?, 1, ?)
            """, (date, market))

        self.conn.commit()

    def is_trading_day(self, date: str) -> bool:
        """判断是否为交易日"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT is_trading_day FROM trading_calendar WHERE trade_date = ?
        """, (date,))

        row = cursor.fetchone()
        return row is not None and row[0] == 1

    def get_trading_days(self, start_date: str, end_date: str) -> List[str]:
        """获取指定范围的交易日列表"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT trade_date FROM trading_calendar
            WHERE trade_date BETWEEN ? AND ?
            AND is_trading_day = 1
            ORDER BY trade_date
        """, (start_date, end_date))

        return [row[0] for row in cursor.fetchall()]

    def log_update(self, operation: str, status: str,
                   symbols_count: int, records_count: int,
                   error_message: str = None, duration: float = 0):
        """记录更新日志"""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO update_logs
            (update_time, operation, status, symbols_count,
             records_count, error_message, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), operation, status,
              symbols_count, records_count, error_message, duration))

        self.conn.commit()

    def get_recent_logs(self, limit: int = 10) -> List[Dict]:
        """获取最近的更新日志"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM update_logs
            ORDER BY update_time DESC
            LIMIT ?
        """, (limit,))

        columns = ['id', 'update_time', 'operation', 'status',
                  'symbols_count', 'records_count', 'error_message', 'duration']

        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def update_market_info(self, trade_date: str,
                          total_stocks: int, total_bonds: int,
                          suspension_count: int = 0):
        """更新市场信息"""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO market_info
            (trade_date, total_stocks, total_bonds, suspension_count)
            VALUES (?, ?, ?, ?)
        """, (trade_date, total_stocks, total_bonds, suspension_count))

        self.conn.commit()

    def get_statistics(self) -> Dict:
        """获取数据库统计信息"""
        cursor = self.conn.cursor()

        stats = {}

        # 数据版本统计
        cursor.execute("SELECT COUNT(*) FROM data_versions")
        stats['total_symbols'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM data_versions WHERE symbol_type = 'stock'")
        stats['total_stocks'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM data_versions WHERE symbol_type = 'bond'")
        stats['total_bonds'] = cursor.fetchone()[0]

        # 交易日统计
        cursor.execute("SELECT COUNT(*) FROM trading_calendar WHERE is_trading_day = 1")
        stats['total_trading_days'] = cursor.fetchone()[0]

        # 最新数据日期
        cursor.execute("SELECT MAX(end_date) FROM data_versions")
        stats['latest_data_date'] = cursor.fetchone()[0]

        # 总记录数
        cursor.execute("SELECT SUM(record_count) FROM data_versions")
        stats['total_records'] = cursor.fetchone()[0] or 0

        # 总文件大小（file_size字段已存储为MB，直接求和即可）
        cursor.execute("SELECT SUM(file_size) FROM data_versions")
        size_mb = cursor.fetchone()[0] or 0
        stats['total_size_mb'] = round(size_mb, 2)

        # 更新日志统计
        cursor.execute("SELECT COUNT(*) FROM update_logs WHERE status = 'success'")
        stats['successful_updates'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM update_logs WHERE status = 'failed'")
        stats['failed_updates'] = cursor.fetchone()[0]

        return stats

    def get_all_symbols(self, symbol_type: str = None) -> List[str]:
        """获取所有标的列表"""
        cursor = self.conn.cursor()

        if symbol_type:
            cursor.execute("""
                SELECT symbol FROM data_versions
                WHERE symbol_type = ?
                ORDER BY symbol
            """, (symbol_type,))
        else:
            cursor.execute("""
                SELECT symbol FROM data_versions
                ORDER BY symbol
            """)

        return [row[0] for row in cursor.fetchall()]

    def cleanup_old_logs(self, days: int = 30):
        """清理旧的日志记录"""
        cursor = self.conn.cursor()

        threshold_date = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute("""
            DELETE FROM update_logs WHERE update_time < ?
        """, (threshold_date,))

        deleted = cursor.rowcount
        self.conn.commit()

        return deleted

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

    def __del__(self):
        """析构函数"""
        self.close()


if __name__ == '__main__':
    # 测试代码
    db = MetadataDB("../data/metadata.db")

    # 测试更新版本
    db.update_data_version(
        symbol='000001.SZ',
        symbol_type='stock',
        start_date='2020-01-01',
        end_date='2024-01-01',
        record_count=1000,
        file_size=102400
    )

    # 测试查询
    print("数据版本:", db.get_data_version('000001.SZ'))

    # 测试统计
    print("数据库统计:", db.get_statistics())

    # 测试日志
    db.log_update('download', 'success', 100, 10000, duration=5.2)
    print("最近日志:", db.get_recent_logs(5))
