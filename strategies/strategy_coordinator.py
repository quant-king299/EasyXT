# -*- coding: utf-8 -*-
"""
单进程策略协调器

替代原来的多进程子调度器模型。
所有策略在同一个进程中运行，共享一个 QMT 连接，
订单去重后统一执行，避免"证券可用数量不足"问题。
"""
import logging
logger = logging.getLogger(__name__)
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

STRATEGY_MODULES = {
    "limit_up": "strategies.quant_strategies.limit_up",
    "etf_trend": "strategies.quant_strategies.etf_trend",
    "etf_hot_theme": "strategies.quant_strategies.etf_hot_theme",
    "dividend_lowvol": "strategies.quant_strategies.dividend_lowvol",
    "cb_double_low": "strategies.quant_strategies.cb_double_low",
    "cb_three_low": "strategies.quant_strategies.cb_three_low",
    "cb_factor_rotation": "strategies.quant_strategies.cb_factor_rotation",
}

def load_strategy_class(name: str):
    import importlib
    mod_path = STRATEGY_MODULES.get(name)
    if not mod_path:
        raise ValueError(f"未知策略: {name}")
    mod = importlib.import_module(mod_path)
    for attr in dir(mod):
        obj = getattr(mod, attr)
        if isinstance(obj, type) and attr.endswith("Strategy"):
            return obj
    raise ValueError(f"未找到策略类: {name}")

def consolidate_orders(all_sells, all_buys):
    """合并多个策略的买卖信号，去重卖单"""
    seen = set()
    unique_sells = []
    for s in all_sells:
        code = s.get("code", "")
        if code and code not in seen:
            unique_sells.append(s)
            seen.add(code)
    return unique_sells, all_buys


def _read_env(key: str, default: str = '') -> str:
    """从 .env 文件读取配置（子进程无法继承内存中的 env）"""
    try:
        env_file = Path(__file__).parent.parent / '.env'
        if env_file.exists():
            for line in env_file.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if line.startswith(f'{key}='):
                    return line.split('=', 1)[1].strip()
    except Exception:
        pass
    return default



def _read_env(key: str, default: str = '') -> str:
    """从 .env 文件直接读取配置（子进程无法继承内存中的 env）"""
    try:
        env_file = Path(__file__).parent.parent / '.env'
        if env_file.exists():
            for line in env_file.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if line.startswith(f'{key}='):
                    return line.split('=', 1)[1].strip()
    except Exception:
        pass
    return default


class StrategyCoordinator:
    """单进程策略协调器"""
    def __init__(self, strategy_names, run_mode="dry_run"):
        self.strategy_names = strategy_names
        self.run_mode = run_mode
        self.api = None
        self._sold = set()

    def init_trading(self):
        if self.run_mode == "dry_run":
            return True
        try:
            from easy_xt import get_api, get_extended_api
            self.api = get_api()
            self.api.init_data()
            qmt_path = _read_env('QMT_USERDATA_PATH')
            if not qmt_path:
                qmt_path = _read_env('QMT_DATA_DIR')
            if not qmt_path:
                qmt_path = "D:\\国金QMT交易端模拟\\userdata_mini"
            import os as _os
            if qmt_path and _os.path.exists(qmt_path):
                self.api.init_trade(qmt_path)
                self.account_id = _read_env('QMT_ACCOUNT_ID')
                if self.account_id:
                    self.api.trade.add_account(self.account_id)
                return True
            return True
        except Exception as e:
            logger.warning(f"连接失败: {e}")
            return False

    def run_once(self):
        self._sold.clear()
        all_sells = []
        all_buys = []
        for name in self.strategy_names:
            success = False
            for attempt in range(3):
                try:
                    cls = load_strategy_class(name)
                    strategy = cls(api=self.api)
                    buy_list, sell_list = strategy.generate_signals()
                    for _, row in sell_list.iterrows():
                        all_sells.append(dict(row))
                    for _, row in buy_list.iterrows():
                        all_buys.append(dict(row))
                    success = True
                    break
                except Exception as e:
                    if attempt < 2:
                        logger.info(f"[{name}] 第{attempt+1}次失败，3s后重试...")
                        import time
                        time.sleep(3)
                    else:
                        logger.warning(f"[{name}] 信号生成失败: {e}")
        sells, buys = consolidate_orders(all_sells, all_buys)
        logger.info(f"  卖出 {len(sells)} 只，买入 {len(buys)} 只（去重后）")
        if self.run_mode == "live" and self.api:
            self._execute(sells, buys)

    def _execute(self, sells, buys):
        acc = self.account_id
        for s in sells:
            code = s.get("code", "")
            price = s.get("price", 0)
            if price <= 0 or code in self._sold:
                continue
            self._sold.add(code)
            try:
                self.api.trade.sell(account_id=acc, code=code,
                    volume=100, price=price, price_type="limit")
                logger.info(f"  [卖出] {code} @{price:.2f}")
            except Exception as e:
                logger.info(f"  [卖出失败] {code}: {e}")
        for b in buys:
            code = b.get("code", "")
            price = b.get("price", 0)
            if price <= 0:
                continue
            try:
                self.api.trade.buy(account_id=acc, code=code,
                    volume=100, price=price, price_type="limit")
                logger.info(f"  [买入] {code} @{price:.2f}")
            except Exception as e:
                logger.info(f"  [买入失败] {code}: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="策略协调器")
    parser.add_argument("--strategies", nargs="+", required=True)
    parser.add_argument("--mode", default="dry_run", choices=["dry_run", "live"])
    parser.add_argument("--schedule", default="daily", choices=["daily", "interval"])
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--daily-time", default="09:35")
    args = parser.parse_args()

    logger.info(f"策略协调器启动: {args.strategies} ({args.mode})")
    coord = StrategyCoordinator(args.strategies, args.mode)
    coord.init_trading()

    run_count = 0
    while True:
        try:
            coord.run_once()
            run_count += 1
            logger.info(f"第 {run_count} 轮执行完成")
            if args.schedule == "interval":
                time.sleep(args.interval * 60)
            else:
                parts = args.daily_time.split(":")
                target_h, target_m = int(parts[0]), int(parts[1])
                now = datetime.now()
                next_run = now.replace(hour=target_h, minute=target_m, second=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                time.sleep((next_run - now).total_seconds())
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"主循环异常: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()

