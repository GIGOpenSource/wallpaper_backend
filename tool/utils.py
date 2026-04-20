import logging
from asyncio import Lock

from django.core.paginator import EmptyPage, Paginator, PageNotAnInteger
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import exception_handler
import os
from logging.handlers import TimedRotatingFileHandler
import logging

class ApiResponse(Response):
    """统一响应格式（修复后）"""
    def __init__(self, data=None, message='success', code=200, **kwargs):
        # 确保message是字符串类型
        if not isinstance(message, str):
            # 如果是字典类型（如表单验证错误），转换为字符串
            if isinstance(message, dict):
                # 将字典转换为用分号分隔的键值对字符串
                message = "; ".join([f"{k}: {', '.join(v)}" for k, v in message.items()])
            else:
                # 其他类型强制转换为字符串
                message = str(message)
        # 确保data不为null，如果为null则设为空字典
        if data is None:
            data = {}

        response_data = {
            'code': code,
            'message': message,
            'data': data
        }
        # 始终使用200作为HTTP状态码
        super().__init__(response_data, status=200, **kwargs)


class CustomPagination(PageNumberPagination):
    page_size = 20  # 默认每页条数
    page_query_param = 'currentPage'  # 匹配前端的currentPage参数
    page_size_query_param = 'pageSize'  # 匹配前端的pageSize参数
    max_page_size = 999  # 最大每页条数限制
    def paginate_queryset(self, queryset, request, view=None):
        """
        重写分页查询方法：
        1. 处理页码非数字、页码超出范围的情况
        2. 超出范围时返回空列表，保持响应格式统一（不抛404）
        """
        # 获取前端传入的每页条数
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        # 初始化Django分页器
        paginator = Paginator(queryset, page_size)
        # 获取前端传入的页码（默认1）
        page_number = request.query_params.get(self.page_query_param, 1)

        try:
            # 尝试获取指定页码的页面对象
            self.page = paginator.page(page_number)
        except PageNotAnInteger:
            # 页码不是数字 → 返回第1页
            self.page = paginator.page(1)
        except EmptyPage:
            # 页码超出范围 → 构造空页（保留请求的页码，返回空数据）
            self.page = type('EmptyPage', (), {
                'number': int(page_number) if page_number.isdigit() else 1,
                'paginator': paginator,
                'object_list': []
            })()
        finally:
            # 绑定request到分页实例（供get_paginated_response使用）
            self.request = request

        # 控制分页控件显示（保留DRF原有逻辑）
        if paginator.num_pages > 1 and self.template is not None:
            self.display_page_controls = True

        # 返回当前页的数据列表（空页则返回空列表）
        return list(self.page.object_list)
    def get_paginated_response(self, data):
        """
        统一分页响应格式：
        - 正常页：返回真实分页数据
        - 空页：返回空数据+正确的请求页码
        """
        # 处理空页场景（页码超出范围）
        if not data and hasattr(self.page, 'object_list') and not self.page.object_list:
            return ApiResponse({
                'pagination': {
                    'page': self.page.number,  # 保留前端请求的页码（比如2）
                    'page_size': self.get_page_size(self.request) or self.page_size,
                    'total': 0,  # 空页总记录数为0
                    'total_pages': 0  # 空页总页数为0
                },
                'results': []
            })
        # 正常分页场景（原有逻辑）
        return ApiResponse({
            'pagination': {
                'page': self.page.number,
                'page_size': self.page.paginator.per_page,
                'total': self.page.paginator.count,
                'total_pages': self.page.paginator.num_pages
            },
            'results': data
        })

from django.utils.translation import gettext as _
def custom_exception_handler(exc, context):
    """
    自定义异常处理函数
    """
    # 调用默认的异常处理函数
    response = exception_handler(exc, context)

    # 如果是页面无效的错误，返回自定义响应
    if isinstance(exc, NotFound) and ("Invalid page" in str(exc.detail) or "无效页面" in str(exc.detail)):
        return ApiResponse(
            data={
                'pagination': {
                    'page': 1,
                    'page_size': 20,
                    'total': 0,
                    'total_pages': 0
                },
                'results': []
            },
            message=_("请求的页面超出范围，返回空结果"),
            code=200
        )

    # 对于其他异常，返回默认处理结果
    return response


def exclude_api_tag_hook(endpoints=None, **kwargs):
    """
    排除默认的 'api' 标签
    """
    if endpoints is None:
        endpoints = []

    # 创建新的端点列表
    filtered_endpoints = []

    for endpoint in endpoints:
        print("Endpoint:", endpoint)

        # 获取操作对象（第三个元素）
        operation = endpoint[2]
        print("Operation:", operation)

        # 检查 operation 是否为字典且包含 tags 字段
        if isinstance(operation, dict) and 'tags' in operation:
            # 如果包含 'api' 标签，则移除
            if 'api' in operation['tags']:
                print("找到了tags", operation['tags'])
                operation['tags'] = [tag for tag in operation['tags'] if tag != 'api']

                # 如果标签为空，则移除整个标签字段
                if not operation['tags']:
                    del operation['tags']

        # 添加到过滤后的端点列表
        filtered_endpoints.append(endpoint)

    return filtered_endpoints

