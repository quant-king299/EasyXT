# -*- coding: utf-8 -*-
"""FTShare 免费版 HTTP 行情快照 Provider。"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List

from .base_provider import BaseDataProvider
from ...env_loader import load_project_env

load_project_env()


class FTShareDataProvider(BaseDataProvider):
    """按自选股列表轮询 FTShare 免费实时行情快照。"""

    def __init__(self, config=None):
        super().__init__("ftshare")
        config = config or {}
        self.api_key = os.getenv("FTSHARE_API_KEY", config.get("api_key", ""))
        self.base_url = os.getenv("FTSHARE_BASE_URL", config.get("base_url", "")) or None
        self.timeout = float(config.get("timeout", 15))
        self.batch_size = min(200, max(1, int(config.get("batch_size", 200))))
        self._client = None

    @staticmethod
    def _short_symbol(value: Any) -> str:
        return str(value or "").upper().replace(".XSHG", ".SH").replace(".XSHE", ".SZ").replace(".BJSE", ".BJ")

    @staticmethod
    def _long_symbol(value: Any) -> str:
        symbol = str(value or "").strip().upper()
        if "." not in symbol and len(symbol) == 6:
            suffix = "XSHG" if symbol.startswith(("5", "6", "9")) else "XSHE"
            symbol = f"{symbol}.{suffix}"
        return symbol.replace(".SH", ".XSHG").replace(".SZ", ".XSHE").replace(".BJ", ".BJSE")

    def connect(self) -> bool:
        if not self.api_key:
            self.logger.info("未配置 FTSHARE_API_KEY")
            return False
        try:
            import ftshare

            self._client = ftshare.market_api(
                api_key=self.api_key, base_url=self.base_url, timeout=self.timeout
            )
            self.connected = True
            return True
        except Exception as exc:
            self.logger.warning("FTShare初始化失败: %s", exc)
            self.connected = False
            return False

    def disconnect(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
        self._client = None
        self.connected = False

    def is_available(self) -> bool:
        return bool(self.connected and self._client is not None and self.api_key)

    def get_realtime_quotes(self, codes: List[str]) -> List[Dict[str, Any]]:
        if not self.is_available() or not codes:
            return []
        requested = list(dict.fromkeys(self._long_symbol(code) for code in codes))
        result = []
        for offset in range(0, len(requested), self.batch_size):
            batch = requested[offset:offset + self.batch_size]
            quoted = ",".join(f'"{symbol}"' for symbol in batch)
            frame = self._client.stock_daec_stocks(
                board="all", filter=f"symkey IN [{quoted}]", page_size=len(batch)
            )
            if frame is None or frame.empty:
                continue
            for row in frame.to_dict("records"):
                previous = float(row.get("prev_close") or 0)
                price = float(row.get("close") or 0)
                change = float(row.get("change") or (price - previous if previous else 0))
                change_rate = float(row.get("change_rate") or 0)
                result.append({
                    "code": self._short_symbol(row.get("symbol")),
                    "name": row.get("name") or "",
                    "price": price,
                    "change": change,
                    "change_pct": change_rate * 100,
                    "volume": int(row.get("volume") or 0),
                    "turnover": float(row.get("turnover") or 0),
                    "timestamp": float(row.get("ts_millis") or time.time() * 1000) / 1000,
                    "source": "ftshare",
                    "open": float(row.get("open") or 0),
                    "high": float(row.get("high") or 0),
                    "low": float(row.get("low") or 0),
                    "previous_close": previous,
                    "turnover_rate": row.get("turnover_rate"),
                    "market_cap": row.get("market_cap"),
                    "pe_ttm": row.get("pe_ttm"),
                    "stale": False,
                })
        return result

    def get_market_snapshot(self, scope: str = "ChinaStock") -> Dict[str, Any]:
        payload = self._client.stock_market(scope=scope, raw=True)
        return dict(payload.get("data") or {})

    def get_provider_info(self) -> Dict[str, Any]:
        info = super().get_provider_info()
        info.update({
            "supported_data_types": ["实时行情", "市场快照"],
            "mode": "HTTP轮询快照（非Tick推送）",
            "batch_size": self.batch_size,
        })
        return info
