# -*- coding: utf-8 -*-
"""
QMT数据源实现

从QMT（迅投XTQuant）获取股票数据
"""
import pandas as pd
from typing import Optional, List, Dict
from datetime import datetime, timedelta

from .base_source import BaseDataSource
from ..utils import validate_date


class QMTSource(BaseDataSource):
    """
    QMT数据源

    从QMT（迅投XTQuant）获取实时和历史数据
    """

    def __init__(self, config: Dict):
        """
        初始化QMT数据源

        Args:
            config: 配置字典
        """
        super().__init__(config)

        self.qmt_path = config.get('path', None)
        self._connection = None  # QMT连接（实际上不需要连接对象）
        self.is_connected = False

    def connect(self) -> bool:
        """
        建立QMT连接

        Returns:
            bool: 连接是否成功
        """
        try:
            from xtquant import xtdata

            # 测试连接 - 获取一只股票的数据
            test_data = xtdata.get_market_data_ex(
                ['000001.SZ'],
                period='1d',
                start_time='20230101',
                end_time='20230102'
            )

            self.is_connected = True
            print("[QMTSource] 连接成功")
            return True

        except ImportError:
            print("[QMTSource] xtquant模块未安装")
            return False
        except Exception as e:
            print(f"[QMTSource] 连接失败: {e}")
            self.is_connected = False
            return False

    def get_price(self,
                  symbol: str,
                  start_date: str,
                  end_date: str,
                  period: str = '1d',
                  adjust: str = 'none') -> Optional[pd.DataFrame]:
        """
        从QMT获取价格数据

        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 数据周期 ('1d', '1w', '1m')
            adjust: 复权类型（暂不支持，仅保留接口）

        Returns:
            DataFrame: 价格数据，包含列：symbol, date, open, high, low, close, volume, amount
        """
        if not self.is_available():
            return None

        try:
            from xtquant import xtdata

            # 验证日期格式
            if not validate_date(start_date) or not validate_date(end_date):
                print(f"[QMTSource] 日期格式错误: {start_date} - {end_date}")
                return None

            # 标准化股票代码
            symbol = self.normalize_symbol(symbol)

            # 调用QMT API
            data = xtdata.get_market_data_ex(
                stock_list=[symbol],
                period=period,
                start_time=start_date,
                end_time=end_date
            )

            if not data or symbol not in data or data[symbol] is None:
                return None

            # 转换为DataFrame
            df = data[symbol].reset_index()

            # 重命名列
            df.rename(columns={'time': 'date'}, inplace=True)
            df['symbol'] = symbol

            # 选择需要的列
            available_columns = ['symbol', 'date']
            required_columns = ['open', 'high', 'low', 'close', 'volume', 'amount']

            for col in required_columns:
                if col in df.columns:
                    available_columns.append(col)

            df = df[available_columns]

            # 缓存数据
            cache_key = self.get_cache_key('price', symbol, start_date, end_date)
            self._cache[cache_key] = df
            self._last_used = datetime.now()

            return df

        except Exception as e:
            print(f"[QMTSource] 获取价格数据失败 ({symbol}): {e}")
            return None

    def get_fundamentals(self,
                         symbols: List[str],
                         date: str,
                         fields: Optional[List[str]] = None) -> Optional[pd.DataFrame]:
        """
        从QMT获取基本面数据

        注意：QMT主要是股本数据，市值需要通过股本×价格计算

        Args:
            symbols: 股票代码列表
            date: 查询日期 (YYYYMMDD)
            fields: 需要的字段列表（支持: circ_mv-流通市值, total_mv-总市值）

        Returns:
            DataFrame: 基本面数据
        """
        if not self.is_available():
            return None

        try:
            from xtquant import xtdata

            # 验证日期格式
            if not validate_date(date):
                print(f"[QMTSource] 日期格式错误: {date}")
                return None

            # 标准化股票代码
            symbols = [self.normalize_symbol(s) for s in symbols]

            # 默认字段
            if fields is None:
                fields = ['circ_mv', 'total_mv']

            result_data = []

            for symbol in symbols:
                try:
                    # 获取股票基本信息（股本数据）
                    info = xtdata.get_instrument_detail(symbol)

                    # 检查是否有有效的股本数据
                    if not info or 'FloatVolume' not in info or info.get('FloatVolume', 0) == 0:
                        # QMT mini版本可能不支持股本数据
                        continue

                    # 获取收盘价
                    close_price = self._get_close_price(symbol, date)

                    if close_price is None:
                        # 无法获取价格，跳过该股票
                        continue

                    # 计算市值
                    row_data = {'symbol': symbol}

                    # 流通股本（股）转成（万股）
                    float_volume = info['FloatVolume'] / 10000  # 股 -> 万股

                    # 总股本（股）转成（万股）
                    total_volume = info['TotalVolume'] / 10000  # 股 -> 万股

                    if 'circ_mv' in fields:
                        # 流通市值（万元）= 流通股本（万股）× 收盘价（元）
                        circ_mv = float_volume * close_price
                        row_data['circ_mv'] = circ_mv

                    if 'total_mv' in fields:
                        # 总市值（万元）= 总股本（万股）× 收盘价（元）
                        row_data['total_mv'] = total_volume * close_price

                    result_data.append(row_data)

                except Exception as e:
                    print(f"[QMTSource] 获取{symbol}基本面数据失败: {e}")
                    continue

            if not result_data:
                return None

            result = pd.DataFrame(result_data)
            result.set_index('symbol', inplace=True)

            return result

        except Exception as e:
            print(f"[QMTSource] 获取基本面数据失败: {e}")
            return None

    def _get_close_price(self, symbol: str, date: str, max_days_back: int = 10) -> Optional[float]:
        """
        获取收盘价（带向前查找）

        Args:
            symbol: 股票代码
            date: 日期 (YYYYMMDD)
            max_days_back: 最多回退天数

        Returns:
            收盘价或None
        """
        try:
            from xtquant import xtdata
            from datetime import datetime as dt

            # 尝试获取当天价格
            data = xtdata.get_market_data_ex(
                stock_list=[symbol],
                period='1d',
                start_time=date,
                end_time=date
            )

            if data and symbol in data and data[symbol] is not None and not data[symbol].empty:
                return float(data[symbol]['close'].iloc[-1])

            # 如果当天没有数据，尝试向前查找
            for i in range(1, max_days_back + 1):
                try:
                    date_obj = dt.strptime(date, '%Y%m%d')
                    prev_date = (date_obj - timedelta(days=i)).strftime('%Y%m%d')

                    data = xtdata.get_market_data_ex(
                        stock_list=[symbol],
                        period='1d',
                        start_time=prev_date,
                        end_time=prev_date
                    )

                    if data and symbol in data and data[symbol] is not None and not data[symbol].empty:
                        return float(data[symbol]['close'].iloc[-1])
                except:
                    continue

            return None

        except Exception as e:
            print(f"[QMTSource] 获取{symbol} {date}收盘价失败: {e}")
            return None

    def get_trading_dates(self,
                          start_date: str,
                          end_date: str) -> Optional[List[str]]:
        """
        从QMT获取交易日历

        注意：QMT可能不提供直接的交易日历接口

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            List[str]: 交易日列表 (YYYYMMDD格式)
        """
        if not self.is_available():
            return None

        try:
            from xtquant import xtdata

            # 验证日期格式
            if not validate_date(start_date) or not validate_date(end_date):
                print(f"[QMTSource] 日期格式错误: {start_date} - {end_date}")
                return None

            # QMT可能没有直接的交易日历接口
            # 这里返回None，表示QMT不支持此功能
            print("[QMTSource] QMT可能不提供交易日历接口")
            return None

        except Exception as e:
            print(f"[QMTSource] 获取交易日历失败: {e}")
            return None

    def is_available(self) -> bool:
        """
        检查QMT数据源是否可用

        Returns:
            bool: 数据源是否可用
        """
        if not self.is_connected:
            return False

        try:
            from xtquant import xtdata
            # 简单测试：尝试获取一只股票的数据
            test_data = xtdata.get_market_data_ex(
                ['000001.SZ'],
                period='1d',
                start_time='20230101',
                end_time='20230101'
            )
            return True
        except Exception:
            return False

    def get_stock_list(self, market: str = 'stock') -> Optional[List[str]]:
        """
        获取股票列表

        Args:
            market: 市场类型 ('stock', 'index', 'fund')

        Returns:
            List[str]: 股票代码列表
        """
        if not self.is_available():
            return None

        try:
            from xtquant import xtdata

            # 获取股票列表
            stock_list = xtdata.get_stock_list_in_sector(market)

            if not stock_list:
                return []

            return stock_list

        except Exception as e:
            print(f"[QMTSource] 获取股票列表失败: {e}")
            return None

    def get_instrument_info(self, symbol: str) -> Optional[Dict]:
        """
        获取证券信息

        Args:
            symbol: 股票代码

        Returns:
            Dict: 证券信息
        """
        if not self.is_available():
            return None

        try:
            from xtquant import xtdata

            # 标准化股票代码
            symbol = self.normalize_symbol(symbol)

            # 获取证券信息
            info = xtdata.get_instrument_detail(symbol)

            return info

        except Exception as e:
            print(f"[QMTSource] 获取证券信息失败: {e}")
            return None

    def get_qmt_info(self) -> Dict:
        """
        获取QMT信息

        Returns:
            Dict: QMT信息
        """
        return {
            'source': 'QMT (XTQuant)',
            'is_connected': self.is_connected,
            'qmt_path': self.qmt_path,
        }