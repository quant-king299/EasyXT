#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速启动脚本 - 本地数据查看器
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'gui_app' / 'widgets'))

from advanced_data_viewer import AdvancedDataViewer
from PyQt5.QtWidgets import QApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    viewer = AdvancedDataViewer()
    viewer.resize(1400, 900)
    viewer.setWindowTitle("📊 本地数据查看器 - 专业版")
    viewer.show()

    sys.exit(app.exec_())
