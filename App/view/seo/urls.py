#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：urls.py
@Author  ：Liang
@Date    ：2026/4/16
@description : seo管理
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from App.view.seo.domain_analysis.view import DetectionLogViewSet
from App.view.seo.view import SEOViewSet
from App.view.seo.sitemap import urls as sitemap_urls
from App.view.seo.tdk import urls as tdk_urls
from App.view.seo.backlink import urls as backlink_urls
from App.view.seo.domain_analysis import urls as domain_analysis_urls
from App.view.seo.page_speed import urls as page_speed_urls
from App.view.seo.content_optimization import urls as content_optimization_urls
from App.view.seo.data_analysis import urls as data_analysis_urls
from App.view.seo.inspection import urls as inspection_urls
from App.view.seo.competitor import urls as competitor_urls
router = DefaultRouter()
router.register(r'seo_view', SEOViewSet, basename='seo_view')
router.register(r'detection-log', DetectionLogViewSet, basename='detection_log')

urlpatterns = [
    path('', include(router.urls)),
    path('sitemap_urls/', include(sitemap_urls)),
    path('tdk/', include(tdk_urls)),
    path('backlink/', include(backlink_urls)),
    path('domain_analysis/', include(domain_analysis_urls)),
    path('page_speed/', include(page_speed_urls)),
    path('content_optimization/', include(content_optimization_urls)),
    path('data_analysis/', include(data_analysis_urls)),
    path('inspection/', include(inspection_urls)),
    path('competitor/', include(competitor_urls))
]
