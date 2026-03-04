
"""
EasyXT学习实例 01 - 基础入门
学习目标：掌握EasyXT的基本初始化和简单数据获取
"""

import sys
import os
import pandas as pd
from datetime import datetime

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import easy_xt

# 不再使用模拟数据
MOCK_MODE = False

def lesson_01_basic_setup():
    """第1课：基础设置和初始化"""
    print("=" * 60)
    print("第1课：EasyXT基础设置")
    print("=" * 60)
    
    # 1. 导入和创建API实例
    print("1. 创建API实例")
    api = easy_xt.get_api()
    print("✓ API实例创建成功")
    
    # 2. 初始化数据服务
    print("\n2. 初始化数据服务")
    try:
        success = api.init_data()
        if success:
            print("✓ 数据服务初始化成功")
        else:
            print("⚠️ 数据服务初始化失败，这是正常的")
            print("💡 原因：需要启动迅投客户端并登录")
            print("🔄 继续使用模拟模式进行学习")
            success = True  # 继续学习
    except Exception as e:
        print(f"⚠️ 数据服务初始化异常: {e}")
        print("🔄 继续使用模拟模式进行学习")
        success = True  # 继续学习
    
    return success

def lesson_02_get_stock_data():
    """第2课：获取股票数据"""
    print("\n" + "=" * 60)
    print("第2课：获取股票数据")
    print("=" * 60)
    
    api = easy_xt.get_api()
    
    # 1. 获取单只股票的历史数据
    print("1. 获取平安银行(000001.SZ)最近10天数据")
    try:
        data = api.get_price('000001.SZ', count=10)
        print("✓ 数据获取成功")
        print(f"数据形状: {data.shape}")
        print("最新5条数据:")
        print(data.tail().to_string())
    except Exception as e:
        print(f"✗ 获取数据失败: {e}")
    
    # 2. 获取多只股票数据
    print("\n2. 获取多只股票数据")
    try:
        codes = ['000001.SZ', '000002.SZ', '600000.SH']  # 平安银行、万科A、浦发银行
        data = api.get_price(codes, count=5)
        if data is None or data.empty:
            if MOCK_MODE:
                print("🔄 切换到模拟数据模式...")
                data = api.mock_get_price(codes, count=5)
            else:
                raise Exception("无法获取数据")
                
        
        if not data.empty:
            print("✓ 多股票数据获取成功")
            print(f"数据形状: {data.shape}")
            print("数据预览:")
            print(data.head(10).to_string())
        else:
            print("✗ 未获取到数据")
    except Exception as e:
        print(f"✗ 获取多股票数据失败: {e}")

def lesson_03_different_periods():
    """第3课：获取不同周期的数据"""
    print("\n" + "=" * 60)
    print("第3课：获取不同周期的数据")
    print("=" * 60)
    
    api = easy_xt.get_api()
    code = '000001.SZ'

    # 测试支持的数据周期
    test_periods = ['1d', '1m', '5m', '15m', '30m', '1h']

    print("测试所有支持的数据周期:")
    for period in test_periods:
        print(f"\n获取 {code} 的 {period} 数据:")
        try:
            data = api.get_price(code, period=period, count=5)
            if not data.empty:
                print(f"✓ {period} 数据获取成功，共 {len(data)} 条")
                if 'time' in data.columns:
                    print(f"时间范围: {data['time'].min()} 到 {data['time'].max()}")
                else:
                    print(f"时间范围: {data.index[0]} 到 {data.index[-1]}")
                print(f"最新价格: {data['close'].iloc[-1]:.2f}")
            else:
                print(f"✗ {period} 数据为空")
        except Exception as e:
            print(f"✗ {period} 数据获取失败: {e}")

    print("\n💡 数据周期使用建议：")
    print("   - 日线数据使用 '1d'")
    print("   - 分钟数据根据需要选择 '1m', '5m', '15m', '30m'")
    print("   - 小时线使用 '1h'")
    print("   - ✅ EasyXT 已添加线程锁保护，所有周期都能正常使用")

