#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级数据查看器组件
符合现有GUI的浅色主题风格
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QDateEdit,
    QFrame, QMessageBox, QFileDialog, QSplitter, QLineEdit,
    QTabWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate, QTimer
from PyQt5.QtGui import QFont, QColor

import pandas as pd

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from data_manager.duckdb_connection_pool import get_db_manager
    from data_manager.financial_data_saver import FinancialDataSaver
    DB_MANAGER_AVAILABLE = True
    FINANCIAL_SAVER_AVAILABLE = True
except ImportError:
    DB_MANAGER_AVAILABLE = False
    FINANCIAL_SAVER_AVAILABLE = False


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
            # 使用统一数据接口（支持QMT API复权方案）
            from data_manager.unified_data_interface import UnifiedDataInterface

            manager = UnifiedDataInterface()

            # 查询数据（只从DuckDB读取，不触发在线获取）
            # local_only=True: 仅显示本地已有数据，避免误解
            df = manager.get_stock_data(
                stock_code=self.stock_code,
                start_date=self.start_date,
                end_date=self.end_date,
                period='1d',
                adjust=self.adjust_type,
                auto_save=False,
                local_only=True  # 只显示本地数据，不在线获取
            )

            if not df.empty:
                # 检查并设置索引
                if 'date' in df.columns:
                    df = df.set_index('date')
                elif 'datetime' in df.columns:
                    df = df.set_index('datetime')
                # 如果没有日期列，保持原样

            self.data_ready.emit(df, self.stock_code)

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            self.error_occurred.emit(f"{str(e)}\n\n{error_detail}")


