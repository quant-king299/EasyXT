#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Download 10 years of 1-minute data in chunks
分批下载10年1分钟数据
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import time

project_root = Path(__file__).parents[1]
sys.path.insert(0, str(project_root))

from xtquant import xtdata

def download_1m_data_chunks(stock_code, start_year, end_year):
    """
    Download 1-minute data year by year

    Args:
        stock_code: Stock code like '511380.SH'
        start_year: Start year (e.g., 2016)
        end_year: End year (e.g., 2026)
    """
    print("=" * 60)
    print(f"Downloading {stock_code} 1-minute data")
    print(f"Period: {start_year} to {end_year}")
    print("=" * 60)

    total_years = end_year - start_year
    success_count = 0
    failed_years = []

    for year in range(start_year, end_year):
        try:
            year_start = f"{year}0101"
            year_end = f"{year}1231"

            print(f"\n[{year-start_year+1}/{total_years}] Downloading {year}...")
            print(f"  Period: {year_start} - {year_end}")

            # Download data for this year
            xtdata.download_history_data(
                stock_code=stock_code,
                period='1m',
                start_time=year_start,
                end_time=year_end
            )

            print(f"  [OK] {year} download completed")
            success_count += 1

            # Add delay to avoid overwhelming the server
            time.sleep(1)

        except Exception as e:
            print(f"  [ERROR] Failed to download {year}: {e}")
            failed_years.append(year)
            continue

    # Summary
    print("\n" + "=" * 60)
    print("Download Summary:")
    print(f"  Total years: {total_years}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {len(failed_years)}")

    if failed_years:
        print(f"  Failed years: {failed_years}")

    print("=" * 60)

    # Verify total data
    print("\nVerifying total data...")
    data = xtdata.get_market_data(
        stock_list=[stock_code],
        period='1m',
        count=0
    )

    if data and 'time' in data:
        time_df = data['time']
        total_records = len(time_df.columns)
        print(f"Total 1-minute records: {total_records:,}")

        # Estimate coverage
        estimated_days = total_records / 240
        estimated_years = estimated_days / 250
        print(f"Estimated coverage: ~{estimated_years:.1f} years")

if __name__ == '__main__':
    # Download 10 years: 2016 to 2026
    download_1m_data_chunks('511380.SH', 2016, 2026)
