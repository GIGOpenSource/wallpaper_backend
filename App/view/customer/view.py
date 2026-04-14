# -*- coding: UTF-8 -*-
from django.db import IntegrityError
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import serializers, viewsets
from rest_framework.decorators import action

from models.models import CustomerUser
from tool.password_hasher import verify_password
from tool.permissions import IsCustomerTokenValid
from tool.token_tools import CustomTokenTool
from tool.utils import ApiResponse
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

class CustomerProfileSerializer(serializers.ModelSerializer):
    """用户信息序列化器"""
    class Meta:
        model = CustomerUser
        fields = ("id", "email", "nickname", "gender", "avatar_url", "badge", "points", "level")
        read_only_fields = ("id", "email", "points", "level")



@extend_schema(tags=["客户账户"])
@extend_schema_view()
class CustomerUserViewSet(viewsets.ViewSet):
    permission_classes_by_action = {
        "register": [],
        "login": [],
        "logout": [IsCustomerTokenValid],
        "profile": [IsCustomerTokenValid],
        "update_profile": [IsCustomerTokenValid],
    }

    def get_permissions(self):
        return [p() for p in self.permission_classes_by_action.get(self.action, [])]

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
        token = CustomTokenTool.generate_customer_token(user.id)
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
        try:
            user = CustomerUser.objects.get(email=email)
        except CustomerUser.DoesNotExist:
            return ApiResponse(message=_("邮箱未注册"), code=400)
        if not verify_password(password, user.password):
            return ApiResponse(message=_("邮箱或密码错误"), code=400)
        user.last_login = timezone.now()
        user.save(update_fields=["last_login", "updated_at"])
        token = CustomTokenTool.generate_customer_token(user.id)
        return ApiResponse(
            data={"token": token, "customer_id": user.id, "email": user.email},
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

    @extend_schema(summary="我的信息")
    @action(detail=False, methods=["get"], url_path="profile")
    def profile(self, request):
        customer_id = request.customer_id
        try:
            user = CustomerUser.objects.get(id=customer_id)
        except CustomerUser.DoesNotExist:
            return ApiResponse(message=_("用户不存在"), code=404)

        return ApiResponse(
            data={
                "customer_id": user.id,
                "email": user.email,
                "nickname": user.nickname,
                "gender": user.gender,
                "avatar_url": user.avatar_url,
                "badge": user.badge,
                "upload_count": user.upload_count,
                "collection_count": user.collection_count,
                "points": user.points,
                "level": user.level,
                "last_login": user.last_login,
                "created_at": user.created_at,
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
