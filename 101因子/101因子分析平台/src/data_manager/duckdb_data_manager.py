"""
DuckDB数据管理器
基于DuckDB的高性能本地数据管理
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
from datetime import datetime, timedelta
import warnings

from .duckdb_storage import DuckDBStorage
from .metadata_db_extended import MetadataDBExtended


class DuckDBDataManager:
    """
    DuckDB数据管理器

    特性：
    1. 高性能列式存储 - 查询速度比SQLite快10-100倍
    2. 支持复权数据 - 前复权、后复权、不复权
    3. 高效的批量操作 - 适合大量数据导入
    4. 强大的窗口函数 - 技术指标计算更快
    5. 支持Parquet - 可直接读写Parquet文件
    6. 从SQLite平滑迁移 - 无需手动转换数据
    """

    def __init__(self, config: Dict = None, config_file: str = None):
        """
        初始化DuckDB数据管理器

        Args:
            config: 配置字典（优先）
            config_file: 配置文件路径
        """
        # 加载配置
        if config is None:
            config = self._load_config_from_file(config_file)

        # 默认配置
        default_config = {
            'data_paths': {
                'root_dir': '../data',
                'database': 'stock_data.ddb',  # DuckDB数据库文件
                'metadata': 'metadata.db'
            },
            'storage': {
                'format': 'duckdb',
                'compression': 'zstd'  # zstd压缩比高，性能好
            },
            'update': {
                'auto_check': True,
                'max_retries': 3,
                'batch_size': 100
            },
            'performance': {
                'threads': 4,
                'memory_limit': '4GB'
            },
            'quality': {
                'min_trading_days': 200,
                'check_price_relation': True,
                'max_change_pct': 20
            }
        }

        self.config = {**default_config, **config}

        # 初始化路径
        self.root_dir = Path(self.config['data_paths']['root_dir'])
        self.db_path = self.root_dir / self.config['data_paths']['database']
        self.metadata_path = self.root_dir / self.config['data_paths']['metadata']

        # 创建目录
        self.root_dir.mkdir(parents=True, exist_ok=True)

        # 初始化存储引擎
        self.storage = DuckDBStorage(
            str(self.db_path),
            compression=self.config['storage']['compression']
        )

        # 初始化元数据管理器
        try:
            self.metadata = MetadataDB(str(self.metadata_path))
        except Exception as e:
            print(f"[WARN] 元数据库初始化失败: {e}")
            self.metadata = None

        # 数据源（延迟加载）
        self._data_source = None

        print(f"[OK] DuckDB数据管理器初始化完成")
        print(f"     数据库路径: {self.db_path}")

    def _load_config_from_file(self, config_file: str = None) -> Dict:
        """从YAML文件加载配置"""
        import yaml

        if config_file is None:
            # 尝试默认配置文件
            script_dir = Path(__file__).parents[2]  # 回到项目根目录
            config_file = script_dir / 'config' / 'data_config.yaml'

        config_path = Path(config_file)

        if not config_path.exists():
            print(f"[WARN] 配置文件不存在: {config_path}，使用默认配置")
            return {}

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            print(f"[OK] 已加载配置文件: {config_path}")
            return config or {}
        except Exception as e:
            print(f"[WARN] 加载配置文件失败: {e}，使用默认配置")
            return {}

    @property
    def data_source(self):
        """获取数据源（延迟加载）"""
        if self._data_source is None:
            try:
                import sys
                import json
                workspace_dir = Path(__file__).parents[4]  # 回到miniqmt扩展目录
                if str(workspace_dir) not in sys.path:
                    sys.path.insert(0, str(workspace_dir))

                from gui_app.backtest.data_manager import DataManager as SourceManager

                # 尝试从unified_config.json加载配置
                config_path = workspace_dir / 'config' / 'unified_config.json'
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    self._data_source = SourceManager()
                    print("[OK] 使用DataManager作为数据源（已加载QMT配置）")
                else:
                    self._data_source = SourceManager()
                    print("[OK] 使用DataManager作为数据源")

            except Exception as e:
                print(f"[WARN] 无法加载数据源: {e}")
                self._data_source = None

        return self._data_source

    def download_data(self, stock_code: str, start_date: str = None,
                      end_date: str = None, period: str = '1d',
                      adjust_type: str = 'none') -> pd.DataFrame:
        """
        下载数据并保存到本地

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 周期
            adjust_type: 复权类型 ('none', 'front', 'back')

        Returns:
            下载的数据
        """
        if self.data_source is None:
            print("[ERROR] 数据源未配置")
            return pd.DataFrame()

        try:
            # 从数据源获取数据
            df = self.data_source.get_stock_data(
                stock_code=stock_code,
                start_date=start_date or '2020-01-01',
                end_date=end_date or datetime.now().strftime('%Y-%m-%d'),
                period=period,
                adjust=adjust_type
            )

            if df.empty:
                print(f"[WARN] 未获取到数据: {stock_code}")
                return pd.DataFrame()

            # 保存到DuckDB
            success, count = self.save_data(df, stock_code, period, adjust_type)

            if success:
                print(f"[OK] 已保存 {count} 条数据到DuckDB: {stock_code} ({adjust_type})")

            return df

        except Exception as e:
            print(f"[ERROR] 下载数据失败: {e}")
            return pd.DataFrame()

    def save_data(self, df: pd.DataFrame, stock_code: str = None,
                  period: str = '1d', adjust_type: str = 'none',
                  symbol_type: str = 'stock') -> Tuple[bool, int]:
        """
        保存数据到DuckDB

        Args:
            df: 数据DataFrame
            stock_code: 股票代码（如果df中有stock_code列则可选）
            period: 周期
            adjust_type: 复权类型
            symbol_type: 标的类型

        Returns:
            (成功标志, 保存的记录数)
        """
        if df.empty:
            return False, 0

        # 如果没有stock_code列，添加它
        if 'stock_code' not in df.columns and stock_code:
            df = df.copy()
            df['stock_code'] = stock_code

        # 确保有必要的列
        required_columns = ['stock_code', 'date', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            print(f"[ERROR] 缺少必要的列: {missing_columns}")
            return False, 0

        # 如果没有amount列，计算它
        if 'amount' not in df.columns:
            df['amount'] = df['close'] * df['volume']

        # 保存到DuckDB
        return self.storage.save_data(df, symbol_type, period, adjust_type)

    def load_data(self, stock_code: str, period: str = '1d',
                  adjust_type: str = 'none') -> pd.DataFrame:
        """
        从DuckDB加载数据

        Args:
            stock_code: 股票代码
            period: 周期
            adjust_type: 复权类型

        Returns:
            数据DataFrame
        """
        return self.storage.load_data(stock_code, period, adjust_type)

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
        return self.storage.load_batch(stock_codes, period, start_date, end_date, adjust_type)

    def update_data(self, stock_codes: List[str] = None, period: str = '1d',
                    adjust_types: List[str] = None):
        """
        增量更新数据

        Args:
            stock_codes: 股票代码列表（None表示全部）
            period: 周期
            adjust_types: 复权类型列表
        """
        if adjust_types is None:
            adjust_types = ['none', 'front', 'back']

        if stock_codes is None:
            # 更新所有股票
            print("[INFO] 更新所有股票数据...")
            # TODO: 从元数据获取股票列表
            return

        print(f"[INFO] 开始更新 {len(stock_codes)} 只股票的数据...")

        for stock_code in stock_codes:
            for adjust_type in adjust_types:
                try:
                    # 获取最新数据的日期
                    df_existing = self.load_data(stock_code, period, adjust_type)
                    if not df_existing.empty:
                        last_date = df_existing.index[-1]
                        start_date = (pd.to_datetime(last_date) + timedelta(days=1)).strftime('%Y-%m-%d')
                    else:
                        start_date = None

                    # 下载数据
                    df_new = self.download_data(
                        stock_code=stock_code,
                        start_date=start_date,
                        period=period,
                        adjust_type=adjust_type
                    )

                    if not df_new.empty:
                        print(f"[OK] 更新完成: {stock_code} ({adjust_type})")

                except Exception as e:
                    print(f"[ERROR] 更新失败 {stock_code} ({adjust_type}): {e}")

    def calculate_indicators(self, stock_code: str, start_date: str, end_date: str,
                            indicators: List[str] = None) -> pd.DataFrame:
        """
        计算技术指标

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            indicators: 指标列表

        Returns:
            包含技术指标的DataFrame
        """
        return self.storage.calculate_indicators(stock_code, start_date, end_date, indicators)

    def get_statistics(self) -> Dict:
        """
        获取数据库统计信息

        Returns:
            统计信息字典
        """
        return self.storage.get_statistics()

    def export_to_parquet(self, output_dir: str, table: str = 'stock_daily'):
        """
        导出数据为Parquet格式

        Args:
            output_dir: 输出目录
            table: 表名
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        parquet_file = output_path / f"{table}.parquet"
        self.storage.export_to_parquet(str(parquet_file), table)

    def import_from_sqlite(self, sqlite_path: str):
        """
        从SQLite数据库导入数据

        Args:
            sqlite_path: SQLite数据库文件路径
        """
        print(f"[INFO] 开始从SQLite导入数据: {sqlite_path}")
        self.storage.import_from_sqlite(sqlite_path)
        print("[OK] SQLite数据导入完成")

    def optimize_database(self):
        """优化数据库性能"""
        self.storage.optimize_database()

    def get_dividend_data(self, stock_code: str) -> pd.DataFrame:
        """
        获取分红数据

        Args:
            stock_code: 股票代码

        Returns:
            分红数据DataFrame
        """
        try:
            query = """
                SELECT ex_date, dividend_per_share, bonus_ratio,
                       rights_issue_ratio, rights_issue_price,
                       record_date, pay_date
                FROM dividends
                WHERE stock_code = ?
                ORDER BY ex_date DESC
            """

            return self.storage.con.execute(query, [stock_code]).df()

        except Exception as e:
            warnings.warn(f"获取分红数据失败: {e}")
            return pd.DataFrame()

    def save_dividend_data(self, df: pd.DataFrame):
        """
        保存分红数据

        Args:
            df: 分红数据DataFrame
        """
        if df.empty:
            return

        try:
            # 注册临时表
            self.storage.con.register('temp_dividends', df)

            # 执行UPSERT
            self.storage.con.execute("""
                INSERT OR REPLACE INTO dividends
                SELECT * FROM temp_dividends
            """)

            print(f"[OK] 已保存 {len(df)} 条分红数据")

        except Exception as e:
            print(f"[ERROR] 保存分红数据失败: {e}")
        finally:
            # 清理临时表
            try:
                self.storage.con.unregister('temp_dividends')
            except:
                pass

    def close(self):
        """关闭数据库连接"""
        self.storage.close()

    def __enter__(self):
        """支持with语句"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持with语句"""
        self.close()
