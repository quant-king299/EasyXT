#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略基础模板
所有策略都应该继承这个基类
"""

import sys
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import easy_xt


class BaseStrategy(ABC):
    """
    策略基类
    所有策略都应该继承这个类
    """
    
    def __init__(self, params: Dict[str, Any] = None):
        """
        初始化策略
        
        Args:
            params: 策略参数字典
        """
        self.params = params or {}
        self.api = easy_xt.get_api()
        self.positions = {}
        self.orders = []
        self.is_running = False
        self.start_time = None
        
    @abstractmethod
    def initialize(self):
        """
        策略初始化 - 子类必须实现
        """
        pass
        
    @abstractmethod
    def on_data(self, data):
        """
        数据处理 - 子类必须实现
        
        Args:
            data: 市场数据
        """
        pass
        
    def on_order(self, order):
        """
        订单状态变化处理
        
        Args:
            order: 订单信息
        """
        self.orders.append(order)
        print(f"订单状态更新: {order}")
        
    def buy(self, stock_code: str, quantity: int, price: float = None):
        """
        买入股票
        
        Args:
            stock_code: 股票代码
            quantity: 买入数量
            price: 买入价格，None表示市价
            
        Returns:
            订单结果
        """
        try:
            if price is None:
                result = self.api.trade.buy_market(stock_code, quantity)
                print(f"市价买入: {stock_code} {quantity}股")
            else:
                result = self.api.trade.buy_limit(stock_code, quantity, price)
                print(f"限价买入: {stock_code} {quantity}股 @{price}")
                
            return result
            
        except Exception as e:
            print(f"买入失败: {str(e)}")
            return None
            
    def sell(self, stock_code: str, quantity: int, price: float = None):
        """
        卖出股票
        
        Args:
            stock_code: 股票代码
            quantity: 卖出数量
            price: 卖出价格，None表示市价
            
        Returns:
            订单结果
        """
        try:
            if price is None:
                result = self.api.trade.sell_market(stock_code, quantity)
                print(f"市价卖出: {stock_code} {quantity}股")
            else:
                result = self.api.trade.sell_limit(stock_code, quantity, price)
                print(f"限价卖出: {stock_code} {quantity}股 @{price}")
                
            return result
            
        except Exception as e:
            print(f"卖出失败: {str(e)}")
            return None
            
    def get_position(self, stock_code: str):
        """
        获取持仓信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            持仓信息
        """
        try:
            return self.api.trade.get_position(stock_code)
        except Exception as e:
            print(f"获取持仓失败: {str(e)}")
            return None
            
    def get_account_info(self):
        """
        获取账户信息
        
        Returns:
            账户信息
        """
        try:
            return self.api.trade.get_account()
        except Exception as e:
            print(f"获取账户信息失败: {str(e)}")
            return None
            
    def log(self, message: str):
        """
        记录日志
        
        Args:
            message: 日志消息
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def start(self):
        """
        启动策略
        """
        self.is_running = True
        self.start_time = datetime.now()
        self.log(f"策略启动: {self.__class__.__name__}")
        
        try:
            self.initialize()
            self.run()
        except Exception as e:
            self.log(f"策略运行错误: {str(e)}")
        finally:
            self.stop()
            
    def stop(self):
        """
        停止策略
        """
        self.is_running = False
        self.log(f"策略停止: {self.__class__.__name__}")
        
    def run(self):
        """
        运行策略主循环
        """
        stock_code = self.params.get('股票代码', '000001.SZ')
        
        while self.is_running:
            try:
                # 获取数据
                data = self.api.data.get_price(stock_code, count=100)
                
                if data is not None and not data.empty:
                    self.on_data(data)
                else:
                    self.log("未获取到数据")
                    
                # 等待一段时间
                import time
                time.sleep(1)
                
            except KeyboardInterrupt:
                self.log("用户中断策略")
                break
            except Exception as e:
                self.log(f"策略运行异常: {str(e)}")
                break