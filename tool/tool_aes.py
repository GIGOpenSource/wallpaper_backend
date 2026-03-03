from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
import hashlib


class AESCipherTool:
    """
    AES加密解密工具类
    与前端CryptoJS保持完全一致的加密解密逻辑
    """

    # ===================== 核心配置（和前端完全对齐） =====================
    # 前端原始密钥字符串
    RAW_KEY_STR = 'zhiliao'
    # 前端固定IV字符串
    IV_STR = '1234567890123456'
    # AES模式和填充
    AES_MODE = AES.MODE_CBC
    PADDING_STYLE = 'pkcs7'
    AES_BLOCK_SIZE = 16  # AES-CBC块大小固定16字节

    @classmethod
    def generate_aes_key(cls):
        """
        生成和前端一致的AES密钥：
        前端逻辑：CryptoJS.MD5('zhiliao').toString() → 截取前16位 → CryptoJS.enc.Utf8.parse(key)
        """
        # 1. 对zhiliao做MD5哈希（32位十六进制字符串，和CryptoJS.MD5结果一致）
        md5_hex = hashlib.md5(cls.RAW_KEY_STR.encode('utf-8')).hexdigest()
        print(f"前端CryptoJS.MD5('{cls.RAW_KEY_STR}')结果：{md5_hex}")
        # 2. 截取前16位字符串（前端：keyHashHex.substring(0, 16)）
        key_16_str = md5_hex[:16]
        print(f"前端截取的16位密钥字符串：{key_16_str}")
        # 3. UTF8编码（前端：CryptoJS.enc.Utf8.parse(key)）
        key = key_16_str.encode('utf-8')
        print(f"最终AES密钥（UTF8编码后）：{key} | 长度：{len(key)}字节")  # 16字节，符合AES-128要求
        return key

    @classmethod
    def encrypt(cls, data):
        """
        前端aesEncrypt的Python实现（用于验证）
        :param data: 要加密的字符串（对应前端data参数）
        :return: 加密后的base64字符串（和前端encrypted.toString()结果格式一致）
        """
        # 生成密钥和IV
        key = cls.generate_aes_key()
        iv = cls.IV_STR.encode('utf-8')  # 前端：CryptoJS.enc.Utf8.parse('1234567890123456')
        # 1. 明文转UTF8字节（前端：CryptoJS.enc.Utf8.parse(data)）
        data_bytes = data.encode('utf-8')
        # 2. PKCS7填充（前端：CryptoJS.pad.Pkcs7）
        padded_data = pad(data_bytes, cls.AES_BLOCK_SIZE, style=cls.PADDING_STYLE)
        # 3. CBC模式加密
        cipher = AES.new(key, cls.AES_MODE, iv)
        encrypted_bytes = cipher.encrypt(padded_data)
        # 4. 模拟CryptoJS的Salted__头（前端encrypted.toString()默认带该头）
        # 注：CryptoJS会自动添加Salted__+随机Salt，这里用固定Salt方便测试（前端是随机的，解密时只需去掉前16字节）
        salt = b'\x00' * 8  # 随机Salt，前端是随机生成的，解密时不依赖
        encrypted_with_salt = b'Salted__' + salt + encrypted_bytes
        # 5. Base64编码（前端：encrypted.toString()）
        return base64.b64encode(encrypted_with_salt).decode('utf-8')

    @classmethod
    def decrypt(cls, encrypted_str):
        """
        前端aesDecrypt的Python实现（核心解密函数）
        :param encrypted_str: 前端aesEncrypt返回的base64字符串
        :return: 解密后的原始字符串
        """
        # 生成和前端一致的密钥
        key = cls.generate_aes_key()
        iv = cls.IV_STR.encode('utf-8')
        try:
            # 1. Base64解码（前端解密第一步自动处理）
            encrypted_with_salt = base64.b64decode(encrypted_str)
            # 2. 去掉CryptoJS自动添加的Salted__头（8字节）+ Salt（8字节），共16字节
            # 前端解密时会自动处理这部分，Python需手动去掉
            if encrypted_with_salt.startswith(b'Salted__'):
                encrypted_bytes = encrypted_with_salt[16:]
            else:
                encrypted_bytes = encrypted_with_salt
            # 3. CBC模式解密
            cipher = AES.new(key, cls.AES_MODE, iv)
            decrypted_padded = cipher.decrypt(encrypted_bytes)
            # 4. 移除PKCS7填充（前端：CryptoJS.pad.Pkcs7）
            decrypted_bytes = unpad(decrypted_padded, cls.AES_BLOCK_SIZE, style=cls.PADDING_STYLE)
            # 5. UTF8解码（前端：decrypted.toString(CryptoJS.enc.Utf8)）
            result = decrypted_bytes.decode('utf-8')
            if not result:
                print("解密结果为空，请检查密钥/IV是否和前端一致")
            return result
        except Exception as e:
            raise Exception(f"AES解密失败：{str(e)}\n请核对：1.密钥生成逻辑 2.IV 3.密文是否完整")

aes = AESCipherTool()
# encrypted_str = "seo94giAT4flcI4PP1yqSFXB4NSXryLXJ6APud4RvEpdYRT01y1BXAQdqo9xW/kmjBQQcC7RNfCR7i63RTvX+g=="
# a = AESCipherTool.decrypt(encrypted_str)
# print(a)
# # ===================== 测试验证（和前端交叉验证） =====================
# if __name__ == "__main__":
#     # 测试数据（和前端testData一致）
#     test_data = '123456'
#     print("===== 加密测试 =====")
#     # 加密（模拟前端aesEncrypt）
#     encrypted_str = AESCipherTool.encrypt(test_data)
#     print(f"前端风格加密结果：{encrypted_str}")
#     # encrypted_str = "decrypted_inviter"
#     print("\n===== 解密测试 =====")
#     # 解密（模拟前端aesDecrypt）
#     try:
#         decrypted_str = AESCipherTool.decrypt(encrypted_str)
#         print(f"✅ 解密成功！原始数据：{decrypted_str}")
#     except Exception as e:
#         print(f"❌ {e}")