"""
聚宽到Ptrade代码转换器
"""
import ast
import sys
import json
import os
from typing import Dict, List, Any, Optional
import statsmodels.api as sm

class JQToPtradeConverter:
    """聚宽到Ptrade代码转换器"""
    
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
                'get_current_data': 'get_snapshot',  # 聚宽的get_current_data映射到Ptrade的get_snapshot
                'get_fundamentals': 'get_fundamentals',
                'get_index_stocks': 'get_index_stocks',
                'get_industry_stocks': 'get_industry_stocks',
                'get_concept_stocks': 'get_concept_stocks',
                'get_all_securities': 'get_Ashares',  # 聚宽的get_all_securities映射到Ptrade的get_Ashares（获取A股代码列表）
                'get_security_info': 'get_stock_info',  # 聚宽的get_security_info映射到Ptrade的get_stock_info
                'attribute_history': 'get_history',  # 聚宽的attribute_history映射到Ptrade的get_history
                'get_bars': 'get_history',  # 聚宽的get_bars映射到Ptrade的get_history
                'get_snapshot': 'get_snapshot'  # Ptrade支持的get_snapshot
            }
            
            # 交易API
            self.api_mapping.update({
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
            })
        
        # 需要移除的API（Ptrade不支持的API）
        self.removed_apis = {
            'set_option',
            'set_commission',
            'set_slippage',
            'set_price_limit',
            'set_order_cost'
        }
        
        # 需要特殊处理的API
        self.special_handlers = {
            # 可以添加特殊处理函数
        }
        
        # 导入映射 - Ptrade不需要导入语句
        self.import_mapping = {}
    
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
            
            # 添加必要的头部信息（不包含导入语句）
            ptrade_code = self._add_header(ptrade_code)
            
            # 确保生成符合Ptrade要求的策略结构
            ptrade_code = self._ensure_ptrade_structure(ptrade_code)
            
            # 清理重复内容
            ptrade_code = self._clean_duplicate_content(ptrade_code)
            
            # 整合定时任务函数逻辑到Ptrade标准函数中
            ptrade_code = self._integrate_timing_functions(ptrade_code)
            
            return ptrade_code
            
        except Exception as e:
            raise Exception(f"代码转换失败: {str(e)}")
    
    def _transform_ast(self, tree: ast.AST) -> ast.AST:
        """
        转换AST节点
        
        Args:
            tree: 原始AST树
            
        Returns:
            ast.AST: 转换后的AST树
        """
        # 创建转换器访问器
        transformer = JQToPtradeTransformer(self.api_mapping, self.special_handlers, self.import_mapping, self.removed_apis)
        return transformer.visit(tree)
    
    def _add_header(self, code: str) -> str:
        """
        添加必要的头部信息（不包含导入语句）
        
        Args:
            code: 转换后的代码
            
        Returns:
            str: 添加头部信息后的代码
        """
        header = '''# 自动生成的Ptrade策略代码
# 原始代码来自聚宽策略

'''
        return header + code
    
    def _ensure_ptrade_structure(self, code: str) -> str:
        """
        确保生成符合Ptrade要求的策略结构
        
        Args:
            code: 转换后的代码
            
        Returns:
            str: 符合Ptrade结构的代码
        """
        # 移除重复的头部信息
        if code.startswith('# 自动生成的Ptrade策略代码\n# 原始代码来自聚宽策略\n\n# 自动生成的Ptrade策略代码\n# 原始代码来自聚宽策略\n\n'):
            code = '# 自动生成的Ptrade策略代码\n# 原始代码来自聚宽策略\n\n' + code.split('\n\n', 2)[-1]
        
        # 确保有正确的函数结构
        required_functions = ['initialize', 'before_trading_start', 'handle_data', 'after_trading_end']
        existing_functions = []
        
        # 检查已存在的函数
        lines = code.split('\n')
        for line in lines:
            if line.startswith('def '):
                func_name = line.split('(')[0].replace('def ', '').strip()
                existing_functions.append(func_name)
        
        # 添加缺失的函数
        if 'initialize' not in existing_functions:
            # 在代码开头添加initialize函数
            init_func = '''def initialize(context):
    # 初始化
    pass

'''
            code = init_func + code
        
        if 'before_trading_start' not in existing_functions:
            # 在initialize函数后添加before_trading_start函数
            lines = code.split('\n')
            new_lines = []
            inserted = False
            for line in lines:
                new_lines.append(line)
                if line.strip() == 'def initialize(context):' and not inserted:
                    # 跳过initialize函数体
                    i = len(new_lines)
                    while i < len(lines) and (lines[i].strip() == '' or lines[i].startswith(' ') or lines[i].startswith('\t')):
                        new_lines.append(lines[i])
                        i += 1
                    # 添加before_trading_start函数
                    new_lines.append('')
                    new_lines.append('def before_trading_start(context, data):')
                    new_lines.append('    # 盘前处理')
                    new_lines.append('    pass')
                    new_lines.append('')
                    inserted = True
            if inserted:
                code = '\n'.join(new_lines)
            else:
                # 如果没有找到合适的位置，添加到代码末尾
                code = code.rstrip() + '\n\ndef before_trading_start(context, data):\n    # 盘前处理\n    pass\n'
        
        if 'handle_data' not in existing_functions:
            # 在代码末尾添加handle_data函数
            handle_func = '''
def handle_data(context, data):
    # 盘中处理
    pass
'''
            code = code.rstrip() + handle_func
        
        if 'after_trading_end' not in existing_functions:
            # 在代码末尾添加after_trading_end函数
            after_func = '''
def after_trading_end(context, data):
    # 收盘后处理
    pass
'''
            code = code.rstrip() + after_func
        
        # 修复函数调用中的语法错误
        lines = code.split('\n')
        fixed_lines = []
        for line in lines:
            # 修复缺少右括号的函数调用
            if ('run_daily(' in line or 'run_weekly(' in line) and line.count('(') > line.count(')'):
                # 确保行末有右括号
                line = line.rstrip() + ')'
            fixed_lines.append(line)
        code = '\n'.join(fixed_lines)
        
        return code
    
    def _clean_duplicate_content(self, code: str) -> str:
        """
        清理重复内容
        
        Args:
            code: 代码
            
        Returns:
            str: 清理后的代码
        """
        lines = code.split('\n')
        cleaned_lines = []
        seen_lines = set()
        
        for line in lines:
            # 跳过空行的重复检查
            if line.strip() == '':
                cleaned_lines.append(line)
                continue
                
            # 如果是函数定义行，重置seen_lines
            if line.startswith('def '):
                seen_lines = set()
                cleaned_lines.append(line)
                seen_lines.add(line.strip())
                continue
                
            # 如果是注释行，允许重复
            if line.strip().startswith('#'):
                cleaned_lines.append(line)
                continue
                
            # 检查是否已经见过这一行
            if line.strip() not in seen_lines:
                cleaned_lines.append(line)
                seen_lines.add(line.strip())
        
        return '\n'.join(cleaned_lines)
    
    def _integrate_timing_functions(self, code: str) -> str:
        """
        整合定时任务函数逻辑到Ptrade标准函数中
        
        Args:
            code: 代码
            
        Returns:
            str: 整合后的代码
        """
        # 移除导入语句
        code_lines = code.split('\n')
        filtered_lines = []
        for line in code_lines:
            if not line.startswith('import ') and not line.startswith('from ') and not 'import' in line.split():
                filtered_lines.append(line)
        code = '\n'.join(filtered_lines)
        
        # 替换全局变量引用
        code = code.replace('g.', 'context.')
        
        # 修复log替换错误
        code = code.replace('locontext.', 'log.')
        
        # 移除不支持的API调用
        for api in self.removed_apis:
            # 移除整行的API调用
            lines = code.split('\n')
            filtered_lines = []
            for line in lines:
                if not line.strip().startswith(api + '('):
                    filtered_lines.append(line)
            code = '\n'.join(filtered_lines)
        
        # 修正定时任务函数调用
        code = self._fix_timing_functions(code)
        
        # 修正API参数差异
        code = self._fix_api_parameters(code)
        
        # 修复语法错误
        code = self._fix_syntax_errors(code)
        
        # 修复缩进问题
        code = self._fix_indentation(code)
        
        # 确保正确的函数结构
        code = self._ensure_structure(code)
        
        return code
    
    def _fix_timing_functions(self, code: str) -> str:
        """修正定时任务函数调用"""
        import re
        # 修正run_daily和run_weekly调用，移除reference_security参数，并调整参数顺序以适应Ptrade
        lines = code.split('\n')
        fixed_lines = []
        
        for line in lines:
            if 'run_daily(' in line:
                # 移除reference_security参数
                line = re.sub(r',\\s*reference_security=[^,)]+', '', line)
                line = re.sub(r'reference_security=[^,)]+,\\s*', '', line)
                line = re.sub(r'reference_security=[^,)]+', '', line)
                # 调整run_daily参数顺序以适应Ptrade (需要context作为第一个参数)
                if 'run_daily(' in line and 'context' not in line.split('(')[1].split(',')[0]:
                    # 在函数名后添加context参数
                    line = line.replace('run_daily(', 'run_daily(context, ')
            elif 'run_weekly(' in line:
                # Ptrade不支持run_weekly，需要转换为run_daily或run_interval
                # 先移除reference_security参数
                line = re.sub(r',\\s*reference_security=[^,)]+', '', line)
                line = re.sub(r'reference_security=[^,)]+,\\s*', '', line)
                line = re.sub(r'reference_security=[^,)]+', '', line)
                # 将run_weekly转换为run_daily（作为简化处理）
                # 注意：weekday参数在Ptrade中被忽略
                line = line.replace('run_weekly(', 'run_daily(context, ')
            elif 'run_monthly(' in line:
                # Ptrade不支持run_monthly，需要转换为run_daily或run_interval
                line = re.sub(r',\\s*reference_security=[^,)]+', '', line)
                line = re.sub(r'reference_security=[^,)]+,\\s*', '', line)
                line = re.sub(r'reference_security=[^,)]+', '', line)
                # 将run_monthly转换为run_daily（作为简化处理）
                # 注意：monthday参数在Ptrade中被忽略
                line = line.replace('run_monthly(', 'run_daily(context, ')
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _fix_api_parameters(self, code: str) -> str:
        """修正API参数差异"""
        import re
        lines = code.split('\n')
        fixed_lines = []
        
        for line in lines:
            # 移除get_price中的frequency参数
            if 'get_price(' in line and 'frequency' in line:
                # Ptrade不使用frequency参数
                line = re.sub(r',\\s*frequency=[^,)]+', '', line)
                line = re.sub(r'frequency=[^,)]+,\\s*', '', line)
                line = re.sub(r'frequency=[^,)]+', '', line)
            
            # 移除多余的逗号（修复语法错误）
            line = re.sub(r'(get_price\([^)]*?),\s*,', r'\1,', line)
            line = re.sub(r'(get_history\([^)]*?),\s*,', r'\1,', line)
            
            # 移除skip_paused参数
            if 'skip_paused' in line:
                line = re.sub(r',\\s*skip_paused=[^,)]+', '', line)
                line = re.sub(r'skip_paused=[^,)]+,\\s*', '', line)
                line = re.sub(r'skip_paused=[^,)]+', '', line)
            
            # 移除panel参数
            if 'panel' in line and 'panel=' in line:
                line = re.sub(r',\\s*panel=[^,)]+', '', line)
                line = re.sub(r'panel=[^,)]+,\\s*', '', line)
                line = re.sub(r'panel=[^,)]+', '', line)
            
            # 修正get_all_securities为get_Ashares
            if 'get_all_securities(' in line:
                line = line.replace('get_all_securities(', 'get_Ashares(')
            
            # 修正get_security_info为get_stock_info
            if 'get_security_info(' in line:
                line = line.replace('get_security_info(', 'get_stock_info(')
            
            # 修正get_current_data为get_snapshot
            if 'get_current_data(' in line:
                line = line.replace('get_current_data(', 'get_snapshot(')
            
            # 修正portfolio属性
            if 'portfolio.available_cash' in line:
                line = line.replace('portfolio.available_cash', 'portfolio.cash')
            
            if 'portfolio.portfolio_value' in line:
                line = line.replace('portfolio.portfolio_value', 'portfolio.total_value')
            
            # 修正持仓属性
            if 'closeable_amount' in line:
                line = line.replace('closeable_amount', 'amount')
            
            # 标准化证券代码后缀
            line = self._standardize_security_code(line)
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _standardize_security_code(self, line: str) -> str:
        """标准化证券代码后缀"""
        import re
        # 将 .XSHG 替换为 .SS
        line = re.sub(r'\.XSHG(?![a-zA-Z0-9])', '.SS', line)
        # 将 .XSHE 替换为 .SZ
        line = re.sub(r'\.XSHE(?![a-zA-Z0-9])', '.SZ', line)
        return line
    
    def _fix_syntax_errors(self, code: str) -> str:
        """修复语法错误"""
        import re
        lines = code.split('\n')
        fixed_lines = []
        
        for line in lines:
            # 修复多余的逗号
            line = re.sub(r'(get_price\([^)]*?),\s*,', r'\1,', line)
            line = re.sub(r'(get_history\([^)]*?),\s*,', r'\1,', line)
            line = re.sub(r'(get_Ashares\([^)]*?),\s*,', r'\1,', line)
            line = re.sub(r'(get_index_stocks\([^)]*?),\s*,', r'\1,', line)
            line = re.sub(r'(get_industry_stocks\([^)]*?),\s*,', r'\1,', line)
            line = re.sub(r'(get_concept_stocks\([^)]*?),\s*,', r'\1,', line)
            line = re.sub(r'(get_fundamentals\([^)]*?),\s*,', r'\1,', line)
            line = re.sub(r'(get_stock_info\([^)]*?),\s*,', r'\1,', line)
            line = re.sub(r'(get_snapshot\([^)]*?),\s*,', r'\1,', line)
            # 修复定时任务函数的多余逗号
            line = re.sub(r'(run_daily\([^)]*?),\s*,', r'\1,', line)
            line = re.sub(r'(run_weekly\([^)]*?),\s*,', r'\1,', line)
            line = re.sub(r'(run_monthly\([^)]*?),\s*,', r'\1,', line)
            # 修复末尾多余的逗号
            line = re.sub(r'(get_price\([^)]*?),\s*\)', r'\1)', line)
            line = re.sub(r'(get_history\([^)]*?),\s*\)', r'\1)', line)
            line = re.sub(r'(get_Ashares\([^)]*?),\s*\)', r'\1)', line)
            line = re.sub(r'(get_index_stocks\([^)]*?),\s*\)', r'\1)', line)
            line = re.sub(r'(get_industry_stocks\([^)]*?),\s*\)', r'\1)', line)
            line = re.sub(r'(get_concept_stocks\([^)]*?),\s*\)', r'\1)', line)
            line = re.sub(r'(get_fundamentals\([^)]*?),\s*\)', r'\1)', line)
            line = re.sub(r'(get_stock_info\([^)]*?),\s*\)', r'\1)', line)
            line = re.sub(r'(get_snapshot\([^)]*?),\s*\)', r'\1)', line)
            # 修复定时任务函数末尾的多余逗号
            line = re.sub(r'(run_daily\([^)]*?),\s*\)', r'\1)', line)
            line = re.sub(r'(run_weekly\([^)]*?),\s*\)', r'\1)', line)
            line = re.sub(r'(run_monthly\([^)]*?),\s*\)', r'\1)', line)
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _fix_indentation(self, code: str) -> str:
        """修复缩进问题"""
        lines = code.split('\n')
        fixed_lines = []
        
        for line in lines:
            # 修复不正确的缩进
            stripped_line = line.lstrip()
            if stripped_line:
                # 计算当前缩进
                current_indent = len(line) - len(stripped_line)
                
                # 如果是2个或3个空格的缩进，调整为4个空格的倍数
                if current_indent in [2, 3, 6, 7]:
                    # 调整为最接近的4的倍数
                    new_indent = ((current_indent // 4) + 1) * 4
                    line = ' ' * new_indent + stripped_line
                elif current_indent == 1:
                    # 调整为4个空格
                    line = '    ' + stripped_line
                elif current_indent % 4 != 0:
                    # 其他不规则缩进调整为4的倍数
                    new_indent = (current_indent // 4) * 4
                    line = ' ' * new_indent + stripped_line
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _ensure_structure(self, code: str) -> str:
        """确保正确的函数结构"""
        # 确保有initialize函数
        if 'def initialize(' not in code:
            init_func = '''def initialize(context):
    pass

'''
            code = init_func + code
        
        # 确保有before_trading_start函数
        if 'def before_trading_start(' not in code:
            # 在initialize函数后添加
            lines = code.split('\n')
            new_lines = []
            inserted = False
            for line in lines:
                new_lines.append(line)
                if line.strip() == 'def initialize(context):' and not inserted:
                    # 跳过initialize函数体
                    i = len(new_lines)
                    while i < len(lines) and (lines[i].strip() == '' or lines[i].startswith(' ') or lines[i].startswith('\t')):
                        new_lines.append(lines[i])
                        i += 1
                    # 添加before_trading_start函数
                    new_lines.append('')
                    new_lines.append('def before_trading_start(context, data):')
                    new_lines.append('    pass')
                    new_lines.append('')
                    inserted = True
            if not inserted:
                # 如果没有找到合适的位置，添加到代码末尾
                code = code.rstrip() + '\n\ndef before_trading_start(context, data):\n    pass\n'
            else:
                code = '\n'.join(new_lines)
        
        # 确保有handle_data函数
        if 'def handle_data(' not in code:
            code = code.rstrip() + '\n\ndef handle_data(context, data):\n    pass\n'
        
        # 确保有after_trading_end函数
        if 'def after_trading_end(' not in code:
            code = code.rstrip() + '\n\ndef after_trading_end(context, data):\n    pass\n'
        
        return code

class JQToPtradeTransformer(ast.NodeTransformer):
    """聚宽到Ptrade AST转换器"""
    
    def __init__(self, api_mapping: Dict[str, str], special_handlers: Dict[str, Any], import_mapping: Dict[str, str], removed_apis: set):
        self.api_mapping = api_mapping
        self.special_handlers = special_handlers
        self.import_mapping = import_mapping
        self.removed_apis = removed_apis
    
    def visit_Call(self, node: ast.Call) -> Optional[ast.AST]:
        """
        转换函数调用节点
        
        Args:
            node: 函数调用节点
            
        Returns:
            ast.AST: 转换后的节点
        """
        # 如果是函数调用，检查是否需要映射
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
                    # 如果是完整路径映射，需要特殊处理
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
        """
        转换导入语句 - Ptrade不需要导入语句，直接移除
        """
        # 返回None来移除节点
        return None
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> Optional[ast.AST]:
        """
        转换from导入语句 - Ptrade不需要导入语句，直接移除
        """
        # 返回None来移除节点
        return None
    
    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        """
        转换赋值语句
        
        Args:
            node: 赋值节点
            
        Returns:
            ast.AST: 转换后的节点
        """
        # 处理 g.xxx = ... 这样的全局变量赋值
        for target in node.targets:
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                if target.value.id == 'g':
                    # 将 g.xxx 转换为 context.xxx
                    target.value.id = 'context'
        return self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name) -> ast.AST:
        """
        转换名称引用
        
        Args:
            node: 名称节点
            
        Returns:
            ast.AST: 转换后的节点
        """
        # 处理对 g 的直接引用
        if node.id == 'g':
            # 将 g 转换为 context
            node.id = 'context'
        return self.generic_visit(node)
    
    def visit_Expr(self, node: ast.Expr) -> Optional[ast.AST]:
        """
        转换表达式语句
        
        Args:
            node: 表达式节点
            
        Returns:
            ast.AST: 转换后的节点
        """
        # 如果表达式包含需要移除的函数调用，移除整个表达式
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            if node.value.func.id in self.removed_apis:
                return None
        
        # 继续遍历子节点
        return self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        """
        转换函数定义
        
        Args:
            node: 函数定义节点
            
        Returns:
            ast.AST: 转换后的节点
        """
        # 不再需要转换聚宽的定时任务函数参数，因为这些函数的逻辑会被整合到Ptrade标准函数中
        # 继续遍历子节点
        return self.generic_visit(node)

# 使用示例
if __name__ == "__main__":
    # 示例聚宽代码
    sample_jq_code = '''
import jqdata

def initialize(context):
    # 初始化函数
    g.security = '000001.XSHE'
    set_benchmark('000300.XSHG')

def handle_data(context, data):
    # 处理数据函数
    order('000001.XSHE', 100)
    log.info('下单完成')
'''
    
    # 创建转换器
    converter = JQToPtradeConverter()
    
    # 转换代码
    try:
        ptrade_code = converter.convert(sample_jq_code)
        print("转换后的Ptrade代码:")
        print(ptrade_code)
    except Exception as e:
        print(f"转换失败: {e}")