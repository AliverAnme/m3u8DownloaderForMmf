"""
定时任务调度模块 - 处理定时运行和任务管理
"""

import time
import threading
import schedule
from datetime import datetime, timedelta
from typing import Callable, Dict, Any, List, Optional
import logging
import traceback


class TaskScheduler:
    """定时任务调度器"""

    def __init__(self):
        self.is_running = False
        self.scheduler_thread = None
        self.logger = logging.getLogger('video_downloader.scheduler')
        self.tasks = {}
        self._stop_event = threading.Event()

    def add_interval_task(self, task_name: str, task_func: Callable, interval_minutes: int) -> bool:
        """添加间隔执行的任务"""
        try:
            # 添加到schedule库
            schedule.every(interval_minutes).minutes.do(self._execute_task, task_name, task_func)

            # 记录任务信息
            self.tasks[task_name] = {
                'func': task_func,
                'type': 'interval',
                'interval': interval_minutes,
                'last_run': None,
                'next_run': None,
                'status': 'scheduled'
            }

            self.logger.info(f"已添加间隔任务: {task_name} (每{interval_minutes}分钟)")
            return True

        except Exception as e:
            self.logger.error(f"添加间隔任务失败: {e}")
            return False

    def add_daily_task(self, task_name: str, task_func: Callable, time_str: str) -> bool:
        """添加每日执行的任务"""
        try:
            # 添加到schedule库
            schedule.every().day.at(time_str).do(self._execute_task, task_name, task_func)

            # 记录任务信息
            self.tasks[task_name] = {
                'func': task_func,
                'type': 'daily',
                'time': time_str,
                'last_run': None,
                'next_run': None,
                'status': 'scheduled'
            }

            self.logger.info(f"已添加每日任务: {task_name} (每天{time_str})")
            return True

        except Exception as e:
            self.logger.error(f"添加每日任务失败: {e}")
            return False

    def _execute_task(self, task_name: str, task_func: Callable):
        """执行任务的内部方法"""
        start_time = datetime.now()

        try:
            self.logger.info(f"开始执行任务: {task_name}")

            # 更新任务状态
            if task_name in self.tasks:
                self.tasks[task_name]['status'] = 'running'
                self.tasks[task_name]['last_run'] = start_time.isoformat()

            # 执行任务
            result = task_func()

            # 记录执行结果
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            if result:
                self.logger.info(f"任务 {task_name} 执行成功，耗时 {duration:.2f} 秒")
                status = 'completed'
            else:
                self.logger.warning(f"任务 {task_name} 执行失败，耗时 {duration:.2f} 秒")
                status = 'failed'

            # 更新任务状态
            if task_name in self.tasks:
                self.tasks[task_name]['status'] = status

        except Exception as e:
            self.logger.error(f"任务 {task_name} 执行异常: {e}")
            self.logger.error(traceback.format_exc())

            if task_name in self.tasks:
                self.tasks[task_name]['status'] = 'error'

    def start(self):
        """启动调度器"""
        if self.is_running:
            self.logger.warning("调度器已在运行")
            return

        self.is_running = True
        self._stop_event.clear()

        # 在新线程中运行调度器
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()

        self.logger.info("定时任务调度器已启动")

    def stop(self):
        """停止调度器"""
        if not self.is_running:
            return

        self.is_running = False
        self._stop_event.set()

        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)

        # 清除所有任务
        schedule.clear()

        self.logger.info("定时任务调度器已停止")

    def _scheduler_loop(self):
        """调度器主循环"""
        self.logger.info("调度器主循环开始")

        while self.is_running and not self._stop_event.is_set():
            try:
                # 运行待执行的任务
                schedule.run_pending()

                # 更新下次运行时间
                self._update_next_run_times()

                # 短暂休眠
                self._stop_event.wait(timeout=30)  # 每30秒检查一次

            except Exception as e:
                self.logger.error(f"调度器循环异常: {e}")
                time.sleep(60)  # 出错时等待1分钟再重试

        self.logger.info("调度器主循环结束")

    def _update_next_run_times(self):
        """更新任务的下次运行时间"""
        for job in schedule.jobs:
            if hasattr(job, 'job_func') and hasattr(job.job_func, 'args'):
                task_name = job.job_func.args[0] if job.job_func.args else None
                if task_name and task_name in self.tasks:
                    next_run = job.next_run
                    if next_run:
                        self.tasks[task_name]['next_run'] = next_run.isoformat()

    def get_task_info(self) -> Dict[str, Any]:
        """获取任务信息"""
        return {
            'is_running': self.is_running,
            'total_tasks': len(self.tasks),
            'tasks': dict(self.tasks)
        }

    def remove_task(self, task_name: str) -> bool:
        """移除指定任务"""
        try:
            # 从schedule中移除
            for job in schedule.jobs[:]:  # 创建副本以避免在迭代时修改
                if (hasattr(job, 'job_func') and hasattr(job.job_func, 'args') and
                    job.job_func.args and job.job_func.args[0] == task_name):
                    schedule.cancel_job(job)

            # 从任务字典中移除
            if task_name in self.tasks:
                del self.tasks[task_name]
                self.logger.info(f"已移除任务: {task_name}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"移除任务失败: {e}")
            return False

    def is_task_running(self, task_name: str) -> bool:
        """检查任务是否正在运行"""
        return (task_name in self.tasks and
                self.tasks[task_name]['status'] == 'running')


class SchedulerConfig:
    """调度器配置类"""

    def __init__(self):
        self.auto_start = True
        self.fetch_interval_minutes = 60  # 每小时获取一次新视频
        self.upload_interval_minutes = 120  # 每2小时上传一次
        self.cleanup_time = "03:00"  # 每天凌晨3点清理

    def to_dict(self) -> Dict[str, Any]:
        return {
            'auto_start': self.auto_start,
            'fetch_interval_minutes': self.fetch_interval_minutes,
            'upload_interval_minutes': self.upload_interval_minutes,
            'cleanup_time': self.cleanup_time
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SchedulerConfig':
        config = cls()
        config.auto_start = data.get('auto_start', True)
        config.fetch_interval_minutes = data.get('fetch_interval_minutes', 60)
        config.upload_interval_minutes = data.get('upload_interval_minutes', 120)
        config.cleanup_time = data.get('cleanup_time', "03:00")
        return config
