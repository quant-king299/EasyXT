# -*- coding: utf-8 -*-
"""
多数据源数据管理器
负责获取、清洗和转换回测所需的历史数据
支持多数据源：QMT → QStock → AKShare → 模拟数据
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import warnings
from enum import Enum

class DataSource(Enum):
    """数据源枚举"""
    DUCKDB = "duckdb"  # DuckDB本地数据库（最高优先级，性能最优）
    LOCAL = "local"    # 本地缓存（Parquet）
    QMT = "qmt"        # QMT实时数据
    QSTOCK = "qstock"  # QStock数据
    AKSHARE = "akshare" # AKShare数据
    MOCK = "mock"      # 模拟数据

class DataManager:
    """
    多数据源数据管理器
    
    功能特性：
    1. 多数据源支持：QMT → QStock → AKShare → 模拟数据
    2. 自动数据源切换和手动指定
    3. 数据清洗和质量检查
    4. 格式转换和标准化
    5. 数据源状态监控
    """
    
    def __init__(self, preferred_source: Optional[DataSource] = None,
                 use_local_cache: bool = True):
        """
        初始化数据管理器

        Args:
            preferred_source: 首选数据源，None表示自动选择
            use_local_cache: 是否使用本地缓存
        """
        self.preferred_source = preferred_source
        self.use_local_cache = use_local_cache

        # 初始化DuckDB数据库（最高优先级）
        self.duckdb_connection = None
        self.duckdb_path = 'D:/StockData/stock_data.ddb'
        self._duckdb_enabled = False  # 标记DuckDB是否可用
        try:
            import duckdb
            # 延迟连接，不在初始化时打开
            self._duckdb_enabled = True
            print("[OK] DuckDB数据库已启用 (只读模式)")
        except ImportError:
            print("[INFO] DuckDB未安装，跳过DuckDB数据源")
        except Exception as e:
            print(f"[WARNING] DuckDB初始化失败: {e}")

        # 本地数据管理器（Parquet缓存）已弃用 - 所有数据使用DuckDB
        self.local_data_manager = None
        # 注释：旧版本使用Parquet文件作为缓存，现已全部迁移到DuckDB

        # 检查各数据源可用性
        self.source_status = self._check_all_sources()

        # 确定数据源优先级
        self.source_priority = self._get_source_priority()

        # 显示初始化状态
        self._print_initialization_status()
        
    def _check_all_sources(self) -> Dict[DataSource, Dict[str, any]]:
        """检查所有数据源的可用性"""
        status = {}

        # 检查DuckDB数据库
        status[DataSource.DUCKDB] = self._check_duckdb_status()

        # 检查本地缓存（Parquet）
        status[DataSource.LOCAL] = self._check_local_status()

        # 检查QMT
        status[DataSource.QMT] = self._check_qmt_status()

        # 检查QStock
        status[DataSource.QSTOCK] = self._check_qstock_status()

        # 检查AKShare
        status[DataSource.AKSHARE] = self._check_akshare_status()

        # 模拟数据总是可用
        status[DataSource.MOCK] = {
            'available': True,
            'connected': True,
            'message': '模拟数据生成器'
        }

        return status

    def _check_duckdb_status(self) -> Dict[str, any]:
        """检查DuckDB数据库状态"""
        if self.duckdb_connection is not None:
            try:
                # 测试查询
                result = self.duckdb_connection.execute("""
                    SELECT COUNT(*) as count FROM stock_daily LIMIT 1
                """).fetchone()

                if result and result[0] > 0:
                    return {
                        'available': True,
                        'connected': True,
                        'message': f'DuckDB数据库 ({result[0]:,}条记录)'
                    }
                else:
                    return {
                        'available': True,
                        'connected': False,
                        'message': 'DuckDB数据库为空'
                    }
            except Exception as e:
                return {
                    'available': False,
                    'connected': False,
                    'message': f'DuckDB查询失败: {str(e)[:50]}'
                }
        return {
            'available': False,
            'connected': False,
            'message': 'DuckDB未连接'
        }

    def _check_local_status(self) -> Dict[str, any]:
        """检查本地缓存状态"""
        if self.local_data_manager is not None:
            stats = self.local_data_manager.get_statistics()
            total_symbols = stats.get('total_symbols', 0)
            return {
                'available': True,
                'connected': total_symbols > 0,
                'message': f'本地缓存 ({total_symbols}个标的)'
            }
        return {
            'available': False,
            'connected': False,
            'message': '本地缓存未启用'
        }
        
    def _check_qmt_status(self) -> Dict[str, any]:
        """检查QMT状态"""
        try:
            import xtquant.xtdata as xt_data
            
            # 快速连接检测
            import threading
            result = {'connected': False}
            
            def quick_check():
                try:
                    info = xt_data.get_instrument_detail('000001.SZ')
                    if info and len(info) > 0:
                        result['connected'] = True
                except:
                    result['connected'] = False
            
            check_thread = threading.Thread(target=quick_check)
            check_thread.daemon = True
            check_thread.start()
            check_thread.join(timeout=5.0)  # 增加超时时间到5秒
            
            return {
                'available': True,
                'connected': result['connected'],
                'message': 'QMT已连接' if result['connected'] else 'QMT未连接'
            }
            
        except ImportError:
            return {
                'available': False,
                'connected': False,
                'message': 'xtquant模块未安装'
            }
        except Exception as e:
            return {
                'available': True,
                'connected': False,
                'message': f'QMT连接检测失败: {str(e)}'
            }
    
    def _check_qstock_status(self) -> Dict[str, any]:
        """检查QStock状态"""
        try:
            import qstock as qs

            # 尝试获取一个简单的数据来测试连接
            try:
                # 测试获取股票列表（这个操作通常比较快）
                # 使用更简单的测试方式，避免 qstock.get_data() 的兼容性问题
                try:
                    # 方法1：尝试获取股票列表（更稳定）
                    stock_list = qs.get_stock_list()
                    if stock_list is not None and len(stock_list) > 0:
                        return {
                            'available': True,
                            'connected': True,
                            'message': f'QStock连接正常 (股票列表: {len(stock_list)}只)'
                        }
                    else:
                        return {
                            'available': True,
                            'connected': False,
                            'message': 'QStock无法获取股票列表'
                        }
                except Exception as list_err:
                    # 方法2：如果获取列表失败，尝试简单获取数据
                    # 添加超时和异常处理
                    try:
                        import warnings
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            test_data = qs.get_data('000001', start='2024-01-01', end='2024-01-02')
                    except Exception as data_err:
                        # qstock.get_data() 也失败了，返回不可用状态
                        return {
                            'available': False,
                            'connected': False,
                            'message': f'QStock连接失败: {str(data_err)[:100]}'
                        }

                # 检查是否成功获取数据
                if test_data is not None and not test_data.empty:
                    return {
                        'available': True,
                        'connected': True,
                        'message': 'QStock连接正常'
                    }
                else:
                    return {
                        'available': True,
                        'connected': False,
                        'message': 'QStock无法获取数据'
                    }
            except Exception as e:
                return {
                    'available': True,
                    'connected': False,
                    'message': f'QStock连接测试失败: {str(e)}'
                }
                
        except ImportError:
            return {
                'available': False,
                'connected': False,
                'message': 'qstock模块未安装'
            }
    
    def _check_akshare_status(self) -> Dict[str, any]:
        """检查AKShare状态 - 优化版本"""
        try:
            import akshare as ak
            
            # AKShare模块已安装，标记为可用
            # 不进行实时连接测试，避免网络问题影响启动
            try:
                # 尝试一个轻量级的测试，如果失败也不影响可用性
                # 只是简单检查模块是否正常导入
                version = getattr(ak, '__version__', 'unknown')
                
                return {
                    'available': True,
                    'connected': True,  # 假设连接正常，实际使用时再处理错误
                    'message': f'AKShare模块已安装 (v{version})'
                }
                
            except Exception as e:
                # 即使测试失败，也标记为可用，因为模块已安装
                return {
                    'available': True,
                    'connected': True,  # 乐观假设，实际使用时处理错误
                    'message': f'AKShare模块已安装，连接状态未知'
                }
                
        except ImportError:
            return {
                'available': False,
                'connected': False,
                'message': 'akshare模块未安装'
            }
    
    def _get_source_priority(self) -> List[DataSource]:
        """获取数据源优先级列表"""
        if self.preferred_source:
            # 如果指定了首选数据源，将其放在首位
            priority = [self.preferred_source]
            other_sources = [s for s in DataSource if s != self.preferred_source]
            priority.extend(other_sources)
            return priority
        else:
            # 默认优先级：DuckDB → QMT → LOCAL → QStock → AKShare → MOCK
            # DuckDB优先，因为它性能最优且已迁移大量数据
            priority = [DataSource.QMT, DataSource.QSTOCK, DataSource.AKSHARE, DataSource.MOCK]

            # 如果DuckDB可用，放在第一位（最高优先级）
            if (self.duckdb_connection is not None and
                self.source_status[DataSource.DUCKDB]['connected']):
                priority.insert(0, DataSource.DUCKDB)

            # 如果本地缓存可用，放在第二位
            if (self.local_data_manager is not None and
                self.source_status[DataSource.LOCAL]['connected']):
                if DataSource.DUCKDB in priority:
                    # DuckDB已存在，插入到DuckDB之后
                    duckdb_idx = priority.index(DataSource.DUCKDB)
                    priority.insert(duckdb_idx + 1, DataSource.LOCAL)
                else:
                    # 没有DuckDB，插入到第一位
                    priority.insert(0, DataSource.LOCAL)

            return priority
    
    def _print_initialization_status(self):
        """打印初始化状态"""
        print("[DATA] 多数据源管理器初始化完成")
        print("=" * 50)
        
        for source in DataSource:
            status = self.source_status[source]
            if status['available']:
                if status['connected']:
                    icon = "[OK]"
                    color_status = "已连接"
                else:
                    icon = "[WARNING]"
                    color_status = "未连接"
            else:
                icon = "[ERROR]"
                color_status = "不可用"

            print(f"   {icon} {source.value.upper():<8}: {color_status} - {status['message']}")
        
        print("=" * 50)
        
        # 显示当前可用的数据源
        available_sources = [s.value.upper() for s in self.source_priority 
                           if self.source_status[s]['available'] and self.source_status[s]['connected']]
        
        if available_sources:
            print(f"[TARGET] 可用数据源: {' → '.join(available_sources)}")
        else:
            print("[INFO] 仅模拟数据可用")
        
        print("=" * 50)
    
    def get_connection_status(self) -> Dict[str, any]:
        """获取连接状态信息"""
        # 找到第一个可用且已连接的数据源
        active_source = None
        for source in self.source_priority:
            if (self.source_status[source]['available'] and 
                self.source_status[source]['connected']):
                active_source = source
                break
        
        if not active_source:
            active_source = DataSource.MOCK
        
        return {
            'active_source': active_source.value,
            'source_status': {s.value: status for s, status in self.source_status.items()},
            'qmt_connected': self.source_status[DataSource.QMT]['connected'],
            'xt_available': self.source_status[DataSource.QMT]['available'],
            'data_source': 'real' if active_source != DataSource.MOCK else 'mock',
            'status_message': self._get_status_message(active_source)
        }
    
    def _get_status_message(self, active_source: DataSource) -> str:
        """获取状态消息"""
        if active_source == DataSource.DUCKDB:
            return "[OK] 使用DuckDB数据库，高速读取本地真实数据"
        elif active_source == DataSource.LOCAL:
            return "[OK] 使用本地缓存数据（真实历史数据）"
        elif active_source == DataSource.QMT:
            return "[OK] 已连接到QMT，使用真实市场数据"
        elif active_source == DataSource.QSTOCK:
            return "[OK] 已连接到QStock，使用真实市场数据"
        elif active_source == DataSource.AKSHARE:
            return "[OK] 已连接到AKShare，使用真实市场数据"
        else:
            return "[INFO] 使用模拟数据"
    
    def set_preferred_source(self, source: DataSource):
        """设置首选数据源"""
        self.preferred_source = source
        self.source_priority = self._get_source_priority()
        print(f"[INFO] 首选数据源已设置为: {source.value.upper()}")
    
    def refresh_source_status(self):
        """刷新所有数据源状态"""
        print("[RELOAD] 刷新数据源状态...")
        self.source_status = self._check_all_sources()
        self._print_initialization_status()
    
    def get_stock_data(self,
                      stock_code: str,
                      start_date: str,
                      end_date: str,
                      period: str = '1d',
                      force_source: Optional[DataSource] = None,
                      adjust: str = 'none') -> pd.DataFrame:
        """
        获取股票历史数据（支持多数据源 + 复权）

        Args:
            stock_code: 股票代码 (如 '000001.SZ')
            start_date: 开始日期 ('YYYY-MM-DD')
            end_date: 结束日期 ('YYYY-MM-DD')
            period: 数据周期 ('1d', '1h', '5m' 等)
            force_source: 强制使用指定数据源
            adjust: 复权类型 ('none'=不复权, 'front'=前复权, 'back'=后复权)

        Returns:
            包含OHLCV数据的DataFrame（已应用复权）
        """
        adjust_types = {'none': '不复权', 'front': '前复权', 'back': '后复权'}
        print(f"[DATA] 获取股票数据: {stock_code} ({start_date} ~ {end_date})")
        print(f"   复权类型: {adjust_types.get(adjust, adjust)}")

        # 如果强制指定数据源
        if force_source:
            print(f"[TARGET] 强制使用数据源: {force_source.value.upper()}")
            return self._get_data_from_source(force_source, stock_code, start_date, end_date, period, adjust)

        # 按优先级尝试各个数据源
        downloaded_from = None  # 记录从哪个数据源下载

        for source in self.source_priority:
            if (self.source_status[source]['available'] and
                self.source_status[source]['connected']):

                print(f"[LINK] 尝试数据源: {source.value.upper()}")

                try:
                    data = self._get_data_from_source(source, stock_code, start_date, end_date, period, adjust)
                    if not data.empty:
                        print(f"[OK] 成功从 {source.value.upper()} 获取数据")

                        # 如果不是从本地缓存获取，且启用了本地缓存，则保存到本地
                        if source != DataSource.LOCAL and self.local_data_manager is not None:
                            self._save_to_local_cache(stock_code, data)
                            downloaded_from = source.value

                        return data
                    else:
                        print(f"[WARNING] {source.value.upper()} 返回空数据，尝试下一个数据源")

                except Exception as e:
                    print(f"[WARNING] {source.value.upper()} 获取数据失败: {e}，尝试下一个数据源")
                    continue

        # 如果所有数据源都失败，使用模拟数据
        print("[INFO] 所有数据源失败，使用模拟数据")
        return self._get_data_from_source(DataSource.MOCK, stock_code, start_date, end_date, period, adjust)

    def _save_to_local_cache(self, stock_code: str, data: pd.DataFrame):
        """保存数据到本地缓存"""
        try:
            # 确保日期索引
            if not isinstance(data.index, pd.DatetimeIndex):
                if 'date' in data.columns:
                    data = data.set_index('date')
                data.index = pd.to_datetime(data.index)

            # 保存到本地
            success, file_size = self.local_data_manager.storage.save_data(
                data, stock_code, 'daily'
            )

            if success:
                # 更新元数据
                self.local_data_manager.metadata.update_data_version(
                    symbol=stock_code,
                    symbol_type='stock',
                    start_date=str(data.index.min().date()),
                    end_date=str(data.index.max().date()),
                    record_count=len(data),
                    file_size=file_size
                )
                print(f"[SAVE] 数据已缓存到本地")
        except Exception as e:
            print(f"[WARNING] 保存到本地缓存失败: {e}")
    
    def _get_data_from_source(self, source: DataSource, stock_code: str,
                            start_date: str, end_date: str, period: str, adjust: str = 'none') -> pd.DataFrame:
        """从指定数据源获取数据（支持复权）"""
        if source == DataSource.DUCKDB:
            return self._get_duckdb_data(stock_code, start_date, end_date, adjust)
        elif source == DataSource.LOCAL:
            return self._get_local_data(stock_code, start_date, end_date, adjust)
        elif source == DataSource.QMT:
            return self._get_qmt_data(stock_code, start_date, end_date, period, adjust)
        elif source == DataSource.QSTOCK:
            return self._get_qstock_data(stock_code, start_date, end_date, period)
        elif source == DataSource.AKSHARE:
            return self._get_akshare_data(stock_code, start_date, end_date, period)
        else:  # DataSource.MOCK
            return self._generate_mock_data(stock_code, start_date, end_date)

    def _get_duckdb_data(self, stock_code: str, start_date: str, end_date: str, adjust: str = 'none') -> pd.DataFrame:
        """从DuckDB数据库获取数据（高性能）"""
        try:
            if not self._duckdb_enabled:
                return pd.DataFrame()

            import duckdb

            # 按需打开连接，使用后立即关闭
            con = duckdb.connect(self.duckdb_path, read_only=True)
            try:
                # 构建SQL查询
                query = f"""
                    SELECT date, open, high, low, close, volume, amount
                    FROM stock_daily
                    WHERE stock_code = '{stock_code}'
                      AND date >= '{start_date}'
                      AND date <= '{end_date}'
                    ORDER BY date
                """

                # 执行查询
                df = con.execute(query).df()

                if df.empty:
                    return pd.DataFrame()

                # 确保日期索引
                if 'date' in df.columns:
                    df = df.set_index('date')
                    df.index = pd.to_datetime(df.index)

                # 数据清洗
                df = self._standardize_columns(df)
                df = self._clean_data(df)

                print(f"[OK] DuckDB获取 {len(df)} 条数据")

                return df

            finally:
                # 立即关闭连接
                con.close()

        except Exception as e:
            print(f"[ERROR] DuckDB查询失败: {e}")
            return pd.DataFrame()

        except Exception as e:
            print(f"[WARNING] DuckDB获取数据失败: {e}")
            return pd.DataFrame()

    def _get_local_data(self, stock_code: str, start_date: str, end_date: str, adjust: str = 'none') -> pd.DataFrame:
        """从本地缓存获取数据（支持复权）"""
        try:
            if self.local_data_manager is None:
                return pd.DataFrame()

            # 尝试使用支持复权的数据管理器
            try:
                from data_manager.local_data_manager_with_adjustment import LocalDataManager as LocalDataManagerWithAdjustment
                manager_adjust = LocalDataManagerWithAdjustment()
                df = manager_adjust.load_data(stock_code, 'daily', adjust=adjust)
                manager_adjust.close()

                if not df.empty:
                    df = self._standardize_columns(df)
                    df = self._clean_data(df)
                    print(f"[OK] 本地缓存获取 {len(df)} 条数据（复权类型: {adjust}）")
                    return df
                else:
                    return pd.DataFrame()

            except Exception:
                # 回退到原始方法
                local_results = self.local_data_manager.storage.load_batch(
                    [stock_code], 'daily', start_date, end_date
                )

                if stock_code in local_results:
                    df = local_results[stock_code]
                    df = self._standardize_columns(df)
                    df = self._clean_data(df)
                    print(f"[OK] 本地缓存获取 {len(df)} 条数据（无复权）")
                    return df

            return pd.DataFrame()

        except Exception as e:
            print(f"[WARNING] 本地缓存获取失败: {e}")
            return pd.DataFrame()

    def _get_qmt_data(self, stock_code: str, start_date: str, end_date: str, period: str, adjust: str = 'none') -> pd.DataFrame:
        """通过QMT获取真实数据（支持复权）"""
        try:
            import xtquant.xtdata as xt_data
            
            # 转换日期格式
            start_time = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y%m%d')
            end_time = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y%m%d')
            
            # 映射复权类型
            dividend_map = {
                'none': 'none',
                'front': 'front',
                'back': 'back'
            }
            dividend_type = dividend_map.get(adjust, 'none')

            # 获取历史数据（支持复权）
            data = xt_data.get_market_data_ex(
                stock_list=[stock_code],
                period=period,
                start_time=start_time,
                end_time=end_time,
                dividend_type=dividend_type,  # ← 添加复权参数
                fill_data=True
            )
            
            if data and stock_code in data:
                df = data[stock_code]
                
                # 标准化列名
                df = self._standardize_columns(df)
                
                # 数据清洗
                df = self._clean_data(df)
                
                print(f"[OK] QMT获取 {len(df)} 条数据")
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"[WARNING] QMT获取数据失败: {e}")
            return pd.DataFrame()
    
    def _get_qstock_data(self, stock_code: str, start_date: str, end_date: str, period: str) -> pd.DataFrame:
        """通过QStock获取数据"""
        try:
            import qstock as qs
            
            # 转换股票代码格式 (去掉后缀)
            code = stock_code.split('.')[0]
            
            # 获取数据
            data = qs.get_data(code, start=start_date, end=end_date)
            
            if data is not None and not data.empty:
                # QStock返回的数据格式通常是标准的OHLCV格式
                df = data.copy()
                
                # 标准化列名
                df = self._standardize_columns(df)
                
                # 数据清洗
                df = self._clean_data(df)
                
                print(f"[OK] QStock获取 {len(df)} 条数据")
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"[WARNING] QStock获取数据失败: {e}")
            return pd.DataFrame()
    
    def _get_akshare_data(self, stock_code: str, start_date: str, end_date: str, period: str) -> pd.DataFrame:
        """通过AKShare获取数据 - 增强错误处理版本"""
        import time
        
        try:
            import akshare as ak
            
            # 转换股票代码格式
            code = stock_code.split('.')[0]
            
            # 根据代码后缀确定市场
            if stock_code.endswith('.SZ'):
                symbol = code
            elif stock_code.endswith('.SH'):
                symbol = code
            else:
                symbol = code
            
            print(f"[RELOAD] 尝试通过AKShare获取 {stock_code} 数据...")
            
            # 重试机制：最多尝试3次
            max_retries = 3
            retry_delay = 2  # 秒
            
            for attempt in range(max_retries):
                try:
                    # 获取历史数据
                    data = ak.stock_zh_a_hist(
                        symbol=symbol,
                        period="daily",
                        start_date=start_date.replace('-', ''),
                        end_date=end_date.replace('-', ''),
                        adjust="qfq"  # 前复权
                    )
                    
                    if data is not None and not data.empty:
                        # AKShare返回的列名通常是中文，需要转换
                        column_mapping = {
                            '日期': 'date',
                            '开盘': 'open',
                            '收盘': 'close', 
                            '最高': 'high',
                            '最低': 'low',
                            '成交量': 'volume',
                            '成交额': 'amount',
                            '振幅': 'amplitude',
                            '涨跌幅': 'pct_change',
                            '涨跌额': 'change',
                            '换手率': 'turnover'
                        }
                        
                        df = data.rename(columns=column_mapping)
                        
                        # 设置日期索引
                        if 'date' in df.columns:
                            df['date'] = pd.to_datetime(df['date'])
                            df.set_index('date', inplace=True)
                        
                        # 标准化列名
                        df = self._standardize_columns(df)
                        
                        # 数据清洗
                        df = self._clean_data(df)
                        
                        print(f"[OK] AKShare获取 {len(df)} 条数据 (尝试 {attempt + 1}/{max_retries})")
                        return df
                    else:
                        print(f"[WARNING] AKShare返回空数据 (尝试 {attempt + 1}/{max_retries})")
                        
                except Exception as retry_e:
                    print(f"[WARNING] AKShare获取失败 (尝试 {attempt + 1}/{max_retries}): {str(retry_e)}")
                    
                    # 如果不是最后一次尝试，等待后重试
                    if attempt < max_retries - 1:
                        print(f"[WAIT] 等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                    else:
                        # 最后一次尝试失败，记录详细错误信息
                        error_msg = str(retry_e)
                        if "Server disconnected" in error_msg:
                            print("[INFO] 提示：AKShare服务器连接问题，可能是网络不稳定或服务器维护")
                        elif "timeout" in error_msg.lower():
                            print("[INFO] 提示：请求超时，建议检查网络连接")
                        elif "403" in error_msg or "forbidden" in error_msg.lower():
                            print("[INFO] 提示：访问被拒绝，可能触发了反爬虫机制")
                        else:
                            print(f"[INFO] 提示：AKShare数据获取失败，错误详情：{error_msg}")
            
            # 所有重试都失败了
            print(f"[ERROR] AKShare获取 {stock_code} 数据失败，已尝试 {max_retries} 次")
            return pd.DataFrame()
                
        except ImportError:
            print("[WARNING] akshare模块未安装，请运行: pip install akshare")
            return pd.DataFrame()
        except Exception as e:
            print(f"[ERROR] AKShare模块加载失败: {str(e)}")
            return pd.DataFrame()
    
    def _generate_mock_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """生成模拟数据"""
        print(f"[INFO] 生成模拟数据: {stock_code}")
        
        # 创建日期范围
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        dates = dates[dates.weekday < 5]  # 只保留工作日
        
        # 生成价格数据
        np.random.seed(hash(stock_code) % 2**32)  # 基于股票代码的固定种子
        
        # 基础价格
        base_price = 10.0 + (hash(stock_code) % 100)
        
        # 生成收盘价（随机游走）
        returns = np.random.normal(0.001, 0.02, len(dates))  # 日收益率
        close_prices = [base_price]
        
        for ret in returns[1:]:
            new_price = close_prices[-1] * (1 + ret)
            close_prices.append(max(new_price, 0.1))  # 防止价格为负
        
        close_prices = np.array(close_prices)
        
        # 生成其他价格数据
        high_prices = close_prices * (1 + np.abs(np.random.normal(0, 0.01, len(dates))))
        low_prices = close_prices * (1 - np.abs(np.random.normal(0, 0.01, len(dates))))
        
        # 开盘价基于前一日收盘价
        open_prices = np.roll(close_prices, 1)
        open_prices[0] = base_price
        open_prices = open_prices * (1 + np.random.normal(0, 0.005, len(dates)))
        
        # 确保价格关系合理 (low <= open,close <= high)
        for i in range(len(dates)):
            low_prices[i] = min(low_prices[i], open_prices[i], close_prices[i])
            high_prices[i] = max(high_prices[i], open_prices[i], close_prices[i])
        
        # 生成成交量
        volumes = np.random.lognormal(10, 1, len(dates)).astype(int) * 100
        
        # 创建DataFrame
        df = pd.DataFrame({
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volumes
        }, index=dates)
        
        print(f"[OK] 生成 {len(df)} 条模拟数据")
        return df
    
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        column_mapping = {
            'Open': 'open',
            'High': 'high', 
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'Adj Close': 'adj_close'
        }
        
        # 重命名列
        df = df.rename(columns=column_mapping)
        
        # 确保必要列存在
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in df.columns:
                if col == 'volume':
                    df[col] = 0
                else:
                    # 如果缺少价格列，用close价格填充
                    df[col] = df.get('close', 0)
        
        return df
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据清洗"""
        print("[WIZARD] 开始数据清洗...")
        
        original_length = len(df)
        
        # 1. 删除空值
        df = df.dropna()
        
        # 2. 删除价格为0或负数的数据
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in df.columns:
                df = df[df[col] > 0]
        
        # 3. 检查价格关系的合理性
        if all(col in df.columns for col in price_columns):
            # high >= max(open, close) and low <= min(open, close)
            valid_mask = (
                (df['high'] >= df[['open', 'close']].max(axis=1)) &
                (df['low'] <= df[['open', 'close']].min(axis=1))
            )
            df = df[valid_mask]
        
        # 4. 删除异常波动的数据（日涨跌幅超过20%）
        if 'close' in df.columns and len(df) > 1:
            returns = df['close'].pct_change()
            normal_mask = (returns.abs() <= 0.2) | returns.isna()
            df = df[normal_mask]
        
        # 5. 确保成交量为正数
        if 'volume' in df.columns:
            df = df[df['volume'] >= 0]
        
        cleaned_length = len(df)
        removed_count = original_length - cleaned_length
        
        if removed_count > 0:
            print(f"[WIZARD] 数据清洗完成，删除 {removed_count} 条异常数据")
        
        return df
    
    def get_multiple_stocks_data(self, 
                               stock_codes: List[str], 
                               start_date: str, 
                               end_date: str) -> Dict[str, pd.DataFrame]:
        """
        获取多只股票的数据
        
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            股票代码到DataFrame的字典
        """
        print(f"[DATA] 批量获取 {len(stock_codes)} 只股票数据...")
        
        results = {}
        for stock_code in stock_codes:
            try:
                data = self.get_stock_data(stock_code, start_date, end_date)
                if not data.empty:
                    results[stock_code] = data
                else:
                    print(f"[WARNING] {stock_code} 数据为空")
            except Exception as e:
                print(f"[WARNING] 获取 {stock_code} 数据失败: {e}")
        
        print(f"[OK] 成功获取 {len(results)} 只股票数据")
        return results
    
    def validate_data_quality(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        验证数据质量
        
        Args:
            df: 待验证的数据
            
        Returns:
            数据质量报告
        """
        report = {
            'total_records': len(df),
            'date_range': {
                'start': self._safe_format_date(df.index.min() if not df.empty else None),
                'end': self._safe_format_date(df.index.max() if not df.empty else None)
            },
            'missing_values': df.isnull().sum().to_dict(),
            'data_completeness': (1 - df.isnull().sum() / len(df)).to_dict() if not df.empty else {},
            'price_statistics': {},
            'issues': []
        }
        
        if df.empty:
            report['issues'].append('数据为空')
            return report
        
        # 价格统计
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in df.columns:
                report['price_statistics'][col] = {
                    'min': float(df[col].min()),
                    'max': float(df[col].max()),
                    'mean': float(df[col].mean()),
                    'std': float(df[col].std())
                }
        
        # 检查数据问题
        if df.isnull().any().any():
            report['issues'].append('存在缺失值')
        
        if 'close' in df.columns:
            returns = df['close'].pct_change().dropna()
            if (returns.abs() > 0.2).any():
                report['issues'].append('存在异常波动（单日涨跌幅>20%）')
        
        # 检查价格关系
        if all(col in df.columns for col in price_columns):
            invalid_high = (df['high'] < df[['open', 'close']].max(axis=1)).any()
            invalid_low = (df['low'] > df[['open', 'close']].min(axis=1)).any()
            
            if invalid_high or invalid_low:
                report['issues'].append('存在不合理的价格关系')
        
        return report
    
    def resample_data(self, df: pd.DataFrame, freq: str) -> pd.DataFrame:
        """
        重采样数据到不同频率
        
        Args:
            df: 原始数据
            freq: 目标频率 ('1H', '4H', '1D', '1W', '1M')
            
        Returns:
            重采样后的数据
        """
        if df.empty:
            return df
        
        # OHLCV数据的重采样规则
        agg_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min', 
            'close': 'last',
            'volume': 'sum'
        }
        
        # 只对存在的列进行重采样
        available_agg = {k: v for k, v in agg_dict.items() if k in df.columns}
        
        resampled = df.resample(freq).agg(available_agg)
        
        # 删除空值行
        resampled = resampled.dropna()
        
        print(f"[DATA] 数据重采样完成: {len(df)} -> {len(resampled)} 条记录 (频率: {freq})")
        
        return resampled
    
    def _safe_format_date(self, date_obj) -> Optional[str]:
        """安全地格式化日期对象"""
        if date_obj is None:
            return None
        
        try:
            # 如果是pandas Timestamp对象
            if hasattr(date_obj, 'strftime'):
                return date_obj.strftime('%Y-%m-%d')
            # 如果是datetime对象
            elif hasattr(date_obj, 'date'):
                return date_obj.date().strftime('%Y-%m-%d')
            # 尝试转换为pandas Timestamp
            else:
                return pd.to_datetime(date_obj).strftime('%Y-%m-%d')
        except Exception as e:
            print(f"[WARNING] 日期格式化失败: {e}")
            return None

    # ========== 本地缓存管理方法 ==========

    def update_local_cache(self, symbols: List[str] = None, days_back: int = 5):
        """
        更新本地缓存数据

        Args:
            symbols: 要更新的股票列表，None表示全部
            days_back: 向前回溯天数
        """
        if self.local_data_manager is None:
            print("[WARNING] 本地缓存未启用")
            return

        print("[RELOAD] 更新本地缓存...")
        self.local_data_manager.update_data(symbols=symbols)
        print("[OK] 更新完成")

        # 刷新本地缓存状态
        self.source_status[DataSource.LOCAL] = self._check_local_status()

    def get_local_cache_status(self) -> Dict[str, any]:
        """获取本地缓存状态"""
        if self.local_data_manager is None:
            return {'enabled': False}

        stats = self.local_data_manager.get_statistics()
        return {
            'enabled': True,
            'total_symbols': stats.get('total_symbols', 0),
            'total_records': stats.get('total_records', 0),
            'total_size_mb': stats.get('total_size_mb', 0),
            'latest_date': stats.get('latest_data_date', 'N/A')
        }

    def print_local_cache_status(self):
        """打印本地缓存状态"""
        if self.local_data_manager is None:
            print("[WARNING] 本地缓存未启用")
            return

        print("\n" + "=" * 50)
        print("本地缓存状态")
        print("=" * 50)
        self.local_data_manager.print_summary()
        print("=" * 50 + "\n")

    def clear_local_cache(self, symbol: str = None):
        """
        清除本地缓存

        Args:
            symbol: 要清除的股票代码，None表示全部清除
        """
        if self.local_data_manager is None:
            print("[WARNING] 本地缓存未启用")
            return

        # TODO: 实现清除功能
        print(f"[WARNING] 清除本地缓存功能待实现")

    def preload_data(self, symbols: List[str], start_date: str, end_date: str):
        """
        预加载数据到本地缓存

        Args:
            symbols: 股票列表
            start_date: 开始日期
            end_date: 结束日期
        """
        if self.local_data_manager is None:
            print("[WARNING] 本地缓存未启用")
            return

        print(f"📦 预加载 {len(symbols)} 只股票数据...")

        for symbol in symbols:
            try:
                # 尝试从其他数据源获取并保存
                data = self.get_stock_data(symbol, start_date, end_date, force_source=None)
                # get_stock_data会自动缓存到本地
            except Exception as e:
                print(f"[WARNING] 预加载 {symbol} 失败: {e}")

        print("[OK] 预加载完成")


if __name__ == "__main__":
    # 测试数据管理器
    dm = DataManager()
    
    # 测试单只股票数据获取
    data = dm.get_stock_data('000001.SZ', '2023-01-01', '2023-12-31')
    print(f"[DATA] 获取数据形状: {data.shape}")
    print(f"[DATA] 数据列: {list(data.columns)}")
    
    # 测试数据质量验证
    quality_report = dm.validate_data_quality(data)
    print(f"[DATA] 数据质量报告: {quality_report}")
    
    # 测试数据重采样
    weekly_data = dm.resample_data(data, '1W')
    print(f"[DATA] 周线数据形状: {weekly_data.shape}")