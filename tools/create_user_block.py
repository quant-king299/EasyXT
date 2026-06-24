import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)
"""

通达信自选股转自定义板块工具

将通达信默认自选股转换为API可读取的自定义板块

"""



import sys

from pathlib import Path

from datetime import datetime



# 添加项目路径

project_root = Path(__file__).parent.parent

sys.path.insert(0, str(project_root))

sys.path.insert(0, str(project_root / "easy_xt"))



from easy_xt.tdx_client import TdxClient





def create_custom_sector():

    """创建自定义板块"""

    logger.info("="*70)
    logger.info("  通达信自定义板块创建工具")
    logger.info("="*70)
    logger.info(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


    with TdxClient() as client:

        tq = client.tq



        # 步骤1: 创建新的自定义板块

        logger.info("[步骤1] 创建自定义板块")
        logger.info("-"*70)


        sector_name = "量化选股"  # 板块名称

        stocks = ['605168.SH', '000333.SZ', '600519.SH']  # 测试股票



        logger.info(f"  板块名称: '{sector_name}'")
        logger.info(f"  添加股票: {stocks}")


        try:

            result = tq.send_user_block(

                block_code=sector_name,

                stocks=stocks,

                show=True

            )



            logger.info(f"\n  [OK] 创建成功")
            logger.info(f"  返回结果: {result}")


        except Exception as e:

            logger.error(f"  [ERROR] 创建失败: {e}")
            return



        # 步骤2: 验证板块是否创建成功

        logger.info("\n[步骤2] 验证板块")
        logger.info("-"*70)


        import time

        time.sleep(1)  # 等待一下



        # 尝试获取板块

        try:

            retrieved_stocks = tq.get_stock_list_in_sector(sector_name)



            if retrieved_stocks and len(retrieved_stocks) > 0:

                logger.info(f"  [OK] 板块创建成功！")
                logger.info(f"  板块名称: '{sector_name}'")
                logger.info(f"  股票数量: {len(retrieved_stocks)}")
                logger.info(f"  股票列表: {retrieved_stocks}")
            else:

                logger.warning(f"  [WARN] 板块创建后仍无法读取")


        except Exception as e:

            logger.error(f"  [ERROR] 验证失败: {e}")


        # 步骤3: 检查用户板块列表

        logger.info("\n[步骤3] 检查用户板块列表")
        logger.info("-"*70)


        try:

            user_sectors = tq.get_user_sector()



            if user_sectors:

                logger.info(f"  [OK] 找到 {len(user_sectors)} 个用户板块:")
                for i, sector in enumerate(user_sectors, 1):

                    logger.info(f"    {i}. {sector}")


                if sector_name in user_sectors:

                    logger.info(f"\n  [成功] '{sector_name}' 已在用户板块列表中")
            else:

                logger.info(f"  [INFO] 用户板块列表仍为空")
                logger.info(f"  [提示] 这可能需要重启通达信才能显示")


        except Exception as e:

            logger.error(f"  [ERROR] {e}")


        logger.info("\n" + "="*70)
        logger.info("  使用说明")
        logger.info("="*70)


        print(f"""

成功创建自定义板块: '{sector_name}'



在交易脚本中使用:



    from easy_xt.tdx_client import TdxClient



    with TdxClient() as client:

        stocks = client.get_sector_stocks('{sector_name}')

        logger.info(f"获取到 {{len(stocks)}} 只股票")


添加更多股票到板块:



    # 方法1: 使用send_user_block覆盖（会替换所有股票）

    tq.send_user_block(

        block_code='{sector_name}',

        stocks=['605168.SH', '000333.SZ', '600519.SH', '000001.SZ'],

        show=True

    )



    # 方法2: 在通达信中手动添加

    # 1. 按F6打开自选股设置

    # 2. 找到'{sector_name}'板块

    # 3. 右键 -> 添加股票

        """)





if __name__ == "__main__":

    create_custom_sector()

