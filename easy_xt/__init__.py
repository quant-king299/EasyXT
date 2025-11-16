"""
EasyXT - xtquant的简化API封装
让用户更方便快捷地调用xtquant功能
"""

__version__ = "1.0.0"
__author__ = "CodeBuddy"

# 显示作者信息
print("作者微信: www_ptqmt_com")
print("欢迎关注微信公众号: 王者quant")

# 延迟导入避免循环依赖
def _get_api():
    from .api import EasyXT
    return EasyXT()

def _get_extended_api():
    from .extended_api import ExtendedAPI
    return ExtendedAPI()

def _get_advanced_api():
    from .advanced_trade_api import AdvancedTradeAPI
    return AdvancedTradeAPI()

# 创建全局实例
api = None
extended_api = None
advanced_api = None

def get_api():
    """获取全局API实例"""
    global api
    if api is None:
        api = _get_api()
    return api

def get_extended_api():
    """获取扩展API实例（包含完整的trader功能）"""
    global extended_api
    if extended_api is None:
        extended_api = _get_extended_api()
    return extended_api

def get_advanced_api():
    """获取高级交易API实例"""
    global advanced_api
    if advanced_api is None:
        advanced_api = _get_advanced_api()
    return advanced_api

# 为了向后兼容，在模块级别提供类的导入
def __getattr__(name):
    if name == 'EasyXT':
        from .api import EasyXT
        return EasyXT
    elif name == 'ExtendedAPI':
        from .extended_api import ExtendedAPI
        return ExtendedAPI
    elif name == 'AdvancedTradeAPI':
        from .advanced_trade_api import AdvancedTradeAPI
        return AdvancedTradeAPI
    elif name == 'DataAPI':
        from .data_api import DataAPI
        return DataAPI
    elif name == 'TradeAPI':
        from .trade_api import TradeAPI
        return TradeAPI
    elif name == 'api':
        return get_api()
    elif name == 'extended_api':
        return get_extended_api()
    elif name == 'advanced_api':
        return get_advanced_api()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

# 导出主要接口
__all__ = [
    'EasyXT',
    'ExtendedAPI',
    'AdvancedTradeAPI',
    'DataAPI', 
    'TradeAPI',
    'get_api',
    'get_extended_api',
    'get_advanced_api',
    'api',
    'extended_api',
    'advanced_api'
]