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
    """单进程策略协调器（虚拟簿记 + 持仓感知）"""
    def __init__(self, strategy_names, run_mode="dry_run"):
        self.strategy_names = strategy_names
        self.run_mode = run_mode
        self.api = None
        self.bookkeeper = None  # 延迟初始化

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

    def _query_held_codes(self) -> set:
        """
        查询当前持仓代码集合

        优先走 xttrader，不可用时走信号桥接查询。
        查询失败返回空集合（保守策略：不跳过任何信号）。
        返回的代码统一带交易所后缀（.SH/.SZ），与 _extract_code 输出一致。
        """
        codes = set()
        try:
            # 方式 1：xttrader 直连
            if self.api and self.account_id:
                positions = self.api.trade.get_positions(self.account_id)
                if positions is not None and not positions.empty:
                    for code in positions['code']:
                        codes.add(_extract_code({'code': code}))
                    logger.info(f"[持仓] xttrader 查询到 {len(codes)} 只持仓")
                    return codes
        except Exception:
            pass

        try:
            # 方式 2：信号桥接查询（大QMT 返回代码无后缀，需补齐）
            import sys as _sys
            _bridge_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                '..', 'EasyXT_Strategies_v2.2',
                'strategies', 'quant_strategies', 'qmt_bridge'
            )
            _bridge_dir = os.path.normpath(_bridge_dir)
            if _bridge_dir not in _sys.path:
                _sys.path.insert(0, _bridge_dir)
            from qmt_signal_bridge import QmtSignalBridge
            bridge = QmtSignalBridge()
            pos_list = bridge.query_positions(account_id=self.account_id or '', timeout=10)
            if pos_list:
                for p in pos_list:
                    raw = p.get('stock_code', '')
                    vol = p.get('volume', 0)
                    if raw and vol > 0:  # 只统计有可用数量的持仓
                        codes.add(_extract_code({'code': raw}))
                logger.info(f"[持仓] 信号桥接查询到 {len(codes)} 只有效持仓")
                return codes
        except Exception as e:
            logger.debug(f"[持仓] 信号桥接查询失败: {e}")

        return codes

    def run_once(self):
        # ── 初始化虚拟簿记 ──
        if self.bookkeeper is None:
            from strategies.virtual_bookkeeper import VirtualBookkeeper
            self.bookkeeper = VirtualBookkeeper()

        # ── 每策略独立生成信号（注入虚拟持仓）──
        all_sells = []   # [(strategy_name, sell_dict), ...]
        all_buys = []    # [(strategy_name, buy_dict), ...]
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
                    # ── 注入虚拟持仓 ──
                    virt_pos = self.bookkeeper.get_positions(name)
                    if not virt_pos.empty:
                        strategy.positions = virt_pos
                    buy_list, sell_list = strategy.generate_signals()
                    for _, row in sell_list.iterrows():
                        all_sells.append((name, dict(row)))
                    for _, row in buy_list.iterrows():
                        all_buys.append((name, dict(row)))
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

        # ── 每策略独立过滤（只卖自己的持仓，不买自己已持有的）──
        filtered_sells = []  # [(strategy_name, sell_dict)]
        filtered_buys = []   # [(strategy_name, buy_dict)]
        skipped_buys = 0
        for sname, s in all_sells:
            code = _extract_code(s)
            held = self.bookkeeper.get_held_codes(sname)
            if code in held:
                filtered_sells.append((sname, s))
        for sname, b in all_buys:
            code = _extract_code(b)
            held = self.bookkeeper.get_held_codes(sname)
            all_held = self.bookkeeper.get_all_held_codes()
            if code in held:
                skipped_buys += 1  # 本策略已持有
            elif code in all_held:
                skipped_buys += 1  # 其他策略已持有
            else:
                filtered_buys.append((sname, b))

        if skipped_buys > 0:
            logger.info(f"  跳过 {skipped_buys} 只已持仓股票（虚拟簿记）")

        if failed_names:
            logger.warning(f"以下策略失败: {', '.join(failed_names)}，使用其余策略信号继续")
        logger.info(f"  卖出 {len(filtered_sells)} 只，买入 {len(filtered_buys)} 只（虚拟簿记过滤后）")
        if self.run_mode == "live" and self.api:
            self._execute(filtered_sells, filtered_buys, account_id=self.account_id)

    def _execute(self, sells, buys, account_id):
        """执行交易并更新虚拟簿记"""
        acc = account_id
        for sname, s in sells:
            code = _extract_code(s)
            price = s.get("price", 0)
            if not code or price <= 0:
                continue
            volume = 200 if code.startswith('689') else 100
            price = round(price, 3) if code[:2] in ('11','12','13','51','56','58','15','16','59','588') else round(price, 2)
            try:
                self.api.trade.sell(account_id=acc, code=code,
                    volume=volume, price=price, price_type="limit")
                # 虚拟簿记：扣减持仓
                if self.bookkeeper:
                    self.bookkeeper.record_sell(sname, code, volume, price)
                logger.info(f"  [卖出] {sname}: {code} @{price} vol={volume}")
            except Exception as e:
                logger.info(f"  [卖出失败] {sname}: {code}: {e}")
        for sname, b in buys:
            code = _extract_code(b)
            price = b.get("price", 0)
            if not code or price <= 0:
                continue
            volume = 200 if code.startswith('689') else 100
            price = round(price, 3) if code[:2] in ('11','12','13','51','56','58','15','16','59','588') else round(price, 2)
            try:
                self.api.trade.buy(account_id=acc, code=code,
                    volume=volume, price=price, price_type="limit")
                # 虚拟簿记：增加持仓
                if self.bookkeeper:
                    self.bookkeeper.record_buy(sname, code, volume, price)
                logger.info(f"  [买入] {sname}: {code} @{price} vol={volume}")
            except Exception as e:
                logger.info(f"  [买入失败] {sname}: {code}: {e}")

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

