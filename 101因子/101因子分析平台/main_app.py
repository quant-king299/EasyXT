# -*- coding: utf-8 -*-
"""
101因子量化策略平台 - 完整流程
因子分析 → 信号生成 → 组合构建 → 回测验证 → 实盘部署
"""
import streamlit as st
import sys
from pathlib import Path
import os
import pandas as pd
import plotly.graph_objects as go

# ========== 路径配置（使用绝对路径） ==========
# 获取当前脚本所在目录
current_dir = Path(__file__).parent.resolve()

# 计算主项目根目录
# 当前文件在: EasyXT/101因子/101因子分析平台/main_app.py
# 需要向上2层到达: EasyXT/
main_project_root = current_dir.parent.parent.resolve()

# 添加到Python路径
if str(main_project_root) not in sys.path:
    sys.path.insert(0, str(main_project_root))

if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# 打印调试信息
print(f"[DEBUG] current_dir: {current_dir}")
print(f"[DEBUG] main_project_root: {main_project_root}")
print(f"[DEBUG] easyxt_backtest path: {main_project_root / 'easyxt_backtest'}")
print(f"[DEBUG] easyxt_backtest exists: {(main_project_root / 'easyxt_backtest').exists()}")


# ============================================================================
# 页面函数
# ============================================================================

def render_home_page():
    """渲染主页面"""
    st.title("🎯 101因子量化策略平台")
    st.markdown("---")

    st.markdown("""
    <div style='text-align: center; padding: 2rem 0;'>
        <h2 style='color: #667eea; margin-bottom: 1rem;'>🚀 核心设计理念</h2>
        <div style='display: flex; justify-content: center; align-items: center; gap: 1rem; flex-wrap: wrap;'>
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white; padding: 1rem 2rem; border-radius: 15px;
                        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);'>
                <h3 style='margin: 0;'>📊 因子分析</h3>
                <p style='margin: 0.5rem 0 0 0; font-size: 0.9rem;'>191个Alpha因子</p>
            </div>
            <div style='font-size: 2rem; color: #667eea;'>→</div>
            <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                        color: white; padding: 1rem 2rem; border-radius: 15px;
                        box-shadow: 0 4px 15px rgba(245, 87, 108, 0.4);'>
                <h3 style='margin: 0;'>⚡ 信号生成</h3>
                <p style='margin: 0.5rem 0 0 0; font-size: 0.9rem;'>多因子模型</p>
            </div>
            <div style='font-size: 2rem; color: #667eea;'>→</div>
            <div style='background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                        color: white; padding: 1rem 2rem; border-radius: 15px;
                        box-shadow: 0 4px 15px rgba(79, 172, 254, 0.4);'>
                <h3 style='margin: 0;'>🎯 组合构建</h3>
                <p style='margin: 0.5rem 0 0 0; font-size: 0.9rem;'>权重优化</p>
            </div>
            <div style='font-size: 2rem; color: #667eea;'>→</div>
            <div style='background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
                        color: white; padding: 1rem 2rem; border-radius: 15px;
                        box-shadow: 0 4px 15px rgba(67, 233, 123, 0.4);'>
                <h3 style='margin: 0;'>📈 回测验证</h3>
                <p style='margin: 0.5rem 0 0 0; font-size: 0.9rem;'>绩效分析</p>
            </div>
            <div style='font-size: 2rem; color: #667eea;'>→</div>
            <div style='background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
                        color: white; padding: 1rem 2rem; border-radius: 15px;
                        box-shadow: 0 4px 15px rgba(250, 112, 154, 0.4);'>
                <h3 style='margin: 0;'>🚀 实盘部署</h3>
                <p style='margin: 0.5rem 0 0 0; font-size: 0.9rem;'>自动化交易</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # 使用指南
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### 🚀 快速开始

        1. **因子分析**
           → 使用"📊 因子工作流"研究因子

        2. **配置策略**
           → 使用"📝 配置编辑器"创建配置

        3. **运行回测**
           → 使用"🎯 策略回测"验证策略（**注意：使用2024年数据！**）

        4. **分析结果**
           → 使用"📊 结果分析"查看详情
        """)

    with col2:
        st.markdown("""
        ### 📖 数据说明

        **可用数据范围**：
        - ✅ 2024年全年（价格+市值）
        - ❌ 2020-2023年（无市值数据）

        **推荐回测期间**：
        - 开始：2024-01-02
        - 结束：2024-12-31

        **数据来源**：
        - DuckDB本地数据库
        - QMT实时数据
        - Tushare在线API
        """)

    st.info("""
    ### 🔥 最新功能

    - ✅ 完整的策略回测框架
    - ✅ 配置编辑器（可视化YAML编辑）
    - ✅ 持仓详情展示
    - ✅ 调仓日期优化
    - ✅ 基本面数据自动填充
    - ✅ 实盘代码生成
    """)


