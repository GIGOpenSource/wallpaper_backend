#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：view.py
@Author  ：Liang
@Date    ：2026/4/16
@description : 网站配置接口（帮助与支持、关于、隐私政策等）
"""
from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from rest_framework.decorators import action
from django.utils.translation import get_language
from models.models import SiteConfig
from tool.base_views import BaseViewSet
from tool.permissions import IsAdmin
from tool.utils import ApiResponse, CustomPagination


class SiteConfigSerializer(serializers.ModelSerializer):
    """网站配置序列化器"""
    config_type_display = serializers.CharField(source='get_config_type_display', read_only=True)
    language_display = serializers.CharField(source='get_language_display', read_only=True)

    class Meta:
        model = SiteConfig
        fields = [
            'id', 'config_type', 'config_type_display',
            'config_value', 'title', 'content',
            'language', 'language_display',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BasicSettingsUpdateSerializer(serializers.Serializer):
    """网站基础设置更新序列化器"""
    site_name = serializers.CharField(max_length=100, required=False, help_text="站点名称")
    site_description = serializers.CharField(max_length=500, required=False, help_text="站点描述")
    icp_number = serializers.CharField(max_length=50, required=False, allow_blank=True, help_text="备案号")
    contact_email = serializers.EmailField(required=False, allow_blank=True, help_text="联系邮箱")
    enable_wallpaper_audit = serializers.BooleanField(required=False, help_text="开启壁纸审核")
    enable_comment_audit = serializers.BooleanField(required=False, help_text="开启评论审核")
    allow_user_register = serializers.BooleanField(required=False, help_text="允许用户注册")


class RobotsTxtUpdateSerializer(serializers.Serializer):
    """Robots.txt 更新序列化器"""
    content = serializers.CharField(required=True, help_text="Robots.txt 内容")


class SitemapUpdateSerializer(serializers.Serializer):
    """Sitemap 更新序列化器"""
    content = serializers.CharField(required=True, help_text="Sitemap.xml 内容")

class SitemapURLCreateUpdateSerializer(serializers.Serializer):
    """Sitemap URL 创建/更新序列化器"""
    content = serializers.URLField(required=True, help_text="URL 地址")
    title = serializers.CharField(max_length=200, required=False, allow_blank=True, help_text="标题")
    priority = serializers.IntegerField(required=False, default=0, min_value=0, max_value=100, help_text="优先级（0-100）")
    index_status = serializers.ChoiceField(
        choices=['pending', 'indexed', 'excluded'],
        required=False,
        default='pending',
        help_text="索引状态：pending=待索引，indexed=已索引，excluded=已排除"
    )
    changefreq = serializers.ChoiceField(
        choices=['always', 'hourly', 'daily', 'weekly', 'monthly', 'yearly', 'never'],
        required=False,
        default='weekly',
        help_text="更新频率"
    )
    is_active = serializers.BooleanField(required=False, default=True, help_text="是否启用")


@extend_schema(tags=["网站配置"])
@extend_schema_view(
    retrieve=extend_schema(
        summary="获取网站配置内容",
        description="根据配置类型获取富文本内容（帮助与支持、关于、隐私政策等）",
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
    ),
    update=extend_schema(
            summary="更新网站配置（管理员）",
            description="根据ID更新指定配置",
            request=SiteConfigSerializer,
            responses={
                200: SiteConfigSerializer,
                400: "参数错误",
                403: "无权限",
                404: "配置不存在"
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
    lookup_field = "type"

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsAdmin()]
        return []

    def get_queryset(self):
        if self.action in ["update", "partial_update", "destroy"]:
            return SiteConfig.objects.all()
        return SiteConfig.objects.filter(is_active=True)

    def get_object(self):
        # 备份，避免污染其他请求
        original_lookup_field = self.lookup_field
        original_lookup_url_kwarg = getattr(self, 'lookup_url_kwarg', None)
        try:
            if self.action in ['update', 'partial_update']:
                self.lookup_field = 'id'
                self.lookup_url_kwarg = 'type'
            elif self.action == 'retrieve':
                self.lookup_field = 'config_type'
                self.lookup_url_kwarg = 'type'
            return super().get_object()
        finally:
            # 还原，防止副作用
            self.lookup_field = original_lookup_field
            self.lookup_url_kwarg = original_lookup_url_kwarg

    def retrieve(self, request, *args, **kwargs):
        """获取单个配置内容"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return ApiResponse(data=serializer.data, message="获取成功")

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            request_data = request.data
            # 不允许更新的字段
            protected_fields = {"id", "created_at", "updated_at"}
            # 只更新模型真实字段（避免脏字段写入）
            model_fields = {f.name for f in SiteConfig._meta.fields}
            with transaction.atomic():
                for key, value in request_data.items():
                    if key in protected_fields:
                        continue
                    if key in model_fields:
                        setattr(instance, key, value)
                instance.save()
            serializer = self.get_serializer(instance)
            return ApiResponse(data=serializer.data, message="更新成功")
        except Exception as e:
            return ApiResponse(code=500, message=f"更新失败: {str(e)}")



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

    @extend_schema(
        summary="获取网站基础设置",
        description="获取网站的基础配置信息（无需登录）",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "site_name": {"type": "string", "description": "站点名称"},
                            "site_description": {"type": "string", "description": "站点描述"},
                            "icp_number": {"type": "string", "description": "备案号"},
                            "contact_email": {"type": "string", "description": "联系邮箱"},
                            "enable_wallpaper_audit": {"type": "boolean", "description": "开启壁纸审核"},
                            "enable_comment_audit": {"type": "boolean", "description": "开启评论审核"},
                            "allow_user_register": {"type": "boolean", "description": "允许用户注册"}
                        }
                    },
                    "message": {"type": "string", "example": "获取成功"}
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='basic-settings')
    def get_basic_settings(self, request):
        """获取网站基础设置"""
        try:
            config = SiteConfig.objects.get(
                config_type='basic_settings',
                is_active=True
            )
            return ApiResponse(data=config.config_value, message="获取成功")
        except SiteConfig.DoesNotExist:
            # 返回默认值
            default_settings = {
                'site_name': '',
                'site_description': '',
                'icp_number': '',
                'contact_email': '',
                'enable_wallpaper_audit': True,
                'enable_comment_audit': True,
                'allow_user_register': True
            }
            return ApiResponse(data=default_settings, message="获取成功（默认配置）")

    @extend_schema(
        summary="更新网站基础设置（管理员）",
        description="更新网站的基础配置信息，只需传递需要修改的字段",
        request=BasicSettingsUpdateSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "site_name": {"type": "string"},
                            "site_description": {"type": "string"},
                            "icp_number": {"type": "string"},
                            "contact_email": {"type": "string"},
                            "enable_wallpaper_audit": {"type": "boolean"},
                            "enable_comment_audit": {"type": "boolean"},
                            "allow_user_register": {"type": "boolean"}
                        }
                    },
                    "message": {"type": "string", "example": "更新成功"}
                }
            },
            400: "参数错误"
        }
    )
    @action(detail=False, methods=['post'], url_path='update-basic-settings', permission_classes=[IsAdmin])
    def update_basic_settings(self, request):
        """更新网站基础设置"""
        serializer = BasicSettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取或创建基础设置记录
        config, created = SiteConfig.objects.get_or_create(
            config_type='basic_settings',
            defaults={
                'title': '网站基础设置',
                'config_value': {},
                'is_active': True
            }
        )

        # 合并现有配置和新配置
        current_value = config.config_value or {}
        updated_value = {**current_value, **serializer.validated_data}
        # 更新配置值
        config.config_value = updated_value
        config.save()
        return ApiResponse(data=updated_value, message="更新成功")

    @extend_schema(
        summary="获取 Robots.txt 内容",
        description="获取网站的 Robots.txt 配置内容（无需登录）",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "Robots.txt 内容"}
                        }
                    },
                    "message": {"type": "string", "example": "获取成功"}
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='robots-txt')
    def get_robots_txt(self, request):
        """获取 Robots.txt 内容"""
        try:
            config = SiteConfig.objects.get(
                config_type='robots_txt',
                is_active=True
            )
            return ApiResponse(data={'content': config.content}, message="获取成功")
        except SiteConfig.DoesNotExist:
            # 返回默认值
            default_robots = """User-agent: *
Allow: /wallpaper/
Allow: /category/
Allow: /tag/
Disallow: /admin/
Disallow: /api/
Disallow: /private/
Disallow: /search?
Crawl-delay: 1

User-agent: Googlebot
Allow: /
Disallow: /admin/

User-agent: Googlebot-Image
Allow: /wallpaper/
Allow: /category/
Disallow: /admin/

Sitemap: https://example.com/sitemap.xml"""
            return ApiResponse(data={'content': default_robots}, message="获取成功（默认配置）")

    @extend_schema(
        summary="更新 Robots.txt 内容（管理员）",
        description="更新网站的 Robots.txt 配置内容",
        request=RobotsTxtUpdateSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "Robots.txt 内容"}
                        }
                    },
                    "message": {"type": "string", "example": "更新成功"}
                }
            },
            400: "参数错误"
        }
    )
    @action(detail=False, methods=['post'], url_path='update-robots-txt', permission_classes=[IsAdmin])
    def update_robots_txt(self, request):
        """更新 Robots.txt 内容"""
        serializer = RobotsTxtUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取或创建 Robots.txt 记录
        config, created = SiteConfig.objects.get_or_create(
            config_type='robots_txt',
            defaults={
                'title': 'Robots.txt 配置',
                'content': '',
                'config_value': {},
                'is_active': True
            }
        )

        # 更新 content 字段
        config.content = serializer.validated_data['content']
        config.save()
        return ApiResponse(data={'content': config.content}, message="更新成功")

    @extend_schema(
        summary="获取 Sitemap.xml 内容",
        description="获取网站的 Sitemap.xml 配置内容（无需登录）",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "Sitemap.xml 内容"}
                        }
                    },
                    "message": {"type": "string", "example": "获取成功"}
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='sitemap')
    def get_sitemap(self, request):
        """获取 Sitemap.xml 内容"""
        try:
            config = SiteConfig.objects.get(
                config_type='sitemap',
                is_active=True
            )
            return ApiResponse(data={'content': config.content}, message="获取成功")
        except SiteConfig.DoesNotExist:
            # 返回默认值
            default_sitemap = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <!-- 首页 -->
    <url>
        <loc>https://www.markwallpapers.com/markwallpapers/</loc>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
    <!-- 搜索页 -->
    <url>
        <loc>https://www.markwallpapers.com/markwallpapers/#/search</loc>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>
    <!-- 标签页 -->
    <url>
        <loc>https://www.markwallpapers.com/markwallpapers/#/tags</loc>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>
    <!-- 热门页 -->
    <url>
        <loc>https://www.markwallpapers.com/markwallpapers/#/trending</loc>
        <changefreq>daily</changefreq>
        <priority>0.85</priority>
    </url>
