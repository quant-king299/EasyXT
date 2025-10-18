"""
统一数据接口

提供统一的数据访问接口，屏蔽不同数据源的差异。
"""

from typing import Dict, List, Any, Optional, Union
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from .providers.base_provider import BaseDataProvider
from .providers.tdx_provider import TdxDataProvider
from .providers.ths_provider import ThsDataProvider
from .providers.eastmoney_provider import EastmoneyDataProvider
from .config import RealtimeDataConfig
from .cache import CacheManager


@dataclass
class DataSourceStatus:
    """数据源状态"""
    name: str
    connected: bool
    available: bool
    last_update: float
    error_count: int
    response_time: float


class UnifiedDataAPI:
    """统一数据接口
    
    整合多个数据源，提供统一的数据访问接口。
    支持数据源优先级、故障切换、负载均衡等功能。
    """
    
    def __init__(self, config: Optional[RealtimeDataConfig] = None):
        """初始化统一数据接口
        
        Args:
            config: 配置对象
        """
        self.config = config or RealtimeDataConfig()
        self.logger = logging.getLogger(__name__)
        
        # 初始化缓存管理器
        if self.config.get('cache_enabled', True):
            self.cache_manager = CacheManager(self.config.get_cache_config())
            self.logger.info("缓存管理器已启用")
        else:
            self.cache_manager = None
            self.logger.info("缓存管理器已禁用")
        
        # 初始化数据源提供者
        self.providers: Dict[str, BaseDataProvider] = {}
        self._init_providers()
        
        # 数据源状态跟踪
        self.source_status: Dict[str, DataSourceStatus] = {}
        self._init_status_tracking()
        
        # 配置参数
        self.max_workers = getattr(self.config, 'max_workers', 3)
        self.timeout = getattr(self.config, 'timeout', 10)
        self.retry_count = getattr(self.config, 'retry_count', 2)
        
    def _init_providers(self):
        """初始化数据源提供者"""
        try:
            # 通达信数据源
            if self.config.is_provider_enabled('tdx'):
                tdx_config = self.config.get_provider_config('tdx')
                self.providers['tdx'] = TdxDataProvider(tdx_config)
                self.logger.info("通达信数据源初始化成功")
            
            # 同花顺数据源
            if self.config.is_provider_enabled('ths'):
                ths_config = self.config.get_provider_config('ths')
                self.providers['ths'] = ThsDataProvider(ths_config)
                self.logger.info("同花顺数据源初始化成功")
            
            # 东方财富数据源
            if self.config.is_provider_enabled('eastmoney'):
                em_config = self.config.get_provider_config('eastmoney')
                self.providers['eastmoney'] = EastmoneyDataProvider(em_config)
                self.logger.info("东方财富数据源初始化成功")
                
        except Exception as e:
            self.logger.error(f"初始化数据源提供者失败: {e}")
    
    def _init_status_tracking(self):
        """初始化状态跟踪"""
        for name, provider in self.providers.items():
            self.source_status[name] = DataSourceStatus(
                name=name,
                connected=False,
                available=False,
                last_update=0,
                error_count=0,
                response_time=0
            )
    
    def connect_all(self) -> Dict[str, bool]:
        """连接所有数据源
        
        Returns:
            Dict[str, bool]: 各数据源连接结果
        """
        results = {}
        
        for name, provider in self.providers.items():
            try:
                start_time = time.time()
                success = provider.connect()
                response_time = time.time() - start_time
                
                results[name] = success
                
                # 更新状态
                status = self.source_status[name]
                status.connected = success
                status.available = success
                status.last_update = time.time()
                status.response_time = response_time
                
                if success:
                    status.error_count = 0
                    self.logger.info(f"{name}数据源连接成功，响应时间: {response_time:.2f}s")
                else:
                    status.error_count += 1
                    self.logger.warning(f"{name}数据源连接失败")
                    
            except Exception as e:
                results[name] = False
                status = self.source_status[name]
                status.connected = False
                status.available = False
                status.error_count += 1
                self.logger.error(f"{name}数据源连接异常: {e}")
        
        return results
    
    def disconnect_all(self):
        """断开所有数据源连接"""
        for name, provider in self.providers.items():
            try:
                provider.disconnect()
                status = self.source_status[name]
                status.connected = False
                status.available = False
                self.logger.info(f"{name}数据源已断开连接")
            except Exception as e:
                self.logger.error(f"断开{name}数据源连接失败: {e}")
    
    def get_available_providers(self, data_type: str = None) -> List[str]:
        """获取可用的数据源列表
        
        Args:
            data_type: 数据类型筛选
            
        Returns:
            List[str]: 可用数据源名称列表
        """
        available = []
        
        for name, provider in self.providers.items():
            status = self.source_status[name]
            
            # 检查基本可用性
            if not (status.connected and status.available):
                continue
            
            # 检查数据类型支持
            if data_type:
                provider_info = provider.get_provider_info()
                supported_types = provider_info.get('supported_data_types', [])
                
                if data_type == 'realtime_quotes':
                    if '实时行情' not in supported_types:
                        continue
                elif data_type == 'hot_stocks':
                    if name not in ['ths', 'eastmoney']:  # 只有同花顺和东方财富支持
                        continue
                elif data_type == 'concept_data':
                    if name not in ['ths', 'eastmoney']:
                        continue
            
            available.append(name)
        
        # 按优先级和响应时间排序
        available.sort(key=lambda x: (
            self.source_status[x].error_count,  # 错误次数越少越优先
            self.source_status[x].response_time  # 响应时间越短越优先
        ))
        
        return available
    
    def get_realtime_quotes(self, codes: List[str], 
                          preferred_source: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取实时行情数据
        
        Args:
            codes: 股票代码列表
            preferred_source: 首选数据源
            
        Returns:
            List[Dict]: 实时行情数据
        """
        # 尝试从缓存获取
        if self.cache_manager:
            cache_key = f"quotes_{preferred_source or 'auto'}_{'_'.join(sorted(codes))}"
            cached_result = self.cache_manager.get(cache_key, "realtime_quotes")
            if cached_result:
                self.logger.debug(f"从缓存获取行情数据: {len(codes)}个股票")
                return cached_result
        
        # 确定数据源优先级
        available_sources = self.get_available_providers('realtime_quotes')
        
        if preferred_source and preferred_source in available_sources:
            # 将首选数据源移到最前面
            available_sources.remove(preferred_source)
            available_sources.insert(0, preferred_source)
        
        if not available_sources:
            self.logger.error("没有可用的实时行情数据源")
            return []
        
        # 尝试获取数据
        for source_name in available_sources:
            try:
                provider = self.providers[source_name]
                start_time = time.time()
                
                quotes = provider.get_realtime_quotes(codes)
                
                if quotes:
                    # 更新状态
                    status = self.source_status[source_name]
                    status.last_update = time.time()
                    status.response_time = time.time() - start_time
                    status.error_count = 0
                    
                    # 缓存结果
                    if self.cache_manager:
                        cache_key = f"quotes_{preferred_source or 'auto'}_{'_'.join(sorted(codes))}"
                        self.cache_manager.set(cache_key, quotes, "realtime_quotes")
                    
                    self.logger.info(f"从{source_name}成功获取{len(quotes)}条实时行情")
                    return quotes
                
            except Exception as e:
                # 更新错误状态
                status = self.source_status[source_name]
                status.error_count += 1
                
                self.logger.warning(f"从{source_name}获取实时行情失败: {e}")
                
                # 如果错误次数过多，暂时标记为不可用
                if status.error_count >= 3:
                    status.available = False
                    self.logger.warning(f"{source_name}数据源暂时不可用")
        
        self.logger.error("所有数据源都无法获取实时行情")
        return []
    
    def get_hot_stocks(self, market: str = 'all', count: int = 50,
                      data_type: str = '大家都在看') -> List[Dict[str, Any]]:
        """获取热门股票数据
        
        Args:
            market: 市场类型
            count: 获取数量
            data_type: 数据类型
            
        Returns:
            List[Dict]: 热门股票数据
        """
        # 尝试从缓存获取
        if self.cache_manager:
            cache_key = f"hot_stocks_{market}_{count}_{data_type}"
            cached_result = self.cache_manager.get(cache_key, "hot_stocks")
            if cached_result:
                self.logger.debug(f"从缓存获取热门股票: {count}个")
                return cached_result
        
        # 优先使用同花顺，备选东方财富
        available_sources = self.get_available_providers('hot_stocks')
        
        # 同花顺优先
        if 'ths' in available_sources:
            available_sources.remove('ths')
            available_sources.insert(0, 'ths')
        
        for source_name in available_sources:
            try:
                provider = self.providers[source_name]
                
                if source_name == 'ths':
                    # 同花顺热股排行
                    hot_stocks = provider.get_hot_stock_rank(data_type, count)
                elif source_name == 'eastmoney':
                    # 东方财富热门股票
                    hot_stocks = provider.get_hot_stocks(market, count)
                else:
                    continue
                
                if hot_stocks:
                    # 缓存结果
                    if self.cache_manager:
                        cache_key = f"hot_stocks_{market}_{count}_{data_type}"
                        self.cache_manager.set(cache_key, hot_stocks, "hot_stocks")
                    
                    self.logger.info(f"从{source_name}成功获取{len(hot_stocks)}条热门股票")
                    return hot_stocks
                
            except Exception as e:
                self.logger.warning(f"从{source_name}获取热门股票失败: {e}")
        
        return []
    
    def get_concept_data(self, count: int = 50) -> List[Dict[str, Any]]:
        """获取概念数据
        
        Args:
            count: 获取数量
            
        Returns:
            List[Dict]: 概念数据
        """
        # 尝试从缓存获取
        if self.cache_manager:
            cache_key = f"concept_data_{count}"
            cached_result = self.cache_manager.get(cache_key, "concept_data")
            if cached_result:
                self.logger.debug(f"从缓存获取概念数据: {count}个")
                return cached_result
        
        # 优先使用同花顺，备选东方财富
        available_sources = self.get_available_providers('concept_data')
        
        # 同花顺优先
        if 'ths' in available_sources:
            available_sources.remove('ths')
            available_sources.insert(0, 'ths')
        
        for source_name in available_sources:
            try:
                provider = self.providers[source_name]
                
                if source_name == 'ths':
                    # 同花顺概念排行
                    concepts = provider.get_concept_rank(count)
                elif source_name == 'eastmoney':
                    # 东方财富概念板块
                    concepts = provider.get_sector_data('concept')
                else:
                    continue
                
                if concepts:
                    # 缓存结果
                    if self.cache_manager:
                        cache_key = f"concept_data_{count}"
                        self.cache_manager.set(cache_key, concepts, "concept_data")
                    
                    self.logger.info(f"从{source_name}成功获取{len(concepts)}条概念数据")
                    return concepts
                
            except Exception as e:
                self.logger.warning(f"从{source_name}获取概念数据失败: {e}")
        
        return []
    
    def get_market_status(self) -> Dict[str, Any]:
        """获取市场状态
        
        Returns:
            Dict: 市场状态信息
        """
        # 优先使用通达信，备选东方财富
        available_sources = self.get_available_providers()
        
        # 通达信优先
        if 'tdx' in available_sources:
            available_sources.remove('tdx')
            available_sources.insert(0, 'tdx')
        
        for source_name in available_sources:
            try:
                provider = self.providers[source_name]
                
                if hasattr(provider, 'get_market_status'):
                    status = provider.get_market_status()
                    if status:
                        self.logger.info(f"从{source_name}成功获取市场状态")
                        return status
                
            except Exception as e:
                self.logger.warning(f"从{source_name}获取市场状态失败: {e}")
        
        return {
            'market_status': 'unknown',
            'timestamp': int(time.time()),
            'source': 'unified_api'
        }
    
    def get_multi_source_data(self, codes: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """并行获取多数据源数据
        
        Args:
            codes: 股票代码列表
            
        Returns:
            Dict: 各数据源的数据结果
        """
        results = {}
        available_sources = self.get_available_providers('realtime_quotes')
        
        if not available_sources:
            return results
        
        # 使用线程池并行获取
        with ThreadPoolExecutor(max_workers=min(len(available_sources), self.max_workers)) as executor:
            # 提交任务
            future_to_source = {}
            for source_name in available_sources:
                provider = self.providers[source_name]
                future = executor.submit(provider.get_realtime_quotes, codes)
                future_to_source[future] = source_name
            
            # 收集结果
            for future in as_completed(future_to_source, timeout=self.timeout):
                source_name = future_to_source[future]
                try:
                    data = future.result()
                    if data:
                        results[source_name] = data
                        self.logger.info(f"{source_name}并行获取数据成功: {len(data)}条")
                except Exception as e:
                    self.logger.warning(f"{source_name}并行获取数据失败: {e}")
        
        return results
    
    def get_source_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有数据源状态
        
        Returns:
            Dict: 数据源状态信息
        """
        status_info = {}
        
        for name, status in self.source_status.items():
            provider = self.providers.get(name)
            provider_info = provider.get_provider_info() if provider else {}
            
            status_info[name] = {
                'name': status.name,
                'connected': status.connected,
                'available': status.available,
                'last_update': status.last_update,
                'error_count': status.error_count,
                'response_time': status.response_time,
                'provider_info': provider_info
            }
        
        return status_info
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查
        
        Returns:
            Dict: 健康状态信息
        """
        total_sources = len(self.providers)
        available_sources = len(self.get_available_providers())
        
        health_status = {
            'overall_status': 'healthy' if available_sources > 0 else 'unhealthy',
            'total_sources': total_sources,
            'available_sources': available_sources,
            'availability_rate': available_sources / total_sources if total_sources > 0 else 0,
            'timestamp': int(time.time()),
            'sources': self.get_source_status()
        }
        
        return health_status


# 导出类供外部使用
__all__ = ['UnifiedDataAPI', 'DataSourceStatus']