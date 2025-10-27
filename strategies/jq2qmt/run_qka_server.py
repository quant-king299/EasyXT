#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动 qka FastAPI 服务端的便捷脚本：自动修复 PYTHONPATH 并调用 qmt_server。
用法示例：
python strategies\jq2qmt\run_qka_server.py --account YOUR_ACCOUNT_ID --mini-qmt-path "C:\\Path\\To\\miniQMT" --host 127.0.0.1 --port 8000
"""

import sys
import os
import argparse

# 将 qka 包根目录加入 PYTHONPATH（包含子包 qka/*）
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
QKA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'qka'))
XTQUANT_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, 'xtquant'))
# 注入 qka 与 xtquant 包路径
for p in (QKA_ROOT, XTQUANT_ROOT):
    if p not in sys.path:
        sys.path.append(p)
# 支持环境变量覆盖 xtquant 路径（如需）
XTQUANT_ENV = os.environ.get('XTQUANT_PATH')
if XTQUANT_ENV and XTQUANT_ENV not in sys.path:
    sys.path.append(XTQUANT_ENV)

from qka.qka.server import qmt_server  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="启动 qka 服务端")
    parser.add_argument("--account", required=True, help="QMT证券账户ID，例如 110XXXXXX")
    parser.add_argument("--mini-qmt-path", required=True, help="miniQMT安装路径，例如 C:\\QMT\\bin")
    parser.add_argument("--host", default="127.0.0.1", help="服务绑定地址，默认 127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="服务端口，默认 8000")
    parser.add_argument("--token", default=None, help="可选，指定自定义Token；不指定则自动生成")
    args = parser.parse_args()

    qmt_server(
        account_id=args.account,
        mini_qmt_path=args.mini_qmt_path,
        host=args.host,
        port=args.port,
        token=args.token,
    )


if __name__ == "__main__":
    main()
