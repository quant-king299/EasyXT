#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EasyXT GUI启动脚本
用于启动聚宽代码转Ptrade的图形界面
"""

import sys
import os

def main():
    """启动GUI应用程序"""
    # 获取项目路径
    project_path = os.path.dirname(os.path.abspath(__file__))
    
    print("正在启动EasyXT量化交易策略管理平台...")
    print("作者微信: www_ptqmt_com")
    print("欢迎关注微信公众号: 王者quant")
    
    try:
        # 更改当前工作目录到项目根目录
        os.chdir(project_path)
        
        # 添加项目路径到sys.path
        sys.path.insert(0, project_path)
        
        # 导入并启动GUI应用
        from gui_app.main_window import main as gui_main
        gui_main()
    except Exception as e:
        print(f"启动GUI应用程序失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()