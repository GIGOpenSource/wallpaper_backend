#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：urls.py
@Author  ：Liang
@Date    ：2026/4/16
@description : 网站配置路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from App.view.seo.sitemap.view import SitemapURLViewSet

router = DefaultRouter()
router.register(r'', SitemapURLViewSet, basename='site-map-config')


urlpatterns = [
    path('', include(router.urls)),

]
