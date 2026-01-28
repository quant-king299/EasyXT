# -*- coding: utf-8 -*-
"""
扩展的元数据库管理 - 支持复权因子
"""

import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


class MetadataDB:
    """元数据库管理器（支持复权）"""

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

        # 1. 数据版本表（原有）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_versions (
                symbol TEXT NOT NULL,
                symbol_type TEXT NOT NULL,
                data_type TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                last_update TEXT,
                record_count INTEGER,
                file_size REAL,
                data_quality REAL,
                PRIMARY KEY (symbol, data_type)
            )
        """)

        # 2. 分红数据表（新增）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dividends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                ex_date TEXT NOT NULL,
                dividend_per_share REAL NOT NULL,
                dividend_rate REAL,
                record_date TEXT,
                payout_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, ex_date)
            )
        """)

        # 3. 股票分割数据表（新增）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_splits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                ex_date TEXT NOT NULL,
                split_ratio REAL NOT NULL,
                split_from INTEGER,
                split_to INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, ex_date)
            )
        """)

        # 4. 复权因子缓存表（新增）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS adjustment_factors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                ex_date TEXT NOT NULL,
                adjustment_type TEXT NOT NULL,
                factor REAL NOT NULL,
                cumulative_factor REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, ex_date, adjustment_type)
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dividends_symbol ON dividends(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dividends_date ON dividends(ex_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_splits_symbol ON stock_splits(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_splits_date ON stock_splits(ex_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_factors_symbol ON adjustment_factors(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_factors_date ON adjustment_factors(ex_date)")

        self.conn.commit()

    def save_dividends(self, symbol: str, dividends_df: pd.DataFrame):
        """
        保存分红数据

        Args:
            symbol: 股票代码
            dividends_df: DataFrame with columns:
                - ex_date: 除权日 (YYYY-MM-DD)
                - dividend_per_share: 每股分红
                - record_date: 登记日 (可选)
                - payout_date: 派息日 (可选)
        """
        cursor = self.conn.cursor()

        # 清空旧数据
        cursor.execute("DELETE FROM dividends WHERE symbol=?", (symbol,))

        # 插入新数据
        for _, row in dividends_df.iterrows():
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO dividends
                    (symbol, ex_date, dividend_per_share, record_date, payout_date)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    symbol,
                    row['ex_date'],
                    float(row['dividend_per_share']),
                    row.get('record_date'),
                    row.get('payout_date')
                ))
            except Exception as e:
                print(f"[WARNING] 插入分红数据失败 {symbol} {row['ex_date']}: {e}")

        self.conn.commit()
        print(f"[OK] 保存 {symbol} 分红数据 {len(dividends_df)} 条")

    def get_dividends(self, symbol: str) -> pd.DataFrame:
        """获取分红数据"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT ex_date, dividend_per_share, record_date, payout_date
            FROM dividends
            WHERE symbol=?
            ORDER BY ex_date
        """, (symbol,))

        rows = cursor.fetchall()

        if rows:
            return pd.DataFrame(rows, columns=['ex_date', 'dividend_per_share', 'record_date', 'payout_date'])
        return pd.DataFrame()

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

    def save_stock_split(self, symbol: str, ex_date: str,
                         split_from: int, split_to: int):
        """
        保存股票分割数据

        Args:
            symbol: 股票代码
            ex_date: 除权日
            split_from: 拆分前股数
            split_to: 拆分后股数
        """
        cursor = self.conn.cursor()

        split_ratio = split_to / split_from

        cursor.execute("""
            INSERT OR REPLACE INTO stock_splits
            (symbol, ex_date, split_ratio, split_from, split_to)
            VALUES (?, ?, ?, ?, ?)
        """, (symbol, ex_date, split_ratio, split_from, split_to))

        self.conn.commit()
        print(f"[OK] 保存 {symbol} 分割数据: {split_from}:{split_to} ({ex_date})")

    def get_all_dividends(self) -> pd.DataFrame:
        """获取所有分红数据"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT symbol, ex_date, dividend_per_share
            FROM dividends
            ORDER BY symbol, ex_date
        """)

        rows = cursor.fetchall()

        if rows:
            return pd.DataFrame(rows, columns=['symbol', 'ex_date', 'dividend_per_share'])
        return pd.DataFrame()

    def get_dividend_statistics(self, symbol: str = None) -> Dict:
        """获取分红统计信息"""
        cursor = self.conn.cursor()

        if symbol:
            cursor.execute("""
                SELECT COUNT(*) as count,
                       SUM(dividend_per_share) as total_dividend
                FROM dividends
                WHERE symbol=?
            """, (symbol,))
        else:
            cursor.execute("""
                SELECT COUNT(*) as count,
                       SUM(dividend_per_share) as total_dividend
                FROM dividends
            """)

        row = cursor.fetchone()
        return {
            'dividend_count': row[0] if row[0] else 0,
            'total_dividend': row[1] if row[1] else 0
        }

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

        # 分红数据统计
        cursor.execute("SELECT COUNT(DISTINCT symbol) FROM dividends")
        stats['stocks_with_dividends'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM dividends")
        stats['total_dividend_records'] = cursor.fetchone()[0]

        # 总记录数
        cursor.execute("SELECT SUM(record_count) FROM data_versions")
        stats['total_records'] = cursor.fetchone()[0] or 0

        # 总文件大小
        cursor.execute("SELECT SUM(file_size) FROM data_versions")
        size_mb = cursor.fetchone()[0] or 0
        stats['total_size_mb'] = round(size_mb, 2)

        return stats

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

    def __del__(self):
        """析构函数"""
        self.close()
