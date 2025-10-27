"""
jq2qmt-adapter: EasyXT 与 JQ2QMT/qka 的集成适配层（可打包）

注意：本包为最小包装层，实际实现复用仓库内 strategies/adapters/jq2qmt_adapter.py。
为保证在当前仓库下可用，运行时将项目根目录加入 sys.path，并从原文件导入符号。
"""
import os
import sys

# 将项目根目录加入 sys.path，便于导入 strategies.*
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from strategies.adapters.jq2qmt_adapter import EasyXTJQ2QMTAdapter, JQ2QMTManager  # noqa: F401

__all__ = [
    "EasyXTJQ2QMTAdapter",
    "JQ2QMTManager",
]
