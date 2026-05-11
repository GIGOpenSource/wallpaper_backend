#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：view.py
@Author  ：Liang
@Date    ：2026/5/11
@description : 关键词研究视图 - Google Trends分析
"""
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework.decorators import action

from tool.base_views import BaseViewSet
from tool.permissions import IsAdmin
from tool.utils import ApiResponse
from .google_trends_tool import GoogleTrendsTool


@extend_schema(tags=["关键词研究"])
@extend_schema_view(
    interest_over_time=extend_schema(
        summary="关键词兴趣趋势",
        description="获取关键词随时间的搜索兴趣变化趋势，支持多个关键词对比",
        parameters=[
            OpenApiParameter(name="keywords", type=str, required=True, 
                           description="关键词，多个用逗号分隔，最多5个"),
            OpenApiParameter(name="geo", type=str, required=False, 
                           description="国家/地区代码（如US,CN），留空表示全球"),
            OpenApiParameter(name="timeframe", type=str, required=False, 
                           description="时间范围：now 1-H, now 4-H, now 7-d, today 1-m, today 3-m, today 12-m, today+5-y, all, 或自定义日期范围YYYY-MM-DD YYYY-MM-DD",
                           default='today 12-m'),
            OpenApiParameter(name="gprop", type=str, required=False, 
                           description="搜索类型：web(网页), images(图片), news(新闻), youtube, froogle(Google购物)",
                           default='', enum=['', 'web', 'images', 'news', 'youtube', 'froogle']),
        ],
    ),
    related_queries=extend_schema(
        summary="相关查询分析",
        description="获取关键词的热门相关查询和上升查询",
        parameters=[
            OpenApiParameter(name="keyword", type=str, required=True, description="要分析的关键词"),
            OpenApiParameter(name="geo", type=str, required=False, description="国家/地区代码"),
            OpenApiParameter(name="timeframe", type=str, required=False, description="时间范围", default='today 12-m'),
            OpenApiParameter(name="gprop", type=str, required=False, description="搜索类型", default=''),
        ],
    ),
    interest_by_region=extend_schema(
        summary="地区兴趣分布",
        description="获取关键词在不同地区的搜索兴趣度",
        parameters=[
            OpenApiParameter(name="keywords", type=str, required=True, description="关键词，多个用逗号分隔"),
            OpenApiParameter(name="geo", type=str, required=False, description="国家代码（如US），留空返回国家级别数据"),
            OpenApiParameter(name="timeframe", type=str, required=False, description="时间范围", default='today 12-m'),
        ],
    ),
    compare_keywords=extend_schema(
        summary="关键词对比",
        description="比较2-5个关键词的搜索趋势",
        parameters=[
            OpenApiParameter(name="keywords", type=str, required=True, 
                           description="要比较的关键词，用逗号分隔，2-5个"),
            OpenApiParameter(name="geo", type=str, required=False, description="国家/地区代码"),
            OpenApiParameter(name="timeframe", type=str, required=False, description="时间范围", default='today 12-m'),
        ],
    ),
    trending_searches=extend_schema(
        summary="热门搜索",
        description="获取当前热门搜索话题（每日趋势）",
        parameters=[
            OpenApiParameter(name="geo", type=str, required=False, description="国家/地区代码", default='US'),
            OpenApiParameter(name="category", type=str, required=False, description="分类", default='all'),
        ],
    ),
)
class KeywordResearchViewSet(BaseViewSet):
    """
    关键词研究 ViewSet
    基于Google Trends提供关键词分析功能
    """
    permission_classes = [IsAdmin]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trends_tool = GoogleTrendsTool()
    
    @action(detail=False, methods=['get'], name='关键词兴趣趋势')
    def interest_over_time(self, request):
        """
        获取关键词兴趣趋势
        
        示例：
        GET /api/seo/keyword/interest_over_time/?keywords=Cartoon,Anime&geo=&timeframe=today 12-m&gprop=
        GET /api/seo/keyword/interest_over_time/?keywords=Wallpaper&geo=US&timeframe=now 7-d&gprop=images
        """
        keywords_param = request.query_params.get('keywords')
        if not keywords_param:
            return ApiResponse(code=400, message="请提供 keywords 参数")
        
        # 解析关键词
        keywords = [k.strip() for k in keywords_param.split(',') if k.strip()]
        if len(keywords) > 5:
            return ApiResponse(code=400, message="最多支持5个关键词")
        
        geo = request.query_params.get('geo', '')
        timeframe = request.query_params.get('timeframe', 'today 12-m')
        gprop = request.query_params.get('gprop', '')
        
        # 验证gprop参数
        valid_gprops = ['', 'web', 'images', 'news', 'youtube', 'froogle']
        if gprop not in valid_gprops:
            return ApiResponse(code=400, message=f"gprop必须是以下值之一: {valid_gprops}")
        
        try:
            result = self.trends_tool.get_interest_over_time(
                keywords=keywords,
                geo=geo,
                timeframe=timeframe,
                gprop=gprop
            )
            
            if 'error' in result:
                error_msg = result['error']
                # 检查是否是连接错误
                if '无法连接' in error_msg or '科学上网' in error_msg:
                    return ApiResponse(
                        code=503, 
                        message=f"Google Trends服务不可用: {error_msg}"
                    )
                return ApiResponse(code=500, message=f"获取数据失败: {error_msg}")
            
            return ApiResponse(
                data=result,
                message="获取兴趣趋势成功"
            )
            
        except ConnectionError as e:
            return ApiResponse(
                code=503,
                message=str(e)
            )
        except Exception as e:
            return ApiResponse(code=500, message=f"请求失败: {str(e)}")
    
    @action(detail=False, methods=['get'], name='相关查询分析')
    def related_queries(self, request):
        """
        获取相关查询（热门查询和上升查询）
        
        示例：
        GET /api/seo/keyword/related_queries/?keyword=Cartoon&geo=US&timeframe=today 1-m
        """
        keyword = request.query_params.get('keyword')
        if not keyword:
            return ApiResponse(code=400, message="请提供 keyword 参数")
        
        geo = request.query_params.get('geo', '')
        timeframe = request.query_params.get('timeframe', 'today 12-m')
        gprop = request.query_params.get('gprop', '')
        
        try:
            result = self.trends_tool.get_related_queries(
                keyword=keyword,
                geo=geo,
                timeframe=timeframe,
                gprop=gprop
            )
            
            if 'error' in result:
                error_msg = result['error']
                if '无法连接' in error_msg or '科学上网' in error_msg:
                    return ApiResponse(code=503, message=f"Google Trends服务不可用: {error_msg}")
                return ApiResponse(code=500, message=f"获取数据失败: {error_msg}")
            
            return ApiResponse(
                data=result,
                message="获取相关查询成功"
            )
            
        except ConnectionError as e:
            return ApiResponse(code=503, message=str(e))
        except Exception as e:
            return ApiResponse(code=500, message=f"请求失败: {str(e)}")
    
    @action(detail=False, methods=['get'], name='地区兴趣分布')
    def interest_by_region(self, request):
        """
        获取按地区划分的兴趣度
        
        示例：
        GET /api/seo/keyword/interest_by_region/?keywords=Wallpaper,Cartoon&geo=US
        """
        keywords_param = request.query_params.get('keywords')
        if not keywords_param:
            return ApiResponse(code=400, message="请提供 keywords 参数")
        
        keywords = [k.strip() for k in keywords_param.split(',') if k.strip()]
        if len(keywords) > 5:
            return ApiResponse(code=400, message="最多支持5个关键词")
        
        geo = request.query_params.get('geo', '')
        timeframe = request.query_params.get('timeframe', 'today 12-m')
        
        try:
            result = self.trends_tool.get_interest_by_region(
                keywords=keywords,
                geo=geo,
                timeframe=timeframe
            )
            
            return ApiResponse(
                data={
                    'regions': result,
                    'keywords': keywords,
                    'geo': geo or 'Worldwide'
                },
                message="获取地区分布成功"
            )
            
        except Exception as e:
            return ApiResponse(code=500, message=f"请求失败: {str(e)}")
    
    @action(detail=False, methods=['get'], name='关键词对比')
    def compare_keywords(self, request):
        """
        比较多个关键词的趋势
        
        示例：
        GET /api/seo/keyword/compare_keywords/?keywords=Wallpaper,Background,Image&geo=US&timeframe=today 12-m
        """
        keywords_param = request.query_params.get('keywords')
        if not keywords_param:
            return ApiResponse(code=400, message="请提供 keywords 参数")
        
        keywords = [k.strip() for k in keywords_param.split(',') if k.strip()]
        if len(keywords) < 2 or len(keywords) > 5:
            return ApiResponse(code=400, message="需要提供2-5个关键词进行比较")
        
        geo = request.query_params.get('geo', '')
        timeframe = request.query_params.get('timeframe', 'today 12-m')
        
        try:
            result = self.trends_tool.compare_keywords(
                keywords=keywords,
                geo=geo,
                timeframe=timeframe
            )
            
            if 'error' in result:
                return ApiResponse(code=400, message=result['error'])
            
            return ApiResponse(
                data=result,
                message="关键词对比完成"
            )
            
        except Exception as e:
            return ApiResponse(code=500, message=f"请求失败: {str(e)}")
    
    @action(detail=False, methods=['get'], name='热门搜索')
    def trending_searches(self, request):
        """
        获取当前热门搜索话题
        
        示例：
        GET /api/seo/keyword/trending_searches/?geo=US
        """
        geo = request.query_params.get('geo', 'US')
        category = request.query_params.get('category', 'all')
        
        try:
            result = self.trends_tool.get_trending_searches(
                geo=geo,
                category=category
            )
            
            return ApiResponse(
                data={
                    'trending_searches': result,
                    'geo': geo,
                    'category': category
                },
                message="获取热门搜索成功"
            )
            
        except Exception as e:
            return ApiResponse(code=500, message=f"请求失败: {str(e)}")
