"""
股票量化交易学习案例 - 修复交易服务版
基于真实交易版，修复交易服务初始化问题

功能包括：
1. qstock真实数据获取 (多种方式尝试)
2. 完整的技术指标计算
3. 智能交易信号生成
4. EasyXT真实交易下单 (修复初始化问题)
5. 交易前二次确认
6. 完整的资金管理
7. 交易日志记录

作者：王者quant
日期：2025-01-11
修复版：解决交易服务未初始化问题
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys
from datetime import datetime, timedelta
import warnings
import time
import requests
warnings.filterwarnings('ignore')

# 强制要求真实数据和真实交易
REQUIRE_REAL_DATA = True
REQUIRE_REAL_TRADING = True

# 尝试导入qstock - 增加错误处理
try:
    import qstock as qs
    QSTOCK_AVAILABLE = True
    print("✅ qstock库导入成功")
except ImportError as e:
    if REQUIRE_REAL_DATA:
        print(f"❌ qstock库导入失败: {e}")
        print("💡 建议安装: pip install qstock")
        print("🚫 要求使用真实数据，程序无法继续")
        sys.exit(1)
    else:
        QSTOCK_AVAILABLE = False
        print(f"❌ qstock库导入失败: {e}")

# 添加easy_xt路径并导入 - 必须成功
current_dir = os.path.dirname(os.path.abspath(__file__))
easy_xt_path = os.path.join(current_dir, '..', 'easy_xt')
if os.path.exists(easy_xt_path):
    sys.path.append(easy_xt_path)

try:
    from easy_xt import EasyXT
    EASY_XT_AVAILABLE = True
    print("✅ easy_xt模块加载成功")
except ImportError as e:
    try:
        # 尝试直接导入
        sys.path.append(os.path.join(current_dir, '..'))
        from easy_xt.api import EasyXT
        EASY_XT_AVAILABLE = True
        print("✅ easy_xt模块加载成功")
    except ImportError as e2:
        if REQUIRE_REAL_TRADING:
            print(f"❌ easy_xt模块导入失败: {e}")
            print("🚫 要求使用真实交易，程序无法继续")
            sys.exit(1)
        else:
            EASY_XT_AVAILABLE = False
            print(f"⚠️ easy_xt模块未找到: {e}")

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 配置信息 - 请根据实际情况修改
USERDATA_PATH = r'D:\国金QMT交易端模拟\userdata_mini'  # 修改为实际的迅投客户端路径
DEFAULT_ACCOUNT_ID = "39020958"  # 修改为实际账号

class FixedRealTradingQStockStrategy:
    """基于真实qstock数据和easy_xt交易的策略类 (修复交易服务版)"""
    
    def __init__(self):
        """初始化真实交易策略"""
        self.data_dir = "data"
        self.log_dir = "logs"
        
        # 创建必要目录
        for dir_path in [self.data_dir, self.log_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        
        # 初始化真实交易接口 - 修复版
        self.trader = None
        self.trade_initialized = False
        self.account_id = DEFAULT_ACCOUNT_ID
        
        if EASY_XT_AVAILABLE:
            self._init_trading_service()
        
        # 交易参数
        self.position = {}
        self.cash = 100000
        self.trade_log = []
        
        print("🚀 修复版真实交易QStock策略初始化完成")
    
    def _init_trading_service(self):
        """初始化交易服务 - 修复版"""
        try:
            print("🔧 正在初始化EasyXT交易服务...")
            
            # 1. 创建EasyXT实例
            self.trader = EasyXT()
            print("✅ EasyXT实例创建成功")
            
            # 2. 初始化数据服务
            print("📊 初始化数据服务...")
            data_success = self.trader.init_data()
            if data_success:
                print("✅ 数据服务初始化成功")
            else:
                print("⚠️ 数据服务初始化失败，但继续尝试交易服务")
            
            # 3. 初始化交易服务
            print(f"💼 初始化交易服务，路径: {USERDATA_PATH}")
            trade_success = self.trader.init_trade(USERDATA_PATH, 'qstock_strategy_session')
            
            if trade_success:
                print("✅ 交易服务初始化成功")
                
                # 4. 添加交易账户
                print(f"👤 添加交易账户: {self.account_id}")
                account_success = self.trader.add_account(self.account_id, 'STOCK')
                
                if account_success:
                    print("✅ 交易账户添加成功")
                    self.trade_initialized = True
                    print("🎉 EasyXT真实交易接口完全初始化成功")
                else:
                    print("⚠️ 交易账户添加失败，但交易服务已初始化")
                    self.trade_initialized = True
            else:
                print("❌ 交易服务初始化失败")
                print("💡 请检查:")
                print(f"   1. 迅投客户端是否已启动并登录")
                print(f"   2. userdata路径是否正确: {USERDATA_PATH}")
                print(f"   3. 账户ID是否正确: {self.account_id}")
                
                if REQUIRE_REAL_TRADING:
                    print("🚫 要求使用真实交易，程序无法继续")
                    sys.exit(1)
                
        except Exception as e:
            print(f"❌ EasyXT初始化异常: {e}")
            print("💡 可能的解决方案:")
            print("   1. 确保迅投客户端已启动")
            print("   2. 检查userdata路径")
            print("   3. 确认账户权限")
            
            if REQUIRE_REAL_TRADING:
                print("🚫 要求使用真实交易，程序无法继续")
                sys.exit(1)
    
    def get_real_stock_data_with_retry(self, stock_code, count=60, max_retries=3):
        """
        使用qstock获取真实股票数据 - 增加重试机制和多种获取方式
        
        Args:
            stock_code (str): 股票代码
            count (int): 获取数据条数
            max_retries (int): 最大重试次数
            
        Returns:
            pd.DataFrame: 真实股票数据
        """
        print(f"📊 使用qstock获取股票 {stock_code} 真实数据...")
        
        for attempt in range(max_retries):
            try:
                print(f"  尝试第 {attempt + 1}/{max_retries} 次...")
                
                # 方法1: 使用get_data (默认方法)
                if attempt == 0:
                    print("  📈 使用 qs.get_data() 方法...")
                    data = qs.get_data(stock_code)
                
                # 方法2: 使用get_data_sina (新浪数据源)
                elif attempt == 1:
                    print("  📈 使用 qs.get_data_sina() 方法...")
                    try:
                        data = qs.get_data_sina(stock_code)
                    except AttributeError:
                        print("    ⚠️ get_data_sina 方法不存在，尝试其他方法")
                        data = qs.get_data(stock_code)
                
                # 方法3: 使用历史数据接口
                else:
                    print("  📈 使用历史数据接口...")
                    end_date = datetime.now().strftime('%Y-%m-%d')
                    start_date = (datetime.now() - timedelta(days=count*2)).strftime('%Y-%m-%d')
                    try:
                        data = qs.get_data(stock_code, start=start_date, end=end_date)
                    except:
                        data = qs.get_data(stock_code)
                
                # 验证数据
                if data is not None and not data.empty and len(data) >= 10:
                    print(f"  ✅ 成功获取 {len(data)} 条数据")
                    return self._validate_and_clean_data(data)
                else:
                    print(f"  ⚠️ 数据不足，获取到 {len(data) if data is not None else 0} 条")
                    
            except Exception as e:
                print(f"  ❌ 第 {attempt + 1} 次尝试失败: {e}")
                if attempt < max_retries - 1:
                    print(f"  等待 {(attempt + 1) * 2} 秒后重试...")
                    time.sleep((attempt + 1) * 2)
        
        print("❌ 所有尝试均失败，无法获取真实数据")
        return None
    
    def _validate_and_clean_data(self, data):
        """验证和清洗数据"""
        if data is None or data.empty:
            return None
        
        print(f"📋 数据验证:")
        print(f"  原始数据形状: {data.shape}")
        print(f"  列名: {list(data.columns)}")
        
        # 标准化列名
        column_mapping = {
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }
        
        for old_name, new_name in column_mapping.items():
            if old_name in data.columns:
                data = data.rename(columns={old_name: new_name})
        
        # 确保必要列存在
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            print(f"❌ 缺少必要列: {missing_columns}")
            return None
        
        # 清理数据
        original_len = len(data)
        data = data.dropna()
        data = data[data['volume'] > 0]
        
        # 确保数据类型
        for col in required_columns:
            data[col] = pd.to_numeric(data[col], errors='coerce')
        
        data = data.dropna()
        
        if len(data) < 10:
            print(f"❌ 清洗后数据不足: {len(data)} 条")
            return None
        
        print(f"✅ 数据验证通过: {original_len} -> {len(data)} 条")
        print(f"  价格范围: {data['close'].min():.2f} - {data['close'].max():.2f}")
        print(f"  最新价格: {data['close'].iloc[-1]:.2f}")
        
        return data
    
    def calculate_technical_indicators(self, data):
        """计算技术指标"""
        print("📈 计算技术指标...")
        
        # 移动平均线
        data['MA5'] = data['close'].rolling(window=5).mean()
        data['MA10'] = data['close'].rolling(window=10).mean()
        data['MA20'] = data['close'].rolling(window=20).mean()
        
        # RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['RSI14'] = 100 - (100 / (1 + rs))
        
        # MACD
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
        
        # KDJ指标
        low_min = data['low'].rolling(window=9).min()
        high_max = data['high'].rolling(window=9).max()
        rsv = (data['close'] - low_min) / (high_max - low_min) * 100
        data['K'] = rsv.ewm(com=2).mean()
        data['D'] = data['K'].ewm(com=2).mean()
        data['J'] = 3 * data['K'] - 2 * data['D']
        
        print("✅ 技术指标计算完成")
        return data
    
    def generate_trading_signals(self, data):
        """生成交易信号"""
        print("🎯 生成交易信号...")
        
        data['signal'] = 0
        data['confidence'] = 0
        data['signal_reason'] = ''
        
        for i in range(1, len(data)):
            signals = []
            reasons = []
            
            # 信号1: MA金叉死叉
            if data['MA5'].iloc[i] > data['MA10'].iloc[i] and data['MA5'].iloc[i-1] <= data['MA10'].iloc[i-1]:
                signals.append(1)
                reasons.append("MA金叉")
            elif data['MA5'].iloc[i] < data['MA10'].iloc[i] and data['MA5'].iloc[i-1] >= data['MA10'].iloc[i-1]:
                signals.append(-1)
                reasons.append("MA死叉")
            
            # 信号2: RSI超买超卖
            if data['RSI14'].iloc[i] < 30:
                signals.append(1)
                reasons.append("RSI超卖")
            elif data['RSI14'].iloc[i] > 70:
                signals.append(-1)
                reasons.append("RSI超买")
            
            # 信号3: MACD金叉死叉
            if (data['MACD'].iloc[i] > data['MACD_signal'].iloc[i] and 
                data['MACD'].iloc[i-1] <= data['MACD_signal'].iloc[i-1]):
                signals.append(1)
                reasons.append("MACD金叉")
            elif (data['MACD'].iloc[i] < data['MACD_signal'].iloc[i] and 
                  data['MACD'].iloc[i-1] >= data['MACD_signal'].iloc[i-1]):
                signals.append(-1)
                reasons.append("MACD死叉")
            
            # 信号4: 布林带突破
            if data['close'].iloc[i] < data['BB_lower'].iloc[i]:
                signals.append(1)
                reasons.append("跌破布林下轨")
            elif data['close'].iloc[i] > data['BB_upper'].iloc[i]:
                signals.append(-1)
                reasons.append("突破布林上轨")
            
            # 信号5: KDJ指标
            if data['K'].iloc[i] < 20 and data['D'].iloc[i] < 20:
                signals.append(1)
                reasons.append("KDJ超卖")
            elif data['K'].iloc[i] > 80 and data['D'].iloc[i] > 80:
                signals.append(-1)
                reasons.append("KDJ超买")
            
            # 综合信号
            if signals:
                buy_signals = signals.count(1)
                sell_signals = signals.count(-1)
                
                if buy_signals > sell_signals:
                    data.loc[data.index[i], 'signal'] = 1
                    data.loc[data.index[i], 'confidence'] = min(95, 40 + buy_signals * 15)
                elif sell_signals > buy_signals:
                    data.loc[data.index[i], 'signal'] = -1
                    data.loc[data.index[i], 'confidence'] = min(95, 40 + sell_signals * 15)
                else:
                    data.loc[data.index[i], 'confidence'] = 50
                
                data.loc[data.index[i], 'signal_reason'] = ", ".join(reasons)
        
        signal_count = (data['signal'] != 0).sum()
        print(f"✅ 生成 {signal_count} 个交易信号")
        return data
    
    def execute_real_trades(self, data, stock_code):
        """执行真实交易 (修复版 - 支持EasyXT真实下单)"""
        print("💼 交易信号分析...")
        
        # 检查交易服务状态
        if self.trade_initialized:
            print("✅ EasyXT交易服务已就绪，支持真实下单")
        else:
            print("⚠️ 注意: EasyXT交易服务未初始化，当前为演示模式")
        
        # 筛选高质量信号
        high_confidence_signals = data[(data['signal'] != 0) & (data['confidence'] >= 70)]
        all_signals = data[data['signal'] != 0]
        
        print(f"📊 交易信号统计:")
        print(f"  总信号数: {len(all_signals)}")
        print(f"  高置信度信号(≥70%): {len(high_confidence_signals)}")
        print(f"  买入信号: {(all_signals['signal'] == 1).sum()}")
        print(f"  卖出信号: {(all_signals['signal'] == -1).sum()}")
        
        if not all_signals.empty:
            print(f"\n📋 最近5个交易信号:")
            recent_signals = all_signals.tail(5)
            for idx, row in recent_signals.iterrows():
                signal_type = "🟢买入" if row['signal'] == 1 else "🔴卖出"
                print(f"  {idx.strftime('%Y-%m-%d')}: {signal_type} | 价格: {row['close']:.2f} | 置信度: {row['confidence']:.0f}%")
                print(f"    📝 {row['signal_reason']}")
        
        # 处理高置信度信号 - 真实交易
        if len(high_confidence_signals) > 0:
            print(f"\n🔥 发现 {len(high_confidence_signals)} 个高置信度交易信号")
            
            # 获取最新信号
            latest_signal = high_confidence_signals.iloc[-1]
            signal_type = "买入" if latest_signal['signal'] == 1 else "卖出"
            
            print(f"\n📈 最新高置信度信号:")
            print(f"  股票代码: {stock_code}")
            print(f"  信号类型: {signal_type}")
            print(f"  当前价格: {latest_signal['close']:.2f}")
            print(f"  置信度: {latest_signal['confidence']:.0f}%")
            print(f"  信号原因: {latest_signal['signal_reason']}")
            print(f"  信号日期: {latest_signal.name.strftime('%Y-%m-%d')}")
            
            if self.trade_initialized:
                # 二次确认
                if self._confirm_trade(stock_code, signal_type, latest_signal['close'], latest_signal['confidence']):
                    self._execute_trade_order(stock_code, latest_signal['signal'], latest_signal['close'])
                else:
                    print("❌ 用户取消交易")
            else:
                print("💡 建议手动执行此交易信号")
        else:
            print(f"\n💡 当前无高置信度信号，建议继续观察")
            if len(all_signals) > 0:
                print("📊 可关注中等置信度信号进行参考")
    
    def _confirm_trade(self, stock_code, signal_type, price, confidence):
        """交易前二次确认"""
        print(f"\n" + "="*60)
        print(f"🚨 交易确认")
        print(f"="*60)
        print(f"股票代码: {stock_code}")
        print(f"操作类型: {signal_type}")
        print(f"参考价格: {price:.2f} 元")
        print(f"信号置信度: {confidence:.0f}%")
        print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"="*60)
        print("💡 这是真实交易，将通过EasyXT接口执行")
        print("⚠️  请确认您已经做好风险控制准备")
        print(f"="*60)
        
        while True:
            confirm = input("是否确认执行此交易? (y/n): ").lower().strip()
            if confirm in ['y', 'yes', '是', '确认']:
                return True
            elif confirm in ['n', 'no', '否', '取消']:
                return False
            else:
                print("请输入 y/n 或 是/否")
    
    def _execute_trade_order(self, stock_code, signal, price):
        """执行具体的交易下单 - 修复版"""
        try:
            # 获取账户信息和持仓
            account_info = self._get_account_info()
            position_info = self._get_position_info(stock_code)
            
            # 计算交易数量
            quantity = self._calculate_trade_quantity(signal, price, account_info, position_info)
            
            if quantity <= 0:
                print(f"❌ 交易数量计算错误或资金不足，取消交易")
                return
            
            if signal == 1:  # 买入
                print(f"📈 执行买入订单:")
                print(f"   股票代码: {stock_code}")
                print(f"   买入数量: {quantity} 股")
                print(f"   买入价格: {price:.2f} 元")
                print(f"   预计金额: {quantity * price:.2f} 元")
                
                # 调用EasyXT的买入接口 - 修复版
                try:
                    if self.trade_initialized and self.trader:
                        # 使用修复后的API调用
                        result = self.trader.buy(
                            account_id=self.account_id,
                            code=stock_code,
                            volume=quantity,
                            price=price,
                            price_type='limit'  # 使用限价单
                        )
                        
                        if result:
                            print(f"✅ 买入订单提交成功")
                            print(f"   订单编号: {result}")
                            status = '提交成功'
                        else:
                            print(f"⚠️ 买入订单提交，等待确认")
                            status = '已提交'
                    else:
                        print(f"⚠️ 交易服务未初始化，模拟执行买入")
                        status = '模拟执行'
                        
                except Exception as e:
                    print(f"❌ 买入订单执行失败: {e}")
                    status = f'执行失败: {str(e)}'
                
            elif signal == -1:  # 卖出
                print(f"📉 执行卖出订单:")
                print(f"   股票代码: {stock_code}")
                print(f"   卖出数量: {quantity} 股")
                print(f"   卖出价格: {price:.2f} 元")
                print(f"   预计金额: {quantity * price:.2f} 元")
                
                # 调用EasyXT的卖出接口 - 修复版
                try:
                    if self.trade_initialized and self.trader:
                        # 使用修复后的API调用
                        result = self.trader.sell(
                            account_id=self.account_id,
                            code=stock_code,
                            volume=quantity,
                            price=price,
                            price_type='limit'  # 使用限价单
                        )
                        
                        if result:
                            print(f"✅ 卖出订单提交成功")
                            print(f"   订单编号: {result}")
                            status = '提交成功'
                        else:
                            print(f"⚠️ 卖出订单提交，等待确认")
                            status = '已提交'
                    else:
                        print(f"⚠️ 交易服务未初始化，模拟执行卖出")
                        status = '模拟执行'
                        
                except Exception as e:
                    print(f"❌ 卖出订单执行失败: {e}")
                    status = f'执行失败: {str(e)}'
            
            # 记录交易日志
            trade_record = {
                'timestamp': datetime.now(),
                'stock_code': stock_code,
                'action': '买入' if signal == 1 else '卖出',
                'quantity': quantity,
                'price': price,
                'amount': quantity * price,
                'status': status
            }
            self.trade_log.append(trade_record)
            
        except Exception as e:
            print(f"❌ 交易执行失败: {e}")
            # 记录失败日志
            trade_record = {
                'timestamp': datetime.now(),
                'stock_code': stock_code,
                'action': '买入' if signal == 1 else '卖出',
                'quantity': 0,
                'price': price,
                'amount': 0,
                'status': f'失败: {str(e)}'
            }
            self.trade_log.append(trade_record)
    
    def _get_account_info(self):
        """获取账户信息 - 修复版"""
        try:
            if self.trade_initialized and self.trader:
                # 使用修复后的API调用
                account_info = self.trader.get_account_asset(self.account_id)
                if account_info:
                    print(f"✅ 成功获取账户信息")
                    return account_info
            
            print(f"⚠️ 无法获取账户信息，使用默认值")
            return {'cash': 100000, 'total_asset': 100000}  # 默认值
            
        except Exception as e:
            print(f"⚠️ 获取账户信息异常: {e}")
            return {'cash': 100000, 'total_asset': 100000}  # 默认值
    
    def _get_position_info(self, stock_code):
        """获取持仓信息 - 修复版"""
        try:
            if self.trade_initialized and self.trader:
                # 使用修复后的API调用
                positions = self.trader.get_positions(self.account_id, stock_code)
                if not positions.empty:
                    print(f"✅ 找到 {stock_code} 的持仓信息")
                    return positions.iloc[0].to_dict()
                else:
                    print(f"⚠️ 未找到 {stock_code} 的持仓")
                    return {'volume': 0, 'can_use_volume': 0}
            
            print(f"⚠️ 无法获取持仓信息，使用默认值")
            return {'volume': 0, 'can_use_volume': 0}
            
        except Exception as e:
            print(f"⚠️ 获取持仓信息异常: {e}")
            return {'volume': 0, 'can_use_volume': 0}
    
    def _calculate_trade_quantity(self, signal, price, account_info, position_info):
        """计算交易数量"""
        try:
            if signal == 1:  # 买入
                # 计算可用资金
                available_cash = account_info.get('cash', 100000)
                print(f"  可用资金: {available_cash:.2f} 元")
                
                # 使用30%的资金进行单次交易
                trade_amount = available_cash * 0.3
                print(f"  计划投入: {trade_amount:.2f} 元 (30%资金)")
                
                # 计算可买数量（考虑手续费约0.1%）
                quantity = int(trade_amount / (price * 1.001)) // 100 * 100  # 按手计算
                quantity = max(100, quantity)  # 最少1手
                
                print(f"  计算数量: {quantity} 股")
                return quantity
                
            elif signal == -1:  # 卖出
                # 获取可卖数量
                can_sell = position_info.get('can_use_volume', 0)
                total_volume = position_info.get('volume', 0)
                
                print(f"  总持仓: {total_volume} 股")
                print(f"  可卖数量: {can_sell} 股")
                
                if can_sell > 0:
                    # 卖出50%持仓或最少100股
                    quantity = max(100, can_sell // 2)
                    quantity = min(quantity, can_sell)  # 不能超过可卖数量
                    print(f"  计划卖出: {quantity} 股 (50%持仓)")
                    return quantity
                else:
                    print("⚠️ 无可卖持仓，使用演示数量")
                    return 100  # 演示模式下使用默认数量
                    
        except Exception as e:
            print(f"⚠️ 计算交易数量失败: {e}")
            return 100  # 默认1手
    
    def analyze_performance(self, data):
        """分析策略绩效"""
        print("\n" + "=" * 60)
        print("📊 策略绩效分析")
        print("=" * 60)
        
        signals = data[data['signal'] != 0].copy()
        
        if signals.empty:
            print("❌ 无交易信号，无法分析绩效")
            return
        
        # 信号质量分析
        print(f"📈 信号质量分析:")
        print(f"  总信号数: {len(signals)}")
        print(f"  买入信号: {(signals['signal'] == 1).sum()}")
        print(f"  卖出信号: {(signals['signal'] == -1).sum()}")
        print(f"  平均置信度: {signals['confidence'].mean():.1f}%")
        print(f"  高置信度信号(≥70%): {len(signals[signals['confidence'] >= 70])}")
        print(f"  最高置信度: {signals['confidence'].max():.1f}%")
        
        # 价格分析
        if len(signals) > 1:
            price_changes = []
            for i in range(len(signals) - 1):
                current_signal = signals.iloc[i]
                next_signal = signals.iloc[i + 1]
                
                if current_signal['signal'] == 1:  # 买入后的价格变化
                    price_change = (next_signal['close'] - current_signal['close']) / current_signal['close']
                    price_changes.append(price_change)
            
            if price_changes:
                avg_return = np.mean(price_changes) * 100
                win_rate = len([x for x in price_changes if x > 0]) / len(price_changes) * 100
                max_return = max(price_changes) * 100
                min_return = min(price_changes) * 100
                
                print(f"\n💰 收益分析:")
                print(f"  平均单次收益率: {avg_return:.2f}%")
                print(f"  胜率: {win_rate:.1f}%")
                print(f"  最大单次收益: {max_return:.2f}%")
                print(f"  最大单次亏损: {min_return:.2f}%")
        
        # 最新状态
        latest = data.iloc[-1]
        print(f"\n📊 最新技术指标:")
        print(f"  最新价格: {latest['close']:.2f}")
        print(f"  MA5: {latest['MA5']:.2f}")
        print(f"  MA10: {latest['MA10']:.2f}")
        print(f"  MA20: {latest['MA20']:.2f}")
        print(f"  RSI14: {latest['RSI14']:.1f}")
        print(f"  MACD: {latest['MACD']:.4f}")
        print(f"  K值: {latest['K']:.1f}")
        print(f"  D值: {latest['D']:.1f}")
        
        # 交易日志统计
        if self.trade_log:
            print(f"\n📝 交易记录统计:")
            print(f"  总交易次数: {len(self.trade_log)}")
            successful_trades = [t for t in self.trade_log if '成功' in t['status']]
            print(f"  成功交易: {len(successful_trades)}")
            print(f"  成功率: {len(successful_trades)/len(self.trade_log)*100:.1f}%")
    
    def save_data(self, data, stock_code):
        """保存数据到文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存分析数据
        filename = f"{self.data_dir}/{stock_code}_fixed_trading_{timestamp}.csv"
        data.to_csv(filename, encoding='utf-8-sig')
        print(f"💾 分析数据已保存到: {filename}")
        
        # 保存交易日志
        if self.trade_log:
            log_filename = f"{self.log_dir}/fixed_trade_log_{timestamp}.csv"
            pd.DataFrame(self.trade_log).to_csv(log_filename, index=False, encoding='utf-8-sig')
            print(f"📝 交易日志已保存到: {log_filename}")
        
        # 保存信号摘要
        signals = data[data['signal'] != 0]
        if not signals.empty:
            summary_filename = f"{self.data_dir}/{stock_code}_signals_{timestamp}.csv"
            signal_summary = signals[['close', 'signal', 'confidence', 'signal_reason']].copy()
            signal_summary.to_csv(summary_filename, encoding='utf-8-sig')
            print(f"📋 信号摘要已保存到: {summary_filename}")
    
    def run_strategy(self, stock_code="000001"):
        """运行完整策略"""
        print("=" * 60)
        print("🚀 启动修复版真实交易量化策略")
        print("=" * 60)
        
        # 第一步：获取真实数据
        print("\n第一步：获取真实股票数据")
        print("=" * 40)
        data = self.get_real_stock_data_with_retry(stock_code)
        
        if data is None:
            print("❌ 无法获取股票数据，策略终止")
            return
        
        # 第二步：计算技术指标
        print("\n第二步：计算技术指标")
        print("=" * 40)
        data = self.calculate_technical_indicators(data)
        
        # 第三步：生成交易信号
        print("\n第三步：生成交易信号")
        print("=" * 40)
        data = self.generate_trading_signals(data)
        
        # 第四步：执行交易
        print("\n第四步：执行交易分析")
        print("=" * 40)
        self.execute_real_trades(data, stock_code)
        
        # 第五步：绩效分析
        print("\n第五步：策略绩效分析")
        print("=" * 40)
        self.analyze_performance(data)
        
        # 第六步：保存数据
        print("\n第六步：保存数据")
        print("=" * 40)
        self.save_data(data, stock_code)
        
        return data


