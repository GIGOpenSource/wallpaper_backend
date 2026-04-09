#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：NoBad
@File    ：tool_tools.py
@Author  ：LYP
@Date    ：2025/10/31 15:37
@description :
"""
import hashlib
import json

import redis
import base64
import time
from datetime import timedelta
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from tool.tools import getEnvConfig, logger

# -------------------------- 配置项（需根据项目自定义，建议存环境变量）--------------------------
# AES 密钥：必须 16/24/32 字节（对应 AES-128/AES-192/AES-256），这里用 32 字节示例
AES_SECRET_KEY = b"zhiliao-12345678"  # 实际项目需替换为随机密钥
# Token 过期时长（示例：2 小时）
TOKEN_EXPIRE_HOURS = 2
# AES 初始化向量（IV）长度：固定 16 字节（AES 标准）
AES_IV_LENGTH = 16


class RedisTool(object):
    """
    redis 工具类
    """

    def __init__(self):
        self.host = getEnvConfig("REDIS_HOST", "localhost")
        self.port = int(getEnvConfig("REDIS_PORT", 6379))
        self.password = getEnvConfig("REDIS_PASSWORD", "")
        self.db = int(getEnvConfig("REDIS_DB", 0))
        self.ex = 604800
        max_connections = getEnvConfig("REDIS_MAX_CONNECTIONS", 10)
        try:
            max_connections = int(max_connections)
            if max_connections <= 0:
                raise ValueError("max_connections 必须是正整数")
        except (ValueError, TypeError):
            raise ValueError("max_connections 必须是正整数")
        self.pool = redis.ConnectionPool(host=self.host, port=self.port, password=self.password, db=self.db,
                                         max_connections=max_connections)
        try:
            self.client = redis.Redis(connection_pool=self.pool, decode_responses=True)
            # 验证连接（触发认证，密码错误会立即报错）
            self.client.ping()
            print(f"Redis连接成功！地址：{self.host}:{self.port}")
        except redis.AuthenticationError:
            raise ValueError(f"Redis密码错误！配置的密码：{self.password}")
        except redis.ConnectionError:
            raise ConnectionError(f"Redis连接失败！地址：{self.host}:{self.port}，请检查IP/端口/防火墙")
        except Exception as e:
            raise Exception(f"Redis初始化失败：{e}")

    def setKey(self, key, values, ex=None):
        """
        :param key:
        :param values:
        :param ex:
        :return:
        """
        if ex is None:
            ex = self.ex
        self.client.set(key, values, ex=ex)
        return True

    def getKey(self, key):
        """
        :param key:
        :return:
        """
        result = self.client.get(key)
        if result:
            return result.decode()
        return None

    def delKey(self, key):
        """

        :param key:
        :return:
        """
        self.client.delete(key)
        return True

    def expireKey(self, key, ex):
        """移除默认值，必须传 ex，避免误用"""
        self.client.expire(key, ex)
        return True

    def setIncrKey(self, key, ex=None):
        """
        新增：自增计数 + 首次设置过期时间（核心方法）
        :param key: Redis键名
        :param ex: 过期时间（秒），不传则用默认7天
        :return: 自增后的当前计数
        """
        if not isinstance(ex, int) or ex <= 0:
            raise ValueError("setIncrKey 的 ex 必须是正整数（秒）")
        # 1. 自增计数（key不存在则创建，初始值1，自增后返回当前值）
        current_count = self.client.incr(key)
        # 2. 仅当首次创建（current_count == 1）时，设置过期时间
        if current_count == 1 and ex is not None:
            self.expireKey(key, ex)  # 用修复后的 expireKey 方法
        return current_count

_redis = RedisTool()


class CustomTokenTool:

    @staticmethod
    def _aes_encrypt(data: bytes) -> tuple[bytes, bytes]:
        """AES 加密：返回（加密后数据 + 初始化向量 IV）"""
        iv = get_random_bytes(AES_IV_LENGTH)  # 每次加密生成随机 IV（增强安全性）
        cipher = AES.new(AES_SECRET_KEY, AES.MODE_CBC, iv)  # CBC 模式（需 IV 确保同明文不同密文）
        encrypted_data = cipher.encrypt(pad(data, AES.block_size))  # 填充数据至块大小（AES 要求）
        return encrypted_data, iv

    @staticmethod
    def _aes_decrypt(encrypted_data: bytes, iv: bytes) -> bytes:
        """AES 解密：传入加密数据 + IV，返回明文"""
        cipher = AES.new(AES_SECRET_KEY, AES.MODE_CBC, iv)
        decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)  # 去除填充
        return decrypted_data

    @classmethod
    def generate_token(cls, user_id: int,expire_days: int = 7) -> str:
        """
        生成 Token：基于用户 ID + 过期时间戳，AES 加密后 Base64 编码
        :param user_id: 自定义 User 模型的主键 ID（关联用户）
        :param expire_days: 过期天数（默认7天，支持动态调整）
        :return: 最终可传输的 Token 字符串
        """
        # 1. 构建 Token 核心数据（用户 ID + 过期时间戳）
        # expire_seconds = int(timedelta(days=expire_days).total_seconds())
        # expire_timestamp = int(time.time()) + expire_seconds
        expire_timestamp = int(time.time()) + int(timedelta(hours=TOKEN_EXPIRE_HOURS).total_seconds())
        token_core = f"{user_id}:{expire_timestamp}".encode("utf-8")  # 格式："用户ID:过期时间戳"
        # 2. AES 加密核心数据
        encrypted_core, iv = cls._aes_encrypt(token_core)
        # 3. 拼接「IV + 加密后数据」，再 Base64 编码（便于 HTTP 传输，避免特殊字符）
        token_bytes = iv + encrypted_core  # IV 需随 Token 一起传输，解密时需用
        token = "Token" + base64.b64encode(token_bytes).decode("utf-8")
        expire_seconds = 7 *24 * 3600
        _redis.setKey(token, user_id,expire_seconds)
        return token

    @classmethod
    def verify_token(cls, token: str) -> tuple[bool, int or str]:
        """
        校验 Token：解密 + 检查过期 + 提取用户 ID
        :param token: 客户端传入的 Token 字符串
        :return: (是否有效, 有效则返回用户 ID，无效则返回 None)
        """
        try:
            if not token:
                return False, None
            token_key = _redis.getKey(token)
            if token_key:
                return True, token_key
            else:
                return False, None
        except Exception as e:
            # 捕获所有异常（Base64 解码失败、AES 解密失败、格式错误等），均视为 Token 无效
            print(f"Token 校验失败：{str(e)}")
            return False, None

    @classmethod
    def delete_token(cls, token):
        """
        删除 Token（登出时使用）
        :param token: 要删除的 Token 字符串
        """
        if token:
            _redis.delKey(token)

    @classmethod
    def generate_customer_token(cls, customer_id: int) -> str:
        """C 端客户 Token（Redis 中的 key 与后台 Token 不同，避免混淆）。"""
        expire_timestamp = int(time.time()) + int(timedelta(hours=TOKEN_EXPIRE_HOURS).total_seconds())
        token_core = f"c:{customer_id}:{expire_timestamp}".encode("utf-8")
        encrypted_core, iv = cls._aes_encrypt(token_core)
        token_bytes = iv + encrypted_core
        token = "CToken" + base64.b64encode(token_bytes).decode("utf-8")
        expire_seconds = 7 * 24 * 3600
        _redis.setKey(token, str(customer_id), expire_seconds)
        return token

    @classmethod
    def verify_customer_token(cls, token: str) -> tuple[bool, int | None]:
        try:
            if not token or not token.startswith("CToken"):
                return False, None
            token_key = _redis.getKey(token)
            if token_key:
                return True, int(token_key)
            return False, None
        except Exception as e:
            print(f"Customer Token 校验失败：{str(e)}")
            return False, None

    @classmethod
    def delete_customer_token(cls, token):
        if token:
            _redis.delKey(token)

"""
是否生成token，如果token已有且有效则不生成 
"""
def generate_is_user_token(request, user):
    if request:
        existing_token = 0
        if existing_token:
            is_valid, user_id = CustomTokenTool.verify_token(existing_token)
            if is_valid and user_id == user.id:
                return existing_token
    # 生成新的 token
    token = CustomTokenTool.generate_token(user.id)
    if request:
        logger.info(f"生成的 Token：{token}")
    return token


class MBTIredis(object):
    """
    MBTI房间专属Redis业务类
    专注处理房间unique_key的生成、状态检查、信息查询、标记已使用等业务
    依赖通用RedisTool实例，解耦基础操作和业务逻辑
    """
    def __init__(self, redis_tool,key_prefix: str = "mbti_house"):
        self.redis = redis_tool  # 注入通用Redis工具实例，依赖解耦
        self.room_ex = 172800    # 房间key固定过期时间：2天（秒）
        self.room_key_pattern = f"{key_prefix}:{{host_id}}@{{unique_key}}"# 房间key格式模板
        self.enforce = False

    def generate_room_key_with_check(self, host_id, host_status, invitee_id, invitee_status,test_type=None,enforce=None):
        """
        【主方法】生成房间unique_key，生成前检查房主是否有未使用的key
        有则返回Unused状态，无则生成新key并存储
        :param host_id: 房主ID
        :param host_status: 房主答题状态
        :param invitee_id: 邀请者ID
        :param invitee_status: 邀请者答题状态
        :return: 元组 (status, unique_key)
                 status：success/exists_unused/fail
                 unique_key：成功返回key，否则返回None
        """
        enforce = self.enforce if enforce is None else enforce
        # 第一步：检查房主是否有未过期、未使用的房间key
        try:
            room_info = self._check_host_has_unused_key(host_id, enforce)
            if room_info[0]:
                key = room_info[0]
                if '@'in key.decode('utf-8'):
                    key = key.decode('utf-8').split('@')[1]
                status = room_info[1]
                if status:
                    status = "Used"
                else:
                    status = "Unused"
                return status, key
        except Exception as e:
            print(f"检查房主[{host_id}]未使用房间key失败：{str(e)}")
            return "fail", None
        try:
            unique_key = self._generate_md5_key()
            # 拼接完整Redis键名
            redis_key = self.room_key_pattern.format(host_id=host_id, unique_key=unique_key)
            # 构造房间数据，新增is_used状态（初始未使用）
            room_data = {
                "host_id": host_id,
                "host_status": host_status,
                "invitee_id": invitee_id,
                "invitee_status": invitee_status,
                "test_type":test_type,
                "is_used": False,
                "room_pay_status":"non_payable",
            }
            # JSON序列化存储（替代str(dict)，解决eval安全风险）
            self.redis.setKey(redis_key, json.dumps(room_data, ensure_ascii=False), ex=self.room_ex)
            return "success", unique_key
        except Exception as e:
            print(f"生成房主[{host_id}]房间key失败：{str(e)}")
            return "fail", None

    def generate_room_key(self, host_id, host_status, invitee_id, invitee_status):
        """
        【兼容原方法】无检查直接生成房间unique_key（对应原generate_unique_key_and_store1）
        :param 入参同上方方法
        :return: 生成的unique_key
        """
        unique_key = self._generate_md5_key()
        redis_key = self.room_key_pattern.format(host_id=host_id, unique_key=unique_key)
        room_data = {
            "host_id": host_id,
            "host_status": host_status,
            "invitee_id": invitee_id,
            "invitee_status": invitee_status
        }
        self.redis.setKey(redis_key, json.dumps(room_data, ensure_ascii=False), ex=self.room_ex)
        return unique_key

    def get_room_info_by_key(self, host_id, unique_key):
        """
        根据房主ID+unique_key查询房间详细信息（修复原方法仅传unique_key的bug）
        :param host_id: 房主ID
        :param unique_key: 房间唯一key
        :return: 房间信息字典，key不存在/解析失败返回None
        """
        redis_key = self.room_key_pattern.format(host_id=host_id, unique_key=unique_key)
        data_str = self.redis.getKey(redis_key)
        if not data_str:
            return None
        try:
            # JSON解析（替代eval，安全无风险）
            return json.loads(data_str)
        except Exception as e:
            print(f"解析房间[{redis_key}]信息失败：{str(e)}")
            return None

    def update_room_info_by_key(self, host_id, unique_key, **update_data):
        """
        通用方法：根据房主ID+房间key修改房间任意信息
        支持灵活修改单个/多个字段，保留原有未修改字段，原子性更新
        :param host_id: 房主ID
        :param unique_key: 房间唯一key
        :param update_data: 可变参数字典，传入要修改的字段和值（如host_status="done", is_used=False）
        :return: tuple (status: str, old_info: dict)
                 status：success-修改成功，not_exist-房间不存在，fail-修改失败
                 old_info：修改前的房间信息（失败/不存在则返回None）
        """
        if not update_data:
            print("修改失败：未传入任何要更新的字段")
            return "fail", None
        redis_key = self.room_key_pattern.format(host_id=host_id, unique_key=unique_key)
        data_str = self.redis.getKey(redis_key)
        # 房间key不存在/已过期
        if not data_str:
            print(f"修改失败：房间key[{redis_key}]不存在或已过期")
            return "not_exist", None
        try:
            # 加载原有信息，更新传入的字段（保留未修改字段）
            old_info = json.loads(data_str)
            old_info.update(update_data)  # 核心：字典更新，覆盖传入的字段
            # 重新序列化存储，保留原过期时间
            self.redis.setKey(redis_key, json.dumps(old_info, ensure_ascii=False), ex=self.room_ex)
            print(f"房间key[{redis_key}]修改成功，更新字段：{update_data.keys()}")
            return "success", old_info
        except Exception as e:
            print(f"修改房间key[{redis_key}]信息失败：{str(e)}")
            return "fail", None

    def mark_room_key_used(self, host_id, unique_key):
        """
        标记房间key为已使用（核心配套方法），保证检查逻辑闭环
        :param host_id: 房主ID
        :param unique_key: 房间唯一key
        :return: True-标记成功，False-标记失败（key不存在/异常）
        """
        redis_key = self.room_key_pattern.format(host_id=host_id, unique_key=unique_key)
        data_str = self.redis.getKey(redis_key)
        if not data_str:
            print(f"标记失败：房间key[{redis_key}]不存在或已过期")
            return False
        try:
            room_data = json.loads(data_str)
            room_data["is_used"] = True  # 更新使用状态
            # 重新存储，保留原过期时间
            self.redis.setKey(redis_key, json.dumps(room_data, ensure_ascii=False), ex=self.room_ex)
            print(f"房间key[{redis_key}]已成功标记为已使用")
            return True
        except Exception as e:
            print(f"标记房间key[{redis_key}]为已使用失败：{str(e)}")
            return False

    def _generate_md5_key(self):
        """
        私有方法：生成MD5唯一key（秒级时间戳，高并发可优化为毫秒+随机数）
        :return: MD5加密后的32位字符串
        """
        timestamp = str(int(time.time()))
        # 高并发优化版：timestamp = str(int(time.time()*1000)) + str(random.randint(0, 999))
        return hashlib.md5(timestamp.encode("utf-8")).hexdigest()

    def _check_host_has_unused_key(self, host_id, enforce):
        """
        私有方法：检查房主是否有未过期、未使用的房间key，存在则返回key和使用状态
        使用scan迭代查询，避免keys阻塞Redis
        :param host_id: 房主ID
        :return: 存在则返回 (room_key: str, is_used: bool)，不存在则返回 (None, None)
        """
        scan_pattern = f"mbti_house:{host_id}@*"
        cursor = 0
        while True:
            # Scan迭代查询，count=10每次取10个，可根据实际场景调整
            cursor, keys = self.redis.client.scan(cursor, match=scan_pattern, count=10)
            if keys:
                for key in keys:
                    # 先尝试获取key的value，为空则跳过（key过期/被删除）
                    data_str = self.redis.getKey(key)
                    if not data_str:
                        continue
                    # 解析json，做异常捕获避免脏数据导致程序崩溃
                    try:
                        room_data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    # 提取使用状态，默认True（无该字段则视为已使用）
                    is_used = room_data.get("is_used", True)
                    if enforce:
                        key_str = key.decode('utf-8')
                        unique_key = key_str.split("@")[-1]
                        # 如果强制使用, 则标记为已使用
                        mbti_redis.mark_room_key_used(host_id=host_id, unique_key=unique_key)
                        break
                    if is_used:
                        break
                    # 找到目标key，直接返回key和使用状态（优先返回第一个符合的）
                    return key, is_used
            # cursor=0表示迭代结束，无符合条件的key
            if cursor == 0:
                break
        # 迭代完成未找到，返回None
        return None, None

mbti_redis = MBTIredis(_redis)
trialcase_redis = MBTIredis(_redis, key_prefix="trialcase_house")