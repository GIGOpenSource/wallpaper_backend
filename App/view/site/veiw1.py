#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：view.py
@Author  ：Liang
@Date    ：2026/4/16
@description : 网站配置接口（帮助与支持、关于、隐私政策等）
"""
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import serializers
from rest_framework.decorators import action

from models.models import SiteConfig
from tool.base_views import BaseViewSet
from tool.utils import ApiResponse


class SiteConfigSerializer(serializers.ModelSerializer):
    """网站配置序列化器"""
    config_type_display = serializers.CharField(source='get_config_type_display', read_only=True)

    class Meta:
        model = SiteConfig
        fields = ['id', 'config_type', 'config_type_display', 'title', 'content', 'is_active', 'created_at',
                  'updated_at']
        read_only_fields = fields


@extend_schema(tags=["网站配置"])
@extend_schema_view(
    retrieve=extend_schema(
        summary="获取网站配置内容",
        description="根据配置类型获取富文本内容（帮助与支持、关于、隐私政策等）",
        parameters=[
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "config_type": {"type": "string", "description": "配置类型"},
                            "config_type_display": {"type": "string", "description": "配置类型显示名称"},
                            "title": {"type": "string", "description": "标题"},
                            "content": {"type": "string", "description": "富文本内容（HTML）"},
                        }
                    },
                    "message": {"type": "string", "example": "获取成功"}
                }
            },
            404: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 404},
                    "message": {"type": "string", "example": "配置不存在"}
                }
            }
        }
    ),
    list=extend_schema(
        summary="获取所有启用的网站配置",
        description="返回所有启用状态的配置列表（不包含具体内容，仅元数据）",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "config_type": {"type": "string"},
                                "config_type_display": {"type": "string"},
                                "title": {"type": "string"},
                            }
                        }
                    },
                    "message": {"type": "string", "example": "获取成功"}
                }
            }
        }
    )
)
class SiteConfigViewSet(BaseViewSet):
    """
    网站配置 ViewSet
    提供网站配置内容的查询功能（无需登录）
    """
    queryset = SiteConfig.objects.all()
    serializer_class = SiteConfigSerializer
    permission_classes = []
    authentication_classes = []
    lookup_field = 'type'  # 告诉 DRF 和 Swagger 路径参数名为 'type'

    def get_queryset(self):
        """只返回启用的配置"""
        return SiteConfig.objects.filter(is_active=True)

    # 移除此处的 @extend_schema，使用类级别的 @extend_schema_view 统一管理，或者只保留 summary
    def retrieve(self, request, *args, **kwargs):
        """获取单个配置内容"""
        config_type = kwargs.get('type')  # 从 kwargs 获取 'type'

        # 验证配置类型是否有效
        valid_types = dict(SiteConfig.CONFIG_TYPE_CHOICES).keys()
        if config_type not in valid_types:
            return ApiResponse(
                code=400,
                message=f"无效的配置类型，可选值：{', '.join(valid_types)}"
            )
        try:
            config = SiteConfig.objects.get(config_type=config_type, is_active=True)
        except SiteConfig.DoesNotExist:
            return ApiResponse(code=404, message="配置不存在或已禁用")

        serializer = self.get_serializer(config)
        return ApiResponse(data=serializer.data, message="获取成功")

    def list(self, request, *args, **kwargs):
        """获取所有启用的配置列表"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        # 只返回基本信息，不返回详细内容
        data = [
            {
                'id': item['id'],
                'config_type': item['config_type'],
                'config_type_display': item['config_type_display'],
                'title': item['title'],
            }
            for item in serializer.data
        ]

        return ApiResponse(data=data, message="获取成功")
