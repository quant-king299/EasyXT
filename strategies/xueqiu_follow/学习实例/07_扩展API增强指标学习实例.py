#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EasyXT扩展API增强指标学习实例 - 完整版
系统性介绍扩展API的各种功能，包括数据获取、技术指标计算、真实数据处理等
每个课程需要回车确认继续
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import time
import sqlite3
warnings.filterwarnings('ignore')

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def print_status(message, status="info"):
    """打印状态信息"""
    if status == "success":
        print(f"✅ {message}")
    elif status == "error":
        print(f"❌ {message}")
    elif status == "warning":
        print(f"⚠️ {message}")
    else:
        print(f"ℹ️ {message}")

def print_separator(title="", length=60):
    """打印分隔线"""
    if title:
        print(f"\n{'='*length}")
        print(f"{title}")
        print(f"{'='*length}")
    else:
        print("="*length)

def wait_for_continue(lesson_name=""):
    """等待用户按回车继续"""
    if lesson_name:
        input(f"\n📚 {lesson_name} 学习完成，按回车键继续下一课程...")
    else:
        input(f"\n按回车键继续...")
    print()

def print_course_header(course_num, course_name, description=""):
    """打印课程标题"""
    print_separator()
    print(f"第{course_num}课：{course_name}")
    if description:
        print(f"📖 {description}")
    print_separator()

try:
    # 导入xtquant
    print_status("正在导入xtquant模块...")
    import xtquant.xtdata as xt
    print_status("xtquant.xtdata 导入成功", "success")
    
    import xtquant.xttrader as trader
    print_status("xtquant.xttrader 导入成功", "success")
    
except ImportError as e:
    print_status(f"导入xtquant失败: {e}", "error")
    print("请确保已正确安装xtquant")
    sys.exit(1)

try:
    from easy_xt.extended_api import ExtendedAPI
    print_status("ExtendedAPI 导入成功", "success")
except ImportError as e:
    print_status(f"导入ExtendedAPI失败: {e}", "error")
    sys.exit(1)

print_separator("EasyXT扩展API增强指标学习实例 - 完整版")
print("🎯 本课程将系统性介绍扩展API的各种功能")
print("📚 包括：数据获取、质量检查、技术指标计算、真实数据处理等")
print("⏰ 每个课程学习完成后需要按回车键继续")
print_separator()

# ================================
# 数据获取和处理类
# ================================

