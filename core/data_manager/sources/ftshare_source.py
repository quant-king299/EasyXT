# -*- coding: utf-8 -*-
"""FTShare 云行情数据源适配器。"""
from __future__ import annotations

import logging
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .base_source import BaseDataSource
from easy_xt.env_loader import load_project_env

load_project_env()

logger = logging.getLogger(__name__)


class FTShareSource(BaseDataSource):
    """通过官方 ``ftshare`` SDK 获取行情、日历和财务数据。"""

    _PERIOD_MAP = {
        "1m": ("minute", 1), "5m": ("minute", 5),
        "15m": ("minute", 15), "30m": ("minute", 30),
        "60m": ("minute", 60), "1d": ("day", 1),
        "1w": ("week", 1), "1mo": ("month", 1),
    }
    _ADJUST_MAP = {
        "none": "none", "qfq": "forward", "hfq": "backward",
        "forward": "forward", "backward": "backward",
    }
    _COLUMN_ALIASES = {
        "time": "date", "datetime": "date", "timestamp": "date", "ts_millis": "date",
        "ts": "date", "trade_date": "date", "code": "symbol",
        "trade_code": "symbol", "stock_code": "symbol",
        "vol": "volume", "turnover": "amount",
    }
    _FUNDAMENTAL_ALIASES = {
        "total_assets": "t_assets", "total_liabilities": "t_liability",
        "total_equity": "t_equity",
    }

    def __init__(self, config: Dict, client: Any = None):
        super().__init__(config)
        self._client = client
        self.api_key = config.get("api_key") or os.getenv("FTSHARE_API_KEY")
        self.base_url = config.get("base_url") or os.getenv("FTSHARE_BASE_URL") or None
        self.timeout = float(config.get("timeout", 15))

    def connect(self) -> bool:
        if self._client is not None:
            self._connection = self._client
            self.is_connected = True
            return True
        if not self.api_key:
            logger.info("[FTShareSource] 未配置 FTSHARE_API_KEY")
            return False
        try:
            import ftshare

            self._client = ftshare.market_api(
                api_key=self.api_key, base_url=self.base_url, timeout=self.timeout
            )
            self._connection = self._client
            self.is_connected = True
            return True
        except ImportError:
            logger.info("[FTShareSource] ftshare SDK 未安装")
        except Exception as exc:
            logger.warning("[FTShareSource] 初始化失败: %s", exc)
        self._connection = None
        self.is_connected = False
        return False

    @staticmethod
    def _to_millis(value: str, end_of_day: bool = False) -> int:
        suffix = " 23:59:59.999" if end_of_day else " 00:00:00"
        parsed = datetime.strptime(value + suffix, "%Y%m%d %H:%M:%S.%f" if end_of_day else "%Y%m%d %H:%M:%S")
        return int(parsed.timestamp() * 1000)

    @classmethod
    def _normalize_frame(cls, value: Any, symbol: Optional[str] = None) -> pd.DataFrame:
        if value is None:
            return pd.DataFrame()
        frame = value.copy() if isinstance(value, pd.DataFrame) else pd.DataFrame(value)
        if frame.empty:
            return frame
        frame.rename(
            columns={key: target for key, target in cls._COLUMN_ALIASES.items()
                     if key in frame.columns and target not in frame.columns},
            inplace=True,
        )
        if symbol and "symbol" not in frame.columns:
            frame["symbol"] = symbol
        if "date" in frame.columns:
            numeric = pd.to_numeric(frame["date"], errors="coerce")
            if numeric.notna().any() and numeric.dropna().abs().median() > 10_000_000_000:
                parsed_date = pd.to_datetime(numeric, unit="ms", errors="coerce")
            else:
                parsed_date = pd.to_datetime(frame["date"], errors="coerce")
            has_time = (parsed_date.dt.hour.ne(0) | parsed_date.dt.minute.ne(0)
                        | parsed_date.dt.second.ne(0))
            frame["date"] = parsed_date.dt.strftime("%Y%m%d")
            frame.loc[has_time, "date"] = parsed_date.loc[has_time].dt.strftime("%Y%m%d%H%M%S")
        for column in ("open", "high", "low", "close", "volume", "amount"):
            if column in frame.columns:
                frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return frame

    def get_price(self, symbol: str, start_date: str, end_date: str,
                  period: str = "1d", adjust: str = "none") -> Optional[pd.DataFrame]:
        if not self.is_available():
            return None
        try:
            unit, value = self._PERIOD_MAP[period.lower()]
            adjustment = self._ADJUST_MAP[adjust.lower()]
            normalized = self.normalize_symbol(symbol)
            start = pd.Timestamp(datetime.strptime(start_date, "%Y%m%d"))
            end = pd.Timestamp(datetime.strptime(end_date, "%Y%m%d"))
            if end < start:
                raise ValueError("开始日期不能晚于结束日期")
            chunks = []
            cursor = start
            while cursor <= end:
                if unit == "minute":
                    chunk_end = min(cursor + pd.Timedelta(days=2), end)
                    result = self._client.stock_minutes(
                        symbol=normalized, interval_value=value, adjust_kind=adjustment,
                        since_ts_millis=self._to_millis(cursor.strftime("%Y%m%d")),
                        until_ts_millis=self._to_millis(chunk_end.strftime("%Y%m%d"), end_of_day=True),
                        limit=1000,
                    )
                else:
                    chunk_end = min(cursor + pd.DateOffset(months=12) - pd.Timedelta(days=1), end)
                    result = self._client.stock_candlesticks(
                        symbol=normalized, interval_unit=unit, interval_value=value,
                        adjust_kind=adjustment,
                        since_ts_millis=self._to_millis(cursor.strftime("%Y%m%d")),
                        until_ts_millis=self._to_millis(chunk_end.strftime("%Y%m%d"), end_of_day=True),
                        limit=1000,
                    )
                frame = self._normalize_frame(result, normalized)
                if not frame.empty:
                    chunks.append(frame)
                cursor = chunk_end + pd.Timedelta(days=1)
            frame = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
            if "date" in frame.columns:
                if unit != "minute":
                    frame["date"] = frame["date"].astype(str).str[:8]
                frame.drop_duplicates(subset=["symbol", "date"], keep="last", inplace=True)
                frame.sort_values("date", inplace=True, ignore_index=True)
            if frame.empty:
                return None
            self._last_used = datetime.now()
            return frame
        except (KeyError, ValueError) as exc:
            logger.info("[FTShareSource] 参数错误: %s", exc)
        except Exception as exc:
            logger.warning("[FTShareSource] 获取行情失败 (%s): %s", symbol, exc)
        return None

    def get_realtime_kline(self, symbols: List[str], period: str = "1m") -> Optional[pd.DataFrame]:
        """获取官方实时分钟 K 或实时日 K；该接口不是 tick 逐笔。"""
        if not self.is_available() or not symbols:
            return None
        normalized = [self.normalize_symbol(symbol) for symbol in symbols]
        try:
            method = (self._client.stock_realtime_day_kline if period.lower() == "1d"
                      else self._client.stock_realtime_minute_kline)
            frame = self._normalize_frame(method(symbols=normalized))
            self._last_used = datetime.now()
            return None if frame.empty else frame
        except Exception as exc:
            logger.warning("[FTShareSource] 获取实时K线失败: %s", exc)
            return None

    def get_fundamentals(self, symbols: List[str], date: str,
                         fields: Optional[List[str]] = None) -> Optional[pd.DataFrame]:
        """获取单票资产负债表，并仅保留查询日之前已披露的记录。"""
        if not self.is_available() or not symbols:
            return None
        frames = []
        for symbol in symbols:
            normalized = self.normalize_symbol(symbol)
            try:
                frame = self._normalize_frame(
                    self._client.balance(stock_code=normalized, all_pages=True), normalized
                )
                if frame.empty:
                    continue
                date_columns = [c for c in ("announcement_date", "publish_date", "date") if c in frame.columns]
                if date_columns:
                    comparable = pd.to_datetime(frame[date_columns[0]], errors="coerce")
                    frame = frame.loc[comparable <= pd.to_datetime(date)]
                    frame = frame.assign(_known_date=comparable.loc[frame.index]).sort_values("_known_date")
                if frame.empty:
                    continue
                if fields:
                    for requested in fields:
                        actual = self._FUNDAMENTAL_ALIASES.get(requested, requested)
                        if actual in frame.columns and requested not in frame.columns:
                            converted = pd.to_numeric(frame[actual], errors="coerce")
                            frame[requested] = converted.where(converted.notna(), frame[actual])
                    selected = [c for c in ["symbol", *fields] if c in frame.columns]
                    frame = frame[selected]
                frames.append(frame.tail(1))
            except Exception as exc:
                logger.warning("[FTShareSource] 获取财务数据失败 (%s): %s", symbol, exc)
        return pd.concat(frames, ignore_index=True) if frames else None

    def get_trading_dates(self, start_date: str, end_date: str) -> Optional[List[str]]:
        if not self.is_available():
            return None
        try:
            response = self._client.trading_calendar(
                market="cn", start_date=start_date, end_date=end_date, raw=True
            )
            if isinstance(response, dict):
                dates = response.get("data", {}).get("trade_dates")
                if dates is not None:
                    return [str(value) for value in dates]
            frame = self._normalize_frame(response)
            if frame.empty:
                return []
            open_column = next((c for c in ("is_open", "is_trading_day", "open") if c in frame.columns), None)
            if open_column:
                frame = frame.loc[frame[open_column].astype(str).str.lower().isin({"1", "true", "yes"})]
            if "date" not in frame.columns:
                return None
            return frame["date"].astype(str).str[:8].tolist()
        except Exception as exc:
            logger.warning("[FTShareSource] 获取交易日历失败: %s", exc)
            return None

    def call(self, endpoint: str, **kwargs: Any) -> Any:
        """调用尚未封装进 EasyXT 统一接口的 FTShare SDK 方法。"""
        if not self.is_available() or endpoint.startswith("_"):
            raise RuntimeError("FTShare 数据源不可用或接口名非法")
        method = getattr(self._client, endpoint)
        if not callable(method):
            raise AttributeError(endpoint)
        return method(**kwargs)

    @staticmethod
    def _free_catalog_path() -> Path:
        return Path(__file__).resolve().parents[3] / "config" / "ftshare_free_endpoints.json"

    @classmethod
    def list_free_endpoints(cls, keyword: Optional[str] = None) -> List[Dict[str, Any]]:
        """读取本地保存的 FTShare 免费版接口清单。"""
        with cls._free_catalog_path().open("r", encoding="utf-8") as handle:
            endpoints = json.load(handle)["endpoints"]
        if not keyword:
            return endpoints
        needle = keyword.strip().lower()
        return [item for item in endpoints if needle in " ".join(
            str(item.get(key) or "") for key in ("title", "sdk_method", "path")
        ).lower()]

    def call_free(self, endpoint: str, **kwargs: Any) -> Any:
        """只允许调用本地清单内的免费接口，可传中文名或 SDK 方法名。"""
        matches = [item for item in self.list_free_endpoints()
                   if endpoint in (item.get("title"), item.get("sdk_method"))]
        if not matches:
            raise ValueError(f"接口不在 FTShare 免费版清单中: {endpoint}")
        return self.call(matches[0]["sdk_method"], **kwargs)

    def is_available(self) -> bool:
        return bool(self.is_connected and self._connection is not None)

    def close(self):
        if self._client is not None:
            try:
                self._client.close()
            except Exception as exc:
                logger.warning("[FTShareSource] 关闭连接失败: %s", exc)
        self._connection = None
        self.is_connected = False
