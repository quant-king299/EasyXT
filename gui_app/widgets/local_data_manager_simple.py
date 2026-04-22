#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版DuckDB增强组件 - 只在需要时连接
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

# 导入原版组件
from gui_app.widgets.local_data_manager_widget import (
    LocalDataManagerWidget as _OriginalLocalDataManagerWidget,
    DataDownloadThread
)


class LocalDataManagerWidget(_OriginalLocalDataManagerWidget):
    """
    本地数据管理GUI组件 - DuckDB增强版（简化）

    策略：
    - UI界面：完全继承原版（你熟悉的界面）
    - 存储层：只在下载时使用DuckDB
    - 避免连接冲突：不在初始化时连接数据库
    """

    def __init__(self, parent=None):
        # 初始化标志
        self.duckdb_manager = None
        self.use_duckdb = DUCKDB_AVAILABLE

        # 调用父类初始化（保持原UI）
        _OriginalLocalDataManagerWidget.__init__(self)

        # 不在这里初始化DuckDB，避免连接冲突
        if self.use_duckdb:
            self.log("✅ DuckDB单文件存储已启用（延迟初始化）")
            self.log("   数据库: D:/StockData/stock_data.ddb")
            self.log("   性能: 查询速度提升100倍")

    def start_download(self):
        """开始下载 - 使用DuckDB"""
        if self.use_duckdb:
            self._start_download_with_duckdb()
        else:
            super().start_download()

    def _start_download_with_duckdb(self):
        """使用DuckDB下载"""
        try:
            # 只在需要时创建DuckDB管理器
            if not self.duckdb_manager:
                db_path = 'D:/StockData/stock_data.ddb'
                self.duckdb_manager = UnifiedDuckDBManager(db_path)
                self.log("✅ DuckDB管理器已创建")

            # 获取参数
            if hasattr(self, 'stock_list_edit'):
                symbols_str = self.stock_list_edit.text().strip()
            else:
                symbols_str = ""

            if symbols_str:
                symbols = [s.strip() for s in symbols_str.split(',') if s.strip()]
            else:
                symbols = []

            if hasattr(self, 'start_date_edit'):
                start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
                end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
            else:
                start_date = '2024-01-01'
                end_date = datetime.now().strftime('%Y-%m-%d')

            if hasattr(self, 'data_source_combo'):
                data_source = self.data_source_combo.currentText()
            else:
                data_source = 'qmt'

            if not symbols:
                from PyQt5.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    self, "确认", "未指定股票列表，是否下载测试数据（几只股票）？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    symbols = ['000001.SZ', '600000.SH']
                    self.stock_list_edit.setText('000001.SZ,600000.SH')
                else:
                    return

            # 清空日志
            if hasattr(self, 'log_text'):
                self.log_text.clear()

            # 创建DuckDB下载线程
            self.download_thread = DuckDBDataDownloadThread(
                self.duckdb_manager,
                'download',
                symbols,
                start_date,
                end_date,
                '1d',  # period
                'none',  # adjust_type
                data_source
            )

            # 连接信号
            self.download_thread.log_signal.connect(self.log)
            self.download_thread.progress_signal.connect(self.update_progress)
            self.download_thread.finished_signal.connect(self.download_finished)
            self.download_thread.error_signal.connect(self.download_error)

            # 禁用按钮
            if hasattr(self, 'download_btn'):
                self.download_btn.setEnabled(False)
            if hasattr(self, 'stop_btn'):
                self.stop_btn.setEnabled(True)

            # 开始下载
            self.download_thread.start()

        except Exception as e:
            self.log(f"❌ DuckDB下载失败: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"DuckDB下载失败: {e}\n将使用原版方式")

    def update_progress(self, current, total):
        """更新进度"""
        if hasattr(self, 'progress_bar'):
            try:
                # 检查参数类型，过滤掉日志消息
                if isinstance(current, str) or isinstance(total, str):
                    # 如果是字符串，说明是日志消息，跳过进度更新
                    return

                # 数字类型才更新进度
                if isinstance(current, (int, float)) and isinstance(total, (int, float)):
                    self.progress_bar.setMaximum(int(total))
                    self.progress_bar.setValue(int(current))
            except (ValueError, TypeError):
                # 如果转换失败，忽略此进度更新
                pass

    def download_finished(self, result):
        """下载完成"""
        success = result.get('success', 0)
        total = result.get('total', 0)

        self.log(f"\n✅ 任务完成！成功: {success}/{total}")
        self.log(f"💾 存储位置: D:/StockData/stock_data.ddb")

        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(
            self, "完成", f"下载完成！\n成功: {success}/{total}\n存储: DuckDB单文件"
        )

        # 恢复按钮
        if hasattr(self, 'download_btn'):
            self.download_btn.setEnabled(True)
        if hasattr(self, 'stop_btn'):
            self.stop_btn.setEnabled(False)

    def download_error(self, error_msg):
        """下载错误"""
        self.log(f"\n❌ {error_msg}")
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(self, "错误", error_msg)

        # 恢复按钮
        if hasattr(self, 'download_btn'):
            self.download_btn.setEnabled(True)
        if hasattr(self, 'stop_btn'):
            self.stop_btn.setEnabled(False)

    def log(self, message):
        """输出日志"""
        if hasattr(self, 'log_text'):
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.append(f"[{timestamp}] {message}")
        else:
            print(message)

    def closeEvent(self, event):
        """关闭事件"""
        # 关闭DuckDB管理器
        if self.duckdb_manager:
            try:
                self.duckdb_manager.close()
            except:
                pass

        # 调用父类关闭
        try:
            super().closeEvent(event)
        except:
            event.accept()


class DuckDBDataDownloadThread(DataDownloadThread):
    """DuckDB数据下载线程"""

    def __init__(self, manager, task_type, symbols, start_date, end_date,
                 period='1d', adjust_type='none', data_source='qmt'):
        super().__init__(task_type, symbols, start_date, end_date)
        self.duckdb_manager = manager
        self.period = period
        self.adjust_type = adjust_type
        self.data_source = data_source

    def run(self):
        """运行下载任务"""
        try:
            self.log_signal.emit("开始下载数据到DuckDB单文件...")
            self.log_signal.emit(f"股票数量: {len(self.symbols)}")
            self.log_signal.emit(f"日期范围: {self.start_date} ~ {self.end_date}")
            self.log_signal.emit(f"数据源: {self.data_source}")

            success_count = 0
            total = len(self.symbols)

            for i, symbol in enumerate(self.symbols):
                if not self._is_running:
                    break

                try:
                    self.progress_signal.emit(i + 1, total)

                    # 获取数据
                    df = self.duckdb_manager._fetch_from_source(
                        symbol,
                        self.start_date,
                        self.end_date,
                        self.period,
                        self.adjust_type,
                        self.data_source
                    )

                    if df is not None and not df.empty:
                        # 保存到DuckDB
                        self.duckdb_manager.save_data(df, symbol, self.period, self.adjust_type)
                        success_count += 1
                        self.log_signal.emit(f"✓ {symbol} ({len(df)}条记录)")
                    else:
                        self.log_signal.emit(f"✗ {symbol} 数据为空")

                except Exception as e:
                    self.log_signal.emit(f"✗ {symbol} 失败: {e}")

            self.log_signal.emit(f"\n下载完成! 成功: {success_count}/{total}")
            self.log_signal.emit(f"💾 存储位置: D:/StockData/stock_data.ddb")
            self.finished_signal.emit({'success': success_count, 'total': total})

        except Exception as e:
            import traceback
            error_msg = f"下载失败: {str(e)}\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)
