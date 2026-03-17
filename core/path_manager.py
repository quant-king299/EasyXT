"""
统一路径管理模块
解决项目中 sys.path.insert() 到处都是的问题

使用方法：
    from core.path_manager import init_paths, get_project_root

    # 初始化路径（幂等性，多次调用只生效一次）
    init_paths()

    # 获取项目根目录
    root = get_project_root()

    # 获取相对路径
    config_path = get_path('config', 'unified_config.json')
"""
import sys
import os
from pathlib import Path
from typing import Optional


class PathManager:
    """
    路径管理器 - 单例模式

    功能：
    1. 自动检测项目根目录
    2. 一次性设置所有Python路径
    3. 提供便捷的路径获取方法
    4. 幂等性设计，多次调用不重复添加路径
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化路径管理器（只执行一次）"""
        if self._initialized:
            return

        # 先初始化logger
        try:
            import logging
            self.logger = logging.getLogger(__name__)
        except:
            self.logger = None

        # 自动检测项目根目录
        self.project_root = self._find_project_root()

        # 一次性设置所有需要的路径
        self._setup_paths()

        self._initialized = True

        # 记录日志（如果可用）
        if self.logger:
            self.logger.info(f"✅ PathManager initialized: project_root={self.project_root}")

    def _find_project_root(self) -> Path:
        """
        自动查找项目根目录

        查找标志：同时包含以下目录
        - easy_xt/
        - core/
        - strategies/

        Returns:
            Path: 项目根目录
        """
        # 从当前文件开始向上查找
        current = Path(__file__).resolve().parent

        # 向上查找，最多找6层
        for _ in range(6):
            # 检查是否同时包含这三个关键目录
            if (current / "easy_xt").exists() and \
               (current / "core").exists() and \
               (current / "strategies").exists():
                return current

            # 继续向上查找
            current = current.parent

        # 如果找不到，返回当前文件的上两层（core的上两层是项目根）
        fallback = Path(__file__).parent.parent
        if self.logger:
            self.logger.warning(f"⚠️ Could not find project root markers, using fallback: {fallback}")
        return fallback

    def _setup_paths(self):
        """
        一次性设置所有Python路径

        只执行一次，避免重复添加相同的路径
        """
        # 需要添加到 sys.path 的目录
        paths_to_add = [
            self.project_root,                    # 项目根目录
            self.project_root / "easy_xt",        # EasyXT模块
            self.project_root / "core",           # 核心模块
            self.project_root / "core" / "config", # 配置模块
            self.project_root / "core" / "data_manager", # 数据管理模块
            self.project_root / "core" / "alpha_analysis", # Alpha分析模块
            self.project_root / "strategies",     # 策略模块
        ]

        # 添加路径（避免重复）
        for path in paths_to_add:
            path_str = str(path)
            if path_str not in sys.path:
                sys.path.insert(0, path_str)
                if self.logger:
                    self.logger.debug(f"Added to sys.path: {path_str}")

        if self.logger:
            self.logger.info(f"✅ Setup complete: {len(paths_to_add)} paths configured")

    def get_path(self, *parts) -> Path:
        """
        获取相对于项目根目录的路径

        Args:
            *parts: 路径组成部分

        Returns:
            Path: 完整路径

        Examples:
            >>> get_path('config', 'unified_config.json')
            Path('C:/.../miniqmt扩展/config/unified_config.json')

            >>> get_path('strategies', 'xueqiu_follow')
            Path('C:/.../miniqmt扩展/strategies/xueqiu_follow')
        """
        return self.project_root.joinpath(*parts)

    def get_easyxt_path(self) -> Path:
        """获取easy_xt目录"""
        return self.project_root / "easy_xt"

    def get_core_path(self) -> Path:
        """获取core目录"""
        return self.project_root / "core"

    def get_strategies_path(self) -> Path:
        """获取strategies目录"""
        return self.project_root / "strategies"

    def get_config_path(self, filename: str = "unified_config.json") -> Path:
        """
        获取配置文件路径

        Args:
            filename: 配置文件名

        Returns:
            Path: 配置文件完整路径
        """
        return self.project_root / "config" / filename

    def get_xueqiu_config_path(self, filename: str = "unified_config.json") -> Path:
        """
        获取雪球跟单配置文件路径

        Args:
            filename: 配置文件名

        Returns:
            Path: 配置文件完整路径
        """
        return self.project_root / "strategies" / "xueqiu_follow" / "config" / filename

    def get_reports_path(self, subfolder: str = "") -> Path:
        """
        获取报告输出目录

        Args:
            subfolder: 子文件夹名称（可选）

        Returns:
            Path: 报告目录路径
        """
        reports_path = self.project_root / "strategies" / "reports"
        if subfolder:
            return reports_path / subfolder
        return reports_path

    def get_logs_path(self) -> Path:
        """获取日志目录"""
        return self.project_root / "logs"

    def get_data_path(self, *parts) -> Path:
        """
        获取数据目录路径

        Args:
            *parts: 路径组成部分

        Returns:
            Path: 数据目录路径
        """
        return self.project_root / "data".joinpath(*parts) if parts else self.project_root / "data"


