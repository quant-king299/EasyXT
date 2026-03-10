"""
股票量化交易学习案例 - 真实数据获取与交易结合
完整的从数据获取到交易执行的学习案例

功能包括：
1. 数据获取模块（使用DataManager获取真实数据）
2. 技术指标计算
3. 交易信号生成
4. 交易执行（支持真实交易和模拟交易）
5. 风险管理
6. 交易监控

数据源支持：
- QMT本地数据（推荐，速度快）
- Tushare在线数据（需要token）
- DuckDB本地数据库（可选，极速）

作者：王者quant
日期：2025-01-09
更新：2025-03-10（改为使用真实数据）

=====================================================================
🔴🔴🔴 重要配置 - 在这里设置交易模式 🔴🔴🔴
=====================================================================

【交易模式配置】（找到这里！修改下面的配置）

# 配置1：数据模式
USE_REAL_DATA = True      # True=使用真实数据(QMT/Tushare/DuckDB)  False=使用模拟数据
                          # 建议：保持True，使用真实数据学习

# 配置2：交易模式
USE_REAL_TRADING = True  # False=模拟交易(零风险)  True=真实交易(有风险)
                          # ⚠️ 警告：True会真实下单，请谨慎！
                          # 建议：学习阶段保持False

【配置说明】
- 学习推荐：USE_REAL_DATA=True, USE_REAL_TRADING=False（真实数据+模拟交易）
- 快速测试：USE_REAL_DATA=False, USE_REAL_TRADING=False（模拟数据+模拟交易）
- 实盘运行：USE_REAL_DATA=True, USE_REAL_TRADING=True（真实数据+真实交易）
           ⚠️ 实盘需要QMT交易账号，有真实资金风险！

【如何启用真实交易】
方法1（推荐）：运行时使用命令行参数
  python 学习实例/10_数据获取与交易结合案例.py --real-trading

方法2：直接修改下面这行
  USE_REAL_TRADING = False  # 改成 True

【重要提示】
- 真实交易有风险，可能导致资金损失
- 建议先在模拟模式下充分测试策略
- 实盘前请确保理解策略逻辑和风险
- 使用小资金开始，逐步增加

=====================================================================
"""

# ==================== 配置区域（修改这里！）====================
USE_REAL_DATA = True       # 数据模式：True=真实数据，False=模拟数据
USE_REAL_TRADING = True   # 交易模式：False=模拟交易，True=真实交易⚠️
# ===============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys
import argparse
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入数据管理器
try:
    from easyxt_backtest import DataManager
    DATA_MANAGER_AVAILABLE = True
    print("✅ DataManager模块加载成功")
except ImportError as e:
    DATA_MANAGER_AVAILABLE = False
    print(f"⚠️ DataManager模块未找到: {e}")

# 导入交易API（可选）
try:
    import easy_xt
    EASY_XT_AVAILABLE = True
    print("[OK] easy_xt模块加载成功")
except ImportError as e:
    EASY_XT_AVAILABLE = False
    print(f"[WARNING] easy_xt模块未找到: {e}")

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

