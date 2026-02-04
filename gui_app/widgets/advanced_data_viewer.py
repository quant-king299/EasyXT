#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级本地数据查看器 - 上下分栏布局 + 专业交易风格
重点：数据表格查看
"""

import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QPushButton, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox,
    QProgressBar, QSplitter, QFrame, QMessageBox,
    QDateEdit, QFileDialog, QTreeWidget, QTreeWidgetItem,
    QLineEdit, QStatusBar, QToolBar, QAction, QAbstractItemView,
    QMenu, QApplication, QScrollArea
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate, QTimer, QSize
from PyQt5.QtGui import QFont, QColor, QIcon, QStandardItemModel, QStandardItem, QPalette

# 添加父目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'data_manager'))

import duckdb
import pandas as pd

try:
    from data_manager.duckdb_connection_pool import get_db_manager
    DB_MANAGER_AVAILABLE = True
except ImportError:
    DB_MANAGER_AVAILABLE = False


# 专业交易风格样式表
DARK_THEME_STYLESHEET = """
QWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
    font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
    font-size: 11px;
}

QTableWidget {
    background-color: #252526;
    alternate-background-color: #2a2a2a;
    gridline-color: #3e3e42;
    border: 1px solid #3e3e42;
    selection-background-color: #264f78;
    color: #d4d4d4;
}

QTableWidget::item {
    padding: 6px;
    border: none;
}

QTableWidget::item:selected {
    background-color: #264f78;
    color: #ffffff;
}

QTableWidget::item:hover {
    background-color: #2a2d2e;
}

QHeaderView::section {
    background-color: #333333;
    color: #cccccc;
    padding: 8px;
    border: none;
    border-right: 1px solid #3e3e42;
    border-bottom: 1px solid #3e3e42;
    font-weight: bold;
}

QTreeWidget {
    background-color: #252526;
    border: 1px solid #3e3e42;
}

QTreeWidget::item {
    padding: 5px;
}

QTreeWidget::item:selected {
    background-color: #264f78;
    color: #ffffff;
}

QTreeWidget::item:hover {
    background-color: #2a2d2e;
}

QTreeWidget::branch:has-children:!has-siblings:closed,
QTreeWidget::branch:closed:has-children:has-siblings {
    border-image: none;
    image: url(none);
}

QLineEdit {
    background-color: #3c3c3c;
    border: 1px solid #3e3e42;
    border-radius: 3px;
    padding: 5px;
    color: #d4d4d4;
}

QLineEdit:focus {
    border: 1px solid #007acc;
}

QComboBox {
    background-color: #3c3c3c;
    border: 1px solid #3e3e42;
    border-radius: 3px;
    padding: 5px;
    color: #d4d4d4;
}

QComboBox::drop-down {
    border: none;
}

QComboBox::down-arrow {
    image: url(none);
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #cccccc;
    width: 0;
    height: 0;
}

QCheckBox {
    spacing: 5px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    background-color: #3c3c3c;
    border: 1px solid #3e3e42;
    border-radius: 3px;
}

QCheckBox::indicator:checked {
    background-color: #007acc;
    border-color: #007acc;
}

QCheckBox::indicator:checked::after {
    content: '✓';
}

QPushButton {
    background-color: #0e639c;
    color: white;
    border: none;
    border-radius: 3px;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #1177bb;
}

QPushButton:pressed {
    background-color: #0e5485;
}

QPushButton:disabled {
    background-color: #3c3c3c;
    color: #7f7f7f;
}

QDateEdit {
    background-color: #3c3c3c;
    border: 1px solid #3e3e42;
    border-radius: 3px;
    padding: 5px;
    color: #d4d4d4;
}

QSplitter::handle {
    background-color: #3e3e42;
}

QSplitter::handle:horizontal {
    width: 2px;
}

QSplitter::handle:vertical {
    height: 2px;
}

QLabel {
    color: #cccccc;
}