# ========================================
# 全局单例实例
# ========================================
_path_manager = None


def _get_manager() -> PathManager:
    """获取PathManager单例"""
    global _path_manager
    if _path_manager is None:
        _path_manager = PathManager()
    return _path_manager


# ========================================
# 公共API函数
# ========================================

def init_paths() -> PathManager:
    """
    初始化项目路径（幂等性，多次调用只生效一次）

    这是推荐的初始化方式，只需在程序开始时调用一次

    Returns:
        PathManager: 路径管理器实例

    Examples:
        >>> # 在程序开始时调用
        >>> from core.path_manager import init_paths
        >>> init_paths()
        >>>
        >>> # 现在可以正常导入其他模块
        >>> from easy_xt import xt_trader
        >>> from core.config import get_config
    """
    return _get_manager()


def get_project_root() -> Path:
    """
    获取项目根目录

    Returns:
        Path: 项目根目录路径

    Examples:
        >>> root = get_project_root()
        >>> print(root)
        PosixPath('/path/to/miniqmt扩展')
    """
    return _get_manager().project_root


def get_path(*parts) -> Path:
    """
    获取相对于项目根目录的路径

    Args:
        *parts: 路径组成部分

    Returns:
        Path: 完整路径

    Examples:
        >>> config_path = get_path('config', 'unified_config.json')
        >>> strategy_path = get_path('strategies', 'xueqiu_follow')
    """
    return _get_manager().get_path(*parts)


def get_easyxt_path() -> Path:
    """获取easy_xt目录路径"""
    return _get_manager().get_easyxt_path()


def get_core_path() -> Path:
    """获取core目录路径"""
    return _get_manager().get_core_path()


def get_strategies_path() -> Path:
    """获取strategies目录路径"""
    return _get_manager().get_strategies_path()


def get_config_path(filename: str = "unified_config.json") -> Path:
    """
    获取配置文件路径

    Args:
        filename: 配置文件名

    Returns:
        Path: 配置文件完整路径
    """
    return _get_manager().get_config_path(filename)


def get_xueqiu_config_path(filename: str = "unified_config.json") -> Path:
    """
    获取雪球跟单配置文件路径

    Args:
        filename: 配置文件名

    Returns:
        Path: 配置文件完整路径
    """
    return _get_manager().get_xueqiu_config_path(filename)


def get_reports_path(subfolder: str = "") -> Path:
    """
    获取报告输出目录

    Args:
        subfolder: 子文件夹名称（可选）

    Returns:
        Path: 报告目录路径
    """
    return _get_manager().get_reports_path(subfolder)


def get_logs_path() -> Path:
    """获取日志目录路径"""
    return _get_manager().get_logs_path()


# ========================================
# 便捷导入
# ========================================
__all__ = [
    'init_paths',
    'get_project_root',
    'get_path',
    'get_easyxt_path',
    'get_core_path',
    'get_strategies_path',
    'get_config_path',
    'get_xueqiu_config_path',
    'get_reports_path',
    'get_logs_path',
    'PathManager',
]
