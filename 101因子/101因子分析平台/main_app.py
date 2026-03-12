# -*- coding: utf-8 -*-
"""
101因子分析平台 - 主应用入口
提供多页面导航
"""
import streamlit as st
import sys
import os
from pathlib import Path

# 添加项目路径
project_path = Path(__file__).parent
sys.path.insert(0, str(project_path))


def render_main_page():
    """渲染主页面"""
    st.title("🎯 101因子分析平台")
    st.markdown("---")

    st.markdown("""
    ## 欢迎使用101因子分析平台！

    这是一个功能强大的量化研究平台，提供：

    ### 📊 因子分析
    - 支持191个Alpha因子（Alpha101 + Alpha191）
    - IC/IR分析
    - 因子相关性分析
    - 分层回测

    ### 🎯 策略回测
    - 完整的回测框架
    - 小市值策略
    - 网格交易策略（固定/自适应/ATR）
    - 因子策略
    - 自定义策略

    ### 📈 工作流
    - 可视化策略构建
    - 拖拽式操作
    - 实时结果展示

    ---

    ### 🚀 快速开始

    请从左侧导航栏选择功能模块。
    """)

    # 平台特性
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div style='padding: 1.5rem; background: white; border-radius: 15px;
                    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
                    border-left: 5px solid #667eea;'>
            <h3 style='color: #667eea;'>📊 因子计算</h3>
            <p>191个Alpha因子<br/>40+基础操作符<br/>向量化计算</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style='padding: 1.5rem; background: white; border-radius: 15px;
                    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
                    border-left: 5px solid #FF6B6B;'>
            <h3 style='color: #FF6B6B;'>🎯 策略回测</h3>
            <p>完整交易模拟<br/>专业绩效分析<br/>多策略支持</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div style='padding: 1.5rem; background: white; border-radius: 15px;
                    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
                    border-left: 5px solid #4ECDC4;'>
            <h3 style='color: #4ECDC4;'>📈 可视化</h3>
            <p>交互式图表<br/>实时结果<br/>拖拽操作</p>
        </div>
        """, unsafe_allow_html=True)


def main():
    """主应用"""

    # 页面配置
    st.set_page_config(
        page_title="101因子分析平台",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 自定义CSS
    st.markdown("""
    <style>
        .main {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
    </style>
    """, unsafe_allow_html=True)

    # 侧边栏导航
    with st.sidebar:
        st.markdown("""
        <div style='text-align: center; padding: 1rem;'>
            <h1 style='color: #667eea; margin: 0;'>🎯</h1>
            <h2 style='color: #667eea; margin: 0.5rem 0;'>101因子平台</h2>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        page = st.radio(
            "📂 选择功能",
            [
                "🏠 主页",
                "🎯 策略回测",
                "🔄 网格回测",
                "📊 因子工作流",
                "📈 因子分析"
            ],
            index=0
        )

        st.markdown("---")

        st.markdown("""
        <div style='padding: 1rem; background: #f8f9fa; border-radius: 10px;'>
            <p style='margin: 0; font-size: 0.9rem;'>
                <strong>版本:</strong> v2.0<br/>
                <strong>数据源:</strong> EasyXT<br/>
                <strong>因子数:</strong> 191个
            </p>
        </div>
        """, unsafe_allow_html=True)

    # 路由到不同页面
    if page == "🏠 主页":
        render_main_page()

    elif page == "🎯 策略回测":
        from src.workflow.strategy_backtest_page import render_strategy_backtest_page
        render_strategy_backtest_page()

    elif page == "🔄 网格回测":
        from src.workflow.grid_backtest_page import page as grid_backtest_page
        grid_backtest_page()

    elif page == "📊 因子工作流":
        # 使用原有的工作流UI
        from src.workflow.ui_enhanced import WorkflowUIEnhanced
        ui = WorkflowUIEnhanced()
        ui.run()

    elif page == "📈 因子分析":
        st.title("📈 因子分析")
        st.info("因子分析功能开发中...")

        st.markdown("""
        ### 即将推出

        - IC/IR分析
        - 因子相关性分析
        - 因子有效性检验
        - 分层回测
        """)


if __name__ == "__main__":
    main()
