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


class StrategyParameterWidget(QWidget):
    """策略参数配置面板"""
    
    parameter_changed = pyqtSignal(str, dict)
    
    def __init__(self):
        super().__init__()
        self.current_strategy = None
        self.parameter_widgets = {}
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 策略选择区域
        strategy_group = QGroupBox("策略选择")
        strategy_layout = QGridLayout(strategy_group)
        
        strategy_layout.addWidget(QLabel("策略类型:"), 0, 0)
        self.strategy_type_combo = QComboBox()
        self.strategy_type_combo.addItems([
            "趋势跟踪策略", "均值回归策略", "网格交易策略", 
            "套利策略", "条件单策略", "自定义策略"
        ])
        self.strategy_type_combo.currentTextChanged.connect(self.on_strategy_type_changed)
        strategy_layout.addWidget(self.strategy_type_combo, 0, 1)
        
        strategy_layout.addWidget(QLabel("具体策略:"), 1, 0)
        self.strategy_combo = QComboBox()
        self.strategy_combo.currentTextChanged.connect(self.on_strategy_changed)
        strategy_layout.addWidget(self.strategy_combo, 1, 1)
        
        # 刷新策略列表按钮
        refresh_btn = QPushButton("刷新策略列表")
        refresh_btn.clicked.connect(self.refresh_strategy_list)
        strategy_layout.addWidget(refresh_btn, 0, 2)
        
        # 新建策略按钮
        new_strategy_btn = QPushButton("新建策略")
        new_strategy_btn.clicked.connect(self.create_new_strategy)
        strategy_layout.addWidget(new_strategy_btn, 1, 2)
        
        layout.addWidget(strategy_group)
        
        # 参数配置区域
        self.params_group = QGroupBox("策略参数配置")
        self.params_scroll = QScrollArea()
        self.params_widget = QWidget()
        self.params_layout = QFormLayout(self.params_widget)
        self.params_scroll.setWidget(self.params_widget)
        self.params_scroll.setWidgetResizable(True)
        
        params_main_layout = QVBoxLayout(self.params_group)
        params_main_layout.addWidget(self.params_scroll)
        
        layout.addWidget(self.params_group)
        
        # 参数操作按钮
        param_btn_layout = QHBoxLayout()
        
        self.load_params_btn = QPushButton("加载参数")
        self.load_params_btn.clicked.connect(self.load_parameters)
        
        self.save_params_btn = QPushButton("保存参数")
        self.save_params_btn.clicked.connect(self.save_parameters)
        
        self.reset_params_btn = QPushButton("重置参数")
        self.reset_params_btn.clicked.connect(self.reset_parameters)
        
        param_btn_layout.addWidget(self.load_params_btn)
        param_btn_layout.addWidget(self.save_params_btn)
        param_btn_layout.addWidget(self.reset_params_btn)
        param_btn_layout.addStretch()
        
        layout.addLayout(param_btn_layout)
        
        # 初始化策略列表
        self.refresh_strategy_list()
        
    def refresh_strategy_list(self):
        """刷新策略列表"""
        current_type = self.strategy_type_combo.currentText()
        self.strategy_combo.clear()
        
        # 根据策略类型加载对应的策略文件
        strategy_folders = {
            "趋势跟踪策略": "trend_following",
            "均值回归策略": "mean_reversion", 
            "网格交易策略": "grid_trading",
            "套利策略": "arbitrage",
            "条件单策略": "conditional_orders",
            "自定义策略": "custom"
        }
        
        if current_type in strategy_folders:
            folder_name = strategy_folders[current_type]
            strategy_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                       "strategies", folder_name)
            
            if os.path.exists(strategy_path):
                # 扫描策略文件
                for file in os.listdir(strategy_path):
                    if file.endswith('.py') and not file.startswith('__'):
                        strategy_name = file[:-3]  # 去掉.py扩展名
                        self.strategy_combo.addItem(strategy_name)
                        
        # 如果没有找到策略文件，添加示例策略
        if self.strategy_combo.count() == 0:
            self.add_example_strategies(current_type)
            
    def add_example_strategies(self, strategy_type):
        """添加示例策略"""
        example_strategies = {
            "趋势跟踪策略": ["双均线策略", "MACD策略", "布林带策略"],
            "均值回归策略": ["RSI策略", "均值回归策略", "配对交易"],
            "网格交易策略": ["固定网格", "动态网格", "马丁格尔网格"],
            "套利策略": ["统计套利", "期现套利", "跨市场套利"],
            "条件单策略": ["止损止盈", "追踪止损", "时间条件单"],
            "自定义策略": ["策略模板", "回测框架", "信号生成器"]
        }
        
        if strategy_type in example_strategies:
            for strategy in example_strategies[strategy_type]:
                self.strategy_combo.addItem(strategy)
                
    def on_strategy_type_changed(self):
        """策略类型改变"""
        self.refresh_strategy_list()
        
    def on_strategy_changed(self):
        """策略改变"""
        strategy_name = self.strategy_combo.currentText()
        if strategy_name:
            self.current_strategy = strategy_name
            self.load_strategy_parameters(strategy_name)
            
    def load_strategy_parameters(self, strategy_name):
        """加载策略参数"""
        # 清除现有参数控件
        self.clear_parameter_widgets()
        
        # 根据策略名称加载对应的参数配置
        params = self.get_strategy_default_params(strategy_name)
        
        # 创建参数控件
        for param_name, param_config in params.items():
            self.create_parameter_widget(param_name, param_config)
            
    def get_strategy_default_params(self, strategy_name):
        """获取策略默认参数"""
        # 这里定义各种策略的默认参数
        default_params = {
            "双均线策略": {
                "股票代码": {"type": "text", "default": "000001.SZ", "desc": "交易股票代码"},
                "短期均线": {"type": "int", "default": 5, "min": 1, "max": 50, "desc": "短期移动平均线周期"},
                "长期均线": {"type": "int", "default": 20, "min": 10, "max": 200, "desc": "长期移动平均线周期"},
                "交易数量": {"type": "int", "default": 1000, "min": 100, "max": 100000, "desc": "每次交易股数"},
                "止损比例": {"type": "float", "default": 0.05, "min": 0.01, "max": 0.2, "desc": "止损比例"},
                "止盈比例": {"type": "float", "default": 0.1, "min": 0.02, "max": 0.5, "desc": "止盈比例"},
                "启用止损": {"type": "bool", "default": True, "desc": "是否启用止损"},
                "启用止盈": {"type": "bool", "default": True, "desc": "是否启用止盈"}
            },
            "网格交易策略": {
                "股票代码": {"type": "text", "default": "000001.SZ", "desc": "交易股票代码"},
                "网格数量": {"type": "int", "default": 10, "min": 3, "max": 50, "desc": "网格层数"},
                "网格间距": {"type": "float", "default": 0.02, "min": 0.005, "max": 0.1, "desc": "网格间距比例"},
                "基准价格": {"type": "float", "default": 10.0, "min": 1.0, "max": 1000.0, "desc": "网格基准价格"},
                "单网格数量": {"type": "int", "default": 100, "min": 100, "max": 10000, "desc": "单个网格交易数量"},
                "最大持仓": {"type": "int", "default": 10000, "min": 1000, "max": 100000, "desc": "最大持仓数量"},
                "启用动态调整": {"type": "bool", "default": False, "desc": "是否启用动态网格调整"}
            },
            "条件单策略": {
                "股票代码": {"type": "text", "default": "000001.SZ", "desc": "交易股票代码"},
                "条件类型": {"type": "combo", "default": "价格条件", "options": ["价格条件", "时间条件", "技术指标条件"], "desc": "条件单类型"},
                "触发价格": {"type": "float", "default": 10.0, "min": 1.0, "max": 1000.0, "desc": "条件触发价格"},
                "交易方向": {"type": "combo", "default": "买入", "options": ["买入", "卖出"], "desc": "交易方向"},
                "交易数量": {"type": "int", "default": 1000, "min": 100, "max": 100000, "desc": "交易数量"},
                "有效期": {"type": "combo", "default": "当日有效", "options": ["当日有效", "本周有效", "本月有效", "长期有效"], "desc": "条件单有效期"},
                "触发时间": {"type": "time", "default": "09:30:00", "desc": "时间条件触发时间"},
                "启用短信通知": {"type": "bool", "default": False, "desc": "触发时发送短信通知"}
            },
            "RSI策略": {
                "股票代码": {"type": "text", "default": "000001.SZ", "desc": "交易股票代码"},
                "RSI周期": {"type": "int", "default": 14, "min": 5, "max": 50, "desc": "RSI计算周期"},
                "超买阈值": {"type": "float", "default": 70.0, "min": 60.0, "max": 90.0, "desc": "RSI超买阈值"},
                "超卖阈值": {"type": "float", "default": 30.0, "min": 10.0, "max": 40.0, "desc": "RSI超卖阈值"},
                "交易数量": {"type": "int", "default": 1000, "min": 100, "max": 100000, "desc": "每次交易股数"},
                "持仓比例": {"type": "float", "default": 0.5, "min": 0.1, "max": 1.0, "desc": "最大持仓比例"}
            }
        }
        
        return default_params.get(strategy_name, {
            "股票代码": {"type": "text", "default": "000001.SZ", "desc": "交易股票代码"},
            "交易数量": {"type": "int", "default": 1000, "min": 100, "max": 100000, "desc": "交易数量"}
        })
        
    def create_parameter_widget(self, param_name, param_config):
        """创建参数控件"""
        param_type = param_config.get("type", "text")
        default_value = param_config.get("default", "")
        description = param_config.get("desc", "")
        
        # 创建标签
        label = QLabel(f"{param_name}:")
        label.setToolTip(description)
        
        # 根据参数类型创建对应的控件
        if param_type == "text":
            widget = QLineEdit(str(default_value))
            
        elif param_type == "int":
            widget = QSpinBox()
            widget.setMinimum(param_config.get("min", 0))
            widget.setMaximum(param_config.get("max", 999999))
            widget.setValue(default_value)
            
        elif param_type == "float":
            widget = QDoubleSpinBox()
            widget.setMinimum(param_config.get("min", 0.0))
            widget.setMaximum(param_config.get("max", 999999.0))
            widget.setDecimals(4)
            widget.setSingleStep(0.01)
            widget.setValue(default_value)
            
        elif param_type == "bool":
            widget = QCheckBox()
            widget.setChecked(default_value)
            
        elif param_type == "combo":
            widget = QComboBox()
            options = param_config.get("options", [])
            widget.addItems(options)
            if default_value in options:
                widget.setCurrentText(default_value)
                
        elif param_type == "time":
            widget = QTimeEdit()
            widget.setDisplayFormat("HH:mm:ss")
            if isinstance(default_value, str):
                from PyQt5.QtCore import QTime
                time_obj = QTime.fromString(default_value, "HH:mm:ss")
                widget.setTime(time_obj)
                
        elif param_type == "datetime":
            widget = QDateTimeEdit()
            widget.setDateTime(QDateTime.currentDateTime())
            
        else:
            widget = QLineEdit(str(default_value))
            
        # 设置工具提示
        widget.setToolTip(description)
        
        # 添加到布局
        self.params_layout.addRow(label, widget)
        
        # 保存控件引用
        self.parameter_widgets[param_name] = widget
        
        # 连接信号
        if hasattr(widget, 'textChanged'):
            widget.textChanged.connect(self.on_parameter_changed)
        elif hasattr(widget, 'valueChanged'):
            widget.valueChanged.connect(self.on_parameter_changed)
        elif hasattr(widget, 'stateChanged'):
            widget.stateChanged.connect(self.on_parameter_changed)
        elif hasattr(widget, 'currentTextChanged'):
            widget.currentTextChanged.connect(self.on_parameter_changed)
            
    def clear_parameter_widgets(self):
        """清除参数控件"""
        # 清除所有控件
        for i in reversed(range(self.params_layout.count())):
            item = self.params_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                    
        self.parameter_widgets.clear()
        
    def on_parameter_changed(self):
        """参数改变"""
        if self.current_strategy:
            params = self.get_current_parameters()
            self.parameter_changed.emit(self.current_strategy, params)
            
    def get_current_parameters(self):
        """获取当前参数值"""
        params = {}
        
        for param_name, widget in self.parameter_widgets.items():
            if isinstance(widget, QLineEdit):
                params[param_name] = widget.text()
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                params[param_name] = widget.value()
            elif isinstance(widget, QCheckBox):
                params[param_name] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                params[param_name] = widget.currentText()
            elif isinstance(widget, QTimeEdit):
                params[param_name] = widget.time().toString("HH:mm:ss")
            elif isinstance(widget, QDateTimeEdit):
                params[param_name] = widget.dateTime().toString("yyyy-MM-dd HH:mm:ss")
                
        return params
        
    def load_parameters(self):
        """加载参数文件"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "加载策略参数", "", "JSON文件 (*.json);;所有文件 (*)"
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    params = json.load(f)
                    
                self.set_parameters(params)
                QMessageBox.information(self, "成功", "参数加载成功")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载参数失败: {str(e)}")
                
    def save_parameters(self):
        """保存参数文件"""
        if not self.current_strategy:
            QMessageBox.warning(self, "警告", "请先选择策略")
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存策略参数", f"{self.current_strategy}_参数.json", "JSON文件 (*.json)"
        )
        
        if filename:
            try:
                params = self.get_current_parameters()
                params['策略名称'] = self.current_strategy
                params['保存时间'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(params, f, ensure_ascii=False, indent=2)
                    
                QMessageBox.information(self, "成功", "参数保存成功")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存参数失败: {str(e)}")
                
    def reset_parameters(self):
        """重置参数"""
        if self.current_strategy:
            reply = QMessageBox.question(
                self, "确认", "确定要重置所有参数到默认值吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.load_strategy_parameters(self.current_strategy)
                
    def set_parameters(self, params):
        """设置参数值"""
        for param_name, value in params.items():
            if param_name in self.parameter_widgets:
                widget = self.parameter_widgets[param_name]
                
                if isinstance(widget, QLineEdit):
                    widget.setText(str(value))
                elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                    widget.setValue(value)
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(bool(value))
                elif isinstance(widget, QComboBox):
                    widget.setCurrentText(str(value))
                elif isinstance(widget, QTimeEdit):
                    from PyQt5.QtCore import QTime
                    if isinstance(value, str):
                        time_obj = QTime.fromString(value, "HH:mm:ss")
                        widget.setTime(time_obj)
                        
    def create_new_strategy(self):
        """创建新策略"""
        from PyQt5.QtWidgets import QInputDialog
        
        strategy_name, ok = QInputDialog.getText(
            self, "新建策略", "请输入策略名称:"
        )
        
        if ok and strategy_name:
            # 获取当前策略类型对应的文件夹
            current_type = self.strategy_type_combo.currentText()
            strategy_folders = {
                "趋势跟踪策略": "trend_following",
                "均值回归策略": "mean_reversion", 
                "网格交易策略": "grid_trading",
                "套利策略": "arbitrage",
                "条件单策略": "conditional_orders",
                "自定义策略": "custom"
            }
            
            if current_type in strategy_folders:
                folder_name = strategy_folders[current_type]
                strategy_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                    "strategies", folder_name
                )
                
                # 创建策略文件
                strategy_file = os.path.join(strategy_path, f"{strategy_name}.py")
                
                if os.path.exists(strategy_file):
                    QMessageBox.warning(self, "警告", "策略文件已存在")
                    return
                    
                try:
                    # 创建策略模板
                    template = self.get_strategy_template(strategy_name, current_type)
                    
                    with open(strategy_file, 'w', encoding='utf-8') as f:
                        f.write(template)
                        
                    QMessageBox.information(self, "成功", f"策略文件创建成功:\n{strategy_file}")
                    
                    # 刷新策略列表
                    self.refresh_strategy_list()
                    
                    # 选择新创建的策略
                    index = self.strategy_combo.findText(strategy_name)
                    if index >= 0:
                        self.strategy_combo.setCurrentIndex(index)
                        
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"创建策略文件失败: {str(e)}")
                    
    def get_strategy_template(self, strategy_name, strategy_type):
        """获取策略模板"""
        template = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
{strategy_name} - {strategy_type}
创建时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import easy_xt


class {strategy_name.replace(" ", "")}Strategy:
    """
    {strategy_name}策略类
    """
    
    def __init__(self, params=None):
        """
        初始化策略
        
        Args:
            params (dict): 策略参数
        """
        self.params = params or {{}}
        self.api = easy_xt.get_api()
        self.positions = {{}}
        self.orders = []
        
    def initialize(self):
        """
        策略初始化
        """
        print(f"初始化策略: {strategy_name}")
        print(f"策略参数: {{self.params}}")
        
    def on_data(self, data):
        """
        数据处理函数
        
        Args:
            data: 市场数据
        """
        # 在这里实现策略逻辑
        pass
        
    def on_order(self, order):
        """
        订单状态变化处理
        
        Args:
            order: 订单信息
        """
        self.orders.append(order)
        
    def buy(self, stock_code, quantity, price=None):
        """
        买入股票
        
        Args:
            stock_code (str): 股票代码
            quantity (int): 买入数量
            price (float): 买入价格，None表示市价
        """
        try:
            if price is None:
                # 市价买入
                result = self.api.trade.buy_market(stock_code, quantity)
            else:
                # 限价买入
                result = self.api.trade.buy_limit(stock_code, quantity, price)
                
            print(f"买入订单: {{stock_code}} {{quantity}}股 价格:{{price or '市价'}}")
            return result
            
        except Exception as e:
            print(f"买入失败: {{str(e)}}")
            return None
            
    def sell(self, stock_code, quantity, price=None):
        """
        卖出股票
        
        Args:
            stock_code (str): 股票代码
            quantity (int): 卖出数量
            price (float): 卖出价格，None表示市价
        """
        try:
            if price is None:
                # 市价卖出
                result = self.api.trade.sell_market(stock_code, quantity)
            else:
                # 限价卖出
                result = self.api.trade.sell_limit(stock_code, quantity, price)
                
            print(f"卖出订单: {{stock_code}} {{quantity}}股 价格:{{price or '市价'}}")
            return result
            
        except Exception as e:
            print(f"卖出失败: {{str(e)}}")
            return None
            
    def run(self):
        """
        运行策略
        """
        try:
            self.initialize()
            
            # 获取股票代码
            stock_code = self.params.get('股票代码', '000001.SZ')
            
            # 获取数据
            data = self.api.data.get_price(stock_code, count=100)
            
            if data is not None and not data.empty:
                print(f"获取到数据: {{len(data)}}条")
                self.on_data(data)
            else:
                print("未获取到数据")
                
        except Exception as e:
            print(f"策略运行错误: {{str(e)}}")


def main():
    """
    主函数 - 用于测试策略
    """
    # 示例参数
    params = {{
        '股票代码': '000001.SZ',
        '交易数量': 1000
    }}
    
    # 创建策略实例
    strategy = {strategy_name.replace(" ", "")}Strategy(params)
    
    # 运行策略
    strategy.run()


if __name__ == "__main__":
    main()
'''
        return template


class StrategyMonitorWidget(QWidget):
    """策略监控面板"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 策略状态区域
        status_group = QGroupBox("策略运行状态")
        status_layout = QGridLayout(status_group)
        
        # 运行状态指示器
        status_layout.addWidget(QLabel("运行状态:"), 0, 0)
        self.status_label = QLabel("未运行")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #cccccc;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
            }
        """)
        status_layout.addWidget(self.status_label, 0, 1)
        
        # 运行时间
        status_layout.addWidget(QLabel("运行时间:"), 1, 0)
        self.runtime_label = QLabel("00:00:00")
        status_layout.addWidget(self.runtime_label, 1, 1)
        
        # 总收益
        status_layout.addWidget(QLabel("总收益:"), 2, 0)
        self.profit_label = QLabel("0.00")
        status_layout.addWidget(self.profit_label, 2, 1)
        
        # 今日交易次数
        status_layout.addWidget(QLabel("今日交易:"), 3, 0)
        self.trade_count_label = QLabel("0")
        status_layout.addWidget(self.trade_count_label, 3, 1)
        
        layout.addWidget(status_group)
        
        # 持仓信息
        position_group = QGroupBox("持仓信息")
        position_layout = QVBoxLayout(position_group)
        
        self.position_table = QTableWidget()
        self.position_table.setColumnCount(7)
        self.position_table.setHorizontalHeaderLabels([
            "股票代码", "股票名称", "持仓数量", "可用数量", "成本价", "现价", "浮动盈亏"
        ])
        self.position_table.horizontalHeader().setStretchLastSection(True)
        position_layout.addWidget(self.position_table)
        
        layout.addWidget(position_group)
        
        # 委托记录
        order_group = QGroupBox("委托记录")
        order_layout = QVBoxLayout(order_group)
        
        self.order_table = QTableWidget()
        self.order_table.setColumnCount(8)
        self.order_table.setHorizontalHeaderLabels([
            "委托时间", "股票代码", "股票名称", "买卖方向", "委托数量", "委托价格", "成交数量", "订单状态"
        ])
        self.order_table.horizontalHeader().setStretchLastSection(True)
        order_layout.addWidget(self.order_table)
        
        layout.addWidget(order_group)
        
    def update_status(self, status, runtime=None, profit=None, trade_count=None):
        """更新策略状态"""
        self.status_label.setText(status)
        
        # 根据状态设置颜色
        if status == "运行中":
            color = "#44aa44"
        elif status == "已停止":
            color = "#ff4444"
        elif status == "暂停":
            color = "#ff8800"
        else:
            color = "#cccccc"
            
        self.status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
            }}
        """)
        
        if runtime is not None:
            self.runtime_label.setText(runtime)
        if profit is not None:
            self.profit_label.setText(f"{profit:.2f}")
        if trade_count is not None:
            self.trade_count_label.setText(str(trade_count))
            
    def update_positions(self, positions):
        """更新持仓信息"""
        self.position_table.setRowCount(len(positions))
        
        for i, position in enumerate(positions):
            self.position_table.setItem(i, 0, QTableWidgetItem(position.get('股票代码', '')))
            self.position_table.setItem(i, 1, QTableWidgetItem(position.get('股票名称', '')))
            self.position_table.setItem(i, 2, QTableWidgetItem(str(position.get('持仓数量', 0))))
            self.position_table.setItem(i, 3, QTableWidgetItem(str(position.get('可用数量', 0))))
            self.position_table.setItem(i, 4, QTableWidgetItem(f"{position.get('成本价', 0):.2f}"))
            self.position_table.setItem(i, 5, QTableWidgetItem(f"{position.get('现价', 0):.2f}"))
            self.position_table.setItem(i, 6, QTableWidgetItem(f"{position.get('浮动盈亏', 0):.2f}"))
            
    def update_orders(self, orders):
        """更新委托记录"""
        self.order_table.setRowCount(len(orders))
        
        for i, order in enumerate(orders):
            self.order_table.setItem(i, 0, QTableWidgetItem(order.get('委托时间', '')))
            self.order_table.setItem(i, 1, QTableWidgetItem(order.get('股票代码', '')))
            self.order_table.setItem(i, 2, QTableWidgetItem(order.get('股票名称', '')))
            self.order_table.setItem(i, 3, QTableWidgetItem(order.get('买卖方向', '')))
            self.order_table.setItem(i, 4, QTableWidgetItem(str(order.get('委托数量', 0))))
            self.order_table.setItem(i, 5, QTableWidgetItem(f"{order.get('委托价格', 0):.2f}"))
            self.order_table.setItem(i, 6, QTableWidgetItem(str(order.get('成交数量', 0))))
            self.order_table.setItem(i, 7, QTableWidgetItem(order.get('订单状态', '')))


