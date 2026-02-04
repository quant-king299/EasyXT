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

widgets_path = os.path.join(project_root, 'gui_app', 'widgets')
if widgets_path not in sys.path:
    sys.path.insert(0, widgets_path)

# 导入财务数据保存线程
try:
    from advanced_data_viewer_widget import BatchFinancialSaveThread
    BATCH_SAVE_AVAILABLE = True
except ImportError:
    BATCH_SAVE_AVAILABLE = False


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
            elif self.task_type == 'backfill_history':
                self._backfill_history()
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
            failed_list = []  # 记录失败的股票及原因

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
                        failed_list.append(f"{symbol} - 数据为空")
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
                        failed_list.append(f"{symbol} - 保存失败")

                    # 每下载100只股票输出一次日志
                    if (i + 1) % 100 == 0:
                        self.log_signal.emit(f"📊 进度: {i + 1}/{total} | 成功: {success_count} | 失败: {failed_count}")

                except Exception as e:
                    failed_count += 1
                    failed_list.append(f"{symbol} - {str(e)[:50]}")
                    continue

            manager.close()

            result = {
                'total': total,
                'success': success_count,
                'failed': failed_count,
                'failed_list': failed_list,
                'task_type': 'download_stocks'
            }

            self.finished_signal.emit(result)
            self.log_signal.emit(f"✅ 下载完成! 总数: {total}, 成功: {success_count}, 失败: {failed_count}")

            # 输出失败清单
            if failed_list:
                self.log_signal.emit("")
                self.log_signal.emit("=" * 70)
                self.log_signal.emit("  失败清单:")
                for failed_item in failed_list:
                    self.log_signal.emit(f"    ✗ {failed_item}")
                self.log_signal.emit("=" * 70)

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
            failed_list = []  # 记录失败的可转债及原因

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
                        failed_list.append(f"{symbol} - 数据为空")
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
                        failed_list.append(f"{symbol} - 保存失败")

                    # 每下载50只可转债输出一次日志
                    if (i + 1) % 50 == 0:
                        self.log_signal.emit(f"📊 进度: {i + 1}/{total} | 成功: {success_count} | 失败: {failed_count}")

                except Exception as e:
                    failed_count += 1
                    failed_list.append(f"{symbol} - {str(e)[:50]}")
                    continue

            manager.close()

            result = {
                'total': total,
                'success': success_count,
                'failed': failed_count,
                'failed_list': failed_list,
                'task_type': 'download_bonds'
            }

            self.finished_signal.emit(result)
            self.log_signal.emit(f"✅ 下载完成! 总数: {total}, 成功: {success_count}, 失败: {failed_count}")

            # 输出失败清单
            if failed_list:
                self.log_signal.emit("")
                self.log_signal.emit("=" * 70)
                self.log_signal.emit("  失败清单:")
                for failed_item in failed_list:
                    self.log_signal.emit(f"    ✗ {failed_item}")
                self.log_signal.emit("=" * 70)

        except Exception as e:
            import traceback
            error_msg = f"下载可转债数据失败: {str(e)}\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)

    def _update_data(self):
        """更新数据（增量）- 使用DuckDB存储，批量处理避免连接冲突"""
        try:
            from data_manager.duckdb_connection_pool import get_db_manager
            from xtquant import xtdata
            import pandas as pd

            self.log_signal.emit("✅ 数据管理器初始化成功")

            # 获取DuckDB管理器
            manager = get_db_manager(r'D:/StockData/stock_data.ddb')

            # 查找需要更新的股票（落后超过0天，包括今天的数据）
            # 说明：落后0天表示今天的数据可能还没收盘，落后1天表示昨天数据缺失
            query = """
                SELECT
                    stock_code,
                    MAX(date) as latest_date,
                    DATEDIFF('day', MAX(date), CURRENT_DATE) as days_behind
                FROM stock_daily
                GROUP BY stock_code
                HAVING DATEDIFF('day', MAX(date), CURRENT_DATE) > 0
                ORDER BY days_behind DESC
            """

            df_stocks = manager.execute_read_query(query)

            if df_stocks.empty:
                self.log_signal.emit("✅ 所有数据都是最新的，无需更新")
                self.finished_signal.emit({'total': 0, 'success': 0, 'failed': 0, 'task_type': 'update_data'})
                return

            stock_codes = df_stocks['stock_code'].tolist()
            self.log_signal.emit(f"📊 发现 {len(stock_codes)} 只股票需要更新")

            total = len(stock_codes)
            success_count = 0
            failed_count = 0
            skipped_count = 0
            failed_list = []

            # === 步骤1: 批量收集所有数据（不写入数据库） ===
            self.log_signal.emit("📥 [步骤1/2] 从QMT批量收集数据...")
            update_data = []

            for i, stock_code in enumerate(stock_codes):
                if not self._is_running:
                    self.log_signal.emit("⚠️ 用户中断更新")
                    break

                try:
                    self.progress_signal.emit(i + 1, total)

                    # 进度显示
                    if (i + 1) % 100 == 0 or i == 0:
                        self.log_signal.emit(f"  📈 进度: {i+1}/{total} ({(i+1)/total*100:.1f}%)")

                    # 获取最新日期和落后天数
                    stock_data = df_stocks[df_stocks['stock_code'] == stock_code].iloc[0]
                    latest_date = stock_data['latest_date']
                    days_behind = stock_data['days_behind']

                    # 计算需要获取的条数
                    # 策略：最少30条，落后天数多时适当增加
                    # 考虑到QMT数据是最近往回数，获取足够的数据确保覆盖缺失
                    count = int(days_behind) + 30  # 增加30天缓冲
                    # 最少获取30条，最多获取500条（约2年数据）
                    count = max(30, min(count, 500))

                    # 从QMT获取数据（使用count参数）
                    data = xtdata.get_market_data_ex(
                        stock_list=[stock_code],
                        period='1d',
                        count=count
                    )

                    if isinstance(data, dict) and stock_code in data:
                        df = data[stock_code]
                        if not df.empty:
                            # 转换数据格式
                            df_processed = pd.DataFrame({
                                'stock_code': stock_code,
                                'symbol_type': 'stock',
                                'date': pd.to_datetime(df['time'], unit='ms').dt.strftime('%Y-%m-%d'),
                                'period': '1d',
                                'open': df['open'],
                                'high': df['high'],
                                'low': df['low'],
                                'close': df['close'],
                                'volume': df['volume'].astype('int64'),
                                'amount': df['amount'],
                                'adjust_type': 'none',
                                'factor': 1.0,
                                'created_at': datetime.now(),
                                'updated_at': datetime.now()
                            })

                            # 填充复权数据
                            for col in ['open', 'high', 'low', 'close']:
                                df_processed[f'{col}_front'] = df_processed[col]
                                df_processed[f'{col}_back'] = df_processed[col]
                                df_processed[f'{col}_geometric_front'] = df_processed[col]
                                df_processed[f'{col}_geometric_back'] = df_processed[col]

                            # 只保留最新日期之后的数据
                            latest_date_str = pd.to_datetime(latest_date).strftime('%Y-%m-%d')
                            df_processed = df_processed[df_processed['date'] > latest_date_str]

                            if not df_processed.empty:
                                update_data.append(df_processed)
                                success_count += 1
                            else:
                                skipped_count += 1
                        else:
                            skipped_count += 1
                    else:
                        failed_count += 1
                        failed_list.append(stock_code)

                except Exception as e:
                    self.log_signal.emit(f"  [{i+1}/{total}] {stock_code}: ✗ 错误 - {str(e)[:50]}")
                    failed_count += 1
                    failed_list.append(f"{stock_code} - {str(e)[:30]}")

            self.log_signal.emit(f"📥 数据收集完成: {len(update_data)} 条记录，来自 {success_count} 只股票")

            # === 步骤2: 批量写入DuckDB（一次性写入，减少连接时间） ===
            self.log_signal.emit("💾 [步骤2/2] 批量写入DuckDB...")
            self.log_signal.emit("⏳ 提示：写入期间请勿进行其他数据库操作...")

            if update_data:
                try:
                    # 合并所有数据
                    df_all = pd.concat(update_data, ignore_index=True)

                    # 使用延迟写入策略，给其他连接释放的时间
                    import time
                    self.log_signal.emit("⏳ 等待其他连接释放...")
                    time.sleep(2)  # 等待2秒，让其他可能的连接释放

                    # 一次性写入（连接池会自动重试）
                    self.log_signal.emit("💾 正在写入数据库...")
                    with manager.get_write_connection() as con:
                        con.register('temp_updates', df_all)
                        con.execute("INSERT INTO stock_daily SELECT * FROM temp_updates")
                        con.unregister('temp_updates')

                    self.log_signal.emit(f"✅ 成功保存 {len(df_all)} 条记录到数据库")
                except Exception as e:
                    self.log_signal.emit(f"❌ 批量写入失败: {str(e)}")
                    # 尝试分批写入
                    self.log_signal.emit("🔄 尝试分批写入...")
                    batch_size = 1000
                    success_batches = 0
                    for i in range(0, len(update_data), batch_size):
                        batch = update_data[i:i+batch_size]
                        df_batch = pd.concat(batch, ignore_index=True)
                        try:
                            # 每批次之间等待，让连接释放
                            if i > 0:
                                time.sleep(0.5)
                            with manager.get_write_connection() as con:
                                con.register('temp_batch', df_batch)
                                con.execute("INSERT INTO stock_daily SELECT * FROM temp_batch")
                                con.unregister('temp_batch')
                            success_batches += 1
                            self.log_signal.emit(f"  ✅ 批次 {i//batch_size + 1} 写入成功 ({len(df_batch)} 条)")
                        except Exception as batch_error:
                            self.log_signal.emit(f"  ❌ 批次 {i//batch_size + 1} 写入失败: {batch_error}")

                    if success_batches > 0:
                        self.log_signal.emit(f"✅ 分批写入完成，成功 {success_batches}/{(len(update_data)-1)//batch_size + 1} 个批次")

            # 输出结果
            result = {
                'total': total,
                'success': success_count,
                'failed': failed_count,
                'skipped': skipped_count,
                'failed_list': failed_list,
                'task_type': 'update_data'
            }

            self.finished_signal.emit(result)
            self.log_signal.emit(f"✅ 更新完成! 总数: {total}, 成功: {success_count}, 跳过: {skipped_count}, 失败: {failed_count}")

            # 输出失败清单
            if failed_list:
                self.log_signal.emit("")
                self.log_signal.emit("=" * 70)
                self.log_signal.emit("  失败清单:")
                for failed_item in failed_list[:20]:  # 只显示前20个
                    self.log_signal.emit(f"    ✗ {failed_item}")
                if len(failed_list) > 20:
                    self.log_signal.emit(f"    ... 还有 {len(failed_list) - 20} 只")
                self.log_signal.emit("=" * 70)

        except ImportError as e:
            error_msg = f"导入模块失败: {str(e)}\n请确保 data_manager.duckdb_connection_pool 模块可用"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)
        except Exception as e:
            import traceback
            error_msg = f"更新数据失败: {str(e)}\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)

    def _backfill_history(self):
        """补充历史数据（从2018年开始）"""
        try:
            from data_manager.duckdb_connection_pool import get_db_manager
            from xtquant import xtdata
            import pandas as pd

            self.log_signal.emit("✅ 数据管理器初始化成功")

            # 获取DuckDB管理器
            manager = get_db_manager(r'D:/StockData/stock_data.ddb')

            # 查询所有股票及其最早日期
            query = """
                SELECT
                    stock_code,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date
                FROM stock_daily
                GROUP BY stock_code
                ORDER BY stock_code
            """

            df_stocks = manager.execute_read_query(query)

            if df_stocks.empty:
                self.log_signal.emit("⚠️ 数据库中没有数据，请先下载A股数据")
                self.finished_signal.emit({'total': 0, 'success': 0, 'failed': 0, 'task_type': 'backfill_history'})
                return

            # 筛选需要补充历史的股票（最早日期晚于2018-06-01）
            cutoff_date = pd.to_datetime('2018-06-01')
            needs_backfill = df_stocks[df_stocks['earliest_date'] > cutoff_date]

            if needs_backfill.empty:
                self.log_signal.emit("✅ 所有股票都有完整历史数据")
                self.finished_signal.emit({'total': 0, 'success': 0, 'failed': 0, 'task_type': 'backfill_history'})
                return

            stock_codes = needs_backfill['stock_code'].tolist()
            self.log_signal.emit(f"📊 发现 {len(stock_codes)} 只股票需要补充历史数据")

            # 从QMT获取完整历史数据（使用较大count值）
            # 2018-06到2026年约2000个交易日
            count = 2500
            self.log_signal.emit(f"📡 将获取每只股票的最近 {count} 条数据...")

            total = len(stock_codes)
            success_count = 0
            failed_count = 0
            failed_list = []
            backfill_data = []

            for i, stock_code in enumerate(stock_codes):
                try:
                    # 进度显示
                    if (i + 1) % 100 == 0:
                        self.log_signal.emit(f"📊 进度: {i+1}/{total} ({(i+1)/total*100:.1f}%)")

                    # 从QMT获取数据
                    data = xtdata.get_market_data_ex(
                        stock_list=[stock_code],
                        period='1d',
                        count=count
                    )

                    if isinstance(data, dict) and stock_code in data:
                        df = data[stock_code]
                        if not df.empty:
                            # 转换数据格式
                            df_processed = pd.DataFrame({
                                'stock_code': stock_code,
                                'symbol_type': 'stock',
                                'date': pd.to_datetime(df['time'], unit='ms').dt.strftime('%Y-%m-%d'),
                                'period': '1d',
                                'open': df['open'],
                                'high': df['high'],
                                'low': df['low'],
                                'close': df['close'],
                                'volume': df['volume'].astype('int64'),
                                'amount': df['amount'],
                                'adjust_type': 'none',
                                'factor': 1.0,
                                'created_at': datetime.now(),
                                'updated_at': datetime.now()
                            })

                            # 填充复权数据
                            for col in ['open', 'high', 'low', 'close']:
                                df_processed[f'{col}_front'] = df_processed[col]
                                df_processed[f'{col}_back'] = df_processed[col]
                                df_processed[f'{col}_geometric_front'] = df_processed[col]
                                df_processed[f'{col}_geometric_back'] = df_processed[col]

                            backfill_data.append(df_processed)
                            success_count += 1
                        else:
                            failed_count += 1
                            failed_list.append(f"{stock_code} - 数据为空")
                    else:
                        failed_count += 1
                        failed_list.append(f"{stock_code} - 获取失败")

                except Exception as e:
                    self.log_signal.emit(f"  [{i+1}/{total}] {stock_code}: ✗ 错误 - {str(e)[:50]}")
                    failed_count += 1
                    failed_list.append(f"{stock_code} - {str(e)[:30]}")

            self.log_signal.emit(f"📥 历史数据收集完成: {success_count} 只股票成功")

            # 批量写入DuckDB（替换旧数据）
            if backfill_data:
                self.log_signal.emit("💾 正在写入数据库...")
                import time
                time.sleep(2)

                try:
                    # 合并所有数据
                    df_all = pd.concat(backfill_data, ignore_index=True)

                    # 获取涉及的股票列表
                    stocks_to_update = df_all['stock_code'].unique().tolist()

                    with manager.get_write_connection() as con:
                        # 先删除这些股票的旧数据
                        for stock in stocks_to_update:
                            con.execute(f"DELETE FROM stock_daily WHERE stock_code = '{stock}'")

                        # 插入新的完整数据
                        con.register('temp_backfill', df_all)
                        con.execute("INSERT INTO stock_daily SELECT * FROM temp_backfill")
                        con.unregister('temp_backfill')

                    self.log_signal.emit(f"✅ 成功保存 {len(df_all)} 条记录")
                except Exception as e:
                    self.log_signal.emit(f"❌ 写入失败: {str(e)}")

            result = {
                'total': total,
                'success': success_count,
                'failed': failed_count,
                'failed_list': failed_list,
                'task_type': 'backfill_history'
            }

            self.finished_signal.emit(result)
            self.log_signal.emit(f"✅ 历史数据补充完成! 总数: {total}, 成功: {success_count}, 失败: {failed_count}")

            # 输出失败清单
            if failed_list:
                self.log_signal.emit("")
                self.log_signal.emit("=" * 70)
                self.log_signal.emit("  失败清单:")
                for failed_item in failed_list:
                    self.log_signal.emit(f"    ✗ {failed_item}")
                self.log_signal.emit("=" * 70)

        except Exception as e:
            import traceback
            error_msg = f"补充历史数据失败: {str(e)}\n{traceback.format_exc()}"
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
        self.period = period  # '1d', '1m', '5m', '15m', '30m', '60m', 'tick'
        self._is_running = True

    def run(self):
        """运行下载任务"""
        try:
            from xtquant import xtdata
            from datetime import datetime
            import pandas as pd

            # 检查DuckDB管理器是否可用
            try:
                from data_manager.duckdb_connection_pool import get_db_manager
                manager = get_db_manager(r'D:/StockData/stock_data.ddb')
                self.log_signal.emit(f"[OK] 数据管理器初始化成功")
            except ImportError:
                self.error_signal.emit("DuckDB管理器不可用，请确保data_manager.duckdb_connection_pool模块存在")
                return
            except Exception as e:
                self.error_signal.emit(f"DuckDB管理器初始化失败: {e}")
                return

            self.log_signal.emit(f"[INFO] 正在下载 {self.stock_code}...")
            self.log_signal.emit(f"   数据周期: {self.period}")
            self.log_signal.emit(f"   日期范围: {self.start_date} ~ {self.end_date}")

            # 转换日期格式
            start_dt = datetime.strptime(self.start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(self.end_date, '%Y-%m-%d')
            start_str = start_dt.strftime('%Y%m%d')
            end_str = end_dt.strftime('%Y%m%d')

            # 映射周期到QMT API格式
            period_map = {
                '1d': '1d',
                '1m': '1m',
                '5m': '5m',
                '15m': '15m',
                '30m': '30m',
                '60m': '60m',
                'tick': 'tick'
            }
            qmt_period = period_map.get(self.period, '1d')

            # 下载数据
            # 统一使用get_market_data_ex获取数据（支持日线和分钟线）
            # 计算需要获取的数据条数
            start_dt = datetime.strptime(self.start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(self.end_date, '%Y-%m-%d')
            days_diff = (end_dt - start_dt).days + 1

            if self.period == '1d':
                # 日线：直接获取天数，加20天缓冲
                count = max(days_diff + 20, 30)
                self.log_signal.emit(f"📡 正在从QMT获取日线数据（约{days_diff}个交易日）...")
            elif self.period == 'tick':
                # tick数据：需要先下载历史数据
                self.log_signal.emit(f"📥 正在下载tick历史数据...")
                try:
                    # 对于tick数据，需要先使用download_history_data下载
                    # 注意：tick数据下载需要指定到秒
                    start_time_str = start_dt.strftime('%Y%m%d') + "000000"
                    end_time_str = end_dt.strftime('%Y%m%d') + "235959"

                    # 调用下载函数
                    xtdata.download_history_data(
                        stock_code=self.stock_code,
                        period='tick',
                        start_time=start_time_str,
                        end_time=end_time_str
                    )
                    self.log_signal.emit(f"✓ tick数据下载完成")
                except Exception as e:
                    self.log_signal.emit(f"⚠ tick数据下载警告: {str(e)}")
                    self.log_signal.emit(f"  继续尝试读取本地数据...")

                # 下载后尝试读取，设置较大的count
                count = 100000
                self.log_signal.emit(f"📡 正在读取已下载的tick数据...")
            else:
                # 分钟线：估算每天的条数
                if self.period == '1m':
                    count_per_day = 240  # 4小时 * 60分钟
                elif self.period == '5m':
                    count_per_day = 48
                elif self.period == '15m':
                    count_per_day = 16
                elif self.period == '30m':
                    count_per_day = 8
                else:  # 60m
                    count_per_day = 4

                count = days_diff * count_per_day
                # 限制最大条数，避免数据量过大
                count = min(count, 50000)
                self.log_signal.emit(f"📡 正在从QMT获取{self.period}分钟线数据（最多{count}条）...")

            # 使用count参数获取数据（QMT API支持的方式）
            if self.period == 'tick':
                # tick数据需要指定字段列表
                data = xtdata.get_market_data_ex(
                    field_list=['time', 'lastPrice', 'volume', 'amount', 'func_type', 'openInt'],
                    stock_list=[self.stock_code],
                    period=qmt_period,
                    start_time=start_str,
                    end_time=end_str,
                    count=count
                )
            else:
                data = xtdata.get_market_data_ex(
                    stock_list=[self.stock_code],
                    period=qmt_period,
                    count=count
                )

            if isinstance(data, dict) and self.stock_code in data:
                df = data[self.stock_code]
                if df.empty:
                    self.error_signal.emit(f"没有获取到 {self.stock_code} 的数据，请检查代码和日期范围")
                    return
            else:
                self.error_signal.emit(f"没有获取到 {self.stock_code} 的数据，请检查代码和日期范围")
                return

            # 根据日期范围过滤数据
            self.log_signal.emit("🔍 正在过滤日期范围...")
            df['datetime'] = pd.to_datetime(df['time'], unit='ms')

            if self.period == '1d':
                # 日线：只保留日期范围内的数据
                df = df[(df['datetime'] >= start_dt) & (df['datetime'] <= end_dt)]
            else:
                # 分钟线/tick：只保留日期范围内的数据（精确到分钟/秒）
                # 使用当天的23:59:59作为结束时间
                from datetime import datetime as dt, time as dt_time
                end_dt_dt = dt.combine(end_dt, dt_time(23, 59, 59))
                df = df[(df['datetime'] >= start_dt) & (df['datetime'] <= end_dt_dt)]

            if df.empty:
                self.error_signal.emit(f"在指定日期范围内没有数据，请检查日期设置")
                return

            record_count = len(df)
            self.log_signal.emit(f"📊 获取到 {record_count} 条数据")

            # 转换数据格式
            self.log_signal.emit("💾 正在保存到DuckDB...")

            # 转换为标准格式
            if self.period == 'tick':
                # tick数据处理（字段结构不同）
                time_series = pd.to_datetime(df['time'], unit='ms')

                df_processed = pd.DataFrame({
                    'stock_code': self.stock_code,
                    'symbol_type': 'stock' if (self.stock_code.startswith('0') or self.stock_code.startswith('3') or self.stock_code.startswith('6')) else 'etf',
                    'datetime': time_series,
                    'period': 'tick',
                    'lastPrice': df['lastPrice'] if 'lastPrice' in df.columns else 0,
                    'volume': df['volume'].astype('int64') if 'volume' in df.columns else 0,
                    'amount': df['amount'] if 'amount' in df.columns else 0,
                    'func_type': df['func_type'] if 'func_type' in df.columns else 0,
                    'openInt': df['openInt'] if 'openInt' in df.columns else 0,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                })

                table_name = 'stock_tick'

                # 确保stock_tick表存在
                with manager.get_write_connection() as con:
                    con.execute(f"""
                        CREATE TABLE IF NOT EXISTS {table_name} (
                            stock_code VARCHAR(20),
                            symbol_type VARCHAR(10),
                            datetime TIMESTAMP,
                            period VARCHAR(10),
                            lastPrice DOUBLE,
                            volume BIGINT,
                            amount DOUBLE,
                            func_type INTEGER,
                            openInt DOUBLE,
                            created_at TIMESTAMP,
                            updated_at TIMESTAMP
                        )
                    """)

                # 保存tick数据
                with manager.get_write_connection() as con:
                    con.register('temp_data', df_processed)
                    # 删除该股票在日期范围内的旧数据
                    con.execute(f"DELETE FROM {table_name} WHERE stock_code = '{self.stock_code}' AND datetime >= '{start_dt}' AND datetime <= '{end_dt}'")
                    # 插入新数据
                    con.execute(f"INSERT INTO {table_name} SELECT * FROM temp_data")
                    con.unregister('temp_data')

                self.log_signal.emit(f"✅ 已保存 {len(df_processed)} 条tick记录到DuckDB")

                result = {
                    'success': True,
                    'symbol': self.stock_code,
                    'record_count': len(df_processed),
                    'file_size': len(df_processed) * 0.0001
                }

                self.finished_signal.emit(result)
                self.log_signal.emit(f"[OK] {self.stock_code} 下载完成!")
                return

            if 'time' in df.columns:
                # QMT返回的数据格式
                # 日线：使用DATE类型（字符串YYYY-MM-DD）
                # 分钟线：使用TIMESTAMP类型（直接保存datetime对象）
                time_series = pd.to_datetime(df['time'], unit='ms')
                if self.period == '1d':
                    date_series = time_series.dt.strftime('%Y-%m-%d')
                else:
                    date_series = time_series  # 直接使用datetime对象（支持分钟线）

                df_processed = pd.DataFrame({
                    'stock_code': self.stock_code,
                    'symbol_type': 'stock' if (self.stock_code.startswith('0') or self.stock_code.startswith('3') or self.stock_code.startswith('6')) else 'etf',
                    'date': date_series,
                    'period': self.period,
                    'open': df['open'],
                    'high': df['high'],
                    'low': df['low'],
                    'close': df['close'],
                    'volume': df['volume'].astype('int64') if 'volume' in df.columns else 0,
                    'amount': df['amount'] if 'amount' in df.columns else 0,
                    'adjust_type': 'none',
                    'factor': 1.0,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                })

                # 添加复权列（全部使用原始价格）
                for col in ['open', 'high', 'low', 'close']:
                    df_processed[f'{col}_front'] = df_processed[col]
                    df_processed[f'{col}_back'] = df_processed[col]
                    df_processed[f'{col}_geometric_front'] = df_processed[col]
                    df_processed[f'{col}_geometric_back'] = df_processed[col]

                # 保存到DuckDB
                if self.period == '1d':
                    table_name = 'stock_daily'
                else:
                    table_name = f'stock_{self.period}'

                with manager.get_write_connection() as con:
                    con.register('temp_data', df_processed)
                    # 删除该股票该周期的旧数据
                    con.execute(f"DELETE FROM {table_name} WHERE stock_code = '{self.stock_code}'")
                    # 插入新数据
                    con.execute(f"INSERT INTO {table_name} SELECT * FROM temp_data")
                    con.unregister('temp_data')

                self.log_signal.emit(f"✅ 已保存 {len(df_processed)} 条记录到DuckDB")

                result = {
                    'success': True,
                    'symbol': self.stock_code,
                    'record_count': len(df_processed),
                    'file_size': len(df_processed) * 0.0001  # 估算
                }

                self.finished_signal.emit(result)
                self.log_signal.emit(f"[OK] {self.stock_code} 下载完成!")

            else:
                self.error_signal.emit("数据格式不正确")

        except Exception as e:
            import traceback
            error_msg = f"[ERROR] 下载失败: {str(e)}\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)

    def stop(self):
        """停止下载"""
        self._is_running = False
        self.quit()
        self.wait()


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
            import duckdb

            db_path = r'D:/StockData/stock_data.ddb'
            con = duckdb.connect(db_path, read_only=True)

            # 检查1分钟数据
            has_1min = False
            records_1min = 0
            start_1min = ''
            end_1min = ''
            try:
                result = con.execute(f"""
                    SELECT
                        COUNT(*) as cnt,
                        MIN(date) as start_date,
                        MAX(date) as end_date
                    FROM stock_1m
                    WHERE stock_code = '{self.stock_code}'
                """).fetchone()
                if result and result[0] > 0:
                    has_1min = True
                    records_1min = result[0]
                    start_1min = str(result[1]) if result[1] else ''
                    end_1min = str(result[2]) if result[2] else ''
                    self.log_signal.emit(f"✓ 1分钟数据: {records_1min:,} 条 ({start_1min} ~ {end_1min})")
            except Exception:
                pass

            # 检查日线数据
            has_daily = False
            records_daily = 0
            start_daily = ''
            end_daily = ''
            try:
                result = con.execute(f"""
                    SELECT
                        COUNT(*) as cnt,
                        MIN(date) as start_date,
                        MAX(date) as end_date
                    FROM stock_daily
                    WHERE stock_code = '{self.stock_code}'
                """).fetchone()
                if result and result[0] > 0:
                    has_daily = True
                    records_daily = result[0]
                    start_daily = str(result[1]) if result[1] else ''
                    end_daily = str(result[2]) if result[2] else ''
                    self.log_signal.emit(f"✓ 日线数据: {records_daily:,} 条 ({start_daily} ~ {end_daily})")
            except Exception:
                pass

            # 检查tick数据
            has_tick = False
            records_tick = 0
            start_tick = ''
            end_tick = ''
            try:
                result = con.execute(f"""
                    SELECT
                        COUNT(*) as cnt,
                        MIN(datetime) as start_time,
                        MAX(datetime) as end_time
                    FROM stock_tick
                    WHERE stock_code = '{self.stock_code}'
                """).fetchone()
                if result and result[0] > 0:
                    has_tick = True
                    records_tick = result[0]
                    start_tick = str(result[1]) if result[1] else ''
                    end_tick = str(result[2]) if result[2] else ''
                    self.log_signal.emit(f"✓ Tick数据: {records_tick:,} 条 ({start_tick} ~ {end_tick})")
            except Exception:
                pass

            con.close()

            result = {
                'stock': self.stock_code,
                'has_1min': has_1min,
                'has_daily': has_daily,
                'has_tick': has_tick,
                'records_1min': records_1min,
                'records_daily': records_daily,
                'records_tick': records_tick,
                'start_1min': start_1min,
                'end_1min': end_1min,
                'start_daily': start_daily,
                'end_daily': end_daily,
                'start_tick': start_tick,
                'end_tick': end_tick
            }

            self.finished_signal.emit(result)

        except Exception as e:
            self.log_signal.emit(f"✗ 验证失败: {e}")
            result = {
                'stock': self.stock_code,
                'has_1min': False,
                'has_daily': False,
                'records_1min': 0,
                'records_daily': 0,
                'start_1min': '',
                'end_1min': '',
                'start_daily': '',
                'end_daily': ''
            }
            self.finished_signal.emit(result)


class FinancialDataDownloadThread(QThread):
    """QMT财务数据下载线程"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # current, total
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, stock_list=None, table_list=None, start_time=None, end_time=None):
        super().__init__()
        # 默认下载常用股票
        self.stock_list = stock_list or ["000001.SZ", "600519.SH", "511380.SH", "512100.SH"]
        # 默认下载主要财务报表
        self.table_list = table_list or ["Balance", "Income", "CashFlow"]
        # 默认时间范围：最近3年
        from datetime import datetime, timedelta
        if end_time is None:
            end_time = datetime.now()
        else:
            end_time = datetime.strptime(end_time, '%Y%m%d')

        if start_time is None:
            start_time = end_time - timedelta(days=365*3)  # 默认3年
        else:
            start_time = datetime.strptime(start_time, '%Y%m%d')

        self.start_time = start_time.strftime('%Y%m%d')
        self.end_time = end_time.strftime('%Y%m%d')
        self._is_running = True

    def run(self):
        """运行下载任务"""
        try:
            from xtquant import xtdata

            self.log_signal.emit("=" * 70)
            self.log_signal.emit("  【QMT财务数据下载】")
            self.log_signal.emit("=" * 70)

            # 步骤0: 过滤ETF和指数
            self.log_signal.emit("【步骤0】过滤ETF和指数")
            self.log_signal.emit("-" * 70)

            filtered_stock_list = []
            etf_count = 0
            index_count = 0
            stock_count = 0

            for stock_code in self.stock_list:
                try:
                    # 获取股票类型信息
                    type_info = xtdata.get_instrument_type(stock_code)

                    # 判断类型
                    if isinstance(type_info, dict):
                        if type_info.get('stock', False):
                            # 是股票
                            filtered_stock_list.append(stock_code)
                            stock_count += 1
                            self.log_signal.emit(f"[OK] {stock_code}: 股票")
                        elif type_info.get('etf', False) or type_info.get('fund', False):
                            # 是ETF或基金
                            etf_count += 1
                            self.log_signal.emit(f"[SKIP] {stock_code}: ETF/基金（无财务报表）")
                        elif type_info.get('index', False):
                            # 是指数
                            index_count += 1
                            self.log_signal.emit(f"[SKIP] {stock_code}: 指数（无财务报表）")
                        else:
                            # 未知类型，尝试下载
                            self.log_signal.emit(f"[INFO] {stock_code}: 类型未知，将尝试下载")
                            filtered_stock_list.append(stock_code)
                            stock_count += 1
                    else:
                        # 如果返回的不是字典，尝试下载
                        self.log_signal.emit(f"[INFO] {stock_code}: 类型={type_info}，将尝试下载")
                        filtered_stock_list.append(stock_code)
                        stock_count += 1

                except Exception as e:
                    # 如果获取类型失败，也尝试下载
                    self.log_signal.emit(f"[WARN] {stock_code}: 无法获取类型信息，将尝试下载")
                    filtered_stock_list.append(stock_code)
                    stock_count += 1

            self.log_signal.emit("")
            self.log_signal.emit(f"[统计] 原始数量: {len(self.stock_list)}")
            self.log_signal.emit(f"  - 股票: {stock_count} 只（将下载）")
            self.log_signal.emit(f"  - ETF/基金: {etf_count} 只（已跳过）")
            self.log_signal.emit(f"  - 指数: {index_count} 只（已跳过）")
            self.log_signal.emit("")

            if not filtered_stock_list:
                self.log_signal.emit("[INFO] 没有需要下载财务数据的股票")
                result = {
                    'total': len(self.stock_list),
                    'success': 0,
                    'failed': 0,
                    'skipped': len(self.stock_list),
                    'task_type': 'financial_data'
                }
                self.finished_signal.emit(result)
                return

            # 更新股票列表为过滤后的列表
            self.stock_list = filtered_stock_list
            total_stocks = len(self.stock_list)
            total_tables = len(self.table_list)

            self.log_signal.emit(f"[INFO] 准备下载 {total_stocks} 只股票的财务数据")
            self.log_signal.emit(f"[INFO] 数据表: {', '.join(self.table_list)}")
            self.log_signal.emit(f"[INFO] 时间范围: {self.start_time} ~ {self.end_time}")
            self.log_signal.emit("")

            success_count = 0
            failed_count = 0
            failed_list = []  # 记录失败的股票及原因

            # 步骤1: 下载财务数据
            self.log_signal.emit("【步骤1】下载财务数据到QMT本地")
            self.log_signal.emit("-" * 70)

            try:
                self.log_signal.emit(f"[INFO] 正在下载 {self.stock_list} 的财务数据...")
                result = xtdata.download_financial_data(
                    stock_list=self.stock_list,
                    table_list=self.table_list
                )

                if result is None or result == '':
                    self.log_signal.emit("[OK] 财务数据下载完成")
                else:
                    self.log_signal.emit(f"[返回] {result}")

            except Exception as e:
                error_msg = f"[ERROR] 下载失败: {e}"
                self.log_signal.emit(error_msg)
                self.error_signal.emit(error_msg)
                return

            # 步骤2: 读取并验证数据
            self.log_signal.emit("")
            self.log_signal.emit("【步骤2】读取并验证财务数据")
            self.log_signal.emit("-" * 70)

            for i, stock_code in enumerate(self.stock_list):
                if not self._is_running:
                    self.log_signal.emit("[WARN] 用户中断下载")
                    break

                try:
                    self.progress_signal.emit(i + 1, total_stocks)
                    self.log_signal.emit(f"[{i+1}/{total_stocks}] {stock_code}:")

                    # 读取财务数据（添加时间范围参数）
                    result = xtdata.get_financial_data(
                        stock_list=[stock_code],
                        table_list=self.table_list,
                        start_time=self.start_time,
                        end_time=self.end_time,
                        report_type='report_time'
                    )

                    # 处理返回结果（可能是dict或DataFrame）
                    total_records = 0

                    if isinstance(result, dict):
                        # 字典格式：{stock_code: {table_name: data}}
                        if stock_code in result:
                            stock_data = result[stock_code]

                            for table_name in self.table_list:
                                if table_name in stock_data:
                                    table_data = stock_data[table_name]
                                    if isinstance(table_data, pd.DataFrame):
                                        record_count = len(table_data)
                                        total_records += record_count
                                        self.log_signal.emit(f"    [OK] {table_name}: {record_count} 条记录")
                                    elif isinstance(table_data, dict):
                                        record_count = len(table_data)
                                        total_records += record_count
                                        self.log_signal.emit(f"    [OK] {table_name}: {record_count} 条记录")
                                    elif isinstance(table_data, list):
                                        record_count = len(table_data)
                                        total_records += record_count
                                        self.log_signal.emit(f"    [OK] {table_name}: {record_count} 条记录")
                        else:
                            self.log_signal.emit(f"    [WARN] {stock_code} 不在返回结果中")

                    elif isinstance(result, pd.DataFrame):
                        # DataFrame格式：直接是数据
                        record_count = len(result)
                        total_records += record_count
                        self.log_signal.emit(f"    [OK] 财务数据: {record_count} 条记录")
                        self.log_signal.emit(f"    [INFO] 列: {list(result.columns)[:5]}...")

                    if total_records > 0:
                        success_count += 1
                        self.log_signal.emit(f"    [OK] 共 {total_records} 条财务数据")
                    else:
                        failed_count += 1
                        failed_list.append(f"{stock_code} - 数据为空")
                        self.log_signal.emit(f"    [WARN] 没有获取到财务数据")

                except Exception as e:
                    failed_count += 1
                    failed_list.append(f"{stock_code} - {str(e)[:50]}")
                    self.log_signal.emit(f"    [ERROR] {e}")
                    continue

            # 完成
            result = {
                'total': total_stocks,
                'success': success_count,
                'failed': failed_count,
                'failed_list': failed_list,
                'skipped': etf_count + index_count,
                'task_type': 'financial_data'
            }

            self.finished_signal.emit(result)

            self.log_signal.emit("")
            self.log_signal.emit("=" * 70)
            self.log_signal.emit("  下载完成!")
            self.log_signal.emit(f"  有效股票: {total_stocks} 只")
            self.log_signal.emit(f"  成功: {success_count} 只")
            self.log_signal.emit(f"  失败: {failed_count} 只")
            if etf_count + index_count > 0:
                self.log_signal.emit(f"  跳过: {etf_count + index_count} 只（ETF/指数无财务数据）")
            self.log_signal.emit("=" * 70)

        except ImportError:
            error_msg = "[ERROR] 导入xtquant失败，请确保QMT已安装并运行"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)
        except Exception as e:
            import traceback
            error_msg = f"[ERROR] 财务数据下载失败: {str(e)}\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)

    def stop(self):
        """停止下载"""
        self._is_running = False
        self.quit()
        self.wait()


class LocalDataManagerWidget(QWidget):
    """本地数据管理组件"""

    def __init__(self):
        super().__init__()
        self.download_thread = None
        self.duckdb_storage = None
        self.duckdb_con = None  # 添加DuckDB连接属性
        self.init_ui()

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
        self.data_type_combo.addItems(["日线数据", "1分钟数据", "5分钟数据", "15分钟数据", "30分钟数据", "60分钟数据", "Tick数据"])
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

        # 补充历史数据按钮
        self.backfill_data_btn = QPushButton("📜 补充历史数据")
        self.backfill_data_btn.clicked.connect(self.backfill_historical_data)
        self.backfill_data_btn.setStyleSheet("""
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
        btn_layout.addWidget(self.backfill_data_btn)

        action_layout.addLayout(btn_layout, 2, 0, 1, 4)

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

        # ========== 快速操作区域 ==========
        quick_action_group = QGroupBox("⚡ 快速操作")
        quick_action_layout = QGridLayout()
        quick_action_group.setLayout(quick_action_layout)
        left_layout.addWidget(quick_action_group)

        # 快速操作按钮
        other_action_layout = QHBoxLayout()

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
        quick_action_layout.addLayout(other_action_layout, 0, 0, 1, 4)

        # ========== QMT财务数据下载区域 ==========
        financial_group = QGroupBox("💰 QMT财务数据")
        financial_layout = QGridLayout()
        financial_group.setLayout(financial_layout)
        left_layout.addWidget(financial_group)

        # 第一行：股票列表选择
        financial_layout.addWidget(QLabel("股票列表:"), 0, 0)

        self.financial_stock_combo = QComboBox()
        self.financial_stock_combo.addItems([
            "默认股票列表 (4只)",
            "自定义股票列表",
            "全部A股（谨慎使用）",
            "沪深300成分股",
            "中证500成分股",
            "中证1000成分股"
        ])
        financial_layout.addWidget(self.financial_stock_combo, 0, 1, 1, 3)

        # 第二行：数据表选择
        financial_layout.addWidget(QLabel("数据表:"), 1, 0)

        # 使用复选框让用户选择数据表
        table_check_layout = QHBoxLayout()

        self.financial_balance_check = QCheckBox("资产负债表")
        self.financial_balance_check.setChecked(True)
        table_check_layout.addWidget(self.financial_balance_check)

        self.financial_income_check = QCheckBox("利润表")
        self.financial_income_check.setChecked(True)
        table_check_layout.addWidget(self.financial_income_check)

        self.financial_cashflow_check = QCheckBox("现金流量表")
        self.financial_cashflow_check.setChecked(True)
        table_check_layout.addWidget(self.financial_cashflow_check)

        self.financial_cap_check = QCheckBox("股本结构")
        table_check_layout.addWidget(self.financial_cap_check)

        table_check_layout.addStretch()
        financial_layout.addLayout(table_check_layout, 1, 1, 1, 3)

        # 第三行：下载按钮
        self.financial_download_btn = QPushButton("💰 下载QMT财务数据")
        self.financial_download_btn.clicked.connect(self.download_financial_data)
        self.financial_download_btn.setStyleSheet("""
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
        financial_layout.addWidget(self.financial_download_btn, 2, 0, 1, 2)

        # 保存到DuckDB按钮
        self.financial_save_btn = QPushButton("💾 保存到DuckDB")
        self.financial_save_btn.clicked.connect(self.save_financial_to_duckdb)
        self.financial_save_btn.setStyleSheet("""
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
        financial_layout.addWidget(self.financial_save_btn, 2, 2, 1, 2)

        # 添加说明标签
        financial_note = QLabel("说明: 下载财务数据后，点击「保存到DuckDB」可永久存储")
        financial_note.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        financial_layout.addWidget(financial_note, 3, 0, 1, 4)


        # ========== 手动下载单个标的区域 ==========
        manual_group = QGroupBox("🎯 手动下载单个标的（支持分钟线）")
        manual_layout = QGridLayout()
        manual_group.setLayout(manual_layout)
        left_layout.addWidget(manual_group)

        # 第一行：股票代码输入
        manual_layout.addWidget(QLabel("股票/ETF代码:"), 0, 0)
        self.stock_code_input = QLineEdit()
        self.stock_code_input.setPlaceholderText("例如: 512100.SH 或 159915.SZ")
        manual_layout.addWidget(self.stock_code_input, 0, 1, 1, 3)

        # 第二行：常用ETF快捷按钮
        etf_label = QLabel("常用ETF:")
        etf_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        manual_layout.addWidget(etf_label, 1, 0)

        etf_button_layout = QHBoxLayout()
        common_etfs = [
            ("511380.SH", "可转债ETF"),
            ("512100.SH", "中证1000"),
            ("510300.SH", "沪深300"),
            ("510500.SH", "中证500"),
            ("159915.SZ", "深证ETF")
        ]

        for code, name in common_etfs:
            etf_btn = QPushButton(f"{code}")
            etf_btn.setToolTip(f"{name}")
            etf_btn.clicked.connect(lambda checked, c=code: self.stock_code_input.setText(c))
            etf_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E3F2FD;
                    color: #1976D2;
                    border: 1px solid #2196F3;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 9pt;
                }
                QPushButton:hover {
                    background-color: #BBDEFB;
                }
            """)
            etf_button_layout.addWidget(etf_btn)

        etf_button_layout.addStretch()
        manual_layout.addLayout(etf_button_layout, 1, 1, 1, 3)

        # 第三行：数据类型选择
        manual_layout.addWidget(QLabel("数据类型:"), 2, 0)
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems([
            "日线数据",
            "1分钟数据",
            "5分钟数据",
            "15分钟数据",
            "30分钟数据",
            "60分钟数据",
            "Tick数据"
        ])
        manual_layout.addWidget(self.data_type_combo, 2, 1)

        # 日期范围
        manual_layout.addWidget(QLabel("日期范围:"), 2, 2)
        date_range_layout = QHBoxLayout()

        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-3))
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        date_range_layout.addWidget(self.start_date_edit)

        date_range_layout.addWidget(QLabel("~"))

        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        date_range_layout.addWidget(self.end_date_edit)

        manual_layout.addLayout(date_range_layout, 2, 3)

        # 第四行：下载按钮
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
        manual_layout.addWidget(self.manual_download_btn, 3, 0, 1, 4)

        # 说明标签
        manual_note = QLabel("💡 提示：分钟线数据建议只下载最近1-3个月，避免数据量过大")
        manual_note.setStyleSheet("color: #FF9800; font-size: 9pt; padding: 5px;")
        manual_layout.addWidget(manual_note, 4, 0, 1, 4)

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
        self.log("本地数据管理组件已加载")
        self.log("提示：首次使用请先下载数据")

        # 加载DuckDB统计数据
        QTimer.singleShot(100, self.load_duckdb_statistics)

    def log(self, message):
        """输出日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.append(f"[{timestamp}] {message}")
        # 滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)

    def load_duckdb_statistics(self):
        """从DuckDB加载统计数据"""
        try:
            import duckdb

            db_path = r'D:/StockData/stock_data.ddb'
            con = duckdb.connect(db_path, read_only=True)

            # 统计stock_daily表
            stats_daily = con.execute("""
                SELECT
                    COUNT(DISTINCT stock_code) as stock_count,
                    SUM(CASE WHEN symbol_type = 'stock' THEN 1 ELSE 0 END) as stock_only,
                    SUM(CASE WHEN symbol_type = 'etf' THEN 1 ELSE 0 END) as etf_count,
                    COUNT(*) as total_records,
                    MAX(date) as latest_date
                FROM stock_daily
            """).fetchone()

            # 统计所有分钟数据表
            minute_tables = ['stock_1m', 'stock_5m', 'stock_15m', 'stock_30m', 'stock_60m']
            minute_records = 0
            minute_stocks = set()

            for table in minute_tables:
                try:
                    result = con.execute(f"""
                        SELECT
                            COUNT(DISTINCT stock_code) as cnt,
                            COUNT(*) as records
                        FROM {table}
                    """).fetchone()
                    if result:
                        minute_stocks.update(con.execute(f"SELECT DISTINCT stock_code FROM {table}").fetchall())
                        minute_records += result[1]
                except:
                    pass

            con.close()

            # 更新UI
            total_symbols = stats_daily[0] if stats_daily else 0
            stock_count = stats_daily[1] if stats_daily else 0
            etf_count = stats_daily[2] if stats_daily else 0
            daily_records = stats_daily[3] if stats_daily else 0
            latest_date = str(stats_daily[4]) if stats_daily and stats_daily[4] else 'N/A'

            total_records = daily_records + minute_records
            total_bonds = 0  # 暂时没有可转债数据

            # 估算存储大小（每条记录约0.1KB）
            size_mb = total_records * 0.0001

            self.total_symbols_label.setText(f"标的总数: {total_symbols:,}")
            self.total_stocks_label.setText(f"股票数量: {stock_count:,}")
            self.total_bonds_label.setText(f"可转债数量: {total_bonds:,}")
            self.total_records_label.setText(f"总记录数: {total_records:,}")
            self.total_size_label.setText(f"存储大小: {size_mb:.2f} MB")
            self.latest_date_label.setText(f"最新日期: {latest_date}")

        except Exception as e:
            self.log(f"[ERROR] 加载统计数据失败: {e}")

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
            "60分钟数据": "60m",
            "Tick数据": "tick"
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

        else:
            self.log(f"❌ {stock_code} 下载失败")

    def on_single_download_error(self, error_msg):
        """单个标的下载出错"""
        self.manual_download_btn.setEnabled(True)
        QMessageBox.critical(self, "下载失败", error_msg)

    def download_financial_data(self):
        """下载QMT财务数据"""
        if self.download_thread and self.download_thread.isRunning():
            QMessageBox.warning(self, "提示", "已有下载任务正在运行")
            return

        # 获取股票列表
        stock_selection = self.financial_stock_combo.currentText()

        if "默认股票列表" in stock_selection:
            stock_list = ["000001.SZ", "600519.SH", "511380.SH", "512100.SH"]
        elif "自定义股票列表" in stock_selection:
            # 弹出输入对话框让用户输入股票列表
            text, ok = QInputDialog.getText(
                self, "输入股票列表",
                "请输入股票代码，用逗号分隔:\n例如: 000001.SZ,600519.SH,511380.SH"
            )
            if not ok or not text.strip():
                return
            stock_list = [s.strip() for s in text.split(',')]
        elif "全部A股" in stock_selection:
            # 警告用户
            reply = QMessageBox.question(
                self, "确认下载",
                "即将下载全部A股的财务数据，这可能需要较长时间。\n\n确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
            # 获取全部A股列表
            try:
                from xtquant import xtdata
                all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
                stock_list = all_stocks[:100]  # 限制前100只，避免太多
                QMessageBox.information(self, "提示", f"为避免下载时间过长，限制为前100只股票")
            except:
                QMessageBox.warning(self, "错误", "获取股票列表失败")
                return
        elif "沪深300" in stock_selection:
            # 获取沪深300成分股
            try:
                from xtquant import xtdata
                stock_list = xtdata.get_stock_list_in_sector('沪深300')
            except:
                stock_list = ["000001.SZ", "600519.SH", "511380.SH"]
        elif "中证500" in stock_selection:
            try:
                from xtquant import xtdata
                stock_list = xtdata.get_stock_list_in_sector('中证500')
            except:
                stock_list = ["000001.SZ", "600519.SH", "511380.SH"]
        elif "中证1000" in stock_selection:
            try:
                from xtquant import xtdata
                stock_list = xtdata.get_stock_list_in_sector('中证1000')
            except:
                stock_list = ["000001.SZ", "600519.SH", "511380.SH"]
        else:
            stock_list = ["000001.SZ", "600519.SH", "511380.SH"]

        # 获取数据表列表
        table_list = []
        if self.financial_balance_check.isChecked():
            table_list.append("Balance")
        if self.financial_income_check.isChecked():
            table_list.append("Income")
        if self.financial_cashflow_check.isChecked():
            table_list.append("CashFlow")
        if self.financial_cap_check.isChecked():
            table_list.append("Capitalization")

        if not table_list:
            QMessageBox.warning(self, "提示", "请至少选择一个数据表")
            return

        self.log(f"💰 开始下载QMT财务数据")
        self.log(f"   股票数量: {len(stock_list)}")
        self.log(f"   数据表: {', '.join(table_list)}")

        # 创建下载线程
        self.download_thread = FinancialDataDownloadThread(
            stock_list=stock_list,
            table_list=table_list
        )
        self.download_thread.log_signal.connect(self.log)
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.on_financial_download_finished)
        self.download_thread.error_signal.connect(self.on_financial_download_error)
        self.download_thread.start()

        self._set_download_state(True)

    def on_financial_download_finished(self, result):
        """财务数据下载完成"""
        self._set_download_state(False)
        self.progress_bar.setVisible(False)

        total = result.get('total', 0)
        success = result.get('success', 0)
        failed = result.get('failed', 0)
        skipped = result.get('skipped', 0)

        msg = f"QMT财务数据下载完成！\n\n"
        msg += f"有效股票: {total} 只\n"
        msg += f"成功: {success} 只\n"
        msg += f"失败: {failed} 只"
        if skipped > 0:
            msg += f"\n跳过: {skipped} 只（ETF/指数无财务数据）"

        if failed > 0:
            QMessageBox.warning(self, "下载完成", msg)
        else:
            QMessageBox.information(self, "下载完成", msg)

    def save_financial_to_duckdb(self):
        """保存财务数据到DuckDB"""
        # 检查模块是否可用
        if not BATCH_SAVE_AVAILABLE:
            QMessageBox.warning(self, "功能不可用",
                "批量保存财务数据模块不可用。\n\n请确保 advanced_data_viewer_widget.py 文件存在且可导入。")
            return

        # 获取股票列表
        stock_selection = self.financial_stock_combo.currentText()

        if "默认股票列表" in stock_selection:
            stock_list = ["000001.SZ", "600519.SH", "511380.SH", "512100.SH"]
        elif "自定义股票列表" in stock_selection:
            text, ok = QInputDialog.getText(
                self, "输入股票列表",
                "请输入股票代码，用逗号分隔:\n例如: 000001.SZ,600519.SH"
            )
            if not ok or not text.strip():
                return
            stock_list = [s.strip() for s in text.split(',')]
        elif "沪深300" in stock_selection:
            try:
                from xtquant import xtdata
                stock_list = xtdata.get_stock_list_in_sector('沪深300')
            except:
                stock_list = ["000001.SZ", "600519.SH"]
        elif "中证500" in stock_selection:
            try:
                from xtquant import xtdata
                stock_list = xtdata.get_stock_list_in_sector('中证500')
            except:
                stock_list = ["000001.SZ", "600519.SH"]
        elif "中证1000" in stock_selection:
            try:
                from xtquant import xtdata
                stock_list = xtdata.get_stock_list_in_sector('中证1000')
            except:
                stock_list = ["000001.SZ", "600519.SH"]
        elif "全部A股" in stock_selection:
            reply = QMessageBox.question(
                self, "确认保存",
                "即将保存全部A股的财务数据到DuckDB，这可能需要较长时间。\n\n确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
            try:
                from xtquant import xtdata
                stock_list = xtdata.get_stock_list_in_sector('沪深A股')
            except:
                QMessageBox.warning(self, "错误", "获取股票列表失败")
                return
        else:
            stock_list = ["000001.SZ", "600519.SH"]

        self.log(f"💾 开始保存财务数据到DuckDB")
        self.log(f"   股票数量: {len(stock_list)}")

        # 创建保存线程
        self.save_thread = BatchFinancialSaveThread(stock_list)
        self.save_thread.log_signal.connect(self.log)
        self.save_thread.progress_signal.connect(self.update_progress)
        self.save_thread.finished_signal.connect(self.on_financial_save_finished)
        self.save_thread.error_signal.connect(self.on_financial_save_error)
        self.save_thread.start()

        self._set_download_state(True)

    def on_financial_save_finished(self, result):
        """财务数据保存完成"""
        self._set_download_state(False)
        self.progress_bar.setVisible(False)

        total = result.get('total', 0)
        success = result.get('success', 0)
        failed = result.get('failed', 0)

        msg = f"财务数据保存完成！\n\n"
        msg += f"总数: {total} 只\n"
        msg += f"成功: {success} 只\n"
        msg += f"失败: {failed} 只"

        if failed > 0:
            QMessageBox.warning(self, "保存完成", msg)
        else:
            QMessageBox.information(self, "保存完成", msg)

        # 重新加载数据信息
        self.load_duckdb_statistics()

    def on_financial_save_error(self, error_msg):
        """财务数据保存出错"""
        self._set_download_state(False)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "保存失败", error_msg)

    def download_single_financial(self):
        """下载单只股票的财务数据"""
        stock_code = self.financial_stock_input.text().strip()

        if not stock_code:
            QMessageBox.warning(self, "提示", "请输入股票代码")
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

        # 获取数据表列表
        table_list = []
        if self.financial_balance_check.isChecked():
            table_list.append("Balance")
        if self.financial_income_check.isChecked():
            table_list.append("Income")
        if self.financial_cashflow_check.isChecked():
            table_list.append("CashFlow")
        if self.financial_cap_check.isChecked():
            table_list.append("Capitalization")

        if not table_list:
            QMessageBox.warning(self, "提示", "请至少选择一个数据表")
            return

        self.log(f"💰 开始下载 {stock_code} 的财务数据")
        self.log(f"   数据表: {', '.join(table_list)}")

        # 创建下载线程
        self.download_thread = FinancialDataDownloadThread(
            stock_list=[stock_code],
            table_list=table_list
        )
        self.download_thread.log_signal.connect(self.log)
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.on_single_financial_finished)
        self.download_thread.error_signal.connect(self.on_financial_download_error)
        self.download_thread.start()

        self._set_download_state(True)

    def on_single_financial_finished(self, result):
        """单只股票财务数据下载完成"""
        self._set_download_state(False)
        self.progress_bar.setVisible(False)

        total = result.get('total', 0)
        success = result.get('success', 0)
        failed = result.get('failed', 0)
        skipped = result.get('skipped', 0)

        msg = f"财务数据下载完成！\n\n"
        msg += f"有效股票: {total} 只\n"
        msg += f"成功: {success} 只"
        if failed > 0:
            msg += f"\n失败: {failed} 只"
        if skipped > 0:
            msg += f"\n跳过: {skipped} 只（ETF/指数）"

        if failed > 0:
            QMessageBox.warning(self, "下载完成", msg)
        else:
            QMessageBox.information(self, "下载完成", msg)

        # 刷新财务数据统计
        self.refresh_financial_stats()

    def refresh_financial_stats(self):
        """刷新财务数据统计"""
        try:
            from xtquant import xtdata

            self.log("[INFO] 正在统计已下载的财务数据...")

            # 测试几只常用股票
            test_stocks = ["000001.SZ", "600519.SH", "511380.SH", "512100.SH"]
            table_list = ["Balance", "Income", "CashFlow"]

            total_count = 0
            stock_count = 0

            for stock_code in test_stocks:
                try:
                    result = xtdata.get_financial_data(
                        stock_list=[stock_code],
                        table_list=table_list,
                        start_time="20200101",
                        end_time="20260130",
                        report_type='report_time'
                    )

                    if isinstance(result, dict) and stock_code in result:
                        stock_data = result[stock_code]
                        count = 0
                        for table_name in table_list:
                            if table_name in stock_data:
                                table_data = stock_data[table_name]
                                if isinstance(table_data, dict):
                                    count += len(table_data)
                                elif hasattr(table_data, '__len__'):
                                    count += len(table_data)

                        if count > 0:
                            stock_count += 1
                            total_count += count

                except Exception as e:
                    continue

            self.log(f"[OK] 财务数据统计更新完成: {stock_count}只股票, {total_count}条记录")

        except Exception as e:
            self.log(f"[ERROR] 统计财务数据失败: {e}")

    def view_financial_data(self):
        """查看选中股票的财务数据"""
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

        self.log(f"[INFO] 查看 {stock_code} 的财务数据")

        # 提示用户使用数据查看器
        QMessageBox.information(
            self,
            "查看财务数据",
            f"「查看财务数据」功能已迁移到「📈 数据查看器」标签页\n\n"
            f"请在「📈 数据查看器」标签页中：\n"
            f"1. 选择股票: {stock_code}\n"
            f"2. 点击「💰 加载财务数据」按钮\n\n"
            f"新功能支持查看更详细的财务指标数据。"
        )

    def on_financial_download_error(self, error_msg):
        """财务数据下载出错"""
        self._set_download_state(False)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "下载失败", error_msg)

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

    def backfill_historical_data(self):
        """补充历史数据（获取2018年以来的完整数据）"""
        reply = QMessageBox.question(
            self, "确认操作",
            "此操作将为所有股票补充2018年以来的完整历史数据。\n\n"
            "可能需要较长时间，确定要继续吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.No:
            return

        if self.download_thread and self.download_thread.isRunning():
            QMessageBox.warning(self, "提示", "已有下载任务正在运行")
            return

        self.log("📜 开始补充历史数据（2018年起）...")

        self.download_thread = DataDownloadThread(
            task_type='backfill_history',
            symbols=None,
            start_date='20180101',
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
        self.load_duckdb_statistics()

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
        self.backfill_data_btn.setEnabled(not is_downloading)
        self.manual_download_btn.setEnabled(not is_downloading)
        self.verify_data_btn.setEnabled(not is_downloading)
        self.financial_download_btn.setEnabled(not is_downloading)
        self.stop_btn.setVisible(is_downloading)
        self.progress_bar.setVisible(is_downloading)

        if is_downloading:
            self.progress_bar.setValue(0)

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
        has_tick = result.get('has_tick', False)
        records_1min = result.get('records_1min', 0)
        records_daily = result.get('records_daily', 0)
        records_tick = result.get('records_tick', 0)
        start_1min = result.get('start_1min', '')
        end_1min = result.get('end_1min', '')
        start_daily = result.get('start_daily', '')
        end_daily = result.get('end_daily', '')
        start_tick = result.get('start_tick', '')
        end_tick = result.get('end_tick', '')

        msg = f"{stock} 数据验证结果:\n\n"
        msg += f"1分钟数据: {'✓ 存在' if has_1min else '✗ 不存在'}"
        if has_1min:
            msg += f"\n   记录数: {records_1min:,} 条"
            msg += f"\n   时间范围: {start_1min} ~ {end_1min}"
        else:
            msg += "\n"

        msg += f"\n日线数据: {'✓ 存在' if has_daily else '✗ 不存在'}"
        if has_daily:
            msg += f"\n   记录数: {records_daily:,} 条"
            msg += f"\n   时间范围: {start_daily} ~ {end_daily}"

        msg += f"\nTick数据: {'✓ 存在' if has_tick else '✗ 不存在'}"
        if has_tick:
            msg += f"\n   记录数: {records_tick:,} 条"
            msg += f"\n   时间范围: {start_tick} ~ {end_tick}"

        if has_1min or has_daily or has_tick:
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
            # 使用只读模式连接，避免配置冲突
            import duckdb

            # DuckDB数据库路径
            db_path = Path('D:/StockData/stock_data.ddb')

            if not db_path.exists():
                self.stats_label.setText(f"❌ 数据库不存在: {db_path}")
                self.data_table.setRowCount(1)
                self.data_table.setColumnCount(1)
                self.data_table.setHorizontalHeaderLabels(["错误"])
                self.data_table.setItem(0, 0, QTableWidgetItem(f"数据库不存在:\n{db_path}"))
                return

            # 创建只读连接
            con = duckdb.connect(str(db_path), read_only=True)

            # 映射复权类型
            adjust_map = {
                "none": "none",
                "qfq": "front",
                "hfq": "back"
            }
            duckdb_adjust = adjust_map.get(self.adjust, "none")

            # 加载数据（直接查询DuckDB）
            query = f"""
                SELECT
                    date,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    amount
                FROM stock_daily
                WHERE stock_code = '{self.stock_code}'
                  AND period = '1d'
                  AND adjust_type = '{duckdb_adjust}'
                ORDER BY date
            """

            df = con.execute(query).df()
            con.close()

            if df.empty:
                self.stats_label.setText(f"❌ 未找到 {self.stock_code} 的数据")
                self.data_table.setRowCount(1)
                self.data_table.setColumnCount(1)
                self.data_table.setHorizontalHeaderLabels(["提示"])
                self.data_table.setItem(0, 0, QTableWidgetItem(f"未找到 {self.stock_code} 的数据\n请先下载该股票的数据"))
                return

            # 设置日期为索引
            df.set_index('date', inplace=True)

            # 显示数据
            self._display_data(df)

        except Exception as e:
            self.stats_label.setText(f"❌ 加载失败: {str(e)}")
            import traceback
            traceback.print_exc()
            self.data_table.setRowCount(1)
            self.data_table.setColumnCount(1)
            self.data_table.setHorizontalHeaderLabels(["错误"])
            self.data_table.setItem(0, 0, QTableWidgetItem(f"加载数据失败:\n{str(e)}"))

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
            # 使用只读模式连接
            import duckdb

            # DuckDB数据库路径
            db_path = Path('D:/StockData/stock_data.ddb')

            # 映射复权类型
            adjust_map = {
                "none": "none",
                "qfq": "front",
                "hfq": "back"
            }
            duckdb_adjust = adjust_map.get(self.adjust, "none")

            # 创建只读连接并加载数据
            con = duckdb.connect(str(db_path), read_only=True)
            query = f"""
                SELECT
                    date,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    amount
                FROM stock_daily
                WHERE stock_code = '{self.stock_code}'
                  AND period = '1d'
                  AND adjust_type = '{duckdb_adjust}'
                ORDER BY date
            """
            df = con.execute(query).df()
            con.close()

            # 设置日期为索引
            df.set_index('date', inplace=True)

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


class FinancialDataViewerDialog(QDialog):
    """财务数据查看对话框"""

    def __init__(self, stock_code: str, parent=None):
        super().__init__(parent)
        self.stock_code = stock_code
        self.setWindowTitle(f"查看财务数据 - {stock_code}")
        self.setMinimumSize(1000, 700)
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

        # 数据表选择
        info_layout.addWidget(QLabel("数据表:"))
        self.table_combo = QComboBox()
        self.table_combo.addItems(["Balance (资产负债表)", "Income (利润表)", "CashFlow (现金流量表)", "Capitalization (股本结构)"])
        self.table_combo.currentIndexChanged.connect(self.load_data)
        info_layout.addWidget(self.table_combo)

        info_layout.addStretch()

        # 导出CSV按钮
        export_btn = QPushButton("📊 导出CSV")
        export_btn.clicked.connect(self.export_financial_csv)
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

        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.load_data)
        refresh_btn.setStyleSheet("""
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
        info_layout.addWidget(refresh_btn)

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
            from xtquant import xtdata
            import pandas as pd

            # 获取选择的数据表
            table_text = self.table_combo.currentText()
            table_map = {
                "Balance (资产负债表)": "Balance",
                "Income (利润表)": "Income",
                "CashFlow (现金流量表)": "CashFlow",
                "Capitalization (股本结构)": "Capitalization"
            }
            table_name = table_map.get(table_text, "Balance")

            # 下载财务数据
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(0)
            self.stats_label.setText("正在加载数据...")

            # 先下载
            xtdata.download_financial_data(
                stock_list=[self.stock_code],
                table_list=[table_name]
            )

            # 再读取
            result = xtdata.get_financial_data(
                stock_list=[self.stock_code],
                table_list=[table_name],
                start_time="20200101",
                end_time="20260130",
                report_type='report_time'
            )

            if isinstance(result, dict) and self.stock_code in result:
                stock_data = result[self.stock_code]

                if table_name in stock_data:
                    table_data = stock_data[table_name]

                    if isinstance(table_data, pd.DataFrame):
                        # DataFrame格式
                        self._display_dataframe(table_data)
                    elif isinstance(table_data, dict):
                        # 字典格式，转换为表格显示
                        self._display_dict(table_data)
                    else:
                        self.stats_label.setText(f"数据类型: {type(table_data)}")
                        QMessageBox.information(self, "提示", f"数据格式: {type(table_data)}")
                else:
                    self.stats_label.setText(f"未找到 {table_name} 表数据")
                    QMessageBox.information(self, "提示", f"未找到 {table_name} 表数据\n\n可能原因：\n1. 该股票没有此表数据\n2. 需要先下载财务数据")
            else:
                self.stats_label.setText("未找到财务数据")
                QMessageBox.information(self, "提示", "未找到财务数据\n\n请先下载财务数据")

        except Exception as e:
            self.stats_label.setText(f"加载失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"加载财务数据失败: {str(e)}")

    def _display_dataframe(self, df):
        """显示DataFrame"""
        # 重置索引
        df = df.reset_index()

        # 设置列
        columns = df.columns.tolist()
        self.data_table.setColumnCount(len(columns))
        self.data_table.setHorizontalHeaderLabels(columns)

        # 设置行
        self.data_table.setRowCount(len(df))

        # 填充数据（显示前100条）
        display_df = df.head(100)

        for row_idx in range(len(display_df)):
            for col_idx, col in enumerate(columns):
                value = display_df.iloc[row_idx, col_idx]
                item = QTableWidgetItem(str(value))
                self.data_table.setItem(row_idx, col_idx, item)

        # 调整列宽
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # 更新统计信息
        total = len(df)
        if total > 100:
            self.stats_label.setText(f"总记录数: {total} 条 (显示前100条)")
        else:
            self.stats_label.setText(f"总记录数: {total} 条")

    def _display_dict(self, data):
        """显示字典数据"""
        # 将字典转换为表格
        self.data_table.setColumnCount(2)
        self.data_table.setHorizontalHeaderLabels(["字段名", "值"])

        # 获取所有键
        keys = list(data.keys())
        self.data_table.setRowCount(len(keys))

        for row_idx, key in enumerate(keys):
            value = data[key]

            # 字段名
            key_item = QTableWidgetItem(str(key))
            self.data_table.setItem(row_idx, 0, key_item)

            # 值
            value_str = str(value) if not isinstance(value, (list, dict)) else f"{type(value).__name__}({len(value)})"
            value_item = QTableWidgetItem(value_str)
            self.data_table.setItem(row_idx, 1, value_item)

        # 调整列宽
        self.data_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.data_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        # 更新统计信息
        self.stats_label.setText(f"字段数量: {len(keys)} 个")

    def export_financial_csv(self):
        """导出财务数据为CSV"""
        try:
            from xtquant import xtdata
            import pandas as pd

            # 获取选择的数据表
            table_text = self.table_combo.currentText()
            table_map = {
                "Balance (资产负债表)": "Balance",
                "Income (利润表)": "Income",
                "CashFlow (现金流量表)": "CashFlow",
                "Capitalization (股本结构)": "Capitalization"
            }
            table_name = table_map.get(table_text, "Balance")

            # 下载数据
            xtdata.download_financial_data(
                stock_list=[self.stock_code],
                table_list=[table_name]
            )

            # 读取数据
            result = xtdata.get_financial_data(
                stock_list=[self.stock_code],
                table_list=[table_name],
                start_time="20200101",
                end_time="20260130",
                report_type='report_time'
            )

            if isinstance(result, dict) and self.stock_code in result:
                stock_data = result[self.stock_code]

                if table_name in stock_data:
                    table_data = stock_data[table_name]

                    # 转换为DataFrame
                    if isinstance(table_data, pd.DataFrame):
                        df = table_data
                    elif isinstance(table_data, dict):
                        # 字典转换为DataFrame
                        df = pd.DataFrame.from_dict(table_data, orient='index').T
                    else:
                        QMessageBox.warning(self, "提示", f"无法导出数据类型: {type(table_data)}")
                        return

                    # 选择保存路径
                    default_name = f"{self.stock_code}_{table_name}_财务数据.csv"
                    file_path, _ = QFileDialog.getSaveFileName(
                        self,
                        "导出财务数据CSV",
                        default_name,
                        "CSV文件 (*.csv)"
                    )

                    if file_path:
                        # 导出为CSV
                        df.to_csv(file_path, encoding='utf-8-sig', index=True)
                        QMessageBox.information(self, "成功", f"财务数据已导出到:\n{file_path}\n\n共 {len(df)} 条记录")
                else:
                    QMessageBox.warning(self, "提示", f"未找到 {table_name} 表数据")
            else:
                QMessageBox.warning(self, "提示", "未找到财务数据")

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
