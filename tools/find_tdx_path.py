import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)
"""

自动查找通达信安装路径

"""



import sys

from pathlib import Path



logger.info("="*70)
logger.info("  通达信路径查找工具")
logger.info("="*70)


# 常见的通达信安装路径

common_paths = [

    r"D:\new_tdx64.2",

    r"D:\new_tdx64",

    r"C:\new_tdx64",

    r"H:\new_tdx64",

    r"E:\new_tdx64",

    r"D:\通达信",

    r"C:\Program Files\new_tdx64",

    r"C:\Program Files (x86)\new_tdx64",

]



logger.info("\n[正在查找通达信安装路径...]\n")


found_paths = []



for tdx_path in common_paths:

    path = Path(tdx_path)



    # 检查路径是否存在

    if path.exists():

        logger.info(f"[OK] 找到: {tdx_path}")


        # 检查是否有自选股文件

        zxg_file = path / "T0002" / "blocknew" / "zxg.blk"

        if zxg_file.exists():

            logger.info(f"     └─ 自选股文件存在: {zxg_file}")
            found_paths.append(tdx_path)

        else:

            logger.warning(f"     └─ [WARN] 自选股文件不存在")
    else:

        logger.info(f"[空] {tdx_path}")


# 汇总

logger.info("\n" + "="*70)
logger.info("  查找结果")
logger.info("="*70)


if found_paths:

    logger.info(f"\n[成功] 找到 {len(found_paths)} 个可用的通达信安装:\n")


    for i, path in enumerate(found_paths, 1):

        logger.info(f"{i}. {path}")


        # 显示配置代码

        logger.info(f"\n   配置代码:")
        logger.info(f"   tdx_path = Path(r\"{path}\")")
        print()



    # 推荐使用第一个

    recommended = found_paths[0]

    logger.info("="*70)
    logger.info("  [推荐配置]")
    logger.info("="*70)
    logger.info(f"\n在 tools/parse_tdx_zixg.py 第74行修改为:")
    logger.info(f"  tdx_path = Path(r\"{recommended}\")")


else:

    logger.info("\n[未找到] 自动查找未找到通达信安装路径")
    logger.info("\n[手动设置]")
    logger.info("1. 找到您的通达信安装目录")
    logger.info("2. 在 tools/parse_tdx_zixg.py 第74行修改路径")
    logger.info("3. 格式: tdx_path = Path(r\"您的路径\")")


    logger.info("\n[如何找到通达信路径]")
    logger.info("方法1: 右键通达信图标 → 属性 → 起始位置")
    logger.info("方法2: 在通达信中按 帮助 → 关于，查看安装路径")
    logger.info("方法3: 在文件资源管理器中搜索 tdxw.exe")


logger.info("\n" + "="*70)
