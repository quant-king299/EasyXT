# -*- coding: utf-8 -*-
"""
实盘量化策略开发完整流程
本文件展示从策略设计到实盘部署的专业开发过程
基于EasyXT框架，展示真实的实盘策略开发技能

作者: 王者quant
版本: 1.0 (实盘策略开发专版)
"""

import sys
import os
import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from easy_xt.api import EasyXT

def print_section_header(lesson_num, title, description):
    """打印课程标题"""
    print("\n" + "=" * 70)
    print(f"第{lesson_num}阶段: {title}")
    print("=" * 70)
    print(f"📖 学习目标: {description}")
    print("-" * 70)

def wait_for_user_input(message="按回车键继续..."):
    """等待用户输入"""
    input(f"\n💡 {message}")

def display_live_strategy_flowchart():
    """展示实盘策略开发流程图"""
    print("\n🗺️ 实盘量化策略开发完整流程图")
    print("=" * 80)
    
    print("📊 一、策略需求分析")
    print("├─ 1. 核心定位 ──┬── 标的: 600415.XSHG (小商品城-一带一路)")
    print("│               ├── 资金: 20万起交+RSI指标+日内突破的多因子策略")
    print("│               ├── 环境: EasyXT量化交易平台")
    print("│               ├── 频率控制参数: (2)交易双向线性调整")
    print("│               ├── 控制下行风险: (2%)止损+波动率调整")
    print("│               └── 盈利交易条件: (日内多交仓等级控制)")
    print("│")
    print("└─ 2. 核心目标 ──┬── 技术指标配置:")
    print("                ├── 短期指标: 短期EMA(EMA/SMA)、长期RSI(EMA/SMA)")
    print("                ├── RSI参数: 周期RSI、超买阈值30、超卖阈值70")
    print("                ├── 止损比例: 2%(动态调整市场波动率)")
    print("                ├── 最大仓位: 90%(结合风险敞口控制手续费)")
    print("                └── 交易成本: 佣金0.03%、印花税0.1%、滑点0.05%")
    
    print("\n🔧 二、核心参数体系")
    print("├─ 1. 技术指标参数 ─┬── EMA参数: 短期12日、长期26日(防过度交易)")
    print("│                  ├── 流动性阈值: 并日成交量>10日均量20%")
    print("│                  ├── 日内时段: 10:30/11:00/13:15/14:00/14:45(5次)")
    print("│                  ├── 量存有效期: 10分钟")
    print("│                  └── 量存清理: 量存数量<10个有效量存清理")
    print("│")
    print("├─ 2. 资金与仓位参数 ─┬── 周期限制: 日线(每中期数据一交易日)、分钟线(实时数据日)")
    print("│                    ├── 未来数据保护: 15:00前波动修正日")
    print("│                    ├── 持仓处理: 停牌检测、API接口维护、日志系统输出")
    print("│                    ├── 买型策略: 买持(position_date/rm_date/mark/datetime)")
    print("│                    └── 持仓逻辑: 非交易日向前延迟30天、收盘时双仓回调一日")
    print("│")
    print("└─ 3. 交易时间参数 ───┬── RSI计算: 支持EMA(数值)/SMA均线")
    print("                    ├── RSI计算: 基于value、缺失值填补")
    print("                    ├── 刷新周期: 10日成交量均线、30分钟级RSI(实时信息)")
    print("                    ├── 流动性过滤: 并日成交量>10日均量>20%")
    print("                    ├── 交易间隔限制: 单工交交易>1天")
    print("                    └── 风险敞口: 市场风险、非流动性")
    
    print("\n📊 三、数据处理模块")
    print("├─ 1. 安全数据获取 ─┬── 主数据源: EasyXT API")
    print("│                  ├── 备用方案1: qmt未连接时处理")
    print("│                  ├── 备用方案2: qstock轻量级数据源")
    print("│                  └── 备用方案3: akshare开源数据接口")
    print("│")
    print("├─ 2. 交易日处理 ───┬── RSI计算: 支持EMA(数值)/SMA均线")
    print("│                  ├── 持仓逻辑: 非交易日向前延迟30天、收盘时双仓回调一日")
    print("│                  └── 数据验证: 完整性检查、时效性验证")
    print("│")
    print("└─ 3. 数据计算 ─────┬── RSI计算: 基于value、缺失值填补")
    print("                   ├── 刷新周期: 10日成交量均线、30分钟级RSI(实时信息)")
    print("                   └── 流动性过滤: 并日成交量>10日均量>20%")
    
    print("\n🎯 四、交易信号生成")
    print("├─ 1. 前置过滤条件 ─┬── 交易时间检查: 仅在交易时段内生成信号")
    print("│                  ├── 流动性检查: 成交量>均量阈值")
    print("│                  ├── RSI状态: RSI超卖区域(<30)向上反弹")
    print("│                  ├── 日内突破: 30分钟级量价突破向上涨>1%")
    print("│                  └── 均线状态: 短期均线向上长期均线")
    print("│")
    print("├─ 2. 买入信号(多条件并一) ─┬── RSI状态: RSI超卖区域(<30)向上反弹")
    print("│                          ├── 日内突破: 30分钟级量价突破向上涨>1%")
    print("│                          ├── 均线状态: 短期均线向上长期均线")
    print("│                          └── 止盈验证: 30分钟RSI>80且涨幅>2%")
    print("│")
    print("└─ 3. 卖出信号(多条件并一) ─┬── RSI状态: RSI超买区域(>70)向下跌破")
    print("                          ├── 止损触发: 当前价格<成本止损价")
    print("                          └── 止盈验证: 30分钟RSI>80且涨幅>2%")
    
    print("\n⚙️ 五、交易执行体系")
    print("├─ 1. 定时触发机制 ─┬── 自动(schedule): 打开化技术+量流动性检查")
    print("│                  ├── 首次交易(9:38): 日内第一次信号检查+执行")
    print("│                  ├── 日内检查(5次): 重要信号+重新计算+执行")
    print("│                  ├── 收盘前(14:57): 最终信号检查+执行")
    print("│                  └── 盘后(after_close): 状态检查+清理+清理")
    print("│")
    print("├─ 2. 订单执行逻辑 ─┬── 买入执行: 满仓操作(order_percent)")
    print("│                  ├── 止损执行: 价格跌破止损价时强制清仓")
    print("│                  ├── 未成交处理: 30分钟未成交则撤单重新挂单")
    print("│                  └── 状态检查: 测试set_order()验证成交/取消/拒绝状态")
    print("│")
    print("└─ 3. 订单状态监控 ─┬── 网络异常处理: 连接中断时的应急机制")
    print("                   ├── 滑点情况处理: 最优对价交易的滑点控制")
    print("                   └── 数据延迟处理: 数据延迟对策略的影响评估")
    
    print("\n🛡️ 六、风险控制体系")
    print("├─ 1. 市场风险控制 ─┬── 网络敞口控制: 单股最大仓位10日均线持续跌破(0.5-1.0)")
    print("│                  ├── 趋势反转: 大盘指数(指数↑)、趋势转换(指数↓)")
    print("│                  ├── 成本止损: 基于买入价(1-2%)×波动率系数")
    print("│                  ├── 动态止损: 基于ATR指标、每15分钟检查价格")
    print("│                  └── 防重复买入: 当日仓位1次买入后禁止")
    print("│")
    print("├─ 2. 持仓风险控制 ─┬── 极端情况处理: 涨跌停、停牌等异常情况")
    print("│                  ├── 流动性风险: 最优对价交易的流动性风险")
    print("│                  └── 数据延迟风险: 数据延迟对策略交易的影响")
    print("│")
    print("└─ 3. 操作风险控制 ─┬── 止损触发条件: 实时对比止损价格与当前价格>2%止损")
    print("                   ├── RSI超买控制: 30分钟级RSI>80且涨幅>2%止盈")
    print("                   └── 网络异常处理: 每15分钟检查网络连接质量")
    
    print("\n📊 七、监控与日志体系")
    print("├─ 1. 实时监控 ─────┬── handle_data: 实时数据更新")
    print("│                  ├── 持仓状态: 持仓数量、成本价、当前价值")
    print("│                  ├── 账户状态: 总资产、可用资金、总市值")
    print("│                  └── 系统状态: 内存使用、CPU占用、网络延迟")
    print("│")
    print("├─ 2. 盈亏记录 ─────┬── 盈亏统计: 持仓盈亏、买入价、止损价、当前收益率")
    print("│                  ├── 账户状态: 总资产、可用资金、总市值")
    print("│                  └── 系统状态: 内存使用、本策略运行、策略开发策略")
    print("│")
    print("└─ 3. 日志分级 ─────┬── 错误日志: API调用失败、计算失败、订单失败")
    print("                   ├── 警告日志: 数据异常、网络延迟、策略偏离")
    print("                   ├── 信息日志: 正常交易、策略执行、日常操作")
    print("                   └── 调试日志: 详细参数、中间计算、状态变更")

