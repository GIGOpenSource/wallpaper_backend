"""
@Project ：wallpaper
@File    ：view.py
@Author  ：LiangHB
@Date    ：2026/4/14 17:13
@description : 壁纸相关视图逻辑
"""
import io
import json
import os
import uuid

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import F
from django.db.models.functions import Greatest
from PIL import Image
from django.utils import timezone

from App.view.wallpapers.search_models.search_models import TAG_MAPPING
from tool.base_views import BaseViewSet
from tool.middleware import logger
from tool.permissions import IsCustomerTokenValid, IsOwnerOrAdmin, IsAdmin
from tool.token_tools import CustomTokenTool
from tool.uploader_data import bytes_from_uploaded_image, upload_image_to_cos
from tool.utils import CustomPagination, ApiResponse
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiRequest, OpenApiExample
from django.utils.translation import get_language, gettext as _, activate
import pandas as pd
from rest_framework.decorators import api_view, action
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser, FormParser
from models.models import (
    Wallpapers,
    WallpaperTag,
    WallpaperCategory,
    NavigationTag,
    WallpaperLike,
    WallpaperCollection,
    CustomerWallpaperUpload,
    CustomerUser, RecommendStrategy,
)


def _parse_tag_ids(raw):
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        out = []
        for x in raw:
            try:
                out.append(int(x))
            except (TypeError, ValueError):
                continue
        return out
    s = str(raw).strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            arr = json.loads(s)
            out = []
            for x in arr:
                try:
                    out.append(int(x))
                except (TypeError, ValueError):
                    continue
            return out
        except json.JSONDecodeError:
            return []
    return [int(x) for x in s.split(",") if x.strip().isdigit()]


def _parse_tag_names(raw):
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    s = str(raw).strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            arr = json.loads(s)
            return [str(x).strip() for x in arr if str(x).strip()]
        except json.JSONDecodeError:
            return []
    return [x.strip() for x in s.split(",") if x.strip()]


def _person_wallpaper_cos_key(title: str, original_filename: str) -> tuple[str, str]:
    """COS 对象键 person_wallpaper/{title}.{ext}，扩展名随上传文件。"""
    _, ext = os.path.splitext(original_filename or "")
    ext = (ext or ".jpg").lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        ext = ".jpg"
    base = (title or "").strip()
    for ch in '<>:"|?*\\/\x00':
        base = base.replace(ch, "")
    base = base.strip(" .")[:180]
    if not base:
        base = uuid.uuid4().hex[:12]
    return f"person_wallpaper/{base}{ext}", ext.lstrip(".").lower()


def _image_meta_from_bytes(content: bytes):
    try:
        with Image.open(io.BytesIO(content)) as im:
            fmt = (im.format or "").lower() or None
            return im.width, im.height, fmt
    except Exception:
        return 0, 0, None


# ====================优化查询218start===============================
class WallpapersListSerializer(serializers.ModelSerializer):
    """壁纸列表序列化器（轻量级，只包含必要字段）"""
    # tags = serializers.SerializerMethodField()
    aspect_ratio = serializers.SerializerMethodField()
    # is_liked = serializers.SerializerMethodField()
    # is_collected = serializers.SerializerMethodField()

    class Meta:
        model = Wallpapers
        fields = [
            'id', 'name', 'url', 'thumb_url', 'width', 'height', 'image_format',
            'has_watermark', 'is_live', 'is_hd', 'hot_score', 'like_count',
            'collect_count', 'download_count', 'view_count', 'created_at',
            'aspect_ratio','audit_status'
        ]
        read_only_fields = fields

    def get_tags(self, obj):
        return [{'id': tag.id, 'name': tag.name} for tag in obj.tags.all()]

    def get_aspect_ratio(self, obj):
        if not obj.width or not obj.height:
            return None

        def gcd(a, b):
            while b:
                a, b = b, a % b
            return a

        common_divisor = gcd(obj.width, obj.height)
        return f"{obj.width // common_divisor}:{obj.height // common_divisor}"

    def get_is_liked(self, obj):
        liked_ids = self.context.get("liked_wallpaper_ids")
        return obj.id in liked_ids if liked_ids else False

    def get_is_collected(self, obj):
        collected_ids = self.context.get("collected_wallpaper_ids")
        return obj.id in collected_ids if collected_ids else False


class WallpapersAdminListSerializer(serializers.ModelSerializer):
    """壁纸列表序列化器（管理员使用，包含详细信息）"""
    tags = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    uploader = serializers.SerializerMethodField()
    aspect_ratio = serializers.SerializerMethodField()

    class Meta:
        model = Wallpapers
        fields = [
            'id', 'name', 'url', 'thumb_url', 'width', 'height', 'image_format',
            'source_url', 'description', 'has_watermark', 'category', 'tags',
            'is_live', 'is_hd', 'hot_score', 'like_count', 'collect_count',
            'download_count', 'view_count', 'created_at', 'aspect_ratio',
            'audit_status', 'uploader', 'audit_remark', 'audited_at','description'
        ]
        read_only_fields = fields

    def get_tags(self, obj):
        return [
            {
                'id': tag.id,
                'name': tag.name,
            }
            for tag in obj.tags.all()
        ]

    def get_category(self, obj):
        return [
            {
                'id': cat.id,
                'name': cat.name,
            }
            for cat in obj.category.all()
        ]

    def get_uploader(self, obj):
        """获取上传者信息"""
        try:
            upload_record = getattr(obj, 'customer_upload', None)
            if not upload_record:
                return None
            customer = getattr(upload_record, 'customer', None)
            if not customer:
                return None
            return {
                "id": customer.id,
                "email": customer.email,
                "nickname": customer.nickname,
                "gender": customer.gender,
                "avatar_url": customer.avatar_url,
                "badge": customer.badge,
                "points": customer.points,
                "level": customer.level,
                "upload_count": customer.upload_count,
                "collection_count": customer.collection_count,
                "last_login": customer.last_login.isoformat() if customer.last_login else None,
                "created_at": customer.created_at.isoformat() if customer.created_at else None,
            }
        except ObjectDoesNotExist:
            return None
    def get_aspect_ratio(self, obj):
        """计算宽高比，格式如 16:9"""
        if not obj.width or not obj.height:
            return None
        def gcd(a, b):
            while b:
                a, b = b, a % b
            return a
        common_divisor = gcd(obj.width, obj.height)
        width_ratio = obj.width // common_divisor
        height_ratio = obj.height // common_divisor
        return f"{width_ratio}:{height_ratio}"

class WallpapersSerializer(serializers.ModelSerializer):
    """壁纸详情序列化器（包含完整信息）"""
    category = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    aspect_ratio = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_collected = serializers.SerializerMethodField()
    uploader = serializers.SerializerMethodField()

    class Meta:
        model = Wallpapers
        fields = [
            'id', 'name', 'url', 'thumb_url', 'width', 'height', 'image_format',
            'source_url', 'description', 'has_watermark', 'category', 'tags',
            'is_live', 'is_hd', 'hot_score', 'like_count', 'collect_count', 'download_count',
            'view_count', 'created_at', 'aspect_ratio', 'is_liked', 'is_collected',
            'uploader',
        ]
        read_only_fields = ['id', 'created_at', 'like_count', 'collect_count', 'download_count']

    def __init__(self, *args, **kwargs):
        super(WallpapersSerializer, self).__init__(*args, **kwargs)
        if not self.context.get('include_detail_info'):
            self.fields.pop('uploader', None)

    def get_uploader(self, obj):
        """获取上传者简要信息"""
        logger.debug(
            f"get_uploader called for wallpaper {obj.id}, include_detail_info: {self.context.get('include_detail_info')}")
        try:
            upload_record = getattr(obj, 'customer_upload', None)
            if not upload_record:
                return None
            customer = getattr(upload_record, 'customer', None)
            if not customer:
                return None
            return {
                "id": customer.id,
                "email": customer.email,
                "nickname": customer.nickname,
                "gender": customer.gender,
                "avatar_url": customer.avatar_url,
                "badge": customer.badge,
                "points": customer.points,
                "level": customer.level,
                "upload_count": customer.upload_count,
                "collection_count": customer.collection_count,
                "last_login": customer.last_login.isoformat() if customer.last_login else None,
                "created_at": customer.created_at.isoformat() if customer.created_at else None,
            }
        except ObjectDoesNotExist:
            return None

    def get_category(self, obj):
        return [
            {
                'id': cat.id,
                'name': cat.name,
            }
            for cat in obj.category.all()
        ]

    def get_tags(self, obj):
        return [
            {
                'id': tag.id,
                'name': tag.name,
            }
            for tag in obj.tags.all()
        ]

    def get_aspect_ratio(self, obj):
        """计算宽高比，格式如 16:9"""
        if not obj.width or not obj.height:
            return None

        def gcd(a, b):
            while b:
                a, b = b, a % b
            return a

        common_divisor = gcd(obj.width, obj.height)
        width_ratio = obj.width // common_divisor
        height_ratio = obj.height // common_divisor
        return f"{width_ratio}:{height_ratio}"

    def get_is_liked(self, obj):
        cid = self.context.get("customer_id")
        if not cid:
            return False
        liked_cache = self.context.get("liked_wallpaper_ids")
        if liked_cache is not None:
            return obj.id in liked_cache
        return WallpaperLike.objects.filter(customer_id=cid, wallpaper_id=obj.pk).exists()

    def get_is_collected(self, obj):
        cid = self.context.get("customer_id")
        if not cid:
            return False
        collected_cache = self.context.get("collected_wallpaper_ids")
        if collected_cache is not None:
            return obj.id in collected_cache
        return WallpaperCollection.objects.filter(user_id=cid, wallpaper_id=obj.pk).exists()


