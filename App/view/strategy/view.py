# -*- coding: UTF-8 -*-
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from rest_framework.decorators import action

from models.models import RecommendStrategy, Wallpapers
from tool.base_views import BaseViewSet
from tool.permissions import IsAdmin
from tool.utils import ApiResponse, CustomPagination


class RecommendStrategySerializer(serializers.ModelSerializer):
    """推荐策略序列化器"""

    class Meta:
        model = RecommendStrategy
        fields = [
            "id",
            "name",
            "priority",
            "content_limit",
            "strategy_type",
            "apply_area",
            "start_time",
            "end_time",
            "status",
            "stats_data",
            "wallpaper_ids",
            "platform",
            "remark",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_wallpaper_ids(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("wallpaper_ids 必须是数组")
        clean_ids = []
        for item in value:
            try:
                clean_ids.append(int(item))
            except (TypeError, ValueError):
                raise serializers.ValidationError("wallpaper_ids 中必须是整数ID")
        return clean_ids

    def validate(self, attrs):
        start_time = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end_time = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start_time and end_time and start_time > end_time:
            raise serializers.ValidationError("start_time 不能晚于 end_time")
        return attrs
@extend_schema(tags=["推荐策略"])
@extend_schema_view(
    list=extend_schema(
        summary="策略列表（管理员）",
        description="管理员查看策略列表，支持分页和多种筛选条件。当 strategy_type 为 home/hot 且未传其他管理参数时，返回推荐内容而非策略配置",
        parameters=[
            OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码"),
            OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量"),
            OpenApiParameter(name="strategy_type", type=str, required=False, description="策略类型：home/hot/banner"),
            OpenApiParameter(name="status", type=str, required=False, description="状态：draft/active/inactive"),
            OpenApiParameter(name="apply_area", type=str, required=False, description="应用区域"),
            OpenApiParameter(name="platform", type=str, required=False, description="平台：pc/phone/all"),
            OpenApiParameter(name="name", type=str, required=False, description="策略名称（模糊搜索）"),
            OpenApiParameter(name="filter_status", type=str, required=False, description="筛选状态：expired(已过期)/paused(已暂停)/active_now(生效中)")
        ],
    ),
)
# ... existing code ...

class RecommendStrategyViewSet(BaseViewSet):
    """
    推荐策略管理：
    - 支持 CRUD 配置首页/热门策略
    - 支持按策略计算推荐内容
    """

    queryset = RecommendStrategy.objects.all()
    serializer_class = RecommendStrategySerializer
    pagination_class = CustomPagination

    def get_permissions(self):
        if self.action in ["list"]:
            strategy_type = (self.request.query_params.get("strategy_type") or "").strip()
            if strategy_type in ["home", "hot"]:
                has_admin_params = any([
                    self.request.query_params.get("status"),
                    self.request.query_params.get("name"),
                    self.request.query_params.get("filter_status"),
                ])
                if not has_admin_params:
                    return []
        return [IsAdmin()]

    def get_queryset(self):
        from django.utils import timezone
        queryset = super().get_queryset()

        strategy_type = (self.request.query_params.get("strategy_type") or "").strip()
        status = (self.request.query_params.get("status") or "").strip()
        apply_area = (self.request.query_params.get("apply_area") or "").strip()
        name = (self.request.query_params.get("name") or "").strip()
        filter_status = (self.request.query_params.get("filter_status") or "").strip()

        if strategy_type in ["home", "hot"]:
            queryset = queryset.filter(strategy_type=strategy_type)
        if status in ["draft", "active", "inactive"]:
            queryset = queryset.filter(status=status)
        if apply_area:
            queryset = queryset.filter(apply_area=apply_area)
        if name:
            queryset = queryset.filter(name__icontains=name)
        now = timezone.now()
        if filter_status == "expired":
            queryset = queryset.filter(
                status="active",
                end_time__isnull=False,
                end_time__lt=now
            )
        elif filter_status == "paused":
            queryset = queryset.filter(status="inactive")
        elif filter_status == "active_now":
            active_list = []
            for item in queryset.filter(status="active"):
                if (item.start_time is None or item.start_time <= now) and \
                   (item.end_time is None or item.end_time >= now):
                    active_list.append(item.id)
            queryset = queryset.filter(id__in=active_list)

        return queryset.order_by("-priority", "-created_at")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="策略列表获取成功")



    @extend_schema(
        summary="获取策略统计数据",
        description="根据策略类型统计策略总数、生效中、已过期、内容总数",
        parameters=[
            OpenApiParameter(name="strategy_type", type=str, required=True, description="策略类型：home/hot"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "total_count": {"type": "integer", "description": "策略总数"},
                            "active_count": {"type": "integer", "description": "生效中数量"},
                            "expired_count": {"type": "integer", "description": "已过期数量"},
                            "total_content_count": {"type": "integer", "description": "内容总数（所有策略的壁纸数量之和）"}
                        }
                    },
                    "message": {"type": "string", "example": "获取成功"}
                }
            }
        }
    )
    @action(detail=False, methods=["get"], url_path="statistics")
    def statistics(self, request):
        """获取策略统计数据"""
        strategy_type = (request.query_params.get("strategy_type") or "").strip()
        if strategy_type not in ["home", "hot"]:
            return ApiResponse(code=400, message="strategy_type 必须是 home 或 hot")

        now = timezone.now()

        # 策略总数
        total_count = RecommendStrategy.objects.filter(strategy_type=strategy_type).count()

        # 生效中数量（status=active 且在有效期内）
        active_strategies = RecommendStrategy.objects.filter(
            strategy_type=strategy_type,
            status="active"
        )
        active_count = 0
        for s in active_strategies:
            if (s.start_time is None or s.start_time <= now) and (s.end_time is None or s.end_time >= now):
                active_count += 1
        # 已过期数量（status=active 但已过结束时间）
        expired_count = RecommendStrategy.objects.filter(
            strategy_type=strategy_type,
            status="active",
            end_time__isnull=False,
            end_time__lt=now
        ).count()
        # 内容总数（所有策略的壁纸数量之和）
        strategies = RecommendStrategy.objects.filter(strategy_type=strategy_type)
        total_content_count = sum(
            len(s.wallpaper_ids or []) for s in strategies
        )
        return ApiResponse(
            data={
                "total_count": total_count,
                "active_count": active_count,
                "expired_count": expired_count,
                "total_content_count": total_content_count,
            },
            message="获取成功"
        )