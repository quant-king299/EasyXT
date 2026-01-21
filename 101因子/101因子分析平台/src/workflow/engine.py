"""
工作流引擎模块
实现可视化因子构建和策略编排功能
"""
import json
import uuid
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
import sys
import os

# 添加项目路径
project_path = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_path)


@dataclass
class Node:
    """工作流节点基类"""
    id: str
    node_type: str
    position: Dict[str, float]
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    data: Any = None


class WorkflowEngine:
    """
    工作流引擎
    支持可视化节点式因子构建和策略编排
    """
    
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.connections: List[Dict[str, str]] = []
        self.execution_order: List[str] = []
    
    def add_node(self, node_type: str, position: Dict[str, float], params: Optional[Dict[str, Any]] = None) -> str:
        """
        添加节点到工作流
        
        Args:
            node_type: 节点类型
            position: 节点位置 {'x': float, 'y': float}
            params: 节点参数
            
        Returns:
            str: 节点ID
        """
        if params is None:
            params = {}
        node_id = str(uuid.uuid4())
        node = Node(
            id=node_id,
            node_type=node_type,
            position=position,
            params=params,
            inputs=[],
            outputs=[]
        )
        self.nodes[node_id] = node
        return node_id
    
    def connect_nodes(self, from_node: str, to_node: str, from_output: str = "", to_input: str = ""):
        """
        连接两个节点
        
        Args:
            from_node: 源节点ID
            to_node: 目标节点ID
            from_output: 源输出端口
            to_input: 目标输入端口
        """
        connection = {
            'from_node': from_node,
            'to_node': to_node,
            'from_output': from_output,
            'to_input': to_input
        }
        self.connections.append(connection)
        
        # 更新节点的输入输出信息
        if from_node in self.nodes:
            if from_output not in self.nodes[from_node].outputs:
                self.nodes[from_node].outputs.append(from_output)
        if to_node in self.nodes:
            if to_input not in self.nodes[to_node].inputs:
                self.nodes[to_node].inputs.append(to_input)
    
    def auto_connect_nodes(self):
        """
        自动根据节点类型推断连接关系

        按照常见的因子分析流程自动连接节点：
        数据加载 → 因子计算 → 分析/回测
        """
        # 如果已有连接，不覆盖
        if self.connections:
            return

        # 定义节点执行优先级（数字越小越先执行）
        priority = {
            'data_loader': 1,
            'data_processor': 2,
            'factor_calculator': 3,
            'ic_analyzer': 4,
            'factor_correlation': 5,
            'signal_generator': 6,
            'backtester': 7,
            'performance_analyzer': 8,
            'portfolio_optimizer': 9,
            'risk_manager': 10
        }

        # 按优先级排序节点
        sorted_nodes = sorted(
            self.nodes.items(),
            key=lambda x: priority.get(x[1].node_type, 999)
        )

        # 自动连接相邻的节点
        for i in range(len(sorted_nodes) - 1):
            from_id, from_node = sorted_nodes[i]
            to_id, to_node = sorted_nodes[i + 1]

            # 根据节点类型推断端口
            output_port = self._infer_output_port(from_node.node_type)
            input_port = self._infer_input_port(to_node.node_type)

            self.connect_nodes(from_id, to_id, output_port, input_port)

        print(f"[DEBUG] 自动连接了 {len(self.connections)} 个节点")

    def _infer_output_port(self, node_type: str) -> str:
        """推断节点的输出端口"""
        port_map = {
            'data_loader': 'data',
            'data_processor': 'processed_data',
            'factor_calculator': 'factor_data',
            'ic_analyzer': 'ic_series',
            'signal_generator': 'signals',
            'backtester': 'returns',
            'performance_analyzer': 'metrics'
        }
        return port_map.get(node_type, 'output')

    def _infer_input_port(self, node_type: str) -> str:
        """推断节点的输入端口"""
        port_map = {
            'data_processor': 'data',
            'factor_calculator': 'price_data',
            'ic_analyzer': 'factor_data',
            'factor_correlation': 'factor_data',
            'signal_generator': 'factor_data',
            'backtester': 'factor_data',
            'performance_analyzer': 'returns_data',
            'portfolio_optimizer': 'signals'
        }
        return port_map.get(node_type, 'input')

    def execute_workflow(self) -> Dict[str, Any]:
        """
        执行工作流

        Returns:
            Dict: 执行结果
        """
        # 自动修复数据加载节点的空 symbols 参数
        self._fix_data_loader_symbols()

        # 自动连接节点（如果没有连接的话）
        self.auto_connect_nodes()

        # 计算执行顺序
        self.execution_order = self._topological_sort()

        results = {}

        for node_id in self.execution_order:
            node = self.nodes[node_id]
            try:
                result = self._execute_node(node, results)
                results[node_id] = result
                node.data = result
            except Exception as e:
                print(f"执行节点 {node_id} ({node.node_type}) 时出错: {e}")
                results[node_id] = None

        return results

    def _fix_data_loader_symbols(self):
        """自动修复数据加载节点的空 symbols 参数"""
        for node_id, node in self.nodes.items():
            if node.node_type == 'data_loader':
                symbols = node.params.get('symbols', [])
                if not symbols or (isinstance(symbols, list) and len(symbols) == 0):
                    print(f"[DEBUG] 修复节点 {node_id[:8]} 的空 symbols 参数")
                    # 使用默认股票代码
                    node.params['symbols'] = ['000001.SZ', '000002.SZ', '600000.SH']
                    print(f"[DEBUG] 已设置默认 symbols: {node.params['symbols']}")
    
    def _topological_sort(self) -> List[str]:
        """拓扑排序，确定节点执行顺序"""
        in_degree = {node_id: 0 for node_id in self.nodes}
        
        # 计算每个节点的入度
        for conn in self.connections:
            in_degree[conn['to_node']] += 1
        
        # 拓扑排序
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        order = []
        
        while queue:
            node_id = queue.pop(0)
            order.append(node_id)
            
            # 查找从此节点出发的连接
            for conn in self.connections:
                if conn['from_node'] == node_id:
                    in_degree[conn['to_node']] -= 1
                    if in_degree[conn['to_node']] == 0:
                        queue.append(conn['to_node'])
        
        # 检查是否有循环依赖
        if len(order) != len(self.nodes):
            raise ValueError("工作流中存在循环依赖")
        
        return order
    
    def _execute_node(self, node: Node, results: Dict[str, Any]) -> Any:
        """执行单个节点"""
        node_executor = self._get_node_executor(node.node_type)
        if node_executor:
            return node_executor(node.params, results)
        else:
            raise ValueError(f"未知的节点类型: {node.node_type}")
    
    def _get_node_executor(self, node_type: str) -> Optional[Callable]:
        """获取节点执行器"""
        executors = {
            'data_loader': self._execute_data_loader,
            'factor_calculator': self._execute_factor_calculator,
            'ic_analyzer': self._execute_ic_analyzer,
            'backtester': self._execute_backtester,
            'performance_analyzer': self._execute_performance_analyzer,
            'data_processor': self._execute_data_processor,
            'signal_generator': self._execute_signal_generator,
            'portfolio_optimizer': self._execute_portfolio_optimizer,
            'risk_manager': self._execute_risk_manager,
            'factor_correlation': self._execute_factor_correlation,  # 新增
        }
        return executors.get(node_type)
    
    def _execute_data_loader(self, params: Dict[str, Any], results: Dict[str, Any]) -> pd.DataFrame:
        """执行数据加载节点"""
        from src.easyxt_adapter.data_loader import EasyXTDataLoader
        
        symbols = params.get('symbols', [])
        start_date = params.get('start_date', '2023-01-01')
        end_date = params.get('end_date', '2023-12-31')
        fields = params.get('fields', ['open', 'high', 'low', 'close', 'volume'])
        
        print(f"WorkflowEngine - 数据加载节点参数: symbols={symbols}, start_date={start_date}, end_date={end_date}, fields={fields}")
        
        loader = EasyXTDataLoader()
        data = loader.get_historical_data(symbols, start_date, end_date, fields)

        # 添加数据加载后的验证
        print(f"WorkflowEngine - 加载数据后形状: {data.shape}")
        print(f"WorkflowEngine - 数据索引类型: {type(data.index)}, 索引名称: {data.index.names if hasattr(data.index, 'names') else 'N/A'}")

        # 检查 symbol 列的实际内容
        if hasattr(data.index, 'get_level_values'):
            symbols_in_data = data.index.get_level_values('symbol').unique().tolist()
            print(f"WorkflowEngine - 数据中的 symbol (前10个): {symbols_in_data[:10]}")
            # 检查是否有单字符 symbol
            single_chars = [s for s in symbols_in_data if len(str(s)) == 1]
            if single_chars:
                print(f"WorkflowEngine - 警告: 发现单字符 symbol: {single_chars[:10]}")
        print(f"WorkflowEngine - 加载数据后列: {list(data.columns)}")
        if isinstance(data.index, pd.MultiIndex):
            print(f"WorkflowEngine - 加载数据后索引名称: {data.index.names}")
            unique_symbols = data.index.get_level_values('symbol').unique().tolist()[:10]
            print(f"WorkflowEngine - 加载数据后symbol级别唯一值: {unique_symbols}")
            
            # 检查是否出现单字符问题
            for sym in unique_symbols:
                if len(str(sym)) == 1:
                    print(f"警告: WorkflowEngine - 发现单字符symbol: '{sym}' in {unique_symbols}")
        
        return data
    
    def _execute_factor_calculator(self, params: Dict[str, Any], results: Dict[str, Any]) -> pd.Series:
        """执行因子计算节点"""
        from src.factor_engine.calculator import FactorCalculator
        
        factor_name = params.get('factor_name', 'alpha001')
        data = self._get_input_data(params, results)
        
        if data is not None:
            calculator = FactorCalculator()
            try:
                print(f"[DEBUG] _execute_factor_calculator - 输入数据类型: {type(data)}, 形状: {data.shape}, 索引名称: {data.index.names if hasattr(data.index, 'names') else 'N/A'}")
                factor_data = calculator.calculate_single_factor(data, factor_name)

                print(f"[DEBUG] _execute_factor_calculator - calculate_single_factor 返回: type={type(factor_data)}, 形状: {factor_data.shape if hasattr(factor_data, 'shape') else 'N/A'}, 索引类型: {type(factor_data.index)}, 索引名称: {factor_data.index.names if hasattr(factor_data.index, 'names') else 'N/A'}")

                # 确保返回有效的Series
                if factor_data is None:
                    print(f"警告: 因子 {factor_name} 计算返回了None")
                    # 返回一个空的Series，但保持相同的索引
                    return pd.Series(index=data.index, dtype=float, name=factor_name)
                elif isinstance(factor_data, pd.DataFrame):
                    # 如果返回的是DataFrame，需要确保正确转换为Series
                    if not factor_data.empty:
                        # 如果DataFrame有且仅有一列，直接转换为Series
                        if len(factor_data.columns) == 1:
                            result_series = factor_data.iloc[:, 0]
                            result_series.name = factor_name
                            return result_series  # 直接返回，不要重新包装
                        else:
                            # 如果有多列，使用stack方法将DataFrame转换为MultiIndex Series
                            print(f"WorkflowEngine - stacking DataFrame with columns: {factor_data.columns.tolist()[:10]}")  # 调试信息

                            result_series = factor_data.stack()

                            # 检查stack后的索引情况
                            if isinstance(result_series.index, pd.MultiIndex):
                                print(f"WorkflowEngine - after stacking, index names: {result_series.index.names}")
                                print(f"WorkflowEngine - after stacking, symbol level unique values: {result_series.index.get_level_values(1).unique().tolist()[:10] if len(result_series.index.names) > 1 else 'N/A'}")

                                # 确保MultiIndex的名称正确
                                if len(result_series.index.names) >= 2:
                                    # 检查当前的索引名称是否正确
                                    if result_series.index.names[0] != 'date' or result_series.index.names[1] != 'symbol':
                                        # 如果顺序不对，重新设置
                                        result_series.index.names = ['date', 'symbol']
                                else:
                                    # 如果索引名字不够，设置默认名字
                                    result_series.index.names = ['date', 'symbol']
                            result_series.name = factor_name
                            return result_series  # 直接返回，不要重新包装
                    else:
                        return pd.Series(index=data.index, dtype=float, name=factor_name)
                elif isinstance(factor_data, pd.Series):
                    # 如果已经是Series，直接返回
                    if factor_data.name is None or factor_data.name == factor_data.index.name:
                        factor_data.name = factor_name
                    return factor_data
                else:
                    # 如果是其他类型，创建Series
                    return pd.Series(factor_data, index=data.index, name=factor_name)
            except Exception as e:
                print(f"计算因子 {factor_name} 时出错: {e}")
                import traceback
                traceback.print_exc()
                # 返回一个空的Series，但保持相同的索引
                return pd.Series(index=data.index, dtype=float, name=factor_name)
        else:
            raise ValueError("因子计算节点缺少输入数据")
    
    def _execute_ic_analyzer(self, params: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """执行IC分析节点"""
        from src.analysis.ic_analysis import ICAnalysis
        
        # 从上游节点获取因子数据
        factor_data = self._get_input_data(params, results, 'factor_data')
        
        # 如果没有直接获取到因子数据，尝试从最近的因子计算结果中获取
        if factor_data is None or (hasattr(factor_data, 'empty') and factor_data.empty):
            # 遍历已执行的结果，寻找因子数据
            for node_id in reversed(self.execution_order):
                if node_id in results and results[node_id] is not None:
                    result = results[node_id]
                    if isinstance(result, pd.Series) and not result.empty:
                        # 检查是否是因子数据（通常包含日期和股票的多级索引）
                        if isinstance(result.index, pd.MultiIndex) and 'date' in result.index.names:
                            factor_data = result
                            break
                    elif isinstance(result, pd.DataFrame) and not result.empty:
                        # 如果DataFrame有因子相关的列
                        factor_data = result
                        break
                    elif isinstance(result, dict):
                        # 如果是字典，尝试从中提取因子数据
                        if 'factor_data' in result and result['factor_data'] is not None:
                            factor_data = result['factor_data']
                            break
                        elif 'ic_series' in result and result['ic_series'] is not None:
                            factor_data = result['ic_series']
                            break
                        else:
                            # 尝试获取字典中的第一个Series
                            for key, value in result.items():
                                if isinstance(value, pd.Series) and not value.empty:
                                    factor_data = value
                                    break
        
        # 获取收益率数据 - 优先尝试从上游节点获取
        returns_data = self._get_input_data(params, results, 'returns_data')
        
        # 如果没有直接获取到收益率数据，尝试从数据加载节点获取并计算收益率
        if returns_data is None or (hasattr(returns_data, 'empty') and returns_data.empty):
            # 尝试从数据加载节点的结果中获取价格数据并计算收益率
            for node_id in reversed(self.execution_order):
                if node_id in results and results[node_id] is not None:
                    result = results[node_id]
                    if isinstance(result, pd.DataFrame) and not result.empty:
                        # 检查是否是价格数据（包含close列）
                        if 'close' in result.columns:
                            try:
                                # 按股票分组计算收益率
                                returns_data = result.groupby(level=1)['close'].pct_change()
                                break
                            except:
                                pass
                    elif isinstance(result, dict):
                        # 如果结果是字典，检查是否包含价格数据
                        if 'price_data' in result and result['price_data'] is not None:
                            price_data = result['price_data']
                            if isinstance(price_data, pd.DataFrame) and 'close' in price_data.columns:
                                try:
                                    returns_data = price_data.groupby(level=1)['close'].pct_change()
                                    break
                                except:
                                    pass
                        elif 'returns' in result and result['returns'] is not None:
                            returns_data = result['returns']
                            break
        
        # 如果仍然没有收益率数据，尝试从因子数据的同源数据计算
        if (returns_data is None or (hasattr(returns_data, 'empty') and returns_data.empty)) and factor_data is not None:
            # 尝试找到与因子数据同期的价格数据来计算收益率
            # 遍历所有已执行结果寻找价格数据
            for node_id in reversed(self.execution_order):
                if node_id in results and results[node_id] is not None:
                    result = results[node_id]
                    if isinstance(result, pd.DataFrame) and not result.empty:
                        # 检查是否是包含价格信息的DataFrame
                        if 'close' in result.columns:
                            try:
                                # 限制价格数据的时间范围与因子数据匹配
                                factor_dates = factor_data.index.get_level_values('date').unique()
                                filtered_price_data = result[result.index.get_level_values('date').isin(factor_dates)]
                                if not filtered_price_data.empty:
                                    returns_data = filtered_price_data.groupby(level=1)['close'].pct_change()
                                    break
                            except:
                                pass
        
        if factor_data is not None and hasattr(factor_data, 'empty') and not factor_data.empty and \
           returns_data is not None and hasattr(returns_data, 'empty') and not returns_data.empty:
            
            analyzer = ICAnalysis()
            try:
                # 确保factor_data和returns_data是Series类型且格式正确
                if isinstance(factor_data, pd.DataFrame):
                    # 如果是DataFrame，取第一个数值列
                    numeric_cols = factor_data.select_dtypes(include=[np.number]).columns
                    if len(numeric_cols) > 0:
                        factor_data = factor_data[numeric_cols[0]]
                    else:
                        # 如果没有数值列，转换为Series
                        factor_data = pd.Series(index=factor_data.index, dtype=float)
                
                if isinstance(returns_data, pd.DataFrame):
                    # 如果是DataFrame，取close列或其他价格列
                    if 'close' in returns_data.columns:
                        returns_data = returns_data['close']
                    elif 'return' in returns_data.columns:
                        returns_data = returns_data['return']
                    elif 'returns' in returns_data.columns:
                        returns_data = returns_data['returns']
                    else:
                        # 取第一个数值列
                        numeric_cols = returns_data.select_dtypes(include=[np.number]).columns
                        if len(numeric_cols) > 0:
                            returns_data = returns_data[numeric_cols[0]]
                        else:
                            returns_data = pd.Series(index=returns_data.index, dtype=float)
                
                # 特别处理MultiIndex数据，确保因子数据和收益率数据的索引一致
                if isinstance(factor_data.index, pd.MultiIndex) and isinstance(returns_data.index, pd.MultiIndex):
                    # 对于MultiIndex，确保索引层级一致
                    if factor_data.index.equals(returns_data.index):
                        # 索引完全相同，可以直接使用
                        pass
                    else:
                        # 索引不完全相同，需要对齐
                        factor_data, returns_data = factor_data.align(returns_data, join='inner')
                
                ic_series = analyzer.calculate_ic(factor_data, returns_data)  # type: ignore
                ic_stats = analyzer.calculate_ic_stats(ic_series)
                
                return {
                    'ic_series': ic_series,
                    'ic_stats': ic_stats,
                    'summary': {
                        'ic_mean': ic_stats['ic_mean'],
                        'ic_ir': ic_stats['ic_ir'],
                        'ic_prob': ic_stats['ic_prob']
                    }
                }
            except Exception as e:
                print(f"IC分析执行出错: {e}")
                import traceback
                traceback.print_exc()
                # 返回默认值
                return {
                    'ic_series': pd.Series(dtype=float),
                    'ic_stats': {
                        'ic_mean': 0.0,
                        'ic_std': 0.0,
                        'ic_ir': 0.0,
                        'ic_prob': 0.0,
                        'ic_abs_mean': 0.0,
                        't_stat': 0.0,
                        'p_value': 1.0
                    },
                    'summary': {
                        'ic_mean': 0.0,
                        'ic_ir': 0.0,
                        'ic_prob': 0.0
                    }
                }
        else:
            print(f"IC分析节点数据不足: factor_data is None: {factor_data is None}, returns_data is None: {returns_data is None}")
            if factor_data is not None:
                print(f"factor_data type: {type(factor_data)}, empty: {factor_data.empty if hasattr(factor_data, 'empty') else 'N/A'}, index: {factor_data.index.names if hasattr(factor_data, 'index') else 'N/A'}")
            if returns_data is not None:
                print(f"returns_data type: {type(returns_data)}, empty: {returns_data.empty if hasattr(returns_data, 'empty') else 'N/A'}, index: {returns_data.index.names if hasattr(returns_data, 'index') else 'N/A'}")
            
            # 尝试提供更多信息
            print("已执行的结果节点:")
            for node_id in self.execution_order:
                if node_id in results:
                    result = results[node_id]
                    print(f"  - {node_id}: {type(result)}, empty: {hasattr(result, 'empty') and result.empty if result is not None else 'N/A'}")
            
            raise ValueError("IC分析节点缺少因子数据或收益率数据")
    
    def _calculate_stock_weights(self, stocks: List[str], factor_values: pd.Series,
                                  weight_method: str, n_stocks: Optional[int] = None) -> Dict[str, float]:
        """
        计算股票权重

        Args:
            stocks: 股票代码列表
            factor_values: 因子值Series（索引包含date和symbol）
            weight_method: 权重分配方式 ('equal', 'fixed_n', 'factor_weighted')
            n_stocks: 固定股票数量（仅用于fixed_n模式）

        Returns:
            Dict[str, float]: 股票代码 -> 权重
        """
        weights = {}

        if weight_method == 'equal':
            # 等权重：平均分配
            weight = 1.0 / len(stocks) if stocks else 0
            weights = {stock: weight for stock in stocks}

        elif weight_method == 'fixed_n':
            # 固定N只：每只固定权重
            if not n_stocks or n_stocks <= 0:
                n_stocks = 10  # 默认10只
            n_stocks = min(n_stocks, len(stocks))  # 不能超过可用股票数

            # 只使用前n_stocks只股票
            selected_stocks = stocks[:n_stocks]
            weight = 1.0 / len(selected_stocks)
            weights = {stock: weight for stock in selected_stocks}

        elif weight_method == 'factor_weighted':
            # 因子值加权：因子值标准化后作为权重
            # 提取这些股票的因子值
            current_factor_values = factor_values.loc[factor_values.index.get_level_values('symbol').isin(stocks)]

            # 标准化到[0, 1]范围
            min_val = current_factor_values.min()
            max_val = current_factor_values.max()

            if max_val > min_val:
                normalized = (current_factor_values - min_val) / (max_val - min_val)
                # 归一化使得总和为1
                total = normalized.sum()
                if total > 0:
                    for stock, norm_val in zip(stocks, normalized):
                        weights[stock] = norm_val / total
            else:
                # 所有因子值相同，使用等权重
                weight = 1.0 / len(stocks) if stocks else 0
                weights = {stock: weight for stock in stocks}

        return weights

    def _execute_backtester(self, params: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """执行回测节点"""
        from src.analysis.backtest import BacktestEngine
        
        # 从上游节点获取因子数据
        factor_data = self._get_input_data(params, results, 'factor_data')
        
        # 如果没有直接获取到因子数据，尝试从最近的因子计算结果中获取
        if factor_data is None or (hasattr(factor_data, 'empty') and factor_data.empty):
            # 遍历已执行的结果，寻找因子数据
            # 优先查找同时包含 date 和 symbol 的 MultiIndex Series
            for node_id in reversed(self.execution_order):
                if node_id in results and results[node_id] is not None:
                    result = results[node_id]
                    node = self.nodes.get(node_id)

                    if isinstance(result, pd.Series) and not result.empty:
                        # 检查是否是因子数据（包含日期和股票的多级索引）
                        if isinstance(result.index, pd.MultiIndex):
                            if 'date' in result.index.names and 'symbol' in result.index.names:
                                # 同时包含 date 和 symbol，这是正确的因子数据
                                factor_data = result
                                print(f"[DEBUG] 回测节点从节点 {node_id} ({node.node_type if node else 'unknown'}) 获取到正确的 factor_data: shape={result.shape}, index_names={result.index.names}")
                                break
                            elif 'date' in result.index.names and 'symbol' not in result.index.names:
                                # 只有 date，可能是 ic_series，跳过
                                continue
                    elif isinstance(result, dict) and 'factor_data' in result:
                        # 检查字典中的 factor_data
                        candidate = result['factor_data']
                        if isinstance(candidate, pd.Series) and not candidate.empty:
                            if isinstance(candidate.index, pd.MultiIndex):
                                if 'date' in candidate.index.names and 'symbol' in candidate.index.names:
                                    factor_data = candidate
                                    print(f"[DEBUG] 回测节点从字典的 factor_data 键获取到正确的数据: shape={candidate.shape}, index_names={candidate.index.names}")
                                    break
        
        # 获取价格数据
        price_data = self._get_input_data(params, results, 'price_data')
        
        # 如果没有直接获取到价格数据，尝试从数据加载节点获取
        if price_data is None or (hasattr(price_data, 'empty') and price_data.empty):
            for node_id in reversed(self.execution_order):
                if node_id in results and results[node_id] is not None:
                    result = results[node_id]
                    if isinstance(result, pd.DataFrame) and not result.empty:
                        # 检查是否是价格数据（包含open, high, low, close等列）
                        required_cols = ['open', 'close']  # 最基本的价格列
                        if all(col in result.columns for col in required_cols):
                            price_data = result
                            break
                    elif isinstance(result, dict):
                        if 'price_data' in result and result['price_data'] is not None:
                            price_data = result['price_data']
                            break
                        elif 'data' in result and isinstance(result['data'], pd.DataFrame):
                            # 检查是否是价格数据（包含open, close等列）
                            temp_required_cols = ['open', 'close']
                            if all(col in result['data'].columns for col in temp_required_cols):
                                price_data = result['data']
                                print(f"[DEBUG] 从 'data' 键中找到价格数据")
                                break
                        elif 'returns' in result and isinstance(result['returns'], pd.DataFrame):
                            price_data = result['returns']
                            break
                        elif isinstance(result, pd.DataFrame):
                            # 检查字典中的DataFrame是否包含价格数据
                            temp_required_cols = ['open', 'close']  # 最基本的价格列
                            if all(col in result.columns for col in temp_required_cols):
                                price_data = result
                                break
        
        if factor_data is not None and not (hasattr(factor_data, 'empty') and factor_data.empty) and \
           price_data is not None and not (hasattr(price_data, 'empty') and price_data.empty):

            print(f"[DEBUG] 回测节点获取到数据:")
            print(f"[DEBUG] factor_data: type={type(factor_data)}, shape={factor_data.shape}, index_names={factor_data.index.names if hasattr(factor_data.index, 'names') else 'N/A'}")
            print(f"[DEBUG] price_data: type={type(price_data)}, shape={price_data.shape}, index_names={price_data.index.names if hasattr(price_data.index, 'names') else 'N/A'}")

            backtester = BacktestEngine()

            # 解析weight_method参数（从格式 "equal: 等权重" 中提取 "equal"）
            weight_method_raw = params.get('weight_method', 'equal')
            if isinstance(weight_method_raw, str) and ':' in weight_method_raw:
                weight_method = weight_method_raw.split(':')[0].strip()
            else:
                weight_method = weight_method_raw

            try:
                # 运行多空组合回测
                ls_results = backtester.backtest_long_short_portfolio(
                    factor_data=factor_data,  # type: ignore
                    price_data=price_data,
                    top_quantile=params.get('top_quantile', 0.2),
                    bottom_quantile=params.get('bottom_quantile', 0.2),
                    transaction_cost=params.get('transaction_cost', 0.001),
                    weight_method=weight_method,
                    fixed_n_stocks=params.get('fixed_n_stocks', None)
                )
                
                # 运行分层回测
                n_quantiles = params.get('n_quantiles', 5)
                quantile_results = backtester.backtest_quantile_portfolio(
                    factor_data=factor_data,  # type: ignore
                    price_data=price_data,
                    n_quantiles=n_quantiles
                )
                
                return {
                    'long_short_results': ls_results,
                    'quantile_results': quantile_results,
                    'summary': self._summarize_backtest_results(ls_results, quantile_results)
                }
            except Exception as e:
                print(f"回测执行出错: {e}")
                # 返回默认结果
                return {
                    'long_short_results': {'error': str(e)},
                    'quantile_results': {},
                    'summary': {}
                }
        else:
            print(f"回测节点数据不足: factor_data is None: {factor_data is None}, price_data is None: {price_data is None}")
            if factor_data is not None:
                print(f"factor_data type: {type(factor_data)}, empty: {hasattr(factor_data, 'empty') and factor_data.empty}")
            if price_data is not None:
                print(f"price_data type: {type(price_data)}, empty: {hasattr(price_data, 'empty') and price_data.empty}")
            
            raise ValueError("回测节点缺少因子数据或价格数据")
    
    def _execute_performance_analyzer(self, params: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """执行绩效分析节点"""
        from src.analysis.performance import PerformanceAnalyzer
        
        returns_data = self._get_input_data(params, results, 'returns_data')
        benchmark_data = self._get_input_data(params, results, 'benchmark_data')
        
        if returns_data is not None:
            analyzer = PerformanceAnalyzer()
            perf_metrics = analyzer.calculate_strategy_performance(returns_data, benchmark_data)
            
            return {
                'metrics': perf_metrics,
                'summary': {
                    'annual_return': perf_metrics['annual_return'],
                    'sharpe_ratio': perf_metrics['sharpe_ratio'],
                    'max_drawdown': perf_metrics['max_drawdown'],
                    'win_rate': perf_metrics['win_rate']
                }
            }
        else:
            raise ValueError("绩效分析节点缺少收益率数据")
    
    def _execute_data_processor(self, params: Dict[str, Any], results: Dict[str, Any]) -> Any:
        """执行数据处理节点"""
        from src.factor_engine.neutralization import FactorNeutralizer

        data = self._get_input_data(params, results)

        if data is None:
            raise ValueError("数据处理节点缺少输入数据")

        # 解析operation参数
        operation_raw = params.get('operation', 'standardize')
        if isinstance(operation_raw, str) and ':' in operation_raw:
            operation = operation_raw.split(':')[0].strip()
        else:
            operation = operation_raw

        print(f"[DEBUG] 数据处理操作: {operation}")

        # 确保数据是Series格式
        if isinstance(data, pd.DataFrame):
            # 如果是DataFrame，尝试转换为Series
            if len(data.columns) > 0:
                data = data.iloc[:, 0]

        if not isinstance(data, pd.Series):
            return data

        try:
            if operation == 'standardize':
                # Z-Score标准化（按日期分组）
                if isinstance(data.index, pd.MultiIndex):
                    return data.groupby(level=0).transform(lambda x: (x - x.mean()) / (x.std() + 1e-8))
                else:
                    return (data - data.mean()) / (data.std() + 1e-8)

            elif operation == 'rank':
                # 排名标准化（0-1之间）
                if isinstance(data.index, pd.MultiIndex):
                    return data.groupby(level=0).rank(pct=True)
                else:
                    return data.rank(pct=True)

            elif operation == 'neutralize':
                # 因子中性化
                neutralize_method_raw = params.get('neutralize_method', 'both')
                if isinstance(neutralize_method_raw, str) and ':' in neutralize_method_raw:
                    neutralize_method = neutralize_method_raw.split(':')[0].strip()
                else:
                    neutralize_method = neutralize_method_raw

                print(f"[DEBUG] 中性化方式: {neutralize_method}")

                # 获取市值数据（从上游节点获取）
                market_cap = None
                if neutralize_method in ['market_cap', 'both']:
                    # 尝试从数据加载节点获取市值数据
                    for node_id in reversed(self.execution_order):
                        if node_id in results and results[node_id] is not None:
                            result = results[node_id]
                            if isinstance(result, pd.DataFrame):
                                if 'market_cap' in result.columns or 'total_mv' in result.columns:
                                    # 获取市值列
                                    mc_col = 'market_cap' if 'market_cap' in result.columns else 'total_mv'
                                    market_cap = result[mc_col]
                                    print(f"[DEBUG] 从节点 {node_id} 获取市值数据")
                                    break

                # 执行中性化
                if neutralize_method == 'industry':
                    result = FactorNeutralizer.neutralize_by_industry(data)
                    print(f"[DEBUG] 行业中性化完成")
                elif neutralize_method == 'market_cap':
                    if market_cap is None:
                        print("[WARNING] 市值中性化需要市值数据，但未找到，跳过中性化")
                        result = data
                    else:
                        result = FactorNeutralizer.neutralize_by_market_cap(data, market_cap)
                        print(f"[DEBUG] 市值中性化完成")
                elif neutralize_method == 'both':
                    if market_cap is None:
                        print("[WARNING] 双重中性化需要市值数据，但未找到，仅做行业中性化")
                        result = FactorNeutralizer.neutralize_by_industry(data)
                    else:
                        result = FactorNeutralizer.neutralize_both(data, market_cap)
                        print(f"[DEBUG] 双重中性化完成")
                else:
                    result = data

                return result

            elif operation == 'winsorize':
                # 去极值处理
                winsorize_method_raw = params.get('winsorize_method', 'mad')
                if isinstance(winsorize_method_raw, str) and ':' in winsorize_method_raw:
                    winsorize_method = winsorize_method_raw.split(':')[0].strip()
                else:
                    winsorize_method = winsorize_method_raw

                if isinstance(data.index, pd.MultiIndex):
                    # 按日期分组去极值
                    if winsorize_method == 'mad':
                        # MAD法：中位数 ± 3 * MAD
                        def winsorize_mad(x):
                            median = x.median()
                            mad = (x - median).abs().median()
                            upper = median + 3 * mad
                            lower = median - 3 * mad
                            return x.clip(lower, upper)
                        return data.groupby(level=0).transform(winsorize_mad)
                    elif winsorize_method == 'sigma':
                        # 3σ法：均值 ± 3 * 标准差
                        def winsorize_sigma(x):
                            mean = x.mean()
                            std = x.std()
                            upper = mean + 3 * std
                            lower = mean - 3 * std
                            return x.clip(lower, upper)
                        return data.groupby(level=0).transform(winsorize_sigma)
                    else:  # percentile
                        # 百分位法：将超过上下1%分位数的值截断
                        def winsorize_percentile(x):
                            upper = x.quantile(0.99)
                            lower = x.quantile(0.01)
                            return x.clip(lower, upper)
                        return data.groupby(level=0).transform(winsorize_percentile)
                else:
                    # 全局去极值
                    if winsorize_method == 'mad':
                        median = data.median()
                        mad = (data - median).abs().median()
                        return data.clip(median - 3 * mad, median + 3 * mad)
                    elif winsorize_method == 'sigma':
                        return data.clip(data.mean() - 3 * data.std(), data.mean() + 3 * data.std())
                    else:  # percentile
                        return data.clip(data.quantile(0.01), data.quantile(0.99))

            elif operation == 'fill_na':
                # 填充缺失值
                fill_method_raw = params.get('fill_method', 'median')
                if isinstance(fill_method_raw, str) and ':' in fill_method_raw:
                    fill_method = fill_method_raw.split(':')[0].strip()
                else:
                    fill_method = fill_method_raw

                if isinstance(data.index, pd.MultiIndex):
                    # 按日期分组填充
                    if fill_method == 'mean':
                        return data.groupby(level=0).transform(lambda x: x.fillna(x.mean()))
                    elif fill_method == 'median':
                        return data.groupby(level=0).transform(lambda x: x.fillna(x.median()))
                    elif fill_method == 'ffill':
                        return data.groupby(level=0).fillna(method='ffill')
                    else:  # zero
                        return data.fillna(0)
                else:
                    # 全局填充
                    if fill_method == 'mean':
                        return data.fillna(data.mean())
                    elif fill_method == 'median':
                        return data.fillna(data.median())
                    elif fill_method == 'ffill':
                        return data.fillna(method='ffill')
                    else:  # zero
                        return data.fillna(0)

            else:
                return data

        except Exception as e:
            print(f"[ERROR] 数据处理失败: {e}")
            import traceback
            traceback.print_exc()
            return data

    def _execute_signal_generator(self, params: Dict[str, Any], results: Dict[str, Any]) -> pd.Series:
        """执行信号生成节点"""
        factor_data = self._get_input_data(params, results, 'factor_data')

        if factor_data is None or factor_data.empty:
            raise ValueError("信号生成节点缺少因子数据或数据为空")

        print(f"[DEBUG] 信号生成 - 输入数据: type={type(factor_data)}, shape={factor_data.shape if hasattr(factor_data, 'shape') else 'N/A'}")
        print(f"[DEBUG] 信号生成 - 索引类型: {type(factor_data.index)}, 索引名称: {factor_data.index.names if hasattr(factor_data.index, 'names') else 'N/A'}")

        signal_method = params.get('method', 'rank')
        threshold = params.get('threshold', 0.8)

        try:
            if signal_method == 'rank':
                # 基于排名的信号 - 在每个日期横截面上进行排名
                if isinstance(factor_data.index, pd.MultiIndex):
                    # MultiIndex: (date, symbol) - 按日期分组排名
                    ranked_data = factor_data.groupby(level=0).rank(pct=True)
                    print(f"[DEBUG] 排名后数据: shape={ranked_data.shape}, 范围=[{ranked_data.min():.3f}, {ranked_data.max():.3f}]")

                    # 生成信号：前threshold%做多，后(1-threshold)%做空
                    signals = pd.Series(0, index=factor_data.index)
                    signals[ranked_data >= threshold] = 1
                    signals[ranked_data <= (1 - threshold)] = -1
                else:
                    # 单索引：直接排名
                    ranked_data = factor_data.rank(pct=True)
                    signals = pd.Series(0, index=factor_data.index)
                    signals[ranked_data >= threshold] = 1
                    signals[ranked_data <= (1 - threshold)] = -1

            elif signal_method == 'value':
                # 基于因子值的信号 - 标准化后根据阈值生成信号
                if isinstance(factor_data.index, pd.MultiIndex):
                    # MultiIndex: 按日期分组标准化
                    mean_val = factor_data.groupby(level=0).transform('mean')
                    std_val = factor_data.groupby(level=0).transform('std')
                    normalized = (factor_data - mean_val) / std_val
                    normalized = normalized.fillna(0)  # 处理NaN

                    print(f"[DEBUG] 标准化后数据: shape={normalized.shape}, 范围=[{normalized.min():.3f}, {normalized.max():.3f}]")

                    # 生成信号
                    signals = pd.Series(0, index=factor_data.index)
                    signals[normalized >= threshold] = 1
                    signals[normalized <= -threshold] = -1
                else:
                    # 单索引：全局标准化
                    mean_val = factor_data.mean()
                    std_val = factor_data.std()
                    normalized = (factor_data - mean_val) / std_val
                    normalized = normalized.fillna(0)

                    signals = pd.Series(0, index=factor_data.index)
                    signals[normalized >= threshold] = 1
                    signals[normalized <= -threshold] = -1
            else:
                signals = pd.Series(0, index=factor_data.index)

            # 统计信号分布
            signal_counts = signals.value_counts()
            print(f"[DEBUG] 信号分布: 做多={signal_counts.get(1, 0)}, 做空={signal_counts.get(-1, 0)}, 中性={signal_counts.get(0, 0)}")

            return signals

        except Exception as e:
            import traceback
            print(f"[ERROR] 信号生成失败: {e}")
            traceback.print_exc()
            raise ValueError(f"信号生成失败: {str(e)}")
    
    def _execute_portfolio_optimizer(self, params: Dict[str, Any], results: Dict[str, Any]) -> pd.Series:
        """执行投资组合优化节点"""
        signals = self._get_input_data(params, results, 'signals')
        prices = self._get_input_data(params, results, 'prices')
        
        if signals is not None:
            weight_method = params.get('weight_method', 'equal')
            max_weight = params.get('max_weight', 0.1)
            
            if weight_method == 'equal':
                # 等权重
                weights = signals.copy()
                long_signals = signals > 0
                short_signals = signals < 0
                
                if long_signals.any():
                    n_long = long_signals.sum()
                    weights[long_signals] = 0.5 / n_long if n_long > 0 else 0
                if short_signals.any():
                    n_short = short_signals.sum()
                    weights[short_signals] = -00.5 / n_short if n_short > 0 else 0
                
                # 限制权重
                weights = weights.clip(-max_weight, max_weight)
            elif weight_method == 'proportional':
                # 按信号强度比例加权
                abs_signals = signals.abs()
                total_abs_signal = abs_signals.groupby(level=0).sum()
                weights = signals / total_abs_signal
                weights = weights.clip(-max_weight, max_weight)
            else:
                weights = pd.Series(0, index=signals.index)
            
            return weights
        else:
            raise ValueError("投资组合优化节点缺少信号数据")
    
    def _execute_risk_manager(self, params: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """执行风险管理节点"""
        positions = self._get_input_data(params, results, 'positions')
        risk_limits = params.get('risk_limits', {})
        
        risk_report = {
            'position_limits_respected': True,
            'sector_exposure': {},
            'individual_position_limits': [],
            'overall_risk_metrics': {}
        }
        
        # 简化的风险管理检查
        if positions is not None and isinstance(positions, pd.Series):
            # 检查头寸限制
            max_position_limit = risk_limits.get('max_position', 0.1)
            violations = positions.abs() > max_position_limit
            risk_report['individual_position_limits'] = violations.tolist()
            risk_report['position_limits_respected'] = not violations.any()
        
        return risk_report
    
    def _get_input_data(self, params: Dict[str, Any], results: Dict[str, Any], key: Optional[str] = None) -> Any:
        """获取节点输入数据"""
        print(f"[DEBUG] _get_input_data 查找: key={key}")

        # 首先尝试从参数中获取数据
        if key:
            if key in params:
                return params[key]
        elif 'data' in params:
            return params['data']
        elif 'input_data' in params:
            return params['input_data']

        # 如果参数中没有，尝试从结果中获取
        if results:
            # 按执行顺序反向搜索，找到最近的合适数据
            for node_id in reversed(self.execution_order):
                if node_id not in results:
                    continue

                result = results[node_id]
                if result is None:
                    continue

                print(f"[DEBUG] 检查节点 {node_id[:8]}, result类型: {type(result).__name__}")

                # 如果指定了特定键，尝试从结果字典中获取
                if key and isinstance(result, dict):
                    if key in result:
                        print(f"[DEBUG] 在结果中找到key: {key}")
                        return result[key]

                    # 特殊映射：从回测结果中提取数据
                    if key == 'returns_data':
                        if 'returns' in result:
                            print(f"[DEBUG] 从回测结果中提取returns作为returns_data")
                            return result['returns']
                        elif 'long_short_results' in result and isinstance(result['long_short_results'], dict):
                            if 'returns' in result['long_short_results']:
                                print(f"[DEBUG] 从long_short_results中提取returns")
                                return result['long_short_results']['returns']

                    # 特殊映射：从回测结果中提取价格数据作为基准
                    if key == 'benchmark_data':
                        if 'prices' in result:
                            print(f"[DEBUG] 从回测结果中提取prices作为benchmark_data")
                            return result['prices']

                # 智能匹配：根据key和result类型判断
                if key:
                    # 特殊处理：因子计算节点返回的Series
                    if key == 'factor_data' and isinstance(result, (pd.Series, pd.DataFrame)):
                        print(f"[DEBUG] 找到因子数据: type={type(result).__name__}")
                        return result

                    # 特殊处理：信号数据
                    if key == 'signals' and isinstance(result, pd.Series):
                        # 检查是否是信号数据（值通常为-1, 0, 1）
                        unique_vals = result.dropna().unique()
                        if len(unique_vals) <= 5 and set(unique_vals).issubset({-1, 0, 1}):
                            print(f"[DEBUG] 找到信号数据: type={type(result).__name__}, shape={result.shape}")
                            return result

                    # 特殊处理：价格数据DataFrame
                    if key in ['price_data', 'prices', 'benchmark_data'] and isinstance(result, pd.DataFrame):
                        if any(col in result.columns for col in ['open', 'high', 'low', 'close', 'volume']):
                            print(f"[DEBUG] 找到价格数据: type={type(result).__name__}, shape={result.shape}")
                            return result

                    # 特殊处理：收益率数据
                    if key in ['returns_data', 'returns'] and isinstance(result, pd.Series):
                        # 检查是否是收益率数据（值通常较小）
                        if result.abs().max() < 1:  # 收益率通常绝对值小于1
                            print(f"[DEBUG] 找到收益率数据: type={type(result).__name__}")
                            return result

                # 如果没有指定键，直接返回结果
                elif not key:
                    print(f"[DEBUG] 未指定key，返回result: type={type(result).__name__}")
                    return result

            # 如果按执行顺序没找到，遍历所有结果尝试匹配
            for node_id in reversed(list(results.keys())):
                result = results[node_id]
                if result is None:
                    continue

                if isinstance(result, dict) and key:
                    if key in result:
                        return result[key]

                    # 再次尝试特殊映射
                    if key == 'returns_data' and 'returns' in result:
                        return result['returns']

                elif key is None:
                    return result

                # Series可以作为factor_data或signals
                elif isinstance(result, pd.Series):
                    if key in ['factor_data', 'signals']:
                        print(f"[DEBUG] 找到匹配数据(备用): key={key}, type={type(result).__name__}")
                        return result
                    elif key == 'price_data' or key == 'prices':
                        # Series不可能是价格数据
                        continue

                # DataFrame可以作为price_data
                elif isinstance(result, pd.DataFrame):
                    if key in ['price_data', 'prices', 'benchmark_data']:
                        if any(col in result.columns for col in ['open', 'high', 'low', 'close', 'volume']):
                            print(f"[DEBUG] 找到匹配数据(备用): key={key}, type={type(result).__name__}")
                            return result

        print(f"[DEBUG] _get_input_data 未找到数据: key={key}, results_keys={list(results.keys()) if results else 'None'}")
        return None
    
    def _summarize_backtest_results(self, ls_results: Dict, quantile_results: Dict) -> Dict:
        """汇总回测结果"""
        summary = {}

        if 'error' not in ls_results:
            # 提取时间范围 - 从returns数据中获取
            if 'returns' in ls_results and not ls_results['returns'].empty:
                dates = ls_results['returns'].index.get_level_values('date')
                summary['start_date'] = dates.min().strftime('%Y-%m-%d')
                summary['end_date'] = dates.max().strftime('%Y-%m-%d')
                summary['trading_days'] = len(dates.unique())
            else:
                # 如果没有returns，尝试从quantile_results中获取
                if quantile_results and len(quantile_results) > 0:
                    first_q = list(quantile_results.values())[0]
                    if 'returns' in first_q and not first_q['returns'].empty:
                        dates = first_q['returns'].index.get_level_values('date')
                        summary['start_date'] = dates.min().strftime('%Y-%m-%d')
                        summary['end_date'] = dates.max().strftime('%Y-%m-%d')
                        summary['trading_days'] = len(dates.unique())

            summary.update({
                'ls_total_return': ls_results.get('total_return', 0),
                'ls_annual_return': ls_results.get('annual_return', 0),
                'ls_sharpe_ratio': ls_results.get('sharpe_ratio', 0),
                'ls_max_drawdown': ls_results.get('max_drawdown', 0)
            })

        # 汇总分层回测结果
        for q_name, q_result in quantile_results.items():
            summary[f'{q_name}_annual_return'] = q_result.get('annual_return', 0)
            summary[f'{q_name}_sharpe_ratio'] = q_result.get('sharpe_ratio', 0)

        return summary
    
    def save_workflow(self, filepath: str, name: str = None, description: str = None):
        """
        保存工作流到文件

        Args:
            filepath: 文件路径
            name: 工作流名称（可选）
            description: 工作流描述（可选）
        """
        import datetime

        workflow_data = {
            'metadata': {
                'name': name or os.path.basename(filepath).replace('.json', ''),
                'description': description or '',
                'created_at': datetime.datetime.now().isoformat(),
                'node_count': len(self.nodes),
                'connection_count': len(self.connections)
            },
            'nodes': {
                node_id: {
                    'id': node.id,
                    'node_type': node.node_type,
                    'position': node.position,
                    'params': node.params,
                    'inputs': node.inputs,
                    'outputs': node.outputs
                } for node_id, node in self.nodes.items()
            },
            'connections': self.connections
        }

        # 确保目录存在
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(workflow_data, f, indent=2, ensure_ascii=False)

    def load_workflow(self, filepath: str):
        """从文件加载工作流"""
        with open(filepath, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)

        self.nodes = {}
        for node_id, node_data in workflow_data['nodes'].items():
            node = Node(
                id=node_data['id'],
                node_type=node_data['node_type'],
                position=node_data['position'],
                params=node_data['params'],
                inputs=node_data['inputs'],
                outputs=node_data['outputs']
            )
            self.nodes[node_id] = node

        self.connections = workflow_data['connections']

        # 返回元数据（如果有的话）
        return workflow_data.get('metadata', {})

    @staticmethod
    def list_saved_workflows(workflows_dir: str = "workflows") -> list:
        """
        列出所有已保存的工作流

        Args:
            workflows_dir: 工作流保存目录

        Returns:
            list: 工作流信息列表
        """
        import os

        # 如果目录不存在，返回空列表
        if not os.path.exists(workflows_dir):
            os.makedirs(workflows_dir)
            return []

        workflows = []
        for filename in os.listdir(workflows_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(workflows_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    metadata = data.get('metadata', {})
                    workflows.append({
                        'filename': filename,
                        'filepath': filepath,
                        'name': metadata.get('name', filename.replace('.json', '')),
                        'description': metadata.get('description', ''),
                        'created_at': metadata.get('created_at', ''),
                        'node_count': metadata.get('node_count', 0),
                        'connection_count': metadata.get('connection_count', 0)
                    })
                except Exception as e:
                    # 如果文件读取失败，添加基本信息
                    workflows.append({
                        'filename': filename,
                        'filepath': filepath,
                        'name': filename.replace('.json', ''),
                        'description': '[读取失败]',
                        'created_at': '',
                        'node_count': 0,
                        'connection_count': 0
                    })

        # 按创建时间排序
        workflows.sort(key=lambda x: x['created_at'], reverse=True)
        return workflows

    @staticmethod
    def delete_workflow(filepath: str) -> bool:
        """
        删除工作流文件

        Args:
            filepath: 文件路径

        Returns:
            bool: 是否删除成功
        """
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception as e:
            print(f"删除工作流失败: {e}")
            return False

    def _execute_factor_correlation(self, params: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """执行因子相关性分析节点"""
        from src.analysis.factor_correlation import FactorCorrelationAnalyzer

        # 收集所有因子数据
        factor_dict = {}

        # 从已执行的节点中提取因子数据
        for node_id, result in results.items():
            if result is None:
                continue

            # 尝试提取因子数据
            if isinstance(result, pd.Series):
                # 如果是Series，检查是否是因子数据
                if len(result) > 0:
                    factor_dict[f'factor_{node_id[:8]}'] = result
            elif isinstance(result, pd.DataFrame):
                # 如果是DataFrame，尝试提取因子列
                if 'factor_value' in result.columns:
                    factor_dict[f'factor_{node_id[:8]}'] = result.set_index(['date', 'symbol'])['factor_value'] if isinstance(result.index, pd.MultiIndex) else result['factor_value']
                # 或者取第一个数值列
                else:
                    numeric_cols = result.select_dtypes(include=[np.number]).columns
                    if len(numeric_cols) > 0:
                        factor_dict[f'factor_{node_id[:8]}'] = result[numeric_cols[0]]

        if len(factor_dict) < 2:
            raise ValueError("因子相关性分析需要至少两个因子数据")

        # 获取参数
        threshold = params.get('threshold', 0.7)
        method = params.get('method', 'spearman')
        n_clusters = params.get('n_clusters', None)

        # 执行相关性分析
        try:
            analyzer = FactorCorrelationAnalyzer(factor_dict)

            # 计算相关系数矩阵
            corr_matrix = analyzer.calculate_correlation(method=method)

            # 找出高相关性因子对
            high_corr_pairs = analyzer.find_high_correlation_pairs(threshold=threshold, method=method)

            # 层次聚类分析
            if n_clusters:
                cluster_result = analyzer.hierarchical_clustering(n_clusters=n_clusters)
            else:
                cluster_result = analyzer.hierarchical_clustering()

            # 生成去重建议
            removal_suggestions = analyzer.generate_removal_suggestions(threshold=threshold, method=method)

            # 生成详细报告
            report = analyzer.generate_report()

            return {
                'correlation_matrix': corr_matrix,
                'high_correlation_pairs': high_corr_pairs,
                'cluster_result': cluster_result,
                'removal_suggestions': removal_suggestions,
                'correlation_report': report,
                'factor_names': list(factor_dict.keys()),
                'n_factors': len(factor_dict),
                'correlation_summary': {
                    'n_factors': len(factor_dict),
                    'n_high_corr_pairs': len(high_corr_pairs),
                    'max_correlation': float(corr_matrix.abs().max().max()) if len(corr_matrix) > 0 else 0.0,
                    'avg_correlation': float(corr_matrix.abs().values[np.triu_indices_from(corr_matrix.values, k=1)].mean()) if len(corr_matrix) > 0 else 0.0,
                    'threshold': threshold
                }
            }
        except Exception as e:
            print(f"因子相关性分析出错: {str(e)}")
            import traceback
            traceback.print_exc()
            raise


# 测试代码
if __name__ == '__main__':
    # 创建测试工作流
    engine = WorkflowEngine()
    
    print("工作流引擎测试开始...")
    
    # 添加数据加载节点
    data_node_id = engine.add_node(
        node_type='data_loader',
        position={'x': 100, 'y': 100},
        params={
            'symbols': ['000001.SZ', '000002.SZ', '600000.SH'],
            'start_date': '2023-01-01',
            'end_date': '2023-02-28',
            'fields': ['open', 'high', 'low', 'close', 'volume']
        }
    )
    
    # 添加因子计算节点
    factor_node_id = engine.add_node(
        node_type='factor_calculator',
        position={'x': 300, 'y': 100},
        params={
            'factor_name': 'alpha001'
        }
    )
    
    # 添加IC分析节点
    ic_node_id = engine.add_node(
        node_type='ic_analyzer',
        position={'x': 500, 'y': 100},
        params={}
    )
    
    # 连接节点
    engine.connect_nodes(data_node_id, factor_node_id)
    engine.connect_nodes(factor_node_id, ic_node_id)
    
    print(f"创建了 {len(engine.nodes)} 个工作流节点")
    print(f"创建了 {len(engine.connections)} 个连接")
    
    # 执行工作流（注意：这需要真实数据，可能会失败如果没有QMT服务）
    try:
        results = engine.execute_workflow()
        print(f"工作流执行完成，结果数: {len(results)}")
        
        for node_id, result in results.items():
            node = engine.nodes[node_id]
            print(f"节点 {node.node_type}: {type(result).__name__ if result is not None else 'None'}")
    except Exception as e:
        print(f"工作流执行出错: {e}")
        print("这可能是由于缺少数据源或QMT服务未启动造成的")
    
    print("工作流引擎测试完成!")