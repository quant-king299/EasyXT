#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键补充数据工具（独立运行）
在GUI关闭的情况下运行，避免数据库锁定冲突
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def update_data():
    """一键补充数据"""
    print("=" * 70)
    print("一键补充数据工具")
    print("=" * 70)
    print()
    print("注意：请确保GUI已关闭后再运行此工具")
    print()

    try:
        from xtquant import xtdata
        import duckdb

        db_path = r'D:/StockData/stock_data.ddb'

        # 步骤1：检查需要更新的股票
        print("[步骤1] 检查需要更新的股票...")
        read_con = duckdb.connect(db_path, read_only=True)
        try:
            query = """
                SELECT
                    stock_code,
                    MAX(date) as latest_date,
                    DATEDIFF('day', MAX(date), CURRENT_DATE) as days_behind
                FROM stock_daily
                GROUP BY stock_code
                HAVING DATEDIFF('day', MAX(date), CURRENT_DATE) > 3
                ORDER BY days_behind DESC
            """
            df_stocks = read_con.execute(query).df()
        finally:
            read_con.close()

        if df_stocks.empty:
            print("[OK] 所有数据都是最新的，无需更新")
            return

        stock_codes = df_stocks['stock_code'].tolist()
        print(f"[OK] 发现 {len(stock_codes)} 只股票需要更新")
        print()

        total = len(stock_codes)
        success_count = 0
        failed_count = 0
        skipped_count = 0
        failed_list = []

        # 步骤2：批量收集数据
        print("[步骤2] 从QMT获取数据...")
        update_data = []

        for i, stock_code in enumerate(stock_codes):
            try:
                # 进度显示
                if (i + 1) % 100 == 0 or i == 0:
                    print(f"  进度: {i+1}/{total} ({(i+1)/total*100:.1f}%)")

                # 获取最新日期和落后天数
                latest_date = df_stocks[df_stocks['stock_code'] == stock_code]['latest_date'].values[0]
                days_behind = df_stocks[df_stocks['stock_code'] == stock_code]['days_behind'].values[0]

                # 计算需要获取的条数（加20天缓冲，确保覆盖所有周末和节假日）
                count = int(days_behind) + 20
                # 最少获取30条，最多获取100条
                count = max(30, min(count, 100))

                # 从QMT获取数据（使用count参数）
                data = xtdata.get_market_data_ex(
                    stock_list=[stock_code],
                    period='1d',
                    count=count
                )

                if isinstance(data, dict) and stock_code in data:
                    df = data[stock_code]
                    if not df.empty:
                        # 转换数据格式
                        df_processed = pd.DataFrame({
                            'stock_code': stock_code,
                            'symbol_type': 'stock',
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

                        # 只保留最新日期之后的数据
                        latest_date_str = pd.to_datetime(latest_date).strftime('%Y-%m-%d')
                        df_processed = df_processed[df_processed['date'] > latest_date_str]

                        if df_processed.empty:
                            skipped_count += 1
                            continue

                        # 填充复权数据
                        for col in ['open', 'high', 'low', 'close']:
                            df_processed[f'{col}_front'] = df_processed[col]
                            df_processed[f'{col}_back'] = df_processed[col]
                            df_processed[f'{col}_geometric_front'] = df_processed[col]
                            df_processed[f'{col}_geometric_back'] = df_processed[col]

                        update_data.append(df_processed)
                        success_count += 1
                    else:
                        skipped_count += 1
                else:
                    failed_count += 1
                    failed_list.append(stock_code)

            except Exception as e:
                print(f"  [{i+1}/{total}] {stock_code}: [错误] {str(e)[:50]}")
                failed_count += 1
                failed_list.append(stock_code)

        print(f"  收集完成: {len(update_data)} 条记录")
        print()

        # 步骤3：批量写入
        if update_data:
            print("[步骤3] 保存到DuckDB...")
            df_all = pd.concat(update_data, ignore_index=True)

            write_con = duckdb.connect(db_path, read_only=False)
            try:
                write_con.register('temp_updates', df_all)
                write_con.execute("INSERT INTO stock_daily SELECT * FROM temp_updates")
                write_con.unregister('temp_updates')
                print(f"[OK] 成功保存 {len(df_all)} 条记录")
            finally:
                write_con.close()

        # 输出汇总
        print()
        print("=" * 70)
        print("更新完成！")
        print("=" * 70)
        print(f"总数: {total}")
        print(f"成功: {success_count}")
        print(f"跳过: {skipped_count}")
        print(f"失败: {failed_count}")

        if failed_list:
            print()
            print("失败的股票:")
            for stock in failed_list[:10]:
                print(f"  - {stock}")
            if len(failed_list) > 10:
                print(f"  ... 还有 {len(failed_list) - 10} 只")

    except ImportError as e:
        print(f"[错误] 导入失败: {e}")
        print("请确保已安装: pip install pyqt5 duckdb")
    except Exception as e:
        print(f"[错误] 更新失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    update_data()
