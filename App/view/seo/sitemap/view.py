from django.db import transaction
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from rest_framework.decorators import action
from django.utils.translation import get_language
from models.models import SiteConfig
from seo.seo_tools import gsc_tool
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
        return round(obj.priority / 10, 1) if obj.priority else 0.1

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
        priority_str = request.data.get("priority", "1.0")
        priority_value = int(float(priority_str) * 10)
        request.data["priority"] = priority_value

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
        """删除 Sitemap URL（同时删除关联的 PageTDK）"""
        from models.models import PageTDK
        instance = self.get_object()
        sitemap_url_id = instance.id
        try:
            with transaction.atomic():
                # 1. 删除关联的 PageTDK 记录（url_id 指向此 sitemap_url）
                deleted_tdk_count = PageTDK.objects.filter(url_id=sitemap_url_id).delete()[0]
                # 2. 删除 Sitemap URL 自身
                instance.delete()
                if deleted_tdk_count > 0:
                    return ApiResponse(
                        message=f"删除成功，同时删除了 {deleted_tdk_count} 条关联的 TDK 配置"
                    )
                else:
                    return ApiResponse(message="删除成功")
        except Exception as e:
            return ApiResponse(code=500, message=f"删除失败：{str(e)}")

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
        summary="检测 Sitemap 状态",
        description="通过 HTTP 请求检测指定 Sitemap URL 是否可正常访问",
    )
    @action(detail=False, methods=['post'], url_path='check-status')
    def check_status(self, request):
        """检测 Sitemap 状态（固定URL）"""
        import requests
        from datetime import datetime
        sitemap_url = "https://www.markwallpapers.com/sitemap.xml"
        try:
            res = requests.get(sitemap_url, timeout=5)
            status = res.status_code == 200
        except:
            # 请求失败也算 false
            status = False
        # 只返回你要的两个字段
        data = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 当前时间
            "status": status  # true / false
        }
        return ApiResponse(data=data, message="检测完成")


    @extend_schema(
        summary="批量应用 Sitemap 并通知搜索引擎",
        description="选择多个 sitemap_file 记录并依次应用到 /sitemap.xml，每次应用后通过 Google Search Console API 通知收录（间隔 10 秒）",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "sitemap_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "要应用的 sitemap_file ID 数组"
                    },
                    "site_url": {"type": "string", "description": "网站 URL（如 https://www.markwallpapers.com/）"}
                },
                "required": ["sitemap_ids"]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer"},
                    "data": {"type": "object"},
                    "message": {"type": "string"}
                }
            }
        }
    )
    @action(detail=False, methods=['post'], url_path='submit-to-search-engine')
    def submit_to_search_engine(self, request):
        """批量应用 Sitemap 并通过 GSC API 通知 Google"""
        import time
        from seo.seo_tools import gsc_tool

        sitemap_ids = request.data.get('sitemap_ids', [])
        site_url = request.data.get('site_url', 'https://www.markwallpapers.com/')

        # 校验参数
        if not isinstance(sitemap_ids, list) or len(sitemap_ids) == 0:
            return ApiResponse(code=400, message="请提供非空的 sitemap_ids 数组")

        # 确保 URL 格式正确
        if not site_url.endswith('/'):
            site_url += '/'

        results = []
        success_count = 0
        fail_count = 0

        # 循环处理每个 sitemap_id
        for idx, sitemap_id in enumerate(sitemap_ids):
            try:
                with transaction.atomic():
                    # 1. 找到目标 sitemap 并设置为 applied
                    target = SiteConfig.objects.get(id=sitemap_id, config_type='sitemap_file')

                    # 2. 取消其他 sitemap 的 applied 状态（手动遍历更新）
                    other_sitemaps = SiteConfig.objects.filter(
                        config_type='sitemap_file'
                    ).exclude(id=sitemap_id)

                    for sm in other_sitemaps:
                        cv = sm.config_value or {}
                        if cv.get('applied', False):
                            cv['applied'] = False
                            sm.config_value = cv
                            sm.save(update_fields=['config_value'])

                    # 3. 应用当前 sitemap
                    config_value = target.config_value or {}
                    config_value['applied'] = True
                    target.config_value = config_value
                    target.save(update_fields=['config_value'])

                # 2. 构造 Sitemap URL
                sitemap_url = f"{site_url}sitemap.xml"

                # 3. 通过 Google Search Console API 提交 Sitemap
                gsc_result = None
                submit_status = 'success'
                submit_message = '已通过 Google Search Console API 提交'

                try:
                    gsc_result = gsc_tool.submit_sitemap(site_url, sitemap_url)
                except Exception as e:
                    submit_status = 'failed'
                    submit_message = f'GSC API 提交失败: {str(e)}'
                    gsc_result = {'error': str(e)}

                results.append({
                    'sitemap_id': target.id,
                    'title': target.title,
                    'url_count': target.config_value.get('url_count', 0),
                    'sitemap_url': sitemap_url,
                    'submit_status': submit_status,
                    'submit_message': submit_message,
                    'gsc_result': gsc_result
                })

                if submit_status == 'success':
                    success_count += 1
                else:
                    fail_count += 1

                # 4. 如果不是最后一个，等待 10 秒
                if idx < len(sitemap_ids) - 1:
                    time.sleep(10)

            except SiteConfig.DoesNotExist:
                results.append({
                    'sitemap_id': sitemap_id,
                    'submit_status': 'failed',
                    'submit_message': 'Sitemap 不存在或类型不正确'
                })
                fail_count += 1

                # 失败的也等待 10 秒（保持节奏一致）
                if idx < len(sitemap_ids) - 1:
                    time.sleep(10)

        return ApiResponse(
            data={
                'total': len(sitemap_ids),
                'success': success_count,
                'fail': fail_count,
                'results': results
            },
            message=f"批量处理完成，成功{success_count}条，失败{fail_count}条"
        )

    @extend_schema(
        summary="获取当前应用的 Sitemap XML",
        description="获取标记为 applied=True 的 Sitemap XML 内容。添加参数 ?raw=1 可返回纯 XML 格式供 Nginx 代理",
        parameters=[
            OpenApiParameter(name="raw", type=int, required=False, description="设置为 1 时返回纯 XML 格式"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "title": {"type": "string"},
                            "content": {"type": "string"},
                            "url_count": {"type": "integer"}
                        }
                    },
                    "message": {"type": "string"}
                }
            },
            404: "未找到已应用的 Sitemap"
        }
    )
    @action(detail=False, methods=['get'], url_path='get-sitemap-xml', permission_classes=[])
    def get_sitemap_xml(self, request):
        """获取当前应用的 Sitemap XML（支持 raw 纯文本模式）"""
        from django.http import HttpResponse

        sitemap = SiteConfig.objects.filter(
            config_type='sitemap_file',
            is_active=True
        ).order_by('-created_at').first()

        if not sitemap:
            # 如果请求 raw，返回空 XML 头
            if request.query_params.get('raw') == '1':
                empty_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
                return HttpResponse(empty_xml, content_type='application/xml; charset=utf-8')
            return ApiResponse(code=404, message="未找到已应用的 Sitemap")

        # raw=1 模式：直接返回 XML 内容（供 Nginx 代理）
        if request.query_params.get('raw') == '1':
            return HttpResponse(sitemap.content, content_type='application/xml; charset=utf-8')

        # 默认 JSON 模式：供前端调用
        return ApiResponse(
            data={
                'id': sitemap.id,
                'title': sitemap.title,
                'content': sitemap.content,
                'url_count': sitemap.config_value.get('url_count', 0)
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
        # if not isinstance(priority, int) or priority < 0 or priority > 100:
        #     return ApiResponse(code=400, message="优先级必须在 0-100 之间")
        priority = priority*10
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
            priority_value = item.priority / 10 if item.priority else priority / 10
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

    @extend_schema(
        summary="更新 Sitemap XML 记录",
        description="根据 ID 直接更新 sitemap_file 记录的 title、content、config_value 字段",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                        "description": "sitemap_file 记录ID"
                    },
                    "title": {
                        "type": "string",
                        "description": "文件名（可选）"
                    },
                    "content": {
                        "type": "string",
                        "description": "XML 内容（可选）"
                    },
                    "config_value": {
                        "type": "object",
                        "description": "配置值 JSON（可选）",
                        "properties": {
                            "applied": {"type": "boolean", "description": "应用状态"},
                            "file_size": {"type": "integer", "description": "文件大小"},
                            "url_count": {"type": "integer", "description": "URL 数量"},
                            "changefreq": {"type": "string", "description": "更新频率"}
                        }
                    }
                },
                "required": ["id"]
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
                            "title": {"type": "string"},
                            "content_type": {"type": "string"},
                            "url_count": {"type": "integer"},
                            "file_size": {"type": "integer"}
                        }
                    },
                    "message": {"type": "string"}
                }
            },
            400: "参数错误",
            404: "Sitemap 不存在"
        }
    )
    @action(detail=False, methods=['post'], url_path='update-sitemap-xml')
    def update_sitemap_xml(self, request):
        """更新 Sitemap XML 记录"""
        sitemap_id = request.data.get('id')
        
        if not sitemap_id:
            return ApiResponse(code=400, message="请提供 id")
        
        try:
            # 查询 sitemap_file 记录
            sitemap_config = SiteConfig.objects.get(
                id=sitemap_id,
                config_type='sitemap_file'
            )
            # 更新 title（如果提供）
            if 'title' in request.data:
                sitemap_config.title = request.data['title']
            # 更新 content（如果提供）
            if 'content' in request.data:
                sitemap_config.content = request.data['content']
            # 更新 config_value（如果提供）
            if 'config_value' in request.data:
                # 合并现有的 config_value 和新的 config_value
                existing_config = sitemap_config.config_value or {}
                new_config = request.data['config_value']
                existing_config.update(new_config)
                sitemap_config.config_value = existing_config
            sitemap_config.save()
            # 从 title 解析 content_type
            title_parts = sitemap_config.title.split('_')
            content_type = title_parts[0] if len(title_parts) >= 1 else 'unknown'
            return ApiResponse(
                data={
                    'id': sitemap_config.id,
                    'title': sitemap_config.title,
                    'content_type': content_type,
                    'url_count': sitemap_config.config_value.get('url_count', 0),
                    'file_size': sitemap_config.config_value.get('file_size', 0)
                },
                message="更新成功"
            )
        except SiteConfig.DoesNotExist:
            return ApiResponse(code=404, message="Sitemap 记录不存在或类型不正确")
        except Exception as e:
            return ApiResponse(code=500, message=f"更新失败：{str(e)}")
