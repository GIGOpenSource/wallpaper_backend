# -*- coding: UTF-8 -*-
"""
SEO 管理视图
"""
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from tool.permissions import IsAdmin
from tool.utils import ApiResponse
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from seo.seo_tools import gsc_tool, keyword_tool, backlink_tool


@extend_schema(tags=["SEO管理"])
@extend_schema_view(
    dashboard=extend_schema(
        summary="SEO仪表盘数据",
        description="获取SEO健康度、核心指标、热门查询等综合数据",
        parameters=[
            OpenApiParameter(name="site_url", type=str, required=True, description="网站URL，如: https://example.com/"),
            OpenApiParameter(name="days", type=int, required=False, description="统计天数，默认30天"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "message": {"type": "string", "example": "获取成功"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "health_score": {
                                "type": "object",
                                "properties": {
                                    "score": {"type": "number", "example": 75.5},
                                    "level": {"type": "string", "example": "良好"},
                                    "details": {
                                        "type": "object",
                                        "properties": {
                                            "ctr_score": {"type": "number"},
                                            "position_score": {"type": "number"},
                                            "coverage_score": {"type": "number"},
                                            "mobile_score": {"type": "number"}
                                        }
                                    }
                                }
                            },
                            "performance": {
                                "type": "object",
                                "properties": {
                                    "total_clicks": {"type": "number"},
                                    "total_impressions": {"type": "number"},
                                    "avg_ctr": {"type": "number"},
                                    "avg_position": {"type": "number"},
                                    "period_days": {"type": "integer"}
                                }
                            },
                            "top_queries": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string"},
                                        "clicks": {"type": "number"},
                                        "impressions": {"type": "number"},
                                        "ctr": {"type": "number"},
                                        "position": {"type": "number"}
                                    }
                                }
                            },
                            "top_pages": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "page": {"type": "string"},
                                        "clicks": {"type": "number"},
                                        "impressions": {"type": "number"},
                                        "ctr": {"type": "number"},
                                        "position": {"type": "number"}
                                    }
                                }
                            },
                            "country_data": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "country": {"type": "string"},
                                        "clicks": {"type": "number"},
                                        "impressions": {"type": "number"},
                                        "ctr": {"type": "number"},
                                        "position": {"type": "number"}
                                    }
                                }
                            },
                            "device_data": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "device": {"type": "string"},
                                        "clicks": {"type": "number"},
                                        "impressions": {"type": "number"},
                                        "ctr": {"type": "number"},
                                        "position": {"type": "number"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            400: {"description": "参数错误"},
            500: {"description": "服务器错误"}
        }
    ),
    keyword_research=extend_schema(
        summary="关键词研究",
        description="使用第三方 API 进行关键词挖掘，包括搜索量、竞争度、长尾词拓展等",
        parameters=[
            OpenApiParameter(name="keyword", type=str, required=True, description="种子关键词"),
            OpenApiParameter(name="tool", type=str, required=False,
                             description="使用的工具: semrush, ahrefs, generated",
                             enum=["semrush", "ahrefs", "generated"]),
            OpenApiParameter(name="country", type=str, required=False, description="国家代码，默认 us"),
            OpenApiParameter(name="limit", type=int, required=False, description="返回数量限制，默认 100"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "message": {"type": "string", "example": "获取成功"},
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "keyword": {"type": "string"},
                                "search_volume": {"type": "number"},
                                "cpc": {"type": "number"},
                                "competition": {"type": "number"},
                                "difficulty": {"type": "number"},
                                "source": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    ),
    keyword_difficulty=extend_schema(
        summary="关键词难度分析",
        description="分析关键词的优化难度，给出评分和建议",
        parameters=[
            OpenApiParameter(name="keyword", type=str, required=True, description="要分析的关键词"),
            OpenApiParameter(name="search_volume", type=int, required=False, description="搜索量（可选）"),
            OpenApiParameter(name="cpc", type=float, required=False, description="每次点击费用（可选）"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "keyword": {"type": "string"},
                            "difficulty_score": {"type": "number"},
                            "difficulty_level": {"type": "string"},
                            "factors": {"type": "array", "items": {"type": "string"}},
                            "recommendation": {"type": "string"}
                        }
                    }
                }
            }
        }
    ),
    backlinks=extend_schema(
        summary="外链数据查询",
        description="从第三方 API 获取网站的外链数据",
        parameters=[
            OpenApiParameter(name="domain", type=str, required=True, description="要查询的域名"),
            OpenApiParameter(name="tool", type=str, required=False, description="使用的工具: ahrefs, majestic, semrush",
                             enum=["ahrefs", "majestic", "semrush"]),
            OpenApiParameter(name="limit", type=int, required=False, description="返回数量限制，默认 100"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "source_url": {"type": "string"},
                                "target_url": {"type": "string"},
                                "anchor_text": {"type": "string"},
                                "domain_rating": {"type": "number"},
                                "source": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    ),
    backlink_quality=extend_schema(
        summary="外链质量分析",
        description="分析外链质量，检测有毒外链",
        parameters=[
            OpenApiParameter(name="domain", type=str, required=True, description="要分析的域名"),
            OpenApiParameter(name="tool", type=str, required=False, description="使用的工具: ahrefs, majestic, semrush",
                             enum=["ahrefs", "majestic", "semrush"]),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "quality_analysis": {
                                "type": "object",
                                "properties": {
                                    "total_backlinks": {"type": "number"},
                                    "quality_score": {"type": "number"},
                                    "risk_level": {"type": "string"},
                                    "recommendations": {"type": "array", "items": {"type": "string"}}
                                }
                            },
                            "toxic_backlinks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "url": {"type": "string"},
                                        "anchor": {"type": "string"},
                                        "reason": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    )
)
class SEOViewSet(ViewSet):
    """
    SEO 管理 ViewSet
    提供 SEO 数据分析、健康度评估、关键词挖掘、外链管理等功能
    """
    permission_classes = [IsAdmin]

    @extend_schema(
        summary="SEO仪表盘数据",
        description="获取SEO健康度、核心指标、热门查询等综合数据",
        parameters=[
            OpenApiParameter(name="site_url", type=str, required=True, description="网站URL，如: https://example.com/"),
            OpenApiParameter(name="days", type=int, required=False, description="统计天数，默认30天"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "message": {"type": "string", "example": "获取成功"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "health_score": {
                                "type": "object",
                                "properties": {
                                    "score": {"type": "number", "example": 75.5},
                                    "level": {"type": "string", "example": "良好"},
                                    "details": {
                                        "type": "object",
                                        "properties": {
                                            "ctr_score": {"type": "number"},
                                            "position_score": {"type": "number"},
                                            "coverage_score": {"type": "number"},
                                            "mobile_score": {"type": "number"}
                                        }
                                    }
                                }
                            },
                            "performance": {
                                "type": "object",
                                "properties": {
                                    "total_clicks": {"type": "number"},
                                    "total_impressions": {"type": "number"},
                                    "avg_ctr": {"type": "number"},
                                    "avg_position": {"type": "number"},
                                    "period_days": {"type": "integer"}
                                }
                            },
                            "top_queries": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string"},
                                        "clicks": {"type": "number"},
                                        "impressions": {"type": "number"},
                                        "ctr": {"type": "number"},
                                        "position": {"type": "number"}
                                    }
                                }
                            },
                            "top_pages": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "page": {"type": "string"},
                                        "clicks": {"type": "number"},
                                        "impressions": {"type": "number"},
                                        "ctr": {"type": "number"},
                                        "position": {"type": "number"}
                                    }
                                }
                            },
                            "country_data": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "country": {"type": "string"},
                                        "clicks": {"type": "number"},
                                        "impressions": {"type": "number"},
                                        "ctr": {"type": "number"},
                                        "position": {"type": "number"}
                                    }
                                }
                            },
                            "device_data": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "device": {"type": "string"},
                                        "clicks": {"type": "number"},
                                        "impressions": {"type": "number"},
                                        "ctr": {"type": "number"},
                                        "position": {"type": "number"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            400: {"description": "参数错误"},
            500: {"description": "服务器错误"}
        }
    )
    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        """
        SEO 仪表盘数据
        包含：健康度评分、核心指标、热门查询、热门页面、国家分布、设备分布
        """
        site_url = request.query_params.get('site_url')
        if not site_url:
            return ApiResponse(code=400, message="请提供 site_url 参数")

        # 确保 URL 格式正确
        if not site_url.endswith('/'):
            site_url += '/'

        try:
            days = int(request.query_params.get('days', 30))
        except (TypeError, ValueError):
            days = 30

        # 1. 获取 SEO 健康度评分
        health_data = gsc_tool.calculate_seo_health_score(site_url, days)

        # 2. 获取核心性能指标
        performance = health_data.get('performance', {})

        # 3. 获取热门搜索查询
        top_queries = gsc_tool.get_top_queries(site_url, days, limit=10)

        # 4. 获取热门页面
        top_pages = gsc_tool.get_top_pages(site_url, days, limit=10)

        # 5. 获取国家/地区数据
        country_data = gsc_tool.get_country_data(site_url, days, limit=10)

        # 6. 获取设备类型数据
        device_data = gsc_tool.get_device_data(site_url, days)

        # 确定健康度等级
        score = health_data.get('health_score', 0)
        if score >= 80:
            level = "优秀"
        elif score >= 60:
            level = "良好"
        elif score >= 40:
            level = "一般"
        else:
            level = "需优化"

        return ApiResponse(
            data={
                'health_score': {
                    'score': score,
                    'level': level,
                    'details': health_data.get('details', {})
                },
                'performance': performance,
                'top_queries': top_queries,
                'top_pages': top_pages,
                'country_data': country_data,
                'device_data': device_data,
                'period_days': days
            },
            message="SEO 仪表盘数据获取成功"
        )

    @extend_schema(
        summary="关键词研究",
        description="使用第三方 API 进行关键词挖掘，包括搜索量、竞争度、长尾词拓展等",
        parameters=[
            OpenApiParameter(name="keyword", type=str, required=True, description="种子关键词"),
            OpenApiParameter(name="tool", type=str, required=False,
                             description="使用的工具: semrush, ahrefs, generated",
                             enum=["semrush", "ahrefs", "generated"]),
            OpenApiParameter(name="country", type=str, required=False, description="国家代码，默认 us"),
            OpenApiParameter(name="limit", type=int, required=False, description="返回数量限制，默认 100"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "message": {"type": "string", "example": "获取成功"},
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "keyword": {"type": "string"},
                                "search_volume": {"type": "number"},
                                "cpc": {"type": "number"},
                                "competition": {"type": "number"},
                                "difficulty": {"type": "number"},
                                "source": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='keyword-research')
    def keyword_research(self, request):
        """
        关键词研究
        支持 SEMrush、Ahrefs API 以及自动生成长尾词
        """
        keyword = request.query_params.get('keyword')
        if not keyword:
            return ApiResponse(code=400, message="请提供 keyword 参数")

        tool = request.query_params.get('tool', 'generated')
        country = request.query_params.get('country', 'us')

        try:
            limit = int(request.query_params.get('limit', 100))
        except (TypeError, ValueError):
            limit = 100

        keywords = []

        if tool == 'semrush':
            keywords = keyword_tool.semrush_keyword_research(keyword, country, limit)
        elif tool == 'ahrefs':
            keywords = keyword_tool.ahrefs_keyword_research(keyword, country, limit)
        elif tool == 'generated':
            keywords = keyword_tool.generate_long_tail_keywords(keyword)
        else:
            return ApiResponse(code=400, message="不支持的工具类型，请使用: semrush, ahrefs, generated")

        if not keywords:
            return ApiResponse(
                code=200,
                data=[],
                message=f"未找到相关关键词（可能 API 未配置或无数据），建议检查配置或使用 generated 模式"
            )

        return ApiResponse(
            data=keywords,
            message=f"成功获取 {len(keywords)} 个关键词"
        )

    @extend_schema(
        summary="关键词难度分析",
        description="分析关键词的优化难度，给出评分和建议",
        parameters=[
            OpenApiParameter(name="keyword", type=str, required=True, description="要分析的关键词"),
            OpenApiParameter(name="search_volume", type=int, required=False, description="搜索量（可选）"),
            OpenApiParameter(name="cpc", type=float, required=False, description="每次点击费用（可选）"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "keyword": {"type": "string"},
                            "difficulty_score": {"type": "number"},
                            "difficulty_level": {"type": "string"},
                            "factors": {"type": "array", "items": {"type": "string"}},
                            "recommendation": {"type": "string"}
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='keyword-difficulty')
    def keyword_difficulty(self, request):
        """
        关键词难度分析
        """
        keyword = request.query_params.get('keyword')
        if not keyword:
            return ApiResponse(code=400, message="请提供 keyword 参数")

        try:
            search_volume = int(request.query_params.get('search_volume', 0)) or None
        except (TypeError, ValueError):
            search_volume = None

        try:
            cpc = float(request.query_params.get('cpc', 0)) or None
        except (TypeError, ValueError):
            cpc = None

        analysis = keyword_tool.analyze_keyword_difficulty(keyword, search_volume, cpc)

        return ApiResponse(
            data=analysis,
            message="关键词难度分析完成"
        )

    @extend_schema(
        summary="外链数据查询",
        description="从第三方 API 获取网站的外链数据",
        parameters=[
            OpenApiParameter(name="domain", type=str, required=True, description="要查询的域名"),
            OpenApiParameter(name="tool", type=str, required=False, description="使用的工具: ahrefs, majestic, semrush",
                             enum=["ahrefs", "majestic", "semrush"]),
            OpenApiParameter(name="limit", type=int, required=False, description="返回数量限制，默认 100"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "source_url": {"type": "string"},
                                "target_url": {"type": "string"},
                                "anchor_text": {"type": "string"},
                                "domain_rating": {"type": "number"},
                                "source": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='backlinks')
    def backlinks(self, request):
        """
        外链数据查询
        支持 Ahrefs、Majestic、SEMrush API
        """
        domain = request.query_params.get('domain')
        if not domain:
            return ApiResponse(code=400, message="请提供 domain 参数")

        tool = request.query_params.get('tool', 'ahrefs')

        try:
            limit = int(request.query_params.get('limit', 100))
        except (TypeError, ValueError):
            limit = 100

        backlinks = []

        if tool == 'ahrefs':
            backlinks = backlink_tool.ahrefs_backlinks(domain, limit)
        elif tool == 'majestic':
            backlinks = backlink_tool.majestic_backlinks(domain, limit)
        elif tool == 'semrush':
            backlinks = backlink_tool.semrush_backlinks(domain, limit)
        else:
            return ApiResponse(code=400, message="不支持的工具类型，请使用: ahrefs, majestic, semrush")

        if not backlinks:
            return ApiResponse(
                code=200,
                data=[],
                message=f"未找到外链数据（可能 API 未配置或无数据）"
            )

        return ApiResponse(
            data=backlinks,
            message=f"成功获取 {len(backlinks)} 条外链数据"
        )

    @extend_schema(
        summary="外链质量分析",
        description="分析外链质量，检测有毒外链",
        parameters=[
            OpenApiParameter(name="domain", type=str, required=True, description="要分析的域名"),
            OpenApiParameter(name="tool", type=str, required=False, description="使用的工具: ahrefs, majestic, semrush",
                             enum=["ahrefs", "majestic", "semrush"]),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "quality_analysis": {
                                "type": "object",
                                "properties": {
                                    "total_backlinks": {"type": "number"},
                                    "quality_score": {"type": "number"},
                                    "risk_level": {"type": "string"},
                                    "recommendations": {"type": "array", "items": {"type": "string"}}
                                }
                            },
                            "toxic_backlinks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "url": {"type": "string"},
                                        "anchor": {"type": "string"},
                                        "reason": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='backlink-quality')
    def backlink_quality(self, request):
        """
        外链质量分析
        包含质量评分和有毒外链检测
        """
        domain = request.query_params.get('domain')
        if not domain:
            return ApiResponse(code=400, message="请提供 domain 参数")
    
        tool = request.query_params.get('tool', 'ahrefs')
    
        # 获取外链数据
        backlinks = []
        if tool == 'ahrefs':
            backlinks = backlink_tool.ahrefs_backlinks(domain, limit=200)
        elif tool == 'majestic':
            backlinks = backlink_tool.majestic_backlinks(domain, limit=200)
        elif tool == 'semrush':
            backlinks = backlink_tool.semrush_backlinks(domain, limit=200)
        else:
            return ApiResponse(code=400, message="不支持的工具类型，请使用: ahrefs, majestic, semrush")
    
        if not backlinks:
            return ApiResponse(
                code=200,
                data={
                    'quality_analysis': {},
                    'toxic_backlinks': []
                },
                message="未获取到外链数据，无法进行分析"
            )
    
        # 分析外链质量
        quality_analysis = backlink_tool.analyze_backlink_quality(backlinks)
            
        # 检测有毒外链
        toxic_backlinks = backlink_tool.detect_toxic_backlinks(backlinks)
    
        return ApiResponse(
            data={
                'quality_analysis': quality_analysis,
                'toxic_backlinks': toxic_backlinks
            },
            message="外链质量分析完成"
        )
    
    @extend_schema(
        summary="搜索类型分析",
        description="获取不同搜索类型的数据（Web、图片、视频、新闻）",
        parameters=[
            OpenApiParameter(name="site_url", type=str, required=True, description="网站URL"),
            OpenApiParameter(name="days", type=int, required=False, description="统计天数，默认30天"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "message": {"type": "string", "example": "获取成功"},
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "search_type": {"type": "string"},
                                "total_clicks": {"type": "number"},
                                "total_impressions": {"type": "number"},
                                "avg_ctr": {"type": "number"},
                                "avg_position": {"type": "number"}
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='search-types')
    def search_types(self, request):
        """
        获取不同搜索类型的数据（Web、图片、视频、新闻）
        """
        site_url = request.query_params.get('site_url')
        if not site_url:
            return ApiResponse(code=400, message="请提供 site_url 参数")
    
        if not site_url.endswith('/'):
            site_url += '/'
    
        try:
            days = int(request.query_params.get('days', 30))
        except (TypeError, ValueError):
            days = 30
    
        data = gsc_tool.get_search_type_data(site_url, days)
    
        return ApiResponse(
            data=data,
            message="搜索类型数据获取成功"
        )
    
    @extend_schema(
        summary="性能趋势分析",
        description="获取性能趋势数据（按天/周/月）",
        parameters=[
            OpenApiParameter(name="site_url", type=str, required=True, description="网站URL"),
            OpenApiParameter(name="days", type=int, required=False, description="统计天数，默认30天"),
            OpenApiParameter(name="granularity", type=str, required=False, description="时间粒度: day/week/month", 
                             enum=["day", "week", "month"]),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "message": {"type": "string", "example": "获取成功"},
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "date": {"type": "string"},
                                "end_date": {"type": "string"},
                                "clicks": {"type": "number"},
                                "impressions": {"type": "number"},
                                "ctr": {"type": "number"},
                                "position": {"type": "number"}
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='performance-trend')
    def performance_trend(self, request):
        """
        获取性能趋势数据（按天/周/月）
        """
        site_url = request.query_params.get('site_url')
        if not site_url:
            return ApiResponse(code=400, message="请提供 site_url 参数")
    
        if not site_url.endswith('/'):
            site_url += '/'
    
        try:
            days = int(request.query_params.get('days', 30))
        except (TypeError, ValueError):
            days = 30
    
        granularity = request.query_params.get('granularity', 'day')
        if granularity not in ['day', 'week', 'month']:
            granularity = 'day'
    
        data = gsc_tool.get_performance_trend(site_url, days, granularity)
    
        return ApiResponse(
            data=data,
            message=f"性能趋势数据获取成功（粒度：{granularity}）"
        )
    
    @extend_schema(
        summary="按排名范围查询",
        description="根据排名范围获取热门查询，识别优化机会",
        parameters=[
            OpenApiParameter(name="site_url", type=str, required=True, description="网站URL"),
            OpenApiParameter(name="days", type=int, required=False, description="统计天数，默认30天"),
            OpenApiParameter(name="position_range", type=str, required=False, 
                             description="排名范围: 1-3/4-10/11-20/21-50/51-100",
                             enum=["1-3", "4-10", "11-20", "21-50", "51-100"]),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "message": {"type": "string", "example": "获取成功"},
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "clicks": {"type": "number"},
                                "impressions": {"type": "number"},
                                "ctr": {"type": "number"},
                                "position": {"type": "number"},
                                "opportunity": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='queries-by-position')
    def queries_by_position(self, request):
        """
        根据排名范围获取热门查询
        """
        site_url = request.query_params.get('site_url')
        if not site_url:
            return ApiResponse(code=400, message="请提供 site_url 参数")
    
        if not site_url.endswith('/'):
            site_url += '/'
    
        try:
            days = int(request.query_params.get('days', 30))
        except (TypeError, ValueError):
            days = 30
    
        position_range = request.query_params.get('position_range', '1-10')
        valid_ranges = ['1-3', '4-10', '11-20', '21-50', '51-100']
        if position_range not in valid_ranges:
            return ApiResponse(code=400, message=f"无效的排名范围，请使用: {', '.join(valid_ranges)}")
    
        data = gsc_tool.get_top_queries_by_position(site_url, days, position_range)
    
        return ApiResponse(
            data=data,
            message=f"排名 {position_range} 的查询数据获取成功"
        )
    
    @extend_schema(
        summary="移动可用性检查",
        description="获取移动可用性问题（需要配置 GOOGLE_PAGESPEED_API_KEY）",
        parameters=[
            OpenApiParameter(name="site_url", type=str, required=True, description="网站URL"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "message": {"type": "string", "example": "获取成功"},
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "score": {"type": "number"},
                                "severity": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='mobile-usability')
    def mobile_usability(self, request):
        """
        获取移动可用性问题
        """
        site_url = request.query_params.get('site_url')
        if not site_url:
            return ApiResponse(code=400, message="请提供 site_url 参数")
    
        if not site_url.endswith('/'):
            site_url += '/'
    
        issues = gsc_tool.get_mobile_usability_issues(site_url)
    
        return ApiResponse(
            data=issues,
            message=f"发现 {len(issues)} 个移动可用性问题"
        )
    
    @extend_schema(
        summary="Core Web Vitals",
        description="获取核心网页指标：LCP、FID、CLS、FCP、Speed Index（需要配置 GOOGLE_PAGESPEED_API_KEY）",
        parameters=[
            OpenApiParameter(name="site_url", type=str, required=True, description="网站URL"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "message": {"type": "string", "example": "获取成功"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "lcp": {"type": "number", "description": "最大内容绘制时间(ms)"},
                            "fid": {"type": "number", "description": "首次输入延迟(ms)"},
                            "cls": {"type": "number", "description": "累积布局偏移"},
                            "fcp": {"type": "number", "description": "首次内容绘制(ms)"},
                            "speed_index": {"type": "number", "description": "速度指数(ms)"},
                            "performance_score": {"type": "number", "description": "性能评分(0-100)"}
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='core-web-vitals')
    def core_web_vitals(self, request):
        """
        获取核心网页指标 (Core Web Vitals)
        """
        site_url = request.query_params.get('site_url')
        if not site_url:
            return ApiResponse(code=400, message="请提供 site_url 参数")
    
        if not site_url.endswith('/'):
            site_url += '/'
    
        data = gsc_tool.get_core_web_vitals(site_url)
    
        if not data:
            return ApiResponse(
                code=200,
                data={},
                message="未获取到 Core Web Vitals 数据（可能 API 未配置）"
            )
    
        return ApiResponse(
            data=data,
            message="Core Web Vitals 数据获取成功"
        )
    
    @extend_schema(
        summary="Sitemap状态查询",
        description="获取已提交的 Sitemap 列表及其状态信息",
        parameters=[
            OpenApiParameter(name="site_url", type=str, required=True, description="网站URL"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "message": {"type": "string", "example": "获取成功"},
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "type": {"type": "string"},
                                "is_pending": {"type": "boolean"},
                                "is_sitemap_index": {"type": "boolean"},
                                "last_submitted": {"type": "string"},
                                "errors": {"type": "number"},
                                "warnings": {"type": "number"}
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='sitemap-status')
    def sitemap_status(self, request):
        """
        获取 Sitemap 提交状态
        """
        site_url = request.query_params.get('site_url')
        if not site_url:
            return ApiResponse(code=400, message="请提供 site_url 参数")
    
        if not site_url.endswith('/'):
            site_url += '/'
    
        data = gsc_tool.get_sitemap_status(site_url)
    
        return ApiResponse(
            data=data,
            message=f"获取到 {len(data)} 个 Sitemap 状态"
        )
    
    @extend_schema(
        summary="索引覆盖率摘要",
        description="获取索引覆盖率基本信息（详细数据建议在 GSC UI 中查看）",
        parameters=[
            OpenApiParameter(name="site_url", type=str, required=True, description="网站URL"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "message": {"type": "string", "example": "获取成功"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "note": {"type": "string"},
                            "recommendation": {"type": "string"}
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='index-coverage')
    def index_coverage(self, request):
        """
        获取索引覆盖率摘要
        """
        site_url = request.query_params.get('site_url')
        if not site_url:
            return ApiResponse(code=400, message="请提供 site_url 参数")
    
        if not site_url.endswith('/'):
            site_url += '/'
    
        data = gsc_tool.get_index_coverage_summary(site_url)
    
        return ApiResponse(
            data=data,
            message="索引覆盖率信息获取成功"
        )

