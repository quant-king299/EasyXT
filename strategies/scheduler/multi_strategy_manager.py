import logging

logger = logging.getLogger(__name__)
"""
EasyXT 多策略管理框架
====================

多策略调度管理器，纯单线程架构。

核心功能：
  - 统一配置管理多个策略
  - 一次性执行 / 持续运行 双模式
  - 独立子进程隔离，互不影响
  - PID 文件持久化，跨进程状态检测
  - 统一启动/停止/监控
  - 统一日志和报告

使用方式：
  python multi_strategy_manager.py --status
  python multi_strategy_manager.py --start --live --continuous
"""

import os
import sys
import json
import time
import subprocess
import signal
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class StrategyConfig:
    """单个策略的配置"""
    name: str                          # 策略名称
    module_path: str                   # 策略模块路径
    run_script: str                    # 运行脚本路径（相对于 strategies_dir）
    session_id: str                    # SESSION_ID
    enabled: bool = True               # 是否启用
    priority: int = 0                  # 优先级 (0-10, 越大越优先)
    max_capital: float = 0             # 最大资金限制 (0=不限制)
    target_allocation: float = 0       # 目标资金分配比例 (0-1)
    allowed_securities: List[str] = field(default_factory=list)
    restricted_securities: List[str] = field(default_factory=list)
    run_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyState:
    """策略运行状态"""
    name: str
    status: str = "stopped"             # stopped, running, paused, error
    pid: Optional[int] = None
    start_time: Optional[datetime] = None
    last_signal_time: Optional[datetime] = None
    signal_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    current_positions: Dict[str, int] = field(default_factory=dict)
    used_capital: float = 0


class ConflictDetector:
    """策略冲突检测器"""

    @staticmethod
    def check_position_conflict(strategies: Dict[str, StrategyState],
                               configs: Dict[str, StrategyConfig]) -> Dict[str, List[str]]:
        security_positions = defaultdict(list)
        for name, state in strategies.items():
            if state.status != "running":
                continue
            for security in state.current_positions:
                security_positions[security].append(name)
        return {k: v for k, v in security_positions.items() if len(v) > 1}

    @staticmethod
    def check_capital_conflict(strategies: Dict[str, StrategyState],
                              configs: Dict[str, StrategyConfig],
                              total_capital: float) -> Dict[str, float]:
        conflicts = {}
        for name, state in strategies.items():
            config = configs.get(name)
            if not config:
                continue
            if config.max_capital > 0 and state.used_capital > config.max_capital:
                conflicts[name] = state.used_capital - config.max_capital
        return conflicts

    @staticmethod
    def check_security_permission(security: str, config: StrategyConfig) -> bool:
        if config.allowed_securities:
            return security in config.allowed_securities
        if config.restricted_securities:
            return security not in config.restricted_securities
        return True


