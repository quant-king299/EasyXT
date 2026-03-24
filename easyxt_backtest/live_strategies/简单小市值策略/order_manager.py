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

        if self.trader is None:
            print("[INFO] 未连接QMT，返回空持仓")
            return positions

        try:
            # 从QMT获取持仓
            pos = self.trader.query_stock_positions()
            if pos:
                for p in pos:
                    positions[p.stock_code] = p.volume
                print(f"[OK] 获取持仓: {len(positions)} 只股票")
            else:
                print("[INFO] 当前无持仓")
        except Exception as e:
            print(f"[WARN] 获取持仓失败: {e}")

        return positions

    def get_account_info(self) -> Dict:
        """
        获取账户信息

        Returns:
            账户信息字典
        """
        try:
            account = self.trader.query_stock_account()
            return {
                'cash': account.get('cash', 0),
                'market_value': account.get('market_value', 0),
                'total_asset': account.get('total_asset', 0)
            }
        except Exception as e:
            print(f"获取账户信息失败: {e}")
            return {}

    def generate_orders(self, current_positions: Dict[str, int], target_portfolio: Dict[str, float]) -> List[Dict]:
        """
        生成调仓订单

        Args:
            current_positions: 当前持仓 {symbol: volume}
            target_portfolio: 目标组合 {symbol: weight}

        Returns:
            订单列表
        """
        orders = []

        # 获取账户信息
        account = self.get_account_info()
        total_asset = account.get('total_asset', 1000000)

        # 1. 卖出不在目标组合中的股票
        for symbol, volume in current_positions.items():
            if symbol not in target_portfolio:
                orders.append({
                    'symbol': symbol,
                    'direction': 'sell',
                    'volume': volume,
                    'reason': '不在目标组合中'
                })

        # 2. 买入目标组合中的股票
        for symbol, weight in target_portfolio.items():
            target_value = total_asset * weight
            current_value = 0

            if symbol in current_positions:
                # TODO: 获取当前市值
                pass

            # 计算需要买入的金额
            buy_value = target_value - current_value
            if buy_value > 1000:  # 最小交易金额
                # TODO: 根据当前价格计算买入数量
                volume = int(buy_value / 100) * 100  # 简化：假设每股100元
                if volume > 0:
                    orders.append({
                        'symbol': symbol,
                        'direction': 'buy',
                        'volume': volume,
                        'reason': f'目标权重{weight:.2%}'
                    })

        return orders

    def execute_orders(self, orders: List[Dict]) -> List[Dict]:
        """
        执行订单列表

        Args:
            orders: 订单列表

        Returns:
            执行结果列表
        """
        results = []

        for order in orders:
            order_id = self.create_order(
                symbol=order['symbol'],
                direction=order['direction'],
                volume=order['volume']
            )

            success = self.execute_order(order_id)
            results.append({
                'order_id': order_id,
                'symbol': order['symbol'],
                'direction': order['direction'],
                'volume': order['volume'],
                'success': success
            })

        return results
