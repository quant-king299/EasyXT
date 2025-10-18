"""
请求频率限制器
"""

import asyncio
import time
from collections import deque
from typing import Optional


class RateLimiter:
    """请求频率限制器"""
    
    def __init__(self, max_requests: int, time_window: int):
        """
        初始化频率限制器
        
        Args:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口大小（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """获取请求许可"""
        async with self._lock:
            now = time.time()
            
            # 清理过期的请求记录
            while self.requests and self.requests[0] <= now - self.time_window:
                self.requests.popleft()
            
            # 检查是否超过限制
            if len(self.requests) >= self.max_requests:
                # 计算需要等待的时间
                oldest_request = self.requests[0]
                wait_time = oldest_request + self.time_window - now
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    return await self.acquire()
            
            # 记录当前请求
            self.requests.append(now)
    
    def get_remaining_requests(self) -> int:
        """获取剩余可用请求数"""
        now = time.time()
        
        # 清理过期的请求记录
        while self.requests and self.requests[0] <= now - self.time_window:
            self.requests.popleft()
        
        return max(0, self.max_requests - len(self.requests))
    
    def get_reset_time(self) -> Optional[float]:
        """获取限制重置时间"""
        if not self.requests:
            return None
        
        oldest_request = self.requests[0]
        return oldest_request + self.time_window