def main():
    """主函数 - 修复版真实交易QStock策略"""
    print("🎯 QStock真实数据交易策略 (修复交易服务版)")
    print("支持qstock数据获取 + EasyXT真实交易下单，修复了交易服务初始化问题")
    print("⚠️  注意：这是真实交易版本，会执行真实的买卖订单")
    
    print(f"\n🔧 当前配置:")
    print(f"  迅投路径: {USERDATA_PATH}")
    print(f"  账户ID: {DEFAULT_ACCOUNT_ID}")
    print(f"  数据源: qstock")
    print(f"  交易接口: EasyXT")
    
    # 创建策略实例
    strategy = FixedRealTradingQStockStrategy()
    
    # 运行策略
    stock_code = "000001"  # 平安银行
    data = strategy.run_strategy(stock_code)
    
    print("\n" + "=" * 60)
    print("✅ 修复版真实交易QStock策略演示完成！")
    print("📁 所有数据已保存到data目录")
    print("💡 建议：根据信号分析结果进行交易决策")
    print("🔥 核心功能：qstock真实数据 + EasyXT真实交易")
    print("🛠️  修复内容：交易服务初始化流程")
    print("⚠️  风险提示：量化交易存在风险，请谨慎操作")
    print("=" * 60)

if __name__ == "__main__":
    main()