"""
HTTP服务器启动脚本

提供独立的HTTP API服务器启动功能。
"""

import asyncio
import logging
import signal
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .api_server import RealtimeDataAPIServer
from .config.settings import RealtimeDataConfig


class HTTPServerManager:
    """HTTP服务器管理器"""
    
    def __init__(self, config_file=None):
        """初始化服务器管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config = RealtimeDataConfig(config_file)
        self.server = None
        self.running = False
        
        # 配置日志
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('logs/api_server.log', encoding='utf-8')
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    async def start_server(self):
        """启动服务器"""
        try:
            self.server = RealtimeDataAPIServer(self.config)
            await self.server.start_server()
            self.running = True
            
            host = self.server.host
            port = self.server.port
            
            print(f"""
🚀 EasyXT实时数据API服务器已启动

📡 服务地址: http://{host}:{port}
📖 API文档: http://{host}:{port}/docs
🔍 健康检查: http://{host}:{port}/health
📊 服务状态: http://{host}:{port}/status

📋 主要端点:
   GET  /api/v1/quotes?symbols=000001,000002  - 获取实时行情
   POST /api/v1/quotes                        - 批量获取行情
   GET  /api/v1/hot-stocks?count=20           - 获取热门股票
   GET  /api/v1/concepts?count=20             - 获取概念数据
   GET  /api/v1/market-status                 - 获取市场状态
   GET  /api/v1/sources                       - 获取数据源状态
   GET  /api/v1/compare?symbols=000001        - 多数据源对比
   GET  /api/v1/stats                         - 服务器统计

💡 使用示例:
   curl "http://{host}:{port}/api/v1/quotes?symbols=000001,000002"
   curl "http://{host}:{port}/api/v1/hot-stocks?count=10"

按 Ctrl+C 停止服务器
""")
            
            # 设置信号处理
            if sys.platform != 'win32':
                loop = asyncio.get_event_loop()
                for sig in (signal.SIGTERM, signal.SIGINT):
                    loop.add_signal_handler(sig, self._signal_handler)
            
            # 保持运行
            while self.running and self.server.is_running():
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error(f"启动服务器失败: {e}")
            raise
    
    def _signal_handler(self):
        """信号处理器"""
        self.logger.info("收到停止信号")
        self.running = False
    
    async def stop_server(self):
        """停止服务器"""
        try:
            self.running = False
            if self.server:
                await self.server.stop_server()
                self.server = None
            self.logger.info("服务器已停止")
        except Exception as e:
            self.logger.error(f"停止服务器失败: {e}")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='EasyXT实时数据API服务器')
    parser.add_argument('--host', default='localhost', help='服务器地址')
    parser.add_argument('--port', type=int, default=8080, help='服务器端口')
    parser.add_argument('--config', help='配置文件路径')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    
    args = parser.parse_args()
    
    # 创建服务器管理器
    manager = HTTPServerManager(args.config)
    
    # 更新配置
    if args.host != 'localhost':
        manager.config.update_config('api.host', args.host)
    if args.port != 8080:
        manager.config.update_config('api.port', args.port)
    
    # 设置调试模式
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        await manager.start_server()
    except KeyboardInterrupt:
        print("\n正在停止服务器...")
        await manager.stop_server()
        print("服务器已停止")
    except Exception as e:
        print(f"服务器错误: {e}")
        await manager.stop_server()


if __name__ == "__main__":
    # 确保日志目录存在
    os.makedirs('logs', exist_ok=True)
    
    # 运行服务器
    asyncio.run(main())