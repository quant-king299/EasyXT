import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)
"""

xtquant 安装检查脚本

用于检查 xtquant 是否正确安装，并给出安装指引

"""

import sys

import os

import io



# 修复 Windows 控制台编码问题

if sys.platform == 'win32':

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')



# 确保项目根目录在 sys.path 中（xtquant 可能放在项目根目录下）

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if _project_root not in sys.path:

    sys.path.insert(0, _project_root)





def print_banner():

    """打印横幅"""

    logger.info("=" * 70)
    logger.info("EasyXT - xtquant 依赖检查工具")
    logger.info("=" * 70)
    print()





def check_xtquant():

    """检查 xtquant 是否正确安装"""

    logger.info("正在检查 xtquant 安装状态...\n")


    # 检查 1：能否导入 xtquant

    try:

        import xtquant

        logger.info("✓ xtquant 模块可以导入")
    except ImportError as e:

        logger.info("✗ 无法导入 xtquant 模块")
        logger.info(f"  错误信息: {e}")
        return False



    # 检查 2：能否导入 xtdata（核心数据模块）

    try:

        from xtquant import xtdata

        logger.info("✓ xtquant.xtdata 可以导入（核心数据模块）")
    except ImportError as e:

        logger.info("✗ 无法导入 xtquant.xtdata（文件不完整或版本不匹配）")
        logger.info(f"  错误信息: {e}")
        logger.info("\n这是最常见的错误！通常是因为：")
        logger.info("  - GitHub 上的 xtquant 文件不完整（大文件被截断）")
        logger.info("  - 使用了 pip 安装的官方版本（不兼容）")
        return False



    # 检查 3：能否导入 datacenter（投研版交易组件，可选）

    try:

        from xtquant import datacenter

        logger.info("✓ xtquant.datacenter 可以导入（投研版交易组件）")
    except ImportError:

        logger.info("ℹ xtquant.datacenter 不可用（仅投研版需要，miniQMT 不影响使用）")


    logger.info("\n" + "=" * 70)
    logger.info("✓ 所有检查通过！xtquant 安装正确")
    logger.info("=" * 70)
    return True





def show_install_guide():

    """显示安装指南"""

    logger.info("\n" + "=" * 70)
    logger.info("请按以下步骤安装 xtquant：")
    logger.info("=" * 70)
    print()

    logger.info("方法 1：从 GitHub Releases 下载（推荐）")
    logger.info("-" * 70)
    logger.info("1. 访问下载页面：")
    logger.info("   https://github.com/quant-king299/EasyXT/releases/tag/xueqiu_follow-xtquant-v1.0")
    print()

    logger.info("2. 下载完整版 xtquant 压缩包")
    print()

    logger.info("3. 解压到指定目录，例如：")
    logger.info("   - C:\\xtquant_special")
    logger.info("   - D:\\tools\\xtquant")
    print()

    logger.info("4. 设置环境变量（重启终端生效）：")
    logger.info("   PowerShell：")
    logger.info("   setx XTQUANT_PATH \"C:\\xtquant_special\"")
    print()

    logger.info("   CMD：")
    logger.info("   setx XTQUANT_PATH \"C:\\xtquant_special\"")
    print()

    logger.info("方法 2：复制本地完整版本")
    logger.info("-" * 70)
    logger.info("如果你已经有完整版本的 xtquant：")
    logger.info("1. 复制 xtquant 文件夹到 Python 的 site-packages 目录")
    logger.info("2. 或者将 xtquant 文件夹路径添加到 PYTHONPATH 环境变量")
    print()

    logger.info("方法 3：从 QMT 软件目录复制")
    logger.info("-" * 70)
    logger.info("如果安装了迅投 QMT：")
    logger.info("1. 找到 QMT 安装目录，如：")
    logger.info("   D:\\国金证券QMT交易端\\userdata_mini\\Python\\")
    logger.info("2. 复制 xtquant 文件夹到 Python site-packages")
    print()

    logger.info("=" * 70)
    logger.info("安装完成后，重新运行此脚本验证：python check_xtquant.py")
    logger.info("=" * 70)




def main():

    """主函数"""

    print_banner()



    if check_xtquant():

        logger.info("\n✓ 可以继续安装 easy-xt 了！")
        logger.info("  运行: pip install -e .")
        return 0

    else:

        show_install_guide()

        return 1





if __name__ == "__main__":

    sys.exit(main())

