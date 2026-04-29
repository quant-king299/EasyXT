# -*- coding: utf-8 -*-
"""
技术指标策略回测页面
使用 easyxt_backtest 的 TechnicalBacktestEngine 进行单股技术指标回测
"""
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import sys
from pathlib import Path
from datetime import datetime

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
matplotlib.rcParams['axes.unicode_minus'] = False

# 添加项目路径
project_root = Path(__file__).resolve().parent.parent.parent
main_project_root = project_root.parent.parent.resolve()
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(main_project_root))

# 导入回测框架
try:
    from easyxt_backtest.api import TechnicalBacktestEngine
    from easyxt_backtest.strategies.technical import (
        DualMovingAverageStrategy,
        RSIStrategy,
        BollingerBandsStrategy
    )
    from easyxt_backtest.performance import PerformanceAnalyzer
    BACKTEST_AVAILABLE = True
except ImportError as e:
    print(f"[ERROR] 导入回测框架失败: {e}")
    BACKTEST_AVAILABLE = False

# 策略映射
STRATEGY_MAP = {
    "双均线策略": {
        "class": DualMovingAverageStrategy,
        "desc": "短期均线上穿长期均线（金叉）→ 买入，下穿（死叉）→ 卖出",
        "params": ["short_period", "long_period"],
    },
    "RSI策略": {
        "class": RSIStrategy,
        "desc": "RSI < 30（超卖）→ 买入，RSI > 70（超买）→ 卖出",
        "params": ["rsi_period"],
    },
    "布林带策略": {
        "class": BollingerBandsStrategy,
        "desc": "价格跌破下轨 → 买入，突破上轨 → 卖出",
        "params": ["bb_period", "bb_devfactor"],
    },
}


def run_technical_backtest(stock_code, start_date, end_date,
                           strategy_name, strategy_params,
                           initial_cash=100000, commission=0.001):
    """运行技术指标回测"""
    if not BACKTEST_AVAILABLE:
        return None

    strategy_info = STRATEGY_MAP[strategy_name]
    strategy_class = strategy_info["class"]

    # 构建 Backtrader 策略参数
    bt_params = {}
    if strategy_name == "双均线策略":
        bt_params["short_period"] = strategy_params.get("short_period", 5)
        bt_params["long_period"] = strategy_params.get("long_period", 20)
    elif strategy_name == "RSI策略":
        bt_params["rsi_period"] = strategy_params.get("rsi_period", 14)
    elif strategy_name == "布林带策略":
        bt_params["period"] = strategy_params.get("bb_period", 20)
        bt_params["devfactor"] = strategy_params.get("bb_devfactor", 2.0)

    engine = TechnicalBacktestEngine(
        initial_cash=initial_cash,
        commission=commission
    )

    result = engine.quick_backtest(
        stock_code=stock_code,
        start_date=start_date,
        end_date=end_date,
        strategy_class=strategy_class,
        **bt_params
    )

    return result


