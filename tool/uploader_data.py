# -*- coding=utf-8 -*-
import os
import uuid
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
import sys
import logging
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiParameter



from .utils import ApiResponse
from tool.tools import getEnvConfig
# 配置日志
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# COS配置
secret_id = getEnvConfig('TENCENT_COS_SECRET_ID')
secret_key = getEnvConfig('TENCENT_COS_SECRET_KEY')
region = getEnvConfig('TENCENT_COS_REGION', 'ap-shanghai')
bucket_name = getEnvConfig('TENCENT_COS_BUCKET', 'crashcheck-1256118830')

# 初始化COS客户端
try:
    config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
    cos_client = CosS3Client(config)
    print("COS客户端初始化成功")
except Exception as e:
    print("COS客户端初始化失败:", e)
from PIL import Image
import io


def bytes_from_uploaded_image(uploaded_file, quality=100):
    """
    读取上传文件字节。
    - quality 为 100（默认）时：不做转码，保留原图（jpg/png/webp 等）。
    - quality 1–99 且为图片时：转为 JPEG 并压缩（与历史 UploadResourceView 行为一致）。
    """
    try:
        q = int(quality)
    except (TypeError, ValueError):
        q = 100
    q = max(1, min(100, q))
    ct = (getattr(uploaded_file, "content_type", None) or "").lower()
    data = uploaded_file.read()
    if not ct.startswith("image/") or q >= 100:
        return data
    try:
        image = Image.open(io.BytesIO(data))
        if image.mode in ("RGBA", "LA"):
            image = image.convert("RGB")
        output_buffer = io.BytesIO()
        image.save(output_buffer, format="JPEG", quality=q, optimize=True)
        return output_buffer.getvalue()
    except Exception:
        return data


@extend_schema(tags=['上传管理'])
class UploadResourceView(APIView):
    """
    上传资源到腾讯云COS接口
    接收文件和名称，返回访问地址
    """
    parser_classes = (MultiPartParser, FormParser)

    @extend_schema(
        summary='上传头像/图片/视频资源到COS',
        description='上传文件到腾讯云COS，返回可访问的URL地址',
        parameters=[
            OpenApiParameter(
                name='type',
                type=str,
                location=OpenApiParameter.QUERY,
                description='文件类型: img, video 等',
                required=False
            ),
            OpenApiParameter(
                name='file_name',
                type=str,
                location=OpenApiParameter.QUERY,
                description='自定义文件名',
                required=False
            ),
            OpenApiParameter(
                name='quality',
                type=int,
                location=OpenApiParameter.QUERY,
                description='图像质量（1-100），默认85',
                required=False
            )
        ],
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {
                        'type': 'string',
                        'format': 'binary',
                        'description': '要上传的文件'
                    }
                },
                'required': ['file']
            }
        },
        responses={
            200: {
                'description': '上传成功',
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'code': {'type': 'integer', 'example': 200},
                                'message': {'type': 'string', 'example': '上传成功'},
                                'data': {
                                    'type': 'object',
                                    'properties': {
                                        'url': {'type': 'string', 'example': 'https://crashcheck-1256118830.cos.ap-shanghai.myqcloud.com/img/abc123.png'},
                                        'name': {'type': 'string', 'example': 'img/abc123.png'}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            400: {
                'description': '请求参数错误',
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'code': {'type': 'integer', 'example': 400},
                                'message': {'type': 'string', 'example': '未找到上传文件'},
                                'data': {'type': 'object', 'example': {}}
                            }
                        }
                    }
                }
            },
            500: {
                'description': '服务器内部错误',
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'code': {'type': 'integer', 'example': 500},
                                'message': {'type': 'string', 'example': '上传过程中发生错误'},
                                'data': {'type': 'object', 'example': {}}
                            }
                        }
                    }
                }
            }
        }
    )
    def post(self, request):
        try:
            # 获取上传的文件
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                return ApiResponse(
                    data={},
                    message="未找到上传文件",
                    code=400
                )

            # 获取type参数
            file_type = request.query_params.get('type', '')

            # 获取name参数（优先使用查询参数中的name，其次使用表单中的name，最后使用文件名）
            file_name = (request.query_params.get('file_name') or
                        request.POST.get('file_name') or
                        uploaded_file.name)
            quality = int(request.query_params.get('quality', '85'))
            if quality < 1 or quality > 100:
                quality = 85
            # 如果没有提供文件名，则使用UUID生成唯一文件名
            if not file_name or file_name == uploaded_file.name:
                ext = os.path.splitext(uploaded_file.name)[1]
                file_name = f"{uuid.uuid4().hex}{ext}"

            # 构建带路径的文件名
            if file_type:
                full_file_name = f"{file_type}/{file_name}"
            else:
                full_file_name = file_name

            file_content = bytes_from_uploaded_image(uploaded_file, quality=quality)

            # 上传到COS
            response = cos_client.put_object(
                Bucket=bucket_name,
                Body=file_content,
                Key=full_file_name,
                StorageClass='MAZ_STANDARD',  # 使用多可用区存储类
                EnableMD5=False
            )
            if response['ETag']:
                # 生成文件访问URL
                file_url = f"https://{bucket_name}.cos.{region}.myqcloud.com/{full_file_name}"
                return ApiResponse(
                    data={
                        'url': file_url,
                        'name': full_file_name
                    },
                    message="上传成功",
                    code=200
                )
            else:
                return ApiResponse(
                    data={},
                    message="上传失败",
                    code=500
                )

        except Exception as e:
            return ApiResponse(
                data={},
                message=f"上传过程中发生错误: {str(e)}",
                code=500
            )


def upload_image_to_cos(file_content, full_file_name):
    """
    上传图片到腾讯云COS

    Args:
        file_content: 文件内容（bytes）
        full_file_name: 完整文件名（包含路径）

    Returns:
        dict: 包含url和name的字典，或None（上传失败时）
    """
    try:
        response = cos_client.put_object(
            Bucket=bucket_name,
            Body=file_content,
            Key=full_file_name,
            StorageClass='MAZ_STANDARD',
            EnableMD5=False
        )
        if response['ETag']:
            file_url = f"https://{bucket_name}.cos.{region}.myqcloud.com/{full_file_name}"
            return {
                'url': file_url,
                'name': full_file_name
            }
        return None
    except Exception as e:
        logging.error(f"上传图片到COS失败: {str(e)}")
        return None
