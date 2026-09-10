# -*- coding: utf-8 -*-
"""
大 QMT 内置 Python：每日更新本地日线 DAT

使用方式：将本文件内容复制到“大 QMT -> 量化 -> Python 编辑器”中新建的
Python 策略。把策略安排在收盘后运行一次（建议 15:20 以后）。

本脚本只调用大 QMT 的 download_history_data 写入大 QMT 本地 DAT 缓存：
不下单、不读取账户、不连接 DuckDB。DAT 更新完成后，再在 EasyXT 的
“数据管理 -> 一键补全数据”中导入 DuckDB。
"""

import json
import os
import time


PAUSE_SECONDS = 0.03
# QMT guarantees that after_init runs after strategy initialization. Keep a
# short extra delay for the quote connection to finish its cold start.
INITIAL_READY_DELAY_SECONDS = 3

# EasyXT writes its exact jobs beside this script. Set an absolute path here
# only when the strategy is pasted into the QMT editor instead of run as a file.
MANIFEST_PATH = ""
MANIFEST_FILENAME = "easyxt_qmt_dat_update_manifest.json"
# Big QMT's traditional daily DAT writer is most reliable when asked to build
# the complete file.  In manifest mode this applies only to the small stale
# symbol set, not to the full 5,000+ A-share universe.
FULL_DAT_START_DATE = "19900101"


def _load_manifest_jobs():
    path = MANIFEST_PATH
    if not path and globals().get("__file__"):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), MANIFEST_FILENAME)
    if not path or not os.path.isfile(path):
        return None, ""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        jobs = []
        for job in payload.get("jobs", []):
            code, start, end = job.get("stock_code", ""), job.get("start_date", ""), job.get("end_date", "")
            if isinstance(code, str) and "." in code and len(start) == 8 and len(end) == 8:
                jobs.append((code, start, end))
        return jobs, path
    except Exception as exc:
        print("[WARN] Cannot read EasyXT manifest %s: %s" % (path, exc))
        return None, ""


def _run_downloads(C):
    """Run once after QMT has finished strategy initialization."""
    manifest_jobs, manifest_path = _load_manifest_jobs()
    if manifest_jobs is None:
        print("未找到 EasyXT 精确补数清单；本脚本不会自动下载全市场。")
        print("请先在 EasyXT 数据管理中运行“一键补全数据”。")
        return
    if manifest_jobs:
        # Keep the manifest intelligent about *which symbols* need repair, but
        # request a complete daily file for each of those few symbols.  This
        # matches Big QMT's documented/demo DAT download pattern.
        jobs = [(code, FULL_DAT_START_DATE, end) for code, _start, end in manifest_jobs]
        print("EasyXT exact DAT manifest: %s" % manifest_path)
    else:
        print("EasyXT 精确补数清单没有待下载证券，本次无需执行。")
        return

    print("=" * 60)
    print("EasyXT 大QMT DAT 日线更新")
    print("模式: EasyXT精确补数清单；证券数: %d" % len(jobs))
    print("仅下载大QMT本地DAT；不下单、不写DuckDB")
    print("下载接口: download_history_data")
    if manifest_jobs:
        print("DAT重建范围: %s ~ 清单目标日（仅清单内证券）" % FULL_DAT_START_DATE)
    print("=" * 60)

    accepted = 0
    failed = []
    for index, (code, start_date, end_date) in enumerate(jobs, 1):
        try:
            # 此函数由大QMT内置Python提供；不要从 xtquant 导入，也不要在
            # 外部命令行直接运行本脚本。
            download_history_data(code, "1d", start_date, end_date)
            # 迅投下载函数不返回“DAT 已经落盘”的确认；这里只能表示调用已
            # 被大QMT接受。实际覆盖范围由随后 EasyXT DAT 导入再次核验。
            accepted += 1
        except Exception as exc:
            failed.append(code)
            print("[FAIL] %s: %s" % (code, exc))

        if index % 100 == 0 or index == len(jobs):
            print("进度 %d/%d，下载请求已接受 %d，失败 %d" %
                  (index, len(jobs), accepted, len(failed)))
        if PAUSE_SECONDS:
            time.sleep(PAUSE_SECONDS)

    print("完成：下载请求已接受 %d，失败 %d" % (accepted, len(failed)))
    print("提示：请求被接受不等于DAT已落盘；请随后运行EasyXT一键补全进行核验。")
    if failed:
        print("失败代码（最多50只）：%s" % ", ".join(failed[:50]))
    print("下一步：在 EasyXT 数据管理中运行“一键补全数据”导入 DAT。")


def init(C):
    """Do not download here: quote services may not be ready during init."""
    print("EasyXT DAT updater initialized; waiting for after_init.")


def after_init(C):
    """QMT calls this once after init and before bar processing."""
    if INITIAL_READY_DELAY_SECONDS:
        print("Waiting %s seconds for QMT quote services..." % INITIAL_READY_DELAY_SECONDS)
        time.sleep(INITIAL_READY_DELAY_SECONDS)
    _run_downloads(C)


def handlebar(C):
    """No trading or per-bar work is performed by this updater."""
    return
