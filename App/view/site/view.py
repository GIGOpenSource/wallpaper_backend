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
        description="获取网站的 Robots.txt 配置内容（无需登录）。添加参数 ?raw=1 可返回纯文本格式",
        parameters=[
            OpenApiParameter(name="raw", type=int, required=False, description="设置为 1 时返回纯文本格式"),
        ],
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
        from django.http import HttpResponse

        # 如果请求 raw=1，则返回纯文本格式供 Nginx 代理
        if request.query_params.get('raw') == '1':
            try:
                config = SiteConfig.objects.get(config_type='robots_txt', is_active=True)
                return HttpResponse(config.content, content_type='text/plain')
            except SiteConfig.DoesNotExist:
                return HttpResponse("User-agent: *\nDisallow: /", content_type='text/plain')

        # 默认返回 JSON 格式
        try:
            config = SiteConfig.objects.get(config_type='robots_txt', is_active=True)
            return ApiResponse(data={'content': config.content}, message="获取成功")
        except SiteConfig.DoesNotExist:
            default_robots = """User-agent: *\nDisallow: /"""
            return ApiResponse(data={'content': default_robots}, message="使用默认配置")

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