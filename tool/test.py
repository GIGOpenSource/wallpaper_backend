#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：NoBad 
@File    ：test.py
@Author  ：LYP
@Date    ：2025/11/11 15:19 
@description :
"""

import os
from volcenginesdkarkruntime import Ark

# 请确保您已将 API Key 存储在环境变量 ARK_API_KEY 中
# 初始化Ark客户端，从环境变量中读取您的API Key
key = os.environ.get("ARK_API_KEY")
print(key)
client = Ark(
    api_key="e4706286-fc37-4830-b2f4-b70f5987606f"
)

response = client.chat.completions.create(
    # 您可以前往 开通管理页 开通服务，并在 在线推理页 创建ep后进行查看
    model="doubao-seed-1-6-251015",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://ark-project.tos-cn-beijing.ivolces.com/images/view.jpeg"
                    },
                },
                {"type": "text", "text": "这是哪里？"},
            ],
        }
    ],

    # 免费开启推理会话应用层加密，访问 https://www.volcengine.com/docs/82379/1389905 了解更多
    extra_headers={'x-is-encrypted': 'true'},
    temperature=1,
    top_p=0.7,
    max_tokens=32768,
    # reasoning_effort=medium,
)

print(response.choices[0])