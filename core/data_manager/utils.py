# -*- coding: utf-8 -*-
"""
数据管理工具函数

提供日期处理、股票代码处理、数据验证等工具
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Union
import re


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
    except Exception as e:
        print(f"[DateUtils] 日期格式转换失败: {e}")
        return dt_str


def get_trading_date_range(start_date: str,
                           end_date: str,
                           date_format: str = '%Y%m%d') -> List[str]:
    """
    获取日期范围内的所有日期（包括非交易日）

    Args:
        start_date: 开始日期
        end_date: 结束日期
        date_format: 日期格式

    Returns:
        List[str]: 日期列表
    """
    try:
        start = datetime.strptime(start_date, '%Y%m%d')
        end = datetime.strptime(end_date, '%Y%m%d')

        dates = []
        current = start
        while current <= end:
            dates.append(current.strftime(date_format))
            current += timedelta(days=1)

        return dates
    except Exception as e:
        print(f"[DateUtils] 生成日期范围失败: {e}")
        return []


def validate_date(date_str: str) -> bool:
    """
    验证日期字符串是否有效

    Args:
        date_str: 日期字符串（YYYYMMDD格式）

    Returns:
        bool: 是否有效
    """
    try:
        datetime.strptime(date_str, '%Y%m%d')
        return True
    except ValueError:
        return False


def normalize_symbol(symbol) -> str:
    """
    标准化股票代码格式

    Args:
        symbol: 股票代码（支持 str, int, float 等）

    Returns:
        str: 标准化后的股票代码（带.SZ或.SH后缀）
    """
    # 类型转换：支持各种类型的股票代码
    if isinstance(symbol, (int, float)):
        # 如果是数字，先转换为字符串
        # 对于 float，去掉小数点（如 600000.0 -> 600000）
        if isinstance(symbol, float) and symbol.is_integer():
            symbol = str(int(symbol))
        else:
            symbol = str(symbol)
    elif not isinstance(symbol, str):
        symbol = str(symbol)

    symbol = symbol.strip().upper()

    # 如果已经有后缀，直接返回
    if '.' in symbol:
        return symbol

    # 6位数字代码，添加默认后缀
    if len(symbol) == 6 and symbol.isdigit():
        if symbol.startswith('6'):
            return f"{symbol}.SH"  # 上海股票
        elif symbol.startswith(('0', '3')):
            return f"{symbol}.SZ"  # 深圳股票

    return symbol


def normalize_symbols(symbols: Union[str, List[str]]) -> List[str]:
    """
    批量标准化股票代码

    Args:
        symbols: 单个或多个股票代码

    Returns:
        List[str]: 标准化后的股票代码列表
    """
    if isinstance(symbols, str):
        symbols = [symbols]

    return [normalize_symbol(s) for s in symbols]


def validate_symbol(symbol: str) -> bool:
    """
    验证股票代码格式

    Args:
        symbol: 股票代码

    Returns:
        bool: 格式是否正确
    """
    # 支持格式：6位数字 或 6位数字.后缀
    pattern = r'^\d{6}(\.(SZ|SH))?$'
    return bool(re.match(pattern, symbol.upper()))


def is_sh_stock(symbol: str) -> bool:
    """
    判断是否为上海股票

    Args:
        symbol: 股票代码

    Returns:
        bool: 是否为上海股票
    """
    return symbol.startswith('6') or '.SH' in symbol.upper()


def is_sz_stock(symbol: str) -> bool:
    """
    判断是否为深圳股票

    Args:
        symbol: 股票代码

    Returns:
        bool: 是否为深圳股票
    """
    return symbol.startswith(('0', '3')) or '.SZ' in symbol.upper()


def merge_dataframes(dfs: List[pd.DataFrame],
                    on: str = 'date',
                    how: str = 'outer') -> Optional[pd.DataFrame]:
    """
    合并多个DataFrame

    Args:
        dfs: DataFrame列表
        on: 合并键
        how: 合并方式

    Returns:
        合并后的DataFrame
    """
    if not dfs:
        return None

    if len(dfs) == 1:
        return dfs[0].copy()

    try:
        result = dfs[0]
        for df in dfs[1:]:
            result = pd.merge(result, df, on=on, how=how)
        return result
    except Exception as e:
        print(f"[DataUtils] 合并DataFrame失败: {e}")
        return None


def validate_price_data(df: pd.DataFrame) -> bool:
    """
    验证价格数据是否有效

    Args:
        df: 价格数据DataFrame

    Returns:
        bool: 数据是否有效
    """
    if df is None or df.empty:
        return False

    # 检查必要的列
    required_columns = ['date', 'close']
    if not all(col in df.columns for col in required_columns):
        return False

    # 检查是否有无效价格
    if (df['close'] <= 0).any():
        return False

    return True


def remove_duplicate_data(df: pd.DataFrame,
                          subset: Optional[List[str]] = None) -> pd.DataFrame:
    """
    移除重复数据

    Args:
        df: 数据DataFrame
        subset: 用于判断重复的列

    Returns:
        去重后的DataFrame
    """
    if df is None or df.empty:
        return df

    if subset is None:
        subset = ['date', 'symbol'] if 'symbol' in df.columns else ['date']

    return df.drop_duplicates(subset=subset, keep='last')


def sort_by_date(df: pd.DataFrame,
                 date_column: str = 'date',
                 ascending: bool = True) -> pd.DataFrame:
    """
    按日期排序数据

    Args:
        df: 数据DataFrame
        date_column: 日期列名
        ascending: 是否升序

    Returns:
        排序后的DataFrame
    """
    if df is None or df.empty:
        return df

    try:
        return df.sort_values(by=date_column, ascending=ascending).reset_index(drop=True)
    except Exception as e:
        print(f"[DataUtils] 按日期排序失败: {e}")
        return df


def fill_missing_data(df: pd.DataFrame,
                     method: str = 'ffill') -> pd.DataFrame:
    """
    填充缺失数据

    Args:
        df: 数据DataFrame
        method: 填充方法 ('ffill', 'bfill', 'interpolate')

    Returns:
        填充后的DataFrame
    """
    if df is None or df.empty:
        return df

    try:
        if method == 'ffill':
            return df.fillna(method='ffill')
        elif method == 'bfill':
            return df.fillna(method='bfill')
        elif method == 'interpolate':
            return df.interpolate()
        else:
            return df
    except Exception as e:
        print(f"[DataUtils] 填充缺失数据失败: {e}")
        return df


def calculate_returns(prices: pd.Series,
                     method: str = 'simple') -> pd.Series:
    """
    计算收益率

    Args:
        prices: 价格序列
        method: 计算方法 ('simple', 'log')

    Returns:
        收益率序列
    """
    try:
        if method == 'simple':
            return prices.pct_change()
        elif method == 'log':
            return pd.Series(np.log(prices / prices.shift(1)))
        else:
            return prices.pct_change()
    except Exception as e:
        print(f"[DataUtils] 计算收益率失败: {e}")
        return pd.Series()


def format_number(num: float,
                 decimal_places: int = 2) -> str:
    """
    格式化数字

    Args:
        num: 数字
        decimal_places: 小数位数

    Returns:
        格式化后的字符串
    """
    try:
        return f"{num:.{decimal_places}f}"
    except Exception:
        return str(num)


def safe_divide(numerator: float,
                denominator: float,
                default: float = 0.0) -> float:
    """
    安全除法

    Args:
        numerator: 分子
        denominator: 分母
        default: 除零时的默认值

    Returns:
        除法结果
    """
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except Exception:
        return default


def chunk_list(lst: List,
               chunk_size: int) -> List[List]:
    """
    将列表分块

    Args:
        lst: 原始列表
        chunk_size: 每块大小

    Returns:
        分块后的列表
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def print_progress(current: int,
                  total: int,
                  prefix: str = '',
                  suffix: str = ''):
    """
    打印进度条

    Args:
        current: 当前进度
        total: 总数
        prefix: 前缀
        suffix: 后缀
    """
    if total == 0:
        return

    percent = f"{100 * (current / float(total)):.1f}"
    filled_length = int(50 * current // total)
    bar = '█' * filled_length + '-' * (50 - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='', flush=True)

    if current == total:
        print()  # 完成后换行