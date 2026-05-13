#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版DuckDB增强组件 - 所有下载按钮走DuckDB

修复：
- download_stocks/download_bonds 原来走 LocalDataManager+ParquetStorage
  在 pyarrow 版本过低时保存失败。现在统一走 UnifiedDuckDBManager。
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入DuckDB管理器
try:
    from data_manager.unified_duckdb_manager import UnifiedDuckDBManager
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

from config.env_config import get_default_db_path

# 导入原版组件
from gui_app.widgets.local_data_manager_widget import (
    LocalDataManagerWidget as _OriginalLocalDataManagerWidget,
    DataDownloadThread
)


class LocalDataManagerWidget(_OriginalLocalDataManagerWidget):
    """
    本地数据管理GUI组件 - DuckDB增强版

    策略：
    - UI界面：完全继承原版
    - 下载A股/可转债：走 UnifiedDuckDBManager（绕过 pyarrow 依赖）
    - 更新/补全：已由原版直接写 DuckDB，无需覆盖
    """

    def __init__(self, parent=None):
        self.duckdb_manager = None
        self.use_duckdb = DUCKDB_AVAILABLE

        _OriginalLocalDataManagerWidget.__init__(self)

        if self.use_duckdb:
            self.log("DuckDB单文件存储已启用（延迟初始化）")
            self.log(f"   数据库: {get_default_db_path()}")

    def _ensure_duckdb_manager(self):
        """确保 DuckDB 管理器已创建"""
        if not self.duckdb_manager:
            db_path = get_default_db_path()
            self.duckdb_manager = UnifiedDuckDBManager(db_path)
            self.log("DuckDB管理器已创建")
        return self.duckdb_manager

    def _get_duckdb_connection(self):
        """复用已有 duckdb_manager 的连接，避免 read_only 冲突"""
        from pathlib import Path
        db_path = Path(get_default_db_path())
        if not db_path.exists():
            return None
        manager = self._ensure_duckdb_manager()
        return manager.conn

    def load_duckdb_statistics(self):
        """复用 duckdb_manager 连接加载统计，不新开连接"""
        try:
            from pathlib import Path

            db_path = Path(get_default_db_path())

            if not db_path.exists():
                self.log("ℹ️  DuckDB数据库尚未创建，请先下载股票数据")
                self.log(f"💡 数据存储位置：{get_default_db_path()}")
                self.total_symbols_label.setText("标的总数: 0")
                self.total_stocks_label.setText("股票数量: 0")
                self.total_bonds_label.setText("可转债数量: 0")
                self.total_records_label.setText("总记录数: 0")
                self.total_size_label.setText("存储大小: 0.00 MB")
                self.latest_date_label.setText("最新日期: N/A")
                return

            con = self._get_duckdb_connection()
            if con is None:
                return

            # 不关闭连接（属于 duckdb_manager 管理）

            # 检测表结构
            tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]

            if 'stock_daily' in tables:
                cols = [row[0] for row in con.execute("DESCRIBE stock_daily").fetchall()]
                code_col = 'stock_code' if 'stock_code' in cols else 'symbol'
                has_symbol_type = 'symbol_type' in cols

                if has_symbol_type:
                    symbol_type_expr = "SUM(CASE WHEN symbol_type = 'stock' THEN 1 ELSE 0 END)"
                else:
                    symbol_type_expr = "COUNT(*)"

                stats_daily = con.execute(f"""
                    SELECT
                        COUNT(DISTINCT {code_col}) as stock_count,
                        {symbol_type_expr} as stock_only,
                        0 as etf_count,
                        COUNT(*) as total_records,
                        MAX(date) as latest_date
                    FROM stock_daily
                """).fetchone()
            elif 'stock_data' in tables:
                stats_daily = con.execute("""
                    SELECT
                        COUNT(DISTINCT symbol) as stock_count,
                        COUNT(*) as stock_only,
                        0 as etf_count,
                        COUNT(*) as total_records,
                        MAX(date) as latest_date
                    FROM stock_data
                """).fetchone()
            else:
                self.log("ℹ️  数据库中没有数据表，请先下载股票数据")
                return

            # 统计分钟数据表
            minute_tables = ['stock_1m', 'stock_5m', 'stock_15m', 'stock_30m', 'stock_60m']
            minute_records = 0
            for table in minute_tables:
                try:
                    count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                    if count:
                        minute_records += count[0]
                except:
                    pass

            # 更新UI
            total_symbols = stats_daily[0] if stats_daily else 0
            stock_count = stats_daily[1] if stats_daily else 0
            etf_count = stats_daily[2] if stats_daily else 0
            daily_records = stats_daily[3] if stats_daily else 0
            latest_date = str(stats_daily[4]) if stats_daily and stats_daily[4] else 'N/A'

            total_records = daily_records + minute_records
            total_bonds = 0
            size_mb = total_records * 0.0001

            self.total_symbols_label.setText(f"标的总数: {total_symbols:,}" if total_symbols is not None else "标的总数: 0")
            self.total_stocks_label.setText(f"股票数量: {stock_count:,}" if stock_count is not None else "股票数量: 0")
            self.total_bonds_label.setText(f"可转债数量: {total_bonds:,}" if total_bonds is not None else "可转债数量: 0")
            self.total_records_label.setText(f"总记录数: {total_records:,}" if total_records is not None else "总记录数: 0")
            self.total_size_label.setText(f"存储大小: {size_mb:.2f} MB" if size_mb is not None else "存储大小: 0.00 MB")
            self.latest_date_label.setText(f"最新日期: {latest_date}" if latest_date is not None and latest_date != 'N/A' else "最新日期: 无数据")

        except Exception as e:
            self.log(f"[ERROR] 加载统计数据失败: {e}")

    def _get_stock_list(self):
        """获取全部A股列表（排除ETF和基金）"""
        try:
            import easy_xt
            api = easy_xt.get_api()
            try:
                api.init_data()
            except Exception:
                pass

            from xtquant import xtdata
            stock_list = xtdata.get_stock_list_in_sector('沪深A股')
            if not stock_list:
                return []

            etf_patterns = ('51', '159', '150', '588', '50', '56', '58')
            return [s for s in stock_list
                    if not any(s.startswith(p) for p in etf_patterns)]
        except Exception as e:
            self.log(f"获取股票列表失败: {e}")
            return []

    def _get_bond_list(self):
        """获取可转债列表"""
        try:
            from xtquant import xtdata
            bond_list = xtdata.get_stock_list_in_sector('可转债')
            return bond_list if bond_list else []
        except Exception as e:
            self.log(f"获取可转债列表失败: {e}")
            return []

    # ===== 覆盖下载按钮方法 =====

    def download_stocks(self):
        """下载A股数据 - 使用DuckDB"""
        if not self.use_duckdb:
            return super().download_stocks()

        if self.download_thread and self.download_thread.isRunning():
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "提示", "已有下载任务正在运行")
            return

        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")

        self.log(f"开始下载A股数据 ({start_date} ~ {end_date})")

        # 获取股票列表
        self.log("正在获取A股列表...")
        symbols = self._get_stock_list()
        if not symbols:
            self.log("获取股票列表失败，使用默认列表")
            symbols = ['000001.SZ', '600000.SH', '600519.SH']
        self.log(f"获取到 {len(symbols)} 只A股")

        # 创建DuckDB下载线程
        manager = self._ensure_duckdb_manager()
        self.download_thread = DuckDBDataDownloadThread(
            manager, symbols, start_date, end_date
        )
        self._connect_thread_signals()
        self.download_thread.start()
        self._set_download_state(True)

    def download_bonds(self):
        """下载可转债数据 - 使用DuckDB"""
        if not self.use_duckdb:
            return super().download_bonds()

        if self.download_thread and self.download_thread.isRunning():
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "提示", "已有下载任务正在运行")
            return

        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")

        self.log(f"开始下载可转债数据 ({start_date} ~ {end_date})")

        # 获取可转债列表
        self.log("正在获取可转债列表...")
        symbols = self._get_bond_list()
        if not symbols:
            self.log("获取可转债列表失败")
            return
        self.log(f"获取到 {len(symbols)} 只可转债")

        manager = self._ensure_duckdb_manager()
        self.download_thread = DuckDBDataDownloadThread(
            manager, symbols, start_date, end_date
        )
        self._connect_thread_signals()
        self.download_thread.start()
        self._set_download_state(True)

    def update_data(self):
        """一键补充数据 - 使用DuckDB"""
        if not self.use_duckdb:
            return super().update_data()

        if self.download_thread and self.download_thread.isRunning():
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "提示", "已有下载任务正在运行")
            return

        self.log("开始补充数据...")

        manager = self._ensure_duckdb_manager()
        self.download_thread = DuckDBUpdateThread(manager)
        self._connect_thread_signals()
        self.download_thread.start()
        self._set_download_state(True)

    def backfill_historical_data(self):
        """补充历史数据 - 使用DuckDB"""
        if not self.use_duckdb:
            return super().backfill_historical_data()

        from PyQt5.QtWidgets import QMessageBox
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

        start_fmt = self.start_date_edit.date().toString('yyyyMMdd')
        end_fmt = self.end_date_edit.date().toString('yyyyMMdd')

        self.log(f"开始补充历史数据（{start_fmt} ~ {end_fmt}）...")

        manager = self._ensure_duckdb_manager()
        self.download_thread = DuckDBBackfillThread(manager, start_date, end_date)
        self._connect_thread_signals()
        self.download_thread.start()
        self._set_download_state(True)

    def _connect_thread_signals(self):
        """连接下载线程信号"""
        self.download_thread.log_signal.connect(self.log)
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.on_download_finished)
        self.download_thread.error_signal.connect(self.on_download_error)

    def log(self, message):
        """输出日志"""
        if hasattr(self, 'log_text'):
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.append(f"[{timestamp}] {message}")
        else:
            print(message)

    def closeEvent(self, event):
        """关闭事件"""
        if self.duckdb_manager:
            try:
                self.duckdb_manager.close()
            except Exception:
                pass
        try:
            super().closeEvent(event)
        except Exception:
            event.accept()


