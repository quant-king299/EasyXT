"""
QMT路径配置常量
统一管理QMT可能的安装路径列表
"""

import os
import string
from pathlib import Path

# QMT可能的安装路径列表 (模拟盘优先)
QMT_POSSIBLE_PATHS = [
    "D:/国金QMT交易端模拟",
    "C:/国金QMT交易端模拟",
    "D:/QMT",
    "C:/QMT",
    "D:/Program Files/QMT",
    "C:/Program Files/QMT",
    "D:/Program Files (x86)/QMT",
    "C:/Program Files (x86)/QMT",
]

# QMT用户数据子目录
QMT_USERDATA_SUBPATH = "userdata_mini"

# 用于识别模拟盘路径的关键词
QMT_SIMULATED_KEYWORDS = ["模拟", "mini"]

# 磁盘扫描时允许进入第二层的目录名关键词（避免全盘遍历）
_SCAN_RECURSE_KEYWORDS = [
    "qmt", "xtquant", "迅投", "交易", "证券", "极简",
    "program files", "软件",
]


def is_simulated_path(path: str) -> bool:
    """判断路径是否为模拟盘路径（包含模拟盘关键词）"""
    return any(keyword in path for keyword in QMT_SIMULATED_KEYWORDS)


def _iter_drive_roots():
    """枚举本机所有存在的盘符根目录（QMT仅支持Windows）"""
    for letter in string.ascii_uppercase:
        root = f"{letter}:/"
        if os.path.exists(root):
            yield root


def scan_qmt_install_paths(max_depth: int = 2) -> list:
    """
    扫描本机磁盘，返回包含 userdata_mini 子目录的 QMT 安装路径列表。

    任何券商的 QMT 安装目录下都有 userdata_mini 文件夹，以此作为识别特征，
    无需枚举券商名称。为控制耗时，第一层目录全量扫描，
    第二层只进入名称包含 QMT 相关关键词的目录。

    Args:
        max_depth: 扫描深度，默认2层

    Returns:
        list: 候选QMT安装路径列表（QMT安装根目录，非userdata_mini路径）
    """
    found = []
    seen = set()

    def _check(dir_path: Path) -> None:
        key = str(dir_path).lower()
        if key in seen:
            return
        seen.add(key)
        try:
            if (dir_path / QMT_USERDATA_SUBPATH).exists():
                found.append(str(dir_path))
        except OSError:
            pass

    for drive in _iter_drive_roots():
        try:
            level1 = [entry for entry in Path(drive).iterdir() if entry.is_dir()]
        except OSError:
            continue

        for d1 in level1:
            _check(d1)
            if max_depth < 2:
                continue
            # 第二层只进入名称包含QMT相关关键词的目录，控制扫描耗时
            if not any(kw in d1.name.lower() for kw in _SCAN_RECURSE_KEYWORDS):
                continue
            try:
                for d2 in d1.iterdir():
                    if d2.is_dir():
                        _check(d2)
            except OSError:
                continue

    return found
