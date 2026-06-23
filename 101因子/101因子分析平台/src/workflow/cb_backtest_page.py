# -*- coding: utf-8 -*-
"""
统一策略回测 - Streamlit 页面
CB/ETF: 向量化引擎（快，无需复权）
股票:   增强引擎（支持复权、停牌处理）
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

from easyxt_backtest.vectorized_engine import VectorizedBacktestEngine
from easyxt_backtest import EnhancedBacktestEngine
from easyxt_backtest.simple_strategy_adapter import adapt
from core.data_manager import HybridDataManager
from cb_backtest.cb_strategies import STRATEGY_REGISTRY as BUILTIN_CB_REGISTRY
from strategies import get_merged_registry

# 各类资产默认参数
CAT_DEFAULTS = {
    'cb':    {'min_price': 100, 'max_price': 500, 'top_n': 20, 'reb': 5,
              'label': '🔄 可转债',   'engine': 'vectorized'},
    'etf':   {'min_price': 0.5, 'max_price': 10,  'top_n': 10, 'reb': 5,
              'label': '📈 ETF',      'engine': 'vectorized'},
    'stock': {'min_price': 1,   'max_price': 9999,'top_n': 15, 'reb': 20,
              'label': '📊 股票',     'engine': 'enhanced'},
}


def page():
    st.title("📊 策略回测")

    # 加载所有策略并按类别分组
    registry = get_merged_registry(BUILTIN_CB_REGISTRY)
    categorized = {'cb': {}, 'etf': {}, 'stock': {}}
    for key, info in registry.items():
        cat = info.get('category', 'cb')
        if cat in categorized:
            categorized[cat][key] = info

    # 只显示有策略的类别
    available = {c: v for c, v in categorized.items() if v}

    if not available:
        st.warning("未发现策略。请将策略文件放入 src/strategies/ 目录。")
        return

    # ── 三标签页 ──
    tab_labels = [CAT_DEFAULTS[c]['label'] for c in available]
    tabs = st.tabs(tab_labels)

    for (cat, cat_reg), tab in zip(available.items(), tabs):
        with tab:
            _render_category_tab(cat, cat_reg)


def _render_category_tab(cat: str, cat_reg: dict):
    """渲染单个类别的回测标签页"""
    cfg = CAT_DEFAULTS[cat]
    opts = {f"{v['name']} - {v['desc']}": k for k, v in cat_reg.items()}
    if not opts:
        st.info("暂无策略")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("策略与持仓")
        strategy_label = st.selectbox("策略", list(opts.keys()), key=f"s_{cat}")
        strategy_key = opts[strategy_label]
        strategy_info = cat_reg[strategy_key]
        dp = strategy_info.get('params', {})  # 策略自带的默认参数

        top_n = st.slider("持仓数量", 3, 50,
                          value=dp.get('top_n', dp.get('buy_n', cfg['top_n'])),
                          key=f"n_{cat}_{strategy_key}")
        rebalance_days = st.slider("调仓频率（交易日）", 1, 60,
                                   value=dp.get('rebalance_days', cfg['reb']),
                                   help="1=每日调仓, 5=每周, 20=每月",
                                   key=f"reb_{cat}_{strategy_key}")

    with col2:
        st.subheader("资金与过滤")
        initial_cash = st.number_input("初始资金", value=100000, step=10000,
                                       key=f"cash_{cat}")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            min_price = st.number_input("最低价格",
                                        value=float(dp.get('min_price', cfg['min_price'])),
                                        step=1.0, key=f"minp_{cat}_{strategy_key}")
        with col_p2:
            max_price = st.number_input("最高价格",
                                        value=float(dp.get('max_price', cfg['max_price'])),
                                        step=1.0, key=f"maxp_{cat}_{strategy_key}")
        commission = st.number_input("交易费率", value=0.001, step=0.0001,
                                     format="%.4f", help="单边", key=f"comm_{cat}")

    # 日期范围
    st.subheader("回测区间")
    cd1, cd2 = st.columns(2)
    with cd1:
        start_date = st.date_input("开始日期", value=datetime(2024, 1, 1), key=f"sd_{cat}")
    with cd2:
        end_date = st.date_input("结束日期", value=datetime.now(), key=f"ed_{cat}")

    # 运行按钮
    if st.button(f"🚀 开始{cfg['label']}回测", type="primary", use_container_width=True,
                 key=f"btn_{cat}"):
        with st.spinner("回测计算中..."):
            s = start_date.strftime('%Y%m%d')
            e_str = end_date.strftime('%Y%m%d')
            try:
                if cfg['engine'] == 'vectorized':
                    # ── CB/ETF：向量化引擎（快，无需复权） ──
                    engine = VectorizedBacktestEngine(category=cat)
                    result = engine.run_backtest(
                        strategy_func=strategy_info['func'],
                        start_date=s, end_date=e_str,
                        rebalance_days=rebalance_days, top_n=top_n,
                        commission=commission, initial_cash=initial_cash,
                        min_price=min_price, max_price=max_price,
                    )
                else:
                    # ── 股票：增强引擎（支持复权、停牌处理） ──
                    dm = HybridDataManager()
                    adapter = adapt(
                        strategy_info['func'], top_n=top_n,
                        rebalance_days=rebalance_days,
                        start_date=s, end_date=e_str,
                        data_manager=dm, category='stock',
                        adjust='back',
                        min_price=min_price,
                        max_price=max_price,
                    )
                    engine = EnhancedBacktestEngine(
                        initial_cash=initial_cash, commission=commission,
                        data_manager=dm, adjust='back',
                    )
                    enhanced_result = engine.run_backtest(adapter, s, e_str)
                    # 转换为统一格式
                    result = _enhanced_to_dict(enhanced_result, initial_cash)

                metrics = result.get('metrics', {})
                if not metrics:
                    st.error("回测结果为空，请检查数据范围和过滤条件")
                    return

                st.session_state[f'bt_result_{cat}'] = result

            except Exception as e:
                st.error(f"回测失败: {e}")
                import traceback
                st.code(traceback.format_exc())
                return

    # 显示结果
    result = st.session_state.get(f'bt_result_{cat}')
    if result:
        st.caption(f"当前显示: {cfg['label']} 回测结果")
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
                  delta="盈利" if tr >= 0 else "亏损",
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
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=nav_df.index, y=nav_df['nav'],
        mode='lines', name='组合净值',
        line=dict(color='#2196F3', width=2),
    ))
    fig.add_hline(y=1.0, line_dash="dash", line_color="gray")
    fig.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)

    # 回撤
    cummax = nav_df['nav'].cummax()
    dd = (nav_df['nav'] - cummax) / cummax
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=dd.index, y=dd.values, mode='lines',
        fill='tozeroy', line=dict(color='#f44336', width=1.5),
    ))
    fig2.update_layout(title="回撤曲线", height=200, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig2, use_container_width=True)


def _enhanced_to_dict(enhanced_result, initial_cash: float) -> dict:
    """将 EnhancedBacktestResult 转换为向量化引擎统一的 dict 格式"""
    import pandas as pd

    # 指标
    perf = enhanced_result.performance
    metrics = {
        'total_return': perf.get('total_return', 0),
        'annual_return': perf.get('annual_return', 0),
        'max_drawdown': perf.get('max_drawdown', 0),
        'sharpe_ratio': perf.get('sharpe_ratio', 0),
        'calmar_ratio': 0,
        'win_rate': (perf.get('profit_days', 0) / max(perf.get('total_days', 1), 1)
                     if perf.get('total_days', 0) > 0 else 0),
        'total_days': perf.get('total_days', 0),
        'initial_cash': initial_cash,
        'final_value': perf.get('final_value', initial_cash),
    }

    # 净值曲线
    ph = enhanced_result.portfolio_history
    if ph is not None and not ph.empty:
        nav_df = ph[['date', 'value', 'cash', 'daily_return']].copy()
        nav_df = nav_df.set_index('date')
        nav_df['nav'] = nav_df['value'] / initial_cash
        nav_df['holdings_value'] = nav_df['value'] - nav_df['cash']
        nav_df['total_value'] = nav_df['value']
        nav_df['num_holdings'] = ph.get('position_count', 0)
    else:
        nav_df = pd.DataFrame()

    # 交易记录
    trades = []
    trades_df = enhanced_result.trades
    if trades_df is not None and not trades_df.empty:
        for _, row in trades_df.iterrows():
            direction = row.get('direction', 'long')
            trades.append({
                'date': row.get('date', ''),
                'code': row.get('symbol', ''),
                'action': 'buy' if direction == 'long' else 'sell',
                'price': float(row.get('price', 0)),
                'shares': float(row.get('volume', 0)),
                'amount': float(row.get('volume', 0)) * float(row.get('price', 0)),
                'pnl': 0,
            })

    # 持仓历史
    holdings_history = []
    positions_hist = getattr(enhanced_result, 'positions_history', {})
    for dt, pos in sorted(positions_hist.items()):
        codes = [s for s, v in pos.items() if v > 0]
        if codes:
            holdings_history.append((dt, codes))

    return {
        'nav_curve': nav_df,
        'metrics': metrics,
        'trades': trades,
        'holdings_history': holdings_history,
    }
