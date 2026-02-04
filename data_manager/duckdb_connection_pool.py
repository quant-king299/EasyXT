#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DuckDB 连接管理器
解决数据库文件锁定问题，允许多个进程同时访问
"""

import duckdb
import threading
import time
from contextlib import contextmanager
from typing import Optional
from pathlib import Path


class DuckDBConnectionManager:
    """
    DuckDB 连接管理器

    功能：
    1. 自动使用只读模式（GUI）
    2. 连接池管理
    3. 自动重试机制
    4. 上下文管理器支持
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, duckdb_path: str = r'D:/StockData/stock_data.ddb'):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, duckdb_path: str = r'D:/StockData/stock_data.ddb'):
        if self._initialized:
            return

        self.duckdb_path = duckdb_path
        self._write_lock = threading.Lock()
        self._connection_count = 0
        self._initialized = True

    @contextmanager
    def get_read_connection(self):
        """
        获取只读连接（用于GUI查询）

        使用方式：
            with manager.get_read_connection() as con:
                df = con.execute("SELECT * FROM stock_daily").df()
        """
        con = None
        max_retries = 5
        retry_delay = 0.5

        for attempt in range(max_retries):
            try:
                con = duckdb.connect(self.duckdb_path, read_only=True)
                self._connection_count += 1
                yield con
                break
            except Exception as e:
                if "lock" in str(e).lower() or "already open" in str(e).lower():
                    if attempt < max_retries - 1:
                        print(f"[WARNING] 数据库被占用，重试 {attempt + 1}/{max_retries}...")
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                raise
            finally:
                if con:
                    try:
                        con.close()
                        self._connection_count -= 1
                    except:
                        pass

    @contextmanager
    def get_write_connection(self):
        """
        获取写连接（用于数据更新）

        使用方式：
            with manager.get_write_connection() as con:
                con.execute("UPDATE stock_daily SET ...")
        """
        con = None
        max_retries = 10
        retry_delay = 1.0

        with self._write_lock:
            for attempt in range(max_retries):
                try:
                    con = duckdb.connect(self.duckdb_path, read_only=False)
                    self._connection_count += 1
                    yield con
                    break
                except Exception as e:
                    if "lock" in str(e).lower() or "already open" in str(e).lower():
                        if attempt < max_retries - 1:
                            print(f"[WARNING] 数据库被占用，重试 {attempt + 1}/{max_retries}...")
                            time.sleep(retry_delay * (attempt + 1))
                            continue
                    raise
                finally:
                    if con:
                        try:
                            con.close()
                            self._connection_count -= 1
                        except:
                            pass

    def execute_read_query(self, query: str, params: Optional[tuple] = None):
        """
        执行只读查询（快捷方法）

        Args:
            query: SQL查询语句
            params: 查询参数（可选）

        Returns:
            DataFrame: 查询结果
        """
        with self.get_read_connection() as con:
            if params:
                df = con.execute(query, params).df()
            else:
                df = con.execute(query).df()
            return df

    def execute_write_query(self, query: str, params: Optional[tuple] = None):
        """
        执行写操作（快捷方法）

        Args:
            query: SQL更新/插入/删除语句
            params: 查询参数（可选）

        Returns:
            执行结果
        """
        with self.get_write_connection() as con:
            if params:
                result = con.execute(query, params)
            else:
                result = con.execute(query)
            return result

    @property
    def connection_count(self):
        """当前连接数"""
        return self._connection_count


# 全局单例
_db_manager = None


def get_db_manager(duckdb_path: str = r'D:/StockData/stock_data.ddb') -> DuckDBConnectionManager:
    """获取数据库管理器单例"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DuckDBConnectionManager(duckdb_path)
    return _db_manager


# 便捷函数
def query_dataframe(query: str, params: Optional[tuple] = None) -> 'pd.DataFrame':
    """快捷查询函数（只读）"""
    import pandas as pd
    manager = get_db_manager()
    return manager.execute_read_query(query, params)


def execute_update(query: str, params: Optional[tuple] = None):
    """快捷更新函数（写操作）"""
    manager = get_db_manager()
    return manager.execute_write_query(query, params)


if __name__ == "__main__":
    """测试代码"""
    print("=" * 80)
    print("DuckDB 连接管理器测试")
    print("=" * 80)

    manager = get_db_manager()

    # 测试1：只读查询
    print("\n[测试1] 只读查询...")
    try:
        df = manager.execute_read_query("""
            SELECT
                COUNT(DISTINCT stock_code) as stock_count,
                COUNT(*) as total_records
            FROM stock_daily
        """)
        print(f"[OK] 股票数: {df['stock_count'].iloc[0]:,}, 记录数: {df['total_records'].iloc[0]:,}")
    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试2：上下文管理器
    print("\n[测试2] 上下文管理器...")
    try:
        with manager.get_read_connection() as con:
            df = con.execute("SELECT * FROM stock_daily LIMIT 3").df()
            print(f"[OK] 查询到 {len(df)} 条记录")
    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试3：快捷函数
    print("\n[测试3] 快捷函数...")
    try:
        df = query_dataframe("SELECT * FROM stock_daily WHERE stock_code = '511380.SH' LIMIT 3")
        print(f"[OK] 查询到 {len(df)} 条记录")
    except Exception as e:
        print(f"[ERROR] {e}")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