QGroupBox {
    border: 1px solid #3e3e42;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
    color: #cccccc;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
"""


class DataLoadThread(QThread):
    """数据加载线程"""
    data_ready = pyqtSignal(pd.DataFrame, str)
    error_occurred = pyqtSignal(str)

    def __init__(self, stock_code: str, start_date: str, end_date: str, adjust_type: str = 'none'):
        super().__init__()
        self.stock_code = stock_code
        self.start_date = start_date
        self.end_date = end_date
        self.adjust_type = adjust_type

    def run(self):
        try:
            if DB_MANAGER_AVAILABLE:
                manager = get_db_manager(r'D:/StockData/stock_data.ddb')

                # 根据复权类型选择列
                if self.adjust_type == 'none':
                    price_cols = ['open', 'high', 'low', 'close']
                elif self.adjust_type == 'front':
                    price_cols = ['open_front', 'high_front', 'low_front', 'close_front']
                elif self.adjust_type == 'back':
                    price_cols = ['open_back', 'high_back', 'low_back', 'close_back']
                else:
                    price_cols = ['open', 'high', 'low', 'close']

                query = f"""
                    SELECT
                        date,
                        {price_cols[0]} as open,
                        {price_cols[1]} as high,
                        {price_cols[2]} as low,
                        {price_cols[3]} as close,
                        volume,
                        amount
                    FROM stock_daily
                    WHERE stock_code = '{self.stock_code}'
                      AND date >= '{self.start_date}'
                      AND date <= '{self.end_date}'
                    ORDER BY date
                """

                df = manager.execute_read_query(query)
            else:
                con = duckdb.connect(r'D:/StockData/stock_data.ddb', read_only=True)
                df = con.execute("SELECT * FROM stock_daily LIMIT 1").df()
                con.close()

            if not df.empty:
                df = df.set_index('date')

            self.data_ready.emit(df, self.stock_code)

        except Exception as e:
            self.error_occurred.emit(str(e))


class AdvancedDataViewer(QWidget):
    """高级数据查看器 - 上下分栏布局 + 专业交易风格"""

    def __init__(self):
        super().__init__()
        self.current_stock = None
        self.current_data = None
        self.init_ui()
        self.apply_dark_theme()
        self.load_initial_data()

    def init_ui(self):
        """初始化UI - 上下分栏布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 顶部控制栏
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)

        # 主分割器（上下分栏）
        main_splitter = QSplitter(Qt.Vertical)

        # 上部：股票选择列表
        stock_panel = self.create_stock_selection_panel()
        main_splitter.addWidget(stock_panel)

        # 下部：数据表格（重点）
        table_panel = self.create_data_table_panel()
        main_splitter.addWidget(table_panel)

        # 设置分割比例（上3下7）
        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 7)

        layout.addWidget(main_splitter)

        # 状态栏
        self.status_label = QLabel("📊 就绪 - 请选择股票查看数据")
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 8px;
                background-color: #007acc;
                color: white;
                border-radius: 3px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.status_label)

    def create_control_panel(self):
        """创建顶部控制面板"""
        panel = QFrame()
        panel.setFixedHeight(70)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # 左侧：股票信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        self.stock_label = QLabel("当前股票: 未选择")
        self.stock_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #4ec9b0;")
        info_layout.addWidget(self.stock_label)

        self.record_count_label = QLabel("记录数: 0")
        self.record_count_label.setStyleSheet("font-size: 11px; color: #808080;")
        info_layout.addWidget(self.record_count_label)

        layout.addLayout(info_layout)

        # 中间：复权和日期控制
        control_layout = QGridLayout()
        control_layout.setSpacing(8)

        control_layout.addWidget(QLabel("复权类型:"), 0, 0)
        self.adjust_combo = QComboBox()
        self.adjust_combo.addItems(["不复权", "前复权", "后复权"])
        self.adjust_combo.setMinimumWidth(100)
        self.adjust_combo.currentTextChanged.connect(self.on_adjust_changed)
        control_layout.addWidget(self.adjust_combo, 0, 1)

        control_layout.addWidget(QLabel("起始日期:"), 0, 2)
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-3))
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        control_layout.addWidget(self.start_date_edit, 0, 3)

        control_layout.addWidget(QLabel("结束日期:"), 1, 0)
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        control_layout.addWidget(self.end_date_edit, 1, 1)

        layout.addLayout(control_layout)

        # 右侧：操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.load_btn = QPushButton("📥 加载数据")
        self.load_btn.clicked.connect(self.load_current_stock)
        btn_layout.addWidget(self.load_btn)

        self.export_btn = QPushButton("📤 导出Excel")
        self.export_btn.clicked.connect(self.export_to_excel)
        btn_layout.addWidget(self.export_btn)

        layout.addLayout(btn_layout)

        return panel

    def create_stock_selection_panel(self):
        """创建股票选择面板（上部）"""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 标题栏
        header_layout = QHBoxLayout()

        title = QLabel("📁 股票列表")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(title)

        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.setSpacing(5)
        search_layout.addWidget(QLabel("🔍"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入代码或名称搜索...")
        self.search_edit.textChanged.connect(self.filter_stocks)
        search_layout.addWidget(self.search_edit)

        # 筛选按钮
        self.filter_all_btn = QPushButton("全部")
        self.filter_all_btn.setCheckable(True)
        self.filter_all_btn.setChecked(True)
        self.filter_all_btn.clicked.connect(lambda: self.load_stock_list('all'))
        search_layout.addWidget(self.filter_all_btn)

        self.filter_stock_btn = QPushButton("股票")
        self.filter_stock_btn.setCheckable(True)
        self.filter_stock_btn.clicked.connect(lambda: self.load_stock_list('stock'))
        search_layout.addWidget(self.filter_stock_btn)

        self.filter_bond_btn = QPushButton("债券")
        self.filter_bond_btn.setCheckable(True)
        self.filter_bond_btn.clicked.connect(lambda: self.load_stock_list('bond'))
        search_layout.addWidget(self.filter_bond_btn)

        header_layout.addLayout(search_layout)
        layout.addLayout(header_layout)

        # 股票表格（代替树形控件，更适合上下布局）
        self.stock_table = QTableWidget()
        self.stock_table.setColumnCount(4)
        self.stock_table.setHorizontalHeaderLabels(["股票代码", "类型", "记录数", "日期范围"])
        self.stock_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.stock_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.stock_table.setSortingEnabled(True)
        self.stock_table.itemSelectionChanged.connect(self.on_stock_selection_changed)
        self.stock_table.itemDoubleClicked.connect(self.on_stock_double_clicked)
        layout.addWidget(self.stock_table)

        return panel

    def create_data_table_panel(self):
        """创建数据表格面板（下部 - 重点）"""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 标题栏
        header_layout = QHBoxLayout()

        title = QLabel("📋 详细数据")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(title)

        # 数据统计
        self.data_stats_label = QLabel("共 0 条记录")
        self.data_stats_label.setStyleSheet("color: #808080;")
        header_layout.addWidget(self.data_stats_label)

        header_layout.addStretch()

        layout.addLayout(header_layout)

        # 数据表格（主要组件）
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSortingEnabled(True)
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.setColumnCount(8)
        self.data_table.setHorizontalHeaderLabels([
            "日期", "开盘", "最高", "最低", "收盘", "涨跌幅", "成交量", "成交额"
        ])

        # 设置列宽
        self.data_table.setColumnWidth(0, 100)
        for i in range(1, 5):
            self.data_table.setColumnWidth(i, 80)
        self.data_table.setColumnWidth(5, 70)
        self.data_table.setColumnWidth(6, 100)
        self.data_table.setColumnWidth(7, 100)

        layout.addWidget(self.data_table)

        return panel

    def apply_dark_theme(self):
        """应用深色主题"""
        self.setStyleSheet(DARK_THEME_STYLESHEET)

    def load_initial_data(self):
        """加载初始数据"""
        self.load_stock_list('all')

    def load_stock_list(self, filter_type: str = 'all'):
        """加载股票列表"""
        try:
            # 构建筛选条件
            where_clause = ""
            if filter_type != 'all':
                where_clause = f"WHERE symbol_type = '{filter_type}'"

            if DB_MANAGER_AVAILABLE:
                manager = get_db_manager(r'D:/StockData/stock_data.ddb')

                query = f"""
                    SELECT
                        stock_code,
                        symbol_type,
                        COUNT(*) as count,
                        MIN(date) as min_date,
                        MAX(date) as max_date
                    FROM stock_daily
                    {where_clause}
                    GROUP BY stock_code, symbol_type
                    ORDER BY stock_code
                    LIMIT 1000
                """

                df = manager.execute_read_query(query)
            else:
                con = duckdb.connect(r'D:/StockData/stock_data.ddb', read_only=True)
                df = con.execute(f"""
                    SELECT stock_code, symbol_type, COUNT(*) as count,
                           MIN(date) as min_date, MAX(date) as max_date
                    FROM stock_daily
                    {where_clause}
                    GROUP BY stock_code, symbol_type
                    ORDER BY stock_code
                    LIMIT 1000
                """).fetchdf()
                con.close()

            self.populate_stock_table(df)

        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载股票列表失败: {e}")

    def populate_stock_table(self, df: pd.DataFrame):
        """填充股票表格"""
        self.stock_table.setRowCount(len(df))

        for row_idx, (_, data_row) in enumerate(df.iterrows()):
            # 股票代码
            code_item = QTableWidgetItem(data_row['stock_code'])
            code_item.setFont(QFont("Consolas", 10))
            self.stock_table.setItem(row_idx, 0, code_item)

            # 类型
            type_map = {'stock': '股票', 'bond': '债券', 'etf': 'ETF'}
            type_item = QTableWidgetItem(type_map.get(data_row['symbol_type'], data_row['symbol_type']))
            self.stock_table.setItem(row_idx, 1, type_item)

            # 记录数
            count_item = QTableWidgetItem(f"{data_row['count']:,}")
            count_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.stock_table.setItem(row_idx, 2, count_item)

            # 日期范围
            min_date = str(data_row['min_date'])[:10]
            max_date = str(data_row['max_date'])[:10]
            date_item = QTableWidgetItem(f"{min_date} ~ {max_date}")
            self.stock_table.setItem(row_idx, 3, date_item)

        self.data_stats_label.setText(f"共 {len(df)} 只股票")

    def filter_stocks(self):
        """筛选股票"""
        search_text = self.search_edit.text().upper()

        for row in range(self.stock_table.rowCount()):
            code = self.stock_table.item(row, 0).text()
            match = search_text in code
            self.stock_table.setRowHidden(row, not match)

    def on_stock_selection_changed(self):
        """股票选择改变"""
        selected_items = self.stock_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            stock_code = self.stock_table.item(row, 0).text()
            record_count = self.stock_table.item(row, 2).text()
            self.current_stock = stock_code
            self.stock_label.setText(f"当前股票: {stock_code}")
            self.record_count_label.setText(f"记录数: {record_count}")

    def on_stock_double_clicked(self, item: QTableWidgetItem):
        """双击股票加载数据"""
        self.load_current_stock()

    def on_adjust_changed(self, text: str):
        """复权类型改变"""
        if self.current_stock:
            self.load_current_stock()

    def load_current_stock(self):
        """加载当前股票数据"""
        if not self.current_stock:
            QMessageBox.warning(self, "提示", "请先选择股票")
            return

        start_date = self.start_date_edit.date().toString('yyyy-MM-dd')
        end_date = self.end_date_edit.date().toString('yyyy-MM-dd')

        adjust_map = {"不复权": "none", "前复权": "front", "后复权": "back"}
        adjust_type = adjust_map.get(self.adjust_combo.currentText(), "none")

        self.status_label.setText(f"🔄 正在加载 {self.current_stock} 数据...")
        self.load_btn.setEnabled(False)

        # 在线程中加载数据
        self.load_thread = DataLoadThread(self.current_stock, start_date, end_date, adjust_type)
        self.load_thread.data_ready.connect(self.on_data_loaded)
        self.load_thread.error_occurred.connect(self.on_load_error)
        self.load_thread.start()

    def on_data_loaded(self, df: pd.DataFrame, stock_code: str):
        """数据加载完成"""
        self.current_data = df
        self.load_btn.setEnabled(True)

        if not df.empty:
            # 计算涨跌幅
            df_pct = df.copy()
            df_pct['pct_change'] = df_pct['close'].pct_change() * 100

            # 填充数据表格
            self.data_table.setRowCount(len(df_pct))

            for row_idx, (date, row_data) in enumerate(df_pct.iterrows()):
                # 日期
                date_item = QTableWidgetItem(str(date)[:10])
                self.data_table.setItem(row_idx, 0, date_item)

                # OHLC
                for col_idx, col_name in enumerate(['open', 'high', 'low', 'close'], 1):
                    value = row_data[col_name]
                    item = QTableWidgetItem(f"{value:.2f}")

                    # 涨跌颜色
                    if col_name == 'close':
                        if row_idx > 0:
                            prev_close = df_pct.iloc[row_idx - 1]['close']
                            if value > prev_close:
                                item.setForeground(QColor("#ff6b6b"))  # 红涨
                            elif value < prev_close:
                                item.setForeground(QColor("#4ec9b0"))  # 绿跌

                    self.data_table.setItem(row_idx, col_idx, item)

                # 涨跌幅
                pct_change = row_data['pct_change']
                if pd.notna(pct_change):
                    pct_item = QTableWidgetItem(f"{pct_change:+.2f}%")
                    if pct_change > 0:
                        pct_item.setForeground(QColor("#ff6b6b"))
                    elif pct_change < 0:
                        pct_item.setForeground(QColor("#4ec9b0"))
                    self.data_table.setItem(row_idx, 5, pct_item)
                else:
                    self.data_table.setItem(row_idx, 5, QTableWidgetItem("-"))

                # 成交量
                volume_item = QTableWidgetItem(f"{int(row_data['volume']):,}")
                self.data_table.setItem(row_idx, 6, volume_item)

                # 成交额
                amount = row_data.get('amount', 0)
                if pd.notna(amount) and amount > 0:
                    amount_item = QTableWidgetItem(f"{amount:,.0f}")
                else:
                    amount_item = QTableWidgetItem("-")
                self.data_table.setItem(row_idx, 7, amount_item)

            self.status_label.setText(f"✅ {stock_code} - 已加载 {len(df)} 条记录")
        else:
            self.data_table.setRowCount(0)
            self.status_label.setText(f"⚠️ {stock_code} - 该时间段无数据")

    def on_load_error(self, error_msg: str):
        """加载错误"""
        self.load_btn.setEnabled(True)
        QMessageBox.critical(self, "错误", f"数据加载失败: {error_msg}")
        self.status_label.setText("❌ 加载失败")

    def export_to_excel(self):
        """导出到Excel"""
        if self.data_table.rowCount() == 0:
            QMessageBox.warning(self, "提示", "没有数据可导出")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出Excel",
            f"{self.current_stock or 'stock'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx);;CSV Files (*.csv)"
        )

        if file_path:
            try:
                # 收集表格数据
                data = []
                headers = [self.data_table.horizontalHeaderItem(col).text()
                          for col in range(self.data_table.columnCount())]

                for row in range(self.data_table.rowCount()):
                    row_data = []
                    for col in range(self.data_table.columnCount()):
                        item = self.data_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    data.append(row_data)

                df_export = pd.DataFrame(data, columns=headers)

                if file_path.endswith('.csv'):
                    df_export.to_csv(file_path, index=False, encoding='utf-8-sig')
                else:
                    df_export.to_excel(file_path, index=False)

                QMessageBox.information(self, "成功", f"数据已导出到:\n{file_path}")
                self.status_label.setText(f"✅ 已导出 {len(data)} 条记录")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {e}")


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用Fusion风格配合自定义样式

    viewer = AdvancedDataViewer()
    viewer.resize(1400, 900)
    viewer.setWindowTitle("📊 本地数据查看器 - 专业版")
    viewer.show()
    sys.exit(app.exec_())
