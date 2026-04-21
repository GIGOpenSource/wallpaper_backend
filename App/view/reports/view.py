# -*- coding: UTF-8 -*-
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from django.utils import timezone
from rest_framework.decorators import action

from models.models import Report, Wallpapers, WallpaperComment, CustomerUser
from tool.base_views import BaseViewSet
from tool.permissions import IsAdmin
from tool.utils import ApiResponse, CustomPagination
from tool.token_tools import CustomTokenTool


class ReportSerializer(serializers.ModelSerializer):
    """举报序列化器（客户端使用）"""
    reporter_info = serializers.SerializerMethodField()
    target_info = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id', 'reporter_info', 'report_type', 'target_info', 'target_id',
            'target_type', 'reason', 'detail', 'status', 'created_at'
        ]
        read_only_fields = ['id', 'reporter_info', 'target_info', 'created_at']

    def get_reporter_info(self, obj):
        """获取举报人信息"""
        return {
            'id': obj.reporter.id,
            'email': obj.reporter.email,
            'nickname': obj.reporter.nickname,
        }

    def get_target_info(self, obj):
        """获取举报对象信息"""
        if obj.report_type == 'wallpaper':
            try:
                wallpaper = Wallpapers.objects.get(id=obj.target_id)
                return {
                    'id': wallpaper.id,
                    'name': wallpaper.name,
                    'thumb_url': wallpaper.thumb_url,
                }
            except Wallpapers.DoesNotExist:
                return None
        elif obj.report_type == 'comment':
            try:
                comment = WallpaperComment.objects.get(id=obj.target_id)
                return {
                    'id': comment.id,
                    'content': comment.content[:100] + '...' if len(comment.content) > 100 else comment.content,
                }
            except WallpaperComment.DoesNotExist:
                return None
        return None


class ReportAdminSerializer(serializers.ModelSerializer):
    """举报序列化器（管理员使用）"""
    reporter_info = serializers.SerializerMethodField()
    target_info = serializers.SerializerMethodField()
    handler_info = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id', 'reporter_info', 'report_type', 'target_info', 'target_id',
            'target_type', 'reason', 'detail', 'status', 'handler_info',
            'handle_result', 'created_at', 'handled_at'
        ]
        read_only_fields = ['id', 'reporter_info', 'target_info', 'handler_info', 'created_at', 'handled_at']

    def get_reporter_info(self, obj):
        """获取举报人信息"""
        return {
            'id': obj.reporter.id,
            'email': obj.reporter.email,
            'nickname': obj.reporter.nickname,
        }

    def get_target_info(self, obj):
        """获取举报对象信息"""
        if obj.report_type == 'wallpaper':
            try:
                wallpaper = Wallpapers.objects.get(id=obj.target_id)
                return {
                    'id': wallpaper.id,
                    'name': wallpaper.name,
                    'thumb_url': wallpaper.thumb_url,
                }
            except Wallpapers.DoesNotExist:
                return None
        elif obj.report_type == 'comment':
            try:
                comment = WallpaperComment.objects.get(id=obj.target_id)
                return {
                    'id': comment.id,
                    'content': comment.content[:100] + '...' if len(comment.content) > 100 else comment.content,
                }
            except WallpaperComment.DoesNotExist:
                return None
        return None

    def get_handler_info(self, obj):
        """获取处理人信息"""
        if obj.handler:
            return {
                'id': obj.handler.id,
                'username': obj.handler.username,
            }
        return None


