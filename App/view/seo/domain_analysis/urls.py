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

from App.view.seo.domain_analysis.view import DomainAnalysisViewSet

router = DefaultRouter()
router.register(r'', DomainAnalysisViewSet, basename='domain_analysis')
urlpatterns = [
    path('', include(router.urls)),
]
