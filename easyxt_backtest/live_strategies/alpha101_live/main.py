#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Alpha101多因子策略 - 实盘交易主程序

自动生成于: 2026-03-23 09:24:10
策略描述: 使用Alpha101因子的多因子选股策略
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from strategy_logic import Alpha101多因子策略Strategy
from order_manager import OrderManager
from risk_control import RiskController


class Alpha101多因子策略StrategyLive:
    """
    使用Alpha101因子的多因子选股策略 实盘交易版
    """

    def __init__(self, account_id: str = "your_account"):
        """
        初始化实盘策略

        Args:
            account_id: QMT账户ID
        """
        self.account_id = account_id
        self.trader = None
        self.strategy = None
        self.order_manager = None
        self.risk_controller = None

        # 策略配置
        self.rebalance_frequency = "monthly"
        self.is_running = False

    def initialize(self):
        """初始化"""
        print(f"初始化Alpha101多因子策略实盘策略...")

        # TODO: 连接QMT
        # self.trader = XtQuantTrader(self.account_id)

        # 初始化策略
        self.strategy = Alpha101多因子策略Strategy(None)

        # 初始化订单管理
        # self.order_manager = OrderManager(self.trader)

        # 初始化风控
        risk_config = {}
        self.risk_controller = RiskController(risk_config)

        print("✅ 初始化完成（模拟模式）")
        return True

    def on_rebalance(self):
        """调仓回调"""
        print(f"\n[{datetime.now()}] 🔔 触发调仓")

        # 1. 获取当前持仓
        # current_positions = self.order_manager.get_positions()

        # 2. 计算目标组合
        date = datetime.now().strftime('%Y%m%d')
        target_portfolio = self.strategy.run_rebalance(date)

        print(f"✅ 调仓完成（模拟模式）")
        print(f"   目标持仓: {len(target_portfolio)} 只股票")

    def run(self):
        """运行实盘策略"""
        if not self.initialize():
            return

        self.is_running = True

        print(f"\n开始运行Alpha101多因子策略实盘策略...")
        print(f"账户ID: {self.account_id}")
        print(f"⚠️  模拟模式：不会执行实际交易")

        # 执行一次调仓测试
        self.on_rebalance()

        print(f"\n✅ 测试完成！")
        print(f"\n💡 实盘使用时需要:")
        print(f"   1. 配置QMT账户ID")
        print(f"   2. 取消注释QMT相关代码")
        print(f"   3. 运行策略: python main.py")


def main():
    """主函数"""
    # 创建策略实例
    strategy_live = Alpha101多因子策略StrategyLive()

    # 运行策略
    strategy_live.run()


if __name__ == "__main__":
    main()
