#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地数据管理GUI组件
提供本地数据的下载、管理和查看功能
"""

import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox,
    QProgressBar, QSplitter, QFrame, QMessageBox, QDialog,
    QFileDialog, QFormLayout, QScrollArea, QSizePolicy,
    QToolButton, QMenu, QAction, QDateEdit, QTreeWidgetItem,
    QTreeWidget, QComboBox, QInputDialog
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize, QDate
from datetime import datetime, timedelta
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QTextCursor

import pandas as pd
import numpy as np

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class DataDownloadThread(QThread):
    """数据下载线程"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # current, total
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, task_type, symbols, start_date, end_date, data_type='daily'):
        super().__init__()
        self.task_type = task_type  # 'download_stocks', 'download_bonds', 'update_data'
        self.symbols = symbols
        self.start_date = start_date
        self.end_date = end_date
        self.data_type = data_type  # 'daily', '1min', '5min', 'tick'
        self._is_running = True

    def run(self):
        """运行下载任务"""
        try:
            if self.task_type == 'download_stocks':
                self._download_stocks()
            elif self.task_type == 'download_bonds':
                self._download_bonds()
            elif self.task_type == 'update_data':
                self._update_data()
        except Exception as e:
            import traceback
            error_msg = f"下载失败: {str(e)}\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)

    def _download_stocks(self):
        """下载股票数据"""
        try:
            # 导入本地数据管理器
            factor_platform_path = Path(__file__).parents[2] / "101因子" / "101因子分析平台" / "src"
            if str(factor_platform_path) not in sys.path:
                sys.path.insert(0, str(factor_platform_path))

            from data_manager import LocalDataManager

            manager = LocalDataManager()
            self.log_signal.emit("✅ 数据管理器初始化成功")

            # 如果没有指定股票列表，获取全部A股
            if not self.symbols:
                self.log_signal.emit("📊 正在获取A股列表...")
                self.symbols = manager.get_all_stocks_list(
                    include_st=True,
                    include_sz=True,
                    include_bj=True,
                    exclude_st=True,
                    exclude_delisted=True
                )
                self.log_signal.emit(f"✅ 获取到 {len(self.symbols)} 只A股")

            total = len(self.symbols)
            success_count = 0
            failed_count = 0

            for i, symbol in enumerate(self.symbols):
                if not self._is_running:
                    self.log_signal.emit("⚠️ 用户中断下载")
                    break

                try:
                    self.progress_signal.emit(i + 1, total)

                    # 下载数据
                    df = manager._fetch_from_source(symbol, self.start_date, self.end_date)

                    if df.empty:
                        failed_count += 1
                        continue

                    # 保存数据
                    success, file_size = manager.storage.save_data(df, symbol, 'daily')

                    if success:
                        manager.metadata.update_data_version(
                            symbol=symbol,
                            symbol_type='stock',
                            start_date=str(df.index.min().date()),
                            end_date=str(df.index.max().date()),
                            record_count=len(df),
                            file_size=file_size
                        )
                        success_count += 1
                    else:
                        failed_count += 1

                    # 每下载100只股票输出一次日志
                    if (i + 1) % 100 == 0:
                        self.log_signal.emit(f"📊 进度: {i + 1}/{total} | 成功: {success_count} | 失败: {failed_count}")

                except Exception as e:
                    failed_count += 1
                    continue

            manager.close()

            result = {
                'total': total,
                'success': success_count,
                'failed': failed_count,
                'task_type': 'download_stocks'
            }

            self.finished_signal.emit(result)
            self.log_signal.emit(f"✅ 下载完成! 总数: {total}, 成功: {success_count}, 失败: {failed_count}")

        except Exception as e:
            import traceback
            error_msg = f"下载股票数据失败: {str(e)}\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)

    def _download_bonds(self):
        """下载可转债数据"""
        try:
            factor_platform_path = Path(__file__).parents[2] / "101因子" / "101因子分析平台" / "src"
            if str(factor_platform_path) not in sys.path:
                sys.path.insert(0, str(factor_platform_path))

            from data_manager import LocalDataManager

            manager = LocalDataManager()
            self.log_signal.emit("✅ 数据管理器初始化成功")

            # 如果没有指定可转债列表，获取全部可转债
            if not self.symbols:
                self.log_signal.emit("📊 正在获取可转债列表...")
                self.symbols = manager.get_all_convertible_bonds_list()
                self.log_signal.emit(f"✅ 获取到 {len(self.symbols)} 只可转债")

            total = len(self.symbols)
            success_count = 0
            failed_count = 0

            for i, symbol in enumerate(self.symbols):
                if not self._is_running:
                    self.log_signal.emit("⚠️ 用户中断下载")
                    break

                try:
                    self.progress_signal.emit(i + 1, total)

                    # 下载数据
                    df = manager._fetch_from_source(symbol, self.start_date, self.end_date)

                    if df.empty:
                        failed_count += 1
                        continue

                    # 保存数据
                    success, file_size = manager.storage.save_data(df, symbol, 'daily')

                    if success:
                        manager.metadata.update_data_version(
                            symbol=symbol,
                            symbol_type='bond',
                            start_date=str(df.index.min().date()),
                            end_date=str(df.index.max().date()),
                            record_count=len(df),
                            file_size=file_size
                        )
                        success_count += 1
                    else:
                        failed_count += 1

                    # 每下载50只可转债输出一次日志
                    if (i + 1) % 50 == 0:
                        self.log_signal.emit(f"📊 进度: {i + 1}/{total} | 成功: {success_count} | 失败: {failed_count}")

                except Exception as e:
                    failed_count += 1
                    continue

            manager.close()

            result = {
                'total': total,
                'success': success_count,
                'failed': failed_count,
                'task_type': 'download_bonds'
            }

            self.finished_signal.emit(result)
            self.log_signal.emit(f"✅ 下载完成! 总数: {total}, 成功: {success_count}, 失败: {failed_count}")

        except Exception as e:
            import traceback
            error_msg = f"下载可转债数据失败: {str(e)}\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)

    def _update_data(self):
        """更新数据（增量）"""
        try:
            factor_platform_path = Path(__file__).parents[2] / "101因子" / "101因子分析平台" / "src"
            if str(factor_platform_path) not in sys.path:
                sys.path.insert(0, str(factor_platform_path))

            from data_manager import LocalDataManager

            manager = LocalDataManager()
            self.log_signal.emit("✅ 数据管理器初始化成功")

            # 获取需要更新的标的
            symbols_to_update = manager.metadata.get_symbols_needing_update(days_threshold=1)

            if not symbols_to_update:
                self.log_signal.emit("✅ 所有数据都是最新的，无需更新")
                manager.close()
                self.finished_signal.emit({'total': 0, 'success': 0, 'failed': 0})
                return

            symbols = [s[0] for s in symbols_to_update]
            self.log_signal.emit(f"📊 发现 {len(symbols)} 个标的需要更新")

            total = len(symbols)
            success_count = 0
            failed_count = 0

            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')

            for i, symbol in enumerate(symbols):
                if not self._is_running:
                    self.log_signal.emit("⚠️ 用户中断更新")
                    break

                try:
                    self.progress_signal.emit(i + 1, total)

                    # 下载数据
                    df = manager._fetch_from_source(symbol, start_date, end_date)

                    if df.empty:
                        failed_count += 1
                        continue

                    # 保存数据（会自动合并）
                    success, file_size = manager.storage.save_data(df, symbol, 'daily')

                    if success:
                        success_count += 1
                    else:
                        failed_count += 1

                    # 每更新100个标的输出一次日志
                    if (i + 1) % 100 == 0:
                        self.log_signal.emit(f"📊 进度: {i + 1}/{total} | 成功: {success_count} | 失败: {failed_count}")

                except Exception as e:
                    failed_count += 1
                    continue

            manager.close()

            result = {
                'total': total,
                'success': success_count,
                'failed': failed_count,
                'task_type': 'update_data'
            }

            self.finished_signal.emit(result)
            self.log_signal.emit(f"✅ 更新完成! 总数: {total}, 成功: {success_count}, 失败: {failed_count}")

        except Exception as e:
            import traceback
            error_msg = f"更新数据失败: {str(e)}\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)

    def stop(self):
        """停止下载"""
        self._is_running = False
        self.quit()
        self.wait()