class StrategyMonitor:
    """策略监控器"""

    def __init__(self, log_dir: str = None):
        self.log_dir = log_dir or os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(
            self.log_dir,
            f"multi_strategy_{datetime.now().strftime('%Y%m%d')}.log"
        )

    def log(self, level: str, strategy: str, message: str):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] [{level}] [{strategy}] {message}\n"
        logger.info(log_line.strip())
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_line)
        except Exception:
            pass

    def generate_report(self, strategies: Dict[str, StrategyState],
                       configs: Dict[str, StrategyConfig]) -> str:
        report_lines = [
            "=" * 80,
            f"多策略运行报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 80,
            ""
        ]
        total_signals = sum(s.signal_count for s in strategies.values())
        total_errors = sum(s.error_count for s in strategies.values())
        running_count = sum(1 for s in strategies.values() if s.status == "running")
        report_lines.extend([
            f"运行策略数: {running_count}/{len(strategies)}",
            f"总信号数: {total_signals}",
            f"总错误数: {total_errors}",
            ""
        ])
        report_lines.append("策略详情:")
        report_lines.append("-" * 80)
        for name in sorted(configs.keys(), key=lambda x: configs[x].priority, reverse=True):
            state = strategies.get(name)
            config = configs.get(name)
            if not state or not config:
                continue
            status_icon = {"running": "[OK]", "stopped": "[STOP]", "paused": "[PAUSE]", "error": "[ERR]"}.get(state.status, "[?]")
            report_lines.extend([
                f"{status_icon} [{name}] (优先级: {config.priority})",
                f"   状态: {state.status}",
                f"   信号数: {state.signal_count}",
                f"   错误数: {state.error_count}",
                f"   已用资金: {state.used_capital:.2f}",
                f"   持仓: {len(state.current_positions)} 只标的",
            ])
            if state.last_error:
                report_lines.append(f"   最后错误: {state.last_error}")
            report_lines.append("")

        detector = ConflictDetector()
        position_conflicts = detector.check_position_conflict(strategies, configs)
        capital_conflicts = detector.check_capital_conflict(strategies, configs, 0)
        if position_conflicts:
            report_lines.append("[!] 持仓冲突:")
            for security, strategy_names in position_conflicts.items():
                report_lines.append(f"   {security}: {', '.join(strategy_names)}")
            report_lines.append("")
        if capital_conflicts:
            report_lines.append("[!] 资金超限:")
            for strategy_name, over_amount in capital_conflicts.items():
                report_lines.append(f"   {strategy_name}: 超出 {over_amount:.2f}")
            report_lines.append("")
        report_lines.append("=" * 80)
        return "\n".join(report_lines)


