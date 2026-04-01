# -*- coding: utf-8 -*-
"""
Tushare数据源实现

从Tushare在线API获取股票数据
"""
import pandas as pd
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import time

from .base_source import BaseDataSource
from ..utils import validate_date


class TushareSource(BaseDataSource):
    """
    Tushare数据源

    从Tushare在线API获取实时和历史数据
    """

    def __init__(self, config: Dict):
        """
        初始化Tushare数据源

        Args:
            config: 配置字典，必须包含 'token' 字段
        """
        super().__init__(config)

        # 支持多token轮换（限流时自动切换）
        self.tokens = []
        primary = config.get('token')
        secondary = config.get('token_2')
        if primary:
            self.tokens.append(primary)
        if secondary:
            self.tokens.append(secondary)

        self.token = self.tokens[0] if self.tokens else None
        self._active_token_idx = 0
        self._connection = None  # Tushare API实例
        self.is_connected = False

        # API限流配置
        self.api_delay = config.get('api_delay', 0.3)  # 每次API调用间隔（秒）
        self.max_retries = config.get('max_retries', 3)  # 最大重试次数

    def connect(self) -> bool:
        """
        建立Tushare连接

        Returns:
            bool: 连接是否成功
        """
        try:
            import tushare as ts

            if not self.tokens:
                print("[TushareSource] 未提供Tushare Token")
                return False

            # 尝试每个token
            for i, token in enumerate(self.tokens):
                try:
                    ts.set_token(token)
                    conn = ts.pro_api()

                    # 测试连接
                    test_date = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
                    try:
                        conn.daily(ts_code='000001.SZ', trade_date=test_date,
                                   fields='ts_code,trade_date,close')
                    except:
                        conn.daily(ts_code='000001.SZ', trade_date='20230103',
                                   fields='ts_code,trade_date,close')

                    self._connection = conn
                    self.token = token
                    self._active_token_idx = i
                    self.is_connected = True
                    label = f"主token" if i == 0 else f"备用token({i})"
                    print(f"[TushareSource] {label}连接成功")
                    return True
                except Exception as e:
                    label = f"主token" if i == 0 else f"备用token({i})"
                    print(f"[TushareSource] {label}连接失败: {e}")
                    continue

            print("[TushareSource] 所有token均连接失败")
            self._connection = None
            self.is_connected = False
            return False

        except ImportError:
            print("[TushareSource] tushare模块未安装")
            return False

    def _is_rate_limited(self, error: Exception) -> bool:
        """判断异常是否为限流"""
        err_msg = str(error).lower()
        rate_limit_keywords = ['limit', 'rate', 'freq', 'exceed', '每分钟',
                               'restricted', 'timeout', 'too many', '频次']
        return any(kw in err_msg for kw in rate_limit_keywords)

    def _switch_token(self) -> bool:
        """
        切换到下一个token

        Returns:
            bool: 是否切换成功
        """
        if len(self.tokens) <= 1:
            return False

        import tushare as ts
        next_idx = (self._active_token_idx + 1) % len(self.tokens)
        next_token = self.tokens[next_idx]

        try:
            ts.set_token(next_token)
            self._connection = ts.pro_api()
            self.token = next_token
            self._active_token_idx = next_idx
            label = f"主token" if next_idx == 0 else f"备用token({next_idx})"
            print(f"[TushareSource] 已切换到{label}")
            return True
        except Exception as e:
            print(f"[TushareSource] 切换token失败: {e}")
            return False

    def _api_call_with_fallback(self, api_func, *args, **kwargs):
        """
        带token轮换的API调用

        遇到限流错误时自动切换到备用token重试

        Args:
            api_func: API调用函数
            *args, **kwargs: API参数

        Returns:
            API返回结果
        """
        last_error = None

        for attempt in range(len(self.tokens)):
            try:
                result = api_func(*args, **kwargs)
                return result
            except Exception as e:
                last_error = e
                if self._is_rate_limited(e):
                    print(f"[TushareSource] 请求被限流，尝试切换token...")
                    if not self._switch_token():
                        break
                    # 切换成功后重试
                    continue
                else:
                    # 非限流错误，不切换token，直接抛出
                    raise

        # 所有token都失败了
        raise last_error

    def get_price(self,
                  symbol: str,
                  start_date: str,
                  end_date: str,
                  period: str = '1d',
                  adjust: str = 'none') -> Optional[pd.DataFrame]:
        """
        从Tushare获取价格数据

        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 数据周期（仅支持'1d'）
            adjust: 复权类型（暂不支持，仅保留接口）

        Returns:
            DataFrame: 价格数据，包含列：symbol, date, open, high, low, close, vol, amount
        """
        if not self.is_available():
            return None

        try:
            # 验证日期格式
            if not validate_date(start_date) or not validate_date(end_date):
                print(f"[TushareSource] 日期格式错误: {start_date} - {end_date}")
                return None

            # 标准化股票代码
            symbol = self.normalize_symbol(symbol)

            # 调用API（带token轮换）
            df = self._api_call_with_fallback(
                self._connection.daily,
                ts_code=symbol,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                return None

            # 重命名列
            df.rename(columns={
                'trade_date': 'date',
                'vol': 'volume'
            }, inplace=True)

            # 选择需要的列
            df = df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'amount']]

            # 缓存数据
            cache_key = self.get_cache_key('price', symbol, start_date, end_date)
            self._cache[cache_key] = df
            self._last_used = datetime.now()

            # API限流延迟
            time.sleep(self.api_delay)

            return df

        except Exception as e:
            print(f"[TushareSource] 获取价格数据失败 ({symbol}): {e}")
            return None

    def get_fundamentals(self,
                         symbols: List[str],
                         date: str,
                         fields: Optional[List[str]] = None) -> Optional[pd.DataFrame]:
        """
        从Tushare获取基本面数据

        Args:
            symbols: 股票代码列表
            date: 查询日期 (YYYYMMDD)
            fields: 需要的字段列表

        Returns:
            DataFrame: 基本面数据
        """
        if not self.is_available():
            return None

        try:
            # 验证日期格式
            if not validate_date(date):
                print(f"[TushareSource] 日期格式错误: {date}")
                return None

            # 标准化股票代码
            symbols = [self.normalize_symbol(s) for s in symbols]

            # 默认字段
            if fields is None:
                fields = [
                    'ts_code', 'trade_date',
                    'circ_mv',  # 流通市值
                    'total_mv',  # 总市值
                    'pe',  # 市盈率
                    'pe_ttm',  # 市盈率TTM
                    'pb',  # 市净率
                    'ps',  # 市销率
                    'ps_ttm',  # 市销率TTM
                    'dv_ratio',  # 股息率
                    'total_share',  # 总股本
                    'float_share',  # 流通股本
                    'free_share',  # 自由流通股本
                    'total_mv',  # 总市值
                    'circ_mv'  # 流通市值
                ]

            # 检查缓存（缓存全市场数据）
            cache_key = ('tushare_fundamentals_all', date)
            if cache_key in self._cache:
                cached_df = self._cache[cache_key]
                # 从缓存中筛选需要的股票
                result = cached_df[cached_df['ts_code'].isin(symbols)].copy()
                if not result.empty:
                    result.set_index('ts_code', inplace=True)
                    return result

            # 构建字段列表
            fields_str = 'ts_code,trade_date,' + ','.join(fields)

            # 批量查询全市场数据（带token轮换）
            df = self._api_call_with_fallback(
                self._connection.daily_basic,
                trade_date=date,
                fields=fields_str
            )

            if df is None or df.empty:
                # 如果指定日期没有数据，尝试向前查找（最多3天）
                for i in range(1, 4):
                    try:
                        date_obj = datetime.strptime(date, '%Y%m%d')
                        prev_date = (date_obj - timedelta(days=i)).strftime('%Y%m%d')

                        df = self._api_call_with_fallback(
                            self._connection.daily_basic,
                            trade_date=prev_date,
                            fields=fields_str
                        )

                        if df is not None and not df.empty:
                            print(f"[TushareSource] {date}无数据，使用{prev_date}数据")
                            break
                    except:
                        continue

            if df is None or df.empty:
                print(f"[TushareSource] 获取基本面数据失败：{date}无数据")
                return None

            # 缓存全市场数据
            self._cache[cache_key] = df.copy()

            # 筛选需要的股票
            df_filtered = df[df['ts_code'].isin(symbols)].copy()
            df_filtered.set_index('ts_code', inplace=True)

            # API限流延迟
            time.sleep(self.api_delay)

            return df_filtered

        except Exception as e:
            print(f"[TushareSource] 获取基本面数据失败: {e}")
            return None

    def get_trading_dates(self,
                          start_date: str,
                          end_date: str) -> Optional[List[str]]:
        """
        从Tushare获取交易日历

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            List[str]: 交易日列表 (YYYYMMDD格式)
        """
        if not self.is_available():
            return None

        try:
            # 验证日期格式
            if not validate_date(start_date) or not validate_date(end_date):
                print(f"[TushareSource] 日期格式错误: {start_date} - {end_date}")
                return None

            # 获取交易日历（带token轮换）
            df = self._api_call_with_fallback(
                self._connection.trade_cal,
                exchange='SSE',
                start_date=start_date,
                end_date=end_date,
                is_open=1
            )

            if df is None or df.empty:
                return []

            trading_dates = df['cal_date'].tolist()

            # API限流延迟
            time.sleep(self.api_delay)

            return trading_dates

        except Exception as e:
            print(f"[TushareSource] 获取交易日历失败: {e}")
            return None

    def is_available(self) -> bool:
        """
        检查Tushare数据源是否可用

        Returns:
            bool: 数据源是否可用
        """
        if not self.is_connected or self._connection is None:
            return False

        try:
            # 简单测试：检查token是否有效
            return self.token is not None
        except Exception:
            return False

    def get_stock_list(self,
                       exchange: str = 'SSE',
                       list_status: str = 'L') -> Optional[List[str]]:
        """
        获取股票列表

        Args:
            exchange: 交易所 ('SSE'-上交所, 'SZSE'-深交所)
            list_status: 上市状态 ('L'-上市, 'D'-退市, 'P'-暂停上市)

        Returns:
            List[str]: 股票代码列表
        """
        if not self.is_available():
            return None

        try:
            # 获取股票列表（带token轮换）
            df = self._api_call_with_fallback(
                self._connection.stock_basic,
                exchange=exchange,
                list_status=list_status,
                fields='ts_code,name,area,industry,list_date'
            )

            if df is None or df.empty:
                return []

            # API限流延迟
            time.sleep(self.api_delay)

            return df['ts_code'].tolist()

        except Exception as e:
            print(f"[TushareSource] 获取股票列表失败: {e}")
            return None

    def get_index_list(self) -> Optional[pd.DataFrame]:
        """
        获取指数列表

        Returns:
            DataFrame: 指数列表
        """
        if not self.is_available():
            return None

        try:
            df = self._api_call_with_fallback(
                self._connection.index_basic,
                market='SSE',
                fields='ts_code,name,market,publisher,category,base_date,base_point,list_date'
            )

            if df is None or df.empty:
                return None

            # API限流延迟
            time.sleep(self.api_delay)

            return df

        except Exception as e:
            print(f"[TushareSource] 获取指数列表失败: {e}")
            return None

    def get_api_info(self) -> Dict:
        """
        获取API信息

        Returns:
            Dict: API信息
        """
        return {
            'source': 'Tushare',
            'token_count': len(self.tokens),
            'active_token_idx': self._active_token_idx,
            'active_token_prefix': self.token[:10] + '...' if self.token else None,
            'api_delay': self.api_delay,
            'max_retries': self.max_retries,
            'is_connected': self.is_connected
        }