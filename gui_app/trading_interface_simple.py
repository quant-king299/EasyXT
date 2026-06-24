# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger(__name__)
#!/usr/bin/env python3
"""
简洁交易界面 - 基于您喜欢的UI设计
模仿专业交易软件的简洁风格
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QSizePolicy, QMessageBox, QStatusBar
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import easy_xt
    EASYXT_AVAILABLE = True
except ImportError:
    EASYXT_AVAILABLE = False
    logger.info("EasyXT模块未找到，将使用模拟模式")


class TradingInterface(QMainWindow):
    """简洁交易界面主窗口"""
    
    # 信号定义
    account_updated = pyqtSignal(dict)
    position_updated = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self.account_id = None
        self.is_connected = False
        self.account_info = {}
        self.positions = []
        
        # 初始化EasyXT
        if EASYXT_AVAILABLE:
            self.easyxt = easy_xt.EasyXT()
        else:
            self.easyxt = None
            
        self.init_ui()
        self.setup_timer()
        self.setup_style()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("量化交易系统")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建中央窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 顶部状态栏
        self.create_top_status_bar(main_layout)
        
        # 账户信息区域
        self.create_account_info_section(main_layout)
        
        # 交易操作区域
        self.create_trading_section(main_layout)
        
        # 持仓列表区域
        self.create_position_section(main_layout)
        
        # 底部状态栏
        self.create_status_bar()
        
    def create_top_status_bar(self, parent_layout):
        """创建顶部状态栏"""
        top_frame = QFrame()
        top_frame.setFrameStyle(QFrame.StyledPanel)
        top_frame.setFixedHeight(40)
        
        top_layout = QHBoxLayout(top_frame)
        top_layout.setContentsMargins(10, 5, 10, 5)
        
        # 实盘交易标签
        self.trading_mode_label = QLabel("📊 实盘交易")
        self.trading_mode_label.setFont(QFont("微软雅黑", 10, QFont.Bold))
        
        # 连接状态标签
        self.connection_status_label = QLabel("🔴 未连接")
        self.connection_status_label.setFont(QFont("微软雅黑", 9))
        
        # 连接交易服务按钮
        self.connect_btn = QPushButton("🔌 连接交易服务")
        self.connect_btn.setFixedSize(120, 30)
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        top_layout.addWidget(self.trading_mode_label)
        top_layout.addStretch()
        top_layout.addWidget(self.connection_status_label)
        top_layout.addWidget(self.connect_btn)
        
        parent_layout.addWidget(top_frame)
        
    def create_account_info_section(self, parent_layout):
        """创建账户信息区域"""
        account_group = QGroupBox("账户信息")
        account_group.setFixedHeight(150)
        account_layout = QVBoxLayout(account_group)
        
        # 账户信息表格
        self.account_table = QTableWidget(4, 2)
        self.account_table.setHorizontalHeaderLabels(["项目", "金额"])
        self.account_table.setVerticalHeaderLabels(["总资产", "可用资金", "持仓市值", "今日盈亏"])
        
        # 设置表格样式
        self.account_table.horizontalHeader().setStretchLastSection(True)
        self.account_table.verticalHeader().setDefaultSectionSize(30)
        self.account_table.setAlternatingRowColors(True)
        self.account_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # 初始化账户数据
        self.init_account_table()
        
        account_layout.addWidget(self.account_table)
        parent_layout.addWidget(account_group)
        
    def create_trading_section(self, parent_layout):
        """创建交易操作区域"""
        trading_group = QGroupBox("交易操作")
        trading_group.setFixedHeight(120)
        trading_layout = QGridLayout(trading_group)
        
        # 股票代码
        trading_layout.addWidget(QLabel("股票代码:"), 0, 0)
        self.stock_combo = QComboBox()
        self.stock_combo.setEditable(True)
        self.stock_combo.addItems(["000001.SZ", "600000.SH", "000002.SZ", "600036.SH"])
        trading_layout.addWidget(self.stock_combo, 0, 1)
        
        # 数量
        trading_layout.addWidget(QLabel("数量(股):"), 1, 0)
        self.volume_spin = QSpinBox()
        self.volume_spin.setRange(100, 999999)
        self.volume_spin.setValue(100)
        self.volume_spin.setSingleStep(100)
        trading_layout.addWidget(self.volume_spin, 1, 1)
        
        # 价格
        trading_layout.addWidget(QLabel("价格:"), 2, 0)
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.01, 9999.99)
        self.price_spin.setValue(0.01)
        self.price_spin.setDecimals(2)
        self.price_spin.setSingleStep(0.01)
        trading_layout.addWidget(self.price_spin, 2, 1)
        
        # 买入卖出按钮
        button_layout = QHBoxLayout()
        
        self.buy_btn = QPushButton("📈 买入")
        self.buy_btn.setFixedSize(100, 35)
        self.buy_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff6666;
            }
            QPushButton:pressed {
                background-color: #cc3333;
            }
        """)
        self.buy_btn.clicked.connect(self.buy_stock)
        
        self.sell_btn = QPushButton("📉 卖出")
        self.sell_btn.setFixedSize(100, 35)
        self.sell_btn.setStyleSheet("""
            QPushButton {
                background-color: #00aa00;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00cc00;
            }
            QPushButton:pressed {
                background-color: #008800;
            }
        """)
        self.sell_btn.clicked.connect(self.sell_stock)
        
        button_layout.addWidget(self.buy_btn)
        button_layout.addWidget(self.sell_btn)
        button_layout.addStretch()
        
        trading_layout.addLayout(button_layout, 0, 2, 3, 1)
        
        parent_layout.addWidget(trading_group)
        
    def create_position_section(self, parent_layout):
        """创建持仓列表区域"""
        position_group = QGroupBox("持仓列表")
        position_layout = QVBoxLayout(position_group)
        
        # 持仓表格
        self.position_table = QTableWidget(0, 4)
        self.position_table.setHorizontalHeaderLabels(["股票代码", "持仓数量", "可用数量", "成本"])
        
        # 设置表格样式
        header = self.position_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Stretch)
        
        self.position_table.setAlternatingRowColors(True)
        self.position_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.position_table.setMinimumHeight(200)
        
        position_layout.addWidget(self.position_table)
        parent_layout.addWidget(position_group)
        
    def create_status_bar(self):
        """创建底部状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 添加状态信息
        self.status_bar.showMessage("就绪")
        
        # 添加时间标签
        self.time_label = QLabel()
        self.status_bar.addPermanentWidget(self.time_label)
        
    def init_account_table(self):
        """初始化账户信息表格"""
        items = [
            ("总资产", "0.00"),
            ("可用资金", "0.00"),
            ("持仓市值", "0.00"),
            ("今日盈亏", "0.00")
        ]
        
        for row, (item, value) in enumerate(items):
            self.account_table.setItem(row, 0, QTableWidgetItem(item))
            amount_item = QTableWidgetItem(value)
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.account_table.setItem(row, 1, amount_item)
            
    def setup_timer(self):
        """设置定时器"""
        # 更新时间定时器
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)  # 每秒更新
        
        # 数据更新定时器
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self.update_data)
        self.data_timer.start(5000)  # 每5秒更新
        
    def setup_style(self):
        """设置界面样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
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
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
                alternate-background-color: #f8f8f8;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QComboBox, QSpinBox, QDoubleSpinBox {
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
            QFrame {
                background-color: #e8e8e8;
                border: 1px solid #ccc;
            }
        """)
        
    def toggle_connection(self):
        """切换连接状态"""
        if not self.is_connected:
            self.connect_to_trading()
        else:
            self.disconnect_from_trading()
            
    def connect_to_trading(self):
        """连接到交易服务"""
        try:
            if EASYXT_AVAILABLE and self.easyxt:
                # 尝试连接
                success = self.easyxt.connect()
                if success:
                    self.is_connected = True
                    self.connection_status_label.setText("🟢 已连接")
                    self.connect_btn.setText("🔌 断开连接")
                    self.status_bar.showMessage("交易服务连接成功")
                    
                    # 获取账户信息
                    self.refresh_account_info()
                else:
                    QMessageBox.warning(self, "连接失败", "无法连接到交易服务，请检查配置")
            else:
                # 模拟连接
                self.is_connected = True
                self.connection_status_label.setText("🟡 模拟连接")
                self.connect_btn.setText("🔌 断开连接")
                self.status_bar.showMessage("模拟交易模式")
                self.load_demo_data()
                
        except Exception as e:
            QMessageBox.critical(self, "连接错误", f"连接失败: {str(e)}")
            
    def disconnect_from_trading(self):
        """断开交易服务连接"""
        try:
            if EASYXT_AVAILABLE and self.easyxt:
                self.easyxt.disconnect()
                
            self.is_connected = False
            self.connection_status_label.setText("🔴 未连接")
            self.connect_btn.setText("🔌 连接交易服务")
            self.status_bar.showMessage("已断开连接")
            
            # 清空数据
            self.clear_data()
            
        except Exception as e:
            QMessageBox.warning(self, "断开连接", f"断开连接时出错: {str(e)}")
            
    def refresh_account_info(self):
        """刷新账户信息"""
        try:
            if self.is_connected and EASYXT_AVAILABLE and self.easyxt:
                # 获取真实账户信息
                account_info = self.easyxt.get_account_info()
                if account_info:
                    self.update_account_display(account_info)
                    
                # 获取持仓信息
                positions = self.easyxt.get_positions()
                if positions:
                    self.update_position_display(positions)
                    
        except Exception as e:
            logger.info(f"刷新账户信息失败: {e}")
            
    def load_demo_data(self):
        """加载演示数据"""
        # 模拟账户数据
        demo_account = {
            'total_asset': 100000.00,
            'available_cash': 50000.00,
            'market_value': 50000.00,
            'today_pnl': 1500.00
        }
        self.update_account_display(demo_account)
        
        # 模拟持仓数据
        demo_positions = [
            {'stock_code': '000001.SZ', 'volume': 1000, 'available_volume': 1000, 'cost_price': 12.50},
            {'stock_code': '600000.SH', 'volume': 500, 'available_volume': 500, 'cost_price': 8.80},
        ]
        self.update_position_display(demo_positions)
        
    def update_account_display(self, account_info):
        """更新账户信息显示"""
        items = [
            ("总资产", f"{account_info.get('total_asset', 0):.2f}"),
            ("可用资金", f"{account_info.get('available_cash', 0):.2f}"),
            ("持仓市值", f"{account_info.get('market_value', 0):.2f}"),
            ("今日盈亏", f"{account_info.get('today_pnl', 0):.2f}")
        ]
        
        for row, (item, value) in enumerate(items):
            amount_item = QTableWidgetItem(value)
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            # 根据盈亏设置颜色
            if item == "今日盈亏":
                pnl = account_info.get('today_pnl', 0)
                if pnl > 0:
                    amount_item.setForeground(QColor(255, 0, 0))  # 红色
                elif pnl < 0:
                    amount_item.setForeground(QColor(0, 128, 0))  # 绿色
                    
            self.account_table.setItem(row, 1, amount_item)
            
    def update_position_display(self, positions):
        """更新持仓信息显示"""
        self.position_table.setRowCount(len(positions))
        
        for row, pos in enumerate(positions):
            items = [
                pos.get('stock_code', ''),
                str(pos.get('volume', 0)),
                str(pos.get('available_volume', 0)),
                f"{pos.get('cost_price', 0):.2f}"
            ]
            
            for col, item in enumerate(items):
                table_item = QTableWidgetItem(item)
                if col > 0:  # 数字列右对齐
                    table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.position_table.setItem(row, col, table_item)
                
    def clear_data(self):
        """清空数据显示"""
        # 清空账户信息
        for row in range(self.account_table.rowCount()):
            self.account_table.setItem(row, 1, QTableWidgetItem("0.00"))
            
        # 清空持仓信息
        self.position_table.setRowCount(0)
        
    def buy_stock(self):
        """买入股票"""
        if not self.is_connected:
            QMessageBox.warning(self, "未连接", "请先连接交易服务")
            return
            
        stock_code = self.stock_combo.currentText()
        volume = self.volume_spin.value()
        price = self.price_spin.value()
        
        try:
            if EASYXT_AVAILABLE and self.easyxt:
                # 真实交易
                result = self.easyxt.buy_stock(stock_code, volume, price)
                if result:
                    QMessageBox.information(self, "交易成功", f"买入订单已提交\\n{stock_code} {volume}股 @{price}")
                    self.refresh_account_info()
                else:
                    QMessageBox.warning(self, "交易失败", "买入订单提交失败")
            else:
                # 模拟交易
                QMessageBox.information(self, "模拟交易", 
                                      f"模拟买入: {stock_code}\\n数量: {volume}股\\n价格: {price}")
                
        except Exception as e:
            QMessageBox.critical(self, "交易错误", f"买入失败: {str(e)}")
            
    def sell_stock(self):
        """卖出股票"""
        if not self.is_connected:
            QMessageBox.warning(self, "未连接", "请先连接交易服务")
            return
            
        stock_code = self.stock_combo.currentText()
        volume = self.volume_spin.value()
        price = self.price_spin.value()
        
        try:
            if EASYXT_AVAILABLE and self.easyxt:
                # 真实交易
                result = self.easyxt.sell_stock(stock_code, volume, price)
                if result:
                    QMessageBox.information(self, "交易成功", f"卖出订单已提交\\n{stock_code} {volume}股 @{price}")
                    self.refresh_account_info()
                else:
                    QMessageBox.warning(self, "交易失败", "卖出订单提交失败")
            else:
                # 模拟交易
                QMessageBox.information(self, "模拟交易", 
                                      f"模拟卖出: {stock_code}\\n数量: {volume}股\\n价格: {price}")
                
        except Exception as e:
            QMessageBox.critical(self, "交易错误", f"卖出失败: {str(e)}")
            
    def update_time(self):
        """更新时间显示"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.setText(current_time)
        
    def update_data(self):
        """定时更新数据"""
        if self.is_connected:
            self.refresh_account_info()
            
    def closeEvent(self, event):
        """关闭事件"""
        if self.is_connected:
            self.disconnect_from_trading()
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("量化交易系统")
    app.setApplicationVersion("1.0")
    
    # 设置字体
    font = QFont("微软雅黑", 9)
    app.setFont(font)
    
    # 创建主窗口
    window = TradingInterface()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()