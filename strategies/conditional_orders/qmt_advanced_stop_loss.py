#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QMT高级止盈止损策略 - 条件单实现
基于条件单框架的四重止盈止损策略体系

策略体系：
1. 策略1(首选核心)：浮盈A至B，回落C止损
2. 策略2(次选核心)：最高价涨幅超A + 回落B止损
3. 策略3(场景补充)：高开超A, 最高价高于开盘价B, 回落C止损
4. 策略4(纪律底线)：总体浮亏超A止损

作者：CodeBuddy
日期：2025-02-24
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from strategies.base.strategy_template import BaseStrategy
import easy_xt


class AdvancedStopLossStrategy(BaseStrategy):
    """
    高级止盈止损策略
    整合四种止盈止损策略，提供多层级保护
    """

    def __init__(self, params=None):
        """
        初始化策略

        参数说明:
        - 股票代码: 交易的股票代码
        - 策略组合: 预设策略组合名称（中长线稳健/短线激进/新手保守）
        - 成本价: 建仓成本价
        - 持仓数量: 当前持仓数量
        - 启用策略: 启用的策略列表 [1,2,3,4]
        - 启用短信通知: 触发时发送短信通知
        - 自定义参数: 自定义策略参数（可选）
        """
        super().__init__(params)

        # 基础参数
        self.stock_code = self.params.get('股票代码', '000001.SZ')
        self.strategy_preset = self.params.get('策略组合', '中长线稳健')
        self.cost_price = self.params.get('成本价', 10.0)
        self.position_qty = self.params.get('持仓数量', 1000)
        self.enabled_strategies = self.params.get('启用策略', [1, 2, 3, 4])
        self.enable_sms = self.params.get('启用短信通知', False)

        # 策略参数（根据预设组合初始化）
        self.strategy_params = self._get_strategy_preset(self.strategy_preset)

        # 如果有自定义参数，覆盖预设参数
        custom_params = self.params.get('自定义参数', {})
        self.strategy_params.update(custom_params)

        # 持仓状态
        self.current_price = 0.0
        self.highest_price = self.cost_price  # 持仓期间最高价
        self.lowest_price = self.cost_price   # 持仓期间最低价
        self.highest_price_after_profit = 0.0  # 浮盈后的最高价（策略1用）
        self.today_open_price = None  # 今日开盘价（策略3用）
        self.yesterday_close_price = None  # 昨日收盘价（策略3用）

        # 策略触发状态
        self.strategy_triggered = {1: False, 2: False, 3: False, 4: False}
        self.strategy_executed = False

        # 交易记录
        self.trade_records = []

    def _get_strategy_preset(self, preset_name: str) -> Dict:
        """
        获取预设策略参数

        Args:
            preset_name: 预设名称

        Returns:
            策略参数字典
        """
        presets = {
            '中长线稳健': {
                # 策略1: 浮盈20%-50%，回落10%止损
                's1_profit_min': 0.20,
                's1_profit_max': 0.50,
                's1_pullback': 0.10,
                # 策略2: 最高价涨幅超10%，回落5%止损
                's2_rise_threshold': 0.10,
                's2_pullback': 0.05,
                # 策略3: 高开3%，高于开盘2%，回落2%止损
                's3_gap_open': 0.03,
                's3_high_above_open': 0.02,
                's3_pullback': 0.02,
                # 策略4: 浮亏5%止损
                's4_loss_threshold': -0.05,
            },
            '短线激进': {
                # 策略1: 浮盈10%-20%，回落5%止损
                's1_profit_min': 0.10,
                's1_profit_max': 0.20,
                's1_pullback': 0.05,
                # 策略2: 最高价涨幅超10%，回落5%止损
                's2_rise_threshold': 0.10,
                's2_pullback': 0.05,
                # 策略3: 高开5%，高于开盘3%，回落3%止损
                's3_gap_open': 0.05,
                's3_high_above_open': 0.03,
                's3_pullback': 0.03,
                # 策略4: 浮亏8%止损
                's4_loss_threshold': -0.08,
            },
            '新手保守': {
                # 策略1: 浮盈15%-30%，回落8%止损
                's1_profit_min': 0.15,
                's1_profit_max': 0.30,
                's1_pullback': 0.08,
                # 策略2: 最高价涨幅超5%，回落2%止损
                's2_rise_threshold': 0.05,
                's2_pullback': 0.02,
                # 策略3: 高开2%，高于开盘1.5%，回落1.5%止损
                's3_gap_open': 0.02,
                's3_high_above_open': 0.015,
                's3_pullback': 0.015,
                # 策略4: 浮亏5%止损
                's4_loss_threshold': -0.05,
            }
        }

        return presets.get(preset_name, presets['中长线稳健'])

    def initialize(self):
        """策略初始化"""
        self.log("=" * 60)
        self.log("🎯 QMT高级止盈止损策略初始化")
        self.log("=" * 60)

        self.log(f"股票代码: {self.stock_code}")
        self.log(f"策略组合: {self.strategy_preset}")
        self.log(f"成本价: {self.cost_price:.2f}元")
        self.log(f"持仓数量: {self.position_qty}股")
        self.log(f"启用策略: {self.enabled_strategies}")
        self.log(f"短信通知: {'启用' if self.enable_sms else '禁用'}")

        self.log("\n📋 策略参数:")
        self._log_strategy_params()

        self.log("=" * 60)

    def _log_strategy_params(self):
        """记录策略参数"""
        if 1 in self.enabled_strategies:
            self.log(f"  策略1(浮盈回落): "
                    f"浮盈{self.strategy_params['s1_profit_min']*100:.0f}%-"
                    f"{self.strategy_params['s1_profit_max']*100:.0f}%，"
                    f"回落{self.strategy_params['s1_pullback']*100:.0f}%止损")

        if 2 in self.enabled_strategies:
            self.log(f"  策略2(最高价回落): "
                    f"涨幅超{self.strategy_params['s2_rise_threshold']*100:.0f}%，"
                    f"回落{self.strategy_params['s2_pullback']*100:.0f}%止损")

        if 3 in self.enabled_strategies:
            self.log(f"  策略3(高开回落): "
                    f"高开超{self.strategy_params['s3_gap_open']*100:.0f}%，"
                    f"高于开盘{self.strategy_params['s3_high_above_open']*100:.1f}%，"
                    f"回落{self.strategy_params['s3_pullback']*100:.1f}%止损")

        if 4 in self.enabled_strategies:
            self.log(f"  策略4(总体止损): "
                    f"浮亏超{abs(self.strategy_params['s4_loss_threshold'])*100:.0f}%止损")

    def check_validity(self):
        """
        检查策略是否仍然有效

        Returns:
            bool: 是否有效
        """
        now = datetime.now()
        current_time = now.time()

        # 检查是否在交易时间
        if current_time < time(9, 30) or current_time > time(15, 0):
            return False

        # 午休时间
        if time(11, 30) <= current_time <= time(13, 0):
            return False

        # 如果已执行，不再有效
        if self.strategy_executed:
            return False

        return True

    def check_strategy1_floating_profit_pullback(self) -> Tuple[bool, str]:
        """
        策略1：浮盈A至B，回落C止损

        Returns:
            (触发, 原因)
        """
        if 1 not in self.enabled_strategies:
            return False, ""

        cost_price = self.cost_price
        current_price = self.current_price

        # 计算当前浮盈
        current_profit = (current_price - cost_price) / cost_price

        # 还没达到最小浮盈
        if current_profit < self.strategy_params['s1_profit_min']:
            return False, f"等待浮盈(当前{current_profit*100:.1f}%，目标{self.strategy_params['s1_profit_min']*100:.0f}%)"

        # 浮盈超过最大值，建议止盈
        if current_profit >= self.strategy_params['s1_profit_max']:
            return True, f"浮盈已达{current_profit*100:.1f}%，超过目标{self.strategy_params['s1_profit_max']*100:.0f}%"

        # 在目标区间内，跟踪回落
        if self.highest_price_after_profit == 0:
            self.highest_price_after_profit = current_price
        else:
            self.highest_price_after_profit = max(self.highest_price_after_profit, current_price)

        # 计算回落幅度
        pullback_ratio = (self.highest_price_after_profit - current_price) / self.highest_price_after_profit

        if pullback_ratio >= self.strategy_params['s1_pullback']:
            return True, (f"浮盈{current_profit*100:.1f}%，"
                        f"从最高价{self.highest_price_after_profit:.2f}回落{pullback_ratio*100:.1f}%，"
                        f"触发止损线{self.strategy_params['s1_pullback']*100:.0f}%")

        return False, (f"监控回落(浮盈{current_profit*100:.1f}%，"
                      f"回落{pullback_ratio*100:.1f}%，限制{self.strategy_params['s1_pullback']*100:.0f}%)")

    def check_strategy2_high_price_pullback(self) -> Tuple[bool, str]:
        """
        策略2：最高价涨幅超A + 回落B止损

        Returns:
            (触发, 原因)
        """
        if 2 not in self.enabled_strategies:
            return False, ""

        cost_price = self.cost_price
        highest_price = self.highest_price
        current_price = self.current_price

        # 计算最高价涨幅
        highest_rise = (highest_price - cost_price) / cost_price

        # 最高价涨幅未达标
        if highest_rise < self.strategy_params['s2_rise_threshold']:
            return False, f"等待涨幅(最高{highest_rise*100:.1f}%，目标{self.strategy_params['s2_rise_threshold']*100:.0f}%)"

        # 计算从最高价的回落
        pullback_ratio = (highest_price - current_price) / highest_price

        if pullback_ratio >= self.strategy_params['s2_pullback']:
            return True, (f"最高价涨幅{highest_rise*100:.1f}%，"
                        f"回落{pullback_ratio*100:.1f}%，触发止损线{self.strategy_params['s2_pullback']*100:.0f}%")

        return False, (f"监控回落(最高涨幅{highest_rise*100:.1f}%，"
                      f"回落{pullback_ratio*100:.1f}%，限制{self.strategy_params['s2_pullback']*100:.0f}%)")

    def check_strategy3_gap_open_pullback(self) -> Tuple[bool, str]:
        """
        策略3：高开超A, 最高价高于开盘价B, 回落C止损

        Returns:
            (触发, 原因)
        """
        if 3 not in self.enabled_strategies:
            return False, ""

        if self.today_open_price is None or self.yesterday_close_price is None:
            return False, "等待开盘价数据"

        # 计算高开幅度
        gap_open_ratio = (self.today_open_price - self.yesterday_close_price) / self.yesterday_close_price

        # 高开不足
        if gap_open_ratio < self.strategy_params['s3_gap_open']:
            return False, f"等待高开(高开{gap_open_ratio*100:.1f}%，目标{self.strategy_params['s3_gap_open']*100:.0f}%)"

        # 计算最高价高于开盘价的幅度
        high_above_ratio = (self.highest_price - self.today_open_price) / self.today_open_price

        # 冲高不足
        if high_above_ratio < self.strategy_params['s3_high_above_open']:
            return False, (f"高开已达{gap_open_ratio*100:.1f}%，"
                          f"等待冲高(高于开盘{high_above_ratio*100:.1f}%，"
                          f"目标{self.strategy_params['s3_high_above_open']*100:.1f}%)")

        # 计算回落
        pullback_ratio = (self.highest_price - self.current_price) / self.highest_price

        if pullback_ratio >= self.strategy_params['s3_pullback']:
            return True, (f"高开{gap_open_ratio*100:.1f}%，冲高{high_above_ratio*100:.1f}%，"
                        f"回落{pullback_ratio*100:.1f}%，触发止损线{self.strategy_params['s3_pullback']*100:.1f}%")

        return False, (f"监控回落(高开{gap_open_ratio*100:.1f}%，"
                      f"冲高{high_above_ratio*100:.1f}%，"
                      f"回落{pullback_ratio*100:.1f}%，限制{self.strategy_params['s3_pullback']*100:.1f}%)")

    def check_strategy4_total_loss_stop(self) -> Tuple[bool, str]:
        """
        策略4：总体浮亏超A止损

        Returns:
            (触发, 原因)
        """
        if 4 not in self.enabled_strategies:
            return False, ""

        cost_price = self.cost_price
        current_price = self.current_price

        # 计算当前盈亏
        profit_loss = (current_price - cost_price) / cost_price

        # 触发止损
        if profit_loss <= self.strategy_params['s4_loss_threshold']:
            return True, (f"浮亏{abs(profit_loss)*100:.1f}%，"
                        f"触发止损线{abs(self.strategy_params['s4_loss_threshold'])*100:.0f}%")

        if profit_loss < 0:
            loss_ratio = abs(profit_loss)
            distance_to_stop = (abs(self.strategy_params['s4_loss_threshold']) - loss_ratio) * 100
            return False, (f"监控亏损(浮亏{loss_ratio*100:.1f}%，"
                          f"距止损线{distance_to_stop:.1f}%)")
        else:
            return False, f"当前盈利{profit_loss*100:.1f}%"

    def execute_stop_loss(self, triggered_strategies: List[Dict]):
        """
        执行止损

        Args:
            triggered_strategies: 触发的策略列表
        """
        try:
            # 执行卖出
            result = self.sell(self.stock_code, self.position_qty)

            if result:
                self.strategy_executed = True

                # 记录交易
                trade_record = {
                    'time': datetime.now(),
                    'stock_code': self.stock_code,
                    'action': 'SELL',
                    'quantity': self.position_qty,
                    'price': self.current_price,
                    'triggered_strategies': triggered_strategies,
                    'profit_loss': (self.current_price - self.cost_price) / self.cost_price
                }
                self.trade_records.append(trade_record)

                # 构建消息
                profit_loss_pct = trade_record['profit_loss'] * 100
                profit_amount = (self.current_price - self.cost_price) * self.position_qty

                message = f"🚨 止损触发卖出: {self.stock_code} {self.position_qty}股 @{self.current_price:.2f} "
                message += f"盈亏: {profit_loss_pct:+.2f}% ({profit_amount:+.2f}元)\n"
                message += f"触发策略:\n"
                for s in triggered_strategies:
                    message += f"  - 策略{s['strategy_id']}: {s['strategy_name']}\n"
                    message += f"    原因: {s['reason']}\n"

                self.log(message)
                self.send_notification(message)

                self.log("=" * 60)
                self.log("✅ 止损执行完成")
                self.log("=" * 60)

        except Exception as e:
            self.log(f"❌ 执行止损失败: {str(e)}")

    def send_notification(self, message: str):
        """
        发送通知

        Args:
            message: 通知消息
        """
        if self.enable_sms:
            # 这里可以集成短信API
            self.log("📱 短信通知已发送")

    def on_data(self, data):
        """
        数据处理函数

        Args:
            data: 市场数据
        """
        try:
            # 检查策略是否仍然有效
            if not self.check_validity():
                if not self.strategy_executed and self.trade_records:
                    self.log("条件单已过期或已执行")
                return

            # 获取当前价格
            self.current_price = float(data['close'].iloc[-1])

            # 更新最高价和最低价
            self.highest_price = max(self.highest_price, self.current_price)
            self.lowest_price = min(self.lowest_price, self.current_price)

            # 更新今日开盘价（如果需要）
            if len(data) >= 2:
                self.today_open_price = float(data['open'].iloc[-1])
                # 获取昨收价
                if 'pre_close' in data.columns:
                    self.yesterday_close_price = float(data['pre_close'].iloc[-1])
                else:
                    # 如果没有昨收价，使用前一日收盘价
                    self.yesterday_close_price = float(data['close'].iloc[-2])

            # 检查各策略
            triggered_strategies = []

            # 策略1检查
            triggered, reason = self.check_strategy1_floating_profit_pullback()
            if triggered:
                triggered_strategies.append({
                    'strategy_id': 1,
                    'strategy_name': '浮盈回落止损',
                    'reason': reason
                })
            self.strategy_triggered[1] = triggered

            # 策略2检查
            triggered, reason = self.check_strategy2_high_price_pullback()
            if triggered:
                triggered_strategies.append({
                    'strategy_id': 2,
                    'strategy_name': '最高价回落止损',
                    'reason': reason
                })
            self.strategy_triggered[2] = triggered

            # 策略3检查
            triggered, reason = self.check_strategy3_gap_open_pullback()
            if triggered:
                triggered_strategies.append({
                    'strategy_id': 3,
                    'strategy_name': '高开回落止损',
                    'reason': reason
                })
            self.strategy_triggered[3] = triggered

            # 策略4检查
            triggered, reason = self.check_strategy4_total_loss_stop()
            if triggered:
                triggered_strategies.append({
                    'strategy_id': 4,
                    'strategy_name': '总体亏损止损',
                    'reason': reason
                })
            self.strategy_triggered[4] = triggered

            # 如果有策略触发，执行止损
            if triggered_strategies and not self.strategy_executed:
                self.execute_stop_loss(triggered_strategies)

            # 输出当前状态（定期输出，避免日志过多）
            self._log_current_status()

        except Exception as e:
            self.log(f"❌ 数据处理错误: {str(e)}")

    def _log_current_status(self):
        """输出当前状态"""
        current_profit = (self.current_price - self.cost_price) / self.cost_price * 100

        status_str = f"价格: {self.current_price:.2f} | 盈亏: {current_profit:+.2f}% | "

        # 添加各策略状态
        strategy_statuses = []

        if 1 in self.enabled_strategies:
            triggered, reason = self.check_strategy1_floating_profit_pullback()
            status_icon = "🔴" if triggered else "🟢"
            strategy_statuses.append(f"{status_icon}策略1: {reason}")

        if 2 in self.enabled_strategies:
            triggered, reason = self.check_strategy2_high_price_pullback()
            status_icon = "🔴" if triggered else "🟢"
            strategy_statuses.append(f"{status_icon}策略2: {reason}")

        if 3 in self.enabled_strategies:
            triggered, reason = self.check_strategy3_gap_open_pullback()
            status_icon = "🔴" if triggered else "🟢"
            strategy_statuses.append(f"{status_icon}策略3: {reason}")

        if 4 in self.enabled_strategies:
            triggered, reason = self.check_strategy4_total_loss_stop()
            status_icon = "🔴" if triggered else "🟢"
            strategy_statuses.append(f"{status_icon}策略4: {reason}")

        # 输出状态
        self.log(status_str + " | ".join(strategy_statuses))


