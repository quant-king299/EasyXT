"""
回测报告生成器
用通俗易懂的语言解释回测结果
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional
import io
import base64

# 图表生成
try:
    import matplotlib
    matplotlib.use('Agg')  # 使用非交互式后端
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.font_manager import FontProperties

    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("警告: matplotlib未安装，无法生成图表")


class ReportGenerator:
    """回测报告生成器"""

    def __init__(self, workflow_engine=None):
        """
        初始化报告生成器

        Args:
            workflow_engine: 工作流引擎实例，用于获取节点信息
        """
        self.workflow_engine = workflow_engine

    def _get_factor_value_explanation(self, factor_name: str, min_value: float, max_value: float) -> str:
        """
        根据因子名称和实际值域生成因子值解释

        Args:
            factor_name: 因子名称
            min_value: 实际最小值
            max_value: 实际最大值

        Returns:
            str: 因子值解释HTML
        """
        # 根据因子名称获取元数据
        try:
            from src.factor_engine.factor_metadata import get_factor_info
            factor_info = get_factor_info(factor_name)
            formula = factor_info.get('formula', '')
            description = factor_info.get('description', '')
        except:
            formula = ''
            description = ''

        # 判断因子类型
        if 'rank' in formula and '- 0.5' in formula:
            # Alpha001类型：rank(...) - 0.5，值域[-0.5, 0.5]
            return self._generate_rank_0_5_explanation(min_value, max_value)
        elif 'correlation' in formula:
            # 相关性因子：值域[-1, 1]
            return self._generate_correlation_explanation(min_value, max_value)
        elif 'ts_rank' in formula and formula.startswith('-1'):
            # -ts_rank类型：值域[-1, 0]
            return self._generate_negative_rank_explanation(min_value, max_value)
        elif 'rank' in formula:
            # rank类型：值域[0, 1]或类似
            return self._generate_rank_explanation(min_value, max_value)
        else:
            # 通用解释
            return self._generate_generic_explanation(min_value, max_value, description)

    def _generate_rank_0_5_explanation(self, min_value: float, max_value: float) -> str:
        """生成rank(...)-0.5类型因子的解释（值域约[-0.5, 0.5]）"""
        return f'''
            因子值就是对股票的"排名打分"，范围在<strong>约-0.5 到 0.5</strong>之间：<br><br>
            • 因子值 = <strong>0.5</strong>：排名最靠前的股票（前1%），强烈推荐买入<br>
            • 因子值 = <strong>0.2 ~ 0.4</strong>：排名靠前的股票（前20%），建议买入<br>
            • 因子值 = <strong>0 ~ 0.1</strong>：排名中上的股票，表现一般<br>
            • 因子值 = <strong>0</strong>：排名中间的股票（中位数），中性<br>
            • 因子值 = <strong>-0.2 ~ -0.4</strong>：排名靠后的股票（后20%），建议卖出<br>
            • 因子值 = <strong>-0.5</strong>：排名最后（后1%），强烈回避<br>
            <br>
            💡 <strong>实际数据范围</strong>：[{min_value:.4f}, {max_value:.4f}]<br>
            💡 <strong>小提示</strong>：正值表示排名前50%（建议做多），负值表示排名后50%（建议做空）
        '''

    def _generate_correlation_explanation(self, min_value: float, max_value: float) -> str:
        """生成相关性因子的解释（值域[-1, 1]）"""
        return f'''
            因子值是两个变量的<strong>相关系数</strong>，范围在<strong>[-1, 1]</strong>之间：<br><br>
            • 因子值 ≈ <strong>1</strong>：强正相关，表示变量变化趋势一致<br>
            • 因子值 = <strong>0.3 ~ 0.7</strong>：中度正相关<br>
            • 因子值 ≈ <strong>0</strong>：无明显相关性<br>
            • 因子值 = <strong>-0.3 ~ -0.7</strong>：中度负相关<br>
            • 因子值 ≈ <strong>-1</strong>：强负相关，表示变量变化趋势相反<br>
            <br>
            💡 <strong>实际数据范围</strong>：[{min_value:.4f}, {max_value:.4f}]<br>
            💡 <strong>小提示</strong>：因子值越接近1或-1，表示特征越明显
        '''

    def _generate_negative_rank_explanation(self, min_value: float, max_value: float) -> str:
        """生成负排名因子的解释（值域约[-1, 0]）"""
        return f'''
            因子值是负向排名得分，范围在<strong>约-1 到 0</strong>之间：<br><br>
            • 因子值 ≈ <strong>0</strong>：排名最靠前的股票（表现最好）<br>
            • 因子值 = <strong>-0.3 ~ -0.1</strong>：排名靠前的股票<br>
            • 因子值 = <strong>-0.5</strong>：排名中间的股票<br>
            • 因子值 = <strong>-0.7 ~ -0.9</strong>：排名靠后的股票<br>
            • 因子值 ≈ <strong>-1</strong>：排名最后的股票（表现最差）<br>
            <br>
            💡 <strong>实际数据范围</strong>：[{min_value:.4f}, {max_value:.4f}]<br>
            💡 <strong>小提示</strong>：因子值越大（越接近0），表示股票表现越好
        '''

    def _generate_rank_explanation(self, min_value: float, max_value: float) -> str:
        """生成排名因子的解释（值域约[0, 1]或其他）"""
        return f'''
            因子值是对股票的"排名得分"，范围在<strong>[{min_value:.2f}, {max_value:.2f}]</strong>之间：<br><br>
            • 因子值接近 <strong>{max_value:.2f}</strong>：排名最靠前的股票，强烈推荐<br>
            • 因子值在 <strong>前25%</strong>：排名靠前的股票，建议关注<br>
            • 因子值在 <strong>中间50%</strong>：表现中等的股票<br>
            • 因子值在 <strong>后25%</strong>：排名靠后的股票，建议回避<br>
            • 因子值接近 <strong>{min_value:.2f}</strong>：排名最后的股票<br>
            <br>
            💡 <strong>小提示</strong>：因子值越高，该股票在该因子上表现越好
        '''

    def _generate_generic_explanation(self, min_value: float, max_value: float, description: str) -> str:
        """生成通用因子解释"""
        return f'''
            因子值范围在<strong>[{min_value:.4f}, {max_value:.4f}]</strong>之间：<br><br>
            • 因子值接近 <strong>{max_value:.4f}</strong>：该因子特征最强，建议关注<br>
            • 因子值在 <strong>前25%</strong>：因子特征较强<br>
            • 因子值在 <strong>中间50%</strong>：因子特征中等<br>
            • 因子值在 <strong>后25%</strong>：因子特征较弱<br>
            • 因子值接近 <strong>{min_value:.4f}</strong>：该因子特征最弱<br>
            <br>
            💡 <strong>因子说明</strong>：{description if description else '该因子用于量化分析股票特征'}<br>
            💡 <strong>小提示</strong>：因子值越大（或越小，取决于因子含义），表示该特征越明显
        '''

    def generate_html_report(self, results: Dict[str, Any], workflow_nodes: Dict = None, node_results: Dict = None) -> str:
        """
        生成HTML格式的详细报告

        Args:
            results: 回测结果字典
            workflow_nodes: 工作流节点信息字典
            node_results: 各节点的执行结果

        Returns:
            str: HTML报告内容
        """
        # 标准化键名 - 支持多种键名格式
        normalized_results = self._normalize_results(results)

        html_parts = []

        # HTML头部
        html_parts.append(self._get_html_header())

        # 标题区域
        html_parts.append(self._generate_title_section())

        # 工作流节点解释
        if workflow_nodes:
            html_parts.append(self._generate_workflow_section(workflow_nodes, node_results))

        # 因子公式详解（如果有因子计算节点）
        if workflow_nodes and any(n.node_type == 'factor_calculator' for n in workflow_nodes.values()):
            html_parts.append(self._generate_factor_formula_section(workflow_nodes, node_results))

        # 总体评价
        html_parts.append(self._generate_overview_section(normalized_results))

        # 收益曲线图表
        html_parts.append(self._generate_equity_curve_chart(results))

        # 核心指标解读
        html_parts.append(self._generate_metrics_section(normalized_results))

        # 详细分析
        html_parts.append(self._generate_analysis_section(normalized_results))

        # 投资建议
        html_parts.append(self._generate_advice_section(normalized_results))

        # 回测时间范围
        html_parts.append(self._generate_time_section(normalized_results))

        # HTML尾部
        html_parts.append(self._get_html_footer())

        return "\n".join(html_parts)

    def _generate_workflow_section(self, nodes: Dict, node_results: Dict = None) -> str:
        """生成工作流节点解释区域"""
        # 节点类型解释字典
        node_explanations = {
            'data_loader': {
                'name': '数据加载',
                'icon': '📊',
                'description': '从QMT下载股票历史行情数据（开盘价、收盘价、最高价、最低价、成交量等）',
                'beginner_friendly': '就像从交易软件导出股票数据一样，这是所有分析的基础。',
                'result_explanation': '''
                    <div style="margin-top: 1rem; padding: 1rem; background: #eff6ff; border-radius: 8px;">
                        <strong style="color: #1e40af;">📊 数据加载结果解读：</strong><br>
                        • <strong>日期范围</strong>：数据的起止时间，确保覆盖了您要分析的完整时间段<br>
                        • <strong>股票数量</strong>：成功获取到多少只股票的数据<br>
                        • <strong>前10条数据</strong>：展示部分数据样本，您可以检查数据是否正确加载<br>
                        <br>
                        💡 <strong>为什么显示这些？</strong><br>
                        数据加载是第一步，只有成功获取数据，后续的因子计算、回测才能进行。如果股票数量为0，请检查股票代码是否正确。
                    </div>
                '''
            },
            'factor_calculator': {
                'name': '因子计算',
                'icon': '📈',
                'description': '计算Alpha101因子，这些因子是量化分析师用来选股的数学公式',
                'beginner_friendly': '用数学公式给每只股票打分，分数越高说明股票越值得买。',
                'result_explanation': '''
                    <div style="margin-top: 1rem; padding: 1rem; background: #eff6ff; border-radius: 8px;">
                        <strong style="color: #1e40af;">📈 因子计算结果解读：</strong><br>
                        • <strong>日期范围</strong>：因子值的时间跨度<br>
                        • <strong>股票数量</strong>：为多少只股票计算了因子值<br>
                        • <strong>数据范围</strong>：因子值的最小值和最大值<br>
                        • <strong>均值</strong>：因子值的平均水平<br>
                        • <strong>标准差</strong>：因子值的波动程度<br>
                        <br>
                        💡 <strong>因子值的含义</strong>：<br>
                        不同的因子有不同的值域和含义，具体解释请查看"节点执行结果"中的动态解读部分。
                    </div>
                '''
            },
            'ic_analyzer': {
                'name': 'IC分析',
                'icon': '🔍',
                'description': 'IC（Information Coefficient，信息系数）衡量因子预测能力的重要指标',
                'beginner_friendly': 'IC就像因子的"考试分数"，分数越高说明因子选股越准。通常IC>0.03就算及格，>0.05算优秀。',
                'result_explanation': '''
                    <div style="margin-top: 1rem; padding: 1rem; background: #f0fdf4; border-radius: 8px;">
                        <strong style="color: #166534;">🔍 IC分析结果解读：</strong><br>
                        <strong>什么是IC？</strong><br>
                        IC = 因子值和股票收益率的<strong>相关系数</strong>，范围是-1到1。<br><br>
                        • <strong>IC > 0.05</strong>：因子非常优秀，选股能力很强 ⭐⭐⭐⭐⭐<br>
                        • <strong>0.03 < IC < 0.05</strong>：因子表现良好 ⭐⭐⭐⭐<br>
                        • <strong>0.01 < IC < 0.03</strong>：因子勉强可用 ⭐⭐⭐<br>
                        • <strong>IC < 0.01</strong>：因子基本没用 ⭐<br><br>
                        <strong>IR（Information Ratio）</strong>：IC的均值/IC的标准差<br>
                        • IR > 1.0：因子稳定优秀<br>
                        • IR > 0.5：因子稳定可用<br>
                        • IR < 0.5：因子波动太大，不稳定<br><br>
                        💡 <strong>简单理解：</strong><br>
                        IC = 0.05 意味着如果因子值高，股票涨的概率也高；因子值低，股票跌的概率也高。这就是我们要找的好因子！
                    </div>
                '''
            },
            'backtester': {
                'name': '回测分析',
                'icon': '💰',
                'description': '模拟历史交易，计算策略的收益、风险等指标',
                'beginner_friendly': '就像用历史数据"模拟炒股"，看看如果用这个策略过去能赚多少钱。',
                'result_explanation': '''
                    <div style="margin-top: 1rem; padding: 1rem; background: #eff6ff; border-radius: 8px;">
                        <strong style="color: #1e40af;">💰 回测结果解读：</strong><br>
                        回测告诉我们如果过去用这个策略交易，最终收益会是多少。<br><br>
                        <strong>关键指标说明：</strong><br>
                        • <strong>总收益率</strong>：投资100元，最后变成多少钱（包括本金）<br>
                        • <strong>年化收益率</strong>：平均每年赚多少百分比<br>
                        • <strong>夏普比率</strong>：赚钱的同时承担了多少风险（越高越好）<br>
                        • <strong>最大回撤</strong>：最惨的时候亏了多少百分比（越小越好）<br><br>
                        💡 <strong>重要提示：</strong><br>
                        回测收益好 ≠ 实盘也能赚钱！历史数据不代表未来。实盘前要充分测试，控制风险！
                    </div>
                '''
            },
            'signal_generator': {
                'name': '信号生成',
                'icon': '🎯',
                'description': '根据因子值生成买卖信号（做多、做空、观望）',
                'beginner_friendly': '把因子打分转换成具体的买卖指令：分数高就买，分数低就卖。',
                'result_explanation': '''
                    <div style="margin-top: 1rem; padding: 1rem; background: #eff6ff; border-radius: 8px;">
                        <strong style="color: #1e40af;">🎯 信号生成结果解读：</strong><br>
                        <strong>什么是买卖信号？</strong><br>
                        信号告诉我们每只股票应该：<br>
                        • <strong>1 (做多)</strong>：买入并持有，预期股票会涨<br>
                        • <strong>0 (观望)</strong>：不操作，等待机会<br>
                        • <strong>-1 (做空)</strong>：卖出或做空，预期股票会跌<br><br>
                        <strong>输出的数据说明：</strong><br>
                        • <strong>日期范围</strong>：信号覆盖的时间段，每天都会生成新的信号<br>
                        • <strong>股票数量</strong>：为多少只股票生成了信号<br>
                        • <strong>前10条数据</strong>：展示部分信号样本，可以查看具体的买卖指令<br><br>
                        💡 <strong>实际应用：</strong><br>
                        信号生成后，还需要配合<strong>交易执行模块</strong>才能真正下单。这个节点只是告诉你"买什么、卖什么"，但不会自动交易。
                    </div>
                '''
            },
            'performance_analyzer': {
                'name': '绩效分析',
                'icon': '📊',
                'description': '计算策略的详细绩效指标（收益率、波动率、夏普比率等）',
                'beginner_friendly': '对策略进行全面体检，看看它到底赚不赚钱，风险大不大。',
                'result_explanation': '''
                    <div style="margin-top: 1rem; padding: 1rem; background: #eff6ff; border-radius: 8px;">
                        <strong style="color: #1e40af;">📊 绩效分析结果解读：</strong><br>
                        绩效分析会计算一系列专业指标，全面评估策略表现。<br><br>
                        <strong>主要指标：</strong><br>
                        • <strong>累计收益率</strong>：整个回测期间的总收益<br>
                        • <strong>年化收益率</strong>：折算成年度收益率，便于比较<br>
                        • <strong>波动率</strong>：收益的波动程度，波动越大风险越大<br>
                        • <strong>夏普比率</strong>：每承担一单位风险获得的收益（>1为良好）<br>
                        • <strong>最大回撤</strong>：历史上最大亏损幅度<br>
                        • <strong>胜率</strong>：盈利交易占总交易的比例<br><br>
                        💡 <strong>如何判断好坏：</strong><br>
                        年化收益率>15% 且 夏普比率>1 且 最大回撤<20% = 优秀的策略
                    </div>
                '''
            }
        }

        # 生成节点列表HTML
        nodes_html = ""
        for idx, (node_id, node) in enumerate(nodes.items(), 1):
            node_type = node.node_type
            explanation = node_explanations.get(node_type, {
                'name': node_type,
                'icon': '📦',
                'description': f'{node_type}节点',
                'beginner_friendly': f'执行{node_type}操作',
                'result_explanation': ''
            })

            # 获取节点参数
            params = node.params if hasattr(node, 'params') else {}
            params_html = self._format_node_params(node_type, params)

            # 获取节点执行结果
            result_html = ''
            if node_results and node_id in node_results:
                result = node_results[node_id]
                if result is not None:
                    # 传递节点对象，以便获取参数信息
                    result_html = self._format_node_result(node_type, result, node)

            nodes_html += f"""
                        <div style="background: white; padding: 1.5rem; border-radius: 12px; margin-bottom: 1rem; border-left: 4px solid #667eea; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                            <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                                <span style="font-size: 2rem; margin-right: 1rem;">{explanation['icon']}</span>
                                <div>
                                    <div style="font-size: 1.2rem; font-weight: 600; color: #1f2937;">{idx}. {explanation['name']}</div>
                                    <div style="font-size: 0.9rem; color: #6b7280; margin-top: 0.3rem;">节点ID: {node_id[:8]}...</div>
                                </div>
                            </div>

                            <div style="margin-bottom: 1rem;">
                                <div style="font-weight: 600; color: #374151; margin-bottom: 0.5rem;">📝 节点功能：</div>
                                <div style="color: #4b5563; line-height: 1.6;">{explanation['description']}</div>
                            </div>

                            <div style="margin-bottom: 1rem; padding: 1rem; background: #fef3c7; border-radius: 8px; border-left: 3px solid #f59e0b;">
                                <div style="font-weight: 600; color: #92400e; margin-bottom: 0.5rem;">💡 新手理解：</div>
                                <div style="color: #78350f; line-height: 1.6;">{explanation['beginner_friendly']}</div>
                            </div>

                            {result_html}

                            {explanation.get('result_explanation', '')}

                            {params_html}
                        </div>
            """

        return f"""
                <div class="section">
                    <h2 class="section-title">🔧 工作流节点说明</h2>
                    <div style="background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%); padding: 1.5rem; border-radius: 12px; margin-bottom: 2rem;">
                        <div style="color: #4c1d95; font-weight: 600; margin-bottom: 0.5rem;">📋 工作流概览</div>
                        <div style="color: #6d28d9; line-height: 1.6;">
                            本次回测共使用了 <strong>{len(nodes)}</strong> 个节点，按顺序执行。
                            每个节点都负责一个特定的任务，组合起来形成完整的量化分析流程。
                        </div>
                    </div>
                    {nodes_html}
                </div>
        """

    def _format_factor_calculator_result(self, result: pd.Series, node) -> str:
        """格式化因子计算节点的结果，包含动态因子值解释"""
        # 获取因子名称
        factor_name = 'alpha001'  # 默认值
        if node and hasattr(node, 'params'):
            factor_name = node.params.get('factor_name', 'alpha001')

        # 获取基本信息
        info_text = []
        if hasattr(result.index, 'names'):
            index_names = result.index.names
            if isinstance(index_names, list) and len(index_names) >= 2:
                # MultiIndex
                if 'date' in index_names:
                    dates = result.index.get_level_values('date')
                    info_text.append(f"• <strong>日期范围</strong>：{dates.min()} ~ {dates.max()}")
                    info_text.append(f"• <strong>交易日数</strong>：{len(dates.unique())} 天")

                if 'symbol' in index_names:
                    symbols = result.index.get_level_values('symbol').unique()
                    info_text.append(f"• <strong>股票数量</strong>：{len(symbols)} 只")

        # 显示统计信息
        min_val = float(result.min())
        max_val = float(result.max())
        mean_val = float(result.mean())
        std_val = float(result.std())

        info_text.append(f"• <strong>数据范围</strong>：[{min_val:.6f}, {max_val:.6f}]")
        info_text.append(f"• <strong>均值</strong>：{mean_val:.6f}")
        info_text.append(f"• <strong>标准差</strong>：{std_val:.6f}")

        info_html = '<br>'.join(info_text)

        # 获取动态因子值解释
        factor_explanation = self._get_factor_value_explanation(factor_name, min_val, max_val)

        return f'''
                        <div style="margin-top: 1rem; padding: 1rem; background: #f0fdf4; border-radius: 8px; border-left: 3px solid #10b981;">
                            <div style="font-weight: 600; color: #166534; margin-bottom: 0.5rem;">✅ 因子计算结果：</div>
                            <div style="color: #14532d; line-height: 1.8; margin-bottom: 1rem;">
                                {info_html}
                            </div>
                            <div style="margin-top: 1rem; padding: 1rem; background: #eff6ff; border-radius: 8px; border-left: 3px solid #3b82f6;">
                                <div style="font-weight: 600; color: #1e40af; margin-bottom: 0.5rem;">💡 <strong>{factor_name.upper()}</strong> 因子值解读：</div>
                                <div style="color: #1e3a8a; line-height: 1.8;">
                                    {factor_explanation}
                                </div>
                            </div>
                        </div>
            '''

    def _format_node_result(self, node_type: str, result: Any, node=None) -> str:
        """格式化节点执行结果"""
        import pandas as pd
        import numpy as np

        if result is None:
            return '''
                        <div style="margin-top: 1rem; padding: 1rem; background: #fef2f2; border-radius: 8px; border-left: 3px solid #ef4444;">
                            <div style="font-weight: 600; color: #991b1b; margin-bottom: 0.5rem;">⚠️ 节点执行结果：</div>
                            <div style="color: #7f1d1d;">该节点执行失败或没有返回数据</div>
                        </div>
            '''

        # 回测节点特殊处理
        if node_type == 'backtester' and isinstance(result, dict):
            return self._format_backtest_result(result)

        # IC分析节点特殊处理
        if node_type == 'ic_analyzer' and isinstance(result, dict):
            return self._format_ic_result(result)

        # 因子计算节点特殊处理 - 添加动态因子值解释
        if node_type == 'factor_calculator' and isinstance(result, pd.Series):
            return self._format_factor_calculator_result(result, node)

        # Series类型结果（因子值、信号等）
        if isinstance(result, pd.Series):
            if len(result) == 0:
                return '''
                            <div style="margin-top: 1rem; padding: 1rem; background: #fef3c7; border-radius: 8px;">
                                <div style="font-weight: 600; color: #92400e;">📊 节点执行结果：</div>
                                <div style="color: #78350f; margin-top: 0.5rem;">返回了空数据</div>
                            </div>
                '''

            # 获取基本信息
            info_text = []
            if hasattr(result.index, 'names'):
                index_names = result.index.names
                if isinstance(index_names, list) and len(index_names) >= 2:
                    # MultiIndex
                    if 'date' in index_names:
                        dates = result.index.get_level_values('date')
                        info_text.append(f"• <strong>日期范围</strong>：{dates.min()} ~ {dates.max()}")
                        info_text.append(f"• <strong>交易日数</strong>：{len(dates.unique())} 天")

                    if 'symbol' in index_names:
                        symbols = result.index.get_level_values('symbol').unique()
                        info_text.append(f"• <strong>股票数量</strong>：{len(symbols)} 只")

                        # 显示股票列表（最多显示5只）
                        symbol_list = list(symbols[:5])
                        if len(symbols) > 5:
                            symbol_list.append(f"... (共{len(symbols)}只)")
                        info_text.append(f"• <strong>股票列表</strong>：{', '.join(symbol_list)}")
                else:
                    # 单索引
                    if len(result) > 0:
                        info_text.append(f"• <strong>数据量</strong>：{len(result)} 条")
                        if hasattr(result.index, 'min'):
                            info_text.append(f"• <strong>范围</strong>：{result.index.min()} ~ {result.index.max()}")

            # 显示统计信息
            info_text.append(f"• <strong>数据类型</strong>：{result.dtype}")
            info_text.append(f"• <strong>数据范围</strong>：[{result.min():.4f}, {result.max():.4f}]")
            info_text.append(f"• <strong>均值</strong>：{result.mean():.4f}")
            info_text.append(f"• <strong>标准差</strong>：{result.std():.4f}")

            info_html = '<br>'.join(info_text)

            return f'''
                        <div style="margin-top: 1rem; padding: 1rem; background: #f0fdf4; border-radius: 8px; border-left: 3px solid #10b981;">
                            <div style="font-weight: 600; color: #166534; margin-bottom: 0.5rem;">✅ 节点执行结果：</div>
                            <div style="color: #14532d; line-height: 1.8;">
                                {info_html}
                            </div>
                        </div>
            '''

        # DataFrame类型结果
        elif isinstance(result, pd.DataFrame):
            return f'''
                        <div style="margin-top: 1rem; padding: 1rem; background: #f0fdf4; border-radius: 8px;">
                            <div style="font-weight: 600; color: #166534;">✅ 节点执行结果：</div>
                            <div style="color: #14532d; margin-top: 0.5rem;">
                                • <strong>数据形状</strong>：{result.shape[0]} 行 × {result.shape[1]} 列<br>
                                • <strong>列名</strong>：{', '.join(result.columns.tolist()[:5])}{'...' if len(result.columns) > 5 else ''}<br>
                                • <strong>行数</strong>：{len(result)} 条记录
                            </div>
                        </div>
            '''

        # 字典类型结果（IC分析、回测结果等）
        elif isinstance(result, dict):
            items = []
            for key, value in result.items():
                if isinstance(value, (int, float)):
                    items.append(f"• <strong>{key}</strong>：{value}")
                elif isinstance(value, str):
                    items.append(f"• <strong>{key}</strong>：{value}")
                elif isinstance(value, pd.Series):
                    items.append(f"• <strong>{key}</strong>：Series ({len(value)} 条)")
                elif value is None:
                    items.append(f"• <strong>{key}</strong>：None")
                else:
                    items.append(f"• <strong>{key}</strong>：{type(value).__name__}")

            return f'''
                        <div style="margin-top: 1rem; padding: 1rem; background: #f0fdf4; border-radius: 8px;">
                            <div style="font-weight: 600; color: #166534;">✅ 节点执行结果：</div>
                            <div style="color: #14532d; margin-top: 0.5rem; line-height: 1.8;">
                                {'<br>'.join(items[:10])}
                                {f"<br>... (共{len(result)}项)" if len(result) > 10 else ""}
                            </div>
                        </div>
            '''

        return ''

    def _format_backtest_result(self, result: dict) -> str:
        """格式化回测节点结果"""
        html_parts = []

        # 提取关键指标
        summary = result.get('summary', {})
        long_short = result.get('long_short_results', {})

        # 显示摘要信息
        if summary:
            html_parts.append('''
                        <div style="margin-top: 1rem; padding: 1rem; background: #f0fdf4; border-radius: 8px; border-left: 3px solid #10b981;">
                            <div style="font-weight: 600; color: #166534; margin-bottom: 1rem;">✅ 回测核心指标：</div>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem;">
                        ''')

            # 总收益率
            if 'total_return' in summary or 'ls_total_return' in summary:
                total_return = summary.get('total_return') or summary.get('ls_total_return', 0)
                total_return_pct = total_return * 100
                color = '#10b981' if total_return >= 0 else '#ef4444'
                html_parts.append(f'''
                            <div style="padding: 0.8rem; background: white; border-radius: 8px; border-left: 3px solid {color};">
                                <div style="font-size: 0.85rem; color: #6b7280;">💰 总收益率</div>
                                <div style="font-size: 1.5rem; font-weight: bold; color: {color};">{total_return_pct:.2f}%</div>
                                <div style="font-size: 0.75rem; color: #9ca3af; margin-top: 0.3rem;">
                                    {"盈利" if total_return >= 0 else "亏损"}
                                </div>
                            </div>
                        ''')

            # 年化收益率
            if 'annual_return' in summary or 'ls_annual_return' in summary:
                annual_return = summary.get('annual_return') or summary.get('ls_annual_return', 0)
                annual_return_pct = annual_return * 100
                color = '#10b981' if annual_return >= 0 else '#ef4444'
                html_parts.append(f'''
                            <div style="padding: 0.8rem; background: white; border-radius: 8px; border-left: 3px solid {color};">
                                <div style="font-size: 0.85rem; color: #6b7280;">📊 年化收益率</div>
                                <div style="font-size: 1.5rem; font-weight: bold; color: {color};">{annual_return_pct:.2f}%</div>
                                <div style="font-size: 0.75rem; color: #9ca3af; margin-top: 0.3rem;">
                                    每年平均收益
                                </div>
                            </div>
                        ''')

            # 夏普比率
            if 'sharpe_ratio' in summary or 'ls_sharpe_ratio' in summary:
                sharpe = summary.get('sharpe_ratio') or summary.get('ls_sharpe_ratio', 0)
                sharpe_color = '#10b981' if sharpe > 1 else '#f59e0b' if sharpe > 0 else '#ef4444'
                html_parts.append(f'''
                            <div style="padding: 0.8rem; background: white; border-radius: 8px; border-left: 3px solid {sharpe_color};">
                                <div style="font-size: 0.85rem; color: #6b7280;">🎯 夏普比率</div>
                                <div style="font-size: 1.5rem; font-weight: bold; color: {sharpe_color};">{sharpe:.3f}</div>
                                <div style="font-size: 0.75rem; color: #9ca3af; margin-top: 0.3rem;">
                                    {"优秀" if sharpe > 1 else "良好" if sharpe > 0 else "较差"}
                                </div>
                            </div>
                        ''')

            # 最大回撤
            if 'max_drawdown' in summary or 'ls_max_drawdown' in summary:
                max_dd = summary.get('max_drawdown') or summary.get('ls_max_drawdown', 0)
                max_dd_pct = abs(max_dd) * 100
                dd_color = '#10b981' if max_dd > -0.1 else '#f59e0b' if max_dd > -0.2 else '#ef4444'
                html_parts.append(f'''
                            <div style="padding: 0.8rem; background: white; border-radius: 8px; border-left: 3px solid {dd_color};">
                                <div style="font-size: 0.85rem; color: #6b7280;">📉 最大回撤</div>
                                <div style="font-size: 1.5rem; font-weight: bold; color: {dd_color};">{max_dd_pct:.2f}%</div>
                                <div style="font-size: 0.75rem; color: #9ca3af; margin-top: 0.3rem;">
                                    {"风险很小" if max_dd > -0.1 else "风险可控" if max_dd > -0.2 else "风险较大"}
                                </div>
                            </div>
                        ''')

            html_parts.append('''
                            </div>
                        </div>
                        <div style="margin-top: 1rem; padding: 1rem; background: #eff6ff; border-radius: 8px;">
                            <div style="font-weight: 600; color: #1e40af; margin-bottom: 0.5rem;">📊 收益曲线数据说明：</div>
                            <div style="color: #1e40af; line-height: 1.8;">
                                <strong>long_short_results</strong> 包含每日收益数据：<br>
                                • <strong>returns</strong>：多空组合每日收益率<br>
                                • <strong>cumulative_return</strong>：累计收益率（从1开始）<br>
                                <br>
                                例如：cumulative_return = 0.539439 表示最终收益率为 53.94%
                            </div>
                        </div>
                        ''')

        return '\n'.join(html_parts)

    def _format_ic_result(self, result: dict) -> str:
        """格式化IC分析结果"""
        html_parts = []

        html_parts.append('''
                    <div style="margin-top: 1rem; padding: 1rem; background: #f0fdf4; border-radius: 8px; border-left: 3px solid #10b981;">
                        <div style="font-weight: 600; color: #166534; margin-bottom: 1rem;">✅ IC分析结果：</div>
        ''')

        # IC统计
        if 'ic_stats' in result:
            stats = result['ic_stats']
            ic_mean = stats.get('ic_mean', 0)
            ic_std = stats.get('ic_std', 0)
            ic_ir = stats.get('ic_ir', 0)
            ic_prob = stats.get('ic_prob', 0)

            # IC均值评级
            if abs(ic_mean) > 0.05:
                ic_rating = "⭐⭐⭐⭐⭐ 非常优秀"
                ic_color = "#10b981"
            elif abs(ic_mean) > 0.03:
                ic_rating = "⭐⭐⭐⭐ 表现良好"
                ic_color = "#3b82f6"
            elif abs(ic_mean) > 0.01:
                ic_rating = "⭐⭐⭐ 勉强可用"
                ic_color = "#f59e0b"
            else:
                ic_rating = "⭐ 基本没用"
                ic_color = "#ef4444"

            html_parts.append(f'''
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1rem;">
                            <div style="padding: 1rem; background: white; border-radius: 8px;">
                                <div style="font-size: 0.85rem; color: #6b7280; margin-bottom: 0.3rem;">IC均值</div>
                                <div style="font-size: 1.8rem; font-weight: bold; color: {ic_color};">{ic_mean:.4f}</div>
                                <div style="font-size: 0.75rem; color: {ic_color}; margin-top: 0.3rem;">{ic_rating}</div>
                            </div>
                            <div style="padding: 1rem; background: white; border-radius: 8px;">
                                <div style="font-size: 0.85rem; color: #6b7280; margin-bottom: 0.3rem;">IC标准差</div>
                                <div style="font-size: 1.5rem; font-weight: 600; color: #374151;">{ic_std:.4f}</div>
                                <div style="font-size: 0.75rem; color: #9ca3af; margin-top: 0.3rem;">波动程度</div>
                            </div>
                            <div style="padding: 1rem; background: white; border-radius: 8px;">
                                <div style="font-size: 0.85rem; color: #6b7280; margin-bottom: 0.3rem;">IC_IR</div>
                                <div style="font-size: 1.5rem; font-weight: 600; color: #374151;">{ic_ir:.3f}</div>
                                <div style="font-size: 0.75rem; color: #9ca3af; margin-top: 0.3rem;">
                                    {"稳定优秀" if ic_ir > 1 else "稳定可用" if ic_ir > 0.5 else "不够稳定"}
                                </div>
                            </div>
                            <div style="padding: 1rem; background: white; border-radius: 8px;">
                                <div style="font-size: 0.85rem; color: #6b7280; margin-bottom: 0.3rem;">t统计量</div>
                                <div style="font-size: 1.5rem; font-weight: 600; color: #374151;">{stats.get('t_stat', 0):.3f}</div>
                                <div style="font-size: 0.75rem; color: #9ca3af; margin-top: 0.3rem;">统计显著性</div>
                            </div>
                        </div>
            ''')

        html_parts.append('''
                    </div>
                    <div style="margin-top: 1rem; padding: 1rem; background: #fef3c7; border-radius: 8px;">
                        <div style="font-weight: 600; color: #92400e; margin-bottom: 0.5rem;">💡 结果解读：</div>
                        <div style="color: #78350f; line-height: 1.8;">
                            IC均值代表因子预测能力的平均水平，IC_IR代表稳定性。
                            IC > 0.03 且 IR > 0.5 说明因子有效且稳定。
                        </div>
                    </div>
        ''')

        return '\n'.join(html_parts)

    def _generate_factor_formula_section(self, nodes: Dict, node_results: Dict = None) -> str:
        """生成因子公式详解区域"""
        # 查找因子计算节点
        factor_node = None
        for node_id, node in nodes.items():
            if node.node_type == 'factor_calculator':
                factor_node = node
                break

        if not factor_node:
            return ''

        # 获取因子名称
        factor_name = factor_node.params.get('factor_name', 'alpha001')

        # 获取因子元数据
        try:
            from src.factor_engine.factor_metadata import get_factor_info
            factor_info = get_factor_info(factor_name)
        except:
            factor_info = {
                'name': factor_name,
                'formula': '因子公式无法获取',
                'description': '无法获取因子描述',
                'logic': '无法获取逻辑解释'
            }

        return f'''
                <div class="section">
                    <h2 class="section-title">📐 因子计算公式详解</h2>
                    <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); padding: 2rem; border-radius: 12px; border-left: 5px solid #f59e0b;">
                        <div style="font-size: 1.5rem; font-weight: 600; color: #92400e; margin-bottom: 1rem;">📊 {factor_info['name']} ({factor_name})</div>
                        <div style="color: #78350f; font-size: 1.1rem; margin-bottom: 1rem;">{factor_info['category']} · {factor_info.get('author', 'WorldQuant')}</div>
                        <div style="color: #78350f; margin-bottom: 1.5rem; line-height:1.8;">{factor_info['description']}</div>
                    </div>

                    <div style="margin-top: 2rem;">
                        <h3 style="color: #1f2937; font-size: 1.3rem; margin-bottom: 1rem;">📝 计算公式</h3>
                        <div style="background: white; padding: 1.5rem; border-radius: 12px; border-left: 4px solid #667eea;">
                            <code style="display: block; background: #f8f9fa; padding: 1rem; border-radius: 8px; font-family: 'Courier New', monospace; line-height: 1.6; font-size: 0.95rem; word-wrap: break-word; white-space: pre-wrap;">
{factor_info['formula']}
                            </code>
                        </div>
                    </div>

                    <div style="margin-top: 2rem;">
                        <h3 style="color: #1f2937; font-size: 1.3rem; margin-bottom: 1rem;">💡 公式解读（分步骤说明）</h3>
                        {self._explain_formula_alpha001(factor_info)}
                    </div>

                    <div style="margin-top: 2rem;">
                        <h3 style="color: #1f2937; font-size: 1.3rem; margin-bottom: 1rem;">🎯 因子的实际意义</h3>
                        <div style="background: white; padding: 1.5rem; border-radius: 12px; border-left: 4px solid #10b981;">
                            <div style="color: #065f46; line-height: 1.8;">
                                {factor_info['logic']}
                            </div>
                        </div>
                    </div>

                    <div style="margin-top: 2rem;">
                        <h3 style="color: #1f2937; font-size: 1.3rem; margin-bottom: 1rem;">📊 实际计算示例</h3>
                        {self._generate_formula_example()}
                    </div>
                </div>
        '''

    def _explain_formula_alpha001(self, factor_info: dict) -> str:
        """解释Alpha001公式的每个步骤"""
        return '''
            <div style="background: white; padding: 1.5rem; border-radius: 12px; border-left: 4px solid #3b82f6;">
                <div style="color: #1e3a8a; line-height: 1.8;">
                    <strong>步骤1：判断涨跌</strong><br>
                    <code>returns < 0 ? stddev(returns, 20) : close</code><br>
                    • 如果当天<strong>下跌</strong>：计算过去20天的<strong>波动率</strong><br>
                    • 如果当天<strong>上涨</strong>：使用当天<strong>收盘价</strong><br>
                    <br>
                    <strong>含义：</strong>下跌时用波动率，上涨时用价格，反映市场情绪<br>
                    <br>
                    <strong>步骤2：计算幂次</strong><br>
                    <code>SignedPower(..., 2)</code><br>
                    • 对步骤1的结果进行<strong>平方</strong>（2次方）<br>
                    <br>
                    <strong>步骤3：找最大值</strong><br>
                    <code>Ts_ArgMax(..., 5)</code><br>
                    • 在过去5天内找<strong>最大值</strong><br>
                    <br>
                    <strong>步骤4：归一化</strong><br>
                    <code>... - 0.5</code><br>
                    • 减去0.5，让因子值围绕0波动<br>
                    <br>
                    💡 <strong>简单理解：</strong><br>
                    这个因子衡量股票的<strong>动量</strong>（趋势强度），同时考虑了<strong>波动率</strong>。
                    因子值越高，说明股票近期表现越好。
                </div>
            </div>
        '''

    def _generate_formula_example(self) -> str:
        """生成因子计算的数值示例"""
        return '''
            <div style="background: #f0fdf4; padding: 1.5rem; border-radius: 12px; border-left: 4px solid #059669;">
                <div style="font-weight: 600; color: #065f46; margin-bottom: 1rem;">🔢 数值示例</div>
                <div style="color: #064e3b; line-height: 1.8;">
                    <strong>假设某股票过去5天的数据：</strong><br>
                    <table style="width: 100%; border-collapse: collapse; margin-top: 1rem;">
                        <tr style="background: #d1fae5; text-align: left;">
                            <th style="padding: 0.5rem; border: 1px solid #047857;">日期</th>
                            <th style="padding: 0.5rem; border: 1px solid #047857;">收盘价</th>
                            <th style="padding: 0.5rem; border: 1px solid #047857;">收益率</th>
                        </tr>
                        <tr>
                            <td style="padding: 0.5rem; border: 1px solid #047857;">2023-02-06</td>
                            <td style="padding: 0.5rem; border: 1px solid #047857;">10.0</td>
                            <td style="padding: 0.5rem; border: 1px solid #047857;">-0.02 (下跌)</td>
                        </tr>
                        <tr>
                            <td style="padding: 0.5rem; border: 1px solid #047857;">2023-02-07</td>
                            <td style="padding: 0.5rem; border: 1px solid #047857;">9.8</td>
                            <td style="padding: 0.5rem; border: 1px solid #047857;">-0.03 (下跌)</td>
                        </tr>
                        <tr>
                            <td style="padding: 0.5rem; border: 1px solid #047857;">2023-02-08</td>
                            <td style="padding: 0.5rem; border: 1px solid #047857;">10.2</td>
                            <td style="padding: 0.5rem; border: 1px solid #047857;">+0.04 (上涨)</td>
                        </tr>
                        <tr>
                            <td style="padding: 0.5rem; border: 1px solid #047857;">2023-02-09</td>
                            <td style="padding: 0.5rem; border: 1px solid #047857;">10.5</td>
                            <td style="padding: 0.5rem; border: 1px solid #047857;">+0.05 (上涨)</td>
                        </tr>
                        <tr>
                            <td style="padding: 0.5rem; border: 1px solid #047857;">2023-02-10</td>
                            <td style="padding: 0.5rem; border: 1px solid #047857;">10.3</td>
                            <td style="padding: 0.5rem; border: 1px solid #047857;">-0.01 (下跌)</td>
                        </tr>
                    </table>

                    <div style="margin-top: 1rem; padding: 1rem; background: white; border-radius: 8px;">
                        <div style="font-family: 'Courier New', monospace; font-size: 0.9rem;">
                            因子值计算过程：<br>
                            1. 判断涨跌：今天下跌 → 使用波动率<br>
                            2. 计算幂次：波动率²<br>
                            3. 找最大值：过去5天最大<br>
                            4. 归一化：减去0.5<br>
                            <strong>最终因子值：-0.2</strong>
                        </div>
                    </div>

                    <div style="margin-top: 1rem; padding: 1rem; background: #fef3c7; border-radius: 8px;">
                        <div style="font-weight: 600; color: #92400e; margin-bottom: 0.5rem;">💡 解读：</div>
                        <div style="color: #78350f; line-height: 1.6;">
                            • 因子值为负说明该股票近期表现不佳<br>
                            • 因子值接近0说明股票表现平平<br>
                            • 因子值为正说明股票近期表现良好<br>
                            <br>
                            在回测中，我们会<strong>买入因子值高</strong>的股票，<strong>卖出因子值低</strong>的股票。
                        </div>
                    </div>
                </div>
            </div>
        '''

    def _format_node_params(self, node_type: str, params: Dict) -> str:
        """格式化节点参数显示"""
        if not params:
            return ""

        # 参数说明字典
        param_explanations = {
            'symbols': '股票代码列表：选择要分析的股票',
            'start_date': '开始日期：回测的起始时间',
            'end_date': '结束日期：回测的结束时间',
            'fields': '数据字段：选择需要的数据类型（价格、成交量等）',
            'factor_name': '因子名称：选择使用哪个Alpha101因子',
            'input_mode': '输入模式：选择股票池的来源',
            'preset': '预设类型：预定义的股票池（如沪深300、创业板等）',
            'top_quantile': '做多比例：选择表现最好的多少比例股票做多',
            'bottom_quantile': '做空比例：选择表现最差多少比例股票做空',
            'transaction_cost': '交易成本：每次买卖的费用比例（默认0.1%）',
            'method': '信号方法：生成买卖信号的方式（按排名或按值）',
            'threshold': '阈值：判断买卖的标准'
        }

        params_html = '<div style="margin-top: 1rem;"><div style="font-weight: 600; color: #374151; margin-bottom: 0.5rem;">⚙️ 节点参数：</div><div style="background: #f9fafb; padding: 1rem; border-radius: 8px;">'

        for key, value in params.items():
            # 跳过一些不重要的参数
            if key in ['position', 'input_mode', 'custom_symbols', 'symbols']:
                continue

            explanation = param_explanations.get(key, '')
            value_display = str(value)

            # 限制显示长度
            if isinstance(value, list) and len(value) > 5:
                value_display = f"[{value[0]}, {value[1]}, ... 共{len(value)}项]"

            params_html += f"""
                            <div style="margin-bottom: 0.8rem; padding-bottom: 0.8rem; border-bottom: 1px solid #e5e7eb;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
                                    <span style="font-weight: 600; color: #4b5563;">{key}</span>
                                    <span style="color: #667eea; font-family: monospace;">{value_display}</span>
                                </div>
                                {f'<div style="font-size: 0.85rem; color: #6b7280;">💡 {explanation}</div>' if explanation else ''}
                            </div>
            """

        params_html += '</div></div>'
        return params_html

    def _generate_time_section(self, results: Dict[str, Any]) -> str:
        """生成时间范围区域"""
        start_date = results.get('start_date', '未知')
        end_date = results.get('end_date', '未知')
        trading_days = results.get('trading_days', 0)

        return f"""
                <div class="section">
                    <h2 class="section-title">📅 回测时间范围</h2>
                    <div style="background: white; padding: 1.5rem; border-radius: 12px; border-left: 4px solid #667eea; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                        <div style="display: flex; justify-content: space-around; text-align: center;">
                            <div>
                                <div style="font-size: 0.9rem; color: #9ca3af; margin-bottom: 0.3rem;">开始日期</div>
                                <div style="font-size: 1.3rem; font-weight: bold; color: #667eea;">{start_date}</div>
                            </div>
                            <div>
                                <div style="font-size: 0.9rem; color: #9ca3af; margin-bottom: 0.3rem;">结束日期</div>
                                <div style="font-size: 1.3rem; font-weight: bold; color: #667eea;">{end_date}</div>
                            </div>
                            <div>
                                <div style="font-size: 0.9rem; color: #9ca3af; margin-bottom: 0.3rem;">交易日数</div>
                                <div style="font-size: 1.3rem; font-weight: bold; color: #667eea;">{trading_days} 天</div>
                            </div>
                        </div>
                    </div>

                </div>
        """

    def _get_hs300_benchmark(self, dates: pd.DatetimeIndex) -> Optional[pd.Series]:
        """
        获取沪深300指数的真实收益数据

        Args:
            dates: 策略的日期索引

        Returns:
            pd.Series: 沪深300的累积收益率，如果获取失败返回None
        """
        try:
            # 提取日期范围
            if len(dates) == 0:
                return None

            start_date = dates.min()
            end_date = dates.max()

            print(f"[DEBUG] 尝试获取沪深300数据: {start_date} 到 {end_date}")

            # 尝试从EasyXT获取沪深300数据
            try:
                from src.easyxt_adapter.api_wrapper import get_easyxt_instance
                easyxt = get_easyxt_instance()

                if easyxt is None:
                    print("[DEBUG] EasyXT实例为None，无法获取沪深300数据")
                    return None

                print(f"[DEBUG] EasyXT实例类型: {type(easyxt)}")

                # 检查EasyXT连接状态
                if hasattr(easyxt, 'connected'):
                    if not easyxt.connected:
                        print("[DEBUG] EasyXT未连接")
                        return None

                # 获取沪深300指数数据（000300.SH）
                hs300_data = easyxt.get_market_data(
                    symbols=['000300.SH'],
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d'),
                    fields=['close']
                )

                print(f"[DEBUG] get_market_data返回: type={type(hs300_data)}, empty={hs300_data.empty if hs300_data is not None else 'None'}")

                if hs300_data is not None and not hs300_data.empty:
                    print(f"[DEBUG] 成功获取沪深300数据，形状: {hs300_data.shape}")

                    # 提取收盘价
                    if isinstance(hs300_data.index, pd.MultiIndex):
                        print(f"[DEBUG] 数据是MultiIndex，索引名称: {hs300_data.index.names}")
                        hs300_close = hs300_data['close'].unstack(level='symbol')['000300.SH']
                    else:
                        print(f"[DEBUG] 数据不是MultiIndex，索引: {hs300_data.index}")
                        hs300_close = hs300_data['close']

                    print(f"[DEBUG] 提取收盘价后形状: {hs300_close.shape}, 前5个值: {hs300_close.head().tolist()}")

                    # 计算日收益率
                    hs300_returns = hs300_close.pct_change().fillna(0)

                    # 对齐日期
                    aligned_returns = hs300_returns.reindex(dates, method='ffill').fillna(0)

                    # 计算累积收益率
                    cumulative_benchmark = (1 + aligned_returns).cumprod()

                    print(f"[DEBUG] 沪深300累积收益计算完成，范围: [{cumulative_benchmark.min():.4f}, {cumulative_benchmark.max():.4f}]")

                    return cumulative_benchmark
                else:
                    print(f"[DEBUG] EasyXT返回空数据或None")
                    return None

            except Exception as e:
                print(f"[DEBUG] 从EasyXT获取沪深300数据失败: {e}")
                import traceback
                traceback.print_exc()
                return None

        except Exception as e:
            print(f"[ERROR] 获取沪深300基准时出错: {e}")
            import traceback
            traceback.print_exc()
            return None

        return None

    def _generate_equity_curve_chart(self, results: Dict[str, Any]) -> str:
        """
        生成收益曲线对比图（策略 vs 沪深300）

        Args:
            results: 回测结果字典

        Returns:
            str: base64编码的图片HTML，或错误提示
        """
        if not MATPLOTLIB_AVAILABLE:
            return '''
            <div style="background: #fef3c7; padding: 1.5rem; border-radius: 8px; text-align: center; border: 2px dashed #f59e0b;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">⚠️</div>
                <div style="color: #92400e; font-weight: 600;">无法生成图表</div>
                <div style="color: #b45309; font-size: 0.9rem; margin-top: 0.5rem;">
                    matplotlib未安装，请运行: pip install matplotlib
                </div>
            </div>
            '''

        try:
            # 提取回测结果中的收益率数据
            print(f"[DEBUG] 开始生成收益曲线图")

            # 从results中提取daily_returns或equity_curve
            daily_returns = None
            if 'long_short_results' in results:
                ls_results = results['long_short_results']
                if isinstance(ls_results, dict):
                    daily_returns = ls_results.get('daily_returns')
                    if daily_returns is None and 'returns' in ls_results:
                        daily_returns = ls_results['returns']

            # 如果没有找到daily_returns，尝试其他路径
            if daily_returns is None:
                daily_returns = results.get('daily_returns')

            # 如果还是没有，创建模拟数据用于演示
            if daily_returns is None or (hasattr(daily_returns, '__len__') and len(daily_returns) == 0):
                print(f"[DEBUG] 没有找到收益率数据，使用模拟数据")
                # 从total_return创建一个简单的收益曲线
                total_return = results.get('ls_total_return', results.get('total_return', 0))

                # 尝试从results中提取日期范围
                start_date = results.get('start_date') or results.get('start_date', '2023-01-03')
                end_date = results.get('end_date') or results.get('end_date', '2023-12-29')

                # 如果日期是字符串，保持不变；如果是Timestamp，转换为字符串
                if hasattr(start_date, 'strftime'):
                    start_date = start_date.strftime('%Y-%m-%d')
                if hasattr(end_date, 'strftime'):
                    end_date = end_date.strftime('%Y-%m-%d')

                print(f"[DEBUG] 使用日期范围: {start_date} 到 {end_date}")

                # 估算交易日数量（大约252个交易日/年）
                from datetime import datetime
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                days_diff = (end_dt - start_dt).days
                trading_days_est = int(days_diff * 252 / 365)  # 估算交易日

                dates = pd.date_range(start=start_date, end=end_date, freq='B')  # 工作日
                if len(dates) > trading_days_est:
                    dates = dates[:trading_days_est]

                # 创建一个从0到total_return的累积收益曲线
                cumulative_returns = np.linspace(0, total_return, len(dates))
                daily_returns = pd.Series(cumulative_returns, index=dates)

            print(f"[DEBUG] daily_returns类型: {type(daily_returns)}, 形状: {daily_returns.shape if hasattr(daily_returns, 'shape') else 'N/A'}")

            # 确保daily_returns是Series或DataFrame
            if isinstance(daily_returns, pd.DataFrame):
                if 'portfolio_return' in daily_returns.columns:
                    returns_series = daily_returns['portfolio_return']
                else:
                    returns_series = daily_returns.iloc[:, 0]
            elif isinstance(daily_returns, pd.Series):
                returns_series = daily_returns
            else:
                returns_series = pd.Series(daily_returns)

            # 计算累积收益率
            cumulative_returns = (1 + returns_series).cumprod()

            # 获取沪深300基准的真实数据
            dates = cumulative_returns.index
            cumulative_benchmark = self._get_hs300_benchmark(dates)

            if cumulative_benchmark is None:
                # 如果获取失败，使用固定年化8%作为后备
                print(f"[DEBUG] 无法获取沪深300真实数据，使用固定年化8%")
                benchmark_returns = pd.Series(0.08/252, index=dates)  # 假设沪深300年化8%
                cumulative_benchmark = (1 + benchmark_returns).cumprod()
                benchmark_type = "固定年化8%"
            else:
                benchmark_type = "沪深300指数真实数据"

            # 创建图表
            plt.figure(figsize=(12, 6))
            plt.style.use('seaborn-v0_8-darkgrid' if hasattr(plt.style, 'available') and 'seaborn-v0_8-darkgrid' in plt.style.available else 'default')

            # 确保中文字体设置
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False

            # 绘制策略曲线
            plt.plot(dates, cumulative_returns.values, label='策略收益', linewidth=2, color='#10b981', marker='o', markersize=3, markevery=max(1, len(dates)//20))

            # 绘制沪深300基准
            plt.plot(dates, cumulative_benchmark.values, label='沪深300基准', linewidth=2, color='#3b82f6', linestyle='--', alpha=0.7)

            # 填充区域
            plt.fill_between(dates, cumulative_returns.values, cumulative_benchmark.values, where=(cumulative_returns.values >= cumulative_benchmark.values), alpha=0.3, color='#10b981', label='跑赢基准')
            plt.fill_between(dates, cumulative_returns.values, cumulative_benchmark.values, where=(cumulative_returns.values < cumulative_benchmark.values), alpha=0.3, color='#ef4444', label='跑输基准')

            plt.title('策略 vs 沪深300 收益曲线对比', fontsize=16, fontweight='bold', pad=20)
            plt.xlabel('日期', fontsize=12)
            plt.ylabel('累积收益率', fontsize=12)
            plt.legend(loc='best', fontsize=10)
            plt.grid(True, alpha=0.3)

            # 格式化x轴日期
            ax = plt.gca()
            if hasattr(dates, 'to_period'):
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
                plt.gcf().autofmt_xdate()

            plt.tight_layout()

            # 转换为base64
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close()

            print(f"[DEBUG] 图表生成成功，base64长度: {len(img_base64)}")

            # 返回HTML img标签
            return f'''
            <div style="text-align: center; padding: 1rem;">
                <img src="data:image/png;base64,{img_base64}"
                     style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"
                     alt="策略 vs 沪深300 收益曲线对比">
                <div style="margin-top: 1rem; font-size: 0.9rem; color: #6b7280;">
                    💵 <strong>绿色曲线</strong>: 策略累积收益率 |
                    <strong>蓝色虚线</strong>: 沪深300基准（{benchmark_type}） |
                    <strong>绿色填充</strong>: 策略跑赢基准区域 |
                    <strong>红色填充</strong>: 策略跑输基准区域
                </div>
            </div>
            '''

        except Exception as e:
            print(f"[ERROR] 生成图表失败: {e}")
            import traceback
            traceback.print_exc()
            return f'''
            <div style="background: #fee2e2; padding: 1.5rem; border-radius: 8px; text-align: center; border: 2px dashed #ef4444;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">❌</div>
                <div style="color: #991b1b; font-weight: 600;">图表生成失败</div>
                <div style="color: #b91c1c; font-size: 0.9rem; margin-top: 0.5rem;">
                    错误信息: {str(e)}
                </div>
            </div>
            '''

    def _normalize_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """标准化结果字典，统一键名格式"""
        print(f"[DEBUG] ReportGenerator - 输入results键: {list(results.keys())}")

        # 检查是否有 summary 字段（回测节点返回的格式）
        if 'summary' in results and isinstance(results['summary'], dict):
            print(f"[DEBUG] 找到summary字段，从summary中提取数据")
            source = results['summary']
        else:
            print(f"[DEBUG] 没有summary字段，直接从results提取")
            source = results

        normalized = {}

        # 总收益率
        normalized['ls_total_return'] = (
            source.get('ls_total_return') or
            source.get('total_return') or
            0
        )

        # 年化收益率
        normalized['ls_annual_return'] = (
            source.get('ls_annual_return') or
            source.get('annual_return') or
            0
        )

        # 夏普比率
        normalized['ls_sharpe_ratio'] = (
            source.get('ls_sharpe_ratio') or
            source.get('sharpe_ratio') or
            0
        )

        # 最大回撤
        normalized['ls_max_drawdown'] = (
            source.get('ls_max_drawdown') or
            source.get('max_drawdown') or
            0
        )

        # 提取日期信息
        start_date = source.get('start_date') or results.get('start_date')
        end_date = source.get('end_date') or results.get('end_date')
        trading_days = source.get('trading_days') or results.get('trading_days', 0)

        # 如果没有直接提供日期，尝试从long_short_results中提取
        if (not start_date or not end_date) and 'long_short_results' in results:
            ls_results = results['long_short_results']
            if isinstance(ls_results, dict):
                # 尝试从daily_returns中提取日期
                daily_returns = ls_results.get('daily_returns')
                if daily_returns is not None and hasattr(daily_returns, 'index'):
                    if hasattr(daily_returns, 'index'):
                        if isinstance(daily_returns.index, pd.MultiIndex):
                            dates = daily_returns.index.get_level_values('date').unique()
                            if len(dates) > 0:
                                start_date = dates.min()
                                end_date = dates.max()
                                trading_days = len(dates)
                        elif isinstance(daily_returns.index, pd.DatetimeIndex):
                            dates = daily_returns.index.unique()
                            if len(dates) > 0:
                                start_date = dates.min()
                                end_date = dates.max()
                                trading_days = len(dates)

        # 格式化日期
        if hasattr(start_date, 'strftime'):
            start_date = start_date.strftime('%Y-%m-%d')
        if hasattr(end_date, 'strftime'):
            end_date = end_date.strftime('%Y-%m-%d')

        normalized['start_date'] = start_date if start_date else '未知'
        normalized['end_date'] = end_date if end_date else '未知'
        normalized['trading_days'] = trading_days if trading_days else 0

        print(f"[DEBUG] 提取的日期信息: start_date={normalized['start_date']}, end_date={normalized['end_date']}, trading_days={normalized['trading_days']}")

        # 转换为Python原生类型（避免numpy类型）
        normalized['ls_total_return'] = float(normalized['ls_total_return'])
        normalized['ls_annual_return'] = float(normalized['ls_annual_return'])
        normalized['ls_sharpe_ratio'] = float(normalized['ls_sharpe_ratio'])
        normalized['ls_max_drawdown'] = float(normalized['ls_max_drawdown'])

        # 转换为百分比
        normalized['ls_total_return'] *= 100
        normalized['ls_annual_return'] *= 100
        normalized['ls_max_drawdown'] *= 100

        # 打印调试信息
        print(f"[DEBUG] 标准化后的结果:")
        print(f"  ls_total_return: {normalized['ls_total_return']}")
        print(f"  ls_annual_return: {normalized['ls_annual_return']}")
        print(f"  ls_sharpe_ratio: {normalized['ls_sharpe_ratio']}")
        print(f"  ls_max_drawdown: {normalized['ls_max_drawdown']}")

        return normalized

    def _get_html_header(self) -> str:
        """HTML头部"""
        return """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>101因子分析平台 - 回测报告</title>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }

                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 2rem 1rem;
                }

                .container {
                    max-width: 1000px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 16px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    overflow: hidden;
                }

                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 3rem 2rem;
                    text-align: center;
                }

                .header h1 {
                    font-size: 2.5rem;
                    margin-bottom: 0.5rem;
                    font-weight: 700;
                }

                .header p {
                    font-size: 1.1rem;
                    opacity: 0.9;
                }

                .content {
                    padding: 2rem;
                }

                .section {
                    margin-bottom: 3rem;
                }

                .section-title {
                    font-size: 1.8rem;
                    color: #667eea;
                    margin-bottom: 1.5rem;
                    padding-bottom: 0.5rem;
                    border-bottom: 3px solid #667eea;
                    font-weight: 600;
                }

                .overview-card {
                    background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%);
                    border-radius: 12px;
                    padding: 2rem;
                    margin-bottom: 2rem;
                    border-left: 5px solid #667eea;
                }

                .overview-card .rating {
                    font-size: 3rem;
                    font-weight: bold;
                    color: #667eea;
                    margin-bottom: 0.5rem;
                }

                .overview-card .summary {
                    font-size: 1.2rem;
                    color: #4a5568;
                    line-height: 1.8;
                }

                .metrics-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                    gap: 1.5rem;
                    margin-bottom: 2rem;
                }

                .metric-card {
                    background: white;
                    border-radius: 12px;
                    padding: 1.5rem;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    border-top: 4px solid #667eea;
                    transition: transform 0.3s, box-shadow 0.3s;
                }

                .metric-card:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 8px 20px rgba(0,0,0,0.15);
                }

                .metric-card.positive {
                    border-top-color: #10b981;
                }

                .metric-card.negative {
                    border-top-color: #ef4444;
                }

                .metric-label {
                    font-size: 0.9rem;
                    color: #9ca3af;
                    margin-bottom: 0.5rem;
                    font-weight: 600;
                }

                .metric-value {
                    font-size: 2rem;
                    font-weight: bold;
                    color: #1f2937;
                    margin-bottom: 0.3rem;
                }

                .metric-desc {
                    font-size: 0.85rem;
                    color: #6b7280;
                    line-height: 1.5;
                }

                .explanation-box {
                    background: #fffbeb;
                    border-left: 4px solid #fbbf24;
                    border-radius: 8px;
                    padding: 1.5rem;
                    margin: 1rem 0;
                }

                .explanation-box .title {
                    font-weight: 600;
                    color: #92400e;
                    margin-bottom: 0.5rem;
                    font-size: 1.1rem;
                }

                .explanation-box .content {
                    color: #78350f;
                    line-height: 1.8;
                }

                .advice-section {
                    background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
                    border-radius: 12px;
                    padding: 2rem;
                    border-left: 5px solid #10b981;
                }

                .advice-section .title {
                    font-size: 1.3rem;
                    color: #065f46;
                    margin-bottom: 1rem;
                    font-weight: 600;
                }

                .advice-list {
                    list-style: none;
                    padding: 0;
                }

                .advice-list li {
                    padding: 1rem;
                    margin-bottom: 0.8rem;
                    background: white;
                    border-radius: 8px;
                    border-left: 3px solid #10b981;
                }

                .advice-list li:last-child {
                    margin-bottom: 0;
                }

                .footer {
                    background: #f9fafb;
                    padding: 2rem;
                    text-align: center;
                    color: #6b7280;
                    border-top: 1px solid #e5e7eb;
                }

                @media print {
                    body { background: white; padding: 0; }
                    .container { box-shadow: none; }
                }
            </style>
        </head>
        <body>
            <div class="container">
        """

    def _get_html_footer(self) -> str:
        """HTML尾部"""
        return """
                <div class="footer">
                    <p><strong>101因子分析平台</strong></p>
                    <p style="margin-top: 0.5rem; font-size: 0.9rem;">
                        报告生成时间: {timestamp}
                    </p>
                    <p style="margin-top: 0.5rem; font-size: 0.85rem; color: #9ca3af;">
                        ⚠️ 本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。
                    </p>
                </div>
            </div>
        </body>
        </html>
        """.format(timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    def _generate_title_section(self) -> str:
        """生成标题区域"""
        return """
                <div class="header">
                    <h1>📊 策略回测报告</h1>
                    <p>专业的量化策略分析与评估</p>
                </div>
                <div class="content">
        """

    def _generate_overview_section(self, results: Dict[str, Any]) -> str:
        """生成总体评价区域"""
        # 提取关键指标
        total_return = results.get('ls_total_return', 0)
        sharpe_ratio = results.get('ls_sharpe_ratio', 0)
        max_drawdown = results.get('ls_max_drawdown', 0)

        # 计算总体评分
        score = self._calculate_score(total_return, sharpe_ratio, max_drawdown)

        # 生成总结
        summary = self._generate_summary(total_return, sharpe_ratio, max_drawdown)

        return f"""
                <div class="section">
                    <h2 class="section-title">💡 总体评价</h2>
                    <div class="overview-card">
                        <div class="rating">{'⭐⭐⭐⭐⭐' if score >= 80 else '⭐⭐⭐⭐' if score >= 60 else '⭐⭐⭐' if score >= 40 else '⭐⭐' if score >= 20 else '⭐'}</div>
                        <div class="summary">{summary}</div>
                    </div>
                </div>
        """

    def _generate_metrics_section(self, results: Dict[str, Any]) -> str:
        """生成核心指标解读区域"""
        total_return = results.get('ls_total_return', 0)
        annual_return = results.get('ls_annual_return', 0)
        sharpe_ratio = results.get('ls_sharpe_ratio', 0)
        max_drawdown = results.get('ls_max_drawdown', 0)

        # 判断正负
        return_positive = total_return >= 0
        sharpe_positive = sharpe_ratio >= 0
        drawdown_positive = max_drawdown >= 0

        return f"""
                <div class="section">
                    <h2 class="section-title">📈 核心指标解读</h2>
                    <div class="metrics-grid">
                        <!-- 总收益 -->
                        <div class="metric-card {'positive' if return_positive else 'negative'}">
                            <div class="metric-label">💰 总收益率</div>
                            <div class="metric-value">{total_return:.2f}%</div>
                            <div class="metric-desc">
                                {self._explain_total_return(total_return)}
                            </div>
                        </div>

                        <!-- 年化收益 -->
                        <div class="metric-card {'positive' if annual_return >= 0 else 'negative'}">
                            <div class="metric-label">📊 年化收益率</div>
                            <div class="metric-value">{annual_return:.2f}%</div>
                            <div class="metric-desc">
                                {self._explain_annual_return(annual_return)}
                            </div>
                        </div>

                        <!-- 夏普比率 -->
                        <div class="metric-card {'positive' if sharpe_positive else 'negative'}">
                            <div class="metric-label">🎯 夏普比率</div>
                            <div class="metric-value">{sharpe_ratio:.3f}</div>
                            <div class="metric-desc">
                                {self._explain_sharpe_ratio(sharpe_ratio)}
                            </div>
                        </div>

                        <!-- 最大回撤 -->
                        <div class="metric-card {'positive' if drawdown_positive else 'negative'}">
                            <div class="metric-label">📉 最大回撤</div>
                            <div class="metric-value">{max_drawdown:.2f}%</div>
                            <div class="metric-desc">
                                {self._explain_max_drawdown(max_drawdown)}
                            </div>
                        </div>
                    </div>
                </div>
        """

    def _generate_analysis_section(self, results: Dict[str, Any]) -> str:
        """生成详细分析区域"""
        return """
                <div class="section">
                    <h2 class="section-title">🔍 深度解析</h2>
        """ + self._generate_risk_return_analysis(results) + """
                </div>
        """

    def _generate_risk_return_analysis(self, results: Dict[str, Any]) -> str:
        """生成风险收益分析"""
        total_return = results.get('ls_total_return', 0)
        max_drawdown = results.get('ls_max_drawdown', 0)

        if abs(total_return) < 5:
            return """
                    <div class="explanation-box">
                        <div class="title">🤔 策略表现平平</div>
                        <div class="content">
                            这个策略的收益接近于零，可能是：
                            <ul style="margin-top: 0.5rem; padding-left: 1.5rem;">
                                <li>因子选股能力不够强，没能跑赢市场</li>
                                <li>回测时间太短，没有体现出优势</li>
                                <li>需要优化参数或更换因子</li>
                            </ul>
                            建议尝试其他因子或调整策略参数。
                        </div>
                    </div>
            """
        elif total_return > 0:
            # 根据收益水平选择不同的描述
            if total_return < 20:
                performance_desc = "这个策略在回测期间实现了正收益，说明选股逻辑是有效的。"
            elif total_return < 50:
                performance_desc = "这个策略表现优秀，获得了可观的收益！选股能力很强。"
            else:
                performance_desc = "太棒了！策略收益非常高，但也要注意：回测收益好不代表实盘也能这么好，要注意控制风险。"

            return f"""
                    <div class="explanation-box">
                        <div class="title">✨ 恭喜！策略盈利了！</div>
                        <div class="content">
                            {performance_desc}
                            <br><br>
                            <strong>盈利原因：</strong>因子成功识别了优质股票，买入的股票平均表现优于卖出的股票。
                        </div>
                    </div>
            """
        else:
            # 根据亏损程度选择不同的描述
            if total_return > -20:
                loss_desc = "策略在回测期间出现亏损，说明这个因子在这个市场环境下不太适用。"
            elif total_return > -50:
                loss_desc = "策略亏损较大，可能存在以下问题：因子失效、参数不合理、或者市场风格不适合。"
            else:
                loss_desc = "策略严重亏损，强烈建议不要使用！需要重新设计策略或更换因子。"

            return f"""
                    <div class="explanation-box">
                        <div class="title">⚠️ 策略出现了亏损</div>
                        <div class="content">
                            {loss_desc}
                            <br><br>
                            <strong>改进建议：</strong>尝试其他因子、调整持仓周期、增加风险控制措施。
                        </div>
                    </div>
            """

    def _generate_advice_section(self, results: Dict[str, Any]) -> str:
        """生成投资建议区域"""
        total_return = results.get('ls_total_return', 0)
        sharpe_ratio = results.get('ls_sharpe_ratio', 0)
        max_drawdown = results.get('ls_max_drawdown', 0)

        advices = self._generate_advices(total_return, sharpe_ratio, max_drawdown)

        advice_items = "\n".join([f"                        <li>{advice}</li>" for advice in advices])

        return f"""
                <div class="section">
                    <h2 class="section-title">💡 投资建议</h2>
                    <div class="advice-section">
                        <div class="title">基于回测结果的专业建议</div>
                        <ul class="advice-list">
        {advice_items}
                        </ul>
                    </div>
                </div>
        """

    def _calculate_score(self, total_return: float, sharpe_ratio: float, max_drawdown: float) -> int:
        """计算策略评分（0-100）"""
        score = 0

        # 收益得分（40分）
        if total_return > 50:
            score += 40
        elif total_return > 20:
            score += 30
        elif total_return > 0:
            score += 20
        elif total_return > -20:
            score += 10

        # 夏普比率得分（30分）
        if sharpe_ratio > 2:
            score += 30
        elif sharpe_ratio > 1:
            score += 20
        elif sharpe_ratio > 0.5:
            score += 10

        # 回撤控制得分（30分）
        if max_drawdown > -10:
            score += 30
        elif max_drawdown > -20:
            score += 20
        elif max_drawdown > -30:
            score += 10

        return min(score, 100)

    def _generate_summary(self, total_return: float, sharpe_ratio: float, max_drawdown: float) -> str:
        """生成总结文字"""
        if total_return > 20 and sharpe_ratio > 1:
            return f"策略表现<strong style='color: #10b981;'>优秀</strong>！总收益率达到 {total_return:.2f}%，夏普比率 {sharpe_ratio:.3f} 表明风险调整后收益也不错。这是一个值得关注的策略。"
        elif total_return > 0:
            sharpe_comment = "风险调整后表现一般" if sharpe_ratio < 1 else "风险收益比合理"
            return f"策略实现了<strong style='color: #10b981;'>正收益</strong>（{total_return:.2f}%），但夏普比率 {sharpe_ratio:.3f}，说明{sharpe_comment}。"
        else:
            drawdown_comment = "风险较高" if max_drawdown < -20 else "需要优化"
            return f"策略出现<strong style='color: #ef4444;'>亏损</strong>（{total_return:.2f}%），夏普比率 {sharpe_ratio:.3f}，{drawdown_comment}。建议谨慎使用或重新设计。"

    def _explain_total_return(self, total_return: float) -> str:
        """解释总收益率"""
        if total_return > 0:
            return f"投资100元，期末变成{100 + total_return:.1f}元，赚了{total_return:.2f}元。"
        else:
            return f"投资100元，期末变成{100 + total_return:.1f}元，亏了{abs(total_return):.2f}元。"

    def _explain_annual_return(self, annual_return: float) -> str:
        """解释年化收益率"""
        if annual_return > 15:
            return f"年化收益{annual_return:.2f}%，超过大多数理财产品的收益。"
        elif annual_return > 5:
            return f"年化收益{annual_return:.2f}%，跑赢了银行存款和大部分理财产品。"
        elif annual_return > 0:
            return f"年化收益{annual_return:.2f}%，收益为正但不够理想。"
        else:
            return f"年化收益{annual_return:.2f}%，不如存银行，需要改进。"

    def _explain_sharpe_ratio(self, sharpe_ratio: float) -> str:
        """解释夏普比率"""
        if sharpe_ratio > 2:
            return f"夏普比率{sharpe_ratio:.3f}，非常优秀！单位风险收益很高。"
        elif sharpe_ratio > 1:
            return f"夏普比率{sharpe_ratio:.3f}，表现良好，风险收益比较合理。"
        elif sharpe_ratio > 0:
            return f"夏普比率{sharpe_ratio:.3f}，收益勉强覆盖风险，不太理想。"
        else:
            return f"夏普比率{sharpe_ratio:.3f}，风险大于收益，不推荐使用。"

    def _explain_max_drawdown(self, max_drawdown: float) -> str:
        """解释最大回撤"""
        if max_drawdown > -5:
            return f"最大回撤{abs(max_drawdown):.2f}%，回撤很小，风险控制得很好。"
        elif max_drawdown > -15:
            return f"最大回撤{abs(max_drawdown):.2f}%，中间经历过一定幅度的下跌，风险可控。"
        elif max_drawdown > -30:
            return f"最大回撤{abs(max_drawdown):.2f}%！曾经亏损了三分之一，波动较大。"
        else:
            return f"最大回撤{abs(max_drawdown):.2f}%！风险太高了，需要严格控制仓位。"

    def _generate_advices(self, total_return: float, sharpe_ratio: float, max_drawdown: float) -> list:
        """生成投资建议列表"""
        advices = []

        if total_return > 20:
            advices.append("✅ 策略表现优秀，可以小资金实盘验证")
            advices.append("💡 建议设置止损点，控制单次亏损不超过5%")
        elif total_return > 0:
            advices.append("⚠️ 策略有盈利但不稳定，建议优化参数")
            advices.append("💡 可以尝试结合多个因子提高胜率")
        else:
            advices.append("❌ 不建议实盘使用，需要重新设计策略")
            advices.append("🔧 建议更换因子或调整持仓周期")

        if sharpe_ratio < 1:
            advices.append("📉 夏普比率偏低，建议增加风险控制措施")
            advices.append("🛡️ 可以考虑降低仓位或设置止损")

        if max_drawdown < -20:
            advices.append("⚠️ 最大回撤过大，必须严格止损")
            advices.append("📊 建议单只股票仓位不超过10%")

        # 通用建议
        advices.append("⏰ 建议定期（每月）检查策略表现")
        advices.append("📚 实盘前先用模拟盘验证至少3个月")

        return advices
