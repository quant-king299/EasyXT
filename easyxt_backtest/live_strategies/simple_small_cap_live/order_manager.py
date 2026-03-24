# -*- coding: utf-8 -*-
"""
订单管理模块

提供订单执行和管理功能。
"""

from typing import List, Dict
from datetime import datetime


class OrderManager:
    """
    订单管理器

    功能：
    1. 创建订单
    2. 执行订单
    3. 跟踪订单状态
    4. 记录交易历史
    """

    def __init__(self, trader):
        """
        初始化订单管理器

        Args:
            trader: QMT交易接口实例
        """
        self.trader = trader
        self.order_history = []
        self.current_orders = {}

    def create_order(self, symbol: str, direction: str, volume: int, price: float = None):
        """
        创建订单

        Args:
            symbol: 股票代码
            direction: 方向 ('buy'/'sell')
            volume: 数量
            price: 价格 (None=市价单)
        """
        order = {
            'symbol': symbol,
            'direction': direction,
            'volume': volume,
            'price': price,
            'status': 'pending',
            'created_at': datetime.now()
        }

        order_id = f"{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.current_orders[order_id] = order

        return order_id

    def execute_order(self, order_id: str):
        """
        执行订单

        Args:
            order_id: 订单ID
        """
        order = self.current_orders.get(order_id)
        if not order:
            print(f"订单不存在: {order_id}")
            return False

        try:
            # 调用QMT交易接口
            if order['direction'] == 'buy':
                result = self.trader.order_buy(
                    stock_code=order['symbol'],
                    order_type=0,  # 限价单
                    price=order['price'],
                    volume=order['volume']
                )
            else:
                result = self.trader.order_sell(
                    stock_code=order['symbol'],
                    order_type=0,
                    price=order['price'],
                    volume=order['volume']
                )

            order['status'] = 'filled'
            order['filled_at'] = datetime.now()
            self.order_history.append(order)

            return True

        except Exception as e:
            print(f"执行订单失败: {e}")
            order['status'] = 'failed'
            return False

    def cancel_order(self, order_id: str):
        """
        取消订单

        Args:
            order_id: 订单ID
        """
        if order_id in self.current_orders:
            self.current_orders[order_id]['status'] = 'cancelled'
            return True
        return False

    def get_positions(self) -> Dict[str, int]:
        """
        获取当前持仓

        Returns:
            持仓字典 {symbol: volume}
        """
        positions = {}

        try:
            # 从QMT获取持仓
            pos = self.trader.query_stock_positions()
            for p in pos:
                positions[p['stock_code']] = p['volume']
        except Exception as e:
            print(f"获取持仓失败: {e}")

        return positions

    def get_account_info(self) -> Dict:
        """
        获取账户信息

        Returns:
            账户信息字典
        """
        try:
            account = self.trader.query_stock_account()
            return {{
                'cash': account.get('cash', 0),
                'market_value': account.get('market_value', 0),
                'total_asset': account.get('total_asset', 0)
            }}
        except Exception as e:
            print(f"获取账户信息失败: {e}")
            return {}
