"""
WebSocket服务器启动脚本

提供独立的WebSocket服务器启动功能。
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from .push_service import RealtimeDataPushService
from .config.settings import RealtimeDataConfig


class WebSocketServer:
    """WebSocket服务器管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        """初始化服务器
        
        Args:
            config_file: 配置文件路径
        """
        self.config = RealtimeDataConfig(config_file)
        self.service = RealtimeDataPushService(self.config)
        self.logger = logging.getLogger(__name__)
        
        # 设置日志
        self._setup_logging()
        
        # 信号处理
        self._setup_signal_handlers()
    
    def _setup_logging(self):
        """设置日志配置"""
        logging_config = self.config.config.get('logging', {})
        level = logging_config.get('level', 'INFO')
        format_str = logging_config.get('format', 
                                       '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format=format_str,
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('realtime_push_service.log', encoding='utf-8')
            ]
        )
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            self.logger.info(f"收到信号 {signum}，准备关闭服务...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self):
        """启动服务器"""
        try:
            self.logger.info("正在启动实时数据推送服务...")
            await self.service.start_server()
            
            ws_config = self.config.get_websocket_config()
            host = ws_config.get('host', 'localhost')
            port = ws_config.get('port', 8765)
            
            self.logger.info(f"服务器已启动: ws://{host}:{port}")
            self.logger.info("按 Ctrl+C 停止服务")
            
            # 保持服务运行
            while self.service.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("收到中断信号")
        except Exception as e:
            self.logger.error(f"服务器启动失败: {e}")
            raise
    
    async def stop(self):
        """停止服务器"""
        self.logger.info("正在停止服务器...")
        await self.service.stop_server()
        self.logger.info("服务器已停止")
    
    def run(self):
        """运行服务器"""
        try:
            asyncio.run(self.start())
        except KeyboardInterrupt:
            self.logger.info("服务已停止")
        except Exception as e:
            self.logger.error(f"服务运行异常: {e}")
            sys.exit(1)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='EasyXT实时数据推送服务')
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--host', help='服务器地址')
    parser.add_argument('--port', type=int, help='服务器端口')
    
    args = parser.parse_args()
    
    # 创建服务器
    server = WebSocketServer(args.config)
    
    # 覆盖配置参数
    if args.host:
        server.config.update_config('websocket.host', args.host)
    if args.port:
        server.config.update_config('websocket.port', args.port)
    
    # 运行服务器
    server.run()


if __name__ == '__main__':
    main()