"""
定时任务调度模块 - 处理定时运行和任务管理
"""

import time
import threading
import schedule
from datetime import datetime, timedelta
from typing import Callable, Dict, Any, List
import logging
import traceback
import signal
import os
import sys

from ..core.config import Config


class TaskScheduler:
    """定时任务调度器"""

    def __init__(self):
        self.is_running = False
        self.scheduler_thread = None
        self.tasks = {}
        self.logger = self._setup_logger()
        self._shutdown_event = threading.Event()
        self._task_lock = threading.RLock()
        self._max_concurrent_tasks = 3  # 限制并发任务数
        self._running_tasks = set()

        # 注册信号处理器
        self._register_signal_handlers()

    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('scheduler')
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            # 使用RotatingFileHandler防止日志文件过大
            from logging.handlers import RotatingFileHandler
            handler = RotatingFileHandler(
                'scheduler.log',
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

            # 同时输出到控制台（非守护进程模式）
            if not getattr(Config, 'DAEMON_MODE', False):
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                logger.addHandler(console_handler)

        return logger

    def _register_signal_handlers(self):
        """注册信号处理器"""
        def signal_handler(signum, frame):
            self.logger.info(f"收到信号 {signum}，开始安全关闭调度器...")
            self.stop()

        # 注册常见的终止信号
        for sig in [signal.SIGINT, signal.SIGTERM]:
            try:
                signal.signal(sig, signal_handler)
            except (ValueError, OSError):
                # 在某些环境中可能无法注册信号处理器
                pass

    def add_interval_task(self, task_name: str, func: Callable,
                         interval_minutes: int, *args, **kwargs) -> bool:
        """添加间隔执行的任务"""
        with self._task_lock:
            try:
                # 验证参数
                if not task_name or not task_name.strip():
                    self.logger.error("任务名称不能为空")
                    return False

                if interval_minutes <= 0:
                    self.logger.error("执行间隔必须大于0")
                    return False

                if not callable(func):
                    self.logger.error("任务函数必须是可调用的")
                    return False

                # 检查任务是否已存在
                if task_name in self.tasks:
                    self.logger.warning(f"任务 {task_name} 已存在，将被替换")
                    self.remove_task(task_name)

                # 包装任务函数，添加错误处理和日志
                def wrapped_task():
                    if task_name in self._running_tasks:
                        self.logger.warning(f"任务 {task_name} 正在运行中，跳过本次执行")
                        return

                    if len(self._running_tasks) >= self._max_concurrent_tasks:
                        self.logger.warning(f"并发任务数达到限制 ({self._max_concurrent_tasks})，跳过任务 {task_name}")
                        return

                    self._running_tasks.add(task_name)
                    try:
                        self.logger.info(f"开始执行任务: {task_name}")
                        start_time = datetime.now()

                        # 设置任务超时（默认30分钟）
                        timeout = kwargs.pop('timeout', 1800)
                        result = self._run_with_timeout(func, timeout, *args, **kwargs)

                        end_time = datetime.now()
                        duration = (end_time - start_time).total_seconds()
                        self.logger.info(f"任务 {task_name} 执行完成，耗时: {duration:.2f}秒")
                        return result
                    except Exception as e:
                        self.logger.error(f"任务 {task_name} 执行失败: {e}")
                        self.logger.error(traceback.format_exc())
                    finally:
                        self._running_tasks.discard(task_name)

                # 添加到schedule
                job = schedule.every(interval_minutes).minutes.do(wrapped_task)
                self.tasks[task_name] = {
                    'job': job,
                    'function': func,
                    'type': 'interval',
                    'interval': interval_minutes,
                    'args': args,
                    'kwargs': kwargs,
                    'created_at': datetime.now(),
                    'last_run': None,
                    'run_count': 0,
                    'error_count': 0
                }

                self.logger.info(f"任务 {task_name} 已添加，执行间隔: {interval_minutes}分钟")
                return True

            except Exception as e:
                self.logger.error(f"添加任务 {task_name} 失败: {e}")
                return False

    def _run_with_timeout(self, func: Callable, timeout: int, *args, **kwargs):
        """带超时的任务执行"""
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                self.logger.error(f"任务执行超时 ({timeout}秒)")
                raise TimeoutError(f"任务执行超时 ({timeout}秒)")

    def add_daily_task(self, task_name: str, func: Callable,
                      time_str: str, *args, **kwargs) -> bool:
        """添加每日执行的任务"""
        with self._task_lock:
            try:
                # 验证时间格式
                try:
                    datetime.strptime(time_str, "%H:%M")
                except ValueError:
                    self.logger.error(f"时间格式无效: {time_str}，应为 HH:MM 格式")
                    return False

                # 验证参数
                if not task_name or not task_name.strip():
                    self.logger.error("任务名称不能为空")
                    return False

                if not callable(func):
                    self.logger.error("任务函数必须是可调用的")
                    return False

                # 检查任务是否已存在
                if task_name in self.tasks:
                    self.logger.warning(f"任务 {task_name} 已存在，将被替换")
                    self.remove_task(task_name)

                def wrapped_task():
                    if task_name in self._running_tasks:
                        self.logger.warning(f"每日任务 {task_name} 正在运行中，跳过本次执行")
                        return

                    self._running_tasks.add(task_name)
                    try:
                        self.logger.info(f"开始执行每日任务: {task_name}")
                        start_time = datetime.now()

                        # 每日任务默认超时2小时
                        timeout = kwargs.pop('timeout', 7200)
                        result = self._run_with_timeout(func, timeout, *args, **kwargs)

                        end_time = datetime.now()
                        duration = (end_time - start_time).total_seconds()
                        self.logger.info(f"每日任务 {task_name} 执行完成，耗时: {duration:.2f}秒")

                        # 更新任务统计
                        if task_name in self.tasks:
                            self.tasks[task_name]['last_run'] = datetime.now()
                            self.tasks[task_name]['run_count'] += 1

                        return result
                    except Exception as e:
                        self.logger.error(f"每日任务 {task_name} 执行失败: {e}")
                        self.logger.error(traceback.format_exc())

                        # 更新错误统计
                        if task_name in self.tasks:
                            self.tasks[task_name]['error_count'] += 1
                    finally:
                        self._running_tasks.discard(task_name)

                job = schedule.every().day.at(time_str).do(wrapped_task)
                self.tasks[task_name] = {
                    'job': job,
                    'function': func,
                    'type': 'daily',
                    'time': time_str,
                    'args': args,
                    'kwargs': kwargs,
                    'created_at': datetime.now(),
                    'last_run': None,
                    'run_count': 0,
                    'error_count': 0
                }

                self.logger.info(f"每日任务 {task_name} 已添加，执行时间: {time_str}")
                return True

            except Exception as e:
                self.logger.error(f"添加每日任务 {task_name} 失败: {e}")
                return False

    def remove_task(self, task_name: str) -> bool:
        """移除任务"""
        with self._task_lock:
            if task_name in self.tasks:
                try:
                    schedule.cancel_job(self.tasks[task_name]['job'])
                    del self.tasks[task_name]
                    self.logger.info(f"任务 {task_name} 已移除")
                    return True
                except Exception as e:
                    self.logger.error(f"移除任务 {task_name} 失败: {e}")
                    return False
            return False

    def get_task_info(self) -> List[Dict[str, Any]]:
        """获取所有任务信息"""
        with self._task_lock:
            task_list = []
            for name, task in self.tasks.items():
                info = {
                    'name': name,
                    'type': task['type'],
                    'created_at': task['created_at'].isoformat(),
                    'last_run': task['last_run'].isoformat() if task['last_run'] else None,
                    'run_count': task['run_count'],
                    'error_count': task['error_count'],
                    'is_running': name in self._running_tasks,
                    'next_run': None
                }

                # 获取下次运行时间
                try:
                    if hasattr(task['job'], 'next_run') and task['job'].next_run:
                        info['next_run'] = task['job'].next_run.isoformat()
                except:
                    pass

                # 添加任务特定信息
                if task['type'] == 'interval':
                    info['interval_minutes'] = task['interval']
                elif task['type'] == 'daily':
                    info['time'] = task['time']

                task_list.append(info)

            return task_list

    def start(self):
        """启动调度器"""
        with self._task_lock:
            if self.is_running:
                self.logger.warning("调度器已在运行中")
                return

            self.is_running = True
            self._shutdown_event.clear()

            def run_scheduler():
                self.logger.info("任务调度器已启动")
                consecutive_errors = 0
                max_consecutive_errors = 5

                while self.is_running and not self._shutdown_event.is_set():
                    try:
                        schedule.run_pending()
                        consecutive_errors = 0  # 重置错误计数

                        # 使用事件等待而不是简单的sleep，以便快速响应关闭信号
                        self._shutdown_event.wait(30)  # 每30秒检查一次

                    except Exception as e:
                        consecutive_errors += 1
                        self.logger.error(f"调度器运行异常: {e}")

                        if consecutive_errors >= max_consecutive_errors:
                            self.logger.error(f"连续 {max_consecutive_errors} 次错误，调度器将停止")
                            break

                        # 错误后等待更长时间
                        self._shutdown_event.wait(60)

                self.logger.info("调度器线程已退出")

            self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=False)
            self.scheduler_thread.start()

            self.logger.info(f"调度器启动成功，当前有 {len(self.tasks)} 个任务")

    def stop(self):
        """停止调度器"""
        with self._task_lock:
            if not self.is_running:
                return

            self.logger.info("正在停止调度器...")
            self.is_running = False
            self._shutdown_event.set()

            # 等待正在运行的任务完成（最多等待5分钟）
            if self._running_tasks:
                self.logger.info(f"等待 {len(self._running_tasks)} 个正在运行的任务完成...")
                timeout = 300  # 5分钟
                start_time = time.time()

                while self._running_tasks and (time.time() - start_time) < timeout:
                    time.sleep(1)

                if self._running_tasks:
                    self.logger.warning(f"仍有 {len(self._running_tasks)} 个任务未完成，强制停止")

            # 等待调度器线程结束
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=10)
                if self.scheduler_thread.is_alive():
                    self.logger.warning("调度器线程未能在10秒内正常结束")

            self.logger.info("任务调度器已停止")

    def run_task_once(self, task_name: str) -> bool:
        """立即执行指定任务一次"""
        with self._task_lock:
            if task_name not in self.tasks:
                self.logger.error(f"任务 {task_name} 不存在")
                return False

            if task_name in self._running_tasks:
                self.logger.warning(f"任务 {task_name} 正在运行中")
                return False

            try:
                task = self.tasks[task_name]
                self.logger.info(f"手动执行任务: {task_name}")

                # 在单独的线程中执行任务以避免阻塞
                def execute_task():
                    self._running_tasks.add(task_name)
                    try:
                        start_time = datetime.now()
                        result = task['function'](*task['args'], **task['kwargs'])
                        end_time = datetime.now()
                        duration = (end_time - start_time).total_seconds()

                        # 更新统计信息
                        task['last_run'] = datetime.now()
                        task['run_count'] += 1

                        self.logger.info(f"手动任务 {task_name} 执行完成，耗时: {duration:.2f}秒")
                        return result
                    except Exception as e:
                        task['error_count'] += 1
                        self.logger.error(f"手动执行任务 {task_name} 失败: {e}")
                        self.logger.error(traceback.format_exc())
                        return False
                    finally:
                        self._running_tasks.discard(task_name)

                # 启动执行线程
                exec_thread = threading.Thread(target=execute_task, daemon=True)
                exec_thread.start()

                return True

            except Exception as e:
                self.logger.error(f"启动手动任务 {task_name} 失败: {e}")
                return False

    def get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        with self._task_lock:
            return {
                'is_running': self.is_running,
                'total_tasks': len(self.tasks),
                'running_tasks': len(self._running_tasks),
                'running_task_names': list(self._running_tasks),
                'max_concurrent_tasks': self._max_concurrent_tasks,
                'thread_alive': self.scheduler_thread.is_alive() if self.scheduler_thread else False
            }


class SchedulerConfig:
    """调度器配置"""

    # 默认任务配置
    DEFAULT_FETCH_INTERVAL = 120  # 2小时获取一次新数据
    DEFAULT_UPLOAD_INTERVAL = 60   # 1小时检查一次上传
    DEFAULT_CLEANUP_TIME = "03:00"  # 凌晨3点清理

    # 任务重试配置
    MAX_RETRIES = 3
    RETRY_DELAY = 300  # 5分钟后重试

    # 超时配置
    DEFAULT_TASK_TIMEOUT = 1800  # 30分钟
    DAILY_TASK_TIMEOUT = 7200   # 2小时

    # 并发限制
    MAX_CONCURRENT_TASKS = 3

    # 日志配置
    LOG_LEVEL = logging.INFO
    LOG_FILE = "scheduler.log"
    MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
