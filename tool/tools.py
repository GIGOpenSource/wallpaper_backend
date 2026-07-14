#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：WallPaper 
@File    ：tools.py
@Author  ：LHB
@Date    ：2025/10/30 13:36 
@description :
"""
import ast
import decimal
import random
import os
import re
from enum import Enum
import logging


import numpy as np
import requests
from urllib.parse import urlparse
from django.contrib.auth.hashers import make_password, check_password
from dotenv import load_dotenv
from django.utils.translation import get_language,gettext as _


load_dotenv()
logger = logging.getLogger('info')
res = dict()


def encryptPassword(password):
    """
    密码加密
    :param password:
    :return:
    """
    return make_password(password, None, 'pbkdf2_sha256')


def checkPassword(password, hash_password):
    """
    密码校验
    :param password:
    :param hash_password:
    :return:
    """
    return check_password(password, hash_password)


def getEnvConfig(key: str, default=None):
    """
    获取环境变量
    :param default:
    :param key:
    :return:
    """
    return os.getenv(key, default)


class CustomStatus(Enum):
    """
    自定义状态枚举类
    """
    # 成功状态
    SUCCESS = (200, "成功")
    LOGINSUCCESS = (200, "登录成功")
    CREATED = (201, "创建成功")
    PAYSUCCESS = (200, "支付成功")
    UPDATED = (202, "更新成功")
    DELETED = (204, "删除成功")
    FAIL = (400, "服务器内部错误")

    # 客户端错误状态
    BAD_REQUEST = (400, "请求参数错误")
    UNAUTHORIZED = (401, "未授权访问")
    FORBIDDEN = (403, "禁止访问")
    NOT_FOUND = (404, "资源不存在")
    METHOD_NOT_ALLOWED = (405, "请求方法不允许")

    # 认证授权相关错误
    USERNAME_EXISTS = (400, "用户名已存在")
    INVALID_CREDENTIALS = (400, "用户名或密码错误")
    ACCOUNT_DISABLED = (400, "账户已被禁用")
    MISSING_REQUIRED_FIELDS = (400, "缺少必要字段")
    TOKEN_EXPIRED = (400, "令牌已过期")
    TOKEN_INVALID = (400, "令牌无效")
    PERMISSION_DENIED = (400, "权限不足")
    CREDENTIALS_EMPTY = (400, "用户名或密码不能为空")
    USER_NOT_FOUND = (400, "用户不存在")

    # 业务逻辑错误状态
    PRODUCT_NOT_AVAILABLE = (400, "商品不可用")
    INSUFFICIENT_STOCK = (400, "库存不足")
    ORDER_ALREADY_PAID = (400, "订单已支付")
    PAYMENT_FAILED = (400, "支付失败")
    INVALID_OPERATION = (400, "无效操作")

    # 数据验证错误
    VALIDATION_ERROR = (400,"数据验证失败")
    INVALID_FORMAT = (400, "数据格式不正确")
    OUT_OF_RANGE = (400, "数值超出范围")

    # 服务器错误状态
    INTERNAL_ERROR = (500, "服务器内部错误")
    DATABASE_ERROR = (5001, "数据库操作失败")
    SERVICE_UNAVAILABLE = (5002, "服务暂时不可用")
    TIMEOUT_ERROR = (5003, "请求超时")
    THIRD_PARTY_ERROR = (5004, "第三方服务错误")

    # 微信小程序错误
    WECHAT_LOGIN_FAILED = (400, "微信登录失败")
    WECHAT_TOKEN_EXPIRED = (400, "微信令牌已过期")
    WECHAT_USER_NOT_FOUND = (400, "微信用户不存在")
    WECHAT_CODE_INVALID = (400, "微信授权码无效,请重新获取授权")
    WECHAT_NETWORK_ERROR = (400, "微信网络请求失败")
    WECHAT_INFO_FETCH_FAILED = (400, "获取微信用户信息失败")
    UPDATA_USER_INFO_ERROR = (400, "更新用户信息失败")
    UPDATA_USER_INFO_SUCCESS = (200, "更新用户信息成功")
    WECHAT_OPENID_ERROR = (400, "获取openId失败")
    WECHAT_LOGIN_SUCCESS = (200, "获取openId成功")
    WECHAT_PHONE_SUCCESS = (200, "获取手机号成功")
    WECHAT_PHONE_ERROR = (400, "获取手机号失败")
    GET_USER_INFO_ERROR = (400, "获取用户信息失败")
    GET_USER_INFO_SUCCESS = (200, "获取用户信息成功")
    GET_POSTER_CONTENT_ERROR = (400, "获取海报内容失败，请稍后")
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def to_dict(self):
        """
        转换为字典格式
        """
        return {'code': self.code, 'message': self.message}

    @classmethod
    def custom_message(cls, status, custom_msg):
        """
        创建自定义消息的状态响应
        :param status: CustomStatus枚举值
        :param custom_msg: 自定义消息
        :return: 包含自定义消息的字典
        """
        return {'code': status.code, 'message': custom_msg}

    def to_response(self, data=None):
        """
        转换为完整的响应格式，包含数据
        :param data: 返回的数据内容
        :return: 完整的响应字典
        """
        response = {
            'code': self.code,
            'message': self.message
        }
        if data is not None:
            response['data'] = data
        return response


from PIL import Image, ImageDraw, ImageFont



from PIL import Image, ImageDraw, ImageColor


def draw_rounded_gradient_bar(
    score,
    width=400,  # 增大进度条宽度
    height=40,  # 增大进度条高度（整体放大）
    radius=20,  # 圆角半径与高度匹配，效果更明显
    start_color="#7B61FF",  # 深紫起始色
    end_color="#FF9BDB",    # 粉色结束色
    bg_color="#e7d9f3"      # 浅紫背景色
):
    # 创建仅包含进度条的画布（尺寸与进度条完全贴合）
    img = Image.new("RGBA", (width, height), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # 1. 绘制进度条背景（完整圆角，底层）
    bg_rect = (0, 0, width-2, height)
    draw.rounded_rectangle(bg_rect, radius=radius, fill=bg_color)
    # 计算填充宽度（确保有效范围）
    fill_width = int(score / 100 * width)
    if fill_width <= 0:
        return img
    fill_width = min(fill_width, width)  # 限制最大宽度不超过进度条总宽
    # 2. 填充区域（直角矩形，配合反向圆角偏移）
    # radius 是预留一块
    fill_rect = (radius, 0, 5 + fill_width, height)
    tail_color = ImageColor.getrgb(start_color)
    # 3. 绘制平滑渐变填充
    for x in range(fill_rect[0], fill_rect[2]):
        ratio = (x - fill_rect[0]) / fill_width
        r = int(ImageColor.getrgb(start_color)[0] + ratio * (ImageColor.getrgb(end_color)[0] - ImageColor.getrgb(start_color)[0]))
        g = int(ImageColor.getrgb(start_color)[1] + ratio * (ImageColor.getrgb(end_color)[1] - ImageColor.getrgb(start_color)[1]))
        b = int(ImageColor.getrgb(start_color)[2] + ratio * (ImageColor.getrgb(end_color)[2] - ImageColor.getrgb(start_color)[2]))
        tail_color = (r, g, b)
        draw.rectangle((x, fill_rect[1], x + 1, fill_rect[3]), fill=(r, g, b))
    # 4. 绘制头部反向圆角（左侧）
    head_radius = min(radius, fill_width)
    if head_radius > 0:
        draw.pieslice(
            (fill_rect[0]-radius, fill_rect[3] - 2*head_radius, fill_rect[0] + 2*head_radius-radius, fill_rect[3]),
            start=90, end=270,
            fill=start_color
        )
    tail_radius = min(radius, fill_width)
    if tail_radius > 0:
        draw.pieslice(
            (fill_rect[2] - 2*tail_radius + radius, fill_rect[3] - 2*tail_radius, fill_rect[2] + radius, fill_rect[3]),
            start=270, end=90,
            fill=tail_color
        )
    return img



def uploadFile(path, key, bucket_name):
    """

    :param path:
    :param key:
    :param bucket_name
    :return:
    """
    from tool.uploader_data import cos_client
    with open(path, "rb") as local_file:
        response = cos_client.put_object(
            Bucket=bucket_name,
            Body=local_file,  # 传入文件流，解决 seek() 报错
            Key=key,
            StorageClass='MAZ_STANDARD',
            EnableMD5=False
        )
        return response

def draw_rounded_gradient_deep_bar(
    score,
    width=400,
    height=40,
    radius=20,
    start_color="#7B61FF",  # Purple
    mid_color="#FF9BDB",    # Pink (currently used as end_color)
    end_color="#FF0000",    # Red
    bg_color="#e7d9f3"
):
    score = max(score, 10)
    # 创建仅包含进度条的画布（尺寸与进度条完全贴合）
    img = Image.new("RGBA", (width, height), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # 1. 绘制进度条背景（完整圆角，底层）
    bg_rect = (0, 0, width-2, height)
    draw.rounded_rectangle(bg_rect, radius=radius, fill=bg_color)
    # 计算填充宽度（确保有效范围）
    fill_width = int(score / 100 * width)
    if fill_width <= 0:
        return img
    fill_width = min(fill_width, width)  # 限制最大宽度不超过进度条总宽
    # 2. 填充区域（直角矩形，配合反向圆角偏移）
    # radius 是预留一块  渐变长度 给左右多出来的半圆留位置
    fill_rect = (radius, 0, fill_width-21, height)
    # 3. 绘制平滑渐变填充
    # 3. 绘制平滑渐变填充（三色渐变）
    max_fill_width = int(100 / 100 * width)  # 最大填充宽度
    tail_color = ImageColor.getrgb(start_color)
    # 在渐变绘制部分修改为：
    for x in range(fill_rect[0], fill_rect[2]):
        # 使用整个进度条宽度作为基准计算比例
        ratio = (x - fill_rect[0]) / max_fill_width
        ratio = min(ratio, 1.0)  # 确保不超过1.0

        # 颜色过渡逻辑保持不变
        if ratio <= 0.5:  # 0%-50%: 紫色到粉色
            local_ratio = ratio * 2  # 映射到0-1
            base_color = ImageColor.getrgb(start_color)
            target_color = ImageColor.getrgb(mid_color)
        else:  # 50%-100%: 粉色到红色
            local_ratio = (ratio - 0.5) * 2  # 映射到0-1
            base_color = ImageColor.getrgb(mid_color)
            target_color = ImageColor.getrgb(end_color)

        # 颜色插值计算保持不变
        r = int(base_color[0] + local_ratio * (target_color[0] - base_color[0]))
        g = int(base_color[1] + local_ratio * (target_color[1] - base_color[1]))
        b = int(base_color[2] + local_ratio * (target_color[2] - base_color[2]))
        tail_color = (r, g, b)
        draw.rectangle((x, fill_rect[1], x + 1, fill_rect[3]), fill=(r, g, b))
    # 4. 绘制头部反向圆角（左侧）
    head_radius = min(radius, fill_width)
    if head_radius > 0:
        draw.pieslice(
            (fill_rect[0] - head_radius, 0,
             fill_rect[0] + head_radius, 2 * head_radius),
            start=90, end=270, fill=start_color
        )
    tail_radius = min(radius, fill_width)
    if tail_radius > 0:
        # 根据当前进度位置决定尾部圆角颜色
        draw.pieslice(
            (fill_rect[2] - tail_radius, height-2 * tail_radius,
             fill_rect[2] + tail_radius, height),
            start=270, end=90, fill=tail_color
        )
    return img
