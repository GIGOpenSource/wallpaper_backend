#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：Crush_Check
@File    ：larg_models_tool.py
@Author  ：LHB
@Date    ：2026/01/19 15:19
@description :
"""
from typing import Optional, List, Dict, Any

from volcenginesdkarkruntime import Ark

from models.models import PromptTemplate
from tool.tools import getEnvConfig, logger
from django.utils.translation import get_language,gettext as _

class VolcEngineArk(object):
    """"""
    def __init__(self, image_url_list:  Optional[List[str]] = None, prompt_id: Optional[int] = None, model: str = getEnvConfig("ARK_MODEL"), add_text=None,question=None,answer=None,poster_type=None):
        self.image_urls = image_url_list
        self.prompt_id = prompt_id
        self.model = model
        self.base_url = getEnvConfig("VOLCENGINE_BASE_URL")
        self.api_key = getEnvConfig("ARK_API_KEY")
        self.client = Ark(api_key=self.api_key)
        self.prompt_text = self.get_prompt_text()
        self.question = question
        self.answer = answer
        self.poster_type = poster_type
        content = []
        message_add = ""
        if self.poster_type == "answer":
            message_add = _("用户提问：")+str(question)+"。" + _("用户答案：")+str(answer)+_("""
             # 一、强制输出规则（违反则无效）
            1. 输出格式为标准JSON，无任何多余内容（无注释、无换行、无特殊符号、无代码块），可直接用json.loads解析。
            2. 严格遵循以下结构，字段不可缺失、不可新增。
            # 二、输出结构（强制要求,正确的结构）
                    {
                        "result": {
                            "key_points":"要点",
                            "summary": "展开回答"
                        },
                    }
            # 三、中文返回结果
            """)
        if self.poster_type == "crush_check" and not self.image_urls:
            raise ValueError(_("请传入至少一个图片地址"))
        if self.poster_type == "crush_check":
            content = [{"type": "image_url", "image_url": {"url": url}} for url in self.image_urls]
        if self.poster_type == "tarot_card":
            message_add = _("用户提问：") + str(question) + "。" + _("用户抽中的牌为：") + str(answer) + _("""
                         # 一、强制输出规则（违反则无效）
                        1. 输出格式为标准JSON，无任何多余内容（无注释、无换行、无特殊符号、无代码块），可直接用json.loads解析。
                        2. 严格遵循以下结构，字段不可缺失、不可新增。
                        # 二、输出结构（强制要求,正确的结构）
                                {
                                    "result": {
                                        "summary": "核心能量：xxxxx。/n 
                                        情感人际：xxxxx。/n
                                        xxx：xxx。/n 
                                        使用'/n'换行输出"
                                    },
                                }
                        # 三、中文返回结果
                        """)
        if self.poster_type == "crush_check":
            message_add = _("""
            # 一、强制输出规则（违反则无效）
            1. 输出格式为标准JSON，无任何多余内容（无注释、无换行、无特殊符号、无代码块），可直接用json.loads解析。
            2. 严格遵循以下结构，字段不可缺失、不可新增，数据类型正确（分数为整数，summary为字符串）。
            3. 根据对话判断对方是男或女，不用表述出来，仅在gender数据里。
            4. 整数分数0-100分。
            # 二、输出结构（强制要求,正确的结构）
                    {
                        "result": {
                            "poster": {
                                "flags": {"关键词1": 整数分数, "关键词2": 整数分数, "关键词3": 整数分数, "关键词4": 整数分数},
                                "summary": "一句话总结（格式：TA是一个XXXX，字数20-30字）"
                                "gender":"male或female"
                                },
                                "report": {
                                    "summary": "法医结论行动建议一句话总结（格式：字数200字）不显示“法医结论字样”",
                                    "flags": {"风险关键词1": 整数分数, "风险关键词2": 整数分数, "风险关键词3": 整数分数, "风险关键词4": 整数分数},
                                    "danger":"最隐蔽风险",
                                    "advise":"行动建议",
                                    "advise_summary":"行动建议核心结论",
                                    "detail":"{"详细解读段落1":"内容","详细解读段落2":"内容","详细解读段落3":"",....}
                                }"
                            }"
                    }
            # 三、输出结构组成示例：
                        reslut:{
                            poster:{
                            “海报要求”
                            }
                            report:{
                            “报告要求”
                            }
                        }
            ### 3.1海报要求：
                必须4个关键词，每个关键字的分数根据分析出的结果应为不同数值：
                flags: {"词1":分数,"词2":分数,"词3":分数,"词4":分数}
                summary:一句话总结（如“TA是一个XXXX”，字数限制为20-40字）
            ### 3.2报告要求：
                必须4个风险评分，每个风险评分关键字有分数
                summary总结,只包含结果，不含标题
                activate行动建议：一句话不分点。
                detail内容为字典格式{"key":"value"}可以有多个
            # 四、中文语言返回结果
            """)
        print(f"======larg_models_tool====当前识别的语言：{get_language()}")
        content.append({"type": "text", "text": self.prompt_text})
        if "输出格式为标准JSON" not in self.prompt_text:
            content.append({"type": "text", "text": message_add})
        if add_text:
            content.append({"type": "text", "text": add_text})
        self.messages = [{"role": "user", "content": content}]
        logger.info(f"======最终的输出参数为：{content}")
    def genterateFlags(self):
        """
        获取分析的结果
        :return:
        """
        completion = self.client.chat.completions.create(model=self.model, messages=self.messages)
        result = completion.choices[0].message.content
        return result

    def get_prompt_text(self):
        """
        获取提示语
        :return:
        """
        prompt = PromptTemplate.objects.get(id=self.prompt_id).prompt_content
        return prompt

from openai import OpenAI
from django.utils.translation import activate

class LargeModelClient(object):
    """
    统一大模型调用类，支持火山引擎和DeepSeek
    """
    def __init__(self, image_url_list: Optional[List[str]] = None,
                 prompt_id: Optional[int] = None,
                 model_provider: str = "volcengine",  # "volcengine" 或 "deepseek"
                 model: str = None,
                 add_text=None,
                 question=None,
                 answer=None,
                 poster_type=None,
                 trialcase_content:Optional[List[Dict[str,Any]]]=None):
        self.image_urls = image_url_list
        self.prompt_id = prompt_id
        self.model_provider = model_provider
        self.question = question
        self.answer = answer
        self.poster_type = poster_type
        self.trialcase_content = trialcase_content
        if not self.question and not self.image_urls and not trialcase_content:
            raise ValueError(_("请传入至少一个图片地址"))
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

        self.prompt_text = self.get_prompt_text()
        self.messages = self._build_messages(add_text)

    def _build_messages(self, add_text):
        """
        构建消息内容
        """
        content = []
        if not self.answer and not self.question:
            if self.model_provider == "volcengine" and self.image_urls:
                content = [{"type": "image_url", "image_url": {"url": url}} for url in self.image_urls]
            else:
                content = [{"type": "text", "text": "请分析用户提供的信息"}]
        message_add = ""
        if self.poster_type == "trial_case":
            content = [{"type": "image_url", "image_url": {"url": url}} for url in self.image_urls]
            template = _("{nick_name1}的视角；{nick_name1}的事件描述：{question1}；{nick_name1}的问题及委屈点：{issue_description1}；"
                         "{nick_name2}的视角；{nick_name2}的事件描述：{question2}；{nick_name2}的问题及委屈点：{issue_description2}；"
                         "{instructions}")
            message_add = template.format(
                nick_name1=self.trialcase_content[0]["nickname"],
                nick_name2=self.trialcase_content[1]["nickname"],
                question1=self.trialcase_content[0]["event_description"],
                question2=self.trialcase_content[1]["event_description"],
                issue_description1=self.trialcase_content[0]["issue_description"],
                issue_description2=self.trialcase_content[1]["issue_description"],
                instructions=_("""
                            # 一、强制输出规则（违反则无效）
                            1. 输出格式为标准JSON，无任何多余内容（无注释、无换行、无特殊符号、无代码块），可直接用json.loads解析。
                            2. 严格遵循JSON结构，字段不可缺失、不可新增、最重要可直接用json.loads解析。
                            3. 参数解读：
                                analysis: 问题原因分析是怎么回事。
                                percentage:问题占比，用户1占比多少用户2占比多少 和为100%。
                                verdict: 最终判决,虚拟一个《爱情法典》第几章触犯了什么，不对。
                                resolution: 和解方案,谁道歉理解....。
                                judge_advice: 本判决自双方签字（或击掌）之日起生效，给点温馨的话。
                                case_name: 案件名，根据事件起个名如2026-XX-00x号（年-名-号 随机就行）。
                                presiding_judge:审判长名称，活泼可爱的名字，如长耳朵小兔法官等。
                                open_court_time:开庭时间名，一个发散的名字，如一个阳关刚好的下午茶时刻。
                            # 二、输出结构（强制要求,正确的结构，不要额外换行，除了内容）
                                {
                                    "result": {
                                        "analysis": ".....",
                                        "percentage": {"user1":xx%,"user2":xx%}",
                                        "verdict": "1、..../n  2、......./n " (使用'/n'换行输出"),
                                        "resolution": "1、..../n  2、......./n (使用'/n'换行输出")",
                                        "judge_advice": "本判决自双方签字（或击掌）之日起生效，......(使用'/n'换行输出")",
                                        "case_name":"xxxx-xxx-xxx号",
                                        "presiding_judge":"审判长名",
                                        "open_court_time":"开庭事件名"
                                    },
                                }
                            # 三、中文返回结果
                            """)
            )
        if self.poster_type == "answer":
            template = _("用户提问：{question}。用户答案：{answer}{instructions}")
            message_add = template.format(
                question=str(self.question),
                answer=str(self.answer),
                instructions=_("""
                 # 一、强制输出规则（违反则无效）
                1. 输出格式为标准JSON，无任何多余内容（无注释、无换行、无特殊符号、无代码块），可直接用json.loads解析。
                2. 严格遵循以下结构，字段不可缺失、不可新增。
                # 二、输出结构（强制要求,正确的结构）
                        {
                            "result": {
                                "key_points":"要点",
                                "summary": "展开回答"
                            },
                        }
                # 三、中文返回结果
                """)
            )
        if self.poster_type == "tarot_card":
            template = _("用户提问：{question}。用户抽中的牌为：{answer}{instructions}")
            message_add = template.format(
                question=str(self.question),
                answer=str(self.answer),
                instructions=_("""
                    # 一、强制输出规则（违反则无效）
                    1. 输出格式为标准JSON，无任何多余内容（无注释、无换行、无特殊符号、无代码块），可直接用json.loads解析。
                    2. 严格遵循以下结构，字段不可缺失、不可新增。
                    # 二、输出结构（强制要求,正确的结构）
                            {
                                "result": {
                                    "summary": "核心能量：xxxxx。/n 
                                    情感人际：xxxxx。/n
                                    xxx：xxx。/n 
                                    使用'/n'换行输出"
                                },
                            }
                    # 三、中文返回结果
                """)
            )
        if self.poster_type == "crush_check":
            message_add = _("""
            # 一、强制输出规则（违反则无效）
            1. 输出格式为标准JSON，无任何多余内容（无注释、无换行、无特殊符号、无代码块），可直接用json.loads解析。
            2. 严格遵循以下结构，字段不可缺失、不可新增，数据类型正确（分数为整数，summary为字符串）。
            3. 根据对话判断对方是男或女，不用表述出来，仅在gender数据里。
            4. 整数分数0-100分。
            # 二、输出结构（强制要求,正确的结构）
                    {
                        "result": {
                            "poster": {
                                "flags": {"关键词1": 整数分数, "关键词2": 整数分数, "关键词3": 整数分数, "关键词4": 整数分数},
                                "summary": "一句话总结（格式：TA是一个XXXX，字数20-30字）"
                                "gender":"male或female"
                                },
                                "report": {
                                    "summary": "法医结论行动建议一句话总结（格式：字数200字）不显示“法医结论字样”",
                                    "flags": {"风险关键词1": 整数分数, "风险关键词2": 整数分数, "风险关键词3": 整数分数, "风险关键词4": 整数分数},
                                    "danger":"最隐蔽风险",
                                    "advise":"行动建议",
                                    "advise_summary":"行动建议核心结论",
                                    "detail":"{"详细解读段落1":"内容","详细解读段落2":"内容","详细解读段落3":"",....}
                                }"
                            }"
                    }
            # 三、输出结构组成示例：
                        reslut:{
                            poster:{
                            "海报要求"
                            }
                            report:{
                            "报告要求"
                            }
                        }
            ### 3.1海报要求：
                必须4个关键词，每个关键字的分数根据分析出的结果应为不同数值：
                flags: {"词1":分数,"词2":分数,"词3":分数,"词4":分数}
                summary:一句话总结（如"TA是一个XXXX"，字数限制为20-40字）
            ### 3.2报告要求：
                必须4个风险评分，每个风险评分关键字有分数
                summary总结,只包含结果，不含标题
                activate行动建议：一句话不分点。
                detail内容为字典格式{"key":"value"}可以有多个
            # 四、中文语言返回结果
            """)
        print(f"======larg_models_tool====当前识别的语言：{get_language()}")
        if "输出格式为标准JSON" not in self.prompt_text:
            content.append({"type": "text", "text": message_add})
        if add_text:
            content.append({"type": "text", "text": add_text})
        if self.poster_type == 'trial_case' and self.prompt_text:
            content.append({"type": "text", "text": self.prompt_text})
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
    def get_prompt_text(self):
        """
        获取提示语
        :return:
        """
        prompt = PromptTemplate.objects.get(id=self.prompt_id).prompt_content
        return prompt