# -*- coding: utf-8 -*-
"""
离线填充 django.po（不调用百度/任何网络 API）

用法：
  1. 按需在下方 DICT 或 tool/po_translations.json 里补译文
  2. python tool/translate_po_local.py
  3. python manage.py compilemessages

说明：
  - 只填充 msgstr 为空的条目
  - DICT 里没有的 msgid：默认跳过（也可改 FILL_MISSING_AS_TAG = True 写成 [en]原文 方便联调）
"""
from __future__ import annotations

import json
from pathlib import Path

import polib

# ====== 你可改的配置 ======
LOCALE_ROOT = Path(r"C:\Users\l'l\wallpaper\locale")
# Django 语言目录名 -> 本脚本词典里的 key
LANG_DIRS = {
    "en": "en",
    "es": "es",
    "pt": "pt",
    "ja": "ja",
    "ko": "ko",
    "fr": "fr",
    "de": "de",
}
# 词典没有时：False=跳过；True=写成 "[en]该邮箱已被注册" 这种占位，方便先测语言切换
FILL_MISSING_AS_TAG = False
# 可选：额外 JSON 词典（同结构），会覆盖同名条目
EXTRA_JSON = Path(__file__).with_name("po_translations.json")

# msgid(中文) -> { 语言代码: 译文 }
# 先覆盖注册/登录等高频；其余你自己往里加，或写到 po_translations.json
DICT: dict[str, dict[str, str]] = {
    "两次输入的密码不一致": {
        "en": "The two passwords do not match",
        "es": "Las dos contraseñas no coinciden",
        "pt": "As duas senhas não coincidem",
        "ja": "パスワードが一致しません",
        "ko": "비밀번호가 일치하지 않습니다",
        "fr": "Les deux mots de passe ne correspondent pas",
        "de": "Die beiden Passwörter stimmen nicht überein",
    },
    "密码长度不能超过72字节": {
        "en": "Password must not exceed 72 bytes",
        "es": "La contraseña no debe superar los 72 bytes",
        "pt": "A senha não pode exceder 72 bytes",
        "ja": "パスワードは72バイト以下にしてください",
        "ko": "비밀번호는 72바이트를 초과할 수 없습니다",
        "fr": "Le mot de passe ne doit pas dépasser 72 octets",
        "de": "Das Passwort darf 72 Bytes nicht überschreiten",
    },
    "该邮箱已被注册": {
        "en": "This email is already registered",
        "es": "Este correo ya está registrado",
        "pt": "Este e-mail já está registrado",
        "ja": "このメールアドレスは既に登録されています",
        "ko": "이미 등록된 이메일입니다",
        "fr": "Cet e-mail est déjà enregistré",
        "de": "Diese E-Mail-Adresse ist bereits registriert",
    },
    "参数校验失败": {
        "en": "Validation failed",
        "es": "Error de validación",
        "pt": "Falha na validação",
        "ja": "入力内容が正しくありません",
        "ko": "유효성 검사에 실패했습니다",
        "fr": "Échec de la validation",
        "de": "Validierung fehlgeschlagen",
    },
    "注册成功": {
        "en": "Registration successful",
        "es": "Registro exitoso",
        "pt": "Registro concluído com sucesso",
        "ja": "登録に成功しました",
        "ko": "등록되었습니다",
        "fr": "Inscription réussie",
        "de": "Registrierung erfolgreich",
    },
    "邮箱未注册": {
        "en": "Email is not registered",
        "es": "El correo no está registrado",
        "pt": "E-mail não registrado",
        "ja": "このメールアドレスは登録されていません",
        "ko": "등록되지 않은 이메일입니다",
        "fr": "E-mail non enregistré",
        "de": "E-Mail ist nicht registriert",
    },
    "账号已被禁用，请联系客服": {
        "en": "Account disabled. Please contact support",
        "es": "Cuenta deshabilitada. Contacte con soporte",
        "pt": "Conta desativada. Contacte o suporte",
        "ja": "アカウントが無効です。サポートにお問い合わせください",
        "ko": "계정이 비활성화되었습니다. 고객센터에 문의하세요",
        "fr": "Compte désactivé. Contactez le support",
        "de": "Konto deaktiviert. Bitte Support kontaktieren",
    },
    "邮箱或密码错误": {
        "en": "Incorrect email or password",
        "es": "Correo o contraseña incorrectos",
        "pt": "E-mail ou senha incorretos",
        "ja": "メールアドレスまたはパスワードが正しくありません",
        "ko": "이메일 또는 비밀번호가 올바르지 않습니다",
        "fr": "E-mail ou mot de passe incorrect",
        "de": "E-Mail oder Passwort falsch",
    },
    "登录成功": {
        "en": "Login successful",
        "es": "Inicio de sesión exitoso",
        "pt": "Login bem-sucedido",
        "ja": "ログインに成功しました",
        "ko": "로그인되었습니다",
        "fr": "Connexion réussie",
        "de": "Anmeldung erfolgreich",
    },
    "未提供 Token": {
        "en": "Token not provided",
        "es": "Token no proporcionado",
        "pt": "Token não fornecido",
        "ja": "トークンが提供されていません",
        "ko": "토큰이 제공되지 않았습니다",
        "fr": "Jeton non fourni",
        "de": "Token nicht angegeben",
    },
    "登出成功": {
        "en": "Logout successful",
        "es": "Cierre de sesión exitoso",
        "pt": "Logout bem-sucedido",
        "ja": "ログアウトしました",
        "ko": "로그아웃되었습니다",
        "fr": "Déconnexion réussie",
        "de": "Abmeldung erfolgreich",
    },
    "请先登录或提供用户ID": {
        "en": "Please log in or provide a user ID",
        "es": "Inicie sesión o proporcione un ID de usuario",
        "pt": "Faça login ou informe um ID de usuário",
        "ja": "ログインするかユーザーIDを指定してください",
        "ko": "로그인하거나 사용자 ID를 제공하세요",
        "fr": "Veuillez vous connecter ou fournir un ID utilisateur",
        "de": "Bitte anmelden oder Benutzer-ID angeben",
    },
    "用户不存在": {
        "en": "User does not exist",
        "es": "El usuario no existe",
        "pt": "Usuário não existe",
        "ja": "ユーザーが存在しません",
        "ko": "사용자가 존재하지 않습니다",
        "fr": "L'utilisateur n'existe pas",
        "de": "Benutzer existiert nicht",
    },
    "获取成功": {
        "en": "Retrieved successfully",
        "es": "Obtenido con éxito",
        "pt": "Obtido com sucesso",
        "ja": "取得に成功しました",
        "ko": "조회되었습니다",
        "fr": "Récupéré avec succès",
        "de": "Erfolgreich abgerufen",
    },
    "保存成功": {
        "en": "Saved successfully",
        "es": "Guardado con éxito",
        "pt": "Salvo com sucesso",
        "ja": "保存しました",
        "ko": "저장되었습니다",
        "fr": "Enregistré avec succès",
        "de": "Erfolgreich gespeichert",
    },
    "保存成功，账号已禁用，token已失效": {
        "en": "Saved. Account disabled and token invalidated",
        "es": "Guardado. Cuenta deshabilitada y token invalidado",
        "pt": "Salvo. Conta desativada e token invalidado",
        "ja": "保存しました。アカウントは無効化され、トークンは失効しました",
        "ko": "저장되었습니다. 계정이 비활성화되고 토큰이 무효화되었습니다",
        "fr": "Enregistré. Compte désactivé et jeton invalidé",
        "de": "Gespeichert. Konto deaktiviert und Token ungültig",
    },
    "token不能为空": {
        "en": "Token cannot be empty",
        "es": "El token no puede estar vacío",
        "pt": "O token não pode estar vazio",
        "ja": "トークンを空にできません",
        "ko": "토큰은 비울 수 없습니다",
        "fr": "Le jeton ne peut pas être vide",
        "de": "Token darf nicht leer sein",
    },
    "token无效或已过期": {
        "en": "Token is invalid or expired",
        "es": "Token inválido o expirado",
        "pt": "Token inválido ou expirado",
        "ja": "トークンが無効または期限切れです",
        "ko": "토큰이 유효하지 않거나 만료되었습니다",
        "fr": "Jeton invalide ou expiré",
        "de": "Token ungültig oder abgelaufen",
    },
    "Token 无效或已过期": {
        "en": "Token is invalid or expired",
        "es": "Token inválido o expirado",
        "pt": "Token inválido ou expirado",
        "ja": "トークンが無効または期限切れです",
        "ko": "토큰이 유효하지 않거나 만료되었습니다",
        "fr": "Jeton invalide ou expiré",
        "de": "Token ungültig oder abgelaufen",
    },
    "无效的用户名或密码": {
        "en": "Invalid username or password",
        "es": "Usuario o contraseña inválidos",
        "pt": "Nome de usuário ou senha inválidos",
        "ja": "ユーザー名またはパスワードが無効です",
        "ko": "잘못된 사용자 이름 또는 비밀번호",
        "fr": "Nom d'utilisateur ou mot de passe invalide",
        "de": "Ungültiger Benutzername oder Passwort",
    },
    "无效的token": {
        "en": "Invalid token",
        "es": "Token inválido",
        "pt": "Token inválido",
        "ja": "無効なトークン",
        "ko": "유효하지 않은 토큰",
        "fr": "Jeton invalide",
        "de": "Ungültiger Token",
    },
    "客户用户不存在": {
        "en": "Customer user does not exist",
        "es": "El usuario cliente no existe",
        "pt": "Usuário cliente não existe",
        "ja": "顧客ユーザーが存在しません",
        "ko": "고객 사용자가 존재하지 않습니다",
        "fr": "L'utilisateur client n'existe pas",
        "de": "Kundenbenutzer existiert nicht",
    },
    "查询成功": {
        "en": "Query successful",
        "es": "Consulta exitosa",
        "pt": "Consulta bem-sucedida",
        "ja": "照会に成功しました",
        "ko": "조회되었습니다",
        "fr": "Requête réussie",
        "de": "Abfrage erfolgreich",
    },
    "更新失败": {
        "en": "Update failed",
        "es": "Error al actualizar",
        "pt": "Falha na atualização",
        "ja": "更新に失敗しました",
        "ko": "업데이트에 실패했습니다",
        "fr": "Échec de la mise à jour",
        "de": "Aktualisierung fehlgeschlagen",
    },
}


