# -*- coding: utf-8 -*-
"""
大 QMT 内置 Python：每日更新本地日线 DAT

使用方式：将本文件内容复制到“大 QMT -> 量化 -> Python 编辑器”中新建的
Python 策略。把策略安排在收盘后运行一次（建议 15:20 以后）。

本脚本只调用大 QMT 的 download_history_data 写入大 QMT 本地 DAT 缓存：
不下单、不读取账户、不连接 DuckDB。DAT 更新完成后，再在 EasyXT 的
“数据管理 -> 一键补全数据”中导入 DuckDB。
"""

from datetime import datetime, timedelta
import time


# 每日重复下载最近若干自然日，覆盖周末、节假日及偶发的当日延迟。
LOOKBACK_CALENDAR_DAYS = 21

# 大QMT常见的板块名称。默认仅启用沪深A股，最稳定地修复 DAT 落后问题。
# ETF/北交所是否可通过本券商大QMT下载存在差异；确认板块名称和权限后再
# 加入 OPTIONAL_SECTOR_NAMES，避免一个不支持的市场中断主任务。
SECTOR_NAMES = ("沪深A股",)
OPTIONAL_SECTOR_NAMES = ()  # 例如：("沪深ETF", "北交所A股")

# 无法从板块接口取得的代码可在这里手工补充，格式如 "510300.SH"。
EXTRA_CODES = ()

# 0 表示不限制；排障时可改为小正数，只更新前 N 只证券。
MAX_SYMBOLS = 0
PAUSE_SECONDS = 0.03


def _get_sector_codes(C, sector_name):
    """兼容不同大QMT版本的板块代码查询入口。"""
    resolver = globals().get("get_stock_list_in_sector")
    if callable(resolver):
        return resolver(sector_name) or []

    context_resolver = getattr(C, "get_stock_list_in_sector", None)
    if callable(context_resolver):
        return context_resolver(sector_name) or []

    raise RuntimeError(
        "当前大QMT Python环境没有 get_stock_list_in_sector；"
        "请将需更新代码填入 EXTRA_CODES，或用大QMT数据管理界面下载。"
    )


def _collect_codes(C):
    """收集并去重目标证券；单个可选市场失败不会影响沪深A股更新。"""
    codes = []
    for sector_name in SECTOR_NAMES:
        sector_codes = _get_sector_codes(C, sector_name)
        if not sector_codes:
            raise RuntimeError("板块 %s 未返回任何证券代码" % sector_name)
        codes.extend(sector_codes)

    for sector_name in OPTIONAL_SECTOR_NAMES:
        try:
            codes.extend(_get_sector_codes(C, sector_name))
        except Exception as exc:
            print("[SKIP] 可选板块 %s 不可用: %s" % (sector_name, exc))

    codes.extend(EXTRA_CODES)
    unique_codes = sorted(set(code for code in codes if isinstance(code, str) and "." in code))
    return unique_codes[:MAX_SYMBOLS] if MAX_SYMBOLS else unique_codes


def init(C):
    """大QMT策略启动时执行一次日线增量下载。"""
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=LOOKBACK_CALENDAR_DAYS)).strftime("%Y%m%d")
    codes = _collect_codes(C)

    print("=" * 60)
    print("EasyXT 大QMT DAT 日线更新")
    print("范围: %s ~ %s；证券数: %d" % (start_date, end_date, len(codes)))
    print("仅下载大QMT本地DAT；不下单、不写DuckDB")
    print("=" * 60)

    success = 0
    failed = []
    for index, code in enumerate(codes, 1):
        try:
            # 此函数由大QMT内置Python提供；不要从 xtquant 导入，也不要在
            # 外部命令行直接运行本脚本。
            download_history_data(code, "1d", start_date, end_date)
            success += 1
        except Exception as exc:
            failed.append(code)
            print("[FAIL] %s: %s" % (code, exc))

        if index % 100 == 0 or index == len(codes):
            print("进度 %d/%d，成功 %d，失败 %d" % (index, len(codes), success, len(failed)))
        if PAUSE_SECONDS:
            time.sleep(PAUSE_SECONDS)

    print("完成：成功 %d，失败 %d" % (success, len(failed)))
    if failed:
        print("失败代码（最多50只）：%s" % ", ".join(failed[:50]))
    print("下一步：在 EasyXT 数据管理中运行“一键补全数据”导入 DAT。")
