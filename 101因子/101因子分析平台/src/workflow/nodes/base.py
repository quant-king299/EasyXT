"""
工作流节点基类
定义工作流中所有节点的基类和接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd


class BaseNode(ABC):
    """
    工作流节点基类
    所有工作流节点都应该继承这个类
    """
    
    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        """
        初始化节点
        
        Args:
            node_id: 节点唯一标识
            name: 节点名称
            params: 节点参数
        """
        self.node_id = node_id
        self.name = name
        self.params = params or {}
        self.inputs = {}
        self.outputs = {}
        self.metadata = {}
    
    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行节点逻辑
        
        Args:
            input_data: 输入数据字典
            
        Returns:
            Dict: 输出数据字典
        """
        pass
    
    def set_input(self, key: str, value: Any):
        """
        设置输入数据
        
        Args:
            key: 输入键名
            value: 输入值
        """
        self.inputs[key] = value
    
    def get_output(self, key: str) -> Any:
        """
        获取输出数据
        
        Args:
            key: 输出键名
            
        Returns:
            Any: 输出值
        """
        return self.outputs.get(key)
    
    def validate(self) -> bool:
        """
        验证节点配置是否正确
        
        Returns:
            bool: 验证结果
        """
        return True
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        获取节点元数据
        
        Returns:
            Dict: 元数据
        """
        return self.metadata


class DataNode(BaseNode):
    """数据节点基类"""
    
    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """数据节点执行逻辑（通常不需要输入）"""
        return self._execute_data(input_data)
    
    @abstractmethod
    def _execute_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行数据操作的具体逻辑"""
        pass


class TransformNode(BaseNode):
    """变换节点基类"""
    
    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """变换节点执行逻辑"""
        if not self.validate_inputs(input_data):
            raise ValueError("输入数据验证失败")
        return self._execute_transform(input_data)
    
    def validate_inputs(self, input_data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        return len(input_data) > 0
    
    @abstractmethod
    def _execute_transform(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行变换操作的具体逻辑"""
        pass


class AnalysisNode(BaseNode):
    """分析节点基类"""
    
    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析节点执行逻辑"""
        if not self.validate_inputs(input_data):
            raise ValueError("输入数据验证失败")
        return self._execute_analysis(input_data)
    
    def validate_inputs(self, input_data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        return len(input_data) > 0
    
    @abstractmethod
    def _execute_analysis(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行分析操作的具体逻辑"""
        pass


class OutputNode(BaseNode):
    """输出节点基类"""
    
    def __init__(self, node_id: str, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, name, params)
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """输出节点执行逻辑"""
        if not self.validate_inputs(input_data):
            raise ValueError("输入数据验证失败")
        return self._execute_output(input_data)
    
    def validate_inputs(self, input_data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        return len(input_data) > 0
    
    @abstractmethod
    def _execute_output(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行输出操作的具体逻辑"""
        pass