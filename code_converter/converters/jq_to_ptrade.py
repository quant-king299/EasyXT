"""
聚宽到Ptrade代码转换器
"""
import ast
import sys
import json
import os
from typing import Dict, List, Any, Optional

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
                'get_current_data': 'get_current_data',
                'get_fundamentals': 'get_fundamentals',
                'get_index_stocks': 'get_index_stocks',
                'get_industry_stocks': 'get_industry_stocks',
                'get_concept_stocks': 'get_concept_stocks',
                'get_all_securities': 'get_all_securities',
                'get_security_info': 'get_security_info',
                'attribute_history': 'get_price',  # 聚宽的attribute_history映射到Ptrade的get_price
                'get_bars': 'get_price',  # 聚宽的get_bars映射到Ptrade的get_price
                
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
        required_functions = ['initialize', 'before_trading_start', 'handle_data']
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
            code = '\n'.join(new_lines)
        
        if 'handle_data' not in existing_functions:
            # 在代码末尾添加handle_data函数
            handle_func = '''
def handle_data(context, data):
    # 盘中处理
    pass
'''
            code = code.rstrip() + handle_func
        
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
        # 检查是否是聚宽的定时任务函数，需要转换为Ptrade兼容的函数
        function_name = node.name
        if function_name in ['before_market_open', 'market_open', 'after_market_close']:
            # 保持函数定义，但确保参数正确
            # Ptrade函数通常接收context和data参数
            if len(node.args.args) == 1 and node.args.args[0].arg == 'context':
                # 添加data参数
                node.args.args.append(ast.arg(arg='data', annotation=None))
        
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