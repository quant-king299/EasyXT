"""
可转债 & ETF 数据获取工具
========================

数据源: 东方财富公开 HTTP API（免费，无需注册）
"""

import pandas as pd
import numpy as np
import time
from typing import List, Optional

try:
    import requests
except ImportError:
    requests = None

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}


def _fetch_pages(url, params, rename_map, numeric_cols):
    """分页抓取东方财富列表数据"""
    all_items = []
    for page in range(1, 999):
        params['pn'] = str(page)
        try:
            resp = requests.get(url, params=params, timeout=15, headers=HEADERS)
            data = resp.json()
            if not data.get('data') or not data['data'].get('diff'):
                break
            batch = data['data']['diff']
            if not batch:
                break
            all_items.extend(batch)
            total = data['data'].get('total', 0)
            if len(all_items) >= total:
                print(f'    已获取 {len(all_items)}/{total} 条')
                break
            time.sleep(0.25)
        except Exception:
            if page == 1:
                time.sleep(1)
                continue
            break

    if not all_items:
        return pd.DataFrame()

    df = pd.DataFrame(all_items)
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


# ============================================================================
# 可转债
# ============================================================================

CB_RENAME = {
    'f12': 'bond_code', 'f14': 'bond_name',
    'f2': 'price', 'f3': 'pct_change', 'f26': 'list_date',
    'f232': 'stock_code', 'f234': 'stock_name',
    'f229': 'stock_price', 'f235': 'convert_price',
    'f236': 'convert_value',
    'f239': 'remain_year', 'f240': 'ytm',
    'f241': 'cb_volume', 'f237': 'bond_value',
    'f20': 'market_cap', 'f249': 'put_price',
}
CB_NUMERIC = ['price', 'cb_volume', 'stock_price', 'convert_price',
              'remain_year', 'convert_value', 'pct_change']


def get_cb_list() -> pd.DataFrame:
    """获取全市场可转债列表（分页，取全部）"""
    if requests is None:
        raise ImportError("pip install requests")

    params = {
        'pn': '1', 'pz': '100', 'po': '0', 'np': '1',
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': '2', 'invt': '2', 'fid': 'f3',
        'fs': 'b:MK0354',
        'fields': 'f2,f3,f12,f14,f20,f26,f229,f232,f234,f235,f236,f237,f239,f240,f241,f249',
    }

    df = _fetch_pages(
        'https://push2.eastmoney.com/api/qt/clist/get',
        params, CB_RENAME, CB_NUMERIC
    )

    # 溢价率自算：(price - convert_value) / convert_value * 100
    if 'price' in df.columns and 'convert_value' in df.columns:
        cv = df['convert_value'].replace(0, np.nan)
        df['premium_rt'] = np.where(cv.notna(), (df['price'] - cv) / cv * 100, np.nan)

    return df


def get_cb_from_duckdb(duckdb_path: str = None) -> pd.DataFrame:
    """
    从 DuckDB 读取可转债最新日行情（优先数据源，秒级）。

    需要先在 GUI 的 "Tushare下载 → 可转债数据" 中下载 cb_basic 和 cb_daily。

    返回列: bond_code, price, premium_rt, convert_value, stock_code, stock_name, list_date
    """
    try:
        import duckdb
        path = duckdb_path or 'D:/StockData/stock_data.ddb'
        con = duckdb.connect(path, read_only=True)

        tables = con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
        if 'cb_daily' not in [t[0] for t in tables]:
            con.close()
            return pd.DataFrame()

        # cb_daily: ts_code, trade_date, close, cb_value(转股价值), cb_over_rate(溢价率%),
        #           bond_value(纯债价值), bond_over_rate(纯债溢价率%)
        # cb_basic: ts_code, stk_code, stk_short_name, list_date, remain_size(剩余规模:亿元)
        latest = con.execute(
            "SELECT MAX(trade_date) FROM cb_daily"
        ).fetchone()[0]

        df = con.execute(f"""
            SELECT
                d.ts_code as bond_code,
                d.close as price,
                d.cb_over_rate as premium_rt,
                d.cb_value as convert_value,
                d.bond_value,
                b.stk_code as stock_code,
                b.stk_short_name as stock_name,
                b.list_date,
                b.remain_size as cb_volume
            FROM cb_daily d
            JOIN cb_basic b ON d.ts_code = b.ts_code
            WHERE d.trade_date = '{latest}'
        """).fetchdf()

        con.close()

        if not df.empty:
            # 去掉 .SH/.SZ 后缀方便匹配
            df['bond_code_short'] = df['bond_code'].str.replace('.SH', '').str.replace('.SZ', '')
            print(f'    [DuckDB] {len(df)} 只转债 (最新日期: {latest})')

        return df
    except Exception as e:
        return pd.DataFrame()


