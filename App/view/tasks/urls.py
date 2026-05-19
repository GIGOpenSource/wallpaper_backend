#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：urls.py
@Author  ：AI Assistant
@Date    ：2026/5/19
@description : 定时任务管理URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from App.view.tasks.views import TaskManagementViewSet

router = DefaultRouter()
router.register(r'', TaskManagementViewSet, basename='task')

urlpatterns = [
    path('', include(router.urls)),
]
