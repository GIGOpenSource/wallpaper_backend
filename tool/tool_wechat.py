#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：NoBad 
@File    ：tool_wechat.py
@Author  ：LYP
@Date    ：2025/10/31 16:06 
@description :
"""
import json
import time
import os
from datetime import datetime, timedelta
import json5
import requests
from NoBad.settings.dev import KEY_DIR
from base64 import b64encode, b64decode
from django.db import transaction
from Cryptodome.PublicKey import RSA
from Cryptodome.Signature import pkcs1_15
from Cryptodome.Hash import SHA256
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.forms import model_to_dict

from models.models import WeChatUser as _, WeChatPayOrder as Order, Product, UserPoster, AITrialCase
from tool.tools import getEnvConfig, logger
from tool.token_tools import _redis


@transaction.atomic
def checkWechatUserIsExist(openId: str, session_key: str, types: str, username: str = None, avatar: str = None,
                           phone: str = None,gender: str=None,platform: str=None) -> _ or bool:
    """
    获取用户是否存在
    :param openId: 用户唯一标识
    :param session_key: session
    :param types: create update
    :param username: 用户昵称
    :param avatar: 头像
    :param phone: 手机号
    :return:
    """
    if types == "update":
        _.objects.filter(open_id=openId).update(user_telphone=phone)
        return True
    try:
        data = _.objects.get(open_id=openId)

    except _.DoesNotExist:
        data = _.objects.create(open_id=openId, is_vip=False, session_key=session_key, share_success_count=0, allow_count=0,
                                fail_count=0, created_at=datetime.now(),username=username, user_avatar=avatar, user_gender=gender,platform=platform)
    return data


def getWechatAccessToken():
    """
    获取微信access token
    :return:
    """
    key = "access_token"
    access_token = _redis.getKey(key)
    if access_token:
        return access_token
    else:
        appId = getEnvConfig("APPID")
        appSecret = getEnvConfig("APPSECRET")
        baseUrl = getEnvConfig("WECHAT_BASE_URL")
        endPath = getEnvConfig("GET_ACCESS_TOKEN_END_PATH").format(appId, appSecret)
        url = baseUrl + endPath
        response = requests.get(url).json()
        if 'access_token' in response.keys():
            access_token = response['access_token']
            expire_seconds = 7200 # 2小时
            _redis.setKey(key, access_token, ex=expire_seconds)
            return access_token
        else:
            return False


def genterateWechatAuth(body: str, nonceStr: str, timestamp):
    """
    构造微信支付 Authorization
    :param body:
    :param nonceStr:
    :param timestamp
    :return:
    """
    # 1 生成签名字符串

    end_path = getEnvConfig("WECHAT_PAY_JSAPI_METHOD")
    mchId = getEnvConfig("WECHAT_MCHID")
    serialNo = getEnvConfig("WECHAT_SerialNo")
    genteate_sign_str = f"POST\n{end_path}\n{timestamp}\n{nonceStr}\n{body}\n"
    with open(f"{KEY_DIR}/apiclient_key.pem") as f:
        rsa_key = RSA.importKey(f.read())
    signer = pkcs1_15.new(rsa_key)
    digest = SHA256.new(genteate_sign_str.encode('utf8'))
    sing_str = b64encode(signer.sign(digest)).decode('utf8')
    authorization = 'WECHATPAY2-SHA256-RSA2048 ' \
                    'mchid="%s",' \
                    'nonce_str="%s",' \
                    'signature="%s",' \
                    'timestamp="%s",' \
                    'serial_no="%s"' \
                    % (mchId,
                       nonceStr,
                       sing_str,
                       timestamp,
                       serialNo
                       )
    return authorization


def decryptData(nonce, ciphertext, associated_data):
    """
    解密数据
    :param nonce:
    :param ciphertext:
    :param associated_data:
    :return:
    """
    key_bytes = str.encode(getEnvConfig("WECHAT_API_KEY"))
    nonce_bytes = str.encode(nonce)
    ad_bytes = str.encode(associated_data)
    data = b64decode(ciphertext)
    aesgcm = AESGCM(key_bytes)
    data_str = aesgcm.decrypt(nonce_bytes, data, ad_bytes).decode('utf-8')
    data_list = list(data_str)
    data_list.pop(0)
    data_list.pop(data_list.__len__() - 1)
    data_list_str = "".join(data_list)
    _ = data_list_str.split(",")
    data_source = list()
    for i in _:
        data_source.append("".join(i))
    data_json = "{" + ",".join(data_source) + "}"
    _json = json5.loads(data_json)
    # _json = None
    print("_json===>", _json)
    return _json


@transaction.atomic
def updataOrderNotify(data: dict):
    """
    创建订单
    :param data:
    :return:
    """
    try:
        openid = data["payer"]["openid"]
        out_trade_no = data["out_trade_no"]
        userData = _.objects.get(open_id=openid)
        orderData = Order.objects.get(out_trade_no=out_trade_no, openid=openid)
        productData = Product.objects.get(id=orderData.product_id)
        orderData.transaction_id = data["transaction_id"]
        orderData.total_fee = float(data["amount"]["total"] / 100)
        orderData.payer_total = float(data["amount"]["payer_total"] / 100)
        orderData.fee_type = data["amount"]["currency"]
        orderData.trade_type = data["trade_type"]
        orderData.trade_state = data["trade_state"]
        orderData.pay_time = str(data["success_time"]).replace("T", " ").strip("+08:00")
        orderData.update_time = datetime.now()
        orderData.notify_time = str(data["success_time"]).replace("T", " ").strip("+08:00")
        orderData.is_notify_processed = True
        days = productData.days
        logger.info(f"准备更新的数据为==>:{data}")
        logger.info(f"订单data===>：{orderData}")
        logger.info(f"用户为==>:{userData.username}")
        logger.info(f"用户充值类型为==>:{productData.product_type}")
        logger.info(f"充值天数为==>:{days}天")
        if "vip" in productData.product_type:
            userData.is_vip = True
            userData.vip_type = productData.name
            old_date = userData.vip_expire_date
            if old_date:
                userData.vip_expire_date = old_date + timedelta(days=int(days))
            else:
                userData.vip_expire_date = datetime.now() + timedelta(days=int(days))
            userData.save()
        if "once" in productData.product_type:
            logger.info(f"更新的父 posterid为==>:{orderData.posterId}")
            try:
                # 尝试获取子记录
                posterDeep = UserPoster.objects.get(parent_id=orderData.posterId)
                posterDeep.is_active_by_user = "True"
                posterDeep.save()
            except UserPoster.DoesNotExist:
                # 如果子记录不存在，则更新id等于posterId的记录
                try:
                    poster = UserPoster.objects.get(id=orderData.posterId)
                    poster.is_active_by_user = "True"
                    poster.save()
                except UserPoster.DoesNotExist:
                    logger.error(f"未找到id为{orderData.posterId}的海报记录")

        def update_poster_status(poster, is_active=True, pay_status="pay_completed"):
            """更新海报的激活状态和支付状态"""
            poster.is_active_by_user = is_active  # 改用布尔值，而非字符串"True"
            poster.content["room_pay_status"] = pay_status
            poster.save()
        if "trial_case" in productData.product_type:
            poster_id = orderData.posterId
            trial_poster = UserPoster.objects.get(id=poster_id)
            # 使用 filter 获取所有具有相同 unique_key 的记录
            related_posters = UserPoster.objects.filter(unique_key=trial_poster.unique_key)
            # 遍历所有相关记录并将 is_active_by_user 设置为 "True"
            for poster in related_posters:
                poster.is_active_by_user = "True"
                poster.status = "waiting"
                poster.save()
            case_number = trial_poster.unique_key.split("@")[1]
            related_trialcase = AITrialCase.objects.filter(case_number=case_number)
            for trial_case in related_trialcase:
                trial_case.status = "done"
                trial_case.save()

        if "mbti" in productData.product_type:
            poster_id = orderData.posterId
            try:
                if "single" in productData.product_type:
                    # 处理单人海报逻辑
                    single_poster = UserPoster.objects.get(id=poster_id)
                    update_poster_status(single_poster)
                elif "double" in productData.product_type:
                    # 处理双人海报逻辑
                    double_poster = UserPoster.objects.get(id=poster_id)
                    unique_key = None
                    otherId = None
                    # 根据海报类型获取关联信息
                    if double_poster.parse_type == "once_mbti":  # 父类
                        unique_key = double_poster.unique_key
                        content = double_poster.content
                        otherId = content.get("invitee") if content.get("master") else content.get("inviter")
                        other_parent = UserPoster.objects.get(user_id=otherId, unique_key=unique_key)
                        other_self = UserPoster.objects.get(parent_id=poster_id)
                        other_child = UserPoster.objects.get(parent_id=other_parent.id)
                    elif double_poster.parse_type == "once_mbti_double":  # 子类
                        other_self = UserPoster.objects.get(id=double_poster.parent_id)
                        unique_key = other_self.unique_key
                        content = other_self.content
                        otherId = content.get("invitee") if content.get("master") else content.get("inviter")
                        other_parent = UserPoster.objects.get(user_id=otherId, unique_key=unique_key)
                        other_child = UserPoster.objects.get(parent_id=other_parent.id)
                    # 批量更新所有关联海报
                    for poster in [double_poster, other_self, other_parent, other_child]:
                        update_poster_status(poster)
                # 更新用户MBTI激活状态（原代码else分支逻辑修正）
                userData.mbti_is_active = True
            except UserPoster.DoesNotExist as e:
                logger.error(f"未找到海报记录，海报ID：{poster_id}，错误信息：{str(e)}")
            except Exception as e:
                logger.error(f"更新MBTI海报状态失败，海报ID：{poster_id}，错误信息：{str(e)}")
            logger.info(f"更新MBTI海报状态，海报ID：{poster_id}")
        orderData.save()
        logger.info(f"更新订单成功,更新结果为:{model_to_dict(orderData)}")
        return True
    except Order.DoesNotExist:
        pass

def generateSign(timestamp, nonceStr, packId):
    """
    生成小程序调起支付签名
    :param timestamp: 秒级时间戳（str/int，如1554208460）
    :param nonceStr: 随机字符串（与支付调用一致）
    :param packId: 完整格式的prepay_id（如"prepay_id=xxx"）
    :return: base64编码的签名串
    """
    try:
        # 1. 获取并验证appId
        appId = getEnvConfig("APPID")
        if not appId or not appId.startswith("wx"):
            raise ValueError(f"无效的APPID: {appId}（需为小程序APPID）")

        # 2. 构造签名串（严格按文档格式，结尾必须带\n）
        data = f"{appId}\n{timestamp}\n{nonceStr}\nprepay_id={packId}\n"
        logger.info(f"构造的签名串==》{data}")
        print(f"构造的签名串：\n{repr(data)}")  # 打印签名串（repr可显示换行符）

        # 3. 读取私钥（增加路径验证）
        key_path = os.path.join(KEY_DIR, "apiclient_key.pem")
        if not os.path.exists(key_path):
            raise FileNotFoundError(f"私钥文件不存在: {key_path}")
        with open(key_path, "r", encoding="utf-8") as f:
            private_key_content = f.read()
        if "-----BEGIN PRIVATE KEY-----" not in private_key_content:
            raise ValueError("私钥格式错误：需为PKCS#8格式（BEGIN PRIVATE KEY）")

        # 4. 签名计算（SHA256 with RSA + Base64）
        private_key = RSA.importKey(private_key_content)
        hash_obj = SHA256.new(data.encode("utf-8"))
        signer = pkcs1_15.new(private_key)
        signature = signer.sign(hash_obj)
        encoded_signature = b64encode(signature).decode("utf-8")
        logger.info(f"base64构造的签名串==》\n{encoded_signature}")
        return encoded_signature

    except Exception as e:
        print(f"签名生成失败：{str(e)}")


# TODO
def genterateUnlimitedQRCode(openId):
    """
    生成小程序码
    :param openId:
    env_version 正式版为 "release"，体验版为 "trial"，开发版为 "develop"。
    :return:
    """
    from NoBad.settings.dev import DOWNLOAD_DIR
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
        response = requests.post(url, json=data)
        save_path = f"{openId}.png"
        content_type = response.headers.get('Content-Type', '')
        if content_type.startswith('image/'):
            image_data = response.content
            if save_path:
                try:
                    with open(f"{DOWNLOAD_DIR}/{save_path}", 'wb') as f:
                        f.write(image_data)
                    logger.info(f"二维码已保存到: {DOWNLOAD_DIR}/{save_path}")
                except IOError as e:
                    logger.error(f"保存二维码文件失败: {str(e)}")
            return save_path
        else:
            try:
                error_result = response.json()
                logger.error(f"微信API返回错误: {error_result}")
                key = "access_token"
                access_token = _redis.delKey(key)
                logger.info(f"重新获取access_token==>{access_token}")
            except ValueError:
                logger.error(f"无法解析微信API响应: {response.text}")
            return None

    except requests.RequestException as e:
        logger.error(f"网络请求异常: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"生成二维码过程中发生错误: {str(e)}")
        return None

