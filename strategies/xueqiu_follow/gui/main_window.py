#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雪球跟单系统GUI主窗口
基于PyQt5的雪球跟单策略管理界面
"""

import sys
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import asyncio
import threading

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox,
    QProgressBar, QSplitter, QFrame, QMessageBox,
    QFileDialog, QFormLayout, QScrollArea, QTreeWidget,
    QTreeWidgetItem, QStatusBar, QToolBar, QAction,
    QApplication, QMainWindow
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

# 添加strategies路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from xueqiu_follow.core.xueqiu_collector import XueqiuCollector
    # 直接使用easy_xt的AdvancedTradeAPI
    from xueqiu_follow.core.risk_manager import RiskManager
    from xueqiu_follow.core.strategy_engine import StrategyEngine
    from xueqiu_follow.core.config_manager import ConfigManager
    XUEQIU_AVAILABLE = True
except ImportError:
    XUEQIU_AVAILABLE = False


class XueqiuFollowWidget(QWidget):
    """雪球跟单系统主界面组件"""
    
    # 信号定义
    status_changed = pyqtSignal(str)
    portfolio_updated = pyqtSignal(dict)
    position_updated = pyqtSignal(dict)
    risk_alert = pyqtSignal(str, str)
    
    def __init__(self):
        super().__init__()
        self.strategy_engine = None
        self.is_running = False
        self.config = {}
        self.portfolios = {}
        
        # 定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_data)
        
        self.init_ui()
        self.load_config()
        self.setup_connections()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        
        # 工具栏
        self.create_toolbar(layout)
        
        # 主要内容区域
        self.create_main_content(layout)
        
        # 状态栏
        self.create_status_bar(layout)
        
        self.setWindowTitle("雪球跟单系统")
        self.resize(1200, 800)
    
    def create_toolbar(self, parent_layout):
        """创建工具栏"""
        toolbar_frame = QFrame()
        toolbar_layout = QHBoxLayout(toolbar_frame)
        
        # 启动/停止按钮
        self.start_btn = QPushButton("启动跟单")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.start_btn.clicked.connect(self.start_strategy)
        
        self.stop_btn = QPushButton("停止跟单")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_strategy)
        self.stop_btn.setEnabled(False)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新数据")
        self.refresh_btn.clicked.connect(self.refresh_data)
        
        # 风险报告按钮
        self.risk_report_btn = QPushButton("风险报告")
        self.risk_report_btn.clicked.connect(self.show_risk_report)
        
        # 紧急停止按钮
        self.emergency_stop_btn = QPushButton("紧急停止")
        self.emergency_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF5722;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
        """)
        self.emergency_stop_btn.clicked.connect(self.emergency_stop)
        
        toolbar_layout.addWidget(self.start_btn)
        toolbar_layout.addWidget(self.stop_btn)
        toolbar_layout.addWidget(QFrame())  # 分隔符
        toolbar_layout.addWidget(self.refresh_btn)
        toolbar_layout.addWidget(self.risk_report_btn)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.emergency_stop_btn)
        
        parent_layout.addWidget(toolbar_frame)
    
    def create_main_content(self, parent_layout):
        """创建主要内容区域"""
        # 创建选项卡
        self.tab_widget = QTabWidget()
        
        # 组合监控选项卡
        self.portfolio_tab = self.create_portfolio_tab()
        self.tab_widget.addTab(self.portfolio_tab, "组合监控")
        
        # 持仓管理选项卡
        self.position_tab = self.create_position_tab()
        self.tab_widget.addTab(self.position_tab, "持仓管理")
        
        # 交易记录选项卡
        self.trade_tab = self.create_trade_tab()
        self.tab_widget.addTab(self.trade_tab, "交易记录")
        
        # 风险控制选项卡
        self.risk_tab = self.create_risk_tab()
        self.tab_widget.addTab(self.risk_tab, "风险控制")
        
        # 系统设置选项卡
        self.settings_tab = self.create_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "系统设置")
        
        parent_layout.addWidget(self.tab_widget)
    
    def create_portfolio_tab(self):
        """创建组合监控选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 组合列表
        portfolio_group = QGroupBox("跟单组合列表")
        portfolio_layout = QVBoxLayout(portfolio_group)
        
        self.portfolio_table = QTableWidget()
        self.portfolio_table.setColumnCount(7)
        self.portfolio_table.setHorizontalHeaderLabels([
            "组合名称", "跟单比例", "总资产", "今日收益", "收益率", "状态", "操作"
        ])
        self.portfolio_table.horizontalHeader().setStretchLastSection(True)
        
        portfolio_layout.addWidget(self.portfolio_table)
        layout.addWidget(portfolio_group)
        
        # 组合详情
        detail_group = QGroupBox("组合详情")
        detail_layout = QVBoxLayout(detail_group)
        
        self.portfolio_detail = QTextEdit()
        self.portfolio_detail.setMaximumHeight(150)
        detail_layout.addWidget(self.portfolio_detail)
        
        layout.addWidget(detail_group)
        
        return widget
    
    def create_position_tab(self):
        """创建持仓管理选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 持仓列表
        position_group = QGroupBox("当前持仓")
        position_layout = QVBoxLayout(position_group)
        
        self.position_table = QTableWidget()
        self.position_table.setColumnCount(8)
        self.position_table.setHorizontalHeaderLabels([
            "股票代码", "股票名称", "持仓数量", "可用数量", "成本价", "现价", "盈亏", "盈亏率"
        ])
        self.position_table.horizontalHeader().setStretchLastSection(True)
        
        position_layout.addWidget(self.position_table)
        layout.addWidget(position_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.sync_position_btn = QPushButton("同步持仓")
        self.sync_position_btn.clicked.connect(self.sync_positions)
        
        self.clear_position_btn = QPushButton("清空持仓")
        self.clear_position_btn.clicked.connect(self.clear_positions)
        
        button_layout.addWidget(self.sync_position_btn)
        button_layout.addWidget(self.clear_position_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        return widget
    
    def create_trade_tab(self):
        """创建交易记录选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 交易记录表格
        trade_group = QGroupBox("交易记录")
        trade_layout = QVBoxLayout(trade_group)
        
        self.trade_table = QTableWidget()
        self.trade_table.setColumnCount(8)
        self.trade_table.setHorizontalHeaderLabels([
            "时间", "股票代码", "股票名称", "操作", "数量", "价格", "金额", "状态"
        ])
        self.trade_table.horizontalHeader().setStretchLastSection(True)
        
        trade_layout.addWidget(self.trade_table)
        layout.addWidget(trade_group)
        
        # 统计信息
        stats_group = QGroupBox("交易统计")
        stats_layout = QGridLayout(stats_group)
        
        self.total_trades_label = QLabel("总交易次数: 0")
        self.success_rate_label = QLabel("成功率: 0%")
        self.total_profit_label = QLabel("总盈亏: ¥0.00")
        self.today_trades_label = QLabel("今日交易: 0")
        
        stats_layout.addWidget(self.total_trades_label, 0, 0)
        stats_layout.addWidget(self.success_rate_label, 0, 1)
        stats_layout.addWidget(self.total_profit_label, 1, 0)
        stats_layout.addWidget(self.today_trades_label, 1, 1)
        
        layout.addWidget(stats_group)
        
        return widget
    
    def create_risk_tab(self):
        """创建风险控制选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 风险设置
        risk_settings_group = QGroupBox("风险控制设置")
        risk_settings_layout = QFormLayout(risk_settings_group)
        
        self.max_position_ratio = QDoubleSpinBox()
        self.max_position_ratio.setRange(0.01, 1.0)
        self.max_position_ratio.setSingleStep(0.01)
        self.max_position_ratio.setValue(0.1)
        self.max_position_ratio.setSuffix("%")
        
        self.stop_loss_ratio = QDoubleSpinBox()
        self.stop_loss_ratio.setRange(0.01, 0.5)
        self.stop_loss_ratio.setSingleStep(0.01)
        self.stop_loss_ratio.setValue(0.05)
        self.stop_loss_ratio.setSuffix("%")
        
        self.max_daily_loss = QDoubleSpinBox()
        self.max_daily_loss.setRange(100, 100000)
        self.max_daily_loss.setSingleStep(100)
        self.max_daily_loss.setValue(5000)
        self.max_daily_loss.setPrefix("¥")
        
        risk_settings_layout.addRow("单股最大仓位:", self.max_position_ratio)
        risk_settings_layout.addRow("止损比例:", self.stop_loss_ratio)
        risk_settings_layout.addRow("日最大亏损:", self.max_daily_loss)
        
        layout.addWidget(risk_settings_group)
        
        # 风险监控
        risk_monitor_group = QGroupBox("风险监控")
        risk_monitor_layout = QVBoxLayout(risk_monitor_group)
        
        self.risk_status = QTextEdit()
        self.risk_status.setMaximumHeight(200)
        risk_monitor_layout.addWidget(self.risk_status)
        
        layout.addWidget(risk_monitor_group)
        
        return widget
    
    def create_settings_tab(self):
        """创建系统设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 账户设置
        account_group = QGroupBox("账户设置")
        account_layout = QFormLayout(account_group)
        
        self.account_id = QLineEdit()
        self.account_password = QLineEdit()
        self.account_password.setEchoMode(QLineEdit.Password)
        
        account_layout.addRow("账户ID:", self.account_id)
        account_layout.addRow("账户密码:", self.account_password)
        
        layout.addWidget(account_group)
        
        # 雪球设置
        xueqiu_group = QGroupBox("雪球设置")
        xueqiu_layout = QFormLayout(xueqiu_group)
        
        self.xueqiu_cookie = QTextEdit()
        self.xueqiu_cookie.setMaximumHeight(100)
        self.sync_interval = QSpinBox()
        self.sync_interval.setRange(1, 60)
        self.sync_interval.setValue(3)
        self.sync_interval.setSuffix("秒")
        
        xueqiu_layout.addRow("雪球Cookie:", self.xueqiu_cookie)
        xueqiu_layout.addRow("同步间隔:", self.sync_interval)
        
        layout.addWidget(xueqiu_group)
        
        # 保存按钮
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self.save_config)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        
        return widget
    
    def create_status_bar(self, parent_layout):
        """创建状态栏"""
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        
        self.status_label = QLabel("就绪")
        self.connection_status = QLabel("未连接")
        self.last_update_time = QLabel("最后更新: --")
        
        status_layout.addWidget(QLabel("状态:"))
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.connection_status)
        status_layout.addWidget(self.last_update_time)
        
        parent_layout.addWidget(status_frame)
    
    def setup_connections(self):
        """设置信号连接"""
        self.status_changed.connect(self.update_status)
        self.portfolio_updated.connect(self.update_portfolio_display)
        self.position_updated.connect(self.update_position_display)
        self.risk_alert.connect(self.show_risk_alert)
    
    def load_config(self):
        """加载配置"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                    self.apply_config()
        except Exception as e:
            QMessageBox.warning(self, "警告", f"加载配置失败: {str(e)}")
    
    def apply_config(self):
        """应用配置到界面"""
        if 'account' in self.config:
            account = self.config['account']
            self.account_id.setText(account.get('account_id', ''))
        
        if 'xueqiu' in self.config:
            xueqiu = self.config['xueqiu']
            self.xueqiu_cookie.setPlainText(xueqiu.get('cookie', ''))
            self.sync_interval.setValue(xueqiu.get('sync_interval', 3))
        
        if 'risk' in self.config:
            risk = self.config['risk']
            self.max_position_ratio.setValue(risk.get('max_position_ratio', 0.1))
            self.stop_loss_ratio.setValue(risk.get('stop_loss_ratio', 0.05))
            self.max_daily_loss.setValue(risk.get('max_daily_loss', 5000))
    
    def save_config(self):
        """保存配置"""
        try:
            self.config.update({
                'account': {
                    'account_id': self.account_id.text(),
                    'password': self.account_password.text()
                },
                'xueqiu': {
                    'cookie': self.xueqiu_cookie.toPlainText(),
                    'sync_interval': self.sync_interval.value()
                },
                'risk': {
                    'max_position_ratio': self.max_position_ratio.value(),
                    'stop_loss_ratio': self.stop_loss_ratio.value(),
                    'max_daily_loss': self.max_daily_loss.value()
                }
            })
            
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            
            QMessageBox.information(self, "成功", "配置保存成功!")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")
    
    def start_strategy(self):
        """启动策略"""
        try:
            if not XUEQIU_AVAILABLE:
                QMessageBox.warning(self, "警告", "雪球跟单模块不可用，请检查依赖")
                return
            
            # 初始化配置管理器与策略引擎（必须传入 ConfigManager 实例）
            config_manager = ConfigManager()
            self.strategy_engine = StrategyEngine(config_manager)
            
            # 启动策略
            self.strategy_engine.start()
            
            self.is_running = True
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            
            # 启动定时更新
            self.update_timer.start(self.sync_interval.value() * 1000)
            
            self.status_changed.emit("运行中")
            QMessageBox.information(self, "成功", "雪球跟单策略启动成功!")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动策略失败: {str(e)}")
    
    def stop_strategy(self):
        """停止策略"""
        try:
            if self.strategy_engine:
                self.strategy_engine.stop()
            
            self.is_running = False
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            
            # 停止定时更新
            self.update_timer.stop()
            
            self.status_changed.emit("已停止")
            QMessageBox.information(self, "成功", "雪球跟单策略已停止!")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"停止策略失败: {str(e)}")
    
    def emergency_stop(self):
        """紧急停止"""
        reply = QMessageBox.question(
            self, "确认", "确定要紧急停止所有交易吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.strategy_engine:
                    self.strategy_engine.emergency_stop()
                
                self.stop_strategy()
                self.status_changed.emit("紧急停止")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"紧急停止失败: {str(e)}")
    
    def refresh_data(self):
        """刷新数据"""
        try:
            if self.strategy_engine:
                # 刷新组合数据
                portfolios = self.strategy_engine.get_portfolios()
                self.portfolio_updated.emit(portfolios)
                
                # 刷新持仓数据
                positions = self.strategy_engine.get_positions()
                self.position_updated.emit(positions)
            
            self.last_update_time.setText(f"最后更新: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            QMessageBox.warning(self, "警告", f"刷新数据失败: {str(e)}")
    
    def update_data(self):
        """定时更新数据"""
        if self.is_running:
            self.refresh_data()
    
    def sync_positions(self):
        """同步持仓"""
        try:
            if self.strategy_engine:
                self.strategy_engine.sync_positions()
                QMessageBox.information(self, "成功", "持仓同步完成!")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"同步持仓失败: {str(e)}")
    
    def clear_positions(self):
        """清空持仓"""
        reply = QMessageBox.question(
            self, "确认", "确定要清空所有持仓吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.strategy_engine:
                    self.strategy_engine.clear_positions()
                    QMessageBox.information(self, "成功", "持仓清空完成!")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"清空持仓失败: {str(e)}")
    
    def show_risk_report(self):
        """显示风险报告"""
        try:
            if self.strategy_engine:
                risk_report = self.strategy_engine.get_risk_report()
                self.risk_status.setPlainText(risk_report)
                self.tab_widget.setCurrentIndex(3)  # 切换到风险控制选项卡
        except Exception as e:
            QMessageBox.warning(self, "警告", f"获取风险报告失败: {str(e)}")
    
    def update_status(self, status):
        """更新状态"""
        self.status_label.setText(status)
    
    def update_portfolio_display(self, portfolios):
        """更新组合显示"""
        self.portfolio_table.setRowCount(len(portfolios))
        
        for i, (name, data) in enumerate(portfolios.items()):
            self.portfolio_table.setItem(i, 0, QTableWidgetItem(name))
            self.portfolio_table.setItem(i, 1, QTableWidgetItem(f"{data.get('ratio', 0):.2%}"))
            self.portfolio_table.setItem(i, 2, QTableWidgetItem(f"¥{data.get('total_value', 0):,.2f}"))
            self.portfolio_table.setItem(i, 3, QTableWidgetItem(f"¥{data.get('daily_pnl', 0):,.2f}"))
            self.portfolio_table.setItem(i, 4, QTableWidgetItem(f"{data.get('return_rate', 0):.2%}"))
            self.portfolio_table.setItem(i, 5, QTableWidgetItem(data.get('status', '未知')))
    
    def update_position_display(self, positions):
        """更新持仓显示"""
        self.position_table.setRowCount(len(positions))
        
        for i, (code, data) in enumerate(positions.items()):
            self.position_table.setItem(i, 0, QTableWidgetItem(code))
            self.position_table.setItem(i, 1, QTableWidgetItem(data.get('name', '')))
            self.position_table.setItem(i, 2, QTableWidgetItem(str(data.get('volume', 0))))
            self.position_table.setItem(i, 3, QTableWidgetItem(str(data.get('available', 0))))
            self.position_table.setItem(i, 4, QTableWidgetItem(f"{data.get('cost_price', 0):.2f}"))
            self.position_table.setItem(i, 5, QTableWidgetItem(f"{data.get('current_price', 0):.2f}"))
            self.position_table.setItem(i, 6, QTableWidgetItem(f"{data.get('pnl', 0):.2f}"))
            self.position_table.setItem(i, 7, QTableWidgetItem(f"{data.get('pnl_ratio', 0):.2%}"))
    
    def show_risk_alert(self, level, message):
        """显示风险警告"""
        if level == "critical":
            QMessageBox.critical(self, "严重风险警告", message)
        elif level == "warning":
            QMessageBox.warning(self, "风险警告", message)
        else:
            QMessageBox.information(self, "风险提示", message)


class XueqiuFollowMainWindow(QMainWindow):
    """雪球跟单系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("雪球跟单系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 设置中央组件
        self.xueqiu_widget = XueqiuFollowWidget()
        self.setCentralWidget(self.xueqiu_widget)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建状态栏
        self.statusBar().showMessage("雪球跟单系统就绪")
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        # 导入配置
        import_action = QAction('导入配置', self)
        import_action.triggered.connect(self.import_config)
        file_menu.addAction(import_action)
        
        # 导出配置
        export_action = QAction('导出配置', self)
        export_action.triggered.connect(self.export_config)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        # 关于
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def import_config(self):
        """导入配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入配置文件", "", "JSON Files (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.xueqiu_widget.config = config
                self.xueqiu_widget.apply_config()
                QMessageBox.information(self, "成功", "配置导入成功!")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入配置失败: {str(e)}")
    
    def export_config(self):
        """导出配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出配置文件", "", "JSON Files (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.xueqiu_widget.config, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "成功", "配置导出成功!")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出配置失败: {str(e)}")
    
    def show_about(self):
        """显示关于信息"""
        QMessageBox.about(self, "关于", 
                         "雪球跟单系统\n\n"
                         "基于PyQt5的专业雪球跟单交易系统\n"
                         "支持多组合跟单、风险控制、实时监控\n\n"
                         "版本: V1.0\n"
                         "作者: EasyXT团队")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 设置暗色主题
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, QColor(0, 0, 0))
    palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    app.setPalette(palette)
    
    window = XueqiuFollowMainWindow()
    window.show()
    
    sys.exit(app.exec_())