"""
告警管理器

管理告警规则、发送告警通知、告警历史记录等。
"""

import time
import logging
import threading
import smtplib
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警状态"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    condition: str  # 告警条件描述
    level: AlertLevel
    threshold: float
    duration: int = 0  # 持续时间（秒），0表示立即告警
    cooldown: int = 300  # 冷却时间（秒）
    enabled: bool = True
    tags: Dict[str, str] = field(default_factory=dict)
    notification_channels: List[str] = field(default_factory=list)


@dataclass
class Alert:
    """告警实例"""
    id: str
    rule_name: str
    level: AlertLevel
    title: str
    message: str
    value: float
    threshold: float
    timestamp: datetime
    status: AlertStatus = AlertStatus.ACTIVE
    resolved_at: Optional[datetime] = None
    tags: Dict[str, str] = field(default_factory=dict)
    source: str = ""
    fingerprint: str = ""


class NotificationChannel:
    """通知渠道基类"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
    
    def send(self, alert: Alert) -> bool:
        """发送告警通知"""
        raise NotImplementedError


class EmailChannel(NotificationChannel):
    """邮件通知渠道"""
    
    def send(self, alert: Alert) -> bool:
        """发送邮件通知"""
        try:
            smtp_server = self.config.get('smtp_server')
            smtp_port = self.config.get('smtp_port', 587)
            username = self.config.get('username')
            password = self.config.get('password')
            to_emails = self.config.get('to_emails', [])
            
            if not all([smtp_server, username, password, to_emails]):
                logger.error("邮件配置不完整")
                return False
            
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = username
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = f"[{alert.level.value.upper()}] {alert.title}"
            
            # 邮件内容
            body = f"""
告警详情：

级别: {alert.level.value.upper()}
时间: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
来源: {alert.source}
消息: {alert.message}
当前值: {alert.value}
阈值: {alert.threshold}
标签: {alert.tags}

