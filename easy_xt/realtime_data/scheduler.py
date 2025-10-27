"""
P1-011: 异步任务调度器

实现高性能的异步任务调度系统，支持：
1. 定时任务调度
2. 延迟任务执行
3. 任务优先级管理
4. 任务状态监控
5. 失败重试机制
6. 并发控制
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import threading
import heapq
from functools import wraps

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 正在执行
    COMPLETED = "completed"  # 执行完成
    FAILED = "failed"        # 执行失败
    CANCELLED = "cancelled"  # 已取消
    RETRYING = "retrying"    # 重试中


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[Exception] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time: Optional[float] = None
    retry_count: int = 0


@dataclass
class Task:
    """任务定义"""
    id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    scheduled_time: Optional[datetime] = None
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: Optional[float] = None
    created_time: datetime = field(default_factory=datetime.now)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[TaskResult] = None
    
    def __lt__(self, other):
        """用于优先级队列排序"""
        if self.scheduled_time and other.scheduled_time:
            return self.scheduled_time < other.scheduled_time
        return self.priority.value > other.priority.value


class TaskScheduler:
    """异步任务调度器"""
    
    def __init__(self, max_workers: int = 10, max_concurrent_tasks: int = 100):
        """初始化任务调度器
        
        Args:
            max_workers: 最大工作线程数
            max_concurrent_tasks: 最大并发任务数
        """
        self.max_workers = max_workers
        self.max_concurrent_tasks = max_concurrent_tasks
        
        # 任务存储
        self.tasks: Dict[str, Task] = {}
        self.task_queue: List[Task] = []  # 优先级队列
        self.running_tasks: Dict[str, asyncio.Task] = {}
        
        # 定时任务
        self.scheduled_tasks: Dict[str, Task] = {}
        self.recurring_tasks: Dict[str, Dict] = {}
        
        # 执行器
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        
        # 控制标志
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
        # 统计信息
        self.statistics = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'cancelled_tasks': 0,
            'retry_tasks': 0,
            'average_execution_time': 0.0
        }
        
        # 锁
        self._lock = threading.Lock()
        
        logger.info(f"任务调度器初始化完成，最大工作线程: {max_workers}，最大并发任务: {max_concurrent_tasks}")
    
    def start(self):
        """启动任务调度器"""
        if self.is_running:
            logger.warning("任务调度器已经在运行")
            return
        
        self.is_running = True
        self.shutdown_event.clear()
        
        # 获取或创建事件循环
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        
        # 启动调度器主循环
        if self.loop.is_running():
            # 如果循环已经在运行，创建任务
            asyncio.create_task(self._scheduler_loop())
        else:
            # 如果循环未运行，运行直到完成
            self.loop.run_until_complete(self._scheduler_loop())
        
        logger.info("任务调度器已启动")
    
    async def start_async(self):
        """异步启动任务调度器"""
        if self.is_running:
            logger.warning("任务调度器已经在运行")
            return
        
        self.is_running = True
        self.shutdown_event.clear()
        self.loop = asyncio.get_event_loop()
        
        # 启动调度器主循环
        asyncio.create_task(self._scheduler_loop())
        logger.info("任务调度器已异步启动")
    
    def stop(self):
        """停止任务调度器"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.shutdown_event.set()
        
        # 取消所有运行中的任务
        for task_id, task in self.running_tasks.items():
            if not task.done():
                task.cancel()
                logger.info(f"取消任务: {task_id}")
        
        # 关闭线程池
        self.thread_pool.shutdown(wait=True)
        
        logger.info("任务调度器已停止")
    
    async def _scheduler_loop(self):
        """调度器主循环"""
        logger.info("调度器主循环已启动")
        
        while self.is_running:
            try:
                # 处理定时任务
                await self._process_scheduled_tasks()
                
                # 处理任务队列
                await self._process_task_queue()
                
                # 清理完成的任务
                await self._cleanup_completed_tasks()
                
                # 短暂休眠
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"调度器主循环异常: {e}")
                await asyncio.sleep(1)
        
        logger.info("调度器主循环已退出")
    
    async def _process_scheduled_tasks(self):
        """处理定时任务"""
        current_time = datetime.now()
        
        # 检查定时任务
        ready_tasks = []
        with self._lock:
            for task_id, task in list(self.scheduled_tasks.items()):
                if task.scheduled_time and task.scheduled_time <= current_time:
                    ready_tasks.append(task)
                    del self.scheduled_tasks[task_id]
        
        # 将就绪的任务加入执行队列
        for task in ready_tasks:
            await self._execute_task(task)
    
    async def _process_task_queue(self):
        """处理任务队列"""
        # 检查是否可以执行更多任务
        if len(self.running_tasks) >= self.max_concurrent_tasks:
            return
        
        # 从队列中取出任务执行
        tasks_to_execute = []
        with self._lock:
            available_slots = self.max_concurrent_tasks - len(self.running_tasks)
            while self.task_queue and len(tasks_to_execute) < available_slots:
                task = heapq.heappop(self.task_queue)
                tasks_to_execute.append(task)
        
        # 执行任务
        for task in tasks_to_execute:
            await self._execute_task(task)
    
    async def _execute_task(self, task: Task):
        """执行单个任务"""
        if len(self.running_tasks) >= self.max_concurrent_tasks:
            # 如果达到并发限制，重新加入队列
            with self._lock:
                heapq.heappush(self.task_queue, task)
            return
        
        task.status = TaskStatus.RUNNING
        task.result = TaskResult(
            task_id=task.id,
            status=TaskStatus.RUNNING,
            start_time=datetime.now()
        )
        
        # 创建异步任务
        async_task = asyncio.create_task(self._run_task_wrapper(task))
        self.running_tasks[task.id] = async_task
        
        logger.debug(f"开始执行任务: {task.name} ({task.id})")
    
    async def _run_task_wrapper(self, task: Task):
        """任务执行包装器"""
        try:
            # 执行任务
            if asyncio.iscoroutinefunction(task.func):
                # 异步函数
                if task.timeout:
                    result = await asyncio.wait_for(
                        task.func(*task.args, **task.kwargs),
                        timeout=task.timeout
                    )
                else:
                    result = await task.func(*task.args, **task.kwargs)
            else:
                # 同步函数，在线程池中执行
                if task.timeout:
                    result = await asyncio.wait_for(
                        self.loop.run_in_executor(
                            self.thread_pool,
                            lambda: task.func(*task.args, **task.kwargs)
                        ),
                        timeout=task.timeout
                    )
                else:
                    result = await self.loop.run_in_executor(
                        self.thread_pool,
                        lambda: task.func(*task.args, **task.kwargs)
                    )
            
            # 任务成功完成
            task.status = TaskStatus.COMPLETED
            task.result.status = TaskStatus.COMPLETED
            task.result.result = result
            task.result.end_time = datetime.now()
            task.result.execution_time = (
                task.result.end_time - task.result.start_time
            ).total_seconds()
            
            # 更新统计信息
            with self._lock:
                self.statistics['completed_tasks'] += 1
                self._update_average_execution_time(task.result.execution_time)
            
            logger.debug(f"任务执行成功: {task.name} ({task.id})")
            
        except asyncio.CancelledError:
            # 任务被取消
            task.status = TaskStatus.CANCELLED
            task.result.status = TaskStatus.CANCELLED
            task.result.end_time = datetime.now()
            
            with self._lock:
                self.statistics['cancelled_tasks'] += 1
            
            logger.info(f"任务被取消: {task.name} ({task.id})")
            
        except Exception as e:
            # 任务执行失败
            task.result.error = e
            task.result.end_time = datetime.now()
            task.result.execution_time = (
                task.result.end_time - task.result.start_time
            ).total_seconds()
            
            # 检查是否需要重试
            if task.result.retry_count < task.max_retries:
                task.status = TaskStatus.RETRYING
                task.result.status = TaskStatus.RETRYING
                task.result.retry_count += 1
                
                # 延迟后重新调度
                retry_delay = task.retry_delay * (2 ** (task.result.retry_count - 1))  # 指数退避
                task.scheduled_time = datetime.now() + timedelta(seconds=retry_delay)
                
                with self._lock:
                    self.scheduled_tasks[task.id] = task
                    self.statistics['retry_tasks'] += 1
                
                logger.warning(f"任务执行失败，将在 {retry_delay}s 后重试 (第{task.result.retry_count}次): {task.name} ({task.id}) - {e}")
            else:
                # 重试次数用尽，标记为失败
                task.status = TaskStatus.FAILED
                task.result.status = TaskStatus.FAILED
                
                with self._lock:
                    self.statistics['failed_tasks'] += 1
                
                logger.error(f"任务执行失败，重试次数用尽: {task.name} ({task.id}) - {e}")
        
        finally:
            # 从运行任务列表中移除
            if task.id in self.running_tasks:
                del self.running_tasks[task.id]
    
    async def _cleanup_completed_tasks(self):
        """清理已完成的任务"""
        # 定期清理旧的已完成任务，避免内存泄漏
        current_time = datetime.now()
        cleanup_threshold = current_time - timedelta(hours=1)  # 保留1小时内的任务记录
        
        tasks_to_remove = []
        with self._lock:
            for task_id, task in self.tasks.items():
                if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                    task.result and task.result.end_time and 
                    task.result.end_time < cleanup_threshold):
                    tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            logger.debug(f"清理旧任务记录: {task_id}")
    
    def _update_average_execution_time(self, execution_time: float):
        """更新平均执行时间"""
        completed = self.statistics['completed_tasks']
        if completed == 1:
            self.statistics['average_execution_time'] = execution_time
        else:
            current_avg = self.statistics['average_execution_time']
            self.statistics['average_execution_time'] = (
                (current_avg * (completed - 1) + execution_time) / completed
            )
    
    def submit_task(self, 
                   func: Callable, 
                   *args, 
                   name: Optional[str] = None,
                   priority: TaskPriority = TaskPriority.NORMAL,
                   max_retries: int = 3,
                   retry_delay: float = 1.0,
                   timeout: Optional[float] = None,
                   **kwargs) -> str:
        """提交任务
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            name: 任务名称
            priority: 任务优先级
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            timeout: 超时时间（秒）
            **kwargs: 函数关键字参数
            
        Returns:
            str: 任务ID
        """
        task_id = str(uuid.uuid4())
        task_name = name or f"{func.__name__}_{task_id[:8]}"
        
        task = Task(
            id=task_id,
            name=task_name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout
        )
        
        with self._lock:
            self.tasks[task_id] = task
            heapq.heappush(self.task_queue, task)
            self.statistics['total_tasks'] += 1
        
        logger.info(f"提交任务: {task_name} ({task_id})")
        return task_id
    
    def schedule_task(self, 
                     func: Callable, 
                     scheduled_time: Union[datetime, float],
                     *args,
                     name: Optional[str] = None,
                     priority: TaskPriority = TaskPriority.NORMAL,
                     max_retries: int = 3,
                     retry_delay: float = 1.0,
                     timeout: Optional[float] = None,
                     **kwargs) -> str:
        """调度定时任务
        
        Args:
            func: 要执行的函数
            scheduled_time: 调度时间（datetime对象或延迟秒数）
            *args: 函数参数
            name: 任务名称
            priority: 任务优先级
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            timeout: 超时时间（秒）
            **kwargs: 函数关键字参数
            
        Returns:
            str: 任务ID
        """
        task_id = str(uuid.uuid4())
        task_name = name or f"{func.__name__}_{task_id[:8]}"
        
        # 处理调度时间
        if isinstance(scheduled_time, (int, float)):
            scheduled_time = datetime.now() + timedelta(seconds=scheduled_time)
        
        task = Task(
            id=task_id,
            name=task_name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            scheduled_time=scheduled_time,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout
        )
        
        with self._lock:
            self.tasks[task_id] = task
            self.scheduled_tasks[task_id] = task
            self.statistics['total_tasks'] += 1
        
        logger.info(f"调度定时任务: {task_name} ({task_id}) 于 {scheduled_time}")
        return task_id
    
    def schedule_recurring_task(self,
                              func: Callable,
                              interval: float,
                              *args,
                              name: Optional[str] = None,
                              max_executions: Optional[int] = None,
                              **kwargs) -> str:
        """调度周期性任务
        
        Args:
            func: 要执行的函数
            interval: 执行间隔（秒）
            *args: 函数参数
            name: 任务名称
            max_executions: 最大执行次数（None表示无限制）
            **kwargs: 函数关键字参数
            
        Returns:
            str: 任务ID
        """
        task_id = str(uuid.uuid4())
        task_name = name or f"{func.__name__}_recurring_{task_id[:8]}"
        
        recurring_info = {
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'interval': interval,
            'name': task_name,
            'max_executions': max_executions,
            'execution_count': 0,
            'next_execution': datetime.now() + timedelta(seconds=interval)
        }
        
        with self._lock:
            self.recurring_tasks[task_id] = recurring_info
        
        # 调度第一次执行
        self._schedule_next_recurring_execution(task_id)
        
        logger.info(f"调度周期性任务: {task_name} ({task_id}) 间隔 {interval}s")
        return task_id
    
    def _schedule_next_recurring_execution(self, recurring_task_id: str):
        """调度下一次周期性任务执行"""
        if recurring_task_id not in self.recurring_tasks:
            return
        
        recurring_info = self.recurring_tasks[recurring_task_id]
        
        # 检查是否达到最大执行次数
        if (recurring_info['max_executions'] is not None and 
            recurring_info['execution_count'] >= recurring_info['max_executions']):
            del self.recurring_tasks[recurring_task_id]
            logger.info(f"周期性任务已完成所有执行: {recurring_info['name']}")
            return
        
        # 创建包装函数，执行后自动调度下一次
        def recurring_wrapper():
            try:
                result = recurring_info['func'](*recurring_info['args'], **recurring_info['kwargs'])
                recurring_info['execution_count'] += 1
                
                # 调度下一次执行
                if recurring_task_id in self.recurring_tasks:
                    next_time = datetime.now() + timedelta(seconds=recurring_info['interval'])
                    self.schedule_task(
                        self._schedule_next_recurring_execution,
                        next_time,
                        recurring_task_id,
                        name=f"schedule_next_{recurring_info['name']}"
                    )
                
                return result
            except Exception as e:
                logger.error(f"周期性任务执行失败: {recurring_info['name']} - {e}")
                raise
        
        # 调度执行
        self.schedule_task(
            recurring_wrapper,
            recurring_info['next_execution'],
            name=f"{recurring_info['name']}_exec_{recurring_info['execution_count'] + 1}"
        )
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功取消
        """
        # 取消运行中的任务
        if task_id in self.running_tasks:
            async_task = self.running_tasks[task_id]
            async_task.cancel()
            logger.info(f"取消运行中的任务: {task_id}")
            return True
        
        # 从调度队列中移除
        with self._lock:
            if task_id in self.scheduled_tasks:
                del self.scheduled_tasks[task_id]
                logger.info(f"取消定时任务: {task_id}")
                return True
            
            # 从任务队列中移除
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task in self.task_queue:
                    self.task_queue.remove(task)
                    heapq.heapify(self.task_queue)
                    task.status = TaskStatus.CANCELLED
                    logger.info(f"取消队列中的任务: {task_id}")
                    return True
            
            # 取消周期性任务
            if task_id in self.recurring_tasks:
                del self.recurring_tasks[task_id]
                logger.info(f"取消周期性任务: {task_id}")
                return True
        
        return False
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[TaskStatus]: 任务状态，如果任务不存在返回None
        """
        if task_id in self.tasks:
            return self.tasks[task_id].status
        return None
    
    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """获取任务结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[TaskResult]: 任务结果，如果任务不存在返回None
        """
        if task_id in self.tasks:
            return self.tasks[task_id].result
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取调度器统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        with self._lock:
            stats = self.statistics.copy()
            stats.update({
                'running_tasks': len(self.running_tasks),
                'queued_tasks': len(self.task_queue),
                'scheduled_tasks': len(self.scheduled_tasks),
                'recurring_tasks': len(self.recurring_tasks),
                'total_active_tasks': len(self.tasks)
            })
        return stats
    
    def list_tasks(self, status_filter: Optional[TaskStatus] = None) -> List[Dict[str, Any]]:
        """列出任务
        
        Args:
            status_filter: 状态过滤器
            
        Returns:
            List[Dict[str, Any]]: 任务列表
        """
        tasks = []
        with self._lock:
            for task in self.tasks.values():
                if status_filter is None or task.status == status_filter:
                    task_info = {
                        'id': task.id,
                        'name': task.name,
                        'status': task.status.value,
                        'priority': task.priority.value,
                        'created_time': task.created_time.isoformat(),
                        'scheduled_time': task.scheduled_time.isoformat() if task.scheduled_time else None,
                        'max_retries': task.max_retries,
                        'retry_count': task.result.retry_count if task.result else 0
                    }
                    
                    if task.result:
                        task_info.update({
                            'start_time': task.result.start_time.isoformat() if task.result.start_time else None,
                            'end_time': task.result.end_time.isoformat() if task.result.end_time else None,
                            'execution_time': task.result.execution_time,
                            'error': str(task.result.error) if task.result.error else None
                        })
                    
                    tasks.append(task_info)
        
        return tasks