class TradingStrategy:
    """交易策略类 - 整合数据获取、信号生成和交易执行"""

    def __init__(self, use_real_trading=False, use_real_data=True):
        """
        初始化交易策略

        Args:
            use_real_trading (bool): 是否使用真实交易，默认False使用模拟
            use_real_data (bool): 是否使用真实数据，默认True
        """
        self.use_real_trading = use_real_trading
        self.use_real_data = use_real_data and DATA_MANAGER_AVAILABLE
        self.data_dir = "data"
        self.log_dir = "logs"

        # 创建必要目录
        for dir_path in [self.data_dir, self.log_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

        # 初始化数据管理器
        if self.use_real_data:
            try:
                self.data_manager = DataManager()
                print("✅ DataManager初始化成功")
            except Exception as e:
                print(f"❌ DataManager初始化失败: {e}")
                self.use_real_data = False
                print("📝 将使用模拟数据")

        # 初始化交易接口
        if self.use_real_trading and EASY_XT_AVAILABLE:
            try:
                # 使用真实交易API的适配器（使用easy_xt基础API）
                self.trader = RealTradeAdapter()
                print("  [信息] 真实交易模式已启用")
            except Exception as e:
                print(f"  [错误] 真实交易初始化失败: {e}")
                self.use_real_trading = False
                print("  [提示] 切换到模拟交易模式")

        if not self.use_real_trading:
            self.trader = MockTrader()
            print("  [信息] 模拟交易模式已启用")

        # 交易参数
        self.position = {}  # 持仓信息
        self.cash = 100000  # 初始资金
        self.trade_log = []  # 交易记录

        data_mode = "真实数据" if self.use_real_data else "模拟数据"
        trade_mode = "真实交易" if self.use_real_trading else "模拟交易"
        print(f"🚀 交易策略初始化完成 - {data_mode}/{trade_mode}模式")
    
    def load_sample_data(self, stock_code='000001', start_date=None, end_date=None):
        """
        加载股票数据（优先使用真实数据）

        Args:
            stock_code (str): 股票代码
            start_date (str): 开始日期，格式YYYYMMDD，默认60天前
            end_date (str): 结束日期，格式YYYYMMDD，默认今天

        Returns:
            pd.DataFrame: 股票数据
        """
        try:
            # 如果使用真实数据
            if self.use_real_data:
                print(f"📊 使用DataManager获取真实数据...")

                # 设置默认日期范围
                if end_date is None:
                    end_date = datetime.now().strftime('%Y%m%d')
                if start_date is None:
                    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')

                # 获取数据
                data = self.data_manager.get_price(
                    codes=stock_code,
                    start_date=start_date,
                    end_date=end_date
                )

                if data is not None and not data.empty:
                    # 处理MultiIndex
                    if isinstance(data.index, pd.MultiIndex):
                        data = data.reset_index()

                    # 标准化列名和索引
                    if 'date' in data.columns:
                        # 检查date列是否为时间戳（整数）
                        if pd.api.types.is_integer_dtype(data['date']):
                            # 毫秒级时间戳转换（QMT返回的是毫秒级时间戳）
                            # 判断是否为毫秒级（大于10000000000）或秒级时间戳
                            first_timestamp = data['date'].iloc[0]
                            if first_timestamp > 10000000000:  # 毫秒级
                                data['date'] = pd.to_datetime(data['date'], unit='ms')
                            else:  # 秒级
                                data['date'] = pd.to_datetime(data['date'], unit='s')
                        else:
                            data['date'] = pd.to_datetime(data['date'])

                        # 设置索引
                        data.set_index('date', inplace=True)

                    # 确保必要的列存在
                    required_columns = ['open', 'high', 'low', 'close', 'volume']
                    missing_columns = [col for col in required_columns if col not in data.columns]

                    if missing_columns:
                        print(f"⚠️ 数据缺少以下列: {missing_columns}")
                        return self._generate_sample_data(stock_code)

                    print(f"✅ 成功加载真实数据: {len(data)} 条记录")
                    print(f"📅 数据范围: {data.index[0].strftime('%Y-%m-%d')} 至 {data.index[-1].strftime('%Y-%m-%d')}")
                    return data
                else:
                    print(f"⚠️ 未能获取到真实数据，使用模拟数据")

            # 使用模拟数据
            print("📊 生成模拟股票数据...")
            return self._generate_sample_data(stock_code)

        except Exception as e:
            print(f"❌ 加载数据失败: {e}")
            print("📊 使用模拟数据...")
            return self._generate_sample_data(stock_code)
    
    def _generate_sample_data(self, stock_code, days=60):
        """
        生成模拟股票数据

        ⚠️ 警告：这是模拟数据，仅供学习和测试使用！
        实盘交易请务必使用真实数据！
        """
        print(f"⚠️ 生成 {days} 天的模拟数据（仅供学习使用）")

        # 生成日期序列（仅包含工作日）
        dates = pd.date_range(end=datetime.now(), periods=days * 7 // 5, freq='B')

        # 生成价格数据 (随机游走)
        np.random.seed(42)  # 固定随机种子以便复现

        initial_price = 10.0
        returns = np.random.normal(0.001, 0.02, len(dates))  # 日收益率
        prices = [initial_price]

        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))

        # 生成OHLC数据
        data = []
        for i, (date, close) in enumerate(zip(dates, prices)):
            high = close * (1 + abs(np.random.normal(0, 0.01)))
            low = close * (1 - abs(np.random.normal(0, 0.01)))
            open_price = prices[i-1] if i > 0 else close
            volume = np.random.randint(1000000, 10000000)

            data.append({
                'open': open_price,
                'high': max(open_price, high, close),
                'low': min(open_price, low, close),
                'close': close,
                'volume': volume
            })

        df = pd.DataFrame(data, index=dates)

        # 保存模拟数据
        filename = f"{self.data_dir}/{stock_code}_sample_data.csv"
        df.to_csv(filename)
        print(f"✅ 模拟数据已保存到 {filename}")
        print("⚠️ 提醒：这是模拟数据，实盘请使用真实数据！")

        return df
    
    def calculate_indicators(self, data):
        """
        计算技术指标
        
        Args:
            data (pd.DataFrame): 原始股票数据
            
        Returns:
            pd.DataFrame: 添加技术指标的数据
        """
        print("📈 计算技术指标...")
        
        try:
            # 移动平均线
            data['MA5'] = data['close'].rolling(window=5).mean()
            data['MA10'] = data['close'].rolling(window=10).mean()
            data['MA20'] = data['close'].rolling(window=20).mean()
            
            # RSI指标
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            data['RSI'] = 100 - (100 / (1 + rs))
            
            # MACD指标
            exp1 = data['close'].ewm(span=12).mean()
            exp2 = data['close'].ewm(span=26).mean()
            data['MACD'] = exp1 - exp2
            data['MACD_signal'] = data['MACD'].ewm(span=9).mean()
            data['MACD_hist'] = data['MACD'] - data['MACD_signal']
            
            # 布林带
            data['BB_middle'] = data['close'].rolling(window=20).mean()
            bb_std = data['close'].rolling(window=20).std()
            data['BB_upper'] = data['BB_middle'] + (bb_std * 2)
            data['BB_lower'] = data['BB_middle'] - (bb_std * 2)
            
            # 成交量指标
            data['VOL_MA5'] = data['volume'].rolling(window=5).mean()
            
            print("✅ 技术指标计算完成")
            return data
            
        except Exception as e:
            print(f"❌ 计算技术指标失败: {e}")
            return data
    
    def generate_signals(self, data):
        """
        生成交易信号
        
        Args:
            data (pd.DataFrame): 包含技术指标的数据
            
        Returns:
            pd.DataFrame: 添加交易信号的数据
        """
        print("🎯 生成交易信号...")
        
        try:
            # 初始化信号列
            data['signal'] = 0  # 0: 无信号, 1: 买入, -1: 卖出
            data['signal_strength'] = 0  # 信号强度 0-100
            
            # 策略1: 移动平均线交叉
            ma_cross_buy = (data['MA5'] > data['MA10']) & (data['MA5'].shift(1) <= data['MA10'].shift(1))
            ma_cross_sell = (data['MA5'] < data['MA10']) & (data['MA5'].shift(1) >= data['MA10'].shift(1))
            
            # 策略2: RSI超买超卖
            rsi_oversold = data['RSI'] < 30
            rsi_overbought = data['RSI'] > 70
            
            # 策略3: MACD金叉死叉
            macd_golden = (data['MACD'] > data['MACD_signal']) & (data['MACD'].shift(1) <= data['MACD_signal'].shift(1))
            macd_death = (data['MACD'] < data['MACD_signal']) & (data['MACD'].shift(1) >= data['MACD_signal'].shift(1))
            
            # 策略4: 布林带突破
            bb_break_up = data['close'] > data['BB_upper']
            bb_break_down = data['close'] < data['BB_lower']
            
            # 综合信号生成
            buy_signals = ma_cross_buy | (rsi_oversold & macd_golden) | bb_break_down
            sell_signals = ma_cross_sell | (rsi_overbought & macd_death) | bb_break_up
            
            # 设置信号
            data.loc[buy_signals, 'signal'] = 1
            data.loc[sell_signals, 'signal'] = -1
            
            # 计算信号强度
            for idx in data.index:
                if data.loc[idx, 'signal'] != 0:
                    strength = 0
                    
                    # MA信号强度
                    if ma_cross_buy.loc[idx] or ma_cross_sell.loc[idx]:
                        strength += 25
                    
                    # RSI信号强度
                    if rsi_oversold.loc[idx] or rsi_overbought.loc[idx]:
                        strength += 25
                    
                    # MACD信号强度
                    if macd_golden.loc[idx] or macd_death.loc[idx]:
                        strength += 25
                    
                    # 布林带信号强度
                    if bb_break_up.loc[idx] or bb_break_down.loc[idx]:
                        strength += 25
                    
                    data.loc[idx, 'signal_strength'] = min(strength, 100)
            
            # 统计信号
            buy_count = (data['signal'] == 1).sum()
            sell_count = (data['signal'] == -1).sum()
            
            print(f"✅ 信号生成完成: 买入信号 {buy_count} 个, 卖出信号 {sell_count} 个")
            return data
            
        except Exception as e:
            print(f"❌ 生成交易信号失败: {e}")
            return data
    
    def execute_trades(self, data, stock_code):
        """
        执行交易
        
        Args:
            data (pd.DataFrame): 包含交易信号的数据
            stock_code (str): 股票代码
        """
        print("💼 开始执行交易...")
        
        executed_trades = 0
        
        for idx, row in data.iterrows():
            if row['signal'] != 0:
                try:
                    if row['signal'] == 1:  # 买入信号
                        result = self._execute_buy(stock_code, row['close'], row['signal_strength'], idx)
                        if result:
                            executed_trades += 1
                    
                    elif row['signal'] == -1:  # 卖出信号
                        result = self._execute_sell(stock_code, row['close'], row['signal_strength'], idx)
                        if result:
                            executed_trades += 1
                            
                except Exception as e:
                    print(f"❌ 执行交易失败 {idx}: {e}")
                    continue
        
        print(f"✅ 交易执行完成，共执行 {executed_trades} 笔交易")
        self._save_trade_log()
    
    def _execute_buy(self, stock_code, price, strength, date):
        """执行买入操作"""
        try:
            # 计算买入数量 (基于信号强度和可用资金)
            max_position_value = self.cash * 0.3  # 最大单笔投资30%资金
            position_ratio = strength / 100 * 0.5  # 根据信号强度调整仓位
            buy_value = max_position_value * position_ratio
            quantity = int(buy_value / price / 100) * 100  # 整手买入
            
            if quantity < 100 or buy_value > self.cash:
                return False
            
            # 执行买入
            if self.use_real_trading:
                # 真实交易
                success = self.trader.buy(stock_code, price, quantity)
            else:
                # 模拟交易
                success = self.trader.buy(stock_code, price, quantity)
            
            if success:
                # 更新持仓和资金
                if stock_code not in self.position:
                    self.position[stock_code] = {'quantity': 0, 'avg_price': 0}
                
                old_quantity = self.position[stock_code]['quantity']
                old_avg_price = self.position[stock_code]['avg_price']
                
                new_quantity = old_quantity + quantity
                new_avg_price = ((old_quantity * old_avg_price) + (quantity * price)) / new_quantity
                
                self.position[stock_code]['quantity'] = new_quantity
                self.position[stock_code]['avg_price'] = new_avg_price
                self.cash -= quantity * price
                
                # 记录交易
                trade_record = {
                    'date': date,
                    'stock_code': stock_code,
                    'action': 'BUY',
                    'price': price,
                    'quantity': quantity,
                    'amount': quantity * price,
                    'signal_strength': strength,
                    'cash_after': self.cash
                }
                self.trade_log.append(trade_record)
                
                print(f"  ✅ 买入 {stock_code}: {quantity}股 @ {price:.2f}, 强度: {strength}")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ 买入操作失败: {e}")
            return False
    
    def _execute_sell(self, stock_code, price, strength, date):
        """执行卖出操作"""
        try:
            if stock_code not in self.position or self.position[stock_code]['quantity'] <= 0:
                return False
            
            # 计算卖出数量 (基于信号强度和持仓)
            current_quantity = self.position[stock_code]['quantity']
            sell_ratio = strength / 100 * 0.8  # 根据信号强度调整卖出比例
            quantity = int(current_quantity * sell_ratio / 100) * 100  # 整手卖出
            
            if quantity < 100:
                quantity = current_quantity  # 全部卖出
            
            # 执行卖出
            if self.use_real_trading:
                # 真实交易
                success = self.trader.sell(stock_code, price, quantity)
            else:
                # 模拟交易
                success = self.trader.sell(stock_code, price, quantity)
            
            if success:
                # 更新持仓和资金
                self.position[stock_code]['quantity'] -= quantity
                self.cash += quantity * price
                
                # 记录交易
                trade_record = {
                    'date': date,
                    'stock_code': stock_code,
                    'action': 'SELL',
                    'price': price,
                    'quantity': quantity,
                    'amount': quantity * price,
                    'signal_strength': strength,
                    'cash_after': self.cash
                }
                self.trade_log.append(trade_record)
                
                print(f"  ✅ 卖出 {stock_code}: {quantity}股 @ {price:.2f}, 强度: {strength}")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ 卖出操作失败: {e}")
            return False
    
    def _save_trade_log(self):
        """保存交易记录"""
        if self.trade_log:
            df = pd.DataFrame(self.trade_log)
            filename = f"{self.log_dir}/trade_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False)
            print(f"📁 交易记录已保存到 {filename}")
    
    def analyze_performance(self):
        """分析交易绩效"""
        print("\n" + "=" * 50)
        print("📊 交易绩效分析")
        print("=" * 50)
        
        if not self.trade_log:
            print("❌ 无交易记录")
            return
        
        df = pd.DataFrame(self.trade_log)
        
        # 基本统计
        total_trades = len(df)
        buy_trades = len(df[df['action'] == 'BUY'])
        sell_trades = len(df[df['action'] == 'SELL'])
        
        print(f"📈 总交易次数: {total_trades}")
        print(f"📈 买入次数: {buy_trades}")
        print(f"📈 卖出次数: {sell_trades}")
        
        # 资金变化
        initial_cash = 100000
        final_cash = self.cash
        total_position_value = sum([pos['quantity'] * pos['avg_price'] for pos in self.position.values()])
        total_value = final_cash + total_position_value
        
        print(f"💰 初始资金: {initial_cash:,.2f}")
        print(f"💰 剩余现金: {final_cash:,.2f}")
        print(f"💰 持仓市值: {total_position_value:,.2f}")
        print(f"💰 总资产: {total_value:,.2f}")
        print(f"📊 总收益率: {((total_value - initial_cash) / initial_cash * 100):+.2f}%")
        
        # 持仓情况
        if self.position:
            print(f"\n📋 当前持仓:")
            for stock, pos in self.position.items():
                if pos['quantity'] > 0:
                    print(f"  {stock}: {pos['quantity']}股, 成本价: {pos['avg_price']:.2f}")
    
    def visualize_results(self, data, stock_code):
        """可视化交易结果"""
        print("📈 绘制交易结果图表...")
        
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
            
            # 1. 价格走势和交易信号
            ax1.plot(data.index, data['close'], label='收盘价', linewidth=2, color='blue')
            ax1.plot(data.index, data['MA5'], label='MA5', alpha=0.7, color='orange')
            ax1.plot(data.index, data['MA20'], label='MA20', alpha=0.7, color='red')
            
            # 标记买卖点
            buy_signals = data[data['signal'] == 1]
            sell_signals = data[data['signal'] == -1]
            
            ax1.scatter(buy_signals.index, buy_signals['close'], 
                       color='green', marker='^', s=100, label='买入信号', zorder=5)
            ax1.scatter(sell_signals.index, sell_signals['close'], 
                       color='red', marker='v', s=100, label='卖出信号', zorder=5)
            
            ax1.set_title(f'{stock_code} 价格走势与交易信号', fontsize=14)
            ax1.set_ylabel('价格 (元)')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 2. RSI指标
            ax2.plot(data.index, data['RSI'], color='purple', label='RSI')
            ax2.axhline(y=70, color='r', linestyle='--', alpha=0.7, label='超买线(70)')
            ax2.axhline(y=30, color='g', linestyle='--', alpha=0.7, label='超卖线(30)')
            ax2.set_title('RSI指标')
            ax2.set_ylabel('RSI')
            ax2.set_ylim(0, 100)
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            # 3. MACD指标
            ax3.plot(data.index, data['MACD'], color='blue', label='MACD')
            ax3.plot(data.index, data['MACD_signal'], color='red', label='Signal')
            ax3.bar(data.index, data['MACD_hist'], alpha=0.6, color='green', label='Histogram')
            ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax3.set_title('MACD指标')
            ax3.set_ylabel('MACD')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            # 4. 交易统计
            if self.trade_log:
                trade_df = pd.DataFrame(self.trade_log)
                trade_df['date'] = pd.to_datetime(trade_df['date'])
                
                # 按日期统计交易金额
                daily_trades = trade_df.groupby(trade_df['date'].dt.date)['amount'].sum()
                ax4.bar(daily_trades.index, daily_trades.values, alpha=0.7, color='skyblue')
                ax4.set_title('每日交易金额')
                ax4.set_ylabel('交易金额 (元)')
                ax4.tick_params(axis='x', rotation=45)
            else:
                ax4.text(0.5, 0.5, '无交易记录', ha='center', va='center', transform=ax4.transAxes)
                ax4.set_title('交易统计')
            
            ax4.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # 保存图表
            chart_filename = f"{self.data_dir}/{stock_code}_trading_results.png"
            plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
            plt.show()
            
            print(f"✅ 图表已保存到 {chart_filename}")
            
        except Exception as e:
            print(f"❌ 绘制图表失败: {e}")


