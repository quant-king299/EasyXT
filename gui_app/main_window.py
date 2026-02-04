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
project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_path)

# 尝试导入easy_xt
try:
    import easy_xt
    EASYXT_AVAILABLE = True
except ImportError:
    EASYXT_AVAILABLE = False
    print("警告: easy_xt未安装，部分功能将不可用")

# 导入各个功能组件
from gui_app.widgets.backtest_widget import BacktestWidget
from gui_app.widgets.jq2qmt_widget import JQ2QMTWidget
from gui_app.widgets.jq_to_ptrade_widget import JQToPtradeWidget
from gui_app.widgets.grid_trading_widget import GridTradingWidget
from gui_app.widgets.conditional_order_widget import ConditionalOrderWidget
from gui_app.widgets.local_data_manager_widget import LocalDataManagerWidget
from gui_app.widgets.advanced_data_viewer_widget import AdvancedDataViewerWidget


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
        self.data_manager_widget = LocalDataManagerWidget()
        data_manager_layout.addWidget(self.data_manager_widget)
        self.tab_widget.addTab(data_manager_tab, "📊 数据管理")

        # 高级数据查看器标签页
        advanced_viewer_tab = QWidget()
        advanced_viewer_layout = QVBoxLayout(advanced_viewer_tab)
        self.advanced_data_viewer_widget = AdvancedDataViewerWidget()
        advanced_viewer_layout.addWidget(self.advanced_data_viewer_widget)
        self.tab_widget.addTab(advanced_viewer_tab, "📈 数据查看器")
        
    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 添加连接状态指示器
        self.connection_status = QLabel("🔴 MiniQMT未连接")
        self.connection_status.setStyleSheet("""
            QLabel {
                background-color: #ff4444;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QLabel:hover {
                background-color: #ff6666;
                cursor: pointer;
            }
        """)
        # 添加提示文本
        self.connection_status.setToolTip("点击刷新连接状态")
        # 连接鼠标点击事件
        self.connection_status.mousePressEvent = self.on_connection_status_clicked
        
        self.status_bar.addPermanentWidget(self.connection_status)
        self.status_bar.showMessage("就绪")

        # 检查MiniQMT连接状态（启动时延迟1秒检查）
        QTimer.singleShot(1000, self.check_connection_status)

        # 定期检查连接状态（每30秒检查一次）
        self.connection_check_timer = QTimer()
        self.connection_check_timer.timeout.connect(self.check_connection_status)
        self.connection_check_timer.start(30000)  # 30秒

    def on_connection_status_clicked(self, event):
        """连接状态标签被点击事件"""
        print("手动刷新连接状态...")
        self.check_connection_status()

    def check_connection_status(self):
        """检查MiniQMT连接状态"""
        print("\n" + "="*60)
        print("开始检查MiniQMT连接状态...")
        print("="*60)

        try:
            # 检查easy_xt是否可用
            if not EASYXT_AVAILABLE:
                print("❌ EasyXT不可用")
                self.update_connection_status(False)
                return

            print("✓ EasyXT可用")

            try:
                api = easy_xt.get_api()
                print("✓ 成功获取API实例")
            except Exception as e:
                print(f"❌ 获取API失败: {str(e)}")
                self.update_connection_status(False)
                return

            # 检查data服务
            if not hasattr(api, 'data'):
                print("❌ API没有data属性")
                self.update_connection_status(False)
                return

            print("✓ API有data属性")

            # 尝试初始化数据服务
            print("\n尝试初始化数据服务...")
            try:
                if hasattr(api, 'init_data'):
                    init_result = api.init_data()
                    print(f"  init_data() 返回: {init_result}")

                    if init_result:
                        print("✓ 数据服务初始化成功")
                    else:
                        print("⚠ 数据服务初始化返回False，但继续尝试获取数据...")
                else:
                    print("⚠ API没有init_data方法，直接尝试获取数据")
            except Exception as e:
                print(f"⚠ 初始化数据服务时出现异常: {str(e)}")
                print("  继续尝试获取数据...")

            # 尝试获取行情数据来验证连接
            test_codes = ['511090.SH', '000001.SZ']
            connected = False

            for code in test_codes:
                try:
                    print(f"\n尝试获取 {code} 的行情数据...")
                    price_df = api.data.get_current_price([code])

                    print(f"  返回类型: {type(price_df)}")
                    print(f"  是否为None: {price_df is None}")

                    if price_df is not None:
                        print(f"  是否为空: {price_df.empty if hasattr(price_df, 'empty') else 'N/A'}")
                        print(f"  长度: {len(price_df) if hasattr(price_df, '__len__') else 'N/A'}")

                        if hasattr(price_df, 'empty') and not price_df.empty:
                            connected = True
                            print(f"✓ 连接验证成功：通过{code}获取到行情数据")
                            print(f"  数据预览:\n{price_df.head()}")
                            break
                        else:
                            print(f"  返回为空DataFrame")
                    else:
                        print(f"  返回为None")

                except Exception as e:
                    print(f"  ❌ 获取{code}行情异常: {str(e)}")
                    import traceback
                    print(f"  详细错误: {traceback.format_exc()}")
                    continue

            print("\n" + "="*60)
            if connected:
                print("✅ 最终结果: MiniQMT已连接")
            else:
                print("❌ 最终结果: MiniQMT未连接")
            print("="*60 + "\n")

            self.update_connection_status(connected)

        except Exception as e:
            print(f"\n❌ 检查连接状态异常: {str(e)}")
            import traceback
            print(f"详细错误堆栈:\n{traceback.format_exc()}")
            print("="*60 + "\n")
            self.update_connection_status(False)

    def update_connection_status(self, connected: bool):
        """更新连接状态显示

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
            self.status_bar.showMessage("MiniQMT已连接")
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
            self.status_bar.showMessage("MiniQMT未连接，请检查QMT客户端是否启动")

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