def render_control_panel():
    """控制面板"""
    st.title("🎛️ 控制面板")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(label="📊 因子库", value="191个", delta="Alpha101+191")

    with col2:
        st.metric(label="🎯 策略数", value="5个", delta="小市值/网格/自定义")

    with col3:
        st.metric(label="📈 数据源", value="3个", delta="DuckDB/QMT/Tushare")

    with col4:
        st.metric(label="🔗 系统状态", value="正常", delta="在线")


def main():
    """主应用"""

    # 页面配置
    st.set_page_config(
        page_title="101因子量化策略平台",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 初始化session state
    if 'config' not in st.session_state:
        st.session_state.config = None
    if 'backtest_result' not in st.session_state:
        st.session_state.backtest_result = None
    if 'generated_code_path' not in st.session_state:
        st.session_state.generated_code_path = None

    # 侧边栏导航
    with st.sidebar:
        st.markdown("""
        <div style='text-align: center; padding: 1rem;'>
            <h1 style='color: #667eea; margin: 0;'>🎯</h1>
            <h2 style='color: #667eea; margin: 0.5rem 0;'>量化策略平台</h2>
            <p style='font-size: 0.8rem; color: #666;'>完整流程支持</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # 分组导航
        st.markdown("""
        <div style='padding: 0.5rem; background: #e8f4f8; border-radius: 10px; margin-bottom: 0.5rem;'>
            <p style='margin: 0; font-size: 0.85rem; font-weight: bold; color: #667eea;'>
                🏠 首页
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        st.markdown("""
        <div style='padding: 0.5rem; background: #e8f4f8; border-radius: 10px; margin-bottom: 0.5rem;'>
            <p style='margin: 0; font-size: 0.85rem; font-weight: bold; color: #667eea;'>
                📊 研究工具
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        st.markdown("""
        <div style='padding: 0.5rem; background: #e8f4f8; border-radius: 10px; margin-bottom: 0.5rem;'>
            <p style='margin: 0; font-size: 0.85rem; font-weight: bold; color: #667eea;'>
                🎯 策略开发
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        st.markdown("""
        <div style='padding: 0.5rem; background: #e8f4f8; border-radius: 10px; margin-bottom: 0.5rem;'>
            <p style='margin: 0; font-size: 0.85rem; font-weight: bold; color: #667eea;'>
                🚀 部署运维
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # 配置管理区域
        st.markdown("### 📋 配置管理")

        # 显示当前配置状态
        if st.session_state.config is not None:
            config = st.session_state.config
            st.success(f"✅ 已加载配置")
            st.info(f"**{config.name}**")
            st.caption(f"版本: {config.version}")
            if st.button("🔄 清除配置", key="clear_config_sidebar"):
                st.session_state.config = None
                st.session_state.backtest_result = None
                st.rerun()
        else:
            st.warning("⚠️ 未加载配置")

        st.markdown("---")

        # 上传配置文件
        st.markdown("### 📤 上传配置")
        uploaded_file = st.file_uploader(
            "选择YAML文件",
            type=['yaml', 'yml'],
            key="sidebar_config_upload",
            label_visibility="collapsed"
        )

        if uploaded_file is not None:
            try:
                import tempfile
                import yaml
                from easyxt_backtest.config import load_strategy_config

                # 保存到临时文件
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
                    f.write(uploaded_file.getvalue().decode('utf-8'))
                    temp_path = f.name

                # 加载配置
                config = load_strategy_config(temp_path)
                st.session_state.config = config
                st.success(f"✅ 配置加载成功: {config.name}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 加载失败: {e}")

        st.markdown("---")

        # 导航菜单
        page = st.radio(
            "功能导航",
            [
                "🏠 平台首页",
                "🎛️ 控制面板",
                "📊 因子工作流",
                "📝 配置编辑器",
                "📁 配置管理",
                "🎯 策略回测",
                "📊 结果分析",
                "💻 实盘代码生成",
                "🔄 网格回测"
            ],
            index=0,
            label_visibility="collapsed"
        )

        st.markdown("---")

        st.markdown(f"""
        <div style='padding: 0.5rem; background: #f8f9fa; border-radius: 10px;'>
            <p style='margin: 0; font-size: 0.8rem;'>
                <strong>路径配置</strong><br/>
                主目录: {main_project_root.name}<br/>
                <br/>
                <strong>📦 核心功能</strong><br/>
                • 191个Alpha因子<br/>
                • 完整回测框架<br/>
                • 实盘部署支持<br/>
                <br/>
                <strong>🔧 最新修复</strong><br/>
                • 调仓日期优化<br/>
                • 数据自动填充
            </p>
        </div>
        """, unsafe_allow_html=True)

    # 路由到不同页面
    if page == "🏠 平台首页":
        render_home_page()

    elif page == "🎛️ 控制面板":
        render_control_panel()

    elif page == "📊 因子工作流":
        try:
            from src.workflow.ui_enhanced import WorkflowUIEnhanced
            ui = WorkflowUIEnhanced()
            ui.run()
        except Exception as e:
            st.error(f"加载因子工作流失败: {e}")
            import traceback
            st.code(traceback.format_exc())

    elif page == "📝 配置编辑器":
        try:
            from easyxt_backtest.web_app.config_editor import render_config_editor
            from easyxt_backtest.web_app.config_editor import init_editor_session_state
            init_editor_session_state()
            render_config_editor()
        except Exception as e:
            st.error(f"导入配置编辑器失败: {e}")
            import traceback
            st.code(traceback.format_exc())

    elif page == "📁 配置管理":
        try:
            from easyxt_backtest.web_app.streamlit_app import page_config_management
            page_config_management()
        except Exception as e:
            st.error(f"导入配置管理失败: {e}")
            import traceback
            st.code(traceback.format_exc())

    elif page == "🎯 策略回测":
        st.title("🎯 策略回测")

        if st.session_state.config is None:
            st.warning("⚠️ 请先从「📝 配置编辑器」或「📁 配置管理」加载配置文件")
            st.info("💡 提示：您可以在配置编辑器中上传YAML文件，或在配置管理中选择已有配置")
        else:
            config = st.session_state.config

            # 使用选项卡展示配置详情
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📋 策略配置",
                "🔬 因子配置",
                "⚙️ 回测设置",
                "💾 数据源",
                "🛡️ 风控模型"
            ])

            with tab1:
                st.markdown("### 基本信息")
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("策略名称", config.name)
                with col2:
                    st.metric("版本", config.version)
                with col3:
                    st.metric("描述", config.description if hasattr(config, 'description') and config.description else "无")

                st.markdown("---")

                st.markdown("### 股票池配置")
                if hasattr(config, 'stock_pool') and config.stock_pool:
                    pool_type = config.stock_pool.get('type', 'unknown')
                    st.info(f"**类型**: {pool_type}")

                    if pool_type == 'index_constituents':
                        index_code = config.stock_pool.get('index_code', '未知')
                        st.info(f"**指数代码**: {index_code}")
                    elif pool_type == 'custom':
                        symbols = config.stock_pool.get('symbols', [])
                        st.info(f"**股票数量**: {len(symbols)}")
                        if symbols:
                            with st.expander("查看股票列表"):
                                st.write(symbols)
                else:
                    st.warning("未配置股票池")

            with tab2:
                st.markdown("### 评分因子")

                if hasattr(config, 'scoring_factors') and config.scoring_factors:
                    factors_df = []
                    for factor in config.scoring_factors:
                        factors_df.append({
                            '因子名称': factor.name,
                            '因子类型': factor.factor_type,
                            '权重': factor.weight,
                            '方向': factor.direction,
                            '参数': str(factor.params) if factor.params else '默认'
                        })

                    df = pd.DataFrame(factors_df)
                    st.dataframe(df, use_container_width=True)

                    st.markdown(f"**总计**: {len(config.scoring_factors)} 个因子")
                else:
                    st.warning("未配置评分因子")

                st.markdown("---")

                st.markdown("### 剔除因子")
                if hasattr(config, 'filtering_factors') and config.filtering_factors:
                    for factor in config.filtering_factors:
                        with st.expander(f"🔹 {factor.name}"):
                            st.write(f"**类型**: {factor.factor_type}")
                            st.write(f"**参数**: {factor.params}")
                else:
                    st.info("未配置剔除因子")

            with tab3:
                st.markdown("### 回测参数")

                if hasattr(config, 'backtest_config'):
                    bt_config = config.backtest_config

                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**时间范围**")
                        start_date = st.text_input(
                            "开始日期",
                            value=bt_config.get('start_date', '20240102'),
                            help="格式: YYYYMMDD"
                        )
                        end_date = st.text_input(
                            "结束日期",
                            value=bt_config.get('end_date', '20241231'),
                            help="格式: YYYYMMDD"
                        )

                    with col2:
                        st.markdown("**资金与费用**")
                        initial_cash = st.number_input(
                            "初始资金",
                            value=float(bt_config.get('initial_cash', 1000000.0)),
                            min_value=10000.0,
                            step=100000.0
                        )
                        commission = st.number_input(
                            "手续费率",
                            value=bt_config.get('commission', 0.0003),
                            min_value=0.0,
                            max_value=0.01,
                            step=0.0001,
                            format="%.4f"
                        )

                    st.markdown("---")

                    st.markdown("**调仓频率**")
                    rebalance_freq = bt_config.get('rebalance_frequency', 'monthly')
                    freq_options = {
                        'daily': '每日',
                        'weekly': '每周',
                        'monthly': '每月',
                        'quarterly': '每季度'
                    }
                    st.info(f"**当前设置**: {freq_options.get(rebalance_freq, rebalance_freq)}")

            with tab4:
                st.markdown("### 数据源配置")

                st.markdown("**可用数据源**")
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.success("**DuckDB**")
                    st.caption("✅ 已连接")
                    st.caption("📍 D:/StockData/")
                    st.caption("📊 2024年价格+市值数据")

                with col2:
                    st.info("**QMT**")
                    st.caption("🔄 可选")
                    st.caption("⚡ 实时数据接口")

                with col3:
                    st.info("**Tushare**")
                    st.caption("🔄 可选")
                    st.caption("🌐 在线数据API")

                st.markdown("---")

                use_real_data = st.checkbox(
                    "📡 使用DuckDB真实数据",
                    value=True,
                    help="勾选后使用DuckDB中的历史数据"
                )

                if use_real_data:
                    st.success("✅ 将使用DuckDB数据（支持基本面因子）")
                else:
                    st.warning("⚠️ 将使用模拟数据（仅支持技术因子）")

            with tab5:
                st.markdown("### 组合构建")

                if hasattr(config, 'portfolio_config'):
                    port_config = config.portfolio_config

                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**持仓数量**")
                        if 'target_position_count' in port_config:
                            st.info(f"目标持仓数: {port_config['target_position_count']}")

                        st.markdown("**权重方式**")
                        weight_method = port_config.get('weighting_method', 'equal_weight')
                        method_names = {
                            'equal_weight': '等权重',
                            'market_cap_weight': '市值加权',
                            'factor_weight': '因子加权'
                        }
                        st.success(f"**{method_names.get(weight_method, weight_method)}**")

                    with col2:
                        st.markdown("**选股方式**")
                        if 'selection_method' in port_config:
                            st.info(f"{port_config['selection_method']}")

                        st.markdown("**调仓日期**")
                        st.info("每月第一个交易日")
                else:
                    st.warning("未配置组合构建参数")

            st.markdown("---")
            st.markdown("---")

            # 运行回测按钮
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🚀 开始回测", type="primary", use_container_width=True):
                    with st.spinner("⏳ 正在运行回测..."):
                        try:
                            from easyxt_backtest.data import create_data_manager
                            from easyxt_backtest.strategies.config_driven_strategy import ConfigDrivenStrategy
                            from easyxt_backtest.enhanced_backtest_engine import EnhancedBacktestEngine

                            # 创建数据管理器
                            data_manager = None
                            if use_real_data:
                                try:
                                    data_manager = create_data_manager()
                                    st.info("✅ 已连接数据源")
                                except Exception as e:
                                    st.warning(f"⚠️ 数据源连接失败: {e}")
                                    data_manager = None

                            # 创建策略
                            strategy = ConfigDrivenStrategy(config, data_manager=data_manager)

                            # 创建回测引擎
                            engine = EnhancedBacktestEngine(
                                initial_cash=initial_cash,
                                commission=commission,
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
                            import traceback
                            with st.expander("查看错误详情"):
                                st.code(traceback.format_exc())

            # 显示回测结果
            if st.session_state.backtest_result:
                st.markdown("---")
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

                    portfolio_history = result.portfolio_history.copy()
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
                        key="portfolio_view_mode_main"
                    )

                    if view_mode == "📋 列表视图":
                        # 简洁的表格视图
                        portfolio_df = result.portfolio_history.copy()

                        # 去重
                        portfolio_df = portfolio_df.drop_duplicates(subset=['date'], keep='last')

                        # 添加中文星期
                        try:
                            from datetime import datetime
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

    elif page == "📊 结果分析":
        try:
            from easyxt_backtest.web_app.streamlit_app import page_analysis
            page_analysis()
        except Exception as e:
            st.error(f"导入结果分析失败: {e}")
            import traceback
            st.code(traceback.format_exc())

    elif page == "💻 实盘代码生成":
        try:
            from easyxt_backtest.web_app.streamlit_app import page_code_generation
            page_code_generation()
        except Exception as e:
            st.error(f"导入代码生成失败: {e}")
            import traceback
            st.code(traceback.format_exc())

    elif page == "🔄 网格回测":
        try:
            from src.workflow.grid_backtest_page import page as grid_backtest_page
            grid_backtest_page()
        except Exception as e:
            st.error(f"加载网格回测失败: {e}")
            import traceback
            st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
