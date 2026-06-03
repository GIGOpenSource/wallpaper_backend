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
    target_id = serializers.SerializerMethodField()
    recipient_maps = serializers.SerializerMethodField()


    class Meta:
        model = Notification
        fields = [
            'id', 'sender_info', 'notification_type', 'content_display',
            'target_id', 'target_type', 'target_content', 'extra_data', 'is_read', 'created_at',
            'recipient_maps'
        ]
        read_only_fields = fields


    def get_recipient_maps(self, obj):
        """仅管理员查看系统公告时返回该system_code下的所有接收者信息列表"""
        is_admin = self.context.get('is_admin', False)
        if not is_admin or not obj.system_code:
            return None

        # 查询该system_code下的所有接收者信息
        recipients = Notification.objects.filter(
            system_code=obj.system_code
        ).select_related('recipient').values(
            'recipient_id',
            'recipient__nickname',
            'recipient__avatar_url',
            'recipient__gender'
        ).distinct()

        # 转换为数组格式，每个元素包含完整信息
        recipient_list = [
            {
                'id': item['recipient_id'],
                'nickname': item['recipient__nickname'] or f"用户{item['recipient_id']}",
                'avatar_url': item['recipient__avatar_url'],
                'gender': item['recipient__gender'],
            }
            for item in recipients
        ]
        return recipient_list

    def get_target_id(self, obj):
        """自定义 target_id 返回逻辑"""
        from models.models import WallpaperComment
        try:
            if obj.target_type == 'comment':
                comment = WallpaperComment.objects.select_related('wallpaper').get(id=obj.target_id)
                return comment.wallpaper.id
        except Exception:
            pass
        return obj.target_id

    def get_sender_info(self, obj):
        # 系统公告和活动公告不显示发送者，统一显示为系统
        if obj.notification_type in ['system']:
            return {'nickname': '系统通知', 'avatar_url': None}
        if obj.notification_type in ['Activity']:
            return {'nickname': '活动通知', 'avatar_url': None}

        if obj.notification_type in ['feature']:
            return {'nickname': '功能通知', 'avatar_url': None}
        # 其他类型通知显示实际发送者
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
                    'wallpaper_id': comment.wallpaper.id,
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
        # 系统公告和活动公告：显示标题 + 内容
        if obj.notification_type in ['system', 'Activity']:
            title = obj.extra_data.get('title', '')
            content = obj.extra_data.get('content', '')
            if title and content:
                return f"{title} : {content}"
            elif title:
                return title
            elif content:
                return content
            else:
                return "系统公告"
        
        # 其他类型通知的显示逻辑
        nickname = obj.sender.nickname if obj.sender else "系统"
        if obj.notification_type == 'like':
            return f"{nickname} 赞了你的帖子"
        if obj.notification_type == 'wallpaper_like':
            return f"{nickname} 赞了你的壁纸"
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
        elif obj.notification_type == 'feature':
            # 更新公告也显示标题+内容
            title = obj.extra_data.get('title', '')
            content = obj.extra_data.get('content', '')
            if title and content:
                return f"{title} {content}"
            elif title:
                return title
            elif content:
                return content
            else:
                return "更新公告"
        else:
            return "收到一条新消息"


