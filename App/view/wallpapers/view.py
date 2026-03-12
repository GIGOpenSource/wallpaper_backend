"""
@Project ：Crush_check StarSign
@File    ：view.py
@Author  ：LiangHB
@Date    ：2026/3/4 17:09
@description : 星座相关视图逻辑
"""
from App.view.wallpapers.search_models.search_models import TAG_MAPPING
from tool.base_views import BaseViewSet
from tool.middleware import logger
from tool.utils import CustomPagination, ApiResponse
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from django.utils.translation import get_language, gettext as _, activate
import pandas as pd
from rest_framework.decorators import api_view, action
from rest_framework import serializers
# 导入壁纸模型
from models.models import Wallpapers, WallpaperTag, WallpaperCategory, NavigationTag


# ==================== 壁纸相关视图 ====================

class WallpapersSerializer(serializers.ModelSerializer):
    """壁纸序列化器"""

    class Meta:
        model = Wallpapers
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


@extend_schema(tags=["壁纸管理"])
@extend_schema_view(
    list=extend_schema(
        summary="获取壁纸列表",
        parameters=[
            OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码"),
            OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量"),
            OpenApiParameter(name="name", type=str, required=False, description="壁纸名称搜索"),
            OpenApiParameter(name="tag_id", type=str, required=False,
                             description="标签 ID 查询，支持单个或多个（逗号分隔）"),
            OpenApiParameter(name="category_id", type=str, required=False,description="分类 ID 筛选，支持单个或多个（逗号分隔）"),
            OpenApiParameter(name="media_live", type=str, required=False,description="静态false或动态true"),
            OpenApiParameter(name="platform", type=str, required=False,description="平台电脑PC或手机PHONE "),
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
    update=extend_schema(summary="更新壁纸", request=WallpapersSerializer),
    partial_update=extend_schema(summary="部分更新壁纸", request=WallpapersSerializer),
    destroy=extend_schema(summary="删除壁纸", description="删除指定壁纸记录",
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
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(serializer.data)

    def get_queryset(self):
        """
        动态过滤查询
        """
        queryset = super().get_queryset()
        # 筛选参数：name
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

        # 筛选参数：tag_id（支持单个和多个，逗号分隔）
        tag_ids = self.request.query_params.get("tag_id")
        if tag_ids:
            tag_id_list = [int(tid.strip()) for tid in tag_ids.split(',') if tid.strip().isdigit()]
            if tag_id_list:
                # 使用 filter 进行多对多查询，会匹配包含任一标签的壁纸
                queryset = queryset.filter(tags__id__in=tag_id_list).distinct()
        return queryset

    @extend_schema(
        summary="获取所有壁纸标签",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "message": {"type": "string", "example": "标签获取成功"},
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer", "example": 1},
                                "name": {"type": "string", "example": "风景"},
                                "created_at": {"type": "string", "format": "date-time"}
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='tags')
    def tags(self, request):
        """
        获取所有壁纸标签列表
        """
        tags = WallpaperTag.objects.all().order_by('-created_at')
        data = [
            {
                'id': tag.id,
                'name': tag.name,
                'created_at': tag.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            for tag in tags
        ]
        return ApiResponse(data=data, message="标签获取成功")

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


class WallpapersSerializer(serializers.ModelSerializer):
    """壁纸序列化器"""

    class Meta:
        model = NavigationTag
        fields = '__all__'


@extend_schema(tags=["导航管理"])
@extend_schema_view(
    list=extend_schema(
        summary="获取导航列表",
        parameters=[
            OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码"),
            OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "results": {"type": "array", "items": {"$ref": "#/components/schemas/NavigationTag"}},
                            "total": {"type": "integer", "example": 50}
                        }
                    },
                    "message": {"type": "string", "example": "列表获取成功"}
                }
            }
        }
    ),
    retrieve=extend_schema(summary="获取导航详情", responses={200: WallpapersSerializer, 404: "导航不存在"}),
    create=extend_schema(summary="创建导航", request=WallpapersSerializer),
    update=extend_schema(summary="更新导航", request=WallpapersSerializer),
    partial_update=extend_schema(summary="部分更新导航", request=WallpapersSerializer),
    destroy=extend_schema(summary="删除导航", description="删除指定导航记录",
                          responses={204: "删除成功", 404: "导航不存在"})
)
class NavigationTagViewSet(BaseViewSet):
    """
    导航管理 ViewSet
    提供导航的增删改查功能
    """
    queryset = NavigationTag.objects.all()
    serializer_class = WallpapersSerializer
    pagination_class = CustomPagination