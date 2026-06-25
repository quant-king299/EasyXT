# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger(__name__)
#!/usr/bin/env python3
"""
多策略管理 GUI 组件
==================

可视化多策略调度管理，支持：
  - 策略列表展示（名称/状态/模式/PID）
  - 单策略启动/停止
  - 一键全部启动/停止
  - 模拟/实盘模式切换
  - 一次性/持续运行模式切换
  - 实时日志输出
  - 自动状态刷新
"""

import os
import sys
import json
import time
import signal
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QPlainTextEdit, QCheckBox, QRadioButton, QButtonGroup,
    QMessageBox, QSplitter, QFrame, QComboBox, QSpinBox,
    QLineEdit, QFormLayout, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QProcess, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QColor, QBrush

# 项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
SCHEDULER_DIR = PROJECT_ROOT / "strategies" / "scheduler"
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# 策略进程管理（纯 subprocess，无线程问题）
# ---------------------------------------------------------------------------

class StdoutReader(QThread):
    """后台读取子进程 stdout，通过信号发射到 GUI"""
    line_signal = pyqtSignal(str)

    def __init__(self, name: str, proc: subprocess.Popen):
        super().__init__()
        self.name = name
        self.proc = proc
        self._stop = False

    def run(self):
        try:
            while not self._stop and self.proc.poll() is None:
                line = self.proc.stdout.readline()
                if line:
                    self.line_signal.emit(f"[{self.name}] {line.rstrip()}")
                else:
                    break  # EOF
        except Exception:
            pass

    def quit_reader(self):
        self._stop = True
        self.wait(2000)  # 最多等 2 秒
        if self.isRunning():
            self.terminate()


class ProcessManager:
    """进程管理器——通过 PID 文件 + subprocess 管理策略进程"""

    def __init__(self):
        self.log_dir = SCHEDULER_DIR / "logs"
        self.log_dir.mkdir(exist_ok=True)
        self._processes: Dict[str, subprocess.Popen] = {}  # 保存进程引用

    def pid_file(self, name: str) -> Path:
        return self.log_dir / f"{name}.pid"

    def write_pid_file(self, name: str, pid: int, run_mode: str, schedule_type: str):
        try:
            self.pid_file(name).write_text(
                json.dumps({
                    "pid": pid,
                    "run_mode": run_mode,
                    "schedule_type": schedule_type,
                    "start_time": datetime.now().isoformat(),
                }, ensure_ascii=False)
            )
        except Exception:
            pass

    def read_pid_file(self, name: str) -> Optional[Dict]:
        pf = self.pid_file(name)
        if not pf.exists():
            return None
        try:
            data = json.loads(pf.read_text())
            pid = data.get("pid")
            if pid:
                # Windows: 用 ctypes 检测进程存活
                try:
                    import ctypes
                    handle = ctypes.windll.kernel32.OpenProcess(0x0400, False, pid)
                    if handle:
                        ctypes.windll.kernel32.CloseHandle(handle)
                        return data
                except Exception:
                    pass
                # 跨平台 fallback
                try:
                    os.kill(pid, 0)
                    return data
                except OSError:
                    pass
            pf.unlink(missing_ok=True)
            return None
        except Exception:
            return None

    def remove_pid_file(self, name: str):
        try:
            self.pid_file(name).unlink(missing_ok=True)
        except Exception:
            pass

    def is_running(self, name: str) -> Optional[Dict]:
        return self.read_pid_file(name)

    def start(self, name: str, run_mode: str, continuous: bool,
              schedule_type: str = "daily", daily_time: str = "09:35",
              interval_minutes: int = 60) -> Optional[subprocess.Popen]:
        """启动策略，返回 subprocess.Popen 或 None"""
        if continuous:
            return self._start_scheduler(name, run_mode, schedule_type,
                                         daily_time, interval_minutes)
        else:
            return self._start_one_shot(name, run_mode)

    def _start_scheduler(self, name: str, run_mode: str, schedule_type: str,
                         daily_time: str, interval_minutes: int) -> Optional[subprocess.Popen]:
        """启动持续运行调度器，返回进程对象"""
        script = str(SCHEDULER_DIR / "strategy_scheduler.py")
        cmd = [
            sys.executable, script,
            "--strategy", name,
            "--mode", run_mode,
            "--schedule", schedule_type,
        ]
        if schedule_type == "daily":
            cmd += ["--daily-time", daily_time]
        else:
            cmd += ["--interval", str(interval_minutes)]

        try:
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                if sys.platform == "win32" else 0,
            )
            self._processes[name] = proc
            self.write_pid_file(name, proc.pid, run_mode, schedule_type)
            return proc
        except Exception as e:
            logger.info(f"启动调度器失败 ({name}): {e}")
            return None

    def _start_coordinator(self, names: list, run_mode: str,
                          schedule_type: str = "daily") -> Optional[subprocess.Popen]:
        """单进程协调器，多策略订单去重"""
        script = str(PROJECT_ROOT / "strategies" / "strategy_coordinator.py")
        cmd = [sys.executable, script, "--strategies"] + names + ["--mode", run_mode, "--schedule", schedule_type]
        if schedule_type == "daily":
            cmd += ["--daily-time", "09:35"]
        try:
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                if sys.platform == "win32" else 0,
            )
            main_name = "_".join(sorted(names))
            self._processes[main_name] = proc
            self.write_pid_file(main_name, proc.pid, run_mode, "coordinated")
            return proc
        except Exception as e:
            logger.info(f"启动协调器失败: {e}")
            return None


    def _start_one_shot(self, name: str, run_mode: str) -> Optional[subprocess.Popen]:
        """启动一次性执行，返回进程对象"""
        strategy_dir = PROJECT_ROOT / "strategies" / "quant_strategies"
        script = strategy_dir / f"run_{name}.py"

        if not script.exists():
            logger.info(f"策略脚本不存在: {script}")
            return None

        cmd = [sys.executable, str(script)]
        if run_mode == "live":
            cmd.append("--trade")

        try:
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                env=env,
                cwd=str(strategy_dir),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                if sys.platform == "win32" else 0,
            )
            self._processes[name] = proc
            self.write_pid_file(name, proc.pid, run_mode, "once")
            return proc
        except Exception as e:
            logger.info(f"启动策略失败 ({name}): {e}")
            return None

    def stop(self, name: str) -> bool:
        """停止策略（通过 PID 文件）"""
        # 先尝试通过进程句柄终止
        proc = self._processes.pop(name, None)
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        # 兜底：通过 PID 文件杀进程
        data = self.read_pid_file(name)
        if data:
            pid = data["pid"]
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
        self.remove_pid_file(name)
        return True

    def stop_all_running(self) -> int:
        """停止所有运行中的策略，返回停止数量"""
        count = 0
        # 1. 先停止有进程句柄的（GUI 启动的）
        for name in list(self._processes.keys()):
            if self.stop(name):
                count += 1
        # 2. 再扫 PID 文件（CLI 或其他来源启动的）
        for pf in self.log_dir.glob("*.pid"):
            name = pf.stem
            if self.stop(name):
                count += 1
        return count


