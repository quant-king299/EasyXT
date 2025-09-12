# -*- coding: utf-8 -*-
"""
扩展API学习实例
本文件展示了xtquant的高级API使用方法和扩展功能
"""

import xtquant.xtdata as xt
import xtquant.xttrader as trader
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import threading
import time
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("扩展API学习实例 - 高级功能演示")
print("=" * 60)

# ================================
# 1. 高级数据获取API
# ================================

class AdvancedDataAPI:
    """高级数据获取接口"""
    
    def __init__(self):
        self.cache = {}
        
    def get_multi_period_data(self, stock_codes, periods=['1d', '1h', '30m']):
        """获取多周期数据"""
        result = {}
        
        for period in periods:
            print(f"正在获取{period}周期数据...")
            try:
                # 使用count参数而不是时间范围，更稳定
                data = xt.get_market_data_ex(
                    stock_list=stock_codes,
                    period=period,
                    count=100  # 获取最近100条数据
                )
                
                if data:
                    result[period] = data
                    print(f"✅ {period}周期数据获取成功")
                    
                    # 显示数据概览
                    for stock_code in stock_codes:
                        if stock_code in data and len(data[stock_code]) > 0:
                            df = data[stock_code]
                            print(f"   {stock_code}: {len(df)}条数据, 最新价格: {df['close'].iloc[-1]:.2f}")
                else:
                    print(f"❌ {period}周期数据为空")
                    result[period] = {}
                    
            except Exception as e:
                print(f"❌ 获取{period}周期数据失败: {e}")
                result[period] = {}
                
            # 添加短暂延迟避免API调用过于频繁
            time.sleep(0.5)
            
        return result
    
    def get_sector_data(self, sector_code):
        """获取板块数据"""
        print(f"正在获取板块数据: {sector_code}")
        
        try:
            # 获取板块成分股
            stocks = xt.get_sector_stocks(sector_code)
            print(f"板块成分股数量: {len(stocks)}")
            
            # 获取板块整体数据
            sector_data = {}
            for i, stock in enumerate(stocks[:10]):  # 限制前10只股票
                try:
                    print(f"  获取{stock}数据... ({i+1}/10)")
                    data = xt.get_market_data_ex(
                        stock_list=[stock],
                        period='1d',
                        count=30
                    )
                    if stock in data:
                        sector_data[stock] = data[stock]
                        print(f"  ✅ {stock}数据获取成功")
                except Exception as e:
                    print(f"  ❌ 获取{stock}数据失败: {e}")
                    
                time.sleep(0.2)
                
        except Exception as e:
            print(f"❌ 获取板块数据失败: {e}")
            sector_data = {}
                
        return sector_data
    
    def get_financial_data_batch(self, stock_codes, report_type='year'):
        """批量获取财务数据"""
        print(f"正在批量获取财务数据...")
        financial_data = {}
        
        for stock_code in stock_codes:
            try:
                print(f"  获取{stock_code}财务数据...")
                # 获取财务数据
                data = xt.get_financial_data(
                    stock_list=[stock_code],
                    table_list=['Balance', 'Income', 'CashFlow'],
                    start_time='20200101',
                    report_type=report_type
                )
                financial_data[stock_code] = data
                print(f"  ✅ {stock_code}财务数据获取成功")
                
            except Exception as e:
                print(f"  ❌ 获取{stock_code}财务数据失败: {e}")
                
            time.sleep(0.3)
                
        return financial_data
    
    def get_level2_data(self, stock_codes):
        """获取Level2数据（需要相应权限）"""
        print(f"正在获取Level2数据...")
        level2_data = {}
        
        for stock_code in stock_codes:
            try:
                print(f"  获取{stock_code}的Level2数据...")
                
                # 获取五档行情
                tick_data = xt.get_full_tick([stock_code])
                
                if tick_data and stock_code in tick_data:
                    tick = tick_data[stock_code]
                    
                    level2_info = {
                        'bid_prices': [tick.get(f'bidPrice{i}', 0) for i in range(1, 6)],
                        'bid_volumes': [tick.get(f'bidVolume{i}', 0) for i in range(1, 6)],
                        'ask_prices': [tick.get(f'askPrice{i}', 0) for i in range(1, 6)],
                        'ask_volumes': [tick.get(f'askVolume{i}', 0) for i in range(1, 6)],
                        'last_price': tick.get('lastPrice', 0),
                        'volume': tick.get('volume', 0),
                        'amount': tick.get('amount', 0)
                    }
                    
                    level2_data[stock_code] = level2_info
                    print(f"  ✅ {stock_code}: 最新价={level2_info['last_price']:.2f}")
                else:
                    print(f"  ❌ {stock_code}: 无Level2数据")
                    
            except Exception as e:
                print(f"  ❌ 获取{stock_code} Level2数据失败: {e}")
                
            time.sleep(0.2)  # 避免请求过于频繁
                
        return level2_data