def lesson_04_date_range_data():
    """第4课：按日期范围获取数据"""
    print("\n" + "=" * 60)
    print("第4课：按日期范围获取数据")
    print("=" * 60)
    
    api = easy_xt.get_api()
    code = '000001.SZ'
    
    # 1. 按日期范围获取数据（使用近期日期）
    print("1. 获取最近一周的数据")
    try:
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        print(f"获取 {start_str} 到 {end_str} 的数据")
        
        data = api.get_price(
            codes=code,
            start=start_str,
            end=end_str,
            period='1d'
        )
        if not data.empty:
            print("✓ 日期范围数据获取成功")
            print(f"数据条数: {len(data)}")
            if 'time' in data.columns:
                print(f"日期范围: {data['time'].min()} 到 {data['time'].max()}")
            else:
                print(f"日期范围: {data.index[0]} 到 {data.index[-1]}")
            print("价格统计:")
            print(f"  最高价: {data['high'].max():.2f}")
            print(f"  最低价: {data['low'].min():.2f}")
            print(f"  平均价: {data['close'].mean():.2f}")
        else:
            print("✗ 未获取到数据")
    except Exception as e:
        print(f"✗ 获取日期范围数据失败: {e}")
    
    # 2. 不同的日期格式（使用近期日期）
    print("\n2. 测试不同的日期格式")
    try:
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)
        
        date_formats = [
            (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')),  # 标准格式
            (start_date.strftime('%Y%m%d'), end_date.strftime('%Y%m%d')),      # 紧凑格式
            (start_date.strftime('%Y/%m/%d'), end_date.strftime('%Y/%m/%d'))   # 斜杠格式
        ]
        
        for start, end in date_formats:
            print(f"测试日期格式: {start} 到 {end}")
            try:
                data = api.get_price(code, start=start, end=end)
                if not data.empty:
                    print(f"✓ 格式 {start} 解析成功，获取 {len(data)} 条数据")
                else:
                    print(f"✗ 格式 {start} 未获取到数据")
            except Exception as e:
                print(f"✗ 格式 {start} 解析失败: {e}")
    except Exception as e:
        print(f"✗ 日期格式测试失败: {e}")
    
    # 3. 使用count参数获取数据（更稳定的方式）
    print("\n3. 使用count参数获取最近数据（推荐方式）")
    try:
        data = api.get_price(code, period='1d', count=10)
        if not data.empty:
            print("✓ count方式数据获取成功")
            print(f"数据条数: {len(data)}")
            print("最新5条数据:")
            print(data.tail()[['time', 'code', 'open', 'high', 'low', 'close']].to_string())
        else:
            print("✗ count方式未获取到数据")
    except Exception as e:
        print(f"✗ count方式获取失败: {e}")

def lesson_05_current_price():
    """第5课：获取实时价格和五档行情"""
    print("\n" + "=" * 60)
    print("第5课：获取实时价格和五档行情")
    print("=" * 60)

    api = easy_xt.get_api()

    # 1. 获取单只股票实时价格
    print("1. 获取平安银行实时价格")
    try:
        current = api.get_current_price('000001.SZ')
        if current is None or current.empty:
            if MOCK_MODE:
                print("🔄 切换到模拟数据模式...")
                current = api.mock_get_current_price('000001.SZ')
            else:
                raise Exception("无法获取实时价格")

        if not current.empty:
            print("✓ 实时价格获取成功")
            print(current.to_string())
        else:
            print("✗ 未获取到实时价格")
    except Exception as e:
        print(f"✗ 获取实时价格失败: {e}")

    # 2. 获取五档行情数据（新增）
    print("\n2. 获取五档行情数据（买卖盘口）")
    print("💡 提示：需要先订阅行情才能获取五档数据")
    print("💡 建议：在交易时间内运行，数据更准确")

    try:
        code = '000001.SZ'

        # 使用easy_xt的get_order_book获取五档行情
        print(f"\n使用easy_xt获取 {code} 的五档行情...")
        print("步骤1: 订阅tick行情...")
        print("步骤2: 获取完整tick数据...")
        print("步骤3: 提取五档行情数据...")

        order_book = api.get_order_book(code)

        if order_book is not None and not order_book.empty:
            print("✓ 五档行情获取成功")

            # 获取第一行数据
            data = order_book.iloc[0]

            # 检查五档数据是否有值
            has_bid_ask_data = (
                data['bid1'] > 0 or
                data['ask1'] > 0 or
                data['bidVol1'] > 0 or
                data['askVol1'] > 0
            )

            # 显示基础信息
            print("\n" + "="*50)
            print(f"{'股票代码':<10} {data['code']}")
            print(f"{'最新价':<10} {data['lastPrice']:.2f}")
            print(f"{'开盘价':<10} {data['open']:.2f}")
            print(f"{'最高价':<10} {data['high']:.2f}")
            print(f"{'最低价':<10} {data['low']:.2f}")
            print("="*50)

            if has_bid_ask_data:
                # 有五档数据，正常显示
                print("\n【五档盘口】")
                print(f"{'档位':<8} {'买盘':<20} {'卖盘':<20}")
                print("-"*50)

                for i in range(1, 6):
                    bid_price = data[f'bid{i}']
                    ask_price = data[f'ask{i}']
                    bid_vol = data[f'bidVol{i}']
                    ask_vol = data[f'askVol{i}']

                    if bid_price > 0 or ask_price > 0:
                        bid_str = f"{bid_price:.2f} ({bid_vol:,.0f} 手)" if bid_price > 0 else "--"
                        ask_str = f"{ask_price:.2f} ({ask_vol:,.0f} 手)" if ask_price > 0 else "--"
                        print(f"  {i}档    {bid_str:<20} {ask_str:<20}")
                    else:
                        break

                # 计算买卖价差
                bid1 = data['bid1']
                ask1 = data['ask1']
                if bid1 > 0 and ask1 > 0:
                    spread = ask1 - bid1
                    spread_pct = (spread / bid1) * 100
                    print(f"\n【盘口分析】")
                    print(f"买卖价差: {spread:.2f} 元 ({spread_pct:.3f}%)")
                    print(f"中间价: {(bid1 + ask1) / 2:.2f} 元")

                # 计算买卖盘总量
                total_bid_vol = sum(data[f'bidVol{i}'] for i in range(1, 6))
                total_ask_vol = sum(data[f'askVol{i}'] for i in range(1, 6))

                if total_bid_vol > 0 or total_ask_vol > 0:
                    print(f"\n【盘口总量】")
                    print(f"买盘总量: {total_bid_vol:,.0f} 手")
                    print(f"卖盘总量: {total_ask_vol:,.0f} 手")

                    if total_bid_vol > 0 and total_ask_vol > 0:
                        ratio = total_bid_vol / total_ask_vol
                        print(f"买卖比: {ratio:.2f}")
                        if ratio > 1:
                            print(f"市场情绪: {'买盘强势' if ratio > 1.2 else '买盘略强'}")
                        elif ratio < 1:
                            print(f"市场情绪: {'卖盘强势' if ratio < 0.8 else '卖盘略强'}")
                        else:
                            print(f"市场情绪: 买卖平衡")

                print(f"\n【数据字段】")
                print(f"可用字段: {', '.join(order_book.columns.tolist())}")

            else:
                # 五档数据为0的情况
                print("\n⚠️ 五档行情数据为空（值为0）")
                print("\n【诊断信息】")
                print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"星期: {['一', '二', '三', '四', '五', '六', '日'][datetime.now().weekday()]}")

                # 检查是否是交易时间
                current_hour = datetime.now().hour
                current_minute = datetime.now().minute
                current_weekday = datetime.now().weekday()

                is_weekend = current_weekday >= 5  # 周六周日
                # 交易时间：9:30-11:30, 13:00-15:00
                morning = (9 < current_hour < 11) or (current_hour == 9 and current_minute >= 30) or (current_hour == 11 and current_minute <= 30)
                afternoon = (13 <= current_hour < 15)
                is_trading_time = morning or afternoon

                print(f"\n【时间检查】")
                print(f"是否周末: {'是' if is_weekend else '否'}")
                print(f"是否交易时间: {'是' if is_trading_time else '否'}")

                if is_weekend:
                    print("\n💡 原因：今天是周末，市场不开盘")
                    print("   请在周一到周五的交易时间（9:30-15:00）运行")

                elif not is_trading_time:
                    print(f"\n💡 原因：当前不是交易时间（当前{current_hour:02d}:{current_minute:02d}）")
                    print("   请在交易时间（9:30-15:00）运行")

                else:
                    print("\n💡 可能原因：")
                    print("   1. QMT未登录或连接断开")
                    print("   2. 股票停牌")
                    print("   3. 需要Level2行情权限才能获取五档数据")
                    print("   4. 订阅数据推送延迟（已自动重试3次）")
                    print("   5. QMT客户端未订阅tick行情")
                    print("\n【订阅机制说明】")
                    print("   五档行情数据通过异步推送获取：")
                    print("   1. subscribe_quote() - 发送订阅请求")
                    print("   2. QMT服务器推送tick数据到客户端")
                    print("   3. get_full_tick() - 从缓存读取推送的数据")
                    print("   4. 如果数据还没推送，需要等待或重试")

                print("\n【建议】")
                print("   ✓ 在交易时间（9:30-15:00）内运行")
                print("   ✓ 确保QMT客户端已登录")
                print("   ✓ 检查QMT客户端是否显示实时五档数据")
                print("   ✓ 确认是否有Level2行情权限")
                print("   ✓ 等待几秒后重试（已自动重试3次，每次间隔2秒）")

        else:
            print("⚠️ 五档行情数据为空")
            print("💡 可能的原因：")
            print("  - QMT客户端未启动")
            print("  - 数据服务未连接")
            print("  - 当前非交易时间")

    except Exception as e:
        error_msg = str(e)
        print(f"⚠️ 获取五档行情失败: {error_msg}")

        if "xtquant" in error_msg or "xtdata" in error_msg:
            print("\n💡 提示：")
            print("  - xtdata需要从迅投QMT客户端目录安装")
            print("  - 请确保QMT客户端已启动")
            print("  - 可以先使用api.get_current_price()获取基础行情")
        else:
            print("\n💡 请检查：")
            print("  - QMT客户端是否已启动")
            print("  - 是否已调用api.init_data()")
            print("  - 网络连接是否正常")

    # 3. 获取多只股票实时价格
    print("\n3. 获取多只股票实时价格")
    try:
        codes = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH']
        current = api.get_current_price(codes)
        if current is None or current.empty:
            if MOCK_MODE:
                print("🔄 切换到模拟数据模式...")
                current = api.mock_get_current_price(codes)
            else:
                raise Exception("无法获取实时价格")

        if not current.empty:
            print("✓ 多股票实时价格获取成功")
            print("实时价格数据:")
            # 显示实际可用的字段
            available_columns = ['code', 'price', 'open', 'high', 'low', 'pre_close']
            display_columns = [col for col in available_columns if col in current.columns]
            print(current[display_columns].to_string())

            # 计算涨跌幅
            if 'price' in current.columns and 'pre_close' in current.columns:
                print("\n涨跌幅计算:")
                for _, row in current.iterrows():
                    if row['pre_close'] > 0:
                        change = row['price'] - row['pre_close']
                        change_pct = (change / row['pre_close']) * 100
                        print(f"{row['code']}: {change:+.2f} ({change_pct:+.2f}%)")
        else:
            print("✗ 未获取到实时价格")
    except Exception as e:
        print(f"✗ 获取多股票实时价格失败: {e}")

