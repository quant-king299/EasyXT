#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EasyXT data-node HTTP service.

Run this on a Windows data node. The service is intentionally small: it exposes
read-only research data endpoints and keeps live trading out of the data layer.
"""

import os
import socket
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DUCKDB_PATH = os.environ.get("DUCKDB_PATH", "D:/StockData/stock_data.ddb")
DEFAULT_NODE_ID = os.environ.get("EASYXT_DATA_NODE_ID", "win_data_node_1")


def _normalize_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if "." in symbol:
        return symbol
    if symbol.startswith(("6", "5", "9")):
        return f"{symbol}.SH"
    return f"{symbol}.SZ"


def _date_for_duckdb(date: str) -> str:
    date = date.strip()
    if len(date) == 8 and date.isdigit():
        return f"{date[:4]}-{date[4:6]}-{date[6:]}"
    return date


def _df_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    clean = df.copy()
    clean = clean.where(pd.notnull(clean), None)
    return clean.to_dict(orient="records")


class DataNode:
    def __init__(self, node_id: str = DEFAULT_NODE_ID, duckdb_path: str = DEFAULT_DUCKDB_PATH):
        self.node_id = node_id
        self.duckdb_path = duckdb_path
        self.started_at = time.time()

    def health(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "node_id": self.node_id,
            "hostname": socket.gethostname(),
            "uptime_seconds": round(time.time() - self.started_at, 3),
            "duckdb_path": self.duckdb_path,
            "duckdb_exists": bool(self.duckdb_path and Path(self.duckdb_path).exists()),
            "sources": self.available_sources(),
        }

    def available_sources(self) -> List[str]:
        sources = []
        if self.duckdb_path and Path(self.duckdb_path).exists():
            sources.append("duckdb")
        try:
            from xtquant import xtdata  # noqa: F401

            sources.append("xtquant")
        except Exception:
            pass
        return sources

    def get_stock_list(self, sector: str = "沪深A股", source: str = "auto") -> List[str]:
        if source in ("auto", "xtquant"):
            try:
                from xtquant import xtdata

                return list(xtdata.get_stock_list_in_sector(sector))
            except Exception:
                if source == "xtquant":
                    raise

        if source in ("auto", "duckdb"):
            try:
                return self._stock_list_from_duckdb()
            except Exception:
                if source == "duckdb":
                    raise
                return []

        raise ValueError(f"Unsupported source: {source}")

    def get_bars(
        self,
        symbols: List[str],
        start_time: str = "",
        end_time: str = "",
        period: str = "1d",
        count: int = -1,
        source: str = "auto",
    ) -> Dict[str, List[Dict[str, Any]]]:
        symbols = [_normalize_symbol(s) for s in symbols]

        if source in ("auto", "duckdb") and period == "1d" and start_time and end_time:
            try:
                result = self._bars_from_duckdb(symbols, start_time, end_time)
                if result or source == "duckdb":
                    return result
            except Exception:
                if source == "duckdb":
                    raise

        if source in ("auto", "xtquant"):
            try:
                return self._bars_from_xtquant(symbols, start_time, end_time, period, count)
            except Exception:
                if source == "xtquant":
                    raise

        return {}

    def get_daily_table(
        self,
        category: str,
        start_time: str,
        end_time: str,
    ) -> List[Dict[str, Any]]:
        category_config = {
            "cb": {
                "table": "cb_daily",
                "code_col": "ts_code",
                "date_col": "trade_date",
                "extra_cols": (
                    "cb_value", "cb_over_rate", "bond_value", "bond_over_rate",
                    "vol", "amount", "pct_chg",
                ),
            },
            "etf": {
                "table": "etf_daily",
                "code_col": "ts_code",
                "date_col": "trade_date",
                "extra_cols": ("vol", "amount", "pct_chg"),
            },
            "stock": {
                "table": "stock_daily",
                "code_col": "stock_code",
                "date_col": "date",
                "extra_cols": ("volume", "amount"),
            },
        }
        if category not in category_config:
            raise ValueError(f"Unsupported category: {category}")

        cfg = category_config[category]
        start = _date_for_duckdb(start_time)
        end = _date_for_duckdb(end_time)
        extra = ", ".join(cfg["extra_cols"])
        query = f"""
            SELECT {cfg['code_col']} AS ts_code,
                   {cfg['date_col']} AS trade_date,
                   open, high, low, close,
                   {extra}
            FROM {cfg['table']}
            WHERE {cfg['date_col']} >= CAST(? AS DATE)
              AND {cfg['date_col']} <= CAST(? AS DATE)
              AND close > 0
            ORDER BY ts_code, {cfg['date_col']}
        """
        con = self._duckdb_connect()
        try:
            df = con.execute(query, [start, end]).fetchdf()
            return _df_records(df)
        finally:
            con.close()

    def get_cb_events(self, start_time: str = "", end_time: str = "") -> Dict[str, List[Dict[str, Any]]]:
        """读取可转债强赎与下修事件，供远程投研端按历史时点过滤。"""
        con = self._duckdb_connect()
        result: Dict[str, List[Dict[str, Any]]] = {"redemption": [], "down_revise": []}
        start = _date_for_duckdb(start_time) if start_time else "1900-01-01"
        end = _date_for_duckdb(end_time) if end_time else "2999-12-31"
        try:
            tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
            if "cb_call" in tables:
                result["redemption"] = _df_records(con.execute(
                    "SELECT ts_code, ann_date, is_call FROM cb_call "
                    "WHERE ann_date BETWEEN ? AND ? ORDER BY ts_code, ann_date",
                    [start, end],
                ).fetchdf())
            if "cb_share" in tables:
                result["down_revise"] = _df_records(con.execute(
                    "SELECT ts_code, publish_date, convert_price, prev_price FROM ("
                    "SELECT ts_code, publish_date, convert_price, "
                    "LAG(convert_price) OVER (PARTITION BY ts_code ORDER BY publish_date) AS prev_price "
                    "FROM cb_share) x WHERE convert_price < prev_price "
                    "AND publish_date BETWEEN ? AND ? ORDER BY ts_code, publish_date",
                    [start, end],
                ).fetchdf())
            return result
        finally:
            con.close()

    def _duckdb_connect(self):
        if not self.duckdb_path:
            raise RuntimeError("DUCKDB_PATH is not configured")
        if not Path(self.duckdb_path).exists():
            raise RuntimeError(f"DuckDB database does not exist: {self.duckdb_path}")
        import duckdb

        return duckdb.connect(self.duckdb_path, read_only=True)

    def _stock_list_from_duckdb(self) -> List[str]:
        con = self._duckdb_connect()
        try:
            queries = [
                "SELECT DISTINCT stock_code AS symbol FROM stock_daily ORDER BY stock_code",
                "SELECT DISTINCT ts_code AS symbol FROM etf_daily ORDER BY ts_code",
            ]
            stocks: List[str] = []
            for query in queries:
                try:
                    stocks.extend(con.execute(query).fetchdf()["symbol"].dropna().astype(str).tolist())
                except Exception:
                    continue
            return sorted(set(stocks))
        finally:
            con.close()

    def _bars_from_duckdb(
        self, symbols: List[str], start_time: str, end_time: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        con = self._duckdb_connect()
        start = _date_for_duckdb(start_time)
        end = _date_for_duckdb(end_time)
        placeholders = ", ".join(["?"] * len(symbols))
        params = symbols + [start, end] + symbols + [start, end]
        query = f"""
            SELECT stock_code AS symbol, date, open, high, low, close, volume, amount
            FROM stock_daily
            WHERE stock_code IN ({placeholders}) AND date >= ? AND date <= ?
            UNION ALL
            SELECT ts_code AS symbol, trade_date AS date, open, high, low, close,
                   vol AS volume, amount
            FROM etf_daily
            WHERE ts_code IN ({placeholders}) AND trade_date >= ? AND trade_date <= ?
            ORDER BY symbol, date
        """
        try:
            df = con.execute(query, params).fetchdf()
        except Exception:
            query = f"""
                SELECT stock_code AS symbol, date, open, high, low, close, volume, amount
                FROM stock_daily
                WHERE stock_code IN ({placeholders}) AND date >= ? AND date <= ?
                ORDER BY symbol, date
            """
            df = con.execute(query, symbols + [start, end]).fetchdf()
        finally:
            con.close()

        return {symbol: _df_records(group.drop(columns=["symbol"])) for symbol, group in df.groupby("symbol")}

    def _bars_from_xtquant(
        self,
        symbols: List[str],
        start_time: str,
        end_time: str,
        period: str,
        count: int,
    ) -> Dict[str, List[Dict[str, Any]]]:
        from xtquant import xtdata

        raw = xtdata.get_market_data_ex(
            field_list=[],
            stock_list=symbols,
            period=period,
            start_time=start_time,
            end_time=end_time,
            count=count,
            dividend_type="none",
            fill_data=True,
        )
        result: Dict[str, List[Dict[str, Any]]] = {}
        for symbol, df in (raw or {}).items():
            if df is None:
                result[symbol] = []
                continue
            item = df.reset_index()
            if "index" in item.columns and "date" not in item.columns:
                item = item.rename(columns={"index": "date"})
            result[symbol] = _df_records(item)
        return result


class BarsRequest(BaseModel):
    symbols: List[str]
    start_time: str = ""
    end_time: str = ""
    period: str = "1d"
    count: int = -1
    source: str = "auto"


node = DataNode()
app = FastAPI(title="EasyXT Data Node", version="0.1.0")


@app.get("/health")
def health() -> Dict[str, Any]:
    return node.health()


@app.get("/stocks")
def stocks(
    sector: str = Query("沪深A股"),
    source: str = Query("auto", pattern="^(auto|xtquant|duckdb)$"),
) -> Dict[str, Any]:
    try:
        data = node.get_stock_list(sector=sector, source=source)
        return {"sector": sector, "source": source, "count": len(data), "stocks": data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/bars")
def bars(req: BarsRequest) -> Dict[str, Any]:
    try:
        data = node.get_bars(
            symbols=req.symbols,
            start_time=req.start_time,
            end_time=req.end_time,
            period=req.period,
            count=req.count,
            source=req.source,
        )
        return {"source": req.source, "period": req.period, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/daily/{category}")
def daily(
    category: str,
    start_time: str = Query(...),
    end_time: str = Query(...),
) -> Dict[str, Any]:
    try:
        records = node.get_daily_table(category, start_time, end_time)
        return {
            "category": category,
            "start_time": start_time,
            "end_time": end_time,
            "count": len(records),
            "data": records,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/events/cb")
def cb_events(
    start_time: str = Query(""),
    end_time: str = Query(""),
) -> Dict[str, Any]:
    try:
        data = node.get_cb_events(start_time, end_time)
        return {"start_time": start_time, "end_time": end_time, **data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def main() -> None:
    import uvicorn

    host = os.environ.get("EASYXT_DATA_SERVICE_HOST", "0.0.0.0")
    port = int(os.environ.get("EASYXT_DATA_SERVICE_PORT", "18820"))
    discovery = None
    try:
        from .discovery import publish_service
        discovery = publish_service(os.environ.get("EASYXT_DATA_NODE_ID", DEFAULT_NODE_ID), port)
    except Exception:
        pass
    try:
        uvicorn.run("easy_xt.data_service.server:app", host=host, port=port, reload=False)
    finally:
        if discovery:
            try:
                discovery[0].unregister_service(discovery[1])
                discovery[0].close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
