#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EasyXT学习实例05: 数据周期详解
演示QMT支持的各种数据周期的使用方法
基于xtdata官方文档v2023-01-31
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from easy_xt import EasyXT
from easy_xt.data_api import get_supported_periods, validate_period

def show_supported_periods():
    """显示支持的数据周期"""
    print("=" * 60)
    print("QMT支持的数据周期类型")
    print("=" * 60)
    
    periods = get_supported_periods()
    
    # Level1数据周期
    level1_periods = ['tick', '1m', '5m', '15m', '30m', '1h', '1d']
    print("\n📊 Level1数据周期 (标准行情数据):")
    print("-" * 40)
    for period in level1_periods:
        if period in periods:
            print(f"  {period:6} - {periods[period]}")
    
    # Level2数据周期
    level2_periods = ['l2quote', 'l2order', 'l2transaction', 'l2quoteaux', 'l2orderqueue', 'l2thousand']
    print(f"\n📈 Level2数据周期 (需要Level2权限):")
    print("-" * 40)
    for period in level2_periods:
        if period in periods:
            print(f"  {period:14} - {periods[period]}")

def demo_daily_data():
    """演示日线数据获取"""
    print("\n" + "=" * 50)
    print("📈 日线数据获取演示")
    print("=" * 50)
    
    try:
        xt = EasyXT()
        if not xt.init_data():
            print("❌ 无法连接到QMT")
            return
        
        # 获取日线数据
        codes = ['000001.SZ', '600000.SH']
        print(f"获取股票: {', '.join(codes)}")
        
        data = xt.get_price(
            codes=codes,
            period='1d',
            count=5  # 最近5个交易日
        )
        
        if data is not None and not data.empty:
            print(f"\n✅ 成功获取日线数据 ({len(data)} 条记录)")
            print("\n数据预览:")
            print(data.head())
            
            # 显示数据统计
            print(f"\n数据统计:")
            print(f"  时间范围: {data['time'].min()} 到 {data['time'].max()}")
            print(f"  股票数量: {data['code'].nunique()}")
            print(f"  数据字段: {list(data.columns)}")
        else:
            print("❌ 未获取到数据")
            
    except Exception as e:
        print(f"❌ 错误: {e}")

def demo_minute_data():
    """演示分钟数据获取"""
    print("\n" + "=" * 50)
    print("⏰ 分钟数据获取演示")
    print("=" * 50)
    
    try:
        xt = EasyXT()
        if not xt.init_data():
            print("❌ 无法连接到QMT")
            return
        
        # 测试不同的分钟周期
        minute_periods = ['1m', '5m', '15m', '30m']
        code = '000001.SZ'
        
        for period in minute_periods:
            try:
                print(f"\n测试 {period} 数据...")
                
                data = xt.get_price(
                    codes=code,
                    period=period,
                    count=10  # 最近10条数据
                )
                
                if data is not None and not data.empty:
                    print(f"✅ {period} 数据获取成功 ({len(data)} 条记录)")
                    print(f"   时间范围: {data['time'].min()} 到 {data['time'].max()}")
                    
                    # 显示最新几条数据
                    print("   最新数据:")
                    latest_data = data.tail(3)[['time', 'open', 'high', 'low', 'close', 'volume']]
                    for _, row in latest_data.iterrows():
                        print(f"     {row['time']}: O={row['open']:.2f} H={row['high']:.2f} L={row['low']:.2f} C={row['close']:.2f} V={row['volume']}")
                else:
                    print(f"❌ {period} 数据为空")
                    
            except Exception as e:
                print(f"❌ {period} 数据获取失败: {e}")
                
    except Exception as e:
        print(f"❌ 初始化失败: {e}")

def demo_tick_data():
    """演示分笔数据获取"""
    print("\n" + "=" * 50)
    print("📊 分笔数据获取演示")
    print("=" * 50)
    
    try:
        xt = EasyXT()
        if not xt.init_data():
            print("❌ 无法连接到QMT")
            return
        
        code = '000001.SZ'
        print(f"获取股票 {code} 的分笔数据...")
        
        data = xt.get_price(
            codes=code,
            period='tick',
            count=5  # 最近5笔成交
        )
        
        if data is not None and not data.empty:
            print(f"✅ 成功获取分笔数据 ({len(data)} 条记录)")
            print("\n分笔数据预览:")
            print(data.head())
            
            # 显示字段说明
            print(f"\n字段说明:")
            print(f"  time: 成交时间")
            print(f"  lastPrice: 成交价格")
            print(f"  volume: 成交量")
            print(f"  amount: 成交金额")
        else:
            print("❌ 未获取到分笔数据")
            
    except Exception as e:
        print(f"❌ 分笔数据获取失败: {e}")

