import polib
import requests
import hashlib
import random

# 百度翻译API配置（替换为你的有效信息）
APPID = "20251120002501888"
SECRET_KEY = "sNfan88yyvUeUNtfIAkm"

# 国际化翻译用的
def baidu_translate(q, from_lang='auto', to_lang='auto'):
    print(f"开始翻译：{q}")
    print(f"目标语言：{to_lang}")
    """调用百度翻译API翻译文本，自动识别源语言"""
    url = 'https://fanyi-api.baidu.com/api/trans/vip/translate'
    salt = random.randint(32768, 65536)
    sign_str = f"{APPID}{q}{salt}{SECRET_KEY}"
    sign = hashlib.md5(sign_str.encode()).hexdigest()
    params = {
        'q': q,
        'from': from_lang,  # 自动识别源语言（关键修复）
        'to': to_lang,
        'appid': APPID,
        'salt': salt,
        'sign': sign
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        result = response.json()
        # 调试信息（可选保留）
        # print(f"原文：{q} | 语言：{from_lang}→{to_lang} | API返回：{result}")
        if 'trans_result' in result and len(result['trans_result']) > 0:
            return result['trans_result'][0]['dst']
        elif 'error_code' in result:
            print(f"翻译失败[{q}]：{result['error_code']} - {result.get('error_msg', '未知错误')}")
    except Exception as e:
        print(f"请求异常[{q}]：{str(e)}")
    return q  # 失败时返回原文


def translate_po_file(po_path, to_lang):
    print(f"开始处理：{po_path}")
    print(f"目标语言：{to_lang}")
    """批量翻译.po文件，自动识别源语言"""
    try:
        po = polib.pofile(po_path)
        translated_count = 0

        # 遍历所有未翻译的非空条目
        for entry in po:
            if not entry.msgstr and entry.msgid.strip():
                # 源语言设为auto，自动识别中英（关键修复）
                translated_text = baidu_translate(entry.msgid, from_lang='auto', to_lang=to_lang)
                if translated_text != entry.msgid:
                    entry.msgstr = translated_text
                    translated_count += 1
                    print(f"已翻译：{entry.msgid} → {translated_text}")

        po.save()
        print(f"\n翻译完成！共处理 {len(po)} 条，成功翻译 {translated_count} 条")
        print(f"结果已保存到：{po_path}")

    except Exception as e:
        print(f"处理PO文件失败：{str(e)}")


if __name__ == "__main__":
    translate_po_file(
        po_path=r"E:\project\nobad\locale\es\LC_MESSAGES\django.po",
        to_lang="spa"   # 西班牙语
    )
    translate_po_file(
        po_path=r"E:\project\nobad\locale\en\LC_MESSAGES\django.po",
        to_lang="en"  # 英语
    )
    translate_po_file(
        po_path=r"E:\project\nobad\locale\pt\LC_MESSAGES\django.po",
        to_lang="pt"  # 葡萄牙语
    )

    translate_po_file(
        po_path=r"E:\project\nobad\locale\ja\LC_MESSAGES\django.po",
        to_lang="jp"  # 日语
    )
    translate_po_file(
        po_path=r"E:\project\nobad\locale\ko\LC_MESSAGES\django.po",
        to_lang="kor"  # 韩语
    )

    translate_po_file(
        po_path=r"E:\project\nobad\locale\fr\LC_MESSAGES\django.po",
        to_lang="fra"   # 法语
    )