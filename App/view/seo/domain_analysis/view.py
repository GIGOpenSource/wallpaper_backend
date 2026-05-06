# -*- coding: UTF-8 -*-
"""
域名分析视图
"""
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from rest_framework.decorators import action
from models.models import DomainAnalysis, BacklinkManagement
from tool.base_views import BaseViewSet
from tool.permissions import IsAdmin
from tool.utils import ApiResponse, CustomPagination
from App.view.seo.domain_analysis.tools import extract_domain, analyze_domain_safety


class DomainAnalysisSerializer(serializers.ModelSerializer):
    """域名分析序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DomainAnalysis
        fields = [
            'id', 'domain', 'safety_score', 'backlink_count',
            'status', 'status_display', 'analyzed_at', 'created_at', 'remark'
        ]
        read_only_fields = ['id', 'analyzed_at', 'created_at']


@extend_schema(tags=["域名分析"])
@extend_schema_view(
    list=extend_schema(
        summary="获取域名分析列表",
        description="获取域名分析列表，支持按状态筛选",
        parameters=[
            OpenApiParameter(name="status", type=str, required=False, description="状态：safe/danger"),
            OpenApiParameter(name="domain", type=str, required=False, description="域名模糊匹配"),
            OpenApiParameter(name="min_safety_score", type=int, required=False, description="最小安全评分"),
        ],
    ),
    retrieve=extend_schema(
        summary="获取域名分析详情",
        description="根据ID获取域名分析详细信息",
    ),
    destroy=extend_schema(
        summary="删除域名分析记录",
        description="删除指定的域名分析记录",
    ),
)
class DomainAnalysisViewSet(BaseViewSet):
    """
    域名分析 ViewSet
    提供域名分析的查询、删除和开始分析功能
    """
    queryset = DomainAnalysis.objects.all()
    serializer_class = DomainAnalysisSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAdmin]

    def list(self, request, *args, **kwargs):
        """获取域名分析列表，支持筛选"""
        queryset = DomainAnalysis.objects.all()
        
        # 按状态筛选
        status = request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # 按域名模糊匹配
        domain = request.query_params.get('domain')
        if domain:
            queryset = queryset.filter(domain__icontains=domain)
        
        # 按最小安全评分筛选
        min_safety_score = request.query_params.get('min_safety_score')
        if min_safety_score:
            try:
                queryset = queryset.filter(safety_score__gte=int(min_safety_score))
            except (TypeError, ValueError):
                pass
        
        # 按分析时间倒序排序
        queryset = queryset.order_by('-analyzed_at')
        
        # 分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="列表获取成功")

    def destroy(self, request, *args, **kwargs):
        """删除域名分析记录"""
        instance = self.get_object()
        instance.delete()
        return ApiResponse(message="删除成功")

    @extend_schema(
        summary="开始域名分析",
        description="从外链列表中获取所有source_page，提取域名并调用第三方API进行分析，如果域名已存在则覆盖更新",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "total_domains": {"type": "integer", "description": "分析的域名总数"},
                            "success_count": {"type": "integer", "description": "成功分析数"},
                            "failed_count": {"type": "integer", "description": "失败数"},
                            "new_count": {"type": "integer", "description": "新增记录数"},
                            "updated_count": {"type": "integer", "description": "更新记录数"}
                        }
                    },
                    "message": {"type": "string"}
                }
            }
        }
    )
    @action(detail=False, methods=['post'], url_path='start-analysis')
    def start_analysis(self, request):
        """
        开始域名分析
        1. 从外链列表获取所有 source_page
        2. 提取域名
        3. 调用第三方API获取安全评分、外链数、状态
        4. 保存或更新到域名分析表
        """
        from django.db import transaction
        
        # 获取所有外链记录的 source_page
        backlinks = BacklinkManagement.objects.values_list('source_page', flat=True).distinct()
        
        if not backlinks:
            return ApiResponse(code=400, message="外链列表为空，无法进行分析")
        
        total_domains = 0
        success_count = 0
        failed_count = 0
        new_count = 0
        updated_count = 0
        
        for source_url in backlinks:
            try:
                # 提取域名
                domain = extract_domain(source_url)
                if not domain:
                    failed_count += 1
                    continue
                
                total_domains += 1
                
                # 调用第三方API分析域名
                analysis_result = analyze_domain_safety(domain)
                
                # 保存或更新到数据库
                with transaction.atomic():
                    domain_obj, created = DomainAnalysis.objects.update_or_create(
                        domain=domain,
                        defaults={
                            'safety_score': analysis_result['safety_score'],
                            'backlink_count': analysis_result['backlink_count'],
                            'status': analysis_result['status'],
                        }
                    )
                    
                    if created:
                        new_count += 1
                    else:
                        updated_count += 1
                    
                    success_count += 1
                    
            except Exception as e:
                failed_count += 1
                continue
        
        return ApiResponse(
            data={
                'total_domains': total_domains,
                'success_count': success_count,
                'failed_count': failed_count,
                'new_count': new_count,
                'updated_count': updated_count
            },
            message=f"域名分析完成，共分析 {total_domains} 个域名，成功 {success_count} 个，失败 {failed_count} 个"
        )

    @extend_schema(
        summary="重新分析指定域名",
        description="传入域名分析记录ID（单个或数组），重新调用API分析并更新数据",
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
                        "description": "域名分析记录ID"
                    }
                },
                "required": ["ids"]
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
                                        "domain": {"type": "string"},
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
    @action(detail=False, methods=['post'], url_path='re-analyze')
    def re_analyze(self, request):
        """
        重新分析指定域名
        支持传入单个ID、ID数组或逗号分隔的ID字符串
        """
        from django.db import transaction
        
        ids_param = request.data.get('ids')
        if not ids_param:
            return ApiResponse(code=400, message="请提供 ids 参数")
        
        # 解析ID列表
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
        
        total_count = len(id_list)
        success_count = 0
        failed_count = 0
        results = []
        
        for domain_id in id_list:
            try:
                # 获取域名分析记录
                domain_obj = DomainAnalysis.objects.get(id=domain_id)
                domain = domain_obj.domain
                
                # 调用第三方API重新分析
                analysis_result = analyze_domain_safety(domain)
                
                # 更新数据库
                with transaction.atomic():
                    domain_obj.safety_score = analysis_result['safety_score']
                    domain_obj.backlink_count = analysis_result['backlink_count']
                    domain_obj.status = analysis_result['status']
                    domain_obj.save()
                
                success_count += 1
                results.append({
                    'id': domain_obj.id,
                    'domain': domain_obj.domain,
                    'status': 'success',
                    'message': '分析成功'
                })
                
            except DomainAnalysis.DoesNotExist:
                failed_count += 1
                results.append({
                    'id': domain_id,
                    'domain': '',
                    'status': 'failed',
                    'message': '记录不存在'
                })
            except Exception as e:
                failed_count += 1
                results.append({
                    'id': domain_id,
                    'domain': '',
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
            message=f"重新分析完成，共处理 {total_count} 个，成功 {success_count} 个，失败 {failed_count} 个"
        )

    @extend_schema(
        summary="获取域名分析统计信息",
        description="获取域名总数、安全域名数、危险域名数等统计信息",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "total_count": {"type": "integer", "description": "域名总数"},
                            "safe_count": {"type": "integer", "description": "安全域名数"},
                            "danger_count": {"type": "integer", "description": "危险域名数"},
                            "avg_safety_score": {"type": "number", "description": "平均安全评分"}
                        }
                    },
                    "message": {"type": "string"}
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """获取域名分析统计信息"""
        from django.db.models import Avg
        
        total_count = DomainAnalysis.objects.count()
        safe_count = DomainAnalysis.objects.filter(status='safe').count()
        danger_count = DomainAnalysis.objects.filter(status='danger').count()
        
        avg_safety = DomainAnalysis.objects.aggregate(
            avg_score=Avg('safety_score')
        )['avg_score'] or 0
        
        return ApiResponse(
            data={
                'total_count': total_count,
                'safe_count': safe_count,
                'danger_count': danger_count,
                'avg_safety_score': round(avg_safety, 2)
            },
            message="统计信息获取成功"
        )
