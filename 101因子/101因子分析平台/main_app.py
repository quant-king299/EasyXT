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

    # QMT 自动启动并登录（仅尝试一次）
    if 'qmt_login_attempted' not in st.session_state:
        st.session_state.qmt_login_attempted = True
        try:
            sys.path.insert(0, str(main_project_root))
            from core.auto_login import QMTAutoLogin
            login = QMTAutoLogin()
            st.toast("🔐 正在启动 QMT 并自动登录...", icon="⏳")
            success = login.login(restart=False, timeout=60)
            if success:
                st.toast("✅ QMT 登录成功", icon="✅")
            else:
                st.warning("⚠️ QMT 自动登录失败，请检查 .env 或手动启动 QMT")
        except Exception as e:
            st.warning(f"⚠️ QMT 启动异常: {e}")

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
                "📊 策略回测",
                "🔄 网格回测",
                "💻 实盘代码生成"
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
        # 已合并到「📊 策略回测」，重定向提示
        st.info("💡 策略回测已合并到「📊 策略回测」页面，请使用左侧导航中的新入口。")
        if False:  # 保留旧代码以防需要恢复
            pass
        # 旧 YAML 配置回测代码已移除 (2026-06-22)
        # ---------------------------------------------------------------

    elif page == "📊 策略回测":
        try:
            from src.workflow.cb_backtest_page import page as cb_page
            cb_page()
        except Exception as e:
            st.error(f"加载策略回测失败: {e}")
            import traceback
            st.code(traceback.format_exc())

    elif page == "🔧 技术指标回测":
        # 已合并到「📊 策略回测」
        st.info("💡 技术指标回测已合并到「📊 策略回测」页面，请使用左侧导航中的新入口。")

    # ---- 以下为保留的旧代码，不再使用 ----
    # 原 "🎯 策略回测" (YAML配置回测) 和 "🔧 技术指标回测" 的旧实现已删除
    # 相关代码请参见 git history
    # ---- 结束 ----

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
