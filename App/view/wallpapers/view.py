"""
@Project ：Crush_check StarSign
@File    ：view.py
@Author  ：LiangHB
@Date    ：2026/3/4 17:09
@description : 星座相关视图逻辑
"""
from tool.base_views import BaseViewSet
from tool.middleware import logger
from tool.utils import CustomPagination, ApiResponse
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from django.utils.translation import get_language, gettext as _, activate
import pandas as pd
from rest_framework.decorators import api_view, action
from rest_framework import serializers
# 导入壁纸模型
from models.models import Wallpapers


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
        name = self.request.query_params.get("name")
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset

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
