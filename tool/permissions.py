from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission

from models.models import User
from tool.token_tools import CustomTokenTool


class IsStaffUser(BasePermission):
    """
       允许 is_staff=True 或 is_active=True 的用户访问
       """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            # 允许 staff 用户或 active 用户访问
        return request.user.is_staff or request.user.is_active
        # return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsOwner(BasePermission):
    """Allow access if user is superuser or owns the object.

    Ownership resolution rules (any matches counts as owner):
    - obj.owner == request.user
    - getattr(obj, 'owner_id') == request.user.id
    - obj.created_by == request.user
    - getattr(obj, 'scheduled_task', None) and obj.scheduled_task.owner == request.user
    """

    def has_permission(self, request, view):
        # 需登录；对象级再判断归属或管理员
        return bool(request.user and request.user.role == 'admin')


class IsTokenValid(BasePermission):
    """
    自定义权限：仅允许携带有效 Token 的请求访问
    """
    message = "Token 无效或已过期"  # 权限拒绝时的提示

    def has_permission(self, request, view):
        token = request.headers.get("token")
        is_valid, user_id = CustomTokenTool.verify_token(token)
        if is_valid:
            return True
        else:
            return False


class IsCustomerTokenValid(BasePermission):
    """C 端客户 Token（请求头 token，值为 CToken 开头）。"""
    message = "客户 Token 无效或已过期"

    def has_permission(self, request, view):
        token = request.headers.get("token")
        is_valid, customer_id = CustomTokenTool.verify_customer_token(token)
        if is_valid:
            request.customer_id = int(customer_id)
            return True
        return False


class IsOwnerOrAdmin(BasePermission):
    """
    自定义权限：仅允许对象所有者或管理员访问
    """
    message = "您没有权限访问此对象"  # 权限拒绝时的提示

    def has_object_permission(self, request, view, obj):

        token = request.headers.get("token")
        is_valid, user_id = CustomTokenTool.verify_token(token)
        # 管理员可访问所有对象
        if getattr(obj, 'role', 'admin') is not None:
            try:
                return True
            except Exception:
                return False
        return False

class URLAuthorization(BasePermission):
    def authenticate(self, request):
        # 获取当前请求的 URL
        url = request.path
        # 获取当前用户
        user = request.user
        token = request.query_params.get('token')
        if not token:
            return
        return True

class HeaderAuthorization(BasePermission):
    def authenticate(self, request):
        # 获取当前请求的 Header
        token = request.META.get('HTTP_AUTHORIZATION')
        # 获取当前用户
        if not token:
            return
        return True

class NotAuthenticated(BasePermission):
    """
    没有权限 兜底认证
    """
    def authenticate(self, request):
        raise AuthenticationFailed({"code":20000,"message":'用户未认证'})
    def authenticate_header(self, request):
        return 'NotAuthenticated'