class StrategyControlWidget(QWidget):
    """策略控制面板"""
    
    strategy_start = pyqtSignal(str, dict)
    strategy_stop = pyqtSignal()
    strategy_pause = pyqtSignal()
    strategy_resume = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.is_paused = False
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 策略控制按钮
        control_group = QGroupBox("策略控制")
        control_layout = QGridLayout(control_group)
        
        self.start_btn = QPushButton("启动策略")
        self.start_btn.setStyleSheet("QPushButton { background-color: #44aa44; }")
        self.start_btn.clicked.connect(self.start_strategy)
        control_layout.addWidget(self.start_btn, 0, 0)
        
        self.stop_btn = QPushButton("停止策略")
        self.stop_btn.setStyleSheet("QPushButton { background-color: #ff4444; }")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_strategy)
        control_layout.addWidget(self.stop_btn, 0, 1)
        
        self.pause_btn = QPushButton("暂停策略")
        self.pause_btn.setStyleSheet("QPushButton { background-color: #ff8800; }")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.pause_strategy)
        control_layout.addWidget(self.pause_btn, 1, 0)
        
        self.resume_btn = QPushButton("恢复策略")
        self.resume_btn.setStyleSheet("QPushButton { background-color: #0078d4; }")
        self.resume_btn.setEnabled(False)
        self.resume_btn.clicked.connect(self.resume_strategy)
        control_layout.addWidget(self.resume_btn, 1, 1)
        
        layout.addWidget(control_group)
        
        # 风险控制
        risk_group = QGroupBox("风险控制")
        risk_layout = QGridLayout(risk_group)
        
        risk_layout.addWidget(QLabel("最大亏损:"), 0, 0)
        self.max_loss_spin = QDoubleSpinBox()
        self.max_loss_spin.setRange(0, 100000)
        self.max_loss_spin.setValue(1000)
        self.max_loss_spin.setSuffix(" 元")
        risk_layout.addWidget(self.max_loss_spin, 0, 1)
        
        risk_layout.addWidget(QLabel("最大持仓:"), 1, 0)
        self.max_position_spin = QSpinBox()
        self.max_position_spin.setRange(0, 1000000)
        self.max_position_spin.setValue(10000)
        self.max_position_spin.setSuffix(" 股")
        risk_layout.addWidget(self.max_position_spin, 1, 1)
        
        self.enable_risk_control = QCheckBox("启用风险控制")
        self.enable_risk_control.setChecked(True)
        risk_layout.addWidget(self.enable_risk_control, 2, 0, 1, 2)
        
        layout.addWidget(risk_group)
        
        # 日志控制
        log_group = QGroupBox("日志设置")
        log_layout = QGridLayout(log_group)
        
        self.enable_file_log = QCheckBox("保存到文件")
        self.enable_file_log.setChecked(True)
        log_layout.addWidget(self.enable_file_log, 0, 0)
        
        self.enable_trade_log = QCheckBox("记录交易日志")
        self.enable_trade_log.setChecked(True)
        log_layout.addWidget(self.enable_trade_log, 0, 1)
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setCurrentText("INFO")
        log_layout.addWidget(QLabel("日志级别:"), 1, 0)
        log_layout.addWidget(self.log_level_combo, 1, 1)
        
        layout.addWidget(log_group)
        
        layout.addStretch()
        
    def start_strategy(self):
        """启动策略"""
        self.is_running = True
        self.is_paused = False
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        self.resume_btn.setEnabled(False)
        
        # 发送启动信号
        self.strategy_start.emit("", {})
        
    def stop_strategy(self):
        """停止策略"""
        self.is_running = False
        self.is_paused = False
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.resume_btn.setEnabled(False)
        
        # 发送停止信号
        self.strategy_stop.emit()
        
    def pause_strategy(self):
        """暂停策略"""
        self.is_paused = True
        
        self.pause_btn.setEnabled(False)
        self.resume_btn.setEnabled(True)
        
        # 发送暂停信号
        self.strategy_pause.emit()
        
    def resume_strategy(self):
        """恢复策略"""
        self.is_paused = False
        
        self.pause_btn.setEnabled(True)
        self.resume_btn.setEnabled(False)
        
        # 发送恢复信号
        self.strategy_resume.emit()


