#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
埋点数据上报接口
"""
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiParameter
from tool.base_views import BaseViewSet
from models.models import TrackEvent
from tool.utils import ApiResponse

class TrackViewSet(BaseViewSet):
    """
    埋点数据上报 ViewSet
    仅支持数据上报，不做验证和统计
    """
    queryset = TrackEvent.objects.all()
    
    @extend_schema(
        summary="上报埋点数据",
        description="接收页面浏览和用户事件行为数据，自动记录IP和UA",
        request=None,
        parameters=[
            OpenApiParameter(name="event_type", type=str, required=True, description="事件类型"),
            OpenApiParameter(name="page_path", type=str, required=False, description="页面路径"),
            OpenApiParameter(name="page_name", type=str, required=False, description="页面名称"),
            OpenApiParameter(name="page_type", type=str, required=False, description="页面分类"),
            OpenApiParameter(name="referrer", type=str, required=False, description="来源地址"),
            OpenApiParameter(name="stay_time", type=int, required=False, description="停留秒数"),
            OpenApiParameter(name="is_bounce", type=bool, required=False, description="是否跳出"),
            OpenApiParameter(name="unique_id", type=str, required=False, description="访客唯一标识"),
            OpenApiParameter(name="event_name", type=str, required=False, description="事件名称"),
            OpenApiParameter(name="event_params", type=dict, required=False, description="事件扩展参数JSON"),
        ],
    )
    @action(detail=False, methods=['post'], url_path='report', name='上报埋点数据', permission_classes=[])
    def report(self, request):
        """
        上报埋点数据
        POST /api/track/report/
        
        请求体示例：
        {
            "event_type": "page_view",
            "page_path": "/home",
            "page_name": "首页",
            "page_type": "homepage",
            "referrer": "https://google.com",
            "stay_time": 30,
            "is_bounce": false,
            "unique_id": "uuid-123456",
            "event_name": "home_view",
            "event_params": {"source": "direct"}
        }
        
        后端自动获取：
        - client_ip: 从请求中获取
        - user_agent: 从请求头获取
        - created_at: 自动记录
        
        返回：
        {"code": 200, "msg": "ok"}
        """
        try:
            # 获取请求数据
            data = request.data
            
            # 自动获取客户端信息
            client_ip = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            
            # 构建保存数据
            track_data = {
                'event_type': data.get('event_type', 'custom'),
                'event_name': data.get('event_name'),
                'event_params': data.get('event_params', {}),
                'page_path': data.get('page_path'),
                'page_name': data.get('page_name'),
                'page_type': data.get('page_type'),
                'referrer': data.get('referrer'),
                'stay_time': int(data.get('stay_time', 0) or 0),
                'is_bounce': bool(data.get('is_bounce', False)),
                'unique_id': data.get('unique_id'),
                'client_ip': client_ip,
                'user_agent': user_agent,
            }
            
            # 直接保存，不做验证
            TrackEvent.objects.create(**track_data)
            
            return ApiResponse(code=200, msg="ok")
            
        except Exception as e:
            # 即使出错也返回成功，保证前端不阻塞
            return ApiResponse(code=200, msg="ok")
    
    def _get_client_ip(self, request):
        """获取客户端真实IP"""
        # 尝试从代理头获取
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip[:45]  # 限制长度
