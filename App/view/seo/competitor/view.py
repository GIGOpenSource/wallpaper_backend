# -*- coding: UTF-8 -*-
"""
竞争对手视图
"""
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from rest_framework.decorators import action
from models.models import Competitor
from tool.base_views import BaseViewSet
from tool.permissions import IsAdmin
from tool.utils import ApiResponse, CustomPagination
from App.view.seo.competitor.tools import extract_domain, fetch_competitor_data


class CompetitorSerializer(serializers.ModelSerializer):
    """竞争对手序列化器"""
    growth_trend_display = serializers.CharField(source='get_growth_trend_display', read_only=True)

    class Meta:
        model = Competitor
        fields = [
            'id', 'name', 'url', 'domain_authority', 'monthly_traffic',
            'keyword_count', 'backlink_count', 'growth_trend', 'growth_trend_display',
            'last_synced_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_synced_at', 'created_at', 'updated_at']


@extend_schema(tags=["竞争对手管理"])
@extend_schema_view(
    list=extend_schema(
        summary="获取竞争对手列表",
        description="获取竞争对手列表，支持按增长趋势筛选",
        parameters=[
            OpenApiParameter(name="growth_trend", type=str, required=False, description="增长趋势：up/stable/down"),
            OpenApiParameter(name="name", type=str, required=False, description="网站名称模糊匹配"),
            OpenApiParameter(name="min_domain_authority", type=int, required=False, description="最小域名权重"),
        ],
    ),
    retrieve=extend_schema(
        summary="获取竞争对手详情",
        description="根据ID获取竞争对手详细信息",
    ),
    create=extend_schema(
        summary="添加竞争对手",
        description="添加竞争对手并自动同步SEO数据",
    ),
    destroy=extend_schema(
        summary="删除竞争对手",
        description="删除指定的竞争对手记录",
    ),
)
class CompetitorViewSet(BaseViewSet):
    """
    竞争对手 ViewSet
    提供竞争对手的增删改查和数据同步功能
    """
    queryset = Competitor.objects.all()
    serializer_class = CompetitorSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAdmin]

    def list(self, request, *args, **kwargs):
        """获取竞争对手列表，支持筛选"""
        queryset = Competitor.objects.all()
        
        # 按增长趋势筛选
        growth_trend = request.query_params.get('growth_trend')
        if growth_trend:
            queryset = queryset.filter(growth_trend=growth_trend)
        
        # 按网站名称模糊匹配
        name = request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)
        
        # 按最小域名权重筛选
        min_domain_authority = request.query_params.get('min_domain_authority')
        if min_domain_authority:
            try:
                queryset = queryset.filter(domain_authority__gte=int(min_domain_authority))
            except (TypeError, ValueError):
                pass
        
        # 按创建时间倒序排序
        queryset = queryset.order_by('-created_at')
        
        # 分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="列表获取成功")

    def create(self, request, *args, **kwargs):
        """添加竞争对手并自动同步数据"""
        from django.db import transaction
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            with transaction.atomic():
                # 保存竞争对手基本信息
                competitor = serializer.save()
                
                # 提取域名
                domain = extract_domain(competitor.url)
                if not domain:
                    return ApiResponse(code=400, message="无法从URL中提取域名")
                
                # 调用第三方API获取SEO数据
                seo_data = fetch_competitor_data(domain)
                
                # 更新竞争对手数据
                competitor.domain_authority = seo_data['domain_authority']
                competitor.monthly_traffic = seo_data['monthly_traffic']
                competitor.keyword_count = seo_data['keyword_count']
                competitor.backlink_count = seo_data['backlink_count']
                competitor.growth_trend = seo_data['growth_trend']
                from django.utils import timezone
                competitor.last_synced_at = timezone.now()
                competitor.save()
                
                # 重新序列化返回完整数据
                result_serializer = self.get_serializer(competitor)
                return ApiResponse(
                    data=result_serializer.data,
                    message="竞争对手添加成功，数据已同步",
                    code=201
                )
        except Exception as e:
            return ApiResponse(code=500, message=f"添加竞争对手失败: {str(e)}")

    def destroy(self, request, *args, **kwargs):
        """删除竞争对手"""
        instance = self.get_object()
        instance.delete()
        return ApiResponse(message="删除成功")

    @extend_schema(
        summary="同步竞争对手数据",
        description="手动同步指定竞争对手的SEO数据（单个或全部）",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "ids": {
                        "oneOf": [
                            {"type": "integer", "description": "单个ID"},
                            {"type": "string", "description": "逗号分隔的ID字符串，如: 1,2,3"},
                            {"type": "array", "items": {"type": "integer"}, "description": "ID数组"}
                        ],
                        "description": "竞争对手ID（可选，不传则同步全部）"
                    }
                }
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "total_count": {"type": "integer", "description": "总处理数"},
                            "success_count": {"type": "integer", "description": "成功数"},
                            "failed_count": {"type": "integer", "description": "失败数"},
                            "results": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "name": {"type": "string"},
                                        "status": {"type": "string"},
                                        "message": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "message": {"type": "string"}
                }
            }
        }
    )
    @action(detail=False, methods=['post'], url_path='sync')
    def sync(self, request):
        """
        同步竞争对手数据
        - 如果传入ids：同步指定的竞争对手
        - 如果ids为空：同步全部竞争对手
        """
        from django.db import transaction
        from django.utils import timezone
        
        ids_param = request.data.get('ids')
        
        # 确定要同步的竞争对手列表
        if ids_param:
            id_list = []
            if isinstance(ids_param, int):
                id_list = [ids_param]
            elif isinstance(ids_param, str):
                # 逗号分隔的字符串
                id_list = [int(id_str.strip()) for id_str in ids_param.split(',') if id_str.strip()]
            elif isinstance(ids_param, list):
                id_list = [int(id_val) for id_val in ids_param]
            else:
                return ApiResponse(code=400, message="ids 参数格式错误")
            
            if not id_list:
                return ApiResponse(code=400, message="ID列表为空")
            
            competitors = Competitor.objects.filter(id__in=id_list)
        else:
            # 同步全部
            competitors = Competitor.objects.all()
        
        total_count = competitors.count()
        success_count = 0
        failed_count = 0
        results = []
        
        for competitor in competitors:
            try:
                # 提取域名
                domain = extract_domain(competitor.url)
                if not domain:
                    failed_count += 1
                    results.append({
                        'id': competitor.id,
                        'name': competitor.name,
                        'status': 'failed',
                        'message': '无法提取域名'
                    })
                    continue
                
                # 调用第三方API获取SEO数据
                seo_data = fetch_competitor_data(domain)
                
                # 更新数据库
                with transaction.atomic():
                    competitor.domain_authority = seo_data['domain_authority']
                    competitor.monthly_traffic = seo_data['monthly_traffic']
                    competitor.keyword_count = seo_data['keyword_count']
                    competitor.backlink_count = seo_data['backlink_count']
                    competitor.growth_trend = seo_data['growth_trend']
                    competitor.last_synced_at = timezone.now()
                    competitor.save()
                
                success_count += 1
                results.append({
                    'id': competitor.id,
                    'name': competitor.name,
                    'status': 'success',
                    'message': '同步成功'
                })
                
            except Exception as e:
                failed_count += 1
                results.append({
                    'id': competitor.id,
                    'name': competitor.name,
                    'status': 'failed',
                    'message': str(e)
                })
        
        return ApiResponse(
            data={
                'total_count': total_count,
                'success_count': success_count,
                'failed_count': failed_count,
                'results': results
            },
            message=f"同步完成，共处理 {total_count} 个，成功 {success_count} 个，失败 {failed_count} 个"
        )

    @extend_schema(
        summary="获取竞争对手统计信息",
        description="获取竞争对手总数、平均域名权重、总流量等统计信息",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "total_count": {"type": "integer", "description": "竞争对手总数"},
                            "avg_domain_authority": {"type": "number", "description": "平均域名权重"},
                            "total_monthly_traffic": {"type": "integer", "description": "总月流量"},
                            "total_keywords": {"type": "integer", "description": "总关键词数"},
                            "total_backlinks": {"type": "integer", "description": "总外链数"},
                            "trend_distribution": {
                                "type": "object",
                                "description": "增长趋势分布",
                                "properties": {
                                    "up": {"type": "integer"},
                                    "stable": {"type": "integer"},
                                    "down": {"type": "integer"}
                                }
                            }
                        }
                    },
                    "message": {"type": "string"}
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """获取竞争对手统计信息"""
        from django.db.models import Avg, Sum
        
        total_count = Competitor.objects.count()
        
        stats = Competitor.objects.aggregate(
            avg_da=Avg('domain_authority'),
            total_traffic=Sum('monthly_traffic'),
            total_keywords=Sum('keyword_count'),
            total_backlinks=Sum('backlink_count')
        )
        
        # 获取趋势分布
        trend_distribution = {
            'up': Competitor.objects.filter(growth_trend='up').count(),
            'stable': Competitor.objects.filter(growth_trend='stable').count(),
            'down': Competitor.objects.filter(growth_trend='down').count(),
        }
        
        return ApiResponse(
            data={
                'total_count': total_count,
                'avg_domain_authority': round(stats['avg_da'] or 0, 2),
                'total_monthly_traffic': stats['total_traffic'] or 0,
                'total_keywords': stats['total_keywords'] or 0,
                'total_backlinks': stats['total_backlinks'] or 0,
                'trend_distribution': trend_distribution
            },
            message="统计信息获取成功"
        )

    @extend_schema(
        summary="关键词差距分析",
        description="分析我们与竞争对手之间的关键词差距，返回共同关键词的排名对比",
        parameters=[
            OpenApiParameter(name="competitor_id", type=int, required=True, description="竞争对手ID"),
            OpenApiParameter(name="our_url", type=str, required=False, description="我们的网站URL（默认: https://www.markwallpapers.com/）"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "our_site": {"type": "string", "description": "我们的网站URL"},
                            "competitor_site": {"type": "string", "description": "竞争对手网站URL"},
                            "competitor_name": {"type": "string", "description": "竞争对手名称"},
                            "keyword_gaps": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "keyword": {"type": "string", "description": "关键词"},
                                        "our_ranking": {"type": "integer", "description": "我们的排名（null表示未排名）"},
                                        "competitor_ranking": {"type": "integer", "description": "竞争对手排名"},
                                        "search_volume": {"type": "integer", "description": "搜索量"},
                                        "difficulty": {"type": "integer", "description": "难度值（0-100）"}
                                    }
                                }
                            },
                            "total_gaps": {"type": "integer", "description": "关键词差距总数"}
                        }
                    },
                    "message": {"type": "string"}
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='keyword-gap')
    def keyword_gap(self, request):
        """
        关键词差距分析
        对比我们与竞争对手在相同关键词上的排名差异
        """
        from seo.seo_tools import GoogleSearchConsoleTool
        
        competitor_id = request.query_params.get('competitor_id')
        if not competitor_id:
            return ApiResponse(code=400, message="请提供 competitor_id 参数")
        
        # 获取竞争对手信息
        try:
            competitor = Competitor.objects.get(id=competitor_id)
        except Competitor.DoesNotExist:
            return ApiResponse(code=404, message="竞争对手不存在")
        
        # 我们的网站URL（默认或从参数获取）
        our_url = request.query_params.get('our_url', 'https://www.markwallpapers.com/')
        if not our_url.endswith('/'):
            our_url += '/'
        
        competitor_url = competitor.url
        if not competitor_url.endswith('/'):
            competitor_url += '/'
        
        try:
            gsc_tool = GoogleSearchConsoleTool()
            
            # 获取时间范围（最近3个月）
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            
            # 获取我们网站的关键词数据
            print(f"🔍 获取我们网站的关键词数据: {our_url}")
            our_keywords_data = gsc_tool.get_search_analytics(
                our_url, start_date, end_date, dimensions=['query']
            )
            
            # 尝试获取竞争对手网站的关键词数据（通常会因为权限失败）
            competitor_keywords_data = None
            try:
                competitor_keywords_data = gsc_tool.get_search_analytics(
                    competitor_url, start_date, end_date, dimensions=['query']
                )
            except Exception:
                # 静默处理，不打印日志
                competitor_keywords_data = None
            
            if not our_keywords_data and not competitor_keywords_data:
                # 如果没有真实数据，生成模拟关键词并查询排名
                print("⚠️ 未找到GSC数据，使用模拟关键词查询排名")
                mock_keywords = self._get_mock_keywords()
                
                # 查询我们网站在这些关键词上的排名
                our_rankings = self._query_keyword_rankings(gsc_tool, our_url, start_date, end_date, mock_keywords)
                
                # 查询竞争对手网站在这些关键词上的排名（会返回空字典）
                competitor_rankings = self._query_keyword_rankings(gsc_tool, competitor_url, start_date, end_date, mock_keywords)
                
                # 构建关键词差距数据
                keyword_gaps = []
                for keyword in mock_keywords:
                    our_ranking = our_rankings.get(keyword)
                    competitor_ranking = competitor_rankings.get(keyword)
                    
                    # 只保留至少一方有排名的关键词
                    if our_ranking is not None or competitor_ranking is not None:
                        # 估算搜索量和难度
                        search_volume = self._estimate_search_volume(keyword)
                        difficulty = self._estimate_difficulty(our_ranking, competitor_ranking)
                        
                        keyword_gaps.append({
                            'keyword': keyword,
                            'our_ranking': round(our_ranking, 1) if our_ranking else None,
                            'competitor_ranking': round(competitor_ranking, 1) if competitor_ranking else 0,
                            'search_volume': search_volume,
                            'difficulty': difficulty
                        })
                
                # 按搜索量排序
                keyword_gaps.sort(key=lambda x: x['search_volume'], reverse=True)
                
                return ApiResponse(
                    data={
                        'keyword_gaps': keyword_gaps,
                        'total': len(keyword_gaps),
                        'our_site': our_url,
                        'competitor_site': competitor_url,
                        'competitor_name': competitor.name,
                        'note': '使用模拟关键词查询排名'
                    },
                    message=f"找到 {len(keyword_gaps)} 个关键词差距"
                )
            else:
                # 构建关键词字典
                our_keywords = {}
                for row in our_keywords_data or []:
                    query = row.get('keys', [{}])[0] if isinstance(row.get('keys'), list) else row.get('query', '')
                    if query:
                        our_keywords[query.lower()] = {
                            'position': row.get('position', 0),
                            'clicks': row.get('clicks', 0),
                            'impressions': row.get('impressions', 0)
                        }
                
                competitor_keywords = {}
                if competitor_keywords_data:
                    for row in competitor_keywords_data:
                        query = row.get('keys', [{}])[0] if isinstance(row.get('keys'), list) else row.get('query', '')
                        if query:
                            competitor_keywords[query.lower()] = {
                                'position': row.get('position', 0),
                                'clicks': row.get('clicks', 0),
                                'impressions': row.get('impressions', 0)
                            }
                
                # 找出共同关键词
                common_keywords = set(our_keywords.keys()) & set(competitor_keywords.keys())
                
                # 找出我们独有的关键词
                our_only_keywords = set(our_keywords.keys()) - set(competitor_keywords.keys())
                
                # 找出竞争对手独有的关键词
                competitor_only_keywords = set(competitor_keywords.keys()) - set(our_keywords.keys())
                
                # 合并所有关键词
                all_gap_keywords = common_keywords | our_only_keywords | competitor_only_keywords
                
                # 构建差距分析结果
                keyword_gaps = []
                for keyword in list(all_gap_keywords)[:50]:  # 限制返回50个
                    our_ranking = None
                    our_search_volume = 0
                    
                    if keyword in our_keywords:
                        our_ranking = round(our_keywords[keyword]['position'], 1)
                        our_search_volume = int(our_keywords[keyword].get('impressions', 0))
                    
                    competitor_ranking = 0
                    competitor_search_volume = 0
                    difficulty = 0
                    
                    if keyword in competitor_keywords:
                        competitor_ranking = round(competitor_keywords[keyword]['position'], 1)
                        competitor_search_volume = int(competitor_keywords[keyword].get('impressions', 0))
                        # 根据排名和点击率估算难度
                        ctr = competitor_keywords[keyword].get('clicks', 0) / max(competitor_search_volume, 1)
                        difficulty = min(100, int((1 - ctr) * 100))
                    elif our_ranking:
                        # 只有我们有排名，中等难度
                        difficulty = 50
                    
                    keyword_gaps.append({
                        'keyword': keyword,
                        'our_ranking': our_ranking,
                        'competitor_ranking': competitor_ranking,
                        'our_search_volume': our_search_volume,
                        'competitor_search_volume': competitor_search_volume,
                        'difficulty': difficulty
                    })
                
                # 按我们的搜索量排序
                keyword_gaps.sort(key=lambda x: x['our_search_volume'], reverse=True)
                
                return ApiResponse(
                    data={
                        'keyword_gaps': keyword_gaps,
                        'total': len(keyword_gaps),
                        'our_site': our_url,
                        'competitor_site': competitor_url,
                        'competitor_name': competitor.name,
                        'note': '仅使用我方GSC数据，竞争对手数据不可用'
                    },
                    message=f"找到 {len(keyword_gaps)} 个关键词"
                )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return ApiResponse(code=500, message=f"关键词差距分析失败: {str(e)}")
    
    def _generate_mock_competitor_keywords(self):
        """生成模拟的竞争对手关键词数据"""
        import random
        
        # 壁纸相关的常见关键词
        mock_keywords = [
            '4k wallpaper', 'hd wallpaper', 'desktop wallpaper', 'mobile wallpaper',
            'anime wallpaper', 'nature wallpaper', 'abstract wallpaper', 'gaming wallpaper',
            'iphone wallpaper', 'android wallpaper', 'mac wallpaper', 'windows wallpaper',
            'cartoon wallpaper', 'minimalist wallpaper', 'dark wallpaper', 'colorful wallpaper',
            'space wallpaper', 'ocean wallpaper', 'mountain wallpaper', 'city wallpaper',
            'car wallpaper', 'sports wallpaper', 'music wallpaper', 'art wallpaper',
            'fantasy wallpaper', 'sci-fi wallpaper', 'vintage wallpaper', 'modern wallpaper',
            'flower wallpaper', 'animal wallpaper', 'landscape wallpaper', 'portrait wallpaper'
        ]
        
        competitor_keywords = {}
        for keyword in mock_keywords:
            # 随机生成排名、点击量、展示量
            position = round(random.uniform(1.0, 20.0), 1)
            impressions = random.randint(100, 10000)
            clicks = int(impressions * random.uniform(0.01, 0.1))
            
            competitor_keywords[keyword] = {
                'position': position,
                'clicks': clicks,
                'impressions': impressions
            }
        
        return competitor_keywords
    
    def _get_mock_keywords(self):
        """获取模拟关键词列表（3个）"""
        return [
            '4k wallpaper',
            'anime wallpaper',
            'hd desktop wallpaper'
        ]
    
    def _query_keyword_rankings(self, gsc_tool, site_url, start_date, end_date, keywords):
        """
        查询网站在指定关键词上的排名
        返回: {keyword: position}
        注意：此方法不会抛出异常，失败时返回空字典
        """
        rankings = {}
        
        try:
            # 获取该网站的搜索分析数据
            rows = gsc_tool.get_search_analytics(
                site_url, start_date, end_date, dimensions=['query']
            )
            
            if not rows:
                return rankings
            
            # 构建关键词到排名的映射
            for row in rows:
                query = row.get('keys', [{}])[0] if isinstance(row.get('keys'), list) else row.get('query', '')
                if query and query.lower() in [k.lower() for k in keywords]:
                    rankings[query.lower()] = row.get('position', 0)
        
        except Exception as e:
            # 静默处理异常，不打印日志（避免刷屏）
            pass
        
        return rankings
    
    def _estimate_search_volume(self, keyword):
        """估算关键词搜索量"""
        # 基于关键词长度和常见程度估算
        volume_map = {
            '4k wallpaper': 50000,
            'anime wallpaper': 30000,
            'hd desktop wallpaper': 20000,
        }
        return volume_map.get(keyword.lower(), 10000)
    
    def _estimate_difficulty(self, our_ranking, competitor_ranking):
        """估算关键词难度"""
        # 如果双方都有排名，取平均排名计算难度
        if our_ranking and competitor_ranking:
            avg_ranking = (our_ranking + competitor_ranking) / 2
            # 排名越靠前，难度越高
            difficulty = max(0, min(100, int(100 - avg_ranking * 3)))
        elif our_ranking or competitor_ranking:
            # 只有一方有排名，中等难度
            difficulty = 50
        else:
            # 都没有排名，低难度
            difficulty = 30
        
        return difficulty
