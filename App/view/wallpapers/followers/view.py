#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：view.py
@Author  ：Liang
@Date    ：2026/4/15
@description : 粉丝与关注功能
"""
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from rest_framework.decorators import action

from models.models import UserFollow, CustomerUser
from tool.base_views import BaseViewSet
from tool.permissions import IsCustomerTokenValid
from tool.token_tools import CustomTokenTool
from tool.utils import ApiResponse, CustomPagination


class CustomerUserBriefSerializer(serializers.ModelSerializer):
    """用户简要信息序列化器（用于粉丝/关注列表）"""
    is_followed = serializers.SerializerMethodField()

    class Meta:
        model = CustomerUser
        fields = [
            'id', 'email', 'nickname', 'gender', 'avatar_url', 
            'points', 'level', 'upload_count', 'collection_count', 'is_followed'
        ]
        read_only_fields = fields

    def get_is_followed(self, obj):
        """判断当前登录用户是否关注了该用户"""
        current_user_id = self.context.get('current_user_id')
        if not current_user_id:
            return False
        return UserFollow.objects.filter(
            follower_id=current_user_id, 
            following_id=obj.id
        ).exists()


@extend_schema(tags=["用户关注"])
@extend_schema_view(
    list=extend_schema(
        summary="获取我的关注列表",
        description="获取当前用户关注的所有用户列表",
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
                            "results": {"type": "array", "items": {"$ref": "#/components/schemas/CustomerUserBrief"}},
                            "total": {"type": "integer", "example": 50}
                        }
                    },
                    "message": {"type": "string", "example": "关注列表获取成功"}
                }
            }
        }
    ),
    create=extend_schema(
        summary="创建关注/取消关注用户",
        description="传入 following_id，如果已关注则取消，未关注则关注",
    ),
)
class UserFollowViewSet(BaseViewSet):
    """
    用户关注与粉丝 ViewSet
    """
    queryset = UserFollow.objects.none()
    serializer_class = CustomerUserBriefSerializer
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

    @extend_schema(
        summary="获取我的关注列表",
        description="获取当前用户关注的所有用户列表",
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
                            "results": {"type": "array", "items": {"$ref": "#/components/schemas/CustomerUserBrief"}},
                            "total": {"type": "integer", "example": 50}
                        }
                    },
                    "message": {"type": "string", "example": "关注列表获取成功"}
                }
            }
        }
    )
    def list(self, request, *args, **kwargs):
        """获取我的关注列表"""
        current_user_id = self.get_serializer_context().get('current_user_id')
        if not current_user_id:
            return ApiResponse(code=401, message="请先登录")
            
        # 查询我关注的关系记录
        queryset = UserFollow.objects.filter(follower_id=current_user_id).select_related('following').order_by('-created_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            users = [item.following for item in page]
            serializer = self.get_serializer(users, many=True, context={'current_user_id': current_user_id})
            return self.get_paginated_response(serializer.data)
        
        users = [item.following for item in queryset]
        serializer = self.get_serializer(users, many=True, context={'current_user_id': current_user_id})
        return ApiResponse(data=serializer.data, message="关注列表获取成功")

    @extend_schema(
        summary="关注/取消关注用户",
        description="传入 following_id，如果已关注则取消，未关注则关注",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "following_id": {"type": "integer", "description": "要关注的用户ID"}
                },
                "required": ["following_id"]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {"is_followed": {"type": "boolean"}},
                    "message": {"type": "string"}
                }
            }
        }
    )
    @action(detail=False, methods=['post'], url_path='toggle')
    def toggle_follow(self, request):
        """
        关注/取消关注用户
        传参：following_id (要关注的用户ID)
        """
        current_user_id = self.get_serializer_context().get('current_user_id')
        following_id = request.data.get('following_id')

        if not following_id:
            return ApiResponse(code=400, message="请提供 following_id")
        
        try:
            following_id = int(following_id)
        except (TypeError, ValueError):
            return ApiResponse(code=400, message="following_id 无效")

        if current_user_id == following_id:
            return ApiResponse(code=400, message="不能关注自己")

        try:
            target_user = CustomerUser.objects.get(id=following_id)
        except CustomerUser.DoesNotExist:
            return ApiResponse(code=404, message="目标用户不存在")

        follow_record, created = UserFollow.objects.get_or_create(
            follower_id=current_user_id,
            following_id=following_id
        )

        if created:
            # 发送关注通知
            try:
                from App.view.notifications.notification_center import NotificationCenter
                current_user = CustomerUser.objects.get(id=current_user_id)
                NotificationCenter.send_follow(
                    recipient_id=following_id,
                    sender_id=current_user_id,
                    follower_nickname=current_user.nickname or current_user.email
                )
            except Exception:
                pass
                
            return ApiResponse(
                data={'is_followed': True},
                message=f"关注 {target_user.nickname or target_user.email} 成功"
            )
        else:
            follow_record.delete()
            return ApiResponse(
                data={'is_followed': False},
                message=f"已取消关注 {target_user.nickname or target_user.email}"
            )

    @extend_schema(
        summary="获取我的粉丝列表",
        description="获取关注当前用户的所有粉丝列表",
        parameters=[
            OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码"),
            OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量"),
        ],
    )
    @action(detail=False, methods=['get'], url_path='my-followers')
    def my_followers(self, request):
        """获取我的粉丝列表"""
        current_user_id = self.get_serializer_context().get('current_user_id')
        if not current_user_id:
            return ApiResponse(code=401, message="请先登录")
            
        # 查询关注我的关系记录
        queryset = UserFollow.objects.filter(following_id=current_user_id).select_related('follower').order_by('-created_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            users = [item.follower for item in page]
            serializer = self.get_serializer(users, many=True, context={'current_user_id': current_user_id})
            return self.get_paginated_response(serializer.data)
        
        users = [item.follower for item in queryset]
        serializer = self.get_serializer(users, many=True, context={'current_user_id': current_user_id})
        return ApiResponse(data=serializer.data, message="粉丝列表获取成功")

    @action(detail=False, methods=['get'], url_path='is-following')
    def is_following(self, request):
        """查询是否关注了某个用户"""
        current_user_id = self.get_serializer_context().get('current_user_id')
        user_id = request.query_params.get('user_id')

        if not user_id:
            return ApiResponse(code=400, message="请提供 user_id")
        
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return ApiResponse(code=400, message="user_id 无效")

        is_followed = UserFollow.objects.filter(
            follower_id=current_user_id,
            following_id=user_id
        ).exists()

        return ApiResponse(data={'is_followed': is_followed})