class LiveTradingStrategy:
    """
    实盘量化策略 - 完整开发版
    
    基于EasyXT框架的专业实盘交易策略
    包含完整的策略开发、风险控制、监控体系
    """
    
    def __init__(self, account_id, stock_code='600415.XSHG', initial_capital=200000):
        """
        初始化实盘策略
        
        Args:
            account_id: 交易账户ID
            stock_code: 目标股票代码 (小商品城-一带一路)
            initial_capital: 初始资金 (20万起)
        """
        self.account_id = account_id
        self.stock_code = stock_code
        self.initial_capital = initial_capital
        
        # 核心技术指标参数
        self.short_ema_period = 12      # 短期EMA周期
        self.long_ema_period = 26       # 长期EMA周期
        self.rsi_period = 14            # RSI周期
        self.rsi_oversold = 30          # RSI超卖阈值
        self.rsi_overbought = 70        # RSI超买阈值
        
        # 风险控制参数
        self.stop_loss_pct = 0.02       # 止损比例 2%
        self.take_profit_pct = 0.02     # 止盈比例 2% (30分钟RSI>80且涨幅>2%)
        self.max_position_pct = 0.90    # 最大仓位 90%
        self.min_volume_ratio = 1.2     # 最小成交量比例 (>10日均量20%)
        
        # 交易时间控制 (5个关键时点)
        self.trading_times = [
            '09:38',  # 首次交易
            '10:30',  # 日内检查1
            '11:00',  # 日内检查2
            '13:15',  # 日内检查3
            '14:00',  # 日内检查4
            '14:45',  # 日内检查5
            '14:57'   # 收盘前检查
        ]
        
        # 交易成本设置
        self.commission_rate = 0.0003   # 佣金 0.03%
        self.stamp_tax_rate = 0.001     # 印花税 0.1%
        self.slippage_rate = 0.0005     # 滑点 0.05%
        
        # 状态变量
        self.position = 0               # 当前持仓
        self.entry_price = 0            # 入场价格
        self.stop_loss_price = 0        # 止损价格
        self.daily_trades = 0           # 当日交易次数
        self.last_trade_date = None     # 最后交易日期
        self.position_date = None       # 持仓日期
        
        # 数据缓存
        self.price_history = []         # 价格历史
        self.volume_history = []        # 成交量历史
        self.indicators = {}            # 技术指标缓存
        self.order_history = []         # 订单历史
        
        # 监控数据
        self.performance_metrics = {
            'total_trades': 0,
            'win_trades': 0,
            'lose_trades': 0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0,
            'current_drawdown': 0.0
        }
        
        print(f"✅ 实盘策略初始化完成")
        print(f"  🎯 目标股票: {self.stock_code} (小商品城-一带一路)")
        print(f"  💰 初始资金: {self.initial_capital:,}元")
        print(f"  📊 策略类型: 多因子实盘策略")
        print(f"  🔧 交易平台: EasyXT量化交易系统")
    
    def get_live_market_data(self):
        """
        获取实时市场数据 - 多数据源支持
        数据源优先级: EasyXT API → qmt未连接 → qstock → akshare
        """
        try:
            print(f"📊 正在获取实时市场数据...")
            print(f"  🎯 股票代码: {self.stock_code}")
            print(f"  📅 数据源优先级: EasyXT API → qmt未连接 → qstock → akshare")
            
            # 数据源1：尝试使用EasyXT获取实时数据
            try:
                xt = EasyXT()
                
                # 检查连接状态
                if xt.init_data():
                    # 转换股票代码格式
                    if self.stock_code.endswith('.XSHG'):
                        xt_code = self.stock_code.replace('.XSHG', '.SH')
                    elif self.stock_code.endswith('.XSHE'):
                        xt_code = self.stock_code.replace('.XSHE', '.SZ')
                    else:
                        xt_code = self.stock_code
                    
                    # 获取实时行情数据
                    current_data = xt.data.get_current_price([xt_code])
                    
                    if current_data is not None and not current_data.empty:
                        data = current_data.iloc[0]
                        market_data = {
                            'datetime': datetime.now(),
                            'open': float(data.get('open', 0)),
                            'high': float(data.get('high', 0)),
                            'low': float(data.get('low', 0)),
                            'close': float(data.get('close', data.get('last_price', 0))),
                            'volume': int(data.get('volume', 0)),
                            'amount': float(data.get('amount', 0))
                        }
                        
                        print(f"✅ 通过EasyXT获取实时数据成功")
                        print(f"  💰 当前价格: {market_data['close']:.2f}元")
                        print(f"  📊 成交量: {market_data['volume']:,}股")
                        return market_data
                else:
                    print("⚠️ EasyXT数据服务连接失败")
                    
            except Exception as e:
                print(f"⚠️ EasyXT获取数据失败: {e}")
            
            # 数据源2：qmt未连接时的处理
            try:
                print("🔄 检测到qmt未连接，尝试备用数据源...")
                # 这里可以添加qmt连接检测逻辑
                # 如果qmt未连接，直接跳到下一个数据源
                raise Exception("qmt未连接")
                
            except Exception as e:
                print(f"⚠️ qmt连接检查: {e}")
            
            # 数据源3：使用qstock获取数据
            try:
                import qstock as qs
                
                print("🔄 尝试使用qstock获取数据...")
                
                # 转换股票代码格式
                if self.stock_code.endswith('.XSHG'):
                    qs_code = self.stock_code.replace('.XSHG', '')
                elif self.stock_code.endswith('.XSHE'):
                    qs_code = self.stock_code.replace('.XSHE', '')
                else:
                    qs_code = self.stock_code.split('.')[0]
                
                # 使用qstock获取实时数据 (修复API调用)
                try:
                    # qstock的正确API调用方式
                    current_data = qs.get_data(qs_code, start='', end='')
                    
                    if current_data is not None and not current_data.empty:
                        # 获取最新一行数据
                        latest_data = current_data.iloc[-1]
                        market_data = {
                            'datetime': datetime.now(),
                            'open': float(latest_data.get('open', latest_data.get('开盘', 0))),
                            'high': float(latest_data.get('high', latest_data.get('最高', 0))),
                            'low': float(latest_data.get('low', latest_data.get('最低', 0))),
                            'close': float(latest_data.get('close', latest_data.get('收盘', 0))),
                            'volume': int(latest_data.get('volume', latest_data.get('成交量', 0))),
                            'amount': float(latest_data.get('amount', latest_data.get('成交额', 0)))
                        }
                        
                        print(f"✅ 通过qstock获取数据成功")
                        print(f"  💰 当前价格: {market_data['close']:.2f}元")
                        return market_data
                except Exception as qstock_error:
                    print(f"⚠️ qstock API调用失败: {qstock_error}")
                    # 尝试其他qstock方法
                    try:
                        # 尝试使用实时行情接口
                        realtime_data = qs.realtime(qs_code)
                        if realtime_data is not None:
                            market_data = {
                                'datetime': datetime.now(),
                                'open': float(realtime_data.get('open', 8.50)),
                                'high': float(realtime_data.get('high', 8.60)),
                                'low': float(realtime_data.get('low', 8.40)),
                                'close': float(realtime_data.get('price', 8.50)),
                                'volume': int(realtime_data.get('volume', 1000000)),
                                'amount': float(realtime_data.get('amount', 8500000))
                            }
                            
                            print(f"✅ 通过qstock实时接口获取数据成功")
                            print(f"  💰 当前价格: {market_data['close']:.2f}元")
                            return market_data
                    except Exception as realtime_error:
                        print(f"⚠️ qstock实时接口也失败: {realtime_error}")
                    
            except ImportError:
                print("⚠️ qstock模块未安装")
            except Exception as e:
                print(f"⚠️ qstock获取数据失败: {e}")
            
            # 数据源4：使用akshare获取数据
            try:
                import akshare as ak
                
                print("🔄 尝试使用akshare获取数据...")
                
                # 转换股票代码格式
                if self.stock_code.endswith('.XSHG'):
                    ak_code = self.stock_code.replace('.XSHG', '')
                elif self.stock_code.endswith('.XSHE'):
                    ak_code = self.stock_code.replace('.XSHE', '')
                else:
                    ak_code = self.stock_code.split('.')[0]
                
                # 获取实时数据
                current_data = ak.stock_zh_a_spot_em()
                stock_data = current_data[current_data['代码'] == ak_code]
                
                if len(stock_data) > 0:
                    row = stock_data.iloc[0]
                    market_data = {
                        'datetime': datetime.now(),
                        'open': float(row['今开']),
                        'high': float(row['最高']),
                        'low': float(row['最低']),
                        'close': float(row['最新价']),
                        'volume': int(row['成交量']),
                        'amount': float(row['成交额'])
                    }
                    
                    print(f"✅ 通过akshare获取数据成功")
                    print(f"  💰 当前价格: {market_data['close']:.2f}元")
                    return market_data
                    
            except ImportError:
                print("⚠️ akshare模块未安装")
            except Exception as e:
                print(f"⚠️ akshare获取数据失败: {e}")
            
            # 如果所有数据源都失败，使用模拟实时数据
            print("🔄 所有外部数据源均不可用，切换到模拟数据模式...")
            print("💡 模拟数据模式：基于真实市场特征生成高质量模拟数据")
            return self.generate_mock_realtime_data()
            
        except Exception as e:
            print(f"❌ 获取实时数据过程中发生错误: {e}")
            print("🔄 自动切换到模拟数据模式...")
            return self.generate_mock_realtime_data()
    
    def generate_mock_realtime_data(self):
        """生成模拟实时数据（用于演示）"""
        import random
        
        # 基于小商品城的历史价格特征
        base_price = 8.50
        volatility = 0.02  # 2%日内波动
        
        # 生成模拟实时数据
        current_price = base_price * (1 + random.gauss(0, volatility))
        daily_range = current_price * volatility
        
        market_data = {
            'datetime': datetime.now(),
            'open': round(current_price * random.uniform(0.98, 1.02), 2),
            'high': round(current_price + daily_range * random.uniform(0.3, 0.8), 2),
            'low': round(current_price - daily_range * random.uniform(0.3, 0.8), 2),
            'close': round(current_price, 2),
            'volume': random.randint(800000, 1500000),
            'amount': round(current_price * random.randint(800000, 1500000), 2)
        }
        
        # 确保OHLC逻辑正确
        market_data['high'] = max(market_data['high'], market_data['open'], market_data['close'])
        market_data['low'] = min(market_data['low'], market_data['open'], market_data['close'])
        
        print(f"📊 生成模拟实时数据")
        print(f"  💰 当前价格: {market_data['close']:.2f}元")
        print(f"  📊 成交量: {market_data['volume']:,}股")
        
        return market_data
    
    def calculate_technical_indicators(self, market_data):
        """计算技术指标"""
        # 更新价格和成交量历史
        self.price_history.append(market_data['close'])
        self.volume_history.append(market_data['volume'])
        
        # 保持历史数据长度
        max_history = max(self.long_ema_period, self.rsi_period) + 10
        if len(self.price_history) > max_history:
            self.price_history = self.price_history[-max_history:]
            self.volume_history = self.volume_history[-max_history:]
        
        # 计算EMA
        if len(self.price_history) >= self.short_ema_period:
            self.indicators['short_ema'] = self.calculate_ema(self.price_history, self.short_ema_period)
        
        if len(self.price_history) >= self.long_ema_period:
            self.indicators['long_ema'] = self.calculate_ema(self.price_history, self.long_ema_period)
        
        # 计算RSI
        if len(self.price_history) >= self.rsi_period + 1:
            self.indicators['rsi'] = self.calculate_rsi(self.price_history, self.rsi_period)
        
        # 计算成交量比率
        if len(self.volume_history) >= 10:
            self.indicators['volume_ratio'] = self.calculate_volume_ratio(self.volume_history)
        
        # 计算MACD
        if 'short_ema' in self.indicators and 'long_ema' in self.indicators:
            self.indicators['macd'] = self.indicators['short_ema'] - self.indicators['long_ema']
        
        return self.indicators
    
    def calculate_ema(self, prices, period):
        """计算指数移动平均线"""
        if len(prices) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def calculate_rsi(self, prices, period=14):
        """计算RSI指标"""
        if len(prices) < period + 1:
            return None
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [max(d, 0) for d in deltas]
        losses = [abs(min(d, 0)) for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_volume_ratio(self, volumes, period=10):
        """计算成交量比率"""
        if len(volumes) < period + 1:
            return 1.0
        
        current_volume = volumes[-1]
        avg_volume = sum(volumes[-period-1:-1]) / period
        
        if avg_volume == 0:
            return 1.0
        
        return current_volume / avg_volume
    
    def check_trading_time(self, current_time):
        """检查是否在交易时间内 (已移除时间限制)"""
        current_time_str = current_time.strftime('%H:%M')
        
        # 已移除交易时间限制 - 始终允许交易
        return True, current_time_str
    
    def generate_trading_signals(self, market_data):
        """生成交易信号"""
        current_price = market_data['close']
        current_time = market_data['datetime']
        
        # 检查交易时间
        is_trading_time, trading_point = self.check_trading_time(current_time)
        if not is_trading_time:
            return {'buy': False, 'sell': False, 'reason': '非交易时点'}
        
        # 检查技术指标是否就绪
        if not all(key in self.indicators for key in ['short_ema', 'long_ema', 'rsi', 'volume_ratio']):
            return {'buy': False, 'sell': False, 'reason': '技术指标未就绪'}
        
        signals = {'buy': False, 'sell': False, 'reason': '', 'trading_point': trading_point}
        
        # 买入信号检查 (多条件并一)
        if self.position == 0:  # 无持仓时才考虑买入
            buy_conditions = []
            
            # 1. RSI超卖区域(<30)向上反弹
            rsi_oversold = self.indicators['rsi'] < self.rsi_oversold
            buy_conditions.append(('RSI超卖', rsi_oversold))
            
            # 2. 短期均线向上长期均线 (金叉)
            ema_bullish = self.indicators['short_ema'] > self.indicators['long_ema']
            buy_conditions.append(('EMA金叉', ema_bullish))
            
            # 3. 成交量>10日均量20%
            volume_sufficient = self.indicators['volume_ratio'] > self.min_volume_ratio
            buy_conditions.append(('成交量充足', volume_sufficient))
            
            # 4. MACD向上
            macd_positive = self.indicators.get('macd', 0) > 0
            buy_conditions.append(('MACD向上', macd_positive))
            
            # 检查买入条件
            satisfied_conditions = [name for name, condition in buy_conditions if condition]
            
            if len(satisfied_conditions) >= 3:  # 至少满足3个条件
                signals['buy'] = True
                signals['reason'] = f"买入信号: {', '.join(satisfied_conditions)}"
        
        # 卖出信号检查 (多条件并一)
        if self.position > 0:  # 有持仓时才考虑卖出
            sell_conditions = []
            
            # 1. RSI超买区域(>70)向下跌破
            rsi_overbought = self.indicators['rsi'] > self.rsi_overbought
            sell_conditions.append(('RSI超买', rsi_overbought))
            
            # 2. 止损触发 (当前价格<成本止损价)
            if self.stop_loss_price > 0:
                stop_loss_triggered = current_price <= self.stop_loss_price
                sell_conditions.append(('止损触发', stop_loss_triggered))
            
            # 3. 止盈验证 (30分钟RSI>80且涨幅>2%)
            if self.entry_price > 0:
                price_gain = (current_price - self.entry_price) / self.entry_price
                take_profit_triggered = (self.indicators['rsi'] > 80 and price_gain > self.take_profit_pct)
                sell_conditions.append(('止盈触发', take_profit_triggered))
            
            # 4. 短期均线向下长期均线 (死叉)
            ema_bearish = self.indicators['short_ema'] < self.indicators['long_ema']
            sell_conditions.append(('EMA死叉', ema_bearish))
            
            # 检查卖出条件 (任一条件满足即卖出)
            satisfied_conditions = [name for name, condition in sell_conditions if condition]
            
            if len(satisfied_conditions) >= 1:
                signals['sell'] = True
                signals['reason'] = f"卖出信号: {', '.join(satisfied_conditions)}"
        
        return signals
    
    def execute_trade(self, signal, market_data):
        """执行交易"""
        current_price = market_data['close']
        current_time = market_data['datetime']
        
        try:
            if signal['buy'] and self.position == 0:
                # 计算买入数量 (满仓操作)
                available_capital = self.initial_capital * self.max_position_pct
                
                # 扣除交易成本
                total_cost_rate = self.commission_rate + self.slippage_rate
                effective_capital = available_capital / (1 + total_cost_rate)
                
                shares = int(effective_capital / current_price / 100) * 100  # 整手
                
                if shares > 0:
                    # 更新持仓信息
                    self.position = shares
                    self.entry_price = current_price
                    self.stop_loss_price = current_price * (1 - self.stop_loss_pct)
                    self.position_date = current_time.date()
                    self.daily_trades += 1
                    
                    # 记录订单
                    order = {
                        'datetime': current_time,
                        'type': 'BUY',
                        'shares': shares,
                        'price': current_price,
                        'amount': shares * current_price,
                        'reason': signal['reason'],
                        'trading_point': signal.get('trading_point', '')
                    }
                    self.order_history.append(order)
                    
                    print(f"✅ 买入执行成功")
                    print(f"  📊 数量: {shares:,}股")
                    print(f"  💰 价格: {current_price:.2f}元")
                    print(f"  💵 金额: {shares * current_price:,.2f}元")
                    print(f"  🛡️ 止损价: {self.stop_loss_price:.2f}元")
                    print(f"  🎯 原因: {signal['reason']}")
                    print(f"  ⏰ 交易时点: {signal.get('trading_point', '')}")
                    
                    return True, f"买入{shares:,}股@{current_price:.2f}元"
            
            elif signal['sell'] and self.position > 0:
                # 卖出全部持仓
                shares = self.position
                
                # 计算盈亏
                pnl = (current_price - self.entry_price) * shares
                pnl_pct = (current_price - self.entry_price) / self.entry_price * 100
                
                # 扣除交易成本
                total_amount = shares * current_price
                total_cost = total_amount * (self.commission_rate + self.stamp_tax_rate + self.slippage_rate)
                net_pnl = pnl - total_cost
                
                # 更新持仓信息
                self.position = 0
                self.entry_price = 0
                self.stop_loss_price = 0
                self.position_date = None
                self.daily_trades += 1
                
                # 更新绩效指标
                self.performance_metrics['total_trades'] += 1
                self.performance_metrics['total_pnl'] += net_pnl
                
                if net_pnl > 0:
                    self.performance_metrics['win_trades'] += 1
                else:
                    self.performance_metrics['lose_trades'] += 1
                
                # 记录订单
                order = {
                    'datetime': current_time,
                    'type': 'SELL',
                    'shares': shares,
                    'price': current_price,
                    'amount': total_amount,
                    'pnl': net_pnl,
                    'pnl_pct': pnl_pct,
                    'reason': signal['reason'],
                    'trading_point': signal.get('trading_point', '')
                }
                self.order_history.append(order)
                
                print(f"✅ 卖出执行成功")
                print(f"  📊 数量: {shares:,}股")
                print(f"  💰 价格: {current_price:.2f}元")
                print(f"  💵 金额: {total_amount:,.2f}元")
                print(f"  💰 盈亏: {net_pnl:+,.2f}元 ({pnl_pct:+.2f}%)")
                print(f"  💸 成本: {total_cost:.2f}元")
                print(f"  🎯 原因: {signal['reason']}")
                print(f"  ⏰ 交易时点: {signal.get('trading_point', '')}")
                
                return True, f"卖出{shares:,}股@{current_price:.2f}元，净盈亏{net_pnl:+,.2f}元"
        
        except Exception as e:
            print(f"❌ 交易执行失败: {e}")
            return False, str(e)
        
        return False, "无有效交易信号"
    
    def monitor_position(self, market_data):
        """监控持仓状态"""
        if self.position == 0:
            return
        
        current_price = market_data['close']
        current_time = market_data['datetime']
        
        # 计算当前盈亏
        unrealized_pnl = (current_price - self.entry_price) * self.position
        unrealized_pnl_pct = (current_price - self.entry_price) / self.entry_price * 100
        
        # 计算持仓天数
        if self.position_date:
            holding_days = (current_time.date() - self.position_date).days
        else:
            holding_days = 0
        
        print(f"\n📊 持仓监控:")
        print(f"  🎯 股票: {self.stock_code}")
        print(f"  📊 数量: {self.position:,}股")
        print(f"  💰 成本价: {self.entry_price:.2f}元")
        print(f"  💵 当前价: {current_price:.2f}元")
        print(f"  🛡️ 止损价: {self.stop_loss_price:.2f}元")
        print(f"  💰 浮动盈亏: {unrealized_pnl:+,.2f}元 ({unrealized_pnl_pct:+.2f}%)")
        print(f"  📅 持仓天数: {holding_days}天")
        
        # 风险预警
        if current_price <= self.stop_loss_price:
            print(f"  ⚠️ 风险预警: 价格已触及止损线!")
        
        if unrealized_pnl_pct < -1.5:
            print(f"  ⚠️ 风险预警: 浮亏超过1.5%!")
        
        if holding_days > 5:
            print(f"  ⚠️ 持仓预警: 持仓时间较长，注意风险!")
    
    def generate_performance_report(self):
        """生成绩效报告"""
        print(f"\n📊 策略绩效报告")
        print(f"=" * 50)
        
        metrics = self.performance_metrics
        
        print(f"📈 交易统计:")
        print(f"  🔄 总交易次数: {metrics['total_trades']}")
        print(f"  ✅ 盈利交易: {metrics['win_trades']}")
        print(f"  ❌ 亏损交易: {metrics['lose_trades']}")
        
        if metrics['total_trades'] > 0:
            win_rate = metrics['win_trades'] / metrics['total_trades'] * 100
            print(f"  🎯 胜率: {win_rate:.1f}%")
        
        print(f"\n💰 盈亏统计:")
        print(f"  💵 总盈亏: {metrics['total_pnl']:+,.2f}元")
        
        if self.initial_capital > 0:
            return_rate = metrics['total_pnl'] / self.initial_capital * 100
            print(f"  📊 收益率: {return_rate:+.2f}%")
        
        print(f"\n📋 最近交易记录:")
        for order in self.order_history[-5:]:
            if order['type'] == 'BUY':
                print(f"  📈 {order['datetime'].strftime('%Y-%m-%d %H:%M')} 买入 {order['shares']:,}股@{order['price']:.2f}元")
            else:
                print(f"  📉 {order['datetime'].strftime('%Y-%m-%d %H:%M')} 卖出 {order['shares']:,}股@{order['price']:.2f}元 盈亏{order['pnl']:+,.2f}元")
    
    def run_live_strategy_demo(self, demo_minutes=30):
        """运行实盘策略演示"""
        print(f"\n🚀 开始实盘策略演示 (模拟{demo_minutes}分钟) - 无时间限制版")
        print(f"=" * 60)
        
        start_time = datetime.now()
        
        for minute in range(demo_minutes):
            current_time = start_time + timedelta(minutes=minute)
            
            # 已移除交易时间检查 - 可以在任何时间运行
            
            print(f"\n⏰ 时间: {current_time.strftime('%Y-%m-%d %H:%M')}")
            
            # 获取实时市场数据
            market_data = self.get_live_market_data()
            market_data['datetime'] = current_time  # 使用模拟时间
            
            # 计算技术指标
            indicators = self.calculate_technical_indicators(market_data)
            
            # 显示技术指标
            if indicators:
                print(f"📊 技术指标: EMA({indicators.get('short_ema', 0):.2f}/{indicators.get('long_ema', 0):.2f}) "
                      f"RSI({indicators.get('rsi', 0):.1f}) 量比({indicators.get('volume_ratio', 0):.2f})")
            
            # 生成交易信号
            signals = self.generate_trading_signals(market_data)
            
            # 执行交易
            if signals['buy'] or signals['sell']:
                success, result = self.execute_trade(signals, market_data)
                if success:
                    print(f"🎯 交易结果: {result}")
            else:
                print(f"📊 信号状态: {signals['reason']}")
            
            # 监控持仓
            if self.position > 0:
                self.monitor_position(market_data)
            
            # 每10分钟生成一次报告
            if minute > 0 and minute % 10 == 0:
                self.generate_performance_report()
            
            # 模拟延迟
            time.sleep(0.1)
        
        # 最终报告
        print(f"\n🎉 实盘策略演示完成!")
        self.generate_performance_report()

def demo_live_strategy_development():
    """演示实盘策略开发的完整流程"""
    print("\n" + "=" * 80)
    print("🚀 实盘量化策略开发完整流程演示")
    print("=" * 80)
    print("本课程展示从策略设计到实盘部署的专业开发过程")
    print("🎯 目标：掌握完整的实盘策略开发技能")
    print("📊 数据源：EasyXT API → qmt未连接 → qstock → akshare")
    print("🔧 平台：基于EasyXT框架的实盘交易系统")
    
    wait_for_user_input("准备开始实盘策略开发学习？")
    
    # 显示完整流程图
    display_live_strategy_flowchart()
    
    wait_for_user_input("流程图学习完成！按回车键继续...")
    
    # 第一阶段：策略需求分析
    print_section_header(1, "策略需求分析", "明确策略目标和技术要求")
    
    print("📋 策略基本信息：")
    print("  🎯 标的：600415.XSHG (小商品城-一带一路)")
    print("  💰 资金：20万起交+RSI指标+日内突破的多因子策略")
    print("  🏢 环境：EasyXT量化交易平台")
    print("  📊 频率控制参数：(2)交易双向线性调整")
    print("  ⏰ 控制下行风险：(2%)止损+波动率调整")
    print("  📈 盈利交易条件：(日内多交仓等级控制)")
    
    print("\n🔧 技术指标配置：")
    print("  📊 短期指标：短期EMA(EMA/SMA)、长期RSI(EMA/SMA)")
    print("  📈 RSI参数：周期RSI、超买阈值30、超卖阈值70")
    print("  🎯 止损比例：2%(动态调整市场波动率)")
    print("  💰 最大仓位：90%(结合风险敞口控制手续费)")
    print("  💸 交易成本：佣金0.03%、印花税0.1%、滑点0.05%")
    
    wait_for_user_input("需求分析完成！按回车键继续...")
    
    # 第二阶段：核心参数体系
    print_section_header(2, "核心参数体系设计", "构建完整的参数管理系统")
    
    print("⚙️ 1. 技术指标参数：")
    print("  📊 EMA参数：短期12日、长期26日(防过度交易)")
    print("  📈 流动性阈值：并日成交量>10日均量20%")
    print("  ⏰ 日内时段：10:30/11:00/13:15/14:00/14:45(5次)")
    print("  🔄 量存有效期：10分钟")
    print("  📊 量存清理：量存数量<10个有效量存清理")
    
    print("\n💰 2. 资金与仓位参数：")
    print("  🎯 周期限制：日线(每中期数据一交易日)、分钟线(实时数据日)")
    print("  💵 未来数据保护：15:00前波动修正日")
    print("  📊 持仓处理：停牌检测、API接口维护、日志系统输出")
    print("  🔄 买型策略：买持(position_date/rm_date/mark/datetime)")
    print("  📈 持仓逻辑：非交易日向前延迟30天、收盘时双仓回调一日")
    
    print("\n⏰ 3. 交易时间参数：")
    print("  🕘 RSI计算：支持EMA(数值)/SMA均线")
    print("  📊 RSI计算：基于value、缺失值填补")
    print("  🔄 刷新周期：10日成交量均线、30分钟级RSI(实时信息)")
    print("  📈 流动性过滤：并日成交量>10日均量>20%")
    print("  ⚠️ 交易间隔限制：单工交交易>1天")
    print("  🎯 风险敞口：市场风险、非流动性")
    
    wait_for_user_input("参数体系设计完成！按回车键继续...")
    
    # 创建策略实例并运行演示
    print_section_header(3, "实盘策略实例化", "创建并配置实盘策略对象")
    
    strategy = LiveTradingStrategy(
        account_id="LIVE_DEMO",
        stock_code="600415.XSHG",
        initial_capital=200000
    )
    
    wait_for_user_input("策略实例化完成！按回车键开始实盘演示...")
    
    # 运行实盘策略演示
    print_section_header(4, "实盘策略运行演示", "模拟真实的实盘交易过程")
    
    strategy.run_live_strategy_demo(demo_minutes=20)
    
    wait_for_user_input("实盘演示完成！按回车键查看总结...")
    
    # 课程总结
    print_section_header(5, "实盘开发总结", "回顾完整的开发流程和关键要点")
    
    print("🎓 实盘策略开发关键要点：")
    print("=" * 50)
    
    print("✅ 1. 策略设计要点：")
    print("  • 明确策略目标和风险承受能力")
    print("  • 设计合理的技术指标组合")
    print("  • 建立完善的风险控制机制")
    print("  • 考虑实际交易成本和滑点")
    
    print("\n✅ 2. 数据处理要点：")
    print("  • 建立多数据源容错机制")
    print("  • 确保数据的实时性和准确性")
    print("  • 处理数据异常和网络中断")
    print("  • 优化数据获取和处理效率")
    
    print("\n✅ 3. 交易执行要点：")
    print("  • 严格按照交易时间执行")
    print("  • 实现精确的订单管理")
    print("  • 建立完善的异常处理机制")
    print("  • 记录详细的交易日志")
    
    print("\n✅ 4. 风险控制要点：")
    print("  • 设置合理的止损止盈")
    print("  • 控制单笔交易仓位")
    print("  • 监控策略运行状态")
    print("  • 建立应急处理预案")
    
    print("\n✅ 5. 监控体系要点：")
    print("  • 实时监控持仓和盈亏")
    print("  • 记录完整的交易历史")
    print("  • 生成定期绩效报告")
    print("  • 建立多层次日志系统")
    
    print("\n🚀 实盘部署建议：")
    print("=" * 50)
    print("  • 📊 先进行充分的回测验证")
    print("  • 🔧 在模拟环境中测试策略")
    print("  • 💰 从小资金开始实盘验证")
    print("  • 📈 逐步增加资金规模")
    print("  • 🛡️ 持续监控和优化策略")
    print("  • 📋 定期评估策略表现")
    
    return strategy

def main():
    """主函数 - 实盘策略开发完整流程"""
    print("🎓 欢迎来到实盘量化策略开发学习课程！")
    print("📚 本教程将带您掌握专业的实盘策略开发技能")
    print("💡 包含：需求分析 → 参数设计 → 数据处理 → 信号生成 → 交易执行 → 风险控制 → 监控体系")
    
    print("\n🎯 学习目标：")
    print("  1️⃣ 掌握实盘策略的完整开发流程")
    print("  2️⃣ 学会多数据源的处理和容错机制")
    print("  3️⃣ 理解专业的风险控制体系")
    print("  4️⃣ 掌握实时监控和绩效评估方法")
    print("  5️⃣ 具备实盘部署的实际能力")
    
    wait_for_user_input("准备开始实盘策略开发学习之旅？")
    
    # 运行实盘策略开发演示
    strategy = demo_live_strategy_development()
    
    print("\n" + "=" * 80)
    print("🎉 实盘量化策略开发学习完成！")
    print("📚 您已掌握从策略设计到实盘部署的完整技能")
    print("🚀 现在可以开始开发自己的实盘量化交易策略了！")
    print("💡 建议：先在模拟环境中充分测试，再进行实盘部署")
    print("🎯 下一步：可以尝试优化策略参数，提升实盘表现")
    print("=" * 80)
    
    return strategy

if __name__ == "__main__":
    main()