@extend_schema(tags=["举报管理"])
@extend_schema_view(
    list=extend_schema(
        summary="获取举报列表（管理员）",
        description="管理员查看所有举报记录（支持分页和筛选）",
        parameters=[
            OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码"),
            OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量"),
            OpenApiParameter(name="report_type", type=str, required=False,
                             description="举报类型：wallpaper/comment/user"),
            OpenApiParameter(name="status", type=str, required=False,
                             description="处理状态：pending/processing/resolved/rejected"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "results": {"type": "array", "items": {"$ref": "#/components/schemas/ReportAdmin"}},
                            "total": {"type": "integer", "example": 50}
                        }
                    },
                    "message": {"type": "string", "example": "举报列表获取成功"}
                }
            }
        }
    ),
    create=extend_schema(
    summary="提交举报",
    description="用户提交举报记录",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "integer",
                    "description": "举报人用户ID（CustomerUser.id）"
                },
                "report_type": {
                    "type": "string",
                    "enum": ["wallpaper", "comment", "user"],
                    "description": "举报类型"
                },
                "target_id": {
                    "type": "integer",
                    "description": "举报对象ID"
                },
                "target_type": {
                    "type": "string",
                    "enum": ["wallpaper", "comment", "user"],
                    "description": "举报对象类型（建议与 report_type 保持一致）"
                },
                "reason": {
                    "type": "string",
                    "enum": [
                        "inappropriate", "copyright", "spam", "harassment",
                        "violence", "pornography", "political", "other"
                    ],
                    "description": "举报原因"
                },
                "detail": {
                    "type": "string",
                    "description": "补充说明（可选）",
                    "default": ""
                }
            },
            "required": ["customer_id", "report_type", "target_id", "target_type", "reason"],
            "example": {
                "report_type": "comment",
                "target_id": 345,
                "target_type": "comment",
                "reason": "spam",
                "detail": "重复发布广告内容"
            }
            }
        },
        responses={201: ReportSerializer, 400: "参数错误", 404: "举报用户不存在"}
    ),
    retrieve=extend_schema(summary="获取举报详情", responses={200: ReportAdminSerializer, 404: "举报不存在"}),
    destroy=extend_schema(summary="删除举报记录", responses={204: "删除成功", 404: "举报不存在"})
)
class ReportViewSet(BaseViewSet):
    """
    举报管理 ViewSet
    提供举报的提交、查看和处理功能
    """
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    pagination_class = CustomPagination

    def get_permissions(self):
        """根据不同操作返回不同的权限类"""
        if self.action in ['list', 'retrieve', 'destroy', 'handle']:
            # 管理员操作
            return [IsAdmin()]
        # 其他操作（如创建）公开
        return []

    def get_serializer_class(self):
        """根据动作返回不同的序列化器"""
        if self.action in ['list', 'retrieve']:
            return ReportAdminSerializer
        return ReportSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        tok = self.request.headers.get("token")
        if tok:
            ok, cid = CustomTokenTool.verify_customer_token(tok)
            if ok:
                ctx["customer_id"] = cid
        return ctx

    def create(self, request, *args, **kwargs):
        """
        提交举报
        """
        customer_id = request.user.id
        if not customer_id:
            return ApiResponse(code=400, message="需要登录或当前token不正确")
        report_type = request.data.get('report_type')
        target_id = request.data.get('target_id')
        target_type = request.data.get('target_type')
        reason = request.data.get('reason')
        detail = request.data.get('detail', '')
        # 校验必填字段
        if not report_type or report_type not in ['wallpaper', 'comment', 'user']:
            return ApiResponse(code=400, message="举报类型无效")
        if not target_id:
            return ApiResponse(code=400, message="举报对象ID不能为空")
        if not target_type or target_type not in ['wallpaper', 'comment', 'user']:
            return ApiResponse(code=400, message="举报对象类型无效")
        if not reason or reason not in ['inappropriate', 'copyright', 'spam', 'harassment', 'violence', 'pornography',
                                        'political', 'other']:
            return ApiResponse(code=400, message="举报原因无效")
        try:
            reporter = CustomerUser.objects.get(id=customer_id)
        except CustomerUser.DoesNotExist:
            return ApiResponse(code=404, message="举报用户不存在")

        # 创建举报记录
        report = Report.objects.create(
            reporter=reporter,
            report_type=report_type,
            target_id=target_id,
            target_type=target_type,
            reason=reason,
            detail=detail
        )

        serializer = self.get_serializer(report)
        return ApiResponse(data=serializer.data, code=201, message="举报已提交")

    def list(self, request, *args, **kwargs):
        """
        管理员获取举报列表
        """
        queryset = self.filter_queryset(self.get_queryset())

        # 支持按举报类型筛选
        report_type = request.query_params.get('report_type')
        if report_type and report_type in ['wallpaper', 'comment', 'user']:
            queryset = queryset.filter(report_type=report_type)

        # 支持按处理状态筛选
        status = request.query_params.get('status')
        if status and status in ['pending', 'processing', 'resolved', 'rejected']:
            queryset = queryset.filter(status=status)

        # 按时间倒序
        queryset = queryset.order_by('-created_at')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="举报列表获取成功")

    @extend_schema(
        summary="处理举报",
        description="管理员处理举报记录（更新状态和处理结果）",
        request=None,
        responses={200: {"type": "object", "properties": {"code": {"type": "integer"}, "message": {"type": "string"}}}}
    )
    @action(detail=True, methods=['post'], url_path='handle')
    def handle(self, request, pk=None):
        """
        处理举报（仅管理员）
        """
        try:
            report = Report.objects.get(id=pk)
        except Report.DoesNotExist:
            return ApiResponse(code=404, message="举报记录不存在")

        status = request.data.get('status')
        handle_result = request.data.get('handle_result', '')

        if not status or status not in ['processing', 'resolved', 'rejected']:
            return ApiResponse(code=400, message="处理状态无效")

        # 更新举报状态
        report.status = status
        report.handle_result = handle_result
        report.handler = request.user
        report.handled_at = timezone.now()
        report.save(update_fields=['status', 'handle_result', 'handler', 'handled_at'])

        return ApiResponse(message="举报已处理")
