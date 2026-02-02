#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
511380.SH 网格策略回测启动脚本
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "gui_app"))

from PyQt5.QtWidgets import QApplication
from gui_app.widgets.grid_backtest_widget import GridBacktestWidget


def main():
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyle('Fusion')

    # 创建主窗口
    widget = GridBacktestWidget()
    widget.resize(1200, 800)
    widget.setWindowTitle("511380.SH 债券ETF网格策略回测系统")
    widget.show()

    print("="*60)
    print("511380.SH 网格策略回测系统已启动")
    print("="*60)
    print("\n使用说明：")
    print("1. 在【参数配置】选项卡中设置回测参数")
    print("2. 点击【运行回测】查看单个参数的回测结果")
    print("3. 在【参数优化】选项卡中进行参数优化")
    print("4. 查看优化结果并选择最佳参数")
    print("\n建议：")
    print("- 首次使用先运行参数优化，找到最佳参数组合")
    print("- 债券ETF波动小，建议价格区间设置在1-3%")
    print("- 网格数量建议在10-20之间")
    print("- 查看交易日志了解策略执行情况")
    print("\n" + "="*60 + "\n")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
