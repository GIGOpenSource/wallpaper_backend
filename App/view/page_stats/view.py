#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
页面统计接口
"""
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiParameter, extend_schema_view
from tool.base_views import BaseViewSet
from models.models import PageStats, TrackEvent
from tool.utils import ApiResponse, CustomPagination
from tool.permissions import IsAdmin
from .serializer import PageStatsSerializer
from seo.seo_tools import PageSEOAnalyzer
from django.db.models import Count, Avg, Q
from django.utils import timezone
import threading

# 全局计数器（生产环境建议使用 Redis）
_aggregate_counter = 0
_seo_counter = 0
_lock = threading.Lock()
seo_analyzer = PageSEOAnalyzer()

def _trigger_seo_update():
    """触发 SEO 评分更新逻辑"""
    global _seo_counter
    with _lock:
        _seo_counter += 1
        if _seo_counter >= 10:
            _seo_counter = 0
            t = threading.Thread(target=_perform_seo_update)
            t.daemon = True
            t.start()

def _perform_seo_update():
    """执行 SEO 评分更新"""
    try:
        # 获取访问量最高的前 20 个页面进行 SEO 评分更新
        top_pages = PageStats.objects.order_by('-visit_count')[:20]
        for page in top_pages:
            score = seo_analyzer.calculate_seo_score(page.page_path)
            page.seo_score = score
            page.save(update_fields=['seo_score'])
    except Exception as e:
        print(f"SEO update error: {e}")

def _trigger_aggregate():
    """触发聚合逻辑"""
    global _aggregate_counter
    with _lock:
        _aggregate_counter += 1
        if _aggregate_counter >= 1:
            _aggregate_counter = 0
            # 异步执行聚合，避免阻塞请求
            t = threading.Thread(target=_perform_aggregation)
            t.daemon = True
            t.start()

def _perform_aggregation():
    """执行数据库聚合操作"""
    try:
        # 1. 获取每个分组的最新 page_name (使用 Subquery 或简单的逻辑)
        # 为了性能，我们先按 path, type, device 分组统计基础数据
        stats = TrackEvent.objects.values('page_path', 'page_type', 'device_type').annotate(
            visit_count=Count('id'),
            avg_stay=Avg('page_stay'),
            bounce_count=Count('id', filter=Q(is_bounce=True))
        )

        for item in stats:
            if not item['page_path']:
                continue
            
            # 2. 获取该路径下最近一次上报的 page_name
            latest_event = TrackEvent.objects.filter(
                page_path=item['page_path'],
                page_type=item['page_type'],
                device_type=item['device_type'],
                page_name__isnull=False
            ).exclude(page_name='').order_by('-created_at').first()
            
            page_name = latest_event.page_name if latest_event else None
                
            bounce_rate = (item['bounce_count'] / item['visit_count'] * 100) if item['visit_count'] > 0 else 0
            
            PageStats.objects.update_or_create(
                page_path=item['page_path'],
                page_type=item['page_type'] or 'unknown',
                device_type=item['device_type'] or 'all',
                defaults={
                    'page_name': page_name,
                    'visit_count': item['visit_count'],
                    'avg_stay_time': item['avg_stay'] or 0,
                    'bounce_rate': round(bounce_rate, 2),
                    'last_updated': timezone.now()
                }
            )
    except Exception as e:
        print(f"Page stats aggregation error: {e}")

@extend_schema(tags=["页面统计管理"])
@extend_schema_view(
    list=extend_schema(
        summary="获取页面统计列表",
        description="支持按页面类型、设备类型筛选，每查询10次自动触发一次数据聚合",
        parameters=[
            OpenApiParameter(name="page_type", type=str, required=False, description="页面类型（如 homepage, search, trending, tag）"),
            OpenApiParameter(name="device_type", type=str, required=False, description="设备类型（desktop, mobile, tablet, all）"),
            OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码"),
            OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量"),
        ],
    ),
    retrieve=extend_schema(summary="获取页面统计详情"),
    destroy=extend_schema(summary="删除统计数据"),
)
class PageStatsViewSet(BaseViewSet):
    """
    页面统计 ViewSet
    仅支持查看和删除，不支持修改
    """
    queryset = PageStats.objects.all()
    serializer_class = PageStatsSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAdmin]

    def get_queryset(self):
        queryset = super().get_queryset()
        page_type = self.request.query_params.get('page_type')
        if page_type:
            queryset = queryset.filter(page_type=page_type)
        device_type = self.request.query_params.get('device_type')
        if device_type:
            queryset = queryset.filter(device_type=device_type)
        return queryset.order_by('-visit_count')

    def list(self, request, *args, **kwargs):
        """获取页面统计列表"""
        # 每次查询都尝试触发聚合
        _trigger_aggregate()
        # 每查询 10 次触发一次 SEO 评分更新
        _trigger_seo_update()
        
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="列表获取成功")

    def retrieve(self, request, *args, **kwargs):
        """获取统计详情"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return ApiResponse(data=serializer.data, message="详情获取成功")
        except Exception as e:
            return ApiResponse(code=500, message=f"详情获取失败: {str(e)}")

    def destroy(self, request, *args, **kwargs):
        """删除统计数据"""
        try:
            instance = self.get_object()
            instance.delete()
            return ApiResponse(message="删除成功")
        except Exception as e:
            return ApiResponse(code=500, message=f"删除失败: {str(e)}")
