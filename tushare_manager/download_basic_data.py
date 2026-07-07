#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础数据下载模块（5000分专属）

提供4类基础设施级数据的下载：
1. 复权因子 (adj_factor) — 本地快速计算复权价格
2. 每日涨跌停价格 (stk_limit) — 打板/连板策略必需
3. 停复牌信息 (suspend_d) — 过滤停牌股，避免回测虚假信号
4. 申万行业分类+成分 (index_classify + index_member_all) — 行业中性化

用法:
    # 命令行
    python -m tushare_manager.download_basic_data --all
    python -m tushare_manager.download_basic_data --adj-factor --start 20230101
    python -m tushare_manager.download_basic_data --stk-limit --start 20230101
    python -m tushare_manager.download_basic_data --suspend --start 20230101
    python -m tushare_manager.download_basic_data --sw-industry

    # 代码调用
    from tushare_manager.download_basic_data import download_all_basic
    download_all_basic(start_date='20230101')
"""

import argparse
import time
import pandas as pd
import numpy as np
import duckdb
from datetime import datetime, timedelta
from typing import Optional, List, Callable
from pathlib import Path

try:
    from .tushare_config import TushareConfig
except ImportError:
    from tushare_config import TushareConfig


# ─── 工具函数 ──────────────────────────────────────────────

def _log(message: str, level: str = "INFO"):
    """统一日志输出"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    prefix = {"INFO": "  ", "WARN": "⚠️", "OK": "✅", "ERROR": "❌"}.get(level, "  ")
    print(f"[{timestamp}] [{level}] {prefix} {message}")


def _get_pro_api():
    """获取 tushare pro_api 实例"""
    import tushare as ts
    config = TushareConfig()
    token = config.token
    if not token:
        raise ValueError("未配置 Tushare Token，请在 .env 中设置 TUSHARE_TOKEN")
    ts.set_token(token)
    return ts.pro_api()


def _get_db_path(db_path: Optional[str] = None) -> str:
    """获取 DuckDB 路径"""
    if db_path:
        return db_path
    config = TushareConfig()
    return config.db_path


def _api_call_with_retry(api_func, max_retries: int = 3, delay: float = 0.05,
                         log_label: str = "") -> Optional[pd.DataFrame]:
    """
    带重试的 API 调用（适配 5000 积分用户，500次/分钟）

    Args:
        api_func: 无参 lambda，返回 DataFrame
        max_retries: 最大重试次数
        delay: 调用间隔（秒），5000分用户可设更短
        log_label: 日志标签
    """
    for attempt in range(max_retries):
        try:
            df = api_func()
            time.sleep(delay)
            if df is not None and not df.empty:
                return df
            return df  # 返回空 DataFrame 也正常（可能该日期无数据）
        except Exception as e:
            if attempt < max_retries - 1:
                _log(f"{log_label} 调用失败(重试 {attempt+1}/{max_retries}): {e}", "WARN")
                time.sleep(delay * 3)
            else:
                _log(f"{log_label} 调用失败: {e}", "ERROR")
                return None


def _ensure_table(conn, table_name: str, create_sql: str):
    """确保表存在"""
    try:
        conn.execute(f"SELECT COUNT(*) FROM {table_name} LIMIT 1")
    except Exception:
        conn.execute(create_sql)
        _log(f"已创建表 {table_name}")


def _upsert_by_date(conn, table_name: str, df: pd.DataFrame, date_col: str = 'trade_date'):
    """
    按日期批量写入（先删除该日期的旧数据再插入）

    Args:
        conn: DuckDB 连接
        table_name: 表名
        df: 要写入的数据
        date_col: 日期列名
    """
    if df is None or df.empty:
        return 0

    # 将日期列转为字符串用于 DELETE
    dates = df[date_col].unique().tolist()
    for d in dates:
        d_str = str(d)
        conn.execute(f"DELETE FROM {table_name} WHERE {date_col} = '{d_str}'")

    conn.execute(f"INSERT INTO {table_name} SELECT * FROM df")
    return len(df)


# ─── 获取交易日列表 ──────────────────────────────────────

