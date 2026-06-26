#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚拟簿记系统 — 多策略共享账户的持仓隔离

原理：
  多个策略共享同一个 QMT 账户，无法物理隔离持仓。
  本模块在下单时记录每笔委托归属哪个策略，形成"虚拟持仓"。
  每个策略只看自己的持仓，策略 A 不能卖出策略 B 的标的。

用法：
  from strategies.virtual_bookkeeper import VirtualBookkeeper

  bk = VirtualBookkeeper()
  bk.record_buy("cb_double_low", "000001.SZ", 100, 10.50)
  positions = bk.get_positions("cb_double_low")  # → pd.DataFrame
"""

import json
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_BOOK_FILE = Path(__file__).parent / "scheduler" / "logs" / "virtual_book.json"


class VirtualBookkeeper:
    """虚拟簿记管理器"""

    def __init__(self, book_file: Optional[str] = None):
        self.book_file = Path(book_file) if book_file else DEFAULT_BOOK_FILE
        self.book_file.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    # ───── 持久化 ─────

    def _load(self) -> dict:
        if self.book_file.exists():
            try:
                return json.loads(self.book_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {"strategies": {}, "last_sync": None, "account_id": ""}

    def _save(self):
        self.data["last_sync"] = datetime.now().isoformat()
        self.book_file.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ───── 持仓查询 ─────

    def get_positions(self, strategy_name: str) -> pd.DataFrame:
        """
        获取某个策略的虚拟持仓

        Returns:
            DataFrame: columns=[code, volume, cost_price, market_value, last_buy]
        """
        holdings = self.data.get("strategies", {}).get(strategy_name, {})
        if not holdings:
            return pd.DataFrame(columns=["code", "volume", "cost_price", "market_value", "last_buy"])

        rows = []
        for code, info in holdings.items():
            rows.append({
                "code": code,
                "volume": info.get("volume", 0),
                "cost_price": info.get("cost", 0),
                "market_value": info.get("volume", 0) * info.get("cost", 0),
                "last_buy": info.get("last_buy", ""),
            })
        return pd.DataFrame(rows)

    def get_all_positions(self) -> Dict[str, pd.DataFrame]:
        """获取所有策略的虚拟持仓"""
        return {
            name: self.get_positions(name)
            for name in self.data.get("strategies", {})
        }

    def get_held_codes(self, strategy_name: str) -> set:
        """获取某策略持有的股票代码集合"""
        holdings = self.data.get("strategies", {}).get(strategy_name, {})
        return {code for code, info in holdings.items() if info.get("volume", 0) > 0}

    def get_all_held_codes(self) -> set:
        """获取所有策略合计持有的股票代码集合"""
        codes = set()
        for name in self.data.get("strategies", {}):
            codes |= self.get_held_codes(name)
        return codes

    # ───── 交易记录 ─────

    def record_buy(self, strategy_name: str, code: str, volume: int, price: float):
        """
        记录买入——虚拟持仓增加

        Args:
            strategy_name: 策略名称
            code: 股票代码（如 000001.SZ）
            volume: 买入数量（股）
            price: 成交价格
        """
        strategies = self.data.setdefault("strategies", {})
        holdings = strategies.setdefault(strategy_name, {})

        if code in holdings:
            old_vol = holdings[code].get("volume", 0)
            old_cost = holdings[code].get("cost", 0)
            new_vol = old_vol + volume
            # 加权平均成本
            new_cost = round((old_vol * old_cost + volume * price) / new_vol, 4)
            holdings[code]["volume"] = new_vol
            holdings[code]["cost"] = new_cost
        else:
            holdings[code] = {
                "volume": volume,
                "cost": round(price, 4),
                "last_buy": datetime.now().isoformat(),
            }

        self._save()
        logger.info(f"[簿记] {strategy_name} 买入 {code} {volume}股 @{price:.3f} → 持仓{holdings[code]['volume']}股")

    def record_sell(self, strategy_name: str, code: str, volume: int, price: float = 0):
        """
        记录卖出——虚拟持仓减少

        Args:
            strategy_name: 策略名称
            code: 股票代码
            volume: 卖出数量（股）
            price: 成交价格（可选，仅日志用）
        """
        holdings = self.data.get("strategies", {}).get(strategy_name, {})
        if code not in holdings:
            logger.warning(f"[簿记] {strategy_name} 尝试卖出未持有的 {code}，忽略")
            return

        old_vol = holdings[code].get("volume", 0)
        new_vol = max(0, old_vol - volume)

        if new_vol > 0:
            holdings[code]["volume"] = new_vol
        else:
            del holdings[code]

        self._save()
        logger.info(f"[簿记] {strategy_name} 卖出 {code} {min(volume, old_vol)}股 @{price:.3f} → 剩余{new_vol}股")

    def set_allocation(self, strategy_name: str, allocation: Dict[str, dict]):
        """
        直接设置某策略的完整持仓（用于初始导入或手工修正）

        Args:
            strategy_name: 策略名称
            allocation: {code: {"volume": int, "cost": float}}
        """
        self.data.setdefault("strategies", {})[strategy_name] = allocation
        self._save()

    # ───── 对账（与真实 QMT 账户同步）──

    MANUAL_STRATEGY = "_manual"  # 保留策略名：手工/外部买入的持仓

    def sync_from_account(self, real_positions: Dict[str, int]):
        """
        从真实 QMT 账户同步持仓到簿记。

        首次运行时，账户中原有的持仓会被归入 "_manual" 策略。
        后续所有策略的 get_all_held_codes() 都会包含这些手动持仓，
        从而避免重复买入。

        Args:
            real_positions: {code: volume} — QMT 账户的真实可用持仓
        """
        if not real_positions:
            return

        # 计算虚拟持仓合计（不含 _manual）
        virtual_totals = {}
        for name in self.data.get("strategies", {}):
            if name == self.MANUAL_STRATEGY:
                continue
            for code, info in self.data["strategies"][name].items():
                vol = info.get("volume", 0)
                virtual_totals[code] = virtual_totals.get(code, 0) + vol

        # 找出真实账户中有但虚拟簿记中没有的持仓 → 归入 _manual
        manual = self.data.setdefault("strategies", {}).setdefault(self.MANUAL_STRATEGY, {})
        new_manual = 0
        for code, real_vol in real_positions.items():
            virt_vol = virtual_totals.get(code, 0)
            if virt_vol <= 0 and real_vol > 0:
                # 虚拟簿记中没有此持仓 → 归入手动
                manual[code] = {
                    "volume": real_vol,
                    "cost": 0,  # 成本未知
                    "last_buy": "manual",
                }
                new_manual += 1
            elif real_vol > virt_vol:
                # 真实持仓多于虚拟 → 差值归入手动（可能手工加仓了）
                extra = real_vol - virt_vol
                manual[code] = {
                    "volume": extra,
                    "cost": 0,
                    "last_buy": "manual_extra",
                }
                new_manual += 1

        if new_manual > 0:
            self._save()
            logger.info(f"[簿记] 同步 {new_manual} 只手动/外部持仓到 '_manual' 策略")

        # 反向清理：真实账户已清仓但簿记还有的 → 从 _manual 清理
        cleaned = 0
        for code in list(manual.keys()):
            real_vol = real_positions.get(code, 0)
            if real_vol <= 0:
                del manual[code]
                cleaned += 1
        if cleaned > 0:
            self._save()
            logger.info(f"[簿记] 清理 {cleaned} 只已清仓的手动持仓")

    # ───── 汇总信息 ─────

    def summary(self) -> dict:
        """返回各策略持仓汇总"""
        result = {}
        for name in self.data.get("strategies", {}):
            holdings = self.data["strategies"][name]
            total_value = sum(
                info.get("volume", 0) * info.get("cost", 0)
                for info in holdings.values()
            )
            result[name] = {
                "positions": len(holdings),
                "total_value": round(total_value, 2),
                "codes": list(holdings.keys()),
            }
        return result

    def clear_strategy(self, strategy_name: str):
        """清空某个策略的虚拟持仓"""
        if strategy_name in self.data.get("strategies", {}):
            del self.data["strategies"][strategy_name]
            self._save()
            logger.info(f"[簿记] 已清空 {strategy_name} 的虚拟持仓")
