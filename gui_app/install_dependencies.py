import logging

logger = logging.getLogger(__name__)
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
    logger.info("=" * 60)
    logger.info("🔧 EasyXT GUI依赖安装工具")
    logger.info("=" * 60)
    
    # 依赖列表
    dependencies = [
        "PyQt5>=5.15.0",
        "pyqtgraph>=0.12.0", 
        "matplotlib>=3.5.0",
        "mplfinance>=0.12.0",
        "pandas>=1.3.0",
        "numpy>=1.21.0"
    ]
    
    logger.info("将要安装以下依赖包:")
    for dep in dependencies:
        logger.info(f"  - {dep}")
    
    logger.info("\n开始安装...")
    
    success_count = 0
    for i, dep in enumerate(dependencies, 1):
        logger.info(f"\n[{i}/{len(dependencies)}] 正在安装 {dep}...")
        
        if install_package(dep):
            logger.info(f"✅ {dep} 安装成功")
            success_count += 1
        else:
            logger.info(f"❌ {dep} 安装失败")
    
    logger.info("\n" + "=" * 60)
    logger.info(f"安装完成: {success_count}/{len(dependencies)} 个包安装成功")
    
    if success_count == len(dependencies):
        logger.info("🎉 所有依赖安装成功！现在可以运行GUI了")
        logger.info("运行命令: python 启动GUI.py")
    else:
        logger.info("⚠️  部分依赖安装失败，请手动安装失败的包")
    
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
    input("按回车键退出...")