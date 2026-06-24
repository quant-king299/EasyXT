import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)
#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""

Minute Data Download Tool

Supports 1min, 5min, 15min, 30min, 60min data download

"""



import os

import sys

import argparse

from datetime import datetime, timedelta

import time



project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, project_root)



try:

    from xtquant import xtdata

    logger.info("[OK] Successfully imported xtquant")
except ImportError as e:

    logger.error(f"[ERROR] Failed to import xtquant: {e}")
    sys.exit(1)



PERIOD_MAP = {

    '1m': '1m',

    '5m': '5m',

    '15m': '15m',

    '30m': '30m',

    '60m': '60m',

    '1d': '1d'

}



def download_minute_data(stock_code, period='1m', start_date="", end_date="", force_download=False):

    """Download stock minute data"""

    try:

        logger.info(f"  Downloading {stock_code} {period} data...")


        if not start_date:

            end_date = datetime.now().strftime('%Y%m%d')

            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')

        elif not end_date:

            end_date = datetime.now().strftime('%Y%m%d')



        xtdata.download_history_data(

            stock_code=stock_code,

            period=period,

            start_time=start_date,

            end_time=end_date,

            incrementally=not force_download

        )



        logger.info(f"  [OK] {stock_code} {period} download completed")
        return True



    except Exception as e:

        logger.error(f"  [ERROR] Failed to download {stock_code}: {e}")
        return False



def get_market_data(stock_code, period='1m', count=0):

    """Get downloaded market data"""

    try:

        df = xtdata.get_market_data(

            stock_list=[stock_code],

            period=period,

            count=count

        )

        return df

    except Exception as e:

        logger.error(f"  [ERROR] Failed to get data: {e}")
        return None



def verify_download(stock_code, period='1m'):

    """Verify if data is successfully downloaded"""

    try:

        data = get_market_data(stock_code, period, count=1)



        # xtdata.get_market_data returns a dict {stock_code: DataFrame}

        if data is not None:

            if isinstance(data, dict):

                # Check if any stock has data

                for stock, df in data.items():

                    if df is not None and not df.empty:

                        logger.info(f"  [OK] Verified: {stock_code} {period} data available ({len(df)} records)")
                        return True

            elif hasattr(data, 'empty') and not data.empty:

                logger.info(f"  [OK] Verified: {stock_code} {period} data available")
                return True



        logger.error(f"  [ERROR] Verification failed: {stock_code} {period} data not available")
        return False

    except Exception as e:

        logger.error(f"  [ERROR] Verification error: {e}")
        return False



def download_stocks(stocks, period='1m', start_date="", end_date="", force_download=False, verify=False):

    """Download multiple stocks minute data"""

    logger.info("=" * 60)
    logger.info(f"Minute Data Download Tool - Period: {period}")
    logger.info("=" * 60)


    if start_date:

        logger.info(f"Start Date: {start_date}")
    if end_date:

        logger.info(f"End Date: {end_date}")
    logger.info(f"Force Download: {'Yes' if force_download else 'No'}")
    logger.info(f"Verify Data: {'Yes' if verify else 'No'}")
    print()



    if not stocks:

        logger.error("[ERROR] No stock list specified")
        return



    total_count = len(stocks)

    success_count = 0

    failed_count = 0



    logger.info(f"\nStart downloading {total_count} stocks {period} data...")
    logger.info("-" * 60)


    for i, stock_code in enumerate(stocks, 1):

        try:

            logger.info(f"[{i:4d}/{total_count:4d}] {stock_code}")


            if download_minute_data(stock_code, period, start_date, end_date, force_download):

                success_count += 1



                if verify:

                    verify_download(stock_code, period)

            else:

                failed_count += 1



            if i < total_count:

                time.sleep(0.1)



        except KeyboardInterrupt:

            logger.info("\n\nDownload interrupted by user")
            break

        except Exception as e:

            logger.error(f"  [ERROR] Error processing {stock_code}: {e}")
            failed_count += 1



    logger.info("-" * 60)
    logger.info("Download Statistics:")
    logger.info(f"  Total Stocks: {total_count:4d}")
    logger.info(f"  Successful:   {success_count:4d}")
    logger.info(f"  Failed:       {failed_count:4d}")
    if total_count > 0:

        logger.info(f"  Success Rate: {success_count/total_count*100:.1f}%")
    logger.info("=" * 60)


def main():

    """Main function"""

    parser = argparse.ArgumentParser(description='Minute data download tool')

    parser.add_argument('--stocks', required=True, help='Stock codes separated by comma')

    parser.add_argument('--period', default='1m', choices=['1m', '5m', '15m', '30m', '60m', '1d'],

                        help='Data period (default: 1m)')

    parser.add_argument('--start-date', help='Start date (YYYYMMDD)')

    parser.add_argument('--end-date', help='End date (YYYYMMDD)')

    parser.add_argument('--force', action='store_true', help='Force re-download all data')

    parser.add_argument('--verify', action='store_true', help='Verify data after download')



    args = parser.parse_args()



    # Process stock list

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



    logger.info(f"Stocks to download: {', '.join(stock_list)}")
    logger.info(f"Data period: {args.period}")
    print()



    download_stocks(

        stocks=stock_list,

        period=args.period,

        start_date=args.start_date,

        end_date=args.end_date,

        force_download=args.force,

        verify=args.verify

    )



if __name__ == "__main__":

    main()

