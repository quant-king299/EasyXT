# -*- coding: utf-8 -*-
"""
可视化策略配置编辑器

提供交互式界面创建和编辑策略配置。
"""

import streamlit as st
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import dataclasses


# 预定义因子库
FACTOR_LIBRARY = {
    "基本面因子": {
        "市盈率": {
            "field": "pe_ratio",
            "factor_type": "fundamental",
            "default_direction": -1,  # 负相关（低PE好）
            "description": "市盈率，衡量股票估值水平"
        },
        "市净率": {
            "field": "pb_ratio",
            "factor_type": "fundamental",
            "default_direction": -1,
            "description": "市净率，衡量股价相对于账面价值"
        },
        "市值": {
            "field": "market_cap",
            "factor_type": "fundamental",
            "default_direction": -1,
            "description": "总市值"
        },
        "ROE": {
            "field": "roe",
            "factor_type": "fundamental",
            "default_direction": 1,
            "description": "净资产收益率"
        },
        "ROA": {
            "field": "roa",
            "factor_type": "fundamental",
            "default_direction": 1,
            "description": "总资产收益率"
        },
        "营收增长率": {
            "field": "revenue_growth",
            "factor_type": "fundamental",
            "default_direction": 1,
            "description": "营业收入增长率"
        },
        "净利润增长率": {
            "field": "profit_growth",
            "factor_type": "fundamental",
            "default_direction": 1,
            "description": "净利润增长率"
        },
        "毛利率": {
            "field": "gross_margin",
            "factor_type": "fundamental",
            "default_direction": 1,
            "description": "销售毛利率"
        },
        "资产负债率": {
            "field": "debt_ratio",
            "factor_type": "fundamental",
            "default_direction": -1,
            "description": "资产负债率"
        }
    },
    "技术因子": {
        "动量": {
            "field": "momentum_20",
            "factor_type": "technical",
            "default_direction": 1,
            "description": "20日收益率动量"
        },
        "反转": {
            "field": "reversal_5",
            "factor_type": "technical",
            "default_direction": -1,
            "description": "5日反转"
        },
        "波动率": {
            "field": "volatility_20",
            "factor_type": "technical",
            "default_direction": -1,
            "description": "20日波动率"
        },
        "换手率": {
            "field": "turnover_20",
            "factor_type": "technical",
            "default_direction": -1,
            "description": "20日平均换手率"
        },
        "RSI": {
            "field": "rsi",
            "factor_type": "technical",
            "default_direction": -1,
            "description": "相对强弱指标"
        },
        "MACD": {
            "field": "macd",
            "factor_type": "technical",
            "default_direction": 1,
            "description": "MACD指标"
        }
    },
    "Alpha101因子": {
        "Alpha001": {
            "field": "alpha001",
            "factor_type": "alpha101",
            "default_direction": 1,
            "description": "相关性因子"
        },
        "Alpha002": {
            "field": "alpha002",
            "factor_type": "alpha101",
            "default_direction": -1,
            "description": "价格-成交量趋势"
        },
        "Alpha003": {
            "field": "alpha003",
            "factor_type": "alpha101",
            "default_direction": 1,
            "description": "成交量变化率"
        },
        "Alpha004": {
            "field": "alpha004",
            "factor_type": "alpha101",
            "default_direction": -1,
            "description": "价格波动"
        },
        "Alpha005": {
            "field": "alpha005",
            "factor_type": "alpha101",
            "default_direction": -1,
            "description": "开盘价位置"
        }
    }
}

# 排除条件库
FILTER_LIBRARY = {
    "股票状态": {
        "ST股票": {
            "type": "stock_status",
            "condition": "not_in",
            "values": ["ST", "*ST", "S*ST"],
            "description": "排除ST、*ST股票"
        },
        "停牌股票": {
            "type": "stock_status",
            "condition": "not_in",
            "values": ["停牌"],
            "description": "排除停牌股票"
        },
        "涨跌停": {
            "type": "stock_status",
            "condition": "not_in",
            "values": ["涨停", "跌停"],
            "description": "排除涨跌停股票"
        }
    },
    "市场类型": {
        "只保留主板": {
            "type": "market",
            "condition": "in",
            "values": ["主板"],
            "description": "只包含主板股票"
        },
        "排除创业板": {
            "type": "market",
            "condition": "not_in",
            "values": ["创业板"],
            "description": "排除创业板"
        },
        "排除科创板": {
            "type": "market",
            "condition": "not_in",
            "values": ["科创板"],
            "description": "排除科创板"
        }
    },
    "基本面筛选": {
        "市值范围": {
            "type": "fundamental",
            "condition": "between",
            "field": "market_cap",
            "description": "按市值筛选（单位：亿）"
        },
        "市盈率范围": {
            "type": "fundamental",
            "condition": "between",
            "field": "pe_ratio",
            "description": "按市盈率筛选"
        },
        "市净率范围": {
            "type": "fundamental",
            "condition": "between",
            "field": "pb_ratio",
            "description": "按市净率筛选"
        },
        "ROE筛选": {
            "type": "fundamental",
            "condition": "greater_than",
            "field": "roe",
            "description": "ROE大于指定值"
        }
    }
}


