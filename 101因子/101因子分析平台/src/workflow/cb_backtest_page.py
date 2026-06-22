# -*- coding: utf-8 -*-
"""
统一策略回测 - Streamlit 页面
支持 可转债 / ETF / 股票 三类策略，自动匹配数据源
"""

import sys
import os
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import numpy as np
import duckdb

# 路径
src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_root = os.path.dirname(src_path)
easyxt_root = os.path.dirname(project_root)
if src_path not in sys.path:
    sys.path.insert(0, src_path)
if easyxt_root not in sys.path:
    sys.path.insert(0, easyxt_root)

from cb_backtest.cb_data_manager import CBDataManager
from cb_backtest.cb_backtest_engine import CBBactestEngine
from cb_backtest.cb_strategies import STRATEGY_REGISTRY as BUILTIN_CB_REGISTRY
from ..strategies import get_merged_registry, list_strategies_by_category

DB_PATH = 'D:/StockData/stock_data.ddb'


def _check_data():
    """检查各类数据是否可用"""
    status = {}
    try:
        con = duckdb.connect(DB_PATH, read_only=True)
        tables = [t[0] for t in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()]
        status['cb'] = 'cb_daily' in tables and 'cb_basic' in tables
        status['etf'] = 'etf_daily' in tables
        status['stock'] = 'stock_daily' in tables
        con.close()
    except Exception:
        status = {'cb': False, 'etf': False, 'stock': False}

    try:
        mgr = CBDataManager()
        s, e = mgr.get_available_date_range()
        status['cb_range'] = f"{s} ~ {e}"
    except Exception:
        status['cb_range'] = None

    return status


def _run_cb_backtest(strategy_func, start_date, end_date, top_n, rebalance_days,
                     initial_cash, commission, min_price, max_price):
    """运行可转债回测（使用 CB 引擎）"""
    engine = CBBactestEngine()
    return engine.run_backtest(
        strategy=strategy_func,
        start_date=str(start_date), end_date=str(end_date),
        rebalance_days=rebalance_days, top_n=top_n,
        commission=commission, initial_cash=initial_cash,
        min_price=min_price, max_price=max_price,
    )


def _load_generic_df(table_name, start_date, end_date):
    """从 DuckDB 加载 ETF/股票日线数据，统一列名为 ts_code, trade_date, close"""
    s = start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else str(start_date)
    e = end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date)
    con = duckdb.connect(DB_PATH, read_only=True)
    if table_name == 'etf_daily':
        df = con.execute(f"""
            SELECT ts_code, trade_date, close, vol, amount
            FROM {table_name}
            WHERE trade_date >= '{s}' AND trade_date <= '{e}' AND close > 0
            ORDER BY trade_date, ts_code
        """).fetchdf()
    else:
        df = con.execute(f"""
            SELECT stock_code AS ts_code, date AS trade_date, close, volume AS vol, amount
            FROM stock_daily
            WHERE date >= '{s}' AND date <= '{e}' AND close > 0
            ORDER BY date, stock_code
        """).fetchdf()
    con.close()
    return df


# ============================================================
# 页面
# ============================================================

