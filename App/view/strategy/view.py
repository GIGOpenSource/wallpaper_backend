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
        parameters=[
            OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码"),
            OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量"),
            OpenApiParameter(name="strategy_type", type=str, required=False, description="策略类型：home/hot"),
            OpenApiParameter(name="status", type=str, required=False, description="状态：draft/active/inactive"),
            OpenApiParameter(name="apply_area", type=str, required=False, description="应用区域"),
        ],
    ),
    retrieve=extend_schema(summary="策略详情"),
    create=extend_schema(summary="创建策略"),
    update=extend_schema(summary="更新策略"),
    partial_update=extend_schema(summary="部分更新策略"),
    destroy=extend_schema(summary="删除策略"),
)
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
        # 推荐结果可公开读取，其余管理动作仅管理员
        if self.action in ["recommend"]:
            return []
        return [IsAdmin()]

    def get_queryset(self):
        queryset = super().get_queryset()
        strategy_type = (self.request.query_params.get("strategy_type") or "").strip()
        status = (self.request.query_params.get("status") or "").strip()
        apply_area = (self.request.query_params.get("apply_area") or "").strip()
        if strategy_type in ["home", "hot"]:
            queryset = queryset.filter(strategy_type=strategy_type)
        if status in ["draft", "active", "inactive"]:
            queryset = queryset.filter(status=status)
        if apply_area:
            queryset = queryset.filter(apply_area=apply_area)
        return queryset

    @extend_schema(
        summary="获取推荐内容（首页/热门）",
        parameters=[
            OpenApiParameter(name="strategy_type", type=str, required=True, description="策略类型：home/hot"),
            OpenApiParameter(name="apply_area", type=str, required=False, description="应用区域，默认 global"),
        ],
    )
    @action(detail=False, methods=["get"], url_path="recommend")
    def recommend(self, request):
        strategy_type = (request.query_params.get("strategy_type") or "").strip()
        apply_area = (request.query_params.get("apply_area") or "global").strip()
        if strategy_type not in ["home", "hot"]:
            return ApiResponse(code=400, message="strategy_type 必须是 home 或 hot")

        now = timezone.now()
        strategies = RecommendStrategy.objects.filter(
            strategy_type=strategy_type,
            apply_area=apply_area,
            status="active",
        ).order_by("-priority", "-created_at")

        matched_strategy = None
        for item in strategies:
            if item.start_time and now < item.start_time:
                continue
            if item.end_time and now > item.end_time:
                continue
            matched_strategy = item
            break

        if not matched_strategy:
            return ApiResponse(
                data={"strategy": None, "results": []},
                message="未命中生效策略",
            )

        wallpaper_ids = matched_strategy.wallpaper_ids or []
        if not wallpaper_ids:
            return ApiResponse(
                data={"strategy": RecommendStrategySerializer(matched_strategy).data, "results": []},
                message="策略已命中，但未配置壁纸内容",
            )

        wallpaper_map = Wallpapers.objects.filter(id__in=wallpaper_ids).in_bulk()
        ordered_wallpapers = [wallpaper_map[w_id] for w_id in wallpaper_ids if w_id in wallpaper_map]
        if matched_strategy.content_limit and matched_strategy.content_limit > 0:
            ordered_wallpapers = ordered_wallpapers[: matched_strategy.content_limit]

        results = [
            {
                "id": wp.id,
                "name": wp.name,
                "thumb_url": wp.thumb_url,
                "url": wp.url,
                "width": wp.width,
                "height": wp.height,
                "download_count": wp.download_count,
                "view_count": wp.view_count,
                "hot_score": wp.hot_score,
            }
            for wp in ordered_wallpapers
        ]

        return ApiResponse(
            data={
                "strategy": RecommendStrategySerializer(matched_strategy).data,
                "results": results,
            },
            message="推荐内容获取成功",
        )
