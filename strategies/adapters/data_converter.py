#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EasyXT与JQ2QMT数据格式转换器
处理不同系统间的数据格式转换
"""

from typing import List, Dict, Any
import re


class DataConverter:
    """数据格式转换器"""
    
    @staticmethod
    def easyxt_to_jq2qmt(easyxt_positions: List[Dict]) -> List[Dict]:
        """
        EasyXT持仓格式转JQ2QMT格式
        
        Args:
            easyxt_positions: EasyXT格式持仓列表
                [
                    {
                        'symbol': '000001.SZ',
                        'name': '平安银行',
                        'quantity': 1000,
                        'avg_price': 12.50,
                        'market_value': 12500.0,  # 可选
                        'pnl': 500.0  # 可选
                    }
                ]
        
        Returns:
            List[Dict]: JQ2QMT格式持仓列表
                [
                    {
                        'code': '000001.SZ',
                        'name': '平安银行',
                        'volume': 1000,
                        'cost': 12.50
                    }
                ]
        """
        jq2qmt_positions = []
        
        for pos in easyxt_positions:
            # 转换股票代码格式
            code = DataConverter._convert_symbol_to_jq_format(pos.get('symbol', ''))
            
            jq2qmt_pos = {
                'code': code,
                'name': pos.get('name', ''),
                'volume': int(pos.get('quantity', 0)),
                'cost': float(pos.get('avg_price', 0.0))
            }
            
            # 添加可选字段
            if 'market_value' in pos:
                jq2qmt_pos['market_value'] = float(pos['market_value'])
            
            if 'pnl' in pos:
                jq2qmt_pos['pnl'] = float(pos['pnl'])
            
            jq2qmt_positions.append(jq2qmt_pos)
        
        return jq2qmt_positions
    
    @staticmethod
    def jq2qmt_to_easyxt(jq2qmt_positions: List[Dict]) -> List[Dict]:
        """
        JQ2QMT持仓格式转EasyXT格式
        
        Args:
            jq2qmt_positions: JQ2QMT格式持仓列表
                [
                    {
                        'code': '000001.XSHE',
                        'name': '平安银行',
                        'volume': 1000,
                        'cost': 12.50
                    }
                ]
        
        Returns:
            List[Dict]: EasyXT格式持仓列表
        """
        easyxt_positions = []
        
        for pos in jq2qmt_positions:
            # 转换股票代码格式
            symbol = DataConverter._convert_jq_code_to_symbol(pos.get('code', ''))
            
            easyxt_pos = {
                'symbol': symbol,
                'name': pos.get('name', ''),
                'quantity': int(pos.get('volume', 0)),
                'avg_price': float(pos.get('cost', 0.0))
            }
            
            # 计算市值
            if easyxt_pos['quantity'] > 0 and easyxt_pos['avg_price'] > 0:
                easyxt_pos['market_value'] = easyxt_pos['quantity'] * easyxt_pos['avg_price']
            else:
                easyxt_pos['market_value'] = 0.0
            
            # 添加可选字段
            if 'market_value' in pos:
                easyxt_pos['market_value'] = float(pos['market_value'])
            
            if 'pnl' in pos:
                easyxt_pos['pnl'] = float(pos['pnl'])
            
            easyxt_positions.append(easyxt_pos)
        
        return easyxt_positions
    
    @staticmethod
    def jq2qmt_to_easyxt_total(jq2qmt_total_positions: List[Dict]) -> List[Dict]:
        """
        JQ2QMT总持仓格式转EasyXT格式
        
        Args:
            jq2qmt_total_positions: JQ2QMT总持仓格式
                [
                    {
                        'code': '000001.XSHE',
                        'name': '平安银行',
                        'total_volume': 1000,
                        'avg_cost': 12.50
                    }
                ]
        
        Returns:
            List[Dict]: EasyXT格式持仓列表
        """
        easyxt_positions = []
        
        for pos in jq2qmt_total_positions:
            # 转换股票代码格式
            symbol = DataConverter._convert_jq_code_to_symbol(pos.get('code', ''))
            
            easyxt_pos = {
                'symbol': symbol,
                'name': pos.get('name', ''),
                'quantity': int(pos.get('total_volume', 0)),
                'avg_price': float(pos.get('avg_cost', 0.0))
            }
            
            # 计算市值
            if easyxt_pos['quantity'] > 0 and easyxt_pos['avg_price'] > 0:
                easyxt_pos['market_value'] = easyxt_pos['quantity'] * easyxt_pos['avg_price']
            else:
                easyxt_pos['market_value'] = 0.0
            
            easyxt_positions.append(easyxt_pos)
        
        return easyxt_positions
    
    @staticmethod
    def _convert_symbol_to_jq_format(symbol: str) -> str:
        """
        将EasyXT股票代码转换为聚宽格式
        
        Args:
            symbol: EasyXT格式股票代码 (如: '000001.SZ', '600000.SH')
        
        Returns:
            str: 聚宽格式股票代码 (如: '000001.XSHE', '600000.XSHG')
        """
        if not symbol:
            return symbol
        
        # 处理深圳交易所
        if symbol.endswith('.SZ'):
            code = symbol.replace('.SZ', '.XSHE')
        # 处理上海交易所
        elif symbol.endswith('.SH'):
            code = symbol.replace('.SH', '.XSHG')
        # 处理北京交易所
        elif symbol.endswith('.BJ'):
            code = symbol.replace('.BJ', '.XBSE')
        # 已经是聚宽格式
        elif '.X' in symbol:
            code = symbol
        else:
            # 默认处理：根据代码前缀判断交易所
            if symbol.startswith(('000', '001', '002', '003', '300')):
                code = symbol + '.XSHE'  # 深圳
            elif symbol.startswith(('600', '601', '603', '605', '688')):
                code = symbol + '.XSHG'  # 上海
            elif symbol.startswith(('430', '831', '832', '833', '834', '835', '836', '837', '838', '839')):
                code = symbol + '.XBSE'  # 北京
            else:
                code = symbol  # 保持原样
        
        return code
    
    @staticmethod
    def _convert_jq_code_to_symbol(jq_code: str) -> str:
        """
        将聚宽格式股票代码转换为EasyXT格式
        
        Args:
            jq_code: 聚宽格式股票代码 (如: '000001.XSHE', '600000.XSHG')
        
        Returns:
            str: EasyXT格式股票代码 (如: '000001.SZ', '600000.SH')
        """
        if not jq_code:
            return jq_code
        
        # 处理深圳交易所
        if jq_code.endswith('.XSHE'):
            symbol = jq_code.replace('.XSHE', '.SZ')
        # 处理上海交易所
        elif jq_code.endswith('.XSHG'):
            symbol = jq_code.replace('.XSHG', '.SH')
        # 处理北京交易所
        elif jq_code.endswith('.XBSE'):
            symbol = jq_code.replace('.XBSE', '.BJ')
        # 已经是EasyXT格式
        elif jq_code.endswith(('.SZ', '.SH', '.BJ')):
            symbol = jq_code
        else:
            # 默认保持原样
            symbol = jq_code
        
        return symbol
    
    @staticmethod
    def validate_easyxt_position(position: Dict) -> bool:
        """
        验证EasyXT持仓数据格式
        
        Args:
            position: EasyXT持仓数据
        
        Returns:
            bool: 是否有效
        """
        required_fields = ['symbol', 'quantity', 'avg_price']
        
        # 检查必需字段
        for field in required_fields:
            if field not in position:
                return False
        
        # 检查数据类型
        try:
            quantity = int(position['quantity'])
            avg_price = float(position['avg_price'])
            
            # 检查数值合理性
            if quantity < 0:  # 允许负持仓（做空）
                pass
            if avg_price <= 0:
                return False
                
        except (ValueError, TypeError):
            return False
        
        # 检查股票代码格式
        symbol = position['symbol']
        if not isinstance(symbol, str) or len(symbol) < 6:
            return False
        
        return True
    
    @staticmethod
    def validate_jq2qmt_position(position: Dict) -> bool:
        """
        验证JQ2QMT持仓数据格式
        
        Args:
            position: JQ2QMT持仓数据
        
        Returns:
            bool: 是否有效
        """
        required_fields = ['code', 'volume', 'cost']
        
        # 检查必需字段
        for field in required_fields:
            if field not in position:
                return False
        
        # 检查数据类型
        try:
            volume = int(position['volume'])
            cost = float(position['cost'])
            
            # 检查数值合理性
            if volume < 0:  # 允许负持仓
                pass
            if cost <= 0:
                return False
                
        except (ValueError, TypeError):
            return False
        
        # 检查股票代码格式
        code = position['code']
        if not isinstance(code, str) or len(code) < 6:
            return False
        
        return True
    
    @staticmethod
    def normalize_positions(positions: List[Dict], format_type: str = 'easyxt') -> List[Dict]:
        """
        标准化持仓数据
        
        Args:
            positions: 持仓数据列表
            format_type: 格式类型 ('easyxt' 或 'jq2qmt')
        
        Returns:
            List[Dict]: 标准化后的持仓数据
        """
        normalized = []
        
        for pos in positions:
            if format_type == 'easyxt':
                if DataConverter.validate_easyxt_position(pos):
                    # 标准化数值
                    normalized_pos = {
                        'symbol': pos['symbol'].upper(),
                        'name': pos.get('name', ''),
                        'quantity': int(pos['quantity']),
                        'avg_price': round(float(pos['avg_price']), 3),
                        'market_value': round(int(pos['quantity']) * float(pos['avg_price']), 2)
                    }
                    
                    # 添加可选字段
                    if 'pnl' in pos:
                        normalized_pos['pnl'] = round(float(pos['pnl']), 2)
                    
                    normalized.append(normalized_pos)
            
            elif format_type == 'jq2qmt':
                if DataConverter.validate_jq2qmt_position(pos):
                    # 标准化数值
                    normalized_pos = {
                        'code': pos['code'].upper(),
                        'name': pos.get('name', ''),
                        'volume': int(pos['volume']),
                        'cost': round(float(pos['cost']), 3)
                    }
                    
                    # 添加可选字段
                    if 'market_value' in pos:
                        normalized_pos['market_value'] = round(float(pos['market_value']), 2)
                    
                    if 'pnl' in pos:
                        normalized_pos['pnl'] = round(float(pos['pnl']), 2)
                    
                    normalized.append(normalized_pos)
        
        return normalized
    
    @staticmethod
    def merge_positions(positions_list: List[List[Dict]], format_type: str = 'easyxt') -> List[Dict]:
        """
        合并多个持仓列表
        
        Args:
            positions_list: 多个持仓列表
            format_type: 格式类型 ('easyxt' 或 'jq2qmt')
        
        Returns:
            List[Dict]: 合并后的持仓列表
        """
        merged = {}
        
        for positions in positions_list:
            for pos in positions:
                if format_type == 'easyxt':
                    key = pos['symbol']
                    if key in merged:
                        # 合并持仓
                        merged[key]['quantity'] += pos['quantity']
                        # 重新计算平均成本
                        total_cost = (merged[key]['avg_price'] * (merged[key]['quantity'] - pos['quantity']) + 
                                    pos['avg_price'] * pos['quantity'])
                        merged[key]['avg_price'] = total_cost / merged[key]['quantity'] if merged[key]['quantity'] != 0 else 0
                        merged[key]['market_value'] = merged[key]['quantity'] * merged[key]['avg_price']
                    else:
                        merged[key] = pos.copy()
                
                elif format_type == 'jq2qmt':
                    key = pos['code']
                    if key in merged:
                        # 合并持仓
                        merged[key]['volume'] += pos['volume']
                        # 重新计算平均成本
                        total_cost = (merged[key]['cost'] * (merged[key]['volume'] - pos['volume']) + 
                                    pos['cost'] * pos['volume'])
                        merged[key]['cost'] = total_cost / merged[key]['volume'] if merged[key]['volume'] != 0 else 0
                    else:
                        merged[key] = pos.copy()
        
        # 过滤掉持仓为0的股票
        result = []
        for pos in merged.values():
            if format_type == 'easyxt' and pos['quantity'] != 0:
                result.append(pos)
            elif format_type == 'jq2qmt' and pos['volume'] != 0:
                result.append(pos)
        
        return result


class PositionDiffer:
    """持仓差异分析器"""
    
    @staticmethod
    def compare_positions(current_positions: List[Dict], target_positions: List[Dict], 
                         format_type: str = 'easyxt') -> Dict[str, List[Dict]]:
        """
        比较当前持仓与目标持仓的差异
        
        Args:
            current_positions: 当前持仓
            target_positions: 目标持仓
            format_type: 格式类型
        
        Returns:
            Dict: 差异分析结果
                {
                    'to_buy': [...],    # 需要买入的股票
                    'to_sell': [...],   # 需要卖出的股票
                    'to_adjust': [...], # 需要调整的股票
                    'unchanged': [...]  # 无需变动的股票
                }
        """
        if format_type == 'easyxt':
            symbol_key = 'symbol'
            quantity_key = 'quantity'
        else:
            symbol_key = 'code'
            quantity_key = 'volume'
        
        # 转换为字典格式便于查找
        current_dict = {pos[symbol_key]: pos for pos in current_positions}
        target_dict = {pos[symbol_key]: pos for pos in target_positions}
        
        result = {
            'to_buy': [],
            'to_sell': [],
            'to_adjust': [],
            'unchanged': []
        }
        
        # 分析目标持仓
        for symbol, target_pos in target_dict.items():
            if symbol not in current_dict:
                # 新买入
                result['to_buy'].append(target_pos)
            else:
                current_pos = current_dict[symbol]
                current_qty = current_pos[quantity_key]
                target_qty = target_pos[quantity_key]
                
                if current_qty == target_qty:
                    # 无需变动
                    result['unchanged'].append(target_pos)
                else:
                    # 需要调整
                    adjust_pos = target_pos.copy()
                    adjust_pos['adjust_quantity'] = target_qty - current_qty
                    result['to_adjust'].append(adjust_pos)
        
        # 分析当前持仓中需要清仓的
        for symbol, current_pos in current_dict.items():
            if symbol not in target_dict:
                # 需要清仓
                sell_pos = current_pos.copy()
                sell_pos[quantity_key] = 0  # 目标持仓为0
                result['to_sell'].append(sell_pos)
        
        return result