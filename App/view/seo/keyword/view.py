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
import csv
import io
from django.http import HttpResponse

from models.models import KeywordLibrary, Competitor, WebsiteKeyword
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
            OpenApiParameter(name="keyword_type", type=str, required=False, description="类型：hot(热门)/long_tail(长尾词)/normal(词库)"),
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
        """获取关键词列表，支持按类型、分类、收藏状态筛选和排序"""
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
        
        # 5. 排序逻辑
        order_by = request.query_params.get('order_by', 'monthly_search_volume')
        order_direction = request.query_params.get('order_direction', 'desc')
        
        # 构建排序字段
        valid_order_fields = ['monthly_search_volume', 'updated_at', 'created_at', 'optimization_difficulty', 'cpc']
        if order_by not in valid_order_fields:
            order_by = 'monthly_search_volume'
        
        # 确定排序方向
        if order_direction.lower() == 'asc':
            sort_field = order_by
        else:
            sort_field = f'-{order_by}'
        
        queryset = queryset.order_by(sort_field)
        
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
    
    @extend_schema(
        summary="导出关键词",
        description="根据筛选条件或ID列表导出关键词数据为 CSV 文件，支持全选/多选/反选",
        parameters=[
            OpenApiParameter(name="category", type=str, required=False, description="分类：style/theme/device/type"),
            OpenApiParameter(name="keyword_type", type=str, required=False, description="类型：hot(热门)/long_tail(长尾词)/normal(词库)"),
            OpenApiParameter(name="ids", type=str, required=False, description="关键词 ID 列表，逗号分隔，如：1,3,4,5,13,54"),
            OpenApiParameter(name="select_all", type=bool, required=False, description="全选标识：true(全部导出)/null(默认，按ids导出)/false(反选，排除ids)"),
        ],
    )
    @action(detail=False, methods=['get'], name='导出关键词')
    def export_keywords(self, request):
        """导出关键词为 CSV 文件，支持全选/多选/反选"""
        # 获取筛选参数
        category = request.query_params.get('category')
        keyword_type = request.query_params.get('keyword_type')
        ids_param = request.query_params.get('ids')
        select_all = request.query_params.get('select_all')
        
        # 构建查询集
        queryset = KeywordLibrary.objects.all()
        
        # 应用基础筛选（分类和类型）
        if category:
            queryset = queryset.filter(category=category)
        
        if keyword_type:
            queryset = queryset.filter(keyword_type=keyword_type)
        
        # 处理选择逻辑
        if select_all is not None:
            select_all_lower = select_all.lower() if isinstance(select_all, str) else str(select_all).lower()
            
            if select_all_lower == 'true':
                # 全选：导出所有符合基础筛选的数据
                pass
            elif select_all_lower == 'false':
                # 反选：排除指定的 IDs
                if ids_param:
                    try:
                        ids = [int(id_str.strip()) for id_str in ids_param.split(',') if id_str.strip()]
                        queryset = queryset.exclude(id__in=ids)
                    except ValueError:
                        return ApiResponse(code=400, message="ID 格式错误")
            else:
                # null 或其他值：按 IDs 导出（多选）
                if ids_param:
                    try:
                        ids = [int(id_str.strip()) for id_str in ids_param.split(',') if id_str.strip()]
                        queryset = queryset.filter(id__in=ids)
                    except ValueError:
                        return ApiResponse(code=400, message="ID 格式错误")
                else:
                    # 如果没有传 IDs 且 select_all 不是 true，返回空结果
                    queryset = KeywordLibrary.objects.none()
        else:
            # select_all 为 null：按 IDs 导出（默认行为）
            if ids_param:
                try:
                    ids = [int(id_str.strip()) for id_str in ids_param.split(',') if id_str.strip()]
                    queryset = queryset.filter(id__in=ids)
                except ValueError:
                    return ApiResponse(code=400, message="ID 格式错误")
            # 如果既没有 select_all 也没有 ids，则按分类和类型导出全部
        
        # 按搜索量降序排列
        queryset = queryset.order_by('-monthly_search_volume')
        
        # 确定文件名标签
        if select_all and select_all.lower() == 'true':
            category_label = category or 'all'
            type_label = keyword_type or 'all'
        elif ids_param:
            category_label = 'selected'
            type_label = f'{len(ids_param.split(","))}个'
        else:
            category_label = category or 'all'
            type_label = keyword_type or 'all'
        
        return self._generate_csv_response(queryset, category_label, type_label)
    
    def _generate_csv_response(self, queryset, category_label, type_label):
        """生成 CSV 响应文件的通用方法"""
        # 创建内存中的 CSV 文件
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow([
            'ID', '关键词', '类型', '分类', '月搜索量',
            '优化难度', 'CPC', '趋势', '竞争度',
            '是否收藏', '父关键词', '推荐分数', '创建时间', '更新时间'
        ])
        
        # 写入数据行
        for kw in queryset:
            writer.writerow([
                kw.id,
                kw.keyword,
                kw.get_keyword_type_display(),
                kw.get_category_display(),
                kw.monthly_search_volume,
                kw.optimization_difficulty,
                kw.cpc,
                kw.trend,
                kw.competition,
                '是' if kw.is_favorite else '否',
                kw.parent_keyword or '',
                kw.recommendation_score,
                kw.created_at.strftime('%Y-%m-%d %H:%M:%S') if kw.created_at else '',
                kw.updated_at.strftime('%Y-%m-%d %H:%M:%S') if kw.updated_at else ''
            ])
        
        # 生成响应
        response = HttpResponse(
            content_type='text/csv; charset=utf-8-sig',
            headers={'Content-Disposition': f'attachment; filename="keywords_{category_label}_{type_label}.csv"'}
        )
        response.write(output.getvalue())
        
        return response
    
    @extend_schema(
        summary="导入关键词",
        description="从 CSV 或 Excel 文件导入关键词数据",
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {'type': 'string', 'format': 'binary', 'description': 'CSV 或 Excel 文件'},
                    'keyword_type': {'type': 'string', 'description': '关键词类型：hot/long_tail/normal', 'default': 'normal'},
                },
                'required': ['file']
            }
        },
    )
    @action(detail=False, methods=['post'], name='导入关键词')
    def import_keywords(self, request):
        """从 CSV 文件导入关键词"""
        file_obj = request.FILES.get('file')
        if not file_obj:
            return ApiResponse(code=400, message="请上传文件")
        
        # 获取关键词类型参数（可选，默认 normal）
        keyword_type = request.POST.get('keyword_type', 'normal')
        
        # 验证文件类型
        if not file_obj.name.endswith('.csv'):
            return ApiResponse(code=400, message="仅支持 CSV 格式文件")
        
        try:
            # 读取 CSV 文件
            decoded_file = file_obj.read().decode('utf-8-sig')
            csv_reader = csv.DictReader(io.StringIO(decoded_file))
            
            success_count = 0
            error_count = 0
            errors = []
            
            for row_num, row in enumerate(csv_reader, start=2):  # 从第2行开始（第1行是表头）
                try:
                    # 提取字段
                    keyword = row.get('关键词', '').strip()
                    if not keyword:
                        errors.append(f"第{row_num}行：关键词不能为空")
                        error_count += 1
                        continue
                    
                    # 准备数据
                    data = {
                        'keyword_type': keyword_type,
                        'monthly_search_volume': int(row.get('月搜索量', 0) or 0),
                        'optimization_difficulty': float(row.get('优化难度', 0) or 0),
                        'cpc': float(row.get('CPC', 0) or 0),
                        'trend': row.get('趋势', 'stable'),
                        'competition': float(row.get('竞争度', 0) or 0),
                        'is_favorite': row.get('是否收藏', '否') == '是',
                        'parent_keyword': row.get('父关键词', '').strip() or None,
                        'recommendation_score': int(row.get('推荐分数', 0) or 0),
                    }
                    
                    # 处理分类映射（中文转英文）
                    category_display = row.get('分类', '风格').strip()
                    category_map = {
                        '风格': 'style',
                        '主题': 'theme',
                        '设备': 'device',
                        '类型': 'type',
                    }
                    data['category'] = category_map.get(category_display, 'style')
                    
                    # 使用 update_or_create 实现幂等导入
                    kw, created = KeywordLibrary.objects.update_or_create(
                        keyword=keyword,
                        defaults=data
                    )
                    
                    if created:
                        success_count += 1
                    else:
                        # 如果已存在，也算成功（更新）
                        success_count += 1
                        
                except Exception as e:
                    errors.append(f"第{row_num}行：{str(e)}")
                    error_count += 1
            
            return ApiResponse(
                data={
                    'success_count': success_count,
                    'error_count': error_count,
                    'errors': errors[:10] if errors else []  # 最多返回10条错误信息
                },
                message=f"导入完成：成功 {success_count} 条，失败 {error_count} 条"
            )
            
        except UnicodeDecodeError:
            return ApiResponse(code=400, message="文件编码错误，请使用 UTF-8 编码的 CSV 文件")
        except Exception as e:
            return ApiResponse(code=500, message=f"导入失败: {str(e)}")
    
    @extend_schema(
        summary="批量收藏关键词",
        description="根据关键词 ID 列表批量设置收藏状态",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'ids': {
                        'oneOf': [
                            {'type': 'array', 'items': {'type': 'integer'}, 'description': '关键词 ID 列表，如 [1,2,3,4]'},
                            {'type': 'integer', 'description': '单个关键词 ID，如 1'}
                        ]
                    },
                    'is_favorite': {'type': 'boolean', 'description': '收藏状态：true(收藏)/false(取消收藏)', 'default': True}
                },
                'required': ['ids']
            }
        },
    )
    @action(detail=False, methods=['post'], name='批量收藏关键词')
    def batch_favorite_keywords(self, request):
        """批量收藏或取消收藏关键词"""
        ids = request.data.get('ids')
        if not ids:
            return ApiResponse(code=400, message="请提供 ids 参数")
        
        # 处理单个 ID 或 ID 列表
        if isinstance(ids, int):
            ids = [ids]
        elif isinstance(ids, str):
            # 支持逗号分隔的字符串
            try:
                ids = [int(id_str.strip()) for id_str in ids.split(',') if id_str.strip()]
            except ValueError:
                return ApiResponse(code=400, message="ID 格式错误")
        
        if not isinstance(ids, list) or len(ids) == 0:
            return ApiResponse(code=400, message="ID 列表不能为空")
        
        # 获取收藏状态（默认 true）
        is_favorite = request.data.get('is_favorite', True)
        
        try:
            # 批量更新收藏状态
            updated_count = KeywordLibrary.objects.filter(id__in=ids).update(is_favorite=is_favorite)
            
            if updated_count == 0:
                return ApiResponse(code=404, message="未找到指定的关键词")
            
            action_text = "收藏" if is_favorite else "取消收藏"
            return ApiResponse(
                data={
                    'updated_count': updated_count,
                    'is_favorite': is_favorite
                },
                message=f"成功{action_text} {updated_count} 个关键词"
            )
            
        except Exception as e:
            return ApiResponse(code=500, message=f"操作失败: {str(e)}")
    
    @extend_schema(
        summary="关键词数据看板",
        description="获取关键词统计数据：词库总数、长尾词总数、今日新增、已优化数",
    )
    @action(detail=False, methods=['get'], name='关键词数据看板')
    def keyword_dashboard(self, request):
        """关键词数据看板"""
        from datetime import datetime, timedelta, timezone as dt_timezone
        
        try:
            # 1. 关键词库总数
            total_count = KeywordLibrary.objects.count()
            
            # 2. 长尾词总数
            long_tail_count = KeywordLibrary.objects.filter(keyword_type='long_tail').count()
            
            # 3. 今日新增（与昨日对比）
            now_utc = datetime.now(dt_timezone.utc)
            today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday_start = today_start - timedelta(days=1)
            
            # 今日新增数量
            today_new = KeywordLibrary.objects.filter(
                created_at__gte=today_start
            ).count()
            
            # 昨日新增数量
            yesterday_new = KeywordLibrary.objects.filter(
                created_at__gte=yesterday_start,
                created_at__lt=today_start
            ).count()
            
            # 计算变化
            new_change = today_new - yesterday_new
            new_trend = 'up' if new_change > 0 else ('down' if new_change < 0 else 'stable')
            
            # 4. 已优化数（暂时固定为 99）
            optimized_count = 99
            
            return ApiResponse(
                data={
                    'total_count': total_count,
                    'long_tail_count': long_tail_count,
                    'today_new': today_new,
                    'yesterday_new': yesterday_new,
                    'new_change': new_change,
                    'new_trend': new_trend,
                    'optimized_count': optimized_count,
                },
                message="关键词数据看板获取成功"
            )
            
        except Exception as e:
            return ApiResponse(code=500, message=f"获取数据失败: {str(e)}")


