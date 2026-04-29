#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：view.py
@Author  ：Liang
@Date    ：2026/4/28
@description : 页面TDK管理
"""
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from models.models import PageTDK
from tool.base_views import BaseViewSet
from tool.permissions import IsAdmin
from tool.utils import ApiResponse, CustomPagination


class PageTDKSerializer(serializers.ModelSerializer):
    """页面TDK序列化器"""
    page_type_display = serializers.CharField(source='get_page_type_display', read_only=True)
    url_content = serializers.SerializerMethodField(help_text="关联的URL地址")

    class Meta:
        model = PageTDK
        fields = [
            'id', 'page_type', 'page_type_display', 'title', 'description',
            'keywords', 'url', 'url_content', 'applied_count',
            'is_template', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_url_content(self, obj):
        """获取关联的URL地址"""
        if obj.url:
            return obj.url.content
        return None


@extend_schema(tags=["页面TDK管理"])
@extend_schema_view(
    list=extend_schema(
        summary="获取页面TDK列表",
        description="支持按页面类型、是否模板、是否启用筛选，"
                    "page_type:category,tag,detail,search,article,custom",
        parameters=[
            OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码"),
            OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量"),
            OpenApiParameter(name="is_template", type=str, required=False, description="是否模板"),
        ],
    ),
    retrieve=extend_schema(summary="获取页面TDK详情"),
    create=extend_schema(summary="创建页面TDK"),
    update=extend_schema(summary="更新页面TDK"),
    partial_update=extend_schema(summary="部分更新页面TDK"),
    destroy=extend_schema(summary="删除页面TDK"),
)
class PageTDKViewSet(BaseViewSet):
    """
    页面TDK管理 ViewSet
    管理页面的Title、Description、Keywords配置
    """
    queryset = PageTDK.objects.all()
    serializer_class = PageTDKSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAdmin]

    def get_queryset(self):
        queryset = super().get_queryset()
        # 按页面类型筛选
        page_type = self.request.query_params.get('page_type')
        if page_type:
            queryset = queryset.filter(page_type=page_type)

        # 按是否模板筛选
        is_template = self.request.query_params.get('is_template')
        if is_template is not None:
            queryset = queryset.filter(is_template=is_template.lower() == 'true')

        # 按是否启用筛选
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset.order_by('-updated_at')

    def list(self, request, *args, **kwargs):
        """获取页面TDK列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="列表获取成功")

    def retrieve(self, request, *args, **kwargs):
        """获取页面TDK详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return ApiResponse(data=serializer.data, message="获取成功")

    def create(self, request, *args, **kwargs):
        """创建页面TDK"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        result_serializer = self.get_serializer(instance)
        return ApiResponse(data=result_serializer.data, message="创建成功", code=201)

    def update(self, request, *args, **kwargs):
        """更新页面TDK"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        result_serializer = self.get_serializer(instance)
        return ApiResponse(data=result_serializer.data, message="更新成功")

    def partial_update(self, request, *args, **kwargs):
        """部分更新页面TDK"""
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """删除页面TDK"""
        instance = self.get_object()
        instance.delete()
        return ApiResponse(message="删除成功")