def init_editor_session_state():
    """初始化编辑器会话状态"""
    if 'selected_factors' not in st.session_state:
        st.session_state.selected_factors = []
    if 'selected_filters' not in st.session_state:
        st.session_state.selected_filters = []
    if 'strategy_name' not in st.session_state:
        st.session_state.strategy_name = "我的策略"
    if 'strategy_description' not in st.session_state:
        st.session_state.strategy_description = ""
    if 'universe_type' not in st.session_state:
        st.session_state.universe_type = "沪深300"
    if 'universe_index_code' not in st.session_state:
        st.session_state.universe_index_code = "000300.SH"


def render_factor_selector():
    """渲染因子选择器"""
    st.subheader("📊 选择打分因子")

    # 因子类别选择
    factor_categories = list(FACTOR_LIBRARY.keys())

    selected_category = st.selectbox(
        "选择因子类别",
        factor_categories,
        key="factor_category_select"
    )

    # 显示该类别下的所有因子
    factors_in_category = FACTOR_LIBRARY[selected_category]

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"**{selected_category}因子列表**")

        for factor_name, factor_info in factors_in_category.items():
            with st.container():
                col_a, col_b = st.columns([3, 1])

                with col_a:
                    st.markdown(f"**{factor_name}**")
                    st.caption(factor_info['description'])
                    st.markdown(f"*字段: `{factor_info['field']}`*")

                with col_b:
                    # 检查是否已选择
                    is_selected = any(
                        f['name'] == factor_name
                        for f in st.session_state.selected_factors
                    )

                    if st.button(
                        "添加" if not is_selected else "已添加",
                        key=f"add_{factor_name}",
                        disabled=is_selected,
                        use_container_width=True
                    ):
                        add_factor(factor_name, factor_info)

    with col2:
        st.markdown("**已选择的因子**")

        if not st.session_state.selected_factors:
            st.info("暂未选择任何因子")
        else:
            for i, factor in enumerate(st.session_state.selected_factors):
                with st.expander(f"{i+1}. {factor['name']}", expanded=True):
                    # 因子配置
                    new_name = st.text_input(
                        "因子名称",
                        value=factor['name'],
                        key=f"factor_name_{i}"
                    )

                    # 方向选择
                    direction = st.selectbox(
                        "因子方向",
                        options=[("正相关", 1), ("负相关", -1)],
                        index=0 if factor['direction'] == 1 else 1,
                        key=f"factor_direction_{i}"
                    )
                    direction = direction[1]

                    # 权重
                    weight = st.slider(
                        "权重",
                        min_value=0.0,
                        max_value=1.0,
                        value=factor['weight'],
                        step=0.05,
                        key=f"factor_weight_{i}"
                    )

                    # 标准化
                    normalize = st.selectbox(
                        "标准化方法",
                        options=["zscore", "minmax", "rank", "winsorize", "none"],
                        index=["zscore", "minmax", "rank", "winsorize", "none"].index(factor['normalize'])
                        if factor.get('normalize') in ["zscore", "minmax", "rank", "winsorize", "none"]
                        else 0,
                        key=f"factor_normalize_{i}"
                    )

                    # 中性化
                    neutralize = st.checkbox(
                        "行业中性化",
                        value=factor.get('neutralize', {}).get('enabled', False),
                        key=f"factor_neutralize_{i}"
                    )

                    # 更新因子配置
                    factor.update({
                        'name': new_name,
                        'direction': direction,
                        'weight': weight,
                        'normalize': normalize,
                        'neutralize': {'enabled': neutralize, 'by': 'industry'} if neutralize else {'enabled': False}
                    })

                    # 删除按钮
                    if st.button("🗑️ 删除", key=f"remove_{i}", use_container_width=True):
                        st.session_state.selected_factors.pop(i)
                        st.rerun()

            # 权重总和检查
            total_weight = sum(f['weight'] for f in st.session_state.selected_factors)
            st.metric("权重总和", f"{total_weight:.2%}")

            if abs(total_weight - 1.0) > 0.01:
                st.warning(f"⚠️ 权重总和应为100%，当前为{total_weight:.2%}")
                if st.button("自动归一化权重"):
                    normalize_weights()


