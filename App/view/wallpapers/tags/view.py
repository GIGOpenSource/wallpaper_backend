# -*- coding: UTF-8 -*-
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from django.utils import timezone
from django.db.models import Count
from django.core.cache import cache

from models.models import WallpaperTag, Wallpapers, NavigationTag
from tool.base_views import BaseViewSet
from tool.utils import ApiResponse, CustomPagination
from django.utils.translation import gettext as _


class WallpaperTagSerializer(serializers.ModelSerializer):
    """壁纸标签序列化器"""
    wallpaper_count = serializers.SerializerMethodField()

    class Meta:
        model = WallpaperTag
        fields = ['id', 'name', 'created_at', 'wallpaper_count']
        read_only_fields = ['id', 'created_at', 'wallpaper_count']

    def get_wallpaper_count(self, obj):
        """获取标签关联的壁纸总数"""
        cache_key = f"tag_{obj.id}_wallpaper_count"
        count = cache.get(cache_key)
        if count is None:
            try:
                count = obj.wallpapers_set.count()
            except AttributeError:
                count = 0
            cache.set(cache_key, count, timeout=86400)
        return count


@extend_schema(tags=["标签管理"])
class WallpaperTagViewSet(BaseViewSet):
    """
    标签管理 ViewSet
    提供标签列表、热门标签等功能
    """
    queryset = WallpaperTag.objects.all()
    serializer_class = WallpaperTagSerializer
    @extend_schema(
        summary="获取所有标签列表（含壁纸总数）",
        description="每日早8点第一次调用会查询实际总数并缓存，之后24小时内直接返回缓存值",
        parameters=[
            OpenApiParameter(name="q", type=str, required=False, description="关键词搜索"),
        ],
    )
    @action(detail=False, methods=['get'], url_path='list')
    def list_tags(self, request):
        """
        获取所有标签列表，包含每个标签的壁纸总数
        缓存策略：每日早8点第一次调用时刷新缓存
        """

        q = (request.query_params.get("q") or "").strip()
        
        now = timezone.now()
        cache_reset_key = "tag_list_cache_reset_time"
        last_reset_time = cache.get(cache_reset_key)
        
        today_8am = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if now.hour < 8:
            today_8am = today_8am - timezone.timedelta(days=1)
        
        if last_reset_time is None or last_reset_time < today_8am:
            cache.set(cache_reset_key, now, timeout=None)
        
        cache_key = "all_tags_with_count"
        
        if last_reset_time and last_reset_time >= today_8am:
            cached_data = cache.get(cache_key)
            if cached_data:
                return ApiResponse(data=cached_data, message="标签列表获取成功（缓存）")
        qs = WallpaperTag.objects.all().order_by('-created_at')
        if q:
            qs = qs.filter(name__icontains=q)
        tags = list(qs)
        data = []
        for tag in tags:
            count = Wallpapers.objects.filter(tags=tag).count()
            cache.set(f"tag_{tag.id}_wallpaper_count", count, timeout=86400)
            data.append({
                'id': tag.id,
                'name': tag.name,
                'created_at': tag.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'wallpaper_count': count
            })
        cache.set(cache_key, data, timeout=86400)
        return ApiResponse(data=data, message="标签列表获取成功")

    @extend_schema(
        summary="获取热门标签（按壁纸数量排序）",
        description="返回壁纸数量最多的热门标签，支持自定义数量",
        parameters=[
            OpenApiParameter(name="limit", type=int, required=False, description="返回数量，默认 10，最大 20"),
        ],
    )
    @action(detail=False, methods=['get'], url_path='hot')
    def hot_tags(self, request):
        """
        获取热门标签：按壁纸数量排序
        """
        try:
            limit = int(request.query_params.get("limit", 10))
        except (TypeError, ValueError):
            limit = 10
        
        limit = max(1, min(20, limit))
        
        cache_key = f"hot_tags_{limit}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return ApiResponse(data=cached_data, message="热门标签获取成功（缓存）")
        
        tags = WallpaperTag.objects.annotate(
            wallpaper_count=Count('wallpapers_set')
        ).order_by('-wallpaper_count')[:limit]
        
        data = []
        for tag in tags:
            count = tag.wallpaper_count
            cache.set(f"tag_{tag.id}_wallpaper_count", count, timeout=86400)
            data.append({
                'id': tag.id,
                'name': tag.name,
                'wallpaper_count': count
            })
        
        cache.set(cache_key, data, timeout=3600)
        return ApiResponse(data=data, message="热门标签获取成功")



class NavigationTagSerializer(serializers.ModelSerializer):
    """壁纸序列化器"""

    class Meta:
        model = NavigationTag
        fields = '__all__'

@extend_schema(tags=["导航管理"])
@extend_schema_view(
    list=extend_schema(
        summary="获取导航列表",
        parameters=[
            OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码"),
            OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "results": {"type": "array", "items": {"$ref": "#/components/schemas/NavigationTag"}},
                            "total": {"type": "integer", "example": 50}
                        }
                    },
                    "message": {"type": "string", "example": "列表获取成功"}
                }
            }
        }
    ),
    retrieve=extend_schema(summary="获取导航详情", responses={200: NavigationTagSerializer, 404: "导航不存在"}),
    create=extend_schema(summary="创建导航", request=NavigationTagSerializer),
    update=extend_schema(summary="更新导航", request=NavigationTagSerializer),
    partial_update=extend_schema(summary="部分更新导航", request=NavigationTagSerializer),
    destroy=extend_schema(summary="删除导航", description="删除指定导航记录",
                          responses={204: "删除成功", 404: "导航不存在"})
)
class NavigationTagViewSet(BaseViewSet):
    """
    导航管理 ViewSet
    提供导航的增删改查功能
    """
    queryset = NavigationTag.objects.all()
    serializer_class = NavigationTagSerializer
    pagination_class = CustomPagination

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(serializer.data)