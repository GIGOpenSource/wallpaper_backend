# -*- coding: UTF-8 -*-
"""
SEO 管理视图
"""
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from tool.permissions import IsAdmin
from tool.utils import ApiResponse
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from seo.seo_tools import gsc_tool


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
    )
)
class SEOViewSet(ViewSet):
    """
    SEO 管理 ViewSet
    提供 SEO 数据分析、健康度评估等功能
    """
    permission_classes = [IsAdmin]

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
