# -*- coding: utf-8 -*-
"""
回测窗口组件
专业的回测界面，集成Backtrader回测引擎和HTML报告生成
"""

import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QTextEdit, QProgressBar, QGroupBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QSplitter, QFrame, QDateEdit, QCheckBox, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate, QTimer
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional

# 导入matplotlib用于绘制图表
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.dates as mdates
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 支持中文
    plt.rcParams['axes.unicode_minus'] = False
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[WARNING] matplotlib未安装，净值曲线将显示为占位符")

# 导入回测模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    # 优先使用修复版引擎
    from backtest.engine import AdvancedBacktestEngine, DualMovingAverageStrategy
    print("[OK] 使用修复版回测引擎")
except ImportError:
    try:
        from backtest.engine import AdvancedBacktestEngine, DualMovingAverageStrategy
        print("[WARNING] 使用原版回测引擎")
    except ImportError:
        print("[ERROR] 回测引擎导入失败")
        AdvancedBacktestEngine = None
        DualMovingAverageStrategy = None

try:
    from backtest.data_manager import DataManager, DataSource
    from backtest.risk_analyzer import RiskAnalyzer
except ImportError:
    print("⚠️ 回测模块导入失败，请检查模块路径")
    DataManager = None
    DataSource = None
    RiskAnalyzer = None


class BacktestWorker(QThread):
    """回测工作线程"""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    results_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, backtest_params):
        super().__init__()
        self.backtest_params = backtest_params
        self.is_running = True
    
    def run(self):
        """执行回测"""
        try:
            self.status_updated.emit("🚀 初始化回测引擎...")
            self.progress_updated.emit(10)
            
            # 创建回测引擎
            engine = AdvancedBacktestEngine(
                initial_cash=self.backtest_params['initial_cash'],
                commission=self.backtest_params['commission']
            )
            
            self.status_updated.emit("📊 获取历史数据...")
            self.progress_updated.emit(30)

            # 获取数据（支持复权）
            data_manager = DataManager()
            stock_data = data_manager.get_stock_data(
                stock_code=self.backtest_params['stock_code'],
                start_date=self.backtest_params['start_date'],
                end_date=self.backtest_params['end_date'],
                adjust=self.backtest_params.get('adjust', 'none')  # ← 添加复权参数
            )
            
            if stock_data.empty:
                raise Exception("无法获取股票数据")
            
            self.status_updated.emit("🔧 配置策略参数...")
            self.progress_updated.emit(50)
            
            # 添加数据和策略
            engine.add_data(stock_data)
            engine.add_strategy(
                DualMovingAverageStrategy,
                short_period=self.backtest_params['short_period'],
                long_period=self.backtest_params['long_period'],
                rsi_period=self.backtest_params['rsi_period']
            )
            
            self.status_updated.emit("⚡ 执行回测计算...")
            self.progress_updated.emit(70)
            
            # 运行回测
            results = engine.run_backtest()
            
            self.status_updated.emit("📈 分析风险指标...")
            self.progress_updated.emit(90)
            
            # 获取详细结果
            detailed_results = engine.get_detailed_results()
            
            # 风险分析
            risk_analyzer = RiskAnalyzer()
            portfolio_curve = detailed_results['portfolio_curve']
            
            # 提取净值序列用于风险分析
            if isinstance(portfolio_curve, dict) and 'values' in portfolio_curve:
                portfolio_values = portfolio_curve['values']
            else:
                # 如果格式不正确，使用空列表
                portfolio_values = []
            
            risk_analysis = risk_analyzer.analyze_portfolio(portfolio_values)
            
            # 合并结果
            final_results = {
                'performance_metrics': results,
                'detailed_results': detailed_results,
                'risk_analysis': risk_analysis,
                'portfolio_curve': portfolio_curve,
                'stock_data': stock_data,
                'backtest_params': self.backtest_params
            }
            
            self.status_updated.emit("✅ 回测完成")
            self.progress_updated.emit(100)
            
            self.results_ready.emit(final_results)
            
        except Exception as e:
            self.error_occurred.emit(f"回测执行失败: {str(e)}")
    
    def stop(self):
        """停止回测"""
        self.is_running = False
        self.terminate()


