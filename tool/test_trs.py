import requests
import hashlib
import random

APPID = "20251120002501888"
SECRET_KEY = "sNfan88yyvUeUNtfIAkm"
# SECRET_KEY = "klktbxFQTlIxSUGPSVie7"

url = 'https://fanyi-api.baidu.com/api/trans/vip/translate'
q = "你好世界"
# 强制转字符串！！！
salt = str(random.randint(32768,65536))
sign_str = f"{APPID}{q}{salt}{SECRET_KEY}"
sign = hashlib.md5(sign_str.encode("utf-8")).hexdigest()

params={
    "q": q,
    "from": "auto",
    "to": "kor",
    "appid": APPID,
    "salt": salt,
    "sign": sign
}

resp = requests.get(url,params=params)
print("sign_str:", sign_str)
print("本地md5 sign:", sign)
print("返回结果：", resp.json())