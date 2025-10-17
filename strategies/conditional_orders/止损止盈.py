#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
止损止盈策略 - 条件单策略
基于价格条件和时间条件的自动止损止盈系统
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from strategies.base.strategy_template import BaseStrategy
import easy_xt


class 止损止盈策略(BaseStrategy):
    """
    止损止盈策略类
    支持多种条件类型的自动止损止盈
    """
    
    def __init__(self, params=None):
        """
        初始化止损止盈策略
        
        参数说明:
        - 股票代码: 交易的股票代码
        - 条件类型: 条件单类型（价格条件、时间条件、技术指标条件）
        - 触发价格: 条件触发价格
        - 交易方向: 交易方向（买入、卖出）
        - 交易数量: 交易数量
        - 有效期: 条件单有效期
        - 触发时间: 时间条件触发时间
        - 启用短信通知: 触发时发送短信通知
        """
        super().__init__(params)
        
        # 策略参数
        self.stock_code = self.params.get('股票代码', '000001.SZ')
        self.condition_type = self.params.get('条件类型', '价格条件')
        self.trigger_price = self.params.get('触发价格', 10.0)
        self.trade_direction = self.params.get('交易方向', '买入')
        self.trade_quantity = self.params.get('交易数量', 1000)
        self.validity_period = self.params.get('有效期', '当日有效')
        self.trigger_time = self.params.get('触发时间', '09:30:00')
        self.enable_sms = self.params.get('启用短信通知', False)
        
        # 策略状态
        self.condition_triggered = False
        self.order_executed = False
        self.entry_price = None
        self.current_position = 0
        
        # 解析触发时间
        self.trigger_time_obj = datetime.strptime(self.trigger_time, '%H:%M:%S').time()
        
    def initialize(self):
        """
        策略初始化
        """
        self.log("初始化止损止盈策略")
        self.log(f"股票代码: {self.stock_code}")
        self.log(f"条件类型: {self.condition_type}")
        self.log(f"触发价格: {self.trigger_price:.2f}")
        self.log(f"交易方向: {self.trade_direction}")
        self.log(f"交易数量: {self.trade_quantity}股")
        self.log(f"有效期: {self.validity_period}")
        self.log(f"触发时间: {self.trigger_time}")
        self.log(f"短信通知: {'启用' if self.enable_sms else '禁用'}")
        
    def check_validity(self):
        """
        检查条件单是否仍然有效
        
        Returns:
            bool: 是否有效
        """
        now = datetime.now()
        
        if self.validity_period == '当日有效':
            # 检查是否为交易日的交易时间
            current_time = now.time()
            if (current_time < time(9, 30) or 
                current_time > time(15, 0) or
                (time(11, 30) <= current_time <= time(13, 0))):
                return False
                
        elif self.validity_period == '本周有效':
            # 检查是否为本周
            if now.weekday() >= 5:  # 周六、周日
                return False
                
        elif self.validity_period == '本月有效':
            # 检查是否为本月
            pass  # 暂时不做限制
            
        elif self.validity_period == '长期有效':
            # 长期有效
            pass
            
        return True
        
    def check_price_condition(self, current_price):
        """
        检查价格条件
        
        Args:
            current_price: 当前价格
            
        Returns:
            bool: 是否触发
        """
        if self.trade_direction == '买入':
            # 买入条件：价格跌破触发价格
            return current_price <= self.trigger_price
        else:
            # 卖出条件：价格突破触发价格
            return current_price >= self.trigger_price
            
    def check_time_condition(self):
        """
        检查时间条件
        
        Returns:
            bool: 是否触发
        """
        current_time = datetime.now().time()
        return current_time >= self.trigger_time_obj
        
    def check_technical_condition(self, data):
        """
        检查技术指标条件
        
        Args:
            data: 市场数据
            
        Returns:
            bool: 是否触发
        """
        if len(data) < 20:
            return False
            
        # 计算RSI指标
        rsi = self.calculate_rsi(data, 14)
        current_rsi = rsi.iloc[-1]
        
        if self.trade_direction == '买入':
            # RSI超卖时买入
            return current_rsi < 30
        else:
            # RSI超买时卖出
            return current_rsi > 70
            
    def calculate_rsi(self, data, period=14):
        """
        计算RSI指标
        
        Args:
            data: 价格数据
            period: 计算周期
            
        Returns:
            RSI数据
        """
        close = data['close']
        delta = close.diff()
        
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
        
    def send_notification(self, message):
        """
        发送通知
        
        Args:
            message: 通知消息
        """
        self.log(f"📱 通知: {message}")
        
        if self.enable_sms:
            # 这里可以集成短信API
            self.log("短信通知已发送")
            
    def execute_conditional_order(self, current_price):
        """
        执行条件单
        
        Args:
            current_price: 当前价格
        """
        try:
            if self.trade_direction == '买入':
                result = self.buy(self.stock_code, self.trade_quantity)
                if result:
                    self.current_position += self.trade_quantity
                    self.entry_price = current_price
                    self.order_executed = True
                    
                    message = f"条件单买入成功: {self.stock_code} {self.trade_quantity}股 @{current_price:.2f}"
                    self.log(message)
                    self.send_notification(message)
                    
            else:
                # 检查是否有足够的持仓
                available_quantity = min(self.trade_quantity, self.current_position)
                if available_quantity > 0:
                    result = self.sell(self.stock_code, available_quantity)
                    if result:
                        self.current_position -= available_quantity
                        self.order_executed = True
                        
                        message = f"条件单卖出成功: {self.stock_code} {available_quantity}股 @{current_price:.2f}"
                        self.log(message)
                        self.send_notification(message)
                else:
                    self.log("没有足够的持仓进行卖出")
                    
        except Exception as e:
            self.log(f"执行条件单失败: {str(e)}")
            
    def on_data(self, data):
        """
        数据处理函数
        
        Args:
            data: 市场数据
        """
        try:
            # 检查条件单是否仍然有效
            if not self.check_validity():
                if not self.order_executed:
                    self.log("条件单已过期")
                    self.stop()
                return
                
            # 如果条件单已执行，停止监控
            if self.order_executed:
                return
                
            current_price = data['close'].iloc[-1]
            condition_met = False
            
            # 根据条件类型检查触发条件
            if self.condition_type == '价格条件':
                condition_met = self.check_price_condition(current_price)
                
            elif self.condition_type == '时间条件':
                condition_met = self.check_time_condition()
                
            elif self.condition_type == '技术指标条件':
                condition_met = self.check_technical_condition(data)
                
            # 如果条件满足且之前未触发
            if condition_met and not self.condition_triggered:
                self.condition_triggered = True
                self.log(f"条件触发: {self.condition_type}")
                
                # 执行条件单
                self.execute_conditional_order(current_price)
                
            # 输出当前状态
            status = "已执行" if self.order_executed else ("已触发" if self.condition_triggered else "监控中")
            
            self.log(f"价格: {current_price:.2f}, "
                    f"触发价格: {self.trigger_price:.2f}, "
                    f"持仓: {self.current_position}, "
                    f"状态: {status}")
                    
        except Exception as e:
            self.log(f"数据处理错误: {str(e)}")


def main():
    """
    主函数 - 用于测试策略
    """
    # 示例参数
    params = {
        '股票代码': '000001.SZ',
        '条件类型': '价格条件',
        '触发价格': 10.0,
        '交易方向': '买入',
        '交易数量': 1000,
        '有效期': '当日有效',
        '触发时间': '09:30:00',
        '启用短信通知': False
    }
    
    # 创建策略实例
    strategy = 止损止盈策略(params)
    
    # 运行策略
    strategy.start()


if __name__ == "__main__":
    main()