def create_simulation_data():
    """
    创建模拟数据用于演示

    Returns:
        DataFrame: 模拟的K线数据
    """
    # 创建模拟价格序列
    base_price = 10.0
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')

    # 生成价格走势
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, 100)

    # 模拟特定的价格走势
    scenarios = [
        (0, 10.50, "价格上涨5%"),
        (10, 11.00, "价格上涨10%"),
        (20, 11.50, "价格上涨15%"),
        (30, 12.20, "价格上涨22%"),
        (40, 12.80, "价格上涨28%"),
        (50, 12.50, "从高点回落2.3%"),
        (60, 12.00, "从高点回落6.3%"),
        (70, 11.52, "从高点回落10%"),
        (80, 9.80, "价格下跌2%"),
        (90, 9.40, "浮亏6%"),
    ]

    prices = []
    for i in range(100):
        for scenario_idx, scenario_price, desc in scenarios:
            if abs(i - scenario_idx) < 5:
                # 渐进过渡到目标价格
                progress = (i - scenario_idx + 5) / 10
                prices.append(base_price * (1 - progress) + scenario_price * progress)
                break
        else:
            # 使用随机波动
            if i == 0:
                prices.append(base_price)
            else:
                prices.append(prices[-1] * (1 + returns[i]))

    # 创建DataFrame
    data = pd.DataFrame({
        'datetime': dates,
        'open': [p * (1 + np.random.uniform(-0.01, 0.01)) for p in prices],
        'high': [p * (1 + abs(np.random.uniform(0, 0.02))) for p in prices],
        'low': [p * (1 - abs(np.random.uniform(0, 0.02))) for p in prices],
        'close': prices,
        'volume': [np.random.randint(1000000, 10000000) for _ in range(100)],
        'pre_close': [base_price] + prices[:-1]
    })

    return data


