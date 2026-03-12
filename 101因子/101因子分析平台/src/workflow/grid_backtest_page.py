# -*- coding: utf-8 -*-
"""
网格策略回测页面
提供完整的网格交易策略回测功能
使用新的统一 easyxt_backtest 框架
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

# 添加项目路径（使用绝对路径避免相对路径问题）
project_root = Path(__file__).resolve().parent.parent.parent  # 101因子/101因子分析平台/
main_project_root = project_root.parent.parent.resolve()  # miniqmt扩展/

sys.path.insert(0, str(project_root))
sys.path.insert(0, str(main_project_root))

# 导入新的回测框架
try:
    from easyxt_backtest import GridBacktestEngine
    from core.data_manager import HybridDataManager
    print("[OK] GridBacktestEngine imported successfully")
except ImportError as e:
    print(f"[ERROR] Failed to import: {e}")
    GridBacktestEngine = None
    HybridDataManager = None


def run_grid_backtest(stock_code, start_date, end_date, strategy_mode, params, initial_cash=100000):
    """
    运行网格策略回测

    Args:
        stock_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        strategy_mode: 策略模式（fixed/adaptive/atr）
        params: 策略参数字典
        initial_cash: 初始资金

    Returns:
        回测结果字典
    """
    if GridBacktestEngine is None:
        return None

    # 初始化数据管理器
    data_manager = HybridDataManager()

    # 创建回测引擎
    engine = GridBacktestEngine(
        initial_cash=initial_cash,
        commission=0.0001,  # 万分之一手续费（适合ETF）
        data_manager=data_manager
    )

    # 运行回测
    result = engine.run_backtest(
        stock_code=stock_code,
        start_date=start_date,
        end_date=end_date,
        strategy_mode=strategy_mode,
        **params
    )

    return result


def display_backtest_results(result):
    """
    显示回测结果

    Args:
        result: 回测结果字典
    """
    if result is None:
        st.error("回测失败，请检查参数")
        return

    metrics = result['metrics']
    trade_log = result['trade_log']
    equity_curve = result['equity_curve']
    params = result['params']

    # 显示基本指标
    st.subheader("📊 回测结果")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="总收益率",
            value=f"{metrics['total_return']*100:.2f}%",
            delta=None
        )

    with col2:
        sharpe = metrics.get('sharpe_ratio')
        st.metric(
            label="夏普比率",
            value=f"{sharpe:.2f}" if sharpe else "N/A",
            delta=None
        )

    with col3:
        st.metric(
            label="最大回撤",
            value=f"{metrics.get('max_drawdown', 0):.2f}%",
            delta=None
        )

    with col4:
        st.metric(
            label="胜率",
            value=f"{metrics.get('win_rate', 0)*100:.1f}%",
            delta=None
        )

    # 显示交易统计
    st.subheader("📈 交易统计")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("总交易次数", metrics.get('total_trades', 0))
    with col2:
        st.metric("盈利交易", metrics.get('won_trades', 0))
    with col3:
        st.metric("亏损交易", metrics.get('lost_trades', 0))

    # 显示净值曲线
    if not equity_curve.empty:
        st.subheader("💹 净值曲线")

        equity_df = equity_curve.copy()
        equity_df['date'] = pd.to_datetime(equity_df['date'])
        equity_df = equity_df.set_index('date')

        # 计算收益率
        initial_value = metrics['initial_cash']
        equity_df['return'] = (equity_df['portfolio_value'] / initial_value - 1) * 100

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(equity_df.index, equity_df['return'], linewidth=2, color='#2E86AB')
        ax.fill_between(equity_df.index, equity_df['return'], alpha=0.3, color='#2E86AB')
        ax.axhline(y=0, color='gray', linestyle='--', linewidth=1)
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('收益率 (%)', fontsize=12)
        ax.set_title(f"净值曲线 ({params.get('strategy_mode', 'fixed').upper()}策略)", fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.format_xdata = lambda x: pd.to_datetime(x, unit='ms').strftime('%Y-%m-%d') if isinstance(x, (int, float)) else x
        fig.autofmt_xdate()
        st.pyplot(fig)

    # 显示交易明细
    if not trade_log.empty:
        st.subheader("📋 交易明细")

        # 转换日期格式
        trade_display = trade_log.copy()
        if 'date' in trade_display.columns:
            trade_display['date'] = pd.to_datetime(trade_display['date']).dt.strftime('%Y-%m-%d')

        # 显示前100条交易
        st.dataframe(
            trade_display.head(100).reset_index(drop=True),
            width='stretch'  # 替代 use_container_width=True
        )

        # 下载按钮
        csv = trade_display.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 下载完整交易记录",
            data=csv,
            file_name=f"grid_trades_{params.get('strategy_mode', 'fixed')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )


def page():
    """网格策略回测页面主函数"""

    st.set_page_config(
        page_title="网格策略回测",
        page_icon="📊",
        layout="wide"
    )

    st.title("🔄 网格交易策略回测")
    st.markdown("---")

    # 侧边栏：参数配置
    st.sidebar.header("⚙️ 参数配置")

    # 基本参数
    st.sidebar.subheader("基本参数")
    stock_code = st.sidebar.text_input(
        "股票代码",
        value="511380.SH",
        help="输入股票代码，如511380.SH（债券ETF）"
    )

    # 日期选择
    default_start = datetime(2024, 1, 1)
    default_end = datetime(2024, 12, 31)

    start_date = st.sidebar.date_input(
        "开始日期",
        value=default_start,
        max_value=default_end
    )

    end_date = st.sidebar.date_input(
        "结束日期",
        value=default_end,
        min_value=start_date,
        max_value=datetime.now()
    )

    initial_cash = st.sidebar.number_input(
        "初始资金",
        min_value=10000,
        max_value=10000000,
        value=100000,
        step=10000,
        format="%d"
    )

    # 策略模式选择
    st.sidebar.subheader("策略模式")
    strategy_mode = st.sidebar.selectbox(
        "选择策略",
        options=['fixed', 'adaptive', 'atr'],
        format_func=lambda x: {
            'fixed': '📐 固定网格',
            'adaptive': '📊 自适应网格',
            'atr': '📈 ATR动态网格'
        }[x]
    )

    # 根据策略模式显示不同参数
    params = {}

    if strategy_mode == 'fixed':
        st.sidebar.subheader("固定网格参数")

        grid_count = st.sidebar.slider(
            "网格数量",
            min_value=5,
            max_value=50,
            value=15,
            step=1
        )
        params['grid_count'] = grid_count

        price_range = st.sidebar.slider(
            "价格区间 (%)",
            min_value=1,
            max_value=20,
            value=5,
            step=1
        ) / 100.0
        params['price_range'] = price_range

        enable_trailing = st.sidebar.checkbox(
            "启用动态调整基准价",
            value=True
        )
        params['enable_trailing'] = enable_trailing

    elif strategy_mode == 'adaptive':
        st.sidebar.subheader("自适应网格参数")

        buy_threshold = st.sidebar.slider(
            "买入阈值 (%)",
            min_value=0.1,
            max_value=5.0,
            value=1.0,
            step=0.1
        ) / 100.0
        params['buy_threshold'] = buy_threshold

        sell_threshold = st.sidebar.slider(
            "卖出阈值 (%)",
            min_value=0.1,
            max_value=5.0,
            value=1.0,
            step=0.1
        ) / 100.0
        params['sell_threshold'] = sell_threshold

        max_position = st.sidebar.number_input(
            "最大持仓（股）",
            min_value=1000,
            max_value=100000,
            value=10000,
            step=1000
        )
        params['max_position'] = max_position

    elif strategy_mode == 'atr':
        st.sidebar.subheader("ATR网格参数")

        atr_period = st.sidebar.slider(
            "ATR周期",
            min_value=10,
            max_value=500,
            value=300,
            step=10
        )
        params['atr_period'] = atr_period

        atr_multiplier = st.sidebar.slider(
            "ATR倍数",
            min_value=1.0,
            max_value=10.0,
            value=6.0,
            step=0.5
        )
        params['atr_multiplier'] = atr_multiplier

        trailing_period = st.sidebar.slider(
            "动态调整周期（天）",
            min_value=5,
            max_value=60,
            value=20,
            step=5
        )
        params['trailing_period'] = trailing_period

        enable_trailing = st.sidebar.checkbox(
            "启用动态调整基准价",
            value=True
        )
        params['enable_trailing'] = enable_trailing

    # 通用参数
    st.sidebar.subheader("通用参数")

    position_size = st.sidebar.number_input(
        "每格交易数量（股）",
        min_value=100,
        max_value=10000,
        value=1000,
        step=100
    )
    params['position_size'] = position_size

    base_price_input = st.sidebar.text_input(
        "基准价格（留空自动）",
        value="",
        help="留空则使用首日收盘价"
    )
    base_price = float(base_price_input) if base_price_input else None
    params['base_price'] = base_price

    # 数据周期
    data_period = st.sidebar.selectbox(
        "数据周期",
        options=['1d', '1h', '30m', '15m', '5m', '1m'],
        index=0
    )

    # 运行按钮
    st.sidebar.markdown("---")

    # 显示当前配置
    with st.sidebar.expander("📋 查看完整配置"):
        st.json({
            "股票代码": stock_code,
            "日期范围": f"{start_date} ~ {end_date}",
            "初始资金": initial_cash,
            "策略模式": strategy_mode,
            "参数": params,
            "数据周期": data_period
        })

    run_button = st.sidebar.button(
        "🚀 开始回测",
        type="primary",
        use_container_width=True
    )

    # 主界面
    if run_button:
        # 转换日期格式
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        # 显示进度
        with st.spinner(f"正在回测 {stock_code} ({strategy_mode}策略)..."):
            try:
                result = run_grid_backtest(
                    stock_code=stock_code,
                    start_date=start_date_str,
                    end_date=end_date_str,
                    strategy_mode=strategy_mode,
                    params=params,
                    initial_cash=initial_cash
                )

                if result is not None:
                    st.success("✅ 回测完成！")
                    display_backtest_results(result)

            except Exception as e:
                st.error(f"❌ 回测失败：{str(e)}")
                import traceback
                st.error(traceback.format_exc())

    else:
        # 默认显示说明
        st.info("👈 请在左侧配置参数，然后点击「开始回测」按钮")

        # 显示策略说明
        st.subheader("📚 策略说明")

        tab1, tab2, tab3 = st.tabs(["固定网格", "自适应网格", "ATR动态网格"])

        with tab1:
            st.markdown("""
            ### 📐 固定网格策略

            **核心逻辑：**
            1. 在价格区间内设置多个网格线
            2. 价格每跌到一个网格线买入
            3. 价格每涨到一个网格线卖出
            4. 适合震荡行情的ETF品种

            **参数说明：**
            - **网格数量**：网格线的数量，数量越多交易越频繁
            - **价格区间**：网格覆盖的价格范围比例
            - **动态调整**：是否根据市场波动动态调整基准价

            **适用场景：**
            - 震荡行情（横盘整理）
            - 波动率相对稳定的ETF
            - 长期持有的仓位做波段降低成本
            """)

        with tab2:
            st.markdown("""
            ### 📊 自适应网格策略

            **核心逻辑：**
            1. 根据相对涨跌幅触发交易，而非固定网格线
            2. 价格下跌超过买入阈值时买入
            3. 价格上涨超过卖出阈值时卖出
            4. 适合趋势行情或波动较大的品种

            **参数说明：**
            - **买入阈值**：触发买入的跌幅百分比
            - **卖出阈值**：触发卖出的涨幅百分比
            - **最大持仓**：防止仓位过大的风控参数

            **适用场景：**
            - 趋势行情（有明确方向）
            - 波动率较大的品种
            - 需要灵活应对市场变化
            """)

        with tab3:
            st.markdown("""
            ### 📈 ATR动态网格策略

            **核心逻辑：**
            1. 使用ATR（平均真实波幅）计算网格间距
            2. 网格间距 = ATR × 倍数
            3. 根据市场波动率动态调整网格
            4. 适合波动率变化的品种

            **参数说明：**
            - **ATR周期**：计算ATR的时间窗口（分钟数据建议200-500）
            - **ATR倍数**：网格间距相对于ATR的倍数
            - **动态调整周期**：重新计算网格的时间间隔

            **适用场景：**
            - 波动率频繁变化的品种
            - 需要根据市场状态自动调整
            - 分钟级或小时级数据回测
            """)


if __name__ == "__main__":
    page()
