# -*- coding: utf-8 -*-
"""
ATR动态网格策略
基于ATR指标和动态基准价格的网格交易策略
"""

import json
import time
from datetime import datetime
from pathlib import Path
from collections import deque
import easy_xt


class ATR动态网格策略:
    """
    基于ATR指标的动态网格交易策略

    核心特性：
    1. 根据ATR动态调整网格间距
    2. 智能调整基准价格
    3. 波动率自适应
    4. 趋势跟随机制
    """

    def __init__(self, params):
        """初始化策略"""
        # 基础参数
        self.account_id = params.get('账户ID')
        self.account_type = params.get('账户类型', 'STOCK')
        self.stock_pool = params.get('股票池', [])

        # QMT路径和会话ID
        self.qmt_path = params.get('QMT路径', '')
        self.session_id = params.get('会话ID', 'grid_session')

        # ATR参数
        self.atr_period = params.get('ATR周期', 14)           # ATR计算周期
        self.atr_multiplier = params.get('ATR倍数', 0.5)      # ATR倍数（网格间距 = ATR * 倍数）
        self.min_grid_spacing = params.get('最小网格间距', 0.1)  # 最小网格间距（%）
        self.max_grid_spacing = params.get('最大网格间距', 1.0)  # 最大网格间距（%）

        # 网格参数
        self.grid_layers = params.get('网格层数', 5)          # 单边网格层数
        self.position_size = params.get('单次交易数量', 100)   # 每次交易数量
        self.max_position = params.get('最大持仓数量', 1000)   # 最大持仓限制

        # 基准价格调整参数
        self.ma_period = params.get('均线周期', 20)            # 用于判断趋势的均线周期
        self.trend_threshold = params.get('趋势阈值', 0.5)    # 趋势判断阈值（%）

        # 价格模式
        self.price_mode = params.get('价格模式', 5)           # 5=最新价

        # 交易时间控制
        self.trade_period = params.get('交易时间段', 8)       # 8=工作日
        self.trade_start_hour = params.get('交易开始时间', 9)
        self.trade_end_hour = params.get('交易结束时间', 24)
        self.is_auction = params.get('是否参加集合竞价', False)

        # 日志和测试
        self.log_file = params.get('日志文件路径', 'strategies/grid_trading/atr_grid_log.json')
        self.is_test = params.get('是否测试', False)

        # 内部状态
        self.api = None
        self.base_prices = {}          # 各标的基准价格 {stock_code: base_price}
        self.current_atr = {}          # 各标的ATR值 {stock_code: atr}
        self.grid_spacing = {}         # 各标的网格间距（%）{stock_code: spacing}
        self.price_history = {}        # 各标的价格历史（用于计算ATR和MA）{stock_code: deque}
        self.last_action_time = {}     # 上次交易时间

        # 统计信息
        self.trade_count = 0
        self.start_time = datetime.now()

        # 初始化
        self.initialize()

    def initialize(self):
        """初始化策略"""
        print("=" * 60)
        print("ATR动态网格策略".center(50))
        print("=" * 60)

        # 初始化API连接
        try:
            self.api = easy_xt.get_api()

            # 初始化数据服务
            if hasattr(self.api, 'init_data'):
                if self.api.init_data():
                    print("✓ 数据服务初始化成功")
                else:
                    print("⚠ 警告: 数据服务初始化失败")

            # 初始化交易服务（需要QMT路径和会话ID）
            if hasattr(self.api, 'init_trade') and self.qmt_path:
                try:
                    print(f"尝试连接交易服务...")
                    print(f"  QMT路径: {self.qmt_path}")
                    print(f"  会话ID: {self.session_id}")

                    if self.api.init_trade(self.qmt_path, self.session_id):
                        print("✓ 交易服务初始化成功")

                        # 添加交易账户
                        if hasattr(self.api, 'add_account'):
                            if self.api.add_account(self.account_id, self.account_type):
                                print(f"✓ 交易账户 {self.account_id} 添加成功")
                            else:
                                print(f"⚠ 警告: 交易账户添加失败")
                    else:
                        print("⚠ 警告: 交易服务连接失败")
                        print("   请检查：")
                        print("   1. QMT客户端是否已启动")
                        print("   2. QMT路径是否正确")
                        print("   3. 账户是否已在QMT中登录")

                except Exception as e:
                    print(f"⚠ 警告: 交易服务初始化异常 - {str(e)}")
                    print("   提示: 请在QMT客户端手动登录交易账户")
            else:
                if not self.qmt_path:
                    print("⚠ 警告: 未配置QMT路径，无法连接交易服务")
                    print("   请在配置文件中添加 'QMT路径' 参数")
                else:
                    print("⚠ 警告: API不支持init_trade方法")

        except Exception as e:
            print(f"✗ 错误: API初始化异常 - {str(e)}")

        # 初始化价格历史队列
        max_history = max(self.atr_period, self.ma_period) + 5
        for stock in self.stock_pool:
            self.price_history[stock] = deque(maxlen=max_history)
            self.last_action_time[stock] = None

        # 加载或初始化基准价格
        self.load_state()

        print(f"\n策略参数:")
        print(f"  账户ID: {self.account_id}")
        print(f"  账户类型: {self.account_type}")
        print(f"  ATR周期: {self.atr_period}")
        print(f"  ATR倍数: {self.atr_multiplier}")
        print(f"  网格层数: {self.grid_layers}")
        print(f"  最小网格间距: {self.min_grid_spacing}%")
        print(f"  最大网格间距: {self.max_grid_spacing}%")
        print(f"  均线周期: {self.ma_period}")
        print(f"  股票池: {self.stock_pool}")
        print("=" * 60 + "\n")

    def calculate_atr(self, stock_code):
        """
        计算ATR指标
        返回: ATR值
        """
        history = self.price_history[stock_code]
        if len(history) < 2:
            return 0

        tr_list = []
        for i in range(1, len(history)):
            curr = history[i]
            prev = history[i-1]

            high = curr.get('最高价', curr.get('当前价格', 0))
            low = curr.get('最低价', curr.get('当前价格', 0))
            prev_close = prev.get('收盘价', prev.get('当前价格', 0))

            # 计算真实波动范围
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            tr_list.append(tr)

        if not tr_list:
            return 0

        # 计算ATR（使用简单移动平均）
        period = min(self.atr_period, len(tr_list))
        atr = sum(tr_list[-period:]) / period

        return atr

    def calculate_ma(self, stock_code):
        """
        计算移动平均线
        返回: MA值
        """
        history = self.price_history[stock_code]
        if len(history) < self.ma_period:
            # 数据不足，返回当前价格
            if history:
                return history[-1].get('当前价格', 0)
            return 0

        period = min(self.ma_period, len(history))
        sum_price = sum(h.get('当前价格', 0) for h in list(history)[-period:])
        ma = sum_price / period

        return ma

    def update_grid_spacing(self, stock_code, current_price):
        """
        根据ATR更新网格间距

        网格间距(%) = (ATR / 当前价格) * 100 * ATR倍数
        限制在最小和最大网格间距之间
        """
        atr = self.current_atr.get(stock_code, 0)
        if atr <= 0:
            # ATR未计算出来，使用默认间距
            spacing = 0.2
        else:
            # 基于ATR计算网格间距
            spacing = (atr / current_price) * 100 * self.atr_multiplier

        # 限制在最小和最大间距之间
        spacing = max(self.min_grid_spacing, min(self.max_grid_spacing, spacing))

        self.grid_spacing[stock_code] = spacing
        return spacing

    def update_base_price(self, stock_code, current_price):
        """
        智能调整基准价格

        策略：
        1. 如果价格突破MA，跟随趋势调整基准价
        2. 如果价格在MA附近，保持基准价稳定
        """
        ma = self.calculate_ma(stock_code)
        if ma <= 0:
            # MA未计算出来，使用当前价格作为基准价
            if stock_code not in self.base_prices:
                self.base_prices[stock_code] = current_price
            return

        current_base = self.base_prices.get(stock_code, current_price)
        ma_distance = ((current_price - ma) / ma) * 100

        # 趋势判断：价格偏离MA超过阈值
        if abs(ma_distance) > self.trend_threshold:
            # 价格远离MA，跟随趋势调整基准价
            new_base = ma
            if new_base != current_base:
                print(f"  [基准价调整] {stock_code}: {current_base:.3f} → {new_base:.3f} (MA={ma:.3f}, 偏离={ma_distance:.2f}%)")
                self.base_prices[stock_code] = new_base

    def get_grid_prices(self, stock_code):
        """
        获取当前网格价格列表

        返回: {买入网格: [...], 卖出网格: [...]}
        """
        base_price = self.base_prices.get(stock_code, 0)
        spacing = self.grid_spacing.get(stock_code, 0.2)

        if base_price <= 0:
            return {'买入网格': [], '卖出网格': []}

        buy_grids = []
        sell_grids = []

        # 生成买入网格（基准价下方）
        for i in range(1, self.grid_layers + 1):
            price = base_price * (1 - i * spacing / 100)
            buy_grids.append(price)

        # 生成卖出网格（基准价上方）
        for i in range(1, self.grid_layers + 1):
            price = base_price * (1 + i * spacing / 100)
            sell_grids.append(price)

        return {'买入网格': buy_grids, '卖出网格': sell_grids}

    def check_trade_signal(self, stock_code, current_price):
        """
        检查交易信号

        返回: 'buy', 'sell', 或 None
        """
        grids = self.get_grid_prices(stock_code)
        buy_grids = grids['买入网格']
        sell_grids = grids['卖出网格']

        # 检查买入信号：价格跌破买入网格
        for grid_price in reversed(buy_grids):  # 从最接近基准价的网格开始检查
            if current_price <= grid_price:
                return 'buy'

        # 检查卖出信号：价格突破卖出网格
        for grid_price in reversed(sell_grids):  # 从最接近基准价的网格开始检查
            if current_price >= grid_price:
                return 'sell'

        return None

    def get_position(self, stock_code):
        """获取持仓数量"""
        try:
            positions = self.api.trade.get_positions(self.account_id, stock_code)
            if positions is not None and not positions.empty:
                pos = positions.iloc[0]
                # 使用正确的列名：can_use_volume (可用持仓)
                return pos.get('can_use_volume', 0)
        except Exception as e:
            print(f"  ✗ 获取持仓失败: {str(e)}")
        return 0

    def get_available_cash(self):
        """获取可用资金"""
        try:
            account = self.api.trade.get_account_asset(self.account_id)
            return account.get('可用资金', 0)
        except Exception as e:
            print(f"  ✗ 获取资金失败: {str(e)}")
        return 0

    def place_order(self, stock_code, order_type, price):
        """下单"""
        try:
            # 检查持仓和资金
            position = self.get_position(stock_code)
            cash = self.get_available_cash()

            if order_type == 'buy':
                # 买入检查
                if position >= self.max_position:
                    print(f"  ⚠ 持仓已达上限 ({position}/{self.max_position})，取消买入")
                    return False

                required_cash = price * self.position_size * 1.01  # 预留1%费用
                if required_cash > cash:
                    print(f"  ⚠ 资金不足 (需{required_cash:.2f}, 可用{cash:.2f})，取消买入")
                    return False

                # 执行买入
                order_id = self.api.trade.order_stock(
                    account_id=self.account_id,
                    stock_code=stock_code,
                    order_type=0,  # 0=买入
                    order_volume=self.position_size,
                    price_type=self.price_mode,  # 使用指定价格模式
                    price=price
                )

                if order_id:
                    print(f"  ✓ 买入成功: {stock_code} @ {price:.3f} x{self.position_size} (委托号: {order_id})")
                    self.trade_count += 1
                    self.last_action_time[stock_code] = datetime.now()
                    return True
                else:
                    print(f"  ✗ 买入失败")
                    return False

            elif order_type == 'sell':
                # 卖出检查
                if position < self.position_size:
                    print(f"  ⚠ 持仓不足 (持仓{position}, 需卖{self.position_size})，取消卖出")
                    return False

                # 执行卖出
                order_id = self.api.trade.order_stock(
                    account_id=self.account_id,
                    stock_code=stock_code,
                    order_type=1,  # 1=卖出
                    order_volume=min(position, self.position_size),
                    price_type=self.price_mode,
                    price=price
                )

                if order_id:
                    print(f"  ✓ 卖出成功: {stock_code} @ {price:.3f} x{min(position, self.position_size)} (委托号: {order_id})")
                    self.trade_count += 1
                    self.last_action_time[stock_code] = datetime.now()
                    return True
                else:
                    print(f"  ✗ 卖出失败")
                    return False

        except Exception as e:
            print(f"  ✗ 下单异常: {str(e)}")
            return False

        return False

    def update_price_history(self, stock_code, tick_data):
        """
        更新价格历史数据

        tick_data应包含：当前价格, 最高价, 最低价, 收盘价
        """
        if not tick_data:
            return

        price_info = {
            '时间': datetime.now(),
            '当前价格': tick_data.get('当前价格', 0),
            '最高价': tick_data.get('最高价', tick_data.get('当前价格', 0)),
            '最低价': tick_data.get('最低价', tick_data.get('当前价格', 0)),
            '收盘价': tick_data.get('当前价格', 0)
        }

        self.price_history[stock_code].append(price_info)

    def load_state(self):
        """加载策略状态"""
        state_file = self.log_file.replace('.json', '_state.json')

        try:
            if Path(state_file).exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.base_prices = state.get('基准价格', {})
                    print(f"✓ 已加载策略状态 (基准价格: {self.base_prices})")
            else:
                print(f"ℹ 首次运行，将自动初始化基准价格")
        except Exception as e:
            print(f"⚠ 加载状态失败: {str(e)}")

    def save_state(self):
        """保存策略状态"""
        state_file = self.log_file.replace('.json', '_state.json')

        try:
            state = {
                '基准价格': self.base_prices,
                '最后更新': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠ 保存状态失败: {str(e)}")

    def is_trade_time(self):
        """判断是否在交易时间"""
        now = datetime.now()

        # 检查星期
        if self.trade_period == 8:  # 工作日
            if now.weekday() >= 5:  # 周六、周日
                return False
        elif now.weekday() != self.trade_period:
            return False

        # 检查小时
        if not (self.trade_start_hour <= now.hour < self.trade_end_hour):
            return False

        # 检查集合竞价
        if not self.is_auction:
            if now.hour == 9 and 15 <= now.minute <= 25:
                return False

        return True

    def run_bar(self):
        """主循环（每个bar调用一次）"""
        if not self.is_trade_time():
            return

        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ATR动态网格扫描")

        # 遍历股票池
        for stock_code in self.stock_pool:
            try:
                # 获取行情
                tick_data = self.api.data.get_current_price(stock_code)
                if not tick_data or not tick_data.get('当前价格'):
                    print(f"  {stock_code}: ⚠ 无法获取行情数据")
                    continue

                current_price = tick_data['当前价格']
                high_price = tick_data.get('最高价', current_price)
                low_price = tick_data.get('最低价', current_price)

                # 更新价格历史
                tick_data['最高价'] = max(current_price, high_price)
                tick_data['最低价'] = min(current_price, low_price)
                self.update_price_history(stock_code, tick_data)

                # 计算ATR
                atr = self.calculate_atr(stock_code)
                self.current_atr[stock_code] = atr

                # 初始化基准价格（首次运行）
                if stock_code not in self.base_prices:
                    self.base_prices[stock_code] = current_price
                    print(f"  {stock_code}: 初始化基准价 = {current_price:.3f}")
                    continue

                # 更新基准价格（智能调整）
                self.update_base_price(stock_code, current_price)

                # 更新网格间距
                spacing = self.update_grid_spacing(stock_code, current_price)

                # 显示当前状态
                base_price = self.base_prices[stock_code]
                position = self.get_position(stock_code)

                print(f"  {stock_code}:")
                print(f"    价格: {current_price:.3f} | 基准价: {base_price:.3f} | ATR: {atr:.4f} | 网格间距: {spacing:.3f}%")
                print(f"    持仓: {position} | 网格: {self.grid_layers}层 x{self.position_size}")

                # 检查交易信号
                signal = self.check_trade_signal(stock_code, current_price)

                if signal == 'buy':
                    print(f"    触发买入信号 @ {current_price:.3f}")
                    self.place_order(stock_code, 'buy', current_price)

                elif signal == 'sell':
                    print(f"    触发卖出信号 @ {current_price:.3f}")
                    self.place_order(stock_code, 'sell', current_price)
                else:
                    print(f"    无交易信号")

            except Exception as e:
                print(f"  {stock_code}: ✗ 处理异常 - {str(e)}")
                import traceback
                traceback.print_exc()

        # 保存状态
        self.save_state()

    def start(self):
        """启动策略"""
        print("\n" + "=" * 60)
        print("策略启动".center(50))
        print("=" * 60)
        print("\n开始监控市场...")
        print(f"交易时间: {self.trade_start_hour}:00 - {self.trade_end_hour}:00")
        print(f"按 Ctrl+C 停止策略\n")

        try:
            while True:
                self.run_bar()
                time.sleep(3)  # 3秒扫描一次

        except KeyboardInterrupt:
            print("\n\n" + "=" * 60)
            print("策略停止".center(50))
            print("=" * 60)

            # 统计信息
            duration = (datetime.now() - self.start_time).total_seconds() / 60
            print(f"\n运行时长: {duration:.1f}分钟")
            print(f"交易次数: {self.trade_count}")
            print(f"基准价格: {self.base_prices}")
            print(f"\n状态已保存到: {self.log_file.replace('.json', '_state.json')}")
            print("\n策略已安全退出")


# 测试代码
if __name__ == '__main__':
    # 配置参数
    params = {
        '账户ID': '39020958',
        '账户类型': 'STOCK',
        '股票池': ['511090.SH'],
        'ATR周期': 14,
        'ATR倍数': 0.5,
        '最小网格间距': 0.1,
        '最大网格间距': 0.8,
        '网格层数': 5,
        '单次交易数量': 100,
        '最大持仓数量': 500,
        '均线周期': 20,
        '趋势阈值': 0.3,
        '价格模式': 5,
        '交易时间段': 8,
        '交易开始时间': 9,
        '交易结束时间': 24,
        '是否参加集合竞价': False,
        '是否测试': True,
        '日志文件路径': 'strategies/grid_trading/atr_grid_log.json'
    }

    # 创建并启动策略
    strategy = ATR动态网格策略(params)
    strategy.start()
