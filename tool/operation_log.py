# -*- coding: UTF-8 -*-
"""
操作日志工具类
"""
from django.utils import timezone


def log_operation(operator=None, module="", operation_type="other", target_id=None,
                  target_name=None, description="", request=None, status=1,
                  error_message=None, extra_data=None):
    """
    记录操作日志

    Args:
        operator: 操作人（User 对象）
        module: 操作模块（如：用户管理、壁纸管理）
        operation_type: 操作类型（create/update/delete/query/export/import/login/logout/audit/other）
        target_id: 操作对象ID
        target_name: 操作对象名称
        description: 操作描述
        request: Django request 对象（可选，自动提取 IP、URL 等信息）
        status: 操作状态（1=成功，0=失败）
        error_message: 错误信息
        extra_data: 扩展数据（字典）

    Returns:
        OperationLog 对象
    """
    from models.models import OperationLog

    # 提取 request 信息
    ip_address = None
    request_url = None
    request_method = None
    user_agent = None

    if request:
        # 获取 IP 地址
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')

        request_url = request.get_full_path()
        request_method = request.method
        user_agent = request.META.get('HTTP_USER_AGENT', '')

    # 获取操作人姓名
    operator_name = ""
    operator_id = None
    if operator:
        operator_name = getattr(operator, 'username', '') or getattr(operator, 'email', '')
        operator_id = getattr(operator, 'id', None)

    # 创建日志记录
    log = OperationLog.objects.create(
        operator_id=operator_id,
        operator_name=operator_name,
        module=module,
        operation_type=operation_type,
        target_id=str(target_id) if target_id else None,
        target_name=target_name,
        description=description,
        request_method=request_method,
        request_url=request_url,
        ip_address=ip_address,
        user_agent=user_agent,
        extra_data=extra_data or {},
        status=status,
        error_message=error_message,
    )
    return log

