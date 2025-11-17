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
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
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

# 导入数据管理器用于连接状态检测
try:
    from backtest.data_manager import DataManager
    DATA_MANAGER_AVAILABLE = True
except ImportError:
    DATA_MANAGER_AVAILABLE = False
    print("⚠️ 数据管理器不可用，将使用简化的连接检测")

# 导入各个功能组件
from widgets.backtest_widget import BacktestWidget
from widgets.jq2qmt_widget import JQ2QMTWidget
from widgets.jq_to_ptrade_widget import JQToPtradeWidget
from backtest.monitor_widget import MonitorWidget
from trading_widget import TradingWidget
from strategy_executor import StrategyExecutorThread
from strategy_monitor import StrategyMonitorWidget
from strategy_control import StrategyControlWidget
from strategy_parameter import StrategyParameterWidget


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.executor_thread = None
        self.init_ui()
        self.setup_connections()
        
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
        
        # 启动定时器更新状态
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(5000)  # 每5秒更新一次
        
    def create_tabs(self):
        """创建各个功能标签页"""
        # 策略参数配置标签页
        strategy_tab = QWidget()
        strategy_layout = QVBoxLayout(strategy_tab)
        self.strategy_param_widget = StrategyParameterWidget()
        strategy_layout.addWidget(self.strategy_param_widget)
        self.tab_widget.addTab(strategy_tab, "策略参数")
        
        # 回测分析标签页
        backtest_tab = QWidget()
        backtest_layout = QVBoxLayout(backtest_tab)
        self.backtest_widget = BacktestWidget()
        backtest_layout.addWidget(self.backtest_widget)
        self.tab_widget.addTab(backtest_tab, "回测分析")
        
        # 实盘交易标签页
        trading_tab = QWidget()
        trading_layout = QVBoxLayout(trading_tab)
        self.trading_widget = TradingWidget()
        trading_layout.addWidget(self.trading_widget)
        self.tab_widget.addTab(trading_tab, "实盘交易")
        
        # 聚宽到QMT集成标签页
        try:
            from adapters.jq2qmt_adapter import EasyXTJQ2QMTAdapter
            JQ2QMT_AVAILABLE = True
        except ImportError:
            JQ2QMT_AVAILABLE = False
            
        if JQ2QMT_AVAILABLE:
            jq2qmt_tab = QWidget()
            jq2qmt_layout = QVBoxLayout(jq2qmt_tab)
            self.jq2qmt_widget = JQ2QMTWidget()
            jq2qmt_layout.addWidget(self.jq2qmt_widget)
            self.tab_widget.addTab(jq2qmt_tab, "JQ2QMT集成")
        
        # 聚宽到Ptrade转换标签页
        jq_to_ptrade_tab = QWidget()
        jq_to_ptrade_layout = QVBoxLayout(jq_to_ptrade_tab)
        self.jq_to_ptrade_widget = JQToPtradeWidget()
        jq_to_ptrade_layout.addWidget(self.jq_to_ptrade_widget)
        self.tab_widget.addTab(jq_to_ptrade_tab, "JQ转Ptrade")
        
        # 系统监控标签页
        monitor_tab = QWidget()
        monitor_layout = QVBoxLayout(monitor_tab)
        self.monitor_widget = MonitorWidget()
        monitor_layout.addWidget(self.monitor_widget)
        self.tab_widget.addTab(monitor_tab, "系统监控")
        
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
        
        # 添加刷新连接状态按钮
        refresh_btn = QPushButton("刷新连接")
        refresh_btn.setMaximumWidth(80)
        refresh_btn.clicked.connect(self.check_connection_status)
        self.status_bar.addPermanentWidget(refresh_btn)
        
        self.status_bar.addPermanentWidget(self.connection_status)
        self.status_bar.showMessage("就绪")
        
        # 创建连接检查定时器
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self.check_connection_status)
        self.connection_timer.start(30000)  # 每30秒检查一次
        
        # 初始检查连接状态
        self.check_connection_status()
        
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_strategy_action = QAction('新建策略', self)
        new_strategy_action.setShortcut('Ctrl+N')
        new_strategy_action.triggered.connect(self.strategy_param_widget.create_new_strategy)
        file_menu.addAction(new_strategy_action)
        
        load_params_action = QAction('加载参数', self)
        load_params_action.setShortcut('Ctrl+O')
        load_params_action.triggered.connect(self.strategy_param_widget.load_parameters)
        file_menu.addAction(load_params_action)
        
        save_params_action = QAction('保存参数', self)
        save_params_action.setShortcut('Ctrl+S')
        save_params_action.triggered.connect(self.strategy_param_widget.save_parameters)
        file_menu.addAction(save_params_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 策略菜单
        strategy_menu = menubar.addMenu('策略')
        
        start_action = QAction('启动策略', self)
        start_action.setShortcut('F5')
        start_action.triggered.connect(lambda: self.start_strategy(None, None))
        strategy_menu.addAction(start_action)
        
        stop_action = QAction('停止策略', self)
        stop_action.setShortcut('F6')
        stop_action.triggered.connect(self.stop_strategy)
        strategy_menu.addAction(stop_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        refresh_strategies_action = QAction('刷新策略列表', self)
        refresh_strategies_action.triggered.connect(self.strategy_param_widget.refresh_strategy_list)
        tools_menu.addAction(refresh_strategies_action)
        
        tools_menu.addSeparator()
        
        # 回测功能
        backtest_action = QAction('📊 专业回测', self)
        backtest_action.setShortcut('Ctrl+B')
        backtest_action.triggered.connect(self.open_backtest_window)
        tools_menu.addAction(backtest_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def setup_connections(self):
        """设置信号连接"""
        # 参数变化信号
        self.strategy_param_widget.parameter_changed.connect(self.on_parameter_changed)
        
    def start_strategy(self, strategy_name, params):
        """启动策略"""
        if self.executor_thread and self.executor_thread.isRunning():
            QMessageBox.warning(self, "警告", "策略正在运行中")
            return
            
        # 获取当前策略和参数
        current_strategy = self.strategy_param_widget.current_strategy
        current_params = self.strategy_param_widget.get_current_parameters()
        
        if not current_strategy:
            QMessageBox.warning(self, "警告", "请先选择策略")
            return
            
        # 创建执行线程
        self.executor_thread = StrategyExecutorThread(current_strategy, current_params)
        
        # 连接信号
        self.executor_thread.status_update.connect(self.update_status)
        self.executor_thread.log_message.connect(self.append_log)
        self.executor_thread.error_message.connect(self.append_error_log)
        
        # 启动线程
        self.executor_thread.start()
        self.status_bar.showMessage("策略运行中...")
        
    def stop_strategy(self):
        """停止策略"""
        if self.executor_thread and self.executor_thread.isRunning():
            self.executor_thread.stop()
            self.executor_thread.wait()
            
        self.status_bar.showMessage("策略已停止")
        
    def on_parameter_changed(self, strategy_name, params):
        """参数改变处理"""
        pass
        
    def append_log(self, message):
        """添加日志"""
        pass
        
    def append_error_log(self, message):
        """添加错误日志"""
        pass
        
    def update_status(self):
        """更新状态"""
        pass
        
    def check_connection_status(self):
        """检查EasyXT连接状态"""
        try:
            # 优先使用EasyXT API检测
            api = easy_xt.get_api()
            if api:
                # 检查API是否可用
                connection_ok = False
                
                # 尝试检查连接状态
                if hasattr(api, 'is_connected'):
                    try:
                        connection_ok = api.is_connected()
                    except:
                        connection_ok = False
                
                # 如果没有is_connected方法，尝试其他检测方式
                if not connection_ok:
                    try:
                        # 尝试获取账户信息来检测连接
                        if hasattr(api, 'trade') and hasattr(api.trade, 'get_account'):
                            account_info = api.trade.get_account()
                            connection_ok = account_info is not None
                        elif hasattr(api, 'data') and hasattr(api.data, 'get_price'):
                            # 尝试获取数据来检测连接
                            test_data = api.data.get_price('000001.SZ', count=1)
                            connection_ok = test_data is not None
                        else:
                            # API存在但无法确定连接状态
                            connection_ok = True
                    except:
                        connection_ok = False
                
                if connection_ok:
                    self.connection_status.setText("EasyXT已连接")
                    self.connection_status.setStyleSheet("""
                        QLabel {
                            background-color: #44aa44;
                            color: white;
                            padding: 4px 8px;
                            border-radius: 4px;
                            font-weight: bold;
                        }
                    """)
                else:
                    self.connection_status.setText("EasyXT连接异常")
                    self.connection_status.setStyleSheet("""
                        QLabel {
                            background-color: #ff8800;
                            color: white;
                            padding: 4px 8px;
                            border-radius: 4px;
                            font-weight: bold;
                        }
                    """)
            else:
                self.connection_status.setText("EasyXT未初始化")
                self.connection_status.setStyleSheet("""
                    QLabel {
                        background-color: #ff4444;
                        color: white;
                        padding: 4px 8px;
                        border-radius: 4px;
                        font-weight: bold;
                    }
                """)
            
            # 备用检测：使用数据管理器
            if DATA_MANAGER_AVAILABLE:
                try:
                    data_manager = DataManager()
                    status = data_manager.get_connection_status()
                    
                    if status.get('qmt_connected'):
                        self.connection_status.setText("MiniQMT已连接")
                        self.connection_status.setStyleSheet("""
                            QLabel {
                                background-color: #44aa44;
                                color: white;
                                padding: 4px 8px;
                                border-radius: 4px;
                                font-weight: bold;
                            }
                        """)
                    elif status.get('xt_available'):
                        # 如果xtquant可用但qmt未连接，显示警告状态
                        if "EasyXT未" in self.connection_status.text():
                            self.connection_status.setText("xtquant可用")
                            self.connection_status.setStyleSheet("""
                                QLabel {
                                    background-color: #ff8800;
                                    color: white;
                                    padding: 4px 8px;
                                    border-radius: 4px;
                                    font-weight: bold;
                                }
                            """)
                except Exception as dm_e:
                    # 数据管理器检测失败，不影响主要检测结果
                    pass
                
        except Exception as e:
            self.connection_status.setText("连接检测失败")
            self.connection_status.setStyleSheet("""
                QLabel {
                    background-color: #ff4444;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-weight: bold;
                }
            """)
            print(f"连接状态检测错误: {str(e)}")
    
    def open_backtest_window(self):
        """打开回测窗口"""
        try:
            # 导入回测窗口组件
            from widgets.backtest_widget import BacktestWidget
            
            # 创建回测窗口
            self.backtest_window = BacktestWidget()
            self.backtest_window.setWindowTitle("📊 专业回测系统 - EasyXT")
            
            # 设置窗口图标和属性
            self.backtest_window.setWindowFlags(Qt.Window)
            self.backtest_window.setAttribute(Qt.WA_DeleteOnClose)
            
            # 显示窗口
            self.backtest_window.show()
            self.backtest_window.raise_()
            self.backtest_window.activateWindow()
            
            # 更新状态栏
            self.status_bar.showMessage("回测窗口已打开", 3000)
            
        except ImportError as e:
            error_msg = f"""无法导入回测模块:
{str(e)}

请确保回测模块已正确安装。"""
            QMessageBox.critical(self, "导入错误", error_msg)
        except Exception as e:
            error_msg = f"打开回测窗口失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于", 
                         "EasyXT量化交易策略管理平台\n\n"
                         "版本: 3.0\n"
                         "专业的量化交易策略开发和管理工具\n\n"
                         "功能特性:\n"
                         "• 策略参数可视化配置\n"
                         "• 实时策略监控和控制\n"
                         "• 完整的风险管理系统\n"
                         "• 策略模板和代码生成\n"
                         "• 交易记录和绩效分析")
                         
    def closeEvent(self, event):
        """关闭事件"""
        if self.executor_thread and self.executor_thread.isRunning():
            reply = QMessageBox.question(
                self, "确认", "策略正在运行，确定要退出吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.executor_thread.stop()
                self.executor_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


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