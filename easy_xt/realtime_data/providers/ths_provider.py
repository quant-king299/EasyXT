"""
同花顺数据提供者

基于HTTP请求实现的同花顺数据接口，支持热度排行和概念数据获取。
参考综合自定义交易系统v5.5.7.6.5项目的成熟实现。
"""

import requests
import json
import time
import random
from typing import List, Dict, Any, Optional
import logging
from urllib.parse import urlencode
from .base_provider import BaseDataProvider

logger = logging.getLogger(__name__)


class ThsDataProvider(BaseDataProvider):
    """同花顺数据提供者
    
    提供同花顺热度排行、概念数据等接口。
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化同花顺数据提供者
        
        Args:
            config: 配置字典，包含URL、请求头等设置
        """
        super().__init__("ths")
        self.config = config or {}
        self.session = requests.Session()
        self.base_url = self.config.get('base_url', 'http://data.10jqka.com.cn')
        self.timeout = self.config.get('timeout', 15)
        self.retry_count = self.config.get('retry_count', 2)
        
        # 设置请求头
        headers = self.config.get('headers', {})
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'http://data.10jqka.com.cn/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache'
        }
        default_headers.update(headers)
        self.session.headers.update(default_headers)
        
        # 热度数据类型映射（基于参考项目）
        self.hot_data_types = {
            '大家都在看': 'normal',
            '快速飙升中': 'skyrocket',
            '技术交易派': 'tech',
            '价值投资派': 'value',
            '趋势投资派': 'trend'
        }
    
    def connect(self) -> bool:
        """连接到同花顺服务
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 测试连接
            response = self.session.get(
                f"{self.base_url}/",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                self.connected = True
                self.logger.info("同花顺服务连接成功")
                return True
            else:
                self.logger.error(f"同花顺服务连接失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"同花顺服务连接异常: {e}")
            return False
    
    def disconnect(self) -> None:
        """断开连接"""
        try:
            self.session.close()
            self.connected = False
            self.logger.info("同花顺服务连接已断开")
        except Exception as e:
            self.logger.error(f"断开同花顺服务连接异常: {e}")
    
    def _make_request(self, url: str, params: Optional[Dict] = None, 
                     method: str = 'GET') -> Optional[requests.Response]:
        """发起HTTP请求
        
        Args:
            url: 请求URL
            params: 请求参数
            method: 请求方法
            
        Returns:
            Response对象或None
        """
        for attempt in range(self.retry_count):
            try:
                # 添加随机延迟，避免被限流
                if attempt > 0:
                    time.sleep(random.uniform(1, 3))
                
                if method.upper() == 'GET':
                    response = self.session.get(
                        url, 
                        params=params, 
                        timeout=self.timeout
                    )
                else:
                    response = self.session.post(
                        url, 
                        data=params, 
                        timeout=self.timeout
                    )
                
                if response.status_code == 200:
                    return response
                else:
                    self.logger.warning(f"请求失败，状态码: {response.status_code}")
                    
            except Exception as e:
                self.logger.error(f"请求异常 (尝试 {attempt + 1}/{self.retry_count}): {e}")
                
        return None
    
    def get_hot_stock_rank(self, data_type: str = '大家都在看', 
                          count: int = 50) -> List[Dict[str, Any]]:
        """获取热股排行
        
        Args:
            data_type: 数据类型 ('大家都在看', '快速飙升中', '技术交易派', '价值投资派', '趋势投资派')
            count: 获取数量
            
        Returns:
            List[Dict]: 热股排行数据
        """
        try:
            # 数据类型映射（基于参考项目的实际API）
            data_dict = {
                '大家都在看': 'normal',
                '快速飙升中': 'skyrocket',
                '技术交易派': 'tech',
                '价值投资派': 'value',
                '趋势投资派': 'trend'
            }
            
            list_type = data_dict.get(data_type, 'normal')
            
            # 根据类型确定时间参数
            if list_type in ['normal', 'skyrocket']:
                time_type = 'hour'
            else:
                time_type = 'day'
            
            # 构建请求URL（使用参考项目的实际API）
            url = 'https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock'
            
            params = {
                'stock_type': 'a',
                'type': time_type,
                'list_type': list_type,
                'data_type': '1'
            }
            
            response = self._make_request(url, params)
            if not response:
                return []
            
            # 解析JSON响应
            data = response.json()
            
            if data.get('status_code') == 0 and 'data' in data:
                stocks = []
                items = data['data'].get('stock_list', [])[:count]
                
                for i, item in enumerate(items):
                    stock_info = {
                        'rank': i + 1,
                        'code': item.get('stock_code', ''),
                        'name': item.get('stock_name', ''),
                        'hot_value': float(item.get('hot_value', 0)),
                        'price': float(item.get('price', 0)),
                        'change_pct': float(item.get('change_percent', 0)),
                        'data_type': data_type,
                        'timestamp': int(time.time()),
                        'source': 'ths'
                    }
                    stocks.append(stock_info)
                
                self.logger.info(f"成功获取{data_type}排行数据: {len(stocks)}条")
                return stocks
            
            return []
            
        except Exception as e:
            self.logger.error(f"获取热股排行失败: {e}")
            return []
    
    def get_concept_rank(self, count: int = 50) -> List[Dict[str, Any]]:
        """获取概念热度排行
        
        Args:
            count: 获取数量
            
        Returns:
            List[Dict]: 概念排行数据
        """
        try:
            # 使用同花顺板块API（基于参考项目）
            url = 'https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/plate'
            
            params = {
                'type': 'concept'
            }
            
            response = self._make_request(url, params)
            if not response:
                return []
            
            # 解析JSON响应
            data = response.json()
            
            if data.get('status_code') == 0 and 'data' in data:
                concepts = []
                items = data['data'].get('plate_list', [])[:count]
                
                for i, item in enumerate(items):
                    concept_info = {
                        'rank': i + 1,
                        'concept_code': item.get('code', ''),
                        'concept_name': item.get('name', ''),
                        'hot_value': float(item.get('hot_value', 0)),
                        'change_pct': float(item.get('change_percent', 0)),
                        'stock_count': int(item.get('stock_count', 0)),
                        'timestamp': int(time.time()),
                        'source': 'ths'
                    }
                    concepts.append(concept_info)
                
                self.logger.info(f"成功获取概念热度排行: {len(concepts)}条")
                return concepts
            
            return []
            
        except Exception as e:
            self.logger.error(f"获取概念排行失败: {e}")
            return []
    
    def get_realtime_quotes(self, codes: List[str]) -> List[Dict[str, Any]]:
        """获取实时行情数据（同花顺不是主要行情源，返回空列表）
        
        Args:
            codes: 股票代码列表
            
        Returns:
            List[Dict]: 空列表（同花顺主要用于热度数据）
        """
        self.logger.info("同花顺数据源主要用于热度数据，不提供实时行情")
        return []
    
    def get_sector_stocks(self, sector_name: str, count: int = 50) -> List[Dict[str, Any]]:
        """获取板块成分股
        
        Args:
            sector_name: 板块名称
            count: 获取数量
            
        Returns:
            List[Dict]: 板块成分股数据
        """
        try:
            # 构建板块查询URL
            url = f"{self.base_url}/v2/line/bk_{sector_name}/last.js"
            
            response = self._make_request(url)
            if not response:
                return []
            
            text = response.text
            
            # 解析JSONP响应
            if 'last(' in text and text.endswith(')'):
                json_str = text[text.find('(') + 1:-1]
                data = json.loads(json_str)
                
                if 'data' in data and data['data']:
                    stocks = []
                    items = data['data'][:count]
                    
                    for item in items:
                        if isinstance(item, str):
                            parts = item.split(',')
                            if len(parts) >= 2:
                                stock_info = {
                                    'code': parts[0],
                                    'name': parts[1],
                                    'sector': sector_name,
                                    'timestamp': int(time.time()),
                                    'source': 'ths'
                                }
                                stocks.append(stock_info)
                    
                    self.logger.info(f"成功获取板块{sector_name}成分股: {len(stocks)}只")
                    return stocks
            
            return []
            
        except Exception as e:
            self.logger.error(f"获取板块成分股失败: {e}")
            return []
    
    def get_market_sentiment(self) -> Dict[str, Any]:
        """获取市场情绪数据
        
        Returns:
            Dict: 市场情绪指标
        """
        try:
            # 获取多个热度数据来分析市场情绪
            hot_stocks = self.get_hot_stock_rank('实时热度', 20)
            concept_rank = self.get_concept_rank(10)
            
            if not hot_stocks and not concept_rank:
                return {}
            
            # 计算市场情绪指标
            sentiment = {
                'hot_stock_count': len(hot_stocks),
                'hot_concept_count': len(concept_rank),
                'avg_hot_value': 0,
                'top_concepts': [],
                'timestamp': int(time.time()),
                'source': 'ths'
            }
            
            # 计算平均热度值
            if hot_stocks:
                total_hot = sum(stock.get('hot_value', 0) for stock in hot_stocks)
                sentiment['avg_hot_value'] = round(total_hot / len(hot_stocks), 2)
            
            # 获取热门概念
            if concept_rank:
                sentiment['top_concepts'] = [
                    {
                        'name': concept['concept_name'],
                        'hot_value': concept['hot_value']
                    }
                    for concept in concept_rank[:5]
                ]
            
            return sentiment
            
        except Exception as e:
            self.logger.error(f"获取市场情绪数据失败: {e}")
            return {}
    
    def is_available(self) -> bool:
        """检查数据源是否可用
        
        Returns:
            bool: 数据源是否可用
        """
        try:
            # 尝试获取少量数据来测试可用性
            test_data = self.get_hot_stock_rank('大家都在看', 5)
            return len(test_data) > 0
        except Exception:
            return False
    
    def get_provider_info(self) -> Dict[str, Any]:
        """获取数据提供者信息
        
        Returns:
            Dict: 提供者信息
        """
        info = super().get_provider_info()
        info.update({
            'base_url': self.base_url,
            'supported_data_types': list(self.hot_data_types.keys()),
            'features': ['热度排行', '概念数据', '板块成分股', '市场情绪']
        })
        return info