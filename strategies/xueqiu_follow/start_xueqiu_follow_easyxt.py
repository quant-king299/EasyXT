#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雪球跟单策略启动脚本 - 使用 easy_xt 模块
配置信息：
- 使用 easy_xt 自动检测 QMT 路径
- 账号: 39020958
- 跟单组合: https://xueqiu.com/P/ZHXXXXXX
"""

import os
import sys
import json
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 添加当前目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 添加 easy_xt 相关路径
easy_xt_path = os.path.join(project_root, 'easy_xt')
easyxt_main_path = os.path.join(project_root, 'EasyXT-main', 'easy_xt')
xtquant_path = os.path.join(project_root, 'xtquant')

for p in (easy_xt_path, easyxt_main_path, xtquant_path):
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

# 导入依赖检查
def check_dependencies():
    """检查依赖模块"""
    missing_deps = []
    
    try:
        import requests
    except ImportError:
        missing_deps.append('requests')
    
    try:
        import bs4
    except ImportError:
        missing_deps.append('beautifulsoup4')
    
    try:
        from easy_xt.config import config
        from easy_xt import get_advanced_api
    except ImportError:
        missing_deps.append('easy_xt (QMT交易模块)')
    
    if missing_deps:
        print("❌ 缺少以下依赖模块:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print("\n请安装缺少的模块:")
        for dep in missing_deps:
            if dep == 'beautifulsoup4':
                print(f"   pip install {dep}")
            elif dep != 'easy_xt (QMT交易模块)':
                print(f"   pip install {dep}")
        return False
    
    return True

# 导入项目模块
qmt_available = False
qmt_config = None
get_advanced_api = None

try:
    from easy_xt.config import config as qmt_config
    from easy_xt import get_advanced_api
    qmt_available = True
except ImportError as e:
    print(f"⚠️ QMT模块导入失败: {e}")
    qmt_available = False

# 导入模块
try:
    # 添加雪球跟单系统路径
    xueqiu_follow_path = os.path.join(project_root, 'strategies', 'xueqiu_follow')
    if xueqiu_follow_path not in sys.path:
        sys.path.insert(0, xueqiu_follow_path)
    
    # 添加utils目录到路径
    utils_path = os.path.join(xueqiu_follow_path, 'utils')
    if utils_path not in sys.path:
        sys.path.insert(0, utils_path)
    
    # 添加core目录到路径
    core_path = os.path.join(xueqiu_follow_path, 'core')
    if core_path not in sys.path:
        sys.path.insert(0, core_path)
    
    from core.config_manager import ConfigManager
    from core.xueqiu_collector_real import XueqiuCollectorReal
    from core.trade_executor import TradeExecutor
    from core.risk_manager import RiskManager
    from core.strategy_engine import StrategyEngine
    print("✅ 模块导入成功")
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    sys.exit(1)

def print_banner():
    """打印启动横幅"""
    print("=" * 70)
    print("🚀 雪球跟单策略 - EasyXT 版本")
    print("=" * 70)
    print(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        from core.config_manager import ConfigManager as _Cfg
        _cfg = _Cfg()
        portfolios = _cfg.get_portfolios()
        enabled_names = [str(p.get('name') or p.get('code')) for p in portfolios if p.get('enabled', False)]
        combo_str = ', '.join(enabled_names) if enabled_names else '未配置'
    except Exception:
        combo_str = '未配置'
    print(f"📊 跟单组合: {combo_str}")
    try:
        from core.config_manager import ConfigManager as _Cfg2
        _cfg2 = _Cfg2()
        account_id = _cfg2.get_setting('settings.account.account_id')
        account_str = str(account_id) if account_id else '未配置'
    except Exception:
        account_str = '未配置'
    print(f"🏦 交易账号: {account_str}")
    print("🔧 交易接口: EasyXT (高级交易API)")
    print("=" * 70)

def check_qmt_config(config_file_path: str) -> bool:
    """检查 QMT 配置（优先使用配置文件路径，兜底自动检测）
    
    Args:
        config_file_path: 配置文件中的 QMT 路径
    """
    print("\n🔍 检查 QMT 配置...")
    
    if not qmt_available:
        print("❌ QMT 模块不可用")
        return False
    
    try:
        # 第一优先级：使用配置文件中的路径
        if config_file_path:
            print(f"📁 尝试使用配置文件中的 QMT 路径: {config_file_path}")
            
            # 处理可能的 userdata_mini 后缀
            if config_file_path.endswith('/userdata_mini') or config_file_path.endswith('\\userdata_mini'):
                qmt_base_path = os.path.dirname(config_file_path)
            else:
                qmt_base_path = config_file_path
            
            # 验证配置文件路径
            if qmt_config.set_qmt_path(qmt_base_path):
                print("✅ 配置文件中的 QMT 路径设置成功")
                return True
            else:
                print(f"❌ 配置文件中的 QMT 路径无效: {qmt_base_path}")
        
        # 第二优先级：自动检测路径（兜底）
        print("🔧 尝试自动检测 QMT 路径...")
        qmt_config.print_qmt_status()
        
        # 验证自动检测的配置
        is_valid, msg = qmt_config.validate_qmt_setup()
        if is_valid:
            print(f"✅ 自动检测 QMT 路径成功: {msg}")
            return True
        else:
            print(f"❌ 自动检测 QMT 路径失败: {msg}")
            return False
            
    except Exception as e:
        print(f"❌ QMT 配置检查异常: {e}")
        return False

def test_qmt_connection() -> bool:
    """测试 QMT 连接"""
    print("\n🔗 测试 QMT 连接...")
    
    if not qmt_available:
        print("❌ QMT 模块不可用")
        return False
    
    try:
        # 获取 API
        api = get_advanced_api()
        
        # 获取连接参数
        userdata_path = qmt_config.get_userdata_path()
        if not userdata_path:
            print("❌ 无法获取 userdata 路径")
            return False
        
        print(f"📁 userdata 路径: {userdata_path}")
        
        # 连接测试
        print("🔌 正在连接交易服务...")
        success = api.connect(userdata_path, session_id="xueqiu_test")
        
        if success:
            print("✅ 交易服务连接成功")
            
            # 测试账户
            account_id = "39020958"
            print(f"👤 测试账户: {account_id}")
            
            account_success = api.add_account(account_id, "STOCK")
            if account_success:
                print("✅ 账户添加成功")
                
                # 简单查询测试
                try:
                    asset = api.get_account_asset_detailed(account_id)
                    if asset:
                        print(f"💰 账户总资产: {asset.get('total_asset', 0)}")
                    else:
                        print("⚠️ 账户查询无数据")
                except Exception as e:
                    print(f"⚠️ 账户查询失败: {e}")
            else:
                print("❌ 账户添加失败")
            
            # 断开连接
            api.disconnect()
            print("✅ 连接测试完成")
            return account_success
        else:
            print("❌ 交易服务连接失败")
            return False
            
    except Exception as e:
        print(f"❌ 连接测试异常: {e}")
        return False

def load_config() -> Optional[Dict[str, Any]]:
    """加载配置"""
    # 尝试加载统一配置文件
    config_path = os.path.join(current_dir, 'config', 'unified_config.json')
    
    if not os.path.exists(config_path):
        # 如果统一配置文件不存在，尝试其他配置文件
        config_path = os.path.join(current_dir, 'config', 'portfolios.json')
        if not os.path.exists(config_path):
            print("❌ 未找到配置文件")
            return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        print("✅ 配置文件加载成功")
        
        # 显示关键配置
        account_id = config_data.get('settings', {}).get('account', {}).get('account_id', '未配置')
        trade_mode = config_data.get('settings', {}).get('trading', {}).get('trade_mode', 'paper_trading')
        
        # 获取组合信息
        portfolios = config_data.get('portfolios', {}).get('portfolios', [])
        portfolio_names = [p.get('name', '未知') for p in portfolios if p.get('enabled', False)]
        
        # 检查雪球cookie配置
        xueqiu_cookie = config_data.get('xueqiu_settings', {}).get('cookie', '')
        if xueqiu_cookie:
            print("✅ 雪球cookie配置已加载")
        else:
            print("⚠️ 雪球cookie未配置，可能无法获取真实持仓数据")
        
        print(f"🏦 交易账号: {account_id}")
        print(f"💼 交易模式: {trade_mode}")
        if portfolio_names:
            print(f"📊 跟单组合: {', '.join(portfolio_names)}")
        else:
            print("📊 跟单组合: 未配置")
        
        return config_data
        
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return None

def update_config_with_qmt(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """使用 QMT 配置更新系统配置"""
    try:
        # 获取 QMT 路径
        userdata_path = qmt_config.get_userdata_path()
        if userdata_path:
            config_data['settings']['account']['qmt_path'] = userdata_path
            print(f"✅ 更新 QMT 路径: {userdata_path}")
        
        # 添加 QMT 特定配置
        if 'qmt' not in config_data['settings']:
            config_data['settings']['qmt'] = {}
        
        config_data['settings']['qmt'].update({
            'session_id': 'xueqiu_follow',
            'api_type': 'advanced',
            'auto_retry': True,
            'retry_count': 3,
            'timeout': 30
        })
        
        print("✅ QMT 配置更新完成")
        return config_data
        
    except Exception as e:
        print(f"❌ QMT 配置更新失败: {e}")
        return config_data

class XueqiuFollowSystem:
    """雪球跟单策略主类"""
    
    def __init__(self, config_data: Dict[str, Any]):
        self.config_data = config_data
        self.config_manager = None
        self.collector = None
        self.executor = None
        self.risk_manager = None
        self.strategy_engine = None
        self.running = False
        
    async def initialize(self) -> bool:
        """初始化系统"""
        try:
            print("\n🔧 初始化雪球跟单策略...")
            
            # 初始化配置管理器
            self.config_manager = ConfigManager()
            # 强制启用智能差额跟投，避免重复买入
            try:
                self.config_manager.set_setting('settings.follow_mode.mode', 'smart_follow', save=False)
            except Exception:
                pass
            # 使用配置数据更新配置管理器
            if self.config_data:
                # 更新主配置
                if 'settings' in self.config_data:
                    self.config_manager._settings = self.config_data['settings']
                # 更新组合配置
                if 'portfolios' in self.config_data:
                    self.config_manager._portfolios = self.config_data['portfolios']
                # 雪球配置通过set_setting方法设置
                if 'xueqiu_settings' in self.config_data:
                    for key, value in self.config_data['xueqiu_settings'].items():
                        self.config_manager.set_setting(f'xueqiu.{key}', value, save=False)
            print("✅ 配置管理器初始化完成")
            
            # 初始化雪球数据收集器（使用真实采集器）
            self.collector = XueqiuCollectorReal()
            # 传递雪球cookie配置
            if hasattr(self.config_manager, '_xueqiu_settings'):
                xueqiu_cookie = self.config_manager._xueqiu_settings.get('cookie', '')
                if xueqiu_cookie:
                    print("✅ 使用配置的雪球cookie初始化数据收集器")
            await self.collector.initialize()
            print("✅ 雪球数据收集器初始化完成")
            
            # 启动前主动获取并打印当前持仓（优先历史调仓记录）
            try:
                portfolios_cfg = getattr(self.config_manager, "_portfolios", {}) or {}
                enabled_portfolios = [p for p in portfolios_cfg.get('portfolios', []) if isinstance(p, dict) and p.get('enabled', False)]
                if enabled_portfolios:
                    print("🔍 预检：从历史调仓记录解析当前持仓权重")
                    for p in enabled_portfolios:
                        # 提取组合代码：优先code/symbol，其次从URL末尾截取
                        code = p.get('code') or p.get('symbol')
                        if not code:
                            url = p.get('url', '')
                            if isinstance(url, str) and url:
                                code = url.strip('/').split('/')[-1]
                        if not code:
                            continue
                        # 让收集器使用默认策略：优先最近完整快照型历史调仓记录，必要时回退当前持仓API
                        holdings = await self.collector.get_portfolio_holdings(code)
                        # 若默认方法仅得到极少持仓（如1只），启用兜底：选最近一条“完整快照型”记录
                        total_count = len(holdings or [])
                        if not holdings or total_count <= 1:
                            fallback = await self._reconstruct_holdings_by_replay(code)
                            if fallback:
                                holdings = fallback
                                total_count = len(holdings or [])
                        
                        if holdings:
                            print(f"📊 组合 {code} 当前持仓（基于历史调仓权重）:")
                            for h in holdings:
                                try:
                                    tw = h.get('target_weight', 0) or 0
                                    sym = h.get('symbol','')
                                    nm = h.get('name','')
                                    # 兼容不同字段命名
                                    print(f"   - {sym} {nm}: {tw:.2%}")
                                except Exception:
                                    # 防止格式化异常
                                    print(f"   - {h}")
                            print(f"📈 持仓数量: {total_count}")
                        else:
                            print(f"⚠️ 组合 {code} 未获取到持仓，可能cookie失效或API限制")
                else:
                    print("ℹ️ 未配置启用的跟单组合，跳过持仓预检")
            except Exception as e:
                print(f"⚠️ 持仓预检异常: {e}")
            
            # 初始化交易执行器（使用 QMT 配置）
            userdata_path = qmt_config.get_userdata_path() if qmt_config else None
            if not userdata_path:
                # 如果qmt_config不可用，尝试从配置中获取
                userdata_path = self.config_data['settings']['account'].get('qmt_path', '')
            
            qmt_config_dict = {
                'userdata_path': userdata_path,
                'account_id': self.config_data['settings']['account']['account_id'],
                'session_id': self.config_data['settings']['qmt']['session_id'],
                'max_concurrent_orders': 10,
                'order_timeout': 30,
                'retry_times': 3,
                'retry_delay': 1
            }
            
            self.executor = TradeExecutor(qmt_config_dict)
            if not await self.executor.initialize():
                raise Exception("交易执行器初始化失败")
            print("✅ 交易执行器初始化完成")
            
            # 初始化风险管理器
            self.risk_manager = RiskManager(self.config_manager)
            print("✅ 风险管理器初始化完成")
            
            # 初始化策略引擎
            self.strategy_engine = StrategyEngine(self.config_manager)
            await self.strategy_engine.initialize()
            print("✅ 策略引擎初始化完成")
            
            print("🎉 系统初始化完成！")
            return True
            
        except Exception as e:
            print(f"❌ 系统初始化失败: {e}")
            return False
    
    async def start(self):
        """启动系统"""
        try:
            print("\n🚀 启动雪球跟单策略...")
            
            self.running = True
            
            # 启动前先同步一次账户持仓，确保智能差额使用最新持仓
            try:
                await self.strategy_engine.sync_positions()
            except Exception:
                pass
            # 启动策略引擎
            await self.strategy_engine.start()
            
            print("✅ 系统启动成功！")
            print("\n📊 系统状态:")
            print("   - 雪球数据收集: 运行中")
            print("   - 交易执行: 就绪")
            print("   - 风险管理: 激活")
            print("   - 策略引擎: 运行中")
            
            # 主循环
            while self.running:
                try:
                    # 系统状态检查
                    await self._check_system_health()
                    
                    # 等待
                    await asyncio.sleep(10)
                    
                except KeyboardInterrupt:
                    print("\n⚠️ 收到停止信号...")
                    break
                except Exception as e:
                    print(f"❌ 系统运行异常: {e}")
                    await asyncio.sleep(5)
            
        except Exception as e:
            print(f"❌ 系统启动失败: {e}")
        finally:
            await self.stop()
    
    async def _check_system_health(self):
        """检查系统健康状态"""
        try:
            # 检查各组件状态
            if self.collector and hasattr(self.collector, 'health_check'):
                if not self.collector.health_check():
                    print("⚠️ 数据收集器状态异常")
            
            if self.executor and hasattr(self.executor, 'get_execution_stats'):
                stats = self.executor.get_execution_stats()
                if stats['total_orders'] > 0:
                    success_rate = stats['success_rate']
                    if success_rate < 0.8:  # 成功率低于80%
                        print(f"⚠️ 交易成功率较低: {success_rate:.2%}")
            
        except Exception as e:
            print(f"⚠️ 健康检查异常: {e}")
    
    async def _fallback_fetch_full_snapshot(self, portfolio_code: str) -> Optional[list]:
        """
        兜底：当默认解析得到的持仓过少时，主动抓取历史调仓数据，选最近的“完整快照型”记录来解析持仓。
        筛选策略：
          - 优先选择最近一条持仓数量 >= min_count 的记录（默认 15）
          - 若近14天内无满足条件，则选择最近时间的“持仓数量最多”的记录
        """
        try:
            import requests
            min_count = 15
            max_records = 50
            headers = {
                "User-Agent": "Mozilla/5.0",
            }
            # 从配置管理器拿 cookie（此前已通过 set_setting('xueqiu.cookie', ...) 注入）
            cookie = ""
            try:
                if hasattr(self.config_manager, "_xueqiu_settings"):
                    cookie = self.config_manager._xueqiu_settings.get("cookie", "") or ""
            except Exception:
                pass
            if cookie:
                headers["Cookie"] = cookie
            
            url = "https://xueqiu.com/cubes/rebalancing/history.json"
            params = {"cube_symbol": portfolio_code, "count": max_records, "page": 1}
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            if resp.status_code != 200:
                print(f"⚠️ 兜底历史API状态码异常: {resp.status_code}")
                return None
            data = resp.json() if resp.content else {}
            # 常见结构为 {'list': [record,...]}
            records = []
            if isinstance(data, dict):
                if isinstance(data.get("list"), list):
                    records = data.get("list") or []
                elif isinstance(data.get("rebalancings"), list):
                    records = data.get("rebalancings") or []
            
            if not records:
                return None
            
            # 选取最近满足条件的快照
            import math, time as _t
            now_ms = int(_t.time() * 1000)
            chosen = None
            best = None  # 保存持仓数量最多且时间最近的记录
            for r in records:
                if not isinstance(r, dict):
                    continue
                histories = r.get("rebalancing_histories", []) or []
                count = len(histories)
                created_at = r.get("created_at", 0) or 0
                # 维护最佳
                if best is None or (count > len(best.get("rebalancing_histories", []) or []) or (count == len(best.get("rebalancing_histories", []) or []) and created_at > (best.get("created_at") or 0))):
                    best = r
                # 近14天内且达到阈值的记录优先
                days = (now_ms - created_at) / (1000 * 60 * 60 * 24) if created_at else math.inf
                if count >= min_count and days <= 14:
                    chosen = r
                    break
            if chosen is None:
                chosen = best
            
            histories = chosen.get("rebalancing_histories", []) or []
            if not histories:
                return None
            
            # 解析为 holdings
            parsed = []
            for h in histories:
                if not isinstance(h, dict):
                    continue
                symbol = h.get("stock_symbol", "") or ""
                name = h.get("stock_name", "") or ""
                tw = h.get("target_weight", 0) or 0
                pw = h.get("prev_weight", 0) or 0
                parsed.append({
                    "type": "add" if (tw >= pw) else "update",
                    "symbol": symbol,
                    "name": name,
                    "target_weight": (tw / 100.0),
                    "prev_weight": (pw / 100.0),
                    "weight_change": ((tw - pw) / 100.0),
                })
            return parsed or None
        except Exception as e:
            print(f"⚠️ 兜底解析异常: {e}")
            return None

    async def _reconstruct_holdings_by_replay(self, portfolio_code: str) -> Optional[list]:
        """
        全量回放历史调仓记录，按时间从最早到最近逐条应用，重建当前完整持仓。
        逻辑：
          - 拉取多页历史调仓列表（list 或 rebalancings）
          - 按 created_at 升序遍历；对每条记录的 rebalancing_histories：
              * target_weight（百分比）/100 为最终权重
              * target_weight 为 0 表示删除该持仓
          - 将最新权重 > 0 的持仓输出为列表（包含 symbol/name/target_weight）
        """
        try:
            import requests, math, time as _t
            headers = { "User-Agent": "Mozilla/5.0" }
            # 从配置管理器拿 cookie
            try:
                if hasattr(self.config_manager, "_xueqiu_settings"):
                    cookie = self.config_manager._xueqiu_settings.get("cookie", "") or ""
                    if cookie:
                        headers["Cookie"] = cookie
            except Exception:
                pass

            url = "https://xueqiu.com/cubes/rebalancing/history.json"
            # 分页抓取，最多 5 页，每页 50 条（上限 250 记录）
            all_records = []
            max_pages = 5
            page_size = 50
            for page in range(1, max_pages + 1):
                params = {"cube_symbol": portfolio_code, "count": page_size, "page": page}
                resp = requests.get(url, headers=headers, params=params, timeout=10)
                if resp.status_code != 200:
                    # 如果某页失败，停止进一步分页
                    break
                data = resp.json() if resp.content else {}
                records = []
                if isinstance(data, dict):
                    if isinstance(data.get("list"), list):
                        records = data.get("list") or []
                    elif isinstance(data.get("rebalancings"), list):
                        records = data.get("rebalancings") or []
                if not records:
                    # 没有更多记录
                    break
                all_records.extend([r for r in records if isinstance(r, dict)])

            if not all_records:
                return None

            # 按时间升序回放
            all_records.sort(key=lambda r: (r.get("created_at") or 0))

            weights = {}  # symbol -> 最终权重(0-1)
            names = {}    # symbol -> 最新名称
            for r in all_records:
                histories = r.get("rebalancing_histories", []) or []
                if not isinstance(histories, list):
                    continue
                for h in histories:
                    if not isinstance(h, dict):
                        continue
                    symbol = (h.get("stock_symbol") or "").strip()
                    name = (h.get("stock_name") or "").strip()
                    tw_pct = h.get("target_weight", 0) or 0  # 百分比
                    try:
                        tw = float(tw_pct) / 100.0
                    except Exception:
                        tw = 0.0
                    # 回放：设置最终权重；为 0 则删除/清零
                    if symbol:
                        names[symbol] = name or names.get(symbol, "")
                        if tw > 0:
                            weights[symbol] = tw
                        else:
                            # 目标权重为 0 代表移除
                            if symbol in weights:
                                del weights[symbol]

            if not weights:
                return None

            # 生成持仓列表
            result = []
            for sym, tw in weights.items():
                result.append({
                    "type": "position",
                    "symbol": sym,
                    "name": names.get(sym, ""),
                    "target_weight": tw,
                })
            return result or None
        except Exception as e:
            print(f"⚠️ 重放解析异常: {e}")
            return None
    
    async def stop(self):
        """停止系统"""
        try:
            print("\n🛑 停止雪球跟单策略...")
            
            self.running = False
            
            # 停止各组件
            if self.strategy_engine:
                await self.strategy_engine.stop()
                print("✅ 策略引擎已停止")
            
            if self.executor:
                await self.executor.close()
                print("✅ 交易执行器已关闭")
            
            if self.collector:
                await self.collector.close()
                print("✅ 数据收集器已关闭")
            
            print("✅ 系统已安全停止")
            
        except Exception as e:
            print(f"❌ 系统停止异常: {e}")

async def main():
    """主函数"""
    print_banner()
    
    # 1. 检查依赖
    if not check_dependencies():
        return
    
    # 2. 加载配置
    config_data = load_config()
    if not config_data:
        return
    
    # 3. 获取配置文件中的 QMT 路径
    config_file_qmt_path = config_data.get('settings', {}).get('account', {}).get('qmt_path', '')
    
    # 4. 检查 QMT 配置（优先使用配置文件路径，兜底自动检测）
    if not check_qmt_config(config_file_qmt_path):
        print("\n❌ QMT 配置检查失败，请运行测试脚本:")
        print("   python test_qmt_connection.py")
        return
    
    # 5. 测试 QMT 连接
    if not test_qmt_connection():
        print("\n❌ QMT 连接测试失败")
        return
    
    # 6. 更新配置
    config_data = update_config_with_qmt(config_data)
    
    # 7. 安全确认
    if config_data['settings']['trading']['trade_mode'] == 'real':
        print("\n⚠️ 警告：当前配置为真实交易模式！")
        print("   这将执行真实的买卖操作，可能造成资金损失")
        
        if not config_data.get('safety', {}).get('auto_confirm', False):
            confirm = input("\n请输入 'YES' 确认启动真实交易: ")
            if confirm != 'YES':
                print("❌ 用户取消启动")
                return
        
        print("✅ 真实交易模式确认")
    else:
        print("✅ 模拟交易模式")
    
    # 8. 启动系统
    system = XueqiuFollowSystem(config_data)
    
    if await system.initialize():
        try:
            await system.start()
        except KeyboardInterrupt:
            print("\n⚠️ 用户中断")
        except Exception as e:
            print(f"\n❌ 系统运行异常: {e}")
    else:
        print("❌ 系统初始化失败")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")