#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：view.py
@Author  ：Liang
@Date    ：2026/5/21
@description : 壁纸URL检测与清理
"""
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from rest_framework.decorators import action

from models.models import Wallpapers
from tool.base_views import BaseViewSet
from tool.permissions import IsAdmin
from tool.token_tools import _redis
from tool.utils import ApiResponse


# ==================== 序列化器 ====================

class WallpaperUrlCheckSerializer(serializers.Serializer):
    """壁纸URL检测序列化器"""
    start_id = serializers.IntegerField(required=True, min_value=1, help_text="起始壁纸ID")
    end_id = serializers.IntegerField(required=True, min_value=1, help_text="结束壁纸ID")


class WallpaperPoolQuerySerializer(serializers.Serializer):
    """壁纸删除池查询序列化器"""
    pool_token = serializers.CharField(required=True, help_text="删除池标识token")
    page = serializers.IntegerField(required=False, default=1, min_value=1, help_text="页码")
    page_size = serializers.IntegerField(required=False, default=50, min_value=1, max_value=200, help_text="每页数量")


class WallpaperPoolDeleteSerializer(serializers.Serializer):
    """壁纸批量删除序列化器"""
    pool_token = serializers.CharField(required=True, help_text="删除池标识token")
    wallpaper_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_null=True,
        help_text="要删除的壁纸ID列表，不传则删除整个池子的所有壁纸"
    )


@extend_schema(tags=["壁纸URL检测"])
@extend_schema_view(
    check_wallpaper_urls=extend_schema(
        summary="检测壁纸URL有效性",
        description="接收壁纸ID范围,通过本地服务器网络环境访问壁纸URL,将404的壁纸ID缓存到Redis删除池",
        request=WallpaperUrlCheckSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "pool_token": {"type": "string", "description": "删除池标识token"},
                            "checked_count": {"type": "integer", "description": "已检测数量"},
                            "total_in_range": {"type": "integer", "description": "范围内总数"},
                            "not_found_count": {"type": "integer", "description": "未找到数量"},
                            "not_found_ids": {"type": "array", "items": {"type": "integer"}, "description": "未找到的壁纸ID列表(前100个)"}
                        }
                    },
                    "message": {"type": "string", "example": "检测完成,共检测200个壁纸,发现50个无效URL"}
                }
            },
            400: {"description": "参数错误"}
        }
    ),
    get_delete_pool=extend_schema(
        summary="获取删除池",
        description="获取指定删除池的壁纸ID列表,支持分页查询",
        parameters=[
            OpenApiParameter(name="pool_token", type=str, required=True, description="删除池标识token"),
            OpenApiParameter(name="page", type=int, required=False, description="页码,默认1"),
            OpenApiParameter(name="page_size", type=int, required=False, description="每页数量,默认50"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "pool_token": {"type": "string", "description": "删除池标识token"},
                            "total_count": {"type": "integer", "description": "总数量"},
                            "page": {"type": "integer", "description": "当前页码"},
                            "page_size": {"type": "integer", "description": "每页数量"},
                            "wallpaper_ids": {"type": "array", "items": {"type": "integer"}, "description": "壁纸ID列表"}
                        }
                    },
                    "message": {"type": "string", "example": "获取成功"}
                }
            },
            404: {"description": "删除池不存在或已过期"}
        }
    ),
    delete_from_pool=extend_schema(
        summary="从删除池批量删除壁纸",
        description="根据删除池token和壁纸ID列表,批量删除壁纸",
        request=WallpaperPoolDeleteSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "pool_token": {"type": "string", "description": "删除池标识token"},
                            "deleted_count": {"type": "integer", "description": "实际删除数量"},
                            "requested_count": {"type": "integer", "description": "请求删除数量"}
                        }
                    },
                    "message": {"type": "string", "example": "成功删除50个壁纸"}
                }
            },
            400: {"description": "参数错误"},
            404: {"description": "删除池不存在或已过期"}
        }
    )
)
class WallpaperCheckViewSet(BaseViewSet):
    """
    壁纸URL检测 ViewSet
    提供壁纸URL有效性检测、删除池管理、批量删除功能
    """
    permission_classes = [IsAdmin]

    @action(detail=False, methods=['post'], url_path='check-wallpaper-urls', name='检测壁纸URL')
    def check_wallpaper_urls(self, request):
        """
        检测壁纸URL有效性
        接收壁纸ID范围，通过本地服务器网络环境访问壁纸URL，将404的壁纸ID缓存到Redis删除池
        使用并发请求提升检测速度
        """
        serializer = WallpaperUrlCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        start_id = serializer.validated_data['start_id']
        end_id = serializer.validated_data['end_id']
        
        if start_id > end_id:
            return ApiResponse(code=400, message="起始ID不能大于结束ID")
        
        # 获取壁纸列表
        wallpapers = list(Wallpapers.objects.filter(id__gte=start_id, id__lte=end_id).values('id', 'url'))
        
        if not wallpapers:
            return ApiResponse(data={'checked_count': 0, 'not_found_ids': []}, message="指定范围内没有壁纸")
        
        # User-Agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        not_found_ids = []
        checked_count = 0
        
        # 单个URL检测函数
        def check_single_url(wallpaper):
            wallpaper_id = wallpaper['id']
            wallpaper_url = wallpaper['url']
            
            try:
                # 发送HEAD请求检测URL
                response = requests.head(
                    wallpaper_url,
                    headers=headers,
                    timeout=5,
                    allow_redirects=True,
                    verify=False
                )
                
                # 如果返回404，记录ID
                if response.status_code == 404:
                    return wallpaper_id
                return None
                
            except Exception as e:
                # 请求失败也记录下来
                print(f"壁纸ID {wallpaper_id} URL检测失败: {str(e)}")
                return wallpaper_id
        
        # 使用线程池并发检测，最多50个并发
        max_workers = min(50, len(wallpapers))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_id = {executor.submit(check_single_url, wallpaper): wallpaper['id'] 
                           for wallpaper in wallpapers}
            
            # 收集结果
            for future in as_completed(future_to_id):
                try:
                    result = future.result()
                    if result is not None:
                        not_found_ids.append(result)
                    checked_count += 1
                except Exception as e:
                    print(f"检测任务异常: {str(e)}")
                    checked_count += 1
        
        # 生成删除池token：当前日期 + 时间戳
        now = datetime.now()
        pool_token = f"wallpaper_delete_{now.strftime('%Y%m%d_%H%M%S')}"
        
        # 将404的壁纸ID缓存到Redis
        if not_found_ids:
            redis_key = f"wallpaper:delete_pool:{pool_token}"
            _redis.setKey(redis_key, json.dumps(not_found_ids), ex=86400 * 7)  # 缓存7天
        
        response_data = {
            'pool_token': pool_token,
            'checked_count': checked_count,
            'total_in_range': len(wallpapers),
            'not_found_count': len(not_found_ids),
            'not_found_ids': not_found_ids[:100],  # 只返回前100个，避免响应过大
        }
        
        message = f"检测完成，共检测{checked_count}个壁纸，发现{len(not_found_ids)}个无效URL"
        return ApiResponse(data=response_data, message=message)

    @action(detail=False, methods=['get'], url_path='get-delete-pool', name='获取删除池')
    def get_delete_pool(self, request):
        """
        获取指定删除池的壁纸ID列表
        """
        serializer = WallpaperPoolQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        pool_token = serializer.validated_data['pool_token']
        page = serializer.validated_data['page']
        page_size = serializer.validated_data['page_size']
        
        # 从Redis获取删除池数据
        redis_key = f"wallpaper:delete_pool:{pool_token}"
        cached_data = _redis.getKey(redis_key)
        
        if not cached_data:
            return ApiResponse(code=404, message="删除池不存在或已过期")
        
        # 解析数据
        try:
            all_ids = json.loads(cached_data)
        except Exception as e:
            return ApiResponse(code=500, message=f"数据解析失败: {str(e)}")
        
        # 分页处理
        total_count = len(all_ids)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_ids = all_ids[start_idx:end_idx]
        
        response_data = {
            'pool_token': pool_token,
            'total_count': total_count,
            'page': page,
            'page_size': page_size,
            'wallpaper_ids': page_ids,
        }
        
        return ApiResponse(data=response_data, message="获取成功")

    @action(detail=False, methods=['post'], url_path='delete-from-pool', name='从删除池批量删除壁纸')
    def delete_from_pool(self, request):
        """
        根据删除池token和壁纸ID列表，批量删除壁纸
        如果传了wallpaper_ids则删除指定的，如果没传则删除整个池子的所有壁纸
        """
        serializer = WallpaperPoolDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        pool_token = serializer.validated_data['pool_token']
        wallpaper_ids = serializer.validated_data.get('wallpaper_ids')
        
        # 验证删除池是否存在
        redis_key = f"wallpaper:delete_pool:{pool_token}"
        cached_data = _redis.getKey(redis_key)
        
        if not cached_data:
            return ApiResponse(code=404, message="删除池不存在或已过期")
        
        # 解析Redis中的数据
        try:
            all_ids = json.loads(cached_data)
        except Exception as e:
            return ApiResponse(code=500, message=f"数据解析失败: {str(e)}")
        
        # 如果没有传wallpaper_ids，则删除整个池子的所有壁纸
        if not wallpaper_ids:
            wallpaper_ids = all_ids
        
        if not wallpaper_ids:
            return ApiResponse(code=400, message="壁纸ID列表不能为空")
        
        # 批量删除壁纸
        deleted_count, _ = Wallpapers.objects.filter(id__in=wallpaper_ids).delete()
        
        # 从Redis中移除已删除的ID
        try:
            remaining_ids = [wid for wid in all_ids if wid not in wallpaper_ids]
            if remaining_ids:
                _redis.setKey(redis_key, json.dumps(remaining_ids), ex=86400 * 7)
            else:
                # 如果全部删除，移除Redis key
                _redis.delKey(redis_key)
        except Exception as e:
            print(f"更新Redis删除池失败: {str(e)}")
        
        response_data = {
            'pool_token': pool_token,
            'deleted_count': deleted_count,
            'requested_count': len(wallpaper_ids),
            'total_in_pool': len(all_ids),
        }
        
        message = f"成功删除{deleted_count}个壁纸"
        return ApiResponse(data=response_data, message=message)
