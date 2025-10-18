#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 qstock与EasyXT完美结合量化交易案例
=======================================

面向群体：熟悉qstock但不了解EasyXT的量化交易者
核心价值：展示如何将qstock的数据获取能力与EasyXT的交易执行能力完美结合

功能特色：
✨ qstock多源数据获取 (股票、基金、期货、数字货币)
✨ EasyXT专业交易执行 (支持A股、港股、美股)
✨ 智能策略引擎 (多种经典策略+自定义策略)
✨ 风险管理系统 (仓位控制、止盈止损、资金管理)
✨ 实时监控面板 (交易信号、持仓状态、收益分析)
✨ 回测验证系统 (历史数据验证策略有效性)

作者：MiniQMT团队
版本：2.0.0 (完美结合版)
日期：2025-01-26
GitHub: https://github.com/quant-king299/EasyXT
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys
import time
import json
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed

warnings.filterwarnings('ignore')

# 设置中文显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")

print("🚀 qstock与EasyXT完美结合量化交易系统")
print("=" * 60)

# ==================== 模块导入和环境检查 ====================

# 1. qstock数据获取模块
try:
    import qstock as qs
    QSTOCK_AVAILABLE = True
    print("✅ qstock数据模块加载成功")
    print(f"   版本信息: {getattr(qs, '__version__', '未知版本')}")
    print("   支持数据源: 股票、基金、期货、数字货币")
except ImportError as e:
    print(f"❌ qstock模块导入失败: {e}")
    print("💡 安装命令: pip install qstock")
    print("🔗 官方文档: https://github.com/tkfy920/qstock")
    QSTOCK_AVAILABLE = False

# 2. EasyXT交易执行模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(current_dir))

try:
    import easy_xt
    from easy_xt.api import EasyXT
    EASYXT_AVAILABLE = True
    print("✅ EasyXT交易模块加载成功")
    print("   支持市场: A股、港股、美股")
    print("   支持功能: 实时交易、持仓管理、资金查询")
except ImportError as e:
    print(f"❌ EasyXT模块导入失败: {e}")
    print("💡 请确保EasyXT模块在正确路径")
    print("🔗 项目地址: https://github.com/quant-king299/EasyXT")
    EASYXT_AVAILABLE = False

# 3. 技术分析模块
try:
    import talib
    TALIB_AVAILABLE = True
    print("✅ TA-Lib技术分析库加载成功")
except ImportError:
    print("⚠️ TA-Lib未安装，将使用内置技术指标")
    TALIB_AVAILABLE = False

print("=" * 60)

# ==================== 配置参数 ====================

# 交易配置
TRADING_CONFIG = {
    'userdata_path': r'D:\国金QMT交易端模拟\userdata_mini',  # 修改为实际路径
    'account_id': '39020958',  # 修改为实际账号
    'session_id': 'qstock_easyxt_session',
    'max_position_ratio': 0.8,  # 最大仓位比例
    'single_stock_ratio': 0.2,  # 单股最大仓位
    'stop_loss_ratio': 0.05,    # 止损比例
    'take_profit_ratio': 0.15,  # 止盈比例
}

# 策略配置
STRATEGY_CONFIG = {
    'data_period': 60,           # 数据周期(天)
    'signal_threshold': 70,      # 信号置信度阈值
    'min_volume': 1000000,       # 最小成交量过滤
    'price_range': (5, 200),     # 价格范围过滤
    'update_interval': 30,       # 更新间隔(秒)
}

# 监控股票池
STOCK_POOL = {
    'core_stocks': ['000001', '000002', '600000', '600036', '000858'],  # 核心股票
    'growth_stocks': ['300059', '300015', '002415', '000725'],          # 成长股
    'value_stocks': ['600519', '000858', '002304', '600036'],           # 价值股
    'tech_stocks': ['000063', '002230', '300496', '688981'],            # 科技股
}

