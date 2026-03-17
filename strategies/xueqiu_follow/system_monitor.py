#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雪球跟单策略实时监控工具
"""

import sys
import os
import asyncio
import time
import json
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 添加internal目录到路径
internal_dir = os.path.join(current_dir, 'internal')
if internal_dir not in sys.path:
    sys.path.insert(0, internal_dir)

# 使用绝对导入
from internal.config_manager import ConfigManager


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, config_manager: ConfigManager = None):
        self.config_manager = config_manager or ConfigManager()
        self.monitoring = True
        self.stats = {
            'start_time': datetime.now(),
            'cpu_history': [],
            'memory_history': [],
            'network_history': [],
            'error_count': 0,
            'warning_count': 0,
            'trade_count': 0,
            'last_update': None
        }
        
        # 监控配置
        self.check_interval = self.config_manager.get_setting('monitoring.check_interval', 30)
        self.max_history = 100  # 保留最近100个数据点
        
    async def start_monitoring(self):
        """开始监控"""
        print("🔍 启动系统监控...")
        print(f"监控间隔: {self.check_interval}秒")
        print("按 Ctrl+C 停止监控\n")
        
        try:
            while self.monitoring:
                await self._collect_metrics()
                await self._check_alerts()
                self._display_status()
                
                await asyncio.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print("\n监控已停止")
        except Exception as e:
            print(f"\n监控过程中发生错误: {e}")
    
    async def _collect_metrics(self):
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self.stats['cpu_history'].append({
                'time': datetime.now(),
                'value': cpu_percent
            })
            
            # 内存使用
            memory = psutil.virtual_memory()
            self.stats['memory_history'].append({
                'time': datetime.now(),
                'percent': memory.percent,
                'available_gb': memory.available / (1024**3),
                'used_gb': memory.used / (1024**3)
            })
            
            # 网络IO
            network = psutil.net_io_counters()
            self.stats['network_history'].append({
                'time': datetime.now(),
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv
            })
            
            # 限制历史数据长度
            for key in ['cpu_history', 'memory_history', 'network_history']:
                if len(self.stats[key]) > self.max_history:
                    self.stats[key] = self.stats[key][-self.max_history:]
            
            # 更新时间
            self.stats['last_update'] = datetime.now()
            
        except Exception as e:
            print(f"指标收集错误: {e}")
    
    async def _check_alerts(self):
        """检查告警条件"""
        try:
            # 检查CPU使用率
            if self.stats['cpu_history']:
                latest_cpu = self.stats['cpu_history'][-1]['value']
                if latest_cpu > 80:
                    self._log_alert('WARNING', f'CPU使用率过高: {latest_cpu:.1f}%')
            
            # 检查内存使用率
            if self.stats['memory_history']:
                latest_memory = self.stats['memory_history'][-1]
                if latest_memory['percent'] > 85:
                    self._log_alert('WARNING', f'内存使用率过高: {latest_memory["percent"]:.1f}%')
                
                if latest_memory['available_gb'] < 0.5:
                    self._log_alert('CRITICAL', f'可用内存不足: {latest_memory["available_gb"]:.2f}GB')
            
            # 检查日志文件错误
            await self._check_log_errors()
            
        except Exception as e:
            print(f"告警检查错误: {e}")
    
    async def _check_log_errors(self):
        """检查日志文件中的错误"""
        try:
            log_dir = Path('logs')
            if not log_dir.exists():
                return
            
            # 检查今天的日志文件
            today = datetime.now().strftime('%Y%m%d')
            log_files = list(log_dir.glob(f'*{today}.log'))
            
            for log_file in log_files:
                try:
                    # 读取最后几行
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        recent_lines = lines[-50:] if len(lines) > 50 else lines
                    
                    # 统计错误和警告
                    for line in recent_lines:
                        if 'ERROR' in line:
                            self.stats['error_count'] += 1
                        elif 'WARNING' in line:
                            self.stats['warning_count'] += 1
                        elif '订单执行成功' in line:
                            self.stats['trade_count'] += 1
                            
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"日志检查错误: {e}")
    
    def _log_alert(self, level: str, message: str):
        """记录告警"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"\n🚨 [{timestamp}] {level}: {message}")
        
        # 可以在这里添加更多告警处理逻辑，如发送邮件、短信等
    
    def _display_status(self):
        """显示系统状态"""
        # 清屏
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 60)
        print("🔍 雪球跟单策略实时监控")
        print("=" * 60)
        
        # 运行时间
        uptime = datetime.now() - self.stats['start_time']
        print(f"运行时间: {self._format_timedelta(uptime)}")
        print(f"最后更新: {self.stats['last_update'].strftime('%H:%M:%S') if self.stats['last_update'] else 'N/A'}")
        print()
        
        # 系统资源
        print("💻 系统资源:")
        if self.stats['cpu_history']:
            latest_cpu = self.stats['cpu_history'][-1]['value']
            cpu_trend = self._get_trend(self.stats['cpu_history'], 'value')
            print(f"   CPU使用率: {latest_cpu:.1f}% {cpu_trend}")
        
        if self.stats['memory_history']:
            latest_memory = self.stats['memory_history'][-1]
            memory_trend = self._get_trend(self.stats['memory_history'], 'percent')
            print(f"   内存使用率: {latest_memory['percent']:.1f}% {memory_trend}")
            print(f"   可用内存: {latest_memory['available_gb']:.2f}GB")
            print(f"   已用内存: {latest_memory['used_gb']:.2f}GB")
        
        print()
        
        # 业务指标
        print("📊 业务指标:")
        print(f"   交易次数: {self.stats['trade_count']}")
        print(f"   错误次数: {self.stats['error_count']}")
        print(f"   警告次数: {self.stats['warning_count']}")
        print()
        
        # 网络状态
        if len(self.stats['network_history']) >= 2:
            current_net = self.stats['network_history'][-1]
            prev_net = self.stats['network_history'][-2]
            
            sent_rate = (current_net['bytes_sent'] - prev_net['bytes_sent']) / self.check_interval
            recv_rate = (current_net['bytes_recv'] - prev_net['bytes_recv']) / self.check_interval
            
            print("🌐 网络状态:")
            print(f"   上传速率: {self._format_bytes(sent_rate)}/s")
            print(f"   下载速率: {self._format_bytes(recv_rate)}/s")
            print()
        
        # 配置状态
        print("⚙️ 配置状态:")
        enabled_portfolios = self.config_manager.get_enabled_portfolios()
        print(f"   启用组合: {len(enabled_portfolios)}")
        
        emergency_stop = self.config_manager.get_global_setting('emergency_stop', False)
        print(f"   紧急停止: {'是' if emergency_stop else '否'}")
        print()
        
        # 性能图表（简化版）
        if len(self.stats['cpu_history']) > 10:
            print("📈 CPU使用率趋势 (最近10个数据点):")
            self._draw_simple_chart([h['value'] for h in self.stats['cpu_history'][-10:]], max_val=100)
            print()
        
        if len(self.stats['memory_history']) > 10:
            print("📈 内存使用率趋势 (最近10个数据点):")
            self._draw_simple_chart([h['percent'] for h in self.stats['memory_history'][-10:]], max_val=100)
            print()
        
        print("按 Ctrl+C 停止监控")
    
    def _get_trend(self, history: List[Dict], key: str) -> str:
        """获取趋势指示"""
        if len(history) < 3:
            return ""
        
        recent_values = [h[key] for h in history[-3:]]
        
        if recent_values[-1] > recent_values[-2] > recent_values[-3]:
            return "📈"
        elif recent_values[-1] < recent_values[-2] < recent_values[-3]:
            return "📉"
        else:
            return "➡️"
    
    def _draw_simple_chart(self, values: List[float], max_val: float = 100, width: int = 40):
        """绘制简单的文本图表"""
        if not values:
            return
        
        # 标准化值到图表宽度
        normalized = [int(v / max_val * width) for v in values]
        
        # 绘制图表
        chart_line = ""
        for val in normalized:
            if val == 0:
                chart_line += "▁"
            elif val <= width * 0.25:
                chart_line += "▂"
            elif val <= width * 0.5:
                chart_line += "▄"
            elif val <= width * 0.75:
                chart_line += "▆"
            else:
                chart_line += "█"
        
        print(f"   {chart_line}")
        print(f"   0%{' ' * (width-6)}100%")
    
    def _format_timedelta(self, td: timedelta) -> str:
        """格式化时间差"""
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}小时{minutes}分钟{seconds}秒"
        elif minutes > 0:
            return f"{minutes}分钟{seconds}秒"
        else:
            return f"{seconds}秒"
    
    def _format_bytes(self, bytes_val: float) -> str:
        """格式化字节数"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024:
                return f"{bytes_val:.1f}{unit}"
            bytes_val /= 1024
        return f"{bytes_val:.1f}TB"
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """获取统计摘要"""
        summary = {
            'uptime': datetime.now() - self.stats['start_time'],
            'trade_count': self.stats['trade_count'],
            'error_count': self.stats['error_count'],
            'warning_count': self.stats['warning_count']
        }
        
        if self.stats['cpu_history']:
            cpu_values = [h['value'] for h in self.stats['cpu_history']]
            summary['cpu_avg'] = sum(cpu_values) / len(cpu_values)
            summary['cpu_max'] = max(cpu_values)
        
        if self.stats['memory_history']:
            memory_values = [h['percent'] for h in self.stats['memory_history']]
            summary['memory_avg'] = sum(memory_values) / len(memory_values)
            summary['memory_max'] = max(memory_values)
        
        return summary


async def main():
    """主函数"""
    try:
        config = ConfigManager()
        monitor = SystemMonitor(config)
        
        await monitor.start_monitoring()
        
    except KeyboardInterrupt:
        print("\n监控已停止")
    except Exception as e:
        print(f"监控启动失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)