def display_results(result, strategy_name, stock_code, initial_cash):
    """显示回测结果"""
    metrics = result.get('metrics', {})
    risk_analysis = result.get('risk_analysis', {})
    portfolio_curve = result.get('portfolio_curve', {})
    trades = result.get('trades', [])

    # 关键指标卡片
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_return = metrics.get('total_return', 0)
        st.metric(
            label="总收益率",
            value=f"{total_return:.2%}",
            delta=f"{total_return:.2%}"
        )

    with col2:
        annual_return = metrics.get('annual_return', 0)
        st.metric(
            label="年化收益率",
            value=f"{annual_return:.2%}",
            delta=f"{annual_return:.2%}"
        )

    with col3:
        sharpe = metrics.get('sharpe_ratio', 0)
        st.metric(
            label="夏普比率",
            value=f"{sharpe:.3f}",
        )

    with col4:
        max_dd = metrics.get('max_drawdown', 0)
        st.metric(
            label="最大回撤",
            value=f"{max_dd:.2%}",
            delta=f"{max_dd:.2%}",
            delta_color="inverse"
        )

    # 详细结果标签页
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 净值曲线",
        "📊 风险分析",
        "📋 交易记录",
        "⚙️ 完整指标"
    ])

    with tab1:
        dates = portfolio_curve.get('dates', [])
        values = portfolio_curve.get('values', [])

        if dates and values:
            fig, ax = plt.subplots(figsize=(12, 6))

            # 净值（归一化）
            net_values = [v / initial_cash for v in values]

            ax.plot(dates, net_values, linewidth=2, color='#2E86AB', label='策略净值')
            ax.axhline(y=1.0, color='red', linestyle='--', linewidth=1, alpha=0.7, label='基准线')
            ax.fill_between(dates, net_values, 1.0, alpha=0.15, color='#2E86AB')

            ax.set_xlabel('日期', fontsize=12)
            ax.set_ylabel('净值', fontsize=12)
            ax.set_title(f'{stock_code} {strategy_name} 净值曲线', fontsize=14, fontweight='bold')
            ax.legend(fontsize=10)
            ax.grid(True, alpha=0.3)
            fig.autofmt_xdate()
            st.pyplot(fig)
        else:
            st.info("暂无净值曲线数据")

    with tab2:
        if risk_analysis:
            # 使用 PerformanceAnalyzer 生成报告
            if BACKTEST_AVAILABLE:
                try:
                    analyzer = PerformanceAnalyzer()
                    report_lines = []
                    report_lines.append("=" * 60)
                    report_lines.append("风险分析报告")
                    report_lines.append("=" * 60)
                    report_lines.append("")
                    report_lines.append("【收益指标】")
                    report_lines.append(f"  总收益率:     {risk_analysis.get('total_return', 0):>10.2%}")
                    report_lines.append(f"  年化收益率:   {risk_analysis.get('annual_return', 0):>10.2%}")
                    report_lines.append(f"  初始资金:     {risk_analysis.get('initial_cash', initial_cash):>10,.2f} 元")
                    report_lines.append(f"  最终资金:     {risk_analysis.get('final_value', initial_cash):>10,.2f} 元")
                    report_lines.append("")
                    report_lines.append("【风险指标】")
                    report_lines.append(f"  最大回撤:     {risk_analysis.get('max_drawdown', 0):>10.2%}")
                    report_lines.append(f"  波动率:       {risk_analysis.get('volatility', 0):>10.2%}")
                    report_lines.append("")
                    report_lines.append("【风险调整收益】")
                    report_lines.append(f"  夏普比率:     {risk_analysis.get('sharpe_ratio', 0):>10.2f}")
                    report_lines.append(f"  卡尔玛比率:   {risk_analysis.get('calmar_ratio', 0):>10.2f}")
                    report_lines.append("")
                    report_lines.append("=" * 60)

                    st.code("\n".join(report_lines), language=None)
                except Exception:
                    st.json(risk_analysis)
            else:
                st.json(risk_analysis)
        else:
            st.info("暂无风险分析数据")

    with tab3:
        if trades:
            st.subheader("交易统计")
            for trade in trades:
                if len(trade) >= 2:
                    st.write(f"**{trade[0]}**: {trade[1]}")
        else:
            st.info("暂无交易记录")

    with tab4:
        st.subheader("全部指标")
        all_metrics = {**metrics, **risk_analysis}
        if all_metrics:
            metrics_df = pd.DataFrame([
                {"指标": k, "数值": f"{v:.4%}" if isinstance(v, float) and abs(v) < 10 else str(v)}
                for k, v in all_metrics.items()
            ])
            st.dataframe(metrics_df, use_container_width=True)
        else:
            st.info("暂无指标数据")


