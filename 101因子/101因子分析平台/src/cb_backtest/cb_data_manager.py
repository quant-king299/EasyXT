# -*- coding: utf-8 -*-
"""
可转债数据管理器
从 DuckDB 加载可转债行情数据，提供给回测引擎使用
"""

import os
import duckdb
import pandas as pd


class CBDataManager:
    """可转债数据管理器"""

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = self._auto_detect_db_path()
        self.db_path = db_path

    @staticmethod
    def _auto_detect_db_path():
        common = [
            os.environ.get('DUCKDB_PATH', ''),
            'D:/StockData/stock_data.ddb',
            'C:/StockData/stock_data.ddb',
            'E:/StockData/stock_data.ddb',
        ]
        for p in common:
            if p and os.path.exists(p):
                return p
        return 'D:/StockData/stock_data.ddb'

    def _get_conn(self):
        return duckdb.connect(self.db_path, read_only=True)

    def get_cb_basic(self) -> pd.DataFrame:
        """获取可转债基本信息"""
        conn = self._get_conn()
        try:
            df = conn.execute("""
                SELECT ts_code, bond_short_name, stk_code, stk_short_name,
                       conv_price, list_date, delist_date, maturity_date,
                       coupon_rate, maturity, remain_size
                FROM cb_basic
                ORDER BY ts_code
            """).fetchdf()
            return df
        finally:
            conn.close()

    def get_cb_daily(self, start_date=None, end_date=None,
                     ts_codes=None) -> pd.DataFrame:
        """
        获取可转债日行情

        Returns:
            DataFrame: ts_code, trade_date, open, high, low, close,
                       vol, amount, pct_chg, cb_value, cb_over_rate,
                       bond_value, bond_over_rate
        """
        conn = self._get_conn()
        try:
            conditions = []
            if start_date:
                conditions.append(f"trade_date >= '{start_date}'")
            if end_date:
                conditions.append(f"trade_date <= '{end_date}'")
            if ts_codes:
                codes_str = ','.join(f"'{c}'" for c in ts_codes)
                conditions.append(f"ts_code IN ({codes_str})")

            where = f" WHERE {' AND '.join(conditions)}" if conditions else ""

            df = conn.execute(f"""
                SELECT ts_code, trade_date, open, high, low, close,
                       vol, amount, pct_chg,
                       cb_value, cb_over_rate, bond_value, bond_over_rate
                FROM cb_daily
                {where}
                ORDER BY ts_code, trade_date
            """).fetchdf()
            return df
        finally:
            conn.close()

    def get_available_date_range(self) -> tuple:
        """获取数据的日期范围"""
        conn = self._get_conn()
        try:
            row = conn.execute("""
                SELECT MIN(trade_date), MAX(trade_date) FROM cb_daily
            """).fetchone()
            if row and row[0]:
                return str(row[0])[:10], str(row[1])[:10]
            return None, None
        finally:
            conn.close()
