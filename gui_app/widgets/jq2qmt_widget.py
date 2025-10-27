#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JQ2QMT集成GUI组件
提供JQ2QMT功能的可视化管理界面
"""

import sys
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox,
    QProgressBar, QSplitter, QFrame, QMessageBox,
    QFileDialog, QFormLayout, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

# 添加strategies路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'strategies'))

try:
    from adapters.jq2qmt_adapter import EasyXTJQ2QMTAdapter, jq2qmt_manager
    from adapters.data_converter import DataConverter, PositionDiffer
    JQ2QMT_AVAILABLE = True
except ImportError:
    JQ2QMT_AVAILABLE = False


class JQ2QMTConfigWidget(QWidget):
    """JQ2QMT配置组件"""
    
    def __init__(self):
        super().__init__()
        self.config = {}
        self.init_ui()
        self.load_default_config()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 基础配置
        basic_group = QGroupBox("基础配置")
        basic_layout = QFormLayout(basic_group)
        
        self.server_url_edit = QLineEdit("http://localhost:5366")
        basic_layout.addRow("服务器地址:", self.server_url_edit)
        
        self.enabled_checkbox = QCheckBox("启用JQ2QMT集成")
        basic_layout.addRow("", self.enabled_checkbox)
        
        layout.addWidget(basic_group)
        
        # 认证配置
        auth_group = QGroupBox("认证配置")
        auth_layout = QFormLayout(auth_group)
        
        self.use_crypto_auth = QCheckBox("使用RSA加密认证")
        self.use_crypto_auth.setChecked(True)
        auth_layout.addRow("", self.use_crypto_auth)
        
        self.client_id_edit = QLineEdit("easyxt_client")
        auth_layout.addRow("客户端ID:", self.client_id_edit)
        
        # 私钥文件选择
        key_layout = QHBoxLayout()
        self.private_key_file_edit = QLineEdit("keys/easyxt_private.pem")
        self.browse_key_button = QPushButton("浏览...")
        self.browse_key_button.clicked.connect(self.browse_private_key)
        key_layout.addWidget(self.private_key_file_edit)
        key_layout.addWidget(self.browse_key_button)
        auth_layout.addRow("私钥文件:", key_layout)
        
        self.simple_api_key_edit = QLineEdit()
        self.simple_api_key_edit.setPlaceholderText("简单API密钥（不使用RSA时）")
        auth_layout.addRow("API密钥:", self.simple_api_key_edit)
        
        layout.addWidget(auth_group)
        
        # 同步设置
        sync_group = QGroupBox("同步设置")
        sync_layout = QFormLayout(sync_group)
        
        self.auto_sync_checkbox = QCheckBox("自动同步持仓")
        self.auto_sync_checkbox.setChecked(True)
        sync_layout.addRow("", self.auto_sync_checkbox)
        
        self.sync_interval_spin = QSpinBox()
        self.sync_interval_spin.setRange(10, 3600)
        self.sync_interval_spin.setValue(30)
        self.sync_interval_spin.setSuffix(" 秒")
        sync_layout.addRow("同步间隔:", self.sync_interval_spin)
        
        self.retry_times_spin = QSpinBox()
        self.retry_times_spin.setRange(1, 10)
        self.retry_times_spin.setValue(3)
        sync_layout.addRow("重试次数:", self.retry_times_spin)
        
        layout.addWidget(sync_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.test_connection_button = QPushButton("测试连接")
        self.test_connection_button.clicked.connect(self.test_connection)
        
        self.save_config_button = QPushButton("保存配置")
        self.save_config_button.clicked.connect(self.save_config)
        
        self.load_config_button = QPushButton("加载配置")
        self.load_config_button.clicked.connect(self.load_config)
        
        button_layout.addWidget(self.test_connection_button)
        button_layout.addStretch()
        button_layout.addWidget(self.load_config_button)
        button_layout.addWidget(self.save_config_button)
        
        layout.addLayout(button_layout)
        
        # 状态显示
        self.status_label = QLabel("状态: 未连接")
        layout.addWidget(self.status_label)
    
    def browse_private_key(self):
        """浏览私钥文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择私钥文件", "", "PEM文件 (*.pem);;所有文件 (*)"
        )
        if file_path:
            self.private_key_file_edit.setText(file_path)
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return {
            'enabled': self.enabled_checkbox.isChecked(),
            'server_url': self.server_url_edit.text(),
            'auth_config': {
                'use_crypto_auth': self.use_crypto_auth.isChecked(),
                'client_id': self.client_id_edit.text(),
                'private_key_file': self.private_key_file_edit.text(),
                'simple_api_key': self.simple_api_key_edit.text()
            },
            'sync_settings': {
                'auto_sync': self.auto_sync_checkbox.isChecked(),
                'sync_interval': self.sync_interval_spin.value(),
                'retry_times': self.retry_times_spin.value()
            }
        }
    
    def set_config(self, config: Dict[str, Any]):
        """设置配置"""
        self.enabled_checkbox.setChecked(config.get('enabled', False))
        self.server_url_edit.setText(config.get('server_url', 'http://localhost:5366'))
        
        auth_config = config.get('auth_config', {})
        self.use_crypto_auth.setChecked(auth_config.get('use_crypto_auth', True))
        self.client_id_edit.setText(auth_config.get('client_id', 'easyxt_client'))
        self.private_key_file_edit.setText(auth_config.get('private_key_file', 'keys/easyxt_private.pem'))
        self.simple_api_key_edit.setText(auth_config.get('simple_api_key', ''))
        
        sync_settings = config.get('sync_settings', {})
        self.auto_sync_checkbox.setChecked(sync_settings.get('auto_sync', True))
        self.sync_interval_spin.setValue(sync_settings.get('sync_interval', 30))
        self.retry_times_spin.setValue(sync_settings.get('retry_times', 3))
    
    def load_default_config(self):
        """加载默认配置"""
        default_config = {
            'enabled': False,
            'server_url': 'http://localhost:5366',
            'auth_config': {
                'use_crypto_auth': True,
                'client_id': 'easyxt_client',
                'private_key_file': 'keys/easyxt_private.pem',
                'simple_api_key': ''
            },
            'sync_settings': {
                'auto_sync': True,
                'sync_interval': 30,
                'retry_times': 3
            }
        }
        self.set_config(default_config)
    
    def test_connection(self):
        """测试连接"""
        if not JQ2QMT_AVAILABLE:
            QMessageBox.warning(self, "警告", "JQ2QMT适配器不可用，请检查安装")
            return
        
        config = self.get_config()
        if not config['enabled']:
            QMessageBox.information(self, "提示", "请先启用JQ2QMT集成")
            return
        
        try:
            adapter = EasyXTJQ2QMTAdapter(config)
            if adapter.test_connection():
                self.status_label.setText("状态: 连接成功")
                self.status_label.setStyleSheet("color: green")
                QMessageBox.information(self, "成功", "JQ2QMT服务器连接成功")
            else:
                self.status_label.setText("状态: 连接失败")
                self.status_label.setStyleSheet("color: red")
                QMessageBox.warning(self, "失败", "JQ2QMT服务器连接失败")
        except Exception as e:
            self.status_label.setText(f"状态: 错误 - {str(e)}")
            self.status_label.setStyleSheet("color: red")
            QMessageBox.critical(self, "错误", f"连接测试失败: {str(e)}")
    
    def save_config(self):
        """保存配置"""
        config = self.get_config()
        try:
            config_file = "config/jq2qmt_config.json"
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(self, "成功", "配置已保存")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")
    
    def load_config(self):
        """加载配置"""
        try:
            config_file = "config/jq2qmt_config.json"
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.set_config(config)
                QMessageBox.information(self, "成功", "配置已加载")
            else:
                QMessageBox.information(self, "提示", "配置文件不存在，使用默认配置")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载配置失败: {str(e)}")


