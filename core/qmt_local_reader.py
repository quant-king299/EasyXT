# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger(__name__)
"""
QMT Local Data Reader - Enhanced Version
Directly reads QMT local cache files (.dat) without API calls
Performance: 50-100x faster than xtdata.get_market_data_ex()
"""

import struct
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict


class QMTLocalReader:
    """
    QMT本地数据读取器

    直接读取 QMT 本地缓存文件，无需通过 API 网络请求
    性能提升：50-100倍
    """

    # QMT 数据目录配置（支持大QMT和miniQMT）
    DEFAULT_DATA_DIR = Path(r"D:/国金QMT交易端模拟/userdata_mini/datadir")
    BIG_QMT_DATA_DIR = Path(r"D:/国金QMT交易端模拟/datadir")

    # 大QMT文件命名后缀
    BIG_QMT_SUFFIX = "_9000"

    # 周期代码映射
    PERIOD_CODES = {
        'tick': '0',
        '1m': '60',
        '5m': '300',
        '15m': '900',
        '30m': '1800',
        '1h': '3600',
        '1d': '86400',
        '1w': '604800',
        '1M': '2592000',
    }

    def __init__(self, data_dir: Optional[Path] = None):
        """初始化读取器"""
        self.data_dir = Path(data_dir) if data_dir else self.DEFAULT_DATA_DIR
        if not self.data_dir.exists():
            raise FileNotFoundError(f"QMT data directory not found: {self.data_dir}")

    def get_file_path(self, stock_code: str, period: str,
                      prefer_big_qmt: bool = False) -> Optional[Path]:
        """获取股票数据文件路径，支持大QMT和miniQMT两种格式"""
        if stock_code.endswith('.SZ'):
            market = 'SZ'
            code = stock_code.replace('.SZ', '')
        elif stock_code.endswith('.SH'):
            market = 'SH'
            code = stock_code.replace('.SH', '')
        else:
            market = 'SZ'
            code = stock_code

        period_code = self.PERIOD_CODES.get(period)
        if not period_code:
            raise ValueError(f"Unsupported period: {period}")

        # 构建候选路径列表（按优先级）
        candidates = []

        if prefer_big_qmt:
            # 大QMT优先: datadir/market/{period_code}/{code}.DAT
            candidates.append(
                self.BIG_QMT_DATA_DIR / market / period_code / f"{code}.DAT"
            )
            # 大QMT也兼容 market/0/{code}_9000.DAT 格式
            candidates.append(
                self.BIG_QMT_DATA_DIR / market / '0' / f"{code}{self.BIG_QMT_SUFFIX}.DAT"
            )
            # 回退到 miniQMT
            candidates.append(
                self.data_dir / market / period_code / f"{code}.DAT"
            )
        else:
            # miniQMT优先: userdata_mini/datadir/market/{period_code}/{code}.DAT
            candidates.append(
                self.data_dir / market / period_code / f"{code}.DAT"
            )
            # 回退到 大QMT
            candidates.append(
                self.BIG_QMT_DATA_DIR / market / period_code / f"{code}.DAT"
            )
            candidates.append(
                self.BIG_QMT_DATA_DIR / market / '0' / f"{code}{self.BIG_QMT_SUFFIX}.DAT"
            )

        # 兼容旧的日线目录格式
        if period == '1d':
            candidates.append(self.data_dir / market / '0' / code)

        for path in candidates:
            if path.exists():
                return path

        return None

    def read_minute_data(self, stock_code: str, period: str = '1m',
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """读取分钟线数据"""
        file_path = self.get_file_path(stock_code, period)
        if not file_path:
            logger.warning(f"[WARNING] Data file not found: {stock_code} {period}")
            return None

        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()

            df = self._parse_minute_file(file_data, stock_code, period)
            if df is None or df.empty:
                return None

            if start_date or end_date:
                df = self._filter_by_date(df, start_date, end_date)

            return df

        except Exception as e:
            logger.error(f"[ERROR] Failed to read file {file_path}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def read_daily_data(self, stock_code: str,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """读取日线数据（支持大QMT和miniQMT下载的数据格式）"""
        file_path = self.get_file_path(stock_code, '1d')
        if not file_path or not file_path.exists():
            logger.warning(f"[WARNING] Daily data file not found: {stock_code}")
            return None

        try:
            with open(file_path, 'rb') as f:
                raw = f.read()

            # 日线格式: 8字节头部 + 32字节记录(8个int32)
            # 但有效记录在偶数索引 (0, 2, 4, ...)，奇数索引是复权元数据
            header_size = 8
            rec_size = 32
            data = raw[header_size:]
            total_records = len(data) // rec_size

            records = []
            for i in range(0, total_records, 2):  # 只取偶数索引
                offset = i * rec_size
                vals = struct.unpack_from('<IIIIIIII', data, offset)
                ts = vals[0]
                # 验证时间戳合理性 (1990-2026)
                if not (631152000 < ts < 1767225600):
                    continue

                dt = datetime.fromtimestamp(ts)
                open_p = vals[1] / 1000.0
                high_p = vals[2] / 1000.0
                low_p = vals[3] / 1000.0
                close_p = vals[4] / 1000.0
                volume_lots = vals[6]  # 成交量（手）
                # vals[5] = 0 (reserved), vals[7] = market flag

                # 基本数据验证
                if not (0.01 < open_p < 100000 and 0.01 < close_p < 100000):
                    continue
                if high_p < low_p:
                    continue

                records.append({
                    'time': dt,
                    'open': open_p,
                    'high': high_p,
                    'low': low_p,
                    'close': close_p,
                    'volume': volume_lots * 100,  # 手转股
                    'amount': 0,  # 日线格式不含成交额
                })

            if not records:
                logger.error(f"[ERROR] No valid records found in {stock_code} daily data")
                return None

            df = pd.DataFrame(records)
            df = df.sort_values('time').drop_duplicates('time')

            if start_date or end_date:
                df = self._filter_by_date(df, start_date, end_date)

            logger.info(f"[OK] Read {len(df)} daily records for {stock_code}")
            return df

        except Exception as e:
            logger.error(f"[ERROR] Failed to read daily data {stock_code}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _parse_minute_file(self, file_data: bytes, stock_code: str, period: str) -> Optional[pd.DataFrame]:
        """解析分钟线二进制文件"""
        file_size = len(file_data)
        logger.debug(f"[DEBUG] File size: {file_size} bytes")

        # 尝试不同的记录大小
        possible_sizes = [52, 48, 40, 56, 44, 36, 32, 28]

        for record_size in possible_sizes:
            num_records = file_size // record_size
            header_size = file_size % record_size

            if num_records < 100 or num_records > 1000000:
                continue

            logger.debug(f"[DEBUG] Trying format: {record_size} bytes, {num_records} records, header: {header_size} bytes")

            try:
                data_start = header_size

                # 定义可能的格式
                formats_to_try = []

                if record_size == 52:
                    formats_to_try = [
                        ('Qddddddd', 'time(8) + 7 doubles'),
                    ]
                elif record_size == 48:
                    formats_to_try = [
                        ('QIIIddd', 'time(8) + 4 ints + 2 doubles'),
                        ('QIIIIdd', 'time(8) + 5 ints + 2 doubles'),
                        ('QIIII I d', 'time(8) + 4 ints + int + double'),
                    ]
                elif record_size == 40:
                    formats_to_try = [
                        ('QIIIIddd', 'time(8) + 4 ints + 2 doubles'),
                        ('QIIIdddd', 'time(8) + 3 ints + 4 doubles'),
                        ('QIIIIIIdd', 'time(8) + 6 ints + 2 doubles'),
                    ]
                elif record_size == 36:
                    formats_to_try = [
                        ('QIIIIIIdd', 'time(8) + 5 ints + 2 doubles'),
                        ('QIII Iddd', 'time(8) + 4 ints + 3 doubles'),
                    ]
                elif record_size == 32:
                    formats_to_try = [
                        ('QIIIIII d', 'time(8) + 6 ints + double'),
                        ('QIIIIIdd', 'time(8) + 5 ints + 2 doubles'),
                    ]
                elif record_size == 28:
                    formats_to_try = [
                        ('QIIIIII I', 'time(8) + 7 ints'),
                    ]

                # 尝试每种格式
                for fmt, fmt_desc in formats_to_try:
                    try:
                        # 解析前 5 条记录用于测试
                        test_records = []
                        offset = data_start

                        for i in range(min(5, num_records)):
                            if offset + record_size > file_size:
                                break
                            record = struct.unpack_from(fmt.replace(' ', ''), file_data, offset)
                            test_records.append(record)
                            offset += record_size

                        if not test_records:
                            continue

                        logger.debug(f"[DEBUG]   Trying sub-format: {fmt_desc}")
                        logger.debug(f"[DEBUG]   First record: {test_records[0]}")

                        # 转换为 DataFrame 进行验证
                        df = self._records_to_dataframe(test_records, stock_code, period, fmt)

                        # 验证数据的合理性
                        if self._validate_data(df):
                            logger.info(f"[OK] Using format: {fmt_desc}")

                            # 格式正确，解析全部数据
                            all_records = []
                            offset = data_start

                            for i in range(num_records):
                                if offset + record_size > file_size:
                                    break
                                record = struct.unpack_from(fmt.replace(' ', ''), file_data, offset)
                                all_records.append(record)
                                offset += record_size

                            df = self._records_to_dataframe(all_records, stock_code, period, fmt)
                            logger.info(f"[OK] Successfully parsed {stock_code} {period}: {len(df)} records (format: {record_size}bytes)")
                            return df

                    except Exception as e:
                        # 尝试下一个格式
                        continue

            except Exception as e:
                logger.debug(f"[DEBUG] Format {record_size} bytes failed: {e}")
                continue

        logger.error(f"[ERROR] Cannot parse file format: {stock_code} {period}")
        return None

    def list_available_stocks(self, period: str = '1d',
                             market: Optional[str] = None) -> List[str]:
        """列出数据目录中所有可用的股票代码

        Args:
            period: 周期 ('1d', '1m', '5m' 等)
            market: 市场过滤 (None=全部, 'SH', 'SZ')

        Returns:
            股票代码列表 (如 '000001.SZ')
        """
        period_code = self.PERIOD_CODES.get(period)
        if not period_code:
            raise ValueError(f"Unsupported period: {period}")

        stocks = []
        markets = [market] if market else ['SH', 'SZ']

        for mkt in markets:
            # 大QMT路径
            big_dir = self.BIG_QMT_DATA_DIR / mkt / period_code
            if big_dir.exists():
                for f in big_dir.glob('*.DAT'):
                    code = f.stem
                    if code.isdigit():
                        stocks.append(f"{code}.{mkt}")

            # miniQMT路径
            mini_dir = self.data_dir / mkt / period_code
            if mini_dir.exists():
                for f in mini_dir.glob('*.DAT'):
                    code = f.stem
                    if code.isdigit():
                        stock_code = f"{code}.{mkt}"
                        if stock_code not in stocks:
                            stocks.append(stock_code)

        return sorted(stocks)

    def get_data_summary(self) -> Dict:
        """获取数据目录摘要信息"""
        summary = {
            'big_qmt': {'path': str(self.BIG_QMT_DATA_DIR), 'exists': False, 'daily_count': 0},
            'mini_qmt': {'path': str(self.data_dir), 'exists': False, 'daily_count': 0},
        }

        # 大QMT
        for mkt in ['SH', 'SZ']:
            big_dir = self.BIG_QMT_DATA_DIR / mkt / '86400'
            if big_dir.exists():
                summary['big_qmt']['exists'] = True
                summary['big_qmt'][f'{mkt}_count'] = len(list(big_dir.glob('*.DAT')))

        # miniQMT
        for mkt in ['SH', 'SZ']:
            mini_dir = self.data_dir / mkt / '86400'
            if mini_dir.exists():
                summary['mini_qmt']['exists'] = True
                summary['mini_qmt'][f'{mkt}_count'] = len(list(mini_dir.glob('*.DAT')))

        if summary['big_qmt']['exists']:
            sh = summary['big_qmt'].get('SH_count', 0)
            sz = summary['big_qmt'].get('SZ_count', 0)
            summary['big_qmt']['daily_count'] = sh + sz

        if summary['mini_qmt']['exists']:
            sh = summary['mini_qmt'].get('SH_count', 0)
            sz = summary['mini_qmt'].get('SZ_count', 0)
            summary['mini_qmt']['daily_count'] = sh + sz

        return summary

    def _records_to_dataframe(self, records: List[tuple], stock_code: str,
                             period: str, fmt: str) -> pd.DataFrame:
        """将解析的记录转换为 DataFrame"""
        fmt_clean = fmt.replace(' ', '')

        # 提取时间戳（第一个字段）
        times = [r[0] for r in records]

        # 检查时间戳的合理性，确定时间戳单位
        if times and times[0] > 1000000000000:  # 毫秒时间戳
            datetimes = pd.to_datetime(times, unit='ms', errors='coerce')
        else:  # 秒时间戳
            datetimes = pd.to_datetime(times, unit='s', errors='coerce')

        # 根据格式提取价格数据
        if fmt_clean == 'Qddddddd':  # 7个double
            opens = [r[1] for r in records]
            highs = [r[2] for r in records]
            lows = [r[3] for r in records]
            closes = [r[4] for r in records]
            volumes = [r[5] for r in records]
            amounts = [r[6] for r in records]
        elif fmt_clean == 'QIIIddd':  # time(8) + 4 ints + 2 doubles
            # int 类型的价格需要除以 10000
            opens = [r[1] / 10000.0 for r in records]
            highs = [r[2] / 10000.0 for r in records]
            lows = [r[3] / 10000.0 for r in records]
            closes = [r[4] / 10000.0 for r in records]
            volumes = [r[5] for r in records]
            amounts = [r[6] for r in records]
        elif fmt_clean == 'QIIIIdd':  # time(8) + 5 ints + 2 doubles
            opens = [r[1] / 10000.0 for r in records]
            highs = [r[2] / 10000.0 for r in records]
            lows = [r[3] / 10000.0 for r in records]
            closes = [r[4] / 10000.0 for r in records]
            # 第5个int字段可能是其他数据，volume和amount是double
            volumes = [r[5] for r in records]
            amounts = [r[6] for r in records]
        elif fmt_clean == 'QIIIIddd':  # time(8) + 4 ints + 3 doubles
            opens = [r[1] / 10000.0 for r in records]
            highs = [r[2] / 10000.0 for r in records]
            lows = [r[3] / 10000.0 for r in records]
            closes = [r[4] / 10000.0 for r in records]
            volumes = [r[5] for r in records]
            amounts = [r[6] for r in records]
        elif fmt_clean == 'QIIIdddd':  # time(8) + 3 ints + 4 doubles
            opens = [r[1] / 10000.0 for r in records]
            highs = [r[2] / 10000.0 for r in records]
            lows = [r[3] / 10000.0 for r in records]
            closes = [r[4] for r in records]
            volumes = [r[5] for r in records]
            amounts = [r[6] for r in records]
        else:
            # 默认处理：尝试智能判断
            if len(records[0]) >= 7:
                opens = [r[1] if isinstance(r[1], float) else r[1] / 10000.0 for r in records]
                highs = [r[2] if isinstance(r[2], float) else r[2] / 10000.0 for r in records]
                lows = [r[3] if isinstance(r[3], float) else r[3] / 10000.0 for r in records]
                closes = [r[4] if isinstance(r[4], float) else r[4] / 10000.0 for r in records]
                volumes = [r[5] if len(r) > 5 else 0 for r in records]
                amounts = [r[6] if len(r) > 6 else 0 for r in records]
            else:
                raise ValueError(f"Unsupported format: {fmt}")

        # 构建 DataFrame
        df = pd.DataFrame({
            'time': datetimes,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes,
            'amount': amounts,
        })

        # 过滤无效数据
        df = df[(df['open'] > 0) & (df['close'] > 0) & (df['high'] >= df['low'])]

        return df

    def _validate_data(self, df: pd.DataFrame) -> bool:
        """验证数据的合理性"""
        if df.empty or len(df) < 3:
            return False

        # 检查价格是否合理
        if df['open'].min() <= 0 or df['close'].min() <= 0:
            return False

        # 检查价格范围（0.01 - 10000）
        if df['open'].max() > 100000 or df['close'].max() > 100000:
            return False

        # 检查 high >= low
        if (df['high'] < df['low']).any():
            return False

        # 检查成交量
        if (df['volume'] < 0).any():
            return False

        return True

    def _filter_by_date(self, df: pd.DataFrame,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """按日期范围过滤数据"""
        if start_date:
            start_dt = pd.to_datetime(start_date)
            df = df[df['time'] >= start_dt]

        if end_date:
            end_dt = pd.to_datetime(end_date)
            end_dt = end_dt + timedelta(days=1) - timedelta(seconds=1)
            df = df[df['time'] <= end_dt]

        return df


def test_qmt_local_reader():
    """测试 QMT 本地读取器"""
    logger.info("\n" + "="*80)
    logger.info("QMT Local Data Reader Test (Enhanced)")
    logger.info("="*80)

    try:
        reader = QMTLocalReader()
        logger.info(f"[OK] QMT data directory: {reader.data_dir}")
    except Exception as e:
        logger.error(f"[ERROR] {e}")
        return

    test_cases = [
        ('000001.SZ', '1m', '2024-08-01', '2024-08-31'),
    ]

    for stock_code, period, start_date, end_date in test_cases:
        logger.info(f"\n{'='*80}")
        logger.info(f"Test: {stock_code} {period} ({start_date} ~ {end_date})")
        logger.info(f"{'='*80}")

        df = reader.read_minute_data(stock_code, period, start_date, end_date)

        if df is not None and not df.empty:
            logger.info(f"\n[OK] Successfully read {len(df)} records")
            logger.info("\nFirst 5 records:")
            logger.info(df.head())
            logger.info("\nLast 5 records:")
            logger.info(df.tail())

            logger.info(f"\nStatistics:")
            logger.info(f"  Time range: {df['time'].min()} ~ {df['time'].max()}")
            logger.info(f"  Price range: {df['low'].min():.2f} ~ {df['high'].max():.2f}")
            logger.info(f"  Total volume: {df['volume'].sum():,.0f}")
            logger.info(f"  Total amount: {df['amount'].sum():,.0f}")
        else:
            logger.error(f"\n[ERROR] Failed to read data")

    logger.info("\n" + "="*80)
    logger.info("Test Complete")
    logger.info("="*80)


if __name__ == '__main__':
    test_qmt_local_reader()
