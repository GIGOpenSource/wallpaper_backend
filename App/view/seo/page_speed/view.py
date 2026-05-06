# -*- coding: UTF-8 -*-
"""
页面速度管理视图
"""
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from rest_framework.decorators import action
from django.db import models
from models.models import PageSpeed
from tool.base_views import BaseViewSet
from tool.permissions import IsAdmin
from tool.utils import ApiResponse, CustomPagination
from App.view.seo.page_speed.tools import test_page_speed, get_site_prefix


class PageSpeedSerializer(serializers.ModelSerializer):
    """页面速度序列化器"""
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    mobile_friendly_display = serializers.CharField(source='get_mobile_friendly_display', read_only=True)

    class Meta:
        model = PageSpeed
        fields = [
            'id', 'page_path', 'platform', 'platform_display', 'full_url', 'overall_score',
            'mobile_friendly', 'mobile_friendly_display',
            'lcp', 'fid', 'cls', 'load_time', 'page_size',
            'issue_count', 'tested_at', 'created_at', 'remark'
        ]
        read_only_fields = ['id', 'full_url', 'tested_at', 'created_at']


class PageSpeedMobileSerializer(serializers.ModelSerializer):
    """移动端页面速度序列化器（简化版）"""
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    mobile_friendly_display = serializers.CharField(source='get_mobile_friendly_display', read_only=True)

    class Meta:
        model = PageSpeed
        fields = [
            'id', 'page_path', 'platform', 'platform_display',
            'mobile_friendly', 'mobile_friendly_display',
            'overall_score', 'load_time'
        ]


class PageSpeedCreateUpdateSerializer(serializers.Serializer):
    """页面速度创建/更新序列化器"""
    page_path = serializers.CharField(max_length=500, required=True, help_text="页面路径，如 /markwallpapers/search")
    platform = serializers.ChoiceField(
        choices=['page', 'phone', 'pad'],
        required=False,
        default='page',
        help_text="平台类型：page(桌面端)/phone(手机)/pad(平板)"
    )
    remark = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="备注")


