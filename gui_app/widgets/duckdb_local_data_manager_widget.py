#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DuckDB本地数据管理GUI组件
提供基于DuckDB的数据下载、管理和查看功能

核心特性：
1. DuckDB单文件存储
2. 高性能数据下载和查询
3. 可视化进度显示
4. 完整的错误处理
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QCheckBox, QSpinBox, QComboBox, QProgressBar, QMessageBox,
    QDateEdit, QFileDialog, QSplitter, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt5.QtGui import QFont, QColor

import pandas as pd

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入统一DuckDB管理器
try:
    from data_manager.unified_duckdb_manager import UnifiedDuckDBManager
    DUCKDB_MANAGER_AVAILABLE = True
except ImportError:
    DUCKDB_MANAGER_AVAILABLE = False
    print("警告: 统一DuckDB管理器未找到")


class DuckDBDataDownloadThread(QThread):
    """DuckDB数据下载线程"""

    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # current, total
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, manager, task_type, symbols, start_date, end_date,
                 period='1d', adjust_type='none', data_source='qmt'):
        super().__init__()
        self.manager = manager
        self.task_type = task_type
        self.symbols = symbols if symbols else []
        self.start_date = start_date
        self.end_date = end_date
        self.period = period
        self.adjust_type = adjust_type
        self.data_source = data_source
        self._is_running = True

    def run(self):
        """运行下载任务"""
        try:
            if self.task_type == 'download':
                self._download()
            elif self.task_type == 'update':
                self._update()
            elif self.task_type == 'backfill':
                self._backfill()
        except Exception as e:
            import traceback
            error_msg = f"任务失败: {str(e)}\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg)
            self.error_signal.emit(error_msg)

    def _download(self):
        """下载数据"""
        self.log_signal.emit(f"开始下载数据...")
        self.log_signal.emit(f"股票数量: {len(self.symbols)}")
        self.log_signal.emit(f"日期范围: {self.start_date} ~ {self.end_date}")
        self.log_signal.emit(f"数据源: {self.data_source}")

        if not self._is_running:
            return

        try:
            # 使用DuckDB管理器下载
            results = self.manager.download_data(
                self.symbols,
                self.start_date,
                self.end_date,
                self.period,
                self.adjust_type,
                self.data_source
            )

            success_count = len(results)
            total = len(self.symbols)

            self.log_signal.emit(f"\n下载完成!")
            self.log_signal.emit(f"成功: {success_count}/{total}")
            self.finished_signal.emit({
                'success': success_count,
                'total': total,
                'results': results
            })

        except Exception as e:
            self.error_signal.emit(f"下载失败: {e}")

    def _update(self):
        """增量更新数据"""
        self.log_signal.emit(f"开始增量更新...")

        try:
            results = self.manager.update_data(
                self.symbols,
                self.period,
                self.adjust_type,
                days_back=5
            )

            success_count = len(results)
            total = len(self.symbols)

            self.log_signal.emit(f"\n更新完成!")
            self.log_signal.emit(f"成功: {success_count}/{total}")
            self.finished_signal.emit({
                'success': success_count,
                'total': total
            })

        except Exception as e:
            self.error_signal.emit(f"更新失败: {e}")

    def _backfill(self):
        """回填历史数据"""
        self.log_signal.emit(f"开始回填历史数据...")

        # 回填逻辑与下载类似，但日期范围更远
        self._download()

    def stop(self):
        """停止任务"""
        self._is_running = False


