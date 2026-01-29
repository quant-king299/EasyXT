"""
混合数据管理器
支持从SQLite平滑迁移到DuckDB
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import warnings

try:
    from .duckdb_data_manager import DuckDBDataManager
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    print("[WARN] DuckDB未安装，将使用SQLite")

from .local_data_manager import LocalDataManager


class HybridDataManager:
    """
    混合数据管理器

    策略：
    1. 优先从DuckDB读取
    2. DuckDB没有时从SQLite读取并自动迁移
    3. 新数据写入DuckDB
    4. 支持一键完整迁移
    """

    def __init__(self, config: Dict = None, config_file: str = None,
                 use_duckdb: bool = True, auto_migrate: bool = True):
        """
        初始化混合数据管理器

        Args:
            config: 配置字典
            config_file: 配置文件路径
            use_duckdb: 是否使用DuckDB（如果DuckDB可用）
            auto_migrate: 是否自动迁移数据（从SQLite到DuckDB）
        """
        self.use_duckdb = use_duckdb and DUCKDB_AVAILABLE
        self.auto_migrate = auto_migrate

        # 初始化DuckDB管理器
        if self.use_duckdb:
            try:
                self.duckdb_manager = DuckDBDataManager(config, config_file)
                print("[OK] DuckDB数据管理器初始化成功")
            except Exception as e:
                print(f"[WARN] DuckDB初始化失败: {e}，将使用SQLite")
                self.use_duckdb = False
                self.duckdb_manager = None
        else:
            self.duckdb_manager = None

        # 初始化SQLite管理器（作为后备）
        try:
            self.sqlite_manager = LocalDataManager(config, config_file)
            print("[OK] SQLite数据管理器初始化成功")
        except Exception as e:
            print(f"[WARN] SQLite初始化失败: {e}")
            self.sqlite_manager = None

        # 统计信息
        self.stats = {
            'duckdb_hits': 0,
            'sqlite_hits': 0,
            'migrated_records': 0
        }

    def load_data(self, stock_code: str, period: str = '1d',
                  adjust_type: str = 'none') -> pd.DataFrame:
        """
        加载数据（优先从DuckDB）

        Args:
            stock_code: 股票代码
            period: 周期
            adjust_type: 复权类型

        Returns:
            数据DataFrame
        """
        # 1. 尝试从DuckDB加载
        if self.use_duckdb and self.duckdb_manager:
            try:
                df = self.duckdb_manager.load_data(stock_code, period, adjust_type)
                if not df.empty:
                    self.stats['duckdb_hits'] += 1
                    return df
            except Exception as e:
                warnings.warn(f"从DuckDB加载失败: {e}")

        # 2. 从SQLite加载
        if self.sqlite_manager:
            try:
                df = self.sqlite_manager.storage.load_batch(
                    [stock_code], period, adjust_type=adjust_type
                )

                if stock_code in df and not df[stock_code].empty:
                    self.stats['sqlite_hits'] += 1
                    df_sqlite = df[stock_code]

                    # 自动迁移到DuckDB
                    if self.auto_migrate and self.use_duckdb and self.duckdb_manager:
                        self._migrate_record(df_sqlite, stock_code, period, adjust_type)

                    return df_sqlite

            except Exception as e:
                warnings.warn(f"从SQLite加载失败: {e}")

        return pd.DataFrame()

    def save_data(self, df: pd.DataFrame, stock_code: str = None,
                  period: str = '1d', adjust_type: str = 'none',
                  save_to_sqlite: bool = False) -> Tuple[bool, int]:
        """
        保存数据（优先保存到DuckDB）

        Args:
            df: 数据DataFrame
            stock_code: 股票代码
            period: 周期
            adjust_type: 复权类型
            save_to_sqlite: 是否同时保存到SQLite

        Returns:
            (成功标志, 保存的记录数)
        """
        success = False
        count = 0

        # 保存到DuckDB
        if self.use_duckdb and self.duckdb_manager:
            try:
                success, count = self.duckdb_manager.save_data(
                    df, stock_code, period, adjust_type
                )
            except Exception as e:
                warnings.warn(f"保存到DuckDB失败: {e}")

        # 可选：同时保存到SQLite
        if save_to_sqlite and self.sqlite_manager:
            try:
                success_sqlite, count_sqlite = self.sqlite_manager.storage.save_data(
                    df, period, adjust_type
                )
                if not success:
                    success, count = success_sqlite, count_sqlite
            except Exception as e:
                warnings.warn(f"保存到SQLite失败: {e}")

        return success, count

    def download_data(self, stock_code: str, start_date: str = None,
                      end_date: str = None, period: str = '1d',
                      adjust_type: str = 'none',
                      save_to_sqlite: bool = False) -> pd.DataFrame:
        """
        下载数据（使用DuckDB的数据源）

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 周期
            adjust_type: 复权类型
            save_to_sqlite: 是否同时保存到SQLite

        Returns:
            下载的数据
        """
        # 使用DuckDB管理器的数据源（如果有）
        data_source_manager = (self.duckdb_manager if self.use_duckdb and self.duckdb_manager
                               else self.sqlite_manager)

        if data_source_manager is None or data_source_manager.data_source is None:
            print("[ERROR] 数据源未配置")
            return pd.DataFrame()

        try:
            # 下载数据
            df = data_source_manager.data_source.get_stock_data(
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date,
                period=period,
                adjust=adjust_type
            )

            if df.empty:
                return pd.DataFrame()

            # 保存到DuckDB
            success, count = self.save_data(df, stock_code, period, adjust_type, save_to_sqlite)

            if success:
                print(f"[OK] 已保存 {count} 条数据: {stock_code} ({adjust_type})")

            return df

        except Exception as e:
            print(f"[ERROR] 下载数据失败: {e}")
            return pd.DataFrame()

    def load_batch(self, stock_codes: List[str], period: str = '1d',
                   start_date: str = None, end_date: str = None,
                   adjust_type: str = 'none') -> Dict[str, pd.DataFrame]:
        """
        批量加载数据

        Args:
            stock_codes: 股票代码列表
            period: 周期
            start_date: 开始日期
            end_date: 结束日期
            adjust_type: 复权类型

        Returns:
            {stock_code: DataFrame} 字典
        """
        result = {}

        # 优先从DuckDB批量加载
        if self.use_duckdb and self.duckdb_manager:
            try:
                result = self.duckdb_manager.load_batch(
                    stock_codes, period, start_date, end_date, adjust_type
                )

                # 如果DuckDB中有部分数据，记录一下
                if result:
                    self.stats['duckdb_hits'] += len(result)
                    missing_codes = set(stock_codes) - set(result.keys())

                    # 对于缺失的代码，尝试从SQLite加载
                    if missing_codes and self.sqlite_manager:
                        for code in missing_codes:
                            df = self.load_data(code, period, adjust_type)
                            if not df.empty:
                                result[code] = df

                    return result

            except Exception as e:
                warnings.warn(f"从DuckDB批量加载失败: {e}")

        # 从SQLite批量加载
        if self.sqlite_manager:
            try:
                result = self.sqlite_manager.storage.load_batch(
                    stock_codes, period, start_date, end_date, adjust_type
                )

                # 自动迁移
                if self.auto_migrate and self.use_duckdb and self.duckdb_manager:
                    for code, df in result.items():
                        if not df.empty:
                            self._migrate_record(df, code, period, adjust_type)

            except Exception as e:
                warnings.warn(f"从SQLite批量加载失败: {e}")

        return result

    def _migrate_record(self, df: pd.DataFrame, stock_code: str,
                       period: str, adjust_type: str):
        """迁移单条记录到DuckDB"""
        if not self.use_duckdb or not self.duckdb_manager:
            return

        try:
            df['stock_code'] = stock_code
            success, count = self.duckdb_manager.save_data(df, stock_code, period, adjust_type)

            if success:
                self.stats['migrated_records'] += count

        except Exception as e:
            warnings.warn(f"迁移数据失败 ({stock_code}): {e}")

    def migrate_all_data(self, batch_size: int = 100):
        """
        完整迁移所有数据从SQLite到DuckDB

        Args:
            batch_size: 批量大小
        """
        if not self.use_duckdb or not self.duckdb_manager:
            print("[ERROR] DuckDB不可用，无法迁移")
            return

        if not self.sqlite_manager:
            print("[ERROR] SQLite管理器不可用")
            return

        print("[INFO] 开始完整数据迁移...")
        print(f"     批量大小: {batch_size}")

        try:
            # 获取所有股票列表
            stats = self.sqlite_manager.get_statistics()
            total_symbols = stats.get('total_symbols', 0)

            if total_symbols == 0:
                print("[WARN] SQLite中没有数据")
                return

            print(f"[INFO] 共 {total_symbols} 只股票需要迁移")

            # 获取所有股票代码
            # TODO: 从元数据获取完整列表
            # 这里简化处理，假设从某个地方获取
            print("[INFO] 数据迁移功能开发中...")
            print("[INFO] 提示: 可以使用 import_from_sqlite() 方法导入整个数据库")

        except Exception as e:
            print(f"[ERROR] 迁移失败: {e}")

    def import_from_sqlite(self, sqlite_path: str):
        """
        从SQLite数据库导入所有数据到DuckDB

        Args:
            sqlite_path: SQLite数据库文件路径
        """
        if not self.use_duckdb or not self.duckdb_manager:
            print("[ERROR] DuckDB不可用")
            return

        print(f"[INFO] 从SQLite导入数据: {sqlite_path}")
        self.duckdb_manager.import_from_sqlite(sqlite_path)

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        stats = {
            'usage_stats': self.stats.copy(),
            'duckdb_available': self.use_duckdb,
            'sqlite_available': self.sqlite_manager is not None
        }

        if self.use_duckdb and self.duckdb_manager:
            stats['duckdb'] = self.duckdb_manager.get_statistics()

        if self.sqlite_manager:
            stats['sqlite'] = self.sqlite_manager.get_statistics()

        return stats

    def optimize_databases(self):
        """优化所有数据库"""
        if self.use_duckdb and self.duckdb_manager:
            print("[INFO] 优化DuckDB数据库...")
            self.duckdb_manager.optimize_database()

        if self.sqlite_manager:
            print("[INFO] 优化SQLite数据库...")
            # SQLite没有直接的优化方法

    def close(self):
        """关闭所有连接"""
        if self.duckdb_manager:
            self.duckdb_manager.close()

        # SQLite管理器不需要显式关闭

    def __enter__(self):
        """支持with语句"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持with语句"""
        self.close()