class RealTradeAdapter:
    """真实交易API适配器 - 使用easy_xt基础API（与02_交易基础.py相同）"""

    def __init__(self):
        self.api = None
        self.connected = False
        self.account_id = None

        try:
            import json
            from pathlib import Path

            # 获取easy_xt API（与02_交易基础.py相同的方式）
            self.api = easy_xt.get_api()
            print("  [API] API实例创建成功")

            # 读取配置
            project_root = Path(__file__).parent.parent
            config_path = project_root / 'config' / 'unified_config.json'

            userdata_path = None
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    userdata_path = config.get('settings', {}).get('account', {}).get('qmt_path')
                    self.account_id = config.get('settings', {}).get('account', {}).get('account_id')

            if not userdata_path:
                userdata_path = r'D:\国金QMT交易端模拟\userdata_mini'

            print(f"  [配置] QMT路径: {userdata_path}")
            print(f"  [配置] 账户ID: {self.account_id}")

            # 初始化数据服务
            try:
                data_success = self.api.init_data()
                if data_success:
                    print("  [成功] 数据服务初始化成功")
                else:
                    print("  [警告] 数据服务初始化失败，继续尝试")
            except Exception as e:
                print(f"  [警告] 数据服务初始化异常: {e}")

            # 初始化交易服务（与02_交易基础.py相同）
            try:
                trade_success = self.api.init_trade(userdata_path, 'learning_session')
                if trade_success:
                    print("  [成功] 交易服务初始化成功")
                    self.connected = True
                else:
                    print("  [失败] 交易服务初始化失败")
                    print("  [提示] 请确保QMT客户端已启动并登录")
                    return
            except Exception as e:
                print(f"  [异常] 交易服务初始化异常: {e}")
                print("  [提示] 请确保QMT客户端已启动并登录")
                return

            # 添加账户（与02_交易基础.py相同）
            if self.account_id:
                try:
                    add_success = self.api.add_account(self.account_id, 'STOCK')
                    if add_success:
                        print(f"  [成功] 交易账户添加成功: {self.account_id}")
                    else:
                        print(f"  [警告] 交易账户添加失败")
                except Exception as e:
                    print(f"  [警告] 添加交易账户异常: {e}")

            # 检查交易时间（与02_交易基础.py相同的逻辑）
            try:
                from datetime import datetime
                now = datetime.now()
                current_hour = now.hour
                current_minute = now.minute
                current_weekday = now.weekday()

                is_weekend = current_weekday >= 5  # 周六周日
                morning = (9 < current_hour < 11) or (current_hour == 9 and current_minute >= 30) or (current_hour == 11 and current_minute <= 30)
                afternoon = (13 <= current_hour < 15)
                is_trading_time = morning or afternoon

                now_str = now.strftime('%Y-%m-%d %H:%M:%S')
                weekday_str = ['一', '二', '三', '四', '五', '六', '日'][current_weekday]
                print(f"  [时间] {now_str} 星期{weekday_str}")

                if is_weekend:
                    print(f"  [警告] 今天是周末，市场不开盘")
                elif is_trading_time:
                    print(f"  [信息] 当前在交易时间，可以正常交易")
                else:
                    print(f"  [警告] 当前不在交易时间")
                    print(f"  [信息] 交易时间: 周一至周五 9:30-11:30, 13:00-15:00")
            except Exception as e:
                print(f"  [警告] 检查交易时间失败: {e}")

        except Exception as e:
            print(f"  [错误] 初始化失败: {e}")
            import traceback
            traceback.print_exc()

    def buy(self, stock_code, price, quantity):
        """买入（与02_交易基础.py相同的调用方式）"""
        if not self.connected or not self.api:
            print("  [错误] 未连接交易服务")
            return False

        if not self.account_id:
            print("  [错误] 未设置账户ID")
            return False

        try:
            print(f"  [下单] 买入 {stock_code} {quantity}股 @ {price:.2f}元")

            # 使用easy_xt的buy方法（与02_交易基础.py完全相同）
            order_id = self.api.buy(
                account_id=self.account_id,
                code=stock_code,
                volume=quantity,
                price=price,
                price_type='limit'  # 限价单
            )

            if order_id:
                print(f"  [成功] 委托成功，订单号: {order_id}")
                return True
            else:
                print(f"  [失败] 委托失败")
                return False

        except Exception as e:
            print(f"  [错误] 买入失败: {e}")
            return False

    def sell(self, stock_code, price, quantity):
        """卖出（与02_交易基础.py相同的调用方式）"""
        if not self.connected or not self.api:
            print("  [错误] 未连接交易服务")
            return False

        if not self.account_id:
            print("  [错误] 未设置账户ID")
            return False

        try:
            print(f"  [下单] 卖出 {stock_code} {quantity}股 @ {price:.2f}元")

            # 使用easy_xt的sell方法（与02_交易基础.py完全相同）
            order_id = self.api.sell(
                account_id=self.account_id,
                code=stock_code,
                volume=quantity,
                price=price,
                price_type='limit'  # 限价单
            )

            if order_id:
                print(f"  [成功] 委托成功，订单号: {order_id}")
                return True
            else:
                print(f"  [失败] 委托失败")
                return False

        except Exception as e:
            print(f"  [错误] 卖出失败: {e}")
            return False