def _get_trading_dates(pro, start_date: str, end_date: str) -> List[str]:
    """获取交易日列表"""
    df = pro.trade_cal(exchange='SSE', start_date=start_date, end_date=end_date, is_open='1')
    if df is None or df.empty:
        return []
    return df['cal_date'].tolist()


# ═══════════════════════════════════════════════════════════
# 1. 复权因子 adj_factor
# ═══════════════════════════════════════════════════════════

SQL_CREATE_ADJ_FACTOR = """
CREATE TABLE IF NOT EXISTS adj_factor (
    ts_code VARCHAR,
    trade_date DATE,
    adj_factor DOUBLE,
    PRIMARY KEY (ts_code, trade_date)
)
"""


def download_adj_factor(db_path: Optional[str] = None,
                        start_date: str = '20200101',
                        end_date: Optional[str] = None,
                        progress_callback: Optional[Callable] = None) -> dict:
    """
    下载复权因子数据

    按日期遍历（每次获取全市场），减少 API 调用次数。

    Args:
        db_path: DuckDB 路径
        start_date: 开始日期 (YYYYMMDD)
        end_date: 结束日期 (YYYYMMDD)，默认今天
        progress_callback: 进度回调 callback(current, total, message)

    Returns:
        {'total_dates': N, 'total_records': M, 'errors': [...]}
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')

    db_path = _get_db_path(db_path)
    _log(f"下载复权因子数据: {start_date} ~ {end_date}")

    pro = _get_pro_api()
    conn = duckdb.connect(db_path)
    _ensure_table(conn, 'adj_factor', SQL_CREATE_ADJ_FACTOR)

    # 获取交易日列表
    trading_dates = _get_trading_dates(pro, start_date, end_date)
    if not trading_dates:
        _log("未获取到交易日列表", "ERROR")
        conn.close()
        return {'total_dates': 0, 'total_records': 0, 'errors': []}

    # 检查已下载到哪天（增量）
    try:
        existing_max = conn.execute("SELECT MAX(trade_date) FROM adj_factor").fetchone()[0]
        if existing_max:
            existing_str = existing_str = pd.Timestamp(existing_max).strftime('%Y%m%d')
            # 从已下载的下一天开始
            filtered = [d for d in trading_dates if d > existing_str]
            skipped = len(trading_dates) - len(filtered)
            if skipped > 0:
                _log(f"增量下载：跳过已有 {skipped} 天，还需下载 {len(filtered)} 天")
            trading_dates = filtered
    except Exception:
        pass

    total_records = 0
    errors = []
    total = len(trading_dates)

    for i, trade_date in enumerate(trading_dates):
        if progress_callback:
            progress_callback(i + 1, total, f"下载复权因子 {trade_date}")

        df = _api_call_with_retry(
            lambda td=trade_date: pro.adj_factor(trade_date=td),
            log_label=f"adj_factor[{trade_date}]"
        )

        if df is not None and not df.empty:
            # 转换日期格式
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
            count = _upsert_by_date(conn, 'adj_factor', df, 'trade_date')
            total_records += count

        if (i + 1) % 50 == 0 or (i + 1) == total:
            _log(f"[{i+1}/{total}] 已下载 {total_records:,} 条复权因子")

    conn.close()
    _log(f"复权因子下载完成: {total_records:,} 条", "OK")
    return {'total_dates': total, 'total_records': total_records, 'errors': errors}


# ═══════════════════════════════════════════════════════════
# 1b. ETF 复权因子 fund_adj — 与股票共享 adj_factor 表
# ═══════════════════════════════════════════════════════════


def download_etf_adj_factor(db_path: Optional[str] = None,
                            start_date: str = '20200101',
                            end_date: Optional[str] = None,
                            progress_callback: Optional[Callable] = None) -> dict:
    """
    下载 ETF 复权因子数据（Tushare fund_adj 接口）

    按日期遍历（每次获取全市场 ETF），存入 adj_factor 表（与股票共用）。

    ETF 每年分红/拆分时复权因子会变化，回测需要本地 adj_factor 做复权计算。
    新增分红时只需增量下载新日期的行，历史行不变。

    Args:
        db_path: DuckDB 路径
        start_date: 开始日期 (YYYYMMDD)
        end_date: 结束日期 (YYYYMMDD)，默认今天
        progress_callback: 进度回调 callback(current, total, message)

    Returns:
        {'total_dates': N, 'total_records': M, 'errors': [...]}
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')

    db_path = _get_db_path(db_path)
    _log(f"下载 ETF 复权因子数据: {start_date} ~ {end_date}")

    pro = _get_pro_api()
    conn = duckdb.connect(db_path)
    _ensure_table(conn, 'adj_factor', SQL_CREATE_ADJ_FACTOR)

    # 获取交易日列表
    trading_dates = _get_trading_dates(pro, start_date, end_date)
    if not trading_dates:
        _log("未获取到交易日列表", "ERROR")
        conn.close()
        return {'total_dates': 0, 'total_records': 0, 'errors': []}

    # ETF fund_adj 增量：按 ts_code 粒度检测已有最新日期
    try:
        existing_map = {}
        rows = conn.execute(
            "SELECT ts_code, MAX(trade_date) FROM adj_factor WHERE ts_code LIKE '1%' OR ts_code LIKE '5%' OR ts_code LIKE '15%' OR ts_code LIKE '16%' OR ts_code LIKE '58%' GROUP BY ts_code"
        ).fetchall()
        for ts_code, max_date in rows:
            if max_date:
                existing_map[ts_code] = pd.Timestamp(max_date).strftime('%Y%m%d')
    except Exception:
        existing_map = {}

    total_records = 0
    errors = []
    total = len(trading_dates)

    for i, trade_date in enumerate(trading_dates):
        if progress_callback:
            progress_callback(i + 1, total, f"下载 ETF 复权因子 {trade_date}")

        # Tushare fund_adj: 按日期拉取全市场 ETF 复权因子
        # 不传 ts_code 参数则返回当日所有 ETF
        df = _api_call_with_retry(
            lambda td=trade_date: pro.fund_adj(trade_date=td),
            log_label=f"fund_adj[{trade_date}]"
        )

        if df is not None and not df.empty:
            # 只保留 adj_factor 表需要的列（丢弃 discount_rate）
            if 'discount_rate' in df.columns:
                df = df[['ts_code', 'trade_date', 'adj_factor']]
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
            count = _upsert_by_date(conn, 'adj_factor', df, 'trade_date')
            total_records += count

        if (i + 1) % 50 == 0 or (i + 1) == total:
            _log(f"[{i+1}/{total}] 已下载 {total_records:,} 条 ETF 复权因子")

    conn.close()
    _log(f"ETF 复权因子下载完成: {total_records:,} 条", "OK")
    return {'total_dates': total, 'total_records': total_records, 'errors': errors}


