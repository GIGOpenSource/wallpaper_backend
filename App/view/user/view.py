#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from django.db import IntegrityError
from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework.exceptions import ValidationError

from models.models import User, Role, CustomerUser
from tool.base_views import BaseViewSet
from tool.password_hasher import verify_password
from tool.permissions import IsTokenValid, IsOwnerOrAdmin, IsAdmin
from tool.token_tools import CustomTokenTool, generate_is_user_token
from tool.utils import ApiResponse, CustomPagination
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

@extend_schema(tags=["(Admin)系统用户管理 管理员登录注册退出"])
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
        token = request.auth
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


#用户角色序列化器
class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'

@extend_schema(tags=["角色管理"])
@extend_schema_view(
    list=extend_schema(
        summary="获取所有角色管理列表",
        description="获取角色管理列表",
        parameters=[
            OpenApiParameter(name="user_type", type=str, required=False, description="角色类型：admin、customer"),
            OpenApiParameter(name="name", type=str, required=False, description="角色名称中文名"),
        ],
    ),
    create=extend_schema(summary="创建角色"),
    retrieve=extend_schema(summary="获取评论详情"),
    update=extend_schema(
        summary="更新角色",
        description="修改角色内容",
    ),
    partial_update=extend_schema(
        summary="部分更新角色",
        description="部分修改自己的角色",
    ),
    destroy=extend_schema(
        summary="删除角色论",
        description="删除自己的角色",
        responses={204: "删除成功", 404: "角色不存在"}
    )
)
class RoleViewSet(BaseViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAdmin]

    def list(self, request, *args, **kwargs):
        """
        管理员获取所有评论列表
        """
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.order_by('-created_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="角色列表获取成功")

    def get_queryset(self):
        queryset = super().get_queryset()
        user_type = self.request.query_params.get('user_type')
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)
        if user_type in ['admin', 'customer']:
            queryset = queryset.filter(user_type=user_type)
        return queryset.order_by('user_type', 'sort_order', '-created_at')

    @extend_schema(
        summary="更新角色用户数量统计",
        description="手动触发角色用户数量统计更新",
    )
    @action(detail=True, methods=['post'], url_path='update-count')
    def update_user_count(self, request, pk=None):
        """更新角色用户数量"""
        try:
            role = self.get_object()
            count = role.update_user_count()
            return ApiResponse(
                data={'user_count': count},
                message=f"用户数量已更新为 {count}"
            )
        except Exception as e:
            return ApiResponse(code=500, message=f"更新失败: {', '.join(e.args)}")


class AdminUserUpdateSerializer(serializers.Serializer):
    """管理员更新序列化器"""
    username = serializers.CharField(max_length=20, required=False, help_text="用户名")
    email = serializers.EmailField(required=False, help_text="邮箱")
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, help_text="手机号")
    role_id = serializers.IntegerField(required=False, help_text="角色ID")
    password = serializers.CharField(max_length=256, required=False, write_only=True, help_text="密码（可选，不传则不修改）")


    def create(self, validated_data):
        """创建用户（根据 role_id 判断是管理员还是C端用户）"""
        from tool.password_hasher import hash_password
        username = validated_data.get('username')
        email = validated_data.get('email')
        password = validated_data.get('password')
        phone = validated_data.get('phone', '')
        role_id = validated_data.get('role_id')
        
        if not username or not email or not password:
            raise serializers.ValidationError("用户名、邮箱和密码为必填项")
        
        # 尝试获取角色，如果不存在则创建 C 端用户
        role_code = None
        is_customer = False
        
        if role_id:
            try:
                role = Role.objects.get(id=role_id, user_type='admin', is_active=True)
                role_code = role.code
            except Role.DoesNotExist:
                # role_id 不存在，说明是 C 端用户
                is_customer = True
                role_code = 'customer'
        else:
            # 没有传 role_id，默认创建 C 端用户
            is_customer = True
            role_code = 'customer'
        
        # 如果是 C 端用户，使用 CustomerUser 表
        if is_customer:
            # 检查邮箱是否已存在
            if CustomerUser.objects.filter(email=email).exists():
                raise serializers.ValidationError("邮箱已存在")
            
            # 创建 C 端用户
            customer_user = CustomerUser.objects.create(
                email=email,
                password=password,  # CustomerUser 的 save 方法会自动哈希
                nickname=username,
            )
            return customer_user
        
        # 如果是管理员，使用 User 表
        # 检查用户名是否已存在
        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError("用户名已存在")
        # 检查邮箱是否已存在
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("邮箱已存在")
        
        # 创建管理员用户
        user = User.objects.create(
            username=username,
            email=email,
            password=hash_password(password[:72]),
            phone=phone,
            role=role_code
        )
        
        # 更新角色用户数量统计
        try:
            role = Role.objects.get(code=role_code)
            role.user_count += 1
            role.save(update_fields=['user_count'])
        except Role.DoesNotExist:
            pass
        
        return user
    def update(self, instance, validated_data):
        """更新管理员（此方法在 ViewSet.update 中手动处理，这里仅作占位）"""
        return instance


