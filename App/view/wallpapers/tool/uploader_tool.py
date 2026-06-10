import io
import json
import os
import uuid

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import F, Case, When, IntegerField, Q
from django.db.models.functions import Greatest
from PIL import Image
from django.utils import timezone

from App.view.wallpapers.search_models.search_models import TAG_MAPPING
from models.models import WallpaperTag
from tool.base_views import BaseViewSet
from tool.middleware import logger
from tool.permissions import IsCustomerTokenValid, IsOwnerOrAdmin, IsAdmin
from tool.token_tools import CustomTokenTool
from tool.uploader_data import bytes_from_uploaded_image, upload_image_to_cos
from tool.utils import CustomPagination, ApiResponse
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiRequest, OpenApiExample
from django.utils.translation import get_language, gettext as _, activate
import pandas as pd
from rest_framework.decorators import api_view, action
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser, FormParser


def _image_meta_from_bytes(content: bytes):
    try:
        with Image.open(io.BytesIO(content)) as im:
            fmt = (im.format or "").lower() or None
            return im.width, im.height, fmt
    except Exception:
        return 0, 0, None


# ====================== 抽离的公共上传方法 ======================
def _upload_and_get_urls(uploaded_file, token):
    """
    上传图片/视频到 COS，返回：url, thumb_url, w, h, fmt, is_live, cos_key
    """
    import uuid
    import os

    orig_name = uploaded_file.name or "image.jpg"
    name_part, ext = os.path.splitext(orig_name)
    ext = ext.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4"):
        ext = ".jpg"

    token_suffix = token[-8:] if token and len(token) >= 8 else (token or "00000000")[-8:].ljust(8, '0')
    unique_base = f"{token_suffix}_{name_part}"
    cos_key = f"person_wallpaper/{unique_base}{ext}"
    thumb_cos_key = f"person_wallpaper/{unique_base}_thumb{ext}"
    _ext_hint = ext.lstrip(".")

    try:
        file_content = bytes_from_uploaded_image(uploaded_file, quality=100)
    except Exception as e:
        logger.error(f"读取文件失败: {e}")
        return None

    cos_ret = upload_image_to_cos(file_content, cos_key)
    if not cos_ret:
        return None
    file_url = cos_ret["url"]

    # 缩略图 / 元信息
    if ext == ".mp4":
        thumb_url = ""
        w, h, pil_fmt = 0, 0, "mp4"
    else:
        try:
            uploaded_file.seek(0)
            thumb_content = bytes_from_uploaded_image(uploaded_file, quality=10)
            thumb_ret = upload_image_to_cos(thumb_content, thumb_cos_key)
            thumb_url = thumb_ret["url"] if thumb_ret else f"{file_url.rsplit('.',1)[0]}_thumb.{_ext_hint}"
        except:
            thumb_url = ""
        w, h, pil_fmt = _image_meta_from_bytes(file_content)

    fmt = (pil_fmt or _ext_hint or "").lower()
    if fmt == "jpeg":
        fmt = "jpg"
    is_live = (ext == ".mp4")
    return file_url, thumb_url, w, h, fmt, is_live, cos_key

# ====================== 抽离：标签获取 ======================
def _get_tag_objects(tag_ids, tag_names):
    #0
    tag_objs = []
    for tid in tag_ids:
        t = WallpaperTag.objects.filter(pk=tid).first()
        if t:
            tag_objs.append(t)
    for nm in tag_names:
        nm_clean = nm[:50].strip()
        if nm_clean:
            t, _ = WallpaperTag.objects.get_or_create(name=nm_clean)
            tag_objs.append(t)
    return list({t.id: t for t in tag_objs}.values())