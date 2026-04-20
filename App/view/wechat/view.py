#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：NoBad
@File    ：view.py
@Author  ：LYP
@Date    ：2025/10/30 13:26
@description :小程序相关函数
"""
import base64
import json
import random
import time
import requests
import uuid

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from datetime import datetime
from django.http import JsonResponse
from django.forms import model_to_dict
from rest_framework.decorators import api_view, action
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from App.view.user.view import deactivate_user_and_delete_posters
from models.models import WeChatUser as ChatUser, InvitationRecord
from models.models import WeChatUser
from tool.permissions import IsTokenValid
from tool.tools import getEnvConfig, logger, res, CustomStatus
from tool.token_tools import CustomTokenTool, _redis
from tool.tool_wechat import checkWechatUserIsExist
from tool.utils import ApiResponse
from django.utils.translation import gettext as _

is_token = IsTokenValid()

import pytz
def check_and_update_vip_status(user):
    """
    检查用户VIP状态并在过期时更新为非VIP
    Args:
        user: 用户对象，应包含 vip_expire_date 和 is_vip 字段
    Returns:
        bool: 返回是否更新了VIP状态
    """
    # 获取当前时间（UTC时区）
    current_time = datetime.now(pytz.UTC)
    # 如果VIP已过期且当前状态仍为VIP
    if user.vip_expire_date is None and user.is_vip:
        user.is_vip = False
        from datetime import timedelta
        user.vip_expire_date = current_time - timedelta(days=1)
        user.save()
        return True

        # 情况2: 如果VIP已过期且当前状态仍为VIP，则设置为非VIP
    elif user.vip_expire_date and user.vip_expire_date < current_time and user.is_vip:
        user.is_vip = False
        user.save()
        return True

        # 情况3: 如果VIP未过期且当前是非VIP，则设置为VIP
    elif user.vip_expire_date and user.vip_expire_date >= current_time and not user.is_vip:
        user.is_vip = True
        user.save()
        return True

    return False

@extend_schema(
    methods=['POST'],
    tags=["微信接口"],
    summary="微信登陆byOpenId",
    description="通过微信授权码获取用户openId和session_key",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'code': {'type': 'string', 'description': '微信登录授权码'},
                'inviter_openid': {'type': 'string', 'description': '邀请人openid（可选）'},
                'username': {'type': 'string', 'description': '用户名'},
                'avatarUrl': {'type': 'string', 'description': '头像'},
                'gender': {'type': 'string', 'description': '性别'},
            },
            'required': ['code']
        }
    },
    responses={
        200: {
            'description': '成功获取openId',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'code': {'type': 'integer', 'example': 200},
                            'message': {'type': 'string', 'example': '登录成功'},
                            'data': {
                                'type': 'object',
                                'properties': {
                                    'openid': {'type': 'string', 'example': 'oO2lj5PjHbG4xxxxxx'},
                                    'token': {'type': 'string',
                                              'example': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.xxxxxx'}
                                }
                            }
                        }
                    }
                }
            }
        },
        400: {
            'description': '获取openId失败'
        }
    }
)
@api_view(['POST'])
def getWechatOpenId(request):
    """
    微信登陆byOpenId
    :param request:
    :return:
    """
    res.clear()
    try:
        if request.method == 'POST':
            body = json.loads(request.body)
            code = body.get('code')
            username = body.get('username')
            avatarUrl = body.get('avatarUrl')
            gender = body.get('gender')
            inviter_openid = body.get('inviter_openid')  # 获取邀请人openid
            session_key = ''
            session_key = body.get('session_key')
            token = request.headers.get("token")
            if not token:
                return ApiResponse(code=403, message=_("token不能为空"))
            # 2. 通过token获取openId和用户信息
            openId = _redis.getKey(token)
            if not openId:
                return ApiResponse(code=403, message=_("token无效或已过期"))
            user_exists = WeChatUser.objects.filter(open_id=openId, is_deleted=False).exists()
            if user_exists:
                user = WeChatUser.objects.get(open_id=openId, is_deleted=False)
                is_new_user = False
                # 检查VIP状态并更新
                check_and_update_vip_status(user)
            else:
                # 用户不存在 如果存在历史记录则删除该用户数据，并重新创建用户
                deactivate_user_and_delete_posters(openId)
                user = checkWechatUserIsExist(openId, session_key, "create", platform="wechat_mini")
                is_new_user = True
            if user.is_deleted and user.is_in_deletion_period():
                user.cancel_account_deletion()
                logger.info(f"微信用户 {openId} 在注销流程中重新登录，已自动取消注销")
            if not user_exists and inviter_openid:
                try:
                    inviter = WeChatUser.objects.get(open_id=inviter_openid)
                    InvitationRecord.objects.get_or_create(
                        invitee=user,  # 自己被谁邀请的
                        defaults={'inviter': inviter}  # 被这个人邀请的 点击者
                    )
                    is_new_user = True
                    if is_new_user:
                        old_count = inviter.share_success_count
                        inviter.share_success_count = old_count + 1
                        count = int(getEnvConfig("Is_Actice_count"))
                        if inviter.share_success_count % count == 0:
                            # 重置分享计数
                            inviter.share_success_count = 0
                            # allow_count加1（处理None的情况）
                            inviter.allow_count = (inviter.allow_count or 0) + 1
                        inviter.save()
                except WeChatUser.DoesNotExist:
                    # 邀请人不存在，记录日志但不影响正常登录流程
                    logger.warning(f"邀请人 {inviter_openid} 不存在")
            return JsonResponse(CustomStatus.WECHAT_LOGIN_SUCCESS.to_response(
                {"openid": openId, "token": token, "is_new": is_new_user}))
    except Exception as e:
        logger.error(f"获取微信openId失败: {str(e)}")
        return JsonResponse(CustomStatus.WECHAT_OPENID_ERROR.to_response())


@extend_schema(
    methods=['POST'],
    tags=["微信接口"],
    summary="获取用户手机号",
    description="通过微信授权码获取用户手机号",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'code': {'type': 'string', 'description': '微信授权码'},
                'openId': {'type': 'string', 'description': '用户openId'}
            },
            'required': ['code', 'openId']
        }
    },
    responses={
        200: {
            'description': '成功获取手机号',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'code': {'type': 'integer', 'example': 200},
                            'message': {'type': 'string', 'example': '获取成功'},
                            'data': {
                                'type': 'object',
                                'properties': {
                                    'phone': {'type': 'string', 'example': '13800138000'}
                                }
                            }
                        }
                    }
                }
            }
        },
        400: {
            'description': '获取手机号失败'
        }
    }
)
@api_view(['POST'])
def getUserPhone(request):
    """
    获取用户手机号
    :param request:
    :return:
    """
    res.clear()
    is_token_result = is_token.has_permission(request, None)
    if not is_token_result:
        return JsonResponse(CustomStatus.UNAUTHORIZED.to_response())
    try:
        if request.method == "POST":
            body = json.loads(request.body)
            code = body.get("code")
            openId = body.get("openId")
            base_url = getEnvConfig("WECHAT_BASE_URL")
            end_path = getEnvConfig("GET_USER_PHONE_END_PATH")
            access_token = getWechatAccessToken()
            url = base_url + end_path.format(access_token)
            response = requests.post(url, json={"code": code}).json()
            if "phone_info" in response.keys():
                phoneInfo = response["phone_info"]
                phoneNumber = phoneInfo["purePhoneNumber"]
                checkWechatUserIsExist(openId=openId, session_key="", types="update", phone=phoneNumber)
                return JsonResponse(CustomStatus.WECHAT_PHONE_SUCCESS.to_response({"phone": phoneNumber}))
            else:
                return JsonResponse(
                    CustomStatus.WECHAT_PHONE_ERROR.custom_message(status=CustomStatus.WECHAT_PHONE_ERROR,
                                                                   custom_msg=response["errmsg"]))
    except Exception as e:
        logger.error(f"获取微信手机号失败: {str(e)}")
        return JsonResponse(CustomStatus.WECHAT_PHONE_ERROR.to_response())


@extend_schema(
    tags=["微信接口"],  # 文档中的标签（与类视图分组一致）
    summary="获取用户信息",  # 接口摘要
    description="通过 Token 验证后，获取当前登录用户的详细信息",  # 接口描述
    methods=['GET'],  # 支持的请求方法（GET/POST 等）
    # 可选：定义请求参数（如 Query 参数）
    parameters=[
        # 示例：如果需要用户 ID 作为参数
        # OpenApiParameter(name="user_id", type=int, location=OpenApiParameter.QUERY, description="用户 ID")
    ],
    # 可选：定义响应格式
    responses={
        200: {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer"},
                "username": {"type": "string"},
                "email": {"type": "string"}
            }
        }
    },
)
@api_view(['GET'])
def getUserInfo(request):
    """
    获取用户信息
    :param request:
    :return:
    """
    res.clear()
    try:
        if request.method == "GET":
            openId = request.GET.get("openId")
            try:
                data = ChatUser.objects.get(open_id=openId)
                check_and_update_vip_status(data)
                user_data = model_to_dict(data)
                return JsonResponse(CustomStatus.GET_USER_INFO_SUCCESS.to_response(user_data))
            except ChatUser.DoesNotExist:
                return JsonResponse(
                    CustomStatus.GET_USER_INFO_ERROR.custom_message(status=CustomStatus.GET_USER_INFO_ERROR,
                                                                    custom_msg=_("用户不存在")))
    except Exception as e:
        logger.error(f"获取用户信息失败: {str(e)}")
        return JsonResponse(CustomStatus.GET_USER_INFO_ERROR.to_response())


@extend_schema(
    methods=['POST'],
    tags=["微信接口"],
    summary="更新用户信息",
    description="更新用户的昵称和头像信息",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'openId': {'type': 'string', 'description': '用户openId'},
                'username': {'type': 'string', 'description': '用户昵称'},
                'user_avatar': {'type': 'string', 'description': '用户头像URL'}
            },
            'required': ['openId']
        }
    },
    responses={
        200: {
            'description': '更新成功',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'code': {'type': 'integer', 'example': 200},
                            'message': {'type': 'string', 'example': '更新成功'}
                        }
                    }
                }
            }
        },
        400: {
            'description': _('更新失败')
        }
    }
)
@api_view(['POST'])
@transaction.atomic
def updataUserInfo(request):
    """
    更新用户信息
    :param request:
    :return:
    """
    res.clear()
    try:
        # result = is_token.has_permission(request, None)
        # if not result:
        #     return JsonResponse(CustomStatus.UNAUTHORIZED.to_response())
        if request.method == "POST":
            body = json.loads(request.body)
            openId = body.get("openId")
            username = body.get("username")
            user_avatar = body.get("user_avatar") or body.get("avatarUrl")
            user_gender = body.get("user_gender") or body.get("gender")
            data = ChatUser.objects.get(open_id=openId)
            if username:
                data.username = username
            if user_avatar:
                data.user_avatar = user_avatar
            if user_gender:
                data.user_gender = user_gender
            data.save()
            return JsonResponse(CustomStatus.UPDATA_USER_INFO_SUCCESS.to_response())
    except Exception as e:
        logger.error(f"更新用户信息失败: {str(e)}")
        return JsonResponse(CustomStatus.UPDATA_USER_INFO_ERROR.to_response())




@extend_schema(
    methods=['POST'],
    tags=["微信接口"],
    summary="获取邀请人列表信息",
    description="获取邀请人列表信息",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'openId': {'type': 'string', 'description': 'Id'}
            },
            'required': ['openId']
        }
    },
)
@api_view(['POST'])
def getAcquireNewUsers(request):
    """
    获取拉新用户
    :param request:
    :return:
    """
    res.clear()
    if request.method == "POST":
        body = json.loads(request.body)
        openId = body.get("openId")
        userData = ChatUser.objects.get(open_id=openId)
        # 获取该用户的所有邀请记录
        invitation_records = InvitationRecord.objects.filter(inviter=userData).select_related('invitee')
        total_count = invitation_records.count()
        invitees_details = []
        for record in invitation_records:
            invitees_details.append({
                'username': record.invitee.username or '未知用户',
                'openid': record.invitee.open_id,
                'created_at': record.created_at,
                'avatar': record.invitee.user_avatar or '',
                'gender': record.invitee.user_gender or 'unknown'
            })
        data = {
            'total_count': total_count,
            'invitees_list': invitees_details
        }
        return JsonResponse(CustomStatus.SUCCESS.to_response(data=data))




@extend_schema(
    methods=['POST'],
    tags=["应用Apk微信接口"],
    summary="应用Apk微信登录byOpenId",
    description="通过微信授权码获取用户openId和session_key code换openid",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'code': {'type': 'string', 'description': '微信登录授权码'},
                'openid': {'type': 'string', 'description': '微信登录授权码'},
                'inviter_openid': {'type': 'string', 'description': '微信登录授权码'},
                'access_token': {'type': 'string', 'description': '邀请人openid（可选）'},
                'username': {'type': 'string', 'description': '邀请人openid（可选）'},
                'avatarUrl': {'type': 'string', 'description': '邀请人openid（可选）'},
                'gender': {'type': 'string', 'description': '邀请人openid（可选）'},
                'refresh_token': {'type': 'string', 'description': '邀请人openid（可选）'},
            },
            'required': []
        }
    },
    responses={
        200: {
            'description': '成功获取openId',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'code': {'type': 'integer', 'example': 200},
                            'message': {'type': 'string', 'example': '登录成功'},
                            'data': {
                                'type': 'object',
                                'properties': {
                                    'openid': {'type': 'string', 'example': 'oO2lj5PjHbG4xxxxxx'},
                                    'token': {'type': 'string',
                                              'example': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.xxxxxx'}
                                }
                            }
                        }
                    }
                }
            }
        },
        400: {
            'description': '获取openId失败'
        }
    }
)
@api_view(['POST'])
def getApkWechatOpenId(request):
    body = json.loads(request.body)
    code = body.get('code')
    openid = body.get('openid')
    access_token = body.get('access_token')
    inviter_openid = body.get('inviter_openid')
    refresh_token = body.get('refresh_token')
    try:
        if openid:
            openId =openid
            session_key = refresh_token
            expire_seconds = 7 * 24 * 3600
            redis_key = f"wx_session_key:{openId}"
            _redis.setKey(redis_key, session_key, expire_seconds)
            token = CustomTokenTool.generate_token(openId, expire_days=7)
            user_exists = WeChatUser.objects.filter(open_id=openId).exists()
            if body['username'] and body['avatarUrl']:
                user = checkWechatUserIsExist(openId, session_key=session_key, types="create",
                                              username=body['username'], avatar=body['avatarUrl'],
                                              gender=body['gender'], platform="apk_mini")
            else:
                user = checkWechatUserIsExist(openId, session_key, "create", platform="apk_mini")
            is_new_user = False
            if not user_exists and inviter_openid:
                try:
                    inviter = WeChatUser.objects.get(open_id=inviter_openid)
                    InvitationRecord.objects.get_or_create(
                        invitee=user,  # 自己被谁邀请的
                        defaults={'inviter': inviter}  # 被这个人邀请的 点击者
                    )
                    is_new_user = True
                    if is_new_user:
                        old_count = inviter.share_success_count
                        inviter.share_success_count = old_count + 1
                        count = int(getEnvConfig("Is_Actice_count"))
                        if inviter.share_success_count % count == 0:
                            # 重置分享计数
                            inviter.share_success_count = 0
                            # allow_count加1（处理None的情况）
                            inviter.allow_count = (inviter.allow_count or 0) + 1
                        inviter.save()

                except WeChatUser.DoesNotExist:
                    # 邀请人不存在，记录日志但不影响正常登录流程
                    logger.warning(f"邀请人 {inviter_openid} 不存在")
            return JsonResponse(CustomStatus.WECHAT_LOGIN_SUCCESS.to_response(
                {"openid": openId, "token": token, "is_new": is_new_user}))
        else:
            return JsonResponse(
                CustomStatus.WECHAT_INFO_FETCH_FAILED.custom_message(status=CustomStatus.WECHAT_INFO_FETCH_FAILED,
                                                                     custom_msg="登录失败"))
    except Exception as e:
        logger.error(f"获取微信openId失败: {str(e)}")
        return JsonResponse(CustomStatus.WECHAT_OPENID_ERROR.to_response())


@extend_schema(
    methods=['POST'],
    tags=["微信接口"],
    summary="检查微信用户注销状态",
    description="获取微信用户openid并返回用户是否处于注销流程中，如果在注销流程中则返回false，否则返回true，用户不存在也返回false",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'code': {'type': 'string', 'description': '微信登录授权码'},
            },
            'required': ['code']
        }
    },
    responses={
        200: {
            'description': '成功获取用户注销状态',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'code': {'type': 'integer', 'example': 200},
                            'message': {'type': 'string', 'example': '查询成功'},
                            'data': {
                                'type': 'object',
                                'properties': {
                                    'openid': {'type': 'string', 'example': 'oO2lj5PjHbG4xxxxxx'},
                                    'can_login': {'type': 'boolean', 'example': True}
                                }
                            }
                        }
                    }
                }
            }
        },
        400: {
            'description': '查询失败'
        }
    }
)
@api_view(['POST'])
def checkWechatUserDeletionStatus(request):
    """
    检查微信用户注销状态
    :param request:
    :return:
    """
    res.clear()
    try:
        if request.method == 'POST':
            body = json.loads(request.body)
            code = body.get('code')
            session_key = ''
            token = ''
            if not code:
                return JsonResponse(CustomStatus.WECHAT_CODE_INVALID.to_response())
            # 通过微信code获取openid
            base_url = getEnvConfig("WECHAT_BASE_URL")
            end_path = getEnvConfig("LOGIN_END_PATH")
            appId = getEnvConfig("APPID")
            appSecret = getEnvConfig("APPSECRET")
            login_url = base_url + end_path.format(appId, appSecret, code)
            response = requests.get(login_url).json()
            if "openid" not in response.keys():
                return JsonResponse(
                    CustomStatus.WECHAT_INFO_FETCH_FAILED.custom_message(
                        status=CustomStatus.WECHAT_INFO_FETCH_FAILED,
                        custom_msg=response.get("errmsg")
                    )
                )
            if "openid" in response.keys():
                openId = response.get("openid")
                session_key = response.get("session_key")
                expire_seconds = 7 * 24 * 3600
                redis_key = f"wx_session_key:{openId}"
                _redis.setKey(redis_key, session_key, expire_seconds)
                openId = response.get("openid")
                token = CustomTokenTool.generate_token(openId, expire_days=7)
            try:
                # 尝试获取用户
                user = WeChatUser.objects.get(open_id=openId)
                # 检查用户是否在注销流程中
                if user.is_deleted and user.is_in_deletion_period():
                    # 用户在注销流程中，不能登录
                    can_login = True
                    logger.info(f"微信用户 {openId} 在注销流程中，无法登录")
                else:
                    # 用户不在注销流程中，可以登录
                    can_login = False
            except WeChatUser.DoesNotExist:
                # 用户不存在，返回false
                can_login = False
                logger.info(f"微信用户 {openId} 不存在")
            return JsonResponse(
                CustomStatus.WECHAT_LOGIN_SUCCESS.to_response({
                    "openid": openId,
                    "in_deletion_process": can_login,
                    "token": token,
                    "session_key":session_key
                })
            )
    except Exception as e:
        logger.error(f"检查微信用户注销状态失败: {str(e)}")
        return JsonResponse(CustomStatus.WECHAT_OPENID_ERROR.to_response())

from django.http import HttpResponse
from tool.tool_wechat import getWechatAccessToken

@extend_schema(
    methods=['GET'],
    tags=["微信接口"],
    summary="获取小程序码",
    description="通过当前token获取用户openId，生成对应的小程序码",
    parameters=[

    ],
    responses={
        200: {
            'description': '成功返回小程序码图片',
            'content': {
                'image/png': {
                    'schema': {
                        'type': 'string',
                        'format': 'binary'
                    }
                }
            }
        },
        400: {
            'description': '生成小程序码失败'
        },
        403: {
            'description': 'token无效'
        }
    }
)
@api_view(['GET'])
def getUnlimitedQRCode(request):
    """
    获取小程序码（返回Base64编码字符串，支持前台显示/复制）
    :param request:
    :return: 包含Base64图片的JSON响应
    """
    token = request.headers.get("token")
    if not token:
        return JsonResponse(CustomStatus.UNAUTHORIZED.to_response())

    # 通过token获取openId
    openId = _redis.getKey(token)
    if not openId:
        return JsonResponse(CustomStatus.UNAUTHORIZED.to_response())

    # 生成小程序码
    access_token = getWechatAccessToken()
    data = {
        "page": "pages/index/index",
        "scene": str(openId),
        "env_version": "release",
        "check_path": False
    }
    baseUrl = getEnvConfig("WECHAT_BASE_URL")
    end_path = getEnvConfig("GET_UNLIMITED_QRCODE")
    url = f"{baseUrl}{end_path.format(access_token)}"

    try:
        response = requests.post(url, json=data, timeout=10)  # 增加超时，避免卡死
        content_type = response.headers.get('Content-Type', '')

        # 1. 微信返回图片（正常情况）
        if content_type.startswith('image/'):
            # 提取图片格式（png/jpeg等）
            img_format = content_type.split('/')[-1]
            # 将二进制图片转为Base64编码（带前缀，前台可直接使用）
            img_base64 = base64.b64encode(response.content).decode('utf-8')
            # 拼接Base64完整前缀（前台可直接赋值给img标签的src）
            img_base64_full = f"data:{content_type};base64,{img_base64}"

            # 返回封装后的响应：包含Base64字符串、格式等信息
            return ApiResponse(
                code=200,
                message="生成小程序码成功",
                data={
                    "qrcode_base64": img_base64_full,  # 完整Base64（推荐）
                    "qrcode_base64_raw": img_base64,  # 纯Base64（可选，前台可自行拼接前缀）
                    "img_format": img_format  # 图片格式
                }
            )
        # 2. 微信返回错误JSON（异常情况）
        else:
            error_result = response.json()
            logger.error(f"微信API返回错误: {error_result}")
            return ApiResponse(
                code=400,
                message=f"生成小程序码失败：{error_result.get('errmsg', '未知错误')}",
                data=error_result
            )
    except requests.exceptions.Timeout:
        logger.error("生成小程序码失败：请求微信API超时")
        return ApiResponse(code=400, message="生成小程序码失败：请求超时")
    except Exception as e:
        logger.error(f"生成小程序码失败: {str(e)}", exc_info=True)
        return ApiResponse(code=400, message=f"生成小程序码失败：{str(e)}")