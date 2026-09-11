# -*- coding: utf-8 -*-
"""
EasyXT 学习实例 24：FTShare 免费数据源详细教程

学习内容：
1. 安全配置 FTShare API Key
2. 查看与搜索本地保存的 160 个免费接口
3. 获取免费实时行情快照
4. 获取多年历史日 K（EasyXT 自动按 12 个月分段）
5. 获取交易日历和三张财务报表
6. 用中文名称调用免费接口
7. 理解免费版、基础版和专业版的行情边界

运行前：
    在项目根目录 .env.local 中配置：
    FTSHARE_API_KEY=你的API_KEY
    FTSHARE_ENABLED=true
    EASYXT_FTSHARE_ENABLED=true

安全提示：不要把 API Key 写进本文件、提交到 Git 或发送到聊天中。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from easy_xt.env_loader import load_project_env

load_project_env(PROJECT_ROOT)


def title(text: str) -> None:
    print("\n" + "=" * 78)
    print(text)
    print("=" * 78)


def lesson_01_check_environment() -> bool:
    """只显示配置状态，绝不打印真实密钥。"""
    title("第1课：检查环境与SDK")
    try:
        import ftshare

        print(f"[OK] FTShare SDK: {Path(ftshare.__file__).parent}")
    except ImportError:
        print("[FAIL] 尚未安装 ftshare SDK")
        print("安装：pip install git+https://github.com/FTShare-Lab/FTShare-python-sdk.git")
        return False

    configured = bool(os.getenv("FTSHARE_API_KEY"))
    print(f"[{'OK' if configured else 'FAIL'}] FTSHARE_API_KEY: {'已配置' if configured else '未配置'}")
    return configured


def lesson_02_free_catalog() -> None:
    """本课不联网，可随时查看本地接口清单。"""
    title("第2课：查询本地160个免费接口")
    from core.data_manager.sources.ftshare_source import FTShareSource

    endpoints = FTShareSource.list_free_endpoints()
    print(f"本地免费接口总数：{len(endpoints)}")
    print("\n资金流相关接口：")
    for item in FTShareSource.list_free_endpoints("资金流"):
        print(f"- {item['title']}: {item['sdk_method']}({', '.join(item['params'])})")
    print("\n可将关键词换成：财务、指数、基金、期货、龙虎榜、股东、宏观等。")


def lesson_03_realtime_quotes() -> None:
    """免费实时数据是HTTP快照，不是Tick推送或历史分钟K。"""
    title("第3课：获取免费实时行情快照")
    from easy_xt.realtime_data.providers.ftshare_provider import FTShareDataProvider

    provider = FTShareDataProvider({"timeout": 15, "batch_size": 200})
    if not provider.connect():
        print("[FAIL] FTShare连接失败")
        return
    try:
        quotes = provider.get_realtime_quotes(["000001.SZ", "600519.SH"])
        for quote in quotes:
            print(
                f"{quote['code']} {quote['name']} 价格={quote['price']:.2f} "
                f"涨跌幅={quote['change_pct']:+.2f}% "
                f"成交额={quote['turnover']:,.0f} PE={quote.get('pe_ttm')}"
            )
        snapshot = provider.get_market_snapshot()
        print("市场成交额：", snapshot.get("turnover"))
        print("涨跌分布：", snapshot.get("distribution"))
    finally:
        provider.disconnect()


def lesson_04_history_and_calendar() -> None:
    """多年请求由适配器自动拆分，调用者不需要手动循环年份。"""
    title("第4课：历史日K与交易日历")
    from core.data_manager.config import DataManagerConfig
    from core.data_manager.sources.ftshare_source import FTShareSource

    source = FTShareSource(DataManagerConfig().get_source_config("ftshare"))
    if not source.connect():
        print("[FAIL] FTShare连接失败")
        return
    try:
        frame = source.get_price("000001.SZ", "20240101", "20260911", period="1d")
        if frame is not None:
            print(f"日K记录：{len(frame)}，日期：{frame['date'].min()} ~ {frame['date'].max()}")
            print(frame.tail(3).to_string(index=False))
        dates = source.get_trading_dates("20260901", "20260911")
        print("交易日：", dates)
    finally:
        source.close()


def lesson_05_financial_statements() -> None:
    title("第5课：财务数据与防止未来函数")
    from core.data_manager.config import DataManagerConfig
    from core.data_manager.sources.ftshare_source import FTShareSource

    source = FTShareSource(DataManagerConfig().get_source_config("ftshare"))
    if not source.connect():
        return
    try:
        # 统一接口会按 publish_date 过滤，只返回查询日之前已披露的最新一期。
        latest = source.get_fundamentals(
            ["000001.SZ", "600519.SH"],
            date="20260911",
            fields=["total_assets", "asset_liability_ratio"],
        )
        print("查询日可知的最新财务数据：")
        print(latest.to_string(index=False) if latest is not None else "无数据")

        # 原始免费接口可获取完整报表历史。
        income = source.call_free("A股利润表", stock_code="600519.SH", all_pages=True)
        print(f"贵州茅台利润表：{len(income)}期")
        print(income[["year", "report_type_cn", "publish_date", "n_profit"]].head().to_string(index=False))
    finally:
        source.close()


def lesson_06_call_by_chinese_name() -> None:
    title("第6课：按中文名称调用任意免费接口")
    from core.data_manager.config import DataManagerConfig
    from core.data_manager.sources.ftshare_source import FTShareSource

    manager = FTShareSource(DataManagerConfig().get_source_config("ftshare"))
    if not manager.connect():
        return
    try:
        valuation = manager.call_free(
            "东方财富个股估值",
            symbol="000001",
            limit=5,
        )
        print(valuation.head().to_string(index=False))
    finally:
        manager.close()


def lesson_07_plan_boundaries() -> None:
    title("第7课：套餐和数据边界")
    print("免费版：日/周/月/年K、实时行情快照、财务、资金流、行业、基金、宏观等。")
    print("基础版：股票/ETF/指数历史分钟K、批量K线、公告研报等。")
    print("专业版：股票/ETF/指数实时分钟K和实时日K。")
    print("大QMT桥接：Tick、五档和低延迟交易行情，仍应作为实盘首选。")
    print("FTShare免费快照：适合跨平台看盘、全市场扫描和基本面补充。")


def main() -> int:
    lesson_02_free_catalog()  # 离线课程始终可以运行
    lesson_07_plan_boundaries()
    if not lesson_01_check_environment():
        return 2
    lesson_03_realtime_quotes()
    lesson_04_history_and_calendar()
    lesson_05_financial_statements()
    lesson_06_call_by_chinese_name()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