def lesson_06_stock_list():
    """第6课：获取股票列表"""
    print("\n" + "=" * 60)
    print("第6课：获取股票列表")
    print("=" * 60)

    api = easy_xt.get_api()

    # 1. 获取所有A股列表
    print("1. 获取A股列表")
    try:
        stock_list = api.get_stock_list('A股')
        if stock_list:
            print(f"✓ A股列表获取成功，共 {len(stock_list)} 只股票")
            print("前10只股票:")
            for i, code in enumerate(stock_list[:10]):
                print(f"  {i+1}. {code}")
        else:
            print("✗ 未获取到股票列表")
    except Exception as e:
        print(f"✗ 获取股票列表失败: {e}")
    
    # 2. 获取沪深300列表
    print("\n2. 获取沪深300列表")
    try:
        hs300_list = api.get_stock_list('沪深300')
        if hs300_list:
            print(f"✓ 沪深300列表获取成功，共 {len(hs300_list)} 只股票")
            print("前10只股票:")
            for i, code in enumerate(hs300_list[:10]):
                print(f"  {i+1}. {code}")
        else:
            print("✗ 未获取到沪深300列表")
    except Exception as e:
        print(f"✗ 获取沪深300列表失败: {e}")

def lesson_07_trading_dates():
    """第7课：获取交易日历"""
    print("\n" + "=" * 60)
    print("第7课：获取交易日历")
    print("=" * 60)
    
    api = easy_xt.get_api()
    
    # 1. 获取最近的交易日
    print("1. 获取最近10个交易日")
    try:
        trading_dates = api.get_trading_dates(market='SH', count=10)
        if trading_dates:
            print("✓ 交易日获取成功")
            print("最近10个交易日:")
            for i, date in enumerate(trading_dates[-10:]):
                print(f"  {i+1}. {date}")
        else:
            print("✗ 未获取到交易日")
    except Exception as e:
        print(f"✗ 获取交易日失败: {e}")
    
    # 2. 获取指定时间段的交易日（使用近期日期）
    print("\n2. 获取本月的交易日")
    try:
        from datetime import datetime
        current_date = datetime.now()
        start_of_month = current_date.replace(day=1)
        
        start_str = start_of_month.strftime('%Y-%m-%d')
        end_str = current_date.strftime('%Y-%m-%d')
        
        print(f"获取 {start_str} 到 {end_str} 的交易日")
        
        trading_dates = api.get_trading_dates(
            market='SH',
            start=start_str,
            end=end_str
        )
        if trading_dates:
            print(f"✓ 本月交易日获取成功，共 {len(trading_dates)} 天")
            print("交易日列表:")
            for date in trading_dates:
                print(f"  {date}")
        else:
            print("✗ 未获取到交易日")
    except Exception as e:
        print(f"✗ 获取交易日失败: {e}")
    
    # 3. 获取最近30个交易日（更稳定的方式）
    print("\n3. 获取最近30个交易日（推荐方式）")
    try:
        trading_dates = api.get_trading_dates(market='SH', count=30)
        if trading_dates:
            print(f"✓ 最近30个交易日获取成功")
            print("最近10个交易日:")
            for i, date in enumerate(trading_dates[-10:]):
                print(f"  {i+1}. {date}")
            print(f"... 共 {len(trading_dates)} 个交易日")
        else:
            print("✗ 未获取到交易日")
    except Exception as e:
        print(f"✗ 获取交易日失败: {e}")

