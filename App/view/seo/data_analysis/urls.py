# -*- coding: UTF-8 -*-
"""
SEO数据分析路由配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from App.view.seo.data_analysis.view import SEODashboardStatsViewSet

router = DefaultRouter()
router.register(r'', SEODashboardStatsViewSet, basename='seo-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]
