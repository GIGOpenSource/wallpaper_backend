# -*- coding: UTF-8 -*-
"""
域名分析视图
"""
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from rest_framework.decorators import action
from models.models import DomainAnalysis, BacklinkManagement, DetectionLog
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
        summary="重新分析域名",
        description="传入域名分析记录ID（单个或数组），重新调用API分析并更新数据。如果ids为空，则进行全站检测",
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
                        "description": "域名分析记录ID（可选，不传则全站检测）"
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
        重新分析域名
        - 如果传入ids：分析指定的域名
        - 如果ids为空：全站检测（从外链列表获取所有域名）
        - 自动创建检测日志
        """
        from django.db import transaction
        
        ids_param = request.data.get('ids')
        
        # 判断是全站检测还是指定ID检测
        is_full_scan = not ids_param
        
        if is_full_scan:
            # 全站检测：从外链列表获取所有 source_page
            backlinks = BacklinkManagement.objects.values_list('source_page', flat=True).distinct()
            
            if not backlinks:
                return ApiResponse(code=400, message="外链列表为空，无法进行检测")
            
            # 提取所有域名
            domain_set = set()
            for source_url in backlinks:
                domain = extract_domain(source_url)
                if domain:
                    domain_set.add(domain)
            
            if not domain_set:
                return ApiResponse(code=400, message="未提取到有效域名")
            
            # 获取或创建域名分析记录
            id_list = []
            for domain in domain_set:
                domain_obj, created = DomainAnalysis.objects.get_or_create(
                    domain=domain,
                    defaults={
                        'safety_score': 0,
                        'backlink_count': 0,
                        'status': 'safe'
                    }
                )
                id_list.append(domain_obj.id)
        else:
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
        invalid_count = 0  # 失效数量
        suspicious_count = 0  # 可疑数量
        new_discovery_count = 0  # 新发现数量
        
        for domain_id in id_list:
            try:
                # 获取域名分析记录
                domain_obj = DomainAnalysis.objects.get(id=domain_id)
                domain = domain_obj.domain
                old_status = domain_obj.status
                
                # 调用第三方API重新分析
                analysis_result = analyze_domain_safety(domain)
                
                # 更新数据库
                with transaction.atomic():
                    domain_obj.safety_score = analysis_result['safety_score']
                    domain_obj.backlink_count = analysis_result['backlink_count']
                    domain_obj.status = analysis_result['status']
                    domain_obj.save()
                
                success_count += 1
                
                # 统计异常情况
                if analysis_result['status'] == 'danger':
                    if old_status == 'safe':
                        invalid_count += 1  # 从安全变为危险，视为失效
                elif analysis_result['safety_score'] < 60:
                    suspicious_count += 1  # 安全评分低于60，视为可疑
                
                # 如果是新创建的记录
                if (domain_obj.created_at and 
                    (domain_obj.updated_at - domain_obj.created_at).total_seconds() < 5):
                    new_discovery_count += 1
                
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
        
        # 创建检测日志
        if is_full_scan:
            log_content = f"全站域名检测完成，共检测 {total_count} 个域名"
            log_category = 'full_scan'
        else:
            log_content = f"手动检测 {total_count} 个域名"
            log_category = 'manual'
        
        # 构建结果摘要
        summary_parts = []
        if invalid_count > 0:
            summary_parts.append(f"发现{invalid_count}个失效域名")
        if suspicious_count > 0:
            summary_parts.append(f"发现{suspicious_count}个可疑域名")
        if new_discovery_count > 0:
            summary_parts.append(f"发现{new_discovery_count}个新域名")
        if failed_count > 0:
            summary_parts.append(f"{failed_count}个检测失败")
        
        result_summary = "，".join(summary_parts) if summary_parts else "检测结果正常"
        
        # 确定日志状态
        if failed_count == total_count:
            log_status = 'failed'  # 全部失败
        elif failed_count > 0 or invalid_count > 0:
            log_status = 'warning'  # 有部分失败或失效
        else:
            log_status = 'success'  # 全部成功
        
        # 创建日志记录
        DetectionLog.objects.create(
            content=log_content,
            category=log_category,
            status=log_status,
            result_summary=result_summary,
            operator=request.user.username if hasattr(request, 'user') and request.user else '系统'
        )
        
        return ApiResponse(
            data={
                'total_count': total_count,
                'success_count': success_count,
                'failed_count': failed_count,
                'invalid_count': invalid_count,
                'suspicious_count': suspicious_count,
                'new_discovery_count': new_discovery_count,
                'results': results
            },
            message=f"检测完成，共处理 {total_count} 个，成功 {success_count} 个，失败 {failed_count} 个"
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


class DetectionLogSerializer(serializers.ModelSerializer):
    """检测日志序列化器"""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DetectionLog
        fields = [
            'id', 'check_time', 'content', 'category', 'category_display',
            'status', 'status_display', 'result_summary', 'operator'
        ]
        read_only_fields = ['id', 'check_time']


class DetectionLogCreateSerializer(serializers.Serializer):
    """检测日志创建序列化器"""
    content = serializers.CharField(required=True, help_text="检测内容")
    category = serializers.ChoiceField(
        choices=DetectionLog.CATEGORY_CHOICES,
        required=True,
        help_text="类别"
    )
    status = serializers.ChoiceField(
        choices=DetectionLog.STATUS_CHOICES,
        required=False,
        default='success',
        help_text="状态：success/failed/warning"
    )
    result_summary = serializers.CharField(max_length=500, required=False, allow_blank=True, help_text="结果摘要")
    operator = serializers.CharField(max_length=100, required=False, allow_blank=True, help_text="操作人")


@extend_schema(tags=["检测日志"])
@extend_schema_view(
    list=extend_schema(
        summary="获取检测日志列表",
        description="获取检测日志列表，支持按类别、时间范围筛选",
        parameters=[
            OpenApiParameter(name="category", type=str, required=False, description="类别：health_check/invalid_check/new_discovery/domain_check/full_scan/manual"),
            OpenApiParameter(name="start_date", type=str, required=False, description="开始日期（YYYY-MM-DD）"),
            OpenApiParameter(name="end_date", type=str, required=False, description="结束日期（YYYY-MM-DD）"),
        ],
    ),
    retrieve=extend_schema(
        summary="获取检测日志详情",
        description="根据ID获取检测日志详细信息",
    ),
    create=extend_schema(
        summary="创建检测日志",
        description="手动创建检测日志记录",
        request=DetectionLogCreateSerializer,
    ),
    destroy=extend_schema(
        summary="删除检测日志",
        description="删除指定的检测日志记录",
    ),
)
class DetectionLogViewSet(BaseViewSet):
    """
    检测日志 ViewSet
    提供检测日志的增删改查功能
    """
    queryset = DetectionLog.objects.all()
    serializer_class = DetectionLogSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAdmin]

    # def get_serializer_class(self):
    #     if self.action in ['create']:
    #         return DetectionLogCreateSerializer
    #     return DetectionLogSerializer

    def list(self, request, *args, **kwargs):
        """获取检测日志列表，支持筛选"""
        queryset = DetectionLog.objects.all()
        
        # 按类别筛选
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # 按时间范围筛选
        start_date = request.query_params.get('start_date')
        if start_date:
            try:
                from django.utils import timezone
                from datetime import datetime
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                queryset = queryset.filter(check_time__gte=start_dt)
            except (TypeError, ValueError):
                pass
        
        end_date = request.query_params.get('end_date')
        if end_date:
            try:
                from django.utils import timezone
                from datetime import datetime
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                # 包含整天
                from datetime import timedelta
                end_dt = end_dt + timedelta(days=1)
                queryset = queryset.filter(check_time__lt=end_dt)
            except (TypeError, ValueError):
                pass
        
        # 按检测时间倒序排序
        queryset = queryset.order_by('-check_time')
        
        # 分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="列表获取成功")

    def create(self, request, *args, **kwargs):
        """创建检测日志"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        
        log = DetectionLog.objects.create(
            content=validated_data['content'],
            category=validated_data['category'],
            status=validated_data.get('status', 'success'),
            result_summary=validated_data.get('result_summary'),
            operator=validated_data.get('operator')
        )
        
        result_serializer = DetectionLogSerializer(log)
        return ApiResponse(data=result_serializer.data, message="创建成功", code=201)

    def destroy(self, request, *args, **kwargs):
        """删除检测日志"""
        instance = self.get_object()
        instance.delete()
        return ApiResponse(message="删除成功")
