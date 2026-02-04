#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补充更新缺失的股票数据
检查DuckDB中数据较旧的股票，从QMT补充最新数据
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def update_missing_stock_data(stock_codes=None, days_behind=30):
    """
    补充更新缺失的股票数据

    Args:
        stock_codes: 指定股票代码列表，None表示自动查找落后股票
        days_behind: 落后天数阈值，默认30天
    """
    print("=" * 70)
    print("补充更新缺失的股票数据")
    print("=" * 70)

    try:
        from data_manager.duckdb_connection_pool import get_db_manager
        from xtquant import xtdata
        import pandas as pd

        print("\n[步骤1] 连接数据源...")
        manager = get_db_manager(r'D:/StockData/stock_data.ddb')

        print("[步骤2] 查找需要更新的股票...")

        if stock_codes is None:
            # 自动查找落后超过指定天数的股票
            query = f"""
                SELECT
                    stock_code,
                    MAX(date) as latest_date,
                    DATEDIFF('day', MAX(date), CURRENT_DATE) as days_behind
                FROM stock_daily
                GROUP BY stock_code
                HAVING DATEDIFF('day', MAX(date), CURRENT_DATE) > {days_behind}
                ORDER BY days_behind DESC
            """
            df_stocks = manager.execute_read_query(query)
            stock_codes = df_stocks['stock_code'].tolist()

        if not stock_codes:
            print(f"\n✓ 没有发现需要更新的股票（落后>{days_behind}天）")
            return

        print(f"\n发现 {len(stock_codes)} 只股票需要更新:")
        print(f"  {', '.join(stock_codes[:20])}")
        if len(stock_codes) > 20:
            print(f"  ... 还有 {len(stock_codes) - 20} 只")

        print("\n[步骤3] 从QMT补充数据...")
        print("-" * 70)

        success_count = 0
        failed_count = 0
        skipped_count = 0

        for idx, stock_code in enumerate(stock_codes, 1):
            try:
                print(f"\n[{idx}/{len(stock_codes)}] {stock_code}:")

                # 查询该股票在DuckDB中的最新日期
                query = f"""
                    SELECT MAX(date) as latest_date
                    FROM stock_daily
                    WHERE stock_code = '{stock_code}'
                """
                result = manager.execute_read_query(query)
                if result.empty:
                    print("  ⊗ 数据库中无该股票记录，跳过")
                    skipped_count += 1
                    continue

                latest_date = result.iloc[0]['latest_date']
                print(f"  数据库最新日期: {latest_date}")

                # 计算需要补充的日期范围
                start_date = (pd.to_datetime(latest_date) + timedelta(days=1)).strftime('%Y%m%d')
                end_date = (datetime.now() + timedelta(days=1)).strftime('%Y%m%d')

                print(f"  补充范围: {start_date} ~ {end_date}")

                # 从QMT获取数据
                print(f"  正在从QMT下载...")
                try:
                    download_result = xtdata.download_history_data2(
                        stock_code,
                        '1d',
                        start_time=start_date,
                        end_time=end_date
                    )
                except TypeError as e:
                    # API参数顺序可能不同，尝试不同的调用方式
                    print(f"  警告: download_history_data2调用失败，尝试直接获取数据...")
                    download_result = None

                # 获取数据
                data = xtdata.get_market_data_ex(
                    stock_list=[stock_code],
                    period='1d',
                    start_time=start_date,
                    end_time=end_date
                )

                if isinstance(data, dict) and stock_code in data:
                    df = data[stock_code]
                    if df.empty:
                        print("  ⊗ QMT无新数据")
                        skipped_count += 1
                        continue

                    print(f"  获取到 {len(df)} 条新数据")

                    # 转换数据格式
                    df_processed = pd.DataFrame({
                        'stock_code': stock_code,
                        'symbol_type': 'stock',  # 固定为stock
                        'date': pd.to_datetime(df['time'], unit='ms').dt.strftime('%Y-%m-%d'),
                        'period': '1d',
                        'open': df['open'],
                        'high': df['high'],
                        'low': df['low'],
                        'close': df['close'],
                        'volume': df['volume'].astype('int64'),
                        'amount': df['amount'],
                        'adjust_type': 'none',
                        'factor': 1.0,
                        'created_at': datetime.now(),
                        'updated_at': datetime.now()
                    })

                    # 填充复权数据（与原始价格相同）
                    for col in ['open', 'high', 'low', 'close']:
                        df_processed[f'{col}_front'] = df_processed[col]
                        df_processed[f'{col}_back'] = df_processed[col]
                        df_processed[f'{col}_geometric_front'] = df_processed[col]
                        df_processed[f'{col}_geometric_back'] = df_processed[col]

                    # 保存到DuckDB
                    print(f"  正在保存到DuckDB...")

                    # 使用原生DuckDB连接插入数据
                    with manager.get_write_connection() as con:
                        con.register('temp_data', df_processed)
                        con.execute("""
                            INSERT INTO stock_daily
                            SELECT * FROM temp_data
                        """)
                        con.unregister('temp_data')

                    # 验证
                    new_count = manager.execute_read_query(f"""
                        SELECT COUNT(*) as count
                        FROM stock_daily
                        WHERE stock_code = '{stock_code}'
                          AND date > '{latest_date}'
                    """).iloc[0]['count']

                    print(f"  ✓ 成功补充 {new_count} 条记录")
                    success_count += 1

                else:
                    print("  ⊗ 获取数据失败")
                    failed_count += 1

            except Exception as e:
                print(f"  ⊗ 错误: {e}")
                failed_count += 1

        # 输出汇总
        print("\n" + "=" * 70)
        print("补充更新完成！")
        print("=" * 70)
        print(f"总计: {len(stock_codes)} 只股票")
        print(f"成功: {success_count} 只")
        print(f"失败: {failed_count} 只")
        print(f"跳过: {skipped_count} 只")

    except Exception as e:
        print(f"\n✗ 更新失败: {e}")
        import traceback
        traceback.print_exc()


def update_specific_stocks():
    """更新指定的几只股票"""
    # 更新落后最多的几只股票
    stocks = ['000001.SZ', '000004.SZ']
    update_missing_stock_data(stocks)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='补充更新缺失的股票数据')
    parser.add_argument('--stocks', nargs='+', help='指定股票代码列表')
    parser.add_argument('--days', type=int, default=30, help='落后天数阈值（默认30天）')
    parser.add_argument('--auto', action='store_true', help='自动更新所有落后股票')

    args = parser.parse_args()

    if args.stocks:
        update_missing_stock_data(args.stocks)
    elif args.auto:
        update_missing_stock_data(days_behind=args.days)
    else:
        # 默认更新指定的问题股票
        update_specific_stocks()
