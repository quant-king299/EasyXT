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
            return [s for s in stock_list if not s.startswith(etf_pattern)
                    for etf_pattern in etf_pattern] if False else \
                   [s for s in stock_list
                    if not any(s.startswith(p) for p in etf_pattern)]
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
