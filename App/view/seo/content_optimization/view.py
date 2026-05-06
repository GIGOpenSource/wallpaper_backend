# -*- coding: UTF-8 -*-
"""
内容优化建议视图
"""
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from rest_framework.decorators import action
from django.db import models
from models.models import PageSpeed
from tool.base_views import BaseViewSet
from tool.permissions import IsAdmin
from tool.utils import ApiResponse, CustomPagination
from App.view.seo.content_optimization.tools import analyze_page_content
from App.view.seo.page_speed.tools import get_site_prefix


class ContentOptimizationSerializer(serializers.ModelSerializer):
    """内容优化序列化器"""
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)

    class Meta:
        model = PageSpeed
        fields = [
            'id', 'page_path', 'platform', 'platform_display', 'full_url',
            'page_title', 'content_score', 'word_count', 'issue_count',
            'optimization_suggestions', 'last_optimized_at', 'created_at'
        ]
        read_only_fields = ['id', 'full_url', 'last_optimized_at', 'created_at']


class ContentOptimizationCreateSerializer(serializers.Serializer):
    """内容优化创建序列化器"""
    page_path = serializers.CharField(max_length=500, required=True, help_text="页面路径，如 /markwallpapers/search")
    platform = serializers.ChoiceField(
        choices=['page', 'phone', 'pad'],
        required=False,
        default='page',
        help_text="平台类型：page(桌面端)/phone(手机)/pad(平板)"
    )


