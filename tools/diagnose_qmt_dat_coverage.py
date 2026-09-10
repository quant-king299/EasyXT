#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读诊断大QMT/miniQMT日线 DAT 实际落盘位置与最新日期。

示例（在 EasyXT 项目根目录运行）：
    python tools/diagnose_qmt_dat_coverage.py
    python tools/diagnose_qmt_dat_coverage.py 000638.SZ 300344.SZ 600696.SH

不会下载、写入、删除数据，也不会连接交易接口。
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.qmt_local_reader import QMTLocalReader
from data_manager.qmt_paths import resolve_qmt_paths


DEFAULT_CODES = [
    "000638.SZ", "300344.SZ", "600696.SH", "688287.SH", "600355.SH",
    "600599.SH", "600636.SH", "600421.SH", "605081.SH", "600193.SH",
]


def _file_path(datadir: Path, code: str) -> Path:
    pure, _, market = code.partition(".")
    return datadir / market / "86400" / f"{pure}.DAT"


def _latest_date(datadir: Path, code: str) -> str:
    reader = QMTLocalReader(data_dir=datadir, big_data_dir=datadir)
    data = reader.read_daily_data(code)
    if data is None or data.empty:
        return "no readable daily records"
    return data["time"].max().strftime("%Y-%m-%d")


def inspect(datadir: Path, code: str) -> str:
    path = _file_path(datadir, code)
    if not path.is_file():
        return "missing"
    stat = path.stat()
    modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    try:
        latest = _latest_date(datadir, code)
    except Exception as exc:  # diagnostic must continue with the next path/code
        latest = f"read error: {exc}"
    return f"latest={latest}; size={stat.st_size:,}; modified={modified}; path={path}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only QMT DAT coverage diagnostic")
    parser.add_argument("codes", nargs="*", help="symbols such as 000001.SZ")
    args = parser.parse_args()
    codes = args.codes or DEFAULT_CODES

    paths = resolve_qmt_paths(force_refresh=True)
    candidates = []
    for label, value in (("big_qmt_datadir", paths.get("datadir_big")),
                         ("mini_qmt_datadir", paths.get("datadir_mini"))):
        if value and value not in [path for _, path in candidates]:
            candidates.append((label, Path(value)))

    print("EasyXT QMT DAT coverage diagnostic (read-only)")
    print("=" * 72)
    if not candidates:
        print("No QMT datadir could be resolved. Check QMT_DATA_DIR / QMT_DATADIR.")
        return 2
    for label, datadir in candidates:
        print(f"[{label}] {datadir} (exists={datadir.is_dir()})")
        for code in codes:
            print(f"  {code}: {inspect(datadir, code)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