class StrategyExecutorThread(QThread):
    """策略执行线程"""
    
    status_update = pyqtSignal(str, str, float, int)  # status, runtime, profit, trade_count
    position_update = pyqtSignal(list)
    order_update = pyqtSignal(list)
    log_message = pyqtSignal(str)
    error_message = pyqtSignal(str)
    
    def __init__(self, strategy_name, parameters):
        super().__init__()
        self.strategy_name = strategy_name
        self.parameters = parameters
        self.is_running = False
        self.is_paused = False
        
    def run(self):
        """运行策略"""
        try:
            self.is_running = True
            start_time = datetime.now()
            
            self.log_message.emit(f"开始执行策略: {self.strategy_name}")
            self.log_message.emit(f"策略参数: {self.parameters}")
            
            # 模拟策略执行
            trade_count = 0
            total_profit = 0.0
            
            while self.is_running:
                if not self.is_paused:
                    # 计算运行时间
                    runtime = datetime.now() - start_time
                    runtime_str = str(runtime).split('.')[0]  # 去掉微秒
                    
                    # 模拟交易
                    if trade_count < 10:  # 模拟最多10次交易
                        trade_count += 1
                        profit_change = np.random.uniform(-50, 100)  # 随机盈亏
                        total_profit += profit_change
                        
                        self.log_message.emit(f"执行交易 #{trade_count}, 盈亏: {profit_change:.2f}")
                        
                        # 更新状态
                        self.status_update.emit("运行中", runtime_str, total_profit, trade_count)
                        
                        # 模拟持仓更新
                        positions = [{
                            '股票代码': self.parameters.get('股票代码', '000001.SZ'),
                            '股票名称': '平安银行',
                            '持仓数量': trade_count * 100,
                            '可用数量': trade_count * 100,
                            '成本价': 10.0 + np.random.uniform(-0.5, 0.5),
                            '现价': 10.0 + np.random.uniform(-1, 1),
                            '浮动盈亏': total_profit
                        }]
                        self.position_update.emit(positions)
                        
                        # 模拟订单更新
                        orders = [{
                            '委托时间': datetime.now().strftime("%H:%M:%S"),
                            '股票代码': self.parameters.get('股票代码', '000001.SZ'),
                            '股票名称': '平安银行',
                            '买卖方向': '买入' if trade_count % 2 == 1 else '卖出',
                            '委托数量': 100,
                            '委托价格': 10.0 + np.random.uniform(-0.5, 0.5),
                            '成交数量': 100,
                            '订单状态': '已成交'
                        }]
                        self.order_update.emit(orders)
                        
                    # 等待一段时间
                    self.msleep(2000)  # 2秒
                else:
                    # 暂停状态
                    self.msleep(100)
                    
        except Exception as e:
            self.error_message.emit(f"策略执行错误: {str(e)}")
        finally:
            self.is_running = False
            self.log_message.emit("策略执行结束")
            
    def stop(self):
        """停止策略"""
        self.is_running = False
        
    def pause(self):
        """暂停策略"""
        self.is_paused = True
        
    def resume(self):
        """恢复策略"""
        self.is_paused = False


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
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧控制面板
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 创建标签页
        self.left_tabs = QTabWidget()
        
        # 策略参数配置标签页
        self.strategy_params = StrategyParameterWidget()
        self.left_tabs.addTab(self.strategy_params, "策略参数")
        
        # 策略控制标签页
        self.strategy_control = StrategyControlWidget()
        self.left_tabs.addTab(self.strategy_control, "策略控制")
        
        left_layout.addWidget(self.left_tabs)
        
        # 执行日志
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        
        # 日志控制按钮
        log_btn_layout = QHBoxLayout()
        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.clicked.connect(self.log_text.clear)
        save_log_btn = QPushButton("保存日志")
        save_log_btn.clicked.connect(self.save_log)
        
        log_btn_layout.addWidget(clear_log_btn)
        log_btn_layout.addWidget(save_log_btn)
        log_btn_layout.addStretch()
        
        log_layout.addLayout(log_btn_layout)
        left_layout.addWidget(log_group)
        
        splitter.addWidget(left_widget)
        
        # 右侧监控面板
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 策略监控标签页
        self.strategy_monitor = StrategyMonitorWidget()
        right_layout.addWidget(self.strategy_monitor)
        
        splitter.addWidget(right_widget)
        
        # 设置分割器比例
        splitter.setSizes([600, 1000])
        
        # 创建状态栏
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
        
        # 创建菜单栏
        self.create_menu_bar()
        
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_strategy_action = QAction('新建策略', self)
        new_strategy_action.setShortcut('Ctrl+N')
        new_strategy_action.triggered.connect(self.strategy_params.create_new_strategy)
        file_menu.addAction(new_strategy_action)
        
        load_params_action = QAction('加载参数', self)
        load_params_action.setShortcut('Ctrl+O')
        load_params_action.triggered.connect(self.strategy_params.load_parameters)
        file_menu.addAction(load_params_action)
        
        save_params_action = QAction('保存参数', self)
        save_params_action.setShortcut('Ctrl+S')
        save_params_action.triggered.connect(self.strategy_params.save_parameters)
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
        start_action.triggered.connect(self.strategy_control.start_strategy)
        strategy_menu.addAction(start_action)
        
        stop_action = QAction('停止策略', self)
        stop_action.setShortcut('F6')
        stop_action.triggered.connect(self.strategy_control.stop_strategy)
        strategy_menu.addAction(stop_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        refresh_strategies_action = QAction('刷新策略列表', self)
        refresh_strategies_action.triggered.connect(self.strategy_params.refresh_strategy_list)
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
        # 策略控制信号
        self.strategy_control.strategy_start.connect(self.start_strategy)
        self.strategy_control.strategy_stop.connect(self.stop_strategy)
        self.strategy_control.strategy_pause.connect(self.pause_strategy)
        self.strategy_control.strategy_resume.connect(self.resume_strategy)
        
        # 参数变化信号
        self.strategy_params.parameter_changed.connect(self.on_parameter_changed)
        
    def start_strategy(self, strategy_name, params):
        """启动策略"""
        if self.executor_thread and self.executor_thread.isRunning():
            QMessageBox.warning(self, "警告", "策略正在运行中")
            return
            
        # 获取当前策略和参数
        current_strategy = self.strategy_params.current_strategy
        current_params = self.strategy_params.get_current_parameters()
        
        if not current_strategy:
            QMessageBox.warning(self, "警告", "请先选择策略")
            return
            
        self.log_text.append(f"\n{'='*50}")
        self.log_text.append(f"启动策略: {current_strategy}")
        self.log_text.append(f"{'='*50}")
        
        # 创建执行线程
        self.executor_thread = StrategyExecutorThread(current_strategy, current_params)
        
        # 连接信号
        self.executor_thread.status_update.connect(self.strategy_monitor.update_status)
        self.executor_thread.position_update.connect(self.strategy_monitor.update_positions)
        self.executor_thread.order_update.connect(self.strategy_monitor.update_orders)
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
            
        self.strategy_monitor.update_status("已停止")
        self.status_bar.showMessage("策略已停止")
        self.log_text.append("策略已停止")
        
    def pause_strategy(self):
        """暂停策略"""
        if self.executor_thread and self.executor_thread.isRunning():
            self.executor_thread.pause()
            
        self.strategy_monitor.update_status("暂停")
        self.status_bar.showMessage("策略已暂停")
        self.log_text.append("策略已暂停")
        
    def resume_strategy(self):
        """恢复策略"""
        if self.executor_thread and self.executor_thread.isRunning():
            self.executor_thread.resume()
            
        self.strategy_monitor.update_status("运行中")
        self.status_bar.showMessage("策略已恢复")
        self.log_text.append("策略已恢复")
        
    def on_parameter_changed(self, strategy_name, params):
        """参数改变处理"""
        self.log_text.append(f"策略参数已更新: {strategy_name}")
        
    def append_log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.ensureCursorVisible()
        
    def append_error_log(self, message):
        """添加错误日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] ❌ {message}")
        self.log_text.ensureCursorVisible()
        
    def save_log(self):
        """保存日志"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存日志", f"策略日志_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", 
            "文本文件 (*.txt)"
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                QMessageBox.information(self, "成功", "日志保存成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
                
    def check_connection_status(self):
        """检查MiniQMT连接状态"""
        try:
            if DATA_MANAGER_AVAILABLE:
                # 使用数据管理器检测连接状态
                data_manager = DataManager()
                status = data_manager.get_connection_status()
                
                if status['qmt_connected']:
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
                elif status['xt_available']:
                    self.connection_status.setText("MiniQMT未连接")
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
                    self.connection_status.setText("xtquant不可用")
                    self.connection_status.setStyleSheet("""
                        QLabel {
                            background-color: #ff4444;
                            color: white;
                            padding: 4px 8px;
                            border-radius: 4px;
                            font-weight: bold;
                        }
                    """)
            else:
                # 回退到简单的API检测
                api = easy_xt.get_api()
                if api:
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
                    raise Exception("API未初始化")
                
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
        }
        QTabBar::tab:selected {
            background-color: white;
            border-bottom: 2px solid #0078d4;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #c0c0c0;
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
            background-color: #0078d4;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #106ebe;
        }
        QPushButton:pressed {
            background-color: #005a9e;
        }
        QPushButton:disabled {
            background-color: #cccccc;
            color: #666666;
        }
    """)
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()