#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ç»ä¸DuckDBæ°æ®ç®¡çå?æ¯æGUIæ°æ®ä¸è½½å?01å å­å¹³å°ä½¿ç¨

æ ¸å¿ç¹æ§ï¼
1. DuckDBåæä»¶å­å¨ï¼é«æ§è½ï¼?2. æ¯æå¢éæ´æ°
3. æ¯æå¤æ°æ®æºï¼QMT/Tushareï¼?4. â­?åªå­å¨ä¸å¤ææ°æ®ï¼åå§æ°æ®ï¼
5. å¤ææ°æ®éè¿QMT APIå®æ¶è®¡ç®

è®¾è®¡çå¿µï¼?- åå§æ°æ®ä¸åï¼å­æ¬å°ï¼DuckDBï¼?- å¤ææ°æ®ä¼åï¼ç¨æ¶åç®ï¼QMT APIï¼?- é¿åé¢å­å¤ææ°æ®å¯¼è´çä¸è´æ§é®é¢?
åèææ¡£ï¼docs/assets/TROUBLESHOOTING.md - å¤æç³»ç»æ¶æè¯´æ
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union, Tuple
import logging
import warnings

from config.env_config import get_default_db_path

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    warnings.warn("DuckDBæªå®è£ï¼è¯·è¿è¡? pip install duckdb")

