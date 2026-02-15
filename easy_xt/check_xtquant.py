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


def print_banner():
    """打印横幅"""
    print("=" * 70)
    print("EasyXT - xtquant 依赖检查工具")
    print("=" * 70)
    print()


def check_xtquant():
    """检查 xtquant 是否正确安装"""
    print("正在检查 xtquant 安装状态...\n")

    # 检查 1：能否导入 xtquant
    try:
        import xtquant
        print("✓ xtquant 模块可以导入")
    except ImportError as e:
        print("✗ 无法导入 xtquant 模块")
        print(f"  错误信息: {e}")
        return False

    # 检查 2：能否导入 datacenter（关键组件）
    try:
        from xtquant import datacenter
        print("✓ xtquant.datacenter 可以导入（关键组件）")
    except ImportError as e:
        print("✗ 无法导入 xtquant.datacenter（文件不完整或版本不匹配）")
        print(f"  错误信息: {e}")
        print("\n这是最常见的错误！通常是因为：")
        print("  - GitHub 上的 xtquant 文件不完整（大文件被截断）")
        print("  - 使用了 pip 安装的官方版本（不兼容）")
        return False

    # 检查 3：检查关键文件
    try:
        import xtquant.xtdata as xtdata
        print("✓ xtquant.xtdata 可以导入")
    except ImportError as e:
        print("✗ 无法导入 xtquant.xtdata")
        print(f"  错误信息: {e}")
        return False

    print("\n" + "=" * 70)
    print("✓ 所有检查通过！xtquant 安装正确")
    print("=" * 70)
    return True


def show_install_guide():
    """显示安装指南"""
    print("\n" + "=" * 70)
    print("请按以下步骤安装 xtquant：")
    print("=" * 70)
    print()
    print("方法 1：从 GitHub Releases 下载（推荐）")
    print("-" * 70)
    print("1. 访问下载页面：")
    print("   https://github.com/quant-king299/EasyXT/releases/tag/xueqiu_follow-xtquant-v1.0")
    print()
    print("2. 下载完整版 xtquant 压缩包")
    print()
    print("3. 解压到指定目录，例如：")
    print("   - C:\\xtquant_special")
    print("   - D:\\tools\\xtquant")
    print()
    print("4. 设置环境变量（重启终端生效）：")
    print("   PowerShell：")
    print("   setx XTQUANT_PATH \"C:\\xtquant_special\"")
    print()
    print("   CMD：")
    print("   setx XTQUANT_PATH \"C:\\xtquant_special\"")
    print()
    print("方法 2：复制本地完整版本")
    print("-" * 70)
    print("如果你已经有完整版本的 xtquant：")
    print("1. 复制 xtquant 文件夹到 Python 的 site-packages 目录")
    print("2. 或者将 xtquant 文件夹路径添加到 PYTHONPATH 环境变量")
    print()
    print("方法 3：从 QMT 软件目录复制")
    print("-" * 70)
    print("如果安装了迅投 QMT：")
    print("1. 找到 QMT 安装目录，如：")
    print("   D:\\国金证券QMT交易端\\userdata_mini\\Python\\")
    print("2. 复制 xtquant 文件夹到 Python site-packages")
    print()
    print("=" * 70)
    print("安装完成后，重新运行此脚本验证：python check_xtquant.py")
    print("=" * 70)


def main():
    """主函数"""
    print_banner()

    if check_xtquant():
        print("\n✓ 可以继续安装 easy-xt 了！")
        print("  运行: pip install -e .")
        return 0
    else:
        show_install_guide()
        return 1


if __name__ == "__main__":
    sys.exit(main())