def render_filter_selector():
    """渲染排除条件选择器"""
    st.subheader("🔍 选择排除条件")

    filter_categories = list(FILTER_LIBRARY.keys())

    selected_category = st.selectbox(
        "选择条件类别",
        filter_categories,
        key="filter_category_select"
    )

    filters_in_category = FILTER_LIBRARY[selected_category]

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"**{selected_category}条件列表**")

        for filter_name, filter_info in filters_in_category.items():
            with st.container():
                col_a, col_b = st.columns([3, 1])

                with col_a:
                    st.markdown(f"**{filter_name}**")
                    st.caption(filter_info['description'])
                    st.markdown(f"*类型: `{filter_info['type']}`*")

                with col_b:
                    is_selected = any(
                        f['name'] == filter_name
                        for f in st.session_state.selected_filters
                    )

                    if st.button(
                        "添加" if not is_selected else "已添加",
                        key=f"add_filter_{filter_name}",
                        disabled=is_selected,
                        use_container_width=True
                    ):
                        add_filter(filter_name, filter_info)

    with col2:
        st.markdown("**已选择的条件**")

        if not st.session_state.selected_filters:
            st.info("暂未选择任何条件")
        else:
            for i, filter_conf in enumerate(st.session_state.selected_filters):
                with st.expander(f"{i+1}. {filter_conf['name']}"):
                    st.json(filter_conf)

                    if st.button("🗑️ 删除", key=f"remove_filter_{i}", use_container_width=True):
                        st.session_state.selected_filters.pop(i)
                        st.rerun()


def render_basic_config():
    """渲染基本配置"""
    st.subheader("📝 基本配置")

    col1, col2 = st.columns(2)

    with col1:
        st.session_state.strategy_name = st.text_input(
            "策略名称",
            value=st.session_state.strategy_name
        )

        st.session_state.strategy_description = st.text_area(
            "策略描述",
            value=st.session_state.strategy_description,
            height=100
        )

    with col2:
        # 回测配置
        st.markdown("**回测参数**")

        start_date = st.text_input(
            "开始日期",
            value="20200101",
            help="格式: YYYYMMDD"
        )

        end_date = st.text_input(
            "结束日期",
            value="20231231",
            help="格式: YYYYMMDD"
        )

        initial_cash = st.number_input(
            "初始资金",
            min_value=100000,
            max_value=100000000,
            value=1000000,
            step=100000
        )

        commission = st.number_input(
            "佣金率",
            min_value=0.0,
            max_value=0.01,
            value=0.001,
            format="%.4f"
        )

    # 股票池配置
    st.markdown("**股票池配置**")

    col1, col2 = st.columns(2)

    with col1:
        universe_options = {
            "沪深300": "000300.SH",
            "中证500": "000905.SH",
            "中证1000": "000852.SH",
            "上证50": "000016.SH",
            "创业板指": "399006.SZ",
            "科创50": "000688.SH",
            "全A股": "all"
        }

        selected_universe = st.selectbox(
            "股票池",
            options=list(universe_options.keys()),
            index=0,
            help="选择股票池指数"
        )

        st.session_state.universe_type = selected_universe
        st.session_state.universe_index_code = universe_options[selected_universe]

    with col2:
        st.info(f"""
        **当前股票池**: {selected_universe}

        **指数代码**: {universe_options[selected_universe]}

        **说明**:
        - 沪深300: 300只大盘股
        - 中证500: 500只中盘股
        - 中证1000: 1000只小盘股
        - 全A股: 所有A股（数据量大）
        """)

    return {
        'start_date': start_date,
        'end_date': end_date,
        'initial_cash': initial_cash,
        'commission': commission
    }


