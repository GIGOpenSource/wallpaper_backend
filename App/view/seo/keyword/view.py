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
from rest_framework import serializers
from rest_framework.decorators import action

from models.models import KeywordLibrary
from tool.base_views import BaseViewSet
from tool.permissions import IsAdmin
from tool.utils import ApiResponse, CustomPagination
from .google_trends_tool import GoogleTrendsTool
from tool.keyword_mining_tool import KeywordMiningTool


class KeywordLibrarySerializer(serializers.ModelSerializer):
    """关键词词库序列化器"""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    keyword_type_display = serializers.CharField(source='get_keyword_type_display', read_only=True)

    class Meta:
        model = KeywordLibrary
        fields = [
            'id', 'keyword', 'keyword_type', 'keyword_type_display', 'category', 'category_display',
            'monthly_search_volume', 'optimization_difficulty', 'cpc',
            'trend', 'competition', 'is_favorite',
            'parent_keyword', 'recommendation_score',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


@extend_schema(tags=["关键词研究"])
@extend_schema_view(
    list=extend_schema(
        summary="获取关键词列表",
        description="获取关键词词库列表，支持按关键词、分类、类型、收藏状态筛选",
        parameters=[
            OpenApiParameter(name="keyword", type=str, required=False, description="关键词模糊搜索"),
            OpenApiParameter(name="category", type=str, required=False, description="分类：style/theme/device/type"),
            OpenApiParameter(name="keyword_type", type=str, required=False, description="类型：core(核心词)/long_tail(长尾词)"),
            OpenApiParameter(name="is_favorite", type=bool, required=False, description="是否收藏"),
        ],
    ),
    retrieve=extend_schema(
        summary="获取关键词详情",
        description="根据ID获取关键词详细信息",
    ),
    create=extend_schema(
        summary="创建关键词",
        description="新增一个关键词到词库",
    ),
    update=extend_schema(
        summary="更新关键词",
        description="全量更新关键词信息",
    ),
    partial_update=extend_schema(
        summary="部分更新关键词",
        description="部分更新关键词信息",
    ),
    destroy=extend_schema(
        summary="删除关键词",
        description="从词库中删除关键词",
    ),
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
    基于Google Trends提供关键词分析功能，并提供关键词词库管理
    """
    permission_classes = [IsAdmin]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trends_tool = GoogleTrendsTool()
        self.mining_tool = KeywordMiningTool()
    
    # ==================== 关键词词库 CRUD ====================
    
    queryset = KeywordLibrary.objects.all()
    serializer_class = KeywordLibrarySerializer
    pagination_class = CustomPagination
    
    def list(self, request, *args, **kwargs):
        """获取关键词列表，支持按类型、分类、收藏状态筛选"""
        queryset = KeywordLibrary.objects.all()
        
        # 1. 按关键词类型筛选（核心逻辑：区分热门、长尾、普通）
        keyword_type = request.query_params.get('keyword_type')
        if keyword_type:
            queryset = queryset.filter(keyword_type=keyword_type)
        
        # 2. 按关键词模糊搜索
        keyword = request.query_params.get('keyword')
        if keyword:
            queryset = queryset.filter(keyword__icontains=keyword)
        
        # 3. 按分类筛选
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # 4. 按收藏状态筛选
        is_favorite = request.query_params.get('is_favorite')
        if is_favorite is not None:
            queryset = queryset.filter(is_favorite=is_favorite.lower() == 'true')
        
        queryset = queryset.order_by('-monthly_search_volume')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="关键词列表获取成功")
    
    def create(self, request, *args, **kwargs):
        """创建关键词"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return ApiResponse(data=serializer.data, message="关键词创建成功", code=201)
    
    def retrieve(self, request, *args, **kwargs):
        """获取关键词详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return ApiResponse(data=serializer.data, message="获取成功")
    
    def update(self, request, *args, **kwargs):
        """全量更新关键词"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return ApiResponse(data=serializer.data, message="关键词更新成功")
    
    def partial_update(self, request, *args, **kwargs):
        """部分更新关键词"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return ApiResponse(data=serializer.data, message="关键词更新成功")
    
    def destroy(self, request, *args, **kwargs):
        """删除关键词"""
        instance = self.get_object()
        instance.delete()
        return ApiResponse(message="关键词删除成功")
    
    # ==================== Google Trends 分析接口 ====================
    
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
    
    # ==================== AI 关键词挖掘接口 ====================
    
    @extend_schema(
        summary="AI 挖掘热门关键词",
        description="基于种子关键词，使用 AI 挖掘相关的热门关键词",
        parameters=[
            OpenApiParameter(name="seed_keyword", type=str, required=True, description="种子关键词"),
            OpenApiParameter(name="category", type=str, required=False, description="分类：style/theme/device/type", default='style'),
            OpenApiParameter(name="count", type=int, required=False, description="返回数量（10-20）", default=15),
        ],
    )
    @action(detail=False, methods=['get'], name='AI 挖掘热门关键词')
    def ai_mine_hot_keywords(self, request):
        """AI 挖掘热门关键词（挖掘后自动持久化到词库）"""
        seed_keyword = request.query_params.get('seed_keyword')
        if not seed_keyword:
            return ApiResponse(code=400, message="请提供 seed_keyword 参数")
        
        category = request.query_params.get('category', 'style')
        count = int(request.query_params.get('count', 15))
        
        # 限制数量范围
        if count < 10:
            count = 10
        elif count > 20:
            count = 20
        
        try:
            keywords = self.mining_tool.mine_hot_keywords(
                seed_keyword=seed_keyword,
                category=category,
                count=count
            )
            
            # 核心逻辑：批量持久化
            saved_count = 0
            for item in keywords:
                kw, created = KeywordLibrary.objects.update_or_create(
                    keyword=item.get('keyword'),
                    defaults={
                        'keyword_type': 'hot',  # 标记为热门关键词
                        'category': item.get('category', category),
                        'monthly_search_volume': item.get('monthly_search_volume', 0),
                        'optimization_difficulty': item.get('optimization_difficulty', 0),
                        'cpc': item.get('cpc', 0),
                        'trend': item.get('trend', 'stable'),
                        'competition': item.get('competition', 0),
                    }
                )
                if created:
                    saved_count += 1
            
            return ApiResponse(
                data={
                    'seed_keyword': seed_keyword,
                    'category': category,
                    'keywords': keywords,
                    'total': len(keywords),
                    'saved_to_library': saved_count
                },
                message=f"成功挖掘 {len(keywords)} 个热门关键词，其中 {saved_count} 个已新存入词库"
            )
        except Exception as e:
            return ApiResponse(code=500, message=f"挖掘失败: {str(e)}")
    
    @extend_schema(
        summary="AI 扩展长尾关键词",
        description="基于父关键词，使用 AI 扩展相关的长尾关键词，支持词性和修饰词筛选",
        parameters=[
            OpenApiParameter(name="parent_keyword", type=str, required=True, description="父关键词（核心词）"),
            OpenApiParameter(name="pos", type=str, required=False, description="词性：noun(名词)/adjective(形容词)/verb(动词)", default='noun'),
            OpenApiParameter(name="modifiers", type=str, required=False, description="修饰词，逗号分隔（如：4k,高清,免费,下载）"),
            OpenApiParameter(name="count", type=int, required=False, description="返回数量（10-20）", default=15),
        ],
    )
    @action(detail=False, methods=['get'], name='AI 扩展长尾关键词')
    def ai_expand_long_tail(self, request):
        """AI 扩展长尾关键词（扩展后自动持久化到词库）"""
        parent_keyword = request.query_params.get('parent_keyword')
        if not parent_keyword:
            return ApiResponse(code=400, message="请提供 parent_keyword 参数")
        
        pos = request.query_params.get('pos', 'noun')
        modifiers = request.query_params.get('modifiers', '')
        count = int(request.query_params.get('count', 15))
        
        # 限制数量范围
        if count < 10:
            count = 10
        elif count > 20:
            count = 20
        
        try:
            keywords = self.mining_tool.expand_long_tail_keywords(
                parent_keyword=parent_keyword,
                pos=pos,
                modifiers=modifiers,
                count=count
            )
            
            # 核心逻辑：批量持久化
            saved_count = 0
            for item in keywords:
                kw, created = KeywordLibrary.objects.update_or_create(
                    keyword=item.get('long_tail_keyword'),
                    defaults={
                        'keyword_type': 'long_tail',
                        'parent_keyword': parent_keyword,
                        'monthly_search_volume': item.get('monthly_search_volume', 0),
                        'optimization_difficulty': item.get('optimization_difficulty', 0),
                        'cpc': item.get('cpc', 0),
                        'recommendation_score': item.get('recommendation_score', 0),
                    }
                )
                if created:
                    saved_count += 1
            
            return ApiResponse(
                data={
                    'parent_keyword': parent_keyword,
                    'pos': pos,
                    'modifiers': modifiers,
                    'keywords': keywords,
                    'total': len(keywords),
                    'saved_to_library': saved_count
                },
                message=f"成功扩展 {len(keywords)} 个长尾关键词，其中 {saved_count} 个已新存入词库"
            )
        except Exception as e:
            return ApiResponse(code=500, message=f"扩展失败: {str(e)}")
