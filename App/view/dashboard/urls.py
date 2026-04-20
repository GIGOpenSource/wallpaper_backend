#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：urls.py
@Author  ：LiangHB
@Date    ：2026/4/20 14:39
@description : 面板统计相关路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from App.view.dashboard.view import DashboardStatsViewSet

router = DefaultRouter()
router.register(r"stats", DashboardStatsViewSet, basename="dashboard_stats")

urlpatterns = [
    path("", include(router.urls)),
]