class PositionViewerWidget(QWidget):
    """持仓查看器组件"""
    
    def __init__(self):
        super().__init__()
        self.adapter = None
        self.init_ui()
        self.setup_timer()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 控制面板
        control_layout = QHBoxLayout()
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItem("所有策略", "all")
        control_layout.addWidget(QLabel("策略:"))
        control_layout.addWidget(self.strategy_combo)
        
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh_positions)
        control_layout.addWidget(self.refresh_button)
        
        self.auto_refresh_checkbox = QCheckBox("自动刷新")
        self.auto_refresh_checkbox.setChecked(True)
        control_layout.addWidget(self.auto_refresh_checkbox)
        
        control_layout.addStretch()
        
        self.status_label = QLabel("状态: 未连接")
        control_layout.addWidget(self.status_label)
        
        layout.addLayout(control_layout)
        
        # 持仓表格
        self.position_table = QTableWidget()
        self.position_table.setColumnCount(6)
        self.position_table.setHorizontalHeaderLabels([
            "股票代码", "股票名称", "持仓数量", "成本价", "市值", "更新时间"
        ])
        
        # 设置表格属性
        header = self.position_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.position_table.setAlternatingRowColors(True)
        self.position_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        layout.addWidget(self.position_table)
        
        # 统计信息
        stats_layout = QHBoxLayout()
        
        self.total_positions_label = QLabel("总持仓: 0")
        self.total_value_label = QLabel("总市值: ¥0.00")
        self.last_update_label = QLabel("最后更新: 未知")
        
        stats_layout.addWidget(self.total_positions_label)
        stats_layout.addWidget(self.total_value_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.last_update_label)
        
        layout.addLayout(stats_layout)
    
    def setup_timer(self):
        """设置定时器"""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh)
        self.refresh_timer.start(30000)  # 30秒刷新一次
    
    def set_adapter(self, adapter: EasyXTJQ2QMTAdapter):
        """设置适配器"""
        self.adapter = adapter
        self.refresh_positions()
    
    def refresh_positions(self):
        """刷新持仓数据"""
        if not self.adapter or not self.adapter.is_available():
            self.status_label.setText("状态: 适配器不可用")
            self.status_label.setStyleSheet("color: red")
            return
        
        try:
            strategy_name = self.strategy_combo.currentData()
            
            if strategy_name == "all":
                # 获取所有策略持仓
                all_strategies = self.adapter.get_all_strategies()
                if all_strategies:
                    self.display_all_strategies(all_strategies)
                else:
                    self.clear_table()
            else:
                # 获取指定策略持仓
                positions = self.adapter.get_strategy_positions(strategy_name)
                if positions:
                    self.display_positions(positions)
                else:
                    self.clear_table()
            
            self.status_label.setText("状态: 刷新成功")
            self.status_label.setStyleSheet("color: green")
            
        except Exception as e:
            self.status_label.setText(f"状态: 刷新失败 - {str(e)}")
            self.status_label.setStyleSheet("color: red")
    
    def display_positions(self, positions: List[Dict]):
        """显示持仓数据"""
        self.position_table.setRowCount(len(positions))
        
        total_value = 0.0
        
        for row, pos in enumerate(positions):
            # 股票代码
            self.position_table.setItem(row, 0, QTableWidgetItem(pos.get('symbol', '')))
            
            # 股票名称
            self.position_table.setItem(row, 1, QTableWidgetItem(pos.get('name', '')))
            
            # 持仓数量
            quantity = pos.get('quantity', 0)
            self.position_table.setItem(row, 2, QTableWidgetItem(str(quantity)))
            
            # 成本价
            avg_price = pos.get('avg_price', 0.0)
            self.position_table.setItem(row, 3, QTableWidgetItem(f"{avg_price:.3f}"))
            
            # 市值
            market_value = pos.get('market_value', quantity * avg_price)
            self.position_table.setItem(row, 4, QTableWidgetItem(f"{market_value:.2f}"))
            total_value += market_value
            
            # 更新时间
            update_time = datetime.now().strftime('%H:%M:%S')
            self.position_table.setItem(row, 5, QTableWidgetItem(update_time))
        
        # 更新统计信息
        self.total_positions_label.setText(f"总持仓: {len(positions)}")
        self.total_value_label.setText(f"总市值: ¥{total_value:,.2f}")
        self.last_update_label.setText(f"最后更新: {datetime.now().strftime('%H:%M:%S')}")
    
    def display_all_strategies(self, all_strategies: List[Dict]):
        """显示所有策略的持仓"""
        total_positions = []
        
        for strategy in all_strategies:
            for pos in strategy['positions']:
                pos['strategy_name'] = strategy['strategy_name']
                total_positions.append(pos)
        
        # 扩展表格列数以显示策略名称
        self.position_table.setColumnCount(7)
        self.position_table.setHorizontalHeaderLabels([
            "策略名称", "股票代码", "股票名称", "持仓数量", "成本价", "市值", "更新时间"
        ])
        
        self.position_table.setRowCount(len(total_positions))
        
        total_value = 0.0
        
        for row, pos in enumerate(total_positions):
            # 策略名称
            self.position_table.setItem(row, 0, QTableWidgetItem(pos.get('strategy_name', '')))
            
            # 股票代码
            self.position_table.setItem(row, 1, QTableWidgetItem(pos.get('symbol', '')))
            
            # 股票名称
            self.position_table.setItem(row, 2, QTableWidgetItem(pos.get('name', '')))
            
            # 持仓数量
            quantity = pos.get('quantity', 0)
            self.position_table.setItem(row, 3, QTableWidgetItem(str(quantity)))
            
            # 成本价
            avg_price = pos.get('avg_price', 0.0)
            self.position_table.setItem(row, 4, QTableWidgetItem(f"{avg_price:.3f}"))
            
            # 市值
            market_value = pos.get('market_value', quantity * avg_price)
            self.position_table.setItem(row, 5, QTableWidgetItem(f"{market_value:.2f}"))
            total_value += market_value
            
            # 更新时间
            update_time = datetime.now().strftime('%H:%M:%S')
            self.position_table.setItem(row, 6, QTableWidgetItem(update_time))
        
        # 更新统计信息
        self.total_positions_label.setText(f"总持仓: {len(total_positions)}")
        self.total_value_label.setText(f"总市值: ¥{total_value:,.2f}")
        self.last_update_label.setText(f"最后更新: {datetime.now().strftime('%H:%M:%S')}")
    
    def clear_table(self):
        """清空表格"""
        self.position_table.setRowCount(0)
        self.total_positions_label.setText("总持仓: 0")
        self.total_value_label.setText("总市值: ¥0.00")
    
    def auto_refresh(self):
        """自动刷新"""
        if self.auto_refresh_checkbox.isChecked():
            self.refresh_positions()