class DataManager:
    """数据管理器 - 负责数据获取、清理和质量检查"""
    
    def __init__(self):
        self.cache = {}
        self.quality_threshold = 0.8  # 数据质量阈值
    
    def get_clean_data(self, stock_code, period='1d', count=100, show_details=True):
        """获取清洁的高质量数据"""
        try:
            if show_details:
                print(f"  🔍 正在获取{stock_code}的{period}数据...")
            
            # 方法1: 使用get_market_data_ex
            data = xt.get_market_data_ex(
                stock_list=[stock_code],
                period=period,
                count=count,
                dividend_type='front_ratio',  # 前复权真实数据
                fill_data=True
            )
            
            if stock_code not in data or len(data[stock_code]) == 0:
                if show_details:
                    print(f"  ❌ 无法获取{stock_code}数据")
                return None
            
            df = data[stock_code].copy()
            
            # 数据质量检查
            valid_close = df['close'].notna().sum()
            quality_ratio = valid_close / len(df)
            
            if quality_ratio < self.quality_threshold:
                if show_details:
                    print(f"  ⚠️ 数据质量不佳，有效数据: {valid_close}/{len(df)} ({quality_ratio:.1%})")
                return None
            
            # 数据清理
            df = self._clean_dataframe(df, show_details)
            
            if df is not None and len(df) > 0:
                if show_details:
                    print(f"  ✅ 成功获取{len(df)}条高质量数据 (质量: {quality_ratio:.1%})")
                return df
            else:
                if show_details:
                    print(f"  ❌ 数据清理后为空")
                return None
                
        except Exception as e:
            if show_details:
                print(f"  ❌ 获取数据失败: {e}")
            return None
    
    def _clean_dataframe(self, df, show_details=False):
        """清理DataFrame数据"""
        try:
            if df is None or len(df) == 0:
                return None
            
            original_len = len(df)
            
            # 1. 处理时间索引
            if 'time' in df.columns:
                try:
                    time_col = df['time']
                    sample_time = str(time_col.iloc[0])
                    
                    if len(sample_time) == 13 and sample_time.isdigit():
                        df.index = pd.to_datetime(time_col, unit='ms')
                    elif len(sample_time) == 10 and sample_time.isdigit():
                        df.index = pd.to_datetime(time_col, unit='s')
                    elif len(sample_time) == 8 and sample_time.isdigit():
                        df.index = pd.to_datetime(time_col, format='%Y%m%d')
                    else:
                        df.index = pd.to_datetime(time_col)
                    
                    df = df.drop('time', axis=1)
                except:
                    pass  # 时间转换失败不影响数据使用
            
            # 2. 移除无效价格数据
            if 'close' in df.columns:
                valid_mask = (df['close'] > 0) & df['close'].notna()
                df = df[valid_mask]
            
            # 3. 填充NaN值
            price_cols = ['open', 'high', 'low', 'close', 'preClose']
            for col in price_cols:
                if col in df.columns:
                    df[col] = df[col].fillna(method='ffill').fillna(method='bfill')
            
            # 4. 处理成交量
            if 'volume' in df.columns:
                df['volume'] = df['volume'].fillna(0)
                df.loc[df['volume'] < 0, 'volume'] = 0
            
            if 'amount' in df.columns:
                df['amount'] = df['amount'].fillna(0)
                df.loc[df['amount'] < 0, 'amount'] = 0
            
            # 5. 修复OHLC逻辑
            if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
                for idx in df.index:
                    row = df.loc[idx]
                    if all(pd.notna(row[col]) for col in ['open', 'high', 'low', 'close']):
                        prices = [row['open'], row['close']]
                        df.loc[idx, 'high'] = max(row['high'], max(prices))
                        df.loc[idx, 'low'] = min(row['low'], min(prices))
            
            final_len = len(df)
            if show_details and final_len < original_len:
                print(f"    数据清理: {original_len}→{final_len}条")
            
            return df if final_len > 0 else None
            
        except Exception as e:
            if show_details:
                print(f"    数据清理失败: {e}")
            return df
    
    def check_data_quality(self, stock_codes, periods=['1d']):
        """检查数据质量"""
        print("🔍 开始数据质量检查...")
        
        quality_report = {}
        
        for period in periods:
            print(f"\n📊 检查{period}周期数据:")
            period_report = {}
            
            for stock_code in stock_codes:
                print(f"  检查 {stock_code}...")
                
                df = self.get_clean_data(stock_code, period, count=50, show_details=False)
                
                if df is not None:
                    # 计算质量评分
                    score = self._calculate_quality_score(df)
                    period_report[stock_code] = {
                        'status': 'success',
                        'data_count': len(df),
                        'quality_score': score,
                        'latest_price': df['close'].iloc[-1] if len(df) > 0 else 0
                    }
                    print(f"    ✅ 质量评分: {score:.1f}/10.0, 数据量: {len(df)}条")
                else:
                    period_report[stock_code] = {
                        'status': 'failed',
                        'data_count': 0,
                        'quality_score': 0,
                        'latest_price': 0
                    }
                    print(f"    ❌ 数据获取失败")
            
            quality_report[period] = period_report
        
        return quality_report
    
    def _calculate_quality_score(self, df):
        """计算数据质量评分"""
        score = 10.0
        
        if len(df) == 0:
            return 0
        
        # 检查NaN值比例
        nan_ratio = df.isnull().sum().sum() / (len(df) * len(df.columns))
        score -= nan_ratio * 5  # NaN值扣分
        
        # 检查零成交量比例
        if 'volume' in df.columns:
            zero_volume_ratio = (df['volume'] == 0).sum() / len(df)
            if zero_volume_ratio > 0.5:  # 超过50%零成交量
                score -= 2
        
        # 检查价格连续性
        if 'close' in df.columns and len(df) > 1:
            price_changes = df['close'].pct_change().abs()
            extreme_changes = (price_changes > 0.2).sum()  # 超过20%变化
            if extreme_changes > len(df) * 0.1:  # 超过10%的数据有极端变化
                score -= 1
        
        return max(0, score)

# ================================
# 技术指标计算类
# ================================

