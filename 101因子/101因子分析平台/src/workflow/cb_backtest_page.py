# -*- coding: utf-8 -*-
"""
可转债回测 - Streamlit 页面
集成在 101因子分析平台 中
"""

import sys
import os
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import numpy as np

# 确保 src 在路径中
src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from cb_backtest.cb_data_manager import CBDataManager
from cb_backtest.cb_backtest_engine import CBBactestEngine
from cb_backtest.cb_strategies import STRATEGY_REGISTRY


def page():
    """可转债回测页面"""
    st.title("🔄 可转债本地回测")

    # 数据状态检测
    with st.expander("📦 数据状态", expanded=False):
        try:
            mgr = CBDataManager()
            start, end = mgr.get_available_date_range()
            if start and end:
                basic_df = mgr.get_cb_basic()
                st.success(
                    f"数据就绪 | 行情范围: {start} ~ {end} | 可转债数量: {len(basic_df)}"
                )
                st.dataframe(basic_df[['ts_code', 'bond_short_name', 'stk_code',
                                       'stk_short_name', 'conv_price', 'coupon_rate']].head(20),
                             use_container_width=True)
            else:
                st.warning(
                    "未检测到可转债数据。请先在「📥 Tushare下载」中下载：\n"
                    "1. 可转债基本信息（cb_basic）\n"
                    "2. 可转债日行情（cb_daily，含转股溢价率）"
                )
                return
        except Exception as e:
            st.error(f"数据检测失败: {e}")
            return

    # 参数配置
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("策略与持仓")
        strategy_options = {f"{info['name']} - {info['desc']}": key
                           for key, info in STRATEGY_REGISTRY.items()}
        strategy_label = st.selectbox("策略", list(strategy_options.keys()), index=0)
        strategy_key = strategy_options[strategy_label]

        top_n = st.slider("持仓数量", 5, 50, 20)
        rebalance_days = st.slider("调仓频率（交易日）", 1, 60, 5,
                                   help="1=每日调仓, 5=每周, 20=每月")

    with col2:
        st.subheader("资金与过滤")
        initial_cash = st.number_input("初始资金", value=100000, step=10000, min_value=10000)

        col_price1, col_price2 = st.columns(2)
        with col_price1:
            min_price = st.number_input("最低价格", value=100.0, step=5.0)
        with col_price2:
            max_price = st.number_input("最高价格", value=150.0, step=5.0)

        commission = st.number_input("交易费率", value=0.001, step=0.0001,
                                     format="%.4f", help="单边费率，买卖各收一次")

    # 日期范围
    st.subheader("回测区间")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_date = st.date_input("开始日期", value=datetime(2023, 1, 1))
    with col_d2:
        end_date = st.date_input("结束日期", value=datetime.now())

    # 运行回测
    if st.button("🚀 开始回测", type="primary", use_container_width=True):
        with st.spinner("回测计算中..."):
            try:
                engine = CBBactestEngine()
                strategy_func = STRATEGY_REGISTRY[strategy_key]['func']

                result = engine.run_backtest(
                    strategy=strategy_func,
                    start_date=str(start_date),
                    end_date=str(end_date),
                    rebalance_days=rebalance_days,
                    top_n=top_n,
                    commission=commission,
                    initial_cash=initial_cash,
                    min_price=min_price,
                    max_price=max_price,
                )

                metrics = result.get('metrics', {})
                if not metrics:
                    st.error("回测结果为空，请检查数据范围和过滤条件")
                    return

                # 存入 session state 以便后续查看
                st.session_state['cb_backtest_result'] = result

            except Exception as e:
                st.error(f"回测失败: {e}")
                import traceback
                st.code(traceback.format_exc())
                return

    # 显示结果
    result = st.session_state.get('cb_backtest_result')
    if result:
        metrics = result.get('metrics', {})
        nav_df = result.get('nav_curve', pd.DataFrame())

        if metrics:
            _render_metrics(metrics)
        if not nav_df.empty:
            _render_nav_chart(nav_df)

        # 详细结果的标签页
        tab_h, tab_t = st.tabs(["📋 持仓历史", "💰 交易记录"])

        with tab_h:
            holdings_history = result.get('holdings_history', [])
            if holdings_history:
                records = []
                for date_val, codes in holdings_history:
                    records.append({
                        '日期': str(date_val)[:10],
                        '持仓数': len(codes),
                        '持仓代码': ', '.join(codes)
                    })
                st.dataframe(pd.DataFrame(records), use_container_width=True, height=400)
            else:
                st.info("暂无持仓历史")

        with tab_t:
            trades = result.get('trades', [])
            if trades:
                trades_df = pd.DataFrame(trades)
                trades_df['date'] = trades_df['date'].astype(str).str[:10]
                trades_df.rename(columns={
                    'date': '日期', 'code': '代码', 'action': '方向',
                    'price': '价格', 'shares': '数量', 'amount': '金额', 'pnl': '盈亏'
                }, inplace=True)
                st.dataframe(trades_df, use_container_width=True, height=400)

                total_buy = trades_df[trades_df['方向'] == 'buy']['金额'].sum()
                total_sell = trades_df[trades_df['方向'] == 'sell']['金额'].sum()
                total_pnl = trades_df[trades_df['方向'] == 'sell']['盈亏'].sum()
                st.caption(f"总买入: ¥{total_buy:,.0f} | 总卖出: ¥{total_sell:,.0f} | 总盈亏: ¥{total_pnl:,.0f}")
            else:
                st.info("暂无交易记录")


