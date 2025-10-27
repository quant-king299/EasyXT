#!/usr/bin/env python3
"""
P1-009: 监控告警系统主服务

统一启动和管理所有监控组件，提供完整的监控告警功能。
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from easy_xt.realtime_data.monitor.integration import MonitoringService
from easy_xt.realtime_data.monitor.alert_manager import AlertLevel, AlertRule
from easy_xt.realtime_data.config import RealtimeDataConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/monitor_service.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class MonitorServiceManager:
    """监控服务管理器"""
    
    def __init__(self, config_file: str = None):
        """初始化监控服务管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file or "config/monitor_config.json"
        self.config = self._load_config()
        self.monitoring_service: Optional[MonitoringService] = None
        self._shutdown_event = asyncio.Event()
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("监控服务管理器初始化完成")
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        try:
            # 尝试加载配置文件
            config = RealtimeDataConfig(self.config_file)
            return config.get_monitor_config()
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}，使用默认配置")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "system_monitor": {
                "enabled": True,
                "interval": 30,
                "history_size": 1000
            },
            "data_source_monitor": {
                "enabled": True,
                "interval": 60,
                "timeout": 10,
                "data_sources": [
                    {
                        "name": "tdx_server",
                        "type": "tcp",
                        "host": "119.147.212.81",
                        "port": 7709
                    },
                    {
                        "name": "eastmoney_api",
                        "type": "http",
                        "url": "http://push2his.eastmoney.com/api/qt/stock/get",
                        "timeout": 5
                    }
                ]
            },
            "api_monitor": {
                "enabled": True,
                "interval": 30,
                "history_size": 1000
            },
            "alert_manager": {
                "enabled": True,
                "email": {
                    "smtp_server": "smtp.qq.com",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "from_addr": "",
                    "to_addrs": []
                },
                "webhook": {
                    "enabled": False,
                    "url": ""
                }
            },
            "metrics_collector": {
                "enabled": True,
                "collection_interval": 30,
                "retention_days": 7
            },
            "dashboard": {
                "enabled": True,
                "host": "0.0.0.0",
                "port": 8080
            }
        }
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"接收到信号 {signum}，准备关闭服务...")
        self._shutdown_event.set()
    
    async def start(self):
        """启动监控服务"""
        try:
            logger.info("正在启动监控告警系统...")
            
            # 创建监控服务
            self.monitoring_service = MonitoringService(self.config)
            
            # 启动监控服务
            await self.monitoring_service.start()
            
            logger.info("✅ 监控告警系统启动成功")
            logger.info("监控功能:")
            logger.info("  - 系统性能监控 (CPU、内存、磁盘、网络)")
            logger.info("  - 数据源状态监控 (通达信、东方财富等)")
            logger.info("  - API性能监控 (响应时间、成功率)")
            logger.info("  - 智能告警系统 (邮件、Webhook)")
            logger.info("  - 监控仪表板 (Web界面)")
            
            # 等待关闭信号
            await self._shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"启动监控服务失败: {e}")
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """停止监控服务"""
        if self.monitoring_service:
            logger.info("正在停止监控服务...")
            await self.monitoring_service.stop()
            logger.info("✅ 监控服务已停止")
    
    def create_default_alert_rules(self) -> list:
        """创建默认告警规则"""
        rules = []
        
        # 系统资源告警规则
        rules.extend([
            AlertRule(
                name="high_cpu_usage",
                condition="CPU使用率过高",
                level=AlertLevel.WARNING,
                threshold=80.0,
                duration=300,  # 持续5分钟
                cooldown=600,  # 冷却10分钟
                notification_channels=["email"]
            ),
            AlertRule(
                name="critical_cpu_usage", 
                condition="CPU使用率严重过高",
                level=AlertLevel.CRITICAL,
                threshold=95.0,
                duration=60,   # 持续1分钟
                cooldown=300,  # 冷却5分钟
                notification_channels=["email", "webhook"]
            ),
            AlertRule(
                name="high_memory_usage",
                condition="内存使用率过高",
                level=AlertLevel.WARNING,
                threshold=85.0,
                duration=300,
                cooldown=600,
                notification_channels=["email"]
            ),
            AlertRule(
                name="disk_space_low",
                condition="磁盘空间不足",
                level=AlertLevel.CRITICAL,
                threshold=90.0,
                duration=0,    # 立即告警
                cooldown=3600, # 冷却1小时
                notification_channels=["email", "webhook"]
            )
        ])
        
        # 数据源告警规则
        rules.extend([
            AlertRule(
                name="data_source_offline",
                condition="数据源离线",
                level=AlertLevel.CRITICAL,
                threshold=1.0,  # 连接失败
                duration=0,
                cooldown=300,
                notification_channels=["email", "webhook"]
            ),
            AlertRule(
                name="data_source_slow_response",
                condition="数据源响应缓慢",
                level=AlertLevel.WARNING,
                threshold=5.0,  # 响应时间超过5秒
                duration=180,   # 持续3分钟
                cooldown=600,
                notification_channels=["email"]
            )
        ])
        
        # API性能告警规则
        rules.extend([
            AlertRule(
                name="api_high_error_rate",
                condition="API错误率过高",
                level=AlertLevel.WARNING,
                threshold=10.0,  # 错误率超过10%
                duration=300,
                cooldown=600,
                notification_channels=["email"]
            ),
            AlertRule(
                name="api_slow_response",
                condition="API响应缓慢",
                level=AlertLevel.WARNING,
                threshold=3.0,   # 平均响应时间超过3秒
                duration=300,
                cooldown=600,
                notification_channels=["email"]
            )
        ])
        
        return rules
    
    def print_status(self):
        """打印服务状态"""
        print("\n" + "="*60)
        print("📊 EasyXT监控告警系统状态")
        print("="*60)
        
        if self.monitoring_service:
            print("🟢 服务状态: 运行中")
            print(f"📁 配置文件: {self.config_file}")
            print(f"🔧 监控组件: {len([k for k, v in self.config.items() if v.get('enabled', False)])} 个已启用")
            
            # 显示启用的组件
            enabled_components = []
            for component, config in self.config.items():
                if config.get('enabled', False):
                    enabled_components.append(component)
            
            print(f"📋 启用组件: {', '.join(enabled_components)}")
            
            if self.config.get('dashboard', {}).get('enabled'):
                dashboard_config = self.config['dashboard']
                print(f"🌐 监控面板: http://{dashboard_config['host']}:{dashboard_config['port']}")
        else:
            print("🔴 服务状态: 未启动")
        
        print("="*60)


async def main():
    """主函数"""
    try:
        # 创建监控服务管理器
        manager = MonitorServiceManager()
        
        # 显示状态
        manager.print_status()
        
        # 启动服务
        await manager.start()
        
    except KeyboardInterrupt:
        logger.info("用户中断，正在退出...")
    except Exception as e:
        logger.error(f"服务运行异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 确保日志目录存在
    Path("logs").mkdir(exist_ok=True)
    
    # 运行服务
    asyncio.run(main())