@extend_schema(tags=["内容优化建议"])
@extend_schema_view(
    list=extend_schema(
        summary="获取内容优化列表",
        description="获取已分析页面的内容优化列表，支持按评分范围、问题数筛选",
        parameters=[
            OpenApiParameter(name="min_score", type=int, required=False, description="最小内容评分"),
            OpenApiParameter(name="max_score", type=int, required=False, description="最大内容评分"),
            OpenApiParameter(name="min_issues", type=int, required=False, description="最小问题数"),
            OpenApiParameter(name="max_issues", type=int, required=False, description="最大问题数"),
            OpenApiParameter(name="page_path", type=str, required=False, description="页面路径模糊匹配"),
            OpenApiParameter(name="platform", type=str, required=False, description="平台类型：page/phone/pad"),
        ],
    ),
    retrieve=extend_schema(
        summary="获取内容优化详情",
        description="根据ID获取页面内容优化详细信息",
    ),
    destroy=extend_schema(
        summary="删除内容优化记录",
        description="删除指定的内容优化记录",
    ),
)
class ContentOptimizationViewSet(BaseViewSet):
    """
    内容优化建议 ViewSet
    提供页面内容优化的分析和管理功能
    """
    queryset = PageSpeed.objects.all()
    serializer_class = ContentOptimizationSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAdmin]

    def get_queryset(self):
        """只返回有内容优化数据的记录"""
        return PageSpeed.objects.filter(
            content_score__gt=0
        ).order_by('-last_optimized_at')

    def list(self, request, *args, **kwargs):
        """获取内容优化列表，支持多种筛选条件"""
        queryset = self.get_queryset()
        
        # 按平台筛选
        platform = request.query_params.get('platform')
        if platform:
            queryset = queryset.filter(platform=platform)
        
        # 按内容评分范围筛选
        min_score = request.query_params.get('min_score')
        if min_score:
            try:
                queryset = queryset.filter(content_score__gte=int(min_score))
            except (TypeError, ValueError):
                pass
        
        max_score = request.query_params.get('max_score')
        if max_score:
            try:
                queryset = queryset.filter(content_score__lte=int(max_score))
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
        
        # 按页面路径模糊匹配
        page_path = request.query_params.get('page_path')
        if page_path:
            queryset = queryset.filter(page_path__icontains=page_path)
        
        # 分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="列表获取成功")

    @extend_schema(
        summary="分析新页面内容",
        description="传入页面路径进行内容分析，创建或更新记录",
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
                            "page_title": {"type": "string"},
                            "content_score": {"type": "integer"},
                            "word_count": {"type": "integer"},
                            "issue_count": {"type": "integer"},
                            "optimization_suggestions": {"type": "string"},
                            "last_optimized_at": {"type": "string", "format": "date-time"}
                        }
                    },
                    "message": {"type": "string"}
                }
            }
        }
    )
    @action(detail=False, methods=['post'], url_path='analyze')
    def analyze_page(self, request):
        """
        分析新页面内容
        - 传入page_path进行内容分析
        - 创建或更新记录
        """
        serializer = ContentOptimizationCreateSerializer(data=request.data)
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
        
        # 调用工具类分析页面内容
        analysis_result = analyze_page_content(page_path, platform)
        
        # 创建或更新记录
        from datetime import datetime
        page_speed, created = PageSpeed.objects.update_or_create(
            page_path=page_path,
            platform=platform,
            defaults={
                'full_url': full_url,
                'page_title': analysis_result['page_title'],
                'content_score': analysis_result['content_score'],
                'word_count': analysis_result['word_count'],
                'optimization_suggestions': analysis_result['optimization_suggestions'],
                'last_optimized_at': datetime.now()
            }
        )
        
        result_serializer = ContentOptimizationSerializer(page_speed)
        return ApiResponse(
            data=result_serializer.data,
            message="页面内容分析并保存成功",
            code=201
        )

    @extend_schema(
        summary="重新分析页面内容",
        description="根据ID重新分析已有记录的内容",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "记录ID"}
                },
                "required": ["id"]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "page_path": {"type": "string"},
                            "page_title": {"type": "string"},
                            "content_score": {"type": "integer"},
                            "word_count": {"type": "integer"},
                            "optimization_suggestions": {"type": "string"},
                            "last_optimized_at": {"type": "string", "format": "date-time"}
                        }
                    },
                    "message": {"type": "string"}
                }
            }
        }
    )
    @action(detail=False, methods=['post'], url_path='re-analyze')
    def re_analyze_page(self, request):
        """
        重新分析页面内容
        - 传入id重新分析该记录
        """
        record_id = request.data.get('id')
        
        if not record_id:
            return ApiResponse(code=400, message="请提供 id 参数")
        
        try:
            page_speed = PageSpeed.objects.get(id=record_id)
        except PageSpeed.DoesNotExist:
            return ApiResponse(code=404, message="记录不存在")
        
        # 使用记录的原有路径和平台
        test_page_path = page_speed.page_path
        test_platform = page_speed.platform
        
        # 拼接完整URL
        site_prefix = get_site_prefix()
        if not test_page_path.startswith('/'):
            page_path_with_slash = '/' + test_page_path
        else:
            page_path_with_slash = test_page_path
        full_url = f"{site_prefix}{page_path_with_slash}"
        
        # 调用工具类分析页面内容
        analysis_result = analyze_page_content(test_page_path, test_platform)
        
        # 更新记录
        from datetime import datetime
        page_speed.page_title = analysis_result['page_title']
        page_speed.content_score = analysis_result['content_score']
        page_speed.word_count = analysis_result['word_count']
        page_speed.optimization_suggestions = analysis_result['optimization_suggestions']
        page_speed.last_optimized_at = datetime.now()
        page_speed.full_url = full_url
        page_speed.save()
        
        result_serializer = ContentOptimizationSerializer(page_speed)
        return ApiResponse(
            data=result_serializer.data,
            message="重新分析成功",
            code=200
        )

    @extend_schema(
        summary="获取内容优化统计信息（看板）",
        description="获取已分析页面数量、平均内容评分、待修复问题个数、优化建议个数",
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
                            "analyzed_pages_count": {"type": "integer", "description": "已分析页面数量"},
                            "avg_content_score": {"type": "number", "description": "平均内容评分"},
                            "total_issues": {"type": "integer", "description": "待修复问题总数"},
                            "total_suggestions": {"type": "integer", "description": "优化建议总数"}
                        }
                    },
                    "message": {"type": "string"}
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        """
        内容优化建议看板
        - 已分析页面数量
        - 平均内容评分
        - 待修复问题个数
        - 优化建议个数
        """
        from django.db.models import Avg, Count
        
        queryset = PageSpeed.objects.filter(content_score__gt=0)
        
        # 按平台筛选
        platform = request.query_params.get('platform')
        if platform:
            queryset = queryset.filter(platform=platform)
        
        # 已分析页面数量
        analyzed_pages_count = queryset.count()
        
        # 平均内容评分
        avg_content_score = queryset.aggregate(avg=Avg('content_score'))['avg'] or 0
        
        # 待修复问题总数
        total_issues = queryset.aggregate(total=Count('issue_count'))['total'] or 0
        # 实际上应该求和问题数，而不是计数
        from django.db.models import Sum
        total_issues = queryset.aggregate(total=Sum('issue_count'))['total'] or 0
        
        # 优化建议总数（统计有优化建议的记录数）
        total_suggestions = queryset.filter(
            optimization_suggestions__isnull=False
        ).exclude(
            optimization_suggestions=''
        ).count()
        
        return ApiResponse(
            data={
                'analyzed_pages_count': analyzed_pages_count,
                'avg_content_score': round(avg_content_score, 2),
                'total_issues': total_issues,
                'total_suggestions': total_suggestions
            },
            message="统计信息获取成功"
        )
