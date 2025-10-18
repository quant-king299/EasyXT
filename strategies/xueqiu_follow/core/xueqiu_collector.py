"""
雪球数据采集器
负责从雪球网站采集组合持仓和调仓信息
"""

import asyncio
import aiohttp
import json
import time
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode
import logging

try:
    from strategies.xueqiu_follow.utils.logger import setup_logger
except ImportError:
    # 如果相对导入失败，使用绝对导入
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from ..utils.logger import setup_logger
try:
    from ..utils.crypto_utils import generate_signature
except ImportError:
    # 如果相对导入失败，使用绝对导入或跳过
    def generate_signature(*args, **kwargs):
        return "mock_signature"
from ..utils.rate_limiter import RateLimiter


class XueqiuCollector:
    """雪球数据采集器"""
    
    def __init__(self):
        self.logger = setup_logger("XueqiuCollector")
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = RateLimiter(max_requests=30, time_window=60)  # 每分钟最多30次请求
        
        # 雪球API配置
        self.base_url = "https://xueqiu.com"
        self.api_base = "https://stock.xueqiu.com"
        
        # 请求头配置
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://xueqiu.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        }
        
        # Cookie和认证信息
        self.cookies = {}
        self.token = None
        
    async def initialize(self):
        """初始化采集器"""
        try:
            self.logger.info("初始化雪球数据采集器...")
            
            # 创建HTTP会话
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.headers
            )
            
            # 获取初始认证信息
            await self._get_initial_auth()
            
            self.logger.info("雪球数据采集器初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"采集器初始化失败: {e}")
            return False
    
    async def _get_initial_auth(self):
        """获取初始认证信息"""
        try:
            # 访问首页获取Cookie
            async with self.session.get(self.base_url) as response:
                if response.status == 200:
                    # 提取token
                    text = await response.text()
                    token_match = re.search(r'window\.TOKEN\s*=\s*["\']([^"\']+)["\']', text)
                    if token_match:
                        self.token = token_match.group(1)
                        self.headers['X-Requested-With'] = 'XMLHttpRequest'
                        self.logger.info("获取认证token成功")
                    
                    # 更新cookies
                    for cookie in response.cookies:
                        if hasattr(cookie, 'key') and hasattr(cookie, 'value'):
                            self.cookies[cookie.key] = cookie.value
                        elif hasattr(cookie, 'name') and hasattr(cookie, 'value'):
                            self.cookies[cookie.name] = cookie.value
                        
        except Exception as e:
            self.logger.warning(f"获取认证信息失败: {e}")
    
    async def get_portfolio_info(self, portfolio_code: str) -> Optional[Dict[str, Any]]:
        """获取组合基本信息"""
        await self.rate_limiter.acquire()
        
        try:
            url = f"{self.api_base}/v1/cubes/nav_daily/all.json"
            params = {
                'cube_symbol': portfolio_code,
                'since': int((datetime.now() - timedelta(days=30)).timestamp() * 1000),
                'until': int(datetime.now().timestamp() * 1000)
            }
            
            async with self.session.get(url, params=params, cookies=self.cookies) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('error_code') == 0:
                        return data.get('list', [])
                    else:
                        self.logger.error(f"API返回错误: {data.get('error_description')}")
                else:
                    self.logger.error(f"请求失败，状态码: {response.status}")
                    
        except Exception as e:
            self.logger.error(f"获取组合信息失败: {e}")
        
        return None
    
    async def get_portfolio_holdings(self, portfolio_code: str) -> Optional[List[Dict[str, Any]]]:
        """获取组合当前持仓"""
        await self.rate_limiter.acquire()
        
        try:
            url = f"{self.api_base}/v1/cubes/rebalancing/history.json"
            params = {
                'cube_symbol': portfolio_code,
                'count': 20,
                'page': 1
            }
            
            async with self.session.get(url, params=params, cookies=self.cookies) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('error_code') == 0:
                        rebalancings = data.get('list', [])
                        if rebalancings:
                            # 获取最新调仓记录的持仓
                            latest_rebalancing = rebalancings[0]
                            return await self._parse_holdings(latest_rebalancing)
                    else:
                        self.logger.error(f"API返回错误: {data.get('error_description')}")
                else:
                    self.logger.error(f"请求失败，状态码: {response.status}")
                    
        except Exception as e:
            self.logger.error(f"获取组合持仓失败: {e}")
        
        return None
    
    async def _parse_holdings(self, rebalancing_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析持仓数据"""
        holdings = []
        
        try:
            rebalancing_histories = rebalancing_data.get('rebalancing_histories', [])
            
            for history in rebalancing_histories:
                stock_symbol = history.get('stock_symbol', '')
                stock_name = history.get('stock_name', '')
                target_weight = history.get('target_weight', 0)
                prev_weight = history.get('prev_weight', 0)
                
                # 只保留目标权重大于0的持仓
                if target_weight > 0:
                    holding = {
                        'symbol': stock_symbol,
                        'name': stock_name,
                        'target_weight': target_weight / 100.0,  # 转换为小数
                        'prev_weight': prev_weight / 100.0,
                        'weight_change': (target_weight - prev_weight) / 100.0,
                        'updated_at': rebalancing_data.get('updated_at')
                    }
                    holdings.append(holding)
            
            self.logger.info(f"解析到 {len(holdings)} 个持仓")
            return holdings
            
        except Exception as e:
            self.logger.error(f"解析持仓数据失败: {e}")
            return []
    
    async def get_rebalancing_history(self, portfolio_code: str, days: int = 7) -> List[Dict[str, Any]]:
        """获取调仓历史"""
        await self.rate_limiter.acquire()
        
        try:
            url = f"{self.api_base}/v1/cubes/rebalancing/history.json"
            params = {
                'cube_symbol': portfolio_code,
                'count': 50,
                'page': 1
            }
            
            async with self.session.get(url, params=params, cookies=self.cookies) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('error_code') == 0:
                        rebalancings = data.get('list', [])
                        
                        # 过滤指定天数内的调仓记录
                        cutoff_time = datetime.now() - timedelta(days=days)
                        recent_rebalancings = []
                        
                        for rebalancing in rebalancings:
                            created_at = rebalancing.get('created_at')
                            if created_at and datetime.fromtimestamp(created_at / 1000) > cutoff_time:
                                recent_rebalancings.append(rebalancing)
                        
                        self.logger.info(f"获取到 {len(recent_rebalancings)} 条近期调仓记录")
                        return recent_rebalancings
                    else:
                        self.logger.error(f"API返回错误: {data.get('error_description')}")
                else:
                    self.logger.error(f"请求失败，状态码: {response.status}")
                    
        except Exception as e:
            self.logger.error(f"获取调仓历史失败: {e}")
        
        return []
    
    async def monitor_portfolio_changes(self, portfolio_code: str, callback=None) -> bool:
        """监控组合变化"""
        self.logger.info(f"开始监控组合 {portfolio_code} 的变化...")
        
        last_holdings = None
        last_check_time = None
        
        while True:
            try:
                # 获取当前持仓
                current_holdings = await self.get_portfolio_holdings(portfolio_code)
                current_time = datetime.now()
                
                if current_holdings is not None:
                    # 检查是否有变化
                    if last_holdings is not None:
                        changes = self._detect_changes(last_holdings, current_holdings)
                        if changes and callback:
                            await callback(portfolio_code, changes, current_holdings)
                    
                    last_holdings = current_holdings
                    last_check_time = current_time
                    
                    self.logger.debug(f"组合 {portfolio_code} 检查完成，持仓数量: {len(current_holdings)}")
                else:
                    self.logger.warning(f"获取组合 {portfolio_code} 持仓失败")
                
                # 等待下次检查（30秒间隔）
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error(f"监控组合变化时发生错误: {e}")
                await asyncio.sleep(60)  # 错误时等待更长时间
    
    def _detect_changes(self, old_holdings: List[Dict], new_holdings: List[Dict]) -> List[Dict]:
        """检测持仓变化"""
        changes = []
        
        # 创建持仓字典便于比较
        old_dict = {h['symbol']: h for h in old_holdings}
        new_dict = {h['symbol']: h for h in new_holdings}
        
        # 检查新增和变化的持仓
        for symbol, new_holding in new_dict.items():
            if symbol not in old_dict:
                # 新增持仓
                changes.append({
                    'type': 'add',
                    'symbol': symbol,
                    'name': new_holding['name'],
                    'weight': new_holding['target_weight'],
                    'change': new_holding['target_weight']
                })
            else:
                old_holding = old_dict[symbol]
                weight_diff = new_holding['target_weight'] - old_holding['target_weight']
                if abs(weight_diff) > 0.001:  # 权重变化超过0.1%
                    changes.append({
                        'type': 'modify',
                        'symbol': symbol,
                        'name': new_holding['name'],
                        'old_weight': old_holding['target_weight'],
                        'new_weight': new_holding['target_weight'],
                        'change': weight_diff
                    })
        
        # 检查删除的持仓
        for symbol, old_holding in old_dict.items():
            if symbol not in new_dict:
                changes.append({
                    'type': 'remove',
                    'symbol': symbol,
                    'name': old_holding['name'],
                    'weight': 0,
                    'change': -old_holding['target_weight']
                })
        
        return changes
    
    async def close(self):
        """关闭采集器"""
        if self.session:
            await self.session.close()
            self.logger.info("雪球数据采集器已关闭")


# 使用示例
async def main():
    collector = XueqiuCollector()
    
    try:
        await collector.initialize()
        
        # 测试获取组合信息
        portfolio_code = "ZH000000"  # 示例组合代码
        holdings = await collector.get_portfolio_holdings(portfolio_code)
        
        if holdings:
            print(f"组合 {portfolio_code} 当前持仓:")
            for holding in holdings:
                print(f"  {holding['symbol']} {holding['name']}: {holding['target_weight']:.2%}")
        
    finally:
        await collector.close()


if __name__ == "__main__":
    asyncio.run(main())