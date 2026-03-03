from App.view.poster.view import safe_parse_json
from models.models import StarSignDict
from tool.middleware import logger
from tool.tools import getEnvConfig


def calculate_zodiac_sign(birth_datetime, timezone_str='Asia/Shanghai'):
    """
    根据出生日期时间计算星座
    :param birth_datetime: datetime对象或日期字符串
    :param timezone_str: 时区字符串，默认'Asia/Shanghai'
    :return: 星座编码（如：aries, taurus等）
    """
    from django.utils import timezone
    import pytz
    # 转换为datetime对象
    if isinstance(birth_datetime, str):
        try:
            # 尝试解析ISO格式
            from dateutil import parser
            birth_dt = parser.parse(birth_datetime)
        except Exception:
            return None
    else:
        birth_dt = birth_datetime
    # 处理时区
    if birth_dt.tzinfo is None:
        local_tz = pytz.timezone(timezone_str)
        birth_dt = local_tz.localize(birth_dt)
    # 转换为UTC时间
    utc_dt = birth_dt.astimezone(pytz.UTC)
    # 获取月和日
    month = utc_dt.month
    day = utc_dt.day
    # 判断星座（使用UTC日期）
    if (month == 3 and day >= 21) or (month == 4 and day <= 19):
        return "白羊座"  # aries
    elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
        return "金牛座"  # taurus
    elif (month == 5 and day >= 21) or (month == 6 and day <= 21):
        return "双子座"  # gemini
    elif (month == 6 and day >= 22) or (month == 7 and day <= 22):
        return "巨蟹座"  # cancer
    elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
        return "狮子座"  # leo
    elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
        return "处女座"  # virgo
    elif (month == 9 and day >= 23) or (month == 10 and day <= 23):
        return "天秤座"  # libra
    elif (month == 10 and day >= 24) or (month == 11 and day <= 22):
        return "天蝎座"  # scorpio
    elif (month == 11 and day >= 23) or (month == 12 and day <= 21):
        return "射手座"  # sagittarius
    elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
        return "摩羯座"  # capricorn
    elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
        return "水瓶座"  # aquarius
    elif (month == 2 and day >= 19) or (month == 3 and day <= 20):
        return "双鱼座"  # pisces
    return None


def get_zodiac_with_gender(zodiac_code, gender):
    """
    根据星座编码和性别生成带性别的星座标识
    :param zodiac_code: 星座编码（如：aries）
    :param gender: 性别（'male'或'female'）
    :return: 带性别的星座标识（如：摩羯男、射手女）
    """
    if not zodiac_code:
        return None
    # 根据性别添加后缀
    if gender.lower() == 'male':
        return f"{zodiac_code}_m"
    elif gender.lower() == 'female':
        return f"{zodiac_code}_f"
    else:
        return zodiac_code

def get_zodiac_english_name(chinese_name):
    """
    将中文星座名称转换为对应的英文标识
    :param chinese_name: 中文星座名（如"摩羯座"、"白羊座"）
    :return: 英文标识（如"capricorn"、"aries"），无匹配返回None
    """
    # 从StarSignDict的ZODIAC_NAME_CHOICES中反向查找
    zodiac_mapping = {v: k for k, v in StarSignDict.ZODIAC_NAME_CHOICES}
    return zodiac_mapping.get(chinese_name)

def get_zodiac_chinese_name(english_name):
    """
    将英文星座名称转换为对应的中文名称
    :param english_name: 英文星座名（如"capricorn"、"aries"）
    :return: 中文星座名（如"摩羯座"、"白羊座"），无匹配返回None
    """
    # 从StarSignDict的ZODIAC_NAME_CHOICES中查找
    zodiac_mapping = {k: v for k, v in StarSignDict.ZODIAC_NAME_CHOICES}
    return zodiac_mapping.get(english_name)


