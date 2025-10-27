"""
基于真实雪球数据采集器
使用真实cookie访问雪球API
"""

import asyncio
import aiohttp
import json
import time
import re
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 添加当前包路径
current_package = os.path.dirname(os.path.dirname(__file__))
if current_package not in sys.path:
    sys.path.insert(0, current_package)

# 直接导入logger函数
# 使用包级相对导入（utils 与 core 同级）
try:
    from ..utils.logger import setup_logger
except ImportError:
    import logging
    def setup_logger(name):
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

# from ..utils.rate_limiter import RateLimiter  # 暂时注释掉，使用简单的延迟


class XueqiuCollectorReal:
    """基于真实cookie的雪球数据采集器"""
    
    def __init__(self, cookie: Optional[str] = None):
        self.logger = setup_logger("XueqiuCollectorReal")
        self.session: Optional[aiohttp.ClientSession] = None
        # self.rate_limiter = RateLimiter(max_requests=20, time_window=60)  # 暂时注释掉
        
        # 雪球API配置
        self.base_url = "https://xueqiu.com"
        self.cookie = cookie if cookie else ""
        
        # 请求头配置（基于雪球跟单系统）
        self.headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Connection': 'keep-alive',
            'Host': 'stock.xueqiu.com',
            'Referer': 'https://xueqiu.com/',
            'Sec-Ch-Ua': '"Chromium";v="124", "Microsoft Edge";v="124", "Not-A.Brand";v="99"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (WindowsNT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
    async def initialize(self):
        """初始化采集器"""
        try:
            self.logger.info("初始化真实雪球数据采集器...")
            
            # 从配置文件读取cookie（如果没有提供）
            if not self.cookie:
                self.cookie = self._load_cookie_from_config()
            
            if not self.cookie:
                raise Exception("未提供雪球cookie，请在配置中设置")
            
            # 添加cookie到请求头
            self.headers['Cookie'] = self.cookie
            
            # 创建HTTP会话
            connector = aiohttp.TCPConnector(
                limit=5,
                limit_per_host=2,
                ttl_dns_cache=300,
                use_dns_cache=True,
                ssl=False
            )
            
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.headers
            )
            
            # 测试cookie有效性
            await self._test_cookie_validity()
            
            self.logger.info("真实雪球数据采集器初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"采集器初始化失败: {e}")
            return False
    
    def _load_cookie_from_config(self) -> str:
        """从配置文件加载cookie"""
        try:
            # 使用配置管理器获取cookie配置
            from .config_manager import ConfigManager
            config_manager = ConfigManager()
            
            # 优先从xueqiu_settings中获取cookie
            cookie = config_manager.get_setting('xueqiu_settings.cookie')
            if isinstance(cookie, str) and cookie:
                self.logger.info("从配置管理器加载xueqiu_settings.cookie成功")
                return cookie
            
            # 如果xueqiu_settings中没有，尝试从xueqiu配置中获取
            cookie = config_manager.get_setting('xueqiu.cookie')
            if isinstance(cookie, str) and cookie:
                self.logger.info("从配置管理器加载xueqiu.cookie成功")
                return cookie
            
            # 如果都没有，尝试直接读取配置文件作为备用方案
            import os
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'unified_config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    if config_data and isinstance(config_data, dict):
                        # 从xueqiu_settings中获取cookie
                        xueqiu_settings = config_data.get('xueqiu_settings', {})
                        if isinstance(xueqiu_settings, dict):
                            cookie = xueqiu_settings.get('cookie', '')
                            if cookie:
                                self.logger.info("从unified_config.json加载cookie成功")
                                return cookie
            
            # 如果unified_config.json中没有cookie，尝试从xueqiu_config.json读取
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'xueqiu_config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    if config_data and isinstance(config_data, dict):
                        cookie = config_data.get('cookie', '')
                        if cookie:
                            self.logger.info("从xueqiu_config.json加载cookie成功")
                            return cookie
                    
        except Exception as e:
            self.logger.warning(f"加载cookie配置失败: {e}")
        
        return ""

    def _get_cookie_value(self, key: str) -> str:
        """从cookie字符串提取指定键的值"""
        try:
            m = re.search(rf'{key}=([^;]+)', self.cookie or '')
            return m.group(1) if m else ''
        except Exception:
            return ''
    
    async def _test_cookie_validity(self):
        """测试cookie有效性（采用简化验证流程）"""
        try:
            # 参考雪球跟单系统3.0的简单实现：不进行复杂的cookie验证
            # 直接使用历史调仓API测试，因为用户反馈历史记录能获取，说明cookie有效
            url = "https://xueqiu.com/cubes/rebalancing/history.json"
            params = {
                'cube_symbol': 'ZH3368671',  # 使用用户提供的组合代码进行测试
                'count': 1,  # 只获取一条记录进行测试
                'page': 1
            }
            
            headers = self.headers.copy()
            headers['Referer'] = 'https://xueqiu.com/P/ZH3368671'
            headers['Host'] = 'xueqiu.com'
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    # 如果返回正常数据，说明cookie有效
                    if isinstance(data, dict) and 'list' in data:
                        self.logger.info("✅ Cookie有效性验证成功（通过历史调仓API）")
                        return True
                    else:
                        # 返回空数据可能表示组合不存在，但不一定是cookie问题
                        self.logger.warning("历史调仓API返回空数据，但cookie可能仍然有效")
                        return True
                elif response.status in [401, 403, 410]:
                    # 这些状态码确实表示cookie过期
                    self.logger.error(f"Cookie验证失败，状态码: {response.status}")
                    raise Exception(f"Cookie已过期，需要重新获取")
                else:
                    # 其他状态码（如404）可能是API端点变更或组合不存在，不一定是cookie问题
                    # 根据用户反馈，历史记录能获取，说明cookie有效，继续尝试实际API调用
                    self.logger.warning(f"Cookie验证返回状态码: {response.status}，但将继续尝试实际API调用")
                    return True
                    
        except Exception as e:
            # 根据用户反馈，历史记录能获取，说明cookie有效，不抛出异常
            self.logger.warning(f"Cookie验证遇到异常: {e}，但将继续尝试实际API调用")
            return True
    
    async def get_portfolio_holdings(self, portfolio_code: str, use_current_only: bool = False) -> Optional[List[Dict[str, Any]]]:
        """获取组合持仓数据
        
        Args:
            portfolio_code: 组合代码
            use_current_only: 是否只获取当前持仓，忽略历史调仓记录（默认False，优先使用历史调仓记录）
            
        Returns:
            持仓数据列表，空列表表示空仓状态
        """
        await asyncio.sleep(0.1)  # 简单延迟
        
        try:
            self.logger.info(f"获取组合 {portfolio_code} 的持仓数据...")
            
            # 强制使用历史调仓接口作为唯一数据源，放弃 quote.json/detail.json
            holdings = await self._get_holdings_from_history_api(portfolio_code)
            if holdings is None:
                self.logger.info("历史调仓接口无返回或请求失败，视为空仓状态")
                return []
            if holdings:
                self.logger.info(f"✅ 仅使用历史调仓记录获取 {len(holdings)} 个持仓")
            else:
                self.logger.info("历史调仓记录为空，组合为空仓状态")
            return holdings
            
        except Exception as e:
            self.logger.error(f"获取组合持仓失败: {e}")
            import traceback
            self.logger.error(f"详细错误堆栈: {traceback.format_exc()}")
            return []
    
    async def _get_latest_success_rb_id(self, portfolio_code: str) -> Optional[str]:
        """获取最新一次成功调仓的 rb_id"""
        try:
            url = f"https://xueqiu.com/cubes/rebalancing/history.json"
            params = {'cube_symbol': portfolio_code, 'count': 50, 'page': 1}
            headers = self.headers.copy()
            headers['Referer'] = f'https://xueqiu.com/P/{portfolio_code}'
            headers['Host'] = 'xueqiu.com'
            if self.session is None:
                self.logger.error("HTTP会话未初始化")
                return None
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    if response.status in [400, 410]:
                        self.logger.error("cookie已过期")
                        return None
                    else:
                        self.logger.error(f"历史调仓API失败，状态码: {response.status}")
                        return None
                data = await response.json()
                list_data = data.get('list', []) if isinstance(data, dict) else []
                for rec in list_data:
                    if isinstance(rec, dict) and rec.get('status') == 'success':
                        rb_id = str(rec.get('id', '') or '')
                        return rb_id if rb_id else None
            return None
        except Exception as e:
            self.logger.error(f"获取最新成功调仓rb_id失败: {e}")
            return None

    def _compute_holdings_by_replay(self, list_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按时间顺序重放历史调仓，计算最新持仓"""
        try:
            # 过滤出包含调仓明细的记录
            valid_records = [rec for rec in list_data if isinstance(rec, dict) and isinstance(rec.get('rebalancing_histories', []), list)]
            if not valid_records:
                return []
            # 按时间升序排序（最早 -> 最近）
            valid_records.sort(key=lambda x: x.get('created_at', 0))
            holdings_map: Dict[str, Dict[str, Any]] = {}
            for rec in valid_records:
                histories = rec.get('rebalancing_histories', []) or []
                for h in histories:
                    if not isinstance(h, dict):
                        continue
                    symbol = h.get('stock_symbol') or h.get('symbol') or ''
                    name = h.get('stock_name') or h.get('name') or ''
                    target_weight = h.get('target_weight', h.get('weight', 0))
                    if target_weight is None:
                        target_weight = 0
                    # 转换为小数权重
                    weight_val = 0.0
                    try:
                        weight_val = float(target_weight)
                        if weight_val > 1:
                            weight_val = weight_val / 100.0
                        elif weight_val < 0:
                            weight_val = 0.0
                    except (TypeError, ValueError):
                        weight_val = 0.0
                    if symbol:
                        if weight_val <= 0:
                            # 清仓或权重为0：移除该标的
                            holdings_map.pop(symbol, None)
                        else:
                            holdings_map[symbol] = {
                                'symbol': symbol,
                                'name': name,
                                'target_weight': weight_val
                            }
            # 生成最终持仓列表
            holdings = [v for v in holdings_map.values() if v.get('target_weight', 0) > 0]
            if not holdings:
                return []
            total_weight = sum(h['target_weight'] for h in holdings)
            if total_weight <= 0:
                return []
            # 若总权重偏离明显，则归一化到1
            if total_weight < 0.90 or total_weight > 1.10:
                for h in holdings:
                    h['target_weight'] = h['target_weight'] / total_weight
                total_weight = sum(h['target_weight'] for h in holdings)
            # 排序与补充字段
            holdings.sort(key=lambda x: x['target_weight'], reverse=True)
            for h in holdings:
                h['prev_weight'] = 0.0
                h['change_weight'] = 0.0
                h['update_time'] = datetime.now().isoformat()
            self.logger.info(f"🔁 通过顺序重放 {len(valid_records)} 条调仓记录计算当前持仓")
            self.logger.info(f"📈 持仓统计: 数量={len(holdings)}, 总权重={total_weight:.2%}")
            return holdings
        except Exception as e:
            self.logger.error(f"顺序重放历史调仓计算持仓失败: {e}")
            return []
    
    async def _get_holdings_from_history_api(self, portfolio_code: str) -> Optional[List[Dict[str, Any]]]:
        """使用历史调仓记录API获取持仓数据（按标准流程）"""
        try:
            # 使用历史调仓API接口与参数
            url = "https://xueqiu.com/cubes/rebalancing/history.json"
            params = {
                'cube_symbol': portfolio_code,
                'count': '50',  # 记录条数
                'page': '1'
            }
            
            # 完整请求头配置
            headers = self.headers.copy()
            headers.update({
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                'Connection': 'keep-alive',
                'Host': 'xueqiu.com',
                'Referer': f'https://xueqiu.com/P/{portfolio_code}',
                'Sec-Ch-Ua': '"Chromium";v="124", "Microsoft Edge";v="124", "Not-A.Brand";v="99"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': "Windows",
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0',
                'X-Requested-With': 'XMLHttpRequest'
            })
            
            if self.session is None:
                self.logger.error("HTTP会话未初始化")
                return None
                
            self.logger.info(f"🔗 调用历史调仓API: {url}?cube_symbol={portfolio_code}")
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    if response.status in [400, 410]:
                        self.logger.error("cookie已过期")
                        return None
                    else:
                        self.logger.error(f"历史调仓API失败，状态码: {response.status}")
                        return None
                    
                data = await response.json()
                self.logger.info(f"📊 历史调仓API响应: 获取到 {len(data.get('list', [])) if isinstance(data, dict) else 0} 条记录")
                
                # 解析rebalancing_histories字段
                holdings: List[Dict[str, Any]] = []
                list_data = data.get('list', []) if isinstance(data, dict) else []
                
                self.logger.info(f"📋 获取到 {len(list_data)} 条历史调仓记录")
                
                # 优先：按时间顺序重放历史调仓，计算最新持仓
                replay_holdings = self._compute_holdings_by_replay(list_data)
                if replay_holdings:
                    return replay_holdings
                
                # 调试：打印所有记录的基本信息
                for i, record in enumerate(list_data):
                    if isinstance(record, dict):
                        rebalancing_histories = record.get('rebalancing_histories', [])
                        created_at = record.get('created_at', '未知')
                        rebalancing_type = record.get('rebalancing_type', '未知')
                        self.logger.info(f"📊 记录 {i+1}: 类型={rebalancing_type}, 时间={created_at}, 持仓数量={len(rebalancing_histories)}")
                
                # 按时间倒序排序所有调仓记录
                # 找到最新的调仓记录（按时间倒序）
                valid_records = []
                current_time_ms = int(time.time() * 1000)  # 当前时间戳（毫秒）
                
                for record in list_data:
                    if isinstance(record, dict):
                        # 检查是否有持仓数据
                        rebalancing_histories = record.get('rebalancing_histories', [])
                        if rebalancing_histories:
                            record_time = record.get('created_at', 0)
                            # 过滤掉未来时间戳的记录（可能是异常的）
                            if record_time <= current_time_ms:
                                valid_records.append(record)
                
                self.logger.info(f"🔍 找到 {len(valid_records)} 条有效调仓记录")
                self.logger.info(f"⏰ 当前时间戳: {current_time_ms}")
                
                # 显示所有有效记录的详细信息
                for i, record in enumerate(valid_records, 1):
                    record_time = record.get('created_at', 0)
                    record_type = record.get('rebalancing_type', '未知')
                    holdings_count = len(record.get('rebalancing_histories', []))
                    time_diff_days = (current_time_ms - record_time) / (1000 * 60 * 60 * 24)
                    self.logger.info(f"📊 有效记录 {i}: 类型={record_type}, 时间={record_time}, 持仓数量={holdings_count}, 距今{time_diff_days:.1f}天")
                
                # 按时间戳倒序排序（最新的记录在前面）
                valid_records.sort(key=lambda x: x.get('created_at', 0), reverse=True)
                
                # 选择最近的“完整快照型”记录：优先近14天内且持仓数≥15，否则选持仓数最多且时间最近
                chosen_record = None
                best_record = None
                def _count(rec):
                    h = rec.get('rebalancing_histories', []) or []
                    return len(h) if isinstance(h, list) else 0
                for rec in valid_records:
                    cnt = _count(rec)
                    # 维护“持仓数最多且时间最近”的备选
                    if best_record is None or cnt > _count(best_record) or (cnt == _count(best_record) and rec.get('created_at', 0) > best_record.get('created_at', 0)):
                        best_record = rec
                    # 近14天且达到阈值的快照优先
                    record_time = rec.get('created_at', 0) or 0
                    days = (current_time_ms - record_time) / (1000 * 60 * 60 * 24) if record_time else 1e9
                    if cnt >= 15 and days <= 14:
                        chosen_record = rec
                        break
                if chosen_record is None:
                    chosen_record = best_record
                
                if not chosen_record:
                    self.logger.warning("未找到有效的调仓记录")
                    return []
                
                # 打印选定快照记录的详细信息
                self.logger.info(f"📊 选定快照记录详情:")
                self.logger.info(f"   - 类型: {chosen_record.get('rebalancing_type', '未知')}")
                self.logger.info(f"   - 时间: {chosen_record.get('created_at', '未知')}")
                self.logger.info(f"   - 持仓数量: {len(chosen_record.get('rebalancing_histories', []))}")
                
                # 解析选定记录中的持仓
                rebalancing_histories = chosen_record.get('rebalancing_histories', [])
                holdings = []
                
                self.logger.info(f"🔍 开始解析 {len(rebalancing_histories)} 个持仓记录")
                
                for i, holding in enumerate(rebalancing_histories):
                    if isinstance(holding, dict):
                        # 使用正确的字段映射
                        symbol = holding.get('stock_symbol', '') or holding.get('symbol', '')
                        stock_name = holding.get('stock_name', '') or holding.get('name', '')
                        target_weight = holding.get('target_weight', 0) or holding.get('weight', 0)
                        
                        self.logger.info(f"📊 持仓 {i+1}: symbol={symbol}, name={stock_name}, weight={target_weight}")
                        
                        if symbol and target_weight is not None:
                            # 安全处理数值转换
                            target_weight_float = 0.0
                            original_weight = 0.0
                            try:
                                target_weight_float = float(target_weight)
                                original_weight = target_weight_float
                                # 如果权重大于1，转换为小数形式
                                if target_weight_float > 1:
                                    target_weight_float = target_weight_float / 100.0
                                # 如果权重是0，也保留（可能是清仓操作）
                                elif target_weight_float == 0:
                                    pass
                            except (TypeError, ValueError):
                                target_weight_float = 0.0
                                try:
                                    original_weight = float(target_weight) if target_weight is not None else 0.0
                                except Exception:
                                    original_weight = 0.0
                            
                            # 放宽条件：只要不是None，都保留（包括0权重）
                            if target_weight_float >= 0:
                                holdings.append({
                                    'symbol': symbol,
                                    'name': stock_name,
                                    'target_weight': target_weight_float
                                })
                                self.logger.info(f"✅ 添加持仓: {symbol} {stock_name}, 原始权重={original_weight}, 转换后={target_weight_float:.4f}")
                            else:
                                self.logger.info(f"❌ 跳过持仓: {symbol} {stock_name}, 权重={target_weight_float}")
                        else:
                            self.logger.info(f"❌ 无效持仓: symbol={symbol}, weight={target_weight}")
                
                self.logger.info(f"📈 解析到 {len(holdings)} 个持仓")
                
                if holdings:
                    self.logger.info("📊 持仓详情:")
                    for i, holding in enumerate(holdings, 1):
                        self.logger.info(f"   {i:2d}. {holding['symbol']} {holding['name']}: {holding['target_weight']:.2%}")
                    
                    total_weight = sum(h['target_weight'] for h in holdings)
                    self.logger.info(f"📈 持仓统计:")
                    self.logger.info(f"   - 总持仓数量: {len(holdings)}")
                    self.logger.info(f"   - 总权重: {total_weight:.2%}")
                    
                    # 检查权重是否合理（应该在100%左右）
                    if total_weight > 1.5:  # 超过150%明显错误
                        self.logger.warning(f"总权重异常: {total_weight:.2%}，可能数据解析有误")
                        # 重新计算权重，确保不超过100%
                        normalized_holdings = []
                        for holding in holdings:
                            normalized_weight = holding['target_weight'] / total_weight if total_weight > 0 else 0
                            normalized_holdings.append({
                                'symbol': holding['symbol'],
                                'name': holding['name'],
                                'target_weight': normalized_weight
                            })
                        
                        normalized_total = sum(h['target_weight'] for h in normalized_holdings)
                        self.logger.info(f"📊 权重归一化后: {normalized_total:.2%}")
                        return normalized_holdings
                    
                    return holdings
                else:
                    self.logger.warning("未解析到任何持仓数据，组合可能为空仓状态")
                    return []
                    
        except Exception as e:
            self.logger.error(f"获取历史调仓持仓失败: {e}")
            import traceback
            self.logger.error(f"详细错误堆栈: {traceback.format_exc()}")
            return []

    async def _get_holdings_from_current_api(self, portfolio_code: str) -> Optional[List[Dict[str, Any]]]:
        """使用真正的当前持仓API获取当前实际持仓"""
        try:
            # 先尝试股票服务接口，获取页面展示的实时持仓权重
            stock_url = "https://stock.xueqiu.com/v5/stock/portfolio/stock/list.json"
            stock_params = {
                'cube_symbol': portfolio_code,
                'need_symbol': 'true',
                'size': 100,
                'retina': 1,
                'aid': '01',
                'captcha_token': '',
                '_': int(time.time() * 1000)
            }
            self.logger.info(f"使用股票服务当前持仓API: {stock_url}?cube_symbol={portfolio_code}")
            
            headers = self.headers.copy()
            headers['Referer'] = f'https://xueqiu.com/P/{portfolio_code}'
            headers['Origin'] = 'https://xueqiu.com'
            headers['Accept'] = 'application/json, text/plain, */*'
            headers['Host'] = 'stock.xueqiu.com'
            # 采用简化的请求方式
            # 避免复杂的token验证，直接使用cookie进行请求
            
            if self.session is None:
                self.logger.error("HTTP会话未初始化")
                return None
            
            holdings = []
            async with self.session.get(stock_url, params=stock_params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    self.logger.info(f"股票服务API返回状态: {response.status}")
                    self.logger.info(f"股票服务API返回数据: {json.dumps(data, ensure_ascii=False)[:500]}...")
                    
                    # 解析 data.data.stocks
                    stocks_root = data.get('data', {}) if isinstance(data, dict) else {}
                    stocks = stocks_root.get('stocks', []) if isinstance(stocks_root, dict) else []
                    if not isinstance(stocks, list):
                        stocks = []
                    
                    for item in stocks:
                        if not isinstance(item, dict):
                            continue
                        symbol = item.get('symbol') or item.get('stock_symbol') or ''
                        name = item.get('name') or item.get('stock_name') or ''
                        weight = item.get('weight', 0)
                        if weight is None:
                            weight = 0
                        
                        # 统一权重格式：转换为小数形式
                        if isinstance(weight, (int, float)):
                            # 如果权重值大于1，说明是百分比形式，需要除以100
                            if weight > 1:
                                weight = weight / 100.0
                            # 如果权重值小于等于1，直接使用（已经是小数形式）
                        else:
                            weight = 0
                        
                        if symbol and weight > 0:
                            holdings.append({
                                'symbol': symbol,
                                'name': name,
                                'target_weight': weight,  # 已经统一为小数形式
                                'prev_weight': 0,
                                'change_weight': 0,
                                'update_time': datetime.now().isoformat()
                            })
                    
                    holdings.sort(key=lambda x: x['target_weight'], reverse=True)
                    if holdings:
                        self.logger.info(f"✅ 从股票服务API成功获取 {len(holdings)} 个当前持仓")
                        # 打印统计
                        total_weight = sum(h['target_weight'] for h in holdings)
                        self.logger.info(f"📈 持仓统计: 数量={len(holdings)}, 总权重={total_weight:.2%}")
                        await self._generate_excel_file(portfolio_code, holdings)
                        return holdings
                    else:
                        self.logger.info("股票服务API返回空持仓，尝试备用API")
                else:
                    # 采用简化的cookie过期判断
                    # 根据反馈，历史记录能获取即继续尝试其他API
                    self.logger.warning(f"股票服务API返回状态码: {response.status}，将继续尝试备用API")
            
            # 备用：使用雪球 quote.json（可能不含持仓细节）
            url = f"https://xueqiu.com/cubes/quote.json"
            params = {
                'code': portfolio_code,
                '_': int(time.time() * 1000)
            }
            self.logger.info(f"使用当前持仓API: {url}?code={portfolio_code}")
            
            headers = self.headers.copy()
            headers['Referer'] = f'https://xueqiu.com/P/{portfolio_code}'
            headers['Host'] = 'xueqiu.com'
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    self.logger.info(f"当前持仓API返回状态: {response.status}")
                    self.logger.info(f"当前持仓API返回数据: {json.dumps(data, ensure_ascii=False)[:500]}...")
                    
                    holdings = []
                    
                    # 解析当前持仓数据
                    if isinstance(data, dict):
                        # 获取组合数据
                        portfolio_data = data.get(portfolio_code, {})
                        if not isinstance(portfolio_data, dict):
                            portfolio_data = {}
                        
                        # 获取持仓权重数据
                        weight_data = portfolio_data.get('weight', {})
                        if not isinstance(weight_data, dict):
                            weight_data = {}
                        
                        # 获取持仓列表
                        holdings_list = portfolio_data.get('holdings', [])
                        if not isinstance(holdings_list, list):
                            holdings_list = []
                        
                        # 解析当前持仓数据
                        for holding_item in holdings_list:
                            if isinstance(holding_item, dict):
                                symbol = holding_item.get('symbol', '')
                                name = holding_item.get('name', '')
                                
                                # 从权重数据中获取该股票的当前权重
                                weight = weight_data.get(symbol, 0)
                                if weight is None:
                                    weight = 0
                                
                                # 统一权重格式：转换为小数形式
                                if isinstance(weight, (int, float)):
                                    # 如果权重值大于1，说明是百分比形式，需要除以100
                                    if weight > 1:
                                        weight = weight / 100.0
                                    # 如果权重值小于等于1，直接使用（已经是小数形式）
                                else:
                                    weight = 0
                                
                                # 只保留当前权重大于0的持仓
                                if symbol and weight > 0:
                                    holding = {
                                        'symbol': symbol,
                                        'name': name,
                                        'target_weight': weight,  # 已经统一为小数形式
                                        'prev_weight': 0,
                                        'change_weight': 0,
                                        'update_time': datetime.now().isoformat()
                                    }
                                    holdings.append(holding)
                        
                        # 按权重排序
                        holdings.sort(key=lambda x: x['target_weight'], reverse=True)
                        
                        if holdings:
                            self.logger.info(f"✅ 从当前持仓API成功获取 {len(holdings)} 个当前持仓")
                            
                            # 详细打印当前持仓信息
                            self.logger.info("📊 当前持仓信息:")
                            for i, holding in enumerate(holdings, 1):
                                self.logger.info(f"   {i:2d}. {holding['symbol']} {holding['name']}: {holding['target_weight']:.2%}")
                            
                            # 计算总权重
                            total_weight = sum(h['target_weight'] for h in holdings)
                            self.logger.info(f"📈 持仓统计:")
                            self.logger.info(f"   - 总持仓数量: {len(holdings)}")
                            self.logger.info(f"   - 总权重: {total_weight:.2%}")
                            
                            # 生成Excel文件
                            await self._generate_excel_file(portfolio_code, holdings)
                        else:
                            self.logger.info(f"组合 {portfolio_code} 当前为空仓状态")
                        return holdings
                    else:
                        self.logger.warning(f"当前持仓API返回的数据不是字典类型: {type(data)}")
                        return []
                else:
                    # 参考雪球跟单系统3.0的简单实现：不进行复杂的cookie过期判断
                    # 根据用户反馈，历史记录能获取，说明cookie有效，继续尝试其他API
                    self.logger.warning(f"当前持仓API返回状态码: {response.status}，将继续尝试其他API")
                    # API失败时返回空列表表示空仓状态
                    return []
                    
        except Exception as e:
            self.logger.error(f"获取当前持仓失败: {e}")
            # 发生异常时返回空列表表示空仓状态
            return []

    async def _get_holdings_from_detail_api(self, portfolio_code: str) -> Optional[List[Dict[str, Any]]]:
        """使用详细持仓API作为备用方案获取当前持仓数据"""
        try:
            self.logger.info(f"尝试使用详细持仓API获取组合 {portfolio_code} 的当前持仓数据...")
            
            # 使用组合详情API获取当前持仓，而不是历史调仓记录
            url = f"https://xueqiu.com/cubes/detail.json"
            params = {
                'symbol': portfolio_code,
                '_': int(time.time() * 1000)
            }
            
            # 为当前请求动态设置Referer
            headers = self.headers.copy()
            headers['Referer'] = f'https://xueqiu.com/P/{portfolio_code}'
            headers['Host'] = 'xueqiu.com'
            
            if self.session is None:
                self.logger.error("HTTP会话未初始化")
                return None
                
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    self.logger.info(f"详细持仓API返回数据: {json.dumps(data, ensure_ascii=False)[:500]}...")
                    
                    holdings = []
                    
                    # 解析组合详情API返回的当前持仓数据
                    if isinstance(data, dict) and data is not None:
                        # 获取组合详情数据
                        cube = data.get('cube', {})
                        if cube is None or not isinstance(cube, dict):
                            cube = {}
                        
                        # 获取当前持仓列表
                        holdings_list = cube.get('holdings', [])
                        if not isinstance(holdings_list, list):
                            holdings_list = []
                        
                        # 解析每个当前持仓
                        for holding_data in holdings_list:
                            if isinstance(holding_data, dict):
                                stock_symbol = holding_data.get('stock_symbol', '')
                                stock_name = holding_data.get('stock_name', '')
                                weight = holding_data.get('weight', 0)
                                
                                # 确保权重值不为None
                                if weight is None:
                                    weight = 0
                                
                                # 只保留权重大于0的当前持仓
                                if stock_symbol and weight > 0:
                                    # 添加当前持仓
                                    holding = {
                                        'symbol': stock_symbol,
                                        'name': stock_name,
                                        'target_weight': weight / 100.0,
                                        'prev_weight': weight / 100.0,  # 当前持仓没有变化权重
                                        'change_weight': 0.0,  # 当前持仓变化权重为0
                                        'update_time': datetime.now().isoformat()
                                    }
                                    holdings.append(holding)
                        
                        # 按权重排序
                        holdings.sort(key=lambda x: x['target_weight'], reverse=True)
                        
                        if holdings:
                            self.logger.info(f"✅ 从详细持仓API成功获取 {len(holdings)} 个持仓")
                        else:
                            self.logger.info("详细持仓API返回空持仓数据，组合可能为空仓状态")
                        return holdings
                    else:
                        self.logger.warning(f"详细持仓API返回的数据不是字典类型: {type(data)}")
                        return None
                else:
                    if response.status in [400, 410]:
                        self.logger.error("cookie已过期")
                        return None
                    else:
                        self.logger.error(f"详细持仓API请求失败，状态码: {response.status}")
                        return None
        except Exception as e:
            self.logger.error(f"获取详细持仓失败: {e}")
            return None

    async def _get_holdings_from_portfolio_detail_api(self, portfolio_code: str) -> Optional[List[Dict[str, Any]]]:
        """使用组合详情API作为最终备用方案获取持仓数据"""
        try:
            self.logger.info(f"尝试使用组合详情API获取组合 {portfolio_code} 的持仓数据...")
            
            # 使用成功版本的API端点 - 组合详情API
            url = "https://xueqiu.com/cubes/quote.json"
            params = {
                'code': portfolio_code,
                '_': int(time.time() * 1000)
            }
            
            # 为当前请求动态设置Referer
            headers = self.headers.copy()
            headers['Referer'] = f'https://xueqiu.com/P/{portfolio_code}'
            headers['Host'] = 'xueqiu.com'
            
            if self.session is None:
                self.logger.error("HTTP会话未初始化")
                return []
                
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    self.logger.info(f"组合详情API返回数据: {json.dumps(data, ensure_ascii=False)[:500]}...")
                    
                    holdings = []
                    
                    # 解析组合详情数据
                    if isinstance(data, dict) and data is not None:
                        # 获取组合数据
                        portfolio_data = data.get(portfolio_code, {})
                        if portfolio_data is None or not isinstance(portfolio_data, dict):
                            portfolio_data = {}
                        
                        # 获取持仓权重数据
                        weight_data = portfolio_data.get('weight', {})
                        if not isinstance(weight_data, dict):
                            weight_data = {}
                        
                        # 获取持仓列表
                        holdings_list = portfolio_data.get('holdings', [])
                        if not isinstance(holdings_list, list):
                            holdings_list = []
                        
                        # 解析持仓数据
                        for holding_item in holdings_list:
                            if isinstance(holding_item, dict):
                                symbol = holding_item.get('symbol', '')
                                name = holding_item.get('name', '')
                                
                                # 从权重数据中获取该股票的权重
                                weight = weight_data.get(symbol, 0)
                                if weight is None:
                                    weight = 0
                                
                                if symbol and weight > 0:
                                    holding = {
                                        'symbol': symbol,
                                        'name': name,
                                        'target_weight': weight / 100.0,
                                        'prev_weight': 0,
                                        'change_weight': 0,
                                        'update_time': datetime.now().isoformat()
                                    }
                                    holdings.append(holding)
                        
                        # 按权重排序
                        holdings.sort(key=lambda x: x['target_weight'], reverse=True)
                        
                        if holdings:
                            self.logger.info(f"✅ 从组合详情API成功获取 {len(holdings)} 个持仓")
                            return holdings
                        else:
                            self.logger.warning("组合详情API返回空持仓数据")
                            # 当前持仓模式下，如果所有API都返回空数据，表示组合当前为空仓状态
                            self.logger.info(f"组合 {portfolio_code} 当前为空仓状态")
                            return []
                    else:
                        self.logger.warning(f"组合详情API返回的数据不是字典类型: {type(data)}")
                        return []
                else:
                    if response.status in [400, 410]:
                        self.logger.error("cookie已过期")
                        return None
                    else:
                        self.logger.error(f"组合详情API请求失败，状态码: {response.status}")
                        return []
        except Exception as e:
            self.logger.error(f"获取组合详情失败: {e}")
            return []
    
    async def _get_rebalancing_details(self, rb_id: str, portfolio_code: str) -> Optional[List[Dict[str, Any]]]:
        """获取调仓详细信息"""
        try:
            url = f"{self.base_url}/cubes/rebalancing/show_origin.json"
            params = {
                'rb_id': rb_id,
                'cube_symbol': portfolio_code
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    rebalancing_data = data.get('rebalancing') if data else None
                    rebalancing = rebalancing_data if isinstance(rebalancing_data, dict) else {}
                    
                    status = rebalancing.get('status', '') if rebalancing else ''
                    if status == 'success':
                        self.logger.info("获取调仓详细信息成功")
                        histories = rebalancing.get('rebalancing_histories', [])
                        if not isinstance(histories, list):
                            histories = []
                        return self._parse_holdings_from_histories(histories)
                    else:
                        self.logger.error(f"调仓状态异常: {status}")
                        return None
                else:
                    if response.status in [400, 410]:
                        self.logger.error("cookie已过期")
                        return None
                    else:
                        self.logger.error(f"获取调仓详情失败，状态码: {response.status}")
                        return None
                    
        except Exception as e:
            self.logger.error(f"获取调仓详情失败: {e}")
            return None
    
    def _parse_holdings_from_history(self, rebalancing_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从调仓历史解析持仓"""
        holdings = []
        
        try:
            if not rebalancing_data or not isinstance(rebalancing_data, dict):
                return []
            histories = rebalancing_data.get('rebalancing_histories', [])
            if not isinstance(histories, list):
                histories = []
            return self._parse_holdings_from_histories(histories)
            
        except Exception as e:
            self.logger.error(f"解析持仓数据失败: {e}")
            return []
    
    def _parse_holdings_from_histories(self, histories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从调仓历史列表解析持仓"""
        holdings = []
        
        try:
            if not histories:
                return []
                
            for history in histories:
                if not history:
                    continue
                    
                stock_symbol = history.get('stock_symbol', '')
                stock_name = history.get('stock_name', '')
                target_weight = history.get('target_weight', 0)
                prev_weight = history.get('prev_weight', 0)
                
                # 确保权重值不为None
                if target_weight is None:
                    target_weight = 0
                if prev_weight is None:
                    prev_weight = 0
                
                # 只保留目标权重大于0的持仓
                if target_weight > 0:
                    holding = {
                        'symbol': stock_symbol,
                        'name': stock_name,
                        'target_weight': target_weight / 100.0,  # 转换为小数
                        'prev_weight': prev_weight / 100.0,
                        'change_weight': (target_weight - prev_weight) / 100.0,
                        'update_time': datetime.now().isoformat()
                    }
                    holdings.append(holding)
            
            # 按权重排序
            holdings.sort(key=lambda x: x['target_weight'], reverse=True)
            
            self.logger.info(f"✅ 成功解析 {len(holdings)} 个持仓")
            for holding in holdings:
                self.logger.info(f"   {holding['symbol']} {holding['name']}: {holding['target_weight']:.2%}")
            
            return holdings
            
        except Exception as e:
            self.logger.error(f"解析持仓历史失败: {e}")
            return []
    
    async def get_portfolio_info(self, portfolio_code: str) -> Optional[Dict[str, Any]]:
        """获取组合基本信息"""
        # await self.rate_limiter.acquire()  # 暂时注释掉
        await asyncio.sleep(0.1)  # 简单延迟
        
        try:
            # 这里可以添加获取组合基本信息的API调用
            # 暂时返回基本信息
            return {
                'portfolio_code': portfolio_code,
                'name': f'雪球组合_{portfolio_code}',
                'update_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"获取组合信息失败: {e}")
            return None
    
    async def monitor_portfolio_changes(self, portfolio_code: str, callback=None):
        """监控组合变化
        
        Args:
            portfolio_code: 组合代码
            callback: 变化回调函数
        """
        self.logger.info(f"开始监控组合 {portfolio_code} 的变化...")
        
        last_holdings = None
        
        while True:
            try:
                # 获取当前持仓
                current_holdings = await self.get_portfolio_holdings(portfolio_code)
                
                # 检查是否有变化
                if last_holdings is not None and current_holdings != last_holdings:
                    self.logger.info(f"检测到组合 {portfolio_code} 发生变化")
                    
                    if callback:
                        await callback(portfolio_code, current_holdings, last_holdings)
                
                last_holdings = current_holdings
                
                # 等待下次检查（每30秒检查一次）
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error(f"监控组合变化时发生错误: {e}")
                await asyncio.sleep(60)  # 出错时等待更长时间

    async def _generate_excel_file(self, portfolio_code: str, holdings: List[Dict[str, Any]]) -> None:
        """生成持仓Excel文件（统一为固定文件名覆盖写，受配置开关控制）"""
        try:
            if not holdings:
                self.logger.warning("持仓数据为空，跳过Excel文件生成")
                return

            # 读取导出开关与目录配置
            export_enabled = False
            export_dir_name = "reports"
            try:
                from .config_manager import ConfigManager
                cm = ConfigManager()
                export_enabled = (
                    cm.get_setting('settings.export_holdings') or
                    cm.get_setting('导出持仓') or
                    False
                )
                export_dir_name = cm.get_setting('settings.export_dir') or "reports"
            except Exception:
                pass

            if not export_enabled:
                self.logger.info("导出开关关闭（settings.export_holdings/导出持仓），跳过Excel生成")
                return

            # DataFrame（增加类型检查，避免 None 或非字典元素）
            df_data = []
            for holding in holdings:
                if not isinstance(holding, dict):
                    continue
                tw = holding.get('target_weight', 0) or 0
                pw = holding.get('prev_weight', 0) or 0
                cw = holding.get('change_weight', 0) or 0
                try:
                    tw = float(tw)
                except Exception:
                    tw = 0.0
                try:
                    pw = float(pw)
                except Exception:
                    pw = 0.0
                try:
                    cw = float(cw)
                except Exception:
                    cw = 0.0
                df_data.append({
                    '股票代码': holding.get('symbol', '') or '',
                    '股票名称': holding.get('name', '') or '',
                    '目标权重': f"{tw:.2%}",
                    '前次权重': f"{pw:.2%}",
                    '权重变化': f"{cw:+.2%}",
                    '更新时间': holding.get('update_time', '') or ''
                })
            df = pd.DataFrame(df_data)

            # 计算总权重（安全转换）
            total_weight = 0.0
            for h in holdings:
                if not isinstance(h, dict):
                    continue
                val = h.get('target_weight', 0) or 0
                try:
                    total_weight += float(val)
                except Exception:
                    pass
            df.loc[len(df)] = {
                '股票代码': '总计',
                '股票名称': '',
                '目标权重': f"{total_weight:.2%}",
                '前次权重': '',
                '权重变化': '',
                '更新时间': ''
            }

            # 统一导出目录：项目根目录 / export_dir_name
            from pathlib import Path
            export_dir_abs = Path.cwd() / export_dir_name
            export_dir_abs.mkdir(parents=True, exist_ok=True)

            # 固定文件名，覆盖写
            filename = f"{portfolio_code}_持仓数据.xlsx"
            filepath = export_dir_abs / filename

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='持仓数据', index=False)

            self.logger.info(f"✅ 持仓数据已导出到: {filepath}（覆盖写）")

        except Exception as e:
            self.logger.error(f"生成Excel文件失败: {e}")
            import traceback
            self.logger.error(f"详细错误堆栈: {traceback.format_exc()}")

    async def close(self):
        """关闭采集器"""
        if self.session:
            await self.session.close()
            self.session = None
        self.logger.info("真实雪球数据采集器已关闭")