class AdvancedDataViewerWidget(QWidget):
    """高级数据查看器组件 - 浅色主题风格"""

    def __init__(self):
        super().__init__()
        self.current_stock = None
        self.current_data = None
        self.search_timer = None  # 搜索延迟定时器
        self.data_loaded = False  # 标记数据是否已加载
        self.init_ui()
        # 不在初始化时加载数据，延迟到用户首次访问时加载
        # 这样即使没有DuckDB数据库，GUI也能正常启动

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 控制面板
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)

        # 主分割器（上下分栏）
        main_splitter = QSplitter(Qt.Vertical)

        # 上部：股票选择
        stock_panel = self.create_stock_selection_panel()
        main_splitter.addWidget(stock_panel)

        # 下部：详细数据
        data_panel = self.create_data_table_panel()
        main_splitter.addWidget(data_panel)

        # 设置分割比例（上3下7）
        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 7)

        layout.addWidget(main_splitter)

    def create_control_panel(self):
        """创建控制面板"""
        group = QGroupBox("控制面板")
        layout = QHBoxLayout(group)

        # 左侧：股票信息
        info_layout = QVBoxLayout()
        self.stock_label = QLabel("当前股票: 未选择")
        self.stock_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.stock_label.setStyleSheet("color: #2196F3;")
        info_layout.addWidget(self.stock_label)

        self.record_count_label = QLabel("记录数: 0")
        self.record_count_label.setStyleSheet("color: #757575;")
        info_layout.addWidget(self.record_count_label)

        layout.addLayout(info_layout)

        # 中间：复权和日期
        control_layout = QGridLayout()
        control_layout.setSpacing(8)

        control_layout.addWidget(QLabel("复权类型:"), 0, 0)
        self.adjust_combo = QComboBox()
        self.adjust_combo.addItems(["不复权", "前复权", "后复权", "等比前复权", "等比后复权"])
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

        self.load_btn = QPushButton("📥 加载数据")
        self.load_btn.clicked.connect(self.load_current_stock)
        btn_layout.addWidget(self.load_btn)

        self.export_btn = QPushButton("📤 导出Excel")
        self.export_btn.clicked.connect(self.export_to_excel)
        btn_layout.addWidget(self.export_btn)

        layout.addLayout(btn_layout)

        return group

    def create_stock_selection_panel(self):
        """创建股票选择面板"""
        group = QGroupBox("股票列表")
        layout = QVBoxLayout(group)

        # 搜索和筛选
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("🔍 搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入代码全局搜索（如000001）...")
        self.search_edit.textChanged.connect(self.on_search_text_changed)
        filter_layout.addWidget(self.search_edit)

        self.filter_all_btn = QPushButton("全部")
        self.filter_all_btn.setCheckable(True)
        self.filter_all_btn.setChecked(True)
        self.filter_all_btn.clicked.connect(lambda: self.load_stock_list('all'))
        filter_layout.addWidget(self.filter_all_btn)

        self.filter_stock_btn = QPushButton("股票")
        self.filter_stock_btn.setCheckable(True)
        self.filter_stock_btn.clicked.connect(lambda: self.load_stock_list('stock'))
        filter_layout.addWidget(self.filter_stock_btn)

        self.filter_bond_btn = QPushButton("债券")
        self.filter_bond_btn.setCheckable(True)
        self.filter_bond_btn.clicked.connect(lambda: self.load_stock_list('bond'))
        filter_layout.addWidget(self.filter_bond_btn)

        layout.addLayout(filter_layout)

        # 股票表格
        self.stock_table = QTableWidget()
        self.stock_table.setColumnCount(4)
        self.stock_table.setHorizontalHeaderLabels(["股票代码", "类型", "记录数", "日期范围"])
        self.stock_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.stock_table.setSelectionMode(QTableWidget.SingleSelection)
        self.stock_table.setSortingEnabled(True)
        self.stock_table.setMaximumHeight(250)
        self.stock_table.itemSelectionChanged.connect(self.on_stock_selection_changed)
        self.stock_table.itemDoubleClicked.connect(self.on_stock_double_clicked)
        layout.addWidget(self.stock_table)

        return group

    def create_data_table_panel(self):
        """创建数据表格面板"""
        group = QGroupBox("详细数据")
        layout = QVBoxLayout(group)

        # 标签页切换（行情数据 / 财务数据）
        self.data_tab_widget = QTabWidget()

        # 行情数据标签页
        market_data_widget = QWidget()
        market_layout = QVBoxLayout(market_data_widget)

        # 统计信息
        stats_layout = QHBoxLayout()
        self.data_stats_label = QLabel("共 0 条记录")
        self.data_stats_label.setStyleSheet("color: #757575;")
        stats_layout.addWidget(self.data_stats_label)
        stats_layout.addStretch()
        market_layout.addLayout(stats_layout)

        # 数据表格
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSortingEnabled(True)
        self.data_table.setSelectionBehavior(QTableWidget.SelectRows)
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

        market_layout.addWidget(self.data_table)
        self.data_tab_widget.addTab(market_data_widget, "📈 行情数据")

        # 财务数据标签页
        financial_data_widget = QWidget()
        financial_layout = QVBoxLayout(financial_data_widget)

        # 财务数据统计
        fin_stats_layout = QHBoxLayout()
        self.fin_stats_label = QLabel("点击上方「加载财务数据」按钮查看")
        self.fin_stats_label.setStyleSheet("color: #757575;")
        fin_stats_layout.addWidget(self.fin_stats_label)
        fin_stats_layout.addStretch()
        financial_layout.addLayout(fin_stats_layout)

        # 操作按钮
        fin_btn_layout = QHBoxLayout()
        self.load_fin_btn = QPushButton("💰 加载财务数据")
        self.load_fin_btn.clicked.connect(self.load_financial_data)
        fin_btn_layout.addWidget(self.load_fin_btn)

        fin_btn_layout.addStretch()
        financial_layout.addLayout(fin_btn_layout)

        # 财务数据表格
        self.financial_table = QTableWidget()
        self.financial_table.setAlternatingRowColors(True)
        self.financial_table.setSortingEnabled(True)
        self.financial_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.financial_table.setColumnCount(5)
        self.financial_table.setHorizontalHeaderLabels([
            "报告期", "净资产收益率", "毛利率", "净利率", "资产负债率"
        ])

        # 设置列宽
        self.financial_table.setColumnWidth(0, 100)
        for i in range(1, 5):
            self.financial_table.setColumnWidth(i, 100)

        financial_layout.addWidget(self.financial_table)
        self.data_tab_widget.addTab(financial_data_widget, "💰 财务数据")

        # Tick数据标签页
        tick_data_widget = QWidget()
        tick_layout = QVBoxLayout(tick_data_widget)

        # Tick数据统计
        tick_stats_layout = QHBoxLayout()
        self.tick_stats_label = QLabel("选择日期后点击「加载Tick数据」查看")
        self.tick_stats_label.setStyleSheet("color: #757575;")
        tick_stats_layout.addWidget(self.tick_stats_label)
        tick_stats_layout.addStretch()
        tick_layout.addLayout(tick_stats_layout)

        # Tick数据操作区域
        tick_ctrl_layout = QHBoxLayout()

        tick_ctrl_layout.addWidget(QLabel("选择日期:"))
        self.tick_date_edit = QDateEdit()
        self.tick_date_edit.setCalendarPopup(True)
        self.tick_date_edit.setDate(QDate.currentDate())
        self.tick_date_edit.setDisplayFormat("yyyy-MM-dd")
        tick_ctrl_layout.addWidget(self.tick_date_edit)

        tick_ctrl_layout.addWidget(QLabel("时间段:"))
        self.tick_time_combo = QComboBox()
        self.tick_time_combo.addItems(["全天", "9:15-11:30", "13:00-15:00", "9:30-10:00", "10:00-10:30", "14:00-14:30"])
        tick_ctrl_layout.addWidget(self.tick_time_combo)

        tick_ctrl_layout.addStretch()

        self.load_tick_btn = QPushButton("📊 加载Tick数据")
        self.load_tick_btn.clicked.connect(self.load_tick_data)
        tick_ctrl_layout.addWidget(self.load_tick_btn)

        tick_layout.addLayout(tick_ctrl_layout)

        # Tick数据表格
        self.tick_table = QTableWidget()
        self.tick_table.setAlternatingRowColors(True)
        self.tick_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.tick_table.setColumnCount(7)
        self.tick_table.setHorizontalHeaderLabels([
            "时间", "价格", "成交量", "成交额", "买卖方向", "持仓量", "数据类型"
        ])

        # 设置列宽
        self.tick_table.setColumnWidth(0, 120)
        self.tick_table.setColumnWidth(1, 80)
        self.tick_table.setColumnWidth(2, 100)
        self.tick_table.setColumnWidth(3, 100)
        self.tick_table.setColumnWidth(4, 80)
        self.tick_table.setColumnWidth(5, 100)
        self.tick_table.setColumnWidth(6, 80)

        tick_layout.addWidget(self.tick_table)
        self.data_tab_widget.addTab(tick_data_widget, "📊 Tick数据")

        layout.addWidget(self.data_tab_widget)

        return group

    def load_initial_data(self):
        """加载初始数据"""
        self.load_stock_list('all')

    def load_stock_list(self, filter_type: str = 'all', search_text: str = ''):
        """加载股票列表（支持全局搜索）"""
        try:
            # 检查数据库文件是否存在
            db_path = r'D:/StockData/stock_data.ddb'
            if not os.path.exists(db_path):
                # 数据库不存在，显示友好提示而不是错误
                self.data_stats_label.setText("⚠️ 未找到DuckDB数据库，请先下载数据")
                self.stock_table.setRowCount(0)
                return

            # 构建WHERE子句
            conditions = []

            # 类型筛选
            if filter_type != 'all':
                conditions.append(f"symbol_type = '{filter_type}'")

            # 搜索筛选
            if search_text:
                conditions.append(f"stock_code LIKE '%{search_text}%'")

            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            if DB_MANAGER_AVAILABLE:
                manager = get_db_manager(db_path)

                # 显示所有匹配结果（去掉限制，确保显示所有股票）
                limit_clause = ""

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
                    {limit_clause}
                """

                df = manager.execute_read_query(query)
            else:
                import duckdb
                con = duckdb.connect(db_path, read_only=True)
                df = con.execute(query).fetchdf()
                con.close()

            self.populate_stock_table(df)

            # 显示搜索结果统计
            if search_text:
                self.data_stats_label.setText(f"搜索 '{search_text}': 找到 {len(df)} 只股票")
            else:
                self.data_stats_label.setText(f"共 {len(df)} 只股票")

        except Exception as e:
            # 只在调试时显示详细错误，给用户显示友好提示
            import traceback
            print(f"加载股票列表失败: {e}")
            print(traceback.format_exc())

            # 检查是否是数据库不存在的问题
            if "Cannot open file" in str(e) or "系统找不到指定的路径" in str(e):
                self.data_stats_label.setText("⚠️ 未找到DuckDB数据库，请先下载数据")
                self.stock_table.setRowCount(0)
            else:
                self.data_stats_label.setText(f"⚠️ 加载数据失败: {str(e)}")

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

    def on_search_text_changed(self, text: str):
        """搜索文本改变（使用延迟避免频繁查询）"""
        # 停止之前的定时器
        if self.search_timer:
            self.search_timer.stop()
            self.search_timer = None

        # 如果文本为空，重新加载当前类型的所有股票
        if not text.strip():
            # 获取当前选中的筛选类型
            if self.filter_all_btn.isChecked():
                filter_type = 'all'
            elif self.filter_stock_btn.isChecked():
                filter_type = 'stock'
            elif self.filter_bond_btn.isChecked():
                filter_type = 'bond'
            else:
                filter_type = 'all'

            self.load_stock_list(filter_type, '')
            return

        # 延迟500ms后再搜索，避免输入时频繁查询
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(lambda: self.perform_global_search(text))
        self.search_timer.start(500)

    def perform_global_search(self, search_text: str):
        """执行全局搜索"""
        search_text = search_text.strip().upper()

        if not search_text:
            return

        # 获取当前选中的筛选类型
        if self.filter_all_btn.isChecked():
            filter_type = 'all'
        elif self.filter_stock_btn.isChecked():
            filter_type = 'stock'
        elif self.filter_bond_btn.isChecked():
            filter_type = 'bond'
        else:
            filter_type = 'all'

        # 执行搜索
        self.load_stock_list(filter_type, search_text)

    def filter_stocks(self):
        """筛选股票（保留用于兼容性，现在由全局搜索替代）"""
        pass

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

        adjust_map = {"不复权": "none", "前复权": "front", "后复权": "back", "等比前复权": "geometric_front", "等比后复权": "geometric_back"}
        adjust_type = adjust_map.get(self.adjust_combo.currentText(), "none")

        self.load_btn.setEnabled(False)
        self.load_btn.setText("加载中...")

        # 在线程中加载数据
        self.load_thread = DataLoadThread(self.current_stock, start_date, end_date, adjust_type)
        self.load_thread.data_ready.connect(self.on_data_loaded)
        self.load_thread.error_occurred.connect(self.on_load_error)
        self.load_thread.start()

    def on_data_loaded(self, df: pd.DataFrame, stock_code: str):
        """数据加载完成"""
        self.current_data = df
        self.load_btn.setEnabled(True)
        self.load_btn.setText("📥 加载数据")

        if not df.empty:
            # 计算涨跌幅（date此时是索引）
            df_pct = df.copy()
            df_pct['pct_change'] = df_pct['close'].pct_change() * 100

            # 重置索引，确保date是列而不是索引
            df_pct = df_pct.reset_index()

            # 如果索引没有名字，手动命名为'date'
            if 'index' in df_pct.columns:
                df_pct = df_pct.rename(columns={'index': 'date'})

            # 倒序排列：最新的数据在上面
            df_pct = df_pct.iloc[::-1].reset_index(drop=True)

            # 填充数据表格
            self.data_table.setRowCount(len(df_pct))

            # 刷新股票列表（显示最新的日期范围）
            # 获取当前选中的筛选类型
            if self.filter_all_btn.isChecked():
                filter_type = 'all'
            elif self.filter_stock_btn.isChecked():
                filter_type = 'stock'
            elif self.filter_bond_btn.isChecked():
                filter_type = 'bond'
            else:
                filter_type = 'all'

            # 重新加载股票列表
            self.load_stock_list(filter_type, '')

            # 使用 iloc 直接访问，避免 iterrows 的潜在问题
            for row_idx in range(len(df_pct)):
                # 日期
                date = df_pct.iloc[row_idx]['date']

                # 日期格式化
                if isinstance(date, pd.Timestamp):
                    date_str = date.strftime('%Y-%m-%d')
                elif isinstance(date, pd.datetime64):
                    date_str = pd.Timestamp(date).strftime('%Y-%m-%d')
                elif hasattr(date, 'strftime'):
                    date_str = date.strftime('%Y-%m-%d')
                else:
                    # 如果是字符串，直接使用
                    date_str = str(date)
                    # 如果是整数时间戳，转换
                    if date_str.isdigit() and len(date_str) > 10:
                        from datetime import datetime as dt
                        date_ts = int(date_str) / 1000  # 毫秒转秒
                        date_str = dt.fromtimestamp(date_ts).strftime('%Y-%m-%d')

                date_item = QTableWidgetItem(date_str)
                self.data_table.setItem(row_idx, 0, date_item)

                # OHLC
                for col_idx, col_name in enumerate(['open', 'high', 'low', 'close'], 1):
                    value = df_pct.iloc[row_idx][col_name]
                    item = QTableWidgetItem(f"{value:.2f}")

                    # 涨跌颜色（红涨绿跌）
                    if col_name == 'close':
                        if row_idx < len(df_pct) - 1:
                            prev_close = df_pct.iloc[row_idx + 1]['close']
                            if value > prev_close:
                                item.setForeground(QColor("#f44336"))  # 红涨
                            elif value < prev_close:
                                item.setForeground(QColor("#4CAF50"))  # 绿跌

                    self.data_table.setItem(row_idx, col_idx, item)

                # 涨跌幅
                pct_change = df_pct.iloc[row_idx]['pct_change']
                if pd.notna(pct_change):
                    pct_item = QTableWidgetItem(f"{pct_change:+.2f}%")
                    if pct_change > 0:
                        pct_item.setForeground(QColor("#f44336"))
                    elif pct_change < 0:
                        pct_item.setForeground(QColor("#4CAF50"))
                    self.data_table.setItem(row_idx, 5, pct_item)
                else:
                    self.data_table.setItem(row_idx, 5, QTableWidgetItem("-"))

                # 成交量
                volume_item = QTableWidgetItem(f"{int(df_pct.iloc[row_idx]['volume']):,}")
                self.data_table.setItem(row_idx, 6, volume_item)

                # 成交额
                amount = df_pct.iloc[row_idx].get('amount', 0)
                if pd.notna(amount) and amount > 0:
                    amount_item = QTableWidgetItem(f"{amount:,.0f}")
                else:
                    amount_item = QTableWidgetItem("-")
                self.data_table.setItem(row_idx, 7, amount_item)

            self.data_stats_label.setText(f"共 {len(df)} 条记录 - {stock_code}")
        else:
            self.data_table.setRowCount(0)
            self.data_stats_label.setText(f"{stock_code} 该时间段无数据")

    def on_load_error(self, error_msg: str):
        """加载错误"""
        self.load_btn.setEnabled(True)
        self.load_btn.setText("📥 加载数据")
        QMessageBox.critical(self, "错误", f"数据加载失败: {error_msg}")

    def load_financial_data(self):
        """加载财务数据"""
        if not self.current_stock:
            QMessageBox.warning(self, "提示", "请先选择股票")
            return

        self.load_fin_btn.setEnabled(False)
        self.load_fin_btn.setText("加载中...")

        # 使用线程加载财务数据（传递完整股票代码）
        self.fin_thread = FinancialDataLoadThread(self.current_stock)
        self.fin_thread.data_ready.connect(self.on_financial_data_loaded)
        self.fin_thread.error_occurred.connect(self.on_financial_load_error)
        self.fin_thread.start()

    def on_financial_data_loaded(self, df: pd.DataFrame):
        """财务数据加载完成"""
        self.load_fin_btn.setEnabled(True)
        self.load_fin_btn.setText("💰 加载财务数据")

        if not df.empty:
            # 填充财务数据表格
            self.financial_table.setRowCount(len(df))

            for row_idx, (_, row_data) in enumerate(df.iterrows()):
                # 报告期
                report_value = row_data.get('报告期', '')
                report_item = QTableWidgetItem(str(report_value)[:10])
                self.financial_table.setItem(row_idx, 0, report_item)

                # 财务指标
                for col_idx, (key, format_fn) in enumerate([
                    ('净资产收益率', lambda x: f"{x:.2f}%" if pd.notna(x) else "-"),
                    ('毛利率', lambda x: f"{x:.2f}%" if pd.notna(x) else "-"),
                    ('净利率', lambda x: f"{x:.2f}%" if pd.notna(x) else "-"),
                    ('资产负债率', lambda x: f"{x:.2f}%" if pd.notna(x) else "-"),
                ], 1):
                    value = row_data.get(key)
                    if pd.notna(value):
                        item = QTableWidgetItem(format_fn(value))
                        # 根据指标好坏着色
                        if key == '净资产收益率':
                            if value > 15:
                                item.setForeground(QColor("#4CAF50"))  # 好 - 绿
                            elif value < 5:
                                item.setForeground(QColor("#f44336"))  # 差 - 红
                        elif key == '资产负债率':
                            if value > 70:
                                item.setForeground(QColor("#f44336"))  # 高风险 - 红
                            elif value < 30:
                                item.setForeground(QColor("#4CAF50"))  # 低风险 - 绿
                    else:
                        item = QTableWidgetItem("-")
                    self.financial_table.setItem(row_idx, col_idx, item)

            self.fin_stats_label.setText(f"共 {len(df)} 期财务数据")
        else:
            self.financial_table.setRowCount(0)
            self.fin_stats_label.setText("该股票暂无财务数据")

    def load_tick_data(self):
        """加载Tick数据"""
        if not self.current_stock:
            QMessageBox.warning(self, "提示", "请先选择股票")
            return

        tick_date = self.tick_date_edit.date().toString('yyyy-MM-dd')
        time_range = self.tick_time_combo.currentText()

        self.load_tick_btn.setEnabled(False)
        self.load_tick_btn.setText("加载中...")

        # 使用线程加载tick数据
        self.tick_thread = TickDataLoadThread(self.current_stock, tick_date, time_range)
        self.tick_thread.data_ready.connect(self.on_tick_data_loaded)
        self.tick_thread.error_occurred.connect(self.on_tick_load_error)
        self.tick_thread.start()

    def on_tick_data_loaded(self, df: pd.DataFrame):
        """Tick数据加载完成"""
        self.load_tick_btn.setEnabled(True)
        self.load_tick_btn.setText("📊 加载Tick数据")

        if not df.empty:
            # 填充tick数据表格
            self.tick_table.setRowCount(len(df))

            for row_idx, (_, row_data) in enumerate(df.iterrows()):
                # 时间
                time_value = row_data.get('datetime', row_data.get('time', ''))
                if isinstance(time_value, pd.Timestamp):
                    time_str = time_value.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                else:
                    time_str = str(time_value)
                time_item = QTableWidgetItem(time_str)
                self.tick_table.setItem(row_idx, 0, time_item)

                # 价格
                price = row_data.get('lastPrice', row_data.get('price', 0))
                price_item = QTableWidgetItem(f"{price:.2f}" if pd.notna(price) else "-")
                self.tick_table.setItem(row_idx, 1, price_item)

                # 成交量
                volume = row_data.get('volume', row_data.get('vol', 0))
                if pd.notna(volume) and volume > 0:
                    volume_item = QTableWidgetItem(f"{int(volume):,}")
                else:
                    volume_item = QTableWidgetItem("-")
                self.tick_table.setItem(row_idx, 2, volume_item)

                # 成交额
                amount = row_data.get('amount', row_data.get('money', 0))
                if pd.notna(amount) and amount > 0:
                    amount_item = QTableWidgetItem(f"{amount:,.0f}")
                else:
                    amount_item = QTableWidgetItem("-")
                self.tick_table.setItem(row_idx, 3, amount_item)

                # 买卖方向
                bid_ask = row_data.get('func_type', row_data.get('type', ''))
                if bid_ask == 1:
                    bid_ask_str = "买入"
                    bid_ask_item.setForeground(QColor("#f44336"))
                elif bid_ask == 2:
                    bid_ask_str = "卖出"
                    bid_ask_item.setForeground(QColor("#4CAF50"))
                else:
                    bid_ask_str = "-"
                bid_ask_item = QTableWidgetItem(bid_ask_str)
                self.tick_table.setItem(row_idx, 4, bid_ask_item)

                # 持仓量
                open_interest = row_data.get('openInt', row_data.get('oi', 0))
                if pd.notna(open_interest) and open_interest > 0:
                    oi_item = QTableWidgetItem(f"{int(open_interest):,}")
                else:
                    oi_item = QTableWidgetItem("-")
                self.tick_table.setItem(row_idx, 5, oi_item)

                # 数据类型
                data_type = row_data.get('data_type', 'tick')
                type_item = QTableWidgetItem("Tick")
                self.tick_table.setItem(row_idx, 6, type_item)

            self.tick_stats_label.setText(f"共 {len(df)} 条Tick数据")
        else:
            self.tick_table.setRowCount(0)
            self.tick_stats_label.setText("该日期暂无Tick数据")

    def on_tick_load_error(self, error_msg: str):
        """Tick数据加载错误"""
        self.load_tick_btn.setEnabled(True)
        self.load_tick_btn.setText("📊 加载Tick数据")
        QMessageBox.warning(self, "提示", f"Tick数据加载失败\n\n{error_msg}")

    def on_financial_load_error(self, error_msg: str):
        """财务数据加载错误"""
        self.load_fin_btn.setEnabled(True)
        self.load_fin_btn.setText("💰 加载财务数据")
        QMessageBox.warning(self, "提示", f"财务数据加载失败\n\n{error_msg}\n\n数据来源: QMT迅投xtdata接口")

    def export_to_excel(self):
        """导出到Excel"""
        current_tab = self.data_tab_widget.currentIndex()

        if current_tab == 0:
            # 导出行情数据
            table = self.data_table
            prefix = "market"
        else:
            # 导出财务数据
            table = self.financial_table
            prefix = "financial"

        if table.rowCount() == 0:
            QMessageBox.warning(self, "提示", "没有数据可导出")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出Excel",
            f"{self.current_stock or 'stock'}_{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx);;CSV Files (*.csv)"
        )

        if file_path:
            try:
                # 收集表格数据
                data = []
                headers = [table.horizontalHeaderItem(col).text()
                          for col in range(table.columnCount())]

                for row in range(table.rowCount()):
                    row_data = []
                    for col in range(table.columnCount()):
                        item = table.item(row, col)
                        row_data.append(item.text() if item else "")
                    data.append(row_data)

                df_export = pd.DataFrame(data, columns=headers)

                if file_path.endswith('.csv'):
                    df_export.to_csv(file_path, index=False, encoding='utf-8-sig')
                else:
                    df_export.to_excel(file_path, index=False)

                QMessageBox.information(self, "成功", f"数据已导出到:\n{file_path}")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {e}")


class FinancialDataLoadThread(QThread):
    """财务数据加载线程 - 使用QMT数据源"""
    data_ready = pyqtSignal(pd.DataFrame)
    error_occurred = pyqtSignal(str)

    def __init__(self, stock_code: str):
        super().__init__()
        self.stock_code = stock_code

    def run(self):
        try:
            # 尝试从QMT获取财务数据
            try:
                from xtquant import xtdata
            except ImportError:
                self.error_occurred.emit("QMT xtdata 不可用")
                return

            # 获取财务数据（使用QMT接口）
            try:
                # 获取资产负债表、利润表、现金流量表
                tables = ['Balance', 'Income', 'CashFlow']

                # 使用动态结束日期（当前日期）
                from datetime import datetime
                end_date = datetime.now().strftime('%Y%m%d')

                result = xtdata.get_financial_data(
                    stock_list=[self.stock_code],
                    table_list=tables,
                    start_time="20200101",
                    end_time=end_date,
                    report_type='report_time'
                )

                if not isinstance(result, dict):
                    self.error_occurred.emit(f"QMT返回数据格式错误: 期望dict, 实际{type(result)}")
                    return

                if self.stock_code not in result:
                    self.error_occurred.emit(f"QMT返回数据中不包含股票: {self.stock_code}")
                    return

                stock_data = result[self.stock_code]

                # 检查是否有利润表数据
                if 'Income' not in stock_data:
                    self.error_occurred.emit("QMT返回数据中不包含利润表(Income)")
                    return

                income_df = stock_data['Income']

                # 检查Income是否为DataFrame
                if not isinstance(income_df, pd.DataFrame):
                    self.error_occurred.emit(f"利润表数据格式错误: 期望DataFrame, 实际{type(income_df)}")
                    return

                if income_df.empty:
                    self.error_occurred.emit("利润表数据为空")
                    return

                # 获取资产负债表数据（用于计算资产负债率）
                balance_df = stock_data.get('Balance', pd.DataFrame())

                # 提取并计算财务指标
                # QMT列名映射：
                # m_timetag -> 报告期时间戳
                # net_profit_incl_min_int_inc -> 归属母公司所有者的净利润
                # revenue -> 营业收入
                # total_operating_cost -> 营业总成本
                # tot_assets -> 总资产
                # tot_liab -> 总负债

                records = []

                for idx, row in income_df.iterrows():
                    # 获取报告期时间戳并转换为日期字符串
                    timetag = row.get('m_timetag')
                    if pd.isna(timetag):
                        continue

                    # 将时间戳转换为日期字符串 (格式: YYYYMMDD -> YYYY-MM-DD)
                    if isinstance(timetag, (int, float)):
                        report_date = str(int(timetag))
                        if len(report_date) == 8:
                            report_date_formatted = f"{report_date[0:4]}-{report_date[4:6]}-{report_date[6:8]}"
                        else:
                            report_date_formatted = report_date
                    else:
                        report_date_formatted = str(timetag)[:10]

                    # 提取净利润（万元）
                    net_profit = row.get('net_profit_incl_min_int_inc', 0)
                    if pd.isna(net_profit):
                        net_profit = 0

                    # 提取营业收入（万元）
                    revenue = row.get('revenue', 0)
                    if pd.isna(revenue):
                        revenue = 0
                    # 如果revenue为0，尝试operating_revenue
                    if revenue == 0:
                        revenue = row.get('operating_revenue', 0)
                        if pd.isna(revenue):
                            revenue = 0

                    # 提取营业成本（万元）
                    cost = row.get('total_operating_cost', 0)
                    if pd.isna(cost):
                        cost = 0

                    # 计算净利率 (%)
                    net_margin = (net_profit / revenue * 100) if revenue > 0 else 0

                    # 计算毛利率 (%)
                    gross_margin = ((revenue - cost) / revenue * 100) if revenue > 0 else 0

                    # 尝试从资产负债表获取数据计算ROE和资产负债率
                    roe = 0
                    debt_ratio = 0

                    if isinstance(balance_df, pd.DataFrame) and not balance_df.empty:
                        # 查找同一报告期的资产负债表数据
                        balance_row = balance_df[balance_df['m_timetag'] == timetag]
                        if not balance_row.empty:
                            bal_row = balance_row.iloc[0]

                            # 总资产（万元）
                            total_assets = bal_row.get('tot_assets', 0)
                            if pd.isna(total_assets):
                                total_assets = 0

                            # 总负债（万元）
                            total_liabilities = bal_row.get('tot_liab', 0)
                            if pd.isna(total_liabilities):
                                total_liabilities = 0

                            # 股东权益（万元）
                            total_equity = bal_row.get('total_equity', 0)
                            if pd.isna(total_equity):
                                total_equity = 0

                            # 如果股东权益为0，尝试用总资产减总负债计算
                            if total_equity == 0 and total_assets > 0:
                                total_equity = total_assets - total_liabilities

                            # 计算净资产收益率ROE (%)
                            if total_equity > 0:
                                roe = (net_profit / total_equity * 100)

                            # 计算资产负债率 (%)
                            if total_assets > 0:
                                debt_ratio = (total_liabilities / total_assets * 100)

                    records.append({
                        '报告期': report_date_formatted,
                        '净资产收益率': roe,
                        '毛利率': gross_margin,
                        '净利率': net_margin,
                        '资产负债率': debt_ratio
                    })

                if records:
                    df = pd.DataFrame(records)
                    # 按报告期降序排列（最新的在前面）
                    df = df.sort_values('报告期', ascending=False)
                    self.data_ready.emit(df)
                else:
                    self.error_occurred.emit("无法从QMT财务数据中提取有效记录")

            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                self.error_occurred.emit(f"从QMT获取财务数据失败: {str(e)}\n\n详细信息:\n{error_detail}")

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            self.error_occurred.emit(f"发生错误: {str(e)}\n\n详细信息:\n{error_detail}")


class FinancialDataSaveThread(QThread):
    """财务数据保存线程 - 保存QMT数据到DuckDB"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str, int)  # message, percentage
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, stock_code: str):
        super().__init__()
        self.stock_code = stock_code

    def run(self):
        """运行保存任务"""
        try:
            self.log_signal.emit(f"开始保存 {self.stock_code} 的财务数据到DuckDB...")
            self.progress_signal.emit("连接数据库...", 10)

            # 获取数据库管理器
            if not DB_MANAGER_AVAILABLE:
                self.error_signal.emit("数据库管理器不可用")
                return

            manager = get_db_manager(r'D:/StockData/stock_data.ddb')

            # 创建财务数据保存器
            if not FINANCIAL_SAVER_AVAILABLE:
                self.error_signal.emit("财务数据保存器不可用")
                return

            saver = FinancialDataSaver(manager)

            self.progress_signal.emit("从QMT获取数据...", 30)

            # 从QMT获取财务数据
            from xtquant import xtdata

            tables = ['Balance', 'Income', 'CashFlow']
            result = xtdata.get_financial_data(
                stock_list=[self.stock_code],
                table_list=tables,
                start_time="20200101",
                end_time="20260130",
                report_type='report_time'
            )

            if not isinstance(result, dict) or self.stock_code not in result:
                self.error_signal.emit(f"QMT返回数据格式错误")
                return

            stock_data = result[self.stock_code]

            self.progress_signal.emit("准备数据...", 50)

            # 提取各个表的数据
            income_df = stock_data.get('Income')
            if not isinstance(income_df, pd.DataFrame):
                income_df = pd.DataFrame()
            balance_df = stock_data.get('Balance')
            if not isinstance(balance_df, pd.DataFrame):
                balance_df = pd.DataFrame()
            cashflow_df = stock_data.get('CashFlow')
            if not isinstance(cashflow_df, pd.DataFrame):
                cashflow_df = pd.DataFrame()

            self.progress_signal.emit("保存到DuckDB...", 70)

            # 保存到DuckDB
            save_result = saver.save_from_qmt(
                self.stock_code,
                income_df,
                balance_df,
                cashflow_df
            )

            self.progress_signal.emit("完成...", 100)

            if save_result['success']:
                summary = f"""
财务数据保存成功！

股票代码: {save_result['stock_code']}
- 利润表: {save_result['income_count']} 条记录
- 资产负债表: {save_result['balance_count']} 条记录
- 现金流量表: {save_result['cashflow_count']} 条记录
"""
                self.log_signal.emit(summary)
                self.finished_signal.emit(save_result)
            else:
                self.error_signal.emit(f"保存失败: {save_result.get('error', '未知错误')}")

        except ImportError:
            self.error_signal.emit("无法导入xtquant，请确保QMT已安装并运行")
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            self.error_signal.emit(f"保存失败: {str(e)}\n\n详细信息:\n{error_detail}")


