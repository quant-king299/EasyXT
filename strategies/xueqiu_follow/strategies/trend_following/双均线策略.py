#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双均线策略 - 趋势跟踪策略
基于短期和长期移动平均线的交叉信号进行交易
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from strategies.base.strategy_template import BaseStrategy
import easy_xt


class 双均线策略(BaseStrategy):
    """
    双均线策略类
    当短期均线上穿长期均线时买入，下穿时卖出
    """
    
    def __init__(self, params=None):
        """
        初始化双均线策略
        
        参数说明:
        - 股票代码: 交易的股票代码
        - 短期均线: 短期移动平均线周期
        - 长期均线: 长期移动平均线周期
        - 交易数量: 每次交易的股数
        - 止损比例: 止损比例
        - 止盈比例: 止盈比例
        - 启用止损: 是否启用止损
        - 启用止盈: 是否启用止盈
        """
        super().__init__(params)
        
        # 策略参数
        self.stock_code = self.params.get('股票代码', '000001.SZ')
        self.short_period = self.params.get('短期均线', 5)
        self.long_period = self.params.get('长期均线', 20)
        self.trade_quantity = self.params.get('交易数量', 1000)
        self.stop_loss_ratio = self.params.get('止损比例', 0.05)
        self.stop_profit_ratio = self.params.get('止盈比例', 0.1)
        self.enable_stop_loss = self.params.get('启用止损', True)
        self.enable_stop_profit = self.params.get('启用止盈', True)
        
        # 策略状态
        self.last_signal = None
        self.entry_price = None
        self.position_size = 0
        
    def initialize(self):
        """
        策略初始化
        """
        self.log("初始化双均线策略")
        self.log(f"股票代码: {self.stock_code}")
        self.log(f"短期均线: {self.short_period}日")
        self.log(f"长期均线: {self.long_period}日")
        self.log(f"交易数量: {self.trade_quantity}股")
        self.log(f"止损比例: {self.stop_loss_ratio*100:.1f}%")
        self.log(f"止盈比例: {self.stop_profit_ratio*100:.1f}%")
        
    def calculate_ma(self, data, period):
        """
        计算移动平均线
        
        Args:
            data: 价格数据
            period: 周期
            
        Returns:
            移动平均线数据
        """
        return data['close'].rolling(window=period).mean()
        
    def generate_signal(self, data):
        """
        生成交易信号
        
        Args:
            data: 市场数据
            
        Returns:
            交易信号: 'buy', 'sell', 'hold'
        """
        if len(data) < self.long_period:
            return 'hold'
            
        # 计算移动平均线
        short_ma = self.calculate_ma(data, self.short_period)
        long_ma = self.calculate_ma(data, self.long_period)
        
        # 获取最新的均线值
        current_short_ma = short_ma.iloc[-1]
        current_long_ma = long_ma.iloc[-1]
        prev_short_ma = short_ma.iloc[-2]
        prev_long_ma = long_ma.iloc[-2]
        
        # 判断交叉信号
        if (prev_short_ma <= prev_long_ma and 
            current_short_ma > current_long_ma):
            return 'buy'  # 金叉买入
        elif (prev_short_ma >= prev_long_ma and 
              current_short_ma < current_long_ma):
            return 'sell'  # 死叉卖出
        else:
            return 'hold'
            
    def check_stop_conditions(self, current_price):
        """
        检查止损止盈条件
        
        Args:
            current_price: 当前价格
            
        Returns:
            是否需要平仓
        """
        if self.entry_price is None or self.position_size == 0:
            return False
            
        # 计算盈亏比例
        if self.position_size > 0:  # 多头持仓
            profit_ratio = (current_price - self.entry_price) / self.entry_price
        else:  # 空头持仓
            profit_ratio = (self.entry_price - current_price) / self.entry_price
            
        # 检查止损
        if self.enable_stop_loss and profit_ratio <= -self.stop_loss_ratio:
            self.log(f"触发止损: 亏损{profit_ratio*100:.2f}%")
            return True
            
        # 检查止盈
        if self.enable_stop_profit and profit_ratio >= self.stop_profit_ratio:
            self.log(f"触发止盈: 盈利{profit_ratio*100:.2f}%")
            return True
            
        return False
        
    def on_data(self, data):
        """
        数据处理函数
        
        Args:
            data: 市场数据
        """
        try:
            current_price = data['close'].iloc[-1]
            
            # 检查止损止盈
            if self.check_stop_conditions(current_price):
                if self.position_size > 0:
                    self.sell(self.stock_code, abs(self.position_size))
                elif self.position_size < 0:
                    self.buy(self.stock_code, abs(self.position_size))
                    
                self.position_size = 0
                self.entry_price = None
                return
                
            # 生成交易信号
            signal = self.generate_signal(data)
            
            if signal != self.last_signal:
                self.log(f"信号变化: {self.last_signal} -> {signal}")
                
                if signal == 'buy' and self.position_size <= 0:
                    # 买入信号
                    if self.position_size < 0:
                        # 先平空头
                        self.buy(self.stock_code, abs(self.position_size))
                        
                    # 开多头
                    result = self.buy(self.stock_code, self.trade_quantity)
                    if result:
                        self.position_size = self.trade_quantity
                        self.entry_price = current_price
                        self.log(f"买入成功: {self.trade_quantity}股 @{current_price:.2f}")
                        
                elif signal == 'sell' and self.position_size >= 0:
                    # 卖出信号
                    if self.position_size > 0:
                        # 先平多头
                        self.sell(self.stock_code, self.position_size)
                        
                    # 开空头（如果支持）
                    # result = self.sell(self.stock_code, self.trade_quantity)
                    # if result:
                    #     self.position_size = -self.trade_quantity
                    #     self.entry_price = current_price
                    #     self.log(f"卖出成功: {self.trade_quantity}股 @{current_price:.2f}")
                    
                    self.position_size = 0
                    self.entry_price = None
                    self.log(f"平仓成功 @{current_price:.2f}")
                    
                self.last_signal = signal
                
            # 输出当前状态
            if len(data) >= self.long_period:
                short_ma = self.calculate_ma(data, self.short_period).iloc[-1]
                long_ma = self.calculate_ma(data, self.long_period).iloc[-1]
                
                self.log(f"价格: {current_price:.2f}, "
                        f"短期均线: {short_ma:.2f}, "
                        f"长期均线: {long_ma:.2f}, "
                        f"持仓: {self.position_size}, "
                        f"信号: {signal}")
                        
        except Exception as e:
            self.log(f"数据处理错误: {str(e)}")


def main():
    """
    主函数 - 用于测试策略
    """
    # 示例参数
    params = {
        '股票代码': '000001.SZ',
        '短期均线': 5,
        '长期均线': 20,
        '交易数量': 1000,
        '止损比例': 0.05,
        '止盈比例': 0.1,
        '启用止损': True,
        '启用止盈': True
    }
    
    # 创建策略实例
    strategy = 双均线策略(params)
    
    # 运行策略
    strategy.start()


if __name__ == "__main__":
    main()