@extend_schema(tags=["页面速度管理"])
@extend_schema_view(
    list=extend_schema(
        summary="获取页面速度列表",
        description="获取页面速度列表，支持按评分范围、问题数筛选",
        parameters=[
            OpenApiParameter(name="min_score", type=int, required=False, description="最小综合评分"),
            OpenApiParameter(name="max_score", type=int, required=False, description="最大综合评分"),
            OpenApiParameter(name="min_issues", type=int, required=False, description="最小问题数"),
            OpenApiParameter(name="max_issues", type=int, required=False, description="最大问题数"),
            OpenApiParameter(name="page_path", type=str, required=False, description="页面路径模糊匹配"),
        ],
    ),
    retrieve=extend_schema(
        summary="获取页面速度详情",
        description="根据ID获取页面速度详细信息",
    ),
    create=extend_schema(
        summary="创建页面速度记录",
        description="添加新的页面速度记录（会自动测试）",
        request=PageSpeedCreateUpdateSerializer,
    ),
    update=extend_schema(
        summary="更新页面速度记录",
        description="完整更新页面速度记录",
        request=PageSpeedCreateUpdateSerializer,
    ),
    partial_update=extend_schema(
        summary="部分更新页面速度记录",
        description="部分更新页面速度记录字段",
        request=PageSpeedCreateUpdateSerializer,
    ),
    destroy=extend_schema(
        summary="删除页面速度记录",
        description="删除指定的页面速度记录",
    ),
)
class PageSpeedViewSet(BaseViewSet):
    """
    页面速度 ViewSet
    提供页面速度的增删改查功能
    """
    queryset = PageSpeed.objects.all()
    serializer_class = PageSpeedSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PageSpeedCreateUpdateSerializer
        return PageSpeedSerializer

    def list(self, request, *args, **kwargs):
        """获取页面速度列表，支持多种筛选条件"""
        queryset = PageSpeed.objects.all()
        
        # 按平台筛选
        platform = request.query_params.get('platform')
        if platform:
            queryset = queryset.filter(platform=platform)
        
        # 按综合评分范围筛选
        min_score = request.query_params.get('min_score')
        if min_score:
            try:
                queryset = queryset.filter(overall_score__gte=int(min_score))
            except (TypeError, ValueError):
                pass
        
        max_score = request.query_params.get('max_score')
        if max_score:
            try:
                queryset = queryset.filter(overall_score__lte=int(max_score))
            except (TypeError, ValueError):
                pass
        
        # 按问题数范围筛选
        min_issues = request.query_params.get('min_issues')
        if min_issues:
            try:
                queryset = queryset.filter(issue_count__gte=int(min_issues))
            except (TypeError, ValueError):
                pass
        
        max_issues = request.query_params.get('max_issues')
        if max_issues:
            try:
                queryset = queryset.filter(issue_count__lte=int(max_issues))
            except (TypeError, ValueError):
                pass
        
        # 按移动友好性筛选
        mobile_friendly = request.query_params.get('mobile_friendly')
        if mobile_friendly:
            queryset = queryset.filter(mobile_friendly=mobile_friendly)
        
        # 按页面路径模糊匹配
        page_path = request.query_params.get('page_path')
        if page_path:
            queryset = queryset.filter(page_path__icontains=page_path)
        
        # 按测试时间倒序排序
        queryset = queryset.order_by('-tested_at')
        
        # 分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            # 如果查询的是移动端数据，使用简化序列化器
            if platform in ['phone', 'pad']:
                serializer = PageSpeedMobileSerializer(page, many=True)
            else:
                serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # 如果查询的是移动端数据，使用简化序列化器
        if platform in ['phone', 'pad']:
            serializer = PageSpeedMobileSerializer(queryset, many=True)
        else:
            serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="列表获取成功")

    def create(self, request, *args, **kwargs):
        """创建页面速度记录并自动测试"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        
        page_path = validated_data['page_path']
        platform = validated_data.get('platform', 'page')
        
        # 拼接完整URL
        site_prefix = get_site_prefix()
        if not page_path.startswith('/'):
            page_path_with_slash = '/' + page_path
        else:
            page_path_with_slash = page_path
        full_url = f"{site_prefix}{page_path_with_slash}"
        
        # 调用工具类测试页面速度
        test_result = test_page_speed(page_path, platform)
        
        # 创建或更新记录
        page_speed, created = PageSpeed.objects.update_or_create(
            page_path=page_path,
            platform=platform,
            defaults={
                'full_url': full_url,
                'overall_score': test_result['overall_score'],
                'mobile_friendly': test_result.get('mobile_friendly'),
                'lcp': test_result['lcp'],
                'fid': test_result['fid'],
                'cls': test_result['cls'],
                'load_time': test_result['load_time'],
                'page_size': test_result['page_size'],
                'issue_count': test_result['issue_count'],
                'remark': validated_data.get('remark')
            }
        )
        
        result_serializer = PageSpeedSerializer(page_speed)
        return ApiResponse(
            data=result_serializer.data,
            message="页面速度测试并保存成功",
            code=201
        )

    def update(self, request, *args, **kwargs):
        """更新页面速度记录"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        
        if 'page_path' in validated_data:
            instance.page_path = validated_data['page_path']
            # 重新拼接完整URL
            site_prefix = get_site_prefix()
            page_path = validated_data['page_path']
            if not page_path.startswith('/'):
                page_path = '/' + page_path
            instance.full_url = f"{site_prefix}{page_path}"
        
        if 'remark' in validated_data:
            instance.remark = validated_data.get('remark')
        
        instance.save()
        
        result_serializer = PageSpeedSerializer(instance)
        return ApiResponse(data=result_serializer.data, message="更新成功")

    def partial_update(self, request, *args, **kwargs):
        """部分更新页面速度记录"""
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """删除页面速度记录"""
        instance = self.get_object()
        instance.delete()
        return ApiResponse(message="删除成功")

    @extend_schema(
        summary="获取页面速度统计信息",
        description="获取页面总数、平均评分、优秀页面数、待优化页面数。支持按平台筛选",
        parameters=[
            OpenApiParameter(name="platform", type=str, required=False, description="平台类型：page/phone/pad"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "total_count": {"type": "integer", "description": "总页面数"},
                            "avg_score": {"type": "number", "description": "平均评分"},
                            "excellent_count": {"type": "integer", "description": "优秀页面数（评分>=90）"},
                            "needs_improvement_count": {"type": "integer", "description": "待优化页面数（评分<70）"}
                        }
                    },
                    "message": {"type": "string"}
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """获取页面速度统计信息"""
        from django.db.models import Avg
        
        queryset = PageSpeed.objects.all()
        
        # 按平台筛选
        platform = request.query_params.get('platform')
        if platform:
            queryset = queryset.filter(platform=platform)
        
        total_count = queryset.count()
        avg_score = queryset.aggregate(avg=Avg('overall_score'))['avg'] or 0
        excellent_count = queryset.filter(overall_score__gte=90).count()
        needs_improvement_count = queryset.filter(overall_score__lt=70).count()
        
        return ApiResponse(
            data={
                'total_count': total_count,
                'avg_score': round(avg_score, 2),
                'excellent_count': excellent_count,
                'needs_improvement_count': needs_improvement_count
            },
            message="统计信息获取成功"
        )

    @extend_schema(
        summary="测试新页面",
        description="传入页面路径，自动测试页面速度并保存结果。支持指定平台类型（桌面端/手机/平板）",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "page_path": {"type": "string", "description": "页面路径，如 /markwallpapers/search"},
                    "platform": {"type": "string", "description": "平台类型：page(桌面端)/phone(手机)/pad(平板)，默认page"}
                },
                "required": ["page_path"]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 201},
                    "data": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "page_path": {"type": "string"},
                            "platform": {"type": "string"},
                            "full_url": {"type": "string"},
                            "overall_score": {"type": "integer"},
                            "mobile_friendly": {"type": "string"},
                            "lcp": {"type": "number"},
                            "fid": {"type": "number"},
                            "cls": {"type": "number"},
                            "load_time": {"type": "number"},
                            "page_size": {"type": "number"},
                            "issue_count": {"type": "integer"}
                        }
                    },
                    "message": {"type": "string"}
                }
            }
        }
    )
    @action(detail=False, methods=['post'], url_path='test')
    def test_new_page(self, request):
        """
        测试新页面
        1. 接收页面路径和平台类型
        2. 拼接完整URL
        3. 调用PageSpeed API进行测试
        4. 保存测试结果到数据库
        """
        page_path = request.data.get('page_path')
        if not page_path:
            return ApiResponse(code=400, message="请提供 page_path 参数")
        
        # 获取平台类型，默认为 page
        platform = request.data.get('platform', 'page')
        
        # 拼接完整URL
        site_prefix = get_site_prefix()
        if not page_path.startswith('/'):
            page_path_with_slash = '/' + page_path
        else:
            page_path_with_slash = page_path
        full_url = f"{site_prefix}{page_path_with_slash}"
        
        # 调用工具类测试页面速度
        test_result = test_page_speed(page_path, platform)
        
        # 创建或更新记录
        page_speed, created = PageSpeed.objects.update_or_create(
            page_path=page_path,
            platform=platform,
            defaults={
                'full_url': full_url,
                'overall_score': test_result['overall_score'],
                'mobile_friendly': test_result.get('mobile_friendly'),
                'lcp': test_result['lcp'],
                'fid': test_result['fid'],
                'cls': test_result['cls'],
                'load_time': test_result['load_time'],
                'page_size': test_result['page_size'],
                'issue_count': test_result['issue_count']
            }
        )
        
        result_serializer = PageSpeedSerializer(page_speed)
        return ApiResponse(
            data=result_serializer.data,
            message="页面速度测试成功" if created else "页面速度更新成功",
            code=201
        )
