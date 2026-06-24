import logging

logger = logging.getLogger(__name__)
#!/usr/bin/env python3
"""
P1-009监控告警系统启动脚本

快速启动EasyXT监控告警系统的便捷脚本。
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from easy_xt.realtime_data.monitor_service import MonitorServiceManager


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="EasyXT监控告警系统")
    parser.add_argument(
        "--config", 
        default="config/monitor_config.json",
        help="配置文件路径 (默认: config/monitor_config.json)"
    )
    parser.add_argument(
        "--test", 
        action="store_true",
        help="运行测试模式"
    )
    parser.add_argument(
        "--status", 
        action="store_true",
        help="显示系统状态"
    )
    
    args = parser.parse_args()
    
    if args.test:
        # 运行测试
        logger.info("🧪 运行监控系统测试...")
        os.system("python tests/test_monitor_system.py")
        return
    
    # 创建必要的目录
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    
    # 启动监控服务
    try:
        manager = MonitorServiceManager(args.config)
        
        if args.status:
            manager.print_status()
            return
        
        logger.info("🚀 启动EasyXT监控告警系统...")
        logger.info("按 Ctrl+C 停止服务")
        
        asyncio.run(manager.start())
        
    except KeyboardInterrupt:
        logger.info("\n👋 用户中断，服务已停止")
    except Exception as e:
        logger.info(f"❌ 启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()