class DuckDBDataDownloadThread(DataDownloadThread):
    """DuckDB数据下载线程 - 绕过 ParquetStorage/pyarrow"""

    def __init__(self, manager, symbols, start_date, end_date,
                 period='1d', adjust_type='none', data_source='qmt'):
        super().__init__('download', symbols, start_date, end_date)
        self.duckdb_manager = manager
        self.period = period
        self.adjust_type = adjust_type
        self.data_source = data_source

    def run(self):
        try:
            self.log_signal.emit(f"使用DuckDB存储，股票数量: {len(self.symbols)}")
            self.log_signal.emit(f"日期范围: {self.start_date} ~ {self.end_date}")

            success_count = 0
            total = len(self.symbols)
            failed_list = []

            for i, symbol in enumerate(self.symbols):
                if not self._is_running:
                    self.log_signal.emit("用户中断下载")
                    break

                try:
                    self.progress_signal.emit(i + 1, total)

                    df = self.duckdb_manager._fetch_from_source(
                        symbol, self.start_date, self.end_date,
                        self.period, self.adjust_type, self.data_source
                    )

                    if df is not None and not df.empty:
                        self.duckdb_manager.save_data(
                            df, symbol, self.period, self.adjust_type
                        )
                        success_count += 1
                        if (i + 1) % 100 == 0:
                            self.log_signal.emit(
                                f"  进度: {i+1}/{total} | 成功: {success_count}"
                            )
                    else:
                        failed_list.append(f"{symbol} - 数据为空")

                except Exception as e:
                    failed_list.append(f"{symbol} - {str(e)[:50]}")

            failed_count = len(failed_list)
            self.log_signal.emit(
                f"\n下载完成! 成功: {success_count}/{total}, 失败: {failed_count}"
            )
            self.log_signal.emit(f"存储: DuckDB ({get_default_db_path()})")

            if failed_list and len(failed_list) <= 20:
                self.log_signal.emit("失败清单:")
                for item in failed_list:
                    self.log_signal.emit(f"  {item}")

            self.finished_signal.emit({
                'total': total,
                'success': success_count,
                'failed': failed_count,
                'failed_list': failed_list,
            })

        except Exception as e:
            import traceback
            error_msg = f"下载失败: {str(e)}\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)


