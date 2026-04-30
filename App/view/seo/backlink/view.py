# -*- coding: UTF-8 -*-
"""
外链管理视图
"""
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from rest_framework.decorators import action
from django.db import models
from models.models import BacklinkManagement
from tool.base_views import BaseViewSet
from tool.permissions import IsAdmin
from tool.utils import ApiResponse, CustomPagination


class BacklinkManagementSerializer(serializers.ModelSerializer):
    """外链管理序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    attribute_display = serializers.CharField(source='get_attribute_display', read_only=True)

    class Meta:
        model = BacklinkManagement
        fields = [
            'id', 'source_page', 'target_page', 'anchor_text',
            'da_score', 'quality_score', 'attribute', 'attribute_display',
            'status', 'status_display', 'created_at', 'updated_at', 'remark'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BacklinkManagementCreateUpdateSerializer(serializers.Serializer):
    """外链管理创建/更新序列化器"""
    source_page = serializers.URLField(required=True, help_text="来源页面")
    target_page = serializers.URLField(required=True, help_text="目标页面")
    anchor_text = serializers.CharField(max_length=200, required=False, allow_blank=True, allow_null=True, help_text="锚文本")
    da_score = serializers.IntegerField(required=False, default=0, min_value=0, max_value=100, help_text="DA评分（0-100）")
    quality_score = serializers.IntegerField(required=False, default=0, min_value=0, max_value=100, help_text="质量评分（0-100）")
    attribute = serializers.ChoiceField(
        choices=['dofollow', 'nofollow', 'ugc', 'sponsored'],
        required=False,
        default='dofollow',
        help_text="属性"
    )
    status = serializers.ChoiceField(
        choices=['active', 'inactive', 'pending', 'toxic'],
        required=False,
        default='pending',
        help_text="状态"
    )
    remark = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="备注")


@extend_schema(tags=["外链管理"])
@extend_schema_view(
    list=extend_schema(
        summary="获取外链列表",
        description="获取外链管理列表，支持按状态、属性、目标页面筛选",
        parameters=[
            OpenApiParameter(name="status", type=str, required=False, description="状态：active/inactive/pending/toxic"),
            OpenApiParameter(name="attribute", type=str, required=False, description="属性：dofollow/nofollow/ugc/sponsored"),
            OpenApiParameter(name="target_page", type=str, required=False, description="目标页面模糊匹配"),
            OpenApiParameter(name="source_page", type=str, required=False, description="来源页面模糊匹配"),
            OpenApiParameter(name="min_quality_score", type=int, required=False, description="最小质量评分"),
            OpenApiParameter(name="max_quality_score", type=int, required=False, description="最大质量评分"),
        ],
    ),
    retrieve=extend_schema(
        summary="获取外链详情",
        description="根据ID获取外链详细信息",
    ),
    create=extend_schema(
        summary="创建外链记录",
        description="添加新的外链记录",
        request=BacklinkManagementCreateUpdateSerializer,
    ),
    update=extend_schema(
        summary="更新外链记录",
        description="完整更新外链记录",
        request=BacklinkManagementCreateUpdateSerializer,
    ),
    partial_update=extend_schema(
        summary="部分更新外链记录",
        description="部分更新外链记录字段",
        request=BacklinkManagementCreateUpdateSerializer,
    ),
    destroy=extend_schema(
        summary="删除外链记录",
        description="删除指定的外链记录",
    ),
)
class BacklinkManagementViewSet(BaseViewSet):
    """
    外链管理 ViewSet
    提供外链的增删改查功能
    """
    queryset = BacklinkManagement.objects.all()
    serializer_class = BacklinkManagementSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return BacklinkManagementCreateUpdateSerializer
        return BacklinkManagementSerializer

    def list(self, request, *args, **kwargs):
        """获取外链列表，支持多种筛选条件"""
        queryset = BacklinkManagement.objects.all()
        
        # 按状态筛选
        status = request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # 按属性筛选
        attribute = request.query_params.get('attribute')
        if attribute:
            queryset = queryset.filter(attribute=attribute)
        
        # 按目标页面模糊匹配
        target_page = request.query_params.get('target_page')
        if target_page:
            queryset = queryset.filter(target_page__icontains=target_page)
        
        # 按来源页面模糊匹配
        source_page = request.query_params.get('source_page')
        if source_page:
            queryset = queryset.filter(source_page__icontains=source_page)
        
        # 按质量评分范围筛选
        min_quality_score = request.query_params.get('min_quality_score')
        if min_quality_score:
            try:
                queryset = queryset.filter(quality_score__gte=int(min_quality_score))
            except (TypeError, ValueError):
                pass
        
        max_quality_score = request.query_params.get('max_quality_score')
        if max_quality_score:
            try:
                queryset = queryset.filter(quality_score__lte=int(max_quality_score))
            except (TypeError, ValueError):
                pass
        
        # 按创建时间倒序排序
        queryset = queryset.order_by('-created_at')
        
        # 分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="列表获取成功")

    def create(self, request, *args, **kwargs):
        """创建外链记录"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        
        backlink = BacklinkManagement.objects.create(
            source_page=validated_data['source_page'],
            target_page=validated_data['target_page'],
            anchor_text=validated_data.get('anchor_text'),
            da_score=validated_data.get('da_score', 0),
            quality_score=validated_data.get('quality_score', 0),
            attribute=validated_data.get('attribute', 'dofollow'),
            status=validated_data.get('status', 'pending'),
            remark=validated_data.get('remark')
        )
        
        result_serializer = BacklinkManagementSerializer(backlink)
        return ApiResponse(data=result_serializer.data, message="创建成功", code=201)

    def update(self, request, *args, **kwargs):
        """更新外链记录"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        
        if 'source_page' in validated_data:
            instance.source_page = validated_data['source_page']
        if 'target_page' in validated_data:
            instance.target_page = validated_data['target_page']
        if 'anchor_text' in validated_data:
            instance.anchor_text = validated_data.get('anchor_text')
        if 'da_score' in validated_data:
            instance.da_score = validated_data['da_score']
        if 'quality_score' in validated_data:
            instance.quality_score = validated_data['quality_score']
        if 'attribute' in validated_data:
            instance.attribute = validated_data['attribute']
        if 'status' in validated_data:
            instance.status = validated_data['status']
        if 'remark' in validated_data:
            instance.remark = validated_data.get('remark')
        
        instance.save()
        
        result_serializer = BacklinkManagementSerializer(instance)
        return ApiResponse(data=result_serializer.data, message="更新成功")

    def partial_update(self, request, *args, **kwargs):
        """部分更新外链记录"""
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """删除外链记录"""
        instance = self.get_object()
        instance.delete()
        return ApiResponse(message="删除成功")

    @extend_schema(
        summary="获取外链统计信息",
        description="获取外链总数、各状态数量、平均质量评分等统计信息",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "total_count": {"type": "integer", "description": "外链总数"},
                            "active_count": {"type": "integer", "description": "有效外链数"},
                            "inactive_count": {"type": "integer", "description": "失效外链数"},
                            "pending_count": {"type": "integer", "description": "待审核外链数"},
                            "toxic_count": {"type": "integer", "description": "有毒外链数"},
                            "avg_quality_score": {"type": "number", "description": "平均质量评分"},
                            "avg_da_score": {"type": "number", "description": "平均DA评分"},
                            "dofollow_count": {"type": "integer", "description": "Dofollow外链数"},
                            "nofollow_count": {"type": "integer", "description": "Nofollow外链数"}
                        }
                    },
                    "message": {"type": "string"}
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """获取外链统计信息"""
        total_count = BacklinkManagement.objects.count()
        active_count = BacklinkManagement.objects.filter(status='active').count()
        inactive_count = BacklinkManagement.objects.filter(status='inactive').count()
        pending_count = BacklinkManagement.objects.filter(status='pending').count()
        toxic_count = BacklinkManagement.objects.filter(status='toxic').count()
        
        # 计算平均质量评分和DA评分
        avg_quality = BacklinkManagement.objects.aggregate(
            avg_quality=models.Avg('quality_score')
        )['avg_quality'] or 0
        
        avg_da = BacklinkManagement.objects.aggregate(
            avg_da=models.Avg('da_score')
        )['avg_da'] or 0
        
        dofollow_count = BacklinkManagement.objects.filter(attribute='dofollow').count()
        nofollow_count = BacklinkManagement.objects.filter(attribute='nofollow').count()
        
        return ApiResponse(
            data={
                'total_count': total_count,
                'active_count': active_count,
                'inactive_count': inactive_count,
                'pending_count': pending_count,
                'toxic_count': toxic_count,
                'avg_quality_score': round(avg_quality, 2),
                'avg_da_score': round(avg_da, 2),
                'dofollow_count': dofollow_count,
                'nofollow_count': nofollow_count
            },
            message="统计信息获取成功"
        )
