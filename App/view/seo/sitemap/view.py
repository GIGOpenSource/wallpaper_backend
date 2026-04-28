from django.db import transaction
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from rest_framework.decorators import action
from django.utils.translation import get_language
from models.models import SiteConfig
from tool.base_views import BaseViewSet
from tool.permissions import IsAdmin
from tool.utils import ApiResponse, CustomPagination
from django.utils import timezone

class SitemapURLSerializer(serializers.ModelSerializer):
    """Sitemap URL 序列化器"""
    index_status = serializers.SerializerMethodField(help_text="索引状态")
    changefreq = serializers.SerializerMethodField(help_text="更新频率")

    class Meta:
        model = SiteConfig
        fields = [
            'id', 'content', 'title', 'priority',
            'index_status', 'changefreq',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_index_status(self, obj):
        """获取索引状态"""
        return obj.config_value.get('index_status', 'pending')

    def get_changefreq(self, obj):
        """获取更新频率"""
        return obj.config_value.get('changefreq', 'weekly')

    def get_priority_display(self, obj):
        """将 0-100 转换为 0.1-1.0"""
        return round(obj.priority / 100, 1) if obj.priority else 0.1

class SitemapSerializer(serializers.ModelSerializer):
    """Sitemap 记录序列化器"""
    url_count = serializers.SerializerMethodField(help_text="URL 数量")
    file_size = serializers.SerializerMethodField(help_text="文件大小（字节）")
    applied = serializers.SerializerMethodField(help_text="应用状态")
    generated_at = serializers.SerializerMethodField(help_text="生成时间")

    class Meta:
        model = SiteConfig
        fields = [
            'id', 'config_type', 'content', 'title', 'priority',
            'url_count', 'file_size', 'applied', 'generated_at',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_url_count(self, obj):
        """获取 URL 数量"""
        return obj.config_value.get('url_count', 0)

    def get_file_size(self, obj):
        """获取文件大小"""
        return obj.config_value.get('file_size', 0)

    def get_applied(self, obj):
        """获取应用状态"""
        return obj.config_value.get('applied', False)

    def get_generated_at(self, obj):
        """获取生成时间"""
        return obj.config_value.get('generated_at', '')


class SitemapURLCreateUpdateSerializer(serializers.Serializer):
    """Sitemap URL 创建/更新序列化器"""
    content = serializers.URLField(required=True, help_text="URL 地址")
    title = serializers.CharField(max_length=200, required=False, allow_blank=True, help_text="标题")
    priority = serializers.IntegerField(required=False, default=0, min_value=0, max_value=100, help_text="优先级（0-100）")
    index_status = serializers.ChoiceField(
        choices=['pending', 'indexed', 'excluded'],
        required=False,
        default='pending',
        help_text="索引状态"
    )
    changefreq = serializers.ChoiceField(
        choices=['always', 'hourly', 'daily', 'weekly', 'monthly', 'yearly', 'never'],
        required=False,
        default='weekly',
        help_text="更新频率"
    )
    is_active = serializers.BooleanField(required=False, default=True, help_text="是否启用")


@extend_schema(tags=["Sitemap 管理"])
class SitemapURLViewSet(BaseViewSet):
    """Sitemap URL 管理"""
    queryset = SiteConfig.objects.filter(config_type='sitemap_url')
    serializer_class = SitemapURLSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return SitemapURLCreateUpdateSerializer
        elif self.action == 'list_sitemaps':
            return SitemapSerializer
        return SitemapURLSerializer

    @extend_schema(
        summary="获取 Sitemap URL 列表",
        parameters=[
            OpenApiParameter(name="index_status", type=str, required=False, description="索引状态"),
            OpenApiParameter(name="changefreq", type=str, required=False, description="更新频率"),
            OpenApiParameter(name="is_active", type=bool, required=False, description="是否启用"),
            OpenApiParameter(name="url", type=str, required=False, description="URL 模糊匹配"),
        ],
    )
    def list(self, request, *args, **kwargs):
        """获取 Sitemap URL 列表"""
        queryset = SiteConfig.objects.filter(config_type='sitemap_url')

        index_status = request.query_params.get('index_status')
        if index_status:
            queryset = queryset.filter(config_value__index_status=index_status)

        changefreq = request.query_params.get('changefreq')
        if changefreq:
            queryset = queryset.filter(config_value__changefreq=changefreq)

        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        url = request.query_params.get('url')
        if url:
            queryset = queryset.filter(content__icontains=url)

        queryset = queryset.order_by('-priority', '-created_at')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = serializer.data
            # 转换 priority：从 1-10 转为 0.1-1.0
            for item in data:
                if 'priority' in item and item['priority'] is not None:
                    item['priority'] = round(item['priority'] / 10, 1)

            return self.get_paginated_response(data)
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data
        # 转换 priority：从 1-10 转为 0.1-1.0
        for item in data:
            if 'priority' in item and item['priority'] is not None:
                item['priority'] = round(item['priority'] / 10, 1)

        return ApiResponse(data=data, message="列表获取成功")

    @extend_schema(
        summary="获取 Sitemap URL 详情",
    )
    def retrieve(self, request, *args, **kwargs):
        """获取 Sitemap URL 详情"""
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="创建 Sitemap URL",
        request=SitemapURLCreateUpdateSerializer,
    )
    def create(self, request, *args, **kwargs):
        """创建 Sitemap URL"""
        serializer = self.get_serializer(data=request.data)
        request.data["priority"] = int(request.data.get("priority", 1) * 10)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        config_value = {
            'index_status': validated_data.get('index_status', 'pending'),
            'changefreq': validated_data.get('changefreq', 'weekly')
        }
        config = SiteConfig.objects.create(
            config_type='sitemap_url',
            content=validated_data['content'],
            title=validated_data.get('title', ''),
            priority=float(validated_data.get('priority', 0)),
            config_value=config_value,
            is_active=validated_data.get('is_active', True)
        )
        result_serializer = SitemapURLSerializer(config)
        response = {
            "id": config.id,
            "content": config.content,
            "title": config.title,
            "priority": config.priority/10,
            "index_status": config.config_value.get("index_status"),
            "changefreq": config.config_value.get("changefreq"),
            "is_active": config.is_active,
            "created_at": config.created_at,
            "updated_at": config.updated_at
        }
        return ApiResponse(data=response, message="创建成功", code=201)

    @extend_schema(
        summary="获取 Sitemap 记录列表",
        description="获取已生成的 Sitemap XML 文件列表，支持按类型、应用状态筛选",
        parameters=[
            OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码"),
            OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量"),
        ],
    )
    @action(detail=False, methods=['get'], url_path='list-sitemaps')
    def list_sitemaps(self, request):
        """获取 Sitemap 记录列表"""
        queryset = SiteConfig.objects.filter(config_type='sitemap_file')
        # 排序：按创建时间倒序
        queryset = queryset.order_by('-created_at')
        # 分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SitemapSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = SitemapSerializer(queryset, many=True)
        data = serializer.data
        for item in data:
            if 'priority' in item and item['priority'] is not None:
                item['priority'] = round(item['priority'] / 10, 1)
        return ApiResponse(data=data, message="列表获取成功")


    @extend_schema(
        summary="更新 Sitemap URL",
        request=SitemapURLCreateUpdateSerializer,
    )
    def update(self, request, *args, **kwargs):
        """更新 Sitemap URL"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        # serializer.is_valid(raise_exception=False)
        # validated_data = serializer.validated_data
        if 'content' in  request.data:
            instance.content = request.data['content']
        if 'title' in request.data:
            instance.title = request.data.get('title', '')
        if 'priority' in request.data:
            instance.priority = request.data['priority']*10
        if 'is_active' in request.data:
            instance.is_active = request.data['is_active']

        if 'index_status' in request.data or 'changefreq' in request.data:
            config_value = instance.config_value or {}
            if 'index_status' in request.data:
                config_value['index_status'] = request.data['index_status']
            if 'changefreq' in request.data:
                config_value['changefreq'] = request.data['changefreq']
            instance.config_value = config_value

        instance.save()

        result_serializer = SitemapURLSerializer(instance)
        return ApiResponse(data=result_serializer.data, message="更新成功")

    def partial_update(self, request, *args, **kwargs):
        """部分更新 Sitemap URL"""
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """删除 Sitemap URL"""
        instance = self.get_object()
        instance.delete()
        return ApiResponse(message="删除成功")

    @extend_schema(
        summary="获取 Sitemap 统计信息",
        description="获取 URL 总数、已索引数、待索引数、索引率等统计信息",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "total_urls": {"type": "integer", "description": "总 URL 数"},
                            "indexed_count": {"type": "integer", "description": "已索引数"},
                            "pending_count": {"type": "integer", "description": "待索引数"},
                            "excluded_count": {"type": "integer", "description": "已排除数"},
                            "index_rate": {"type": "number", "description": "索引率（百分比）"}
                        }
                    },
                    "message": {"type": "string"}
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """获取 Sitemap 统计信息"""
        queryset = SiteConfig.objects.filter(config_type='sitemap_url')
        total_urls = queryset.count()
        indexed_count = queryset.filter(config_value__index_status='indexed').count()
        pending_count = queryset.filter(config_value__index_status='pending').count()
        excluded_count = queryset.filter(config_value__index_status='excluded').count()
        index_rate = round((indexed_count / total_urls * 100), 2) if total_urls > 0 else 0

        return ApiResponse(
            data={
                'total_urls': total_urls,
                'indexed_count': indexed_count,
                'pending_count': pending_count,
                'excluded_count': excluded_count,
                'index_rate': index_rate
            },
            message="获取成功"
        )


    @extend_schema(
        summary="生成 Sitemap XML",
        description="根据内容类型、更新频率、默认优先级生成 Sitemap XML 文件并保存到数据库",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "content_type": {
                        "type": "string",
                        "enum": ["article", "category", "tag", "page"],
                        "description": "Sitemap 类型（文章/分类/标签/页面）"
                    },
                    "changefreq": {
                        "type": "string",
                        "enum": ["always", "hourly", "daily", "weekly", "monthly", "yearly", "never"],
                        "description": "更新频率"
                    },
                    "priority": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "默认优先级（0-100）"
                    }
                },
                "required": ["content_type", "changefreq", "priority"]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "title": {"type": "string", "description": "文件名"},
                            "url_count": {"type": "integer", "description": "URL 数量"},
                            "file_size": {"type": "integer", "description": "文件大小（字节）"}
                        }
                    },
                    "message": {"type": "string"}
                }
            },
            400: "参数错误"
        }
    )
    @action(detail=False, methods=['post'], url_path='generate-xml')
    def generate_xml(self, request):
        """生成 Sitemap XML 并保存到数据库"""
        content_type = request.data.get('content_type')
        changefreq = request.data.get('changefreq', 'weekly')
        priority = request.data.get('priority', 50)
        # 参数验证
        if not content_type or content_type not in ['article', 'category', 'tag', 'page']:
            return ApiResponse(code=400, message="请提供有效的内容类型（article/category/tag/page）")
        if changefreq not in ['always', 'hourly', 'daily', 'weekly', 'monthly', 'yearly', 'never']:
            return ApiResponse(code=400, message="请提供有效的更新频率")
        if not isinstance(priority, int) or priority < 0 or priority > 100:
            return ApiResponse(code=400, message="优先级必须在 0-100 之间")
        # 根据内容类型筛选 sitemap_url 记录
        queryset = SiteConfig.objects.filter(
            config_type='sitemap_url',
            is_active=True,
            title=content_type,
            priority=priority
        ).order_by('-priority', '-created_at')
        # 生成 XML 内容
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        url_count = 0
        for item in queryset:
            url = item.content
            item_changefreq = item.config_value.get('changefreq', changefreq)
            priority_value = item.priority / 100 if item.priority else priority / 100
            xml_content += '  <url>\n'
            xml_content += f'    <loc>{url}</loc>\n'
            xml_content += f'    <changefreq>{item_changefreq}</changefreq>\n'
            xml_content += f'    <priority>{priority_value:.1f}</priority>\n'
            xml_content += '  </url>\n'
            url_count += 1
        xml_content += '</urlset>'
        # 计算文件大小
        file_size = len(xml_content.encode('utf-8'))
        # 生成文件名：类型_更新频率
        filename = f"{content_type}_{changefreq}"
        # 保存到 SiteConfig 表
        sitemap_config = SiteConfig.objects.create(
            config_type='sitemap_file',
            title=filename,
            content=xml_content,
            priority=priority,
            config_value={
                'changefreq': changefreq,
                'url_count': url_count,
                'file_size': file_size,
                'applied': False,  # 默认未应用
            },
            created_at=timezone.now().isoformat(),
            is_active=True
        )
        return ApiResponse(
            data={
                'id': sitemap_config.id,
                'title': filename,
                'content_type': content_type,
                'url_count': url_count,
                'file_size': file_size
            },
            message=f"Sitemap XML 生成成功，共 {url_count} 个 URL，文件大小 {file_size} 字节"
        )
