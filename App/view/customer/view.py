# -*- coding: UTF-8 -*-
from django.db import IntegrityError
from django.db.models import Count
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers, viewsets
from rest_framework.decorators import action

from models.models import CustomerUser
from tool.base_views import BaseViewSet
from tool.password_hasher import verify_password
from tool.permissions import IsCustomerTokenValid, IsAdmin
from tool.token_tools import CustomTokenTool, generate_is_user_token
from tool.utils import ApiResponse, CustomPagination
from django.utils.translation import gettext as _


class CustomerRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomerUser
        fields = ("id", "email", "password", "confirm_password")

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError(_("两次输入的密码不一致"))
        return data

    def validate_password(self, value):
        if len(value.encode("utf-8")) > 72:
            raise serializers.ValidationError(_("密码长度不能超过72字节"))
        return value

    def validate_email(self, value):
        return value.strip().lower()

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        return CustomerUser.objects.create(**validated_data)


class CustomerLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    platform = serializers.CharField(
        required=False,
        default="",
        help_text="平台标识: PC, Phone, 或留空不区分"
    )

class CustomerProfileSerializer(serializers.ModelSerializer):
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    """用户信息序列化器"""
    class Meta:
        model = CustomerUser
        fields = ("id", "email", "nickname", "gender", "avatar_url", "badge", "points",
                  "level", "status", "followers_count","following_count")
        read_only_fields = ("id", "email", "points", "level","followers_count","following_count")
    
    def get_followers_count(self, obj):
        return obj.followers.count()
    def get_following_count(self, obj):
        return obj.following.count()

class CustomerUserListSerializer(serializers.ModelSerializer):
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    """用户列表序列化器（管理员使用）"""
    class Meta:
        model = CustomerUser
        fields = ("id", "email", "nickname", "gender", "avatar_url", "badge", "points",
                  "level", "status", "upload_count", "collection_count",
                  "last_login", "created_at","followers_count","following_count")
        read_only_fields = ("id", "email", "points", "level","followers_count","following_count", "created_at")
    def get_followers_count(self, obj):
        return obj.followers.count()
    def get_following_count(self, obj):
        return obj.following.count()