def filter_cb_pool(df, max_price=130, max_premium=50, exclude_high_price=True):
    """过滤可转债池"""
    pool = df.copy()
    if exclude_high_price:
        pool = pool[(pool['price'] >= 80) & (pool['price'] <= 500)]
    else:
        pool = pool[pool['price'] >= 80]
    pool = pool[pool['price'] <= max_price]
    if 'premium_rt' in pool.columns:
        pool = pool[pool['premium_rt'].between(-10, max_premium)]
    if 'remain_year' in pool.columns:
        pool = pool[pool['remain_year'] >= 0.5]
    return pool.reset_index(drop=True)


# ============================================================================
# ETF
# ============================================================================

ETF_RENAME = {
    'f12': 'fund_code', 'f14': 'fund_name',
    'f2': 'price', 'f3': 'pct_change',
    'f5': 'volume', 'f6': 'amount',
    'f15': 'high', 'f16': 'low', 'f17': 'open',
    'f18': 'pre_close', 'f20': 'market_cap',
    'f21': 'circulate_cap', 'f22': 'turnover_rate',
}
ETF_NUMERIC = ['price', 'pct_change', 'volume', 'amount', 'high', 'low',
               'open', 'pre_close', 'market_cap', 'turnover_rate']


def get_etf_list() -> pd.DataFrame:
    """获取全市场 ETF 列表"""
    if requests is None:
        raise ImportError("pip install requests")

    params = {
        'pn': '1', 'pz': '100', 'po': '0', 'np': '1',
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': '2', 'invt': '2', 'fid': 'f3',
        'fs': 'b:MK0021,b:MK0022,b:MK0023',
        'fields': 'f2,f3,f5,f6,f12,f14,f15,f16,f17,f18,f20,f21,f22',
    }

    return _fetch_pages(
        'https://push2.eastmoney.com/api/qt/clist/get',
        params, ETF_RENAME, ETF_NUMERIC
    )


def get_etf_premium(etf_code: str) -> Optional[float]:
    """获取单只 ETF 溢价率 (市场价 - IOPV) / IOPV * 100"""
    if requests is None:
        return None
    clean = etf_code.replace('.SH', '').replace('.SZ', '')
    secid = f'1.{clean}' if clean.startswith(('51','56','58','588')) else f'0.{clean}'
    try:
        resp = requests.get('https://push2.eastmoney.com/api/qt/stock/get', params={
            'secid': secid,
            'fields': 'f43,f44,f161,f171',
            'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
        }, timeout=10, headers=HEADERS)
        d = resp.json().get('data', {})
        iopv = float(d.get('f161') or d.get('f171') or 0)
        price = float(d.get('f43') or d.get('f44') or 0)
        return (price - iopv) / iopv * 100 if iopv > 0 and price > 0 else None
    except Exception:
        return None


def get_etf_from_duckdb(duckdb_path: str = None) -> pd.DataFrame:
    """
    从 DuckDB 读取 ETF 最新日行情。

    返回列: fund_code, price, pct_change, volume, amount
    """
    try:
        import duckdb
        path = duckdb_path or 'D:/StockData/stock_data.ddb'
        con = duckdb.connect(path, read_only=True)
        tables = con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
        if 'etf_daily' not in [t[0] for t in tables]:
            con.close()
            return pd.DataFrame()

        latest = con.execute("SELECT MAX(trade_date) FROM etf_daily").fetchone()[0]
        df = con.execute(f"""
            SELECT d.ts_code as fund_code,
                   d.close as price,
                   d.pct_chg as pct_change,
                   d.vol as volume,
                   d.amount as amount,
                   d.pre_close,
                   b.name as fund_name
            FROM etf_daily d
            LEFT JOIN etf_basic b ON d.ts_code = b.ts_code
            WHERE d.trade_date = '{latest}'
              AND d.close > 0
              AND d.amount > 0
        """).fetchdf()
        con.close()
        if not df.empty:
            print(f'    [DuckDB] {len(df)} 只 ETF (最新: {latest})')
        return df
    except Exception:
        return pd.DataFrame()


def get_etf_kline_from_duckdb(ts_code: str, count: int = 120) -> list:
    """从 DuckDB 获取单只 ETF 的 K 线 close 序列"""
    try:
        import duckdb
        con = duckdb.connect('D:/StockData/stock_data.ddb', read_only=True)
        rows = con.execute("""
            SELECT close FROM etf_daily
            WHERE ts_code = ? AND close > 0
            ORDER BY trade_date DESC LIMIT ?
        """, [ts_code, count]).fetchall()
        con.close()
        return [r[0] for r in rows[::-1]] if rows and len(rows) >= 30 else []
    except Exception:
        return []


def get_easyxt_api():
    try:
        from easy_xt import get_api
        api = get_api()
        api.init_data()
        return api
    except Exception:
        return None