</urlset>"""
            return ApiResponse(data={'content': default_sitemap}, message="获取成功（默认配置）")

    @extend_schema(
        summary="更新 Sitemap.xml 内容（管理员）",
        description="更新网站的 Sitemap.xml 配置内容",
        request=SitemapUpdateSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "Sitemap.xml 内容"}
                        }
                    },
                    "message": {"type": "string", "example": "更新成功"}
                }
            },
            400: "参数错误"
        }
    )
    @action(detail=False, methods=['post'], url_path='update-sitemap', permission_classes=[IsAdmin])
    def update_sitemap(self, request):
        """更新 Sitemap.xml 内容"""
        serializer = SitemapUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取或创建 Sitemap 记录
        config, created = SiteConfig.objects.get_or_create(
            config_type='sitemap',
            defaults={
                'title': 'Sitemap 配置',
                'content': '',
                'config_value': {},
                'is_active': True
            }
        )

        # 更新 content 字段
        config.content = serializer.validated_data['content']
        config.save()
        return ApiResponse(data={'content': config.content}, message="更新成功")


# @extend_schema(tags=["Sitemap URL管理1"])
# @extend_schema_view(
#     list=extend_schema(
#         summary="获取 Sitemap URL 列表",
#         description="分页获取 Sitemap URL 列表，支持按索引状态和更新频率筛选",
#         parameters=[
#             OpenApiParameter(name="index_status", type=str, required=False, description="索引状态筛选 (pending/indexed/excluded)"),
#             OpenApiParameter(name="changefreq", type=str, required=False, description="更新频率筛选 (daily/weekly/monthly)"),
#             OpenApiParameter(name="is_active", type=bool, required=False, description="是否启用筛选"),
#             OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码"),
#             OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量"),
#         ],
#     ),
#     retrieve=extend_schema(summary="获取标签详情", responses={200: SitemapURLSerializer, 404: "标签不存在"}),
#     update=extend_schema(summary="更新标签(Admin)", request=SitemapURLSerializer),
#     partial_update=extend_schema(summary="部分更新标签(Admin)", request=SitemapURLSerializer),
#     destroy=extend_schema(summary="删除标签(Admin)", description="删除指定标签记录",
#                           responses={204: "删除成功", 404: "标签不存在"})
#
# )
    # permission_classes = [IsAdmin]
    #
    # def get_queryset(self):
    #     """获取查询集，支持筛选"""
    #     queryset = super().get_queryset()
    #
    #     # 索引状态筛选
    #     index_status = self.request.query_params.get('index_status')
    #     if index_status:
    #         # 使用 JSONField 查询
    #         queryset = queryset.filter(config_value__index_status=index_status)
    #
    #     # 更新频率筛选
    #     changefreq = self.request.query_params.get('changefreq')
    #     if changefreq:
    #         queryset = queryset.filter(config_value__changefreq=changefreq)
    #
    #     # 是否启用筛选
    #     is_active = self.request.query_params.get('is_active')
    #     if is_active is not None:
    #         queryset = queryset.filter(is_active=is_active.lower() == 'true')
    #
    #     # 按优先级排序
    #     return queryset.order_by('priority', '-created_at')
    #
    # @extend_schema(
    #     summary="创建 Sitemap URL",
    #     request=SitemapURLCreateUpdateSerializer,
    # )
    # def create(self, request, *args, **kwargs):
    #     """创建 Sitemap URL"""
    #     try:
    #         serializer = self.get_serializer(data=request.data)
    #         serializer.is_valid(raise_exception=True)
    #
    #         validated_data = serializer.validated_data
    #
    #         # 构建 config_value
    #         config_value = {
    #             'index_status': validated_data.get('index_status', 'pending'),
    #             'changefreq': validated_data.get('changefreq', 'weekly')
    #         }
    #
    #         # 创建记录
    #         config = SiteConfig.objects.create(
    #             config_type='sitemap_url',
    #             content=validated_data['content'],
    #             title=validated_data.get('title', ''),
    #             priority=validated_data.get('priority', 0),
    #             config_value=config_value,
    #             is_active=validated_data.get('is_active', True)
    #         )
    #
    #         # 返回结果
    #         result_serializer = SitemapURLSerializer(config)
    #         return ApiResponse(
    #             data=result_serializer.data,
    #             message="创建成功",
    #             code=201
    #         )
    #     except Exception as e:
    #         return ApiResponse(code=500, message=f"创建失败: {str(e)}")
    #
    # def list(self, request, *args, **kwargs):
    #     """获取 Sitemap URL 列表"""
    #     queryset = SiteConfig.objects.filter(config_type='sitemap_url')
    #
    #     index_status = request.query_params.get('index_status')
    #     if index_status:
    #         queryset = queryset.filter(config_value__index_status=index_status)
    #     changefreq = request.query_params.get('changefreq')
    #     if changefreq:
    #         queryset = queryset.filter(config_value__changefreq=changefreq)
    #
    #     is_active = request.query_params.get('is_active')
    #     if is_active is not None:
    #         queryset = queryset.filter(is_active=is_active.lower() == 'true')
    #
    #     url = request.query_params.get('url')
    #     if url:
    #         queryset = queryset.filter(content__icontains=url)
    #
    #     queryset = queryset.order_by('priority', '-created_at')
    #
    #     page = self.paginate_queryset(queryset)
    #     if page is not None:
    #         serializer = self.get_serializer(page, many=True)
    #         return self.get_paginated_response(serializer.data)
    #
    #     serializer = self.get_serializer(queryset, many=True)
    #     return ApiResponse(data=serializer.data, message="列表获取成功")
    #
    # @extend_schema(
    #     summary="更新 Sitemap URL",
    #     request=SitemapURLCreateUpdateSerializer,
    # )
    # def update(self, request, *args, **kwargs):
    #     """更新 Sitemap URL"""
    #     try:
    #         instance = self.get_object()
    #         serializer = self.get_serializer(instance, data=request.data)
    #         serializer.is_valid(raise_exception=True)
    #
    #         validated_data = serializer.validated_data
    #
    #         # 更新字段
    #         if 'content' in validated_data:
    #             instance.content = validated_data['content']
    #         if 'title' in validated_data:
    #             instance.title = validated_data.get('title', '')
    #         if 'priority' in validated_data:
    #             instance.priority = validated_data['priority']
    #         if 'is_active' in validated_data:
    #             instance.is_active = validated_data['is_active']
    #
    #         # 更新 config_value
    #         if 'index_status' in validated_data or 'changefreq' in validated_data:
    #             config_value = instance.config_value or {}
    #             if 'index_status' in validated_data:
    #                 config_value['index_status'] = validated_data['index_status']
    #             if 'changefreq' in validated_data:
    #                 config_value['changefreq'] = validated_data['changefreq']
    #             instance.config_value = config_value
    #
    #         instance.save()
    #
    #         result_serializer = SitemapURLSerializer(instance)
    #         return ApiResponse(data=result_serializer.data, message="更新成功")
    #     except Exception as e:
    #         return ApiResponse(code=500, message=f"更新失败: {str(e)}")
    #
    # def partial_update(self, request, *args, **kwargs):
    #     """部分更新 Sitemap URL"""
    #     return self.update(request, *args, **kwargs)
    #
    # def destroy(self, request, *args, **kwargs):
    #     """删除 Sitemap URL"""
    #     try:
    #         instance = self.get_object()
    #         instance.delete()
    #         return ApiResponse(message="删除成功")
    #     except Exception as e:
    #         return ApiResponse(code=500, message=f"删除失败: {str(e)}")
