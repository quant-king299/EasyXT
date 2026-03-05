#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
511380.SH 网格策略回测GUI
提供可视化的参数配置、回测执行和结果展示
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox,
    QProgressBar, QSplitter, QFrame, QMessageBox,
    QDateEdit, QFileDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt5.QtGui import QFont, QColor

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "strategies"))

try:
    from strategies.grid_strategy_511380 import GridBacktester, GridParameterOptimizer
    from data_manager import LocalDataManager
    GRID_STRATEGY_AVAILABLE = True
except ImportError as e:
    GRID_STRATEGY_AVAILABLE = False
    print(f"[ERROR] 网格策略模块导入失败: {e}")


class GridBacktestWorker(QThread):
    """网格回测工作线程"""

    progress_updated = pyqtSignal(int, str)
    backtest_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        """执行回测"""
        try:
            self.progress_updated.emit(10, "初始化回测引擎...")

            backtester = GridBacktester(
                initial_cash=self.params['initial_cash'],
                commission=self.params['commission']
            )

            self.progress_updated.emit(30, "运行回测...")

            # 获取策略模式
            strategy_mode = self.params.get('strategy_mode', 'fixed')

            # 根据策略模式传递不同的参数
            if strategy_mode == 'fixed':
                result = backtester.run_backtest(
                    stock_code=self.params['stock_code'],
                    start_date=self.params['start_date'],
                    end_date=self.params['end_date'],
                    grid_count=self.params['grid_count'],
                    price_range=self.params['price_range'],
                    position_size=self.params['position_size'],
                    base_price=self.params.get('base_price') or None,
                    enable_trailing=self.params['enable_trailing'],
                    data_period=self.params.get('data_period', '1m'),
                    strategy_mode='fixed'
                )

            elif strategy_mode == 'adaptive':
                result = backtester.run_backtest(
                    stock_code=self.params['stock_code'],
                    start_date=self.params['start_date'],
                    end_date=self.params['end_date'],
                    buy_threshold=self.params['buy_threshold'],
                    sell_threshold=self.params['sell_threshold'],
                    position_size=self.params['position_size'],
                    base_price=self.params.get('base_price') or None,
                    data_period=self.params.get('data_period', '1m'),
                    strategy_mode='adaptive'
                )

            elif strategy_mode == 'atr':
                result = backtester.run_backtest(
                    stock_code=self.params['stock_code'],
                    start_date=self.params['start_date'],
                    end_date=self.params['end_date'],
                    atr_period=self.params['atr_period'],
                    atr_multiplier=self.params['atr_multiplier'],
                    position_size=self.params['position_size'],
                    base_price=self.params.get('base_price') or None,
                    data_period=self.params.get('data_period', '1m'),
                    strategy_mode='atr'
                )

            self.progress_updated.emit(100, "回测完成")
            self.backtest_completed.emit(result)

        except Exception as e:
            import traceback
            error_msg = f"回测失败: {str(e)}\n{traceback.format_exc()}"
            self.error_occurred.emit(error_msg)


class GridOptimizationWorker(QThread):
    """参数优化工作线程"""

    progress_updated = pyqtSignal(int, str)
    optimization_completed = pyqtSignal(pd.DataFrame)
    error_occurred = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        """执行参数优化"""
        try:
            self.progress_updated.emit(5, "初始化优化器...")

            backtester = GridBacktester(
                initial_cash=self.params['initial_cash'],
                commission=self.params['commission']
            )

            optimizer = GridParameterOptimizer(backtester)

            self.progress_updated.emit(10, "开始网格搜索...")

            # 构建参数网格
            param_grid = {
                'grid_count': list(range(
                    self.params['grid_count_min'],
                    self.params['grid_count_max'] + 1,
                    self.params['grid_count_step']
                )),
                'price_range': [
                    x / 100 for x in range(
                        self.params['price_range_min'],
                        self.params['price_range_max'] + 1,
                        self.params['price_range_step']
                    )
                ]
            }

            # 添加position_size到优化参数（如果需要）
            if self.params.get('optimize_position_size'):
                param_grid['position_size'] = [
                    x for x in range(
                        self.params['position_size_min'],
                        self.params['position_size_max'] + 1,
                        self.params['position_size_step']
                    )
                ]

            self.progress_updated.emit(20, "执行参数回测...")

            results_df = optimizer.grid_search(
                stock_code=self.params['stock_code'],
                start_date=self.params['start_date'],
                end_date=self.params['end_date'],
                param_grid=param_grid,
                optimization_metric=self.params['optimization_metric'],
                data_period=self.params.get('data_period', '1m')  # 新增：传递数据周期
            )

            self.progress_updated.emit(100, "优化完成")
            self.optimization_completed.emit(results_df)

        except Exception as e:
            import traceback
            error_msg = f"优化失败: {str(e)}\n{traceback.format_exc()}"
            self.error_occurred.emit(error_msg)


