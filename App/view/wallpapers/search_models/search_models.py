TAG_MAPPING = {'Nandi': 3638, 'Hinduism': 3637, 'Ganesha': 3636, 'Durga': 3635, 'Vishnu': 3634, 'Shiva': 3633,
               'Indian Palace': 241, 'Pexels': 242, '批量': 151, '测试1': 152, '测试2': 154, '南迪': 3638, '湿婆': 3633,
               '毗湿奴': 3634, '杜尔迦': 3635, '伽内什': 3636, '印度教': 3637, '印度宫殿': 241, '佩克斯': 242,
               'Batch': 151, 'Test1': 152, 'Test2': 154, '印度皇宫': 241, '希瓦': 3633}


def generate_tag_mapping(tag_list: list) -> dict:
    """
    将标签列表转换为 TAG_MAPPING 字典（关键词→标签ID）
    :param tag_list: 标签列表（格式如你提供的[{id:xxx, name:xxx}, ...]）
    :return: 映射字典
    """
    # 基础映射（标签名称→ID）
    tag_mapping = {item["name"]: item["id"] for item in tag_list}

    # 补充同义词/别名（提升用户输入匹配度）
    synonyms = {
        # 英文标签的中文别名
        "南迪": 3638,  # Nandi
        "湿婆": 3633,  # Shiva
        "毗湿奴": 3634,  # Vishnu
        "杜尔迦": 3635,  # Durga
        "伽内什": 3636,  # Ganesha
        "印度教": 3637,  # Hinduism
        "印度宫殿": 241,  # Indian Palace
        "佩克斯": 242,  # Pexels
        # 中文标签的英文别名（可选）
        "Batch": 151,  # 批量
        "Test1": 152,  # 测试1
        "Test2": 154,  # 测试2
        # 补充模糊匹配关键词
        "印度皇宫": 241,  # 对应 Indian Palace
        "希瓦": 3633,  # 对应 Shiva（另一种译法）
    }

    # 合并基础映射和同义词映射
    tag_mapping.update(synonyms)
    return tag_mapping


# ========== 应用示例 ==========
# 你的原始标签列表数据
raw_tag_list = [
    {"id": 3638, "name": "Nandi", "created_at": "2026-03-11 08:40:14"},
    {"id": 3637, "name": "Hinduism", "created_at": "2026-03-11 08:39:56"},
    {"id": 3636, "name": "Ganesha", "created_at": "2026-03-11 08:39:34"},
    {"id": 3635, "name": "Durga", "created_at": "2026-03-11 08:18:59"},
    {"id": 3634, "name": "Vishnu", "created_at": "2026-03-11 08:18:47"},
    {"id": 3633, "name": "Shiva", "created_at": "2026-03-11 08:18:24"},
    {"id": 241, "name": "Indian Palace", "created_at": "2026-03-11 05:43:59"},
    {"id": 242, "name": "Pexels", "created_at": "2026-03-11 05:43:59"},
    {"id": 151, "name": "批量", "created_at": "2026-03-10 09:20:54"},
    {"id": 152, "name": "测试1", "created_at": "2026-03-10 09:20:54"},
    {"id": 154, "name": "测试2", "created_at": "2026-03-10 09:20:54"},
]
raw_tag_list = [
    {
        "id": 3638,
        "name": "Nandi",
        "created_at": "2026-03-11 08:40:14"
    },
    {
        "id": 3637,
        "name": "Hinduism",
        "created_at": "2026-03-11 08:39:56"
    },
    {
        "id": 3636,
        "name": "Ganesha",
        "created_at": "2026-03-11 08:39:34"
    },
    {
        "id": 3635,
        "name": "Durga",
        "created_at": "2026-03-11 08:18:59"
    },
    {
        "id": 3634,
        "name": "Vishnu",
        "created_at": "2026-03-11 08:18:47"
    },
    {
        "id": 3633,
        "name": "Shiva",
        "created_at": "2026-03-11 08:18:24"
    },
    {
        "id": 241,
        "name": "Indian Palace",
        "created_at": "2026-03-11 05:43:59"
    },
    {
        "id": 242,
        "name": "Pexels",
        "created_at": "2026-03-11 05:43:59"
    },
    {
        "id": 151,
        "name": "批量",
        "created_at": "2026-03-10 09:20:54"
    },
    {
        "id": 152,
        "name": "测试1",
        "created_at": "2026-03-10 09:20:54"
    },
    {
        "id": 154,
        "name": "测试2",
        "created_at": "2026-03-10 09:20:54"
    }
]
# 生成最终的 TAG_MAPPING
TAG_MAPPING = generate_tag_mapping(raw_tag_list)

print(TAG_MAPPING)