# 策略默认配置（名称 → (中文名, 优先级, 调度类型, 调度参数)）
STRATEGY_INFO = {
    "limit_up":           ("涨停板策略", 8, "interval", "5"),
    "etf_trend":          ("ETF趋势轮动", 7, "daily", "09:35"),
    "etf_hot_theme":      ("ETF热门主题", 7, "daily", "09:40"),
    "dividend_lowvol":    ("红利低波",    6, "daily", "09:50"),
    "cb_double_low":      ("可转债双低",  5, "daily", "09:35"),
    "cb_three_low":       ("可转债三低",  5, "daily", "09:40"),
    "cb_factor_rotation": ("可转债因子",  5, "daily", "09:45"),
}

# 用户自定义覆盖（来自表格编辑），name → {"schedule_type": ..., "schedule_value": ...}
_strategy_overrides: Dict[str, dict] = {}

def get_strategy_schedule(name: str):
    """获取策略的调度配置（默认+用户覆盖）"""
    override = _strategy_overrides.get(name, {})
    default = STRATEGY_INFO[name]
    return (
        override.get("schedule_type", default[2]),
        override.get("schedule_value", default[3]),
    )


# ---------------------------------------------------------------------------
# GUI 组件
# ---------------------------------------------------------------------------

class MultiStrategyWidget(QWidget):
    """多策略管理 GUI 组件"""

    log_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pm = ProcessManager()
        self._readers: list = []  # 跟踪后台日志读取线程
        self.init_ui()

        # 定时刷新状态
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_status)
        self.refresh_timer.start(5000)  # 每5秒刷新

        # 初始刷新
        self.refresh_status()

    # ---- UI 构建 ----

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ===== 顶部：模式选择 =====
        top_layout = QHBoxLayout()

        # 运行模式
        mode_group = QGroupBox("运行模式")
        mode_hbox = QHBoxLayout(mode_group)
        self.rb_dry_run = QRadioButton("模拟")
        self.rb_live = QRadioButton("实盘")
        self.rb_dry_run.setChecked(True)
        self.rb_dry_run.setToolTip("生成交易信号但不下单")
        self.rb_live.setToolTip("真实下单交易（请谨慎使用）")
        mode_hbox.addWidget(self.rb_dry_run)
        mode_hbox.addWidget(self.rb_live)

        # 调度模式
        sched_group = QGroupBox("调度模式")
        sched_hbox = QHBoxLayout(sched_group)
        self.cb_continuous = QCheckBox("持续运行")
        self.cb_continuous.setChecked(True)
        self.cb_continuous.setToolTip("勾选=持续运行（while True 循环）\n取消=一次性执行")
        sched_hbox.addWidget(self.cb_continuous)
        sched_hbox.addStretch()

        top_layout.addWidget(mode_group)
        top_layout.addWidget(sched_group)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        # ===== 中间：策略列表 =====
        table_group = QGroupBox("策略列表")
        table_layout = QVBoxLayout(table_group)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["策略名称", "中文名", "状态", "调度类型", "调度参数", "PID", "操作"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 130)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 75)
        self.table.setColumnWidth(4, 70)
        self.table.setColumnWidth(5, 60)
        self.table.setColumnWidth(6, 60)
        self.table.setColumnWidth(7, 170)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        # 填充策略行（仅显示本地已安装的策略）
        available = []
        for name in STRATEGY_INFO:
            script = PROJECT_ROOT / "strategies" / "quant_strategies" / f"run_{name}.py"
            if script.exists():
                available.append(name)
        sorted_names = sorted(available,
                              key=lambda n: STRATEGY_INFO[n][1], reverse=True)
        self.table.setRowCount(len(sorted_names))
        self._strategy_rows = {}  # name → row index
        for i, name in enumerate(sorted_names):
            self._strategy_rows[name] = i
            info = STRATEGY_INFO[name]
            sched_type, sched_val = get_strategy_schedule(name)

            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem(info[0]))
            self.table.setItem(i, 2, QTableWidgetItem("—"))  # 状态
            # 每策略独立调度类型（可双击切换）
            self.table.setItem(i, 3, QTableWidgetItem(sched_type))
            self.table.item(i, 3).setToolTip("双击切换 daily / interval")
            # 每策略独立调度参数（可双击编辑）
            self.table.setItem(i, 4, QTableWidgetItem(str(sched_val)))
            self.table.item(i, 4).setToolTip(
                "daily: HH:MM (如 09:35)\ninterval: 分钟数 (如 5)\n双击编辑"
            )
            self.table.setItem(i, 5, QTableWidgetItem("—"))  # PID
            # 操作按钮
            btn_start = QPushButton("▶ 启动")
            btn_start.setFixedWidth(75)
            btn_start.clicked.connect(lambda checked, n=name: self.start_strategy(n))
            btn_stop = QPushButton("⏹ 停止")
            btn_stop.setFixedWidth(75)
            btn_stop.clicked.connect(lambda checked, n=name: self.stop_strategy(n))
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(4)
            btn_layout.addWidget(btn_start)
            btn_layout.addWidget(btn_stop)
            self.table.setCellWidget(i, 7, btn_widget)
            # 保存按钮引用
            self.table.item(i, 0).setData(Qt.UserRole, (btn_start, btn_stop))

        # 表格双击编辑（调度类型和参数）
        self.table.cellChanged.connect(self._on_cell_changed)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self._editing_cell = None  # 防递归

        table_layout.addWidget(self.table)

        # 批量操作按钮
        batch_layout = QHBoxLayout()
        self.btn_start_all = QPushButton("▶ 全部启动")
        self.btn_start_all.clicked.connect(self.start_all)
        self.btn_stop_all = QPushButton("⏹ 全部停止")
        self.btn_stop_all.clicked.connect(self.stop_all)
        self.btn_refresh = QPushButton("🔄 刷新状态")
        self.btn_refresh.clicked.connect(self.refresh_status)
        self.btn_report = QPushButton("📊 查看报告")
        self.btn_report.clicked.connect(self.show_report)

        batch_layout.addWidget(self.btn_start_all)
        batch_layout.addWidget(self.btn_stop_all)
        batch_layout.addWidget(self.btn_refresh)
        batch_layout.addWidget(self.btn_report)
        batch_layout.addStretch()
        table_layout.addLayout(batch_layout)

        layout.addWidget(table_group)

        # ===== 底部：日志输出 =====
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumBlockCount(500)
        self.log_output.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_output)

        # 日志过滤栏
        filter_layout = QHBoxLayout()
        self.cb_verbose = QCheckBox("显示详细日志（数据获取过程）")
        self.cb_verbose.setChecked(False)
        self.cb_verbose.setToolTip("勾选=显示所有日志\n取消=只显示买卖信号/错误/关键信息")
        filter_layout.addWidget(self.cb_verbose)
        filter_layout.addStretch()
        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.setFixedWidth(80)
        clear_log_btn.clicked.connect(self.log_output.clear)
        filter_layout.addWidget(clear_log_btn)
        log_layout.addLayout(filter_layout)

        layout.addWidget(log_group)

    # ---- 表格编辑 ----

    def _on_cell_double_clicked(self, row: int, col: int):
        """双击单元格切换调度类型（col=3）"""
        if col != 3:
            return
        name = self.table.item(row, 0).text()
        current = self.table.item(row, 3).text()
        new_type = "interval" if current == "daily" else "daily"
        new_val = "60" if new_type == "interval" else "09:35"

        self._editing_cell = (row, col)
        self.table.item(row, 3).setText(new_type)
        self._editing_cell = (row, 4)
        self.table.item(row, 4).setText(new_val)
        self._editing_cell = None

        _strategy_overrides[name] = {"schedule_type": new_type, "schedule_value": new_val}
        self._log(f"⚙️ {name}: {new_type} {new_val}")

    def _on_cell_changed(self, row: int, col: int):
        """手动编辑调度参数值（col=4）后保存"""
        if self._editing_cell and self._editing_cell[0] == row:
            return
        if col != 4:
            return
        name = self.table.item(row, 0).text()
        sched_type = self.table.item(row, 3).text()
        sched_val = self.table.item(row, 4).text().strip()
        _strategy_overrides[name] = {"schedule_type": sched_type, "schedule_value": sched_val}
        self._log(f"⚙️ {name}: {sched_type} {sched_val}")

    # ---- 日志（含过滤） ----

    # 重要日志关键词（默认过滤模式下显示）
    _IMPORTANT_KEYWORDS = [
        "ERROR", "WARN", "买入", "卖出", "信号", "交易", "下单",
        "委托", "成交", "触发", "止损", "止盈", "调仓", "轮动",
        "=====", "启动", "完成", "停止", "失败",
    ]

    def _should_show(self, msg: str) -> bool:
        """判断日志是否应该显示"""
        if self.cb_verbose.isChecked():
            return True
        for kw in self._IMPORTANT_KEYWORDS:
            if kw in msg:
                return True
        return False

    def _log(self, msg: str):
        if not self._should_show(msg):
            return
        ts = datetime.now().strftime('%H:%M:%S')
        self.log_output.appendPlainText(f"[{ts}] {msg}")
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # ---- 状态刷新 ----

    def refresh_status(self):
        """刷新策略状态表格"""
        for name, row in self._strategy_rows.items():
            data = self.pm.is_running(name)
            if data:
                self.table.item(row, 2).setText("● 运行中")
                self.table.item(row, 2).setForeground(QBrush(QColor("#00aa00")))
                self.table.item(row, 5).setText(str(data["pid"]))
                btns = self.table.item(row, 0).data(Qt.UserRole)
                if btns:
                    btns[0].setEnabled(False)
                    btns[1].setEnabled(True)
            else:
                self.table.item(row, 2).setText("○ 已停止")
                self.table.item(row, 2).setForeground(QBrush(QColor("#999999")))
                self.table.item(row, 5).setText("—")
                btns = self.table.item(row, 0).data(Qt.UserRole)
                if btns:
                    btns[0].setEnabled(True)
                    btns[1].setEnabled(False)

    # ---- 策略操作 ----

    def start_strategy(self, name: str):
        """启动单个策略"""
        run_mode = "live" if self.rb_live.isChecked() else "dry_run"
        continuous = self.cb_continuous.isChecked()

        if run_mode == "live" and continuous:
            reply = QMessageBox.question(
                self, "确认实盘",
                f"即将以【实盘+持续运行】模式启动 {name}，\n"
                f"策略将真实下单！确认继续？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        # 使用每策略独立的调度参数
        schedule_type, schedule_value = get_strategy_schedule(name)

        if schedule_type == "daily":
            daily_time = schedule_value
            interval = 60
        else:
            daily_time = "09:35"
            try:
                interval = int(schedule_value)
            except ValueError:
                interval = 60

        # 检查是否已在运行
        existing = self.pm.is_running(name)
        if existing:
            info = STRATEGY_INFO[name]
            self._log(f"⚠️ {info[0]} 已在运行 (PID={existing['pid']})，跳过")
            self.refresh_status()
            return

        self._log(f"启动 {name} (模式={run_mode}, 持续={continuous}, 调度={schedule_type})")

        proc = self.pm.start(
            name, run_mode, continuous,
            schedule_type, daily_time, interval
        )

        if proc:
            info = STRATEGY_INFO[name]
            mode_text = "实盘" if run_mode == "live" else "模拟"
            cont_text = "持续运行" if continuous else "一次性"
            self._log(f"✅ {info[0]} 已启动 (PID={proc.pid}, {mode_text}, {cont_text})")
            # 启动后台线程读取子进程 stdout，实时显示到日志
            reader = StdoutReader(name, proc)
            reader.line_signal.connect(self._log)
            reader.start()
            self._readers.append(reader)
        else:
            self._log(f"❌ {name} 启动失败")

        self.refresh_status()

    def stop_strategy(self, name: str):
        """停止单个策略"""
        info = STRATEGY_INFO[name]
        self._log(f"停止 {name}...")

        if self.pm.stop(name):
            self._log(f"✅ {info[0]} 已停止")
        else:
            self._log(f"⚠️ {name} 未在运行")

        self.refresh_status()

    def _select_strategies_dialog(self, all_names):
        """弹出策略选择对话框，返回用户选中的策略名称列表"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QDialogButtonBox, QGroupBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("选择要启动的策略")
        dialog.resize(320, 400)
        
        layout = QVBoxLayout(dialog)
        group = QGroupBox("策略列表 (全选 = 全部启动)")
        group_layout = QVBoxLayout(group)
        
        checkboxes = {}
        for name in sorted(all_names):
            cn_name = STRATEGY_INFO[name][0]
            cb = QCheckBox(f"{cn_name} ({name})")
            cb.setChecked(True)
            group_layout.addWidget(cb)
            checkboxes[name] = cb
        
        layout.addWidget(group)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)
        
        if dialog.exec_() == QDialog.Accepted:
            return [name for name, cb in checkboxes.items() if cb.isChecked()]
        return all_names  # 取消 = 全部
    
    def start_all(self):
        """启动所有策略（单进程协调器，订单去重）"""
        names = self._select_strategies_dialog(list(self._strategy_rows.keys()))
        self._log(f"========== 协调启动 ({len(names)} 个策略) ==========")

        if len(names) <= 1:
            for name in names:
                self.start_strategy(name)
        else:
            run_mode = 'live' if self.rb_live.isChecked() else 'dry_run'
            if self.cb_continuous.isChecked():
                proc = self.pm._start_coordinator(names, run_mode, "daily")
            else:
                proc = None
                for name in names:
                    proc = self.pm._start_one_shot(name, run_mode)
            if proc:
                reader = StdoutReader("协调器", proc)
                reader.line_signal.connect(self._log)
                reader.start()
                self._readers.append(reader)
                self._log(f"✅ 协调器已启动 (PID={proc.pid})")

        self.refresh_status()

    def stop_all(self):
        """停止所有策略"""
        self._log("========== 全部停止 ==========")
        count = self.pm.stop_all_running()
        self._log(f"✅ 已停止 {count} 个策略")
        self.refresh_status()

    def show_report(self):
        """显示简要运行报告"""
        running = []
        for name in self._strategy_rows:
            data = self.pm.is_running(name)
            if data:
                info = STRATEGY_INFO[name]
                running.append(
                    f"  ● {name} ({info[0]})  PID={data['pid']}  "
                    f"模式={data['run_mode']}  "
                    f"启动={data.get('start_time', '?')[:19]}"
                )

        if running:
            msg = f"运行中: {len(running)}/{len(self._strategy_rows)}\n\n" + "\n".join(running)
        else:
            msg = "当前无运行中的策略"

        QMessageBox.information(self, "运行报告", msg)

    def closeEvent(self, event):
        """关闭时的处理"""
        running = sum(1 for n in self._strategy_rows if self.pm.is_running(n))
        if running > 0:
            reply = QMessageBox.question(
                self, "确认关闭",
                f"有 {running} 个策略正在运行中。\n\n"
                f"需要先停止策略吗？",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.stop_all()
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return

        # 停止所有后台 reader 线程
        self.refresh_timer.stop()
        for reader in self._readers:
            reader.quit_reader()
        self._readers.clear()
        event.accept()
