#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：view.py
@Author  ：Liang
@Date    ：2026/4/16
@description : 网站配置接口（帮助与支持、关于、隐私政策等）
"""
import os
import warnings
import requests
from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from rest_framework.decorators import action
from django.utils.translation import get_language
from models.models import SiteConfig
from tool.base_views import BaseViewSet
from tool.permissions import IsAdmin
from tool.utils import ApiResponse, CustomPagination

# 禁用 SSL 警告
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


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


class RobotsRuleAddSerializer(serializers.Serializer):
    """Robots 规则添加序列化器"""
    user_agent = serializers.CharField(required=True, max_length=100, help_text="User-agent，例如: * 或 Googlebot")
    allow_paths = serializers.ListField(
        child=serializers.CharField(max_length=500),
        required=False,
        default=list,
        help_text="Allow 路径列表，每行一个路径，例如: [/wallpaper/, /category/]"
    )
    disallow_paths = serializers.ListField(
        child=serializers.CharField(max_length=500),
        required=False,
        default=list,
        help_text="Disallow 路径列表，每行一个路径，例如: [/admin/, /api/]"
    )
    crawl_delay = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=10,
        help_text="抓取延迟（秒），数据库存1-10，实际显示0.1~1"
    )
    sitemap = serializers.URLField(
        required=False,
        allow_blank=True,
        help_text="Sitemap 地址"
    )


class RobotsTestSerializer(serializers.Serializer):
    """Robots 规则测试序列化器"""
    user_agent = serializers.CharField(
        required=True,
        help_text="User-agent 类型，支持: Googlebot, Googlebot-Image, Bingbot, Baiduspider, 或 * 表示全部"
    )
    url_path = serializers.CharField(
        required=True,
        max_length=500,
        help_text="URL 路径，例如: /wallpaper/"
    )


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

    @extend_schema(
        summary="获取 Robots.txt 统计信息",
        description="解析 Robots.txt 内容，返回规则数量、Allow路径数量、Disallow数量、最后更新时间等统计信息",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "total_rules": {"type": "integer", "description": "总规则数"},
                            "allow_count": {"type": "integer", "description": "Allow路径数量"},
                            "disallow_count": {"type": "integer", "description": "Disallow数量"},
                            "sitemap_count": {"type": "integer", "description": "Sitemap数量"},
                            "user_agents": {"type": "array", "items": {"type": "string"}, "description": "User-agent列表"},
                            "last_updated": {"type": "string", "description": "最后更新时间"}
                        }
                    },
                    "message": {"type": "string", "example": "获取成功"}
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='robots-statistics')
    def robots_statistics(self, request):
        """获取 Robots.txt 统计信息"""
        try:
            config = SiteConfig.objects.get(config_type='robots_txt', is_active=True)
            content = config.content
            last_updated = config.updated_at
        except SiteConfig.DoesNotExist:
            content = "User-agent: *\nDisallow: /"
            last_updated = None

        # 解析 Robots.txt 内容
        lines = content.split('\n')
        allow_count = 0
        disallow_count = 0
        sitemap_count = 0
        user_agents = []
        total_rules = 0

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # 统计 Allow
            if line.lower().startswith('allow:'):
                allow_count += 1
                total_rules += 1
            # 统计 Disallow
            elif line.lower().startswith('disallow:'):
                disallow_count += 1
                total_rules += 1
            # 统计 Sitemap
            elif line.lower().startswith('sitemap:'):
                sitemap_count += 1
            # 统计 User-agent
            elif line.lower().startswith('user-agent:'):
                agent = line.split(':', 1)[1].strip()
                if agent and agent not in user_agents:
                    user_agents.append(agent)

        return ApiResponse(
            data={
                'total_rules': total_rules,
                'allow_count': allow_count,
                'disallow_count': disallow_count,
                'sitemap_count': sitemap_count,
                'user_agents': user_agents,
                'user_agents_count':len(user_agents),
                'last_updated': last_updated
            },
            message="获取成功"
        )

    @extend_schema(
        summary="获取 Robots.txt 规则列表（可视化）",
        description="将 Robots.txt 内容按 User-agent 拆分成多条规则，返回序号、User-agent、Allow、Disallow、Crawl-delay",
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
                                "id": {"type": "integer", "description": "规则序号（用于删除）"},
                                "user_agent": {"type": "string", "description": "User-agent"},
                                "allow": {"type": "array", "items": {"type": "string"}, "description": "Allow 路径列表"},
                                "disallow": {"type": "array", "items": {"type": "string"}, "description": "Disallow 路径列表"},
                                "crawl_delay": {"type": "number", "description": "抓取延迟（秒），显示为0.1~1"},
                                "sitemap": {"type": "string", "description": "Sitemap 地址"}
                            }
                        }
                    },
                    "message": {"type": "string", "example": "获取成功"}
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='robots-rules')
    def get_robots_rules(self, request):
        """获取 Robots.txt 规则列表（可视化）"""
        try:
            config = SiteConfig.objects.get(config_type='robots_txt', is_active=True)
            content = config.content
        except SiteConfig.DoesNotExist:
            content = "User-agent: *\nDisallow: /"

        # 解析 Robots.txt 内容
        rules = self._parse_robots_content(content)
        return ApiResponse(data=rules, message="获取成功")

    def _parse_robots_content(self, content):
        """解析 Robots.txt 内容为规则列表"""
        lines = content.split('\n')
        rules = []
        current_rule = None
        rule_id = 0
        sitemaps = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # 处理 Sitemap（全局）
            if line.lower().startswith('sitemap:'):
                sitemap_url = line.split(':', 1)[1].strip()
                sitemaps.append(sitemap_url)
                continue

            # 处理 User-agent（新规则开始）
            if line.lower().startswith('user-agent:'):
                # 保存上一个规则
                if current_rule is not None:
                    rules.append(current_rule)
                
                rule_id += 1
                user_agent = line.split(':', 1)[1].strip()
                current_rule = {
                    'id': rule_id,
                    'user_agent': user_agent,
                    'allow': [],
                    'disallow': [],
                    'crawl_delay': None,
                    'sitemap': None
                }
                continue

            # 处理 Allow
            if line.lower().startswith('allow:') and current_rule:
                path = line.split(':', 1)[1].strip()
                current_rule['allow'].append(path)
                continue

            # 处理 Disallow
            if line.lower().startswith('disallow:') and current_rule:
                path = line.split(':', 1)[1].strip()
                current_rule['disallow'].append(path)
                continue

            # 处理 Crawl-delay
            if line.lower().startswith('crawl-delay:') and current_rule:
                delay_value = int(line.split(':', 1)[1].strip())
                # 数据库存1-10，实际显示0.1~1
                current_rule['crawl_delay'] = delay_value / 10.0
                continue

        # 保存最后一个规则
        if current_rule is not None:
            rules.append(current_rule)

        # 如果有 sitemap，添加到第一个规则或单独处理
        if sitemaps:
            if rules:
                rules[0]['sitemap'] = sitemaps[0] if len(sitemaps) == 1 else ', '.join(sitemaps)
            else:
                # 如果没有规则，创建一个只包含 sitemap 的规则
                rules.append({
                    'id': rule_id + 1,
                    'user_agent': '*',
                    'allow': [],
                    'disallow': [],
                    'crawl_delay': None,
                    'sitemap': ', '.join(sitemaps)
                })

        return rules

    @extend_schema(
        summary="删除 Robots.txt 规则",
        description="根据规则序号删除指定的 User-agent 规则",
        parameters=[
            OpenApiParameter(name="rule_id", type=int, required=True, description="规则序号（从 get_robots_rules 接口获取）"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {"type": "object"},
                    "message": {"type": "string", "example": "删除成功"}
                }
            },
            404: "规则不存在"
        }
    )
    @action(detail=False, methods=['delete'], url_path='delete-robots-rule', permission_classes=[IsAdmin])
    def delete_robots_rule(self, request):
        """删除 Robots.txt 规则"""
        rule_id = request.query_params.get('rule_id')
        if not rule_id:
            return ApiResponse(code=400, message="请提供规则序号")

        try:
            rule_id = int(rule_id)
        except ValueError:
            return ApiResponse(code=400, message="规则序号必须为整数")

        try:
            config = SiteConfig.objects.get(config_type='robots_txt', is_active=True)
            content = config.content
        except SiteConfig.DoesNotExist:
            return ApiResponse(code=404, message="Robots.txt 配置不存在")

        # 解析当前内容
        rules = self._parse_robots_content(content)
        
        # 查找要删除的规则
        target_rule = None
        for rule in rules:
            if rule['id'] == rule_id:
                target_rule = rule
                break

        if not target_rule:
            return ApiResponse(code=404, message=f"规则序号 {rule_id} 不存在")

        # 重新构建 Robots.txt 内容（排除要删除的规则）
        new_content = self._rebuild_robots_content(rules, exclude_id=rule_id)
        
        # 更新配置
        config.content = new_content
        config.save()

        return ApiResponse(data={'deleted_rule': target_rule}, message="删除成功")

    @extend_schema(
        summary="添加 Robots.txt 规则",
        description="追加一个新的 User-agent 规则到 Robots.txt",
        request=RobotsRuleAddSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "更新后的 Robots.txt 内容"}
                        }
                    },
                    "message": {"type": "string", "example": "添加成功"}
                }
            },
            400: "参数错误"
        }
    )
    @action(detail=False, methods=['post'], url_path='add-robots-rule', permission_classes=[IsAdmin])
    def add_robots_rule(self, request):
        """添加 Robots.txt 规则"""
        serializer = RobotsRuleAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        user_agent = validated_data['user_agent']
        allow_paths = validated_data.get('allow_paths', [])
        disallow_paths = validated_data.get('disallow_paths', [])
        crawl_delay = validated_data.get('crawl_delay')
        sitemap = validated_data.get('sitemap', '')

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

        # 解析现有内容
        existing_rules = self._parse_robots_content(config.content or '')
        
        # 构建新规则
        new_rule_lines = [f"User-agent: {user_agent}"]
        
        # 添加 Allow 路径
        for path in allow_paths:
            if path:
                new_rule_lines.append(f"Allow: {path}")
        
        # 添加 Disallow 路径
        for path in disallow_paths:
            if path:
                new_rule_lines.append(f"Disallow: {path}")
        
        # 添加 Crawl-delay（存储1-10，显示0.1-1）
        if crawl_delay is not None:
            # 用户传入的是显示值（0.1-1），需要转换为存储值（1-10）
            stored_delay = int(crawl_delay * 10)
            stored_delay = max(1, min(10, stored_delay))  # 限制在1-10范围内
            new_rule_lines.append(f"Crawl-delay: {stored_delay}")
        
        # 添加空行分隔
        new_rule_text = '\n'.join(new_rule_lines)
        
        # 追加到现有内容
        if config.content and config.content.strip():
            new_content = config.content.rstrip() + '\n\n' + new_rule_text
        else:
            new_content = new_rule_text
        
        # 如果有 sitemap，追加到末尾
        if sitemap:
            new_content += f"\n\nSitemap: {sitemap}"

        # 更新配置
        config.content = new_content
        config.save()

        return ApiResponse(data={'content': config.content}, message="添加成功")

    def _rebuild_robots_content(self, rules, exclude_id=None):
        """根据规则列表重建 Robots.txt 内容"""
        content_parts = []
        
        for rule in rules:
            if exclude_id and rule['id'] == exclude_id:
                continue
            
            rule_lines = [f"User-agent: {rule['user_agent']}"]
            
            # 添加 Allow
            for path in rule.get('allow', []):
                if path:
                    rule_lines.append(f"Allow: {path}")
            
            # 添加 Disallow
            for path in rule.get('disallow', []):
                if path:
                    rule_lines.append(f"Disallow: {path}")
            
            # 添加 Crawl-delay
            if rule.get('crawl_delay') is not None:
                # 显示值（0.1-1）转存储值（1-10）
                stored_delay = int(rule['crawl_delay'] * 10)
                stored_delay = max(1, min(10, stored_delay))
                rule_lines.append(f"Crawl-delay: {stored_delay}")
            
            content_parts.append('\n'.join(rule_lines))
        
        # 添加 Sitemap（从第一个规则中获取）
        sitemap = None
        for rule in rules:
            if rule.get('sitemap'):
                sitemap = rule['sitemap']
                break
        
        result = '\n\n'.join(content_parts)
        if sitemap:
            result += f"\n\nSitemap: {sitemap}"
        
        return result


    @extend_schema(
        summary="测试 Robots.txt 规则",
        description="测试指定 User-agent 对 URL 路径的访问权限，返回匹配规则和说明",
        request=RobotsTestSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "user_agent": {"type": "string", "description": "User-agent"},
                            "url": {"type": "string", "description": "完整URL"},
                            "result": {"type": "string", "enum": ["allowed", "disallowed"], "description": "结果：允许/禁止"},
                            "matched_rule": {"type": "string", "description": "匹配的 Allow/Disallow 规则"},
                            "explanation": {"type": "string", "description": "详细说明"}
                        }
                    },
                    "message": {"type": "string", "example": "测试完成"}
                }
            },
            400: "参数错误"
        }
    )
    @action(detail=False, methods=['post'], url_path='test-robots-rule', permission_classes=[IsAdmin])
    def test_robots_rule(self, request):
        """测试 Robots.txt 规则"""
        serializer = RobotsTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_agent = serializer.validated_data['user_agent']
        url_path = serializer.validated_data['url_path']

        # 确保路径以 / 开头
        if not url_path.startswith('/'):
            url_path = '/' + url_path

        # 拼接完整URL
        base_url = "https://www.markwallpapers.com"
        full_url = base_url + url_path

        # 获取 Robots.txt 内容
        try:
            config = SiteConfig.objects.get(config_type='robots_txt', is_active=True)
            content = config.content
        except SiteConfig.DoesNotExist:
            content = "User-agent: *\nDisallow: /"

        # 解析规则
        rules = self._parse_robots_content(content)

        # 如果 user_agent 是 *，则遍历所有默认的 user-agent
        if user_agent == '*':
            default_agents = ['Googlebot', 'Googlebot-Image', 'Bingbot', 'Baiduspider']
            results = []
            for agent in default_agents:
                result = self._test_access(rules, agent, url_path)
                results.append({
                    'user_agent': agent,
                    'url': full_url,
                    'result': result['result'],
                    'matched_rule': result['matched_rule'],
                    'explanation': result['explanation'],
                    'status_code': result['status_code']
                })
            return ApiResponse(data=results, message="测试完成")

        # 单个 user-agent 测试
        result = self._test_access(rules, user_agent, url_path)

        # 构建返回数据
        response_data = [{
            'user_agent': user_agent,
            'url': full_url,
            'result': result['result'],
            'matched_rule': result['matched_rule'],
            'explanation': result['explanation'],
            'status_code':result['status_code']
        }]

        return ApiResponse(data=response_data, message="测试完成")

    def _test_access(self, rules, user_agent, url_path):
        """
        【正确版 robots 协议解析】
        1. 先加载 * 通用规则
        2. 再加载 当前爬虫专属规则（覆盖通用）
        3. 合并后按 最长匹配原则 判断
        4. 专属规则不需要重复写通用的 Disallow，自动继承
        """
        user_agent_lower = user_agent.lower()

        # ======================
        # 第一步：收集所有规则
        # ======================
        allow_patterns = []
        disallow_patterns = []

        # 1. 先加载 通用规则 *
        for rule_block in rules:
            block_agent = rule_block.get('user_agent', '').lower()
            if block_agent == '*':
                allow_patterns.extend(rule_block.get('allow', []))
                disallow_patterns.extend(rule_block.get('disallow', []))
                break

        # 2. 再加载 爬虫自身专属规则（会覆盖/叠加）
        for rule_block in rules:
            block_agent = rule_block.get('user_agent', '').lower()
            if block_agent == user_agent_lower:
                allow_patterns.extend(rule_block.get('allow', []))
                disallow_patterns.extend(rule_block.get('disallow', []))
                break

        # 去重
        allow_patterns = list(set(allow_patterns))
        disallow_patterns = list(set(disallow_patterns))

        # ======================
        # 第二步：最长匹配原则
        # ======================
        best_match = None
        best_type = None
        max_len = -1

        # 检查 Allow
        for pat in allow_patterns:
            if not pat:
                continue
            if self._url_matches_pattern(url_path, pat):
                l = len(pat)
                if l > max_len:
                    max_len = l
                    best_match = pat
                    best_type = 'allow'

        # 检查 Disallow
        for pat in disallow_patterns:
            if not pat:
                continue
            if self._url_matches_pattern(url_path, pat):
                l = len(pat)
                if l > max_len:
                    max_len = l
                    best_match = pat
                    best_type = 'disallow'

        if best_type == 'disallow':
            return {
                'result': 'disallowed',
                'status_code': 403,
                'matched_rule': f'Disallow: {best_match}',
                'explanation': f'根据 robots 规则（通用+专属），{user_agent} 禁止访问 {url_path}'
            }
        else:
            return {
                'result': 'allowed',
                'status_code': 200,
                'matched_rule': f'Allow: {best_match or "/"}',
                'explanation': f'根据 robots 规则（通用+专属），{user_agent} 允许访问 {url_path}'
            }

    def _url_matches_pattern(self, url_path, pattern):
        """robots.txt 标准通配符匹配 *"""
        import re
        # 转义正则，把 * 变成 .*
        regex_pattern = re.escape(pattern).replace(r'\*', '.*')
        # 前缀匹配（robots 标准）
        return re.match(regex_pattern, url_path) is not None