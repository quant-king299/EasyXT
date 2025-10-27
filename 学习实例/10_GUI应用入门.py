#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EasyXT学习实例 11 - GUI应用入门
学习目标：掌握 gui_app 下各模块的用途、依赖检查，以及如何启动主GUI、简洁交易界面与回测窗口
用法:
  python 学习实例/11_GUI应用入门.py [--auto] [--run]
  - --auto: 自动连续执行，不等待回车
  - --run: 实际启动对应GUI子进程（默认仅讲解与检查，不启动）
"""

import sys
import os
import subprocess
import shutil
from datetime import datetime

# 项目根路径加入 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

GUI_DIR = os.path.join(project_root, "gui_app")
README_PATH = os.path.join(GUI_DIR, "README_Enhanced.md")
MAIN_WINDOW = os.path.join(GUI_DIR, "main_window.py")
SIMPLE_TRADING = os.path.join(GUI_DIR, "trading_interface_simple.py")
BACKTEST_WIDGET = os.path.join(GUI_DIR, "widgets", "backtest_widget.py")
REQUIREMENTS = os.path.join(GUI_DIR, "requirements.txt")

AUTO_MODE = ("--auto" in sys.argv)
RUN_MODE = ("--run" in sys.argv)


def pause():
    if not AUTO_MODE:
        try:
            input("\n按回车键继续下一课...")
        except KeyboardInterrupt:
            print("\n已中断")
            sys.exit(0)


def print_header(title: str):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def safe_exists(path: str) -> bool:
    try:
        return os.path.exists(path)
    except Exception:
        return False


def lesson_01_overview():
    """第1课：GUI应用结构总览"""
    print_header("第1课：GUI应用结构总览")
    print("目标：了解 gui_app 的主要文件与功能定位")

    if not safe_exists(GUI_DIR):
        print(f"✗ 未找到目录: {GUI_DIR}")
        return

    print(f"✓ 发现目录: {GUI_DIR}")

    # 关键文件
    key_files = [
        ("增强说明文档", README_PATH),
        ("专业主窗口", MAIN_WINDOW),
        ("简洁交易界面", SIMPLE_TRADING),
        ("回测窗口组件", BACKTEST_WIDGET),
        ("依赖清单", REQUIREMENTS),
    ]
    for name, path in key_files:
        mark = "✓" if safe_exists(path) else "✗"
        print(f"{mark} {name}: {os.path.relpath(path, project_root)}")

    print("\n简述：")
    print("- main_window.py: PyQt5 专业策略管理平台（参数配置/监控/控制/日志/回测入口）")
    print("- trading_interface_simple.py: 简洁交易界面，快速体验账户/下单/持仓展示")
    print("- widgets/backtest_widget.py: 独立回测窗口组件，可单独运行，支持参数配置/进度/结果分析")
    print("- README_Enhanced.md: 增强版平台说明，列出01-10案例整合与功能清单")
    print("- requirements.txt: GUI所需依赖（PyQt5、pandas、numpy、matplotlib、pyqtgraph 等）")

    pause()


def lesson_02_check_dependencies():
    """第2课：检查依赖与环境"""
    print_header("第2课：检查依赖与环境")

    # Python版本
    print(f"Python版本: {sys.version.split()[0]}")

    # 检查 PyQt5、pandas、numpy、matplotlib、pyqtgraph
    to_check = [
        ("PyQt5", "PyQt5"),
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("matplotlib(可选)", "matplotlib"),
        ("pyqtgraph(可选)", "pyqtgraph"),
    ]
    for label, mod in to_check:
        try:
            __import__(mod)
            print(f"✓ 已安装: {label}")
        except Exception:
            print(f"⚠️ 未检测到: {label}")

    if safe_exists(REQUIREMENTS):
        print(f"\n可参考依赖清单: {os.path.relpath(REQUIREMENTS, project_root)}")
        print("安装示例:")
        print("  pip install -r gui_app/requirements.txt")
    else:
        print("\n未发现 requirements.txt，可按需安装:")
        print("  pip install PyQt5 pandas numpy matplotlib pyqtgraph")

    pause()


def _run_gui_script(py_file: str, title: str):
    """根据 RUN_MODE 决定是否实际启动 GUI 子进程"""
    rel = os.path.relpath(py_file, project_root)
    if not safe_exists(py_file):
        print(f"✗ 未找到 {title}: {rel}")
        return

    print(f"✓ 已找到 {title}: {rel}")
    print("启动方式（命令行示例）:")
    print(f"  python {rel}")

    if not RUN_MODE:
        print("提示：未指定 --run，本课仅讲解不实际拉起窗口。")
        return

    # 实际启动子进程（避免阻塞当前教学脚本）
    try:
        print("🔄 正在启动子进程...")
        creationflags = 0
        # 在 Windows 上用独立窗口更友好，可选：subprocess.CREATE_NEW_CONSOLE
        if os.name == "nt" and hasattr(subprocess, "CREATE_NEW_CONSOLE"):
            creationflags = subprocess.CREATE_NEW_CONSOLE

        subprocess.Popen([sys.executable, py_file],
                         cwd=project_root,
                         creationflags=creationflags)
        print("✓ 已尝试启动，若无界面请检查依赖与环境。")
    except Exception as e:
        print(f"✗ 启动失败: {e}")


def lesson_03_launch_main_window():
    """第3课：启动专业主窗口 main_window.py"""
    print_header("第3课：启动专业主窗口")
    print("功能亮点：")
    print("- 策略参数配置、保存/加载，内置模板与代码生成")
    print("- 策略执行线程、状态监控、持仓/委托实时展示")
    print("- 回测入口：菜单 工具 -> 📊 专业回测")
    print("- EasyXT 连接状态检测，状态栏实时展示")

    _run_gui_script(MAIN_WINDOW, "专业主窗口 (main_window.py)")
    pause()


def lesson_04_launch_simple_trading():
    """第4课：启动简洁交易界面 trading_interface_simple.py"""
    print_header("第4课：启动简洁交易界面")
    print("场景：快速体验账户/持仓/下单流程（EasyXT可用则真实连接，否则有模拟模式）")
    print("操作区：股票代码、数量、价格，支持买入/卖出；顶部可连接/断开交易服务")

    _run_gui_script(SIMPLE_TRADING, "简洁交易界面 (trading_interface_simple.py)")
    pause()


def lesson_05_launch_backtest_widget():
    """第5课：启动回测窗口组件 widgets/backtest_widget.py"""
    print_header("第5课：启动回测窗口组件")
    print("功能：回测参数配置、执行进度、性能概览、详细指标、风险分析、交易记录、HTML报告导出")
    print("数据源：DataManager自动选择 QMT→QStock→AKShare→模拟，可手动切换")

    _run_gui_script(BACKTEST_WIDGET, "回测窗口组件 (widgets/backtest_widget.py)")
    pause()


def lesson_06_tips_and_troubleshooting():
    """第6课：常见问题与建议"""
    print_header("第6课：常见问题与建议")
    print("- 依赖安装：")
    print("  pip install PyQt5 pandas numpy matplotlib pyqtgraph")
    print("- 字体/中文：代码中已设置中文字体，若乱码可检查系统字体。")
    print("- QMT连接：需本机已安装并登录迅投客户端；EasyXT需可用。")
    print("- 运行策略卡住：核对数据周期、网络、以及是否在交易时段。")
    print("- 回测无数据：检查 DataManager 数据源状态，可改用模拟或缩短日期区间。")
    print("- Windows启动新窗口：本脚本以子进程方式尝试拉起独立窗口，防止阻塞/卡死。")

    print("\n进阶：将回测组件嵌入主窗口")
    print("- 在 main_window 的工具菜单已提供入口；也可在自定义窗口中 import BacktestWidget 并嵌入布局。")

    pause()


def main():
    print("🎓 GUI应用入门学习课程")
    print("本课程将带您了解并体验 gui_app 下的主窗口、简洁交易界面与回测窗口")
    print("可选参数：--auto 自动连续执行；--run 实际启动GUI子进程")

    lessons = [
        lesson_01_overview,
        lesson_02_check_dependencies,
        lesson_03_launch_main_window,
        lesson_04_launch_simple_trading,
        lesson_05_launch_backtest_widget,
        lesson_06_tips_and_troubleshooting,
    ]

    for idx, lesson in enumerate(lessons, 1):
        try:
            lesson()
            if AUTO_MODE:
                print(f"\n✓ 第{idx}课完成，自动继续...")
        except KeyboardInterrupt:
            print("\n\n学习已中断")
            break
        except Exception as e:
            print(f"\n课程执行出错: {e}")
            if not AUTO_MODE:
                try:
                    input("按回车键继续...")
                except KeyboardInterrupt:
                    break

    print("\n🎉 GUI应用入门课程完成！")
    print("接下来可以：")
    print("- 在 --run 下实际体验完整交互")
    print("- 阅读 gui_app/README_Enhanced.md 了解增强功能与案例集合")
    print("- 在主窗口中探索策略参数与回测功能")


if __name__ == "__main__":
    main()