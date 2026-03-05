# -*- coding: utf-8 -*-
"""
策略回测页面
提供完整的小市值策略回测功能
使用importlib直接加载模块，绕过__init__.py的相对导入问题
"""
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import sys
import os
import importlib.util
from pathlib import Path
from datetime import datetime

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
matplotlib.rcParams['axes.unicode_minus'] = False

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 定义easyxt_backtest路径（但不加入sys.path，避免触发__init__.py）
backtest_path = Path(r"C:\Users\Administrator\Desktop\miniqmt扩展\easyxt_backtest")
if not backtest_path.exists():
    print(f"[ERROR] easyxt_backtest not found at: {backtest_path}", file=sys.stderr)


def load_module_from_file(module_name, file_path):
    """直接从文件加载模块，绕过__init__.py避免相对导入错误"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def render_header():
    """渲染页面标题"""
    st.markdown("""
    <div style='background: linear-gradient(135deg, #FF6B6B 0%, #4ECDC4 100%);
                padding: 2rem; border-radius: 15px; margin-bottom: 2rem;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);'>
        <h1 style='color: white; text-align: center; margin: 0;
                   font-size: 2.5rem; font-weight: 700;'>
            🎯 策略回测平台
        </h1>
        <p style='color: rgba(255, 255, 255, 0.9); text-align: center;
                  margin-top: 0.5rem; font-size: 1.1rem;'>
            基于EasyXT的完整回测框架 - 小市值策略
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_config_panel():
    """渲染配置面板"""
    st.markdown("""
    <div style='background: white; padding: 1.5rem; border-radius: 15px;
                margin: 1rem 0; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
                border-left: 5px solid #FF6B6B;'>
        <h2 style='color: #2c3e50; margin-top: 0;'>⚙️ 回测配置</h2>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 📅 回测时间")
        start_date = st.date_input(
            "开始日期",
            value=pd.to_datetime("2015-01-01"),
            key="start_date",
            help="回测开始日期"
        )
        end_date = st.date_input(
            "结束日期",
            value=pd.to_datetime("2024-12-31"),
            key="end_date",
            help="回测结束日期"
        )

    with col2:
        st.markdown("#### 📊 策略参数")
        num_stocks = st.slider(
            "选股数量",
            min_value=1,
            max_value=50,
            value=5,
            step=1,
            key="num_stocks",
            help="每次调仓选择的股票数量"
        )
        universe_size = st.slider(
            "股票池大小",
            min_value=100,
            max_value=5000,
            value=500,
            step=100,
            key="universe_size",
            help="从多少只小市值股票中筛选"
        )

    with col3:
        st.markdown("#### 💰 资金设置")
        initial_cash = st.number_input(
            "初始资金（元）",
            min_value=100000,
            max_value=10000000,
            value=1000000,
            step=100000,
            key="initial_cash",
            help="回测初始资金"
        )

    return start_date, end_date, num_stocks, universe_size, initial_cash


def run_backtest(start_date, end_date, num_stocks, universe_size, initial_cash):
    """运行回测（完整功能版 - 使用importlib绕过相对导入）"""
    try:
        backtest_path = Path(r"C:\Users\Administrator\Desktop\miniqmt扩展\easyxt_backtest")

        # 使用importlib直接加载模块文件，绕过包的__init__.py
        # 按照依赖顺序加载：strategy_base -> data_manager -> performance -> engine
        load_module_from_file('strategy_base', backtest_path / 'strategy_base.py')

        data_manager_module = load_module_from_file(
            'data_manager',
            backtest_path / 'data_manager.py'
        )
        DataManager = data_manager_module.DataManager

        load_module_from_file('performance', backtest_path / 'performance.py')

        engine_module = load_module_from_file(
            'engine',
            backtest_path / 'engine.py'
        )
        BacktestEngine = engine_module.BacktestEngine

        # 使用wrapper获取策略类
        from strategy_wrapper import get_small_cap_strategy_class
        SmallCapStrategy = get_small_cap_strategy_class()

        # 显示进度
        progress_bar = st.progress(0)
        status_text = st.empty()

        status_text.text("初始化数据管理器...")
        progress_bar.progress(10)

        # 初始化
        dm = DataManager()

        status_text.text("创建策略实例...")
        progress_bar.progress(20)

        strategy = SmallCapStrategy(
            index_code='399101.SZ',  # 中小100指数
            select_num=num_stocks
        )
        strategy.data_manager = dm

        status_text.text("初始化回测引擎...")
        progress_bar.progress(30)

        # 运行回测
        engine = BacktestEngine(data_manager=dm, initial_cash=initial_cash)

        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        status_text.text("运行回测...")
        progress_bar.progress(40)

        results = engine.run_backtest(strategy, start_str, end_str)

        progress_bar.progress(100)
        status_text.text("✅ 回测完成！")

        return results, None

    except Exception as e:
        import traceback
        error_msg = f"回测错误: {e}\n\n{traceback.format_exc()}"
        return None, error_msg


def render_performance_metrics(performance, initial_cash):
    """渲染性能指标"""
    st.markdown("""
    <div style='background: white; padding: 1.5rem; border-radius: 15px;
                margin: 1rem 0; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
                border-left: 5px solid #4ECDC4;'>
        <h2 style='color: #2c3e50; margin-top: 0;'>📊 性能指标</h2>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="💰 总收益率",
            value=f"{performance['total_return'] * 100:.2f}%",
            delta=None,
            help="从回测开始到结束的总收益率"
        )

    with col2:
        st.metric(
            label="📈 年化收益率",
            value=f"{performance['annual_return'] * 100:.2f}%",
            delta=None,
            help="按年化计算的收益率"
        )

    with col3:
        delta_color = "normal" if performance['max_drawdown'] >= 0 else "inverse"
        st.metric(
            label="⚠️ 最大回撤",
            value=f"{performance['max_drawdown'] * 100:.2f}%",
            delta=None,
            delta_color=delta_color,
            help="回测期间最大的资产回撤"
        )

    with col4:
        st.metric(
            label="🎯 夏普比率",
            value=f"{performance['sharpe_ratio']:.2f}",
            delta=None,
            help="风险调整后的收益指标"
        )

    # 详细指标
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 💵 资金情况")
        st.markdown(f"""
        <div style='padding: 1rem; background: #f8f9fa; border-radius: 10px;'>
            <p style='margin: 0.5rem 0;'><strong>初始资金:</strong> {initial_cash:,.2f} 元</p>
            <p style='margin: 0.5rem 0;'><strong>最终资金:</strong> {initial_cash * (1 + performance['total_return']):,.2f} 元</p>
            <p style='margin: 0.5rem 0;'><strong>净盈利:</strong> {initial_cash * performance['total_return']:,.2f} 元</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("#### ⚡ 风险指标")
        st.markdown(f"""
        <div style='padding: 1rem; background: #f8f9fa; border-radius: 10px;'>
            <p style='margin: 0.5rem 0;'><strong>最大回撤:</strong> {performance['max_drawdown'] * 100:.2f}%</p>
            <p style='margin: 0.5rem 0;'><strong>波动率:</strong> {performance['volatility'] * 100:.2f}%</p>
            <p style='margin: 0.5rem 0;'><strong>夏普比率:</strong> {performance['sharpe_ratio']:.2f}</p>
        </div>
        """, unsafe_allow_html=True)


def render_equity_curve(returns):
    """渲染净值曲线"""
    st.markdown("""
    <div style='background: white; padding: 1.5rem; border-radius: 15px;
                margin: 1rem 0; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
                border-left: 5px solid #95E1D3;'>
        <h2 style='color: #2c3e50; margin-top: 0;'>📈 净值曲线</h2>
    </div>
    """, unsafe_allow_html=True)

    if returns is None or returns.empty:
        st.warning("⚠️ 没有净值数据")
        return

    # 计算累计净值
    cumulative_returns = (1 + returns).cumprod()

    # 创建图表
    fig, ax = plt.subplots(figsize=(12, 6))

    cumulative_returns.plot(ax=ax, linewidth=2, color='#FF6B6B')

    ax.set_title("策略净值曲线", fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel("日期", fontsize=12)
    ax.set_ylabel("累计净值", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle='--')

    # 填充区域
    ax.fill_between(cumulative_returns.index, 1, cumulative_returns.values,
                     alpha=0.3, color='#FF6B6B')

    # 格式化Y轴
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.2f}'))

    plt.tight_layout()
    st.pyplot(fig)


def render_drawdown_chart(returns):
    """渲染回撤图"""
    st.markdown("""
    <div style='background: white; padding: 1.5rem; border-radius: 15px;
                margin: 1rem 0; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
                border-left: 5px solid #F38181;'>
        <h2 style='color: #2c3e50; margin-top: 0;'>📉 回撤曲线</h2>
    </div>
    """, unsafe_allow_html=True)

    if returns is None or returns.empty:
        st.warning("⚠️ 没有回撤数据")
        return

    # 计算回撤
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max

    # 创建图表
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.fill_between(drawdown.index, drawdown.values * 100, 0,
                    alpha=0.3, color='#F38181')
    drawdown.plot(ax=ax, linewidth=2, color='#F38181')

    ax.set_title("策略回撤曲线", fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel("日期", fontsize=12)
    ax.set_ylabel("回撤 (%)", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle='--')

    plt.tight_layout()
    st.pyplot(fig)


def render_trade_records(trades):
    """渲染交易记录"""
    st.markdown("""
    <div style='background: white; padding: 1.5rem; border-radius: 15px;
                margin: 1rem 0; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
                border-left: 5px solid #AA96DA;'>
        <h2 style='color: #2c3e50; margin-top: 0;'>📋 交易记录</h2>
    </div>
    """, unsafe_allow_html=True)

    if trades is None or trades.empty:
        st.warning("⚠️ 没有交易记录")
        return

    # 统计信息
    col1, col2, col3, col4 = st.columns(4)

    buy_trades = trades[trades['direction'] == 'buy']
    sell_trades = trades[trades['direction'] == 'sell']

    with col1:
        st.metric("总交易", len(trades), "笔")
    with col2:
        st.metric("买入", len(buy_trades), "笔")
    with col3:
        st.metric("卖出", len(sell_trades), "笔")
    with col4:
        if not trades.empty:
            total_amount = (trades['price'] * trades['volume']).sum()
            st.metric("成交额", f"{total_amount/10000:.1f}", "万元")

    st.markdown("---")

    # 交易记录表格
    st.dataframe(
        trades,
        use_container_width=True,
        height=400,
        column_config={
            "date": st.column_config.TextColumn("日期", width="medium"),
            "symbol": st.column_config.TextColumn("代码", width="small"),
            "direction": st.column_config.TextColumn("方向", width="small"),
            "volume": st.column_config.NumberColumn("数量", format="%d"),
            "price": st.column_config.NumberColumn("价格", format="%.2f"),
            "amount": st.column_config.NumberColumn("金额", format="%.2f")
        }
    )


def render_backtest_summary(results, initial_cash):
    """渲染回测摘要"""
    st.markdown("""
    <div style='background: white; padding: 1.5rem; border-radius: 15px;
                margin: 1rem 0; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
                border-left: 5px solid #FCBAD3;'>
        <h2 style='color: #2c3e50; margin-top: 0;'>📊 回测摘要</h2>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📈 收益指标")
        perf = results.performance

        st.markdown(f"""
        | 指标 | 数值 |
        |------|------|
        | 总收益率 | **{perf['total_return'] * 100:.2f}%** |
        | 年化收益率 | **{perf['annual_return'] * 100:.2f}%** |
        | 初始资金 | {initial_cash:,.2f} 元 |
        | 最终资金 | {initial_cash * (1 + perf['total_return']):,.2f} 元 |
        | 净盈利 | {initial_cash * perf['total_return']:,.2f} 元 |
        """)

    with col2:
        st.markdown("#### ⚠️ 风险指标")
        st.markdown(f"""
        | 指标 | 数值 |
        |------|------|
        | 最大回撤 | **{perf['max_drawdown'] * 100:.2f}%** |
        | 波动率 | {perf['volatility'] * 100:.2f}% |
        | 夏普比率 | {perf['sharpe_ratio']:.2f} |
        | 卡玛比率 | {perf.get('calmar_ratio', 0):.2f} |
        """)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📊 交易统计")
        st.markdown(f"""
        | 指标 | 数值 |
        |------|------|
        | 总交易次数 | {len(results.trades)} 笔 |
        | 交易天数 | {len(results.returns)} 天 |
        | 平均每日交易 | {len(results.trades) / max(len(results.returns), 1):.2f} 笔 |
        """)

    with col2:
        st.markdown("#### ⏱️ 时间统计")
        # 使用真实的returns数据
        if hasattr(results, 'returns') and results.returns is not None and not results.returns.empty:
            start = results.returns.index[0]
            end = results.returns.index[-1]
            days = (end - start).days
            years = days / 365.25

            st.markdown(f"""
            | 指标 | 数值 |
            |------|------|
            | 回测开始 | {start} |
            | 回测结束 | {end} |
            | 回测天数 | {days} 天 |
            | 回测年限 | {years:.2f} 年 |
            """)
        else:
            st.markdown("""
            | 指标 | 数值 |
            |------|------|
            | 时间数据 | 暂无（请查看净值曲线） |
            """)


def render_strategy_backtest_page():
    """渲染策略回测页面"""

    # 页面标题
    render_header()

    # 配置面板
    start_date, end_date, num_stocks, universe_size, initial_cash = render_config_panel()

    # 运行按钮
    st.markdown("---")
    run_button = st.button(
        "🚀 开始回测",
        type="primary",
        use_container_width=True,
        key="run_backtest"
    )

    if run_button:
        # 运行回测
        results, error = run_backtest(
            start_date, end_date, num_stocks, universe_size, initial_cash
        )

        if error:
            st.error(f"❌ {error}")
            return

        if results is None:
            st.error("❌ 回测失败，请检查配置")
            return

        # 展示结果
        st.success("✅ 回测完成！")
        st.markdown("---")

        # 创建标签页
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 性能指标",
            "📈 净值曲线",
            "📉 回撤分析",
            "📋 交易记录",
            "📄 详细报告"
        ])

        with tab1:
            render_performance_metrics(results.performance, initial_cash)
            render_backtest_summary(results, initial_cash)

        with tab2:
            render_equity_curve(results.returns)

        with tab3:
            render_drawdown_chart(results.returns)

        with tab4:
            render_trade_records(results.trades)

        with tab5:
            st.markdown("#### 📄 完整回测报告")
            st.json({
                "performance": {
                    k: float(v) if isinstance(v, (int, float, np.number)) else str(v)
                    for k, v in results.performance.items()
                },
                "summary": {
                    "total_trades": len(results.trades),
                    "trading_days": len(results.returns),
                    "initial_cash": initial_cash,
                    "final_cash": float(initial_cash * (1 + results.performance['total_return']))
                }
            })

    # 使用说明
    st.markdown("---")
    with st.expander("💡 使用说明"):
        st.markdown("""
        ### 策略说明
        - **策略类型**: 小市值策略
        - **选股逻辑**: 每月从股票池中选择流通市值最小的N只股票
        - **调仓频率**: 每月第一个交易日
        - **权重分配**: 等权重配置

        ### 参数说明
        - **选股数量**: 每次调仓持有的股票数量（建议3-10只）
        - **股票池大小**: 从多少只股票中筛选（建议300-1000只）
        - **初始资金**: 回测起始资金

        ### 性能指标说明
        - **总收益率**: 整个回测期间的累计收益率
        - **年化收益率**: 按年化计算的收益率
        - **最大回撤**: 回测期间最大的资产回撤幅度
        - **夏普比率**: 风险调整后的收益指标（越大越好）

        ### 数据来源
        - **价格数据**: DuckDB本地数据库（优先）→ QMT → Tushare
        - **市值数据**: QMT实时计算 → 缓存 → Tushare
        """)


if __name__ == "__main__":
    render_strategy_backtest_page()
