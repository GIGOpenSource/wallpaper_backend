#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
内容优化建议 URL 配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from App.view.seo.content_optimization.view import ContentOptimizationViewSet

router = DefaultRouter()
router.register(r'', ContentOptimizationViewSet, basename='content_optimization')

urlpatterns = [
    path('', include(router.urls)),
]