告警ID: {alert.id}
规则: {alert.rule_name}
            """
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # 发送邮件
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"告警邮件发送成功: {alert.id}")
            return True
            
        except Exception as e:
            logger.error(f"发送告警邮件失败: {e}")
            return False


class WebhookChannel(NotificationChannel):
    """Webhook通知渠道"""
    
    def send(self, alert: Alert) -> bool:
        """发送Webhook通知"""
        try:
            import requests
            
            url = self.config.get('url')
            method = self.config.get('method', 'POST')
            headers = self.config.get('headers', {})
            timeout = self.config.get('timeout', 10)
            
            if not url:
                logger.error("Webhook URL未配置")
                return False
            
            # 构造请求数据
            data = {
                'alert_id': alert.id,
                'rule_name': alert.rule_name,
                'level': alert.level.value,
                'title': alert.title,
                'message': alert.message,
                'value': alert.value,
                'threshold': alert.threshold,
                'timestamp': alert.timestamp.isoformat(),
                'status': alert.status.value,
                'source': alert.source,
                'tags': alert.tags
            }
            
            # 发送请求
            if method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            else:
                response = requests.get(url, params=data, headers=headers, timeout=timeout)
            
            if response.status_code == 200:
                logger.info(f"Webhook告警发送成功: {alert.id}")
                return True
            else:
                logger.error(f"Webhook告警发送失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"发送Webhook告警失败: {e}")
            return False


class AlertManager:
    """告警管理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化告警管理器
        
        Args:
            config: 配置信息
        """
        self.config = config or {}
        
        # 告警规则
        self.rules: Dict[str, AlertRule] = {}
        
        # 活跃告警
        self.active_alerts: Dict[str, Alert] = {}
        
        # 告警历史
        self.alert_history: List[Alert] = []
        self.max_history_size = self.config.get('max_history_size', 10000)
        
        # 通知渠道
        self.notification_channels: Dict[str, NotificationChannel] = {}
        
        # 告警抑制（防止重复告警）
        self.suppression_cache: Dict[str, datetime] = {}
        
        # 运行状态
        self._running = False
        self._check_thread = None
        self._lock = threading.RLock()
        
        # 初始化通知渠道
        self._init_notification_channels()
        
        logger.info("告警管理器初始化完成")
    
    def _init_notification_channels(self):
        """初始化通知渠道"""
        channels_config = self.config.get('notification_channels', {})
        
        for name, config in channels_config.items():
            channel_type = config.get('type')
            
            if channel_type == 'email':
                self.notification_channels[name] = EmailChannel(name, config)
            elif channel_type == 'webhook':
                self.notification_channels[name] = WebhookChannel(name, config)
            else:
                logger.warning(f"未知的通知渠道类型: {channel_type}")
    
    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        with self._lock:
            self.rules[rule.name] = rule
            logger.info(f"添加告警规则: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """删除告警规则"""
        with self._lock:
            if rule_name in self.rules:
                del self.rules[rule_name]
                logger.info(f"删除告警规则: {rule_name}")
    
    def update_rule(self, rule: AlertRule):
        """更新告警规则"""
        with self._lock:
            self.rules[rule.name] = rule
            logger.info(f"更新告警规则: {rule.name}")
    
    def trigger_alert(self, 
                     rule_name: str,
                     title: str,
                     message: str,
                     value: float,
                     threshold: float,
                     source: str = "",
                     tags: Dict[str, str] = None) -> Optional[Alert]:
        """触发告警
        
        Args:
            rule_name: 规则名称
            title: 告警标题
            message: 告警消息
            value: 当前值
            threshold: 阈值
            source: 告警来源
            tags: 标签
            
        Returns:
            Alert: 告警实例，如果被抑制则返回None
        """
        rule = self.rules.get(rule_name)
        if not rule or not rule.enabled:
            return None
        
        # 生成告警指纹（用于去重）
        fingerprint = self._generate_fingerprint(rule_name, source, tags or {})
        
        # 检查是否在冷却期内
        if self._is_suppressed(fingerprint, rule.cooldown):
            return None
        
        # 创建告警
        alert = Alert(
            id=self._generate_alert_id(),
            rule_name=rule_name,
            level=rule.level,
            title=title,
            message=message,
            value=value,
            threshold=threshold,
            timestamp=datetime.now(),
            source=source,
            tags=tags or {},
            fingerprint=fingerprint
        )
        
        # 添加到活跃告警
        with self._lock:
            self.active_alerts[alert.id] = alert
            self.alert_history.append(alert)
            
            # 保持历史记录大小
            if len(self.alert_history) > self.max_history_size:
                self.alert_history.pop(0)
            
            # 更新抑制缓存
            self.suppression_cache[fingerprint] = datetime.now()
        
        # 发送通知
        self._send_notifications(alert, rule)
        
        logger.warning(f"触发告警: {alert.id} - {title}")
        return alert
    
    def resolve_alert(self, alert_id: str):
        """解决告警"""
        with self._lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now()
                
                del self.active_alerts[alert_id]
                logger.info(f"告警已解决: {alert_id}")
    
    def suppress_alert(self, alert_id: str):
        """抑制告警"""
        with self._lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.status = AlertStatus.SUPPRESSED
                logger.info(f"告警已抑制: {alert_id}")
    
    def _generate_fingerprint(self, rule_name: str, source: str, tags: Dict[str, str]) -> str:
        """生成告警指纹"""
        import hashlib
        
        content = f"{rule_name}:{source}:{sorted(tags.items())}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _generate_alert_id(self) -> str:
        """生成告警ID"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _is_suppressed(self, fingerprint: str, cooldown: int) -> bool:
        """检查是否在抑制期内"""
        if fingerprint not in self.suppression_cache:
            return False
        
        last_time = self.suppression_cache[fingerprint]
        return (datetime.now() - last_time).total_seconds() < cooldown
    
    def _send_notifications(self, alert: Alert, rule: AlertRule):
        """发送通知"""
        for channel_name in rule.notification_channels:
            channel = self.notification_channels.get(channel_name)
            if channel:
                try:
                    success = channel.send(alert)
                    if success:
                        logger.info(f"通知发送成功: {channel_name} -> {alert.id}")
                    else:
                        logger.error(f"通知发送失败: {channel_name} -> {alert.id}")
                except Exception as e:
                    logger.error(f"发送通知异常: {channel_name} -> {alert.id}, 错误: {e}")
    
    def get_active_alerts(self, level: AlertLevel = None) -> List[Alert]:
        """获取活跃告警
        
        Args:
            level: 告警级别过滤
            
        Returns:
            List[Alert]: 告警列表
        """
        with self._lock:
            alerts = list(self.active_alerts.values())
            
            if level:
                alerts = [a for a in alerts if a.level == level]
            
            # 按时间降序排序
            alerts.sort(key=lambda x: x.timestamp, reverse=True)
            return alerts
    
    def get_alert_history(self, 
                         duration: timedelta = None,
                         level: AlertLevel = None,
                         limit: int = 100) -> List[Alert]:
        """获取告警历史
        
        Args:
            duration: 时间范围
            level: 告警级别过滤
            limit: 数量限制
            
        Returns:
            List[Alert]: 告警历史
        """
        with self._lock:
            alerts = self.alert_history.copy()
            
            # 时间过滤
            if duration:
                cutoff_time = datetime.now() - duration
                alerts = [a for a in alerts if a.timestamp >= cutoff_time]
            
            # 级别过滤
            if level:
                alerts = [a for a in alerts if a.level == level]
            
            # 按时间降序排序
            alerts.sort(key=lambda x: x.timestamp, reverse=True)
            
            return alerts[:limit]
    
    def get_alert_stats(self, duration: timedelta = timedelta(hours=24)) -> Dict[str, Any]:
        """获取告警统计
        
        Args:
            duration: 统计时间范围
            
        Returns:
            Dict: 统计信息
        """
        history = self.get_alert_history(duration)
        
        if not history:
            return {
                'total_alerts': 0,
                'by_level': {},
                'by_rule': {},
                'by_source': {},
                'resolution_rate': 0.0,
                'avg_resolution_time': 0.0
            }
        
        # 按级别统计
        by_level = {}
        for level in AlertLevel:
            by_level[level.value] = len([a for a in history if a.level == level])
        
        # 按规则统计
        by_rule = {}
        for alert in history:
            by_rule[alert.rule_name] = by_rule.get(alert.rule_name, 0) + 1
        
        # 按来源统计
        by_source = {}
        for alert in history:
            source = alert.source or 'unknown'
            by_source[source] = by_source.get(source, 0) + 1
        
        # 解决率统计
        resolved_count = len([a for a in history if a.status == AlertStatus.RESOLVED])
        resolution_rate = (resolved_count / len(history)) * 100
        
        # 平均解决时间
        resolved_alerts = [a for a in history 
                          if a.status == AlertStatus.RESOLVED and a.resolved_at]
        avg_resolution_time = 0.0
        if resolved_alerts:
            total_time = sum((a.resolved_at - a.timestamp).total_seconds() 
                           for a in resolved_alerts)
            avg_resolution_time = total_time / len(resolved_alerts)
        
        return {
            'total_alerts': len(history),
            'active_alerts': len(self.active_alerts),
            'by_level': by_level,
            'by_rule': by_rule,
            'by_source': by_source,
            'resolution_rate': resolution_rate,
            'avg_resolution_time': avg_resolution_time,
            'time_range': {
                'start': history[-1].timestamp.isoformat() if history else None,
                'end': history[0].timestamp.isoformat() if history else None
            }
        }
    
    def cleanup_old_alerts(self, max_age: timedelta = timedelta(days=7)):
        """清理旧告警"""
        with self._lock:
            cutoff_time = datetime.now() - max_age
            
            # 清理历史记录
            self.alert_history = [a for a in self.alert_history 
                                if a.timestamp >= cutoff_time]
            
            # 清理抑制缓存
            self.suppression_cache = {
                k: v for k, v in self.suppression_cache.items()
                if (datetime.now() - v).total_seconds() < 3600  # 保留1小时内的
            }
            
            logger.info(f"清理旧告警完成，保留 {len(self.alert_history)} 条历史记录")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取管理器统计信息"""
        with self._lock:
            return {
                'manager_info': {
                    'rules_count': len(self.rules),
                    'active_alerts_count': len(self.active_alerts),
                    'history_size': len(self.alert_history),
                    'max_history_size': self.max_history_size,
                    'notification_channels': list(self.notification_channels.keys()),
                    'suppression_cache_size': len(self.suppression_cache)
                },
                'alert_stats': self.get_alert_stats(),
                'rules': {
                    name: {
                        'level': rule.level.value,
                        'threshold': rule.threshold,
                        'enabled': rule.enabled,
                        'cooldown': rule.cooldown,
                        'channels': rule.notification_channels
                    }
                    for name, rule in self.rules.items()
                }
            }


# 预定义告警规则
def create_system_alert_rules() -> List[AlertRule]:
    """创建系统监控告警规则"""
    return [
        AlertRule(
            name="cpu_high",
            condition="CPU使用率 > 80%",
            level=AlertLevel.WARNING,
            threshold=80.0,
            cooldown=300,
            notification_channels=["email", "webhook"]
        ),
        AlertRule(
            name="memory_high",
            condition="内存使用率 > 85%",
            level=AlertLevel.WARNING,
            threshold=85.0,
            cooldown=300,
            notification_channels=["email", "webhook"]
        ),
        AlertRule(
            name="disk_high",
            condition="磁盘使用率 > 90%",
            level=AlertLevel.CRITICAL,
            threshold=90.0,
            cooldown=600,
            notification_channels=["email", "webhook"]
        )
    ]


def create_api_alert_rules() -> List[AlertRule]:
    """创建API监控告警规则"""
    return [
        AlertRule(
            name="api_error_rate_high",
            condition="API错误率 > 5%",
            level=AlertLevel.WARNING,
            threshold=5.0,
            cooldown=300,
            notification_channels=["webhook"]
        ),
        AlertRule(
            name="api_response_time_high",
            condition="API响应时间 > 2000ms",
            level=AlertLevel.WARNING,
            threshold=2000.0,
            cooldown=300,
            notification_channels=["webhook"]
        )
    ]


def create_data_source_alert_rules() -> List[AlertRule]:
    """创建数据源监控告警规则"""
    return [
        AlertRule(
            name="data_source_offline",
            condition="数据源离线",
            level=AlertLevel.CRITICAL,
            threshold=0.0,
            cooldown=600,
            notification_channels=["email", "webhook"]
        ),
        AlertRule(
            name="data_source_availability_low",
            condition="数据源可用性 < 95%",
            level=AlertLevel.WARNING,
            threshold=95.0,
            cooldown=300,
            notification_channels=["webhook"]
        )
    ]