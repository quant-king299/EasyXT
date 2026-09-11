# -*- coding: utf-8 -*-
"""检查 FTShare 配置并拉取少量行情；不会打印 API Key。"""
from __future__ import annotations

import argparse

from core.data_manager.config import DataManagerConfig
from core.data_manager.sources import FTShareSource


def main() -> int:
    parser = argparse.ArgumentParser(description="EasyXT FTShare 连通性检查")
    parser.add_argument("--symbol", default="000001.SZ")
    parser.add_argument("--start", default="20260901")
    parser.add_argument("--end", default="20260911")
    parser.add_argument("--period", default="1d")
    args = parser.parse_args()

    config = DataManagerConfig().get_source_config("ftshare")
    if not config.get("api_key"):
        print("[FAIL] 未配置 FTSHARE_API_KEY，请写入项目根目录 .env.local")
        return 2

    source = FTShareSource(config)
    if not source.connect():
        print("[FAIL] FTShare SDK 初始化失败")
        return 3
    try:
        frame = source.get_price(args.symbol, args.start, args.end, args.period)
        if frame is None or frame.empty:
            print("[FAIL] 接口未返回数据，请检查 Key 权限、额度、代码和日期")
            return 4
        print(f"[OK] FTShare 返回 {len(frame)} 条记录")
        print(frame.tail(3).to_string(index=False))
        return 0
    finally:
        source.close()


if __name__ == "__main__":
    raise SystemExit(main())
