"""
股票量化交易学习案例 - 数据获取与easy_xt交易结合
完整的从数据获取到交易执行的学习案例

功能包括：
1. 数据获取模块 (使用现有数据或akshare)
2. 技术指标计算
3. 交易信号生成
4. easy_xt交易执行
5. 风险管理
6. 交易监控

作者：CodeBuddy
日期：2025-01-09
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 添加easy_xt路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'easy_xt'))

try:
    from easy_xt.EasyXT import EasyXT
    EASY_XT_AVAILABLE = True
    print("✅ easy_xt模块加载成功")
except ImportError as e:
    EASY_XT_AVAILABLE = False
    print(f"⚠️ easy_xt模块未找到: {e}")
    print("📝 将使用模拟交易模式")

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

class TradingStrategy:
    """交易策略类 - 整合数据获取、信号生成和交易执行"""
    
    def __init__(self, use_real_trading=False):
        """
        初始化交易策略
        
        Args:
            use_real_trading (bool): 是否使用真实交易，默认False使用模拟
        """
        self.use_real_trading = use_real_trading and EASY_XT_AVAILABLE
        self.data_dir = "data"
        self.log_dir = "logs"
        
        # 创建必要目录
        for dir_path in [self.data_dir, self.log_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        
        # 初始化交易接口
        if self.use_real_trading:
            try:
                self.trader = EasyXT()
                print("✅ EasyXT交易接口初始化成功")
            except Exception as e:
                print(f"❌ EasyXT初始化失败: {e}")
                self.use_real_trading = False
                print("📝 切换到模拟交易模式")
        
        if not self.use_real_trading:
            self.trader = MockTrader()
            print("📝 使用模拟交易模式")
        
        # 交易参数
        self.position = {}  # 持仓信息
        self.cash = 100000  # 初始资金
        self.trade_log = []  # 交易记录
        
        print(f"🚀 交易策略初始化完成 - {'真实交易' if self.use_real_trading else '模拟交易'}模式")
    
    def load_sample_data(self, stock_code='000001'):
        """
        加载示例数据 (使用现有CSV文件或生成模拟数据)
        
        Args:
            stock_code (str): 股票代码
            
        Returns:
            pd.DataFrame: 股票数据
        """
        try:
            # 尝试加载现有数据文件
            csv_files = [
                f"{stock_code}_SZ_data.csv",
                f"{stock_code}_SH_data.csv",
                f"{self.data_dir}/{stock_code}_historical.csv"
            ]
            
            for csv_file in csv_files:
                if os.path.exists(csv_file):
                    print(f"📊 加载现有数据文件: {csv_file}")
                    data = pd.read_csv(csv_file, index_col=0, parse_dates=True)
                    
                    # 标准化列名
                    if 'close' not in data.columns and '收盘' in data.columns:
                        data = data.rename(columns={
                            '开盘': 'open', '最高': 'high', '最低': 'low', 
                            '收盘': 'close', '成交量': 'volume'
                        })
                    
                    if len(data) > 0:
                        print(f"✅ 成功加载 {len(data)} 条数据")
                        return data
            
            # 如果没有现有数据，生成模拟数据
            print("📊 生成模拟股票数据...")
            return self._generate_sample_data(stock_code)
            
        except Exception as e:
            print(f"❌ 加载数据失败: {e}")
            return self._generate_sample_data(stock_code)
    
    def _generate_sample_data(self, stock_code, days=60):
        """生成模拟股票数据"""
        print(f"🎲 生成 {days} 天的模拟数据...")
        
        # 生成日期序列
        dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
        
        # 生成价格数据 (随机游走)
        np.random.seed(42)  # 固定随机种子以便复现
        
        initial_price = 10.0
        returns = np.random.normal(0.001, 0.02, days)  # 日收益率
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
                order_result = self.trader.buy(stock_code, price, quantity)
                if order_result and order_result.get('success', False):
                    success = True
                else:
                    return False
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
                order_result = self.trader.sell(stock_code, price, quantity)
                if order_result and order_result.get('success', False):
                    success = True
                else:
                    return False
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


class MockTrader:
    """模拟交易器"""
    
    def __init__(self):
        self.orders = []
        print("📝 模拟交易器初始化完成")
    
    def buy(self, stock_code, price, quantity):
        """模拟买入"""
        order = {
            'stock_code': stock_code,
            'action': 'BUY',
            'price': price,
            'quantity': quantity,
            'timestamp': datetime.now()
        }
        self.orders.append(order)
        return True
    
    def sell(self, stock_code, price, quantity):
        """模拟卖出"""
        order = {
            'stock_code': stock_code,
            'action': 'SELL',
            'price': price,
            'quantity': quantity,
            'timestamp': datetime.now()
        }
        self.orders.append(order)
        return True


def main():
    """主函数 - 完整的交易策略演示"""
    print("=" * 60)
    print("🚀 股票量化交易学习案例 - 数据获取与交易结合")
    print("=" * 60)
    
    # 初始化交易策略
    strategy = TradingStrategy(use_real_trading=False)  # 使用模拟交易
    
    # 测试股票
    stock_code = '000001'
    
    print("\n" + "=" * 40)
    print("📊 第一步：加载股票数据")
    print("=" * 40)
    
    # 加载数据
    data = strategy.load_sample_data(stock_code)
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
    print("📝 这是一个完整的从数据获取到交易执行的学习案例")
    print("🔄 您可以修改策略参数来测试不同的交易策略")
    print("=" * 60)


if __name__ == "__main__":
    main()