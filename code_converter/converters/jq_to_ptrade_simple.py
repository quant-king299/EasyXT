"""
聚宽到Ptrade代码转换器 - 简化版本
"""
import ast
import json
import os
from typing import Dict, Any, Optional

class JQToPtradeConverter:
    """聚宽到Ptrade代码转换器 - 简化版本"""
    
    def __init__(self, api_mapping_file=None):
        # API映射规则
        if api_mapping_file and os.path.exists(api_mapping_file):
            with open(api_mapping_file, 'r', encoding='utf-8') as f:
                self.api_mapping = json.load(f)
        else:
            # 默认API映射规则
            self.api_mapping = {
                # 数据获取API
                'get_price': 'get_price',
                'get_current_data': 'get_current_data',
                'get_fundamentals': 'get_fundamentals',
                'get_index_stocks': 'get_index_stocks',
                'get_industry_stocks': 'get_industry_stocks',
                'get_concept_stocks': 'get_concept_stocks',
                'get_all_securities': 'get_all_securities',
                'get_security_info': 'get_security_info',
                'attribute_history': 'get_price',
                'get_bars': 'get_price',
                
                # 交易API
                'order': 'order',
                'order_value': 'order_value',
                'order_target': 'order_target',
                'order_target_value': 'order_target_value',
                'cancel_order': 'cancel_order',
                'get_open_orders': 'get_open_orders',
                'get_trades': 'get_trades',
                'set_order_cost': 'set_order_cost',
                
                # 账户API
                'get_portfolio': 'get_portfolio',
                'get_positions': 'get_positions',
                'get_orders': 'get_orders',
                
                # 系统API
                'log': 'log',
                'record': 'record',
                'plot': 'plot',
                'set_benchmark': 'set_benchmark',
                'set_option': 'set_option',
                
                # 风险控制API
                'set_slippage': 'set_slippage',
                'set_commission': 'set_commission',
                'set_price_limit': 'set_price_limit',
                
                # 定时任务API
                'run_daily': 'run_daily',
                'run_weekly': 'run_weekly',
                'run_monthly': 'run_monthly',
            }
        
        # 需要移除的API（Ptrade不支持的API）
        self.removed_apis = {
            'set_option',
            'set_commission',
            'set_slippage',
            'set_price_limit',
            'set_benchmark',
            'set_order_cost'
        }
    
    def convert(self, jq_code: str) -> str:
        """
        转换聚宽代码为Ptrade代码
        
        Args:
            jq_code: 聚宽策略代码
            
        Returns:
            str: 转换后的Ptrade代码
        """
        try:
            # 解析代码为AST
            tree = ast.parse(jq_code)
            
            # 转换AST
            converted_tree = self._transform_ast(tree)
            
            # 生成代码
            ptrade_code = ast.unparse(converted_tree)
            
            # 添加必要的头部信息
            ptrade_code = self._add_header(ptrade_code)
            
            # 确保生成符合Ptrade要求的策略结构
            ptrade_code = self._ensure_ptrade_structure(ptrade_code)
            
            # 整合定时任务函数逻辑
            ptrade_code = self._integrate_timing_functions(ptrade_code)
            
            return ptrade_code
            
        except Exception as e:
            # 如果AST转换失败，使用字符串替换方法
            return self._convert_by_string_replacement(jq_code)
    
    def _transform_ast(self, tree: ast.AST) -> ast.AST:
        """转换AST节点"""
        transformer = JQToPtradeTransformer(self.api_mapping, self.removed_apis)
        return transformer.visit(tree)
    
    def _add_header(self, code: str) -> str:
        """添加必要的头部信息"""
        header = '''# 自动生成的Ptrade策略代码
# 原始代码来自聚宽策略

'''
        return header + code
    
    def _ensure_ptrade_structure(self, code: str) -> str:
        """确保生成符合Ptrade要求的策略结构"""
        # 确保包含必要的函数
        required_functions = {
            'initialize': '''def initialize(context):
    log.info('初始函数开始运行且全局只运行一次')
    pass

''',
            'before_trading_start': '''def before_trading_start(context, data):
    # 盘前处理
    pass

''',
            'handle_data': '''def handle_data(context, data):
    # 盘中处理
    pass

''',
            'after_trading_end': '''def after_trading_end(context, data):
    # 收盘后处理
    pass

'''
        }
        
        # 检查已存在的函数
        existing_functions = []
        lines = code.split('\n')
        for line in lines:
            if line.startswith('def '):
                func_name = line.split('(')[0].replace('def ', '').strip()
                existing_functions.append(func_name)
        
        # 添加缺失的函数
        for func_name, func_code in required_functions.items():
            if func_name not in existing_functions:
                code = func_code + code if func_name == 'initialize' else code + '\n' + func_code
        
        return code
    
    def _integrate_timing_functions(self, code: str) -> str:
        """整合定时任务函数逻辑到Ptrade标准函数中"""
        lines = code.split('\n')
        
        # 提取定时任务函数的内容
        timing_functions = {}
        current_func = None
        func_content = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith('def before_market_open('):
                current_func = 'before_market_open'
                func_content = []
            elif line.startswith('def market_open('):
                current_func = 'market_open'
                func_content = []
            elif line.startswith('def after_market_close('):
                current_func = 'after_market_close'
                func_content = []
            elif current_func and (line.startswith('def ') or (line.strip() == '' and i + 1 < len(lines) and not lines[i + 1].startswith(' ') and lines[i + 1].startswith('def '))):
                # 函数结束
                timing_functions[current_func] = func_content[:]
                current_func = None
                func_content = []
                continue
            elif current_func:
                func_content.append(line)
            
            i += 1
        
        # 保存最后一个函数
        if current_func:
            timing_functions[current_func] = func_content[:]
        
        # 整合到标准函数中
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith('def initialize('):
                new_lines.append(line)
                i += 1
                # 复制initialize函数体，但移除run_daily调用
                while i < len(lines) and not (lines[i].startswith('def ') and lines[i] != 'def initialize(context):'):
                    if 'run_daily(' not in lines[i]:
                        new_lines.append(lines[i])
                    i += 1
                continue
            elif line.startswith('def before_trading_start('):
                new_lines.append(line)
                i += 1
                # 复制before_trading_start函数体
                while i < len(lines) and not (lines[i].startswith('def ') and lines[i] != 'def before_trading_start(context, data):'):
                    new_lines.append(lines[i])
                    i += 1
                # 添加before_market_open的逻辑
                if 'before_market_open' in timing_functions:
                    new_lines.append('')
                    for func_line in timing_functions['before_market_open']:
                        if func_line.strip() and not func_line.startswith('def '):
                            # 添加适当的缩进
                            if not func_line.startswith('    '):
                                new_lines.append('    ' + func_line)
                            else:
                                new_lines.append(func_line)
                continue
            elif line.startswith('def handle_data('):
                new_lines.append(line)
                i += 1
                # 复制handle_data函数体
                while i < len(lines) and not (lines[i].startswith('def ') and lines[i] != 'def handle_data(context, data):'):
                    new_lines.append(lines[i])
                    i += 1
                # 添加market_open的逻辑
                if 'market_open' in timing_functions:
                    new_lines.append('')
                    for func_line in timing_functions['market_open']:
                        if func_line.strip() and not func_line.startswith('def '):
                            # 添加适当的缩进
                            if not func_line.startswith('    '):
                                new_lines.append('    ' + func_line.replace('get_bars', 'get_price'))
                            else:
                                new_lines.append(func_line.replace('get_bars', 'get_price'))
                continue
            elif line.startswith('def after_trading_end('):
                new_lines.append(line)
                i += 1
                # 复制after_trading_end函数体
                while i < len(lines) and not (lines[i].startswith('def ') and lines[i] != 'def after_trading_end(context, data):'):
                    new_lines.append(lines[i])
                    i += 1
                # 添加after_market_close的逻辑
                if 'after_market_close' in timing_functions:
                    new_lines.append('')
                    for func_line in timing_functions['after_market_close']:
                        if func_line.strip() and not func_line.startswith('def '):
                            # 添加适当的缩进
                            if not func_line.startswith('    '):
                                new_lines.append('    ' + func_line)
                            else:
                                new_lines.append(func_line)
                continue
            elif line.startswith('def before_market_open(') or line.startswith('def market_open(') or line.startswith('def after_market_close('):
                # 跳过这些函数的定义
                while i < len(lines) and not (lines[i].startswith('def ') or lines[i].strip() == ''):
                    i += 1
                # 如果是空行，也跳过
                if i < len(lines) and lines[i].strip() == '':
                    i += 1
                continue
            else:
                new_lines.append(line)
                i += 1
        
        return '\n'.join(new_lines)
    
    def _convert_by_string_replacement(self, jq_code: str) -> str:
        """
        通过字符串替换方法转换代码
        当AST转换失败时使用此方法作为备选
        """
        # 添加头部信息
        ptrade_code = '''# 自动生成的Ptrade策略代码
# 原始代码来自聚宽策略

'''
        
        # 移除导入语句
        lines = jq_code.split('\n')
        filtered_lines = []
        for line in lines:
            if not line.strip().startswith('import ') and not line.strip().startswith('from '):
                filtered_lines.append(line)
        code_body = '\n'.join(filtered_lines)
        
        # 替换g.为context.
        code_body = code_body.replace('g.', 'context.')
        
        # 替换get_bars为get_price
        code_body = code_body.replace('get_bars', 'get_price')
        
        # 移除不支持的API调用
        for api in self.removed_apis:
            lines = code_body.split('\n')
            new_lines = []
            for line in lines:
                if f'{api}(' not in line and f' {api}(' not in line:
                    new_lines.append(line)
            code_body = '\n'.join(new_lines)
        
        # 移除run_daily调用
        lines = code_body.split('\n')
        new_lines = []
        for line in lines:
            if 'run_daily(' not in line:
                new_lines.append(line)
        code_body = '\n'.join(new_lines)
        
        # 添加标准函数结构
        ptrade_code += '''def initialize(context):
    log.info('初始函数开始运行且全局只运行一次')
    pass

def before_trading_start(context, data):
    # 盘前处理
    pass

def handle_data(context, data):
    # 盘中处理
    pass

def after_trading_end(context, data):
    # 收盘后处理
    pass

'''
        
        return ptrade_code