class DuckDBUpdateThread(DataDownloadThread):
    """DuckDB更新线程 - 使用 UnifiedDuckDBManager 写 stock_data"""

    def __init__(self, manager):
        super().__init__('update_data', None, None, None)
        self.duckdb_manager = manager

    def run(self):
        try:
            from datetime import datetime, timedelta
            import pandas as pd

            self.log_signal.emit("正在检测缺失数据...")

            # 通过 VIEW 查询需要更新的股票（VIEW 支持 SELECT）
            con = self.duckdb_manager.conn
            try:
                df_stocks = con.execute("""
                    SELECT
                        stock_code,
                        MAX(date) as latest_date,
                        DATEDIFF('day', MAX(date), CURRENT_DATE) as days_behind
                    FROM stock_daily
                    WHERE stock_code IS NOT NULL
                    GROUP BY stock_code
                    HAVING DATEDIFF('day', MAX(date), CURRENT_DATE) > 0
                    ORDER BY days_behind DESC
                """).fetchdf()
            except Exception:
                # stock_daily VIEW 可能不存在，尝试 stock_data
                df_stocks = con.execute("""
                    SELECT
                        symbol as stock_code,
                        MAX(date) as latest_date,
                        DATEDIFF('day', MAX(date), CURRENT_DATE) as days_behind
                    FROM stock_data
                    GROUP BY symbol
                    HAVING DATEDIFF('day', MAX(date), CURRENT_DATE) > 0
                    ORDER BY days_behind DESC
                """).fetchdf()

            if df_stocks.empty:
                self.log_signal.emit("所有数据都是最新的，无需更新")
                self.finished_signal.emit({'total': 0, 'success': 0, 'failed': 0})
                return

            stock_codes = df_stocks['stock_code'].tolist()
            self.log_signal.emit(f"发现 {len(stock_codes)} 只股票需要更新")

            total = len(stock_codes)
            success_count = 0
            failed_list = []

            for i, symbol in enumerate(stock_codes):
                if not self._is_running:
                    self.log_signal.emit("用户中断更新")
                    break

                try:
                    self.progress_signal.emit(i + 1, total)

                    row = df_stocks[df_stocks['stock_code'] == symbol].iloc[0]
                    latest_dt = pd.to_datetime(row['latest_date'])
                    start_dt = latest_dt + timedelta(days=1)
                    end_dt = datetime.now()

                    start_date = start_dt.strftime('%Y%m%d')
                    end_date = end_dt.strftime('%Y%m%d')

                    df = self.duckdb_manager._fetch_from_source(
                        symbol, start_date, end_date, '1d', 'none', 'qmt'
                    )

                    if df is not None and not df.empty:
                        self.duckdb_manager.save_data(df, symbol, '1d', 'none')
                        success_count += 1
                        if (i + 1) % 100 == 0:
                            self.log_signal.emit(f"  进度: {i+1}/{total} | 成功: {success_count}")
                    else:
                        failed_list.append(f"{symbol} - 无新数据")

                except Exception as e:
                    failed_list.append(f"{symbol} - {str(e)[:50]}")

            failed_count = len(failed_list)
            self.log_signal.emit(f"更新完成! 成功: {success_count}/{total}, 失败: {failed_count}")

            self.finished_signal.emit({
                'total': total,
                'success': success_count,
                'failed': failed_count,
                'failed_list': failed_list,
            })

        except Exception as e:
            import traceback
            error_msg = f"更新失败: {str(e)}\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)


