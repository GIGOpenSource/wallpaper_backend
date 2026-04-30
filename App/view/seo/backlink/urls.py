#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：urls.py
@Author  ：Liang
@Date    ：2026/4/30
@description : 外链管理路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from App.view.seo.backlink.view import BacklinkManagementViewSet

router = DefaultRouter()
router.register(r'', BacklinkManagementViewSet, basename='backlink')

urlpatterns = [
    path('', include(router.urls)),
]