class PortfolioChart(QWidget):
    """投资组合净值曲线图表组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        if MATPLOTLIB_AVAILABLE:
            # 创建matplotlib图表
            self.figure = Figure(figsize=(10, 6), dpi=100)
            self.canvas = FigureCanvas(self.figure)
            layout.addWidget(self.canvas)
            
            # 初始化空图表
            self.ax = self.figure.add_subplot(111)
            self.ax.set_title('投资组合净值曲线', fontsize=14, fontweight='bold')
            self.ax.set_xlabel('日期')
            self.ax.set_ylabel('净值')
            self.ax.grid(True, alpha=0.3)
            self.canvas.draw()
        else:
            # 如果matplotlib不可用，显示占位符
            placeholder = QLabel("净值曲线图已生成\n(需要安装matplotlib查看图表)")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("""
                QLabel {
                    background-color: #f0f0f0;
                    border: 2px dashed #ccc;
                    border-radius: 8px;
                    padding: 20px;
                    font-size: 14px;
                    color: #666;
                }
            """)
            layout.addWidget(placeholder)
    
    def plot_portfolio_curve(self, dates, values, initial_value=100000):
        """绘制投资组合净值曲线"""
        if not MATPLOTLIB_AVAILABLE or not dates or not values:
            return
            
        try:
            # 清除之前的图表
            self.ax.clear()
            
            # 计算净值（以初始资金为基准）
            net_values = [v / initial_value for v in values]
            
            # 绘制净值曲线
            self.ax.plot(dates, net_values, 'b-', linewidth=2, label='净值曲线')
            
            # 添加基准线
            self.ax.axhline(y=1.0, color='r', linestyle='--', alpha=0.7, label='基准线')
            
            # 设置图表样式
            self.ax.set_title('投资组合净值曲线', fontsize=14, fontweight='bold')
            self.ax.set_xlabel('日期')
            self.ax.set_ylabel('净值')
            self.ax.grid(True, alpha=0.3)
            self.ax.legend()
            
            # 格式化x轴日期
            if len(dates) > 10:
                self.ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=max(1, len(dates)//10)))
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            
            # 自动调整布局
            self.figure.tight_layout()
            
            # 刷新图表
            self.canvas.draw()
            
        except Exception as e:
            print(f"绘制净值曲线时出错: {e}")


class BacktestWidget(QWidget):
    """
    回测窗口主组件
    
    功能特性：
    1. 回测参数配置界面
    2. 实时回测进度显示
    3. 回测结果可视化
    4. HTML报告生成和导出
    5. 参数优化功能
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.backtest_worker = None
        self.current_results = None
        self.data_manager = DataManager()  # 初始化数据管理器
        
        self.init_ui()
        self.setup_connections()
        self.update_connection_status()  # 更新连接状态显示
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("📊 专业回测系统")
        self.setMinimumSize(1200, 800)
        
        # 主布局
        main_layout = QHBoxLayout(self)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧参数配置面板
        left_panel = self.create_parameter_panel()
        splitter.addWidget(left_panel)
        
        # 右侧结果显示面板
        right_panel = self.create_results_panel()
        splitter.addWidget(right_panel)
        
        # 设置分割比例
        splitter.setSizes([400, 800])
        
        # 应用样式
        self.apply_styles()
    
    def create_parameter_panel(self) -> QWidget:
        """创建参数配置面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 标题
        title_label = QLabel("🔧 回测参数配置")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 基础参数组
        basic_group = self.create_basic_params_group()
        layout.addWidget(basic_group)
        
        # 策略参数组
        strategy_group = self.create_strategy_params_group()
        layout.addWidget(strategy_group)
        
        # 高级参数组
        advanced_group = self.create_advanced_params_group()
        layout.addWidget(advanced_group)
        
        # 控制按钮
        control_group = self.create_control_buttons()
        layout.addWidget(control_group)
        
        # 进度显示
        progress_group = self.create_progress_group()
        layout.addWidget(progress_group)
        
        layout.addStretch()
        
        return panel
    
    def create_basic_params_group(self) -> QGroupBox:
        """创建基础参数组"""
        group = QGroupBox("📊 基础参数")
        layout = QGridLayout(group)
        
        # 股票代码
        layout.addWidget(QLabel("股票代码:"), 0, 0)
        self.stock_code_edit = QLineEdit("000001.SZ")
        layout.addWidget(self.stock_code_edit, 0, 1)
        
        # 开始日期
        layout.addWidget(QLabel("开始日期:"), 1, 0)
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate.currentDate().addYears(-1))
        self.start_date_edit.setCalendarPopup(True)
        layout.addWidget(self.start_date_edit, 1, 1)
        
        # 结束日期
        layout.addWidget(QLabel("结束日期:"), 2, 0)
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setCalendarPopup(True)
        layout.addWidget(self.end_date_edit, 2, 1)
        
        # 初始资金
        layout.addWidget(QLabel("初始资金:"), 3, 0)
        self.initial_cash_spin = QDoubleSpinBox()
        self.initial_cash_spin.setRange(10000, 10000000)
        self.initial_cash_spin.setValue(100000)
        self.initial_cash_spin.setSuffix(" 元")
        layout.addWidget(self.initial_cash_spin, 3, 1)
        
        # 手续费率
        layout.addWidget(QLabel("手续费率:"), 4, 0)
        self.commission_spin = QDoubleSpinBox()
        self.commission_spin.setRange(0.0001, 0.01)
        self.commission_spin.setValue(0.001)
        self.commission_spin.setDecimals(4)
        self.commission_spin.setSuffix("%")
        layout.addWidget(self.commission_spin, 4, 1)

        # 复权类型选择（第4行第2列）
        layout.addWidget(QLabel("复权类型:"), 4, 2)
        self.adjust_combo = QComboBox()
        self.adjust_combo.addItems([
            "不复权 (原始价格)",
            "前复权 (短期回测)",
            "后复权 (长期回测)"
        ])
        self.adjust_combo.setCurrentIndex(0)
        self.adjust_combo.setToolTip(
            "不复权：实时交易\n"
            "前复权：当前价真实，适合短期回测（1年内）\n"
            "后复权：历史价真实，适合长期回测（3年以上）"
        )
        layout.addWidget(self.adjust_combo, 4, 3)

        # 数据源选择（第5行）
        layout.addWidget(QLabel("数据源选择:"), 5, 0)
        self.data_source_combo = QComboBox()
        self.data_source_combo.addItems([
            "自动选择 (QMT→QStock→AKShare→模拟)",
            "强制QMT",
            "强制QStock",
            "强制AKShare",
            "强制模拟数据"
        ])
        self.data_source_combo.currentTextChanged.connect(self.on_data_source_changed)
        layout.addWidget(self.data_source_combo, 5, 1)

        # 数据源状态（第5行第2列）
        layout.addWidget(QLabel("数据源状态:"), 5, 2)
        self.data_source_label = QLabel("检测中...")
        self.data_source_label.setStyleSheet("color: orange; font-weight: bold;")
        layout.addWidget(self.data_source_label, 5, 3)

        # 刷新连接按钮（第5行第3列）
        self.refresh_connection_btn = QPushButton("🔄 刷新")
        self.refresh_connection_btn.clicked.connect(self.refresh_connection_status)
        self.refresh_connection_btn.setToolTip("检查各数据源连接状态")
        layout.addWidget(self.refresh_connection_btn, 5, 4)
        
        return group
    
    def create_strategy_params_group(self) -> QGroupBox:
        """创建策略参数组"""
        group = QGroupBox("🎯 策略参数")
        layout = QGridLayout(group)
        
        # 策略选择
        layout.addWidget(QLabel("策略类型:"), 0, 0)
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["双均线策略", "RSI策略", "MACD策略"])
        layout.addWidget(self.strategy_combo, 0, 1)
        
        # 短期均线周期
        layout.addWidget(QLabel("短期均线:"), 1, 0)
        self.short_period_spin = QSpinBox()
        self.short_period_spin.setRange(3, 50)
        self.short_period_spin.setValue(5)
        layout.addWidget(self.short_period_spin, 1, 1)
        
        # 长期均线周期
        layout.addWidget(QLabel("长期均线:"), 2, 0)
        self.long_period_spin = QSpinBox()
        self.long_period_spin.setRange(10, 200)
        self.long_period_spin.setValue(20)
        layout.addWidget(self.long_period_spin, 2, 1)
        
        # RSI周期
        layout.addWidget(QLabel("RSI周期:"), 3, 0)
        self.rsi_period_spin = QSpinBox()
        self.rsi_period_spin.setRange(5, 50)
        self.rsi_period_spin.setValue(14)
        layout.addWidget(self.rsi_period_spin, 3, 1)
        
        return group
    
    def create_advanced_params_group(self) -> QGroupBox:
        """创建高级参数组"""
        group = QGroupBox("⚙️ 高级选项")
        layout = QGridLayout(group)
        
        # 参数优化
        self.optimize_checkbox = QCheckBox("启用参数优化")
        layout.addWidget(self.optimize_checkbox, 0, 0, 1, 2)
        
        # 基准比较
        self.benchmark_checkbox = QCheckBox("基准比较")
        layout.addWidget(self.benchmark_checkbox, 1, 0, 1, 2)
        
        # 风险分析
        self.risk_analysis_checkbox = QCheckBox("详细风险分析")
        self.risk_analysis_checkbox.setChecked(True)
        layout.addWidget(self.risk_analysis_checkbox, 2, 0, 1, 2)
        
        return group
    
    def create_control_buttons(self) -> QGroupBox:
        """创建控制按钮组"""
        group = QGroupBox("🎮 操作控制")
        layout = QVBoxLayout(group)
        
        # 开始回测按钮
        self.start_button = QPushButton("🚀 开始回测")
        self.start_button.setMinimumHeight(40)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        layout.addWidget(self.start_button)
        
        # 停止回测按钮
        self.stop_button = QPushButton("⏹️ 停止回测")
        self.stop_button.setMinimumHeight(40)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        layout.addWidget(self.stop_button)
        
        # 导出报告按钮
        self.export_button = QPushButton("📄 导出HTML报告")
        self.export_button.setMinimumHeight(40)
        self.export_button.setEnabled(False)
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        layout.addWidget(self.export_button)
        
        return group
    
    def create_progress_group(self) -> QGroupBox:
        """创建进度显示组"""
        group = QGroupBox("📊 执行状态")
        layout = QVBoxLayout(group)
        
        # 状态标签
        self.status_label = QLabel("💤 等待开始...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        return group
    
    def create_results_panel(self) -> QWidget:
        """创建结果显示面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 标题
        title_label = QLabel("📈 回测结果分析")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 创建标签页
        self.results_tabs = QTabWidget()
        
        # 性能概览标签页
        self.overview_tab = self.create_overview_tab()
        self.results_tabs.addTab(self.overview_tab, "📊 性能概览")
        
        # 详细指标标签页
        self.metrics_tab = self.create_metrics_tab()
        self.results_tabs.addTab(self.metrics_tab, "📈 详细指标")
        
        # 风险分析标签页
        self.risk_tab = self.create_risk_tab()
        self.results_tabs.addTab(self.risk_tab, "⚠️ 风险分析")
        
        # 交易记录标签页
        self.trades_tab = self.create_trades_tab()
        self.results_tabs.addTab(self.trades_tab, "💼 交易记录")
        
        layout.addWidget(self.results_tabs)
        
        return panel
    
    def create_overview_tab(self) -> QWidget:
        """创建性能概览标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 关键指标卡片
        cards_layout = QGridLayout()
        
        # 总收益率卡片
        self.total_return_card = self.create_metric_card("总收益率", "0.00%", "#4CAF50")
        cards_layout.addWidget(self.total_return_card, 0, 0)
        
        # 年化收益率卡片
        self.annual_return_card = self.create_metric_card("年化收益率", "0.00%", "#2196F3")
        cards_layout.addWidget(self.annual_return_card, 0, 1)
        
        # 夏普比率卡片
        self.sharpe_card = self.create_metric_card("夏普比率", "0.00", "#FF9800")
        cards_layout.addWidget(self.sharpe_card, 1, 0)
        
        # 最大回撤卡片
        self.drawdown_card = self.create_metric_card("最大回撤", "0.00%", "#f44336")
        cards_layout.addWidget(self.drawdown_card, 1, 1)
        
        layout.addLayout(cards_layout)
        
        # 净值曲线图表
        self.portfolio_chart = PortfolioChart()
        layout.addWidget(self.portfolio_chart)
        
        return tab
    
    def create_metric_card(self, title: str, value: str, color: str) -> QFrame:
        """创建指标卡片"""
        card = QFrame()
        card.setFrameStyle(QFrame.Box)
        card.setStyleSheet(f"""
            QFrame {{
                border: 2px solid {color};
                border-radius: 10px;
                background-color: white;
                padding: 10px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        
        # 标题
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px;")
        layout.addWidget(title_label)
        
        # 数值
        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 24px;")
        layout.addWidget(value_label)
        
        # 保存引用以便更新
        card.value_label = value_label
        
        return card
    
    def create_metrics_tab(self) -> QWidget:
        """创建详细指标标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 指标表格
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(2)
        self.metrics_table.setHorizontalHeaderLabels(["指标名称", "数值"])
        self.metrics_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.metrics_table)
        
        return tab
    
    def create_risk_tab(self) -> QWidget:
        """创建风险分析标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 风险报告文本
        self.risk_report_text = QTextEdit()
        self.risk_report_text.setReadOnly(True)
        self.risk_report_text.setFont(QFont("Consolas", 10))
        
        layout.addWidget(self.risk_report_text)
        
        return tab
    
    def create_trades_tab(self) -> QWidget:
        """创建交易记录标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 交易记录表格
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(6)
        self.trades_table.setHorizontalHeaderLabels([
            "日期", "操作", "价格", "数量", "金额", "收益"
        ])
        self.trades_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.trades_table)
        
        return tab
    
    def setup_connections(self):
        """设置信号连接"""
        self.start_button.clicked.connect(self.start_backtest)
        self.stop_button.clicked.connect(self.stop_backtest)
        self.export_button.clicked.connect(self.export_html_report)
    
    def on_data_source_changed(self, text: str):
        """数据源选择改变时的处理"""
        if DataSource is None:
            return
            
        # 根据选择设置数据源
        if "强制QMT" in text:
            self.data_manager.set_preferred_source(DataSource.QMT)
        elif "强制QStock" in text:
            self.data_manager.set_preferred_source(DataSource.QSTOCK)
        elif "强制AKShare" in text:
            self.data_manager.set_preferred_source(DataSource.AKSHARE)
        elif "强制模拟数据" in text:
            self.data_manager.set_preferred_source(DataSource.MOCK)
        else:  # 自动选择
            self.data_manager.set_preferred_source(None)
        
        # 更新状态显示
        self.update_connection_status()
    
    def apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #2196F3;
            }
        """)
    
    def start_backtest(self):
        """开始回测"""
        try:
            # 检查引擎是否可用
            if AdvancedBacktestEngine is None:
                QMessageBox.critical(self, "错误", "回测引擎不可用，请检查模块安装")
                return
            
            # 验证参数
            if not self.validate_parameters():
                return
            
            # 获取参数
            params = self.get_backtest_parameters()

            # 显示回测参数信息
            print(f"📊 开始回测:")
            print(f"  股票代码: {params['stock_code']}")
            print(f"  时间范围: {params['start_date']} ~ {params['end_date']}")
            print(f"  初始资金: {params['initial_cash']:,.0f} 元")
            print(f"  复权类型: {params['adjust']}")  # ← 添加复权信息
            
            # 更新UI状态
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.export_button.setEnabled(False)
            
            # 重置进度
            self.progress_bar.setValue(0)
            self.status_label.setText("🚀 准备开始回测...")
            
            # 创建并启动工作线程
            self.backtest_worker = BacktestWorker(params)
            self.backtest_worker.progress_updated.connect(self.update_progress)
            self.backtest_worker.status_updated.connect(self.update_status)
            self.backtest_worker.results_ready.connect(self.handle_results)
            self.backtest_worker.error_occurred.connect(self.handle_error)
            self.backtest_worker.finished.connect(self.backtest_finished)
            
            self.backtest_worker.start()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动回测失败: {str(e)}")
            self.backtest_finished()
    
    def stop_backtest(self):
        """停止回测"""
        if self.backtest_worker and self.backtest_worker.isRunning():
            self.backtest_worker.stop()
            self.status_label.setText("⏹️ 正在停止回测...")
    
    def validate_parameters(self) -> bool:
        """验证参数"""
        # 检查股票代码
        if not self.stock_code_edit.text().strip():
            QMessageBox.warning(self, "参数错误", "请输入股票代码")
            return False
        
        # 检查日期范围
        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()
        
        if start_date >= end_date:
            QMessageBox.warning(self, "参数错误", "开始日期必须早于结束日期")
            return False
        
        # 检查策略参数
        if self.short_period_spin.value() >= self.long_period_spin.value():
            QMessageBox.warning(self, "参数错误", "短期均线周期必须小于长期均线周期")
            return False
        
        return True
    
    def get_backtest_parameters(self) -> Dict[str, Any]:
        """获取回测参数（包含复权类型）"""
        # 获取复权类型
        adjust_map = {
            "不复权 (原始价格)": "none",
            "前复权 (短期回测)": "front",
            "后复权 (长期回测)": "back"
        }
        adjust_text = self.adjust_combo.currentText()
        adjust = adjust_map.get(adjust_text, "none")

        return {
            'stock_code': self.stock_code_edit.text().strip(),
            'start_date': self.start_date_edit.date().toPyDate().strftime('%Y-%m-%d'),
            'end_date': self.end_date_edit.date().toPyDate().strftime('%Y-%m-%d'),
            'initial_cash': self.initial_cash_spin.value(),
            'commission': self.commission_spin.value() / 100,  # 转换为小数
            'short_period': self.short_period_spin.value(),
            'long_period': self.long_period_spin.value(),
            'rsi_period': self.rsi_period_spin.value(),
            'adjust': adjust,  # ← 添加复权参数
            'optimize_enabled': self.optimize_checkbox.isChecked(),
            'benchmark_enabled': self.benchmark_checkbox.isChecked(),
            'risk_analysis_enabled': self.risk_analysis_checkbox.isChecked()
        }
    
    def update_progress(self, value: int):
        """更新进度"""
        self.progress_bar.setValue(value)
    
    def update_status(self, status: str):
        """更新状态"""
        self.status_label.setText(status)
    
    def handle_results(self, results: Dict[str, Any]):
        """处理回测结果"""
        self.current_results = results
        
        # 更新性能概览
        self.update_overview_tab(results)
        
        # 更新详细指标
        self.update_metrics_tab(results)
        
        # 更新风险分析
        self.update_risk_tab(results)
        
        # 更新交易记录
        self.update_trades_tab(results)
        
        # 启用导出按钮
        self.export_button.setEnabled(True)
    
    def handle_error(self, error_msg: str):
        """处理错误"""
        QMessageBox.critical(self, "回测错误", error_msg)
        self.status_label.setText(f"❌ 回测失败: {error_msg}")
    
    def backtest_finished(self):
        """回测完成"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        if self.backtest_worker:
            self.backtest_worker.deleteLater()
            self.backtest_worker = None
    
    def update_overview_tab(self, results: Dict[str, Any]):
        """更新性能概览标签页"""
        metrics = results.get('performance_metrics', {})
        
        # 更新指标卡片 - 使用更高精度显示
        self.total_return_card.value_label.setText(f"{metrics.get('total_return', 0):.4%}")
        self.annual_return_card.value_label.setText(f"{metrics.get('annualized_return', 0):.4%}")
        self.sharpe_card.value_label.setText(f"{metrics.get('sharpe_ratio', 0):.3f}")
        self.drawdown_card.value_label.setText(f"{metrics.get('max_drawdown', 0):.4%}")
        
        # 更新净值曲线图表
        try:
            portfolio_curve = results.get('portfolio_curve', {})
            if portfolio_curve and 'dates' in portfolio_curve and 'values' in portfolio_curve:
                dates = portfolio_curve['dates']
                values = portfolio_curve['values']
                initial_value = results.get('backtest_params', {}).get('initial_cash', 100000)
                
                # 绘制净值曲线
                self.portfolio_chart.plot_portfolio_curve(dates, values, initial_value)
            else:
                print("⚠️ 没有找到有效的投资组合曲线数据")
        except Exception as e:
            print(f"更新净值曲线时出错: {e}")
    
    def update_metrics_tab(self, results: Dict[str, Any]):
        """更新详细指标标签页"""
        metrics = results.get('performance_metrics', {})
        risk_metrics = results.get('risk_analysis', {})
        
        # 合并所有指标
        all_metrics = {**metrics, **risk_metrics}
        
        # 设置表格行数
        self.metrics_table.setRowCount(len(all_metrics))
        
        # 填充数据
        for i, (key, value) in enumerate(all_metrics.items()):
            # 指标名称
            name_item = QTableWidgetItem(self.format_metric_name(key))
            self.metrics_table.setItem(i, 0, name_item)
            
            # 指标数值
            value_item = QTableWidgetItem(self.format_metric_value(key, value))
            self.metrics_table.setItem(i, 1, value_item)
    
    def update_risk_tab(self, results: Dict[str, Any]):
        """更新风险分析标签页"""
        risk_analysis = results.get('risk_analysis', {})
        
        # 生成风险报告
        risk_analyzer = RiskAnalyzer()
        risk_report = risk_analyzer.generate_risk_report(risk_analysis)
        
        self.risk_report_text.setPlainText(risk_report)
    
    def update_trades_tab(self, results: Dict[str, Any]):
        """更新交易记录标签页"""
        # 从回测结果中提取真实的交易记录
        detailed_results = results.get('detailed_results', {})
        trades_data = detailed_results.get('trades', [])
        
        # 如果没有交易记录，显示提示信息
        if not trades_data:
            trades_data = [("无交易记录", "请检查策略参数", "", "", "", "")]
        
        self.trades_table.setRowCount(len(trades_data))
        
        for i, trade in enumerate(trades_data):
            for j, value in enumerate(trade):
                item = QTableWidgetItem(str(value))
                # 根据操作类型设置颜色
                if j == 1:  # 操作列
                    if str(value) == "买入":
                        item.setBackground(QColor(220, 255, 220))  # 浅绿色
                    elif str(value) == "卖出":
                        item.setBackground(QColor(255, 220, 220))  # 浅红色
                # 根据收益设置颜色
                elif j == 5 and str(value).startswith(('+', '-')):  # 收益列
                    if str(value).startswith('+'):
                        item.setBackground(QColor(220, 255, 220))  # 浅绿色
                    elif str(value).startswith('-'):
                        item.setBackground(QColor(255, 220, 220))  # 浅红色
                
                self.trades_table.setItem(i, j, item)
    
    def format_metric_name(self, key: str) -> str:
        """格式化指标名称"""
        name_mapping = {
            'total_return': '总收益率',
            'annualized_return': '年化收益率',
            'volatility': '年化波动率',
            'sharpe_ratio': '夏普比率',
            'max_drawdown': '最大回撤',
            'win_rate': '胜率',
            'profit_factor': '盈利因子',
            'sqn': 'SQN指标',
            'sortino_ratio': '索提诺比率',
            'calmar_ratio': '卡尔马比率',
            'var_95': '95% VaR',
            'cvar_95': '95% CVaR'
        }
        return name_mapping.get(key, key.replace('_', ' ').title())
    
    def format_metric_value(self, key: str, value: Any) -> str:
        """格式化指标数值"""
        if isinstance(value, (int, float)):
            if 'return' in key or 'drawdown' in key or 'var' in key or 'cvar' in key or 'rate' in key:
                return f"{value:.4%}"
            elif 'ratio' in key or 'factor' in key or 'sqn' in key:
                return f"{value:.3f}"
            else:
                return f"{value:.2f}"
        else:
            return str(value)
    
    def export_html_report(self):
        """导出HTML报告"""
        if not self.current_results:
            QMessageBox.warning(self, "导出失败", "没有可导出的回测结果")
            return
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存HTML报告", 
            f"回测报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            "HTML文件 (*.html)"
        )
        
        if file_path:
            try:
                # 生成HTML报告
                html_content = self.generate_html_report(self.current_results)
                
                # 保存文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                QMessageBox.information(self, "导出成功", f"HTML报告已保存到:\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"保存HTML报告失败: {str(e)}")
    
    def generate_html_report(self, results: Dict[str, Any]) -> str:
        """生成HTML报告"""
        # 这里应该使用专业的HTML模板生成器
        # 目前返回简单的HTML内容
        
        metrics = results.get('performance_metrics', {})
        risk_analysis = results.get('risk_analysis', {})
        params = results.get('backtest_params', {})
        
        html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>回测报告 - {params.get('stock_code', 'N/A')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .section {{ margin-bottom: 30px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
        .metric-card {{ border: 1px solid #ddd; padding: 15px; border-radius: 5px; text-align: center; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #2196F3; }}
        .metric-label {{ color: #666; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 回测报告</h1>
        <p>股票代码: {params.get('stock_code', 'N/A')} | 
           回测期间: {params.get('start_date', 'N/A')} ~ {params.get('end_date', 'N/A')}</p>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="section">
        <h2>📈 关键指标</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{metrics.get('total_return', 0):.4%}</div>
                <div class="metric-label">总收益率</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{metrics.get('sharpe_ratio', 0):.2f}</div>
                <div class="metric-label">夏普比率</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{metrics.get('max_drawdown', 0):.4%}</div>
                <div class="metric-label">最大回撤</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{metrics.get('win_rate', 0):.2%}</div>
                <div class="metric-label">胜率</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>📊 详细指标</h2>
        <table>
            <tr><th>指标名称</th><th>数值</th></tr>
            <tr><td>总收益率</td><td>{metrics.get('total_return', 0):.4%}</td></tr>
            <tr><td>年化收益率</td><td>{metrics.get('annualized_return', 0):.4%}</td></tr>
            <tr><td>年化波动率</td><td>{metrics.get('volatility', 0):.4%}</td></tr>
            <tr><td>夏普比率</td><td>{metrics.get('sharpe_ratio', 0):.3f}</td></tr>
            <tr><td>最大回撤</td><td>{metrics.get('max_drawdown', 0):.4%}</td></tr>
            <tr><td>胜率</td><td>{metrics.get('win_rate', 0):.2%}</td></tr>
            <tr><td>盈利因子</td><td>{metrics.get('profit_factor', 0):.2f}</td></tr>
        </table>
    </div>
    
    <div class="section">
        <h2>⚙️ 回测参数</h2>
        <table>
            <tr><th>参数名称</th><th>参数值</th></tr>
            <tr><td>股票代码</td><td>{params.get('stock_code', 'N/A')}</td></tr>
            <tr><td>回测期间</td><td>{params.get('start_date', 'N/A')} ~ {params.get('end_date', 'N/A')}</td></tr>
            <tr><td>初始资金</td><td>{params.get('initial_cash', 0):,.0f} 元</td></tr>
            <tr><td>手续费率</td><td>{params.get('commission', 0):.4f}</td></tr>
            <tr><td>短期均线</td><td>{params.get('short_period', 'N/A')} 日</td></tr>
            <tr><td>长期均线</td><td>{params.get('long_period', 'N/A')} 日</td></tr>
            <tr><td>RSI周期</td><td>{params.get('rsi_period', 'N/A')} 日</td></tr>
        </table>
    </div>
    
    <div class="section">
        <h2>📝 免责声明</h2>
        <p>本报告仅供参考，不构成投资建议。历史业绩不代表未来表现，投资有风险，入市需谨慎。</p>
    </div>
</body>
</html>
        """
        
        return html_template
    
    def update_connection_status(self):
        """更新连接状态显示"""
        try:
            status = self.data_manager.get_connection_status()
            active_source = status.get('active_source', 'mock')
            
            # 根据活跃数据源设置显示
            if active_source == 'qmt':
                self.data_source_label.setText("✅ QMT已连接 (真实数据)")
                self.data_source_label.setStyleSheet("color: green; font-weight: bold;")
            elif active_source == 'duckdb':
                self.data_source_label.setText("✅ DuckDB数据库 (真实数据)")
                self.data_source_label.setStyleSheet("color: green; font-weight: bold;")
            elif active_source == 'local':
                self.data_source_label.setText("✅ 本地缓存 (真实数据)")
                self.data_source_label.setStyleSheet("color: green; font-weight: bold;")
            elif active_source == 'qstock':
                self.data_source_label.setText("✅ QStock已连接 (真实数据)")
                self.data_source_label.setStyleSheet("color: green; font-weight: bold;")
            elif active_source == 'akshare':
                self.data_source_label.setText("✅ AKShare已连接 (真实数据)")
                self.data_source_label.setStyleSheet("color: green; font-weight: bold;")
            elif active_source == 'mock':
                self.data_source_label.setText("🎲 使用模拟数据")
                self.data_source_label.setStyleSheet("color: orange; font-weight: bold;")
            else:
                # 未知数据源
                self.data_source_label.setText(f"❓ 数据源: {active_source}")
                self.data_source_label.setStyleSheet("color: gray; font-weight: bold;")
            
            # 显示详细状态信息
            source_status = status.get('source_status', {})
            status_details = []
            for source_name, source_info in source_status.items():
                if source_info['available']:
                    if source_info['connected']:
                        status_details.append(f"{source_name.upper()}:✅")
                    else:
                        status_details.append(f"{source_name.upper()}:⚠️")
                else:
                    status_details.append(f"{source_name.upper()}:❌")
            
            tooltip_text = "数据源状态:\
" + "\
".join(status_details)
            self.data_source_label.setToolTip(tooltip_text)
                
        except Exception as e:
            self.data_source_label.setText("❓ 状态检测失败")
            self.data_source_label.setStyleSheet("color: gray; font-weight: bold;")
            print(f"连接状态检测失败: {e}")

    def refresh_connection_status(self):
        """刷新连接状态"""
        self.data_source_label.setText("🔄 检测中...")
        self.data_source_label.setStyleSheet("color: blue; font-weight: bold;")
        
        # 刷新数据管理器状态
        if self.data_manager:
            self.data_manager.refresh_source_status()
        else:
            # 重新初始化数据管理器
            self.data_manager = DataManager()
        
        # 更新状态显示
        QTimer.singleShot(1000, self.update_connection_status)  # 延迟1秒更新


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # 创建回测窗口
    backtest_widget = BacktestWidget()
    backtest_widget.show()
    
    sys.exit(app.exec_())