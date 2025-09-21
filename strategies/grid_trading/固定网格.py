#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
固定网格策略 - 网格交易策略
在固定价格区间内设置网格，低买高卖
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


class 固定网格策略(BaseStrategy):
    """
    固定网格策略类
    在基准价格上下设置固定间距的网格，低买高卖
    """
    
    def __init__(self, params=None):
        """
        初始化固定网格策略
        
        参数说明:
        - 股票代码: 交易的股票代码
        - 网格数量: 网格层数
        - 网格间距: 网格间距比例
        - 基准价格: 网格基准价格
        - 单网格数量: 单个网格交易数量
        - 最大持仓: 最大持仓数量
        - 启用动态调整: 是否启用动态网格调整
        """
        super().__init__(params)
        
        # 策略参数
        self.stock_code = self.params.get('股票代码', '000001.SZ')
        self.grid_count = self.params.get('网格数量', 10)
        self.grid_spacing = self.params.get('网格间距', 0.02)  # 2%
        self.base_price = self.params.get('基准价格', 10.0)
        self.grid_quantity = self.params.get('单网格数量', 100)
        self.max_position = self.params.get('最大持仓', 10000)
        self.enable_dynamic = self.params.get('启用动态调整', False)
        
        # 网格状态
        self.grid_levels = []
        self.grid_orders = {}
        self.current_position = 0
        
    def initialize(self):
        """
        策略初始化
        """
        self.log("初始化固定网格策略")
        self.log(f"股票代码: {self.stock_code}")
        self.log(f"网格数量: {self.grid_count}")
        self.log(f"网格间距: {self.grid_spacing*100:.1f}%")
        self.log(f"基准价格: {self.base_price:.2f}")
        self.log(f"单网格数量: {self.grid_quantity}股")
        self.log(f"最大持仓: {self.max_position}股")
        
        # 初始化网格
        self.setup_grid()
        
    def setup_grid(self):
        """
        设置网格
        """
        self.grid_levels = []
        
        # 计算网格价格
        for i in range(-self.grid_count//2, self.grid_count//2 + 1):
            if i == 0:
                continue  # 跳过基准价格
                
            grid_price = self.base_price * (1 + i * self.grid_spacing)
            self.grid_levels.append({
                'level': i,
                'price': grid_price,
                'type': 'buy' if i < 0 else 'sell',
                'quantity': self.grid_quantity,
                'filled': False
            })
            
        # 按价格排序
        self.grid_levels.sort(key=lambda x: x['price'])
        
        self.log("网格设置完成:")
        for grid in self.grid_levels:
            self.log(f"  Level {grid['level']:2d}: {grid['type']:4s} "
                    f"{grid['quantity']:4d}股 @{grid['price']:7.2f}")
                    
    def find_triggered_grids(self, current_price):
        """
        查找触发的网格
        
        Args:
            current_price: 当前价格
            
        Returns:
            触发的网格列表
        """
        triggered = []
        
        for grid in self.grid_levels:
            if grid['filled']:
                continue
                
            # 买入网格：价格跌破网格价格
            if (grid['type'] == 'buy' and 
                current_price <= grid['price'] and
                self.current_position < self.max_position):
                triggered.append(grid)
                
            # 卖出网格：价格突破网格价格
            elif (grid['type'] == 'sell' and 
                  current_price >= grid['price'] and
                  self.current_position > 0):
                triggered.append(grid)
                
        return triggered
        
    def execute_grid_order(self, grid, current_price):
        """
        执行网格订单
        
        Args:
            grid: 网格信息
            current_price: 当前价格
        """
        try:
            if grid['type'] == 'buy':
                # 买入
                result = self.buy(self.stock_code, grid['quantity'], grid['price'])
                if result:
                    self.current_position += grid['quantity']
                    grid['filled'] = True
                    self.log(f"网格买入成功: Level {grid['level']} "
                            f"{grid['quantity']}股 @{grid['price']:.2f}")
                    
            elif grid['type'] == 'sell':
                # 卖出
                sell_quantity = min(grid['quantity'], self.current_position)
                result = self.sell(self.stock_code, sell_quantity, grid['price'])
                if result:
                    self.current_position -= sell_quantity
                    grid['filled'] = True
                    self.log(f"网格卖出成功: Level {grid['level']} "
                            f"{sell_quantity}股 @{grid['price']:.2f}")
                    
        except Exception as e:
            self.log(f"执行网格订单失败: {str(e)}")
            
    def reset_filled_grids(self, current_price):
        """
        重置已成交的网格
        
        Args:
            current_price: 当前价格
        """
        for grid in self.grid_levels:
            if not grid['filled']:
                continue
                
            # 买入网格成交后，如果价格重新上涨，重置网格
            if (grid['type'] == 'buy' and 
                current_price > grid['price'] * (1 + self.grid_spacing * 0.5)):
                grid['filled'] = False
                self.log(f"重置买入网格: Level {grid['level']}")
                
            # 卖出网格成交后，如果价格重新下跌，重置网格
            elif (grid['type'] == 'sell' and 
                  current_price < grid['price'] * (1 - self.grid_spacing * 0.5)):
                grid['filled'] = False
                self.log(f"重置卖出网格: Level {grid['level']}")
                
    def on_data(self, data):
        """
        数据处理函数
        
        Args:
            data: 市场数据
        """
        try:
            current_price = data['close'].iloc[-1]
            
            # 查找触发的网格
            triggered_grids = self.find_triggered_grids(current_price)
            
            # 执行触发的网格订单
            for grid in triggered_grids:
                self.execute_grid_order(grid, current_price)
                
            # 重置已成交的网格
            if self.enable_dynamic:
                self.reset_filled_grids(current_price)
                
            # 输出当前状态
            filled_buy_grids = len([g for g in self.grid_levels 
                                  if g['type'] == 'buy' and g['filled']])
            filled_sell_grids = len([g for g in self.grid_levels 
                                   if g['type'] == 'sell' and g['filled']])
            
            self.log(f"价格: {current_price:.2f}, "
                    f"持仓: {self.current_position}, "
                    f"已买入网格: {filled_buy_grids}, "
                    f"已卖出网格: {filled_sell_grids}")
                    
            # 动态调整基准价格
            if self.enable_dynamic:
                price_deviation = abs(current_price - self.base_price) / self.base_price
                if price_deviation > self.grid_spacing * self.grid_count * 0.5:
                    self.log(f"价格偏离过大，重新设置网格")
                    self.base_price = current_price
                    self.setup_grid()
                    
        except Exception as e:
            self.log(f"数据处理错误: {str(e)}")


def main():
    """
    主函数 - 用于测试策略
    """
    # 示例参数
    params = {
        '股票代码': '000001.SZ',
        '网格数量': 10,
        '网格间距': 0.02,
        '基准价格': 10.0,
        '单网格数量': 100,
        '最大持仓': 10000,
        '启用动态调整': False
    }
    
    # 创建策略实例
    strategy = 固定网格策略(params)
    
    # 运行策略
    strategy.start()


if __name__ == "__main__":
    main()