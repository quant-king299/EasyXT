#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新下载有问题的股票数据
"""

import sys
from pathlib import Path
import duckdb

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_manager.unified_data_interface import UnifiedDataInterface


def find_problem_stocks(duckdb_path: str = r'D:/StockData/stock_data.ddb'):
    """查找有问题的股票"""
    con = duckdb.connect(duckdb_path, read_only=True)

    # 查找数据量少的或日期异常的股票
    problem_stocks = con.execute("""
        SELECT
            stock_code,
            COUNT(*) as count,
            MIN(date) as min_date,
            MAX(date) as max_date
        FROM stock_daily
        WHERE adjust_type = 'none'
        GROUP BY stock_code
        HAVING COUNT(*) < 10
           OR MIN(date) < '1990-01-01'
           OR MIN(date) > '2026-01-01'
        ORDER BY stock_code
    """).fetchdf()

    con.close()

    return problem_stocks['stock_code'].tolist()


def redownload_stock(stock_code: str, start_date: str = '2020-01-01', end_date: str = '2025-01-31'):
    """
    重新下载单只股票数据

    Args:
        stock_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
    """
    print(f"\n{'='*60}")
    print(f"重新下载: {stock_code}")
    print(f"{'='*60}")

    try:
        interface = UnifiedDataInterface()
        interface.connect(read_only=False)  # 使用写模式

        print(f"日期范围: {start_date} ~ {end_date}")

        # 删除旧数据
        print(f"删除旧数据...")
        interface.con.execute(f"DELETE FROM stock_daily WHERE stock_code = '{stock_code}'")

        # 下载新数据
        print(f"开始下载...")
        df = interface.get_stock_data(
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            period='1d',
            auto_save=True
        )

        interface.close()

        if not df.empty:
            print(f"[OK] 下载成功: {len(df)} 条记录")
            # 检查是否有date列
            if 'date' in df.columns:
                print(f"日期范围: {df['date'].min()} ~ {df['date'].max()}")
            elif df.index.name == 'date' or 'date' in str(type(df.index)):
                print(f"日期范围: {df.index.min()} ~ {df.index.max()}")
            return True
        else:
            print(f"[WARNING] 下载成功但无数据")
            return False

    except Exception as e:
        print(f"[ERROR] 下载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def redownload_all_problem_stocks():
    """重新下载所有有问题的股票"""
    print("=" * 80)
    print("查找并重新下载有问题的股票")
    print("=" * 80)

    # 查找问题股票
    print("\n[1] 查找问题股票...")
    problem_stocks = find_problem_stocks()

    if not problem_stocks:
        print("[OK] 未发现问题股票")
        return

    print(f"发现 {len(problem_stocks)} 只问题股票:")
    for stock in problem_stocks[:10]:  # 只显示前10个
        print(f"  - {stock}")
    if len(problem_stocks) > 10:
        print(f"  ... 还有 {len(problem_stocks) - 10} 只")

    # 询问是否继续
    print(f"\n总共需要重新下载 {len(problem_stocks)} 只股票")
    response = input("是否继续？(y/n): ").strip().lower()

    if response != 'y':
        print("已取消")
        return

    # 批量下载
    print("\n[2] 开始重新下载...")
    success_count = 0
    failed_count = 0

    for i, stock_code in enumerate(problem_stocks, 1):
        print(f"\n[{i}/{len(problem_stocks)}] {stock_code}")
        success = redownload_stock(stock_code)

        if success:
            success_count += 1
        else:
            failed_count += 1

    # 总结
    print("\n" + "=" * 80)
    print("下载完成！")
    print("=" * 80)
    print(f"总计: {len(problem_stocks)} 只")
    print(f"成功: {success_count} 只")
    print(f"失败: {failed_count} 只")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='重新下载有问题的股票')
    parser.add_argument('--stock', type=str, help='重新下载指定股票')
    parser.add_argument('--all', action='store_true', help='重新下载所有问题股票')
    parser.add_argument('--list', action='store_true', help='列出所有问题股票')
    parser.add_argument('--start', type=str, default='2020-01-01', help='开始日期')
    parser.add_argument('--end', type=str, default='2025-01-31', help='结束日期')

    args = parser.parse_args()

    if args.list:
        # 只列出问题股票
        print("问题股票列表:")
        problem_stocks = find_problem_stocks()
        if problem_stocks:
            for stock in problem_stocks:
                print(f"  {stock}")
            print(f"\n共 {len(problem_stocks)} 只")
        else:
            print("  未发现问题股票")

    elif args.stock:
        # 重新下载指定股票
        redownload_stock(args.stock, args.start, args.end)

    elif args.all:
        # 重新下载所有问题股票
        redownload_all_problem_stocks()

    else:
        print("使用方法:")
        print("  列出问题股票: python redownload_problem_stocks.py --list")
        print("  重新下载指定股票: python redownload_problem_stocks.py --stock 000001.SZ")
        print("  重新下载所有问题股票: python redownload_problem_stocks.py --all")
        print()
        print("示例:")
        print("  python redownload_problem_stocks.py --stock 000001.SZ --start 2020-01-01 --end 2025-01-31")