class DuckDBBackfillThread(DataDownloadThread):
    """DuckDB回补线程 - 使用 UnifiedDuckDBManager 写 stock_data"""

    def __init__(self, manager, start_date, end_date):
        super().__init__('backfill_history', None, start_date, end_date)
        self.duckdb_manager = manager

    def run(self):
        try:
            from xtquant import xtdata
            import pandas as pd

            self.log_signal.emit(f"回补日期范围: {self.start_date} ~ {self.end_date}")

            # 查询已有股票列表
            con = self.duckdb_manager.conn
            try:
                df_stocks = con.execute("""
                    SELECT DISTINCT stock_code FROM stock_daily
                """).fetchdf()
                stock_codes = df_stocks['stock_code'].tolist()
            except Exception:
                df_stocks = con.execute("""
                    SELECT DISTINCT symbol as stock_code FROM stock_data
                """).fetchdf()
                stock_codes = df_stocks['stock_code'].tolist()

            if not stock_codes:
                self.log_signal.emit("数据库中没有股票，请先下载数据")
                self.finished_signal.emit({'total': 0, 'success': 0, 'failed': 0})
                return

            total = len(stock_codes)
            success_count = 0
            failed_list = []

            for i, symbol in enumerate(stock_codes):
                if not self._is_running:
                    self.log_signal.emit("用户中断")
                    break

                try:
                    self.progress_signal.emit(i + 1, total)

                    df = self.duckdb_manager._fetch_from_source(
                        symbol, self.start_date, self.end_date, '1d', 'none', 'qmt'
                    )

                    if df is not None and not df.empty:
                        self.duckdb_manager.save_data(df, symbol, '1d', 'none')
                        success_count += 1
                        if (i + 1) % 100 == 0:
                            self.log_signal.emit(f"  进度: {i+1}/{total} | 成功: {success_count}")
                    else:
                        failed_list.append(f"{symbol} - 无数据")

                except Exception as e:
                    failed_list.append(f"{symbol} - {str(e)[:50]}")

            failed_count = len(failed_list)
            self.log_signal.emit(f"回补完成! 成功: {success_count}/{total}, 失败: {failed_count}")

            self.finished_signal.emit({
                'total': total,
                'success': success_count,
                'failed': failed_count,
                'failed_list': failed_list,
            })

        except Exception as e:
            import traceback
            error_msg = f"回补失败: {str(e)}\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)
