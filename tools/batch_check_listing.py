# -*- coding: utf-8 -*-
"""
稳健的批量检查股票上市日期（带重试机制）
"""
import os
import sys
import pandas as pd
from datetime import datetime
import time

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 读取.env
env_file = '.env'
if os.path.exists(env_file):
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip() and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

import tushare as ts
import duckdb

TOKEN = os.getenv('TUSHARE_TOKEN')
if not TOKEN:
    print("[ERROR] TUSHARE_TOKEN not set")
    sys.exit(1)

ts.set_token(TOKEN)
pro = ts.pro_api()

DUCKDB_PATH = os.getenv('DUCKDB_PATH', 'D:/StockData/stock_data.ddb')

print("="*70)
print("批量检查股票上市日期（稳健版）")
print("="*70)

START_DATE = '2022-01-01'

def get_list_date_with_retry(stock_code, max_retries=3, delay=2):
    """带重试机制的获取上市日期"""
    for attempt in range(max_retries):
        try:
            # 方法1：使用stock_basic
            basic_info = pro.stock_basic(
                ts_code=stock_code,
                fields='ts_code,name,list_date,market'
            )

            if not basic_info.empty:
                return {
                    'code': stock_code,
                    'name': basic_info.iloc[0]['name'],
                    'list_date': basic_info.iloc[0]['list_date'],
                    'market': basic_info.iloc[0]['market'],
                    'source': 'stock_basic'
                }

            # 方法2：使用daily_basic
            basic_info = pro.daily_basic(
                ts_code=stock_code,
                fields='ts_code,list_date'
            )

            if not basic_info.empty:
                return {
                    'code': stock_code,
                    'name': 'N/A',
                    'list_date': basic_info.iloc[0]['list_date'],
                    'market': 'N/A',
                    'source': 'daily_basic'
                }

            # 如果都失败，返回None
            return None

        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  [{stock_code}] 重试 {attempt+1}/{max_retries}: {str(e)[:30]}")
                time.sleep(delay * (attempt + 1))  # 递增延迟
            else:
                print(f"  [{stock_code}] 失败: {str(e)[:40]}")
                return {'code': stock_code, 'error': str(e)[:50]}

    return None

try:
    # 连接DuckDB
    con = duckdb.connect(DUCKDB_PATH, read_only=True)

    # 查询所有需要补充历史的股票
    query = """
        SELECT
            stock_code,
            MIN(date) as earliest_date
        FROM stock_daily
        GROUP BY stock_code
        HAVING MIN(date) > '2022-01-01'
        ORDER BY stock_code
    """

    df_stocks = con.execute(query).df()

    print(f"\n发现 {len(df_stocks)} 只股票需要检查")
    print(f"开始日期: {START_DATE}\n")

    con.close()

    # 统计
    results = {
        'not_listed': [],      # 未上市
        'already_listed': [],  # 已上市
        'not_found': [],       # 未找到
        'error': []            # 查询出错
    }

    # 逐个检查（慢但稳定）
    total = len(df_stocks)
    for i, row in df_stocks.iterrows():
        stock_code = row['stock_code']

        if (i + 1) % 10 == 0:
            print(f"进度: {i+1}/{total} ({(i+1)/total*100:.1f}%)")

        # 获取上市日期（带重试）
        info = get_list_date_with_retry(stock_code, max_retries=2, delay=1)

        if info and 'error' in info:
            results['error'].append(info)
        elif info and 'list_date' in info:
            list_date = info['list_date']
            list_date_formatted = f"{list_date[:4]}-{list_date[4:6]}-{list_date[6:]}"

            # 判断是否在2022-01-01之前上市
            if list_date > '20220101':
                results['not_listed'].append({
                    'code': stock_code,
                    'name': info.get('name', 'N/A'),
                    'list_date': list_date_formatted,
                    'market': info.get('market', 'N/A')
                })
            else:
                results['already_listed'].append({
                    'code': stock_code,
                    'name': info.get('name', 'N/A'),
                    'list_date': list_date_formatted,
                    'market': info.get('market', 'N/A'),
                    'earliest': row['earliest_date'].strftime('%Y-%m-%d')
                })
                print(f"  ! {stock_code} ({info.get('name', 'N/A')}) 已上市于 {list_date_formatted}")
        else:
            results['not_found'].append(stock_code)

        # 避免请求过快（每秒1次）
        time.sleep(1)

    # 输出结果
    print("\n" + "="*70)
    print("统计结果")
    print("="*70)

    print(f"\n[OK] 未上市股票（2022-01-01之后上市）: {len(results['not_listed'])} 只")
    print(f"    这些股票无法获取2022年之前的历史数据 - 正常现象")

    print(f"\n[WARNING] 已上市但无数据（2022-01-01之前上市）: {len(results['already_listed'])} 只")
    print(f"    这些股票应该有历史数据但获取失败 - 需要调查")

    print(f"\n[?] 未找到上市信息: {len(results['not_found'])} 只")
    print(f"\n[ERROR] 查询出错: {len(results['error'])} 只")

    # 显示已上市的股票
    if results['already_listed']:
        print("\n" + "="*70)
        print(f"已上市但无数据的股票详情（{len(results['already_listed'])}只）：")
        print("="*70)
        for item in results['already_listed'][:20]:
            print(f"  {item['code']} ({item['name']}):")
            print(f"    上市日期: {item['list_date']}")
            print(f"    最早数据: {item['earliest']}")
        if len(results['already_listed']) > 20:
            print(f"  ... 还有 {len(results['already_listed'])-20} 只")

    # 显示未上市股票示例
    if results['not_listed']:
        print("\n" + "="*70)
        print(f"未上市股票示例（{len(results['not_listed'])}只中的前10只）：")
        print("="*70)
        for item in results['not_listed'][:10]:
            print(f"  {item['code']} ({item['name']}, {item['market']}): {item['list_date']}")
        if len(results['not_listed']) > 10:
            print(f"  ... 还有 {len(results['not_listed'])-10} 只")

    print("\n" + "="*70)
    print("结论")
    print("="*70)

    total_checked = len(results['not_listed']) + len(results['already_listed']) + len(results['not_found']) + len(results['error'])

    if len(results['already_listed']) == 0:
        print(f"[OK] 所有 {total_checked} 只失败股票都是因为上市时间晚于2022-01-01")
        print("      这是完全正常的现象，无法获取上市之前的历史数据")
    else:
        pct_not_listed = len(results['not_listed']) / total_checked * 100
        pct_already_listed = len(results['already_listed']) / total_checked * 100

        print(f"统计结果:")
        print(f"  - {len(results['not_listed'])}只 ({pct_not_listed:.1f}%) 未上市 - 正常")
        print(f"  - {len(results['already_listed'])}只 ({pct_already_listed:.1f}%) 已上市但无数据 - 需调查")

        if len(results['already_listed']) < 20:
            print(f"\n  大部分失败都是正常的新股，只有{len(results['already_listed'])}只需要进一步调查")
        else:
            print(f"\n  有{len(results['already_listed'])}只已上市股票无法获取数据，可能原因：")
            print(f"    1. QMT本地数据不完整（科创板/创业板新股）")
            print(f"    2. Tushare数据缺失")
            print(f"    3. 股票长期停牌")

    print("="*70)

except Exception as e:
    print(f"\n错误: {e}")
    import traceback
    traceback.print_exc()
