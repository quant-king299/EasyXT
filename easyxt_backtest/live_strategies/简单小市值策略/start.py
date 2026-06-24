import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)
#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""

Simple Small Cap Strategy - Launcher

启动脚本

"""



import sys

import subprocess

from pathlib import Path



def print_header():

    """打印标题"""

    print("")

    logger.info("=" * 60)
    logger.info("  Simple Small Cap Strategy - Live Trading")
    logger.info("  简单小市值策略 - 实盘交易")
    logger.info("=" * 60)
    print("")



def check_python():

    """检查Python版本"""

    logger.info("[INFO] Python Version:")
    logger.info(f"       {sys.version}")
    print("")



def check_config():

    """检查配置文件"""

    config_path = Path(__file__).parent.parent.parent.parent / 'config' / 'unified_config.json'

    if config_path.exists():

        logger.info(f"[OK] Config file: {config_path}")
    else:

        logger.warning("[WARN] Config file not found")
    print("")



def run_strategy():

    """运行策略"""

    logger.info("=" * 60)
    logger.info("  Starting Strategy...")
    logger.info("  启动策略...")
    logger.info("=" * 60)
    print("")



    # 运行main.py

    main_path = Path(__file__).parent / 'main.py'

    try:

        subprocess.run([sys.executable, str(main_path)], check=True)

    except KeyboardInterrupt:

        logger.info("\n[INFO] User interrupted")
    except subprocess.CalledProcessError as e:

        logger.error(f"\n[ERROR] Strategy failed with code: {e.returncode}")
        return 1

    return 0



def main():

    """主函数"""

    print_header()

    check_python()

    check_config()



    exit_code = run_strategy()



    print("")

    logger.info("=" * 60)
    logger.info("  Program Exit")
    logger.info("  程序退出")
    logger.info("=" * 60)
    print("")



    input("Press Enter to exit... (按回车键退出...)")



    return exit_code



if __name__ == "__main__":

    sys.exit(main() or 0)

