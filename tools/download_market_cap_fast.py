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

try:
    import tushare as ts
    TUSHARE_AVAILABLE = True
except ImportError:
    print("❌ 请先安装 tushare: pip install tushare")
    sys.exit(1)


def get_tushare_token():
    """获取Tushare Token"""
    token = os.environ.get('TUSHARE_TOKEN', '')
    if not token:
        try:
            with open('.env', 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('TUSHARE_TOKEN='):
                        token = line.split('=')[1].strip()
                        break
        except:
            pass
    return token


def main():
    """主函数"""
    print("=" * 70)
    print("超高速A股市值数据下载器")
    print("=" * 70)

    # 获取token
    token = get_tushare_token()
    if not token:
        print("\n请输入 Tushare Token:")
        print("获取地址: https://tushare.pro/user/token")
        token = input("Token: ").strip()

    ts.set_token(token)
    pro = ts.pro_api()

    # 配置
    db_path = 'D:/StockData/stock_data.ddb'

    print("\n请输入下载日期范围:")
    start_date = input("开始日期 (YYYYMMDD, 默认: 20240101): ").strip() or "20240101"
    end_date = input("结束日期 (YYYYMMDD, 默认: 20241231): ").strip() or "20241231"

    print(f"\n📅 下载范围: {start_date} ~ {end_date}")

    # 连接数据库
    conn = duckdb.connect(db_path)

    # 检查已有数据
    print("\n🔍 检查已有数据...")
    try:
        existing = conn.execute(f"""
            SELECT COUNT(DISTINCT date) as count
            FROM stock_market_cap
            WHERE date BETWEEN '{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}'
                AND '{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}'
        """).fetchone()
        print(f"  已有数据: {existing[0]} 个交易日")
    except:
        print("  已有数据: 0 个交易日")
        existing = (0,)

    # 获取交易日历
    print("\n获取交易日历...")
    trade_cal = pro.trade_cal(
        exchange='SSE',
        start_date=start_date,
        end_date=end_date,
        is_open=1
    )

    all_dates = trade_cal['cal_date'].tolist()
    total = len(all_dates)
    print(f"✅ 共 {total} 个交易日")

    # 找出缺失的日期
    try:
        existing_dates = set(row[0] for row in conn.execute(f"""
            SELECT DISTINCT date FROM stock_market_cap
            WHERE date BETWEEN '{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}'
                AND '{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}'
        """).fetchall())

        missing_dates = [d for d in all_dates if d not in existing_dates]
        print(f"✨ 需要下载: {len(missing_dates)} 个交易日")

        if len(missing_dates) == 0:
            print("\n✅ 所有数据已存在！无需下载")
            return
    except:
        missing_dates = all_dates
        print(f"✨ 需要下载: {len(missing_dates)} 个交易日")

    # 开始下载（超高速模式）
    print(f"\n🚀 开始下载（超高速模式）...")
    print("=" * 70)

    total_inserted = 0
    start_time = time.time()

    for idx, trade_date in enumerate(missing_dates, 1):
        try:
            # 获取数据
            df = pro.daily_basic(
                trade_date=trade_date,
                fields='ts_code,trade_date,close,pe,pb,total_mv,circ_mv,turnover_rate'
            )

            if df is not None and not df.empty:
                # 转换日期
                df['date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')

                # 重命名列
                df.rename(columns={'ts_code': 'stock_code'}, inplace=True)

                # 选择需要的列
                df_insert = df[['stock_code', 'date', 'circ_mv', 'total_mv', 'close', 'pe', 'pb', 'turnover_rate']].copy()
                df_insert = df_insert.fillna(0)

                # 使用to_sql的APPEND模式（最快！）
                df_insert.to_sql(
                    'stock_market_cap',
                    conn,
                    if_exists='append',
                    index=False,
                    method='multi'
                )

                total_inserted += len(df_insert)

            # 每20个交易日显示一次进度
            if idx % 20 == 0 or idx == len(missing_dates):
                elapsed = time.time() - start_time
                speed = idx / elapsed if elapsed > 0 else 0
                eta = (len(missing_dates) - idx) / speed if speed > 0 else 0

                print(f"[{idx}/{len(missing_dates)}] {trade_date} | "
                      f"已插入: {total_inserted:,}条 | "
                      f"速度: {speed:.1f}天/秒 | "
                      f"预计剩余: {eta/60:.1f}分钟")

        except Exception as e:
            print(f"[{idx}/{len(missing_dates)}] {trade_date} | ❌ 失败: {str(e)[:30]}")
            continue

    # 完成
    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print("✅ 下载完成！")
    print(f"  总记录数: {total_inserted:,}")
    print(f"  总耗时: {elapsed/60:.1f} 分钟")
    print(f"  平均速度: {len(missing_dates)/elapsed:.1f} 天/秒")
    print("=" * 70)

    conn.close()


if __name__ == '__main__':
    main()