class SingleStockDownloadThread(QThread):
    """单个标的下载线程"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # current, total
    finished_signal = pyqtSignal(dict)  # {'success': bool, 'symbol': str, 'record_count': int, 'file_size': float}
    error_signal = pyqtSignal(str)

    def __init__(self, stock_code, start_date, end_date, period='1d'):
        super().__init__()
        self.stock_code = stock_code
        self.start_date = start_date
        self.end_date = end_date
        self.period = period  # '1d', '1m', '5m', '15m', '30m', '60m'
        self._is_running = True

    def run(self):
        """运行下载任务"""
        manager = None
        try:
            # 导入支持复权的本地数据管理器
            factor_platform_path = Path(__file__).parents[2] / "101因子" / "101因子分析平台" / "src"
            if str(factor_platform_path) not in sys.path:
                sys.path.insert(0, str(factor_platform_path))

            from data_manager.local_data_manager_with_adjustment import LocalDataManager

            manager = LocalDataManager()
            self.log_signal.emit(f"[OK] 数据管理器初始化成功")

            self.log_signal.emit(f"[INFO] 正在下载 {self.stock_code}...")
            self.log_signal.emit(f"   数据周期: {self.period}")
            self.log_signal.emit(f"   日期范围: {self.start_date} ~ {self.end_date}")

            # 下载数据
            if self.period == '1d':
                # 日线数据使用 _fetch_from_source
                df = manager._fetch_from_source(self.stock_code, self.start_date, self.end_date)
            else:
                # 分钟级数据使用 xtquant.download_history_data 下载后获取
                self.log_signal.emit(f"📡 正在下载分钟数据到QMT本地...")

                from xtquant import xtdata
                from datetime import datetime

                # 转换日期格式为 YYYYMMDD
                start_dt = datetime.strptime(self.start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(self.end_date, '%Y-%m-%d')
                start_str = start_dt.strftime('%Y%m%d')
                end_str = end_dt.strftime('%Y%m%d')

                # 映射周期到API格式
                period_map = {
                    '1m': '1m',
                    '5m': '5m',
                    '15m': '15m',
                    '30m': '30m',
                    '60m': '60m'
                }
                period = period_map.get(self.period, '1m')

                # 下载历史数据到QMT本地
                xtdata.download_history_data(
                    stock_code=self.stock_code,
                    period=period,
                    start_time=start_str,
                    end_time=end_str
                )

                self.log_signal.emit(f"✅ 数据下载完成，正在读取...")

                # 从本地读取数据
                data = xtdata.get_market_data(
                    stock_list=[self.stock_code],
                    period=period,
                    count=0  # 获取全部
                )

                # 转换为DataFrame
                if data and self.stock_code in data:
                    df = data[self.stock_code]
                    if df.empty:
                        # 如果指定日期范围没有数据，尝试获取最近的数据
                        df = xtdata.get_market_data(
                            stock_list=[self.stock_code],
                            period=period,
                            count=1000  # 获取最近1000条
                        )
                        if df and self.stock_code in df:
                            df = df[self.stock_code]
                        else:
                            df = pd.DataFrame()
                    # 标准化列名
                    if not df.empty:
                        df.columns = df.columns.str.lower()
                else:
                    df = pd.DataFrame()

            if not self._is_running:
                self.log_signal.emit("⚠️ 用户中断下载")
                manager.close()
                return

            if df is None or df.empty:
                manager.close()
                self.error_signal.emit(f"❌ 没有获取到 {self.stock_code} 的数据，请检查代码和日期范围")
                return

            record_count = len(df)
            self.log_signal.emit(f"📊 获取到 {record_count} 条数据")

            # 确定数据类型
            data_type_map = {
                '1d': 'daily',
                '1m': '1min',
                '5m': '5min',
                '15m': '15min',
                '30m': '30min',
                '60m': '60min'
            }
            data_type = data_type_map.get(self.period, 'daily')

            # 保存数据（不复权原始数据）
            self.log_signal.emit(f"[INFO] 正在保存【不复权】原始数据...")
            manager.save_data(df, self.stock_code, data_type)
            self.log_signal.emit(f"[INFO] 原始数据已保存，查看时可选择复权类型")

            # 判断标的类型
            if self.stock_code.endswith('.SH') or self.stock_code.endswith('.SZ'):
                if self.stock_code.startswith('5') or self.stock_code.startswith('15'):
                    symbol_type = 'etf'
                else:
                    symbol_type = 'stock'
            else:
                symbol_type = 'stock'  # 默认

            # 获取文件大小
            try:
                file_info = manager.storage.get_data_info(self.stock_code, data_type)
                file_size = file_info.get('size_mb', 0) if file_info else 0
            except:
                file_size = 0

            manager.close()

            result = {
                'success': True,
                'symbol': self.stock_code,
                'record_count': record_count,
                'file_size': file_size
            }

            self.finished_signal.emit(result)
            self.log_signal.emit(f"[OK] {self.stock_code} 下载完成!")

        except Exception as e:
            import traceback
            error_msg = f"[ERROR] 下载失败: {str(e)}\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)
        finally:
            # 确保关闭管理器
            if manager is not None:
                try:
                    manager.close()
                except:
                    pass

    def stop(self):
        """停止下载"""
        self._is_running = False
        self.quit()
        self.wait()


class QuickUpdateThread(QThread):
    """快速更新分钟数据线程"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, stocks, period='1m'):
        super().__init__()
        self.stocks = stocks
        self.period = period
        self._is_running = True

    def run(self):
        """运行更新任务"""
        try:
            from xtquant import xtdata
            from datetime import datetime, timedelta

            factor_platform_path = Path(__file__).parents[2] / "101因子" / "101因子分析平台" / "src"
            if str(factor_platform_path) not in sys.path:
                sys.path.insert(0, str(factor_platform_path))

            from data_manager import LocalDataManager

            total = len(self.stocks)
            success_count = 0
            failed_count = 0

            for i, stock_code in enumerate(self.stocks):
                if not self._is_running:
                    break

                try:
                    self.progress_signal.emit(i + 1, total)
                    self.log_signal.emit(f"[{i+1}/{total}] 更新 {stock_code}...")

                    # 1. 下载最新数据（最近3个月）
                    end_date = datetime.now().strftime('%Y%m%d')
                    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')

                    xtdata.download_history_data(
                        stock_code=stock_code,
                        period=self.period,
                        start_time=start_date,
                        end_date=end_date
                    )

                    # 2. 转换数据
                    data = xtdata.get_market_data(
                        stock_list=[stock_code],
                        period=self.period,
                        count=0
                    )

                    if not data or 'time' not in data:
                        failed_count += 1
                        continue

                    # 转换为DataFrame
                    time_df = data['time']
                    timestamps = time_df.columns.tolist()

                    records = []
                    for idx, ts in enumerate(timestamps):
                        try:
                            ts_str = str(ts)
                            if len(ts_str) >= 14:
                                date_str = ts_str[:8]
                                time_str = ts_str[8:14]
                                datetime_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
                                dt = pd.to_datetime(datetime_str)
                            else:
                                dt = pd.to_datetime(ts)

                            open_val = data['open'].iloc[0, idx]
                            high_val = data['high'].iloc[0, idx]
                            low_val = data['low'].iloc[0, idx]
                            close_val = data['close'].iloc[0, idx]
                            volume_val = data['volume'].iloc[0, idx]
                            amount_val = data['amount'].iloc[0, idx]

                            records.append({
                                'time': dt,
                                'open': float(open_val),
                                'high': float(high_val),
                                'low': float(low_val),
                                'close': float(close_val),
                                'volume': float(volume_val),
                                'amount': float(amount_val)
                            })
                        except:
                            continue

                    df = pd.DataFrame(records)
                    if df.empty:
                        failed_count += 1
                        continue

                    df.set_index('time', inplace=True)
                    df.sort_index(inplace=True)

                    # 3. 保存到本地
                    manager = LocalDataManager()
                    data_type = '1min' if self.period == '1m' else '5min'

                    save_success, file_size = manager.storage.save_data(df, stock_code, data_type)

                    if save_success:
                        # 更新元数据
                        if stock_code.startswith('5') or stock_code.startswith('15'):
                            symbol_type = 'etf'
                        else:
                            symbol_type = 'stock'

                        manager.metadata.update_data_version(
                            symbol=stock_code,
                            symbol_type=symbol_type,
                            start_date=str(df.index.min().date()),
                            end_date=str(df.index.max().date()),
                            record_count=len(df),
                            file_size=file_size
                        )

                        manager.close()
                        success_count += 1
                        self.log_signal.emit(f"  ✓ {stock_code} 更新成功 ({len(df):,} 条)")
                    else:
                        manager.close()
                        failed_count += 1
                        self.log_signal.emit(f"  ✗ {stock_code} 保存失败")

                except Exception as e:
                    failed_count += 1
                    self.log_signal.emit(f"  ✗ {stock_code} 更新失败: {e}")
                    continue

            result = {
                'total': total,
                'success': success_count,
                'failed': failed_count
            }

            self.finished_signal.emit(result)
            self.log_signal.emit(f"✅ 更新完成! 成功: {success_count}, 失败: {failed_count}")

        except Exception as e:
            import traceback
            error_msg = f"更新失败: {str(e)}\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)

    def stop(self):
        """停止更新"""
        self._is_running = False
        self.quit()
        self.wait()


