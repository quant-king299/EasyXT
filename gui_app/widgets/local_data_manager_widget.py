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

            # 使用DuckDB存储
            manager = LocalDataManager(
                config={
                    'data_paths': {
                        'root_dir': 'D:/StockData',
                        'raw_data': 'raw',
                        'metadata': 'metadata.db'
                    },
                    'storage': {
                        'format': 'duckdb',  # 使用DuckDB存储
                        'compression': 'snappy'
                    }
                }
            )
            self.log_signal.emit("✅ 数据管理器初始化成功 (DuckDB单文件存储)")

            # 如果没有指定股票列表，获取全部A股（排除ETF）
            if not self.symbols:
                self.log_signal.emit("📊 正在获取A股列表（排除ETF）...")
                all_stocks = manager.get_all_stocks_list(
                    include_st=True,
                    include_sz=True,
                    include_bj=True,
                    exclude_st=True,
                    exclude_delisted=True
                )

                # 过滤掉ETF和基金
                etf_patterns = [
                    '51',      # 上海ETF：510xxx, 511xxx, 512xxx, 513xxx, 515xxx, 516xxx
                    '159',     # 深圳ETF：159xxx
                    '150',     # 深圳基金：150xxx
                    '588',     # 上海ETF：588xxx
                    '50',      # 上海50开头基金
                    '56',      # 上海56开头基金
                    '58',      # 上海58开头基金
                ]

                self.symbols = []
                for stock in all_stocks:
                    is_etf = False
                    for pattern in etf_patterns:
                        if stock.startswith(pattern):
                            is_etf = True
                            break

                    if not is_etf:
                        self.symbols.append(stock)

                self.log_signal.emit(f"✅ 获取到 {len(self.symbols)} 只A股（已排除ETF和基金）")

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

                    # 尝试获取数据（不保存）
                    df = manager._fetch_from_source(symbol, self.start_date, self.end_date)

                    if df.empty:
                        # 数据确实为空
                        failed_count += 1
                        failed_list.append(f"{symbol} - 数据为空")
                    else:
                        # 数据获取成功，尝试保存
                        try:
                            success, file_size = manager.storage.save_data(df, symbol, data_type='daily')

                            if success:
                                # 更新元数据
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
                                # 保存失败
                                failed_count += 1
                                failed_list.append(f"{symbol} - 保存失败 (数据量:{len(df)})")
                        except Exception as save_error:
                            # 保存异常
                            failed_count += 1
                            failed_list.append(f"{symbol} - 保存异常: {str(save_error)[:30]}")

                    # 每下载100只股票输出一次日志
                    if (i + 1) % 100 == 0:
                        self.log_signal.emit(f"📊 进度: {i + 1}/{total} | 成功: {success_count} | 失败: {failed_count}")

                except Exception as e:
                    failed_count += 1
                    failed_list.append(f"{symbol} - {str(e)[:50]}")
                    continue

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

                    # 下载数据 - 使用正确的参数调用DuckDB管理器
                    period = '1d'  # 日线数据
                    adjust_type = 'none'  # 不复权
                    data_source = 'qmt'  # 使用QMT数据源

                    df = manager._fetch_from_source(symbol, self.start_date, self.end_date,
                                                   period, adjust_type, data_source)

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
        """更新缺失数据（智能补全）- 自动检测并补充所有缺失的历史数据"""
        try:
            from data_manager.duckdb_connection_pool import get_db_manager
            from xtquant import xtdata
            import pandas as pd

            self.log_signal.emit("✅ 数据管理器初始化成功")
            self.log_signal.emit("📋 正在检测缺失数据...")

            # 获取DuckDB管理器
            manager = get_db_manager(r'D:/StockData/stock_data.ddb')

            # 查找需要更新的股票（任何缺失数据的股票）
            # 策略：自动检测每只股票的最新日期，补充从该日期之后的所有缺失数据
            # 不管缺失1天还是100天，都会一并补全
            query = """
                SELECT
                    stock_code,
                    MAX(date) as latest_date,
                    DATEDIFF('day', MAX(date), CURRENT_DATE) as days_behind
                FROM stock_daily
                WHERE stock_code IS NOT NULL  -- 过滤掉NULL记录
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
            skipped_list = []
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
                    matching_stocks = df_stocks[df_stocks['stock_code'] == stock_code]
                    if matching_stocks.empty:
                        self.log_signal.emit(f"  [{i+1}/{total}] {stock_code}: ⚠️ 跳过 - 未找到股票信息")
                        skipped_count += 1
                        continue

                    stock_data = matching_stocks.iloc[0]
                    latest_date = stock_data['latest_date']
                    days_behind = stock_data['days_behind']

                    # 计算获取数据的日期范围
                    # 从DuckDB最新日期的下一天开始，到今天
                    from datetime import datetime, timedelta
                    latest_dt = pd.to_datetime(latest_date)
                    start_dt = latest_dt + timedelta(days=1)  # 从最新日期的下一天开始
                    end_dt = datetime.now()  # 到今天

                    # 格式化为QMT需要的格式：YYYYMMDD
                    start_time = start_dt.strftime('%Y%m%d')
                    end_time = end_dt.strftime('%Y%m%d')

                    # 从QMT获取数据（使用日期范围参数，获取所有缺失数据）
                    # 步骤1: 先下载数据到QMT本地
                    xtdata.download_history_data(
                        stock_code,
                        period='1d',
                        start_time=start_time,
                        end_time=end_time,
                        incrementally=True
                    )

                    # 步骤2: 再从本地读取数据
                    data = xtdata.get_market_data_ex(
                        stock_list=[stock_code],
                        period='1d',
                        start_time=start_time,
                        end_time=end_time
                    )

                    if isinstance(data, dict) and stock_code in data:
                        df = data[stock_code]
                        if not df.empty:
                            # 转换数据格式
                            # 注意：QMT返回的时间戳是UTC时间，需要转换为北京时间
                            time_series = pd.to_datetime(df['time'], unit='ms', utc=True).dt.tz_convert('Asia/Shanghai')
                            df_processed = pd.DataFrame({
                                'stock_code': stock_code,
                                'symbol_type': 'stock',
                                'date': time_series.dt.strftime('%Y-%m-%d'),
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
                                # 输出补充的信息
                                date_range_start = df_processed['date'].min()
                                date_range_end = df_processed['date'].max()
                                days_added = len(df_processed)
                                self.log_signal.emit(f"  [{i+1}/{total}] {stock_code}: ✅ 补充 {days_added} 条数据 ({date_range_start} ~ {date_range_end})")
                                success_count += 1
                            else:
                                self.log_signal.emit(f"  [{i+1}/{total}] {stock_code}: ⚠️ 无新数据（已是最新）")
                                skipped_count += 1
                                skipped_list.append(stock_code)
                        else:
                            skipped_count += 1
                            skipped_list.append(stock_code)
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
                        # 注册临时表
                        con.register('temp_updates', df_all)

                        # 策略：先删除重复数据，再插入新数据
                        # 修复类型转换问题：明确将temp_updates的date列转换为DATE类型
                        self.log_signal.emit("  🗑️ 删除重复数据...")
                        con.execute("""
                            DELETE FROM stock_daily
                            WHERE (stock_code, CAST(date AS DATE), period, adjust_type) IN (
                                SELECT stock_code, CAST(date AS DATE), period, adjust_type
                                FROM temp_updates
                            )
                        """)

                        # 插入新数据（只插入表结构中存在的列）
                        self.log_signal.emit("  📝 插入新数据...")
                        con.execute("""
                            INSERT INTO stock_daily (
                                stock_code, symbol_type, date, period,
                                open, high, low, close, volume, amount,
                                adjust_type, factor, created_at, updated_at
                            )
                            SELECT
                                stock_code, symbol_type, CAST(date AS DATE), period,
                                open, high, low, close, volume, amount,
                                adjust_type, factor, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                            FROM temp_updates
                        """)

                        # 注销临时表
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
                                con.execute("""
                                    INSERT INTO stock_daily (
                                        stock_code, symbol_type, date, period,
                                        open, high, low, close, volume, amount,
                                        adjust_type, factor, created_at, updated_at
                                    )
                                    SELECT
                                        stock_code, symbol_type, CAST(date AS DATE), period,
                                        open, high, low, close, volume, amount,
                                        adjust_type, factor, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                                    FROM temp_batch
                                """)
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

            # 输出跳过清单
            if skipped_list:
                self.log_signal.emit("")
                self.log_signal.emit("=" * 70)
                self.log_signal.emit(f"  跳过清单 ({len(skipped_list)} 只):")
                for skipped_code in skipped_list[:30]:
                    self.log_signal.emit(f"    ⊗ {skipped_code}")
                if len(skipped_list) > 30:
                    self.log_signal.emit(f"    ... 还有 {len(skipped_list) - 30} 只")
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
        """补充历史数据（根据用户填写的日期范围）"""
        try:
            from data_manager.duckdb_connection_pool import get_db_manager
            from xtquant import xtdata
            import pandas as pd

            self.log_signal.emit("✅ 数据管理器初始化成功")

            # 获取用户填写的日期参数
            start_date = self.start_date if self.start_date else '20180101'
            end_date = self.end_date if self.end_date else datetime.now().strftime('%Y%m%d')

            self.log_signal.emit(f"📅 补充日期范围: {start_date} ~ {end_date}")

            # 转换日期格式
            start_dt = pd.to_datetime(start_date, format='%Y%m%d')
            end_dt = pd.to_datetime(end_date, format='%Y%m%d')

            # 获取DuckDB管理器
            manager = get_db_manager(r'D:/StockData/stock_data.ddb')

            # 查询所有股票及其最早日期（排除ETF和基金）
            query = """
                SELECT
                    stock_code,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date
                FROM stock_daily
                WHERE symbol_type = 'stock'
                  AND stock_code NOT LIKE '51%.SH'  -- 排除上海ETF
                  AND stock_code NOT LIKE '159%.SZ'  -- 排除深圳ETF
                  AND stock_code NOT LIKE '150%.SZ'  -- 排除深圳ETF
                  AND stock_code NOT LIKE '588%.SH'  -- 排除上海ETF
                  AND stock_code NOT LIKE '50%.SH'   -- 排除上海50开头基金
                  AND stock_code NOT LIKE '56%.SH'   -- 排除上海56开头基金
                  AND stock_code NOT LIKE '58%.SH'   -- 排除上海58开头基金
                GROUP BY stock_code
                ORDER BY stock_code
            """

            df_stocks = manager.execute_read_query(query)

            if df_stocks.empty:
                self.log_signal.emit("⚠️ 数据库中没有数据，请先下载A股数据")
                self.finished_signal.emit({'total': 0, 'success': 0, 'failed': 0, 'task_type': 'backfill_history'})
                return

            # 筛选需要补充数据的股票
            # 逻辑：数据库中的最新数据早于今天，说明需要更新
            today = datetime.now().date()
            needs_update = df_stocks[df_stocks['latest_date'] < pd.Timestamp(today)].copy()

            if needs_update.empty:
                self.log_signal.emit(f"✅ 所有股票数据都是最新的（截至{today}）")
                self.finished_signal({'total': 0, 'success': 0, 'failed': 0, 'task_type': 'backfill_history'})
                return

            # 为每只股票计算需要补充的日期范围
            # 补充范围：从数据库中最新数据的第二天 到 今天
            needs_update['need_start'] = (needs_update['latest_date'] + timedelta(days=1)).dt.strftime('%Y%m%d')
            needs_update['need_end'] = today.strftime('%Y%m%d')

            # 过滤掉不合理的日期范围（need_start > need_end）
            needs_update = needs_update[needs_update['need_start'] <= needs_update['need_end']]

            if needs_update.empty:
                self.log_signal.emit(f"✅ 所有股票数据都是最新的")
                self.finished_signal({'total': 0, 'success': 0, 'failed': 0, 'task_type': 'backfill_history'})
                return

            stock_codes = needs_update['stock_code'].tolist()
            self.log_signal.emit(f"📊 发现 {len(stock_codes)} 只股票需要更新数据（已排除ETF和基金）")
            self.log_signal.emit(f"📅 更新范围: 各股票最新数据日期的第二天 ~ 今天")

            total = len(stock_codes)
            success_count = 0
            failed_count = 0
            failed_list = []
            backfill_data = []

            # ===== 批量下载优化 =====
            BATCH_SIZE = 100  # 每批处理100只股票
            self.log_signal.emit(f"🚀 使用批量下载模式，每批{BATCH_SIZE}只股票")

            for batch_start in range(0, total, BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, total)
                batch_codes = stock_codes[batch_start:batch_end]

                self.log_signal.emit(f"📊 批次 {batch_start//BATCH_SIZE + 1}/{(total-1)//BATCH_SIZE + 1}: 处理股票 {batch_start+1}-{batch_end}...")

                # 批量读取数据（先让QMT批量下载到本地）
                try:
                    # 批量触发下载（逐个触发但批量处理）
                    for stock_code in batch_codes:
                        try:
                            stock_info = needs_update[needs_update['stock_code'] == stock_code].iloc[0]
                            need_start = stock_info['need_start']
                            need_end = stock_info['need_end']

                            xtdata.download_history_data(
                                stock_code=stock_code,
                                period='1d',
                                start_time=need_start,
                                end_time=need_end
                            )
                        except:
                            pass  # 忽略单个股票下载失败

                    # 批量读取数据
                    batch_data = xtdata.get_market_data_ex(
                        stock_list=batch_codes,
                        period='1d',
                        start_time=start_date,
                        end_time=end_date
                    )

                    # 处理每只股票的数据
                    for stock_code in batch_codes:
                        try:
                            # 获取该股票需要补充的日期范围
                            stock_info = needs_update[needs_update['stock_code'] == stock_code].iloc[0]
                            need_start = stock_info['need_start']
                            need_end = stock_info['need_end']

                            # 检查数据是否存在
                            if isinstance(batch_data, dict) and stock_code in batch_data:
                                df = batch_data[stock_code]
                                if not df.empty:
                                    # 转换数据格式
                                    time_series = pd.to_datetime(df['time'], unit='ms', utc=True).dt.tz_convert('Asia/Shanghai')
                                    df_processed = pd.DataFrame({
                                        'stock_code': stock_code,
                                        'symbol_type': 'stock',
                                        'date': time_series.dt.strftime('%Y-%m-%d'),
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

                                    # 过滤：确保日期在补充范围内
                                    df_processed['date_dt'] = pd.to_datetime(df_processed['date'])
                                    need_start_dt = pd.to_datetime(need_start, format='%Y%m%d')
                                    need_end_dt = pd.to_datetime(need_end, format='%Y%m%d')
                                    df_processed = df_processed[
                                        (df_processed['date_dt'] >= need_start_dt) &
                                        (df_processed['date_dt'] <= need_end_dt)
                                    ]
                                    df_processed = df_processed.drop(columns=['date_dt'])

                                    if not df_processed.empty:
                                        # 不添加复权列，只保存不复权数据
                                        backfill_data.append(df_processed)
                                        success_count += 1
                                    else:
                                        failed_count += 1
                                        failed_list.append(f"{stock_code} - 过滤后无数据（{need_start}~{need_end}）")
                                else:
                                    failed_count += 1
                                    failed_list.append(f"{stock_code} - 返回空数据（{need_start}~{need_end}）")
                            else:
                                failed_count += 1
                                failed_list.append(f"{stock_code} - QMT下载失败（{need_start}~{need_end}）")

                        except Exception as e:
                            failed_count += 1
                            failed_list.append(f"{stock_code} - {str(e)[:30]}")

                except Exception as batch_error:
                    self.log_signal.emit(f"  ⚠️ 批次处理失败: {str(batch_error)[:50]}")
                    # 批次失败，逐个处理
                    for stock_code in batch_codes:
                        failed_count += 1
                        failed_list.append(f"{stock_code} - 批次失败: {str(batch_error)[:20]}")

                # 每批次进度更新
                if (batch_end) % 500 == 0 or batch_end == total:
                    self.log_signal.emit(f"📊 进度: {batch_end}/{total} ({batch_end/total*100:.1f}%) - 成功:{success_count}, 失败:{failed_count}")

            self.log_signal.emit(f"📥 历史数据收集完成: {success_count} 只股票成功")

            # 统计失败原因
            new_stock_count = sum(1 for item in failed_list if '新股' in item)
            no_data_count = sum(1 for item in failed_list if '无数据' in item or '空数据' in item)
            error_count = sum(1 for item in failed_list if '获取失败' in item or '错误' in item)

            self.log_signal.emit(f"📊 失败统计: 总数{failed_count}, 新股{new_stock_count}, 无数据{no_data_count}, 错误{error_count}")

            # 批量写入DuckDB（只插入缺失数据，不删除已有数据）
            if backfill_data:
                self.log_signal.emit("💾 正在写入数据库（只插入缺失部分）...")
                import time
                time.sleep(2)

                try:
                    # 合并所有数据
                    df_all = pd.concat(backfill_data, ignore_index=True)

                    with manager.get_write_connection() as con:
                        # 直接插入缺失数据（不删除已有数据）
                        con.register('temp_backfill', df_all)
                        con.execute("""
                            INSERT INTO stock_daily (
                                stock_code, symbol_type, date, period,
                                open, high, low, close, volume, amount,
                                adjust_type, factor, created_at, updated_at
                            )
                            SELECT
                                stock_code, symbol_type, CAST(date AS DATE), period,
                                open, high, low, close, volume, amount,
                                adjust_type, factor, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                            FROM temp_backfill
                            WHERE NOT EXISTS (
                                SELECT 1 FROM stock_daily sd
                                WHERE sd.stock_code = temp_backfill.stock_code
                                AND sd.date = temp_backfill.date
                                AND sd.period = temp_backfill.period
                            )
                        """)
                        con.unregister('temp_backfill')

                    inserted_count = len(df_all)
                    self.log_signal.emit(f"✅ 成功插入 {inserted_count} 条新记录（已有数据保留）")
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

            # 输出失败清单（分类显示）
            if failed_list:
                self.log_signal.emit("")
                self.log_signal.emit("=" * 70)
                self.log_signal.emit("  失败分类:")

                # 新股
                new_stocks = [item for item in failed_list if '新股' in item]
                if new_stocks:
                    self.log_signal.emit(f"\n  [INFO] 新股（上市时间晚于开始日期）: {len(new_stocks)} 只")
                    for item in new_stocks[:10]:  # 只显示前10个
                        self.log_signal.emit(f"    - {item}")
                    if len(new_stocks) > 10:
                        self.log_signal.emit(f"    ... 省略 {len(new_stocks)-10} 只")

                # 过滤后无数据
                no_data_after_filter = [item for item in failed_list if '过滤后无数据' in item]
                if no_data_after_filter:
                    self.log_signal.emit(f"\n  [WARNING] 过滤后无数据: {len(no_data_after_filter)} 只")
                    for item in no_data_after_filter[:5]:
                        self.log_signal.emit(f"    - {item}")
                    if len(no_data_after_filter) > 5:
                        self.log_signal.emit(f"    ... 省略 {len(no_data_after_filter)-5} 只")

                # 返回空数据（QMT/Tushare都获取到了但为空）
                empty_data = [item for item in failed_list if '返回空数据' in item]
                if empty_data:
                    self.log_signal.emit(f"\n  [WARNING] 数据源返回空: {len(empty_data)} 只")
                    for item in empty_data[:5]:
                        self.log_signal.emit(f"    - {item}")
                    if len(empty_data) > 5:
                        self.log_signal.emit(f"    ... 省略 {len(empty_data)-5} 只")

                # 所有数据源均失败
                all_failed = [item for item in failed_list if '所有数据源均失败' in item]
                if all_failed:
                    self.log_signal.emit(f"\n  [ERROR] QMT和Tushare都失败: {len(all_failed)} 只")
                    for item in all_failed[:5]:
                        self.log_signal.emit(f"    - {item}")
                    if len(all_failed) > 5:
                        self.log_signal.emit(f"    ... 省略 {len(all_failed)-5} 只")

                # 其他异常
                others = [item for item in failed_list if item not in new_stocks + no_data_after_filter + empty_data + all_failed]
                if others:
                    self.log_signal.emit(f"\n  [ERROR] 其他异常: {len(others)} 只")
                    for item in others[:5]:
                        self.log_signal.emit(f"    - {item}")
                    if len(others) > 5:
                        self.log_signal.emit(f"    ... 省略 {len(others)-5} 只")

                self.log_signal.emit(f"\n  总计: {len(failed_list)} 只失败")
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
            # 注意：QMT返回的时间戳是UTC时间，需要转换为北京时间
            df['datetime'] = pd.to_datetime(df['time'], unit='ms', utc=True).dt.tz_convert('Asia/Shanghai')

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
                # 注意：QMT返回的时间戳是UTC时间，需要转换为北京时间
                time_series = pd.to_datetime(df['time'], unit='ms', utc=True).dt.tz_convert('Asia/Shanghai')

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
                # 注意：QMT返回的时间戳是UTC时间，需要转换为北京时间
                # 日线：使用DATE类型（字符串YYYY-MM-DD）
                # 分钟线：使用TIMESTAMP类型（直接保存datetime对象）
                time_series = pd.to_datetime(df['time'], unit='ms', utc=True).dt.tz_convert('Asia/Shanghai')
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

                # 性能优化：移除预存复权列（提升5倍I/O性能）
                # 复权功能改用按需调用QMT API实现
                # 查询时自动调用QMT API获取复权数据
                # 价格列: 4个（open, high, low, close）
                # 复权支持: none（不复权）, front（前复权）, back（后复权）, geometric_front（等比前复权）, geometric_back（等比后复权）

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

        self.update_data_btn = QPushButton("🔄 更新缺失数据")
        self.update_data_btn.setToolTip("智能补全所有缺失的历史数据\n自动检测每只股票的最新日期，补充缺失的部分")
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
        self.backfill_data_btn = QPushButton("📜 补全历史数据")
        self.backfill_data_btn.setToolTip("补充指定日期之前的历史空白\n用于首次使用或发现历史数据缺失时")
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

        # 进度标签
        self.progress_label = QLabel()
        self.progress_label.setVisible(False)
        self.progress_label.setStyleSheet("color: #666; font-size: 9pt;")
        action_layout.addWidget(self.progress_label, 4, 0, 1, 4)

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
        action_layout.addWidget(self.stop_btn, 5, 0, 1, 4)

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

        self.manual_start_date_edit = QDateEdit()
        self.manual_start_date_edit.setCalendarPopup(True)
        self.manual_start_date_edit.setDate(QDate.currentDate().addMonths(-3))
        self.manual_start_date_edit.setDisplayFormat("yyyy-MM-dd")
        date_range_layout.addWidget(self.manual_start_date_edit)

        date_range_layout.addWidget(QLabel("~"))

        self.manual_end_date_edit = QDateEdit()
        self.manual_end_date_edit.setCalendarPopup(True)
        self.manual_end_date_edit.setDate(QDate.currentDate())
        self.manual_end_date_edit.setDisplayFormat("yyyy-MM-dd")
        date_range_layout.addWidget(self.manual_end_date_edit)

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
        self.log("=" * 80)
        self.log("🎯 首次使用指南：请根据情况选择合适的下载选项")
        self.log("")
        self.log("📥 【下载A股数据】- 首次使用必选！")
        self.log("   用途：从零开始建立数据库，自动获取全部A股列表")
        self.log("   说明：下载指定日期范围内的所有A股日线数据")
        self.log("   建议：首次可先下载2024年数据测试，确认无误后再下载更早年份")
        self.log("")
        self.log("📜 【补全历史数据】- 发现历史数据缺失时使用")
        self.log("   用途：补充指定日期之前的历史空白")
        self.log("   说明：需要数据库中已有股票列表，只补充缺失的部分")
        self.log("")
        self.log("🔄 【更新缺失数据】- 日常更新推荐使用")
        self.log("   用途：智能检测并补充最近缺失的数据")
        self.log("   说明：自动补充每只股票从最新日期之后到今天的所有缺失数据")
        self.log("=" * 80)
        self.log("💡 建议：首次使用请点击「下载A股数据」按钮开始")

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
            from pathlib import Path

            db_path = Path(r'D:/StockData/stock_data.ddb')

            # 检查数据库文件是否存在
            if not db_path.exists():
                # 首次使用，数据库文件不存在是正常的
                self.log("ℹ️  DuckDB数据库尚未创建，请先下载股票数据")
                self.log("")
                self.log("🚀 推荐操作流程：")
                self.log("   1. 设置日期范围（建议首次：2024-01-01 ~ 今天）")
                self.log("   2. 点击「📥 下载A股数据」按钮")
                self.log("   3. 等待下载完成（首次可能需要几小时）")
                self.log("")
                self.log("💡 提示：下载过程可以最小化窗口，不影响使用")
                self.log("💡 数据存储位置：D:/StockData/stock_data.ddb")
                self.total_symbols_label.setText("标的总数: 0")
                self.total_stocks_label.setText("股票数量: 0")
                self.total_bonds_label.setText("可转债数量: 0")
                self.total_records_label.setText("总记录数: 0")
                self.total_size_label.setText("存储大小: 0.00 MB")
                self.latest_date_label.setText("最新日期: N/A")
                return

            con = duckdb.connect(str(db_path), read_only=True)

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

            # 安全格式化，处理None值
            self.total_symbols_label.setText(f"标的总数: {total_symbols:,}" if total_symbols is not None else "标的总数: 0")
            self.total_stocks_label.setText(f"股票数量: {stock_count:,}" if stock_count is not None else "股票数量: 0")
            self.total_bonds_label.setText(f"可转债数量: {total_bonds:,}" if total_bonds is not None else "可转债数量: 0")
            self.total_records_label.setText(f"总记录数: {total_records:,}" if total_records is not None else "总记录数: 0")
            self.total_size_label.setText(f"存储大小: {size_mb:.2f} MB" if size_mb is not None else "存储大小: 0.00 MB")
            self.latest_date_label.setText(f"最新日期: {latest_date}" if latest_date is not None and latest_date != 'N/A' else "最新日期: 无数据")

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
        start_date = self.manual_start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.manual_end_date_edit.date().toString("yyyy-MM-dd")

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
        """补充历史数据（获取指定日期范围的完整数据）"""
        # 获取用户选择的日期
        start_date = self.start_date_edit.date().toString('yyyy-MM-dd')
        end_date = self.end_date_edit.date().toString('yyyy-MM-dd')

        reply = QMessageBox.question(
            self, "确认操作",
            f"此操作将为缺失历史数据的股票补充 {start_date} 起至 {end_date} 的数据。\n\n"
            f"只会补充数据库中缺失的部分，已有数据不会被删除。\n\n"
            "可能需要较长时间，确定要继续吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.No:
            return

        if self.download_thread and self.download_thread.isRunning():
            QMessageBox.warning(self, "提示", "已有下载任务正在运行")
            return

        # 获取用户输入的日期
        start_date = self.start_date_edit.date().toString('yyyyMMdd')
        end_date = self.end_date_edit.date().toString('yyyyMMdd')

        self.log(f"📜 开始补充历史数据（{start_date} ~ {end_date}）...")

        self.download_thread = DataDownloadThread(
            task_type='backfill_history',
            symbols=None,
            start_date=start_date,
            end_date=end_date
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
        skipped = result.get('skipped', 0)

        msg = f"下载完成！\n总数: {total}\n成功: {success}\n跳过: {skipped}\n失败: {failed}"

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
            # 显示加载状态
            self.stats_label.setText(f"⏳ 正在加载 {self.stock_code} 的数据...")

            # 使用只读模式连接，避免配置冲突
            import duckdb
            import io
            from contextlib import redirect_stdout

            # 捕获print输出
            log_buffer = io.StringIO()

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
            adjust_type = adjust_map.get(self.adjust, "none")

            con.close()

            # 更新状态：开始查询
            self.stats_label.setText(f"📡 正在查询 {self.stock_code} ({adjust_type})...")

            # 使用统一数据接口查询（支持QMT API复权方案）
            # 重定向print输出到log_buffer
            with redirect_stdout(log_buffer):
                from data_manager.unified_data_interface import UnifiedDataManager

                manager = UnifiedDataManager()

                # 获取数据范围（最近1年）
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - pd.Timedelta(days=365)).strftime('%Y-%m-%d')

                # 查询数据（只显示本地已有数据）
                df = manager.get_stock_data(
                    stock_code=self.stock_code,
                    start_date=start_date,
                    end_date=end_date,
                    period='1d',
                    adjust=adjust_type,
                    auto_save=False,
                    local_only=True  # 只显示本地数据
                )

            # 获取日志输出
            log_output = log_buffer.getvalue()

            # 如果有日志输出，显示在状态栏
            if log_output.strip():
                # 提取关键信息
                lines = log_output.strip().split('\n')
                for line in lines:
                    if '[INFO]' in line or '[OK]' in line or '[WARN]' in line:
                        print(f"📋 {line}")  # 同时输出到控制台

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
            # 使用统一数据接口查询（支持QMT API复权方案）
            from data_manager.unified_data_interface import UnifiedDataManager

            # 映射复权类型
            adjust_map = {
                "none": "none",
                "qfq": "front",
                "hfq": "back"
            }
            adjust_type = adjust_map.get(self.adjust, "none")

            manager = UnifiedDataManager()

            # 获取数据范围（最近1年）
            from datetime import datetime
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - pd.Timedelta(days=365)).strftime('%Y-%m-%d')

            # 查询数据（只导出本地已有数据）
            df = manager.get_stock_data(
                stock_code=self.stock_code,
                start_date=start_date,
                end_date=end_date,
                period='1d',
                adjust=adjust_type,
                auto_save=False,
                local_only=True  # 只导出本地数据
            )

            # 设置日期为索引
            df.set_index('date', inplace=True)

            # 选择保存路径
            default_name = f"{self.stock_code}_{self.adjust}_data.csv"
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
