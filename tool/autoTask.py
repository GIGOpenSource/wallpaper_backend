import pickle
import random
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.utils import timezone

import logging

# 导入定时任务
from App.view.tasks.hot_score_update import update_hot_score_daily
from App.view.tasks.sync_wallpaper_counts import sync_wallpaper_all_counts

logger = logging.getLogger(__name__)

fixed_exec_time = timezone.make_aware(
    datetime(2025, 10, 16, 10, 42, 0)  # 年、月、日、时、分、秒
)

class DjangoTaskScheduler:
    def __init__(self):
        # 初始化调度器
        self.scheduler = BackgroundScheduler(
            timezone=timezone.get_current_timezone_name()
        )
        # 添加数据库存储
        self.scheduler.add_jobstore(DjangoJobStore(), 'default')
        self.is_running = False

    def start(self):
        """启动调度器"""
        if not self.is_running:
            try:
                self.scheduler.start()
                self.is_running = True
                logging.info("调度器启动成功")
            except Exception as e:
                logging.info(f"调度器启动失败:  ")
                self.shutdown()

    def shutdown(self):
        """关闭调度器"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logging.info("调度器已关闭")

    def add_job(self, func, trigger, job_id, fixed_time=None,replace_existing=True, nums=None, **kwargs):
        """
        添加定时任务
        :param func: 任务函数
        :param trigger: 触发器类型 (如 'cron周期特定时间点执行', 'interval间隔', 'date日期')
        :param job_id: 任务唯一标识
        :param replace_existing: 是否替换已存在的任务
        :param kwargs: 触发器参数 (如 hour, minute 等)
        """
        try:
            if trigger == "cron":
                # 标准 cron 触发器，直接传递给 APScheduler
                self.scheduler.add_job(
                    func,
                    trigger='cron',
                    id=job_id,
                    replace_existing=replace_existing,
                    **kwargs
                )
                logging.info(f"Cron任务 {job_id} 添加成功")
            elif trigger == "daily":
                """
                每日执行N次  trigger=daily    nums=1~5
                """
                if nums is None or not (1 <= nums <= 5):
                    raise ValueError("当trigger为'daily'时，nums必须为1~5之间的整数")

                random_times = []
                for _ in range(nums):
                    hour = random.randint(0, 23)
                    minute = random.randint(0, 59)
                    random_times.append((hour, minute))

                random_times.sort()

                hours = [str(time[0]) for time in random_times]
                minutes = [str(time[1]) for time in random_times]

                hour_str = ",".join(hours)
                minute_str = ",".join(minutes)
                self.scheduler.add_job(
                    func,
                    trigger='cron',
                    id=job_id,
                    hour=hour_str,
                    minute=minute_str,  # 可指定分钟，默认0分
                    replace_existing=replace_existing,
                    args=kwargs.get('args', ()),
                    kwargs=kwargs.get('kwargs', {})
                )
                logging.info(f"每日随机任务 {job_id} 添加成功，每日执行{nums}次，时间点：{random_times}时")
            elif trigger == "weekly":
                """
                每周执行N次
                """
                if nums is None or not (1 <= nums <= 7):
                    raise ValueError("当trigger为'weekly'时，nums必须为1~7之间的整数")
                # 获取一周中的N个随机星期几（例如：周一、周三、周五）
                days_of_week = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
                selected_days = random.sample(days_of_week, nums)
                selected_days.sort()

                self.scheduler.add_job(
                    func,
                    trigger='cron',
                    id=job_id,
                    day_of_week=','.join(selected_days),
                    hour=kwargs.get('hour', 0),
                    minute=kwargs.get('minute', 0),
                    replace_existing=replace_existing,
                    args=kwargs.get('args', ()),
                    kwargs=kwargs.get('kwargs', {})
                )
                logging.info(f"每周任务 {job_id} 添加成功，每周在{selected_days}执行")
            elif trigger == "monthly":
                """
                每月执行N次
                """
                if nums is None or not (1 <= nums <= 31):
                    raise ValueError("当trigger为'monthly'时，nums必须为1~31之间的整数")
                # 获取一个月中的N个随机日期（例如：1号、15号、28号）
                selected_dates = random.sample(range(1, 32), nums)
                selected_dates.sort()
                self.scheduler.add_job(
                    func,
                    trigger='cron',
                    id=job_id,
                    day=','.join(map(str, selected_dates)),
                    hour=kwargs.get('hour', 0),
                    minute=kwargs.get('minute', 0),
                    replace_existing=replace_existing,
                    args=kwargs.get('args', ()),
                    kwargs=kwargs.get('kwargs', {})
                )
                logging.info(f"每月任务 {job_id} 添加成功，每月在{selected_dates}号执行")
            elif trigger == "fixed":
                """
                每fixed 
                """
                scheduler.add_job(
                    func,
                    trigger='date',
                    job_id=job_id,
                    run_date=fixed_time,
                    args=kwargs.get('args', ()),
                    kwargs=kwargs.get('kwargs', {})
                )
                logging.info(f"固定任务 {job_id} 添加成功，每日执行{nums}次，时间点：{fixed_time}时")
            elif trigger == "fixed213":
                self.scheduler.add_job(
                        func,
                        trigger=trigger,
                        id=job_id,
                        replace_existing=replace_existing, **kwargs
                )
                logging.info(f"任务 {job_id} 添加成功")
            elif trigger == 'timing':
                # 每小时执行一次：使用cron触发器，分钟固定为0（整点执行），小时不限制（* 表示每小时）
                self.scheduler.add_job(
                    func,
                    trigger='cron',  # 定时循环执行用cron触发器
                    id=job_id,
                    hour=0,  # 每小时（0-23点均执行）
                    minute=0,  # 固定在每小时的0分执行（可根据需要调整，如minute=30表示每小时30分）
                    replace_existing=True,  # 若存在同名job_id，替换旧任务
                    args=(),  # 无参数传递时用空元组
                    kwargs={}  # 无关键字参数时用空字典
                )
                logging.info(f"定时任务{job_id} 添加成功")
        except Exception as e:
            logging.info(f"添加任务 {job_id} 失败: {e}")

    def remove_job(self, job_id):
        """删除定时任务"""
        try:
            self.scheduler.remove_job(job_id)
            logging.info(f"任务 {job_id} 已删除")
        except Exception as e:
            logging.info(f"删除任务 {job_id} 失败: {e}")

    def pause_job(self, job_id):
        """暂停定时任务"""
        try:
            self.scheduler.pause_job(job_id)
            logging.info(f"任务 {job_id} 已暂停")
        except Exception as e:
            logging.info(f"暂停任务 {job_id} 失败: {e}")

    def resume_job(self, job_id):
        """恢复定时任务"""
        try:
            self.scheduler.resume_job(job_id)
            logging.info(f"任务 {job_id} 已恢复")
        except Exception as e:
            logging.info(f"恢复任务 {job_id} 失败: {e}")

    def modify_job(self, job_id, **kwargs):
        try:
            old_job = self.scheduler.get_job(job_id)
            if not old_job:
                logging.error(f"任务 {job_id} 不存在")
                return False

            logging.info(f"修改前任务 {job_id} 触发器: {old_job.trigger}")
            logging.info(f"修改前任务 {job_id} 下次执行: {old_job.next_run_time}")

            # 提取时间字段
            trigger_fields = ['year', 'month', 'day', 'day_of_week', 'hour', 'minute', 'second']
            cron_kwargs = {k: v for k, v in kwargs.items() if k in trigger_fields}

            # --------------------------
            # 核心：reschedule_job + 强制计算下次运行时间
            # --------------------------
            if cron_kwargs:
                from apscheduler.triggers.cron import CronTrigger
                trigger = CronTrigger(**cron_kwargs)

                # 手动计算最近的下一次执行时间（解决 None 问题）
                now = datetime.now(self.scheduler.timezone)
                next_run_time = trigger.get_next_fire_time(None, now)

                # 直接修改任务（官方底层最终方案）
                self.scheduler.modify_job(
                    job_id,
                    trigger=trigger,
                    next_run_time=next_run_time  # 强制写入！
                )

            # 修改其他参数
            other_kwargs = {k: v for k, v in kwargs.items() if k not in trigger_fields}
            if other_kwargs:
                self.scheduler.modify_job(job_id, **other_kwargs)

            # 最终验证
            new_job = self.scheduler.get_job(job_id)
            logging.info(f"修改后任务 {job_id} 触发器: {new_job.trigger}")
            logging.info(f"修改后任务 {job_id} 下次执行: {new_job.next_run_time}")
            logging.info(f"任务 {job_id} 修改成功. ✅")
            return True

        except Exception as e:
            logging.error(f"修改任务失败: {e}", exc_info=True)
            raise

    def get_all_jobs(self):
        """获取所有定时任务"""
        try:
            jobs = self.scheduler.get_jobs()
            logging.info(f"获取到 {len(jobs)} 个任务")
            return jobs
        except Exception as e:
            logging.info(f"获取任务失败: {e}")
            return []

    def get_job(self, job_id):
        """获取指定任务"""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                logging.info(f"获取任务 {job_id} 成功")
                return job
            else:
                logging.info(f"任务 {job_id} 不存在")
                return None
        except Exception as e:
            logging.error(f"获取任务 {job_id} 失败: {e}")
            return None

    def delete_job(self, job_id):
        """删除定时任务"""
        try:
            self.scheduler.remove_job(job_id)
            logging.info(f"任务 {job_id} 已删除")
            return True
        except Exception as e:
            logging.info(f"删除任务 {job_id} 失败: {e}")
            return False
# 初始化调度器
scheduler = DjangoTaskScheduler()
scheduler.start()

logger.info("调度器启动完成，等待任务注册")

def user_stat_task(user_id, task_desc):
    """用户统计任务函数"""
    logging.info(f"执行用户统计任务：用户ID={user_id}，任务描述={task_desc}")

# scheduler.get_all_jobs("user_stat_daily_1001")