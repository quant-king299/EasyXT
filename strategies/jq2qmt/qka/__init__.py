"""
QKA - 量化交易框架

统一的访问接口，支持 qka.xxx 的访问模式
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("qka")
except PackageNotFoundError:
    __version__ = "0.1.0"  # fallback version

# 核心功能直接导入
from qka.core.data import Data
from qka.core.backtest import Backtest
from qka.core.strategy import Strategy

# 子模块导入
from qka import core, utils, mcp

# 交易相关（有依赖的模块暂时不导入，避免导入错误）
# from qka.brokers.trade import create_trader
# from qka.brokers.client import QMTClient
# from qka.brokers.server import QMTServer

__all__ = [
    # 核心功能
    'Data', 'Backtest', 'Strategy',
    # 子模块
    'core', 'utils', 'mcp'
]