def page():
    """技术指标回测页面主函数"""

    st.title("🔧 技术指标策略回测")
    st.markdown("---")

    if not BACKTEST_AVAILABLE:
        st.error("❌ 回测框架未安装，请检查 easyxt_backtest 模块")
        return

    # 侧边栏：参数配置
    st.sidebar.header("⚙️ 参数配置")

    # 基本参数
    st.sidebar.subheader("基本参数")
    stock_code = st.sidebar.text_input(
        "股票代码",
        value="000001.SZ",
        help="输入股票代码，如 000001.SZ"
    )

    default_start = datetime(2024, 1, 1)
    default_end = datetime(2024, 12, 31)

    start_date = st.sidebar.date_input("开始日期", value=default_start)
    end_date = st.sidebar.date_input("结束日期", value=default_end, min_value=start_date)

    initial_cash = st.sidebar.number_input(
        "初始资金",
        min_value=10000,
        max_value=10000000,
        value=100000,
        step=10000,
        format="%d"
    )

    commission = st.sidebar.slider(
        "手续费率 (%)",
        min_value=0.01,
        max_value=0.30,
        value=0.10,
        step=0.01
    ) / 100.0

    # 策略选择
    st.sidebar.subheader("策略选择")
    strategy_name = st.sidebar.selectbox(
        "选择策略",
        options=list(STRATEGY_MAP.keys()),
        format_func=lambda x: {
            "双均线策略": "📈 双均线策略",
            "RSI策略": "📊 RSI策略",
            "布林带策略": "🎯 布林带策略",
        }[x]
    )

    # 根据策略显示不同参数
    strategy_params = {}

    if strategy_name == "双均线策略":
        st.sidebar.subheader("均线参数")
        strategy_params["short_period"] = st.sidebar.slider(
            "短期均线周期",
            min_value=3, max_value=30, value=5, step=1
        )
        strategy_params["long_period"] = st.sidebar.slider(
            "长期均线周期",
            min_value=10, max_value=120, value=20, step=1
        )

    elif strategy_name == "RSI策略":
        st.sidebar.subheader("RSI参数")
        strategy_params["rsi_period"] = st.sidebar.slider(
            "RSI周期",
            min_value=5, max_value=30, value=14, step=1
        )

    elif strategy_name == "布林带策略":
        st.sidebar.subheader("布林带参数")
        strategy_params["bb_period"] = st.sidebar.slider(
            "均线周期",
            min_value=10, max_value=50, value=20, step=1
        )
        strategy_params["bb_devfactor"] = st.sidebar.slider(
            "标准差倍数",
            min_value=1.0, max_value=3.0, value=2.0, step=0.1
        )

    # 运行按钮
    st.sidebar.markdown("---")

    with st.sidebar.expander("📋 查看完整配置"):
        st.json({
            "股票代码": stock_code,
            "日期范围": f"{start_date} ~ {end_date}",
            "初始资金": initial_cash,
            "手续费率": f"{commission:.4f}",
            "策略": strategy_name,
            "策略参数": strategy_params,
        })

    run_button = st.sidebar.button(
        "🚀 开始回测",
        type="primary",
        use_container_width=True
    )

    # 主界面
    if run_button:
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        with st.spinner(f"正在回测 {stock_code} ({strategy_name})..."):
            try:
                result = run_technical_backtest(
                    stock_code=stock_code,
                    start_date=start_str,
                    end_date=end_str,
                    strategy_name=strategy_name,
                    strategy_params=strategy_params,
                    initial_cash=initial_cash,
                    commission=commission
                )

                if result is not None:
                    st.success("✅ 回测完成！")
                    display_results(result, strategy_name, stock_code, initial_cash)
                else:
                    st.error("回测返回空结果，请检查数据是否可用")

            except Exception as e:
                st.error(f"❌ 回测失败：{str(e)}")
                import traceback
                st.code(traceback.format_exc())

    else:
        # 默认显示策略说明
        st.info("👈 请在左侧配置参数，然后点击「开始回测」按钮")

        st.subheader("📚 策略说明")

        tab1, tab2, tab3 = st.tabs(["双均线策略", "RSI策略", "布林带策略"])

        with tab1:
            st.markdown("""
            ### 📈 双均线策略

            **核心逻辑：**
            1. 计算短期均线（如5日）和长期均线（如20日）
            2. 短期均线上穿长期均线（金叉）→ 买入信号
            3. 短期均线下穿长期均线（死叉）→ 卖出信号

            **参数说明：**
            - **短期均线周期**：快线周期，反应灵敏但噪声多
            - **长期均线周期**：慢线周期，反应慢但信号更可靠

            **适用场景：**
            - 趋势明显的行情
            - 日线级别及以上
            """)

        with tab2:
            st.markdown("""
            ### 📊 RSI策略

            **核心逻辑：**
            1. 计算 RSI（相对强弱指标）
            2. RSI < 30（超卖区域）→ 买入信号
            3. RSI > 70（超买区域）→ 卖出信号

            **参数说明：**
            - **RSI周期**：计算 RSI 的时间窗口，常用14日

            **适用场景：**
            - 震荡行情
            - 寻找短期超买超卖机会
            """)

        with tab3:
            st.markdown("""
            ### 🎯 布林带策略

            **核心逻辑：**
            1. 计算中轨（均线）和上下轨（均线 ± N倍标准差）
            2. 价格跌破下轨 → 买入信号
            3. 价格突破上轨 → 卖出信号

            **参数说明：**
            - **均线周期**：中轨的周期，常用20日
            - **标准差倍数**：上下轨的宽度，常用2倍

            **适用场景：**
            - 震荡行情
            - 波动率回归策略
            """)


if __name__ == "__main__":
    page()
