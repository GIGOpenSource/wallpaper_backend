#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：urls.py
@Author  ：Liang
@Date    ：2026/5/7
@description : 竞争对手管理路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from App.view.seo.competitor.view import CompetitorViewSet

router = DefaultRouter()
router.register(r'', CompetitorViewSet, basename='competitor')
urlpatterns = [
    path('', include(router.urls)),
]
