# -*- coding: UTF-8 -*-
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from django.utils import timezone
from django.db.models import Count
from django.core.cache import cache

from models.models import WallpaperTag, Wallpapers, NavigationTag
from tool.base_views import BaseViewSet
from tool.permissions import IsAdmin
from tool.utils import ApiResponse, CustomPagination
from django.utils.translation import gettext as _


class WallpaperTagSerializer(serializers.ModelSerializer):
    """壁纸标签序列化器"""
    class Meta:
        model = WallpaperTag
        fields = ['id', 'name', 'created_at', 'wallpaper_count', 'pc_count', 'phone_count']
        read_only_fields = ['id', 'created_at', 'wallpaper_count', 'pc_count', 'phone_count']



@extend_schema(tags=["(Admin)标签管理"])
@extend_schema_view(
     list=extend_schema(
        summary="获取标签列表",
        description="默认返回全部标签；仅当传入 pageSize 时启用分页。支持按关键词搜索。",
        parameters=[
            OpenApiParameter(
                name="name",
                type=str,
                required=False,
                description="标签名称关键词（模糊搜索）",
            ),
            OpenApiParameter(
                name="currentPage",
                type=int,
                required=False,
                description="当前页码（仅在传入 pageSize 时生效）",
            ),
            OpenApiParameter(
                name="pageSize",
                type=int,
                required=False,
                description="每页数量；不传则不分页，返回全部数据",
            ),
        ],
    ),
    retrieve=extend_schema(summary="获取标签详情", responses={200: WallpaperTagSerializer, 404: "标签不存在"}),
    create=extend_schema(summary="创建标签", request=WallpaperTagSerializer),
    update=extend_schema(summary="更新标签(Admin)", request=WallpaperTagSerializer),
    partial_update=extend_schema(summary="部分更新标签(Admin)", request=WallpaperTagSerializer),
    destroy=extend_schema(summary="删除标签(Admin)", description="删除指定标签记录",
                          responses={204: "删除成功", 404: "标签不存在"})
)
class WallpaperTagViewSet(BaseViewSet):
    """
    标签管理 ViewSet
    提供标签列表、热门标签等功能
    """
    queryset = WallpaperTag.objects.all()
    serializer_class = WallpaperTagSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        """支持按标签名称模糊查询（q 参数）"""
        queryset = super().get_queryset()
        name = self.request.query_params.get("name", "").strip()
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset.order_by("-created_at")

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)  # 关键点
            serializer = self.get_serializer(queryset, many=True)
            return ApiResponse(code=200, data=serializer.data, message="列表获取成功")
        except Exception as e:
            return ApiResponse(code=500, message=f"列表获取失败: {str(e)}")

    def get_permissions(self):
        """根据不同操作返回不同的权限类"""
        if self.action in ['update', 'partial_update', 'destroy']:
            # 写操作：需要管理员权限
            return [IsAdmin()]
        # 读操作无需权限
        return []

    @extend_schema(
        summary="获取所有标签列表（含壁纸总数）",
        description="每日早8点第一次调用会查询实际总数并缓存，之后24小时内直接返回缓存值。支持通过 platform 参数或 User-Agent 自动识别设备类型",
        parameters=[
            OpenApiParameter(name="q", type=str, required=False, description="关键词搜索"),
            OpenApiParameter(name="platform", type=str, required=False, description="平台类型：PC 或 PHONE，优先级高于 User-Agent 识别"),
        ],
    )
    @action(detail=False, methods=['get'], url_path='list')
    def list_tags(self, request):
        """
        获取所有标签列表，包含每个标签的壁纸总数
        缓存策略：每日早8点第一次调用时刷新缓存
        支持按平台筛选：PC 或 PHONE
        优先使用 platform 参数，其次通过 User-Agent 自动识别
        """

        q = (request.query_params.get("q") or "").strip()
        platform_param = (request.query_params.get("platform") or "").upper()
        
        # 如果前端没有传 platform 参数，则通过 User-Agent 自动识别
        if not platform_param:
            user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
            if any(keyword in user_agent for keyword in ['mobile', 'android', 'iphone', 'ipad']):
                platform = 'PHONE'
            else:
                platform = 'PC'
        else:
            platform = platform_param
        
        now = timezone.now()
        cache_reset_key = "tag_list_cache_reset_time"
        last_reset_time = cache.get(cache_reset_key)

        today_8am = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if now.hour < 8:
            today_8am = today_8am - timezone.timedelta(days=1)

        need_refresh = last_reset_time is None or last_reset_time < today_8am
        # need_refresh = True

        if need_refresh:
            cache.set(cache_reset_key, now, timeout=None)
            qs = WallpaperTag.objects.all()
            if q:
                qs = qs.filter(name__icontains=q)
            
            # 使用聚合查询一次性获取所有标签的统计数据
            from django.db.models import Count, Q
            
            # 1. 获取每个标签的总数
            total_counts = Wallpapers.objects.filter(
                tags__in=qs
            ).values('tags__id').annotate(
                count=Count('id')
            )
            total_dict = {item['tags__id']: item['count'] for item in total_counts}
            
            # 2. 获取每个标签的PC端数量 (category__id=1)
            pc_counts = Wallpapers.objects.filter(
                tags__in=qs,
                category__id=1
            ).values('tags__id').annotate(
                count=Count('id', distinct=True)
            )
            pc_dict = {item['tags__id']: item['count'] for item in pc_counts}
            
            # 3. 获取每个标签的手机端数量 (category__id=2)
            phone_counts = Wallpapers.objects.filter(
                tags__in=qs,
                category__id=2
            ).values('tags__id').annotate(
                count=Count('id', distinct=True)
            )
            phone_dict = {item['tags__id']: item['count'] for item in phone_counts}
            
            # 4. 批量更新标签数据
            tags_to_update = []
            for tag in qs:
                tag.wallpaper_count = total_dict.get(tag.id, 0)
                tag.pc_count = pc_dict.get(tag.id, 0)
                tag.phone_count = phone_dict.get(tag.id, 0)
                tags_to_update.append(tag)
            
            if tags_to_update:
                WallpaperTag.objects.bulk_update(tags_to_update, ['wallpaper_count', 'pc_count', 'phone_count'])

        qs = WallpaperTag.objects.all().order_by('-created_at')
        if q:
            qs = qs.filter(name__icontains=q)

        # 根据平台参数返回不同的字段
        if platform == 'PC':
            data = list(qs.values('id', 'name', 'created_at', 'pc_count'))
            for item in data:
                if item['created_at']:
                    item['created_at'] = item['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                # 重命名字段以便前端使用
                item['wallpaper_count'] = item.pop('pc_count')
        elif platform == 'PHONE':
            data = list(qs.values('id', 'name', 'created_at', 'phone_count'))
            for item in data:
                if item['created_at']:
                    item['created_at'] = item['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                # 重命名字段以便前端使用
                item['wallpaper_count'] = item.pop('phone_count')
        else:
            # 默认返回总数
            data = list(qs.values('id', 'name', 'created_at', 'wallpaper_count'))
            for item in data:
                if item['created_at']:
                    item['created_at'] = item['created_at'].strftime('%Y-%m-%d %H:%M:%S')

        message = "标签列表获取成功（已更新计数）" if need_refresh else "标签列表获取成功（缓存）"
        return ApiResponse(data=data, message=message)

    @extend_schema(
        summary="获取热门标签（按壁纸数量排序）",
        description="返回壁纸数量最多的热门标签，支持自定义数量",
        parameters=[
            OpenApiParameter(name="limit", type=int, required=False, description="返回数量，默认 10，最大 20"),
            OpenApiParameter(name="platform", type=str, required=False, description="平台类型：PC 或 PHONE，不传则按总数排序"),
        ],
    )
    @action(detail=False, methods=['get'], url_path='hot')
    def hot_tags(self, request):
        """
        获取热门标签：按壁纸数量排序
        支持按平台筛选：PC 或 PHONE
        """
        try:
            limit = int(request.query_params.get("limit", 10))
        except (TypeError, ValueError):
            limit = 10

        limit = max(1, min(20, limit))
        
        platform = (request.query_params.get("platform") or "").upper()

        cache_key = f"hot_tags_{limit}_{platform}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return ApiResponse(data=cached_data, message="热门标签获取成功（缓存）")

        now = timezone.now()
        cache_reset_key = "tag_list_cache_reset_time"
        last_reset_time = cache.get(cache_reset_key)

        today_8am = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if now.hour < 8:
            today_8am = today_8am - timezone.timedelta(days=1)

        need_refresh = last_reset_time is None or last_reset_time < today_8am

        if need_refresh:
            cache.set(cache_reset_key, now, timeout=None)

            from django.db.models import Count
            
            all_tags = WallpaperTag.objects.all()
            
            # 1. 获取每个标签的总数
            total_counts = Wallpapers.objects.filter(
                tags__in=all_tags
            ).values('tags__id').annotate(
                count=Count('id')
            )
            total_dict = {item['tags__id']: item['count'] for item in total_counts}
            
            # 2. 获取每个标签的PC端数量
            pc_counts = Wallpapers.objects.filter(
                tags__in=all_tags,
                category__id=1
            ).values('tags__id').annotate(
                count=Count('id', distinct=True)
            )
            pc_dict = {item['tags__id']: item['count'] for item in pc_counts}
            
            # 3. 获取每个标签的手机端数量
            phone_counts = Wallpapers.objects.filter(
                tags__in=all_tags,
                category__id=2
            ).values('tags__id').annotate(
                count=Count('id', distinct=True)
            )
            phone_dict = {item['tags__id']: item['count'] for item in phone_counts}
            
            # 4. 批量更新标签数据
            tags_to_update = []
            for tag in all_tags:
                tag.wallpaper_count = total_dict.get(tag.id, 0)
                tag.pc_count = pc_dict.get(tag.id, 0)
                tag.phone_count = phone_dict.get(tag.id, 0)
                tags_to_update.append(tag)

            if tags_to_update:
                WallpaperTag.objects.bulk_update(tags_to_update, ['wallpaper_count', 'pc_count', 'phone_count'])

        # 根据平台参数选择排序字段
        if platform == 'PC':
            tags = WallpaperTag.objects.order_by('-pc_count')[:limit]
            data = [{
                'id': tag.id,
                'name': tag.name,
                'wallpaper_count': tag.pc_count
            } for tag in tags]
        elif platform == 'PHONE':
            tags = WallpaperTag.objects.order_by('-phone_count')[:limit]
            data = [{
                'id': tag.id,
                'name': tag.name,
                'wallpaper_count': tag.phone_count
            } for tag in tags]
        else:
            # 默认按总数排序
            tags = WallpaperTag.objects.order_by('-wallpaper_count')[:limit]
            data = [{
                'id': tag.id,
                'name': tag.name,
                'wallpaper_count': tag.wallpaper_count
            } for tag in tags]

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

    def get_permissions(self):
        """根据不同操作返回不同的权限类"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # 写操作：需要管理员权限
            return [IsAdmin()]
        # 读操作无需权限
        return []

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(serializer.data)