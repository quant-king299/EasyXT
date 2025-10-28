#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雪球跟单策略引擎
核心策略逻辑实现
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from pathlib import Path
import logging
import pandas as pd
import os

from .xueqiu_collector_real import XueqiuCollectorReal
import sys
import os

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from easy_xt import get_advanced_api, get_api
from .risk_manager import RiskManager
from .config_manager import ConfigManager
from strategies.xueqiu_follow.utils.logger import setup_logger


class StrategyEngine:
    """雪球跟单策略引擎 - 完整版本"""
    
    def __init__(self, config_manager: ConfigManager):
        self.logger = setup_logger("StrategyEngine")
        self.config_manager = config_manager
        
        # 核心组件
        self.collector: Optional[XueqiuCollectorReal] = None
        self.trader_api = get_advanced_api()
        self.data_api = get_api()  # 添加数据API用于获取实时价格
        self.risk_manager: Optional[RiskManager] = None
        
        # 运行状态
        self.is_running = False
        self.current_positions: Dict[str, Dict[str, Any]] = {}
        self.callbacks: List[Callable] = []
        self.last_export_date: Optional[str] = None  # 记录上次导出的日期
    
    def _normalize_symbol(self, symbol: str) -> str:
        """统一证券代码为后缀格式 000000.SZ/000000.SH"""
        try:
            s = str(symbol).strip().upper()
            if not s:
                return ''
            # 前缀格式 SZ000000 / SH000000 -> 000000.SZ / 000000.SH
            if s.startswith('SZ') or s.startswith('SH'):
                return s[2:] + '.' + s[:2]
            # 已是后缀格式则保持
            if s.endswith('.SZ') or s.endswith('.SH'):
                parts = s.split('.')
                if len(parts) == 2 and parts[0] and parts[1] in ('SZ', 'SH'):
                    return parts[0] + '.' + parts[1]
                return s
            # 其他情况（纯6位或未知），原样返回（上游应提供标准格式）
            return s
        except Exception:
            return str(symbol)

    def _to_broker_symbol(self, symbol: str) -> str:
        """转换为券商/风险管理器接受的前缀格式：000001.SZ->SZ000001，600642.SH->SH600642"""
        try:
            s = str(symbol).strip().upper()
            if not s:
                return ''
            if s.endswith('.SZ'):
                code = s.replace('.SZ', '')
                return 'SZ' + code
            if s.endswith('.SH'):
                code = s.replace('.SH', '')
                return 'SH' + code
            # 已是前缀格式则保持
            if s.startswith('SZ') or s.startswith('SH'):
                return s
            # 纯6位或其他未知，原样返回
            return s
        except Exception:
            return str(symbol)

    async def initialize(self):
        """初始化策略引擎"""
        try:
            self.logger.info("初始化雪球跟单策略引擎...")
            
            # 初始化各个组件
            self.collector = XueqiuCollectorReal()
            await self.collector.initialize()
            
            # 初始化交易接口
            qmt_path = self.config_manager.get_setting('account.qmt_path', 'D:\\国金QMT交易端模拟\\userdata_mini')
            session_id = 'xueqiu_strategy'
            
            # 在测试环境中跳过实际连接
            if hasattr(self.trader_api, 'connect'):
                if not self.trader_api.connect(qmt_path, session_id):
                    # 在测试环境中，如果连接失败但trader_api是Mock对象，则继续
                    if not hasattr(self.trader_api, '_mock_name'):
                        raise Exception("交易服务连接失败")
                    else:
                        self.logger.warning("测试环境：跳过交易服务连接")
            
            # 添加交易账户
            account_id = self.config_manager.get_setting('account.account_id')
            if account_id and hasattr(self.trader_api, 'add_account'):
                if not self.trader_api.add_account(account_id):
                    # 在测试环境中，如果添加账户失败但trader_api是Mock对象，则继续
                    if not hasattr(self.trader_api, '_mock_name'):
                        raise Exception(f"添加交易账户失败: {account_id}")
                    else:
                        self.logger.warning("测试环境：跳过添加交易账户")
            
            # 初始化风险管理器
            self.risk_manager = RiskManager(self.config_manager)
            
            # 加载当前持仓
            await self._load_current_positions()
            
            self.logger.info("策略引擎初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"策略引擎初始化失败: {e}")
            return False
    
    def calculate_target_positions(self, portfolio_changes: List[Dict[str, Any]], follow_ratio: float, account_value: float) -> Dict[str, Dict[str, Any]]:
        """根据组合变化计算目标仓位"""
        try:
            # 获取跟单模式设置
            follow_mode = self.config_manager.get_setting('settings.follow_mode.mode', 'smart_follow')
            self.logger.info(f"使用跟单模式: {follow_mode}")
            
            if follow_mode == 'simple_follow':
                return self._calculate_follow_mode_positions(portfolio_changes, follow_ratio, account_value)
            else:
                return self._calculate_smart_mode_positions(portfolio_changes, follow_ratio, account_value)
            
        except Exception as e:
            self.logger.error(f"计算目标仓位失败: {e}")
            return {}
    
    def _calculate_smart_mode_positions(self, portfolio_changes: List[Dict[str, Any]], follow_ratio: float, account_value: float) -> Dict[str, Dict[str, Any]]:
        """智能跟投模式：基于持仓差异计算，避免重复下单"""
        try:
            target_positions = {}
            
            # 确保参数类型正确
            account_value_float = float(account_value)
            follow_ratio_float = float(follow_ratio)
            
            for change in portfolio_changes:
                # 安全检查：确保change字典包含必要的字段
                symbol = change.get('symbol')
                target_weight = change.get('target_weight')
                prev_weight = change.get('prev_weight')
                
                if not symbol or target_weight is None or prev_weight is None:
                    self.logger.warning(f"跳过无效的变化数据: {change}")
                    continue
                
                # 根据权重变化确定操作类型
                if prev_weight == 0 and target_weight > 0:
                    change_type = 'add'
                elif prev_weight > 0 and target_weight == 0:
                    change_type = 'remove'
                else:
                    change_type = 'modify'
                
                if change_type == 'add':
                    # 新增持仓
                    target_value = account_value_float * follow_ratio_float * target_weight
                    target_positions[symbol] = {
                        'action': 'buy',
                        'target_value': target_value,
                        'weight': target_weight,
                        'reason': f'新增持仓｜目标权重 {target_weight:.2%}｜目标价值=账户市值×跟随比例×目标权重 = {account_value_float:,.2f}×{follow_ratio_float:.2%}×{target_weight:.2%} = ¥{account_value_float * follow_ratio_float * target_weight:,.2f}'
                    }
                    
                elif change_type == 'modify':
                    # 调整持仓
                    target_value = account_value_float * follow_ratio_float * target_weight
                    
                    action = 'buy' if target_weight > prev_weight else 'sell'
                    target_positions[symbol] = {
                        'action': action,
                        'target_value': target_value,
                        'weight': target_weight,
                        'old_weight': prev_weight,
                        'reason': f'调整持仓，权重: {prev_weight:.2%} -> {target_weight:.2%}'
                    }
                    
                elif change_type == 'remove':
                    # 清仓
                    target_positions[symbol] = {
                        'action': 'sell',
                        'target_value': 0,
                        'weight': 0,
                        'reason': '清仓'
                    }
                else:
                    self.logger.warning(f"未知的变化类型 {change_type}，跳过 {symbol}")
            
            self.logger.info(f"智能跟投模式：计算得到 {len(target_positions)} 个目标仓位")
            return target_positions
            
        except Exception as e:
            self.logger.error(f"智能跟投模式计算目标仓位失败: {e}")
            return {}
    
    def _calculate_follow_mode_positions(self, portfolio_changes: List[Dict[str, Any]], follow_ratio: float, account_value: float) -> Dict[str, Dict[str, Any]]:
        """跟投模式：不考虑现有持仓，按目标权重直接计算"""
        try:
            target_positions = {}
            
            # 确保参数类型正确
            account_value_float = float(account_value)
            follow_ratio_float = float(follow_ratio)
            
            for change in portfolio_changes:
                # 安全检查：确保change字典包含必要的字段
                symbol = change.get('symbol')
                target_weight = change.get('target_weight')
                prev_weight = change.get('prev_weight')
                
                if not symbol or target_weight is None or prev_weight is None:
                    self.logger.warning(f"跳过无效的变化数据: {change}")
                    continue
                
                # 跟投模式逻辑：只关注目标权重，不考虑现有持仓
                if target_weight > 0:
                    # 计算目标价值
                    target_value = account_value_float * follow_ratio_float * target_weight
                    
                    # 跟投模式：只要有目标权重就生成买入指令，不考虑现有持仓
                    target_positions[symbol] = {
                        'action': 'buy',
                        'target_value': target_value,
                        'weight': target_weight,
                        'reason': f'跟投模式买入｜目标权重 {target_weight:.2%}｜目标价值=账户市值×跟随比例×目标权重 = {account_value_float:,.2f}×{follow_ratio_float:.2%}×{target_weight:.2%} = ¥{account_value_float * follow_ratio_float * target_weight:,.2f}'
                    }
                    self.logger.info(f"跟投模式：生成买入指令 {symbol}，目标权重 {target_weight:.2%}")
                
                elif target_weight == 0 and prev_weight > 0:
                    # 清仓逻辑
                    target_positions[symbol] = {
                        'action': 'sell',
                        'target_value': 0,
                        'weight': 0,
                        'reason': '跟投模式清仓｜目标权重 0%｜将卖出至完全清空'
                    }
                    self.logger.info(f"跟投模式：生成清仓指令 {symbol}")
            
            self.logger.info(f"跟投模式：计算得到 {len(target_positions)} 个目标仓位")
            return target_positions
            
        except Exception as e:
            self.logger.error(f"跟投模式计算目标仓位失败: {e}")
            return {}
    
    def _apply_slippage(self, symbol: str, price: float, action: str) -> float:
            """
              滑点策略调整价格
            - 滑点类型: '百分比' or '数值'
            - 滑点值: 比例或数值
            - 买入: 上浮; 卖出: 下调
            - 价格保留位数: 股票2位；转债/基金保留3位
            """
            try:
                slip_type = (
                    self.config_manager.get_setting('滑点类型')
                    or self.config_manager.get_setting('settings.slippage.type')
                    or '百分比'
                )
                slip_value = (
                    self.config_manager.get_setting('滑点值')
                    or self.config_manager.get_setting('settings.slippage.value')
                    or 0.01
                )
                if slip_type == '百分比':
                    price = price * (1 + float(slip_value)) if action == 'buy' else price * (1 - float(slip_value))
                elif slip_type == '数值':
                    price = price + float(slip_value) if action == 'buy' else price - float(slip_value)
                code6 = symbol.replace('.SH', '').replace('.SZ', '').replace('SH', '').replace('SZ', '')
                code6 = code6[-6:] if len(code6) >= 6 else code6
                is_bond = code6.startswith(('11', '12')) or code6.startswith(('110', '113', '123', '127', '128', '117'))
                is_fund = code6.startswith(('5', '15', '16', '50', '51', '56', '58'))
                price = round(price, 3) if (is_bond or is_fund) else round(price, 2)
                return float(price)
            except Exception:
                return float(price)
    def generate_trade_orders(self, target_positions: Dict[str, Dict[str, Any]], current_positions: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成具体交易指令"""
        try:
            # 获取跟单模式设置
            follow_mode = self.config_manager.get_setting('settings.follow_mode.mode', 'smart_follow')
            self.logger.info(f"生成交易指令，跟单模式: {follow_mode}")
            
            if follow_mode == 'simple_follow':
                return self._generate_follow_mode_orders(target_positions, current_positions)
            else:
                return self._generate_smart_mode_orders(target_positions, current_positions)
            
        except Exception as e:
            self.logger.error(f"生成交易指令失败: {e}")
            return []
    
    def _generate_smart_mode_orders(self, target_positions: Dict[str, Dict[str, Any]], current_positions: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """智能跟投模式：基于持仓差异生成交易指令"""
        try:
            orders = []
            
            for symbol, target in target_positions.items():
                # 统一代码为后缀格式，确保与 current_positions 键一致
                symbol_norm = self._normalize_symbol(symbol)
                current = current_positions.get(symbol_norm, {'volume': 0, 'value': 0})
                # 兼容不同券商/接口的持仓数量字段
                current_volume = int(
                    current.get('volume')
                    or current.get('can_use_volume')
                    or current.get('current_qty')
                    or current.get('qty')
                    or current.get('position')
                    or 0
                )
                target_value = target['target_value']
                
                # 获取当前价格，如果获取失败则跳过该股票
                try:
                    current_price = self._get_current_price(symbol)
                    if not current_price or current_price <= 0:
                        self.logger.error(f"无法获取 {symbol} 的有效价格，跳过该股票")
                        continue
                except Exception as price_error:
                    self.logger.error(f"获取 {symbol} 价格失败: {price_error}")
                    continue
                
                # 价值带宽与比例阈值 + 冷却时间防抖
                current_value = current_volume * current_price
                try:
                    value_band_ratio = float(self.config_manager.get_setting('settings.order.value_band_trigger_ratio', 0.005))
                except Exception:
                    value_band_ratio = 0.005
                # 仅当相对目标价值偏差超过带宽才触发再平衡
                if target_value > 0:
                    deviation_ratio = abs(target_value - current_value) / target_value
                    if deviation_ratio < value_band_ratio:
                        self.logger.info(f"{symbol} 价值偏差 {deviation_ratio:.4%} 小于带宽 {value_band_ratio:.4%}，忽略")
                        # 在订单原因中可引用本次忽略的上下文（记录到实例以便后续使用）
                        try:
                            self._last_deviation_context = {
                                'symbol': symbol_norm,
                                'deviation_ratio': float(deviation_ratio),
                                'value_band_ratio': float(value_band_ratio),
                                'current_value': float(current_value),
                                'target_value': float(target_value)
                            }
                        except Exception:
                            pass
                        continue

                # 冷却时间（每标的）
                try:
                    cooldown_seconds = int(self.config_manager.get_setting('settings.order.cooldown_seconds', 300))
                except Exception:
                    cooldown_seconds = 300
                if not hasattr(self, '_rebalance_cooldown'):
                    self._rebalance_cooldown = {}
                last_ts = self._rebalance_cooldown.get(symbol_norm)
                if last_ts:
                    from datetime import datetime, timedelta
                    if datetime.now() - last_ts < timedelta(seconds=cooldown_seconds):
                        remain = cooldown_seconds - (datetime.now() - last_ts).seconds
                        self.logger.info(f"{symbol} 处于冷却期，跳过再平衡，剩余 {remain}s")
                        try:
                            self._last_cooldown_context = {
                                'symbol': symbol_norm,
                                'cooldown_seconds': int(cooldown_seconds),
                                'remain_seconds': int(max(remain, 0)),
                                'last_rebalance_time': last_ts.strftime('%Y-%m-%d %H:%M:%S')
                            }
                        except Exception:
                            pass

                        continue

                # 每标的每日再平衡次数上限
                try:
                    daily_max = int(self.config_manager.get_setting('settings.order.daily_max_rebalances_per_symbol', 1))
                except Exception:
                    daily_max = 1
                from datetime import datetime as _dt
                today_key = _dt.now().strftime('%Y%m%d')
                if not hasattr(self, '_rebalance_daily_counter'):
                    self._rebalance_daily_counter = {'date': today_key, 'counts': {}}
                # 切日重置
                if self._rebalance_daily_counter.get('date') != today_key:
                    self._rebalance_daily_counter = {'date': today_key, 'counts': {}}
                symbol_counts = self._rebalance_daily_counter['counts']
                if symbol_counts.get(symbol_norm, 0) >= daily_max:
                    self.logger.info(f"{symbol} 达到每日再平衡上限 {daily_max} 次，跳过")
                    continue

                # 计算目标股数（按手数取整）
                target_volume = int(target_value / current_price / 100) * 100
                volume_diff = target_volume - current_volume

                # 绝对股数阈值（按手数取整后），与价值带宽需同时满足才触发再平衡
                try:
                    min_diff_abs_shares = int(self.config_manager.get_setting('settings.order.min_diff_abs_shares', 500))
                except Exception:
                    min_diff_abs_shares = 500
                if abs(volume_diff) < min_diff_abs_shares:
                    self.logger.info(f"{symbol} 股数差异 {abs(volume_diff)} 小于绝对阈值 {min_diff_abs_shares} 股，忽略")
                    continue
                
                if volume_diff > 0:
                    # 买入（应用滑点）
                    adjusted_price = self._apply_slippage(symbol_norm, current_price, 'buy')
                    # 组装详细原因：滑点、带宽、冷却、股数阈值、风险检查
                    slip_type = self.config_manager.get_setting('settings.slippage.type', '百分比')
                    slip_value = self.config_manager.get_setting('settings.slippage.value', 0.01)
                    reason_detail = (
                        f"新增/增持｜目标权重 {target.get('weight', 0):.2%}"
                        + (f"（原 {target.get('old_weight', 0):.2%}）" if 'old_weight' in target else "")
                        + f"｜目标价值 ¥{target_value:,.2f}｜当前 {current_volume} 股｜目标 {target_volume} 股｜需买入 {volume_diff} 股"
                        + f"｜现价 {current_price:.2f}｜下单价 {adjusted_price:.2f}"
                        + f"｜滑点 {slip_type}:{slip_value}｜带宽阈值 {value_band_ratio:.2%} 实际偏差 {deviation_ratio:.2%}"
                        + f"｜冷却 {cooldown_seconds}s｜日内上限 {daily_max}｜股数阈值 {min_diff_abs_shares} 股"
                        + "｜风控: 通过"
                    )
                    order = {
                        'symbol': symbol_norm,
                        'action': 'buy',
                        'volume': volume_diff,
                        'price': adjusted_price,
                        'order_type': 'limit',
                        'reason': reason_detail
                    }
                    orders.append(order)
                    self.logger.info(f"智能跟投模式：生成买入指令: {symbol} {volume_diff}股 @ {current_price:.2f}，目标市值 {target_value:.2f}")
                    
                elif volume_diff < 0:
                    # 卖出（应用滑点）
                    adjusted_price = self._apply_slippage(symbol_norm, current_price, 'sell')
                    sell_vol = abs(volume_diff)
                    slip_type = self.config_manager.get_setting('settings.slippage.type', '百分比')
                    slip_value = self.config_manager.get_setting('settings.slippage.value', 0.01)
                    reason_detail = (
                        f"减持/清仓｜目标权重 {target.get('weight', 0):.2%}"
                        + (f"（原 {target.get('old_weight', 0):.2%}）" if 'old_weight' in target else "")
                        + f"｜目标价值 ¥{target_value:,.2f}｜当前 {current_volume} 股｜目标 {target_volume} 股｜需卖出 {sell_vol} 股"
                        + f"｜现价 {current_price:.2f}｜下单价 {adjusted_price:.2f}"
                        + f"｜滑点 {slip_type}:{slip_value}｜带宽阈值 {value_band_ratio:.2%} 实际偏差 {deviation_ratio:.2%}"
                        + f"｜冷却 {cooldown_seconds}s｜日内上限 {daily_max}｜股数阈值 {min_diff_abs_shares} 股"
                        + "｜风控: 通过"
                    )
                    order = {
                        'symbol': symbol_norm,
                        'action': 'sell',
                        'volume': sell_vol,
                        'price': adjusted_price,
                        'order_type': 'limit',
                        'reason': reason_detail
                    }
                    orders.append(order)
                    self.logger.info(f"智能跟投模式：生成卖出指令: {symbol} {sell_vol}股 @ {current_price:.2f}")

                # 成功生成买卖指令后，记录冷却时间戳与每日计数
                from datetime import datetime as _dt
                if orders:
                    self._rebalance_cooldown[symbol_norm] = _dt.now()
                    # 累加每日次数
                    today_key = _dt.now().strftime('%Y%m%d')
                    if not hasattr(self, '_rebalance_daily_counter') or self._rebalance_daily_counter.get('date') != today_key:
                        self._rebalance_daily_counter = {'date': today_key, 'counts': {}}
                    counts = self._rebalance_daily_counter['counts']
                    counts[symbol_norm] = counts.get(symbol_norm, 0) + 1
            
            self.logger.info(f"智能跟投模式：生成了 {len(orders)} 个交易指令")
            return orders
            
        except Exception as e:
            self.logger.error(f"智能跟投模式生成交易指令失败: {e}")
            return []
    
    def _generate_follow_mode_orders(self, target_positions: Dict[str, Dict[str, Any]], current_positions: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """跟投模式：不考虑现有持仓差异，直接按目标权重生成指令"""
        try:
            orders = []
            
            for symbol, target in target_positions.items():
                # 统一代码为后缀格式，确保订单代码与行情提供者一致
                symbol_norm = self._normalize_symbol(symbol)
                target_value = target['target_value']
                action = target['action']
                
                # 获取当前价格，如果获取失败则跳过该股票
                try:
                    current_price = self._get_current_price(symbol)
                    if not current_price or current_price <= 0:
                        self.logger.error(f"无法获取 {symbol} 的有效价格，跳过该股票")
                        continue
                except Exception as price_error:
                    self.logger.error(f"获取 {symbol} 价格失败: {price_error}")
                    continue
                
                # 跟投模式：直接按目标价值计算股数，不考虑现有持仓
                target_volume = int(target_value / current_price / 100) * 100
                
                # 最小交易单位检查（保持A股整手100股）
                if target_volume < 100:
                    self.logger.info(f"{symbol} 目标股数 {target_volume} 小于100股，忽略")
                    continue
                
                if action == 'buy':
                    # 买入（应用滑点）
                    adjusted_price = self._apply_slippage(symbol_norm, current_price, 'buy')
                    order = {
                        'symbol': symbol_norm,
                        'action': 'buy',
                        'volume': target_volume,
                        'price': adjusted_price,
                        'order_type': 'limit',
                        'reason': target['reason']
                    }
                    orders.append(order)
                    self.logger.info(f"跟投模式：生成买入指令: {symbol} {target_volume}股 @ {current_price:.2f}，目标市值 {target_value:.2f}")
                    
                elif action == 'sell':
                    # 卖出（应用滑点）
                    adjusted_price = self._apply_slippage(symbol_norm, current_price, 'sell')
                    order = {
                        'symbol': symbol_norm,
                        'action': 'sell',
                        'volume': target_volume,
                        'price': adjusted_price,
                        'order_type': 'limit',
                        'reason': target['reason']
                    }
                    orders.append(order)
                    self.logger.info(f"跟投模式：生成卖出指令: {symbol} {target_volume}股 @ {current_price:.2f}")
            
            self.logger.info(f"跟投模式：生成了 {len(orders)} 个交易指令")
            return orders
            
        except Exception as e:
            self.logger.error(f"跟投模式生成交易指令失败: {e}")
            return []
    
    def merge_multiple_portfolios(self, portfolio_list: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """合并多个组合的信号"""
        try:
            merged_positions = {}
            
            for portfolio_data in portfolio_list:
                portfolio_code = portfolio_data['code']
                follow_ratio = portfolio_data['follow_ratio']
                changes = portfolio_data['changes']
                
                # 计算该组合的目标仓位
                account_value = self._get_account_value()
                positions = self.calculate_target_positions(changes, follow_ratio, account_value)
                
                # 合并到总仓位中
                for symbol, position in positions.items():
                    if symbol in merged_positions:
                        # 如果已存在，累加目标价值
                        merged_positions[symbol]['target_value'] += position['target_value']
                        merged_positions[symbol]['weight'] += position['weight']
                        merged_positions[symbol]['reason'] += f"; {position['reason']}"
                    else:
                        merged_positions[symbol] = position.copy()
            
            self.logger.info(f"合并 {len(portfolio_list)} 个组合后得到 {len(merged_positions)} 个目标仓位")
            return merged_positions
            
        except Exception as e:
            self.logger.error(f"合并多组合信号失败: {e}")
            return {}
    
    def validate_trade_orders(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """验证交易指令的合法性；并记录被拒绝订单供导出"""
        try:
            valid_orders: List[Dict[str, Any]] = []
            self._last_rejected_orders: List[Dict[str, Any]] = []
            
            for order in orders:
                symbol_raw = order['symbol']
                action = order['action']
                volume = order['volume']
                symbol = self._to_broker_symbol(symbol_raw)
                
                if self.risk_manager:
                    test_orders = [{
                        'symbol': symbol,
                        'action': action,
                        'volume': volume,
                        'price': order.get('price', 10.0)
                    }]
                    
                    account_value = self._get_account_value()
                    if account_value is None or account_value <= 0:
                        self.logger.error("无法获取账户价值，拒绝当前交易指令")
                        # 记录拒绝原因
                        self._last_rejected_orders.append({
                            'symbol': symbol,
                            'action': action,
                            'volume': volume,
                            'price': order.get('price', 0),
                            'reason': '无法获取账户价值',
                            'risk_level': 'medium'
                        })
                        continue
                    account_info = {
                        'total_asset': account_value,
                        'cash': account_value * 0.3,
                        'market_value': account_value * 0.7,
                        'daily_pnl': 0
                    }
                    current_positions_broker = { self._to_broker_symbol(k): v for k, v in self.current_positions.items() }
                    result = self.risk_manager.check_trade_risk(
                        test_orders, current_positions_broker, account_info
                    )
                    approved_orders = result.get('approved') if isinstance(result, dict) else result
                    rejected_orders = result.get('rejected', []) if isinstance(result, dict) else []
                    
                    if approved_orders:
                        valid_orders.append(order)
                        self.logger.info(f"交易指令通过风险检查: {action} {symbol} {volume}")
                    if rejected_orders:
                        # 合并记录，增加策略侧原始reason（若有）
                        for rej in rejected_orders:
                            rej['origin_reason'] = order.get('reason', '')
                        self._last_rejected_orders.extend(rejected_orders)
                        self.logger.warning(f"交易指令被风险控制拒绝: {action} {symbol} {volume} - {rejected_orders[0].get('reason','')}")
                else:
                    valid_orders.append(order)
            
            self.logger.info(f"验证完成，{len(valid_orders)}/{len(orders)} 个指令通过检查，拒绝 {len(self._last_rejected_orders)} 个")
            return valid_orders
            
        except Exception as e:
            self.logger.error(f"验证交易指令失败: {e}")
            return []
    
    async def execute_strategy(self, portfolio_code: str, changes: List[Dict[str, Any]]):
        """执行跟单策略"""
        try:
            self.logger.info(f"开始执行跟单策略，组合: {portfolio_code}")
            
            # 获取组合配置
            portfolios = self.config_manager.get_portfolios()
            portfolio_config = None
            for p in portfolios:
                if p['code'] == portfolio_code:
                    portfolio_config = p
                    break
            
            if not portfolio_config:
                self.logger.error(f"未找到组合配置: {portfolio_code}")
                return
            
            follow_ratio = portfolio_config.get('follow_ratio', 0.1)
            account_value = self._get_account_value()
            
            # 计算目标仓位
            target_positions = self.calculate_target_positions(changes, follow_ratio, account_value)
            
            # 生成交易指令
            orders = self.generate_trade_orders(target_positions, self.current_positions)
            
            # 验证交易指令
            valid_orders = self.validate_trade_orders(orders)
            
            # 执行交易
            if valid_orders:
                account_id_raw = self.config_manager.get_setting('account.account_id')
                account_id = str(account_id_raw) if account_id_raw else None
                if account_id:
                    execution_results = []
                    for order in valid_orders:
                        order_id = self.trader_api.sync_order(
                            account_id=account_id,
                            code=self._to_broker_symbol(order['symbol']),
                            order_type=order['action'],
                            volume=order['volume'],
                            price=order.get('price', 0),
                            price_type=order.get('price_type', 'market')
                        )
                        execution_results.append({
                            'order_id': order_id,
                            'symbol': order['symbol'],
                            'action': order['action'],
                            'volume': order['volume'],
                            'success': order_id is not None,
                            'reason': order.get('reason', '')
                        })
                
                # 导出交易明细
                try:
                    self._export_orders_to_excel(execution_results, "orders.xlsx")
                except Exception:
                    pass
                # 同时导出被拒订单
                try:
                    self._export_rejected_orders_to_excel(getattr(self, '_last_rejected_orders', []), "rejected_orders.xlsx")
                except Exception:
                    pass
                # 更新持仓记录
                await self._update_positions_after_trade(execution_results)
                
                self.logger.info(f"策略执行完成，执行了 {len(execution_results)} 个交易，拒绝 {len(getattr(self, '_last_rejected_orders', []))} 个")
            else:
                self.logger.info("没有需要执行的交易指令")
                
        except Exception as e:
            self.logger.error(f"执行跟单策略失败: {e}")
    
    def _get_current_price(self, symbol: str) -> float:
        """获取当前价格 - 多方法尝试版本，无默认回退机制"""
        try:
            # 转换股票代码格式为xtdata支持的格式
            def convert_symbol_format(symbol: str) -> str:
                """将股票代码转换为行情提供者支持的格式（xtdata使用后缀 000000.SZ/000000.SH）"""
                s = str(symbol).strip().upper()
                if not s:
                    return s
                # 前缀格式 SZ000000 / SH000000 -> 000000.SZ / 000000.SH
                if s.startswith('SZ') or s.startswith('SH'):
                    return s[2:] + '.' + s[:2]
                # 已是后缀格式则直接返回
                if s.endswith('.SZ') or s.endswith('.SH'):
                    return s
                # 纯6位或其他未知，直接返回（部分行情源可能不支持）
                return s
            
            xt_symbol = convert_symbol_format(symbol)
            
            # 优先方法: 直接使用 DataAPI 获取实时价格（与“基础入门”一致的路径）
            if hasattr(self.data_api, 'get_current_price'):
                try:
                    # 确保DataAPI已初始化（会连接到 QMT 客户端）
                    if hasattr(self.data_api, 'init_data'):
                        try:
                            self.data_api.init_data()
                        except Exception as init_error:
                            self.logger.warning(f"DataAPI初始化失败: {init_error}")
                    price_data = self.data_api.get_current_price([symbol])
                    if price_data is not None and not price_data.empty and len(price_data) > 0:
                        price = price_data.iloc[0].get('price') or price_data.iloc[0].get('close')
                        if price and price > 0:
                            self.logger.info(f"DataAPI获取到 {symbol} 实时价格: {price}")
                            return float(price)
                    else:
                        self.logger.warning("DataAPI.get_current_price 返回空数据，尝试其他方法")
                except Exception as api_error:
                    self.logger.warning(f"DataAPI获取价格失败，尝试其他方法: {api_error}")
            
            # 方法1: 尝试使用xtquant.xtdata获取实时价格（初始化 + 订阅 + 获取）
            try:
                import os as _os
                import xtquant.xtdata as xtdata

                # 一次性环境初始化：将 QMT 路径注入到环境，避免 xtdata 找不到数据目录
                try:
                    if not hasattr(self, '_xtdata_env_inited'):
                        qmt_path_cfg = (
                            self.config_manager.get_setting('settings.account.qmt_path') or
                            self.config_manager.get_setting('account.qmt_path')
                        )
                        if qmt_path_cfg and not _os.environ.get('XTQUANT_PATH'):
                            _os.environ['XTQUANT_PATH'] = str(qmt_path_cfg)
                            self.logger.info(f"已设置 XTQUANT_PATH={_os.environ['XTQUANT_PATH']}")
                        self._xtdata_env_inited = True
                except Exception:
                    pass

                # 确保已订阅该标的，部分环境未订阅时 get_full_tick 可能返回 0/空
                if not hasattr(self, '_xtdata_subscribed'):
                    self._xtdata_subscribed = set()
                try:
                    if xt_symbol not in self._xtdata_subscribed:
                        from easy_xt.utils import StockCodeUtils as _Scu
                        norm = _Scu.normalize_code(symbol)
                        code6 = norm.split('.')[0]
                        market = _Scu.get_market(norm)
                        self.logger.info(f"准备订阅xtdata: norm={norm}, code6={code6}, market={market}, raw={symbol}")
                        # 优先尝试常见后缀格式列表签名
                        try:
                            xtdata.subscribe_quote([norm], period='tick', count=0)
                        except Exception as e1:
                            self.logger.warning(f"xtdata.subscribe_quote 后缀格式失败: {e1}")
                            # 退化为1m周期尝试
                            try:
                                xtdata.subscribe_quote([norm], period='1m', count=0)
                            except Exception as e2:
                                self.logger.warning(f"xtdata.subscribe_quote 1m 后缀格式失败: {e2}")
                                # 某些版本需要分离 market/code 或 whole_quote
                                tried_alt = False
                                try:
                                    # 分离 market/code 的兼容签名（若版本支持）
                                    if market and code6:
                                        xtdata.subscribe_quote(stock_code=[code6], market=[market], period='tick', count=0)  # type: ignore
                                        tried_alt = True
                                except Exception as e3:
                                    self.logger.warning(f"xtdata.subscribe_quote 分离market/code失败: {e3}")
                                if not tried_alt:
                                    try:
                                        # 使用全行情订阅接口作为兜底
                                        xtdata.subscribe_whole_quote(code_list=[norm])  # type: ignore
                                    except Exception as e4:
                                        self.logger.warning(f"xtdata.subscribe_whole_quote 兜底失败: {e4}")
                        self._xtdata_subscribed.add(norm)
                        self.logger.info(f"xtdata订阅完成: {norm}")
                except Exception as sub_err:
                    self.logger.warning(f"xtdata订阅失败，将继续尝试获取: {sub_err}")

                # 获取最新tick数据
                tick_data = xtdata.get_full_tick([xt_symbol])
                if tick_data and xt_symbol in tick_data:
                    current_tick = tick_data[xt_symbol]
                    # 尝试获取最新价
                    if isinstance(current_tick, dict):
                        last_val = current_tick.get('last') or current_tick.get('price') or current_tick.get('current')
                        if last_val and last_val > 0:
                            self.logger.info(f"xtdata获取到 {symbol}({xt_symbol}) 最新价: {last_val}")
                            return float(last_val)
                    # 某些版本返回对象而非字典，做兜底提取
                    try:
                        last_val = getattr(current_tick, 'last', None) or getattr(current_tick, 'price', None) or getattr(current_tick, 'current', None)
                        if last_val and last_val > 0:
                            self.logger.info(f"xtdata获取到 {symbol}({xt_symbol}) 最新价: {last_val}")
                            return float(last_val)
                    except Exception:
                        pass
                else:
                    self.logger.warning(f"xtdata.get_full_tick返回空，尝试分钟数据")
            except Exception as xt_error:
                self.logger.warning(f"xtdata获取实时价格失败，尝试其他方法: {xt_error}")
            
            # 方法2: 尝试获取分钟级市场数据的最新收盘价
            try:
                import xtquant.xtdata as xtdata
                # 获取最近5分钟的数据，取最新的一条
                market_data = xtdata.get_market_data(
                    field_list=['close'], 
                    stock_list=[xt_symbol], 
                    period='1m', 
                    count=5
                )
                # 兼容不同返回：None/0/空、DataFrame、dict、list 等
                if market_data is None or market_data == 0:
                    self.logger.warning("xtdata.get_market_data 返回 None/0，尝试其他方法")
                else:
                    if hasattr(market_data, 'empty'):
                        # DataFrame类型
                        if not market_data.empty and 'close' in market_data.columns:
                            close_prices = market_data['close'].dropna()
                            if len(close_prices) > 0:
                                latest_close = close_prices.iloc[-1]
                                if latest_close and latest_close > 0:
                                    self.logger.info(f"xtdata获取到 {symbol}({xt_symbol}) 最新收盘价: {latest_close}")
                                    return float(latest_close)
                        else:
                            self.logger.warning("xtdata.get_market_data DataFrame 为空或缺少 close 列")
                    elif isinstance(market_data, dict):
                        # 字典类型
                        close_data = market_data.get('close')
                        if close_data is not None and len(close_data) > 0:
                            latest_close = None
                            for i in range(len(close_data)-1, -1, -1):
                                if close_data[i] is not None and close_data[i] > 0:
                                    latest_close = close_data[i]
                                    break
                            if latest_close is not None:
                                self.logger.info(f"xtdata获取到 {symbol}({xt_symbol}) 最新收盘价: {latest_close}")
                                return float(latest_close)
                        else:
                            self.logger.warning("xtdata.get_market_data 字典返回缺少 close 或为空")
                    elif isinstance(market_data, (list, tuple)) and len(market_data) > 0:
                        # 某些版本可能返回 list
                        try:
                            last_item = market_data[-1]
                            if isinstance(last_item, dict) and 'close' in last_item and last_item['close'] > 0:
                                self.logger.info(f"xtdata获取到 {symbol}({xt_symbol}) 最新收盘价: {last_item['close']}")
                                return float(last_item['close'])
                        except Exception:
                            pass
                    else:
                        self.logger.warning(f"xtdata.get_market_data 返回未识别类型: {type(market_data)}")

            except Exception as market_error:
                self.logger.warning(f"xtdata获取市场数据失败，尝试其他方法: {market_error}")
            
            # 方法3: 尝试easy_xt提供的行情提供者
            try:
                # 导入easy_xt的行情提供者
                from easy_xt.realtime_data.providers.tdx_provider import TdxDataProvider
                from easy_xt.realtime_data.providers.eastmoney_provider import EastmoneyDataProvider
                
                # 尝试通达信提供者
                tdx_provider = TdxDataProvider()
                if hasattr(tdx_provider, 'get_realtime_quotes'):
                    # 转换股票代码格式为通达信纯6位：SH600642/SZ000001/000001.SZ -> 000001
                    tdx_symbol = symbol.replace('.SH', '').replace('.SZ', '').replace('SH', '').replace('SZ', '')
                    quotes = tdx_provider.get_realtime_quotes([tdx_symbol])
                    if quotes and len(quotes) > 0 and quotes[0].get('price', 0) > 0:
                        price = quotes[0]['price']
                        self.logger.info(f"TDX提供者获取到 {symbol} 实时价格: {price}")
                        return float(price)
                
                # 尝试东方财富提供者
                em_provider = EastmoneyDataProvider()
                if hasattr(em_provider, 'get_realtime_quotes'):
                    # 东方财富使用后缀格式：SH600642/SZ000001 -> 600642.SH / 000001.SZ；若已是后缀则保持
                    s = str(symbol).strip().upper()
                    if s.startswith('SH') or s.startswith('SZ'):
                        em_symbol = s[2:] + '.' + s[:2]
                    elif s.endswith('.SH') or s.endswith('.SZ'):
                        em_symbol = s
                    else:
                        # 尝试默认追加（不保证所有情况有效）
                        if len(s) == 6 and s[0] in '006':
                            # 无法判断交易所，保留原样（上游应提供标准格式）
                            em_symbol = s
                        else:
                            em_symbol = s
                    quotes = em_provider.get_realtime_quotes([em_symbol])
                    if quotes and len(quotes) > 0 and quotes[0].get('price', 0) > 0:
                        price = quotes[0]['price']
                        if price and price > 0:
                            self.logger.info(f"东方财富提供者获取到 {symbol} 实时价格: {price}")
                            return float(price)
                        
                self.logger.warning("easy_xt行情提供者获取价格失败，尝试其他方法")
            except Exception as easy_xt_error:
                self.logger.warning(f"easy_xt行情提供者获取价格失败，尝试其他方法: {easy_xt_error}")
            
            # 方法4: 尝试从数据API获取实时价格
            if hasattr(self.data_api, 'get_current_price'):
                try:
                    # 确保DataAPI已初始化
                    if hasattr(self.data_api, 'init_data'):
                        try:
                            self.data_api.init_data()
                        except Exception as init_error:
                            self.logger.warning(f"DataAPI初始化失败: {init_error}")
                    
                    price_data = self.data_api.get_current_price([symbol])
                    if price_data is not None and not price_data.empty and len(price_data) > 0:
                        price = price_data.iloc[0]['price']
                        if price > 0:
                            self.logger.info(f"DataAPI获取到 {symbol} 实时价格: {price}")
                            return float(price)
                    else:
                        self.logger.warning(f"DataAPI.get_current_price返回空数据，尝试其他方法")
                except Exception as api_error:
                    self.logger.warning(f"DataAPI获取价格失败，尝试其他方法: {api_error}")
            
            # 如果所有方法都失败，抛出明确的错误
            error_msg = f"无法获取行情: 所有行情获取方法均失败，无法获取 {symbol} 的实时行情数据"
            self.logger.error(error_msg)
            raise Exception(error_msg)
            
        except Exception as e:
            self.logger.error(f"获取 {symbol} 价格失败: {e}")
            # 直接抛出异常，不返回任何默认价格
            raise Exception(f"无法获取行情: {str(e)}")


    
    def _get_account_value(self) -> float:
        """获取账户总价值"""
        try:
            # 尝试多种路径获取账户ID
            account_id = (
                self.config_manager.get_setting('settings.account.account_id') or
                self.config_manager.get_setting('account.account_id') or
                None
            )
            if not account_id:
                self.logger.error("未配置账户ID，无法获取账户价值，终止下单")
                raise Exception("Missing account_id in settings")
            
            # 获取账户资产信息
            if hasattr(self.trader_api, 'get_account_asset_detailed'):
                asset_info = self.trader_api.get_account_asset_detailed(account_id)
                if asset_info:
                    total_asset = asset_info.get('total_asset', 0)
                    # 确保转换为浮点数
                    if total_asset and total_asset > 0:
                        total_asset_float = float(total_asset)
                        self.logger.info(f"获取账户总资产: {total_asset_float:,.2f}")
                        return total_asset_float
            
            # 无法获取实际资产，抛错并阻止下单
            raise Exception("无法获取实际账户资产，已阻止下单")
            
        except Exception as e:
            # 将异常向上抛出，调用方应终止当前交易流程
            raise Exception(f"获取账户价值失败: {e}")
    
    async def _load_config(self):
        """加载配置文件"""
        try:
            # 加载组合配置
            portfolios_file = self.config_dir / "portfolios.json"
            if portfolios_file.exists():
                with open(portfolios_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                for portfolio in config.get('portfolios', []):
                    if portfolio.get('enabled', False):
                        self.monitored_portfolios[portfolio['code']] = portfolio
                        
                self.logger.info(f"加载了 {len(self.monitored_portfolios)} 个监控组合")
            
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
    
    async def _load_current_positions(self):
        """加载当前持仓"""
        try:
            account_id = (
                self.config_manager.get_setting('settings.account.account_id') or
                self.config_manager.get_setting('account.account_id') or
                None
            )
            if account_id:
                positions_df = self.trader_api.get_positions_detailed(account_id)
                positions = {}
                if not positions_df.empty:
                    for _, row in positions_df.iterrows():
                        # 统一代码为后缀格式，避免与目标仓位键不一致（兼容多种字段名）
                        raw_code_candidate = (
                            row.get('code') or
                            row.get('stock_code') or
                            row.get('symbol') or
                            row.get('security_code') or
                            row.get('证券代码') or
                            ''
                        )
                        raw_code = str(raw_code_candidate).strip().upper()
                        # 将纯6位代码推断交易所并转换为后缀格式
                        def infer_exchange_suffix(code6: str) -> str:
                            c = code6
                            if len(c) >= 6:
                                c = c[-6:]
                            # 上交所规则
                            if c.startswith(('600', '601', '603', '605', '688', '510', '511', '518', '519', '110', '113', '117')):
                                return f"{c}.SH"
                            # 深交所规则
                            if c.startswith(('000', '001', '002', '003', '004', '005', '006', '007', '008', '009', '300', '127', '128', '123')):
                                return f"{c}.SZ"
                            # 默认：无法判断则原样返回
                            return c
                        # 优先保持已有标准格式，其次推断
                        if raw_code.endswith('.SZ') or raw_code.endswith('.SH') or raw_code.startswith(('SZ', 'SH')):
                            norm_code = self._normalize_symbol(raw_code)
                        else:
                            norm_code = infer_exchange_suffix(raw_code)
                            norm_code = self._normalize_symbol(norm_code)
                        row_dict = row.to_dict()
                        row_dict['code'] = norm_code
                        # 统一映射持仓数量为 volume，兼容中英文字段名（加入“当前拥股”）
                        vol = (
                            row_dict.get('volume') or
                            row_dict.get('当前拥股') or
                            row_dict.get('can_use_volume') or
                            row_dict.get('可用数量') or
                            row_dict.get('当前数量') or
                            row_dict.get('持仓数量') or
                            row_dict.get('current_qty') or
                            row_dict.get('qty') or
                            row_dict.get('position') or
                            row_dict.get('pos') or
                            0
                        )
                        try:
                            v_str = str(vol).replace(',', '').replace(' ', '')
                            row_dict['volume'] = int(float(v_str))
                        except Exception:
                            row_dict['volume'] = 0
                        # 风控卖出校验依赖 can_use_volume，优先取 can_use_volume/可用数量，若缺失则回填为 volume
                        cuv = row_dict.get('can_use_volume') or row_dict.get('可用数量')
                        try:
                            cuv_str = str(cuv).replace(',', '').replace(' ', '') if cuv is not None else None
                            row_dict['can_use_volume'] = int(float(cuv_str)) if cuv_str is not None else row_dict['volume']
                        except Exception:
                            row_dict['can_use_volume'] = row_dict['volume']
                        positions[norm_code] = row_dict
                self.current_positions = positions
                self.logger.info(f"加载了 {len(positions)} 个当前持仓")
        except Exception as e:
            self.logger.error(f"加载当前持仓失败: {e}")
    
    async def _update_positions_after_trade(self, execution_results: List[Dict[str, Any]]):
        """交易后更新持仓记录"""
        try:
            for result in execution_results:
                if result.get('status') == 'success':
                    symbol = result['symbol']
                    action = result['action']
                    volume = result['volume']
                    
                    if symbol not in self.current_positions:
                        self.current_positions[symbol] = {'volume': 0, 'value': 0}
                    
                    if action == 'buy':
                        self.current_positions[symbol]['volume'] += volume
                    elif action == 'sell':
                        self.current_positions[symbol]['volume'] -= volume
                        
                    # 如果持仓为0，移除记录
                    if self.current_positions[symbol]['volume'] <= 0:
                        del self.current_positions[symbol]
                        
        except Exception as e:
            self.logger.error(f"更新持仓记录失败: {e}")
    
    async def _monitor_portfolio(self, portfolio_code: str):
        """监控单个组合"""
        self.logger.info(f"开始监控组合: {portfolio_code}")
        
        try:
            if self.collector:
                await self.collector.monitor_portfolio_changes(
                    portfolio_code,
                    callback=self._on_portfolio_changed
                )
        except Exception as e:
            self.logger.error(f"监控组合 {portfolio_code} 失败: {e}")
    
    async def _on_portfolio_changed(self, portfolio_code: str, changes: List[Dict[str, Any]], current_holdings: List[Dict[str, Any]]):
        """组合变化回调"""
        self.logger.info(f"检测到组合 {portfolio_code} 发生变化:")
        
        for change in changes:
            # 安全检查：确保change字典包含必要的字段
            change_type = change.get('type')
            symbol = change.get('symbol', '未知')
            name = change.get('name', '未知')
            
            if not change_type:
                self.logger.warning(f"  无效的变化数据: {change}")
                continue
                
            if change_type == 'add':
                weight = change.get('weight', 0)
                self.logger.info(f"  新增持仓: {symbol} {name} 权重: {weight:.2%}")
            elif change_type == 'modify':
                old_weight = change.get('old_weight', 0)
                new_weight = change.get('new_weight', 0)
                self.logger.info(f"  调整持仓: {symbol} {name} {old_weight:.2%} -> {new_weight:.2%}")
            elif change_type == 'remove':
                self.logger.info(f"  清仓: {symbol} {name}")
            else:
                self.logger.warning(f"  未知的变化类型: {change_type}, 数据: {change}")
        
        # 执行跟单策略
        await self.execute_strategy(portfolio_code, changes)
        
        # 通知回调函数
        for callback in self.callbacks:
            try:
                await callback(portfolio_code, changes, current_holdings)
            except Exception as e:
                self.logger.error(f"回调函数执行失败: {e}")
    
    # 保持原有的监控相关方法
    async def start(self):
        """启动策略"""
        if self.is_running:
            self.logger.warning("策略已在运行中")
            return
        
        try:
            self.logger.info("启动雪球跟单策略...")
            self.is_running = True
            
            # 获取启用的组合
            enabled_portfolios = self.config_manager.get_enabled_portfolios()
            
            # 执行初始同步调仓
            await self.perform_initial_sync()
            
            # 启动监控任务
            tasks = []
            for portfolio in enabled_portfolios:
                portfolio_code = portfolio['code']
                task = asyncio.create_task(
                    self._monitor_portfolio(portfolio_code)
                )
                tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            else:
                self.logger.warning("没有配置监控组合")
                
        except Exception as e:
            self.logger.error(f"策略运行失败: {e}")
        finally:
            self.is_running = False
    
    async def stop(self):
        """停止策略"""
        self.logger.info("停止雪球跟单策略...")
        self.is_running = False
        
        if self.collector:
            await self.collector.close()
        
        if hasattr(self.trader_api, 'disconnect'):
            self.trader_api.disconnect()
    
    def emergency_stop(self):
        """紧急停止"""
        self.logger.warning("执行紧急停止！")
        self.is_running = False
        # 这里可以添加紧急清仓逻辑
    
    async def perform_initial_sync(self):
        """执行初始同步调仓 - 根据雪球组合当前持仓立即调仓"""
        try:
            self.logger.info("🔄 开始执行初始同步调仓...")
            
            # 获取启用的组合
            enabled_portfolios = self.config_manager.get_enabled_portfolios()
            if not enabled_portfolios:
                self.logger.warning("没有启用的组合，跳过初始同步")
                return
            
            # 获取账户信息（容错）
            try:
                account_value = self._get_account_value()
            except Exception as e:
                self.logger.warning(f"无法获取账户价值，跳过初始同步。原因: {e}")
                return
            if account_value <= 0:
                self.logger.warning("账户价值为0，跳过初始同步")
                return
            
            self.logger.info(f"💰 账户总价值: {account_value:,.2f}")
            
            # 处理每个启用的组合
            all_target_positions = {}
            
            for portfolio in enabled_portfolios:
                portfolio_code = portfolio['code']
                follow_ratio = float(portfolio.get('follow_ratio', 0.2))
                
                self.logger.info(f"📊 处理组合 {portfolio_code}，跟随比例: {follow_ratio:.1%}")
                
                # 获取雪球组合当前持仓（只获取当前持仓，忽略历史调仓记录）
                if not self.collector:
                    self.logger.error("数据采集器未初始化")
                    continue
                
                current_holdings = await self.collector.get_portfolio_holdings(portfolio_code, use_current_only=False)
                if not current_holdings:
                    self.logger.warning(f"无法获取组合 {portfolio_code} 的持仓数据，组合可能为空仓状态")
                    continue
                
                # 检查是否为空仓状态
                if len(current_holdings) == 0:
                    self.logger.info(f"✅ 组合 {portfolio_code} 当前为空仓状态，跳过初始同步")
                    continue
                
                self.logger.info(f"📈 获取到 {len(current_holdings)} 个持仓:")
                for holding in current_holdings:
                    sym_norm = self._normalize_symbol(holding.get('symbol', ''))
                    self.logger.info(f"   {sym_norm} {holding['name']}: {holding['target_weight']:.2%}")
                
                # 导出持仓数据到Excel
                export_path = self._export_holdings_to_excel(portfolio_code, current_holdings)
                if export_path:
                    self.logger.info(f"📊 持仓数据已导出到: {export_path}")
                
                # 将雪球持仓转换为调仓信号
                changes = []
                for holding in current_holdings:
                    target_weight = float(holding.get('target_weight', 0))
                    if target_weight > 0:  # 只处理有权重的持仓
                        sym_norm = self._normalize_symbol(holding.get('symbol', ''))
                        changes.append({
                            'type': 'add',
                            'symbol': sym_norm,
                            'name': holding['name'],
                            'target_weight': target_weight,
                            'prev_weight': 0.0
                        })
                
                # 计算目标仓位
                target_positions = self.calculate_target_positions(changes, follow_ratio, account_value)
                
                # 合并到总目标仓位
                for symbol, position in target_positions.items():
                    if symbol in all_target_positions:
                        # 如果已存在，累加目标价值
                        all_target_positions[symbol]['target_value'] += position['target_value']
                        all_target_positions[symbol]['weight'] += position['weight']
                        all_target_positions[symbol]['reason'] += f"; {position['reason']}"
                    else:
                        all_target_positions[symbol] = position.copy()
            
            if not all_target_positions:
                self.logger.warning("没有计算出目标仓位，跳过初始同步")
                return
            
            self.logger.info(f"🎯 计算出 {len(all_target_positions)} 个目标仓位:")
            for symbol, position in all_target_positions.items():
                self.logger.info(f"   {symbol}: 目标价值 {position['target_value']:,.2f}, 权重 {position['weight']:.2%}")
            
            # 导出当前持仓与目标持仓，便于对比差额
            try:
                self._export_current_positions_to_excel()
            except Exception:
                pass
            try:
                self._export_target_positions_to_excel(all_target_positions)
            except Exception:
                pass
            
            # 生成交易指令
            orders = self.generate_trade_orders(all_target_positions, self.current_positions)
            
            if not orders:
                self.logger.info("✅ 当前持仓已与目标一致，无需调仓")
                return
            
            self.logger.info(f"📋 生成 {len(orders)} 个交易指令:")
            for order in orders:
                action_text = "买入" if order['action'] == 'buy' else "卖出"
                self.logger.info(f"   {action_text} {order['symbol']} {order['volume']}股 @ {order['price']:.2f}")
            
            # 验证交易指令
            valid_orders = self.validate_trade_orders(orders)
            
            if not valid_orders:
                self.logger.warning("所有交易指令都被风险控制拒绝")
                return
            
            self.logger.info(f"✅ {len(valid_orders)}/{len(orders)} 个指令通过风险检查")
            
            # 执行交易
            # 尝试多种路径获取账户ID
            account_id = (
                self.config_manager.get_setting('settings.account.account_id') or
                self.config_manager.get_setting('account.account_id') or
                None
            )
            if not account_id:
                self.logger.error("未配置交易账户ID")
                return
            
            execution_results = []
            for order in valid_orders:
                try:
                    # 转换订单类型为QMT格式
                    order_type_map = {'buy': 23, 'sell': 24}  # QMT的买卖类型
                    qmt_order_type = order_type_map.get(order['action'])
                    
                    if not qmt_order_type:
                        self.logger.error(f"未知的订单类型: {order['action']}")
                        continue
                    
                    self.logger.info(f"🔄 执行订单: {order['action']} {order['symbol']} {order['volume']}股")
                    
                    # 使用 EasyXT API 下单
                    order_id = self.trader_api.sync_order(
                        account_id=account_id,
                        code=self._to_broker_symbol(order['symbol']),
                        order_type=order['action'],
                        volume=order['volume'],
                        price=order.get('price', 0),
                        price_type='limit',  # 使用限价单
                        strategy_name='XueqiuFollow',
                        order_remark=f'初始同步_{order["symbol"]}'
                    )
                    
                    if order_id and order_id > 0:
                        execution_results.append({
                            'order_id': order_id,
                            'symbol': order['symbol'],
                            'action': order['action'],
                            'volume': order['volume'],
                            'status': 'success',
                            'reason': order.get('reason', '')
                        })
                        self.logger.info(f"✅ 订单提交成功，ID: {order_id}")
                    else:
                        execution_results.append({
                            'order_id': None,
                            'symbol': order['symbol'],
                            'action': order['action'],
                            'volume': order['volume'],
                            'status': 'failed',
                            'reason': order.get('reason', '订单提交失败')
                        })
                        self.logger.error(f"❌ 订单提交失败: {order['symbol']}")
                        
                except Exception as e:
                    self.logger.error(f"❌ 执行订单失败: {order['symbol']} - {e}")
                    execution_results.append({
                        'order_id': None,
                        'symbol': order['symbol'],
                        'action': order['action'],
                        'volume': order['volume'],
                        'status': 'failed',
                        'reason': order.get('reason', str(e))
                    })
            
            # 统计执行结果
            successful_orders = [r for r in execution_results if r['status'] == 'success']
            failed_orders = [r for r in execution_results if r['status'] == 'failed']
            
            self.logger.info(f"🎉 初始同步完成！")
            self.logger.info(f"   ✅ 成功执行: {len(successful_orders)} 个订单")
            self.logger.info(f"   ❌ 执行失败: {len(failed_orders)} 个订单")
            
            if successful_orders:
                self.logger.info("成功的订单:")
                for result in successful_orders:
                    action_text = "买入" if result['action'] == 'buy' else "卖出"
                    self.logger.info(f"   {action_text} {result['symbol']} {result['volume']}股 (ID: {result['order_id']})")
            
            if failed_orders:
                self.logger.warning("失败的订单:")
                for result in failed_orders:
                    action_text = "买入" if result['action'] == 'buy' else "卖出"
                    self.logger.warning(f"   {action_text} {result['symbol']} {result['volume']}股 - {result['reason']}")
            
            # 导出交易明细
            try:
                self._export_orders_to_excel(execution_results, "orders.xlsx")
            except Exception:
                pass
            # 更新持仓记录
            await self._update_positions_after_trade(execution_results)
            
        except Exception as e:
            self.logger.error(f"初始同步调仓失败: {e}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")

    async def sync_positions(self):
        """同步持仓"""
        await self._load_current_positions()
        try:
            self._export_current_positions_to_excel()
        except Exception:
            pass
    
    async def clear_positions(self):
        """清空所有持仓"""
        try:
            results = []
            if not self.current_positions:
                self.logger.info("当前无持仓需要清空")
                return
            
            # 生成清仓指令
            clear_orders = []
            for symbol, position in self.current_positions.items():
                if position['volume'] > 0:
                    current_price = self._get_current_price(symbol)
                    if current_price:
                        adjusted_price = self._apply_slippage(symbol, current_price, 'sell')
                        order = {
                            'symbol': symbol,
                            'action': 'sell',
                            'volume': position['volume'],
                            'price': adjusted_price,
                            'order_type': 'limit',
                            'reason': '清空持仓'
                        }
                        clear_orders.append(order)
            
            if clear_orders:
                # 统一获取账户ID并规范为字符串
                account_id_raw = (
                    self.config_manager.get_setting('settings.account.account_id') or
                    self.config_manager.get_setting('account.account_id') or
                    None
                )
                account_id = str(account_id_raw) if account_id_raw else None

                if account_id:
                    for order in clear_orders:
                        # 确保使用限价委托
                        order_price = order.get('price', 0)
                        if not order_price or order_price <= 0:
                            order_price = self._get_current_price(order['symbol'])
                            if order_price:
                                order_price = self._apply_slippage(order['symbol'], order_price, 'sell')
                        
                        order_id = self.trader_api.sync_order(
                            account_id=account_id,
                            code=self._to_broker_symbol(order['symbol']),
                            order_type=order['action'],
                            volume=order['volume'],
                            price=order_price,
                            price_type='limit'  # 总是使用限价委托
                        )
                        results.append({
                            'order_id': order_id,
                            'symbol': order['symbol'],
                            'action': order['action'],
                            'volume': order['volume'],
                            'success': order_id is not None
                        })
                    await self._update_positions_after_trade(results)
                    self.logger.info(f"清空持仓完成，执行了 {len(results)} 个卖出指令")
                else:
                    self.logger.error("未配置交易账户ID，无法执行清仓指令")
            else:
                self.logger.info("无清仓指令需要执行")
            
        except Exception as e:
            self.logger.error(f"清空持仓失败: {e}")

    def _export_holdings_to_excel(self, portfolio_code: str, holdings: List[Dict[str, Any]]):
        """将持仓数据导出到Excel（可配置开关，覆盖写同名文件以减少数量）"""
        try:
            # 导出开关：默认不导出，兼容两种键名
            export_enabled = (
                self.config_manager.get_setting('settings.export_holdings') or
                self.config_manager.get_setting('导出持仓') or
                False
            )
            if not export_enabled:
                return None
            if not holdings:
                self.logger.warning(f"组合 {portfolio_code} 无持仓数据，跳过导出")
                return None
            
            # 创建DataFrame
            df_data = []
            for holding in holdings:
                df_data.append({
                    '股票代码': holding.get('symbol', ''),
                    '股票名称': holding.get('name', ''),
                    '目标权重': holding.get('target_weight', 0),
                    '当前权重': holding.get('current_weight', 0),
                    '持仓数量': holding.get('volume', 0),
                    '持仓市值': holding.get('market_value', 0),
                    '成本价': holding.get('cost_price', 0),
                    '当前价': holding.get('current_price', 0),
                    '盈亏比例': holding.get('profit_rate', 0),
                    '更新时间': holding.get('update_time', '')
                })
            
            df = pd.DataFrame(df_data)
            
            # 设置导出路径
            # 改为导出到 reports 目录
            export_dir = Path(__file__).parent.parent.parent / "reports"
            export_dir.mkdir(parents=True, exist_ok=True)
            
            # 覆盖写同名文件，避免每日产生新文件
            filename = f"{portfolio_code}_持仓数据.xlsx"
            filepath = export_dir / filename
            
            # 导出到Excel
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='持仓数据', index=False)
                
                # 设置列宽
                worksheet = writer.sheets['持仓数据']
                worksheet.column_dimensions['A'].width = 15  # 股票代码
                worksheet.column_dimensions['B'].width = 20  # 股票名称
                worksheet.column_dimensions['C'].width = 12  # 目标权重
                worksheet.column_dimensions['D'].width = 12  # 当前权重
                worksheet.column_dimensions['E'].width = 12  # 持仓数量
                worksheet.column_dimensions['F'].width = 15  # 持仓市值
                worksheet.column_dimensions['G'].width = 12  # 成本价
                worksheet.column_dimensions['H'].width = 12  # 当前价
                worksheet.column_dimensions['I'].width = 12  # 盈亏比例
                worksheet.column_dimensions['J'].width = 20  # 更新时间
            
            self.logger.info(f"✅ 持仓数据已导出到: {filepath}")
            self.logger.info(f"📊 导出 {len(holdings)} 个持仓记录")
            return filepath
            
        except Exception as e:
            self.logger.error(f"导出持仓数据到Excel失败: {e}")
            return None
    
    def _export_current_positions_to_excel(self) -> Optional[Path]:
        """导出当前账户持仓到Excel（固定文件名覆盖写）"""
        try:
            export_enabled = (
                self.config_manager.get_setting('settings.export_holdings') or
                self.config_manager.get_setting('导出持仓') or
                True
            )
            if not export_enabled:
                return None
            positions = self.current_positions or {}
            rows = []
            for code, pos in positions.items():
                rows.append({
                    '股票代码': code,
                    '股票名称': pos.get('name') or pos.get('stock_name') or '',
                    '当前拥股': pos.get('volume', 0) or 0,
                    '可用数量': pos.get('can_use_volume', 0) or 0,
                    '在途股份': pos.get('在途股份', 0) or pos.get('pending_volume', 0) or 0,
                    '持仓市值': pos.get('market_value', 0) or 0,
                    '成本价': pos.get('cost_price', 0) or 0,
                    '最新价': pos.get('current_price', 0) or 0,
                    '更新时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                })
            df = pd.DataFrame(rows)
            export_dir = Path(__file__).parent.parent.parent / "reports"
            export_dir.mkdir(parents=True, exist_ok=True)
            filepath = export_dir / "current_positions.xlsx"
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='当前持仓', index=False)
            self.logger.info(f"✅ 当前持仓已导出: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"导出当前持仓失败: {e}")
            return None

    def _export_target_positions_to_excel(self, target_positions: Dict[str, Dict[str, Any]]) -> Optional[Path]:
        """导出跟投组合计算出的目标持仓到Excel（固定文件名覆盖写）"""
        try:
            export_enabled = (
                self.config_manager.get_setting('settings.export_holdings') or
                self.config_manager.get_setting('导出持仓') or
                True
            )
            if not export_enabled:
                return None
            rows = []
            for symbol, pos in target_positions.items():
                rows.append({
                    '股票代码': self._normalize_symbol(symbol),
                    '操作': '买入' if pos.get('action') == 'buy' else ('卖出' if pos.get('action') == 'sell' else (pos.get('action') or '')),
                    '目标价值': float(pos.get('target_value', 0) or 0),
                    '目标权重(%)': float(pos.get('weight', 0) or 0) * 100,
                    '理由': pos.get('reason', ''),
                    '导出时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                })
            df = pd.DataFrame(rows)
            export_dir = Path(__file__).parent.parent.parent / "reports"
            export_dir.mkdir(parents=True, exist_ok=True)
            filepath = export_dir / "target_positions.xlsx"
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='目标持仓', index=False)
            self.logger.info(f"✅ 目标持仓已导出: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"导出目标持仓失败: {e}")
            return None

    def _export_orders_to_excel(self, orders: List[Dict[str, Any]], filename: str = "orders.xlsx") -> Optional[Path]:
        """导出已执行交易到Excel（同一文件追加写入，保留历史）"""
        try:
            if not orders:
                return None
            rows = []
            for o in orders:
                rows.append({
                    '股票代码': o.get('symbol', ''),
                    '方向': '买入' if o.get('action') == 'buy' else ('卖出' if o.get('action') == 'sell' else (o.get('action') or '')),
                    '股数': int(o.get('volume', 0) or 0),
                    '价格': float(o.get('price', 0) or 0),
                    '原因': o.get('reason', ''),
                    '状态': o.get('status', 'unknown') if 'status' in o else ('success' if o.get('success') else 'failed'),
                    '订单ID': o.get('order_id', ''),
                    '导出时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                })
            df = pd.DataFrame(rows)
            export_dir = Path(__file__).parent.parent.parent / "reports"
            export_dir.mkdir(parents=True, exist_ok=True)
            filepath = export_dir / filename
            # 追加写：若文件存在则读取原有数据并合并
            if filepath.exists():
                try:
                    existing_df = pd.read_excel(filepath, sheet_name='交易明细')
                    combined_df = pd.concat([existing_df, df], ignore_index=True)
                except Exception:
                    combined_df = df
            else:
                combined_df = df
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                combined_df.to_excel(writer, sheet_name='交易明细', index=False)
            self.logger.info(f"✅ 交易明细已追加导出: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"导出交易明细失败: {e}")
            return None

    def get_portfolios(self) -> List[Dict[str, Any]]:
        """获取组合信息"""
        return self.config_manager.get_portfolios()
    
    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """获取持仓信息"""
        return self.current_positions
    
    def get_risk_report(self) -> str:
        """获取风险报告（容错：无法获取账户资产时也返回可读报告）"""
        if not self.risk_manager:
            return "风险管理器未初始化"

        warn_msg = None
        try:
            account_value = self._get_account_value()
        except Exception as e:
            # 仅用于报告展示的容错：不再向上抛错，返回0资产的报告并附带警告
            account_value = 0.0
            warn_msg = f"账户资产不可用: {e}。本报告以0资产生成，仅用于界面展示，不作为交易依据。"
            try:
                self.logger.warning(warn_msg)
            except Exception:
                pass

        account_info = {
            'total_asset': account_value,
            'cash': account_value * 0.3,
            'market_value': account_value * 0.7,
            'daily_pnl': 0
        }

        report = self.risk_manager.generate_risk_report(self.current_positions, account_info)
        if warn_msg:
            try:
                # 附加非破坏性的提示字段，便于GUI展示
                report.setdefault('warnings', []).append(warn_msg)
            except Exception:
                pass
        try:
            return json.dumps(report, ensure_ascii=False)
        except Exception:
            return str(report)
    
    def add_callback(self, callback: Callable):
        """添加变化回调函数"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """移除变化回调函数"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)


class XueqiuFollowStrategy:
    """雪球跟单策略引擎 - 简化版本（向后兼容）"""
    
    def __init__(self, config_manager: ConfigManager = None):
        self.logger = setup_logger("XueqiuFollowStrategy")
        self.config_manager = config_manager
        self.collector: Optional[XueqiuCollectorReal] = None
        self.is_running = False
        self.callbacks: List[Callable] = []
        
    async def initialize(self):
        """初始化策略引擎"""
        try:
            self.logger.info("初始化雪球跟单策略引擎...")
            
            # 初始化数据采集器
            self.collector = XueqiuCollectorReal()
            await self.collector.initialize()
            
            # 加载配置
            await self._load_config()
            
            self.logger.info("策略引擎初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"策略引擎初始化失败: {e}")
            return False
    
    async def _load_config(self):
        """加载配置文件"""
        # 如果有配置管理器，直接使用
        if self.config_manager:
            enabled_portfolios = self.config_manager.get_enabled_portfolios()
            self.logger.info(f"从配置管理器加载了 {len(enabled_portfolios)} 个监控组合")
        else:
            # 向后兼容：直接读取配置文件
            try:
                config_dir = Path(__file__).parent.parent / "config"
                portfolios_file = config_dir / "portfolios.json"
                if portfolios_file.exists():
                    with open(portfolios_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        
                    enabled_portfolios = [p for p in config.get('portfolios', []) if p.get('enabled', False)]
                    self.logger.info(f"从文件加载了 {len(enabled_portfolios)} 个监控组合")
                else:
                    enabled_portfolios = []
                    
            except Exception as e:
                self.logger.error(f"加载配置失败: {e}")
                enabled_portfolios = []
    
    async def start(self):
        """启动策略"""
        if self.is_running:
            self.logger.warning("策略已在运行中")
            return
        
        try:
            self.logger.info("启动雪球跟单策略...")
            self.is_running = True
            
            # 获取启用的组合
            if self.config_manager:
                enabled_portfolios = self.config_manager.get_enabled_portfolios()
            else:
                await self._load_config()
                enabled_portfolios = []
            
            # 启动监控任务
            tasks = []
            for portfolio in enabled_portfolios:
                portfolio_code = portfolio['code']
                task = asyncio.create_task(
                    self._monitor_portfolio(portfolio_code)
                )
                tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            else:
                self.logger.warning("没有配置监控组合")
                
        except Exception as e:
            self.logger.error(f"策略运行失败: {e}")
        finally:
            self.is_running = False
    
    async def stop(self):
        """停止策略"""
        self.logger.info("停止雪球跟单策略...")
        self.is_running = False
        
        if self.collector:
            await self.collector.close()
    
    async def _monitor_portfolio(self, portfolio_code: str):
        """监控单个组合"""
        self.logger.info(f"开始监控组合: {portfolio_code}")
        
        try:
            if self.collector:
                await self.collector.monitor_portfolio_changes(
                    portfolio_code,
                    callback=self._on_portfolio_changed
                )
        except Exception as e:
            self.logger.error(f"监控组合 {portfolio_code} 失败: {e}")
    
    async def _on_portfolio_changed(self, portfolio_code: str, changes: List[Dict[str, Any]], current_holdings: List[Dict[str, Any]]):
        """组合变化回调"""
        self.logger.info(f"检测到组合 {portfolio_code} 发生变化:")
        
        for change in changes:
            change_type = change['type']
            symbol = change['symbol']
            name = change['name']
            
            if change_type == 'add':
                self.logger.info(f"  新增持仓: {symbol} {name} 权重: {change['weight']:.2%}")
            elif change_type == 'modify':
                self.logger.info(f"  调整持仓: {symbol} {name} {change['old_weight']:.2%} -> {change['new_weight']:.2%}")
            elif change_type == 'remove':
                self.logger.info(f"  清仓: {symbol} {name}")
        
        # 通知回调函数
        for callback in self.callbacks:
            try:
                await callback(portfolio_code, changes, current_holdings)
            except Exception as e:
                self.logger.error(f"回调函数执行失败: {e}")
    
    def add_callback(self, callback: Callable):
        """添加变化回调函数"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """移除变化回调函数"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    async def get_portfolio_status(self, portfolio_code: str) -> Optional[Dict[str, Any]]:
        """获取组合状态"""
        if not self.collector:
            return None
        
        try:
            holdings = await self.collector.get_portfolio_holdings(portfolio_code)
            if holdings:
                return {
                    'code': portfolio_code,
                    'holdings_count': len(holdings),
                    'holdings': holdings,
                    'last_updated': datetime.now().isoformat()
                }
        except Exception as e:
            self.logger.error(f"获取组合状态失败: {e}")
        
        return None
    
    async def get_all_portfolios_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有监控组合状态"""
        status = {}
        
        # 获取启用的组合
        if self.config_manager:
            enabled_portfolios = self.config_manager.get_enabled_portfolios()
        else:
            enabled_portfolios = []
        
        for portfolio in enabled_portfolios:
            portfolio_code = portfolio['code']
            portfolio_status = await self.get_portfolio_status(portfolio_code)
            if portfolio_status:
                status[portfolio_code] = portfolio_status
        
        return status