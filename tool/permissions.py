from packaging.utils import _
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission

from models.models import User,CustomerUser
from tool.token_tools import CustomTokenTool


class IsStaffUser(BasePermission):
    """允许 is_staff=True 或 is_active=True 的用户访问"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_staff or request.user.is_active


class IsOwner(BasePermission):
    """允许管理员访问"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # 只允许 User 表的管理员
        if isinstance(request.user, User):
            if request.user.role in ['admin', 'operator', 'super_admin']:
                return True
        return False


class IsAdmin(BasePermission):
    """Allow access if user is superuser or owns the object.

    Ownership resolution rules (any matches counts as owner):
    - obj.owner == request.user
    - getattr(obj, 'owner_id') == request.user.id
    - obj.created_by == request.user
    - getattr(obj, 'scheduled_task', None) and obj.scheduled_task.owner == request.user
    """
    def has_permission(self, request, view):
        try:
            role = request.user.role
        except AttributeError:
            raise AuthenticationFailed({"code": 401, "message": "管理员无role权限"})
        if not request.user or not role:
            raise AuthenticationFailed({"code": 401, "message": "请提供有效的管理员token"})
        try:
            if role in ['operator', 'admin']:
                return True
            else:
                raise AuthenticationFailed({"code": 401, "message": "管理员role权限不够"})
        except User.DoesNotExist:
            raise AuthenticationFailed(_('token对应的管理员不存在'))

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
        raise AuthenticationFailed({"code": 401, "message": "请先登录"})


class IsOwnerOrAdmin(BasePermission):
    """
    自定义权限：仅允许对象所有者或管理员访问
    """
    message = "您没有权限访问此对象"  # 权限拒绝时的提示

    def has_object_permission(self, request, view, obj):
        from models.models import User, CustomerUser

        # 管理员可以操作所有对象
        if isinstance(request.user, User):
            if hasattr(request.user, 'role') and request.user.role in ['admin', 'operator', 'super_admin']:
                return True

        # 客户用户只能操作自己上传的壁纸
        if isinstance(request.user, CustomerUser):
            # 检查是否有 customer_upload 关系
            if hasattr(obj, 'customer_upload'):
                upload_relation = obj.customer_upload
                if upload_relation and upload_relation.customer_id == request.user.id:
                    return True
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