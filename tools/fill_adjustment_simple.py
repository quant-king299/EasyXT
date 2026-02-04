#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单填充复权数据 - 使用现有数据
不依赖分红数据，直接复制原始数据到复权列
"""

import duckdb
import pandas as pd
from datetime import datetime

def fill_adjustment_simple():
    """简单填充复权数据（直接复制原始数据）"""
    duckdb_path = r'D:/StockData/stock_data.ddb'

    print("=" * 80)
    print("简单填充五维复权数据")
    print("=" * 80)
    print("\n说明: 将原始OHLC数据复制到复权列")
    print("适用: 债券、ETF等通常不分红的标的")
    print()

    # 使用只读模式检查
    try:
        con = duckdb.connect(duckdb_path, read_only=False)
        print("[OK] 数据库连接成功")
    except Exception as e:
        print(f"[ERROR] 无法连接数据库: {e}")
        print("\n请尝试:")
        print("1. 关闭所有使用该数据库的程序")
        print("2. 删除 D:\\StockData\\stock_data.ddb.wal 文件（如果存在）")
        return

    # 获取股票列表
    stocks = con.execute("""
        SELECT DISTINCT stock_code
        FROM stock_daily
        WHERE adjust_type = 'none'
        ORDER BY stock_code
    """).fetchdf()['stock_code'].tolist()

    print(f"\n共 {len(stocks)} 只股票需要处理")
    print("开始处理...\n")

    success_count = 0
    failed_count = 0

    for i, stock_code in enumerate(stocks, 1):
        try:
            # 检查是否已有复权数据
            check = con.execute(f"""
                SELECT COUNT(*) as cnt
                FROM stock_daily
                WHERE stock_code = '{stock_code}'
                  AND open_front IS NOT NULL
            """).fetchone()

            if check and check[0] > 0:
                print(f"[{i}/{len(stocks)}] {stock_code}... [SKIP] 已有数据")
                success_count += 1
                continue

            # 直接更新：将原始数据复制到复权列
            con.execute(f"""
                UPDATE stock_daily
                SET
                    open_front = open,
                    high_front = high,
                    low_front = low,
                    close_front = close,
                    open_back = open,
                    high_back = high,
                    low_back = low,
                    close_back = close,
                    open_geometric_front = open,
                    high_geometric_front = high,
                    low_geometric_front = low,
                    close_geometric_front = close,
                    open_geometric_back = open,
                    high_geometric_back = high,
                    low_geometric_back = low,
                    close_geometric_back = close
                WHERE stock_code = '{stock_code}'
                  AND adjust_type = 'none'
            """)

            affected = con.execute(f"""
                SELECT COUNT(*) FROM stock_daily
                WHERE stock_code = '{stock_code}' AND adjust_type = 'none'
            """).fetchone()[0]

            print(f"[{i}/{len(stocks)}] {stock_code}... [OK] {affected}条")
            success_count += 1

        except Exception as e:
            print(f"[{i}/{len(stocks)}] {stock_code}... [ERROR] {str(e)[:50]}")
            failed_count += 1

    con.close()

    print("\n" + "=" * 80)
    print("处理完成！")
    print("=" * 80)
    print(f"总计: {len(stocks)} 只")
    print(f"成功: {success_count} 只")
    print(f"失败: {failed_count} 只")

    # 验证结果
    print("\n验证结果:")
    con = duckdb.connect(duckdb_path, read_only=True)
    verify = con.execute("""
        SELECT
            COUNT(DISTINCT stock_code) as stocks,
            COUNT(*) as total_rows,
            COUNT(open_front) as has_front
        FROM stock_daily
        WHERE adjust_type = 'none'
    """).fetchdf()
    con.close()

    print(verify.to_string(index=False))


if __name__ == "__main__":
    fill_adjustment_simple()
