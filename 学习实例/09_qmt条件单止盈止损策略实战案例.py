#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QMT条件单止盈止损策略实战案例
基于条件单框架实现实际的自动止盈止损委托

功能特点：
1. 支持四种止盈止损策略
2. 自动创建条件单并监控
3. 触发后自动执行实际交易委托
4. 可视化管理多个条件单

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
import io

# Windows控制台编码处理
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目路径
project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_path)

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

try:
    import easy_xt
    from xtquant import xtdata
    from easy_xt.utils import StockCodeUtils
    EASYXT_AVAILABLE = True
except ImportError:
    EASYXT_AVAILABLE = False
    print("警告: easy_xt未安装，本案例需要easy_xt支持")


class StopLossConditionOrderManager:
    """
    止盈止损条件单管理器
    管理多个条件单，支持自动创建、监控和执行
    """

    def __init__(self):
        """初始化管理器"""
        self.orders = []  # 存储所有条件单
        self.order_counter = 0  # 条件单计数器
        self.trade_api = None  # 交易API
        self._trade_initialized = False  # 交易API是否已初始化
        self.monitoring_active = False  # 是否正在监控

        # 初始化交易连接
        self.init_trade_connection()

    def init_trade_connection(self):
        """初始化交易连接"""
        if not EASYXT_AVAILABLE:
            print("提示: EasyXT不可用，无法执行实际交易")
            return

        try:
            # 读取配置文件
            config_file = os.path.join(project_path, 'config', 'unified_config.json')
            if not os.path.exists(config_file):
                print("提示: 未找到配置文件 config/unified_config.json")
                print("将使用默认配置或需要手动设置交易参数")
                return

            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 获取配置
            settings = config.get('settings', {})
            account_config = settings.get('account', {})

            userdata_path = account_config.get('qmt_path', '')
            account_id = account_config.get('account_id', '')

            if not userdata_path or not account_id:
                print("提示: 配置文件中未设置完整的账户信息")
                return

            print(f"正在初始化交易连接...")
            print(f"  QMT路径: {userdata_path}")
            print(f"  账户ID: {account_id}")

            # 获取扩展API实例
            self.trade_api = easy_xt.get_extended_api()

            # 初始化交易服务
            if hasattr(self.trade_api, 'init_trade'):
                result = self.trade_api.init_trade(userdata_path)
                if result:
                    self._trade_initialized = True
                    print("✓ 交易服务连接成功")
                else:
                    print("✗ 交易服务连接失败")
                    return

            # 添加账户
            account_type = 'STOCK'
            if self.trade_api.add_account(account_id, account_type):
                print(f"✓ 已添加账户: {account_id} ({account_type})")
            else:
                print(f"✗ 添加账户失败: {account_id}")

        except Exception as e:
            print(f"初始化交易连接时出错: {str(e)}")

    def create_advanced_stop_loss_order(self, params: Dict) -> Optional[Dict]:
        """
        创建高级止盈止损条件单

        参数说明:
        - stock_code: 股票代码
        - cost_price: 成本价
        - position_qty: 持仓数量
        - strategy_preset: 策略组合名称（中长线稳健/短线激进/新手保守）
        - enabled_strategies: 启用的策略列表 [1,2,3,4]
        - validity_hours: 有效期（小时），默认24小时

        返回:
            条件单字典，如果创建失败返回None
        """
        try:
            # 获取参数
            stock_code = params.get('stock_code', '000001.SZ')
            cost_price = params.get('cost_price', 10.0)
            position_qty = params.get('position_qty', 1000)
            strategy_preset = params.get('strategy_preset', '中长线稳健')
            enabled_strategies = params.get('enabled_strategies', [1, 2, 3, 4])
            validity_hours = params.get('validity_hours', 24)

            # 获取策略参数
            strategy_params = self._get_strategy_preset(strategy_preset)

            # 创建条件单
            self.order_counter += 1
            order_id = f"ASL{self.order_counter:04d}"  # ASL = Advanced Stop Loss

            # 计算有效期
            expiry_time = datetime.now() + timedelta(hours=validity_hours)

            # 构建条件单对象
            order = {
                'id': order_id,
                'stock_code': stock_code,
                'cost_price': cost_price,
                'position_qty': position_qty,
                'strategy_preset': strategy_preset,
                'enabled_strategies': enabled_strategies,
                'strategy_params': strategy_params,
                'status': '等待中',
                'created_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'expiry': expiry_time.strftime("%Y-%m-%d %H:%M:%S"),

                # 运行时状态
                'highest_price': cost_price,
                'lowest_price': cost_price,
                'highest_price_after_profit': 0.0,
                'today_open_price': None,
                'yesterday_close_price': None,
                'current_price': 0.0,

                # 触发记录
                'triggered_strategies': [],
                'triggered_price': None,
                'triggered_time': None,
            }

            self.orders.append(order)

            print("="*60)
            print(f"✅ 创建高级止盈止损条件单成功: {order_id}")
            print("="*60)
            print(f"股票代码: {stock_code}")
            print(f"成本价: {cost_price:.2f}元")
            print(f"持仓数量: {position_qty}股")
            print(f"策略组合: {strategy_preset}")
            print(f"启用策略: {enabled_strategies}")
            print(f"有效期至: {order['expiry']}")
            print("="*60)

            return order

        except Exception as e:
            print(f"❌ 创建条件单失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _get_strategy_preset(self, preset_name: str) -> Dict:
        """获取预设策略参数"""
        presets = {
            '中长线稳健': {
                's1_profit_min': 0.20, 's1_profit_max': 0.50, 's1_pullback': 0.10,
                's2_rise_threshold': 0.10, 's2_pullback': 0.05,
                's3_gap_open': 0.03, 's3_high_above_open': 0.02, 's3_pullback': 0.02,
                's4_loss_threshold': -0.05,
            },
            '短线激进': {
                's1_profit_min': 0.10, 's1_profit_max': 0.20, 's1_pullback': 0.05,
                's2_rise_threshold': 0.10, 's2_pullback': 0.05,
                's3_gap_open': 0.05, 's3_high_above_open': 0.03, 's3_pullback': 0.03,
                's4_loss_threshold': -0.08,
            },
            '新手保守': {
                's1_profit_min': 0.15, 's1_profit_max': 0.30, 's1_pullback': 0.08,
                's2_rise_threshold': 0.05, 's2_pullback': 0.02,
                's3_gap_open': 0.02, 's3_high_above_open': 0.015, 's3_pullback': 0.015,
                's4_loss_threshold': -0.05,
            }
        }
        return presets.get(preset_name, presets['中长线稳健'])

    def get_current_price(self, stock_code: str) -> Optional[float]:
        """获取股票当前价格"""
        if not EASYXT_AVAILABLE:
            print("提示: EasyXT不可用，无法获取实时价格")
            return None

        try:
            normalized_code = StockCodeUtils.normalize_code(stock_code)

            # 尝试使用get_full_tick获取实时价格
            tick_data = xtdata.get_full_tick([normalized_code])
            if tick_data and normalized_code in tick_data:
                tick_info = tick_data[normalized_code]
                if tick_info and 'lastPrice' in tick_info:
                    return float(tick_info['lastPrice'])
                elif tick_info and 'price' in tick_info:
                    return float(tick_info['price'])

            # 如果失败，尝试get_market_data
            current_data = xtdata.get_market_data(
                stock_list=[normalized_code],
                period='tick',
                count=1
            )

            if current_data and isinstance(current_data, dict) and normalized_code in current_data:
                data_array = current_data[normalized_code]
                if hasattr(data_array, '__len__') and len(data_array) > 0:
                    first_item = data_array[0]
                    if hasattr(first_item, 'lastPrice'):
                        return float(first_item['lastPrice'])

            return None
        except Exception as e:
            print(f"获取{stock_code}当前价格失败: {str(e)}")
            return None

    def check_strategies(self, order: Dict) -> List[Dict]:
        """检查所有策略是否触发"""
        triggered_strategies = []
        current_price = order['current_price']
        cost_price = order['cost_price']
        params = order['strategy_params']
        enabled = order['enabled_strategies']

        # 更新最高价和最低价
        order['highest_price'] = max(order['highest_price'], current_price)
        order['lowest_price'] = min(order['lowest_price'], current_price)

        # 策略1: 浮盈回落止损
        if 1 in enabled:
            triggered, reason = self._check_strategy1(order, current_price, cost_price, params)
            if triggered:
                triggered_strategies.append({'strategy_id': 1, 'name': '浮盈回落止损', 'reason': reason})

        # 策略2: 最高价回落止损
        if 2 in enabled:
            triggered, reason = self._check_strategy2(order, current_price, cost_price, params)
            if triggered:
                triggered_strategies.append({'strategy_id': 2, 'name': '最高价回落止损', 'reason': reason})

        # 策略3: 高开回落止损
        if 3 in enabled:
            triggered, reason = self._check_strategy3(order, current_price, cost_price, params)
            if triggered:
                triggered_strategies.append({'strategy_id': 3, 'name': '高开回落止损', 'reason': reason})

        # 策略4: 总体亏损止损
        if 4 in enabled:
            triggered, reason = self._check_strategy4(order, current_price, cost_price, params)
            if triggered:
                triggered_strategies.append({'strategy_id': 4, 'name': '总体亏损止损', 'reason': reason})

        return triggered_strategies

    def _check_strategy1(self, order: Dict, current_price: float, cost_price: float, params: Dict) -> Tuple[bool, str]:
        """检查策略1：浮盈回落止损"""
        current_profit = (current_price - cost_price) / cost_price

        if current_profit < params['s1_profit_min']:
            return False, f"等待浮盈(当前{current_profit*100:.1f}%，目标{params['s1_profit_min']*100:.0f}%)"

        if current_profit >= params['s1_profit_max']:
            return True, f"浮盈达{current_profit*100:.1f}%，超过目标{params['s1_profit_max']*100:.0f}%"

        # 监控回落
        if order['highest_price_after_profit'] == 0:
            order['highest_price_after_profit'] = current_price
        else:
            order['highest_price_after_profit'] = max(order['highest_price_after_profit'], current_price)

        pullback_ratio = (order['highest_price_after_profit'] - current_price) / order['highest_price_after_profit']

        if pullback_ratio >= params['s1_pullback']:
            return True, f"从最高价回落{pullback_ratio*100:.1f}%，触发止损线{params['s1_pullback']*100:.0f}%"

        return False, f"监控回落(回落{pullback_ratio*100:.1f}%，限制{params['s1_pullback']*100:.0f}%)"

    def _check_strategy2(self, order: Dict, current_price: float, cost_price: float, params: Dict) -> Tuple[bool, str]:
        """检查策略2：最高价回落止损"""
        highest_price = order['highest_price']
        highest_rise = (highest_price - cost_price) / cost_price

        if highest_rise < params['s2_rise_threshold']:
            return False, f"等待涨幅(最高{highest_rise*100:.1f}%，目标{params['s2_rise_threshold']*100:.0f}%)"

        pullback_ratio = (highest_price - current_price) / highest_price

        if pullback_ratio >= params['s2_pullback']:
            return True, f"最高价涨幅{highest_rise*100:.1f}%，回落{pullback_ratio*100:.1f}%，触发止损"

        return False, f"监控回落(回落{pullback_ratio*100:.1f}%，限制{params['s2_pullback']*100:.0f}%)"

    def _check_strategy3(self, order: Dict, current_price: float, cost_price: float, params: Dict) -> Tuple[bool, str]:
        """检查策略3：高开回落止损"""
        if order['today_open_price'] is None or order['yesterday_close_price'] is None:
            return False, "等待开盘数据"

        gap_open_ratio = (order['today_open_price'] - order['yesterday_close_price']) / order['yesterday_close_price']

        if gap_open_ratio < params['s3_gap_open']:
            return False, f"等待高开(高开{gap_open_ratio*100:.1f}%，目标{params['s3_gap_open']*100:.0f}%)"

        high_above_ratio = (order['highest_price'] - order['today_open_price']) / order['today_open_price']

        if high_above_ratio < params['s3_high_above_open']:
            return False, f"等待冲高(高于开盘{high_above_ratio*100:.1f}%，目标{params['s3_high_above_open']*100:.1f}%)"

        pullback_ratio = (order['highest_price'] - current_price) / order['highest_price']

        if pullback_ratio >= params['s3_pullback']:
            return True, f"高开{gap_open_ratio*100:.1f}%，回落{pullback_ratio*100:.1f}%，触发止损"

        return False, f"监控回落(回落{pullback_ratio*100:.1f}%，限制{params['s3_pullback']*100:.1f}%)"

    def _check_strategy4(self, order: Dict, current_price: float, cost_price: float, params: Dict) -> Tuple[bool, str]:
        """检查策略4：总体亏损止损"""
        profit_loss = (current_price - cost_price) / cost_price

        if profit_loss <= params['s4_loss_threshold']:
            return True, f"浮亏{abs(profit_loss)*100:.1f}%，触发止损线{abs(params['s4_loss_threshold'])*100:.0f}%"

        if profit_loss < 0:
            loss_ratio = abs(profit_loss)
            distance_to_stop = (abs(params['s4_loss_threshold']) - loss_ratio) * 100
            return False, f"监控亏损(浮亏{loss_ratio*100:.1f}%，距止损{distance_to_stop:.1f}%)"

        return False, f"当前盈利{profit_loss*100:.1f}%"

    def execute_sell_order(self, order: Dict) -> bool:
        """执行卖出委托"""
        if not EASYXT_AVAILABLE:
            print("提示: EasyXT不可用，无法执行实际交易")
            return False

        if not self._trade_initialized or self.trade_api is None:
            print("提示: 交易API未初始化，无法执行交易")
            return False

        try:
            stock_code = order['stock_code']
            quantity = order['position_qty']
            current_price = order['current_price']

            # 获取账户ID
            if not hasattr(self.trade_api, 'trade_api') or self.trade_api.trade_api is None:
                print("提示: trade_api未初始化")
                return False

            if not hasattr(self.trade_api.trade_api, 'accounts') or not self.trade_api.trade_api.accounts:
                print("提示: 未添加交易账户")
                return False

            account_id = list(self.trade_api.trade_api.accounts.keys())[0]

            # 执行市价卖出
            order_id = self.trade_api.trade_api.sell(
                account_id=account_id,
                code=stock_code,
                volume=quantity,
                price=current_price,  # 使用当前价格作为限价
                price_type='limit'
            )

            if order_id:
                print(f"✓ 卖出委托成功: {stock_code} {quantity}股 @{current_price:.2f}")
                print(f"  委托号: {order_id}")
                return True
            else:
                print(f"✗ 卖出委托失败")
                return False

        except Exception as e:
            print(f"❌ 执行卖出委托失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def monitor_and_execute(self):
        """监控并执行条件单"""
        if not EASYXT_AVAILABLE:
            print("提示: EasyXT不可用，无法监控条件单")
            return

        print("\n" + "="*60)
        print("🔍 开始监控条件单...")
        print("="*60)

        for order in self.orders:
            if order['status'] != '等待中':
                continue

            # 检查是否过期
            try:
                expiry_time = datetime.strptime(order['expiry'], "%Y-%m-%d %H:%M:%S")
                if datetime.now() > expiry_time:
                    order['status'] = '已过期'
                    print(f"⏰ 条件单已过期: {order['id']}")
                    continue
            except:
                pass

            # 获取当前价格
            current_price = self.get_current_price(order['stock_code'])
            if current_price is None or current_price <= 0:
                print(f"⚠ 无法获取 {order['stock_code']} 的价格，跳过")
                continue

            order['current_price'] = current_price

            # 更新今日开盘价和昨收价
            try:
                normalized_code = StockCodeUtils.normalize_code(order['stock_code'])
                tick_data = xtdata.get_full_tick([normalized_code])
                if tick_data and normalized_code in tick_data:
                    tick_info = tick_data[normalized_code]
                    if 'open' in tick_info:
                        order['today_open_price'] = float(tick_info['open'])
                    if 'lastClose' in tick_info:
                        order['yesterday_close_price'] = float(tick_info['lastClose'])
            except:
                pass

            # 检查策略
            triggered_strategies = self.check_strategies(order)

            # 如果有策略触发，执行卖出
            if triggered_strategies:
                print(f"\n🚨 条件单触发: {order['id']}")
                print(f"股票: {order['stock_code']}")
                print(f"当前价格: {current_price:.2f}元")
                print(f"触发策略:")
                for s in triggered_strategies:
                    print(f"  - 策略{s['strategy_id']}: {s['name']}")
                    print(f"    原因: {s['reason']}")

                # 执行卖出
                success = self.execute_sell_order(order)

                if success:
                    order['status'] = '已触发'
                    order['triggered_price'] = current_price
                    order['triggered_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    order['triggered_strategies'] = triggered_strategies

                    profit_loss = (current_price - order['cost_price']) / order['cost_price']
                    profit_amount = (current_price - order['cost_price']) * order['position_qty']

                    print(f"✓ 条件单执行完成")
                    print(f"  盈亏: {profit_loss*100:+.2f}% ({profit_amount:+.2f}元)")
                else:
                    print(f"✗ 条件单执行失败")

            else:
                # 显示当前状态
                profit_loss = (current_price - order['cost_price']) / order['cost_price']
                print(f"{order['id']} | {order['stock_code']} | 价格: {current_price:.2f} | 盈亏: {profit_loss*100:+.2f}%")

    def start_monitoring(self, interval_seconds: int = 5):
        """启动持续监控"""
        import time

        self.monitoring_active = True
        print(f"\n🚀 启动持续监控，检查间隔: {interval_seconds}秒")
        print("按 Ctrl+C 停止监控\n")

        try:
            while self.monitoring_active:
                self.monitor_and_execute()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n\n⏹ 监控已停止")
        finally:
            self.monitoring_active = False

    def list_orders(self):
        """列出所有条件单"""
        print("\n" + "="*80)
        print(f"{'ID':<8} {'股票':<12} {'成本价':<8} {'数量':<8} {'策略组合':<12} {'状态':<8} {'创建时间'}")
        print("="*80)

        for order in self.orders:
            print(f"{order['id']:<8} {order['stock_code']:<12} {order['cost_price']:<8.2f} "
                  f"{order['position_qty']:<8} {order['strategy_preset']:<12} "
                  f"{order['status']:<8} {order['created_time']}")

            # 如果已触发，显示触发信息
            if order['status'] == '已触发':
                print(f"  └─ 触发时间: {order['triggered_time']}, 触发价: {order['triggered_price']:.2f}")
                print(f"  └─ 触发策略: {[s['strategy_id'] for s in order['triggered_strategies']]}")

        print("="*80 + "\n")


def demo_create_orders():
    """演示创建条件单"""
    print("\n" + "="*60)
    print("📝 QMT条件单止盈止损策略实战案例")
    print("="*60)

    # 创建管理器
    manager = StopLossConditionOrderManager()

    # 创建几个示例条件单
    orders_config = [
        {
            'stock_code': '511090.SH',  # 示例债券
            'cost_price': 102.50,
            'position_qty': 1000,
            'strategy_preset': '中长线稳健',
            'enabled_strategies': [1, 2, 3, 4],
            'validity_hours': 24,
        },
        {
            'stock_code': '000001.SZ',
            'cost_price': 10.00,
            'position_qty': 1000,
            'strategy_preset': '短线激进',
            'enabled_strategies': [2, 4],  # 只启用策略2和4
            'validity_hours': 48,
        },
    ]

    for config in orders_config:
        manager.create_advanced_stop_loss_order(config)

    # 列出所有条件单
    manager.list_orders()

    # 询问是否启动监控
    print("\n" + "="*60)
    print("💡 使用说明:")
    print("1. 条件单已创建，可以启动监控")
    print("2. 监控会定期检查条件并自动执行交易")
    print("3. 按 Ctrl+C 可以停止监控")
    print("="*60)

    response = input("\n是否启动监控? (y/n): ").lower()
    if response == 'y':
        manager.start_monitoring(interval_seconds=5)
    else:
        print("\n提示: 可以通过以下方式启动监控:")
        print("  manager.start_monitoring(interval_seconds=5)")


def demo_simple_usage():
    """演示简单用法"""
    print("\n" + "="*60)
    print("📖 简单用法示例")
    print("="*60)

    # 创建管理器
    manager = StopLossConditionOrderManager()

    # 创建一个条件单
    order = manager.create_advanced_stop_loss_order({
        'stock_code': '511090.SH',
        'cost_price': 102.50,
        'position_qty': 1000,
        'strategy_preset': '中长线稳健',
        'enabled_strategies': [1, 2, 3, 4],
    })

    if order:
        print("\n✓ 条件单创建成功!")
        print(f"  ID: {order['id']}")
        print(f"  状态: {order['status']}")

        # 启动监控（在实际使用时）
        # manager.start_monitoring(interval_seconds=5)

    print("\n" + "="*60)
    print("💡 更多用法:")
    print("  - 查看所有条件单: manager.list_orders()")
    print("  - 单次监控检查: manager.monitor_and_execute()")
    print("  - 持续监控: manager.start_monitoring(interval_seconds=5)")
    print("="*60)


def main():
    """主函数"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'simple':
        demo_simple_usage()
    else:
        demo_create_orders()


if __name__ == "__main__":
    main()
