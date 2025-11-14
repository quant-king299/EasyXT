"""
代码解析工具
"""
import ast
from typing import List, Dict, Any

class CodeParser:
    """代码解析器"""
    
    @staticmethod
    def parse_code(code: str) -> ast.AST:
        """
        解析代码为AST
        
        Args:
            code: 源代码字符串
            
        Returns:
            ast.AST: 解析后的AST树
        """
        return ast.parse(code)
    
    @staticmethod
    def extract_functions(tree: ast.AST) -> List[str]:
        """
        提取代码中的函数名
        
        Args:
            tree: AST树
            
        Returns:
            List[str]: 函数名列表
        """
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
        return functions
    
    @staticmethod
    def extract_imports(tree: ast.AST) -> List[Dict[str, Any]]:
        """
        提取代码中的导入语句
        
        Args:
            tree: AST树
            
        Returns:
            List[Dict[str, Any]]: 导入信息列表
        """
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'type': 'import',
                        'name': alias.name,
                        'alias': alias.asname
                    })
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.append({
                        'type': 'from',
                        'module': node.module,
                        'name': alias.name,
                        'alias': alias.asname
                    })
        return imports