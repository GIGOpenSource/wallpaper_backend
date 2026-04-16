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

from models.models import Notification, UserNotificationSettings
from tool.base_views import BaseViewSet
from tool.permissions import IsCustomerTokenValid
from tool.token_tools import CustomTokenTool
from tool.utils import ApiResponse, CustomPagination


class NotificationSerializer(serializers.ModelSerializer):
    """通知序列化器"""
    sender_info = serializers.SerializerMethodField()
    content_display = serializers.SerializerMethodField()
    target_content = serializers.SerializerMethodField()  # 新增：目标对象（壁纸/评论）的内容摘要
    
    class Meta:
        model = Notification
        fields = [
            'id', 'sender_info', 'notification_type', 'content_display', 
            'target_id', 'target_type', 'target_content', 'extra_data', 'is_read', 'created_at'
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

    def get_target_content(self, obj):
        """获取被互动对象（如壁纸、评论）的简要内容及原始上下文"""
        from models.models import Wallpapers, WallpaperComment
        try:
            if obj.target_type == 'wallpaper':
                # 场景：别人评论/点赞了我的壁纸
                wallpaper = Wallpapers.objects.only('name', 'thumb_url', 'description').get(id=obj.target_id)
                return {
                    'type': 'wallpaper',
                    'id': wallpaper.id,
                    'source_data': {
                        'name': wallpaper.name,
                        'thumb_url': wallpaper.thumb_url,
                        'description': wallpaper.description or '',
                        'obj_type': 'wallpaper'
                    }
                }
            elif obj.target_type == 'comment':
                # 场景：别人回复了我的评论，或点赞了某条评论
                comment = WallpaperComment.objects.select_related('parent__customer', 'wallpaper').get(id=obj.target_id)
                result = {
                    'type': 'comment',
                    'content': comment.content[:50],
                    'wallpaper_name': comment.wallpaper.name,
                    'wallpaper_id': comment.wallpaper.id
                }
                # 确定 source_data：如果是回复，显示被回复的评论；如果是首评，显示壁纸信息
                if comment.parent:
                    # 情况1：回复了别人的评论 -> source_data 是被回复的那条
                    source_obj = comment.parent
                    result['source_data'] = {
                        'id': source_obj.id,
                        'content': source_obj.content,
                        'author': source_obj.customer.nickname or source_obj.customer.email,
                        'obj_type': 'comment'
                    }
                else:
                    # 情况2：首次评论壁纸 -> source_data 是该壁纸
                    wallpaper = comment.wallpaper
                    result['source_data'] = {
                        'id': wallpaper.id,
                        'name': wallpaper.name,
                        'thumb_url': wallpaper.thumb_url,
                        'obj_type': 'wallpaper'
                    }
                return result
        except Exception:
            pass
        return None

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
        elif obj.notification_type == 'reward':
            points = obj.extra_data.get('points', 0)
            reason = obj.extra_data.get('reason', '系统奖励')
            return f"{reason} {points} 积分"
        elif obj.notification_type == 'announcement':
            return obj.extra_data.get('title', '系统公告')
        else:
            return "收到一条新消息"


@extend_schema(tags=["消息通知"])
@extend_schema_view(
    list=extend_schema(
        summary="获取我的通知列表",
        description="分页获取当前用户的通知，支持按类型筛选（显示所有历史消息，不受设置影响）",
        parameters=[
            OpenApiParameter(name="type", type=str, required=False, description="通知类型筛选 (like/comment/follow/reward/announcement)"),
            OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码"),
            OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量"),
        ],
    ),
    destroy=extend_schema(
        summary="删除通知",
        description="删除指定的一条通知",
        responses={204: "删除成功", 404: "通知不存在或无权操作"}
    ),
)
class NotificationViewSet(BaseViewSet):
    """
    消息通知 ViewSet
    """
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    pagination_class = CustomPagination
    permission_classes = [IsCustomerTokenValid]

    def get_queryset(self):
        """只返回当前用户的通知"""
        current_user_id = self.get_serializer_context().get('current_user_id')
        if current_user_id:
            return Notification.objects.filter(recipient_id=current_user_id)
        return Notification.objects.none()

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

    @extend_schema(
        summary="标记通知为已读",
        description="传入通知ID或 'all' 来标记单条或全部通知为已读",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "id": {"oneOf": [{"type": "integer"}, {"type": "string", "enum": ["all"]}], "description": "通知ID 或 'all'"}
                },
                "required": ["id"]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "message": {"type": "string", "example": "标记成功"}
                }
            }
        }
    )
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

    @extend_schema(
        summary="获取未读通知数量",
        description="返回当前用户未读消息的总数（根据用户设置过滤）",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {"count": {"type": "integer"}},
                    "message": {"type": "string"}
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        """获取未读通知数量（根据用户设置过滤）"""
        current_user_id = self.get_serializer_context().get('current_user_id')
        if not current_user_id:
            return ApiResponse(code=401, message="请先登录")
        
        # 获取用户的通知设置
        try:
            settings = UserNotificationSettings.objects.get(user_id=current_user_id)
        except UserNotificationSettings.DoesNotExist:
            # 如果没有设置，默认全部开启，返回所有未读数
            count = Notification.objects.filter(recipient_id=current_user_id, is_read=False).count()
            return ApiResponse(data={'count': count})
        
        # 构建需要排除的通知类型列表
        excluded_types = []
        if not settings.enable_like_notification:
            excluded_types.append('like')
        if not settings.enable_comment_notification:
            excluded_types.append('comment')
        if not settings.enable_reply_notification:
            excluded_types.append('reply')
        if not settings.enable_follow_notification:
            excluded_types.append('follow')
        
        # 查询未读通知
        queryset = Notification.objects.filter(recipient_id=current_user_id, is_read=False)
        if excluded_types:
            queryset = queryset.exclude(notification_type__in=excluded_types)
        
        count = queryset.count()
        return ApiResponse(data={'count': count})

    @extend_schema(
        summary="获取通知设置",
        description="获取当前用户的通知开关设置",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "enable_like_notification": {"type": "boolean", "description": "点赞通知"},
                            "enable_comment_notification": {"type": "boolean", "description": "评论通知"},
                            "enable_reply_notification": {"type": "boolean", "description": "回复通知"},
                            "enable_follow_notification": {"type": "boolean", "description": "关注通知"}
                        }
                    },
                    "message": {"type": "string"}
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='notification-settings')
    def get_notification_settings(self, request):
        """获取通知设置"""
        current_user_id = self.get_serializer_context().get('current_user_id')
        if not current_user_id:
            return ApiResponse(code=401, message="请先登录")
        
        # 使用 get_or_create 确保有默认值
        settings, created = UserNotificationSettings.objects.get_or_create(
            user_id=current_user_id,
            defaults={
                'enable_like_notification': True,
                'enable_comment_notification': True,
                'enable_reply_notification': True,
                'enable_follow_notification': True,
            }
        )
        
        return ApiResponse(
            data={
                'enable_like_notification': settings.enable_like_notification,
                'enable_comment_notification': settings.enable_comment_notification,
                'enable_reply_notification': settings.enable_reply_notification,
                'enable_follow_notification': settings.enable_follow_notification,
            },
            message="获取成功"
        )

    @extend_schema(
        summary="更新通知设置",
        description="更新当前用户的通知开关设置（只传需要修改的字段）",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "enable_like_notification": {"type": "boolean", "description": "点赞通知"},
                    "enable_comment_notification": {"type": "boolean", "description": "评论通知"},
                    "enable_reply_notification": {"type": "boolean", "description": "回复通知"},
                    "enable_follow_notification": {"type": "boolean", "description": "关注通知"}
                }
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "message": {"type": "string", "example": "设置更新成功"}
                }
            }
        }
    )
    @action(detail=False, methods=['post'], url_path='update-notification-settings')
    def update_notification_settings(self, request):
        """更新通知设置"""
        current_user_id = self.get_serializer_context().get('current_user_id')
        if not current_user_id:
            return ApiResponse(code=401, message="请先登录")
        
        # 获取或创建设置
        settings, created = UserNotificationSettings.objects.get_or_create(
            user_id=current_user_id,
            defaults={
                'enable_like_notification': True,
                'enable_comment_notification': True,
                'enable_reply_notification': True,
                'enable_follow_notification': True,
            }
        )
        
        # 更新字段（只更新传入的字段）
        if 'enable_like_notification' in request.data:
            settings.enable_like_notification = request.data['enable_like_notification']
        if 'enable_comment_notification' in request.data:
            settings.enable_comment_notification = request.data['enable_comment_notification']
        if 'enable_reply_notification' in request.data:
            settings.enable_reply_notification = request.data['enable_reply_notification']
        if 'enable_follow_notification' in request.data:
            settings.enable_follow_notification = request.data['enable_follow_notification']
        
        settings.save()
        
        return ApiResponse(
            data={
                'enable_like_notification': settings.enable_like_notification,
                'enable_comment_notification': settings.enable_comment_notification,
                'enable_reply_notification': settings.enable_reply_notification,
                'enable_follow_notification': settings.enable_follow_notification,
            },
            message="设置更新成功"
        )
