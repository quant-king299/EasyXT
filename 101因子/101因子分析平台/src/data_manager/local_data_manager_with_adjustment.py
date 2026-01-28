# -*- coding: utf-8 -*-
"""
本地数据管理器（支持复权）
"""

from pathlib import Path
import pandas as pd
from typing import Optional, Literal

from .metadata_db_extended import MetadataDB
from .adjustment_calculator import AdjustmentCalculator


class LocalDataManager:
    """本地数据管理器（支持复权）"""

    def __init__(self, data_dir: str = "D:/StockData"):
        """
        初始化本地数据管理器

        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 元数据库（支持分红数据）
        self.metadata = MetadataDB(self.data_dir / "metadata.db")

        # 存储管理器
        self.storage = DataStorage(self.data_dir)

    def load_data(self, stock_code: str, data_type: str = 'daily',
                 adjust: Literal['none', 'qfq', 'hfq'] = 'none'):
        """
        加载数据（支持复权）

        Args:
            stock_code: 股票代码，如 '000001.SZ'
            data_type: 数据类型 ('daily', '1min', '5min' 等)
            adjust: 复权类型
                - 'none': 不复权（默认）
                - 'qfq': 前复权
                - 'hfq': 后复权

        Returns:
            DataFrame: 根据adjust参数返回对应的数据
        """
        # 加载原始数据
        df = self.storage.load_data(stock_code, data_type)

        if df.empty:
            return df

        # 如果不需要复权，直接返回
        if adjust == 'none':
            return df.copy()

        # 获取分红数据
        dividends = self.metadata.get_dividends(stock_code)

        if dividends.empty:
            print(f"[WARNING] {stock_code} 无分红数据，返回不复权数据")
            return df.copy()

        # 应用复权
        df_adjusted = AdjustmentCalculator.apply_adjustment(
            df, dividends, adjust
        )

        return df_adjusted

    def save_data(self, df: pd.DataFrame, stock_code: str,
                 data_type: str = 'daily') -> tuple:
        """
        保存数据到本地

        Args:
            df: 数据
            stock_code: 股票代码
            data_type: 数据类型

        Returns:
            (success: bool, file_size_mb: float)
        """
        # 构建文件路径
        type_dir = self.data_dir / "raw" / data_type
        type_dir.mkdir(parents=True, exist_ok=True)

        file_path = type_dir / f"{stock_code}.parquet"

        # 保存为Parquet
        df.to_parquet(file_path, compression='snappy')

        # 计算文件大小
        file_size_mb = file_path.stat().st_size / (1024 * 1024)

        # 更新元数据
        symbol_type = self._determine_symbol_type(stock_code)
        self.metadata.update_data_version(
            symbol=stock_code,
            symbol_type=symbol_type,
            start_date=str(df.index.min().date()),
            end_date=str(df.index.max().date()),
            record_count=len(df),
            file_size=file_size_mb
        )

        print(f"[OK] 已保存 {stock_code} {data_type} 数据")
        print(f"  记录数: {len(df):,}")
        print(f"  文件大小: {file_size_mb:.2f} MB")

        return True, file_size_mb

    def save_dividends(self, stock_code: str, dividends_df: pd.DataFrame):
        """
        保存分红数据

        Args:
            stock_code: 股票代码
            dividends_df: 分红数据，需包含列：
                - ex_date: 除权日
                - dividend_per_share: 每股分红
                - record_date: 登记日（可选）
                - payout_date: 派息日（可选）
        """
        # 确保必需列存在
        required_cols = ['ex_date', 'dividend_per_share']
        if not all(col in dividends_df.columns for col in required_cols):
            raise ValueError(f"分红数据必须包含列: {required_cols}")

        # 保存到数据库
        self.metadata.save_dividends(stock_code, dividends_df)

        print(f"[OK] 已保存 {stock_code} 分红数据 {len(dividends_df)} 条")

    def get_dividends(self, stock_code: str) -> pd.DataFrame:
        """获取分红数据"""
        return self.metadata.get_dividends(stock_code)

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return self.metadata.get_statistics()

    def _determine_symbol_type(self, stock_code: str) -> str:
        """判断标的类型"""
        if stock_code.endswith('.SH') or stock_code.endswith('.SZ'):
            if stock_code.startswith('5') or stock_code.startswith('15'):
                return 'etf'
            elif stock_code.startswith('0') or stock_code.startswith('3'):
                if '转债' in stock_code or 'bond' in stock_code.lower():
                    return 'bond'
            return 'stock'
        return 'stock'

    def close(self):
        """关闭数据库连接"""
        if self.metadata:
            self.metadata.close()


class DataStorage:
    """数据存储管理"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def load_data(self, stock_code: str, data_type: str) -> pd.DataFrame:
        """加载数据"""
        file_path = self._get_file_path(stock_code, data_type)

        if not file_path.exists():
            return pd.DataFrame()

        return pd.read_parquet(file_path)

    def _get_file_path(self, stock_code: str, data_type: str) -> Path:
        """获取文件路径"""
        type_dir = self.data_dir / "raw" / data_type
        return type_dir / f"{stock_code}.parquet"


# 使用示例
def example_usage():
    """使用示例"""

    manager = LocalDataManager()

    # 1. 保存原始数据
    print("=" * 60)
    print("1. 保存原始数据（不复权）")
    print("=" * 60)
    df = pd.DataFrame({
        'open': [100, 101, 102],
        'high': [102, 103, 104],
        'low': [99, 100, 101],
        'close': [101, 102, 103],
        'volume': [1000000] * 3
    }, index=pd.date_range('2024-01-01', periods=3))

    manager.save_data(df, '000001.SZ', 'daily')
    print()

    # 2. 保存分红数据
    print("=" * 60)
    print("2. 保存分红数据")
    print("=" * 60)
    dividends = pd.DataFrame({
        'ex_date': ['2024-01-02', '2024-01-03'],
        'dividend_per_share': [0.5, 0.3]
    })

    manager.save_dividends('000001.SZ', dividends)
    print()

    # 3. 加载不同复权类型的数据
    print("=" * 60)
    print("3. 加载不同复权类型的数据")
    print("=" * 60)

    # 不复权
    df_none = manager.load_data('000001.SZ', 'daily', adjust='none')
    print("不复权:")
    print(df_none.head())
    print()

    # 前复权
    df_qfq = manager.load_data('000001.SZ', 'daily', adjust='qfq')
    print("前复权:")
    print(df_qfq.head())
    print()

    # 后复权
    df_hfq = manager.load_data('000001.SZ', 'daily', adjust='hfq')
    print("后复权:")
    print(df_hfq.head())
    print()

    # 4. 查看统计
    print("=" * 60)
    print("4. 数据统计")
    print("=" * 60)
    stats = manager.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")

    manager.close()


if __name__ == '__main__':
    example_usage()
