#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自适应网格策略测试脚本

适合标的：
- 511090.SH - 30年国债ETF
- 511130.SH - 30年国债ETF
- 511280.SH - 5年国债ETF
- 511260.SH - 10年国债ETF

特点：
- 基于相对涨跌幅触发交易
- 自动跟随价格调整
- 适合反复震荡行情

测试建议：
1. 先在测试模式运行，检查参数设置
2. 小仓位测试（100-200股/次）
3. 观察1-2天，确认策略稳定后再加大仓位
4. 设置合理的持仓限制（不超过账户资金的30%）

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
# 导入策略
from strategies.grid_trading.自适应网格策略 import 自适应网格策略
import easy_xt


class 自适应网格测试器:
    """自适应网格测试器"""

    def __init__(self, config_file='adaptive_grid_config.json'):
        """
        初始化测试器

        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = self.load_config()
        self.strategy = None

        # 测试统计
        self.stats = {
            '开始时间': None,
            '运行次数': 0,
            '买入次数': 0,
            '卖出次数': 0,
            '总收益': 0,
            '手续费': 0,
            '交易日志': []
        }

    def load_config(self):
        """加载配置文件"""
        default_config = {
            "账户ID": "",  # 留空则在运行时询问
            "账户类型": "STOCK",
            "股票池": ["511090.SH", "511130.SH"],
            "股票名称": ["30年国债", "30年国债"],
            "买入涨跌幅": -0.15,  # 下跌0.15%买入
            "卖出涨跌幅": 0.15,   # 上涨0.15%卖出
            "单次交易数量": 100,
            "最大持仓数量": 500,
            "价格模式": 5,
            "交易时间段": 8,  # 工作日
            "交易开始时间": 9,
            "交易结束时间": 24,
            "是否参加集合竞价": False,
            "是否测试": True,  # 默认测试模式
            "日志文件路径": "",
            "监控间隔": 3,  # 监控刷新间隔（秒）
            "统计周期": 60  # 统计输出周期（秒）
        }

        # 尝试从文件加载配置
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
                print(f"✅ 已加载配置文件: {self.config_file}")
            except Exception as e:
                print(f"⚠️ 加载配置文件失败: {e}，使用默认配置")
        else:
            # 保存默认配置
            self.save_config(default_config)
            print(f"📝 已创建默认配置文件: {self.config_file}")

        return default_config

    def save_config(self, config=None):
        """保存配置文件"""
        if config is None:
            config = self.config

        try:
            config_path = os.path.join(
                os.path.dirname(__file__),
                self.config_file
            )
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print(f"✅ 配置已保存: {config_path}")
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")

    def print_banner(self):
        """打印横幅"""
        print("\n" + "="*80)
        print(" "*25 + "国债ETF高频网格测试")
        print("="*80)
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

    def print_config(self):
        """打印配置信息"""
        print("\n📋 当前配置:")
        print("-"*80)
        print(f"账户ID: {'*' * 10 if self.config['账户ID'] else '未设置'}")
        print(f"账户类型: {self.config['账户类型']}")
        print(f"股票池: {self.config['股票池']}")
        print(f"网格阈值: 买入{self.config['买入涨跌幅']}% / 卖出{self.config['卖出涨跌幅']}%")
        print(f"交易数量: {self.config['单次交易数量']}股/次")
        print(f"最大持仓: {self.config['最大持仓数量']}股")
        print(f"价格模式: {self._get_price_mode_name()}")
        print(f"测试模式: {'是' if self.config['是否测试'] else '否（实盘）'}")
        print("-"*80)

    def _get_price_mode_name(self):
        """获取价格模式名称"""
        price_modes = {
            4: '卖一价', 5: '最新价', 6: '买一价'
        }
        return price_modes.get(self.config['价格模式'],
                              f'模式{self.config["价格模式"]}')

    def check_account_config(self):
        """检查账户配置"""
        if not self.config['账户ID']:
            print("\n⚠️ 未配置账户ID")
            print("请选择:")
            print("1. 输入账户ID")
            print("2. 仅测试（不连接账户）")

            choice = input("\n请选择 (1/2): ").strip()

            if choice == '1':
                account_id = input("请输入账户ID: ").strip()
                if account_id:
                    self.config['账户ID'] = account_id
                    self.save_config()
                    print(f"✅ 账户ID已保存")
                else:
                    print("❌ 账户ID不能为空，将以测试模式运行")
                    self.config['是否测试'] = True
            else:
                print("将以测试模式运行（不实际下单）")
                self.config['是否测试'] = True

    def setup_log_file(self):
        """设置日志文件路径"""
        if not self.config['日志文件路径']:
            # 自动生成日志文件路径
            log_dir = os.path.join(os.path.dirname(__file__), 'logs')
            os.makedirs(log_dir, exist_ok=True)

            date_str = datetime.now().strftime('%Y%m%d')
            log_file = os.path.join(log_dir, f'bond_etf_grid_{date_str}.json')
            self.config['日志文件路径'] = log_file

            print(f"📝 日志文件: {log_file}")

    def print_market_status(self):
        """打印市场状态"""
        print("\n📊 市场状态:")
        print("-"*80)

        for i, stock_code in enumerate(self.config['股票池']):
            try:
                # 获取行情
                api = easy_xt.get_api()
                price_df = api.data.get_current_price([stock_code])

                if price_df is None or price_df.empty:
                    print(f"{stock_code}: 无法获取行情")
                    continue

                stock_data = price_df[price_df['code'] == stock_code].iloc[0]

                # 获取持仓
                position_info = "无持仓"
                account_id = self.config.get('账户ID')
                if account_id and not self.config['是否测试']:
                    try:
                        position_df = api.trade.get_positions(account_id, stock_code)
                        if position_df is not None and not position_df.empty:
                            pos = position_df.iloc[0]
                            if pos['持仓量'] >= 10:
                                position_info = f"{pos['持仓量']}股 " \
                                             f"(可用{pos['可用数量']}股)"
                    except:
                        pass

                # 打印行情
                print(f"{stock_code} ({self.config['股票名称'][i]})")
                change_pct = ((stock_data['price'] - stock_data['pre_close']) /
                            stock_data['pre_close'] * 100)
                print(f"  最新价: {stock_data['price']:.3f}  "
                      f"涨跌: {change_pct:+.2f}%  "
                      f"持仓: {position_info}")
                print(f"  时间: {datetime.now().strftime('%H:%M:%S')}")
                print()

            except Exception as e:
                print(f"{stock_code}: 获取行情失败 - {e}")

        print("-"*80)

    def calculate_pnl(self):
        """计算盈亏"""
        if self.stats['交易日志']:
            df = pd.DataFrame(self.stats['交易日志'])

            # 计算买入总成本
            buy_df = df[df['交易类型'] == '买']
            if not buy_df.empty:
                buy_cost = (buy_df['交易数量'] * buy_df['触发价格']).sum()
                # 手续费（万分之1）
                buy_fee = buy_cost * 0.0001
            else:
                buy_cost = 0
                buy_fee = 0

            # 计算卖出总收入
            sell_df = df[df['交易类型'] == '卖']
            if not sell_df.empty:
                sell_revenue = (sell_df['交易数量'] * sell_df['触发价格']).sum()
                # 手续费（万分之1）
                sell_fee = sell_revenue * 0.0001
            else:
                sell_revenue = 0
                sell_fee = 0

            # 总盈亏
            total_pnl = sell_revenue - buy_cost - buy_fee - sell_fee

            return total_pnl, buy_fee + sell_fee
        else:
            return 0, 0

    def print_statistics(self):
        """打印统计信息"""
        pnl, fee = self.calculate_pnl()

        print("\n📈 交易统计:")
        print("-"*80)
        print(f"运行时长: {self._get_runtime()}")
        print(f"运行次数: {self.stats['运行次数']}")
        print(f"买入次数: {self.stats['买入次数']}")
        print(f"卖出次数: {self.stats['卖出次数']}")
        print(f"总交易: {self.stats['买入次数'] + self.stats['卖出次数']}次")
        print(f"预估收益: {pnl:.2f}元")
        print(f"预估手续费: {fee:.2f}元")
        print(f"净收益: {pnl - fee:.2f}元")
        print("-"*80)

    def _get_runtime(self):
        """获取运行时长"""
        if self.stats['开始时间']:
            delta = datetime.now() - self.stats['开始时间']
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{delta.days}天{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "00:00:00"

    def run_test(self):
        """运行测试"""
        self.print_banner()
        self.print_config()

        # 检查账户配置
        if not self.config['是否测试']:
            self.check_account_config()

        # 设置日志文件
        self.setup_log_file()

        # 询问是否开始
        print("\n是否开始测试? (y/n): ", end='')
        if input().strip().lower() != 'y':
            print("已取消")
            return

        # 初始化数据连接
        print("\n⏳ 正在初始化数据服务...")
        try:
            api = easy_xt.get_api()
            if api.init_data():
                print("✅ 数据服务初始化成功")
            else:
                print("⚠️ 数据服务初始化失败，请确保迅投客户端已启动")
        except Exception as e:
            print(f"⚠️ 数据服务初始化异常: {e}")

        # 初始化策略
        print("\n⏳ 正在初始化策略...")
        try:
            self.strategy = 自适应网格策略(self.config)
            self.strategy.initialize()  # 调用策略的初始化方法
            self.stats['开始时间'] = datetime.now()

            # 覆盖策略的日志方法，收集统计信息
            original_log = self.strategy.log
            self.stats['交易日志'] = []

            def enhanced_log(msg):
                """增强的日志方法"""
                original_log(msg)

                # 解析交易日志
                if '买入成功' in msg or '卖出成功' in msg:
                    self.stats['运行次数'] += 1
                    if '买入成功' in msg:
                        self.stats['买入次数'] += 1
                    else:
                        self.stats['卖出次数'] += 1

            self.strategy.log = enhanced_log

            print("✅ 策略初始化成功\n")

        except Exception as e:
            print(f"❌ 策略初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return

        # 打印市场状态
        self.print_market_status()

        # 主循环
        print("\n🚀 开始运行测试...")
        print("提示: 按 Ctrl+C 停止测试\n")
        print("="*80)

        try:
            import time
            last_stats_time = datetime.now()

            while True:
                # 执行策略逻辑
                try:
                    # 模拟数据推送
                    data = {'close': pd.Series([100])}  # 占位数据
                    self.strategy.on_data(data)

                    # 定期打印市场状态
                    if (datetime.now() - last_stats_time).seconds >= \
                       self.config['统计周期']:
                        self.print_market_status()
                        self.print_statistics()
                        last_stats_time = datetime.now()

                    # 等待下一次检查
                    time.sleep(self.config['监控间隔'])

                except KeyboardInterrupt:
                    print("\n\n⏹️ 收到停止信号，正在退出...")
                    break
                except Exception as e:
                    print(f"\n❌ 运行错误: {e}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(5)  # 等待后继续

        except KeyboardInterrupt:
            print("\n\n⏹️ 测试已停止")

        # 打印最终统计
        print("\n" + "="*80)
        print(" "*30 + "测试结束")
        print("="*80)
        self.print_statistics()
        self.print_market_status()

        # 显示日志文件位置
        if not self.config['是否测试'] and \
           os.path.exists(self.config['日志文件路径']):
            print(f"\n📝 交易日志已保存到:")
            print(f"   {self.config['日志文件路径']}")


def main():
    """主函数"""
    tester = 自适应网格测试器()
    tester.run_test()


if __name__ == "__main__":
    main()
