#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from django.db import IntegrityError
from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, extend_schema_view

from models.models import User
from tool.password_hasher import verify_password
from tool.permissions import IsTokenValid, IsOwnerOrAdmin
from tool.token_tools import CustomTokenTool, generate_is_user_token
from tool.utils import ApiResponse
from django.utils.translation import gettext as _

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'confirm_password')  # 新增 id（生成 Token 需用）

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError(_("两次输入的密码不一致"))
        return data

    def validate_password(self, value):
        """
        验证密码长度不超过72字节
        """
        if len(value.encode('utf-8')) > 72:
            raise serializers.ValidationError(_("密码长度不能超过72字节"))
        return value

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        # 使用自定义加密替代 Django 的 make_password
        return User.objects.create(** validated_data)

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

@extend_schema(tags=["系统用户管理"])
@extend_schema_view(
    list=extend_schema(summary='获取管理员列表（需有效 Token）'),
    retrieve=extend_schema(summary='获取用户详情（需有效 Token）'),
    destroy=extend_schema(summary='删除用户'),
    update=extend_schema(summary='更新用户'),
)
class UserViewSet(viewsets.ViewSet):
    # 权限分配：登录/注册允许匿名访问，其他接口需有效 Token
    permission_classes_by_action = {
        'register': [],  # 匿名可访问
        'login': [],  # 匿名可访问
        'list': [IsTokenValid],  # 需有效 Token
        'retrieve': [IsTokenValid],  # 需有效 Token
        'destroy': [IsTokenValid, IsOwnerOrAdmin],  # 删除操作需要同时满足两个权限
    }
    queryset = User.objects.all()

    def get_permissions(self):
        """动态获取当前接口的权限类"""
        return [perm() for perm in self.permission_classes_by_action.get(self.action, [])]

    # -------------------------- 注册接口：生成 Token 返回 --------------------------
    @extend_schema(
        request=RegisterSerializer,
        responses={
            201: {"type": "object", "properties": {"token": {"type": "string"}, "user_id": {"type": "integer"}}}},
        summary=_("管理员注册（匿名可访问）"),
    )
    @action(detail=False, methods=['post'], url_path='register')
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # 生成自定义 Token（用管理员 ID 关联）
            token = CustomTokenTool.generate_token(user_id=user.id)
            return ApiResponse(
                {"token": token, "user_id": user.id, "username": user.username},

            )
        return ApiResponse(serializer.errors)
    @extend_schema(
        request=LoginSerializer,
        responses={
            200: {"type": "object", "properties": {"token": {"type": "string"}, "user_id": {"type": "integer"}}}},
        summary="管理员登录（匿名可访问）"
    )
    @action(detail=False, methods=['post'], url_path='login')
    def login(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        # 1. 校验输入
        if not username or not password:
            return ApiResponse(message=_('管理员名和密码不能为空'),code=400)
        # 2. 查询管理员并校验密码
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return ApiResponse(message= _('管理员名不存在'),code=400)
        except IntegrityError:  # 避免管理员名重复（理论上 username 已设 unique，此处兜底）
            return ApiResponse(message=_('管理员名重复'),code=400)

        if verify_password(password, user.password):  # 注意参数顺序：原始密码在前，哈希密码在后
            token = generate_is_user_token(request,user)
            return ApiResponse(
                {"token": token, "user_id": user.id, "username": user.username},
            )
        return ApiResponse(message=_("管理员名密码错误"),code=400)

    def list(self, request):
        # print(_("当前登录管理员：%s") % request.user.username)
        users = self.queryset.all()
        serializer = RegisterSerializer(users, many=True)
        return ApiResponse(serializer.data)

    @extend_schema(
        responses={200: {"type": "object", "properties": {"message": {"type": "string"}}}},
        summary=_("管理员登出（需有效 Token）")
    )
    @action(detail=False, methods=['post'], url_path='logout')
    def logout(self, request):
        # 从请求头获取 Token
        from django.utils.translation import get_language
        current_language = get_language()
        print(f"当前识别的语言：{current_language}")  # 应输出 'ja'
        token = request.session.get('auth_token')
        if not token:
            return ApiResponse(message=_("未提供有效 Token"),code=400)
        if token:
            CustomTokenTool.delete_token(token)
            # 调用工具类删除 Redis 中的 Token
            return ApiResponse(message=_("登出成功，Token 已失效"))
        return ApiResponse(message=_("未提供有效 Token"),code=400)


def deactivate_user_and_delete_posters(open_id):
    """
    历史微信注销流程占位。微信管理员表已移除，请使用 client 邮箱账户体系。
    """
    return {
        "success": False,
        "message": "微信账户已下线，请使用邮箱注册登录（/client/users/register/）",
    }
