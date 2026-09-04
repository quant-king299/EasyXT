# -*- coding: utf-8 -*-
"""
通用向量化回测引擎

一次加载全量日线数据，逐日向量化过滤、选股、查价。
支持可转债 / ETF / 股票三类资产。
"""

import logging

logger = logging.getLogger(__name__)

import os
from pathlib import Path
import pandas as pd
import numpy as np
from .metrics import DEFAULT_RISK_FREE_RATE, annualized_return, annualized_sharpe
from typing import Callable, Dict, Any, List, Optional
from easyxt_backtest.research.universe import universe_as_of
from easyxt_backtest.research.audit import build_experiment_manifest

from config.env_config import get_default_db_path

DB_PATH = get_default_db_path()
DATA_MODE_DUCKDB_ONLY = 'duckdb_only'

# 各类资产配置
CATEGORY_CONFIG = {
    'cb': {
        'table': 'cb_daily',
        'code_col': 'ts_code',
        'date_col': 'trade_date',
        'extra_cols': ('cb_value', 'cb_over_rate', 'bond_value', 'bond_over_rate',
                       'vol', 'amount', 'pct_chg'),
        'trading_unit': 10,       # 可转债10张/手
        'default_min_price': 100,
        'default_max_price': 500,
        'fallback_sort_col': 'cb_over_rate',  # 策略失败时的兜底排序
        'limit_up_pct': 19.5,
        'limit_down_pct': -19.5,
    },
    'etf': {
        'table': 'etf_daily',
        'code_col': 'ts_code',
        'date_col': 'trade_date',
        'extra_cols': ('vol', 'amount', 'pct_chg'),
        'trading_unit': 100,
        'default_min_price': 0.5,
        'default_max_price': 10,
        'fallback_sort_col': 'pct_chg',
        'limit_up_pct': 9.5,
        'limit_down_pct': -9.5,
    },
    'stock': {
        'table': 'stock_daily',
        'code_col': 'stock_code',
        'date_col': 'date',
        'extra_cols': ('vol', 'amount'),
        'trading_unit': 100,
        'default_min_price': 1,
        'default_max_price': 9999,
        'fallback_sort_col': 'amount',  # 成交额排序
        'limit_up_pct': 9.5,
        'limit_down_pct': -9.5,
    },
}