class TechnicalIndicators:
    """技术指标计算器"""
    
    @staticmethod
    def calculate_macd(df, fast=12, slow=26, signal=9):
        """计算MACD指标"""
        try:
            if len(df) < slow + signal:
                return None
            
            close = df['close']
            
            # 计算EMA
            ema_fast = close.ewm(span=fast).mean()
            ema_slow = close.ewm(span=slow).mean()
            
            # MACD线
            macd_line = ema_fast - ema_slow
            
            # 信号线
            signal_line = macd_line.ewm(span=signal).mean()
            
            # 柱状图
            histogram = macd_line - signal_line
            
            # 最新值
            latest_macd = macd_line.iloc[-1]
            latest_signal = signal_line.iloc[-1]
            latest_hist = histogram.iloc[-1]
            
            # 趋势判断
            if len(macd_line) > 1:
                macd_trend = "上升" if latest_macd > macd_line.iloc[-2] else "下降"
            else:
                macd_trend = "中性"
            
            # 金叉死叉判断
            if len(macd_line) > 1:
                prev_diff = macd_line.iloc[-2] - signal_line.iloc[-2]
                curr_diff = latest_macd - latest_signal
                
                if prev_diff <= 0 and curr_diff > 0:
                    cross_signal = "金叉"  # 金叉
                elif prev_diff >= 0 and curr_diff < 0:
                    cross_signal = "死叉"   # 死叉
                else:
                    cross_signal = "无"
            else:
                cross_signal = "无"
            
            return {
                'macd': latest_macd,
                'signal': latest_signal,
                'histogram': latest_hist,
                'trend': macd_trend,
                'cross': cross_signal,
                'buy_signal': cross_signal == "金叉",
                'sell_signal': cross_signal == "死叉"
            }
            
        except Exception as e:
            print(f"    MACD计算失败: {e}")
            return None
    
    @staticmethod
    def calculate_kdj(df, n=9, m1=3, m2=3):
        """计算KDJ指标"""
        try:
            if len(df) < n:
                return None
            
            high = df['high']
            low = df['low']
            close = df['close']
            
            # 计算RSV
            lowest_low = low.rolling(window=n).min()
            highest_high = high.rolling(window=n).max()
            
            rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
            rsv = rsv.fillna(50)  # 填充NaN为50
            
            # 计算K、D、J
            k_values = []
            d_values = []
            
            k_prev = 50  # 初始K值
            d_prev = 50  # 初始D值
            
            for rsv_val in rsv:
                if pd.notna(rsv_val):
                    k_curr = (2/3) * k_prev + (1/3) * rsv_val
                    d_curr = (2/3) * d_prev + (1/3) * k_curr
                    
                    k_values.append(k_curr)
                    d_values.append(d_curr)
                    
                    k_prev = k_curr
                    d_prev = d_curr
                else:
                    k_values.append(k_prev)
                    d_values.append(d_prev)
            
            k_series = pd.Series(k_values, index=df.index)
            d_series = pd.Series(d_values, index=df.index)
            j_series = 3 * k_series - 2 * d_series
            
            # 最新值
            latest_k = k_series.iloc[-1]
            latest_d = d_series.iloc[-1]
            latest_j = j_series.iloc[-1]
            
            # 趋势判断
            if len(k_series) > 1:
                k_trend = "上升" if latest_k > k_series.iloc[-2] else "下降"
                d_trend = "上升" if latest_d > d_series.iloc[-2] else "下降"
            else:
                k_trend = d_trend = "中性"
            
            # 信号判断
            if latest_k > 80 and latest_d > 80:
                signal = "超买"
                buy_signal = False
                sell_signal = True
            elif latest_k < 20 and latest_d < 20:
                signal = "超卖"
                buy_signal = True
                sell_signal = False
            else:
                signal = "正常"
                buy_signal = False
                sell_signal = False
            
            return {
                'k': latest_k,
                'd': latest_d,
                'j': latest_j,
                'k_trend': k_trend,
                'd_trend': d_trend,
                'signal': signal,
                'buy_signal': buy_signal,
                'sell_signal': sell_signal
            }
            
        except Exception as e:
            print(f"    KDJ计算失败: {e}")
            return None
    
    @staticmethod
    def calculate_rsi(df, period=14):
        """计算RSI指标"""
        try:
            if len(df) < period + 1:
                return None
            
            close = df['close']
            delta = close.diff()
            
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            latest_rsi = rsi.iloc[-1]
            
            # 趋势判断
            if len(rsi) > 1:
                rsi_trend = "上升" if latest_rsi > rsi.iloc[-2] else "下降"
            else:
                rsi_trend = "中性"
            
            # 信号判断
            if latest_rsi > 70:
                signal = "超买"
                overbought = True
                oversold = False
                buy_signal = False
                sell_signal = True
            elif latest_rsi < 30:
                signal = "超卖"
                overbought = False
                oversold = True
                buy_signal = True
                sell_signal = False
            else:
                signal = "正常"
                overbought = False
                oversold = False
                buy_signal = False
                sell_signal = False
            
            # 背离检测（简化版）
            divergence = False
            if len(rsi) > 10 and len(close) > 10:
                recent_price_trend = close.iloc[-5:].is_monotonic_increasing
                recent_rsi_trend = rsi.iloc[-5:].is_monotonic_increasing
                divergence = recent_price_trend != recent_rsi_trend
            
            return {
                'rsi': latest_rsi,
                'trend': rsi_trend,
                'signal': signal,
                'overbought': overbought,
                'oversold': oversold,
                'divergence': divergence,
                'buy_signal': buy_signal,
                'sell_signal': sell_signal
            }
            
        except Exception as e:
            print(f"    RSI计算失败: {e}")
            return None
    
    @staticmethod
    def calculate_bollinger_bands(df, period=20, std_dev=2):
        """计算布林带指标"""
        try:
            if len(df) < period:
                return None
            
            close = df['close']
            
            # 中轨（移动平均线）
            middle_band = close.rolling(window=period).mean()
            
            # 标准差
            std = close.rolling(window=period).std()
            
            # 上轨和下轨
            upper_band = middle_band + (std * std_dev)
            lower_band = middle_band - (std * std_dev)
            
            # 最新值
            latest_close = close.iloc[-1]
            latest_upper = upper_band.iloc[-1]
            latest_middle = middle_band.iloc[-1]
            latest_lower = lower_band.iloc[-1]
            
            # 带宽
            bandwidth = ((latest_upper - latest_lower) / latest_middle) * 100
            
            # %B指标
            percent_b = (latest_close - latest_lower) / (latest_upper - latest_lower)
            
            # 位置判断
            if latest_close > latest_upper:
                position = "上轨上方"
                buy_signal = False
                sell_signal = True
            elif latest_close < latest_lower:
                position = "下轨下方"
                buy_signal = True
                sell_signal = False
            elif latest_close > latest_middle:
                position = "上半区"
                buy_signal = False
                sell_signal = False
            else:
                position = "下半区"
                buy_signal = False
                sell_signal = False
            
            # 信号判断
            if latest_close > latest_upper:
                signal = "卖出"
            elif latest_close < latest_lower:
                signal = "买入"
            else:
                signal = "持有"
            
            return {
                'upper': latest_upper,
                'middle': latest_middle,
                'lower': latest_lower,
                'current_price': latest_close,
                'bandwidth': bandwidth,
                'percent_b': percent_b,
                'position': position,
                'signal': signal,
                'buy_signal': buy_signal,
                'sell_signal': sell_signal
            }
            
        except Exception as e:
            print(f"    布林带计算失败: {e}")
            return None