@extend_schema(tags=["(Admin)系统用户管理"])
@extend_schema_view(
    list=extend_schema(
        summary="获取管理员列表",
        parameters=[
            OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码"),
            OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量"),
            OpenApiParameter(name="username", type=str, required=False, description="管理员名字"),
        ],
    ),
    retrieve=extend_schema(summary="获取管理员详情"),
    create=extend_schema(
        summary="创建管理员",
        request=AdminUserUpdateSerializer,
    ),
    update=extend_schema(
        summary="更新管理员信息",
        description="支持更新用户名、邮箱、手机号、角色等字段，只需传递需要修改的字段",
        request=AdminUserUpdateSerializer,
    ),
    partial_update=extend_schema(
        summary="部分更新管理员",
        description="部分更新管理员信息",
        request=AdminUserUpdateSerializer,
    ),
    destroy=extend_schema(summary="删除管理员"),
)
class AdminUserViewSet(BaseViewSet):
    """
    后台管理员管理 ViewSet
    支持管理员的增删改查及角色分配
    """
    queryset = User.objects.all()
    serializer_class = AdminUserUpdateSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return AdminUserUpdateSerializer
        return AdminUserUpdateSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        username = self.request.query_params.get('username')
        if username:
            queryset = queryset.filter(username__icontains=username)
        return queryset.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        """创建用户（管理员或C端用户）"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # 判断是哪种类型的用户
            if isinstance(user, CustomerUser):
                # C 端用户返回格式
                return ApiResponse(
                    data={
                        'id': user.id,
                        'email': user.email,
                        'nickname': user.nickname,
                        'user_type': 'customer',
                        'status': user.status,
                        'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    },
                    message="C端用户创建成功",
                    code=201
                )
            else:
                # 后台管理员返回格式
                role_id = None
                if user.role:
                    try:
                        role = Role.objects.get(code=user.role)
                        role_id = role.id
                    except Role.DoesNotExist:
                        pass

                return ApiResponse(
                    data={
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'phone': user.phone,
                        'role': user.role,
                        'role_id': role_id,
                        'role_display': user.get_role_display(),
                        'user_type': 'admin',
                    },
                    message="管理员创建成功",
                    code=201
                )
        except Exception as e:
            return ApiResponse(code=500, message=f"创建失败: {', '.join(e.args)}")


    def update(self, request, *args, **kwargs):
        """更新管理员信息（包括角色）"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)

            validated_data = serializer.validated_data
            old_role_code = instance.role

            # 更新基本字段
            if 'username' in validated_data:
                instance.username = validated_data['username']
            if 'email' in validated_data:
                instance.email = validated_data['email']
            if 'phone' in validated_data:
                instance.phone = validated_data['phone']

            # 更新角色（通过 role_id）
            new_role_code = None
            if 'role_id' in validated_data:
                role_id = validated_data['role_id']
                try:
                    role = Role.objects.get(id=role_id, user_type='admin', is_active=True)
                    new_role_code = role.code
                    instance.role = new_role_code
                except Role.DoesNotExist:
                    return ApiResponse(code=400, message=f"角色 ID '{role_id}' 不存在或已禁用")

            # 更新密码（如果提供）
            if 'password' in validated_data and validated_data['password']:
                from tool.password_hasher import hash_password
                password = validated_data['password']
                if not password.startswith('$2b$'):
                    instance.password = hash_password(password[:72])

            instance.save()

            # 更新角色用户数量统计
            if new_role_code and new_role_code != old_role_code:
                # 旧角色用户数 -1
                if old_role_code:
                    try:
                        old_role = Role.objects.get(code=old_role_code)
                        old_role.user_count = max(0, old_role.user_count - 1)
                        old_role.save(update_fields=['user_count'])
                    except Role.DoesNotExist:
                        pass

                # 新角色用户数 +1
                try:
                    new_role = Role.objects.get(code=new_role_code)
                    new_role.user_count += 1
                    new_role.save(update_fields=['user_count'])
                except Role.DoesNotExist:
                    pass
            role_id = None
            if instance.role:
                try:
                    role = Role.objects.get(code=instance.role)
                    role_id = role.id
                except Role.DoesNotExist:
                    pass

            return ApiResponse(
                data={
                    'id': instance.id,
                    'username': instance.username,
                    'email': instance.email,
                    'phone': instance.phone,
                    'role': instance.role,
                    'role_id': role_id,
                    'role_display': instance.get_role_display(),
                },
                message="更新成功"
            )

        except Exception as e:
            return ApiResponse(code=500, message=f"更新失败: {', '.join(e.args)}")


    def partial_update(self, request, *args, **kwargs):
        """部分更新管理员信息"""
        return self.update(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        """获取管理员列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            data = []
            for user in page:
                role_id = None
                if user.role:
                    try:
                        role = Role.objects.get(code=user.role, user_type='admin')
                        role_id = role.id
                    except Role.DoesNotExist:
                        role_id = None
                        pass

                data.append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'phone': user.phone,
                    'role': user.role,
                    'role_id': role_id,
                    'role_display': user.get_role_display(),
                    'last_login': user.last_login,
                    'created_at': user.created_at,
                })
            return self.get_paginated_response(data)

        data = []
        for user in queryset:
            role_id = None
            if user.role:
                try:
                    role = Role.objects.get(code=user.role)
                    role_id = role.id
                except Role.DoesNotExist:
                    pass
            data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'phone': user.phone,
                'role': user.role,
                'role_id': role_id,
                'role_display': user.get_role_display(),
                'last_login': user.last_login,
                'created_at': user.created_at,
            })
        return ApiResponse(data=data, message="列表获取成功")

    def retrieve(self, request, *args, **kwargs):
        """获取管理员详情"""
        try:
            instance = self.get_object()
            data = {
                'id': instance.id,
                'username': instance.username,
                'email': instance.email,
                'phone': instance.phone,
                'role': instance.role,
                'role_display': instance.get_role_display(),
                'last_login': instance.last_login,
                'created_at': instance.created_at,
                'updated_at': instance.updated_at,
            }
            return ApiResponse(data=data, message="详情获取成功")
        except Exception as e:
            return ApiResponse(code=500, message=f"获取详情失败: {', '.join(e.args)}")

    def destroy(self, request, *args, **kwargs):
        try:
            if request.user.role == 'super_admin':
                pass
            else:
                return ApiResponse(code=401, message=f"删除失败: 非超级管理员不可删除")
        except Exception as e:
            return ApiResponse(code=401, message=f"删除失败:权限有问题，请联系管理员")
        """删除管理员"""
        try:
            instance = self.get_object()
            old_role_code = instance.role

            # 删除前更新角色用户数 -1
            if old_role_code:
                try:
                    old_role = Role.objects.get(code=old_role_code)
                    old_role.user_count = max(0, old_role.user_count - 1)
                    old_role.save(update_fields=['user_count'])
                except Role.DoesNotExist:
                    pass

            instance.delete()
            return ApiResponse(message="删除成功")
        except Exception as e:
            error_messages = "; ".join(str(msg) for msg in e.args) if e.args else str(e)
            return ApiResponse(code=500, message=f"删除失败: {error_messages}")
