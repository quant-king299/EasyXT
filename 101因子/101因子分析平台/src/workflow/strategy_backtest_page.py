# -*- coding: utf-8 -*-
"""
策略回测页面
提供完整的小市值策略回测功能
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

# 验证 easyxt_backtest 是否存在
easyxt_backtest_path = main_project_root / "easyxt_backtest"
if not easyxt_backtest_path.exists():
    print(f"[WARNING] easyxt_backtest not found at: {easyxt_backtest_path}", file=sys.stderr)
else:
    print(f"[OK] easyxt_backtest found at: {easyxt_backtest_path}", file=sys.stderr)


def check_market_cap_data(data_manager, start_date, end_date):
    """
    检查市值数据是否完整

    Returns:
        dict: {
            'needs_download': bool,  # 是否需要下载数据
            'message': str,          # 提示信息
            'missing_range': str     # 缺失的日期范围
        }
    """
    try:
        if not data_manager.duckdb_con:
            return {
                'needs_download': True,
                'message': 'DuckDB数据库未连接',
                'missing_range': f'{start_date.strftime("%Y%m%d")} ~ {end_date.strftime("%Y%m%d")}'
            }

        # 检查stock_market_cap表是否存在
        try:
            data_manager.duckdb_con.execute("SELECT COUNT(*) FROM stock_market_cap LIMIT 1").fetchone()
        except:
            return {
                'needs_download': True,
                'message': '**stock_market_cap表不存在**，请先下载市值数据',
                'missing_range': f'{start_date.strftime("%Y%m%d")} ~ {end_date.strftime("%Y%m%d")}'
            }

        # 检查日期范围
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        result = data_manager.duckdb_con.execute(f"""
            SELECT
                COUNT(DISTINCT date) as date_count,
                MIN(date) as min_date,
                MAX(date) as max_date
            FROM stock_market_cap
            WHERE date BETWEEN '{start_str}' AND '{end_str}'
        """).fetchone()

        date_count = result[0] if result else 0

        # 计算应该有的交易日数量（粗略估算：每周5天）
        days_diff = (end_date - start_date).days
        expected_trading_days = days_diff * 5 / 7  # 约每周5个交易日

        # 如果数据覆盖度低于50%，提示下载
        coverage = date_count / max(expected_trading_days, 1)
        needs_download = coverage < 0.5

        if date_count == 0:
            message = f'**完全没有市值数据** ({start_str} ~ {end_str})'
        elif coverage < 0.3:
            message = f'**市值数据严重不足**：仅有 {date_count} 天数据，预计需要约 {int(expected_trading_days)} 天'
        elif coverage < 0.5:
            message = f'**市值数据不足**：仅有 {date_count} 天数据，预计需要约 {int(expected_trading_days)} 天（覆盖率 {coverage*100:.1f}%）'
        else:
            message = f'市值数据良好：{date_count} 天数据（覆盖率 {coverage*100:.1f}%）'

        return {
            'needs_download': needs_download,
            'message': message,
            'missing_range': f'{start_str} ~ {end_str}'
        }

    except Exception as e:
        # 检查失败，保守提示
        return {
            'needs_download': False,  # 检查失败不阻止回测
            'message': f'数据检查失败: {e}',
            'missing_range': ''
        }


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

    # 使用session_state管理日期
    if 'start_date' not in st.session_state:
        st.session_state.start_date = pd.to_datetime("2024-01-01").date()
    if 'end_date' not in st.session_state:
        st.session_state.end_date = pd.to_datetime("2024-12-31").date()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 📅 回测时间")
        
        # 直接使用date_input，不添加额外的确认逻辑
        # Streamlit的设计理念就是"输入即更新"
        start_date = st.date_input(
            "开始日期",
            value=st.session_state.start_date,
            key="start_date_widget",
            help="回测开始日期",
            on_change=lambda: st.session_state.update(start_date=st.session_state.start_date)
        )
        end_date = st.date_input(
            "结束日期", 
            value=st.session_state.end_date,
            key="end_date_widget",
            help="回测结束日期"
        )
        
        # 更新session_state
        st.session_state.start_date = start_date
        st.session_state.end_date = end_date
        
        # 转换为datetime
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)


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

    # 显示当前生效的日期范围
    days_diff = (end_dt - start_dt).days
    expected_trading_days = int(days_diff * 5 / 7)
    
    st.markdown("---")
    st.info(f"""
    ✓ 当前生效的回测范围：
    • 开始日期：{start_dt.strftime('%Y-%m-%d')}
    • 结束日期：{end_dt.strftime('%Y-%m-%d')}
    • 时间跨度：{days_diff} 天（约 {expected_trading_days} 个交易日）
    
    ℹ️ 如需修改日期，直接在上方修改即可，会自动更新
    """)

    return start_dt, end_dt, num_stocks, universe_size, initial_cash


def run_backtest(start_date, end_date, num_stocks, universe_size, initial_cash):
    """运行回测（使用新的统一框架）"""
    try:
        # 使用新框架的 API
        from easyxt_backtest.api import SelectionBacktestEngine
        from easyxt_backtest.strategies.small_cap_strategy import SmallCapStrategy
        from easyxt_backtest.data_manager import DataManager

        # 显示进度
        progress_bar = st.progress(0)
        status_text = st.empty()

        status_text.text("初始化数据管理器...")
        progress_bar.progress(10)

        # 初始化
        dm = DataManager()

        # 检查市值数据是否完整
        status_text.text("检查市值数据...")
        progress_bar.progress(15)

        data_check_info = check_market_cap_data(dm, start_date, end_date)
        if data_check_info['needs_download']:
            st.warning(f"""
            ⚠️ **市值数据不完整**

            {data_check_info['message']}

            **📥 从GUI下载数据（推荐）：**

            1️⃣ **启动主GUI**（新窗口）
            ```bash
            cd "C:\\Users\\Administrator\\Desktop\\miniqmt扩展"
            python run_gui.py
            ```

            2️⃣ **进入下载页面**
            - 点击 **"📥 Tushare数据下载"** 标签页
            - 选择 **"💰 市值数据"** 子标签页

            3️⃣ **快速下载**
            - ✅ Token会自动读取（从 .env 文件）
            - 点击 **"2024年全年"** 快速按钮
            - 点击 **"🚀 开始下载全A股市值数据"**
            - 等待5-10分钟完成下载

            4️⃣ **返回回测**
            - 下载完成后回到此页面
            - 重新运行回测即可

            **🔄 或者继续回测：**
            系统会自动使用Tushare API在线获取（速度较慢，每次调仓都需查询）
            """)

            if not st.checkbox("数据不完整，但我仍要继续回测（使用Tushare API）", value=False, key="continue_without_data"):
                return None, "用户取消回测"

            st.info("⏳ 将使用Tushare API在线获取数据，速度可能较慢...")

        status_text.text("创建策略实例...")
        progress_bar.progress(20)

        try:
            strategy = SmallCapStrategy(
                index_code='399101.SZ',  # 中小板综指
                select_num=num_stocks,
                universe_size=universe_size if universe_size > 0 else None,
                data_manager=dm  # 传入数据管理器
            )
            status_text.text("策略实例创建成功")
        except Exception as e:
            import traceback
            error_msg = f"创建策略实例失败: {e}\n\n{traceback.format_exc()}"
            status_text.text("策略实例创建失败")
            return None, error_msg

        progress_bar.progress(25)

        status_text.text("初始化回测引擎...")
        progress_bar.progress(30)

        try:
            # 使用新框架的回测引擎
            engine = SelectionBacktestEngine(
                initial_cash=initial_cash,
                commission=0.001
            )
            status_text.text("回测引擎初始化成功")
        except Exception as e:
            import traceback
            error_msg = f"初始化回测引擎失败: {e}\n\n{traceback.format_exc()}"
            status_text.text("回测引擎初始化失败")
            return None, error_msg

        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        status_text.text(f"运行回测: {start_str} ~ {end_str}...")
        progress_bar.progress(40)

        try:
            results = engine.run_backtest(strategy, start_str, end_str)
            progress_bar.progress(100)
            status_text.text("✅ 回测完成！")
            return results, None
        except Exception as e:
            import traceback
            error_msg = f"回测执行失败: {e}\n\n{traceback.format_exc()}"
            status_text.text("回测执行失败")
            return None, error_msg

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
        if hasattr(results, 'returns') and results.returns is not None and not results.returns.empty and len(results.returns.index) > 0:
            try:
                # 处理字符串格式的日期索引（YYYYMMDD格式）
                start_str = str(results.returns.index[0])
                end_str = str(results.returns.index[-1])

                # ✅ 检查格式是否为 YYYYMMDD（8位数字）
                if len(start_str) == 8 and start_str.isdigit() and len(end_str) == 8 and end_str.isdigit():
                    # 转换为datetime对象以便计算天数
                    start = pd.to_datetime(start_str, format='%Y%m%d')
                    end = pd.to_datetime(end_str, format='%Y%m%d')

                    days = (end - start).days
                    years = days / 365.25

                    st.markdown(f"""
                    | 指标 | 数值 |
                    |------|------|
                    | 回测开始 | {start.strftime('%Y-%m-%d')} |
                    | 回测结束 | {end.strftime('%Y-%m-%d')} |
                    | 回测天数 | {days} 天 |
                    | 回测年限 | {years:.2f} 年 |
                    """)
                else:
                    # 尝试直接解析（可能是 datetime 对象或其他格式）
                    start = pd.to_datetime(results.returns.index[0])
                    end = pd.to_datetime(results.returns.index[-1])
                    days = (end - start).days
                    years = days / 365.25

                    st.markdown(f"""
                    | 指标 | 数值 |
                    |------|------|
                    | 回测开始 | {start.strftime('%Y-%m-%d')} |
                    | 回测结束 | {end.strftime('%Y-%m-%d')} |
                    | 回测天数 | {days} 天 |
                    | 回测年限 | {years:.2f} 年 |
                    """)
            except Exception as e:
                st.markdown(f"""
                | 指标 | 数值 |
                |------|------|
                | 时间数据 | 解析失败: {str(e)[:50]} |
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

    # 数据准备提示
    with st.expander("💡 **数据准备提示**（首次使用必读）", expanded=False):
        st.markdown("""
        ### 📥 市值数据下载（全市场数据）

        **为什么需要下载市值数据？**
        - 小市值策略需要按市值排序选股
        - DuckDB本地数据最快（秒级响应）
        - 在线API较慢且可能不稳定

        **🌟 推荐方式：从GUI下载（简单快捷）⭐**

        #### 步骤：
        1. **启动主GUI**
           ```bash
           cd "C:\\Users\\Administrator\\Desktop\\miniqmt扩展"
           python run_gui.py
           ```

        2. **进入下载页面**
           - 在GUI主窗口中找到 **"📥 Tushare数据下载"** 标签页
           - 点击 **"💰 市值数据"** 子标签页

        3. **配置下载参数**
           - ✅ **Token自动读取**：GUI会自动读取 .env 文件中的 TUSHARE_TOKEN
           - 点击 **"2024年全年"** 快速按钮
           - 或者手动设置日期范围（如 2024-01-01 ~ 2024-12-31）

        4. **开始下载**
           - 点击 **"🚀 开始下载全A股市值数据"** 按钮
           - 等待5-10分钟，下载约5000只股票 × 243个交易日

        **优点：**
        - ✅ 图形界面，操作简单
        - ✅ Token自动读取（.env配置）
        - ✅ 实时进度显示
        - ✅ 可视化日志输出
        - ✅ 自动处理错误和重试

        **参数说明：**
        - **选股数量**：最终持仓的股票数（如5只）
        - **股票池大小**：从多少只小市值股票中筛选（如500只）
          - 例如：从全市场筛选市值最小的500只，再从中选5只持仓
          - 股票池越大，选股范围越广，但可能风险更高

        **数据源优先级（自动切换）：**
        1. ⭐ **DuckDB**（本地，最快）- 从GUI下载后
        2. ⚡ **Tushare**（在线，准确）- 自动fallback
        3. ⚠️ **QMT**（本地，仅供参考）- 可能不准确

        **检查当前数据状态：**
        """, unsafe_allow_html=True)

        # 添加快速检查按钮
        if st.button("🔍 检查市值数据", use_container_width=True):
            try:
                import sys
                import os
                sys.path.insert(0, str(Path(__file__).parent.parent.parent))
                from easyxt_backtest.data_manager import DataManager

                with st.spinner("检查数据中..."):
                    dm = DataManager()
                    info = check_market_cap_data(dm, start_date, end_date)

                    if info['needs_download']:
                        st.error(f"""
                        ⚠️ {info['message']}

                        **📥 下载数据步骤：**

                        1️⃣ **启动主GUI**（如果未打开）
                        ```bash
                        cd "C:\\Users\\Administrator\\Desktop\\miniqmt扩展"
                        python run_gui.py
                        ```

                        2️⃣ **进入下载页面**
                        - 点击 **"📥 Tushare数据下载"** 标签页
                        - 选择 **"💰 市值数据"** 子标签页

                        3️⃣ **配置并下载**
                        - Token自动读取（.env配置）
                        - 点击 **"2024年全年"** 快速按钮
                        - 点击 **"🚀 开始下载全A股市值数据"**

                        💡 下载约需5-10分钟，完成后即可回测
                        """)
                    else:
                        st.success(f"""
                        ✅ {info['message']}

                        数据充足，可以开始回测！
                        """)
            except Exception as e:
                st.warning(f"数据检查失败: {e}")
                st.info("""
                💡 **提示：** 如果尚未下载市值数据，建议：

                1. 启动主GUI：`python run_gui.py`
                2. 进入 **"📥 Tushare数据下载"** → **"💰 市值数据"**
                3. Token自动读取（.env配置），点击 **"2024年全年"** 快速下载
                4. 等待5-10分钟完成下载

                下载完成后即可快速回测！
                """)

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