# 装饰器支持
def scheduled_task(scheduler: TaskScheduler, 
                  scheduled_time: Union[datetime, float],
                  name: Optional[str] = None,
                  priority: TaskPriority = TaskPriority.NORMAL,
                  max_retries: int = 3,
                  retry_delay: float = 1.0,
                  timeout: Optional[float] = None):
    """定时任务装饰器
    
    Args:
        scheduler: 任务调度器实例
        scheduled_time: 调度时间
        name: 任务名称
        priority: 任务优先级
        max_retries: 最大重试次数
        retry_delay: 重试延迟
        timeout: 超时时间
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return scheduler.schedule_task(
                func, scheduled_time, *args,
                name=name, priority=priority,
                max_retries=max_retries, retry_delay=retry_delay,
                timeout=timeout, **kwargs
            )
        return wrapper
    return decorator


def recurring_task(scheduler: TaskScheduler,
                  interval: float,
                  name: Optional[str] = None,
                  max_executions: Optional[int] = None):
    """周期性任务装饰器
    
    Args:
        scheduler: 任务调度器实例
        interval: 执行间隔
        name: 任务名称
        max_executions: 最大执行次数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return scheduler.schedule_recurring_task(
                func, interval, *args,
                name=name, max_executions=max_executions,
                **kwargs
            )
        return wrapper
    return decorator


# 全局调度器实例
_global_scheduler: Optional[TaskScheduler] = None


def get_global_scheduler() -> TaskScheduler:
    """获取全局调度器实例"""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = TaskScheduler()
    return _global_scheduler


def start_global_scheduler():
    """启动全局调度器"""
    scheduler = get_global_scheduler()
    if not scheduler.is_running:
        scheduler.start()


def stop_global_scheduler():
    """停止全局调度器"""
    global _global_scheduler
    if _global_scheduler and _global_scheduler.is_running:
        _global_scheduler.stop()
        _global_scheduler = None