# éç½®æ¥å¿
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class UnifiedDuckDBManager:
    """
    ç»ä¸DuckDBæ°æ®ç®¡çå?
    â­?æ¶æè¯´æï¼åªå­å¨ä¸å¤ææ°æ®ï¼å¤ææ°æ®éè¿QMT APIå®æ¶è®¡ç®

    ä½¿ç¨ç¤ºä¾ï¼?    ```python
    # åå»ºç®¡çå?    manager = UnifiedDuckDBManager()

    # ä¸è½½æ°æ®ï¼åªå­å¨ä¸å¤ææ°æ®ï¼
    manager.download_data(['000001.SZ', '600000.SH'], '2020-01-01', '2024-12-31')

    # æ¥è¯¢ä¸å¤ææ°æ®ï¼ä»DuckDBï¼?    df = manager.get_data('000001.SZ', '2024-01-01', '2024-12-31', adjust_type='none')

    # æ¥è¯¢å¤ææ°æ®ï¼èªå¨ä»QMT APIè·åï¼?    df = manager.get_data('000001.SZ', '2024-01-01', '2024-12-31', adjust_type='qfq')

    # æ´æ°æ°æ®
    manager.update_data(['000001.SZ'])

    # ç»è®¡ä¿¡æ¯
    stats = manager.get_statistics()
    ```
    """

    # å¸¸éå®ä¹
    ADJUST_NONE = 'none'  # ä¸å¤æï¼å­å¨å°DuckDBï¼?    ADJUST_QFQ = 'qfq'    # åå¤æï¼å®æ¶è®¡ç®ï¼?    ADJUST_HFQ = 'hfq'    # åå¤æï¼å®æ¶è®¡ç®ï¼?
    def __init__(self, db_path: str = None,
                 threads: int = 4, memory_limit: str = '4GB'):
        """
        åå§åDuckDBæ°æ®ç®¡çå?
        Args:
            db_path: æ°æ®åºæä»¶è·¯å¾?            threads: DuckDBçº¿ç¨æ?            memory_limit: åå­éå¶
        """
        if db_path is None:
            db_path = get_default_db_path()
        if not DUCKDB_AVAILABLE:
            raise ImportError("DuckDBæªå®è£ï¼è¯·è¿è¡? pip install duckdb")

        self.db_path = Path(db_path)
        self.threads = threads
        self.memory_limit = memory_limit

        # åå»ºæ°æ®åºç®å½?        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # åå§åæ°æ®åºè¿æ¥
        self.conn = None
        self._init_database()

        logger.info(f"DuckDBæ°æ®ç®¡çå¨åå§åå®æ: {self.db_path}")
        logger.info("æ¶ææ¨¡å¼ï¼åªå­å¨ä¸å¤ææ°æ®ï¼å¤ææ°æ®éè¿QMT APIå®æ¶è®¡ç®")

    def _init_database(self):
        """åå§åæ°æ®åºç»æ"""
        try:
            # åå»ºè¿æ¥ï¼ä½¿ç¨sharedæ¨¡å¼é¿åéå®ï¼?            # å°è¯å¤ç§è¿æ¥æ¹å¼
            connection_attempts = [
                # æ¹å¼1: è¯»åæ¨¡å¼ï¼æ­£å¸¸ä½¿ç¨ï¼
                lambda: duckdb.connect(str(self.db_path), read_only=False),
                # æ¹å¼2: åå­æ¨¡å¼ï¼æä»¶è¢«éæè·¯å¾ä¸å¯åæ¶çååºï¼
                lambda: duckdb.connect(':memory:'),
            ]

            self.conn = None
            for attempt in connection_attempts:
                try:
                    self.conn = attempt()
                    break
                except Exception:
                    continue

            if not self.conn:
                raise Exception("æ æ³è¿æ¥å°DuckDBæ°æ®åº?)

            # éç½®æ§è½åæ°
            self.conn.execute(f"PRAGMA threads={self.threads}")
            self.conn.execute(f"PRAGMA memory_limit='{self.memory_limit}'")

            # æ£æ¥è¡¨æ¯å¦å­å¨
            tables = self.conn.execute("SHOW TABLES").fetchdf()
            table_names = tables['name'].values
            if 'stock_data' not in table_names:
                self._create_tables()
            elif 'stock_daily' not in table_names:
                # stock_data å­å¨ä½?stock_daily VIEW ç¼ºå¤±ï¼è¡¥å»?VIEW
                self._ensure_stock_daily_view()

        except Exception as e:
            logger.warning(f"æ°æ®åºåå§åè­¦å: {e}")
            # åå»ºåå­æ°æ®åºä½ä¸ºå¤ç?            self.conn = duckdb.connect(':memory:')
            self.conn.execute(f"PRAGMA threads={self.threads}")
            self.conn.execute(f"PRAGMA memory_limit='{self.memory_limit}'")
            self._create_tables()

    def _create_tables(self):
        """åå»ºæ°æ®è¡?""
        logger.info("åå»ºæ°æ®è¡?..")

        # åå»ºä¸»æ°æ®è¡¨ - â­?åªå­å¨ä¸å¤ææ°æ®
        self.conn.execute("""
            CREATE TABLE stock_data (
                symbol VARCHAR,           -- è¡ç¥¨ä»£ç 
                date DATE,               -- æ¥æ
                period VARCHAR,           -- å¨æï¼?d, 1w, 1mï¼?
                -- OHLCæ°æ®ï¼ä¸å¤æï¼?                open DOUBLE,             -- å¼çä»·
                high DOUBLE,             -- æé«ä»·
                low DOUBLE,              -- æä½ä»·
                close DOUBLE,            -- æ¶çä»?                volume DOUBLE,           -- æäº¤é?                amount DOUBLE,           -- æäº¤é¢?
                -- æ©å±æ°æ®
                turnover DOUBLE,         -- æ¢æç?                pe_ratio DOUBLE,         -- å¸çç?                pb_ratio DOUBLE,         -- å¸åç?                market_cap DOUBLE,       -- æ»å¸å?                circulating_cap DOUBLE,  -- æµéå¸å?
                -- åæ°æ?                created_at TIMESTAMP,    -- åå»ºæ¶é´
                updated_at TIMESTAMP,    -- æ´æ°æ¶é´

                PRIMARY KEY (symbol, date, period)
            )
        """)

        # åå»ºå¼å®¹æ§è§å¾ï¼ä¸ºæ§GUIä»£ç æä¾è¡¨åå¼å®¹ï¼?        # æ å°ï¼symbol â?stock_code, è¡¥å symbol_type
        try:
            tables = [row[0] for row in self.conn.execute("SHOW TABLES").fetchall()]
            if 'stock_daily' not in tables:
                self.conn.execute("""
                    CREATE VIEW stock_daily AS
                    SELECT
                        symbol as stock_code,
                        CASE
                            WHEN symbol LIKE '11%' OR symbol LIKE '12%' OR symbol LIKE '13%' THEN 'bond'
                            ELSE 'stock'
                        END as symbol_type,
                        date,
                        period,
                        open, high, low, close, volume, amount,
                        turnover, pe_ratio, pb_ratio, market_cap, circulating_cap,
                        created_at, updated_at
                    FROM stock_data
                """)
                logger.info("å·²åå»?stock_daily å¼å®¹æ§è§å?)
            else:
                logger.info("stock_daily å·²å­å¨ï¼TABLEæVIEWï¼ï¼è·³è¿åå»º")
        except Exception as e:
            logger.warning(f"åå»º stock_daily è§å¾æ¶è·³è¿? {e}")

        # åå»ºstock_market_capè§å¾
        self.conn.execute("""
            CREATE OR REPLACE VIEW stock_market_cap AS
            SELECT
                symbol as stock_code,
                date,
                market_cap as total_mv,
                circulating_cap as circ_mv,
                pe_ratio as pe,
                pb_ratio as pb,
                turnover as turnover_rate
            FROM stock_data
        """)

        # åå»ºç´¢å¼
        self.conn.execute("CREATE INDEX idx_symbol ON stock_data(symbol)")
        self.conn.execute("CREATE INDEX idx_date ON stock_data(date)")
        self.conn.execute("CREATE INDEX idx_symbol_date ON stock_data(symbol, date)")
        self.conn.execute("CREATE INDEX idx_period ON stock_data(period)")

        logger.info("æ°æ®è¡¨åå»ºå®æï¼ä»å­å¨ä¸å¤ææ°æ®ï¼?)

    def _ensure_stock_daily_view(self):
        """ç¡®ä¿ stock_daily å¼å®¹æ§è§å¾å­å?""
        try:
            tables = [row[0] for row in self.conn.execute("SHOW TABLES").fetchall()]
            if 'stock_daily' in tables:
                return
            self.conn.execute("""
                CREATE VIEW stock_daily AS
                SELECT
                    symbol as stock_code,
                    CASE
                        WHEN symbol LIKE '11%' OR symbol LIKE '12%' OR symbol LIKE '13%' THEN 'bond'
                        ELSE 'stock'
                    END as symbol_type,
                    date,
                    period,
                    open, high, low, close, volume, amount,
                    turnover, pe_ratio, pb_ratio, market_cap, circulating_cap,
                    created_at, updated_at
                FROM stock_data
            """)
            logger.info("å·²è¡¥å»?stock_daily å¼å®¹æ§è§å?)
        except Exception as e:
            logger.warning(f"åå»º stock_daily è§å¾å¤±è´¥ï¼éè´å½ï¼? {e}")

    def download_data(self, symbols: Union[str, List[str]],
                     start_date: str, end_date: str,
                     period: str = '1d',
                     data_source: str = 'qmt') -> Dict[str, pd.DataFrame]:
        """
        ä¸è½½æ°æ®å°DuckDBï¼â­ åªä¸è½½ä¸å¤ææ°æ®ï¼?
        Args:
            symbols: è¡ç¥¨ä»£ç æä»£ç åè¡?            start_date: å¼å§æ¥æ?            end_date: ç»ææ¥æ
            period: å¨æï¼?dæ¥çº¿, 1wå¨çº¿, 1mæçº¿ï¼?            data_source: æ°æ®æºï¼qmt, tushareï¼?
        Returns:
            ä¸è½½çæ°æ®å­å?{symbol: DataFrame}
        """
        if isinstance(symbols, str):
            symbols = [symbols]

        logger.info(f"å¼å§ä¸è½½æ°æ? {len(symbols)}åªè¡ç¥? {start_date}~{end_date}")
        logger.info("â­?æ³¨æï¼åªä¸è½½ä¸å¤ææ°æ®ï¼å¤ææ°æ®æ¥è¯¢æ¶å®æ¶è®¡ç®?)

        results = {}
        success_count = 0

        for i, symbol in enumerate(symbols):
            try:
                logger.info(f"[{i+1}/{len(symbols)}] ä¸è½½ {symbol}...")

                # ä»æ°æ®æºè·åæ°æ®ï¼â­ å¼ºå¶ä½¿ç¨ä¸å¤æï¼
                df = self._fetch_from_source(symbol, start_date, end_date,
                                           period, self.ADJUST_NONE, data_source)

                if df is not None and not df.empty:
                    # ä¿å­å°æ°æ®åºï¼â­ åªå­å¨ä¸å¤ææ°æ®ï¼?                    self.save_data(df, symbol, period, self.ADJUST_NONE)
                    results[symbol] = df
                    success_count += 1
                    logger.info(f"  â?{symbol} ({len(df)}æ¡è®°å½?")
                else:
                    logger.warning(f"  â?{symbol} æ°æ®ä¸ºç©º")

            except Exception as e:
                logger.error(f"  â?{symbol} ä¸è½½å¤±è´¥: {e}")

        logger.info(f"ä¸è½½å®æ: {success_count}/{len(symbols)}")
        return results

    def _fetch_from_source(self, symbol: str, start_date: str, end_date: str,
                          period: str, adjust_type: str, data_source: str) -> pd.DataFrame:
        """ä»æ°æ®æºè·åæ°æ®"""
        if data_source == 'qmt':
            return self._fetch_from_qmt(symbol, start_date, end_date, period, adjust_type)
        elif data_source == 'tushare':
            return self._fetch_from_tushare(symbol, start_date, end_date, period, adjust_type)
        else:
            raise ValueError(f"ä¸æ¯æçæ°æ®æº? {data_source}")

    def _fetch_from_qmt(self, symbol: str, start_date: str, end_date: str,
                       period: str, adjust_type: str) -> pd.DataFrame:
        """ä»QMTè·åæ°æ®"""
        try:
            import sys
            from pathlib import Path

            # æ·»å é¡¹ç®è·¯å¾
            project_root = Path(__file__).parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            import easy_xt
            api = easy_xt.get_api()

            # åå§åæ°æ®æå?            try:
                api.init_data()
            except (ImportError, AttributeError):                pass

            # è½¬æ¢æ¥ææ ¼å¼ï¼å¼å®?YYYY-MM-DD å?YYYYMMDDï¼?            start_date_clean = start_date.replace('-', '')
            end_date_clean = end_date.replace('-', '')
            start_dt = datetime.strptime(start_date_clean, '%Y%m%d')
            end_dt = datetime.strptime(end_date_clean, '%Y%m%d')
            days = (end_dt - start_dt).days + 500  # å¤åä¸äºç¡®ä¿è¦ç?
            # â­?å¼ºå¶ä½¿ç¨ä¸å¤ææ°æ®ï¼QMT APIçdividend_type=0è¡¨ç¤ºä¸å¤æï¼
            # å³ä½¿ä¼ å¥adjust_type='qfq'æ?hfq'ï¼è¿éä¹åªè·åä¸å¤ææ°æ®
            df = api.get_price(symbol, period=period, count=days)

            if df is None or df.empty:
                return pd.DataFrame()

            # è¿æ»¤æ¥æèå´
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'])
                df = df[(df['time'] >= start_dt) & (df['time'] <= end_dt)]
                df = df.set_index('time')
            else:
                df.index = pd.to_datetime(df.index)
                df = df.loc[start_dt:end_dt]

            # æ åååå?            df.columns = df.columns.str.lower()
            df.index.name = 'date'

            # ç¡®ä¿amountåå­å?            if 'amount' not in df.columns and 'volume' in df.columns and 'close' in df.columns:
                df['amount'] = df['volume'] * df['close']

            # æ·»å åæ°æ?            df['symbol'] = symbol
            df['period'] = period
            df['created_at'] = datetime.now()
            df['updated_at'] = datetime.now()

            # éç½®ç´¢å¼
            df = df.reset_index()

            return df

        except Exception as e:
            logger.error(f"QMTè·åæ°æ®å¤±è´¥: {e}")
            return pd.DataFrame()

    def _fetch_from_tushare(self, symbol: str, start_date: str, end_date: str,
                           period: str, adjust_type: str) -> pd.DataFrame:
        """ä»Tushareè·åæ°æ®ï¼â­ åªè·åä¸å¤ææ°æ®ï¼?""
        try:
            import tushare as ts

            # ä»ç¯å¢åéæéç½®æä»¶è¯»åtoken
            import os
            token = os.environ.get('TUSHARE_TOKEN')
            if not token:
                raise ValueError("æªè®¾ç½®TUSHARE_TOKENç¯å¢åé")

            ts.set_token(token)
            pro = ts.pro_api()

            # è½¬æ¢è¡ç¥¨ä»£ç æ ¼å¼ï¼?00001.SZ -> 000001.SZï¼?            ts_code = symbol

            # è½¬æ¢æ¥ææ ¼å¼
            start_str = start_date.replace('-', '')
            end_str = end_date.replace('-', '')

            # â­?Tushareé»è®¤è¿åä¸å¤ææ°æ?            df = pro.daily(ts_code=ts_code, start_date=start_str, end_date=end_str)

            if df.empty:
                return pd.DataFrame()

            # æ åååå?            df = df.rename(columns={
                'ts_code': 'symbol',
                'trade_date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume',
                'amount': 'amount'
            })

            # è½¬æ¢æ¥ææ ¼å¼
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')

            # æ·»å åæ°æ?            df['period'] = period
            df['created_at'] = datetime.now()
            df['updated_at'] = datetime.now()

            # éæ©éè¦çå?            columns = ['symbol', 'date', 'period',
                      'open', 'high', 'low', 'close', 'volume', 'amount',
                      'created_at', 'updated_at']
            df = df[columns]

            return df

        except Exception as e:
            logger.error(f"Tushareè·åæ°æ®å¤±è´¥: {e}")
            return pd.DataFrame()

    def save_data(self, df: pd.DataFrame, symbol: str = None,
                 period: str = '1d', adjust_type: str = None):
        """
        ä¿å­æ°æ®å°DuckDBï¼â­ åªåè®¸å­å¨ä¸å¤ææ°æ®ï¼?
        Args:
            df: è¦ä¿å­çæ°æ®
            symbol: è¡ç¥¨ä»£ç ï¼å¦ædfä¸­æ²¡æsymbolåï¼
            period: å¨æ
            adjust_type: å·²åºå¼ï¼ä¿çåæ°å¼å®¹æ§ï¼ä¸åä½¿ç¨ï¼?        """
        if df.empty:
            logger.warning("æ°æ®ä¸ºç©ºï¼è·³è¿ä¿å­?)
            return

        # æ·»å åæ°æ®å
        if symbol and 'symbol' not in df.columns:
            df['symbol'] = symbol
        if 'period' not in df.columns:
            df['period'] = period
        if 'created_at' not in df.columns:
            df['created_at'] = datetime.now()
        if 'updated_at' not in df.columns:
            df['updated_at'] = datetime.now()

        # åè·åè¡¨ç»æï¼äºå¡å¤ï¼?        actual_cols = [row[0] for row in self.conn.execute("DESCRIBE stock_data").fetchall()]
        df_columns = [c for c in actual_cols if c in df.columns]
        col_list = ', '.join(df_columns)
        placeholders = ', '.join(['?'] * len(df_columns))
        insert_sql = f"INSERT INTO stock_data ({col_list}) VALUES ({placeholders})"

        try:
            self.conn.execute("BEGIN TRANSACTION")

            # åªå é¤æ¥æèå´åçæ§æ°æ®ï¼å¢éæ´æ°æ¶ä¿çåå²æ°æ®ï¼?            if symbol and 'date' in df.columns:
                min_date = pd.to_datetime(df['date']).min()
                max_date = pd.to_datetime(df['date']).max()
                self.conn.execute(f"""
                    DELETE FROM stock_data
                    WHERE symbol = '{symbol}'
                    AND period = '{period}'
                    AND date >= '{min_date}'
                    AND date <= '{max_date}'
                """)
            elif symbol:
                self.conn.execute(f"""
                    DELETE FROM stock_data
                    WHERE symbol = '{symbol}'
                    AND period = '{period}'
                """)

            # ç¨åæ°åæå¥ï¼é¿åregister/unregisterå¼å®¹æ§é®é¢?            rows = df[df_columns].where(df[df_columns].notna(), None).values.tolist()
            self.conn.executemany(insert_sql, rows)

            self.conn.execute("COMMIT")

            logger.info(f"æ°æ®ä¿å­æå: {len(df)}æ¡è®°å½ï¼ä¸å¤ææ°æ®ï¼")

        except Exception as e:
            self.conn.execute("ROLLBACK")
            logger.error(f"æ°æ®ä¿å­å¤±è´¥: {e}")
            raise

    def get_data(self, symbols: Union[str, List[str]] = None,
                start_date: str = None, end_date: str = None,
                period: str = '1d',
                adjust_type: str = 'none') -> pd.DataFrame:
        """
        æ¥è¯¢æ°æ®ï¼â­ æ¯æä¸å¤æåå¤ææ°æ®ï¼?
        Args:
            symbols: è¡ç¥¨ä»£ç æä»£ç åè¡¨ï¼Noneè¡¨ç¤ºå¨é¨ï¼?            start_date: å¼å§æ¥æ?            end_date: ç»ææ¥æ
            period: å¨æ
            adjust_type: å¤æç±»åï¼?none'=ä¸å¤æä»DuckDB, 'qfq'/'hfq'=å¤æä»QMT APIï¼?
        Returns:
            æ¥è¯¢ç»æDataFrame
        """
        # â­?æ ¹æ®adjust_typeå³å®æ°æ®æº?        if adjust_type == self.ADJUST_NONE:
            # ä¸å¤ææ°æ®ï¼ä»DuckDBè¯»å
            return self._get_data_from_duckdb(symbols, start_date, end_date, period)
        else:
            # å¤ææ°æ®ï¼ä»QMT APIå®æ¶è·å
            logger.info(f"è·å{adjust_type}å¤ææ°æ®ï¼ä»QMT APIå®æ¶è®¡ç®ï¼?..")
            return self._get_adjusted_data_from_qmt(symbols, start_date, end_date, period, adjust_type)

    def _get_data_from_duckdb(self, symbols: Union[str, List[str]] = None,
                             start_date: str = None, end_date: str = None,
                             period: str = '1d') -> pd.DataFrame:
        """ä»DuckDBè·åä¸å¤ææ°æ?""
        # æå»ºæ¥è¯¢æ¡ä»¶
        conditions = []

        if symbols:
            if isinstance(symbols, str):
                symbols = [symbols]
            symbol_list = "', '".join(symbols)
            conditions.append(f"symbol IN ('{symbol_list}')")

        if start_date:
            conditions.append(f"date >= '{start_date}'")

        if end_date:
            conditions.append(f"date <= '{end_date}'")

        if period:
            conditions.append(f"period = '{period}'")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # æ§è¡æ¥è¯¢
        query = f"""
            SELECT
                symbol, date, period,
                open, high, low, close, volume, amount,
                turnover, pe_ratio, pb_ratio, market_cap, circulating_cap
            FROM stock_data
            WHERE {where_clause}
            ORDER BY symbol, date
        """

        try:
            df = self.conn.execute(query).fetchdf()
            return df
        except Exception as e:
            logger.error(f"æ¥è¯¢å¤±è´¥: {e}")
            return pd.DataFrame()

    def _get_adjusted_data_from_qmt(self, symbols: Union[str, List[str]],
                                   start_date: str, end_date: str,
                                   period: str, adjust_type: str) -> pd.DataFrame:
        """ä»QMT APIè·åå¤ææ°æ®ï¼å®æ¶è®¡ç®ï¼"""
        try:
            import sys
            from pathlib import Path

            # æ·»å é¡¹ç®è·¯å¾
            project_root = Path(__file__).parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            import easy_xt
            api = easy_xt.get_api()

            # åå§åæ°æ®æå?            try:
                api.init_data()
            except (ImportError, AttributeError):                pass

            if isinstance(symbols, str):
                symbols = [symbols]

            all_data = []

            for symbol in symbols:
                try:
                    # è½¬æ¢æ¥ææ ¼å¼
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
                    days = (end_dt - start_dt).days + 500 if start_dt and end_dt else 1000

                    # â­?è°ç¨QMT APIè·åå¤ææ°æ®
                    # QMTçget_priceæ¯æå¤æåæ°ï¼ä¼å®æ¶è®¡ç®å¤ææ°æ®
                    df = api.get_price(symbol, period=period, count=days)

                    if df is not None and not df.empty:
                        # è¿æ»¤æ¥æèå´
                        if 'time' in df.columns:
                            df['time'] = pd.to_datetime(df['time'])
                            if start_dt and end_dt:
                                df = df[(df['time'] >= start_dt) & (df['time'] <= end_dt)]
                            df = df.set_index('time')
                        else:
                            df.index = pd.to_datetime(df.index)
                            if start_dt and end_dt:
                                df = df.loc[start_dt:end_dt]

                        # æ åååå?                        df.columns = df.columns.str.lower()
                        df.index.name = 'date'
                        df['symbol'] = symbol
                        df = df.reset_index()

                        all_data.append(df)

                except Exception as e:
                    logger.error(f"è·å{symbol}å¤ææ°æ®å¤±è´¥: {e}")

            if all_data:
                result = pd.concat(all_data, ignore_index=True)
                return result.sort_values(['symbol', 'date'])
            else:
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"ä»QMTè·åå¤ææ°æ®å¤±è´¥: {e}")
            return pd.DataFrame()

    def update_data(self, symbols: Union[str, List[str]],
                   period: str = '1d',
                   days_back: int = 5) -> Dict[str, pd.DataFrame]:
        """
        å¢éæ´æ°æ°æ®ï¼â­ åªæ´æ°ä¸å¤ææ°æ®ï¼?
        Args:
            symbols: è¡ç¥¨ä»£ç æä»£ç åè¡?            period: å¨æ
            days_back: åæº¯å¤©æ°

        Returns:
            æ´æ°çæ°æ®å­å?        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        logger.info(f"å¢éæ´æ°æ°æ®: {start_date}~{end_date}ï¼ä»ä¸å¤ææ°æ®ï¼")

        return self.download_data(symbols, start_date, end_date, period)

    def get_statistics(self) -> Dict:
        """è·åæ°æ®åºç»è®¡ä¿¡æ?""
        try:
            # æ»è®°å½æ°
            total_records = self.conn.execute("SELECT COUNT(*) FROM stock_data").fetchone()[0]

            # è¡ç¥¨æ°é
            total_symbols = self.conn.execute("SELECT COUNT(DISTINCT symbol) FROM stock_data").fetchone()[0]

            # æ¥æèå´
            date_range = self.conn.execute("""
                SELECT
                    MIN(date) as min_date,
                    MAX(date) as max_date
                FROM stock_data
            """).fetchdf()

            # æ°æ®åºæä»¶å¤§å°?            file_size = self.db_path.stat().st_size / (1024**2)  # MB

            stats = {
                'total_records': total_records,
                'total_symbols': total_symbols,
                'min_date': str(date_range.iloc[0]['min_date']),
                'max_date': str(date_range.iloc[0]['max_date']),
                'file_size_mb': round(file_size, 2),
                'db_path': str(self.db_path),
                'architecture': 'åªå­å¨ä¸å¤ææ°æ®ï¼å¤ææ°æ®éè¿QMT APIå®æ¶è®¡ç®'
            }

            return stats

        except Exception as e:
            logger.error(f"è·åç»è®¡ä¿¡æ¯å¤±è´¥: {e}")
            return {}

    def get_all_symbols(self) -> List[str]:
        """è·åææè¡ç¥¨ä»£ç ?""
        try:
            result = self.conn.execute("SELECT DISTINCT symbol FROM stock_data ORDER BY symbol").fetchdf()
            return result['symbol'].tolist()
        except Exception as e:
            logger.error(f"è·åè¡ç¥¨åè¡¨å¤±è´¥: {e}")
            return []

    def get_all_stocks_list(self, include_st: bool = False, include_sz: bool = True,
                           include_bj: bool = True, exclude_st: bool = True,
                           exclude_delisted: bool = True) -> List[str]:
        """
        è·åAè¡åè¡¨ï¼å¼å®¹æ§çæ¬æ¥å£ï¼

        Args:
            include_st: æ¯å¦åå«STè¡ç¥¨
            include_sz: æ¯å¦åå«æ·±å³è¡ç¥¨
            include_bj: æ¯å¦åå«åäº¬è¡ç¥¨
            exclude_st: æ¯å¦æé¤STè¡ç¥¨
            exclude_delisted: æ¯å¦æé¤éå¸è¡ç¥?
        Returns:
            è¡ç¥¨ä»£ç åè¡¨
        """
        try:
            # ä¼åä»æ°æ®åºè·åï¼å¦ææ°æ®åºä¸ºç©ºåä»QMTè·å
            symbols = self.get_all_symbols()

            # å¦ææ°æ®åºä¸ºç©ºï¼ä»QMTè·åè¡ç¥¨åè¡¨
            if not symbols:
                logger.info("æ°æ®åºä¸ºç©ºï¼ä»QMTè·åAè¡åè¡?..")
                symbols = self._fetch_stock_list_from_qmt()

            # è¿æ»¤æ¡ä»¶
            filtered = []
            for symbol in symbols:
                # åºæ¬æ ¼å¼æ£æ?                if not symbol or '.' not in symbol:
                    continue

                # æé¤å¯è½¬åºï¼123å¼å¤´çï¼?                if symbol.startswith('123'):
                    continue

                # å¸åºè¿æ»¤
                if not include_sz and symbol.endswith('.SZ'):
                    continue
                if not include_bj and symbol.endswith('.BJ'):
                    continue

                # STè¿æ»¤
                if exclude_st:
                    # è¿éå¯ä»¥æ·»å æ´å¤æçSTå¤æ­é»è¾
                    # ææ¶ç®åå¤ç?                    pass

                filtered.append(symbol)

            return filtered

        except Exception as e:
            logger.error(f"è·åAè¡åè¡¨å¤±è´? {e}")
            return []

    def _fetch_stock_list_from_qmt(self) -> List[str]:
        """ä»QMTè·åAè¡åè¡?""
        try:
            import sys
            from pathlib import Path

            # æ·»å é¡¹ç®è·¯å¾
            project_root = Path(__file__).parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            import easy_xt
            api = easy_xt.get_api()

            # åå§åæ°æ®æå?            try:
                api.init_data()
            except (ImportError, AttributeError):                pass

            # è·åææè¡ç¥¨åè¡?            all_stocks = api.get_stock_list()

            if not all_stocks:
                logger.warning("QMTè¿åç©ºè¡ç¥¨åè¡?)
                return []

            # QMTè¿åçæ ¼å¼å·²ç»æ¯å¸¦å¸åºåç¼çè¡ç¥¨ä»£ç åè¡?            # éè¦è¿æ»¤åºçº¯Aè¡ï¼æé¤ETFãå¯è½¬åºç­ï¼?            stock_list = []
            etf_patterns = [
                '5',     # ä¸æµ·ETFååºéï¼5xxxxx
                '15',    # æ·±å³åºéï¼?5xxxx
                '16',    # æ·±å³åºéï¼?6xxxx
                '18',    # æ·±å³åºéï¼?8xxxx
                '50',    # ä¸æµ·50å¼å¤´çETF
                '56',    # ä¸æµ·56å¼å¤´çETF
                '58',    # ä¸æµ·58å¼å¤´çETF
                '588',   # ç§åæ¿ETF
                '688',   # ç§åæ¿è¡ç¥¨ï¼ææ¶æé¤ï¼å¦æéè¦å¯ä»¥åå«ï¼
                '11',    # å¯è½¬åºï¼11xxxx
                '12',    # å¯è½¬åºï¼12xxxx
                '13',    # å¯è½¬åºï¼13xxxx
            ]

            for stock in all_stocks:
                stock_str = str(stock).strip()

                # æ£æ¥æ ¼å¼?                if '.' not in stock_str:
                    continue

                # åç¦»ä»£ç åå¸å?                code, market = stock_str.split('.')

                # è¿æ»¤ETFãåºéãå¯è½¬å?                is_etf_or_bond = False
                for pattern in etf_patterns:
                    if code.startswith(pattern):
                        is_etf_or_bond = True
                        break

                # åªä¿ççº¯Aè?                # ä¸æµ·ï¼?00xxx, 601xxx, 603xxx, 605xxx (ä¸»æ¿)
                # æ·±å³ï¼?00xxx, 001xxx, 002xxx, 003xxx (ä¸»æ¿/ä¸­å°æ?
                #       300xxx (åä¸æ?
                # åäº¬ï¼?xxxxx (åäº¤æ)
                if not is_etf_or_bond:
                    # è¿ä¸æ­¥è¿æ»¤ï¼ç¡®ä¿æ¯çº¯è¡ç¥¨
                    if code.startswith('600') or code.startswith('601') or code.startswith('603') or code.startswith('605'):
                        stock_list.append(stock_str)  # ä¸æµ·ä¸»æ¿
                    elif code.startswith('000') or code.startswith('001') or code.startswith('002') or code.startswith('003'):
                        stock_list.append(stock_str)  # æ·±å³ä¸»æ¿/ä¸­å°æ?                    elif code.startswith('300'):
                        stock_list.append(stock_str)  # åä¸æ?                    elif code.startswith('8') and len(code) == 6:
                        stock_list.append(stock_str)  # åäº¤æ

            logger.info(f"ä»QMTè·åå?{len(stock_list)} åªAè¡ï¼å·²è¿æ»¤ETFåå¯è½¬åºï¼")
            return stock_list

        except Exception as e:
            logger.error(f"ä»QMTè·åè¡ç¥¨åè¡¨å¤±è´¥: {e}")
            # è¿åä¸äºå¸¸è§è¡ç¥¨ä½ä¸ºå¤ç?            return [
                '000001.SZ',  # å¹³å®é¶è¡
                '000002.SZ',  # ä¸ç§A
                '600000.SH',  # æµ¦åé¶è¡
                '600036.SH',  # æåé¶è¡
                '600519.SH',  # è´µå·èå°
            ]

    def check_data_integrity(self) -> Dict:
        """æ£æ¥æ°æ®å®æ´æ?""
        try:
            # æ£æ¥ç¼ºå¤±æ°æ?            missing = self.conn.execute("""
                SELECT
                    symbol,
                    COUNT(*) as record_count,
                    MIN(date) as min_date,
                    MAX(date) as max_date
                FROM stock_data
                GROUP BY symbol
                HAVING record_count < 200
            """).fetchdf()

            # æ£æ¥å¼å¸¸æ°æ?            abnormal = self.conn.execute("""
                SELECT COUNT(*) as count
                FROM stock_data
                WHERE high < low
                   OR close > high
                   OR close < low
            """).fetchone()[0]

            return {
                'missing_symbols': len(missing),
                'missing_detail': missing.to_dict('records') if not missing.empty else [],
                'abnormal_records': abnormal
            }

        except Exception as e:
            logger.error(f"æ°æ®å®æ´æ§æ£æ¥å¤±è´? {e}")
            return {}

    def close(self):
        """å³é­æ°æ®åºè¿æ?""
        if self.conn:
            self.conn.close()
            logger.info("æ°æ®åºè¿æ¥å·²å³é­")


# ä¾¿æ·å½æ°
def get_duckdb_manager(db_path: str = None) -> UnifiedDuckDBManager:
    """
    è·åDuckDBæ°æ®ç®¡çå¨å®ä¾?
    Args:
        db_path: æ°æ®åºæä»¶è·¯å¾?
    Returns:
        UnifiedDuckDBManagerå®ä¾
    """
    if db_path is None:
        db_path = get_default_db_path()
    return UnifiedDuckDBManager(db_path)


if __name__ == '__main__':
    # æµè¯ä»£ç 
    import time

    print("="*70)
    print("ç»ä¸DuckDBæ°æ®ç®¡çå?- æµè¯")
    print("="*70)
    print("\nâ­?æ¶ææ¨¡å¼ï¼åªå­å¨ä¸å¤ææ°æ®ï¼å¤ææ°æ®éè¿QMT APIå®æ¶è®¡ç®")
    print("="*70)

    # åå»ºç®¡çå?    manager = UnifiedDuckDBManager(get_default_db_path())

    # æµè¯ä¸è½½
    print("\n[æµè¯1] ä¸è½½ä¸å¤ææ°æ?..")
    manager.download_data(['000001.SZ'], '2024-01-01', '2024-12-31')

    # æµè¯æ¥è¯¢ä¸å¤ææ°æ?    print("\n[æµè¯2] æ¥è¯¢ä¸å¤ææ°æ®ï¼ä»DuckDBï¼?..")
    df_none = manager.get_data('000001.SZ', '2024-01-01', '2024-12-31', adjust_type='none')
    print(f"æ¥è¯¢ç»æ: {len(df_none)}æ¡è®°å½?)

    # æµè¯æ¥è¯¢å¤ææ°æ®
    print("\n[æµè¯3] æ¥è¯¢åå¤ææ°æ®ï¼ä»QMT APIå®æ¶è®¡ç®ï¼?..")
    df_qfq = manager.get_data('000001.SZ', '2024-01-01', '2024-12-31', adjust_type='qfq')
    print(f"æ¥è¯¢ç»æ: {len(df_qfq)}æ¡è®°å½?)

    # ç»è®¡ä¿¡æ¯
    print("\n[æµè¯4] ç»è®¡ä¿¡æ¯...")
    stats = manager.get_statistics()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # å³é­
    manager.close()
    print("\nâ?æµè¯å®æ")
