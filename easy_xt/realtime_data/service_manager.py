"""
Windows服务管理器
统一管理HTTP API和WebSocket服务
"""

import asyncio
import threading
import time
import signal
import sys
import logging
from typing import Optional
import multiprocessing as mp

from .http_server import HTTPServerManager
from .websocket_server import WebSocketServer
from .config.server_config import ServerConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/service_manager.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class EasyXTServiceManager:
    """EasyXT服务管理器"""
    
    def __init__(self):
        self.config = ServerConfig()
        self.http_process: Optional[mp.Process] = None
        self.websocket_process: Optional[mp.Process] = None
        self.running = False
        
    def start_http_server_process(self):
        """启动HTTP服务器进程"""
        try:
            logger.info(f"启动HTTP服务器进程 (端口: {self.config.HTTP_PORT})")
            
            def run_http():
                import asyncio
                from .http_server import HTTPServerManager
                
                async def start_http_async():
                    manager = HTTPServerManager()
                    await manager.start_server()
                
                asyncio.run(start_http_async())
            
            self.http_process = mp.Process(target=run_http, name="EasyXT-HTTP")
            self.http_process.start()
            logger.info(f"HTTP服务器进程已启动 (PID: {self.http_process.pid})")
            
        except Exception as e:
            logger.error(f"启动HTTP服务器失败: {e}")
            raise
    
    def start_websocket_server_process(self):
        """启动WebSocket服务器进程"""
        try:
            logger.info(f"启动WebSocket服务器进程 (端口: {self.config.WEBSOCKET_PORT})")
            
            def run_websocket():
                server = WebSocketServer(
                    host=self.config.WEBSOCKET_HOST,
                    port=self.config.WEBSOCKET_PORT
                )
                asyncio.run(server.start())
            
            self.websocket_process = mp.Process(target=run_websocket, name="EasyXT-WebSocket")
            self.websocket_process.start()
            logger.info(f"WebSocket服务器进程已启动 (PID: {self.websocket_process.pid})")
            
        except Exception as e:
            logger.error(f"启动WebSocket服务器失败: {e}")
            raise
    
    def start_services(self):
        """启动所有服务"""
        logger.info("=== EasyXT 实时数据服务启动 ===")
        
        try:
            # 启动HTTP服务器
            self.start_http_server_process()
            time.sleep(2)  # 等待HTTP服务器启动
            
            # 启动WebSocket服务器
            self.start_websocket_server_process()
            time.sleep(2)  # 等待WebSocket服务器启动
            
            self.running = True
            logger.info("所有服务启动成功")
            logger.info(f"HTTP API: http://{self.config.HTTP_HOST}:{self.config.HTTP_PORT}")
            logger.info(f"WebSocket: ws://{self.config.WEBSOCKET_HOST}:{self.config.WEBSOCKET_PORT}")
            
        except Exception as e:
            logger.error(f"服务启动失败: {e}")
            self.stop_services()
            raise
    
    def stop_services(self):
        """停止所有服务"""
        logger.info("正在停止所有服务...")
        self.running = False
        
        # 停止HTTP服务器
        if self.http_process and self.http_process.is_alive():
            logger.info("停止HTTP服务器进程")
            self.http_process.terminate()
            self.http_process.join(timeout=10)
            if self.http_process.is_alive():
                logger.warning("强制终止HTTP服务器进程")
                self.http_process.kill()
        
        # 停止WebSocket服务器
        if self.websocket_process and self.websocket_process.is_alive():
            logger.info("停止WebSocket服务器进程")
            self.websocket_process.terminate()
            self.websocket_process.join(timeout=10)
            if self.websocket_process.is_alive():
                logger.warning("强制终止WebSocket服务器进程")
                self.websocket_process.kill()
        
        logger.info("所有服务已停止")
    
    def monitor_services(self):
        """监控服务状态"""
        while self.running:
            try:
                # 检查HTTP服务器
                if self.http_process and not self.http_process.is_alive():
                    logger.error("HTTP服务器进程异常退出，尝试重启")
                    self.start_http_server_process()
                
                # 检查WebSocket服务器
                if self.websocket_process and not self.websocket_process.is_alive():
                    logger.error("WebSocket服务器进程异常退出，尝试重启")
                    self.start_websocket_server_process()
                
                time.sleep(30)  # 每30秒检查一次
                
            except Exception as e:
                logger.error(f"服务监控异常: {e}")
                time.sleep(60)  # 出错时等待更长时间
    
    def run(self):
        """运行服务管理器"""
        # 注册信号处理器
        def signal_handler(signum, frame):
            logger.info(f"收到信号 {signum}，正在关闭服务...")
            self.stop_services()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # 启动服务
            self.start_services()
            
            # 监控服务
            self.monitor_services()
            
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在关闭服务...")
        except Exception as e:
            logger.error(f"服务运行异常: {e}")
        finally:
            self.stop_services()

def main():
    """主函数"""
    import os
    
    # 确保日志目录存在
    os.makedirs('logs', exist_ok=True)
    
    # 创建并运行服务管理器
    manager = EasyXTServiceManager()
    manager.run()

if __name__ == "__main__":
    main()