# ================================
# 2. 高级交易API
# ================================

class AdvancedTradeAPI:
    """高级交易接口"""
    
    def __init__(self, account_id):
        self.account_id = account_id
        self.order_manager = OrderManager()
        
    def smart_order(self, stock_code, direction, volume, strategy='twap'):
        """智能下单"""
        print(f"执行智能下单: {stock_code}, 方向: {direction}, 数量: {volume}, 策略: {strategy}")
        
        if strategy == 'twap':
            return self.twap_order(stock_code, direction, volume)
        elif strategy == 'vwap':
            return self.vwap_order(stock_code, direction, volume)
        elif strategy == 'iceberg':
            return self.iceberg_order(stock_code, direction, volume)
        else:
            return self.market_order(stock_code, direction, volume)
    
    def twap_order(self, stock_code, direction, total_volume, time_window=300):
        """时间加权平均价格算法下单"""
        print(f"执行TWAP算法下单: {stock_code}, 方向: {direction}, 总量: {total_volume}")
        
        # 将订单分割成多个小单
        num_orders = 10
        order_volume = total_volume // num_orders
        interval = time_window // num_orders
        
        order_ids = []
        
        def place_order():
            for i in range(num_orders):
                try:
                    print(f"提交TWAP子订单{i+1}: {order_volume}股")
                    # 这里是模拟下单，实际使用时需要取消注释
                    # if direction == 'buy':
                    #     order_id = trader.order_stock(
                    #         self.account_id, stock_code,
                    #         trader.ORDER_TYPE.MARKET,
                    #         trader.ORDER_DIRECTION.BUY,
                    #         order_volume
                    #     )
                    # else:
                    #     order_id = trader.order_stock(
                    #         self.account_id, stock_code,
                    #         trader.ORDER_TYPE.MARKET,
                    #         trader.ORDER_DIRECTION.SELL,
                    #         order_volume
                    #     )
                    
                    order_id = f"TWAP_{i+1}_{int(time.time())}"  # 模拟订单ID
                    order_ids.append(order_id)
                    print(f"✅ TWAP子订单{i+1}已提交: {order_id}")
                    
                    if i < num_orders - 1:  # 最后一个订单不需要等待
                        time.sleep(interval)
                        
                except Exception as e:
                    print(f"❌ TWAP子订单{i+1}提交失败: {e}")
        
        # 在新线程中执行
        thread = threading.Thread(target=place_order)
        thread.start()
        
        return order_ids
    
    def market_order(self, stock_code, direction, volume):
        """市价单"""
        print(f"提交市价单: {stock_code} {direction} {volume}股")
        
        try:
            # 模拟下单
            order_id = f"MARKET_{direction}_{int(time.time())}"
            print(f"✅ 市价单已提交: {order_id}")
            return order_id
        except Exception as e:
            print(f"❌ 市价单提交失败: {e}")
            return None

# ================================
# 3. 订单管理器
# ================================

class OrderManager:
    """订单管理器"""
    
    def __init__(self):
        self.orders = {}
        self.order_history = []
        
    def add_order(self, order_id, order_info):
        """添加订单"""
        self.orders[order_id] = order_info
        print(f"订单已添加: {order_id}")
        
    def update_order_status(self, order_id, status):
        """更新订单状态"""
        if order_id in self.orders:
            self.orders[order_id]['status'] = status
            self.orders[order_id]['update_time'] = datetime.now()
            print(f"订单状态已更新: {order_id} -> {status}")
            
    def get_active_orders(self):
        """获取活跃订单"""
        active_orders = {}
        for order_id, order_info in self.orders.items():
            if order_info.get('status') not in ['已成', '已撤', '废单']:
                active_orders[order_id] = order_info
        return active_orders
    
    def cancel_all_orders(self, account_id):
        """撤销所有订单"""
        active_orders = self.get_active_orders()
        
        for order_id in active_orders:
            try:
                # trader.cancel_order_stock(account_id, order_id)
                print(f"✅ 撤销订单: {order_id}")
            except Exception as e:
                print(f"❌ 撤销订单{order_id}失败: {e}")

# ================================
# 4. 数据存储和管理
# ================================

