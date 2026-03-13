"""
QKA数据模块

提供统一的数据获取、缓存和管理功能，支持多数据源、多周期、多因子的数据获取。
"""

from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import akshare as ak
import dask.dataframe as dd
from typing import List, Dict, Optional, Callable
from qka.utils.logger import logger

class Data():
    """
    数据管理类
    
    负责股票数据的获取、缓存和管理，支持多数据源、并发下载和自定义因子计算。
    
    Attributes:
        symbols (List[str]): 股票代码列表
        period (str): 数据周期，如 '1d'、'1m' 等
        adjust (str): 复权方式，如 'qfq'、'hfq'、'bfq'
        factor (Callable): 因子计算函数
        source (str): 数据源，如 'akshare'、'qmt'
        pool_size (int): 并发下载线程数
        datadir (Path): 数据缓存目录
        target_dir (Path): 目标存储目录
    """
    
    def __init__(
        self, 
        symbols: Optional[List[str]] = None,
        period: str = '1d',
        adjust: str = 'qfq',
        factor: Callable[[pd.DataFrame], pd.DataFrame] = lambda df: df,
        source: str = 'akshare',
        pool_size: int = 10,
        datadir: Optional[Path] = None
    ):
        """
        初始化数据对象
        
        Args:
            symbols: [维度1] 标的，如 ['000001.SZ', '600000.SH']
            period: [维度2] 周期，如 '1m', '5m', '1d' 等
            factor: [维度3] 因子字典，key为因子名，value为因子函数
            source: [维度4] 数据来源 ('qmt', 'akshare')
            pool_size: 并发池大小
            datadir: 缓存根目录，默认为项目根目录下的 datadir
        """
        self.symbols = symbols or []
        self.period = period
        self.adjust = adjust
        self.factor = factor
        self.source = source
        self.pool_size = pool_size

        # 初始化缓存目录
        if datadir is None:
            # 默认使用当前工作目录下的 datadir
            self.datadir = Path.cwd() / "datadir"
        else:
            self.datadir = Path(datadir)
        
        self.datadir.mkdir(parents=True, exist_ok=True)

        self.target_dir = self.datadir / self.source / self.period / (self.adjust or "bfq")
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def _download(self, symbol: str) -> Path:
        """
        下载单个股票的数据
        
        Args:
            symbol (str): 股票代码
            
        Returns:
            Path: 数据文件路径
        """
        path = self.target_dir / f"{symbol}.parquet"

        if path.exists():
             return path

        if self.source == 'akshare':
            df = self._get_from_akshare(symbol)
        else:
            df = pd.DataFrame()

        if len(df) == 0:
            return path

        table = pa.Table.from_pandas(df)
        pq.write_table(table, path)

        return path

    def get(self) -> dd.DataFrame:
        """
        获取历史数据
        
        并发下载所有股票数据，应用因子计算，并返回合并后的Dask DataFrame。
        
        Returns:
            dd.DataFrame: 合并后的股票数据，每只股票的列名格式为 {symbol}_{column}
        """
        # 准备缓存目录

        with ThreadPoolExecutor(max_workers=self.pool_size) as executor:
            # 提交下载任务
            futures = {
                executor.submit(self._download, symbol): symbol
                for symbol in self.symbols
            }

            # 添加tqdm进度条
            with tqdm(total=len(self.symbols), desc="下载数据") as pbar:
                for future in as_completed(futures):
                    symbol = futures[future]
                    pbar.update(1)
                    pbar.set_postfix_str(f"当前: {symbol}")

        dfs = []
        for symbol in self.symbols:
            df = dd.read_parquet(str(self.target_dir / f"{symbol}.parquet"))
            df = self.factor(df)
            column_mapping = {col: f'{symbol}_{col}' for col in df.columns}
            dfs.append(df.rename(columns=column_mapping))

        df = dd.concat(dfs, axis=1, join='outer')

        return df

    def _get_from_akshare(self, symbol: str) -> pd.DataFrame:
        """
        从 akshare 获取单个股票的数据。

        Args:
            symbol (str): 股票代码，支持带后缀如 000001.SZ 或不带后缀的 000001

        Returns:
            pd.DataFrame: 股票数据，以 date 为索引，包含 open, high, low, close, volume, amount 列
        """
        column_mapping = {
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
        }

        # 下载数据
        df = ak.stock_zh_a_hist(symbol=symbol, period='daily', adjust=self.adjust)

        # 数据标准化处理
        # 1. 标准化列名
        df = df.rename(columns=column_mapping)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])

        # 2. 确保数值列为数值类型
        numeric_cols = [c for c in ("open", "high", "low", "close", "volume", "amount") if c in df.columns]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # 3. 只保留需要的列
        mapped_columns = list(column_mapping.values())
        available_columns = [col for col in mapped_columns if col in df.columns]
        df = df[available_columns]

        df = df.set_index('date')
        # 设置索引
        return df
