# -*- coding: utf-8 -*-
"""
统一策略回测 - Streamlit 页面
使用 easyxt_backtest 统一的 EnhancedBacktestEngine
"""

import sys
import os
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 路径
src_path = Path(__file__).resolve().parent.parent
project_root = src_path.parent
easyxt_root = project_root.parent.parent
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(easyxt_root))

from easyxt_backtest import EnhancedBacktestEngine
from easyxt_backtest.simple_strategy_adapter import adapt
from core.data_manager import HybridDataManager
from cb_backtest.cb_strategies import STRATEGY_REGISTRY as BUILTIN_CB_REGISTRY
from ..strategies import get_merged_registry, list_strategies_by_category

DB_PATH = 'D:/StockData/stock_data.ddb'


def _check_data():
    status = {}
    try:
        import duckdb
        con = duckdb.connect(DB_PATH, read_only=True)
        tables = [t[0] for t in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()]
        status['cb'] = 'cb_daily' in tables
        status['etf'] = 'etf_daily' in tables
        status['stock'] = 'stock_daily' in tables
        con.close()
    except Exception:
        status = {'cb': False, 'etf': False, 'stock': False}
    return status


def page():
    st.title("📊 策略回测")

    data_status = _check_data()
    with st.expander("📦 数据状态", expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.metric("可转债", "✅" if data_status['cb'] else "❌")
        c2.metric("ETF", "✅" if data_status['etf'] else "❌")
        c3.metric("股票", "✅" if data_status['stock'] else "❌")
        missing = [k for k in ['cb', 'etf', 'stock'] if not data_status[k]]
        if missing:
            st.warning(f"缺少数据: {', '.join(missing)}")

    if not any(data_status.values()):
        return

    # 加载策略
    registry = get_merged_registry(BUILTIN_CB_REGISTRY)
    if not registry:
        st.warning("未发现策略。请将策略文件放入 src/strategies/ 目录。")
        return

    all_categorized = {}
    if (cb := list_strategies_by_category(registry, 'cb')): all_categorized['🔄 可转债'] = cb
    if (etf := list_strategies_by_category(registry, 'etf')): all_categorized['📈 ETF'] = etf
    if (stock := list_strategies_by_category(registry, 'stock')): all_categorized['📊 股票'] = stock

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("策略")
        tabs = st.tabs(list(all_categorized.keys()))
        strategy_key, strategy_info, strategy_category = None, None, None
        for tab, (cat_name, cat_reg) in zip(tabs, all_categorized.items()):
            with tab:
                opts = {v['name']: k for k, v in cat_reg.items()}
                if opts:
                    label = st.selectbox("选择策略", list(opts.keys()), key=f"s_{cat_name}")
                    strategy_key = opts[label]
                    strategy_info = cat_reg[strategy_key]
                    strategy_category = cat_reg[strategy_key].get('category', 'cb')
                    st.caption(f"📝 {strategy_info['desc']}")

    with col2:
        st.subheader("参数")
        dp = strategy_info.get('params', {}) if strategy_info else {}
        top_n = st.slider("持仓数量", 3, 50, value=dp.get('top_n', dp.get('buy_n', 10)))
        reb = st.slider("调仓频率（交易日）", 1, 60, 5)
        cash = st.number_input("初始资金", value=100000, step=10000)
        commission = st.number_input("交易费率", value=0.001, step=0.0001, format="%.4f")

    cd1, cd2 = st.columns(2)
    with cd1: start_date = st.date_input("开始日期", value=datetime(2024, 1, 1))
    with cd2: end_date = st.date_input("结束日期", value=datetime(2025, 6, 30))

    if st.button("🚀 开始回测", type="primary", use_container_width=True):
        if not strategy_info:
            st.error("请先选择策略")
            return

        with st.spinner("加载数据..."):
            dm = HybridDataManager()
            s = start_date.strftime('%Y%m%d')
            e = end_date.strftime('%Y%m%d')

            # 检查数据是否可用
            test_df = dm.get_price(strategy_key, s, e, verbose=False)
            if test_df is None or test_df.empty:
                st.error("所选日期范围内无数据，请检查数据下载状态")
                return
            count = len(test_df)
            codes = test_df.index.get_level_values(1).nunique() if hasattr(test_df.index, 'get_level_values') else 0
            st.info(f"已加载 {count:,} 条数据 | {codes} 只标的")

        with st.spinner("回测计算中..."):
            try:
                func = strategy_info['func']
                adapter = adapt(func, top_n=top_n, rebalance_days=reb,
                                start_date=s, end_date=e, data_manager=dm)
                engine = EnhancedBacktestEngine(
                    initial_cash=cash, commission=commission, data_manager=dm,
                )
                result = engine.run_backtest(adapter, s, e)
                if result and result.performance:
                    st.session_state['bt_result'] = {
                        'performance': result.performance,
                        'trades': result.trades,
                        'returns': result.returns,
                    }
                else:
                    st.error("回测结果为空")
            except Exception as ex:
                st.error(f"回测失败: {ex}")
                import traceback
                st.code(traceback.format_exc())

    # 显示结果
    br = st.session_state.get('bt_result')
    if br:
        perf = br['performance']
        if perf:
            st.subheader("📊 回测指标")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("总收益率", f"{perf.get('total_return', 0):.2%}")
            c2.metric("年化收益率", f"{perf.get('annual_return', 0):.2%}")
            c3.metric("最大回撤", f"{perf.get('max_drawdown', 0):.2%}")
            c4.metric("夏普比率", f"{perf.get('sharpe_ratio', 0):.2f}")

        returns_df = br.get('returns')
        if returns_df is not None and not returns_df.empty:
            st.subheader("📈 净值曲线")
            nav = (1 + returns_df['return']).cumprod()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=nav.index, y=nav.values,
                          mode='lines', name='净值', line=dict(color='#2196F3', width=2)))
            fig.add_hline(y=1.0, line_dash="dash", line_color="gray")
            fig.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)

            cmax = nav.cummax()
            dd = (nav - cmax) / cmax
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=dd.index, y=dd.values, mode='lines',
                           fill='tozeroy', line=dict(color='#f44336', width=1.5)))
            fig2.update_layout(title="回撤曲线", height=200, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig2, use_container_width=True)

        trades_df = br.get('trades')
        if trades_df is not None and not trades_df.empty:
            with st.expander("💰 交易记录"):
                st.dataframe(trades_df, use_container_width=True, height=300)
