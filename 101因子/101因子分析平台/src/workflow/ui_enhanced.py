"""
工作流UI模块 - 增强版
提供现代化、美观的可视化工作流界面
"""
import streamlit as st
import pandas as pd
import numpy as np
import json
import sys
import os
from typing import Dict, Any

# 添加项目路径
project_path = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_path)

from src.workflow.engine import WorkflowEngine
from src.factor_engine.factor_metadata import list_all_factors


# ===================== 自定义CSS样式 =====================
CUSTOM_CSS = """
<style>
    /* 全局样式 */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 0;
    }

    /* 顶部标题栏 */
    .header-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    }

    .header-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: white;
        text-align: center;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
    }

    .header-subtitle {
        font-size: 1rem;
        color: rgba(255, 255, 255, 0.9);
        text-align: center;
        margin-top: 0.5rem;
    }

    /* 卡片样式 */
    .node-card {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
        border-left: 5px solid;
        position: relative;
        overflow: hidden;
    }

    .node-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
    }

    .node-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 5px;
        background: linear-gradient(90deg, var(--card-color, #667eea), transparent);
    }

    /* 节点图标 */
    .node-icon {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        display: inline-block;
        animation: float 3s ease-in-out infinite;
    }

    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
    }

    /* 节点标题 */
    .node-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #2c3e50;
        margin: 0.5rem 0;
    }

    /* 参数标签 */
    .param-label {
        font-size: 0.85rem;
        color: #7f8c8d;
        font-weight: 500;
        margin-bottom: 0.25rem;
    }

    .param-value {
        font-size: 0.95rem;
        color: #2c3e50;
        background: #f8f9fa;
        padding: 0.5rem;
        border-radius: 8px;
        margin-bottom: 0.75rem;
        font-family: 'Courier New', monospace;
    }

    /* 统计卡片 */
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 1.5rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
    }

    .stat-card:hover {
        transform: scale(1.05);
    }

    .stat-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }

    .stat-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }

    /* 按钮样式 */
    .custom-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 10px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }

    .custom-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }

    /* 结果展示卡片 */
    .result-card {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }

    .result-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid #ecf0f1;
    }

    .result-icon {
        font-size: 2rem;
    }

    .result-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #2c3e50;
        margin: 0;
    }

    /* 数据表格样式 */
    .dataframe-container {
        background: white;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
    }

    /* 侧边栏样式 */
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%);
    }

    /* 空状态提示 */
    .empty-state {
        text-align: center;
        padding: 3rem;
        background: white;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }

    .empty-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
        opacity: 0.5;
    }

    .empty-text {
        font-size: 1.1rem;
        color: #7f8c8d;
    }

    /* 成功/错误消息 */
    .success-message {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        box-shadow: 0 4px 15px rgba(17, 153, 142, 0.3);
    }

    .error-message {
        background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        box-shadow: 0 4px 15px rgba(235, 51, 73, 0.3);
    }

    /* 节点分类标题 */
    .category-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.75rem 1rem;
        border-radius: 10px;
        font-weight: 600;
        margin: 1.5rem 0 1rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* 工具提示 */
    .tooltip {
        position: relative;
        display: inline-block;
    }

    .tooltip .tooltip-text {
        visibility: hidden;
        width: 200px;
        background-color: #555;
        color: #fff;
        text-align: center;
        border-radius: 6px;
        padding: 5px 0;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        margin-left: -100px;
        opacity: 0;
        transition: opacity 0.3s;
    }

    .tooltip:hover .tooltip-text {
        visibility: visible;
        opacity: 1;
    }

    /* 进度条 */
    .progress-container {
        background: #ecf0f1;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }

    /* 标签页样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        background: white;
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
        font-weight: 600;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }

    /* 响应式调整 */
    @media (max-width: 768px) {
        .header-title {
            font-size: 1.8rem;
        }

        .node-card {
            padding: 1rem;
        }

        .stat-value {
            font-size: 2rem;
        }
    }
</style>
"""


