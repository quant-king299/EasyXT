#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PTQMT客户端
用于聚宽策略通过中转服务与QMT客户端通信
"""

import requests
import time
from datetime import datetime as dt

# 尝试导入聚宽环境的函数
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

# 添加模拟日志函数
try:
    # 尝试使用聚宽的log函数
    from jqdata import log
except ImportError:
    # 如果不存在，创建模拟log函数
    class MockLogger:
        def info(self, *args):
            print("INFO:", *args)
        
        def warning(self, *args):
            print("WARNING:", *args)
        
        def error(self, *args):
            print("ERROR:", *args)
    
    log = MockLogger()

class PTQMTClient:
    """PTQMT客户端 - 通过中转服务发送信号"""
    
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
    
    def get_result(self, signal_id):
        """查询交易执行结果"""
        try:
            response = requests.get(
                f"{self.base_url}/api/get_result/{signal_id}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return result.get('result')
                else:
                    print(f"❌ 查询结果失败: {result.get('message')}")
                    return None
            else:
                print(f"❌ HTTP错误: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ 异常: {e}")
            return None

# 初始化PTQMT客户端
ptqmt_client = PTQMTClient(
    base_url="http://www.ptqmt.com:8080",
    token="test_token"
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
    通过中转服务发送限价单信号
    
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

        # 发送限价单信号
        current_time_ms = dt.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # 精确到毫秒
        order_remark = f"{strategy_name}_{current_time_ms}"  # 格式为：策略名称_时间
        
        log.info(f"[限价单] {strategy_name} 发送: 股票={security}, 类型={'买入' if order_type == ORDER_TYPE_BUY else '卖出'}, 数量={abs(adjustment)}, 价格={adjusted_price}")
        
        signal_id = ptqmt_client.send_signal(
            strategy_name=strategy_name,
            stock_code=security,
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
    通过中转服务发送市价单信号
    
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

        # 发送市价单信号
        current_time_ms = dt.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # 精确到毫秒
        order_remark = f"{strategy_name}_market_{current_time_ms}"  # 格式为：策略名称_market_时间
        
        log.info(f"[市价单] {strategy_name} 发送: 股票={security}, 类型={'买入' if order_type == ORDER_TYPE_BUY else '卖出'}, 数量={abs(adjustment)}, 当前价格={current_price}")
        
        signal_id = ptqmt_client.send_signal(
            strategy_name=strategy_name,
            stock_code=security,
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

def query_order_result(signal_id):
    """
    查询订单执行结果
    
    参数:
    signal_id: 信号ID
    
    返回:
    dict: 执行结果或None（失败）
    """
    try:
        result = ptqmt_client.get_result(signal_id)
        if result:
            log.info(f"[结果查询] 信号ID {signal_id[:8]}... 查询成功")
            return result
        else:
            log.warning(f"[结果查询] 信号ID {signal_id[:8]}... 查询失败或暂无结果")
            return None
    except Exception as e:
        log.error(f"[结果查询] 查询信号ID {signal_id[:8]}... 失败: {str(e)}")
        return None