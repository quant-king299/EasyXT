# -*- coding: utf-8 -*-
"""大QMT内置策略实时行情桥接 Provider。"""
from __future__ import annotations

import asyncio
import json
import os
import inspect
import threading
import time
from typing import Any, Dict, List

import websockets

from .base_provider import BaseDataProvider
from ...realtime_bridge.relay import normalize_symbol
from ...env_loader import load_project_env

load_project_env()


class BigQmtBridgeDataProvider(BaseDataProvider):
    """从大QMT桥接中继接收推送行情，不依赖 MiniQMT/xtquant。"""

    def __init__(self, config=None):
        super().__init__("big_qmt_bridge")
        config = config or {}
        configured_url = config.get("url")
        if not configured_url:
            configured_url = "ws://%s:%s" % (
                config.get("ws_host", "127.0.0.1"),
                config.get("ws_port", 18766),
            )
        self.url = os.getenv(
            "EASYXT_BIG_QMT_BRIDGE_URL",
            configured_url,
        )
        self.token = os.getenv("EASYXT_BIG_QMT_BRIDGE_TOKEN", config.get("token", ""))
        self.connect_timeout = float(config.get("connect_timeout", config.get("timeout", 3)))
        self.reconnect_delay = float(config.get("reconnect_delay", 2))
        self.stale_after = float(config.get("stale_after", 10))
        self._quotes: Dict[str, Dict[str, Any]] = {}
        self._health: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._thread = None
        self._last_message_time = 0.0
        self._loop = None
        self._websocket = None
        self.request_timeout = float(config.get("request_timeout", 2))

    def _connection_url(self) -> str:
        if not self.token:
            return self.url
        separator = "&" if "?" in self.url else "?"
        return "%s%stoken=%s" % (self.url, separator, self.token)

    def connect(self) -> bool:
        if self._thread and self._thread.is_alive():
            return self.is_available()
        self._stop.clear()
        self._ready.clear()
        self._thread = threading.Thread(
            target=self._thread_main,
            name="easyxt-big-qmt-bridge",
            daemon=True,
        )
        self._thread.start()
        self._ready.wait(self.connect_timeout)
        return self.is_available()

    def _thread_main(self):
        try:
            asyncio.run(self._receive_loop())
        except Exception as exc:
            self.logger.warning("大QMT行情桥接线程退出: %s", exc)
        finally:
            self.connected = False

    async def _receive_loop(self):
        self._loop = asyncio.get_running_loop()
        while not self._stop.is_set():
            try:
                connect_options = {
                    "ping_interval": 20, "ping_timeout": 10,
                    "open_timeout": self.connect_timeout,
                    "max_size": 4 * 1024 * 1024,
                }
                # websockets 15 会自动读取系统代理；本机桥接必须直连。
                if "proxy" in inspect.signature(websockets.connect).parameters:
                    connect_options["proxy"] = None
                async with websockets.connect(self._connection_url(), **connect_options) as websocket:
                    self._websocket = websocket
                    self.connected = True
                    self._last_message_time = time.time()
                    self._ready.set()
                    while not self._stop.is_set():
                        try:
                            raw = await asyncio.wait_for(websocket.recv(), timeout=1)
                        except asyncio.TimeoutError:
                            continue
                        self._handle_message(json.loads(raw))
            except Exception as exc:
                self.connected = False
                self._websocket = None
                self._ready.set()
                if not self._stop.is_set():
                    self.logger.debug("大QMT行情桥接等待重连: %s", exc)
                    await asyncio.sleep(self.reconnect_delay)

    def _handle_message(self, message: Dict[str, Any]):
        now = time.time()
        self._last_message_time = now
        message_type = message.get("type")
        with self._lock:
            if message_type == "welcome":
                self._health = dict(message.get("health") or {})
            elif message_type == "health":
                self._health = dict(message)
            elif message_type == "quotes":
                for quote in message.get("data") or []:
                    if not isinstance(quote, dict):
                        continue
                    symbol = normalize_symbol(quote.get("symbol") or quote.get("code"))
                    if symbol:
                        item = dict(quote)
                        item["symbol"] = symbol
                        self._quotes[symbol] = item

    def disconnect(self) -> None:
        self._stop.set()
        self.connected = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=max(2.0, self.reconnect_delay + 1))
        self._websocket = None
        self._loop = None

    def is_available(self) -> bool:
        return bool(
            self.connected
            and self._thread
            and self._thread.is_alive()
            and time.time() - self._last_message_time < max(10.0, self.stale_after * 2)
        )

    def get_realtime_quotes(self, codes: List[str]) -> List[Dict[str, Any]]:
        result = self._collect_quotes(codes)
        found = {item["code"] for item in result}
        missing = [normalize_symbol(code) for code in codes
                   if normalize_symbol(code) not in found]
        if missing and self.is_available() and self._loop and self._websocket:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._websocket.send(json.dumps({
                        "type": "snapshot", "symbols": missing,
                    })),
                    self._loop,
                )
                future.result(timeout=self.request_timeout)
                deadline = time.time() + self.request_timeout
                while time.time() < deadline:
                    result = self._collect_quotes(codes)
                    if all(symbol in {item["code"] for item in result}
                           for symbol in missing):
                        break
                    time.sleep(0.02)
            except Exception as exc:
                self.logger.debug("请求大QMT精确快照失败: %s", exc)
        return result

    def _collect_quotes(self, codes: List[str]) -> List[Dict[str, Any]]:
        now = time.time()
        result = []
        with self._lock:
            for raw_code in codes:
                symbol = normalize_symbol(raw_code)
                quote = self._quotes.get(symbol)
                if not quote:
                    continue
                received_at = float(quote.get("relay_receive_time") or 0)
                if not received_at or now - received_at > self.stale_after:
                    continue
                previous_close = float(quote.get("last_close") or quote.get("pre_close") or 0)
                price = float(quote.get("price") or quote.get("last_price") or 0)
                change = price - previous_close if previous_close else float(quote.get("change") or 0)
                change_pct = change / previous_close * 100 if previous_close else float(quote.get("change_pct") or 0)
                result.append({
                    "code": symbol,
                    "name": quote.get("name", ""),
                    "price": price,
                    "change": change,
                    "change_pct": change_pct,
                    "volume": quote.get("volume", 0),
                    "turnover": quote.get("amount", quote.get("turnover", 0)),
                    "timestamp": quote.get("market_time", quote.get("collector_time", received_at)),
                    "source": "big_qmt_bridge",
                    "sequence": quote.get("sequence"),
                    "bid_price": quote.get("bid_price", []),
                    "ask_price": quote.get("ask_price", []),
                    "bid_volume": quote.get("bid_volume", []),
                    "ask_volume": quote.get("ask_volume", []),
                    "stale": False,
                })
        return result

    def get_provider_info(self) -> Dict[str, Any]:
        info = super().get_provider_info()
        with self._lock:
            info.update({
                "supported_data_types": ["实时行情"],
                "url": self.url,
                "cached_quotes": len(self._quotes),
                "health": dict(self._health),
                "last_message_time": self._last_message_time,
            })
        return info
