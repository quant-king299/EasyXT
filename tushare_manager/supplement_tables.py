#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补充 DuckDB 缺失表：stock_basic（股票基本信息）和 index_components（指数成分股）
数据来源：Tushare

用法:
    python -m tushare_manager.supplement_tables --all
    python -m tushare_manager.supplement_tables --stock-basic
    python -m tushare_manager.supplement_tables --index-components --index 000300.SH,399101.SZ
"""

import argparse
import time
import pandas as pd
from datetime import datetime
from typing import List, Optional

try:
    from .tushare_downloader import TushareDownloader
except ImportError:
    from tushare_downloader import TushareDownloader


def download_stock_basic(db_path: str = None) -> pd.DataFrame:
    """下载股票基本信息并保存到 DuckDB"""
    dl = TushareDownloader(db_path=db_path)

    dl._log("下载股票基本信息 (stock_basic)...")
    df = dl._api_call('stock_basic',
                      exchange='',
                      list_status='L',
                      fields='ts_code,symbol,name,area,industry,market,list_date,delist_date,is_hs,exchange,curr_type,enname')
    if df is None or df.empty:
        dl._log("stock_basic 下载失败", "ERROR")
        return pd.DataFrame()

    dl._log(f"获取 {len(df)} 条股票基本信息")
    dl.save_to_duckdb(df, 'stock_basic', primary_keys=['ts_code'])
    dl._log(f"stock_basic 已保存到 DuckDB ({len(df)} 条)")

    # 也下载已退市股票，以便回测时识别
    dl._log("下载退市股票信息...")
    df_delist = dl._api_call('stock_basic',
                             exchange='',
                             list_status='D',
                             fields='ts_code,symbol,name,area,industry,market,list_date,delist_date,is_hs,exchange,curr_type,enname')
    if df_delist is not None and not df_delist.empty:
        dl.save_to_duckdb(df_delist, 'stock_basic', primary_keys=['ts_code'])
        dl._log(f"退市股票: {len(df_delist)} 条已追加")

    return pd.concat([df, df_delist], ignore_index=True) if df_delist is not None and not df_delist.empty else df


def download_index_components(
    index_codes: List[str] = None,
    start_date: str = '20200101',
    db_path: str = None
) -> pd.DataFrame:
    """
    下载指数成分股权重数据

    Args:
        index_codes: 指数代码列表，默认沪深300+中证500+中小综指
        start_date: 起始日期
        db_path: DuckDB 路径
    """
    if index_codes is None:
        index_codes = ['000300.SH', '000905.SH', '399101.SZ']

    dl = TushareDownloader(db_path=db_path)
    all_dfs = []

    for index_code in index_codes:
        dl._log(f"下载指数成分股: {index_code} (从 {start_date})...")

        # 按月批量下载，尊重 Tushare 频率限制
        start = datetime.strptime(start_date, '%Y%m%d')
        end = datetime.now()
        current = start

        count = 0
        while current <= end:
            month_start = current.strftime('%Y%m%d')
            # 下个月1号
            if current.month == 12:
                month_end = datetime(current.year + 1, 1, 1).strftime('%Y%m%d')
            else:
                month_end = datetime(current.year, current.month + 1, 1).strftime('%Y%m%d')

            df = dl._api_call('index_weight',
                              index_code=index_code,
                              start_date=month_start,
                              end_date=month_end)
            if df is not None and not df.empty:
                all_dfs.append(df)
                count += len(df)

            # 每批间隔稍长
            time.sleep(0.2)

            # 推进到下个月
            if current.month == 12:
                current = datetime(current.year + 1, 1, 1)
            else:
                current = datetime(current.year, current.month + 1, 1)

        dl._log(f"  {index_code}: {count} 条成分股数据")

    if not all_dfs:
        dl._log("未获取到任何指数成分股数据", "ERROR")
        return pd.DataFrame()

    result = pd.concat(all_dfs, ignore_index=True)
    dl.save_to_duckdb(result, 'index_components', primary_keys=['index_code', 'con_code', 'trade_date'])
    dl._log(f"index_components 已保存到 DuckDB ({len(result)} 条)")

    return result


def main():
    parser = argparse.ArgumentParser(description="补充 DuckDB 缺失表")
    parser.add_argument('--all', action='store_true', help='下载所有缺失表')
    parser.add_argument('--stock-basic', action='store_true', help='仅下载 stock_basic')
    parser.add_argument('--index-components', action='store_true', help='仅下载 index_components')
    parser.add_argument('--index', default='000300.SH,000905.SH,399101.SZ',
                        help='指数代码，逗号分隔')
    parser.add_argument('--start', default='20200101', help='指数成分股起始日期')
    parser.add_argument('--db-path', default=None, help='DuckDB 路径')
    args = parser.parse_args()

    if not any([args.all, args.stock_basic, args.index_components]):
        args.all = True

    if args.all or args.stock_basic:
        download_stock_basic(db_path=args.db_path)

    if args.all or args.index_components:
        index_codes = [c.strip() for c in args.index.split(',')]
        download_index_components(index_codes=index_codes,
                                  start_date=args.start,
                                  db_path=args.db_path)

    print("\n完成!")


if __name__ == '__main__':
    main()
