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

import cv2
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


def add_text_opencv(img, text, pos, font_size=30, color=(255, 255, 255), font_path="simhei.ttf", is_center=False,
                    max_width=None, line_spacing=20):
    """
    OpenCV添加文字（支持中文+自动折行+居中显示）
    """
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA))
    draw = ImageDraw.Draw(img_pil)
    # 加载字体
    try:
        font = ImageFont.truetype(font_path, font_size, encoding="utf-8")
    except:
        font = ImageFont.load_default()
    # 处理折行
    if max_width:
        chars = list(text)
        lines = []
        current_line = ""
        for char in chars:
            test_line = current_line + char
            if draw.textlength(test_line, font=font) <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)
    else:
        lines = [text]
    # 逐行绘制（居中/左对齐）
    start_x, start_y = pos
    font_height = font.getbbox("测")[3] - font.getbbox("测")[1]
    y = start_y
    for line in lines:
        line_width = draw.textlength(line, font=font)
        draw_x = start_x - (line_width // 2) if is_center else start_x
        draw.text((draw_x, y), line, font=font, fill=color)
        y += font_height + line_spacing
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGBA2BGRA)


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


def generate_emotion_image(full_file_name, keywords, score, summary, img_character_url, background, backplane, user, config):
    """
    生成外层的海报
    :param full_file_name:
    :param keywords:
    :param score:
    :param summary:
    :param template:人物模版
    :param background: 背景
    :param user
    :return:
    """
    logger.info("开始生成海报=========")
    from tool.uploader_data import cos_client
    from WallPaper.settings.dev import IMAGE_DIR, FONT_DIR, DOWNLOAD_DIR
    bucket_name = getEnvConfig('TENCENT_COS_BUCKET', 'crashcheck-1256118830')
    # try:
    #     if not template.images.constrained_target:
    #         raise ValueError("模板图片约束目标为空")
    #     img_character_url = random.choice(template.images.constrained_target).templateimage.image_url
    # except IndexError:
    #     # 处理空序列情况
    #     logger.error("无法从空的 constrained_target 序列中选择图片")
    #     img_character_url = None  # 或设置默认图片URL
    img_character_path = downloadFile(img_character_url)  # 人物头像
    img_back_url = random.choice(background.images.constrained_target).templateimage.image_url
    img_backplane_url = random.choice(backplane.images.constrained_target).templateimage.image_url
    img_back_path = downloadFile(img_back_url)
    img_backplane_path = downloadFile(img_backplane_url)

    # ---------------------- 1. 定义预设中心点位置（核心） ----------------------
    def parse_config_field(field_value):
        """解析单个字段配置，返回 (pos_tuple, size, font_path)"""
        if not field_value:
            return None, None, None
        # 确保字段值是字典格式（处理字符串转字典）
        if isinstance(field_value, str):
            field_dict = ast.literal_eval(field_value.strip())
        else:
            field_dict = field_value
        pos = ast.literal_eval(field_dict.get("pos", "").strip()) if field_dict.get("pos") else None
        # 解析字号（默认32）
        size = field_dict.get("size", 14)
        # 解析字体路径（默认simhei.ttf）
        fonturl = field_dict.get("fonturl", "simhei.ttf")
        font_path = f"{FONT_DIR}/{fonturl}"
        return pos, size, font_path

    # 1、生成配置对象 位置、缩放、字体
    character_pos, character_scale, __ = parse_config_field(config.character_pos)
    keyword_pos, keyword_size, keyword_font = parse_config_field(config.keyword_pos)
    context_pos, context_size, context_font = parse_config_field(config.context_pos)
    score_pos, score_size, score_font = parse_config_field(config.score_pos)
    star_pos, star_size, star_font = parse_config_field(config.star_pos)
    qrcode_pos, qrcode_scale, __ = parse_config_field(config.qrcode_pos)
    background_plane_pos, background_plane_scale, __ = parse_config_field(config.background_plane)
    username_pos, username_size, username_font = parse_config_field(config.username_pos)
    useravatar_pos, useravatar_size, useravatar_font = parse_config_field(config.useravatar_pos)
    # 解析总结
    summary_pos, summary_size, summary_font = parse_config_field(config.summary_start_pos)
    summary_config = config.summary_start_pos
    if summary_config:
        summary_start_pos = ast.literal_eval(summary_config.get("pos", "").strip())
        summary_width = summary_config.get("width", 600)
        summary_line_spacing = summary_config.get("line", 20)
    else:
        summary_start_pos = (255, 1000)  # 默认位置
        summary_width = 600  # 默认宽度
        summary_line_spacing = 20  # 默认行间距
    # 1、预设中心点位置
    preset_centers_config = {
        "character_pos": character_pos,
        "keyword_pos": keyword_pos,
        "context_pos": context_pos,
        "score_pos": score_pos,
        "star_pos": star_pos,
        "qrcode_pos": qrcode_pos,
        "background_plane_pos": background_plane_pos,
        "username_pos": username_pos,
        "useravatar_pos": useravatar_pos,
        "summary_start_pos": summary_start_pos,
        "summary_width": summary_width,
        "summary_line_spacing": summary_line_spacing
    }
    # 2、 检验图片尺寸
    background_img = cv2.imread(f"{DOWNLOAD_DIR}/{img_back_path}", cv2.IMREAD_UNCHANGED)
    # 关键1：创建#2A2936纯色图（和背景图同尺寸）
    # solid_color = np.full((background_img.shape[0], background_img.shape[1], 3), (36, 29, 42), dtype=np.uint8)
    solid_color = np.full((background_img.shape[0], background_img.shape[1], 3), (54, 41, 42), dtype=np.uint8)
    # 关键2：如果是透明图（4通道），用纯色图填充，保留Alpha通道；否则直接替换
    if background_img.shape[-1] == 4:
        background_img = background_img[:, :, :3]  # 丢弃Alpha通道，转为3通道
    background_img = solid_color  # 直接赋值3通道纯色图，通道数完全匹配
    assert background_img.shape[:2] == (1090, 710), "背景尺寸必须为 1090, 710（高*宽）"

    img_backplane_img = cv2.imread(f"{DOWNLOAD_DIR}/{img_backplane_path}")
    assert img_backplane_img.shape[:2] == (506, 650), "背板尺寸必须为 506, 650（高*宽）"

    character_img = cv2.imread(f"{DOWNLOAD_DIR}/{img_character_path}")
    assert character_img.shape[:2] == (807, 537), "人物尺寸必须为 807, 537（高*宽）"
    logger.info("开始生成海报001=========")
    # 3、图片配置添加 缩放配置
    images_config = []
    # 添加人物图（位置从配置解析，缩放比例0.35）

    if background_plane_pos and img_backplane_path:
        images_config.append((f"{DOWNLOAD_DIR}/{img_backplane_path}", background_plane_scale, "background_plane_pos"))
    # 添加二维码（如果有二维码图片路径，位置从配置解析，缩放比例从size字段获取）
    qrcode_img_path = f"{DOWNLOAD_DIR}/{user.open_id}.png"
    if qrcode_pos and os.path.exists(qrcode_img_path):
        images_config.append((qrcode_img_path, qrcode_scale, "qrcode_pos"))
    if character_pos and img_character_path:
        images_config.append((f"{DOWNLOAD_DIR}/{img_character_path}", character_scale, "character_pos"))
    keywords_value = [v for key, v in keywords.items()]  # 4个分数
    keywords_key = [key for key, v in keywords.items()]

    # 确保分数和坐标数量一致
    assert len(keywords_value) == len(keyword_pos) == 4, "分数和坐标数量必须均为4个"
    # 遍历每个分数和坐标，生成进度条
    for idx, (score, original_pos) in enumerate(zip(keywords_value, keyword_pos)):
        # 生成进度条（PIL Image对象）
        progress_img = draw_rounded_gradient_bar(score, width=400, height=40, radius=20)
        # 将PIL Image转换为OpenCV格式（RGBA→BGR）
        progress_img_cv = cv2.cvtColor(np.array(progress_img), cv2.COLOR_RGBA2BGRA)
        # 保存为临时文件（或直接传递内存对象，这里用临时文件更稳妥）
        temp_img_path = f"{DOWNLOAD_DIR}/progress_bar_{idx}.png"
        cv2.imwrite(temp_img_path, progress_img_cv)
        # 坐标y轴加20
        new_pos = (original_pos[0] + 100, original_pos[1] + 50)
        # 更新预设位置配置（为当前进度条添加新坐标）
        preset_centers_config[f"keyword_pos_{idx}"] = new_pos
        # 添加到图片配置列表
        images_config.append((temp_img_path, 0.5, f"keyword_pos_{idx}"))
    # ---------------------- 4. 按动态配置拼接图片 ----------------------
    for img_path, scale, pos_name in images_config:
        center = preset_centers_config.get(pos_name)
        if not center:
            print(f"警告：{pos_name} 位置配置不存在，跳过图片 {img_path}")
            continue
        # 读取图片时保留Alpha通道
        img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            print(f"警告：未找到图片 {img_path}，跳过")
            continue
        # 缩放图片
        h, w = img.shape[:2]
        new_w, new_h = int(w * scale), int(h * scale)
        img_resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        # 中心点转左上角坐标
        center_x, center_y = center
        x = int(center_x - new_w // 2)
        y = int(center_y - new_h // 2)
        # 边界校验并拼接（添加Alpha混合）
        y1, y2 = y, y + new_h
        x1, x2 = x, x + new_w
        if 0 <= y1 < y2 <= background_img.shape[0] and 0 <= x1 < x2 <= background_img.shape[1]:
            # 关键：有Alpha通道则混合，无则直接覆盖
            if img_resized.shape[-1] == 4:
                alpha = img_resized[:, :, 3] / 255.0  # 透明比例（0=完全透明，1=不透明）
                bg_alpha = 1 - alpha
                # 逐通道混合（避免黑边）
                for c in range(3):
                    background_img[y1:y2, x1:x2, c] = (
                            alpha * img_resized[:, :, c] + bg_alpha * background_img[y1:y2, x1:x2, c]
                    ).astype(np.uint8)
            else:
                background_img[y1:y2, x1:x2] = img_resized
        else:
            print(f"警告：图片 {img_path} 在 {pos_name} 位置超出底图，跳过")
    # ---------------------- 5. 动态生成文字配置（基于解析的字段值） ----------------------
    while len(keywords) < 4:
        keywords.append("")
    # 动态生成文字配置（每个条目都用解析后的位置、字号、字体）
    text_config = [
        # 关键词（4个位置，从keyword_pos嵌套元组中取 【text内容、位置、字体大小、RGB、字体路径、是否居中】）
        (keywords_key[0], keyword_pos[0] if keyword_pos and len(keyword_pos) >= 1 else (0, 0), keyword_size,
         (127, 37, 230), keyword_font, False),
        (keywords_key[1], keyword_pos[1] if keyword_pos and len(keyword_pos) >= 2 else (0, 40), keyword_size,
         (127, 37, 230), keyword_font, False),
        (keywords_key[2], keyword_pos[2] if keyword_pos and len(keyword_pos) >= 3 else (0, 80), keyword_size,
         (127, 37, 230), keyword_font, False),
        (keywords_key[3], keyword_pos[3] if keyword_pos and len(keyword_pos) >= 4 else (0, 120), keyword_size,
         (127, 37, 230), keyword_font, False),
        # 标题“测试结果”：颜色改为 #FFFFFF（RGB：255,255,255）
        (_("测试结果"), context_pos, context_size, (255, 255, 255), context_font, False),
        # 分数：保持原颜色（按需可改）
        (_("含渣量:")+str(score)+"%", score_pos, score_size, (0, 0, 0), score_font, False),
        # 用户名：保持原颜色
        # (user.username, username_pos, username_size, (0, 0, 0), username_font, True),
        # summary：颜色改为 #FFFFFF（RGB：255,255,255）
        (
            f"{summary}", summary_start_pos, 32, (255, 255, 255), summary_font, False, summary_width,
            summary_line_spacing),
    ]
    # ---------------------- 6. 批量添加文字 ----------------------
    for item in text_config:
        if len(item) == 6:
            text, pos, font_size, color, fontpath, is_center = item
            background_img = add_text_opencv(background_img, text, pos, font_size, color, fontpath, is_center)
        elif len(item) == 8:
            text, pos, font_size, color, fontpath, is_center, max_width, line_spacing = item
            background_img = add_text_opencv(background_img, text, pos, font_size, color, fontpath, is_center,
                                             max_width, line_spacing)

    save_success = cv2.imwrite(f"{IMAGE_DIR}/once_{score}_parse.png", background_img)
    if not save_success:
        raise IOError(f"本地图片保存失败：{IMAGE_DIR}/once_{score}_parse.png（可能无写入权限或路径不存在）")
    local_img_path = os.path.join(IMAGE_DIR, f"once_{score}_parse.png")

    # 4. 读取本地图片并上传到 COS（用文件流替代 Image 对象）
    try:
        with open(local_img_path, "rb") as local_file:
            logger.info("海报图片生成成功==========")
            response = uploadFile(f"{IMAGE_DIR}/once_{score}_parse.png", full_file_name, bucket_name)
            logger.info("海报图片上传成功")
    finally:
        try:
            os.remove(local_img_path)
        except:
            pass
            # 删除进度条临时文件
        for idx in range(4):  # 删除progress_bar_0.png到progress_bar_3.png
            progress_bar_path = os.path.join(DOWNLOAD_DIR, f"progress_bar_{idx}.png")
            try:
                if os.path.exists(progress_bar_path):
                    os.remove(progress_bar_path)
            except:
                pass
        try:
            img_character_full_path = os.path.join(DOWNLOAD_DIR, img_character_path)
            if os.path.exists(img_character_full_path):
                os.remove(img_character_full_path)
        except:
            pass
        try:
            img_back_full_path = os.path.join(DOWNLOAD_DIR, img_back_path)
            if os.path.exists(img_back_full_path):
                os.remove(img_back_full_path)
        except:
            pass

        return response


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


def generate_risk_advice_image(full_file_name, json_data, background,config):
    logger.info("开始生成深度报告图片==========")
    from WallPaper.settings.dev import SIGN_DIR,IMAGE_DIR, FONT_DIR, DOWNLOAD_DIR
    """生成深度报告宽度500px的长图（左对齐+背景留白300px+裁剪拼接）"""
    # 配置路径
    pingfang_path = f"{FONT_DIR}/{config.keyword_pos['fonturl']}"   # 为了平方字体
    pingfangSc_path = f"{FONT_DIR}/{config.qrcode_pos['fonturl']}"  # 为了平方SC字体
    alimama_path = f"{FONT_DIR}/{config.context_pos['fonturl']}" # 阿里妈妈shuheiTi-Bold

    icon1_path = f"{SIGN_DIR}/action_1.png"
    icon2_path = f"{SIGN_DIR}/action_2.png"
    bg_path = f"{SIGN_DIR}/backdeep.png"  # 背景图路径
    bucket_name = getEnvConfig('TENCENT_COS_BUCKET', 'crashcheck-1256118830')
    file_name = full_file_name.split("img/")[1]
    local_img_path = f"{IMAGE_DIR}/{file_name}"
    # ---------------------- 1. 加载背景图（保留原始大小） ----------------------
    decimal.getcontext().prec = 20
    bg_img = Image.open(bg_path).convert("RGBA")
    bg_width, bg_height = bg_img.size  # 948*6125
    target_width = 500
    bg_scale_ratio = decimal.Decimal(target_width) / decimal.Decimal(bg_width)  # 缩放比例

    # ---------------------- 2. 创建临时画布绘制内容 ----------------------
    temp_height = 3000  # 临时高度用于绘制内容
    temp_canvas = Image.new("RGBA", (target_width, temp_height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(temp_canvas)

    # ---------------------- 3. 配置字体 ----------------------
    try:
        font_summary = ImageFont.truetype(pingfangSc_path, 20)
        font_summary_advise_text = ImageFont.truetype(pingfang_path, 20)
        font_fengxian = ImageFont.truetype(pingfangSc_path, 22)
        font_socre_fengxian = ImageFont.truetype(pingfang_path, 18)
        font_17_alimama = ImageFont.truetype(alimama_path, 26)
    except OSError as e:
        raise Exception(f"字体加载失败：{e}")

    # ---------------------- 4. 绘制“风险评分与行动建议”（左对齐+层叠） ----------------------
    icon1 = Image.open(icon1_path).convert("RGBA")
    title1 = (_("风险评分与行动建议"))
    title1_bbox = draw.textbbox((0, 0), title1, font=font_17_alimama)
    title1_width = title1_bbox[2]
    title1_height = title1_bbox[3]

    # 图标层叠：图标作为背景，文字左对齐覆盖（左间距30px）
    icon1_width = title1_width + 85  # 图标宽度
    icon1_height = title1_height + 30 #底图高度高度
    icon1 = icon1.resize((icon1_width, icon1_height), Image.Resampling.LANCZOS)
    # 位置：左对齐30px，背景留白300px后
    content_start_y = 132  # 背景顶部留白300px
    icon1_x = 0   # 左侧【底部图片】距离上方高度
    icon1_y = content_start_y
    title1_x = icon1_x + (icon1_width - title1_width) // 2  +12 # 图标右侧间距10px  文字距离左侧
    title1_y = icon1_y + (icon1_height - title1_height) // 2
    # 先画图标（背景），再画文字（层叠覆盖）
    temp_canvas.paste(icon1, (icon1_x, icon1_y), mask=icon1)
    draw.text((title1_x, title1_y), title1, font=font_17_alimama, fill=(255, 255, 255, 255))

    # ---------------------- 5. 绘制summary段落 ----------------------
    summary = json_data["summary"]
    summary_x = 42
    summary_y = icon1_y + icon1_height + 30
    max_width_summary = target_width - 90
    chars = list(summary)
    current_line = ""
    lines = []
    for char in chars:
        test_line = current_line + char
        if draw.textlength(test_line, font=font_summary) <= max_width_summary:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = char
    if current_line:
        lines.append(current_line)
    for line in lines:
        draw.text((summary_x, summary_y), line, font=font_summary, fill=(51, 51, 51, 255))
        summary_y += font_summary.getbbox("测")[3] + 8

    # ---------------------- 6. 绘制flags进度条（风险等级靠右） ----------------------
    flags = json_data["flags"]
    progress_y = summary_y + 24 # 进度条区域距离上不距离
    for flag_name, score in flags.items():
        # 风险等级判断
        if score < 20:
            risk_level = _("低风险")
        elif score < 40:
            risk_level = _("中低风险")
        elif score < 60:
            risk_level = _("中风险")
        else:
            risk_level = _("高风险")

        # 标题左侧，风险等级右侧显示
        flag_title = f"{flag_name}：{score} %"
        # 计算风险等级宽度，靠右对齐
        risk_level_bbox = draw.textbbox((0, 0), risk_level, font=font_fengxian)
        risk_level_width = risk_level_bbox[2]
        risk_level_x = target_width - 40 - risk_level_width  # 右侧边距30px

        # 绘制左侧标题和右侧风险等级
        draw.text((summary_x, progress_y), flag_title, font=font_fengxian, fill=(61, 61, 61, 255))
        draw.text((risk_level_x, progress_y), risk_level, font=font_socre_fengxian, fill=(61, 61, 61, 200))

        # 生成进度条
        progress_bar = draw_rounded_gradient_deep_bar(score, width=410, height=20, radius=10)
        bar_x = summary_x
        bar_y = progress_y + 46 # 文字距离进度条的位置
        temp_canvas.paste(progress_bar, (bar_x, bar_y), mask=progress_bar)
        progress_y = bar_y + 46

    # ---------------------- 7. 绘制风险与建议 ----------------------
    # 最隐蔽风险
    hidden_risk_title = _(" · 最隐蔽风险：")
    hidden_risk_content = json_data["danger"]
    draw.text((summary_x, progress_y), hidden_risk_title, font=font_summary, fill=(51, 51, 51, 255))
    title_bbox = draw.textbbox((0, 0), hidden_risk_title, font=font_summary)
    title_width = title_bbox[2]

    # 为最隐蔽风险内容添加自动换行
    hidden_risk_lines = []
    current_line = ""
    for char in hidden_risk_content:
        test_line = current_line + char
        if draw.textlength(test_line, font=font_summary_advise_text) <= (max_width_summary - title_width):
            current_line = test_line
        else:
            hidden_risk_lines.append(current_line)
            current_line = char
    if current_line:
        hidden_risk_lines.append(current_line)
    # 绘制多行文本
    line_height = font_summary_advise_text.getbbox("测")[3] + 8
    for i, line in enumerate(hidden_risk_lines):
        draw.text((summary_x + title_width, progress_y + i * line_height), line, font=font_socre_fengxian,
                  fill=(51, 51, 51, 200))

    progress_y += len(hidden_risk_lines) * line_height

    # 行动建议
    advise_title = _(" · 行动建议：")
    advise_content = json_data["advise"]
    draw.text((summary_x, progress_y), advise_title, font=font_summary, fill=(51, 51, 51, 255))
    title_bbox = draw.textbbox((0, 0), advise_title, font=font_summary)
    title_width = title_bbox[2]

    # 为行动建议内容添加自动换行
    advise_lines = []
    current_line = ""
    for char in advise_content:
        test_line = current_line + char
        if draw.textlength(test_line, font=font_summary_advise_text) <= (max_width_summary - title_width):
            current_line = test_line
        else:
            advise_lines.append(current_line)
            current_line = char
    if current_line:
        advise_lines.append(current_line)

    # 绘制多行文本
    line_height = font_summary_advise_text.getbbox("测")[3] + 8
    for i, line in enumerate(advise_lines):
        draw.text((summary_x + title_width, progress_y + i * line_height), line, font=font_summary_advise_text, fill=(51, 51, 51, 200))
    progress_y += len(advise_lines) * line_height

    # 行动建议总结
    advise_summary_title = _("结论：")
    advise_summary_content = json_data["advise_summary"]
    draw.text((summary_x, progress_y), advise_summary_title, font=font_summary, fill=(51, 51, 51, 255))
    title_bbox = draw.textbbox((0, 0), advise_summary_title, font=font_summary)
    title_width = title_bbox[2]

    # 为行动建议总结内容添加自动换行
    advise_summary_lines = []
    current_line = ""
    for char in advise_summary_content:
        test_line = current_line + char
        if draw.textlength(test_line, font=font_summary_advise_text) <= (max_width_summary - title_width):
            current_line = test_line
        else:
            advise_summary_lines.append(current_line)
            current_line = char
    if current_line:
        advise_summary_lines.append(current_line)

    # 绘制多行文本
    line_height = font_summary_advise_text.getbbox("测")[3] + 8
    for i, line in enumerate(advise_summary_lines):
        draw.text((summary_x + title_width, progress_y + i * line_height), line, font=font_summary_advise_text, fill=(51, 51, 51, 200))
    progress_y = progress_y + len(advise_summary_lines) * line_height
    # ---------------------- 8. 绘制“详细解读”（左对齐+层叠） ----------------------
    icon2 = Image.open(icon2_path).convert("RGBA")
    title2 = _("详细解读")
    title2_bbox = draw.textbbox((0, 0), title2, font=font_17_alimama)
    title2_width = title2_bbox[2]
    title2_height = title2_bbox[3]

    # 图标层叠设置
    icon2_width = title2_width + 85  # 图标长度
    icon2_height = title2_height + 30  # 图标高度

    icon2 = icon2.resize((icon2_width, icon2_height), Image.Resampling.LANCZOS)
    # 位置：左对齐30px
    icon2_x = 0
    icon2_y = progress_y + 30  # 详细解读距离上一段距离
    title2_x = icon2_x + (icon2_width - title2_width) // 2 + 12  # 详细解读文字左距离
    title2_y = icon2_y + (icon2_height - title2_height) // 2
    # 层叠绘制
    temp_canvas.paste(icon2, (icon2_x, icon2_y), mask=icon2)
    draw.text((title2_x, title2_y), title2, font=font_17_alimama, fill=(255, 255, 255, 255))

    # ---------------------- 9. 绘制detail内容 ----------------------
    detail = json_data["detail"]
    detail_y = icon2_y + icon2_height + 20
    detail_index = 1
    for key, value in detail.items():
        key_with_index = f"{detail_index}. {key}"
        draw.text((summary_x, detail_y), key_with_index, font=font_summary, fill=(51, 51, 51, 255))
        detail_y += font_summary.getbbox(_("测"))[3] + 8

        value_chars = list(value)
        value_current_line = ""
        value_lines = []
        for char in value_chars:
            test_line = value_current_line + char
            if draw.textlength(test_line, font=font_summary_advise_text) <= (max_width_summary - 20):
                value_current_line = test_line
            else:
                value_lines.append(value_current_line)
                value_current_line = char
        if value_current_line:
            value_lines.append(value_current_line)

        for line in value_lines:
            draw.text((summary_x + 20, detail_y), line, font=font_summary_advise_text, fill=(51, 51, 51, 200))
            detail_y += font_summary_advise_text.getbbox(_("测"))[3] + 5
        detail_index += 1
        detail_y += 15
    # ---------------------- 10. 裁剪内容画布到实际高度 ----------------------
    content_total_height = detail_y + 20
    temp_canvas_cropped = temp_canvas.crop((0, 0, target_width, content_total_height))

    # ---------------------- 11. 处理背景图：保留顶部300px、底部300px，中间裁剪拼接 ----------------------
    # 缩放背景图的顶部300px和底部300px（按比例）
    bg_top_height_original = 50
    bg_bottom_height_original = 50
    bg_top_height_scaled = int(bg_top_height_original * bg_scale_ratio)
    bg_bottom_height_scaled = int(bg_bottom_height_original * bg_scale_ratio)

    # 裁剪背景图的顶部和底部（缩放后）
    bg_img_scaled = bg_img.resize((target_width, int(bg_height * bg_scale_ratio)), Image.Resampling.LANCZOS)
    bg_top = bg_img_scaled.crop((0, 0, target_width, bg_top_height_scaled))
    bg_bottom = bg_img_scaled.crop(
        (0, bg_img_scaled.height - bg_bottom_height_scaled, target_width, bg_img_scaled.height))

    # 计算中间需要的背景高度（内容高度 - 顶部高度）
    bg_mid_needed_height = content_total_height - bg_top_height_scaled
    if bg_mid_needed_height < 0:
        bg_mid_needed_height = 0

    # 裁剪背景图的中间部分（从顶部300px后取需要的高度）
    bg_mid_start_y = bg_top_height_scaled
    bg_mid_end_y = bg_mid_start_y + bg_mid_needed_height
    if bg_mid_end_y > bg_img_scaled.height - bg_bottom_height_scaled:
        bg_mid_end_y = bg_img_scaled.height - bg_bottom_height_scaled
    bg_mid = bg_img_scaled.crop((0, bg_mid_start_y, target_width, bg_mid_end_y))

    # ---------------------- 12. 拼接背景图：顶部 + 中间 + 底部 ----------------------
    final_bg_height = bg_top_height_scaled + bg_mid_needed_height + bg_bottom_height_scaled
    final_bg = Image.new("RGBA", (target_width, final_bg_height), (255, 255, 255, 0))
    # 粘贴顶部
    final_bg.paste(bg_top, (0, 0))
    # 粘贴中间
    final_bg.paste(bg_mid, (0, bg_top_height_scaled))
    # 粘贴底部
    final_bg.paste(bg_bottom, (0, bg_top_height_scaled + bg_mid_needed_height))

    # ---------------------- 13. 将内容叠加到背景图（内容从顶部px开始） ----------------------
    final_img = Image.new("RGBA", (target_width, final_bg_height), (255, 255, 255, 0))
    final_img.paste(final_bg, (0, 0))
    # 内容叠加位置：背景顶部px（缩放后）对应内容的0位置
    final_img.paste(temp_canvas_cropped, (0, 0), mask=temp_canvas_cropped)

    # ---------------------- 14. 保存图片（无损PNG） ----------------------
    os.makedirs(IMAGE_DIR, exist_ok=True)
    final_img.save(local_img_path, format="PNG")
    logger.info("深度报告图片保存生成==========")
    # 4. 读取本地图片并上传到 COS（用文件流替代 Image 对象）
    try:
        response = uploadFile(f"{IMAGE_DIR}/{file_name}", full_file_name, bucket_name)
        logger.info("深度报告图片上传成功==========")
    finally:
        # 5. 上传完成后删除本地临时文件（必选，避免占用空间）
        # os.remove(local_img_name)
        # os.remove(base_img_path)
        return response

#
def downloadFile(file_url) -> str:
    """
    下载文件
    :param file_url:
    :return:file_name
    """
    from WallPaper.settings.dev import DOWNLOAD_DIR
    parsed_url = urlparse(file_url)
    file_name = os.path.basename(parsed_url.path)
    save_path = f"{DOWNLOAD_DIR}/{file_name}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    response = requests.get(file_url, headers=headers, timeout=10, stream=True)
    response.raise_for_status()
    with open(save_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:  # 过滤空块
                f.write(chunk)
    return file_name
