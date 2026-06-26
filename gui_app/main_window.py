# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger(__name__)
#!/usr/bin/env python3
"""
EasyXT量化交易策略管理平台
基于PyQt5的专业量化交易策略参数设置和管理界面
用于策略开发、参数配置、实时监控和交易执行
"""

import sys
import os
import json
import traceback
import importlib.util
from datetime import datetime
from typing import Dict, Any, Optional, List

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QTextEdit, QLabel, QPushButton, QComboBox,
    QSpinBox, QDoubleSpinBox, QSlider, QGroupBox, QGridLayout,
    QListWidget, QListWidgetItem, QProgressBar, QStatusBar,
    QMenuBar, QAction, QMessageBox, QFileDialog, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
    QLineEdit, QFormLayout, QTreeWidget, QTreeWidgetItem,
    QDockWidget, QToolBar, QFrame, QSizePolicy, QDateTimeEdit,
    QTimeEdit, QDateEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSettings, QSize, QDateTime
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor, QPixmap

import pandas as pd
import numpy as np

try:
    import pyqtgraph as pg
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False

try:
    # 修复导入错误
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# 添加项目路径
project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_path)

# 尝试导入easy_xt
try:
    import easy_xt
    EASYXT_AVAILABLE = True
except ImportError:
    EASYXT_AVAILABLE = False
    logger.info("警告: easy_xt未安装，部分功能将不可用")