def render_portfolio_config():
    """渲染组合配置"""
    st.subheader("💼 组合构建配置")

    col1, col2 = st.columns(2)

    with col1:
        select_method = st.selectbox(
            "选股方式",
            options=["top_n", "quantile", "threshold"],
            help="top_n: 选择得分最高的N只\nquantile: 按分位数选择\nthreshold: 按阈值筛选"
        )

        if select_method == "top_n":
            top_n = st.number_input("选择数量", min_value=1, max_value=500, value=30)
        else:
            top_n = None

    with col2:
        weight_method = st.selectbox(
            "权重分配方式",
            options=["equal", "market_cap", "factor_score"],
            help="equal: 等权重\nmarket_cap: 按市值加权\nfactor_score: 按因子得分加权"
        )

    return {
        'select_method': select_method,
        'top_n': top_n if select_method == "top_n" else None,
        'weight_method': weight_method
    }


def render_rebalance_config():
    """渲染调仓配置"""
    st.subheader("⚙️ 调仓配置")

    col1, col2 = st.columns(2)

    with col1:
        frequency = st.selectbox(
            "调仓频率",
            options=["daily", "weekly", "monthly", "quarterly"],
            help="daily: 每日\nweekly: 每周\nmonthly: 每月\nquarterly: 每季度"
        )

    with col2:
        if frequency == "monthly":
            rebalance_day = st.number_input("调仓日", min_value=1, max_value=28, value=1)
        else:
            rebalance_day = None

    return {
        'frequency': frequency,
        'rebalance_day': rebalance_day
    }


def add_factor(factor_name: str, factor_info: Dict):
    """添加因子到已选列表"""
    # 检查是否已存在
    if any(f['name'] == factor_name for f in st.session_state.selected_factors):
        return

    # 添加新因子
    st.session_state.selected_factors.append({
        'name': factor_name,
        'factor_type': factor_info['factor_type'],
        'field': factor_info['field'],
        'direction': factor_info['default_direction'],
        'weight': 0.1,  # 默认权重
        'normalize': 'zscore',
        'neutralize': {'enabled': False}
    })

    st.rerun()


def add_filter(filter_name: str, filter_info: Dict):
    """添加排除条件"""
    # 检查是否已存在
    if any(f['name'] == filter_name for f in st.session_state.selected_filters):
        return

    # 添加新条件
    filter_config = {
        'name': filter_name,
        'type': filter_info['type'],
        'condition': filter_info['condition']
    }

    if 'values' in filter_info:
        filter_config['values'] = filter_info['values']

    if 'field' in filter_info:
        filter_config['field'] = filter_info['field']
        filter_config['min_value'] = None
        filter_config['max_value'] = None

    st.session_state.selected_filters.append(filter_config)
    st.rerun()


def normalize_weights():
    """归一化权重"""
    if not st.session_state.selected_factors:
        return

    total = sum(f['weight'] for f in st.session_state.selected_factors)
    if total > 0:
        for factor in st.session_state.selected_factors:
            factor['weight'] = factor['weight'] / total

    st.rerun()


def generate_yaml_config(backtest_config: Dict, portfolio_config: Dict, rebalance_config: Dict) -> str:
    """生成YAML配置"""
    config = {
        'strategy': {
            'name': st.session_state.strategy_name,
            'version': '1.0.0',
            'author': '101因子平台',
            'description': st.session_state.strategy_description
        },
        'backtest': backtest_config,
        'universe': {
            'type': 'index' if st.session_state.universe_index_code != 'all' else 'all',
            'index_code': st.session_state.universe_index_code
        },
        'exclude_filters': [],
        'scoring_factors': [],
        'portfolio': portfolio_config,
        'rebalance': rebalance_config,
        'live_trading': {
            'account_id': 'your_account'
        }
    }

    # 添加排除条件
    for filter_conf in st.session_state.selected_filters:
        filter_dict = {
            'name': filter_conf['name'],
            'type': filter_conf['type'],
            'condition': filter_conf['condition']
        }

        if 'values' in filter_conf:
            filter_dict['values'] = filter_conf['values']

        if 'field' in filter_conf:
            filter_dict['field'] = filter_conf['field']

        if 'min_value' in filter_conf:
            filter_dict['min_value'] = filter_conf['min_value']

        if 'max_value' in filter_conf:
            filter_dict['max_value'] = filter_conf['max_value']

        config['exclude_filters'].append(filter_dict)

    # 添加打分因子
    for factor in st.session_state.selected_factors:
        factor_dict = {
            'name': factor['name'],
            'factor_type': factor['factor_type'],
            'field': factor['field'],
            'direction': factor['direction'],
            'weight': factor['weight'],
            'normalize': factor['normalize'],
            'neutralize': factor['neutralize']
        }

        config['scoring_factors'].append(factor_dict)

    return yaml.dump(config, allow_unicode=True, default_flow_style=False)


