"""
代码生成工具
"""
import ast
from typing import List, Dict, Any

class CodeGenerator:
    """代码生成器"""
    
    @staticmethod
    def generate_code(tree: ast.AST) -> str:
        """
        将AST树生成代码
        
        Args:
            tree: AST树
            
        Returns:
            str: 生成的代码字符串
        """
        return ast.unparse(tree)
    
    @staticmethod
    def add_imports(code: str, imports: List[str]) -> str:
        """
        添加导入语句到代码开头
        
        Args:
            code: 原始代码
            imports: 导入语句列表
            
        Returns:
            str: 添加导入语句后的代码
        """
        import_section = '\n'.join(imports) + '\n\n'
        return import_section + code
    
    @staticmethod
    def add_header(code: str, header: str) -> str:
        """
        添加头部信息到代码
        
        Args:
            code: 原始代码
            header: 头部信息
            
        Returns:
            str: 添加头部信息后的代码
        """
        return header + '\n' + code