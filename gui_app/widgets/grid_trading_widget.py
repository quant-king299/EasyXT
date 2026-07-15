# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger(__name__)
#!/usr/bin/env python3
"""
网格交易GUI组件
提供网格交易策略的可视化配置、监控和管理界面
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox,
    QProgressBar, QSplitter, QFrame, QMessageBox,
    QFormLayout, QScrollArea, QSizePolicy,
    QToolButton, QMenu, QAction
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize, QMutex, QWaitCondition, QObject, QEvent
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QTextCursor

# 添加项目路径
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.append(PROJECT_ROOT)
sys.path.append(os.path.join(PROJECT_ROOT, 'strategies'))


def _read_env(key: str, default: str = '') -> str:
    """从项目根目录 .env 文件读取配置"""
    try:
        env_file = os.path.join(PROJECT_ROOT, '.env')
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f'{key}='):
                        return line.split('=', 1)[1].strip()
    except Exception:
        pass
    return default

try:
    import easy_xt
    EASYXT_AVAILABLE = True
except ImportError:
    EASYXT_AVAILABLE = False
    logger.info("EasyXT未安装，部分功能将不可用")


class _NoWheelFilter(QObject):
    """禁止QSpinBox/QDoubleSpinBox滚轮调整，防止滚动页面时误改参数"""
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            event.ignore()
            return True
        return super().eventFilter(obj, event)


class StrategyThread(QThread):
    """策略运行线程"""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, strategy):
        super().__init__()
        self.strategy = strategy
        self._is_running = True

    def run(self):
        """运行策略"""
        try:
            self.log_signal.emit("策略线程已启动，开始监控...")
            # 调用策略的start方法（start方法内部会调用initialize和run）
            if hasattr(self.strategy, 'start'):
                self.strategy.start()
            elif hasattr(self.strategy, 'run'):
                # 如果没有start方法，直接调用run
                self.strategy.run()
            else:
                self.log_signal.emit("警告：策略对象没有start或run方法")
        except Exception as e:
            self.log_signal.emit(f"策略运行异常: {str(e)}")
            import traceback
            self.log_signal.emit(f"详细错误: {traceback.format_exc()}")
        finally:
            self._is_running = False
            self.finished_signal.emit()

    def stop(self):
        """停止策略"""
        self._is_running = False
        # 设置策略的is_running标志为False
        if hasattr(self.strategy, 'is_running'):
            self.strategy.is_running = False
        # 调用策略的stop方法
        if hasattr(self.strategy, 'stop'):
            try:
                self.strategy.stop()
            except Exception:                pass
        # 终止线程
        self.quit()
        self.wait(max(1000, 3000))  # 最多等待3秒


class GridTradingWidget(QWidget):
    """网格交易策略GUI组件"""

    # 信号定义
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.strategy = None
        self.is_running = False
        self.config_file = ""
        self.strategy_thread = None  # 策略线程
        self.init_ui()
        self.setup_timer()

    def init_ui(self):
        """初始化用户界面"""
        # 主布局：上下分割
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # 顶部：策略选择和账户配置（横向布局）
        top_widget = self.create_top_panel()
        main_layout.addWidget(top_widget)

        # 中部：策略参数配置（滚动区域）
        params_widget = self.create_params_panel()
        main_layout.addWidget(params_widget)

        # 底部：监控和控制区域
        monitor_widget = self.create_monitor_panel()
        main_layout.addWidget(monitor_widget)

        # 自动加载默认配置文件
        self._auto_load_default_config()

        # 禁止所有参数输入框的滚轮调整，避免滚动页面时误操作
        self._disable_spinbox_wheel()

    def create_top_panel(self) -> QWidget:
        """创建顶部面板：策略选择和账户配置"""
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setSpacing(15)

        # 左侧：策略选择
        strategy_group = QGroupBox("策略选择")
        strategy_group.setFixedWidth(350)
        strategy_layout = QVBoxLayout(strategy_group)
        strategy_layout.setSpacing(12)
        strategy_layout.setContentsMargins(15, 20, 15, 15)

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "固定网格（优化版）",
            "自适应网格策略",
            "ATR动态网格策略"
        ])
        self.strategy_combo.currentIndexChanged.connect(self.on_strategy_changed)
        strategy_layout.addWidget(QLabel("选择策略:"))
        strategy_layout.addWidget(self.strategy_combo)

        self.config_file_edit = QLineEdit()
        self.config_file_edit.setPlaceholderText("自动生成配置文件路径")
        self.config_file_edit.setReadOnly(True)
        strategy_layout.addWidget(QLabel("配置文件:"))
        strategy_layout.addWidget(self.config_file_edit)

        self.save_config_btn = QPushButton("💾 保存配置")
        self.save_config_btn.clicked.connect(self.save_config)
        self.save_config_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800; color: white;
                border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #F57C00; }
        """)
        strategy_layout.addWidget(self.save_config_btn)

        strategy_layout.addStretch()
        layout.addWidget(strategy_group)

        # 右侧：账户配置
        account_group = QGroupBox("账户配置")
        account_group.setMinimumWidth(400)
        account_layout = QFormLayout(account_group)
        account_layout.setSpacing(12)
        account_layout.setContentsMargins(15, 20, 15, 15)
        account_layout.setHorizontalSpacing(15)
        account_layout.setVerticalSpacing(12)

        # 账户信息已从 .env 自动加载，GUI 不再显示敏感信息
        self.account_type_combo = QComboBox()
        self.account_type_combo.addItems(["STOCK", "CREDIT"])
        account_layout.addRow("账户类型:", self.account_type_combo)

        # 添加测试模式选项
        self.test_mode_check = QCheckBox("测试模式（不保存日志）")
        self.test_mode_check.setChecked(True)  # 默认测试模式
        self.test_mode_check.setToolTip(
            "勾选：测试模式，不保存交易日志\n"
            "不勾选：实盘模式，保存交易日志并执行实际交易"
        )
        account_layout.addRow("", self.test_mode_check)

        layout.addWidget(account_group)
        layout.addStretch()

        return panel

    def create_params_panel(self) -> QWidget:
        """创建参数配置面板"""
        group = QGroupBox("策略参数配置")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)

        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)  # 无边框更美观

        # 参数容器
        params_container = QWidget()
        self.params_layout = QVBoxLayout(params_container)
        self.params_layout.setSpacing(15)
        self.params_layout.setContentsMargins(10, 10, 10, 10)

        # 创建参数UI
        self.create_params_ui()

        scroll.setWidget(params_container)
        layout.addWidget(scroll)

        return group

    def create_params_ui(self):
        """创建参数配置UI"""
        # 清空现有布局
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 股票池配置
        stock_group = QGroupBox("股票池配置")
        stock_layout = QFormLayout(stock_group)
        stock_layout.setSpacing(10)
        stock_layout.setContentsMargins(15, 15, 15, 15)
        stock_layout.setHorizontalSpacing(15)
        stock_layout.setVerticalSpacing(10)

        self.stock_pool_edit = QLineEdit("511090.SH, 511130.SH")
        self.stock_pool_edit.setPlaceholderText("用逗号分隔多个股票代码")
        stock_layout.addRow("股票池:", self.stock_pool_edit)

        self.params_layout.addWidget(stock_group)

        # 根据选择的策略创建参数
        strategy = self.strategy_combo.currentText()

        if "固定网格" in strategy:
            self.create_fixed_grid_params()
        elif "自适应" in strategy:
            self.create_adaptive_grid_params()
        elif "ATR" in strategy:
            self.create_atr_grid_params()

        self.params_layout.addStretch()

    def create_fixed_grid_params(self):
        """创建固定网格参数"""
        params_group = QGroupBox("固定网格参数")
        params_layout = QFormLayout(params_group)
        params_layout.setSpacing(10)
        params_layout.setContentsMargins(15, 15, 15, 15)
        params_layout.setHorizontalSpacing(15)
        params_layout.setVerticalSpacing(10)

        self.base_price_spin = QDoubleSpinBox()
        self.base_price_spin.setRange(0, 9999)
        self.base_price_spin.setValue(0)
        self.base_price_spin.setSuffix(" (0=自动)")
        params_layout.addRow("基准价格:", self.base_price_spin)

        self.grid_count_spin = QSpinBox()
        self.grid_count_spin.setRange(1, 20)
        self.grid_count_spin.setValue(5)
        params_layout.addRow("网格层数:", self.grid_count_spin)

        self.grid_spacing_spin = QDoubleSpinBox()
        self.grid_spacing_spin.setRange(0.001, 1.0)
        self.grid_spacing_spin.setValue(0.01)
        self.grid_spacing_spin.setSingleStep(0.01)
        self.grid_spacing_spin.setDecimals(3)
        params_layout.addRow("网格间距(%):", self.grid_spacing_spin)

        self.grid_quantity_spin = QSpinBox()
        self.grid_quantity_spin.setRange(100, 10000)
        self.grid_quantity_spin.setValue(100)
        self.grid_quantity_spin.setSingleStep(100)
        params_layout.addRow("单网格数量:", self.grid_quantity_spin)

        self.max_position_spin = QSpinBox()
        self.max_position_spin.setRange(100, 100000)
        self.max_position_spin.setValue(1000)
        params_layout.addRow("最大持仓:", self.max_position_spin)

        self.params_layout.addWidget(params_group)

    def create_adaptive_grid_params(self):
        """创建自适应网格参数"""
        params_group = QGroupBox("自适应网格参数")
        params_layout = QFormLayout(params_group)
        params_layout.setSpacing(10)
        params_layout.setContentsMargins(15, 15, 15, 15)
        params_layout.setHorizontalSpacing(15)
        params_layout.setVerticalSpacing(10)

        self.buy_threshold_spin = QDoubleSpinBox()
        self.buy_threshold_spin.setRange(-5.0, 0)
        self.buy_threshold_spin.setValue(-0.05)
        self.buy_threshold_spin.setSingleStep(0.01)
        self.buy_threshold_spin.setDecimals(3)
        params_layout.addRow("买入阈值(%):", self.buy_threshold_spin)

        self.sell_threshold_spin = QDoubleSpinBox()
        self.sell_threshold_spin.setRange(0, 5.0)
        self.sell_threshold_spin.setValue(0.05)
        self.sell_threshold_spin.setSingleStep(0.01)
        self.sell_threshold_spin.setDecimals(3)
        params_layout.addRow("卖出阈值(%):", self.sell_threshold_spin)

        self.trade_quantity_spin = QSpinBox()
        self.trade_quantity_spin.setRange(100, 10000)
        self.trade_quantity_spin.setValue(100)
        self.trade_quantity_spin.setSingleStep(100)
        params_layout.addRow("单次交易数量:", self.trade_quantity_spin)

        self.max_position_spin2 = QSpinBox()
        self.max_position_spin2.setRange(100, 100000)
        self.max_position_spin2.setValue(500)
        params_layout.addRow("最大持仓:", self.max_position_spin2)

        self.params_layout.addWidget(params_group)

    def create_atr_grid_params(self):
        """创建ATR动态网格参数"""
        params_group = QGroupBox("ATR动态网格参数")
        params_layout = QFormLayout(params_group)
        params_layout.setSpacing(10)
        params_layout.setContentsMargins(15, 15, 15, 15)
        params_layout.setHorizontalSpacing(15)
        params_layout.setVerticalSpacing(10)

        self.atr_period_spin = QSpinBox()
        self.atr_period_spin.setRange(5, 50)
        self.atr_period_spin.setValue(14)
        params_layout.addRow("ATR周期:", self.atr_period_spin)

        self.atr_multiplier_spin = QDoubleSpinBox()
        self.atr_multiplier_spin.setRange(0.1, 5.0)
        self.atr_multiplier_spin.setValue(0.5)
        self.atr_multiplier_spin.setSingleStep(0.1)
        params_layout.addRow("ATR倍数:", self.atr_multiplier_spin)

        self.min_grid_spacing_spin = QDoubleSpinBox()
        self.min_grid_spacing_spin.setRange(0.05, 2.0)
        self.min_grid_spacing_spin.setValue(0.5)
        params_layout.addRow("最小间距(%):", self.min_grid_spacing_spin)

        self.max_grid_spacing_spin = QDoubleSpinBox()
        self.max_grid_spacing_spin.setRange(0.1, 5.0)
        self.max_grid_spacing_spin.setValue(0.8)
        params_layout.addRow("最大间距(%):", self.max_grid_spacing_spin)

        self.grid_layers_spin = QSpinBox()
        self.grid_layers_spin.setRange(1, 20)
        self.grid_layers_spin.setValue(5)
        params_layout.addRow("网格层数:", self.grid_layers_spin)

        self.trade_quantity_spin3 = QSpinBox()
        self.trade_quantity_spin3.setRange(100, 10000)
        self.trade_quantity_spin3.setValue(100)
        params_layout.addRow("单次数量:", self.trade_quantity_spin3)

        self.max_position_spin3 = QSpinBox()
        self.max_position_spin3.setRange(100, 100000)
        self.max_position_spin3.setValue(500)
        params_layout.addRow("最大持仓:", self.max_position_spin3)

        self.ma_period_spin = QSpinBox()
        self.ma_period_spin.setRange(5, 60)
        self.ma_period_spin.setValue(20)
        params_layout.addRow("均线周期:", self.ma_period_spin)

        self.params_layout.addWidget(params_group)

    def create_monitor_panel(self) -> QWidget:
        """创建监控面板"""
        # 使用分割器，上半部分表格，下半部分日志和控制
        splitter = QSplitter(Qt.Vertical)

        # 上半部分：标签页（监控和交易记录）
        tab_widget = QTabWidget()

        # 标签页1：实时监控
        monitor_tab = QWidget()
        monitor_layout = QVBoxLayout(monitor_tab)
        monitor_layout.setContentsMargins(5, 5, 5, 5)

        self.status_table = QTableWidget(0, 6)
        self.status_table.setHorizontalHeaderLabels([
            "股票代码", "当前价格", "基准价格", "持仓数量", "最新信号", "状态"
        ])
        self.status_table.horizontalHeader().setStretchLastSection(True)
        self.status_table.setAlternatingRowColors(True)
        self.status_table.setMinimumHeight(120)
        monitor_layout.addWidget(self.status_table)

        tab_widget.addTab(monitor_tab, "实时监控")

        # 标签页2：交易记录
        trade_tab = QWidget()
        trade_layout = QVBoxLayout(trade_tab)
        trade_layout.setContentsMargins(5, 5, 5, 5)

        self.trade_table = QTableWidget(0, 5)
        self.trade_table.setHorizontalHeaderLabels([
            "时间", "股票代码", "类型", "数量", "价格"
        ])
        self.trade_table.horizontalHeader().setStretchLastSection(True)
        self.trade_table.setAlternatingRowColors(True)
        self.trade_table.setMinimumHeight(120)
        trade_layout.addWidget(self.trade_table)

        tab_widget.addTab(trade_tab, "交易记录")

        splitter.addWidget(tab_widget)

        # 下半部分：控制和日志
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setSpacing(10)

        # 控制按钮
        control_layout = QHBoxLayout()

        self.start_btn = QPushButton("▶ 启动策略")
        self.start_btn.setFixedSize(110, 36)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #00aa00;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #00cc00;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.start_btn.clicked.connect(self.start_strategy)

        self.stop_btn = QPushButton("⏸ 停止策略")
        self.stop_btn.setFixedSize(110, 36)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6600;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #ff8833;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_strategy)

        self.clear_log_btn = QPushButton("🗑 清除日志")
        self.clear_log_btn.setFixedSize(110, 36)
        self.clear_log_btn.clicked.connect(self.clear_log)

        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.clear_log_btn)
        control_layout.addStretch()

        bottom_layout.addLayout(control_layout)

        # 日志输出
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(8, 8, 8, 8)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.log_text.setContextMenuPolicy(Qt.CustomContextMenu)
        self.log_text.customContextMenuRequested.connect(self._show_log_context_menu)
        self.log_text.setMinimumHeight(150)  # 从80增加到150
        self.log_text.setMaximumHeight(250)  # 从150增加到250
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

        bottom_layout.addWidget(log_group)
        splitter.addWidget(bottom_widget)

        # 设置分割比例（表格占50%，控制和日志占50%）
        splitter.setSizes([200, 250])  # 从[200, 150]增加到[200, 250]

        return splitter

    def setup_timer(self):
        """设置定时器"""
        # 数据更新定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_monitor_data)
        self.update_timer.start(3000)  # 每3秒更新一次

    def on_strategy_changed(self, index):
        """策略选择改变事件"""
        # 重新创建参数UI
        self.create_params_ui()
        # 更新配置文件路径
        self.update_config_file_path()

    def update_config_file_path(self):
        """更新配置文件路径"""
        strategy = self.strategy_combo.currentText()

        if "固定网格" in strategy:
            config_name = "fixed_grid_config.json"
        elif "自适应" in strategy:
            config_name = "adaptive_grid_config.json"
        elif "ATR" in strategy:
            config_name = "atr_grid_config.json"
        else:
            config_name = "grid_config.json"

        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            '..', 'strategies', 'grid_trading',
            config_name
        )
        self.config_file_edit.setText(config_path)

    def _disable_spinbox_wheel(self):
        """禁止所有 QSpinBox/QDoubleSpinBox 滚轮调整参数"""
        self._wheel_filter = _NoWheelFilter(self)
        for spin in self.findChildren(QSpinBox) + self.findChildren(QDoubleSpinBox):
            spin.installEventFilter(self._wheel_filter)
            spin.setFocusPolicy(Qt.StrongFocus)

    def _auto_load_default_config(self):
        """启动时自动加载默认配置文件"""
        default_config = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'strategies', 'grid_trading', 'atr_grid_config.json'
        )
        if os.path.exists(default_config):
            try:
                with open(default_config, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.apply_config(config)
                self.config_file = default_config
            except Exception:
                pass  # 静默失败，使用界面默认值

    def save_config(self):
        """保存当前参数到配置文件"""
        config_file = getattr(self, 'config_file', '') or ''
        if not config_file:
            QMessageBox.warning(self, "保存失败", "未找到配置文件路径")
            return

        try:
            # 读取现有配置（保留未在GUI显示的字段）
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}

            # 更新股票池
            pool_text = self.stock_pool_edit.text().strip()
            config['股票池'] = [s.strip() for s in pool_text.replace('，', ',').split(',') if s.strip()]

            # 更新账户类型
            config['账户类型'] = self.account_type_combo.currentText()

            # 更新策略参数
            strategy = self.strategy_combo.currentText()
            if 'ATR' in strategy:
                if hasattr(self, 'atr_period_spin'):
                    config['ATR周期'] = self.atr_period_spin.value()
                if hasattr(self, 'atr_multiplier_spin'):
                    config['ATR倍数'] = self.atr_multiplier_spin.value()
                if hasattr(self, 'min_grid_spacing_spin'):
                    config['最小网格间距'] = self.min_grid_spacing_spin.value()
                if hasattr(self, 'max_grid_spacing_spin'):
                    config['最大网格间距'] = self.max_grid_spacing_spin.value()
                if hasattr(self, 'grid_layers_spin'):
                    config['网格层数'] = self.grid_layers_spin.value()
                if hasattr(self, 'trade_quantity_spin3'):
                    config['单次交易数量'] = self.trade_quantity_spin3.value()
                if hasattr(self, 'max_position_spin3'):
                    config['最大持仓数量'] = self.max_position_spin3.value()
                if hasattr(self, 'ma_period_spin'):
                    config['均线周期'] = self.ma_period_spin.value()

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            self.log(f"配置已保存: {os.path.basename(config_file)}")
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"无法保存配置文件:\n{str(e)}")

    def apply_config(self, config: dict):
        """应用配置到界面"""
        # 账户ID和QMT路径已从 .env 自动加载，不再从配置文件读取
        self.account_type_combo.setCurrentText(config.get('账户类型', 'STOCK'))

        # 设置股票池
        stock_pool = config.get('股票池', [])
        self.stock_pool_edit.setText(', '.join(stock_pool))

        # 根据配置类型设置参数
        strategy = self.strategy_combo.currentText()

        if 'ATR周期' in config:
            if hasattr(self, 'atr_period_spin'):
                self.atr_period_spin.setValue(config.get('ATR周期', 14))
            if hasattr(self, 'atr_multiplier_spin'):
                self.atr_multiplier_spin.setValue(config.get('ATR倍数', 0.5))
            if hasattr(self, 'min_grid_spacing_spin'):
                self.min_grid_spacing_spin.setValue(config.get('最小网格间距', 0.5))
            if hasattr(self, 'max_grid_spacing_spin'):
                self.max_grid_spacing_spin.setValue(config.get('最大网格间距', 0.8))
            if hasattr(self, 'grid_layers_spin'):
                self.grid_layers_spin.setValue(config.get('网格层数', 5))
            if hasattr(self, 'trade_quantity_spin3'):
                self.trade_quantity_spin3.setValue(config.get('单次交易数量', 100))
            if hasattr(self, 'max_position_spin3'):
                self.max_position_spin3.setValue(config.get('最大持仓数量', 500))
            if hasattr(self, 'ma_period_spin'):
                self.ma_period_spin.setValue(config.get('均线周期', 20))

    def get_config(self) -> dict:
        """获取当前配置"""
        config = {
            '账户ID': _read_env('QMT_ACCOUNT_ID'),
            '账户类型': self.account_type_combo.currentText(),
            'QMT路径': _read_env('QMT_DATA_DIR'),
            '股票池': [s.strip() for s in self.stock_pool_edit.text().split(',')],
            '价格模式': 5,  # 最新价
            '交易时间段': 8,  # 工作日
            '交易开始时间': 9,
            '交易结束时间': 24,
            '是否参加集合竞价': False,
            '是否测试': self.test_mode_check.isChecked(),  # 根据复选框状态
        }

        strategy = self.strategy_combo.currentText()

        if "固定网格" in strategy:
            config.update({
                '基准价格': self.base_price_spin.value(),
                '网格数量': self.grid_count_spin.value(),
                '网格间距': self.grid_spacing_spin.value(),
                '单网格数量': self.grid_quantity_spin.value(),
                '最大持仓': self.max_position_spin.value(),
                '启用动态调整': True,
            })
        elif "自适应" in strategy:
            config.update({
                '买入涨跌幅': self.buy_threshold_spin.value(),
                '卖出涨跌幅': self.sell_threshold_spin.value(),
                '单次交易数量': self.trade_quantity_spin.value(),
                '最大持仓数量': self.max_position_spin2.value(),
            })
        elif "ATR" in strategy:
            config.update({
                'ATR周期': self.atr_period_spin.value(),
                'ATR倍数': self.atr_multiplier_spin.value(),
                '最小网格间距': self.min_grid_spacing_spin.value(),
                '最大网格间距': self.max_grid_spacing_spin.value(),
                '网格层数': self.grid_layers_spin.value(),
                '单次交易数量': self.trade_quantity_spin3.value(),
                '最大持仓数量': self.max_position_spin3.value(),
                '均线周期': self.ma_period_spin.value(),
                '趋势阈值': 0.3,
            })

        return config

    def start_strategy(self):
        """启动策略"""
        if self.is_running:
            self.log("策略已在运行中")
            return

        try:
            # 获取配置
            config = self.get_config()

            # 根据策略类型导入相应的策略类
            strategy = self.strategy_combo.currentText()

            self.log("=" * 60)
            self.log(f"正在启动策略: {strategy}")
            self.log("=" * 60)

            if "固定网格" in strategy:
                from strategies.grid_trading.固定网格_优化版 import 固定网格策略优化版
                self.strategy = 固定网格策略优化版(config)
                self.log("✓ 策略对象创建成功: 固定网格策略优化版")
            elif "自适应" in strategy:
                from strategies.grid_trading.自适应网格策略 import 自适应网格策略
                self.strategy = 自适应网格策略(config)
                self.log("✓ 策略对象创建成功: 自适应网格策略")
            elif "ATR" in strategy:
                # 先检查ATR策略的类名
                import strategies.grid_trading.ATR动态网格策略 as atr_module
                atr_class_name = None
                for name in dir(atr_module):
                    obj = getattr(atr_module, name)
                    if isinstance(obj, type) and 'ATR' in name and '策略' in name:
                        atr_class_name = name
                        break

                if atr_class_name:
                    atr_class = getattr(atr_module, atr_class_name)
                    self.strategy = atr_class(config)
                    self.log(f"✓ 策略对象创建成功: {atr_class_name}")
                else:
                    raise ImportError(f"未找到ATR策略类")
            else:
                raise ValueError(f"未知的策略类型: {strategy}")

            # 在新线程中运行策略
            self.strategy_thread = StrategyThread(self.strategy)
            self.strategy_thread.log_signal.connect(self.log)
            self.strategy_thread.finished_signal.connect(self.on_strategy_finished)

            self.is_running = True
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)

            self.log(f"✓ 股票池: {config['股票池']}")
            self.log(f"✓ 账户ID: {config['账户ID']}")
            self.log(f"✓ 测试模式: {'是' if config.get('是否测试') else '否'}")
            self.log("→ 正在启动策略线程...")

            # 启动线程
            self.strategy_thread.start()

            QMessageBox.information(self, "启动成功",
                f"策略已启动！\n\n"
                f"策略类型: {strategy}\n"
                f"股票池: {config['股票池']}\n"
                f"测试模式: {'是' if config.get('是否测试') else '否'}\n\n"
                f"策略将在后台运行，详细日志请查看下方日志区域。"
            )

        except Exception as e:
            self.is_running = False
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.log(f"❌ 启动失败: {str(e)}")
            QMessageBox.critical(self, "启动失败", f"无法启动策略:\n{str(e)}")
            import traceback
            traceback.print_exc()

    def stop_strategy(self):
        """停止策略"""
        if not self.is_running:
            self.log("策略未在运行")
            return

        self.log("=" * 60)
        self.log("正在停止策略...")
        self.log("=" * 60)

        # 停止策略线程
        if self.strategy_thread and self.strategy_thread.isRunning():
            self.strategy_thread.stop()
            self.log("✓ 策略线程已停止")

        self.is_running = False
        self.strategy = None
        self.strategy_thread = None
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        self.log("✓ 策略已完全停止")

        QMessageBox.information(self, "停止成功", "策略已停止")

    def on_strategy_finished(self):
        """策略执行完成的回调"""
        self.log("⚠ 策略线程已退出")
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def update_monitor_data(self):
        """更新监控数据"""
        if not self.is_running or not self.strategy:
            return

        try:
            # 尝试从策略对象获取状态信息
            if hasattr(self.strategy, 'get_status'):
                status = self.strategy.get_status()
                # 更新状态表格
                # 这里可以根据策略返回的状态更新UI
        except Exception as e:
            # 不显示错误，避免日志刷屏
            pass

    def _show_log_context_menu(self, pos):
        """日志区域右键菜单 - 支持复制"""
        menu = QMenu(self.log_text)
        copy_action = menu.addAction("复制选中")
        copy_action.triggered.connect(self.log_text.copy)
        copy_all_action = menu.addAction("复制全部")
        copy_all_action.triggered.connect(lambda: self._copy_all_log())
        menu.addSeparator()
        clear_action = menu.addAction("清空日志")
        clear_action.triggered.connect(self.clear_log)
        menu.exec_(self.log_text.mapToGlobal(pos))

    def _copy_all_log(self):
        """复制全部日志到剪贴板"""
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(self.log_text.toPlainText())

    def clear_log(self):
        """清除日志"""
        self.log_text.clear()
        self.trade_table.setRowCount(0)

    def log(self, message: str):
        """输出日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        self.log_text.append(log_message)
        self.log_text.moveCursor(QTextCursor.End)


# 导出类
__all__ = ['GridTradingWidget']
