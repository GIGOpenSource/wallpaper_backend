# -*- coding: UTF-8 -*-
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from rest_framework.decorators import action

from models.models import OperationLog, User
from tool.base_views import BaseViewSet
from tool.permissions import IsAdmin
from tool.utils import ApiResponse, CustomPagination


class OperationLogSerializer(serializers.ModelSerializer):
    """操作日志序列化器"""
    operator_info = serializers.SerializerMethodField()
    operation_type_display = serializers.CharField(source='get_operation_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = OperationLog
        fields = [
            'id', 'operator_id', 'operator_info', 'operator_name', 'module',
            'operation_type', 'operation_type_display', 'target_id', 'target_name',
            'description', 'request_method', 'request_url', 'ip_address',
            'status', 'status_display', 'error_message', 'extra_data', 'created_at'
        ]
        read_only_fields = fields

    def get_operator_info(self, obj):
        """获取操作人信息"""
        if obj.operator_id:
            user = User.objects.get(id=obj.operator_id)
            return {
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'role_display': user.get_role_display()
            }
        return None


@extend_schema(tags=["操作日志管理"])
@extend_schema_view(
    list=extend_schema(
        summary="获取操作日志列表",
        description="支持按操作人、模块、操作类型、时间范围筛选",
        parameters=[
            OpenApiParameter(name="operator_id", type=int, required=False, description="操作人ID"),
            OpenApiParameter(name="module", type=str, required=False, description="操作模块"),
            OpenApiParameter(name="operation_type", type=str, required=False, description="操作类型"),
            OpenApiParameter(name="start_date", type=str, required=False, description="开始日期（YYYY-MM-DD）"),
            OpenApiParameter(name="end_date", type=str, required=False, description="结束日期（YYYY-MM-DD）"),
            OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码"),
            OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量"),
        ],
    ),
    retrieve=extend_schema(summary="获取日志详情"),
    destroy=extend_schema(summary="删除日志"),
)
class OperationLogViewSet(BaseViewSet):
    """
    操作日志管理 ViewSet
    仅支持查看和删除，不支持修改
    """
    queryset = OperationLog.objects.all()
    serializer_class = OperationLogSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAdmin]

    def get_queryset(self):
        queryset = super().get_queryset()

        # 按操作人筛选
        operator_id = self.request.query_params.get('operator_id')
        if operator_id:
            queryset = queryset.filter(operator_id=operator_id)

        # 按模块筛选
        module = self.request.query_params.get('module')
        if module:
            queryset = queryset.filter(module=module)

        # 按操作类型筛选
        operation_type = self.request.query_params.get('operation_type')
        if operation_type:
            queryset = queryset.filter(operation_type=operation_type)

        # 按时间范围筛选
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        return queryset.order_by('-created_at')

    def list(self, request, *args, **kwargs):
        """获取操作日志列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="列表获取成功")

    def retrieve(self, request, *args, **kwargs):
        """获取日志详情"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return ApiResponse(data=serializer.data, message="详情获取成功")
        except Exception as e:
            return ApiResponse(code=500, message=f"详情获取失败: {str(e)}")

    def destroy(self, request, *args, **kwargs):
        """删除日志"""
        try:
            instance = self.get_object()
            instance.delete()
            return ApiResponse(message="删除成功")
        except Exception as e:
            return ApiResponse(code=500, message=f"删除失败: {str(e)}")

    @extend_schema(
        summary="批量删除日志",
        description="根据条件批量删除操作日志",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "日志ID列表"
                    },
                    "days_before": {
                        "type": "integer",
                        "description": "删除多少天前的日志（与 ids 二选一）"
                    }
                }
            }
        },
    )
    @action(detail=False, methods=['post'], url_path='batch-delete')
    def batch_delete(self, request):
        """批量删除日志"""
        try:
            ids = request.data.get('ids', [])
            days_before = request.data.get('days_before')

            if ids:
                count = OperationLog.objects.filter(id__in=ids).count()
                OperationLog.objects.filter(id__in=ids).delete()
                return ApiResponse(
                    data={'deleted_count': count},
                    message=f"成功删除 {count} 条日志"
                )
            elif days_before:
                from django.utils import timezone
                from datetime import timedelta

                cutoff_date = timezone.now() - timedelta(days=int(days_before))
                count = OperationLog.objects.filter(created_at__lt=cutoff_date).count()
                OperationLog.objects.filter(created_at__lt=cutoff_date).delete()
                return ApiResponse(
                    data={'deleted_count': count},
                    message=f"成功删除 {count} 条 {days_before} 天前的日志"
                )
            else:
                return ApiResponse(code=400, message="请提供 ids 或 days_before 参数")
        except Exception as e:
            return ApiResponse(code=500, message=f"批量删除失败: {str(e)}")

    @extend_schema(
        summary="获取操作统计",
        description="获取操作日志的统计数据",
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """获取操作统计"""
        try:
            from django.db.models import Count

            # 按模块统计
            module_stats = OperationLog.objects.values('module').annotate(
                count=Count('id')
            ).order_by('-count')

            # 按操作类型统计
            type_stats = OperationLog.objects.values('operation_type').annotate(
                count=Count('id')
            ).order_by('-count')

            # 按操作人统计（前10名）
            operator_stats = OperationLog.objects.values(
                'operator_id', 'operator_name'
            ).annotate(
                count=Count('id')
            ).order_by('-count')[:10]

            # 总日志数
            total_count = OperationLog.objects.count()

            return ApiResponse(
                data={
                    'total_count': total_count,
                    'module_stats': list(module_stats),
                    'type_stats': list(type_stats),
                    'operator_stats': list(operator_stats),
                },
                message="统计成功"
            )
        except Exception as e:
            return ApiResponse(code=500, message=f"统计失败: {str(e)}")