def demo_period_validation():
    """演示周期验证功能"""
    print("\n" + "=" * 50)
    print("✅ 数据周期验证演示")
    print("=" * 50)
    
    # 测试有效周期
    valid_periods = ['1d', '1m', '5m', '15m', '30m', '1h', 'tick']
    print("有效周期测试:")
    for period in valid_periods:
        is_valid = validate_period(period)
        print(f"  {period:6} - {'✅ 支持' if is_valid else '❌ 不支持'}")
    
    # 测试无效周期
    invalid_periods = ['2m', '10m', '45m', '2h', '1w', '1M']
    print(f"\n无效周期测试:")
    for period in invalid_periods:
        is_valid = validate_period(period)
        print(f"  {period:6} - {'✅ 支持' if is_valid else '❌ 不支持'}")
    
    # 演示错误处理
    print(f"\n错误处理演示:")
    try:
        xt = EasyXT()
        if xt.init_data():
            # 尝试使用不支持的周期
            data = xt.get_price('000001.SZ', period='2m')
    except ValueError as e:
        print(f"✅ 正确捕获错误: {e}")
    except Exception as e:
        print(f"❌ 其他错误: {e}")

def demo_level2_data():
    """演示Level2数据获取（需要权限）"""
    print("\n" + "=" * 50)
    print("📈 Level2数据获取演示 (需要权限)")
    print("=" * 50)
    
    try:
        xt = EasyXT()
        if not xt.init_data():
            print("❌ 无法连接到QMT")
            return
        
        code = '000001.SZ'
        level2_periods = ['l2quote', 'l2order', 'l2transaction']
        
        for period in level2_periods:
            try:
                print(f"\n测试 {period} 数据...")
                
                data = xt.get_price(
                    codes=code,
                    period=period,
                    count=1
                )
                
                if data is not None and not data.empty:
                    print(f"✅ {period} 数据获取成功")
                    print(f"   数据字段: {list(data.columns)}")
                else:
                    print(f"❌ {period} 数据为空 (可能需要Level2权限)")
                    
            except Exception as e:
                error_msg = str(e)
                if "权限" in error_msg or "permission" in error_msg.lower():
                    print(f"❌ {period} 需要Level2权限")
                else:
                    print(f"❌ {period} 获取失败: {error_msg[:50]}...")
                    
    except Exception as e:
        print(f"❌ 初始化失败: {e}")

def demo_data_usage_tips():
    """数据使用技巧和建议"""
    print("\n" + "=" * 50)
    print("💡 数据使用技巧和建议")
    print("=" * 50)
    
    tips = [
        "1. 日线数据 (1d): 适合长期分析，数据量小，获取速度快",
        "2. 小时数据 (1h): 适合日内分析，平衡了精度和数据量",
        "3. 分钟数据 (1m/5m/15m/30m): 适合短期交易，注意限制时间范围",
        "4. 分笔数据 (tick): 最高精度，数据量大，适合高频分析",
        "5. Level2数据: 需要购买权限，提供更详细的市场信息",
        "",
        "📋 使用建议:",
        "• 分钟数据建议使用count参数限制数量，避免内存溢出",
        "• 长期回测使用日线数据，短期策略使用分钟数据",
        "• 实时监控可以结合tick数据和Level2数据",
        "• 在QMT客户端中预先下载历史数据可以提高获取速度",
        "",
        "⚠️  注意事项:",
        "• 分钟数据在非交易时间可能为空",
        "• Level2数据需要相应的市场权限",
        "• 数据获取失败时检查网络连接和QMT客户端状态",
        "• 大量数据获取时注意内存使用情况"
    ]
    
    for tip in tips:
        print(f"  {tip}")

def main():
    """主函数"""
    print("EasyXT数据周期详解")
    print("基于xtdata官方文档v2023-01-31")
    
    # 显示支持的周期
    show_supported_periods()
    
    # 周期验证演示
    demo_period_validation()
    
    # 询问是否进行实际数据测试
    try:
        choice = input("\n是否进行实际数据获取测试? (y/n): ").lower().strip()
        if choice in ['y', 'yes', '是']:
            # 日线数据演示
            demo_daily_data()
            
            # 分钟数据演示
            demo_minute_data()
            
            # 分笔数据演示
            demo_tick_data()
            
            # Level2数据演示
            demo_level2_data()
        
        # 显示使用技巧
        demo_data_usage_tips()
        
        print(f"\n" + "=" * 60)
        print("数据周期详解完成！")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n程序已取消")

if __name__ == "__main__":
    main()