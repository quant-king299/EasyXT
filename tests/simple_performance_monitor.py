#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版性能监控器 - 用于测试
"""

import time
import psutil
import logging
from typing import Dict, Any


class SimplePerformanceMonitor:
    """简化版性能监控器"""
    
    def __init__(self):
        """初始化监控器"""
        self.start_time = None
        self.end_time = None
        self.cpu_samples = []
        self.memory_samples = []
        self.monitoring = False
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 获取进程对象
        try:
            self.process = psutil.Process()
        except Exception as e:
            self.logger.warning(f"无法获取进程信息: {e}")
            self.process = None
    
    def start_monitoring(self):
        """开始监控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.start_time = time.time()
        self.cpu_samples = []
        self.memory_samples = []
        
        # 记录初始状态
        self._record_sample()
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """停止监控并返回结果"""
        if not self.monitoring:
            return {}
        
        self.monitoring = False
        self.end_time = time.time()
        
        # 记录最终状态
        self._record_sample()
        
        # 计算统计信息
        total_time = self.end_time - self.start_time
        
        if self.cpu_samples:
            avg_cpu = sum(self.cpu_samples) / len(self.cpu_samples)
            max_cpu = max(self.cpu_samples)
        else:
            avg_cpu = 0
            max_cpu = 0
        
        if self.memory_samples:
            avg_memory = sum(self.memory_samples) / len(self.memory_samples)
            peak_memory = max(self.memory_samples)
        else:
            avg_memory = 0
            peak_memory = 0
        
        return {
            'total_time': total_time,
            'avg_cpu_percent': avg_cpu,
            'max_cpu_percent': max_cpu,
            'avg_memory_mb': avg_memory,
            'peak_memory_mb': peak_memory,
            'sample_count': len(self.cpu_samples)
        }
    
    def _record_sample(self):
        """记录当前性能样本"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=None)
            self.cpu_samples.append(cpu_percent)
            
            # 内存使用情况
            if self.process:
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                self.memory_samples.append(memory_mb)
            else:
                # 使用系统内存信息
                memory = psutil.virtual_memory()
                memory_mb = memory.used / 1024 / 1024
                self.memory_samples.append(memory_mb)
                
        except Exception as e:
            self.logger.error(f"记录性能样本失败: {e}")
    
    def record_intermediate_sample(self):
        """记录中间样本（可在测试过程中调用）"""
        if self.monitoring:
            self._record_sample()