def ai_generate_daily_mood(zodiac_name, gender, today):
    """
    模拟AI生成每日星座心情数据
    实际项目中这里会调用真实的AI接口
    """
    import random
    providers = ["deepseek","qwen","volcengine",]  # 可用的模型提供商列表
    result = {}
    for provider in providers:
        try:
            logger.info(f"尝试使用 {provider} 模型生成塔罗牌深度分析...")
            data = {
                "gender": gender,
                "zodiac_name": zodiac_name,
                "today": today,
            }
            model_client = Simple_LargeModelClient(
                user_data=data,
                model_provider=provider,
            )
            result = model_client.generate_response()
            parsed_data = safe_parse_json(result)
            result = parsed_data.get("result", {})
            if result:
                logger.info(f"使用 {provider} 模型生成塔罗牌深度分析成功")
                return result
        except Exception as e:
            logger.error(f"使用 {provider} 模型生成塔罗牌深度分析失败: {str(e)}")
            # 模拟AI生成的数据
            continue
    if not result:
        result = {
            "encourage_sentence": f"今日{zodiac_name}的你，充满活力与机遇！",
            "mood_score": random.randint(60, 95),
            "love_score": random.randint(50, 90),
            "wealth_score": random.randint(45, 85),
            "career_score": random.randint(55, 88),
            "study_score": random.randint(40, 80),
            "contact_score": random.randint(50, 90)
        }
    return result

from django.utils.translation import get_language,gettext as _
from volcenginesdkarkruntime import Ark
from openai import OpenAI

class Simple_LargeModelClient(object):
    """
    统一大模型调用类，支持火山引擎和DeepSeek
    """
    def __init__(self,model_provider: str = "volcengine",
                 poster_type:str = "mood",model: str = None,
                 user_data: dict = None,add_text=None,):
        self.model_provider = model_provider
        self.poster_type = poster_type
        self.user_data = user_data or {}
        # 根据提供商设置配置
        if self.model_provider == "volcengine":
            self.model = model or getEnvConfig("ARK_MODEL")
            self.base_url = getEnvConfig("VOLCENGINE_BASE_URL")
            self.api_key = getEnvConfig("ARK_API_KEY")
            self.client = Ark(api_key=self.api_key)
        elif self.model_provider == "deepseek":  # deepseek
            self.model = model or getEnvConfig("DS_MODEL")
            self.base_url = "https://api.deepseek.com"
            self.api_key = getEnvConfig("DS_API_KEY")
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        elif self.model_provider == "qwen":  # deepseek
            self.model = model or getEnvConfig("QW_MODEL")
            self.base_url = getEnvConfig("QW_BASE_URL")
            self.api_key = getEnvConfig("QW_API_KEY")
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.messages = self._build_messages(add_text)
    def _build_messages(self, add_text):
        """
        构建消息内容
        """
        content = []
        message_add = ""
        if self.poster_type == "mood":
            template = _("用户星座：{zodiac_name}，用户性别：{gender},今日日期{today}"
                         "{instructions}")
            message_add = template.format(
                zodiac_name=str(self.user_data["zodiac_name"]),
                gender=str(self.user_data["gender"]),
                today=str(self.user_data["today"]),
                instructions=_("""
                # 一、角色
                你是一个星座心情表，结合当天的用户星座和用户性别。
                # 二、强制输出规则（违反则无效）
                1. 输出格式为标准JSON，无任何多余内容（无注释、无换行、无特殊符号、无代码块），可直接用json.loads解析。
                2. 严格遵循以下结构，字段不可缺失、不可新增。
                # 三、输出结构（强制要求,正确的结构）
                   {
                        "result": {
                        "encourage_sentence": "鼓励今天的该星座的一句话",
                        "mood_score": 26(示例分数，下面的按实际情况的来),
                        "love_score": 85,
                        "wealth_score": 00,
                        "career_score": 00,
                        "study_score": 98,
                        "contact_score": 00,
                        }
                    }
                # 三、中文返回结果
                """)
            )
        content.append({"type": "text", "text": message_add})
        logger.info(f"======最终的输出参数为：{content}")
        return [{"role": "user", "content": content}]
    def generate_response(self):
        """
        调用大模型生成响应
        :return: 模型生成的内容
        """
        if self.model_provider == "volcengine":
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages
            )
        else:  # deepseek
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                stream=False
            )
        result = completion.choices[0].message.content
        return result