class GridBacktestWidget(QWidget):
    """511380.SH网格策略回测界面"""

    def __init__(self):
        super().__init__()
        self.backtest_result = None
        self.optimization_result = None
        self.worker = None

        self.init_ui()
        self.load_default_params()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 标题
        title = QLabel("511380.SH 债券ETF网格策略回测")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 创建选项卡
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        # 选项卡1：参数配置
        config_tab = self.create_config_tab()
        tab_widget.addTab(config_tab, "参数配置")

        # 选项卡2：回测结果
        self.results_tab = self.create_results_tab()
        tab_widget.addTab(self.results_tab, "回测结果")

        # 选项卡3：参数优化
        self.optimization_tab = self.create_optimization_tab()
        tab_widget.addTab(self.optimization_tab, "参数优化")

    def create_config_tab(self):
        """创建参数配置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 基本参数组
        basic_group = QGroupBox("基本参数")
        basic_layout = QGridLayout()

        # 股票代码
        basic_layout.addWidget(QLabel("股票代码:"), 0, 0)
        self.stock_code_edit = QLineEdit("511380.SH")
        basic_layout.addWidget(self.stock_code_edit, 0, 1)

        # 初始资金
        basic_layout.addWidget(QLabel("初始资金:"), 0, 2)
        self.initial_cash_spin = QSpinBox()
        self.initial_cash_spin.setRange(10000, 10000000)
        self.initial_cash_spin.setValue(100000)
        self.initial_cash_spin.setSuffix(" 元")
        basic_layout.addWidget(self.initial_cash_spin, 0, 3)

        # 手续费率
        basic_layout.addWidget(QLabel("手续费率:"), 1, 0)
        self.commission_spin = QDoubleSpinBox()
        self.commission_spin.setRange(0.0001, 0.01)
        self.commission_spin.setValue(0.0001)
        self.commission_spin.setDecimals(4)
        self.commission_spin.setSingleStep(0.0001)
        basic_layout.addWidget(QLabel("万分之一"), 1, 1)
        basic_layout.addWidget(self.commission_spin, 1, 1)

        # 数据周期选择（新增）
        basic_layout.addWidget(QLabel("数据周期:"), 1, 2)
        self.data_period_combo = QComboBox()
        self.data_period_combo.addItem("1分钟 (1m)", "1m")
        self.data_period_combo.addItem("5分钟 (5m)", "5m")
        self.data_period_combo.addItem("15分钟 (15m)", "15m")
        self.data_period_combo.addItem("30分钟 (30m)", "30m")
        self.data_period_combo.addItem("60分钟 (1h)", "1h")
        self.data_period_combo.addItem("日线 (1d)", "1d")
        self.data_period_combo.addItem("周线 (1w)", "1w")
        self.data_period_combo.setCurrentIndex(0)  # 默认1分钟
        self.data_period_combo.setToolTip("选择回测使用的数据周期\n1分钟: 准确但慢\n日线: 快速但粗糙")
        basic_layout.addWidget(self.data_period_combo, 1, 3)

        # 日期范围
        basic_layout.addWidget(QLabel("开始日期:"), 2, 0)
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        # 根据数据周期设置不同的默认时间范围
        self.start_date_edit.setDate(QDate.currentDate().addDays(-30))  # 改为30天（更适合1分钟）
        basic_layout.addWidget(self.start_date_edit, 2, 1)

        basic_layout.addWidget(QLabel("结束日期:"), 2, 2)
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        basic_layout.addWidget(self.end_date_edit, 2, 3)

        # 添加自动更新日期的按钮
        date_update_layout = QHBoxLayout()
        self.auto_update_date_check = QCheckBox("自动更新为最新日期")
        self.auto_update_date_check.setChecked(True)  # 默认勾选
        self.auto_update_date_check.setToolTip("运行回测时自动将结束日期设为今天")
        date_update_layout.addWidget(self.auto_update_date_check)
        date_update_layout.addStretch()
        basic_layout.addLayout(date_update_layout, 3, 0, 1, 4)

        # 添加智能时间范围调整按钮
        smart_date_layout = QHBoxLayout()
        self.smart_date_check = QCheckBox("智能调整时间范围")
        self.smart_date_check.setChecked(True)  # 默认勾选
        self.smart_date_check.setToolTip("根据数据周期自动调整时间范围\n1分钟: 30天\n5分钟: 60天\n日线: 90天")
        smart_date_layout.addWidget(self.smart_date_check)
        smart_date_layout.addStretch()
        basic_layout.addLayout(smart_date_layout, 4, 0, 1, 4)

        # 连接信号：当周期改变时，自动调整时间范围
        self.data_period_combo.currentTextChanged.connect(self.on_data_period_changed)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # 策略模式选择
        strategy_group = QGroupBox("策略模式")
        strategy_layout = QGridLayout()

        strategy_layout.addWidget(QLabel("策略模式:"), 0, 0)
        self.strategy_mode_combo = QComboBox()
        self.strategy_mode_combo.addItem("固定网格", "fixed")
        self.strategy_mode_combo.addItem("自适应网格", "adaptive")
        self.strategy_mode_combo.addItem("ATR动态网格", "atr")
        self.strategy_mode_combo.setCurrentIndex(0)
        self.strategy_mode_combo.setToolTip(
            "• 固定网格：在固定价格区间内设置等间距网格\n"
            "• 自适应网格：根据相对涨跌幅触发交易（适合趋势行情）\n"
            "• ATR动态网格：根据ATR波动率动态调整网格间距"
        )
        strategy_layout.addWidget(self.strategy_mode_combo, 0, 1, 1, 3)

        strategy_group.setLayout(strategy_layout)
        layout.addWidget(strategy_group)

        # 连接信号：策略模式改变时显示/隐藏参数
        self.strategy_mode_combo.currentIndexChanged.connect(self.on_strategy_mode_changed)

        # 固定网格参数组
        self.fixed_grid_group = QGroupBox("固定网格参数")
        fixed_grid_layout = QGridLayout()

        # 网格数量
        fixed_grid_layout.addWidget(QLabel("网格数量:"), 0, 0)
        self.grid_count_spin = QSpinBox()
        self.grid_count_spin.setRange(3, 50)
        self.grid_count_spin.setValue(15)
        fixed_grid_layout.addWidget(self.grid_count_spin, 0, 1)

        # 价格区间
        fixed_grid_layout.addWidget(QLabel("价格区间:"), 0, 2)
        self.price_range_spin = QDoubleSpinBox()
        self.price_range_spin.setRange(0.5, 10.0)
        self.price_range_spin.setValue(5.0)
        self.price_range_spin.setSuffix("%")
        fixed_grid_layout.addWidget(self.price_range_spin, 0, 3)

        # 每格数量
        fixed_grid_layout.addWidget(QLabel("每格交易数量:"), 1, 0)
        self.position_size_spin = QSpinBox()
        self.position_size_spin.setRange(100, 10000)
        self.position_size_spin.setValue(1000)
        self.position_size_spin.setSuffix(" 股")
        fixed_grid_layout.addWidget(self.position_size_spin, 1, 1)

        # 基准价格
        fixed_grid_layout.addWidget(QLabel("基准价格:"), 1, 2)
        self.base_price_edit = QLineEdit()
        self.base_price_edit.setPlaceholderText("留空使用首日收盘价")
        fixed_grid_layout.addWidget(self.base_price_edit, 1, 3)

        # 动态调整
        self.enable_trailing_check = QCheckBox("启用动态调整基准价")
        self.enable_trailing_check.setChecked(True)
        fixed_grid_layout.addWidget(self.enable_trailing_check, 2, 0, 1, 4)

        self.fixed_grid_group.setLayout(fixed_grid_layout)
        layout.addWidget(self.fixed_grid_group)

        # 自适应网格参数组（初始隐藏）
        self.adaptive_grid_group = QGroupBox("自适应网格参数")
        adaptive_grid_layout = QGridLayout()

        # 买入阈值
        adaptive_grid_layout.addWidget(QLabel("买入阈值:"), 0, 0)
        self.buy_threshold_spin = QDoubleSpinBox()
        self.buy_threshold_spin.setRange(0.1, 10.0)
        self.buy_threshold_spin.setValue(1.0)
        self.buy_threshold_spin.setSuffix("%")
        self.buy_threshold_spin.setToolTip("价格下跌超过该百分比时触发买入")
        adaptive_grid_layout.addWidget(self.buy_threshold_spin, 0, 1)

        # 卖出阈值
        adaptive_grid_layout.addWidget(QLabel("卖出阈值:"), 0, 2)
        self.sell_threshold_spin = QDoubleSpinBox()
        self.sell_threshold_spin.setRange(0.1, 10.0)
        self.sell_threshold_spin.setValue(1.0)
        self.sell_threshold_spin.setSuffix("%")
        self.sell_threshold_spin.setToolTip("价格上涨超过该百分比时触发卖出")
        adaptive_grid_layout.addWidget(self.sell_threshold_spin, 0, 3)

        # 每格交易数量
        adaptive_grid_layout.addWidget(QLabel("每格交易数量:"), 1, 0)
        self.adaptive_position_size_spin = QSpinBox()
        self.adaptive_position_size_spin.setRange(100, 10000)
        self.adaptive_position_size_spin.setValue(1000)
        self.adaptive_position_size_spin.setSuffix(" 股")
        adaptive_grid_layout.addWidget(self.adaptive_position_size_spin, 1, 1)

        # 基准价格
        adaptive_grid_layout.addWidget(QLabel("基准价格:"), 1, 2)
        self.adaptive_base_price_edit = QLineEdit()
        self.adaptive_base_price_edit.setPlaceholderText("留空使用首日收盘价")
        adaptive_grid_layout.addWidget(self.adaptive_base_price_edit, 1, 3)

        self.adaptive_grid_group.setLayout(adaptive_grid_layout)
        layout.addWidget(self.adaptive_grid_group)
        self.adaptive_grid_group.setVisible(False)  # 初始隐藏

        # ATR动态网格参数组（初始隐藏）
        self.atr_grid_group = QGroupBox("ATR动态网格参数")
        atr_grid_layout = QGridLayout()

        # ATR周期
        atr_grid_layout.addWidget(QLabel("ATR周期:"), 0, 0)
        self.atr_period_spin = QSpinBox()
        self.atr_period_spin.setRange(5, 50)
        self.atr_period_spin.setValue(14)
        self.atr_period_spin.setSuffix(" 天")
        self.atr_period_spin.setToolTip("ATR计算周期（默认14天）")
        atr_grid_layout.addWidget(self.atr_period_spin, 0, 1)

        # ATR倍数
        atr_grid_layout.addWidget(QLabel("ATR倍数:"), 0, 2)
        self.atr_multiplier_spin = QDoubleSpinBox()
        self.atr_multiplier_spin.setRange(0.1, 5.0)
        self.atr_multiplier_spin.setValue(1.0)
        self.atr_multiplier_spin.setSingleStep(0.1)
        self.atr_multiplier_spin.setToolTip("网格间距 = ATR * 倍数")
        atr_grid_layout.addWidget(self.atr_multiplier_spin, 0, 3)

        # 每格交易数量
        atr_grid_layout.addWidget(QLabel("每格交易数量:"), 1, 0)
        self.atr_position_size_spin = QSpinBox()
        self.atr_position_size_spin.setRange(100, 10000)
        self.atr_position_size_spin.setValue(1000)
        self.atr_position_size_spin.setSuffix(" 股")
        atr_grid_layout.addWidget(self.atr_position_size_spin, 1, 1)

        # 基准价格
        atr_grid_layout.addWidget(QLabel("基准价格:"), 1, 2)
        self.atr_base_price_edit = QLineEdit()
        self.atr_base_price_edit.setPlaceholderText("留空使用首日收盘价")
        atr_grid_layout.addWidget(self.atr_base_price_edit, 1, 3)

        self.atr_grid_group.setLayout(atr_grid_layout)
        layout.addWidget(self.atr_grid_group)
        self.atr_grid_group.setVisible(False)  # 初始隐藏

        # 按钮
        button_layout = QHBoxLayout()
        self.run_backtest_btn = QPushButton("▶ 运行回测")
        self.run_backtest_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.run_backtest_btn.clicked.connect(self.run_backtest)
        button_layout.addWidget(self.run_backtest_btn)

        layout.addLayout(button_layout)

        # 说明
        info_label = QLabel(
            "提示：\n"
            "• 固定网格：适合震荡行情，在固定价格区间内高抛低吸\n"
            "• 自适应网格：根据涨跌幅触发，适合趋势行情或波动大的品种\n"
            "• ATR动态网格：根据ATR波动率动态调整，适合波动率变化的品种\n"
            "• 1分钟数据准确但慢（建议30天），日线数据快速但粗糙\n"
            "• 选择数据周期后，时间范围会自动调整以匹配数据量"
        )
        info_label.setStyleSheet("color: #666; font-size: 11px; padding: 10px;")
        layout.addWidget(info_label)

        layout.addStretch()
        return widget

    def create_results_tab(self):
        """创建回测结果选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 关键指标
        metrics_group = QGroupBox("关键指标")
        metrics_layout = QGridLayout()

        self.metrics_labels = {}
        metrics = [
            ("总收益率", "total_return"),
            ("夏普比率", "sharpe_ratio"),
            ("最大回撤", "max_drawdown"),
            ("交易次数", "total_trades"),
            ("盈利次数", "won_trades"),
            ("胜率", "win_rate")
        ]

        for i, (label_text, key) in enumerate(metrics):
            row = i // 2
            col = (i % 2) * 2

            metrics_layout.addWidget(QLabel(f"{label_text}:"), row, col)
            value_label = QLabel("--")
            value_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            metrics_layout.addWidget(value_label, row, col + 1)
            self.metrics_labels[key] = value_label

        metrics_group.setLayout(metrics_layout)
        layout.addWidget(metrics_group)

        # 净值曲线图表（双Y轴：净值 + 持仓）
        chart_group = QGroupBox("净值曲线 & 持仓变化")
        chart_layout = QVBoxLayout()

        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure
        import matplotlib.pyplot as plt

        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False

        # 创建图表（2个子图：净值 + 持仓）
        self.figure = Figure(figsize=(10, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)

        # 子图1：净值曲线
        self.ax1 = self.figure.add_subplot(211)
        self.ax1.set_title("净值曲线")
        self.ax1.set_ylabel("净值")
        self.ax1.grid(True, alpha=0.3)

        # 子图2：持仓变化
        self.ax2 = self.figure.add_subplot(212, sharex=self.ax1)
        self.ax2.set_title("持仓变化")
        self.ax2.set_xlabel("日期")
        self.ax2.set_ylabel("持仓（股）")
        self.ax2.grid(True, alpha=0.3)

        self.figure.tight_layout(pad=3.0)

        chart_layout.addWidget(self.canvas)
        chart_group.setLayout(chart_layout)
        layout.addWidget(chart_group)

        # 交易日志
        trade_group = QGroupBox("交易日志")
        trade_layout = QVBoxLayout()
        self.trade_table = QTableWidget()
        self.trade_table.setColumnCount(5)
        self.trade_table.setHorizontalHeaderLabels(["日期", "方向", "价格", "数量", "触发价"])
        self.trade_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        trade_layout.addWidget(self.trade_table)
        trade_group.setLayout(trade_layout)
        layout.addWidget(trade_group)

        return widget

    def create_optimization_tab(self):
        """创建参数优化选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 优化参数组
        opt_group = QGroupBox("优化参数")
        opt_layout = QGridLayout()

        # 网格数量范围
        opt_layout.addWidget(QLabel("网格数量:"), 0, 0)
        range_layout = QHBoxLayout()
        self.grid_min_spin = QSpinBox()
        self.grid_min_spin.setRange(3, 20)
        self.grid_min_spin.setValue(5)
        range_layout.addWidget(self.grid_min_spin)

        range_layout.addWidget(QLabel("-"))

        self.grid_max_spin = QSpinBox()
        self.grid_max_spin.setRange(5, 50)
        self.grid_max_spin.setValue(15)
        range_layout.addWidget(self.grid_max_spin)

        range_layout.addWidget(QLabel("步长:"))
        self.grid_step_spin = QSpinBox()
        self.grid_step_spin.setRange(1, 10)
        self.grid_step_spin.setValue(5)
        range_layout.addWidget(self.grid_step_spin)

        opt_layout.addLayout(range_layout, 0, 1, 1, 3)

        # 价格区间范围
        opt_layout.addWidget(QLabel("价格区间(%):"), 1, 0)
        range_layout2 = QHBoxLayout()
        self.price_min_spin = QSpinBox()
        self.price_min_spin.setRange(1, 5)
        self.price_min_spin.setValue(1)
        range_layout2.addWidget(self.price_min_spin)

        range_layout2.addWidget(QLabel("-"))

        self.price_max_spin = QSpinBox()
        self.price_max_spin.setRange(3, 10)
        self.price_max_spin.setValue(5)
        range_layout2.addWidget(self.price_max_spin)

        range_layout2.addWidget(QLabel("步长:"))
        self.price_step_spin = QSpinBox()
        self.price_step_spin.setRange(1, 5)
        self.price_step_spin.setValue(1)
        range_layout2.addWidget(self.price_step_spin)

        opt_layout.addLayout(range_layout2, 1, 1, 1, 3)

        # 优化目标
        opt_layout.addWidget(QLabel("优化目标:"), 2, 0)
        self.optimization_metric_combo = QComboBox()
        self.optimization_metric_combo.addItems([
            "total_return (总收益率)",
            "sharpe_ratio (夏普比率)",
            "max_drawdown (最大回撤)"
        ])
        opt_layout.addWidget(self.optimization_metric_combo, 2, 1, 1, 3)

        opt_group.setLayout(opt_layout)
        layout.addWidget(opt_group)

        # 运行优化按钮
        self.run_optimization_btn = QPushButton("🚀 开始参数优化")
        self.run_optimization_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
        """)
        self.run_optimization_btn.clicked.connect(self.run_optimization)
        layout.addWidget(self.run_optimization_btn)

        # 优化结果表格
        result_group = QGroupBox("优化结果（Top 20）")
        result_layout = QVBoxLayout()
        self.opt_results_table = QTableWidget()
        self.opt_results_table.setColumnCount(8)
        self.opt_results_table.setHorizontalHeaderLabels([
            "排名", "网格数", "区间(%)", "收益率(%)",
            "夏普比率", "最大回撤(%)", "交易次数", "胜率(%)"
        ])
        self.opt_results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        result_layout.addWidget(self.opt_results_table)
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        return widget

    def on_strategy_mode_changed(self, index: int):
        """策略模式改变时显示/隐藏对应的参数组"""
        strategy_mode = self.strategy_mode_combo.currentData()

        # 隐藏所有策略参数组
        self.fixed_grid_group.setVisible(False)
        self.adaptive_grid_group.setVisible(False)
        self.atr_grid_group.setVisible(False)

        # 显示选中的策略参数组
        if strategy_mode == 'fixed':
            self.fixed_grid_group.setVisible(True)
        elif strategy_mode == 'adaptive':
            self.adaptive_grid_group.setVisible(True)
        elif strategy_mode == 'atr':
            self.atr_grid_group.setVisible(True)

        print(f"[策略模式] 切换到: {self.strategy_mode_combo.currentText()}")

    def load_default_params(self):
        """加载默认参数"""
        # 可以从配置文件加载历史参数
        pass

    def on_data_period_changed(self, period_value: str):
        """当数据周期改变时自动调整时间范围"""
        if not self.smart_date_check.isChecked():
            return

        # 根据数据周期智能调整时间范围
        period_ranges = {
            '1m': 30,    # 1分钟数据用30天
            '5m': 60,    # 5分钟数据用60天
            '15m': 90,   # 15分钟数据用90天
            '30m': 120,  # 30分钟数据用120天
            '1h': 180,   # 1小时数据用180天
            '1d': 365,   # 日线数据用365天
            '1w': 730    # 周线数据用730天
        }

        days = period_ranges.get(period_value, 30)

        # 更新开始日期
        today = QDate.currentDate()
        start_date = today.addDays(-days)
        self.start_date_edit.setDate(start_date)

        print(f"[智能调整] 数据周期: {period_value}, 时间范围调整为: {days}天")

    def get_backtest_params(self):
        """获取回测参数"""
        # 获取选择的数据周期
        data_period = self.data_period_combo.currentData()

        # 获取策略模式
        strategy_mode = self.strategy_mode_combo.currentData()

        params = {
            'stock_code': self.stock_code_edit.text(),
            'initial_cash': self.initial_cash_spin.value(),
            'commission': self.commission_spin.value(),
            'start_date': self.start_date_edit.date().toString('yyyy-MM-dd'),
            'end_date': self.end_date_edit.date().toString('yyyy-MM-dd'),
            'strategy_mode': strategy_mode,  # 新增：策略模式
            'data_period': data_period
        }

        # 根据策略模式添加不同的参数
        if strategy_mode == 'fixed':
            params['grid_count'] = self.grid_count_spin.value()
            params['price_range'] = self.price_range_spin.value() / 100
            params['position_size'] = self.position_size_spin.value()
            params['enable_trailing'] = self.enable_trailing_check.isChecked()

            base_price = self.base_price_edit.text().strip()
            if base_price:
                try:
                    params['base_price'] = float(base_price)
                except:
                    pass

        elif strategy_mode == 'adaptive':
            params['buy_threshold'] = self.buy_threshold_spin.value() / 100
            params['sell_threshold'] = self.sell_threshold_spin.value() / 100
            params['position_size'] = self.adaptive_position_size_spin.value()

            base_price = self.adaptive_base_price_edit.text().strip()
            if base_price:
                try:
                    params['base_price'] = float(base_price)
                except:
                    pass

        elif strategy_mode == 'atr':
            params['atr_period'] = self.atr_period_spin.value()
            params['atr_multiplier'] = self.atr_multiplier_spin.value()
            params['position_size'] = self.atr_position_size_spin.value()

            base_price = self.atr_base_price_edit.text().strip()
            if base_price:
                try:
                    params['base_price'] = float(base_price)
                except:
                    pass

        return params

    def get_optimization_params(self):
        """获取优化参数"""
        base_params = self.get_backtest_params()

        # 解析优化目标
        metric_text = self.optimization_metric_combo.currentText()
        metric = metric_text.split()[0]

        opt_params = {
            **base_params,
            'grid_count_min': self.grid_min_spin.value(),
            'grid_count_max': self.grid_max_spin.value(),
            'grid_count_step': self.grid_step_spin.value(),
            'price_range_min': self.price_min_spin.value(),
            'price_range_max': self.price_max_spin.value(),
            'price_range_step': self.price_step_spin.value(),
            'optimization_metric': metric,
            'optimize_position_size': False
        }

        return opt_params

    def run_backtest(self):
        """运行回测"""
        if not GRID_STRATEGY_AVAILABLE:
            QMessageBox.warning(self, "错误", "网格策略模块未安装")
            return

        # 自动更新日期（如果勾选了）
        if self.auto_update_date_check.isChecked():
            from datetime import datetime, timedelta
            today = QDate.currentDate()
            ninety_days_ago = today.addDays(-90)

            self.end_date_edit.setDate(today)
            self.start_date_edit.setDate(ninety_days_ago)

            print(f"[日期更新] 自动更新为: {ninety_days_ago.toString('yyyy-MM-dd')} ~ {today.toString('yyyy-MM-dd')}")

        params = self.get_backtest_params()

        # 禁用按钮
        self.run_backtest_btn.setEnabled(False)
        self.run_backtest_btn.setText("回测运行中...")

        # 启动工作线程
        self.worker = GridBacktestWorker(params)
        self.worker.progress_updated.connect(lambda p, msg: print(f"[{p}%] {msg}"))
        self.worker.backtest_completed.connect(self.on_backtest_completed)
        self.worker.error_occurred.connect(self.on_backtest_error)
        self.worker.start()

    def on_backtest_completed(self, result):
        """回测完成"""
        self.backtest_result = result

        # 更新指标显示
        metrics = result['metrics']
        self.metrics_labels['total_return'].setText(f"{metrics['total_return']*100:.2f}%")
        self.metrics_labels['sharpe_ratio'].setText(f"{metrics['sharpe_ratio']:.2f}" if metrics['sharpe_ratio'] else "N/A")
        self.metrics_labels['max_drawdown'].setText(f"{metrics['max_drawdown']:.2f}%")
        self.metrics_labels['total_trades'].setText(f"{metrics['total_trades']}")
        self.metrics_labels['won_trades'].setText(f"{metrics['won_trades']}")
        self.metrics_labels['win_rate'].setText(f"{metrics['win_rate']*100:.2f}%")

        # 更新交易日志
        trade_log = result['trade_log']
        self.trade_table.setRowCount(len(trade_log))
        for i, trade in trade_log.iterrows():
            self.trade_table.setItem(i, 0, QTableWidgetItem(str(trade['date'])))
            self.trade_table.setItem(i, 1, QTableWidgetItem(trade['action']))
            self.trade_table.setItem(i, 2, QTableWidgetItem(f"{trade['price']:.3f}"))
            self.trade_table.setItem(i, 3, QTableWidgetItem(f"{trade['size']}"))
            self.trade_table.setItem(i, 4, QTableWidgetItem(f"{trade['trigger_price']:.3f}"))

        # 绘制净值曲线和持仓变化
        equity_curve = result['equity_curve']
        if not equity_curve.empty:
            # 清空两个子图
            self.ax1.clear()
            self.ax2.clear()

            # 转换日期格式
            dates = pd.to_datetime(equity_curve['date'])
            values = equity_curve['portfolio_value'].values
            positions = equity_curve['position'].values
            initial_value = metrics['initial_cash']

            # 数据采样：如果数据点太多，进行采样以提高显示效果
            max_points = 2000  # 最多显示2000个点
            if len(dates) > max_points:
                step = len(dates) // max_points
                dates = dates[::step]
                values = values[::step]
                positions = positions[::step]

            # ===== 子图1：净值曲线 =====
            # 绘制净值曲线
            self.ax1.plot(dates, values,
                         color='#2E86DE',
                         linewidth=1.2,
                         linestyle='-',
                         alpha=0.9,
                         label='净值')

            # 添加填充区域
            self.ax1.fill_between(dates,
                                 values,
                                 initial_value,
                                 where=(values >= initial_value),
                                 color='#2E86DE',
                                 alpha=0.1)

            self.ax1.fill_between(dates,
                                 values,
                                 initial_value,
                                 where=(values < initial_value),
                                 color='#E74C3C',
                                 alpha=0.1)

            # 标记初始资金线
            self.ax1.axhline(y=initial_value,
                           color='#95A5A6',
                           linestyle='--',
                           linewidth=1.5,
                           alpha=0.7,
                           label='初始资金')

            # 标记最高点和最低点
            import numpy as np
            max_idx = np.argmax(values)
            min_idx = np.argmin(values)
            dates_array = np.array(dates)

            self.ax1.scatter([dates_array[max_idx]], [values[max_idx]],
                           color='#27AE60', s=100,
                           marker='^', zorder=5,
                           label=f'最高: {values[max_idx]:.0f}')
            self.ax1.scatter([dates_array[min_idx]], [values[min_idx]],
                           color='#C0392B', s=100,
                           marker='v', zorder=5,
                           label=f'最低: {values[min_idx]:.0f}')

            # 设置标题和标签
            return_color = '#27AE60' if metrics['total_return'] >= 0 else '#C0392B'
            self.ax1.set_title(f"净值曲线 (收益率: {metrics['total_return']*100:.2f}%)",
                            color=return_color,
                            fontweight='bold',
                            fontsize=11)
            self.ax1.set_ylabel("净值", fontsize=10)
            self.ax1.grid(True, alpha=0.3, linestyle=':', linewidth=0.5)
            self.ax1.legend(loc='best', fontsize=8, framealpha=0.9)

            # 格式化y轴（显示为千分位）
            import matplotlib.ticker as ticker
            self.ax1.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))

            # ===== 子图2：持仓变化 =====
            # 绘制持仓曲线（填充区域）
            self.ax2.fill_between(dates,
                                 positions,
                                 color='#F39C12',
                                 alpha=0.3,
                                 label='持仓')
            self.ax2.plot(dates, positions,
                         color='#F39C12',
                         linewidth=1.2,
                         alpha=0.8,
                         label='持仓数量')

            # 标记最大持仓点
            max_pos_idx = np.argmax(positions)
            min_pos_idx = np.argmin(positions)

            self.ax2.scatter([dates_array[max_pos_idx]], [positions[max_pos_idx]],
                           color='#C0392B', s=100,
                           marker='v', zorder=5,
                           label=f'最大: {int(positions[max_pos_idx])}股')
            self.ax2.scatter([dates_array[min_pos_idx]], [positions[min_pos_idx]],
                           color='#27AE60', s=100,
                           marker='^', zorder=5,
                           label=f'最小: {int(positions[min_pos_idx])}股')

            # 标注持仓信息
            position_size = result['params']['position_size']
            strategy_mode = result['params'].get('strategy_mode', 'fixed')

            if strategy_mode == 'fixed':
                grid_count = result['params']['grid_count']
                max_possible = grid_count * position_size
                actual_max = int(positions[max_pos_idx])
                title = f"持仓变化 - 固定网格 (最大: {actual_max}股 / 理论最大: {max_possible}股 = {actual_max/max_possible*100:.1f}%)"
            elif strategy_mode == 'adaptive':
                actual_max = int(positions[max_pos_idx])
                title = f"持仓变化 - 自适应网格 (最大持仓: {actual_max}股)"
            elif strategy_mode == 'atr':
                atr_period = result['params'].get('atr_period', 14)
                atr_multiplier = result['params'].get('atr_multiplier', 1.0)
                actual_max = int(positions[max_pos_idx])
                title = f"持仓变化 - ATR网格 (ATR: {atr_period}天 x {atr_multiplier}, 最大持仓: {actual_max}股)"
            else:
                actual_max = int(positions[max_pos_idx])
                title = f"持仓变化 (最大持仓: {actual_max}股)"

            self.ax2.set_title(title,
                            fontweight='bold',
                            fontsize=11)
            self.ax2.set_xlabel("日期", fontsize=10)
            self.ax2.set_ylabel("持仓（股）", fontsize=10)
            self.ax2.grid(True, alpha=0.3, linestyle=':', linewidth=0.5)
            self.ax2.legend(loc='best', fontsize=8, framealpha=0.9)

            # 格式化x轴日期显示
            import matplotlib.dates as mdates
            self.ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            self.ax2.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//10)))
            self.figure.autofmt_xdate()

            # 设置边距
            self.ax1.margins(x=0.02, y=0.05)
            self.ax2.margins(x=0.02, y=0.05)

            self.canvas.draw()

        # 恢复按钮
        self.run_backtest_btn.setEnabled(True)
        self.run_backtest_btn.setText("▶ 运行回测")

        QMessageBox.information(self, "回测完成",
            f"回测完成！\n\n"
            f"总收益率: {metrics['total_return']*100:.2f}%\n"
            f"夏普比率: {metrics['sharpe_ratio']:.2f}\n" if metrics['sharpe_ratio'] else "夏普比率: N/A\n"
            f"最大回撤: {metrics['max_drawdown']:.2f}%\n"
            f"交易次数: {metrics['total_trades']}")

    def on_backtest_error(self, error_msg):
        """回测错误"""
        self.run_backtest_btn.setEnabled(True)
        self.run_backtest_btn.setText("▶ 运行回测")
        QMessageBox.critical(self, "回测错误", error_msg)

    def run_optimization(self):
        """运行参数优化"""
        if not GRID_STRATEGY_AVAILABLE:
            QMessageBox.warning(self, "错误", "网格策略模块未安装")
            return

        params = self.get_optimization_params()

        # 禁用按钮
        self.run_optimization_btn.setEnabled(False)
        self.run_optimization_btn.setText("优化运行中...")

        # 启动工作线程
        self.worker = GridOptimizationWorker(params)
        self.worker.progress_updated.connect(lambda p, msg: print(f"[{p}%] {msg}"))
        self.worker.optimization_completed.connect(self.on_optimization_completed)
        self.worker.error_occurred.connect(self.on_optimization_error)
        self.worker.start()

    def on_optimization_completed(self, results_df):
        """优化完成"""
        self.optimization_result = results_df

        # 显示Top 20结果
        top_results = results_df.head(20)
        self.opt_results_table.setRowCount(len(top_results))

        for i, row in enumerate(top_results.itertuples()):
            self.opt_results_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.opt_results_table.setItem(i, 1, QTableWidgetItem(str(int(row.grid_count))))
            self.opt_results_table.setItem(i, 2, QTableWidgetItem(f"{row.price_range*100:.1f}"))
            self.opt_results_table.setItem(i, 3, QTableWidgetItem(f"{row.total_return*100:.2f}"))
            self.opt_results_table.setItem(i, 4, QTableWidgetItem(f"{row.sharpe_ratio:.2f}" if pd.notna(row.sharpe_ratio) else "N/A"))
            self.opt_results_table.setItem(i, 5, QTableWidgetItem(f"{row.max_drawdown:.2f}"))
            self.opt_results_table.setItem(i, 6, QTableWidgetItem(f"{int(row.total_trades)}"))
            self.opt_results_table.setItem(i, 7, QTableWidgetItem(f"{row.win_rate*100:.1f}"))

        # 恢复按钮
        self.run_optimization_btn.setEnabled(True)
        self.run_optimization_btn.setText("🚀 开始参数优化")

        # 显示最佳参数
        best = results_df.iloc[0]

        # 根据参数显示不同的信息
        if 'grid_count' in best:
            # 固定网格模式
            QMessageBox.information(self, "优化完成",
                f"参数优化完成！\n\n"
                f"最佳参数（固定网格）:\n"
                f"网格数量: {int(best.grid_count)}\n"
                f"价格区间: {best.price_range*100:.1f}%\n"
                f"总收益率: {best.total_return*100:.2f}%\n"
                f"夏普比率: {best.sharpe_ratio:.2f}\n"
                f"最大回撤: {best.max_drawdown:.2f}%")
        else:
            # 其他模式（暂未实现优化）
            QMessageBox.information(self, "优化完成",
                f"参数优化完成！\n\n"
                f"总收益率: {best.total_return*100:.2f}%\n"
                f"夏普比率: {best.sharpe_ratio:.2f}\n"
                f"最大回撤: {best.max_drawdown:.2f}%")

    def on_optimization_error(self, error_msg):
        """优化错误"""
        self.run_optimization_btn.setEnabled(True)
        self.run_optimization_btn.setText("🚀 开始参数优化")
        QMessageBox.critical(self, "优化错误", error_msg)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    widget = GridBacktestWidget()
    widget.resize(1200, 800)
    widget.setWindowTitle("511380.SH 网格策略回测")
    widget.show()
    sys.exit(app.exec_())