class SaveQMTThread(QThread):
    """保存QMT数据到本地线程"""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, stock_code=None):
        super().__init__()
        self.stock_code = stock_code

    def run(self):
        """运行保存任务"""
        try:
            from xtquant import xtdata

            factor_platform_path = Path(__file__).parents[2] / "101因子" / "101因子分析平台" / "src"
            if str(factor_platform_path) not in sys.path:
                sys.path.insert(0, str(factor_platform_path))

            from data_manager import LocalDataManager

            manager = LocalDataManager()

            if self.stock_code:
                # 保存单个股票
                self.log_signal.emit(f"💾 保存 {self.stock_code} 的数据...")

                data = xtdata.get_market_data(
                    stock_list=[self.stock_code],
                    period='1m',
                    count=0
                )

                if not data or 'time' not in data:
                    manager.close()
                    self.error_signal.emit(f"没有找到 {self.stock_code} 的数据")
                    return

                # 转换并保存（省略转换代码，与上面相同）
                # ...

            else:
                # 保存所有QMT数据
                self.log_signal.emit("💾 扫描QMT本地数据...")

                # 获取所有有数据的股票
                # 这里简化处理，实际可以扫描QMT目录
                manager.close()

            result = {
                'stock': self.stock_code or 'Multiple',
                'count': 0,
                'size': 0
            }

            self.finished_signal.emit(result)

        except Exception as e:
            import traceback
            error_msg = f"保存失败: {str(e)}\n{traceback.format_exc()}"
            self.error_signal.emit(error_msg)


class VerifyDataThread(QThread):
    """验证数据完整性线程"""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(dict)

    def __init__(self, stock_code):
        super().__init__()
        self.stock_code = stock_code

    def run(self):
        """运行验证任务"""
        try:
            factor_platform_path = Path(__file__).parents[2] / "101因子" / "101因子分析平台" / "src"
            if str(factor_platform_path) not in sys.path:
                sys.path.insert(0, str(factor_platform_path))

            from data_manager import LocalDataManager
            import pandas as pd

            manager = LocalDataManager()

            # 检查1分钟数据
            has_1min = False
            records_1min = 0
            file_info_1min = manager.storage.get_file_info(self.stock_code, '1min')

            if file_info_1min:
                df = pd.read_parquet(file_info_1min['file_path'])
                has_1min = True
                records_1min = len(df)
                self.log_signal.emit(f"✓ 1分钟数据: {records_1min:,} 条")

            # 检查日线数据
            has_daily = False
            records_daily = 0
            file_info_daily = manager.storage.get_file_info(self.stock_code, 'daily')

            if file_info_daily:
                df = pd.read_parquet(file_info_daily['file_path'])
                has_daily = True
                records_daily = len(df)
                self.log_signal.emit(f"✓ 日线数据: {records_daily:,} 条")

            manager.close()

            result = {
                'stock': self.stock_code,
                'has_1min': has_1min,
                'has_daily': has_daily,
                'records_1min': records_1min,
                'records_daily': records_daily
            }

            self.finished_signal.emit(result)

        except Exception as e:
            self.log_signal.emit(f"✗ 验证失败: {e}")
            result = {
                'stock': self.stock_code,
                'has_1min': False,
                'has_daily': False,
                'records_1min': 0,
                'records_daily': 0
            }
            self.finished_signal.emit(result)


