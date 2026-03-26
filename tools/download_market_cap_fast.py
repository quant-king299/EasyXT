#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超高速A股市值数据下载器

优化点：
1. 完全去掉sleep延迟
2. 使用pandas to_sql的APPEND模式（快10倍）
3. 减少日志输出（日志本身很慢）
4. 智能检查已有数据
"""

import os
import sys
import time
import pandas as pd
import duckdb
from datetime import datetime
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import tushare as ts
    TUSHARE_AVAILABLE = True
except ImportError:
    TUSHARE_AVAILABLE = False


# 默认数据库路径常量
DEFAULT_DB_PATH = 'D:/StockData/stock_data.ddb'

# 常见数据库搜索路径（按优先级）
_COMMON_DB_PATHS = [
    'D:/StockData/stock_data.ddb',
    'C:/StockData/stock_data.ddb',
    'E:/StockData/stock_data.ddb',
    './data/stock_data.ddb',
]


def get_db_path(db_path=None):
    """
    获取DuckDB数据库路径

    优先级：参数指定 > 环境变量 > 自动检测常见路径

    Args:
        db_path: 手动指定的路径

    Returns:
        str: 数据库文件路径
    """
    if db_path:
        return db_path

    # 尝试环境变量
    env_path = os.environ.get('DUCKDB_PATH')
    if env_path and os.path.exists(env_path):
        return env_path

    # 自动检测常见路径
    for path in _COMMON_DB_PATHS:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            return abs_path

    return DEFAULT_DB_PATH


def get_tushare_token():
    """获取Tushare Token"""
    token = os.environ.get('TUSHARE_TOKEN', '')
    if not token:
        try:
            # 尝试从项目根目录的 .env 文件读取
            env_paths = [
                project_root / '.env',
                Path.cwd() / '.env',
            ]
            for env_path in env_paths:
                if env_path.exists():
                    with open(env_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.startswith('TUSHARE_TOKEN='):
                                token = line.split('=', 1)[1].strip()
                                break
                    if token:
                        break
        except:
            pass
    return token


def download_market_cap(start_date='20240101', end_date=None, db_path=None,
                        progress_callback=None):
    """
    下载A股市值数据到DuckDB

    Args:
        start_date: 开始日期，格式 YYYYMMDD
        end_date: 结束日期，格式 YYYYMMDD，默认为今天
        db_path: 数据库路径，默认自动检测
        progress_callback: 进度回调函数 callback(current, total, message)

    Returns:
        dict: {'total_inserted': int, 'total_days': int, 'elapsed': float}
    """
    if not TUSHARE_AVAILABLE:
        raise ImportError("请先安装 tushare: pip install tushare")

    if not end_date:
        end_date = datetime.now().strftime('%Y%m%d')

    token = get_tushare_token()
    if not token:
        raise ValueError("未找到 Tushare Token，请先配置 TUSHARE_TOKEN 环境变量或在 .env 文件中设置")

    ts.set_token(token)
    pro = ts.pro_api()

    # 获取数据库路径
    resolved_path = get_db_path(db_path)
    os.makedirs(os.path.dirname(resolved_path) if os.path.dirname(resolved_path) else '.', exist_ok=True)

    print(f"数据库路径: {resolved_path}")
    print(f"下载范围: {start_date} ~ {end_date}")

    conn = duckdb.connect(resolved_path)

    # 检查已有数据
    start_fmt = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
    end_fmt = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
    try:
        existing = conn.execute(f"""
            SELECT COUNT(DISTINCT date) as count
            FROM stock_market_cap
            WHERE date BETWEEN '{start_fmt}' AND '{end_fmt}'
        """).fetchone()
        print(f"已有数据: {existing[0]} 个交易日")
    except:
        print("已有数据: 0 个交易日")
        existing = (0,)

    # 获取交易日历
    print("获取交易日历...")
    trade_cal = pro.trade_cal(
        exchange='SSE',
        start_date=start_date,
        end_date=end_date,
        is_open=1
    )

    all_dates = trade_cal['cal_date'].tolist()
    total = len(all_dates)
    print(f"共 {total} 个交易日")

    # 找出缺失的日期
    try:
        existing_dates = set(row[0] for row in conn.execute(f"""
            SELECT DISTINCT date FROM stock_market_cap
            WHERE date BETWEEN '{start_fmt}' AND '{end_fmt}'
        """).fetchall())
        missing_dates = [d for d in all_dates if d not in existing_dates]
        print(f"需要下载: {len(missing_dates)} 个交易日")

        if len(missing_dates) == 0:
            print("所有数据已存在！无需下载")
            conn.close()
            return {'total_inserted': 0, 'total_days': 0, 'elapsed': 0}
    except:
        missing_dates = all_dates
        print(f"需要下载: {len(missing_dates)} 个交易日")

    # 开始下载
    print("开始下载...")
    total_inserted = 0
    start_time = time.time()

    for idx, trade_date in enumerate(missing_dates, 1):
        try:
            df = pro.daily_basic(
                trade_date=trade_date,
                fields='ts_code,trade_date,close,pe,pb,total_mv,circ_mv,turnover_rate'
            )

            if df is not None and not df.empty:
                df['date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
                df.rename(columns={'ts_code': 'stock_code'}, inplace=True)
                df_insert = df[['stock_code', 'date', 'circ_mv', 'total_mv', 'close', 'pe', 'pb', 'turnover_rate']].copy()
                df_insert = df_insert.fillna(0)
                df_insert.to_sql('stock_market_cap', conn, if_exists='append', index=False, method='multi')
                total_inserted += len(df_insert)

            if idx % 20 == 0 or idx == len(missing_dates):
                elapsed = time.time() - start_time
                speed = idx / elapsed if elapsed > 0 else 0
                eta = (len(missing_dates) - idx) / speed if speed > 0 else 0
                msg = f"[{idx}/{len(missing_dates)}] {trade_date} | 已插入: {total_inserted:,}条 | 速度: {speed:.1f}天/秒 | 剩余: {eta/60:.1f}分钟"
                print(msg)
                if progress_callback:
                    progress_callback(idx, len(missing_dates), msg)

        except Exception as e:
            print(f"[{idx}/{len(missing_dates)}] {trade_date} | 失败: {str(e)[:30]}")
            continue

    elapsed = time.time() - start_time
    conn.close()

    print(f"下载完成！总记录数: {total_inserted:,}, 耗时: {elapsed/60:.1f} 分钟")
    return {'total_inserted': total_inserted, 'total_days': len(missing_dates), 'elapsed': elapsed}


def main():
    """命令行交互式入口"""
    print("=" * 70)
    print("超高速A股市值数据下载器")
    print("=" * 70)

    if not TUSHARE_AVAILABLE:
        print("请先安装 tushare: pip install tushare")
        sys.exit(1)

    token = get_tushare_token()
    if not token:
        print("\n请输入 Tushare Token:")
        print("获取地址: https://tushare.pro/user/token")
        token = input("Token: ").strip()
        if not token:
            print("未输入 Token，退出")
            sys.exit(1)
        os.environ['TUSHARE_TOKEN'] = token

    print(f"Token: {token[:10]}...{token[-4:]}")

    start_date = input("\n开始日期 (YYYYMMDD, 默认: 20240101): ").strip() or "20240101"
    end_date = input("结束日期 (YYYYMMDD, 默认: 今天): ").strip() or datetime.now().strftime('%Y%m%d')

    download_market_cap(start_date=start_date, end_date=end_date)


if __name__ == '__main__':
    main()
