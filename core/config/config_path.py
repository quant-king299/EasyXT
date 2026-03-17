"""
配置路径管理
提供统一的配置文件路径查找功能
"""

import os
from pathlib import Path
from typing import Optional, List


def get_project_root() -> Path:
    """获取项目根目录"""
    # 从当前文件向上查找项目根目录
    current = Path(__file__).resolve()

    # 向上查找，直到找到包含特定文件/目录的根目录
    markers = [
        '.git',           # Git仓库根目录
        'pyproject.toml', # Python项目文件
        'setup.py',       # Python setup文件
        'core',           # core目录
        'easy_xt',        # easy_xt目录
    ]

    for parent in [current, *current.parents]:
        # 检查是否存在任何标记文件/目录
        if any((parent / marker).exists() for marker in markers):
            return parent

    # 如果没有找到，返回当前文件的祖父目录（假设是项目根目录）
    return current.parent.parent


def get_config_dir(env_var: str = 'EASYXT_CONFIG_PATH') -> Path:
    """
    获取配置目录

    优先级：
    1. 环境变量（最高优先级）
    2. 项目根目录/config/
    3. 当前工作目录/config/
    4. 用户主目录/.miniqmt/

    Args:
        env_var: 环境变量名

    Returns:
        配置目录路径
    """
    # 1. 检查环境变量
    env_path = os.getenv(env_var)
    if env_path:
        config_dir = Path(env_path)
        if config_dir.exists() and config_dir.is_dir():
            return config_dir

    # 获取项目根目录
    project_root = get_project_root()

    # 2. 项目根目录/config/
    config_dir = project_root / 'config'
    if config_dir.exists() and config_dir.is_dir():
        return config_dir

    # 3. 当前工作目录/config/
    cwd_config = Path.cwd() / 'config'
    if cwd_config.exists() and cwd_config.is_dir():
        return cwd_config

    # 4. 用户主目录/.miniqmt/
    user_config = Path.home() / '.miniqmt'

    # 如果以上都不存在，创建项目根目录/config/
    config_dir = project_root / 'config'
    config_dir.mkdir(parents=True, exist_ok=True)

    return config_dir


def get_config_path(filename: str = 'unified_config.json', env_var: str = 'EASYXT_CONFIG_PATH') -> Path:
    """
    获取配置文件路径

    Args:
        filename: 配置文件名
        env_var: 环境变量名

    Returns:
        配置文件完整路径
    """
    config_dir = get_config_dir(env_var)
    return config_dir / filename


def list_config_files(config_dir: Optional[Path] = None) -> List[Path]:
    """
    列出配置目录中的所有配置文件

    Args:
        config_dir: 配置目录，如果为None则使用默认配置目录

    Returns:
        配置文件列表
    """
    if config_dir is None:
        config_dir = get_config_dir()

    if not config_dir.exists():
        return []

    config_extensions = ['.json', '.yaml', '.yml', '.toml', '.ini']
    config_files = []

    for file in config_dir.iterdir():
        if file.is_file() and file.suffix in config_extensions:
            config_files.append(file)

    return sorted(config_files)


def find_config_file(name: str, config_dir: Optional[Path] = None) -> Optional[Path]:
    """
    在配置目录中查找特定的配置文件

    Args:
        name: 配置文件名（可以带或不带扩展名）
        config_dir: 配置目录，如果为None则使用默认配置目录

    Returns:
        配置文件路径，如果未找到则返回None
    """
    if config_dir is None:
        config_dir = get_config_dir()

    if not config_dir.exists():
        return None

    # 尝试直接匹配
    direct_path = config_dir / name
    if direct_path.exists():
        return direct_path

    # 尝试添加常见的扩展名
    extensions = ['.json', '.yaml', '.yml', '.toml', '.ini']
    for ext in extensions:
        path = config_dir / f"{name}{ext}"
        if path.exists():
            return path

    return None
