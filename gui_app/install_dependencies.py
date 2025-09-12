"""
GUI依赖安装脚本
"""

import subprocess
import sys
import os

def install_package(package):
    """安装包"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("🔧 EasyXT GUI依赖安装工具")
    print("=" * 60)
    
    # 依赖列表
    dependencies = [
        "PyQt5>=5.15.0",
        "pyqtgraph>=0.12.0", 
        "matplotlib>=3.5.0",
        "mplfinance>=0.12.0",
        "pandas>=1.3.0",
        "numpy>=1.21.0"
    ]
    
    print("将要安装以下依赖包:")
    for dep in dependencies:
        print(f"  - {dep}")
    
    print("\n开始安装...")
    
    success_count = 0
    for i, dep in enumerate(dependencies, 1):
        print(f"\n[{i}/{len(dependencies)}] 正在安装 {dep}...")
        
        if install_package(dep):
            print(f"✅ {dep} 安装成功")
            success_count += 1
        else:
            print(f"❌ {dep} 安装失败")
    
    print("\n" + "=" * 60)
    print(f"安装完成: {success_count}/{len(dependencies)} 个包安装成功")
    
    if success_count == len(dependencies):
        print("🎉 所有依赖安装成功！现在可以运行GUI了")
        print("运行命令: python 启动GUI.py")
    else:
        print("⚠️  部分依赖安装失败，请手动安装失败的包")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
    input("按回车键退出...")