def load_dict() -> dict[str, dict[str, str]]:
    data = {k: dict(v) for k, v in DICT.items()}
    if EXTRA_JSON.exists():
        extra = json.loads(EXTRA_JSON.read_text(encoding="utf-8"))
        for msgid, langs in extra.items():
            data.setdefault(msgid, {}).update(langs)
        print(f"已合并 JSON 词典: {EXTRA_JSON}")
    return data


def translate_one(po_path: Path, lang_key: str, mapping: dict[str, dict[str, str]]) -> None:
    po = polib.pofile(str(po_path))
    filled = skipped = tagged = 0
    for entry in po:
        if not entry.msgid or entry.msgid.strip() == "" or entry.msgstr:
            continue
        # 保留占位符的原文（含 %(name)s / {name}）原样进词典时请整句配置
        hit = mapping.get(entry.msgid, {}).get(lang_key)
        if hit:
            entry.msgstr = hit
            filled += 1
        elif FILL_MISSING_AS_TAG:
            entry.msgstr = f"[{lang_key}]{entry.msgid}"
            tagged += 1
        else:
            skipped += 1
    po.save()
    print(
        f"{po_path}: 填入 {filled}，占位 {tagged}，跳过 {skipped}"
    )


def main() -> None:
    mapping = load_dict()
    if not LOCALE_ROOT.exists():
        raise SystemExit(f"找不到 locale 目录: {LOCALE_ROOT}")

    for dir_name, lang_key in LANG_DIRS.items():
        po_path = LOCALE_ROOT / dir_name / "LC_MESSAGES" / "django.po"
        if not po_path.exists():
            print(f"跳过（无文件）: {po_path}")
            continue
        translate_one(po_path, lang_key, mapping)

    print("\n完成。请执行: python manage.py compilemessages")


if __name__ == "__main__":
    main()
