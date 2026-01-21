import requests
from typing import Any


class QMTClient:
    """QMT客户端最小内核版本 - 仅保留client.api核心功能"""

    def __init__(self, base_url: str = "http://localhost:8000", token: str = None):
        """初始化交易客户端

        Args:
            base_url: API服务器地址，默认为本地8000端口
            token: 访问令牌，必须与服务器的token一致
        """
        if not token:
            raise ValueError("必须提供访问令牌(token)")

        self.base_url = base_url.rstrip('/')
        self.token = token
        self.session = requests.Session()
        self.headers = {"X-Token": self.token}

    def api(self, method_name: str, **params) -> Any:
        """通用调用接口方法

        Args:
            method_name: 要调用的接口名称
            **params: 接口参数，作为关键字参数传入

        Returns:
            接口返回的数据

        Raises:
            Exception: API调用失败或服务器返回错误
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/{method_name}",
                json=params or {},
                headers=self.headers
            )
            response.raise_for_status()
            result = response.json()

            if not result.get('success'):
                raise Exception(f"API调用失败: {result.get('detail')}")

            return result.get('data')

        except requests.RequestException as e:
            raise Exception(f"网络请求失败: {str(e)}")
        except Exception as e:
            raise Exception(f"调用 {method_name} 失败: {str(e)}")