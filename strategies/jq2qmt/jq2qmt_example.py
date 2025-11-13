# 导入函数库
import time
import requests
from datetime import datetime as dt

# 简化的QMT客户端，通过中转服务发送信号
class QMTClient:
    """QMT客户端 - 通过中转服务发送信号"""
    
    def __init__(self, base_url="http://www.ptqmt.com:8080", token="test_token"):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def send_signal(self, strategy_name, stock_code, order_type, order_volume, price_type, price):
        """发送交易信号到中转服务"""
        # 处理股票代码格式 - 确保使用QMT支持的格式
        if stock_code.endswith('.XSHE'):
            # 转换聚宽格式到QMT格式
            stock_code = stock_code.replace('.XSHE', '.SZ')
        elif stock_code.endswith('.XSHG'):
            # 转换聚宽格式到QMT格式
            stock_code = stock_code.replace('.XSHG', '.SH')
        
        payload = {
            "strategy_name": strategy_name,
            "stock_code": stock_code,
            "order_type": order_type,
            "order_volume": order_volume,
            "price_type": price_type,
            "price": price
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/send_signal",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return result.get('signal_id')
                else:
                    print(f"❌ 信号发送失败: {result.get('message')}")
                    return None
            else:
                print(f"❌ HTTP错误: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ 异常: {e}")
            return None

try:
    from jqdata import *
except ImportError:
    # 在非聚宽环境中提供模拟函数
    
    def get_current_data():
        class MockCurrentData:
            def __getitem__(self, key):
                class MockStockData:
                    def __init__(self):
                        self.paused = False
                        self.last_price = 10.0
                        self.high_limit = 11.0
                        self.low_limit = 9.0
                return MockStockData()
        return MockCurrentData()
    
    class SecurityNotExist(Exception):
        pass
    
    class OrderCost:
        def __init__(self, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5):
            pass
    
    class MockContext:
        def __init__(self):
            self.current_dt = dt.now()
            class Portfolio:
                def __init__(self):
                    self.available_cash = 100000
                    class Positions:
                        def __init__(self):
                            self.total_amount = 1000
                        def __getitem__(self, key):
                            return self
                    self.positions = Positions()
                    self.positions_value = 50000
                def __getattr__(self, name):
                    return getattr(self, name, 0)
            self.portfolio = Portfolio()
        
        def __getattr__(self, name):
            return getattr(self, name, None)
    
    context = MockContext()
    
    def set_benchmark(security):
        pass
    
    def set_option(key, value):
        pass
    
    def set_order_cost(cost, type='stock'):
        pass
    
    def run_daily(func, time='09:30', reference_security='000300.XSHG'):
        pass
    
    def get_bars(security, count=5, unit='1d', fields=['close'], include_now=True):
        import pandas as pd
        import numpy as np
        data = {
            'close': np.random.rand(count) * 10 + 5
        }
        return pd.DataFrame(data)
    
    def get_trades():
        return {}
    
    def order(security, amount):
        class MockOrderResult:
            def __init__(self):
                self.status = 'filled'
                self.add_time = dt.now()
                self.is_buy = True
                self.amount = 100
                self.filled = 100
                self.security = security
                self.order_id = 'mock_order_id'
                self.price = 10.5
                self.avg_cost = 10.5
                self.side = 'long'
                self.action = 'open'
                self.commission = 0.0
        return MockOrderResult()
    
    def order_target(security, amount):
        class MockOrderResult:
            def __init__(self):
                self.status = 'filled'
                self.add_time = dt.now()
                self.is_buy = True
                self.amount = 100
                self.filled = 100
                self.security = security
                self.order_id = 'mock_order_id'
                self.price = 10.5
                self.avg_cost = 10.5
                self.side = 'long'
                self.action = 'open'
                self.commission = 0.0
        return MockOrderResult()
    
    def order_value(security, value):
        class MockOrderResult:
            def __init__(self):
                self.status = 'filled'
                self.add_time = dt.now()
                self.is_buy = True
                self.amount = 100
                self.filled = 100
                self.security = security
                self.order_id = 'mock_order_id'
                self.price = 10.5
                self.avg_cost = 10.5
                self.side = 'long'
                self.action = 'open'
                self.commission = 0.0
        return MockOrderResult()
    
    def order_target_value(security, value):
        class MockOrderResult:
            def __init__(self):
                self.status = 'filled'
                self.add_time = dt.now()
                self.is_buy = True
                self.amount = 100
                self.filled = 100
                self.security = security
                self.order_id = 'mock_order_id'
                self.price = 10.5
                self.avg_cost = 10.5
                self.side = 'long'
                self.action = 'open'
                self.commission = 0.0
        return MockOrderResult()

# 添加模拟日志函数
try:
    # 尝试使用聚宽的log函数
    from jqdata import log
except (ImportError, NameError):
    # 如果不存在，创建模拟log函数
    class MockLogger:
        def info(self, *args):
            print("INFO:", *args)
        
        def warning(self, *args):
            print("WARNING:", *args)
        
        def error(self, *args):
            print("ERROR:", *args)
    
    log = MockLogger()

# 初始化客户端（使用中转服务地址）
client = QMTClient(
    base_url="http://www.ptqmt.com:8080",  # 使用中转服务地址
    token="test_token"  # 使用中转服务的测试token
)

# 定义常量（直接使用数字而不是xtconstant）
# 订单类型
ORDER_TYPE_BUY = 23      # 买入
ORDER_TYPE_SELL = 24     # 卖出

# 价格类型
PRICE_TYPE_LIMIT = 11            # 限价单 (FIX_PRICE)
PRICE_TYPE_MARKET = 44           # 市价单 (MARKET_PEER_PRICE_FIRST)
PRICE_TYPE_MARKET_MINE = 45      # 本方最优价格委托 (MARKET_MINE_PRICE_FIRST)

def send_limit_order(security, adjustment, strategy_name, price=None, current_data=None):
    """
    发送限价单的通用函数（通过中转服务）
    
    参数:
    security: 股票代码（聚宽格式，如 000001.XSHE）
    adjustment: 调整数量（正数为买入，负数为卖出）
    strategy_name: 策略名称
    price: 订单价格（可选，不提供则使用当前价格微调）
    current_data: 当前数据对象，可选
    
    返回:
    str: 信号ID或None（失败）
    """
    try:
        # 获取当前数据
        if current_data is None:
            current_data = get_current_data()

        # 检查股票是否停牌
        if current_data[security].paused:
            log.warning(f"[{strategy_name}] {security} 停牌，无法交易")
            return None

        # 涨停/跌停检查
        if current_data[security].last_price == current_data[security].high_limit:
            if adjustment > 0:  # 买入时涨停
                log.warning(f"[{strategy_name}] {security} 涨停，无法买入")
                return None
        elif current_data[security].last_price == current_data[security].low_limit:
            if adjustment < 0:  # 卖出时跌停
                log.warning(f"[{strategy_name}] {security} 跌停，无法卖出")
                return None

        # 获取当前价格
        current_price = current_data[security].last_price
        if current_price <= 0:
            log.error(f"[{strategy_name}] {security} 价格无效: {current_price}")
            return None

        # 确定买卖方向
        order_type = ORDER_TYPE_BUY if adjustment > 0 else ORDER_TYPE_SELL

        # 确定价格
        if price is None:
            # 根据买卖方向调整价格确保成交
            if order_type == ORDER_TYPE_BUY:
                # 买入时价格上浮1%
                adjusted_price = current_price * 1.01
            else:
                # 卖出时价格下浮1%
                adjusted_price = current_price * 0.99
        else:
            adjusted_price = price

        # 保留两位小数
        adjusted_price = round(adjusted_price, 2)

        # 处理股票代码格式 - 确保使用QMT支持的格式
        stock_code = security
        if security.endswith('.XSHE'):
            # 转换聚宽格式到QMT格式
            stock_code = security.replace('.XSHE', '.SZ')
        elif security.endswith('.XSHG'):
            # 转换聚宽格式到QMT格式
            stock_code = security.replace('.XSHG', '.SH')
        elif '.' not in security:
            # 如果没有后缀，根据股票代码规则添加
            number_part = ''.join(filter(str.isdigit, security))
            if len(number_part) == 6:
                if number_part.startswith('6') or number_part.startswith('5'):
                    stock_code = number_part + '.SH'
                elif number_part.startswith('0') or number_part.startswith('3') or number_part.startswith('1'):
                    stock_code = number_part + '.SZ'
                elif number_part.startswith('4') or number_part.startswith('8'):
                    stock_code = number_part + '.BJ'

        # 确保股票代码格式正确（数字.SH/SZ/BJ）
        if not (stock_code.endswith('.SH') or stock_code.endswith('.SZ') or stock_code.endswith('.BJ')):
            log.error(f"[{strategy_name}] 股票代码格式错误: {stock_code}")
            return None

        # 发送限价单信号到中转服务
        current_time_ms = dt.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # 精确到毫秒
        order_remark = f"{strategy_name}_{current_time_ms}"  # 格式为：策略名称_时间
        
        log.info(f"[限价单] {strategy_name} 发送: 股票={stock_code}, 类型={'买入' if order_type == ORDER_TYPE_BUY else '卖出'}, 数量={abs(adjustment)}, 价格={adjusted_price}")
        
        signal_id = client.send_signal(
            strategy_name=strategy_name,
            stock_code=stock_code,
            order_type=order_type,
            order_volume=abs(adjustment),
            price_type=PRICE_TYPE_LIMIT,  # 使用限价单常量
            price=adjusted_price
        )

        if signal_id:
            log.info(f"[限价单] {strategy_name} 发送成功，信号ID: {signal_id}")
        else:
            log.error(f"[限价单] {strategy_name} 发送失败")
        
        return signal_id
        
    except Exception as e:
        log.error(f"[{strategy_name}] 发送限价单失败: {str(e)}")
        return None

def send_market_order(security, adjustment, strategy_name, current_data=None):
    """
    发送市价单的通用函数（通过中转服务）
    
    参数:
    security: 股票代码（聚宽格式，如 000001.XSHE）
    adjustment: 调整数量（正数为买入，负数为卖出）
    strategy_name: 策略名称
    current_data: 当前数据对象，可选
    
    返回:
    str: 信号ID或None（失败）
    """
    try:
        # 获取当前数据
        if current_data is None:
            current_data = get_current_data()

        # 检查股票是否停牌
        if current_data[security].paused:
            log.warning(f"[{strategy_name}] {security} 停牌，无法交易")
            return None

        # 获取当前价格（用于日志，市价单不需要指定价格）
        current_price = current_data[security].last_price
        if current_price <= 0:
            log.error(f"[{strategy_name}] {security} 价格无效: {current_price}")
            return None

        # 确定买卖方向
        order_type = ORDER_TYPE_BUY if adjustment > 0 else ORDER_TYPE_SELL

        # 处理股票代码格式 - 确保使用QMT支持的格式
        stock_code = security
        if security.endswith('.XSHE'):
            # 转换聚宽格式到QMT格式
            stock_code = security.replace('.XSHE', '.SZ')
        elif security.endswith('.XSHG'):
            # 转换聚宽格式到QMT格式
            stock_code = security.replace('.XSHG', '.SH')
        elif '.' not in security:
            # 如果没有后缀，根据股票代码规则添加
            number_part = ''.join(filter(str.isdigit, security))
            if len(number_part) == 6:
                if number_part.startswith('6') or number_part.startswith('5'):
                    stock_code = number_part + '.SH'
                elif number_part.startswith('0') or number_part.startswith('3') or number_part.startswith('1'):
                    stock_code = number_part + '.SZ'
                elif number_part.startswith('4') or number_part.startswith('8'):
                    stock_code = number_part + '.BJ'

        # 确保股票代码格式正确（数字.SH/SZ/BJ）
        if not (stock_code.endswith('.SH') or stock_code.endswith('.SZ') or stock_code.endswith('.BJ')):
            log.error(f"[{strategy_name}] 股票代码格式错误: {stock_code}")
            return None

        # 发送市价单信号到中转服务
        current_time_ms = dt.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # 精确到毫秒
        order_remark = f"{strategy_name}_market_{current_time_ms}"  # 格式为：策略名称_market_时间
        
        log.info(f"[市价单] {strategy_name} 发送: 股票={stock_code}, 类型={'买入' if order_type == ORDER_TYPE_BUY else '卖出'}, 数量={abs(adjustment)}, 当前价格={current_price}")
        
        signal_id = client.send_signal(
            strategy_name=strategy_name,
            stock_code=stock_code,
            order_type=order_type,
            order_volume=abs(adjustment),
            price_type=PRICE_TYPE_MARKET,  # 使用市价单常量 (44 = 对手方最优价格)
            price=0  # 市价单价格设为0
        )

        if signal_id:
            log.info(f"[市价单] {strategy_name} 发送成功，信号ID: {signal_id}")
        else:
            log.error(f"[市价单] {strategy_name} 发送失败")
        
        return signal_id
        
    except Exception as e:
        log.error(f"[{strategy_name}] 发送市价单失败: {str(e)}")
        return None

# 股票池 - 增加更多股票（20只以上）
g = type('G', (), {})()  # 创建一个全局对象g
# 为g对象添加stock_pool属性
setattr(g, 'stock_pool', [
    '000001.XSHE',  # 平安银行
    '000002.XSHE',  # 万科A
    '000651.XSHE',  # 格力电器
    '000858.XSHE',  # 五粮液
    '002415.XSHE',  # 海康威视
    '600036.XSHG',    # 招商银行
    '600519.XSHG',    # 贵州茅台
    '601318.XSHG',    # 中国平安
    '000333.XSHE',  # 美的集团
    '600030.XSHG',    # 中信证券
    '000063.XSHE',  # 中兴通讯
    '600048.XSHG',    # 保利发展
    '002230.XSHE',  # 科大讯飞
    '300015.XSHE',  # 爱尔眼科
    '002475.XSHE',  # 立讯精密
    '600000.XSHG',    # 浦发银行
    '600104.XSHG',    # 上汽集团
    '000725.XSHE',  # 京东方A
    '002027.XSHE',  # 分众传媒
    '002142.XSHE',  # 宁波银行
    '600019.XSHG',    # 宝钢股份
    '600028.XSHG',    # 中国石化
    '600031.XSHG',    # 三一重工
    '600050.XSHG',    # 中国联通
    '600111.XSHG',    # 北方稀土
    '600276.XSHG',    # 恒瑞医药
    '600309.XSHG',    # 万华化学
    '600436.XSHG',    # 片仔癀
    '600703.XSHG',    # 三安光电
])

# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')

    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')

    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
      # 开盘前运行
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
      # 开盘时运行（每30分钟运行一次，增加交易频率）
    run_daily(market_open, time='09:30', reference_security='000300.XSHG')
    run_daily(market_open, time='10:00', reference_security='000300.XSHG')
    run_daily(market_open, time='10:30', reference_security='000300.XSHG')
    run_daily(market_open, time='11:00', reference_security='000300.XSHG')
    run_daily(market_open, time='11:30', reference_security='000300.XSHG')
    run_daily(market_open, time='13:00', reference_security='000300.XSHG')
    run_daily(market_open, time='13:30', reference_security='000300.XSHG')
    run_daily(market_open, time='14:00', reference_security='000300.XSHG')
    run_daily(market_open, time='14:30', reference_security='000300.XSHG')
      # 收盘后运行
    run_daily(after_market_close, time='after_close', reference_security='000300.XSHG')

## 开盘前运行函数
def before_market_open(context):
    # 输出运行时间
    log.info('函数运行时间(before_market_open)：'+str(context.current_dt.time()))

    # 随机选择一只股票进行交易（增加交易机会）
    import random
    # 验证股票代码是否存在
    available_stocks = []
    for stock in g.stock_pool:
        try:
            # 尝试获取股票信息来验证是否存在
            get_current_data()[stock]
            available_stocks.append(stock)
        except:
            log.info('股票 %s 不存在或无法获取数据，跳过' % stock)
            continue
    
    if available_stocks:
        g.security = random.choice(available_stocks)
        log.info('今日交易标的: %s (从%d只可用股票中随机选择)' % (g.security, len(available_stocks)))
    else:
        # 如果没有可用股票，默认使用平安银行
        g.security = '000001.XSHE'
        log.info('没有可用股票，使用默认股票: %s' % g.security)

## 开盘时运行函数（测试限价单和市价单）
def market_open(context):
    log.info('函数运行时间(market_open):'+str(context.current_dt.time()))
    security = g.security
    
    try:
        # 获取股票的当前价格
        current_data = get_current_data()
        current_price = current_data[security].last_price
        
        # 检查价格是否有效
        if current_price <= 0:
            log.info('股票 %s 当前价格无效: %.2f，跳过交易' % (security, current_price))
            return
            
        # 获取过去3根1分钟K线的数据
        close_data = get_bars(security, count=3, unit='1m', fields=['close'])
        
        if len(close_data) >= 2:
            # 计算短期价格变化率
            price_change = (current_price - close_data['close'][-2]) / close_data['close'][-2]
            
            # 取得当前的现金
            cash = context.portfolio.available_cash
            # 安全获取持仓数量
            try:
                position_amount = context.portfolio.positions[security].total_amount
            except:
                position_amount = 0
            
            # 更敏感的交易条件（0.2%的价格波动就触发交易）
            # 价格上涨0.2%以上且有资金则测试买入
            if price_change > 0.002 and cash > 1000:
                log.info("=" * 70)
                log.info("【测试】价格上涨 %.2f%%, 测试买入 %s" % (price_change*100, security))
                log.info("=" * 70)
                log.info("当前可用资金: ¥%.2f, 持仓数量: %d" % (cash, position_amount))
                
                # 计算交易数量（确保是100的整数倍）
                volume = 100  # 固定100股用于测试
                test_price = current_price * 1.01
                
                if volume > 0:
                    # ========== 测试限价单 ==========
                    log.info("\n【测试限价单】")
                    log.info("下单参数: 股票=%s, 类型=买入(23), 数量=%d股, 价格=%s, 价格类型=限价(11)" % (security, volume, test_price))
                    limit_result = send_limit_order(security, volume, 'LimitOrder_BUY', price=test_price, current_data=current_data)
                    
                    if limit_result is None:
                        log.error("限价单发送失败")
                    else:
                        log.info("限价单成功，信号ID: %s" % str(limit_result))
                    
                    # ========== 测试市价单 ==========
                    log.info("\n【测试市价单】")
                    log.info("下单参数: 股票=%s, 类型=买入(23), 数量=%d股, 价格类型=市价(44)" % (security, volume))
                    market_result = send_market_order(security, volume, 'MarketOrder_BUY', current_data=current_data)
                    
                    if market_result is None:
                        log.error("市价单发送失败")
                    else:
                        log.info("市价单成功，信号ID: %s" % str(market_result))
                    
                    log.info("\n【测试总结】")
                    log.info("限价单结果: %s | 市价单结果: %s" % (limit_result, market_result))
                    log.info("=" * 70)
                
            # 价格下跌0.2%以上且有持仓则测试卖出
            elif price_change < -0.002 and position_amount > 0:
                log.info("=" * 70)
                log.info("【测试】价格下跌 %.2f%%, 测试卖出 %s" % (abs(price_change)*100, security))
                log.info("=" * 70)
                log.info("当前持仓数量: %d" % position_amount)
                
                # 计算交易数量（确保是100的整数倍）
                volume = 100  # 固定100股用于测试
                test_price = current_price * 0.99
                
                if volume > 0:
                    # ========== 测试限价单卖出 ==========
                    log.info("\n【测试限价单卖出】")
                    log.info("下单参数: 股票=%s, 类型=卖出(24), 数量=%d股, 价格=%s, 价格类型=限价(11)" % (security, volume, test_price))
                    limit_result = send_limit_order(security, -volume, 'LimitOrder_SELL', price=test_price, current_data=current_data)
                    
                    if limit_result is None:
                        log.error("限价单发送失败")
                    else:
                        log.info("限价单成功，信号ID: %s" % str(limit_result))
                    
                    # ========== 测试市价单卖出 ==========
                    log.info("\n【测试市价单卖出】")
                    log.info("下单参数: 股票=%s, 类型=卖出(24), 数量=%d股, 价格类型=市价(44)" % (security, volume))
                    market_result = send_market_order(security, -volume, 'MarketOrder_SELL', current_data=current_data)
                    
                    if market_result is None:
                        log.error("市价单发送失败")
                    else:
                        log.info("市价单成功，信号ID: %s" % str(market_result))
                    
                    log.info("\n【测试总结】")
                    log.info("限价单结果: %s | 市价单结果: %s" % (limit_result, market_result))
                    log.info("=" * 70)
            else:
                log.info("价格波动较小 %.2f%%, 不触发交易" % (price_change*100))
        else:
            log.info("数据不足，跳过本次交易检查")
    except SecurityNotExist as e:
        log.error("股票 %s 不存在: %s" % (security, str(e)))
        # 从股票池中移除不存在的股票
        if hasattr(g, 'stock_pool') and security in g.stock_pool:
            g.stock_pool.remove(security)
            log.info("已从股票池中移除 %s" % security)
    except Exception as e:
        log.error("获取股票数据时发生错误: %s" % str(e))

## 收盘后运行函数
def after_market_close(context):
    log.info(str('函数运行时间(after_market_close):'+str(context.current_dt.time())))
    #得到当天所有成交记录
    trades = get_trades()
    for _trade in trades.values():
        log.info('成交记录：'+str(_trade))
    log.info('一天结束')
    log.info('##############################################################')