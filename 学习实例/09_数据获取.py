# -*- coding: utf-8 -*-
"""
数据获取学习实例 - 改进版
本文件展示了xtquant数据获取的各种方法和技巧，并修复了常见问题
"""

import sys
import os

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

try:
    import xtquant.xtdata as xt
    print("✅ 成功导入xtquant.xtdata模块")
except ImportError as e:
    print(f"❌ 导入xtquant.xtdata失败: {e}")
    print("尝试其他导入方式...")
    
    try:
        # 尝试直接从xtquant目录导入
        xtquant_path = os.path.join(parent_dir, 'xtquant')
        if os.path.exists(xtquant_path):
            sys.path.insert(0, xtquant_path)
            import xtdata as xt
            print("✅ 成功从xtquant目录导入xtdata模块")
        else:
            raise ImportError("找不到xtquant目录")
    except ImportError:
        print("❌ 无法导入任何xtdata模块")
        print("请检查xtquant是否正确安装")
        print("当前搜索路径:")
        for path in sys.path:
            print(f"  - {path}")
        sys.exit(1)

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

print("=" * 60)
print("MiniQMT 数据获取学习实例 - 改进版")
print("=" * 60)

# ================================
# 工具函数
# ================================

def safe_format_time(timestamp):
    """安全地格式化时间戳"""
    try:
        if isinstance(timestamp, (int, float)):
            # 时间戳格式，转换为日期字符串
            return pd.to_datetime(timestamp, unit='ms').strftime('%Y-%m-%d')
        else:
            # 已经是日期格式
            return str(timestamp)[:10]
    except Exception:
        return str(timestamp)

def safe_calculate_days_diff(time1, time2):
    """安全地计算两个时间的天数差"""
    try:
        if isinstance(time1, (int, float)):
            # 时间戳格式
            date1 = pd.to_datetime(time1, unit='ms')
            date2 = pd.to_datetime(time2, unit='ms')
        else:
            # 日期格式
            date1 = pd.to_datetime(str(time1))
            date2 = pd.to_datetime(str(time2))
        
        return (date1 - date2).days
    except Exception:
        return 0

def is_trading_time():
    """检查当前是否为交易时间"""
    now = datetime.now()
    current_time = now.strftime('%H:%M')
    is_trading_day = now.weekday() < 5  # 周一到周五
    is_trading_time = (('09:30' <= current_time <= '11:30') or 
                      ('13:00' <= current_time <= '15:00'))
    return is_trading_day and is_trading_time, now

# ================================
# 1. 基础行情数据获取
# ================================

def get_basic_market_data():
    """获取基础行情数据"""
    print("\n1. 基础行情数据获取")
    print("-" * 40)
    
    # 定义股票代码
    stock_codes = ['000001.SZ', '600000.SH', '000002.SZ']
    
    try:
        # 获取最近30天的日线数据
        print("获取日线数据...")
        data = xt.get_market_data_ex(
            stock_list=stock_codes,
            period='1d',
            count=30
        )
        
        for stock_code in stock_codes:
            if stock_code in data:
                df = data[stock_code]
                print(f"\n{stock_code} 数据概览:")
                print(f"  数据条数: {len(df)}")
                print(f"  最新价格: {df['close'].iloc[-1]:.2f}")
                print(f"  最高价: {df['high'].max():.2f}")
                print(f"  最低价: {df['low'].min():.2f}")
                print(f"  平均成交量: {df['volume'].mean():.0f}")
            else:
                print(f"{stock_code}: 数据获取失败")
                
    except Exception as e:
        print(f"获取行情数据失败: {e}")

# ================================
# 2. 实时行情数据 - 改进版
# ================================

