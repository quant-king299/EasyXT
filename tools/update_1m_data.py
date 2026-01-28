#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Update 1-minute data from QMT and save to local database
自动更新1分钟数据并保存到本地数据库

Usage:
    python tools/update_1m_data.py --stocks 511380.SH
    python tools/update_1m_data.py --stocks 511380.SH,512100.SH --period 5m
    python tools/update_1m_data.py --stocks 511380.SH --force
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# Setup paths
project_root = Path(__file__).parents[1]
sys.path.insert(0, str(project_root))
factor_platform_path = project_root / "101因子" / "101因子分析平台" / "src"
sys.path.insert(0, str(factor_platform_path))

from xtquant import xtdata
from data_manager import LocalDataManager

def convert_xtdata_to_dataframe(stock_code, period='1m'):
    """Convert xtdata format to pandas DataFrame"""
    data = xtdata.get_market_data(
        stock_list=[stock_code],
        period=period,
        count=0
    )

    if not data or 'time' not in data:
        return None

    time_df = data['time']
    timestamps = time_df.columns.tolist()

    records = []
    for i, ts in enumerate(timestamps):
        try:
            ts_str = str(ts)
            if len(ts_str) >= 14:
                date_str = ts_str[:8]
                time_str = ts_str[8:14]
                datetime_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
                dt = pd.to_datetime(datetime_str)
            else:
                dt = pd.to_datetime(ts)

            open_val = data['open'].iloc[0, i] if 'open' in data else None
            high_val = data['high'].iloc[0, i] if 'high' in data else None
            low_val = data['low'].iloc[0, i] if 'low' in data else None
            close_val = data['close'].iloc[0, i] if 'close' in data else None
            volume_val = data['volume'].iloc[0, i] if 'volume' in data else None
            amount_val = data['amount'].iloc[0, i] if 'amount' in data else None

            records.append({
                'time': dt,
                'open': float(open_val) if open_val is not None else None,
                'high': float(high_val) if high_val is not None else None,
                'low': float(low_val) if low_val is not None else None,
                'close': float(close_val) if close_val is not None else None,
                'volume': float(volume_val) if volume_val is not None else 0,
                'amount': float(amount_val) if amount_val is not None else 0
            })
        except Exception:
            continue

    df = pd.DataFrame(records)
    if not df.empty:
        df.set_index('time', inplace=True)
        df.sort_index(inplace=True)

    return df

def update_stock_data(stock_code, period='1m', force_download=False):
    """Update single stock data"""
    print(f"\n{'='*60}")
    print(f"Processing {stock_code} {period}")
    print(f"{'='*60}")

    # 1. Download latest data from QMT
    print("\n[1/3] Downloading from QMT...")

    # Get current date and calculate start date (last 3 months to ensure we get recent data)
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')

    try:
        xtdata.download_history_data(
            stock_code=stock_code,
            period=period,
            start_time=start_date,
            end_time=end_date
        )
        print("[OK] Download completed")
    except Exception as e:
        print(f"[WARNING] Download failed: {e}")
        print("Trying to use existing QMT data...")

    # 2. Convert data
    print("\n[2/3] Converting data format...")
    df = convert_xtdata_to_dataframe(stock_code, period)

    if df is None or df.empty:
        print("[ERROR] No data available")
        return False

    print(f"[OK] Converted {len(df)} records")
    print(f"  Date range: {df.index.min()} to {df.index.max()}")

    # 3. Save to local database
    print("\n[3/3] Saving to local database...")
    manager = LocalDataManager()

    # Determine data type
    data_type_map = {
        '1m': '1min',
        '5m': '5min',
        '15m': '15min',
        '30m': '30min',
        '60m': '60min',
        '1d': 'daily'
    }
    data_type = data_type_map.get(period, '1min')

    # Check if existing data exists
    existing_file = manager.storage.get_file_info(stock_code, data_type)

    # Save data
    success, file_size = manager.storage.save_data(df, stock_code, data_type)

    if not success:
        print("[ERROR] Failed to save data")
        manager.close()
        return False

    print(f"[OK] Data saved ({file_size:.2f} MB)")

    # Determine symbol type
    if stock_code.endswith('.SH') or stock_code.endswith('.SZ'):
        if stock_code.startswith('5') or stock_code.startswith('15'):
            symbol_type = 'etf'
        else:
            symbol_type = 'stock'
    else:
        symbol_type = 'stock'

    # Update metadata
    manager.metadata.update_data_version(
        symbol=stock_code,
        symbol_type=symbol_type,
        start_date=str(df.index.min().date()),
        end_date=str(df.index.max().date()),
        record_count=len(df),
        file_size=file_size
    )

    manager.close()

    # Summary
    print(f"\n[SUCCESS] {stock_code} {period} data updated!")
    print(f"  Records: {len(df):,}")
    print(f"  Date range: {df.index.min().date()} to {df.index.max().date()}")
    print(f"  File size: {file_size:.2f} MB")

    if existing_file:
        print(f"  Previous size: {existing_file['file_size_mb']:.2f} MB")

    return True

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Update 1-minute data from QMT')
    parser.add_argument('--stocks', required=True, help='Stock codes separated by comma')
    parser.add_argument('--period', default='1m', choices=['1m', '5m', '15m', '30m', '60m'],
                        help='Data period (default: 1m)')
    parser.add_argument('--force', action='store_true', help='Force re-download all data')

    args = parser.parse_args()

    # Parse stock list
    stock_list = []
    for stock in args.stocks.split(','):
        stock = stock.strip()
        if not stock:
            continue

        # Normalize stock code
        if '.' not in stock and len(stock) == 6:
            if stock.startswith(('000', '002', '300', '301', '15')):
                stock_list.append(f"{stock}.SZ")
            elif stock.startswith(('600', '601', '603', '605', '688', '5', '51')):
                stock_list.append(f"{stock}.SH")
            else:
                stock_list.append(stock)
        else:
            stock_list.append(stock)

    print("=" * 60)
    print("QMT 1-Minute Data Update Tool")
    print("=" * 60)
    print(f"Stocks: {', '.join(stock_list)}")
    print(f"Period: {args.period}")
    print(f"Total stocks: {len(stock_list)}")
    print("=" * 60)

    # Update each stock
    success_count = 0
    failed_count = 0

    for stock_code in stock_list:
        try:
            if update_stock_data(stock_code, args.period, args.force):
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"[ERROR] Failed to update {stock_code}: {e}")
            failed_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("Update Summary:")
    print(f"  Total: {len(stock_list)}")
    print(f"  Success: {success_count}")
    print(f"  Failed: {failed_count}")
    print("=" * 60)

if __name__ == '__main__':
    main()