class AnnouncementSerializer(serializers.Serializer):
    """管理员发送公告的请求序列化器"""
    notification_type = serializers.ChoiceField(
        choices=['system', 'feature', 'Activity'],
        required=True,
        help_text="公告类型：system=系统公告，feature=更新公告，Activity=活动公告"
    )
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
            OpenApiParameter(name="notification_type", type=str, required=False, description="通知类型筛选 (feature/Activity/system)"),
            OpenApiParameter(name="type", type=str, required=False, description="通知公告 announcement"),
            OpenApiParameter(name="title", type=str, required=False, description="通知标题"),
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
        is_admin = self.get_serializer_context().get('is_admin', False)
        if is_admin:
            return Notification.objects.all()
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
        is_admin = self.get_serializer_context().get('is_admin', False)

        if not current_user_id:
            return ApiResponse(code=401, message="请先登录")

        if is_admin:
            queryset = Notification.objects.all().select_related('sender', 'recipient')
        else:
            queryset = Notification.objects.filter(recipient_id=current_user_id).select_related('sender')
        n_type = request.query_params.get('type')
        notification_type = request.query_params.get('notification_type')
        if n_type:
            if n_type == 'announcement' and not notification_type:
                queryset = queryset.filter(notification_type__in=['system', 'feature', 'Activity'])
            else:
                queryset = queryset.filter(notification_type=notification_type)
        title = request.query_params.get('title', '').strip()
        if title:
            queryset = queryset.filter(extra_data__title__icontains=title)

        if is_admin and (n_type == 'announcement' or notification_type in ['system', 'feature', 'Activity']):
            # 分离有system_code和没有system_code的记录
            has_code_queryset = queryset.exclude(system_code__isnull=True).exclude(system_code='')
            no_code_queryset = queryset.filter(system_code__isnull=True) | queryset.filter(system_code='')

            # 对有system_code的记录进行去重
            if has_code_queryset.exists():
                # 获取每个system_code的最新记录ID
                from django.db.models import Max
                latest_ids = has_code_queryset.values('system_code').annotate(
                    latest_id=Max('id')
                ).values_list('latest_id', flat=True)

                has_code_queryset = Notification.objects.filter(id__in=latest_ids)

            # 合并两个查询集（先去重的，再未去重的）
            if has_code_queryset.exists() and no_code_queryset.exists():
                # 使用Union合并，但需要先转为list再排序
                combined_ids = list(has_code_queryset.values_list('id', flat=True)) + \
                               list(no_code_queryset.values_list('id', flat=True))
                queryset = Notification.objects.filter(id__in=combined_ids)
            elif has_code_queryset.exists():
                queryset = has_code_queryset
            # 如果只有没有code的记录，保持原样

            # queryset = queryset.order_by('system_code', '-created_at').distinct('system_code')

        queryset = queryset.order_by('-created_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="通知列表获取成功")

    def destroy(self, request, *args, **kwargs):
        """删除通知（管理员删除带system_code的公告时会批量删除）"""
        current_user_id = self.get_serializer_context().get('current_user_id')
        is_admin = self.get_serializer_context().get('is_admin', False)

        if not current_user_id:
            return ApiResponse(code=401, message="请先登录")

        try:
            notification = self.get_object()
        except Notification.DoesNotExist:
            return ApiResponse(code=404, message="通知不存在")

        # 管理员删除逻辑
        if is_admin:
            if notification.system_code:
                # 有system_code，删除该code下的所有记录
                deleted_count, _ = Notification.objects.filter(
                    system_code=notification.system_code
                ).delete()
                return ApiResponse(
                    data={'deleted_count': deleted_count},
                    message=f"已删除 {deleted_count} 条相关通知"
                )
            else:
                # 无system_code，只删除当前记录
                notification.delete()
                return ApiResponse(message="删除成功")
        else:
            # 普通用户只能删除自己的通知
            if notification.recipient_id != current_user_id:
                return ApiResponse(code=403, message="无权操作此通知")
            notification.delete()
            return ApiResponse(message="删除成功")


    @extend_schema(
        summary="管理员发送系统公告",
        description="send_to：all/specific；notification_type：system/feature/Activity管理员向用户发送系统公告，支持发送给全部用户或指定用户",
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
        import hashlib
        import time
        # 验证请求数据
        serializer = AnnouncementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        title = serializer.validated_data['title']
        content = serializer.validated_data['content']
        send_to = serializer.validated_data['send_to']
        user_ids = serializer.validated_data.get('user_ids', [])
        notification_type = serializer.validated_data.get('notification_type', 'system')
        timestamp = str(int(time.time() * 1000))
        system_code = hashlib.md5(timestamp.encode('utf-8')).hexdigest()

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
                    notification_type=notification_type,
                    extra_data={
                        'title': title,
                        'content': content,
                        'sent_by_admin': request.user.username if hasattr(request, 'user') else 'system',
                        'notification_type': notification_type,
                        'send_to':send_to,
                    },
                    system_code=system_code
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
        # 设置按钮默认是true 开启状态
        if not settings.enable_like_notification:
            excluded_types.append('like')
            excluded_types.append('wallpaper_like')
        if not settings.enable_comment_notification:
            excluded_types.append('comment')
        if not settings.enable_reply_notification:
            excluded_types.append('reply')
        if not settings.enable_follow_notification:
            excluded_types.append('follow')

        queryset = Notification.objects.filter(recipient_id=current_user_id, is_read=False)
        actual_count = queryset.count()
        if excluded_types:
            queryset = queryset.exclude(notification_type__in=excluded_types)

        count = queryset.count()
        return ApiResponse(data={'count': count,'actual_count':actual_count})

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
