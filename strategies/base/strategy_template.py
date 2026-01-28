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
import pandas as pd

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import easy_xt


class BaseStrategy(ABC):
    """
    策略基类
    所有策略都应该继承这个类

    支持复权参数：
    - adjust='none': 不复权（原始价格，适合实时交易）
    - adjust='front': 前复权（当前价真实，适合短期回测）
    - adjust='back': 后复权（历史价真实，适合长期回测）
    """

    def __init__(self, params: Dict[str, Any] = None):
        """
        初始化策略

        Args:
            params: 策略参数字典，可包含：
                - adjust: 复权类型 ('none', 'front', 'back')
                - 其他策略参数...
        """
        self.params = params or {}
        self.api = easy_xt.get_api()

        # 复权参数
        self.adjust = self.params.get('adjust', 'none')  # 默认不复权
        valid_adjusts = ['none', 'front', 'back']
        if self.adjust not in valid_adjusts:
            raise ValueError(f"无效的复权类型 '{self.adjust}'，必须是: {valid_adjusts}")

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

    def get_historical_data(self,
                           stock_code: str,
                           start_date: str = None,
                           end_date: str = None,
                           period: str = '1d',
                           count: int = None) -> pd.DataFrame:
        """
        获取历史数据（支持复权）

        Args:
            stock_code: 股票代码
            start_date: 开始日期 (格式: '2023-01-01')
            end_date: 结束日期 (格式: '2024-12-31')
            period: 数据周期 ('1d', '1m', '5m', '15m', '30m', '1h')
            count: 数据条数（如果指定，忽略start_date）

        Returns:
            DataFrame: 价格数据（使用策略的复权设置）
        """
        try:
            df = self.api.data.get_price(
                codes=stock_code,
                start=start_date,
                end=end_date,
                period=period,
                count=count,
                adjust=self.adjust  # 使用策略的复权设置
            )
            return df
        except Exception as e:
            self.log(f"获取历史数据失败: {str(e)}")
            return pd.DataFrame()

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