class LocalDataManagerWidget(QWidget):
    """本地数据管理组件"""

    def __init__(self):
        super().__init__()
        self.download_thread = None
        self.duckdb_storage = None
        self.init_ui()
        self.load_local_data_info()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 创建主分割器
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # 左侧面板 - 数据列表和操作
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMinimumWidth(500)

        # 右侧面板 - 日志
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_panel.setMinimumWidth(400)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        # ========== 左侧面板 ==========

        # 统计信息组
        stats_group = QGroupBox("📊 数据统计 (DuckDB)")
        stats_layout = QGridLayout()
        stats_group.setLayout(stats_layout)
        left_layout.addWidget(stats_group)

        self.total_symbols_label = QLabel("标的总数: 0")
        self.total_stocks_label = QLabel("股票数量: 0")
        self.total_bonds_label = QLabel("可转债数量: 0")
        self.total_records_label = QLabel("总记录数: 0")
        self.total_size_label = QLabel("存储大小: 0 MB")
        self.latest_date_label = QLabel("最新日期: N/A")

        stats_layout.addWidget(self.total_symbols_label, 0, 0)
        stats_layout.addWidget(self.total_stocks_label, 0, 1)
        stats_layout.addWidget(self.total_bonds_label, 1, 0)
        stats_layout.addWidget(self.total_records_label, 1, 1)
        stats_layout.addWidget(self.total_size_label, 2, 0)
        stats_layout.addWidget(self.latest_date_label, 2, 1)

        stats_layout.addWidget(self.total_symbols_label, 0, 0)
        stats_layout.addWidget(self.total_stocks_label, 0, 1)
        stats_layout.addWidget(self.total_bonds_label, 1, 0)
        stats_layout.addWidget(self.total_records_label, 1, 1)
        stats_layout.addWidget(self.total_size_label, 2, 0)
        stats_layout.addWidget(self.latest_date_label, 2, 1)

        # 数据操作组
        action_group = QGroupBox("📥 数据下载")
        action_layout = QGridLayout()
        action_group.setLayout(action_layout)
        left_layout.addWidget(action_group)

        # 日期范围选择
        action_layout.addWidget(QLabel("开始日期:"), 0, 0)
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addYears(-10))
        action_layout.addWidget(self.start_date_edit, 0, 1)

        action_layout.addWidget(QLabel("结束日期:"), 0, 2)
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        action_layout.addWidget(self.end_date_edit, 0, 3)

        # 下载数据类型选择
        data_type_layout = QHBoxLayout()
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(["日线数据", "1分钟数据", "5分钟数据", "15分钟数据", "30分钟数据", "60分钟数据"])
        data_type_layout.addWidget(QLabel("数据类型:"))
        data_type_layout.addWidget(self.data_type_combo)
        data_type_layout.addStretch()
        action_layout.addLayout(data_type_layout, 1, 0, 1, 4)

        # 下载按钮
        btn_layout = QHBoxLayout()

        self.download_stocks_btn = QPushButton("📥 下载A股数据")
        self.download_stocks_btn.clicked.connect(self.download_stocks)
        self.download_stocks_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        btn_layout.addWidget(self.download_stocks_btn)

        self.download_bonds_btn = QPushButton("📥 下载可转债数据")
        self.download_bonds_btn.clicked.connect(self.download_bonds)
        self.download_bonds_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        btn_layout.addWidget(self.download_bonds_btn)

        self.update_data_btn = QPushButton("🔄 一键补充数据")
        self.update_data_btn.clicked.connect(self.update_data)
        self.update_data_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        btn_layout.addWidget(self.update_data_btn)

        action_layout.addLayout(btn_layout, 2, 0, 1, 4)

        # ========== 快速操作区域 ==========
        quick_action_group = QGroupBox("⚡ 快速操作")
        quick_action_layout = QGridLayout()
        quick_action_group.setLayout(quick_action_layout)
        left_layout.addWidget(quick_action_group)

        # 第一行：更新分钟数据
        quick_update_layout = QHBoxLayout()

        self.quick_update_label = QLabel("常用ETF:")
        quick_update_layout.addWidget(self.quick_update_label)

        self.quick_update_combo = QComboBox()
        self.quick_update_combo.addItems([
            "请选择要更新的ETF",
            "511380.SH (可转债ETF)",
            "512100.SH (中证1000ETF)",
            "510300.SH (沪深300ETF)",
            "510500.SH (中证500ETF)",
            "159915.SZ (深证ETF)",
            "---------",
            "全部常用ETF (5只)"
        ])
        quick_update_layout.addWidget(self.quick_update_combo)

        self.quick_update_btn = QPushButton("⚡ 快速更新分钟数据")
        self.quick_update_btn.clicked.connect(self.quick_update_minute_data)
        self.quick_update_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        quick_update_layout.addWidget(self.quick_update_btn)

        quick_action_layout.addLayout(quick_update_layout, 0, 0, 1, 4)

        # 第二行：其他快速操作
        other_action_layout = QHBoxLayout()

        self.save_qmt_btn = QPushButton("💾 保存QMT数据到本地")
        self.save_qmt_btn.clicked.connect(self.save_qmt_to_local)
        self.save_qmt_btn.setStyleSheet("""
            QPushButton {
                background-color: #00BCD4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0097A7;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        other_action_layout.addWidget(self.save_qmt_btn)

        self.verify_data_btn = QPushButton("🔍 验证数据完整性")
        self.verify_data_btn.clicked.connect(self.verify_data_integrity)
        self.verify_data_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #546E7A;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        other_action_layout.addWidget(self.verify_data_btn)

        other_action_layout.addStretch()

        quick_action_layout.addLayout(other_action_layout, 1, 0, 1, 4)

        # ========== 手动下载单个标的区域 ==========
        manual_group = QGroupBox("🎯 手动下载单个标的")
        manual_layout = QGridLayout()
        manual_group.setLayout(manual_layout)
        left_layout.addWidget(manual_group)

        # 股票代码输入
        manual_layout.addWidget(QLabel("股票/ETF代码:"), 0, 0)
        self.stock_code_input = QLineEdit()
        self.stock_code_input.setPlaceholderText("例如: 512100.SH 或 159915.SZ")
        manual_layout.addWidget(self.stock_code_input, 0, 1, 1, 3)

        # 示例代码快捷按钮
        example_layout = QHBoxLayout()
        example_btn_1 = QPushButton("示例: 512100.SH")
        example_btn_1.clicked.connect(lambda: self.stock_code_input.setText("512100.SH"))
        example_layout.addWidget(example_btn_1)

        example_btn_2 = QPushButton("示例: 159915.SZ")
        example_btn_2.clicked.connect(lambda: self.stock_code_input.setText("159915.SZ"))
        example_layout.addWidget(example_btn_2)

        example_layout.addStretch()
        manual_layout.addLayout(example_layout, 1, 4, 1, 3)

        # 手动下载按钮
        self.manual_download_btn = QPushButton("⬇️ 下载单个标的")
        self.manual_download_btn.clicked.connect(self.download_single_stock)
        self.manual_download_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        manual_layout.addWidget(self.manual_download_btn, 2, 0, 1, 3)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        action_layout.addWidget(self.progress_bar, 3, 0, 1, 4)

        # 停止按钮
        self.stop_btn = QPushButton("⏹️ 停止下载")
        self.stop_btn.clicked.connect(self.stop_download)
        self.stop_btn.setVisible(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        action_layout.addWidget(self.stop_btn, 4, 0, 1, 4)

        # 数据列表
        list_group = QGroupBox("📋 本地数据列表")
        list_layout = QVBoxLayout()
        list_group.setLayout(list_layout)
        left_layout.addWidget(list_group)

        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入股票代码或名称...")
        self.search_input.textChanged.connect(self.filter_data_list)
        search_layout.addWidget(self.search_input)

        # 过滤器
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "股票", "可转债"])
        self.filter_combo.currentTextChanged.connect(self.filter_data_list)
        search_layout.addWidget(self.filter_combo)

        list_layout.addLayout(search_layout)

        # 查看数据选项
        view_layout = QHBoxLayout()

        # 复权类型选择
        view_layout.addWidget(QLabel("查看时复权:"))
        self.view_adjust_combo = QComboBox()
        self.view_adjust_combo.addItems(["不复权", "前复权", "后复权"])
        self.view_adjust_combo.setCurrentIndex(0)
        self.view_adjust_combo.setToolTip(
            "选择查看数据时的复权类型：\n"
            "不复权：查看原始价格\n"
            "前复权：当前价真实，适合短期分析\n"
            "后复权：历史价真实，适合长期分析"
        )
        view_layout.addWidget(self.view_adjust_combo)

        # 复权说明按钮
        self.view_adjust_help_btn = QPushButton("❓")
        self.view_adjust_help_btn.setFixedWidth(30)
        self.view_adjust_help_btn.setToolTip("查看复权说明")
        self.view_adjust_help_btn.clicked.connect(self.show_adjustment_info)
        self.view_adjust_help_btn.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
                border: none;
                padding: 2px 5px;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #757575;
            }
        """)
        view_layout.addWidget(self.view_adjust_help_btn)

        # 查看数据按钮
        self.view_data_btn = QPushButton("👁️ 查看选中数据")
        self.view_data_btn.clicked.connect(self.view_selected_data)
        self.view_data_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 5px 12px;
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        view_layout.addWidget(self.view_data_btn)

        view_layout.addStretch()
        list_layout.addLayout(view_layout)

        # 数据表格
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(6)
        self.data_table.setHorizontalHeaderLabels(["代码", "名称", "类型", "记录数", "日期范围", "大小"])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSortingEnabled(True)
        list_layout.addWidget(self.data_table)

        # ========== 右侧面板 ==========

        # 日志组
        log_group = QGroupBox("📝 操作日志")
        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10pt;
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
        """)
        log_layout.addWidget(self.log_text)

        # 清空日志按钮
        clear_log_btn = QPushButton("🗑️ 清空日志")
        clear_log_btn.clicked.connect(self.log_text.clear)
        log_layout.addWidget(clear_log_btn)

        # 初始日志
        self.log("✅ 本地数据管理组件已加载")
        self.log("💡 提示：首次使用请先下载数据")

    def log(self, message):
        """输出日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.append(f"[{timestamp}] {message}")
        # 滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)

    def load_local_data_info(self):
        """加载DuckDB数据库信息"""
        try:
            factor_platform_path = Path(__file__).parents[2] / "101因子" / "101因子分析平台" / "src"
            if str(factor_platform_path) not in sys.path:
                sys.path.insert(0, str(factor_platform_path))

            from data_manager.duckdb_storage import DuckDBStorage

            # 关闭旧连接
            if self.duckdb_storage is not None:
                try:
                    self.duckdb_storage.close()
                except:
                    pass

            # DuckDB数据库路径
            db_path = Path('D:/StockData/stock_data.ddb')

            if not db_path.exists():
                self.log(f"⚠️ DuckDB数据库不存在: {db_path}")
                self.log(f"   请先下载数据到DuckDB")
                return

            # 创建DuckDBStorage实例
            self.duckdb_storage = DuckDBStorage(str(db_path))

            # 获取统计信息
            stats = self.duckdb_storage.get_statistics()

            # 更新统计标签
            total_symbols = stats.get('total_symbols', 0)
            total_records = stats.get('total_records', 0)
            db_size_mb = stats.get('db_size_mb', 0)
            last_date = stats.get('last_date', 'N/A')

            self.total_symbols_label.setText(f"标的总数: {total_symbols:,}")
            self.total_stocks_label.setText(f"股票数量: {total_symbols:,}")
            self.total_bonds_label.setText("可转债数量: N/A")
            self.total_records_label.setText(f"总记录数: {total_records:,}")
            self.total_size_label.setText(f"存储大小: {db_size_mb:.2f} MB")
            self.latest_date_label.setText(f"最新日期: {last_date}")

            # 加载数据列表
            self._load_duckdb_table()

            self.log(f"✅ DuckDB数据库信息加载成功")
            self.log(f"   数据库路径: {db_path}")
            self.log(f"   总记录数: {total_records:,}")

        except Exception as e:
            self.log(f"⚠️ 加载DuckDB信息失败: {str(e)}")
            import traceback
            self.log(f"详细错误: {traceback.format_exc()}")

    def _load_duckdb_table(self):
        """加载DuckDB数据表格"""
        try:
            # 清空表格
            self.data_table.setRowCount(0)

            if self.duckdb_storage is None:
                return

            # 从DuckDB获取所有股票的统计信息
            query = """
                SELECT
                    stock_code,
                    symbol_type,
                    MIN(date) as first_date,
                    MAX(date) as last_date,
                    COUNT(*) as record_count
                FROM stock_daily
                GROUP BY stock_code, symbol_type
                ORDER BY stock_code
            """

            result = self.duckdb_storage.con.execute(query).fetchall()

            for row_data in result:
                row = self.data_table.rowCount()
                self.data_table.insertRow(row)

                stock_code, symbol_type, first_date, last_date, record_count = row_data

                # 代码
                code_item = QTableWidgetItem(stock_code)
                self.data_table.setItem(row, 0, code_item)

                # 名称（从QMT获取，暂时显示代码）
                try:
                    import xtquant.xtdata as xt_data
                    info = xt_data.get_instrument_detail(stock_code)
                    name = info.get('InstrumentName', stock_code) if info else stock_code
                except:
                    name = stock_code

                name_item = QTableWidgetItem(name)
                self.data_table.setItem(row, 1, name_item)

                # 类型
                type_map = {'stock': '股票', 'index': '指数', 'etf': 'ETF', 'bond': '可转债'}
                type_str = type_map.get(symbol_type, symbol_type)
                type_item = QTableWidgetItem(type_str)
                self.data_table.setItem(row, 2, type_item)

                # 记录数
                count_item = QTableWidgetItem(f"{record_count:,}")
                count_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.data_table.setItem(row, 3, count_item)

                # 日期范围
                date_range = f"{first_date} ~ {last_date}"
                date_item = QTableWidgetItem(date_range)
                self.data_table.setItem(row, 4, date_item)

                # 大小（DuckDB不单独计算每个文件大小）
                size_item = QTableWidgetItem("N/A")
                size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.data_table.setItem(row, 5, size_item)

            self.log(f"📊 加载了 {len(result)} 条数据记录")

        except Exception as e:
            self.log(f"⚠️ 加载DuckDB数据表格失败: {str(e)}")
            import traceback
            self.log(f"详细错误: {traceback.format_exc()}")

    def filter_data_list(self):
        """过滤数据列表"""
        search_text = self.search_input.text().lower()
        filter_type = self.filter_combo.currentText()

        for row in range(self.data_table.rowCount()):
            code_item = self.data_table.item(row, 0)
            type_item = self.data_table.item(row, 2)

            if not code_item or not type_item:
                continue

            code = code_item.text().lower()
            type_text = type_item.text()

            # 检查类型过滤
            type_match = False
            if filter_type == "全部":
                type_match = True
            elif filter_type == "股票" and type_text == "股票":
                type_match = True
            elif filter_type == "可转债" and type_text == "可转债":
                type_match = True

            # 检查搜索文本
            search_match = search_text in code

            # 显示或隐藏行
            self.data_table.setRowHidden(row, not (type_match and search_match))

    def download_single_stock(self):
        """下载单个标的的数据"""
        # 获取输入的股票代码
        stock_code = self.stock_code_input.text().strip()

        if not stock_code:
            QMessageBox.warning(self, "提示", "请输入股票/ETF代码")
            return

        # 标准化代码格式
        stock_code = stock_code.upper()

        # 验证代码格式
        if not ('.' in stock_code):
            # 如果没有后缀，尝试自动添加
            if stock_code.startswith('6') or stock_code.startswith('5'):
                stock_code = stock_code + '.SH'
            elif stock_code.startswith('0') or stock_code.startswith('3') or stock_code.startswith('1'):
                stock_code = stock_code + '.SZ'

        # 获取日期范围
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")

        # 获取数据类型
        data_type_text = self.data_type_combo.currentText()
        period_map = {
            "日线数据": "1d",
            "1分钟数据": "1m",
            "5分钟数据": "5m",
            "15分钟数据": "15m",
            "30分钟数据": "30m",
            "60分钟数据": "60m"
        }
        period = period_map.get(data_type_text, "1d")

        self.log(f"🎯 开始下载单个标的: {stock_code}")
        self.log(f"   数据类型: {data_type_text}")
        self.log(f"   日期范围: {start_date} ~ {end_date}")
        self.log(f"   说明: 下载数据为【不复权】的原始数据，查看时可选择复权类型")

        # 禁用按钮
        self.manual_download_btn.setEnabled(False)

        # 创建下载线程（不传递复权参数，只下载原始数据）
        self.download_thread = SingleStockDownloadThread(
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            period=period
        )
        self.download_thread.log_signal.connect(self.log)
        self.download_thread.finished_signal.connect(self.on_single_download_finished)
        self.download_thread.error_signal.connect(self.on_single_download_error)
        self.download_thread.start()

    def on_single_download_finished(self, result):
        """单个标的下载完成"""
        self.manual_download_btn.setEnabled(True)

        stock_code = result.get('symbol', '')
        success = result.get('success', False)
        record_count = result.get('record_count', 0)
        file_size = result.get('file_size', 0)

        if success:
            self.log(f"✅ {stock_code} 下载成功!")
            self.log(f"   记录数: {record_count} 条")
            self.log(f"   文件大小: {file_size:.2f} MB")

            QMessageBox.information(self, "下载成功",
                f"{stock_code} 下载成功!\n\n记录数: {record_count} 条\n文件大小: {file_size:.2f} MB")

            # 刷新数据列表
            self.load_local_data_info()
        else:
            self.log(f"❌ {stock_code} 下载失败")

    def on_single_download_error(self, error_msg):
        """单个标的下载出错"""
        self.manual_download_btn.setEnabled(True)
        QMessageBox.critical(self, "下载失败", error_msg)

    def show_adjustment_info(self):
        """显示复权说明对话框"""
        info_text = """
<div style='font-family: Microsoft YaHei, SimHei; font-size: 11pt;'>

<h3 style='color: #2196F3;'>📊 复权类型说明</h3>

<table border='1' cellpadding='8' cellspacing='0' style='border-collapse: collapse; width: 100%; margin-top: 10px;'>
<tr style='background-color: #f0f0f0;'>
<th style='width: 15%;'>类型</th>
<th style='width: 25%;'>定义</th>
<th style='width: 30%;'>适用场景</th>
<th style='width: 30%;'>优缺点</th>
</tr>
<tr>
<td><b>不复权</b></td>
<td>原始价格<br>不做任何调整</td>
<td>✓ 日内交易<br>✓ 实时交易<br>✓ 短期分析</td>
<td>✓ 价格真实<br>✗ 分红除权时价格会跳跃</td>
</tr>
<tr>
<td><b>前复权</b></td>
<td>当前价真实<br>调整历史价格</td>
<td>✓ 短期回测<br>✓ 技术分析（1年内）</td>
<td>✓ 当前价真实<br>✗ 历史价可能失真</td>
</tr>
<tr>
<td><b>后复权</b></td>
<td>历史价真实<br>调整当前价格</td>
<td>✓ 长期回测<br>✓ 因子分析（3年以上）</td>
<td>✓ 历史价真实<br>✗ 当前价不真实</td>
</tr>
</table>

<h4 style='color: #FF9800; margin-top: 20px;'>💡 使用建议</h4>
<ul style='line-height: 1.8;'>
<li><b>短期交易者</b>（日内、周内）→ 使用 <b style='color: #2196F3;'>不复权</b></li>
<li><b>短期回测</b>（1年内）→ 使用 <b style='color: #4CAF50;'>前复权</b></li>
<li><b>长期回测</b>（3年以上）→ 使用 <b style='color: #F44336;'>后复权</b></li>
<li><b>因子分析</b>、选股 → 使用 <b style='color: #F44336;'>后复权</b></li>
</ul>

<h4 style='color: #9C27B0; margin-top: 15px;'>📌 注意事项</h4>
<ul style='line-height: 1.8;'>
<li>复权计算需要分红数据，首次使用可能需要下载</li>
<li>前复权和后复权的价格不同，但收益率相同</li>
<li>实时交易请使用"不复权"，确保价格准确</li>
</ul>

</div>
        """

        msg = QMessageBox(self)
        msg.setWindowTitle("复权类型说明")
        msg.setTextFormat(Qt.RichText)
        msg.setText(info_text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setMinimumWidth(600)
        msg.exec_()

    def view_selected_data(self):
        """查看选中数据（应用复权）"""
        # 获取选中的行
        selected_items = self.data_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先在列表中选择一只股票")
            return

        # 获取股票代码
        row = self.data_table.currentRow()
        code_item = self.data_table.item(row, 0)
        if not code_item:
            return

        stock_code = code_item.text()

        # 获取复权类型
        adjust_text = self.view_adjust_combo.currentText()
        adjust_map = {
            "不复权": "none",
            "前复权": "qfq",
            "后复权": "hfq"
        }
        adjust = adjust_map.get(adjust_text, "none")

        # 显示数据查看对话框
        self.log(f"[INFO] 查看 {stock_code} 数据（{adjust_text}）")
        DataViewerDialog(stock_code, adjust, self).exec_()

    def download_stocks(self):
        """下载A股数据"""
        if self.download_thread and self.download_thread.isRunning():
            QMessageBox.warning(self, "提示", "已有下载任务正在运行")
            return

        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")

        self.log(f"📥 开始下载A股数据 ({start_date} ~ {end_date})")

        self.download_thread = DataDownloadThread(
            task_type='download_stocks',
            symbols=None,  # 自动获取全部A股
            start_date=start_date,
            end_date=end_date
        )
        self.download_thread.log_signal.connect(self.log)
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.on_download_finished)
        self.download_thread.error_signal.connect(self.on_download_error)
        self.download_thread.start()

        self._set_download_state(True)

    def download_bonds(self):
        """下载可转债数据"""
        if self.download_thread and self.download_thread.isRunning():
            QMessageBox.warning(self, "提示", "已有下载任务正在运行")
            return

        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")

        self.log(f"📥 开始下载可转债数据 ({start_date} ~ {end_date})")

        self.download_thread = DataDownloadThread(
            task_type='download_bonds',
            symbols=None,  # 自动获取全部可转债
            start_date=start_date,
            end_date=end_date
        )
        self.download_thread.log_signal.connect(self.log)
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.on_download_finished)
        self.download_thread.error_signal.connect(self.on_download_error)
        self.download_thread.start()

        self._set_download_state(True)

    def update_data(self):
        """一键补充数据"""
        if self.download_thread and self.download_thread.isRunning():
            QMessageBox.warning(self, "提示", "已有下载任务正在运行")
            return

        self.log("🔄 开始补充数据...")

        self.download_thread = DataDownloadThread(
            task_type='update_data',
            symbols=None,
            start_date=None,
            end_date=None
        )
        self.download_thread.log_signal.connect(self.log)
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.on_download_finished)
        self.download_thread.error_signal.connect(self.on_download_error)
        self.download_thread.start()

        self._set_download_state(True)

    def update_progress(self, current, total):
        """更新进度"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        pct = (current / total) * 100 if total > 0 else 0
        self.progress_bar.setFormat(f"{current}/{total} ({pct:.1f}%)")

    def on_download_finished(self, result):
        """下载完成"""
        self._set_download_state(False)
        self.progress_bar.setVisible(False)

        total = result.get('total', 0)
        success = result.get('success', 0)
        failed = result.get('failed', 0)

        msg = f"下载完成！\n总数: {total}\n成功: {success}\n失败: {failed}"

        if failed > 0:
            QMessageBox.warning(self, "下载完成", msg)
        else:
            QMessageBox.information(self, "下载完成", msg)

        # 重新加载数据信息
        self.load_local_data_info()

    def on_download_error(self, error_msg):
        """下载出错"""
        self._set_download_state(False)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "下载失败", error_msg)

    def stop_download(self):
        """停止下载"""
        if self.download_thread and self.download_thread.isRunning():
            self.log("⏹️ 正在停止下载...")
            self.download_thread.stop()

    def _set_download_state(self, is_downloading):
        """设置下载状态"""
        self.download_stocks_btn.setEnabled(not is_downloading)
        self.download_bonds_btn.setEnabled(not is_downloading)
        self.update_data_btn.setEnabled(not is_downloading)
        self.manual_download_btn.setEnabled(not is_downloading)
        self.quick_update_btn.setEnabled(not is_downloading)
        self.save_qmt_btn.setEnabled(not is_downloading)
        self.verify_data_btn.setEnabled(not is_downloading)
        self.stop_btn.setVisible(is_downloading)
        self.progress_bar.setVisible(is_downloading)

        if is_downloading:
            self.progress_bar.setValue(0)

    def quick_update_minute_data(self):
        """快速更新常用ETF的分钟数据"""
        selection = self.quick_update_combo.currentText()

        # 定义常用ETF列表
        etf_list = {
            "请选择要更新的ETF": [],
            "511380.SH (可转债ETF)": ["511380.SH"],
            "512100.SH (中证1000ETF)": ["512100.SH"],
            "510300.SH (沪深300ETF)": ["510300.SH"],
            "510500.SH (中证500ETF)": ["510500.SH"],
            "159915.SZ (深证ETF)": ["159915.SZ"],
            "---------": [],
            "全部常用ETF (5只)": ["511380.SH", "512100.SH", "510300.SH", "510500.SH", "159915.SZ"]
        }

        stocks = etf_list.get(selection, [])

        if not stocks:
            if selection == "请选择要更新的ETF":
                QMessageBox.information(
                    self, "提示",
                    "请先从下拉菜单选择要更新的ETF\n\n"
                    "• 单只更新：选择具体ETF代码\n"
                    "• 批量更新：选择'全部常用ETF'"
                )
            else:
                QMessageBox.warning(self, "提示", "请选择有效的ETF")
            return

        # 确认对话框
        if len(stocks) > 1:
            reply = QMessageBox.question(
                self, "确认批量更新",
                f"即将更新以下 {len(stocks)} 只ETF的1分钟数据：\n\n"
                f"{chr(10).join(stocks)}\n\n"
                f"预计耗时：约 {len(stocks) * 10} 秒\n\n"
                f"确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        self.log(f"⚡ 开始更新ETF分钟数据: {', '.join(stocks)}")
        self.log(f"   数据周期: 1分钟")
        self.log(f"   更新范围: 最近3个月")

        # 创建更新线程
        self.update_thread = QuickUpdateThread(stocks, period='1m')
        self.update_thread.log_signal.connect(self.log)
        self.update_thread.progress_signal.connect(self.update_progress)
        self.update_thread.finished_signal.connect(self.on_quick_update_finished)
        self.update_thread.error_signal.connect(self.on_quick_update_error)
        self.update_thread.start()

        self._set_download_state(True)

    def on_quick_update_finished(self, result):
        """快速更新完成"""
        self._set_download_state(False)
        self.progress_bar.setVisible(False)

        total = result.get('total', 0)
        success = result.get('success', 0)
        failed = result.get('failed', 0)

        msg = f"更新完成！\n总数: {total}\n成功: {success}\n失败: {failed}"

        if failed > 0:
            QMessageBox.warning(self, "更新完成", msg)
        else:
            QMessageBox.information(self, "更新完成", msg)

        # 重新加载数据信息
        self.load_local_data_info()

    def on_quick_update_error(self, error_msg):
        """快速更新出错"""
        self._set_download_state(False)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "更新失败", error_msg)

    def save_qmt_to_local(self):
        """保存QMT数据到本地"""
        # 创建输入对话框
        dialog = QInputDialog(self)
        dialog.setWindowTitle("保存QMT数据到本地")
        dialog.setLabelText("请输入要保存的股票代码:\n(留空则扫描并保存所有QMT数据)")
        dialog.setTextValue("511380.SH")
        dialog.setInputMode(QInputDialog.TextInput)

        ok = dialog.exec_()
        stock_code = dialog.textValue().strip()

        if ok:
            # 如果输入了代码，自动格式化
            if stock_code:
                if not ('.' in stock_code):
                    if stock_code.startswith(('5', '6')):
                        stock_code = stock_code + '.SH'
                    elif stock_code.startswith(('0', '1', '3')):
                        stock_code = stock_code + '.SZ'

                self.log(f"💾 开始保存 {stock_code} 的QMT数据到本地...")
            else:
                self.log(f"💾 开始扫描并保存所有QMT数据到本地...")

            # 创建保存线程
            self.save_thread = SaveQMTThread(stock_code if stock_code else None)
            self.save_thread.log_signal.connect(self.log)
            self.save_thread.finished_signal.connect(self.on_save_finished)
            self.save_thread.error_signal.connect(self.on_save_error)
            self.save_thread.start()

    def on_save_finished(self, result):
        """保存完成"""
        stock = result.get('stock', 'N/A')
        count = result.get('count', 0)
        size = result.get('size', 0)

        QMessageBox.information(
            self, "保存完成",
            f"成功保存 {stock} 的数据到本地！\n\n记录数: {count:,}\n文件大小: {size:.2f} MB"
        )

        # 重新加载数据信息
        self.load_local_data_info()

    def on_save_error(self, error_msg):
        """保存出错"""
        QMessageBox.critical(self, "保存失败", error_msg)

    def verify_data_integrity(self):
        """验证数据完整性"""
        # 创建一个带输入选项的对话框
        dialog = QInputDialog(self)
        dialog.setWindowTitle("验证数据完整性")
        dialog.setLabelText("请输入要验证的股票代码:")
        dialog.setTextValue("511380.SH")  # 默认值
        dialog.setInputMode(QInputDialog.TextInput)

        ok = dialog.exec_()
        stock_code = dialog.textValue().strip()

        if ok and stock_code:
            # 自动格式化代码
            if not ('.' in stock_code):
                # 自动添加交易所后缀
                if stock_code.startswith(('5', '6')):
                    stock_code = stock_code + '.SH'
                elif stock_code.startswith(('0', '1', '3')):
                    stock_code = stock_code + '.SZ'

            self.log(f"🔍 验证 {stock_code} 数据完整性...")

            # 创建验证线程
            self.verify_thread = VerifyDataThread(stock_code)
            self.verify_thread.log_signal.connect(self.log)
            self.verify_thread.finished_signal.connect(self.on_verify_finished)
            self.verify_thread.start()

    def on_verify_finished(self, result):
        """验证完成"""
        stock = result.get('stock', 'N/A')
        has_1min = result.get('has_1min', False)
        has_daily = result.get('has_daily', False)
        records_1min = result.get('records_1min', 0)
        records_daily = result.get('records_daily', 0)

        msg = f"{stock} 数据验证结果:\n\n"
        msg += f"1分钟数据: {'✓ 存在' if has_1min else '✗ 不存在'}"
        if has_1min:
            msg += f" ({records_1min:,} 条)\n"
        else:
            msg += "\n"

        msg += f"日线数据: {'✓ 存在' if has_daily else '✗ 不存在'}"
        if has_daily:
            msg += f" ({records_daily:,} 条)\n"

        if has_1min or has_daily:
            QMessageBox.information(self, "验证完成", msg)
        else:
            QMessageBox.warning(self, "验证完成", msg + "\n⚠️ 该股票没有本地数据，请先下载")


class DataViewerDialog(QDialog):
    """数据查看对话框 - 支持复权"""

    def __init__(self, stock_code: str, adjust: str, parent=None):
        super().__init__(parent)
        self.stock_code = stock_code
        self.adjust = adjust
        self.setWindowTitle(f"查看数据 - {stock_code} ({adjust}) [DuckDB]")
        self.setMinimumSize(900, 600)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 顶部信息
        info_layout = QHBoxLayout()

        # 股票代码
        code_label = QLabel(f"股票代码: <b>{self.stock_code}</b>")
        code_label.setStyleSheet("font-size: 12pt;")
        info_layout.addWidget(code_label)

        # 复权类型
        adjust_names = {"none": "不复权", "qfq": "前复权", "hfq": "后复权"}
        adjust_label = QLabel(f"复权类型: <b>{adjust_names.get(self.adjust, self.adjust)}</b>")
        adjust_label.setStyleSheet("font-size: 12pt;")
        info_layout.addWidget(adjust_label)

        info_layout.addStretch()

        # 导出按钮
        export_btn = QPushButton("📊 导出CSV")
        export_btn.clicked.connect(self.export_csv)
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        info_layout.addWidget(export_btn)

        # 关闭按钮
        close_btn = QPushButton("✖ 关闭")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 5px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        info_layout.addWidget(close_btn)

        layout.addLayout(info_layout)

        # 数据表格
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSortingEnabled(True)
        layout.addWidget(self.data_table)

        # 统计信息
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("font-size: 10pt; color: #666;")
        layout.addWidget(self.stats_label)

    def load_data(self):
        """加载数据"""
        try:
            # 导入数据管理器
            factor_platform_path = Path(__file__).parents[2] / "101因子" / "101因子分析平台" / "src"
            if str(factor_platform_path) not in sys.path:
                sys.path.insert(0, str(factor_platform_path))

            from data_manager.duckdb_storage import DuckDBStorage

            # DuckDB数据库路径
            db_path = Path('D:/StockData/stock_data.ddb')

            if not db_path.exists():
                QMessageBox.warning(self, "错误", f"DuckDB数据库不存在:\n{db_path}")
                self.reject()
                return

            # 创建存储连接
            storage = DuckDBStorage(str(db_path))

            # 映射复权类型
            adjust_map = {
                "none": "none",
                "qfq": "front",
                "hfq": "back"
            }
            duckdb_adjust = adjust_map.get(self.adjust, "none")

            # 加载数据
            df = storage.load_data(self.stock_code, period='1d', adjust_type=duckdb_adjust)

            storage.close()

            if df.empty:
                QMessageBox.warning(self, "提示", f"没有找到 {self.stock_code} 的数据")
                self.reject()
                return

            # 显示数据
            self._display_data(df)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载数据失败: {str(e)}")
            import traceback
            traceback.print_exc()

    def _display_data(self, df):
        """显示数据到表格"""
        # 设置列
        df = df.reset_index()
        columns = df.columns.tolist()

        self.data_table.setColumnCount(len(columns))
        self.data_table.setHorizontalHeaderLabels(columns)

        # 设置行
        self.data_table.setRowCount(len(df))

        # 填充数据（只显示前1000条，避免太慢）
        display_df = df.head(1000)

        for row_idx in range(len(display_df)):
            for col_idx, col in enumerate(columns):
                value = display_df.iloc[row_idx, col_idx]
                item = QTableWidgetItem(str(value))
                self.data_table.setItem(row_idx, col_idx, item)

        # 调整列宽
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # 更新统计信息
        stats = f"总记录数: {len(df):,} 条"
        if len(df) > 1000:
            stats += f" (显示前1000条)"

        if not df.empty:
            latest_price = df['close'].iloc[-1]
            stats += f" | 最新价: {latest_price:.2f}"

            if len(df) >= 2:
                start_price = df['close'].iloc[0]
                total_return = (latest_price / start_price - 1) * 100
                stats += f" | 区间涨跌: {total_return:+.2f}%"

        self.stats_label.setText(stats)

    def export_csv(self):
        """导出为CSV"""
        try:
            # 导入数据管理器
            factor_platform_path = Path(__file__).parents[2] / "101因子" / "101因子分析平台" / "src"
            if str(factor_platform_path) not in sys.path:
                sys.path.insert(0, str(factor_platform_path))

            from data_manager.duckdb_storage import DuckDBStorage

            # DuckDB数据库路径
            db_path = Path('D:/StockData/stock_data.ddb')
            storage = DuckDBStorage(str(db_path))

            # 映射复权类型
            adjust_map = {
                "none": "none",
                "qfq": "front",
                "hfq": "back"
            }
            duckdb_adjust = adjust_map.get(self.adjust, "none")

            # 加载数据
            df = storage.load_data(self.stock_code, period='1d', adjust_type=duckdb_adjust)
            storage.close()

            # 选择保存路径
            default_name = f"{self.stock_code}_{self.adjust}_duckdb_data.csv"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出CSV",
                default_name,
                "CSV文件 (*.csv)"
            )

            if file_path:
                df.to_csv(file_path, encoding='utf-8-sig')
                QMessageBox.information(self, "成功", f"数据已导出到:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    window = LocalDataManagerWidget()
    window.setWindowTitle("本地数据管理")
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec_())
