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
from django.utils import timezone

from models.models import Notification, UserNotificationSettings, CustomerUser
from tool.base_views import BaseViewSet
from tool.permissions import IsCustomerTokenValid, IsAdmin
from tool.token_tools import CustomTokenTool
from tool.utils import ApiResponse, CustomPagination


class NotificationSerializer(serializers.ModelSerializer):
    """通知序列化器"""
    sender_info = serializers.SerializerMethodField()
    content_display = serializers.SerializerMethodField()
    target_content = serializers.SerializerMethodField()

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
                comment = WallpaperComment.objects.select_related('parent__customer', 'wallpaper').get(id=obj.target_id)
                result = {
                    'type': 'comment',
                    'content': comment.content[:50],
                    'wallpaper_name': comment.wallpaper.name,
                    'wallpaper_id': comment.wallpaper.id
                }
                if comment.parent:
                    source_obj = comment.parent
                    result['source_data'] = {
                        'id': source_obj.id,
                        'content': source_obj.content,
                        'author': source_obj.customer.nickname or source_obj.customer.email,
                        'obj_type': 'comment'
                    }
                else:
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


class AnnouncementSerializer(serializers.Serializer):
    """管理员发送公告的请求序列化器"""
    title = serializers.CharField(max_length=200, required=True, help_text="公告标题")
    content = serializers.CharField(required=True, help_text="公告内容")
    send_to = serializers.ChoiceField(
        choices=['all', 'specific'],
        required=True,
        help_text="发送对象：all=全部用户，specific=指定用户"
    )
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="指定用户ID列表（当 send_to=specific 时必填）"
    )

    def validate(self, attrs):
        if attrs['send_to'] == 'specific' and not attrs.get('user_ids'):
            raise serializers.ValidationError("指定用户时必须提供 user_ids 列表")
        return attrs


@extend_schema(tags=["消息通知"])
@extend_schema_view(
    list=extend_schema(
        summary="获取我的通知列表",
        description="分页获取当前用户的通知，支持按类型筛选。\n\n"
                    "**普通用户**：只返回自己的通知\n\n"
                    "**后台管理员**：返回所有用户的通知",
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
    permission_classes = []

    def get_permissions(self):
        """根据不同操作返回不同的权限类"""
        if self.action in ['send_announcement']:
            return [IsAdmin()]
        return []

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
                ctx["user_type"] = "customer"
                ctx["is_admin"] = False
            else:
                from models.models import User
                ok_admin, admin_id = CustomTokenTool.verify_token(tok)
                if ok_admin:
                    try:
                        admin_user = User.objects.get(id=admin_id)
                        ctx["current_user_id"] = admin_id
                        ctx["user_type"] = "admin"
                        ctx["is_admin"] = admin_user.role in ['admin', 'operator', 'super_admin']
                    except User.DoesNotExist:
                        pass
        return ctx

    def list(self, request, *args, **kwargs):
        """获取通知列表"""
        current_user_id = self.get_serializer_context().get('current_user_id')
        user_type = self.get_serializer_context().get('user_type')
        is_admin = self.get_serializer_context().get('is_admin', False)

        if not current_user_id:
            return ApiResponse(code=401, message="请先登录")

        if is_admin:
            queryset = Notification.objects.all().select_related('sender', 'recipient')
        else:
            queryset = Notification.objects.filter(recipient_id=current_user_id).select_related('sender')

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
        summary="管理员发送系统公告",
        description="send_to：all/special；notification_type：system/feature/Activity管理员向用户发送系统公告，支持发送给全部用户或指定用户",
        request=AnnouncementSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "success_count": {"type": "integer", "description": "成功发送数量"},
                            "total_count": {"type": "integer", "description": "总发送数量"}
                        }
                    },
                    "message": {"type": "string", "example": "公告发送成功"}
                }
            },
            400: "参数错误",
            403: "无权限"
        }
    )
    @action(detail=False, methods=['post'], url_path='send-announcement', permission_classes=[IsAdmin])
    def send_announcement(self, request):
        """
        管理员发送系统公告
        - 支持发送给全部用户或指定用户
        - 自动记录发送人（管理员）
        """
        # 验证请求数据
        serializer = AnnouncementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        title = serializer.validated_data['title']
        content = serializer.validated_data['content']
        send_to = serializer.validated_data['send_to']
        user_ids = serializer.validated_data.get('user_ids', [])
        notification_type = serializer.validated_data['notification_type',""]
        # 确定接收者列表
        if send_to == 'all':
            recipients = CustomerUser.objects.all()
        else:
            recipients = CustomerUser.objects.filter(id__in=user_ids)
            # 检查是否有不存在的用户
            if recipients.count() != len(user_ids):
                return ApiResponse(code=400, message="部分用户ID不存在")

        total_count = recipients.count()
        if total_count == 0:
            return ApiResponse(code=400, message="没有符合条件的接收者")

        # 批量创建通知
        notifications = []
        for recipient in recipients:
            notifications.append(
                Notification(
                    recipient=recipient,
                    sender=None,  # 系统公告不需要发送者
                    notification_type='announcement',
                    extra_data={
                        'title': title,
                        'content': content,
                        'sent_by_admin': request.user.username if hasattr(request, 'user') else 'system',
                        'notification_type': notification_type
                    }
                )
            )
        Notification.objects.bulk_create(notifications, batch_size=100)
        return ApiResponse(
            data={
                'success_count': total_count,
                'total_count': total_count
            },
            message=f"公告已成功发送给 {total_count} 个用户"
        )

    @extend_schema(
        summary="标记通知为已读",
        description="传入通知ID或 'all' 来标记单条或全部通知为已读",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "id": {"oneOf": [{"type": "integer"}, {"type": "string", "enum": ["all"]}], "description": "special 或 'all'"}
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

        try:
            settings = UserNotificationSettings.objects.get(user_id=current_user_id)
        except UserNotificationSettings.DoesNotExist:
            count = Notification.objects.filter(recipient_id=current_user_id, is_read=False).count()
            return ApiResponse(data={'count': count})

        excluded_types = []
        if not settings.enable_like_notification:
            excluded_types.append('like')
        if not settings.enable_comment_notification:
            excluded_types.append('comment')
        if not settings.enable_reply_notification:
            excluded_types.append('reply')
        if not settings.enable_follow_notification:
            excluded_types.append('follow')

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

        settings, created = UserNotificationSettings.objects.get_or_create(
            user_id=current_user_id,
            defaults={
                'enable_like_notification': True,
                'enable_comment_notification': True,
                'enable_reply_notification': True,
                'enable_follow_notification': True,
            }
        )

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
