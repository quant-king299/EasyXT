import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)
# -*- coding: utf-8 -*-

"""

简单函数策略适配器



将 func(df, top_n) -> List[str] 形式的策略函数

转换为 EnhancedBacktestEngine 所需的 StrategyBase 实例。



用法:

    from easyxt_backtest.simple_strategy_adapter import adapt

    from easyxt_backtest import EnhancedBacktestEngine



    engine = EnhancedBacktestEngine(initial_cash=100000)

    strategy = adapt(my_func, top_n=20, rebalance_days=5,

                     start_date='20240101', end_date='20250630')

    result = engine.run_backtest(strategy, start_date, end_date)

"""



import pandas as pd

from typing import Callable, List, Dict, Optional

from .strategy_base import StrategyBase





class SimpleFunctionAdapter(StrategyBase):

    """将简单函数适配为 StrategyBase"""



    def __init__(self, func: Callable, top_n: int = 20,

                 rebalance_days: int = 5,

                 start_date: str = '20200101',

                 end_date: str = '20251231',

                 data_manager=None,

                 category: str = 'stock',

                 adjust: str = 'none',

                 **extra_kwargs):

        super().__init__(data_manager)

        self.func = func

        self.top_n = top_n

        self._rebalance_days = rebalance_days

        self._start = start_date

        self._end = end_date

        self._extra = extra_kwargs

        self.category = category

        self.adjust = adjust  # 复权类型（仅 stock 类别使用）



        # 预加载并缓存该类别的全部日线数据（供选股和价格查询共用）

        self._category_data: Optional[pd.DataFrame] = None

        self._adjustment_cache = None  # 延迟初始化

        self._load_category_data()



    # ========== 数据预加载 ==========



    def _load_category_data(self):

        """预加载整个回测区间的类别数据到内存（CB/ETF 数据量小，参考旧版 CBBactestEngine 设计）。

        股票数据量太大不预加载，按需查询 DuckDB。"""

        # 只有 cb/etf 预加载（数据量可控），stock 按需查询

        if self.category not in ('cb', 'etf'):

            logger.info(f"[INFO] SimpleFunctionAdapter: stock 类别不预加载，按需查询 DuckDB")
            return



        import duckdb

        db_path = 'D:/StockData/stock_data.ddb'



        # YYYYMMDD → YYYY-MM-DD

        if len(self._start) == 8 and self._start.isdigit():

            start_fmt = f'{self._start[:4]}-{self._start[4:6]}-{self._start[6:]}'

        else:

            start_fmt = self._start

        if len(self._end) == 8 and self._end.isdigit():

            end_fmt = f'{self._end[:4]}-{self._end[4:6]}-{self._end[6:]}'

        else:

            end_fmt = self._end



        con = None

        try:

            con = duckdb.connect(db_path, read_only=True)



            if self.category == 'cb':

                query = f"""

                    SELECT ts_code, trade_date, open, high, low, close,

                           vol, amount, pct_chg,

                           cb_value, cb_over_rate, bond_value, bond_over_rate

                    FROM cb_daily

                    WHERE trade_date >= DATE '{start_fmt}'

                      AND trade_date <= DATE '{end_fmt}'

                      AND close > 0

                    ORDER BY ts_code, trade_date

                """

            else:  # etf

                query = f"""

                    SELECT ts_code, trade_date, open, high, low, close,

                           vol, amount, pct_chg

                    FROM etf_daily

                    WHERE trade_date >= DATE '{start_fmt}'

                      AND trade_date <= DATE '{end_fmt}'

                      AND close > 0

                    ORDER BY ts_code, trade_date

                """



            df = con.execute(query).fetchdf()

            if not df.empty:

                df['trade_date'] = pd.to_datetime(df['trade_date'])

                # 构建按日期快速查找的索引

                df.sort_values(['trade_date', 'ts_code'], inplace=True)

                print(f"[OK] SimpleFunctionAdapter 预加载 {self.category} 数据: "

                      f"{len(df)} 行, {df['ts_code'].nunique()} 只标的, "

                      f"{df['trade_date'].nunique()} 个交易日")

            else:

                logger.warning(f"[WARN] SimpleFunctionAdapter: {self.category} 数据为空")


            self._category_data = df

        except Exception as e:

            logger.error(f"[ERROR] SimpleFunctionAdapter 预加载失败: {e}")
            import traceback

            traceback.print_exc()

            self._category_data = pd.DataFrame()

        finally:

            if con is not None:

                try:

                    con.close()

                except Exception:

                    pass



    # ========== DuckDB 直连工具 ==========



    @staticmethod

    def _norm_date(date: str) -> str:

        """YYYYMMDD → YYYY-MM-DD"""

        if len(date) == 8 and date.isdigit():

            return f'{date[:4]}-{date[4:6]}-{date[6:]}'

        return date



    @staticmethod

    def _date_to_ts(date: str):

        """YYYYMMDD 或 YYYY-MM-DD → pd.Timestamp"""

        if len(date) == 8 and date.isdigit():

            return pd.Timestamp(f'{date[:4]}-{date[4:6]}-{date[6:]}')

        return pd.Timestamp(date)



    # ========== 价格查询接口（供引擎使用，避免走 UnifiedDataInterface） ==========



    def get_prices_for_date(self, symbols: List[str], date: str) -> Dict[str, float]:

        """

        批量查询多个标的在某日的 close 价格（一次向量化过滤，替代逐 symbol 查询）。



        引擎 _get_current_prices 优先使用此方法，大幅减少 DataFrame 扫描次数。

        """

        # CB/ETF: 从缓存向量化过滤

        if self._category_data is not None and not self._category_data.empty:

            date_dt = self._date_to_ts(date)

            day_data = self._category_data[

                (self._category_data['trade_date'] == date_dt) &

                (self._category_data['ts_code'].isin(symbols))

            ]

            if not day_data.empty:

                return dict(zip(day_data['ts_code'], day_data['close'].astype(float)))

            return {}



        # Stock: 直连 DuckDB，用 IN 子句一次查询

        if self.category == 'stock':

            return self._query_stock_prices_for_date(symbols, date)



        return {}



    def _query_stock_prices_for_date(self, symbols: List[str], date: str) -> Dict[str, float]:

        """直连 DuckDB 批量查询当日股票收盘价（IN 子句，支持后复权）"""

        import duckdb

        date_fmt = self._norm_date(date)

        con = None

        try:

            con = duckdb.connect('D:/StockData/stock_data.ddb', read_only=True)

            clean_codes = [s.replace('.SZ', '').replace('.SH', '') for s in symbols]

            all_codes = list(set(symbols + clean_codes))

            in_clause = ','.join(f"'{c}'" for c in all_codes)



            if self.adjust != 'none':

                df = con.execute(f"""

                    WITH latest AS (

                        SELECT ts_code, adj_factor FROM (

                            SELECT ts_code, adj_factor,

                                   ROW_NUMBER() OVER (PARTITION BY ts_code ORDER BY trade_date DESC) AS rn

                            FROM adj_factor

                            WHERE ts_code IN ({in_clause})

                        ) sub WHERE rn = 1

                    )

                    SELECT s.stock_code,

                           s.close / COALESCE(f_today.adj_factor, 1.0)

                                  * COALESCE(l.adj_factor, 1.0) AS close

                    FROM stock_daily s

                    LEFT JOIN adj_factor f_today

                      ON s.stock_code = f_today.ts_code AND s.date = f_today.trade_date

                    LEFT JOIN latest l ON s.stock_code = l.ts_code

                    WHERE s.stock_code IN ({in_clause})

                      AND s.date = DATE '{date_fmt}'

                      AND s.stock_code NOT LIKE '%TEST%'

                """).fetchdf()

            else:

                df = con.execute(f"""

                    SELECT stock_code, close FROM stock_daily

                    WHERE stock_code IN ({in_clause})

                      AND date = DATE '{date_fmt}'

                      AND stock_code NOT LIKE '%TEST%'

                """).fetchdf()



            if not df.empty:

                result = {}

                for _, row in df.iterrows():

                    code = row['stock_code']

                    result[code] = float(row['close'])

                    if not code.endswith('.SZ') and not code.endswith('.SH'):

                        for suffix in ['.SZ', '.SH']:

                            result[code + suffix] = float(row['close'])

                return {s: result[s] for s in symbols if s in result}

            return {}

        except Exception as e:

            logger.debug(f"  [DEBUG] _query_stock_prices_for_date 异常: {e}")
            return {}

        finally:

            if con is not None:

                try:

                    con.close()

                except Exception:

                    pass



    def get_price(self, symbol: str, date: str) -> Optional[float]:

        """

        查询某个标的在某日的 close 价格。

        ...

        """

        # CB/ETF: 从缓存查

        if self._category_data is not None and not self._category_data.empty:

            date_dt = self._date_to_ts(date)

            mask = ((self._category_data['ts_code'] == symbol) &

                    (self._category_data['trade_date'] == date_dt))

            rows = self._category_data.loc[mask, 'close']

            if not rows.empty:

                return float(rows.iloc[0])

            # 失败时打印候选值帮助诊断（仅前几次）

            if not hasattr(self, '_get_price_miss_count'):

                self._get_price_miss_count = 0

            self._get_price_miss_count += 1

            if self._get_price_miss_count <= 3:

                available_codes = self._category_data[

                    self._category_data['trade_date'] == date_dt

                ]['ts_code'].unique()[:5]

                print(f"  [get_price MISS] symbol={symbol}, date={date}, "

                      f"缓存中当日可用代码示例: {list(available_codes)}")

            return None



        # Stock: 直连 DuckDB 查询单条

        if self.category == 'stock':

            return self._query_stock_price(symbol, date)



        return None



    def _query_stock_price(self, symbol: str, date: str) -> Optional[float]:

        """直连 DuckDB 查询单只股票的收盘价（支持复权）"""

        import duckdb

        date_fmt = self._norm_date(date)

        con = None

        try:

            con = duckdb.connect('D:/StockData/stock_data.ddb', read_only=True)

            code_clean = symbol.replace('.SZ', '').replace('.SH', '')



            if self.adjust != 'none':

                # 后复权：adj_close = close / factor_today * factor_latest

                result = con.execute(f"""

                    WITH stock_raw AS (

                        SELECT date, close

                        FROM stock_daily

                        WHERE (stock_code = '{symbol}' OR stock_code = '{code_clean}')

                          AND date = DATE '{date_fmt}'

                    ),

                    factors AS (

                        SELECT trade_date, adj_factor

                        FROM adj_factor

                        WHERE ts_code = '{symbol}'

                    ),

                    today_factor AS (

                        SELECT f.adj_factor

                        FROM stock_raw s

                        JOIN factors f ON f.trade_date = s.date

                    ),

                    latest_factor AS (

                        SELECT adj_factor FROM factors

                        ORDER BY trade_date DESC LIMIT 1

                    )

                    SELECT s.close / COALESCE(t.adj_factor, 1.0) * COALESCE(l.adj_factor, 1.0) AS adj_close

                    FROM stock_raw s

                    LEFT JOIN today_factor t ON TRUE

                    LEFT JOIN latest_factor l ON TRUE

                """).fetchone()

            else:

                result = con.execute(f"""

                    SELECT close FROM stock_daily

                    WHERE (stock_code = '{symbol}' OR stock_code = '{code_clean}')

                      AND date = DATE '{date_fmt}'

                    LIMIT 1

                """).fetchone()



            if result and result[0]:

                return float(result[0])

            return None

        except Exception as e:

            logger.debug(f"  [DEBUG] _query_stock_price 异常: symbol={symbol}, date={date}, error={e}")
            return None

        finally:

            if con is not None:

                try:

                    con.close()

                except Exception:

                    pass



    def get_prices_batch(self, symbols: List[str],

                         start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:

        """

        批量获取多个标的在日期区间内的日线数据。



        引擎 _load_daily_prices 会优先使用此方法，

        从而正确加载 CB/ETF/Stock 的日线价格用于逐日盯市计算。



        CB/ETF: 从缓存过滤（快）

        Stock: 直连 DuckDB 批量查询

        """

        # CB/ETF: 从缓存查

        if self._category_data is not None and not self._category_data.empty:

            start_dt = self._date_to_ts(start_date)

            end_dt = self._date_to_ts(end_date)

            result = {}

            for symbol in symbols:

                mask = ((self._category_data['ts_code'] == symbol) &

                        (self._category_data['trade_date'] >= start_dt) &

                        (self._category_data['trade_date'] <= end_dt))

                sym_df = self._category_data.loc[mask].copy()

                if not sym_df.empty:

                    sym_df = sym_df.set_index('trade_date')

                    sym_df.index = sym_df.index.strftime('%Y%m%d')

                    result[symbol] = sym_df

            if result:

                print(f"[OK] SimpleFunctionAdapter.get_prices_batch: "

                      f"返回 {len(result)} 只标的日线数据 [{self.category}]")

            return result



        # Stock: 直连 DuckDB 批量查询

        if self.category == 'stock':

            return self._query_stock_prices_batch(symbols, start_date, end_date)



        return {}



    def _query_stock_prices_batch(self, symbols: List[str],

                                   start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:

        """直连 DuckDB 批量查询股票日线数据（支持后复权）"""

        import duckdb

        start_fmt = self._norm_date(start_date)

        end_fmt = self._norm_date(end_date)

        con = None

        result = {}

        try:

            con = duckdb.connect('D:/StockData/stock_data.ddb', read_only=True)

            for symbol in symbols:

                code_clean = symbol.replace('.SZ', '').replace('.SH', '')



                if self.adjust != 'none':

                    # 后复权：adj_close = close / factor_today * factor_latest

                    df = con.execute(f"""

                        SELECT s.stock_code AS ts_code, s.date AS trade_date,

                               s.open, s.high, s.low,

                               s.close / COALESCE(f_today.adj_factor, 1.0)

                                      * COALESCE(f_latest.adj_factor, 1.0) AS close,

                               s.volume, s.amount

                        FROM stock_daily s

                        LEFT JOIN adj_factor f_today

                          ON s.stock_code = f_today.ts_code AND s.date = f_today.trade_date

                        LEFT JOIN (

                            SELECT ts_code, adj_factor FROM (

                                SELECT ts_code, adj_factor,

                                       ROW_NUMBER() OVER (PARTITION BY ts_code ORDER BY trade_date DESC) AS rn

                                FROM adj_factor

                                WHERE ts_code = '{symbol}'

                            ) sub WHERE rn = 1

                        ) f_latest ON TRUE

                        WHERE (s.stock_code = '{symbol}' OR s.stock_code = '{code_clean}')

                          AND s.date >= DATE '{start_fmt}' AND s.date <= DATE '{end_fmt}'

                          AND s.close > 0

                        ORDER BY s.date

                    """).fetchdf()

                else:

                    df = con.execute(f"""

                        SELECT stock_code AS ts_code, date AS trade_date,

                               open, high, low, close, volume, amount

                        FROM stock_daily

                        WHERE (stock_code = '{symbol}' OR stock_code = '{code_clean}')

                          AND date >= DATE '{start_fmt}' AND date <= DATE '{end_fmt}'

                          AND close > 0

                        ORDER BY date

                    """).fetchdf()



                if not df.empty:

                    df['trade_date'] = pd.to_datetime(df['trade_date'])

                    df = df.set_index('trade_date')

                    df.index = df.index.strftime('%Y%m%d')

                    result[symbol] = df



            adj_label = '(后复权)' if self.adjust != 'none' else '(不复权)'

            if result:

                print(f"[OK] SimpleFunctionAdapter.get_prices_batch(stock) {adj_label}: "

                      f"返回 {len(result)} 只股票日线数据")

        except Exception as e:

            logger.warning(f"[WARN] _query_stock_prices_batch 失败: {e}")
        finally:

            if con is not None:

                try:

                    con.close()

                except Exception:

                    pass

        return result



    # ========== StrategyBase 接口实现 ==========



    def select_stocks(self, date: str) -> List[str]:

        """选股：CB/ETF 从缓存筛选，stock 直连 DuckDB 查询当日数据"""

        # Stock: 直连 DuckDB（数据量太大不适合预加载）

        if self.category == 'stock':

            return self._select_stocks_from_duckdb(date)



        # CB/ETF: 从缓存筛选

        if self._category_data is None or self._category_data.empty:

            logger.debug(f"  [DEBUG] select_stocks: 缓存数据为空 [类别:{self.category}, 日期:{date}]")
            return []



        date_dt = self._date_to_ts(date)

        day_df = self._category_data[self._category_data['trade_date'] == date_dt].copy()

        if day_df.empty:

            logger.debug(f"  [DEBUG] select_stocks: 当日无数据 [类别:{self.category}, 日期:{date}]")
            return []



        logger.debug(f"  [DEBUG] select_stocks: 输入数据形状={day_df.shape}, 类别={self.category}")
        sample_codes = day_df['ts_code'].head(3).tolist()

        logger.debug(f"  [DEBUG] select_stocks: 输入数据中的代码示例: {sample_codes}")


        try:

            result = self.func(day_df, top_n=self.top_n, **self._extra)

        except Exception as e:

            logger.error(f"  [ERROR] select_stocks: 策略函数执行失败: {e}")
            return []



        print(f"  [DEBUG] select_stocks: 策略返回的代码: "

              f"{result[:5] if isinstance(result, list) else result}")



        return result[:self.top_n] if isinstance(result, list) else []



    def _select_stocks_from_duckdb(self, date: str) -> List[str]:

        """Stock 类别：直连 DuckDB 查询当日数据（避免预加载海量股票数据）"""

        import duckdb

        date_fmt = self._norm_date(date)

        con = None

        try:

            con = duckdb.connect('D:/StockData/stock_data.ddb', read_only=True)

            df = con.execute(f"""

                SELECT stock_code AS ts_code, date AS trade_date,

                       close,

                       (close - LAG(close) OVER (

                           PARTITION BY stock_code ORDER BY date

                       )) / NULLIF(LAG(close) OVER (

                           PARTITION BY stock_code ORDER BY date

                       ), 0) * 100 AS pct_chg,

                       amount

                FROM stock_daily

                WHERE date = DATE '{date_fmt}'

                  AND close > 0 AND amount > 0

                  AND stock_code NOT LIKE '%TEST%'

            """).fetchdf()



            if df.empty:

                logger.debug(f"  [DEBUG] select_stocks(stock): 当日无数据 [日期:{date}]")
                return []

            df['trade_date'] = pd.to_datetime(df['trade_date'])



            logger.debug(f"  [DEBUG] select_stocks(stock): 输入数据形状={df.shape}")
            sample_codes = df['ts_code'].head(3).tolist()

            logger.debug(f"  [DEBUG] select_stocks(stock): 输入数据中的代码示例: {sample_codes}")


            result = self.func(df, top_n=self.top_n, **self._extra)

            print(f"  [DEBUG] select_stocks(stock): 策略返回的代码: "

                  f"{result[:5] if isinstance(result, list) else result}")



            return result[:self.top_n] if isinstance(result, list) else []

        except Exception as e:

            logger.error(f"  [ERROR] _select_stocks_from_duckdb 失败: {e}")
            return []

        finally:

            if con is not None:

                try:

                    con.close()

                except Exception:

                    pass



    def get_target_weights(self, date: str, selected: List[str]) -> Dict[str, float]:

        if not selected:

            return {}

        w = 1.0 / len(selected)

        return {s: w for s in selected}



    def get_rebalance_dates(self, start_date: str, end_date: str) -> List[str]:

        return self._get_all_trading_days(start_date or self._start,

                                          end_date or self._end)





def adapt(func: Callable, top_n: int = 20, rebalance_days: int = 5,

          start_date: str = '20200101', end_date: str = '20251231',

          data_manager=None, category: str = 'stock',

          adjust: str = 'none', **extra) -> StrategyBase:

    """快速适配: 给一个函数, 返回 StrategyBase"""

    return SimpleFunctionAdapter(

        func, top_n=top_n, rebalance_days=rebalance_days,

        start_date=start_date, end_date=end_date,

        data_manager=data_manager, category=category,

        adjust=adjust, **extra,

    )

