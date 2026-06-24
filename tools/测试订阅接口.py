import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)
"""

测试EasyXT新增的订阅接口

验证 api.subscribe() 和 api.subscribe_whole() 是否正常工作

"""



import sys

import os

from datetime import datetime



# 添加项目根目录到Python路径

current_dir = os.path.dirname(os.path.abspath(__file__))

parent_dir = os.path.dirname(current_dir)

sys.path.insert(0, parent_dir)



import easy_xt

import time





def test_subscribe_single():

    """测试订阅单只股票"""

    logger.info("=" * 60)
    logger.info("测试1: 订阅单只股票 api.subscribe()")
    logger.info("=" * 60)


    api = easy_xt.get_api()

    if not api.init_data():

        logger.info("❌ 数据服务初始化失败")
        return False



    code = '000001.SZ'

    logger.info(f"\n股票: {code}")


    # 定义回调

    counter = {'count': 0, 'max': 3}



    def on_tick(data):

        if code in data:

            tick_list = data[code]

            # subscribe_whole_quote的回调中，值是tick数组

            if isinstance(tick_list, list) and len(tick_list) > 0:

                tick = tick_list[-1]

            else:

                tick = tick_list

            counter['count'] += 1

            print(f"  [推送 #{counter['count']}] {datetime.now().strftime('%H:%M:%S')} "

                  f"最新价: {tick.get('lastPrice', 0):.2f}")



    # 订阅

    logger.info(f"\n订阅...")
    seq = api.subscribe(code, callback=on_tick)



    if seq > 0:

        logger.info(f"✓ 订阅成功，订阅号: {seq}")


        # 等待推送

        logger.info("等待推送（接收3次）...")
        start = time.time()

        while counter['count'] < counter['max'] and (time.time() - start) < 10:

            time.sleep(0.5)



        if counter['count'] >= counter['max']:

            logger.info(f"✓ 接收到 {counter['count']} 次推送")


        # 取消订阅

        api.unsubscribe(seq)

        logger.info("✓ 已取消订阅")
        return True

    else:

        logger.info("✗ 订阅失败")
        return False





def test_subscribe_multiple():

    """测试订阅多只股票"""

    logger.info("\n" + "=" * 60)
    logger.info("测试2: 订阅多只股票 api.subscribe_whole()")
    logger.info("=" * 60)


    api = easy_xt.get_api()

    if not api.init_data():

        logger.info("❌ 数据服务初始化失败")
        return False



    codes = ['000001.SZ', '000002.SZ']

    logger.info(f"\n股票列表: {codes}")


    # 定义回调

    counter = {'count': 0, 'max': 3}



    def on_tick(data):

        counter['count'] += 1

        logger.info(f"\n  [推送 #{counter['count']}] {datetime.now().strftime('%H:%M:%S')}")
        for code in codes:

            if code in data:

                tick_list = data[code]

                # subscribe_whole_quote的回调中，值是tick数组

                if isinstance(tick_list, list) and len(tick_list) > 0:

                    tick = tick_list[-1]

                else:

                    tick = tick_list

                logger.info(f"    {code}: {tick.get('lastPrice', 0):.2f}")


    # 订阅

    logger.info(f"\n使用 subscribe_whole() 订阅...")
    seq = api.subscribe_whole(codes, callback=on_tick)



    if seq > 0:

        logger.info(f"✓ 订阅成功，订阅号: {seq}")


        # 等待推送

        logger.info("等待推送（接收3次）...")
        start = time.time()

        while counter['count'] < counter['max'] and (time.time() - start) < 10:

            time.sleep(0.5)



        if counter['count'] >= counter['max']:

            logger.info(f"\n✓ 接收到 {counter['count']} 次推送")


        # 取消订阅

        api.unsubscribe(seq)

        logger.info("✓ 已取消订阅")
        return True

    else:

        logger.info("✗ 订阅失败")
        return False





def test_without_callback():

    """测试不使用回调的订阅"""

    logger.info("\n" + "=" * 60)
    logger.info("测试3: 订阅但不使用回调")
    logger.info("=" * 60)


    api = easy_xt.get_api()

    if not api.init_data():

        logger.info("❌ 数据服务初始化失败")
        return False



    code = '000001.SZ'

    logger.info(f"\n股票: {code}")


    # 订阅但不传回调

    logger.info(f"\n订阅（无回调）...")
    seq = api.subscribe(code, callback=None)



    if seq > 0:

        logger.info(f"✓ 订阅成功，订阅号: {seq}")


        # 等待一下让数据推送

        logger.info("等待2秒让数据推送...")
        time.sleep(2.0)



        # 手动获取数据

        import xtquant.xtdata as xt

        tick_data = xt.get_full_tick([code])



        if tick_data and code in tick_data:

            tick = tick_data[code]

            logger.info(f"✓ 手动获取数据成功")
            logger.info(f"  最新价: {tick.get('lastPrice', 0):.2f}")


            # 检查五档

            ask_price = tick.get('askPrice', [])

            bid_price = tick.get('bidPrice', [])



            if len(ask_price) > 0 and len(bid_price) > 0:

                logger.info(f"  买一: {bid_price[0]:.2f}  卖一: {ask_price[0]:.2f}")


        # 取消订阅

        api.unsubscribe(seq)

        logger.info("✓ 已取消订阅")
        return True

    else:

        logger.info("✗ 订阅失败")
        return False





def main():

    """主函数"""

    logger.info("🧪 测试EasyXT订阅接口")
    logger.info("=" * 60)


    results = []



    # 运行测试

    try:

        results.append(("订阅单只股票", test_subscribe_single()))

        time.sleep(1)



        results.append(("订阅多只股票", test_subscribe_multiple()))

        time.sleep(1)



        results.append(("订阅（无回调）", test_without_callback()))



    except KeyboardInterrupt:

        logger.info("\n\n测试已中断")
    except Exception as e:

        logger.info(f"\n❌ 测试出错: {e}")
        import traceback

        traceback.print_exc()



    # 总结

    logger.info("\n" + "=" * 60)
    logger.info("测试总结")
    logger.info("=" * 60)


    for name, success in results:

        status = "✓ 通过" if success else "✗ 失败"

        logger.info(f"  {name:<20} {status}")


    success_count = sum(1 for _, s in results if s)

    logger.info(f"\n通过率: {success_count}/{len(results)}")


    if success_count == len(results):

        logger.info("\n🎉 所有测试通过！订阅接口工作正常")
    else:

        logger.info(f"\n⚠️ 有 {len(results) - success_count} 个测试失败")




if __name__ == "__main__":

    main()

