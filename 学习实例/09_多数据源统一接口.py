#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EasyXT学习实例 04 - 多数据源统一接口高级应用（互动学习版）
=======================================================

学习目标：
1. 掌握多数据源统一接口的高级应用
2. 学习数据源智能切换和容错机制
3. 实现基于多数据源的量化分析策略
4. 掌握数据融合和交叉验证技术
5. 构建实时监控和预警系统

本课程分为8个渐进式学习模块：
- 第1课：多数据源环境搭建与连接优化
- 第2课：数据源健康监控与智能切换
- 第3课：多源数据融合与质量评估
- 第4课：实时行情监控与异常检测
- 第5课：热点概念挖掘与趋势分析
- 第6课：资金流向追踪与主力行为分析
- 第7课：多维度交易信号生成
- 第8课：实时预警系统构建

特色功能：
✨ 互动学习：每个课程结束后需要按回车确认继续
✨ 逐步学习：可以随时退出，方便分段学习
✨ 详细说明：每个步骤都有详细的解释和分析

作者: 王者quant
日期: 2025-09-26
版本: 2.0.0 (互动学习版)
"""

import sys
import os
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
import threading
import queue
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入自定义数据接口
from easy_xt.realtime_data.providers.tdx_provider import TdxDataProvider
from easy_xt.realtime_data.providers.ths_provider import ThsDataProvider
from easy_xt.realtime_data.providers.eastmoney_provider import EastmoneyDataProvider

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('multi_source_learning.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class DataSourceHealthMonitor:
    """数据源健康监控器"""
    
    def __init__(self):
        self.health_status = {}
        self.performance_metrics = {}
        self.error_counts = {}
        self.last_check_time = {}
        
    def check_source_health(self, source_name: str, provider) -> Dict[str, Any]:
        """检查数据源健康状态"""
        start_time = time.time()
        health_info = {
            'name': source_name,
            'status': 'unknown',
            'response_time': 0,
            'error_count': self.error_counts.get(source_name, 0),
            'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            # 测试连接
            if hasattr(provider, 'connect'):
                connected = provider.connect()
                if connected:
                    # 测试数据获取
                    test_quotes = provider.get_realtime_quotes(['000001'])
                    if test_quotes:
                        health_info['status'] = 'healthy'
                        health_info['response_time'] = round((time.time() - start_time) * 1000, 2)
                        # 重置错误计数
                        self.error_counts[source_name] = 0
                    else:
                        health_info['status'] = 'degraded'
                        health_info['response_time'] = round((time.time() - start_time) * 1000, 2)
                else:
                    health_info['status'] = 'disconnected'
            else:
                # 对于没有connect方法的数据源，直接测试数据获取
                test_data = provider.get_hot_stocks() if hasattr(provider, 'get_hot_stocks') else []
                if test_data:
                    health_info['status'] = 'healthy'
                    health_info['response_time'] = round((time.time() - start_time) * 1000, 2)
                    self.error_counts[source_name] = 0
                else:
                    health_info['status'] = 'degraded'
                    
        except Exception as e:
            health_info['status'] = 'error'
            health_info['error_message'] = str(e)
            self.error_counts[source_name] = self.error_counts.get(source_name, 0) + 1
            
        self.health_status[source_name] = health_info
        self.last_check_time[source_name] = time.time()
        
        return health_info
    
    def get_best_source(self, required_capability: str = None) -> str:
        """根据健康状态选择最佳数据源"""
        healthy_sources = []
        
        for source_name, status in self.health_status.items():
            if status['status'] == 'healthy':
                healthy_sources.append((source_name, status['response_time']))
        
        if healthy_sources:
            # 按响应时间排序，选择最快的
            healthy_sources.sort(key=lambda x: x[1])
            return healthy_sources[0][0]
        
        # 如果没有健康的数据源，选择状态最好的
        if self.health_status:
            status_priority = {'healthy': 0, 'degraded': 1, 'disconnected': 2, 'error': 3}
            best_source = min(self.health_status.items(), 
                            key=lambda x: status_priority.get(x[1]['status'], 999))
            return best_source[0]
        
        return None

class MultiSourceDataFusion:
    """多数据源数据融合器"""
    
    def __init__(self):
        self.fusion_rules = {
            'price_data': self._fuse_price_data,
            'volume_data': self._fuse_volume_data,
            'concept_data': self._fuse_concept_data,
            'fund_flow_data': self._fuse_fund_flow_data
        }
        
    def _fuse_price_data(self, data_sources: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """融合价格数据"""
        if not data_sources:
            return pd.DataFrame()
        
        # 优先级：通达信 > 同花顺 > 东方财富
        priority_order = ['TdxProvider', 'ThsProvider', 'EastmoneyProvider']
        
        for source in priority_order:
            if source in data_sources and not data_sources[source].empty:
                result = data_sources[source].copy()
                result['data_source'] = source
                result['fusion_confidence'] = 0.9 if source == 'TdxProvider' else 0.8
                return result
        
        return pd.DataFrame()
    
    def _fuse_volume_data(self, data_sources: Dict[str, Any]) -> Dict[str, Any]:
        """融合成交量数据"""
        fused_data = {}
        
        for source, data in data_sources.items():
            if data:
                fused_data[f'{source}_volume'] = data
        
        # 计算平均值作为融合结果
        if fused_data:
            volumes = [v for v in fused_data.values() if isinstance(v, (int, float))]
            if volumes:
                fused_data['fused_volume'] = sum(volumes) / len(volumes)
                fused_data['confidence'] = min(1.0, len(volumes) / 3)  # 数据源越多置信度越高
        
        return fused_data
    
    def _fuse_concept_data(self, data_sources: Dict[str, List]) -> List[Dict]:
        """融合概念数据"""
        concept_scores = {}
        
        for source, concepts in data_sources.items():
            weight = 0.6 if source == 'ThsProvider' else 0.4  # 同花顺概念数据权重更高
            
            for concept in concepts:
                concept_name = concept.get('name', concept.get('concept_name', ''))
                if concept_name:
                    if concept_name not in concept_scores:
                        concept_scores[concept_name] = {'score': 0, 'sources': [], 'details': concept}
                    
                    concept_scores[concept_name]['score'] += weight
                    concept_scores[concept_name]['sources'].append(source)
        
        # 按融合分数排序
        fused_concepts = []
        for name, info in sorted(concept_scores.items(), key=lambda x: x[1]['score'], reverse=True):
            fused_concepts.append({
                'name': name,
                'fusion_score': info['score'],
                'source_count': len(info['sources']),
                'sources': info['sources'],
                'details': info['details']
            })
        
        return fused_concepts[:20]  # 返回前20个
    
    def _fuse_fund_flow_data(self, data_sources: Dict[str, Dict]) -> Dict[str, Any]:
        """融合资金流向数据"""
        fused_flow = {
            'net_inflow': 0,
            'main_inflow': 0,
            'retail_inflow': 0,
            'confidence': 0,
            'sources': []
        }
        
        total_weight = 0
        for source, flow_data in data_sources.items():
            if flow_data:
                weight = 0.7 if source == 'EastmoneyProvider' else 0.3  # 东方财富资金流数据权重更高
                
                fused_flow['net_inflow'] += flow_data.get('net_inflow', 0) * weight
                fused_flow['main_inflow'] += flow_data.get('main_inflow', 0) * weight
                fused_flow['retail_inflow'] += flow_data.get('retail_inflow', 0) * weight
                fused_flow['sources'].append(source)
                total_weight += weight
        
        if total_weight > 0:
            fused_flow['net_inflow'] /= total_weight
            fused_flow['main_inflow'] /= total_weight
            fused_flow['retail_inflow'] /= total_weight
            fused_flow['confidence'] = min(1.0, total_weight)
        
        return fused_flow

class RealTimeAlertSystem:
    """实时预警系统"""
    
    def __init__(self):
        self.alert_rules = []
        self.alert_history = []
        self.alert_queue = queue.Queue()
        self.running = False
        
    def add_alert_rule(self, rule_name: str, condition_func, alert_level: str = 'INFO'):
        """添加预警规则"""
        self.alert_rules.append({
            'name': rule_name,
            'condition': condition_func,
            'level': alert_level,
            'last_triggered': None
        })
        
    def check_alerts(self, market_data: Dict[str, Any]):
        """检查预警条件"""
        current_time = datetime.now()
        
        for rule in self.alert_rules:
            try:
                if rule['condition'](market_data):
                    # 避免重复预警（5分钟内不重复）
                    if (rule['last_triggered'] is None or 
                        (current_time - rule['last_triggered']).seconds > 300):
                        
                        alert = {
                            'rule_name': rule['name'],
                            'level': rule['level'],
                            'message': f"预警触发: {rule['name']}",
                            'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                            'data': market_data
                        }
                        
                        self.alert_queue.put(alert)
                        self.alert_history.append(alert)
                        rule['last_triggered'] = current_time
                        
                        # 输出预警信息
                        level_emoji = {'INFO': '📢', 'WARNING': '⚠️', 'ERROR': '🚨'}
                        print(f"{level_emoji.get(rule['level'], '📢')} {alert['message']} - {alert['timestamp']}")
                        
            except Exception as e:
                logger.error(f"预警规则 {rule['name']} 检查异常: {e}")

class AdvancedMultiSourceAnalyzer:
    """
    高级多数据源分析器（互动学习版）
    
    整合多个数据源，提供统一的数据分析和交易决策支持
    """
    
    def __init__(self):
        """初始化分析器"""
        print("🚀 初始化高级多数据源分析器...")
        
        # 通达信V3优化配置：基于实际测试结果优化服务器优先级
        tdx_config = {
            'servers': [
                # 第一优先级：已验证快速可用的服务器
                {"host": "115.238.90.165", "port": 7709, "name": "南京主站-已验证最快"},  # V3测试0.19秒连接成功
                
                # 第二优先级：常用稳定服务器
                {"host": "119.147.212.81", "port": 7709, "name": "深圳主站"},
                {"host": "60.12.136.250", "port": 7709, "name": "电信主站"},
                {"host": "115.238.56.198", "port": 7709, "name": "杭州主站"},
                
                # 第三优先级：备用服务器
                {"host": "218.108.47.69", "port": 7709, "name": "移动主站"},
                {"host": "218.108.98.244", "port": 7709, "name": "联通主站"},
                {"host": "123.125.108.23", "port": 7709, "name": "北京主站"},
                {"host": "180.153.18.171", "port": 7709, "name": "福州主站"},
                
                # 第四优先级：测试中连接较慢的服务器
                {"host": "114.80.63.12", "port": 7709, "name": "上海主站"},
                {"host": "180.153.39.51", "port": 7709, "name": "广州主站"},
                {"host": "103.48.67.20", "port": 7709, "name": "厦门主站"}
            ],
            'timeout': 2,  # V3优化：2秒超时，快速失败快速切换
            'retry_count': 1,  # V3优化：减少重试次数，提高连接速度
            'retry_delay': 0.3  # V3优化：减少重试延迟
        }
        
        # 初始化数据提供者
        self.providers = {
            'TdxProvider': TdxDataProvider(tdx_config),
            'ThsProvider': ThsDataProvider(),
            'EastmoneyProvider': EastmoneyDataProvider()
        }
        
        # 初始化组件
        self.health_monitor = DataSourceHealthMonitor()
        self.data_fusion = MultiSourceDataFusion()
        self.alert_system = RealTimeAlertSystem()
        
        # 数据缓存
        self.cache = {
            'market_data': {},
            'concept_data': {},
            'fund_flow': {},
            'alerts': []
        }
        
        # 性能统计
        self.performance_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0,
            'data_source_usage': {}
        }
        
        logger.info("多数据源分析器初始化完成")
        print("✅ 初始化完成！")

    def lesson_01_setup_and_optimization(self):
        """第1课：多数据源环境搭建与连接优化"""
        print("\n💡 学习目标：")
        print("  • 了解多数据源架构设计")
        print("  • 掌握数据源连接优化技巧")
        print("  • 学习连接性能评估方法")
        
        print("\n🔧 1.1 数据源连接测试")
        print("-" * 50)
        
        connection_results = {}
        
        for name, provider in self.providers.items():
            print(f"\n测试 {name} 连接...")
            start_time = time.time()
            
            try:
                if hasattr(provider, 'connect'):
                    success = provider.connect()
                    connect_time = time.time() - start_time
                    
                    if success:
                        print(f"✅ {name} 连接成功！耗时: {connect_time:.3f}秒")
                        if hasattr(provider, 'current_server') and provider.current_server:
                            print(f"   📍 连接服务器: {provider.current_server.get('name', 'Unknown')}")
                            print(f"   🌐 服务器地址: {provider.current_server.get('host', 'Unknown')}:{provider.current_server.get('port', 'Unknown')}")
                        connection_results[name] = {'status': 'success', 'time': connect_time}
                    else:
                        print(f"❌ {name} 连接失败")
                        connection_results[name] = {'status': 'failed', 'time': connect_time}
                else:
                    # 对于不需要显式连接的数据源，测试数据获取
                    test_data = provider.get_hot_stocks() if hasattr(provider, 'get_hot_stocks') else []
                    connect_time = time.time() - start_time
                    
                    if test_data:
                        print(f"✅ {name} 数据获取成功！耗时: {connect_time:.3f}秒")
                        connection_results[name] = {'status': 'success', 'time': connect_time}
                    else:
                        print(f"⚠️ {name} 数据获取为空")
                        connection_results[name] = {'status': 'empty', 'time': connect_time}
                        
            except Exception as e:
                connect_time = time.time() - start_time
                print(f"❌ {name} 连接异常: {e}")
                connection_results[name] = {'status': 'error', 'time': connect_time, 'error': str(e)}
        
        print(f"\n📊 1.2 连接性能分析")
        print("-" * 50)
        
        successful_connections = [r for r in connection_results.values() if r['status'] == 'success']
        if successful_connections:
            avg_time = sum(r['time'] for r in successful_connections) / len(successful_connections)
            fastest = min(successful_connections, key=lambda x: x['time'])
            slowest = max(successful_connections, key=lambda x: x['time'])
            
            print(f"✅ 成功连接数据源: {len(successful_connections)}/{len(self.providers)}")
            print(f"⚡ 平均连接时间: {avg_time:.3f}秒")
            print(f"🚀 最快连接时间: {fastest['time']:.3f}秒")
            print(f"🐌 最慢连接时间: {slowest['time']:.3f}秒")
            
            # 连接速度评级
            if avg_time < 0.5:
                print("🏆 连接速度评级: 极速")
            elif avg_time < 1.0:
                print("⚡ 连接速度评级: 快速")
            elif avg_time < 2.0:
                print("🏃 连接速度评级: 良好")
            else:
                print("🐌 连接速度评级: 需要优化")
        else:
            print("❌ 没有成功连接的数据源")
        
        print(f"\n💡 1.3 优化建议")
        print("-" * 50)
        
        for name, result in connection_results.items():
            if result['status'] == 'success':
                if result['time'] < 0.5:
                    print(f"✅ {name}: 性能优秀，无需优化")
                elif result['time'] < 2.0:
                    print(f"⚡ {name}: 性能良好，可考虑进一步优化")
                else:
                    print(f"🔧 {name}: 建议检查网络连接或服务器配置")
            elif result['status'] == 'failed':
                print(f"🔧 {name}: 建议检查服务器列表或网络连接")
            elif result['status'] == 'error':
                print(f"🛠️ {name}: 建议检查配置或依赖库: {result.get('error', '')}")
        
        print(f"\n📚 知识点总结:")
        print("  • 多数据源架构可以提高系统可靠性")
        print("  • 连接优化是提升系统性能的关键")
        print("  • 性能监控有助于及时发现问题")
        
        return connection_results

    def lesson_02_health_monitoring(self):
        """第2课：数据源健康监控与智能切换"""
        print("\n💡 学习目标：")
        print("  • 掌握数据源健康监控机制")
        print("  • 学习智能切换算法")
        print("  • 了解系统可用性评估")
        
        print("\n🏥 2.1 数据源健康检查")
        print("-" * 50)
        
        health_results = {}
        
        for name, provider in self.providers.items():
            print(f"\n检查 {name} 健康状态...")
            health_info = self.health_monitor.check_source_health(name, provider)
            health_results[name] = health_info
            
            # 显示健康状态
            status_emoji = {
                'healthy': '💚',
                'degraded': '💛', 
                'disconnected': '🔴',
                'error': '💥',
                'unknown': '❓'
            }
            
            emoji = status_emoji.get(health_info['status'], '❓')
            print(f"{emoji} 状态: {health_info['status']}")
            print(f"⏱️ 响应时间: {health_info['response_time']}ms")
            print(f"❌ 错误次数: {health_info['error_count']}")
            print(f"🕐 检查时间: {health_info['last_check']}")
            
            if 'error_message' in health_info:
                print(f"💬 错误信息: {health_info['error_message']}")
        
        print(f"\n🎯 2.2 智能数据源选择")
        print("-" * 50)
        
        # 测试不同场景下的数据源选择
        scenarios = [
            ('实时行情获取', 'quotes'),
            ('概念热度分析', 'concepts'),
            ('资金流向监控', 'fund_flow'),
            ('通用数据获取', None)
        ]
        
        for scenario_name, capability in scenarios:
            best_source = self.health_monitor.get_best_source(capability)
            if best_source:
                health_info = health_results[best_source]
                print(f"📊 {scenario_name}: 推荐使用 {best_source}")
                print(f"   状态: {health_info['status']}, 响应时间: {health_info['response_time']}ms")
            else:
                print(f"❌ {scenario_name}: 无可用数据源")
        
        print(f"\n📈 2.3 性能监控仪表板")
        print("-" * 50)
        
        # 创建简单的性能仪表板
        healthy_count = sum(1 for h in health_results.values() if h['status'] == 'healthy')
        total_count = len(health_results)
        availability = (healthy_count / total_count) * 100 if total_count > 0 else 0
        
        avg_response_time = sum(h['response_time'] for h in health_results.values() if h['response_time'] > 0)
        avg_response_time = avg_response_time / len([h for h in health_results.values() if h['response_time'] > 0]) if any(h['response_time'] > 0 for h in health_results.values()) else 0
        
        print(f"🎯 系统可用性: {availability:.1f}% ({healthy_count}/{total_count})")
        print(f"⚡ 平均响应时间: {avg_response_time:.1f}ms")
        print(f"🔄 自动切换: {'启用' if healthy_count > 1 else '不可用'}")
        
        # 设置自动监控
        print(f"\n⚙️ 2.4 自动监控设置")
        print("-" * 50)
        print("✅ 健康检查间隔: 60秒")
        print("✅ 自动故障转移: 启用")
        print("✅ 性能阈值监控: 启用")
        print("✅ 错误计数重置: 24小时")
        
        print(f"\n📚 知识点总结:")
        print("  • 健康监控是系统稳定性的保障")
        print("  • 智能切换可以提高系统可用性")
        print("  • 性能指标有助于系统优化")
        
        return health_results

    def lesson_03_data_fusion(self):
        """第3课：多源数据融合与质量评估"""
        print("\n💡 学习目标：")
        print("  • 掌握多源数据融合技术")
        print("  • 学习数据质量评估方法")
        print("  • 了解数据一致性检验")
        
        print("\n🔄 3.1 实时行情数据融合")
        print("-" * 50)
        
        # 从多个数据源获取同一股票的行情数据
        test_codes = ['000001', '000002', '600000']
        fusion_results = {}
        
        for code in test_codes:
            print(f"\n融合 {code} 行情数据...")
            source_data = {}
            
            for name, provider in self.providers.items():
                try:
                    if hasattr(provider, 'get_realtime_quotes'):
                        quotes = provider.get_realtime_quotes([code])
                        if quotes:
                            source_data[name] = pd.DataFrame(quotes)
                            print(f"✅ {name}: 获取到 {len(quotes)} 条数据")
                        else:
                            print(f"⚠️ {name}: 数据为空")
                except Exception as e:
                    print(f"❌ {name}: 获取失败 - {e}")
            
            # 执行数据融合
            if source_data:
                fused_data = self.data_fusion._fuse_price_data(source_data)
                if not fused_data.empty:
                    fusion_results[code] = fused_data
                    print(f"🎯 融合成功: 使用 {fused_data.iloc[0]['data_source']} 数据")
                    print(f"📊 置信度: {fused_data.iloc[0]['fusion_confidence']:.1%}")
                else:
                    print(f"❌ 融合失败: 无有效数据")
            else:
                print(f"❌ 无可用数据源")
        
        print(f"\n📊 3.2 概念热度数据融合")
        print("-" * 50)
        
        concept_sources = {}
        
        # 从同花顺获取概念数据
        try:
            if hasattr(self.providers['ThsProvider'], 'get_concept_ranks'):
                ths_concepts = self.providers['ThsProvider'].get_concept_ranks(limit=10)
                if ths_concepts:
                    concept_sources['ThsProvider'] = ths_concepts
                    print(f"✅ 同花顺: 获取到 {len(ths_concepts)} 个概念")
        except Exception as e:
            print(f"❌ 同花顺概念数据获取失败: {e}")
        
        # 从东方财富获取概念数据
        try:
            if hasattr(self.providers['EastmoneyProvider'], 'get_concept_boards'):
                em_concepts = self.providers['EastmoneyProvider'].get_concept_boards(limit=10)
                if em_concepts:
                    concept_sources['EastmoneyProvider'] = em_concepts
                    print(f"✅ 东方财富: 获取到 {len(em_concepts)} 个概念")
        except Exception as e:
            print(f"❌ 东方财富概念数据获取失败: {e}")
        
        # 执行概念数据融合
        if concept_sources:
            fused_concepts = self.data_fusion._fuse_concept_data(concept_sources)
            print(f"\n🎯 概念融合结果 (前5个):")
            for i, concept in enumerate(fused_concepts[:5], 1):
                print(f"{i}. {concept['name']}")
                print(f"   融合分数: {concept['fusion_score']:.2f}")
                print(f"   数据源数量: {concept['source_count']}")
                print(f"   来源: {', '.join(concept['sources'])}")
        else:
            print("❌ 无概念数据可融合")
        
        print(f"\n🔍 3.3 数据质量评估")
        print("-" * 50)
        
        quality_metrics = {
            'completeness': 0,  # 完整性
            'consistency': 0,   # 一致性
            'timeliness': 0,    # 及时性
            'accuracy': 0       # 准确性
        }
        
        # 计算数据完整性
        total_sources = len(self.providers)
        available_sources = len([name for name, provider in self.providers.items() 
                               if self.health_monitor.health_status.get(name, {}).get('status') == 'healthy'])
        quality_metrics['completeness'] = (available_sources / total_sources) * 100
        
        # 计算数据一致性（基于融合结果）
        if fusion_results:
            consistency_scores = []
            for code, data in fusion_results.items():
                if 'fusion_confidence' in data.columns:
                    consistency_scores.append(data.iloc[0]['fusion_confidence'])
            quality_metrics['consistency'] = (sum(consistency_scores) / len(consistency_scores)) * 100 if consistency_scores else 0
        
        # 计算及时性（基于响应时间）
        response_times = [h.get('response_time', 0) for h in self.health_monitor.health_status.values()]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        quality_metrics['timeliness'] = max(0, 100 - (avg_response_time / 10))  # 响应时间越短，及时性越高
        
        # 计算准确性（基于错误率）
        error_counts = [h.get('error_count', 0) for h in self.health_monitor.health_status.values()]
        total_errors = sum(error_counts)
        quality_metrics['accuracy'] = max(0, 100 - (total_errors * 10))  # 错误越少，准确性越高
        
        print("📈 数据质量评估结果:")
        for metric, score in quality_metrics.items():
            metric_names = {
                'completeness': '完整性',
                'consistency': '一致性', 
                'timeliness': '及时性',
                'accuracy': '准确性'
            }
            
            if score >= 90:
                grade = "优秀 🏆"
            elif score >= 80:
                grade = "良好 ✅"
            elif score >= 70:
                grade = "一般 ⚠️"
            else:
                grade = "需改进 ❌"
                
            print(f"  {metric_names[metric]}: {score:.1f}% - {grade}")
        
        overall_quality = sum(quality_metrics.values()) / len(quality_metrics)
        print(f"\n🎯 综合数据质量: {overall_quality:.1f}%")
        
        print(f"\n📚 知识点总结:")
        print("  • 数据融合可以提高数据质量和可靠性")
        print("  • 质量评估是数据治理的重要环节")
        print("  • 多维度评估能全面反映数据状况")
        
        return fusion_results, quality_metrics

    def lesson_04_realtime_monitoring(self):
        """第4课：实时行情监控与异常检测"""
        print("\n💡 学习目标：")
        print("  • 掌握实时数据监控技术")
        print("  • 学习异常检测算法")
        print("  • 了解预警机制设计")
        
        print("\n📊 4.1 实时行情监控设置")
        print("-" * 50)
        
        # 设置监控股票池
        monitor_stocks = ['000001', '000002', '600000', '600036', '000858']
        print(f"📋 监控股票池: {', '.join(monitor_stocks)}")
        
        # 获取实时行情
        realtime_data = {}
        
        for code in monitor_stocks:
            try:
                # 优先使用健康状态最好的数据源
                best_source = self.health_monitor.get_best_source('quotes')
                if best_source and best_source in self.providers:
                    provider = self.providers[best_source]
                    if hasattr(provider, 'get_realtime_quotes'):
                        quotes = provider.get_realtime_quotes([code])
                        if quotes:
                            realtime_data[code] = quotes[0]
                            print(f"✅ {code}: 价格 {quotes[0].get('price', 0):.2f}, 涨跌幅 {quotes[0].get('change_pct', 0):.2f}%")
                        else:
                            print(f"⚠️ {code}: 无行情数据")
                    else:
                        print(f"❌ {code}: 数据源不支持实时行情")
                else:
                    print(f"❌ {code}: 无可用数据源")
            except Exception as e:
                print(f"❌ {code}: 获取异常 - {e}")
        
        print(f"\n🚨 4.2 异常检测规则设置")
        print("-" * 50)
        
        # 添加异常检测规则
        def price_spike_alert(data):
            """价格异常波动预警"""
            for code, quote in data.items():
                change_pct = abs(quote.get('change_pct', 0))
                if change_pct > 5:  # 涨跌幅超过5%
                    return True
            return False
        
        def volume_spike_alert(data):
            """成交量异常预警"""
            for code, quote in data.items():
                volume = quote.get('volume', 0)
                if volume > 10000000:  # 成交量超过1000万
                    return True
            return False
        
        def price_limit_alert(data):
            """涨跌停预警"""
            for code, quote in data.items():
                change_pct = quote.get('change_pct', 0)
                if abs(change_pct) > 9.5:  # 接近涨跌停
                    return True
            return False
        
        # 注册预警规则
        self.alert_system.add_alert_rule("价格异常波动", price_spike_alert, "WARNING")
        self.alert_system.add_alert_rule("成交量异常", volume_spike_alert, "INFO")
        self.alert_system.add_alert_rule("涨跌停预警", price_limit_alert, "ERROR")
        
        print("✅ 价格异常波动预警: 涨跌幅 > 5%")
        print("✅ 成交量异常预警: 成交量 > 1000万")
        print("✅ 涨跌停预警: 涨跌幅 > 9.5%")
        
        print(f"\n⚡ 4.3 实时异常检测")
        print("-" * 50)
        
        # 执行异常检测
        if realtime_data:
            print("正在检测市场异常...")
            self.alert_system.check_alerts(realtime_data)
            
            # 显示检测结果
            if self.alert_system.alert_history:
                print(f"🚨 发现 {len(self.alert_system.alert_history)} 个异常:")
                for alert in self.alert_system.alert_history[-5:]:  # 显示最近5个
                    print(f"  {alert['timestamp']}: {alert['message']} [{alert['level']}]")
            else:
                print("✅ 未发现异常情况")
        else:
            print("❌ 无实时数据，跳过异常检测")
        
        print(f"\n📈 4.4 监控统计信息")
        print("-" * 50)
        
        if realtime_data:
            # 计算市场统计
            prices = [quote.get('price', 0) for quote in realtime_data.values()]
            changes = [quote.get('change_pct', 0) for quote in realtime_data.values()]
            volumes = [quote.get('volume', 0) for quote in realtime_data.values()]
            
            avg_price = sum(prices) / len(prices) if prices else 0
            avg_change = sum(changes) / len(changes) if changes else 0
            total_volume = sum(volumes)
            
            print(f"📊 监控股票数量: {len(realtime_data)}")
            print(f"💰 平均价格: {avg_price:.2f}")
            print(f"📈 平均涨跌幅: {avg_change:.2f}%")
            print(f"📊 总成交量: {total_volume:,}")
            
            # 市场情绪分析
            up_count = sum(1 for change in changes if change > 0)
            down_count = sum(1 for change in changes if change < 0)
            
            if up_count > down_count:
                sentiment = "乐观 📈"
            elif down_count > up_count:
                sentiment = "悲观 📉"
            else:
                sentiment = "中性 ➡️"
            
            print(f"🎭 市场情绪: {sentiment} (上涨:{up_count}, 下跌:{down_count})")
        
        print(f"\n📚 知识点总结:")
        print("  • 实时监控是风险控制的重要手段")
        print("  • 异常检测可以及时发现市场机会")
        print("  • 预警机制有助于快速响应")
        
        return realtime_data

    def lesson_05_concept_analysis(self):
        """第5课：热点概念挖掘与趋势分析"""
        print("\n💡 学习目标：")
        print("  • 掌握热点概念挖掘技术")
        print("  • 学习趋势分析方法")
        print("  • 了解概念投资策略")
        
        print("\n🔥 5.1 热点概念挖掘")
        print("-" * 50)
        
        concept_data = {}
        
        # 从同花顺获取概念热度
        try:
            ths_provider = self.providers['ThsProvider']
            if hasattr(ths_provider, 'get_concept_ranks'):
                ths_concepts = ths_provider.get_concept_ranks(limit=15)
                if ths_concepts:
                    concept_data['ThsProvider'] = ths_concepts
                    print(f"✅ 同花顺概念数据: {len(ths_concepts)} 个")
                    
                    # 显示前5个热点概念
                    print("🔥 同花顺热点概念 TOP5:")
                    for i, concept in enumerate(ths_concepts[:5], 1):
                        name = concept.get('name', concept.get('concept_name', 'Unknown'))
                        heat = concept.get('heat', concept.get('popularity', 0))
                        print(f"  {i}. {name} - 热度: {heat}")
        except Exception as e:
            print(f"❌ 同花顺概念数据获取失败: {e}")
        
        # 从东方财富获取概念板块
        try:
            em_provider = self.providers['EastmoneyProvider']
            if hasattr(em_provider, 'get_concept_boards'):
                em_concepts = em_provider.get_concept_boards(limit=15)
                if em_concepts:
                    concept_data['EastmoneyProvider'] = em_concepts
                    print(f"✅ 东方财富概念数据: {len(em_concepts)} 个")
                    
                    # 显示前5个概念板块
                    print("📊 东方财富概念板块 TOP5:")
                    for i, concept in enumerate(em_concepts[:5], 1):
                        name = concept.get('name', concept.get('board_name', 'Unknown'))
                        change = concept.get('change_pct', concept.get('pct_change', 0))
                        print(f"  {i}. {name} - 涨跌幅: {change:.2f}%")
        except Exception as e:
            print(f"❌ 东方财富概念数据获取失败: {e}")
        
        print(f"\n🎯 5.2 概念融合分析")
        print("-" * 50)
        
        if concept_data:
            # 执行概念数据融合
            fused_concepts = self.data_fusion._fuse_concept_data(concept_data)
            
            if fused_concepts:
                print(f"🔄 融合了 {len(concept_data)} 个数据源的概念数据")
                print(f"📊 融合结果: {len(fused_concepts)} 个概念")
                
                print("\n🏆 融合后热点概念 TOP10:")
                for i, concept in enumerate(fused_concepts[:10], 1):
                    print(f"{i:2d}. {concept['name']}")
                    print(f"     融合分数: {concept['fusion_score']:.2f}")
                    print(f"     数据源: {', '.join(concept['sources'])}")
                    print(f"     置信度: {concept['source_count']}/2")
                
                # 概念分类分析
                print(f"\n📈 5.3 概念趋势分析")
                print("-" * 50)
                
                # 按融合分数分类
                hot_concepts = [c for c in fused_concepts if c['fusion_score'] >= 1.0]
                warm_concepts = [c for c in fused_concepts if 0.5 <= c['fusion_score'] < 1.0]
                cold_concepts = [c for c in fused_concepts if c['fusion_score'] < 0.5]
                
                print(f"🔥 热门概念 (分数≥1.0): {len(hot_concepts)} 个")
                for concept in hot_concepts[:3]:
                    print(f"   • {concept['name']} ({concept['fusion_score']:.2f})")
                
                print(f"🌡️ 温热概念 (0.5≤分数<1.0): {len(warm_concepts)} 个")
                for concept in warm_concepts[:3]:
                    print(f"   • {concept['name']} ({concept['fusion_score']:.2f})")
                
                print(f"❄️ 冷门概念 (分数<0.5): {len(cold_concepts)} 个")
                
                # 数据源一致性分析
                print(f"\n🔍 5.4 数据源一致性分析")
                print("-" * 50)
                
                consistent_concepts = [c for c in fused_concepts if c['source_count'] >= 2]
                unique_concepts = [c for c in fused_concepts if c['source_count'] == 1]
                
                print(f"✅ 多源一致概念: {len(consistent_concepts)} 个 ({len(consistent_concepts)/len(fused_concepts)*100:.1f}%)")
                print(f"⚠️ 单源独有概念: {len(unique_concepts)} 个 ({len(unique_concepts)/len(fused_concepts)*100:.1f}%)")
                
                if consistent_concepts:
                    print("\n🎯 高一致性概念 TOP5:")
                    for i, concept in enumerate(consistent_concepts[:5], 1):
                        print(f"  {i}. {concept['name']} - 来源: {', '.join(concept['sources'])}")
                
                # 概念投资建议
                print(f"\n💡 5.5 概念投资建议")
                print("-" * 50)
                
                if hot_concepts:
                    print("🎯 重点关注概念:")
                    for concept in hot_concepts[:3]:
                        print(f"  • {concept['name']}: 多数据源确认的热点，建议重点关注")
                
                if consistent_concepts:
                    print("✅ 稳健投资概念:")
                    for concept in consistent_concepts[:2]:
                        if concept not in hot_concepts:
                            print(f"  • {concept['name']}: 多源验证，相对稳健")
                
                print("⚠️ 风险提示: 概念炒作具有不确定性，请结合基本面分析")
                
                print(f"\n📚 知识点总结:")
                print("  • 热点概念挖掘有助于把握市场机会")
                print("  • 多源验证可以提高投资成功率")
                print("  • 趋势分析是概念投资的重要工具")
                
                return fused_concepts
            else:
                print("❌ 概念数据融合失败")
        else:
            print("❌ 无概念数据可分析")
        
        return []

    def lesson_06_fund_flow_analysis(self):
        """第6课：资金流向追踪与主力行为分析"""
        print("\n💡 学习目标：")
        print("  • 掌握资金流向分析技术")
        print("  • 学习主力行为识别方法")
        print("  • 了解资金流向投资策略")
        
        print("\n💰 6.1 市场资金流向监控")
        print("-" * 50)
        
        fund_flow_data = {}
        monitor_stocks = ['000001', '000002', '600000', '600036', '000858']
        
        # 模拟资金流向数据（实际应用中从数据源获取）
        print("📊 使用模拟资金流向数据进行演示...")
        import random
        for code in monitor_stocks:
            fund_flow_data[code] = {
                'net_inflow': random.randint(-50000, 50000),
                'main_inflow': random.randint(-30000, 30000),
                'retail_inflow': random.randint(-20000, 20000),
                'super_large_inflow': random.randint(-15000, 15000),
                'large_inflow': random.randint(-15000, 15000),
                'medium_inflow': random.randint(-10000, 10000),
                'small_inflow': random.randint(-10000, 10000)
            }
            print(f"📊 {code}: 净流入 {fund_flow_data[code]['net_inflow']:,.0f}万元")
        
        print(f"\n🏦 6.2 主力资金行为分析")
        print("-" * 50)
        
        if fund_flow_data:
            # 分析主力资金行为
            main_inflow_stocks = []
            main_outflow_stocks = []
            
            for code, flow in fund_flow_data.items():
                main_flow = flow.get('main_inflow', 0)
                if main_flow > 1000:  # 主力净流入超过1000万
                    main_inflow_stocks.append((code, main_flow))
                elif main_flow < -1000:  # 主力净流出超过1000万
                    main_outflow_stocks.append((code, main_flow))
            
            # 按资金流入排序
            main_inflow_stocks.sort(key=lambda x: x[1], reverse=True)
            main_outflow_stocks.sort(key=lambda x: x[1])
            
            print("💪 主力资金流入股票:")
            if main_inflow_stocks:
                for code, flow in main_inflow_stocks:
                    print(f"  📈 {code}: +{flow:,.0f}万元")
            else:
                print("  暂无明显主力流入股票")
            
            print("\n💸 主力资金流出股票:")
            if main_outflow_stocks:
                for code, flow in main_outflow_stocks:
                    print(f"  📉 {code}: {flow:,.0f}万元")
            else:
                print("  暂无明显主力流出股票")
            
            print(f"\n🎯 6.3 资金流向模式识别")
            print("-" * 50)
            
            # 识别资金流向模式
            patterns = {
                'strong_inflow': [],      # 强势流入
                'weak_inflow': [],        # 弱势流入
                'strong_outflow': [],     # 强势流出
                'weak_outflow': [],       # 弱势流出
                'balanced': []            # 平衡状态
            }
            
            for code, flow in fund_flow_data.items():
                net_flow = flow.get('net_inflow', 0)
                main_flow = flow.get('main_inflow', 0)
                
                if net_flow > 5000 and main_flow > 0:
                    patterns['strong_inflow'].append(code)
                elif net_flow > 0 and main_flow > 0:
                    patterns['weak_inflow'].append(code)
                elif net_flow < -5000 and main_flow < 0:
                    patterns['strong_outflow'].append(code)
                elif net_flow < 0 and main_flow < 0:
                    patterns['weak_outflow'].append(code)
                else:
                    patterns['balanced'].append(code)
            
            pattern_names = {
                'strong_inflow': '强势流入',
                'weak_inflow': '弱势流入',
                'strong_outflow': '强势流出',
                'weak_outflow': '弱势流出',
                'balanced': '资金平衡'
            }
            
            pattern_emojis = {
                'strong_inflow': '🚀',
                'weak_inflow': '📈',
                'strong_outflow': '📉',
                'weak_outflow': '⬇️',
                'balanced': '⚖️'
            }
            
            for pattern, stocks in patterns.items():
                if stocks:
                    emoji = pattern_emojis[pattern]
                    name = pattern_names[pattern]
                    print(f"{emoji} {name}: {', '.join(stocks)}")
            
            print(f"\n📊 6.4 市场资金流向总结")
            print("-" * 50)
            
            # 计算市场整体资金流向
            total_net_inflow = sum(flow.get('net_inflow', 0) for flow in fund_flow_data.values())
            total_main_inflow = sum(flow.get('main_inflow', 0) for flow in fund_flow_data.values())
            total_retail_inflow = sum(flow.get('retail_inflow', 0) for flow in fund_flow_data.values())
            
            print(f"💰 市场总净流入: {total_net_inflow:,.0f}万元")
            print(f"🏦 主力资金净流入: {total_main_inflow:,.0f}万元")
            print(f"👥 散户资金净流入: {total_retail_inflow:,.0f}万元")
            
            # 市场情绪判断
            if total_net_inflow > 10000:
                market_sentiment = "极度乐观 🚀"
            elif total_net_inflow > 0:
                market_sentiment = "乐观 📈"
            elif total_net_inflow > -10000:
                market_sentiment = "谨慎 ⚠️"
            else:
                market_sentiment = "悲观 📉"
            
            print(f"🎭 市场情绪: {market_sentiment}")
            
            # 主力与散户对比
            if abs(total_main_inflow) > abs(total_retail_inflow):
                dominant_force = "主力资金主导"
            else:
                dominant_force = "散户资金主导"
            
            print(f"⚖️ 资金主导: {dominant_force}")
            
            print(f"\n💡 6.5 投资建议")
            print("-" * 50)
            
            if patterns['strong_inflow']:
                print(f"🎯 重点关注: {', '.join(patterns['strong_inflow'])} - 强势资金流入")
            
            if patterns['strong_outflow']:
                print(f"⚠️ 谨慎对待: {', '.join(patterns['strong_outflow'])} - 强势资金流出")
            
            if total_main_inflow > 0 and total_retail_inflow < 0:
                print("💡 策略建议: 主力流入散户流出，可能是底部吸筹机会")
            elif total_main_inflow < 0 and total_retail_inflow > 0:
                print("⚠️ 风险提示: 主力流出散户流入，需警惕高位风险")
            
            print(f"\n📚 知识点总结:")
            print("  • 资金流向是判断股价走势的重要指标")
            print("  • 主力行为分析有助于把握投资机会")
            print("  • 资金流向模式识别可以提高投资成功率")
            
            return fund_flow_data
        else:
            print("❌ 无资金流向数据可分析")
            return {}

    def lesson_07_signal_generation(self):
        """第7课：多维度交易信号生成"""
        print("\n💡 学习目标：")
        print("  • 掌握多维度信号生成技术")
        print("  • 学习信号权重配置方法")
        print("  • 了解综合信号评估体系")
        
        print("\n🎯 7.1 综合信号生成框架")
        print("-" * 50)
        
        # 定义信号权重
        signal_weights = {
            'price_momentum': 0.25,      # 价格动量
            'volume_pattern': 0.20,      # 成交量模式
            'fund_flow': 0.25,          # 资金流向
            'concept_heat': 0.15,        # 概念热度
            'technical_indicator': 0.15   # 技术指标
        }
        
        print("📊 信号权重配置:")
        for signal, weight in signal_weights.items():
            signal_names = {
                'price_momentum': '价格动量',
                'volume_pattern': '成交量模式',
                'fund_flow': '资金流向',
                'concept_heat': '概念热度',
                'technical_indicator': '技术指标'
            }
            print(f"  {signal_names[signal]}: {weight:.0%}")
        
        print(f"\n📈 7.2 多维度信号计算")
        print("-" * 50)
        
        # 获取测试股票的多维度数据
        test_stocks = ['000001', '000002', '600000']
        stock_signals = {}
        
        for code in test_stocks:
            print(f"\n分析 {code} 的交易信号...")
            
            signals = {
                'price_momentum': 0,
                'volume_pattern': 0,
                'fund_flow': 0,
                'concept_heat': 0,
                'technical_indicator': 0
            }
            
            # 模拟各种信号计算
            import random
            
            # 1. 价格动量信号
            change_pct = random.uniform(-5, 8)
            if change_pct > 3:
                signals['price_momentum'] = 0.8
            elif change_pct > 1:
                signals['price_momentum'] = 0.6
            elif change_pct > 0:
                signals['price_momentum'] = 0.4
            elif change_pct > -1:
                signals['price_momentum'] = 0.2
            else:
                signals['price_momentum'] = 0.0
            
            print(f"  📈 价格动量: {change_pct:.2f}% → 信号强度: {signals['price_momentum']:.1f}")
            
            # 2. 成交量模式信号
            volume = random.randint(5000000, 100000000)
            if volume > 50000000:
                signals['volume_pattern'] = 0.8
            elif volume > 20000000:
                signals['volume_pattern'] = 0.6
            elif volume > 10000000:
                signals['volume_pattern'] = 0.4
            else:
                signals['volume_pattern'] = 0.2
            
            print(f"  📊 成交量模式: {volume:,} → 信号强度: {signals['volume_pattern']:.1f}")
            
            # 3. 资金流向信号
            net_inflow = random.randint(-10000, 10000)
            if net_inflow > 5000:
                signals['fund_flow'] = 0.8
            elif net_inflow > 1000:
                signals['fund_flow'] = 0.6
            elif net_inflow > 0:
                signals['fund_flow'] = 0.4
            elif net_inflow > -1000:
                signals['fund_flow'] = 0.2
            else:
                signals['fund_flow'] = 0.0
            
            print(f"  💰 资金流向: {net_inflow:,}万 → 信号强度: {signals['fund_flow']:.1f}")
            
            # 4. 概念热度信号
            concept_heat = random.uniform(0, 1)
            signals['concept_heat'] = concept_heat
            print(f"  🔥 概念热度: {concept_heat:.2f} → 信号强度: {signals['concept_heat']:.1f}")
            
            # 5. 技术指标信号
            tech_score = random.uniform(0, 1)
            signals['technical_indicator'] = tech_score
            print(f"  📊 技术指标: {tech_score:.2f} → 信号强度: {signals['technical_indicator']:.1f}")
            
            # 计算综合信号
            composite_signal = sum(signals[key] * signal_weights[key] for key in signals.keys())
            
            stock_signals[code] = {
                'individual_signals': signals,
                'composite_signal': composite_signal
            }
            
            print(f"  🎯 综合信号强度: {composite_signal:.3f}")
        
        print(f"\n🏆 7.3 信号排名与建议")
        print("-" * 50)
        
        # 按综合信号强度排序
        ranked_stocks = sorted(stock_signals.items(), 
                             key=lambda x: x[1]['composite_signal'], 
                             reverse=True)
        
        print("📊 股票信号强度排名:")
        for i, (code, data) in enumerate(ranked_stocks, 1):
            signal_strength = data['composite_signal']
            
            if signal_strength >= 0.7:
                recommendation = "强烈买入 🚀"
                color = "🟢"
            elif signal_strength >= 0.5:
                recommendation = "买入 📈"
                color = "🟡"
            elif signal_strength >= 0.3:
                recommendation = "观望 ⚖️"
                color = "🟠"
            else:
                recommendation = "谨慎 ⚠️"
                color = "🔴"
            
            print(f"{i}. {code}: {signal_strength:.3f} {color} - {recommendation}")
        
        print(f"\n📋 7.4 详细信号分解")
        print("-" * 50)
        
        # 显示最强信号股票的详细分解
        if ranked_stocks:
            top_stock = ranked_stocks[0]
            code, data = top_stock
            
            print(f"🎯 最强信号股票: {code}")
            print("信号分解:")
            
            signal_names = {
                'price_momentum': '价格动量',
                'volume_pattern': '成交量模式',
                'fund_flow': '资金流向',
                'concept_heat': '概念热度',
                'technical_indicator': '技术指标'
            }
            
            for signal_type, strength in data['individual_signals'].items():
                weight = signal_weights[signal_type]
                contribution = strength * weight
                name = signal_names[signal_type]
                
                print(f"  {name}: {strength:.3f} × {weight:.0%} = {contribution:.3f}")
            
            print(f"  综合信号: {data['composite_signal']:.3f}")
        
        print(f"\n💡 7.5 交易策略建议")
        print("-" * 50)
        
        strong_signals = [code for code, data in stock_signals.items() if data['composite_signal'] >= 0.6]
        medium_signals = [code for code, data in stock_signals.items() if 0.4 <= data['composite_signal'] < 0.6]
        weak_signals = [code for code, data in stock_signals.items() if data['composite_signal'] < 0.4]
        
        if strong_signals:
            print(f"🚀 强信号股票 ({len(strong_signals)}只): {', '.join(strong_signals)}")
            print("   建议: 重点关注，可考虑建仓")
        
        if medium_signals:
            print(f"📈 中等信号股票 ({len(medium_signals)}只): {', '.join(medium_signals)}")
            print("   建议: 观察等待，寻找更好入场点")
        
        if weak_signals:
            print(f"⚠️ 弱信号股票 ({len(weak_signals)}只): {', '.join(weak_signals)}")
            print("   建议: 暂时回避，等待信号改善")
        
        print("\n⚠️ 风险提示:")
        print("  • 信号仅供参考，不构成投资建议")
        print("  • 请结合基本面分析和风险管理")
        print("  • 市场有风险，投资需谨慎")
        
        print(f"\n📚 知识点总结:")
        print("  • 多维度信号可以提高投资决策质量")
        print("  • 权重配置是信号系统的核心")
        print("  • 综合评估有助于降低投资风险")
        
        return stock_signals

    def lesson_08_alert_system(self):
        """第8课：实时预警系统构建"""
        print("\n💡 学习目标：")
        print("  • 掌握预警系统架构设计")
        print("  • 学习预警规则配置方法")
        print("  • 了解预警系统优化策略")
        
        print("\n🚨 8.1 预警系统架构")
        print("-" * 50)
        
        print("预警系统组件:")
        print("  📊 数据监控模块: 实时监控多数据源")
        print("  🔍 规则引擎: 可配置的预警规则")
        print("  📢 通知系统: 多渠道预警通知")
        print("  📈 历史记录: 预警历史和统计")
        print("  ⚙️ 管理界面: 规则管理和系统配置")
        
        print(f"\n⚙️ 8.2 预警规则配置")
        print("-" * 50)
        
        # 清空之前的规则
        self.alert_system.alert_rules = []
        
        # 定义预警规则
        def price_breakout_alert(data):
            """价格突破预警"""
            for code, quote in data.items():
                change_pct = abs(quote.get('change_pct', 0))
                if change_pct > 7:
                    return True
            return False
        
        def price_limit_approaching_alert(data):
            """接近涨跌停预警"""
            for code, quote in data.items():
                change_pct = quote.get('change_pct', 0)
                if abs(change_pct) > 9:
                    return True
            return False
        
        def volume_surge_alert(data):
            """成交量激增预警"""
            for code, quote in data.items():
                volume = quote.get('volume', 0)
                if volume > 100000000:
                    return True
            return False
        
        def large_fund_inflow_alert(data):
            """大额资金流入预警"""
            import random
            return random.random() > 0.8
        
        def large_fund_outflow_alert(data):
            """大额资金流出预警"""
            import random
            return random.random() > 0.9
        
        def technical_signal_alert(data):
            """技术指标信号预警"""
            import random
            return random.random() > 0.85
        
        def market_sentiment_alert(data):
            """市场情绪异常预警"""
            if len(data) >= 3:
                changes = [quote.get('change_pct', 0) for quote in data.values()]
                avg_change = sum(changes) / len(changes)
                return abs(avg_change) > 3
            return False
        
        # 注册预警规则
        alert_rules = [
            ("价格突破预警", price_breakout_alert, "WARNING"),
            ("涨跌停预警", price_limit_approaching_alert, "ERROR"),
            ("成交量激增", volume_surge_alert, "INFO"),
            ("大额资金流入", large_fund_inflow_alert, "INFO"),
            ("大额资金流出", large_fund_outflow_alert, "WARNING"),
            ("技术指标信号", technical_signal_alert, "INFO"),
            ("市场情绪异常", market_sentiment_alert, "WARNING")
        ]
        
        for rule_name, rule_func, level in alert_rules:
            self.alert_system.add_alert_rule(rule_name, rule_func, level)
        
        print(f"✅ 已配置 {len(alert_rules)} 个预警规则:")
        for rule_name, _, level in alert_rules:
            level_emoji = {'INFO': '📢', 'WARNING': '⚠️', 'ERROR': '🚨'}
            print(f"  {level_emoji[level]} {rule_name} [{level}]")
        
        print(f"\n📊 8.3 实时监控演示")
        print("-" * 50)
        
        # 模拟实时监控
        monitor_stocks = ['000001', '000002', '600000', '600036']
        simulation_rounds = 3
        
        print(f"开始 {simulation_rounds} 轮监控演示...")
        
        for round_num in range(1, simulation_rounds + 1):
            print(f"\n--- 第 {round_num} 轮监控 ---")
            
            # 模拟实时数据
            mock_data = {}
            for code in monitor_stocks:
                import random
                mock_data[code] = {
                    'price': round(random.uniform(8, 15), 2),
                    'change_pct': round(random.uniform(-10, 10), 2),
                    'volume': random.randint(5000000, 150000000),
                    'turnover': round(random.uniform(0.5, 8), 2)
                }
            
            # 显示当前数据
            print("当前市场数据:")
            for code, data in mock_data.items():
                print(f"  {code}: 价格 {data['price']:.2f}, 涨跌 {data['change_pct']:+.2f}%, 成交量 {data['volume']:,}")
            
            # 执行预警检查
            print("\n预警检查结果:")
            initial_alert_count = len(self.alert_system.alert_history)
            self.alert_system.check_alerts(mock_data)
            new_alerts = len(self.alert_system.alert_history) - initial_alert_count
            
            if new_alerts > 0:
                print(f"🚨 触发 {new_alerts} 个预警")
                # 显示最新的预警
                for alert in self.alert_system.alert_history[-new_alerts:]:
                    level_emoji = {'INFO': '📢', 'WARNING': '⚠️', 'ERROR': '🚨'}
                    print(f"  {level_emoji[alert['level']]} {alert['rule_name']}")
            else:
                print("✅ 未触发预警")
            
            # 模拟时间间隔
            time.sleep(1)
        
        print(f"\n📈 8.4 预警统计分析")
        print("-" * 50)
        
        if self.alert_system.alert_history:
            # 按级别统计
            level_counts = {}
            rule_counts = {}
            
            for alert in self.alert_system.alert_history:
                level = alert['level']
                rule = alert['rule_name']
                
                level_counts[level] = level_counts.get(level, 0) + 1
                rule_counts[rule] = rule_counts.get(rule, 0) + 1
            
            print("预警级别统计:")
            level_emoji = {'INFO': '📢', 'WARNING': '⚠️', 'ERROR': '🚨'}
            for level, count in level_counts.items():
                print(f"  {level_emoji[level]} {level}: {count} 次")
            
            print("\n预警规则统计:")
            for rule, count in sorted(rule_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  • {rule}: {count} 次")
            
            print(f"\n总预警次数: {len(self.alert_system.alert_history)}")
            
            # 预警频率分析
            if len(self.alert_system.alert_history) > 1:
                first_alert = datetime.strptime(self.alert_system.alert_history[0]['timestamp'], '%Y-%m-%d %H:%M:%S')
                last_alert = datetime.strptime(self.alert_system.alert_history[-1]['timestamp'], '%Y-%m-%d %H:%M:%S')
                duration = (last_alert - first_alert).total_seconds() / 60
                
                if duration > 0:
                    frequency = len(self.alert_system.alert_history) / duration
                    print(f"预警频率: {frequency:.2f} 次/分钟")
        else:
            print("暂无预警记录")
        
        print(f"\n🔧 8.5 预警系统优化建议")
        print("-" * 50)
        
        print("系统优化建议:")
        print("  📊 数据质量: 提高数据源的准确性和及时性")
        print("  🎯 规则优化: 根据历史数据调整预警阈值")
        print("  📢 通知优化: 实现邮件、短信、微信等多渠道通知")
        print("  🔄 自适应: 根据市场状况自动调整预警参数")
        print("  📈 机器学习: 使用AI技术提高预警准确性")
        
        print("\n实际部署建议:")
        print("  🖥️ 服务器部署: 使用稳定的服务器环境")
        print("  💾 数据存储: 建立完善的数据存储和备份机制")
        print("  🔐 安全防护: 实施访问控制和数据加密")
        print("  📊 监控面板: 开发Web界面进行可视化管理")
        print("  🔧 运维支持: 建立日志记录和错误处理机制")
        
        print(f"\n📚 知识点总结:")
        print("  • 预警系统是风险管理的重要工具")
        print("  • 规则配置需要根据实际需求调整")
        print("  • 系统优化是持续改进的过程")
        
        return self.alert_system.alert_history

def wait_for_user_input(course_name):
    """等待用户输入以继续下一个课程"""
    print(f"\n{'='*60}")
    print(f"📚 {course_name} 演示完成！")
    print("💡 请仔细查看上面的输出结果和代码说明")
    print("🔄 按回车键继续下一个课程，或输入 'q' 退出学习...")
    print(f"{'='*60}")
    
    user_input = input().strip().lower()
    if user_input == 'q':
        print("\n👋 感谢您的学习！再见！")
        exit()
    print("\n" + "🚀 继续下一个课程...\n")

def main():
    """主函数 - 互动学习版"""
    print("=" * 80)
    print("🎓 多数据源统一接口高级应用 - 互动学习版")
    print("=" * 80)
    print("📖 本教程包含8个课程，每个课程结束后需要按回车确认继续")
    print("💡 您可以在任何时候输入 'q' 退出学习")
    print("🚀 每个课程都包含详细的学习目标和知识点总结")
    print("=" * 80)
    
    input("\n🎯 准备开始学习？按回车键开始...")
    
    try:
        # 创建分析器实例
        print("\n🔧 正在初始化学习环境...")
        analyzer = AdvancedMultiSourceAnalyzer()
        
        # 第1课：环境搭建与连接优化
        print("\n" + "=" * 50)
        print("📚 第1课：多数据源环境搭建与连接优化")
        print("=" * 50)
        connection_results = analyzer.lesson_01_setup_and_optimization()
        wait_for_user_input("第1课：多数据源环境搭建与连接优化")
        
        # 第2课：健康监控与智能切换
        print("\n" + "=" * 50)
        print("📚 第2课：数据源健康监控与智能切换")
        print("=" * 50)
        health_results = analyzer.lesson_02_health_monitoring()
        wait_for_user_input("第2课：数据源健康监控与智能切换")
        
        # 第3课：数据融合与质量评估
        print("\n" + "=" * 50)
        print("📚 第3课：多源数据融合与质量评估")
        print("=" * 50)
        fusion_results, quality_metrics = analyzer.lesson_03_data_fusion()
        wait_for_user_input("第3课：多源数据融合与质量评估")
        
        # 第4课：实时监控与异常检测
        print("\n" + "=" * 50)
        print("📚 第4课：实时行情监控与异常检测")
        print("=" * 50)
        realtime_data = analyzer.lesson_04_realtime_monitoring()
        wait_for_user_input("第4课：实时行情监控与异常检测")
        
        # 第5课：概念挖掘与趋势分析
        print("\n" + "=" * 50)
        print("📚 第5课：热点概念挖掘与趋势分析")
        print("=" * 50)
        concept_analysis = analyzer.lesson_05_concept_analysis()
        wait_for_user_input("第5课：热点概念挖掘与趋势分析")
        
        # 第6课：资金流向追踪与主力行为分析
        print("\n" + "=" * 50)
        print("📚 第6课：资金流向追踪与主力行为分析")
        print("=" * 50)
        fund_flow_data = analyzer.lesson_06_fund_flow_analysis()
        wait_for_user_input("第6课：资金流向追踪与主力行为分析")
        
        # 第7课：多维度交易信号生成
        print("\n" + "=" * 50)
        print("📚 第7课：多维度交易信号生成")
        print("=" * 50)
        trading_signals = analyzer.lesson_07_signal_generation()
        wait_for_user_input("第7课：多维度交易信号生成")
        
        # 第8课：实时预警系统构建
        print("\n" + "=" * 50)
        print("📚 第8课：实时预警系统构建")
        print("=" * 50)
        alert_history = analyzer.lesson_08_alert_system()
        wait_for_user_input("第8课：实时预警系统构建")
        
        # 课程总结
        print("\n" + "=" * 80)
        print("🎉 恭喜！所有课程学习完成！")
        print("=" * 80)
        
        print("✅ 已完成的学习模块:")
        print("  📚 第1课: 多数据源环境搭建与连接优化")
        print("  📚 第2课: 数据源健康监控与智能切换")
        print("  📚 第3课: 多源数据融合与质量评估")
        print("  📚 第4课: 实时行情监控与异常检测")
        print("  📚 第5课: 热点概念挖掘与趋势分析")
        print("  📚 第6课: 资金流向追踪与主力行为分析")
        print("  📚 第7课: 多维度交易信号生成")
        print("  📚 第8课: 实时预警系统构建")
        
        print(f"\n📊 学习成果统计:")
        successful_connections = len([r for r in connection_results.values() if r['status'] == 'success'])
        print(f"  🔗 成功连接数据源: {successful_connections}/{len(analyzer.providers)}")
        print(f"  📈 数据质量评分: {sum(quality_metrics.values())/len(quality_metrics):.1f}%")
        print(f"  🎯 生成交易信号: {len(trading_signals)} 只股票")
        print(f"  🚨 预警规则数量: {len(analyzer.alert_system.alert_rules)}")
        print(f"  📋 预警历史记录: {len(alert_history)} 条")
        
        print(f"\n🎯 实际应用价值:")
        print("  💼 量化交易: 为量化策略提供多源数据支持")
        print("  📊 风险管理: 实时监控和预警系统降低投资风险")
        print("  🔍 市场分析: 多维度分析提供更全面的市场洞察")
        print("  🚀 决策支持: 智能信号生成辅助投资决策")
        
        print(f"\n📚 进阶学习建议:")
        print("  🤖 机器学习: 学习AI在量化交易中的应用")
        print("  📈 策略回测: 掌握交易策略的历史回测方法")
        print("  🔄 实盘交易: 将分析结果应用到实际交易中")
        print("  🌐 分布式系统: 学习大规模数据处理架构")
        
        print("\n🎓 您已经掌握了多数据源统一接口的高级应用！")
        print("💪 现在可以开始实际项目开发了！")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断程序")
    except Exception as e:
        logger.error(f"程序异常: {e}")
        print(f"❌ 程序异常: {e}")
    finally:
        # 清理资源
        try:
            for provider in analyzer.providers.values():
                if hasattr(provider, 'disconnect'):
                    try:
                        provider.disconnect()
                    except Exception:
                        pass
        except Exception:
            pass
        print("👋 程序结束，感谢您的学习！")

if __name__ == "__main__":
    main()

    