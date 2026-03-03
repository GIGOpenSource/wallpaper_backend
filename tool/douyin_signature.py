import hashlib


def is_arr_map(map_data: dict) -> bool:
    """
    判断是否为关联数组（PHP中的isArrMap逻辑）
    :param map_data: 待判断的字典/列表
    :return: True=关联数组（字符串键），False=索引数组（数字键）
    """
    if not isinstance(map_data, dict):
        return False
    # 只要存在一个字符串类型的键，就视为关联数组
    for key in map_data.keys():
        if isinstance(key, str):
            return True
    return False


def array_to_str(map_data) -> str:
    """
    数组转字符串（复刻PHP的arrayToStr逻辑）
    :param map_data: 待转换的字典/列表
    :return: 转换后的字符串
    """
    is_map = is_arr_map(map_data)
    result = "map[" if is_map else ""

    # 获取键列表并排序（关联数组按键排序，索引数组按原有顺序）
    key_arr = list(map_data.keys()) if isinstance(map_data, dict) else list(range(len(map_data)))
    if is_map:
        key_arr.sort()  # 关联数组按键排序

    params_arr = []
    for key in key_arr:
        value = map_data[key] if isinstance(map_data, dict) else map_data[key]

        if isinstance(value, (dict, list)):
            # 递归处理嵌套数组
            str_val = array_to_str(value)
        else:
            # 非数组值转字符串并去除首尾空格
            str_val = str(value).strip()

        if is_map:
            # 关联数组格式：key:value
            params_arr.append(f"{key}:{str_val}")
        else:
            # 索引数组直接拼接值
            params_arr.append(str_val)

    # 拼接参数数组（关联数组用空格分隔，索引数组用空格分隔）
    result += " ".join(params_arr)

    # 补充首尾符号
    if not is_map:
        result = f"[{result}]"
    else:
        result = f"{result}]"

    return result


def sign(map_data: dict, payment_salt: str = "your_payment_salt") -> str:
    """
    复刻PHP的sign函数逻辑
    :param map_data: 待签名的参数字典
    :param payment_salt: 签名盐值（默认值与PHP一致）
    :return: MD5签名结果
    """
    r_list = []

    # 遍历参数，过滤指定键和无效值
    for k, v in map_data.items():
        # 跳过指定键
        if k in ["other_settle_params", "app_id", "sign", "thirdparty_id"]:
            continue

        # 处理值：转字符串并去除首尾空格
        if isinstance(v, (dict, list)):
            # 数组类型转字符串
            value = array_to_str(v)
        else:
            value = str(v).strip()

        # 去除首尾引号（如果字符串首尾都是双引号）
        len_val = len(value)
        if len_val > 1 and value[0] == "\"" and value[-1] == "\"":
            value = value[1:-1].strip()

        # 跳过空值或"null"
        if value == "" or value == "null":
            continue

        r_list.append(value)

    # 加入盐值并排序
    r_list.append(payment_salt)
    r_list.sort()  # 按字符串排序（对应PHP的SORT_STRING）

    # 拼接字符串并MD5加密
    sign_str = "&".join(r_list)
    md5_sign = hashlib.md5(sign_str.encode("utf-8")).hexdigest()

    return md5_sign

# test_params = {
#     "app_id": "test_appid",  # 会被跳过
#     "merchant_id": "123456",
#     "out_trade_no": "ORDER20240520",
#     "total_amount": 100,
#     "description": "\"测试商品\"",  # 会去除首尾引号
#     "null_param": "null",  # 会被跳过
#     "empty_param": "",  # 会被跳过
#     "nested_map": {"a": 1, "b": [2, 3]},  # 嵌套关联数组
#     "nested_list": [4, {"c": 5}],  # 嵌套索引数组
#     "other_settle_params": "xxx"  # 会被跳过
# }
#
# # 生成签名（盐值使用默认值"your_payment_salt"，可自定义传入）
# signature = sign(test_params)
# print("签名结果:", signature)