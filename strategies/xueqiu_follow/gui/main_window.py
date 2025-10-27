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
    from xueqiu_follow.start_xueqiu_follow_easyxt import XueqiuFollowSystem, check_qmt_config, test_qmt_connection
    XUEQIU_AVAILABLE = True
except ImportError:
    XUEQIU_AVAILABLE = False


class XueqiuFollowWidget(QWidget):
    """雪球跟单系统主界面组件"""
    
    # 信号定义
    status_changed = pyqtSignal(str)
    portfolio_updated = pyqtSignal(list)
    position_updated = pyqtSignal(dict)
    risk_alert = pyqtSignal(str, str)
    
    def __init__(self):
        super().__init__()
        self.strategy_engine = None
        self.system = None  # 复用 start_xueqiu_follow_easyxt 的系统类
        self.is_running = False
        self.config = {}
        self.portfolios = {}
        # 名称缓存，避免重复查询
        self._code_name_cache = {}
        # 异步运行所需
        self._loop = None
        self._loop_thread = None
        
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
            "组合名称", "跟单比例", "总资产", "组合收益", "收益率", "状态", "操作"
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

    def _render_today_orders_table(self, orders_df):
        """将当日委托渲染到交易记录表格"""
        try:
            if orders_df is None or getattr(orders_df, 'empty', True):
                self.trade_table.setRowCount(0)
                return
            rows = len(orders_df)
            self.trade_table.setRowCount(rows)
            for i, (_, row) in enumerate(orders_df.iterrows()):
                def _get(k, default=''):
                    try:
                        return row.get(k, default)
                    except Exception:
                        return default
                t = _get('order_time') or _get('entrust_time') or _get('time') or ''
                code = _get('stock_code') or _get('code') or _get('symbol') or ''
                name = _get('stock_name') or _get('name') or ''
                side = (_get('order_type') or _get('entrust_bs') or _get('side') or '').replace('买入','买').replace('卖出','卖')
                vol = _get('order_volume') or _get('entrust_amount') or _get('qty') or 0
                price = _get('price') or _get('entrust_price') or _get('order_price') or 0
                amount = _get('amount') or (float(price) * float(vol) if price and vol else 0)
                status = _get('order_status') or _get('entrust_status') or _get('status') or ''

                self.trade_table.setItem(i, 0, QTableWidgetItem(str(t)))
                self.trade_table.setItem(i, 1, QTableWidgetItem(str(code)))
                self.trade_table.setItem(i, 2, QTableWidgetItem(str(name)))
                self.trade_table.setItem(i, 3, QTableWidgetItem(str(side)))
                self.trade_table.setItem(i, 4, QTableWidgetItem(str(vol)))
                self.trade_table.setItem(i, 5, QTableWidgetItem(f"{float(price):.2f}" if price else ""))
                self.trade_table.setItem(i, 6, QTableWidgetItem(f"{float(amount):.2f}" if amount else ""))
                self.trade_table.setItem(i, 7, QTableWidgetItem(str(status)))
        except Exception:
            pass

    def _render_today_trades_table(self, trades_df):
        """将当日成交渲染到交易记录表格（优先显示）"""
        try:
            if trades_df is None or getattr(trades_df, 'empty', True):
                self.trade_table.setRowCount(0)
                return
            rows = len(trades_df)
            self.trade_table.setRowCount(rows)
            for i, (_, row) in enumerate(trades_df.iterrows()):
                def _get(k, default=''):
                    try:
                        return row.get(k, default)
                    except Exception:
                        return default
                t = _get('traded_time') or _get('time') or ''
                code = _get('stock_code') or _get('code') or _get('symbol') or ''
                name = _get('stock_name') or _get('name') or ''
                if not name:
                    try:
                        from xtquant import xtdata as _xt
                        norm = code
                        if not norm or ('.' not in norm):
                            from easy_xt.utils import StockCodeUtils as _Scu
                            norm = _Scu.normalize_code(code)
                        cached = getattr(self, '_code_name_cache', {}).get(norm)
                        if cached:
                            name = cached
                        else:
                            info = _xt.get_instrument_detail(norm)
                            name = (info.get('InstrumentName') or info.get('cn_name')) if isinstance(info, dict) else ''
                            if name:
                                self._code_name_cache[norm] = name
                    except Exception:
                        pass
                side = (_get('order_type') or _get('side') or '').replace('买入','买').replace('卖出','卖')
                vol = _get('traded_volume') or _get('volume') or 0
                price = _get('traded_price') or _get('price') or 0
                amount = _get('traded_amount') or (float(price) * float(vol) if price and vol else 0)
                status = '成交'

                self.trade_table.setItem(i, 0, QTableWidgetItem(str(t)))
                self.trade_table.setItem(i, 1, QTableWidgetItem(str(code)))
                self.trade_table.setItem(i, 2, QTableWidgetItem(str(name)))
                self.trade_table.setItem(i, 3, QTableWidgetItem(str(side)))
                self.trade_table.setItem(i, 4, QTableWidgetItem(str(vol)))
                self.trade_table.setItem(i, 5, QTableWidgetItem(f"{float(price):.2f}" if price else ""))
                self.trade_table.setItem(i, 6, QTableWidgetItem(f"{float(amount):.2f}" if amount else ""))
                self.trade_table.setItem(i, 7, QTableWidgetItem(status))
        except Exception:
            pass
    
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

    def _render_today_orders_table(self, orders_df):
        """将当日委托渲染到交易记录表格"""
        try:
            if orders_df is None or getattr(orders_df, 'empty', True):
                self.trade_table.setRowCount(0)
                return
            rows = len(orders_df)
            self.trade_table.setRowCount(rows)
            for i, (_, row) in enumerate(orders_df.iterrows()):
                def _get(k, default=''):
                    try:
                        return row.get(k, default)
                    except Exception:
                        return default
                t = _get('order_time') or _get('entrust_time') or _get('time') or ''
                code = _get('stock_code') or _get('code') or _get('symbol') or ''
                name = _get('stock_name') or _get('name') or ''
                side = (_get('order_type') or _get('entrust_bs') or _get('side') or '').replace('买入','买').replace('卖出','卖')
                vol = _get('order_volume') or _get('entrust_amount') or _get('qty') or 0
                price = _get('price') or _get('entrust_price') or _get('order_price') or 0
                amount = _get('amount') or (float(price) * float(vol) if price and vol else 0)
                status = _get('order_status') or _get('entrust_status') or _get('status') or ''

                self.trade_table.setItem(i, 0, QTableWidgetItem(str(t)))
                self.trade_table.setItem(i, 1, QTableWidgetItem(str(code)))
                self.trade_table.setItem(i, 2, QTableWidgetItem(str(name)))
                self.trade_table.setItem(i, 3, QTableWidgetItem(str(side)))
                self.trade_table.setItem(i, 4, QTableWidgetItem(str(vol)))
                self.trade_table.setItem(i, 5, QTableWidgetItem(f"{float(price):.2f}" if price else ""))
                self.trade_table.setItem(i, 6, QTableWidgetItem(f"{float(amount):.2f}" if amount else ""))
                self.trade_table.setItem(i, 7, QTableWidgetItem(str(status)))
        except Exception:
            pass

    def _render_today_trades_table(self, trades_df):
        """将当日成交渲染到交易记录表格（优先显示）"""
        try:
            if trades_df is None or getattr(trades_df, 'empty', True):
                self.trade_table.setRowCount(0)
                return
            rows = len(trades_df)
            self.trade_table.setRowCount(rows)
            for i, (_, row) in enumerate(trades_df.iterrows()):
                def _get(k, default=''):
                    try:
                        return row.get(k, default)
                    except Exception:
                        return default
                t = _get('traded_time') or _get('time') or ''
                code = _get('stock_code') or _get('code') or _get('symbol') or ''
                name = _get('stock_name') or _get('name') or ''
                if not name:
                    try:
                        from xtquant import xtdata as _xt
                        norm = code
                        if not norm or ('.' not in norm):
                            from easy_xt.utils import StockCodeUtils as _Scu
                            norm = _Scu.normalize_code(code)
                        cached = getattr(self, '_code_name_cache', {}).get(norm)
                        if cached:
                            name = cached
                        else:
                            info = _xt.get_instrument_detail(norm)
                            name = (info.get('InstrumentName') or info.get('cn_name')) if isinstance(info, dict) else ''
                            if name:
                                self._code_name_cache[norm] = name
                    except Exception:
                        pass
                side = (_get('order_type') or _get('side') or '').replace('买入','买').replace('卖出','卖')
                vol = _get('traded_volume') or _get('volume') or 0
                price = _get('traded_price') or _get('price') or 0
                amount = _get('traded_amount') or (float(price) * float(vol) if price and vol else 0)
                status = '成交'

                self.trade_table.setItem(i, 0, QTableWidgetItem(str(t)))
                self.trade_table.setItem(i, 1, QTableWidgetItem(str(code)))
                self.trade_table.setItem(i, 2, QTableWidgetItem(str(name)))
                self.trade_table.setItem(i, 3, QTableWidgetItem(str(side)))
                self.trade_table.setItem(i, 4, QTableWidgetItem(str(vol)))
                self.trade_table.setItem(i, 5, QTableWidgetItem(f"{float(price):.2f}" if price else ""))
                self.trade_table.setItem(i, 6, QTableWidgetItem(f"{float(amount):.2f}" if amount else ""))
                self.trade_table.setItem(i, 7, QTableWidgetItem(status))
        except Exception:
            pass
    
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

    def _render_today_orders_table(self, orders_df):
        """将当日委托渲染到交易记录表格"""
        try:
            if orders_df is None or getattr(orders_df, 'empty', True):
                self.trade_table.setRowCount(0)
                return
            rows = len(orders_df)
            self.trade_table.setRowCount(rows)
            for i, (_, row) in enumerate(orders_df.iterrows()):
                def _get(k, default=''):
                    try:
                        return row.get(k, default)
                    except Exception:
                        return default
                t = _get('order_time') or _get('entrust_time') or _get('time') or ''
                code = _get('stock_code') or _get('code') or _get('symbol') or ''
                name = _get('stock_name') or _get('name') or ''
                side = (_get('order_type') or _get('entrust_bs') or _get('side') or '').replace('买入','买').replace('卖出','卖')
                vol = _get('order_volume') or _get('entrust_amount') or _get('qty') or 0
                price = _get('price') or _get('entrust_price') or _get('order_price') or 0
                amount = _get('amount') or (float(price) * float(vol) if price and vol else 0)
                status = _get('order_status') or _get('entrust_status') or _get('status') or ''

                self.trade_table.setItem(i, 0, QTableWidgetItem(str(t)))
                self.trade_table.setItem(i, 1, QTableWidgetItem(str(code)))
                self.trade_table.setItem(i, 2, QTableWidgetItem(str(name)))
                self.trade_table.setItem(i, 3, QTableWidgetItem(str(side)))
                self.trade_table.setItem(i, 4, QTableWidgetItem(str(vol)))
                self.trade_table.setItem(i, 5, QTableWidgetItem(f"{float(price):.2f}" if price else ""))
                self.trade_table.setItem(i, 6, QTableWidgetItem(f"{float(amount):.2f}" if amount else ""))
                self.trade_table.setItem(i, 7, QTableWidgetItem(str(status)))
        except Exception:
            pass

    def _render_today_trades_table(self, trades_df):
        """将当日成交渲染到交易记录表格（优先显示）"""
        try:
            if trades_df is None or getattr(trades_df, 'empty', True):
                self.trade_table.setRowCount(0)
                return
            rows = len(trades_df)
            self.trade_table.setRowCount(rows)
            for i, (_, row) in enumerate(trades_df.iterrows()):
                def _get(k, default=''):
                    try:
                        return row.get(k, default)
                    except Exception:
                        return default
                t = _get('traded_time') or _get('time') or ''
                code = _get('stock_code') or _get('code') or _get('symbol') or ''
                name = _get('stock_name') or _get('name') or ''
                if not name:
                    try:
                        from xtquant import xtdata as _xt
                        norm = code
                        if not norm or ('.' not in norm):
                            from easy_xt.utils import StockCodeUtils as _Scu
                            norm = _Scu.normalize_code(code)
                        cached = getattr(self, '_code_name_cache', {}).get(norm)
                        if cached:
                            name = cached
                        else:
                            info = _xt.get_instrument_detail(norm)
                            name = (info.get('InstrumentName') or info.get('cn_name')) if isinstance(info, dict) else ''
                            if name:
                                self._code_name_cache[norm] = name
                    except Exception:
                        pass
                side = (_get('order_type') or _get('side') or '').replace('买入','买').replace('卖出','卖')
                vol = _get('traded_volume') or _get('volume') or 0
                price = _get('traded_price') or _get('price') or 0
                amount = _get('traded_amount') or (float(price) * float(vol) if price and vol else 0)
                status = '成交'

                self.trade_table.setItem(i, 0, QTableWidgetItem(str(t)))
                self.trade_table.setItem(i, 1, QTableWidgetItem(str(code)))
                self.trade_table.setItem(i, 2, QTableWidgetItem(str(name)))
                self.trade_table.setItem(i, 3, QTableWidgetItem(str(side)))
                self.trade_table.setItem(i, 4, QTableWidgetItem(str(vol)))
                self.trade_table.setItem(i, 5, QTableWidgetItem(f"{float(price):.2f}" if price else ""))
                self.trade_table.setItem(i, 6, QTableWidgetItem(f"{float(amount):.2f}" if amount else ""))
                self.trade_table.setItem(i, 7, QTableWidgetItem(status))
        except Exception:
            pass
    
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

    def _render_today_orders_table(self, orders_df):
        """将当日委托渲染到交易记录表格"""
        try:
            if orders_df is None or getattr(orders_df, 'empty', True):
                self.trade_table.setRowCount(0)
                return
            rows = len(orders_df)
            self.trade_table.setRowCount(rows)
            for i, (_, row) in enumerate(orders_df.iterrows()):
                def _get(k, default=''):
                    try:
                        return row.get(k, default)
                    except Exception:
                        return default
                t = _get('order_time') or _get('entrust_time') or _get('time') or ''
                code = _get('stock_code') or _get('code') or _get('symbol') or ''
                name = _get('stock_name') or _get('name') or ''
                side = (_get('order_type') or _get('entrust_bs') or _get('side') or '').replace('买入','买').replace('卖出','卖')
                vol = _get('order_volume') or _get('entrust_amount') or _get('qty') or 0
                price = _get('price') or _get('entrust_price') or _get('order_price') or 0
                amount = _get('amount') or (float(price) * float(vol) if price and vol else 0)
                status = _get('order_status') or _get('entrust_status') or _get('status') or ''

                self.trade_table.setItem(i, 0, QTableWidgetItem(str(t)))
                self.trade_table.setItem(i, 1, QTableWidgetItem(str(code)))
                self.trade_table.setItem(i, 2, QTableWidgetItem(str(name)))
                self.trade_table.setItem(i, 3, QTableWidgetItem(str(side)))
                self.trade_table.setItem(i, 4, QTableWidgetItem(str(vol)))
                self.trade_table.setItem(i, 5, QTableWidgetItem(f"{float(price):.2f}" if price else ""))
                self.trade_table.setItem(i, 6, QTableWidgetItem(f"{float(amount):.2f}" if amount else ""))
                self.trade_table.setItem(i, 7, QTableWidgetItem(str(status)))
        except Exception:
            pass

    def _render_today_trades_table(self, trades_df):
        """将当日成交渲染到交易记录表格（优先显示）"""
        try:
            if trades_df is None or getattr(trades_df, 'empty', True):
                self.trade_table.setRowCount(0)
                return
            rows = len(trades_df)
            self.trade_table.setRowCount(rows)
            for i, (_, row) in enumerate(trades_df.iterrows()):
                def _get(k, default=''):
                    try:
                        return row.get(k, default)
                    except Exception:
                        return default
                t = _get('traded_time') or _get('time') or ''
                code = _get('stock_code') or _get('code') or _get('symbol') or ''
                name = _get('stock_name') or _get('name') or ''
                if not name:
                    try:
                        from xtquant import xtdata as _xt
                        norm = code
                        if not norm or ('.' not in norm):
                            from easy_xt.utils import StockCodeUtils as _Scu
                            norm = _Scu.normalize_code(code)
                        cached = getattr(self, '_code_name_cache', {}).get(norm)
                        if cached:
                            name = cached
                        else:
                            info = _xt.get_instrument_detail(norm)
                            name = (info.get('InstrumentName') or info.get('cn_name')) if isinstance(info, dict) else ''
                            if name:
                                self._code_name_cache[norm] = name
                    except Exception:
                        pass
                side = (_get('order_type') or _get('side') or '').replace('买入','买').replace('卖出','卖')
                vol = _get('traded_volume') or _get('volume') or 0
                price = _get('traded_price') or _get('price') or 0
                amount = _get('traded_amount') or (float(price) * float(vol) if price and vol else 0)
                status = '成交'

                self.trade_table.setItem(i, 0, QTableWidgetItem(str(t)))
                self.trade_table.setItem(i, 1, QTableWidgetItem(str(code)))
                self.trade_table.setItem(i, 2, QTableWidgetItem(str(name)))
                self.trade_table.setItem(i, 3, QTableWidgetItem(str(side)))
                self.trade_table.setItem(i, 4, QTableWidgetItem(str(vol)))
                self.trade_table.setItem(i, 5, QTableWidgetItem(f"{float(price):.2f}" if price else ""))
                self.trade_table.setItem(i, 6, QTableWidgetItem(f"{float(amount):.2f}" if amount else ""))
                self.trade_table.setItem(i, 7, QTableWidgetItem(status))
        except Exception:
            pass
    
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

    def _render_today_orders_table(self, orders_df):
        """将当日委托渲染到交易记录表格"""
        try:
            if orders_df is None or getattr(orders_df, 'empty', True):
                self.trade_table.setRowCount(0)
                return
            rows = len(orders_df)
            self.trade_table.setRowCount(rows)
            for i, (_, row) in enumerate(orders_df.iterrows()):
                def _get(k, default=''):
                    try:
                        return row.get(k, default)
                    except Exception:
                        return default
                t = _get('order_time') or _get('entrust_time') or _get('time') or ''
                code = _get('stock_code') or _get('code') or _get('symbol') or ''
                name = _get('stock_name') or _get('name') or ''
                side = (_get('order_type') or _get('entrust_bs') or _get('side') or '').replace('买入','买').replace('卖出','卖')
                vol = _get('order_volume') or _get('entrust_amount') or _get('qty') or 0
                price = _get('price') or _get('entrust_price') or _get('order_price') or 0
                amount = _get('amount') or (float(price) * float(vol) if price and vol else 0)
                status = _get('order_status') or _get('entrust_status') or _get('status') or ''

                self.trade_table.setItem(i, 0, QTableWidgetItem(str(t)))
                self.trade_table.setItem(i, 1, QTableWidgetItem(str(code)))
                self.trade_table.setItem(i, 2, QTableWidgetItem(str(name)))
                self.trade_table.setItem(i, 3, QTableWidgetItem(str(side)))
                self.trade_table.setItem(i, 4, QTableWidgetItem(str(vol)))
                self.trade_table.setItem(i, 5, QTableWidgetItem(f"{float(price):.2f}" if price else ""))
                self.trade_table.setItem(i, 6, QTableWidgetItem(f"{float(amount):.2f}" if amount else ""))
                self.trade_table.setItem(i, 7, QTableWidgetItem(str(status)))
        except Exception:
            pass

    def _render_today_trades_table(self, trades_df):
        """将当日成交渲染到交易记录表格（优先显示）"""
        try:
            if trades_df is None or getattr(trades_df, 'empty', True):
                self.trade_table.setRowCount(0)
                return
            rows = len(trades_df)
            self.trade_table.setRowCount(rows)
            for i, (_, row) in enumerate(trades_df.iterrows()):
                def _get(k, default=''):
                    try:
                        return row.get(k, default)
                    except Exception:
                        return default
                t = _get('traded_time') or _get('time') or ''
                code = _get('stock_code') or _get('code') or _get('symbol') or ''
                name = _get('stock_name') or _get('name') or ''
                if not name:
                    try:
                        from xtquant import xtdata as _xt
                        norm = code
                        if not norm or ('.' not in norm):
                            from easy_xt.utils import StockCodeUtils as _Scu
                            norm = _Scu.normalize_code(code)
                        cached = getattr(self, '_code_name_cache', {}).get(norm)
                        if cached:
                            name = cached
                        else:
                            info = _xt.get_instrument_detail(norm)
                            name = (info.get('InstrumentName') or info.get('cn_name')) if isinstance(info, dict) else ''
                            if name:
                                self._code_name_cache[norm] = name
                    except Exception:
                        pass
                side = (_get('order_type') or _get('side') or '').replace('买入','买').replace('卖出','卖')
                vol = _get('traded_volume') or _get('volume') or 0
                price = _get('traded_price') or _get('price') or 0
                amount = _get('traded_amount') or (float(price) * float(vol) if price and vol else 0)
                status = '成交'

                self.trade_table.setItem(i, 0, QTableWidgetItem(str(t)))
                self.trade_table.setItem(i, 1, QTableWidgetItem(str(code)))
                self.trade_table.setItem(i, 2, QTableWidgetItem(str(name)))
                self.trade_table.setItem(i, 3, QTableWidgetItem(str(side)))
                self.trade_table.setItem(i, 4, QTableWidgetItem(str(vol)))
                self.trade_table.setItem(i, 5, QTableWidgetItem(f"{float(price):.2f}" if price else ""))
                self.trade_table.setItem(i, 6, QTableWidgetItem(f"{float(amount):.2f}" if amount else ""))
                self.trade_table.setItem(i, 7, QTableWidgetItem(status))
        except Exception:
            pass
    
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
        """加载配置（优先 unified_config.json）"""
        try:
            base_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
            unified_path = os.path.normpath(os.path.join(base_dir, 'unified_config.json'))
            legacy_path = os.path.normpath(os.path.join(base_dir, 'settings.json'))

            if os.path.exists(unified_path):
                with open(unified_path, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                # 归一化为 GUI 使用的扁平结构（不改变磁盘文件结构）
                settings = raw.get('settings', {})
                account = settings.get('account', {})
                risk = settings.get('risk', {})
                xq = raw.get('xueqiu_settings', raw.get('xueqiu', {}))
                self.config = {
                    'account': {
                        'account_id': account.get('account_id', ''),
                        'password': account.get('password', '')
                    },
                    'xueqiu': {
                        'cookie': xq.get('cookie', ''),
                        'sync_interval': xq.get('sync_interval', 3)
                    },
                    'risk': {
                        'max_position_ratio': risk.get('max_position_ratio', 0.1),
                        'stop_loss_ratio': risk.get('stop_loss_ratio', 0.05),
                        'max_daily_loss': risk.get('max_daily_loss', 5000)
                    }
                }
                # 记录路径以便保存时写回 unified
                self._config_file_path = unified_path
                self.apply_config()
            elif os.path.exists(legacy_path):
                with open(legacy_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                self._config_file_path = legacy_path
                self.apply_config()
            else:
                # 若均不存在，初始化默认结构并指向 unified 写入路径
                self.config = {
                    'account': {'account_id': '', 'password': ''},
                    'xueqiu': {'cookie': '', 'sync_interval': 3},
                    'risk': {'max_position_ratio': 0.1, 'stop_loss_ratio': 0.05, 'max_daily_loss': 5000}
                }
                self._config_file_path = unified_path
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
        """保存配置（优先写回 unified_config.json 的对应结构）"""
        try:
            # 收集界面值（扁平结构）
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
            
            # 构造 unified 结构
            unified = {
                'settings': {
                    'account': {
                        'account_id': self.config['account']['account_id'],
                        'password': self.config['account']['password']
                    },
                    'risk': {
                        'max_position_ratio': self.config['risk']['max_position_ratio'],
                        'stop_loss_ratio': self.config['risk']['stop_loss_ratio'],
                        'max_daily_loss': self.config['risk']['max_daily_loss']
                    }
                },
                'xueqiu_settings': {
                    'cookie': self.config['xueqiu']['cookie'],
                    'sync_interval': self.config['xueqiu']['sync_interval']
                }
            }
            
            # 目标路径：优先统一配置文件
            target_path = getattr(self, '_config_file_path', None)
            if not target_path:
                base_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
                target_path = os.path.normpath(os.path.join(base_dir, 'unified_config.json'))
            
            # 确保目录存在
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(unified, f, ensure_ascii=False, indent=2)
            
            QMessageBox.information(self, "成功", f"配置保存成功!\n路径: {target_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")
    
    def _ensure_event_loop(self):
        """确保存在后台事件循环线程"""
        if getattr(self, "_loop", None) and self._loop.is_running():
            return
        
        def _run_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()
        
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=_run_loop, args=(self._loop,), daemon=True)
        self._loop_thread.start()
    
    def _run_coro(self, coro):
        """在线程中的事件循环里调度协程"""
        self._ensure_event_loop()
        return asyncio.run_coroutine_threadsafe(coro, self._loop)
    
    def start_strategy(self):
        """启动策略（对齐启动脚本：initialize -> start，均为异步）"""
        try:
            if not XUEQIU_AVAILABLE:
                QMessageBox.warning(self, "警告", "雪球跟单模块不可用，请检查依赖")
                return
            
            # 复用 start_xueqiu_follow_easyxt 的系统类，保证交易链路一致
            # 优先加载 strategies/xueqiu_follow/config/unified_config.json 作为完整配置基线
            base_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
            unified_path = os.path.normpath(os.path.join(base_dir, 'unified_config.json'))
            loaded = {}
            try:
                if os.path.exists(unified_path):
                    with open(unified_path, 'r', encoding='utf-8') as f:
                        loaded = json.load(f) or {}
            except Exception as _e:
                # 若加载失败，退回最小结构
                loaded = {}
            # 构造配置：以文件为准，覆盖账户ID/密码；若缺失则补齐必要结构
            settings = loaded.get('settings') or {}
            settings.setdefault('account', {})
            if self.account_id.text():
                settings['account']['account_id'] = self.account_id.text()
            if self.account_password.text():
                settings['account']['password'] = self.account_password.text()
            settings.setdefault('trading', {})
            settings['trading'].setdefault('trade_mode', 'paper_trading')
            # 补齐脚本期望的 settings.qmt 字段，避免 KeyError: 'qmt'
            settings.setdefault('qmt', {})
            settings['qmt'].setdefault('session_id', 'xueqiu_follow')
            settings['qmt'].setdefault('api_type', 'advanced')
            settings['qmt'].setdefault('auto_retry', True)
            settings['qmt'].setdefault('retry_count', 3)
            settings['qmt'].setdefault('timeout', 30)
            loaded['settings'] = settings
            config_data = loaded
            # 在系统初始化前做与脚本一致的QMT检查（同步执行，快速失败）
            try:
                if not check_qmt_config():
                    raise Exception('QMT 配置检查失败')
                if not test_qmt_connection():
                    raise Exception('QMT 连接测试失败')
            except Exception as _e:
                raise Exception(f'前置检查失败: {_e}')

            # 关键配置快速校验（比对脚本前置自检，给出更明确的GUI错误信息）
            try:
                acc = (config_data.get('settings', {}).get('account', {}) or {})
                qmt_path = acc.get('qmt_path') or acc.get('userdata_path') or ''
                account_id_val = acc.get('account_id') or ''
                if not account_id_val:
                    raise Exception('未配置账户ID，请在配置中设置 settings.account.account_id')
                if qmt_path and not os.path.exists(qmt_path):
                    raise Exception(f'QMT路径不存在: {qmt_path}，请检查 settings.account.qmt_path')
            except Exception as pre_e:
                raise Exception(f'配置校验失败: {pre_e}')

            self.system = XueqiuFollowSystem(config_data)
            # 使用系统内部的策略引擎供 GUI 查询
            fut_sys_init = self._run_coro(self.system.initialize())
            if not fut_sys_init.result(timeout=60):
                raise Exception('系统初始化失败')
            self.strategy_engine = self.system.strategy_engine
            # 启动系统（异步，不阻塞）
            self._run_coro(self.system.start())
            
            self.is_running = True
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)

            # 更新连接状态
            try:
                self.connection_status.setText("已连接")
            except Exception:
                pass
            
            # 启动定时更新
            self.update_timer.start(self.sync_interval.value() * 1000)
            
            self.status_changed.emit("运行中")
            QMessageBox.information(self, "成功", "雪球跟单策略启动成功!")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动策略失败: {str(e)}")
    
    def stop_strategy(self):
        """停止策略（对齐异步 stop）"""
        try:
            # 优先停止系统（内部会停止策略引擎/执行器/采集器）
            if self.system:
                try:
                    self._run_coro(self.system.stop()).result(timeout=30)
                except Exception:
                    pass
            elif self.strategy_engine:
                # 兼容旧逻辑
                try:
                    self._run_coro(self.strategy_engine.stop()).result(timeout=15)
                except Exception:
                    try:
                        self.strategy_engine.stop()
                    except Exception:
                        pass
            
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
            # 刷新策略引擎数据（组合）
            if self.strategy_engine:
                # 优先使用启用的组合；随后基于实际持仓+雪球持仓成分，计算每个组合的实际资产与当日盈亏
                try:
                    enabled = self.strategy_engine.config_manager.get_enabled_portfolios()
                except Exception:
                    enabled = self.strategy_engine.get_portfolios()
                enabled = enabled or []

                # 从策略引擎获取当前账户持仓快照（含 market_value 与 pnl 等字段，若可用）
                try:
                    positions_map = self.strategy_engine.get_positions() or {}
                except Exception:
                    positions_map = {}

                def normalize_variants(sym: str) -> List[str]:
                    variants = set()
                    if not sym:
                        return []
                    s = sym.upper()
                    variants.add(s)
                    # 兼容 "SZ000001" <-> "000001.SZ"
                    if len(s) >= 2 and (s.startswith('SZ') or s.startswith('SH')) and len(s) >= 8:
                        code6 = s[2:8]
                        suffix = 'SZ' if s.startswith('SZ') else 'SH'
                        variants.add(f"{code6}.{suffix}")
                        variants.add(code6)
                    if '.' in s and len(s) >= 9:
                        parts = s.split('.')
                        if len(parts[0]) == 6 and parts[1] in ('SZ','SH'):
                            variants.add(parts[0])
                            variants.add(parts[1]+parts[0])
                    return list(variants)

                def pick_pos(code: str) -> Optional[Dict[str, Any]]:
                    for k in normalize_variants(code):
                        if k in positions_map:
                            return positions_map.get(k)
                    return None

                enriched = []
                for p in enabled:
                    name = p.get('name') or p.get('code') or '组合'
                    code = p.get('code') or p.get('symbol')
                    follow_ratio = float(p.get('follow_ratio', 0) or 0.0)

                    total_value = 0.0
                    # 组合收益：用账户持仓的“总盈亏”聚合（与 QMT 数据一致）
                    combo_pnl = 0.0
                    return_rate = None

                    # 若 collector 可用，则用雪球持仓成分来归属实际资产与当日盈亏
                    holdings = None
                    try:
                        if getattr(self.strategy_engine, 'collector', None) and code:
                            fut = self._run_coro(self.strategy_engine.collector.get_portfolio_holdings(code))
                            holdings = fut.result(timeout=5)
                    except Exception:
                        holdings = None

                    if holdings:
                        for h in holdings:
                            sym = h.get('symbol') or h.get('stock_symbol')
                            pos = pick_pos(sym)
                            if not pos:
                                continue
                            mv = float(pos.get('market_value', pos.get('value', 0)) or 0)
                            # 组合收益：优先聚合券商持仓的总盈亏（profit_loss/pnl），若无则 0
                            pnl_total = pos.get('pnl')
                            if pnl_total is None:
                                pnl_total = pos.get('profit_loss')
                            pnl = float(pnl_total or 0.0)
                            total_value += mv
                            combo_pnl += pnl
                        if total_value > 0:
                            return_rate = (combo_pnl / total_value) if total_value else None
                    else:
                        # 回退：按账户总资产×跟随比例估算（维持旧逻辑避免空白）
                        try:
                            account_value = float(self.strategy_engine._get_account_value() or 0)
                        except Exception:
                            account_value = 0.0
                        total_value = account_value * follow_ratio if account_value else 0.0
                        # 无法精确拆分组合收益时，置空等待后续回填
                        combo_pnl = None
                        return_rate = None

                    enriched.append({
                        'name': name,
                        'code': code,
                        'ratio': follow_ratio,
                        'total_value': total_value if total_value else None,
                        'combo_pnl': combo_pnl,
                        'return_rate': return_rate,
                        'status': p.get('status', '就绪')
                    })

                self.portfolio_updated.emit(enriched)

            # 优先用 QMT 详细持仓对齐 GUI；若失败再回退策略引擎的持仓
            qmt_positions_sent = False
            try:
                if getattr(self, 'system', None) and getattr(self.system, 'executor', None):
                    executor = self.system.executor
                    trader_api = getattr(executor, 'trader_api', None)
                    # 获取账号
                    account_id = self.account_id.text() or ((self.system.config_data.get('settings', {}).get('account', {}) or {}).get('account_id'))
                    if trader_api and hasattr(trader_api, 'get_positions_detailed') and account_id:
                        positions_df = trader_api.get_positions_detailed(account_id)
                        if positions_df is not None and not getattr(positions_df, 'empty', True):
                            # 映射为 GUI 统一结构
                            positions_map = {}
                            for _, row in positions_df.iterrows():
                                try:
                                    code = row.get('code') or row.get('stock_code') or ''
                                    if not code:
                                        continue
                                    volume = float(row.get('volume', 0) or 0)
                                    market_value = float(row.get('market_value', 0) or 0)
                                    open_price = float(row.get('open_price', 0) or 0)
                                    can_use = float(row.get('can_use_volume', 0) or 0)
                                    current_price = (market_value / volume) if volume else 0.0
                                    # 日内盈亏（今日收益）优先：daily_pnl / today_profit / pnl_today
                                    pnl_today = row.get('daily_pnl')
                                    if pnl_today is None:
                                        pnl_today = row.get('today_profit')
                                    if pnl_today is None:
                                        pnl_today = row.get('pnl_today')
                                    pnl = float(pnl_today if pnl_today is not None else (row.get('profit_loss', 0))) or 0.0
                                    pnl_ratio = float(row.get('profit_loss_ratio', 0) or 0)
                                    # 兜底计算：若券商未返回盈亏或盈亏率，则依据昨收/成本价与现价计算
                                    if (pnl == 0 or pnl_ratio == 0):
                                        try:
                                            # 优先昨收（更贴近“今日收益”定义）
                                            preclose = row.get('preclose') or row.get('prev_close') or row.get('yesterday_close')
                                            preclose = float(preclose or 0)
                                            if preclose > 0 and volume > 0:
                                                calc_pnl_today = (current_price - preclose) * volume
                                                if pnl == 0:
                                                    pnl = calc_pnl_today
                                                if pnl_ratio == 0 and preclose:
                                                    pnl_ratio = (current_price / preclose - 1.0)
                                            elif open_price and volume:
                                                calc_pnl = (current_price - open_price) * volume
                                                calc_ratio = (current_price / open_price - 1.0) if open_price else 0.0
                                                if pnl == 0:
                                                    pnl = calc_pnl
                                                if pnl_ratio == 0:
                                                    pnl_ratio = calc_ratio
                                        except Exception:
                                            pass
                                    # 名称优先取接口字段，否则通过 xtquant 获取
                                    name_val = row.get('stock_name') or row.get('name') or ''
                                    if not name_val:
                                        try:
                                            norm = code
                                            if not norm or ('.' not in norm):
                                                from easy_xt.utils import StockCodeUtils as _Scu
                                                norm = _Scu.normalize_code(code)
                                            cached = self._code_name_cache.get(norm)
                                            if cached:
                                                name_val = cached
                                            else:
                                                try:
                                                    from xtquant import xtdata as _xt
                                                    info = _xt.get_instrument_detail(norm)
                                                    if info and isinstance(info, dict):
                                                        name_val = info.get('InstrumentName') or info.get('cn_name') or ''
                                                        if name_val:
                                                            self._code_name_cache[norm] = name_val
                                                except Exception:
                                                    pass
                                        except Exception:
                                            pass
                                    positions_map[code] = {
                                        'name': name_val,
                                        'volume': int(volume),
                                        'available': int(can_use),
                                        'cost_price': float(open_price),
                                        'current_price': float(current_price),
                                        'pnl': float(pnl),
                                        'pnl_ratio': float(pnl_ratio)
                                    }
                                except Exception:
                                    continue
                            if positions_map:
                                self.position_updated.emit(positions_map)
                                qmt_positions_sent = True
            except Exception:
                qmt_positions_sent = False

            if not qmt_positions_sent and self.strategy_engine:
                positions = self.strategy_engine.get_positions()
                self.position_updated.emit(positions)

            # 刷新交易记录与连接状态（复用系统执行器）
            try:
                if getattr(self, 'system', None) and getattr(self.system, 'executor', None):
                    executor = self.system.executor
                    trader_api = getattr(executor, 'trader_api', None)
                    account_id = None
                    # 取账号ID：GUI输入优先，其次配置
                    if self.account_id.text():
                        account_id = self.account_id.text()
                    else:
                        try:
                            account_id = (self.system.config_data.get('settings', {}).get('account', {}) or {}).get('account_id')
                        except Exception:
                            account_id = None

                    # 连接状态：以 trader_api 内部状态或一次轻量查询推断
                    connected = False
                    try:
                        if trader_api and hasattr(trader_api, 'accounts'):
                            connected = bool(account_id and trader_api.accounts and account_id in trader_api.accounts)
                        if not connected and trader_api and hasattr(trader_api, 'get_today_orders') and account_id:
                            # 轻量探测：调用当日委托（失败不抛到外层）
                            _ = trader_api.get_today_orders(account_id)
                            connected = True
                    except Exception:
                        connected = False

                    self.connection_status.setText("已连接" if connected else "未连接")

                    # 优先显示“当日成交”，与QMT成交表一致；若无成交再回退展示“当日委托”
                    try:
                        rendered = False
                        if trader_api and hasattr(trader_api, 'get_today_trades') and account_id:
                            trades_df = trader_api.get_today_trades(account_id)
                            if trades_df is not None and not getattr(trades_df, 'empty', True):
                                # 为 trades_df 缺失的股票名称补齐（使用与持仓相同的缓存/xtdata）
                                try:
                                    from xtquant import xtdata as _xt
                                    def _fill_name(code):
                                        try:
                                            norm = code
                                            if not norm or ('.' not in norm):
                                                from easy_xt.utils import StockCodeUtils as _Scu
                                                norm = _Scu.normalize_code(code)
                                            if norm in getattr(self, '_code_name_cache', {}):
                                                return self._code_name_cache[norm]
                                            info = _xt.get_instrument_detail(norm)
                                            name = (info.get('InstrumentName') or info.get('cn_name')) if isinstance(info, dict) else ''
                                            if name:
                                                self._code_name_cache[norm] = name
                                            return name
                                        except Exception:
                                            return ''

                                    # 当列缺失、全为NaN、或全为空字符串时统一补齐；否则只补空白项
                                    code_col = 'stock_code' if 'stock_code' in trades_df.columns else ('code' if 'code' in trades_df.columns else ('symbol' if 'symbol' in trades_df.columns else None))
                                    if code_col:
                                        need_fill_all = ('stock_name' not in trades_df.columns)
                                        if not need_fill_all:
                                            name_series = trades_df['stock_name']
                                            try:
                                                name_series = name_series.astype(str)
                                            except Exception:
                                                pass
                                            is_blank = name_series.isna() | (name_series.str.strip() == '')
                                            need_fill_all = bool(is_blank.all())
                                        
                                        if need_fill_all:
                                            trades_df['stock_name'] = trades_df[code_col].apply(_fill_name)
                                        else:
                                            blank_mask = trades_df['stock_name'].isna() | (trades_df['stock_name'].astype(str).str.strip() == '')
                                            trades_df.loc[blank_mask, 'stock_name'] = trades_df.loc[blank_mask, code_col].apply(_fill_name)
                                except Exception:
                                    pass

                                self._render_today_trades_table(trades_df)
                                rendered = True
                                # 统计
                                try:
                                    total_trades = len(trades_df)
                                    total_amount = float(trades_df.get('traded_amount', []).sum()) if hasattr(trades_df, 'get') else 0.0
                                    self.total_trades_label.setText(f"总交易次数: {total_trades}")
                                    self.total_profit_label.setText(f"总盈亏: ¥{total_amount:,.2f}")
                                    self.today_trades_label.setText(f"今日交易: {total_trades}")
                                except Exception:
                                    pass
                        if not rendered and trader_api and hasattr(trader_api, 'get_today_orders') and account_id:
                            orders_df = trader_api.get_today_orders(account_id)
                            self._render_today_orders_table(orders_df)
                            try:
                                total_orders = 0 if orders_df is None or getattr(orders_df, 'empty', True) else len(orders_df)
                                self.total_trades_label.setText(f"总交易次数: {total_orders}")
                                self.today_trades_label.setText(f"今日交易: {total_orders}")
                            except Exception:
                                pass
                    except Exception:
                        # 不影响其他展示
                        pass
            except Exception:
                self.connection_status.setText("未连接")

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
        """更新组合显示（对 None/非法数值做健壮格式化）"""
        # portfolios 是列表，每个元素为一个组合配置字典
        self.portfolio_table.setRowCount(len(portfolios))

        def fmt_money(value):
            if value is None:
                return "--"
            try:
                return f"¥{float(value):,.2f}"
            except Exception:
                return "--"

        def fmt_pct(value):
            if value is None:
                return "--"
            try:
                return f"{float(value):.2%}"
            except Exception:
                return "--"

        for i, p in enumerate(portfolios):
            name = p.get('name') or p.get('code') or f"组合{i+1}"
            ratio = p.get('ratio')
            total_value = p.get('total_value')
            combo_pnl = p.get('combo_pnl')
            return_rate = p.get('return_rate')
            status = p.get('status', '未知')

            self.portfolio_table.setItem(i, 0, QTableWidgetItem(str(name)))
            self.portfolio_table.setItem(i, 1, QTableWidgetItem(fmt_pct(ratio)))
            self.portfolio_table.setItem(i, 2, QTableWidgetItem(fmt_money(total_value)))
            self.portfolio_table.setItem(i, 3, QTableWidgetItem(fmt_money(combo_pnl)))
            self.portfolio_table.setItem(i, 4, QTableWidgetItem(fmt_pct(return_rate)))
            self.portfolio_table.setItem(i, 5, QTableWidgetItem(str(status)))
    
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