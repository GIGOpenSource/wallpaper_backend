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

from App.view.seo.view import SEOViewSet
from App.view.seo.sitemap import urls as sitemap_urls
router = DefaultRouter()
router.register(r'seo_view', SEOViewSet, basename='seo_view')

urlpatterns = [
    path('', include(router.urls)),
    path('sitemap_urls/', include(sitemap_urls))
]