class QStockEasyXTIntegration:
    """qstock与EasyXT完美结合的量化交易系统"""
    
    def __init__(self):
        """初始化系统"""
        print("\n🔧 初始化qstock与EasyXT集成系统...")
        
        # 数据存储
        self.data_cache = {}
        self.signal_history = []
        self.trade_history = []
        self.performance_metrics = {}
        
        # 系统状态
        self.is_trading_enabled = False
        self.is_monitoring = False
        self.last_update_time = None
        
        # 创建必要目录
        self.ensure_directories()
        
        # 初始化数据获取模块
        self.init_data_module()
        
        # 初始化交易执行模块
        self.init_trading_module()
        
        print("✅ 系统初始化完成")
    
    def ensure_directories(self):
        """确保必要目录存在"""
        directories = ['data', 'logs', 'reports', 'backtest']
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"📁 创建目录: {directory}")
    
    def init_data_module(self):
        """初始化qstock数据获取模块"""
        print("\n📊 初始化qstock数据获取模块...")
        
        if not QSTOCK_AVAILABLE:
            print("❌ qstock不可用，数据获取功能受限")
            return
        
        # 测试qstock连接
        try:
            # 测试获取基础数据 - 修复qstock API调用
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
            test_data = qs.get_data('000001', start=start_date, end=end_date)
            
            if test_data is not None and not test_data.empty:
                print("✅ qstock数据连接测试成功")
                print(f"   测试数据: {len(test_data)} 条记录")
                print(f"   最新价格: {test_data['close'].iloc[-1]:.2f}")
            else:
                print("⚠️ qstock数据连接测试失败")
        except Exception as e:
            print(f"⚠️ qstock连接测试异常: {e}")
            # 尝试不带参数的调用
            try:
                test_data = qs.get_data('000001')
                if test_data is not None and not test_data.empty:
                    print("✅ qstock基础数据连接成功")
                    print(f"   数据条数: {len(test_data)}")
                else:
                    print("⚠️ qstock基础数据获取失败")
            except Exception as e2:
                print(f"⚠️ qstock基础连接也失败: {e2}")
    
    def init_trading_module(self):
        """初始化EasyXT交易执行模块"""
        print("\n💼 初始化EasyXT交易执行模块...")
        
        if not EASYXT_AVAILABLE:
            print("❌ EasyXT不可用，交易功能受限")
            return
        
        try:
            # 创建EasyXT实例
            self.trader = EasyXT()
            print("✅ EasyXT实例创建成功")
            
            # 初始化数据服务
            if self.trader.init_data():
                print("✅ EasyXT数据服务初始化成功")
            else:
                print("⚠️ EasyXT数据服务初始化失败")
            
            # 初始化交易服务
            if self.trader.init_trade(
                TRADING_CONFIG['userdata_path'], 
                TRADING_CONFIG['session_id']
            ):
                print("✅ EasyXT交易服务初始化成功")
                
                # 添加交易账户
                if self.trader.add_account(TRADING_CONFIG['account_id'], 'STOCK'):
                    print("✅ 交易账户添加成功")
                    self.is_trading_enabled = True
                else:
                    print("⚠️ 交易账户添加失败")
            else:
                print("⚠️ EasyXT交易服务初始化失败")
                print("💡 请检查:")
                print("   1. 迅投客户端是否已启动并登录")
                print("   2. userdata路径是否正确")
                print("   3. 账户ID是否正确")
                
        except Exception as e:
            print(f"❌ EasyXT初始化异常: {e}")
    
    # ==================== qstock数据获取增强功能 ====================
    
    def get_multi_source_data(self, symbol: str, period: int = 60) -> Dict[str, pd.DataFrame]:
        """
        使用qstock获取多源数据
        
        Args:
            symbol: 股票代码
            period: 数据周期(天)
            
        Returns:
            包含多种数据的字典
        """
        print(f"\n📊 使用qstock获取 {symbol} 的多源数据...")
        
        data_dict = {}
        
        if not QSTOCK_AVAILABLE:
            print("❌ qstock不可用")
            return data_dict
        
        try:
            # 1. 基础K线数据 - 修复qstock API调用
            print("  📈 获取K线数据...")
            try:
                # 方法1: 使用日期范围获取数据
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=period)).strftime('%Y-%m-%d')
                kline_data = qs.get_data(symbol, start=start_date, end=end_date)
            except:
                try:
                    # 方法2: 使用默认参数获取数据
                    kline_data = qs.get_data(symbol)
                    if kline_data is not None and not kline_data.empty and len(kline_data) > period:
                        kline_data = kline_data.tail(period)  # 取最近的数据
                except:
                    kline_data = None
            
            if kline_data is not None and not kline_data.empty:
                data_dict['kline'] = self.clean_kline_data(kline_data)
                print(f"    ✅ K线数据: {len(data_dict['kline'])} 条")
            
            # 2. 实时行情数据
            print("  📊 获取实时行情...")
            try:
                # 尝试不同的实时数据获取方法
                if hasattr(qs, 'get_realtime'):
                    realtime_data = qs.get_realtime([symbol])
                elif hasattr(qs, 'realtime'):
                    realtime_data = qs.realtime([symbol])
                else:
                    realtime_data = None
                    
                if realtime_data is not None and not realtime_data.empty:
                    data_dict['realtime'] = realtime_data
                    print(f"    ✅ 实时行情: {len(realtime_data)} 条")
                else:
                    print("    ⚠️ 实时行情数据为空")
            except Exception as e:
                print(f"    ⚠️ 实时行情获取失败: {e}")
            
            # 3. 资金流向数据
            print("  💰 获取资金流向...")
            try:
                if hasattr(qs, 'get_fund_flow'):
                    fund_flow = qs.get_fund_flow([symbol])
                elif hasattr(qs, 'fund_flow'):
                    fund_flow = qs.fund_flow([symbol])
                else:
                    fund_flow = None
                    
                if fund_flow is not None and not fund_flow.empty:
                    data_dict['fund_flow'] = fund_flow
                    print(f"    ✅ 资金流向: {len(fund_flow)} 条")
                else:
                    print("    ⚠️ 资金流向数据为空")
            except Exception as e:
                print(f"    ⚠️ 资金流向获取失败: {e}")
            
            # 4. 财务数据
            print("  📋 获取财务数据...")
            try:
                if hasattr(qs, 'get_financial_data'):
                    financial_data = qs.get_financial_data(symbol)
                elif hasattr(qs, 'financial'):
                    financial_data = qs.financial(symbol)
                else:
                    financial_data = None
                    
                if financial_data is not None and not financial_data.empty:
                    data_dict['financial'] = financial_data
                    print(f"    ✅ 财务数据: {len(financial_data)} 条")
                else:
                    print("    ⚠️ 财务数据为空")
            except Exception as e:
                print(f"    ⚠️ 财务数据获取失败: {e}")
            
            # 5. 新闻舆情数据
            print("  📰 获取新闻数据...")
            try:
                if hasattr(qs, 'get_news'):
                    news_data = qs.get_news(symbol)
                elif hasattr(qs, 'news'):
                    news_data = qs.news(symbol)
                else:
                    news_data = None
                    
                if news_data is not None and not news_data.empty:
                    data_dict['news'] = news_data
                    print(f"    ✅ 新闻数据: {len(news_data)} 条")
                else:
                    print("    ⚠️ 新闻数据为空")
            except Exception as e:
                print(f"    ⚠️ 新闻数据获取失败: {e}")
            
            # 缓存数据
            self.data_cache[symbol] = {
                'data': data_dict,
                'timestamp': datetime.now(),
                'symbol': symbol
            }
            
            print(f"✅ {symbol} 多源数据获取完成，共 {len(data_dict)} 种数据类型")
            
        except Exception as e:
            print(f"❌ 多源数据获取失败: {e}")
        
        return data_dict
    
    def clean_kline_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """清洗K线数据"""
        if data is None or data.empty:
            return pd.DataFrame()
        
        # 标准化列名
        column_mapping = {
            'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume',
            'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume'
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in data.columns:
                data = data.rename(columns={old_col: new_col})
        
        # 确保必要列存在
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in data.columns]
        
        if missing_cols:
            print(f"⚠️ 缺少必要列: {missing_cols}")
            return pd.DataFrame()
        
        # 数据清洗
        data = data.dropna()
        data = data[data['volume'] > 0]
        
        # 数据类型转换
        for col in required_cols:
            data[col] = pd.to_numeric(data[col], errors='coerce')
        
        data = data.dropna()
        
        return data
    
    def get_market_overview(self) -> Dict[str, Any]:
        """获取市场概览数据"""
        print("\n🌍 获取市场概览数据...")
        
        market_data = {}
        
        if not QSTOCK_AVAILABLE:
            return market_data
        
        try:
            # 1. 市场指数
            print("  📊 获取主要指数...")
            indices = ['000001', '399001', '399006']  # 上证、深证、创业板
            index_data = {}
            
            for index in indices:
                try:
                    # 尝试获取指数数据
                    if hasattr(qs, 'get_realtime'):
                        data = qs.get_realtime([index])
                    elif hasattr(qs, 'realtime'):
                        data = qs.realtime([index])
                    else:
                        # 使用基础数据获取
                        data = qs.get_data(index)
                        if data is not None and not data.empty:
                            # 转换为实时格式
                            latest = data.iloc[-1]
                            data = pd.DataFrame([{
                                'code': index,
                                'price': latest['close'],
                                'change': latest['close'] - latest['open'],
                                'change_pct': (latest['close'] - latest['open']) / latest['open'] * 100
                            }])
                    
                    if data is not None and not data.empty:
                        index_data[index] = data.iloc[0].to_dict()
                except Exception as e:
                    print(f"    ⚠️ {index} 数据获取失败: {e}")
                    continue
            
            market_data['indices'] = index_data
            print(f"    ✅ 指数数据: {len(index_data)} 个")
            
            # 2. 涨跌停统计
            print("  📈 获取涨跌停统计...")
            try:
                limit_stats = {'limit_up_count': 0, 'limit_down_count': 0}
                
                if hasattr(qs, 'get_limit_up'):
                    limit_up = qs.get_limit_up()
                    if limit_up is not None and not limit_up.empty:
                        limit_stats['limit_up_count'] = len(limit_up)
                
                if hasattr(qs, 'get_limit_down'):
                    limit_down = qs.get_limit_down()
                    if limit_down is not None and not limit_down.empty:
                        limit_stats['limit_down_count'] = len(limit_down)
                
                market_data['limit_stats'] = limit_stats
                print(f"    ✅ 涨停: {limit_stats['limit_up_count']} 只")
                print(f"    ✅ 跌停: {limit_stats['limit_down_count']} 只")
            except Exception as e:
                print(f"    ⚠️ 涨跌停统计获取失败: {e}")
            
            # 3. 热门概念
            print("  🔥 获取热门概念...")
            try:
                hot_concepts = None
                if hasattr(qs, 'get_hot_concept'):
                    hot_concepts = qs.get_hot_concept()
                elif hasattr(qs, 'hot_concept'):
                    hot_concepts = qs.hot_concept()
                
                if hot_concepts is not None and not hot_concepts.empty:
                    market_data['hot_concepts'] = hot_concepts.head(10)
                    print(f"    ✅ 热门概念: {len(market_data['hot_concepts'])} 个")
                else:
                    print("    ⚠️ 热门概念数据为空")
            except Exception as e:
                print(f"    ⚠️ 热门概念获取失败: {e}")
            
            # 4. 资金流向
            print("  💰 获取市场资金流向...")
            try:
                market_fund_flow = None
                if hasattr(qs, 'get_market_fund_flow'):
                    market_fund_flow = qs.get_market_fund_flow()
                elif hasattr(qs, 'market_fund_flow'):
                    market_fund_flow = qs.market_fund_flow()
                
                if market_fund_flow is not None:
                    market_data['market_fund_flow'] = market_fund_flow
                    print("    ✅ 市场资金流向获取成功")
                else:
                    print("    ⚠️ 市场资金流向数据为空")
            except Exception as e:
                print(f"    ⚠️ 市场资金流向获取失败: {e}")
            
        except Exception as e:
            print(f"❌ 市场概览获取失败: {e}")
        
        return market_data
    
    # ==================== 智能策略引擎 ====================
    
    def calculate_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        if data is None or data.empty:
            return data
        
        print("📈 计算技术指标...")
        
        try:
            # 基础移动平均线
            data['MA5'] = data['close'].rolling(window=5).mean()
            data['MA10'] = data['close'].rolling(window=10).mean()
            data['MA20'] = data['close'].rolling(window=20).mean()
            data['MA60'] = data['close'].rolling(window=60).mean()
            
            # EMA指数移动平均
            data['EMA12'] = data['close'].ewm(span=12).mean()
            data['EMA26'] = data['close'].ewm(span=26).mean()
            
            # MACD
            data['MACD'] = data['EMA12'] - data['EMA26']
            data['MACD_signal'] = data['MACD'].ewm(span=9).mean()
            data['MACD_hist'] = data['MACD'] - data['MACD_signal']
            
            # RSI
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            data['RSI'] = 100 - (100 / (1 + rs))
            
            # 布林带
            data['BB_middle'] = data['close'].rolling(window=20).mean()
            bb_std = data['close'].rolling(window=20).std()
            data['BB_upper'] = data['BB_middle'] + (bb_std * 2)
            data['BB_lower'] = data['BB_middle'] - (bb_std * 2)
            data['BB_width'] = (data['BB_upper'] - data['BB_lower']) / data['BB_middle']
            
            # KDJ
            low_min = data['low'].rolling(window=9).min()
            high_max = data['high'].rolling(window=9).max()
            rsv = (data['close'] - low_min) / (high_max - low_min) * 100
            data['K'] = rsv.ewm(com=2).mean()
            data['D'] = data['K'].ewm(com=2).mean()
            data['J'] = 3 * data['K'] - 2 * data['D']
            
            # 成交量指标
            data['volume_ma5'] = data['volume'].rolling(window=5).mean()
            data['volume_ma20'] = data['volume'].rolling(window=20).mean()
            data['volume_ratio'] = data['volume'] / data['volume_ma20']
            
            # 价格强度
            data['price_strength'] = (data['close'] - data['low']) / (data['high'] - data['low'])
            
            # 波动率
            data['volatility'] = data['close'].rolling(window=20).std() / data['close'].rolling(window=20).mean()
            
            # 如果有TA-Lib，使用更多指标
            if TALIB_AVAILABLE:
                try:
                    import talib
                    # ADX
                    data['ADX'] = talib.ADX(data['high'].values, data['low'].values, data['close'].values, timeperiod=14)
                    # CCI
                    data['CCI'] = talib.CCI(data['high'].values, data['low'].values, data['close'].values, timeperiod=14)
                    # Williams %R
                    data['WILLR'] = talib.WILLR(data['high'].values, data['low'].values, data['close'].values, timeperiod=14)
                    print("  ✅ TA-Lib高级指标计算完成")
                except:
                    print("  ⚠️ TA-Lib指标计算失败")
            
            print(f"✅ 技术指标计算完成，共 {len([col for col in data.columns if col not in ['open', 'high', 'low', 'close', 'volume']])} 个指标")
            
        except Exception as e:
            print(f"❌ 技术指标计算失败: {e}")
        
        return data
    
    def generate_trading_signals(self, symbol: str, data: pd.DataFrame) -> List[Dict]:
        """生成交易信号"""
        print(f"\n🎯 为 {symbol} 生成交易信号...")
        
        if data is None or data.empty:
            return []
        
        signals = []
        
        try:
            # 确保有足够的数据
            if len(data) < 30:
                print("⚠️ 数据不足，无法生成可靠信号")
                return signals
            
            latest_data = data.iloc[-1]
            prev_data = data.iloc[-2]
            
            signal_strength = 0
            signal_reasons = []
            
            # 策略1: 趋势跟踪策略
            trend_signals = self._trend_following_strategy(data)
            signal_strength += trend_signals['strength']
            signal_reasons.extend(trend_signals['reasons'])
            
            # 策略2: 均值回归策略
            mean_reversion_signals = self._mean_reversion_strategy(data)
            signal_strength += mean_reversion_signals['strength']
            signal_reasons.extend(mean_reversion_signals['reasons'])
            
            # 策略3: 动量策略
            momentum_signals = self._momentum_strategy(data)
            signal_strength += momentum_signals['strength']
            signal_reasons.extend(momentum_signals['reasons'])
            
            # 策略4: 成交量确认策略
            volume_signals = self._volume_confirmation_strategy(data)
            signal_strength += volume_signals['strength']
            signal_reasons.extend(volume_signals['reasons'])
            
            # 策略5: 技术形态识别
            pattern_signals = self._pattern_recognition_strategy(data)
            signal_strength += pattern_signals['strength']
            signal_reasons.extend(pattern_signals['reasons'])
            
            # 综合信号评估
            confidence = min(95, max(0, 50 + signal_strength * 10))
            
            if abs(signal_strength) >= 0.5:  # 信号强度阈值
                signal_type = 'BUY' if signal_strength > 0 else 'SELL'
                
                signal = {
                    'symbol': symbol,
                    'timestamp': datetime.now(),
                    'signal_type': signal_type,
                    'strength': signal_strength,
                    'confidence': confidence,
                    'price': latest_data['close'],
                    'reasons': signal_reasons,
                    'technical_data': {
                        'MA5': latest_data.get('MA5', 0),
                        'MA20': latest_data.get('MA20', 0),
                        'RSI': latest_data.get('RSI', 50),
                        'MACD': latest_data.get('MACD', 0),
                        'volume_ratio': latest_data.get('volume_ratio', 1),
                    }
                }
                
                signals.append(signal)
                print(f"✅ 生成{signal_type}信号，强度: {signal_strength:.2f}, 置信度: {confidence:.1f}%")
                print(f"   信号原因: {', '.join(signal_reasons[:3])}")
            else:
                print("💡 当前无明确交易信号")
            
        except Exception as e:
            print(f"❌ 信号生成失败: {e}")
        
        return signals
    
    def _trend_following_strategy(self, data: pd.DataFrame) -> Dict:
        """趋势跟踪策略"""
        strength = 0
        reasons = []
        
        try:
            latest = data.iloc[-1]
            
            # MA趋势判断
            if latest['close'] > latest['MA5'] > latest['MA20']:
                strength += 0.3
                reasons.append("多头排列")
            elif latest['close'] < latest['MA5'] < latest['MA20']:
                strength -= 0.3
                reasons.append("空头排列")
            
            # MA金叉死叉
            if len(data) >= 2:
                prev = data.iloc[-2]
                if latest['MA5'] > latest['MA20'] and prev['MA5'] <= prev['MA20']:
                    strength += 0.4
                    reasons.append("MA金叉")
                elif latest['MA5'] < latest['MA20'] and prev['MA5'] >= prev['MA20']:
                    strength -= 0.4
                    reasons.append("MA死叉")
            
            # MACD趋势
            if latest['MACD'] > latest['MACD_signal'] and latest['MACD'] > 0:
                strength += 0.2
                reasons.append("MACD多头")
            elif latest['MACD'] < latest['MACD_signal'] and latest['MACD'] < 0:
                strength -= 0.2
                reasons.append("MACD空头")
                
        except Exception as e:
            print(f"⚠️ 趋势策略计算异常: {e}")
        
        return {'strength': strength, 'reasons': reasons}
    
    def _mean_reversion_strategy(self, data: pd.DataFrame) -> Dict:
        """均值回归策略"""
        strength = 0
        reasons = []
        
        try:
            latest = data.iloc[-1]
            
            # RSI超买超卖
            if latest['RSI'] < 30:
                strength += 0.3
                reasons.append("RSI超卖")
            elif latest['RSI'] > 70:
                strength -= 0.3
                reasons.append("RSI超买")
            
            # 布林带位置
            if latest['close'] < latest['BB_lower']:
                strength += 0.2
                reasons.append("跌破布林下轨")
            elif latest['close'] > latest['BB_upper']:
                strength -= 0.2
                reasons.append("突破布林上轨")
            
            # KDJ超买超卖
            if latest['K'] < 20 and latest['D'] < 20:
                strength += 0.2
                reasons.append("KDJ超卖")
            elif latest['K'] > 80 and latest['D'] > 80:
                strength -= 0.2
                reasons.append("KDJ超买")
                
        except Exception as e:
            print(f"⚠️ 均值回归策略计算异常: {e}")
        
        return {'strength': strength, 'reasons': reasons}
    
    def _momentum_strategy(self, data: pd.DataFrame) -> Dict:
        """动量策略"""
        strength = 0
        reasons = []
        
        try:
            if len(data) < 5:
                return {'strength': 0, 'reasons': []}
            
            latest = data.iloc[-1]
            
            # 价格动量
            price_change_5d = (latest['close'] - data.iloc[-5]['close']) / data.iloc[-5]['close']
            if price_change_5d > 0.05:
                strength += 0.2
                reasons.append("5日强势上涨")
            elif price_change_5d < -0.05:
                strength -= 0.2
                reasons.append("5日持续下跌")
            
            # 成交量动量
            if latest['volume_ratio'] > 2:
                strength += 0.1
                reasons.append("成交量放大")
            elif latest['volume_ratio'] < 0.5:
                strength -= 0.1
                reasons.append("成交量萎缩")
            
            # 价格强度
            if latest['price_strength'] > 0.8:
                strength += 0.1
                reasons.append("价格强势")
            elif latest['price_strength'] < 0.2:
                strength -= 0.1
                reasons.append("价格弱势")
                
        except Exception as e:
            print(f"⚠️ 动量策略计算异常: {e}")
        
        return {'strength': strength, 'reasons': reasons}
    
    def _volume_confirmation_strategy(self, data: pd.DataFrame) -> Dict:
        """成交量确认策略"""
        strength = 0
        reasons = []
        
        try:
            latest = data.iloc[-1]
            
            # 量价配合
            price_change = (latest['close'] - data.iloc[-2]['close']) / data.iloc[-2]['close']
            volume_change = (latest['volume'] - data.iloc[-2]['volume']) / data.iloc[-2]['volume']
            
            if price_change > 0.02 and volume_change > 0.5:
                strength += 0.2
                reasons.append("量价齐升")
            elif price_change < -0.02 and volume_change > 0.5:
                strength -= 0.2
                reasons.append("量价背离")
            
            # 成交量突破
            if latest['volume'] > latest['volume_ma20'] * 2:
                strength += 0.1
                reasons.append("成交量突破")
                
        except Exception as e:
            print(f"⚠️ 成交量策略计算异常: {e}")
        
        return {'strength': strength, 'reasons': reasons}
    
    def _pattern_recognition_strategy(self, data: pd.DataFrame) -> Dict:
        """技术形态识别策略"""
        strength = 0
        reasons = []
        
        try:
            if len(data) < 10:
                return {'strength': 0, 'reasons': []}
            
            # 简单形态识别
            recent_data = data.tail(10)
            
            # 连续上涨/下跌
            consecutive_up = 0
            consecutive_down = 0
            
            for i in range(1, len(recent_data)):
                if recent_data.iloc[i]['close'] > recent_data.iloc[i-1]['close']:
                    consecutive_up += 1
                    consecutive_down = 0
                elif recent_data.iloc[i]['close'] < recent_data.iloc[i-1]['close']:
                    consecutive_down += 1
                    consecutive_up = 0
                else:
                    consecutive_up = 0
                    consecutive_down = 0
            
            if consecutive_up >= 3:
                strength += 0.1
                reasons.append(f"连续{consecutive_up}日上涨")
            elif consecutive_down >= 3:
                strength -= 0.1
                reasons.append(f"连续{consecutive_down}日下跌")
            
            # 突破形态
            latest = data.iloc[-1]
            high_20 = data.tail(20)['high'].max()
            low_20 = data.tail(20)['low'].min()
            
            if latest['close'] > high_20 * 0.99:
                strength += 0.15
                reasons.append("突破20日新高")
            elif latest['close'] < low_20 * 1.01:
                strength -= 0.15
                reasons.append("跌破20日新低")
                
        except Exception as e:
            print(f"⚠️ 形态识别策略计算异常: {e}")
        
        return {'strength': strength, 'reasons': reasons}
    
    # ==================== EasyXT交易执行增强功能 ====================
    
    def execute_trading_signal(self, signal: Dict) -> Dict:
        """执行交易信号"""
        print(f"\n💼 执行交易信号: {signal['symbol']} {signal['signal_type']}")
        
        if not self.is_trading_enabled:
            print("⚠️ 交易功能未启用，仅记录信号")
            return {'status': 'disabled', 'message': '交易功能未启用'}
        
        try:
            # 获取账户信息
            account_info = self.get_account_info()
            if not account_info:
                return {'status': 'error', 'message': '无法获取账户信息'}
            
            # 获取持仓信息
            position_info = self.get_position_info(signal['symbol'])
            
            # 风险检查
            risk_check = self.risk_management_check(signal, account_info, position_info)
            if not risk_check['passed']:
                return {'status': 'rejected', 'message': risk_check['reason']}
            
            # 计算交易数量
            quantity = self.calculate_trade_quantity(signal, account_info, position_info)
            if quantity <= 0:
                return {'status': 'error', 'message': '交易数量计算错误'}
            
            # 执行交易
            if signal['signal_type'] == 'BUY':
                result = self.execute_buy_order(signal['symbol'], quantity, signal['price'])
            else:
                result = self.execute_sell_order(signal['symbol'], quantity, signal['price'])
            
            # 记录交易
            trade_record = {
                'timestamp': datetime.now(),
                'symbol': signal['symbol'],
                'signal_type': signal['signal_type'],
                'quantity': quantity,
                'price': signal['price'],
                'confidence': signal['confidence'],
                'result': result
            }
            self.trade_history.append(trade_record)
            
            return result
            
        except Exception as e:
            print(f"❌ 交易执行失败: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_account_info(self) -> Dict:
        """获取账户信息"""
        try:
            if self.is_trading_enabled and hasattr(self, 'trader'):
                account_info = self.trader.get_account_asset(TRADING_CONFIG['account_id'])
                if account_info:
                    print(f"✅ 账户总资产: {account_info.get('total_asset', 0):.2f}")
                    print(f"   可用资金: {account_info.get('cash', 0):.2f}")
                    return account_info
            
            # 模拟账户信息
            return {
                'total_asset': 100000,
                'cash': 50000,
                'market_value': 50000,
                'profit_loss': 0
            }
            
        except Exception as e:
            print(f"⚠️ 获取账户信息失败: {e}")
            return {}
    
    def get_position_info(self, symbol: str) -> Dict:
        """获取持仓信息"""
        try:
            if self.is_trading_enabled and hasattr(self, 'trader'):
                positions = self.trader.get_positions(TRADING_CONFIG['account_id'], symbol)
                if not positions.empty:
                    position = positions.iloc[0]
                    return {
                        'volume': position.get('volume', 0),
                        'can_use_volume': position.get('can_use_volume', 0),
                        'cost_price': position.get('cost_price', 0),
                        'market_value': position.get('market_value', 0)
                    }
            
            return {'volume': 0, 'can_use_volume': 0, 'cost_price': 0, 'market_value': 0}
            
        except Exception as e:
            print(f"⚠️ 获取持仓信息失败: {e}")
            return {'volume': 0, 'can_use_volume': 0, 'cost_price': 0, 'market_value': 0}
    
    def risk_management_check(self, signal: Dict, account_info: Dict, position_info: Dict) -> Dict:
        """风险管理检查"""
        try:
            # 检查1: 最大仓位限制
            total_asset = account_info.get('total_asset', 100000)
            current_position_value = position_info.get('market_value', 0)
            max_position_value = total_asset * TRADING_CONFIG['max_position_ratio']
            
            if signal['signal_type'] == 'BUY':
                trade_value = signal['price'] * 100  # 最小交易单位
                if current_position_value + trade_value > max_position_value:
                    return {'passed': False, 'reason': '超过最大仓位限制'}
            
            # 检查2: 单股仓位限制
            single_stock_max = total_asset * TRADING_CONFIG['single_stock_ratio']
            if signal['signal_type'] == 'BUY' and current_position_value > single_stock_max:
                return {'passed': False, 'reason': '超过单股最大仓位'}
            
            # 检查3: 止损检查
            if position_info.get('volume', 0) > 0:
                cost_price = position_info.get('cost_price', 0)
                current_price = signal['price']
                loss_ratio = (cost_price - current_price) / cost_price
                
                if loss_ratio > TRADING_CONFIG['stop_loss_ratio']:
                    if signal['signal_type'] == 'BUY':
                        return {'passed': False, 'reason': '触发止损，不宜加仓'}
            
            # 检查4: 信号置信度
            if signal['confidence'] < STRATEGY_CONFIG['signal_threshold']:
                return {'passed': False, 'reason': '信号置信度不足'}
            
            return {'passed': True, 'reason': '风险检查通过'}
            
        except Exception as e:
            return {'passed': False, 'reason': f'风险检查异常: {e}'}
    
    def calculate_trade_quantity(self, signal: Dict, account_info: Dict, position_info: Dict) -> int:
        """计算交易数量"""
        try:
            if signal['signal_type'] == 'BUY':
                # 买入数量计算
                available_cash = account_info.get('cash', 0)
                trade_amount = available_cash * 0.3  # 使用30%资金
                
                # 考虑手续费
                price_with_fee = signal['price'] * 1.001
                quantity = int(trade_amount / price_with_fee) // 100 * 100
                
                return max(100, quantity)  # 最少1手
                
            else:
                # 卖出数量计算
                can_sell = position_info.get('can_use_volume', 0)
                if can_sell > 0:
                    # 根据信号强度决定卖出比例
                    sell_ratio = min(0.5, abs(signal['strength']))
                    quantity = int(can_sell * sell_ratio) // 100 * 100
                    return max(100, min(quantity, can_sell))
                
                return 0
                
        except Exception as e:
            print(f"⚠️ 交易数量计算失败: {e}")
            return 0
    
    def execute_buy_order(self, symbol: str, quantity: int, price: float) -> Dict:
        """执行买入订单"""
        try:
            print(f"📈 执行买入: {symbol}, 数量: {quantity}, 价格: {price:.2f}")
            
            if hasattr(self, 'trader'):
                order_id = self.trader.buy(
                    account_id=TRADING_CONFIG['account_id'],
                    code=symbol,
                    volume=quantity,
                    price=price,
                    price_type='limit'
                )
                
                if order_id:
                    print(f"✅ 买入订单提交成功，订单号: {order_id}")
                    return {'status': 'success', 'order_id': order_id, 'message': '买入订单提交成功'}
                else:
                    return {'status': 'failed', 'message': '买入订单提交失败'}
            else:
                print("⚠️ 模拟买入执行")
                return {'status': 'simulated', 'message': '模拟买入执行'}
                
        except Exception as e:
            print(f"❌ 买入订单执行异常: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def execute_sell_order(self, symbol: str, quantity: int, price: float) -> Dict:
        """执行卖出订单"""
        try:
            print(f"📉 执行卖出: {symbol}, 数量: {quantity}, 价格: {price:.2f}")
            
            if hasattr(self, 'trader'):
                order_id = self.trader.sell(
                    account_id=TRADING_CONFIG['account_id'],
                    code=symbol,
                    volume=quantity,
                    price=price,
                    price_type='limit'
                )
                
                if order_id:
                    print(f"✅ 卖出订单提交成功，订单号: {order_id}")
                    return {'status': 'success', 'order_id': order_id, 'message': '卖出订单提交成功'}
                else:
                    return {'status': 'failed', 'message': '卖出订单提交失败'}
            else:
                print("⚠️ 模拟卖出执行")
                return {'status': 'simulated', 'message': '模拟卖出执行'}
                
        except Exception as e:
            print(f"❌ 卖出订单执行异常: {e}")
            return {'status': 'error', 'message': str(e)}
    
    # ==================== 实时监控面板 ====================
    
    def start_real_time_monitoring(self):
        """启动实时监控"""
        print("\n🔄 启动实时监控系统...")
        
        self.is_monitoring = True
        
        # 创建监控线程
        monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        monitor_thread.start()
        
        print("✅ 实时监控系统已启动")
        print("💡 按 Ctrl+C 停止监控")
        
        try:
            while self.is_monitoring:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 停止监控系统...")
            self.is_monitoring = False
    
    def _monitoring_loop(self):
        """监控主循环"""
        while self.is_monitoring:
            try:
                print(f"\n{'='*60}")
                print(f"🔄 实时监控更新 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*60}")
                
                # 监控股票池
                all_signals = []
                
                for category, stocks in STOCK_POOL.items():
                    print(f"\n📊 监控 {category}...")
                    
                    for stock in stocks[:2]:  # 限制监控数量
                        try:
                            # 获取数据
                            data_dict = self.get_multi_source_data(stock, period=30)
                            
                            if 'kline' in data_dict and not data_dict['kline'].empty:
                                # 计算技术指标
                                kline_data = self.calculate_technical_indicators(data_dict['kline'])
                                
                                # 生成信号
                                signals = self.generate_trading_signals(stock, kline_data)
                                all_signals.extend(signals)
                                
                                # 显示关键信息
                                latest = kline_data.iloc[-1]
                                print(f"  {stock}: 价格 {latest['close']:.2f}, RSI {latest.get('RSI', 50):.1f}")
                            else:
                                print(f"  ⚠️ {stock}: 无K线数据")
                                
                        except Exception as e:
                            print(f"  ⚠️ {stock} 监控异常: {e}")
                
                # 处理信号
                if all_signals:
                    print(f"\n🎯 发现 {len(all_signals)} 个交易信号")
                    
                    for signal in all_signals:
                        if signal['confidence'] >= STRATEGY_CONFIG['signal_threshold']:
                            print(f"  🔥 高质量信号: {signal['symbol']} {signal['signal_type']} (置信度: {signal['confidence']:.1f}%)")
                            
                            # 可以选择自动执行或手动确认
                            # result = self.execute_trading_signal(signal)
                else:
                    print("💡 当前无交易信号")
                
                # 显示账户状态
                self._display_account_status()
                
                # 等待下次更新
                time.sleep(STRATEGY_CONFIG['update_interval'])
                
            except Exception as e:
                print(f"❌ 监控循环异常: {e}")
                time.sleep(10)
    
    def _display_account_status(self):
        """显示账户状态"""
        try:
            account_info = self.get_account_info()
            
            print(f"\n💼 账户状态:")
            print(f"  总资产: {account_info.get('total_asset', 0):,.2f}")
            print(f"  可用资金: {account_info.get('cash', 0):,.2f}")
            print(f"  持仓市值: {account_info.get('market_value', 0):,.2f}")
            print(f"  浮动盈亏: {account_info.get('profit_loss', 0):,.2f}")
            
            if self.trade_history:
                print(f"  今日交易: {len(self.trade_history)} 笔")
                
        except Exception as e:
            print(f"⚠️ 账户状态显示异常: {e}")
    
    # ==================== 策略回测系统 ====================
    
    def run_backtest(self, symbol: str, start_date: str, end_date: str) -> Dict:
        """运行策略回测"""
        print(f"\n📈 开始回测 {symbol} ({start_date} 至 {end_date})")
        
        try:
            # 获取历史数据
            print("📊 获取历史数据...")
            if QSTOCK_AVAILABLE:
                try:
                    historical_data = qs.get_data(symbol, start=start_date, end=end_date)
                except:
                    try:
                        # 如果带参数失败，尝试不带参数
                        historical_data = qs.get_data(symbol)
                        if historical_data is not None and not historical_data.empty:
                            # 手动筛选日期范围
                            historical_data.index = pd.to_datetime(historical_data.index)
                            start_dt = pd.to_datetime(start_date)
                            end_dt = pd.to_datetime(end_date)
                            historical_data = historical_data[(historical_data.index >= start_dt) & (historical_data.index <= end_dt)]
                    except:
                        historical_data = None
            else:
                print("❌ qstock不可用，无法进行回测")
                return {}
            
            if historical_data is None or historical_data.empty:
                print("❌ 无法获取历史数据")
                return {}
            
            # 清洗数据
            historical_data = self.clean_kline_data(historical_data)
            print(f"✅ 获取历史数据 {len(historical_data)} 条")
            
            # 计算技术指标
            historical_data = self.calculate_technical_indicators(historical_data)
            
            # 模拟交易
            backtest_results = self._simulate_trading(symbol, historical_data)
            
            # 计算绩效指标
            performance_metrics = self._calculate_performance_metrics(backtest_results)
            
            # 生成报告
            self._generate_backtest_report(symbol, backtest_results, performance_metrics)
            
            return {
                'symbol': symbol,
                'period': f"{start_date} 至 {end_date}",
                'trades': backtest_results,
                'performance': performance_metrics
            }
            
        except Exception as e:
            print(f"❌ 回测失败: {e}")
            return {}
    
    def _simulate_trading(self, symbol: str, data: pd.DataFrame) -> List[Dict]:
        """模拟交易过程"""
        print("🔄 模拟交易过程...")
        
        trades = []
        position = 0
        cash = 100000
        
        for i in range(30, len(data)):  # 从第30天开始，确保有足够数据计算指标
            current_data = data.iloc[:i+1]
            
            # 生成信号
            signals = self.generate_trading_signals(symbol, current_data)
            
            if signals:
                signal = signals[0]
                current_price = signal['price']
                
                if signal['signal_type'] == 'BUY' and position == 0 and cash > current_price * 100:
                    # 买入
                    quantity = int(cash * 0.3 / current_price) // 100 * 100
                    if quantity > 0:
                        position = quantity
                        cash -= quantity * current_price
                        
                        trades.append({
                            'date': data.index[i],
                            'action': 'BUY',
                            'price': current_price,
                            'quantity': quantity,
                            'cash': cash,
                            'position_value': position * current_price,
                            'total_value': cash + position * current_price,
                            'signal_confidence': signal['confidence']
                        })
                
                elif signal['signal_type'] == 'SELL' and position > 0:
                    # 卖出
                    cash += position * current_price
                    
                    trades.append({
                        'date': data.index[i],
                        'action': 'SELL',
                        'price': current_price,
                        'quantity': position,
                        'cash': cash,
                        'position_value': 0,
                        'total_value': cash,
                        'signal_confidence': signal['confidence']
                    })
                    
                    position = 0
        
        print(f"✅ 模拟交易完成，共 {len(trades)} 笔交易")
        return trades
    
    def _calculate_performance_metrics(self, trades: List[Dict]) -> Dict:
        """计算绩效指标"""
        if not trades:
            return {}
        
        # 基础统计
        total_trades = len(trades)
        buy_trades = [t for t in trades if t['action'] == 'BUY']
        sell_trades = [t for t in trades if t['action'] == 'SELL']
        
        # 收益计算
        initial_value = 100000
        final_value = trades[-1]['total_value']
        total_return = (final_value - initial_value) / initial_value
        
        # 交易对分析
        trade_pairs = []
        for i in range(min(len(buy_trades), len(sell_trades))):
            buy_trade = buy_trades[i]
            sell_trade = sell_trades[i]
            
            profit = (sell_trade['price'] - buy_trade['price']) * buy_trade['quantity']
            profit_rate = profit / (buy_trade['price'] * buy_trade['quantity'])
            
            trade_pairs.append({
                'buy_date': buy_trade['date'],
                'sell_date': sell_trade['date'],
                'buy_price': buy_trade['price'],
                'sell_price': sell_trade['price'],
                'quantity': buy_trade['quantity'],
                'profit': profit,
                'profit_rate': profit_rate
            })
        
        # 胜率计算
        winning_trades = [tp for tp in trade_pairs if tp['profit'] > 0]
        win_rate = len(winning_trades) / len(trade_pairs) if trade_pairs else 0
        
        # 平均收益
        avg_profit = np.mean([tp['profit'] for tp in trade_pairs]) if trade_pairs else 0
        avg_profit_rate = np.mean([tp['profit_rate'] for tp in trade_pairs]) if trade_pairs else 0
        
        return {
            'total_trades': total_trades,
            'trade_pairs': len(trade_pairs),
            'total_return': total_return,
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_profit_rate': avg_profit_rate,
            'final_value': final_value,
            'max_profit': max([tp['profit'] for tp in trade_pairs]) if trade_pairs else 0,
            'max_loss': min([tp['profit'] for tp in trade_pairs]) if trade_pairs else 0
        }
    
    def _generate_backtest_report(self, symbol: str, trades: List[Dict], metrics: Dict):
        """生成回测报告"""
        print(f"\n📊 {symbol} 回测报告")
        print("=" * 50)
        
        if not metrics:
            print("❌ 无交易数据，无法生成报告")
            return
        
        print(f"总交易次数: {metrics['total_trades']}")
        print(f"完整交易对: {metrics['trade_pairs']}")
        print(f"总收益率: {metrics['total_return']:.2%}")
        print(f"胜率: {metrics['win_rate']:.2%}")
        print(f"平均收益: {metrics['avg_profit']:.2f}")
        print(f"平均收益率: {metrics['avg_profit_rate']:.2%}")
        print(f"最大盈利: {metrics['max_profit']:.2f}")
        print(f"最大亏损: {metrics['max_loss']:.2f}")
        print(f"最终资产: {metrics['final_value']:.2f}")
        
        # 保存详细报告
        report_file = f"reports/backtest_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'symbol': symbol,
                'trades': trades,
                'metrics': metrics,
                'timestamp': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"📄 详细报告已保存: {report_file}")
    
    # ==================== 主要演示功能 ====================
    
    def run_comprehensive_demo(self):
        """运行综合演示"""
        print("\n🚀 qstock与EasyXT完美结合综合演示")
        print("=" * 60)
        
        try:
            # 1. 市场概览
            print("\n📊 第一步: 获取市场概览")
            market_overview = self.get_market_overview()
            
            # 2. 多源数据获取演示
            print("\n📈 第二步: 多源数据获取演示")
            demo_symbol = '000001'
            multi_data = self.get_multi_source_data(demo_symbol, period=60)
            
            if 'kline' in multi_data and not multi_data['kline'].empty:
                # 3. 技术指标计算
                print("\n📊 第三步: 技术指标计算")
                kline_with_indicators = self.calculate_technical_indicators(multi_data['kline'])
                
                # 4. 交易信号生成
                print("\n🎯 第四步: 交易信号生成")
                signals = self.generate_trading_signals(demo_symbol, kline_with_indicators)
                
                # 5. 风险管理演示
                if signals:
                    print("\n🛡️ 第五步: 风险管理检查")
                    account_info = self.get_account_info()
                    position_info = self.get_position_info(demo_symbol)
                    
                    for signal in signals:
                        risk_check = self.risk_management_check(signal, account_info, position_info)
                        print(f"  风险检查结果: {risk_check}")
                
                # 6. 策略回测演示
                print("\n📈 第六步: 策略回测演示")
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
                backtest_result = self.run_backtest(demo_symbol, start_date, end_date)
                
                # 7. 可视化展示
                print("\n📊 第七步: 数据可视化")
                self.create_visualization(demo_symbol, kline_with_indicators, signals)
                
            else:
                print("❌ 无法获取K线数据，跳过后续演示")
            
            # 8. 实时监控选项
            print("\n🔄 第八步: 实时监控选项")
            print("💡 如需启动实时监控，请调用 start_real_time_monitoring() 方法")
            
            print("\n✅ 综合演示完成！")
            print("🎉 qstock与EasyXT完美结合展示成功")
            
        except Exception as e:
            print(f"❌ 综合演示异常: {e}")
    
    def create_visualization(self, symbol: str, data: pd.DataFrame, signals: List[Dict]):
        """创建数据可视化"""
        try:
            print(f"📊 创建 {symbol} 数据可视化...")
            
            fig, axes = plt.subplots(3, 1, figsize=(15, 12))
            fig.suptitle(f'{symbol} qstock+EasyXT 量化分析', fontsize=16, fontweight='bold')
            
            # 子图1: 价格和移动平均线
            ax1 = axes[0]
            ax1.plot(data.index, data['close'], label='收盘价', linewidth=2)
            ax1.plot(data.index, data['MA5'], label='MA5', alpha=0.7)
            ax1.plot(data.index, data['MA20'], label='MA20', alpha=0.7)
            
            # 标记交易信号
            for signal in signals:
                if signal['signal_type'] == 'BUY':
                    ax1.scatter(data.index[-1], signal['price'], color='red', marker='^', s=100, label='买入信号')
                else:
                    ax1.scatter(data.index[-1], signal['price'], color='green', marker='v', s=100, label='卖出信号')
            
            ax1.set_title('价格走势与交易信号')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 子图2: 技术指标
            ax2 = axes[1]
            ax2.plot(data.index, data['RSI'], label='RSI', color='purple')
            ax2.axhline(y=70, color='r', linestyle='--', alpha=0.5, label='超买线')
            ax2.axhline(y=30, color='g', linestyle='--', alpha=0.5, label='超卖线')
            ax2.set_title('RSI指标')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            ax2.set_ylim(0, 100)
            
            # 子图3: MACD
            ax3 = axes[2]
            ax3.plot(data.index, data['MACD'], label='MACD', color='blue')
            ax3.plot(data.index, data['MACD_signal'], label='Signal', color='red')
            ax3.bar(data.index, data['MACD_hist'], label='Histogram', alpha=0.3)
            ax3.set_title('MACD指标')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # 保存图表
            chart_file = f"reports/{symbol}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            print(f"📊 图表已保存: {chart_file}")
            
            plt.show()
            
        except Exception as e:
            print(f"⚠️ 可视化创建失败: {e}")

def main():
    """主函数 - 演示qstock与EasyXT的完美结合"""
    print("🎯 欢迎使用 qstock与EasyXT完美结合量化交易系统")
    print("=" * 60)
    print("💡 本系统专为熟悉qstock但不了解EasyXT的用户设计")
    print("🚀 展示如何将qstock的数据获取能力与EasyXT的交易执行能力完美结合")
    print("=" * 60)
    
    # 创建系统实例
    system = QStockEasyXTIntegration()
    
    # 运行综合演示
    system.run_comprehensive_demo()
    
    print("\n" + "=" * 60)
    print("🎉 演示完成！")
    print("💡 您已经了解了qstock与EasyXT的完美结合方式")
    print("🚀 现在可以开始构建您自己的量化交易系统了！")
    print("=" * 60)
    
    # 可选: 启动实时监控
    while True:
        choice = input("\n是否启动实时监控系统? (y/n): ").lower().strip()
        if choice in ['y', 'yes', '是']:
            system.start_real_time_monitoring()
            break
        elif choice in ['n', 'no', '否']:
            print("👋 感谢使用，再见！")
            break
        else:
            print("请输入 y/n")

if __name__ == "__main__":
    main()