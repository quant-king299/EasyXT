#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SimHei字体自动安装工具
解决matplotlib中文字体显示问题
"""

import os
import sys
import shutil
import matplotlib

def print_header():
    print("=" * 50)
    print("     SimHei 字体自动安装工具")
    print("=" * 50)
    print()

def check_font_source():
    """检查SimHei字体源文件"""
    print("[1/5] 检查SimHei字体文件...")
    source_path = r"C:\Windows\Fonts\simhei.ttf"

    if not os.path.exists(source_path):
        print(f"  ✗ 错误：找不到字体文件 {source_path}")
        print("  请确保Windows系统中有SimHei字体")
        return False

    print(f"  ✓ 找到SimHei字体文件")
    return True

def get_font_destination():
    """获取matplotlib字体目录"""
    print("[2/5] 查找matplotlib字体目录...")

    font_dir = os.path.join(
        os.path.dirname(matplotlib.__file__),
        'mpl-data',
        'fonts',
        'ttf'
    )

    if not os.path.exists(font_dir):
        print(f"  ✗ 错误：找不到字体目录 {font_dir}")
        return None

    print(f"  ✓ 字体目录: {font_dir}")
    return font_dir

def copy_font(source, dest_dir):
    """复制字体文件"""
    print("[3/5] 复制SimHei字体...")

    dest_file = os.path.join(dest_dir, 'simhei.ttf')

    try:
        shutil.copy(source, dest_file)
        print(f"  ✓ 字体已复制到: {dest_file}")
        return True
    except Exception as e:
        print(f"  ✗ 复制失败: {e}")
        return False

def clear_cache():
    """清除matplotlib缓存"""
    print("[4/5] 清除matplotlib缓存...")

    try:
        cache_dir = matplotlib.get_cachedir()
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir, ignore_errors=True)
            print(f"  ✓ 缓存已清除: {cache_dir}")
        else:
            print(f"  ℹ 缓存目录不存在，无需清除")
        return True
    except Exception as e:
        print(f"  ⚠ 清除缓存失败: {e}")
        print(f"  ℹ 这不影响使用，可以忽略")
        return True  # 缓存清除失败不影响使用

def verify_installation():
    """验证字体安装"""
    print("[5/5] 验证字体安装...")

    try:
        import matplotlib.pyplot as plt
        plt.rcParams['font.sans-serif'] = ['SimHei']

        # 测试绘制
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        fig = Figure(figsize=(5, 4))
        canvas = FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)
        ax.set_title('测试中文字体净值曲线')
        ax.plot([1, 2, 3], [1, 4, 2])
        canvas.draw()

        print("  ✓ 字体验证通过，可以正常使用")
        return True

    except Exception as e:
        print(f"  ⚠ 字体验证警告: {e}")
        print(f"  ℹ 字体可能已安装，但验证过程出现问题")
        print(f"  ℹ 建议运行程序测试实际效果")
        return True  # 不影响程序运行

def main():
    print_header()

    # 检查字体源文件
    source_font = r"C:\Windows\Fonts\simhei.ttf"
    if not check_font_source():
        return 1
    print()

    # 获取目标目录
    font_dir = get_font_destination()
    if not font_dir:
        return 1
    print()

    # 复制字体
    if not copy_font(source_font, font_dir):
        return 1
    print()

    # 清除缓存
    clear_cache()
    print()

    # 验证安装
    verify_installation()
    print()

    print("=" * 50)
    print("         安装完成！")
    print("=" * 50)
    print()
    print("现在可以运行: python run_gui.py")
    print()

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n用户中断安装")
        sys.exit(1)
    except Exception as e:
        print(f"\n安装过程出现错误: {e}")
        sys.exit(1)
