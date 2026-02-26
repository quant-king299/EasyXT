#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tushare数据下载模块
支持从Tushare下载各类数据并保存到DuckDB
"""

import time
import pandas as pd
import tushare as ts
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import duckdb

from .tushare_config import TushareConfig


class TushareDownloader:
    """Tushare数据下载器"""

    def __init__(self, token: Optional[str] = None, db_path: Optional[str] = None):
        """
        初始化下载器

        Args:
            token: Tushare token，默认从配置读取
            db_path: DuckDB路径，默认从配置读取
        """
        self.config = TushareConfig()

        # 设置token
        self.token = token or self.config.token
        ts.set_token(self.token)

        # 初始化pro接口
        self.pro = ts.pro_api()

        # 设置数据库路径
        self.db_path = db_path or self.config.db_path

        # 统计信息
        self.stats = {
            'total_requests': 0,
            'total_records': 0,
            'start_time': None,
            'errors': []
        }

    def _log(self, message: str, level: str = "INFO"):
        """输出日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] [{level}] {message}")

    def _api_call(self, api_name: str, **kwargs) -> Optional[pd.DataFrame]:
        """
        调用Tushare API（带重试和限流）

        Args:
            api_name: API方法名
            **kwargs: API参数

        Returns:
            DataFrame or None
        """
        # 内部使用的合理默认值
        max_retries = 3
        retry_delay = 0.12  # 保守值，适配2000积分用户（每分钟500次）

        for attempt in range(max_retries):
            try:
                self.stats['total_requests'] += 1

                # 调用API
                api_method = getattr(self.pro, api_name)
                df = api_method(**kwargs)

                # 限流 - 每次调用后等待
                time.sleep(retry_delay)

                if df is not None and not df.empty:
                    self.stats['total_records'] += len(df)

                return df

            except Exception as e:
                if attempt < max_retries - 1:
                    self._log(f"API调用失败，重试 {attempt + 1}/{max_retries}: {e}", "WARN")
                    time.sleep(retry_delay * 2)
                else:
                    self._log(f"API调用失败: {e}", "ERROR")
                    self.stats['errors'].append(f"{api_name}: {str(e)}")
                    return None

    def _get_db_connection(self):
        """获取数据库连接"""
        return duckdb.connect(self.db_path)

    # ==================== 财务数据 ====================

    def download_income(self, ts_code: str = None, period: str = None,
                       start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        下载利润表数据

        Args:
            ts_code: 股票代码，多个用逗号分隔
            period: 报告期，如 '20231231'
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame
        """
        self._log(f"下载利润表数据: {ts_code or '全部'}")

        df_list = []
        if ts_code and ',' in ts_code:
            codes = ts_code.split(',')
        else:
            codes = [ts_code] if ts_code else [None]

        for code in codes:
            df = self._api_call('income', ts_code=code, period=period,
                               start_date=start_date, end_date=end_date)
            if df is not None and not df.empty:
                df_list.append(df)

        if df_list:
            return pd.concat(df_list, ignore_index=True)
        return pd.DataFrame()

    def download_balancesheet(self, ts_code: str = None, period: str = None,
                              start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """下载资产负债表数据"""
        self._log(f"下载资产负债表数据: {ts_code or '全部'}")

        df_list = []
        if ts_code and ',' in ts_code:
            codes = ts_code.split(',')
        else:
            codes = [ts_code] if ts_code else [None]

        for code in codes:
            df = self._api_call('balancesheet', ts_code=code, period=period,
                               start_date=start_date, end_date=end_date)
            if df is not None and not df.empty:
                df_list.append(df)

        if df_list:
            return pd.concat(df_list, ignore_index=True)
        return pd.DataFrame()

    def download_cashflow(self, ts_code: str = None, period: str = None,
                         start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """下载现金流量表数据"""
        self._log(f"下载现金流量表数据: {ts_code or '全部'}")

        df_list = []
        if ts_code and ',' in ts_code:
            codes = ts_code.split(',')
        else:
            codes = [ts_code] if ts_code else [None]

        for code in codes:
            df = self._api_call('cashflow', ts_code=code, period=period,
                               start_date=start_date, end_date=end_date)
            if df is not None and not df.empty:
                df_list.append(df)

        if df_list:
            return pd.concat(df_list, ignore_index=True)
        return pd.DataFrame()

    def download_fina_indicator(self, ts_code: str = None, period: str = None,
                                start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """下载财务指标数据"""
        self._log(f"下载财务指标数据: {ts_code or '全部'}")

        df_list = []
        if ts_code and ',' in ts_code:
            codes = ts_code.split(',')
        else:
            codes = [ts_code] if ts_code else [None]

        for code in codes:
            df = self._api_call('fina_indicator', ts_code=code, period=period,
                               start_date=start_date, end_date=end_date)
            if df is not None and not df.empty:
                df_list.append(df)

        if df_list:
            return pd.concat(df_list, ignore_index=True)
        return pd.DataFrame()

    # ==================== 分红数据 ====================

    def download_dividend(self, ts_code: str = None) -> pd.DataFrame:
        """
        下载分红送股数据

        Args:
            ts_code: 股票代码

        Returns:
            DataFrame
        """
        self._log(f"下载分红数据: {ts_code or '全部'}")

        df_list = []
        if ts_code and ',' in ts_code:
            codes = ts_code.split(',')
        else:
            codes = [ts_code] if ts_code else [None]

        for code in codes:
            df = self._api_call('dividend', ts_code=code)
            if df is not None and not df.empty:
                df_list.append(df)

        if df_list:
            return pd.concat(df_list, ignore_index=True)
        return pd.DataFrame()

    # ==================== 股东数据 ====================

    def download_top10_holders(self, ts_code: str, period: str = None) -> pd.DataFrame:
        """下载前十大股东数据"""
        self._log(f"下载前十大股东: {ts_code}")
        return self._api_call('top10_holders', ts_code=ts_code, period=period)

    def download_top10_floatholders(self, ts_code: str, period: str = None) -> pd.DataFrame:
        """下载前十大流通股东数据"""
        self._log(f"下载前十大流通股东: {ts_code}")
        return self._api_call('top10_floatholders', ts_code=ts_code, period=period)

    def download_holder_num(self, ts_code: str = None) -> pd.DataFrame:
        """下载股东人数数据"""
        self._log(f"下载股东人数: {ts_code or '全部'}")
        return self._api_call('stk_holder_num', ts_code=ts_code)

    # ==================== 资金流向 ====================

    def download_moneyflow(self, ts_code: str = None, trade_date: str = None) -> pd.DataFrame:
        """下载个股资金流向数据"""
        self._log(f"下载资金流向: {ts_code}")
        return self._api_call('moneyflow', ts_code=ts_code, trade_date=trade_date)

    def download_moneyflow_hsgt(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """下载沪深港通资金流向"""
        self._log(f"下载沪深港通资金流向: {start_date} ~ {end_date}")
        return self._api_call('moneyflow_hsgt', start_date=start_date, end_date=end_date)

    # ==================== 大宗交易 ====================

    def download_block_trade(self, ts_code: str = None, trade_date: str = None,
                            start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """下载大宗交易数据"""
        self._log(f"下载大宗交易: {ts_code}")
        return self._api_call('block_trade', ts_code=ts_code, trade_date=trade_date,
                             start_date=start_date, end_date=end_date)

    # ==================== 股票回购 ====================

    def download_repurchase(self, ann_date: str = None, start_date: str = None,
                           end_date: str = None) -> pd.DataFrame:
        """下载股票回购数据"""
        self._log(f"下载股票回购数据")
        return self._api_call('stk_repurchase', ann_date=ann_date,
                             start_date=start_date, end_date=end_date)

    # ==================== 限售股解禁 ====================

    def download_str限售股解禁(self, ts_code: str = None) -> pd.DataFrame:
        """下载限售股解禁数据"""
        self._log(f"下载限售股解禁: {ts_code}")
        return self._api_call('stk_limit', ts_code=ts_code)

    # ==================== 保存到DuckDB ====================

    def save_to_duckdb(self, df: pd.DataFrame, table_name: str,
                       primary_keys: List[str] = None):
        """
        保存DataFrame到DuckDB（使用UPSERT）

        Args:
            df: 要保存的数据
            table_name: 表名
            primary_keys: 主键列列表，用于UPSERT
        """
        if df is None or df.empty:
            self._log(f"数据为空，跳过保存到 {table_name}", "WARN")
            return

        con = self._get_db_connection()

        try:
            # 先将所有数值类型转换为 DOUBLE，避免 INT32 溢出
            df_processed = df.copy()
            for col in df_processed.columns:
                # 跳过主键列（通常是字符串）
                if primary_keys and col in primary_keys:
                    continue
                # 将数值类型转换为 DOUBLE
                if pd.api.types.is_numeric_dtype(df_processed[col]):
                    df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce')

            # 创建表（如果不存在）- 使用更安全的类型
            con.register('temp_df', df_processed)

            # 检查表是否存在，如果存在且结构不对则重建
            table_exists = con.execute(f"""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = '{table_name}'
            """).fetchone()[0] > 0

            if table_exists:
                # 表已存在，检查是否有 INT32 类型的列（会导致溢出）
                schema = con.execute(f"DESCRIBE {table_name}").fetchdf()
                has_int32 = any(schema['column_type'] == 'INTEGER')

                if has_int32:
                    self._log(f"表 {table_name} 结构已过时（有INTEGER类型），正在重建...", "WARN")
                    con.execute(f"DROP TABLE {table_name}")
                    table_exists = False

            if not table_exists:
                # 表不存在，创建新表（所有数值列用 DOUBLE）
                columns_sql = []
                for col in df_processed.columns:
                    dtype = df_processed[col].dtype
                    col_name = col.replace("'", "''")  # 转义列名中的单引号

                    if pd.api.types.is_string_dtype(dtype) or dtype == 'object':
                        columns_sql.append(f'"{col_name}" VARCHAR')
                    elif pd.api.types.is_numeric_dtype(dtype):
                        columns_sql.append(f'"{col_name}" DOUBLE')
                    else:
                        columns_sql.append(f'"{col_name}" DOUBLE')  # 默认用 DOUBLE

                create_sql = f"""
                    CREATE TABLE {table_name} (
                        {', '.join(columns_sql)}
                    )
                """
                con.execute(create_sql)

            # 如果有主键，先删除已存在的记录
            if primary_keys:
                for _, row in df_processed.iterrows():
                    conditions = []
                    for pk in primary_keys:
                        val = row.get(pk)
                        if pd.notna(val):
                            if isinstance(val, str):
                                conditions.append(f"{pk} = '{val}'")
                            else:
                                conditions.append(f"{pk} = {val}")

                    if conditions:
                        delete_sql = f"DELETE FROM {table_name} WHERE {' AND '.join(conditions)}"
                        con.execute(delete_sql)

            # 插入新数据
            con.execute(f"INSERT INTO {table_name} SELECT * FROM temp_df")
            con.unregister('temp_df')

            self._log(f"已保存 {len(df)} 条记录到 {table_name}")

        except Exception as e:
            self._log(f"保存到 {table_name} 失败: {e}", "ERROR")
            if 'temp_df' in [t[0] for t in con.execute("SHOW TABLES").fetchall()]:
                con.unregister('temp_df')
        finally:
            con.close()

    # ==================== 批量下载 ====================

    def batch_download_financial(self, stock_list: List[str], years: int = 5,
                                 progress_callback=None) -> Dict[str, Any]:
        """
        批量下载财务数据

        Args:
            stock_list: 股票代码列表
            years: 获取最近N年的数据
            progress_callback: 进度回调函数 callback(current, total, message)

        Returns:
            结果统计
        """
        self._log(f"开始批量下载财务数据: {len(stock_list)} 只股票")

        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years)
        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')

        result = {
            'total': len(stock_list),
            'success': 0,
            'failed': 0,
            'failed_list': []
        }

        for i, stock_code in enumerate(stock_list):
            try:
                if progress_callback:
                    progress_callback(i + 1, len(stock_list), f"正在下载 {stock_code}")

                # 下载三种财务报表
                income_df = self.download_income(ts_code=stock_code,
                                                start_date=start_str, end_date=end_str)
                balance_df = self.download_balancesheet(ts_code=stock_code,
                                                        start_date=start_str, end_date=end_str)
                cashflow_df = self.download_cashflow(ts_code=stock_code,
                                                     start_date=start_str, end_date=end_str)

                # 保存到数据库
                if not income_df.empty:
                    self.save_to_duckdb(income_df, 'financial_income',
                                       primary_keys=['ts_code', 'end_date'])
                if not balance_df.empty:
                    self.save_to_duckdb(balance_df, 'financial_balance',
                                       primary_keys=['ts_code', 'end_date'])
                if not cashflow_df.empty:
                    self.save_to_duckdb(cashflow_df, 'financial_cashflow',
                                       primary_keys=['ts_code', 'end_date'])

                result['success'] += 1

            except Exception as e:
                result['failed'] += 1
                result['failed_list'].append(f"{stock_code}: {str(e)}")
                self._log(f"下载 {stock_code} 失败: {e}", "ERROR")

        return result

    def batch_download_dividend(self, stock_list: List[str],
                                progress_callback=None) -> Dict[str, Any]:
        """批量下载分红数据"""
        self._log(f"开始批量下载分红数据: {len(stock_list)} 只股票")

        result = {
            'total': len(stock_list),
            'success': 0,
            'failed': 0,
            'failed_list': []
        }

        # 分批处理（每批100只）
        batch_size = 100
        for i in range(0, len(stock_list), batch_size):
            batch = stock_list[i:i + batch_size]
            ts_codes = ','.join(batch)

            try:
                if progress_callback:
                    progress_callback(i + 1, len(stock_list), f"下载分红数据 {i+1}-{min(i+batch_size, len(stock_list))}")

                df = self.download_dividend(ts_code=ts_codes)

                if not df.empty:
                    self.save_to_duckdb(df, 'dividends', primary_keys=['ts_code', 'ex_date'])
                    result['success'] += len(batch)
                else:
                    result['failed'] += len(batch)

            except Exception as e:
                result['failed'] += len(batch)
                result['failed_list'].append(f"{ts_codes}: {str(e)}")
                self._log(f"下载分红数据失败: {e}", "ERROR")

        return result

    def get_stock_list(self, list_status: str = 'L') -> pd.DataFrame:
        """
        获取股票列表

        Args:
            list_status: 上市状态 L上市 D退市 P暂停上市

        Returns:
            DataFrame
        """
        self._log(f"获取股票列表: {list_status}")
        return self._api_call('stock_basic', exchange='', list_status=list_status,
                             fields='ts_code,symbol,name,area,industry,list_date')


if __name__ == "__main__":
    # 测试下载器
    downloader = TushareDownloader()

    # 测试获取股票列表
    print("\n=== 测试获取股票列表 ===")
    stocks = downloader.get_stock_list()
    print(f"获取到 {len(stocks)} 只股票")
    print(stocks.head())

    # 测试下载财务数据
    print("\n=== 测试下载财务数据 ===")
    income_df = downloader.download_income(ts_code='000001.SZ', period='20231231')
    print(f"利润表: {len(income_df)} 条")
    if not income_df.empty:
        print(income_df.head())

    # 测试下载分红数据
    print("\n=== 测试下载分红数据 ===")
    div_df = downloader.download_dividend(ts_code='000001.SZ')
    print(f"分红数据: {len(div_df)} 条")
    if not div_df.empty:
        print(div_df.head())