def get_realtime_data():
    """获取实时行情数据 - 改进版"""
    print("\n2. 实时行情数据获取")
    print("-" * 40)
    
    stock_codes = ['000001.SZ', '600000.SH', '000002.SZ']
    
    # 检查交易时间
    is_trading, now = is_trading_time()
    if not is_trading:
        print("  ⚠️  当前非交易时间，实时数据可能不可用")
        print(f"  当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print("  交易时间: 周一至周五 09:30-11:30, 13:00-15:00")
    
    try:
        print("获取实时tick数据...")
        tick_data = xt.get_full_tick(stock_codes)
        
        success_count = 0
        if tick_data and isinstance(tick_data, dict):
            for stock_code in stock_codes:
                if stock_code in tick_data and tick_data[stock_code]:
                    tick = tick_data[stock_code]
                    print(f"\n{stock_code} 实时数据:")
                    print(f"  最新价: {tick.get('lastPrice', 0):.2f}")
                    print(f"  涨跌幅: {tick.get('pctChg', 0):.2f}%")
                    print(f"  成交量: {tick.get('volume', 0):,}")
                    print(f"  成交额: {tick.get('amount', 0):,.0f}")
                    print(f"  买一价: {tick.get('bidPrice1', 0):.2f}")
                    print(f"  卖一价: {tick.get('askPrice1', 0):.2f}")
                    success_count += 1
                else:
                    print(f"{stock_code}: 实时数据获取失败")
        
        # 如果实时数据获取失败，尝试获取最新日线数据
        if success_count == 0:
            print("\n  实时数据不可用，获取最新日线数据作为参考...")
            latest_data = xt.get_market_data_ex(
                stock_list=stock_codes,
                period='1d',
                count=1
            )
            
            for stock_code in stock_codes:
                if stock_code in latest_data:
                    df = latest_data[stock_code]
                    if len(df) > 0:
                        latest = df.iloc[-1]
                        print(f"\n{stock_code} 最新日线数据:")
                        print(f"  收盘价: {latest['close']:.2f}")
                        print(f"  成交量: {latest['volume']:,.0f}")
                        print(f"  成交额: {latest['amount']:,.0f}")
                        print(f"  数据日期: {safe_format_time(df.index[-1])}")
                
    except Exception as e:
        print(f"获取实时数据失败: {e}")
        print("  可能的原因:")
        print("  1. 当前非交易时间")
        print("  2. 网络连接问题")
        print("  3. 数据服务权限限制")

# ================================
# 3. 多周期数据获取
# ================================

def get_multi_period_data():
    """获取多周期数据"""
    print("\n3. 多周期数据获取")
    print("-" * 40)
    
    stock_code = '000001.SZ'
    periods = ['1m', '5m', '15m', '30m', '1h', '1d']
    
    for period in periods:
        try:
            print(f"\n获取{period}周期数据...")
            data = xt.get_market_data_ex(
                stock_list=[stock_code],
                period=period,
                count=10  # 获取最近10条数据
            )
            
            if stock_code in data:
                df = data[stock_code]
                if len(df) > 0:
                    print(f"  {period}周期: 共{len(df)}条数据")
                    print(f"  最新价格: {df['close'].iloc[-1]:.2f}")
                    print(f"  时间范围: {df.index[0]} 到 {df.index[-1]}")
                else:
                    print(f"  {period}周期: 无数据")
            else:
                print(f"  {period}周期: 获取失败")
                
        except Exception as e:
            print(f"  {period}周期获取失败: {e}")

# ================================
# 4. 股票基本信息
# ================================

def get_stock_info():
    """获取股票基本信息"""
    print("\n4. 股票基本信息获取")
    print("-" * 40)
    
    stock_codes = ['000001.SZ', '600000.SH', '000002.SZ']
    
    for stock_code in stock_codes:
        try:
            print(f"\n{stock_code} 基本信息:")
            info = xt.get_instrument_detail(stock_code)
            
            if info:
                print(f"  股票名称: {info.get('InstrumentName', 'N/A')}")
                print(f"  交易所: {info.get('ExchangeID', 'N/A')}")
                print(f"  产品类别: {info.get('ProductClass', 'N/A')}")
                print(f"  最小变动价位: {info.get('PriceTick', 0)}")
                print(f"  合约乘数: {info.get('VolumeMultiple', 1)}")
                print(f"  上市日期: {info.get('OpenDate', 'N/A')}")
                print(f"  到期日期: {info.get('ExpireDate', 'N/A')}")
            else:
                print(f"  获取{stock_code}信息失败")
                
        except Exception as e:
            print(f"  获取{stock_code}信息失败: {e}")

# ================================
# 5. 板块和指数数据
# ================================

def get_sector_and_index_data():
    """获取板块和指数数据"""
    print("\n5. 板块和指数数据获取")
    print("-" * 40)
    
    try:
        # 获取主要指数数据
        index_codes = ['000001.SH', '399001.SZ', '399006.SZ']  # 上证指数、深证成指、创业板指
        
        print("获取主要指数数据...")
        index_data = xt.get_market_data_ex(
            stock_list=index_codes,
            period='1d',
            count=5
        )
        
        index_names = {
            '000001.SH': '上证指数',
            '399001.SZ': '深证成指', 
            '399006.SZ': '创业板指'
        }
        
        for index_code in index_codes:
            if index_code in index_data:
                df = index_data[index_code]
                if len(df) > 0:
                    latest_close = df['close'].iloc[-1]
                    prev_close = df['close'].iloc[-2] if len(df) > 1 else latest_close
                    change_pct = ((latest_close - prev_close) / prev_close) * 100
                    
                    print(f"  {index_names.get(index_code, index_code)}: {latest_close:.2f} ({change_pct:+.2f}%)")
                    
    except Exception as e:
        print(f"获取指数数据失败: {e}")

# ================================
# 6. 历史数据分析 - 改进版
# ================================

def analyze_historical_data():
    """分析历史数据 - 改进版"""
    print("\n6. 历史数据分析")
    print("-" * 40)
    
    stock_code = '000001.SZ'
    
    try:
        # 获取较长期的历史数据
        print(f"分析{stock_code}历史数据...")
        data = xt.get_market_data_ex(
            stock_list=[stock_code],
            period='1d',
            count=100  # 获取最近100天数据
        )
        
        if stock_code in data:
            df = data[stock_code]
            
            if len(df) > 0:
                # 基础统计 - 使用安全的时间格式化
                print(f"\n基础统计信息:")
                start_date = safe_format_time(df.index[0])
                end_date = safe_format_time(df.index[-1])
                print(f"  数据期间: {start_date} 到 {end_date}")
                print(f"  总交易日: {len(df)}天")
                
                # 价格统计
                closes = df['close']
                print(f"\n价格统计:")
                print(f"  当前价格: {closes.iloc[-1]:.2f}")
                print(f"  期间最高: {closes.max():.2f}")
                print(f"  期间最低: {closes.min():.2f}")
                print(f"  平均价格: {closes.mean():.2f}")
                print(f"  价格标准差: {closes.std():.2f}")
                
                # 涨跌统计
                daily_returns = closes.pct_change().dropna()
                up_days = (daily_returns > 0).sum()
                down_days = (daily_returns < 0).sum()
                
                print(f"\n涨跌统计:")
                print(f"  上涨天数: {up_days}天 ({up_days/len(daily_returns)*100:.1f}%)")
                print(f"  下跌天数: {down_days}天 ({down_days/len(daily_returns)*100:.1f}%)")
                print(f"  平均日收益率: {daily_returns.mean()*100:.2f}%")
                print(f"  收益率标准差: {daily_returns.std()*100:.2f}%")
                print(f"  最大单日涨幅: {daily_returns.max()*100:.2f}%")
                print(f"  最大单日跌幅: {daily_returns.min()*100:.2f}%")
                
                # 成交量统计
                volumes = df['volume']
                print(f"\n成交量统计:")
                print(f"  平均成交量: {volumes.mean():,.0f}")
                print(f"  最大成交量: {volumes.max():,.0f}")
                print(f"  最小成交量: {volumes.min():,.0f}")
                
                # 简单技术指标
                print(f"\n简单技术指标:")
                ma5 = closes.rolling(5).mean().iloc[-1]
                ma20 = closes.rolling(20).mean().iloc[-1]
                ma60 = closes.rolling(60).mean().iloc[-1] if len(closes) >= 60 else None
                
                print(f"  MA5: {ma5:.2f}")
                print(f"  MA20: {ma20:.2f}")
                if ma60:
                    print(f"  MA60: {ma60:.2f}")
                
                # 价格相对位置
                current_price = closes.iloc[-1]
                print(f"\n价格相对位置:")
                print(f"  相对MA5: {((current_price/ma5-1)*100):+.2f}%")
                print(f"  相对MA20: {((current_price/ma20-1)*100):+.2f}%")
                if ma60:
                    print(f"  相对MA60: {((current_price/ma60-1)*100):+.2f}%")
                        
            else:
                print(f"  {stock_code}无历史数据")
        else:
            print(f"  获取{stock_code}数据失败")
            
    except Exception as e:
        print(f"分析历史数据失败: {e}")

# ================================
# 7. 数据导出功能
# ================================

def export_data_example():
    """数据导出示例"""
    print("\n7. 数据导出示例")
    print("-" * 40)
    
    stock_codes = ['000001.SZ', '600000.SH']
    
    try:
        print("获取数据并导出...")
        data = xt.get_market_data_ex(
            stock_list=stock_codes,
            period='1d',
            count=30
        )
        
        for stock_code in stock_codes:
            if stock_code in data:
                df = data[stock_code]
                
                # 导出到CSV文件
                filename = f"{stock_code.replace('.', '_')}_data.csv"
                df.to_csv(filename, encoding='utf-8-sig')
                print(f"  {stock_code}数据已导出到: {filename}")
                
                # 显示数据预览
                print(f"  数据预览 (最近5天):")
                print(df.tail().to_string())
                print()
                
    except Exception as e:
        print(f"数据导出失败: {e}")

# ================================
# 8. 数据质量检查 - 改进版
# ================================

def check_data_quality():
    """检查数据质量 - 改进版"""
    print("\n8. 数据质量检查")
    print("-" * 40)
    
    stock_codes = ['000001.SZ', '600000.SH', '000002.SZ']
    
    for stock_code in stock_codes:
        try:
            print(f"\n检查{stock_code}数据质量:")
            
            data = xt.get_market_data_ex(
                stock_list=[stock_code],
                period='1d',
                count=50
            )
            
            if stock_code in data:
                df = data[stock_code]
                
                if len(df) > 0:
                    # 检查缺失值
                    missing_data = df.isnull().sum()
                    print(f"  缺失值检查:")
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        if col in missing_data:
                            print(f"    {col}: {missing_data[col]}个缺失值")
                    
                    # 检查异常值
                    print(f"  异常值检查:")
                    
                    # 检查价格逻辑
                    price_errors = 0
                    for i in range(len(df)):
                        row = df.iloc[i]
                        if row['high'] < row['low']:
                            price_errors += 1
                        if row['close'] > row['high'] or row['close'] < row['low']:
                            price_errors += 1
                        if row['open'] > row['high'] or row['open'] < row['low']:
                            price_errors += 1
                    
                    print(f"    价格逻辑错误: {price_errors}个")
                    
                    # 检查零值
                    zero_volumes = (df['volume'] == 0).sum()
                    zero_prices = (df['close'] == 0).sum()
                    
                    print(f"    零成交量: {zero_volumes}天")
                    print(f"    零价格: {zero_prices}天")
                    
                    # 数据连续性检查 - 使用安全的日期计算
                    date_gaps = 0
                    if len(df) > 1:
                        for i in range(1, len(df)):
                            days_diff = safe_calculate_days_diff(df.index[i], df.index[i-1])
                            if days_diff > 3:  # 超过3天的间隔可能是数据缺失
                                date_gaps += 1
                    
                    print(f"    日期间隔异常: {date_gaps}个")
                    
                    if price_errors == 0 and zero_prices == 0 and date_gaps == 0:
                        print(f"  ✅ 数据质量良好")
                    else:
                        print(f"  ⚠️  发现数据质量问题")
                        
                else:
                    print(f"  ❌ 无数据")
            else:
                print(f"  ❌ 数据获取失败")
                
        except Exception as e:
            print(f"  ❌ 检查失败: {e}")

# ================================
# 主函数
# ================================

def main():
    """主函数 - 运行所有数据获取示例"""
    
    print("开始运行数据获取学习实例...")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 基础行情数据
        get_basic_market_data()
        
        # 2. 实时数据
        get_realtime_data()
        
        # 3. 多周期数据
        get_multi_period_data()
        
        # 4. 股票信息
        get_stock_info()
        
        # 5. 板块和指数
        get_sector_and_index_data()
        
        # 6. 历史数据分析
        analyze_historical_data()
        
        # 7. 数据导出
        export_data_example()
        
        # 8. 数据质量检查
        check_data_quality()
        
        print("\n" + "=" * 60)
        print("✅ 数据获取学习实例运行完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 运行过程中出现错误: {e}")
        print("=" * 60)

if __name__ == "__main__":
    main()