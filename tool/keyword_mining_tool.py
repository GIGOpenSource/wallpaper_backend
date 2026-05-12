#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：WallPaper
@File    ：keyword_mining_tool.py
@Author  ：Liang
@Date    ：2026/5/12
@description : 关键词挖掘大模型工具
"""
import json
from typing import List, Dict, Any
from openai import OpenAI
from tool.tools import getEnvConfig, logger


class KeywordMiningTool:
    """
    关键词挖掘工具类
    支持热门关键词挖掘和长尾词扩展
    """

    def __init__(self, model_provider: str = "deepseek"):
        """
        初始化大模型客户端
        :param model_provider: 模型提供商，目前支持 deepseek
        """
        self.model_provider = model_provider
        
        if model_provider == "deepseek":
            self.model = getEnvConfig("DS_MODEL") or "deepseek-chat"
            self.api_key = getEnvConfig("DS_API_KEY")
            self.base_url = "https://api.deepseek.com"
        elif model_provider == "qwen":
            self.model = getEnvConfig("QW_MODEL") or "qwen-turbo"
            self.api_key = getEnvConfig("QW_API_KEY")
            self.base_url = getEnvConfig("QW_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        else:
            raise ValueError(f"不支持的模型提供商: {model_provider}")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        通用大模型调用方法
        :param system_prompt: 系统提示词
        :param user_prompt: 用户提示词
        :return: 模型返回的原始字符串
        """
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                stream=False
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"大模型调用失败: {str(e)}")
            raise Exception(f"关键词挖掘服务异常: {str(e)}")

    def _parse_json_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        解析大模型返回的 JSON 字符串
        :param response_text: 模型返回的文本
        :return: 解析后的列表数据
        """
        try:
            # 尝试直接解析
            data = json.loads(response_text)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "keywords" in data:
                return data["keywords"]
            else:
                return []
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试提取代码块中的 JSON
            try:
                start_idx = response_text.find("```json")
                if start_idx != -1:
                    end_idx = response_text.find("```", start_idx + 7)
                    json_str = response_text[start_idx + 7:end_idx].strip()
                    return json.loads(json_str)
                
                # 尝试查找第一个 [ 和最后一个 ]
                start_idx = response_text.find("[")
                end_idx = response_text.rfind("]")
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx:end_idx + 1]
                    return json.loads(json_str)
            except Exception as e:
                logger.error(f"JSON 解析失败: {str(e)}, 原始内容: {response_text[:200]}")
            
            return []

    def mine_hot_keywords(self, seed_keyword: str, category: str = "style", count: int = 15) -> List[Dict[str, Any]]:
        """
        挖掘热门关键词
        :param seed_keyword: 种子关键词
        :param category: 分类（style/theme/device/type）
        :param count: 返回数量（10-20）
        :return: 关键词列表
        """
        system_prompt = """你是一个专业的 SEO 关键词分析专家。请根据用户提供的种子关键词，挖掘相关的热门关键词。
你必须严格返回标准的 JSON 格式数组，不要包含任何额外的解释或 Markdown 标记。
返回的每个对象必须包含以下字段：
- keyword: 关键词字符串
- category: 分类（style/theme/device/type）
- monthly_search_volume: 月搜索量（整数）
- optimization_difficulty: 优化难度（0-100 的整数）
- cpc: CPC 点击成本（浮点数，保留两位小数）
- trend: 趋势（rising/falling/stable）
- competition: 竞争度（0-1 的浮点数，保留两位小数）
"""
        
        user_prompt = f"""请基于种子关键词 "{seed_keyword}"，挖掘 {count} 个相关的热门壁纸类关键词。
分类指定为：{category}。
请直接返回 JSON 数组格式。"""

        response_text = self._call_llm(system_prompt, user_prompt)
        return self._parse_json_response(response_text)

    def expand_long_tail_keywords(self, parent_keyword: str, 
                                  pos: str = "noun", 
                                  modifiers: str = "", 
                                  count: int = 15) -> List[Dict[str, Any]]:
        """
        扩展长尾关键词
        :param parent_keyword: 父关键词（核心词）
        :param pos: 词性（noun/adjective/verb）
        :param modifiers: 修饰词，逗号分隔（如：4k,高清,免费）
        :param count: 返回数量（10-20）
        :return: 长尾关键词列表
        """
        # 构建修饰词描述
        modifier_desc = f"必须包含以下修饰词中的一个或多个：{modifiers}" if modifiers else "可以适当加入流行修饰词"
        
        # 构建词性描述
        pos_map = {"noun": "名词", "adjective": "形容词", "verb": "动词"}
        pos_desc = pos_map.get(pos, "名词")
        
        system_prompt = f"""你是一个专业的多语言 SEO 长尾关键词挖掘专家。
请根据用户提供的核心词、词性和修饰词要求，扩展出相关的长尾关键词。
**重要规则：**
1. **语言匹配**：如果核心词是英文，返回的长尾词必须是英文；如果核心词是中文，返回的长尾词必须是中文。
2. **格式要求**：你必须严格返回标准的 JSON 格式数组，不要包含任何额外的解释或 Markdown 标记。
3. **字段定义**：
   - long_tail_keyword: 长尾关键词字符串
   - parent_keyword: 父关键词字符串
   - monthly_search_volume: 月搜索量（整数）
   - optimization_difficulty: 优化难度（0-100 的整数）
   - recommendation_score: 推荐度（0-100 的整数，越高越推荐）
   - cpc: CPC 点击成本（浮点数，保留两位小数）
"""
        
        user_prompt = f"""请基于以下要求扩展 {count} 个长尾关键词：
- 核心词（父关键词）：{parent_keyword}
- 词性要求：{pos_desc}
- 修饰词要求：{modifier_desc}
- 数量：{count} 个

请直接返回 JSON 数组格式。"""

        response_text = self._call_llm(system_prompt, user_prompt)
        return self._parse_json_response(response_text)
