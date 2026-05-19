#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：views.py
@Author  ：AI Assistant
@Date    ：2026/5/19
@description : 定时任务管理视图
"""
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from tool.base_views import BaseViewSet
from tool.permissions import IsAdmin
from tool.utils import ApiResponse
from tool.autoTask import scheduler
from App.view.tasks.hot_score_update import update_hot_score_daily
from App.view.tasks.sync_wallpaper_counts import sync_wallpaper_all_counts
import logging

logger = logging.getLogger(__name__)


# 定义可管理的任务列表
MANAGEABLE_JOBS = {
    'update_hot_score_daily': {
        'name': '更新热门评分',
        'description': '每日凌晨3点更新壁纸热门评分',
        'func': update_hot_score_daily,
        'default_hour': 3,
        'default_minute': 0
    },
    'sync_wallpaper_all_counts': {
        'name': '同步壁纸计数',
        'description': '同步评论数、点赞数、收藏数',
        'func': sync_wallpaper_all_counts,
        'default_hour': 4,
        'default_minute': 0
    }
}


@extend_schema(tags=["(Admin)定时任务管理"])
@extend_schema_view(
    list=extend_schema(
        summary="获取所有定时任务状态",
        description="返回系统中所有可管理的定时任务的当前状态",
    ),
)
class TaskManagementViewSet(BaseViewSet):
    """
    定时任务管理 ViewSet
    提供启动、停止、暂停、恢复、设置执行时间的功能
    """
    permission_classes = [IsAdmin]
    
    def list(self, request, *args, **kwargs):
        """
        获取所有可管理任务的状态
        """
        jobs_info = []
        
        for job_id, job_info in MANAGEABLE_JOBS.items():
            job = scheduler.get_job(job_id)
            
            # 检查任务是否存在
            if job is None:
                status = 'stopped'
                next_run_time = None
            else:
                # job 是 Job 对象
                if job.next_run_time:
                    status = 'running'
                    next_run_time = str(job.next_run_time)
                else:
                    status = 'paused'
                    next_run_time = None
            
            jobs_info.append({
                'job_id': job_id,
                'name': job_info['name'],
                'description': job_info['description'],
                'status': status,
                'next_run_time': next_run_time
            })
        
        return ApiResponse(data=jobs_info, message="获取成功")
    
    @extend_schema(
        summary="启动定时任务",
        description="启动指定的定时任务，如果任务不存在则重新添加",
        parameters=[
            OpenApiParameter(
                name='job_id',
                type=str,
                required=True,
                description='任务ID',
                enum=['update_hot_score_daily', 'sync_wallpaper_all_counts']
            )
        ],
    )
    @action(detail=False, methods=['post'], url_path='start')
    def start_task(self, request):
        """
        启动定时任务
        """
        job_id = request.data.get('job_id')
        
        if not job_id:
            return ApiResponse(code=400, message="请提供任务ID (job_id)")
        
        if job_id not in MANAGEABLE_JOBS:
            return ApiResponse(code=404, message=f"任务 {job_id} 不存在或不可管理")
        
        try:
            job = scheduler.get_job(job_id)
            job_config = MANAGEABLE_JOBS[job_id]
            
            # 检查任务是否存在
            if job is None:
                # 任务不存在，重新添加
                scheduler.add_job(
                    func=job_config['func'],
                    trigger='cron',
                    job_id=job_id,
                    hour=job_config['default_hour'],
                    minute=job_config['default_minute'],
                    replace_existing=True
                )
                logger.info(f"任务 {job_id} 已重新添加")
                return ApiResponse(message=f"任务 {job_id} 已启动")
            else:
                # 任务已存在，恢复执行
                scheduler.resume_job(job_id)
                logger.info(f"任务 {job_id} 已恢复")
                return ApiResponse(message=f"任务 {job_id} 已恢复运行")
                
        except Exception as e:
            logger.error(f"启动任务 {job_id} 失败: {e}")
            return ApiResponse(code=500, message=f"启动任务失败: {str(e)}")
    
    @extend_schema(
        summary="停止定时任务",
        description="删除指定的定时任务",
        parameters=[
            OpenApiParameter(
                name='job_id',
                type=str,
                required=True,
                description='任务ID',
                enum=['update_hot_score_daily', 'sync_wallpaper_all_counts']
            )
        ],
    )
    @action(detail=False, methods=['post'], url_path='stop')
    def stop_task(self, request):
        """
        停止定时任务（删除）
        """
        job_id = request.data.get('job_id')
        
        if not job_id:
            return ApiResponse(code=400, message="请提供任务ID (job_id)")
        
        if job_id not in MANAGEABLE_JOBS:
            return ApiResponse(code=404, message=f"任务 {job_id} 不存在或不可管理")
        
        try:
            job = scheduler.get_job(job_id)
            
            # 检查任务是否存在
            if job is None:
                return ApiResponse(code=404, message=f"任务 {job_id} 不存在")
            
            # 删除任务
            scheduler.delete_job(job_id)
            logger.info(f"任务 {job_id} 已删除")
            return ApiResponse(message=f"任务 {job_id} 已停止")
            
        except Exception as e:
            logger.error(f"停止任务 {job_id} 失败: {e}")
            return ApiResponse(code=500, message=f"停止任务失败: {str(e)}")
    
    @extend_schema(
        summary="暂停定时任务",
        description="暂停指定的定时任务，任务配置保留但不执行",
        parameters=[
            OpenApiParameter(
                name='job_id',
                type=str,
                required=True,
                description='任务ID',
                enum=['update_hot_score_daily', 'sync_wallpaper_all_counts']
            )
        ],
    )
    @action(detail=False, methods=['post'], url_path='pause')
    def pause_task(self, request):
        """
        暂停定时任务
        """
        job_id = request.data.get('job_id')
        
        if not job_id:
            return ApiResponse(code=400, message="请提供任务ID (job_id)")
        
        if job_id not in MANAGEABLE_JOBS:
            return ApiResponse(code=404, message=f"任务 {job_id} 不存在或不可管理")
        
        try:
            job = scheduler.get_job(job_id)
            
            # 检查任务是否存在
            if job is None:
                return ApiResponse(code=404, message=f"任务 {job_id} 不存在")
            
            # 暂停任务
            scheduler.pause_job(job_id)
            logger.info(f"任务 {job_id} 已暂停")
            return ApiResponse(message=f"任务 {job_id} 已暂停")
            
        except Exception as e:
            logger.error(f"暂停任务 {job_id} 失败: {e}")
            return ApiResponse(code=500, message=f"暂停任务失败: {str(e)}")
    
    @extend_schema(
        summary="恢复定时任务",
        description="恢复已暂停的定时任务",
        parameters=[
            OpenApiParameter(
                name='job_id',
                type=str,
                required=True,
                description='任务ID',
                enum=['update_hot_score_daily', 'sync_wallpaper_all_counts']
            )
        ],
    )
    @action(detail=False, methods=['post'], url_path='resume')
    def resume_task(self, request):
        """
        恢复定时任务
        """
        job_id = request.data.get('job_id')
        
        if not job_id:
            return ApiResponse(code=400, message="请提供任务ID (job_id)")
        
        if job_id not in MANAGEABLE_JOBS:
            return ApiResponse(code=404, message=f"任务 {job_id} 不存在或不可管理")
        
        try:
            job = scheduler.get_job(job_id)
            
            # 检查任务是否存在
            if job is None:
                return ApiResponse(code=404, message=f"任务 {job_id} 不存在")
            
            # 恢复任务
            scheduler.resume_job(job_id)
            logger.info(f"任务 {job_id} 已恢复")
            return ApiResponse(message=f"任务 {job_id} 已恢复运行")
            
        except Exception as e:
            logger.error(f"恢复任务 {job_id} 失败: {e}")
            return ApiResponse(code=500, message=f"恢复任务失败: {str(e)}")
    
    @extend_schema(
        summary="设置定时任务执行时间",
        description="修改定时任务的执行时间，支持设置年月日时分秒，不设置的字段默认为每天/每月/每年执行",
        parameters=[
            OpenApiParameter(
                name='job_id',
                type=str,
                required=True,
                description='任务ID',
                enum=['update_hot_score_daily', 'sync_wallpaper_all_counts']
            ),
            OpenApiParameter(
                name='hour',
                type=int,
                required=False,
                description='执行小时（0-23），不传则保持原值'
            ),
            OpenApiParameter(
                name='minute',
                type=int,
                required=False,
                description='执行分钟（0-59），不传则保持原值'
            ),
            OpenApiParameter(
                name='second',
                type=int,
                required=False,
                description='执行秒数（0-59），不传则保持原值'
            ),
            OpenApiParameter(
                name='day',
                type=str,
                required=False,
                description='执行日期（1-31或*），*表示每天，不传则保持原值'
            ),
            OpenApiParameter(
                name='month',
                type=str,
                required=False,
                description='执行月份（1-12或*），*表示每月，不传则保持原值'
            ),
            OpenApiParameter(
                name='year',
                type=str,
                required=False,
                description='执行年份（如2026或*），*表示每年，不传则保持原值'
            ),
            OpenApiParameter(
                name='day_of_week',
                type=str,
                required=False,
                description='星期几（0-6或mon-sun，多个用逗号分隔，或*），*表示每天，不传则保持原值'
            )
        ],
    )
    @action(detail=False, methods=['post'], url_path='set-schedule')
    def set_schedule(self, request):
        """
        设置定时任务执行时间
        """
        job_id = request.data.get('job_id') or request.query_params.get('job_id')
        hour = request.data.get('hour') or request.query_params.get('hour')
        minute = request.data.get('minute') or request.query_params.get('minute')
        second = request.data.get('second') or request.query_params.get('second')
        day = request.data.get('day') or request.query_params.get('day')
        month = request.data.get('month') or request.query_params.get('month')
        year = request.data.get('year') or request.query_params.get('year')
        day_of_week = request.data.get('day_of_week') or request.query_params.get('day_of_week')
        
        # 转换类型为整数
        if hour is not None:
            try:
                hour = int(hour)
                if not (0 <= hour <= 23):
                    return ApiResponse(code=400, message="小时范围为0-23")
            except (ValueError, TypeError):
                return ApiResponse(code=400, message="小时必须为整数")
        
        if minute is not None:
            try:
                minute = int(minute)
                if not (0 <= minute <= 59):
                    return ApiResponse(code=400, message="分钟范围为0-59")
            except (ValueError, TypeError):
                return ApiResponse(code=400, message="分钟必须为整数")
        
        if second is not None:
            try:
                second = int(second)
                if not (0 <= second <= 59):
                    return ApiResponse(code=400, message="秒数范围为0-59")
            except (ValueError, TypeError):
                return ApiResponse(code=400, message="秒数必须为整数")
        
        if not job_id:
            return ApiResponse(code=400, message="请提供任务ID (job_id)")
        
        if job_id not in MANAGEABLE_JOBS:
            return ApiResponse(code=404, message=f"任务 {job_id} 不存在或不可管理")
        
        try:
            job = scheduler.get_job(job_id)
            job_config = MANAGEABLE_JOBS[job_id]
            
            # 检查任务是否存在
            if job is None:
                # 任务不存在，重新添加，使用默认值
                scheduler.add_job(
                    func=job_config['func'],
                    trigger='cron',
                    job_id=job_id,
                    hour=hour if hour is not None else job_config['default_hour'],
                    minute=minute if minute is not None else job_config['default_minute'],
                    second=second if second is not None else 0,
                    day=day if day is not None else '*',
                    month=month if month is not None else '*',
                    year=year if year is not None else '*',
                    day_of_week=day_of_week if day_of_week is not None else '*',
                    replace_existing=True
                )
                time_str = f"{hour if hour is not None else job_config['default_hour']}:{minute if minute is not None else job_config['default_minute']:02d}"
                logger.info(f"任务 {job_id} 已创建，执行时间为 {time_str}")
                return ApiResponse(message=f"任务 {job_id} 已启动，执行时间为 {time_str}")
            else:
                # 直接调用封装好的修改方法
                scheduler.modify_job(
                    job_id=job_id,
                    year=year,
                    month=month,
                    day=day,
                    day_of_week=day_of_week,
                    hour=hour,
                    minute=minute,
                    second=second
                )

                # 修复时间拼接（解决 星期216:41 乱码）
                time_desc = []
                if year: time_desc.append(f"{year}年")
                if month: time_desc.append(f"{month}月")
                if day: time_desc.append(f"{day}日")
                if day_of_week and day_of_week != "*":
                    time_desc.append(f"周{day_of_week}")
                time_desc.append(f"{hour}:{minute:02d}")
                time_str = "".join(time_desc)

                logger.info(f"任务 {job_id} 执行时间已修改为 {time_str}")
                return ApiResponse(message=f"任务 {job_id} 执行时间已设置为 {time_str}")
                
        except Exception as e:
            logger.error(f"设置任务 {job_id} 执行时间失败: {e}")
            return ApiResponse(code=500, message=f"设置执行时间失败: {str(e)}")