# ═══════════════════════════════════════════════════════════
# 2. 每日涨跌停价格 stk_limit
# ═══════════════════════════════════════════════════════════

SQL_CREATE_STK_LIMIT = """
CREATE TABLE IF NOT EXISTS stk_limit (
    ts_code VARCHAR,
    trade_date DATE,
    up_limit DOUBLE,
    down_limit DOUBLE,
    PRIMARY KEY (ts_code, trade_date)
)
"""


def download_stk_limit(db_path: Optional[str] = None,
                       start_date: str = '20200101',
                       end_date: Optional[str] = None,
                       progress_callback: Optional[Callable] = None) -> dict:
    """
    下载每日涨跌停价格

    按日期遍历（每次获取全市场）。

    Args:
        db_path: DuckDB 路径
        start_date: 开始日期 (YYYYMMDD)
        end_date: 结束日期 (YYYYMMDD)，默认今天
        progress_callback: 进度回调

    Returns:
        {'total_dates': N, 'total_records': M, 'errors': [...]}
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')

    db_path = _get_db_path(db_path)
    _log(f"下载涨跌停价格: {start_date} ~ {end_date}")

    pro = _get_pro_api()
    conn = duckdb.connect(db_path)
    _ensure_table(conn, 'stk_limit', SQL_CREATE_STK_LIMIT)

    trading_dates = _get_trading_dates(pro, start_date, end_date)
    if not trading_dates:
        _log("未获取到交易日列表", "ERROR")
        conn.close()
        return {'total_dates': 0, 'total_records': 0, 'errors': []}

    # 增量检查
    try:
        existing_max = conn.execute("SELECT MAX(trade_date) FROM stk_limit").fetchone()[0]
        if existing_max:
            existing_str = pd.Timestamp(existing_max).strftime('%Y%m%d')
            filtered = [d for d in trading_dates if d > existing_str]
            skipped = len(trading_dates) - len(filtered)
            if skipped > 0:
                _log(f"增量下载：跳过已有 {skipped} 天，还需下载 {len(filtered)} 天")
            trading_dates = filtered
    except Exception:
        pass

    total_records = 0
    errors = []
    total = len(trading_dates)

    for i, trade_date in enumerate(trading_dates):
        if progress_callback:
            progress_callback(i + 1, total, f"下载涨跌停价格 {trade_date}")

        df = _api_call_with_retry(
            lambda td=trade_date: pro.stk_limit(trade_date=td),
            log_label=f"stk_limit[{trade_date}]"
        )

        if df is not None and not df.empty:
            # 只保留需要的列
            cols = [c for c in ['ts_code', 'trade_date', 'up_limit', 'down_limit'] if c in df.columns]
            df = df[cols]
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
            count = _upsert_by_date(conn, 'stk_limit', df, 'trade_date')
            total_records += count

        if (i + 1) % 50 == 0 or (i + 1) == total:
            _log(f"[{i+1}/{total}] 已下载 {total_records:,} 条涨跌停数据")

    conn.close()
    _log(f"涨跌停价格下载完成: {total_records:,} 条", "OK")
    return {'total_dates': total, 'total_records': total_records, 'errors': errors}


# ═══════════════════════════════════════════════════════════
# 3. 停复牌信息 suspend_d
# ═══════════════════════════════════════════════════════════

SQL_CREATE_SUSPEND = """
CREATE TABLE IF NOT EXISTS suspend_info (
    ts_code VARCHAR,
    trade_date DATE,
    suspend_type VARCHAR,
    suspend_timing VARCHAR,
    PRIMARY KEY (ts_code, trade_date)
)
"""


def download_suspend(db_path: Optional[str] = None,
                     start_date: str = '20200101',
                     end_date: Optional[str] = None,
                     progress_callback: Optional[Callable] = None) -> dict:
    """
    下载停复牌信息（Tushare suspend_d 接口）

    按日期遍历（每次获取当日停牌股票）。

    Args:
        db_path: DuckDB 路径
        start_date: 开始日期 (YYYYMMDD)
        end_date: 结束日期 (YYYYMMDD)，默认今天
        progress_callback: 进度回调

    Returns:
        {'total_dates': N, 'total_records': M, 'errors': [...]}
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')

    db_path = _get_db_path(db_path)
    _log(f"下载停复牌信息: {start_date} ~ {end_date}")

    pro = _get_pro_api()
    conn = duckdb.connect(db_path)
    _ensure_table(conn, 'suspend_info', SQL_CREATE_SUSPEND)

    trading_dates = _get_trading_dates(pro, start_date, end_date)
    if not trading_dates:
        _log("未获取到交易日列表", "ERROR")
        conn.close()
        return {'total_dates': 0, 'total_records': 0, 'errors': []}

    # 增量检查
    try:
        existing_max = conn.execute("SELECT MAX(trade_date) FROM suspend_info").fetchone()[0]
        if existing_max:
            existing_str = pd.Timestamp(existing_max).strftime('%Y%m%d')
            filtered = [d for d in trading_dates if d > existing_str]
            skipped = len(trading_dates) - len(filtered)
            if skipped > 0:
                _log(f"增量下载：跳过已有 {skipped} 天，还需下载 {len(filtered)} 天")
            trading_dates = filtered
    except Exception:
        pass

    total_records = 0
    errors = []
    total = len(trading_dates)

    for i, trade_date in enumerate(trading_dates):
        if progress_callback:
            progress_callback(i + 1, total, f"下载停复牌信息 {trade_date}")

        df = _api_call_with_retry(
            lambda td=trade_date: pro.suspend_d(trade_date=td),
            log_label=f"suspend_d[{trade_date}]"
        )

        if df is not None and not df.empty:
            # API 返回: ts_code, trade_date, suspend_timing, suspend_type
            if 'trade_date' in df.columns:
                df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d', errors='coerce')
            df = df.dropna(subset=['trade_date'])

            if not df.empty:
                # 只保留需要的列
                cols = [c for c in ['ts_code', 'trade_date', 'suspend_type', 'suspend_timing'] if c in df.columns]
                df = df[cols]
                _upsert_by_date(conn, 'suspend_info', df, 'trade_date')
                total_records += len(df)

        if (i + 1) % 50 == 0 or (i + 1) == total:
            _log(f"[{i+1}/{total}] 已下载 {total_records:,} 条停复牌记录")

    conn.close()
    _log(f"停复牌信息下载完成: {total_records:,} 条", "OK")
    return {'total_dates': total, 'total_records': total_records, 'errors': errors}


