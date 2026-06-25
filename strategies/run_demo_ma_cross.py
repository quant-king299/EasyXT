#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 名称: 双均线交叉示例
# 优先级: 1
# 调度: daily 09:35
"""
自定义策略示例：双均线交叉

这是一个演示策略，展示如何编写能在多策略管理界面中自动发现的策略。

== 元信息注释（前20行）==
  # 名称: 策略中文名         — 显示在界面中
  # 优先级: 1-10             — 数字越大越靠前
  # 调度: daily 09:35        — 每日 09:35 执行
  # 调度: interval 5         — 每 5 分钟执行一次

== 数据获取方式 ==
  1. 通达信数据（免费，需打开通达信）
     from easy_xt.tdx_client import TdxClient
     with TdxClient() as client:
         df = client.get_market_data(stock_list=['000001.SZ'], ...)

  2. DuckDB 本地数据库（需先在 GUI 下载数据）
     from data_manager.duckdb_connection_pool import get_db_manager
     manager = get_db_manager()
     df = manager.execute_read_query("SELECT * FROM stock_daily WHERE ...")

  3. Tushare Pro（需 token）
     import tushare as ts
     pro = ts.pro_api('your_token')

  4. QMT xtdata（需打开 QMT）
     from xtquant import xtdata
     data = xtdata.get_market_data_ex(...)

== 文件位置 ==
  放在 strategies/ 目录下，命名为 run_xxx.py
  多策略管理界面会自动发现并显示
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    """策略主逻辑 — 在这里编写你的交易策略"""
    print("[demo_ma_cross] 策略开始执行...")

    # ======== 编写你的策略逻辑 ========

    # 示例：从通达信获取行情数据
    try:
        from easy_xt.tdx_client import TdxClient

        with TdxClient() as client:
            df = client.get_market_data(
                stock_list=['000001.SZ', '600519.SH'],
                start_time='20250601',
                period='1d',
                count=20
            )
            print(f"获取到 {len(df)} 条行情数据")
            if not df.empty:
                print(df.head())
    except Exception as e:
        print(f"通达信获取失败: {e}")
        print("提示: 请确保通达信已运行，且在 .env 中配置了 TDX_PATH")

    # ======== 你的策略逻辑 ========
    # TODO: 计算指标、生成信号、发送预警...

    print("[demo_ma_cross] 策略执行完成")


if __name__ == "__main__":
    main()
