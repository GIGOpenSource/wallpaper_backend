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
        description="接收页面浏览和用户事件行为数据，自动记录IP和UA（若前端未传）",
        request=None,
        parameters=[
            OpenApiParameter(name="event_type", type=str, required=True, description="事件类型"),
            OpenApiParameter(name="page_path", type=str, required=False, description="页面路径"),
            OpenApiParameter(name="page_name", type=str, required=False, description="页面名称"),
            OpenApiParameter(name="page_type", type=str, required=False, description="页面分类"),
            OpenApiParameter(name="referer", type=str, required=False, description="来源地址"),
            OpenApiParameter(name="page_stay", type=int, required=False, description="停留秒数"),
            OpenApiParameter(name="is_bounce", type=bool, required=False, description="是否跳出"),
            OpenApiParameter(name="unique_id", type=str, required=False, description="访客唯一标识"),
            OpenApiParameter(name="event_name", type=str, required=False, description="事件名称"),
            OpenApiParameter(name="event_params", type=dict, required=False, description="事件扩展参数JSON"),
            OpenApiParameter(name="device_type", type=str, required=False, description="设备类型（desktop/mobile/tablet）"),
            OpenApiParameter(name="region", type=str, required=False, description="地区标识（us/ja等）"),
            OpenApiParameter(name="app_version", type=str, required=False, description="应用版本号"),
            OpenApiParameter(name="event_time", type=str, required=False, description="事件触发时间 yyyy-MM-dd HH:mm:ss"),
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
            
            # 设备类型：优先取前端传的，没有则解析 UA
            device_type = data.get('device_type')
            if not device_type:
                device_type, _ = self._parse_ua(user_agent)
            
            # 处理事件时间与跳出逻辑
            event_time_str = data.get('event_time')
            event_time = None
            if event_time_str:
                try:
                    from django.utils.dateparse import parse_datetime
                    event_time = parse_datetime(event_time_str)
                except:
                    pass

            # --- 后端自动判定 is_bounce ---
            is_bounce = False
            event_name = data.get('event_name', '')
            page_stay = int(data.get('page_stay', 0) or 0)
            unique_id = data.get('unique_id')
            page_path = data.get('page_path')

            if event_name == 'page_hide':
                # 判定规则：停留时间 < 10秒 视为跳出
                if page_stay < 10:
                    is_bounce = True
            elif event_name == 'page_launch':
                # launch 事件通常不直接判定跳出，除非是秒开秒关（由后续的 hide 决定）
                is_bounce = False
            else:
                # 其他事件（如 click, search）不改变跳出状态，保持默认或由前端传参决定
                is_bounce = bool(data.get('is_bounce', False))

            # 构建保存数据
            track_data = {
                'event_type': data.get('event_type', 'custom'),
                'event_name': event_name,
                'event_params': data.get('event_params', {}),
                'page_path': page_path,
                'page_name': data.get('page_name'),
                'page_type': data.get('page_type'),
                'referer': data.get('referer'),
                'page_stay': page_stay,
                'is_bounce': is_bounce,
                'unique_id': unique_id,
                'client_ip': client_ip,
                'user_agent': user_agent,
                'device_type': device_type,
                'browser': data.get('browser') or self._parse_ua(user_agent)[1],
                'region': data.get('region'),
                'app_version': data.get('app_version'),
                'event_time': event_time,
            }
            
            # 直接保存，不做验证
            TrackEvent.objects.create(**track_data)
            
            return ApiResponse(message="ok")
            
        except Exception as e:
            # 即使出错也返回成功，保证前端不阻塞
            return ApiResponse(message="ok")
    
    def _get_client_ip(self, request):
        """获取客户端真实IP"""
        # 尝试从代理头获取
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip[:45]  # 限制长度

    def _parse_ua(self, user_agent):
        """解析 User-Agent 获取设备类型和浏览器名称"""
        ua = user_agent.lower() if user_agent else ''
        device_type = 'desktop'
        browser = 'unknown'

        # 1. 识别设备类型（优先级：iPad > 其他平板 > 手机 > 桌面）
        if 'ipad' in ua:
            device_type = 'tablet'
        elif 'tablet' in ua or 'android' in ua and 'mobile' not in ua:
            device_type = 'tablet'
        elif 'mobile' in ua or 'iphone' in ua or 'android' in ua:
            device_type = 'mobile'
        elif 'harmonyos' in ua:
            device_type = 'mobile'

        # 2. 识别浏览器/应用
        if 'micromessenger' in ua:
            browser = 'wechat'
        elif 'edg/' in ua:
            browser = 'edge'
        elif 'chrome/' in ua and 'edg/' not in ua:
            browser = 'chrome'
        elif 'firefox/' in ua:
            browser = 'firefox'
        elif 'safari/' in ua and 'chrome/' not in ua:
            browser = 'safari'
        elif 'trident/' in ua or 'msie' in ua:
            browser = 'ie'
        
        return device_type, browser
