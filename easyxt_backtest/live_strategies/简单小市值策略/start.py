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
    print("=" * 60)
    print("  Simple Small Cap Strategy - Live Trading")
    print("  简单小市值策略 - 实盘交易")
    print("=" * 60)
    print("")

def check_python():
    """检查Python版本"""
    print("[INFO] Python Version:")
    print(f"       {sys.version}")
    print("")

def check_config():
    """检查配置文件"""
    config_path = Path(__file__).parent.parent.parent.parent / 'config' / 'unified_config.json'
    if config_path.exists():
        print(f"[OK] Config file: {config_path}")
    else:
        print("[WARN] Config file not found")
    print("")

def run_strategy():
    """运行策略"""
    print("=" * 60)
    print("  Starting Strategy...")
    print("  启动策略...")
    print("=" * 60)
    print("")

    # 运行main.py
    main_path = Path(__file__).parent / 'main.py'
    try:
        subprocess.run([sys.executable, str(main_path)], check=True)
    except KeyboardInterrupt:
        print("\n[INFO] User interrupted")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Strategy failed with code: {e.returncode}")
        return 1
    return 0

def main():
    """主函数"""
    print_header()
    check_python()
    check_config()

    exit_code = run_strategy()

    print("")
    print("=" * 60)
    print("  Program Exit")
    print("  程序退出")
    print("=" * 60)
    print("")

    input("Press Enter to exit... (按回车键退出...)")

    return exit_code

if __name__ == "__main__":
    sys.exit(main() or 0)