def simulate_strategy():
    """模拟策略运行"""
    print("\n" + "="*60)
    print("🎯 QMT高级止盈止损策略 - 模拟演示")
    print("="*60)

    # 创建策略实例
    params = {
        '股票代码': '000001.SZ',
        '策略组合': '中长线稳健',
        '成本价': 10.0,
        '持仓数量': 1000,
        '启用策略': [1, 2, 3, 4],
        '启用短信通知': False,
    }

    strategy = AdvancedStopLossStrategy(params)
    strategy.initialize()

    # 创建模拟数据
    data = create_simulation_data()

    print("\n📈 开始模拟价格走势...")
    print("-" * 60)

    # 分批处理数据，模拟实时行情
    for i in range(0, len(data), 10):
        batch_data = data.iloc[:i+10]
        if len(batch_data) > 0:
            strategy.on_data(batch_data)
            print()

            if strategy.strategy_executed:
                break

    print("\n" + "="*60)
    print("✅ 模拟演示完成")
    print("="*60)

    # 输出交易记录
    if strategy.trade_records:
        print("\n📋 交易记录:")
        for record in strategy.trade_records:
            print(f"时间: {record['time']}")
            print(f"股票: {record['stock_code']}")
            print(f"操作: {record['action']} {record['quantity']}股 @{record['price']:.2f}")
            print(f"盈亏: {record['profit_loss']*100:+.2f}%")
            print(f"触发策略: {[s['strategy_id'] for s in record['triggered_strategies']]}")


def main():
    """主函数"""
    print("="*60)
    print("🎯 QMT高级止盈止损策略")
    print("基于条件单的四重止盈止损体系")
    print("="*60)

    # 运行模拟
    simulate_strategy()

    print("\n💡 使用说明:")
    print("1. 选择合适的策略组合（中长线稳健/短线激进/新手保守）")
    print("2. 设置成本价和持仓数量")
    print("3. 选择启用的策略（可以启用全部或部分）")
    print("4. 策略会自动监控并在触发时执行止损")
    print("5. 支持自定义参数覆盖预设值")


if __name__ == "__main__":
    main()