class VectorizedBacktestEngine:
    """
    通用向量化回测引擎

    CB/ETF/股票共享同一套回测逻辑，仅数据源和交易参数不同。
    """

    def __init__(self, category: str = 'cb', db_path: str = None,
                 data_mode: str = DATA_MODE_DUCKDB_ONLY):
        if category not in CATEGORY_CONFIG:
            raise ValueError(f"不支持类别: {category}，可选: {list(CATEGORY_CONFIG.keys())}")
        if data_mode != DATA_MODE_DUCKDB_ONLY:
            raise ValueError("日线回测只支持 data_mode='duckdb_only'；"
                             "下载、实时行情和实盘交易请使用独立的数据接口")
        self.category = category
        self.cfg = CATEGORY_CONFIG[category]
        # This engine must never initialize DataAPI/xtquant.  It reads the
        # local DuckDB file, or the Data Node's /daily endpoint, which itself
        # is a read-only DuckDB query.
        self.data_mode = data_mode
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = DB_PATH

    def run_backtest(
        self,
        strategy_func: Callable,
        start_date: str,
        end_date: str,
        rebalance_days: int = 5,
        top_n: int = 20,
        commission: float = 0.001,
        slippage_bps: float = 5.0,
        max_participation_rate: float = 0.1,
        initial_cash: float = 100000.0,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        signal_lag_days: int = 1,
        universe_history: Optional[pd.DataFrame] = None,
        data_snapshot: str = "unversioned",
        universe_version: str = "data_default",
        risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
        **strategy_kwargs
    ) -> Dict[str, Any]:
        """
        Args:
            strategy_func: 策略函数 (df_day, top_n, **kwargs) -> List[str]
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            rebalance_days: 调仓频率（交易日数）
            top_n: 持仓数量
            commission: 单边交易费率
            initial_cash: 初始资金
            min_price: 最低价格过滤（None=用默认值）
            max_price: 最高价格过滤（None=用默认值）
            signal_lag_days: 信号到成交的交易日间隔，默认 1（T 日信号、T+1 成交）
        """
        if min_price is None:
            min_price = self.cfg['default_min_price']
        if max_price is None:
            max_price = self.cfg['default_max_price']
        if signal_lag_days != 1:
            raise ValueError("当前仅支持 signal_lag_days=1，以确保日线回测使用 T+1 成交")
        if slippage_bps < 0 or slippage_bps > 1000:
            raise ValueError("slippage_bps 必须在 0 到 1000 之间")
        if not 0 < max_participation_rate <= 1:
            raise ValueError("max_participation_rate 必须在 0 和 1 之间")

        # ── 加载全量日线数据 ──
        df = self._load_daily_data(start_date, end_date)
        if df.empty:
            return self._empty_result()

        df['trade_date'] = pd.to_datetime(df[self.cfg['date_col']])
        code_col = self.cfg['code_col']
        df.sort_values(['trade_date', code_col], inplace=True)
        # ── CB 强赎过滤 + 下修标记 ──
        if self.category == 'cb':
            df = self._filter_redemption_risk(df)
            df = self._mark_down_revise(df)

        trading_dates = sorted(df['trade_date'].unique())

        cash = initial_cash
        holdings: Dict[str, tuple] = {}  # code → (shares, buy_price)
        nav_list = []
        holdings_history = []
        trades = []
        rebalance_counter = 0
        pending_selected: Optional[List[str]] = None
        unit = self.cfg['trading_unit']

        for i, date in enumerate(trading_dates):
            day_df = df[df['trade_date'] == date].copy()
            if universe_history is not None:
                active_symbols = set(universe_as_of(universe_history, date))
                day_df = day_df[day_df[code_col].astype(str).isin(active_symbols)].copy()

            # 基本过滤
            mask = (day_df['close'] >= min_price) & (day_df['close'] <= max_price)
            if 'vol' in day_df.columns:
                mask &= (day_df['vol'] > 0)
            day_df_filtered = day_df[mask].copy()

            # 计算持仓市值
            holdings_value = 0.0
            for code, (shares, buy_price) in holdings.items():
                rows = day_df[day_df[code_col] == code]
                if not rows.empty:
                    holdings_value += shares * rows.iloc[0]['close']
                else:
                    holdings_value += shares * buy_price

            total_value = cash + holdings_value
            nav = total_value / initial_cash

            rebalance_counter += 1
            should_rebalance = (rebalance_counter >= rebalance_days) or (i == 0)

            # 执行上一交易日收盘后产生的信号；日线数据使用当日开盘价成交。
            if pending_selected is not None:
                cash, holdings = self._execute_rebalance(
                    day_df, pending_selected, holdings, cash, total_value, top_n,
                    commission, unit, trades, date, code_col, slippage_bps,
                    max_participation_rate,
                    self.cfg['limit_up_pct'], self.cfg['limit_down_pct'],
                )
                holdings_history.append((date, list(holdings.keys())))
                pending_selected = None
            # 当前日只产生信号，下一交易日才成交，避免收盘价未来函数。
            if should_rebalance and not day_df_filtered.empty:
                rebalance_counter = 0
                try:
                    selected = strategy_func(day_df_filtered, top_n=top_n, **strategy_kwargs)
                except Exception:
                    selected = []
                if not selected:
                    fallback = self.cfg['fallback_sort_col']
                    selected = (
                        day_df_filtered.nsmallest(top_n, fallback)[code_col].tolist()
                        if fallback in day_df_filtered.columns
                        else day_df_filtered.nsmallest(top_n, 'close')[code_col].tolist()
                    )
                pending_selected = selected[:top_n]

            # 成交完成后按收盘价重新估值，保证净值、现金和持仓状态一致。
            close_holdings_value = 0.0
            for code, (shares, buy_price) in holdings.items():
                rows = day_df[day_df[code_col] == code]
                if not rows.empty and pd.notna(rows.iloc[0].get('close')):
                    close_holdings_value += shares * float(rows.iloc[0]['close'])
                else:
                    close_holdings_value += shares * buy_price
            close_total_value = cash + close_holdings_value
            close_nav = close_total_value / initial_cash
            nav_list.append({
                'date': date, 'nav': close_nav, 'cash': cash,
                'holdings_value': close_holdings_value,
                'total_value': close_total_value, 'num_holdings': len(holdings)
            })

        result = self._build_result(
            nav_list, trades, holdings_history, initial_cash, risk_free_rate
        )
        result.setdefault('parameters', {})['signal_timing'] = 'close_to_next_open'
        result['parameters']['signal_lag_days'] = signal_lag_days
        result['parameters']['commission'] = commission
        result['parameters']['risk_free_rate'] = risk_free_rate
        result['parameters']['slippage_bps'] = slippage_bps
        result['parameters']['max_participation_rate'] = max_participation_rate
        result['parameters']['universe_mode'] = 'point_in_time' if universe_history is not None else 'data_default'
        result['experiment_manifest'] = build_experiment_manifest(
            expression=getattr(strategy_func, '__name__', 'callable_strategy'),
            data_snapshot=data_snapshot,
            universe_version=universe_version,
            parameters=result['parameters'],
            cost_model={
                'commission': commission,
                'slippage_bps': slippage_bps,
                'max_participation_rate': max_participation_rate,
            },
        )
        return result
    @staticmethod
    def _execute_rebalance(day_df, selected, holdings, cash, total_value, top_n, commission, unit, trades, date, code_col, slippage_bps=0.0, max_participation_rate=1.0, limit_up_pct=9.5, limit_down_pct=-9.5):
        """按当日开盘价执行前一交易日的目标持仓。"""
        price_col = 'open' if 'open' in day_df.columns else 'close'
        slip = slippage_bps / 10000.0
        for code in [c for c in holdings if c not in selected]:
            shares, buy_price = holdings[code]
            rows = day_df[day_df[code_col] == code]
            # 标的当天没有行情时视为停牌/数据缺失，不能伪造按买入价成交。
            if rows.empty:
                continue
            if not VectorizedBacktestEngine._can_sell(rows.iloc[0], limit_down_pct):
                continue
            sell_price = rows.iloc[0][price_col] if not rows.empty else buy_price
            sell_price *= (1 - slip)
            proceeds = shares * sell_price * (1 - commission)
            cash += proceeds
            trades.append({'date': date, 'code': code, 'action': 'sell', 'price': sell_price,
                           'shares': shares, 'amount': proceeds, 'pnl': (sell_price - buy_price) * shares})
            del holdings[code]
        for code in [c for c in selected if c not in holdings]:
            rows = day_df[day_df[code_col] == code]
            if rows.empty:
                continue
            row = rows.iloc[0]
            if not VectorizedBacktestEngine._can_buy(row, limit_up_pct):
                continue
            buy_price = rows.iloc[0][price_col]
            buy_price *= (1 + slip)
            if pd.isna(buy_price) or buy_price <= 0:
                continue
            budget = min(total_value / max(top_n, 1), cash)
            shares = int(budget / (buy_price * unit)) * unit
            cost = shares * buy_price * (1 + commission)
            if pd.notna(row.get('amount')) and row.get('amount', 0) > 0:
                capacity = float(row['amount']) * max_participation_rate
                shares = min(shares, int(capacity / (buy_price * unit)) * unit)
                cost = shares * buy_price * (1 + commission)
            if cost > cash:
                shares = int(cash / (buy_price * unit * (1 + commission))) * unit
                cost = shares * buy_price * (1 + commission)
            if shares > 0:
                cash -= cost
                holdings[code] = (shares, buy_price)
                trades.append({'date': date, 'code': code, 'action': 'buy', 'price': buy_price,
                               'shares': shares, 'amount': cost, 'pnl': 0})
        return cash, holdings
    @staticmethod
    def _can_buy(row, limit_up_pct: float = 9.5) -> bool:
        """检查停牌、无成交量和涨停导致的不可买入状态。"""
        if pd.isna(row.get('open')) or float(row.get('open', 0) or 0) <= 0:
            return False
        if 'vol' in row and pd.notna(row.get('vol')) and float(row.get('vol', 0) or 0) <= 0:
            return False
        pct = row.get('pct_chg')
        return not (pd.notna(pct) and float(pct) >= limit_up_pct)
    @staticmethod
    def _can_sell(row, limit_down_pct: float = -9.5) -> bool:
        """检查停牌、无成交量和跌停导致的不可卖出状态。"""
        if pd.isna(row.get('open')) or float(row.get('open', 0) or 0) <= 0:
            return False
        if 'vol' in row and pd.notna(row.get('vol')) and float(row.get('vol', 0) or 0) <= 0:
            return False
        pct = row.get('pct_chg')
        return not (pd.notna(pct) and float(pct) <= limit_down_pct)

    # ── 数据加载 ──

    def _load_daily_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """从 DuckDB 加载全量日线数据；不连接 xtquant。"""
        import duckdb
        s = f'{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}'
        e = f'{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}'
        label = {'cb': 'CB', 'etf': 'ETF', 'stock': '股票'}[self.category]
        table = self.cfg['table']
        code_col = self.cfg['code_col']
        date_col = self.cfg['date_col']
        extra = ', '.join(self.cfg['extra_cols'])

        con = None
        try:
            if not Path(self.db_path).exists():
                raise FileNotFoundError(f"DuckDB database does not exist: {self.db_path}")
            con = duckdb.connect(self.db_path, read_only=True)
            df = con.execute(f"""
                SELECT {code_col} AS ts_code, {date_col} AS trade_date,
                       open, high, low, close,
                       {extra}
                FROM {table}
                WHERE {date_col} >= DATE '{s}'
                  AND {date_col} <= DATE '{e}'
                  AND close > 0
                ORDER BY ts_code, {date_col}
            """).fetchdf()
            print(f"[{label}引擎] 加载 {table}: {len(df)} 行, "
                  f"{df['ts_code'].nunique()} 只标的, "
                  f"{df['trade_date'].nunique()} 个交易日")
            return df
        except Exception as e:
            logger.info(f"[{label}引擎] 数据加载失败: {e}")
            return self._load_daily_data_from_data_node(start_date, end_date, label)
        finally:
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass
    def _load_daily_data_from_data_node(self, start_date: str, end_date: str, label: str) -> pd.DataFrame:
        """从 Data Node 的 DuckDB-only /daily 端点加载日线数据。"""
        host = os.environ.get("EASYXT_DATA_NODE_HOST")
        port = os.environ.get("EASYXT_DATA_SERVICE_PORT", "18820")
        if not host and os.environ.get("EASYXT_DATA_NODE_DISCOVERY", "mdns").lower() == "mdns":
            try:
                from easy_xt.data_service.discovery import discover_service
                discovered = discover_service()
                if discovered:
                    host, port = discovered["host"], str(discovered["port"])
            except Exception:
                pass
        if not host:
            return pd.DataFrame()
        try:
            import requests
            session = requests.Session()
            session.trust_env = False
            url = f"http://{host}:{port}/daily/{self.category}"
            resp = session.get(
                url,
                params={"start_time": start_date, "end_time": end_date},
                timeout=120,
            )
            resp.raise_for_status()
            payload = resp.json()
            rows = payload.get("data", [])
            df = pd.DataFrame(rows)
            if not df.empty:
                df["trade_date"] = pd.to_datetime(df["trade_date"])
                df.sort_values(["ts_code", "trade_date"], inplace=True)
            print(f"[{label}引擎] 从 Data Node 加载: {len(df)} 行")
            return df
        except Exception as exc:
            logger.info(f"[{label}引擎] Data Node 加载失败: {exc}")
            return pd.DataFrame()
    def _filter_redemption_risk(self, df: pd.DataFrame) -> pd.DataFrame:
        """排除处于强赎危险区的可转债
        从 cb_call 表获取强赎状态，对每个交易日排除：
        - 已满足强赎条件
        - 公告提示强赎
        - 公告实施强赎
        只在状态为'公告不强赎'或之前处于安全状态时保留。
        Args:
            df: cb_daily DataFrame，含 ts_code, trade_date 列
        Returns:
            过滤后的 DataFrame
        """
        import duckdb
        try:
            con = duckdb.connect(self.db_path, read_only=True)
            # 检查 cb_call 表是否存在
            exists = con.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'cb_call'"
            ).fetchone()[0] > 0
            if not exists:
                con.close()
                return df
            calls = con.execute("""
                SELECT ts_code, ann_date, is_call
                FROM cb_call
                WHERE call_type = '强赎'
                ORDER BY ts_code, ann_date
            """).fetchdf()
            con.close()
            if calls.empty:
                return df
            # 定义需要排除的状态
            danger_statuses = {'已满足强赎条件', '公告提示强赎', '公告实施强赎'}
            # 按转债分组，对每个交易日构建状态时间线
            # 简化方案：取每个 CB 最早的强赎危险公告日期，从该日期起排除
            # 如果后续有"公告不强赎"，则从该日期起恢复安全
            excluded_set = set()
            for ts_code, group in calls.groupby('ts_code'):
                group = group.sort_values('ann_date')
                is_danger = False
                danger_start = None
                for _, row in group.iterrows():
                    if row['is_call'] in danger_statuses:
                        if not is_danger:
                            is_danger = True
                            danger_start = row['ann_date']
                    elif row['is_call'] == '公告不强赎':
                        if is_danger:
                            # 记录排除区间
                            excluded_set.add((ts_code, danger_start, row['ann_date']))
                            is_danger = False
                # 如果结束时仍在危险区，排除到数据结束日
                if is_danger and danger_start is not None:
                    excluded_set.add((ts_code, danger_start, pd.Timestamp.max))
            # 过滤 DataFrame
            if excluded_set:
                before_count = len(df)
                original_shape = len(df)
                mask = pd.Series(True, index=df.index)
                for ts_code, start, end in excluded_set:
                    code_mask = (df['ts_code'] == ts_code) & \
                                (df['trade_date'] >= start)
                    if end is not pd.Timestamp.max:
                        code_mask = code_mask & (df['trade_date'] <= end)
                    mask = mask & ~code_mask
                df = df[mask]
                removed = original_shape - len(df)
                if removed > 0:
                    unique_excluded = len(set(c[0] for c in excluded_set))
                    print(f"[CB引擎] 强赎过滤: 排除 {removed} 行 ({unique_excluded} 只转债)")
            return df
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"[CB引擎] 强赎过滤异常，降级为不过滤: {e}")
            return self._filter_redemption_from_remote(df)
    def _mark_down_revise(self, df: pd.DataFrame) -> pd.DataFrame:
        """标记可转债下修事件
        从 cb_share 表检测转股价下降日期，在 DataFrame 中增加
        'days_since_down_revise' 列：
        - NaN: 从未下修
        - 0: 当天发生下修
        - N: 最近一次下修是 N 天前
        策略可通过此列过滤或加权：
        - 下修后转股价值跳升，短期内可能有机会
        - 策略可设置阈值如 days_since_down_revise <= 60
        """
        import duckdb
        try:
            con = duckdb.connect(self.db_path, read_only=True)
            exists = con.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'cb_share'"
            ).fetchone()[0] > 0
            if not exists:
                con.close()
                df['days_since_down_revise'] = float('nan')
                return df
            # 检测每次 convert_price 下降（下修事件）
            down = con.execute("""
                SELECT ts_code, publish_date
                FROM (
                    SELECT ts_code, publish_date, convert_price,
                           LAG(convert_price) OVER (PARTITION BY ts_code ORDER BY publish_date) AS prev_price
                    FROM cb_share
                ) sub
                WHERE convert_price < prev_price
                ORDER BY ts_code, publish_date
            """).fetchdf()
            con.close()
            if down.empty:
                df['days_since_down_revise'] = float('nan')
                return df
            # 将下修日期转为 dict: ts_code -> [date1, date2, ...]
            down['publish_date'] = pd.to_datetime(down['publish_date'])
            revise_dates = down.groupby('ts_code')['publish_date'].apply(list).to_dict()
            df = df.copy()
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df['days_since_down_revise'] = float('nan')
            for ts_code, dates in revise_dates.items():
                mask = df['ts_code'] == ts_code
                if not mask.any():
                    continue
                code_df = df.loc[mask]
                # 对每个交易日，找最近的下修日期
                for trade_dt in code_df['trade_date'].unique():
                    prior_revises = [d for d in dates if d <= trade_dt]
                    if prior_revises:
                        days = (trade_dt - max(prior_revises)).days
                        df.loc[(df['ts_code'] == ts_code) & (df['trade_date'] == trade_dt),
                               'days_since_down_revise'] = days
            marked = df['days_since_down_revise'].notna().sum()
            if marked > 0:
                print(f"[CB引擎] 下修标记: {marked} 行已标记 ({len(revise_dates)} 只转债有过下修)")
            return df
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"[CB引擎] 下修标记异常，降级为不标记: {e}")
            return self._mark_down_revise_from_remote(df)
    def _get_remote_cb_events(self) -> Dict[str, List[Dict[str, Any]]]:
        """从 Windows 数据节点读取可转债公司行为事件。"""
        host = os.environ.get("EASYXT_DATA_NODE_HOST")
        port = os.environ.get("EASYXT_DATA_SERVICE_PORT", "18820")
        if not host and os.environ.get("EASYXT_DATA_NODE_DISCOVERY", "mdns").lower() == "mdns":
            try:
                from easy_xt.data_service.discovery import discover_service
                discovered = discover_service()
                if discovered:
                    host, port = discovered["host"], str(discovered["port"])
            except Exception:
                pass
        if not host:
            return {"redemption": [], "down_revise": []}
        import requests
        session = requests.Session()
        session.trust_env = False
        response = session.get(
            f"http://{host}:{port}/events/cb",
            params={"start_time": "19000101", "end_time": "29991231"},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        return {
            "redemption": payload.get("redemption", []),
            "down_revise": payload.get("down_revise", []),
        }
    def _filter_redemption_from_remote(self, df: pd.DataFrame) -> pd.DataFrame:
        try:
            events = self._get_remote_cb_events().get("redemption", [])
            if not events:
                return df
            event_df = pd.DataFrame(events)
            event_df["ann_date"] = pd.to_datetime(event_df["ann_date"])
            danger = event_df[event_df["is_call"].astype(str).isin(
                ["已满足强赎条件", "公告提示强赎", "公告实施强赎", "强赎"]
            )]
            if danger.empty:
                return df
            out = df.copy()
            out["trade_date"] = pd.to_datetime(out["trade_date"])
            for _, event in danger.iterrows():
                out = out[~((out["ts_code"] == event["ts_code"]) &
                            (out["trade_date"] >= event["ann_date"]))]
            return out
        except Exception as exc:
            logger.warning("远程强赎事件读取失败，保留原始数据: %s", exc)
            return df
    def _mark_down_revise_from_remote(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["days_since_down_revise"] = float("nan")
        try:
            events = self._get_remote_cb_events().get("down_revise", [])
            if not events:
                return out
            event_df = pd.DataFrame(events)
            event_df["publish_date"] = pd.to_datetime(event_df["publish_date"])
            out["trade_date"] = pd.to_datetime(out["trade_date"])
            for code, group in event_df.groupby("ts_code"):
                dates = group["publish_date"].tolist()
                mask = out["ts_code"] == code
                for idx in out.index[mask]:
                    prior = [d for d in dates if d <= out.at[idx, "trade_date"]]
                    if prior:
                        out.at[idx, "days_since_down_revise"] = (
                            out.at[idx, "trade_date"] - max(prior)
                        ).days
            return out
        except Exception as exc:
            logger.warning("远程下修事件读取失败，保留未标记结果: %s", exc)
            return out
    # ── 结果构建 ──

    def _build_result(self, nav_list: list, trades: list,
                      holdings_history: list,
                      initial_cash: float,
                      risk_free_rate: float = DEFAULT_RISK_FREE_RATE) -> Dict[str, Any]:
        nav_df = pd.DataFrame(nav_list)
        if nav_df.empty:
            return self._empty_result()

        nav_df.set_index('date', inplace=True)
        nav_df['daily_return'] = nav_df['nav'].pct_change().fillna(0)

        return {
            'nav_curve': nav_df,
            'metrics': self._calc_metrics(nav_df, initial_cash, risk_free_rate),
            'holdings_history': holdings_history,
            'trades': trades,
        }

    @staticmethod
    def _calc_metrics(nav_df: pd.DataFrame, initial_cash: float,
                      risk_free_rate: float = DEFAULT_RISK_FREE_RATE) -> dict:
        if nav_df.empty or len(nav_df) < 2:
            return {}

        total_days = len(nav_df)
        final_nav = nav_df['nav'].iloc[-1]
        total_return = final_nav - 1
        annual_return = annualized_return(total_return, total_days)

        cummax = nav_df['nav'].cummax()
        drawdown = (nav_df['nav'] - cummax) / cummax
        max_drawdown = drawdown.min()

        sharpe = annualized_sharpe(nav_df['daily_return'], risk_free_rate)

        calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        win_rate = (nav_df['daily_return'] > 0).sum() / total_days

        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe,
            'calmar_ratio': calmar,
            'win_rate': win_rate,
            'total_days': total_days,
            'initial_cash': initial_cash,
            'final_value': nav_df['total_value'].iloc[-1],
        }

    def _empty_result(self) -> Dict[str, Any]:
        return {
            'nav_curve': pd.DataFrame(),
            'metrics': {},
            'holdings_history': [],
            'trades': [],
        }


# 向后兼容别名
CBBactestEngine = lambda **kw: VectorizedBacktestEngine(category='cb', **kw)
ETFBacktestEngine = lambda **kw: VectorizedBacktestEngine(category='etf', **kw)
StockBacktestEngine = lambda **kw: VectorizedBacktestEngine(category='stock', **kw)
