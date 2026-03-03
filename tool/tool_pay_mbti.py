from django.http import JsonResponse

from models.models import UserPoster
from tool.middleware import logger
from tool.token_tools import mbti_redis
from tool.tools import CustomStatus


def handle_double_mbti_pay_status(posterId, product, body):
    """
    处理双人MBTI房间支付状态逻辑
    :param posterId: 海报ID
    :param product: 产品对象（包含product_code属性）
    :param body: 请求体（包含pay_action等参数）
    :return: JsonResponse | None（有返回值则直接返回，None则继续后续逻辑）
    """
    try:
        if "double" in product.product_code:
            poster = UserPoster.objects.get(id=posterId)
            unique_key = poster.unique_key
            if poster.content.get("master",""):
                inviter_id = poster.user_id
            else:
                if poster.content.get("inviter","") and unique_key:
                    inviter_id = poster.content.get("inviter","")
                else:
                    poster = UserPoster.objects.get(id=poster.parent_id)
                    inviter_id = poster.content.get("inviter", "")
                    unique_key = poster.unique_key
            room_info = mbti_redis.get_room_info_by_key(
                host_id=inviter_id,
                unique_key=unique_key
            )
            if room_info:
                cancel_pay = body.get("pay_action")
                if cancel_pay == "cancel_pay":
                    data = {"room_pay_status": "affordable"}
                    mbti_redis.update_room_info_by_key(host_id=int(inviter_id),
                                                       unique_key=unique_key, **data)
                    return JsonResponse({
                        "code": 200,
                        "message": f"取消成功，当前状态为affordable",
                        "data": None
                    })
                room_pay_status = room_info.get("room_pay_status")
                if room_pay_status == "affordable":
                    data = {"room_pay_status": "other_paying"}
                    mbti_redis.update_room_info_by_key(host_id=int(inviter_id),
                                                       unique_key=unique_key, **data)
                else:
                    return JsonResponse({
                        "code": 400,
                        "message": f"不可支付当前状态为 {room_pay_status}",
                        "data": None
                    })
    except Exception as e:
        logger.error(f"获取海报内容失败: {str(e)}")
        return JsonResponse(CustomStatus.GET_POSTER_CONTENT_ERROR.to_response())
    return None