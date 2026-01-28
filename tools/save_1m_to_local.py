#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Save QMT 1-minute data to local database
将QMT的1分钟数据保存到本地数据库
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

project_root = Path(__file__).parents[1]
sys.path.insert(0, str(project_root))

# Add 101 factor platform path
factor_platform_path = project_root / "101因子" / "101因子分析平台" / "src"
sys.path.insert(0, str(factor_platform_path))

from xtquant import xtdata
from data_manager import LocalDataManager

def convert_xtdata_to_dataframe(stock_code, period='1m'):
    """
    Convert xtdata format to pandas DataFrame

    Args:
        stock_code: Stock code like '511380.SH'
        period: Data period ('1m', '5m', etc.)

    Returns:
        DataFrame with standard columns
    """
    print(f"Fetching {stock_code} {period} data from QMT...")

    # Get data from QMT
    data = xtdata.get_market_data(
        stock_list=[stock_code],
        period=period,
        count=0  # Get all data
    )

    if not data or 'time' not in data:
        print(f"[ERROR] No data available for {stock_code}")
        return None

    # Extract data from wide format to long format
    time_df = data['time']

    # Get timestamps (columns)
    timestamps = time_df.columns.tolist()

    print(f"Found {len(timestamps)} records")

    # Build DataFrame
    records = []

    for i, ts in enumerate(timestamps):
        try:
            # Parse timestamp (format: YYYYMMDDHHMMSS or int)
            ts_str = str(ts)

            if len(ts_str) >= 14:
                # Format: YYYYMMDDHHMMSS
                date_str = ts_str[:8]
                time_str = ts_str[8:14]
                datetime_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
                dt = pd.to_datetime(datetime_str)
            else:
                # Try to parse as is
                dt = pd.to_datetime(ts)

            # Extract OHLCV data
            # Each field is a DataFrame with 1 row and many columns
            open_val = data['open'].iloc[0, i] if 'open' in data else None
            high_val = data['high'].iloc[0, i] if 'high' in data else None
            low_val = data['low'].iloc[0, i] if 'low' in data else None
            close_val = data['close'].iloc[0, i] if 'close' in data else None
            volume_val = data['volume'].iloc[0, i] if 'volume' in data else None
            amount_val = data['amount'].iloc[0, i] if 'amount' in data else None

            record = {
                'time': dt,
                'open': float(open_val) if open_val is not None else None,
                'high': float(high_val) if high_val is not None else None,
                'low': float(low_val) if low_val is not None else None,
                'close': float(close_val) if close_val is not None else None,
                'volume': float(volume_val) if volume_val is not None else 0,
                'amount': float(amount_val) if amount_val is not None else 0
            }

            records.append(record)

        except Exception as e:
            print(f"[WARNING] Failed to process record {i}: {e}")
            continue

    # Create DataFrame
    df = pd.DataFrame(records)

    if not df.empty:
        # Set time as index
        df.set_index('time', inplace=True)
        # Sort by index
        df.sort_index(inplace=True)

        print(f"Created DataFrame: {df.shape}")
        print(f"Date range: {df.index.min()} to {df.index.max()}")

    return df

def save_to_local_database(stock_code, period='1m'):
    """
    Save QMT data to local database

    Args:
        stock_code: Stock code like '511380.SH'
        period: Data period
    """
    print("=" * 60)
    print(f"Saving {stock_code} {period} data to local database")
    print("=" * 60)

    # Convert data
    df = convert_xtdata_to_dataframe(stock_code, period)

    if df is None or df.empty:
        print("[ERROR] No data to save")
        return False

    # Initialize local data manager
    print("\nInitializing local data manager...")
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

    # Save data
    print(f"\nSaving data ({data_type})...")
    success, file_size = manager.storage.save_data(df, stock_code, data_type)

    if not success:
        print("[ERROR] Failed to save data")
        manager.close()
        return False

    print(f"[OK] Data saved successfully")
    print(f"  File size: {file_size:.2f} MB")
    print(f"  Records: {len(df)}")

    # Determine symbol type
    if stock_code.endswith('.SH') or stock_code.endswith('.SZ'):
        if stock_code.startswith('5') or stock_code.startswith('15'):
            symbol_type = 'etf'
        else:
            symbol_type = 'stock'
    else:
        symbol_type = 'stock'

    # Update metadata
    print("\nUpdating metadata...")
    manager.metadata.update_data_version(
        symbol=stock_code,
        symbol_type=symbol_type,
        start_date=str(df.index.min().date()),
        end_date=str(df.index.max().date()),
        record_count=len(df),
        file_size=file_size
    )

    manager.close()

    print("\n" + "=" * 60)
    print("Save completed successfully!")
    print("=" * 60)
    print(f"Stock: {stock_code}")
    print(f"Period: {period}")
    print(f"Records: {len(df)}")
    print(f"Date range: {df.index.min().date()} to {df.index.max().date()}")
    print(f"File size: {file_size:.2f} MB")
    print("=" * 60)

    return True

if __name__ == '__main__':
    # Save 1-minute data for 511380.SH
    save_to_local_database('511380.SH', '1m')
