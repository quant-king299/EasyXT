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
        self.init_ui()
        self.setup_timer()

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
            "止盈止损单"
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
        self.order_price_spin.setRange(0.01, 9999.99)
        self.order_price_spin.setValue(100.0)
        self.order_price_spin.setDecimals(2)
        self.order_price_spin.setSuffix(" (0=市价)")
        action_layout.addRow("价格:", self.order_price_spin)

        layout.addWidget(action_group)

        # 有效期设置
        expiry_group = QGroupBox("有效期设置")
        expiry_layout = QFormLayout(expiry_group)
        expiry_layout.setSpacing(12)  # 行间距12px
        expiry_layout.setContentsMargins(15, 20, 15, 15)  # 边距
        # 设置标签和输入框之间的水平间距
        expiry_layout.setHorizontalSpacing(18)  # 标签与输入框间距18px
        expiry_layout.setVerticalSpacing(15)  # 行间距15px

        self.valid_date_edit = QDateEdit()
        self.valid_date_edit.setMinimumWidth(200)  # 设置最小宽度200px
        self.valid_date_edit.setDate(datetime.now().date() + timedelta(days=1))
        self.valid_date_edit.setCalendarPopup(True)
        expiry_layout.addRow("有效日期:", self.valid_date_edit)

        self.valid_time_edit = QDateTimeEdit()
        self.valid_time_edit.setMinimumWidth(250)  # 设置最小宽度250px
        self.valid_time_edit.setDateTime(
            QDateTime.currentDateTime().addDays(1)
        )
        self.valid_time_edit.setDisplayFormat("yyyy-MM-dd hh:mm:ss")
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
        elif "止盈止损" in order_type:
            self.create_stop_condition_ui(parent_widget)

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

        elif "止盈止损" in order_type:
            stop_type = self.stop_type_combo.currentText()
            desc += f"{stop_type}"
            if "止盈" in stop_type or "止盈止损" in stop_type:
                profit = self.stop_profit_price_spin.value()
                desc += f" (止盈价: {profit:.2f})"
            if "止损" in stop_type or "止盈止损" in stop_type:
                loss = self.stop_loss_price_spin.value()
                desc += f" (止损价: {loss:.2f})"

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
                'expiry': self.valid_time_edit.dateTime().toString("yyyy-MM-dd hh:mm:ss"),
                'status': '等待中',
                'created_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

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
            elif "止盈止损" in order_type:
                type_str = "止盈止损"
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

    def monitor_orders(self):
        """监控条件单（模拟触发）"""
        # 这里应该连接到实际的条件单监控系统
        # 目前只是模拟
        pass

    def log(self, message: str):
        """输出日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        self.log_text.append(log_message)
        self.log_text.moveCursor(QTextCursor.End)


# 导出类
__all__ = ['ConditionalOrderWidget']