class JQToPtradeTransformer(ast.NodeTransformer):
    """聚宽到Ptrade AST转换器"""
    
    def __init__(self, api_mapping: Dict[str, str], removed_apis: set):
        self.api_mapping = api_mapping
        self.removed_apis = removed_apis
    
    def visit_Call(self, node: ast.Call) -> Optional[ast.AST]:
        """转换函数调用节点"""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            # 检查是否是需要移除的API
            if func_name in self.removed_apis:
                # 返回None来移除节点
                return None
            elif func_name in self.api_mapping:
                # 映射函数名
                node.func.id = self.api_mapping[func_name]
        elif isinstance(node.func, ast.Attribute):
            # 处理属性访问，如 log.info
            attr_name = node.func.attr
            if isinstance(node.func.value, ast.Name):
                full_name = f"{node.func.value.id}.{attr_name}"
                if full_name in self.api_mapping:
                    if '.' in self.api_mapping[full_name]:
                        # 映射到新的属性访问
                        new_parts = self.api_mapping[full_name].split('.')
                        node.func.value.id = new_parts[0]
                        node.func.attr = new_parts[1]
                    else:
                        # 映射到简单函数名
                        node.func = ast.Name(id=self.api_mapping[full_name], ctx=ast.Load())
        
        # 继续遍历子节点
        return self.generic_visit(node)
    
    def visit_Import(self, node: ast.Import) -> Optional[ast.AST]:
        """转换导入语句 - Ptrade不需要导入语句，直接移除"""
        return None
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> Optional[ast.AST]:
        """转换from导入语句 - Ptrade不需要导入语句，直接移除"""
        return None
    
    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        """转换赋值语句"""
        # 处理 g.xxx = ... 这样的全局变量赋值
        for target in node.targets:
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                if target.value.id == 'g':
                    # 将 g.xxx 转换为 context.xxx
                    target.value.id = 'context'
        return self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name) -> ast.AST:
        """转换名称引用"""
        # 处理对 g 的直接引用
        if node.id == 'g':
            # 将 g 转换为 context
            node.id = 'context'
        return self.generic_visit(node)
    
    def visit_Expr(self, node: ast.Expr) -> Optional[ast.AST]:
        """转换表达式语句"""
        # 如果表达式包含需要移除的函数调用，移除整个表达式
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            if node.value.func.id in self.removed_apis:
                return None
        return self.generic_visit(node)