# ═══════════════════════════════════════════════════════════
# 4. 申万行业分类 + 成分
# ═══════════════════════════════════════════════════════════

SQL_CREATE_SW_CLASSIFY = """
CREATE TABLE IF NOT EXISTS sw_classify (
    index_code VARCHAR PRIMARY KEY,
    industry_name VARCHAR,
    level VARCHAR,
    industry_code VARCHAR,
    is_pub VARCHAR
)
"""

SQL_CREATE_SW_MEMBER = """
CREATE TABLE IF NOT EXISTS sw_member (
    index_code VARCHAR,
    con_code VARCHAR,
    in_date DATE,
    out_date DATE,
    is_new VARCHAR,
    PRIMARY KEY (index_code, con_code)
)
"""


def download_sw_industry(db_path: Optional[str] = None,
                         progress_callback: Optional[Callable] = None) -> dict:
    """
    下载申万行业分类和成分股

    分两步：
    1. 下载行业分类（index_classify）— L1/L2 两级
    2. 下载每个行业的成分股（index_member_all）

    Args:
        db_path: DuckDB 路径
        progress_callback: 进度回调

    Returns:
        {'classify_count': N, 'member_count': M, 'errors': [...]}
    """
    db_path = _get_db_path(db_path)
    _log("下载申万行业分类数据")

    pro = _get_pro_api()
    conn = duckdb.connect(db_path)
    _ensure_table(conn, 'sw_classify', SQL_CREATE_SW_CLASSIFY)
    _ensure_table(conn, 'sw_member', SQL_CREATE_SW_MEMBER)

    # ─── 步骤1: 下载行业分类 ───
    all_classify = []
    for level in ['L1', 'L2']:
        if progress_callback:
            progress_callback(0, 2, f"下载申万 {level} 行业分类")

        df = _api_call_with_retry(
            lambda lv=level: pro.index_classify(level=lv, src='SW2021'),
            log_label=f"index_classify[{level}]"
        )
        if df is not None and not df.empty:
            df['level'] = level
            all_classify.append(df)
            _log(f"  {level}: {len(df)} 个行业")

    if not all_classify:
        _log("未获取到申万行业分类", "ERROR")
        conn.close()
        return {'classify_count': 0, 'member_count': 0, 'errors': ['no classify data']}

    classify_df = pd.concat(all_classify, ignore_index=True)

    # 标准化列名
    col_map = {}
    if 'industry_name' in classify_df.columns:
        pass  # 已有
    elif 'name' in classify_df.columns:
        col_map['name'] = 'industry_name'

    if 'index_code' not in classify_df.columns and 'code' in classify_df.columns:
        col_map['code'] = 'index_code'

    classify_df = classify_df.rename(columns=col_map)

    # 保存分类数据
    cols = [c for c in ['index_code', 'industry_name', 'level', 'industry_code', 'is_pub']
            if c in classify_df.columns]
    classify_df = classify_df[cols]

    conn.execute("DELETE FROM sw_classify")
    conn.execute("INSERT INTO sw_classify SELECT * FROM classify_df")
    _log(f"已保存 {len(classify_df)} 个申万行业分类", "OK")

    # ─── 步骤2: 下载成分股 ───
    index_codes = classify_df['index_code'].tolist()
    total_member = 0
    total = len(index_codes)

    for i, index_code in enumerate(index_codes):
        if progress_callback:
            progress_callback(i + 1, total, f"下载成分股 {index_code}")

        df = _api_call_with_retry(
            lambda ic=index_code: pro.index_member_all(index_code=ic),
            log_label=f"index_member[{index_code}]"
        )

        if df is not None and not df.empty:
            # 标准化列名
            col_map2 = {}
            if 'con_code' not in df.columns and 'con_ts_code' in df.columns:
                col_map2['con_ts_code'] = 'con_code'

            df = df.rename(columns=col_map2)

            # 转换日期
            for col in ['in_date', 'out_date']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], format='%Y%m%d', errors='coerce')

            # 只保留需要的列
            cols2 = [c for c in ['index_code', 'con_code', 'in_date', 'out_date', 'is_new']
                     if c in df.columns]
            df = df[cols2]

            if not df.empty:
                # 删除已有的该行业成分
                conn.execute(f"DELETE FROM sw_member WHERE index_code = '{index_code}'")
                conn.execute("INSERT INTO sw_member SELECT * FROM df")
                total_member += len(df)

        if (i + 1) % 10 == 0 or (i + 1) == total:
            _log(f"[{i+1}/{total}] 已下载 {total_member:,} 条成分股")

    conn.close()
    _log(f"申万行业数据下载完成: {len(classify_df)} 个行业, {total_member:,} 条成分股", "OK")
    return {'classify_count': len(classify_df), 'member_count': total_member, 'errors': []}