# ======================优化结束end================================
class CollectionItemSerializer(serializers.ModelSerializer):
    wallpaper = WallpapersSerializer(read_only=True)

    class Meta:
        model = WallpaperCollection
        fields = ["id", "created_at", "wallpaper"]


@extend_schema(tags=["壁纸管理"])
@extend_schema_view(
    list=extend_schema(
        summary="获取壁纸列表(Admin也可用)",
        description="默认只显示审核通过或未审核的壁纸（排除审核不通过的）",
        parameters=[
            OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码"),
            OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量"),
            OpenApiParameter(name="name", type=str, required=False, description="壁纸名称搜索"),
            OpenApiParameter(name="tag_id", type=str, required=False,
                             description="标签 ID 查询，支持单个或多个（逗号分隔）"),
            OpenApiParameter(name="category_id", type=str, required=False,
                             description="分类 ID 筛选，支持单个或多个（逗号分隔）"),
            OpenApiParameter(name="media_live", type=str, required=False, description="静态false或动态true"),
            OpenApiParameter(name="platform", type=str, required=False, description="平台电脑PC或手机PHONE "),
            OpenApiParameter(name="resolution", type=str, required=False,
                             description="分辨率多选，逗号分隔，如 3840x2160,2560x1440,1920x1080"),
            OpenApiParameter(name="aspect_ratio", type=str, required=False,
                             description="宽高比多选，逗号分隔，如 16:9,21:9,9:16"),
            OpenApiParameter(name="order", type=str, required=False,
                             description="排序规则（只能传一个）：latest=最新, views=最多浏览, downloads=最多下载, hot=热度"),
            OpenApiParameter(name="audit_status", type=str, required=False,
                             description="审核状态筛选（仅管理员）：pending/approved/rejected"),

        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "results": {"type": "array", "items": {"$ref": "#/components/schemas/Wallpapers"}},
                            "total": {"type": "integer", "example": 50}
                        }
                    },
                    "message": {"type": "string", "example": "列表获取成功"}
                }
            }
        }
    ),
    retrieve=extend_schema(summary="获取壁纸详情", responses={200: WallpapersSerializer, 404: "壁纸不存在"}),
    create=extend_schema(summary="创建壁纸", request=WallpapersSerializer),
    # update=extend_schema(summary="更新壁纸(Admin或自己上传可删)", request=WallpapersSerializer),
    partial_update=extend_schema(summary="部分更新壁纸", request=WallpapersSerializer),
    destroy=extend_schema(summary="删除壁纸(Admin或自己上传可删)", description="删除指定壁纸记录",
                          responses={204: "删除成功", 404: "壁纸不存在"})
)
class WallpapersViewSet(BaseViewSet):
    """
    壁纸管理 ViewSet
    提供壁纸的增删改查功能
    """
    queryset = Wallpapers.objects.all()
    serializer_class = WallpapersSerializer
    pagination_class = CustomPagination

    def get_permissions(self):
        """根据不同操作返回不同的权限类"""
        if self.action in ['update', 'partial_update', 'destroy']:
            # 写操作：需要是管理员或者是上传者本人
            return [IsOwnerOrAdmin()]
        elif self.action in ['audit_approve', 'audit_reject', 'batch_delete']:
            return [IsAdmin()]
        # 读操作无需权限
        return []
    def get_serializer_class(self):
        """根据动作返回不同的序列化器"""
        if self.action == 'list':
            return WallpapersListSerializer
        return WallpapersSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["customer_id"] = None
        tok = self.request.headers.get("token")
        if tok:
            ok, cid = CustomTokenTool.verify_customer_token(tok)
            if ok:
                ctx["customer_id"] = cid
        return ctx
    def get_queryset(self):
        """
        动态过滤查询
        """
        from models.models import User
        queryset = super().get_queryset()
        # 默认过滤：排除审核不通过的壁纸（除非是管理员查看）
        is_admin = False
        if hasattr(self.request, 'user') and isinstance(self.request.user, User):
            if self.request.user.role in ['admin', 'operator']:
                is_admin = True

        if not is_admin:
            # 非管理员：只显示审核通过或未审核的壁纸
            queryset = queryset.exclude(audit_status='rejected')
        else:
            # 管理员可以按审核状态筛选
            audit_status = self.request.query_params.get("audit_status", "").strip()
            if audit_status and audit_status in ['pending', 'approved', 'rejected']:
                queryset = queryset.filter(audit_status=audit_status)


        if self.action == 'retrieve':
            queryset = queryset.select_related('customer_upload__customer')

        # 筛选参数：platform
        platform = self.request.query_params.get("platform", "")
        if platform.upper() == 'PC':
            queryset = queryset.filter(category__id=1).distinct()
        elif platform.upper() == 'PHONE':
            queryset = queryset.filter(category__id=2).distinct()

        media_live = self.request.query_params.get("media_live", "")
        if media_live.lower() == 'true':
            queryset = queryset.filter(category__id=4).distinct()
        elif media_live.lower() == 'false':
            queryset = queryset.filter(category__id=3).distinct()

        user_input = self.request.query_params.get("name", "").strip()
        if user_input:
            # 1. 找出所有用户输入中包含的TAG_MAPPING关键词
            matched_tags = []
            for keyword, tag_id in TAG_MAPPING.items():
                # 判断用户输入是否包含当前关键词（不区分大小写）
                if keyword.lower() in user_input.lower():
                    matched_tags.append((len(keyword), keyword, tag_id))

            if matched_tags:
                # 2. 排序：优先匹配长度更长的关键词（多个关键词时优先匹配更精准的）
                # 例如：输入"关键词123"，同时匹配"关键词1"和"关键词123"，优先选后者
                matched_tags.sort(key=lambda x: x[0], reverse=True)

                # 3. 获取优先级最高的标签ID进行筛选
                highest_priority_tag_id = matched_tags[0][2]
                queryset = queryset.filter(tags__id=highest_priority_tag_id).distinct()

                # 可选：如果需要同时匹配所有包含的标签（交集），取消下面注释
                # tag_ids = [tag[2] for tag in matched_tags]
                # queryset = queryset.filter(tags__id__in=tag_ids).distinct()
            else:
                # 4. 未匹配到任何TAG_MAPPING关键词 → 降级为原有的名称模糊搜索
                queryset = queryset.filter(name__icontains=user_input)
        from django.db.models import F, Q
        # 筛选参数：tag_id（支持单个和多个，逗号分隔）
        tag_ids = self.request.query_params.get("tag_id")
        if tag_ids:
            tag_id_list = [int(tid.strip()) for tid in tag_ids.split(',') if tid.strip().isdigit()]
            if tag_id_list:
                # 使用 filter 进行多对多查询，会匹配包含任一标签的壁纸
                queryset = queryset.filter(tags__id__in=tag_id_list).distinct()
        resolution = self.request.query_params.get("resolution", "")
        if resolution:
            res_list = [r.strip() for r in resolution.split(',') if r.strip()]
            if res_list:
                q_resolution = Q()
                for res in res_list:
                    if 'x' in res.lower():
                        parts = res.lower().split('x')
                        if len(parts) == 2:
                            try:
                                w, h = int(parts[0]), int(parts[1])
                                q_resolution |= Q(width=w, height=h)
                            except ValueError:
                                continue
                if q_resolution:
                    queryset = queryset.filter(q_resolution).distinct()

        aspect_ratio = self.request.query_params.get("aspect_ratio", "")
        if aspect_ratio:
            # 支持 16:9 和 16-9 两种格式
            aspect_ratio = aspect_ratio.replace('-', ':')
            ratio_list = [r.strip() for r in aspect_ratio.split(',') if r.strip()]
            if ratio_list:
                where_clauses = []
                params = []
                for ratio in ratio_list:
                    if ':' in ratio:
                        try:
                            w_ratio, h_ratio = map(int, ratio.split(':'))
                            if w_ratio > 0 and h_ratio > 0:
                                # 使用原生 SQL 片段进行比例计算： width * h_ratio = height * w_ratio
                                where_clauses.append("(width * %s = height * %s AND width > 0 AND height > 0)")
                                params.extend([h_ratio, w_ratio])
                        except ValueError:
                            continue

                if where_clauses:
                    # 将多个比例条件用 OR 连接，例如：(条件1) OR (条件2)
                    sql_or = " OR ".join(where_clauses)
                    queryset = queryset.extra(where=[f"({sql_or})"], params=params)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        # 判断是否为管理员
        from models.models import User
        is_admin = False
        if hasattr(request, 'user') and isinstance(request.user, User):
            if request.user.role in ['admin', 'operator']:
                is_admin = True
        # 根据用户角色选择不同的查询优化策略
        if is_admin:
            # 管理员：使用详细序列化器，预加载关联数据
            queryset = queryset.prefetch_related('tags', 'category').select_related('customer_upload__customer')
        else:
            # 普通用户：使用轻量级序列化器
            queryset = queryset.prefetch_related('tags').only(
                'id', 'name', 'url', 'thumb_url', 'width', 'height', 'image_format',
                'has_watermark', 'is_live', 'is_hd', 'hot_score', 'like_count',
                'collect_count', 'download_count', 'view_count', 'created_at', 'audit_status'
            )
        order = request.query_params.get("order", "").lower()
        order_mapping = {
            "latest": "-created_at",
            "views": "-view_count",
            "downloads": "-download_count",
            "hot": "-hot_score",
        }
        if order in order_mapping:
            queryset = queryset.order_by(order_mapping[order])
        customer_id = self.get_serializer_context().get("customer_id")
        if customer_id:
            liked_ids = set(
                WallpaperLike.objects.filter(customer_id=customer_id)
                .values_list('wallpaper_id', flat=True)
            )
            collected_ids = set(
                WallpaperCollection.objects.filter(user_id=customer_id)
                .values_list('wallpaper_id', flat=True)
            )
        else:
            liked_ids = set()
            collected_ids = set()
        page = self.paginate_queryset(queryset)
        if page is not None:
            context = self.get_serializer_context()
            context['liked_wallpaper_ids'] = liked_ids
            context['collected_wallpaper_ids'] = collected_ids
            # 根据管理员身份选择序列化器
            if is_admin:
                serializer = WallpapersAdminListSerializer(page, many=True, context=context)
            else:
                serializer = WallpapersListSerializer(page, many=True, context=context)
            return self.get_paginated_response(serializer.data)
        context = self.get_serializer_context()
        context['liked_wallpaper_ids'] = liked_ids
        context['collected_wallpaper_ids'] = collected_ids
        # 根据管理员身份选择序列化器
        if is_admin:
            serializer = WallpapersAdminListSerializer(queryset, many=True, context=context)
        else:
            serializer = WallpapersListSerializer(queryset, many=True, context=context)

        return ApiResponse(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        获取壁纸详情，并自动增加浏览量
        """
        instance = self.get_object()
        Wallpapers.objects.filter(pk=instance.pk).update(
            view_count=F("view_count") + 1,
            hot_score=F("hot_score") + 10
        )
        instance.refresh_from_db(fields=["view_count", "hot_score"])
        ctx = self.get_serializer_context()
        ctx['include_detail_info'] = True
        serializer = self.get_serializer(instance, context=ctx)
        return ApiResponse(serializer.data)

    @extend_schema(
        summary="更新壁纸信息",
        description=(
            "管理员或上传者可以更新壁纸信息。"
            "如果 is_change=true 且提供 file，则更换图片并更新所有相关属性；"
            "否则只更新元数据字段（名称、描述、分类、标签等）。"
        ),
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "is_change": {"type": "boolean", "description": "是否更换图片（true=更换图片，false或不传=仅更新元数据）"},
                    "file": {"type": "string", "format": "binary", "description": "新图片文件（is_change=true 时必填）"},
                    "name": {"type": "string", "description": "壁纸名称"},
                    "description": {"type": "string", "description": "壁纸描述"},
                    "source_url": {"type": "string", "description": "来源链接"},
                    "has_watermark": {"type": "boolean", "description": "是否有水印"},
                    "is_hd": {"type": "boolean", "description": "是否高清"},
                    "is_live": {"type": "boolean", "description": "是否动态壁纸"},
                    "category_ids": {
                        "type": "string",
                        "description": "分类ID列表，逗号分隔，如 '1,3'"
                    },
                    "tag_ids": {
                        "type": "string",
                        "description": "标签ID列表，逗号分隔，如 '3677,3680'"
                    },
                    "audit_status": {
                        "type": "string",
                        "enum": ["pending", "approved", "rejected"],
                        "description": "审核状态（仅管理员可修改）"
                    },
                    "audit_remark": {"type": "string", "description": "审核备注（仅管理员）"}
                }
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {"$ref": "#/components/schemas/Wallpapers"},
                    "message": {"type": "string", "example": "更新成功"}
                }
            },
            400: "参数错误",
            403: "无权限",
            404: "壁纸不存在"
        }
    )
    def update(self, request, *args, **kwargs):
        """
        更新壁纸信息
        - 如果 is_change=true 且提供 file：更换图片并更新所有属性
        - 否则：只更新元数据字段
        - 管理员可修改审核状态
        """
        from django.db import transaction

        instance = self.get_object()

        # 判断是否更换图片
        is_change_param = request.data.get("is_change", "false")
        if isinstance(is_change_param, bool):
            is_change = is_change_param
        else:
            is_change = str(is_change_param).lower() == "true"

        # 如果是非管理员，不允许修改审核相关字段
        is_admin = False
        if hasattr(request, 'user') and request.user:
            from models.models import User
            if isinstance(request.user, User) and request.user.role in ['admin', 'operator', 'super_admin']:
                is_admin = True

        if not is_admin:
            request.data.pop('audit_status', None)
            request.data.pop('audit_remark', None)
            request.data.pop('audited_at', None)

        try:
            with transaction.atomic():
                if is_change:
                    # === 更换图片模式 ===
                    uploaded_file = request.FILES.get("file")
                    if not uploaded_file:
                        return ApiResponse(code=400, message="更换图片时必须上传文件 file")

                    # 处理文件上传
                    orig_name = uploaded_file.name or "image.jpg"
                    _, orig_ext = os.path.splitext(orig_name)
                    ext = orig_ext.lower()
                    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4"):
                        ext = ".jpg"

                    # 生成唯一的文件名
                    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
                    unique_id = uuid.uuid4().hex[:8]
                    unique_base = f"{timestamp}_{unique_id}"

                    # COS 路径
                    cos_key = f"wallpaper/{unique_base}{ext}"
                    thumb_cos_key = f"wallpaper/{unique_base}_thumb{ext}"
                    _ext_hint = ext.lstrip(".")

                    # 读取文件内容
                    try:
                        file_content = bytes_from_uploaded_image(uploaded_file, quality=100)
                    except Exception as e:
                        logger.error(f"读取上传文件失败: {e}", exc_info=True)
                        return ApiResponse(code=400, message=f"读取文件失败：{e}")

                    # 上传原图到 COS
                    cos_ret = upload_image_to_cos(file_content, cos_key)
                    if not cos_ret:
                        return ApiResponse(code=500, message="上传原图到云存储失败")

                    file_url = cos_ret["url"]

                    # 处理缩略图
                    if ext == ".mp4":
                        thumb_url = ""
                        w, h = 0, 0
                        pil_fmt = "mp4"
                    else:
                        try:
                            uploaded_file.seek(0)
                            thumb_content = bytes_from_uploaded_image(uploaded_file, quality=10)
                            thumb_ret = upload_image_to_cos(thumb_content, thumb_cos_key)
                            if thumb_ret:
                                thumb_url = thumb_ret["url"]
                            else:
                                thumb_url = file_url.rsplit(".", 1)[0] + "_thumb." + _ext_hint

                            w, h, pil_fmt = _image_meta_from_bytes(file_content)
                        except Exception as e:
                            logger.error(f"生成缩略图失败: {e}", exc_info=True)
                            thumb_url = file_url.rsplit(".", 1)[0] + "_thumb." + _ext_hint
                            w, h, pil_fmt = 0, 0, None

                    # 格式化图片格式
                    fmt = (pil_fmt or _ext_hint or "").lower()
                    if fmt == "jpeg":
                        fmt = "jpg"

                    # 自动判断是否高清
                    is_hd_param = request.data.get("is_hd")
                    if is_hd_param is not None:
                        new_is_hd = str(is_hd_param).lower() == "true"
                    else:
                        new_is_hd = w >= 1920 or h >= 1080 if (w and h) else False

                    # 自动判断是否动态壁纸
                    is_live_param = request.data.get("is_live")
                    if is_live_param is not None:
                        new_is_live = str(is_live_param).lower() == "true"
                    else:
                        new_is_live = (ext == ".mp4")

                    # 更新图片相关字段
                    instance.url = file_url[:500]
                    instance.thumb_url = thumb_url[:500] if thumb_url else None
                    instance.width = w or 0
                    instance.height = h or 0
                    instance.image_format = fmt[:20] if fmt else None
                    instance.is_hd = new_is_hd
                    instance.is_live = new_is_live

                # 更新其他字段（无论是否更换图片都可以更新）
                name = request.data.get("name")
                description = request.data.get("description")
                source_url = request.data.get("source_url")
                has_watermark = request.data.get("has_watermark")
                audit_status = request.data.get("audit_status")
                audit_remark = request.data.get("audit_remark")

                if name is not None:
                    instance.name = str(name)[:200]
                if description is not None:
                    instance.description = str(description).strip() or None
                if source_url is not None:
                    instance.source_url = str(source_url)[:500] or None
                if has_watermark is not None and not is_change:
                    # 如果没换图片，可以手动修改 has_watermark
                    instance.has_watermark = str(has_watermark).lower() == "true"
                elif has_watermark is not None and is_change:
                    # 如果换了图片，也可以手动覆盖
                    instance.has_watermark = str(has_watermark).lower() == "true"

                if audit_status is not None:
                    if audit_status not in ['pending', 'approved', 'rejected']:
                        return ApiResponse(code=400, message="审核状态无效")
                    instance.audit_status = audit_status
                    instance.audited_at = timezone.now() if audit_status in ['approved', 'rejected'] else None
                if audit_remark is not None:
                    instance.audit_remark = str(audit_remark).strip() or None

                instance.save()

                # 提取分类和标签ID
                category_ids = request.data.get("category_ids")
                tag_ids = request.data.get("tag_ids")

                # 更新分类（如果提供）
                if category_ids is not None:
                    if isinstance(category_ids, list):
                        instance.category.set(category_ids)
                    elif isinstance(category_ids, str):
                        cat_id_list = [int(cid.strip()) for cid in category_ids.split(',') if cid.strip().isdigit()]
                        instance.category.set(cat_id_list)

                # 更新标签（如果提供）
                if tag_ids is not None:
                    if isinstance(tag_ids, list):
                        instance.tags.set(tag_ids)
                    elif isinstance(tag_ids, str):
                        tag_id_list = [int(tid.strip()) for tid in tag_ids.split(',') if tid.strip().isdigit()]
                        instance.tags.set(tag_id_list)

                # 刷新实例以获取最新数据
                instance.refresh_from_db()

                # 返回更新后的完整数据
                ctx = self.get_serializer_context()
                ctx['include_detail_info'] = True
                response_serializer = WallpapersSerializer(instance, context=ctx)
                return ApiResponse(
                    data=response_serializer.data,
                    message="更换图片并更新成功" if is_change else "更新成功"
                )
        except Exception as e:
            logger.error(f"更新壁纸失败: {e}", exc_info=True)
            return ApiResponse(code=500, message=f"更新失败：{str(e)}")

    @extend_schema(
        summary="审核通过单张壁纸(Admin)",
        request=None,
        responses={200: {"type": "object", "properties": {"code": {"type": "integer"}, "message": {"type": "string"}}}}
    )
    @action(detail=True, methods=['post'], url_path='audit/approve')
    def audit_approve(self, request, pk=None):
        """
        审核通过壁纸
        仅管理员可用
        """
        from django.utils import timezone
        try:
            wallpaper = Wallpapers.objects.get(id=pk)
        except Wallpapers.DoesNotExist:
            return ApiResponse(code=404, message="壁纸不存在")
        wallpaper.audit_status = 'approved'
        wallpaper.audited_at = timezone.now()
        wallpaper.audit_remark = request.data.get('remark', '')
        wallpaper.save(update_fields=['audit_status', 'audited_at', 'audit_remark'])
        logger.info(f"壁纸 #{pk} 审核通过 by {request.user.username}")
        return ApiResponse(message="审核通过")

    @extend_schema(
        summary="审核拒绝单张(Admin)",
        request=None,
        responses={200: {"type": "object", "properties": {"code": {"type": "integer"}, "message": {"type": "string"}}}}
    )
    @action(detail=True, methods=['post'], url_path='audit/reject')
    def audit_reject(self, request, pk=None):
        """
        审核拒绝壁纸
        仅管理员可用
        """
        from django.utils import timezone
        try:
            wallpaper = Wallpapers.objects.get(id=pk)
        except Wallpapers.DoesNotExist:
            return ApiResponse(code=404, message="壁纸不存在")

            # 获取拒绝原因
        remark = request.data.get('remark', '')
        wallpaper.audit_status = 'rejected'
        wallpaper.audited_at = timezone.now()
        wallpaper.audit_remark = remark
        wallpaper.save(update_fields=['audit_status', 'audited_at', 'audit_remark'])
        logger.info(f"壁纸 #{pk} 审核拒绝 by {request.user.username}, 原因: {remark}")
        return ApiResponse(message="审核拒绝")

    @extend_schema(
        summary="批量审核通过(Admin)",
        request=OpenApiRequest(
            request={"wallpaper_ids": [1, 2, 3]},
            examples=[
                OpenApiExample(
                    name="审核通过示例",
                    value={"wallpaper_ids": [805471, 805472, 805473]},
                    request_only=True
                )
            ]
        ),
        responses={200: {"type": "object", "properties": {"code": {"type": "integer"}, "data": {"type": "object"},
                                                          "message": {"type": "string"}}}}
    )
    @action(detail=False, methods=['post'], url_path='audit/batch-approve')
    def audit_batch_approve(self, request):
        """
        批量审核通过
        仅管理员可用
        """
        from django.utils import timezone
        wallpaper_ids = request.data.get('wallpaper_ids', [])
        if not wallpaper_ids:
            return ApiResponse(code=400, message="请提供壁纸ID列表")
        count = Wallpapers.objects.filter(id__in=wallpaper_ids).update(
            audit_status='approved',
            audited_at=timezone.now()

        )
        logger.info(f"批量审核通过 {count} 张壁纸 by {request.user.username}")
        return ApiResponse(data={'count': count}, message=f"已审核通过 {count} 张壁纸")

    @extend_schema(
        summary="批量审核拒绝(Admin)",
        request=OpenApiRequest(
            request={"wallpaper_ids": [1, 2, 3], "remark": "拒绝原因"},
            examples=[
                OpenApiExample(
                    name="审核拒绝示例",
                    value={"wallpaper_ids": [805471, 805472, 805473], "remark": "图片模糊不清"},
                    request_only=True
                )
            ]
        ),
        responses={200: {"type": "object", "properties": {"code": {"type": "integer"}, "data": {"type": "object"},
                                                          "message": {"type": "string"}}}}
    )
    @action(detail=False, methods=['post'], url_path='audit/batch-reject')
    def audit_batch_reject(self, request):
        """
        批量审核拒绝
        仅管理员可用
        """
        from django.utils import timezone
        wallpaper_ids = request.data.get('wallpaper_ids', [])
        remark = request.data.get('remark', '')

        count = Wallpapers.objects.filter(id__in=wallpaper_ids).update(
            audit_status='rejected',
            audited_at=timezone.now(),
            audit_remark=remark
        )
        logger.info(f"批量审核拒绝 {count} 张壁纸 by {request.user.username}, 原因: {remark}")
        return ApiResponse(data={'count': count}, message=f"已审核拒绝 {count} 张壁纸")


    @extend_schema(
        summary="猜你喜欢",
        description="根据传入的壁纸 ID，推荐具有相同标签的其他壁纸（按匹配标签数量排序）",
        parameters=[
            OpenApiParameter(name="wallpaper_id", type=int, required=True, description="壁纸 ID"),
            OpenApiParameter(name="limit", type=int, required=False, description="返回数量限制，默认 10"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "message": {"type": "string", "example": "推荐成功"},
                    "data": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Wallpapers"}
                    }
                }
            },
            404: {"description": "壁纸不存在"}
        }
    )
    @action(detail=False, methods=['get'], url_path='guess_you_like')
    def guess_you_like(self, request):
        """
        猜你喜欢：根据传入的壁纸 ID，推荐具有相同标签的其他壁纸
        """
        from django.db.models import Count, Q
        wallpaper_id = request.query_params.get("wallpaper_id")
        limit = int(request.query_params.get("limit", 10))
        if not wallpaper_id:
            return ApiResponse(code=400, message="请提供壁纸 ID")
        try:
            # 获取指定壁纸及其标签
            target_wallpaper = Wallpapers.objects.prefetch_related('tags').get(id=wallpaper_id)
            target_tags = target_wallpaper.tags.all()
            if not target_tags.exists():
                # 如果该壁纸没有标签，返回空列表
                return ApiResponse(data=[], message="该壁纸没有标签，无法推荐")
            target_tag_ids = list(target_tags.values_list('id', flat=True))
            # 查询具有相同标签的其他壁纸（排除自身）
            # 使用 annotate 计算匹配的标签数量
            recommended_wallpapers = Wallpapers.objects.filter(
                tags__id__in=target_tag_ids
            ).exclude(
                id=wallpaper_id
            ).annotate(
                match_count=Count('tags', filter=Q(tags__id__in=target_tag_ids))
            ).order_by(
                '-match_count', '-hot_score', '-created_at'
            ).distinct()[:limit]
            # 序列化返回数据
            serializer = self.get_serializer(recommended_wallpapers, many=True)
            return ApiResponse(data=serializer.data, message=f"为您找到{len(serializer.data)}个相关推荐")
        except Wallpapers.DoesNotExist:
            return ApiResponse(code=404, message="指定的壁纸不存在")
        except Exception as e:
            logger.error(f"猜你喜欢推荐失败：{str(e)}", exc_info=True)
            return ApiResponse(code=500, message=f"推荐失败：{str(e)}")

    @extend_schema(summary="点赞/取消点赞（需客户 Token）")
    @action(
        detail=False,
        methods=["post"],
        url_path="toggle-like",
        permission_classes=[IsCustomerTokenValid],
    )
    def toggle_like(self, request):
        wid = request.data.get("wallpaper_id")
        if not wid:
            return ApiResponse(code=400, message="请提供 wallpaper_id")
        try:
            wid = int(wid)
        except (TypeError, ValueError):
            return ApiResponse(code=400, message="wallpaper_id 无效")
        cid = request.user.id
        try:
            with transaction.atomic():
                wp = Wallpapers.objects.select_for_update().get(pk=wid)
                like, created = WallpaperLike.objects.get_or_create(
                    customer_id=cid, wallpaper=wp
                )
                if created:
                    Wallpapers.objects.filter(pk=wp.pk).update(
                        like_count=F("like_count") + 1,
                        hot_score=F("hot_score") + 50  # 点赞一次加 50 分
                    )
                    liked = True
                    message = "点赞成功"
                    
                    # 发送点赞通知（如果不是给自己点赞）
                    try:
                        upload_record = getattr(wp, 'customer_upload', None)
                        if upload_record and upload_record.customer_id != cid:
                            from App.view.notifications.notification_center import NotificationCenter
                            NotificationCenter.send_like(
                                recipient_id=upload_record.customer_id,
                                sender_id=cid,
                                wallpaper_id=wp.id,
                                wallpaper_name=wp.name[:50]
                            )
                    except Exception:
                        pass
                else:
                    like.delete()
                    message = "取消点赞成功"
                    Wallpapers.objects.filter(pk=wp.pk).update(
                        like_count=Greatest(F("like_count") - 1, 0),
                        hot_score=Greatest(F("hot_score") - 50, 0)  # 取消点赞减 50 分
                    )
                    liked = False
                wp.refresh_from_db(fields=["like_count"])
        except Wallpapers.DoesNotExist:
            return ApiResponse(code=404, message="壁纸不存在")
        return ApiResponse(
            data={"liked": liked, "like_count": wp.like_count},
            message=message,
        )

    @extend_schema(summary="收藏/取消收藏（需客户 Token）")
    @action(
        detail=False,
        methods=["post"],
        url_path="toggle-collect",
        permission_classes=[IsCustomerTokenValid],
    )
    def toggle_collect(self, request):
        wid = request.data.get("wallpaper_id")
        if not wid:
            return ApiResponse(code=400, message="请提供 wallpaper_id")
        try:
            wid = int(wid)
        except (TypeError, ValueError):
            return ApiResponse(code=400, message="wallpaper_id 无效")
        cid = request.user.id
        try:
            with transaction.atomic():
                wp = Wallpapers.objects.select_for_update().get(pk=wid)
                row, created = WallpaperCollection.objects.get_or_create(
                    user_id=cid, wallpaper=wp
                )
                if created:
                    Wallpapers.objects.filter(pk=wp.pk).update(
                        collect_count=F("collect_count") + 1,
                        hot_score=F("hot_score") + 200  # 收藏一次加 200 分
                    )
                    CustomerUser.objects.filter(pk=cid).update(
                        collection_count=F("collection_count") + 1
                    )
                    collected = True
                else:
                    row.delete()
                    Wallpapers.objects.filter(pk=wp.pk).update(
                        collect_count=Greatest(F("collect_count") - 1, 0),
                        hot_score=Greatest(F("hot_score") - 200, 0)  # 取消收藏减 200 分
                    )
                    CustomerUser.objects.filter(pk=cid).update(
                        collection_count=Greatest(F("collection_count") - 1, 0)
                    )
                    collected = False
                wp.refresh_from_db(fields=["collect_count"])
        except Wallpapers.DoesNotExist:
            return ApiResponse(code=404, message="壁纸不存在")
        return ApiResponse(
            data={"collected": collected, "collect_count": wp.collect_count},
            message="操作成功",
        )
        # 2) 在 WallpapersViewSet 里新增批量删除接口
    @extend_schema(
        summary="批量删除壁纸(Admin)",
        description="根据 wallpaper_ids 批量删除壁纸",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "wallpaper_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "壁纸ID列表，如 [1,2,3,4]"
                    }
                },
                "required": ["wallpaper_ids"],
                "example": {"wallpaper_ids": [1, 2, 3, 4]}
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
    @action(detail=False, methods=['post'], url_path='batch-delete')
    def batch_delete(self, request):
        wallpaper_ids = request.data.get('wallpaper_ids', [])
        if not isinstance(wallpaper_ids, list) or not wallpaper_ids:
            return ApiResponse(code=400, message="wallpaper_ids 必须是非空数组")

        valid_ids = []
        for item in wallpaper_ids:
            try:
                valid_ids.append(int(item))
            except (TypeError, ValueError):
                return ApiResponse(code=400, message="wallpaper_ids 只能包含整数ID")
        # 去重，避免重复删除
        valid_ids = list(set(valid_ids))
        queryset = Wallpapers.objects.filter(id__in=valid_ids)
        deleted_count = queryset.count()
        if deleted_count == 0:
            return ApiResponse(code=404, message="未找到可删除的壁纸")
        queryset.delete()
        return ApiResponse(
            data={"deleted_count": deleted_count, "wallpaper_ids": valid_ids},
            message=f"批量删除成功，共删除 {deleted_count} 条"
        )
    @extend_schema(summary="记录一次下载并返回累计下载量（需客户 Token）")
    @action(
        detail=False,
        methods=["post"],
        url_path="record-download",
        permission_classes=[IsCustomerTokenValid],
    )
    def record_download(self, request):
        wid = request.data.get("wallpaper_id")
        if not wid:
            return ApiResponse(code=400, message="请提供 wallpaper_id")
        try:
            wid = int(wid)
        except (TypeError, ValueError):
            return ApiResponse(code=400, message="wallpaper_id 无效")
        try:
            with transaction.atomic():
                wp = Wallpapers.objects.select_for_update().get(pk=wid)
                Wallpapers.objects.filter(pk=wp.pk).update(
                    download_count=F("download_count") + 1,
                    hot_score=F("hot_score") + 400
                )
                wp.refresh_from_db(fields=["download_count", "hot_score"])
        except Wallpapers.DoesNotExist:
            return ApiResponse(code=404, message="壁纸不存在")
        return ApiResponse(
            data={"download_count": wp.download_count},
            message="记录成功",
        )
    @extend_schema(
        summary="我的收藏列表（仅需客户 Token）",
        parameters=[
            OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码"),
            OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量"),
            OpenApiParameter(name="platform", type=str, required=False, description="平台筛选：PC 或 PHONE"),
        ],
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="my-collections",
        permission_classes=[IsCustomerTokenValid],
    )
    def my_collections(self, request):
        token = request.headers.get("token")
        is_valid, customer_id = CustomTokenTool.verify_customer_token(token)
        if not is_valid or not customer_id:
            return ApiResponse(code=401, message="客户 Token 无效或已过期")

        qs = (
            WallpaperCollection.objects
            .filter(user_id=customer_id)
            .select_related("wallpaper")
            .prefetch_related("wallpaper__tags", "wallpaper__category")
            .order_by("-created_at")
        )

        platform = request.query_params.get("platform", "").upper()
        if platform == 'PC':
            qs = qs.filter(wallpaper__category__id=1)
        elif platform == 'PHONE':
            qs = qs.filter(wallpaper__category__id=2)

        page = self.paginate_queryset(qs)
        if page is not None:
            data = CollectionItemSerializer(
                page,
                many=True,
                context=self.get_serializer_context(),
            ).data
            return self.get_paginated_response(data)
        data = CollectionItemSerializer(
            qs,
            many=True,
            context=self.get_serializer_context(),
        ).data
        return ApiResponse(data=data, message="获取收藏列表成功")


    @extend_schema(
        summary="管理员上传壁纸",
        description=(
            "管理员上传壁纸到 COS，自动处理原图和缩略图。"
            "支持设置分类、标签、审核状态等完整字段。"
        ),
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "format": "binary", "description": "壁纸文件（必填）"},
                    "name": {"type": "string", "description": "壁纸名称（必填）"},
                    "description": {"type": "string", "description": "壁纸描述（可选）"},
                    "source_url": {"type": "string", "description": "来源链接（可选）"},
                    "has_watermark": {"type": "boolean", "description": "是否有水印（可选，默认 false）"},
                    "is_hd": {"type": "boolean", "description": "是否高清（可选，默认自动判断）"},
                    "is_live": {"type": "boolean", "description": "是否动态壁纸（可选，默认根据文件扩展名判断）"},
                    "category_ids": {
                        "type": "string",
                        "description": "分类 ID 列表，逗号分隔，如 '1,3' 表示电脑+静态（可选）"
                    },
                    "tag_ids": {
                        "type": "string",
                        "description": "标签 ID 列表，逗号分隔，如 '3677,3680'（可选）"
                    },
                    "audit_status": {
                        "type": "string",
                        "enum": ["pending", "approved", "rejected"],
                        "description": "审核状态（可选，默认 pending）"
                    },
                    "audit_remark": {"type": "string", "description": "审核备注（可选）"}
                },
                "required": ["file", "name"]
            }
        },
        responses={
            201: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 201},
                    "data": {"$ref": "#/components/schemas/Wallpapers"},
                    "message": {"type": "string", "example": "上传成功"}
                }
            },
            400: "参数错误",
            500: "服务器错误"
        }
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="upload-admin",
        permission_classes=[IsAdmin],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_admin(self, request):
        """
        管理员上传壁纸
        - 自动处理原图和缩略图
        - 支持设置分类、标签、审核状态
        - 需要管理员权限
        """
        from django.db import transaction

        # 验证文件
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return ApiResponse(code=400, message="请上传文件 file")
        # 验证必填字段
        name = (request.data.get("name") or "").strip()
        if not name:
            return ApiResponse(code=400, message="请提供壁纸名称 name")
        # 解析可选字段
        description = (request.data.get("description") or "").strip() or None
        source_url = (request.data.get("source_url") or "").strip() or None
        has_watermark = request.data.get("has_watermark", "false").lower() == "true"
        # 解析 is_hd 和 is_live（可选，不传则自动判断）
        is_hd_param = request.data.get("is_hd")
        is_live_param = request.data.get("is_live")
        audit_status = request.data.get("audit_status", "pending").strip()
        audit_remark = (request.data.get("audit_remark") or "").strip() or None
        # 验证审核状态
        if audit_status and audit_status not in ['pending', 'approved', 'rejected']:
            return ApiResponse(code=400, message="审核状态无效，可选值：pending/approved/rejected")
        # 解析分类和标签
        category_ids = _parse_tag_ids(request.data.get("category_ids"))
        tag_ids = _parse_tag_ids(request.data.get("tag_ids"))
        # 处理文件扩展名
        orig_name = uploaded_file.name or "image.jpg"
        _, orig_ext = os.path.splitext(orig_name)
        ext = orig_ext.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4"):
            ext = ".jpg"
        # 生成唯一的文件名
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        unique_base = f"{timestamp}_{unique_id}"
        # COS 路径
        cos_key = f"wallpaper/{unique_base}{ext}"
        thumb_cos_key = f"wallpaper/{unique_base}_thumb{ext}"
        _ext_hint = ext.lstrip(".")
        # 读取文件内容
        try:
            file_content = bytes_from_uploaded_image(uploaded_file, quality=100)
        except Exception as e:
            logger.error(f"读取上传文件失败: {e}", exc_info=True)
            return ApiResponse(code=400, message=f"读取文件失败：{e}")
        # 上传原图到 COS
        cos_ret = upload_image_to_cos(file_content, cos_key)
        if not cos_ret:
            return ApiResponse(code=500, message="上传原图到云存储失败，请检查 COS 配置")
        file_url = cos_ret["url"]
        # 处理缩略图
        if ext == ".mp4":
            # 视频文件不生成缩略图
            thumb_url = ""
            w, h = 0, 0
            pil_fmt = "mp4"
        else:
            # 图片文件生成缩略图
            try:
                uploaded_file.seek(0)
                thumb_content = bytes_from_uploaded_image(uploaded_file, quality=10)
                thumb_ret = upload_image_to_cos(thumb_content, thumb_cos_key)
                if thumb_ret:
                    thumb_url = thumb_ret["url"]
                else:
                    thumb_url = file_url.rsplit(".", 1)[0] + "_thumb." + _ext_hint

                # 获取图片尺寸
                w, h, pil_fmt = _image_meta_from_bytes(file_content)
            except Exception as e:
                logger.error(f"生成缩略图失败: {e}", exc_info=True)
                thumb_url = file_url.rsplit(".", 1)[0] + "_thumb." + _ext_hint
                w, h, pil_fmt = 0, 0, None

        # 格式化图片格式
        fmt = (pil_fmt or _ext_hint or "").lower()
        if fmt == "jpeg":
            fmt = "jpg"

        # 自动判断是否高清（如果未手动指定）
        if is_hd_param is not None:
            is_hd = is_hd_param.lower() == "true"
        else:
            is_hd = w >= 1920 or h >= 1080 if (w and h) else False

        # 自动判断是否动态壁纸（如果未手动指定）
        if is_live_param is not None:
            is_live = is_live_param.lower() == "true"
        else:
            is_live = (ext == ".mp4")
        try:
            with transaction.atomic():
                # 创建壁纸记录
                wp = Wallpapers.objects.create(
                    name=name[:200],
                    url=file_url[:500],
                    thumb_url=thumb_url[:500] if thumb_url else None,
                    width=w or 0,
                    height=h or 0,
                    image_format=(fmt[:20] if fmt else None),
                    source_url=source_url[:500] if source_url else None,
                    description=description,
                    has_watermark=has_watermark,
                    is_hd=is_hd,
                    is_live=is_live,
                    audit_status=audit_status if audit_status else 'pending',
                    audit_remark=audit_remark,
                    audited_at=timezone.now() if audit_status in ['approved', 'rejected'] else None
                )

                # 添加分类（如果提供了）
                if category_ids:
                    wp.category.set(category_ids)

                # 添加标签（如果提供了）
                if tag_ids:
                    tag_objs = []
                    for tid in tag_ids:
                        t = WallpaperTag.objects.filter(pk=tid).first()
                        if t:
                            tag_objs.append(t)
                    wp.tags.set(tag_objs)

            # 返回完整的壁纸信息
            ctx = self.get_serializer_context()
            ctx['include_detail_info'] = True
            serializer = WallpapersSerializer(wp, context=ctx)

            return ApiResponse(
                data=serializer.data,
                message="上传成功",
                code=201
            )
        except Exception as e:
            logger.error(f"保存壁纸记录失败: {e}", exc_info=True)
            return ApiResponse(code=500, message=f"保存壁纸失败：{e}")

    @extend_schema(
        summary="我的上传列表（仅需客户 Token）",
        description="查看当前用户上传的所有壁纸记录，支持分页和平台筛选",
        parameters=[
            OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码"),
            OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量"),
            OpenApiParameter(name="platform", type=str, required=False, description="平台筛选：PC 或 PHONE"),
        ],
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="my-uploads",
        permission_classes=[IsCustomerTokenValid],
    )
    def my_uploads(self, request):
        token = request.headers.get("token")
        is_valid, customer_id = CustomTokenTool.verify_customer_token(token)
        if not is_valid or not customer_id:
            return ApiResponse(code=401, message="客户 Token 无效或已过期")

        # 通过 CustomerWallpaperUpload 关联查询壁纸
        qs = (
            CustomerWallpaperUpload.objects
            .filter(customer_id=customer_id)
            .select_related("wallpaper")
            .prefetch_related("wallpaper__tags", "wallpaper__category")
            .order_by("-created_at")
        )

        platform = request.query_params.get("platform", "").upper()
        if platform == 'PC':
            qs = qs.filter(wallpaper__category__id=1)
        elif platform == 'PHONE':
            qs = qs.filter(wallpaper__category__id=2)

        page = self.paginate_queryset(qs)
        if page is not None:
            # 序列化壁纸数据
            wallpapers = [item.wallpaper for item in page]
            serializer = WallpapersSerializer(
                wallpapers,
                many=True,
                context=self.get_serializer_context(),
            )
            return self.get_paginated_response(serializer.data)

        wallpapers = [item.wallpaper for item in qs]
        data = WallpapersSerializer(
            wallpapers,
            many=True,
            context=self.get_serializer_context(),
        ).data
        return ApiResponse(data=data, message="获取上传列表成功")

    @extend_schema(
        summary="精选壁纸（按平台推荐）",
        description="根据平台（PC/手机）返回精选壁纸，支持自定义数量（5-10张）",
        parameters=[
            OpenApiParameter(name="platform", type=str, required=True, description="平台：PC 或 PHONE"),
            OpenApiParameter(name="limit", type=int, required=False, description="返回数量，默认 6，范围 5-10"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "message": {"type": "string", "example": "精选壁纸获取成功"},
                    "data": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Wallpapers"}
                    }
                }
            },
            400: {"description": "参数错误"}
        }
    )
    @action(detail=False, methods=['get'], url_path='featured')
    def featured(self, request):
        """
        精选壁纸：根据平台返回高质量壁纸，优先应用推荐策略
        策略匹配顺序：platform -> all -> 默认平台分类
        """
        platform = request.query_params.get("platform", "").upper()
        if platform not in ['PC', 'PHONE', 'ALL']:
            return ApiResponse(code=400, message="平台参数错误，请输入 PC、PHONE 或 ALL")
        try:
            limit = int(request.query_params.get("limit", 6))
        except (TypeError, ValueError):
            limit = 6

        from django.utils import timezone
        now = timezone.now()

        matched_strategy = None

        if platform in ['PC', 'PHONE']:
            platform_strategies = RecommendStrategy.objects.filter(
                platform=platform.lower(),
                strategy_type="home",
                status="active",
            ).order_by("-priority", "-created_at")

            for item in platform_strategies:
                if item.start_time and now < item.start_time:
                    continue
                if item.end_time and now > item.end_time:
                    continue
                matched_strategy = item
                break

            if not matched_strategy:
                all_strategies = RecommendStrategy.objects.filter(
                    platform="all",
                    strategy_type="home",
                    status="active",
                ).order_by("-priority", "-created_at")

                for item in all_strategies:
                    if item.start_time and now < item.start_time:
                        continue
                    if item.end_time and now > item.end_time:
                        continue
                    matched_strategy = item
                    break
        else:
            all_strategies = RecommendStrategy.objects.filter(
                platform="all",
                strategy_type="home",
                status="active",
            ).order_by("-priority", "-created_at")

            for item in all_strategies:
                if item.start_time and now < item.start_time:
                    continue
                if item.end_time and now > item.end_time:
                    continue
                matched_strategy = item
                break
        if matched_strategy and matched_strategy.wallpaper_ids:
            wallpaper_ids = matched_strategy.wallpaper_ids
            if matched_strategy.content_limit and matched_strategy.content_limit > 0:
                wallpaper_ids = wallpaper_ids[:matched_strategy.content_limit]

            wallpaper_map = Wallpapers.objects.filter(id__in=wallpaper_ids).in_bulk()
            ordered_wallpapers = [wallpaper_map[w_id] for w_id in wallpaper_ids if w_id in wallpaper_map]

            serializer = self.get_serializer(ordered_wallpapers, many=True)
            return ApiResponse(
                data=serializer.data,
                message="精选壁纸获取成功（来自推荐策略）"
            )
        if platform == 'PC':
            queryset = Wallpapers.objects.filter(
                category__id=1,
                is_hd=True
            ).distinct().order_by('-hot_score', '-like_count', '-created_at')[:limit]
        elif platform == 'PHONE':
            queryset = Wallpapers.objects.filter(
                category__id=2,
                is_hd=True
            ).distinct().order_by('-hot_score', '-like_count', '-created_at')[:limit]
        else:
            queryset = Wallpapers.objects.filter(
                is_hd=True
            ).distinct().order_by('-hot_score', '-like_count', '-created_at')[:limit]

        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="精选壁纸获取成功")

    @extend_schema(
        summary="上传个人壁纸到 COS（person_wallpaper/，质量 100）",
        description=(
                "需客户 Token（CToken）。multipart：file、title（文件名主体）；"
                "可选 description；tag_ids（逗号或 JSON 数组）；tag_names（新标签，逗号或 JSON 数组）。"
        ),
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "format": "binary"},
                    "title": {"type": "string", "description": "展示名/文件名主体（不含扩展名）"},
                    "platform": {"type": "string", "description": "平台：PC 或 PHONE"},
                    "description": {"type": "string"},
                    "tag_ids": {"type": "string", "description": "已有标签 id，如 1,2 或 [1,2]"},
                    "tag_names": {"type": "string", "description": "新标签名称，多个用逗号或 JSON 数组"},
                },
                "required": ["file", "title"],
            }
        },
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="upload-person",
        permission_classes=[IsCustomerTokenValid],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_person(self, request):
        token = request.headers.get("token")
        is_valid, customer_id = CustomTokenTool.verify_customer_token(token)
        if not is_valid or not customer_id:
            return ApiResponse(code=401, message="客户 Token 无效或已过期")

        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return ApiResponse(code=400, message="请上传文件 file")

        title = (request.data.get("title") or "").strip()
        if not title:
            return ApiResponse(code=400, message="请提供 title")

        platform = (request.data.get("platform") or "").upper()
        if platform not in ['PC', 'PHONE', 'ALL']:
            return ApiResponse(code=400, message="平台参数错误，请输入 PC 或 PHONE")

        description = (request.data.get("description") or "").strip() or None
        tag_ids = _parse_tag_ids(request.data.get("tag_ids"))
        tag_names = _parse_tag_names(request.data.get("tag_names"))

        orig_name = uploaded_file.name or "image.jpg"
        _, orig_ext = os.path.splitext(orig_name)
        orig_ext = orig_ext.lower()

        token_suffix = token[-8:] if token and len(token) >= 8 else (token or "00000000")[-8:].ljust(8, '0')
        name_part, ext = os.path.splitext(orig_name)
        ext = ext.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4"):
            ext = ".jpg"

        safe_title = (title or "").strip()
        for ch in '<>:"|?*\\/\x00':
            safe_title = safe_title.replace(ch, "")
        safe_title = safe_title.strip(" .")[:180]
        if not safe_title:
            safe_title = uuid.uuid4().hex[:12]

        unique_base = f"{token_suffix}_{name_part}"
        cos_key = f"person_wallpaper/{unique_base}{ext}"
        thumb_cos_key = f"person_wallpaper/{unique_base}_thumb{ext}"
        _ext_hint = ext.lstrip(".")

        try:
            file_content = bytes_from_uploaded_image(uploaded_file, quality=100)
        except Exception as e:
            logger.error(f"读取上传文件失败: {e}", exc_info=True)
            return ApiResponse(code=400, message=f"读取文件失败：{e}")

        cos_ret = upload_image_to_cos(file_content, cos_key)
        if not cos_ret:
            return ApiResponse(code=500, message="上传到云存储失败，请检查 COS 配置")

        file_url = cos_ret["url"]

        if ext == ".mp4":
            thumb_url = ""
            w, h = 0, 0
            pil_fmt = "mp4"
        else:
            uploaded_file.seek(0)
            thumb_content = bytes_from_uploaded_image(uploaded_file, quality=10)
            thumb_ret = upload_image_to_cos(thumb_content, thumb_cos_key)
            if thumb_ret:
                thumb_url = thumb_ret["url"]
            else:
                thumb_url = file_url.rsplit(".", 1)[0] + "_thumb." + _ext_hint
            w, h, pil_fmt = _image_meta_from_bytes(file_content)

        fmt = (pil_fmt or _ext_hint or "").lower()
        if fmt == "jpeg":
            fmt = "jpg"
        is_hd = w >= 1920 or h >= 1080 if (w and h) else False

        is_live = (ext == ".mp4")
        # 确定平台分类 (1:电脑, 2:手机)
        platform_cat_id = 1 if platform == 'PC' else 2
        # 确定类型分类 (3:静态, 4:动态), 默认 3
        type_cat_id = 4 if is_live else 3

        try:
            with transaction.atomic():
                wp = Wallpapers.objects.create(
                    name=title[:200],
                    url=file_url[:500],
                    thumb_url=thumb_url[:500] if thumb_url else None,
                    width=w or 0,
                    height=h or 0,
                    image_format=(fmt[:20] if fmt else None),
                    description=description,
                    has_watermark=False,
                    is_hd=is_hd,
                    is_live=is_live,
                )
                # 同时添加平台分类和类型分类
                wp.category.add(platform_cat_id, type_cat_id)

                CustomerWallpaperUpload.objects.create(
                    wallpaper=wp,
                    customer_id=customer_id,
                    cos_key=cos_key[:500] if cos_key else None,
                )
                CustomerUser.objects.filter(pk=customer_id).update(
                    upload_count=F("upload_count") + 1
                )
                tag_objs = []
                for tid in tag_ids:
                    t = WallpaperTag.objects.filter(pk=tid).first()
                    if t:
                        tag_objs.append(t)
                for nm in tag_names:
                    nm_clean = nm[:50].strip()
                    if not nm_clean:
                        continue
                    t, _ = WallpaperTag.objects.get_or_create(name=nm_clean)
                    tag_objs.append(t)
                dedup = list({t.id: t for t in tag_objs}.values())
                wp.tags.set(dedup)
        except Exception as e:
            logger.error(f"保存壁纸记录失败: {e}", exc_info=True)
            return ApiResponse(code=500, message=f"保存壁纸失败：{e}")
        data = WallpapersSerializer(
            wp, context=self.get_serializer_context()
        ).data
        return ApiResponse(
            data={
                **data,
                "cos_key": cos_key,
                "url": file_url,
            },
            message="上传成功",
        )

    @extend_schema(
        summary="标签联想/建议（可选关键词）",
        parameters=[
            OpenApiParameter(name="q", type=str, required=False, description="关键词"),
            OpenApiParameter(name="limit", type=int, required=False, description="返回条数，默认 20，最大 50"),
        ],
    )
    @action(detail=False, methods=["get"], url_path="suggest-tags")
    def suggest_tags(self, request):
        q = (request.query_params.get("q") or "").strip()
        try:
            limit = int(request.query_params.get("limit", 20))
        except ValueError:
            limit = 20
        limit = max(1, min(50, limit))
        qs = WallpaperTag.objects.all().order_by("-created_at")
        if q:
            qs = qs.filter(name__icontains=q)
        qs = qs[:limit]
        data = [{"id": t.id, "name": t.name} for t in qs]
        return ApiResponse(data=data, message="ok")

    @extend_schema(
        summary="获取所有壁纸分类",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "message": {"type": "string", "example": "分类获取成功"},
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer", "example": 1},
                                "name": {"type": "string", "example": "静态"},
                                "desc": {"type": "string", "example": "静态壁纸分类"},
                                "sort": {"type": "integer", "example": 1},
                                "created_at": {"type": "string", "format": "date-time"}
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='categories')
    def categories(self, request):
        """
        获取所有壁纸分类列表
        """
        categories = WallpaperCategory.objects.all().order_by('sort', '-created_at')
        data = [
            {
                'id': cat.id,
                'name': cat.name,
                'desc': cat.desc or '',
                'sort': cat.sort,
                'created_at': cat.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            for cat in categories
        ]
        return ApiResponse(data=data, message="分类获取成功")

    @extend_schema(
        summary="批量导入壁纸数据",
        description="通过上传 Excel 文件批量导入壁纸数据",
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "format": "binary", "description": "Excel 文件 (.xlsx)"}
                },
                "required": ["file"]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "message": {"type": "string", "example": "导入成功"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "success_count": {"type": "integer", "example": 100},
                            "fail_count": {"type": "integer", "example": 0},
                            "errors": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                }
            },
            400: {"description": "文件格式错误或数据异常"},
            500: {"description": "服务器内部错误"}
        }
    )
    @action(detail=False, methods=['post'], url_path='batch-import')
    def batch_import(self, request):
        """
        批量导入壁纸数据
        Excel 格式要求：
        - 第一行：表头（name, url）
        - 从第二行开始：数据行
        """
        from openpyxl import load_workbook

        # 1. 获取上传的文件
        file = request.FILES.get('file')
        if not file:
            return ApiResponse(code=400, message=_("请上传 Excel 文件"))

        # 2. 验证文件格式
        if not file.name.endswith('.xlsx'):
            return ApiResponse(code=400, message=_("仅支持.xlsx 格式的 Excel 文件"))

        try:
            # 3. 读取 Excel 文件
            wb = load_workbook(file, data_only=True)
            ws = wb.active

            # 4. 获取表头
            headers = [cell.value.strip() if cell.value else "" for cell in ws[1]]

            # 5. 验证必要字段
            required_columns = ['name', 'url']
            if not all(col in headers for col in required_columns):
                return ApiResponse(
                    code=400,
                    message=_("Excel 文件缺少必要字段，需要包含：%(cols)s") % {"cols": ", ".join(required_columns)}
                )

            # 6. 定义数据处理函数
            def process_cell_value(value):
                """处理单元格值，转换类型和处理空值"""
                if value is None or str(value).strip().lower() in ['nan', 'n/a', '', 'none']:
                    return None
                return str(value).strip()

            # 7. 批量导入数据
            success_count = 0
            fail_count = 0
            error_messages = []
            created_list = []
            # 从第 2 行开始读取数据
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                try:
                    # 将行数据转换为字典
                    row_dict = dict(zip(headers, row))
                    # 处理每个字段的值
                    name = process_cell_value(row_dict.get('name'))
                    url = process_cell_value(row_dict.get('url'))
                    # 验证必要字段
                    if not name:
                        raise ValueError("壁纸名称不能为空")
                    if not url:
                        raise ValueError("壁纸链接不能为空")
                    # 简单的 URL 格式验证
                    if not url.startswith(('http://', 'https://')):
                        raise ValueError("壁纸链接必须是有效的 HTTP/HTTPS URL")
                    # 创建记录
                    wallpaper = Wallpapers.objects.create(
                        name=name,
                        url=url
                    )
                    created_list.append(f"{name}")
                    success_count += 1
                except Exception as e:
                    fail_count += 1
                    error_msg = f"第{row_idx}行导入失败：{str(e)}"
                    error_messages.append(error_msg)
                    logger.error(error_msg)

            # 8. 返回结果
            result_data = {
                "success_count": success_count,
                "fail_count": fail_count,
                "created_count": len(created_list),
                "created_list": created_list[:10],  # 只显示前 10 个
            }
            if error_messages:
                result_data["errors"] = error_messages[:20]  # 只显示前 20 个错误

            message = _("导入完成！成功：%(success)d条，失败：%(fail)d条，新增：%(created)d条") % {
                "success": success_count,
                "fail": fail_count,
                "created": len(created_list)
            }
            return ApiResponse(data=result_data, message=message)
        except Exception as e:
            logger.error(f"批量导入失败：{str(e)}", exc_info=True)
            return ApiResponse(code=500, message=_("批量导入失败：%(error)s") % {"error": str(e)})