def _render_metrics(metrics: dict):
    """渲染回测指标"""
    st.subheader("📊 回测指标")

    col1, col2, col3 = st.columns(3)
    with col1:
        tr = metrics.get('total_return', 0)
        st.metric("总收益率", f"{tr:.2%}",
                   delta=f"{'盈利' if tr >= 0 else '亏损'}",
                   delta_color="normal" if tr >= 0 else "inverse")

        ar = metrics.get('annual_return', 0)
        st.metric("年化收益率", f"{ar:.2%}")

        wr = metrics.get('win_rate', 0)
        st.metric("日胜率", f"{wr:.2%}")

    with col2:
        md = metrics.get('max_drawdown', 0)
        st.metric("最大回撤", f"{md:.2%}", delta="风险指标", delta_color="inverse")

        sr = metrics.get('sharpe_ratio', 0)
        st.metric("夏普比率", f"{sr:.2f}")

        cr = metrics.get('calmar_ratio', 0)
        st.metric("卡玛比率", f"{cr:.2f}")

    with col3:
        st.metric("回测天数", f"{metrics.get('total_days', 0)}")
        ic = metrics.get('initial_cash', 0)
        fv = metrics.get('final_value', 0)
        st.metric("初始资金", f"¥{ic:,.0f}")
        st.metric("最终资金", f"¥{fv:,.0f}")


def _render_nav_chart(nav_df: pd.DataFrame):
    """渲染净值曲线"""
    st.subheader("📈 净值曲线")

    # 绘图
    import plotly.graph_objects as go

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=nav_df.index,
        y=nav_df['nav'],
        mode='lines',
        name='组合净值',
        line=dict(color='#2196F3', width=2),
    ))

    # 基准线
    fig.add_hline(y=1.0, line_dash="dash", line_color="gray",
                  annotation_text="初始净值 1.0")

    fig.update_layout(
        xaxis_title="日期",
        yaxis_title="净值",
        height=400,
        margin=dict(l=20, r=20, t=30, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)

    # 回撤曲线
    cummax = nav_df['nav'].cummax()
    drawdown = (nav_df['nav'] - cummax) / cummax

    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(
        x=drawdown.index,
        y=drawdown,
        mode='lines',
        name='回撤',
        fill='tozeroy',
        line=dict(color='#f44336', width=1.5),
    ))
    fig_dd.update_layout(
        title="回撤曲线",
        xaxis_title="日期",
        yaxis_title="回撤",
        height=250,
        margin=dict(l=20, r=20, t=30, b=20),
    )
    st.plotly_chart(fig_dd, use_container_width=True)
