# -*- coding: UTF-8 -*-
from models.models import CustomerUser, Medal, UserMedal
from models.serializers import MedalSerializer, UserMedalSerializer

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import get_authorization_header
from tool.utils import ApiResponse, CustomPagination
from drf_spectacular.utils import extend_schema_view, extend_schema

# 用你项目已有的redis对象，自行import
# from 你的redis模块 import redis_client

from tool.base_views import BaseViewSet
from tool.utils import ApiResponse

class CustomerIsAuthenticated(BasePermission):
    """针对CustomerUser模型的登录校验权限"""
    def has_permission(self, request, view):
        return request.user is not None


@extend_schema_view(
    list=extend_schema(
        summary="获取勋章模板列表",
        description="获取全部勋章模板列表",
        tags=["(Admin)徽章管理"],
    ),
    retrieve=extend_schema(
        summary="获取勋章模板详情",
        description="根据ID获取单条勋章模板详情",
        tags=["(Admin)徽章管理"],
    ),
    create=extend_schema(
        summary="创建勋章模板",
        description="新增勋章模板",
        tags=["(Admin)徽章管理"],
    ),
    update=extend_schema(
        summary="全量更新勋章模板",
        description="全量修改勋章模板信息",
        tags=["(Admin)徽章管理"],
    ),
    partial_update=extend_schema(
        summary="部分更新勋章模板",
        description="局部修改勋章模板信息",
        tags=["(Admin)徽章管理"],
    ),
    destroy=extend_schema(
        summary="删除勋章模板",
        description="删除指定勋章模板",
        tags=["(Admin)徽章管理"],
    ),
    grant=extend_schema(
        summary="发放勋章给用户",
        description="给指定用户发放指定勋章，请求体传入customer_id、medal_id",
        tags=["(Admin)徽章管理"],
    )
)
class MedalAdminViewSet(BaseViewSet):
    """
    管理员：勋章模板CRUD
    管理员新增、修改、删除勋章模板，支持给用户下发勋章
    """
    queryset = Medal.objects.all()
    serializer_class = MedalSerializer
    permission_classes = [CustomerIsAuthenticated]

    @action(methods=["post"], detail=False)
    def grant(self, request):
        customer_id = request.data.get("customer_id")
        medal_id = request.data.get("medal_id")

        if not customer_id or not medal_id:
            return ApiResponse(message="参数缺失，需要customer_id、medal_id", code=400)

        try:
            customer = CustomerUser.objects.get(id=customer_id)
            medal = Medal.objects.get(id=medal_id)
        except CustomerUser.DoesNotExist:
            return ApiResponse(message="用户不存在", code=400)
        except Medal.DoesNotExist:
            return ApiResponse(message="勋章不存在", code=400)

        exists = UserMedal.objects.filter(customer=customer, medal=medal).exists()
        if exists:
            return ApiResponse(message="该用户已经拥有此勋章", code=400)

        obj = UserMedal.objects.create(customer=customer, medal=medal)
        ser = UserMedalSerializer(obj)
        return ApiResponse(
            data=ser.data,
            message="发放成功",
            code=200
        )


@extend_schema_view(
    list=extend_schema(
        summary="公开勋章列表",
        description="所有人可访问，获取全部可用勋章模板，只读",
        tags=["(Client)徽章列表"],
    ),
    retrieve=extend_schema(
        summary="公开勋章详情",
        description="获取单个勋章模板详情，无需登录",
        tags=["(Client)徽章列表"],
    )
)
class MedalViewSet(viewsets.ReadOnlyModelViewSet):
    """
    客户端公开勋章接口
    勋章模板公开只读，所有人可访问
    """
    queryset = Medal.objects.all()
    serializer_class = MedalSerializer
    permission_classes = [AllowAny]


@extend_schema_view(
    list=extend_schema(
        summary="我的已获得勋章",
        description="登录用户查询自己已经拥有的勋章集合，仅返回当前登录用户数据",
        tags=["(Client)我的徽章"],
    ),
    retrieve=extend_schema(
        summary="我的单条勋章详情",
        description="查看自己获得的某一枚勋章详情",
        tags=["(Client)我的徽章"],
    )
)
class UserMedalViewSet(viewsets.ReadOnlyModelViewSet):
    """
    客户端：用户已获得勋章
    需要登录，只能查看自己拥有的勋章
    """
    serializer_class = UserMedalSerializer
    permission_classes = [CustomerIsAuthenticated]
    pagination_class = CustomPagination

    def get_queryset(self):
        user = self.request.user
        print(f"====当前登录customer id:{user.id}====")
        if not isinstance(user, CustomerUser):
            return UserMedal.objects.none()
        return UserMedal.objects.filter(customer=user).select_related("medal")