def main():
    """主函数：运行所有基础学习课程"""
    print("🎓 EasyXT基础入门学习课程")
    print("本课程将带您学习EasyXT的基本功能")
    print("请确保已正确安装xtquant并启动相关服务")
    
    # 运行所有课程
    lessons = [
        lesson_01_basic_setup,
        lesson_02_get_stock_data,
        lesson_03_different_periods,
        lesson_04_date_range_data,
        lesson_05_current_price,
        lesson_06_stock_list,
        lesson_07_trading_dates
    ]
    
    for lesson in lessons:
        try:
            lesson()
            if not (len(sys.argv) > 1 and '--auto' in sys.argv):
                input("\n按回车键继续下一课...")
            else:
                print(f"\n✓ 第{lessons.index(lesson)+1}课完成，自动继续...")
        except KeyboardInterrupt:
            print("\n\n学习已中断")
            break
        except Exception as e:
            print(f"\n课程执行出错: {e}")
            input("按回车键继续...")
    
    print("\n🎉 基础入门课程完成！")
    print("\n已学习内容:")
    print("✓ 第1课: 基础设置和初始化")
    print("✓ 第2课: 获取股票数据")
    print("✓ 第3课: 获取不同周期数据")
    print("✓ 第4课: 按日期范围获取数据")
    print("✓ 第5课: 实时价格和五档行情")
    print("✓ 第6课: 获取股票列表")
    print("✓ 第7课: 获取交易日历")

    print("\n接下来可以学习：")
    print("- 02_交易基础.py - 学习基础交易功能")
    print("- 03_高级交易.py - 学习高级交易功能")
    print("- 04_策略回测.py - 学习策略回测")

if __name__ == "__main__":
    main()