class MockTrader:
    """模拟交易器 - 用于学习测试"""

    def __init__(self):
        self.orders = []
        self.cash = 100000  # 模拟初始资金
        self.position = {}  # 模拟持仓
        print("📝 模拟交易器初始化完成")

    def buy(self, stock_code, price, quantity):
        """模拟买入"""
        # 检查资金是否足够
        required_cash = price * quantity
        if required_cash > self.cash:
            print(f"  ⚠️ 资金不足：需要 {required_cash:.2f}，可用 {self.cash:.2f}")
            return False

        # 模拟买入成功
        order = {
            'stock_code': stock_code,
            'action': 'BUY',
            'price': price,
            'quantity': quantity,
            'amount': required_cash,
            'timestamp': datetime.now(),
            'status': 'filled'
        }
        self.orders.append(order)

        # 更新模拟资金和持仓
        self.cash -= required_cash
        if stock_code not in self.position:
            self.position[stock_code] = {'quantity': 0, 'total_cost': 0}

        old_quantity = self.position[stock_code]['quantity']
        old_total_cost = self.position[stock_code]['total_cost']

        self.position[stock_code]['quantity'] = old_quantity + quantity
        self.position[stock_code]['total_cost'] = old_total_cost + required_cash

        return True

    def sell(self, stock_code, price, quantity):
        """模拟卖出"""
        # 检查持仓是否足够
        if stock_code not in self.position or self.position[stock_code]['quantity'] < quantity:
            print(f"  ⚠️ 持仓不足：想要卖出 {quantity}，持有 {self.position.get(stock_code, {}).get('quantity', 0)}")
            return False

        # 模拟卖出成功
        order = {
            'stock_code': stock_code,
            'action': 'SELL',
            'price': price,
            'quantity': quantity,
            'amount': price * quantity,
            'timestamp': datetime.now(),
            'status': 'filled'
        }
        self.orders.append(order)

        # 更新模拟资金和持仓
        self.cash += price * quantity
        self.position[stock_code]['quantity'] -= quantity

        return True


