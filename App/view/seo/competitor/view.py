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
