# -*- coding: utf-8 -*-
"""大QMT内置Python：按自定义日期区间下载全市场日线DAT。"""

from datetime import datetime
import time


# 用户配置区：YYYYMMDD；END_DATE 留空表示运行当天。
START_DATE = "20260801"
END_DATE = ""
PERIOD = "1d"
SECTOR_NAMES = ("沪深A股",)
EXTRA_CODES = ()
MAX_SYMBOLS = 0  # 0=不限；测试时可设为5
PAUSE_SECONDS = 0.03
INITIAL_READY_DELAY_SECONDS = 3


def _validate_date(value, name):
    try:
        datetime.strptime(value, "%Y%m%d")
    except Exception:
        raise ValueError("%s 必须是 YYYYMMDD 格式，当前值: %s" % (name, value))


def _get_sector_codes(C, sector_name):
    resolver = globals().get("get_stock_list_in_sector")
    if callable(resolver):
        return resolver(sector_name) or []
    resolver = getattr(C, "get_stock_list_in_sector", None)
    if callable(resolver):
        return resolver(sector_name) or []
    raise RuntimeError("当前大QMT环境没有 get_stock_list_in_sector")


def _collect_codes(C):
    codes = []
    for sector_name in SECTOR_NAMES:
        current = _get_sector_codes(C, sector_name)
        if not current:
            raise RuntimeError("板块 %s 未返回证券代码" % sector_name)
        codes.extend(current)
    codes.extend(EXTRA_CODES)
    codes = sorted(set(code for code in codes
                       if isinstance(code, str) and "." in code))
    return codes[:MAX_SYMBOLS] if MAX_SYMBOLS else codes


def _run_downloads(C):
    start_date = START_DATE
    end_date = END_DATE or datetime.now().strftime("%Y%m%d")
    _validate_date(start_date, "START_DATE")
    _validate_date(end_date, "END_DATE")
    if start_date > end_date:
        raise ValueError("START_DATE 不能晚于 END_DATE")
    if PERIOD != "1d":
        raise ValueError("本工具当前只允许 PERIOD='1d'，避免写入错误DAT目录")

    codes = _collect_codes(C)
    print("=" * 60)
    print("EasyXT 大QMT全市场区间下载")
    print("范围: %s ~ %s；周期: %s；证券数: %d" %
          (start_date, end_date, PERIOD, len(codes)))
    print("板块: %s" % ", ".join(SECTOR_NAMES))
    print("仅下载大QMT本地DAT；不下单、不写DuckDB")
    print("=" * 60)

    accepted = 0
    failed = []
    for index, code in enumerate(codes, 1):
        try:
            download_history_data(code, PERIOD, start_date, end_date)
            accepted += 1
        except Exception as exc:
            failed.append(code)
            print("[FAIL] %s: %s" % (code, exc))
        if index % 100 == 0 or index == len(codes):
            print("进度 %d/%d，下载请求已接受 %d，失败 %d" %
                  (index, len(codes), accepted, len(failed)))
        if PAUSE_SECONDS:
            time.sleep(PAUSE_SECONDS)

    print("完成：下载请求已接受 %d，失败 %d" % (accepted, len(failed)))
    print("提示：请求被接受不等于DAT已落盘，请稍后用EasyXT一键补全核验并导入。")
    if failed:
        print("失败代码（最多50只）：%s" % ", ".join(failed[:50]))


def init(C):
    print("EasyXT full-market downloader initialized; waiting for after_init.")


def after_init(C):
    if INITIAL_READY_DELAY_SECONDS:
        time.sleep(INITIAL_READY_DELAY_SECONDS)
    _run_downloads(C)


def handlebar(C):
    return
