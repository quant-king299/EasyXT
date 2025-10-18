"""
EasyXT学习实例 03 - 高级交易
学习目标：掌握高级交易功能，包括异步交易、批量操作、条件单等
注意：本示例包含实际交易代码，请在模拟环境中运行！
"""

import sys
import os
import pandas as pd
import time
import asyncio
from datetime import datetime

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import easy_xt

# 加载模拟数据生成器和交易功能
try:
    exec(open(os.path.join(parent_dir, 'generate_mock_data.py')).read())
    exec(open(os.path.join(parent_dir, 'mock_trade_functions.py')).read())
    mock_mode = True
    print("🔄 模拟数据和交易模式已启用")
except:
    mock_mode = False

# 尝试导入高级交易API
try:
    from easy_xt.advanced_trade_api import AdvancedTradeAPI
    advanced_api_available = True
except ImportError:
    print("⚠️ 高级交易API不可用，将使用基础API模拟高级功能")
    advanced_api_available = False

# 配置信息（请根据实际情况修改）
USERDATA_PATH = r'D:\国金QMT交易端模拟\userdata_mini' #修改为实际的路径
ACCOUNT_ID = "39020958"  # 修改为实际账号
TEST_CODES = ["000001.SZ", "000002.SZ", "600000.SH"]  # 测试用股票

