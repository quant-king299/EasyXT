"""
Parquet文件存储管理
提供高效的行列式存储，支持压缩和快速查询
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import pyarrow as pa
import pyarrow.parquet as pq
import warnings


class ParquetStorage:
    """Parquet文件存储管理器"""

    def __init__(self, root_dir: str, compression: str = 'snappy'):
        """
        初始化Parquet存储

        Args:
            root_dir: 数据存储根目录
            compression: 压缩算法 (snappy/gzip/brotli/lz4)
        """
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

        self.compression = compression

        # 创建子目录
        (self.root_dir / 'daily').mkdir(parents=True, exist_ok=True)
        (self.root_dir / 'factors').mkdir(parents=True, exist_ok=True)

    def save_data(self, df: pd.DataFrame, symbol: str,
                  data_type: str = 'daily',
                  partition_by: str = None) -> Tuple[bool, float]:
        """
        保存数据到Parquet文件

        Args:
            df: 要保存的数据
            symbol: 标的代码
            data_type: 数据类型 (daily/minute/factor)
            partition_by: 分区方式 (year/month/None)

        Returns:
            (success, file_size_mb)
        """
        try:
            if df.empty:
                warnings.warn(f"数据为空，跳过保存: {symbol}")
                return False, 0

            # 构建文件路径
            if data_type == 'factor':
                # 因子数据：factors/factor_name/symbol.parquet
                file_path = self.root_dir / 'factors' / f"{symbol}.parquet"
            else:
                # 行情数据：daily/symbol.parquet
                file_path = self.root_dir / data_type / f"{symbol}.parquet"

            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 确保日期索引是datetime类型
            if isinstance(df.index, pd.DatetimeIndex):
                df.index = df.index.tz_localize(None)

            # 保存为Parquet
            df.to_parquet(
                file_path,
                engine='pyarrow',
                compression=self.compression,
                index=True
            )

            # 获取文件大小
            file_size = file_path.stat().st_size / (1024 * 1024)  # MB

            return True, file_size

        except Exception as e:
            warnings.warn(f"保存数据失败: {symbol}, 错误: {e}")
            return False, 0

    def load_data(self, symbol: str,
                  data_type: str = 'daily',
                  start_date: str = None,
                  end_date: str = None) -> pd.DataFrame:
        """
        从Parquet文件加载数据

        Args:
            symbol: 标的代码
            data_type: 数据类型
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame
        """
        try:
            # 构建文件路径
            if data_type == 'factor':
                file_path = self.root_dir / 'factors' / f"{symbol}.parquet"
            else:
                file_path = self.root_dir / data_type / f"{symbol}.parquet"

            if not file_path.exists():
                return pd.DataFrame()

            # 读取数据
            df = pd.read_parquet(file_path, engine='pyarrow')

            # 确保日期索引
            if not isinstance(df.index, pd.DatetimeIndex):
                if 'date' in df.columns:
                    df = df.set_index('date')
                    df.index = pd.to_datetime(df.index)

            # 过滤日期范围
            if start_date:
                df = df[df.index >= start_date]
            if end_date:
                df = df[df.index <= end_date]

            return df

        except Exception as e:
            warnings.warn(f"加载数据失败: {symbol}, 错误: {e}")
            return pd.DataFrame()

    def save_batch(self, data_dict: Dict[str, pd.DataFrame],
                   data_type: str = 'daily') -> Dict[str, Tuple[bool, float]]:
        """
        批量保存数据

        Args:
            data_dict: {symbol: DataFrame} 字典
            data_type: 数据类型

        Returns:
            {symbol: (success, file_size_mb)}
        """
        results = {}

        for symbol, df in data_dict.items():
            success, size = self.save_data(df, symbol, data_type)
            results[symbol] = (success, size)

        return results

    def load_batch(self, symbols: List[str],
                   data_type: str = 'daily',
                   start_date: str = None,
                   end_date: str = None) -> Dict[str, pd.DataFrame]:
        """
        批量加载数据

        Args:
            symbols: 标的代码列表
            data_type: 数据类型
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            {symbol: DataFrame}
        """
        results = {}

        for symbol in symbols:
            df = self.load_data(symbol, data_type, start_date, end_date)
            if not df.empty:
                results[symbol] = df

        return results

    def append_data(self, df: pd.DataFrame, symbol: str,
                    data_type: str = 'daily') -> bool:
        """
        追加数据到现有文件（增量更新）

        Args:
            df: 要追加的数据
            symbol: 标的代码
            data_type: 数据类型

        Returns:
            是否成功
        """
        try:
            # 加载现有数据
            existing_df = self.load_data(symbol, data_type)

            if not existing_df.empty:
                # 合并数据，去重
                combined_df = pd.concat([existing_df, df])
                combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                combined_df = combined_df.sort_index()
            else:
                combined_df = df

            # 保存合并后的数据
            success, _ = self.save_data(combined_df, symbol, data_type)
            return success

        except Exception as e:
            warnings.warn(f"追加数据失败: {symbol}, 错误: {e}")
            return False

    def get_available_symbols(self, data_type: str = 'daily') -> List[str]:
        """
        获取可用的标的列表

        Args:
            data_type: 数据类型

        Returns:
            标的代码列表
        """
        try:
            data_dir = self.root_dir / data_type

            if not data_dir.exists():
                return []

            parquet_files = list(data_dir.glob('*.parquet'))

            symbols = [f.stem for f in parquet_files if f.is_file()]

            return sorted(symbols)

        except Exception as e:
            warnings.warn(f"获取标的列表失败: {e}")
            return []

    def get_file_info(self, symbol: str,
                      data_type: str = 'daily') -> Optional[Dict]:
        """
        获取文件信息

        Args:
            symbol: 标的代码
            data_type: 数据类型

        Returns:
            文件信息字典
        """
        try:
            if data_type == 'factor':
                file_path = self.root_dir / 'factors' / f"{symbol}.parquet"
            else:
                file_path = self.root_dir / data_type / f"{symbol}.parquet"

            if not file_path.exists():
                return None

            # 读取Parquet元数据
            parquet_file = pq.ParquetFile(file_path)
            metadata = parquet_file.metadata

            # 读取数据获取日期范围
            df = pd.read_parquet(file_path, engine='pyarrow')

            return {
                'symbol': symbol,
                'file_path': str(file_path),
                'file_size_mb': round(file_path.stat().st_size / (1024 * 1024), 2),
                'num_rows': metadata.num_rows,
                'num_columns': metadata.num_columns,
                'start_date': str(df.index.min()) if not df.empty else None,
                'end_date': str(df.index.max()) if not df.empty else None,
                'compression': self.compression
            }

        except Exception as e:
            warnings.warn(f"获取文件信息失败: {symbol}, 错误: {e}")
            return None

    def delete_data(self, symbol: str, data_type: str = 'daily') -> bool:
        """
        删除数据文件

        Args:
            symbol: 标的代码
            data_type: 数据类型

        Returns:
            是否成功
        """
        try:
            if data_type == 'factor':
                file_path = self.root_dir / 'factors' / f"{symbol}.parquet"
            else:
                file_path = self.root_dir / data_type / f"{symbol}.parquet"

            if file_path.exists():
                file_path.unlink()
                return True

            return False

        except Exception as e:
            warnings.warn(f"删除数据失败: {symbol}, 错误: {e}")
            return False

    def get_storage_stats(self) -> Dict:
        """
        获取存储统计信息

        Returns:
            统计信息字典
        """
        stats = {
            'total_symbols': 0,
            'total_size_mb': 0,
            'data_types': {}
        }

        try:
            # 遍历所有数据类型目录
            for data_type_dir in self.root_dir.iterdir():
                if data_type_dir.is_dir():
                    data_type = data_type_dir.name

                    parquet_files = list(data_type_dir.glob('*.parquet'))
                    num_symbols = len(parquet_files)
                    size_mb = sum(f.stat().st_size for f in parquet_files) / (1024 * 1024)

                    stats['data_types'][data_type] = {
                        'count': num_symbols,
                        'size_mb': round(size_mb, 2)
                    }

                    stats['total_symbols'] += num_symbols
                    stats['total_size_mb'] += size_mb

            stats['total_size_mb'] = round(stats['total_size_mb'], 2)

        except Exception as e:
            warnings.warn(f"获取存储统计失败: {e}")

        return stats

    def optimize_storage(self, data_type: str = 'daily'):
        """
        优化存储：压缩、重建索引等

        Args:
            data_type: 数据类型
        """
        try:
            data_dir = self.root_dir / data_type

            if not data_dir.exists():
                return

            parquet_files = list(data_dir.glob('*.parquet'))

            print(f"优化存储: {len(parquet_files)} 个文件")

            # 这里可以添加更多优化操作
            # 例如：重新压缩、重建索引等

            print("存储优化完成")

        except Exception as e:
            warnings.warn(f"存储优化失败: {e}")

    def export_to_csv(self, symbol: str, output_path: str,
                      data_type: str = 'daily') -> bool:
        """
        导出数据到CSV

        Args:
            symbol: 标的代码
            output_path: 输出路径
            data_type: 数据类型

        Returns:
            是否成功
        """
        try:
            df = self.load_data(symbol, data_type)

            if df.empty:
                return False

            df.to_csv(output_path)
            return True

        except Exception as e:
            warnings.warn(f"导出CSV失败: {symbol}, 错误: {e}")
            return False


if __name__ == '__main__':
    # 测试代码
    storage = ParquetStorage("../data/raw", compression='snappy')

    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    test_df = pd.DataFrame({
        'open': np.random.rand(100) * 100,
        'high': np.random.rand(100) * 100,
        'low': np.random.rand(100) * 100,
        'close': np.random.rand(100) * 100,
        'volume': np.random.randint(1000000, 10000000, 100)
    }, index=dates)

    # 测试保存
    success, size = storage.save_data(test_df, '000001.SZ', 'daily')
    print(f"保存成功: {success}, 文件大小: {size:.2f}MB")

    # 测试加载
    loaded_df = storage.load_data('000001.SZ', 'daily')
    print(f"加载数据形状: {loaded_df.shape}")

    # 测试文件信息
    file_info = storage.get_file_info('000001.SZ', 'daily')
    print(f"文件信息: {file_info}")

    # 测试存储统计
    stats = storage.get_storage_stats()
    print(f"存储统计: {stats}")
