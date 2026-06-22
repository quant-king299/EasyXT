"""
EasyXT 策略持续运行调度器
========================

纯单线程架构：
  - while True 主循环 + time.sleep()
  - 所有操作在主线程同步执行
  - 无线程安全问题

功能：
  - 交易日判断（周末/节假日）
  - 交易时段判断（9:30-11:30, 13:00-15:00）
  - 间隔执行 / 每日定时 两种调度模式
  - 状态持久化（断点续跑）
  - Ctrl+C 优雅退出

使用方式：
  python strategy_scheduler.py --strategy etf_trend
  python strategy_scheduler.py --strategy etf_trend --mode live --schedule daily --daily-time 09:35
"""

import os
import sys
import json
import time
import signal
import io
import contextlib
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Dict, List, Optional

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _read_env(key: str, default: str = '') -> str:
    """从项目根目录 .env 文件读取配置（调度器子进程无法继承内存中的 env）"""
    try:
        env_file = PROJECT_ROOT / '.env'
        if env_file.exists():
            for line in env_file.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if line.startswith(f'{key}='):
                    return line.split('=', 1)[1].strip()
    except Exception:
        pass
    return default


# ---------------------------------------------------------------------------
# 交易日判断
# ---------------------------------------------------------------------------

class TradeDayChecker:
    """交易日检查器（周末 + 简单节假日）"""

    # 2025-2026 中国A股节假日（休市日，不含周末）
    HOLIDAYS = {
        # 2025
        "20250101",  # 元旦
        "20250128", "20250129", "20250130", "20250131",  # 春节
        "20250203", "20250204",  # 春节调休休市
        "20250404",  # 清明节
        "20250501", "20250502",  # 劳动节
        "20250505",  # 劳动节调休
        "20250602",  # 端午节
        "20251001", "20251002", "20251003", "20251006", "20251007", "20251008",  # 国庆+中秋
        # 2026
        "20260101",  # 元旦
        "20260217", "20260218", "20260219", "20260220",  # 春节
        "20260406",  # 清明节
        "20260501",  # 劳动节
        "20260619",  # 端午节
        "20261001", "20261002", "20261005", "20261006", "20261007",  # 国庆
    }

    @classmethod
    def is_trade_day(cls, dt: datetime) -> bool:
        """判断是否为交易日"""
        # 周末非交易日
        if dt.weekday() >= 5:
            return False
        # 节假日非交易日
        if dt.strftime("%Y%m%d") in cls.HOLIDAYS:
            return False
        return True

    @classmethod
    def next_trade_day(cls, dt: datetime) -> datetime:
        """获取下一个交易日"""
        d = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        d += timedelta(days=1)
        while not cls.is_trade_day(d):
            d += timedelta(days=1)
        return d


# ---------------------------------------------------------------------------
# 交易时段
# ---------------------------------------------------------------------------

class TradingHours:
    """交易时段"""

    MORNING_START = dt_time(9, 30)
    MORNING_END = dt_time(11, 30)
    AFTERNOON_START = dt_time(13, 0)
    AFTERNOON_END = dt_time(15, 0)

    @classmethod
    def in_trading_session(cls, dt: datetime) -> bool:
        """判断是否在连续竞价时段"""
        t = dt.time()
        return (cls.MORNING_START <= t <= cls.MORNING_END or
                cls.AFTERNOON_START <= t <= cls.AFTERNOON_END)

    @classmethod
    def is_market_open(cls, dt: datetime) -> bool:
        """判断市场是否开盘（含集合竞价）"""
        t = dt.time()
        return dt_time(9, 15) <= t <= dt_time(15, 0)


# ---------------------------------------------------------------------------
# 调度器
# ---------------------------------------------------------------------------

