#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
固定网格策略 - 优化版
在固定价格区间内设置网格，低买高卖

优化内容：
1. ✅ 添加数据服务初始化
2. ✅ 添加状态持久化（从委托记录恢复）
3. ✅ 添加完善风控（资金检查、持仓检查）
4. ✅ 修复API调用
5. ✅ 添加日志保存
6. ✅ 添加实时监控

适用场景：
- 价格在固定区间内长期震荡
- 标的：国债ETF、蓝筹股等
- 预期：低频交易，稳健收益

作者：EasyXT团队
版本：2.0
日期：2025-01-22
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# ========================================
# 路径配置：使用统一路径管理器
# ========================================
# 先添加项目根目录到 Python 路径（用于导入 core.path_manager）
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 使用统一路径管理器初始化所有路径
from core.path_manager import init_paths
init_paths()

# 现在可以导入项目中的其他模块了
import easy_xt


class 固定网格策略优化版:
    """
    固定网格策略类（优化版）
    在基准价格上下设置固定间距的网格，低买高卖
    """

    def __init__(self, params=None):
        """
        初始化固定网格策略

        参数说明:
        - 账户ID: QMT账户ID
        - 账户类型: STOCK=普通股, CREDIT=融资融券
        - 股票池: 交易标的列表
        - 基准价格: 网格基准价格（0表示自动使用当前价）
        - 网格数量: 单边网格层数（如5表示上下各5层）
        - 网格间距: 网格间距比例（如0.02表示2%）
        - 单网格数量: 每个网格交易数量
        - 最大持仓: 单个标的最大持仓限制
        - 价格模式: 5=最新价，4=卖一价，6=买一价
        - 启用动态调整: 是否在价格偏离过大时调整基准价
        - 日志文件路径: 交易日志保存路径
        """
        if params is None:
            params = {}

        self.params = params

        # 策略参数
        self.account_id = params.get('账户ID', '')
        self.account_type = params.get('账户类型', 'STOCK')
        self.stock_pool = params.get('股票池', ['511090.SH'])
        self.base_price = params.get('基准价格', 0)  # 0表示自动获取
        self.grid_count = params.get('网格数量', 5)
        self.grid_spacing = params.get('网格间距', 0.01)  # 1%
        self.grid_quantity = params.get('单网格数量', 100)
        self.max_position = params.get('最大持仓', 1000)
        self.price_mode = params.get('价格模式', 5)
        self.enable_dynamic = params.get('启用动态调整', True)
        self.log_file = params.get('日志文件路径',
                                   os.path.join(os.path.dirname(__file__),
                                              'fixed_grid_log.json'))

        # QMT路径和会话ID（用于交易服务初始化）
        self.qmt_path = params.get('QMT路径', '')
        self.session_id = params.get('会话ID', 'fixed_grid_session')

        # 网格状态
        self.grid_levels = {}  # {stock_code: [grid_list]}
        self.current_positions = {}  # {stock_code: quantity}
        self.trade_log = pd.DataFrame()
        self.api = None

    def log(self, message):
        """日志输出"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}")

    def initialize(self):
        """策略初始化"""
        self.log("="*80)
        self.log("固定网格策略启动（优化版）")
        self.log("="*80)
        self.log(f"账户ID: {self.account_id}")
        self.log(f"股票池: {self.stock_pool}")
        self.log(f"基准价格: {self.base_price if self.base_price > 0 else '自动获取'}")
        self.log(f"网格数量: 单边{self.grid_count}层")
        self.log(f"网格间距: {self.grid_spacing*100:.1f}%")
        self.log(f"单网格数量: {self.grid_quantity}股")
        self.log(f"最大持仓: {self.max_position}股")
        self.log(f"动态调整: {'启用' if self.enable_dynamic else '禁用'}")
        self.log("="*80)

        # 初始化API
        try:
            self.api = easy_xt.get_api()

            # 初始化数据服务
            if self.api.init_data():
                self.log("数据服务初始化成功")
            else:
                self.log("警告: 数据服务初始化失败")

            # 初始化交易服务（需要QMT路径和会话ID）
            if self.qmt_path and hasattr(self.api, 'init_trade'):
                try:
                    self.log(f"尝试连接交易服务...")
                    self.log(f"  QMT路径: {self.qmt_path}")
                    self.log(f"  会话ID: {self.session_id}")

                    if self.api.init_trade(self.qmt_path, self.session_id):
                        self.log("交易服务初始化成功")

                        # 添加交易账户
                        if hasattr(self.api, 'add_account') and self.account_id:
                            if self.api.add_account(self.account_id, self.account_type):
                                self.log(f"交易账户 {self.account_id} 添加成功")
                            else:
                                self.log(f"警告: 交易账户添加失败")
                    else:
                        self.log("警告: 交易服务连接失败")
                        self.log("  请检查QMT客户端是否启动并登录")

                except Exception as e:
                    self.log(f"警告: 交易服务初始化异常 - {str(e)}")
            elif not self.qmt_path:
                self.log("警告: 未配置QMT路径，无法连接交易服务")

        except Exception as e:
            self.log(f"API初始化失败: {str(e)}")
            return

        # 加载交易日志
        self.load_trade_log()

        # 初始化所有股票的网格
        self.setup_all_grids()

        # 如果启用动态调整且基准价为0，自动设置
        if self.base_price == 0:
            self.auto_set_base_price()

    def load_trade_log(self):
        """从文件加载交易日志"""
        try:
            if os.path.exists(self.log_file):
                self.trade_log = pd.read_json(self.log_file, encoding='utf-8')
                if not self.trade_log.empty:
                    self.trade_log['触发时间'] = pd.to_datetime(self.trade_log['触发时间'])
                    self.trade_log['触发价格'] = pd.to_numeric(self.trade_log['触发价格'])
                    self.log(f"成功加载交易日志，共{len(self.trade_log)}条记录")
                else:
                    self.trade_log = pd.DataFrame(columns=[
                        '证券代码', '触发时间', '交易类型',
                        '交易数量', '网格价格', '持仓量'
                    ])
            else:
                self.trade_log = pd.DataFrame(columns=[
                    '证券代码', '触发时间', '交易类型',
                    '交易数量', '网格价格', '持仓量'
                ])
        except Exception as e:
            self.log(f"加载日志失败: {str(e)}")
            self.trade_log = pd.DataFrame(columns=[
                '证券代码', '触发时间', '交易类型',
                '交易数量', '网格价格', '持仓量'
            ])

    def save_trade_log(self):
        """保存交易日志"""
        try:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            self.trade_log.to_json(self.log_file, orient='records',
                                  force_ascii=False, indent=2)
        except Exception as e:
            self.log(f"保存日志失败: {str(e)}")

    def setup_all_grids(self):
        """为所有股票设置网格"""
        for stock_code in self.stock_pool:
            # 设置网格
            self.setup_grid(stock_code)

            # 初始化持仓
            self.current_positions[stock_code] = 0

    def setup_grid(self, stock_code):
        """为单个股票设置网格"""
        base = self.base_price if self.base_price > 0 else self.get_current_price(stock_code)

        if base is None or base == 0:
            self.log(f"{stock_code} 无法获取基准价格，跳过")
            return

        grids = []

        # 计算网格价格（上下各grid_count层）
        for i in range(-self.grid_count, self.grid_count + 1):
            if i == 0:
                continue  # 跳过基准价

            grid_price = base * (1 + i * self.grid_spacing)
            grid_type = 'buy' if i < 0 else 'sell'

            grids.append({
                'level': i,
                'price': round(grid_price, 3),
                'type': grid_type,
                'quantity': self.grid_quantity,
                'filled': False
            })

        # 按level排序（-grid_count 到 +grid_count）
        grids.sort(key=lambda x: abs(x['level']))
        self.grid_levels[stock_code] = grids

        self.log(f"{stock_code} 网格设置完成 (基准价:{base:.3f}):")

        # 显示买入网格（从基准价最近的开始）
        buy_grids = [g for g in grids if g['type'] == 'buy']
        if buy_grids:
            self.log(f"  买入网格 ({len(buy_grids)}层):")
            for grid in buy_grids[:3]:  # 显示最近的3层
                self.log(f"    第{abs(grid['level'])}层: {grid['quantity']:4d}股 @{grid['price']:7.3f}")
            if len(buy_grids) > 3:
                self.log(f"    ... 省略 {len(buy_grids)-3} 层")

        # 显示卖出网格（从基准价最近的开始）
        sell_grids = [g for g in grids if g['type'] == 'sell']
        if sell_grids:
            self.log(f"  卖出网格 ({len(sell_grids)}层):")
            for grid in sell_grids[:3]:  # 显示最近的3层
                self.log(f"    第{grid['level']}层: {grid['quantity']:4d}股 @{grid['price']:7.3f}")
            if len(sell_grids) > 3:
                self.log(f"    ... 省略 {len(sell_grids)-3} 层")

    def get_current_price(self, stock_code):
        """获取当前价格"""
        try:
            price_df = self.api.data.get_current_price([stock_code])
            if price_df is None or price_df.empty:
                return None

            stock_data = price_df[price_df['code'] == stock_code]
            if stock_data.empty:
                return None

            return stock_data.iloc[0]['price']
        except Exception as e:
            self.log(f"获取价格失败 {stock_code}: {str(e)}")
            return None

    def auto_set_base_price(self):
        """自动设置基准价格为当前价"""
        self.log("自动设置基准价格...")
        for stock_code in self.stock_pool:
            current_price = self.get_current_price(stock_code)
            if current_price:
                self.log(f"{stock_code} 基准价格设置为 {current_price:.3f}")
                self.setup_grid(stock_code)

    def get_current_position(self, stock_code):
        """获取当前持仓"""
        try:
            if not self.account_id:
                return 0

            position_df = self.api.trade.get_positions(self.account_id, stock_code)
            if position_df is None or position_df.empty:
                return 0

            pos = position_df.iloc[0]
            volume = pos.get('volume', 0)  # 使用正确的列名
            return int(volume) if volume >= 10 else 0

        except Exception as e:
            self.log(f"获取持仓失败 {stock_code}: {str(e)}")
            return 0

    def check_can_buy(self, stock_code, quantity, price):
        """检查是否可以买入"""
        try:
            if not self.account_id:
                return False

            # 检查持仓限制
            current_pos = self.get_current_position(stock_code)
            if current_pos + quantity > self.max_position:
                return False

            # 检查资金
            asset_dict = self.api.trade.get_account_asset(self.account_id)
            if asset_dict is None:
                return False

            available_cash = asset_dict.get('可用金额', 0)
            required_cash = quantity * price
            commission = required_cash * 0.0001

            return available_cash >= (required_cash + commission)

        except Exception as e:
            self.log(f"检查买入条件失败 {stock_code}: {str(e)}")
            return False

    def check_can_sell(self, stock_code, quantity):
        """检查是否可以卖出"""
        current_pos = self.get_current_position(stock_code)
        return current_pos >= quantity

    def find_triggered_grids(self, stock_code, current_price):
        """查找触发的网格"""
        if stock_code not in self.grid_levels:
            return []

        triggered = []

        for grid in self.grid_levels[stock_code]:
            if grid['filled']:
                continue

            # 买入网格：价格跌破网格价
            if grid['type'] == 'buy' and current_price <= grid['price']:
                if self.check_can_buy(stock_code, grid['quantity'], grid['price']):
                    triggered.append(grid)

            # 卖出网格：价格突破网格价
            elif grid['type'] == 'sell' and current_price >= grid['price']:
                if self.check_can_sell(stock_code, grid['quantity']):
                    triggered.append(grid)

        return triggered

    def execute_grid_order(self, stock_code, grid, current_price):
        """执行网格订单"""
        try:
            order_id = None
            now = datetime.now()

            if grid['type'] == 'buy':
                # 买入
                order_id = self.api.trade.buy(
                    account_id=self.account_id,
                    code=stock_code,
                    volume=grid['quantity'],
                    price=0,  # 市价单
                    price_type='market'
                )

                if order_id and order_id > 0:
                    self.current_positions[stock_code] += grid['quantity']
                    grid['filled'] = True
                    self.log(f"✅ 买入成功: {stock_code} Level{grid['level']} "
                           f"{grid['quantity']}股 @{grid['price']:.3f} 委托号:{order_id}")

                    # 记录日志
                    new_log = pd.DataFrame([{
                        '证券代码': stock_code,
                        '触发时间': now,
                        '交易类型': '买',
                        '交易数量': grid['quantity'],
                        '网格价格': grid['price'],
                        '持仓量': self.current_positions[stock_code]
                    }])
                    # 修复 FutureWarning: 确保 trade_log 有正确的列结构
                    if self.trade_log.empty:
                        self.trade_log = new_log
                    else:
                        self.trade_log = pd.concat([self.trade_log, new_log], ignore_index=True, copy=True)
                    self.save_trade_log()
                else:
                    self.log(f"❌ 买入失败: {stock_code} Level{grid['level']}")
                    return False

            elif grid['type'] == 'sell':
                # 卖出
                sell_qty = min(grid['quantity'], self.current_positions[stock_code])
                order_id = self.api.trade.sell(
                    account_id=self.account_id,
                    code=stock_code,
                    volume=sell_qty,
                    price=0,
                    price_type='market'
                )

                if order_id and order_id > 0:
                    self.current_positions[stock_code] -= sell_qty
                    grid['filled'] = True
                    self.log(f"✅ 卖出成功: {stock_code} Level{grid['level']} "
                           f"{sell_qty}股 @{grid['price']:.3f} 委托号:{order_id}")

                    # 记录日志
                    new_log = pd.DataFrame([{
                        '证券代码': stock_code,
                        '触发时间': now,
                        '交易类型': '卖',
                        '交易数量': sell_qty,
                        '网格价格': grid['price'],
                        '持仓量': self.current_positions[stock_code]
                    }])
                    # 修复 FutureWarning: 确保 trade_log 有正确的列结构
                    if self.trade_log.empty:
                        self.trade_log = new_log
                    else:
                        self.trade_log = pd.concat([self.trade_log, new_log], ignore_index=True, copy=True)
                    self.save_trade_log()
                else:
                    self.log(f"❌ 卖出失败: {stock_code} Level{grid['level']}")
                    return False

            return True

        except Exception as e:
            self.log(f"执行网格订单失败: {str(e)}")
            return False

    def reset_filled_grids(self, stock_code, current_price):
        """重置已成交的网格"""
        if stock_code not in self.grid_levels:
            return

        reset_count = 0
        for grid in self.grid_levels[stock_code]:
            if not grid['filled']:
                continue

            # 买入网格成交后，价格上涨超过网格间距的一半，重置
            if (grid['type'] == 'buy' and
                current_price > grid['price'] * (1 + self.grid_spacing * 0.5)):
                grid['filled'] = False
                reset_count += 1

            # 卖出网格成交后，价格下跌超过网格间距的一半，重置
            elif (grid['type'] == 'sell' and
                  current_price < grid['price'] * (1 - self.grid_spacing * 0.5)):
                grid['filled'] = False
                reset_count += 1

        if reset_count > 0:
            self.log(f"{stock_code} 重置了{reset_count}个网格")

    def check_dynamic_adjustment(self, stock_code):
        """检查是否需要动态调整基准价"""
        if not self.enable_dynamic:
            return False

        current_price = self.get_current_price(stock_code)
        if current_price is None:
            return False

        # 获取当前网格的最高价和最低价
        if stock_code not in self.grid_levels:
            return False

        grids = self.grid_levels[stock_code]
        if not grids:
            return False

        min_grid_price = grids[0]['price']
        max_grid_price = grids[-1]['price']

        # 如果价格偏离网格范围超过50%，重新设置网格
        if current_price < min_grid_price * 0.5 or current_price > max_grid_price * 1.5:
            self.log(f"{stock_code} 价格偏离过大，重新设置网格")
            self.base_price = current_price
            self.setup_grid(stock_code)
            return True

        return False

    def run(self):
        """运行策略主循环"""
        self.log("\n🚀 开始运行固定网格策略...")
        self.log("提示: 按 Ctrl+C 停止策略\n")
        self.log("="*80)

        try:
            import time

            last_stats_time = datetime.now()

            while True:
                for stock_code in self.stock_pool:
                    try:
                        # 获取当前价格
                        current_price = self.get_current_price(stock_code)
                        if current_price is None:
                            continue

                        # 查找触发的网格
                        triggered_grids = self.find_triggered_grids(stock_code, current_price)

                        # 执行触发的网格订单
                        for grid in triggered_grids:
                            self.execute_grid_order(stock_code, grid, current_price)

                        # 重置已成交的网格
                        if self.enable_dynamic:
                            self.reset_filled_grids(stock_code, current_price)

                        # 检查是否需要动态调整
                        self.check_dynamic_adjustment(stock_code)

                        # 输出状态（每60秒一次）
                        if (datetime.now() - last_stats_time).seconds >= 60:
                            filled_count = len([g for g in self.grid_levels.get(stock_code, [])
                                              if g['filled']])
                            total_count = len(self.grid_levels.get(stock_code, []))
                            position = self.get_current_position(stock_code)

                            self.log(f"{stock_code} 价格:{current_price:.3f} "
                                   f"持仓:{position}股 "
                                   f"网格:{filled_count}/{total_count}已触发")

                            last_stats_time = datetime.now()

                    except Exception as e:
                        self.log(f"处理{stock_code}时出错: {str(e)}")
                        continue

                # 等待下一次检查
                time.sleep(3)

        except KeyboardInterrupt:
            self.log("\n⏹️ 策略已停止")
            self.print_summary()
        except Exception as e:
            self.log(f"\n❌ 运行错误: {str(e)}")
            self.print_summary()

    def print_summary(self):
        """打印运行总结"""
        self.log("\n" + "="*80)
        self.log("运行总结")
        self.log("="*80)

        for stock_code in self.stock_pool:
            position = self.get_current_position(stock_code)

            # 统计交易次数
            if not self.trade_log.empty:
                stock_log = self.trade_log[self.trade_log['证券代码'] == stock_code]
                buy_count = len(stock_log[stock_log['交易类型'] == '买'])
                sell_count = len(stock_log[stock_log['交易类型'] == '卖'])
            else:
                buy_count = 0
                sell_count = 0

            self.log(f"\n{stock_code}:")
            self.log(f"  当前持仓: {position}股")
            self.log(f"  买入次数: {buy_count}")
            self.log(f"  卖出次数: {sell_count}")

        self.log(f"\n交易日志已保存到: {self.log_file}")
        self.log("="*80)


def main():
    """主函数 - 用于测试策略"""
    # 示例参数
    params = {
        '账户ID': '39020958',
        '账户类型': 'STOCK',
        '股票池': ['511090.SH', '511130.SH'],
        '基准价格': 0,  # 0表示自动获取当前价
        '网格数量': 5,
        '网格间距': 0.01,  # 1%
        '单网格数量': 100,
        '最大持仓': 1000,
        '价格模式': 5,
        '启用动态调整': True,
        '日志文件路径': os.path.join(
            os.path.dirname(__file__),
            'fixed_grid_log.json'
        )
    }

    # 创建策略实例
    strategy = 固定网格策略优化版(params)

    # 运行策略
    strategy.run()


if __name__ == "__main__":
    main()