class DataManager:
    """数据管理器"""
    
    def __init__(self, db_path='market_data.db'):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """初始化数据库"""
        print(f"初始化数据库: {self.db_path}")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建行情数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT,
                trade_date TEXT,
                open_price REAL,
                high_price REAL,
                low_price REAL,
                close_price REAL,
                volume INTEGER,
                amount REAL,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建交易记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT,
                stock_code TEXT,
                direction TEXT,
                volume INTEGER,
                price REAL,
                trade_time TIMESTAMP,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ 数据库初始化完成")
        
    def save_market_data(self, stock_code, data):
        """保存行情数据"""
        print(f"保存{stock_code}行情数据到数据库...")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved_count = 0
        for index, row in data.iterrows():
            try:
                # 处理不同类型的索引
                if hasattr(index, 'strftime'):
                    # 如果索引是datetime类型
                    trade_date = index.strftime('%Y-%m-%d')
                elif isinstance(index, str):
                    # 如果索引是字符串类型
                    trade_date = index
                else:
                    # 如果索引是其他类型（如整数），使用当前日期
                    trade_date = datetime.now().strftime('%Y-%m-%d')
                
                cursor.execute('''
                    INSERT OR REPLACE INTO market_data 
                    (stock_code, trade_date, open_price, high_price, low_price, close_price, volume, amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    stock_code,
                    trade_date,
                    float(row['open']) if pd.notna(row['open']) else 0.0,
                    float(row['high']) if pd.notna(row['high']) else 0.0,
                    float(row['low']) if pd.notna(row['low']) else 0.0,
                    float(row['close']) if pd.notna(row['close']) else 0.0,
                    int(row['volume']) if pd.notna(row['volume']) else 0,
                    float(row.get('amount', 0)) if pd.notna(row.get('amount', 0)) else 0.0
                ))
                saved_count += 1
            except Exception as e:
                print(f"❌ 保存第{saved_count+1}条数据失败: {e}")
                # 打印调试信息
                print(f"   索引类型: {type(index)}, 索引值: {index}")
                print(f"   数据: open={row.get('open')}, high={row.get('high')}, low={row.get('low')}, close={row.get('close')}")
        
        conn.commit()
        conn.close()
        print(f"✅ 成功保存{saved_count}条{stock_code}数据")
        
    def save_trade_record(self, order_id, stock_code, direction, volume, price, trade_time):
        """保存交易记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trade_records 
            (order_id, stock_code, direction, volume, price, trade_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (order_id, stock_code, direction, volume, price, trade_time))
        
        conn.commit()
        conn.close()
        print(f"✅ 交易记录已保存: {stock_code} {direction} {volume}@{price}")
        
    def get_historical_data(self, stock_code, start_date, end_date):
        """获取历史数据"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT * FROM market_data 
            WHERE stock_code = ? AND trade_date BETWEEN ? AND ?
            ORDER BY trade_date
        '''
        
        df = pd.read_sql_query(query, conn, params=(stock_code, start_date, end_date))
        conn.close()
        
        return df

# ================================
# 5. 实时数据流处理
# ================================

class RealTimeDataStream:
    """实时数据流处理"""
    
    def __init__(self, stock_codes):
        self.stock_codes = stock_codes
        self.subscribers = []
        self.is_running = False
        self.data_buffer = {}
        
    def subscribe(self, callback):
        """订阅数据流"""
        self.subscribers.append(callback)
        print(f"✅ 新订阅者已添加，当前订阅者数量: {len(self.subscribers)}")
        
    def start_stream(self):
        """启动数据流"""
        print(f"启动实时数据流，监控股票: {self.stock_codes}")
        self.is_running = True
        
        def stream_worker():
            while self.is_running:
                try:
                    # 获取实时数据
                    tick_data = xt.get_full_tick(self.stock_codes)
                    
                    for stock_code, data in tick_data.items():
                        # 数据预处理
                        processed_data = self.process_tick_data(stock_code, data)
                        
                        # 通知所有订阅者
                        for callback in self.subscribers:
                            try:
                                callback(stock_code, processed_data)
                            except Exception as e:
                                print(f"❌ 回调函数执行失败: {e}")
                    
                    time.sleep(1)  # 1秒更新一次
                    
                except Exception as e:
                    print(f"❌ 数据流处理错误: {e}")
                    time.sleep(5)
        
        # 在新线程中启动数据流
        stream_thread = threading.Thread(target=stream_worker)
        stream_thread.daemon = True
        stream_thread.start()
        
    def stop_stream(self):
        """停止数据流"""
        self.is_running = False
        print("🛑 实时数据流已停止")
        
    def process_tick_data(self, stock_code, tick_data):
        """处理tick数据"""
        processed = {
            'stock_code': stock_code,
            'timestamp': datetime.now(),
            'last_price': tick_data.get('lastPrice', 0),
            'volume': tick_data.get('volume', 0),
            'amount': tick_data.get('amount', 0),
            'pct_change': tick_data.get('pctChg', 0),
            'bid_ask_spread': tick_data.get('askPrice1', 0) - tick_data.get('bidPrice1', 0)
        }
        
        # 计算技术指标
        if stock_code not in self.data_buffer:
            self.data_buffer[stock_code] = []
        
        self.data_buffer[stock_code].append(processed['last_price'])
        
        # 保持最近100个价格点
        if len(self.data_buffer[stock_code]) > 100:
            self.data_buffer[stock_code] = self.data_buffer[stock_code][-100:]
        
        # 计算移动平均
        if len(self.data_buffer[stock_code]) >= 5:
            processed['ma5'] = np.mean(self.data_buffer[stock_code][-5:])
        if len(self.data_buffer[stock_code]) >= 20:
            processed['ma20'] = np.mean(self.data_buffer[stock_code][-20:])
            
        return processed

# ================================
# 6. 性能跟踪器
# ================================

class PerformanceTracker:
    """性能跟踪器"""
    
    def __init__(self):
        self.trades = []
        self.daily_pnl = {}
        self.positions = {}
        
    def record_trade(self, trade_data):
        """记录交易"""
        self.trades.append({
            'timestamp': datetime.now(),
            'stock_code': trade_data.get('stock_code'),
            'direction': trade_data.get('direction'),
            'volume': trade_data.get('volume'),
            'price': trade_data.get('price'),
            'amount': trade_data.get('volume', 0) * trade_data.get('price', 0)
        })
        
    def calculate_performance(self):
        """计算策略表现"""
        if not self.trades:
            return {}
        
        df = pd.DataFrame(self.trades)
        
        # 计算总收益
        buy_amount = df[df['direction'] == 'buy']['amount'].sum()
        sell_amount = df[df['direction'] == 'sell']['amount'].sum()
        total_pnl = sell_amount - buy_amount
        
        # 计算交易次数
        total_trades = len(df) // 2  # 假设每次完整交易包含买入和卖出
        
        # 计算胜率（简化版）
        profitable_trades = 0
        if total_trades > 0:
            profitable_trades = total_trades // 2  # 简化计算
        
        # 计算最大回撤（简化版）
        max_drawdown = 0
        if len(df) > 0:
            cumulative_pnl = df['amount'].cumsum()
            max_drawdown = (cumulative_pnl.cummax() - cumulative_pnl).max()
        
        # 计算夏普比率（简化版）
        sharpe_ratio = 0
        if len(df) > 1:
            daily_returns = df.groupby(df['timestamp'].dt.date)['amount'].sum()
            if daily_returns.std() > 0:
                sharpe_ratio = daily_returns.mean() / daily_returns.std()
        
        return {
            'total_pnl': total_pnl,
            'total_trades': total_trades,
            'win_rate': profitable_trades / total_trades if total_trades > 0 else 0,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio
        }

# ================================
# 7. 使用示例
# ================================

def advanced_api_example():
    """高级API使用示例"""
    
    print("\n高级API使用示例")
    print("=" * 60)
    
    try:
        # 1. 高级数据获取
        print("\n📊 第一部分：高级数据获取")
        print("-" * 40)
        
        data_api = AdvancedDataAPI()
        stock_codes = ['000001.SZ', '600000.SH']
        
        # 获取多周期数据
        print("1.1 获取多周期数据")
        multi_data = data_api.get_multi_period_data(stock_codes, ['1d', '1h'])
        
        # 获取Level2数据
        print("\n1.2 获取Level2数据")
        level2_data = data_api.get_level2_data(stock_codes)
        
        # 2. 数据管理演示
        print("\n💾 第二部分：数据管理")
        print("-" * 40)
        
        data_manager = DataManager()
        print("✅ 数据管理器初始化完成")
        
        # 保存获取到的数据
        if multi_data.get('1d'):
            for stock_code, df in multi_data['1d'].items():
                if len(df) > 0:
                    # 检查数据格式
                    print(f"检查{stock_code}数据格式:")
                    print(f"  数据形状: {df.shape}")
                    print(f"  索引类型: {type(df.index)}")
                    print(f"  列名: {list(df.columns)}")
                    print(f"  前3行索引: {df.index[:3].tolist()}")
                    
                    data_manager.save_market_data(stock_code, df)
                    print(f"✅ {stock_code}数据已保存到数据库")
        
        # 3. 交易API演示
        print("\n💼 第三部分：高级交易API")
        print("-" * 40)
        
        account_id = "demo_account"  # 演示账户
        trade_api = AdvancedTradeAPI(account_id)
        
        # 演示智能下单
        print("演示TWAP算法下单...")
        order_ids = trade_api.smart_order('000001.SZ', 'buy', 10000, 'twap')
        print(f"TWAP订单ID列表: {order_ids}")
        
        # 4. 性能跟踪演示
        print("\n📈 第四部分：性能跟踪")
        print("-" * 40)
        
        performance_tracker = PerformanceTracker()
        
        # 模拟一些交易记录
        sample_trades = [
            {'stock_code': '000001.SZ', 'direction': 'buy', 'volume': 1000, 'price': 10.50},
            {'stock_code': '000001.SZ', 'direction': 'sell', 'volume': 1000, 'price': 10.80},
            {'stock_code': '600000.SH', 'direction': 'buy', 'volume': 500, 'price': 8.20},
            {'stock_code': '600000.SH', 'direction': 'sell', 'volume': 500, 'price': 8.10}
        ]
        
        for trade in sample_trades:
            performance_tracker.record_trade(trade)
        
        performance = performance_tracker.calculate_performance()
        print("✅ 策略表现分析:")
        print(f"   总收益: {performance.get('total_pnl', 0):.2f}")
        print(f"   交易次数: {performance.get('total_trades', 0)}")
        print(f"   胜率: {performance.get('win_rate', 0):.2%}")
        
        print("\n✅ 高级API示例完成！")
        
    except Exception as e:
        print(f"\n❌ 示例运行出错: {e}")
        import traceback
        traceback.print_exc()

def demo_realtime_monitoring():
    """演示实时监控"""
    print("\n🌊 实时数据监控演示")
    print("监控股票: 000001.SZ, 600000.SH")
    print("运行5秒后自动停止...")
    
    stock_codes = ['000001.SZ', '600000.SH']
    data_stream = RealTimeDataStream(stock_codes)
    
    def on_data(stock_code, data):
        print(f"📊 {stock_code}: {data['last_price']:.2f} ({data['pct_change']:+.2f}%)")
    
    data_stream.subscribe(on_data)
    data_stream.start_stream()
    
    try:
        time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        data_stream.stop_stream()
        print("✅ 实时监控已停止")

def demo_database_management():
    """演示数据库管理"""
    print("\n💾 数据库管理演示")
    
    data_manager = DataManager()
    
    # 显示数据库信息
    import sqlite3
    conn = sqlite3.connect(data_manager.db_path)
    cursor = conn.cursor()
    
    # 查询市场数据表
    cursor.execute("SELECT COUNT(*) FROM market_data")
    market_data_count = cursor.fetchone()[0]
    
    # 查询交易记录表
    cursor.execute("SELECT COUNT(*) FROM trade_records")
    trade_records_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"📊 数据库状态:")
    print(f"   市场数据记录: {market_data_count}条")
    print(f"   交易记录: {trade_records_count}条")
    print(f"   数据库文件: {data_manager.db_path}")

def main():
    """主函数"""
    print("🎯 xtquant扩展API学习实例")
    print("=" * 60)
    print("本程序演示xtquant的高级API功能和使用方法")
    print("=" * 60)
    
    try:
        # 检查xtquant模块
        print("🔍 检查xtquant模块...")
        print(f"✅ xtdata模块: {xt.__name__}")
        print(f"✅ xttrader模块: {trader.__name__}")
        
        # 运行高级API示例
        advanced_api_example()
        
        # 询问用户是否要运行其他功能
        print("\n" + "=" * 60)
        print("🎮 其他可用功能:")
        print("1. 启动实时数据流监控")
        print("2. 数据库管理工具")
        print("=" * 60)
        
        choice = input("请选择要运行的功能 (1-2, 或按Enter跳过): ").strip()
        
        if choice == "1":
            print("启动实时数据流监控...")
            demo_realtime_monitoring()
            
        elif choice == "2":
            print("数据库管理工具...")
            demo_database_management()
            
        else:
            print("跳过额外功能")
        
        print("\n🎉 扩展API学习实例运行完成！")
        print("感谢使用xtquant扩展API学习实例")
        
    except KeyboardInterrupt:
        print("\n\n🛑 用户中断程序")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()