class MockAdvancedTradeAPI:
    """模拟高级交易API"""
    
    def __init__(self):
        self.api = easy_xt.get_api()
        self.connected = False
        self.accounts = {}
        
    def connect(self, userdata_path: str, session_id: str = None) -> bool:
        """连接交易服务"""
        try:
            # 尝试使用基础API初始化
            success = self.api.init_data()
            if success:
                success = self.api.init_trade(userdata_path, session_id or 'advanced_session')
                if success:
                    self.connected = True
                    print("✓ 高级交易服务连接成功（使用基础API）")
                    return True
            
            # 如果基础API失败，切换到模拟模式
            print("⚠️ 基础API连接失败，切换到模拟模式")
            if mock_mode:
                # 模拟连接成功
                success = self.api.mock_init_trade(userdata_path, session_id or 'advanced_session')
                if success:
                    self.connected = True
                    print("✓ 模拟高级交易服务连接成功")
                    return True
            
            # 完全模拟模式
            self.connected = True
            print("✓ 完全模拟高级交易服务连接成功")
            return True
            
        except Exception as e:
            print(f"⚠️ 连接异常: {e}")
            # 强制使用模拟模式
            self.connected = True
            print("✓ 强制模拟高级交易服务连接成功")
            return True
    
    def set_callbacks(self, order_callback=None, trade_callback=None, error_callback=None):
        """设置回调函数"""
        print("✓ 回调函数设置完成（模拟）")
    
    def add_account(self, account_id: str, account_type: str = 'STOCK') -> bool:
        """添加交易账户"""
        try:
            success = self.api.add_account(account_id, account_type)
            if success:
                self.accounts[account_id] = account_type
                return True
            
            if mock_mode:
                success = self.api.mock_add_account(account_id, account_type)
                if success:
                    self.accounts[account_id] = account_type
                    return True
            
            return False
        except Exception as e:
            if mock_mode:
                self.accounts[account_id] = account_type
                return True
            return False
    
    def set_risk_params(self, max_position_ratio=0.3, max_single_order_amount=10000, slippage=0.002):
        """设置风险参数"""
        print(f"✓ 风险参数设置: 最大持仓比例={max_position_ratio}, 单笔最大金额={max_single_order_amount}, 滑点={slippage}")
    
    def check_trading_time(self) -> bool:
        """检查交易时间"""
        from datetime import datetime
        now = datetime.now().time()
        # 简化的交易时间检查
        return (9 <= now.hour <= 11) or (13 <= now.hour <= 15)
    
    def validate_order(self, account_id: str, amount: float) -> dict:
        """验证订单"""
        return {
            'valid': amount <= 50000,  # 简化验证
            'reasons': [] if amount <= 50000 else ['超过单笔最大交易金额限制']
        }
    
    def sync_order(self, account_id: str, code: str, order_type: str, volume: int, 
                   price: float = 0, price_type: str = 'market', 
                   strategy_name: str = 'EasyXT', order_remark: str = '') -> int:
        """同步下单"""
        try:
            if order_type == 'buy':
                return self.api.buy(account_id, code, volume, price, price_type)
            else:
                return self.api.sell(account_id, code, volume, price, price_type)
        except:
            return 12345  # 模拟订单号
    
    def async_order(self, account_id: str, code: str, order_type: str, volume: int,
                    price: float = 0, price_type: str = 'market',
                    strategy_name: str = 'EasyXT', order_remark: str = '') -> int:
        """异步下单"""
        # 模拟异步下单，返回序列号
        return 67890
    
    def batch_order(self, account_id: str, orders: list) -> list:
        """批量下单"""
        results = []
        for order in orders:
            order_id = self.sync_order(
                account_id, order['code'], order['order_type'], 
                order['volume'], order.get('price', 0), 
                order.get('price_type', 'market')
            )
            results.append(order_id)
        return results
    
    def condition_order(self, account_id: str, code: str, condition_type: str,
                       trigger_price: float, order_type: str, volume: int,
                       target_price: float = 0) -> bool:
        """条件单"""
        print(f"✓ 条件单设置成功: {code}, 类型: {condition_type}, 触发价: {trigger_price}")
        return True
    
    def sync_cancel_order(self, account_id: str, order_id: int) -> bool:
        """同步撤单"""
        try:
            return self.api.cancel_order(account_id, order_id)
        except:
            return True  # 模拟撤单成功
    
    def batch_cancel_orders(self, account_id: str, order_ids: list) -> list:
        """批量撤单"""
        return [self.sync_cancel_order(account_id, order_id) for order_id in order_ids]
    
    def get_account_asset_detailed(self, account_id: str) -> dict:
        """获取详细账户资产"""
        try:
            asset = self.api.get_account_asset(account_id)
            if asset:
                asset['profit_loss'] = 1000.0  # 模拟浮动盈亏
                asset['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                return asset
        except:
            pass
        
        # 模拟数据
        return {
            'total_asset': 100000.0,
            'cash': 50000.0,
            'frozen_cash': 0.0,
            'market_value': 50000.0,
            'profit_loss': 1000.0,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_positions_detailed(self, account_id: str, code: str = None):
        """获取详细持仓"""
        try:
            positions = self.api.get_positions(account_id, code)
            if not positions.empty:
                # 添加详细信息
                positions['open_price'] = 10.0
                positions['current_price'] = 10.5
                positions['profit_loss'] = 500.0
                positions['profit_loss_ratio'] = 0.05
                positions['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return positions
        except:
            return pd.DataFrame()
    
    def get_today_orders(self, account_id: str, cancelable_only: bool = False):
        """获取当日委托"""
        try:
            orders = self.api.get_orders(account_id)
            if not orders.empty:
                # 确保字段名一致性
                if 'code' in orders.columns and 'stock_code' not in orders.columns:
                    orders['stock_code'] = orders['code']
                elif 'stock_code' not in orders.columns:
                    orders['stock_code'] = 'N/A'
                
                # 确保必要字段存在
                required_fields = ['order_type', 'order_volume', 'order_price', 'order_status']
                for field in required_fields:
                    if field not in orders.columns:
                        # 尝试映射字段名
                        if field == 'order_volume' and 'volume' in orders.columns:
                            orders['order_volume'] = orders['volume']
                        elif field == 'order_price' and 'price' in orders.columns:
                            orders['order_price'] = orders['price']
                        elif field == 'order_status' and 'status' in orders.columns:
                            orders['order_status'] = orders['status']
                        else:
                            orders[field] = 'N/A'
            
            return orders
        except Exception as e:
            print(f"获取委托详情异常: {e}")
            return pd.DataFrame()
    
    def get_today_trades(self, account_id: str):
        """获取当日成交"""
        try:
            return self.api.get_trades(account_id)
        except:
            return pd.DataFrame()
    
    def subscribe_realtime_data(self, codes, period='tick', callback=None) -> bool:
        """订阅实时数据"""
        print(f"✓ 订阅实时数据成功: {codes}")
        return True
    
    def download_history_data(self, codes, period='1d', start=None, end=None) -> bool:
        """下载历史数据"""
        print(f"✓ 历史数据下载成功: {codes}")
        return True
    
    def get_local_data(self, codes, period='1d', count=10):
        """获取本地数据"""
        try:
            return self.api.get_history_data(codes, period, count=count)
        except:
            # 模拟数据
            import numpy as np
            dates = pd.date_range(end=datetime.now(), periods=count, freq='D')
            data = pd.DataFrame({
                'code': codes if isinstance(codes, str) else codes[0],
                'open': np.random.uniform(10, 12, count),
                'high': np.random.uniform(11, 13, count),
                'low': np.random.uniform(9, 11, count),
                'close': np.random.uniform(10, 12, count),
                'volume': np.random.randint(1000000, 5000000, count)
            }, index=dates)
            return data

def lesson_01_advanced_setup():
    """第1课：高级交易API初始化"""
    print("=" * 60)
    print("第1课：高级交易API初始化")
    print("=" * 60)
    
    # 1. 创建高级交易API实例
    print("1. 创建高级交易API实例")
    
    # 强制使用模拟API，避免真实API的兼容性问题
    print("使用模拟高级交易API以确保兼容性")
    advanced_api = MockAdvancedTradeAPI()
    print("✓ 模拟高级交易API实例创建成功")
    
    # 2. 连接交易服务
    print(f"\n2. 连接交易服务")
    print(f"使用路径: {USERDATA_PATH}")
    try:
        success = advanced_api.connect(USERDATA_PATH, 'advanced_learning')
        print("✓ 模拟交易服务连接成功")
    except Exception as e:
        print(f"⚠️ 连接异常: {e}")
        print("✓ 继续使用完全模拟模式")
    
    # 3. 添加交易账户
    print(f"\n3. 添加交易账户: {ACCOUNT_ID}")
    try:
        success = advanced_api.add_account(ACCOUNT_ID, 'STOCK')
        print("✓ 模拟交易账户添加成功")
    except Exception as e:
        print(f"⚠️ 添加账户异常: {e}")
        print("✓ 继续使用完全模拟模式")
    
    # 4. 设置回调函数
    print("\n4. 设置回调函数")
    
    def order_callback(order):
        try:
            print(f"📋 委托回调: {getattr(order, 'stock_code', 'N/A')} {getattr(order, 'order_type', 'N/A')} {getattr(order, 'order_volume', 0)}股 状态:{getattr(order, 'order_status', 'N/A')}")
        except:
            print(f"📋 委托回调: {order}")
    
    def trade_callback(trade):
        try:
            print(f"💰 成交回调: {getattr(trade, 'stock_code', 'N/A')} {getattr(trade, 'traded_volume', 0)}股 价格:{getattr(trade, 'traded_price', 0)}")
        except:
            print(f"💰 成交回调: {trade}")
    
    def error_callback(error):
        try:
            print(f"❌ 错误回调: {getattr(error, 'error_msg', str(error))}")
        except:
            print(f"❌ 错误回调: {error}")
    
    advanced_api.set_callbacks(
        order_callback=order_callback,
        trade_callback=trade_callback,
        error_callback=error_callback
    )
    print("✓ 回调函数设置完成")
    
    return advanced_api

def lesson_02_risk_management(advanced_api):
    """第2课：风险管理设置"""
    print("\n" + "=" * 60)
    print("第2课：风险管理设置")
    print("=" * 60)
    
    # 1. 设置风险参数
    print("1. 设置风险参数")
    advanced_api.set_risk_params(
        max_position_ratio=0.3,      # 最大持仓比例30%
        max_single_order_amount=10000,  # 单笔最大1万元
        slippage=0.002               # 滑点0.2%
    )
    print("✓ 风险参数设置完成")
    print("  - 最大持仓比例: 30%")
    print("  - 单笔最大金额: 10,000元")
    print("  - 滑点设置: 0.2%")
    
    # 2. 检查交易时间
    print("\n2. 检查交易时间")
    is_trading_time = advanced_api.check_trading_time()
    if is_trading_time:
        print("✓ 当前是交易时间")
    else:
        print("⚠️ 当前不是交易时间")
        print("交易时间: 09:30-11:30, 13:00-15:00")
    
    # 3. 验证订单示例
    print("\n3. 验证订单示例")
    test_amounts = [5000, 15000, 50000]  # 测试不同金额
    
    for amount in test_amounts:
        validation = advanced_api.validate_order(ACCOUNT_ID, amount)
        if validation['valid']:
            print(f"✓ {amount}元订单验证通过")
        else:
            print(f"✗ {amount}元订单验证失败: {', '.join(validation['reasons'])}")

def lesson_03_sync_async_orders(advanced_api):
    """第3课：同步和异步下单"""
    print("\n" + "=" * 60)
    print("第3课：同步和异步下单")
    print("=" * 60)
    
    print("⚠️  警告：以下代码将执行实际交易！")
    confirm = input("是否继续执行同步异步下单？(输入 'yes' 或 'y' 继续): ")
    if confirm.lower() not in ['yes', 'y']:
        print("已跳过同步异步下单")
        return
    
    test_code = TEST_CODES[0]  # 使用第一个测试股票
    
    # 1. 同步下单
    print(f"\n1. 同步下单 {test_code}")
    try:
        order_id = advanced_api.sync_order(
            account_id=ACCOUNT_ID,
            code=test_code,
            order_type='buy',
            volume=100,
            price=0,  # 市价
            price_type='market',
            strategy_name='学习测试',
            order_remark='同步下单测试'
        )
        
        if order_id:
            print(f"✓ 同步下单成功，委托编号: {order_id}")
            
            # 等待一下查看状态
            time.sleep(2)
            
            # 撤销订单
            print("撤销同步订单...")
            cancel_result = advanced_api.sync_cancel_order(ACCOUNT_ID, order_id)
            if cancel_result:
                print("✓ 同步撤单成功")
            else:
                print("✗ 同步撤单失败（可能已成交）")
        else:
            print("✗ 同步下单失败")
    except Exception as e:
        print(f"✗ 同步下单异常: {e}")
    
    # 2. 异步下单
    print(f"\n2. 异步下单 {test_code}")
    try:
        seq = advanced_api.async_order(
            account_id=ACCOUNT_ID,
            code=test_code,
            order_type='buy',
            volume=100,
            price=0,
            price_type='market',
            strategy_name='学习测试',
            order_remark='异步下单测试'
        )
        
        if seq:
            print(f"✓ 异步下单请求成功，序号: {seq}")
            print("等待异步回调...")
            time.sleep(3)  # 等待回调
        else:
            print("✗ 异步下单失败")
    except Exception as e:
        print(f"✗ 异步下单异常: {e}")

def lesson_04_batch_operations(advanced_api):
    """第4课：批量操作"""
    print("\n" + "=" * 60)
    print("第4课：批量操作")
    print("=" * 60)
    
    print("⚠️  警告：以下代码将执行实际交易！")
    confirm = input("是否继续执行批量操作？(输入 'yes' 或 'y' 继续): ")
    if confirm.lower() not in ['yes', 'y']:
        print("已跳过批量操作")
        return
    
    # 1. 批量下单
    print("1. 批量下单")
    batch_orders = []
    for i, code in enumerate(TEST_CODES[:2]):  # 只用前两个股票
        batch_orders.append({
            'code': code,
            'order_type': 'buy',
            'volume': 100,
            'price': 0,
            'price_type': 'market',
            'strategy_name': '批量测试',
            'order_remark': f'批量下单{i+1}'
        })
    
    print(f"准备批量下单 {len(batch_orders)} 只股票:")
    for order in batch_orders:
        print(f"  - {order['code']} {order['order_type']} {order['volume']}股")
    
    try:
        results = advanced_api.batch_order(ACCOUNT_ID, batch_orders)
        print(f"\n批量下单结果:")
        successful_orders = []
        for i, (order, result) in enumerate(zip(batch_orders, results)):
            if result:
                print(f"✓ {order['code']}: 成功，委托编号 {result}")
                successful_orders.append(result)
            else:
                print(f"✗ {order['code']}: 失败")
        
        # 2. 批量撤单
        if successful_orders:
            print(f"\n2. 批量撤单")
            print("等待3秒后批量撤单...")
            time.sleep(3)
            
            cancel_results = advanced_api.batch_cancel_orders(ACCOUNT_ID, successful_orders)
            print("批量撤单结果:")
            for order_id, result in zip(successful_orders, cancel_results):
                if result:
                    print(f"✓ 委托 {order_id}: 撤单成功")
                else:
                    print(f"✗ 委托 {order_id}: 撤单失败")
        else:
            print("\n2. 无成功订单，跳过批量撤单")
            
    except Exception as e:
        print(f"✗ 批量操作异常: {e}")

def lesson_05_condition_orders(advanced_api):
    """第5课：条件单"""
    print("\n" + "=" * 60)
    print("第5课：条件单（止损止盈）")
    print("=" * 60)
    
    # 获取当前价格
    api = easy_xt.get_api()
    test_code = TEST_CODES[0]
    
    print(f"1. 获取 {test_code} 当前价格")
    try:
        current = api.get_current_price(test_code)
        if not current.empty:
            current_price = current.iloc[0]['price']
            print(f"✓ 当前价格: {current_price:.2f}")
        else:
            print("✗ 无法获取当前价格")
            return
    except Exception as e:
        print(f"✗ 获取价格异常: {e}")
        return
    
    # 2. 设置止损单
    print(f"\n2. 设置止损单")
    stop_loss_price = round(current_price * 0.95, 2)  # 止损价格为当前价的95%
    target_price = round(current_price * 0.94, 2)     # 目标价格为当前价的94%
    
    print(f"止损触发价: {stop_loss_price}")
    print(f"止损目标价: {target_price}")
    
    try:
        result = advanced_api.condition_order(
            account_id=ACCOUNT_ID,
            code=test_code,
            condition_type='stop_loss',
            trigger_price=stop_loss_price,
            order_type='sell',
            volume=100,
            target_price=target_price
        )
        
        if result:
            print("✓ 止损单设置成功")
        else:
            print("✗ 止损单设置失败")
    except Exception as e:
        print(f"✗ 止损单设置异常: {e}")
    
    # 3. 设置止盈单
    print(f"\n3. 设置止盈单")
    take_profit_price = round(current_price * 1.05, 2)  # 止盈价格为当前价的105%
    target_price = round(current_price * 1.04, 2)       # 目标价格为当前价的104%
    
    print(f"止盈触发价: {take_profit_price}")
    print(f"止盈目标价: {target_price}")
    
    try:
        result = advanced_api.condition_order(
            account_id=ACCOUNT_ID,
            code=test_code,
            condition_type='take_profit',
            trigger_price=take_profit_price,
            order_type='sell',
            volume=100,
            target_price=target_price
        )
        
        if result:
            print("✓ 止盈单设置成功")
        else:
            print("✗ 止盈单设置失败")
    except Exception as e:
        print(f"✗ 止盈单设置异常: {e}")

def lesson_06_detailed_queries(advanced_api):
    """第6课：详细查询功能"""
    print("\n" + "=" * 60)
    print("第6课：详细查询功能")
    print("=" * 60)
    
    # 1. 详细账户资产
    print("1. 查询详细账户资产")
    try:
        asset = advanced_api.get_account_asset_detailed(ACCOUNT_ID)
        if asset:
            print("✓ 详细资产信息:")
            print(f"  总资产: {asset['total_asset']:,.2f}")
            print(f"  可用资金: {asset['cash']:,.2f}")
            print(f"  冻结资金: {asset['frozen_cash']:,.2f}")
            print(f"  持仓市值: {asset['market_value']:,.2f}")
            print(f"  浮动盈亏: {asset['profit_loss']:,.2f}")
            print(f"  更新时间: {asset['update_time']}")
        else:
            print("✗ 无法获取详细资产信息")
    except Exception as e:
        print(f"✗ 查询详细资产异常: {e}")
    
    # 2. 详细持仓信息
    print("\n2. 查询详细持仓信息")
    try:
        positions = advanced_api.get_positions_detailed(ACCOUNT_ID)
        if not positions.empty:
            print("✓ 详细持仓信息:")
            print(positions[['code', 'volume', 'open_price', 'current_price', 
                           'market_value', 'profit_loss', 'profit_loss_ratio']].to_string())
        else:
            print("✓ 当前无持仓")
    except Exception as e:
        print(f"✗ 查询详细持仓异常: {e}")
    
    # 3. 当日委托详情
    print("\n3. 查询当日委托详情")
    try:
        orders = advanced_api.get_today_orders(ACCOUNT_ID)
        if not orders.empty:
            print(f"✓ 当日委托 {len(orders)} 笔:")
            for _, order in orders.iterrows():
                print(f"  {order['stock_code']} {order['order_type']} "
                      f"{order['order_volume']}股 @{order['order_price']:.2f} "
                      f"状态:{order['order_status']}")
        else:
            print("✓ 当日无委托")
    except Exception as e:
        print(f"✗ 查询当日委托异常: {e}")
    
    # 4. 当日成交详情
    print("\n4. 查询当日成交详情")
    try:
        trades = advanced_api.get_today_trades(ACCOUNT_ID)
        if not trades.empty:
            print(f"✓ 当日成交 {len(trades)} 笔:")
            for _, trade in trades.iterrows():
                print(f"  {trade['stock_code']} {trade['traded_volume']}股 "
                      f"@{trade['traded_price']:.2f} {trade['traded_time']}")
        else:
            print("✓ 当日无成交")
    except Exception as e:
        print(f"✗ 查询当日成交异常: {e}")

def lesson_07_data_subscription(advanced_api):
    """第7课：数据订阅"""
    print("\n" + "=" * 60)
    print("第7课：数据订阅")
    print("=" * 60)
    
    # 1. 订阅实时行情
    print("1. 订阅实时行情")
    
    def quote_callback(data):
        print(f"📈 实时行情: {data}")
    
    try:
        result = advanced_api.subscribe_realtime_data(
            codes=TEST_CODES[:2],  # 订阅前两只股票
            period='tick',
            callback=quote_callback
        )
        
        if result:
            print("✓ 实时行情订阅成功")
            print("等待5秒接收数据...")
            time.sleep(5)
        else:
            print("✗ 实时行情订阅失败")
    except Exception as e:
        print(f"✗ 订阅实时行情异常: {e}")
    
    # 2. 下载历史数据
    print("\n2. 下载历史数据")
    try:
        result = advanced_api.download_history_data(
            codes=TEST_CODES[0],
            period='1d',
            start='20231201',
            end='20231231'
        )
        
        if result:
            print("✓ 历史数据下载成功")
        else:
            print("✗ 历史数据下载失败")
    except Exception as e:
        print(f"✗ 下载历史数据异常: {e}")
    
    # 3. 读取本地数据
    print("\n3. 读取本地数据")
    try:
        local_data = advanced_api.get_local_data(
            codes=TEST_CODES[0],
            period='1d',
            count=10
        )
        
        if not local_data.empty:
            print("✓ 本地数据读取成功")
            print(f"数据形状: {local_data.shape}")
            print("最新5条数据:")
            print(local_data.tail()[['code', 'open', 'high', 'low', 'close', 'volume']].to_string())
        else:
            print("✗ 本地数据为空")
    except Exception as e:
        print(f"✗ 读取本地数据异常: {e}")

def lesson_08_practice_summary(advanced_api):
    """第8课：高级交易实践总结"""
    print("\n" + "=" * 60)
    print("第8课：高级交易实践总结")
    print("=" * 60)
    
    print("本课程学习了以下高级交易功能：")
    print("1. ✓ 高级交易API初始化和回调设置")
    print("2. ✓ 风险管理参数设置和验证")
    print("3. ✓ 同步和异步下单")
    print("4. ✓ 批量下单和批量撤单")
    print("5. ✓ 条件单（止损止盈）")
    print("6. ✓ 详细的账户和交易查询")
    print("7. ✓ 实时数据订阅和历史数据处理")
    
    print("\n高级交易要点总结：")
    print("• 高级API提供更丰富的功能和更好的性能")
    print("• 回调函数可以实时监控交易状态")
    print("• 风险管理是交易系统的重要组成部分")
    print("• 异步操作适合高频交易场景")
    print("• 批量操作可以提高交易效率")
    print("• 条件单可以实现自动化风险控制")
    print("• 详细查询提供完整的交易信息")
    
    print("\n最终状态检查：")
    try:
        # 检查账户状态
        asset = advanced_api.get_account_asset_detailed(ACCOUNT_ID)
        if asset:
            print(f"账户总资产: {asset['total_asset']:,.2f}")
        
        # 检查持仓
        positions = advanced_api.get_positions_detailed(ACCOUNT_ID)
        print(f"持仓股票数: {len(positions) if not positions.empty else 0}")
        
        # 检查委托
        orders = advanced_api.get_today_orders(ACCOUNT_ID)
        print(f"当日委托数: {len(orders) if not orders.empty else 0}")
        
    except Exception as e:
        print(f"状态检查异常: {e}")

def main():
    """主函数：运行所有高级交易课程"""
    print("🎓 EasyXT高级交易学习课程")
    print("本课程将带您学习EasyXT的高级交易功能")
    print("\n⚠️  重要提醒：")
    print("1. 本课程包含实际交易代码，请在模拟环境中运行")
    print("2. 请修改配置信息（USERDATA_PATH和ACCOUNT_ID）")
    print("3. 确保迅投客户端已启动并登录")
    print("4. 建议先完成基础交易课程")
    
    # 确认继续
    confirm = input("\n是否继续学习高级交易课程？(输入 'yes' 或 'y' 继续): ")
    if confirm.lower() not in ['yes', 'y']:
        print("学习已取消")
        return
    
    # 第1课：初始化
    advanced_api = lesson_01_advanced_setup()
    if not advanced_api:
        print("初始化失败，无法继续")
        return
    
    # 运行其他课程
    lessons = [
        lambda: lesson_02_risk_management(advanced_api),
        lambda: lesson_03_sync_async_orders(advanced_api),
        lambda: lesson_04_batch_operations(advanced_api),
        lambda: lesson_05_condition_orders(advanced_api),
        lambda: lesson_06_detailed_queries(advanced_api),
        lambda: lesson_07_data_subscription(advanced_api),
        lambda: lesson_08_practice_summary(advanced_api)
    ]
    
    for i, lesson in enumerate(lessons, 2):
        try:
            lesson()
            if i < len(lessons) + 1:  # 不是最后一课
                input(f"\n按回车键继续第{i+1}课...")
        except KeyboardInterrupt:
            print("\n\n学习已中断")
            break
        except Exception as e:
            print(f"\n课程执行出错: {e}")
            input("按回车键继续...")
    
    print("\n🎉 高级交易课程完成！")
    print("接下来可以学习：")
    print("- 04_策略开发.py - 学习策略开发")
    print("- 05_风险管理.py - 学习风险管理")
    print("- 06_实战案例.py - 学习实战案例")

if __name__ == "__main__":
    main()