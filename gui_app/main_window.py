#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import easy_xt

# 导入各个功能组件
from widgets.backtest_widget import BacktestWidget
from widgets.jq2qmt_widget import JQ2QMTWidget
from widgets.jq_to_ptrade_widget import JQToPtradeWidget


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
        # 回测分析标签页
        backtest_tab = QWidget()
        backtest_layout = QVBoxLayout(backtest_tab)
        self.backtest_widget = BacktestWidget()
        backtest_layout.addWidget(self.backtest_widget)
        self.tab_widget.addTab(backtest_tab, "回测分析")
        
        # 聚宽到Ptrade转换标签页
        jq_to_ptrade_tab = QWidget()
        jq_to_ptrade_layout = QVBoxLayout(jq_to_ptrade_tab)
        self.jq_to_ptrade_widget = JQToPtradeWidget()
        jq_to_ptrade_layout.addWidget(self.jq_to_ptrade_widget)
        self.tab_widget.addTab(jq_to_ptrade_tab, "JQ转Ptrade")
        
    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 添加连接状态指示器
        self.connection_status = QLabel("MiniQMT未连接")
        self.connection_status.setStyleSheet("""
            QLabel {
                background-color: #ff4444;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
            }
        """)
        
        self.status_bar.addPermanentWidget(self.connection_status)
        self.status_bar.showMessage("就绪")
        
    def closeEvent(self, a0):
        """关闭事件"""
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