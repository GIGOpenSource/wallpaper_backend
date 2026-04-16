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
from App.view.site.view import SiteConfigViewSet

router = DefaultRouter()
router.register(r'', SiteConfigViewSet, basename='site-config')

urlpatterns = [
    path('', include(router.urls)),
]