# ═══════════════════════════════════════════════════════════
# 5. 可转债强赎公告 cb_call
# ═══════════════════════════════════════════════════════════

SQL_CREATE_CB_CALL = """
CREATE TABLE IF NOT EXISTS cb_call (
    ts_code VARCHAR,
    ann_date DATE,
    call_type VARCHAR,
    is_call VARCHAR,
    call_date DATE,
    call_price DOUBLE,
    call_price_tax DOUBLE,
    call_vol DOUBLE,
    call_amount DOUBLE,
    payment_date DATE,
    call_reg_date DATE,
    PRIMARY KEY (ts_code, ann_date)
)
"""


def download_cb_call(db_path: Optional[str] = None,
                     start_date: str = '20200101',
                     end_date: Optional[str] = None,
                     progress_callback: Optional[Callable] = None) -> dict:
    """
    下载可转债强赎公告数据（Tushare cb_call 接口）

    用于回测时排除处于强赎危险区的转债：
    - is_call='已满足强赎条件' → 进入强赎区，应排除
    - is_call='公告提示强赎'   → 强赎预告，应排除
    - is_call='公告实施强赎'   → 已确定赎回，应排除
    - is_call='公告不强赎'     → 安全

    Args:
        db_path: DuckDB 路径
        start_date: 公告开始日期 (YYYYMMDD)
        end_date: 公告结束日期 (YYYYMMDD)，默认今天
        progress_callback: 进度回调

    Returns:
        {'total_records': N, 'errors': [...]}
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')

    db_path = _get_db_path(db_path)
    _log(f"下载可转债强赎公告数据: {start_date} ~ {end_date}")

    pro = _get_pro_api()
    conn = duckdb.connect(db_path)
    _ensure_table(conn, 'cb_call', SQL_CREATE_CB_CALL)

    total_records = 0
    errors = []

    # cb_call 数据量小（~2000条），按年分段下载即可
    current = datetime.strptime(start_date, '%Y%m%d')
    end_dt = datetime.strptime(end_date, '%Y%m%d')
    total_years = end_dt.year - current.year + 1

    for i in range(total_years):
        year = current.year + i
        seg_start = f'{year}0101'
        seg_end = f'{year}1231' if year < end_dt.year else end_date

        if progress_callback:
            progress_callback(i + 1, total_years, f"下载可转债强赎 {year}")

        df = _api_call_with_retry(
            lambda ss=seg_start, se=seg_end: pro.cb_call(start_date=ss, end_date=se),
            log_label=f"cb_call[{year}]"
        )

        if df is not None and not df.empty:
            # 转换日期列
            for col in ['ann_date', 'call_date', 'payment_date', 'call_reg_date']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], format='%Y%m%d', errors='coerce')

            # 只保留表结构需要的列
            table_cols = ['ts_code', 'ann_date', 'call_type', 'is_call',
                         'call_date', 'call_price', 'call_price_tax',
                         'call_vol', 'call_amount', 'payment_date', 'call_reg_date']
            cols_to_keep = [c for c in table_cols if c in df.columns]
            df = df[cols_to_keep]

            count = _upsert_by_date(conn, 'cb_call', df, 'ann_date')
            total_records += count

    conn.close()
    _log(f"可转债强赎公告下载完成: {total_records:,} 条", "OK")
    return {'total_records': total_records, 'errors': errors}


# ═══════════════════════════════════════════════════════════
# 6. 可转债转股进度 cb_share（用于检测下修）
# ═══════════════════════════════════════════════════════════

SQL_CREATE_CB_SHARE = """
CREATE TABLE IF NOT EXISTS cb_share (
    ts_code VARCHAR,
    publish_date DATE,
    end_date DATE,
    issue_size DOUBLE,
    convert_price_initial DOUBLE,
    convert_price DOUBLE,
    convert_val DOUBLE,
    convert_vol DOUBLE,
    convert_ratio DOUBLE,
    acc_convert_val DOUBLE,
    acc_convert_vol DOUBLE,
    acc_convert_ratio DOUBLE,
    remain_size DOUBLE,
    total_shares DOUBLE,
    PRIMARY KEY (ts_code, publish_date)
)
"""


def download_cb_share(db_path: Optional[str] = None,
                      progress_callback: Optional[Callable] = None) -> dict:
    """
    下载可转债转股进度数据（Tushare cb_share 接口，逐只下载）

    用于检测下修事件：convert_price 下降 → 下修发生。

    Args:
        db_path: DuckDB 路径
        progress_callback: 进度回调

    Returns:
        {'total_cb': N, 'total_records': M, 'errors': [...]}
    """
    db_path = _get_db_path(db_path)
    _log("下载可转债转股进度数据（逐只下载，用于检测下修）")

    pro = _get_pro_api()
    conn = duckdb.connect(db_path)
    _ensure_table(conn, 'cb_share', SQL_CREATE_CB_SHARE)

    # 从 cb_basic 获取转债列表
    try:
        codes = [r[0] for r in conn.execute(
            "SELECT ts_code FROM cb_basic ORDER BY ts_code"
        ).fetchall()]
    except Exception:
        _log("cb_basic 表不存在，请先下载可转债基本信息", "ERROR")
        conn.close()
        return {'total_cb': 0, 'total_records': 0, 'errors': ['cb_basic not found']}

    if not codes:
        _log("cb_basic 表为空", "WARN")
        conn.close()
        return {'total_cb': 0, 'total_records': 0, 'errors': []}

    _log(f"共 {len(codes)} 只可转债")

    total_records = 0
    errors = []
    total = len(codes)
    last_request_time = 0
    request_interval = 0.06  # ~1000次/分钟（5000积分）

    for i, ts_code in enumerate(codes):
        if progress_callback:
            progress_callback(i + 1, total, f"下载 {ts_code} 转股进度")

        # 限流
        elapsed = time.time() - last_request_time
        if elapsed < request_interval:
            time.sleep(request_interval - elapsed)

        try:
            df = _api_call_with_retry(
                lambda tc=ts_code: pro.cb_share(ts_code=tc),
                log_label=f"cb_share[{ts_code}]",
                max_retries=2
            )
            last_request_time = time.time()

            if df is not None and not df.empty:
                # 转换日期列
                for col in ['publish_date', 'end_date']:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], format='%Y%m%d', errors='coerce')

                # 只保留表结构需要的列
                table_cols = ['ts_code', 'publish_date', 'end_date', 'issue_size',
                             'convert_price_initial', 'convert_price',
                             'convert_val', 'convert_vol', 'convert_ratio',
                             'acc_convert_val', 'acc_convert_vol', 'acc_convert_ratio',
                             'remain_size', 'total_shares']
                cols_to_keep = [c for c in table_cols if c in df.columns]
                df = df[cols_to_keep]

                # 删除该 CB 的旧数据再插入（全量刷新）
                conn.execute("DELETE FROM cb_share WHERE ts_code = ?", [ts_code])
                conn.execute("INSERT INTO cb_share SELECT * FROM df")
                total_records += len(df)

        except Exception as e:
            errors.append(f"{ts_code}: {e}")

        if (i + 1) % 100 == 0 or (i + 1) == total:
            _log(f"[{i+1}/{total}] 已下载 {total_records:,} 条转股记录")

    conn.close()
    _log(f"可转债转股进度下载完成: {total_records:,} 条, {total} 只", "OK")
    return {'total_cb': total, 'total_records': total_records, 'errors': errors}


# ═══════════════════════════════════════════════════════════
# 一键下载全部
# ═══════════════════════════════════════════════════════════

def download_all_basic(db_path: Optional[str] = None,
                       start_date: str = '20200101',
                       end_date: Optional[str] = None,
                       progress_callback: Optional[Callable] = None) -> dict:
    """
    一键下载全部4类基础数据

    Args:
        db_path: DuckDB 路径
        start_date: 开始日期
        end_date: 结束日期
        progress_callback: 进度回调

    Returns:
        各数据类型的结果汇总
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')

    results = {}

    _log("=" * 60)
    _log("开始下载基础数据（5000分专属）")
    _log("=" * 60)

    # 1. 股票复权因子
    _log("\n[1/7] 股票复权因子")
    results['adj_factor'] = download_adj_factor(db_path, start_date, end_date, progress_callback)

    # 2. ETF 复权因子
    _log("\n[2/7] ETF 复权因子")
    results['etf_adj_factor'] = download_etf_adj_factor(db_path, start_date, end_date, progress_callback)

    # 3. 涨跌停价格
    _log("\n[3/7] 涨跌停价格")
    results['stk_limit'] = download_stk_limit(db_path, start_date, end_date, progress_callback)

    # 4. 停复牌信息
    _log("\n[4/7] 停复牌信息")
    results['suspend'] = download_suspend(db_path, start_date, end_date, progress_callback)

    # 5. 可转债强赎公告
    _log("\n[5/7] 可转债强赎公告")
    results['cb_call'] = download_cb_call(db_path, start_date, end_date, progress_callback)

    # 6. 可转债转股进度
    _log("\n[6/7] 可转债转股进度")
    results['cb_share'] = download_cb_share(db_path, progress_callback)

    # 7. 申万行业
    _log("\n[7/7] 申万行业分类")
    results['sw_industry'] = download_sw_industry(db_path, progress_callback)

    _log("\n" + "=" * 60)
    _log("全部基础数据下载完成！", "OK")
    _log("=" * 60)

    return results


