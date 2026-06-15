"""
EasyXT - xtquant的简化API封装
让用户更方便快捷地调用xtquant功能
"""

__version__ = "1.0.0"
__author__ = "CodeBuddy"

# ============================================================
# ⚠️ 线程安全：尽早对 xtdata 下载方法进行 monkey-patch
# 防止 GUI、策略、工具等任何代码直接调用 xtdata.download_history_data
# 或 download_history_data2 时因并发导致卡死
# ============================================================
import threading
import sys

_download_lock = threading.RLock()

def _patch_xtdata_download():
    """对 xtdata 的下载方法进行线程安全包装（RLock 可重入）"""
    try:
        import xtquant.xtdata as xtdata

        _orig_download = xtdata.download_history_data
        _orig_download2 = xtdata.download_history_data2

        def locked_download(*args, **kwargs):
            with _download_lock:
                return _orig_download(*args, **kwargs)

        def locked_download2(*args, **kwargs):
            with _download_lock:
                return _orig_download2(*args, **kwargs)

        xtdata.download_history_data = locked_download
        xtdata.download_history_data2 = locked_download2

        # 同时更新 sys.modules，确保后续 import xtquant.xtdata 获取补丁版本
        sys.modules['xtquant.xtdata'].download_history_data = locked_download
        sys.modules['xtquant.xtdata'].download_history_data2 = locked_download2

        print("[EasyXT] xtdata download functions patched (global RLock)")
        return True
    except ImportError:
        return False

_patch_applied = _patch_xtdata_download()

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

def _get_ai_assistant():
    from .ai_assistant import EasyXTAI
    return EasyXTAI()

# 创建全局实例
api = None
extended_api = None
advanced_api = None
ai_assistant = None

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

def get_ai_assistant(token=None):
    """获取AI助手实例"""
    global ai_assistant
    if ai_assistant is None:
        ai_assistant = _get_ai_assistant()
    return ai_assistant

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
    elif name == 'EasyXTAI':
        from .ai_assistant import EasyXTAI
        return EasyXTAI
    elif name == 'api':
        return get_api()
    elif name == 'extended_api':
        return get_extended_api()
    elif name == 'advanced_api':
        return get_advanced_api()
    elif name == 'ai_assistant':
        return get_ai_assistant()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

# 导出主要接口
__all__ = [
    'EasyXT',
    'ExtendedAPI',
    'AdvancedTradeAPI',
    'DataAPI',
    'TradeAPI',
    'EasyXTAI',
    'get_api',
    'get_extended_api',
    'get_advanced_api',
    'get_ai_assistant',
    'api',
    'extended_api',
    'advanced_api',
    'ai_assistant'
]