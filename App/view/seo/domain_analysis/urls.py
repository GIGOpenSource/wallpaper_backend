#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：urls.py
@Author  ：Liang
@Date    ：2026/4/30
@description : 域名分析路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from App.view.seo.domain_analysis.view import DomainAnalysisViewSet, DetectionLogViewSet

router = DefaultRouter()
router.register(r'', DomainAnalysisViewSet, basename='domain_analysis')


detection_log_router = DefaultRouter()
detection_log_router.register(r'', DetectionLogViewSet, basename='detection_log')

urlpatterns = [
    path('', include(router.urls)),
    path('detection_log/', include(detection_log_router.urls)),
]
