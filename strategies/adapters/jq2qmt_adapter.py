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

# 添加JQ2QMT路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'jq2qmt', 'src'))

try:
    from api.jq_qmt_api import JQQMTAPI
except ImportError:
    JQQMTAPI = None
    print("警告: JQ2QMT API未找到，请确保已正确克隆jq2qmt项目")

from .data_converter import DataConverter


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
        """检查适配器是否可用"""
        return self.jq2qmt_api is not None
    
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
        """
        获取指定策略的持仓信息
        
        Args:
            strategy_name: 策略名称
        
        Returns:
            List[Dict]: EasyXT格式的持仓列表，失败时返回None
        """
        if not self.is_available():
            return None
        
        try:
            # 这里需要调用JQ2QMT的查询接口
            # 由于当前JQQMTAPI类没有查询方法，我们需要直接调用HTTP API
            import requests
            
            url = f"{self.config['server_url']}/api/v1/positions/strategy/{strategy_name}"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                jq2qmt_positions = data.get('positions', [])
                
                # 转换为EasyXT格式
                easyxt_positions = DataConverter.jq2qmt_to_easyxt(jq2qmt_positions)
                return easyxt_positions
            else:
                self.logger.error(f"查询策略持仓失败: {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"查询策略持仓异常: {e}")
            return None
    
    def get_total_positions(self, strategy_names: Optional[List[str]] = None) -> Optional[List[Dict]]:
        """
        获取合并后的总持仓
        
        Args:
            strategy_names: 策略名称列表，None表示获取所有策略
        
        Returns:
            List[Dict]: EasyXT格式的合并持仓列表
        """
        if not self.is_available():
            return None
        
        try:
            import requests
            
            url = f"{self.config['server_url']}/api/v1/positions/total"
            params = {}
            if strategy_names:
                params['strategies'] = ','.join(strategy_names)
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                jq2qmt_positions = data.get('positions', [])
                
                # 转换为EasyXT格式
                easyxt_positions = DataConverter.jq2qmt_to_easyxt_total(jq2qmt_positions)
                return easyxt_positions
            else:
                self.logger.error(f"查询总持仓失败: {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"查询总持仓异常: {e}")
            return None
    
    def get_all_strategies(self) -> Optional[List[Dict]]:
        """
        获取所有策略的持仓信息
        
        Returns:
            List[Dict]: 所有策略信息列表
                [
                    {
                        'strategy_name': '策略名称',
                        'positions': [...],  # EasyXT格式持仓
                        'update_time': '2024-01-01 12:00:00'
                    }
                ]
        """
        if not self.is_available():
            return None
        
        try:
            import requests
            
            url = f"{self.config['server_url']}/api/v1/positions/all"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                strategies = data.get('strategies', [])
                
                # 转换每个策略的持仓格式
                result = []
                for strategy in strategies:
                    easyxt_positions = DataConverter.jq2qmt_to_easyxt(strategy['positions'])
                    result.append({
                        'strategy_name': strategy['strategy_name'],
                        'positions': easyxt_positions,
                        'update_time': strategy['update_time']
                    })
                
                return result
            else:
                self.logger.error(f"查询所有策略失败: {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"查询所有策略异常: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        测试与JQ2QMT服务器的连接
        
        Returns:
            bool: 连接是否正常
        """
        if not self.is_available():
            return False
        
        try:
            import requests
            
            url = f"{self.config['server_url']}/api/v1/auth/info"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                self.logger.info("JQ2QMT服务器连接正常")
                return True
            else:
                self.logger.error(f"JQ2QMT服务器连接失败: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"JQ2QMT服务器连接异常: {e}")
            return False
    
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