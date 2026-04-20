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

    # Token 前缀常量
    TOKEN_PREFIX_USER = "Login:Token"
    TOKEN_PREFIX_CUSTOMER = "Login:CToken"
    TOKEN_MAP_PREFIX_USER = "Login:user_token_map"
    TOKEN_MAP_PREFIX_CUSTOMER = "Login:customer_token_map"

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
    def _build_token(cls, prefix: str, token_core: str) -> str:
        """
        构建 Token 字符串
        :param prefix: Token 前缀 (如 "Login:PC:CToken")
        :param token_core: 加密后的核心数据
        :return: 完整 Token 字符串
        """
        return f"{prefix}{token_core}"

    @classmethod
    def _get_token_map_key(cls, prefix: str, user_id: int, is_customer: bool = False) -> str:
        """
        获取 Token 映射键
        :param prefix: 平台前缀 (如 "PC", "Phone")
        :param user_id: 用户 ID
        :param is_customer: 是否是客户用户
        :return: Redis 键名
        """
        map_prefix = cls.TOKEN_MAP_PREFIX_CUSTOMER if is_customer else cls.TOKEN_MAP_PREFIX_USER
        return f"{map_prefix}:{prefix}:{user_id}"

    @classmethod
    def generate_token(cls, user_id: int, expire_days: int = 7, reuse_existing: bool = True,
                      platform: str = "") -> str:
        """
        生成后台用户 Token
        :param user_id: 用户 ID
        :param expire_days: 过期天数
        :param reuse_existing: 是否复用现有 token
        :param platform: 平台标识 (如 "PC", "Phone", 留空则不区分)
        :return: Token 字符串
        """
        # 构建前缀
        token_prefix = f"{cls.TOKEN_PREFIX_USER}:{platform}" if platform else cls.TOKEN_PREFIX_USER

        # 如果允许复用，先检查是否有现有 token
        if reuse_existing:
            map_key = cls._get_token_map_key(platform, user_id, is_customer=False)
            existing_token = _redis.getKey(map_key)

            if existing_token:
                # 验证 token 是否仍然有效
                token_exists = _redis.getKey(existing_token)
                if token_exists:
                    # Token 有效，延长过期时间
                    expire_seconds = expire_days * 24 * 3600
                    _redis.expireKey(existing_token, expire_seconds)
                    _redis.expireKey(map_key, expire_seconds)
                    return existing_token

        # 生成新 token
        expire_timestamp = int(time.time()) + int(timedelta(hours=TOKEN_EXPIRE_HOURS).total_seconds())
        token_core_data = f"{user_id}:{expire_timestamp}".encode("utf-8")
        encrypted_core, iv = cls._aes_encrypt(token_core_data)
        token_bytes = iv + encrypted_core
        token_base64 = base64.b64encode(token_bytes).decode("utf-8")
        token = cls._build_token(token_prefix, token_base64)

        expire_seconds = expire_days * 24 * 3600
        _redis.setKey(token, user_id, expire_seconds)

        # 存储映射关系
        map_key = cls._get_token_map_key(platform, user_id, is_customer=False)
        _redis.setKey(map_key, token, expire_seconds)

        return token

    @classmethod
    def generate_customer_token(cls, customer_id: int, reuse_existing: bool = True,
                               platform: str = "") -> str:
        """
        生成客户 Token
        :param customer_id: 客户 ID
        :param reuse_existing: 是否复用现有 token
        :param platform: 平台标识 (如 "PC", "Phone", 留空则不区分)
        :return: Token 字符串
        """
        # 构建前缀
        token_prefix = f"{cls.TOKEN_PREFIX_CUSTOMER}:{platform}" if platform else cls.TOKEN_PREFIX_CUSTOMER

        # 如果允许复用，先检查是否有现有 token
        if reuse_existing:
            map_key = cls._get_token_map_key(platform, customer_id, is_customer=True)
            existing_token = _redis.getKey(map_key)

            if existing_token:
                # 验证 token 是否仍然有效
                token_exists = _redis.getKey(existing_token)
                if token_exists:
                    # Token 有效，延长过期时间
                    expire_seconds = 7 * 24 * 3600
                    _redis.expireKey(existing_token, expire_seconds)
                    _redis.expireKey(map_key, expire_seconds)
                    return existing_token

        # 生成新 token
        expire_timestamp = int(time.time()) + int(timedelta(hours=TOKEN_EXPIRE_HOURS).total_seconds())
        token_core_data = f"c:{customer_id}:{expire_timestamp}".encode("utf-8")
        encrypted_core, iv = cls._aes_encrypt(token_core_data)
        token_bytes = iv + encrypted_core
        token_base64 = base64.b64encode(token_bytes).decode("utf-8")
        token = cls._build_token(token_prefix, token_base64)

        expire_seconds = 7 * 24 * 3600
        _redis.setKey(token, str(customer_id), expire_seconds)

        # 存储映射关系
        map_key = cls._get_token_map_key(platform, customer_id, is_customer=True)
        _redis.setKey(map_key, token, expire_seconds)

        return token

    @classmethod
    def verify_token(cls, token: str) -> tuple[bool, int or str]:
        """
        校验 Token
        :param token: Token 字符串
        :return: (是否有效, 用户 ID)
        """
        try:
            if not token:
                return False, None
            token_key = _redis.getKey(token)
            if token_key:
                return True, token_key
            return False, None
        except Exception as e:
            print(f"Token 校验失败：{str(e)}")
            return False, None

    @classmethod
    def verify_customer_token(cls, token: str) -> tuple[bool, int | None]:
        """
        验证客户 Token
        :param token: Token 字符串
        :return: (is_valid, customer_id)
        """
        try:
            if not token:
                return False, None
            # 兼容各种前缀格式
            if not any(token.startswith(prefix) for prefix in [
                cls.TOKEN_PREFIX_CUSTOMER,
                "Login:PC:CToken",
                "Login:Phone:CToken",
                "CToken"
            ]):
                return False, None
            token_key = _redis.getKey(token)
            if token_key:
                return True, int(token_key)
            return False, None
        except Exception as e:
            print(f"Customer Token 校验失败：{str(e)}")
            return False, None

    @classmethod
    def delete_token(cls, token: str):
        """
        删除 Token（登出时使用）
        :param token: Token 字符串
        """
        if token:
            user_id = _redis.getKey(token)
            _redis.delKey(token)
            if user_id:
                # 尝试删除所有可能的映射键
                for platform in ["", "PC", "Phone"]:
                    map_key = cls._get_token_map_key(platform, user_id, is_customer=False)
                    _redis.delKey(map_key)

    @classmethod
    def delete_customer_token(cls, token: str):
        """
        删除客户 Token（登出时使用）
        :param token: Token 字符串
        """
        if token:
            customer_id = _redis.getKey(token)
            _redis.delKey(token)
            if customer_id:
                # 尝试删除所有可能的映射键
                for platform in ["", "PC", "Phone"]:
                    map_key = cls._get_token_map_key(platform, customer_id, is_customer=True)
                    _redis.delKey(map_key)

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
