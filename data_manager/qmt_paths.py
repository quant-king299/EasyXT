# -*- coding: utf-8 -*-
"""QMT 路径解析：区分程序路径、userdata、datadir 三类路径。

三层路径概念（以默认安装 D:\\国金QMT交易端模拟 为例）：
    程序路径   <root>\\bin.x64\\XtMiniQmt.exe（miniQMT）/ XtItClient.exe（大QMT）
    userdata   <root>\\userdata_mini          miniQMT 用户数据（xtquant 连接/交易必需）
    datadir    <root>\\datadir                大QMT 行情数据文件（DAT）
               <root>\\userdata_mini\\datadir miniQMT 行情数据文件（DAT）

环境变量（优先级高于自动推导）：
    QMT_EXE_PATH        miniQMT 程序完整路径
    QMT_EXE_PATH_BIG    大QMT 程序完整路径
    QMT_DATA_DIR / QMT_USERDATA_PATH   userdata_mini 路径
    QMT_DATADIR         行情 datadir（显式指定后大/miniQMT datadir 均使用该值）
"""
import logging
import os
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_ENV_KEYS = (
    'QMT_EXE_PATH', 'QMT_EXE_PATH_BIG',
    'QMT_DATA_DIR', 'QMT_USERDATA_PATH', 'QMT_DATADIR',
)


def _read_env(name: str) -> Optional[str]:
    value = os.getenv(name, '').strip()
    return value or None


def _refresh_env_from_dotenv():
    """优先级：进程环境变量 > .env.local > .env（与 deploy 脚本保持一致）。"""
    loaded = os.getenv('EASYXT_DOTENV_LOADED')
    if loaded:
        return
    project_root = Path(__file__).resolve().parent.parent
    for name in ('.env.local', '.env'):
        env_path = project_root / name
        if not env_path.exists():
            continue
        try:
            for line in env_path.read_text(encoding='utf-8', errors='ignore').splitlines():
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key in _ENV_KEYS and key not in os.environ:
                    os.environ[key] = value
        except Exception as e:
            logger.debug(f"读取 {env_path} 失败: {e}")
    os.environ['EASYXT_DOTENV_LOADED'] = '1'


def resolve_qmt_paths(force_refresh: bool = False) -> Dict[str, Optional[Path]]:
    """解析 QMT 相关路径，全部路径可能为 None（未配置或推导失败）。

    返回 dict 键：
        exe_mini       miniQMT 程序路径
        exe_big        大QMT 程序路径
        userdata_mini  userdata_mini 目录
        install_root   QMT 安装根目录（userdata_mini 的父目录）
        datadir_mini   miniQMT 行情 datadir
        datadir_big    大QMT 行情 datadir
    """
    if force_refresh:
        _refresh_env_from_dotenv()

    userdata_raw = _read_env('QMT_DATA_DIR') or _read_env('QMT_USERDATA_PATH')
    if not userdata_raw:
        # 兜底：复用 easy_xt 配置链（含自动扫描）
        try:
            from easy_xt.config import config
            userdata_raw = config.get_userdata_path()
        except Exception:
            userdata_raw = None

    userdata_mini = Path(userdata_raw) if userdata_raw else None
    install_root = userdata_mini.parent if userdata_mini else None

    explicit_datadir = _read_env('QMT_DATADIR')

    datadir_mini = (
        Path(explicit_datadir) if explicit_datadir
        else (userdata_mini / 'datadir' if userdata_mini else None)
    )
    datadir_big = (
        Path(explicit_datadir) if explicit_datadir
        else (install_root / 'datadir' if install_root else None)
    )

    exe_mini_raw = _read_env('QMT_EXE_PATH')
    exe_big_raw = _read_env('QMT_EXE_PATH_BIG')

    if exe_mini_raw:
        exe_mini = Path(exe_mini_raw)
    elif install_root:
        exe_mini = install_root / 'bin.x64' / 'XtMiniQmt.exe'
    else:
        exe_mini = None

    if exe_big_raw:
        exe_big = Path(exe_big_raw)
    elif exe_mini and exe_mini.parent.exists():
        exe_big = exe_mini.parent / 'XtItClient.exe'
    elif install_root:
        exe_big = install_root / 'bin.x64' / 'XtItClient.exe'
    else:
        exe_big = None

    return {
        'exe_mini': exe_mini,
        'exe_big': exe_big,
        'userdata_mini': userdata_mini,
        'install_root': install_root,
        'datadir_mini': datadir_mini,
        'datadir_big': datadir_big,
    }
