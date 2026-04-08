"""
CSV文件存储管理
简单的文件存储方案，无需额外依赖
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import warnings


class CSVStorage:
    """CSV文件存储管理器（无额外依赖）"""

    def __init__(self, root_dir: str, compression: str = None):
        """
        初始化CSV存储

        Args:
            root_dir: 数据存储根目录
            compression: 压缩算法（CSV不支持，保留参数兼容性）
        """
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        (self.root_dir / 'daily').mkdir(parents=True, exist_ok=True)
        (self.root_dir / 'factors').mkdir(parents=True, exist_ok=True)

    def save_data(self, df: pd.DataFrame, symbol: str,
                  data_type: str = 'daily',
                  partition_by: str = None) -> Tuple[bool, float]:
        """
        保存数据到CSV文件

        Args:
            df: 要保存的数据
            symbol: 标的代码
            data_type: 数据类型 (daily/minute/factor)
            partition_by: 分区方式（CSV不支持，保留参数兼容性）

        Returns:
            (success, file_size_mb)
        """
        try:
            if df.empty:
                warnings.warn(f"数据为空，跳过保存: {symbol}")
                return False, 0

            # 构建文件路径
            if data_type == 'factor':
                # 因子数据：factors/factor_name/symbol.csv
                file_path = self.root_dir / 'factors' / f"{symbol}.csv"
            else:
                # 行情数据：daily/symbol.csv
                file_path = self.root_dir / data_type / f"{symbol}.csv"

            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 确保日期索引是datetime类型
            if isinstance(df.index, pd.DatetimeIndex):
                df.index = df.index.tz_localize(None)

            # 保存为CSV
            df.to_csv(file_path, index=True, encoding='utf-8')

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
        从CSV文件加载数据

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
                file_path = self.root_dir / 'factors' / f"{symbol}.csv"
            else:
                file_path = self.root_dir / data_type / f"{symbol}.csv"

            if not file_path.exists():
                return pd.DataFrame()

            # 读取数据
            df = pd.read_csv(file_path, index_col=0, encoding='utf-8')

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
        追加数据到现有文件

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
                # 合并数据
                combined_df = pd.concat([existing_df, df])
                # 去重
                combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                # 排序
                combined_df = combined_df.sort_index()
            else:
                combined_df = df

            # 保存合并后的数据
            success, _ = self.save_data(combined_df, symbol, data_type)
            return success

        except Exception as e:
            warnings.warn(f"追加数据失败: {symbol}, 错误: {e}")
            return False

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
                file_path = self.root_dir / 'factors' / f"{symbol}.csv"
            else:
                file_path = self.root_dir / data_type / f"{symbol}.csv"

            if file_path.exists():
                file_path.unlink()
                return True

            return False

        except Exception as e:
            warnings.warn(f"删除数据失败: {symbol}, 错误: {e}")
            return False

    def list_symbols(self, data_type: str = 'daily') -> List[str]:
        """
        列出所有已保存的标的代码

        Args:
            data_type: 数据类型

        Returns:
            标的代码列表
        """
        try:
            if data_type == 'factor':
                data_dir = self.root_dir / 'factors'
            else:
                data_dir = self.root_dir / data_type

            if not data_dir.exists():
                return []

            symbols = [f.stem for f in data_dir.glob('*.csv')]
            return sorted(symbols)

        except Exception as e:
            warnings.warn(f"列出标的失败: {e}")
            return []

    def get_storage_info(self) -> Dict[str, any]:
        """
        获取存储信息

        Returns:
            存储信息字典
        """
        info = {
            'storage_type': 'CSV',
            'root_dir': str(self.root_dir),
            'total_symbols': 0,
            'total_files': 0,
            'total_size_mb': 0
        }

        try:
            for data_type in ['daily', 'factors']:
                if data_type == 'factor':
                    data_dir = self.root_dir / 'factors'
                else:
                    data_dir = self.root_dir / data_type

                if data_dir.exists():
                    files = list(data_dir.glob('*.csv'))
                    info['total_files'] += len(files)
                    info['total_symbols'] += len(files)
                    info['total_size_mb'] += sum(f.stat().st_size for f in files) / (1024 * 1024)

        except Exception as e:
            warnings.warn(f"获取存储信息失败: {e}")

        return info
