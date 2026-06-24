import logging

logger = logging.getLogger(__name__)
"""
miniQMT 自动登录启动器

使用方法：
1. 确保已配置 .env 文件中的 QMT 相关参数
2. 运行此脚本：python start_qmt.py
3. 或者：python -m core.auto_login.qmt_login

依赖安装：
pip install pywinauto pyautogui
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.auto_login import QMTAutoLogin


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("miniQMT 自动登录工具")
    logger.info("=" * 60)

    try:
        # 创建自动登录实例
        auto_login = QMTAutoLogin()

        # 执行登录
        logger.info(f"\n正在启动 QMT...")
        logger.info(f"QMT路径: {auto_login.exe_path}")
        logger.info("-" * 60)

        success = auto_login.login(restart=False, timeout=60)

        if success:
            logger.info("\n" + "=" * 60)
            logger.info("[OK] 登录成功！QMT 现在可以正常使用了")
            logger.info("=" * 60)
            return 0
        else:
            logger.info("\n" + "=" * 60)
            logger.info("[X] 登录失败！请检查以下内容：")
            logger.info("  1. .env 文件中的配置是否正确")
            logger.info("  2. QMT 可执行文件路径是否正确")
            logger.info("  3. 密码是否正确")
            logger.info("  4. 网络连接是否正常")
            logger.info("=" * 60)
            return 1

    except ValueError as e:
        logger.info("\n" + "=" * 60)
        logger.info("[X] 配置错误：")
        logger.info(f"  {e}")
        logger.info("\n请按照以下步骤配置：")
        logger.info("  1. 打开 .env 文件（如果没有，从 .env.example 复制）")
        logger.info("  2. 填写以下配置项：")
        logger.info("     - QMT_EXE_PATH: QMT可执行文件完整路径")
        logger.info("     - QMT_PASSWORD: 你的QMT登录密码")
        logger.info("  3. 保存文件后重新运行此脚本")
        logger.info("\n注意：用户ID会自动显示，无需配置")
        logger.info("=" * 60)
        return 1

    except ImportError as e:
        logger.info("\n" + "=" * 60)
        logger.info("[X] 缺少依赖库：")
        logger.info(f"  {e}")
        logger.info("\n请安装必要的依赖：")
        logger.info("  pip install pywinauto pyautogui")
        logger.info("=" * 60)
        return 1

    except Exception as e:
        logger.info("\n" + "=" * 60)
        logger.info(f"[X] 未知错误：{e}")
        logger.info("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
