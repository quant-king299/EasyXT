#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI应用快速启动脚本
用于启动EasyXT量化交易策略管理平台
"""

import sys
import os

def main():
    # 获取项目根目录
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # 添加项目路径到sys.path
    sys.path.insert(0, project_root)
    
    print("=" * 70)
    print("EasyXT量化交易策略管理平台 - 启动器")
    print("=" * 70)
    
    # 检查依赖
    print("\n[*] 检查依赖...")

    dependencies = {
        'PyQt5': 'PyQt5基础库',
        'pandas': 'DataFrame数据处理',
        'numpy': '数值计算库',
    }

    missing_deps = []
    for package, description in dependencies.items():
        try:
            __import__(package)
            print(f"  [OK] {package:<15} - {description}")
        except ImportError:
            print(f"  [FAIL] {package:<15} - {description} (未安装)")
            missing_deps.append(package)

    if missing_deps:
        print(f"\n[WARNING] 缺少以下依赖: {', '.join(missing_deps)}")
        print("请运行以下命令安装:")
        print(f"  pip install {' '.join(missing_deps)}")
        return False

    # 检查转换器
    print("\n[*] 检查转换器...")
    try:
        from code_converter.converters.jq_to_ptrade_unified_v3 import JQToPtradeUnifiedConverter as JQToPtradeConverter
        converter = JQToPtradeConverter()
        print(f"  [OK] 转换器已加载")
        print(f"    - API映射规则: {len(converter.api_mapping)} 条")
        print(f"    - 不支持的API: {len(converter.unsupported_apis)} 个")
    except ImportError as e:
        print(f"  [FAIL] 转换器导入失败: {e}")
        return False

    # 检查GUI组件
    print("\n[*] 检查GUI组件...")
    required_files = [
        'gui_app/main_window.py',
        'gui_app/widgets/jq_to_ptrade_widget.py',
    ]

    for file_path in required_files:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            print(f"  [OK] {file_path}")
        else:
            print(f"  [FAIL] {file_path} (不存在)")
            return False

    # 所有检查通过，启动应用
    print("\n[OK] 所有检查通过，正在启动应用...\n")
    print("=" * 70)
    print()
    
    # 动态导入并启动应用
    try:
        from gui_app.main_window import main as gui_main
        gui_main()
    except Exception as e:
        print(f"[ERROR] 启动应用失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
