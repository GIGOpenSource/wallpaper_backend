"""
@Project ：NoBad
@File    ：tool_tools.py
@Author  ：LHB
@Date    ：2025/11/26 9:47
@description :
"""
import base64
import urllib.parse

import requests
import logging

from NoBad.settings.dev import DOWNLOAD_DIR
from tool.token_tools import _redis
from tool.tools import getEnvConfig, logger

def getDouyinClientToken():
    """
    获取抖音client_token（非用户授权），缓存到Redis
    文档：https://developer.open-douyin.com/docs/resource/zh-CN/mini-app/develop/server/basic-abilities/interface-request-credential/non-user-authorization/get-client_token
    :return: str/client_token 或 False
    """
    # Redis缓存key
    redis_key = "douyin_access_token"
    # 1. 先从Redis获取缓存
    cached_token = _redis.getKey(redis_key)
    if cached_token:
        logger.info("从Redis获取抖音client_token成功")
        return cached_token
    # 2. 缓存不存在，调用抖音接口获取
    try:
        # 获取环境配置
        appid = getEnvConfig("DOUYIN_AppID")
        app_secret = getEnvConfig("DOUYIN_AppSecret")

        token_url = getEnvConfig("DOUYIN_GET_TOKEN") or "https://open.douyin.com/oauth/client_token/"
        # 验证配置完整性
        if not (appid and app_secret):
            logger.error("抖音AppID或AppSecret未配置")
            return False
        # 构造请求参数（grant_type固定为client_credential）
        params = {
            "grant_type": "client_credential",
            "client_key": appid,
            "client_secret": app_secret
        }
        headers = {'Content-Type': 'application/json'}
        # 调用抖音接口
        response = requests.post(
            url=token_url,
            headers=headers,
            json=params,  # 直接传json参数，requests会自动序列化
            timeout=10
        )
        response.raise_for_status()  # 抛出HTTP状态码异常（如404、500）
        result = response.json()
        result = result['data']
        # 处理响应结果
        if result.get("error_code") == 0:
            access_token = result["access_token"]
            expires_in = result["expires_in"]  # 抖音返回有效期（默认7200秒=2小时）
            if 'access_token' in result:
                _redis.setKey(redis_key, access_token, ex=expires_in)
                logger.info(f"获取抖音client_token成功11，缓存{expires_in}秒")
                return access_token
            else:
                return False
        else:
            err_msg = result.get("description", "token获取失败")
            logger.error(f"获取抖音client_token失败：err_no={result.get('error_code')}, err_tips={err_msg}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"抖音client_token接口请求异常：{str(e)}")
        return False
    except Exception as e:
        logger.error(f"获取抖音client_token未知异常：{str(e)}")
        return False


from io import BytesIO
def generate_qrcode(openid: str,qrcode=None ):
    # 1. 生成抖音唤起 URL
    base_path = "pages/index/index"

    encoded_path = urllib.parse.quote(base_path)  # 编码页面路径（如 "pages/index/index"）
    encoded_openid = urllib.parse.quote(openid)
    share_url = (
            f"douyin://dl/business/?t=123456"  # t 参数为固定占位符，无需修改
            f"&path={encoded_path}%3Fuserid%3D{encoded_openid}"  # %3F 是 "?" 的编码，%3D 是 "=" 的编码
    )
    # 2. 生成普通二维码图片
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(share_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    # 3. 返回图片给前端（字节流形式）
    buffer = BytesIO()
    img.save(buffer, format="PNG")



def generateDouyinQRCode(openId):
    """
    生成抖音小程序二维码（支持方形码/抖音圆码，永久有效）
    文档：https://developer.open-douyin.com/docs/resource/zh-CN/mini-app/develop/server/basic-abilities/url-and-qrcode/qrcode/create-qr-code-v2
    :param openId: 用户openId（拼接至path参数，用于页面跳转传参）
    :return: 二维码保存路径（成功）/ None（失败）
    """
    logger.info("生成抖音二维码")
    # 1. 获取抖音access_token（client_token，复用之前的工具函数）
    access_token = getDouyinClientToken()
    if not access_token:
        logger.error("获取抖音access_token失败，无法生成二维码")
        return None

    # 2. 构造请求配置
    base_url = getEnvConfig("DOUYIN_QRCODE_URL")
    appid = getEnvConfig("DOUYIN_AppID")
    if not appid:
        logger.error("抖音AppID未配置")
        return None

    # 3. 构造path参数（小程序页面路径+openId参数，需URL编码）
    page_path = "pages/index/index"
    query_params = f"share_uid={openId}"
    # 按文档要求：小程序path格式为 encode({path}?{query})
    import urllib.parse
    full_path = urllib.parse.quote(f"{page_path}?{query_params}")
    # 4. 构造请求体数据
    data = {
        "appid": appid,
        "app_name": "douyin",  # 固定为抖音
        "path": full_path,
        "width": 430,  # 默认430px，符合抖音推荐尺寸
        "line_color": {"r": 0, "g": 0, "b": 0},  # 线条黑色
        "background": {"r": 255, "g": 255, "b": 255},  # 背景白色
        "is_circle_code": False,  # False=方形码，True=抖音圆码，按需修改
        "set_icon": False  # 不展示小程序图标，按需修改
    }
    # 5. 构造请求头
    headers = {
        "Content-Type": "application/json",
        "access-token": access_token
    }

    try:
        # 6. 调用抖音生成二维码接口
        response = requests.post(base_url, headers=headers, json=data, timeout=15)
        result = response.json()
        # 7. 处理响应结果
        if result.get("err_no") != 0:
            err_msg = result.get("err_msg", "生成二维码失败")
            logger.error(f"抖音API返回错误：err_no={result.get('err_no')}, err_msg={err_msg}")
            # 若token无效，删除缓存重新获取
            if result.get("err_no") == 28001008:
                _redis.delKey("douyin_access_token")
                logger.info("抖音access_token无效，已删除缓存")
            return None

        # 8. 解析base64编码的二维码图片
        base64_img = result["data"].get("img")
        if not base64_img:
            logger.error("抖音API未返回二维码图片数据")
            return None

        # 9. base64解码并保存图片
        save_path = f"{openId}.png"
        full_save_path = f"{DOWNLOAD_DIR}/{save_path}"
        try:
            img_data = base64.b64decode(base64_img)
            with open(full_save_path, "wb") as f:
                f.write(img_data)
            logger.info(f"抖音小程序二维码已保存到：{full_save_path}")
            return save_path
        except (base64.binascii.Error, IOError) as e:
            logger.error(f"解码或保存抖音二维码失败：{str(e)}")
            return None
    except requests.RequestException as e:
        logger.error(f"网络请求异常：{str(e)}")
        return None
    except Exception as e:
        logger.error(f"生成抖音二维码失败：{str(e)}")
        return None

#
# @transaction.atomic
# def updataOrderNotify(data: dict):
#     """
#     创建订单
#     :param data:
#     :return:
#     """
#     try:
#         openid = data["payer"]["openid"]
#         out_trade_no = data["out_trade_no"]
#         userData = _.objects.get(open_id=openid)
#         orderData = Order.objects.get(out_trade_no=out_trade_no, openid=openid)
#         productData = Product.objects.get(id=orderData.product_id)
#         orderData.transaction_id = data["transaction_id"]
#         orderData.total_fee = float(data["amount"]["total"] / 100)
#         orderData.payer_total = float(data["amount"]["payer_total"] / 100)
#         orderData.fee_type = data["amount"]["currency"]
#         orderData.trade_type = data["trade_type"]
#         orderData.trade_state = data["trade_state"]
#         orderData.pay_time = str(data["success_time"]).replace("T", " ").strip("+08:00")
#         orderData.update_time = datetime.now()
#         orderData.notify_time = str(data["success_time"]).replace("T", " ").strip("+08:00")
#         orderData.is_notify_processed = True
#         days = productData.days
#         logger.info(f"准备更新的数据为==>:{data}")
#         logger.info(f"订单data===>：{orderData}")
#         logger.info(f"用户为==>:{userData.username}")
#         logger.info(f"用户充值类型为==>:{productData.product_type}")
#         logger.info(f"充值天数为==>:{days}天")
#         if productData.product_type == "vip":
#             userData.is_vip = True
#             userData.vip_type = productData.name
#             old_date = userData.vip_expire_date
#             if old_date:
#                 userData.vip_expire_date = old_date + timedelta(days=int(days))
#             else:
#                 userData.vip_expire_date = datetime.now() + timedelta(days=int(days))
#             userData.save()
#         if productData.product_type == "once":
#             logger.info(f"更新的父 posterid为==>:{orderData.posterId}")
#             posterDeep = UserPoster.objects.get(parent_id=orderData.posterId)
#             posterDeep.is_active_by_user = "True"
#             posterDeep.save()
#         orderData.save()
#         logger.info(f"更新订单成功,更新结果为:{model_to_dict(orderData)}")
#         return True
#     except Order.DoesNotExist:
#         pass