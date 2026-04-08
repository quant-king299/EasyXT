#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
条件单GUI组件
提供条件单的可视化配置、管理和监控界面
"""

import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox,
    QProgressBar, QSplitter, QFrame, QMessageBox,
    QFileDialog, QFormLayout, QScrollArea, QSizePolicy,
    QDateTimeEdit, QDateEdit, QMenu, QAction
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize, QDateTime
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QTextCursor

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    import easy_xt
    EASYXT_AVAILABLE = True
except ImportError:
    EASYXT_AVAILABLE = False


class ConditionalOrderWidget(QWidget):
    """条件单GUI组件"""

    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.orders = []  # 存储所有条件单
        self.order_counter = 0  # 条件单计数器
        self.monitored_orders = set()  # 已启动监控的条件单ID集合
        self.trade_api = None  # AdvancedTradeAPI实例
        self._trade_initialized = False  # 交易API是否已初始化
        self.init_ui()
        self.setup_timer()
        self.init_trade_connection()  # 自动初始化交易连接

    def init_ui(self):
        """初始化用户界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)

        # 上半部分：条件单配置
        config_widget = self.create_config_panel()
        splitter.addWidget(config_widget)

        # 下半部分：条件单管理
        manage_widget = self.create_manage_panel()
        splitter.addWidget(manage_widget)

        # 设置分割比例
        splitter.setSizes([350, 400])

    def create_config_panel(self) -> QWidget:
        """创建配置面板"""
        # 使用滚动区域包裹整个配置面板
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)  # 减小垂直间距
        layout.setContentsMargins(10, 10, 10, 10)

        # 条件单类型选择
        type_group = QGroupBox("条件单类型")
        type_layout = QFormLayout(type_group)
        type_layout.setSpacing(12)  # 行间距12px
        type_layout.setContentsMargins(15, 20, 15, 15)  # 边距
        # 设置标签和输入框之间的水平间距
        type_layout.setHorizontalSpacing(18)  # 标签与输入框间距18px
        type_layout.setVerticalSpacing(15)  # 行间距15px

        self.order_type_combo = QComboBox()
        self.order_type_combo.setMinimumWidth(200)  # 设置最小宽度200px
        self.order_type_combo.addItems([
            "价格条件单",
            "时间条件单",
            "涨跌幅条件单",
            "止盈止损单",
            "高级止盈止损策略"  # 新增高级止盈止损策略
        ])
        self.order_type_combo.currentIndexChanged.connect(self.on_order_type_changed)
        type_layout.addRow("条件单类型:", self.order_type_combo)

        layout.addWidget(type_group)

        # 条件配置区域（不滚动，直接显示）
        condition_group = QGroupBox("条件配置")
        self.condition_layout = QFormLayout(condition_group)
        self.condition_layout.setSpacing(12)  # 行间距12px
        self.condition_layout.setContentsMargins(15, 15, 15, 15)  # 边距
        # 设置标签和输入框之间的水平间距
        self.condition_layout.setHorizontalSpacing(18)  # 标签与输入框间距18px
        self.condition_layout.setVerticalSpacing(15)  # 行间距15px
        self.create_condition_ui(self.condition_layout)

        layout.addWidget(condition_group)

        # 动作配置
        action_group = QGroupBox("触发动作")
        action_layout = QFormLayout(action_group)
        action_layout.setSpacing(12)  # 行间距12px
        action_layout.setContentsMargins(15, 20, 15, 15)  # 边距
        # 设置标签和输入框之间的水平间距
        action_layout.setHorizontalSpacing(18)  # 标签与输入框间距18px
        action_layout.setVerticalSpacing(15)  # 行间距15px

        self.action_type_combo = QComboBox()
        self.action_type_combo.setMinimumWidth(180)  # 设置最小宽度180px
        self.action_type_combo.addItems(["买入", "卖出"])
        action_layout.addRow("操作类型:", self.action_type_combo)

        self.stock_code_edit = QLineEdit("511090.SH")
        self.stock_code_edit.setMinimumWidth(200)  # 设置最小宽度200px
        action_layout.addRow("股票代码:", self.stock_code_edit)

        self.order_quantity_spin = QSpinBox()
        self.order_quantity_spin.setMinimumWidth(180)  # 设置最小宽度180px
        self.order_quantity_spin.setRange(100, 100000)
        self.order_quantity_spin.setValue(100)
        self.order_quantity_spin.setSingleStep(100)
        action_layout.addRow("数量(股):", self.order_quantity_spin)

        self.order_price_spin = QDoubleSpinBox()
        self.order_price_spin.setMinimumWidth(180)  # 设置最小宽度180px
        self.order_price_spin.setRange(0, 9999.99)  # 允许输入0表示市价
        self.order_price_spin.setValue(0)  # 默认市价
        self.order_price_spin.setDecimals(2)
        self.order_price_spin.setSpecialValueText("市价单")  # 0显示为"市价单"
        action_layout.addRow("价格:", self.order_price_spin)

        # 成本价（用于高级止盈止损策略计算盈亏）
        self.cost_price_input_spin = QDoubleSpinBox()
        self.cost_price_input_spin.setMinimumWidth(180)  # 设置最小宽度180px
        self.cost_price_input_spin.setRange(0.01, 9999.99)
        self.cost_price_input_spin.setValue(10.0)
        self.cost_price_input_spin.setDecimals(2)
        action_layout.addRow("成本价:", self.cost_price_input_spin)

        layout.addWidget(action_group)

        # 有效期设置
        expiry_group = QGroupBox("有效期设置")
        expiry_layout = QFormLayout(expiry_group)
        expiry_layout.setSpacing(12)  # 行间距12px
        expiry_layout.setContentsMargins(15, 20, 15, 15)  # 边距
        # 设置标签和输入框之间的水平间距
        expiry_layout.setHorizontalSpacing(18)  # 标签与输入框间距18px
        expiry_layout.setVerticalSpacing(15)  # 行间距15px

        self.valid_time_edit = QDateTimeEdit()
        self.valid_time_edit.setMinimumWidth(250)  # 设置最小宽度250px
        self.valid_time_edit.setDateTime(
            QDateTime.currentDateTime().addDays(1)
        )
        self.valid_time_edit.setDisplayFormat("yyyy-MM-dd hh:mm:ss")
        self.valid_time_edit.setCalendarPopup(True)
        expiry_layout.addRow("有效期至:", self.valid_time_edit)

        layout.addWidget(expiry_group)

        # 按钮区域
        button_layout = QHBoxLayout()

        self.create_order_btn = QPushButton("➕ 创建条件单")
        self.create_order_btn.setFixedSize(120, 40)
        self.create_order_btn.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0077ee;
            }
        """)
        self.create_order_btn.clicked.connect(self.create_order)

        self.clear_form_btn = QPushButton("🔄 清空表单")
        self.clear_form_btn.setFixedSize(120, 40)
        self.clear_form_btn.clicked.connect(self.clear_form)

        button_layout.addWidget(self.create_order_btn)
        button_layout.addWidget(self.clear_form_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # 添加弹性空间
        layout.addStretch()

        scroll.setWidget(panel)

        # 返回滚动区域而不是面板
        return scroll

    def create_manage_panel(self) -> QWidget:
        """创建管理面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)  # 增加垂直间距到15

        # 条件单列表
        list_group = QGroupBox("活跃条件单")
        list_layout = QVBoxLayout(list_group)
        list_layout.setSpacing(10)  # 增加列表内部间距到10

        self.order_table = QTableWidget(0, 7)
        self.order_table.setHorizontalHeaderLabels([
            "ID", "类型", "股票", "条件", "动作", "状态", "操作"
        ])
        self.order_table.horizontalHeader().setStretchLastSection(True)
        self.order_table.setAlternatingRowColors(True)
        self.order_table.setMinimumHeight(200)
        self.order_table.cellClicked.connect(self.on_order_clicked)
        list_layout.addWidget(self.order_table)

        # 列表操作按钮
        list_button_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self.refresh_order_list)
        list_button_layout.addWidget(self.refresh_btn)

        self.delete_order_btn = QPushButton("🗑 删除选中")
        self.delete_order_btn.clicked.connect(self.delete_selected_order)
        list_button_layout.addWidget(self.delete_order_btn)

        self.disable_order_btn = QPushButton("⏸ 禁用选中")
        self.disable_order_btn.clicked.connect(self.disable_selected_order)
        list_button_layout.addWidget(self.disable_order_btn)

        self.enable_order_btn = QPushButton("▶ 启用选中")
        self.enable_order_btn.clicked.connect(self.enable_selected_order)
        list_button_layout.addWidget(self.enable_order_btn)

        list_button_layout.addStretch()

        list_layout.addLayout(list_button_layout)
        layout.addWidget(list_group)

        # 触发历史记录
        history_group = QGroupBox("触发历史")
        history_layout = QVBoxLayout(history_group)
        history_layout.setSpacing(10)  # 增加内部间距到10

        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels([
            "时间", "条件单ID", "条件", "触发价格", "执行结果"
        ])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setMinimumHeight(120)
        history_layout.addWidget(self.history_table)

        layout.addWidget(history_group)

        # 日志输出
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)
        log_layout.setSpacing(10)  # 增加内部间距到10
        log_layout.setContentsMargins(8, 8, 8, 8)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(150)  # 从80增加到150
        self.log_text.setMaximumHeight(250)  # 添加最大高度250
        self.log_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #444;
            }
        """)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group)

        return panel

    def create_condition_ui(self, parent_widget):
        """创建条件配置UI（根据选择的类型）"""
        order_type = self.order_type_combo.currentText()

        if "价格条件单" in order_type:
            self.create_price_condition_ui(parent_widget)
        elif "时间条件单" in order_type:
            self.create_time_condition_ui(parent_widget)
        elif "涨跌幅条件单" in order_type:
            self.create_change_condition_ui(parent_widget)
        elif "止盈止损单" in order_type:
            self.create_stop_condition_ui(parent_widget)
        elif "高级止盈止损策略" in order_type:
            self.create_advanced_stop_loss_ui(parent_widget)

    def create_price_condition_ui(self, layout):
        """创建价格条件UI"""
        self.condition_direction_combo = QComboBox()
        self.condition_direction_combo.setMinimumWidth(200)  # 设置最小宽度200px
        self.condition_direction_combo.addItems([
            "价格大于等于",
            "价格小于等于",
            "价格突破"
        ])
        layout.addRow("触发条件:", self.condition_direction_combo)

        self.target_price_spin = QDoubleSpinBox()
        self.target_price_spin.setMinimumWidth(180)  # 设置最小宽度180px
        self.target_price_spin.setRange(0.01, 9999.99)
        self.target_price_spin.setValue(100.0)
        self.target_price_spin.setDecimals(2)
        layout.addRow("目标价格:", self.target_price_spin)

    def create_time_condition_ui(self, layout):
        """创建时间条件UI"""
        self.trigger_time_edit = QDateTimeEdit()
        self.trigger_time_edit.setMinimumWidth(250)  # 设置最小宽度250px
        self.trigger_time_edit.setDateTime(QDateTime.currentDateTime())
        self.trigger_time_edit.setDisplayFormat("yyyy-MM-dd hh:mm:ss")
        layout.addRow("触发时间:", self.trigger_time_edit)

        self.trigger_type_combo = QComboBox()
        self.trigger_type_combo.setMinimumWidth(200)  # 设置最小宽度200px
        self.trigger_type_combo.addItems([
            "立即执行",
            "在集合竞价执行"
        ])
        layout.addRow("执行方式:", self.trigger_type_combo)

    def create_change_condition_ui(self, layout):
        """创建涨跌幅条件UI"""
        self.change_direction_combo = QComboBox()
        self.change_direction_combo.setMinimumWidth(200)  # 设置最小宽度200px
        self.change_direction_combo.addItems([
            "涨幅超过",
            "跌幅超过",
            "涨幅回落",
            "跌幅反弹"
        ])
        layout.addRow("触发条件:", self.change_direction_combo)

        self.change_threshold_spin = QDoubleSpinBox()
        self.change_threshold_spin.setMinimumWidth(180)  # 设置最小宽度180px
        self.change_threshold_spin.setRange(-20.0, 20.0)
        self.change_threshold_spin.setValue(2.0)
        self.change_threshold_spin.setDecimals(2)
        self.change_threshold_spin.setSuffix("%")
        layout.addRow("涨跌幅阈值:", self.change_threshold_spin)

        self.reference_price_combo = QComboBox()
        self.reference_price_combo.setMinimumWidth(200)  # 设置最小宽度200px
        self.reference_price_combo.addItems([
            "前收盘价",
            "今日开盘价",
            "指定价格"
        ])
        layout.addRow("基准价格:", self.reference_price_combo)

        self.ref_price_spin = QDoubleSpinBox()
        self.ref_price_spin.setMinimumWidth(180)  # 设置最小宽度180px
        self.ref_price_spin.setRange(0.01, 9999.99)
        self.ref_price_spin.setValue(100.0)
        self.ref_price_spin.setDecimals(2)
        layout.addRow("指定基准:", self.ref_price_spin)

    def create_stop_condition_ui(self, layout):
        """创建止盈止损UI"""
        self.stop_type_combo = QComboBox()
        self.stop_type_combo.setMinimumWidth(200)  # 设置最小宽度200px
        self.stop_type_combo.addItems([
            "止盈单",
            "止损单",
            "止盈止损"
        ])
        layout.addRow("类型:", self.stop_type_combo)

        self.stop_loss_price_spin = QDoubleSpinBox()
        self.stop_loss_price_spin.setMinimumWidth(180)  # 设置最小宽度180px
        self.stop_loss_price_spin.setRange(0.01, 9999.99)
        self.stop_loss_price_spin.setValue(95.0)
        self.stop_loss_price_spin.setDecimals(2)
        layout.addRow("止损价:", self.stop_loss_price_spin)

        self.stop_profit_price_spin = QDoubleSpinBox()
        self.stop_profit_price_spin.setMinimumWidth(180)  # 设置最小宽度180px
        self.stop_profit_price_spin.setRange(0.01, 9999.99)
        self.stop_profit_price_spin.setValue(110.0)
        self.stop_profit_price_spin.setDecimals(2)
        layout.addRow("止盈价:", self.stop_profit_price_spin)

    def create_advanced_stop_loss_ui(self, layout):
        """创建高级止盈止损策略UI"""
        # 快捷预设按钮
        preset_layout = QHBoxLayout()

        preset_label = QLabel("快捷预设:")
        preset_layout.addWidget(preset_label)

        self.preset_conservative_btn = QPushButton("新手保守")
        self.preset_conservative_btn.clicked.connect(lambda: self.apply_preset('新手保守'))
        preset_layout.addWidget(self.preset_conservative_btn)

        self.preset_steady_btn = QPushButton("中长线稳健")
        self.preset_steady_btn.clicked.connect(lambda: self.apply_preset('中长线稳健'))
        preset_layout.addWidget(self.preset_steady_btn)

        self.preset_aggressive_btn = QPushButton("短线激进")
        self.preset_aggressive_btn.clicked.connect(lambda: self.apply_preset('短线激进'))
        preset_layout.addWidget(self.preset_aggressive_btn)

        preset_layout.addStretch()
        layout.addRow(preset_layout)

        # 说明文本
        description_label = QLabel()
        description_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 11px;
                padding: 5px;
                background-color: #e3f2fd;
                border-radius: 4px;
            }
        """)
        description_label.setText(
            "<b>💡 提示：</b>点击上方快捷预设按钮可快速填充参数，也可手动调整下方各策略参数"
        )
        description_label.setWordWrap(True)
        layout.addRow(description_label)

        # ========== 策略1：浮盈回落止损 ==========
        s1_group = QGroupBox("🥇 策略1(浮盈回落止损)")
        s1_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4CAF50;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        s1_layout = QFormLayout(s1_group)

        self.enable_strategy1_cb = QCheckBox("启用策略1")
        self.enable_strategy1_cb.setChecked(True)
        s1_layout.addRow("", self.enable_strategy1_cb)

        self.s1_profit_min_spin = QDoubleSpinBox()
        self.s1_profit_min_spin.setRange(0, 100)
        self.s1_profit_min_spin.setValue(20)
        self.s1_profit_min_spin.setSuffix("%")
        s1_layout.addRow("最小浮盈:", self.s1_profit_min_spin)

        self.s1_profit_max_spin = QDoubleSpinBox()
        self.s1_profit_max_spin.setRange(0, 200)
        self.s1_profit_max_spin.setValue(50)
        self.s1_profit_max_spin.setSuffix("%")
        s1_layout.addRow("最大浮盈:", self.s1_profit_max_spin)

        self.s1_pullback_spin = QDoubleSpinBox()
        self.s1_pullback_spin.setRange(0, 50)
        self.s1_pullback_spin.setValue(10)
        self.s1_pullback_spin.setSuffix("%")
        s1_layout.addRow("回落止损:", self.s1_pullback_spin)

        layout.addRow(s1_group)

        # ========== 策略2：最高价回落止损 ==========
        s2_group = QGroupBox("🥈 策略2(最高价回落止损)")
        s2_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2196F3;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        s2_layout = QFormLayout(s2_group)

        self.enable_strategy2_cb = QCheckBox("启用策略2")
        self.enable_strategy2_cb.setChecked(True)
        s2_layout.addRow("", self.enable_strategy2_cb)

        self.s2_rise_threshold_spin = QDoubleSpinBox()
        self.s2_rise_threshold_spin.setRange(0, 100)
        self.s2_rise_threshold_spin.setValue(10)
        self.s2_rise_threshold_spin.setSuffix("%")
        s2_layout.addRow("涨幅阈值:", self.s2_rise_threshold_spin)

        self.s2_pullback_spin = QDoubleSpinBox()
        self.s2_pullback_spin.setRange(0, 50)
        self.s2_pullback_spin.setValue(5)
        self.s2_pullback_spin.setSuffix("%")
        s2_layout.addRow("回落止损:", self.s2_pullback_spin)

        layout.addRow(s2_group)

        # ========== 策略3：高开回落止损 ==========
        s3_group = QGroupBox("🥉 策略3(高开回落止损)")
        s3_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #FF9800;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        s3_layout = QFormLayout(s3_group)

        self.enable_strategy3_cb = QCheckBox("启用策略3")
        self.enable_strategy3_cb.setChecked(True)
        s3_layout.addRow("", self.enable_strategy3_cb)

        s3_params_layout = QHBoxLayout()

        s3_params_layout.addWidget(QLabel("高开"))
        self.s3_gap_open_spin = QDoubleSpinBox()
        self.s3_gap_open_spin.setRange(0, 20)
        self.s3_gap_open_spin.setValue(3)
        self.s3_gap_open_spin.setSuffix("%")
        s3_params_layout.addWidget(self.s3_gap_open_spin)

        s3_params_layout.addWidget(QLabel("高于开盘"))
        self.s3_high_above_open_spin = QDoubleSpinBox()
        self.s3_high_above_open_spin.setRange(0, 20)
        self.s3_high_above_open_spin.setValue(2)
        self.s3_high_above_open_spin.setSuffix("%")
        s3_params_layout.addWidget(self.s3_high_above_open_spin)

        s3_params_layout.addWidget(QLabel("回落"))
        self.s3_pullback_spin = QDoubleSpinBox()
        self.s3_pullback_spin.setRange(0, 20)
        self.s3_pullback_spin.setValue(2)
        self.s3_pullback_spin.setSuffix("%")
        s3_params_layout.addWidget(self.s3_pullback_spin)

        s3_params_layout.addWidget(QLabel("止损"))
        s3_params_layout.addStretch()

        s3_layout.addRow("条件:", s3_params_layout)
        layout.addRow(s3_group)

        # ========== 策略4：总体亏损止损 ==========
        s4_group = QGroupBox("🛡 策略4(总体亏损止损)")
        s4_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #f44336;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        s4_layout = QFormLayout(s4_group)

        self.enable_strategy4_cb = QCheckBox("启用策略4")
        self.enable_strategy4_cb.setChecked(True)
        s4_layout.addRow("", self.enable_strategy4_cb)

        self.s4_loss_threshold_spin = QDoubleSpinBox()
        self.s4_loss_threshold_spin.setRange(-50, 0)
        self.s4_loss_threshold_spin.setValue(-5)
        self.s4_loss_threshold_spin.setSuffix("%")
        s4_layout.addRow("亏损止损线:", self.s4_loss_threshold_spin)

        # 警告提示
        s4_warning = QLabel("⚠️ 这是最后的防线，建议始终启用以避免深度套牢")
        s4_warning.setStyleSheet("color: #f44336; font-size: 11px;")
        s4_warning.setWordWrap(True)
        s4_layout.addRow("", s4_warning)

        layout.addRow(s4_group)

    def apply_preset(self, preset_name: str):
        """应用预设参数"""
        presets = {
            '中长线稳健': {
                's1_profit_min': 20, 's1_profit_max': 50, 's1_pullback': 10,
                's2_rise_threshold': 10, 's2_pullback': 5,
                's3_gap_open': 3, 's3_high_above_open': 2, 's3_pullback': 2,
                's4_loss_threshold': -5,
            },
            '短线激进': {
                's1_profit_min': 10, 's1_profit_max': 20, 's1_pullback': 5,
                's2_rise_threshold': 10, 's2_pullback': 5,
                's3_gap_open': 5, 's3_high_above_open': 3, 's3_pullback': 3,
                's4_loss_threshold': -8,
            },
            '新手保守': {
                's1_profit_min': 15, 's1_profit_max': 30, 's1_pullback': 8,
                's2_rise_threshold': 5, 's2_pullback': 2,
                's3_gap_open': 2, 's3_high_above_open': 1.5, 's3_pullback': 1.5,
                's4_loss_threshold': -5,
            }
        }

        params = presets.get(preset_name)
        if params:
            self.s1_profit_min_spin.setValue(params['s1_profit_min'])
            self.s1_profit_max_spin.setValue(params['s1_profit_max'])
            self.s1_pullback_spin.setValue(params['s1_pullback'])
            self.s2_rise_threshold_spin.setValue(params['s2_rise_threshold'])
            self.s2_pullback_spin.setValue(params['s2_pullback'])
            self.s3_gap_open_spin.setValue(params['s3_gap_open'])
            self.s3_high_above_open_spin.setValue(params['s3_high_above_open'])
            self.s3_pullback_spin.setValue(params['s3_pullback'])
            self.s4_loss_threshold_spin.setValue(params['s4_loss_threshold'])

    def on_order_type_changed(self, index):
        """条件单类型改变事件"""
        # 清空旧的条件UI
        while self.condition_layout.count():
            item = self.condition_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # 重新创建条件UI
        self.create_condition_ui(self.condition_layout)

    def get_condition_description(self) -> str:
        """获取条件描述"""
        order_type = self.order_type_combo.currentText()
        desc = f"{order_type} - "

        if "价格条件" in order_type:
            direction = self.condition_direction_combo.currentText()
            price = self.target_price_spin.value()
            desc += f"{direction} {price:.2f}元"

        elif "时间条件" in order_type:
            time_str = self.trigger_time_edit.dateTime().toString("yyyy-MM-dd hh:mm:ss")
            desc += f"在 {time_str} 触发"

        elif "涨跌幅" in order_type:
            direction = self.change_direction_combo.currentText()
            threshold = self.change_threshold_spin.value()
            desc += f"{direction} {threshold:.2f}%"

        elif "止盈止损单" in order_type:
            stop_type = self.stop_type_combo.currentText()
            desc += f"{stop_type}"
            if "止盈" in stop_type or "止盈止损" in stop_type:
                profit = self.stop_profit_price_spin.value()
                desc += f" (止盈价: {profit:.2f})"
            if "止损" in stop_type or "止盈止损" in stop_type:
                loss = self.stop_loss_price_spin.value()
                desc += f" (止损价: {loss:.2f})"

        elif "高级止盈止损策略" in order_type:
            enabled = []
            if self.enable_strategy1_cb.isChecked():
                enabled.append("策略1")
            if self.enable_strategy2_cb.isChecked():
                enabled.append("策略2")
            if self.enable_strategy3_cb.isChecked():
                enabled.append("策略3")
            if self.enable_strategy4_cb.isChecked():
                enabled.append("策略4")

            desc += f"启用: {','.join(enabled)}"
            if self.enable_strategy1_cb.isChecked():
                desc += f", 策略1:浮盈{self.s1_profit_min_spin.value():.0f}%-{self.s1_profit_max_spin.value():.0f}%回落{self.s1_pullback_spin.value():.0f}%"
            if self.enable_strategy2_cb.isChecked():
                desc += f", 策略2:涨幅超{self.s2_rise_threshold_spin.value():.0f}%回落{self.s2_pullback_spin.value():.0f}%"
            if self.enable_strategy3_cb.isChecked():
                desc += f", 策略3:高开{self.s3_gap_open_spin.value():.0f}%回落{self.s3_pullback_spin.value():.0f}%"
            if self.enable_strategy4_cb.isChecked():
                desc += f", 策略4:浮亏{abs(self.s4_loss_threshold_spin.value()):.0f}%止损"

        return desc

    def create_order(self):
        """创建条件单"""
        try:
            # 获取基本信息
            order_type = self.order_type_combo.currentText()
            stock_code = self.stock_code_edit.text()
            action = self.action_type_combo.currentText()
            quantity = self.order_quantity_spin.value()
            price = self.order_price_spin.value()

            if not stock_code:
                QMessageBox.warning(self, "输入错误", "请输入股票代码")
                return

            # 获取有效期
            expiry_str = self.valid_time_edit.dateTime().toString("yyyy-MM-dd hh:mm:ss")
            try:
                expiry_time = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
                if expiry_time <= datetime.now():
                    QMessageBox.warning(
                        self,
                        "有效期错误",
                        f"有效期必须晚于当前时间！\n\n当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"设置的有效期: {expiry_str}\n\n请重新设置有效期。"
                    )
                    return
            except Exception as e:
                QMessageBox.warning(self, "有效期错误", f"有效期格式错误: {str(e)}")
                return

            # 创建条件单对象
            self.order_counter += 1
            order = {
                'id': f"CO{self.order_counter:04d}",
                'type': order_type,
                'stock_code': stock_code,
                'action': action,
                'quantity': quantity,
                'price': price,
                'condition': self.get_condition_description(),
                'expiry': expiry_str,
                'status': '等待中',
                'created_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # 如果是高级止盈止损策略，添加额外参数
            if "高级止盈止损策略" in order_type:
                # 保存成本价
                order['cost_price'] = self.cost_price_input_spin.value()
                order['enabled_strategies'] = []
                if self.enable_strategy1_cb.isChecked():
                    order['enabled_strategies'].append(1)
                if self.enable_strategy2_cb.isChecked():
                    order['enabled_strategies'].append(2)
                if self.enable_strategy3_cb.isChecked():
                    order['enabled_strategies'].append(3)
                if self.enable_strategy4_cb.isChecked():
                    order['enabled_strategies'].append(4)

                # 保存各策略参数
                order['strategy_params'] = {}
                if 1 in order['enabled_strategies']:
                    order['strategy_params']['s1_profit_min'] = self.s1_profit_min_spin.value() / 100
                    order['strategy_params']['s1_profit_max'] = self.s1_profit_max_spin.value() / 100
                    order['strategy_params']['s1_pullback'] = self.s1_pullback_spin.value() / 100
                if 2 in order['enabled_strategies']:
                    order['strategy_params']['s2_rise_threshold'] = self.s2_rise_threshold_spin.value() / 100
                    order['strategy_params']['s2_pullback'] = self.s2_pullback_spin.value() / 100
                if 3 in order['enabled_strategies']:
                    order['strategy_params']['s3_gap_open'] = self.s3_gap_open_spin.value() / 100
                    order['strategy_params']['s3_high_above_open'] = self.s3_high_above_open_spin.value() / 100
                    order['strategy_params']['s3_pullback'] = self.s3_pullback_spin.value() / 100
                if 4 in order['enabled_strategies']:
                    order['strategy_params']['s4_loss_threshold'] = self.s4_loss_threshold_spin.value() / 100

            # 添加到列表
            self.orders.append(order)

            # 更新显示
            self.update_order_table()

            # 日志输出
            self.log("=" * 60)
            self.log(f"创建条件单成功: {order['id']}")
            self.log(f"  类型: {order['type']}")
            self.log(f"  股票: {order['stock_code']}")
            self.log(f"  条件: {order['condition']}")
            self.log(f"  动作: {order['action']} {order['quantity']}股 @ {order['price']:.2f}")
            self.log(f"  有效期至: {order['expiry']}")
            self.log("=" * 60)

            QMessageBox.information(self, "创建成功",
                f"条件单已创建！\n\n"
                f"条件单ID: {order['id']}\n"
                f"类型: {order['type']}\n"
                f"条件: {order['condition']}\n\n"
                f"请在命令行窗口监控执行情况。"
            )

        except Exception as e:
            QMessageBox.critical(self, "创建失败", f"无法创建条件单:\n{str(e)}")
            import traceback
            traceback.print_exc()

    def update_order_table(self):
        """更新条件单表格"""
        self.order_table.setRowCount(len(self.orders))

        for row, order in enumerate(self.orders):
            # ID
            self.order_table.setItem(row, 0, QTableWidgetItem(order['id']))

            # 类型
            order_type = order['type']
            if "价格条件" in order_type:
                type_str = "价格"
            elif "时间条件" in order_type:
                type_str = "时间"
            elif "涨跌幅" in order_type:
                type_str = "涨跌幅"
            elif "止盈止损单" in order_type:
                type_str = "止盈止损"
            elif "高级止盈止损策略" in order_type:
                type_str = "高级止损"
            else:
                type_str = order_type[:4]
            self.order_table.setItem(row, 1, QTableWidgetItem(type_str))

            # 股票
            self.order_table.setItem(row, 2, QTableWidgetItem(order['stock_code']))

            # 条件
            condition = order['condition']
            if len(condition) > 30:
                condition = condition[:30] + "..."
            self.order_table.setItem(row, 3, QTableWidgetItem(condition))

            # 动作
            action_str = f"{order['action']}{order['quantity']}股"
            self.order_table.setItem(row, 4, QTableWidgetItem(action_str))

            # 状态
            status = order['status']
            status_item = QTableWidgetItem(status)
            if status == "等待中":
                status_item.setForeground(QColor(0, 150, 0))
            elif status == "已触发":
                status_item.setForeground(QColor(0, 0, 255))
            elif status == "已过期":
                status_item.setForeground(QColor(150, 150, 150))
            self.order_table.setItem(row, 5, status_item)

            # 操作
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(5, 2, 5, 2)

            view_btn = QPushButton("查看")
            view_btn.clicked.connect(lambda checked, r=row: self.view_order(r))
            btn_layout.addWidget(view_btn)

            self.order_table.setCellWidget(row, 6, btn_widget)

    def view_order(self, row):
        """查看条件单详情"""
        order = self.orders[row]

        details = f"""
条件单详情

ID: {order['id']}
类型: {order['type']}
股票代码: {order['stock_code']}
条件: {order['condition']}
动作: {order['action']} {order['quantity']}股 @ {order['price']:.2f}
有效期至: {order['expiry']}
状态: {order['status']}
创建时间: {order['created_time']}
        """

        QMessageBox.information(self, f"条件单详情 - {order['id']}", details)

    def on_order_clicked(self, row, col):
        """表格项点击事件"""
        if col == 6:  # 操作列
            pass  # 操作由按钮处理
        else:
            self.view_order(row)

    def delete_selected_order(self):
        """删除选中的条件单"""
        current_row = self.order_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "未选择", "请先选择要删除的条件单")
            return

        order = self.orders[current_row]

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除条件单 {order['id']} 吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            del self.orders[current_row]
            self.update_order_table()
            self.log(f"条件单已删除: {order['id']}")

    def disable_selected_order(self):
        """禁用选中的条件单"""
        current_row = self.order_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "未选择", "请先选择要禁用的条件单")
            return

        self.orders[current_row]['status'] = '已禁用'
        self.update_order_table()
        self.log(f"条件单已禁用: {self.orders[current_row]['id']}")

    def enable_selected_order(self):
        """启用选中的条件单"""
        current_row = self.order_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "未选择", "请先选择要启用的条件单")
            return

        self.orders[current_row]['status'] = '等待中'
        self.update_order_table()
        self.log(f"条件单已启用: {self.orders[current_row]['id']}")

    def refresh_order_list(self):
        """刷新条件单列表"""
        self.update_order_table()
        self.log("条件单列表已刷新")

    def clear_form(self):
        """清空表单"""
        self.stock_code_edit.clear()
        self.order_quantity_spin.setValue(100)
        self.order_price_spin.setValue(100.0)
        self.log("表单已清空")

    def setup_timer(self):
        """设置定时器"""
        # 监控定时器
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.monitor_orders)
        self.monitor_timer.start(5000)  # 每5秒检查一次

    def init_trade_connection(self):
        """初始化交易连接"""
        if not EASYXT_AVAILABLE:
            self.log("提示: EasyXT不可用，条件单功能受限")
            return

        try:
            import easy_xt
            import json
            import os

            # 读取统一配置文件
            config_file = os.path.join(
                os.path.dirname(__file__), '..', '..', 'config', 'unified_config.json'
            )
            if not os.path.exists(config_file):
                self.log("提示: 未找到统一配置文件 (config/unified_config.json)")
                return

            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 获取QMT路径和账户ID
            settings = config.get('settings', {})
            account_config = settings.get('account', {})

            userdata_path = account_config.get('qmt_path', '')
            account_id = account_config.get('account_id', '')

            if not userdata_path:
                self.log("提示: 统一配置文件中未设置QMT路径 (settings.account.qmt_path)")
                return

            if not account_id:
                self.log("提示: 统一配置文件中未设置账户ID (settings.account.account_id)")
                return

            self.log(f"正在初始化交易连接...")
            self.log(f"  QMT路径: {userdata_path}")
            self.log(f"  账户ID: {account_id}")

            # 获取扩展API实例
            self.trade_api = easy_xt.get_extended_api()

            # 初始化交易服务
            if hasattr(self.trade_api, 'init_trade'):
                result = self.trade_api.init_trade(userdata_path)
                if result:
                    self._trade_initialized = True
                    self.log("✓ 交易服务连接成功")
                else:
                    self.log("✗ 交易服务连接失败")
                    return

            # 添加账户
            account_type = 'STOCK'  # 默认使用股票账户
            try:
                if hasattr(self.trade_api, 'add_account'):
                    if self.trade_api.add_account(account_id, account_type):
                        self.log(f"✓ 已添加账户: {account_id} ({account_type})")
                    else:
                        self.log(f"✗ 添加账户失败: {account_id}")
                else:
                    # 如果没有add_account方法，说明API版本不同，跳过这一步
                    self.log(f"ℹ️ 账户 {account_id} 已连接 (跳过账户添加)")
            except Exception as e:
                # 添加账户失败不影响条件单功能
                self.log(f"⚠️ 添加账户时出现警告: {str(e)}")
                self.log(f"ℹ️ 条件单功能仍可正常使用")

        except Exception as e:
            self.log(f"初始化交易连接时出错: {str(e)}")
            import traceback
            traceback.print_exc()

    def monitor_orders(self):
        """监控条件单并自动触发"""
        if not EASYXT_AVAILABLE:
            return

        try:
            from xtquant import xtdata

            for order in self.orders:
                # 跳过已触发、已禁用或已过期的条件单
                if order['status'] not in ['等待中']:
                    continue

                # 检查是否过期
                try:
                    expiry_time = datetime.strptime(order['expiry'], "%Y-%m-%d %H:%M:%S")
                    if datetime.now() > expiry_time:
                        order['status'] = '已过期'
                        self.log(f"条件单已过期: {order['id']}")
                        self.update_order_table()
                        continue
                except:
                    pass

                # 根据条件单类型进行监控
                order_type = order['type']
                stock_code = order['stock_code']

                # 获取当前价格
                current_price = self._get_current_price(stock_code)
                if current_price is None or current_price <= 0:
                    continue

                # 检查是否触发条件
                triggered = False

                if "价格条件单" in order_type:
                    triggered = self._check_price_condition(order, current_price)
                elif "涨跌幅条件单" in order_type:
                    triggered = self._check_change_condition(order, current_price)
                elif "时间条件单" in order_type:
                    triggered = self._check_time_condition(order)
                elif "止盈止损单" in order_type:
                    triggered = self._check_stop_condition(order, current_price)
                elif "高级止盈止损策略" in order_type:
                    triggered = self._check_advanced_stop_loss_condition(order, current_price)

                # 如果触发条件满足，执行交易
                if triggered:
                    self._execute_order(order, current_price)

        except Exception as e:
            self.log(f"监控条件单时出错: {str(e)}")

    def _get_current_price(self, stock_code: str) -> Optional[float]:
        """获取股票当前价格"""
        try:
            from xtquant import xtdata
            from easy_xt.utils import StockCodeUtils

            normalized_code = StockCodeUtils.normalize_code(stock_code)

            # 尝试使用get_full_tick获取实时价格
            tick_data = xtdata.get_full_tick([normalized_code])
            if tick_data and normalized_code in tick_data:
                tick_info = tick_data[normalized_code]
                if tick_info and 'lastPrice' in tick_info:
                    return float(tick_info['lastPrice'])
                elif tick_info and 'price' in tick_info:
                    return float(tick_info['price'])

            # 如果失败，尝试get_market_data
            current_data = xtdata.get_market_data(
                stock_list=[normalized_code],
                period='tick',
                count=1
            )

            if current_data and isinstance(current_data, dict) and normalized_code in current_data:
                data_array = current_data[normalized_code]
                if hasattr(data_array, '__len__') and len(data_array) > 0:
                    first_item = data_array[0]
                    if hasattr(first_item, 'lastPrice'):
                        return float(first_item['lastPrice'])

            return None
        except Exception as e:
            print(f"获取{stock_code}当前价格失败: {str(e)}")
            return None

    def _check_price_condition(self, order: dict, current_price: float) -> bool:
        """检查价格条件"""
        try:
            condition = order['condition']
            # 解析条件，例如："价格条件单 - 价格大于等于 5.00元"
            if "价格大于等于" in condition:
                import re
                match = re.search(r'(\d+\.?\d*)元', condition)
                if match:
                    target_price = float(match.group(1))
                    return current_price >= target_price

            elif "价格小于等于" in condition:
                import re
                match = re.search(r'(\d+\.?\d*)元', condition)
                if match:
                    target_price = float(match.group(1))
                    return current_price <= target_price

            elif "价格突破" in condition:
                import re
                match = re.search(r'(\d+\.?\d*)元', condition)
                if match:
                    target_price = float(match.group(1))
                    # 突破通常指从下向上突破
                    return current_price > target_price

            return False
        except Exception as e:
            print(f"检查价格条件失败: {str(e)}")
            return False

    def _check_change_condition(self, order: dict, current_price: float) -> bool:
        """检查涨跌幅条件"""
        try:
            condition = order['condition']
            # 需要获取基准价格
            # 这里简化处理，假设基准价格已存储
            # 实际需要根据reference_price_combo获取
            return False
        except:
            return False

    def _check_time_condition(self, order: dict) -> bool:
        """检查时间条件"""
        try:
            condition = order['condition']
            # 解析触发时间，例如："时间条件单 - 在 2026-01-27 16:30:00 触发"
            import re
            match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', condition)
            if match:
                trigger_time = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
                return datetime.now() >= trigger_time
            return False
        except:
            return False

    def _check_stop_condition(self, order: dict, current_price: float) -> bool:
        """检查止盈止损条件"""
        try:
            condition = order['condition']
            # 解析止盈止损价格
            import re
            has_stop_loss = "止损价" in condition
            has_stop_profit = "止盈价" in condition

            if has_stop_loss:
                match = re.search(r'止损价: (\d+\.?\d*)', condition)
                if match:
                    stop_loss_price = float(match.group(1))
                    if current_price <= stop_loss_price:
                        return True

            if has_stop_profit:
                match = re.search(r'止盈价: (\d+\.?\d*)', condition)
                if match:
                    stop_profit_price = float(match.group(1))
                    if current_price >= stop_profit_price:
                        return True

            return False
        except:
            return False

    def _check_advanced_stop_loss_condition(self, order: dict, current_price: float) -> bool:
        """检查高级止盈止损策略条件"""
        try:
            # 初始化运行时状态（如果还没有）
            if 'runtime_state' not in order:
                order['runtime_state'] = {
                    'highest_price': order.get('cost_price', current_price),
                    'lowest_price': order.get('cost_price', current_price),
                    'highest_price_after_profit': 0.0,
                    'today_open_price': None,
                    'yesterday_close_price': None,
                }

            state = order['runtime_state']
            cost_price = order.get('cost_price', current_price)
            enabled_strategies = order.get('enabled_strategies', [1, 2, 3, 4])

            # 更新最高价和最低价
            state['highest_price'] = max(state['highest_price'], current_price)
            state['lowest_price'] = min(state['lowest_price'], current_price)

            # 获取今日开盘价和昨收价
            try:
                from xtquant import xtdata
                from easy_xt.utils import StockCodeUtils
                normalized_code = StockCodeUtils.normalize_code(order['stock_code'])
                tick_data = xtdata.get_full_tick([normalized_code])
                if tick_data and normalized_code in tick_data:
                    tick_info = tick_data[normalized_code]
                    if 'open' in tick_info:
                        state['today_open_price'] = float(tick_info['open'])
                    if 'lastClose' in tick_info:
                        state['yesterday_close_price'] = float(tick_info['lastClose'])
            except:
                pass

            # 获取策略参数（从订单中获取，如果没有则使用默认值）
            params = order.get('strategy_params', {})
            if not params:
                # 如果没有参数，使用默认的中长线稳健参数
                params = {
                    's1_profit_min': 0.20, 's1_profit_max': 0.50, 's1_pullback': 0.10,
                    's2_rise_threshold': 0.10, 's2_pullback': 0.05,
                    's3_gap_open': 0.03, 's3_high_above_open': 0.02, 's3_pullback': 0.02,
                    's4_loss_threshold': -0.05,
                }

            # 检查各策略
            triggered_strategies = []

            # 策略1: 浮盈回落止损
            if 1 in enabled_strategies:
                triggered, reason = self._check_strategy1_advanced(state, current_price, cost_price, params)
                if triggered:
                    triggered_strategies.append(('策略1', reason))

            # 策略2: 最高价回落止损
            if 2 in enabled_strategies:
                triggered, reason = self._check_strategy2_advanced(state, current_price, cost_price, params)
                if triggered:
                    triggered_strategies.append(('策略2', reason))

            # 策略3: 高开回落止损
            if 3 in enabled_strategies:
                triggered, reason = self._check_strategy3_advanced(state, current_price, cost_price, params)
                if triggered:
                    triggered_strategies.append(('策略3', reason))

            # 策略4: 总体亏损止损
            if 4 in enabled_strategies:
                triggered, reason = self._check_strategy4_advanced(state, current_price, cost_price, params)
                if triggered:
                    triggered_strategies.append(('策略4', reason))

            # 如果有策略触发
            if triggered_strategies:
                self.log(f"🚨 高级止盈止损触发: {order['id']}")
                for strategy_name, reason in triggered_strategies:
                    self.log(f"  {strategy_name}: {reason}")
                return True

            return False

        except Exception as e:
            self.log(f"检查高级止盈止损条件失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _check_strategy1_advanced(self, state: dict, current_price: float, cost_price: float, params: dict) -> tuple:
        """检查策略1：浮盈回落止损"""
        current_profit = (current_price - cost_price) / cost_price

        s1_min = params.get('s1_profit_min', 0.20)
        s1_max = params.get('s1_profit_max', 0.50)
        s1_pullback = params.get('s1_pullback', 0.10)

        if current_profit < s1_min:
            return False, ""

        if current_profit >= s1_max:
            return True, f"浮盈{current_profit*100:.1f}%，超过目标{s1_max*100:.0f}%"

        if state['highest_price_after_profit'] == 0:
            state['highest_price_after_profit'] = current_price
        else:
            state['highest_price_after_profit'] = max(state['highest_price_after_profit'], current_price)

        pullback_ratio = (state['highest_price_after_profit'] - current_price) / state['highest_price_after_profit']

        if pullback_ratio >= s1_pullback:
            return True, f"从最高价回落{pullback_ratio*100:.1f}%，触发止损线{s1_pullback*100:.0f}%"

        return False, ""

    def _check_strategy2_advanced(self, state: dict, current_price: float, cost_price: float, params: dict) -> tuple:
        """检查策略2：最高价回落止损"""
        highest_price = state['highest_price']
        highest_rise = (highest_price - cost_price) / cost_price

        s2_threshold = params.get('s2_rise_threshold', 0.10)
        s2_pullback = params.get('s2_pullback', 0.05)

        if highest_rise < s2_threshold:
            return False, ""

        pullback_ratio = (highest_price - current_price) / highest_price

        if pullback_ratio >= s2_pullback:
            return True, f"最高价涨幅{highest_rise*100:.1f}%，回落{pullback_ratio*100:.1f}%，触发止损"

        return False, ""

    def _check_strategy3_advanced(self, state: dict, current_price: float, cost_price: float, params: dict) -> tuple:
        """检查策略3：高开回落止损"""
        if state['today_open_price'] is None or state['yesterday_close_price'] is None:
            return False, ""

        s3_gap_open = params.get('s3_gap_open', 0.03)
        s3_high_above = params.get('s3_high_above_open', 0.02)
        s3_pullback = params.get('s3_pullback', 0.02)

        gap_open_ratio = (state['today_open_price'] - state['yesterday_close_price']) / state['yesterday_close_price']

        if gap_open_ratio < s3_gap_open:
            return False, ""

        high_above_ratio = (state['highest_price'] - state['today_open_price']) / state['today_open_price']

        if high_above_ratio < s3_high_above:
            return False, ""

        pullback_ratio = (state['highest_price'] - current_price) / state['highest_price']

        if pullback_ratio >= s3_pullback:
            return True, f"高开{gap_open_ratio*100:.1f}%，回落{pullback_ratio*100:.1f}%，触发止损"

        return False, ""

    def _check_strategy4_advanced(self, state: dict, current_price: float, cost_price: float, params: dict) -> tuple:
        """检查策略4：总体亏损止损"""
        profit_loss = (current_price - cost_price) / cost_price

        s4_threshold = params.get('s4_loss_threshold', -0.05)

        if profit_loss <= s4_threshold:
            return True, f"浮亏{abs(profit_loss)*100:.1f}%，触发止损线{abs(s4_threshold)*100:.0f}%"

        return False, ""

        if pullback_ratio >= params['s3_pullback']:
            return True, f"高开{gap_open_ratio*100:.1f}%，回落{pullback_ratio*100:.1f}%，触发止损"

        return False, ""

    def _check_strategy4_advanced(self, state: dict, current_price: float, cost_price: float, params: dict) -> tuple:
        """检查策略4：总体亏损止损"""
        profit_loss = (current_price - cost_price) / cost_price

        if profit_loss <= params['s4_loss_threshold']:
            return True, f"浮亏{abs(profit_loss)*100:.1f}%，触发止损线{abs(params['s4_loss_threshold'])*100:.0f}%"

        return False, ""

    def _execute_order(self, order: dict, current_price: float):
        """执行订单"""
        try:
            # 检查交易API是否已初始化
            if self.trade_api is None or not self._trade_initialized:
                self.log(f"提示: 交易API未初始化，请检查配置文件中的QMT路径")
                self.add_to_history(order, current_price, "交易服务未连接")
                return

            # 检查trade_api是否存在
            if not hasattr(self.trade_api, 'trade_api') or self.trade_api.trade_api is None:
                self.log(f"提示: trade_api未初始化")
                self.add_to_history(order, current_price, "交易服务未连接")
                return

            # 检查是否已添加账户
            if not hasattr(self.trade_api.trade_api, 'accounts') or not self.trade_api.trade_api.accounts:
                self.log(f"提示: 未添加交易账户，请先在'网格交易'中配置账户")
                self.add_to_history(order, current_price, "未添加交易账户")
                return

            account_id = list(self.trade_api.trade_api.accounts.keys())[0]

            # 确定订单类型
            action = order['action']
            order_type = 'buy' if action == '买入' else 'sell'

            # 确定下单价格（0表示市价）
            order_price = order['price'] if order['price'] > 0 else current_price
            price_type = 'limit' if order['price'] > 0 else 'market'

            # 执行下单
            if order_type == 'buy':
                order_id = self.trade_api.trade_api.buy(
                    account_id=account_id,
                    code=order['stock_code'],
                    volume=order['quantity'],
                    price=order_price,
                    price_type=price_type
                )
            else:
                order_id = self.trade_api.trade_api.sell(
                    account_id=account_id,
                    code=order['stock_code'],
                    volume=order['quantity'],
                    price=order_price,
                    price_type=price_type
                )

            if order_id:
                order['status'] = '已触发'
                self.update_order_table()
                self.log(f"✓ 条件单触发成功: {order['id']}, 委托号: {order_id}")

                # 添加到触发历史
                self.add_to_history(order, current_price, f"委托成功: {order_id}")
            else:
                self.log(f"✗ 条件单触发失败: {order['id']}, 下单失败")
                self.add_to_history(order, current_price, "下单失败")

        except Exception as e:
            self.log(f"✗ 执行条件单失败: {str(e)}")
            self.add_to_history(order, current_price, f"执行异常: {str(e)}")
            import traceback
            traceback.print_exc()

    def add_to_history(self, order: dict, trigger_price: float, result: str):
        """添加到触发历史"""
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.history_table.setItem(row, 0, QTableWidgetItem(timestamp))
        self.history_table.setItem(row, 1, QTableWidgetItem(order['id']))

        condition = order['condition']
        if len(condition) > 20:
            condition = condition[:20] + "..."
        self.history_table.setItem(row, 2, QTableWidgetItem(condition))

        self.history_table.setItem(row, 3, QTableWidgetItem(f"{trigger_price:.2f}"))
        self.history_table.setItem(row, 4, QTableWidgetItem(result))

    def log(self, message: str):
        """输出日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        self.log_text.append(log_message)
        self.log_text.moveCursor(QTextCursor.End)


# 导出类
__all__ = ['ConditionalOrderWidget']