# ================================
# 综合分析类
# ================================

class ComprehensiveAnalyzer:
    """综合分析器"""
    
    def __init__(self):
        self.data_manager = DataManager()
        self.indicators = TechnicalIndicators()
    
    def analyze_stock(self, stock_code, period='1d', count=60):
        """综合分析单只股票"""
        print(f"📊 开始分析 {stock_code}...")
        
        # 获取数据
        df = self.data_manager.get_clean_data(stock_code, period, count)
        if df is None:
            print(f"  ❌ 无法获取{stock_code}的数据")
            return None
        
        # 计算各项指标
        macd_result = self.indicators.calculate_macd(df)
        kdj_result = self.indicators.calculate_kdj(df)
        rsi_result = self.indicators.calculate_rsi(df)
        boll_result = self.indicators.calculate_bollinger_bands(df)
        
        # 综合信号分析
        buy_signals = 0
        sell_signals = 0
        
        if macd_result and macd_result['buy_signal']:
            buy_signals += 2  # MACD权重较高
        if macd_result and macd_result['sell_signal']:
            sell_signals += 2
        
        if kdj_result and kdj_result['buy_signal']:
            buy_signals += 1
        if kdj_result and kdj_result['sell_signal']:
            sell_signals += 1
        
        if rsi_result and rsi_result['buy_signal']:
            buy_signals += 1
        if rsi_result and rsi_result['sell_signal']:
            sell_signals += 1
        
        if boll_result and boll_result['buy_signal']:
            buy_signals += 1
        if boll_result and boll_result['sell_signal']:
            sell_signals += 1
        
        # 综合判断
        signal_strength = buy_signals - sell_signals
        
        if signal_strength >= 3:
            final_signal = "强烈买入"
            signal_emoji = "🟢"
        elif signal_strength >= 1:
            final_signal = "买入"
            signal_emoji = "🟢"
        elif signal_strength <= -3:
            final_signal = "强烈卖出"
            signal_emoji = "🔴"
        elif signal_strength <= -1:
            final_signal = "卖出"
            signal_emoji = "🔴"
        else:
            final_signal = "持有"
            signal_emoji = "⚪"
        
        return {
            'stock_code': stock_code,
            'data_length': len(df),
            'latest_price': df['close'].iloc[-1],
            'macd': macd_result,
            'kdj': kdj_result,
            'rsi': rsi_result,
            'bollinger': boll_result,
            'final_signal': final_signal,
            'signal_strength': signal_strength,
            'signal_emoji': signal_emoji,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals
        }

