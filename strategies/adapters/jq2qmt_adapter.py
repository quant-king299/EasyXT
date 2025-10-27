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
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'jq2qmt', 'qka'))
from qka.client import QMTClient

from .data_converter import DataConverter
from .order_converter import OrderConverter


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
        
        # 初始化JQ2QMT API客户端
        self.jq2qmt_api = None
        self._init_jq2qmt_api()
        
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
    
    def _init_jq2qmt_api(self):
        """初始化JQ2QMT API客户端"""
        if JQQMTAPI is None:
            self.logger.error("JQ2QMT API不可用，请检查jq2qmt项目是否正确安装")
            return
        
        try:
            auth_config = self.config.get('auth_config', {})
            
            self.jq2qmt_api = JQQMTAPI(
                api_url=self.config.get('server_url', 'http://localhost:5366'),
                private_key_file=auth_config.get('private_key_file'),
                client_id=auth_config.get('client_id', 'easyxt_client'),
                use_crypto_auth=auth_config.get('use_crypto_auth', True),
                simple_api_key=auth_config.get('simple_api_key')
            )
            
            self.logger.info("JQ2QMT API客户端初始化成功")
            
        except Exception as e:
            self.logger.error(f"JQ2QMT API客户端初始化失败: {e}")
            self.jq2qmt_api = None
    
    def is_available(self) -> bool:
        """检查适配器是否可用（qka 模式）"""
        return getattr(self, 'qka_client', None) is not None
    
    def sync_positions_to_qmt(self, strategy_name: str, positions: List[Dict]) -> bool:
        """
        将EasyXT策略持仓同步到QMT
        
        Args:
            strategy_name: 策略名称
            positions: EasyXT格式的持仓列表
                [
                    {
                        'symbol': '000001.SZ',
                        'name': '平安银行',
                        'quantity': 1000,
                        'avg_price': 12.50
                    }
                ]
        
        Returns:
            bool: 同步是否成功
        """
        if not self.is_available():
            self.logger.error("JQ2QMT适配器不可用")
            return False
        
        self.sync_status = 'syncing'
        self.last_error = None
        
        try:
            # 转换持仓格式
            jq2qmt_positions = DataConverter.easyxt_to_jq2qmt(positions)
            
            # 重试机制
            for attempt in range(self.retry_times):
                try:
                    result = self.jq2qmt_api.update_positions(strategy_name, jq2qmt_positions)
                    
                    self.sync_status = 'success'
                    self.last_sync_time = datetime.now()
                    
                    self.logger.info(f"策略 {strategy_name} 持仓同步成功: {len(jq2qmt_positions)} 个持仓")
                    return True
                    
                except Exception as e:
                    self.logger.warning(f"同步尝试 {attempt + 1}/{self.retry_times} 失败: {e}")
                    if attempt < self.retry_times - 1:
                        time.sleep(1)  # 重试前等待1秒
                    else:
                        raise e
        
        except Exception as e:
            self.sync_status = 'error'
            self.last_error = str(e)
            self.logger.error(f"策略 {strategy_name} 持仓同步失败: {e}")
            return False
    
    def get_strategy_positions(self, strategy_name: str) -> Optional[List[Dict]]:
        """在 qka 模式下，直接查询账户资产/持仓，并返回 EasyXT 格式"""
        if not self.is_available():
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
        if not self.is_available():
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
        if not self.is_available():
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
        - 否则，走自有 JQ2QMT 提交端点 /api/v1/orders/submit 批量提交
        """
        if not self.is_available():
            return {"success": False, "message": "adapter not available"}
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
                    payload = {
                        'stock_code': code,
                        'order_type': (xtconstant.STOCK_BUY if is_buy else xtconstant.STOCK_SELL) if xtconstant else (23 if is_buy else 24),
                        'order_volume': volume,
                        'price_type': (xtconstant.FIX_PRICE if is_limit else xtconstant.MARKET_PRICE) if xtconstant else (0 if is_limit else 1),
                        'price': price
                    }
                    resp = requests.post(f"{base_url}/api/order_stock", json=payload, headers=headers, timeout=int(order_settings.get('timeout', 10)))
                    ok = (resp.status_code == 200)
                    data = resp.json() if ok else {"detail": resp.text}
                    results.append({"ok": ok, "status": resp.status_code, "data": data})
                return {"success": all(r.get('ok') for r in results), "results": results}
            else:
                # 默认走 JQ2QMT 批量提交端点
                base_url = self.config.get('server_url', '').rstrip('/')
                endpoint = order_settings.get('endpoint', '/api/v1/orders/submit')
                timeout = int(order_settings.get('timeout', 10))
                url = f"{base_url}{endpoint}"
                headers = {"Content-Type": "application/json"}
                simple_api_key = self.config.get('auth_config', {}).get('simple_api_key')
                if simple_api_key:
                    headers['X-API-Key'] = simple_api_key
                resp = requests.post(url, json={"orders": orders}, headers=headers, timeout=timeout)
                if resp.status_code == 200:
                    return {"success": True, "data": resp.json()}
                else:
                    return {"success": False, "status": resp.status_code, "message": resp.text}
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