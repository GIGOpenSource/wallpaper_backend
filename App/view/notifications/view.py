#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：view.py
@Author  ：Liang
@Date    ：2026/4/15
@description : 消息通知接口
"""
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from rest_framework.decorators import action

from models.models import Notification
from tool.base_views import BaseViewSet
from tool.permissions import IsCustomerTokenValid
from tool.token_tools import CustomTokenTool
from tool.utils import ApiResponse, CustomPagination


class NotificationSerializer(serializers.ModelSerializer):
    """通知序列化器"""
    sender_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'sender_info', 'notification_type', 'content_display', 
            'target_id', 'target_type', 'extra_data', 'is_read', 'created_at'
        ]
        read_only_fields = fields

    def get_sender_info(self, obj):
        if obj.sender:
            return {
                'id': obj.sender.id,
                'nickname': obj.sender.nickname,
                'avatar_url': obj.sender.avatar_url,
            }
        return {'nickname': '系统通知', 'avatar_url': None}

    def get_content_display(self, obj):
        # 根据类型动态组合显示内容
        nickname = obj.sender.nickname if obj.sender else "系统"
        if obj.notification_type == 'like':
            return f"{nickname} 赞了你的帖子"
        elif obj.notification_type == 'comment':
            return f"{nickname} 评论了你的帖子"
        elif obj.notification_type == 'reply':
            return f"{nickname} 回复了你的评论"
        elif obj.notification_type == 'follow':
            return f"{nickname} 关注了你"
        else:
            return obj.extra_data.get('title', obj.content) if hasattr(obj, 'content') else str(obj.extra_data)


@extend_schema(tags=["消息通知"])
@extend_schema_view(
    list=extend_schema(
        summary="获取我的通知列表",
        description="分页获取当前用户的通知，支持按类型筛选",
        parameters=[
            OpenApiParameter(name="type", type=str, required=False, description="通知类型筛选 (like/comment/follow/reward/announcement)"),
            OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码"),
            OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量"),
        ],
    ),
)
class NotificationViewSet(BaseViewSet):
    """
    消息通知 ViewSet
    """
    queryset = Notification.objects.none()
    serializer_class = NotificationSerializer
    pagination_class = CustomPagination
    permission_classes = [IsCustomerTokenValid]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        tok = self.request.headers.get("token")
        if tok:
            ok, cid = CustomTokenTool.verify_customer_token(tok)
            if ok:
                ctx["current_user_id"] = cid
        return ctx

    def list(self, request, *args, **kwargs):
        """获取通知列表"""
        current_user_id = self.get_serializer_context().get('current_user_id')
        if not current_user_id:
            return ApiResponse(code=401, message="请先登录")
        
        queryset = Notification.objects.filter(recipient_id=current_user_id).select_related('sender')
        
        # 类型筛选
        n_type = request.query_params.get('type')
        if n_type:
            queryset = queryset.filter(notification_type=n_type)
            
        queryset = queryset.order_by('-created_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="通知列表获取成功")

    @action(detail=False, methods=['post'], url_path='mark-read')
    def mark_read(self, request):
        """标记通知为已读（传 id 或 all）"""
        current_user_id = self.get_serializer_context().get('current_user_id')
        notification_id = request.data.get('id')
        
        if notification_id == 'all':
            Notification.objects.filter(recipient_id=current_user_id, is_read=False).update(is_read=True)
            return ApiResponse(message="全部标记为已读")
        
        try:
            notification = Notification.objects.get(id=notification_id, recipient_id=current_user_id)
            notification.is_read = True
            notification.save()
            return ApiResponse(message="标记成功")
        except Notification.DoesNotExist:
            return ApiResponse(code=404, message="通知不存在")

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        """获取未读通知数量"""
        current_user_id = self.get_serializer_context().get('current_user_id')
        if not current_user_id:
            return ApiResponse(code=401, message="请先登录")
            
        count = Notification.objects.filter(recipient_id=current_user_id, is_read=False).count()
        return ApiResponse(data={'count': count})