def page():
    st.title("📊 策略回测")

    # 数据检测
    data_status = _check_data()
    with st.expander("📦 数据状态", expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.metric("可转债", "✅" if data_status['cb'] else "❌")
        c2.metric("ETF", "✅" if data_status['etf'] else "❌")
        c3.metric("股票", "✅" if data_status['stock'] else "❌")
        if data_status.get('cb_range'):
            st.caption(f"可转债行情范围: {data_status['cb_range']}")

        missing = [k for k in ['cb', 'etf', 'stock'] if not data_status[k]]
        if missing:
            st.warning(f"缺少数据: {', '.join(missing)}。请先在「📥 Tushare下载」中下载对应数据。")

    if not any(data_status.values()):
        return

    # 加载全部策略
    registry = get_merged_registry(BUILTIN_CB_REGISTRY)
    if not registry:
        st.warning("未发现任何策略")
        return

    # 按类别分组
    cb_strategies = list_strategies_by_category(registry, 'cb')
    etf_strategies = list_strategies_by_category(registry, 'etf')
    stock_strategies = list_strategies_by_category(registry, 'stock')

    all_categorized = {}
    if cb_strategies: all_categorized['🔄 可转债'] = cb_strategies
    if etf_strategies: all_categorized['📈 ETF'] = etf_strategies
    if stock_strategies: all_categorized['📊 股票'] = stock_strategies

    # 策略选择
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("策略")
        category_tabs = st.tabs(list(all_categorized.keys()))

        strategy_key = None
        strategy_info = None
        strategy_category = None

        for tab, (cat_name, cat_reg) in zip(category_tabs, all_categorized.items()):
            with tab:
                opts = {f"{v['name']}": k for k, v in cat_reg.items()}
                if opts:
                    label = st.selectbox("选择策略", list(opts.keys()),
                                         key=f"strat_{cat_name}")
                    strategy_key = opts[label]
                    strategy_info = cat_reg[strategy_key]
                    strategy_category = list(cat_reg.values())[0].get('category', 'cb')
                    st.caption(f"📝 {strategy_info['desc']}")

        is_cb = (strategy_category == 'cb')

        with col2:
            st.subheader("参数")
            default_params = strategy_info.get('params', {}) if strategy_info else {}
            top_n = st.slider("持仓数量", 3, 50,
                              value=default_params.get('top_n', default_params.get('buy_n', 10)))
            rebalance_days = st.slider("调仓频率（交易日）", 1, 60, 5,
                                       help="1=每日, 5=每周, 20=每月")
            initial_cash = st.number_input("初始资金", value=100000, step=10000, min_value=10000)

    # CB 专属参数
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_date = st.date_input("开始日期", value=datetime(2024, 1, 1))
    with col_d2:
        end_date = st.date_input("结束日期", value=datetime(2025, 6, 30))

    if st.button("🚀 开始回测", type="primary", use_container_width=True):
        with st.spinner("回测计算中..."):
            try:
                func = strategy_info['func']
                if is_cb:
                    result = _run_cb_backtest(func, start_date, end_date, top_n,
                                              rebalance_days, initial_cash, 0.001, 100, 200)
                else:
                    table = 'etf_daily' if strategy_category == 'etf' else 'stock_daily'
                    df = _load_generic_df(table, start_date, end_date)
                    if df is None or df.empty:
                        st.error("所选日期范围内无数据")
                        return
                    st.info(f"已加载 {len(df):,} 条数据 | {df['ts_code'].nunique()} 只标的")
                    engine = CBBactestEngine()
                    result = engine.run_backtest(
                        strategy=func, start_date='', end_date='',
                        rebalance_days=rebalance_days, top_n=top_n,
                        initial_cash=initial_cash, commission=0.001,
                        min_price=0, max_price=99999,
                        df=df, code_col='ts_code', date_col='trade_date',
                        price_col='close', vol_col='vol',
                    )

                if result and result.get('metrics'):
                    st.session_state['backtest_result'] = result
                else:
                    st.error("回测结果为空，请扩大日期范围或调整过滤条件")

            except Exception as e:
                st.error(f"回测失败: {e}")
                import traceback
                st.code(traceback.format_exc())

    # 结果显示
    result = st.session_state.get('backtest_result')
    if result:
        metrics = result.get('metrics', {})
        nav_df = result.get('nav_curve', pd.DataFrame())

        if metrics:
            st.subheader("📊 回测指标")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("总收益率", f"{metrics.get('total_return', 0):.2%}")
            c2.metric("年化收益率", f"{metrics.get('annual_return', 0):.2%}")
            c3.metric("最大回撤", f"{metrics.get('max_drawdown', 0):.2%}")
            c4.metric("夏普比率", f"{metrics.get('sharpe_ratio', 0):.2f}")

        if not nav_df.empty:
            st.subheader("📈 净值曲线")
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=nav_df.index, y=nav_df['nav'],
                          mode='lines', name='净值', line=dict(color='#2196F3', width=2)))
            fig.add_hline(y=1.0, line_dash="dash", line_color="gray")
            fig.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)

            # 回撤
            cmax = nav_df['nav'].cummax()
            dd = (nav_df['nav'] - cmax) / cmax
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=dd.index, y=dd, mode='lines',
                           fill='tozeroy', line=dict(color='#f44336', width=1.5)))
            fig2.update_layout(title="回撤曲线", height=200,
                               margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig2, use_container_width=True)

        # 交易记录
        trades = result.get('trades', [])
        if trades:
            with st.expander("💰 交易记录"):
                tdf = pd.DataFrame(trades)
                tdf['date'] = tdf['date'].astype(str).str[:10]
                st.dataframe(tdf, use_container_width=True, height=300)
                total_buy = tdf[tdf['action'] == 'buy']['price'].count() if 'price' in tdf.columns else 0
                total_sell = tdf[tdf['action'] == 'sell']['price'].count() if 'price' in tdf.columns else 0
                st.caption(f"买入 {total_buy} 笔 | 卖出 {total_sell} 笔")
