"""
QKA经纪商模块

提供虚拟交易经纪商功能，管理资金、持仓和交易记录，支持回测环境下的交易操作。
"""

import pandas as pd
from typing import Dict, List, Any, Optional

class Broker:
    """
    虚拟交易经纪商类
    
    管理资金、持仓和交易记录，提供买入卖出操作接口。
    
    Attributes:
        cash (float): 可用现金
        positions (Dict): 持仓记录，格式: {symbol: {'size': 数量, 'avg_price': 平均成本}}
        trade_history (List): 交易历史记录
        timestamp: 当前时间戳
        trades (pd.DataFrame): 交易记录DataFrame
    """
    
    def __init__(self, initial_cash=100000.0):
        """
        初始化Broker类
        
        Args:
            initial_cash (float): 初始资金，默认10万元
        """
        self.cash = initial_cash  # 可用现金
        self.positions = {}       # 持仓记录，格式: {symbol: {'size': 数量, 'avg_price': 平均成本}}
        self.trade_history = []   # 交易历史记录
        self.timestamp = None     # 当前时间戳
        
        # 交易记录
        self.trades = pd.DataFrame(columns=[
            'cash', 'value', 'total',
            'positions', 'trades'
        ])
        
    def on_bar(self, date, get):
        """
        处理每个bar的数据，记录状态
        
        Args:
            date: 当前时间戳
            get: 获取因子数据的函数，格式为 get(factor_name) -> pd.Series
        """
        self.timestamp = date
        
        # 获取当前市场价格
        close_prices = get('close')
        market_prices = close_prices.to_dict() if hasattr(close_prices, 'to_dict') else {}
        
        # 记录状态到trades DataFrame
        if self.timestamp is None:
            return
            
        # 获取当日交易记录
        daily_trades = []
        for trade in self.trade_history:
            if trade['timestamp'] == self.timestamp:
                daily_trades.append(trade)
        
        # 计算持仓市值
        position_value = 0.0
        for symbol, position in self.positions.items():
            if market_prices and symbol in market_prices:
                # 使用市场价格计算市值
                position_value += position['size'] * market_prices[symbol]
            else:
                # 使用平均成本估算市值
                position_value += position['size'] * position['avg_price']
        
        # 计算总资产
        total_assets = self.cash + position_value
        
        # 记录状态
        state_data = {
            'cash': self.cash,
            'value': position_value,
            'total': total_assets,
            'positions': self.positions.copy(),
            'trades': daily_trades.copy()
        }
        
        # 添加到trades
        self.trades.loc[self.timestamp] = state_data
    
    def buy(self, symbol: str, price: float, size: int) -> bool:
        """
        买入操作
        
        Args:
            symbol (str): 交易标的代码
            price (float): 买入价格
            size (int): 买入数量
            
        Returns:
            bool: 交易是否成功
        """
        # 计算买入所需金额
        required_cash = price * size
        
        # 检查资金是否足够
        if self.cash < required_cash:
            print(f"资金不足！需要 {required_cash:.2f}，当前可用 {self.cash:.2f}")
            return False
        
        # 执行买入操作
        self.cash -= required_cash
        
        # 更新持仓
        if symbol in self.positions:
            # 已有持仓，计算新的平均成本
            old_position = self.positions[symbol]
            old_size = old_position['size']
            old_avg_price = old_position['avg_price']
            old_total_value = old_size * old_avg_price
            new_total_value = old_total_value + required_cash
            new_size = old_size + size
            new_avg_price = new_total_value / new_size
            
            self.positions[symbol] = {
                'size': new_size,
                'avg_price': new_avg_price
            }
        else:
            # 新建持仓
            self.positions[symbol] = {
                'size': size,
                'avg_price': price
            }
        
        # 记录交易历史
        self.trade_history.append({
            'action': 'buy',
            'symbol': symbol,
            'price': price,
            'size': size,
            'timestamp': self.timestamp
        })
        
        print(f"买入成功: {symbol} {size}股 @ {price:.2f}，花费 {required_cash:.2f}")
        return True
    
    def sell(self, symbol: str, price: float, size: int) -> bool:
        """
        卖出操作
        
        Args:
            symbol (str): 交易标的代码
            price (float): 卖出价格
            size (int): 卖出数量
            
        Returns:
            bool: 交易是否成功
        """
        # 检查是否有足够的持仓
        if symbol not in self.positions:
            print(f"没有 {symbol} 的持仓！")
            return False
        
        position = self.positions[symbol]
        if position['size'] < size:
            print(f"持仓不足！当前持有 {position['size']}，尝试卖出 {size}")
            return False
        
        # 计算卖出所得金额
        sale_proceeds = price * size
        
        # 执行卖出操作
        self.cash += sale_proceeds
        
        # 更新持仓
        if position['size'] == size:
            # 全部卖出，删除持仓记录
            del self.positions[symbol]
        else:
            # 部分卖出，更新持仓数量
            self.positions[symbol]['size'] -= size
        
        # 记录交易历史
        self.trade_history.append({
            'action': 'sell',
            'symbol': symbol,
            'price': price,
            'size': size,
            'timestamp': self.timestamp
        })
        
        print(f"卖出成功: {symbol} {size}股 @ {price:.2f}，获得 {sale_proceeds:.2f}")
        return True
    
    def get(self, factor: str, timestamp=None) -> Any:
        """
        从trades DataFrame中获取数据
        
        Args:
            factor (str): 列名，可选 'cash', 'value', 'total', 'positions', 'trades'
            timestamp: 时间戳，如果为None则使用当前时间戳
            
        Returns:
            Any: 对应列的数据，如果不存在则返回None
        """
        if timestamp is None:
            timestamp = self.timestamp
        
        if timestamp is None or timestamp not in self.trades.index:
            return None
            
        return self.trades.at[timestamp, factor]
    
    
