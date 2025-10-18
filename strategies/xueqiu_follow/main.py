"""
雪球跟单策略 - 主入口模块
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from strategies.xueqiu_follow.core.strategy_engine import XueqiuFollowStrategy
from strategies.xueqiu_follow.core.config_manager import get_config_manager
from strategies.xueqiu_follow.gui.main_window import XueqiuFollowWidget, XueqiuFollowMainWindow
from strategies.xueqiu_follow.utils.logger import setup_logger


class XueqiuFollowMain:
    """雪球跟单策略主控制器"""
    
    def __init__(self):
        self.logger = setup_logger("XueqiuFollow")
        self.config_manager = get_config_manager()
        self.strategy: Optional[XueqiuFollowStrategy] = None
        self.gui: Optional[XueqiuFollowMainWindow] = None
        
    async def initialize(self):
        """初始化系统"""
        try:
            self.logger.info("正在初始化雪球跟单策略...")
            
            # 验证配置
            config_errors = self.config_manager.validate_settings()
            if config_errors:
                self.logger.warning(f"配置验证发现问题: {config_errors}")
            
            # 初始化策略引擎
            self.strategy = XueqiuFollowStrategy(self.config_manager)
            await self.strategy.initialize()
            
            self.logger.info("雪球跟单策略初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"系统初始化失败: {e}")
            return False
    
    def start_gui(self):
        """启动GUI界面"""
        try:
            self.logger.info("启动GUI界面...")
            from PyQt5.QtWidgets import QApplication
            import sys
            
            app = QApplication(sys.argv)
            self.gui = XueqiuFollowMainWindow(self.config_manager, self.strategy)
            self.gui.show()
            sys.exit(app.exec_())
            
        except Exception as e:
            self.logger.error(f"GUI启动失败: {e}")
    
    async def start_strategy(self):
        """启动策略运行"""
        if not self.strategy:
            self.logger.error("策略引擎未初始化")
            return False
            
        try:
            self.logger.info("启动策略运行...")
            await self.strategy.start()
            return True
            
        except Exception as e:
            self.logger.error(f"策略启动失败: {e}")
            return False
    
    async def stop_strategy(self):
        """停止策略运行"""
        if self.strategy:
            try:
                self.logger.info("停止策略运行...")
                await self.strategy.stop()
                
            except Exception as e:
                self.logger.error(f"策略停止失败: {e}")
    
    async def cleanup(self):
        """清理资源"""
        await self.stop_strategy()
        self.logger.info("系统清理完成")


async def main():
    """主函数"""
    app = XueqiuFollowMain()
    
    try:
        # 初始化系统
        if not await app.initialize():
            return
        
        # 启动GUI界面
        app.start_gui()
        
    except KeyboardInterrupt:
        print("\n收到中断信号，正在退出...")
    except Exception as e:
        print(f"系统运行错误: {e}")
    finally:
        await app.cleanup()


if __name__ == "__main__":
    # 设置事件循环策略（Windows兼容性）
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # 运行主程序
    asyncio.run(main())