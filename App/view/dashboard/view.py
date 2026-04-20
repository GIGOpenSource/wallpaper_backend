#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：view.py
@Author  ：LiangHB
@Date    ：2026/4/20 14:39
@description : 面板统计视图逻辑
"""
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from tool.base_views import BaseViewSet
from tool.middleware import logger
from tool.permissions import IsAdmin
from tool.utils import ApiResponse, CustomPagination
from rest_framework import serializers
from models.models import (
    CustomerUser,
    Wallpapers,
    WallpaperLike,
    WallpaperCollection,
    DashboardStats,
)


class DashboardStatsSerializer(serializers.ModelSerializer):
    """面板统计数据序列化器"""
    
    class Meta:
        model = DashboardStats
        fields = [
            'stat_date', 'total_users', 'total_wallpapers', 'total_views',
            'total_downloads', 'total_likes', 'total_collections',
            'daily_active_users', 'weekly_active_users', 'updated_at'
        ]
        read_only_fields = fields


@extend_schema(tags=["(Admin)面板统计"])
@extend_schema_view(
    list=extend_schema(
        summary="获取面板统计数据",
        description=(
            "返回总用户数量、总壁纸数量、总浏览量、总下载量、总点赞数、总收藏数、"
            "日活跃用户、周活跃用户等统计数据。\n\n"
            "更新策略：每日早8点第一次调用时查询数据库并更新当日统计表，之后直接返回表中数据。"
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "results": {"type": "array", "items": {"$ref": "#/components/schemas/DashboardStats"}},
                            "total": {"type": "integer", "example": 1}
                        }
                    },
                    "message": {"type": "string", "example": "统计数据获取成功"}
                }
            }
        }
    ),
    retrieve=extend_schema(
        summary="获取指定日期的统计数据",
        parameters=[
            OpenApiParameter(name="id", type=str, required=True, description="统计日期，格式：YYYY-MM-DD"),
        ],
        responses={200: DashboardStatsSerializer, 404: "统计数据不存在"}
    ),
)
class DashboardStatsViewSet(BaseViewSet):
    """
    面板统计 ViewSet
    提供系统整体数据统计功能
    """
    queryset = DashboardStats.objects.all()
    serializer_class = DashboardStatsSerializer
    # 面板统计为公开接口，无需认证
    permission_classes = [IsAdmin]
    def get_queryset(self):
        """
        动态过滤查询
        """
        queryset = super().get_queryset()
        
        # 如果是指定日期查询，按日期过滤
        if self.action == 'retrieve':
            stat_date = self.kwargs.get('pk')
            if stat_date:
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(stat_date, '%Y-%m-%d').date()
                    queryset = queryset.filter(stat_date=date_obj)
                except ValueError:
                    pass
        
        return queryset.order_by('-stat_date')
    
    def list(self, request, *args, **kwargs):
        """
        获取今日面板统计数据
        每天8点后第一次请求会更新数据，之后直接返回表中数据
        """
        now = timezone.now()
        today = now.date()
        
        # 计算今日8点的时间
        today_8am = timezone.make_aware(
            timezone.datetime.combine(today, timezone.datetime.min.time()).replace(hour=8)
        )
        if now.hour < 8:
            # 如果当前时间小于8点，则今日8点是昨天的8点
            today_8am = today_8am - timedelta(days=1)
        
        # 尝试获取今日的统计数据
        try:
            stats_record = DashboardStats.objects.get(stat_date=today)
            
            # 检查是否需要更新（今日8点后且记录更新时间早于今日8点）
            need_refresh = False
            if now.hour >= 8:
                if stats_record.updated_at < today_8am:
                    need_refresh = True
            else:
                # 8点前，检查是否是昨天的数据
                yesterday = today - timedelta(days=1)
                if stats_record.stat_date == yesterday:
                    need_refresh = True
            
            if need_refresh:
                logger.info(f"刷新今日({today})面板统计数据...")
                self._calculate_and_save_stats(today, now)
                # 重新获取更新后的记录
                stats_record = DashboardStats.objects.get(stat_date=today)
            else:
                logger.debug(f"使用缓存的统计数据: {today}")
                
        except DashboardStats.DoesNotExist:
            # 今日数据不存在，创建新记录
            logger.info(f"创建今日({today})面板统计数据...")
            self._calculate_and_save_stats(today, now)
            stats_record = DashboardStats.objects.get(stat_date=today)
        
        # 序列化返回
        serializer = self.get_serializer(stats_record)
        return ApiResponse(data=serializer.data, message="统计数据获取成功")
    
    def retrieve(self, request, *args, **kwargs):
        """
        获取指定日期的统计数据
        """
        instance = self.get_object()
        if not instance:
            return ApiResponse(code=404, message="统计数据不存在")
        
        serializer = self.get_serializer(instance)
        return ApiResponse(data=serializer.data, message="获取成功")
    
    def _calculate_and_save_stats(self, stat_date, now):
        """
        计算统计数据并保存到数据库
        :param stat_date: 统计日期
        :param now: 当前时间
        """
        # 总用户数量
        total_users = CustomerUser.objects.count()
        
        # 总壁纸数量
        total_wallpapers = Wallpapers.objects.count()
        
        # 总浏览量
        total_views_result = Wallpapers.objects.aggregate(total=Sum('view_count'))
        total_views = total_views_result['total'] or 0
        
        # 总下载量
        total_downloads_result = Wallpapers.objects.aggregate(total=Sum('download_count'))
        total_downloads = total_downloads_result['total'] or 0
        
        # 总点赞数
        total_likes = WallpaperLike.objects.count()
        
        # 总收藏数
        total_collections = WallpaperCollection.objects.count()
        
        # 日活跃用户（最近24小时内有登录记录的用户）
        yesterday = now - timedelta(hours=24)
        daily_active_users = CustomerUser.objects.filter(
            last_login__gte=yesterday
        ).count()
        
        # 周活跃用户（最近7天内有登录记录的用户）
        week_ago = now - timedelta(days=7)
        weekly_active_users = CustomerUser.objects.filter(
            last_login__gte=week_ago
        ).count()
        
        # 保存或更新统计数据
        stats_record, created = DashboardStats.objects.update_or_create(
            stat_date=stat_date,
            defaults={
                'total_users': total_users,
                'total_wallpapers': total_wallpapers,
                'total_views': total_views,
                'total_downloads': total_downloads,
                'total_likes': total_likes,
                'total_collections': total_collections,
                'daily_active_users': daily_active_users,
                'weekly_active_users': weekly_active_users,
            }
        )
        
        logger.info(f"统计数据已保存: {stat_date}, 创建: {created}")


class CustomerUserSerializer(serializers.ModelSerializer):
    """客户用户序列化器"""

    class Meta:
        model = CustomerUser
        fields = '__all__'


@extend_schema(tags=["(Admin)用户管理"])
@extend_schema_view(
    list=extend_schema(
        summary="获取客户用户列表",
        description="分页获取所有客户用户列表，支持按邮箱和昵称搜索",
        parameters=[
            OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码，默认1"),
            OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量，默认20"),
            OpenApiParameter(name="email", type=str, required=False, description="按邮箱搜索"),
            OpenApiParameter(name="nickname", type=str, required=False, description="按昵称搜索"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "pagination": {
                                "type": "object",
                                "properties": {
                                    "page": {"type": "integer", "example": 1},
                                    "page_size": {"type": "integer", "example": 20},
                                    "total": {"type": "integer", "example": 100},
                                    "total_pages": {"type": "integer", "example": 5}
                                }
                            },
                            "results": {"type": "array", "items": {"$ref": "#/components/schemas/CustomerUser"}}
                        }
                    },
                    "message": {"type": "string", "example": "用户列表获取成功"}
                }
            }
        }
    ),
    retrieve=extend_schema(
        summary="获取客户用户详情",
        description="根据用户ID获取详细信息",
        parameters=[
            OpenApiParameter(name="id", type=int, required=True, description="用户ID"),
        ],
        responses={
            200: CustomerUserSerializer,
            404: "用户不存在"
        }
    ),
)
class CustomerUserViewSet(BaseViewSet):
    """
    客户用户管理 ViewSet
    提供用户列表和详情查询功能（仅管理员可访问）
    """
    queryset = CustomerUser.objects.all()
    serializer_class = CustomerUserSerializer
    pagination_class = CustomPagination
    # 仅管理员可访问
    permission_classes = [IsAdmin]
    def get_queryset(self):
        queryset = super().get_queryset()
        email = self.request.query_params.get('email', '').strip()
        if email:
            queryset = queryset.filter(email__icontains=email)
        nickname = self.request.query_params.get('nickname', '').strip()
        if nickname:
            queryset = queryset.filter(nickname__icontains=nickname)
        return queryset.order_by('-created_at')

    def list(self, request, *args, **kwargs):
        """
        获取客户用户列表（分页）
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="用户列表获取成功")
    def retrieve(self, request, *args, **kwargs):
        """
        获取客户用户详情
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return ApiResponse(data=serializer.data, message="用户详情获取成功")