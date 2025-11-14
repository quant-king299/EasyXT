from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
import inspect
from typing import Any, Dict
from qka.trade import create_trader
import uvicorn
import uuid
import hashlib

class QMTServer:
    def __init__(self, account_id: str, mini_qmt_path: str, host: str = "0.0.0.0", port: int = 8000, token: str = None):
        """初始化交易服务器
        Args:
            account_id: 账户ID
            mini_qmt_path: miniQMT路径
            host: 服务器地址，默认0.0.0.0
            port: 服务器端口，默认8000
            token: 可选的自定义token
        """
        self.account_id = account_id
        self.mini_qmt_path = mini_qmt_path
        self.host = host
        self.port = port
        self.app = FastAPI()
        self.trader = None
        self.account = None
        self.token = token if token else self.generate_token()  # 使用自定义token或生成固定token
        print(f"\n授权Token: {self.token}\n")  # 打印token供客户端使用

    def generate_token(self) -> str:
        """生成基于机器码的固定token"""
        # 获取机器码（例如MAC地址）
        mac = uuid.getnode()
        # 将机器码转换为字符串
        mac_str = str(mac)
        # 使用SHA256哈希生成固定长度的token
        token = hashlib.sha256(mac_str.encode()).hexdigest()
        return token

    async def verify_token(self, x_token: str = Header(...)):
        """验证token的依赖函数"""
        if x_token != self.token:
            raise HTTPException(status_code=401, detail="无效的Token")
        return x_token

    def init_trader(self):
        """初始化交易对象"""
        self.trader, self.account = create_trader(self.account_id, self.mini_qmt_path)

    def convert_to_dict(self, obj):
        """将结果转换为可序列化的字典"""
        # 如果是基本类型，直接返回
        if isinstance(obj, (int, float, str, bool)):
            return obj
        # 如果已经是字典类型，直接返回
        elif isinstance(obj, dict):
            return obj
        # 如果是列表或元组，递归转换每个元素
        elif isinstance(obj, (list, tuple)):
            return [self.convert_to_dict(item) for item in obj]
        # 如果是自定义对象，获取所有公开属性
        elif hasattr(obj, '__dir__'):
            attrs = obj.__dir__()
            # 过滤掉内部属性和方法
            public_attrs = {attr: getattr(obj, attr) 
                           for attr in attrs 
                           if not attr.startswith('_') and not callable(getattr(obj, attr))}
            return public_attrs
        # 其他类型直接返回
        return str(obj)  # 将无法处理的类型转换为字符串

    def convert_method_to_endpoint(self, method_name: str, method):
        """将 XtQuantTrader 方法转换为 FastAPI 端点"""
        sig = inspect.signature(method)
        param_names = list(sig.parameters.keys())
        
        # 创建动态的请求模型
        class_fields = {
            '__annotations__': {}  # 添加类型注解字典
        }
        
        for param in param_names:
            if param in ['self', 'account']:
                continue
            class_fields['__annotations__'][param] = Any
            class_fields[param] = None

        RequestModel = type(f'{method_name}Request', (BaseModel,), class_fields)

        async def endpoint(request: RequestModel, token: str = Depends(self.verify_token)):
            try:
                params = request.dict(exclude_unset=True)
                if 'account' in param_names:
                    params['account'] = self.account
                result = getattr(self.trader, method_name)(**params)
                converted_result = self.convert_to_dict(result)
                return {'success': True, 'data': converted_result}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        self.app.post(f'/api/{method_name}')(endpoint)

    def setup_routes(self):
        """设置所有路由"""
        trader_methods = inspect.getmembers(
            self.trader.__class__, 
            predicate=lambda x: inspect.isfunction(x) or inspect.ismethod(x)
        )
        
        excluded_methods = {'__init__', '__del__', 'register_callback', 'start', 'stop',
                          'connect', 'sleep', 'run_forever', 'set_relaxed_response_order_enabled'}
        
        for method_name, method in trader_methods:
            if not method_name.startswith('_') and method_name not in excluded_methods:
                self.convert_method_to_endpoint(method_name, method)

    def start(self):
        """启动服务器"""
        self.init_trader()
        self.setup_routes()
        uvicorn.run(self.app, host=self.host, port=self.port)

def qmt_server(account_id: str, mini_qmt_path: str, host: str = "0.0.0.0", port: int = 8000, token: str = None):
    """快速创建并启动服务器的便捷函数"""
    server = QMTServer(account_id, mini_qmt_path, host, port, token)
    server.start()