class MultiStrategyManager:
    """多策略管理器"""

    def __init__(self, config_file: str = None,
                 strategies_dir: str = None):
        self.config_file = config_file or os.path.join(
            os.path.dirname(__file__), "multi_strategy_config.json"
        )
        self.base_dir = Path(os.path.dirname(__file__))

        # 策略脚本目录（run_*.py 所在位置，需单独配置）
        # 默认指向 quant_strategies，用户可按需修改
        self.strategies_dir = Path(strategies_dir) if strategies_dir else (
            self.base_dir / "../quant_strategies"
        )

        self.configs: Dict[str, StrategyConfig] = {}
        self.states: Dict[str, StrategyState] = {}
        self.monitor = StrategyMonitor()
        self.detector = ConflictDetector()

        self.running = False
        self.processes: Dict[str, Any] = {}          # 子进程（一次性执行）
        self.scheduler_processes: Dict[str, Any] = {}  # 子进程（持续运行调度器）

        self._load_config()

    def _load_config(self):
        """加载策略配置，并从 PID 文件恢复运行状态"""
        if not os.path.exists(self.config_file):
            self.monitor.log("INFO", "manager", f"配置文件不存在，创建默认配置: {self.config_file}")
            self._create_default_config()
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 读取全局配置中的 strategies_dir
            gs = data.get('global_settings', {})
            if gs.get('strategies_dir'):
                self.strategies_dir = Path(gs['strategies_dir'])
                if not self.strategies_dir.is_absolute():
                    self.strategies_dir = (self.base_dir / self.strategies_dir).resolve()

            for name, cfg in data.get('strategies', {}).items():
                self.configs[name] = StrategyConfig(
                    name=name,
                    module_path=cfg.get('module_path', ''),
                    run_script=cfg.get('run_script', ''),
                    session_id=cfg.get('session_id', name),
                    enabled=cfg.get('enabled', True),
                    priority=cfg.get('priority', 0),
                    max_capital=cfg.get('max_capital', 0),
                    target_allocation=cfg.get('target_allocation', 0),
                    allowed_securities=cfg.get('allowed_securities', []),
                    restricted_securities=cfg.get('restricted_securities', []),
                    run_params=cfg.get('run_params', {})
                )

            running_count = 0
            for name in self.configs.keys():
                if name not in self.states:
                    self.states[name] = StrategyState(name=name)
                pid_data = self._read_pid_file(name)
                if pid_data:
                    self.states[name].status = "running"
                    self.states[name].pid = pid_data["pid"]
                    running_count += 1

            self.monitor.log("INFO", "manager",
                             f"已加载 {len(self.configs)} 个策略配置"
                             + (f" (运行中: {running_count})" if running_count else ""))

        except Exception as e:
            self.monitor.log("ERROR", "manager", f"加载配置失败: {e}")

    def _create_default_config(self):
        """创建默认配置文件"""
        default_config = {
            "global_settings": {
                "strategies_dir": "../quant_strategies",
                "log_dir": "./logs",
                "monitor_interval": 30,
                "auto_restart": True,
                "max_restart_count": 3
            },
            "strategies": {
                # ========== 可转债策略 ==========
                "cb_double_low": {
                    "module_path": "strategies.quant_strategies.cb_double_low",
                    "run_script": "run_cb_double_low.py",
                    "session_id": "cb_double_low",
                    "enabled": False,
                    "priority": 5,
                    "max_capital": 50000,
                    "target_allocation": 0.2,
                    "run_params": {
                        "buy_n": 10, "max_price": 130,
                        "continuous_run": False,
                        "schedule_type": "daily",
                        "schedule_daily_time": "09:35"
                    }
                },
                "cb_three_low": {
                    "module_path": "strategies.quant_strategies.cb_three_low",
                    "run_script": "run_cb_three_low.py",
                    "session_id": "cb_three_low",
                    "enabled": False,
                    "priority": 5,
                    "max_capital": 50000,
                    "target_allocation": 0.2,
                    "run_params": {
                        "buy_n": 10,
                        "continuous_run": False,
                        "schedule_type": "daily",
                        "schedule_daily_time": "09:40"
                    }
                },
                "cb_factor_rotation": {
                    "module_path": "strategies.quant_strategies.cb_factor_rotation",
                    "run_script": "run_cb_factor_rotation.py",
                    "session_id": "cb_factor_rotation",
                    "enabled": False,
                    "priority": 5,
                    "max_capital": 50000,
                    "target_allocation": 0.2,
                    "run_params": {
                        "continuous_run": False,
                        "schedule_type": "daily",
                        "schedule_daily_time": "09:45"
                    }
                },
                # ========== 股票策略 ==========
                "dividend_lowvol": {
                    "module_path": "strategies.quant_strategies.dividend_lowvol",
                    "run_script": "run_dividend_lowvol.py",
                    "session_id": "dividend_lowvol",
                    "enabled": False,
                    "priority": 6,
                    "max_capital": 100000,
                    "target_allocation": 0.3,
                    "run_params": {
                        "buy_n": 15,
                        "continuous_run": False,
                        "schedule_type": "daily",
                        "schedule_daily_time": "09:50"
                    }
                },
                # ========== ETF策略 ==========
                "etf_trend": {
                    "module_path": "strategies.quant_strategies.etf_trend",
                    "run_script": "run_etf_trend.py",
                    "session_id": "etf_trend",
                    "enabled": False,
                    "priority": 7,
                    "max_capital": 80000,
                    "target_allocation": 0.25,
                    "run_params": {
                        "buy_n": 5,
                        "continuous_run": False,
                        "schedule_type": "daily",
                        "schedule_daily_time": "09:35"
                    }
                },
                "etf_hot_theme": {
                    "module_path": "strategies.quant_strategies.etf_hot_theme",
                    "run_script": "run_etf_hot_theme.py",
                    "session_id": "etf_hot_theme",
                    "enabled": False,
                    "priority": 7,
                    "max_capital": 80000,
                    "target_allocation": 0.25,
                    "run_params": {
                        "buy_n": 3,
                        "continuous_run": False,
                        "schedule_type": "daily",
                        "schedule_daily_time": "09:40"
                    }
                },
                # ========== 涨停板策略 ==========
                "limit_up": {
                    "module_path": "strategies.quant_strategies.limit_up",
                    "run_script": "run_limit_up.py",
                    "session_id": "limit_up",
                    "enabled": False,
                    "priority": 8,
                    "max_capital": 50000,
                    "target_allocation": 0.15,
                    "run_params": {
                        "buy_n": 2,
                        "continuous_run": False,
                        "schedule_type": "interval",
                        "schedule_interval": 5
                    }
                }
            },
            "conflict_rules": {
                "allow_same_security": False,
                "max_total_capital": 500000,
                "reserve_ratio": 0.1
            }
        }

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            self.monitor.log("INFO", "manager", f"已创建默认配置文件: {self.config_file}")
            self._load_config()
        except Exception as e:
            self.monitor.log("ERROR", "manager", f"创建配置文件失败: {e}")

    # ---- PID 文件管理 ----

    def _pid_file(self, name: str) -> Path:
        return Path(self.monitor.log_dir) / f"{name}.pid"

    def _write_pid_file(self, name: str, pid: int, run_mode: str, schedule_type: str):
        try:
            data = {
                "pid": pid,
                "run_mode": run_mode,
                "schedule_type": schedule_type,
                "start_time": datetime.now().isoformat(),
            }
            with open(self._pid_file(name), 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception:
            pass

    def _read_pid_file(self, name: str) -> Optional[Dict]:
        pf = self._pid_file(name)
        if not pf.exists():
            return None
        try:
            with open(pf, 'r', encoding='utf-8') as f:
                data = json.load(f)
            pid = data.get("pid")
            if pid:
                try:
                    import ctypes
                    kernel32 = ctypes.windll.kernel32
                    handle = kernel32.OpenProcess(0x0400, False, pid)
                    if handle:
                        kernel32.CloseHandle(handle)
                        return data
                except Exception:
                    pass
                try:
                    os.kill(pid, 0)
                    return data
                except OSError:
                    pass
            pf.unlink(missing_ok=True)
            return None
        except Exception:
            return None

    def _remove_pid_file(self, name: str):
        try:
            self._pid_file(name).unlink(missing_ok=True)
        except Exception:
            pass

    def _resolve_run_script(self, run_script: str) -> str:
        """解析 run_script 路径（支持相对于 strategies_dir 的路径）"""
        script_path = Path(run_script)
        if script_path.is_absolute():
            return str(script_path)
        # 先在 base_dir 找，再在 strategies_dir 找
        for parent in [self.base_dir, self.strategies_dir]:
            candidate = parent / run_script
            if candidate.exists():
                return str(candidate)
        # 默认返回 strategies_dir 下的路径
        return str(self.strategies_dir / run_script)

    # ---- 启动/停止 ----

    def start_strategy(self, name: str, dry_run: bool = True) -> bool:
        """启动单个策略

        两种模式：
        1. 一次性执行：运行 run_*.py 脚本，执行完退出
        2. 持续运行：启动 strategy_scheduler.py 独立子进程
        """
        if name not in self.configs:
            self.monitor.log("ERROR", "manager", f"策略不存在: {name}")
            return False

        config = self.configs[name]
        state = self.states[name]

        if not config.enabled:
            self.monitor.log("WARN", "manager", f"策略未启用: {name}")
            return False

        existing = self._read_pid_file(name)
        if existing:
            self.monitor.log("WARN", "manager",
                             f"策略已在运行 (PID: {existing['pid']}, 模式: {existing['run_mode']})")
            state.status = "running"
            state.pid = existing["pid"]
            return True

        try:
            use_scheduler = config.run_params.get("continuous_run", False)
            run_mode_str = "live" if not dry_run else "dry_run"

            if use_scheduler:
                # ---- 持续运行模式 ----
                scheduler_script = os.path.join(self.base_dir, "strategy_scheduler.py")

                cmd = [
                    "python", scheduler_script,
                    "--strategy", name,
                    "--mode", run_mode_str,
                ]

                schedule_type = config.run_params.get("schedule_type", "daily")
                cmd += ["--schedule", schedule_type]

                if schedule_type == "daily":
                    daily_time = config.run_params.get("schedule_daily_time", "09:35")
                    cmd += ["--daily-time", daily_time]
                elif schedule_type == "interval":
                    interval = config.run_params.get("schedule_interval", 60)
                    cmd += ["--interval", str(interval)]

                self.monitor.log("INFO", name, f"启动持续运行调度器: {' '.join(cmd)}")

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )

                self.scheduler_processes[name] = process
                state.status = "running"
                state.start_time = datetime.now()
                state.pid = process.pid
                self._write_pid_file(name, process.pid, run_mode_str, schedule_type)

                self.monitor.log("INFO", name,
                                 f"调度器已启动 (PID: {process.pid}, "
                                 f"模式: {'模拟' if dry_run else '实盘'}, "
                                 f"调度: {schedule_type})")
                return True

            else:
                # ---- 一次性执行模式 ----
                run_script = self._resolve_run_script(config.run_script)

                if not os.path.exists(run_script):
                    self.monitor.log("ERROR", "manager", f"运行脚本不存在: {run_script}")
                    return False

                cmd = ["python", run_script]
                if not dry_run:
                    cmd.append("--trade")

                env = os.environ.copy()
                env["STRATEGY_NAME"] = name
                env["STRATEGY_SESSION_ID"] = config.session_id

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True
                )

                self.processes[name] = process
                state.status = "running"
                state.start_time = datetime.now()
                state.pid = process.pid
                self._write_pid_file(name, process.pid, run_mode_str, "once")

                self.monitor.log("INFO", name, f"策略启动成功 (PID: {process.pid}, 模式: {'模拟' if dry_run else '实盘'})")
                return True

        except Exception as e:
            state.status = "error"
            state.last_error = str(e)
            self.monitor.log("ERROR", name, f"启动失败: {e}")
            return False

    def stop_strategy(self, name: str) -> bool:
        """停止单个策略"""
        if name not in self.states:
            return False

        state = self.states[name]
        pid_data = self._read_pid_file(name)

        if state.status != "running" and not pid_data:
            self.monitor.log("WARN", "manager", f"策略未运行: {name}")
            return True

        try:
            process = self.processes.pop(name, None)
            if process:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

            sched_process = self.scheduler_processes.pop(name, None)
            if sched_process:
                sched_process.terminate()
                try:
                    sched_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    sched_process.kill()

            if not process and not sched_process and pid_data:
                pid = pid_data["pid"]
                try:
                    os.kill(pid, signal.SIGTERM)
                    self.monitor.log("INFO", name, f"已发送终止信号到 PID: {pid}")
                except OSError:
                    pass

            self._remove_pid_file(name)
            state.status = "stopped"
            state.start_time = None
            self.monitor.log("INFO", name, "策略已停止")
            return True

        except Exception as e:
            self.monitor.log("ERROR", name, f"停止失败: {e}")
            return False

    def start_all(self, dry_run: bool = True):
        """启动所有启用的策略（按优先级排序）"""
        sorted_strategies = sorted(
            self.configs.items(),
            key=lambda x: x[1].priority,
            reverse=True
        )
        for name, config in sorted_strategies:
            if config.enabled:
                self.monitor.log("INFO", "manager", f"正在启动策略: {name} (优先级: {config.priority})")
                self.start_strategy(name, dry_run=dry_run)
                time.sleep(2)

    def stop_all(self):
        """停止所有策略"""
        for name in list(self.states.keys()):
            self.stop_strategy(name)

    def get_status(self) -> Dict[str, Dict]:
        """获取所有策略状态"""
        status = {}
        for name, state in self.states.items():
            config = self.configs.get(name)
            status[name] = {
                "status": state.status,
                "pid": state.pid,
                "start_time": state.start_time.isoformat() if state.start_time else None,
                "signal_count": state.signal_count,
                "error_count": state.error_count,
                "enabled": config.enabled if config else False,
                "priority": config.priority if config else 0
            }
        return status

    def print_status(self):
        """打印策略状态（通过 PID 文件检测实际运行状态）"""
        logger.info("\n" + "=" * 80)
        logger.info("EasyXT Strategy Status Report")
        logger.info("=" * 80)
        logger.info(f"{'Strategy Name':<20} {'Status':<14} {'Mode':<12} {'PID':<10} {'Enabled':<8}")
        logger.info("-" * 80)

        for name in sorted(self.configs.keys(), key=lambda x: self.configs[x].priority, reverse=True):
            state = self.states.get(name)
            config = self.configs.get(name)

            pid_data = self._read_pid_file(name)

            if pid_data:
                status_text = "[RUNNING]"
                pid_text = str(pid_data["pid"])
                mode_text = "持续运行" if pid_data.get("schedule_type", "once") != "once" else "一次性"
            elif state and state.status == "running":
                status_text = "[RUNNING]"
                pid_text = str(state.pid) if state.pid else "-"
                mode_text = "持续运行" if config.run_params.get("continuous_run", False) else "一次性"
            else:
                status_text = "[STOPPED]"
                pid_text = "-"
                mode_text = "持续运行" if config.run_params.get("continuous_run", False) else "一次性"

            enabled_text = "是" if config.enabled else "否"
            logger.info(f"{name:<20} {status_text:<14} {mode_text:<12} {pid_text:<10} {enabled_text:<8}")

        logger.info("-" * 80)
        logger.info("=" * 80 + "\n")

    def generate_report(self) -> str:
        """生成运行报告"""
        return self.monitor.generate_report(self.states, self.configs)

    def save_report(self, report: str = None):
        """保存运行报告"""
        report = report or self.generate_report()
        report_file = os.path.join(
            self.monitor.log_dir,
            f"strategy_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            self.monitor.log("INFO", "manager", f"报告已保存: {report_file}")
        except Exception as e:
            self.monitor.log("ERROR", "manager", f"保存报告失败: {e}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="EasyXT 多策略管理框架",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 查看所有策略状态
  python multi_strategy_manager.py --status

  # 一次性执行（模拟）
  python multi_strategy_manager.py --start cb_double_low etf_trend

  # 一次性执行（实盘）
  python multi_strategy_manager.py --start --live

  # 持续运行（实盘）- 每个策略一个独立进程
  python multi_strategy_manager.py --start --live --continuous

  # 停止所有策略
  python multi_strategy_manager.py --stop

  # 生成运行报告
  python multi_strategy_manager.py --report
        """
    )
    parser.add_argument("--config", "-c", help="配置文件路径")
    parser.add_argument("--strategies-dir", help="策略脚本目录 (默认: ../quant_strategies)")
    parser.add_argument("--dry-run", "-d", action="store_true", default=True, help="模拟模式（不下单）")
    parser.add_argument("--live", "-l", action="store_true", help="实盘模式")
    parser.add_argument("--continuous", action="store_true",
                        help="持续运行模式（每个策略启动独立调度器进程）")
    parser.add_argument("--start", "-s", nargs="*",
                        help="启动指定策略（不指定策略名则启动所有启用的策略）")
    parser.add_argument("--stop", action="store_true", help="停止所有策略")
    parser.add_argument("--status", action="store_true", help="查看策略状态")
    parser.add_argument("--report", "-r", action="store_true", help="生成运行报告")

    args = parser.parse_args()

    dry_run = not args.live

    manager = MultiStrategyManager(
        config_file=args.config,
        strategies_dir=args.strategies_dir,
    )

    if args.stop:
        logger.info("正在停止所有策略...")
        manager.stop_all()
        return

    if args.status:
        manager.print_status()
        return

    if args.report:
        report = manager.generate_report()
        logger.info(report)
        manager.save_report(report)
        return

    if args.start is not None:
        if args.continuous:
            for name in (args.start if len(args.start) > 0 else
                         [n for n, c in manager.configs.items() if c.enabled]):
                if name in manager.configs:
                    manager.configs[name].run_params["continuous_run"] = True

        if len(args.start) == 0:
            manager.start_all(dry_run=dry_run)
        else:
            for name in args.start:
                manager.start_strategy(name, dry_run=dry_run)
    else:
        manager.print_status()
        logger.info("提示: 使用 --help 查看所有命令")
        logger.info("  一次性执行:   python multi_strategy_manager.py --start etf_trend")
        logger.info("  持续运行:     python multi_strategy_manager.py --start --live --continuous")
        logger.info("  查看状态:     python multi_strategy_manager.py --status")
        logger.info("  生成报告:     python multi_strategy_manager.py --report")
        logger.info("  停止所有:     python multi_strategy_manager.py --stop")


if __name__ == "__main__":
    main()
