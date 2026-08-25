# -*- coding: utf-8 -*-
"""加载项目级环境文件，优先级：进程环境 > .env.local > .env。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def _set_missing_from_file(path: Path) -> None:
    try:
        from dotenv import dotenv_values

        values = dotenv_values(str(path))
        for key, value in values.items():
            if key and value is not None:
                os.environ.setdefault(key, value)
        return
    except ImportError:
        pass

    # python-dotenv缺失时支持简单 KEY=VALUE，保证桥接仍能启动。
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def load_project_env(start: Optional[Path] = None) -> Optional[Path]:
    """向上寻找项目根目录并加载机器本地与通用环境文件。"""
    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent
    candidates = (current,) + tuple(current.parents)
    project_root = next(
        (candidate for candidate in candidates if (candidate / ".git").exists()),
        None,
    )
    if project_root is None:
        project_root = next(
            (candidate for candidate in candidates
             if (candidate / "pyproject.toml").exists()),
            None,
        )
    if project_root is None:
        return None

    # setdefault确保外部显式设置的进程环境变量始终优先。
    for filename in (".env.local", ".env"):
        path = project_root / filename
        if path.is_file():
            _set_missing_from_file(path)
    return project_root
