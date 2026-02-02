#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网格交易策略诊断工具
分析网格策略的买卖逻辑和盈亏情况
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from strategies.grid_strategy_511380 import GridBacktester


def analyze_trade_log(result):
    """详细分析交易日志"""
    trade_log = result['trade_log']
    metrics = result['metrics']

    print("=" * 80)
    print("网格交易策略诊断报告")
    print("=" * 80)

    # 1. 基本统计
    print("\n【基本统计】")
    print(f"总收益率: {metrics['total_return']*100:.2f}%")
    print(f"初始资金: {metrics['initial_cash']:,.2f}")
    print(f"最终资金: {metrics['final_value']:,.2f}")
    print(f"总交易次数: {metrics['total_trades']}")
    print(f"盈利交易: {metrics.get('won_trades', 0)}")
    print(f"亏损交易: {metrics.get('lost_trades', 0)}")
    print(f"胜率: {metrics.get('win_rate', 0)*100:.2f}%")

    if trade_log.empty:
        print("\n⚠️ 没有交易记录！可能的原因：")
        print("  1. 价格区间设置太小，价格从未触及网格线")
        print("  2. 回测时间太短")
        print("  3. 数据缺失")
        return

    # 2. 交易顺序分析
    print("\n【交易顺序分析】")
    print(f"首笔交易: {trade_log.iloc[0]['date']} - {trade_log.iloc[0]['action']} @ {trade_log.iloc[0]['price']:.3f}")
    print(f"末笔交易: {trade_log.iloc[-1]['date']} - {trade_log.iloc[-1]['action']} @ {trade_log.iloc[-1]['price']:.3f}")

    # 3. 买卖配对分析
    print("\n【买卖配对分析】")
    buy_trades = trade_log[trade_log['action'] == 'buy']
    sell_trades = trade_log[trade_log['action'] == 'sell']

    print(f"买入次数: {len(buy_trades)}")
    print(f"卖出次数: {len(sell_trades)}")

    if len(buy_trades) > len(sell_trades):
        print(f"⚠️ 买入多于卖出 {len(buy_trades) - len(sell_trades)} 笔（持仓堆积）")
    elif len(sell_trades) > len(buy_trades):
        print(f"⚠️ 卖出多于买入 {len(sell_trades) - len(buy_trades)} 笔（可能存在卖出失败）")

    # 4. 详细配对盈亏分析
    print("\n【详细盈亏分析】")
    pairs = min(len(buy_trades), len(sell_trades))
    total_profit = 0
    total_loss = 0
    profit_trades = 0
    loss_trades = 0

    for i in range(pairs):
        buy_price = buy_trades.iloc[i]['price']
        sell_price = sell_trades.iloc[i]['price']
        buy_date = buy_trades.iloc[i]['date']
        sell_date = sell_trades.iloc[i]['date']

        profit = (sell_price - buy_price) * 1000  # 假设每格1000股

        if profit > 0:
            total_profit += profit
            profit_trades += 1
            status = "✓ 盈利"
        else:
            total_loss += abs(profit)
            loss_trades += 1
            status = "✗ 亏损"

        print(f"  交易对{i+1}: {buy_date}买入@{buy_price:.3f} -> {sell_date}卖出@{sell_price:.3f} | "
              f"盈亏: {profit:.2f}元 {status}")

    # 5. 汇总统计
    print("\n【盈亏汇总】")
    print(f"盈利交易: {profit_trades}笔，总盈利: {total_profit:.2f}元")
    print(f"亏损交易: {loss_trades}笔，总亏损: {total_loss:.2f}元")
    print(f"净盈亏: {total_profit - total_loss:.2f}元")

    if profit_trades + loss_trades > 0:
        avg_profit = total_profit / profit_trades if profit_trades > 0 else 0
        avg_loss = total_loss / loss_trades if loss_trades > 0 else 0
        print(f"平均盈利: {avg_profit:.2f}元/笔")
        print(f"平均亏损: {avg_loss:.2f}元/笔")
        print(f"盈亏比: {avg_profit/avg_loss if avg_loss > 0 else 0:.2f}")

    # 6. 价格分析
    print("\n【价格分析】")
    all_prices = trade_log['price'].values
    print(f"最低价: {all_prices.min():.3f}")
    print(f"最高价: {all_prices.max():.3f}")
    print(f"平均价: {all_prices.mean():.3f}")
    print(f"价格波动: {all_prices.max() - all_prices.min():.3f} "
          f"({(all_prices.max() - all_prices.min())/all_prices.mean()*100:.2f}%)")

    # 7. 诊断建议
    print("\n" + "=" * 80)
    print("【诊断建议】")
    print("=" * 80)

    win_rate = metrics.get('win_rate', 0)
    total_return = metrics['total_return']

    if win_rate < 0.4:
        print("\n❌ 胜率过低 (<40%)")
        print("   可能原因：")
        print("   1. 网格方向反了 - 应该是跌买涨卖")
        print("   2. 价格区间设置不合理 - 区间太小或太大")
        print("   3. 网格数量太多 - 单次收益太小无法覆盖手续费")
        print("   4. 市场趋势不适合 - 单边行情网格策略会亏损")
        print("\n   建议：")
        print("   - 检查网格触发逻辑")
        print("   - 使用GUI工具查看净值曲线图")
        print("   - 尝试不同的参数组合")

    if total_return < 0.01:  # 收益率小于1%
        print("\n⚠️ 收益率过低 (<1%)")
        print("   可能原因：")
        print("   1. 手续费吃掉了利润")
        print("   2. 网格间距太小")
        print("   3. 价格波动不足")
        print("\n   建议：")
        print("   - 增大价格区间 (price_range: 0.02 -> 0.05)")
        print("   - 减少网格数量 (grid_count: 10 -> 5)")
        print("   - 检查手续费设置")

    if len(buy_trades) != len(sell_trades):
        print("\n⚠️ 买卖不平衡")
        print("   可能原因：")
        print("   1. 持仓堆积 - 不断买入但没触发卖出")
        print("   2. 卖出条件太严格 - 检查持仓检查逻辑")
        print("\n   建议：")
        print("   - 调整网格区间中心")
        print("   - 检查卖出条件")

    print("\n" + "=" * 80)
    print("建议使用以下命令运行GUI回测工具进行更详细的分析：")
    print("  python launch_grid_backtest.py")
    print("=" * 80 + "\n")


def main():
    """主函数"""
    print("正在运行网格策略回测...")

    # 创建回测器
    backtester = GridBacktester(
        initial_cash=100000,
        commission=0.0001
    )

    # 运行回测 - 使用默认参数
    result = backtester.run_backtest(
        stock_code='511380.SH',
        start_date='2024-01-01',
        end_date='2024-12-31',
        grid_count=10,
        price_range=0.02,
        position_size=1000,
        enable_trailing=False
    )

    # 分析结果
    analyze_trade_log(result)


if __name__ == "__main__":
    main()