# ─── 命令行入口 ──────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="下载基础数据（5000分专属）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m tushare_manager.download_basic_data --all
  python -m tushare_manager.download_basic_data --adj-factor --start 20230101
  python -m tushare_manager.download_basic_data --stk-limit --start 20230101
  python -m tushare_manager.download_basic_data --suspend --start 20230101
  python -m tushare_manager.download_basic_data --sw-industry
        """
    )

    parser.add_argument('--all', action='store_true', help='下载全部基础数据')
    parser.add_argument('--adj-factor', action='store_true', help='仅下载复权因子')
    parser.add_argument('--stk-limit', action='store_true', help='仅下载涨跌停价格')
    parser.add_argument('--suspend', action='store_true', help='仅下载停复牌信息')
    parser.add_argument('--sw-industry', action='store_true', help='仅下载申万行业分类')
    parser.add_argument('--start', default='20200101', help='开始日期 (YYYYMMDD，默认20200101)')
    parser.add_argument('--end', default=None, help='结束日期 (YYYYMMDD，默认今天)')
    parser.add_argument('--db-path', default=None, help='DuckDB 路径')

    args = parser.parse_args()

    # 默认下载全部
    if not any([args.all, args.adj_factor, args.stk_limit, args.suspend, args.sw_industry]):
        args.all = True

    start_time = time.time()

    if args.all:
        download_all_basic(db_path=args.db_path, start_date=args.start, end_date=args.end)
    else:
        if args.adj_factor:
            download_adj_factor(db_path=args.db_path, start_date=args.start, end_date=args.end)
        if args.stk_limit:
            download_stk_limit(db_path=args.db_path, start_date=args.start, end_date=args.end)
        if args.suspend:
            download_suspend(db_path=args.db_path, start_date=args.start, end_date=args.end)
        if args.sw_industry:
            download_sw_industry(db_path=args.db_path)

    elapsed = time.time() - start_time
    print(f"\n⏱ 总耗时: {elapsed/60:.1f} 分钟")


if __name__ == '__main__':
    main()
