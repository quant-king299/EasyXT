"""
miniQMT 自动登录启动器

使用方法：
1. 确保已配置 .env 文件中的 QMT 相关参数
2. 运行此脚本：python start_qmt_interactive.py
3. 程序会自动完成登录（验证码自动显示）

登录流程：
1. Tab到密码框
2. 输入密码
3. 按回车（验证码会自动显示）
4. 再按回车提交登录
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
    print("=" * 60)
    print("miniQMT 自动登录工具")
    print("=" * 60)

    try:
        # 创建自动登录实例
        auto_login = QMTAutoLogin()

        # 执行登录
        print(f"\n正在启动 QMT...")
        print(f"QMT路径: {auto_login.exe_path}")
        print("-" * 60)

        # 启动QMT（不自动登录）
        import subprocess
        import time

        print("正在启动QMT进程...")
        proc = subprocess.Popen(auto_login.exe_path)
        time.sleep(5)  # 等待QMT启动

        print("\n" + "=" * 60)
        print("QMT登录说明")
        print("=" * 60)
        print("验证码会自动显示，无需手动输入")
        print("程序会自动完成以下步骤：")
        print("1. Tab到密码框")
        print("2. 输入密码")
        print("3. 按回车（验证码自动显示）")
        print("4. 再按回车提交登录")
        print("=" * 60)

        print("\n正在自动登录...")

        # 使用pyautogui模拟键盘操作
        import pyautogui
        import time

        time.sleep(2)  # 等待窗口激活

        # 正确的登录流程
        print("Step 1: Tab到密码框...")
        pyautogui.press('tab')
        time.sleep(0.8)

        print("Step 2: 输入密码...")
        pyautogui.typewrite(auto_login.password, interval=0.05)
        time.sleep(0.5)

        print("Step 3: 按回车（验证码会自动显示）...")
        pyautogui.press('enter')
        time.sleep(1.0)

        print("Step 4: 再按回车提交登录...")
        pyautogui.press('enter')
        print("已按回车键")

        # 等待登录完成
        print("等待登录完成（5秒）...")
        time.sleep(5)

        print("\n" + "=" * 60)
        print("[OK] 登录流程已完成！")
        print("请检查QMT窗口是否成功登录")
        print("=" * 60)
        return 0

    except ValueError as e:
        print("\n" + "=" * 60)
        print("[X] 配置错误：")
        print(f"  {e}")
        print("\n请按照以下步骤配置：")
        print("  1. 打开 .env 文件（如果没有，从 .env.example 复制）")
        print("  2. 填写以下配置项：")
        print("     - QMT_EXE_PATH: QMT可执行文件完整路径")
        print("     - QMT_PASSWORD: 你的QMT登录密码")
        print("  3. 保存文件后重新运行此脚本")
        print("\n注意：用户ID会自动显示，无需配置")
        print("=" * 60)
        return 1

    except ImportError as e:
        print("\n" + "=" * 60)
        print("[X] 缺少依赖库：")
        print(f"  {e}")
        print("\n请安装必要的依赖：")
        print("  pip install pywinauto pyautogui")
        print("=" * 60)
        return 1

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"[X] 未知错误：{e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
