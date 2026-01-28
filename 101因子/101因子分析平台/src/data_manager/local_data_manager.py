"""
本地数据管理器
整合数据下载、存储、更新、查询等功能
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Union
from datetime import datetime, timedelta
import time
import warnings

from .parquet_storage import ParquetStorage
from .metadata_db import MetadataDB


class LocalDataManager:
    """
    本地数据管理器

    功能：
    1. 从QMT/AKShare下载数据并保存到本地
    2. 增量更新数据
    3. 查询本地数据
    4. 数据质量检查
    5. 元数据管理
    """

    def __init__(self, config: Dict = None, config_file: str = None):
        """
        初始化数据管理器

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
                'raw_data': 'raw',
                'metadata': 'metadata.db'
            },
            'storage': {
                'format': 'parquet',
                'compression': 'snappy'
            },
            'update': {
                'auto_check': True,
                'max_retries': 3,
                'batch_size': 100
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
        self.raw_data_dir = self.root_dir / self.config['data_paths']['raw_data']
        self.metadata_path = self.root_dir / self.config['data_paths']['metadata']

        # 创建目录
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)

        # 初始化组件
        self.storage = ParquetStorage(
            str(self.raw_data_dir),
            compression=self.config['storage']['compression']
        )
        self.metadata = MetadataDB(str(self.metadata_path))

        # 数据源（延迟导入）
        self._data_source = None

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
                # 尝试导入DataManager作为数据源
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
                    # 使用配置创建DataManager
                    self._data_source = SourceManager()
                    print("✅ 使用DataManager作为数据源（已加载QMT配置）")
                else:
                    self._data_source = SourceManager()
                    print("✅ 使用DataManager作为数据源")

            except Exception as e:
                print(f"⚠️ 无法加载数据源: {e}")
                self._data_source = None

        return self._data_source

    def _get_qmt_api(self):
        """
        获取QMT API实例（easy_xt或xtdata）

        Returns:
            API实例或None
        """
        try:
            import sys
            import json
            workspace_dir = Path(__file__).parents[4]
            if str(workspace_dir) not in sys.path:
                sys.path.insert(0, str(workspace_dir))

            # 尝试使用easy_xt
            try:
                import easy_xt
                # 检查配置文件
                config_path = workspace_dir / 'config' / 'unified_config.json'
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)

                    # 获取QMT配置
                    qmt_config = config.get('settings', {}).get('account', {})
                    qmt_path = qmt_config.get('qmt_path', '')
                    session_id = config.get('system', {}).get('qmt', {}).get('session_id', 'mini_qmt')

                    print(f"📡 使用easy_xt连接QMT (session: {session_id})")
                    return easy_xt

                print(f"📡 使用easy_xt（默认配置）")
                return easy_xt

            except ImportError:
                # 如果easy_xt不可用，尝试直接使用xtdata
                import xtquant.xtdata as xt_data
                print(f"📡 使用xtdata")
                return xt_data

        except Exception as e:
            print(f"⚠️ 获取QMT API失败: {e}")
            return None

    def download_and_save(self, symbols: Union[str, List[str]],
                          start_date: str, end_date: str,
                          symbol_type: str = 'stock',
                          show_progress: bool = True) -> Dict[str, pd.DataFrame]:
        """
        下载数据并保存到本地

        Args:
            symbols: 标的代码或代码列表
            start_date: 开始日期
            end_date: 结束日期
            symbol_type: 标的类型 (stock/bond)
            show_progress: 是否显示进度

        Returns:
            {symbol: DataFrame} 字典
        """
        start_time = time.time()

        # 标准化输入
        if isinstance(symbols, str):
            symbols = [s.strip() for s in symbols.split(',') if s.strip()]

        print(f"\n{'='*60}")
        print(f"[INFO] 开始下载数据")
        print(f"[INFO] 标的数量: {len(symbols)}")
        print(f"[INFO] 日期范围: {start_date} ~ {end_date}")
        print(f"[INFO] 标的类型: {symbol_type}")
        print(f"{'='*60}\n")

        results = {}
        success_count = 0
        failed_symbols = []

        batch_size = self.config['update']['batch_size']
        total_batches = (len(symbols) + batch_size - 1) // batch_size

        for batch_idx in range(total_batches):
            batch_start = batch_idx * batch_size
            batch_end = min(batch_start + batch_size, len(symbols))
            batch_symbols = symbols[batch_start:batch_end]

            if show_progress:
                print(f"[BATCH] 处理批次 {batch_idx + 1}/{total_batches} (标的 {batch_start + 1}-{batch_end})")

            for symbol in batch_symbols:
                try:
                    # 从数据源获取数据
                    df = self._fetch_from_source(symbol, start_date, end_date)

                    if df.empty:
                        print(f"  [WARN] 获取数据为空: {symbol}")
                        failed_symbols.append(symbol)
                        continue

                    # 数据质量检查
                    if not self._check_data_quality(df):
                        print(f"  [WARN] 数据质量不合格: {symbol}")
                        failed_symbols.append(symbol)
                        continue

                    # 检查是否有现有数据
                    existing_df = self.storage.load_data(symbol, 'daily')

                    # 保存到本地
                    success, file_size = self.storage.save_data(
                        df, symbol, data_type='daily'
                    )

                    if success:
                        # 更新元数据
                        self.metadata.update_data_version(
                            symbol=symbol,
                            symbol_type=symbol_type,
                            start_date=str(df.index.min().date()),
                            end_date=str(df.index.max().date()),
                            record_count=len(df),
                            file_size=file_size,
                            data_quality=1.0
                        )

                        results[symbol] = df
                        success_count += 1

                        if show_progress:
                            print(f"  ✓ {symbol} ({len(df)}条记录, {file_size:.2f}MB)")
                    else:
                        failed_symbols.append(symbol)

                except Exception as e:
                    warnings.warn(f"[ERROR] 处理失败: {symbol}, 错误: {e}")
                    failed_symbols.append(symbol)
                    continue

        # 记录日志
        duration = time.time() - start_time
        self.metadata.log_update(
            operation='download',
            status='success' if not failed_symbols else 'partial',
            symbols_count=len(symbols),
            records_count=sum(len(df) for df in results.values()),
            error_message=f"失败: {len(failed_symbols)}个" if failed_symbols else None,
            duration=duration
        )

        # 打印总结
        print(f"\n{'='*60}")
        print(f"[SUMMARY] 下载完成!")
        print(f"[SUCCESS] 成功: {success_count}/{len(symbols)}")
        if failed_symbols:
            print(f"[FAILED] 失败: {len(failed_symbols)}个 - {failed_symbols[:5]}{'...' if len(failed_symbols) > 5 else ''}")
        print(f"[TIME] 耗时: {duration:.2f}秒")
        print(f"{'='*60}\n")

        return results

    def _fetch_from_source(self, symbol: str,
                          start_date: str, end_date: str) -> pd.DataFrame:
        """从数据源获取数据"""
        # 尝试使用easy_xt API
        try:
            import sys
            workspace_dir = Path(__file__).parents[4]
            if str(workspace_dir) not in sys.path:
                sys.path.insert(0, str(workspace_dir))

            import easy_xt
            api = easy_xt.get_api()

            # 初始化数据服务
            try:
                api.init_data()
            except:
                pass  # 忽略初始化错误

            # 使用api.get_price()获取数据
            from datetime import datetime
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')

            # 计算天数
            days = (end_dt - start_dt).days

            # 获取数据
            df = api.get_price(symbol, period='1d', count=days + 500)  # 多取一些确保覆盖

            if df is not None and not df.empty:
                # 过滤日期范围
                if 'time' in df.columns:
                    df['time'] = pd.to_datetime(df['time'])
                    df = df[(df['time'] >= start_dt) & (df['time'] <= end_dt)]
                    df = df.set_index('time')
                else:
                    df = df.loc[start_dt:end_dt]

                # 标准化列名
                df.columns = df.columns.str.lower()
                return df
        except Exception as e:
            warnings.warn(f"easy_xt获取数据失败: {symbol}, 错误: {e}")

        # 备用方案：尝试使用DataManager
        if self.data_source is not None:
            try:
                df = self.data_source.get_stock_data(
                    stock_code=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    period='1d'
                )

                if not df.empty:
                    # 标准化列名
                    df.columns = df.columns.str.lower()
                    return df
            except Exception as e:
                warnings.warn(f"DataManager获取数据失败: {symbol}, 错误: {e}")

        return pd.DataFrame()

    def _check_data_quality(self, df: pd.DataFrame) -> bool:
        """检查数据质量"""
        if df.empty:
            return False

        min_days = self.config['quality']['min_trading_days']

        if len(df) < min_days:
            return False

        # 检查必需列
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            return False

        # 检查价格关系
        if self.config['quality']['check_price_relation']:
            # high >= max(open, close) and low <= min(open, close)
            valid = (
                (df['high'] >= df[['open', 'close']].max(axis=1)) &
                (df['low'] <= df[['open', 'close']].min(axis=1))
            )
            if valid.sum() / len(df) < 0.95:  # 至少95%的数据有效
                return False

        # 检查异常值
        if 'close' in df.columns:
            returns = df['close'].pct_change()
            max_change = self.config['quality']['max_change_pct'] / 100
            if (returns.abs() > max_change).sum() / len(returns) > 0.05:  # 超过5%的异常数据
                return False

        return True

    def load_data(self, symbols: Union[str, List[str]],
                  start_date: str = None, end_date: str = None,
                  check_local: bool = True) -> Dict[str, pd.DataFrame]:
        """
        加载本地数据

        Args:
            symbols: 标的代码或代码列表
            start_date: 开始日期
            end_date: 结束日期
            check_local: 是否仅从本地加载

        Returns:
            {symbol: DataFrame} 字典
        """
        if isinstance(symbols, str):
            symbols = [s.strip() for s in symbols.split(',') if s.strip()]

        results = {}

        # 从本地加载
        local_results = self.storage.load_batch(symbols, 'daily', start_date, end_date)
        results.update(local_results)

        # 如果有缺失且允许下载
        if check_local:
            missing_symbols = set(symbols) - set(results.keys())
            if missing_symbols:
                print(f"[INFO] 本地缺失 {len(missing_symbols)} 个标的，尝试下载...")

                # 需要日期范围，如果未指定则使用默认
                if not start_date:
                    start_date = (datetime.now() - timedelta(days=365*10)).strftime('%Y-%m-%d')
                if not end_date:
                    end_date = datetime.now().strftime('%Y-%m-%d')

                downloaded = self.download_and_save(
                    list(missing_symbols), start_date, end_date,
                    show_progress=False
                )
                results.update(downloaded)

        return results

    def get_all_symbols(self, symbol_type: str = None) -> List[str]:
        """
        获取所有可用的标的代码

        Args:
            symbol_type: 标的类型过滤 (stock/bond)

        Returns:
            标的代码列表
        """
        return self.metadata.get_all_symbols(symbol_type)

    def update_data(self, symbols: List[str] = None,
                    symbol_type: str = 'stock',
                    days_back: int = 5):
        """
        增量更新数据

        Args:
            symbols: 要更新的标的列表，None表示全部
            symbol_type: 标的类型
            days_back: 向前回溯天数（用于填补缺失）
        """
        print(f"\n开始增量更新...")

        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        # 如果未指定标的，获取需要更新的标的
        if symbols is None:
            symbols_to_update = self.metadata.get_symbols_needing_update(days_threshold=1)
            symbols = [s[0] for s in symbols_to_update]

        if not symbols:
            print("[INFO] 没有需要更新的标的")
            return

        # 下载并保存
        self.download_and_save(
            symbols, start_date, end_date,
            symbol_type=symbol_type
        )

    def get_data_info(self, symbol: str) -> Optional[Dict]:
        """
        获取标的数据信息

        Args:
            symbol: 标的代码

        Returns:
            数据信息字典
        """
        # 从元数据获取
        version_info = self.metadata.get_data_version(symbol)

        # 从文件获取
        file_info = self.storage.get_file_info(symbol, 'daily')

        if version_info or file_info:
            info = {**(version_info or {}), **(file_info or {})}
            return info

        return None

    def get_statistics(self) -> Dict:
        """
        获取数据统计信息

        Returns:
            统计信息字典
        """
        # 元数据统计
        meta_stats = self.metadata.get_statistics()

        # 存储统计
        storage_stats = self.storage.get_storage_stats()

        return {
            **meta_stats,
            'storage': storage_stats
        }

    def print_summary(self):
        """打印数据摘要"""
        stats = self.get_statistics()

        print(f"\n{'='*60}")
        print(f"本地数据管理器 - 数据摘要")
        print(f"{'='*60}")
        print(f"标的总数: {stats.get('total_symbols', 0)}")
        print(f"  - 股票: {stats.get('total_stocks', 0)}")
        print(f"  - 债券: {stats.get('total_bonds', 0)}")
        print(f"交易日数: {stats.get('total_trading_days', 0)}")
        print(f"总记录数: {stats.get('total_records', 0):,}")
        print(f"存储大小: {stats.get('total_size_mb', 0):.2f} MB")
        print(f"最新日期: {stats.get('latest_data_date', 'N/A')}")
        print(f"{'='*60}\n")

    def export_data(self, symbols: List[str], output_dir: str,
                    format: str = 'csv'):
        """
        导出数据

        Args:
            symbols: 标的列表
            output_dir: 输出目录
            format: 导出格式 (csv/excel)
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for symbol in symbols:
            df = self.storage.load_data(symbol, 'daily')

            if df.empty:
                continue

            if format == 'csv':
                file_path = output_path / f"{symbol}.csv"
                df.to_csv(file_path)
            elif format == 'excel':
                file_path = output_path / f"{symbol}.xlsx"
                df.to_excel(file_path)

        print(f"导出完成: {len(symbols)}个标的 -> {output_dir}")

    def initialize_from_qmt(self, symbol_type: str = 'stock',
                           years_back: int = 10):
        """
        从QMT初始化数据（首次使用）

        Args:
            symbol_type: 标的类型 (stock/bond)
            years_back: 回溯年数
        """
        print(f"\n首次初始化数据...")
        print(f"标的类型: {symbol_type}")
        print(f"时间范围: 最近{years_back}年\n")

        # 获取股票列表
        if symbol_type == 'stock':
            # 这里应该从QMT获取股票列表
            # 暂时使用示例代码
            symbols = self._get_stock_list()
        else:
            symbols = self._get_bond_list()

        # 计算日期范围
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365*years_back)).strftime('%Y-%m-%d')

        # 批量下载
        self.download_and_save(
            symbols, start_date, end_date,
            symbol_type=symbol_type
        )

    def get_all_stocks_list(self,
                          include_st: bool = True,
                          include_sz: bool = True,
                          include_bj: bool = True,
                          exclude_st: bool = True,
                          exclude_delisted: bool = True) -> List[str]:
        """
        从QMT获取全部A股列表

        Args:
            include_st: 是否包含上海市场
            include_sz: 是否包含深圳市场
            include_bj: 是否包含北交所
            exclude_st: 是否排除ST股票
            exclude_delisted: 是否排除退市股票

        Returns:
            股票代码列表
        """
        try:
            import sys
            workspace_dir = Path(__file__).parents[4]
            if str(workspace_dir) not in sys.path:
                sys.path.insert(0, str(workspace_dir))

            import easy_xt
            api = easy_xt.get_api()

            # 初始化数据服务
            try:
                api.init_data()
            except:
                pass

            print(f"🔍 尝试从QMT获取A股列表...")

            # 使用正确的板块名称：'沪深A股'
            try:
                stock_list = api.get_stock_list('沪深A股')

                if stock_list and len(stock_list) > 0:
                    print(f"✅ 从QMT获取到 {len(stock_list)} 只A股")
                    return stock_list
                else:
                    print(f"⚠️ QMT返回空列表")
            except Exception as e:
                print(f"⚠️ QMT获取股票列表失败: {e}")

        except Exception as e:
            print(f"⚠️ 连接QMT失败: {e}")

        # 使用预定义列表作为备用
        print(f"✅ 使用预定义股票列表")
        return self._get_predefined_stock_list()

    def _get_predefined_stock_list(self) -> List[str]:
        """获取预定义的股票列表（主要指数成分股）"""
        # 常见的大盘蓝筹股
        return [
            # 沪市主板
            '600000.SH', '600036.SH', '600519.SH', '600900.SH', '601318.SH',
            '601398.SH', '601857.SH', '601988.SH', '601288.SH', '601328.SH',
            '601668.SH', '601728.SH', '601888.SH', '601939.SH', '601998.SH',
            '600030.SH', '600048.SH', '600104.SH', '600276.SH', '600585.SH',
            '600690.SH', '600887.SH', '601012.SH', '601066.SH', '601088.SH',
            '601111.SH', '601138.SH', '601186.SH', '601225.SH', '601229.SH',
            '601231.SH', '601236.SH', '601288.SH', '601298.SH', '601318.SH',
            '601328.SH', '601390.SH', '601398.SH', '601601.SH', '601628.SH',
            '601633.SH', '601668.SH', '601669.SH', '601688.SH', '601766.SH',
            '601788.SH', '601818.SH', '601857.SH', '601888.SH', '601898.SH',
            '601901.SH', '601919.SH', '601928.SH', '601939.SH', '601958.SH',
            '601985.SH', '601988.SH', '601997.SH', '601998.SH', '603259.SH',
            '603288.SH', '603393.SH', '603501.SH', '603808.SH', '603833.SH',
            '603883.SH', '603993.SH', '688981.SH',  # 科创板

            # 深市主板
            '000001.SZ', '000002.SZ', '000006.SZ', '000008.SZ', '000009.SZ',
            '000011.SZ', '000012.SZ', '000025.SZ', '000027.SZ', '000028.SZ',
            '000031.SZ', '000032.SZ', '000034.SZ', '000035.SZ', '000036.SZ',
            '000039.SZ', '000040.SZ', '000043.SZ', '000045.SZ', '000046.SZ',
            '000059.SZ', '000060.SZ', '000061.SZ', '000062.SZ', '000063.SZ',
            '000066.SZ', '000069.SZ', '000070.SZ', '000078.SZ', '000088.SZ',
            '000089.SZ', '000090.SZ', '000096.SZ', '000099.SZ', '000100.SZ',
            '000150.SZ', '000157.SZ', '000158.SZ', '000166.SZ', '000333.SZ',
            '000338.SZ', '000400.SZ', '000401.SZ', '000402.SZ', '000413.SZ',
            '000415.SZ', '000423.SZ', '000425.SZ', '000501.SZ', '000525.SZ',
            '000528.SZ', '000537.SZ', '000538.SZ', '000539.SZ', '000540.SZ',
            '000541.SZ', '000543.SZ', '000547.SZ', '000550.SZ', '000555.SZ',
            '000568.SZ', '000581.SZ', '000596.SZ', '000600.SZ', '000603.SZ',
            '000623.SZ', '000625.SZ', '000627.SZ', '000629.SZ', '000630.SZ',
            '000636.SZ', '000651.SZ', '000652.SZ', '000661.SZ', '000665.SZ',
            '000666.SZ', '000671.SZ', '000672.SZ', '000683.SZ', '000686.SZ',
            '000708.SZ', '000709.SZ', '000712.SZ', '000717.SZ', '000718.SZ',
            '000723.SZ', '000725.SZ', '000726.SZ', '000727.SZ', '000728.SZ',
            '000729.SZ', '000732.SZ', '000733.SZ', '000735.SZ', '000736.SZ',
            '000737.SZ', '000738.SZ', '000739.SZ', '000746.SZ', '000750.SZ',
            '000758.SZ', '000761.SZ', '000766.SZ', '000767.SZ', '000768.SZ',
            '000768.SZ', '000772.SZ', '000776.SZ', '000783.SZ', '000786.SZ',
            '000788.SZ', '000789.SZ', '000790.SZ', '000791.SZ', '000792.SZ',
            '000793.SZ', '000795.SZ', '000796.SZ', '000797.SZ', '000798.SZ',
            '000799.SZ', '000800.SZ', '000801.SZ', '000802.SZ', '000807.SZ',
            '000826.SZ', '000828.SZ', '000830.SZ', '000831.SZ', '000839.SZ',
            '000848.SZ', '000849.SZ', '000850.SZ', '000851.SZ', '000858.SZ',
            '000860.SZ', '000861.SZ', '000863.SZ', '000868.SZ', '000875.SZ',
            '000876.SZ', '000878.SZ', '000880.SZ', '000883.SZ', '000885.SZ',
            '000888.SZ', '000889.SZ', '000890.SZ', '000893.SZ', '000895.SZ',
            '000898.SZ', '000900.SZ', '000901.SZ', '000902.SZ', '000903.SZ',
            '000905.SZ', '000906.SZ', '000908.SZ', '000909.SZ', '000910.SZ',
            '000911.SZ', '000912.SZ', '000913.SZ', '000915.SZ', '000916.SZ',
            '000917.SZ', '000920.SZ', '000921.SZ', '000922.SZ', '000923.SZ',
            '000925.SZ', '000926.SZ', '000927.SZ', '000928.SZ', '000929.SZ',
            '000930.SZ', '000931.SZ', '000932.SZ', '000933.SZ', '000935.SZ',
            '000936.SZ', '000937.SZ', '000938.SZ', '000939.SZ', '000948.SZ',
            '000950.SZ', '000951.SZ', '000957.SZ', '000959.SZ', '000960.SZ',
            '000961.SZ', '000963.SZ', '000966.SZ', '000967.SZ', '000969.SZ',
            '000970.SZ', '000971.SZ', '000973.SZ', '000975.SZ', '000977.SZ',
            '000981.SZ', '000987.SZ', '000988.SZ', '000989.SZ', '000990.SZ',
            '000993.SZ', '000996.SZ', '000997.SZ', '000998.SZ', '000999.SZ',

            # 创业板
            '300001.SZ', '300002.SZ', '300003.SZ', '300005.SZ', '300006.SZ',
            '300007.SZ', '300008.SZ', '300009.SZ', '300010.SZ', '300011.SZ',
            '300012.SZ', '300013.SZ', '300014.SZ', '300015.SZ', '300017.SZ',
            '300020.SZ', '300024.SZ', '300027.SZ', '300029.SZ', '300030.SZ',
            '300033.SZ', '300034.SZ', '300037.SZ', '300038.SZ', '300040.SZ',
            '300042.SZ', '300043.SZ', '300044.SZ', '300045.SZ', '300046.SZ',
            '300047.SZ', '300048.SZ', '300050.SZ', '300052.SZ', '300053.SZ',
            '300054.SZ', '300055.SZ', '300058.SZ', '300059.SZ', '300060.SZ',
            '300062.SZ', '300063.SZ', '300064.SZ', '300065.SZ', '300066.SZ',
            '300067.SZ', '300068.SZ', '300069.SZ', '300070.SZ', '300071.SZ',
            '300072.SZ', '300073.SZ', '300074.SZ', '300075.SZ', '300076.SZ',
            '300077.SZ', '300078.SZ', '300079.SZ', '300080.SZ', '300081.SZ',
            '300082.SZ', '300083.SZ', '300084.SZ', '300085.SZ', '300086.SZ',
            '300087.SZ', '300088.SZ', '300089.SZ', '300090.SZ', '300091.SZ',
            '300092.SZ', '300093.SZ', '300094.SZ', '300095.SZ', '300096.SZ',
            '300097.SZ', '300098.SZ', '300099.SZ', '300100.SZ', '300103.SZ',
            '300104.SZ', '300109.SZ', '300110.SZ', '300111.SZ', '300113.SZ',
            '300115.SZ', '300116.SZ', '300117.SZ', '300118.SZ', '300119.SZ',
            '300122.SZ', '300123.SZ', '300124.SZ', '300125.SZ', '300126.SZ',
            '300127.SZ', '300128.SZ', '300129.SZ', '300130.SZ', '300131.SZ',
            '300132.SZ', '300133.SZ', '300134.SZ', '300136.SZ', '300137.SZ',
            '300138.SZ', '300139.SZ', '300142.SZ', '300143.SZ', '300144.SZ',
            '300145.SZ', '300146.SZ', '300147.SZ', '300148.SZ', '300149.SZ',
            '300151.SZ', '300152.SZ', '300153.SZ', '300154.SZ', '300155.SZ',
            '300156.SZ', '300157.SZ', '300159.SZ', '300160.SZ', '300161.SZ',
            '300163.SZ', '300166.SZ', '300168.SZ', '300169.SZ', '300170.SZ',
            '300171.SZ', '300174.SZ', '300175.SZ', '300177.SZ', '300178.SZ',
            '300179.SZ', '300181.SZ', '300182.SZ', '300183.SZ', '300184.SZ',
            '300187.SZ', '300188.SZ', '300191.SZ', '300197.SZ', '300203.SZ',
            '300206.SZ', '300207.SZ', '300209.SZ', '300211.SZ', '300212.SZ',
            '300213.SZ', '300214.SZ', '300216.SZ', '300218.SZ', '300220.SZ',
            '300222.SZ', '300223.SZ', '300224.SZ', '300226.SZ', '300227.SZ',
            '300228.SZ', '300229.SZ', '300230.SZ', '300233.SZ', '300234.SZ',
            '300235.SZ', '300236.SZ', '300237.SZ', '300238.SZ', '300239.SZ',
            '300240.SZ', '300241.SZ', '300242.SZ', '300243.SZ', '300244.SZ',
            '300245.SZ', '300246.SZ', '300247.SZ', '300248.SZ', '300249.SZ',
            '300250.SZ', '300251.SZ', '300252.SZ', '300253.SZ', '300254.SZ',
            '300255.SZ', '300256.SZ', '300257.SZ', '300258.SZ', '300259.SZ',
            '300260.SZ', '300261.SZ', '300262.SZ', '300263.SZ', '300264.SZ',
            '300265.SZ', '300266.SZ', '300267.SZ', '300268.SZ', '300269.SZ',
            '300270.SZ', '300271.SZ', '300272.SZ', '300273.SZ', '300274.SZ',
            '300275.SZ', '300276.SZ', '300277.SZ', '300278.SZ', '300279.SZ',
            '300281.SZ', '300282.SZ', '300283.SZ', '300284.SZ', '300285.SZ',
            '300286.SZ', '300287.SZ', '300288.SZ', '300289.SZ', '300290.SZ',
            '300291.SZ', '300292.SZ', '300293.SZ', '300294.SZ', '300295.SZ',
            '300296.SZ', '300297.SZ', '300298.SZ', '300299.SZ', '300300.SZ',
        ]

    def get_all_convertible_bonds_list(self,
                                     exclude_delisted: bool = True) -> List[str]:
        """
        从QMT获取全部可转债列表

        Args:
            exclude_delisted: 是否排除已退市转债

        Returns:
            可转债代码列表
        """
        try:
            import sys
            workspace_dir = Path(__file__).parents[4]
            if str(workspace_dir) not in sys.path:
                sys.path.insert(0, str(workspace_dir))

            import easy_xt
            api = easy_xt.get_api()

            # 初始化数据服务
            try:
                api.init_data()
            except:
                pass

            print(f"🔍 尝试从QMT获取可转债列表...")

            # 使用api.get_stock_list()获取可转债列表
            try:
                bond_list = api.get_stock_list('可转债')

                if bond_list and len(bond_list) > 0:
                    print(f"✅ 从QMT获取到 {len(bond_list)} 只可转债")
                    return bond_list
                else:
                    print(f"⚠️ QMT返回空列表")
            except Exception as e:
                print(f"⚠️ QMT获取可转债列表失败: {e}")

        except Exception as e:
            print(f"⚠️ 连接QMT失败: {e}")

        # 使用预定义列表作为备用
        print(f"✅ 使用预定义可转债列表")
        return self._get_predefined_bond_list()

    def _get_predefined_bond_list(self) -> List[str]:
        """获取预定义的可转债列表"""
        return [
            # 沪市可转债 (11xxxx)
            '113011.SH', '113016.SH', '113020.SH', '113021.SH', '113022.SH',
            '113023.SH', '113024.SH', '113027.SH', '113028.SH', '113030.SH',
            '113031.SH', '113032.SH', '113033.SH', '113035.SH', '113036.SH',
            '113037.SH', '113038.SH', '113040.SH', '113041.SH', '113042.SH',
            '113043.SH', '113044.SH', '113045.SH', '113046.SH', '113047.SH',
            '113048.SH', '113049.SH', '113050.SH', '113051.SH', '113052.SH',
            '113053.SH', '113054.SH', '113055.SH', '113056.SH', '113057.SH',
            '113058.SH', '113059.SH', '113060.SH', '113061.SH', '113062.SH',
            '113063.SH', '113064.SH', '113065.SH', '113066.SH', '113067.SH',
            '113068.SH', '113069.SH', '113070.SH', '113071.SH', '113072.SH',
            '113073.SH', '113074.SH', '113075.SH', '113076.SH', '113077.SH',
            '113078.SH', '113079.SH', '113080.SH', '113081.SH', '113082.SH',
            '113083.SH', '113084.SH', '113085.SH', '113086.SH', '113087.SH',
            '113088.SH', '113089.SH', '113090.SH', '113091.SH', '113092.SH',
            '113093.SH', '113094.SH', '113095.SH', '113096.SH', '113097.SH',
            '113098.SH', '113099.SH', '113100.SH', '113101.SH', '113102.SH',
            '113103.SH', '113104.SH', '113105.SH', '113106.SH', '113107.SH',
            '113108.SH', '113109.SH', '113110.SH', '113111.SH', '113112.SH',
            '113113.SH', '113114.SH', '113115.SH', '113116.SH', '113117.SH',
            '113118.SH', '113119.SH', '113120.SH', '113121.SH', '113122.SH',
            '113123.SH', '113124.SH', '113125.SH', '113126.SH', '113127.SH',
            '113128.SH', '113129.SH', '113130.SH', '113131.SH', '113132.SH',
            '113133.SH', '113134.SH', '113135.SH', '113136.SH', '113137.SH',
            '113138.SH', '113139.SH', '113140.SH', '113141.SH', '113142.SH',
            '113143.SH', '113144.SH', '113145.SH', '113146.SH', '113147.SH',
            '113148.SH', '113149.SH', '113150.SH', '113151.SH', '113152.SH',
            '113153.SH', '113154.SH', '113155.SH', '113156.SH', '113157.SH',
            '113158.SH', '113159.SH', '113160.SH', '113161.SH', '113162.SH',
            '113163.SH', '113164.SH', '113165.SH', '113166.SH', '113167.SH',
            '113168.SH', '113169.SH', '113170.SH', '113171.SH', '113172.SH',
            '113173.SH', '113174.SH', '113175.SH', '113176.SH', '113177.SH',
            '113178.SH', '113179.SH', '113180.SH', '113181.SH', '113182.SH',
            '113183.SH', '113184.SH', '113185.SH', '113186.SH', '113187.SH',
            '113188.SH', '113189.SH', '113190.SH', '113191.SH', '113192.SH',
            '113193.SH', '113194.SH', '113195.SH', '113196.SH', '113197.SH',
            '113198.SH', '113199.SH', '113200.SH', '113201.SH', '113202.SH',
            '113203.SH', '113204.SH', '113205.SH', '113206.SH', '113207.SH',
            '113208.SH', '113209.SH', '113210.SH', '113211.SH', '113212.SH',
            '113213.SH', '113214.SH', '113215.SH', '113216.SH', '113217.SH',
            '113218.SH', '113219.SH', '113220.SH', '113221.SH', '113222.SH',
            '113223.SH', '113224.SH', '113225.SH', '113226.SH', '113227.SH',
            '113228.SH', '113229.SH', '113230.SH', '113231.SH', '113232.SH',
            '113233.SH', '113234.SH', '113235.SH', '113236.SH', '113237.SH',
            '113238.SH', '113239.SH', '113240.SH', '113241.SH', '113242.SH',
            '113243.SH', '113244.SH', '113245.SH', '113246.SH', '113247.SH',
            '113248.SH', '113249.SH', '113250.SH', '113251.SH', '113252.SH',
            '113253.SH', '113254.SH', '113255.SH', '113256.SH', '113257.SH',
            '113258.SH', '113259.SH', '113260.SH', '113261.SH', '113262.SH',
            '113263.SH', '113264.SH', '113265.SH', '113266.SH', '113267.SH',
            '113268.SH', '113269.SH', '113270.SH', '113271.SH', '113272.SH',
            '113273.SH', '113274.SH', '113275.SH', '113276.SH', '113277.SH',
            '113278.SH', '113279.SH', '113280.SH', '113281.SH', '113282.SH',
            '113283.SH', '113284.SH', '113285.SH', '113286.SH', '113287.SH',
            '113288.SH', '113289.SH', '113290.SH', '113291.SH', '113292.SH',
            '113293.SH', '113294.SH', '113295.SH', '113296.SH', '113297.SH',
            '113298.SH', '113299.SH', '113300.SH', '113501.SH', '113502.SH',
            '113503.SH', '113504.SH', '113505.SH', '113506.SH', '113507.SH',
            '113508.SH', '113509.SH', '113510.SH', '113511.SH', '113512.SH',
            '113513.SH', '113514.SH', '113515.SH', '113516.SH', '113517.SH',
            '113518.SH', '113519.SH', '113520.SH', '113521.SH', '113522.SH',
            '113523.SH', '113524.SH', '113525.SH', '113526.SH', '113527.SH',
            '113528.SH', '113529.SH', '113530.SH', '113531.SH', '113532.SH',
            '113533.SH', '113534.SH', '113535.SH', '113536.SH', '113537.SH',
            '113538.SH', '113539.SH', '113540.SH', '113541.SH', '113542.SH',
            '113543.SH', '113544.SH', '113545.SH', '113546.SH', '113547.SH',
            '113548.SH', '113549.SH', '113550.SH', '113551.SH', '113552.SH',
            '113553.SH', '113554.SH', '113555.SH', '113556.SH', '113557.SH',
            '113558.SH', '113559.SH', '113560.SH', '113561.SH', '113562.SH',
            '113563.SH', '113564.SH', '113565.SH', '113566.SH', '113567.SH',
            '113568.SH', '113569.SH', '113570.SH', '113571.SH', '113572.SH',
            '113573.SH', '113574.SH', '113575.SH', '113576.SH', '113577.SH',
            '113578.SH', '113579.SH', '113580.SH', '113581.SH', '113582.SH',
            '113583.SH', '113584.SH', '113585.SH', '113586.SH', '113587.SH',
            '113588.SH', '113589.SH', '113590.SH', '113591.SH', '113592.SH',
            '113593.SH', '113594.SH', '113595.SH', '113596.SH', '113597.SH',
            '113598.SH', '113599.SH', '113600.SH', '113601.SH', '113602.SH',
            '113603.SH', '113604.SH', '113605.SH', '113606.SH', '113607.SH',
            '113608.SH', '113609.SH', '113610.SH', '113611.SH', '113612.SH',
            '113613.SH', '113614.SH', '113615.SH', '113616.SH', '113617.SH',
            '113618.SH', '113619.SH', '113620.SH', '113621.SH', '113622.SH',
            '113623.SH', '113624.SH', '113625.SH', '113626.SH', '113627.SH',
            '113628.SH', '113629.SH', '113630.SH', '113631.SH', '113632.SH',
            '113633.SH', '113634.SH', '113635.SH', '113636.SH', '113637.SH',
            '113638.SH', '113639.SH', '113640.SH', '113641.SH', '113642.SH',
            '113643.SH', '113644.SH', '113645.SH', '113646.SH', '113647.SH',
            '113648.SH', '113649.SH', '113650.SH',

            # 深市可转债 (12xxxx)
            '127001.SZ', '127002.SZ', '127003.SZ', '127004.SZ', '127005.SZ',
            '127006.SZ', '127007.SZ', '127008.SZ', '127009.SZ', '127010.SZ',
            '127011.SZ', '127012.SZ', '127013.SZ', '127014.SZ', '127015.SZ',
            '127016.SZ', '127017.SZ', '127018.SZ', '127019.SZ', '127020.SZ',
            '127021.SZ', '127022.SZ', '127023.SZ', '127024.SZ', '127025.SZ',
            '127026.SZ', '127027.SZ', '127028.SZ', '127029.SZ', '127030.SZ',
            '127031.SZ', '127032.SZ', '127033.SZ', '127034.SZ', '127035.SZ',
            '127036.SZ', '127037.SZ', '127038.SZ', '127039.SZ', '127040.SZ',
            '127041.SZ', '127042.SZ', '127043.SZ', '127044.SZ', '127045.SZ',
            '127046.SZ', '127047.SZ', '127048.SZ', '127049.SZ', '127050.SZ',
            '127051.SZ', '127052.SZ', '127053.SZ', '127054.SZ', '127055.SZ',
            '127056.SZ', '127057.SZ', '127058.SZ', '127059.SZ', '127060.SZ',
            '127061.SZ', '127062.SZ', '127063.SZ', '127064.SZ', '127065.SZ',
            '127066.SZ', '127067.SZ', '127068.SZ', '127069.SZ', '127070.SZ',
            '127071.SZ', '127072.SZ', '127073.SZ', '127074.SZ', '127075.SZ',
            '127076.SZ', '127077.SZ', '127078.SZ', '127079.SZ', '127080.SZ',
            '127081.SZ', '127082.SZ', '127083.SZ', '127084.SZ', '127085.SZ',
            '127086.SZ', '127087.SZ', '127088.SZ', '127089.SZ', '127090.SZ',
            '127091.SZ', '127092.SZ', '127093.SZ', '127094.SZ', '127095.SZ',
            '127096.SZ', '127097.SZ', '127098.SZ', '127099.SZ', '127100.SZ',
            '128001.SZ', '128002.SZ', '128003.SZ', '128004.SZ', '128005.SZ',
            '128006.SZ', '128007.SZ', '128008.SZ', '128009.SZ', '128010.SZ',
            '128011.SZ', '128012.SZ', '128013.SZ', '128014.SZ', '128015.SZ',
            '128016.SZ', '128017.SZ', '128018.SZ', '128019.SZ', '128020.SZ',
            '128021.SZ', '128022.SZ', '128023.SZ', '128024.SZ', '128025.SZ',
            '128026.SZ', '128027.SZ', '128028.SZ', '128029.SZ', '128030.SZ',
            '128031.SZ', '128032.SZ', '128033.SZ', '128034.SZ', '128035.SZ',
            '128036.SZ', '128037.SZ', '128038.SZ', '128039.SZ', '128040.SZ',
            '128041.SZ', '128042.SZ', '128043.SZ', '128044.SZ', '128045.SZ',
            '128046.SZ', '128047.SZ', '128048.SZ', '128049.SZ', '128050.SZ',
            '128051.SZ', '128052.SZ', '128053.SZ', '128054.SZ', '128055.SZ',
            '128056.SZ', '128057.SZ', '128058.SZ', '128059.SZ', '128060.SZ',
            '128061.SZ', '128062.SZ', '128063.SZ', '128064.SZ', '128065.SZ',
            '128066.SZ', '128067.SZ', '128068.SZ', '128069.SZ', '128070.SZ',
            '128071.SZ', '128072.SZ', '128073.SZ', '128074.SZ', '128075.SZ',
            '128076.SZ', '128077.SZ', '128078.SZ', '128079.SZ', '128080.SZ',
            '128081.SZ', '128082.SZ', '128083.SZ', '128084.SZ', '128085.SZ',
            '128086.SZ', '128087.SZ', '128088.SZ', '128089.SZ', '128090.SZ',
            '128091.SZ', '128092.SZ', '128093.SZ', '128094.SZ', '128095.SZ',
            '128096.SZ', '128097.SZ', '128098.SZ', '128099.SZ', '128100.SZ',
            '123001.SZ', '123002.SZ', '123003.SZ', '123004.SZ', '123005.SZ',
            '123006.SZ', '123007.SZ', '123008.SZ', '123009.SZ', '123010.SZ',
            '123011.SZ', '123012.SZ', '123013.SZ', '123014.SZ', '123015.SZ',
            '123016.SZ', '123017.SZ', '123018.SZ', '123019.SZ', '123020.SZ',
        ]

    def _get_stock_list(self) -> List[str]:
        """获取股票列表（示例）- 已弃用，请使用get_all_stocks_list()"""
        return self.get_all_stocks_list()

    def _get_bond_list(self) -> List[str]:
        """获取可转债列表（示例）- 已弃用，请使用get_all_convertible_bonds_list()"""
        return self.get_all_convertible_bonds_list()

    def close(self):
        """关闭数据管理器"""
        if self.metadata:
            self.metadata.close()


if __name__ == '__main__':
    # 测试代码
    manager = LocalDataManager()

    # 测试下载
    manager.download_and_save(
        symbols=['000001.SZ', '600000.SH'],
        start_date='2023-01-01',
        end_date='2023-12-31'
    )

    # 测试加载
    data = manager.load_data(['000001.SZ'])
    print(f"加载数据: {list(data.keys())}")

    # 测试统计
    manager.print_summary()

    # 关闭
    manager.close()
