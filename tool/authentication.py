# tools/authentication.py
import token

from rest_framework.authentication import BasicAuthentication
from rest_framework.exceptions import AuthenticationFailed

from django.utils.translation import gettext_lazy as _

from models.models import User
# 导入你的密码验证函数
from tool.password_hasher import verify_password
from tool.token_tools import CustomTokenTool, generate_is_user_token, _redis


class CustomBasicAuthentication(BasicAuthentication):
    """
    完全重写 BasicAuthentication，使用自定义的密码验证逻辑 针对swaggerui文档
    """

    def authenticate_credentials(self, userid, password, request=None):
        """
        核心方法：验证用户名和密码
        - 重写为使用你的 verify_password 函数
        """
        # 1. 查找用户（支持 username/email 登录，根据你的模型调整）
        try:
            # 示例：优先用 username 查找，找不到则用 email
            user = User.objects.get(username=userid)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=userid)
            except User.DoesNotExist:
                # 不暴露“用户不存在”，避免信息泄露
                raise AuthenticationFailed(_('无效的用户名或密码'))
        if not verify_password(password, user.password):
            raise AuthenticationFailed(_('无效的用户名或密码'))
            # 检查 session 中是否有有效的 token
        # token = generate_is_user_token(request,user)
        # token = _redis.getKey(userid)
        request_token = request.headers.get("token")
        tokenUserId = _redis.getKey(request_token)
        if tokenUserId == userid:
            return user, request_token
        else:
            token = generate_is_user_token(request, user)
            return user, token
        # if token:
        #     return user, token
        # else:
        #     token = generate_is_user_token(request, user)
        #     # 4. 验证通过，返回用户对象
        #     return user, token

    def authenticate_header(self, request):
        """指定认证失败时的响应头（DRF 要求实现）"""
        return 'Basic realm="%s"' % self.www_authenticate_realm


# tools/authentication.py（继续添加以下代码）
from drf_spectacular.extensions import OpenApiAuthenticationExtension


# 小锁头
class CustomBasicAuthSchema(OpenApiAuthenticationExtension):
    target_class = 'tool.authentication.CustomBasicAuthentication'
    name = 'CustomBasicAuth'

    def get_security_definition(self, auto_schema):
        # 手动定义 Basic 认证的 OpenAPI 规范（兼容旧版本）
        return {
            'type': 'http',
            'scheme': 'basic',
            'description': "使用用户名/密码登录（密码验证逻辑：截断72字节后验证）"
        }


class TokenAuthentication(BasicAuthentication):
    """
    基于Token的认证：从请求头获取token并验证
    - 要求前端在请求头中携带 `token: <token值>`
    """

    def authenticate(self, request):
        # 1. 从请求头获取token
        token = request.headers.get("token")
        if not token:
            # 未提供token，返回None（表示放弃认证，交给后续认证类处理，若没有后续则认证失败）
            return None

        # 2. 验证token有效性（根据你的业务逻辑实现，示例如下）
        try:
            # # 假设CustomTokenTool有验证token并返回用户ID的方法
            # user_id = CustomTokenTool.verify_token(token)  # 需自行实现token验证逻辑
            # if not user_id:
            #     raise AuthenticationFailed(_('无效的token'))
            #
            # # 3. 根据user_id查询用户
            # user = User.objects.get(id=user_id)
            # if not user.is_active:  # 可选：检查用户是否激活
            #     raise AuthenticationFailed(_('用户已被禁用'))
            #
            # # 4. 认证通过，返回(user, token)
            # return (user, token)
            print("1")
        except User.DoesNotExist:
            raise AuthenticationFailed(_('token对应的用户不存在'))
        except Exception as e:
            # 捕获其他可能的异常（如token过期、格式错误等）
            raise AuthenticationFailed(_(f'token验证失败: {str(e)}'))

    def authenticate_header(self, request):
        """指定认证失败时的响应头"""
        return 'Token realm="API"'


# 为Token认证添加Swagger文档支持（小锁头显示）
class TokenAuthSchema(OpenApiAuthenticationExtension):
    target_class = 'tool.authentication.TokenAuthentication'
    name = 'TokenAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'header',
            'name': 'token',  # 对应请求头的key
            'description': '通过token进行认证，请求头格式：token: <你的token值>'
        }
