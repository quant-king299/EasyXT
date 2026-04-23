"""
QMT连接管理器

提供统一的QMT连接检查和自动登录功能
用于策略启动前和数据获取前的QMT状态检查
"""

import logging
import time
from typing import Optional

try:
    from core.auto_login import QMTAutoLogin
except ImportError:
    QMTAutoLogin = None


class QMTConnectionManager:
    """QMT连接管理器（单例模式）"""

    _instance = None
    _auto_login = None
    _last_check_time = 0
    _check_interval = 30  # 每30秒检查一次，避免频繁检查

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.logger = logging.getLogger(__name__)
        self._auto_login = None

        # 延迟初始化QMTAutoLogin（避免导入错误）
        if QMTAutoLogin:
            try:
                self._auto_login = QMTAutoLogin()
            except Exception as e:
                self.logger.warning(f"QMT自动登录初始化失败: {e}")

    def ensure_qmt_logged_in(self, auto_login: bool = True, timeout: int = 60) -> bool:
        """
        确保QMT已登录

        Args:
            auto_login: 如果QMT未登录，是否自动登录
            timeout: 登录超时时间（秒）

        Returns:
            bool: QMT是否已登录（或登录成功）
        """
        current_time = time.time()

        # 避免频繁检查（30秒内不重复检查）
        if current_time - self._last_check_time < self._check_interval:
            return True

        self._last_check_time = current_time

        try:
            # 检查QMT是否在运行
            if not self._is_qmt_running():
                self.logger.info("QMT未运行")
                if auto_login and self._auto_login:
                    self.logger.info("正在启动并登录QMT...")
                    return self._auto_login.login(restart=False, timeout=timeout)
                else:
                    self.logger.warning("QMT未运行且未启用自动登录")
                    return False

            # 检查QMT是否已登录
            if not self._is_qmt_logged_in():
                self.logger.info("QMT未登录")
                if auto_login and self._auto_login:
                    self.logger.info("正在自动登录QMT...")
                    return self._auto_login.login(restart=False, timeout=timeout)
                else:
                    self.logger.warning("QMT未登录且未启用自动登录")
                    return False

            self.logger.debug("QMT已登录")
            return True

        except Exception as e:
            self.logger.error(f"检查QMT状态失败: {e}")
            return False

    def _is_qmt_running(self) -> bool:
        """检查QMT是否在运行"""
        if not self._auto_login:
            return False

        try:
            return self._auto_login._is_running() is not None
        except Exception:
            return False

    def _is_qmt_logged_in(self) -> bool:
        """检查QMT是否已登录"""
        if not self._auto_login:
            return False

        try:
            app = self._auto_login._is_running()
            if app:
                return self._auto_login._check_logged_in(app)
            return False
        except Exception:
            return False

    def get_qmt_status(self) -> dict:
        """
        获取QMT状态信息

        Returns:
            dict: {
                'running': bool,  # QMT是否在运行
                'logged_in': bool,  # QMT是否已登录
                'can_login': bool   # 是否可以自动登录
            }
        """
        return {
            'running': self._is_qmt_running(),
            'logged_in': self._is_qmt_logged_in(),
            'can_login': self._auto_login is not None
        }


# 全局单例实例
_qmt_manager = None


def get_qmt_manager() -> QMTConnectionManager:
    """获取QMT连接管理器单例"""
    global _qmt_manager
    if _qmt_manager is None:
        _qmt_manager = QMTConnectionManager()
    return _qmt_manager


def ensure_qmt_logged_in(auto_login: bool = True, timeout: int = 60) -> bool:
    """
    确保QMT已登录（便捷函数）

    Args:
        auto_login: 如果QMT未登录，是否自动登录
        timeout: 登录超时时间（秒）

    Returns:
        bool: QMT是否已登录（或登录成功）

    使用示例:
        >>> from core.qmt_connection import ensure_qmt_logged_in
        >>> # 在策略启动前调用
        >>> if ensure_qmt_logged_in():
        >>>     strategy.run()
        >>> else:
        >>>     print("QMT未登录，无法启动策略")
    """
    manager = get_qmt_manager()
    return manager.ensure_qmt_logged_in(auto_login=auto_login, timeout=timeout)


def get_qmt_status() -> dict:
    """
    获取QMT状态信息（便捷函数）

    Returns:
        dict: QMT状态信息

    使用示例:
        >>> from core.qmt_connection import get_qmt_status
        >>> status = get_qmt_status()
        >>> print(f"QMT运行: {status['running']}")
        >>> print(f"QMT登录: {status['logged_in']}")
    """
    manager = get_qmt_manager()
    return manager.get_qmt_status()


# 装饰器：确保QMT已登录
def require_qmt_login(auto_login: bool = True):
    """
    装饰器：确保QMT已登录再执行函数

    Args:
        auto_login: 如果QMT未登录，是否自动登录

    使用示例:
        >>> from core.qmt_connection import require_qmt_login
        >>>
        >>> @require_qmt_login()
        >>> def my_strategy():
        >>>     # 这个函数执行前会自动检查QMT状态
        >>>     api = get_api()
        >>>     data = api.get_stock_data()
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 确保QMT已登录
            if not ensure_qmt_logged_in(auto_login=auto_login):
                raise Exception("QMT未登录，无法执行函数")

            # 执行原函数
            return func(*args, **kwargs)

        return wrapper
    return decorator