# ==================== 关键词竞品分析 ====================

class CompetitorKeywordSerializer(serializers.ModelSerializer):
    """竞争对手序列化器（精简版）"""
    growth_trend_display = serializers.CharField(source='get_growth_trend_display', read_only=True)
    
    class Meta:
        model = Competitor
        fields = [
            'id', 'name', 'url', 'domain_authority', 'monthly_traffic',
            'keyword_count', 'backlink_count', 'growth_trend', 'growth_trend_display',
            'last_synced_at'
        ]


class CompetitorKeywordDetailSerializer(serializers.ModelSerializer):
    """竞争对手关键词详情序列化器"""
    class Meta:
        model = WebsiteKeyword
        fields = [
            'id', 'keyword', 'rank', 'page_title',
            'bidword_companycount', 'long_keyword_count', 'index',
            'created_at', 'updated_at'
        ]


@extend_schema(tags=["关键词竞品分析"])
@extend_schema_view(
    list=extend_schema(
        summary="获取竞争对手列表及Top3关键词",
        description="获取所有竞争对手列表，每个竞争对手返回前3个关键词",
    ),
    retrieve=extend_schema(
        summary="获取竞争对手关键词详情",
        description="根据竞争对手ID获取所有关键词列表",
        parameters=[
            OpenApiParameter(name="id", type=int, required=True, description="竞争对手ID", location="path"),
        ],
    ),
)
class CompetitorKeywordAnalysisViewSet(BaseViewSet):
    """
    关键词竞品分析 ViewSet
    提供竞争对手关键词分析功能
    """
    permission_classes = [IsAdmin]
    queryset = Competitor.objects.all()
    serializer_class = CompetitorKeywordSerializer
    pagination_class = CustomPagination
    
    def list(self, request, *args, **kwargs):
        """获取竞争对手列表及Top3关键词"""
        queryset = Competitor.objects.all().order_by('-created_at')
        
        # 分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            competitors = page
        else:
            competitors = queryset
        
        # 构建返回数据
        result_data = []
        for competitor in competitors:
            # 获取该竞争对手的前3个关键词（按排名排序）
            top_keywords = WebsiteKeyword.objects.filter(
                competitor=competitor
            ).order_by('rank')[:3]
            
            competitor_data = {
                'id': competitor.id,
                'name': competitor.name,
                'url': competitor.url,
                'domain_authority': competitor.domain_authority,
                'monthly_traffic': competitor.monthly_traffic,
                'keyword_count': competitor.keyword_count,
                'backlink_count': competitor.backlink_count,
                'growth_trend': competitor.growth_trend,
                'growth_trend_display': competitor.get_growth_trend_display(),
                'last_synced_at': competitor.last_synced_at,
                'top_keywords': [
                    {
                        'keyword': kw.keyword,
                        'rank': kw.rank,
                        'page_title': kw.page_title,
                    }
                    for kw in top_keywords
                ]
            }
            result_data.append(competitor_data)
        
        if page is not None:
            return self.get_paginated_response(result_data)
        
        return ApiResponse(data=result_data, message="竞争对手列表获取成功")
    
    def retrieve(self, request, *args, **kwargs):
        """获取竞争对手关键词详情"""
        pk = kwargs.get('pk')
        
        try:
            competitor = Competitor.objects.get(id=pk)
        except Competitor.DoesNotExist:
            return ApiResponse(code=404, message="竞争对手不存在")
        
        # 获取该竞争对手的所有关键词（按排名排序）
        keywords = WebsiteKeyword.objects.filter(
            competitor=competitor
        ).order_by('rank')
        
        # 分页
        page = self.paginate_queryset(keywords)
        if page is not None:
            serializer = CompetitorKeywordDetailSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = CompetitorKeywordDetailSerializer(keywords, many=True)
        return ApiResponse(
            data={
                'competitor': {
                    'id': competitor.id,
                    'name': competitor.name,
                    'url': competitor.url,
                    'keyword_count': competitor.keyword_count,
                },
                'keywords': serializer.data
            },
            message="关键词详情获取成功"
        )
