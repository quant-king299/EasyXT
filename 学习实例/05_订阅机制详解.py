"""
EasyXT学习实例 08 - 订阅机制详解
学习目标：掌握xtquant的订阅机制，正确获取实时行情数据

本课重点：
1. 理解订阅机制的工作原理
2. 掌握回调函数的使用
3. 学会正确获取五档行情数据
4. 了解订阅 vs 主动获取的区别
"""

import sys
import os
import pandas as pd
from datetime import datetime
import time

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import xtquant.xtdata as xt
import easy_xt


def print_section(title):
    """打印分节标题"""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_subsection(title):
    """打印子节标题"""
    print("\n" + "-" * 70)
    print(title)
    print("-" * 70)


def lesson_01_subscription_concept():
    """第1课：理解订阅机制"""
    print_section("第1课：订阅机制的核心概念")

    print("""
📚 什么是订阅机制？

订阅机制是xtquant获取实时行情数据的核心方式。

【传统方式】主动获取（拉取模式）
  - 你的程序 → 主动请求数据 → 服务器 → 返回数据
  - 优点：简单直接
  - 缺点：可能有延迟，需要轮询

【订阅方式】推送模式
  - 你的程序 → 订阅股票 → 服务器持续推送最新数据
  - 优点：实时性好，服务器主动推送
  - 缺点：需要理解回调函数

【工作流程】
  1. subscribe_quote() - 发送订阅请求
  2. QMT服务器接收订阅
  3. 有新数据时，服务器主动推送到客户端
  4. 客户端缓存推送的数据
  5. get_full_tick() - 从缓存读取最新数据

【关键点】
  ⚠️ 订阅后数据不是立即返回的，而是异步推送
  ⚠️ 需要等待一小段时间让数据推送完成
  ⚠️ 使用回调函数可以实时接收每一笔推送
    """)

    print("\n💡 类比理解：")
    print("  订阅模式就像订阅报纸：")
    print("    - 你订阅后，报社每天主动送报纸到家里")
    print("    - 你不需要每天去报社查询")
    print("    - 报纸一到就可以阅读")


def lesson_02_subscribe_vs_active():
    """第2课：订阅 vs 主动获取"""
    print_section("第2课：订阅方式 vs 主动获取")

    api = easy_xt.get_api()
    api.init_data()

    code = '000001.SZ'

    print(f"\n示例股票：{code}（平安银行）")

    # 方式1：主动获取
    print_subsection("方式1：主动获取（不订阅）")
    print("直接调用 get_full_tick()，不先订阅")

    tick_data = xt.get_full_tick([code])
    if tick_data and code in tick_data:
        tick = tick_data[code]
        print(f"  最新价: {tick.get('lastPrice', 0):.2f}")
        print(f"  ✗ 五档数据可能为空（因为未订阅）")

        # 检查五档
        ask_price = tick.get('askPrice', 0)
        if ask_price and hasattr(ask_price, '__len__') and len(ask_price) > 0:
            print(f"  卖一: {ask_price[0]:.2f}")
        else:
            print(f"  卖一: 无数据（未订阅）")

    # 方式2：先订阅再获取
    print_subsection("方式2：先订阅再获取（推荐）")
    print("1. 先调用 subscribe_quote() 订阅")
    print("2. 等待数据推送（2-3秒）")
    print("3. 再调用 get_full_tick() 获取")

    xt.subscribe_quote(code, period='tick')
    print("  ✓ 订阅成功，等待数据推送...")
    time.sleep(2.0)

    tick_data = xt.get_full_tick([code])
    if tick_data and code in tick_data:
        tick = tick_data[code]
        print(f"  最新价: {tick.get('lastPrice', 0):.2f}")

        # 检查五档
        ask_price = tick.get('askPrice', 0)
        bid_price = tick.get('bidPrice', 0)

        if ask_price and hasattr(ask_price, '__len__') and len(ask_price) > 0:
            print(f"  ✓ 卖一: {ask_price[0]:.2f}")
            print(f"  ✓ 买一: {bid_price[0]:.2f}")
            print(f"  ✓ 五档数据完整！")

    print("\n【总结】")
    print("  主动获取：简单快速，但数据可能不完整")
    print("  先订后取：推荐方式，数据完整准确")