class DuckDBLocalDataManagerWidget(QWidget):
    """DuckDB本地数据管理组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = None
        self.download_thread = None

        # 初始化UI
        self.init_ui()

        # 初始化管理器
        self.init_manager()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 创建标签页
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        # 下载标签页
        download_tab = self.create_download_tab()
        tab_widget.addTab(download_tab, "📥 数据下载")

        # 查询标签页
        query_tab = self.create_query_tab()
        tab_widget.addTab(query_tab, "🔍 数据查询")

        # 统计标签页
        stats_tab = self.create_stats_tab()
        tab_widget.addTab(stats_tab, "📊 统计信息")

    def create_download_tab(self):
        """创建下载标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 设置组
        settings_group = QGroupBox("下载设置")
        settings_layout = QGridLayout()

        # 数据库路径
        settings_layout.addWidget(QLabel("数据库路径:"), 0, 0)
        self.db_path_edit = QLineEdit("D:/StockData/stock_data.ddb")
        settings_layout.addWidget(self.db_path_edit, 0, 1)

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_database)
        settings_layout.addWidget(browse_btn, 0, 2)

        # 日期范围
        settings_layout.addWidget(QLabel("开始日期:"), 1, 0)
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate.currentDate().addYears(-2))
        self.start_date_edit.setCalendarPopup(True)
        settings_layout.addWidget(self.start_date_edit, 1, 1)

        settings_layout.addWidget(QLabel("结束日期:"), 2, 0)
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setCalendarPopup(True)
        settings_layout.addWidget(self.end_date_edit, 2, 1)

        # 数据源
        settings_layout.addWidget(QLabel("数据源:"), 3, 0)
        self.data_source_combo = QComboBox()
        self.data_source_combo.addItems(['qmt', 'tushare'])
        self.data_source_combo.setCurrentText('qmt')
        settings_layout.addWidget(self.data_source_combo, 3, 1)

        # 周期
        settings_layout.addWidget(QLabel("周期:"), 4, 0)
        self.period_combo = QComboBox()
        self.period_combo.addItems(['1d', '1w', '1m'])
        self.period_combo.setCurrentText('1d')
        settings_layout.addWidget(self.period_combo, 4, 1)

        # 复权类型
        settings_layout.addWidget(QLabel("复权类型:"), 5, 0)
        self.adjust_type_combo = QComboBox()
        self.adjust_type_combo.addItems(['none', 'qfq', 'hfq'])
        self.adjust_type_combo.setCurrentText('none')
        settings_layout.addWidget(self.adjust_type_combo, 5, 1)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # 股票列表组
        stock_group = QGroupBox("股票列表")
        stock_layout = QVBoxLayout()

        self.stock_list_edit = QLineEdit()
        self.stock_list_edit.setPlaceholderText("输入股票代码，用逗号分隔（如：000001.SZ,600000.SH）")
        stock_layout.addWidget(self.stock_list_edit)

        quick_btn_layout = QHBoxLayout()
        quick_a_btn = QPushButton("全部A股")
        quick_a_btn.clicked.connect(lambda: self.load_stock_list('all'))
        quick_btn_layout.addWidget(quick_a_btn)

        quick_bond_btn = QPushButton("全部可转债")
        quick_bond_btn.clicked.connect(lambda: self.load_stock_list('bonds'))
        quick_btn_layout.addWidget(quick_bond_btn)

        stock_layout.addLayout(quick_btn_layout)
        stock_group.setLayout(stock_layout)
        layout.addWidget(stock_group)

        # 操作按钮
        button_layout = QHBoxLayout()

        self.download_btn = QPushButton("🚀 开始下载")
        self.download_btn.clicked.connect(self.start_download)
        button_layout.addWidget(self.download_btn)

        self.update_btn = QPushButton("🔄 增量更新")
        self.update_btn.clicked.connect(self.start_update)
        button_layout.addWidget(self.update_btn)

        self.stop_btn = QPushButton("⏹️ 停止")
        self.stop_btn.clicked.connect(self.stop_download)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)

        layout.addLayout(button_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # 日志输出
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        return widget

    def create_query_tab(self):
        """创建查询标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 查询设置
        query_group = QGroupBox("查询条件")
        query_layout = QGridLayout()

        query_layout.addWidget(QLabel("股票代码:"), 0, 0)
        self.query_symbol_edit = QLineEdit()
        self.query_symbol_edit.setPlaceholderText("留空查询全部")
        query_layout.addWidget(self.query_symbol_edit, 0, 1)

        query_layout.addWidget(QLabel("开始日期:"), 1, 0)
        self.query_start_date = QDateEdit()
        self.query_start_date.setDate(QDate.currentDate().addMonths(-1))
        self.query_start_date.setCalendarPopup(True)
        query_layout.addWidget(self.query_start_date, 1, 1)

        query_layout.addWidget(QLabel("结束日期:"), 2, 0)
        self.query_end_date = QDateEdit()
        self.query_end_date.setDate(QDate.currentDate())
        self.query_end_date.setCalendarPopup(True)
        query_layout.addWidget(self.query_end_date, 2, 1)

        query_btn = QPushButton("🔍 查询")
        query_btn.clicked.connect(self.execute_query)
        query_layout.addWidget(query_btn, 3, 1)

        query_group.setLayout(query_layout)
        layout.addWidget(query_group)

        # 查询结果
        result_group = QGroupBox("查询结果")
        result_layout = QVBoxLayout()

        self.result_table = QTableWidget()
        self.result_table.setAlternatingRowColors(True)
        result_layout.addWidget(self.result_table)

        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        return widget

    def create_stats_tab(self):
        """创建统计标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 统计信息
        stats_group = QGroupBox("数据库统计")
        stats_layout = QVBoxLayout()

        self.stats_label = QLabel("点击刷新获取统计信息")
        self.stats_label.setWordWrap(True)
        stats_layout.addWidget(self.stats_label)

        refresh_btn = QPushButton("🔄 刷新统计")
        refresh_btn.clicked.connect(self.refresh_stats)
        stats_layout.addWidget(refresh_btn)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        return widget

    def init_manager(self):
        """初始化管理器"""
        try:
            db_path = self.db_path_edit.text()
            self.manager = UnifiedDuckDBManager(db_path)
            self.log(f"✅ 数据库初始化成功: {db_path}")
        except Exception as e:
            self.log(f"❌ 数据库初始化失败: {e}")
            QMessageBox.critical(self, "错误", f"数据库初始化失败: {e}")

    def browse_database(self):
        """浏览数据库文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择数据库文件", self.db_path_edit.text(), "DuckDB Files (*.ddb)"
        )
        if file_path:
            self.db_path_edit.setText(file_path)

    def load_stock_list(self, list_type):
        """加载股票列表"""
        try:
            if not self.manager:
                QMessageBox.warning(self, "警告", "请先初始化数据库")
                return

            if list_type == 'all':
                # 获取全部A股列表
                self.log("正在获取A股列表...")
                # 这里可以调用QMT API获取股票列表
                # 暂时使用示例列表
                example_stocks = "000001.SZ,000002.SZ,600000.SH,600036.SH"
                self.stock_list_edit.setText(example_stocks)
                self.log(f"已加载示例股票列表")

            elif list_type == 'bonds':
                # 获取可转债列表
                self.log("正在获取可转债列表...")
                example_bonds = "113011.SH,127001.SZ"
                self.stock_list_edit.setText(example_bonds)
                self.log(f"已加载示例可转债列表")

        except Exception as e:
            self.log(f"❌ 加载股票列表失败: {e}")
            QMessageBox.critical(self, "错误", f"加载失败: {e}")

    def start_download(self):
        """开始下载"""
        if not self.manager:
            QMessageBox.warning(self, "警告", "请先初始化数据库")
            return

        # 获取参数
        symbols_str = self.stock_list_edit.text().strip()
        if symbols_str:
            symbols = [s.strip() for s in symbols_str.split(',') if s.strip()]
        else:
            symbols = []

        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
        period = self.period_combo.currentText()
        adjust_type = self.adjust_type_combo.currentText()
        data_source = self.data_source_combo.currentText()

        if not symbols:
            reply = QMessageBox.question(
                self, "确认", "未指定股票列表，是否下载全部A股？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                # 自动获取股票列表
                self.log("正在获取股票列表...")
                # 这里可以实现自动获取逻辑
                pass
            else:
                return

        # 清空日志
        self.log_text.clear()

        # 创建下载线程
        self.download_thread = DuckDBDataDownloadThread(
            self.manager,
            'download',
            symbols,
            start_date,
            end_date,
            period,
            adjust_type,
            data_source
        )

        # 连接信号
        self.download_thread.log_signal.connect(self.log)
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.download_finished)
        self.download_thread.error_signal.connect(self.download_error)

        # 禁用下载按钮，启用停止按钮
        self.download_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # 开始下载
        self.download_thread.start()

    def start_update(self):
        """开始增量更新"""
        if not self.manager:
            QMessageBox.warning(self, "警告", "请先初始化数据库")
            return

        # 获取参数
        symbols_str = self.stock_list_edit.text().strip()
        if symbols_str:
            symbols = [s.strip() for s in symbols_str.split(',') if s.strip()]
        else:
            # 更新所有已有数据
            symbols = self.manager.get_all_symbols()
            self.log(f"将更新 {len(symbols)} 只股票的数据")

        period = self.period_combo.currentText()
        adjust_type = self.adjust_type_combo.currentText()

        # 清空日志
        self.log_text.clear()

        # 创建更新线程
        self.download_thread = DuckDBDataDownloadThread(
            self.manager,
            'update',
            symbols,
            None,  # start_date（自动计算）
            None,  # end_date（自动计算）
            period,
            adjust_type
        )

        # 连接信号
        self.download_thread.log_signal.connect(self.log)
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.download_finished)
        self.download_thread.error_signal.connect(self.download_error)

        # 禁用按钮
        self.download_btn.setEnabled(False)
        self.update_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # 开始更新
        self.download_thread.start()

    def stop_download(self):
        """停止下载"""
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.stop()
            self.log("⚠️ 正在停止下载...")
            self.download_thread.wait()
            self.log("✓ 下载已停止")

            # 恢复按钮状态
            self.download_btn.setEnabled(True)
            self.update_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def update_progress(self, current, total):
        """更新进度"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def download_finished(self, result):
        """下载完成"""
        success = result.get('success', 0)
        total = result.get('total', 0)

        self.log(f"\n✅ 任务完成！成功: {success}/{total}")
        QMessageBox.information(
            self, "完成", f"下载完成！\n成功: {success}/{total}"
        )

        # 恢复按钮状态
        self.download_btn.setEnabled(True)
        self.update_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def download_error(self, error_msg):
        """下载错误"""
        self.log(f"\n❌ {error_msg}")
        QMessageBox.critical(self, "错误", error_msg)

        # 恢复按钮状态
        self.download_btn.setEnabled(True)
        self.update_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def execute_query(self):
        """执行查询"""
        if not self.manager:
            QMessageBox.warning(self, "警告", "请先初始化数据库")
            return

        try:
            # 获取查询条件
            symbol_str = self.query_symbol_edit.text().strip()
            symbols = symbol_str.split(',') if symbol_str else None
            start_date = self.query_start_date.date().toString("yyyy-MM-dd")
            end_date = self.query_end_date.date().toString("yyyy-MM-dd")

            # 执行查询
            df = self.manager.get_data(
                symbols,
                start_date,
                end_date
            )

            if df.empty:
                QMessageBox.information(self, "提示", "查询结果为空")
                return

            # 显示结果
            self.display_results(df)

            self.log(f"✓ 查询完成，共 {len(df)} 条记录")

        except Exception as e:
            self.log(f"❌ 查询失败: {e}")
            QMessageBox.critical(self, "错误", f"查询失败: {e}")

    def display_results(self, df):
        """显示查询结果"""
        # 清空表格
        self.result_table.setRowCount(0)
        self.result_table.setColumnCount(len(df.columns))
        self.result_table.setHorizontalHeaderLabels(df.columns)

        # 填充数据
        for row_idx, row in df.iterrows():
            self.result_table.insertRow(row_idx)
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                self.result_table.setItem(row_idx, col_idx, item)

        # 调整列宽
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

    def refresh_stats(self):
        """刷新统计信息"""
        if not self.manager:
            QMessageBox.warning(self, "警告", "请先初始化数据库")
            return

        try:
            stats = self.manager.get_statistics()

            stats_text = f"""
📊 数据库统计信息

🗄️ 数据库路径: {stats.get('db_path', 'N/A')}
📦 文件大小: {stats.get('file_size_mb', 0)} MB
📈 总记录数: {stats.get('total_records', 0):,}
💹 股票数量: {stats.get('total_symbols', 0)}
📅 日期范围: {stats.get('min_date', 'N/A')} ~ {stats.get('max_date', 'N/A')}
            """

            self.stats_label.setText(stats_text)
            self.log("✓ 统计信息已刷新")

        except Exception as e:
            self.log(f"❌ 获取统计信息失败: {e}")
            QMessageBox.critical(self, "错误", f"获取统计信息失败: {e}")

    def log(self, message):
        """输出日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def closeEvent(self, event):
        """关闭事件"""
        if self.manager:
            self.manager.close()
        event.accept()


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    widget = DuckDBLocalDataManagerWidget()
    widget.show()
    sys.exit(app.exec_())
