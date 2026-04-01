# -*- coding: utf-8 -*-
"""
目标仓位管理器

参考vnpy的设计，实现简洁高效的目标仓位管理。
"""
from typing import Dict, List, Optional
from datetime import datetime


class PositionManager:
    """
    仓位管理器

    功能：
    1. 跟踪当前持仓
    2. 管理目标仓位
    3. 自动计算调仓指令
    4. 执行交易
    """

    def __init__(self, initial_cash: float = 1000000):
        """
        初始化

        Args:
            initial_cash: 初始资金
        """
        self.initial_cash = initial_cash
        self.cash = initial_cash

        # 当前持仓 {symbol: volume}
        self.positions: Dict[str, float] = {}

        # 目标持仓 {symbol: volume}
        self.target_positions: Dict[str, float] = {}

        # 持仓成本价 {symbol: avg_price}
        self.cost_prices: Dict[str, float] = {}

        # 当前市值 {symbol: market_value}
        self.market_values: Dict[str, float] = {}

    def get_position(self, symbol: str) -> float:
        """获取当前持仓"""
        return self.positions.get(symbol, 0.0)

    def get_target_position(self, symbol: str) -> float:
        """获取目标持仓"""
        return self.target_positions.get(symbol, 0.0)

    def set_target_position(self, symbol: str, target_volume: float) -> None:
        """
        设置目标持仓（数量）

        Args:
            symbol: 股票代码
            target_volume: 目标持仓数量
        """
        self.target_positions[symbol] = target_volume

    def set_target_weights(self, target_weights: Dict[str, float],
                         total_value: float,
                         current_prices: Dict[str, float]) -> None:
        """
        设置目标权重

        Args:
            target_weights: 目标权重字典 {symbol: weight}
            total_value: 总资产
            current_prices: 当前价格字典 {symbol: price}
        """
        self.target_positions.clear()

        for symbol, weight in target_weights.items():
            if symbol not in current_prices:
                continue

            price = current_prices[symbol]
            target_value = total_value * weight
            target_volume = target_value / price

            self.target_positions[symbol] = target_volume

    def update_market_value(self, symbol: str, price: float) -> None:
        """更新市值"""
        position = self.get_position(symbol)
        self.market_values[symbol] = position * price

    def get_total_value(self) -> float:
        """获取总资产"""
        holding_value = sum(self.market_values.values())
        return self.cash + holding_value

    def get_holding_value(self) -> float:
        """获取持仓市值"""
        return sum(self.market_values.values())

    def calculate_rebalance_orders(self,
                                  current_prices: Dict[str, float],
                                  price_tolerance: float = 0.001) -> List[Dict]:
        """
        计算调仓指令（参考vnpy execute_trading设计）

        与vnpy一致：直接计算 target - pos 的差异，全部执行。
        只对非清仓的微调方向添加容差，清仓操作（target=0）必须执行。

        Args:
            current_prices: 当前价格字典
            price_tolerance: 价格容差（默认0.1%）

        Returns:
            调仓指令列表
        """
        orders = []

        # 收集所有需要交易的股票
        all_symbols = set(list(self.positions.keys()) +
                         list(self.target_positions.keys()))

        for symbol in all_symbols:
            if symbol not in current_prices:
                continue

            current_pos = self.get_position(symbol)
            target_pos = self.get_target_position(symbol)
            diff = target_pos - current_pos

            # vnpy风格：直接根据diff方向执行，无容差过滤
            # 唯一例外：非清仓操作的极微小调整可跳过（避免频繁交易手续费吃利润）
            if diff > 0:
                # 买入（如果不是从0开始建仓，且金额极小，可跳过）
                trade_value = diff * current_prices[symbol]
                if target_pos > 0 and current_pos > 0 and trade_value < 500:
                    continue
                price = current_prices[symbol] * (1 + price_tolerance)
                orders.append({
                    'symbol': symbol,
                    'action': 'buy',
                    'volume': diff,
                    'price': price
                })
            elif diff < 0:
                # 卖出：如果目标为0（清仓），必须全部卖出，不管金额多小
                sell_volume = abs(diff)
                price = current_prices[symbol] * (1 - price_tolerance)
                orders.append({
                    'symbol': symbol,
                    'action': 'sell',
                    'volume': sell_volume,
                    'price': price
                })

        # 先卖后买：卖出订单排前面（释放资金用于买入）
        sell_orders = [o for o in orders if o['action'] == 'sell']
        buy_orders = [o for o in orders if o['action'] == 'buy']

        # 卖出按金额从大到小
        for order in sell_orders:
            order['value'] = order['volume'] * order['price']
        sell_orders.sort(key=lambda x: x['value'], reverse=True)

        # 买入按金额从大到小
        for order in buy_orders:
            order['value'] = order['volume'] * order['price']
        buy_orders.sort(key=lambda x: x['value'], reverse=True)

        return sell_orders + buy_orders

    def execute_order(self, order: Dict) -> None:
        """
        执行订单（更新持仓和现金）

        Args:
            order: 订单字典
        """
        symbol = order['symbol']
        action = order['action']
        volume = order['volume']
        price = order['price']

        turnover = volume * price
        commission = turnover * 0.0003  # 万三佣金

        if action == 'buy':
            # 买入
            self.positions[symbol] = self.get_position(symbol) + volume
            self.cash -= (turnover + commission)

            # 更新成本价（简单加权平均）
            old_cost = self.cost_prices.get(symbol, 0)
            old_volume = self.get_position(symbol) - volume
            if old_volume > 0:
                new_cost = (old_cost * old_volume + price * volume) / (old_volume + volume)
            else:
                new_cost = price
            self.cost_prices[symbol] = new_cost

        else:  # 'sell'
            # 卖出
            self.positions[symbol] = self.get_position(symbol) - volume
            self.cash += (turnover - commission)

            # 清空成本价（如果仓位为0）
            if self.get_position(symbol) == 0:
                if symbol in self.cost_prices:
                    del self.cost_prices[symbol]

    def execute_rebalance(self, current_prices: Dict[str, float],
                        price_tolerance: float = 0.001) -> List[Dict]:
        """
        执行调仓（计算并执行订单）

        参考vnpy：先卖后买，释放资金后再买入。

        Args:
            current_prices: 当前价格
            price_tolerance: 价格容差

        Returns:
            执行的订单列表
        """
        # 1. 计算调仓指令（已按先卖后买排序）
        orders = self.calculate_rebalance_orders(current_prices, price_tolerance)

        # 2. 执行订单
        executed_orders = []
        for order in orders:
            if order['action'] == 'buy':
                # 买入时检查资金
                required_cash = order['volume'] * order['price'] * 1.001
                if required_cash > self.cash:
                    # 资金不足，调整为可买的整手（100股）数量
                    max_volume = int(self.cash / (order['price'] * 1.001) / 100) * 100
                    if max_volume <= 0:
                        continue  # 完全买不起，跳过
                    order['volume'] = max_volume

            # 执行订单
            self.execute_order(order)
            executed_orders.append(order)

        # 3. 清理残余仓位（参考vnpy，不保留微小的残余持仓）
        symbols_to_clean = [
            s for s, v in self.positions.items()
            if v <= 1 or (s in current_prices and v * current_prices[s] < 100)
        ]
        for symbol in symbols_to_clean:
            if symbol in self.positions:
                del self.positions[symbol]
            if symbol in self.cost_prices:
                del self.cost_prices[symbol]
            if symbol in self.market_values:
                del self.market_values[symbol]

        # 4. 更新市值
        for symbol in self.positions.keys():
            if symbol in current_prices:
                self.update_market_value(symbol, current_prices[symbol])

        return executed_orders

    def get_portfolio_summary(self) -> Dict:
        """获取组合摘要"""
        total_value = self.get_total_value()
        holding_value = self.get_holding_value()

        positions_list = []
        for symbol, volume in self.positions.items():
            if volume == 0:
                continue
            market_value = self.market_values.get(symbol, 0)
            weight = market_value / total_value if total_value > 0 else 0
            cost_price = self.cost_prices.get(symbol, 0)
            current_price = market_value / volume if volume > 0 else 0

            positions_list.append({
                'symbol': symbol,
                'volume': volume,
                'cost_price': cost_price,
                'current_price': current_price,
                'market_value': market_value,
                'weight': weight,
                'pnl': (current_price - cost_price) * volume if cost_price > 0 else 0,
                'pnl_pct': ((current_price / cost_price) - 1) * 100 if cost_price > 0 else 0
            })

        return {
            'cash': self.cash,
            'holding_value': holding_value,
            'total_value': total_value,
            'positions': positions_list,
            'position_count': len(positions_list)
        }

    def clear_target_positions(self) -> None:
        """清空目标持仓"""
        self.target_positions.clear()

    def get_current_weights(self, total_value: Optional[float] = None) -> Dict[str, float]:
        """
        获取当前权重

        Args:
            total_value: 总资产（如果为None则自动计算）

        Returns:
            权重字典 {symbol: weight}
        """
        if total_value is None:
            total_value = self.get_total_value()

        if total_value == 0:
            return {}

        weights = {}
        for symbol, market_value in self.market_values.items():
            weights[symbol] = market_value / total_value

        return weights