def render_config_editor():
    """渲染配置编辑器主界面"""
    st.title("📝 配置编辑器")

    # 初始化会话状态
    init_editor_session_state()

    st.markdown("---")

    # 顶部：当前配置 + 上传配置
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📋 当前配置")
        if st.session_state.get('config'):
            config = st.session_state.config
            st.info(f"""
            **策略名称**: {config.name}
            **版本**: {config.version}
            **描述**: {config.description}

            **因子数量**: {len(config.scoring_factors)}
            **回测期间**: {config.backtest_config.get('start_date', 'N/A')} - {config.backtest_config.get('end_date', 'N/A')}
            """)
        else:
            st.warning("⚠️ 未加载配置，请上传配置文件或使用配置管理页面")

    with col2:
        st.markdown("### 📤 上传配置")
        uploaded_file = st.file_uploader(
            "上传YAML配置文件",
            type=['yaml', 'yml'],
            help="选择策略配置文件（.yaml或.yml）",
            accept_multiple_files=False,
            key="config_uploader"
        )

        if uploaded_file is not None:
            try:
                import sys
                from pathlib import Path
                # 动态导入
                sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
                from easyxt_backtest.config import load_strategy_config

                # 读取并解析配置
                content = uploaded_file.read()
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    f.write(content.decode('utf-8'))
                    temp_path = f.name

                config = load_strategy_config(temp_path)
                st.session_state.config = config

                # 清理临时文件
                Path(temp_path).unlink()

                st.success(f"✅ 配置加载成功：**{config.name}**")
                st.info(f"**描述**: {config.description}")
                st.info(f"**因子**: {len(config.scoring_factors)} 个")
                st.info(f"**回测期间**: {config.backtest_config.get('start_date', 'N/A')} - {config.backtest_config.get('end_date', 'N/A')}")

                # 强制刷新页面
                st.rerun()

            except Exception as e:
                st.error(f"❌ 配置加载失败: {e}")
                import traceback
                st.code(traceback.format_exc(), language="python")

    st.markdown("---")

    # 创建标签页
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 基本信息", "📊 打分因子", "🔍 排除条件", "💼 组合配置", "💾 保存配置"
    ])

    with tab1:
        backtest_config = render_basic_config()

    with tab2:
        render_factor_selector()

    with tab3:
        render_filter_selector()

    with tab4:
        portfolio_config = render_portfolio_config()
        rebalance_config = render_rebalance_config()

    with tab5:
        st.subheader("💾 保存配置")

        # 配置摘要
        st.markdown("### 策略摘要")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("策略名称", st.session_state.strategy_name)
        with col2:
            st.metric("因子数量", len(st.session_state.selected_factors))
        with col3:
            st.metric("过滤条件", len(st.session_state.selected_filters))
        with col4:
            total_weight = sum(f['weight'] for f in st.session_state.selected_factors)
            st.metric("权重总和", f"{total_weight:.2%}")

        # 生成YAML
        if st.button("生成YAML配置", type="primary", use_container_width=True):
            if not st.session_state.selected_factors:
                st.error("❌ 请至少选择一个打分因子")
            else:
                yaml_content = generate_yaml_config(
                    backtest_config,
                    portfolio_config,
                    rebalance_config
                )

                st.session_state.generated_yaml = yaml_content

        # 显示和下载
        if 'generated_yaml' in st.session_state:
            st.success("✅ 配置生成成功！")

            st.markdown("### 生成的YAML配置")

            st.code(st.session_state.generated_yaml, language='yaml', height=400)

            # 下载按钮
            filename = f"{st.session_state.strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
            st.download_button(
                label="📥 下载YAML文件",
                data=st.session_state.generated_yaml,
                file_name=filename,
                mime='text/yaml',
                use_container_width=True
            )

            # 一键加载到回测
            if st.button("🚀 立即回测此策略", use_container_width=True):
                # 保存临时文件并加载
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
                    f.write(st.session_state.generated_yaml)
                    temp_path = f.name

                # 加载配置
                from easyxt_backtest.config import load_strategy_config
                config = load_strategy_config(temp_path)
                st.session_state.config = config

                st.success("✅ 策略已加载！切换到'策略回测'页面运行回测。")


if __name__ == "__main__":
    render_config_editor()