def main():
    """主函数 - 完整的交易策略演示"""

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='股票量化交易学习案例')
    parser.add_argument('--real-trading', action='store_true',
                       help='启用真实交易模式（默认为模拟交易）')
    parser.add_argument('--sim-data', action='store_true',
                       help='使用模拟数据（默认使用真实数据）')
    parser.add_argument('--stock', type=str, default='000001',
                       help='股票代码（默认：000001）')
    args = parser.parse_args()

    # 初始化交易策略配置
    # 优先使用命令行参数，否则使用文件开头的配置
    use_real_data = not args.sim_data if args.sim_data else USE_REAL_DATA
    use_real_trading = args.real_trading if args.real_trading else USE_REAL_TRADING

    print("=" * 60)
    print("股票量化交易学习案例 - 数据获取与交易结合")
    print("=" * 60)
    print()
    print("[当前配置]")
    print(f"  - 数据模式：{'[OK] 真实数据' if use_real_data else '[TEST] 模拟数据'}")
    print(f"  - 交易模式：{'[WARNING] 真实交易（有风险！）' if use_real_trading else '[OK] 模拟交易（零风险）'}")
    print()
    if use_real_trading:
        print("  [!!!] 警告：已启用真实交易模式 [!!!]")
        print()
    print("[提示]")
    print("  - 配置位置：文件开头第 37-38 行")
    print("  - 或使用命令行：python 10_数据获取与交易结合案例.py --real-trading")
    print()

    # 如果启用真实交易，显示警告
    if use_real_trading:
        print("=" * 60)
        print("🔴🔴🔴 警告：真实交易模式 🔴🔴🔴")
        print("=" * 60)
        print("您即将启用真实交易模式，这会产生真实资金交易！")
        print()
        print("⚠️ 风险提示：")
        print("  1. 真实交易可能导致资金损失")
        print("  2. 策略表现可能与历史回测不同")
        print("  3. 市场波动可能导致意外亏损")
        print("  4. 请确保您已充分测试策略")
        print()
        print("建议：")
        print("  - 先用模拟交易充分测试")
        print("  - 使用小资金验证策略")
        print("  - 设置止损止盈")
        print()

        # 要求用户确认
        confirm = input("确认要启用真实交易吗？(输入 'YES' 确认): ")
        if confirm != 'YES':
            print("❌ 已取消，将使用模拟交易模式")
            use_real_trading = False
        else:
            print("✅ 已启用真实交易模式")
        print("=" * 60)
        print()

    strategy = TradingStrategy(
        use_real_data=use_real_data,
        use_real_trading=use_real_trading
    )

    # 测试股票
    stock_code = args.stock

    print("\n" + "=" * 40)
    print("📊 第一步：加载股票数据")
    print("=" * 40)

    # 加载数据（可指定日期范围）
    data = strategy.load_sample_data(
        stock_code=stock_code,
        # start_date='20240101',  # 可选：指定开始日期
        # end_date='20241231'     # 可选：指定结束日期
    )
    if data.empty:
        print("❌ 无法获取股票数据")
        return
    
    print(f"✅ 数据加载完成，共 {len(data)} 条记录")
    print(f"📅 数据范围: {data.index[0].strftime('%Y-%m-%d')} 至 {data.index[-1].strftime('%Y-%m-%d')}")
    
    print("\n" + "=" * 40)
    print("📈 第二步：计算技术指标")
    print("=" * 40)
    
    # 计算技术指标
    data = strategy.calculate_indicators(data)
    
    print("\n" + "=" * 40)
    print("🎯 第三步：生成交易信号")
    print("=" * 40)
    
    # 生成交易信号
    data = strategy.generate_signals(data)
    
    print("\n" + "=" * 40)
    print("💼 第四步：执行交易")
    print("=" * 40)
    
    # 执行交易
    strategy.execute_trades(data, stock_code)
    
    print("\n" + "=" * 40)
    print("📊 第五步：绩效分析")
    print("=" * 40)
    
    # 分析绩效
    strategy.analyze_performance()
    
    print("\n" + "=" * 40)
    print("📈 第六步：结果可视化")
    print("=" * 40)
    
    # 可视化结果
    strategy.visualize_results(data, stock_code)
    
    print("\n" + "=" * 60)
    print("✅ 完整交易策略演示完成！")
    print("📁 所有文件已保存到相应目录")
    print()
    print("📊 数据模式：", "真实数据" if strategy.use_real_data else "模拟数据")
    print("💼 交易模式：", "真实交易" if strategy.use_real_trading else "模拟交易")
    print()
    print("💡 使用建议：")
    print("  1. 学习阶段：使用真实数据 + 模拟交易")
    print("  2. 测试阶段：使用真实数据 + 模拟交易，验证策略")
    print("  3. 实盘阶段：充分测试后，使用真实数据 + 真实交易")
    print()
    print("🔄 您可以：")
    print("  - 修改策略参数来测试不同的交易策略")
    print("  - 更换股票代码来分析不同标的")
    print("  - 调整日期范围来测试不同时间段")
    print("=" * 60)


if __name__ == "__main__":
    main()