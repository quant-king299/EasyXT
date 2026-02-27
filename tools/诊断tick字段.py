"""
检查tick数据的实际字段
帮助找出五档数据的正确字段名
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import xtquant.xtdata as xt
import time


def check_tick_fields(code='000001.SZ'):
    """检查tick数据的所有字段"""
    print("=" * 60)
    print("检查tick数据的实际字段")
    print("=" * 60)

    print(f"\n测试股票: {code}")

    # 订阅
    print("\n订阅tick行情...")
    result = xt.subscribe_quote(code, period='tick')
    print(f"订阅返回值: {result}")

    # 等待数据推送
    print("\n等待数据推送（3秒）...")
    time.sleep(3.0)

    # 获取tick数据
    print("\n获取tick数据...")
    tick_data = xt.get_full_tick([code])

    if tick_data and code in tick_data:
        tick_info = tick_data[code]

        print(f"\n✓ 获取到tick数据")
        print(f"\ntick_info类型: {type(tick_info)}")

        if isinstance(tick_info, dict):
            print(f"\ntick_info包含 {len(tick_info)} 个字段：\n")

            # 按字段名排序显示
            for key in sorted(tick_info.keys()):
                value = tick_info[key]
                # 显示不同类型的值
                if isinstance(value, (int, float)):
                    if key.startswith('bid') or key.startswith('ask'):
                        # 五档相关字段
                        print(f"  {key:20s} = {value:15.2f}  ⬅️ 五档字段")
                    elif value == 0:
                        print(f"  {key:20s} = {value:15}  ⚠️ 值为0")
                    else:
                        print(f"  {key:20s} = {value:15.2f}")
                else:
                    print(f"  {key:20s} = {value}")

            # 专门显示五档字段
            print(f"\n" + "=" * 60)
            print("五档相关字段检查：")
            print("=" * 60)

            bid_ask_fields = []
            for key in tick_info.keys():
                if 'bid' in key.lower() or 'ask' in key.lower():
                    bid_ask_fields.append(key)

            if bid_ask_fields:
                print(f"\n找到 {len(bid_ask_fields)} 个五档相关字段：")
                for key in sorted(bid_ask_fields):
                    value = tick_info[key]
                    if isinstance(value, (int, float)) and value != 0:
                        print(f"  ✓ {key:20s} = {value:.2f}")
                    else:
                        print(f"  ⚠️ {key:20s} = {value}")
            else:
                print("\n⚠️ 未找到任何五档相关字段！")
                print("这说明当前tick数据不包含五档信息")

            # 尝试其他可能的字段名
            print(f"\n" + "=" * 60)
            print("尝试其他可能的字段名：")
            print("=" * 60)

            possible_names = [
                # 标准字段名
                'bid1', 'bid2', 'bid3', 'bid4', 'bid5',
                'ask1', 'ask2', 'ask3', 'ask4', 'ask5',
                'bidVol1', 'bidVol2', 'bidVol3', 'bidVol4', 'bidVol5',
                'askVol1', 'askVol2', 'askVol3', 'askVol4', 'askVol5',
                # 其他可能的命名
                'bid_price1', 'bid_price2', 'ask_price1', 'ask_price2',
                'buy1', 'buy2', 'sell1', 'sell2',
                'buy_price1', 'sell_price1',
                'BidPrice1', 'AskPrice1',
                'bp1', 'ap1', 'bv1', 'av1',
            ]

            found_alt = False
            for name in possible_names:
                if name in tick_info and tick_info[name] != 0:
                    print(f"  ✓ {name:20s} = {tick_info[name]}")
                    found_alt = True

            if not found_alt:
                print("  ⚠️ 未找到其他有效的五档字段名")

            # 尝试使用get_l2_quote接口
            print(f"\n" + "=" * 60)
            print("尝试使用get_l2_quote接口：")
            print("=" * 60)

            try:
                if hasattr(xt, 'get_l2_quote'):
                    l2_data = xt.get_l2_quote([code])
                    print(f"✓ get_l2_quote接口存在")
                    print(f"返回类型: {type(l2_data)}")

                    if l2_data:
                        print(f"返回数据: {l2_data}")

                        if isinstance(l2_data, dict) and code in l2_data:
                            l2_info = l2_data[code]
                            print(f"\nL2数据字段: {list(l2_info.keys()) if isinstance(l2_info, dict) else l2_info}")
                    else:
                        print("⚠️ get_l2_quote返回空数据")
                else:
                    print("⚠️ get_l2_quote接口不存在")
            except Exception as e:
                print(f"✗ get_l2_quote调用失败: {e}")

        else:
            print(f"\ntick_info不是字典类型，无法分析字段")
            print(f"内容: {tick_info}")

    else:
        print(f"\n✗ 未获取到tick数据")


def try_get_market_data(code='000001.SZ'):
    """尝试使用get_market_data获取五档数据"""
    print("\n" + "=" * 60)
    print("尝试使用get_market_data接口")
    print("=" * 60)

    try:
        # 尝试获取tick数据
        data = xt.get_market_data(
            stock_list=[code],
            period='tick',
            count=1
        )

        print(f"\nget_market_data返回: {type(data)}")

        if data:
            print(f"数据结构: {data}")

            if isinstance(data, dict) and code in data:
                tick_array = data[code]
                print(f"\n{code}的tick数组类型: {type(tick_array)}")

                if hasattr(tick_array, '__len__') and len(tick_array) > 0:
                    first_tick = tick_array[0]
                    print(f"\n第一条tick类型: {type(first_tick)}")

                    if isinstance(first_tick, dict):
                        print(f"字段: {list(first_tick.keys())}")

                        # 检查五档字段
                        print(f"\n五档数据:")
                        for key in sorted(first_tick.keys()):
                            if 'bid' in key.lower() or 'ask' in key.lower():
                                value = first_tick[key]
                                if value != 0:
                                    print(f"  {key}: {value}")
                                else:
                                    print(f"  {key}: 0 (空)")

    except Exception as e:
        print(f"✗ get_market_data失败: {e}")


def main():
    """主函数"""
    print("🔍 检查tick数据的实际字段")
    print("=" * 60)

    code = input("\n请输入股票代码 (默认000001.SZ): ").strip() or "000001.SZ"

    check_tick_fields(code)
    try_get_market_data(code)

    print("\n" + "=" * 60)
    print("检查完成")
    print("\n💡 根据以上检查结果，我们可以确定：")
    print("  1. tick数据实际包含哪些字段")
    print("  2. 五档数据的正确字段名")
    print("  3. 是否需要使用其他接口获取五档数据")


if __name__ == "__main__":
    main()