class StrategyScheduler:
    """单线程策略调度器"""

    def __init__(self, strategy_name: str,
                 run_mode: str = "dry_run",
                 schedule_type: str = "daily",
                 interval_minutes: int = 60,
                 daily_time: str = "09:35"):
        """
        Args:
            strategy_name: 策略名称
            run_mode: dry_run / live
            schedule_type: interval（间隔执行）/ daily（每日定时）
            interval_minutes: 间隔分钟数（schedule_type=interval 时生效）
            daily_time: 每日执行时间 HH:MM（schedule_type=daily 时生效）
        """
        self.strategy_name = strategy_name
        self.run_mode = run_mode
        self.schedule_type = schedule_type
        self.interval_minutes = interval_minutes
        self.daily_time = daily_time

        self.running = False
        self.last_task_run: Dict[str, datetime] = {}

        # 日志
        self.log_dir = Path("./logs")
        self.log_dir.mkdir(exist_ok=True)

        # 策略实例（懒初始化）
        self.api = None
        self.strategy = None

        # 状态持久化
        self.state_file = self.log_dir / f"scheduler_{strategy_name}_state.json"
        self.run_count = 0
        self.success_count = 0
        self.error_count = 0
        self._load_state()

        # 信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    # ---- 信号处理 ----

    def _signal_handler(self, signum, frame):
        name = signal.Signals(signum).name
        self._log("INFO", f"收到信号 {name}，正在停止...")
        self.running = False

    # ---- 日志 ----

    def _log(self, level: str, message: str):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] [{level}] [{self.strategy_name}] {message}"
        print(log_line)
        try:
            log_file = self.log_dir / f"scheduler_{self.strategy_name}_{datetime.now().strftime('%Y%m%d')}.log"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_line + '\n')
        except Exception:
            pass

    # ---- 状态持久化 ----

    def _load_state(self):
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.run_count = data.get('run_count', 0)
                self.success_count = data.get('success_count', 0)
                self.error_count = data.get('error_count', 0)
                self._log("INFO", f"已加载状态: run={self.run_count}, ok={self.success_count}, err={self.error_count}")
        except Exception as e:
            self._log("WARN", f"加载状态失败: {e}")

    def _save_state(self):
        try:
            data = {
                'strategy_name': self.strategy_name,
                'run_count': self.run_count,
                'success_count': self.success_count,
                'error_count': self.error_count,
                'last_save': datetime.now().isoformat(),
            }
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._log("WARN", f"保存状态失败: {e}")

    # ---- 调度判断 ----

    def _should_run_now(self, now: datetime) -> bool:
        """判断是否应该执行策略"""
        if self.schedule_type == "daily":
            # 每日定时：到达指定时间且今天未执行
            h, m = map(int, self.daily_time.split(":"))
            task_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if now < task_time:
                return False
            last = self.last_task_run.get("strategy")
            if last and last.date() == now.date():
                return False
            return True

        elif self.schedule_type == "interval":
            # 间隔执行：距离上次执行超过间隔
            last = self.last_task_run.get("strategy")
            if last:
                elapsed = (now - last).total_seconds()
                return elapsed >= self.interval_minutes * 60
            return True  # 首次运行

        return False

    # ---- 策略执行 ----

    def _run_strategy(self) -> bool:
        """执行策略（主线程同步执行）"""
        try:
            self._log("INFO", "=" * 50)
            self._log("INFO", "开始执行策略...")

            # 初始化 API
            if not self.api:
                from easy_xt import get_api
                self.api = get_api()
                self.api.init_data()
                self._log("INFO", "API 初始化完成")

                # 实盘模式：初始化交易通道 + 添加账户
                if self.run_mode == "live":
                    qmt_path = _read_env('QMT_DATA_DIR')
                    account_id = _read_env('QMT_ACCOUNT_ID')

                    if qmt_path and account_id:
                        session_id = f"scheduler_{self.strategy_name}"
                        ok = self.api.init_trade(qmt_path, session_id)
                        self._log("INFO", f"交易初始化: {'成功' if ok else '失败'} (session={session_id})")
                        if ok:
                            self.api.add_account(account_id)
                            self._log("INFO", f"已添加账户: {account_id}")
                    else:
                        self._log("ERROR", f"缺少配置: QMT_DATA_DIR={qmt_path}, QMT_ACCOUNT_ID={account_id}")

            # 获取策略类
            from strategies.quant_strategies import get_strategy_class
            strategy_class = get_strategy_class(self.strategy_name)
            if not strategy_class:
                self._log("ERROR", f"策略不存在: {self.strategy_name}")
                return False

            # 创建策略实例
            if not self.strategy:
                account_id = _read_env('QMT_ACCOUNT_ID')
                self.strategy = strategy_class(api=self.api, account_id=account_id or None)
                self._log("INFO", f"策略实例创建完成: {strategy_class.__name__}")

            # 执行策略（同时输出到 stdout 和日志）
            dry_run = (self.run_mode == "dry_run")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                result = self.strategy.run(dry_run=dry_run)
            strategy_output = buf.getvalue().strip()
            if strategy_output:
                # 写回真实 stdout（GUI 管道能读到）
                sys.stdout.write(strategy_output + '\n')
                sys.stdout.flush()
                # 写入日志文件
                for line in strategy_output.splitlines():
                    if line.strip():
                        self._log("SIGNAL", line)

            # 更新状态
            self.last_task_run["strategy"] = datetime.now()
            self.run_count += 1
            self.success_count += 1
            self._save_state()

            self._log("INFO", f"策略执行完成 (第 {self.run_count} 次, 成功 {self.success_count} 次)")
            self._log("INFO", "=" * 50)
            return True

        except Exception as e:
            self.error_count += 1
            self._save_state()
            self._log("ERROR", f"策略执行失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ---- 主循环 ----

    def start(self):
        """启动调度器（主循环）"""
        if self.running:
            self._log("WARN", "调度器已在运行中")
            return

        self.running = True
        self._log("INFO", "=" * 50)
        self._log("INFO", f"调度器启动")
        self._log("INFO", f"  策略: {self.strategy_name}")
        self._log("INFO", f"  模式: {self.run_mode}")
        self._log("INFO", f"  调度: {self.schedule_type}")
        if self.schedule_type == "daily":
            self._log("INFO", f"  执行时间: 每日 {self.daily_time}")
        else:
            self._log("INFO", f"  执行间隔: 每 {self.interval_minutes} 分钟")
        self._log("INFO", f"  累计运行: {self.run_count} 次")
        self._log("INFO", "按 Ctrl+C 停止")
        self._log("INFO", "=" * 50)

        # ==================== 主循环 ====================
        while self.running:
            try:
                now = datetime.now()

                # 1. 非交易日跳过
                if not TradeDayChecker.is_trade_day(now):
                    self._log("DEBUG", f"{now.strftime('%Y%m%d')} 非交易日，等待中...")
                    time.sleep(300)  # 非交易日 5 分钟检查一次
                    continue

                # 2. 检查是否到执行时间
                if self._should_run_now(now):
                    self._run_strategy()

                # 3. 等待下一次检查
                time.sleep(60)

            except KeyboardInterrupt:
                self._log("INFO", "用户中断")
                break
            except Exception as e:
                self._log("ERROR", f"主循环异常: {e}")
                time.sleep(60)

        self._log("INFO", "调度器已停止")


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="EasyXT 策略持续运行调度器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python strategy_scheduler.py --strategy etf_trend
  python strategy_scheduler.py --strategy etf_trend --mode live --schedule daily --daily-time 09:35
  python strategy_scheduler.py --strategy cb_double_low --mode dry_run --schedule interval --interval 30
        """
    )
    parser.add_argument("--strategy", "-s", required=True, help="策略名称")
    parser.add_argument("--mode", "-m", choices=["dry_run", "live"], default="dry_run",
                        help="运行模式 (默认: dry_run)")
    parser.add_argument("--schedule", choices=["daily", "interval"], default="daily",
                        help="调度类型: daily=每日定时, interval=间隔执行 (默认: daily)")
    parser.add_argument("--daily-time", default="09:35",
                        help="每日执行时间 HH:MM (默认: 09:35)")
    parser.add_argument("--interval", "-i", type=int, default=60,
                        help="间隔分钟数 (默认: 60)")

    args = parser.parse_args()

    scheduler = StrategyScheduler(
        strategy_name=args.strategy,
        run_mode=args.mode,
        schedule_type=args.schedule,
        interval_minutes=args.interval,
        daily_time=args.daily_time,
    )

    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
