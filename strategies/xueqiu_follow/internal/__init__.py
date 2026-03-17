"""
核心业务逻辑模块
"""

# 延迟导入 - 只在需要时才导入
# 避免__init__.py时就执行导入，防止路径问题

def __getattr__(name):
    """延迟导入支持"""
    import sys
    import os

    # 确保父目录在路径中
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    # 确保utils在路径中
    utils_dir = os.path.join(parent_dir, 'utils')
    if utils_dir not in sys.path:
        sys.path.insert(0, utils_dir)

    if name == 'StrategyEngine':
        from internal.strategy_engine import StrategyEngine
        return StrategyEngine
    elif name == 'XueqiuFollowStrategy':
        from internal.strategy_engine import XueqiuFollowStrategy
        return XueqiuFollowStrategy
    elif name == 'TradeExecutor':
        from internal.trade_executor import TradeExecutor
        return TradeExecutor
    elif name == 'OrderStatus':
        from internal.trade_executor import OrderStatus
        return OrderStatus
    elif name == 'OrderType':
        from internal.trade_executor import OrderType
        return OrderType
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    'StrategyEngine',
    'XueqiuFollowStrategy',
    'TradeExecutor',
    'OrderStatus',
    'OrderType'
]