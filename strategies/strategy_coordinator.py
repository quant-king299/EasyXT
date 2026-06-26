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

# 策略模块路径（优先知识星球专属 quant_strategies/，其次公开 strategies/）
_STRATEGY_NAMES = [
    "limit_up", "etf_trend", "etf_hot_theme", "dividend_lowvol",
    "cb_double_low", "cb_three_low", "cb_factor_rotation",
]

def _resolve_strategy_module(name: str) -> str:
    """解析策略模块路径，优先知识星球目录，失败则尝试公开目录"""
    quant_path = f"strategies.quant_strategies.{name}"
    public_path = f"strategies.{name}"
    import importlib
    try:
        importlib.import_module(quant_path)
        return quant_path
    except ImportError:
        return public_path

def load_strategy_class(name: str):
    import importlib
    if name not in _STRATEGY_NAMES:
        raise ValueError(f"未知策略: {name}")
    mod_path = _resolve_strategy_module(name)
    try:
        mod = importlib.import_module(mod_path)
    except ImportError:
        raise ImportError(
            f"策略 '{name}' 不存在。\n"
            f"部分策略为知识星球专属，请加入知识星球获取完整策略包。"
        )
    for attr in dir(mod):
        obj = getattr(mod, attr)
        if isinstance(obj, type) and attr.endswith("Strategy"):
            return obj
    raise ValueError(f"未找到策略类: {name}")

def _extract_code(row: dict) -> str:
    """从信号行提取代码并补齐交易所后缀（兼容 fund_code/bond_code/stock_code/code）"""
    for key in ("code", "fund_code", "bond_code", "stock_code"):
        if key in row and row[key]:
            code = str(row[key])
            if not code.endswith(('.SH', '.SZ')):
                if code.startswith(('51', '56', '58', '588', '689')):
                    code += '.SH'
                elif code.startswith(('11', '12', '13')):
                    code += '.SH' if code.startswith('11') else '.SZ'
                elif code.startswith(('6',)):
                    code += '.SH'
                else:
                    code += '.SZ'
            return code
    return ""

def consolidate_orders(all_sells, all_buys):
    """合并多个策略的买卖信号，买卖均按代码去重"""
    seen = set()
    unique_sells = []
    for s in all_sells:
        code = _extract_code(s)
        if code and code not in seen:
            unique_sells.append(s)
            seen.add(code)
    unique_buys = []
    for b in all_buys:
        code = _extract_code(b)
        if code and code not in seen:
            unique_buys.append(b)
            seen.add(code)
    return unique_sells, unique_buys


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


def _wait_for_duckdb(max_retries: int = 10, delay: float = 2.0) -> bool:
    """等待 DuckDB 可用，直到数据库被释放"""
    import duckdb
    path = _read_env('DUCKDB_PATH', 'D:/StockData/stock_data.ddb')
    for attempt in range(max_retries):
        try:
            con = duckdb.connect(path, read_only=True)
            con.execute("SELECT 1")
            con.close()
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                import time
                logger.info(f"  [DuckDB] 等待数据库释放... ({attempt + 1}/{max_retries})")
                time.sleep(delay)
                continue
            logger.warning(f"[DuckDB] 等待超时: {e}")
            return False
    return False


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
            qmt_path = _read_env('QMT_USERDATA_PATH') or _read_env('QMT_DATA_DIR')
            import os as _os
            if not qmt_path:
                logger.error("未配置 QMT 路径！请在 .env 中设置 QMT_DATA_DIR 或 QMT_USERDATA_PATH")
                return False
            if not _os.path.exists(qmt_path):
                logger.error(f"QMT 路径不存在: {qmt_path}，请检查 .env 配置")
                return False
            self.api.init_trade(qmt_path)
            self.account_id = _read_env('QMT_ACCOUNT_ID')
            if self.account_id:
                self.api.trade.add_account(self.account_id)
            else:
                logger.warning("未配置 QMT_ACCOUNT_ID，请在 .env 中设置")
            return True
        except Exception as e:
            logger.warning(f"连接失败: {e}")
            return False

    def run_once(self):
        self._sold.clear()
        all_sells = []
        all_buys = []
        failed_names = []
        for i, name in enumerate(self.strategy_names, 1):
            total = len(self.strategy_names)
            logger.info(f"[{i}/{total}] {name} 开始生成信号...")
            _wait_for_duckdb()
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
                    buy_count = len(buy_list) if hasattr(buy_list, '__len__') else 0
                    sell_count = len(sell_list) if hasattr(sell_list, '__len__') else 0
                    logger.info(f"[{i}/{total}] {name} 完成 (买{buy_count} 卖{sell_count})")
                    break
                except Exception as e:
                    if attempt < 2:
                        logger.info(f"[{name}] 第{attempt+1}次失败，3s后重试...")
                        import time
                        time.sleep(3)
                    else:
                        logger.warning(f"[{name}] 信号生成失败: {e}")
                        failed_names.append(name)
        if not all_sells and not all_buys:
            logger.warning("所有策略均无信号，本轮跳过")
            return
        sells, buys = consolidate_orders(all_sells, all_buys)
        if failed_names:
            logger.warning(f"以下策略失败: {', '.join(failed_names)}，使用其余策略信号继续")
        logger.info(f"  卖出 {len(sells)} 只，买入 {len(buys)} 只（去重后）")
        if self.run_mode == "live" and self.api:
            self._execute(sells, buys)

    def _execute(self, sells, buys):
        acc = self.account_id
        for s in sells:
            code = _extract_code(s)
            price = s.get("price", 0)
            if not code or price <= 0 or code in self._sold:
                continue
            self._sold.add(code)
            volume = 200 if code.startswith('689') else 100
            price = round(price, 3) if code[:2] in ('11','12','13','51','56','58','15','16','59','588') else round(price, 2)
            try:
                self.api.trade.sell(account_id=acc, code=code,
                    volume=volume, price=price, price_type="limit")
                logger.info(f"  [卖出] {code} @{price} vol={volume}")
            except Exception as e:
                logger.info(f"  [卖出失败] {code}: {e}")
        for b in buys:
            code = _extract_code(b)
            price = b.get("price", 0)
            if not code or price <= 0:
                continue
            volume = 200 if code.startswith('689') else 100
            price = round(price, 3) if code[:2] in ('11','12','13','51','56','58','15','16','59','588') else round(price, 2)
            try:
                self.api.trade.buy(account_id=acc, code=code,
                    volume=volume, price=price, price_type="limit")
                logger.info(f"  [买入] {code} @{price} vol={volume}")
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

