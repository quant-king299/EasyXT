# -*- coding: utf-8 -*-
"""
101因子平台 - Streamlit Web界面

提供可视化操作界面：
1. YAML配置管理
2. 策略回测
3. 结果展示
4. 实盘代码生成
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import yaml

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

from easyxt_backtest.config import load_strategy_config, StrategyConfig
from easyxt_backtest.strategies.config_driven_strategy import ConfigDrivenStrategy
from easyxt_backtest.backtest_engine import BacktestEngine
from easyxt_backtest.live_trading.code_generator import LiveCodeGenerator

# 导入数据模块
try:
    from easyxt_backtest.data import create_duckdb_data_manager as create_data_manager
    DATA_AVAILABLE = True
except ImportError:
    try:
        from easyxt_backtest.data import create_data_manager
        DATA_AVAILABLE = True
    except ImportError:
        DATA_AVAILABLE = False
        create_data_manager = None

# 导入配置编辑器
from easyxt_backtest.web_app.config_editor import (
    render_config_editor,
    init_editor_session_state
)

# 页面配置
st.set_page_config(
    page_title="101因子平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        padding: 1rem;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """初始化会话状态"""
    if 'config' not in st.session_state:
        st.session_state.config = None
    if 'backtest_result' not in st.session_state:
        st.session_state.backtest_result = None
    if 'generated_code_path' not in st.session_state:
        st.session_state.generated_code_path = None

    # 编辑器会话状态
    if 'selected_factors' not in st.session_state:
        st.session_state.selected_factors = []
    if 'selected_filters' not in st.session_state:
        st.session_state.selected_filters = []
    if 'strategy_name' not in st.session_state:
        st.session_state.strategy_name = "我的策略"
    if 'strategy_description' not in st.session_state:
        st.session_state.strategy_description = ""


def load_example_configs():
    """加载示例配置"""
    examples_dir = project_root / 'easyxt_backtest' / 'config' / 'examples'
    examples = []

    if examples_dir.exists():
        for yaml_file in examples_dir.glob('*.yaml'):
            examples.append(yaml_file.name)

    return examples


def render_header():
    """渲染页面标题"""
    st.markdown('<h1 class="main-title">📊 101因子平台</h1>', unsafe_allow_html=True)
    st.markdown("---")


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.title("🎛️ 控制面板")

        # 功能选择
        page = st.radio(
            "选择功能",
            ["🎨 配置编辑器", "📝 配置管理", "🔄 策略回测", "📈 结果分析", "💻 实盘代码生成"],
            label_visibility="collapsed"
        )

        st.markdown("---")

        # 示例配置加载
        st.subheader("📁 示例策略")
        examples = load_example_configs()

        if examples:
            selected_example = st.selectbox(
                "选择示例配置",
                ["未选择"] + examples
            )

            if selected_example != "未选择":
                if st.button("📥 加载示例", use_container_width=True):
                    config_path = project_root / 'easyxt_backtest' / 'config' / 'examples' / selected_example
                    try:
                        st.session_state.config = load_strategy_config(str(config_path))
                        st.success(f"✅ 成功加载: {selected_example}")
                    except Exception as e:
                        st.error(f"❌ 加载失败: {e}")

        st.markdown("---")

        # 配置上传
        st.subheader("📤 上传配置")
        uploaded_file = st.file_uploader(
            "上传YAML配置文件",
            type=['yaml', 'yml'],
            help="上传策略配置文件"
        )

        if uploaded_file is not None:
            try:
                # 保存临时文件
                temp_path = project_root / 'temp_config.yaml'
                with open(temp_path, 'wb') as f:
                    f.write(uploaded_file.getbuffer())

                st.session_state.config = load_strategy_config(str(temp_path))
                st.success(f"✅ 成功上传: {uploaded_file.name}")

                # 清理临时文件
                temp_path.unlink()
            except Exception as e:
                st.error(f"❌ 上传失败: {e}")

        # 当前配置信息
        if st.session_state.config:
            st.markdown("---")
            st.subheader("ℹ️ 当前配置")
            config = st.session_state.config
            st.info(f"""
            **策略名称**: {config.name}

            **版本**: {config.version}

            **描述**: {config.description}

            **因子数量**: {len(config.scoring_factors)}

            **回测期间**: {config.backtest_config['start_date']} - {config.backtest_config['end_date']}
            """)

    return page


def page_config_management():
    """配置管理页面"""
    st.header("📝 策略配置管理")

    # 如果没有配置，显示上传区域和示例配置选择
    if st.session_state.config is None:
        st.markdown("### 📁 选择示例配置")

        # 加载示例配置
        examples = load_example_configs()

        if examples:
            col1, col2, col3 = st.columns([1, 2, 1])

            with col2:
                st.info("💡 快速开始：选择一个示例配置，或上传自定义配置文件")

                # 示例配置选择
                selected_example = st.selectbox(
                    "选择示例策略",
                    ["-- 请选择示例配置 --"] + examples,
                    key="config_management_example"
                )

                # 加载示例配置按钮
                if selected_example != "-- 请选择示例配置 --":
                    col_a, col_b, col_c = st.columns([1, 2, 1])
                    with col_b:
                        if st.button("📥 加载选中的示例配置", type="primary", use_container_width=True, key="load_example_btn"):
                            config_path = project_root / 'easyxt_backtest' / 'config' / 'examples' / selected_example
                            try:
                                config = load_strategy_config(str(config_path))
                                st.session_state.config = config
                                st.success(f"✅ 成功加载: {selected_example}")
                                st.balloons()
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 加载失败: {e}")
                                import traceback
                                with st.expander("查看错误详情"):
                                    st.code(traceback.format_exc())

                        # 显示配置说明
                        config_descriptions = {
                            "simple_small_cap.yaml": "🎯 **简单小市值策略**\n\n从中小板综指中选择市值最小的10只股票，每月第一个交易日调仓，等权重配置。",
                            "multi_factor_strategy.yaml": "📊 **多因子策略**\n\n结合市值、动量、反转等多个因子进行综合评分，选择最优股票组合。",
                            "alpha101_strategy.yaml": "🔬 **Alpha101因子策略**\n\n使用经典的Alpha101因子进行选股，包含多个技术指标因子。"
                        }

                        if selected_example in config_descriptions:
                            st.markdown("---")
                            st.markdown("### 📖 策略说明")
                            st.markdown(config_descriptions[selected_example])

        st.markdown("---")
        st.markdown("### 📤 上传自定义配置")

        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            uploaded_file = st.file_uploader(
                "选择YAML配置文件",
                type=['yaml', 'yml'],
                key="config_management_upload"
            )

            if uploaded_file is not None:
                try:
                    import tempfile

                    # 保存到临时文件
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
                        f.write(uploaded_file.getvalue().decode('utf-8'))
                        temp_path = f.name

                    # 加载配置
                    config = load_strategy_config(temp_path)
                    st.session_state.config = config
                    st.success(f"✅ 配置加载成功: {config.name}")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 加载失败: {e}")
                    import traceback
                    with st.expander("查看错误详情"):
                        st.code(traceback.format_exc())

        st.markdown("---")
        st.markdown("### 📋 配置文件结构说明")

        with st.expander("查看配置文件结构", expanded=False):
            st.info("""
            配置文件应包含以下内容：

            **基本信息**
            - 策略名称和版本
            - 作者和描述

            **回测参数**
            - 开始/结束日期（建议使用2024年数据）
            - 初始资金和佣金率

            **股票池配置**
            - 指数成分股或自定义股票列表

            **评分因子**
            - 基本面因子（市值、PE、ROE等）
            - 技术因子（动量、反转、波动率等）
            - Alpha101/191因子

            **剔除条件**
            - ST股票、退市股票
            - 市值范围、PE范围等

            **组合构建**
            - 选股方式（top_n、百分比）
            - 权重分配（等权重、市值加权）

            **调仓配置**
            - 调仓频率（月度、周度）
            - 交易时间
            """)

        return

    config = st.session_state.config

    # 配置概览
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("策略名称", config.name)
    with col2:
        st.metric("版本", config.version)
    with col3:
        st.metric("因子数量", len(config.scoring_factors))

    st.markdown("---")

    # 详细配置展示
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 基本信息", "🎯 因子配置", "🔍 过滤条件", "💼 组合构建", "⚙️ 调仓配置"
    ])

    with tab1:
        st.subheader("基本信息")
        st.json({
            "名称": config.name,
            "版本": config.version,
            "作者": config.author,
            "描述": config.description
        })

    with tab2:
        st.subheader("打分因子配置")

        for i, factor in enumerate(config.scoring_factors, 1):
            with st.expander(f"因子 {i}: {factor.name}"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("方向", "正相关" if factor.direction == 1 else "负相关")
                with col2:
                    st.metric("权重", f"{factor.weight:.2%}")
                with col3:
                    st.metric("类型", factor.factor_type)

                st.markdown("**详细配置**")
                st.json({
                    "字段": factor.field,
                    "标准化": factor.normalize,
                    "中性化": factor.neutralize
                })

    with tab3:
        st.subheader("排除条件")

        if config.exclude_filters:
            for i, filter_config in enumerate(config.exclude_filters, 1):
                with st.expander(f"过滤条件 {i}: {filter_config.type} - {filter_config.name}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("类型", filter_config.type)
                    with col2:
                        st.metric("条件", filter_config.condition)

                    if filter_config.values:
                        st.markdown("**值列表**")
                        st.write(", ".join(filter_config.values))
                    if filter_config.field:
                        st.markdown(f"**字段**: {filter_config.field}")
                    if filter_config.min_value is not None:
                        st.markdown(f"**最小值**: {filter_config.min_value}")
                    if filter_config.max_value is not None:
                        st.markdown(f"**最大值**: {filter_config.max_value}")
        else:
            st.info("未配置排除条件")

    with tab4:
        st.subheader("组合构建")
        st.json(config.portfolio_config)

    with tab5:
        st.subheader("调仓配置")
        st.json(config.rebalance_config)


def page_backtest():
    """回测页面"""
    st.header("🔄 策略回测")

    if st.session_state.config is None:
        st.warning("⚠️ 请先从侧边栏加载或上传配置文件")
        return

    config = st.session_state.config

    # 检查策略是否有基本面因子
    has_fundamental_factors = any(
        f.factor_type == 'fundamental' for f in config.scoring_factors
    )

    # 显示数据源提示
    if has_fundamental_factors:
        st.info("""
        💡 **检测到基本面因子**

        您的策略包含基本面因子（市值、PE、ROE等），需要使用真实QMT数据。

        请确保：
        1. ✅ QMT软件正在运行
        2. ✅ 已配置unified_config.json
        3. ✅ 勾选下方"使用真实QMT数据"
        """)
    else:
        st.info("""
        💡 **仅使用技术因子**

        您的策略只包含技术因子，可以使用模拟数据或真实数据。

        建议勾选"使用真实QMT数据"以获得更准确的回测结果。
        """)

    # 回测参数设置
    col1, col2 = st.columns(2)

    with col1:
        start_date = st.text_input(
            "开始日期",
            value=config.backtest_config['start_date'],
            help="格式: YYYYMMDD"
        )

    with col2:
        end_date = st.text_input(
            "结束日期",
            value=config.backtest_config['end_date'],
            help="格式: YYYYMMDD"
        )

    # 数据源选择
    use_real_data = st.checkbox(
        "📡 使用DuckDB数据（Tushare历史数据）",
        value=True,
        help="勾选后使用DuckDB中的Tushare数据，支持基本面因子。取消勾选使用模拟数据（仅支持技术因子）"
    )

    if use_real_data:
        st.info("💡 使用DuckDB数据：支持所有基本面因子（市值、PE、ROE等）")
        st.caption("📍 数据来源: D:/StockData/ (Tushare历史数据)")
    else:
        st.warning("⚠️ 使用模拟数据：仅支持技术因子，不支持基本面因子")

    # 运行回测
    if st.button("🚀 开始回测", type="primary", use_container_width=True):
        with st.spinner("⏳ 正在运行回测..."):
            try:
                # 创建数据管理器
                data_manager = None
                if use_real_data:
                    try:
                        from easyxt_backtest.data import create_data_manager
                        data_manager = create_data_manager()
                        st.info("✅ 已连接真实数据源（QMT）")
                    except Exception as e:
                        st.warning(f"⚠️ 无法连接真实数据源: {e}")
                        st.warning("💡 将使用模拟数据，仅支持技术因子")
                        data_manager = None

                # 创建策略
                strategy = ConfigDrivenStrategy(config, data_manager=data_manager)

                # 创建回测引擎
                engine = BacktestEngine(
                    initial_cash=config.backtest_config['initial_cash'],
                    commission=config.backtest_config['commission'],
                    data_manager=data_manager
                )

                # 运行回测
                result = engine.run_backtest(
                    strategy=strategy,
                    start_date=start_date,
                    end_date=end_date
                )

                # 保存结果
                st.session_state.backtest_result = result

                st.success("✅ 回测完成！")
                st.balloons()

            except Exception as e:
                st.error(f"❌ 回测失败: {e}")
                st.exception(e)

    # 显示回测结果
    if st.session_state.backtest_result:
        st.markdown("---")
        st.subheader("📊 回测结果")

        result = st.session_state.backtest_result
        perf = result.performance

        # 性能指标
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("总收益率", f"{perf.get('total_return', 0):.2%}")
        with col2:
            st.metric("年化收益率", f"{perf.get('annual_return', 0):.2%}")
        with col3:
            st.metric("最大回撤", f"{perf.get('max_drawdown', 0):.2%}")
        with col4:
            sharpe = perf.get('sharpe_ratio', 0)
            st.metric("夏普比率", f"{sharpe:.2f}" if sharpe else "N/A")

        st.markdown("---")

        # 净值曲线
        if not result.portfolio_history.empty:
            st.subheader("📈 净值曲线")

            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=result.portfolio_history['date'],
                y=result.portfolio_history['value'],
                mode='lines',
                name='策略净值',
                line=dict(color='#1f77b4', width=2)
            ))

            fig.update_layout(
                title="策略净值走势",
                xaxis_title="日期",
                yaxis_title="净值",
                hovermode='x unified',
                height=400
            )

            st.plotly_chart(fig, use_container_width=True)

        # 回撤曲线
        if not result.portfolio_history.empty:
            st.subheader("📉 回撤曲线")

            portfolio_history = result.portfolio_history
            portfolio_history['peak'] = portfolio_history['value'].cummax()
            portfolio_history['drawdown'] = (portfolio_history['peak'] - portfolio_history['value']) / portfolio_history['peak']

            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=portfolio_history['date'],
                y=portfolio_history['drawdown'] * 100,
                mode='lines',
                name='回撤',
                fill='tozeroy',
                line=dict(color='#ff7f0e', width=1)
            ))

            fig.update_layout(
                title="回撤走势",
                xaxis_title="日期",
                yaxis_title="回撤 (%)",
                hovermode='x unified',
                height=400
            )

            st.plotly_chart(fig, use_container_width=True)

        # 交易记录
        if not result.trades.empty:
            st.subheader("📋 交易记录")

            st.dataframe(
                result.trades,
                use_container_width=True,
                height=300
            )

        # 持仓详情
        st.markdown("---")
        st.subheader("📊 持仓详情")

        if not result.portfolio_history.empty:
            # 提供两种查看方式
            view_mode = st.radio(
                "查看方式",
                ["📋 列表视图", "📊 可折叠详情"],
                horizontal=True,
                key="portfolio_view_mode"
            )

            if view_mode == "📋 列表视图":
                # 简洁的表格视图
                portfolio_df = result.portfolio_history.copy()

                # 去重
                portfolio_df = portfolio_df.drop_duplicates(subset=['date'], keep='last')

                # 添加中文星期
                try:
                    portfolio_df['date_display'] = portfolio_df['date'].apply(
                        lambda x: datetime.strptime(x, '%Y%m%d').strftime('%Y-%m-%d')
                    )
                    portfolio_df['weekday'] = portfolio_df['date'].apply(
                        lambda x: datetime.strptime(x, '%Y%m%d').strftime('%A')
                    )
                    weekdays = {'Monday': '周一', 'Tuesday': '周二', 'Wednesday': '周三',
                               'Thursday': '周四', 'Friday': '周五', 'Saturday': '周六', 'Sunday': '周日'}
                    portfolio_df['weekday_cn'] = portfolio_df['weekday'].map(weekdays)
                except:
                    portfolio_df['date_display'] = portfolio_df['date']
                    portfolio_df['weekday_cn'] = ''

                # 显示关键列
                display_cols = ['date_display', 'weekday_cn', 'value', 'position_count']
                if 'daily_return' in portfolio_df.columns:
                    display_cols.append('daily_return')
                if 'total_return' in portfolio_df.columns:
                    display_cols.append('total_return')

                st.dataframe(
                    portfolio_df[display_cols].rename(columns={
                        'date_display': '日期',
                        'weekday_cn': '星期',
                        'value': '总资产',
                        'position_count': '持仓数',
                        'daily_return': '当日收益率',
                        'total_return': '累计收益率'
                    }),
                    use_container_width=True,
                    height=400
                )

            else:
                # 详细的折叠视图
                with st.expander("📊 查看每日持仓详情", expanded=True):
                    portfolio_df = result.portfolio_history.copy()

                    # 去重并倒序
                    portfolio_df = portfolio_df.drop_duplicates(subset=['date'], keep='last')
                    portfolio_df = portfolio_df.iloc[::-1].reset_index(drop=True)

                    # 显示最近10天的详情
                    for idx, row in portfolio_df.head(10).iterrows():
                        try:
                            dt = datetime.strptime(row['date'], '%Y%m%d')
                            date_display = dt.strftime('%Y-%m-%d')
                            weekday = dt.strftime('%A')
                            weekdays = {'Monday': '周一', 'Tuesday': '周二', 'Wednesday': '周三',
                                       'Thursday': '周四', 'Friday': '周五', 'Saturday': '周六', 'Sunday': '周日'}
                            weekday_display = weekdays.get(weekday, weekday)
                        except:
                            date_display = row['date']
                            weekday_display = ''

                        st.markdown(f"**{int(row['value']):,.0f}**  *  **{date_display}{weekday_display}**")

                        # 显示持仓股票
                        if 'positions' in row and isinstance(row['positions'], list):
                            positions_str = "  ".join([f"{i}.{stock}" for i, stock in enumerate(row['positions'][:10], 1)])
                            if len(row['positions']) > 10:
                                positions_str += f" ... 等{len(row['positions'])}只"
                            st.markdown(positions_str)
                        else:
                            st.markdown("*无持仓*")

                        # 显示指标
                        metrics = []
                        if 'daily_return' in row:
                            metrics.append(f"当日: {row['daily_return']*100:+.2f}%")
                        if 'total_return' in row:
                            metrics.append(f"累计: {row['total_return']*100:+.2f}%")
                        if 'position_count' in row:
                            metrics.append(f"持仓: {row['position_count']}只")

                        if metrics:
                            st.markdown(" | ".join(metrics))

                        st.markdown("---")

        else:
            st.info("暂无持仓数据")


def page_analysis():
    """结果分析页面"""
    st.header("📈 结果分析")

    if st.session_state.backtest_result is None:
        st.warning("⚠️ 请先运行回测")
        return

    result = st.session_state.backtest_result
    perf = result.performance

    # 详细性能指标
    st.subheader("🎯 性能指标详情")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 收益指标")
        st.metric("初始资金", f"¥{perf.get('initial_cash', 0):,.2f}")
        st.metric("最终资金", f"¥{perf.get('final_value', 0):,.2f}")
        st.metric("总收益", f"¥{perf.get('final_value', 0) - perf.get('initial_cash', 0):,.2f}")
        st.metric("总收益率", f"{perf.get('total_return', 0):.2%}")
        st.metric("年化收益率", f"{perf.get('annual_return', 0):.2%}")

    with col2:
        st.markdown("### 风险指标")
        st.metric("最大回撤", f"{perf.get('max_drawdown', 0):.2%}")
        sharpe = perf.get('sharpe_ratio', 0)
        st.metric("夏普比率", f"{sharpe:.2f}" if sharpe else "N/A")
        st.metric("波动率", f"{perf.get('volatility', 0):.2%}")

    st.markdown("---")

    # 统计摘要
    st.subheader("📊 统计摘要")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("交易天数", f"{len(result.portfolio_history)}")
    with col2:
        st.metric("交易次数", f"{len(result.trades)}")
    with col3:
        if not result.returns.empty:
            win_rate = (result.returns > 0).sum() / len(result.returns)
            st.metric("胜率", f"{win_rate:.2%}")

    st.markdown("---")

    # 持仓详情
    st.subheader("📋 持仓详情")

    if not result.portfolio_history.empty:
        # 创建可展开的区域显示持仓详情
        with st.expander("📊 查看每日持仓详情", expanded=True):
            # 获取持仓详情DataFrame
            portfolio_df = result.portfolio_history

            # 去重
            portfolio_df = portfolio_df.drop_duplicates(subset=['date'], keep='last')

            # 倒序显示
            portfolio_df = portfolio_df.iloc[::-1].reset_index(drop=True)

            # 格式化显示
            for idx, row in portfolio_df.iterrows():
                # 转换日期格式
                try:
                    from datetime import datetime
                    dt = datetime.strptime(row['date'], '%Y%m%d')
                    date_display = dt.strftime('%Y-%m-%d')
                    weekday = dt.strftime('%A')
                    weekdays = {'Monday': '周一', 'Tuesday': '周二', 'Wednesday': '周三',
                               'Thursday': '周四', 'Friday': '周五', 'Saturday': '周六', 'Sunday': '周日'}
                    weekday_display = weekdays.get(weekday, weekday)
                except:
                    date_display = row['date']
                    weekday_display = ''

                # 创建两列布局
                col1, col2 = st.columns([3, 2])

                with col1:
                    st.markdown(f"**{int(row['value']):,.0f}**")
                    st.markdown(f"**{date_display}{weekday_display}**")

                    # 显示持仓股票
                    if 'positions' in row and isinstance(row['positions'], list):
                        for i, stock in enumerate(row['positions'], 1):
                            st.markdown(f"{i}. `{stock}`")
                    else:
                        st.markdown("*无持仓*")

                with col2:
                    # 显示指标
                    metrics_data = []
                    if 'position_count' in row:
                        metrics_data.append(f"持仓数: {row['position_count']}")
                    if 'daily_return' in row:
                        metrics_data.append(f"当日收益: {row['daily_return']*100:.2f}%")
                    if 'total_return' in row:
                        metrics_data.append(f"累计收益: {row['total_return']*100:.2f}%")
                    if 'win_rate' in row:
                        metrics_data.append(f"胜率: {row['win_rate']*100:.2f}%")

                    for metric in metrics_data:
                        st.markdown(f"**{metric}**")

                st.markdown("---")
    else:
        st.info("暂无持仓数据")


def page_code_generation():
    """实盘代码生成页面"""
    st.header("💻 实盘代码生成")

    if st.session_state.config is None:
        st.warning("⚠️ 请先从侧边栏加载或上传配置文件")
        return

    config = st.session_state.config

    # 策略信息
    st.info(f"""
    **当前策略**: {config.name}

    **描述**: {config.description}

    此功能将根据当前配置自动生成完整的实盘交易代码。
    """)

    st.markdown("---")

    # 生成选项
    col1, col2 = st.columns(2)

    with col1:
        output_dir = st.text_input(
            "输出目录",
            value=str(project_root / 'easyxt_backtest' / 'live_strategies' / config.name.replace(' ', '_')),
            help="实盘代码输出目录"
        )

    with col2:
        account_id = st.text_input(
            "QMT账户ID",
            value="your_account",
            help="QMT账户ID"
        )

    # 生成代码
    if st.button("⚙️ 生成实盘代码", type="primary", use_container_width=True):
        with st.spinner("⏳ 正在生成实盘代码..."):
            try:
                # 更新配置中的账户ID
                if not config.live_trading_config:
                    config.live_trading_config = {}
                config.live_trading_config['account_id'] = account_id

                # 生成代码
                generator = LiveCodeGenerator()
                files_created = generator.generate_live_strategy(config, output_dir)

                st.session_state.generated_code_path = output_dir

                st.success("✅ 实盘代码生成完成！")

                # 显示生成的文件
                st.markdown("### 📁 生成的文件")

                for file_type, file_path in files_created.items():
                    file_name = Path(file_path).name
                    st.markdown(f"- **{file_type}**: `{file_name}`")

                st.balloons()

            except Exception as e:
                st.error(f"❌ 代码生成失败: {e}")
                st.exception(e)

    # 显示生成结果
    if st.session_state.generated_code_path:
        st.markdown("---")

        output_path = Path(st.session_state.generated_code_path)

        st.subheader("📂 生成的代码结构")

        if output_path.exists():
            # 显示目录结构
            files = list(output_path.glob('*'))

            for file in sorted(files):
                if file.is_file():
                    st.markdown(f"- 📄 `{file.name}`")

            st.markdown("---")

            # README预览
            readme_file = output_path / 'README.md'
            if readme_file.exists():
                with st.expander("📖 查看README"):
                    readme_content = readme_file.read_text(encoding='utf-8')
                    st.markdown(readme_content)

            # main.py预览
            main_file = output_path / 'main.py'
            if main_file.exists():
                with st.expander("💻 查看main.py"):
                    main_content = main_file.read_text(encoding='utf-8')
                    st.code(main_content, language='python')

            # 使用说明
            st.info(f"""
            💡 **使用方法**:

            1. 进入输出目录:
               ```bash
               cd {output_path}
               ```

            2. 配置QMT账户ID:
               编辑 `main.py`，修改 `account_id` 为你的QMT账户

            3. 运行实盘策略:
               ```bash
               python main.py
               ```

            4. 生成的文件包括:
               - `strategy_config.py`: 策略配置
               - `strategy_logic.py`: 策略逻辑
               - `order_manager.py`: 订单管理
               - `risk_control.py`: 风险控制
               - `main.py`: 主程序
               - `README.md`: 使用文档
            """)


def main():
    """主函数"""
    # 初始化会话状态
    init_session_state()

    # 渲染标题
    render_header()

    # 渲染侧边栏，获取当前页面
    page = render_sidebar()

    # 根据选择渲染不同页面
    if page == "🎨 配置编辑器":
        # 初始化编辑器会话状态
        init_editor_session_state()
        # 渲染配置编辑器
        render_config_editor()
    elif page == "📝 配置管理":
        page_config_management()
    elif page == "🔄 策略回测":
        page_backtest()
    elif page == "📈 结果分析":
        page_analysis()
    elif page == "💻 实盘代码生成":
        page_code_generation()


if __name__ == "__main__":
    main()