class BatchFinancialSaveThread(QThread):
    """批量保存财务数据线程"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str, int, int)  # message, current, total
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, stock_list: list):
        super().__init__()
        self.stock_list = stock_list
        self._is_running = True

    def run(self):
        """批量保存财务数据"""
        try:
            if not DB_MANAGER_AVAILABLE or not FINANCIAL_SAVER_AVAILABLE:
                self.error_signal.emit("数据库模块不可用")
                return

            manager = get_db_manager(r'D:/StockData/stock_data.ddb')
            saver = FinancialDataSaver(manager)

            from xtquant import xtdata

            total = len(self.stock_list)
            success_count = 0
            failed_count = 0
            failed_list = []

            self.log_signal.emit(f"开始批量保存 {total} 只股票的财务数据...")
            self.log_signal.emit("=" * 60)

            for idx, stock_code in enumerate(self.stock_list):
                if not self._is_running:
                    self.log_signal.emit("\n用户中断操作")
                    break

                current = idx + 1
                self.progress_signal.emit(f"正在处理 {stock_code}...", current, total)

                try:
                    # 获取财务数据
                    tables = ['Balance', 'Income', 'CashFlow']
                    result = xtdata.get_financial_data(
                        stock_list=[stock_code],
                        table_list=tables,
                        start_time="20200101",
                        end_time="20260130",
                        report_type='report_time'
                    )

                    if isinstance(result, dict) and stock_code in result:
                        stock_data = result[stock_code]

                        # 确保stock_data是字典类型
                        if not isinstance(stock_data, dict):
                            self.log_signal.emit(
                                f"[{current}/{total}] {stock_code}: 数据格式错误（预期字典，实际类型：{type(stock_data).__name__}）"
                            )
                            failed_count += 1
                            failed_list.append(stock_code)
                            continue

                        # 安全获取财务数据，确保返回DataFrame
                        income_df = stock_data.get('Income')
                        if not isinstance(income_df, pd.DataFrame):
                            income_df = pd.DataFrame()
                        balance_df = stock_data.get('Balance')
                        if not isinstance(balance_df, pd.DataFrame):
                            balance_df = pd.DataFrame()
                        cashflow_df = stock_data.get('CashFlow')
                        if not isinstance(cashflow_df, pd.DataFrame):
                            cashflow_df = pd.DataFrame()

                        # 保存到DuckDB
                        save_result = saver.save_from_qmt(
                            stock_code,
                            income_df,
                            balance_df,
                            cashflow_df
                        )

                        if save_result['success']:
                            total_records = (save_result['income_count'] +
                                          save_result['balance_count'] +
                                          save_result['cashflow_count'])
                            self.log_signal.emit(
                                f"[{current}/{total}] {stock_code}: OK ({total_records}条记录)"
                            )
                            success_count += 1
                        else:
                            self.log_signal.emit(
                                f"[{current}/{total}] {stock_code}: 失败 - {save_result.get('error', '')}"
                            )
                            failed_count += 1
                            failed_list.append(stock_code)
                    else:
                        self.log_signal.emit(f"[{current}/{total}] {stock_code}: 无数据（可能是ETF/指数）")
                        failed_count += 1

                except Exception as e:
                    self.log_signal.emit(f"[{current}/{total}] {stock_code}: 异常 - {str(e)}")
                    failed_count += 1
                    failed_list.append(stock_code)

            # 输出汇总
            self.log_signal.emit("\n" + "=" * 60)
            self.log_signal.emit("批量保存完成！")
            self.log_signal.emit(f"总计: {total} 只股票")
            self.log_signal.emit(f"成功: {success_count} 只")
            self.log_signal.emit(f"失败: {failed_count} 只")

            if failed_list:
                self.log_signal.emit(f"\n失败的股票: {', '.join(failed_list[:10])}")
                if len(failed_list) > 10:
                    self.log_signal.emit(f"  ... 还有 {len(failed_list) - 10} 只")

            self.finished_signal.emit({
                'total': total,
                'success': success_count,
                'failed': failed_count,
                'failed_list': failed_list
            })

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            self.error_signal.emit(f"批量保存失败: {str(e)}\n\n{error_detail}")

    def stop(self):
        """停止保存"""
        self._is_running = False


class TickDataLoadThread(QThread):
    """Tick数据加载线程"""
    data_ready = pyqtSignal(pd.DataFrame)
    error_occurred = pyqtSignal(str)

    def __init__(self, stock_code: str, tick_date: str, time_range: str):
        super().__init__()
        self.stock_code = stock_code
        self.tick_date = tick_date
        self.time_range = time_range

    def run(self):
        try:
            # 首先尝试从DuckDB加载tick数据
            if DB_MANAGER_AVAILABLE:
                manager = get_db_manager(r'D:/StockData/stock_data.ddb')

                # 解析日期
                date_obj = datetime.strptime(self.tick_date, '%Y-%m-%d')

                # 构建时间范围过滤
                time_filter = ""
                if self.time_range == "9:15-11:30":
                    time_filter = "AND EXTRACT(HOUR FROM datetime) >= 9 AND EXTRACT(HOUR FROM datetime) < 12"
                elif self.time_range == "13:00-15:00":
                    time_filter = "AND EXTRACT(HOUR FROM datetime) >= 13 AND EXTRACT(HOUR FROM datetime) < 15"
                elif self.time_range == "9:30-10:00":
                    time_filter = "AND (EXTRACT(HOUR FROM datetime) = 9 AND EXTRACT(MINUTE FROM datetime) >= 30) OR (EXTRACT(HOUR FROM datetime) = 10 AND EXTRACT(MINUTE FROM datetime) < 30)"
                elif self.time_range == "10:00-10:30":
                    time_filter = "AND EXTRACT(HOUR FROM datetime) = 10 AND EXTRACT(MINUTE FROM datetime) >= 0 AND EXTRACT(MINUTE FROM datetime) < 30"
                elif self.time_range == "14:00-14:30":
                    time_filter = "AND EXTRACT(HOUR FROM datetime) = 14 AND EXTRACT(MINUTE FROM datetime) >= 0 AND EXTRACT(MINUTE FROM datetime) < 30"

                # 尝试从stock_tick表查询
                query = f"""
                    SELECT
                        datetime,
                        lastPrice as price,
                        volume,
                        amount,
                        func_type as type,
                        openInt as oi,
                        'tick' as data_type
                    FROM stock_tick
                    WHERE stock_code = '{self.stock_code}'
                      AND DATE_TRUNC('day', datetime) = '{self.tick_date}'
                      {time_filter}
                    ORDER BY datetime
                    LIMIT 50000
                """

                df = manager.execute_read_query(query)

                if not df.empty:
                    self.data_ready.emit(df)
                    return
                else:
                    # 如果DuckDB中没有数据，尝试从QMT实时获取
                    pass
            else:
                # 如果数据库不可用，尝试从QMT获取
                pass

            # 尝试从QMT获取tick数据
            try:
                from xtquant import xtdata

                # 转换日期格式
                date_str = datetime.strptime(self.tick_date, '%Y-%m-%d').strftime('%Y%m%d')

                # 获取tick数据
                tick_data = xtdata.get_market_data_ex(
                    stock_list=[self.stock_code],
                    period='tick',
                    start_time=date_str,
                    end_time=date_str
                )

                if isinstance(tick_data, dict) and self.stock_code in tick_data:
                    df = tick_data[self.stock_code]

                    if not df.empty:
                        # 添加数据类型标记
                        df['data_type'] = 'tick'

                        # 应用时间范围过滤
                        if self.time_range != "全天":
                            df['datetime'] = pd.to_datetime(df['time'], unit='ms')

                            if self.time_range == "9:15-11:30":
                                df = df[(df['datetime'].dt.hour >= 9) & (df['datetime'].dt.hour < 12)]
                            elif self.time_range == "13:00-15:00":
                                df = df[(df['datetime'].dt.hour >= 13) & (df['datetime'].dt.hour < 15)]
                            elif self.time_range == "9:30-10:00":
                                df = df[((df['datetime'].dt.hour == 9) & (df['datetime'].dt.minute >= 30)) |
                                       ((df['datetime'].dt.hour == 10) & (df['datetime'].dt.minute < 30))]
                            elif self.time_range == "10:00-10:30":
                                df = df[(df['datetime'].dt.hour == 10) & (df['datetime'].dt.minute >= 0) & (df['datetime'].dt.minute < 30)]
                            elif self.time_range == "14:00-14:30":
                                df = df[(df['datetime'].dt.hour == 14) & (df['datetime'].dt.minute >= 0) & (df['datetime'].dt.minute < 30)]

                        # 限制返回的行数
                        if len(df) > 50000:
                            df = df.head(50000)

                        self.data_ready.emit(df)
                        return

            except ImportError:
                self.error_occurred.emit("QMT xtdata不可用，且数据库中无tick数据")
                return
            except Exception as e:
                import traceback
                self.error_occurred.emit(f"从QMT获取tick数据失败: {str(e)}")
                return

            # 如果没有任何数据
            self.error_occurred.emit(f"{self.tick_date} 无tick数据，请先在「数据管理」中下载")

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            self.error_occurred.emit(f"加载tick数据出错: {str(e)}\n\n{error_detail}")
