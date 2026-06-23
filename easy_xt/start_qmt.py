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

        success = auto_login.login(restart=False, timeout=60)

        if success:
            print("\n" + "=" * 60)
            print("[OK] 登录成功！QMT 现在可以正常使用了")
            print("=" * 60)
            return 0
        else:
            print("\n" + "=" * 60)
            print("[X] 登录失败！请检查以下内容：")
            print("  1. .env 文件中的配置是否正确")
            print("  2. QMT 可执行文件路径是否正确")
            print("  3. 密码是否正确")
            print("  4. 网络连接是否正常")
            print("=" * 60)
            return 1

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