@extend_schema(tags=["客户账户"])
@extend_schema_view(
    list=extend_schema(
        summary="获取用户列表（管理员）",
        description="支持按邮箱、昵称、状态筛选，并支持按创建时间、粉丝数、关注数、等级排序。",
        parameters=[
            OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码"),
            OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量"),
            OpenApiParameter(name="email", type=str, required=False, description="按邮箱模糊搜索"),
            OpenApiParameter(name="nickname", type=str, required=False, description="按昵称模糊搜索"),
            OpenApiParameter(name="status", type=int, required=False, description="用户状态：1=正常，2=禁用"),
            OpenApiParameter(
                name="order",
                type=str,
                required=False,
                description="排序方式：latest=最新创建，fans=粉丝数降序，following=关注数降序，level=等级降序",
            ),
        ],
        responses={200: CustomerUserListSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="获取用户详情",
        responses={200: CustomerUserListSerializer, 404: "用户不存在"},
    ),
    create=extend_schema(
        summary="创建用户",
        request=CustomerUserListSerializer,
        responses={200: CustomerUserListSerializer},
    ),
    update=extend_schema(
        summary="更新用户",
        request=CustomerUserListSerializer,
        responses={200: CustomerUserListSerializer, 404: "用户不存在"},
    ),
    partial_update=extend_schema(
        summary="部分更新用户",
        request=CustomerUserListSerializer,
        responses={200: CustomerUserListSerializer, 404: "用户不存在"},
    ),
    destroy=extend_schema(
        summary="删除用户（管理员）",
        description="删除指定用户记录",
        responses={204: "删除成功", 404: "用户不存在"},
    ),
)
class CustomerUserViewSet(BaseViewSet):
    permission_classes_by_action = {
        "register": [],
        "login": [],
        "logout": [IsCustomerTokenValid],
        "profile": [],
        "update_profile": [IsCustomerTokenValid],
        "list": [IsAdmin],
    }
    def get_permissions(self):
        return [p() for p in self.permission_classes_by_action.get(self.action, [])]

    def list(self, request, *args, **kwargs):
        """
        管理员获取用户列表（支持分页、筛选、排序）
        - followers_count: 粉丝数（多少人关注我）
        - following_count: 关注数（我关注多少人）
        """
        queryset = CustomerUser.objects.annotate(
            followers_count=Count("followers", distinct=True),  # UserFollow.following -> related_name="followers"
            following_count=Count("following", distinct=True),  # UserFollow.follower  -> related_name="following"
        )
        # 按邮箱搜索
        email = request.query_params.get("email", "").strip()
        if email:
            queryset = queryset.filter(email__icontains=email)
        # 按昵称搜索
        nickname = request.query_params.get("nickname", "").strip()
        if nickname:
            queryset = queryset.filter(nickname__icontains=nickname)
        # 按状态筛选：1=正常，2=禁用
        status = request.query_params.get("status")
        if status:
            try:
                status = int(status)
                if status in [1, 2]:
                    queryset = queryset.filter(status=status)
            except (ValueError, TypeError):
                pass
        # 排序
        order = request.query_params.get("order", "latest").lower()
        order_mapping = {
            "latest": "-created_at",
            "fans": "-followers_count",
            "following": "-following_count",
            "level": "-level",
        }
        queryset = queryset.order_by(order_mapping.get(order, "-created_at"))
        paginator = CustomPagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = CustomerUserListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = CustomerUserListSerializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="用户列表获取成功")

    @extend_schema(
        request=CustomerRegisterSerializer,
        summary="客户注册（邮箱+密码）",
    )
    @action(detail=False, methods=["post"], url_path="register")
    def register(self, request):
        ser = CustomerRegisterSerializer(data=request.data)
        if not ser.is_valid():
            errors = ser.errors
            message_parts = []
            for field, field_errors in errors.items():
                for error in field_errors:
                    message_parts.append(error)
            if message_parts:
                raw_message = message_parts[0]
                clean_message = raw_message.replace(" ", "").replace("的", "").replace("。", "").replace("，", "")
            else:
                clean_message = _("参数校验失败")
            return ApiResponse(data=errors, message=clean_message, code=400)
        try:
            user = ser.save()
        except IntegrityError:
            return ApiResponse(message=_("该邮箱已被注册"), code=400)
        platform = request.data.get("platform", "")
        token = CustomTokenTool.generate_customer_token(user.id, platform=platform)

        return ApiResponse(
            data={"token": token, "customer_id": user.id, "email": user.email},
            message=_("注册成功"),
        )

    @extend_schema(
        request=CustomerLoginSerializer,
        summary="客户登录",
    )
    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        ser = CustomerLoginSerializer(data=request.data)
        if not ser.is_valid():
            return ApiResponse(data=ser.errors, message=_("参数校验失败"), code=400)
        email = ser.validated_data["email"].strip().lower()
        password = ser.validated_data["password"]
        platform = ser.validated_data.get("platform", "")

        try:
            user = CustomerUser.objects.get(email=email)
        except CustomerUser.DoesNotExist:
            return ApiResponse(message=_("邮箱未注册"), code=400)
        if not verify_password(password, user.password):
            return ApiResponse(message=_("邮箱或密码错误"), code=400)
        user.last_login = timezone.now()
        user.save(update_fields=["last_login", "updated_at"])
        token = CustomTokenTool.generate_customer_token(user.id, platform=platform)
        return ApiResponse(
            data={
                "token": token,
                "customer_id": user.id,
                "email": user.email,
                "platform": platform if platform else "default"
            },
            message=_("登录成功"),
        )

    @extend_schema(summary="客户登出（作废 CToken）")
    @action(detail=False, methods=["post"], url_path="logout")
    def logout(self, request):
        token = request.headers.get("token")
        if not token:
            return ApiResponse(message=_("未提供 Token"), code=400)
        CustomTokenTool.delete_customer_token(token)
        return ApiResponse(message=_("登出成功"))

    @extend_schema(
        summary="我的信息/查看他人信息",
        parameters=[
            OpenApiParameter(name="other_id", type=int, required=False, location=OpenApiParameter.QUERY, description="要查看的用户ID（不传则查看自己）"),
        ]
    )
    @action(detail=False, methods=["get"], url_path="profile")
    def profile(self, request):
        # 尝试获取当前登录用户 ID（可选）
        token = request.headers.get("token")
        current_customer_id = None
        if token:
            is_valid, customer_id = CustomTokenTool.verify_customer_token(token)
            if is_valid:
                current_customer_id = int(customer_id)

        # 判断是查看自己还是查看他人
        other_id = request.query_params.get('other_id')

        # 场景3：未登录且未提供 other_id，返回异常
        if not current_customer_id and not other_id:
            return ApiResponse(message=_("请先登录或提供用户ID"), code=401)

        # 确定目标用户
        if other_id:
            # 场景2：查询他人信息（无论是否登录）
            try:
                target_user = CustomerUser.objects.get(id=other_id)
            except CustomerUser.DoesNotExist:
                return ApiResponse(message=_("用户不存在"), code=404)
        else:
            # 场景1：已登录，查询自己的信息
            try:
                target_user = CustomerUser.objects.get(id=current_customer_id)
            except CustomerUser.DoesNotExist:
                return ApiResponse(message=_("用户不存在"), code=404)

        # 计算粉丝数和关注数
        from models.models import UserFollow
        followers_count = UserFollow.objects.filter(following_id=target_user.id).count()
        following_count = UserFollow.objects.filter(follower_id=target_user.id).count()

        # 判断当前用户是否关注了目标用户（仅当已登录且不是查看自己时）
        is_following = False
        if current_customer_id and current_customer_id != target_user.id:
            is_following = UserFollow.objects.filter(
                follower_id=current_customer_id,
                following_id=target_user.id
            ).exists()

        return ApiResponse(
            data={
                "customer_id": target_user.id,
                "email": target_user.email,
                "nickname": target_user.nickname,
                "gender": target_user.gender,
                "avatar_url": target_user.avatar_url,
                "badge": target_user.badge,
                "upload_count": target_user.upload_count,
                "collection_count": target_user.collection_count,
                "points": target_user.points,
                "level": target_user.level,
                "last_login": target_user.last_login,
                "created_at": target_user.created_at,
                "followers_count": followers_count,
                "following_count": following_count,
                "is_following": is_following,
            },
            message=_("获取成功"),
        )



    @extend_schema(
        summary="保存用户信息",
        request=CustomerProfileSerializer,
    )
    @action(detail=False, methods=["post"], url_path="update-profile")
    def update_profile(self, request):
        customer_id = request.customer_id
        try:
            user = CustomerUser.objects.get(id=customer_id)
        except CustomerUser.DoesNotExist:
            return ApiResponse(message=_("用户不存在"), code=404)
        ser = CustomerProfileSerializer(user, data=request.data, partial=True)
        if not ser.is_valid():
            return ApiResponse(data=ser.errors, message=_("参数校验失败"), code=400)

        ser.save()
        return ApiResponse(
            data={
                "customer_id": user.id,
                "nickname": user.nickname,
                "gender": user.gender,
                "avatar_url": user.avatar_url,
                "badge": user.badge,
            },
            message=_("保存成功"),
        )
