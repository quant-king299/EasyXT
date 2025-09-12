# -*- coding: utf-8 -*-
"""
策略开发学习实例 - 交互式学习版
本文件展示了使用easy_xt进行量化策略开发的基本方法和技巧
每个步骤都需要用户确认，方便逐步学习理解

作者: CodeBuddy
版本: 2.0 (交互式学习版)
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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def wait_for_user_input(message="按回车键继续..."):
    """等待用户输入"""
    input(f"\n💡 {message}")

def print_section_header(step_num, title, description=""):
    """打印章节标题"""
    print("\n" + "=" * 70)
    print(f"📚 步骤{step_num}: {title}")
    print("=" * 70)
    if description:
        print(f"📖 学习目标：{description}")

def print_subsection(subtitle):
    """打印子章节标题"""
    print(f"\n📌 {subtitle}")
    print("-" * 50)

class BaseStrategy:
    """基础策略类"""
    
    def __init__(self, account_id, stock_pool):
        self.account_id = account_id
        self.stock_pool = stock_pool if isinstance(stock_pool, list) else [stock_pool]
        self.easy_xt = EasyXT()
        self.is_initialized = False
        
    def initialize(self):
        """初始化策略"""
        try:
            if self.easy_xt.init_data():
                logger.info("✓ 数据服务连接成功")
                self.is_initialized = True
                return True
            else:
                logger.error("❌ 数据服务连接失败")
                return False
        except Exception as e:
            logger.error(f"❌ 策略初始化失败: {e}")
            return False
    
    def buy_stock(self, stock_code, quantity, price=None):
        """买入股票"""
        if not self.is_initialized:
            logger.warning("⚠️ 策略未初始化，无法执行交易")
            return False
            
        try:
            if price is None:
                # 市价买入
                result = self.easy_xt.buy(
                    account_id=self.account_id,
                    stock_code=stock_code,
                    quantity=quantity,
                    price_type='market'
                )
            else:
                # 限价买入
                result = self.easy_xt.buy(
                    account_id=self.account_id,
                    stock_code=stock_code,
                    quantity=quantity,
                    price=price,
                    price_type='limit'
                )
            
            logger.info(f"📈 买入订单提交: {stock_code}, 数量: {quantity}, 价格: {price or '市价'}")
            return result
            
        except Exception as e:
            logger.error(f"❌ 买入失败: {e}")
            return False
    
    def sell_stock(self, stock_code, quantity, price=None):
        """卖出股票"""
        if not self.is_initialized:
            logger.warning("⚠️ 策略未初始化，无法执行交易")
            return False
            
        try:
            if price is None:
                # 市价卖出
                result = self.easy_xt.sell(
                    account_id=self.account_id,
                    stock_code=stock_code,
                    quantity=quantity,
                    price_type='market'
                )
            else:
                # 限价卖出
                result = self.easy_xt.sell(
                    account_id=self.account_id,
                    stock_code=stock_code,
                    quantity=quantity,
                    price=price,
                    price_type='limit'
                )
            
            logger.info(f"📉 卖出订单提交: {stock_code}, 数量: {quantity}, 价格: {price or '市价'}")
            return result
            
        except Exception as e:
            logger.error(f"❌ 卖出失败: {e}")
            return False

class MovingAverageStrategy(BaseStrategy):
    """双均线策略"""
    
    def __init__(self, account_id, stock_pool, short_period=5, long_period=20):
        super().__init__(account_id, stock_pool)
        self.short_period = short_period
        self.long_period = long_period
        
    def calculate_signals(self, stock_code):
        """计算交易信号"""
        try:
            # 获取历史数据
            data = self.easy_xt.get_price(
                codes=stock_code,
                period='1d',
                count=self.long_period + 10
            )
            
            if data is not None and not data.empty:
                # 计算移动平均线
                data[f'MA{self.short_period}'] = data['close'].rolling(self.short_period).mean()
                data[f'MA{self.long_period}'] = data['close'].rolling(self.long_period).mean()
                
                # 生成信号
                latest = data.iloc[-1]
                previous = data.iloc[-2]
                
                # 金叉：短期均线上穿长期均线
                if (latest[f'MA{self.short_period}'] > latest[f'MA{self.long_period}'] and 
                    previous[f'MA{self.short_period}'] <= previous[f'MA{self.long_period}']):
                    return 'BUY'
                
                # 死叉：短期均线下穿长期均线
                elif (latest[f'MA{self.short_period}'] < latest[f'MA{self.long_period}'] and 
                      previous[f'MA{self.short_period}'] >= previous[f'MA{self.long_period}']):
                    return 'SELL'
                
                return 'HOLD'
            
        except Exception as e:
            logger.error(f"❌ 计算双均线信号失败: {e}")
        
        return 'HOLD'

class RSIStrategy(BaseStrategy):
    """RSI策略"""
    
    def __init__(self, account_id, stock_pool, rsi_period=14, oversold=30, overbought=70):
        super().__init__(account_id, stock_pool)
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        
    def calculate_rsi(self, stock_code):
        """计算RSI指标"""
        try:
            # 获取历史数据
            data = self.easy_xt.get_price(
                codes=stock_code,
                period='1d',
                count=self.rsi_period + 20
            )
            
            if data is not None and not data.empty:
                # 计算RSI
                delta = data['close'].diff()
                gain = delta.where(delta > 0, 0)
                loss = -delta.where(delta < 0, 0)
                avg_gain = gain.rolling(window=self.rsi_period).mean()
                avg_loss = loss.rolling(window=self.rsi_period).mean()
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                
                latest_rsi = rsi.iloc[-1]
                
                if latest_rsi < self.oversold:
                    return 'BUY', latest_rsi
                elif latest_rsi > self.overbought:
                    return 'SELL', latest_rsi
                else:
                    return 'HOLD', latest_rsi
                    
        except Exception as e:
            logger.error(f"❌ 计算RSI失败: {e}")
        
        return 'HOLD', 0

class GridStrategy(BaseStrategy):
    """网格策略"""
    
    def __init__(self, account_id, stock_code, base_price, grid_size=0.02, grid_num=10):
        super().__init__(account_id, [stock_code])
        self.stock_code = stock_code
        self.base_price = base_price
        self.grid_size = grid_size
        self.grid_num = grid_num
        self.grid_levels = []
        
    def setup_grid(self):
        """设置网格"""
        # 计算网格价位
        for i in range(-self.grid_num//2, self.grid_num//2 + 1):
            price = self.base_price * (1 + i * self.grid_size)
            self.grid_levels.append(round(price, 2))
        
        self.grid_levels.sort()
        logger.info(f"📊 网格价位设置完成: {self.grid_levels}")

class RiskManager:
    """风险管理器"""
    
    def __init__(self, max_position_ratio=0.1, max_loss_ratio=0.02, max_daily_trades=10):
        self.max_position_ratio = max_position_ratio
        self.max_loss_ratio = max_loss_ratio
        self.max_daily_trades = max_daily_trades
        self.daily_trades = 0
        
    def check_position_limit(self, account_info, stock_code, quantity, price):
        """检查仓位限制"""
        try:
            total_asset = account_info.get('total_asset', 0)
            position_value = quantity * price
            position_ratio = position_value / total_asset if total_asset > 0 else 0
            
            if position_ratio > self.max_position_ratio:
                logger.warning(f"⚠️ 仓位超限: {position_ratio:.2%} > {self.max_position_ratio:.2%}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 仓位检查失败: {e}")
            return True
    
    def check_stop_loss(self, position_info, current_price):
        """检查止损"""
        try:
            avg_price = position_info.get('avg_price', 0)
            if avg_price <= 0:
                return False
                
            loss_ratio = (avg_price - current_price) / avg_price
            
            if loss_ratio > self.max_loss_ratio:
                logger.warning(f"🚨 触发止损: 亏损{loss_ratio:.2%} > {self.max_loss_ratio:.2%}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ 止损检查失败: {e}")
            return False

class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, strategy_class, strategy_params, start_date, end_date, initial_capital=100000):
        self.strategy_class = strategy_class
        self.strategy_params = strategy_params
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.results = {}
        
    def run_backtest(self):
        """运行回测"""
        logger.info(f"📊 开始回测: {self.start_date} 到 {self.end_date}")
        
        # 这里是回测的核心逻辑
        # 实际实现需要获取历史数据并模拟交易
        
        # 模拟结果
        self.results = {
            'total_return': 0.15,
            'annual_return': 0.12,
            'max_drawdown': 0.08,
            'sharpe_ratio': 1.2,
            'win_rate': 0.65
        }
        
        return self.results

def get_stock_basic_info(stock_codes):
    """获取股票基本信息"""
    easy_xt = EasyXT()
    
    if not easy_xt.init_data():
        logger.error("❌ 数据服务初始化失败")
        return {}
    
    logger.info("✓ 数据服务连接成功")
    
    # 股票名称映射（实际应用中可以从数据库或API获取）
    stock_names = {
        '000001.SZ': '平安银行',
        '000002.SZ': '万科A',
        '600000.SH': '浦发银行',
        '600036.SH': '招商银行',
        '000858.SZ': '五粮液'
    }
    
    results = {}
    
    for stock_code in stock_codes:
        try:
            # 获取实时价格数据
            price_data = easy_xt.get_current_price([stock_code])
            
            if price_data is not None and not price_data.empty:
                tick = price_data.iloc[0]
                
                # 尝试不同的字段名，因为不同数据源可能使用不同的字段名
                current_price = 0
                change_pct = 0
                volume = 0
                
                # 尝试获取价格字段
                for price_field in ['lastPrice', 'last_price', 'close', 'price', 'current_price']:
                    if price_field in tick and pd.notna(tick[price_field]):
                        current_price = float(tick[price_field])
                        break
                
                # 尝试获取涨跌幅字段
                for pct_field in ['pctChg', 'pct_chg', 'change_pct', 'change_percent']:
                    if pct_field in tick and pd.notna(tick[pct_field]):
                        change_pct = float(tick[pct_field])
                        break
                
                # 尝试获取成交量字段
                for vol_field in ['volume', 'vol', 'trade_volume']:
                    if vol_field in tick and pd.notna(tick[vol_field]):
                        volume = int(tick[vol_field])
                        break
                
                # 如果价格仍为0，尝试使用历史数据获取最新价格
                if current_price == 0:
                    try:
                        hist_data = easy_xt.get_price(codes=stock_code, period='1d', count=1)
                        if hist_data is not None and not hist_data.empty:
                            current_price = float(hist_data.iloc[-1]['close'])
                            # 计算涨跌幅（如果有前一日数据）
                            if len(hist_data) > 1:
                                prev_close = float(hist_data.iloc[-2]['close'])
                                change_pct = ((current_price - prev_close) / prev_close) * 100
                    except Exception as hist_e:
                        logger.warning(f"⚠️ 获取 {stock_code} 历史数据失败: {hist_e}")
                
                results[stock_code] = {
                    'name': stock_names.get(stock_code, '未知股票'),
                    'current_price': current_price,
                    'change_pct': change_pct,
                    'volume': volume,
                    'turnover': tick.get('amount', tick.get('turnover', 0))
                }
                
                # 打印调试信息
                logger.info(f"📊 {stock_code} 数据字段: {list(tick.index)}")
                
            else:
                logger.warning(f"⚠️ {stock_code} 未获取到数据")
                results[stock_code] = {
                    'name': stock_names.get(stock_code, '未知股票'),
                    'current_price': 0,
                    'change_pct': 0,
                    'volume': 0,
                    'turnover': 0
                }
                
        except Exception as e:
            logger.error(f"❌ 获取 {stock_code} 信息失败: {e}")
            results[stock_code] = {
                'name': stock_names.get(stock_code, '未知股票'),
                'current_price': 0,
                'change_pct': 0,
                'volume': 0,
                'turnover': 0
            }
    
    return results

def calculate_technical_indicators(stock_code):
    """计算技术指标"""
    easy_xt = EasyXT()
    
    if not easy_xt.init_data():
        logger.error("❌ 数据服务初始化失败")
        return None
    
    try:
        # 获取历史数据
        data = easy_xt.get_price(codes=stock_code, period='1d', count=50)
        
        if data is not None and not data.empty:
            indicators = {}
            
            # 移动平均线
            indicators['MA5'] = data['close'].rolling(5).mean()
            indicators['MA10'] = data['close'].rolling(10).mean()
            indicators['MA20'] = data['close'].rolling(20).mean()
            
            # MACD
            exp1 = data['close'].ewm(span=12).mean()
            exp2 = data['close'].ewm(span=26).mean()
            indicators['MACD'] = exp1 - exp2
            indicators['Signal'] = indicators['MACD'].ewm(span=9).mean()
            
            # 布林带
            ma20 = data['close'].rolling(20).mean()
            std20 = data['close'].rolling(20).std()
            indicators['Upper_Band'] = ma20 + (std20 * 2)
            indicators['Lower_Band'] = ma20 - (std20 * 2)
            
            # RSI
            delta = data['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            indicators['RSI'] = 100 - (100 / (1 + rs))
            
            return indicators
            
    except Exception as e:
        logger.error(f"❌ 计算技术指标失败: {e}")
    
    return None

def interactive_demo():
    """交互式演示"""
    print("🎓 策略开发学习实例 - 交互式学习版")
    print("=" * 70)
    print("📚 本教程将逐步演示量化策略开发的各个环节")
    print("💡 每个步骤都需要您按回车键确认，方便学习理解")
    print("🎯 学习完成后，您将掌握完整的量化交易开发流程")
    wait_for_user_input("准备开始学习？按回车键开始...")
    
    # 步骤1: 获取股票基本信息
    print_section_header(1, "获取股票基本信息", "了解如何获取股票的基本信息和实时数据")
    print("📖 涉及知识：EasyXT数据接口、股票代码规范、实时行情获取")
    wait_for_user_input("开始演示获取股票基本信息？")
    
    stock_codes = ['000001.SZ', '000002.SZ', '600000.SH']
    print(f"\n📊 将获取以下股票的基本信息：{stock_codes}")
    
    try:
        basic_info = get_stock_basic_info(stock_codes)
        print("\n📈 股票基本信息获取结果：")
        print("-" * 60)
        for code, info in basic_info.items():
            if info:
                name = info.get('name', '未知')
                price = info.get('current_price', 0)
                change = info.get('change_pct', 0)
                volume = info.get('volume', 0)
                print(f"  📌 {code}: {name}")
                print(f"     💰 当前价格: {price:.2f}元")
                print(f"     📊 涨跌幅: {change:+.2f}%")
                print(f"     📦 成交量: {volume:,}手")
                print()
            else:
                print(f"  ❌ {code}: 信息获取失败")
    except Exception as e:
        print(f"❌ 获取股票基本信息失败: {e}")
    
    wait_for_user_input("步骤1完成！您已学会获取股票基本信息。按回车键继续下一步...")
    
    # 步骤2: 计算技术指标
    print_section_header(2, "计算技术指标", "掌握常用技术指标的计算方法")
    print("📖 涉及知识：移动平均线、MACD、布林带、RSI等技术分析指标")
    wait_for_user_input("开始演示技术指标计算？")
    
    test_stock = '000001.SZ'
    print(f"\n📊 将计算 {test_stock} 的技术指标...")
    
    try:
        indicators = calculate_technical_indicators(test_stock)
        if indicators:
            print("\n📈 技术指标计算结果：")
            print("-" * 60)
            for name, values in indicators.items():
                if hasattr(values, 'iloc') and len(values) > 0:
                    latest_value = values.iloc[-1]
                    if not pd.isna(latest_value):
                        print(f"  📊 {name}: {latest_value:.4f}")
                    else:
                        print(f"  ⚠️ {name}: 数据不足")
            
            print("\n💡 技术指标说明：")
            print("  • MA5/MA10/MA20: 5日/10日/20日移动平均线")
            print("  • MACD: 指数平滑异同移动平均线")
            print("  • Upper_Band/Lower_Band: 布林带上轨/下轨")
            print("  • RSI: 相对强弱指数（0-100，30以下超卖，70以上超买）")
        else:
            print("❌ 技术指标计算失败")
    except Exception as e:
        print(f"❌ 技术指标计算出错: {e}")
    
    wait_for_user_input("步骤2完成！您已学会计算技术指标。按回车键继续下一步...")
    
    # 步骤3: 策略类演示
    print_section_header(3, "策略类演示", "了解不同类型的量化策略")
    print("📖 涉及知识：双均线策略、RSI策略、网格策略的原理和实现")
    wait_for_user_input("开始演示策略类创建？")
    
    demo_account_id = "demo_account"
    stock_pool = ['000001.SZ', '000002.SZ']
    
    try:
        # 3.1 双均线策略
        print_subsection("3.1 创建双均线策略")
        print("📚 策略原理：短期均线上穿长期均线时买入（金叉），下穿时卖出（死叉）")
        print("🎯 适用场景：趋势性行情，能够捕捉中长期趋势")
        
        ma_strategy = MovingAverageStrategy(demo_account_id, stock_pool, short_period=5, long_period=20)
        print(f"✅ 双均线策略创建成功")
        print(f"   📊 股票池: {ma_strategy.stock_pool}")
        print(f"   ⏱️ 短期周期: {ma_strategy.short_period}天")
        print(f"   ⏱️ 长期周期: {ma_strategy.long_period}天")
        
        wait_for_user_input("继续演示RSI策略？")
        
        # 3.2 RSI策略
        print_subsection("3.2 创建RSI策略")
        print("📚 策略原理：RSI低于30时买入（超卖），高于70时卖出（超买）")
        print("🎯 适用场景：震荡行情，利用超买超卖现象进行反转交易")
        
        rsi_strategy = RSIStrategy(demo_account_id, stock_pool, rsi_period=14, oversold=30, overbought=70)
        print(f"✅ RSI策略创建成功")
        print(f"   ⏱️ RSI周期: {rsi_strategy.rsi_period}天")
        print(f"   📉 超卖阈值: {rsi_strategy.oversold}")
        print(f"   📈 超买阈值: {rsi_strategy.overbought}")
        
        wait_for_user_input("继续演示网格策略？")
        
        # 3.3 网格策略
        print_subsection("3.3 创建网格策略")
        print("📚 策略原理：在基准价格上下设置多个买卖网格，低买高卖")
        print("🎯 适用场景：震荡行情，通过频繁交易获取价差收益")
        
        grid_strategy = GridStrategy(demo_account_id, '000001.SZ', base_price=10.0, grid_size=0.02, grid_num=10)
        grid_strategy.setup_grid()
        print(f"✅ 网格策略创建成功")
        print(f"   💰 基准价格: {grid_strategy.base_price}元")
        print(f"   📏 网格间距: {grid_strategy.grid_size*100}%")
        print(f"   🔢 网格数量: {grid_strategy.grid_num}个")
        print(f"   📊 网格价位: {grid_strategy.grid_levels[:5]}...{grid_strategy.grid_levels[-5:]}")
        
    except Exception as e:
        print(f"❌ 策略创建出错: {e}")
    
    wait_for_user_input("步骤3完成！您已学会创建不同类型的策略。按回车键继续下一步...")
    
    # 步骤4: 风险管理演示
    print_section_header(4, "风险管理演示", "掌握量化交易中的风险控制方法")
    print("📖 涉及知识：仓位管理、止损机制、交易频率控制")
    wait_for_user_input("开始演示风险管理？")
    
    try:
        risk_manager = RiskManager(max_position_ratio=0.1, max_loss_ratio=0.02, max_daily_trades=10)
        print("\n🛡️ 风险管理器配置：")
        print("-" * 50)
        print(f"  📊 最大单股仓位比例: {risk_manager.max_position_ratio:.1%}")
        print(f"  🚨 最大亏损比例: {risk_manager.max_loss_ratio:.1%}")
        print(f"  🔄 每日最大交易次数: {risk_manager.max_daily_trades}")
        
        # 模拟仓位检查
        print_subsection("仓位检查演示")
        demo_account = {'total_asset': 100000}
        print(f"📈 模拟账户总资产: {demo_account['total_asset']:,}元")
        print(f"📋 计划买入: 000001.SZ, 1000股, 10.0元/股")
        print(f"💰 买入金额: {1000 * 10.0:,}元")
        print(f"📊 仓位占比: {(1000 * 10.0 / demo_account['total_asset']):.1%}")
        
        demo_check = risk_manager.check_position_limit(demo_account, "000001.SZ", 1000, 10.0)
        print(f"🔍 仓位检查结果: {'✅ 通过' if demo_check else '❌ 不通过'}")
        
        # 模拟止损检查
        print_subsection("止损检查演示")
        position_info = {'stock_code': '000001.SZ', 'avg_price': 10.0}
        current_price = 9.5
        loss_pct = ((position_info['avg_price'] - current_price) / position_info['avg_price'] * 100)
        
        print(f"📈 持仓成本: {position_info['avg_price']}元")
        print(f"💰 当前价格: {current_price}元")
        print(f"📉 浮动亏损: {loss_pct:.2f}%")
        print(f"🚨 止损线: {risk_manager.max_loss_ratio:.1%}")
        
        stop_loss_triggered = risk_manager.check_stop_loss(position_info, current_price)
        print(f"🔍 止损检查结果: {'🚨 触发止损' if stop_loss_triggered else '✅ 正常'}")
        
        print("\n💡 风险管理要点：")
        print("  • 严格控制单股仓位，避免过度集中")
        print("  • 设置止损线，及时止损保护资金")
        print("  • 限制交易频率，避免过度交易")
        print("  • 定期评估策略表现，及时调整")
        
    except Exception as e:
        print(f"❌ 风险管理演示出错: {e}")
    
    wait_for_user_input("步骤4完成！您已学会风险管理方法。按回车键继续下一步...")
    
    # 步骤5: 回测引擎演示
    print_section_header(5, "回测引擎演示", "了解策略回测的基本原理和方法")
    print("📖 涉及知识：历史数据回测、策略性能评估、回测指标分析")
    wait_for_user_input("开始演示回测引擎？")
    
    try:
        strategy_params = {
            'account_id': demo_account_id,
            'stock_pool': stock_pool,
            'short_period': 5,
            'long_period': 20
        }
        
        backtest_engine = BacktestEngine(
            strategy_class=MovingAverageStrategy,
            strategy_params=strategy_params,
            start_date='20240101',
            end_date='20241201',
            initial_capital=100000
        )
        
        print("\n📊 回测引擎配置：")
        print("-" * 50)
        print(f"  🎯 策略类型: 双均线策略")
        print(f"  📅 回测期间: {backtest_engine.start_date} 到 {backtest_engine.end_date}")
        print(f"  💰 初始资金: {backtest_engine.initial_capital:,}元")
        print(f"  📈 股票池: {strategy_params['stock_pool']}")
        print(f"  ⏱️ 短期均线: {strategy_params['short_period']}天")
        print(f"  ⏱️ 长期均线: {strategy_params['long_period']}天")
        
        print_subsection("模拟回测结果")
        print("💡 注意: 以下为模拟数据，实际回测需要连接真实数据源")
        
        # 模拟回测结果
        results = {
            'total_return': 15.2,
            'annual_return': 12.8,
            'max_drawdown': 8.5,
            'sharpe_ratio': 1.25,
            'win_rate': 65.3
        }
        
        print(f"  📈 总收益率: {results['total_return']:+.1f}%")
        print(f"  📊 年化收益率: {results['annual_return']:+.1f}%")
        print(f"  📉 最大回撤: {results['max_drawdown']:.1f}%")
        print(f"  📏 夏普比率: {results['sharpe_ratio']:.2f}")
        print(f"  🎯 胜率: {results['win_rate']:.1f}%")
        
        print("\n💡 回测指标说明：")
        print("  • 总收益率: 策略在回测期间的总收益")
        print("  • 年化收益率: 按年计算的平均收益率")
        print("  • 最大回撤: 策略运行期间的最大亏损幅度")
        print("  • 夏普比率: 风险调整后的收益率（>1为优秀）")
        print("  • 胜率: 盈利交易占总交易次数的比例")
        
    except Exception as e:
        print(f"❌ 回测引擎演示出错: {e}")
    
    wait_for_user_input("步骤5完成！您已学会回测分析方法。按回车键继续...")
    
    # 步骤6: 高级功能演示
    print_section_header(6, "高级功能演示", "了解实际交易中的高级功能")
    print("📖 涉及知识：实时监控、策略组合、参数优化")
    wait_for_user_input("开始演示高级功能？")
    
    print_subsection("6.1 实时监控功能")
    print("🔍 功能描述：实时获取股票价格，监控市场变化")
    print("🎯 应用场景：策略信号确认、风险监控、异常检测")
    print("💡 实现方式：定时获取行情数据，计算技术指标，判断交易信号")
    
    print_subsection("6.2 策略组合功能")
    print("📊 功能描述：同时运行多个策略，分散风险")
    print("🎯 应用场景：双均线+RSI组合，提高信号准确性")
    print("💡 实现方式：多策略并行运行，信号综合判断")
    
    print_subsection("6.3 参数优化功能")
    print("⚙️ 功能描述：通过历史数据优化策略参数")
    print("🎯 应用场景：寻找最佳均线周期、RSI阈值等")
    print("💡 实现方式：网格搜索、遗传算法等优化方法")
    
    print_subsection("6.4 实盘交易接口")
    print("🔄 功能描述：连接真实交易系统，执行买卖操作")
    print("🎯 应用场景：策略信号转化为实际交易")
    print("💡 实现方式：通过EasyXT接口连接迅投客户端")
    
    wait_for_user_input("高级功能介绍完成！按回车键查看学习总结...")
    
    # 学习总结
    print("\n" + "=" * 70)
    print("🎓 学习总结")
    print("=" * 70)
    print("🎉 恭喜您完成了量化策略开发的完整学习！")
    
    print("\n📚 您已经掌握了：")
    print("  1. ✅ 获取股票基本信息和实时数据")
    print("  2. ✅ 计算常用技术指标（MA、MACD、RSI等）")
    print("  3. ✅ 创建不同类型的交易策略")
    print("  4. ✅ 实施风险管理和控制措施")
    print("  5. ✅ 使用回测引擎验证策略效果")
    print("  6. ✅ 了解高级功能和实际应用")
    
    print("\n🎯 EasyXT框架优势：")
    print("  • 🔧 统一的API接口，简化开发流程")
    print("  • 🛡️ 完善的错误处理和日志记录")
    print("  • 🏗️ 模块化设计，易于扩展和维护")
    print("  • 📊 多种策略类型，满足不同需求")
    print("  • 🔒 集成风险管理，保障交易安全")
    
    print("\n⚠️ 实盘交易重要提醒：")
    print("  1. 🔑 需要真实的交易账户ID和userdata_path配置")
    print("  2. 💻 必须启动迅投客户端并登录")
    print("  3. 🧪 建议先在模拟环境中充分测试")
    print("  4. ✅ 确保策略逻辑正确且风险可控")
    print("  5. 📊 定期监控策略表现并及时调整")
    
    print("\n🚀 进阶学习建议：")
    print("  • 📈 尝试修改策略参数，观察效果变化")
    print("  • 🔄 结合多个策略，构建策略组合")
    print("  • 📊 使用真实历史数据进行回测验证")
    print("  • 🧪 在模拟环境中测试完整交易流程")
    print("  • 📚 学习更多高级策略和风险管理技巧")
    
    print("\n💡 学习资源推荐：")
    print("  • 📖 查看其他学习实例文件")
    print("  • 🔍 研究EasyXT API文档")
    print("  • 📊 学习更多技术分析指标")
    print("  • 🎯 关注量化交易最新发展")
    
    wait_for_user_input("🎓 学习完成！感谢您的参与！按回车键退出...")
    
    print("\n" + "=" * 70)
    print("🎉 感谢您完成量化策略开发学习！")
    print("💪 现在您已经具备了开发量化交易策略的基础能力")
    print("🚀 祝您在量化交易的道路上取得成功！")
    print("=" * 70)

if __name__ == "__main__":
    # 运行交互式演示
    interactive_demo()