#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
订单转换器（easyxt -> qka/miniqmt 订单字段规范）
- 仅做转换，不直接执行下发；执行由策略或执行器调用适配层方法完成
"""
from typing import List, Dict, Any

class OrderConverter:
    """订单字段转换工具"""

    @staticmethod
    def target_positions_to_qka_orders(diff_result: Dict[str, List[Dict]], price_map: Dict[str, float],
                                       price_type: str = 'market') -> List[Dict[str, Any]]:
        """
        将持仓差异结果转换为 qka 订单列表
        Args:
            diff_result: PositionDiffer.compare_positions(...) 的结果
            price_map: 代码到价格的映射（若为限价单）
            price_type: 'market' 或 'limit'
        Returns:
            List[Dict]: qka 订单列表（示例字段）
                {
                  'code': '000001.XSHE',
                  'direction': 'BUY'/'SELL',
                  'order_type': 'MARKET'/'LIMIT',
                  'price': 12.35,  # 限价时必填
                  'volume': 1000
                }
        """
        orders: List[Dict[str, Any]] = []
        order_type = 'MARKET' if price_type == 'market' else 'LIMIT'

        def _make(code: str, direction: str, volume: int) -> Dict[str, Any]:
            order = {
                'code': code,
                'direction': direction,
                'order_type': order_type,
                'volume': int(volume)
            }
            if order_type == 'LIMIT':
                order['price'] = float(price_map.get(code, 0.0))
            return order

        # 需要买入的：全部生成 BUY 订单
        for pos in diff_result.get('to_buy', []):
            code = pos.get('code') or pos.get('symbol')
            volume = pos.get('volume') or pos.get('quantity')
            orders.append(_make(code, 'BUY', volume))

        # 需要卖出的：SELL 到 0
        for pos in diff_result.get('to_sell', []):
            code = pos.get('code') or pos.get('symbol')
            current_volume = pos.get('volume') or pos.get('quantity')
            orders.append(_make(code, 'SELL', current_volume))

        # 需要调整的：正数为 BUY，负数为 SELL
        for pos in diff_result.get('to_adjust', []):
            code = pos.get('code') or pos.get('symbol')
            adj = pos.get('adjust_quantity') or pos.get('adjust_volume')
            if adj is None:
                continue
            if adj > 0:
                orders.append(_make(code, 'BUY', adj))
            elif adj < 0:
                orders.append(_make(code, 'SELL', abs(adj)))

        return orders