class JQ2QMTSyncWidget(QWidget):
    """JQ2QMT同步控制组件"""
    
    def __init__(self):
        super().__init__()
        self.adapter = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 同步控制
        sync_group = QGroupBox("同步控制")
        sync_layout = QGridLayout(sync_group)
        
        self.sync_button = QPushButton("立即同步")
        self.sync_button.clicked.connect(self.manual_sync)
        sync_layout.addWidget(self.sync_button, 0, 0)

        self.one_click_button = QPushButton("一键同步下单")
        self.one_click_button.clicked.connect(self.one_click_sync)
        sync_layout.addWidget(self.one_click_button, 0, 1)

        self.sync_all_button = QPushButton("同步所有策略")
        self.sync_all_button.clicked.connect(self.sync_all_strategies)
        sync_layout.addWidget(self.sync_all_button, 0, 2)
        
        self.auto_sync_checkbox = QCheckBox("启用自动同步")
        self.auto_sync_checkbox.setChecked(True)
        sync_layout.addWidget(self.auto_sync_checkbox, 1, 0)
        
        self.sync_progress = QProgressBar()
        sync_layout.addWidget(self.sync_progress, 1, 1)
        
        layout.addWidget(sync_group)
        
        # 同步状态
        status_group = QGroupBox("同步状态")
        status_layout = QFormLayout(status_group)
        
        self.last_sync_label = QLabel("未同步")
        status_layout.addRow("最后同步:", self.last_sync_label)
        
        self.sync_status_label = QLabel("空闲")
        status_layout.addRow("同步状态:", self.sync_status_label)
        
        self.error_label = QLabel("无")
        status_layout.addRow("最后错误:", self.error_label)
        
        layout.addWidget(status_group)
        
        # 同步日志
        log_group = QGroupBox("同步日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        log_button_layout = QHBoxLayout()
        self.clear_log_button = QPushButton("清空日志")
        self.clear_log_button.clicked.connect(self.clear_log)
        log_button_layout.addWidget(self.clear_log_button)
        log_button_layout.addStretch()
        
        log_layout.addLayout(log_button_layout)
        layout.addWidget(log_group)
    
    def set_adapter(self, adapter: EasyXTJQ2QMTAdapter):
        """设置适配器"""
        self.adapter = adapter
        self.update_status()
    
    def manual_sync(self):
        """手动同步"""
        if not self.adapter:
            self.add_log("错误: 适配器未设置")
            return
        
        # 这里需要获取当前策略的持仓数据
        # 实际实现时需要与EasyXT的策略系统集成
        self.add_log("手动同步功能需要与策略系统集成")
    
    def sync_all_strategies(self):
        """同步所有策略"""
        if not self.adapter:
            self.add_log("错误: 适配器未设置")
            return
        
        self.add_log("同步所有策略功能需要与策略系统集成")
    
    def update_status(self):
        """更新状态显示"""
        if not self.adapter:
            return
        
        status = self.adapter.get_sync_status()
        
        self.sync_status_label.setText(status['status'])
        
        if status['last_sync_time']:
            self.last_sync_label.setText(status['last_sync_time'])
        
        if status['last_error']:
            self.error_label.setText(status['last_error'])
            self.error_label.setStyleSheet("color: red")
        else:
            self.error_label.setText("无")
            self.error_label.setStyleSheet("")
    
    def add_log(self, message: str):
        """添加日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        self.log_text.append(log_message)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.clear()


class JQ2QMTWidget(QWidget):
    """JQ2QMT主界面组件"""
    
    def __init__(self):
        super().__init__()
        self.adapter = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("JQ2QMT集成管理")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 检查可用性
        if not JQ2QMT_AVAILABLE:
            warning_label = QLabel("⚠️ JQ2QMT适配器不可用，请检查jq2qmt项目是否正确安装")
            warning_label.setStyleSheet("color: red; font-weight: bold; padding: 10px;")
            warning_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(warning_label)
            return
        
        # 选项卡
        self.tab_widget = QTabWidget()
        
        # 配置选项卡
        self.config_widget = JQ2QMTConfigWidget()
        self.tab_widget.addTab(self.config_widget, "配置")
        
        # 持仓查看选项卡
        self.position_viewer = PositionViewerWidget()
        self.tab_widget.addTab(self.position_viewer, "持仓查看")
        
        # 同步控制选项卡
        self.sync_widget = JQ2QMTSyncWidget()
        self.tab_widget.addTab(self.sync_widget, "同步控制")
        
        layout.addWidget(self.tab_widget)
        
        # 连接信号
        self.config_widget.test_connection_button.clicked.connect(self.update_adapter)
    
    def update_adapter(self):
        """更新适配器"""
        if not JQ2QMT_AVAILABLE:
            return
        
        config = self.config_widget.get_config()
        if config['enabled']:
            try:
                self.adapter = EasyXTJQ2QMTAdapter(config)
                self.position_viewer.set_adapter(self.adapter)
                self.sync_widget.set_adapter(self.adapter)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建适配器失败: {str(e)}")
    
    def get_adapter(self) -> Optional[EasyXTJQ2QMTAdapter]:
        """获取当前适配器"""
        return self.adapter