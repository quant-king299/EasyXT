# -*- coding: utf-8 -*-
"""
数据管理器 - 统一多数据源接口

支持的数据源：
1. DuckDB本地数据库（优先，最快）
2. QMT历史数据
3. Tushare在线API（备用）
"""
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
import warnings
warnings.filterwarnings('ignore')

# 尝试导入各种数据源
try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

try:
    import tushare as ts
    TUSHARE_AVAILABLE = True
except ImportError:
    TUSHARE_AVAILABLE = False

try:
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False


def convert_date_format(dt_str: str,
                       input_format: str = '%Y%m%d',
                       output_format: str = '%Y-%m-%d') -> str:
    """
    转换日期格式

    Args:
        dt_str: 日期字符串
        input_format: 输入格式
        output_format: 输出格式

    Returns:
        转换后的日期字符串
    """
    try:
        dt = datetime.strptime(dt_str, input_format)
        return dt.strftime(output_format)
    except:
        return dt_str


class DataManager:
    """
    统一数据管理器

    功能：
    - 自动选择最优数据源
    - 价格数据查询（OHLCV）
    - 基本面数据查询（市值、财务指标）
    - 交易日历查询
    - 最近交易日价格查找（解决数据缺失问题）
    """

    def __init__(self,
                 duckdb_path: Optional[str] = None,
                 tushare_token: Optional[str] = None):
        """
        初始化数据管理器

        Args:
            duckdb_path: DuckDB数据库路径
            tushare_token: Tushare API Token
        """
        # 读取.env文件
        self._load_env_file()

        self.duckdb_path = duckdb_path or os.getenv('DUCKDB_PATH', 'D:/StockData/stock_data.ddb')
        self.tushare_token = tushare_token or os.getenv('TUSHARE_TOKEN')

        # 数据源连接
        self.duckdb_con = None
        self.tushare_pro = None
        self.qmt_connected = False

        # 缓存
        self.price_cache = {}  # {(date, symbol): price}
        self.fundamental_cache = {}  # {(date, symbol): data} - 单个股票缓存
        self.fundamentals_cache = {}  # {date: DataFrame} - 批量缓存（全市场）
        self.trading_days_cache = None

        # 市值缓存（用于QMT失败时的fallback）
        self.market_value_cache = {}  # {symbol: (date, market_value)}

        # 初始化数据源
        self._init_duckdb()
        self._init_tushare()
        self._init_qmt()

        print(f"[DataManager] DuckDB: {'[OK]' if self.duckdb_con else '[FAIL]'}")
        print(f"[DataManager] Tushare: {'[OK]' if self.tushare_pro else '[FAIL]'}")
        print(f"[DataManager] QMT: {'[OK]' if self.qmt_connected else '[FAIL]'}")

    def _load_env_file(self):
        """加载.env文件"""
        env_files = ['.env', '../.env', '../.env']

        for env_file in env_files:
            env_path = os.path.join(os.path.dirname(__file__), env_file)
            if not os.path.exists(env_path):
                # 尝试项目根目录
                env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), env_file)

            if os.path.exists(env_path):
                try:
                    with open(env_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip() and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                if key.strip() not in os.environ:
                                    os.environ[key.strip()] = value.strip()
                    break
                except Exception as e:
                    pass

    def _init_duckdb(self):
        """初始化DuckDB连接"""
        if not DUCKDB_AVAILABLE:
            return

        try:
            self.duckdb_con = duckdb.connect(self.duckdb_path, read_only=True)
            # 测试连接
            test_query = "SELECT COUNT(*) FROM stock_daily LIMIT 1"
            self.duckdb_con.execute(test_query)
        except Exception as e:
            print(f"[DataManager] DuckDB初始化失败: {e}")
            self.duckdb_con = None

    def _init_tushare(self):
        """初始化Tushare连接"""
        if not TUSHARE_AVAILABLE or not self.tushare_token:
            return

        try:
            ts.set_token(self.tushare_token)
            self.tushare_pro = ts.pro_api()
            # 测试连接
            test_df = self.tushare_pro.daily(ts_code='000001.SZ',
                                            trade_date='20230101',
                                            fields='ts_code,trade_date,close')
        except Exception as e:
            print(f"[DataManager] Tushare初始化失败: {e}")
            self.tushare_pro = None

    def _init_qmt(self):
        """初始化QMT连接"""
        if not QMT_AVAILABLE:
            return

        try:
            # 测试连接
            test_data = xtdata.get_market_data_ex(['000001.SZ'],
                                                  period='1d',
                                                  start_time='20230101',
                                                  end_time='20230102')
            self.qmt_connected = True
        except Exception as e:
            print(f"[DataManager] QMT初始化失败: {e}")
            self.qmt_connected = False

    # ==================== 价格数据接口 ====================

    def get_price(self,
                  codes: Union[str, List[str]],
                  start_date: str,
                  end_date: str,
                  fields: List[str] = ['open', 'high', 'low', 'close', 'volume'],
                  fq: str = 'qfq') -> pd.DataFrame:
        """
        获取价格数据

        Args:
            codes: 股票代码或代码列表
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            fields: 字段列表
            fq: 复权类型 ('qfq'-前复权, 'hfq'-后复权, 'None'-不复权)

        Returns:
            DataFrame with MultiIndex [date, symbol], columns=fields
        """
        if isinstance(codes, str):
            codes = [codes]

        # 优先从DuckDB获取
        if self.duckdb_con:
            df = self._get_price_from_duckdb(codes, start_date, end_date, fields)
            if not df.empty:
                return df

        # 其次从QMT获取
        if self.qmt_connected:
            df = self._get_price_from_qmt(codes, start_date, end_date, fields)
            if not df.empty:
                return df

        # 最后从Tushare获取
        if self.tushare_pro:
            df = self._get_price_from_tushare(codes, start_date, end_date, fields)
            if not df.empty:
                return df

        return pd.DataFrame()

    def _get_price_from_duckdb(self,
                                codes: List[str],
                                start_date: str,
                                end_date: str,
                                fields: List[str]) -> pd.DataFrame:
        """从DuckDB获取价格数据"""
        try:
            # 转换日期格式
            start_formatted = convert_date_format(start_date)
            end_formatted = convert_date_format(end_date)

            # 构建查询
            codes_str = "', '".join(codes)
            fields_str = ', '.join(fields)

            query = f"""
                SELECT
                    stock_code as symbol,
                    date,
                    {fields_str}
                FROM stock_daily
                WHERE stock_code IN ('{codes_str}')
                  AND date >= '{start_formatted}'
                  AND date <= '{end_formatted}'
                  AND period = '1d'
                  AND symbol_type = 'stock'
                ORDER BY date, stock_code
            """

            df = self.duckdb_con.execute(query).df()

            if df.empty:
                return pd.DataFrame()

            # 设置MultiIndex
            df.set_index(['date', 'symbol'], inplace=True)

            # 缓存价格数据
            for idx, row in df.iterrows():
                date_str = idx[0].strftime('%Y%m%d') if isinstance(idx[0], pd.Timestamp) else str(idx[0])
                symbol = idx[1]
                if 'close' in fields:
                    self.price_cache[(date_str, symbol)] = row['close']

            return df

        except Exception as e:
            print(f"[DataManager] DuckDB查询失败: {e}")
            return pd.DataFrame()

    def _get_price_from_qmt(self,
                            codes: List[str],
                            start_date: str,
                            end_date: str,
                            fields: List[str]) -> pd.DataFrame:
        """从QMT获取价格数据"""
        try:
            data = xtdata.get_market_data_ex(
                stock_list=codes,
                period='1d',
                start_time=start_date,
                end_time=end_date
            )

            if not data or len(data) == 0:
                return pd.DataFrame()

            # 转换为DataFrame
            dfs = []
            for symbol in codes:
                if symbol in data and data[symbol] is not None:
                    df = data[symbol].reset_index()
                    df['symbol'] = symbol
                    dfs.append(df)

            if not dfs:
                return pd.DataFrame()

            result = pd.concat(dfs, ignore_index=True)
            result.rename(columns={'time': 'date'}, inplace=True)

            # 设置MultiIndex
            result.set_index(['date', 'symbol'], inplace=True)

            return result

        except Exception as e:
            print(f"[DataManager] QMT查询失败: {e}")
            return pd.DataFrame()

    def _get_price_from_tushare(self,
                                codes: List[str],
                                start_date: str,
                                end_date: str,
                                fields: List[str]) -> pd.DataFrame:
        """从Tushare获取价格数据"""
        try:
            # 转换代码格式 (000001.SZ -> 000001.SZ)
            all_data = []

            for code in codes:
                df = self.tushare_pro.daily(
                    ts_code=code,
                    start_date=start_date,
                    end_date=end_date
                )

                if df is not None and not df.empty:
                    df['symbol'] = code
                    df.rename(columns={'trade_date': 'date'}, inplace=True)
                    all_data.append(df)

            if not all_data:
                return pd.DataFrame()

            result = pd.concat(all_data, ignore_index=True)
            result.set_index(['date', 'symbol'], inplace=True)

            return result

        except Exception as e:
            print(f"[DataManager] Tushare查询失败: {e}")
            return pd.DataFrame()

    # ==================== 基本面数据接口 ====================

    def get_fundamentals(self,
                         codes: List[str],
                         date: str,
                         fields: List[str] = ['circ_mv']) -> pd.DataFrame:
        """
        获取基本面数据

        Args:
            codes: 股票代码列表
            date: 查询日期 (YYYYMMDD)
            fields: 字段列表 (支持: circ_mv-流通市值, total_mv-总市值)

        Returns:
            DataFrame with index=symbol, columns=fields

        优先级（优化后的数据源策略）：
        1. DuckDB（本地，最快）⭐ 推荐优先使用，需先通过GUI下载完整数据
        2. Tushare（在线，备用）⚡ 自动fallback，实时获取历史市值
        3. QMT（仅供参考）⚠️ 使用当前股本×历史价格，可能不准确
        """
        # 优先级1: 从DuckDB获取（本地市值表，速度最快）
        if self.duckdb_con and ('circ_mv' in fields or 'total_mv' in fields):
            df = self._get_fundamentals_from_duckdb(codes, date, fields)
            if not df.empty:
                return df

        # 优先级2: 从Tushare获取（在线API，真实的市值数据）
        if self.tushare_pro and ('circ_mv' in fields or 'total_mv' in fields):
            df = self._get_fundamentals_from_tushare(codes, date, fields)
            if not df.empty:
                return df

        # 优先级3: 从QMT获取（不准确！使用当前股本×历史价格）
        # 注意：QMT的股本数据是时点数据，不是历史数据，计算结果仅供参考
        if self.qmt_connected and ('circ_mv' in fields or 'total_mv' in fields):
            print("[DataManager] 警告: 使用QMT计算市值可能不准确（股本数据非历史数据）")
            df = self._get_fundamentals_from_qmt(codes, date, fields)
            if not df.empty:
                return df

        return pd.DataFrame()

    def _get_fundamentals_from_tushare(self,
                                       codes: List[str],
                                       date: str,
                                       fields: List[str]) -> pd.DataFrame:
        """
        从Tushare获取基本面数据（超高速批量查询版）⚡

        优化：
        1. 批量查询全市场数据（1次API调用 vs 5000次）
        2. 缓存全市场数据，支持任意股票池查询
        3. 添加延迟避免限流
        """
        try:
            import time

            # 检查缓存（缓存全市场数据，不筛选）
            cache_key = ('tushare_fundamentals_all', date)
            if cache_key in self.fundamentals_cache:
                cached_df = self.fundamentals_cache[cache_key]
                # 从缓存中筛选需要的股票
                result = cached_df[cached_df['ts_code'].isin(codes)].copy()
                if not result.empty:
                    result.set_index('ts_code', inplace=True)
                    return result

            # ✨ 批量查询全市场数据（不指定ts_code，返回所有股票）
            df = self.tushare_pro.daily_basic(
                trade_date=date,
                fields='ts_code,trade_date,' + ','.join(fields)
            )

            if df is None or df.empty:
                # 如果指定日期没有数据，尝试向前查找（最多3天）
                for i in range(1, 4):
                    try:
                        from datetime import datetime, timedelta
                        date_obj = datetime.strptime(date, '%Y%m%d')
                        prev_date = (date_obj - timedelta(days=i)).strftime('%Y%m%d')

                        df = self.tushare_pro.daily_basic(
                            trade_date=prev_date,
                            fields='ts_code,trade_date,' + ','.join(fields)
                        )

                        if df is not None and not df.empty:
                            print(f"[DataManager] {date}使用Tushare{prev_date}数据（批量）")
                            break
                    except:
                        continue

            if df is None or df.empty:
                print(f"[DataManager] Tushare批量查询{date}失败：无数据")
                return pd.DataFrame()

            # 缓存全市场数据（不筛选，方便后续复用）
            self.fundamentals_cache[cache_key] = df.copy()

            # 筛选需要的股票
            df_filtered = df[df['ts_code'].isin(codes)].copy()
            df_filtered.set_index('ts_code', inplace=True)

            # 添加延迟避免限流（每次查询间隔0.3秒）
            time.sleep(0.3)

            return df_filtered

        except Exception as e:
            print(f"[DataManager] Tushare批量查询{date}失败: {e}")
            return pd.DataFrame()

        except Exception as e:
            print(f"[DataManager] Tushare基本面查询失败: {e}")
            return pd.DataFrame()

    def _get_tushare_with_fallback(self,
                                   code: str,
                                   date: str,
                                   fields: List[str],
                                   max_days_back: int = 10) -> pd.DataFrame:
        """
        从Tushare获取数据，带日期fallback机制

        向前查找最近的数据（最多max_days_back天）
        """
        from datetime import datetime, timedelta

        date_obj = datetime.strptime(date, '%Y%m%d')

        for i in range(max_days_back):
            prev_date = (date_obj - timedelta(days=i)).strftime('%Y%m%d')

            # 跳过周末
            day_of_week = (date_obj - timedelta(days=i)).weekday()
            if day_of_week >= 5:  # 周六、周日
                continue

            try:
                df = self.tushare_pro.daily_basic(
                    ts_code=code,
                    trade_date=prev_date,
                    fields=','.join(['ts_code', 'trade_date'] + fields)
                )

                if df is not None and not df.empty:
                    print(f"[DataManager] {code} {date}使用Tushare{prev_date}数据")
                    return df

            except Exception:
                continue

        return pd.DataFrame()

    def _get_fundamentals_from_qmt(self,
                                   codes: List[str],
                                   date: str,
                                   fields: List[str]) -> pd.DataFrame:
        """
        从QMT获取基本面数据（主要是市值）

        计算方法：
        - circ_mv (流通市值) = FloatVolume × 收盘价
        - total_mv (总市值) = TotalVolume × 收盘价

        增强功能：
        - 自动回退查找（向前查找最近可用日期）
        - 使用缓存的历史市值数据作为fallback
        - 当FloatVolume为0时返回空，触发fallback到Tushare/DuckDB
        """
        if not QMT_AVAILABLE:
            return pd.DataFrame()

        try:
            result_data = []

            for code in codes:
                # 1. 获取股票基本信息（股本数据）
                info = xtdata.get_instrument_detail(code)

                # 检查是否有有效的股本数据（QMT mini版本FloatVolume可能为0）
                if not info or 'FloatVolume' not in info or info.get('FloatVolume', 0) == 0:
                    # QMT mini版本不支持股本数据，跳过
                    continue

                # 2. 尝试获取收盘价（带日期回退）
                close_price = self._get_close_price_with_fallback(code, date)

                if close_price is None:
                    # QMT无法获取价格，跳过该股票（不再使用缓存）
                    print(f"[DataManager] {code} QMT无法获取 {date} 的价格，跳过")
                    continue

                # 3. 计算市值
                row_data = {'symbol': code}

                # 流通股本（股）转成（万股）
                float_volume = info['FloatVolume'] / 10000  # 股 -> 万股

                # 总股本（股）转成（万股）
                total_volume = info['TotalVolume'] / 10000  # 股 -> 万股

                if 'circ_mv' in fields:
                    # 流通市值（万元）= 流通股本（万股）× 收盘价（元）
                    circ_mv = float_volume * close_price
                    row_data['circ_mv'] = circ_mv

                    # 注意：不再缓存市值数据（每次都重新计算）
                    # 原因：QMT股本数据是时点数据，缓存会导致使用错误的市值

                if 'total_mv' in fields:
                    # 总市值（万元）= 总股本（万股）× 收盘价（元）
                    row_data['total_mv'] = total_volume * close_price

                result_data.append(row_data)

            if not result_data:
                return pd.DataFrame()

            result = pd.DataFrame(result_data)
            result.set_index('symbol', inplace=True)

            # 只返回请求的字段
            available_fields = [f for f in fields if f in result.columns]
            return result[available_fields]

        except Exception as e:
            print(f"[DataManager] QMT基本面查询失败: {e}")
            return pd.DataFrame()

    def _get_close_price_with_fallback(self, code: str, date: str, max_days_back: int = 10) -> Optional[float]:
        """
        获取收盘价（完整的多层fallback机制）

        优先级（按速度和可靠性排序）：
        1. DuckDB当天价格  ← 最快、最可靠！
        2. QMT当天价格
        3. Tushare当天价格
        4. DuckDB向前查找（最多10天）
        5. QMT向前查找（最多10天）

        Args:
            code: 股票代码
            date: 日期 (YYYYMMDD)
            max_days_back: 最多回退天数

        Returns:
            收盘价或None
        """
        # 1. 优先从DuckDB获取当天价格（最快、最可靠）
        if self.duckdb_con:
            price = self._get_single_price_from_duckdb(code, date)
            if price is not None:
                return price  # 静默成功，不打印日志

        # 2. 尝试从QMT获取当天价格
        try:
            price_data = xtdata.get_market_data_ex(
                stock_list=[code],
                period='1d',
                start_time=date,
                end_time=date,
                field_list=['close']
            )

            if price_data and code in price_data and price_data[code] is not None:
                df = price_data[code]
                if not df.empty:
                    close_price = df['close'].values[0] if hasattr(df['close'], 'values') else df['close'].iloc[0]
                    return close_price
        except:
            pass

        # 3. 尝试从Tushare获取当天价格
        if self.tushare_pro:
            try:
                df = self.tushare_pro.daily(
                    ts_code=code,
                    trade_date=date,
                    fields='close'
                )

                if df is not None and not df.empty:
                    price = df.iloc[0]['close']
                    return price
            except:
                pass

        # 4. 向前查找最近的交易日（优先DuckDB）
        from datetime import datetime, timedelta
        date_obj = datetime.strptime(date, '%Y%m%d')

        for i in range(1, max_days_back + 1):
            prev_date = (date_obj - timedelta(days=i)).strftime('%Y%m%d')

            # 跳过周末
            day_of_week = (date_obj - timedelta(days=i)).weekday()
            if day_of_week >= 5:  # 周六、周日
                continue

            # 4a. 先尝试DuckDB（更快）
            if self.duckdb_con:
                price = self._get_single_price_from_duckdb(code, prev_date)
                if price is not None:
                    print(f"[DataManager] {code} {date}使用DuckDB{prev_date}价格: {price:.2f}")
                    return price

            # 4b. 再尝试QMT
            try:
                price_data = xtdata.get_market_data_ex(
                    stock_list=[code],
                    period='1d',
                    start_time=prev_date,
                    end_time=prev_date,
                    field_list=['close']
                )

                if price_data and code in price_data and price_data[code] is not None:
                    df = price_data[code]
                    if not df.empty:
                        close_price = df['close'].values[0] if hasattr(df['close'], 'values') else df['close'].iloc[0]
                        print(f"[DataManager] {code} {date}使用QMT{prev_date}价格: {close_price:.2f}")
                        return close_price
            except:
                continue

        return None

    def _get_single_price_from_duckdb(self, code: str, date: str) -> Optional[float]:
        """
        从DuckDB获取指定日期的价格

        Args:
            code: 股票代码
            date: 日期 (YYYYMMDD)

        Returns:
            收盘价或None
        """
        try:
            # 转换日期格式
            from datetime import datetime
            date_formatted = datetime.strptime(date, '%Y%m%d').strftime('%Y-%m-%d')

            query = f"""
                SELECT close
                FROM stock_daily
                WHERE stock_code = '{code}'
                  AND date = '{date_formatted}'
                  AND period = '1d'
                LIMIT 1
            """

            df = self.duckdb_con.execute(query).df()

            if not df.empty:
                return df.iloc[0]['close']

            return None

        except Exception as e:
            return None

    def _get_fundamentals_from_duckdb(self,
                                      codes: List[str],
                                      date: str,
                                      fields: List[str]) -> pd.DataFrame:
        """
        从DuckDB获取基本面数据

        优先从stock_market_cap表读取市值数据
        如果表不存在，则使用缓存数据
        """
        if not self.duckdb_con:
            return pd.DataFrame()

        try:
            # 检查是否存在stock_market_cap表
            try:
                self.duckdb_con.execute("SELECT COUNT(*) FROM stock_market_cap LIMIT 1").fetchone()
                table_exists = True
            except:
                table_exists = False

            if table_exists:
                # 从市值表读取数据
                codes_str = "','".join(codes)
                date_obj = pd.to_datetime(date, format='%Y%m%d')

                # 查询市值表（使用最近的市值数据）
                query = f"""
                    SELECT DISTINCT
                        stock_code as symbol,
                        circ_mv,
                        total_mv
                    FROM stock_market_cap
                    WHERE stock_code IN ('{codes_str}')
                      AND date <= '{date_obj.strftime('%Y-%m-%d')}'
                    ORDER BY date DESC
                """
                df = self.duckdb_con.execute(query).df()

                if not df.empty:
                    # 对每个股票只保留最近的一条记录
                    df = df.drop_duplicates(subset=['symbol'], keep='first')
                    df.set_index('symbol', inplace=True)

                    # 只返回请求的字段
                    available_fields = [f for f in fields if f in df.columns]
                    if available_fields:
                        print(f"[DataManager] 从DuckDB市值表获取 {len(df)} 只股票的市值数据")
                        return df[available_fields]

            # 表不存在或没有数据，使用缓存
            result_data = []
            for code in codes:
                if code in self.market_value_cache:
                    cached_date, cached_mv = self.market_value_cache[code]
                    result_data.append({
                        'symbol': code,
                        'circ_mv': cached_mv
                    })
                    print(f"[DataManager] {code} 使用缓存市值 ({cached_date})")

            if result_data:
                df = pd.DataFrame(result_data)
                df.set_index('symbol', inplace=True)
                return df

            return pd.DataFrame()

        except Exception as e:
            print(f"[DataManager] DuckDB基本面查询失败: {e}")
            return pd.DataFrame()

            if not result_data:
                return pd.DataFrame()

            result = pd.DataFrame(result_data)
            result.set_index('symbol', inplace=True)

            # 只返回请求的字段
            available_fields = [f for f in fields if f in result.columns]
            return result[available_fields]

        except Exception as e:
            print(f"[DataManager] DuckDB基本面查询失败: {e}")
            return pd.DataFrame()

    def _get_recent_price_from_duckdb(self, code: str, date: str, max_days_back: int = 30) -> Optional[float]:
        """
        从DuckDB获取最近的价格

        Args:
            code: 股票代码
            date: 日期 (YYYYMMDD)
            max_days_back: 最多回退天数

        Returns:
            最近的价格或None
        """
        try:
            # 转换日期格式
            from datetime import datetime, timedelta
            date_obj = datetime.strptime(date, '%Y%m%d')
            start_date = (date_obj - timedelta(days=max_days_back)).strftime('%Y-%m-%d')
            end_date = date_obj.strftime('%Y-%m-%d')

            query = f"""
                SELECT close
                FROM stock_daily
                WHERE stock_code = '{code}'
                  AND date >= '{start_date}'
                  AND date <= '{end_date}'
                  AND period = '1d'
                ORDER BY date DESC
                LIMIT 1
            """

            df = self.duckdb_con.execute(query).df()

            if not df.empty:
                return df.iloc[0]['close']

            return None

        except Exception as e:
            return None

    # ==================== 交易日历接口 ====================

    def get_trading_dates(self,
                          start_date: str,
                          end_date: str) -> List[str]:
        """
        获取交易日历

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            交易日期列表 (YYYYMMDD格式)
        """
        if self.trading_days_cache is not None:
            # 过滤日期范围
            return [d for d in self.trading_days_cache
                    if start_date <= d <= end_date]

        # 优先从DuckDB获取
        if self.duckdb_con:
            dates = self._get_trading_dates_from_duckdb(start_date, end_date)
            if dates:
                return dates

        # 从Tushare获取
        if self.tushare_pro:
            dates = self._get_trading_dates_from_tushare(start_date, end_date)
            if dates:
                return dates

        return []

    def _get_trading_dates_from_duckdb(self,
                                       start_date: str,
                                       end_date: str) -> List[str]:
        """从DuckDB获取交易日历"""
        try:
            start_formatted = convert_date_format(start_date)
            end_formatted = convert_date_format(end_date)

            query = f"""
                SELECT DISTINCT date
                FROM stock_daily
                WHERE date >= '{start_formatted}'
                  AND date <= '{end_formatted}'
                  AND symbol_type = 'stock'
                ORDER BY date
            """

            df = self.duckdb_con.execute(query).df()

            if df.empty:
                return []

            # 转换为YYYYMMDD格式
            dates = []
            for date_val in df['date']:
                if isinstance(date_val, str):
                    dates.append(date_val.replace('-', ''))
                elif isinstance(date_val, pd.Timestamp):
                    dates.append(date_val.strftime('%Y%m%d'))

            return dates

        except Exception as e:
            print(f"[DataManager] DuckDB交易日历查询失败: {e}")
            return []

    def _get_trading_dates_from_tushare(self,
                                        start_date: str,
                                        end_date: str) -> List[str]:
        """从Tushare获取交易日历"""
        try:
            df = self.tushare_pro.trade_cal(
                exchange='SSE',
                start_date=start_date,
                end_date=end_date,
                is_open=1
            )

            if df is not None and not df.empty:
                return df['cal_date'].tolist()

            return []

        except Exception as e:
            print(f"[DataManager] Tushare交易日历查询失败: {e}")
            return []

    # ==================== 关键功能：最近交易日价格查找 ====================

    def get_nearest_price(self,
                          code: str,
                          date: str,
                          max_days_back: int = 10,
                          max_days_forward: int = 2) -> Optional[float]:
        """
        获取最近交易日的价格

        这是修复"调仓日数据缺失"问题的关键功能：
        - 如果当天有数据，返回当天价格
        - 如果当天无数据，向前查找最近的交易日
        - 如果向前找不到，向后查找最近的交易日

        Args:
            code: 股票代码
            date: 日期 (YYYYMMDD)
            max_days_back: 最多向前查找天数
            max_days_forward: 最多向后查找天数

        Returns:
            价格或None
        """
        # 1. 先尝试获取当天价格
        price = self._get_single_price(code, date)
        if price is not None:
            return price

        # 2. 向前查找
        dt_obj = datetime.strptime(date, '%Y%m%d')

        for i in range(1, max_days_back + 1):
            prev_date = (dt_obj - timedelta(days=i)).strftime('%Y%m%d')

            # 跳过周末（简单判断）
            day_of_week = (dt_obj - timedelta(days=i)).weekday()
            if day_of_week >= 5:  # 周六、周日
                continue

            price = self._get_single_price(code, prev_date)
            if price is not None:
                print(f"[DataManager] {code} {date} 无数据，使用 {prev_date} 价格: {price:.2f}")
                return price

        # 3. 向后查找
        for i in range(1, max_days_forward + 1):
            next_date = (dt_obj + timedelta(days=i)).strftime('%Y%m%d')

            # 跳过周末
            day_of_week = (dt_obj + timedelta(days=i)).weekday()
            if day_of_week >= 5:
                continue

            price = self._get_single_price(code, next_date)
            if price is not None:
                print(f"[DataManager] {code} {date} 无数据，使用 {next_date} 价格: {price:.2f}")
                return price

        print(f"[DataManager] {code} {date} 附近无可用价格数据")
        return None

    def _get_single_price(self, code: str, date: str) -> Optional[float]:
        """
        获取单个股票在单个日期的价格

        Args:
            code: 股票代码
            date: 日期 (YYYYMMDD)

        Returns:
            价格或None
        """
        # 1. 检查缓存
        cache_key = (date, code)
        if cache_key in self.price_cache:
            return self.price_cache[cache_key]

        # 2. 从DuckDB查询
        if self.duckdb_con:
            try:
                date_formatted = convert_date_format(date)
                query = f"""
                    SELECT close
                    FROM stock_daily
                    WHERE stock_code = '{code}'
                      AND date = '{date_formatted}'
                      AND period = '1d'
                """

                df = self.duckdb_con.execute(query).df()

                if not df.empty:
                    price = df.iloc[0]['close']
                    self.price_cache[cache_key] = price
                    return price

            except Exception as e:
                print(f"[DataManager] 单股价格查询失败: {e}")

        # 3. 从Tushare查询
        if self.tushare_pro:
            try:
                df = self.tushare_pro.daily(
                    ts_code=code,
                    trade_date=date,
                    fields='close'
                )

                if df is not None and not df.empty:
                    price = df.iloc[0]['close']
                    self.price_cache[cache_key] = price
                    return price

            except Exception as e:
                pass

        return None

    def check_if_delisted(self, code: str, date: str, check_days: int = 30) -> Optional[tuple]:
        """
        检查股票是否退市（连续N天无价格数据）

        Args:
            code: 股票代码
            date: 当前日期 (YYYYMMDD)
            check_days: 检查天数，默认30天

        Returns:
            None (未退市) 或 (last_trade_date, last_price) (已退市)
        """
        from datetime import datetime, timedelta

        dt_obj = datetime.strptime(date, '%Y%m%d')

        # 向前查找最近的有价格的日期
        for i in range(1, check_days + 1):
            check_date = (dt_obj - timedelta(days=i)).strftime('%Y%m%d')

            # 跳过周末
            day_of_week = (dt_obj - timedelta(days=i)).weekday()
            if day_of_week >= 5:  # 周六、周日
                continue

            price = self._get_single_price(code, check_date)
            if price is not None:
                # 找到了最近的价格，说明还没退市（或者刚退市）
                # 检查从那天到今天是否有交易日有数据
                for j in range(i):
                    between_date = (dt_obj - timedelta(days=j)).strftime('%Y%m%d')
                    day_of_week = (dt_obj - timedelta(days=j)).weekday()
                    if day_of_week >= 5:
                        continue

                    between_price = self._get_single_price(code, between_date)
                    if between_price is not None:
                        # 中间有价格数据，说明未退市
                        return None

                # 从找到的最近价格日期到现在都没有数据，判定为退市
                return (check_date, price)

        # 连续check_days都没找到价格，判定为退市
        return (None, None)

    def get_last_trade_date_and_price(self, code: str, date: str) -> Optional[tuple]:
        """
        获取股票的最后交易日和最后价格（用于退市处理）

        Args:
            code: 股票代码
            date: 当前日期 (YYYYMMDD)

        Returns:
            None (有价格) 或 (last_date, last_price) (最后交易日和价格)
        """
        from datetime import datetime, timedelta

        # 先尝试获取当前日期价格
        current_price = self.get_nearest_price(code, date)
        if current_price is not None:
            return None  # 有价格，未退市

        # 当前无价格，向前查找最后交易日
        dt_obj = datetime.strptime(date, '%Y%m%d')

        for i in range(1, 60):  # 最多向前查找60天
            check_date = (dt_obj - timedelta(days=i)).strftime('%Y%m%d')

            # 跳过周末
            day_of_week = (dt_obj - timedelta(days=i)).weekday()
            if day_of_week >= 5:
                continue

            price = self._get_single_price(code, check_date)
            if price is not None:
                return (check_date, price)

        # 无法找到任何历史价格
        return (None, None)

    def get_price_date(self, code: str, query_date: str) -> Optional[str]:
        """
        获取价格数据的实际日期（用于验证价格是否过期）

        Args:
            code: 股票代码
            query_date: 查询日期 (YYYYMMDD)

        Returns:
            价格数据的实际日期，如果无法获取则返回None
        """
        from datetime import datetime, timedelta

        dt_obj = datetime.strptime(query_date, '%Y%m%d')

        # 1. 先尝试获取当天的价格
        price = self._get_single_price(code, query_date)
        if price is not None:
            return query_date

        # 2. 向前查找最近的价格（最多7天）
        for i in range(1, 8):  # 7天
            check_date = (dt_obj - timedelta(days=i)).strftime('%Y%m%d')

            # 跳过周末
            day_of_week = (dt_obj - timedelta(days=i)).weekday()
            if day_of_week >= 5:
                continue

            price = self._get_single_price(code, check_date)
            if price is not None:
                return check_date

        return None

    def is_delisted(self, code: str, date: str, check_days: int = 30) -> tuple:
        """
        检查股票是否已退市（增强版）

        Args:
            code: 股票代码
            date: 当前日期 (YYYYMMDD)
            check_days: 检查天数，默认30天

        Returns:
            (is_delisted: bool, last_trade_date: Optional[str], last_price: Optional[float])
            - is_delisted: True表示已退市，False表示正常
            - last_trade_date: 最后交易日（如果已退市）
            - last_price: 最后价格（如果已退市）
        """
        from datetime import datetime, timedelta

        dt_obj = datetime.strptime(date, '%Y%m%d')

        # 1. 先检查当天是否有价格
        current_price = self._get_single_price(code, date)
        if current_price is not None:
            # 当天有价格，说明未退市
            return (False, None, None)

        # 2. 当天无价格，向前查找最后交易日
        last_trade_date = None
        last_price = None

        for i in range(1, check_days + 1):
            check_date = (dt_obj - timedelta(days=i)).strftime('%Y%m%d')

            # 跳过周末
            day_of_week = (dt_obj - timedelta(days=i)).weekday()
            if day_of_week >= 5:  # 周六、周日
                continue

            price = self._get_single_price(code, check_date)
            if price is not None:
                last_trade_date = check_date
                last_price = price
                break

        # 3. 判断是否退市
        if last_trade_date is None:
            # 连续check_days都没有价格，认为已退市且无价格数据
            return (True, None, None)

        # 4. 检查从最后交易日到今天是否有交易日有数据
        # 如果中间有交易日有数据，说明未退市（可能只是停牌）
        for j in range(1, i):
            between_date = (dt_obj - timedelta(days=j)).strftime('%Y%m%d')
            day_of_week = (dt_obj - timedelta(days=j)).weekday()
            if day_of_week >= 5:
                continue

            between_price = self._get_single_price(code, between_date)
            if between_price is not None:
                # 中间有价格数据，说明未退市（可能只是当天无数据）
                return (False, None, None)

        # 从最后交易日到现在都没有数据，判定为退市
        return (True, last_trade_date, last_price)

    def check_price_data_valid(self, code: str, date: str, max_days_diff: int = 7) -> tuple:
        """
        综合检查价格数据的有效性（包括是否退市）

        Args:
            code: 股票代码
            date: 查询日期 (YYYYMMDD)
            max_days_diff: 允许的最大天数差异，默认7天

        Returns:
            (is_valid: bool, reason: str, price_date: Optional[str], price: Optional[float])
            - is_valid: True表示数据有效，False表示无效
            - reason: 无效的原因（用于日志输出）
            - price_date: 价格数据的实际日期
            - price: 价格
        """
        from datetime import datetime, timedelta

        # 1. 检查是否退市
        is_delisted, last_trade_date, last_price = self.is_delisted(code, date)

        if is_delisted:
            if last_price is not None:
                return (False, f"已退市({last_trade_date}最后价格{last_price:.2f})", last_trade_date, last_price)
            else:
                return (False, "已退市且无历史价格数据", None, None)

        # 2. 获取价格和价格日期
        price = self.get_nearest_price(code, date)
        if price is None:
            return (False, "无价格数据", None, None)

        price_date = self.get_price_date(code, date)
        if price_date is None:
            return (False, "无法确定价格日期", None, None)

        # 3. 检查价格数据是否过期
        price_dt = datetime.strptime(price_date, '%Y%m%d')
        query_dt = datetime.strptime(date, '%Y%m%d')
        days_diff = (query_dt - price_dt).days

        if days_diff > max_days_diff:
            return (False, f"价格数据过期({price_date}，{days_diff}天前)", price_date, price)

        # 4. 所有检查通过
        return (True, "数据有效", price_date, price)

    # ==================== 辅助方法 ====================

    def get_index_components(self, index_code: str, date: str) -> List[str]:
        """
        获取指数成分股

        Args:
            index_code: 指数代码 (如 '399101.SZ')
            date: 查询日期 (YYYYMMDD)

        Returns:
            成分股代码列表
        """
        # 优先使用QMT
        if self.qmt_connected:
            try:
                # QMT获取指数成分股
                components = xtdata.get_instrument_detail(index_code)
                if components and 'Stock' in components:
                    stock_list = components['Stock']
                    if isinstance(stock_list, list):
                        return stock_list
                    elif isinstance(stock_list, str):
                        return [stock_list]
            except Exception as e:
                print(f"[DataManager] QMT获取成分股失败: {e}")

        # 备用：使用Tushare
        if self.tushare_pro:
            try:
                df = self.tushare_pro.index_weight(
                    index_code=index_code,
                    start_date=date,
                    end_date=date
                )

                if df is not None and not df.empty:
                    return df['con_code'].tolist()

            except Exception as e:
                print(f"[DataManager] Tushare获取成分股失败: {e}")

        # 备用2：从DuckDB获取所有A股（如果获取不到指数成分股）
        if self.duckdb_con:
            try:
                # 如果是中小100或中证500，返回所有股票
                if index_code in ['399101.SZ', '399101', '000905.SH', '000905']:
                    query = """
                        SELECT DISTINCT stock_code
                        FROM stock_daily
                        WHERE symbol_type = 'stock'
                        LIMIT 5000
                    """
                    df_stocks = self.duckdb_con.execute(query).df()
                    if not df_stocks.empty:
                        stock_list = df_stocks['stock_code'].tolist()
                        print(f"[DataManager] 从DuckDB获取全市场股票: {len(stock_list)} 只")
                        return stock_list
            except Exception as e:
                print(f"[DataManager] DuckDB获取成分股失败: {e}")

        return []

    def close(self):
        """关闭所有连接"""
        if self.duckdb_con:
            self.duckdb_con.close()
            self.duckdb_con = None

        self.tushare_pro = None
        self.price_cache.clear()
        self.fundamental_cache.clear()
