#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EasyXT与JQ2QMT集成适配器
提供EasyXT策略与JQ2QMT服务器的无缝集成
"""

import sys
import os
import time
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

# 添加 qka 包路径以便导入
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'jq2qmt'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'jq2qmt', 'qka'))

from .data_converter import DataConverter
from .order_converter import OrderConverter

# 尝试导入QMTClient，如果不存在则设为None
try:
    from qka.client import QMTClient
except ImportError:
    QMTClient = None


class EasyXTJQ2QMTAdapter:
    """EasyXT与JQ2QMT集成适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化适配器
        
        Args:
            config: JQ2QMT配置字典
                {
                    'server_url': 'http://localhost:5366',
                    'auth_config': {
                        'use_crypto_auth': True,
                        'private_key_file': 'keys/easyxt_private.pem',
                        'client_id': 'easyxt_client'
                    },
                    'sync_settings': {
                        'auto_sync': True,
                        'sync_interval': 30,
                        'retry_times': 3
                    }
                }
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # 初始化qka客户端（如果启用）
        self.qka_client = None
        self._init_qka_client()
        
        # 同步设置
        self.sync_settings = config.get('sync_settings', {})
        self.auto_sync = self.sync_settings.get('auto_sync', True)
        self.sync_interval = self.sync_settings.get('sync_interval', 30)
        self.retry_times = self.sync_settings.get('retry_times', 3)
        
        # 状态跟踪
        self.last_sync_time = None
        self.sync_status = 'idle'  # idle, syncing, success, error
        self.last_error = None
        
        self.logger.info("EasyXT-JQ2QMT适配器初始化完成")
    
    def _init_qka_client(self):
        """初始化qka客户端"""
        if QMTClient is None:
            self.logger.warning("QMTClient不可用，请检查qka包是否正确安装")
            return
            
        try:
            qka_settings = self.config.get('qka_settings', {})
            if qka_settings.get('enabled', False):
                base_url = qka_settings.get('base_url', 'http://localhost:8000')
                token = qka_settings.get('token', '')
                
                if base_url and token:
                    self.qka_client = QMTClient(base_url=base_url, token=token)
                    self.logger.info("qka客户端初始化成功")
                else:
                    self.logger.warning("qka配置不完整，缺少base_url或token")
            else:
                self.logger.info("qka模式未启用")
        except Exception as e:
            self.logger.error(f"qka客户端初始化失败: {e}")
            self.qka_client = None
    
    def is_available(self) -> bool:
        """检查适配器是否可用（qka 模式）"""
        return getattr(self, 'qka_client', None) is not None
    
    def get_strategy_positions(self, strategy_name: str) -> Optional[List[Dict]]:
        """在 qka 模式下，直接查询账户资产/持仓，并返回 EasyXT 格式"""
        if not self.is_available() or self.qka_client is None:
            return None
        try:
            data = self.qka_client.api('query_stock_asset')  # qka 返回资产与持仓结构
            # 预期 data 可能包含 holdings 列表，每项至少有 stock_code/volume/cost 或等价字段
            jq2qmt_positions = []
            holdings = data.get('holdings') or data.get('positions') or []
            for h in holdings:
                jq2qmt_positions.append({
                    'code': h.get('stock_code') or h.get('code'),
                    'name': h.get('name', ''),
                    'volume': int(h.get('volume') or h.get('position', 0)),
                    'cost': float(h.get('cost') or h.get('avg_price') or 0.0)
                })
            return DataConverter.jq2qmt_to_easyxt(jq2qmt_positions)
        except Exception as e:
            self.logger.error(f"qka 查询持仓失败: {e}")
            return None
    
    def get_total_positions(self, strategy_names: Optional[List[str]] = None) -> Optional[List[Dict]]:
        """qka 模式下的总持仓与账户资产查询，返回 EasyXT 格式"""
        if not self.is_available() or self.qka_client is None:
            return None
        try:
            data = self.qka_client.api('query_stock_asset')
            jq2qmt_positions = []
            holdings = data.get('holdings') or data.get('positions') or []
            for h in holdings:
                jq2qmt_positions.append({
                    'code': h.get('stock_code') or h.get('code'),
                    'name': h.get('name', ''),
                    'volume': int(h.get('volume') or h.get('position', 0)),
                    'cost': float(h.get('cost') or h.get('avg_price') or 0.0)
                })
            return DataConverter.jq2qmt_to_easyxt_total(jq2qmt_positions)
        except Exception as e:
            self.logger.error(f"qka 查询总持仓失败: {e}")
            return None
    
    def get_all_strategies(self) -> Optional[List[Dict]]:
        """qka-only 模式不再区分多策略，返回当前账户的单一持仓信息列表"""
        result = []
        positions = self.get_total_positions() or []
        result.append({
            'strategy_name': 'QKA_ACCOUNT',
            'positions': positions,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        return result
    
    def test_connection(self) -> bool:
        """测试与 qka FastAPI 服务器的连接（校验 token 可用）"""
        if not self.is_available() or self.qka_client is None:
            return False
        try:
            # 调用一个轻量接口，比如查询资产（若存在）。若无，尝试访问基座 /api/query_stock_asset
            resp = self.qka_client.api('query_stock_asset')
            self.logger.info("qka 服务器连接正常")
            return True
        except Exception as e:
            self.logger.error(f"qka 服务器连接失败: {e}")
            return False
    
    def submit_orders(self, orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        提交订单到服务端：
        - 若 order_settings.mode == 'qka' 且启用 qka_settings，则调用 qka FastAPI 接口 /api/order_stock 按单下发
        """
        if not self.is_available() or self.qka_client is None:
            return {"success": False, "message": "qka client not available"}
        try:
            import requests
            order_settings = self.config.get('order_settings', {})
            mode = order_settings.get('mode', '').lower()
            if mode == 'qka' and self.config.get('qka_settings', {}).get('enabled'):
                # 使用 qka 模式：逐单调用 /api/order_stock
                qka_cfg = self.config.get('qka_settings', {})
                base_url = qka_cfg.get('base_url', 'http://localhost:8000').rstrip('/')
                token = qka_cfg.get('token')
                if not token:
                    return {"success": False, "message": "qka token missing"}
                headers = {"Content-Type": "application/json", "X-Token": token}
                results: List[Dict[str, Any]] = []
                # xtconstant 映射
                try:
                    from xtquant import xtconstant
                except Exception:
                    xtconstant = None
                for od in orders:
                    code = od.get('code') or od.get('symbol')
                    volume = int(od.get('volume') or od.get('quantity') or 0)
                    is_buy = (od.get('direction', '').upper() == 'BUY')
                    is_limit = (od.get('order_type', '').upper() == 'LIMIT')
                    price = float(od.get('price') or 0.0)
                    # 使用默认值而不是xtconstant
                    order_type = 23 if is_buy else 24
                    price_type = 0 if is_limit else 1
                    if xtconstant:
                        order_type = xtconstant.STOCK_BUY if is_buy else xtconstant.STOCK_SELL
                        price_type = xtconstant.FIX_PRICE if is_limit else xtconstant.LATEST_PRICE
                    payload = {
                        'stock_code': code,
                        'order_type': order_type,
                        'order_volume': volume,
                        'price_type': price_type,
                        'price': price
                    }
                    resp = requests.post(f"{base_url}/api/order_stock", json=payload, headers=headers, timeout=int(order_settings.get('timeout', 10)))
                    ok = (resp.status_code == 200)
                    data = resp.json() if ok else {"detail": resp.text}
                    results.append({"ok": ok, "status": resp.status_code, "data": data})
                return {"success": all(r.get('ok') for r in results), "results": results}
            else:
                return {"success": False, "message": "qka mode not enabled"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_sync_status(self) -> Dict[str, Any]:
        """
        获取同步状态信息
        
        Returns:
            Dict: 同步状态信息
        """
        return {
            'status': self.sync_status,
            'last_sync_time': self.last_sync_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_sync_time else None,
            'last_error': self.last_error,
            'auto_sync': self.auto_sync,
            'sync_interval': self.sync_interval,
            'is_available': self.is_available()
        }
    
    def set_auto_sync(self, enabled: bool):
        """设置自动同步开关"""
        self.auto_sync = enabled
        self.logger.info(f"自动同步已{'启用' if enabled else '禁用'}")
    
    def set_sync_interval(self, interval: int):
        """设置同步间隔"""
        self.sync_interval = max(10, interval)  # 最小10秒
        self.logger.info(f"同步间隔设置为 {self.sync_interval} 秒")


class JQ2QMTManager:
    """JQ2QMT管理器 - 管理多个适配器实例"""
    
    def __init__(self):
        self.adapters = {}  # strategy_name -> adapter
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def add_adapter(self, strategy_name: str, config: Dict[str, Any]) -> bool:
        """
        为策略添加JQ2QMT适配器
        
        Args:
            strategy_name: 策略名称
            config: JQ2QMT配置
        
        Returns:
            bool: 是否添加成功
        """
        try:
            adapter = EasyXTJQ2QMTAdapter(config)
            if adapter.is_available():
                self.adapters[strategy_name] = adapter
                self.logger.info(f"策略 {strategy_name} 的JQ2QMT适配器添加成功")
                return True
            else:
                self.logger.error(f"策略 {strategy_name} 的JQ2QMT适配器不可用")
                return False
        except Exception as e:
            self.logger.error(f"添加JQ2QMT适配器失败: {e}")
            return False
    
    def remove_adapter(self, strategy_name: str):
        """移除策略的JQ2QMT适配器"""
        if strategy_name in self.adapters:
            del self.adapters[strategy_name]
            self.logger.info(f"策略 {strategy_name} 的JQ2QMT适配器已移除")
    
    def get_adapter(self, strategy_name: str) -> Optional[EasyXTJQ2QMTAdapter]:
        """获取策略的JQ2QMT适配器"""
        return self.adapters.get(strategy_name)
    
    def sync_all_strategies(self) -> Dict[str, bool]:
        """同步所有策略的持仓"""
        results = {}
        for strategy_name, adapter in self.adapters.items():
            # 这里需要获取策略的当前持仓
            # 实际实现时需要与EasyXT的策略系统集成
            results[strategy_name] = False  # 占位符
        return results
    
    def get_all_sync_status(self) -> Dict[str, Dict]:
        """获取所有适配器的同步状态"""
        status = {}
        for strategy_name, adapter in self.adapters.items():
            status[strategy_name] = adapter.get_sync_status()
        return status


# 全局JQ2QMT管理器实例
jq2qmt_manager = JQ2QMTManager()