class WorkflowUIEnhanced:
    """
    工作流用户界面 - 增强版
    提供现代化、美观的可视化工作流构建界面
    """

    def __init__(self):
        # 使用Streamlit session state来持久化引擎状态
        if 'workflow_engine' not in st.session_state:
            st.session_state['workflow_engine'] = WorkflowEngine()
        self.engine = st.session_state['workflow_engine']

        # 动态获取所有可用因子
        self.all_factors = list_all_factors()
        print(f"[DEBUG] UI初始化 - 获取到 {len(self.all_factors)} 个因子: {self.all_factors[:10]}...")

        # 节点类型配置（增强版）
        self.node_types = {
            'data_loader': {
                'name': '数据加载',
                'icon': '📊',
                'color': '#3498db',
                'category': '数据处理',
                'description': '加载股票行情数据',
                'params': {
                    'input_mode': {'type': 'select', 'label': '输入模式', 'options': ['preset', 'custom'], 'default': 'preset'},
                    # 'preset' 参数通过 input_mode 动态处理，不在配置中列出
                    'custom_symbols': {'type': 'text', 'label': '自定义股票代码', 'default': '000001.SZ,000002.SZ'},
                    'start_date': {'type': 'date', 'label': 'start_date', 'default': '2023-01-01'},
                    'end_date': {'type': 'date', 'label': 'end_date', 'default': '2023-12-31'},
                    'fields': {'type': 'multiselect', 'label': '字段', 'options': ['open', 'high', 'low', 'close', 'volume'], 'default': ['open', 'high', 'low', 'close', 'volume']}
                }
            },
            'factor_calculator': {
                'name': '因子计算',
                'icon': '📈',
                'color': '#2ecc71',
                'category': '因子分析',
                'description': f'计算Alpha因子（共{len(self.all_factors)}个）',
                'params': {
                    'factor_name': {'type': 'select', 'label': '因子名称', 'options': self.all_factors, 'default': 'alpha001'}
                }
            },
            'ic_analyzer': {
                'name': 'IC分析',
                'icon': '🔍',
                'color': '#9b59b6',
                'category': '因子分析',
                'description': '计算因子IC/IR值',
                'params': {
                    'periods': {'type': 'number', 'label': '期数', 'default': 1, 'min': 1, 'max': 10}
                }
            },
            'factor_correlation': {
                'name': '因子相关性分析',
                'icon': '🔗',
                'color': '#ff6b9d',
                'category': '因子分析',
                'description': '分析因子间相关性',
                'params': {
                    'threshold': {'type': 'slider', 'label': '相关性阈值', 'default': 0.7, 'min': 0.0, 'max': 1.0, 'step': 0.05},
                    'method': {'type': 'select', 'label': '相关系数方法', 'options': ['spearman', 'pearson'], 'default': 'spearman'},
                    'n_clusters': {'type': 'number', 'label': '聚类数量（留空自动）', 'default': None, 'min': 2, 'max': 10}
                }
            },
            'backtester': {
                'name': '回测引擎',
                'icon': '🧪',
                'color': '#e74c3c',
                'category': '策略回测',
                'description': '执行策略回测（包含完整的绩效分析和分层回测）',
                'params': {
                    'top_quantile': {'type': 'slider', 'label': '做多分位数', 'default': 0.2, 'min': 0.0, 'max': 0.5, 'step': 0.05},
                    'bottom_quantile': {'type': 'slider', 'label': '做空分位数', 'default': 0.2, 'min': 0.0, 'max': 0.5, 'step': 0.05},
                    'transaction_cost': {'type': 'number', 'label': '交易成本', 'default': 0.001, 'min': 0.0, 'max': 0.01, 'step': 0.0001},
                    'weight_method': {
                        'type': 'select',
                        'label': '权重分配方式',
                        'options': [
                            'equal: 等权重（选中股票平均分配）',
                            'fixed_n: 固定N只（选中股票固定数量）',
                            'factor_weighted: 因子值加权（因子值越大权重越高）'
                        ],
                        'default': 'equal'
                    },
                    'fixed_n_stocks': {'type': 'number', 'label': '固定股票数量', 'default': 10, 'min': 1, 'max': 50, 'step': 1, 'help': '当选择"固定N只"模式时，指定做多和做空各选多少只股票'}
                }
            },
            # performance_analyzer 已移除（功能已包含在backtester中）
            # portfolio_optimizer 已移除（单因子回测不需要组合优化）
            'data_processor': {
                'name': '数据处理',
                'icon': '⚙️',
                'color': '#1abc9c',
                'category': '数据处理',
                'description': '数据预处理操作（标准化、去极值、中性化）',
                'params': {
                    'operation': {
                        'type': 'select',
                        'label': '操作类型',
                        'options': [
                            'standardize: 标准化（Z-Score）',
                            'rank: 排名标准化',
                            'neutralize: 因子中性化',
                            'winsorize: 去极值',
                            'fill_na: 填充缺失值'
                        ],
                        'default': 'standardize'
                    },
                    'neutralize_method': {
                        'type': 'select',
                        'label': '中性化方式',
                        'options': [
                            'industry: 行业中性',
                            'market_cap: 市值中性',
                            'both: 行业+市值双重中性'
                        ],
                        'default': 'both'
                    },
                    'winsorize_method': {
                        'type': 'select',
                        'label': '去极值方法',
                        'options': ['mad: MAD法', 'sigma: 3σ法', 'percentile: 百分位法'],
                        'default': 'mad'
                    },
                    'fill_method': {
                        'type': 'select',
                        'label': '缺失值填充方法',
                        'options': ['mean: 均值填充', 'median: 中位数填充', 'ffill: 前向填充', 'zero: 零填充'],
                        'default': 'median'
                    }
                }
            },
            'signal_generator': {
                'name': '信号生成',
                'icon': '🔔',
                'color': '#8e44ad',
                'category': '策略构建',
                'description': '生成交易信号（做多/做空/中性）',
                'params': {
                    'method': {'type': 'select', 'label': '方法', 'options': ['rank', 'value'], 'default': 'rank'},
                    'threshold': {'type': 'slider', 'label': '阈值', 'default': 0.8, 'min': 0.0, 'max': 1.0, 'step': 0.05}
                }
            },
            'risk_manager': {
                'name': '风险管理',
                'icon': '🛡️',
                'color': '#e67e22',
                'category': '策略构建',
                'description': '风险控制管理',
                'params': {
                    'max_position': {'type': 'slider', 'label': '最大头寸', 'default': 0.1, 'min': 0.01, 'max': 0.5, 'step': 0.01}
                }
            }
        }

    def apply_custom_css(self):
        """应用自定义CSS样式"""
        st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    def render_header(self):
        """渲染顶部标题栏"""
        st.markdown("""
        <div class="header-container">
            <h1 class="header-title">101因子分析平台</h1>
            <p class="header-subtitle">专业的量化因子分析与回测系统</p>
        </div>
        """, unsafe_allow_html=True)

        # 统计信息
        if self.engine.nodes:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{len(self.engine.nodes)}</div>
                    <div class="stat-label">工作流节点</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                # 统计不同类型的节点
                node_types = set(node.node_type for node in self.engine.nodes.values())
                st.markdown(f"""
                <div class="stat-card" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">
                    <div class="stat-value">{len(node_types)}</div>
                    <div class="stat-label">节点类型</div>
                </div>
                """, unsafe_allow_html=True)

            with col3:
                results = st.session_state.get('workflow_results')
                executed = len(results) if results else 0
                st.markdown(f"""
                <div class="stat-card" style="background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);">
                    <div class="stat-value">{executed}</div>
                    <div class="stat-label">已执行</div>
                </div>
                """, unsafe_allow_html=True)

            with col4:
                st.markdown(f"""
                <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                    <div class="stat-value">{len(self.all_factors)}</div>
                    <div class="stat-label">Alpha因子</div>
                </div>
                """, unsafe_allow_html=True)

    def render_sidebar(self):
        """渲染侧边栏"""
        # 节点类型选择
        st.subheader("🎨 添加节点")

        # 按分类显示节点
        categories = {}
        for node_type, config in self.node_types.items():
            category = config['category']
            if category not in categories:
                categories[category] = []
            categories[category].append((node_type, config))

        # 使用标签页组织
        category_names = list(categories.keys())
        selected_category = st.selectbox("选择功能分类", category_names)

        # 显示该分类下的节点
        nodes_in_category = categories[selected_category]
        node_options = {config['name']: node_type for node_type, config in nodes_in_category}
        selected_name = st.selectbox("选择节点类型", list(node_options.keys()), key='node_type_select')
        selected_type = node_options[selected_name]

        # 检测节点类型是否改变，如果改变则清空临时参数
        if 'last_selected_type' in st.session_state and st.session_state['last_selected_type'] != selected_type:
            st.session_state['temp_params'] = {}
        st.session_state['last_selected_type'] = selected_type

        # 显示节点描述
        node_config = self.node_types[selected_type]
        st.info(f"**{node_config['icon']} {node_config['name']}**\n\n{node_config['description']}")

        st.markdown("---")

        # 参数配置
        st.markdown("#### ⚙️ 参数配置")

        # 使用 session_state 来持久化参数，避免每次重渲染时丢失
        if 'temp_params' not in st.session_state:
            st.session_state['temp_params'] = {}

        params = st.session_state['temp_params']

        if node_config['params']:
            for param_name, param_config in node_config['params'].items():
                param_label = param_config['label']
                param_default = param_config['default']

                # 特殊处理：数据加载节点的 input_mode 参数
                if selected_type == 'data_loader' and param_name == 'input_mode':
                    # 从 session_state 获取之前的值，如果没有则使用默认值
                    current_input_mode = params.get('input_mode', 'preset')
                    input_mode_index = 0 if current_input_mode == 'preset' else 1

                    input_mode = st.selectbox("输入模式", options=['preset', 'custom'], index=input_mode_index, key='input_mode_select')
                    params['input_mode'] = input_mode

                    # 根据选择显示不同的输入框
                    if input_mode == 'preset':
                        # 显示预设下拉框
                        from src.workflow.stock_presets import PRESET_LIST
                        current_preset = params.get('preset', '📈 沪深A股')

                        selected_preset = st.selectbox(
                            "选择预设类型",
                            options=PRESET_LIST,
                            index=PRESET_LIST.index(current_preset) if current_preset in PRESET_LIST else 0,
                            help="选择常见的股票类型预设",
                            key='preset_select'
                        )
                        # 保存用户的选择
                        params['preset'] = selected_preset

                        # 显示所选预设的股票代码
                        from src.workflow.stock_presets import get_preset_symbols
                        try:
                            preset_symbols = get_preset_symbols(selected_preset)

                            # 显示统计信息
                            st.markdown(f"**📊 股票数量：** `{len(preset_symbols)}` 只")

                            # 显示前10只和后5只
                            if len(preset_symbols) > 15:
                                preview = ', '.join(preset_symbols[:10]) + f' ... (省略 {len(preset_symbols) - 15} 只) ... ' + ', '.join(preset_symbols[-5:])
                            else:
                                preview = ', '.join(preset_symbols)

                            st.markdown(f"**股票代码预览：**")
                            st.code(preview, language=None)

                            # 在expander中显示完整列表
                            with st.expander("📋 查看完整股票列表"):
                                st.text('\n'.join(preset_symbols))
                        except Exception as e:
                            st.warning(f"无法加载预设股票代码: {e}")
                            import traceback
                            st.error(traceback.format_exc())

                    elif input_mode == 'custom':
                        # 显示自定义输入框
                        params['custom_symbols'] = st.text_input(
                            "自定义股票代码",
                            value="000001.SZ,000002.SZ",
                            help="输入逗号分隔的股票代码，如：000001.SZ,000002.SZ"
                        )

                elif param_name == 'custom_symbols':
                    # 只有在选择了custom时才显示这个参数
                    input_mode = params.get('input_mode', 'preset')  # 获取之前选择的input_mode
                    if input_mode == 'custom':
                        params[param_name] = st.text_input("自定义股票代码", value=str(param_default))

                elif param_config['type'] == 'text':
                    params[param_name] = st.text_input(param_label, value=str(param_default))
                elif param_config['type'] == 'number':
                    params[param_name] = st.number_input(
                        param_label,
                        value=param_default,
                        min_value=param_config.get('min', 0),
                        max_value=param_config.get('max', 100),
                        step=param_config.get('step', 1)
                    )
                elif param_config['type'] == 'slider':
                    params[param_name] = st.slider(
                        param_label,
                        value=param_default,
                        min_value=param_config['min'],
                        max_value=param_config['max'],
                        step=param_config['step']
                    )
                elif param_config['type'] == 'select':
                    params[param_name] = st.selectbox(
                        param_label,
                        options=param_config['options'],
                        index=0  # 默认选第一个
                    )
                elif param_config['type'] == 'multiselect':
                    # 处理 multiselect 类型 - 支持多选
                    params[param_name] = st.multiselect(
                        param_label,
                        options=param_config['options'],
                        default=param_default if isinstance(param_config['default'], list) else [param_default]
                    )
                elif param_config['type'] == 'date':
                    import datetime
                    params[param_name] = str(st.date_input(param_label, value=datetime.datetime.strptime(param_default, '%Y-%m-%d')))

                # 特殊处理：因子计算节点显示因子详情
                if selected_type == 'factor_calculator' and param_name == 'factor_name':
                    from src.factor_engine.factor_metadata import get_factor_info
                    factor_info = get_factor_info(params.get('factor_name', 'alpha001'))

                    with st.expander("📖 查看因子详情", expanded=False):
                        # 标题
                        st.markdown(f"### {factor_info.get('icon', '📊')} {factor_info['name']}")
                        st.caption(f"🏷️ {factor_info['category']} · ✍️ {factor_info['author']}")

                        st.markdown("---")

                        # 订式
                        st.markdown("#### 📐 计算公式")
                        st.code(factor_info['formula'], language=None)

                        # 因子说明
                        st.markdown("#### 📝 因子说明")
                        st.info(factor_info['description'])

                        # 逻辑解释
                        st.markdown("#### 💡 逻辑解释")
                        st.warning(factor_info['logic'])

        st.markdown("---")

        # 添加按钮
        if st.button(f"➕ 添加 {node_config['name']}", width="stretch"):
            import random
            position = {
                'x': float(random.randint(100, 700)),
                'y': float(random.randint(100, 500))
            }

            # 特殊处理：数据加载节点需要设置symbols
            if selected_type == 'data_loader':
                print(f"[DEBUG] ========== 开始处理数据加载节点 ==========")
                print(f"[DEBUG] 原始params={params}")

                input_mode = params.get('input_mode', 'preset')
                print(f"[DEBUG] 添加数据加载节点 - input_mode={input_mode}")

                if input_mode == 'preset':
                    # 使用params中保存的preset值
                    preset = params.get('preset', '📈 沪深A股')
                    print(f"[DEBUG] 添加数据加载节点 - preset={preset}")

                    from src.workflow.stock_presets import get_preset_symbols
                    try:
                        symbols = get_preset_symbols(preset)
                        print(f"[DEBUG] 添加数据加载节点 - 获取到的symbols={symbols}")
                        params['symbols'] = symbols
                    except Exception as e:
                        print(f"[DEBUG] 获取preset symbols失败: {e}")
                        # 使用默认值
                        params['symbols'] = ['000001.SZ', '000002.SZ', '600000.SH']
                elif input_mode == 'custom':
                    # 从custom_symbols解析股票代码
                    custom_symbols = params.get('custom_symbols', '000001.SZ,000002.SZ')
                    params['symbols'] = [s.strip() for s in custom_symbols.split(',')]
                else:
                    # 兜底：使用默认值
                    print(f"[DEBUG] 未知的input_mode，使用默认symbols")
                    params['symbols'] = ['000001.SZ', '000002.SZ', '600000.SH']

                print(f"[DEBUG] 添加数据加载节点 - 最终params['symbols']={params.get('symbols', [])}")
                print(f"[DEBUG] ========== 处理数据加载节点结束 ==========")

            # 深拷贝参数，避免所有节点共享同一个字典
            import copy
            params_copy = copy.deepcopy(params)

            node_id = self.engine.add_node(selected_type, position, params_copy)
            st.success(f"✓ 已添加节点: {node_config['name']}")

            # 清空临时参数，准备下一次添加
            st.session_state['temp_params'] = {}

            st.balloons()

        st.markdown("---")

        # 节点概览
        st.markdown("#### 📋 节点概览")
        if len(self.engine.nodes) == 0:
            st.info("💡 请先添加节点")
        else:
            # 按添加顺序显示节点
            st.markdown("**已添加的节点（按添加顺序）:**")
            node_list = list(self.engine.nodes.items())
            for idx, (node_id, node) in enumerate(node_list):
                node_config = self.node_types.get(node.node_type, {})
                icon = node_config.get('icon', '📊')
                name = node_config.get('name', node.node_type)
                st.markdown(f"{idx + 1}. {icon} **{name}**")

            st.info("💡 系统会自动按节点类型推断执行顺序和数据流，无需手动连接")

        st.markdown("---")

        # 工作流管理
        st.markdown("#### 🎯 工作流管理")

        # 使用Tab分离不同功能
        tab1, tab2, tab3 = st.tabs(["执行", "保存", "加载"])

        with tab1:
            if st.button("▶️ 执行工作流", width="stretch"):
                with st.spinner("正在执行工作流..."):
                    try:
                        results = self.engine.execute_workflow()
                        st.session_state['workflow_results'] = results
                        st.success("✓ 工作流执行完成!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"✗ 执行失败: {e}")

            if st.button("🗑️ 清空工作流", width="stretch"):
                st.session_state['workflow_engine'] = WorkflowEngine()
                self.engine = st.session_state['workflow_engine']
                st.session_state['workflow_results'] = None
                st.success("✓ 工作流已清空")
                st.rerun()

            # 添加清理不必要节点的功能
            if self.engine.nodes:
                unnecessary_nodes = [node_id for node_id, node in self.engine.nodes.items()
                                    if node.node_type in ['performance_analyzer', 'portfolio_optimizer']]
                if unnecessary_nodes:
                    st.warning(f"⚠️ 检测到 {len(unnecessary_nodes)} 个不推荐使用的节点（performance_analyzer、portfolio_optimizer）")
                    if st.button("🧹 清理不必要节点", width="stretch"):
                        for node_id in unnecessary_nodes:
                            del self.engine.nodes[node_id]
                        st.success(f"✓ 已清理 {len(unnecessary_nodes)} 个节点")
                        st.rerun()

        with tab2:
            st.markdown("**保存当前工作流**")
            workflow_name = st.text_input("工作流名称", placeholder="例如：单因子回测-动量因子", help="为你的工作流起个名字")
            workflow_desc = st.text_area("工作流描述（可选）", placeholder="描述这个工作流的用途...", height=80)

            # 生成建议的文件名
            if workflow_name:
                import re
                safe_name = re.sub(r'[<>:"/\\|?*]', '_', workflow_name)
                suggested_filename = f"{safe_name}.json"
            else:
                import datetime
                suggested_filename = f"workflow_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            filename = st.text_input("文件名", value=suggested_filename, help="保存在workflows目录下")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 保存", width="stretch"):
                    if filename:
                        if not filename.endswith('.json'):
                            filename += '.json'

                        filepath = os.path.join("workflows", filename)
                        try:
                            self.engine.save_workflow(
                                filepath=filepath,
                                name=workflow_name or filename.replace('.json', ''),
                                description=workflow_desc
                            )
                            st.success(f"✓ 已保存至 {filepath}")
                            # 清空保存缓存以便刷新列表
                            if 'saved_workflows_list' in st.session_state:
                                del st.session_state['saved_workflows_list']
                        except Exception as e:
                            st.error(f"✗ 保存失败: {e}")
                    else:
                        st.warning("请输入文件名")

            with col2:
                if st.button("📋 另存为", width="stretch"):
                    custom_filename = st.text_input("自定义文件名", value=filename)
                    if custom_filename:
                        if not custom_filename.endswith('.json'):
                            custom_filename += '.json'

                        filepath = os.path.join("workflows", custom_filename)
                        try:
                            self.engine.save_workflow(
                                filepath=filepath,
                                name=workflow_name or custom_filename.replace('.json', ''),
                                description=workflow_desc
                            )
                            st.success(f"✓ 已保存至 {filepath}")
                            if 'saved_workflows_list' in st.session_state:
                                del st.session_state['saved_workflows_list']
                        except Exception as e:
                            st.error(f"✗ 保存失败: {e}")

        with tab3:
            st.markdown("**已保存的工作流**")

            # 刷新按钮
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🔄 刷新", width="stretch"):
                    if 'saved_workflows_list' in st.session_state:
                        del st.session_state['saved_workflows_list']
                    st.rerun()

            # 获取工作流列表
            if 'saved_workflows_list' not in st.session_state:
                st.session_state['saved_workflows_list'] = WorkflowEngine.list_saved_workflows()

            workflows = st.session_state['saved_workflows_list']

            if workflows:
                st.markdown(f"**共 {len(workflows)} 个工作流**")

                # 显示工作流列表
                for i, wf in enumerate(workflows):
                    with st.expander(f"📄 {wf['name']}", expanded=False):
                        col1, col2 = st.columns([3, 1])

                        with col1:
                            st.markdown(f"**文件名**: `{wf['filename']}`")
                            if wf['description']:
                                st.markdown(f"**描述**: {wf['description']}")
                            st.markdown(f"""
                            <small style="color: #7f8c8d;">
                            📊 {wf['node_count']} 个节点 |
                            🔗 {wf['connection_count']} 个连接 |
                            📅 {wf['created_at'][:10] if wf['created_at'] else '未知'}
                            </small>
                            """, unsafe_allow_html=True)

                        with col2:
                            if st.button("📂 加载", key=f"load_{i}", width="stretch"):
                                try:
                                    metadata = self.engine.load_workflow(wf['filepath'])
                                    st.session_state['workflow_results'] = None
                                    st.success(f"✓ 已加载: {wf['name']}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"✗ 加载失败: {e}")

                            if st.button("🗑️ 删除", key=f"delete_{i}", width="stretch"):
                                if WorkflowEngine.delete_workflow(wf['filepath']):
                                    del st.session_state['saved_workflows_list']
                                    st.success(f"✓ 已删除: {wf['name']}")
                                    st.rerun()
                                else:
                                    st.error(f"✗ 删除失败")
            else:
                st.info("📭 暂无保存的工作流，请先保存一个工作流")

    def render_canvas(self):
        """渲染画布"""
        st.markdown("### 🎨 工作流画布")

        # 显示节点
        if self.engine.nodes:
            # 按分类显示节点
            categories = {}
            for node_id, node in self.engine.nodes.items():
                node_config = self.node_types[node.node_type]
                category = node_config['category']
                if category not in categories:
                    categories[category] = []
                categories[category].append((node_id, node))

            for category, nodes in categories.items():
                # 分类标题
                st.markdown(f"""
                <div class="category-header">
                    <span>{category}</span>
                    <span style="margin-left: auto; font-size: 0.9rem;">{len(nodes)} 个节点</span>
                </div>
                """, unsafe_allow_html=True)

                # 节点卡片
                cols = st.columns(min(3, len(nodes)))
                for i, (node_id, node) in enumerate(nodes):
                    with cols[i % len(cols)]:
                        node_config = self.node_types[node.node_type]
                        color = node_config['color']

                        st.markdown(f"""
                        <div class="node-card" style="--card-color: {color}; border-left-color: {color};">
                            <div class="node-icon">{node_config['icon']}</div>
                            <div class="node-title">{node_config['name']}</div>
                            <div style="font-size: 0.85rem; color: #7f8c8d; margin-bottom: 1rem;">
                                ID: <code>{node.id[:8]}...</code>
                            </div>
                        """, unsafe_allow_html=True)

                        # 参数详情
                        if node.params:
                            # 特殊处理：因子计算节点显示详细信息
                            if node.node_type == 'factor_calculator' and 'factor_name' in node.params:
                                with st.expander("📋 因子详情", expanded=False):
                                    from src.factor_engine.factor_metadata import get_factor_info
                                    factor_info = get_factor_info(node.params['factor_name'])

                                    # 标题
                                    st.markdown(f"**{factor_info.get('icon', '📊')} {factor_info['name']}**")
                                    st.caption(f"{factor_info['category']}")

                                    # 公式
                                    st.code(factor_info['formula'], language=None)

                                    # 说明
                                    st.text(factor_info['description'])
                            else:
                                with st.expander("📋 参数详情", expanded=False):
                                    for key, value in node.params.items():
                                        st.markdown(f"""
                                        <div class="param-label">{key}</div>
                                        <div class="param-value">{value}</div>
                                        """, unsafe_allow_html=True)

                        st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-icon">📦</div>
                <div class="empty-text">
                    <strong>暂无节点</strong><br>
                    请从左侧边栏添加节点开始构建工作流
                </div>
            </div>
            """, unsafe_allow_html=True)

    def render_results(self):
        """渲染结果"""
        st.markdown("### 📊 执行结果")

        results = st.session_state.get('workflow_results')

        if results:
            for node_id, result in results.items():
                node = self.engine.nodes[node_id]
                node_config = self.node_types[node.node_type]
                color = node_config['color']

                # 结果卡片
                st.markdown(f"""
                <div class="result-card">
                    <div class="result-header">
                        <div class="result-icon">{node_config['icon']}</div>
                        <div>
                            <div class="result-title">{node_config['name']}</div>
                            <div style="font-size: 0.85rem; color: #7f8c8d;">
                                节点ID: <code>{node_id[:8]}...</code>
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if result is None:
                    st.warning("⚠️ 节点执行失败或返回空结果")
                elif isinstance(result, dict):
                    # 检查是否是backtester节点
                    node = self.engine.nodes.get(node_id)
                    if node and node.node_type == 'backtester':
                        st.markdown("#### 📊 回测结果摘要")

                        # 显示关键指标
                        if 'long_short_results' in result:
                            ls_results = result['long_short_results']
                            if isinstance(ls_results, dict):
                                metrics_to_show = ['total_return', 'annual_return', 'sharpe_ratio', 'max_drawdown', 'win_rate']
                                cols = st.columns(3)
                                for i, metric in enumerate(metrics_to_show):
                                    if metric in ls_results:
                                        with cols[i % 3]:
                                            metric_name = {
                                                'total_return': '总收益率',
                                                'annual_return': '年化收益率',
                                                'sharpe_ratio': '夏普比率',
                                                'max_drawdown': '最大回撤',
                                                'win_rate': '胜率'
                                            }.get(metric, metric)
                                            value = ls_results[metric]
                                            if isinstance(value, float):
                                                if 'rate' in metric or 'return' in metric or 'drawdown' in metric:
                                                    st.metric(metric_name, f"{value:.2%}")
                                                else:
                                                    st.metric(metric_name, f"{value:.4f}")

                                # ✨ 显示退市损失统计
                                if 'delisted_stocks_count' in ls_results and ls_results['delisted_stocks_count'] > 0:
                                    st.markdown("---")
                                    st.markdown("##### ⚠️ 退市股票统计")
                                    delisted_cols = st.columns(3)
                                    with delisted_cols[0]:
                                        st.metric("退市股票数量", f"{ls_results['delisted_stocks_count']} 只")
                                    with delisted_cols[1]:
                                        loss = ls_results.get('delisted_total_loss', 0)
                                        st.metric("退市总损失", f"{loss:,.2f} 元")
                                    with delisted_cols[2]:
                                        initial_cash = ls_results.get('initial_cash', 1000000)
                                        loss_pct = (loss / initial_cash * 100) if initial_cash > 0 else 0
                                        st.metric("损失占比", f"{loss_pct:.2f}%")

                                    # 显示退市股票详情
                                    if 'delisted_stocks' in ls_results and ls_results['delisted_stocks']:
                                        with st.expander("📋 查看退市股票详情"):
                                            delisted_df = pd.DataFrame([
                                                {
                                                    '股票代码': symbol,
                                                    '买入均价': f"{info['buy_avg_price']:.2f}",
                                                    '卖出日期': info['sell_date'],
                                                    '卖出价格': f"{info['sell_price']:.2f}",
                                                    '亏损金额': f"{info['loss']:,.2f}",
                                                    '亏损比例': f"{info['loss_pct']:.1f}%"
                                                }
                                                for symbol, info in ls_results['delisted_stocks'].items()
                                            ])
                                            st.dataframe(delisted_df, width="stretch", use_container_width=True)

                                            st.warning("""
                                            💡 **提示**：
                                            - 退市股票已使用最后交易日价格强制卖出
                                            - 损失已计入回测收益
                                            - 建议在选股时过滤退市股票或设置止损策略
                                            """)

                                # 显示交易明细预览
                                if 'trade_details' in ls_results:
                                    trade_details = ls_results['trade_details']
                                    if not trade_details.empty:
                                        st.markdown("##### 📋 交易明细预览")
                                        st.markdown(f"共 **{len(trade_details)}** 条交易记录")

                                        # 格式化显示
                                        display_df = trade_details.copy()
                                        if 'date' in display_df.columns:
                                            display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
                                        if 'price' in display_df.columns:
                                            display_df['price'] = display_df['price'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else '-')
                                        if 'weight' in display_df.columns:
                                            display_df['weight'] = display_df['weight'].apply(lambda x: f"{x:.2%}")

                                        st.dataframe(display_df.head(10), width="stretch", use_container_width=True)
                                    else:
                                        st.info("📭 暂无交易明细（可能没有发生调仓）")

                        # 显示完整的JSON（可选）
                        with st.expander("查看完整数据（JSON格式）"):
                            st.json(json.dumps(result, default=str, ensure_ascii=False, indent=2))
                    else:
                        # 普通字典，直接显示JSON
                        st.json(json.dumps(result, default=str, ensure_ascii=False, indent=2))
                elif isinstance(result, pd.DataFrame):
                    st.markdown("#### 数据预览")
                    st.dataframe(result.head(10), width="stretch")
                    st.markdown(f"""
                    <div style="display: flex; gap: 1rem; margin-top: 1rem;">
                        <span style="background: #e3f2fd; padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.9rem;">
                            📐 形状: {result.shape}
                        </span>
                        <span style="background: #e8f5e9; padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.9rem;">
                            🔢 类型: DataFrame
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
                elif isinstance(result, pd.Series):
                    self._render_series_result(result)
                else:
                    st.write(f"**结果类型:** {type(result).__name__}")
                    st.write(result)

                st.markdown("---")

            # 下载报告按钮
            self._render_download_button(results)

        else:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-icon">📊</div>
                <div class="empty-text">
                    <strong>暂无执行结果</strong><br>
                    请先执行工作流查看结果
                </div>
            </div>
            """, unsafe_allow_html=True)

    def _render_download_button(self, results: Dict[str, Any]):
        """渲染下载报告按钮"""
        st.markdown("---")
        st.markdown("### 📥 下载详细报告")

        # 打印调试信息
        print(f"[DEBUG] _render_download_button - 所有结果键: {list(results.keys())}")
        for node_id, result in results.items():
            node = self.engine.nodes.get(node_id)
            node_type = node.node_type if node else "unknown"
            print(f"[DEBUG] 节点 {node_id[:8]} ({node_type}):")
            if isinstance(result, dict):
                print(f"  字典键: {list(result.keys())}")
                for key, value in result.items():
                    if isinstance(value, (int, float)):
                        print(f"    {key}: {value}")
            elif isinstance(result, (pd.DataFrame, pd.Series)):
                print(f"  数据类型: {type(result).__name__}, shape: {result.shape}")

        # 检查是否有回测结果 - 更灵活的检测
        has_backtest = False
        backtest_result = None

        for node_id, result in results.items():
            if result is None:
                continue
            # 检查是否是回测节点结果（包含关键指标）
            if isinstance(result, dict):
                # 检查多种可能的键名
                if any(key in result for key in ['ls_total_return', 'total_return', 'annual_return', 'sharpe_ratio', 'max_drawdown']):
                    has_backtest = True
                    backtest_result = result
                    print(f"[DEBUG] 找到回测结果在节点 {node_id[:8]}")
                    break
                # 或者检查节点类型
                node = self.engine.nodes.get(node_id)
                if node and node.node_type == 'backtester':
                    has_backtest = True
                    backtest_result = result
                    print(f"[DEBUG] 找到backtester节点 {node_id[:8]}")

                    # 详细检查回测结果结构
                    print(f"[DEBUG] 回测结果键: {list(result.keys())}")
                    if 'long_short_results' in result:
                        ls_results = result['long_short_results']
                        print(f"[DEBUG] long_short_results 类型: {type(ls_results)}")
                        if isinstance(ls_results, dict):
                            print(f"[DEBUG] long_short_results 键: {list(ls_results.keys())}")
                            if 'trade_details' in ls_results:
                                trade_details = ls_results['trade_details']
                                print(f"[DEBUG] trade_details 类型: {type(trade_details)}")
                                if hasattr(trade_details, 'shape'):
                                    print(f"[DEBUG] trade_details 形状: {trade_details.shape}")
                                if hasattr(trade_details, '__len__'):
                                    print(f"[DEBUG] trade_details 长度: {len(trade_details)}")
                                    if not trade_details.empty:
                                        print(f"[DEBUG] trade_details 前5条:")
                                        print(trade_details.head())
                                    else:
                                        print("[WARNING] trade_details 为空")
                            else:
                                print("[WARNING] long_short_results 中没有 trade_details 键")
                    break

        if not has_backtest or backtest_result is None:
            st.info("💡 执行回测节点后即可生成详细报告")
            return

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📄 生成HTML报告", width="stretch"):
                with st.spinner("正在生成报告..."):
                    from src.workflow.report_generator import ReportGenerator

                    try:
                        # 先显示调试信息
                        st.markdown("### 🔍 调试信息")

                        # 显示所有节点结果
                        st.markdown("**所有节点结果：**")
                        for node_id, result in results.items():
                            node = self.engine.nodes.get(node_id)
                            node_type = node.node_type if node else "unknown"
                            st.markdown(f"- **节点 {node_id[:8]}** ({node_type})")

                            if isinstance(result, dict):
                                st.markdown(f"  键: {list(result.keys())}")
                                # 显示数值类型的值
                                numeric_values = {k: v for k, v in result.items() if isinstance(v, (int, float))}
                                if numeric_values:
                                    st.code(numeric_values)
                            elif isinstance(result, (pd.DataFrame, pd.Series)):
                                st.markdown(f"  类型: {type(result).__name__}, 形状: {result.shape}")

                            st.markdown("---")

                        # 生成HTML报告（包含工作流节点信息和执行结果）
                        generator = ReportGenerator(workflow_engine=self.engine)
                        html_content = generator.generate_html_report(
                            results=backtest_result,
                            workflow_nodes=self.engine.nodes,
                            node_results=st.session_state.get('workflow_results', {})
                        )

                        # 保存到临时文件
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                            f.write(html_content)
                            temp_path = f.name

                        st.success("✅ 报告生成成功！")

                        # 提供下载
                        with open(temp_path, 'r', encoding='utf-8') as f:
                            st.download_button(
                                label="⬇️ 下载报告",
                                data=f.read(),
                                file_name=f"回测报告_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.html",
                                mime="text/html",
                                width="stretch"
                            )
                    except Exception as e:
                        st.error(f"❌ 报告生成失败: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())

        with col2:
            if st.button("📊 导出交易明细", width="stretch"):
                with st.spinner("正在导出交易明细..."):
                    try:
                        from src.utils.export_utils import BacktestExporter
                        import tempfile
                        import os

                        # 检查是否有交易明细
                        trade_details = None
                        if 'long_short_results' in backtest_result:
                            ls_results = backtest_result['long_short_results']
                            if isinstance(ls_results, dict) and 'trade_details' in ls_results:
                                trade_details = ls_results['trade_details']

                        if trade_details is None or (isinstance(trade_details, pd.DataFrame) and trade_details.empty):
                            st.warning("⚠️ 没有找到交易明细数据")
                            st.info("💡 交易明细在分组回测中生成，请确保回测已完成")
                        else:
                            # 创建临时文件
                            timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
                            temp_dir = tempfile.gettempdir()
                            output_path = os.path.join(temp_dir, f"交易明细_{timestamp}.xlsx")

                            # 导出到Excel
                            exported_path = BacktestExporter.export_to_excel(
                                backtest_results=ls_results,
                                factor_name="因子回测",
                                output_path=output_path
                            )

                            st.success(f"✅ 成功导出 {len(trade_details)} 条交易记录")

                            # 提供下载
                            with open(exported_path, 'rb') as f:
                                st.download_button(
                                    label="⬇️ 下载Excel文件",
                                    data=f.read(),
                                    file_name=f"交易明细_{timestamp}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    width="stretch"
                                )
                    except Exception as e:
                        st.error(f"❌ 导出失败: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())

        with col3:
            st.markdown("""
            <div style="text-align: center; padding: 1rem; background: #fffbeb; border-radius: 8px; font-size: 0.85rem; color: #92400e;">
                💡 报告特点：<br>
                • 通俗易懂<br>
                • 专业分析<br>
                • 实用建议
            </div>
            """, unsafe_allow_html=True)

    def _render_series_result(self, result: pd.Series):
        """渲染Series结果"""
        try:
            if isinstance(result.index, pd.MultiIndex):
                if 'date' in result.index.names and 'symbol' in result.index.names:
                    dates = result.index.get_level_values('date')
                    symbols = result.index.get_level_values('symbol')

                    col1, col2 = st.columns(2)

                    with col1:
                        st.metric("日期范围", f"{dates.min()} ~ {dates.max()}")

                    with col2:
                        unique_symbols = symbols.unique()
                        if len(unique_symbols) <= 10:
                            st.metric("股票数量", f"{len(unique_symbols)} 只")
                        else:
                            st.metric("股票数量", f"{len(unique_symbols)} 只")

                    st.markdown("#### 数据统计")

                    # 特殊处理：如果是信号数据（值为-1, 0, 1），显示信号分布
                    if result.dtype in ['int64', 'int32'] and set(result.unique()).issubset({-1, 0, 1}):
                        signal_counts = result.value_counts()
                        total = len(result)

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("做多(1)", f"{signal_counts.get(1, 0):,}",
                                    f"{signal_counts.get(1, 0)/total*100:.1f}%")
                        with col2:
                            st.metric("做空(-1)", f"{signal_counts.get(-1, 0):,}",
                                    f"{signal_counts.get(-1, 0)/total*100:.1f}%")
                        with col3:
                            st.metric("观望(0)", f"{signal_counts.get(0, 0):,}",
                                    f"{signal_counts.get(0, 0)/total*100:.1f}%")

                        st.info("💡 信号说明：1=做多, -1=做空, 0=观望。大部分股票标记为观望是正常的，只交易最具代表性的股票。")

                        # 显示一些示例信号
                        st.markdown("#### 信号示例")
                        # 选取包含所有类型信号的样本
                        sample_long = result[result == 1].head(2)
                        sample_short = result[result == -1].head(2)
                        sample_neutral = result[result == 0].head(2)

                        sample_data = pd.concat([sample_long, sample_short, sample_neutral])

                        formatted_sample = []
                        for idx, value in sample_data.items():
                            date_val, symbol_val = idx
                            signal_label = "做多" if value == 1 else "做空" if value == -1 else "观望"
                            formatted_sample.append({
                                'date': str(date_val),
                                'symbol': str(symbol_val),
                                'signal': signal_label,
                                'value': int(value)
                            })

                        st.dataframe(pd.DataFrame(formatted_sample), width="stretch")
                    else:
                        # 非信号数据，显示数据范围和前10条
                        st.info(f"📊 数据范围: [{result.min():.6f}, {result.max():.6f}], 均值: {result.mean():.6f}")

                        # 调试信息
                        print(f"[DEBUG] _render_series_result - result类型: {type(result)}, dtype: {result.dtype}")
                        print(f"[DEBUG] _render_series_result - result前5个值: {result.head().tolist()}")

                        # 改进：显示前10条，但确保包含非零值（如果有的话）
                        series_to_show = result.head(10)

                        # 检查前10条是否全是0或接近0
                        if (series_to_show.abs() < 0.0001).all() and result.abs().max() > 0.01:
                            # 如果前10条都接近0，但数据中有明显非零值，则重新采样
                            print(f"[DEBUG] 前10条数据都接近0，重新采样显示更有代表性的数据")
                            # 选取：最大值、最小值、中间值附近的数据
                            max_idx = result.idxmax()
                            min_idx = result.idxmin()
                            median_val = result.median()
                            median_idx = (result - median_val).abs().idxmin()

                            # 组合样本：前3条 + 最大值 + 最小值 + 中位数附近 + 最后3条
                            sample_indices = list(result.head(3).index) + [max_idx, min_idx, median_idx] + list(result.tail(3).index)
                            # 去重
                            sample_indices = list(dict.fromkeys(sample_indices))  # 保持顺序并去重
                            series_to_show = result.loc[sample_indices]

                            st.info(f"💡 原前10条数据都接近0，已自动切换为代表性数据显示")

                        formatted_data = []
                        for idx, value in series_to_show.items():
                            date_val, symbol_val = idx
                            formatted_data.append({
                                'date': str(date_val),
                                'symbol': str(symbol_val),
                                'value': f'{value:.6f}'  # 显示6位小数
                            })

                        print(f"[DEBUG] _render_series_result - formatted_data前3个: {formatted_data[:3]}")

                        display_df = pd.DataFrame(formatted_data)
                        st.dataframe(display_df, width="stretch")

                    if len(result) <= 100:
                        with st.expander("📈 数据摘要", expanded=False):
                            st.dataframe(result.describe().to_frame().T, width="stretch")
                else:
                    st.write(f"**MultiIndex Series** - 索引层级: {result.index.names}")
                    series_to_show = result.head(10)
                    formatted_data = []
                    for idx, value in series_to_show.items():
                        formatted_data.append({
                            'index': str(idx),
                            'value': value
                        })

                    display_df = pd.DataFrame(formatted_data)
                    st.dataframe(display_df, width="stretch")
            else:
                series_df = result.to_frame(name='value')
                st.markdown("#### 数据趋势")
                st.line_chart(series_df.head(50))

            st.markdown(f"""
            <div style="display: flex; gap: 1rem; margin-top: 1rem;">
                <span style="background: #e3f2fd; padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.9rem;">
                    📐 形状: {result.shape}
                </span>
                <span style="background: #e8f5e9; padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.9rem;">
                    🔢 类型: Series
                </span>
            </div>
            """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"显示Series时出错: {e}")
            if isinstance(result.index, pd.MultiIndex):
                series_to_show = result.head(10)
                formatted_data = []
                for idx, value in series_to_show.items():
                    if isinstance(idx, tuple) and len(idx) >= 2:
                        formatted_data.append({
                            'date': str(idx[0]),
                            'symbol': str(idx[1]),
                            'value': value
                        })
                    else:
                        formatted_data.append({
                            'index': str(idx),
                            'value': value
                        })

                display_df = pd.DataFrame(formatted_data)
                st.dataframe(display_df, width="stretch")

    def run(self):
        """运行UI"""
        # 页面配置
        st.set_page_config(
            page_title="101因子分析平台 - 专业版",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded"
        )

        # 应用自定义CSS
        self.apply_custom_css()

        # 初始化session state
        if 'workflow_results' not in st.session_state:
            st.session_state['workflow_results'] = None

        # 渲染顶部标题
        self.render_header()

        st.markdown("---")

        # 主界面布局
        col1, col2 = st.columns([1, 3])

        with col1:
            self.render_sidebar()

        with col2:
            self.render_canvas()
            st.markdown("---")
            self.render_results()


# 测试函数
def test_enhanced_ui():
    """测试增强UI"""
    print("增强UI模块测试...")

    ui = WorkflowUIEnhanced()
    print(f"已创建增强UI，支持 {len(ui.node_types)} 种节点类型")

    for node_type, config in ui.node_types.items():
        print(f"- {config['icon']} {config['name']} ({node_type}): {config['category']}")

    print("增强UI模块测试完成!")


if __name__ == '__main__':
    ui = WorkflowUIEnhanced()
    ui.run()
