# -*- coding: utf-8 -*-
"""BaoStock 历史数据源。

BaoStock 的 Python 客户端在进程内共享一个全局 socket，且请求/响应没有
线程隔离。本适配器因此用进程级可重入锁包住完整查询，并校验返回代码，
防止并发时把其他证券的数据静默写入缓存。
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd

from .base_source import BaseDataSource

logger = logging.getLogger(__name__)


class BaoStockSource(BaseDataSource):
    """通过 BaoStock 获取 A 股历史行情、估值快照和交易日历。"""

    _api_lock = threading.RLock()

    _PERIOD_MAP = {
        "1d": "d", "d": "d",
        "1w": "w", "w": "w",
        "1m": "m", "m": "m",
        "5m": "5", "5": "5",
        "15m": "15", "15": "15",
        "30m": "30", "30": "30",
        "60m": "60", "60": "60",
    }
    _ADJUST_MAP = {"none": "3", "qfq": "2", "hfq": "1", "3": "3", "2": "2", "1": "1"}
    _NUMERIC_COLUMNS = {
        "open", "high", "low", "close", "preclose", "volume", "amount",
        "turn", "pctChg", "peTTM", "pbMRQ", "psTTM", "pcfNcfTTM", "isST",
        "tradestatus", "adjustflag",
    }
    _FUNDAMENTAL_FIELDS = {"peTTM", "pbMRQ", "psTTM", "pcfNcfTTM", "turn", "isST"}
    _FUNDAMENTAL_ALIASES = {
        "pe": "peTTM", "pe_ttm": "peTTM",
        "pb": "pbMRQ", "pb_mrq": "pbMRQ",
        "ps": "psTTM", "ps_ttm": "psTTM",
        "pcf": "pcfNcfTTM", "pcf_ncf_ttm": "pcfNcfTTM",
    }

    def __init__(self, config: Dict, client=None):
        super().__init__(config)
        self._client = client
        self.timeout = float(config.get("timeout", 15))
        self.max_retries = max(0, int(config.get("max_retries", 1)))

    @staticmethod
    def _to_bs_symbol(symbol: str) -> str:
        value = str(symbol).strip().upper()
        if "." in value:
            code, suffix = value.split(".", 1)
            exchange = {"SH": "sh", "SS": "sh", "XSHG": "sh",
                        "SZ": "sz", "XSHE": "sz"}.get(suffix)
            if exchange and len(code) == 6 and code.isdigit():
                return f"{exchange}.{code}"
        if len(value) == 6 and value.isdigit():
            # 5/6/9 开头通常属于上海；0/1/2/3 开头通常属于深圳。
            if value.startswith(("5", "6", "9")):
                return f"sh.{value}"
            if value.startswith(("0", "1", "2", "3")):
                return f"sz.{value}"
        raise ValueError(f"不支持的证券代码: {symbol}")

    @staticmethod
    def _from_bs_symbol(symbol: str) -> str:
        exchange, code = str(symbol).lower().split(".", 1)
        return f"{code}.{'SH' if exchange == 'sh' else 'SZ'}"

    @staticmethod
    def _to_bs_date(value: str) -> str:
        return datetime.strptime(value, "%Y%m%d").strftime("%Y-%m-%d")

    def _load_client(self):
        if self._client is None:
            import baostock as bs
            self._client = bs
        return self._client

    def _set_socket_timeout_locked(self) -> None:
        """为原生客户端的全局 socket 增加超时；测试客户端不需要。"""
        try:
            import baostock.common.context as context
            sock = getattr(context, "default_socket", None)
            if sock is not None:
                sock.settimeout(self.timeout)
        except (ImportError, AttributeError, OSError):
            pass

    def connect(self) -> bool:
        try:
            client = self._load_client()
            with self._api_lock:
                result = client.login()
                self.is_connected = str(getattr(result, "error_code", "")) == "0"
                if self.is_connected:
                    self._connection = client
                    self._set_socket_timeout_locked()
                else:
                    logger.warning("[BaoStockSource] 登录失败: %s", getattr(result, "error_msg", ""))
            return self.is_connected
        except ImportError:
            logger.info("[BaoStockSource] baostock 模块未安装")
        except Exception as exc:
            logger.warning("[BaoStockSource] 连接失败: %s", exc)
        self._connection = None
        self.is_connected = False
        return False

    def _reset_connection_locked(self) -> bool:
        """关闭损坏的全局 socket 后重新登录，避免 logout 再次阻塞。"""
        try:
            import baostock.common.context as context
            sock = getattr(context, "default_socket", None)
            if sock is not None:
                sock.close()
            if hasattr(context, "default_socket"):
                context.default_socket = None
            if hasattr(context, "user_id"):
                delattr(context, "user_id")
        except (ImportError, AttributeError, OSError):
            pass
        self.is_connected = False
        self._connection = None
        result = self._load_client().login()
        self.is_connected = str(getattr(result, "error_code", "")) == "0"
        if self.is_connected:
            self._connection = self._client
            self._set_socket_timeout_locked()
        return self.is_connected

    def _query(self, request: Callable, expected_symbol: Optional[str] = None) -> Tuple[List[str], List[List[str]]]:
        """执行并完整消费 ResultSet；锁不能在分页读取完成前释放。"""
        last_error = ""
        with self._api_lock:
            for attempt in range(self.max_retries + 1):
                if not self.is_connected and not self._reset_connection_locked():
                    last_error = "无法登录 BaoStock"
                    continue
                try:
                    result = request()
                    if result is None:
                        raise RuntimeError("BaoStock 返回空 ResultSet")
                    error_code = str(getattr(result, "error_code", ""))
                    if error_code != "0":
                        raise RuntimeError(f"{error_code}: {getattr(result, 'error_msg', '')}")
                    fields = list(getattr(result, "fields", []) or [])
                    rows = []
                    while result.next():
                        rows.append(list(result.get_row_data()))
                    if str(getattr(result, "error_code", "")) != "0":
                        raise RuntimeError(
                            f"分页读取失败: {getattr(result, 'error_code', '')}: "
                            f"{getattr(result, 'error_msg', '')}"
                        )
                    if expected_symbol and rows and "code" in fields:
                        code_index = fields.index("code")
                        mismatches = {row[code_index] for row in rows if row[code_index] != expected_symbol}
                        if mismatches:
                            raise RuntimeError(
                                f"响应证券代码不一致: 请求 {expected_symbol}, 返回 {sorted(mismatches)}"
                            )
                    return fields, rows
                except Exception as exc:
                    last_error = str(exc)
                    logger.warning("[BaoStockSource] 查询失败（第 %s 次）: %s", attempt + 1, exc)
                    if attempt < self.max_retries:
                        self._reset_connection_locked()
            raise RuntimeError(last_error or "BaoStock 查询失败")

    @classmethod
    def _frame(cls, fields: List[str], rows: List[List[str]]) -> pd.DataFrame:
        df = pd.DataFrame(rows, columns=fields)
        if df.empty:
            return df
        if "code" in df.columns:
            df.rename(columns={"code": "symbol"}, inplace=True)
            df["symbol"] = df["symbol"].map(cls._from_bs_symbol)
        if "date" in df.columns:
            df["date"] = df["date"].str.replace("-", "", regex=False)
        for column in cls._NUMERIC_COLUMNS.intersection(df.columns):
            df[column] = pd.to_numeric(df[column], errors="coerce")
        return df

    def get_price(self, symbol: str, start_date: str, end_date: str,
                  period: str = "1d", adjust: str = "none") -> Optional[pd.DataFrame]:
        if not self.is_available():
            return None
        try:
            frequency = self._PERIOD_MAP[period.lower()]
            adjustflag = self._ADJUST_MAP[adjust.lower()]
            bs_symbol = self._to_bs_symbol(symbol)
            bs_start = self._to_bs_date(start_date)
            bs_end = self._to_bs_date(end_date)
            if datetime.strptime(end_date, "%Y%m%d") < datetime.strptime(start_date, "%Y%m%d"):
                raise ValueError("开始日期不能晚于结束日期")
            if frequency in {"d", "w", "m"}:
                fields = ("date,code,open,high,low,close,preclose,volume,amount,adjustflag,"
                          "turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST")
            else:
                fields = "date,time,code,open,high,low,close,volume,amount,adjustflag"
            columns, rows = self._query(
                lambda: self._client.query_history_k_data_plus(
                    bs_symbol, fields, start_date=bs_start, end_date=bs_end,
                    frequency=frequency, adjustflag=adjustflag
                ),
                expected_symbol=bs_symbol,
            )
            df = self._frame(columns, rows)
            if df.empty:
                return None
            cache_key = self.get_cache_key("price", symbol, start_date, end_date, period, adjust)
            self._cache[cache_key] = df.copy()
            self._last_used = datetime.now()
            return df
        except (KeyError, ValueError) as exc:
            logger.info("[BaoStockSource] 参数错误: %s", exc)
        except Exception as exc:
            logger.warning("[BaoStockSource] 获取行情失败 (%s): %s", symbol, exc)
        return None

    def get_fundamentals(self, symbols: List[str], date: str,
                         fields: Optional[List[str]] = None) -> Optional[pd.DataFrame]:
        """返回查询日可知的日频估值字段，不把未来财报倒灌到历史日期。"""
        if not self.is_available() or not symbols:
            return None
        try:
            end = datetime.strptime(date, "%Y%m%d")
        except ValueError:
            return None
        requested = list(fields or sorted(self._FUNDAMENTAL_FIELDS))
        requested_to_bs = {
            field: self._FUNDAMENTAL_ALIASES.get(field, field)
            for field in requested
        }
        selected = list(dict.fromkeys(
            field for field in requested_to_bs.values() if field in self._FUNDAMENTAL_FIELDS
        ))
        if not selected:
            return None
        query_fields = "date,code," + ",".join(selected)
        output = []
        for symbol in symbols:
            try:
                bs_symbol = self._to_bs_symbol(symbol)
                columns, rows = self._query(
                    lambda s=bs_symbol: self._client.query_history_k_data_plus(
                        s, query_fields,
                        start_date=(end - timedelta(days=10)).strftime("%Y-%m-%d"),
                        end_date=end.strftime("%Y-%m-%d"), frequency="d", adjustflag="3"
                    ), expected_symbol=bs_symbol,
                )
                frame = self._frame(columns, rows)
                if not frame.empty:
                    for requested_field, bs_field in requested_to_bs.items():
                        if requested_field != bs_field and bs_field in frame.columns:
                            frame[requested_field] = frame[bs_field]
                    output.append(frame.iloc[[-1]])
            except Exception as exc:
                logger.warning("[BaoStockSource] 获取估值失败 (%s): %s", symbol, exc)
        return pd.concat(output, ignore_index=True) if output else None

    def get_trading_dates(self, start_date: str, end_date: str) -> Optional[List[str]]:
        if not self.is_available():
            return None
        try:
            bs_start, bs_end = self._to_bs_date(start_date), self._to_bs_date(end_date)
            columns, rows = self._query(
                lambda: self._client.query_trade_dates(start_date=bs_start, end_date=bs_end)
            )
            frame = pd.DataFrame(rows, columns=columns)
            if frame.empty:
                return []
            return frame.loc[frame["is_trading_day"] == "1", "calendar_date"].str.replace(
                "-", "", regex=False
            ).tolist()
        except Exception as exc:
            logger.warning("[BaoStockSource] 获取交易日历失败: %s", exc)
            return None

    def is_available(self) -> bool:
        return bool(self.is_connected and self._connection is not None)

    def close(self):
        with self._api_lock:
            if self.is_connected and self._client is not None:
                try:
                    self._client.logout()
                except Exception as exc:
                    logger.warning("[BaoStockSource] 退出失败: %s", exc)
            self._connection = None
            self.is_connected = False
