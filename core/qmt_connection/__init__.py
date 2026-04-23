"""
QMT连接管理器

提供统一的QMT连接检查和自动登录功能
"""

from .qmt_connection import (
    QMTConnectionManager,
    get_qmt_manager,
    ensure_qmt_logged_in,
    get_qmt_status,
    require_qmt_login
)

__all__ = [
    'QMTConnectionManager',
    'get_qmt_manager',
    'ensure_qmt_logged_in',
    'get_qmt_status',
    'require_qmt_login'
]
