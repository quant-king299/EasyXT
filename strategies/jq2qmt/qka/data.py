import time
from datetime import datetime
from xtquant import xtdata
import numpy as np
from qka.utils.logger import logger

class QMTData:
    def __init__(self, stocks=None, sector=None, indicators=None):
        self.stocks = stocks
        if sector is not None:
            self.stocks = xtdata.get_stock_list_in_sector(sector)
        
        self.indicators = indicators
    
    def get(self, period, start_time='', end_time=''):

        for stock in self.stocks:
            xtdata.download_history_data(stock_code=stock, period=period, start_time=start_time, end_time=end_time, incrementally=True)
        
        res = xtdata.get_local_data(stock_list=self.stocks, period=period, start_time=start_time, end_time=end_time)

        return res
    
    def subscribe(self, callback):

        delays = []

        def task(res):
            for code, item in res.items():
                rate = (item['lastPrice'] - item['lastClose']) / item['lastClose']
                timetag = datetime.fromtimestamp(item['time'] / 1000)
                current_time = datetime.fromtimestamp(time.time())
                delay_seconds = (current_time - timetag).total_seconds()
                if delay_seconds < 1000:

                    # delays.append(delay_seconds)

                    # if len(delays) >= 1_000_000:
                    #     arr = np.array(delays)
                    #     mean = arr.mean()
                    #     delays.clear()
                    #     logger.info(f'平均延迟 {mean}')

                    if delay_seconds > 3:
                        logger.warning(f'{code} 延迟 {delay_seconds}')

                callback(code, item)

        xtdata.subscribe_whole_quote(code_list=self.stocks, callback=task)

        xtdata.run()

def data(stocks=None, sector=None, indicators=None):
    return QMTData(stocks, sector, indicators)
