#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：view.py
@Author  ：Liang
@Date    ：2026/4/16
@description : 网站配置接口（基础设置 + 多语言页面内容）
"""
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from rest_framework.decorators import action

from models.models import SiteConfig
from tool.base_views import BaseViewSet
from tool.permissions import IsAdmin
from tool.utils import ApiResponse
from django.utils.translation import get_language


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


class PageContentUpdateSerializer(serializers.Serializer):
    """页面内容更新序列化器"""
    title = serializers.CharField(max_length=200, required=True, help_text="标题")
    content = serializers.CharField(required=True, help_text="富文本内容（HTML）")


@extend_schema(tags=["网站配置"])
@extend_schema_view(
    list=extend_schema(
        summary="获取所有启用的配置列表",
        description="返回所有启用状态的配置列表（管理员可见全部，普通用户仅见页面内容）",
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
                                "language": {"type": "string"},
                                "language_display": {"type": "string"},
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
    - 公开接口：获取页面内容、获取基础设置
    - 管理员接口：更新基础设置、更新页面内容
    """
    queryset = SiteConfig.objects.all()
    serializer_class = SiteConfigSerializer
    permission_classes = []
    authentication_classes = []

    def get_queryset(self):
        """只返回启用的配置"""
        return SiteConfig.objects.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        """获取所有启用的配置列表"""
        queryset = self.get_queryset()

        # 如果不是管理员，只返回页面内容
        is_admin = False
        if hasattr(request, 'user') and request.user.is_authenticated:
            from models.models import User
            if isinstance(request.user, User) and request.user.role in ['admin', 'operator', 'super_admin']:
                is_admin = True

        if not is_admin:
            # 普通用户只看页面内容
            page_types = ['privacy_policy', 'terms_of_service', 'about_us', 'help_center']
            queryset = queryset.filter(config_type__in=page_types)

        serializer = self.get_serializer(queryset, many=True)

        # 只返回基本信息
        data = [
            {
                'id': item['id'],
                'config_type': item['config_type'],
                'config_type_display': item['config_type_display'],
                'language': item['language'],
                'language_display': item['language_display'],
                'title': item['title'],
            }
            for item in serializer.data
        ]

        return ApiResponse(data=data, message="获取成功")

    @extend_schema(
        summary="获取页面内容",
        description="根据配置类型和语言获取页面内容（隐私政策、用户协议等）。如果不传语言，自动使用当前请求的语言，默认为简体中文。",
        parameters=[
            OpenApiParameter(
                name="type",
                type=str,
                required=True,
                description="配置类型：privacy_policy/terms_of_service/about_us/help_center",
                enum=["privacy_policy", "terms_of_service", "about_us", "help_center"]
            ),
            OpenApiParameter(
                name="language",
                type=str,
                required=False,
                description="语言代码，不传则使用当前请求语言，默认 zh-hans",
                enum=["es", "en", "pt", "ja", "ko", "zh-hans", "zh-hant", "de", "fr"]
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "config_type": {"type": "string"},
                            "config_type_display": {"type": "string"},
                            "language": {"type": "string"},
                            "language_display": {"type": "string"},
                            "title": {"type": "string"},
                            "content": {"type": "string"},
                        }
                    },
                    "message": {"type": "string", "example": "获取成功"}
                }
            },
            404: "配置不存在"
        }
    )
    @action(detail=False, methods=['get'], url_path='page-content')
    def get_page_content(self, request):
        """获取页面内容"""
        config_type = request.query_params.get('type')
        language = request.query_params.get('language')

        # 验证配置类型
        valid_types = dict(SiteConfig.CONFIG_TYPE_CHOICES).keys()
        page_types = ['privacy_policy', 'terms_of_service', 'about_us', 'help_center']
        if config_type not in page_types:
            return ApiResponse(
                code=400,
                message=f"无效的页面类型，可选值：{', '.join(page_types)}"
            )

        # 如果没有传语言，使用当前请求的语言
        if not language:
            language = get_language() or 'zh-hans'

        try:
            config = SiteConfig.objects.get(
                config_type=config_type,
                language=language,
                is_active=True
            )
        except SiteConfig.DoesNotExist:
            # 如果找不到指定语言，尝试简体中文
            if language != 'zh-hans':
                try:
                    config = SiteConfig.objects.get(
                        config_type=config_type,
                        language='zh-hans',
                        is_active=True
                    )
                except SiteConfig.DoesNotExist:
                    return ApiResponse(code=404, message="配置不存在或已禁用")
            else:
                return ApiResponse(code=404, message="配置不存在或已禁用")

        data = {
            'config_type': config.config_type,
            'config_type_display': config.get_config_type_display(),
            'language': config.language,
            'language_display': config.get_language_display(),
            'title': config.title,
            'content': config.content
        }

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
        summary="更新页面内容（管理员）",
        description="更新指定语言和类型的页面内容（隐私政策、用户协议等）",
        request=PageContentUpdateSerializer,
        parameters=[
            OpenApiParameter(
                name="type",
                type=str,
                required=True,
                description="配置类型：privacy_policy/terms_of_service/about_us/help_center",
                enum=["privacy_policy", "terms_of_service", "about_us", "help_center"]
            ),
            OpenApiParameter(
                name="language",
                type=str,
                required=False,
                description="语言代码，不传则使用当前请求语言，默认 zh-hans",
                enum=["es", "en", "pt", "ja", "ko", "zh-hans", "zh-hant", "de", "fr"]
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "config_type": {"type": "string"},
                            "language": {"type": "string"},
                            "title": {"type": "string"},
                            "content": {"type": "string"}
                        }
                    },
                    "message": {"type": "string", "example": "更新成功"}
                }
            },
            400: "参数错误"
        }
    )
    @action(detail=False, methods=['post'], url_path='update-page-content', permission_classes=[IsAdmin])
    def update_page_content(self, request):
        """更新页面内容"""
        config_type = request.query_params.get('type')
        language = request.query_params.get('language')

        # 验证配置类型
        valid_types = dict(SiteConfig.CONFIG_TYPE_CHOICES).keys()
        page_types = ['privacy_policy', 'terms_of_service', 'about_us', 'help_center']
        if config_type not in page_types:
            return ApiResponse(
                code=400,
                message=f"无效的页面类型，可选值：{', '.join(page_types)}"
            )

        # 如果没有传语言，使用当前请求的语言
        if not language:
            language = get_language() or 'zh-hans'

        # 验证语言
        valid_languages = dict(SiteConfig.LANGUAGE_CHOICES).keys()
        if language not in valid_languages:
            return ApiResponse(
                code=400,
                message=f"无效的语言代码，可选值：{', '.join(valid_languages)}"
            )

        serializer = PageContentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取或创建页面内容记录
        config, created = SiteConfig.objects.update_or_create(
            config_type=config_type,
            language=language,
            defaults={
                'title': serializer.validated_data['title'],
                'content': serializer.validated_data['content'],
                'config_value': {},
                'is_active': True
            }
        )

        # 如果不是新建，更新字段
        if not created:
            config.title = serializer.validated_data['title']
            config.content = serializer.validated_data['content']
            config.save()

        response_data = {
            'config_type': config_type,
            'language': language,
            'title': config.title,
            'content': config.content
        }

        return ApiResponse(data=response_data, message="更新成功")