def lesson_03_callback_function():
    """第3课：使用回调函数接收推送"""
    print_section("第3课：使用回调函数实时接收数据推送")

    # ==================== 演示1：基础回调 ====================
    print_subsection("演示1：回调函数自动执行（无需等待）")

    code = '000001.SZ'

    print(f"\n💡 核心要点：回调函数自动执行，不需要sleep等待！")
    print(f"演示股票：{code}")

    # 创建一个计数器
    counter = {'count': 0, 'max': 5}

    def on_tick_data(data):
        """
        tick数据回调函数

        ⚠️ 重要：这个函数不需要手动调用！
        当服务器推送新数据时，xtquant会自动调用这个函数

        Args:
            data: dict {股票代码: tick数据}
        """
        if code in data:
            tick = data[code]
            counter['count'] += 1

            # 显示精确时间戳，证明是自动执行
            print(f"\n📨 [推送 #{counter['count']}] {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
            print(f"   回调函数自动执行！无需等待！")
            print(f"   最新价: {tick.get('lastPrice', 0):.2f}")

            # 显示五档
            ask_price = tick.get('askPrice', 0)
            bid_price = tick.get('bidPrice', 0)

            if ask_price and hasattr(ask_price, '__len__') and len(ask_price) > 0:
                print(f"   买一: {bid_price[0]:.2f}  卖一: {ask_price[0]:.2f}")

    print("\n开始订阅，将接收5次数据推送...")
    print("(数据来了会自动触发回调函数)\n")

    # 订阅并设置回调
    xt.subscribe_whole_quote(code_list=[code], callback=on_tick_data)

    # 等待推送（这里只是为了保持程序运行，不是等待数据！）
    start_time = time.time()
    while counter['count'] < counter['max'] and (time.time() - start_time) < 30:
        time.sleep(0.01)  # 极短休眠，让CPU可以处理回调

    if counter['count'] >= counter['max']:
        print(f"\n✓ 成功接收 {counter['count']} 次数据推送")
    else:
        print(f"\n⚠️ 30秒内只收到 {counter['count']} 次推送")

    # ==================== 演示2：回调函数中执行逻辑 ====================
    print_subsection("演示2：在回调函数中执行交易逻辑")

    code = '600000.SH'
    last_price = {'value': None}
    alert_count = {'value': 0}

    def on_tick_with_logic(data):
        """回调函数中执行价格监控逻辑"""
        if code in data:
            tick = data[code]
            current_price = tick.get('lastPrice', 0)

            # 首次推送记录价格
            if last_price['value'] is None:
                last_price['value'] = current_price
                print(f"\n📊 [{datetime.now().strftime('%H:%M:%S')}] "
                      f"开始监控: {code}, 初始价格: {current_price:.2f}")
                return

            # 计算价格变化
            price_change = current_price - last_price['value']
            change_pct = (price_change / last_price['value']) * 100

            # 价格变动超过0.01元时触发提示
            if abs(price_change) >= 0.01:
                direction = "📈 上涨" if price_change > 0 else "📉 下跌"
                print(f"\n{direction} | {datetime.now().strftime('%H:%M:%S.%f')[:-3]} | "
                      f"{last_price['value']:.2f} → {current_price:.2f} | "
                      f"变动: {price_change:+.2f} ({change_pct:+.2f}%)")
                last_price['value'] = current_price
                alert_count['value'] += 1

    print(f"\n监控股票: {code}")
    print("策略: 价格变动超过0.01元时触发提示")
    print("注意：回调函数自动执行，无需轮询！\n")

    xt.subscribe_whole_quote(code_list=[code], callback=on_tick_with_logic)

    # 运行10秒
    start_time = time.time()
    while time.time() - start_time < 10:
        time.sleep(0.01)

    print(f"\n✓ 10秒内触发了 {alert_count['value']} 次价格变动提示")

    # ==================== 演示3：多股票回调 ====================
    print_subsection("演示3：同时监控多只股票")

    codes = ['000001.SZ', '000002.SZ']
    push_count = {'value': 0}

    def on_multi_tick(data):
        """多股票回调函数"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        print(f"\n📨 [{timestamp}] 收到推送:")

        for code in codes:
            if code in data:
                tick_list = data[code]
                # subscribe_whole_quote返回的是tick数组
                if isinstance(tick_list, list) and len(tick_list) > 0:
                    tick = tick_list[-1]  # 取最新的tick
                else:
                    tick = tick_list

                price = tick.get('lastPrice', 0)
                print(f"   {code}: {price:.2f} 元", end='  ')

        push_count['value'] += 1

    print(f"\n监控股票: {codes}")
    print(f"目标: 接收 3 次推送\n")

    xt.subscribe_whole_quote(code_list=codes, callback=on_multi_tick)

    start_time = time.time()
    while push_count['value'] < 3 and (time.time() - start_time) < 30:
        time.sleep(0.01)

    print(f"\n✓ 演示完成")

    print("\n【回调函数要点】")
    print("  1. ✅ 回调函数由系统自动调用，有新数据时触发")
    print("  2. ✅ 不需要sleep等待，数据来了立即执行")
    print("  3. ✅ 可以在回调函数中实时处理数据")
    print("  4. ✅ 适合持续监控行情的场景")
    print("  5. ✅ 回调函数中可以实现任意交易逻辑")


def lesson_04_order_book_data():
    """第4课：正确获取五档行情数据"""
    print_section("第4课：五档行情数据结构详解")

    print("""
⚠️ 重要说明：主动获取 vs 回调函数

【方式1：回调函数】推荐 ✅ (详见第3课)
  - 数据推送后回调函数自动执行
  - 实时性最好，零延迟
  - 适合持续监控行情
  - 不需要等待

【方式2：主动获取】本课演示 ⚠️
  - subscribe_quote() 订阅
  - get_full_tick() 从缓存读取
  - 适合一次性获取数据
  - ⚠️ 必须等待数据推送到缓存

【主动获取的两种等待方式】
  ❌ 方式A：固定等待 (time.sleep(2)) - 简单但浪费
  ✅ 方式B：轮询检查 - 数据到了立即返回，推荐

本课演示：轮询检查方式（推荐）
    """)

    api = easy_xt.get_api()
    api.init_data()

    code = '000001.SZ'

    print(f"\n示例股票：{code}")
    print("五档行情包含：买5档 + 卖5档")

    # 订阅
    print("\n步骤1: 订阅tick行情")
    xt.subscribe_quote(code, period='tick')
    print("  ✓ 订阅成功")

    # 轮询等待数据到达
    print("\n步骤2: 轮询等待数据推送（数据到了立即返回）")
    print("       优势：不浪费时间，数据到了立即获取")

    def wait_for_tick(code, timeout=3.0, interval=0.1):
        """
        轮询等待tick数据

        Args:
            code: 股票代码
            timeout: 超时时间（秒）
            interval: 检查间隔（秒）

        Returns:
            tick数据或None
        """
        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            tick_data = xt.get_full_tick([code])

            if tick_data and code in tick_data:
                tick = tick_data[code]

                # 检查五档数据是否存在
                ask_price = tick.get('askPrice', [])
                if ask_price and len(ask_price) > 0 and ask_price[0] > 0:
                    elapsed = time.time() - start_time
                    print(f"  ✓ 数据已到达（耗时 {elapsed:.3f} 秒）")
                    return tick

            time.sleep(interval)

        print("  ⚠️ 超时，数据未到达")
        return None

    # 获取数据
    tick = wait_for_tick(code, timeout=3.0, interval=0.1)

    if tick is not None:
        print("\n步骤3: 获取完整tick数据")
        print_subsection("五档数据的字段结构")

        print("\n原始数据字段（根据官方文档）：")
        print("  askPrice  - 委卖价格数组 [卖1, 卖2, 卖3, 卖4, 卖5]")
        print("  bidPrice  - 委买价格数组 [买1, 买2, 买3, 买4, 买5]")
        print("  askVol    - 委卖量数组 [卖量1, 卖量2, ...]")
        print("  bidVol    - 委买量数组 [买量1, 买量2, ...]")

        print_subsection("实际数据示例")

        ask_price = tick.get('askPrice', [])
        bid_price = tick.get('bidPrice', [])
        ask_vol = tick.get('askVol', [])
        bid_vol = tick.get('bidVol', [])

        print(f"\n  askPrice  = {ask_price}")
        print(f"  bidPrice  = {bid_price}")
        print(f"  askVol    = {ask_vol}")
        print(f"  bidVol    = {bid_vol}")

        print_subsection("五档盘口展示")

        print(f"\n{'档位':<8} {'卖盘':<25} {'买盘':<25}")
        print("-" * 70)

        # 显示五档（从高到低）
        for i in range(5):
            # 从数组取值
            idx = 4 - i  # 倒序显示，卖5在上，买5在下

            ask_p = ask_price[idx] if idx < len(ask_price) else 0
            ask_v = ask_vol[idx] if idx < len(ask_vol) else 0
            bid_p = bid_price[idx] if idx < len(bid_price) else 0
            bid_v = bid_vol[idx] if idx < len(bid_vol) else 0

            if ask_p > 0 or bid_p > 0:
                ask_str = f"{ask_p:.2f} ({ask_v:.0f})" if ask_p > 0 else "--"
                bid_str = f"{bid_p:.2f} ({bid_v:.0f})" if bid_p > 0 else "--"
                print(f"  {i+1}档    {ask_str:<25} {bid_str:<25}")

        print_subsection("盘口分析")

        if len(ask_price) > 0 and len(bid_price) > 0:
            spread = ask_price[0] - bid_price[0]
            spread_pct = (spread / bid_price[0]) * 100 if bid_price[0] > 0 else 0
            mid_price = (ask_price[0] + bid_price[0]) / 2

            print(f"\n  买卖价差: {spread:.2f} 元 ({spread_pct:.3f}%)")
            print(f"  中间价: {mid_price:.2f} 元")

            # 计算买卖盘总量
            total_bid_vol = sum(bid_vol) if isinstance(bid_vol, list) else 0
            total_ask_vol = sum(ask_vol) if isinstance(ask_vol, list) else 0

            print(f"  买盘总量: {total_bid_vol:.0f} 手")
            print(f"  卖盘总量: {total_ask_vol:.0f} 手")

            if total_bid_vol > 0 and total_ask_vol > 0:
                ratio = total_bid_vol / total_ask_vol
                print(f"  买卖比: {ratio:.2f}")

                if ratio > 1.2:
                    print(f"  市场情绪: 买盘强势 📈")
                elif ratio < 0.8:
                    print(f"  市场情绪: 卖盘强势 📉")
                else:
                    print(f"  市场情绪: 买卖平衡 ➡️")

    else:
        print("\n⚠️ 未能获取到五档数据")
        print("   可能原因：")
        print("   - 非交易时间")
        print("   - 网络连接问题")
        print("   - QMT服务未启动")

    print("\n【重要提示】")
    print("  1. 五档数据必须先订阅才能获取")
    print("  2. askPrice/bidPrice 是数组，不是单个值")
    print("  3. 索引0表示第一档（买一/卖一）")
    print("  4. 非交易时间五档数据可能为空")
    print("  5. 主动获取推荐使用轮询检查，而非固定等待")
    print("     - 固定等待: time.sleep(2) - 简单但浪费时间")
    print("     - 轮询检查: 数据到了立即返回 - 推荐 ✅")


def lesson_05_easy_xt_wrapper():
    """第5课：使用EasyXT简化接口"""
    print_section("第5课：使用EasyXT简化获取五档行情")

    api = easy_xt.get_api()
    api.init_data()

    code = '000001.SZ'

    print(f"\nEasyXT已经封装了五档行情的获取逻辑")
    print(f"只需要调用：api.get_order_book('{code}')")

    print_subsection("使用EasyXT获取五档行情")

    order_book = api.get_order_book(code)

    if order_book is not None and not order_book.empty:
        print(f"\n✓ 获取成功！")
        print(f"\n返回数据类型: {type(order_book)}")
        print(f"数据形状: {order_book.shape}")
        print(f"包含字段: {', '.join(order_book.columns)}")

        print_subsection("五档数据展示")

        data = order_book.iloc[0]

        print(f"\n股票代码: {data['code']}")
        print(f"最新价: {data['lastPrice']:.2f}")

        print(f"\n{'档位':<8} {'买盘':<25} {'卖盘':<25}")
        print("-" * 70)

        for i in range(1, 6):
            bid_p = data[f'bid{i}']
            ask_p = data[f'ask{i}']
            bid_v = data[f'bidVol{i}']
            ask_v = data[f'askVol{i}']

            if bid_p > 0 or ask_p > 0:
                bid_str = f"{bid_p:.2f} ({bid_v:.0f})" if bid_p > 0 else "--"
                ask_str = f"{ask_p:.2f} ({ask_v:.0f})" if ask_p > 0 else "--"
                print(f"  {i}档    {bid_str:<25} {ask_str:<25}")

    print("\n【EasyXT的优势】")
    print("  ✓ 自动处理订阅逻辑")
    print("  ✓ 自动等待数据推送")
    print("  ✓ 自动重试机制（最多3次）")
    print("  ✓ 统一的DataFrame返回格式")
    print("  ✓ 简化字段名（bid1-5, ask1-5）")


def lesson_05_5_easy_xt_subscribe():
    """第5.5课：使用EasyXT的订阅接口"""
    print_section("第5.5课：使用EasyXT的订阅接口（新功能）")

    api = easy_xt.get_api()
    api.init_data()

    print("""
🎉 新功能：EasyXT现已封装了订阅接口！

【新增的订阅方法】
  1. api.subscribe()       - 订阅单个或多个股票
  2. api.subscribe_whole()  - 订阅全推行情（推荐多股票）
  3. api.unsubscribe()     - 取消订阅
  4. api.run_forever()     - 持续接收推送
    """)

    # 示例1：基础订阅
    print_subsection("示例1：订阅单只股票")

    code = '000001.SZ'

    print(f"\n股票: {code}")

    # 定义回调函数
    def on_tick(data):
        """tick数据回调"""
        if code in data:
            tick_list = data[code]
            # subscribe_whole_quote的回调中，值是tick数组
            # 取最后一个元素（最新数据）
            if isinstance(tick_list, list) and len(tick_list) > 0:
                tick = tick_list[-1]
            else:
                tick = tick_list

            print(f"  [推送] {datetime.now().strftime('%H:%M:%S')} "
                  f"最新价: {tick.get('lastPrice', 0):.2f}")

    print("\n订阅（将接收5次推送）...")

    # 订阅
    seq = api.subscribe(code, callback=on_tick)

    if seq > 0:
        print(f"✓ 订阅成功，订阅号: {seq}")

        # 接收5次推送
        for i in range(5):
            time.sleep(1)

        # 取消订阅
        api.unsubscribe(seq)
        print("✓ 已取消订阅")
    else:
        print("✗ 订阅失败")

    # 示例2：订阅多只股票
    print_subsection("示例2：订阅多只股票（使用subscribe_whole）")

    codes = ['000001.SZ', '000002.SZ', '600000.SH']

    print(f"\n股票列表: {codes}")

    # 定义回调
    counter = {'count': 0, 'max': 3}

    def on_multi_tick(data):
        """多股票tick回调"""
        for code in codes:
            if code in data:
                tick_list = data[code]
                # subscribe_whole_quote的回调中，值是tick数组
                if isinstance(tick_list, list) and len(tick_list) > 0:
                    tick = tick_list[-1]
                else:
                    tick = tick_list
                print(f"  {code}: {tick.get('lastPrice', 0):.2f}  ", end='')
        print()  # 换行
        counter['count'] += 1

    print("\n使用 subscribe_whole() 订阅多只股票...")

    seq = api.subscribe_whole(codes, callback=on_multi_tick)

    if seq > 0:
        print(f"✓ 订阅成功，订阅号: {seq}")

        # 接收3次推送
        start = time.time()
        while counter['count'] < counter['max'] and (time.time() - start) < 10:
            time.sleep(0.5)

        api.unsubscribe(seq)
        print("✓ 已取消订阅")
    else:
        print("✗ 订阅失败")

    print("\n【EasyXT订阅接口的优势】")
    print("  ✓ 简洁的API，不需要直接调用xtdata")
    print("  ✓ 自动处理连接检查")
    print("  ✓ 统一的错误处理")
    print("  ✓ 支持单股票和多股票订阅")
    print("  ✓ 完整的订阅生命周期管理")

    print("\n【推荐使用场景】")
    print("  场景1：实时监控单只股票 → 使用 api.subscribe()")
    print("  场景2：监控多只股票     → 使用 api.subscribe_whole()")
    print("  场景3：持续监控行情     → 配合 api.run_forever()")


def lesson_06_common_pitfalls():
    """第6课：常见问题及解决方案"""
    print_section("第6课：常见问题及解决方案")

    print("""
❓ 问题1：订阅后获取不到五档数据

原因：
  - 等待时间不够（数据还没推送完成）
  - 字段名错误（应该是askPrice/bidPrice，不是bid1/ask1）
  - 数据是数组格式，需要索引访问

解决：
  ✓ 方式A：使用轮询检查（推荐）
    def wait_for_tick(code, timeout=3.0):
        start = time.time()
        while time.time() - start < timeout:
            tick_data = xt.get_full_tick([code])
            if tick_data and code in tick_data:
                ask_price = tick_data[code].get('askPrice', [])
                if ask_price and len(ask_price) > 0:
                    return tick_data[code]
            time.sleep(0.1)
        return None

  ✓ 方式B：固定等待（简单但不推荐）
    time.sleep(2.0)  # 保守估计，可能浪费时间

  ✓ 使用正确的字段名和索引
    ask_price[0]  # 获取卖一价

💡 最佳实践：
  - 如果只需要一次性获取：使用轮询检查
  - 如果需要持续监控：使用回调函数（第3课）

---

❓ 问题2：为什么要用轮询而不是固定等待？

原因：
  - 固定等待(time.sleep(2))：可能等太久或不够
  - 轮询检查：数据到了立即返回，不浪费时间

对比：
  方式           | 响应时间     | 代码复杂度 | 推荐度
  ---------------|-------------|-----------|--------
  固定等待2秒    | 2秒（固定）  | 简单      | ⭐⭐
  固定等待0.5秒  | 0.5秒       | 简单      | ⭐⭐⭐
  轮询检查       | 0.1-0.3秒   | 中等      | ⭐⭐⭐⭐⭐
  回调函数       | 0秒（实时） | 简单      | ⭐⭐⭐⭐⭐

💡 推荐选择：
  - 持续监控行情 → 使用回调函数
  - 一次性获取   → 使用轮询检查

---

❓ 问题3：非交易时间数据为空

原因：
  - 非交易时间（周末、夜间）五档数据为0是正常的
  - QMT模拟账户可能限制数据

解决：
  ✓ 在交易时间（9:30-15:00）内运行
  ✓ 检查QMT客户端是否显示五档数据
  ✓ 使用实盘账户测试

---

❓ 问题4：回调函数不执行

原因：
  - 订阅后没有保持程序运行
  - 回调函数定义不正确
  - 使用了错误的订阅接口

解决：
  ✓ 使用 subscribe_whole_quote() 订阅
  ✓ 检查回调函数签名是否正确
  ✓ 程序需要保持运行状态接收推送

---

❓ 问题5：获取的数据总是旧的

原因：
  - 只获取了一次，没有持续订阅
  - 没有使用回调函数

解决：
  ✓ 使用回调函数持续接收推送
  ✓ 或者定期重新获取数据
    """)


def lesson_07_practical_exercise():
    """第7课：实战练习"""
    print_section("第7课：实战练习")

    api = easy_xt.get_api()
    api.init_data()

    print("\n练习1：监控单只股票的实时行情")
    print("-" * 70)

    code = '000001.SZ'
    print(f"股票: {code}（平安银行）")
    print("目标: 实时显示最新价和买卖价差\n")

    # 订阅
    xt.subscribe_quote(code, period='tick')

    # 监控5次
    for i in range(5):
        time.sleep(1)

        tick_data = xt.get_full_tick([code])
        if tick_data and code in tick_data:
            tick = tick_data[code]
            last_price = tick.get('lastPrice', 0)

            ask_price = tick.get('askPrice', [])
            bid_price = tick.get('bidPrice', [])

            if len(ask_price) > 0 and len(bid_price) > 0:
                spread = ask_price[0] - bid_price[0]
                print(f"[{i+1}] {datetime.now().strftime('%H:%M:%S')} "
                      f"最新价: {last_price:.2f}  价差: {spread:.3f}")

    print("\n✓ 练习1完成")

    print("\n\n练习2：批量获取多只股票的五档行情")
    print("-" * 70)

    codes = ['000001.SZ', '000002.SZ', '600000.SH']
    print(f"股票列表: {codes}")
    print("目标: 获取这些股票的五档行情\n")

    # 批量订阅
    for code in codes:
        xt.subscribe_quote(code, period='tick')
    print("✓ 批量订阅完成")

    # 等待推送
    time.sleep(2.0)

    # 获取数据
    order_books = api.get_order_book(codes)

    if order_books is not None and not order_books.empty:
        print(f"\n{'股票代码':<12} {'最新价':<10} {'买一':<10} {'卖一':<10} {'价差':<10}")
        print("-" * 70)

        for _, row in order_books.iterrows():
            code = row['code']
            last_price = row['lastPrice']
            bid1 = row['bid1']
            ask1 = row['ask1']
            spread = ask1 - bid1 if bid1 > 0 and ask1 > 0 else 0

            print(f"{code:<12} {last_price:<10.2f} {bid1:<10.2f} {ask1:<10.2f} {spread:<10.3f}")

    print("\n✓ 练习2完成")

    print("\n\n练习3：使用回调函数实时监控（进阶）")
    print("-" * 70)

    code = '000001.SZ'
    print(f"股票: {code}")
    print("目标: 使用回调函数实时监控价格变化")
    print("\n提示：这个练习需要理解回调函数，可以参考第3课的内容")
    print("代码框架：")

    example_code = '''
def monitor_stock_with_callback(code='000001.SZ', duration=10):
    """使用回调函数监控股票"""

    price_history = []

    def on_tick(data):
        if code in data:
            tick = data[code]
            price = tick.get('lastPrice', 0)

            price_history.append(price)

            print(f"[推送] {datetime.now().strftime('%H:%M:%S')} 价格: {price:.2f}")

    # 订阅
    xt.subscribe_whole_quote(code_list=[code], callback=on_tick)

    # 持续运行
    start_time = time.time()
    while time.time() - start_time < duration:
        time.sleep(0.1)

    # 分析
    if len(price_history) > 0:
        max_price = max(price_history)
        min_price = min(price_history)
        print(f"\\n统计: 最高 {max_price:.2f}, 最低 {min_price:.2f}")

# 运行: monitor_stock_with_callback('000001.SZ', duration=10)
'''

    print(example_code)

    print("\n✓ 代码框架已提供，可以作为参考实现")


def main():
    """主函数"""
    print("🎓 EasyXT订阅机制详解")
    print("=" * 70)
    print("本课程将深入讲解xtquant的订阅机制，帮助您正确获取实时行情")
    print("\n建议：")
    print("  1. 按顺序学习各课程")
    print("  2. 在交易时间内运行以获得最佳效果")
    print("  3. 实践每个课程中的代码示例")

    # 运行所有课程
    lessons = [
        ("第1课：订阅机制的核心概念", lesson_01_subscription_concept),
        ("第2课：订阅方式 vs 主动获取", lesson_02_subscribe_vs_active),
        ("第3课：使用回调函数接收推送", lesson_03_callback_function),
        ("第4课：正确获取五档行情数据", lesson_04_order_book_data),
        ("第5课：使用EasyXT简化接口", lesson_05_easy_xt_wrapper),
        ("第5.5课：使用EasyXT的订阅接口（新功能）", lesson_05_5_easy_xt_subscribe),
        ("第6课：常见问题及解决方案", lesson_06_common_pitfalls),
        ("第7课：实战练习", lesson_07_practical_exercise),
    ]

    for title, lesson_func in lessons:
        try:
            lesson_func()

            # 询问是否继续
            if not (len(sys.argv) > 1 and '--auto' in sys.argv):
                input("\n按回车键继续下一课...")
            else:
                print(f"\n✓ {title} 完成，自动继续...")
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n\n学习已中断")
            break
        except Exception as e:
            print(f"\n❌ 课程执行出错: {e}")
            import traceback
            traceback.print_exc()

            if not (len(sys.argv) > 1 and '--auto' in sys.argv):
                input("按回车键继续...")

    print("\n" + "=" * 70)
    print("🎉 订阅机制课程完成！")
    print("\n你已经学会了：")
    print("  ✓ 第1课: 订阅机制的核心概念")
    print("  ✓ 第2课: 订阅方式 vs 主动获取")
    print("  ✓ 第3课: 使用回调函数接收推送")
    print("  ✓ 第4课: 正确获取五档行情数据")
    print("  ✓ 第5课: 使用EasyXT简化接口")
    print("  ✓ 第5.5课: 使用EasyXT的订阅接口（新功能）")
    print("  ✓ 第6课: 常见问题及解决方案")
    print("  ✓ 第7课: 实战练习")

    print("\n接下来可以学习：")
    print("  - 回顾 01_基础入门.py - 巩固基础")
    print("  - 学习 02_交易基础.py - 学习交易功能")
    print("  - 学习 03_高级交易.py - 学习高级功能")
    print("  - 使用 tools/诊断tick字段.py - 诊断数据问题")

    print("\n💡 提示：")
    print("  - 回调函数方式：数据来了自动执行，无需等待（推荐）")
    print("  - 主动获取方式：使用轮询检查，数据到了立即返回")
    print("  - 五档数据需要正确使用 askPrice/bidPrice 数组")
    print("  - 使用EasyXT封装的接口可以简化操作")


if __name__ == "__main__":
    main()