# 导入各个功能组件
from gui_app.widgets.jq2qmt_widget import JQ2QMTWidget
from gui_app.widgets.jq_to_ptrade_widget import JQToPtradeWidget, CONVERTER_AVAILABLE
from gui_app.widgets.grid_trading_widget import GridTradingWidget
from gui_app.widgets.conditional_order_widget import ConditionalOrderWidget
from gui_app.widgets.local_data_manager_widget import LocalDataManagerWidget
from gui_app.widgets.duckdb_local_data_manager_widget import DuckDBLocalDataManagerWidget
from gui_app.widgets.advanced_data_viewer_widget import AdvancedDataViewerWidget
from gui_app.widgets.tushare_data_widget import TushareDataWidget
from gui_app.widgets.multi_strategy_widget import MultiStrategyWidget


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.executor_thread = None
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("EasyXT量化交易策略管理平台")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页控件
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 创建各个功能标签页
        self.create_tabs()
        
        # 创建状态栏
        self.create_status_bar()
        
        # 设置窗口属性
        self.setWindowTitle("EasyXT量化交易策略管理平台")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(800, 600)
        
        # 设置默认标签页
        self.tab_widget.setCurrentIndex(0)
        
    def create_tabs(self):
        """创建各个功能标签页"""
        # 聚宽到Ptrade转换标签页（仅转换器可用时显示）
        if CONVERTER_AVAILABLE:
            jq_to_ptrade_tab = QWidget()
            jq_to_ptrade_layout = QVBoxLayout(jq_to_ptrade_tab)
            self.jq_to_ptrade_widget = JQToPtradeWidget()
            jq_to_ptrade_layout.addWidget(self.jq_to_ptrade_widget)
            self.tab_widget.addTab(jq_to_ptrade_tab, "JQ转Ptrade")

        # 网格交易标签页
        grid_trading_tab = QWidget()
        grid_trading_layout = QVBoxLayout(grid_trading_tab)
        self.grid_trading_widget = GridTradingWidget()
        grid_trading_layout.addWidget(self.grid_trading_widget)
        self.tab_widget.addTab(grid_trading_tab, "网格交易")

        # 条件单标签页
        conditional_order_tab = QWidget()
        conditional_order_layout = QVBoxLayout(conditional_order_tab)
        self.conditional_order_widget = ConditionalOrderWidget()
        conditional_order_layout.addWidget(self.conditional_order_widget)
        self.tab_widget.addTab(conditional_order_tab, "条件单")

        # 本地数据管理标签页
        data_manager_tab = QWidget()
        data_manager_layout = QVBoxLayout(data_manager_tab)
        # 选择数据管理器版本（取消注释想要使用的版本）
        self.data_manager_widget = LocalDataManagerWidget()  # 旧版UI + DuckDB底层（完美方案）
        data_manager_layout.addWidget(self.data_manager_widget)
        self.tab_widget.addTab(data_manager_tab, "📊 数据管理")

        # 高级数据查看器标签页
        advanced_viewer_tab = QWidget()
        advanced_viewer_layout = QVBoxLayout(advanced_viewer_tab)
        self.advanced_data_viewer_widget = AdvancedDataViewerWidget()
        advanced_viewer_layout.addWidget(self.advanced_data_viewer_widget)
        self.tab_widget.addTab(advanced_viewer_tab, "📈 数据查看器")

        # Tushare数据下载标签页
        tushare_data_tab = QWidget()
        tushare_data_layout = QVBoxLayout(tushare_data_tab)
        self.tushare_data_widget = TushareDataWidget()
        tushare_data_layout.addWidget(self.tushare_data_widget)
        self.tab_widget.addTab(tushare_data_tab, "📥 Tushare下载")

        # 多策略管理标签页
        multi_strategy_tab = QWidget()
        multi_strategy_layout = QVBoxLayout(multi_strategy_tab)
        self.multi_strategy_widget = MultiStrategyWidget()
        multi_strategy_layout.addWidget(self.multi_strategy_widget)
        self.tab_widget.addTab(multi_strategy_tab, "🚀 多策略管理")

    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # ── 大QMT 状态标签 ──
        self.big_qmt_status = QLabel("🔴 大QMT未检测")
        self.big_qmt_status.setStyleSheet("""
            QLabel {
                background-color: #ff4444;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
            }
        """)
        self.big_qmt_status.setToolTip("大QMT (XtItClient.exe) 运行状态\n大QMT 或 miniQMT 登录一个即可")
        self.big_qmt_status.mousePressEvent = lambda e: self.check_connection_status()
        self.status_bar.addPermanentWidget(self.big_qmt_status)

        # ── MiniQMT 状态标签 ──
        self.connection_status = QLabel("🔴 MiniQMT未连接")
        self.connection_status.setStyleSheet("""
            QLabel {
                background-color: #ff4444;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
            }
        """)
        self.connection_status.setToolTip("MiniQMT 数据连接状态\n点击刷新")
        self.connection_status.mousePressEvent = self.on_connection_status_clicked
        self.status_bar.addPermanentWidget(self.connection_status)

        self.status_bar.showMessage("就绪")

        # 启动时延迟1秒检查
        QTimer.singleShot(1000, self.check_connection_status)

        # 定期检查（每30秒一次，任意一个连上后自动停止）
        self.connection_check_timer = QTimer()
        self.connection_check_timer.timeout.connect(self.check_connection_status)
        self.connection_check_timer.start(30000)  # 30秒

    def on_connection_status_clicked(self, event):
        """连接状态标签被点击事件"""
        logger.info("手动刷新连接状态...")
        self.check_connection_status()

    def _check_big_qmt(self) -> bool:
        """
        检测大QMT是否在运行（纯 tasklist，瞬时完成）

        Returns:
            bool: 大QMT (XtItClient.exe) 是否正在运行
        """
        try:
            from core.auto_login.qmt_login import QMTAutoLogin
            auto = QMTAutoLogin()
            # 只用 tasklist，不碰 pywinauto（启动时 pywinauto UIA 初始化需 ~15s）
            return auto._is_big_qmt_process_only()
        except Exception as e:
            logger.debug(f"大QMT检测失败: {e}")
            return False

    def check_connection_status(self):
        """检查 QMT 连接状态（大QMT + MiniQMT）"""
        # ── 1. 先检测大QMT（轻量，不卡）──
        big_qmt_ok = self._check_big_qmt()
        self._update_big_qmt_status(big_qmt_ok)

        # ── 2. 如果大QMT已连，跳过 miniQMT 重检测，停止定时器 ──
        if big_qmt_ok:
            logger.info("✅ 大QMT已运行，跳过 miniQMT 检测")
            self.connection_status.setText("⚪ MiniQMT (大QMT已接管)")
            self.connection_status.setStyleSheet("""
                QLabel {
                    background-color: #888888;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-weight: bold;
                }
            """)
            # 停止定时器——大QMT已连接，不再反复检测
            self.connection_check_timer.stop()
            self.status_bar.showMessage("大QMT已连接 ✓")
            return

        # ── 3. 大QMT未连，检测 MiniQMT ──
        logger.info("大QMT未运行，开始检查MiniQMT...")
        mini_connected = False

        try:
            if not EASYXT_AVAILABLE:
                self.update_connection_status(False)
                return

            api = easy_xt.get_api()

            if not hasattr(api, 'data'):
                self.update_connection_status(False)
                return

            # 初始化数据服务
            try:
                api.init_data()
            except Exception:
                pass

            # 验证数据连接（只测一只股票，减少等待）
            try:
                price_df = api.data.get_current_price(['000001.SZ'])
                if price_df is not None and hasattr(price_df, 'empty') and not price_df.empty:
                    mini_connected = True
            except Exception:
                pass

            # ── 4. MiniQMT 连上了也停止定时器 ──
            if mini_connected:
                self.connection_check_timer.stop()
                self.status_bar.showMessage("MiniQMT已连接 ✓")
            else:
                self.status_bar.showMessage("QMT未连接，请启动大QMT或MiniQMT")

        except Exception as e:
            logger.debug(f"MiniQMT检测异常: {e}")

        self.update_connection_status(mini_connected)

    def _update_big_qmt_status(self, running: bool):
        """更新大QMT状态标签"""
        if running:
            self.big_qmt_status.setText("🟢 大QMT已运行")
            self.big_qmt_status.setStyleSheet("""
                QLabel {
                    background-color: #00cc00;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-weight: bold;
                }
            """)
        else:
            self.big_qmt_status.setText("🔴 大QMT未检测")
            self.big_qmt_status.setStyleSheet("""
                QLabel {
                    background-color: #ff4444;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-weight: bold;
                }
            """)

    def update_connection_status(self, connected: bool):
        """更新MiniQMT连接状态显示

        Args:
            connected: 是否已连接
        """
        if connected:
            self.connection_status.setText("🟢 MiniQMT已连接")
            self.connection_status.setStyleSheet("""
                QLabel {
                    background-color: #00cc00;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-weight: bold;
                }
            """)
        else:
            self.connection_status.setText("🔴 MiniQMT未连接")
            self.connection_status.setStyleSheet("""
                QLabel {
                    background-color: #ff4444;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-weight: bold;
                }
            """)

    def closeEvent(self, a0):
        """关闭事件"""
        # 停止连接检查定时器
        if hasattr(self, 'connection_check_timer'):
            self.connection_check_timer.stop()
        a0.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("EasyXT量化交易策略管理平台")
    app.setApplicationVersion("3.0")
    app.setOrganizationName("EasyXT")
    
    # 设置应用程序字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    # 设置样式
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f0f0f0;
        }
        QTabWidget::pane {
            border: 1px solid #c0c0c0;
            background-color: white;
        }
        QTabBar::tab {
            background-color: #e0e0e0;
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        }
        QTabBar::tab:selected {
            background-color: white;
            border-bottom: 2px solid #2196F3;
        }
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
        QPushButton {
            padding: 6px 12px;
            border-radius: 4px;
            border: 1px solid #ccc;
            background-color: #f0f0f0;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
        }
        QPushButton:pressed {
            background-color: #d0d0d0;
        }
    """)
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()