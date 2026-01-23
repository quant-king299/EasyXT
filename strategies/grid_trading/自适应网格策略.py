#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高频分时网格策略 - 优化版
基于相对网格的高频分时交易策略，借鉴QMT网格交易策略实现

核心特性：
1. 相对网格：基于上次触发价格计算涨跌幅，适应市场波动
2. 状态持久化：通过交易日志恢复状态，程序重启不丢失
3. 完善风控：持仓限制、资金检查、时间控制、最小交易量
4. 多标的支持：支持股票池批量交易
5. 灵活配置：支持多种价格模式和网格参数

作者：EasyXT团队
版本：1.0
日期：2025-01-22
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from strategies.base.strategy_template import BaseStrategy
import easy_xt


class 自适应网格策略(BaseStrategy):
    """
    自适应网格策略类

    基于相对涨跌幅触发的网格交易策略，适合震荡行情
    基准价自动跟随价格调整，永不失效
    """

    def __init__(self, params=None):
        """
        初始化自适应网格策略

        参数说明:
        - 股票池: 交易股票代码列表，如 ['511130.SH', '511090.SH']
        - 买入涨跌幅: 下跌百分比触发买入，如 -0.2 表示下跌0.2%买入
        - 卖出涨跌幅: 上涨百分比触发卖出，如 0.2 表示上涨0.2%卖出
        - 单次交易数量: 每次网格触发的交易数量
        - 最大持仓数量: 单个标的最大持仓限制
        - 价格模式: 5=最新价, 4=卖一价, 6=买一价, 等
        - 交易时间段: 8=工作日, 0-6=周日到周六
        - 交易开始时间: 如9表示9:00开始
        - 交易结束时间: 如24表示到24:00
        - 是否参加集合竞价: 是否参与9:15-9:25集合竞价
        - 是否测试: 是=不保存日志，否=保存日志
        - 日志文件路径: 交易日志保存路径
        """
        super().__init__(params)

        # 策略参数
        self.stock_pool = self.params.get('股票池', ['511130.SH', '511090.SH'])
        self.buy_threshold = self.params.get('买入涨跌幅', -0.2)  # 负数表示下跌
        self.sell_threshold = self.params.get('卖出涨跌幅', 0.2)  # 正数表示上涨
        self.trade_quantity = self.params.get('单次交易数量', 100)
        self.max_position = self.params.get('最大持仓数量', 300)
        self.price_mode = self.params.get('价格模式', 5)  # 默认最新价

        # 时间控制参数
        self.trade_weekday = self.params.get('交易时间段', 8)  # 8表示工作日
        self.start_hour = self.params.get('交易开始时间', 9)
        self.end_hour = self.params.get('交易结束时间', 24)
        self.join_auction = self.params.get('是否参加集合竞价', False)

        # QMT路径和会话ID（用于交易服务初始化）
        self.qmt_path = self.params.get('QMT路径', '')
        self.session_id = self.params.get('会话ID', 'adaptive_grid_session')
        self.account_id = self.params.get('账户ID', '')
        self.account_type = self.params.get('账户类型', 'STOCK')

        # 测试模式
        self.is_test = self.params.get('是否测试', False)
        self.log_file = self.params.get('日志文件路径',
                                       os.path.join(os.path.dirname(__file__),
                                                  'trade_log.json'))

        # 网格状态（从日志恢复）
        self.trade_log = pd.DataFrame()
        self.is_first_run = True

    def initialize(self):
        """策略初始化"""
        self.log("="*80)
        self.log("自适应网格策略启动")
        self.log("="*80)
        self.log(f"账户ID: {self.account_id}")
        self.log(f"股票池: {self.stock_pool}")
        self.log(f"买入阈值: {self.buy_threshold}%")
        self.log(f"卖出阈值: {self.sell_threshold}%")
        self.log(f"单次交易: {self.trade_quantity}股")
        self.log(f"最大持仓: {self.max_position}股")
        self.log(f"价格模式: {self._get_price_mode_name()}")
        self.log(f"测试模式: {'是' if self.is_test else '否'}")
        self.log("="*80)

        # 初始化API连接
        try:
            api = easy_xt.get_api()

            # 初始化数据服务
            if api.init_data():
                self.log("数据服务初始化成功")
            else:
                self.log("警告: 数据服务初始化失败")

            # 初始化交易服务（需要QMT路径和会话ID）
            if self.qmt_path and hasattr(api, 'init_trade'):
                try:
                    self.log(f"尝试连接交易服务...")
                    self.log(f"  QMT路径: {self.qmt_path}")
                    self.log(f"  会话ID: {self.session_id}")

                    if api.init_trade(self.qmt_path, self.session_id):
                        self.log("交易服务初始化成功")

                        # 添加交易账户
                        if hasattr(api, 'add_account') and self.account_id:
                            if api.add_account(self.account_id, self.account_type):
                                self.log(f"交易账户 {self.account_id} 添加成功")
                            else:
                                self.log(f"警告: 交易账户 {self.account_id} 添加失败")
                    else:
                        self.log("警告: 交易服务连接失败")
                        self.log("  请检查：")
                        self.log("  1. QMT客户端是否已启动")
                        self.log("  2. QMT路径是否正确")
                        self.log("  3. 账户是否已在QMT中登录")

                except Exception as e:
                    self.log(f"警告: 交易服务初始化异常 - {str(e)}")
            else:
                if not self.qmt_path:
                    self.log("警告: 未配置QMT路径，无法连接交易服务")
                    self.log("  请在配置文件中添加 'QMT路径' 参数")

        except Exception as e:
            self.log(f"警告: API初始化异常 - {str(e)}")

        # 加载交易日志
        self.load_trade_log()

        # 如果是首次运行且非测试模式，记录当前持仓
        if self.is_first_run and not self.is_test:
            self.sync_trade_log_from_orders()

    def _get_price_mode_name(self):
        """获取价格模式名称"""
        price_modes = {
            -1: '无效',
            0: '卖五价', 1: '卖四价', 2: '卖三价',
            3: '卖二价', 4: '卖一价', 5: '最新价',
            6: '买一价', 7: '买二价', 8: '买三价',
            9: '买四价', 10: '买五价'
        }
        return price_modes.get(self.price_mode, f'模式{self.price_mode}')

    def load_trade_log(self):
        """从文件加载交易日志"""
        try:
            if os.path.exists(self.log_file):
                self.trade_log = pd.read_json(self.log_file, encoding='utf-8')
                if not self.trade_log.empty:
                    # 确保列名正确（兼容新旧格式）
                    required_columns = ['证券代码', '触发时间', '交易类型',
                                       '交易数量', '持限制', '触发价格']

                    # 检查是否是旧格式（持有限制）
                    if '持有限制' in self.trade_log.columns and '持限制' not in self.trade_log.columns:
                        self.trade_log.rename(columns={'持有限制': '持限制'}, inplace=True)
                        self.log("检测到旧格式日志，已自动转换")

                    if all(col in self.trade_log.columns for col in required_columns):
                        self.trade_log['触发时间'] = pd.to_datetime(self.trade_log['触发时间'])
                        self.trade_log['触发价格'] = pd.to_numeric(self.trade_log['触发价格'])
                        self.trade_log = self.trade_log.sort_values('触发时间')
                        self.is_first_run = False
                        self.log(f"成功加载交易日志，共{len(self.trade_log)}条记录")
                        self.log(f"最新触发记录:\n{self.trade_log.tail(3).to_string()}")
                    else:
                        self.log("日志文件格式错误，重新开始")
                        self.trade_log = pd.DataFrame(columns=required_columns)
                else:
                    self.log("日志文件为空，开始新交易")
                    self.trade_log = pd.DataFrame(columns=required_columns)
            else:
                self.log("日志文件不存在，开始新交易")
                self.trade_log = pd.DataFrame(columns=required_columns)
        except Exception as e:
            self.log(f"加载日志失败: {str(e)}，开始新交易")
            self.trade_log = pd.DataFrame(columns=[
                '证券代码', '触发时间', '交易类型',
                '交易数量', '持限制', '触发价格'
            ])

    def save_trade_log(self):
        """保存交易日志到文件"""
        if self.is_test:
            return

        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            # 保存为JSON格式
            self.trade_log.to_json(self.log_file, orient='records',
                                  force_ascii=False, indent=2)
        except Exception as e:
            self.log(f"保存日志失败: {str(e)}")

    def sync_trade_log_from_orders(self):
        """
        从委托记录同步交易日志
        用于首次运行时恢复状态
        """
        try:
            # 获取账户所有委托
            account_id = self.params.get('账户ID', '')

            if not account_id:
                self.log("未配置账户ID，跳过委托同步")
                return

            api = easy_xt.get_api()
            orders_df = api.trade.get_orders(account_id)

            if orders_df is None or orders_df.empty:
                self.log("没有委托记录，创建新日志")
                self.trade_log = pd.DataFrame(columns=[
                    '证券代码', '触发时间', '交易类型',
                    '交易数量', '持限制', '触发价格'
                ])
                return

            # 尝试多个可能的备注列名
            remark_column = None
            possible_remark_columns = ['投资备注', '备注', 'remark', 'order_remark', '委托备注']

            for col in possible_remark_columns:
                if col in orders_df.columns:
                    remark_column = col
                    break

            if remark_column is None:
                self.log("未找到备注列，创建新日志")
                self.trade_log = pd.DataFrame(columns=[
                    '证券代码', '触发时间', '交易类型',
                    '交易数量', '持限制', '触发价格'
                ])
                return

            # 解析委托备注中的网格交易记录
            result_list = []
            for idx, row in orders_df.iterrows():
                remark = row[remark_column]
                if pd.notna(remark):
                    remark_str = str(remark)
                    if ',' in remark_str:
                        remark_parts = remark_str.split(',')
                        if len(remark_parts) == 6:  # 网格交易备注格式
                            result_list.append(remark_parts)

            if result_list:
                self.trade_log = pd.DataFrame(result_list)
                self.trade_log.columns = ['证券代码', '触发时间', '交易类型',
                                         '交易数量', '持限制', '触发价格']
                self.trade_log['触发时间'] = pd.to_datetime(self.trade_log['触发时间'])
                self.trade_log['触发价格'] = pd.to_numeric(self.trade_log['触发价格'])
                self.trade_log = self.trade_log.sort_values('触发时间')
                self.save_trade_log()
                self.log(f"从委托记录恢复{len(self.trade_log)}条交易记录")
            else:
                self.log("委托记录中未找到网格交易备注，创建新日志")
                self.trade_log = pd.DataFrame(columns=[
                    '证券代码', '触发时间', '交易类型',
                    '交易数量', '持限制', '触发价格'
                ])

        except Exception as e:
            self.log(f"同步委托记录失败: {str(e)}，创建新日志")
            # 创建空的交易日志
            self.trade_log = pd.DataFrame(columns=[
                '证券代码', '触发时间', '交易类型',
                '交易数量', '持限制', '触发价格'
            ])

    def check_trading_time(self):
        """
        检查是否在交易时间

        Returns:
            bool: True表示在交易时间
        """
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        weekday = now.weekday()  # 0=周一, 6=周日

        # 检查星期
        if self.trade_weekday == 8:  # 工作日
            if weekday > 4:  # 周六、周日
                return False
        elif weekday != self.trade_weekday:
            return False

        # 检查小时范围
        if not (self.start_hour <= current_hour <= self.end_hour):
            return False

        # 检查集合竞价
        if current_hour == 9 and current_minute < (15 if self.join_auction else 30):
            return False

        return True

    def get_last_trigger_price(self, stock_code):
        """
        获取上次触发价格

        Args:
            stock_code: 股票代码

        Returns:
            float: 上次触发价格，如果没有则返回基准价
        """
        if self.trade_log.empty:
            # 没有交易记录，使用前收盘价作为基准
            try:
                api = easy_xt.get_api()
                price_df = api.data.get_current_price([stock_code])
                if price_df is not None and not price_df.empty:
                    stock_data = price_df[price_df['code'] == stock_code]
                    if not stock_data.empty:
                        return stock_data.iloc[0]['pre_close']
            except:
                pass
            return None

        # 查找该股票的最新触发记录
        stock_log = self.trade_log[self.trade_log['证券代码'] == stock_code]
        if stock_log.empty:
            # 该股票没有交易记录，使用前收盘价
            try:
                api = easy_xt.get_api()
                price_df = api.data.get_current_price([stock_code])
                if price_df is not None and not price_df.empty:
                    stock_data = price_df[price_df['code'] == stock_code]
                    if not stock_data.empty:
                        return stock_data.iloc[0]['pre_close']
            except:
                pass
            return None

        # 返回最新触发价格
        return stock_log.iloc[-1]['触发价格']

    def calculate_change_pct(self, current_price, last_price):
        """
        计算相对涨跌幅

        Args:
            current_price: 当前价格
            last_price: 上次触发价格

        Returns:
            float: 涨跌幅百分比
        """
        if last_price is None or last_price == 0:
            return 0

        return ((current_price - last_price) / last_price) * 100

    def check_grid_signal(self, stock_code):
        """
        检查网格交易信号

        Args:
            stock_code: 股票代码

        Returns:
            str: 'buy', 'sell', 或 ''
        """
        try:
            # 获取当前价格
            api = easy_xt.get_api()
            price_df = api.data.get_current_price([stock_code])
            if price_df is None or price_df.empty:
                return ''

            stock_data = price_df[price_df['code'] == stock_code]
            if stock_data.empty:
                return ''

            current_price = stock_data.iloc[0]['price']

            # 获取上次触发价格
            last_price = self.get_last_trigger_price(stock_code)
            if last_price is None:
                self.log(f"{stock_code} 无法获取基准价格，跳过")
                return ''

            # 计算涨跌幅
            change_pct = self.calculate_change_pct(current_price, last_price)

            # 判断交易信号
            if change_pct >= self.sell_threshold:
                self.log(f"{stock_code} 当前价:{current_price:.3f}, "
                        f"上次触发:{last_price:.3f}, "
                        f"涨跌:+{change_pct:.2f}% >= {self.sell_threshold:.2f}% -> 卖出信号")
                return 'sell'

            elif change_pct <= self.buy_threshold:
                self.log(f"{stock_code} 当前价:{current_price:.3f}, "
                        f"上次触发:{last_price:.3f}, "
                        f"涨跌:{change_pct:.2f}% <= {self.buy_threshold:.2f}% -> 买入信号")
                return 'buy'

            else:
                self.log(f"{stock_code} 当前价:{current_price:.3f}, "
                        f"涨跌:{change_pct:.2f}% -> 无交易信号")
                return ''

        except Exception as e:
            self.log(f"检查网格信号失败 {stock_code}: {str(e)}")
            return ''

    def get_current_position(self, stock_code):
        """
        获取当前持仓

        Args:
            stock_code: 股票代码

        Returns:
            dict: {'持仓量': int, '可用数量': int}
        """
        try:
            account_id = self.params.get('账户ID', '')

            if not account_id:
                return {'持仓量': 0, '可用数量': 0}

            api = easy_xt.get_api()
            position_df = api.trade.get_positions(account_id, stock_code)

            if position_df is None or position_df.empty:
                return {'持仓量': 0, '可用数量': 0}

            # 如果指定了股票代码，直接使用第一行
            pos = position_df.iloc[0]

            # 获取持仓数量（使用正确的列名）
            volume = pos.get('volume', 0)  # 总持仓
            can_use_volume = pos.get('can_use_volume', 0)  # 可用持仓

            if volume >= 10:
                return {
                    '持仓量': int(volume),
                    '可用数量': int(can_use_volume)
                }
            return {'持仓量': 0, '可用数量': 0}

        except Exception as e:
            self.log(f"获取持仓失败 {stock_code}: {str(e)}")
            return {'持仓量': 0, '可用数量': 0}

    def check_can_sell(self, stock_code, quantity):
        """
        检查是否可以卖出

        Args:
            stock_code: 股票代码
            quantity: 卖出数量

        Returns:
            bool: True表示可以卖出
        """
        position = self.get_current_position(stock_code)

        if position['持仓量'] < 10:
            return False

        if position['可用数量'] >= quantity:
            return True
        elif position['可用数量'] >= 10:  # 至少可以卖出10股
            return True

        return False

    def check_can_buy(self, stock_code, quantity, price):
        """
        检查是否可以买入

        Args:
            stock_code: 股票代码
            quantity: 买入数量
            price: 买入价格

        Returns:
            bool: True表示可以买入
        """
        try:
            account_id = self.params.get('账户ID', '')

            if not account_id:
                return False

            api = easy_xt.get_api()
            asset_dict = api.trade.get_account_asset(account_id)

            if asset_dict is None or not asset_dict:
                return False

            # 尝试多个可能的键名获取可用资金
            available_cash = 0
            possible_keys = ['cash', '可用金额', '可用', 'available', '可用资金',
                           '可用资产', '总可用', '可用余额', 'enable_amount']

            for key in possible_keys:
                if key in asset_dict:
                    available_cash = asset_dict[key]
                    break

            # 如果还是没找到，尝试直接使用第一个数值类型的键
            if available_cash == 0:
                for key, value in asset_dict.items():
                    if isinstance(value, (int, float)) and value > 0:
                        available_cash = value
                        break

            required_cash = quantity * price

            # 预留手续费（约0.01%）
            commission = required_cash * 0.0001

            return available_cash >= (required_cash + commission)

        except Exception as e:
            self.log(f"检查买入条件失败 {stock_code}: {str(e)}")
            return False

    def check_position_limit(self, stock_code, limit):
        """
        检查是否达到持仓限制

        Args:
            stock_code: 股票代码
            limit: 持仓限制

        Returns:
            bool: True表示未达到限制，可以继续买入
        """
        position = self.get_current_position(stock_code)
        available_space = limit - position['持仓量']

        return available_space >= 10

    def execute_trade(self, stock_code, trade_type, quantity, price):
        """
        执行交易

        Args:
            stock_code: 股票代码
            trade_type: 交易类型 ('buy' 或 'sell')
            quantity: 交易数量
            price: 触发价格

        Returns:
            bool: True表示交易成功
        """
        try:
            account_id = self.params.get('账户ID', '')

            if not account_id:
                self.log("未配置账户ID，无法交易")
                return False

            now = datetime.now()

            # 生成委托备注（用于日志恢复）
            remark = f"{stock_code},{now},{trade_type},{quantity},{self.max_position},{price}"

            # 获取交易API
            api = easy_xt.get_api()

            if trade_type == 'buy':
                # 买入
                order_id = api.trade.buy(
                    account_id=account_id,
                    code=stock_code,
                    volume=quantity,
                    price=0,  # 市价单
                    price_type='market'
                )

                if order_id and order_id > 0:
                    self.log(f"✅ 买入成功: {stock_code} {quantity}股 @{price:.3f} 委托号:{order_id}")
                else:
                    self.log(f"❌ 买入失败: {stock_code} {quantity}股 @{price:.3f}")
                    return False

            elif trade_type == 'sell':
                # 卖出
                order_id = api.trade.sell(
                    account_id=account_id,
                    code=stock_code,
                    volume=quantity,
                    price=0,  # 市价单
                    price_type='market'
                )

                if order_id and order_id > 0:
                    self.log(f"✅ 卖出成功: {stock_code} {quantity}股 @{price:.3f} 委托号:{order_id}")
                else:
                    self.log(f"❌ 卖出失败: {stock_code} {quantity}股 @{price:.3f}")
                    return False

            # 记录交易日志
            new_log = pd.DataFrame([{
                '证券代码': stock_code,
                '触发时间': now,
                '交易类型': '买' if trade_type == 'buy' else '卖',
                '交易数量': quantity,
                '持限制': self.max_position,
                '触发价格': price
            }])

            # 修复 FutureWarning: 确保 trade_log 有正确的列结构
            if self.trade_log.empty:
                self.trade_log = new_log
            else:
                self.trade_log = pd.concat([self.trade_log, new_log],
                                          ignore_index=True, copy=True)
            self.save_trade_log()

            return True

        except Exception as e:
            self.log(f"执行交易失败: {str(e)}")
            return False

    def on_data(self, data):
        """
        数据处理函数（策略主逻辑）

        Args:
            data: 市场数据
        """
        try:
            # 检查交易时间
            if not self.check_trading_time():
                return

            # 如果是首次运行，清空测试日志
            if self.is_first_run:
                if not self.is_test:
                    self.log("首次运行，从委托记录恢复状态...")
                    self.sync_trade_log_from_orders()
                else:
                    self.log("测试模式：清空历史日志")
                    self.trade_log = pd.DataFrame(columns=[
                        '证券代码', '触发时间', '交易类型',
                        '交易数量', '持有限制', '触发价格'
                    ])
                self.is_first_run = False

            # 遍历股票池
            for stock_code in self.stock_pool:
                try:
                    # 检查网格信号
                    signal = self.check_grid_signal(stock_code)

                    if not signal:
                        continue

                    # 获取当前价格
                    try:
                        api = easy_xt.get_api()
                        price_df = api.data.get_current_price([stock_code])
                        if price_df is None or price_df.empty:
                            continue
                        stock_data = price_df[price_df['code'] == stock_code]
                        if stock_data.empty:
                            continue
                        current_price = stock_data.iloc[0]['price']
                    except:
                        continue

                    # 根据信号执行交易
                    if signal == 'sell':
                        # 检查是否可以卖出
                        if self.check_can_sell(stock_code, self.trade_quantity):
                            position = self.get_current_position(stock_code)
                            sell_qty = min(self.trade_quantity,
                                         position['可用数量'])
                            # 确保至少卖出10股
                            if sell_qty >= 10:
                                self.execute_trade(stock_code, 'sell',
                                                 sell_qty, current_price)
                        else:
                            self.log(f"{stock_code} 不可卖出（持仓不足）")

                    elif signal == 'buy':
                        # 检查持仓限制
                        if not self.check_position_limit(stock_code,
                                                        self.max_position):
                            self.log(f"{stock_code} 不可买入（达到持仓限制)")
                            continue

                        # 检查是否可以买入
                        if self.check_can_buy(stock_code,
                                            self.trade_quantity,
                                            current_price):
                            self.execute_trade(stock_code, 'buy',
                                             self.trade_quantity,
                                             current_price)
                        else:
                            self.log(f"{stock_code} 不可买入（资金不足）")

                except Exception as e:
                    self.log(f"处理{stock_code}时出错: {str(e)}")
                    continue

        except Exception as e:
            self.log(f"数据处理错误: {str(e)}")


def main():
    """
    主函数 - 用于测试策略
    """
    # 示例参数
    params = {
        '账户ID': '39020958',  # 需要修改为自己的账户
        '账户类型': 'STOCK',
        '股票池': ['511130.SH', '511090.SH'],  # 30年国债ETF
        '买入涨跌幅': -0.2,  # 下跌0.2%买入
        '卖出涨跌幅': 0.2,   # 上涨0.2%卖出
        '单次交易数量': 100,
        '最大持仓数量': 300,
        '价格模式': 5,  # 最新价
        '交易时间段': 8,  # 工作日
        '交易开始时间': 9,
        '交易结束时间': 24,
        '是否参加集合竞价': False,
        '是否测试': True,  # 测试模式，不保存日志
        '日志文件路径': os.path.join(
            os.path.dirname(__file__),
            'trade_log.json'
        )
    }

    # 创建策略实例
    strategy = 高频分时网格策略(params)

    # 运行策略
    strategy.start()


if __name__ == "__main__":
    main()