# ================================
# 数据库管理类
# ================================

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path="market_analysis.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建分析结果表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL,
                    analysis_date TEXT NOT NULL,
                    latest_price REAL,
                    macd_signal TEXT,
                    kdj_signal TEXT,
                    rsi_signal TEXT,
                    boll_signal TEXT,
                    final_signal TEXT,
                    signal_strength INTEGER,
                    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            print("✅ 数据库初始化完成")
            
        except Exception as e:
            print(f"❌ 数据库初始化失败: {e}")
    
    def save_analysis_result(self, result):
        """保存分析结果"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO analysis_results 
                (stock_code, analysis_date, latest_price, macd_signal, kdj_signal, 
                 rsi_signal, boll_signal, final_signal, signal_strength)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result['stock_code'],
                datetime.now().strftime('%Y-%m-%d'),
                result['latest_price'],
                result['macd']['signal'] if result['macd'] else None,
                result['kdj']['signal'] if result['kdj'] else None,
                result['rsi']['signal'] if result['rsi'] else None,
                result['bollinger']['signal'] if result['bollinger'] else None,
                result['final_signal'],
                result['signal_strength']
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"保存分析结果失败: {e}")
            return False

# ================================
# 主程序
# ================================

def main():
    """主程序"""
    
    # 初始化ExtendedAPI
    try:
        extended_api = ExtendedAPI()
        print_status("ExtendedAPI初始化成功", "success")
        print_status("数据服务连接成功", "success")
    except Exception as e:
        print_status(f"ExtendedAPI初始化失败: {e}", "error")
        return
    
    # 推荐的高质量股票（基于之前的数据质量检查）
    recommended_stocks = ['000001.SZ', '600000.SH', '000002.SZ']
    
    # 创建各种管理器
    data_manager = DataManager()
    analyzer = ComprehensiveAnalyzer()
    db_manager = DatabaseManager()
    
    # 第1课：数据质量检查
    print_course_header(1, "数据质量检查", "学习如何检查和评估数据质量")
    
    print("📋 本课程将教您:")
    print("  • 如何检查数据的完整性")
    print("  • 如何评估数据质量评分")
    print("  • 如何选择高质量的股票数据")
    print()
    
    quality_report = data_manager.check_data_quality(recommended_stocks, ['1d'])
    
    print("\n📊 数据质量报告总结:")
    for period, stocks in quality_report.items():
        print(f"\n{period}周期数据质量:")
        for stock_code, info in stocks.items():
            if info['status'] == 'success':
                print(f"  ✅ {stock_code}: 评分{info['quality_score']:.1f}/10.0, 最新价格{info['latest_price']:.2f}元")
            else:
                print(f"  ❌ {stock_code}: 数据获取失败")
    
    wait_for_continue("数据质量检查")
    
    # 第2课：MACD指标详解
    print_course_header(2, "MACD指标详解", "学习MACD指标的计算和应用")
    
    print("📋 本课程将教您:")
    print("  • MACD指标的计算原理")
    print("  • 金叉死叉信号的识别")
    print("  • MACD趋势分析方法")
    print()
    
    for i, stock_code in enumerate(recommended_stocks[:2]):
        print(f"\n📊 分析 {stock_code} 的MACD指标:")
        
        df = data_manager.get_clean_data(stock_code, period='1d', count=60)
        if df is not None:
            macd_result = TechnicalIndicators.calculate_macd(df)
            
            if macd_result:
                print(f"  📈 数据期间: {len(df)}个交易日")
                print(f"  📊 MACD线: {macd_result['macd']:.4f}")
                print(f"  📊 信号线: {macd_result['signal']:.4f}")
                print(f"  📊 柱状图: {macd_result['histogram']:.4f}")
                print(f"  📈 趋势方向: {macd_result['trend']}")
                print(f"  🎯 交叉信号: {macd_result['cross']}")
                
                if macd_result['cross'] == '金叉':
                    print(f"  🟢 出现金叉信号，可能是买入机会")
                elif macd_result['cross'] == '死叉':
                    print(f"  🔴 出现死叉信号，需要注意风险")
                else:
                    print(f"  ⚪ 暂无明显交叉信号")
                
                # 投资建议
                if macd_result['buy_signal']:
                    print(f"  💡 投资建议: 关注买入机会")
                elif macd_result['sell_signal']:
                    print(f"  💡 投资建议: 考虑减仓或止损")
                else:
                    print(f"  💡 投资建议: 继续观察，等待明确信号")
            else:
                print(f"  ❌ MACD计算失败，可能是数据不足")
        
        if i < len(recommended_stocks[:2]) - 1:
            print()
    
    wait_for_continue("MACD指标详解")
    
    # 第3课：KDJ指标详解
    print_course_header(3, "KDJ指标详解", "学习KDJ指标的超买超卖判断")
    
    print("📋 本课程将教您:")
    print("  • KDJ指标的K、D、J值含义")
    print("  • 超买超卖区域的判断")
    print("  • KDJ指标的买卖信号")
    print()
    
    for i, stock_code in enumerate(recommended_stocks[:2]):
        print(f"\n📊 分析 {stock_code} 的KDJ指标:")
        
        df = data_manager.get_clean_data(stock_code, period='1d', count=60)
        if df is not None:
            kdj_result = TechnicalIndicators.calculate_kdj(df)
            
            if kdj_result:
                print(f"  📈 K值: {kdj_result['k']:.2f} (趋势: {kdj_result['k_trend']})")
                print(f"  📈 D值: {kdj_result['d']:.2f} (趋势: {kdj_result['d_trend']})")
                print(f"  📈 J值: {kdj_result['j']:.2f}")
                print(f"  🎯 市场状态: {kdj_result['signal']}")
                
                if kdj_result['signal'] == '超买':
                    print(f"  🔴 当前处于超买区域，股价可能回调")
                    print(f"  💡 投资建议: 谨慎追高，可考虑减仓")
                elif kdj_result['signal'] == '超卖':
                    print(f"  🟢 当前处于超卖区域，可能出现反弹")
                    print(f"  💡 投资建议: 关注反弹机会，可适量建仓")
                else:
                    print(f"  ⚪ 当前处于正常区域")
                    print(f"  💡 投资建议: 结合其他指标综合判断")
            else:
                print(f"  ❌ KDJ计算失败")
        
        if i < len(recommended_stocks[:2]) - 1:
            print()
    
    wait_for_continue("KDJ指标详解")
    
    # 第4课：RSI指标详解
    print_course_header(4, "RSI指标详解", "学习RSI指标的强弱判断和背离分析")
    
    print("📋 本课程将教您:")
    print("  • RSI指标的强弱判断")
    print("  • 超买超卖的数值标准")
    print("  • 价格与RSI的背离分析")
    print()
    
    for stock_code in recommended_stocks[:1]:  # 详细分析一只
        print(f"\n📊 深度分析 {stock_code} 的RSI指标:")
        
        df = data_manager.get_clean_data(stock_code, period='1d', count=60)
        if df is not None:
            rsi_result = TechnicalIndicators.calculate_rsi(df)
            
            if rsi_result:
                print(f"  📈 RSI值: {rsi_result['rsi']:.2f}")
                print(f"  📈 趋势方向: {rsi_result['trend']}")
                print(f"  🎯 市场状态: {rsi_result['signal']}")
                print(f"  📊 超买状态: {'是' if rsi_result['overbought'] else '否'}")
                print(f"  📊 超卖状态: {'是' if rsi_result['oversold'] else '否'}")
                print(f"  🔍 背离检测: {'发现背离' if rsi_result['divergence'] else '无背离'}")
                
                # 详细解释
                if rsi_result['rsi'] > 70:
                    print(f"\n  📚 RSI解读:")
                    print(f"    RSI > 70，表明股票可能被过度买入")
                    print(f"    市场情绪过于乐观，存在回调风险")
                    print(f"  💡 操作建议: 谨慎追高，可考虑获利了结")
                elif rsi_result['rsi'] < 30:
                    print(f"\n  📚 RSI解读:")
                    print(f"    RSI < 30，表明股票可能被过度卖出")
                    print(f"    市场情绪过于悲观，可能出现反弹")
                    print(f"  💡 操作建议: 关注反弹机会，可适量建仓")
                else:
                    print(f"\n  📚 RSI解读:")
                    print(f"    RSI在30-70之间，属于正常波动区间")
                    print(f"    市场情绪相对平衡")
                    print(f"  💡 操作建议: 结合趋势和其他指标判断")
                
                if rsi_result['divergence']:
                    print(f"\n  ⚠️ 背离警告:")
                    print(f"    价格走势与RSI出现背离")
                    print(f"    这可能预示着趋势即将发生变化")
            else:
                print(f"  ❌ RSI计算失败")
    
    wait_for_continue("RSI指标详解")
    
    # 第5课：布林带指标详解
    print_course_header(5, "布林带指标详解", "学习布林带的通道分析和%B指标")
    
    print("📋 本课程将教您:")
    print("  • 布林带上中下轨的含义")
    print("  • %B指标的应用")
    print("  • 布林带的买卖信号")
    print()
    
    for stock_code in recommended_stocks[:1]:
        print(f"\n📊 分析 {stock_code} 的布林带指标:")
        
        df = data_manager.get_clean_data(stock_code, period='1d', count=60)
        if df is not None:
            boll_result = TechnicalIndicators.calculate_bollinger_bands(df)
            
            if boll_result:
                print(f"  📈 当前价格: {boll_result['current_price']:.2f}元")
                print(f"  📊 上轨价格: {boll_result['upper']:.2f}元")
                print(f"  📊 中轨价格: {boll_result['middle']:.2f}元")
                print(f"  📊 下轨价格: {boll_result['lower']:.2f}元")
                print(f"  📏 带宽: {boll_result['bandwidth']:.2f}%")
                print(f"  📍 %B指标: {boll_result['percent_b']:.2f}")
                print(f"  🎯 价格位置: {boll_result['position']}")
                print(f"  🎯 交易信号: {boll_result['signal']}")
                
                # 详细解释
                print(f"\n  📚 布林带解读:")
                if boll_result['position'] == '上轨上方':
                    print(f"    价格突破上轨，表明强势上涨")
                    print(f"    但也可能存在超买风险")
                    print(f"  💡 操作建议: 谨慎追高，注意回调风险")
                elif boll_result['position'] == '下轨下方':
                    print(f"    价格跌破下轨，表明弱势下跌")
                    print(f"    但也可能存在超卖机会")
                    print(f"  💡 操作建议: 关注反弹机会，可适量建仓")
                elif boll_result['position'] == '上半区':
                    print(f"    价格在中轨上方，趋势相对强势")
                    print(f"  💡 操作建议: 可持有观察，注意上轨压力")
                else:
                    print(f"    价格在中轨下方，趋势相对弱势")
                    print(f"  💡 操作建议: 谨慎操作，关注中轨支撑")
                
                # %B指标解释
                print(f"\n  📊 %B指标解读:")
                if boll_result['percent_b'] > 1:
                    print(f"    %B > 1，价格在上轨上方，可能超买")
                elif boll_result['percent_b'] < 0:
                    print(f"    %B < 0，价格在下轨下方，可能超卖")
                elif boll_result['percent_b'] > 0.8:
                    print(f"    %B > 0.8，接近上轨，注意阻力")
                elif boll_result['percent_b'] < 0.2:
                    print(f"    %B < 0.2，接近下轨，注意支撑")
                else:
                    print(f"    %B在正常范围内，价格波动相对平稳")
            else:
                print(f"  ❌ 布林带计算失败")
    
    wait_for_continue("布林带指标详解")
    
    # 第6课：综合技术分析
    print_course_header(6, "综合技术分析", "学习多指标综合判断和信号强度评估")
    
    print("📋 本课程将教您:")
    print("  • 如何综合多个技术指标")
    print("  • 信号强度的评估方法")
    print("  • 制定综合投资策略")
    print()
    
    print("🔍 开始综合分析推荐股票...")
    
    analysis_results = []
    
    for stock_code in recommended_stocks:
        result = analyzer.analyze_stock(stock_code)
        if result:
            analysis_results.append(result)
            
            print(f"\n📊 {stock_code} 综合分析报告:")
            print(f"  💰 最新价格: {result['latest_price']:.2f}元")
            print(f"  📊 数据期间: {result['data_length']}个交易日")
            
            print(f"\n  🔍 各指标信号:")
            if result['macd']:
                print(f"    MACD: {result['macd']['cross']} (趋势: {result['macd']['trend']})")
            if result['kdj']:
                print(f"    KDJ: {result['kdj']['signal']} (K: {result['kdj']['k']:.1f}, D: {result['kdj']['d']:.1f})")
            if result['rsi']:
                print(f"    RSI: {result['rsi']['signal']} (数值: {result['rsi']['rsi']:.1f})")
            if result['bollinger']:
                print(f"    布林带: {result['bollinger']['signal']} (位置: {result['bollinger']['position']})")
            
            print(f"\n  🎯 综合判断:")
            print(f"    最终信号: {result['signal_emoji']} {result['final_signal']}")
            print(f"    信号强度: {result['signal_strength']} (买入信号: {result['buy_signals']}, 卖出信号: {result['sell_signals']})")
            
            # 投资建议
            print(f"\n  💡 投资建议:")
            if result['final_signal'] in ['强烈买入', '买入']:
                print(f"    多个指标显示买入信号，可考虑建仓")
                print(f"    建议分批买入，设置止损位")
            elif result['final_signal'] in ['强烈卖出', '卖出']:
                print(f"    多个指标显示卖出信号，建议减仓")
                print(f"    如有持仓，考虑止损或获利了结")
            else:
                print(f"    信号不够明确，建议继续观察")
                print(f"    等待更明确的买卖信号出现")
            
            # 保存分析结果
            db_manager.save_analysis_result(result)
    
    wait_for_continue("综合技术分析")
    
    # 第7课：批量分析和投资组合
    print_course_header(7, "批量分析和投资组合", "学习批量分析多只股票并构建投资组合")
    
    print("📋 本课程将教您:")
    print("  • 批量分析多只股票的方法")
    print("  • 投资组合的构建原则")
    print("  • 风险分散和收益优化")
    print()
    
    if analysis_results:
        print("📊 投资组合分析报告:")
        print("=" * 60)
        
        # 按信号强度排序
        sorted_results = sorted(analysis_results, key=lambda x: x['signal_strength'], reverse=True)
        
        buy_candidates = []
        sell_candidates = []
        hold_candidates = []
        
        for result in sorted_results:
            print(f"\n{result['stock_code']} - {result['latest_price']:.2f}元")
            print(f"  信号: {result['signal_emoji']} {result['final_signal']} (强度: {result['signal_strength']})")
            
            if result['final_signal'] in ['强烈买入', '买入']:
                buy_candidates.append(result)
                print(f"  💡 推荐操作: 可考虑买入")
            elif result['final_signal'] in ['强烈卖出', '卖出']:
                sell_candidates.append(result)
                print(f"  💡 推荐操作: 建议卖出")
            else:
                hold_candidates.append(result)
                print(f"  💡 推荐操作: 继续观察")
        
        # 投资组合建议
        print(f"\n📋 投资组合建议:")
        print("=" * 40)
        
        if buy_candidates:
            print(f"\n🟢 买入候选 ({len(buy_candidates)}只):")
            for candidate in buy_candidates:
                print(f"  • {candidate['stock_code']}: {candidate['final_signal']} (强度: {candidate['signal_strength']})")
            
            print(f"\n💡 建仓建议:")
            print(f"  • 可将资金分配给信号强度最高的股票")
            print(f"  • 建议分批建仓，控制单只股票仓位不超过30%")
            print(f"  • 设置止损位，一般为买入价的5-10%")
        
        if sell_candidates:
            print(f"\n🔴 卖出候选 ({len(sell_candidates)}只):")
            for candidate in sell_candidates:
                print(f"  • {candidate['stock_code']}: {candidate['final_signal']} (强度: {candidate['signal_strength']})")
        
        if hold_candidates:
            print(f"\n⚪ 观察候选 ({len(hold_candidates)}只):")
            for candidate in hold_candidates:
                print(f"  • {candidate['stock_code']}: 信号不明确，继续观察")
        
        # 风险提示
        print(f"\n⚠️ 风险提示:")
        print(f"  • 技术分析仅供参考，不构成投资建议")
        print(f"  • 投资有风险，请根据自身情况谨慎决策")
        print(f"  • 建议结合基本面分析和市场环境综合判断")
        print(f"  • 严格执行止损策略，控制投资风险")
    
    wait_for_continue("批量分析和投资组合")
    
    # 第8课：数据管理和历史回顾
    print_course_header(8, "数据管理和历史回顾", "学习数据存储和历史分析回顾")
    
    print("📋 本课程将教您:")
    print("  • 如何存储分析结果")
    print("  • 历史数据的管理方法")
    print("  • 分析结果的回顾和总结")
    print()
    
    try:
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        # 查询今日分析结果
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT stock_code, latest_price, final_signal, signal_strength, created_time
            FROM analysis_results 
            WHERE analysis_date = ?
            ORDER BY signal_strength DESC
        ''', (today,))
        
        results = cursor.fetchall()
        conn.close()
        
        if results:
            print(f"📊 今日分析结果回顾 ({len(results)}条记录):")
            print("=" * 50)
            
            for result in results:
                stock_code, price, signal, strength, created_time = result
                print(f"{stock_code}: {price:.2f}元 - {signal} (强度: {strength}) [{created_time}]")
            
            print(f"\n💾 数据存储位置: {db_manager.db_path}")
            print(f"📈 可用于后续的历史分析和策略回测")
        else:
            print(f"📊 暂无今日分析记录")
        
    except Exception as e:
        print(f"❌ 数据库查询失败: {e}")
    
    wait_for_continue("数据管理和历史回顾")
    
    # 课程总结
    print_separator("课程总结")
    print("🎉 恭喜您完成了EasyXT扩展API增强指标学习课程！")
    print()
    print("📚 您已经学会了:")
    print("  ✅ 数据质量检查和评估")
    print("  ✅ MACD指标的计算和应用")
    print("  ✅ KDJ指标的超买超卖判断")
    print("  ✅ RSI指标的强弱分析")
    print("  ✅ 布林带指标的通道分析")
    print("  ✅ 多指标综合技术分析")
    print("  ✅ 批量分析和投资组合构建")
    print("  ✅ 数据管理和历史回顾")
    print()
    print("💡 实战应用建议:")
    print("  • 定期运行分析程序，跟踪市场变化")
    print("  • 结合基本面分析，提高投资成功率")
    print("  • 严格执行风险管理，设置止损止盈")
    print("  • 持续学习和优化分析策略")
    print()
    print("🔧 技术特色:")
    print("  • 使用真实市场数据，具有实际投资价值")
    print("  • 完善的数据质量检查和清理机制")
    print("  • 多指标综合分析，提高判断准确性")
    print("  • 数据持久化存储，支持历史回顾")
    print()
    print("⚠️ 重要提醒:")
    print("  本程序仅供学习和参考，不构成投资建议")
    print("  投资有风险，请根据自身情况谨慎决策")
    print()
    print("🎊 感谢您的学习，祝您投资顺利！")

if __name__ == "__main__":
    main()